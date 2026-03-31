"""Core memory routes â€” REST API for reading and updating agent persona blocks."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["core-memory"])


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


@router.get("/core-memory")
async def get_all_memories():
    """Get core memories for all agents."""
    from ..core_memory import get_all_core_memories

    memories = await get_all_core_memories()
    return {"memories": memories, "count": len(memories)}


@router.get("/core-memory/{agent}")
async def get_agent_memory(agent: str):
    """Get core memory for a single agent."""
    from ..core_memory import get_core_memory

    memory = await get_core_memory(agent)
    if not memory or not memory.get("bio"):
        return JSONResponse(
            status_code=404,
            content={"error": f"No core memory found for '{agent}'"},
        )
    return {"agent": agent, "memory": memory}


@router.put("/core-memory/{agent}")
async def update_agent_memory(agent: str, request: Request):
    """Update a field in an agent's core memory."""
    from ..core_memory import update_core_memory

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/core-memory/{agent}",
        action_class="admin",
        default_reason=f"Updated core memory for {agent}",
    )
    if denial:
        return denial

    field = body.get("field", "")
    value = body.get("value")

    if not field:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/core-memory/{agent}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="field is required",
            target=agent,
        )
        return JSONResponse(status_code=400, content={"error": "field is required"})
    if value is None:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/core-memory/{agent}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="value is required",
            target=agent,
        )
        return JSONResponse(status_code=400, content={"error": "value is required"})

    try:
        updated = await update_core_memory(agent, field, value)
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/core-memory/{agent}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=agent,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/core-memory/{agent}",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Updated core memory field {field} for {agent}",
        target=agent,
        metadata={"field": field},
    )
    return {"agent": agent, "memory": updated, "updated_field": field}
