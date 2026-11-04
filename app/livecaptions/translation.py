"""Chooses the translation model (NLLB-200 in three sizes). The pipeline keeps
translating with the current one while another loads, then swaps it in.
"""
from __future__ import annotations

import logging
import threading

from . import models, obs_bridge, paths

log = logging.getLogger("translation")

MODEL_FILE = paths.DATA / "translation_model.txt"
TRANSLATION_MODELS = {
    "nllb-600m": "NLLB-200 600M",
    "nllb": "NLLB-200 1.3B",
    "nllb-3.3b": "NLLB-200 3.3B",
}
DEFAULT_MODEL = "nllb"   # the model every install already has


def read_model() -> str:
    try:
        m = MODEL_FILE.read_text().strip()
        return m if m in TRANSLATION_MODELS else DEFAULT_MODEL
    except OSError:
        return DEFAULT_MODEL


class Translation:
    """Which NLLB the caption pipeline uses. `make(key)` builds a Translator."""

    def __init__(self, setup: models.Setup, pipeline, make) -> None:
        self.setup, self.pipeline, self.make = setup, pipeline, make
        self.model_key = read_model()    # chosen (may still be downloading)
        self.loaded_key = ""             # the one translating now
        self.loading = False
        self.status = ""

    def start(self) -> None:
        """At launch: the chosen model if it's here, else the default."""
        key = self.model_key if models.model_ready(self.model_key) else DEFAULT_MODEL
        if models.model_ready(key):
            self._load(key, wait=True)

    def _load(self, key: str, wait: bool = False) -> None:
        self.loading = True
        self.status = f"loading {TRANSLATION_MODELS[key]}…"

        def work():
            try:
                self.pipeline.translator = self.make(key)   # one assignment: the swap is atomic
                self.loaded_key = key
                self.status = ""
            except Exception as e:
                log.exception("Could not load %s", key)
                self.status = f"could not load {TRANSLATION_MODELS[key]} ({e.__class__.__name__})"
            finally:
                self.loading = False

        if wait:
            work()
        else:
            threading.Thread(target=work, daemon=True).start()

    def choose(self, key: str) -> str:
        if key not in TRANSLATION_MODELS:
            return "unknown model"
        obs_bridge.write_atomic(MODEL_FILE, key)
        self.model_key = key
        if not models.model_ready(key):
            self.setup.start(want=key)
            return "downloading"
        if key == self.loaded_key or self.loading:
            return "ok"
        self._load(key)
        return "loading"

    def on_downloaded(self, key: str) -> None:
        """A translation model finished downloading: use it if it's the chosen
        one, or if nothing translates yet."""
        if not self.loading and (key == self.model_key or not self.loaded_key):
            self._load(key, wait=not self.loaded_key)

    def state(self) -> dict:
        return {
            "translation_model": self.model_key,
            "translation_loaded": self.loaded_key,
            "translation_loading": self.loading,
            "translation_status": self.status,
            "translation_default": DEFAULT_MODEL,
            "translation_models": {
                k: {"label": v, "ready": models.model_ready(k),
                    "size_gb": round(models.MODELS[k]["size"] / 1e9, 1)}
                for k, v in TRANSLATION_MODELS.items()},
        }
