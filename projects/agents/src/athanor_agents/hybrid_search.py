"""Hybrid Search — Vector + Keyword with Reciprocal Rank Fusion.

Combines Qdrant vector search with Qdrant payload text matching
for ~18.5% retrieval accuracy improvement over vector-only search.

Catches exact matches that vector search misses (e.g., "ADR-017",
"Qwen3-32B-AWQ", specific IP addresses, model names).

Algorithm: Reciprocal Rank Fusion (RRF)
  rrf_score = sum(weight_i / (k + rank_i + 1))
  k=60 (standard constant, higher = less top-result bias)
  Weights: vector=0.7, keyword=0.3

Ported from: reference/hydra/src/hydra_tools/hybrid_memory.py
Adapted for Athanor: uses Qdrant-only (payload text index),
no Meilisearch dependency. Can be extended to add Meilisearch later.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url

# RRF parameters
RRF_K = 60
VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3


@dataclass
class SearchResult:
    """A single search result with fusion metadata."""
    id: str
    payload: dict
    score: float
    source: str  # "vector", "keyword", "hybrid"
    vector_rank: int | None = None
    keyword_rank: int | None = None
    rrf_score: float = 0.0


def reciprocal_rank_fusion(
    vector_results: list[SearchResult],
    keyword_results: list[SearchResult],
    k: int = RRF_K,
    vector_weight: float = VECTOR_WEIGHT,
    keyword_weight: float = KEYWORD_WEIGHT,
) -> list[SearchResult]:
    """Combine vector and keyword results using RRF.

    Results are keyed by point ID. When the same document appears in both
    lists, scores are summed and source becomes "hybrid".
    """
    if not vector_results and not keyword_results:
        return []

    # Normalize weights
    total_w = vector_weight + keyword_weight
    vw = vector_weight / total_w
    kw = keyword_weight / total_w

    # Build ID → result map
    merged: dict[str, SearchResult] = {}
    scores: dict[str, float] = {}

    for rank, r in enumerate(vector_results):
        merged[r.id] = r
        scores[r.id] = vw / (k + rank + 1)
        r.vector_rank = rank

    for rank, r in enumerate(keyword_results):
        if r.id in merged:
            # Same doc in both — mark hybrid, keep richer payload
            existing = merged[r.id]
            existing.keyword_rank = rank
            existing.source = "hybrid"
            scores[r.id] += kw / (k + rank + 1)
        else:
            r.keyword_rank = rank
            merged[r.id] = r
            scores[r.id] = kw / (k + rank + 1)

    # Apply scores and sort
    for doc_id, result in merged.items():
        result.rrf_score = scores[doc_id]
        result.score = result.rrf_score

    return sorted(merged.values(), key=lambda x: x.rrf_score, reverse=True)


async def hybrid_search(
    client: httpx.AsyncClient,
    collection: str,
    vector: list[float],
    query_text: str,
    limit: int = 5,
    text_fields: list[str] | None = None,
    score_threshold: float = 0.0,
    filter_dict: dict | None = None,
) -> list[dict]:
    """Perform hybrid search: vector + keyword, fused with RRF.

    Args:
        client: Async HTTP client for Qdrant.
        collection: Qdrant collection name.
        vector: Pre-computed embedding vector.
        query_text: Raw query text for keyword matching.
        limit: Max results to return.
        text_fields: Payload fields to search for keywords.
            Defaults to ["text", "content", "title"].
        score_threshold: Minimum vector score for inclusion.
        filter_dict: Additional Qdrant filter to apply to both searches.

    Returns:
        List of Qdrant-style result dicts (id, payload, score) ordered
        by RRF score. Compatible with existing _search_collection output.
    """
    if text_fields is None:
        text_fields = ["text", "content", "title"]

    # Run vector and keyword searches in parallel
    vector_task = _vector_search(
        client, collection, vector, limit * 2, score_threshold, filter_dict
    )
    keyword_task = _keyword_search(
        client, collection, query_text, limit * 2, text_fields, filter_dict
    )

    vector_raw, keyword_raw = await asyncio.gather(
        vector_task, keyword_task, return_exceptions=True
    )

    # Handle failures gracefully — fall back to whichever succeeded
    if isinstance(vector_raw, BaseException):
        logger.debug("Hybrid: vector search failed: %s", vector_raw)
        vector_raw = []
    if isinstance(keyword_raw, BaseException):
        logger.debug("Hybrid: keyword search failed: %s", keyword_raw)
        keyword_raw = []

    # Convert to SearchResult objects
    vector_results = [
        SearchResult(
            id=str(r.get("id", "")),
            payload=r.get("payload", {}),
            score=r.get("score", 0.0),
            source="vector",
        )
        for r in vector_raw
    ]

    keyword_results = [
        SearchResult(
            id=str(r.get("id", "")),
            payload=r.get("payload", {}),
            score=1.0 / (i + 1),  # Assign reciprocal rank as score
            source="keyword",
        )
        for i, r in enumerate(keyword_raw)
    ]

    # Only fuse if both have results, otherwise return whichever worked
    if vector_results and keyword_results:
        fused = reciprocal_rank_fusion(vector_results, keyword_results)
    elif vector_results:
        fused = vector_results
    elif keyword_results:
        fused = keyword_results
    else:
        return []

    # Convert back to Qdrant-compatible format for context.py compatibility
    return [
        {
            "id": r.id,
            "payload": r.payload,
            "score": r.score,
            "_source": r.source,
            "_vector_rank": r.vector_rank,
            "_keyword_rank": r.keyword_rank,
        }
        for r in fused[:limit]
    ]


async def _vector_search(
    client: httpx.AsyncClient,
    collection: str,
    vector: list[float],
    limit: int,
    score_threshold: float,
    filter_dict: dict | None,
) -> list[dict]:
    """Standard Qdrant vector search."""
    body: dict = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
    }
    if score_threshold > 0:
        body["score_threshold"] = score_threshold
    if filter_dict:
        body["filter"] = filter_dict

    resp = await client.post(
        f"{_QDRANT_URL}/collections/{collection}/points/search",
        json=body,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


async def _keyword_search(
    client: httpx.AsyncClient,
    collection: str,
    query_text: str,
    limit: int,
    text_fields: list[str],
    filter_dict: dict | None,
) -> list[dict]:
    """Keyword search via Qdrant payload text matching.

    Splits query into tokens and searches for any token match
    in the specified payload fields. Uses Qdrant's scroll endpoint
    with text match filters.
    """
    # Extract meaningful tokens (skip very short words)
    tokens = [t for t in query_text.split() if len(t) >= 3]
    if not tokens:
        return []

    # Build text match conditions — any token in any field
    should_conditions = []
    for token in tokens[:5]:  # Cap at 5 tokens to keep query reasonable
        for field_name in text_fields:
            should_conditions.append({
                "key": field_name,
                "match": {"text": token},
            })

    scroll_filter: dict = {"should": should_conditions}

    # Combine with any additional filter
    if filter_dict:
        scroll_filter = {
            "must": [
                scroll_filter,
                filter_dict,
            ]
        }

    body = {
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
        "filter": scroll_filter,
    }

    resp = await client.post(
        f"{_QDRANT_URL}/collections/{collection}/points/scroll",
        json=body,
    )
    resp.raise_for_status()
    return resp.json().get("result", {}).get("points", [])
