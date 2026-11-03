"""Builds the Live Captions context graph.

  python context-graph/build.py        (from the project folder; any Python 3.9+, no packages)

Reads:  context-graph/requirements.py   (what was asked for: edit by hand)
        app/livecaptions/*.py           (files, imports, window routes)
        tests/*.py                      (which tests check which files)
        docs/ARCHITECTURE.md            (decisions and test results)
        git tags                        (releases)
Writes: context-graph/graph.json        (nodes + edges, for coding agents and tools)
        context-graph/vault/            (one note per node with [[links]]: open as an Obsidian vault)
        context-graph/OVERVIEW.md       (Mermaid map: requests -> features -> files)

Every edge has a confidence: 1.0 = written by hand or read from code; 0.6 = matched by keyword.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PKG = ROOT / "app" / "livecaptions"
sys.path.insert(0, str(HERE))
from requirements import CONSTRAINTS, FEATURES, REQUIREMENTS  # noqa: E402

nodes: dict[str, dict] = {}
edges: list[dict] = []


def node(nid: str, kind: str, name: str, **info) -> str:
    nodes.setdefault(nid, {"id": nid, "type": kind, "name": name, **info})
    return nid


def edge(src: str, rel: str, dst: str, confidence: float = 1.0) -> None:
    if src in nodes and dst in nodes and src != dst and not any(
            e["source"] == src and e["target"] == dst and e["type"] == rel for e in edges):
        edges.append({"source": src, "type": rel, "target": dst, "confidence": confidence})


def file_id(path: str) -> str:
    """'meaning.py' -> 'file:app/livecaptions/meaning.py'; '/AGENTS.md' -> 'file:AGENTS.md'."""
    rel = path[1:] if path.startswith("/") else f"app/livecaptions/{path}"
    return "file:" + rel


def table(md: str, heading: str) -> list[list[str]]:
    """Rows of the first Markdown table under a '## ...heading' line."""
    part = md.split(heading, 1)[1] if heading in md else ""
    rows = []
    for line in part.splitlines()[1:]:
        if line.startswith("## "):
            break
        if line.startswith("|") and not re.match(r"^\|[-| ]+\|$", line):
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:]  # without the header


def keyword_links(nid: str, text: str, rel: str) -> None:
    """Link a decision/test row to the features whose keywords it mentions (confidence 0.6)."""
    low = text.lower()
    for fid, (name, *_rest, words) in FEATURES.items():
        if any(re.search(rf"\b{re.escape(w)}", low) for w in words):
            edge(nid, rel, "feature:" + fid, 0.6)


# ---- what was asked for ---------------------------------------------------
for cid, text in CONSTRAINTS.items():
    node("constraint:" + cid, "constraint", text)
for fid, (name, does, files, cons, words) in FEATURES.items():
    node("feature:" + fid, "feature", name, does=does)
    for c in cons:
        edge("feature:" + fid, "must_respect", "constraint:" + c)
for rid, (date, text, status, feats, note) in REQUIREMENTS.items():
    node("req:" + rid, "requirement", text, date=date, status=status, note=note)
    for f in feats:
        edge("req:" + rid, "answered_by", "feature:" + f)

# ---- the code ---------------------------------------------------------------
for p in sorted(PKG.glob("*.py")) + [PKG / "dock.html", PKG / "data/overlay.html", PKG / "data/google-docs/LiveCaptions.gs"]:
    rel = p.relative_to(ROOT).as_posix()
    if p.exists() and p.name != "__init__.py":
        first = (ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or "").split("\n")[0] if p.suffix == ".py" else ""
        node("file:" + rel, "file", rel, lines=len(p.read_text(encoding="utf-8").splitlines()), summary=first)
for fid, (_n, _d, files, *_r) in FEATURES.items():
    for f in files:
        rel = file_id(f)[5:]
        if (ROOT / rel).exists():
            node("file:" + rel, "file", rel)
            edge("feature:" + fid, "implemented_in", "file:" + rel)
        else:
            print(f"warning: {fid} names a missing file {rel}")


def imports_of(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(n, ast.ImportFrom) and (n.level == 1 or (n.module or "").startswith("livecaptions")):
            mod = (n.module or "").replace("livecaptions", "").strip(".")
            out.update([mod] if mod else [a.name for a in n.names])
    return out


for p in sorted(PKG.glob("*.py")):
    for mod in imports_of(p):
        edge(file_id(p.name), "imports", file_id(mod + ".py"))

# Window routes ("/style", "/mode", ...) served by translator.py
routes = sorted(set(re.findall(r'url\.path (?:==|in) \(?"(/[a-z/]*)"', (PKG / "translator.py").read_text(encoding="utf-8"))))
ROUTE_FEATURE = {"/style": "caption-styles", "/mode": "caption-modes", "/mic": "mic-control", "/captions": "mic-control",
                 "/speech": "speech", "/gdocs": "google-docs", "/session": "sessions", "/setup": "model-download"}
for r in routes:
    node("route:" + r, "route", r)
    edge("route:" + r, "served_by", "file:app/livecaptions/translator.py")
    for prefix, fid in ROUTE_FEATURE.items():
        if r.startswith(prefix):
            edge("route:" + r, "part_of", "feature:" + fid)

# Tests: what they import, and the feature keywords in their docstring
for p in sorted((ROOT / "tests").glob("*.py")):
    rel = p.relative_to(ROOT).as_posix()
    doc = (ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or "").split("\n")[0]
    node("test:" + rel, "test", rel, summary=doc)
    src = p.read_text(encoding="utf-8")
    for mod in set(re.findall(r"from livecaptions(?:\.(\w+))? import (\w+)", src)):
        name = mod[0] or mod[1]
        edge("test:" + rel, "tests", file_id(name + ".py"))
    keyword_links("test:" + rel, doc + " " + p.stem.replace("_", " "), "checks")

# ---- decisions and evidence (docs/ARCHITECTURE.md) --------------------------
arch = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
for i, (decision, why, revisit) in enumerate(r[:3] for r in table(arch, "## 4. Decisions")):
    nid = node(f"decision:D{i + 1:02d}", "decision", re.sub(r"[`*]", "", decision), why=why, revisit_when=revisit)
    keyword_links(nid, decision + " " + why, "about")
for i, row in enumerate(table(arch, "## 5. What has been tested")):
    claim, how, date, conf = (row + [""] * 4)[:4]
    nid = node(f"evidence:E{i + 1:02d}", "evidence", re.sub(r"[`*]", "", claim), how=how, date=date, confidence=conf)
    keyword_links(nid, claim + " " + how, "proves")
    for t in re.findall(r"tests/(\w+\.py)", how):
        edge(nid, "proved_by", "test:tests/" + t)

# ---- releases ---------------------------------------------------------------
try:
    tags = subprocess.run(["git", "tag", "--sort=v:refname", "-l", "v*"], cwd=ROOT, capture_output=True,
                          text=True, timeout=10).stdout.split()
except Exception:
    tags = []
for prev, tag in zip([None] + tags, tags):
    node("release:" + tag, "release", tag)
    if prev:
        edge("release:" + tag, "follows", "release:" + prev)
if tags:  # the requirement that shipped in the newest release
    edge("req:R21", "shipped_in", "release:" + tags[-1])

# ---- write ------------------------------------------------------------------
graph = {"about": "Live Captions context graph: requests -> features -> files/tests/decisions. Built by context-graph/build.py.",
         "nodes": list(nodes.values()), "edges": edges}
(HERE / "graph.json").write_text(json.dumps(graph, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

FOLDER = {"requirement": "1 Requests", "feature": "2 Features", "constraint": "3 Rules", "file": "4 Files",
          "route": "5 Window routes", "test": "6 Tests", "decision": "7 Decisions", "evidence": "8 Evidence",
          "release": "9 Releases"}
REL_WORDS = {"answered_by": "answered by", "must_respect": "must respect", "implemented_in": "built in",
             "imports": "uses", "served_by": "served by", "part_of": "part of", "tests": "tests", "checks": "checks",
             "about": "about", "proves": "is evidence for", "proved_by": "proved by", "follows": "comes after",
             "shipped_in": "shipped in"}


def title(n: dict) -> str:
    base = {"requirement": n["id"][4:], "constraint": n["id"][11:], "decision": n["id"][9:],
            "evidence": n["id"][9:]}.get(n["type"])
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', "-", n["name"])[:70].strip(" -")
    return f"{base} {name}" if base else name


vault = HERE / "vault"
shutil.rmtree(vault, ignore_errors=True)
link = {nid: f"[[{title(n)}]]" for nid, n in nodes.items()}
for nid, n in nodes.items():
    out_e = [e for e in edges if e["source"] == nid]
    in_e = [e for e in edges if e["target"] == nid]
    meta = {k: v for k, v in n.items() if k not in ("id", "name") and v not in ("", None)}
    lines = ["---", f"id: {nid}", *(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items()), "---",
             f"# {n['name']}", ""]
    for k in ("does", "note", "summary", "why", "revisit_when", "how"):
        if n.get(k):
            lines.append(f"**{k.replace('_', ' ')}:** {n[k]}\n")
    if out_e:
        lines += ["## Links", *(f"- {REL_WORDS[e['type']]} {link[e['target']]}"
                                + ("" if e["confidence"] == 1 else " *(keyword match)*") for e in out_e), ""]
    if in_e:
        lines += ["## Linked from", *(f"- {link[e['source']]} ({REL_WORDS[e['type']]})" for e in in_e), ""]
    d = vault / FOLDER[n["type"]]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{title(n)}.md").write_text("\n".join(lines), encoding="utf-8")

# Start page of the vault
start = ["# Live Captions: context graph", "",
         "Every request, the feature that answers it, the files, tests, decisions and evidence behind it.",
         "Rebuild with `python context-graph/build.py` after a change.", "", "## Requests", ""]
for rid, (date, text, status, *_r) in REQUIREMENTS.items():
    start.append(f"- {link['req:' + rid]} · {date} · **{status}**")
start += ["", "## Rules for every change", *(f"- {link['constraint:' + c]}" for c in CONSTRAINTS), ""]
(vault / "0 Start here.md").write_text("\n".join(start), encoding="utf-8")

# Mermaid overview
STATUS_CLASS = {"done": "done", "partial": "partial", "changed": "changed", "dropped": "changed"}
m = ["# Live Captions: context graph overview", "",
     "Requests (left) → features (middle) → main files (right). Full graph: `graph.json`; notes: `vault/`",
     "(open the folder in Obsidian). Green = done, amber = partly done, grey = changed.", "",
     "Ask it questions: `python context-graph/query.py R21` · `query.py meaning.py` · `query.py --open`", "",
     "![Overview](overview.png)", "",
     "<details><summary>Mermaid source (renders on GitHub)</summary>", "",
     "```mermaid", "flowchart LR"]
for rid, (date, text, status, *_r) in REQUIREMENTS.items():
    short = text if len(text) <= 38 else text[:36].rsplit(" ", 1)[0] + "…"
    m.append(f'  {rid}["{rid} {short}"]:::{STATUS_CLASS[status]}')
for fid, (name, *_r) in FEATURES.items():
    m.append(f'  F_{fid.replace("-", "_")}(["{name}"])')
for rid, (_d, _t, _s, feats, _n) in REQUIREMENTS.items():
    for f in feats:
        m.append(f'  {rid} --> F_{f.replace("-", "_")}')
for fid, (_n, _d, files, *_r) in FEATURES.items():
    for f in files:
        if not f.startswith("/") and f.endswith(".py"):
            m.append(f'  F_{fid.replace("-", "_")} --> {f.replace(".", "_")}[/{f}/]')
m += ["  classDef done fill:#173326,stroke:#4cc38a,color:#e8e9ec",
      "  classDef partial fill:#3a2f14,stroke:#f0b54a,color:#e8e9ec",
      "  classDef changed fill:#2e3038,stroke:#9aa0aa,color:#c9ccd3", "```", "", "</details>", "",
      "Picture: `npx @mermaid-js/mermaid-cli -i <the block above> -o context-graph/overview.png -t dark -b '#1e1f24' -s 2`", ""]
open_reqs = [(rid, t, n) for rid, (_d, t, s, _f, n) in REQUIREMENTS.items() if s == "partial"]
if open_reqs:
    m += ["## Still open", "", *(f"- **{rid}** {t}: {n}" for rid, t, n in open_reqs), ""]
weak = [n for n in nodes.values() if n["type"] == "evidence" and re.search(r"medium|untested|not yet|not re-tested", n.get("confidence", ""))]
if weak:
    m += ["## Not proven yet", "", *(f"- {n['name']}: {n['confidence']}" for n in weak), ""]
counts = {}
for n in nodes.values():
    counts[n["type"]] = counts.get(n["type"], 0) + 1
m += ["## Size", "", ", ".join(f"{v} {k}s" for k, v in counts.items()) + f", {len(edges)} links.", ""]
(HERE / "OVERVIEW.md").write_text("\n".join(m), encoding="utf-8")

# Checks: every requirement reaches code; nothing is left unlinked
problems = []
for rid in REQUIREMENTS:
    feats = [e["target"] for e in edges if e["source"] == "req:" + rid and e["type"] == "answered_by"]
    if not any(e["source"] in feats and e["type"] == "implemented_in" for e in edges):
        problems.append(f"{rid} reaches no file")
for nid, n in nodes.items():
    if not any(nid in (e["source"], e["target"]) for e in edges):
        problems.append(f"{nid} has no links")
print(f"{len(nodes)} nodes, {len(edges)} links -> context-graph/graph.json, vault/ ({len(nodes) + 1} notes), OVERVIEW.md")
print("\n".join("check: " + p for p in problems) if problems else "check: every request reaches code; no unlinked nodes")
