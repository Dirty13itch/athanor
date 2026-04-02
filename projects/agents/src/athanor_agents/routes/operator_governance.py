from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..governance_state import (
    build_governance_snapshot,
    build_governance_drill_snapshot,
    compute_attention_posture,
    enter_system_mode_record,
    get_current_system_mode_record,
    list_attention_budget_records,
    rehearse_governance_drill,
)
from ..operator_contract import build_operator_action, emit_operator_audit_event, require_operator_action


router = APIRouter(prefix="/v1/operator", tags=["operator-governance"])


async def _load_governance_body(
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


@router.get("/governance")
async def get_operator_governance():
    return await build_governance_snapshot()


@router.get("/governance/drills")
async def get_operator_governance_drills():
    return build_governance_drill_snapshot()


@router.post("/governance/drills/{drill_id}/rehearse")
async def rehearse_operator_governance_drill(drill_id: str, request: Request):
    body, action, denial = await _load_governance_body(
        request,
        route=f"/v1/operator/governance/drills/{drill_id}/rehearse",
        action_class="admin",
        default_reason=f"Recorded governance drill rehearsal for {drill_id}",
    )
    if denial:
        return denial

    try:
        artifact = await rehearse_governance_drill(
            drill_id,
            actor=str(body.get("actor") or action.actor or "operator"),
            reason=str(body.get("reason") or action.reason or ""),
            request_context={
                "session_id": action.session_id,
                "correlation_id": action.correlation_id,
            },
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route=f"/v1/operator/governance/drills/{drill_id}/rehearse",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route=f"/v1/operator/governance/drills/{drill_id}/rehearse",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded governance drill rehearsal for {drill_id}",
        target=drill_id,
        metadata={"passed": bool(artifact.get("passed")), "blocker_id": str(artifact.get("blocker_id") or "")},
    )
    return {"status": "recorded", "drill": artifact}


@router.get("/system-mode")
async def get_operator_system_mode():
    current_mode = await get_current_system_mode_record()
    attention = await compute_attention_posture()
    return {"current_mode": current_mode, "attention_posture": attention}


@router.post("/system-mode")
async def set_operator_system_mode(request: Request):
    body, action, denial = await _load_governance_body(
        request,
        route="/v1/operator/system-mode",
        action_class="admin",
        default_reason="Updated operator system mode",
    )
    if denial:
        return denial

    mode = str(body.get("mode") or "").strip()
    if not mode:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/system-mode",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="mode is required",
        )
        return JSONResponse(status_code=400, content={"error": "mode is required"})

    try:
        record = await enter_system_mode_record(
            mode,
            entered_by=str(body.get("actor") or action.actor or "operator"),
            trigger=str(body.get("trigger") or ""),
            exit_conditions=str(body.get("exit_conditions") or ""),
            notes=str(body.get("notes") or ""),
            metadata=dict(body.get("metadata") or {})
            if isinstance(body.get("metadata"), dict) or body.get("metadata") is None
            else {},
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/operator/system-mode",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/operator/system-mode",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Entered system mode {record['mode']}",
        target=record["id"],
        metadata={"mode": record["mode"]},
    )
    return {"status": "updated", "current_mode": record}


@router.get("/attention-budgets")
async def get_operator_attention_budgets(status: str = "", limit: int = 100):
    budgets = await list_attention_budget_records(status=status, limit=limit)
    attention = await compute_attention_posture()
    return {"budgets": budgets, "count": len(budgets), "attention_posture": attention}
