"""Song mode feasibility test (docs/song-mode/02-feasibility.md).

Text test (fast, no model):   python tests/test_songs.py
Audio test (Qwen3-ASR):       python tests/test_songs.py --audio [qwen-0.6b|qwen-1.7b]

The audio is the Mac's Hindi voice, slowed down, with a drone and echo under it
to be a little like a bhajan. It is a stand-in until real recordings come.
The songs are written for this test (no copyrighted lyrics).
"""
from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from livecaptions.song_match import Line, Matcher, Song  # noqa: E402

# (id, title, language, [(line, english, hindi, what the voice reads)])
SONGS = [
    ("man", "Man Mein Tera Naam", "hi", [
        ("मन में तेरा नाम बसा है", "Your name lives in my heart", None, None),
        ("हर पल तेरा ध्यान रहे", "May I think of you every moment", None, None),
        ("सत्संग में जो आया है", "Whoever has come to the satsang", None, None),
        ("उसका जीवन धन्य हुआ", "their life is blessed", None, None),
        ("निरंकार तू ही सहारा", "Nirankar, you alone are my support", None, None),
        ("दुनिया के इस मेले में", "In this fair of the world", None, None),
        ("तेरा प्रेम ही सच्चा है", "only your love is true", None, None),
        ("निरंकार तू ही सहारा", "Nirankar, you alone are my support", None, None),
    ]),
    ("shukar", "Tera Shukar Data", "pa", [
        ("Tera shukar karaan main har vele", "I thank you at every moment", "मैं हर पल तेरा शुक्र करूँ", "तेरा शुकर करां मैं हर वेले"),
        ("Tere bina koi hor na sahara", "Without you there is no other support", "तेरे बिना कोई और सहारा नहीं", "तेरे बिना कोई होर ना सहारा"),
        ("Sangat de vich baith ke gaavan", "Sitting in the sangat, I sing", "संगत में बैठकर मैं गाऊँ", "संगत दे विच बैठ के गावां"),
        ("Mann mera ho gaya nihaal", "My heart is filled with joy", "मेरा मन निहाल हो गया", "मन मेरा हो गया निहाल"),
        ("Tera shukar data, tera shukar", "Thank you, Giver, thank you", "शुक्र है दाता, शुक्र है", "तेरा शुकर दाता, तेरा शुकर"),
        ("Gyan di jot jagai tu", "You lit the light of knowledge", "तूने ज्ञान की ज्योत जलाई", "ज्ञान दी जोत जगाई तू"),
        ("Tera shukar data, tera shukar", "Thank you, Giver, thank you", "शुक्र है दाता, शुक्र है", "तेरा शुकर दाता, तेरा शुकर"),
    ]),
    ("mehar", "Satguru Di Mehar", "pa", [
        ("सतगुरु दी मेहर होई", "The Satguru's grace came", "सतगुरु की कृपा हुई", None),
        ("दिल विच चानण होया", "Light came into the heart", "दिल में उजाला हुआ", None),
        ("भुलेखे सारे मिट गए", "All doubts were wiped away", "सारे भ्रम मिट गए", None),
        ("नाम दा रंग चढ़ गया", "The colour of the Name took hold", "नाम का रंग चढ़ गया", None),
        ("हुण कोई डर ना रहया", "Now no fear is left", "अब कोई डर नहीं रहा", None),
    ]),
    ("naam", "Tera Naam Sahara", "hi", [   # shares words with "man" on purpose
        ("तेरा नाम ही सहारा है", "Your name alone is my support", None, None),
        ("मन में प्रेम जगा दे", "Awaken love in my heart", None, None),
        ("हर पल सेवा करूँ मैं", "May I serve every moment", None, None),
        ("सत्संग की राह दिखा दे", "Show me the path of satsang", None, None),
        ("तेरा नाम ही सहारा है", "Your name alone is my support", None, None),
    ]),
    ("prem", "Prem Ki Ganga", "hi", [   # Hindi written in Roman letters
        ("Prem ki ganga beh rahi hai", "A river of love is flowing", None, "प्रेम की गंगा बह रही है"),
        ("Sab mil ke isme naha lo", "Everyone, bathe in it together", None, "सब मिल के इसमें नहा लो"),
        ("Man ka mail dho dalo", "Wash away the dirt of the mind", None, "मन का मैल धो डालो"),
        ("Guru charan mein aa jao", "Come to the Guru's feet", None, "गुरु चरण में आ जाओ"),
    ]),
    ("formless", "O Formless One", "en", [
        ("O formless one, you live in all", None, "हे निराकार, तुम सब में बसते हो", None),
        ("In every heart your light is found", None, "हर दिल में तुम्हारा प्रकाश है", None),
        ("We gather here to sing your name", None, "हम यहाँ तुम्हारा नाम गाने आए हैं", None),
        ("And leave our pride upon the ground", None, "और अपना अहंकार यहीं छोड़ देते हैं", None),
    ]),
]

