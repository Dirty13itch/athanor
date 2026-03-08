"""GWT-inspired workspace — shared broadcast medium for inter-agent coordination.

Based on Global Workspace Theory (ADR-017): specialized agents compete to
broadcast information through a capacity-limited workspace. Winners are
broadcast to all agents, enabling emergent coordination.

Backed by Redis. Workspace capacity: 7 items (matching GWT's cognitive bottleneck).
Competition cycle: 1Hz (Phase 2). Phase 1 is the basic CRUD + salience scoring.

Phase 3 (this version): Agent subscriptions with keyword-based relevance scoring,
reactive task creation (broadcast → matching agents get tasks), and coalition
endorsement (multiple agents boosting an item's salience).
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
WORKSPACE_SUBSCRIPTIONS_KEY = "athanor:workspace:subscriptions"
WORKSPACE_REACTIONS_KEY = "athanor:workspace:reactions"
WORKSPACE_CAPACITY = 7
COMPETITION_INTERVAL = 1.0  # seconds
COALITION_BONUS = 0.15  # Per-endorsing-agent salience boost
REACTION_COOLDOWN = 300  # Don't re-react to same item within 5 min
MAX_REACTIONS_PER_CYCLE = 2  # Max reactive tasks created per competition cycle

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
class AgentSubscription:
    """An agent's declaration of what workspace topics it cares about.

    Phase 3: agents register keywords, source filters, and relevance thresholds.
    When a broadcast item matches, a reactive task is submitted for that agent.
    """
    agent_name: str = ""
    keywords: list[str] = field(default_factory=list)
    source_filters: list[str] = field(default_factory=list)  # Source agents to react to
    threshold: float = 0.3  # Min keyword relevance to trigger reaction
    react_prompt_template: str = ""  # Template for reactive task prompt

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentSubscription":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


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
    coalition: list[str] = field(default_factory=list)  # Phase 3: endorsing agents

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def compute_salience(item: WorkspaceItem) -> float:
    """Compute salience score for a workspace item.

    Salience = urgency x recency + coalition_bonus
    - Urgency: priority weight
    - Recency: decays over TTL period
    - Coalition: each endorsing agent adds COALITION_BONUS
    """
    urgency = PRIORITY_WEIGHTS.get(ItemPriority(item.priority), 2.0)
    age = time.time() - item.created_at
    recency = max(0.0, 1.0 - (age / item.ttl)) if item.ttl > 0 else 1.0
    base = urgency * recency
    coalition_boost = len(item.coalition) * COALITION_BONUS
    return base + coalition_boost


def compute_keyword_relevance(item: WorkspaceItem, sub: AgentSubscription) -> float:
    """Compute how relevant a workspace item is to an agent's subscription.

    Returns 0.0-1.0 based on keyword matches and source filters.
    """
    content_lower = item.content.lower()
    source_lower = item.source_agent.lower()

    # Source filter match (strong signal)
    source_score = 0.0
    if sub.source_filters:
        for src in sub.source_filters:
            if src.lower() in source_lower:
                source_score = 0.5
                break

    # Keyword match (proportional to matches)
    keyword_score = 0.0
    if sub.keywords:
        matches = sum(1 for kw in sub.keywords if kw.lower() in content_lower)
        keyword_score = min(1.0, matches / max(1, len(sub.keywords) * 0.3))

    # Don't react to own items
    if item.source_agent == sub.agent_name:
        return 0.0

    return min(1.0, source_score + keyword_score)


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
    2. Recompute salience scores (including coalition bonus)
    3. Select top-7 (workspace capacity)
    4. Archive history + publish broadcast via pub/sub
    5. Phase 3: Trigger reactive tasks for subscribed agents
    """
    logger.info("GWT competition cycle started (interval=%.1fs)", COMPETITION_INTERVAL)
    reaction_counter = 0  # Only check reactions every 10 cycles (10s)

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

                # Publish to subscribers
                await r.publish(WORKSPACE_BROADCAST_CHANNEL, entry)

                # Update Continuous State Tensor from broadcast
                try:
                    from .cst import update_cst_from_broadcast

                    # Build broadcast summary for CST update
                    top = broadcast[0]
                    cst_broadcast = {
                        "specialist": top.source_agent,
                        "content": top.content[:200],
                        "confidence": min(top.salience, 1.0),
                        "urgency": 0.5 if top.priority.value in ("critical", "high") else 0.2,
                        "topics": {top.source_agent: 0.3},
                    }
                    await update_cst_from_broadcast(cst_broadcast)
                except Exception as e:
                    logger.debug("CST update failed: %s", e)

            # Phase 3: Trigger reactive tasks every 10 cycles (10s)
            reaction_counter += 1
            if broadcast and reaction_counter >= 10:
                reaction_counter = 0
                try:
                    await _trigger_reactive_tasks(broadcast)
                except Exception as e:
                    logger.warning("Reactive task trigger error: %s", e)

        except Exception as e:
            logger.warning("Competition cycle error: %s", e)

        await asyncio.sleep(COMPETITION_INTERVAL)


