"""Writes captions into a Google Doc, through the small Apps Script that the
user adds to the doc (google-docs/LiveCaptions.gs). That script shows a
"Live Captions" sidebar in Docs (Start/Stop writing) and runs a web app that
receives our lines and appends them to the document.

Why not let the sidebar read from this app directly? Chrome blocks web pages
inside Google Docs from talking to programs on the user's own computer
(Local Network Access), so the lines go out through Google instead.

Connection link (copied from the sidebar):
    https://script.google.com/macros/s/<id>/exec?k=<key>
"""
from __future__ import annotations

import json
import logging
import queue
import ssl
import threading
import time
import urllib.parse
import urllib.request

from . import paths

log = logging.getLogger("gdocs")

CONFIG = paths.DATA / "google_docs.json"
POLL_SECONDS = 5          # ask the doc whether writing is on (when no lines are going out)
BATCH = 20


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # the bundled Python has no system certificates on macOS
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def parse_link(link: str) -> tuple[str, str] | None:
    """-> (web app URL, key) or None if this isn't a Live Captions connection link."""
    link = (link or "").strip()
    u = urllib.parse.urlparse(link)
    key = urllib.parse.parse_qs(u.query).get("k", [""])[0]
    if u.scheme != "https" or u.netloc not in ("script.google.com", "script.googleusercontent.com") \
            or not u.path.endswith("/exec") or len(key) < 16:
        return None
    return f"https://{u.netloc}{u.path}", key


class GoogleDocs:
    def __init__(self) -> None:
        self.url = ""
        self.key = ""
        self.writing: bool | None = None   # None = not known yet
        self.doc = ""
        self.error = ""
        self.sent = 0
        self.last_ok = 0.0
        self.show_time: bool | None = None  # as set in the doc (None = not known yet)
        self.old_script = False             # the doc's script predates Start/Stop from the app
        self._cmd: dict = {}                # sent with the next call: {"cmd": "start"/"stop", "showTime": bool}
        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=1000)
        self._retry: list[dict] = []
        self._wake = threading.Event()
        self._ctx = _ssl_context()
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
            parsed = parse_link(cfg.get("link", ""))
            if parsed:
                self.url, self.key = parsed
        except (OSError, ValueError):
            pass
        threading.Thread(target=self._run, daemon=True).start()

    # ---- settings from the app window ------------------------------------
    def connect(self, link: str) -> str:
        parsed = parse_link(link)
        if not parsed:
            return "That isn't a Live Captions link. Copy it from the sidebar in Google Docs."
        self.url, self.key = parsed
        self.writing, self.doc, self.error = None, "", ""
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"link": link.strip()}), encoding="utf-8")
        self._wake.set()
        return ""

    def disconnect(self) -> None:
        self.url = self.key = ""
        self.writing, self.doc, self.error = None, "", ""
        CONFIG.unlink(missing_ok=True)

    def command(self, writing: bool | None = None, show_time: bool | None = None) -> None:
        """Start/Stop writing or switch time stamps from the app window (sent on the next call)."""
        if writing is not None:
            self._cmd["cmd"] = "start" if writing else "stop"
            self.writing = writing  # show it right away; the doc's answer confirms it
        if show_time is not None:
            self._cmd["showTime"] = self.show_time = show_time
        self._wake.set()

    def status(self) -> dict:
        return {"linked": bool(self.url), "writing": self.writing, "doc": self.doc, "error": self.error,
                "sent": self.sent, "online": time.time() - self.last_ok < 3 * POLL_SECONDS + 10,
                "waiting": self._q.qsize() + len(self._retry),
                "show_time": self.show_time, "old_script": self.old_script}

    def active(self) -> bool:
        """Lines are being written into a doc (keeps the app running without OBS)."""
        return bool(self.url) and self.writing is True

    # ---- captions ----------------------------------------------------------
    def add(self, stamp: str, lang: str, transcript: str, caption: str) -> None:
        if not self.url or self.writing is False:
            return  # not linked, or Stop was pressed in the sidebar
        try:
            self._q.put_nowait({"t": stamp, "lang": lang, "src": transcript, "out": caption})
            self._wake.set()
        except queue.Full:
            pass

    # ---- background sender -----------------------------------------------
    def _call(self, payload: dict | None) -> dict:
        if payload is None:  # status only
            req = urllib.request.Request(self.url + "?" + urllib.parse.urlencode({"k": self.key}))
        else:
            req = urllib.request.Request(self.url, data=json.dumps({"k": self.key, **payload}).encode(),
                                         headers={"Content-Type": "application/json"})
        # Apps Script answers with a redirect to the result (urllib follows it as a GET).
        with urllib.request.urlopen(req, timeout=30, context=self._ctx) as r:
            body = r.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except ValueError:
            # A Google sign-in / error page instead of our answer
            raise RuntimeError("the script is not deployed as a web app for \"Anyone\"") from None

    def _run(self) -> None:
        backoff = 0.0
        while True:
            self._wake.wait(timeout=backoff or POLL_SECONDS)
            self._wake.clear()
            if not self.url:
                continue
            lines, self._retry = self._retry, []
            while len(lines) < BATCH:
                try:
                    lines.append(self._q.get_nowait())
                except queue.Empty:
                    break
            cmd, self._cmd = self._cmd, {}
            try:
                r = self._call({"lines": lines, **cmd} if lines or cmd else None)
                if not r.get("ok"):
                    raise RuntimeError(r.get("error") or "the doc refused the lines")
                self.writing = bool(r.get("writing"))
                self.doc = r.get("doc") or ""
                self.old_script = "showTime" not in r
                self.show_time = r.get("showTime", True)
                if lines and self.writing:
                    self.sent += len(lines)
                self.error, self.last_ok, backoff = "", time.time(), 0.0
                if not self._q.empty():
                    self._wake.set()
            except Exception as e:
                self._retry = lines[-500:]  # sent first next time, in the same order
                self._cmd = {**cmd, **self._cmd}
                self.error = str(e) if isinstance(e, RuntimeError) else "can't reach Google (offline?)"
                log.warning("Google Docs: %s", e)
                backoff = min(60.0, (backoff or 2.0) * 2)
