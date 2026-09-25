#!/usr/bin/env python3
"""Build a source-only release from an explicit allowlist."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / "assets.lock.json").read_text())["project_version"]
name = f"crow-translate-offline-{version}"
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
files = [ROOT / name for name in ["README.md", "LICENSE", "THIRD_PARTY.md", "CHANGELOG.md",
                                "install.sh", "requirements.lock", "assets.lock.json", ".gitignore"]]
for folder in ["runtime", "scripts", "config", "docs", "tests", ".github"]:
    files += [p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
for p in files:
    if not p.is_file() or p.is_symlink() or p.stat().st_size > 2 * 1024 * 1024:
        raise SystemExit(f"Unexpected source file: {p}")
archives = [dist / (name + ".tar.gz"), dist / (name + ".zip")]
for p in archives + [dist / "SHA256SUMS"]:
    if p.exists():
        raise SystemExit(f"Release already exists; move it to a backup before rebuilding: {p}")
with tarfile.open(archives[0], "w:gz") as archive:
    for p in sorted(files):
        info = archive.gettarinfo(str(p), arcname=name + "/" + str(p.relative_to(ROOT)))
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        with p.open("rb") as stream:
            archive.addfile(info, stream)
with zipfile.ZipFile(archives[1], "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(files):
        info = zipfile.ZipInfo(name + "/" + str(p.relative_to(ROOT)), date_time=(2026, 1, 1, 0, 0, 0))
        info.external_attr = (0o100755 if p.name == "install.sh" else 0o100644) << 16
        archive.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
(dist / "SHA256SUMS").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in archives))
print("\n".join(str(p) for p in archives))
