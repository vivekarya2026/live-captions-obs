"""Where Live Captions keeps its files, on macOS and Windows.

  DATA      ~/.livecaptions            settings, live caption text, logs, models
  SESSIONS  ~/Documents/Live Captions  one folder per captioning session

The OBS script (obs/live_captions.lua) uses the same DATA folder.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

HOME = Path(os.environ.get("USERPROFILE") or Path.home()) if IS_WIN else Path.home()
DATA = Path(os.environ.get("LIVECAPTIONS_DATA") or HOME / ".livecaptions")
MODELS = DATA / "models"
RAW_DIR = DATA / "raw"
LOG_FILE = DATA / "translator.log"
PID_FILE = DATA / "translator.pid"
# Speech packages (PyTorch, Qwen3-ASR) downloaded on first run go here, so the
# app folder itself can stay read-only (e.g. C:\Program Files).
PYLIB = DATA / "pylib"
if PYLIB.is_dir() and str(PYLIB) not in sys.path:
    sys.path.append(str(PYLIB))

PACKAGE = Path(__file__).resolve().parent          # app/livecaptions
RESOURCES = PACKAGE / "data"
VOCAB_DIR = RESOURCES / "vocabulary"


def _documents() -> Path:
    if IS_WIN:
        try:  # the real Documents folder (may be redirected to OneDrive)
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return HOME / "Documents"


SESSIONS = Path(os.environ.get("LIVECAPTIONS_SESSIONS") or _documents() / "Live Captions")


def obs_config_dir() -> Path:
    if IS_WIN:
        return Path(os.environ.get("APPDATA", HOME / "AppData/Roaming")) / "obs-studio"
    if IS_MAC:
        return HOME / "Library/Application Support/obs-studio"
    return HOME / ".config/obs-studio"


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if IS_WIN:
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif IS_MAC:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
