"""Song mode: the states from docs/song-mode/04-prototype.md (section 2).

  off -> listening -> suggested -> following <-> lost -> listening

Only *following* puts lyrics on the stream; every other state leaves the
normal captions alone (rule: never stall the captions). The operator's taps
(confirm, not this, back, next, stop, start a song) come from the HTTP
routes; heard text and the clock come from the caption loop.
"""
from __future__ import annotations

import logging
import threading
import time

from . import paths
from .song_match import Matcher, Song, best_line, grams, normalize

log = logging.getLogger("livecaptions.songs")

ON_FILE = paths.DATA / "song_mode.txt"
SUGGEST_FOR = 45      # s: a suggestion nobody tapped goes away
NOT_THIS_FOR = 120    # s: "Not this" keeps a song from being suggested again
LOST_FOR = 60         # s: lost this long = the song is over
END_QUIET = 8         # s: quiet after the last line = the song is over
STALE = 120           # s: no line moved this long while following = over
MIN_SHOW = 1.5        # s: each line stays at least this long on the stream
BIG_MODEL = "qwen-1.7b"


def translation_language(song_language: str, mode: str) -> str:
    """Q2: the translation follows the caption language chosen."""
    if mode == "hi-en":
        return "en"
    if mode in ("en-hi", "en-hinglish"):
        return "hi"
    return "hi" if song_language == "en" else "en"     # auto: the other language


