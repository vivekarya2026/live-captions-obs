"""Song mode: read an upload (any format) and cut it into songs and lines.

Every format becomes one of two shapes, then the same rules apply:
- paragraphs (Word, PDF, text, pasted): a title starts a song; a line in a
  different script or language right under a lyric line is its translation;
- rows (Excel, CSV, tables in Word): columns Title / Line / English / Hindi
  (any order, English or Hindi names), or without headers: line, translation.

Nothing here saves anything: the result goes to the Check page first.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .hinglish import HINGLISH_MARKERS, is_hinglish, to_hinglish

KINDS = (".docx", ".pdf", ".xlsx", ".xlsm", ".csv", ".txt", ".text", ".md")
DEV = re.compile(r"[\u0900-\u097F]")
REPEAT = re.compile(r"\s*(\(\s*[x×]?\s*\d\s*[x×]?\s*\)|\b[x×]\s*\d\b|\b\d\s*[x×]\b|[|।॥]{1,2}\s*[\d०-९]+\s*[|।॥]{1,2}|[|।॥]+)\s*$")
NUMBERED = re.compile(r"^\s*(\d{1,3}|[०-९]{1,3})\s*[.)]\s+")
LABEL = re.compile(r"^\s*(chorus|refrain|antara|asthayi|sthayi|टेक|अंतरा|स्थायी)\s*[:\-]\s*", re.I)
EN_PREFIX = re.compile(r"^\s*(english|eng|translation|meaning)\s*[:\-]\s*", re.I)
HI_PREFIX = re.compile(r"^\s*(hindi|हिंदी|हिन्दी|अर्थ|भावार्थ)\s*[:\-]\s*", re.I)
TITLE_PREFIX = re.compile(r"^\s*(#+\s*|(title|song|bhajan|shabad|गीत|भजन|शब्द)\s*[:\-]\s*)", re.I)
PUNJABI = {"da", "di", "de", "vich", "nal", "naal", "hun", "tusi", "tusin", "sanu", "mainu", "tainu",
           "hoya", "hoyi", "rahya", "karda", "kardi", "kade", "kithe", "ethe", "othe", "hor", "rabb",
           "jeha", "jehi", "vekh", "karan", "vele", "gavan", "nihal", "bina"}
HEADERS = {
    "title": ("title", "song", "song name", "name", "bhajan", "shabad", "गीत", "भजन", "शीर्षक", "नाम"),
    "line": ("line", "lyric", "lyrics", "original", "text", "बोल", "पंक्ति", "लाइन"),
    "en": ("english", "translation", "english translation", "meaning", "अंग्रेज़ी", "अंग्रेजी", "इंग्लिश"),
    "hi": ("hindi", "hindi translation", "हिंदी", "हिन्दी", "हिंदी अनुवाद"),
    "language": ("language", "lang", "भाषा"),
}


class ReadError(Exception):
    """A message for the person, in plain words."""


# ---- readers: file -> paragraphs or rows ------------------------------------
def read_file(path: Path) -> list[tuple]:
    """[('p', text, is_title) | ('row', [cells]) | ('sheet', name)]"""
    kind = path.suffix.lower()
    if kind not in KINDS:
        hint = " Save it as .docx first." if kind in (".doc", ".rtf", ".pages", ".odt") else ""
        raise ReadError(f"Can't read {path.name}: use Word (.docx), PDF, Excel, CSV or text files.{hint}")
    try:
        if kind == ".docx":
            return _docx(path)
        if kind == ".pdf":
            return _pdf(path)
        if kind in (".xlsx", ".xlsm"):
            return _xlsx(path)
        if kind == ".csv":
            return _csv(path.read_bytes())
        return text_items(_decode(path.read_bytes()))
    except ReadError:
        raise
    except FileNotFoundError:
        raise ReadError(f"Couldn't find {path.name}. Was it moved or deleted?")
    except Exception as e:
        raise ReadError(f"Couldn't read {path.name} ({e.__class__.__name__}). Is it open in another app?") from e


def _decode(b: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="ignore")


def text_items(text: str) -> list[tuple]:
    out = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        t = raw.strip()
        m = TITLE_PREFIX.match(t)
        if m and t[m.end():].strip():
            out.append(("p", t[m.end():].strip(), True))
        else:
            out.append(("p", t, False))
    return out


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx(path: Path) -> list[tuple]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    out: list[tuple] = []
    for el in list(body) if body is not None else []:
        if el.tag == f"{W}p":
            out.extend(_docx_paragraph(el))
        elif el.tag == f"{W}tbl":
            for tr in el.iter(f"{W}tr"):
                cells = ["".join(t.text or "" for t in tc.iter(f"{W}t")).strip() for tc in tr.iter(f"{W}tc")]
                out.append(("row", cells))
            out.append(("row", []))
    return out


def _docx_paragraph(p) -> list[tuple]:
    style = p.find(f"{W}pPr/{W}pStyle")
    style = (style.get(f"{W}val") or "") if style is not None else ""
    runs, bold_all, parts = [], True, [""]
    for r in p.iter(f"{W}r"):
        txt = "".join(t.text or "" for t in r.iter(f"{W}t"))
        if r.find(f"{W}br") is not None or r.find(f"{W}cr") is not None:
            parts.append("")              # a line break inside one paragraph
        parts[-1] += txt
        if txt.strip():
            b = r.find(f"{W}rPr/{W}b")
            runs.append(txt)
            bold_all &= b is not None and b.get(f"{W}val") not in ("0", "false")
    text = " ".join(" ".join(parts).split())
    is_title = bool(text) and (bool(re.search(r"heading|title", style, re.I)) or (bold_all and bool(runs)))
    if is_title:
        return [("p", text, True)]
    lines = [("p", " ".join(x.split()), False) for x in parts]
    return lines if any(t for _, t, _ in lines) else [("p", "", False)]


def _pdf(path: Path) -> list[tuple]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ReadError("PDF files need an update of Live Captions. For now, copy the text and use Paste lyrics.")
    text = "\n\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    if not DEV.search(text) and not re.search(r"[A-Za-z]{3}", text):
        raise ReadError(f"Couldn't find any text in {path.name}. If it's a scanned PDF, "
                        "copy the text into Paste lyrics.")
    return text_items(text)


def _xlsx(path: Path) -> list[tuple]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out: list[tuple] = []
    for ws in wb.worksheets:
        out.append(("sheet", ws.title))
        for row in ws.iter_rows(values_only=True):
            out.append(("row", ["" if v is None else str(v).strip() for v in row]))
        out.append(("row", []))
    return out


def _csv(b: bytes) -> list[tuple]:
    text = _decode(b)
    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [("row", [c.strip() for c in r]) for r in csv.reader(io.StringIO(text), dialect)]


# ---- words ------------------------------------------------------------------
def _english_words() -> set[str]:
    try:
        from .translator import ENGLISH_WORDS
        return ENGLISH_WORDS
    except Exception:
        return set()


def kind_of(text: str, english: set[str]) -> str:
    """'dev' (Devanagari), 'en' (English) or 'roman' (Hindi/Punjabi in Roman letters)."""
    if DEV.search(text):
        return "dev"
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return "en"
    if english:
        marks = set(HINGLISH_MARKERS) | PUNJABI
        foreign = sum(1 for w in words if w in marks or w not in english)
        return "roman" if is_hinglish(text, english) or foreign >= 0.4 * len(words) else "en"
    # no dictionary (tests): a small fallback
    common = {"the", "and", "you", "your", "in", "of", "to", "my", "is", "we", "our", "all", "are",
              "with", "every", "here", "o", "a", "i", "me", "it", "on", "for", "love", "heart", "light"}
    return "en" if sum(w in common for w in words) >= max(1, len(words) // 3) else "roman"


def clean_line(t: str) -> str:
    t = LABEL.sub("", NUMBERED.sub("", t))
    for _ in range(2):
        t = REPEAT.sub("", t)
    return " ".join(t.split()).strip(" ,;-–—")


def guess_language(lines: list[str], english: set[str]) -> str:
    kinds = [kind_of(t, english) for t in lines[:8]]
    if kinds and kinds.count("en") > len(kinds) / 2:
        return "en"
    words = []
    for t in lines:
        words += re.findall(r"[a-z]+", (to_hinglish(t) if DEV.search(t) else t).lower())
    hits = sum(w in PUNJABI for w in words)
    return "pa" if words and hits >= 2 and hits / len(words) >= 0.06 else "hi"


# ---- paragraphs -> songs ----------------------------------------------------------
def _songs_from_paragraphs(items: list[tuple], english: set[str]) -> list[dict]:
    # Blocks of lines between blank lines; a title, or 2+ blank lines, starts a new song.
    songs: list[dict] = []
    cur: dict | None = None
    blanks = 2
    block: list[str] = []

    def new(title: str | None):
        nonlocal cur
        cur = {"title": title, "blocks": []}
        songs.append(cur)

    def flush():
        nonlocal block
        if block:
            if cur is None:
                new(None)
            cur["blocks"].append(block)
        block = []

    for it in items:
        _, text, is_title = it
        if not text:
            flush()
            blanks += 1
            continue
        if is_title:
            flush()
            new(text)
        else:
            if blanks >= 2 and not block and cur is not None and cur["blocks"]:
                new(None)                       # two blank lines: next song
            block.append(text)
        blanks = 0
    flush()

    out = []
    for s in songs:
        blocks = [b for b in s["blocks"] if b]
        title = s["title"]
        # A short one-line block at the top, with lyrics after it, is the title.
        if title is None and len(blocks) > 1 and len(blocks[0]) == 1 and len(blocks[0][0]) <= 60:
            title = blocks.pop(0)[0]
        song = _pair_lines([ln for b in blocks for ln in b], english)
        ls = song["lines"]
        # Title typed right above the lyrics: the only line without a translation.
        if title is None and len(ls) > 2 and not ls[0]["translations"] and len(ls[0]["text"]) <= 60 \
                and sum(1 for x in ls[1:] if x["translations"]) >= 0.8 * (len(ls) - 1):
            title = ls.pop(0)["text"]
            song["language"] = guess_language([x["text"] for x in ls], english)
        if ls:
            song["title"], song["title_guessed"] = (title, False) if title else (song["lines"][0]["text"][:60], True)
            out.append(song)
    return out


def _pair_lines(raw: list[str], english: set[str]) -> dict:
    items = []
    for t in raw:
        explicit = None
        if EN_PREFIX.match(t):
            explicit, t = "en", EN_PREFIX.sub("", t)
        elif HI_PREFIX.match(t):
            explicit, t = "hi", HI_PREFIX.sub("", t)
        paren = t.startswith("(") and t.endswith(")") and len(t) > 4
        t = clean_line(t[1:-1] if paren else t)
        if t:
            items.append((t, explicit, paren, kind_of(t, english)))
    plain = [k for _, e, p, k in items if not e and not p]
    kinds = set(plain)
    if "roman" in kinds and "en" in kinds:
        lyric_kind = "roman"              # Hindi/Punjabi in Roman letters, English under it
    else:                                 # the first line that has a different line under it
        lyric_kind = next((plain[i] for i in range(len(plain) - 1) if plain[i] != plain[i + 1]),
                          plain[0] if plain else "dev")
    lines: list[dict] = []
    for t, explicit, paren, k in items:
        last = lines[-1] if lines else None
        if last is not None and (explicit or paren or k != lyric_kind):
            key = explicit or ("hi" if k in ("dev", "roman") else "en")
            if key not in last["translations"]:
                last["translations"][key] = t
                continue
        lines.append({"text": t, "translations": {}})
    return {"lines": lines, "language": guess_language([x["text"] for x in lines], english)}


# ---- rows -> songs -------------------------------------------------------------------
def _header_map(cells: list[str]) -> dict[str, int] | None:
    found = {}
    for i, c in enumerate(cells):
        name = " ".join(c.lower().split())
        for field, names in HEADERS.items():
            if name in names and field not in found:
                found[field] = i
    return found if "line" in found or ("title" in found and len(found) >= 2) else None


def _songs_from_rows(items: list[tuple], english: set[str]) -> list[dict]:
    out: list[dict] = []
    head: dict[str, int] | None = None
    sheet = ""
    cur: dict | None = None
    first_row = True

    def cell(row, key):
        i = head.get(key) if head else None
        return row[i].strip() if i is not None and i < len(row) and row[i] else ""

    def start(title: str | None, language: str = ""):
        nonlocal cur
        cur = {"title": title, "rows": [], "language": language, "sheet": sheet}
        out.append(cur)

    for it in items:
        if it[0] == "sheet":
            sheet, head, cur, first_row = it[1], None, None, True
            continue
        row = [c for c in it[1]]
        if not any(row):
            if head is None or "title" not in head:
                cur = None                       # blank row: next song
            continue
        if first_row:
            first_row = False
            h = _header_map(row)
            if h:
                head = h
                continue
        if head:
            title = cell(row, "title")
            line = cell(row, "line")
            if title and (cur is None or title != cur["title"]):
                start(title, cell(row, "language"))
            if not line:
                continue
            if cur is None:
                start(None)
            cur["rows"].append((line, {k: cell(row, k) for k in ("en", "hi") if cell(row, k)}))
        else:
            vals = [c for c in row if c]
            if cur is None:
                start(None)
            line, rest = vals[0], vals[1:]
            trs = {}
            for v in rest:
                k = "hi" if DEV.search(v) else "en"
                trs.setdefault(k, v)
            cur["rows"].append((line, trs))

    songs = []
    for s in out:
        rows = s["rows"]
        title = s["title"]
        # No title column: a first row with no translation, above rows that have one, is the title.
        if not title and len(rows) > 1 and not rows[0][1] and any(r[1] for r in rows[1:]):
            title = rows.pop(0)[0]
        if not title and s["sheet"] and not re.fullmatch(r"(sheet|blad|feuil|tabelle)\s*\d*", s["sheet"], re.I) \
                and sum(1 for x in out if x["sheet"] == s["sheet"]) == 1:
            title = s["sheet"]
        lines = [{"text": clean_line(t), "translations": {k: clean_line(v) for k, v in tr.items()}}
                 for t, tr in rows if clean_line(t)]
        if not lines:
            continue
        lang = (s["language"] or "").lower()[:2]
        lang = {"hi": "hi", "pa": "pa", "pu": "pa", "en": "en", "हि": "hi", "पं": "pa"}.get(lang) \
            or guess_language([x["text"] for x in lines], english)
        songs.append({"title": title or lines[0]["text"][:60], "title_guessed": not title,
                      "language": lang, "lines": lines})
    return songs


# ---- the one entry point ---------------------------------------------------------------
def parse_items(items: list[tuple], source: str = "", english: set[str] | None = None) -> list[dict]:
    english = _english_words() if english is None else english
    rows = [it for it in items if it[0] in ("row", "sheet")]
    paras = [it for it in items if it[0] == "p"]
    songs = (_songs_from_rows(rows, english) if rows else []) + \
            (_songs_from_paragraphs(paras, english) if any(t for _, t, _ in paras) else [])
    for s in songs:
        s["source"] = source
        s["warnings"] = warnings(s)
    return songs


def parse_file(path: Path, english: set[str] | None = None) -> list[dict]:
    songs = parse_items(read_file(path), path.name, english)
    if not songs:
        raise ReadError(f"No lyrics found in {path.name}. Each line of a song should be on its own line.")
    return songs


def parse_text(text: str, english: set[str] | None = None) -> list[dict]:
    songs = parse_items(text_items(text), "pasted", english)
    if not songs:
        raise ReadError("No lyrics found. Each line of a song should be on its own line.")
    return songs


def warnings(song: dict) -> list[str]:
    w = []
    if song.get("title_guessed"):
        w.append("no title: the first line is used")
    n = len(song["lines"])
    have = sum(1 for ln in song["lines"] if ln["translations"])
    if have == 0:
        w.append("no translation")
    elif have < n:
        w.append(f"translation for {have} of {n} lines")
    if n < 2:
        w.append("only one line")
    return w


# ---- example file (Songs page: "Download an example file") ------------------------------
EXAMPLE = [
    ("Man Mein Tera Naam", "Hindi", [
        ("मन में तेरा नाम बसा है", "Your name lives in my heart", ""),
        ("हर पल तेरा ध्यान रहे", "May I think of you every moment", ""),
        ("निरंकार तू ही सहारा", "Nirankar, you alone are my support", ""),
    ]),
    ("Tera Shukar Data", "Punjabi", [
        ("Tera shukar karaan main har vele", "I thank you at every moment", "मैं हर पल तेरा शुक्र करूँ"),
        ("Tere bina koi hor na sahara", "Without you there is no other support", "तेरे बिना कोई और सहारा नहीं"),
        ("Tera shukar data, tera shukar", "Thank you, Giver, thank you", "शुक्र है दाता, शुक्र है"),
    ]),
]


def write_example(path: Path) -> Path:
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Songs"
    ws.append(["Title", "Line", "English", "Hindi", "Language"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for title, lang, lines in EXAMPLE:
        for i, (line, en, hi) in enumerate(lines):
            ws.append([title if i == 0 else "", line, en, hi, lang if i == 0 else ""])
    for col, width in zip("ABCDE", (22, 40, 40, 36, 10)):
        ws.column_dimensions[col].width = width
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
