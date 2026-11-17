"""Load the project's history into the Graphiti memory graph (incremental: re-run any time).

  context-graph/graphiti/.venv/bin/python context-graph/graphiti/ingest.py            everything new
  ... ingest.py --dry-run                 list what would be added, no API calls
  ... ingest.py --only git,docs --limit 5 some sources, first N new episodes

Sources, added oldest first so later facts supersede earlier ones:
  cg     context-graph/graph.json: one episode per request and per feature
  docs   AGENTS.md, docs/*.md: one episode per "## " section
  git    one episode per commit (message + files changed)
  chats  Cursor chats about this project: one episode per user request + the agent's final reply
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import DATA, GROUP, REPO, make_graphiti, redact

STATE = DATA / "ingested.json"
CHAT_GLOBS = [str(Path.home() / ".cursor/projects/*-Devs-OCR/agent-transcripts/*/*.jsonl"),
              str(Path.home() / ".cursor/projects/*live-captions-obs/agent-transcripts/*/*.jsonl")]
MAX_BODY = 6000


def _dt(s: str) -> datetime:
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def from_context_graph() -> list[dict]:
    g = json.loads((REPO / "context-graph/graph.json").read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in g["nodes"]}
    out_e: dict[str, list] = {}
    in_e: dict[str, list] = {}
    for e in g["edges"]:
        out_e.setdefault(e["source"], []).append(e)
        in_e.setdefault(e["target"], []).append(e)

    def linked(nid: str, etype: str, incoming: bool = False) -> list[dict]:
        es = in_e.get(nid, []) if incoming else out_e.get(nid, [])
        return [nodes[e["source"] if incoming else e["target"]] for e in es if e["type"] == etype]

    eps = []
    for r in (n for n in g["nodes"] if n["type"] == "requirement"):
        feats = linked(r["id"], "answered_by")
        body = (f"User request {r['id'][4:]} ({r['date']}, status {r['status']}): {r['name']}. {r.get('note', '')}\n"
                + "".join(f"Answered by feature '{f['name']}': {f.get('does', '')}\n" for f in feats))
        eps.append(dict(key=f"cg:{r['id']}", name=f"Request {r['id'][4:]}: {r['name']}", body=body,
                        when=_dt(r["date"]), source="context graph request"))
    for f in (n for n in g["nodes"] if n["type"] == "feature"):
        reqs = linked(f["id"], "answered_by", incoming=True)
        lines = [f"Feature '{f['name']}' of Live Captions: {f.get('does', '')}"]
        lines += [f"Requested in {r['id'][4:]}: {r['name']}" for r in reqs]
        lines += [f"Implemented in file {x['name']}" + (f" ({x['summary']})" if x.get("summary") else "")
                  for x in linked(f["id"], "implemented_in")]
        lines += [f"Must respect constraint: {c['name']}" for c in linked(f["id"], "must_respect")]
        lines += [f"Decision '{d['name']}': {d.get('why', '')}. Revisit when {d.get('revisit_when', 'n/a')}"
                  for d in linked(f["id"], "about", incoming=True)]
        lines += [f"Proven by evidence '{e['name']}' ({e.get('how', '')}, confidence {e.get('confidence', '?')})"
                  for e in linked(f["id"], "proves", incoming=True)]
        lines += [f"Checked by test {t['name']}" for t in linked(f["id"], "checks", incoming=True)]
        lines += [f"Served on route {r['name']}" for r in linked(f["id"], "part_of", incoming=True)]
        when = min((_dt(r["date"]) for r in reqs), default=datetime.now(timezone.utc))
        eps.append(dict(key=f"cg:{f['id']}", name=f"Feature: {f['name']}", body="\n".join(lines),
                        when=when, source="context graph feature"))
    return eps


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def from_docs() -> list[dict]:
    files = [REPO / "AGENTS.md", *sorted((REPO / "docs").rglob("*.md"))]
    eps = []
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        when = _dt(_git("log", "-1", "--format=%aI", "--", rel).strip() or datetime.now(timezone.utc).isoformat())
        text = path.read_text(encoding="utf-8")
        for i, part in enumerate(re.split(r"(?m)^(?=## )", text)):
            part = part.strip()
            if len(part) < 80:
                continue
            title = part.splitlines()[0].lstrip("# ").strip()
            for j in range(0, len(part), MAX_BODY):
                chunk = part[j:j + MAX_BODY]
                digest = hashlib.sha1(chunk.encode()).hexdigest()[:10]  # edited sections become new episodes
                eps.append(dict(key=f"docs:{rel}:{i}:{j}:{digest}", name=f"{rel} - {title}",
                                body=f"From {rel}, section '{title}':\n{chunk}", when=when,
                                source=f"project documentation {rel}"))
    return eps


def from_git() -> list[dict]:
    eps = []
    for block in _git("log", "--reverse", "--format=\x1e%H\x1f%aI\x1f%B\x1f", "--name-only").split("\x1e")[1:]:
        sha, date, msg, files = block.split("\x1f")
        files = [f for f in files.split() if f]
        body = (f"Commit {sha[:7]} on {date[:10]}: {msg.strip()}\nFiles changed: {', '.join(files[:40])}"
                + (f" (+{len(files) - 40} more)" if len(files) > 40 else ""))
        eps.append(dict(key=f"git:{sha}", name=f"Commit {sha[:7]}: {msg.strip().splitlines()[0][:80]}",
                        body=body, when=_dt(date), source="git commit"))
    return eps


_TS = re.compile(r"<timestamp>(.*?)</timestamp>")
_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
_SKIP = ("Briefly inform the user", "continue")


def _chat_time(stamp: str) -> datetime | None:
    m = re.match(r"\w+, (\w+ \d+, \d{4}), (\d+:\d+ [AP]M) \(UTC([+-]\d+)\)", stamp)
    if not m:
        return None
    d = datetime.strptime(f"{m[1]} {m[2]}", "%b %d, %Y %I:%M %p")
    return d.replace(tzinfo=timezone.utc) - timedelta(hours=int(m[3]))


def _text(msg: dict) -> str:
    return "\n".join(c.get("text", "") for c in msg.get("message", {}).get("content", []) if c.get("type") == "text")


def from_chats() -> list[dict]:
    eps = []
    for path in sorted({p for g in CHAT_GLOBS for p in glob.glob(g)}):
        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        chat = Path(path).stem[:8]
        last_time = None
        for i, row in enumerate(rows):
            if row.get("role") != "user":
                continue
            raw = _text(row)
            q = _QUERY.search(raw)
            if not q or q[1].strip().startswith(_SKIP):
                continue
            ts = _TS.search(raw)
            last_time = (_chat_time(ts[1]) if ts else None) or last_time
            reply = ""
            for nxt in rows[i + 1:]:
                if nxt.get("role") == "user":
                    break
                if nxt.get("role") == "assistant" and _text(nxt).strip():
                    reply = _text(nxt).strip()
            request = q[1].strip()
            body = (f"The user asked the coding agent (Live Captions project): {request[:2500]}\n\n"
                    f"The agent's final reply: {reply[:3000]}")
            eps.append(dict(key=f"chat:{chat}:{i}", name=f"Chat {chat}: {request.splitlines()[0][:80]}",
                            body=body, when=last_time or datetime.now(timezone.utc), source="agent chat"))
    return eps


SOURCES = {"cg": from_context_graph, "docs": from_docs, "git": from_git, "chats": from_chats}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(SOURCES))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    done = set(json.loads(STATE.read_text())) if STATE.exists() else set()
    eps = [e for s in a.only.split(",") for e in SOURCES[s.strip()]() if e["key"] not in done]
    eps.sort(key=lambda e: e["when"])
    if a.limit:
        eps = eps[:a.limit]
    print(f"{len(eps)} new episodes ({len(done)} already in the graph)")
    if a.dry_run:
        for e in eps:
            print(f"  {e['when']:%Y-%m-%d}  {e['name'][:100]}")
        return

    from graphiti_core.nodes import EpisodeType
    g = make_graphiti()
    await g.build_indices_and_constraints()
    fails = 0
    try:
        for n, e in enumerate(eps, 1):
            t = time.time()
            try:
                await g.add_episode(name=e["name"][:200], episode_body=redact(e["body"])[:MAX_BODY + 500],
                                    source_description=e["source"], reference_time=e["when"],
                                    source=EpisodeType.text, group_id=GROUP)
            except Exception as ex:  # quota / transient API errors: keep what's done, resume next run
                fails += 1
                print(f"[{n}/{len(eps)}] FAILED {e['name'][:70]}: {str(ex)[:200]}", flush=True)
                if fails >= 3:
                    print("Stopping after 3 failures in a row (Gemini quota?). Re-run later to resume.")
                    break
                await asyncio.sleep(30)
                continue
            fails = 0
            done.add(e["key"])
            DATA.mkdir(exist_ok=True)
            STATE.write_text(json.dumps(sorted(done)))
            print(f"[{n}/{len(eps)}] {time.time() - t:4.1f}s  {e['name'][:90]}", flush=True)
    finally:
        await g.close()


if __name__ == "__main__":
    asyncio.run(main())
