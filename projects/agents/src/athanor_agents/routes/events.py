"""Event ingestion, alerts, and pattern detection routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["events"])

EVENT_PRIORITY_MAP = {
    "alert": "critical",
    "state_change": "normal",
    "schedule": "low",
    "webhook": "normal",
}


@router.post("/events")
async def ingest_event(request: Request):
    """Ingest an external event and convert it to a workspace item."""
    from ..workspace import post_item

    body = await request.json()
    source = body.get("source", "external")
    event_type = body.get("event_type", "webhook")
    content = body.get("content", "")
    metadata = body.get("metadata", {})
    priority = EVENT_PRIORITY_MAP.get(event_type, "normal")

    if not content:
        return JSONResponse(status_code=400, content={"error": "content is required"})

    metadata["event_type"] = event_type
    metadata["source"] = source

    item = await post_item(
        source_agent=f"event:{source}",
        content=content,
        priority=priority,
        ttl=600,
        metadata=metadata,
    )

    return {
        "status": "ingested",
        "item_id": item.id,
        "priority": priority,
        "salience": item.salience,
    }


@router.get("/events/query")
async def query_events_endpoint(
    event_type: str = "",
    agent: str = "",
    limit: int = 50,
    since_unix: int = 0,
):
    """Query structured system events for pattern detection."""
    from ..activity import query_events

    events = await query_events(
        event_type=event_type,
        agent=agent,
        limit=limit,
        since_unix=since_unix,
    )
    return {"events": events, "count": len(events)}


@router.get("/alerts")
async def get_alerts():
    """Get currently firing Prometheus alerts and recent history."""
    from ..alerts import get_active_alerts, get_alert_history

    active = await get_active_alerts()
    history = await get_alert_history(limit=20)
    return {**active, "history": history}


@router.post("/alerts/check")
async def trigger_alert_check():
    """Manually trigger a Prometheus alert check."""
    from ..alerts import check_prometheus_alerts

    return await check_prometheus_alerts()


@router.get("/patterns")
async def get_patterns(agent: str = ""):
    """Get the latest pattern detection report."""
    from ..patterns import get_latest_report, get_agent_patterns

    if agent:
        patterns = await get_agent_patterns(agent)
        return {"agent": agent, "patterns": patterns, "count": len(patterns)}

    report = await get_latest_report()
    if not report:
        return {"patterns": [], "recommendations": [], "message": "No pattern report yet. Runs daily at 5:00 AM."}
    return report


@router.post("/patterns/run")
async def trigger_pattern_detection():
    """Manually trigger pattern detection."""
    from ..patterns import run_pattern_detection

    report = await run_pattern_detection()
    return report
