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
_last_broadcast_id: str | None = None  # Dedup: skip CST/history when broadcast unchanged


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
            password=settings.redis_password or None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis


# --- Node heartbeat / cluster capacity ---

HEARTBEAT_KEY_PREFIX = "athanor:heartbeat:"
HEARTBEAT_NODES = ("foundry", "workshop", "dev")
HEARTBEAT_STALE_SECONDS = 30.0

# Model-alias → preferred node
_MODEL_ALIAS_MAP: dict[str, str] = {
    "reasoning": "foundry",
    "coordinator": "foundry",
    "utility": "foundry",
    "fast": "foundry",
    "worker": "workshop",
    "embedding": "dev",
    "reranker": "dev",
}

# Agent name → node where its backing model runs
_AGENT_NODE_MAP: dict[str, str] = {
    "media-agent": "foundry",
    "home-agent": "foundry",
    "research-agent": "foundry",
    "coding-agent": "foundry",
    "creative-agent": "workshop",
    "knowledge-agent": "dev",
}


async def get_cluster_capacity() -> dict[str, dict]:
    """Read heartbeat data from Redis for all cluster nodes.

    Returns a dict keyed by node name::

        {
          "foundry": {
            "alive": True,
            "stale": False,
            "timestamp": 1773012824.4,
            "gpus": [ {index, name, vram_used_mib, vram_total_mib, util_pct, ...} ],
            "system": {load_1m, ram_available_mb, ...},
            "models": {"coordinator": {"healthy": True, "model": "..."}},
          },
          ...
        }

    If a heartbeat key is missing the node entry has ``alive: False``.
    """
    r = await get_redis()
    now = time.time()
    capacity: dict[str, dict] = {}

    for node in HEARTBEAT_NODES:
        key = f"{HEARTBEAT_KEY_PREFIX}{node}"
        try:
            raw = await r.get(key)
            if raw is None:
                capacity[node] = {"alive": False, "stale": True, "models": {}}
                continue
            data = json.loads(raw)
            ts = data.get("timestamp", 0)
            capacity[node] = {
                "alive": True,
                "stale": (now - ts) > HEARTBEAT_STALE_SECONDS,
                "timestamp": ts,
                "gpus": data.get("gpus", []),
                "system": data.get("system", {}),
                "models": data.get("models", {}),
            }
        except Exception as e:
            logger.warning("Failed to read heartbeat for %s: %s", node, e)
            capacity[node] = {"alive": False, "stale": True, "models": {}}

    return capacity


