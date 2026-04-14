"""
Semantic Cache — LLM response caching with vector similarity.

Caches LLM responses in Qdrant and returns them when semantically similar
queries arrive. Expected 30-50% reduction in redundant inference.

Architecture:
    Query → Embed → Qdrant search → if match ≥ threshold → return cached
    Otherwise → call LLM → cache response → return

Ported from Hydra's semantic_cache.py, adapted for Athanor:
- Embedding via LiteLLM at VAULT:4000 (qwen3-embed-8b, 1024-dim)
- Qdrant at VAULT:6333, collection `llm_cache`
- No Prometheus (use existing Grafana stack for monitoring)
"""

import hashlib
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from .circuit_breaker import get_circuit_breakers
from .config import settings
from .services import ensure_openai_base_url, normalize_url

logger = logging.getLogger(__name__)

SEMANTIC_CACHE_EMBED_TIMEOUT = 12.0


@dataclass
class CacheEntry:
    id: str
    query_hash: str
    query: str
    response: str
    model: str
    created_at: str
    expires_at: str
    hit_count: int = 0
    last_hit: Optional[str] = None
    tokens_saved: int = 0
    context_hash: Optional[str] = None


class SemanticCache:
    """
    Qdrant-backed semantic cache for LLM responses.
    """

    def __init__(
        self,
        qdrant_url: str | None = None,
        embedding_url: str | None = None,
        embedding_api_key: str | None = None,
        embedding_model: str = "embedding",
        collection_name: str = "llm_cache",
        similarity_threshold: float = 0.93,
        ttl_hours: int = 48,
        embedding_dim: int = 1024,
    ):
        self.qdrant_url = normalize_url(qdrant_url or settings.qdrant_url)
        self.embedding_url = ensure_openai_base_url(embedding_url or settings.litellm_url)
        self.embedding_api_key = embedding_api_key if embedding_api_key is not None else settings.litellm_api_key
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self.embedding_dim = embedding_dim
        self._initialized = False
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        if self._initialized:
            return True

        self._client = httpx.AsyncClient(timeout=30.0)

        try:
            resp = await self._client.get(
                f"{self.qdrant_url}/collections/{self.collection_name}"
            )

            if resp.status_code == 404:
                await self._create_collection()
            elif resp.status_code != 200:
                logger.error(f"Qdrant collection check failed: {resp.text}")
                return False

            self._initialized = True
            logger.info(f"Semantic cache initialized: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Semantic cache init failed: {e}")
            return False

    async def _create_collection(self):
        resp = await self._client.put(
            f"{self.qdrant_url}/collections/{self.collection_name}",
            json={
                "vectors": {"size": self.embedding_dim, "distance": "Cosine"},
                "optimizers_config": {"indexing_threshold": 20000},
                "on_disk_payload": True,
            },
        )
        if resp.status_code not in [200, 201]:
            raise Exception(f"Failed to create collection: {resp.text}")

    async def _embed(self, text: str) -> Optional[list[float]]:
        """Get embedding via LiteLLM → Qwen3-Embedding."""
        async def _request_embedding() -> list[float]:
            resp = await self._client.post(
                f"{self.embedding_url}/embeddings",
                json={"model": self.embedding_model, "input": text[:8000]},
                headers={"Authorization": f"Bearer {self.embedding_api_key}"},
                timeout=SEMANTIC_CACHE_EMBED_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]

        try:
            embedding = await get_circuit_breakers().execute_with_breaker(
                "embedding",
                _request_embedding,
                fallback=lambda: None,
            )
            if embedding:
                return embedding
            logger.debug("Semantic cache embedding skipped because the embedding circuit is open")
            return None
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    async def lookup(
        self, query: str, model: str, context_hash: Optional[str] = None,
    ) -> Optional[tuple[str, float]]:
        """
        Look up cached response. Returns (response, score) or None.
        """
        if not self._initialized:
            await self.initialize()

        try:
            embedding = await self._embed(query)
            if not embedding:
                return None

            now = datetime.now(timezone.utc).isoformat()
            filter_conditions = [
                {"key": "model", "match": {"value": model}},
                {"key": "expires_at", "range": {"gt": now}},
            ]
            if context_hash:
                filter_conditions.append(
                    {"key": "context_hash", "match": {"value": context_hash}}
                )

            resp = await self._client.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json={
                    "vector": embedding,
                    "limit": 1,
                    "with_payload": True,
                    "score_threshold": self.similarity_threshold,
                    "filter": {"must": filter_conditions},
                },
            )

            if resp.status_code != 200:
                return None

            results = resp.json().get("result", [])
            if not results:
                return None

            best = results[0]
            score = best["score"]
            payload = best["payload"]

            if score >= self.similarity_threshold:
                # Update hit count
                await self._client.post(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points/payload",
                    json={
                        "points": [best["id"]],
                        "payload": {
                            "hit_count": payload.get("hit_count", 0) + 1,
                            "last_hit": datetime.now(timezone.utc).isoformat(),
                        },
                    },
                )
                logger.info(f"Cache HIT model={model} score={score:.4f}")
                return (payload["response"], score)

            return None
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None

    async def store(
        self,
        query: str,
        response: str,
        model: str,
        tokens_used: int = 0,
        context_hash: Optional[str] = None,
    ) -> bool:
        """Store a query-response pair."""
        if not self._initialized:
            await self.initialize()

        try:
            embedding = await self._embed(query)
            if not embedding:
                return False

            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            point_id = int(hashlib.sha256(f"{query_hash}_{model}".encode()).hexdigest()[:8], 16)

            now = datetime.now(timezone.utc)
            expires = now + timedelta(hours=self.ttl_hours)

            resp = await self._client.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={
                    "points": [{
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "query_hash": query_hash,
                            "query": query[:1000],
                            "response": response,
                            "model": model,
                            "created_at": now.isoformat(),
                            "expires_at": expires.isoformat(),
                            "hit_count": 0,
                            "tokens_saved": tokens_used,
                            "context_hash": context_hash,
                        },
                    }],
                },
            )
            return resp.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        if not self._initialized:
            await self.initialize()

        try:
            now = datetime.now(timezone.utc).isoformat()
            resp = await self._client.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/delete",
                json={"filter": {"must": [{"key": "expires_at", "range": {"lt": now}}]}},
            )
            if resp.status_code == 200:
                deleted = resp.json().get("result", {}).get("deleted", 0)
                logger.info(f"Cleaned {deleted} expired cache entries")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        if not self._initialized:
            await self.initialize()

        try:
            resp = await self._client.get(
                f"{self.qdrant_url}/collections/{self.collection_name}"
            )
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                return {
                    "entries": result.get("points_count", 0),
                    "indexed_vectors": result.get("indexed_vectors_count", 0),
                    "collection": self.collection_name,
                    "similarity_threshold": self.similarity_threshold,
                    "ttl_hours": self.ttl_hours,
                }
            return {"error": f"Failed: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        if self._client:
            await self._client.aclose()


# Singleton
_cache: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache


async def cached_completion(
    query: str,
    model: str,
    completion_func,
    context_hash: Optional[str] = None,
    bypass_cache: bool = False,
    **kwargs,
) -> tuple[str, bool]:
    """
    Wrapper for LLM completions with semantic caching.

    Returns (response, was_cached).
    """
    cache = get_semantic_cache()

    if not bypass_cache:
        result = await cache.lookup(query, model, context_hash)
        if result:
            return (result[0], True)

    response = await completion_func(query, model, **kwargs)

    tokens_estimate = len(query) // 4 + len(response) // 4
    await cache.store(query, response, model, tokens_estimate, context_hash)

    return (response, False)


# FastAPI router
def create_cache_router():
    from fastapi import APIRouter, Request
    from pydantic import BaseModel
    from starlette.responses import JSONResponse

    from .operator_contract import (
        build_operator_action,
        emit_operator_audit_event,
        require_operator_action,
    )

    router = APIRouter(prefix="/v1/cache", tags=["semantic-cache"])

    async def _load_operator_body(
        request: Request,
        *,
        route: str,
        action_class: str,
        default_reason: str,
    ):
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(body, dict):
            body = {}

        candidate = build_operator_action(body, default_reason=default_reason)
        try:
            action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            status_code = getattr(exc, "status_code", 400)
            await emit_operator_audit_event(
                service="agent-server",
                route=route,
                action_class=action_class,
                decision="denied",
                status_code=status_code,
                action=candidate,
                detail=str(detail),
            )
            return None, None, JSONResponse(status_code=status_code, content={"error": detail})

        return body, action, None

    class LookupRequest(BaseModel):
        query: str
        model: str
        context_hash: Optional[str] = None

    class StoreRequest(BaseModel):
        query: str
        response: str
        model: str
        tokens_used: int = 0
        context_hash: Optional[str] = None

    @router.post("/lookup")
    async def lookup(req: LookupRequest):
        cache = get_semantic_cache()
        result = await cache.lookup(req.query, req.model, req.context_hash)
        if result:
            return {"hit": True, "response": result[0], "score": result[1]}
        return {"hit": False}

    @router.post("/store")
    async def store(request: Request, req: StoreRequest):
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/cache/store",
            action_class="operator",
            default_reason="Store semantic cache entry",
        )
        if denial:
            return denial
        cache = get_semantic_cache()
        ok = await cache.store(req.query, req.response, req.model, req.tokens_used, req.context_hash)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/cache/store",
            action_class="operator",
            decision="accepted" if ok else "denied",
            status_code=200 if ok else 500,
            action=action,
            detail="Stored semantic cache entry" if ok else "Failed to store semantic cache entry",
            target=req.model,
            metadata={"context_hash": req.context_hash or "", "tokens_used": req.tokens_used},
        )
        return {"stored": ok}

    @router.get("/stats")
    async def stats():
        cache = get_semantic_cache()
        return await cache.get_stats()

    @router.post("/cleanup")
    async def cleanup(request: Request):
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/cache/cleanup",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        cache = get_semantic_cache()
        deleted = await cache.cleanup_expired()
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/cache/cleanup",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Cleaned up {deleted} expired semantic cache entries",
            target=cache.collection_name,
            metadata={"deleted": deleted},
        )
        return {"deleted": deleted}

    return router
