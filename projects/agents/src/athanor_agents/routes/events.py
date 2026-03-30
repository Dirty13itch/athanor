"""Event ingestion, alerts, and pattern detection routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["events"])

EVENT_PRIORITY_MAP = {
    "alert": "critical",
    "state_change": "normal",
    "schedule": "low",
    "webhook": "normal",
}


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    candidate = build_operator_action(body, default_reason=default_reason)
    try:
        action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service="agent-server",
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


@router.post("/events")
async def ingest_event(request: Request):
    """Ingest an external event and convert it to a workspace item."""
    from ..workspace import post_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/events",
        action_class="operator",
        default_reason="Ingested external event",
    )
    if denial:
        return denial
    source = body.get("source", "external")
    event_type = body.get("event_type", "webhook")
    content = body.get("content", "")
    metadata = body.get("metadata", {})
    priority = EVENT_PRIORITY_MAP.get(event_type, "normal")

    if not content:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/events",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="content is required",
            metadata={"event_type": str(event_type), "source": str(source)},
        )
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
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/events",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Ingested event {event_type} from {source}",
        target=str(item.id),
        metadata={"priority": priority, "event_type": str(event_type), "source": str(source)},
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
async def trigger_alert_check(request: Request):
    """Manually trigger a Prometheus alert check."""
    from ..alerts import check_prometheus_alerts

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/alerts/check",
        action_class="admin",
        default_reason="Triggered alert check",
    )
    if denial:
        return denial

    result = await check_prometheus_alerts()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/alerts/check",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Triggered alert check",
        metadata={
            "alert_count": int(result.get("count", 0) or 0),
            "history_count": int(len(result.get("history", [])) if isinstance(result.get("history"), list) else 0),
        },
    )
    return result


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
async def trigger_pattern_detection(request: Request):
    """Manually trigger pattern detection."""
    from ..patterns import run_pattern_detection

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/patterns/run",
        action_class="admin",
        default_reason="Triggered pattern detection",
    )
    if denial:
        return denial

    report = await run_pattern_detection()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/patterns/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Triggered pattern detection",
        metadata={
            "pattern_count": int(len(report.get("patterns", [])) if isinstance(report.get("patterns"), list) else 0),
            "recommendation_count": int(
                len(report.get("recommendations", [])) if isinstance(report.get("recommendations"), list) else 0
            ),
        },
    )
    return report