# Sung, but not in the library: must never lock.
UNKNOWN = [
    "चलो रे मन गुरु के द्वारे",
    "जहाँ प्रेम की बरखा होती",
    "सब संतों का मेला लगा",
    "वहाँ दुख ना कोई होता",
]


def library() -> list[Song]:
    out = []
    for sid, title, lang, lines in SONGS:
        out.append(Song(sid, title, lang, [
            Line(t, {k: v for k, v in (("en", en), ("hi", hi)) if v}) for t, en, hi, _ in lines]).prepare())
    return out


def spoken(sid: str) -> list[str]:
    for s, _, _, lines in SONGS:
        if s == sid:
            return [say or t for t, _, _, say in lines]
    return UNKNOWN


# Scenarios: (name, song id, the line numbers sung in order; None = speech between songs)
SCENARIOS = [
    ("from the start", "man", [0, 1, 2, 3, 4, 5, 6, 7]),
    ("Punjabi, Roman letters", "shukar", [0, 1, 2, 3, 4, 5, 6]),
    ("Punjabi, Devanagari", "mehar", [0, 1, 2, 3, 4]),
    ("starts mid-song", "man", [2, 3, 4, 5, 6]),
    ("repeats the chorus", "shukar", [4, 4, 0, 4, 5, 4]),
    ("similar song (decoy)", "naam", [0, 1, 2, 3, 4]),
    ("Hindi in Roman letters", "prem", [0, 1, 2, 3]),
    ("English song", "formless", [0, 1, 2, 3]),
    ("song not in library", "unknown", [0, 1, 2, 3]),
]


# ---- text noise (what a speech model gets wrong) ---------------------------
def noisy(text: str, rng: random.Random, level: float) -> str:
    words = text.split()
    out = []
    for w in words:
        r = rng.random()
        if r < level * 0.3:
            continue                                  # dropped word
        if r < level * 0.7 and len(w) > 3:            # misheard letters
            i = rng.randrange(1, len(w) - 1)
            w = w[:i] + w[i + 1:]
        out.append(w)
    if rng.random() < level * 0.3:
        out.append(rng.choice(["जी", "हाँ", "हो", "ओ"]))   # filler the singer adds
    return " ".join(out)


def run(scenario, songs, heard_for) -> dict:
    name, sid, order = scenario
    m = Matcher(songs)
    found_at, wrong, shown, lost = None, 0, 0, 0
    for k, i in enumerate(order):
        r = m.feed(heard_for(sid, i))
        if r.state in ("found", "line"):
            shown += 1
            ok = sid != "unknown" and r.song.id == sid and \
                normalize_eq(r.song.lines[r.line].text, songs, sid, i)
            if not ok:
                wrong += 1
            if found_at is None:
                found_at = k + 1
        if r.state == "lost":
            lost += 1
    return {"name": name, "found_at": found_at, "wrong": wrong, "shown": shown, "lost": lost,
            "lines": len(order), "unknown": sid == "unknown"}


def normalize_eq(text: str, songs, sid: str, i: int) -> bool:
    """The shown line is the sung one (or the same words, e.g. a chorus)."""
    from livecaptions.song_match import normalize
    song = next(s for s in songs if s.id == sid)
    return normalize(text) == normalize(song.lines[i].text)


