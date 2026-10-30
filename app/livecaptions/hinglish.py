"""Devanagari Hindi <-> Hinglish (Hindi written in everyday Roman letters).

to_hinglish():  आज के सत्संग में आप सभी का स्वागत है -> Aaj ke satsang mein aap sabhi ka swagat hai
  Standard transliteration gives "aaja ke satsanga mem'", which is not how people
  write Hindi in English letters. This follows common Hinglish spelling: the
  silent inherent "a" (schwa) is dropped (मिलकर -> milkar), frequent words use their
  everyday spelling (में -> mein) and vocabulary terms keep their exact spelling.

to_devanagari(): the reverse, for Hinglish typed/transcribed in Roman letters,
  so the translator (which needs Devanagari) can understand it. Uses a lexicon of
  Hindi words (from the translation model's own vocabulary) keyed by a loose
  Roman spelling, so "hum", "ham", "milkar", "milakar" all find the right word.

is_hinglish(): tells Roman Hinglish apart from English.
"""
from __future__ import annotations

import re
from pathlib import Path

# Frequent words whose everyday spelling rules can't produce.
COMMON = {
    "में": "mein", "मैं": "main", "है": "hai", "हैं": "hain", "हूँ": "hoon", "हूं": "hoon",
    "नहीं": "nahin", "नही": "nahi", "का": "ka", "की": "ki", "के": "ke", "को": "ko", "से": "se",
    "पर": "par", "और": "aur", "या": "ya", "भी": "bhi", "ही": "hi", "तो": "to", "जी": "ji",
    "आप": "aap", "हम": "hum", "तुम": "tum", "यह": "yeh", "ये": "ye", "वह": "woh", "वो": "woh",
    "वे": "ve", "क्या": "kya", "क्यों": "kyon", "क्योंकि": "kyonki", "कैसे": "kaise",
    "कहाँ": "kahan", "कहां": "kahan", "जब": "jab", "तब": "tab", "अब": "ab", "सब": "sab",
    "सभी": "sabhi", "एक": "ek", "था": "tha", "थी": "thi", "थे": "the", "हो": "ho",
    "लिए": "liye", "लिये": "liye", "साथ": "saath", "आज": "aaj", "कल": "kal", "बहुत": "bahut",
    "धन्यवाद": "dhanyavaad", "स्वागत": "swagat", "कृपया": "kripya", "प्रेम": "prem",
    "प्यार": "pyaar", "अपना": "apna", "अपनी": "apni", "अपने": "apne", "हमारा": "hamara",
    "हमारी": "hamari", "हमारे": "hamare", "आपका": "aapka", "आपकी": "aapki", "आपके": "aapke",
    "करें": "karen", "करना": "karna", "करते": "karte", "करता": "karta", "करती": "karti",
    "करेंगे": "karenge", "रहें": "rahen", "रहे": "rahe", "रहा": "raha", "रही": "rahi",
    "चलो": "chalo", "आइए": "aaiye", "आओ": "aao", "मिले": "mile", "सकते": "sakte",
    "भगवान": "Bhagwan", "ईश्वर": "Ishwar", "परमात्मा": "Parmatma", "आशीर्वाद": "aashirwad",
    "विनम्रता": "vinamrata", "ज़रूरी": "zaroori", "जरूरी": "zaroori", "बैठक": "baithak",
    "शामिल": "shamil", "होने": "hone", "होना": "hona", "मन": "man", "दिल": "dil",
    "सच": "sach", "सत्य": "satya", "जीवन": "jeevan", "दुनिया": "duniya", "लोग": "log",
    "हमें": "hamein", "तुम्हें": "tumhein", "उन्हें": "unhein", "चाहिए": "chahiye", "जानना": "jaanna",
    "उन्होंने": "unhone", "किया": "kiya", "गया": "gaya", "गई": "gayi", "दिया": "diya",
    "ज्ञान": "gyan", "प्राप्त": "prapt", "मौजूद": "maujood", "जगह": "jagah", "पहुंचे": "pahunche",
    "पहुँचे": "pahunche", "माता": "Mata", "पिता": "pita", "बाबा": "Baba", "गुरु": "guru",
    "कहा": "kaha", "कहते": "kehte", "बात": "baat", "समय": "samay", "हमेशा": "hamesha",
    "कर": "kar", "करो": "karo", "करके": "karke", "मिलकर": "milkar", "सबको": "sabko",
    "उसे": "use", "इसे": "ise", "उस": "us", "इस": "is", "वाले": "wale", "वाला": "wala",
    "अच्छा": "accha", "अच्छी": "acchi", "अच्छे": "acche", "भाई": "bhai", "बहन": "behen",
    "नमस्ते": "namaste", "शुक्रिया": "shukriya", "लेकिन": "lekin", "ठीक": "theek", "हाँ": "haan",
    "बच्चे": "bacche", "बच्चा": "baccha", "सच्चा": "saccha", "सच्चे": "sacche", "पूरा": "poora",
    "इंसान": "insaan", "ज़िंदगी": "zindagi", "खुशी": "khushi", "शांति": "shanti", "दुख": "dukh",
    "सुख": "sukh", "भक्त": "bhakt", "भक्ति": "bhakti", "श्रद्धा": "shraddha", "विश्वास": "vishwas",
    "मानव": "manav", "मानवता": "manavta", "एकता": "ekta", "परिवार": "parivar", "प्रभु": "Prabhu",
}

