"""Chooses the speech engine:

  * Qwen3-ASR (default) once its packages and model are downloaded. LocalVocal's
    Whisper filter in OBS is then switched off, so the mic isn't transcribed twice.
  * Whisper in OBS (LocalVocal) until then, writing to DATA/raw/speech.txt.
"""
from __future__ import annotations

import logging
import queue
import threading

from . import models, obs_bridge, paths

log = logging.getLogger("speech")

MODEL_FILE = paths.DATA / "speech_model.txt"
LOCAL_MIC_FILE = paths.DATA / "microphone.json"   # mic chosen in the app window when OBS isn't running
SPEECH_MODELS = {"qwen-0.6b": "Qwen3 0.6B (fast)", "qwen-1.7b": "Qwen3 1.7B (larger)"}
DEFAULT_MODEL = "qwen-0.6b"   # with the vocabulary as context it was as accurate as 1.7B, 2x faster
WHISPER_LANG = {"en": "English", "hi": "Hindi", "auto": None}
NOISE_LEVELS = {"low": 0.4, "medium": 0.55, "high": 0.7}   # voice-detector threshold


def read_model() -> str:
    try:
        m = MODEL_FILE.read_text().strip()
        return m if m in SPEECH_MODELS else DEFAULT_MODEL
    except OSError:
        return DEFAULT_MODEL


def local_mic() -> dict:
    """{"name": None (system default) or device name, "muted": bool, "volume": 0..1}"""
    import json
    try:
        d = json.loads(LOCAL_MIC_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"name": d.get("name") or None, "muted": bool(d.get("muted", False)),
            "volume": float(d.get("volume", 1.0))}


def save_local_mic(**changes) -> dict:
    import json
    d = {**local_mic(), **changes}
    obs_bridge.write_atomic(LOCAL_MIC_FILE, json.dumps(d))
    return d


def input_devices() -> list[dict]:
    """Microphones on this computer: [{"id": name, "name": name}] (default first)."""
    try:
        import sounddevice as sd
        names = []
        for d in sd.query_devices():  # one host API only (Windows lists each mic 3-4 times)
            if d["max_input_channels"] > 0 and d["hostapi"] == sd.default.hostapi and d["name"] not in names:
                names.append(d["name"])
    except Exception:
        return []
    return [{"id": "", "name": "System default"}] + [{"id": n, "name": n} for n in names]


