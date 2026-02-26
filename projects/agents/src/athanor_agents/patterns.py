"""Pattern Detection — daily analysis of events and activity logs.

Runs as a scheduled batch job (5:00 AM local time).
Analyzes the last 24h of events to detect:
- Failure clusters (agent failing repeatedly on same type of task)
- Feedback trends (positive/negative trajectories per agent)
- Escalation frequency (agents triggering too many NOTIFY/ASK)
- Schedule reliability (missed or late scheduled runs)

Results are stored in Redis as a daily pattern report.
Agents can read patterns via context injection for self-improvement.
"""

import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PATTERN_REPORT_KEY = "athanor:patterns:report"
PATTERN_HISTORY_KEY = "athanor:patterns:history"


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def run_pattern_detection() -> dict:
    """Run pattern detection over the last 24 hours of events.

    Returns a report dict with detected patterns and recommendations.
    """
    from .activity import query_events, query_activity

    since = int(time.time()) - 86400  # Last 24 hours

    # Gather data
    events = await query_events(limit=500, since_unix=since)
    activity = await query_activity(limit=200, since_unix=since)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "period_hours": 24,
        "event_count": len(events),
        "activity_count": len(activity),
        "patterns": [],
        "recommendations": [],
    }

    # --- Failure cluster detection ---
    failures = [e for e in events if e["event_type"] == "task_failed"]
    if failures:
        failure_by_agent = Counter(e["agent"] for e in failures)
        for agent, count in failure_by_agent.most_common():
            if count >= 3:
                errors = [e["description"][:100] for e in failures if e["agent"] == agent]
                report["patterns"].append({
                    "type": "failure_cluster",
                    "agent": agent,
                    "count": count,
                    "sample_errors": errors[:3],
                    "severity": "high" if count >= 5 else "medium",
                })
                report["recommendations"].append(
                    f"{agent} failed {count} times in 24h. Review task prompts and tool access."
                )

    # --- Feedback trend detection ---
    feedback_events = [e for e in events if e["event_type"] == "feedback_received"]
    if feedback_events:
        fb_by_agent: dict[str, dict] = defaultdict(lambda: {"up": 0, "down": 0})
        for e in feedback_events:
            fb_type = e.get("data", {}).get("feedback_type", "")
            if fb_type == "thumbs_up":
                fb_by_agent[e["agent"]]["up"] += 1
            elif fb_type == "thumbs_down":
                fb_by_agent[e["agent"]]["down"] += 1

        for agent, counts in fb_by_agent.items():
            total = counts["up"] + counts["down"]
            if total >= 3 and counts["down"] > counts["up"]:
                report["patterns"].append({
                    "type": "negative_feedback_trend",
                    "agent": agent,
                    "thumbs_up": counts["up"],
                    "thumbs_down": counts["down"],
                    "severity": "high",
                })
                report["recommendations"].append(
                    f"{agent} received more negative than positive feedback ({counts['down']}↓ vs {counts['up']}↑). "
                    f"Consider adjusting behavior or escalation thresholds."
                )

    # --- Escalation frequency ---
    escalations = [e for e in events if e["event_type"] == "escalation_triggered"]
    if escalations:
        esc_by_agent = Counter(e["agent"] for e in escalations)
        for agent, count in esc_by_agent.most_common():
            if count >= 10:
                tiers = Counter(
                    e.get("data", {}).get("tier", "unknown")
                    for e in escalations if e["agent"] == agent
                )
                report["patterns"].append({
                    "type": "high_escalation_rate",
                    "agent": agent,
                    "count": count,
                    "tiers": dict(tiers),
                    "severity": "medium",
                })
                report["recommendations"].append(
                    f"{agent} triggered {count} escalations in 24h. "
                    f"May need higher autonomy or adjusted confidence thresholds."
                )

    # --- Schedule reliability ---
    schedule_runs = [e for e in events if e["event_type"] == "schedule_run"]
    if schedule_runs:
        runs_by_agent = Counter(e["agent"] for e in schedule_runs)
        report["patterns"].append({
            "type": "schedule_summary",
            "runs_per_agent": dict(runs_by_agent),
            "total_runs": len(schedule_runs),
            "severity": "info",
        })

    # --- Task throughput summary ---
    completions = [e for e in events if e["event_type"] == "task_completed"]
    if completions or failures:
        total = len(completions) + len(failures)
        success_rate = len(completions) / total if total > 0 else 1.0
        report["patterns"].append({
            "type": "task_throughput",
            "completed": len(completions),
            "failed": len(failures),
            "total": total,
            "success_rate": round(success_rate, 3),
            "severity": "info" if success_rate >= 0.8 else "medium",
        })
        if success_rate < 0.8:
            report["recommendations"].append(
                f"Task success rate is {success_rate:.0%} ({len(failures)} failures out of {total}). "
                f"Investigate failing agents."
            )

    # --- Autonomy auto-graduation ---
    await _apply_autonomy_adjustments(report, events, failures, feedback_events)

    # --- Store report in Redis ---
    try:
        r = await _get_redis()
        await r.set(PATTERN_REPORT_KEY, json.dumps(report))

        # Keep 7-day history
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await r.hset(PATTERN_HISTORY_KEY, today, json.dumps(report))

        # Prune history older than 7 days
        all_dates = await r.hkeys(PATTERN_HISTORY_KEY)
        for date_key in all_dates:
            d = date_key.decode() if isinstance(date_key, bytes) else date_key
            try:
                age_days = (datetime.now(timezone.utc) - datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
                if age_days > 7:
                    await r.hdel(PATTERN_HISTORY_KEY, d)
            except ValueError:
                pass
    except Exception as e:
        logger.warning("Failed to store pattern report: %s", e)

    pattern_count = len(report["patterns"])
    rec_count = len(report["recommendations"])
    logger.info(
        "Pattern detection complete: %d events, %d patterns, %d recommendations",
        len(events), pattern_count, rec_count,
    )

    return report


async def _apply_autonomy_adjustments(
    report: dict,
    events: list[dict],
    failures: list[dict],
    feedback_events: list[dict],
):
    """Adjust autonomy levels based on detected patterns.

    Rules:
    - Agent with 5+ successful tasks and 0 failures → lower threshold by 0.02
      (more autonomy, capped at -0.15 total adjustment)
    - Agent with 3+ failures → raise threshold by 0.05 (less autonomy)
    - Agent with negative feedback trend → raise threshold by 0.03
    - Adjustments are cumulative but clamped to ±0.15
    """
    from .escalation import get_all_adjustments, set_autonomy_adjustment

    current = await get_all_adjustments()
    completions = [e for e in events if e["event_type"] == "task_completed"]

    # Count per-agent completions and failures
    comp_by_agent = Counter(e["agent"] for e in completions)
    fail_by_agent = Counter(e["agent"] for e in failures)

    # Get agents with negative feedback
    negative_agents = set()
    fb_by_agent: dict[str, dict] = defaultdict(lambda: {"up": 0, "down": 0})
    for e in feedback_events:
        fb_type = e.get("data", {}).get("feedback_type", "")
        if fb_type == "thumbs_up":
            fb_by_agent[e["agent"]]["up"] += 1
        elif fb_type == "thumbs_down":
            fb_by_agent[e["agent"]]["down"] += 1
    for agent, counts in fb_by_agent.items():
        if counts["down"] > counts["up"] and (counts["up"] + counts["down"]) >= 3:
            negative_agents.add(agent)

    adjustments_made = []

    # All agents that had any activity
    all_agents = set(comp_by_agent.keys()) | set(fail_by_agent.keys()) | negative_agents

    for agent in all_agents:
        comps = comp_by_agent.get(agent, 0)
        fails = fail_by_agent.get(agent, 0)

        # Default category for graduated adjustments: "routine"
        # (most common action type for scheduled tasks)
        category = "routine"
        key = f"{agent}:{category}"
        current_adj = current.get(key, 0.0)

        delta = 0.0

        # Reward: 5+ completions with 0 failures
        if comps >= 5 and fails == 0:
            delta -= 0.02  # Lower threshold = more autonomy

        # Penalize: 3+ failures
        if fails >= 3:
            delta += 0.05  # Raise threshold = less autonomy

        # Penalize: negative feedback trend
        if agent in negative_agents:
            delta += 0.03

        if delta != 0.0:
            new_adj = current_adj + delta
            await set_autonomy_adjustment(agent, category, new_adj)
            adjustments_made.append({
                "agent": agent,
                "category": category,
                "previous": round(current_adj, 3),
                "delta": round(delta, 3),
                "new": round(new_adj, 3),
            })

    if adjustments_made:
        report["autonomy_adjustments"] = adjustments_made
        logger.info("Autonomy adjustments applied: %d agents", len(adjustments_made))


async def get_latest_report() -> dict | None:
    """Get the most recent pattern detection report."""
    try:
        r = await _get_redis()
        raw = await r.get(PATTERN_REPORT_KEY)
        if raw:
            data = raw.decode() if isinstance(raw, bytes) else raw
            return json.loads(data)
    except Exception as e:
        logger.warning("Failed to get pattern report: %s", e)
    return None


async def get_agent_patterns(agent: str) -> list[dict]:
    """Get patterns relevant to a specific agent.

    Used by context injection to give agents self-awareness about their performance.
    """
    report = await get_latest_report()
    if not report:
        return []

    relevant = []
    for pattern in report.get("patterns", []):
        # Direct agent match
        if pattern.get("agent") == agent:
            relevant.append(pattern)
        # Schedule summary includes all agents
        elif pattern.get("type") == "schedule_summary":
            runs = pattern.get("runs_per_agent", {})
            if agent in runs:
                relevant.append({
                    "type": "schedule_summary",
                    "runs": runs[agent],
                    "severity": "info",
                })
        # Throughput is global context
        elif pattern.get("type") == "task_throughput":
            relevant.append(pattern)

    return relevant
