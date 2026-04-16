"""Goals API — feedback, steering goals, trust calibration.

Provides:
- Feedback storage (thumbs up/down on responses)
- Steering goals (user-defined objectives that guide agent behavior)
- Trust scores (derived from feedback + escalation resolution history)
- Rubber-stamp detection (warns if user approves everything blindly)

Goals are stored in Redis. Feedback is stored in the preferences Qdrant collection.
Trust scores are computed on-read from the escalation and feedback history.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from .config import settings
from .durable_state import list_goal_records, soft_delete_goal_record, upsert_goal_record

logger = logging.getLogger(__name__)

GOALS_KEY = "athanor:goals"
FEEDBACK_STATS_KEY = "athanor:feedback:stats"
NOTIFICATION_BUDGET_KEY = "athanor:notification:budget"

# Default daily notification limits per agent
DEFAULT_NOTIFICATION_BUDGET = 10
AGENT_NOTIFICATION_BUDGETS = {
    "general-assistant": 15,
    "home-agent": 20,  # More frequent state changes
    "media-agent": 10,
    "creative-agent": 5,
    "coding-agent": 5,
    "research-agent": 5,
    "knowledge-agent": 5,
    "stash-agent": 5,
}


@dataclass
class Goal:
    """A steering goal that influences agent behavior."""
    id: str
    text: str
    agent: str  # "global" or specific agent name
    priority: str = "normal"  # low, normal, high
    created_at: float = field(default_factory=time.time)
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "agent": self.agent,
            "priority": self.priority,
            "created_at": self.created_at,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        return cls(
            id=data["id"],
            text=data["text"],
            agent=data.get("agent", "global"),
            priority=data.get("priority", "normal"),
            created_at=data.get("created_at", time.time()),
            active=data.get("active", True),
        )


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


# --- Notification Budget ---


async def check_notification_budget(agent: str) -> dict:
    """Check if an agent has remaining notification budget for today.

    Returns dict with: allowed (bool), used (int), limit (int), remaining (int).
    Budget resets daily at midnight UTC via Redis key expiry.
    """
    limit = AGENT_NOTIFICATION_BUDGETS.get(agent, DEFAULT_NOTIFICATION_BUDGET)
    try:
        r = await _get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{NOTIFICATION_BUDGET_KEY}:{agent}:{today}"
        used = int(await r.get(key) or 0)
        return {
            "allowed": used < limit,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
        }
    except Exception as e:
        logger.warning("Notification budget check failed for %s: %s", agent, e)
        return {"allowed": True, "used": 0, "limit": limit, "remaining": limit}


async def increment_notification_count(agent: str) -> int:
    """Increment the daily notification counter for an agent.

    Returns the new count. Key auto-expires at end of UTC day.
    """
    try:
        r = await _get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{NOTIFICATION_BUDGET_KEY}:{agent}:{today}"
        count = await r.incr(key)
        if count == 1:
            # First notification today — set TTL to expire at midnight UTC
            await r.expire(key, 86400)
        return count
    except Exception as e:
        logger.warning("Failed to increment notification count for %s: %s", agent, e)
        return 0


async def get_notification_budgets() -> dict:
    """Get notification budget status for all agents."""
    from .agents import list_agents

    budgets = {}
    for agent_name in list_agents():
        budgets[agent_name] = await check_notification_budget(agent_name)
    return budgets


# --- Feedback ---


async def store_feedback(
    agent: str,
    message_content: str,
    feedback_type: str,  # "thumbs_up" or "thumbs_down"
    response_content: str = "",
) -> dict:
    """Store feedback on an agent response.

    Writes to both:
    - Qdrant preferences collection (for semantic retrieval during context injection)
    - Redis feedback stats (for trust score computation)
    """
    from .activity import store_preference

    # Store as preference for context injection
    content = f"User gave {feedback_type.replace('_', ' ')} on response about: {message_content[:200]}"
    if response_content:
        content += f"\nResponse was: {response_content[:300]}"

    await store_preference(
        agent=agent,
        signal_type=feedback_type,
        content=content,
        category="feedback",
        metadata={
            "message_content": message_content[:500],
            "response_content": response_content[:500],
        },
    )

    # Update Redis counters for trust score
    try:
        r = await _get_redis()
        key = f"{FEEDBACK_STATS_KEY}:{agent}"
        await r.hincrby(key, feedback_type, 1)
        await r.hincrby(key, "total", 1)
    except Exception as e:
        logger.warning("Failed to update feedback stats for %s: %s", agent, e)

    return {"status": "stored", "agent": agent, "feedback_type": feedback_type}


async def get_feedback_stats(agent: str = "") -> dict:
    """Get feedback statistics, optionally filtered by agent."""
    try:
        r = await _get_redis()
        if agent:
            key = f"{FEEDBACK_STATS_KEY}:{agent}"
            raw = await r.hgetall(key)
            return {
                "agent": agent,
                "thumbs_up": int(raw.get(b"thumbs_up", raw.get("thumbs_up", 0))),
                "thumbs_down": int(raw.get(b"thumbs_down", raw.get("thumbs_down", 0))),
                "total": int(raw.get(b"total", raw.get("total", 0))),
            }

        # All agents
        from .agents import list_agents

        stats = {}
        for name in list_agents():
            key = f"{FEEDBACK_STATS_KEY}:{name}"
            raw = await r.hgetall(key)
            if raw:
                stats[name] = {
                    "thumbs_up": int(raw.get(b"thumbs_up", raw.get("thumbs_up", 0))),
                    "thumbs_down": int(raw.get(b"thumbs_down", raw.get("thumbs_down", 0))),
                    "total": int(raw.get(b"total", raw.get("total", 0))),
                }
        return stats
    except Exception as e:
        logger.warning("Failed to get feedback stats: %s", e)
        return {}


# --- Goals ---


async def list_goals(agent: str = "", active_only: bool = True) -> list[dict]:
    """List all steering goals, optionally filtered by agent."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(GOALS_KEY)
        goals = []
        for _id, data in raw.items():
            key = _id.decode() if isinstance(_id, bytes) else _id
            val = data.decode() if isinstance(data, bytes) else data
            goal = Goal.from_dict(json.loads(val))
            if active_only and not goal.active:
                continue
            if agent and goal.agent not in (agent, "global"):
                continue
            goals.append(goal.to_dict())
        goals.sort(key=lambda g: g["created_at"], reverse=True)
        return goals
    except Exception as e:
        logger.warning("Failed to list goals: %s", e)
    try:
        return await list_goal_records(agent=agent, active_only=active_only)
    except Exception as e:
        logger.warning("Durable fallback failed while listing goals: %s", e)
        return []


