"""Developer test: feed WAV clips through the Qwen3 engine (VAD + ASR, real-time
pacing, as if from a microphone) and the caption pipeline, without OBS.

  python tests/test_qwen_live.py [qwen-0.6b|qwen-1.7b] clip1.wav clip2.wav ...
"""
import logging
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import numpy as np
import soundfile as sf

from livecaptions import qwen_engine, translator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

key = sys.argv[1] if sys.argv[1].startswith("qwen-") else "qwen-0.6b"
clips = [c for c in sys.argv[1:] if c.endswith(".wav")]
pipeline = translator.CaptionPipeline(translator.Translator())
results = []
t_end = [0.0]


def on_text(text, final):
    t0 = time.time()
    caption = pipeline.process(text, "speech")
    lag = time.time() - t_end[0]
    results.append((final, lag))
    print(f"  {'FINAL' if final else 'part '} {lag:+5.2f}s vs speech end (translate {time.time() - t0:.2f}s)"
          f" | {text}\n        -> {caption}", flush=True)


eng = qwen_engine.QwenEngine(on_text)
eng.load(key)
eng.context = pipeline.vocab.asr_context_for("hi")
eng._open_stream = lambda: None          # no real microphone: we feed the queue below
eng.start()


def feed(audio: np.ndarray) -> None:
    """Push audio in 32 ms frames at real-time speed, like the mic callback."""
    start = time.time()
    for i in range(0, len(audio), qwen_engine.FRAME):
        eng._audio.put(audio[i:i + qwen_engine.FRAME])
        delay = start + (i + qwen_engine.FRAME) / qwen_engine.SR - time.time()
        if delay > 0:
            time.sleep(delay)


modes = {"h": "hi-en", "e": "en-hinglish"}
for clip in clips:
    name = Path(clip).name
    mode = modes.get(name[0], "auto")
    pipeline.mode = mode
    eng.language = qwen_engine.QWEN_LANG[translator.MODES[mode]["whisper"]]
    audio, sr = sf.read(clip, dtype="float32")
    assert sr == qwen_engine.SR, f"{clip}: need 16 kHz mono"
    pad = np.zeros(int(sr * 0.4), dtype=np.float32)
    print(f"\n--- {name} ({mode}, {len(audio) / sr:.1f}s speech)")
    feed(np.concatenate([pad, audio]))
    t_end[0] = time.time()
    feed(np.zeros(int(sr * 3), dtype=np.float32))   # silence after speaking
eng.stop()
finals = [lag for final, lag in results if final]
if finals:
    print(f"\n{len(finals)} final captions; shown on average {np.mean(finals):.2f}s after the speaker stopped "
          f"(includes the {qwen_engine.END_SILENCE}s pause that ends a sentence)")
