"""Morning Briefing — structured daily digest from multiple data sources.

Gathers data in parallel from:
- Node heartbeats (Redis) — GPU temps, container counts, system load
- Overnight activity (Qdrant) — agent actions in the last 12h
- Task stats (local) — completed/failed/pending tasks
- Prometheus alerts — active firing alerts
- Miniflux RSS (VAULT:8070) — unread article count by category

Returns structured sections sorted by priority, plus a markdown digest.
Wired into the agent server as GET /v1/briefing.

Adapted from Hydra morning_briefing.py (749 LOC) — trimmed to Athanor's
actual data sources, no external APIs (weather, calendar, email).
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

MINIFLUX_URL = os.getenv("MINIFLUX_URL", "http://192.168.1.203:8070")
MINIFLUX_USER = os.getenv("MINIFLUX_USER", "admin")
MINIFLUX_PASS = os.getenv("MINIFLUX_PASS", "")


@dataclass
class BriefingSection:
    title: str
    icon: str
    items: list[dict[str, Any]]
    summary: str
    priority: int  # 1=highest, 5=lowest


@dataclass
class MorningBriefing:
    generated_at: str
    sections: list[BriefingSection]

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "sections": [
                {
                    "title": s.title,
                    "icon": s.icon,
                    "items": s.items,
                    "summary": s.summary,
                    "priority": s.priority,
                }
                for s in sorted(self.sections, key=lambda x: x.priority)
            ],
            "markdown": self.to_markdown(),
        }

    def to_markdown(self) -> str:
        now = datetime.now()
        hour = now.hour
        greeting = (
            "Good morning" if 5 <= hour < 12
            else "Good afternoon" if 12 <= hour < 17
            else "Good evening" if 17 <= hour < 21
            else "Hello"
        )
        lines = [f"# {greeting}, Shaun", f"*{self.generated_at}*", ""]
        for s in sorted(self.sections, key=lambda x: x.priority):
            lines.append(f"## {s.title}")
            lines.append(s.summary)
            if s.items:
                lines.append("")
                for item in s.items[:8]:
                    if isinstance(item, dict):
                        detail = " | ".join(
                            f"{v}" for v in item.values() if v is not None
                        )
                        lines.append(f"- {detail}")
            lines.append("")
        return "\n".join(lines)


# --- Data fetchers (all async, all fault-tolerant) ---


async def fetch_node_health() -> BriefingSection:
    """Node health from Redis heartbeats."""
    try:
        from .workspace import get_redis
        r = await get_redis()
        nodes = ["foundry", "workshop", "dev"]
        items = []
        issues = []
        for node in nodes:
            raw = await r.get(f"athanor:heartbeat:{node}")
            if not raw:
                issues.append(f"{node}: no heartbeat")
                items.append({"node": node, "status": "no heartbeat"})
                continue
            data = json.loads(raw)
            age = time.time() - data.get("timestamp", 0)
            gpus = data.get("gpus", [])
            containers = data.get("containers", 0)
            load = data.get("load_1m", 0)
            gpu_summary = ", ".join(
                f"{g.get('name','?')} {g.get('temp',0)}C {g.get('util',0)}%"
                for g in gpus
            ) if gpus else "no GPUs"
            status = "healthy" if age < 60 else f"stale ({int(age)}s)"
            if age > 60:
                issues.append(f"{node}: heartbeat stale ({int(age)}s)")
            items.append({
                "node": node,
                "status": status,
                "gpus": gpu_summary,
                "containers": containers,
                "load": f"{load:.1f}",
            })

        if issues:
            summary = f"Issues: {'; '.join(issues)}"
            priority = 1
        else:
            summary = f"All {len(nodes)} nodes healthy."
            priority = 4
        return BriefingSection(
            title="Node Health", icon="server",
            items=items, summary=summary, priority=priority,
        )
    except Exception as e:
        logger.warning("briefing: node health failed: %s", e)
        return BriefingSection(
            title="Node Health", icon="server",
            items=[], summary=f"Unable to fetch: {e}", priority=3,
        )


async def fetch_overnight_activity() -> BriefingSection:
    """Agent activity from last 12 hours via Qdrant."""
    try:
        from .activity import query_activity
        cutoff = int((datetime.now() - timedelta(hours=12)).timestamp())
        activity = await query_activity(limit=50, since_unix=cutoff)
        if not activity:
            return BriefingSection(
                title="Overnight Activity", icon="activity",
                items=[], summary="No agent activity in the last 12 hours.",
                priority=4,
            )
        # Aggregate by agent
        by_agent: dict[str, int] = {}
        for a in activity:
            agent = a.get("agent", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1
        items = [
            {"agent": agent, "actions": count}
            for agent, count in sorted(by_agent.items(), key=lambda x: -x[1])
        ]
        summary = f"{len(activity)} agent actions in the last 12h across {len(by_agent)} agents."
        return BriefingSection(
            title="Overnight Activity", icon="activity",
            items=items, summary=summary, priority=3,
        )
    except Exception as e:
        logger.warning("briefing: activity query failed: %s", e)
        return BriefingSection(
            title="Overnight Activity", icon="activity",
            items=[], summary=f"Unable to fetch: {e}", priority=4,
        )


async def fetch_task_stats() -> BriefingSection:
    """Task execution stats from local task engine."""
    try:
        from .tasks import get_task_stats
        stats = await get_task_stats()
        total = stats.get("total", 0)
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        running = stats.get("running", 0)
        pending = stats.get("pending", 0)
        items = [
            {"metric": "Total", "value": total},
            {"metric": "Completed", "value": completed},
            {"metric": "Failed", "value": failed},
            {"metric": "Running", "value": running},
            {"metric": "Pending", "value": pending},
        ]
        if failed > 0:
            summary = f"{failed} task(s) failed. {completed} completed, {running} running."
            priority = 2
        elif total == 0:
            summary = "No tasks in the last 24h."
            priority = 4
        else:
            summary = f"{completed}/{total} tasks completed successfully."
            priority = 4
        return BriefingSection(
            title="Task Stats", icon="check-square",
            items=items, summary=summary, priority=priority,
        )
    except Exception as e:
        logger.warning("briefing: task stats failed: %s", e)
        return BriefingSection(
            title="Task Stats", icon="check-square",
            items=[], summary=f"Unable to fetch: {e}", priority=4,
        )


async def fetch_alerts() -> BriefingSection:
    """Active alerts from Prometheus."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.prometheus_url}/api/v1/alerts")
            resp.raise_for_status()
            alerts = resp.json().get("data", {}).get("alerts", [])
            firing = [a for a in alerts if a.get("state") == "firing"]
            if not firing:
                return BriefingSection(
                    title="Alerts", icon="bell",
                    items=[], summary="No active alerts.", priority=5,
                )
            items = [
                {
                    "alert": a.get("labels", {}).get("alertname", "?"),
                    "severity": a.get("labels", {}).get("severity", "?"),
                    "summary": a.get("annotations", {}).get("summary", "")[:100],
                }
                for a in firing[:10]
            ]
            summary = f"{len(firing)} active alert(s) firing."
            return BriefingSection(
                title="Alerts", icon="bell",
                items=items, summary=summary, priority=1,
            )
    except Exception as e:
        logger.warning("briefing: prometheus alerts failed: %s", e)
        return BriefingSection(
            title="Alerts", icon="bell",
            items=[], summary=f"Unable to fetch: {e}", priority=3,
        )