async def create_goal(text: str, agent: str = "global", priority: str = "normal") -> dict:
    """Create a new steering goal."""
    goal = Goal(
        id=f"goal-{uuid.uuid4().hex[:8]}",
        text=text,
        agent=agent,
        priority=priority,
    )
    try:
        r = await _get_redis()
        await r.hset(GOALS_KEY, goal.id, json.dumps(goal.to_dict()))
        logger.info("Created goal %s: %s (agent=%s)", goal.id, text[:50], agent)
        payload = goal.to_dict()
        await upsert_goal_record(payload)
        return payload
    except Exception as e:
        logger.warning("Failed to create goal: %s", e)
    payload = goal.to_dict()
    await upsert_goal_record(payload)
    return payload


async def delete_goal(goal_id: str) -> bool:
    """Delete a goal by ID."""
    removed = False
    try:
        r = await _get_redis()
        removed = (await r.hdel(GOALS_KEY, goal_id)) > 0
    except Exception as e:
        logger.warning("Failed to delete goal %s: %s", goal_id, e)
    durable_removed = await soft_delete_goal_record(goal_id)
    return bool(removed or durable_removed)


async def get_goals_for_agent(agent: str) -> list[str]:
    """Get goal texts relevant to an agent (agent-specific + global).

    Returns list of goal text strings for prompt injection.
    """
    goals = await list_goals(agent=agent, active_only=True)
    return [g["text"] for g in goals]


# --- Trust Scores ---


