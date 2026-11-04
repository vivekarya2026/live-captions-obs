"""Song mode: the song library (its own SQLite file) and reading uploads.

Library:  ~/.livecaptions/songs/library.db   songs + lines (+ translations)
Originals: ~/.livecaptions/songs/files/       every uploaded file, kept as it came

Uploads in any of: .docx, .pdf, .xlsx, .csv, .txt, or pasted text. They are cut
into songs and lines by song_import.py; nothing is saved until the person
checks the result (Check page) and presses Save.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from . import paths
from .song_match import Line, Song

ROOT = paths.DATA / "songs"
DB = ROOT / "library.db"
FILES = ROOT / "files"
LANGUAGES = ("hi", "pa", "en")


class Library:
    def __init__(self, db: Path = DB) -> None:
        self.db = db
        self._lock = threading.Lock()
        self._songs: list[Song] | None = None   # prepared for matching, rebuilt after changes
        db.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, language TEXT NOT NULL,
                source TEXT DEFAULT '', added REAL, updated REAL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS lines (
                song_id TEXT NOT NULL, n INTEGER NOT NULL, text TEXT NOT NULL,
                translations TEXT DEFAULT '{}', PRIMARY KEY (song_id, n))""")

    def _con(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db, timeout=10)
        c.execute("PRAGMA foreign_keys = ON")
        return c

    # ---- reading ----------------------------------------------------------
    def summary(self) -> list[dict]:
        with self._con() as c:
            rows = c.execute("""SELECT s.id, s.title, s.language, s.source, COUNT(l.n),
                                       GROUP_CONCAT(l.translations, '\x1f')
                                FROM songs s LEFT JOIN lines l ON l.song_id = s.id
                                GROUP BY s.id ORDER BY s.title COLLATE NOCASE""").fetchall()
        out = []
        for sid, title, lang, source, n, trs in rows:
            have = set()
            for t in (trs or "").split("\x1f"):
                try:
                    have |= {k for k, v in json.loads(t or "{}").items() if v}
                except ValueError:
                    pass
            out.append({"id": sid, "title": title, "language": lang, "source": source,
                        "lines": n, "translations": sorted(have)})
        return out

    def get(self, sid: str) -> dict | None:
        with self._con() as c:
            row = c.execute("SELECT id, title, language, source FROM songs WHERE id = ?", (sid,)).fetchone()
            if not row:
                return None
            lines = c.execute("SELECT text, translations FROM lines WHERE song_id = ? ORDER BY n",
                              (sid,)).fetchall()
        return {"id": row[0], "title": row[1], "language": row[2], "source": row[3],
                "lines": [{"text": t, "translations": json.loads(tr or "{}")} for t, tr in lines]}

    def songs(self) -> list[Song]:
        """Every song, ready for the matcher (cached until the library changes)."""
        with self._lock:
            if self._songs is None:
                out = []
                for s in self.summary():
                    full = self.get(s["id"])
                    if full and full["lines"]:
                        out.append(Song(full["id"], full["title"], full["language"], [
                            Line(ln["text"], ln["translations"]) for ln in full["lines"]]).prepare())
                self._songs = out
            return self._songs

    def count(self) -> int:
        with self._con() as c:
            return c.execute("SELECT COUNT(*) FROM songs").fetchone()[0]

    # ---- changing -----------------------------------------------------------
    def save(self, song: dict) -> str:
        """Add or replace one song: {id?, title, language, source?, lines: [{text, translations}]}."""
        sid = song.get("id") or uuid.uuid4().hex[:12]
        title = " ".join(str(song.get("title") or "").split())[:120] or "Untitled song"
        lang = song.get("language") if song.get("language") in LANGUAGES else "hi"
        lines = []
        for ln in song.get("lines") or []:
            text = " ".join(str(ln.get("text") or "").split())[:300]
            if not text:
                continue
            trs = {k: " ".join(str(v or "").split())[:300] for k, v in (ln.get("translations") or {}).items()
                   if k in LANGUAGES and str(v or "").strip()}
            lines.append((text, json.dumps(trs, ensure_ascii=False)))
        if not lines:
            raise ValueError("A song needs at least one line.")
        now = time.time()
        with self._con() as c:
            c.execute("""INSERT INTO songs (id, title, language, source, added, updated) VALUES (?,?,?,?,?,?)
                         ON CONFLICT(id) DO UPDATE SET title=excluded.title, language=excluded.language,
                         updated=excluded.updated""", (sid, title, lang, str(song.get("source") or ""), now, now))
            c.execute("DELETE FROM lines WHERE song_id = ?", (sid,))
            c.executemany("INSERT INTO lines (song_id, n, text, translations) VALUES (?,?,?,?)",
                          [(sid, i, t, tr) for i, (t, tr) in enumerate(lines)])
        self._changed()
        return sid

    def delete(self, sid: str) -> bool:
        with self._con() as c:
            c.execute("DELETE FROM lines WHERE song_id = ?", (sid,))
            gone = c.execute("DELETE FROM songs WHERE id = ?", (sid,)).rowcount > 0
        self._changed()
        return gone

    def keep_original(self, path: Path) -> str:
        """Copy an uploaded file into the library folder; returns the kept file's name."""
        FILES.mkdir(parents=True, exist_ok=True)
        dst = FILES / path.name
        if dst.exists() and dst.read_bytes() != path.read_bytes():
            dst = FILES / f"{path.stem} ({time.strftime('%Y-%m-%d %H%M%S')}){path.suffix}"
        if not dst.exists():
            shutil.copy2(path, dst)
        return dst.name

    def _changed(self) -> None:
        with self._lock:
            self._songs = None
