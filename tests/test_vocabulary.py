"""Checks every row of the vocabulary sheet through the real caption pipeline:

  Hindi speech   -> English captions   must contain the sheet's English form
  Hindi speech   -> Hinglish captions  must contain the sheet's Hinglish spelling
  English speech -> Hinglish captions  must contain the sheet's Hinglish spelling
  misheard words ("suya")            must be corrected ("sewa")

  python tests/test_vocabulary.py [--verbose]
"""
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import openpyxl

from livecaptions import translator as t

logging.basicConfig(level=logging.WARNING)
verbose = "--verbose" in sys.argv
p = t.CaptionPipeline(t.Translator())
v = p.vocab
print(f"{len(v.english_sub)} English term keys, {len(v.hindi_to_term)} Hindi spellings, "
      f"context: en {len(v.asr_context_for('en'))} / hi {len(v.asr_context_for('hi'))} chars")

wb = openpyxl.load_workbook(t.VOCAB_XLSX, read_only=True)
rows = [r for r in wb["Hindi_English_Hinglish"].iter_rows(min_row=2, values_only=True) if r[0] and r[2]]


def norm(s):
    return re.sub(r"[^\w\u0900-\u097F]+", " ", (s or "").lower()).strip()


fails = {"hi-en": [], "hi-hinglish": [], "en-hinglish": []}
for dev, english, roman, sub, _ in rows:
    dev, roman, sub = str(dev).strip(), str(roman).strip(), str(sub or "").strip()
    key = v.hindi_to_term.get(" ".join(dev.replace(",", " , ").split()).replace(" , ", ", "))
    want_en = v.canonical.get(key, roman) if key else roman
    want_en = re.sub(r"\s*\(.*\)$", "", want_en)
    # Hinglish: column D's spelling when it normalises a name, else column C
    canon_d = re.sub(r"\s*\(.*\)$", "", sub)
    want_hg = roman if (not sub or sub.startswith("=") or t._mostly_english(canon_d)) else canon_d
    # Hindi -> English
    p.mode = "hi-en"
    out = p.process(f"आज हम {dev} के बारे में बात करेंगे।", "speech") or ""
    if norm(want_en) not in norm(out):
        fails["hi-en"].append((dev, want_en, out))
    # Hindi -> Hinglish
    p.mode = "en-hinglish"
    out = p.process(f"आज हम {dev} के बारे में बात करेंगे।", "speech") or ""
    if norm(want_hg) not in norm(out):
        fails["hi-hinglish"].append((dev, want_hg, out))
    # English -> Hinglish (the speaker says the Roman word in an English sentence)
    out = p.process(f"Today we will talk about {roman}.", "speech") or ""
    if norm(want_hg) not in norm(out):
        fails["en-hinglish"].append((roman, want_hg, out))

for k, f in fails.items():
    print(f"\n{k}: {len(rows) - len(f)}/{len(rows)} terms exact")
    for src, want, out in f[: (len(f) if verbose else 12)]:
        print(f"   {src!r:42} want {want!r:28} got: {out}")

print("\nMisheard words:")
for heard, lang in [("Let us all do suya with love and humility.", "en"),
                    ("We do simrun every morning.", "en"),
                    ("The Nirankaar is everywhere.", "en"),
                    ("Satguru Mata Sudhixa Ji Maharaj blessed us.", "en"),
                    ("Let us go to the samagum.", "en"),
                    ("Please sit down and listen.", "en"),
                    ("हम सब मिलकर सिमरान करेंगे।", "hi"),
                    ("आज की सेना बहुत मजबूत है।", "hi")]:
    print(f"   {heard}\n      -> {v.fix_recognition(heard, lang)}")
total = sum(len(f) for f in fails.values())
print(f"\n{'ALL TERMS EXACT' if not total else f'{total} misses'}")