# --- Phase 3: Subscriptions, Endorsement, Reactions ---


# Default subscriptions — what each agent cares about
DEFAULT_SUBSCRIPTIONS: dict[str, AgentSubscription] = {
    "media-agent": AgentSubscription(
        agent_name="media-agent",
        keywords=["movie", "show", "episode", "download", "plex", "sonarr", "radarr",
                  "media", "tv", "film", "stream", "torrent", "transcode"],
        source_filters=["event:sonarr", "event:radarr", "event:plex", "event:tdarr"],
        threshold=0.3,
        react_prompt_template=(
            "A workspace broadcast is relevant to your domain: '{content}' "
            "(from {source_agent}). Assess this and take appropriate action — "
            "check media library status, update metadata, or report findings."
        ),
    ),
    "home-agent": AgentSubscription(
        agent_name="home-agent",
        keywords=["motion", "door", "light", "temperature", "humidity", "presence",
                  "home", "room", "sensor", "automation", "climate", "power"],
        source_filters=["event:home-assistant", "event:homeassistant"],
        threshold=0.3,
        react_prompt_template=(
            "Home automation event detected: '{content}' (from {source_agent}). "
            "Check relevant Home Assistant entities and take appropriate action."
        ),
    ),
    "research-agent": AgentSubscription(
        agent_name="research-agent",
        keywords=["research", "investigate", "analyze", "report", "benchmark",
                  "compare", "evaluate", "upgrade", "new version", "release"],
        source_filters=[],
        threshold=0.4,
        react_prompt_template=(
            "A topic needs research: '{content}' (from {source_agent}). "
            "Search for current information and produce a brief summary."
        ),
    ),
    "coding-agent": AgentSubscription(
        agent_name="coding-agent",
        keywords=["code", "bug", "test", "generate", "refactor", "implement",
                  "component", "function", "script", "fix"],
        source_filters=[],
        threshold=0.4,
        react_prompt_template=(
            "A coding task is relevant: '{content}' (from {source_agent}). "
            "Read relevant source files and generate the requested code."
        ),
    ),
    "creative-agent": AgentSubscription(
        agent_name="creative-agent",
        keywords=["image", "portrait", "illustration", "video", "visual",
                  "generate image", "comfyui", "flux", "art", "scene"],
        source_filters=[],
        threshold=0.4,
        react_prompt_template=(
            "A creative request is in the workspace: '{content}' (from {source_agent}). "
            "Craft an appropriate prompt and queue the generation."
        ),
    ),
    "knowledge-agent": AgentSubscription(
        agent_name="knowledge-agent",
        keywords=["knowledge", "document", "index", "search", "qdrant",
                  "docs", "wiki", "reference"],
        source_filters=[],
        threshold=0.5,
        react_prompt_template=(
            "Knowledge-related activity: '{content}' (from {source_agent}). "
            "Check if knowledge base needs updating or can answer the query."
        ),
    ),
}


async def save_subscription(sub: AgentSubscription) -> None:
    """Save or update an agent's subscription in Redis."""
    try:
        r = await get_redis()
        await r.hset(WORKSPACE_SUBSCRIPTIONS_KEY, sub.agent_name, json.dumps(sub.to_dict()))
        logger.info("Subscription saved for %s (%d keywords)", sub.agent_name, len(sub.keywords))
    except Exception as e:
        logger.warning("Failed to save subscription for %s: %s", sub.agent_name, e)


async def get_subscriptions() -> dict[str, AgentSubscription]:
    """Get all agent subscriptions from Redis, falling back to defaults."""
    try:
        r = await get_redis()
        raw = await r.hgetall(WORKSPACE_SUBSCRIPTIONS_KEY)
        if raw:
            return {k: AgentSubscription.from_dict(json.loads(v)) for k, v in raw.items()}
    except Exception as e:
        logger.warning("Failed to get subscriptions: %s", e)
    return dict(DEFAULT_SUBSCRIPTIONS)


