"""Qwen3-ASR speech recognition: listens to the microphone itself (so it works
the same on macOS and Windows), cuts speech into sentences with Silero VAD and
transcribes them with Qwen3-ASR, passing the Nirankari vocabulary as context
(this fixes words like "sewa", "simran", "सुदीक्षा" that it otherwise mishears).

While a sentence is still being spoken a partial caption is sent every
~2 seconds; the final text follows when the speaker pauses.
"""
from __future__ import annotations

import logging
import platform
import queue
import threading
import time
from typing import Callable

import numpy as np

from . import models

log = logging.getLogger("qwen")

SR = 16000
FRAME = 512                 # 32 ms, the frame size Silero VAD expects at 16 kHz
END_SILENCE = 0.6           # seconds of silence that end a sentence (shorter cuts sentences mid-thought)
MAX_SEGMENT = 10.0          # force a cut on very long sentences
MIN_SPEECH = 0.35           # ignore clicks / coughs shorter than this
PARTIAL_EVERY = 2.0         # partial caption while still speaking
QWEN_LANG = {"en": "English", "hi": "Hindi", "auto": None}


def pick_device() -> tuple[str, "object"]:
    import torch
    if torch.cuda.is_available():
        return "cuda:0", torch.float16
    # MPS only on Apple Silicon (on Intel Macs with AMD graphics it is slow and unreliable)
    if (platform.machine() == "arm64" and getattr(torch.backends, "mps", None)
            and torch.backends.mps.is_available()):
        return "mps", torch.float16
    return "cpu", torch.float32


def is_fast_machine() -> bool:
    dev, _ = pick_device()
    return dev != "cpu"


def find_input_device(name: str | None) -> int | None:
    """sounddevice index for the microphone chosen in OBS (matched by name)."""
    import sounddevice as sd
    if not name:
        return None
    want = name.lower().strip()
    best = None
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0:
            continue
        n = d["name"].lower()
        if n == want:
            return i
        # Windows MME truncates names to 31 characters
        if best is None and (n.startswith(want[:28]) or want.startswith(n[:28])):
            best = i
    return best


