#!/usr/bin/env python3
"""MCP server: Qdrant vector database access for Claude Code.

Provides direct access to Qdrant collections on FOUNDRY for semantic search,
collection stats, and point inspection.

Usage in .mcp.json:
  "qdrant": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-qdrant.py"],
    "env": {}
  }
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP


def _default_qdrant_url() -> str:
    node1_host = os.environ.get("ATHANOR_NODE1_HOST", "192.168.1.244").strip()
    return f"http://{node1_host}:6333"


def _default_litellm_url() -> str:
    vault_host = os.environ.get("ATHANOR_VAULT_HOST", "192.168.1.203").strip()
    return f"http://{vault_host}:4000/v1"


QDRANT_URL = os.environ.get("ATHANOR_QDRANT_URL") or os.environ.get("QDRANT_URL") or _default_qdrant_url()

_http = httpx.Client(timeout=30, base_url=QDRANT_URL)
mcp = FastMCP("qdrant")


@mcp.tool()
def qdrant_collections() -> str:
    """List all Qdrant collections with point counts and vector dimensions."""
    resp = _http.get("/collections")
    resp.raise_for_status()
    collections = resp.json()["result"]["collections"]

    result = []
    for col in collections:
        name = col["name"]
        info_resp = _http.get(f"/collections/{name}")
        info_resp.raise_for_status()
        info = info_resp.json()["result"]
        result.append({
            "name": name,
            "points": info.get("points_count", 0),
            "vectors_count": info.get("vectors_count", 0),
            "status": info.get("status", "unknown"),
            "vector_size": _get_vector_size(info),
        })

    return json.dumps(result, indent=2)


def _get_vector_size(info: dict) -> int | None:
    """Extract vector dimension from collection config."""
    config = info.get("config", {})
    params = config.get("params", {})
    vectors = params.get("vectors", {})
    if isinstance(vectors, dict):
        if "size" in vectors:
            return vectors["size"]
        for v in vectors.values():
            if isinstance(v, dict) and "size" in v:
                return v["size"]
    return None


@mcp.tool()
def qdrant_search(
    collection: str,
    query_text: str,
    limit: int = 5,
) -> str:
    """Search a Qdrant collection using the embedding model via LiteLLM.
    Embeds the query text and performs nearest-neighbor search.

    Args:
        collection: Collection name (e.g., 'knowledge', 'conversations', 'signals')
        query_text: Text to search for semantically
        limit: Number of results to return (default 5)
    """
    # Get embedding from LiteLLM
    litellm_url = os.environ.get("ATHANOR_LITELLM_URL") or os.environ.get("LITELLM_URL") or _default_litellm_url()
    litellm_url = litellm_url.rstrip("/")
    if not litellm_url.endswith("/v1"):
        litellm_url = f"{litellm_url}/v1"
    litellm_key = (
        os.environ.get("ATHANOR_LITELLM_API_KEY")
        or os.environ.get("LITELLM_KEY")
        or os.environ.get("LITELLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )

    embed_resp = httpx.post(
        f"{litellm_url}/embeddings",
        json={"model": "embedding", "input": query_text},
        headers={"Authorization": f"Bearer {litellm_key}"},
        timeout=30,
    )
    embed_resp.raise_for_status()
    vector = embed_resp.json()["data"][0]["embedding"]

    # Search Qdrant
    search_resp = _http.post(
        f"/collections/{collection}/points/search",
        json={
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        },
    )
    search_resp.raise_for_status()
    results = search_resp.json()["result"]

    formatted = []
    for r in results:
        entry = {
            "score": r["score"],
            "id": str(r["id"]),
        }
        if r.get("payload"):
            # Include payload but truncate long text fields
            payload = {}
            for k, v in r["payload"].items():
                if isinstance(v, str) and len(v) > 500:
                    payload[k] = v[:500] + "..."
                else:
                    payload[k] = v
            entry["payload"] = payload
        formatted.append(entry)

    return json.dumps(formatted, indent=2)


@mcp.tool()
def qdrant_scroll(
    collection: str,
    limit: int = 10,
    offset: str | None = None,
    filter_key: str | None = None,
    filter_value: str | None = None,
) -> str:
    """Browse points in a Qdrant collection with optional filtering.

    Args:
        collection: Collection name
        limit: Number of points to return (default 10)
        offset: Pagination offset (point ID from previous call)
        filter_key: Optional payload field to filter on
        filter_value: Optional value to match for the filter field
    """
    body: dict = {"limit": limit, "with_payload": True}
    if offset:
        body["offset"] = offset
    if filter_key and filter_value:
        body["filter"] = {
            "must": [{"key": filter_key, "match": {"value": filter_value}}]
        }

    resp = _http.post(f"/collections/{collection}/points/scroll", json=body)
    resp.raise_for_status()
    data = resp.json()["result"]

    points = []
    for p in data.get("points", []):
        entry = {"id": str(p["id"])}
        if p.get("payload"):
            payload = {}
            for k, v in p["payload"].items():
                if isinstance(v, str) and len(v) > 300:
                    payload[k] = v[:300] + "..."
                else:
                    payload[k] = v
            entry["payload"] = payload
        points.append(entry)

    result = {
        "points": points,
        "next_offset": str(data.get("next_page_offset")) if data.get("next_page_offset") else None,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def qdrant_count(collection: str) -> str:
    """Get the exact point count for a collection.

    Args:
        collection: Collection name
    """
    resp = _http.post(
        f"/collections/{collection}/points/count",
        json={"exact": True},
    )
    resp.raise_for_status()
    count = resp.json()["result"]["count"]
    return json.dumps({"collection": collection, "count": count})


if __name__ == "__main__":
    mcp.run()