# Other common Roman spellings of the same words (Roman -> Devanagari).
COMMON_ROMAN_VARIANTS = {
    "acha": "अच्छा", "achha": "अच्छा", "achchha": "अच्छा", "achhi": "अच्छी", "achhe": "अच्छे",
    "bahen": "बहन", "behan": "बहन", "nahi": "नहीं", "nai": "नहीं", "kyunki": "क्योंकि",
    "kyuki": "क्योंकि", "kyu": "क्यों", "kyun": "क्यों", "thik": "ठीक", "han": "हाँ", "ha": "हाँ",
    "hamesa": "हमेशा", "pyar": "प्यार", "me": "में", "mai": "मैं", "mei": "में", "hu": "हूँ",
    "hun": "हूँ", "ho": "हो", "dhanyawad": "धन्यवाद", "dhanyavad": "धन्यवाद", "shukriyaa": "शुक्रिया",
    "jee": "जी", "yah": "यह", "vah": "वह", "wo": "वो", "vo": "वो", "ye": "ये", "aj": "आज",
}

VOWELS = {  # independent vowels
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ॲ": "e",
}
MATRAS = {
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e",
}
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "फ़": "f", "ड़": "d", "ढ़": "dh", "य़": "y",
}
NUKTA, VIRAMA, ANUSVARA, CHANDRABINDU, VISARGA = "़", "्", "ं", "ँ", "ः"
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
WORD = re.compile(r"[\u0900-\u0963\u0966-\u097F]+")
DEV_CHARS = "\u0900-\u097F"
DEV_LETTERS = "\u0900-\u0963\u0966-\u097F"  # without the danda । ॥


