"""Builds vocabulary/hinglish_lexicon.json: loose Roman spelling -> Devanagari word.

Sources: the NLLB translation model's vocabulary (frequent Hindi words) and
AI4Bharat Aksharantar (1.3M real Roman/Devanagari word pairs).
Run once: python build_hinglish_lexicon.py /path/to/aksharantar/hin_*.json
"""
import collections
import json
import re
import sys
from pathlib import Path

import sentencepiece as spm

import hinglish as H

HERE = Path(__file__).resolve().parent
SP = Path.home() / ".captiocr/models/nllb-200-1.3b/sentencepiece.bpe.model"
OUT = HERE / "vocabulary" / "hinglish_lexicon.json"

sp = spm.SentencePieceProcessor(model_file=str(SP))
score = {}
for i in range(sp.get_piece_size()):
    p = sp.id_to_piece(i)
    if p.startswith("▁") and re.fullmatch(r"▁[\u0900-\u0963\u0966-\u097F]{2,}", p):
        score[p[1:]] = sp.get_score(i)

spell = collections.defaultdict(collections.Counter)   # native -> roman spellings
curated = collections.defaultdict(collections.Counter)  # hand-checked sources only
CURATED = {"Dakshina", "AK-Freq", "Existing"}
for f in sys.argv[1:]:
    for line in open(f, encoding="utf-8"):
        d = json.loads(line)
        r, n = d["english word"].strip().lower(), d["native word"].strip()
        if r.isalpha() and n and not re.search(r"(.)\1\1", n):
            spell[n][r] += 1
            if d.get("source") in CURATED:
                curated[n][r] += 1

best: dict[str, tuple] = {}    # loose key -> (priority, native)
exact: dict[str, tuple] = {}   # exact roman spelling -> (priority, native)


def add(key, native, prio, roman=None):
    if key and (key not in best or prio > best[key][0]):
        best[key] = (prio, native)
    if roman and (roman not in exact or prio > exact[roman][0]):
        exact[roman] = (prio, native)


for n, s in score.items():
    add(H.loose_key(H.roman_of(n)), n, (3, s), H.roman_of(n).lower())                  # our own spelling of a frequent word
    total = sum(spell[n].values()) or 1
    for r, c in spell.get(n, {}).items():
        if c >= 2 or c / total >= 0.3:                         # spelling people actually use
            add(H.loose_key(r), n, (2, c, s), r)
for n, sp_counts in spell.items():                             # rarer words, well attested
    if n in score:
        continue
    for r, c in sp_counts.items():
        if c >= 2:
            add(H.loose_key(r), n, (1, c), r)
for n, sp_counts in curated.items():                           # curated pairs, any count
    for r, c in sp_counts.items():
        add(H.loose_key(r), n, (0, n in score, score.get(n, -1e9), c, -len(n)), r)

data = {"exact": {k: v[1] for k, v in exact.items()}, "loose": {k: v[1] for k, v in best.items()}}
OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(exact)} exact + {len(best)} loose spellings -> {OUT} ({OUT.stat().st_size // 1024} KB)")
