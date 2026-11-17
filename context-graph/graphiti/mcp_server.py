"""MCP server (stdio) so coding agents can ask the Graphiti memory graph and add to it.

Cursor: ~/.cursor/mcp.json -> "live-captions-memory": {"command": "<repo>/context-graph/graphiti/.venv/bin/python",
                                                       "args": ["<repo>/context-graph/graphiti/mcp_server.py"]}
"""
from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

from common import GROUP, make_graphiti, redact

mcp = MCPServer("live-captions-memory", instructions=(
    "Long-term memory of the Live Captions project (github.com/vivekarya2026/live-captions-obs): user requests, "
    "features, files, decisions, docs, every commit and past agent chats, with dates. Facts carry valid/invalid "
    "dates, so superseded facts show as ended. Search before changing behaviour or answering 'why/when' questions; "
    "add a memory after finishing a change or learning a decision."))
_g = None


async def graph():
    global _g
    if _g is None:
        _g = make_graphiti()
        await _g.build_indices_and_constraints()
    return _g


def _d(x: datetime | None) -> str:
    return x.strftime("%Y-%m-%d") if x else "?"


@mcp.tool()
async def search_facts(query: str, limit: int = 10) -> str:
    """Facts (relationships) about the project matching a question, newest-valid first, with their dates.
    Example: "why is Qwen 1.7B the default speech model"."""
    g = await graph()
    edges = await g.search(query, group_ids=[GROUP], num_results=max(1, min(limit, 50)))
    if not edges:
        return "No matching facts."
    return "\n".join(f"- {e.fact}  (valid {_d(e.valid_at)}" + (f" until {_d(e.invalid_at)}" if e.invalid_at else "")
                     + ")" for e in edges)


@mcp.tool()
async def search_entities(query: str, limit: int = 8) -> str:
    """Things in the project (features, files, models, people, decisions) matching a query, with summaries."""
    from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
    g = await graph()
    cfg = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
    cfg.limit = max(1, min(limit, 30))
    res = await g.search_(query, config=cfg, group_ids=[GROUP])
    if not res.nodes:
        return "No matching entities."
    return "\n".join(f"- {n.name}: {n.summary}" for n in res.nodes)


@mcp.tool()
async def recent_memories(count: int = 10) -> str:
    """The most recent episodes (commits, chats, notes) added to the memory graph."""
    g = await graph()
    eps = await g.retrieve_episodes(datetime.now(timezone.utc), last_n=max(1, min(count, 50)), group_ids=[GROUP])
    return "\n".join(f"- {_d(e.valid_at)}  {e.name}" for e in sorted(eps, key=lambda e: e.valid_at, reverse=True)) \
        or "Memory graph is empty."


@mcp.tool()
async def add_memory(name: str, text: str, source: str = "agent note") -> str:
    """Save something worth remembering (a decision, a fix and its cause, a user preference) as dated memory.
    Write it as plain sentences; takes ~10-30 s while facts are extracted."""
    from graphiti_core.nodes import EpisodeType
    g = await graph()
    r = await g.add_episode(name=name[:200], episode_body=redact(text)[:8000], source_description=source,
                            reference_time=datetime.now(timezone.utc), source=EpisodeType.text, group_id=GROUP)
    return f"Saved '{name}': {len(r.nodes)} entities, {len(r.edges)} facts."


if __name__ == "__main__":
    mcp.run()
