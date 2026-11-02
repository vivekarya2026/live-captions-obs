"""Speed + quality test for the caption-style models (Natural / Simple).

One-off helper, not part of the app. Converts nothing itself: give it folders of
CTranslate2 int8 models (ct2-transformers-converter --quantization int8 ...).

  cd app && ../.venv/bin/python ../tests/bench_meaning.py /tmp/meaning/Qwen2.5-0.5B-Instruct ...

Sentences: real word-for-word captions from ~/.livecaptions/transcripts (the
longer ones), plus satsang lines. Prints seconds per sentence and every output.
"""
from __future__ import annotations

import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from livecaptions import meaning  # noqa: E402

TERMS = ["sewa", "simran", "satsang", "Nirankar", "Satguru", "sangat", "Samagam", "Maya", "Gyan"]
SATSANG = [
    "So today we all have come to the satsang, and in the satsang we, we learn that sewa should be done with the love and not with the ego.",
    "Satguru has given us the Gyan, and with the Gyan we can see the Nirankar in every moment, in every place, in everyone.",
    "When the mind is, is caught in the Maya, then it does not see the truth, and then it becomes troubled again and again.",
    "If we do simran while walking, while sitting, while working, then our life becomes easy and full of peace.",
    "The sangat is like a family, and in the family nobody is big or small, all are equal in front of the Nirankar.",
    "Last year in the Samagam more than 2000 volunteers did sewa for three days and nights without rest.",
    "We should not judge anyone, because the same Nirankar lives in everyone, and that is what Satguru is teaching us.",
    "My, my mother used to say that whatever happens, happens by the will of God, so do not worry, just keep doing your work.",
    "Sometimes we say we have no time for satsang, but we have time for the phone, for TV, for everything else.",
    "Brothers and sisters, the real meaning of devotion is not only to sing, it is to live with love and humility every day.",
]


def real_sentences(limit: int) -> list[str]:
    out = []
    for f in sorted((Path.home() / ".livecaptions" / "transcripts").glob("*.txt"), reverse=True):
        for line in f.read_text(encoding="utf-8").splitlines():
            if "-> " not in line:
                continue
            s = re.sub(r"\s*\([^)]*\)", "", line.split("-> ", 1)[1]).strip()
            n = len(s.split())
            if 10 <= n <= 45 and re.match(r"[A-Z]", s) and s.isascii() and s not in out \
                    and "included in the list" not in s and not re.search(r"\b(hai|karne|aap|main)\b", s):
                out.append(s)
            if len(out) >= limit:
                return out
    return out


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:]]
    sentences = real_sentences(20) + SATSANG
    report = ["# Caption style speed test\n", f"{len(sentences)} sentences\n"]
    results = {}
    for d in dirs:
        t0 = time.time()
        r = meaning.Rewriter(d)
        load = time.time() - t0
        r.generate("Warm up the model with one short sentence please.", "simple", budget=30)
        times = {"natural": [], "simple": []}
        rejected = {"natural": 0, "simple": 0}
        outs = []
        for s in sentences:
            row = [s]
            for style in ("natural", "simple"):
                out = r.generate(s, style, budget=30)
                times[style].append(r.last_seconds)
                terms = [t for t in TERMS if t.lower() in s.lower()]
                ok = meaning.check(s, out or "", style, terms)
                rejected[style] += ok is None
                row.append(f"{out}  ({r.last_seconds:.2f}s{'' if ok else ', REJECTED'})")
            outs.append(row)
            print(f"[{d.name}] {s}\n   N: {row[1]}\n   S: {row[2]}", flush=True)
        size = sum(f.stat().st_size for f in d.iterdir()) / 1e9
        results[d.name] = (load, size, times, rejected)
        report.append(f"\n## {d.name}\n\nload {load:.1f}s, size {size:.2f} GB\n")
        for style in ("natural", "simple"):
            ts = times[style]
            report.append(f"- {style}: median {statistics.median(ts):.2f}s, max {max(ts):.2f}s, "
                          f"over 1.5s: {sum(t > 1.5 for t in ts)}/{len(ts)}, rejected by checks: {rejected[style]}\n")
        for s, n, si in outs:
            report.append(f"\n- **Word for word:** {s}\n  - **Natural:** {n}\n  - **Simple:** {si}\n")
        del r
    out = Path("/tmp/meaning/report.md")
    out.write_text("".join(report), encoding="utf-8")
    print("\n".join(l for l in "".join(report).splitlines() if l.startswith(("##", "- natural", "- simple", "load"))))
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
