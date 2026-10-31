"""First-run setup: downloads the speech and translation models (and the
Python packages Qwen3-ASR needs) in the background, with progress for the dock.

  runtime    PyTorch + qwen-asr + sounddevice   ~1.5 GB (Mac) / ~2.5 GB (NVIDIA)
  nllb       Meta NLLB-200 1.3B int8 (CTranslate2) translation   1.3 GB
  qwen-0.6b  Qwen3-ASR 0.6B speech recognition (default)         1.8 GB
  qwen-1.7b  Qwen3-ASR 1.7B speech recognition (dock option)     4.4 GB

Until Qwen3 is ready, captions come from Whisper inside OBS (LocalVocal).
"""
from __future__ import annotations

import importlib.util
import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

# Plain HTTPS downloads, not Hugging Face's Xet transfer: Xet hangs at 0% on some networks
# (firewalls, antivirus, proxies) without an error. A read that stalls 30 s fails and retries.
# Must be set before huggingface_hub is imported anywhere.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
STALL_SECONDS = 60  # no new data for this long: tell the user

from . import paths

log = logging.getLogger("setup")

MODELS = {
    "nllb": {"repo": "OpenNMT/nllb-200-distilled-1.3B-ct2-int8", "size": 1.37e9,
             "label": "Translation (NLLB-200)",
             # CTranslate2 conversion has no SentencePiece model: take it from Meta's repo
             "extra": [("facebook/nllb-200-distilled-1.3B", "sentencepiece.bpe.model")]},
    "qwen-0.6b": {"repo": "Qwen/Qwen3-ASR-0.6B", "size": 1.88e9, "label": "Speech (Qwen3-ASR 0.6B)"},
    "qwen-1.7b": {"repo": "Qwen/Qwen3-ASR-1.7B", "size": 4.7e9, "label": "Speech (Qwen3-ASR 1.7B)"},
}
ORDER = ["nllb", "qwen-0.6b", "qwen-1.7b"]  # translation first: Whisper captions need it too
RUNTIME_PACKAGES = ["qwen-asr", "sounddevice", "soundfile", "silero-vad"]
RUNTIME_SIZE = 1.6e9
# Intel Macs: PyTorch stopped at 2.2.2 (which needs NumPy 1.x); only take
# ready-made wheels, since newer helpers (e.g. llvmlite) don't build there.
INTEL_MAC = sys.platform == "darwin" and platform.machine() == "x86_64"
INTEL_MAC_PINS = ["torch==2.2.2", "torchaudio==2.2.2", "numpy<2", "--only-binary=:all:"]


def model_dir(key: str) -> Path:
    return paths.MODELS / key


def model_ready(key: str) -> bool:
    return (model_dir(key) / ".complete").exists()


def runtime_ready() -> bool:
    return all(importlib.util.find_spec(m) for m in ("torch", "qwen_asr", "sounddevice", "silero_vad"))


