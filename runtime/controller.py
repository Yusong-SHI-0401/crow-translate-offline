#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from common import BUS, OBJECT, ROOT, UNIT, isolated_command


def call_bus(method):
    return subprocess.run(["gdbus", "call", "--session", "--dest", BUS, "--object-path", OBJECT,
                           "--method", BUS + ".MainWindow." + method], capture_output=True, text=True)


def start():
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        raise RuntimeError("No desktop session found. Use 'test' for headless verification.")
    state = subprocess.run(["systemctl", "--user", "show", UNIT, "--property=ActiveState", "--value"],
                           capture_output=True, text=True).stdout.strip()
    if state in {"active", "activating"}:
        call_bus("open")
        print("Crow is running. Press Ctrl+Alt+C to show the main window.")
        return
    owner = subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
        "--object-path", "/org/freedesktop/DBus", "--method", "org.freedesktop.DBus.NameHasOwner", BUS],
        capture_output=True, text=True)
    if "true" in owner.stdout:
        raise RuntimeError("Another Crow installation is running. Exit it from its tray menu first.")
    cmd = ["systemd-run", "--user", "--collect", "--unit", UNIT,
           "--description", "Crow Translate Offline", "--property", "Type=exec",
           "--property", "TimeoutStopSec=12", "--property", "KillMode=control-group",
           "--working-directory", str(ROOT)]
    for key in ["DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
                "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE"]:
        if key in os.environ:
            cmd += ["--setenv", key + "=" + os.environ[key]]
    cmd += ["--setenv", "QT_LOGGING_RULES=*.debug=false"]
    subprocess.run(cmd + isolated_command(), check=True)


def uninstall(purge=False):
    subprocess.run(["systemctl", "--user", "stop", UNIT], capture_output=True)
    state = subprocess.run(["systemctl", "--user", "show", UNIT, "--property=ActiveState", "--value"],
                           capture_output=True, text=True)
    if state.returncode or state.stdout.strip() not in {"inactive", "failed"}:
        raise RuntimeError("Cannot verify that the service stopped; files have been retained")
    record = ROOT / "installation.json"
    info = json.loads(record.read_text())
    desktop = info.get("desktop")
    if desktop:
        entry = Path(desktop["path"])
        if entry.exists():
            if entry.read_text() != desktop["content"]:
                raise RuntimeError("The desktop entry changed after installation; review it before uninstalling.")
            if desktop.get("backup"):
                shutil.copy2(desktop["backup"], entry)
            else:
                entry.unlink()
            subprocess.run(["update-desktop-database", str(entry.parent)], capture_output=True)
        info["desktop"] = None
        record.write_text(json.dumps(info, indent=2) + "\n")
    if purge:
        if info.get("prefix") != str(ROOT) or info.get("project") != "crow-translate-offline":
            raise RuntimeError("Installation marker mismatch; refusing deletion")
        shutil.rmtree(ROOT)
        print("Application, models, environment and menu entry removed. Download cache retained.")
    else:
        print(f"Stopped and menu entry removed. Files retained at {ROOT}")
        print("Add --purge to permanently remove this installation as well.")


def main():
    parser = argparse.ArgumentParser(description="Crow Translate with a local, offline English/Chinese engine")
    parser.add_argument("action", nargs="?", default="start", choices=["start", "stop", "status", "test", "logs", "uninstall"])
    parser.add_argument("--purge", action="store_true", help="Permanently remove this installation during uninstall")
    args = parser.parse_args()
    if args.purge and args.action != "uninstall":
        parser.error("--purge is only valid with uninstall")
    if args.action == "start":
        start()
    elif args.action == "stop":
        subprocess.run(["systemctl", "--user", "stop", UNIT], check=True)
    elif args.action == "status":
        raise SystemExit(subprocess.call(["systemctl", "--user", "status", "--no-pager", UNIT]))
    elif args.action == "logs":
        raise SystemExit(subprocess.call(["journalctl", "--user", "-u", UNIT, "--no-pager", "-n", "60"]))
    elif args.action == "test":
        raise SystemExit(subprocess.call(isolated_command("test")))
    elif args.action == "uninstall":
        uninstall(args.purge)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Crow Offline: {exc}") from None