def report(rows: list[dict], title: str) -> bool:
    print(f"\n{title}\n" + "-" * len(title))
    ok_all = True
    for r in rows:
        if r["unknown"]:
            ok = r["shown"] == 0
            print(f"  {'PASS' if ok else 'FAIL'}  {r['name']:<24} shown {r['shown']} (must be 0)")
        else:
            ok = r["found_at"] is not None and r["found_at"] <= 2 and r["wrong"] == 0 and r["lost"] == 0
            print(f"  {'PASS' if ok else 'FAIL'}  {r['name']:<24} found after line {r['found_at']}, "
                  f"shown {r['shown']}/{r['lines']}, wrong {r['wrong']}, lost {r['lost']}")
        ok_all &= ok
    return ok_all


def text_test() -> bool:
    songs = library()
    ok = report([run(s, songs, lambda sid, i: spoken(sid)[i]) for s in SCENARIOS], "Text, exact words")
    rng = random.Random(7)
    rows = [run(s, songs, lambda sid, i: noisy(spoken(sid)[i], rng, 0.5)) for s in SCENARIOS]
    ok &= report(rows, "Text, misheard words (about 1 in 4 words wrong or missing)")
    return ok


# ---- audio ------------------------------------------------------------------
AUDIO = Path("/tmp/lc_song_audio")


