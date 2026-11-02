"""Caption styles (meaning.py): every fallback rule, with a fake model (no download).

  cd app && ../.venv/bin/python ../tests/test_meaning.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from livecaptions import meaning  # noqa: E402

SRC = "So, so we all should do the sewa with love, and then Nirankar is happy with us."


class Fake(meaning.Rewriter):
    """Rewriter without a model: `generate` returns a fixed answer (or sleeps)."""

    def __init__(self, answer: str | None, delay: float = 0.0) -> None:
        self.answer, self.delay, self.last_seconds, self.calls = answer, delay, 0.0, 0

    def generate(self, text, style, context="", budget=meaning.BUDGET_SECONDS):
        self.calls += 1
        if self.delay > budget:
            self.last_seconds = budget
            return None
        self.last_seconds = self.delay
        return self.answer


fails = 0


def expect(name: str, got, want) -> None:
    global fails
    ok = got == want
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f": got {got!r}, want {want!r}"))


good = "We should all do sewa with love, and then Nirankar is pleased with us."
terms = ["sewa", "Nirankar"]
expect("good rewrite is shown", Fake(good).rewrite(SRC, "natural", terms=terms), good)
expect("quotes around it are removed", Fake(f'"{good}"').rewrite(SRC, "natural", terms=terms), good)
expect("empty answer -> word for word", Fake("").rewrite(SRC, "natural", terms=terms), None)
expect("'Here is' -> word for word", Fake("Here is the rewrite: " + good).rewrite(SRC, "natural", terms=terms), None)
expect("'Sure' -> word for word", Fake("Sure! " + good).rewrite(SRC, "simple", terms=terms), None)
expect("too long -> word for word", Fake(good + " " + good).rewrite(SRC, "natural", terms=terms), None)
expect("simple over ~20 words -> word for word",
       Fake(" ".join(["word"] * 26)).rewrite(" ".join(["said"] * 40), "simple"), None)
expect("dropped term -> word for word",
       Fake("We should all serve with love, and God is pleased.").rewrite(SRC, "natural", terms=terms), None)
expect("other script -> word for word", Fake("हम सबको प्यार से sewa करनी चाहिए Nirankar").rewrite(
    SRC, "natural", terms=terms), None)
expect("two lines -> word for word", Fake(good + "\nExplanation: ...").rewrite(SRC, "natural", terms=terms), None)
expect("changed number -> word for word",
       Fake("Over 200 people helped.").rewrite("More than 2000 volunteers helped for three days.", "simple"), None)
slow = Fake(good, delay=5)
expect("invented idea -> word for word", Fake("Then you give them a choice between the truth and the illusion.").rewrite(
    "Well, yes that's right. So then all right, so you give them a choice.", "natural"), None)
expect("changed meaning -> word for word", Fake("You need to make the pizza bigger.").rewrite(
    "The pizza is not going to be this small, so you have to show it.", "simple"), None)
expect("too slow -> word for word", slow.rewrite(SRC, "natural", terms=terms, budget=1.5), None)
short = Fake("Thanks a lot.")
expect("3 words or fewer: not rewritten", short.rewrite("Dhan Nirankar Ji", "simple"), None)
expect("short line never reaches the model", short.calls, 0)
expect("word for word style: not rewritten", Fake(good).rewrite(SRC, "word"), None)
expect("model error -> word for word",
       type("Boom", (Fake,), {"generate": lambda *a, **k: 1 / 0})(good).rewrite(SRC, "natural"), None)

# The pipeline: style off / on / late, and the word-for-word line kept for bilingual.txt
from livecaptions import translator  # noqa: E402

p = translator.CaptionPipeline(None)
p.mode = "hi-en"
line = "We should all do sewa with love and Nirankar is happy with us."
p.style = "word"
p.rewriter = Fake("We should all serve with love, sewa Nirankar.")
expect("Word for word ignores the model", p.process(line, "speech"), p.vocab.apply_english(line))
p.style = "simple"
p.rewriter = Fake("Do sewa with love and Nirankar is pleased.")
out = p.process(line, "speech")
expect("Simple caption shown (with vocabulary)", out, p.vocab.apply_english("Do sewa with love and Nirankar is pleased."))
expect("word-for-word kept for bilingual.txt", p.last.get("word", "").startswith("word for word: "), True)
p.rewriter = Fake("x", delay=9)
expect("late rewrite: word for word shown", p.process(line, "speech"), p.vocab.apply_english(line))
expect("slow note shown in the window", p.style_note, "using word for word (slow computer)")
p.rewriter = Fake("Do sewa with love and Nirankar is pleased.")
p.restyle_now = False
expect("newer speech waiting: rewrite skipped", p.process(line, "speech"), p.vocab.apply_english(line))
p.restyle_now = True
biz = "So then all right, you give them a choice of two websites."
p.rewriter = Fake("You give them a choice of two websites with sewa.")
expect("vocabulary term that wasn't said -> word for word", p.process(biz, "speech"), biz)

print("\nALL STYLE CHECKS PASS" if not fails else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