# --------------------------------------------------------------------------
# Devanagari -> Hinglish
# --------------------------------------------------------------------------
def _syllables(word: str):
    """Split into units [consonant cluster, vowel, nasal]; vowel is None for the
    inherent 'a' and '' when a virama ends the cluster."""
    units, i, n = [], 0, len(word)
    while i < n:
        ch = word[i]
        if ch in VOWELS:
            units.append(["", VOWELS[ch], ""])
            i += 1
        elif ch in CONSONANTS or (i + 1 < n and word[i + 1] == NUKTA):
            cons = []
            while i < n:
                c = word[i]
                if i + 1 < n and word[i + 1] == NUKTA:
                    c, i = c + NUKTA, i + 1
                if c not in CONSONANTS:
                    break
                cons.append(c)
                i += 1
                if i < n and word[i] == VIRAMA:  # conjunct: keep collecting
                    i += 1
                    if i < n and (word[i] in CONSONANTS):
                        continue
                    cons.append(VIRAMA)
                break
            vowel = None
            if cons and cons[-1] == VIRAMA:
                cons.pop()
                vowel = ""
            elif i < n and word[i] in MATRAS:
                vowel = MATRAS[word[i]]
                i += 1
            units.append([cons, vowel, ""])
        elif ch in (ANUSVARA, CHANDRABINDU) and units:
            units[-1][2] = "n"
            i += 1
        elif ch == VISARGA and units:
            units[-1][2] += "h"
            i += 1
        else:
            i += 1
    return units


def _cluster(cons) -> str:
    out = []
    for j, c in enumerate(cons):
        r = CONSONANTS[c]
        if c == "व" and j > 0:  # स्व, द्व, त्व -> sw, dw, tw
            r = "w"
        out.append(r)
    return "".join(out)


def romanize_word(word: str) -> str:
    units = _syllables(word)
    if not units:
        return word
    vowels = [u[1] for u in units]
    # Final inherent 'a' is silent: सत्संग -> satsang. It stays after a conjunct
    # ending in य/र/व: धन्य -> dhanya, मित्र -> mitra (but प्राप्त -> prapt).
    last_cons = units[-1][0]
    keeps_a = len(last_cons) > 1 and last_cons[-1] in ("य", "र", "व")
    if len(units) > 1 and vowels[-1] is None and last_cons and not units[-1][2] and not keeps_a:
        vowels[-1] = ""
    # Medial schwa: drop the inherent 'a' of a single consonant when the previous
    # unit has a vowel and the next unit is a consonant with a vowel (sab-ko, mil-kar).
    for k in range(len(units) - 2, 0, -1):
        if (vowels[k] is None and len(units[k][0]) == 1 and not units[k][2]
                and vowels[k - 1] != "" and units[k + 1][0] and vowels[k + 1] != ""):
            vowels[k] = ""
            break  # one deletion per word keeps long words readable
    out = []
    for k, (cons, _, nasal) in enumerate(units):
        v = vowels[k]
        if v is None:
            v = "a"
        if cons:
            out.append(_cluster(cons))
        # Hinglish shortens long vowels at the end of a word (ji, guru, sabhi) and
        # writes 'aa' as 'a' after the first syllable (nirankar, samagam, prapt)
        if k == len(units) - 1:
            v = {"ee": "i", "oo": "u"}.get(v, v)
        if v == "aa" and k > 0 and len(units) > 2:
            v = "a"
        elif v == "aa" and k == len(units) - 1 and len(units) > 1:
            v = "a"
        out.append(v)
        if nasal:
            nxt = units[k + 1][0][0] if k + 1 < len(units) and units[k + 1][0] else ""
            out.append("m" if nxt in ("प", "फ", "ब", "भ", "म") else nasal)
    return "".join(out)


def roman_of(word: str) -> str:
    return COMMON.get(word) or romanize_word(word)


