"""Caption styles that follow the meaning, not every word.

  word     Word for word: the translation as it is (no AI rewrite)
  natural  The meaning, said the way a person would (keeps every fact)
  simple   The main point, in plain words (at most about 20 words)

A small text model on the computer (Qwen, CTranslate2 int8) rewrites English into
English. NLLB still does the language change, so the model never has to translate.
Fast because: greedy decoding, thinking off, short outputs, and a time limit. When
the rewrite is late or fails a check, `rewrite()` returns None and the caller shows
the word-for-word caption, so captions never stall.
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

log = logging.getLogger("meaning")

STYLES = {
    "word": {"label": "Word for word", "hint": "every word, as said"},
    "natural": {"label": "Natural", "hint": "the meaning, said the way a person would"},
    "simple": {"label": "Simple", "hint": "the main point, in plain words"},
}
SIMPLE_MAX_WORDS = 20
MIN_WORDS = 4          # 3 words or fewer ("ji", "thank you"): nothing to rewrite
BUDGET_SECONDS = float(os.environ.get("LIVECAPTIONS_STYLE_SECONDS", "1.5"))

_RULES = ("Never answer, explain or comment. Never add anything that was not said. "
          "Keep every name, number and word such as sewa, simran, satsang, Nirankar exactly as written. "
          "Write only the new sentence.")
PROMPTS = {
    "natural": ("You rewrite live speech captions. Say the same meaning in fluent, natural English, "
                "the way a person would say it. Keep every fact. Drop filler and repeated words. " + _RULES),
    "simple": (f"You rewrite live speech captions. Say the main point in plain, everyday English, "
               f"in at most {SIMPLE_MAX_WORDS} words. Use short, common words. " + _RULES),
}
# One worked example per style: small models follow an example better than rules.
EXAMPLES = {
    "natural": ("So, so we, we all should do the sewa with, with the love, and then Nirankar is "
                "happy from us.",
                "We should all do sewa with love, and then Nirankar is pleased with us."),
    "simple": ("When we are doing simran in every moment of our life, then the mind becomes "
               "steady and we are not troubled by the worries of the world.",
               "Doing simran all the time keeps the mind calm and free of worry."),
}

_PREAMBLE = re.compile(r"^\s*(here is|here's|sure|certainly|okay,? here|rewritten|rewrite|natural|simple|"
                       r"the speaker|speaker|they (say|said)|this means|in other words|answer|output)\b[^a-z]*",
                       re.IGNORECASE)
_NOT_ENGLISH = re.compile(r"[^\x00-\x7F\u2018\u2019\u201C\u201D\u2013\u2014\u2026\u00C0-\u024F]")
_NUMBER = re.compile(r"\d+")
# A rewrite may reword, but not bring in new ideas: at most this share of its longer
# words may be missing from what was said (the small model sometimes copies words from
# its example or invents a moral, e.g. "choose between truth and illusion").
NEW_WORDS = {"natural": 0.34, "simple": 0.56}


def words(text: str) -> list[str]:
    return re.findall(r"[\w'’-]+", text)


def _stem(w: str) -> str:
    w = w.lower().replace("’", "'").split("'")[0]
    for end in ("ing", "ed", "es", "s", "ly"):
        if len(w) > len(end) + 3 and w.endswith(end):
            return w[:-len(end)]
    return w


def new_word_share(source: str, out: str) -> float:
    have = {_stem(w) for w in words(source)}
    long = [_stem(w) for w in words(out) if len(w) >= 4]
    return sum(w not in have for w in long) / len(long) if long else 0.0


def check(source: str, out: str, style: str, terms: list[str] = ()) -> str | None:
    """The rewrite if it is safe to show, else None (then word for word is shown)."""
    if "\n" in out.strip():  # a second line is an explanation or a reply
        return None
    out = " ".join(out.split()).strip()
    if len(out) >= 2 and out[0] in "\"'“‘" and out[-1] in "\"'”’":  # wrapped in quotes
        out = out[1:-1].strip()
    if not out or _PREAMBLE.match(out) or _NOT_ENGLISH.search(out):
        return None
    n_in, n_out = len(words(source)), len(words(out))
    limit = min(SIMPLE_MAX_WORDS + 4, n_in + 3) if style == "simple" else int(n_in * 1.3) + 3
    if n_out == 0 or n_out > limit:
        return None
    low = out.lower()
    for t in terms:  # vocabulary terms and names must survive
        if t and t.lower() not in low:
            return None
    if not set(_NUMBER.findall(source)) <= set(_NUMBER.findall(out)):
        return None
    if new_word_share(source, out) > NEW_WORDS.get(style, 0.5):
        return None
    return out


class Rewriter:
    """Loads the model once; `rewrite()` is safe to call from one thread at a time."""

    def __init__(self, model_dir: Path, threads: int | None = None) -> None:
        import ctranslate2
        from tokenizers import Tokenizer

        t0 = time.time()
        threads = threads or max(2, min(6, (os.cpu_count() or 4) // 2))
        self.model = ctranslate2.Generator(str(model_dir), device="cpu", compute_type="int8",
                                           intra_threads=threads)
        self.tok = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        # Qwen3 thinks before answering unless given an empty thought; Qwen2.5 doesn't think.
        self.no_think = "<think>\n\n</think>\n\n" if self.tok.token_to_id("<think>") is not None else ""
        self.end = "<|im_end|>"
        self.last_seconds = 0.0
        log.info("Caption style model loaded in %.1fs", time.time() - t0)

    def _prompt(self, text: str, style: str, context: str) -> list[str]:
        ex_in, ex_out = EXAMPLES[style]
        user = (f"Earlier: {context}\n" if context else "") + f"Sentence: {text}"
        chat = (f"<|im_start|>system\n{PROMPTS[style]}<|im_end|>\n"
                f"<|im_start|>user\nSentence: {ex_in}<|im_end|>\n"
                f"<|im_start|>assistant\n{self.no_think}{ex_out}<|im_end|>\n"
                f"<|im_start|>user\n{user}<|im_end|>\n"
                f"<|im_start|>assistant\n{self.no_think}")
        return self.tok.encode(chat, add_special_tokens=False).tokens

    def generate(self, text: str, style: str, context: str = "", budget: float = BUDGET_SECONDS) -> str | None:
        """Raw model output, or None when it ran out of time."""
        n = len(self.tok.encode(text, add_special_tokens=False).ids)
        max_new = min(48, n + 8) if style == "simple" else int(n * 1.3) + 8
        t0 = time.time()
        ids = []
        for step in self.model.generate_tokens(self._prompt(text, style, context), max_length=max_new,
                                               sampling_topk=1, end_token=self.end):
            if step.is_last or step.token == self.end:
                break
            ids.append(step.token_id)
            if time.time() - t0 > budget:
                self.last_seconds = time.time() - t0
                return None
        self.last_seconds = time.time() - t0
        return self.tok.decode(ids)

    def rewrite(self, text: str, style: str, context: str = "", terms: list[str] = (),
                budget: float = BUDGET_SECONDS) -> str | None:
        """`text` in the chosen style, or None (then show word for word)."""
        if style not in PROMPTS or len(words(text)) < MIN_WORDS:
            return None
        try:
            out = self.generate(text, style, context, budget)
        except Exception:
            log.exception("Caption style rewrite failed")
            return None
        if out is None:
            log.info("Style %s: too slow (%.1fs), word for word shown", style, self.last_seconds)
            return None
        ok = check(text, out, style, terms)
        if ok is None:
            log.info("Style %s: rewrite rejected (%r), word for word shown", style, out[:120])
        return ok