async def compute_trust_scores() -> dict:
    """Compute trust scores per agent.

    Trust score (0.0-1.0) is derived from:
    - Feedback ratio: thumbs_up / total feedback
    - Escalation history: approve / (approve + reject) ratio
    - Volume penalty: low sample count → score closer to 0.5 (uncertain)

    Also detects rubber-stamping: if >20 approvals with 0 rejections.
    """
    from .escalation import _pending_actions

    feedback = await get_feedback_stats()

    # Compute escalation stats per agent
    escalation_stats: dict[str, dict] = {}
    for action in _pending_actions:
        agent = action.agent
        if agent not in escalation_stats:
            escalation_stats[agent] = {"approved": 0, "rejected": 0, "total": 0}
        if action.resolved:
            escalation_stats[agent]["total"] += 1
            if action.resolution == "approved":
                escalation_stats[agent]["approved"] += 1
            elif action.resolution == "rejected":
                escalation_stats[agent]["rejected"] += 1

    # Merge into trust scores
    from .agents import list_agents

    scores = {}
    rubber_stamp_warning = False

    for agent_name in list_agents():
        fb = feedback.get(agent_name, {})
        es = escalation_stats.get(agent_name, {})

        fb_up = fb.get("thumbs_up", 0)
        fb_down = fb.get("thumbs_down", 0)
        fb_total = fb_up + fb_down

        es_approved = es.get("approved", 0)
        es_rejected = es.get("rejected", 0)
        es_total = es_approved + es_rejected

        # Feedback score (default 0.5 if no data)
        fb_score = fb_up / fb_total if fb_total > 0 else 0.5

        # Escalation score (default 0.5 if no data)
        es_score = es_approved / es_total if es_total > 0 else 0.5

        # Combined score (weighted: feedback 60%, escalation 40%)
        # With sample penalty: scores regress to baseline with fewer samples
        total_samples = fb_total + es_total
        confidence = min(1.0, total_samples / 20)  # Full confidence at 20+ samples
        raw_score = 0.6 * fb_score + 0.4 * es_score

        # Baseline trust: new agents start at 0.55 instead of 0.5 so pipeline
        # tasks can execute at Level B without waiting for 20+ samples.
        # This avoids the cold-start problem where the trust flywheel can't spin
        # because nothing ever executes to generate trust data.
        baseline = 0.55
        trust_score = baseline + (raw_score - 0.5) * confidence

        # Trust grade
        if trust_score >= 0.8:
            grade = "A"
        elif trust_score >= 0.6:
            grade = "B"
        elif trust_score >= 0.4:
            grade = "C"
        else:
            grade = "D"

        # Rubber-stamp detection
        if es_approved > 20 and es_rejected == 0:
            rubber_stamp_warning = True

        scores[agent_name] = {
            "score": round(trust_score, 3),
            "grade": grade,
            "feedback": {"up": fb_up, "down": fb_down, "total": fb_total},
            "escalation": {"approved": es_approved, "rejected": es_rejected, "total": es_total},
            "samples": total_samples,
        }

    result = {"agents": scores}
    if rubber_stamp_warning:
        result["warning"] = (
            "Rubber-stamp detected: some agents have >20 approvals with 0 rejections. "
            "Consider whether escalation thresholds are set too aggressively."
        )
    return result


# --- Trust → Autonomy Graduation ---


async def apply_trust_adjustments() -> dict:
    """Translate trust scores into escalation threshold adjustments.

    Called by the pattern detection scheduler (5:00 AM daily).

    Algorithm:
    - deviation = trust_score - 0.5  (range: -0.5 to +0.5)
    - ROUTINE adjustment = -deviation * 0.2  (max ±0.10)
    - CONTENT adjustment = -deviation * 0.10 (max ±0.05)
    - Negative adjustment → lower threshold → more autonomy (for high-trust agents)
    - Positive adjustment → higher threshold → more oversight (for low-trust agents)
    - Requires ≥10 samples to act. Below 10, adjustments are reset to 0.

    Returns summary dict with per-agent adjustments made.
    """
    from .escalation import set_autonomy_adjustment, ActionCategory

    trust_data = await compute_trust_scores()
    agents = trust_data.get("agents", {})
    applied: dict[str, dict] = {}

    for agent_name, info in agents.items():
        trust_score = info["score"]
        samples = info["samples"]

        if samples < 10:
            # Insufficient data — clear any existing adjustments to neutral
            await set_autonomy_adjustment(agent_name, ActionCategory.ROUTINE.value, 0.0)
            await set_autonomy_adjustment(agent_name, ActionCategory.CONTENT.value, 0.0)
            applied[agent_name] = {"routine": 0.0, "content": 0.0, "samples": samples, "cleared": True}
            continue

        deviation = trust_score - 0.5  # Positive = trust above neutral

        # Scale adjustments: high trust → negative (lower threshold = more autonomy)
        routine_adj = max(-0.10, min(0.10, -deviation * 0.2))
        content_adj = max(-0.05, min(0.05, -deviation * 0.10))

        await set_autonomy_adjustment(agent_name, ActionCategory.ROUTINE.value, routine_adj)
        await set_autonomy_adjustment(agent_name, ActionCategory.CONTENT.value, content_adj)

        applied[agent_name] = {
            "trust_score": trust_score,
            "samples": samples,
            "routine_adj": round(routine_adj, 3),
            "content_adj": round(content_adj, 3),
        }
        logger.info(
            "Trust adjustment applied: %s score=%.3f routine=%.3f content=%.3f (n=%d)",
            agent_name, trust_score, routine_adj, content_adj, samples,
        )

    return {"adjustments": applied, "agent_count": len(applied)}


