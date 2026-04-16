"""Convention library routes - CRUD, confirm/reject."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["conventions"])


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


@router.get("/conventions")
async def get_conventions(status: str = "confirmed", agent: str = ""):
    """Get conventions filtered by status and optionally by agent."""
    from ..conventions import get_conventions as _get_conventions

    conventions = await _get_conventions(status=status, agent=agent or None)
    return {
        "conventions": [c.to_dict() for c in conventions],
        "count": len(conventions),
        "status": status,
    }


@router.post("/conventions")
async def propose_convention_endpoint(request: Request):
    """Propose a new convention manually."""
    from ..conventions import propose_convention

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/conventions",
        action_class="operator",
        default_reason="Proposed convention",
    )
    if denial:
        return denial
    conv_type = body.get("type", "behavior")
    agent = body.get("agent", "global")
    description = body.get("description", "")
    rule = body.get("rule", "")
    source = body.get("source", "manual")

    if not description or not rule:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/conventions",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="Both 'description' and 'rule' are required",
        )
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'description' and 'rule' are required"},
        )

    conv = await propose_convention(
        convention_type=conv_type,
        agent=agent,
        description=description,
        rule=rule,
        source=source,
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/conventions",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Proposed convention {conv.id}",
        target=conv.id,
        metadata={"agent": agent, "type": conv_type, "source": source},
    )
    return {"status": conv.status, "convention": conv.to_dict()}


@router.post("/conventions/{convention_id}/confirm")
async def confirm_convention_endpoint(convention_id: str, request: Request):
    """Confirm a proposed convention."""
    from ..conventions import confirm_convention

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/conventions/{convention_id}/confirm",
        action_class="admin",
        default_reason=f"Confirmed convention {convention_id}",
    )
    if denial:
        return denial

    conv = await confirm_convention(convention_id)
    if not conv:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/conventions/{convention_id}/confirm",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail="Convention not found in proposed",
            target=convention_id,
        )
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/conventions/{convention_id}/confirm",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Confirmed convention {convention_id}",
        target=convention_id,
    )
    return {"status": "confirmed", "convention": conv.to_dict()}


@router.post("/conventions/{convention_id}/reject")
async def reject_convention_endpoint(convention_id: str, request: Request):
    """Reject a proposed convention."""
    from ..conventions import reject_convention

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/conventions/{convention_id}/reject",
        action_class="admin",
        default_reason=f"Rejected convention {convention_id}",
    )
    if denial:
        return denial

    conv = await reject_convention(convention_id)
    if not conv:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/conventions/{convention_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail="Convention not found in proposed",
            target=convention_id,
        )
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/conventions/{convention_id}/reject",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Rejected convention {convention_id}",
        target=convention_id,
    )
    return {"status": "rejected", "convention": conv.to_dict()}
