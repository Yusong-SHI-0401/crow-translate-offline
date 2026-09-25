"""Environment and paths for one installation; no user-specific paths."""
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNIT = "crow-offline-" + hashlib.sha256(str(ROOT).encode()).hexdigest()[:12] + ".service"
URL = "http://127.0.0.1:5805"
BUS = "org.kde.CrowTranslate"
OBJECT = "/org/kde/CrowTranslate/MainWindow"


def environment():
    env = os.environ.copy()
    for key in list(env):
        if key.lower().endswith("_proxy") or key.startswith(("ARGOS_", "LT_")) or key in {
            "PYTHONPATH", "PYTHONHOME", "LD_LIBRARY_PATH", "QT_PLUGIN_PATH",
            "QT_QPA_PLATFORM_PLUGIN_PATH", "VIRTUAL_ENV", "LIBRETRANSLATE_API_KEY", "OPENAI_API_KEY",
        }:
            env.pop(key, None)
    env.update({
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1",
        "XDG_CONFIG_HOME": str(ROOT / "config"), "XDG_DATA_HOME": str(ROOT / "data"),
        "XDG_CACHE_HOME": str(ROOT / "cache"), "ARGOS_DEVICE_TYPE": "cpu",
        "ARGOS_MODEL_PROVIDER": "OPENNMT", "ARGOS_COMPUTE_TYPE": "int8",
        "ARGOS_INTER_THREADS": "1", "ARGOS_INTRA_THREADS": "4", "ARGOS_CHUNK_TYPE": "MINISBD",
        "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "4",
        "NO_PROXY": "127.0.0.1,localhost,::1", "QT_LOGGING_RULES": "*.debug=false",
    })
    return env


def isolated_command(mode="gui"):
    # This isolates networking only. Desktop IPC and the user's filesystem remain available.
    return ["/usr/bin/bwrap", "--unshare-net", "--bind", "/", "/", "--",
            "/usr/bin/python3", str(ROOT / "session.py"), mode]
