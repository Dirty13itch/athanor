"""Activity logging and preference storage via Qdrant.

Two collections:
- `activity`: Every agent action (searchable, filterable by agent/time/type)
- `preferences`: Explicit user signals (thumbs up/down, "remember this", config choices)

Both use 1024-dim Cosine embeddings from Qwen3-Embedding-0.6B via LiteLLM.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url
_EMBEDDING_URL = settings.llm_base_url.replace("/v1", "") + "/v1"
_EMBEDDING_KEY = settings.llm_api_key

COLLECTIONS = {
    "activity": {
        "vectors": {"size": 1024, "distance": "Cosine"},
    },
    "preferences": {
        "vectors": {"size": 1024, "distance": "Cosine"},
    },
    "conversations": {
        "vectors": {"size": 1024, "distance": "Cosine"},
    },
}


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector via LiteLLM."""
    resp = httpx.post(
        f"{_EMBEDDING_URL}/embeddings",
        json={"model": "embedding", "input": text},
        headers={"Authorization": f"Bearer {_EMBEDDING_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def _point_id(text: str) -> str:
    """Generate a deterministic UUID-format ID from text."""
    h = hashlib.md5(text.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def ensure_collections():
    """Create activity and preferences collections if they don't exist."""
    for name, config in COLLECTIONS.items():
        try:
            resp = httpx.get(f"{_QDRANT_URL}/collections/{name}", timeout=5)
            if resp.status_code == 200:
                logger.info("Collection '%s' already exists", name)
                continue
        except Exception:
            pass

        try:
            resp = httpx.put(
                f"{_QDRANT_URL}/collections/{name}",
                json=config,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Created collection '%s'", name)
        except Exception as e:
            logger.warning("Failed to create collection '%s': %s", name, e)


async def log_activity(
    agent: str,
    action_type: str,
    input_summary: str,
    output_summary: str,
    tools_used: list[str] | None = None,
    duration_ms: int | None = None,
):
    """Log an agent action to the activity collection.

    Embeds the combined input+output text for semantic search.
    Stores metadata for filtering.
    """
    now = datetime.now(timezone.utc).isoformat()
    text = f"Agent: {agent}. Action: {action_type}. Input: {input_summary}. Output: {output_summary}"

    try:
        vector = _get_embedding(text[:2000])
        point_id = _point_id(f"{agent}-{now}-{input_summary[:100]}")

        payload = {
            "agent": agent,
            "action_type": action_type,
            "input_summary": input_summary[:500],
            "output_summary": output_summary[:1000],
            "tools_used": tools_used or [],
            "duration_ms": duration_ms,
            "timestamp": now,
            "timestamp_unix": int(time.time()),
        }

        resp = httpx.put(
            f"{_QDRANT_URL}/collections/activity/points",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to log activity for %s: %s", agent, e)


async def log_conversation(
    agent: str,
    user_message: str,
    assistant_response: str,
    tools_used: list[str] | None = None,
    duration_ms: int | None = None,
    thread_id: str = "",
):
    """Log a conversation turn to the conversations collection.

    Embeds the user message for semantic search. Stores both sides
    of the exchange plus metadata for retrieval.
    """
    now = datetime.now(timezone.utc).isoformat()

    try:
        vector = _get_embedding(user_message[:2000])
        point_id = _point_id(f"conv-{agent}-{now}-{user_message[:100]}")

        payload = {
            "agent": agent,
            "user_message": user_message[:2000],
            "assistant_response": assistant_response[:4000],
            "tools_used": tools_used or [],
            "duration_ms": duration_ms,
            "thread_id": thread_id,
            "timestamp": now,
            "timestamp_unix": int(time.time()),
        }

        resp = httpx.put(
            f"{_QDRANT_URL}/collections/conversations/points",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to log conversation for %s: %s", agent, e)


async def store_preference(
    agent: str,
    signal_type: str,
    content: str,
    category: str = "",
    metadata: dict | None = None,
):
    """Store a user preference signal.

    Args:
        agent: Which agent this preference relates to (or "global")
        signal_type: One of: thumbs_up, thumbs_down, remember_this, config_choice
        content: The preference text (e.g., "I prefer dark themes", "Don't recommend horror")
        category: Optional grouping (e.g., "media", "home", "creative")
        metadata: Optional additional key-value pairs
    """
    now = datetime.now(timezone.utc).isoformat()

    try:
        vector = _get_embedding(content[:2000])
        point_id = _point_id(f"pref-{agent}-{content[:100]}-{now}")

        payload = {
            "agent": agent,
            "signal_type": signal_type,
            "content": content,
            "category": category,
            "timestamp": now,
            "timestamp_unix": int(time.time()),
        }
        if metadata:
            payload["metadata"] = metadata

        resp = httpx.put(
            f"{_QDRANT_URL}/collections/preferences/points",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to store preference: %s", e)


async def query_preferences(
    query: str,
    agent: str = "",
    limit: int = 5,
) -> list[dict]:
    """Query stored preferences by semantic similarity.

    Args:
        query: What to search for (e.g., "media quality preferences")
        agent: Filter by agent name (empty = all agents)
        limit: Max results
    Returns:
        List of preference dicts with score, content, signal_type, etc.
    """
    try:
        vector = _get_embedding(query[:2000])

        body: dict = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }

        if agent:
            body["filter"] = {
                "should": [
                    {"key": "agent", "match": {"value": agent}},
                    {"key": "agent", "match": {"value": "global"}},
                ]
            }

        resp = httpx.post(
            f"{_QDRANT_URL}/collections/preferences/points/search",
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])

        return [
            {
                "score": r["score"],
                "content": r["payload"].get("content", ""),
                "signal_type": r["payload"].get("signal_type", ""),
                "agent": r["payload"].get("agent", ""),
                "category": r["payload"].get("category", ""),
                "timestamp": r["payload"].get("timestamp", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning("Failed to query preferences: %s", e)
        return []


async def query_activity(
    agent: str = "",
    action_type: str = "",
    limit: int = 20,
    since_unix: int = 0,
) -> list[dict]:
    """Query recent activity, optionally filtered by agent or action type.

    Args:
        agent: Filter by agent name (empty = all)
        action_type: Filter by action type (empty = all)
        limit: Max results
        since_unix: Only return activity after this unix timestamp
    Returns:
        List of activity dicts sorted by recency.
    """
    try:
        must_filters = []
        if agent:
            must_filters.append({"key": "agent", "match": {"value": agent}})
        if action_type:
            must_filters.append({"key": "action_type", "match": {"value": action_type}})
        if since_unix > 0:
            must_filters.append({"key": "timestamp_unix", "range": {"gte": since_unix}})

        body: dict = {
            "limit": limit,
            "with_payload": True,
        }
        if must_filters:
            body["filter"] = {"must": must_filters}

        resp = httpx.post(
            f"{_QDRANT_URL}/collections/activity/points/scroll",
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])

        results = []
        for p in points:
            payload = p.get("payload", {})
            results.append({
                "agent": payload.get("agent", ""),
                "action_type": payload.get("action_type", ""),
                "input_summary": payload.get("input_summary", ""),
                "output_summary": payload.get("output_summary", ""),
                "tools_used": payload.get("tools_used", []),
                "duration_ms": payload.get("duration_ms"),
                "timestamp": payload.get("timestamp", ""),
            })

        # Sort by timestamp descending
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]
    except Exception as e:
        logger.warning("Failed to query activity: %s", e)
        return []
