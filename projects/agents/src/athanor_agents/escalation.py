"""Escalation protocol — confidence-based agent behavior tiers.

Three tiers:
- ACT: confidence > threshold → act autonomously, log to activity feed
- NOTIFY: confidence 0.5–threshold → act but send notification
- ASK: confidence < 0.5 → hold in queue, wait for user approval

Thresholds are per-agent and per-action-category.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# Dashboard push notification endpoint (Node 2)
_DASHBOARD_PUSH_URL = settings.dashboard_url + "/api/push/send"
_push_client = httpx.AsyncClient(timeout=5.0)

# ntfy push notification (phone/desktop via VAULT:8880)
_NTFY_URL = settings.ntfy_url
_NTFY_TOPIC = settings.ntfy_topic


class EscalationTier(str, Enum):
    ACT = "act"
    NOTIFY = "notify"
    ASK = "ask"


class ActionCategory(str, Enum):
    READ = "read"           # Status queries, searches — zero stakes
    ROUTINE = "routine"     # Routine adjustments (lights, temp ±1)
    CONTENT = "content"     # Content additions (add show/movie)
    DELETE = "delete"       # Deletions (remove content, disable automation)
    PURGE = "purge"         # Memory tier purge (personal_data, conversations — never autonomous)
    CONFIG = "config"       # Configuration changes
    SECURITY = "security"   # Security-related actions


# Default thresholds: minimum confidence to act autonomously
DEFAULT_THRESHOLDS: dict[ActionCategory, float] = {
    ActionCategory.READ: 0.0,       # Always act on reads
    ActionCategory.ROUTINE: 0.5,    # Low-stakes adjustments
    ActionCategory.CONTENT: 0.8,    # Medium-stakes additions
    ActionCategory.DELETE: 0.95,    # High-stakes deletions
    ActionCategory.PURGE: 1.0,      # Never autonomous (memory tier operations)
    ActionCategory.CONFIG: 0.95,    # High-stakes config changes
    ActionCategory.SECURITY: 1.0,   # Never autonomous
}

# Per-agent threshold overrides (agent → action_category → threshold)
AGENT_THRESHOLDS: dict[str, dict[ActionCategory, float]] = {
    "home-agent": {
        ActionCategory.ROUTINE: 0.4,  # Home automation can be more autonomous
    },
    "media-agent": {
        ActionCategory.CONTENT: 0.85,  # Slightly more cautious with media
    },
}


@dataclass
class PendingAction:
    """An action waiting for user approval."""
    id: str
    agent: str
    action: str
    category: str
    confidence: float
    description: str
    tier: str
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""  # "approved" or "rejected"


# Redis-backed notification queue (persists across container restarts)
_pending_actions: list[PendingAction] = []
_notification_counter: int = 0
_PENDING_REDIS_KEY = "athanor:escalation:pending"
_PENDING_TTL = 86400  # 24 hours — auto-expire unresolved actions


async def _persist_pending(pending: PendingAction):
    """Save a pending action to Redis for persistence across restarts."""
    try:
        from .workspace import get_redis
        r = await get_redis()
        data = {
            "id": pending.id,
            "agent": pending.agent,
            "action": pending.action,
            "category": pending.category,
            "confidence": str(pending.confidence),
            "description": pending.description,
            "tier": pending.tier,
            "created_at": str(pending.created_at),
            "resolved": "1" if pending.resolved else "0",
            "resolution": pending.resolution,
        }
        import json
        await r.hset(_PENDING_REDIS_KEY, pending.id, json.dumps(data))
        await r.expire(_PENDING_REDIS_KEY, _PENDING_TTL)
    except Exception as e:
        logger.debug("Failed to persist pending action to Redis: %s", e)


async def _remove_pending_from_redis(action_id: str):
    """Remove a resolved action from Redis."""
    try:
        from .workspace import get_redis
        r = await get_redis()
        await r.hdel(_PENDING_REDIS_KEY, action_id)
    except Exception as e:
        logger.debug("Failed to remove pending action from Redis: %s", e)


async def load_pending_from_redis():
    """Reload pending actions from Redis on startup."""
    global _pending_actions, _notification_counter
    try:
        from .workspace import get_redis
        import json
        r = await get_redis()
        raw = await r.hgetall(_PENDING_REDIS_KEY)
        loaded = 0
        for key, val in raw.items():
            val_str = val.decode() if isinstance(val, bytes) else val
            data = json.loads(val_str)
            if data.get("resolved") == "1":
                continue
            pending = PendingAction(
                id=data["id"],
                agent=data["agent"],
                action=data["action"],
                category=data["category"],
                confidence=float(data["confidence"]),
                description=data["description"],
                tier=data["tier"],
                created_at=float(data["created_at"]),
            )
            # Avoid duplicates
            if not any(p.id == pending.id for p in _pending_actions):
                _pending_actions.append(pending)
                loaded += 1
        if loaded:
            # Update counter to avoid ID collisions
            _notification_counter = max(_notification_counter, loaded + 100)
            logger.info("Loaded %d pending actions from Redis", loaded)
    except Exception as e:
        logger.debug("Failed to load pending actions from Redis: %s", e)


async def _send_push_notification(
    title: str,
    body: str,
    tag: str = "default",
    url: str = "/",
    actions: list[dict] | None = None,
    data: dict | None = None,
) -> bool:
    """Send a push notification to the dashboard via the push API.

    Checks notification budget before sending. Returns True if sent.
    """
    try:
        payload: dict = {
            "title": title,
            "body": body,
            "tag": tag,
            "url": url,
            "actions": actions or [],
        }
        if data:
            payload["data"] = data

        resp = await _push_client.post(
            _DASHBOARD_PUSH_URL,
            json=payload,
        )
        if resp.status_code == 200:
            result = resp.json()
            sent = result.get("sent", 0)
            if sent > 0:
                logger.info("Push notification sent: %s — %s (%d devices)", title, body[:50], sent)
                return True
            else:
                logger.debug("Push notification: no subscriptions registered")
                return False
        else:
            logger.debug("Push notification failed: HTTP %d", resp.status_code)
            return False
    except Exception as e:
        logger.debug("Push notification failed: %s", e)
        return False


async def _send_ntfy_notification(
    title: str,
    body: str,
    priority: str = "default",
    tags: list[str] | None = None,
) -> bool:
    """Send a notification to ntfy at VAULT:8880 (phone/desktop push)."""
    try:
        headers: dict[str, str] = {
            "Title": title,
            "Priority": priority,
        }
        if tags:
            headers["Tags"] = ",".join(tags)
        resp = await _push_client.post(
            f"{_NTFY_URL}/{_NTFY_TOPIC}",
            content=body.encode(),
            headers=headers,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.debug("ntfy notification failed: %s", e)
        return False


def _fire_push(pending: "PendingAction") -> None:
    """Fire-and-forget push notification for an escalation event.

    Checks notification budget, then sends push. Called from sync functions
    by scheduling on the event loop.
    """
    async def _send():
        # Check notification budget
        try:
            from .goals import check_notification_budget, increment_notification_count
            budget = await check_notification_budget(pending.agent)
            if not budget["allowed"]:
                logger.info(
                    "Push suppressed for %s: budget exhausted (%d/%d)",
                    pending.agent, budget["used"], budget["limit"],
                )
                return
        except Exception:
            pass  # Budget check failure shouldn't block notification

        if pending.tier == EscalationTier.ASK.value:
            # Approval needed — show approve/reject buttons
            await _send_push_notification(
                title=f"🔔 {pending.agent}: Needs approval",
                body=f"{pending.action}\n{pending.description[:100]}",
                tag=f"escalation-{pending.id}",
                url="/notifications",
                actions=[
                    {"action": "approve", "title": "Approve"},
                    {"action": "reject", "title": "Reject"},
                ],
                data={"notificationId": pending.id, "agent": pending.agent, "tier": pending.tier},
            )
            await _send_ntfy_notification(
                title=f"[APPROVAL] {pending.agent}",
                body=f"{pending.action}\n{pending.description[:200]}\n\nReview: {settings.dashboard_url}/notifications",
                priority="high",
                tags=["bell", "rotating_light"],
            )
        else:
            # Notification only — show feedback buttons
            await _send_push_notification(
                title=f"📋 {pending.agent}: {pending.action[:50]}",
                body=pending.description[:100],
                tag=f"notify-{pending.id}",
                url="/activity",
                actions=[
                    {"action": "feedback_up", "title": "👍"},
                    {"action": "feedback_down", "title": "👎"},
                ],
                data={
                    "notificationId": pending.id,
                    "agent": pending.agent,
                    "content": pending.description[:200],
                    "tier": pending.tier,
                },
            )
            await _send_ntfy_notification(
                title=f"{pending.agent}: {pending.action[:60]}",
                body=pending.description[:200],
                priority="default",
                tags=["robot"],
            )

        # Increment budget counter
        try:
            from .goals import increment_notification_count
            await increment_notification_count(pending.agent)
        except Exception as e:
            logger.debug("Notification count increment failed: %s", e)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_send())
        else:
            loop.run_until_complete(_send())
    except RuntimeError:
        # No event loop — skip push
        pass


AUTONOMY_ADJUSTMENTS_KEY = "athanor:autonomy:adjustments"

# Bounds: thresholds can be adjusted within these limits
_MIN_THRESHOLD = 0.0   # READ category already uses 0.0
_MAX_THRESHOLD = 1.0   # SECURITY category already uses 1.0
_MAX_ADJUSTMENT = 0.15  # Max ±0.15 adjustment from base threshold


def get_threshold(agent: str, category: ActionCategory) -> float:
    """Get the autonomous action threshold for an agent + action category.

    Checks for learned autonomy adjustments in Redis (set by pattern detection).
    Falls back to static agent overrides, then defaults.
    """
    # Start with base threshold
    agent_overrides = AGENT_THRESHOLDS.get(agent, {})
    if category in agent_overrides:
        base = agent_overrides[category]
    else:
        base = DEFAULT_THRESHOLDS.get(category, 0.8)

    # Apply learned adjustment from Redis (cached in-memory)
    adjustment = _get_cached_adjustment(agent, category.value)
    if adjustment != 0.0:
        adjusted = max(_MIN_THRESHOLD, min(_MAX_THRESHOLD, base + adjustment))
        return adjusted

    return base


# In-memory cache for autonomy adjustments (refreshed by pattern detection)
_adjustment_cache: dict[str, float] = {}
_adjustment_cache_ts: float = 0.0
_ADJUSTMENT_CACHE_TTL = 300.0  # 5 min cache


def _get_cached_adjustment(agent: str, category: str) -> float:
    """Get cached autonomy adjustment. Returns 0.0 if none."""
    global _adjustment_cache, _adjustment_cache_ts

    # Cache expired — will be refreshed on next async call
    if time.time() - _adjustment_cache_ts > _ADJUSTMENT_CACHE_TTL:
        return 0.0

    key = f"{agent}:{category}"
    return _adjustment_cache.get(key, 0.0)


async def refresh_adjustment_cache():
    """Refresh the in-memory adjustment cache from Redis."""
    global _adjustment_cache, _adjustment_cache_ts

    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.hgetall(AUTONOMY_ADJUSTMENTS_KEY)
        new_cache = {}
        for k, v in raw.items():
            key = k.decode() if isinstance(k, bytes) else k
            val = v.decode() if isinstance(v, bytes) else v
            try:
                new_cache[key] = float(val)
            except ValueError:
                pass
        _adjustment_cache = new_cache
        _adjustment_cache_ts = time.time()
        if new_cache:
            logger.debug("Refreshed autonomy adjustments: %d entries", len(new_cache))
    except Exception as e:
        logger.debug("Failed to refresh autonomy adjustments: %s", e)


async def set_autonomy_adjustment(agent: str, category: str, adjustment: float):
    """Set an autonomy adjustment for an agent+category.

    Positive adjustment = lower threshold = more autonomy.
    Negative adjustment = higher threshold = less autonomy.
    Clamped to ±MAX_ADJUSTMENT.
    """
    adjustment = max(-_MAX_ADJUSTMENT, min(_MAX_ADJUSTMENT, adjustment))

    try:
        from .workspace import get_redis
        r = await get_redis()
        key = f"{agent}:{category}"
        await r.hset(AUTONOMY_ADJUSTMENTS_KEY, key, str(round(adjustment, 3)))

        # Update cache immediately
        _adjustment_cache[key] = adjustment
        logger.info("Set autonomy adjustment: %s = %.3f", key, adjustment)
    except Exception as e:
        logger.warning("Failed to set autonomy adjustment: %s", e)


async def get_all_adjustments() -> dict:
    """Get all current autonomy adjustments."""
    await refresh_adjustment_cache()
    return dict(_adjustment_cache)


def evaluate(
    agent: str,
    action: str,
    category: ActionCategory,
    confidence: float,
) -> EscalationTier:
    """Determine escalation tier for an action.

    Args:
        agent: Agent name
        action: Description of the action
        category: Action category (read, routine, content, etc.)
        confidence: Agent's confidence score (0.0-1.0)

    Returns:
        EscalationTier: act, notify, or ask
    """
    threshold = get_threshold(agent, category)

    if confidence >= threshold:
        return EscalationTier.ACT
    elif confidence >= 0.5:
        return EscalationTier.NOTIFY
    else:
        return EscalationTier.ASK


def queue_pending_action(
    agent: str,
    action: str,
    category: str,
    confidence: float,
    description: str,
) -> PendingAction:
    """Queue an action that needs user approval.

    Returns the PendingAction for tracking.
    """
    global _notification_counter
    _notification_counter += 1

    pending = PendingAction(
        id=f"pending-{_notification_counter}",
        agent=agent,
        action=action,
        category=category,
        confidence=confidence,
        description=description,
        tier=EscalationTier.ASK.value,
    )
    _pending_actions.append(pending)
    logger.info(
        "Queued pending action %s for %s: %s (confidence=%.2f)",
        pending.id, agent, action, confidence,
    )

    # Persist to Redis for survival across restarts
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_persist_pending(pending))
    except RuntimeError:
        pass

    # Fire push notification (async, fire-and-forget)
    _fire_push(pending)

    return pending


def add_notification(
    agent: str,
    action: str,
    category: str,
    confidence: float,
    description: str,
) -> PendingAction:
    """Add a notification (agent acted but wants user to know).

    Returns the notification for tracking.
    """
    global _notification_counter
    _notification_counter += 1

    notif = PendingAction(
        id=f"notif-{_notification_counter}",
        agent=agent,
        action=action,
        category=category,
        confidence=confidence,
        description=description,
        tier=EscalationTier.NOTIFY.value,
        resolved=True,  # Already acted, just informing
        resolution="auto-acted",
    )
    _pending_actions.append(notif)

    # Fire push notification (async, fire-and-forget)
    _fire_push(notif)

    return notif


def get_pending(include_resolved: bool = False) -> list[dict]:
    """Get pending actions, optionally including resolved ones."""
    results = []
    for p in _pending_actions:
        if not include_resolved and p.resolved:
            continue
        results.append({
            "id": p.id,
            "agent": p.agent,
            "action": p.action,
            "category": p.category,
            "confidence": p.confidence,
            "description": p.description,
            "tier": p.tier,
            "created_at": p.created_at,
            "resolved": p.resolved,
            "resolution": p.resolution,
        })
    return results


def resolve_action(action_id: str, approved: bool) -> bool:
    """Resolve a pending action (approve or reject).

    Returns True if action was found and resolved.
    """
    for p in _pending_actions:
        if p.id == action_id and not p.resolved:
            p.resolved = True
            p.resolution = "approved" if approved else "rejected"
            logger.info("Resolved %s: %s", action_id, p.resolution)
            # Remove from Redis
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_remove_pending_from_redis(action_id))
            except RuntimeError:
                pass
            return True
    return False


def get_unread_count() -> int:
    """Get count of unresolved pending actions (for notification badge)."""
    return sum(1 for p in _pending_actions if not p.resolved)


def get_thresholds_config() -> dict:
    """Get all threshold configuration for display/editing."""
    config = {}
    for cat in ActionCategory:
        config[cat.value] = {
            "default": DEFAULT_THRESHOLDS.get(cat, 0.8),
            "agents": {},
        }
    for agent, overrides in AGENT_THRESHOLDS.items():
        for cat, threshold in overrides.items():
            config[cat.value]["agents"][agent] = threshold
    return config
