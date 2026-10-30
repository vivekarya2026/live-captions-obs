"""Talks to OBS through the Live Captions OBS script (obs/live_captions.lua),
using small files in the DATA folder (OBS's WebSocket server crashed OBS):

  obs_control.json  request from us  -> applied once by the script
  obs_ack.txt       "<id> ok"        <- written by the script when done
  obs_state.json    LocalVocal + mic state, rewritten every second by the script
"""
from __future__ import annotations

import json
import logging
import platform
import threading
import time
from pathlib import Path

from . import paths

log = logging.getLogger("obs")

CONTROL = paths.DATA / "obs_control.json"
ACK = paths.DATA / "obs_ack.txt"
STATE = paths.DATA / "obs_state.json"
MIC = "Mic/Aux"
NO_TEXT_SOURCE = "(file output only)"

# Whisper models built into LocalVocal (it downloads them itself). Used only
# until Qwen3-ASR is ready.
WHISPER_FAST = "Whisper Large v3 Turbo q5 (574Mb)"
WHISPER_SMALL = "Whisper Small q5 (181Mb)"

lock = threading.Lock()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def state(max_age: float = 15) -> dict | None:
    """Latest state from the OBS script, or None if OBS / the script isn't running."""
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return st if time.time() - st.get("time", 0) < max_age else None


def mic_state() -> dict:
    return ((state() or {}).get("inputs") or {}).get(MIC) or {}


def mic_name() -> str | None:
    """Name of the microphone chosen for Mic/Aux in OBS (None = system default)."""
    m = mic_state()
    dev = m.get("device_id", "")
    if not dev or dev == "default":
        return None
    for d in m.get("devices", []):
        if d.get("id") == dev:
            return d.get("name")
    return None


_fast = None


def fast_machine() -> bool:
    """Apple Silicon Mac or a PC with an NVIDIA GPU."""
    global _fast
    if _fast is None:
        from .models import has_nvidia
        _fast = (paths.IS_MAC and platform.machine() == "arm64") or has_nvidia()
    return _fast


def obs_log_file() -> Path | None:
    try:
        logs = sorted((paths.obs_config_dir() / "logs").glob("*.txt"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return None
    return logs[-1] if logs else None


def wait_for_model_reload(log_file: Path | None, start_size: int, timeout: float = 60) -> bool:
    """LocalVocal reloads Whisper on most settings changes; overlapping reloads
    crash OBS, so wait for 'Whisper model loaded' in the OBS log."""
    if not log_file:
        time.sleep(8)
        return True
    start = time.time()
    while time.time() < start + timeout:
        try:
            with open(log_file, "rb") as f:
                f.seek(start_size)
                new = f.read()
            if b"Whisper model loaded" in new:
                return True
            if b"Loading whisper model" not in new and time.time() - start > 3:
                return True  # this change didn't reload the model
        except OSError:
            pass
        time.sleep(0.25)
    return False


def send(payload: dict, reloads: bool, source: str = MIC) -> bool:
    """Send one request to the OBS script and wait until it has been applied."""
    log_file = obs_log_file()
    size = log_file.stat().st_size if log_file else 0
    req_id = int(time.time() * 1000) % 2_000_000_000
    write_atomic(CONTROL, json.dumps({"id": req_id, "source": source, **payload}))
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if ACK.read_text().startswith(str(req_id)):
                break
        except OSError:
            pass
        time.sleep(0.1)
    else:
        return False
    if reloads:
        wait_for_model_reload(log_file, size)
    return True
