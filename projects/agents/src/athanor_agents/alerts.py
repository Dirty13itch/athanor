"""Prometheus alert polling and notification bridge.

Polls Prometheus for active alerts every 5 minutes (via scheduler).
New alerts are:
1. Pushed to mobile via Web Push (existing push infrastructure)
2. Posted to GWT workspace for agent visibility
3. Logged as events for pattern detection
4. Stored in Redis history for dashboard display

Deduplication: Redis hash stores alert fingerprints with timestamps.
Same alert won't re-notify within a 1-hour cooldown period.
"""

import asyncio
import hashlib
import json
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# Redis keys
ALERTS_SEEN_KEY = "athanor:alerts:seen"       # fingerprint → timestamp
ALERTS_HISTORY_KEY = "athanor:alerts:history"  # list of recent alert events

# Don't re-notify for the same alert within this window
ALERT_COOLDOWN_SECONDS = 3600  # 1 hour

# Dashboard push URL
_DASHBOARD_PUSH_URL = settings.dashboard_url + "/api/push/send"


def _alert_fingerprint(alert: dict) -> str:
    """Generate a stable fingerprint for an alert (sorted labels hash)."""
    labels = alert.get("labels", {})
    key = json.dumps(labels, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()[:16]


async def check_prometheus_alerts() -> dict:
    """Poll Prometheus for firing alerts. Notify on new ones.

    Returns: {checked: bool, active: int, new: int, error?: str}
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.prometheus_url}/api/v1/alerts")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Failed to query Prometheus alerts: %s", e)
        return {"checked": False, "active": 0, "new": 0, "error": str(e)}

    alerts = data.get("data", {}).get("alerts", [])
    firing = [a for a in alerts if a.get("state") == "firing"]

    if not firing:
        return {"checked": True, "active": 0, "new": 0}

    # Dedup against Redis
    from .workspace import get_redis

    r = await get_redis()
    now = time.time()

    new_alerts = []
    for alert in firing:
        fp = _alert_fingerprint(alert)
        last_seen = await r.hget(ALERTS_SEEN_KEY, fp)

        if last_seen:
            ts = float(last_seen.decode() if isinstance(last_seen, bytes) else last_seen)
            if now - ts < ALERT_COOLDOWN_SECONDS:
                continue  # Already notified within cooldown

        new_alerts.append(alert)
        await r.hset(ALERTS_SEEN_KEY, fp, str(now))

    # Clean up stale fingerprints (older than 24h)
    all_fps = await r.hgetall(ALERTS_SEEN_KEY)
    for fp_key, ts_val in all_fps.items():
        ts = float(ts_val.decode() if isinstance(ts_val, bytes) else ts_val)
        if now - ts > 86400:
            await r.hdel(ALERTS_SEEN_KEY, fp_key)

    # Process each new alert
    for alert in new_alerts:
        alertname = alert.get("labels", {}).get("alertname", "Unknown")
        severity = alert.get("labels", {}).get("severity", "warning")
        instance = alert.get("labels", {}).get("instance", "")
        summary = alert.get("annotations", {}).get("summary", "")
        description = alert.get("annotations", {}).get("description", "")
        body = summary or description or f"Alert {alertname} is firing"

        # 1. Push notification to mobile
        asyncio.create_task(_send_push(alertname, severity, body))

        # 2. Post to GWT workspace for agent visibility
        asyncio.create_task(_post_to_workspace(alertname, severity, body, instance))

        # 3. Log event for pattern detection
        from .activity import log_event

        asyncio.create_task(
            log_event(
                event_type="alert_fired",
                agent="system",
                description=f"[{severity}] {alertname}: {body}",
                data={
                    "alertname": alertname,
                    "severity": severity,
                    "instance": instance,
                },
            )
        )

        # 4. Store in history (capped list)
        history_entry = json.dumps(
            {
                "alertname": alertname,
                "severity": severity,
                "body": body,
                "instance": instance,
                "timestamp": now,
            }
        )
        await r.lpush(ALERTS_HISTORY_KEY, history_entry)
        await r.ltrim(ALERTS_HISTORY_KEY, 0, 99)  # Keep last 100

        logger.info(
            "Alert notification: [%s] %s — %s", severity, alertname, body[:100]
        )

    return {"checked": True, "active": len(firing), "new": len(new_alerts)}


async def _send_push(alertname: str, severity: str, body: str):
    """Send push notification for an alert."""
    prefix = "CRITICAL" if severity == "critical" else "WARNING"
    tag = f"alert-{alertname.lower()}"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                _DASHBOARD_PUSH_URL,
                json={
                    "title": f"[{prefix}] {alertname}",
                    "body": body,
                    "tag": tag,
                    "url": "/monitoring",
                    "actions": [],
                },
            )
    except Exception as e:
        logger.warning("Failed to send alert push: %s", e)


async def _post_to_workspace(
    alertname: str, severity: str, body: str, instance: str
):
    """Post alert to GWT workspace for agent awareness."""
    from .workspace import post_item

    priority = "critical" if severity == "critical" else "high"
    try:
        await post_item(
            source_agent="event:prometheus",
            content=f"[{severity.upper()}] {alertname}: {body}",
            priority=priority,
            ttl=1800,  # 30 min TTL for alerts
            metadata={
                "event_type": "alert",
                "alertname": alertname,
                "severity": severity,
                "instance": instance,
            },
        )
    except Exception as e:
        logger.warning("Failed to post alert to workspace: %s", e)


async def get_active_alerts() -> dict:
    """Get currently firing Prometheus alerts (direct query, no dedup).

    Returns: {alerts: [...], count: int, error?: str}
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.prometheus_url}/api/v1/alerts")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return {"alerts": [], "count": 0, "error": str(e)}

    alerts = data.get("data", {}).get("alerts", [])
    result = []
    for a in alerts:
        if a.get("state") != "firing":
            continue
        result.append(
            {
                "alertname": a.get("labels", {}).get("alertname", ""),
                "severity": a.get("labels", {}).get("severity", ""),
                "instance": a.get("labels", {}).get("instance", ""),
                "summary": a.get("annotations", {}).get("summary", ""),
                "description": a.get("annotations", {}).get("description", ""),
                "active_at": a.get("activeAt", ""),
                "state": a.get("state", ""),
            }
        )

    return {"alerts": result, "count": len(result)}


async def get_alert_history(limit: int = 20) -> list[dict]:
    """Get recent alert notification history from Redis."""
    try:
        from .workspace import get_redis

        r = await get_redis()
        entries = await r.lrange(ALERTS_HISTORY_KEY, 0, limit - 1)
        return [
            json.loads(e.decode() if isinstance(e, bytes) else e) for e in entries
        ]
    except Exception:
        return []
