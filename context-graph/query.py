"""Ask the context graph a question (no packages needed).

  python context-graph/query.py R21           what a request touches: features, files, tests, evidence
  python context-graph/query.py meaning.py    which requests a file serves, and what checks it
  python context-graph/query.py style         anything whose name matches
  python context-graph/query.py --open        requests not fully done, and claims not yet proven

Coding agents: run this before changing a file, to see which requests and tests depend on it.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

G = json.loads((Path(__file__).resolve().parent / "graph.json").read_text(encoding="utf-8"))
NODES = {n["id"]: n for n in G["nodes"]}
OUT: dict[str, list] = {}
IN: dict[str, list] = {}
for e in G["edges"]:
    OUT.setdefault(e["source"], []).append(e)
    IN.setdefault(e["target"], []).append(e)


def find(q: str) -> list[str]:
    ql = q.lower()
    exact = [i for i in NODES if i.lower() in (ql, "req:" + ql) or i.lower().endswith("/" + ql)]
    return exact or [i for i, n in NODES.items() if ql in n["name"].lower() or ql in i.lower()]


def show(nid: str) -> str:
    n = NODES[nid]
    extra = n.get("status") or n.get("confidence") or ""
    return f"{n['type']:11} {n['name']}" + (f"  [{extra}]" if extra else "")


def walk(start: str, depth: int = 3) -> None:
    """Breadth-first both ways: down (request -> feature -> file) and up (file -> feature -> request)."""
    print(show(start))
    seen, q = {start}, deque([(start, 0)])
    while q:
        nid, d = q.popleft()
        if d >= depth:
            continue
        for e, other, arrow in ([(e, e["target"], "→") for e in OUT.get(nid, [])]
                                + [(e, e["source"], "←") for e in IN.get(nid, [])]):
            if other in seen or NODES[other]["type"] == "release":
                continue
            seen.add(other)
            note = "" if e["confidence"] == 1 else " (keyword match)"
            print("  " * (d + 1) + f"{arrow} {e['type']}: {show(other)}{note}")
            # Expand only through features: hub files (translator.py) would list everything
            if NODES[other]["type"] == "feature" or (NODES[other]["type"] == "requirement" and d == 0):
                q.append((other, d + 1))


def main(argv: list[str]) -> None:
    if not argv:
        print(__doc__)
        return
    if argv[0] == "--open":
        for n in G["nodes"]:
            if n["type"] == "requirement" and n["status"] != "done":
                print(f"{n['id'][4:]} [{n['status']}] {n['name']}: {n.get('note', '')}")
        for n in G["nodes"]:
            c = n.get("confidence", "")
            if n["type"] == "evidence" and any(w in c for w in ("medium", "untested", "not yet", "not re-tested")):
                print(f"not proven: {n['name']}: {c}")
        return
    hits = find(" ".join(argv))
    if not hits:
        print("nothing matches; try a request id (R21), a file (meaning.py) or a word (style)")
    for h in hits[:3]:
        walk(h, depth=2 if NODES[h]["type"] == "file" else 3)
        print()
    if len(hits) > 3:
        print("also matches: " + ", ".join(NODES[h]["name"] for h in hits[3:12]))


if __name__ == "__main__":
    main(sys.argv[1:])
