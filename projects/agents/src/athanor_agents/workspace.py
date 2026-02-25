"""GWT-inspired workspace — shared broadcast medium for inter-agent coordination.

Based on Global Workspace Theory (ADR-017): specialized agents compete to
broadcast information through a capacity-limited workspace. Winners are
broadcast to all agents, enabling emergent coordination.

Backed by Redis. Workspace capacity: 7 items (matching GWT's cognitive bottleneck).
Competition cycle: 1Hz (Phase 2). Phase 1 is the basic CRUD + salience scoring.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum

import redis.asyncio as aioredis

from .config import settings

logger = logging.getLogger(__name__)

WORKSPACE_KEY = "athanor:workspace"
WORKSPACE_HISTORY_KEY = "athanor:workspace:history"
WORKSPACE_BROADCAST_CHANNEL = "athanor:workspace:broadcast"
WORKSPACE_CAPACITY = 7
COMPETITION_INTERVAL = 1.0  # seconds

_redis: aioredis.Redis | None = None
_competition_task: asyncio.Task | None = None


class ItemPriority(str, Enum):
    CRITICAL = "critical"   # System alerts, failures
    HIGH = "high"           # User requests, interactive
    NORMAL = "normal"       # Agent-initiated, proactive
    LOW = "low"             # Background tasks, batch


PRIORITY_WEIGHTS = {
    ItemPriority.CRITICAL: 10.0,
    ItemPriority.HIGH: 5.0,
    ItemPriority.NORMAL: 2.0,
    ItemPriority.LOW: 1.0,
}


@dataclass
class WorkspaceItem:
    """An item competing for workspace broadcast."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_agent: str = ""
    content: str = ""
    priority: str = "normal"
    salience: float = 0.0      # Computed score
    ttl: int = 300             # Seconds before expiry
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def compute_salience(item: WorkspaceItem) -> float:
    """Compute salience score for a workspace item.

    Salience = urgency x relevance x recency
    - Urgency: priority weight
    - Relevance: 1.0 (placeholder — will be content-based in Phase 3)
    - Recency: decays over TTL period
    """
    urgency = PRIORITY_WEIGHTS.get(ItemPriority(item.priority), 2.0)
    relevance = 1.0  # Phase 3: content similarity to active context
    age = time.time() - item.created_at
    recency = max(0.0, 1.0 - (age / item.ttl)) if item.ttl > 0 else 1.0
    return urgency * relevance * recency


async def get_redis() -> aioredis.Redis:
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis


async def post_item(
    source_agent: str,
    content: str,
    priority: str = "normal",
    ttl: int = 300,
    metadata: dict | None = None,
) -> WorkspaceItem:
    """Post an item to the workspace for competition.

    Items compete in the next cycle. Higher salience items win broadcast.
    """
    item = WorkspaceItem(
        source_agent=source_agent,
        content=content,
        priority=priority,
        ttl=ttl,
        metadata=metadata or {},
    )
    item.salience = compute_salience(item)

    try:
        r = await get_redis()
        await r.hset(WORKSPACE_KEY, item.id, json.dumps(item.to_dict()))
        logger.info(
            "Workspace item %s posted by %s (salience=%.2f): %s",
            item.id, source_agent, item.salience, content[:80],
        )
    except Exception as e:
        logger.warning("Failed to post workspace item: %s", e)

    return item


async def get_workspace() -> list[WorkspaceItem]:
    """Get all current workspace items, sorted by salience (descending)."""
    try:
        r = await get_redis()
        raw = await r.hgetall(WORKSPACE_KEY)
        items = []
        now = time.time()
        expired = []

        for item_id, data in raw.items():
            item = WorkspaceItem.from_dict(json.loads(data))
            # Check expiry
            if now - item.created_at > item.ttl:
                expired.append(item_id)
                continue
            # Recompute salience (recency decays)
            item.salience = compute_salience(item)
            items.append(item)

        # Clean expired items
        if expired:
            await r.hdel(WORKSPACE_KEY, *expired)
            logger.debug("Cleaned %d expired workspace items", len(expired))

        items.sort(key=lambda x: x.salience, reverse=True)
        return items
    except Exception as e:
        logger.warning("Failed to get workspace: %s", e)
        return []


async def get_broadcast() -> list[WorkspaceItem]:
    """Get the current broadcast — top N items by salience (N = WORKSPACE_CAPACITY)."""
    items = await get_workspace()
    return items[:WORKSPACE_CAPACITY]


async def clear_item(item_id: str) -> bool:
    """Remove a specific item from the workspace."""
    try:
        r = await get_redis()
        removed = await r.hdel(WORKSPACE_KEY, item_id)
        return removed > 0
    except Exception as e:
        logger.warning("Failed to clear workspace item %s: %s", item_id, e)
        return False