async def get_best_node_for_model(model_alias: str) -> tuple[str, bool]:
    """Resolve a model alias to the preferred node and its health status.

    Args:
        model_alias: One of reasoning, coordinator, utility, fast, worker,
                     embedding, reranker.

    Returns:
        (node_name, healthy) — *healthy* is ``True`` when the heartbeat is
        present, not stale, and the matching model slot reports healthy.
    """
    node = _MODEL_ALIAS_MAP.get(model_alias.lower())
    if node is None:
        logger.warning("Unknown model alias '%s', defaulting to foundry", model_alias)
        node = "foundry"

    try:
        capacity = await get_cluster_capacity()
        info = capacity.get(node, {})
        if not info.get("alive") or info.get("stale"):
            return node, False

        # Check the specific model slot that matches the alias
        models = info.get("models", {})
        # Map alias → model slot name in heartbeat
        # Heartbeat slot names: foundry={coordinator,utility}, workshop={worker}, dev={embedding,reranker}
        slot_map = {
            "reasoning": "coordinator",
            "coordinator": "coordinator",
            "utility": "utility",
            "fast": "utility",
            "worker": "worker",
            "embedding": "embedding",
            "reranker": "reranker",
        }
        slot = slot_map.get(model_alias.lower(), "coordinator")
        model_info = models.get(slot, {})
        healthy = model_info.get("healthy", False)
        return node, healthy
    except Exception as e:
        logger.warning("Heartbeat check failed for alias '%s': %s", model_alias, e)
        return node, False


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

    GWT-compliant competition with specialist evaluation:
    1. Collect all workspace candidates
    2. Recompute salience scores (including coalition bonus)
    3. Evaluate specialist salience against workspace content
    4. Active specialists generate proposals (filtered by threshold + inhibition)
    5. Softmax-select winning specialist (stochastic, not deterministic)
    6. Top-7 workspace items become broadcast
    7. Update CST + specialist inhibition
    8. Trigger reactive tasks for subscribed agents
    """
    global _last_broadcast_id
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
            else:
                _last_broadcast_id = None  # Reset so next item always triggers

            # --- Specialist competition ---
            winning_specialist = None
            if broadcast:
                try:
                    winning_specialist = await _run_specialist_competition(broadcast)
                except Exception as e:
                    logger.debug("Specialist competition failed: %s", e)

            # Archive history + publish broadcast via pub/sub
            # Only push when the top broadcast item changes (prevents flooding
            # working memory and history with the same alert every second)
            if broadcast:
                top_id = broadcast[0].id
                broadcast_changed = top_id != _last_broadcast_id

                if broadcast_changed:
                    _last_broadcast_id = top_id
                    r = await get_redis()
                    entry_data = {
                        "timestamp": time.time(),
                        "broadcast": [i.to_dict() for i in broadcast],
                        "total_candidates": len(items),
                    }
                    if winning_specialist:
                        entry_data["winning_specialist"] = winning_specialist
                    entry = json.dumps(entry_data)
                    await r.lpush(WORKSPACE_HISTORY_KEY, entry)
                    await r.ltrim(WORKSPACE_HISTORY_KEY, 0, 99)

                    # Publish to subscribers
                    await r.publish(WORKSPACE_BROADCAST_CHANNEL, entry)

                    # Update Continuous State Tensor from broadcast + specialist
                    try:
                        from .cst import update_cst_from_broadcast

                        top = broadcast[0]
                        cst_broadcast = {
                            "specialist": winning_specialist or top.source_agent,
                            "content": top.content[:200],
                            "confidence": min(top.salience, 1.0),
                            "urgency": 0.5 if top.priority in ("critical", "high") else 0.2,
                            "topics": {top.source_agent: 0.3},
                        }
                        if winning_specialist:
                            cst_broadcast["topics"][winning_specialist] = 0.4
                        await update_cst_from_broadcast(cst_broadcast)
                    except Exception as e:
                        logger.debug("CST update failed: %s", e)

            # Trigger reactive tasks every 10 cycles (10s)
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


async def _run_specialist_competition(
    broadcast: list,
) -> str | None:
    """Run specialist competition against current broadcast items.

    Evaluates all specialists, generates proposals from active ones,
    selects winner via softmax. Updates inhibition for all participants.

    Returns winning specialist agent_name, or None if no specialists active.
    """
    from .specialist import get_specialists, softmax_select, MIN_SALIENCE

    specialists = get_specialists()
    if not specialists:
        return None

    # Build combined text from broadcast items for salience evaluation
    combined_text = " ".join(
        f"{item.source_agent}: {item.content[:100]}"
        for item in broadcast[:3]
    )

    # Phase 1: Evaluate salience for all specialists
    active = []
    salience_scores = []
    for name, specialist in specialists.items():
        salience = specialist.evaluate_salience(combined_text)
        if salience >= MIN_SALIENCE and specialist.inhibition < 0.8:
            active.append(specialist)
            salience_scores.append(salience)

    if not active:
        return None

    # Phase 2: Generate proposals from active specialists
    proposals = []
    for specialist, salience in zip(active, salience_scores):
        proposal = specialist.generate_proposal(
            text=combined_text,
            salience=salience,
        )
        proposals.append(proposal)

    # Phase 3: Score and select via softmax
    competition_scores = [
        specialist.competition_score(proposal.score, salience)
        for specialist, proposal, salience in zip(active, proposals, salience_scores)
    ]

    # Temperature: 0.3 for focused selection in background competition
    winner_idx = softmax_select(competition_scores, temperature=0.3)

    # Phase 4: Update inhibition for all participants
    for i, specialist in enumerate(active):
        specialist.apply_competition_result(won=(i == winner_idx))

    winner = active[winner_idx]
    logger.debug(
        "Specialist competition: %d active, winner=%s (score=%.3f, inhib=%.3f)",
        len(active), winner.agent_name,
        competition_scores[winner_idx], winner.inhibition,
    )

    return winner.agent_name


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
    except Exception as e:
        logger.debug("Reaction cooldown check failed: %s", e)
        return False


async def _set_reaction_cooldown(item_id: str, agent_name: str) -> None:
    """Mark that an agent has reacted to this item."""
    try:
        r = await get_redis()
        key = f"{WORKSPACE_REACTIONS_KEY}:{agent_name}:{item_id}"
        await r.setex(key, REACTION_COOLDOWN, "1")
    except Exception as e:
        logger.debug("Reaction cooldown set failed: %s", e)


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

            # Check node health before queuing work that will fail
            target_node = _AGENT_NODE_MAP.get(agent_name)
            if target_node:
                try:
                    capacity = await get_cluster_capacity()
                    node_info = capacity.get(target_node, {})
                    if not node_info.get("alive") or node_info.get("stale"):
                        logger.warning(
                            "Skipping reactive task for %s: node '%s' heartbeat missing/stale",
                            agent_name, target_node,
                        )
                        continue
                    node_models = node_info.get("models", {})
                    unhealthy = [
                        slot for slot, m in node_models.items()
                        if not m.get("healthy", False)
                    ]
                    if unhealthy:
                        logger.warning(
                            "Skipping reactive task for %s: node '%s' has unhealthy models %s",
                            agent_name, target_node, unhealthy,
                        )
                        continue
                except Exception as e:
                    logger.debug("Heartbeat check failed for %s, proceeding anyway: %s", agent_name, e)

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