def make_clip(text: str, voice: str, path: Path):
    import numpy as np
    import soundfile as sf
    if not path.exists():
        aiff = path.with_suffix(".aiff")
        subprocess.run(["say", "-v", voice, "-r", "105", "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(path)], check=True)
        aiff.unlink()
        a, sr = sf.read(path, dtype="float32")
        t = np.arange(len(a)) / sr
        drone = 0.05 * (np.sin(2 * np.pi * 146.8 * t) + 0.6 * np.sin(2 * np.pi * 220 * t)
                        + 0.4 * np.sin(2 * np.pi * 293.7 * t))            # harmonium-like Sa-Pa-Sa
        wet = a.copy()
        for d, g in ((0.11, 0.35), (0.23, 0.2), (0.37, 0.12)):            # hall echo
            n = int(d * sr)
            wet[n:] += g * a[:-n]
        mix = wet + drone + 0.01 * np.random.default_rng(1).standard_normal(len(a))
        sf.write(path, (mix / max(1e-6, np.abs(mix).max()) * 0.8).astype("float32"), sr)
    import soundfile as sf
    return sf.read(path, dtype="float32")[0]


def audio_test(key: str) -> bool:
    from livecaptions import qwen_engine
    eng = qwen_engine.QwenEngine(lambda *_: None)
    eng.load(key)
    AUDIO.mkdir(exist_ok=True)
    songs = library()
    cache: dict[tuple, str] = {}
    lang_of = {sid: lang for sid, _, lang, _ in SONGS}

    def heard(sid, i):
        if (sid, i) not in cache:
            voice = "Rishi" if lang_of.get(sid) == "en" else "Lekha"
            clip = make_clip(spoken(sid)[i], voice, AUDIO / f"{sid}-{i}.wav")
            cache[(sid, i)] = eng.transcribe_clip(clip)
            print(f"    heard {sid}-{i}: {cache[(sid, i)]}", flush=True)
        return cache[(sid, i)]

    return report([run(s, songs, heard) for s in SCENARIOS], f"Audio through {key} (voice + drone + echo)")


# ---- reading uploads (any format) --------------------------------------------------
def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail and not ok else ''}")
    return ok


def import_test() -> bool:
    import tempfile
    import zipfile
    from livecaptions import song_import as I
    from livecaptions.translator import ENGLISH_WORDS as EN
    print("\nReading uploads\n---------------")
    tmp = Path(tempfile.mkdtemp())
    ok = True
    pasted = ("Man Mein Tera Naam\n\nमन में तेरा नाम बसा है\nYour name lives in my heart\n"
              "हर पल तेरा ध्यान रहे (x2)\nMay I think of you every moment\n\n\n"
              "Tera Shukar Data\nTera shukar karaan main har vele\nI thank you at every moment\n"
              "Tere bina koi hor na sahara\nWithout you there is no other support\n"
              "Sangat de vich baith ke gaavan\nSitting in the sangat, I sing\n\n\n"
              "Title: O Formless One\nO formless one, you live in all\nहे निराकार, तुम सब में बसते हो\n"
              "In every heart your light is found\nहर दिल में तुम्हारा प्रकाश है\n")
    s = I.parse_text(pasted, EN)
    ok &= check("pasted: 3 songs, titles", [x["title"] for x in s] == ["Man Mein Tera Naam", "Tera Shukar Data", "O Formless One"],
                str([x["title"] for x in s]))
    ok &= check("pasted: languages hi / pa / en", [x["language"] for x in s] == ["hi", "pa", "en"], str([x["language"] for x in s]))
    ok &= check("pasted: (x2) removed, translation paired",
                s[0]["lines"][1] == {"text": "हर पल तेरा ध्यान रहे", "translations": {"en": "May I think of you every moment"}},
                str(s[0]["lines"][1]))
    ok &= check("pasted: Roman Punjabi + English paired", all(ln["translations"].get("en") for ln in s[1]["lines"]))
    ok &= check("pasted: English song + Hindi paired", s[2]["lines"][0]["translations"].get("hi", "").startswith("हे"))

    ex = I.write_example(tmp / "ex.xlsx")
    s = I.parse_file(ex, EN)
    ok &= check("Excel with headers", [(x["title"], x["language"], len(x["lines"])) for x in s] ==
                [("Man Mein Tera Naam", "hi", 3), ("Tera Shukar Data", "pa", 3)], str(s))
    (tmp / "s.csv").write_text("सतगुरु दी मेहर होई,The Satguru's grace came\nदिल विच चानण होया,Light came into the heart\n\n"
                               "तेरा नाम ही सहारा है,Your name alone is my support\nमन में प्रेम जगा दे,Awaken love in my heart\n",
                               encoding="utf-8")
    s = I.parse_file(tmp / "s.csv", EN)
    ok &= check("CSV without headers: blank row = next song", len(s) == 2 and s[0]["language"] == "pa", str(s))

    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    p = lambda t, b=False: f'<w:p><w:r>{"<w:rPr><w:b/></w:rPr>" if b else ""}<w:t>{t}</w:t></w:r></w:p>'
    body = (p("Satguru Di Mehar", True) + p("सतगुरु दी मेहर होई") + p("The Satguru's grace came") + p("दिल विच चानण होया")
            + p("Light came into the heart") + p("") + p("Tera Naam Sahara", True) + p("तेरा नाम ही सहारा है")
            + p("Your name alone is my support") + p("मन में प्रेम जगा दे") + p("Awaken love in my heart"))
    with zipfile.ZipFile(tmp / "s.docx", "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", f"<w:document {w}><w:body>{body}</w:body></w:document>")
    s = I.parse_file(tmp / "s.docx", EN)
    ok &= check("Word: bold lines are titles", [x["title"] for x in s] == ["Satguru Di Mehar", "Tera Naam Sahara"]
                and all(len(x["lines"]) == 2 for x in s), str(s))
    try:
        I.parse_file(tmp / "old.doc")
        ok &= check("old .doc refused with a hint", False)
    except I.ReadError as e:
        ok &= check("old .doc refused with a hint", "docx" in str(e))
    try:
        from pypdf import PdfWriter
        PdfWriter().add_blank_page(100, 100) if False else None
        wr = PdfWriter()
        wr.add_blank_page(200, 200)
        wr.write(tmp / "scan.pdf")
        I.parse_file(tmp / "scan.pdf", EN)
        ok &= check("PDF with no text (scan) explained", False)
    except I.ReadError as e:
        ok &= check("PDF with no text (scan) explained", "scanned" in str(e), str(e))
    except ImportError:
        print("  SKIP  PDF (pypdf not installed)")
    return ok


# ---- Song mode states (docs/song-mode/04-prototype.md, section 2) ---------------------
def state_test() -> bool:
    import tempfile
    from livecaptions import song_mode as M
    from livecaptions.song_library import Library
    print("\nSong mode states\n----------------")
    M.ON_FILE = Path(tempfile.mkdtemp()) / "song_mode.txt"
    lib = Library(Path(tempfile.mkdtemp()) / "library.db")
    for sid, title, lang, lines in SONGS:
        lib.save({"title": title, "language": lang, "lines": [
            {"text": t, "translations": {k: v for k, v in (("en", en), ("hi", hi)) if v}} for t, en, hi, _ in lines]})
    by_title = {s["title"]: s["id"] for s in lib.summary()}
    sm = M.SongMode(lib)
    clock = [1000.0]
    M.time.time = lambda: clock[0]
    ok = True

    def sing(sid, i, dt=4.0):
        clock[0] += dt
        sm.hear(spoken(sid)[i], True)
        sm.tick()

    # S1: found -> suggested (nothing on the stream) -> confirm -> following
    sing("man", 0)
    sing("man", 1)
    ok &= check("S1 suggested after 2 lines, stream untouched", sm.state == "suggested" and sm.lyric("hi-en") is None,
                sm.state)
    sm.confirm()
    ok &= check("S1 confirm -> lyric + English on the stream",
                sm.lyric("hi-en") == ("हर पल तेरा ध्यान रहे", "May I think of you every moment"), str(sm.lyric("hi-en")))
    sing("man", 2)
    ok &= check("S1 follows the next line", sm.line == 2, str(sm.line))
    ok &= check("Q2 translation follows the caption language", sm.lyric("en-hi") == ("सत्संग में जो आया है", ""))
    # S6: hard to hear -> lost (normal captions) -> heard again -> following
    for _ in range(3):
        clock[0] += 3
        sm.hear("और आज हम सब यहाँ मिलकर बैठे हैं बहुत अच्छा लगा", True)
    ok &= check("S6 3 misses -> lost, lyric off the stream", sm.state == "lost" and sm.lyric("hi-en") is None, sm.state)
    sing("man", 4)
    ok &= check("S6 heard again -> following at that line", sm.state == "following" and sm.line == 4, f"{sm.state} {sm.line}")
    # Back / Next, and the chorus label
    sm.step(1)
    sm.step(-1)
    ok &= check("Back / Next", sm.line == 4 and sm.chorus, f"{sm.line} chorus={sm.chorus}")
    # S7: last line, then quiet -> song over -> listening
    sm.step(3)
    clock[0] += M.END_QUIET + 1
    sm.tick()
    ok &= check("S7 quiet after the last line -> listening", sm.state == "listening", sm.state)
    # S4: wrong guess -> Not this -> not suggested again for 2 minutes; Pick the song
    sing("naam", 0)
    sing("naam", 1)
    first = sm.song.id if sm.song else ""
    sm.reject()
    sing("naam", 2)
    sing("naam", 3)
    ok &= check("S4 'Not this' keeps it away", sm.state != "suggested" or (sm.song and sm.song.id != first), sm.state)
    sm.start(by_title["Man Mein Tera Naam"])
    ok &= check("S4 operator picks the song -> following line 1", sm.state == "following" and sm.line == 0)
    sm.stop()
    clock[0] += M.NOT_THIS_FOR + 1
    sm.tick()
    sing("naam", 0)
    sing("naam", 1)
    ok &= check("S4 suggested again after 2 minutes", sm.state == "suggested" and sm.song.id == first, sm.state)
    # Suggestion nobody tapped goes away
    clock[0] += M.SUGGEST_FOR + 1
    sm.tick()
    ok &= check("suggestion with no tap goes away (45 s)", sm.state == "listening", sm.state)
    # S5: unknown song: nothing
    for i in range(4):
        sing("unknown", i)
    ok &= check("S5 unknown song: no suggestion", sm.state == "listening", sm.state)
    # Off
    sm.set_on(False)
    sing("man", 0)
    sing("man", 1)
    ok &= check("Song mode off: nothing happens", sm.state == "off")
    M.time.time = time_time
    return ok


time_time = __import__("time").time


if __name__ == "__main__":
    ok = text_test()
    ok &= import_test()
    ok &= state_test()
    if "--audio" in sys.argv:
        key = next((a for a in sys.argv if a.startswith("qwen-")), "qwen-0.6b")
        ok &= audio_test(key)
    print("\nALL SONG CHECKS PASS" if ok else "\nSOME SONG CHECKS FAIL")
    sys.exit(0 if ok else 1)
