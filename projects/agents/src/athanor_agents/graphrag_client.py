"""GraphRAG client helpers for Athanor agents.

Normalizes the FOUNDRY GraphRAG `/query/hybrid` response into the payload
shape used by context injection so GraphRAG can plug into the existing
knowledge lane without forcing the rest of agents to speak a new schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .services import registry

logger = logging.getLogger(__name__)

_GRAPHRAG_QUERY_URL = registry.graphrag.url("/query/hybrid")
_GRAPHRAG_QUERY_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class GraphRAGKnowledgeResult:
    """Normalized GraphRAG knowledge retrieval response."""

    results: list[dict]
    route: str
    warnings: list[str] = field(default_factory=list)


def _normalize_graphrag_hit(hit: dict[str, Any]) -> dict[str, Any]:
    chunk_id = str(hit.get("chunk_id") or "").strip()
    doc_id = str(hit.get("doc_id") or "").strip()
    title = str(hit.get("title") or doc_id or chunk_id or "unknown").strip()
    text = str(hit.get("text") or "").strip()
    category = str(hit.get("category") or "").strip()
    graphrag_origin = str(hit.get("source") or "").strip()
    score_value = hit.get("rrf_score", hit.get("score", 0.0))
    try:
        score = float(score_value)
    except (TypeError, ValueError):
        score = 0.0

    payload = {
        "title": title,
        "source": doc_id or chunk_id or title,
        "text": text,
        "category": category,
        "chunk_id": chunk_id,
        "chunk_index": hit.get("chunk_index"),
        "matched_entities": list(hit.get("matched_entities") or []),
        "graphrag_origin": graphrag_origin,
    }
    return {
        "id": chunk_id or doc_id or title,
        "payload": payload,
        "score": score,
        "_source": f"graphrag:{graphrag_origin or 'unknown'}",
    }


async def query_hybrid_knowledge(
    client: httpx.AsyncClient,
    query_text: str,
    top_k: int = 5,
    score_threshold: float = 0.25,
    timeout_seconds: float = _GRAPHRAG_QUERY_TIMEOUT_SECONDS,
) -> GraphRAGKnowledgeResult:
    """Call GraphRAG hybrid retrieval and normalize the result set."""
    response = await client.post(
        _GRAPHRAG_QUERY_URL,
        json={
            "query": query_text,
            "top_k": top_k,
            "route": "auto",
            "score_threshold": score_threshold,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()

    route = str(data.get("route") or "unknown").strip()
    warnings = [str(item).strip() for item in data.get("warnings", []) if str(item).strip()]
    results = [
        _normalize_graphrag_hit(hit)
        for hit in data.get("results", [])
        if isinstance(hit, dict)
    ]

    logger.debug(
        "GraphRAG hybrid query returned %d result(s) via route=%s warnings=%d",
        len(results),
        route,
        len(warnings),
    )
    return GraphRAGKnowledgeResult(results=results, route=route, warnings=warnings)
