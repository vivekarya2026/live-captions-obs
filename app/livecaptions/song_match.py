"""Song mode: find which song is being sung, and which line, from what the
speech model heard.

Everything is compared in one spelling-proof form: Devanagari is turned into
Roman letters (hinglish.py), then each word gets a loose key (hum/ham,
milkar/milakar, shukar/shukr match). Lines are compared by groups of three
letters, so a word the model mishears only costs a little.

Two jobs:
- `Matcher.feed(heard)` while no song is locked: scores every song, and
  says "found" only when one song clearly wins (`find_*` limits).
- once locked: looks only near the current line (back 1, ahead 3, plus the
  chorus), so the next line wins over a similar line elsewhere. Too many
  misses in a row = lost: the caller falls back to normal captions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .hinglish import DEV_LETTERS, loose_key, to_hinglish

DEV = re.compile(f"[{DEV_LETTERS}]")


def normalize(text: str) -> str:
    """Any script or spelling -> loose Roman words."""
    if DEV.search(text):
        text = to_hinglish(text)
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return " ".join(k for k in (loose_key(w) for w in words) if k)


def grams(norm: str) -> set[str]:
    s = f" {norm} "
    return {s[i:i + 3] for i in range(len(s) - 2)} if len(s) > 3 else set()


def similarity(heard: set[str], line: set[str]) -> float:
    """Dice overlap, 0..1."""
    if not heard or not line:
        return 0.0
    return 2 * len(heard & line) / (len(heard) + len(line))


@dataclass
class Line:
    text: str                      # as uploaded
    translations: dict[str, str]   # "en" / "hi" / "pa" -> text
    grams: set[str] = field(default_factory=set)


@dataclass
class Song:
    id: str
    title: str
    language: str                  # "hi" | "pa" | "en"
    lines: list[Line]
    chorus: set[int] = field(default_factory=set)   # indexes of lines that repeat

    def prepare(self) -> "Song":
        seen: dict[str, int] = {}
        for i, ln in enumerate(self.lines):
            norm = normalize(ln.text)
            ln.grams = grams(norm)
            if norm in seen:                        # written twice = chorus
                self.chorus |= {seen[norm], i}
            seen.setdefault(norm, i)
        return self


def best_line(heard: set[str], song: Song, around: int | None = None,
              prefer: int | None = None) -> tuple[float, int]:
    """Best line for what was heard. Near `around` when following, else anywhere.
    Same words twice (a chorus): the copy nearest after `prefer` (or `around`) wins."""
    n = len(song.lines)
    if around is None:
        idx = range(n)
    else:
        idx = sorted({i for i in range(around - 1, around + 4) if 0 <= i < n} | song.chorus)
    home = prefer if prefer is not None else (around if around is not None else 0)
    near = lambda i: (i - home) % n if n else 0     # 0 = here, 1 = next, …, wraps to the top
    single = {i: similarity(heard, song.lines[i].grams) for i in idx}
    best = (0.0, -1)
    for i, s in single.items():
        if s > best[0] + 1e-9 or (abs(s - best[0]) <= 1e-9 and best[1] >= 0 and near(i) < near(best[1])):
            best = (s, i)
    # The singer ran two lines together: credit the later one (that's where they are now),
    # only when the pair clearly explains more than either line alone.
    for i in idx:
        if i + 1 < n and i + 1 in single:
            pair = similarity(heard, song.lines[i].grams | song.lines[i + 1].grams)
            if pair > max(single[i], single[i + 1]) + 0.08 and pair > best[0]:
                best = (pair, i + 1)
    return best


@dataclass
class Result:
    state: str            # "listening" | "maybe" | "found" | "line" | "miss" | "lost"
    song: Song | None = None
    line: int = -1
    score: float = 0.0


class Matcher:
    # Limits found with tests/test_songs.py (see docs/song-mode/02-feasibility.md).
    FIND_SCORE = 0.42      # a heard piece this close to a line counts as evidence
    FIND_MARGIN = 0.10     # ... and must beat the next song by this much
    FIND_STRONG = 0.62     # one piece this close is enough on its own
    FOLLOW_SCORE = 0.34    # once locked, a line this close moves the caption
    LOST_AFTER = 3         # misses in a row = lost

    def __init__(self, songs: list[Song]) -> None:
        self.songs = songs
        self.ignored: set[str] = set()     # "Not this": not suggested for a while
        self.guesses: list[Song] = []      # best songs for the last heard piece (for "Pick the song")
        self.reset()

    def reset(self) -> None:
        self.song: Song | None = None
        self.line = -1
        self.misses = 0
        self._votes: dict[str, float] = {}
        self._last_best = ""

    def lock(self, song: Song, line: int = 0) -> None:
        """The operator picked or confirmed a song."""
        self.song, self.line, self.misses = song, line, 0

    def feed(self, heard_text: str) -> Result:
        heard = grams(normalize(heard_text))
        if len(heard) < 6:                      # a word or two: not enough to judge
            return Result("listening" if self.song is None else "miss", self.song, self.line)
        if self.song is not None:
            return self._follow(heard)
        return self._find(heard)

    def _find(self, heard: set[str]) -> Result:
        scored = sorted(((best_line(heard, s), s) for s in self.songs if s.id not in self.ignored),
                        key=lambda x: -x[0][0])
        self.guesses = [s for (sc, _), s in scored[:3] if sc >= 0.2]
        if not scored:
            return Result("listening")
        (s1, i1), top = scored[0]
        s2 = scored[1][0][0] if len(scored) > 1 else 0.0
        if s1 < self.FIND_SCORE or s1 - s2 < self.FIND_MARGIN:
            self._votes.clear()
            return Result("listening", score=s1)
        # Two pieces in a row pointing at the same song, or one very close piece.
        votes = self._votes.get(top.id, 0) + 1
        self._votes = {top.id: votes}
        if votes >= 2 or s1 >= self.FIND_STRONG:
            self.lock(top, i1)
            self._votes.clear()
            return Result("found", top, i1, s1)
        return Result("maybe", top, i1, s1)

    def peek(self, partial: str) -> Result | None:
        """A half-heard line while following: move ahead early, only when it's
        clearly the next line (never counts as a miss)."""
        if self.song is None:
            return None
        heard = grams(normalize(partial))
        if len(heard) < 12:
            return None
        s, i = best_line(heard, self.song, self.line)
        here = similarity(heard, self.song.lines[self.line].grams) if self.line >= 0 else 0.0
        if i == self.line + 1 and s >= self.FOLLOW_SCORE + 0.08 and s - here >= self.FIND_MARGIN:
            self.line, self.misses = i, 0
            return Result("line", self.song, i, s)
        return None

    def _follow(self, heard: set[str]) -> Result:
        s, i = best_line(heard, self.song, self.line)
        # The singer jumped (back to verse 1, skipped a verse): a much closer line elsewhere wins.
        far_s, far_i = best_line(heard, self.song, prefer=self.line)
        if far_i != i and far_s >= self.FIND_SCORE and far_s - s >= self.FIND_MARGIN:
            s, i = far_s, far_i
        if s >= self.FOLLOW_SCORE:
            self.line, self.misses = i, 0
            return Result("line", self.song, i, s)
        self.misses += 1
        if self.misses >= self.LOST_AFTER:
            song = self.song
            self.reset()
            return Result("lost", song, -1, s)
        return Result("miss", self.song, self.line, s)
