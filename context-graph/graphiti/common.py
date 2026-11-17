"""Shared setup for the Graphiti memory graph: Gemini for extraction + search, embedded FalkorDB file.

Settings come from context-graph/graphiti/.env (never committed):
  GEMINI_API_KEY=...                    required (https://aistudio.google.com/apikey)
  GRAPHITI_LLM_MODEL=gemini-2.5-flash   optional
  GRAPHITI_SMALL_MODEL=gemini-2.5-flash-lite
"""
from __future__ import annotations

import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / "data"
DB_FILE = DATA / "graph.db"
GROUP = "live-captions"


def load_env() -> None:
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and not k.strip().startswith("#"):
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def make_graphiti():
    load_env()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(f"GEMINI_API_KEY missing: add it to {HERE / '.env'}")
    os.environ.setdefault("SEMAPHORE_LIMIT", "4")  # stay under Gemini's per-minute limits
    from graphiti_core import Graphiti
    from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
    from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
    from redislite.async_falkordb_client import AsyncFalkorDB

    DATA.mkdir(exist_ok=True)
    small = os.environ.get("GRAPHITI_SMALL_MODEL", "gemini-2.5-flash-lite")
    return Graphiti(
        graph_driver=FalkorDriver(falkor_db=AsyncFalkorDB(str(DB_FILE)), database=GROUP.replace("-", "_")),
        llm_client=GeminiClient(config=LLMConfig(
            api_key=key, model=os.environ.get("GRAPHITI_LLM_MODEL", "gemini-2.5-flash"), small_model=small)),
        embedder=GeminiEmbedder(config=GeminiEmbedderConfig(api_key=key, embedding_model="gemini-embedding-001")),
        cross_encoder=GeminiRerankerClient(config=LLMConfig(api_key=key, model=small)),
    )


_SECRETS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),                      # Google API keys
    re.compile(r"ya29\.[0-9A-Za-z_\-\.]+"),                       # Google OAuth tokens
    re.compile(r"\b(gh[pousr]_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_\-]{20,})"),
    re.compile(r"-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----"),
    re.compile(r"https://script\.google\.com/macros/s/[0-9A-Za-z_\-]+"),  # the doc's Web app URL is a password
    re.compile(r"\b[0-9A-Za-z+/]{60,}={0,2}"),                    # long base64 blobs (certs, keys)
]
_ASSIGNED = re.compile(r"(?i)((?:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)\S+")


def redact(text: str) -> str:
    for rx in _SECRETS:
        text = rx.sub("[redacted]", text)
    return _ASSIGNED.sub(r"\1[redacted]", text)