class SongMode:
    def __init__(self, library) -> None:
        self.library = library
        self.lock = threading.RLock()
        self.on = not (ON_FILE.exists() and ON_FILE.read_text().strip() == "off")
        self._songs_ref: list[Song] | None = None
        self.matcher = Matcher([])
        self.ignored: dict[str, float] = {}
        self.shown = 0                     # +1 every time a lyric line goes on the stream
        self.left_at = 0.0                 # when Song mode last stopped following (for the speech model)
        self._to_listening("start")

    # ---- state ------------------------------------------------------------
    def _set(self, state: str, why: str = "") -> None:
        if getattr(self, "state", None) in ("following", "lost") and state not in ("following", "lost"):
            self.left_at = time.time()
        self.state, self.since = state, time.time()
        if why:
            log.info("Song mode: %s (%s)%s", state, why, f" · {self.song.title}" if self.song else "")

    def _to_listening(self, why: str) -> None:
        self.song, self.line, self.heard, self.chorus = None, -1, "", False
        self.matcher.reset()
        self.line_at = 0.0
        self._set("listening" if self.on else "off", why)

    def _refresh_songs(self) -> None:
        songs = self.library.songs()
        if songs is not self._songs_ref:
            self._songs_ref = songs
            self.matcher.songs = songs
            if self.song is not None and not any(s.id == self.song.id for s in songs):
                self._to_listening("song deleted")

    def _move(self, line: int) -> None:
        """Show line `line` of the current song on the stream."""
        line = max(0, min(len(self.song.lines) - 1, line))
        self.line, self.line_at = line, time.time()
        self.chorus = line in self.song.chorus
        self.matcher.lock(self.song, line)
        self.shown += 1
        if self.state != "following":
            self._set("following", f"line {line + 1}")

    # ---- from the caption loop -----------------------------------------------
    def hear(self, text: str, final: bool) -> None:
        with self.lock:
            if not self.on:
                return
            self._refresh_songs()
            if not self.matcher.songs and self.song is None:
                return
            st = self.state
            if st == "following":
                if not final:
                    r = self.matcher.peek(text)
                    if r and time.time() - self.line_at >= MIN_SHOW:
                        self._move(r.line)
                    return
                self.heard = text
                r = self.matcher.feed(text)
                if r.state == "line":
                    if r.line != self.line or time.time() - self.line_at > 3:
                        self._move(r.line)
                elif r.state == "lost":
                    self.matcher.lock(self.song, self.line)
                    self._set("lost", "can't hear the song")
                return
            if not final:
                return
            self.heard = text
            if st == "lost":
                s, i = best_line(grams(normalize(text)), self.song, prefer=self.line)
                if s >= Matcher.FIND_SCORE:
                    self._move(i)
                return
            r = self.matcher.feed(text)
            if st == "listening" and r.state == "found":
                self.song, self.line = r.song, r.line
                self._set("suggested", f"heard {text!r}")
            elif st == "suggested":
                if r.state == "line":
                    self.line = r.line
                elif r.state == "lost":
                    self._to_listening("suggestion faded")

    def tick(self) -> None:
        now = time.time()
        with self.lock:
            for sid, until in list(self.ignored.items()):
                if until < now:
                    del self.ignored[sid]
            self.matcher.ignored = set(self.ignored)
            st = self.state
            if st == "suggested" and now - self.since > SUGGEST_FOR:
                self._to_listening("nobody confirmed")
            elif st == "lost" and now - self.since > LOST_FOR:
                self._to_listening("lost for a minute")
            elif st == "following":
                last = self.line >= len(self.song.lines) - 1
                if (last and now - self.line_at > END_QUIET and now - self.since > END_QUIET) or \
                        now - self.line_at > STALE:
                    self._to_listening("song over")

    # ---- the operator ------------------------------------------------------------
    def confirm(self) -> bool:
        with self.lock:
            if self.state != "suggested" or self.song is None:
                return False
            self._move(self.matcher.line if self.matcher.song is self.song else self.line)
            return True

    def reject(self) -> bool:
        with self.lock:
            if self.song is not None and self.state in ("suggested", "following", "lost"):
                self.ignored[self.song.id] = time.time() + NOT_THIS_FOR
                self.matcher.ignored = set(self.ignored)
            self._to_listening("not this song")
            return True

    def start(self, sid: str, line: int = 0) -> bool:
        with self.lock:
            self._refresh_songs()
            song = next((s for s in self.matcher.songs if s.id == sid), None)
            if song is None:
                return False
            self.ignored.pop(sid, None)
            self.song = song
            self._set("following", "started by the operator")
            self._move(line)
            return True

    def step(self, d: int) -> bool:
        with self.lock:
            if self.song is None or self.state not in ("following", "lost", "suggested"):
                return False
            if self.state == "suggested":
                self._move(self.line)
            else:
                self._move(self.line + d)
            return True

    def stop(self) -> bool:
        with self.lock:
            self._to_listening("stopped by the operator")
            return True

    def set_on(self, on: bool) -> None:
        with self.lock:
            self.on = on
            ON_FILE.parent.mkdir(parents=True, exist_ok=True)
            ON_FILE.write_text("on" if on else "off")
            self._to_listening("switched " + ("on" if on else "off"))

    # ---- output -----------------------------------------------------------------
    def wants_big_model(self) -> bool:
        """While a song is shown (and 2 minutes after), speech uses the 1.7B model (Gate 2)."""
        return self.state in ("following", "lost") or (self.left_at and time.time() - self.left_at < 120)

    def lyric(self, mode: str) -> tuple[str, str] | None:
        """(line, translation) to show, only while following."""
        with self.lock:
            if self.state != "following" or self.song is None:
                return None
            ln = self.song.lines[self.line]
            return ln.text, ln.translations.get(translation_language(self.song.language, mode), "")

    def view(self, mode: str) -> dict:
        with self.lock:
            s = self.song
            out = {"on": self.on, "state": self.state, "count": len(self.library.songs()),
                   "since": round(time.time() - self.since, 1), "heard": self.heard,
                   "guesses": [{"id": g.id, "title": g.title} for g in self.matcher.guesses
                               if not s or g.id != s.id][:3]}
            if s is not None:
                tr = translation_language(s.language, mode)
                ln = s.lines[self.line] if 0 <= self.line < len(s.lines) else None
                nxt = s.lines[self.line + 1] if 0 <= self.line + 1 < len(s.lines) else None
                out["song"] = {"id": s.id, "title": s.title, "language": s.language, "lines": len(s.lines),
                               "line": self.line, "text": ln.text if ln else "",
                               "translation": ln.translations.get(tr, "") if ln else "",
                               "next": nxt.text if nxt else "", "chorus": self.chorus}
            return out
