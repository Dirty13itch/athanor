"""Hybrid Search — Dense + miniCOIL Sparse with Qdrant-native RRF.

Uses Qdrant's /query endpoint to combine:
  1. Dense vector search (1024-dim Qwen3-Embedding via LiteLLM)
  2. miniCOIL sparse search (neural keyword matching, FastEmbed 0.7+)
  3. Reciprocal Rank Fusion (RRF) — performed by Qdrant server

Falls back to vector + payload keyword search (the previous approach)
when:
  - fastembed is not installed
  - The collection doesn't have sparse vectors (e.g. personal_data)
  - miniCOIL model fails to load or compute

Collections that support hybrid search:
  - knowledge: named "dense" + "sparse" vectors (post-miniCOIL migration)

Collections using fallback (keyword scroll):
  - personal_data, conversations, preferences — unnamed dense vectors only

Algorithm (primary):
  Qdrant /query with prefetch=[dense(top20), sparse(top20)], fusion=rrf, limit=5

Algorithm (fallback):
  Python RRF over /search (vector) + /scroll (text match)
  rrf_score = sum(weight_i / (k + rank_i + 1))
  k=60, weights: vector=0.7, keyword=0.3

Ported from: reference/hydra/src/hydra_tools/hybrid_memory.py
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url

# RRF parameters (fallback path)
RRF_K = 60
VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

# miniCOIL model singleton — lazy loaded, thread-safe
_minicoil = None
_minicoil_lock = threading.Lock()
_minicoil_load_attempted = False


def _load_minicoil():
    """Load miniCOIL model. Thread-safe, called once."""
    global _minicoil, _minicoil_load_attempted
    with _minicoil_lock:
        if _minicoil_load_attempted:
            return _minicoil
        _minicoil_load_attempted = True
        try:
            from fastembed import SparseTextEmbedding
            _minicoil = SparseTextEmbedding(model_name="Qdrant/minicoil-v1")
            logger.info("miniCOIL loaded for hybrid search")
        except Exception as e:
            logger.info("miniCOIL not available (fallback to keyword): %s", e)
            _minicoil = None
    return _minicoil


async def _get_minicoil():
    """Async wrapper: loads miniCOIL in a thread pool to avoid blocking."""
    if _minicoil_load_attempted:
        return _minicoil
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _load_minicoil)


def _compute_query_sparse(query_text: str, model) -> dict | None:
    """Compute miniCOIL sparse vector for a query string."""
    try:
        embeddings = list(model.query_embed([query_text], batch_size=1))
        e = embeddings[0]
        return {"indices": e.indices.tolist(), "values": e.values.tolist()}
    except Exception as e:
        logger.debug("miniCOIL query encode failed: %s", e)
        return None


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
    """Combine vector and keyword results using RRF (fallback path)."""
    if not vector_results and not keyword_results:
        return []

    total_w = vector_weight + keyword_weight
    vw = vector_weight / total_w
    kw = keyword_weight / total_w

    merged: dict[str, SearchResult] = {}
    scores: dict[str, float] = {}

    for rank, r in enumerate(vector_results):
        merged[r.id] = r
        scores[r.id] = vw / (k + rank + 1)
        r.vector_rank = rank

    for rank, r in enumerate(keyword_results):
        if r.id in merged:
            existing = merged[r.id]
            existing.keyword_rank = rank
            existing.source = "hybrid"
            scores[r.id] += kw / (k + rank + 1)
        else:
            r.keyword_rank = rank
            merged[r.id] = r
            scores[r.id] = kw / (k + rank + 1)

    for doc_id, result in merged.items():
        result.rrf_score = scores[doc_id]
        result.score = result.rrf_score

    return sorted(merged.values(), key=lambda x: x.rrf_score, reverse=True)


async def _qdrant_hybrid_query(
    client: httpx.AsyncClient,
    collection: str,
    dense_vector: list[float],
    sparse_vector: dict,
    limit: int,
    score_threshold: float,
    filter_dict: dict | None,
) -> list[dict] | None:
    """Qdrant-native hybrid query using named dense + sparse vectors + RRF.

    Returns None on failure (caller should fall back to keyword approach).
    """
    body: dict = {
        "prefetch": [
            {
                "query": dense_vector,
                "using": "dense",
                "limit": limit * 3,
            },
            {
                "query": sparse_vector,
                "using": "sparse",
                "limit": limit * 3,
            },
        ],
        "query": {"fusion": "rrf"},
        "limit": limit,
        "with_payload": True,
    }
    if filter_dict:
        body["filter"] = filter_dict

    try:
        resp = await client.post(
            f"{_QDRANT_URL}/collections/{collection}/points/query",
            json=body,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])
        # Normalize to expected format
        return [
            {
                "id": r["id"],
                "payload": r.get("payload", {}),
                "score": r.get("score", 0.0),
                "_source": "hybrid",
            }
            for r in points
            if r.get("score", 0.0) >= score_threshold
        ]
    except Exception as e:
        logger.debug("Qdrant hybrid query failed for '%s': %s", collection, e)
        return None


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
    """Perform hybrid search: dense + sparse (miniCOIL) or dense + keyword.

    Primary path (when miniCOIL available + collection has sparse vectors):
      Qdrant /query with prefetch=[dense, sparse] + server-side RRF fusion.

    Fallback path (all other cases):
      Dense /search + keyword /scroll, fused with Python RRF.

    Args:
        client: Async HTTP client for Qdrant.
        collection: Qdrant collection name.
        vector: Pre-computed dense embedding vector.
        query_text: Raw query text for sparse/keyword matching.
        limit: Max results to return.
        text_fields: Payload fields to search (fallback only).
        score_threshold: Minimum score for inclusion.
        filter_dict: Additional Qdrant filter applied to both searches.

    Returns:
        List of Qdrant-style result dicts (id, payload, score) ordered by
        hybrid relevance. Compatible with existing _search_collection output.
    """
    if text_fields is None:
        text_fields = ["text", "content", "title"]

    # --- Primary path: miniCOIL + Qdrant-native RRF ---
    model = await _get_minicoil()
    if model is not None:
        loop = asyncio.get_event_loop()
        sparse_vector = await loop.run_in_executor(
            None, _compute_query_sparse, query_text, model
        )
        if sparse_vector is not None:
            results = await _qdrant_hybrid_query(
                client, collection, vector, sparse_vector,
                limit, score_threshold, filter_dict,
            )
            if results is not None:
                logger.debug(
                    "Hybrid search '%s': %d results via miniCOIL+RRF", collection, len(results)
                )
                return results

    # --- Fallback path: vector + keyword text match ---
    logger.debug("Hybrid search '%s': using keyword fallback", collection)
    vector_task = _vector_search(
        client, collection, vector, limit * 2, score_threshold, filter_dict
    )
    keyword_task = _keyword_search(
        client, collection, query_text, limit * 2, text_fields, filter_dict
    )

    vector_raw, keyword_raw = await asyncio.gather(
        vector_task, keyword_task, return_exceptions=True
    )

    if isinstance(vector_raw, BaseException):
        logger.debug("Hybrid fallback: vector search failed: %s", vector_raw)
        vector_raw = []
    if isinstance(keyword_raw, BaseException):
        logger.debug("Hybrid fallback: keyword search failed: %s", keyword_raw)
        keyword_raw = []

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
            score=1.0 / (i + 1),
            source="keyword",
        )
        for i, r in enumerate(keyword_raw)
    ]

    if vector_results and keyword_results:
        fused = reciprocal_rank_fusion(vector_results, keyword_results)
    elif vector_results:
        fused = vector_results
    elif keyword_results:
        fused = keyword_results
    else:
        return []

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
    """Standard Qdrant vector search (unnamed vector, fallback path)."""
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
    """Keyword search via Qdrant payload text matching (fallback path).

    Splits query into tokens and searches for any token match
    in the specified payload fields.
    """
    tokens = [t for t in query_text.split() if len(t) >= 3]
    if not tokens:
        return []

    should_conditions = []
    for token in tokens[:5]:
        for field_name in text_fields:
            should_conditions.append({
                "key": field_name,
                "match": {"text": token},
            })

    scroll_filter: dict = {"should": should_conditions}

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