# --- Daily Digest ---


async def generate_digest_prompt() -> str:
    """Generate the prompt for the daily digest task.

    Gathers current stats and formats them for the general-assistant
    to summarize into a readable morning briefing.
    """
    from .tasks import get_task_stats
    from .escalation import get_unread_count, get_pending

    stats = await get_task_stats()
    pending = get_pending(include_resolved=False)
    unread = get_unread_count()
    trust = await compute_trust_scores()
    goals = await list_goals(active_only=True)

    parts = [
        "Generate a concise morning digest for the Athanor system owner. Include:",
        "",
        f"## Task Stats (last 24h)",
        f"- Total tasks: {stats.get('total', 0)}",
        f"- Completed: {stats.get('completed', 0)}",
        f"- Failed: {stats.get('failed', 0)}",
        f"- Running: {stats.get('running', 0)}",
        f"- Pending: {stats.get('pending', 0)}",
        "",
        f"## Pending Approvals: {unread}",
    ]

    if pending:
        for p in pending[:5]:
            parts.append(f"  - [{p['agent']}] {p['action'][:60]}")

    if goals:
        parts.append("")
        parts.append("## Active Goals")
        for g in goals[:5]:
            parts.append(f"  - [{g['agent']}] {g['text'][:80]}")

    agent_scores = trust.get("agents", {})
    if agent_scores:
        parts.append("")
        parts.append("## Agent Trust Scores")
        for name, info in sorted(agent_scores.items()):
            parts.append(
                f"  - {name}: {info['grade']} ({info['score']:.2f}) "
                f"[{info['samples']} samples]"
            )

    if trust.get("warning"):
        parts.append("")
        parts.append(f"## Warning: {trust['warning']}")

    # Intelligence signals from last 24h
    signals = _get_recent_signals(hours=24)
    if signals:
        parts.append("")
        parts.append(f"## Intelligence Signals ({len(signals)} in last 24h)")
        by_cat: dict[str, list] = {}
        for s in signals:
            cat = s.get("category", "uncategorized")
            by_cat.setdefault(cat, []).append(s)
        for cat, items in sorted(by_cat.items()):
            parts.append(f"  **{cat}** ({len(items)}):")
            for item in sorted(items, key=lambda x: x.get("relevance", 0), reverse=True)[:3]:
                parts.append(f"    - [{item.get('relevance', '?')}] {item.get('title', '?')[:80]}")
                if item.get("summary"):
                    parts.append(f"      {item['summary'][:120]}")

    parts.extend([
        "",
        "Format this as a brief, scannable morning update. Highlight anything "
        "that needs attention. If everything is running smoothly, say so concisely.",
    ])

    return "\n".join(parts)


def _get_recent_signals(hours: int = 24) -> list[dict]:
    """Fetch recent signals from Qdrant, filtered by ingestion time."""
    try:
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = httpx.post(
            f"{settings.qdrant_url}/collections/signals/points/scroll",
            json={
                "limit": 50,
                "with_payload": True,
                "filter": {
                    "must": [
                        {"key": "ingested_at", "range": {"gte": cutoff_iso}}
                    ]
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])
        results = []
        for p in points:
            payload = p.get("payload", {})
            clf = payload.get("classification", {})
            if isinstance(clf, dict) and "error" not in clf:
                results.append({
                    "title": payload.get("title", ""),
                    "category": clf.get("category", "uncategorized"),
                    "relevance": clf.get("relevance", 0),
                    "summary": clf.get("summary", ""),
                    "url": payload.get("url", ""),
                })
        return results
    except Exception as e:
        logger.warning("Failed to fetch recent signals: %s", e)
        return []