async def clear_workspace() -> int:
    """Clear all workspace items. Returns count of items removed."""
    try:
        r = await get_redis()
        count = await r.hlen(WORKSPACE_KEY)
        await r.delete(WORKSPACE_KEY)
        return count
    except Exception as e:
        logger.warning("Failed to clear workspace: %s", e)
        return 0


async def get_stats() -> dict:
    """Get workspace statistics."""
    try:
        r = await get_redis()
        items = await get_workspace()
        broadcast = items[:WORKSPACE_CAPACITY]

        agents = {}
        for item in items:
            agents[item.source_agent] = agents.get(item.source_agent, 0) + 1

        return {
            "total_items": len(items),
            "broadcast_items": len(broadcast),
            "capacity": WORKSPACE_CAPACITY,
            "utilization": len(broadcast) / WORKSPACE_CAPACITY,
            "agents_active": agents,
            "top_item": broadcast[0].to_dict() if broadcast else None,
            "competition_running": _competition_task is not None
                                   and not _competition_task.done(),
        }
    except Exception as e:
        logger.warning("Failed to get workspace stats: %s", e)
        return {"error": str(e)}


async def _competition_cycle():
    """Background competition cycle — runs at 1Hz.

    Each cycle:
    1. Collect all candidates
    2. Recompute salience scores
    3. Select top-7 (workspace capacity)
    4. Log broadcast winners
    5. Archive losers that expired
    """
    logger.info("GWT competition cycle started (interval=%.1fs)", COMPETITION_INTERVAL)
    while True:
        try:
            items = await get_workspace()  # Already cleans expired, recomputes salience
            broadcast = items[:WORKSPACE_CAPACITY]

            if broadcast:
                logger.debug(
                    "Competition cycle: %d candidates, %d broadcast. Top: %s (%.2f)",
                    len(items), len(broadcast),
                    broadcast[0].source_agent, broadcast[0].salience,
                )

            # Archive history + publish broadcast via pub/sub
            if broadcast:
                r = await get_redis()
                entry = json.dumps({
                    "timestamp": time.time(),
                    "broadcast": [i.to_dict() for i in broadcast],
                    "total_candidates": len(items),
                })
                await r.lpush(WORKSPACE_HISTORY_KEY, entry)
                await r.ltrim(WORKSPACE_HISTORY_KEY, 0, 99)

                # Publish to subscribers (Phase 2 pub/sub)
                await r.publish(WORKSPACE_BROADCAST_CHANNEL, entry)

        except Exception as e:
            logger.warning("Competition cycle error: %s", e)

        await asyncio.sleep(COMPETITION_INTERVAL)


AGENT_REGISTRY_KEY = "athanor:agents:registry"


async def register_agent(
    name: str,
    capabilities: list[str],
    agent_type: str = "reactive",
    subscriptions: list[str] | None = None,
):
    """Register an agent's capabilities in Redis for discovery.

    Args:
        name: Agent name (e.g., "media-agent")
        capabilities: List of tool names the agent provides
        agent_type: "reactive" (on-demand) or "proactive" (scheduled)
        subscriptions: Workspace topics this agent cares about
    """
    try:
        r = await get_redis()
        entry = json.dumps({
            "name": name,
            "capabilities": capabilities,
            "type": agent_type,
            "subscriptions": subscriptions or [],
            "registered_at": time.time(),
            "status": "online",
        })
        await r.hset(AGENT_REGISTRY_KEY, name, entry)
        logger.info("Agent '%s' registered (%d capabilities)", name, len(capabilities))
    except Exception as e:
        logger.warning("Failed to register agent '%s': %s", name, e)


async def get_registered_agents() -> dict[str, dict]:
    """Get all registered agents from Redis."""
    try:
        r = await get_redis()
        raw = await r.hgetall(AGENT_REGISTRY_KEY)
        return {k: json.loads(v) for k, v in raw.items()}
    except Exception as e:
        logger.warning("Failed to get registered agents: %s", e)
        return {}


async def start_competition():
    """Start the background competition cycle."""
    global _competition_task
    if _competition_task is not None and not _competition_task.done():
        logger.info("Competition cycle already running")
        return

    # Verify Redis connectivity first
    try:
        r = await get_redis()
        await r.ping()
        _competition_task = asyncio.create_task(_competition_cycle())
        logger.info("GWT workspace competition started")
    except Exception as e:
        logger.warning("Redis not available, GWT workspace disabled: %s", e)


async def stop_competition():
    """Stop the background competition cycle."""
    global _competition_task
    if _competition_task:
        _competition_task.cancel()
        try:
            await _competition_task
        except asyncio.CancelledError:
            pass
        _competition_task = None
        logger.info("GWT workspace competition stopped")
