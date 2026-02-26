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


class EscalationTier(str, Enum):
    ACT = "act"
    NOTIFY = "notify"
    ASK = "ask"


class ActionCategory(str, Enum):
    READ = "read"           # Status queries, searches — zero stakes
    ROUTINE = "routine"     # Routine adjustments (lights, temp ±1)
    CONTENT = "content"     # Content additions (add show/movie)
    DELETE = "delete"       # Deletions (remove content, disable automation)
    CONFIG = "config"       # Configuration changes
    SECURITY = "security"   # Security-related actions


# Default thresholds: minimum confidence to act autonomously
DEFAULT_THRESHOLDS: dict[ActionCategory, float] = {
    ActionCategory.READ: 0.0,       # Always act on reads
    ActionCategory.ROUTINE: 0.5,    # Low-stakes adjustments
    ActionCategory.CONTENT: 0.8,    # Medium-stakes additions
    ActionCategory.DELETE: 0.95,    # High-stakes deletions
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


# In-memory notification queue (will be backed by Redis in Phase 4)
_pending_actions: list[PendingAction] = []
_notification_counter: int = 0


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
                url="/tasks",
                actions=[
                    {"action": "approve", "title": "Approve"},
                    {"action": "reject", "title": "Reject"},
                ],
                data={"taskId": pending.id, "agent": pending.agent},
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
                data={"agent": pending.agent, "content": pending.description[:200]},
            )

        # Increment budget counter
        try:
            from .goals import increment_notification_count
            await increment_notification_count(pending.agent)
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_send())
        else:
            loop.run_until_complete(_send())
    except RuntimeError:
        # No event loop — skip push
        pass


def get_threshold(agent: str, category: ActionCategory) -> float:
    """Get the autonomous action threshold for an agent + action category."""
    agent_overrides = AGENT_THRESHOLDS.get(agent, {})
    if category in agent_overrides:
        return agent_overrides[category]
    return DEFAULT_THRESHOLDS.get(category, 0.8)


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