async def fetch_rss_news() -> BriefingSection | None:
    """Unread articles from Miniflux RSS reader."""
    if not MINIFLUX_PASS:
        return None
    try:
        auth = httpx.BasicAuth(MINIFLUX_USER, MINIFLUX_PASS)
        async with httpx.AsyncClient(timeout=10, auth=auth) as client:
            resp = await client.get(f"{MINIFLUX_URL}/v1/feeds/counters")
            resp.raise_for_status()
            counters = resp.json()
            unreads = counters.get("unreads", {})
            total_unread = sum(unreads.values())

            if total_unread == 0:
                return BriefingSection(
                    title="RSS News", icon="rss",
                    items=[], summary="No unread articles.", priority=5,
                )

            # Get category breakdown
            resp2 = await client.get(f"{MINIFLUX_URL}/v1/categories")
            categories = {
                str(c["id"]): c["title"]
                for c in resp2.json()
            } if resp2.status_code == 200 else {}

            # Get feed → category mapping
            resp3 = await client.get(f"{MINIFLUX_URL}/v1/feeds")
            feed_cat = {}
            if resp3.status_code == 200:
                for feed in resp3.json():
                    feed_cat[str(feed["id"])] = categories.get(
                        str(feed.get("category", {}).get("id", "")), "Other"
                    )

            # Aggregate by category
            by_cat: dict[str, int] = {}
            for feed_id, count in unreads.items():
                if count > 0:
                    cat = feed_cat.get(str(feed_id), "Other")
                    by_cat[cat] = by_cat.get(cat, 0) + count

            items = [
                {"category": cat, "unread": count}
                for cat, count in sorted(by_cat.items(), key=lambda x: -x[1])
            ]
            summary = f"{total_unread} unread articles across {len(by_cat)} categories."
            return BriefingSection(
                title="RSS News", icon="rss",
                items=items, summary=summary, priority=3,
            )
    except Exception as e:
        logger.warning("briefing: miniflux failed: %s", e)
        return None


# --- Generator ---


async def generate_briefing() -> MorningBriefing:
    """Generate complete morning briefing from all data sources in parallel."""
    results = await asyncio.gather(
        fetch_node_health(),
        fetch_overnight_activity(),
        fetch_task_stats(),
        fetch_alerts(),
        fetch_rss_news(),
        return_exceptions=True,
    )
    sections = []
    for result in results:
        if isinstance(result, BriefingSection):
            sections.append(result)
        elif isinstance(result, Exception):
            logger.error("Briefing section failed: %s", result)

    return MorningBriefing(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M %Z"),
        sections=sections,
    )
