import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
spec2 = importlib.util.spec_from_file_location("common", ROOT / "runtime/common.py")
common = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(common)


class CacheAndArchiveTests(unittest.TestCase):
    def test_offline_cache_is_verified_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / "model.zip").write_bytes(b"model")
            asset = {"name": "model.zip", "sha256": hashlib.sha256(b"model").hexdigest()}
            with mock.patch("urllib.request.build_opener", side_effect=AssertionError("network")):
                self.assertEqual(installer.download(asset, cache, offline=True), cache / "model.zip")
                (cache / "model.zip").write_bytes(b"corrupt")
                with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                    installer.download(asset, cache, offline=True)

    def test_offline_missing_asset_fails_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch("urllib.request.build_opener", side_effect=AssertionError("network")):
                with self.assertRaisesRegex(RuntimeError, "missing"):
                    installer.download({"name": "missing", "sha256": "x"}, Path(directory), offline=True)

    def test_model_archive_cannot_escape_destination(self):
        for member in ["../outside", "/tmp/absolute", "safe/../../outside", "..\\outside"]:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / "model.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr(member, "bad")
                with self.assertRaisesRegex(RuntimeError, "Unsafe"):
                    installer.safe_model_extract(archive, Path(directory) / "models")
                self.assertFalse((Path(directory) / "outside").exists())

    def test_model_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "model.zip"
            entry = zipfile.ZipInfo("link")
            entry.create_system = 3
            entry.external_attr = 0o120777 << 16
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(entry, "/tmp/elsewhere")
            with self.assertRaisesRegex(RuntimeError, "Symlinks"):
                installer.safe_model_extract(archive, Path(directory) / "models")

    def test_normal_model_archive_extracts(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "model.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("translate-en_zh/metadata.json", '{"from_code":"en"}')
            installer.safe_model_extract(archive, Path(directory) / "models")
            self.assertTrue((Path(directory) / "models/translate-en_zh/metadata.json").exists())


class RuntimeTests(unittest.TestCase):
    def test_runtime_discards_proxy_and_cloud_overrides(self):
        with mock.patch.dict(os.environ, {"https_proxy": "http://example.invalid", "ARGOS_MODEL_PROVIDER": "OPENAI",
                              "LT_API_KEYS_REMOTE": "https://example.invalid", "PYTHONPATH": "/wrong"}):
            env = common.environment()
        self.assertNotIn("https_proxy", env)
        self.assertNotIn("LT_API_KEYS_REMOTE", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["ARGOS_MODEL_PROVIDER"], "OPENNMT")

    def test_namespace_is_required_in_both_modes(self):
        for mode in ["gui", "test"]:
            command = common.isolated_command(mode)
            self.assertIn("--unshare-net", command)
            self.assertEqual(command[-1], mode)

    def test_exec_escaping_preserves_literal_path(self):
        value = installer.desktop_quote('/tmp/a b/"$`%\\/crow-offline')
        self.assertIn("%%", value)
        self.assertIn('\\"', value)
        self.assertIn('\\$', value)

    def test_manifest_and_requirements_are_pinned(self):
        manifest = json.loads((ROOT / "assets.lock.json").read_text())
        for asset in manifest["assets"]:
            self.assertEqual(len(asset["sha256"]), 64)
            self.assertTrue(asset["url"].startswith("https://"))
            self.assertEqual(Path(asset["name"]).name, asset["name"])
        for line in (ROOT / "requirements.lock").read_text().splitlines():
            if line and not line.startswith("#"):
                self.assertIn("==", line)


if __name__ == "__main__":
    unittest.main()