class QwenEngine:
    def __init__(self, on_text: Callable[[str, bool], None]) -> None:
        self.on_text = on_text
        self.model = None
        self.model_key = ""
        self.language: str | None = None
        self.context = ""
        self.threshold = 0.55
        self.gain = 1.0             # mic volume set in the app window (no OBS)
        self._enabled = True
        self.device_name: str | None = None
        self.status = "not loaded"
        self._audio: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=400)
        self._jobs: "queue.Queue[tuple[np.ndarray, bool, int, int]]" = queue.Queue()
        self._last_partial: tuple[int, int, str] = (0, 0, "")  # segment, samples covered, text
        self._stream = None
        self._started = False
        self._seg_id = 0
        self._lock = threading.Lock()
        self._mic_lock = threading.Lock()
        self._stop = False

    # ---- model -----------------------------------------------------------
    def load(self, key: str) -> None:
        """Load (or switch to) qwen-0.6b / qwen-1.7b. Blocks; call from a thread."""
        if key == self.model_key and self.model is not None:
            return
        import torch
        from qwen_asr import Qwen3ASRModel
        from transformers.utils import logging as hf_logging
        hf_logging.set_verbosity_error()  # "Setting pad_token_id..." on every sentence
        device, dtype = pick_device()
        self.status = f"loading {key}"
        t0 = time.time()
        if device == "cpu":
            torch.set_num_threads(max(2, (torch.get_num_threads() or 4)))
        model = Qwen3ASRModel.from_pretrained(str(models.model_dir(key)), dtype=dtype, device_map=device,
                                              max_new_tokens=160)
        silence = np.zeros(SR // 2, dtype=np.float32)
        model.transcribe(audio=(silence, SR), language="English")  # warm-up
        with self._lock:
            old, self.model, self.model_key = self.model, model, key
        del old
        self.status = f"ready ({key} on {device.split(':')[0]})"
        log.info("Qwen3-ASR %s loaded on %s in %.1fs", key, device, time.time() - t0)

    # ---- audio -----------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, on: bool) -> None:
        """Off = the microphone is closed (not just ignored), so the system's
        mic-in-use indicator goes off; on = opened again."""
        on = bool(on)
        if on == self._enabled:
            return
        self._enabled = on
        with self._mic_lock:
            if on:
                if self._stream is None and self._started:
                    self._open_stream()
            else:
                self._close_stream()
                log.info("Microphone released (listening off)")

    def _close_stream(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def set_microphone(self, name: str | None) -> None:
        with self._mic_lock:
            if name == self.device_name and (self._stream is not None or not self._enabled):
                return
            self.device_name = name
            if self._enabled:
                self._open_stream()

    def _open_stream(self) -> None:
        import sounddevice as sd
        self._close_stream()
        idx = find_input_device(self.device_name)

        def callback(indata, frames, t, status):
            try:
                self._audio.put_nowait(indata[:, 0].copy())
            except queue.Full:
                pass

        try:
            self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=FRAME,
                                          device=idx, callback=callback)
            self._stream.start()
            name = sd.query_devices(idx if idx is not None else sd.default.device[0])["name"]
            log.info("Qwen3 listening to: %s", name)
        except Exception:
            log.exception("Could not open microphone %r", self.device_name)
            self._stream = None

    def start(self) -> None:
        with self._mic_lock:
            self._started = True
            if self._stream is None and self._enabled:
                self._open_stream()
        threading.Thread(target=self._segmenter, daemon=True).start()
        threading.Thread(target=self._worker, daemon=True).start()

    def stop(self) -> None:
        self._stop = True
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass

    def _segmenter(self) -> None:
        from silero_vad import load_silero_vad
        import torch
        vad = load_silero_vad()
        buf: list[np.ndarray] = []
        speaking = False
        silence = 0.0
        last_partial = 0.0
        pending = np.zeros(0, dtype=np.float32)
        frame_s = FRAME / SR
        while not self._stop:
            try:
                chunk = self._audio.get(timeout=0.5)
            except queue.Empty:
                continue
            if not self.enabled or self.model is None:
                buf, speaking, pending = [], False, np.zeros(0, dtype=np.float32)
                continue
            if self.gain != 1.0:
                chunk = chunk * self.gain
            pending = np.concatenate([pending, chunk])
            while len(pending) >= FRAME:
                frame, pending = pending[:FRAME], pending[FRAME:]
                prob = float(vad(torch.from_numpy(frame), SR).item())
                if prob >= self.threshold:
                    if not speaking:
                        speaking, buf, last_partial = True, buf[-8:], 0.0  # keep ~250 ms lead-in
                        self._seg_id += 1
                    silence = 0.0
                    buf.append(frame)
                elif speaking:
                    buf.append(frame)
                    silence += frame_s
                else:
                    buf = (buf + [frame])[-8:]
                    continue
                dur = len(buf) * frame_s
                if speaking and (silence >= END_SILENCE or dur >= MAX_SEGMENT):
                    if dur - silence >= MIN_SPEECH:
                        speech_samples = int((dur - silence) * SR)
                        self._jobs.put((np.concatenate(buf), True, self._seg_id, speech_samples))
                    speaking, buf, silence = False, [], 0.0
                    vad.reset_states()
                elif speaking and dur - last_partial >= PARTIAL_EVERY and self._jobs.empty():
                    last_partial = dur
                    audio = np.concatenate(buf)
                    self._jobs.put((audio, False, self._seg_id, int((dur - silence) * SR)))

    def _worker(self) -> None:
        while not self._stop:
            try:
                audio, final, seg, speech_samples = self._jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            if not final and (seg != self._seg_id or not self._jobs.empty()):
                continue  # a newer piece of audio is waiting: skip this partial
            p_seg, p_samples, p_text = self._last_partial
            if final and p_seg == seg and p_text and p_samples >= speech_samples - int(0.15 * SR):
                # The last partial already heard the whole sentence: use it, no second pass.
                self._last_partial = (0, 0, "")
                self.on_text(p_text, True)
                continue
            with self._lock:
                model = self.model
            if model is None:
                continue
            try:
                t0 = time.time()
                r = model.transcribe(audio=(audio, SR), language=self.language, context=self.context)
                text = (r[0].text or "").strip()
                self._last_partial = (seg, speech_samples, text) if not final else (0, 0, "")
                if text:
                    log.debug("qwen %s %.2fs (%.1fs audio): %s", "final" if final else "partial",
                              time.time() - t0, len(audio) / SR, text)
                    self.on_text(text, final)
            except Exception:
                log.exception("Qwen3 transcription failed")
