"""Activity & preference routes — query activity, conversations, preferences."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["activity"])


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


@router.get("/activity")
async def get_activity(
    agent: str = "",
    action_type: str = "",
    limit: int = 20,
    since: int = 0,
):
    """Query recent agent activity."""
    from ..activity import query_activity

    results = await query_activity(
        agent=agent, action_type=action_type, limit=limit, since_unix=since
    )
    return {"activity": results, "count": len(results)}


@router.get("/conversations")
async def get_conversations(
    agent: str = "",
    limit: int = 20,
    since: int = 0,
):
    """Query recent conversations."""
    from ..activity import query_conversations

    results = await query_conversations(agent=agent, limit=limit, since_unix=since)
    return {"conversations": results, "count": len(results)}


@router.get("/preferences")
async def get_preferences(query: str = "", agent: str = "", limit: int = 10):
    """Search stored user preferences by semantic similarity."""
    from ..activity import query_preferences

    if not query:
        return {"preferences": [], "count": 0, "note": "Provide ?query= to search"}

    results = await query_preferences(query=query, agent=agent, limit=limit)
    return {"preferences": results, "count": len(results)}


@router.post("/preferences")
async def add_preference(request: Request):
    """Store a new user preference signal."""
    from ..activity import store_preference

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/preferences",
        action_class="operator",
        default_reason="Stored preference signal",
    )
    if denial:
        return denial
    agent_name = body.get("agent", "global")
    signal_type = body.get("signal_type", "remember_this")
    content = body.get("content", "")
    category = body.get("category", "")
    metadata = body.get("metadata")

    if not content:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="content is required",
            metadata={"agent": str(agent_name), "signal_type": str(signal_type)},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "content is required"},
        )

    await store_preference(
        agent=agent_name,
        signal_type=signal_type,
        content=content,
        category=category,
        metadata=metadata,
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/preferences",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Stored preference signal for {agent_name}",
        target=str(agent_name),
        metadata={
            "agent": str(agent_name),
            "signal_type": str(signal_type),
            "category": str(category or ""),
        },
    )
    return {"status": "stored", "agent": agent_name, "signal_type": signal_type}