class Speech:
    def __init__(self, setup: models.Setup) -> None:
        self.setup = setup
        self.qwen = None
        self.texts: "queue.Queue[tuple[str, bool]]" = queue.Queue()
        self.model_key = read_model()
        self.loading = False
        self.status = ""
        self.language = "auto"
        self.context = ""
        self.noise = "medium"
        self.enabled = True

    @property
    def engine(self) -> str:
        return "qwen" if self.qwen is not None and self.qwen.model is not None else "whisper"

    def qwen_possible(self, key: str | None = None) -> bool:
        return models.runtime_ready() and models.model_ready(key or self.model_key)

    # ---- settings from the dock / caption mode ----------------------------
    def configure(self, language: str, context: str, noise: str, enabled: bool) -> None:
        self.language, self.context, self.noise, self.enabled = language, context, noise, enabled
        q = self.qwen
        if q is not None:
            q.language = WHISPER_LANG.get(language)
            q.context = context
            q.threshold = NOISE_LEVELS.get(noise, 0.55)
            q.enabled = enabled and not self.mic_muted()

    def mic_muted(self) -> bool:
        return obs_bridge.mic_state().get("muted", False) if obs_bridge.state() else local_mic()["muted"]

    def follow_obs_microphone(self) -> None:
        """Qwen3 listens to the same microphone as OBS's Mic/Aux (or, without
        OBS, the one chosen in the app window)."""
        if self.qwen is None:
            return
        if obs_bridge.state() is not None:
            self.qwen.set_microphone(obs_bridge.mic_name())
            self.qwen.gain = 1.0
        else:
            m = local_mic()
            self.qwen.set_microphone(m["name"])
            self.qwen.gain = max(0.0, min(1.0, m["volume"]))
        self.qwen.enabled = self.enabled and not self.mic_muted()

    # ---- Qwen3 lifecycle -------------------------------------------------
    def start_qwen_if_ready(self, on_started=None) -> None:
        if self.loading or self.engine == "qwen":
            return
        key = self.model_key if self.qwen_possible() else DEFAULT_MODEL
        if not self.qwen_possible(key):
            return
        self.loading = True
        self.status = f"loading {SPEECH_MODELS[key]}…"

        def work():
            try:
                from .qwen_engine import QwenEngine
                eng = self.qwen or QwenEngine(lambda t, final: self.texts.put((t, final)))
                eng.load(key)
                self.qwen = eng
                self.configure(self.language, self.context, self.noise, self.enabled)
                eng.set_microphone(obs_bridge.mic_name() if obs_bridge.state() else local_mic()["name"])
                if not eng._started:
                    eng.start()
                self.status = eng.status
                if on_started:
                    on_started()
            except Exception as e:
                log.exception("Could not start Qwen3-ASR; staying on Whisper")
                self.status = f"Qwen3 failed ({e.__class__.__name__}); using Whisper"
            finally:
                self.loading = False

        threading.Thread(target=work, daemon=True).start()

    def choose_model(self, key: str, on_started=None) -> str:
        if key not in SPEECH_MODELS:
            return "unknown model"
        obs_bridge.write_atomic(MODEL_FILE, key)
        self.model_key = key
        if not self.qwen_possible(key):
            self.setup.start(want=key)
            return "downloading"
        if self.qwen is not None and self.qwen.model_key == key:
            return "ok"
        if self.qwen is not None:
            # keeps captioning with the current size until the other one has loaded
            self.loading = True
            self.status = f"loading {SPEECH_MODELS[key]}…"

            def work():
                try:
                    self.qwen.load(key)
                    self.status = self.qwen.status
                except Exception as e:
                    log.exception("Could not load %s", key)
                    self.status = f"could not load {key} ({e.__class__.__name__})"
                finally:
                    self.loading = False
            threading.Thread(target=work, daemon=True).start()
            return "loading"
        self.start_qwen_if_ready(on_started)
        return "loading"

    # ---- LocalVocal (Whisper) in OBS ---------------------------------------
    def localvocal_settings(self) -> dict:
        lang = {"English": "en", "Hindi": "hi"}.get(WHISPER_LANG.get(self.language) or "", "auto")
        return {
            "whisper_language_select": lang,
            "whisper_model_path": obs_bridge.WHISPER_FAST if obs_bridge.fast_machine() else obs_bridge.WHISPER_SMALL,
            "subtitle_sources": obs_bridge.NO_TEXT_SOURCE,
            "file_output_enable": True,
            "subtitle_output_filename": str(paths.RAW_DIR / "speech.txt"),
            "truncate_output_file": True,
            "no_timestamps": False, "no_context": True,
            "vad_threshold": NOISE_LEVELS.get(self.noise, 0.55) + 0.1,
            "initial_prompt": self.context[:400],
        }

    def sync_obs(self) -> str:
        """Make LocalVocal match the active engine. Returns a status message."""
        with obs_bridge.lock:
            st = obs_bridge.state()
            if st is None:
                return "no OBS · " + self.engine_status()
            mic = (st.get("inputs") or {}).get(obs_bridge.MIC)
            if mic is None:
                return "no Mic/Aux input in OBS"
            if not mic.get("has_filter"):
                return "LocalVocal is not installed in OBS"
            # Whisper only while Qwen3 isn't downloaded yet. While Qwen3 is merely
            # loading (a few seconds), keep Whisper off: switching it on reloads
            # its model in OBS, which pauses OBS for a moment.
            want_on = self.engine == "whisper" and not self.qwen_possible() and self.enabled
            payload: dict = {}
            if want_on:
                want = self.localvocal_settings()

                def differs(k, v):
                    cur = mic.get(k)
                    if isinstance(v, float) and isinstance(cur, (int, float)):
                        return round(cur, 3) != round(v, 3)
                    return cur != v
                if any(differs(k, v) for k, v in want.items()):
                    payload["settings"] = want
            if mic.get("filter_enabled") != want_on:
                payload["filter_enabled"] = want_on
            if payload and not obs_bridge.send(payload, reloads=want_on):
                return "OBS did not respond (is the Live Captions script loaded?)"
            if want_on:
                return "speech: Whisper (until Qwen3 is downloaded)"
            return self.engine_status()

    def engine_status(self) -> str:
        if self.engine == "qwen":
            return f"speech: {SPEECH_MODELS.get(self.qwen.model_key, 'Qwen3')}"
        if self.qwen_possible():
            return f"speech: loading {SPEECH_MODELS.get(self.model_key, 'Qwen3')}…"
        return "speech: waiting for the download" if self.enabled else "captions off"