async def initialize_subscriptions() -> None:
    """Load default subscriptions into Redis if none exist."""
    try:
        r = await get_redis()
        existing = await r.hlen(WORKSPACE_SUBSCRIPTIONS_KEY)
        if existing == 0:
            for name, sub in DEFAULT_SUBSCRIPTIONS.items():
                await r.hset(WORKSPACE_SUBSCRIPTIONS_KEY, name, json.dumps(sub.to_dict()))
            logger.info("Initialized %d default agent subscriptions", len(DEFAULT_SUBSCRIPTIONS))
    except Exception as e:
        logger.warning("Failed to initialize subscriptions: %s", e)


async def endorse_item(item_id: str, agent_name: str) -> WorkspaceItem | None:
    """An agent endorses a workspace item, boosting its salience (coalition).

    Returns updated item or None if not found.
    """
    try:
        r = await get_redis()
        raw = await r.hget(WORKSPACE_KEY, item_id)
        if not raw:
            return None

        item = WorkspaceItem.from_dict(json.loads(raw))
        if agent_name not in item.coalition and agent_name != item.source_agent:
            item.coalition.append(agent_name)
            item.salience = compute_salience(item)
            await r.hset(WORKSPACE_KEY, item_id, json.dumps(item.to_dict()))
            logger.info(
                "Item %s endorsed by %s (coalition=%d, salience=%.2f)",
                item_id, agent_name, len(item.coalition), item.salience,
            )
        return item
    except Exception as e:
        logger.warning("Failed to endorse item %s: %s", item_id, e)
        return None


async def _check_reaction_cooldown(item_id: str, agent_name: str) -> bool:
    """Check if an agent has already reacted to this item recently."""
    try:
        r = await get_redis()
        key = f"{WORKSPACE_REACTIONS_KEY}:{agent_name}:{item_id}"
        exists = await r.exists(key)
        return exists > 0
    except Exception:
        return False


async def _set_reaction_cooldown(item_id: str, agent_name: str) -> None:
    """Mark that an agent has reacted to this item."""
    try:
        r = await get_redis()
        key = f"{WORKSPACE_REACTIONS_KEY}:{agent_name}:{item_id}"
        await r.setex(key, REACTION_COOLDOWN, "1")
    except Exception:
        pass


async def _trigger_reactive_tasks(broadcast: list[WorkspaceItem]) -> None:
    """Phase 3: Match broadcast items against subscriptions, create reactive tasks.

    Called each competition cycle. Max MAX_REACTIONS_PER_CYCLE tasks per cycle
    to avoid overwhelming the task queue.
    """
    from .tasks import submit_task

    subs = await get_subscriptions()
    if not subs:
        return

    reactions_this_cycle = 0

    for item in broadcast:
        if reactions_this_cycle >= MAX_REACTIONS_PER_CYCLE:
            break

        for agent_name, sub in subs.items():
            if reactions_this_cycle >= MAX_REACTIONS_PER_CYCLE:
                break

            relevance = compute_keyword_relevance(item, sub)
            if relevance < sub.threshold:
                continue

            # Check cooldown
            if await _check_reaction_cooldown(item.id, agent_name):
                continue

            # Build reactive task prompt
            prompt = sub.react_prompt_template.format(
                content=item.content[:200],
                source_agent=item.source_agent,
            )

            try:
                task = await submit_task(
                    agent=agent_name,
                    prompt=prompt,
                    priority="normal",
                    metadata={
                        "source": "workspace_reaction",
                        "workspace_item_id": item.id,
                        "relevance_score": round(relevance, 3),
                    },
                )
                await _set_reaction_cooldown(item.id, agent_name)
                reactions_this_cycle += 1
                logger.info(
                    "Reactive task %s created: %s reacting to item %s (relevance=%.2f)",
                    task.id, agent_name, item.id, relevance,
                )
            except Exception as e:
                logger.warning("Failed to create reactive task for %s: %s", agent_name, e)


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
        # Phase 3: Initialize default subscriptions
        await initialize_subscriptions()
        _competition_task = asyncio.create_task(_competition_cycle())
        logger.info("GWT workspace competition started (Phase 3: subscriptions active)")
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