def to_hinglish(text: str, terms: dict[str, str] | None = None) -> str:
    """Convert Devanagari in `text` to Hinglish. `terms` maps Devanagari words or
    phrases to exact Roman spellings (vocabulary), applied first."""
    if terms:
        for dev in sorted(terms, key=len, reverse=True):
            text = re.sub(rf"(?<![{DEV_LETTERS}]){re.escape(dev)}(?![{DEV_LETTERS}])", terms[dev], text)
    out = WORD.sub(lambda m: roman_of(m.group(0)), text).translate(DIGITS)
    out = out.replace("।", ".").replace("॥", ".")
    out = re.sub(r"\s+([.,!?])", r"\1", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    # Respectful "Ji" after a name or title: Sudiksha ji -> Sudiksha Ji
    out = re.sub(r"(\b[A-Z][a-z]+) ji\b", r"\1 Ji", out)
    out = re.sub(r"\b(Ji)( Ji)+\b", r"\1", out)
    out = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out


# --------------------------------------------------------------------------
# Hinglish -> Devanagari
# --------------------------------------------------------------------------
def loose_key(roman: str) -> str:
    """A spelling-insensitive key: hum/ham, milkar/milakar, swagat/svaagat match."""
    w = roman.lower()
    w = re.sub(r"[^a-z]", "", w)
    for a, b in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("w", "v"),
                 ("ph", "f"), ("z", "j"), ("q", "k"), ("ou", "au"), ("ei", "e"), ("ey", "e"),
                 ("chh", "ch"), ("sh", "s"), ("ksh", "ks"), ("x", "ks")):
        w = w.replace(a, b)
    w = re.sub(r"(.)\1+", r"\1", w)          # doubled letters
    w = re.sub(r"(?<=[aeiou])h$", "", w)     # yeh -> ye, vah -> va
    w = re.sub(r"(?<=[bcdfgjklmnprstv])a(?=[bcdfgjklmnprstv][aeiou])", "", w)  # milakar -> milkar
    w = w.replace("y", "i") if len(w) > 2 else w
    return w.replace("u", "a") if w in ("ham", "hum") else w


class HinglishLexicon:
    """Roman spelling -> best Devanagari word (exact spelling first, then loose)."""

    def __init__(self, lexicon_json: Path | None = None, extra: dict[str, str] | None = None):
        import json

        self.exact: dict[str, str] = {}
        self.loose: dict[str, str] = {}
        if lexicon_json and Path(lexicon_json).exists():
            data = json.loads(Path(lexicon_json).read_text(encoding="utf-8"))
            self.exact, self.loose = data.get("exact", {}), data.get("loose", {})
        for dev, roman in COMMON.items():  # everyday spellings always win
            self.exact[roman.lower()] = dev
            self.loose[loose_key(roman)] = dev
        for roman, dev in COMMON_ROMAN_VARIANTS.items():
            self.exact[roman] = dev
            self.loose.setdefault(loose_key(roman), dev)
        for roman, dev in (extra or {}).items():
            self.exact[roman.lower()] = dev
            self.loose[loose_key(roman)] = dev

    def word(self, w: str) -> str:
        lw = w.lower()
        return self.exact.get(lw) or self.loose.get(loose_key(lw)) or roman_word_to_devanagari(lw)


# Rule-based fallback for words not in the lexicon.
_R_CONS = [("chh", "छ"), ("ksh", "क्ष"), ("shr", "श्र"), ("kh", "ख"), ("gh", "घ"), ("ch", "च"),
           ("jh", "झ"), ("th", "थ"), ("dh", "ध"), ("ph", "फ"), ("bh", "भ"), ("sh", "श"),
           ("k", "क"), ("g", "ग"), ("j", "ज"), ("t", "त"), ("d", "द"), ("n", "न"), ("p", "प"),
           ("f", "फ़"), ("b", "ब"), ("m", "म"), ("y", "य"), ("r", "र"), ("l", "ल"), ("v", "व"),
           ("w", "व"), ("s", "स"), ("h", "ह"), ("z", "ज़"), ("q", "क़"), ("c", "क"), ("x", "क्स")]
_R_VOW = [("aa", "आ", "ा"), ("ai", "ऐ", "ै"), ("au", "औ", "ौ"), ("ee", "ई", "ी"), ("oo", "ऊ", "ू"),
          ("a", "अ", ""), ("i", "इ", "ि"), ("u", "उ", "ु"), ("e", "ए", "े"), ("o", "ओ", "ो")]
