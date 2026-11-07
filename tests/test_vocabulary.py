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
      f"ASR context {len(v.asr_context())} chars (vocabulary {len(v.asr_vocab_list())})")

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

# Code-switched Hindi-English (Qwen3-ASR decodes with language=None)
print("\nHindi + English in one sentence:")
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(f"   {'PASS' if ok else 'FAIL'}  {name}{'  | ' + detail if detail else ''}")


ctx = v.asr_context()
check("ASR context: Hinglish instructions + vocabulary, within budget",
      ctx.startswith("Bilingual Hindi-English") and "CRITICAL HOTWORDS" in ctx and "Nirankar" in ctx
      and len(v.asr_vocab_list()) <= 700, f"{len(ctx)} chars")
check("context echo dropped (example sentence, instructions)",
      v.is_context_echo(t.ASR_EXAMPLE) and v.is_context_echo("Speakers switch between English and Hindi mid-sentence")
      and not v.is_context_echo("मेरा phone नहीं मिल रहा, can you please check करो"))
mixed = "so basically कल हम सब office में meeting करेंगे because deadline next week है."
check("mixed line detected", t.detect_language(mixed) == "mixed")
for mode, want in (("hi-en", "meet"), ("en-hinglish", "kal hum sab"), ("en-hi", "कल हम सब")):
    p.mode = mode
    out = p.process(mixed, "speech") or ""
    check(f"mixed line -> {mode} caption", want in out.lower() and "office" in out.lower(), out)
for heard, want in (("सीमरन", "सिमरन"), ("समागन", "समागम"), ("simrun", "simran"), ("nirankaar", "Nirankar"),
                    ("meeting", "meeting"), ("office", "office"), ("कल", "कल")):
    got = v.snap_terms(heard)
    check(f"snap_terms {heard} -> {want}", got == want, got)
check("misheard Hindi in a mixed line: coach -> कुछ", t.fix_confusions("हम coach नहीं कर सकते") == "हम कुछ नहीं कर सकते")
check("plain English untouched", t.fix_confusions("the coach said hi") == "the coach said hi")
p.mode = "hi-en"
out = p.process("आज हम सब सीमरन करेंगे and then we will do sewa.", "speech") or ""
check("vocabulary kept through translation", "simran" in out.lower() and "sewa" in out.lower(), out)
mixed_fail = checks.count(False)

total = sum(len(f) for f in fails.values())
print(f"\n{'HINGLISH CHECKS PASS' if not mixed_fail else f'{mixed_fail} Hinglish checks failed'}")
print(f"\n{'ALL TERMS EXACT' if not total else f'{total} misses'}")
