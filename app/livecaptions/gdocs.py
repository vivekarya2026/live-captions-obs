"""Writes captions into Google Docs, with "Sign in with Google" (no script in the doc).

1. Sign in: the app opens Google's sign-in page in the browser. Google sends the
   browser back to http://127.0.0.1:8765/gdocs/oauth with a one-time code, which
   we swap for a token (OAuth for desktop apps, with PKCE).
2. The only permission asked is "drive.file": the app can see and edit only the
   docs it created itself, nothing else in the user's Drive.
3. Start writing: a new doc "Live Captions · <date>" is made for each session
   (New session in the window = next doc) and each sentence is added at its end.

The OAuth client (made once by the maintainer in Google Cloud, type "Desktop app")
is read from, in order: $LIVECAPTIONS_GOOGLE_CLIENT, ~/.livecaptions/google_oauth_client.json,
or the copy bundled into the installer (data/google-docs/oauth_client.json, added by CI).
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import logging
import os
import queue
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import paths

log = logging.getLogger("gdocs")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DOCS_API = "https://docs.googleapis.com/v1/documents"
SCOPE = "https://www.googleapis.com/auth/drive.file"

ACCOUNT = paths.DATA / "google_account.json"   # refresh token + settings (this computer only)
OLD_CONFIG = paths.DATA / "google_docs.json"     # the old Apps Script link (no longer used)
BATCH = 20
IDLE_SECONDS = 5


def _client_files() -> list[Path]:
    env = os.environ.get("LIVECAPTIONS_GOOGLE_CLIENT")
    return ([Path(env)] if env else []) + [paths.DATA / "google_oauth_client.json",
                                           paths.RESOURCES / "google-docs" / "oauth_client.json"]


def load_client() -> tuple[str, str] | None:
    """-> (client_id, client_secret) from the JSON Google lets you download, or None."""
    for f in _client_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        d = d.get("installed") or d.get("web") or d
        if d.get("client_id"):
            return d["client_id"], d.get("client_secret", "")
    return None


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # the bundled Python has no system certificates on macOS
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _u16(s: str) -> int:
    """Length the way Google Docs counts it (UTF-16 code units)."""
    return len(s.encode("utf-16-le")) // 2


class GoogleError(RuntimeError):
    pass


class GoogleDocs:
    def __init__(self) -> None:
        self.client = load_client()
        self.refresh_token = ""
        self.show_time = True
        self.writing = False
        self.doc_id = ""
        self.doc_title = ""
        self.error = ""
        self.sent = 0
        self._access = ("", 0.0)       # (token, expires at)
        self._pending: dict = {}       # sign-in in progress: state, verifier, redirect
        self._new_doc = True           # next Start makes a new doc
        self._q: "queue.Queue[dict]" = queue.Queue(maxsize=2000)
        self._retry: list[dict] = []
        self._wake = threading.Event()
        self._ctx = _ssl_context()
        try:
            a = json.loads(ACCOUNT.read_text(encoding="utf-8"))
            self.refresh_token = a.get("refresh_token", "")
            self.show_time = a.get("show_time", True)
        except (OSError, ValueError):
            pass
        OLD_CONFIG.unlink(missing_ok=True)
        threading.Thread(target=self._run, daemon=True).start()

    # ---- saved settings ---------------------------------------------------
    def _save(self) -> None:
        ACCOUNT.parent.mkdir(parents=True, exist_ok=True)
        tmp = ACCOUNT.with_suffix(".tmp")
        tmp.write_text(json.dumps({"refresh_token": self.refresh_token, "show_time": self.show_time}),
                       encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)  # the token only for this user
        except OSError:
            pass
        os.replace(tmp, ACCOUNT)

    # ---- sign in ------------------------------------------------------------
    def sign_in_url(self, redirect: str) -> str:
        """Google's sign-in page for this computer; the browser comes back to `redirect`."""
        if not self.client:
            raise GoogleError("Google sign-in isn't set up in this version of the app")
        verifier = secrets.token_urlsafe(48)
        state = secrets.token_urlsafe(24)
        self._pending = {"state": state, "verifier": verifier, "redirect": redirect, "at": time.time()}
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        return AUTH_URL + "?" + urllib.parse.urlencode({
            "client_id": self.client[0], "redirect_uri": redirect, "response_type": "code",
            "scope": SCOPE, "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent"})

    def expects(self, state: str) -> bool:
        """Is this the answer to the sign-in we started (within 10 minutes)?"""
        p = self._pending
        return bool(p) and bool(state) and secrets.compare_digest(state, p["state"]) \
            and time.time() - p["at"] < 600

    def finish_sign_in(self, state: str, code: str, error: str = "") -> str:
        """Called with what Google sent back. -> "" or the problem."""
        if not self.expects(state):
            return "This sign-in link is old. Press Sign in with Google again."
        p, self._pending = self._pending, {}
        if error or not code:
            return "Sign-in was cancelled." if error == "access_denied" else f"Google said: {error or 'no code'}"
        try:
            r = self._post_form(TOKEN_URL, {
                "client_id": self.client[0], "client_secret": self.client[1], "code": code,
                "code_verifier": p["verifier"], "redirect_uri": p["redirect"],
                "grant_type": "authorization_code"})
        except GoogleError as e:
            return str(e)
        if not r.get("refresh_token"):
            return "Google gave no lasting access. Press Sign in with Google again."
        self.refresh_token = r["refresh_token"]
        self._access = (r.get("access_token", ""), time.time() + int(r.get("expires_in", 0)) - 60)
        self.error = ""
        self._save()
        self._wake.set()
        return ""

    def sign_out(self) -> None:
        tok, self.refresh_token = self.refresh_token, ""
        self.writing, self.doc_id, self.doc_title, self._access = False, "", "", ("", 0.0)
        self._new_doc, self.error = True, ""
        self._save()
        if tok:  # also cancel the access at Google (best effort)
            threading.Thread(target=self._revoke, args=(tok,), daemon=True).start()

    def _revoke(self, tok: str) -> None:
        try:
            self._post_form("https://oauth2.googleapis.com/revoke", {"token": tok})
        except Exception:
            pass

    # ---- from the app window -------------------------------------------------
    def command(self, writing: bool | None = None, show_time: bool | None = None) -> None:
        if writing is not None and self.refresh_token:
            self.writing = writing
        if show_time is not None:
            self.show_time = show_time
            self._save()
        self._wake.set()

    def new_session(self) -> None:
        """New session in the window: the next lines go into a new doc."""
        self._new_doc = True
        self._wake.set()

    def doc_url(self) -> str:
        return f"https://docs.google.com/document/d/{self.doc_id}/edit" if self.doc_id else ""

    def status(self) -> dict:
        return {"configured": bool(self.client), "signed_in": bool(self.refresh_token),
                "writing": self.writing, "doc": self.doc_title, "doc_url": self.doc_url(),
                "error": self.error, "sent": self.sent, "show_time": self.show_time,
                "waiting": self._q.qsize() + len(self._retry)}

    def active(self) -> bool:
        """Lines are being written into a doc (keeps the app running without OBS)."""
        return bool(self.refresh_token) and self.writing

    def add(self, stamp: str, lang: str, transcript: str, caption: str) -> None:
        if not self.active():
            return
        try:
            self._q.put_nowait({"t": stamp, "lang": lang, "src": transcript, "out": caption})
            self._wake.set()
        except queue.Full:
            pass

    # ---- Google calls ----------------------------------------------------------
    def _request(self, req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=30, context=self._ctx) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read() or b"{}")
            except ValueError:
                body = {}
            err = body.get("error")
            msg = (err.get("message") if isinstance(err, dict) else body.get("error_description") or err) or ""
            if e.code in (400, 401) and (err == "invalid_grant" or "invalid_grant" in str(msg)):
                raise GoogleError("signed_out") from None
            if e.code == 403 and "has not been used" in str(msg):
                raise GoogleError("The Google Docs API is off in the app's Google Cloud project "
                                  "(maintainer: enable it)") from None
            raise GoogleError(f"Google error {e.code}: {msg}".strip(": ")) from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise ConnectionError(str(e)) from None

    def _post_form(self, url: str, data: dict) -> dict:
        return self._request(urllib.request.Request(
            url, data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"}))

    def _token(self) -> str:
        tok, until = self._access
        if tok and time.time() < until:
            return tok
        r = self._post_form(TOKEN_URL, {"client_id": self.client[0], "client_secret": self.client[1],
                                        "refresh_token": self.refresh_token, "grant_type": "refresh_token"})
        self._access = (r["access_token"], time.time() + int(r.get("expires_in", 3600)) - 60)
        return self._access[0]

    def _api(self, url: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + self._token(),
                                              "Content-Type": "application/json"})
        return self._request(req)

    def _create_doc(self) -> None:
        now = dt.datetime.now()
        title = "Live Captions · " + now.strftime("%-d %b %Y, %H:%M" if os.name != "nt" else "%d %b %Y, %H:%M")
        d = self._api(DOCS_API, {"title": title})
        self.doc_id, self.doc_title, self._new_doc = d["documentId"], title, False
        self.sent = 0
        log.info("Google Docs: new doc %s", title)
        heading = title + "\n"
        self._api(f"{DOCS_API}/{self.doc_id}:batchUpdate", {"requests": [
            {"insertText": {"location": {"index": 1}, "text": heading}},
            {"updateParagraphStyle": {"range": {"startIndex": 1, "endIndex": 1 + _u16(heading)},
                                      "paragraphStyle": {"namedStyleType": "HEADING_2"},
                                      "fields": "namedStyleType"}}]})

    def _append(self, lines: list[dict]) -> None:
        """Adds the lines at the end of the doc (even if someone typed in it meanwhile)."""
        d = self._api(f"{DOCS_API}/{self.doc_id}?fields=body.content.endIndex")
        at = max(1, d["body"]["content"][-1]["endIndex"] - 1)
        text, styles = "", []
        grey = {"color": {"rgbColor": {"red": .42, "green": .435, "blue": .463}}}
        dark = {"color": {"rgbColor": {"red": .12, "green": .12, "blue": .12}}}
        for l in lines:
            stamp = str(l.get("t") or "") if self.show_time else ""
            lang = str(l.get("lang") or "")
            head = " · ".join(x for x in (stamp, lang) if x)
            p1 = (head + "   " if head else "") + str(l.get("src") or "")[:2000] + "\n"
            p2 = (str(l.get("out") or "")[:2000] or " ") + "\n"
            s1 = at + _u16(text)
            s2 = s1 + _u16(p1)
            e2 = s2 + _u16(p2)
            styles += [
                {"updateParagraphStyle": {"range": {"startIndex": s1, "endIndex": e2},
                                          "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                                          "fields": "namedStyleType"}},
                {"updateTextStyle": {"range": {"startIndex": s1, "endIndex": s2},
                                     "textStyle": {"fontSize": {"magnitude": 9, "unit": "PT"},
                                                   "foregroundColor": grey, "bold": False},
                                     "fields": "fontSize,foregroundColor,bold"}},
                {"updateTextStyle": {"range": {"startIndex": s2, "endIndex": e2},
                                     "textStyle": {"fontSize": {"magnitude": 11, "unit": "PT"},
                                                   "foregroundColor": dark, "bold": False},
                                     "fields": "fontSize,foregroundColor,bold"}},
                {"updateParagraphStyle": {"range": {"startIndex": s1, "endIndex": s2},
                                          "paragraphStyle": {"spaceAbove": {"magnitude": 6, "unit": "PT"},
                                                             "spaceBelow": {"magnitude": 0, "unit": "PT"}},
                                          "fields": "spaceAbove,spaceBelow"}}]
            if head:
                styles.append({"updateTextStyle": {"range": {"startIndex": s1, "endIndex": s1 + _u16(head)},
                                                   "textStyle": {"bold": True}, "fields": "bold"}})
            text += p1 + p2
        self._api(f"{DOCS_API}/{self.doc_id}:batchUpdate", {"requests": [
            {"insertText": {"location": {"index": at}, "text": text}}] + styles})

    # ---- background writer -----------------------------------------------------
    def _run(self) -> None:
        backoff = 0.0
        while True:
            self._wake.wait(timeout=backoff or IDLE_SECONDS)
            self._wake.clear()
            if not self.active():
                continue
            lines, self._retry = self._retry, []
            while len(lines) < BATCH:
                try:
                    lines.append(self._q.get_nowait())
                except queue.Empty:
                    break
            try:
                if self._new_doc or not self.doc_id:
                    self._create_doc()
                if lines:
                    self._append(lines)
                    self.sent += len(lines)
                self.error, backoff = "", 0.0
                if not self._q.empty():
                    self._wake.set()
            except Exception as e:
                self._retry = lines[-1000:]  # sent first next time, in the same order
                if isinstance(e, GoogleError) and str(e) == "signed_out":
                    self.refresh_token, self.writing = "", False
                    self._save()
                    self.error = "Google access ended. Press Sign in with Google again."
                    continue
                self.error = str(e) if isinstance(e, GoogleError) else "can't reach Google (offline?)"
                log.warning("Google Docs: %s", e)
                backoff = min(60.0, (backoff or 2.0) * 2)