def has_nvidia() -> bool:
    if sys.platform == "darwin":
        return False
    exe = shutil.which("nvidia-smi")
    if not exe and sys.platform == "win32":
        p = Path(r"C:\Windows\System32\nvidia-smi.exe")
        exe = str(p) if p.exists() else None
    if not exe:
        return False
    try:
        out = subprocess.run([exe, "-L"], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "GPU" in out.stdout
    except Exception:
        return False


def _hf_timeouts() -> None:
    """Every Hugging Face request gets a 30 s connect/read limit. Without it a blocked
    network (firewall, DNS filter, captive portal) makes the download wait forever at 0%."""
    import requests
    from huggingface_hub import configure_http_backend

    class _Timeout(requests.Session):
        def request(self, *a, **kw):
            if kw.get("timeout") is None:
                kw["timeout"] = (30, 60)
            return super().request(*a, **kw)

    configure_http_backend(backend_factory=_Timeout)


def _why(e: BaseException) -> str:
    """A plain reason for a failed download."""
    s = f"{type(e).__name__} {e}".lower()
    if "ssl" in s or "certificate" in s:
        return ("a secure connection to huggingface.co was refused (often antivirus 'HTTPS scanning' "
                "or an office proxy). Turn that off or try another network.")
    if "nospace" in s or "no space" in s or "errno 28" in s:
        return "the disk is full. Free about 15 GB."
    if "timeout" in s or "timed out" in s or "connect" in s or "resolve" in s or "getaddrinfo" in s:
        return ("huggingface.co can't be reached from this network. Turn off the VPN, try another "
                "network (phone hotspot), or allow Live Captions in the firewall/antivirus.")
    return "check the internet connection."


def _dir_size(p: Path) -> int:
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


class Setup:
    """Runs once in a background thread; `status()` feeds the dock."""

    def __init__(self) -> None:
        self.stage = ""
        self.message = ""
        self.error = ""
        self.done = 0.0      # bytes finished in completed steps
        self.current = 0.0   # bytes of the step in progress
        self.total = 0.0
        self.running = False
        self.on_ready: dict[str, list] = {}
        self._dl_dir: Path | None = None
        self._dl_base = 0
        self._seen = (0, 0.0)  # (bytes, time) of the last progress

    # ---- progress -------------------------------------------------------
    def status(self) -> dict:
        cur = self.current
        message = self.message
        if self._dl_dir is not None:
            cur = max(0, _dir_size(self._dl_dir) - self._dl_base)
            now = time.time()
            if cur != self._seen[0] or not self._seen[1]:
                self._seen = (cur, now)
            elif now - self._seen[1] > STALL_SECONDS:
                message = (f"No data for {int(now - self._seen[1])} s. Check the internet; a VPN, firewall "
                           "or antivirus may block huggingface.co. It keeps trying.")
        done = min(self.total, self.done + cur) if self.total else 0
        return {"running": self.running, "stage": self.stage, "message": message,
                "error": self.error, "done": done, "total": self.total,
                "percent": int(100 * done / self.total) if self.total else 100,
                "ready": {"runtime": runtime_ready(), **{k: model_ready(k) for k in MODELS}}}

    def when_ready(self, key: str, fn) -> None:
        self.on_ready.setdefault(key, []).append(fn)

    def _fire(self, key: str) -> None:
        for fn in self.on_ready.get(key, []):
            try:
                fn()
            except Exception:
                log.exception("ready callback for %s failed", key)

    # ---- steps ----------------------------------------------------------
    def start(self) -> None:
        if self.running:
            return
        todo = [k for k in ORDER if not model_ready(k)]
        need_runtime = not runtime_ready()
        if not todo and not need_runtime:
            return
        self.total = sum(MODELS[k]["size"] for k in todo) + (RUNTIME_SIZE if need_runtime else 0)
        self.done, self.error, self.running = 0.0, "", True
        threading.Thread(target=self._run, args=(todo, need_runtime), daemon=True).start()

    def _run(self, todo: list[str], need_runtime: bool) -> None:
        try:
            # Translation first (Whisper captions are translated too), then the
            # speech runtime + default model, then the optional larger model.
            if "nllb" in todo:
                self._download("nllb")
                todo.remove("nllb")
            if need_runtime:
                self._install_runtime()
                self._fire("runtime")
            for key in todo:
                self._download(key)
            self.stage, self.message = "done", "All models are ready"
        except Exception as e:
            log.exception("Setup failed")
            self.error = f"{e.__class__.__name__}: {e}"
            self.message = "Download stopped: " + _why(e) + " Then press Try again."
        finally:
            self.running = False
            self._dl_dir = None

    def _download(self, key: str) -> None:
        from huggingface_hub import hf_hub_download, snapshot_download
        _hf_timeouts()
        info = MODELS[key]
        target = model_dir(key)
        target.mkdir(parents=True, exist_ok=True)
        self.stage, self.message = key, f"Downloading {info['label']}…"
        log.info(self.message)
        self._dl_dir, self._dl_base, self._seen = target, _dir_size(target), (0, 0.0)
        for attempt in range(3):
            try:
                snapshot_download(info["repo"], local_dir=str(target))
                for repo, fname in info.get("extra", []):
                    hf_hub_download(repo, fname, local_dir=str(target))
                break
            except Exception as e:
                if attempt == 2:
                    raise
                log.warning("Download of %s interrupted, retrying", key, exc_info=True)
                self.message = f"Retrying ({attempt + 2} of 3): {_why(e)}"
                time.sleep(5)
        (target / ".complete").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
        self._dl_dir = None
        self.done += info["size"]
        log.info("%s ready", info["label"])
        self._fire(key)

    def _install_runtime(self) -> None:
        self.stage = "runtime"
        nvidia = has_nvidia()
        self.message = "Installing speech engine" + (" (NVIDIA GPU)" if nvidia else "") + "…"
        log.info(self.message)
        pip = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location",
               "--upgrade", "--target", str(paths.PYLIB)]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        torch_pkgs = INTEL_MAC_PINS if INTEL_MAC else ["torch", "torchaudio"]
        cmd = pip + torch_pkgs + RUNTIME_PACKAGES + ["huggingface_hub>=0.34,<1.0"]
        if nvidia:  # CUDA build of PyTorch; everything else from PyPI
            cmd += ["--index-url", "https://download.pytorch.org/whl/cu124",
                    "--extra-index-url", "https://pypi.org/simple"]
        paths.PYLIB.mkdir(parents=True, exist_ok=True)
        with open(paths.LOG_FILE, "a", encoding="utf-8") as logf:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, creationflags=flags)
        if r.returncode != 0:
            raise RuntimeError("could not install the speech engine (see translator.log)")
        if str(paths.PYLIB) not in sys.path:
            sys.path.append(str(paths.PYLIB))
        importlib.invalidate_caches()
        self.done += RUNTIME_SIZE
        self.current = 0.0
