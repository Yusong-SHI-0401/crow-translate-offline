#!/usr/bin/env python3
"""User-level installer: verified assets, fresh venv, offline acceptance test."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import venv
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_environment():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("PIP_", "PYTHON", "LT_", "ARGOS_")) or key.lower().endswith("_proxy"):
            env.pop(key, None)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    return env


def download(asset, cache, proxy=None, offline=False):
    dest = cache / asset["name"]
    if dest.exists():
        if digest(dest) == asset["sha256"]:
            print(f"Verified cache: {dest.name}", flush=True)
            return dest
        raise RuntimeError(f"Checksum mismatch in cache: {dest}. Remove or rename it before retrying.")
    if offline:
        raise RuntimeError(f"Offline cache is missing {asset['name']}")
    proxies = {"http": proxy, "https": proxy} if proxy else {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    request = urllib.request.Request(asset["url"], headers={"User-Agent": "crow-translate-offline/0.1.0"})
    temp = dest.with_suffix(dest.suffix + ".part")
    if temp.exists():
        raise RuntimeError(f"An interrupted download exists: {temp}. Remove it before retrying.")
    print(f"Downloading {asset['name']} (no automatic retries)", flush=True)
    try:
        with opener.open(request, timeout=60) as response, temp.open("xb") as output:
            expected_size = response.headers.get("Content-Length")
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if expected_size and temp.stat().st_size != int(expected_size):
            raise RuntimeError("Incomplete download")
        if digest(temp) != asset["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {asset['name']}")
        temp.rename(dest)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return dest


def safe_model_extract(archive, dest):
    dest = dest.resolve()
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            member = Path(item.filename)
            if member.is_absolute() or ".." in member.parts or "\\" in item.filename:
                raise RuntimeError("Unsafe path in model archive")
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("Symlinks are not allowed in model archives")
            if not (dest / member).resolve().is_relative_to(dest):
                raise RuntimeError("Model archive escapes destination")
        if source.testzip():
            raise RuntimeError("Corrupt model archive")
        source.extractall(dest)


def preflight(python, check_session=True):
    if os.geteuid() == 0:
        raise RuntimeError("Run as your normal desktop user, not root or sudo")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("This release targets Linux x86_64")
    libc, version = platform.libc_ver()
    if libc != "glibc" or tuple(int(v) for v in version.split(".")[:2]) < (2, 35):
        raise RuntimeError("glibc 2.35 or newer is required")
    for tool in ["bwrap", "unsquashfs", "systemctl", "systemd-run", "gdbus", "desktop-file-validate", "update-desktop-database"]:
        if not shutil.which(tool):
            raise RuntimeError(f"Missing {tool}. See docs/Installation.md; no system packages will be installed automatically.")
    result = subprocess.run([python, "-c", "import sys,venv; print('.'.join(map(str,sys.version_info[:2])))"],
                            capture_output=True, text=True, env=clean_environment())
    if result.returncode or result.stdout.strip() not in {"3.10", "3.11", "3.12"}:
        raise RuntimeError("Use a Python 3.10–3.12 interpreter with the venv module; 3.10 is tested")
    subprocess.run(["bwrap", "--unshare-net", "--ro-bind", "/", "/", "--", python, "-c",
                    "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); assert len(socket.if_nameindex())==1"],
                   check=True, env=clean_environment())
    if check_session:
        subprocess.run(["systemctl", "--user", "show-environment"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
    print(f"Preflight OK: Linux x86_64, glibc {version}, Python {result.stdout.strip()}, isolated loopback available")
    return result.stdout.strip()


def pip_command(prefix, proxy=None):
    result = [str(prefix / "engine/bin/python"), "-m", "pip", "--isolated", "--disable-pip-version-check",
              "--no-input", "--keyring-provider", "disabled", "--retries", "0", "--timeout", "60"]
    if proxy:
        result += ["--proxy", proxy]
    return result


def desktop_quote(value):
    # Desktop Exec uses its own escaping, not shell quoting. '%' is a field code.
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%") + '"'


def install_desktop(prefix):
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    entry = data_home / "applications/crow-translate-offline.desktop"
    entry.parent.mkdir(parents=True, exist_ok=True)
    if entry.is_symlink():
        raise RuntimeError("Refusing to replace a symlink at the desktop entry path")
    command = desktop_quote(prefix / "crow-offline")
    content = ("[Desktop Entry]\nType=Application\nName=Crow Translate Offline\n"
               "Name[zh_CN]=Crow Translate 离线\nComment=Offline English-Chinese translation\n"
               f"Exec={command} start\nIcon={prefix}/crow/usr/share/icons/hicolor/128x128/apps/org.kde.CrowTranslate.png\n"
               "Terminal=false\nCategories=Office;\nStartupWMClass=crow-translate\nActions=Stop;\n\n"
               f"[Desktop Action Stop]\nName=Stop Crow and its engine\nName[zh_CN]=停止 Crow 和引擎\nExec={command} stop\n")
    candidate = prefix / "state/menu-entry.desktop"
    candidate.write_text(content)
    subprocess.run(["desktop-file-validate", str(candidate)], check=True)
    backup = None
    if entry.exists():
        backup = prefix / "state/desktop-before-install.desktop"
        shutil.copy2(entry, backup)
    shutil.copy2(candidate, entry)
    refreshed = subprocess.run(["update-desktop-database", str(entry.parent)])
    if refreshed.returncode:
        print("Menu entry installed, but desktop database refresh failed; it may appear after signing in again.")
    return {"path": str(entry), "content": content, "backup": str(backup) if backup else None}


def install(args):
    python = str(Path(args.python).resolve())
    py_version = preflight(python, check_session=not args.no_desktop)
    if args.check:
        return
    prefix = Path(args.prefix).expanduser().absolute()
    if prefix.is_symlink() or (prefix.exists() and any(prefix.iterdir())):
        raise RuntimeError("Destination must be an empty directory. Existing installations are never overwritten.")
    prefix = prefix.resolve()
    if any(ch in str(prefix) for ch in "\n\r"):
        raise RuntimeError("Newlines are not supported in the installation path")
    cache = Path(args.cache).expanduser().absolute()
    cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PROJECT / "assets.lock.json").read_text())
    artifacts = {a["name"]: download(a, cache, args.proxy, args.offline) for a in manifest["assets"]}
    # Create the venv at its final path: moving a populated venv breaks shebangs.
    prefix.mkdir(parents=True, exist_ok=True)
    marker = {"project": "crow-translate-offline", "version": manifest["project_version"],
              "prefix": str(prefix), "python": py_version, "complete": False, "desktop": None,
              "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    record = prefix / "installation.json"
    record.write_text(json.dumps(marker, indent=2) + "\n")
    try:
        for directory in ["state", "config/crow-translate", "data/argos-translate/packages", "cache/minisbd"]:
            (prefix / directory).mkdir(parents=True, exist_ok=True)
        for source in (PROJECT / "runtime").glob("*.py"):
            shutil.copy2(source, prefix / source.name)
        shutil.copy2(PROJECT / "config/crow-translate.conf", prefix / "config/crow-translate/crow-translate.conf")
        shutil.copy2(PROJECT / "requirements.lock", prefix / "requirements.lock")
        shutil.copy2(PROJECT / "assets.lock.json", prefix / "assets.lock.json")
        launcher = prefix / "crow-offline"
        launcher.write_text('#!/usr/bin/env bash\nset -euo pipefail\nroot="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\nexec /usr/bin/python3 "$root/controller.py" "$@"\n')
        launcher.chmod(0o755)
        env = clean_environment()
        subprocess.run([python, "-m", "venv", "--without-pip", str(prefix / "engine")], check=True, env=env)
        bootstrap = [artifacts[a["name"]] for a in manifest["assets"] if a["kind"] == "bootstrap"]
        pip_wheel = next(p for p in bootstrap if p.name.startswith("pip-"))
        bootstrap_code = "import runpy,sys; sys.path.insert(0,sys.argv[1]); sys.argv=['pip']+sys.argv[2:]; runpy.run_module('pip',run_name='__main__')"
        subprocess.run([str(prefix / "engine/bin/python"), "-c", bootstrap_code, str(pip_wheel),
            "--isolated", "--disable-pip-version-check", "install", "--no-index", "--no-deps",
            *map(str, bootstrap)], check=True, env=env)
        wheels = cache / ("wheels-py" + py_version)
        if args.offline:
            if not wheels.is_dir():
                raise RuntimeError(f"Offline wheel cache is missing: {wheels}")
        else:
            wheels.mkdir(exist_ok=True)
            subprocess.run(pip_command(prefix, args.proxy) + ["wheel", "--no-build-isolation",
                "--index-url", "https://pypi.org/simple", "--cache-dir", str(cache / "pip-cache"),
                "--wheel-dir", str(wheels), "-r", str(PROJECT / "requirements.lock")], check=True, env=env)
        subprocess.run(pip_command(prefix) + ["install", "--no-index", "--find-links", str(wheels),
            "-r", str(PROJECT / "requirements.lock")], check=True, env=env)
        subprocess.run(pip_command(prefix) + ["check"], check=True, env=env)
        for asset in manifest["assets"]:
            artifact = artifacts[asset["name"]]
            if asset["kind"] == "crow":
                # Official, verified AppImage runtime supplies the SquashFS offset; no FUSE required.
                artifact.chmod(artifact.stat().st_mode | 0o100)
                offset = subprocess.check_output([str(artifact), "--appimage-offset"], text=True, env=env).strip()
                if not offset.isdigit():
                    raise RuntimeError("Unexpected AppImage offset")
                subprocess.run(["unsquashfs", "-no-progress", "-no-xattrs", "-processors", "4", "-offset", offset,
                                "-dest", str(prefix / "crow"), str(artifact)], check=True, env=env)
            elif asset["kind"] == "model":
                safe_model_extract(artifact, prefix / "data/argos-translate/packages")
            elif asset["kind"] == "sbd":
                shutil.copy2(artifact, prefix / "cache/minisbd" / artifact.name)
        print("Testing the real Crow CLI and engine with no external network...", flush=True)
        subprocess.run([str(launcher), "test"], check=True, env=env)
        if not args.no_desktop:
            marker["desktop"] = install_desktop(prefix)
        marker["complete"] = True
        record.write_text(json.dumps(marker, indent=2) + "\n")
        print(f"\nInstalled and verified. Start with:\n{shlex.quote(str(launcher))} start")
        print("No login autostart was enabled. Keep this installation at its current path.")
    except Exception:
        print(f"Installation incomplete. Existing apps are unchanged. Partial files retained at {prefix}", file=sys.stderr)
        raise


def main():
    default_prefix = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "crow-translate-offline"
    default_cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "crow-translate-offline"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default=str(default_prefix), help="Empty destination directory")
    parser.add_argument("--cache", default=str(default_cache), help="Download cache; retain it for offline reinstalls")
    parser.add_argument("--python", default="/usr/bin/python3", help="Python 3.10–3.12, with venv")
    parser.add_argument("--proxy", help="Explicit download proxy, e.g. http://127.0.0.1:7897")
    parser.add_argument("--offline", action="store_true", help="Install solely from a previously populated cache")
    parser.add_argument("--no-desktop", action="store_true", help="Skip menu installation and user-session check")
    parser.add_argument("--check", action="store_true", help="Read-only prerequisites check")
    try:
        install(parser.parse_args())
    except (OSError, RuntimeError, ValueError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        # Do not print subprocess command lines, which may contain proxy credentials.
        if isinstance(exc, subprocess.CalledProcessError):
            parser.exit(1, f"Installation command failed (exit {exc.returncode}); see output above.\n")
        parser.exit(1, f"Installation failed: {exc}\n")


if __name__ == "__main__":
    main()
