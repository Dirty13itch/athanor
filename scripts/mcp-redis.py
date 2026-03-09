#!/usr/bin/env python3
"""MCP server: Redis cluster state access for Claude Code.

Provides direct access to Redis heartbeats, GWT workspace state,
task queue, scheduler state, and cache operations.

Usage in .mcp.json:
  "redis": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-redis.py"],
    "env": {}
  }
"""

import json
import os

import redis
from mcp.server.fastmcp import FastMCP

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.1.203")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "Jv1Vg9HAML2jHGWjFnTCcIsqSzqZfIQz")

_redis = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
    decode_responses=True, socket_connect_timeout=5,
)

mcp = FastMCP("redis")


@mcp.tool()
def redis_heartbeats() -> str:
    """Get heartbeat status for all Athanor nodes (foundry, workshop, dev).
    Shows GPU metrics, container status, system load, and last-seen time."""
    results = {}
    for node in ["foundry", "workshop", "dev"]:
        key = f"athanor:heartbeat:{node}"
        data = _redis.get(key)
        ttl = _redis.ttl(key)
        if data:
            try:
                parsed = json.loads(data)
                parsed["_ttl_seconds"] = ttl
                results[node] = parsed
            except json.JSONDecodeError:
                results[node] = {"raw": data, "_ttl_seconds": ttl}
        else:
            results[node] = {"status": "NO_HEARTBEAT", "_ttl_seconds": -1}
    return json.dumps(results, indent=2)


@mcp.tool()
def redis_workspace() -> str:
    """Get the GWT (Global Workspace Theory) workspace state.
    Shows active proposals, specialist competition results, and CST."""
    workspace = _redis.get("athanor:workspace")
    cst = _redis.get("athanor:cst")
    result = {
        "workspace": json.loads(workspace) if workspace else None,
        "cst": json.loads(cst) if cst else None,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def redis_scheduler() -> str:
    """Get scheduler state — last run times for all scheduled tasks."""
    keys = _redis.keys("athanor:scheduler:*")
    result = {}
    for key in sorted(keys):
        name = key.split(":")[-1]
        val = _redis.get(key)
        try:
            result[name] = json.loads(val) if val else None
        except (json.JSONDecodeError, TypeError):
            result[name] = val
    return json.dumps(result, indent=2)


@mcp.tool()
def redis_tasks() -> str:
    """Get the task queue state — active and recent tasks."""
    data = _redis.get("athanor:tasks")
    if data:
        try:
            return json.dumps(json.loads(data), indent=2)
        except json.JSONDecodeError:
            return data
    return "No tasks found"


@mcp.tool()
def redis_gpu_zones() -> str:
    """Get GPU zone allocation state from the orchestrator."""
    keys = _redis.keys("athanor:gpu:*")
    result = {}
    for key in sorted(keys):
        name = key.split(":")[-1]
        val = _redis.get(key)
        try:
            result[name] = json.loads(val) if val else None
        except (json.JSONDecodeError, TypeError):
            result[name] = val
    return json.dumps(result, indent=2)


@mcp.tool()
def redis_keys(pattern: str = "athanor:*") -> str:
    """List Redis keys matching a pattern. Default: all athanor:* keys.

    Args:
        pattern: Redis key pattern (e.g., 'athanor:heartbeat:*', 'athanor:workspace*')
    """
    keys = _redis.keys(pattern)
    result = {}
    for key in sorted(keys):
        key_type = _redis.type(key)
        ttl = _redis.ttl(key)
        result[key] = {"type": key_type, "ttl": ttl}
    return json.dumps(result, indent=2)


@mcp.tool()
def redis_get(key: str) -> str:
    """Get the value of a specific Redis key.

    Args:
        key: The Redis key to retrieve (e.g., 'athanor:workspace')
    """
    key_type = _redis.type(key)
    if key_type == "string":
        val = _redis.get(key)
        try:
            return json.dumps(json.loads(val), indent=2)
        except (json.JSONDecodeError, TypeError):
            return val or "(nil)"
    elif key_type == "hash":
        return json.dumps(_redis.hgetall(key), indent=2)
    elif key_type == "list":
        return json.dumps(_redis.lrange(key, 0, -1), indent=2)
    elif key_type == "set":
        return json.dumps(list(_redis.smembers(key)), indent=2)
    elif key_type == "zset":
        return json.dumps(_redis.zrange(key, 0, -1, withscores=True), indent=2)
    else:
        return f"Key '{key}' not found or type '{key_type}' unsupported"


@mcp.tool()
def redis_alerts() -> str:
    """Get recent alerts from the athanor:alerts channel history."""
    history = _redis.get("athanor:alerts:history")
    last_check = _redis.get("athanor:alerts:last_check")
    seen = _redis.get("athanor:alerts:seen")
    result = {
        "history": json.loads(history) if history else None,
        "last_check": last_check,
        "seen": json.loads(seen) if seen else None,
    }
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