_CONJ_START = ("pr", "kr", "tr", "br", "gr", "dr", "sw", "sv", "st", "sp", "sm", "sn", "gy", "ky",
               "py", "by", "dhy", "ty", "kl", "pl", "bl", "fl", "gl", "sk")


def roman_word_to_devanagari(w: str) -> str:
    out, i, n, prev_cons = [], 0, len(w), False
    while i < n:
        for r, dev, matra in _R_VOW:
            if w.startswith(r, i):
                if prev_cons:
                    if i + len(r) == n and r == "i":
                        matra = "ी"  # final -i is long: sabhi, ji
                    out.append(matra)
                else:
                    out.append(dev)
                i += len(r)
                prev_cons = False
                break
        else:
            for r, dev in _R_CONS:
                if w.startswith(r, i):
                    # n before a consonant (after a vowel) is a nasal: sundar -> सुंदर
                    nxt = w[i + 1:i + 2]
                    if r == "n" and out and not prev_cons and nxt and nxt not in "aeiouy":
                        out.append("ं")
                    else:
                        if prev_cons and out and w[max(0, i - 3):i + len(r)].startswith(_CONJ_START) \
                                and len(out) <= 2:
                            out.append(VIRAMA)  # word-initial conjunct: prem -> प्रेम
                        out.append(dev)
                        prev_cons = True
                    i += len(r)
                    break
            else:
                out.append(w[i])
                i += 1
                prev_cons = False
    return "".join(out)


# Words that are clearly Hindi in Roman letters (and not common English words).
HINGLISH_MARKERS = (
    "hai hain mein ka ki ke ko se aur hum ham aap kya nahi nahin bhi yeh woh kar karo karna "
    "karenge karte raha rahe rahi tha thi hoga sab sabhi bahut ji hamesha apna apni apne hamara "
    "hamare hamein tumhe unhe chahiye kyunki kyonki lekin magar abhi kaise kahan jab tab "
    "accha acha theek thik haan dhanyavaad dhanyawad shukriya kripya milkar saath liye wala wale "
    "gaya gayi diya kiya kaha baat samay log jeevan duniya pyaar prem"
).split()


def is_hinglish(text: str, english_words: set[str]) -> bool:
    words = re.findall(r"[A-Za-z']+", text.lower())
    if len(words) < 2:
        return False
    marker_set = set(HINGLISH_MARKERS)
    markers = sum(1 for w in words if w in marker_set)
    english = sum(1 for w in words if w in english_words and w not in marker_set)
    return markers >= 2 and markers >= 0.25 * len(words) and english < 0.6 * len(words)


def to_devanagari(text: str, lexicon: HinglishLexicon, english_words: set[str] | None = None,
                  terms: dict[str, str] | None = None) -> str:
    """Hinglish -> Devanagari, word by word. Vocabulary `terms` (roman -> Devanagari)
    come first; other English words stay in Roman letters (the translator handles
    mixed text well)."""
    english_words = english_words or set()
    terms = {k.lower(): v for k, v in (terms or {}).items()}
    marker_set = set(HINGLISH_MARKERS)

    def repl(m: re.Match) -> str:
        w = m.group(0)
        lw = w.lower()
        if lw in terms:
            return terms[lw]
        if lw in english_words and lw not in marker_set:
            return w
        return lexicon.word(w)

    out = re.sub(r"[A-Za-z']+", repl, text)
    return re.sub(r"(?<=[" + DEV_CHARS + r"])\s*\.\s*$", "।", out)


if __name__ == "__main__":
    for s in ["आज के सत्संग में आप सभी का स्वागत है।",
              "आओ हम सब प्रेम और विनम्रता के साथ सेवा करें",
              "हम सब मिलकर सिमरन करेंगे, क्योंकि यह ज़रूरी है।",
              "समागम में लाखों श्रद्धालु पहुंचे और उन्होंने ज्ञान प्राप्त किया।"]:
        print(to_hinglish(s))
