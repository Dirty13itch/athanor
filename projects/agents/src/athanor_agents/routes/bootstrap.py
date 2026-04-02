"""Bootstrap builder routes for the recursive builder stack."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1/bootstrap", tags=["bootstrap"])


async def _load_body(
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


@router.get("/programs")
async def get_bootstrap_programs():
    from ..bootstrap_state import build_bootstrap_runtime_snapshot, list_bootstrap_programs

    programs = await list_bootstrap_programs()
    snapshot = await build_bootstrap_runtime_snapshot(include_snapshot_write=False)
    return {
        "programs": programs,
        "count": len(programs),
        "status": snapshot,
        "takeover": dict(snapshot.get("takeover") or {}),
    }


@router.get("/programs/{program_id}")
async def get_bootstrap_program_detail(program_id: str):
    from ..bootstrap_state import get_bootstrap_program_detail

    program = await get_bootstrap_program_detail(program_id)
    if not program:
        return JSONResponse(status_code=404, content={"error": f"Unknown bootstrap program '{program_id}'"})
    return {"program": program}


@router.get("/slices")
async def get_bootstrap_slices(program_id: str = "", status: str = "", family: str = "", host_id: str = "", limit: int = 50):
    from ..bootstrap_state import list_bootstrap_slices

    slices = await list_bootstrap_slices(program_id=program_id, status=status, family=family, host_id=host_id, limit=limit)
    return {"slices": slices, "count": len(slices)}


@router.get("/handoffs")
async def get_bootstrap_handoffs(slice_id: str = "", status: str = "", limit: int = 50):
    from ..bootstrap_state import list_bootstrap_handoffs

    handoffs = await list_bootstrap_handoffs(slice_id=slice_id, status=status, limit=limit)
    return {"handoffs": handoffs, "count": len(handoffs)}


@router.get("/blockers")
async def get_bootstrap_blockers(status: str = "", family: str = "", limit: int = 50):
    from ..bootstrap_state import list_bootstrap_blockers

    blockers = await list_bootstrap_blockers(status=status, family=family, limit=limit)
    return {"blockers": blockers, "count": len(blockers)}


@router.get("/integrations")
async def get_bootstrap_integrations(status: str = "", family: str = "", limit: int = 50):
    from ..bootstrap_state import list_bootstrap_integrations

    integrations = await list_bootstrap_integrations(status=status, family=family, limit=limit)
    return {"integrations": integrations, "count": len(integrations)}


@router.post("/slices/{slice_id}/claim")
async def claim_bootstrap_slice_endpoint(slice_id: str, request: Request):
    from ..bootstrap_state import claim_bootstrap_slice

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/slices/{slice_id}/claim",
        action_class="admin",
        default_reason=f"Claimed bootstrap slice {slice_id}",
    )
    if denial:
        return denial

    try:
        result = await claim_bootstrap_slice(
            slice_id,
            host_id=str(body.get("host_id") or ""),
            current_ref=str(body.get("current_ref") or ""),
            worktree_path=str(body.get("worktree_path") or ""),
            files_touched=body.get("files_touched") if isinstance(body.get("files_touched"), list) else [],
            next_step=str(body.get("next_step") or ""),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/slices/{slice_id}/claim",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=slice_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/slices/{slice_id}/claim",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Claimed bootstrap slice {slice_id}",
        target=slice_id,
        metadata={"host_id": result["host_id"]},
    )
    return {"status": "claimed", "slice": result}


@router.post("/slices/{slice_id}/handoff")
async def handoff_bootstrap_slice_endpoint(slice_id: str, request: Request):
    from ..bootstrap_state import handoff_bootstrap_slice

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/slices/{slice_id}/handoff",
        action_class="admin",
        default_reason=f"Handed off bootstrap slice {slice_id}",
    )
    if denial:
        return denial

    try:
        result = await handoff_bootstrap_slice(
            slice_id,
            from_host=str(body.get("from_host") or ""),
            to_host=str(body.get("to_host") or ""),
            current_ref=str(body.get("current_ref") or ""),
            worktree_path=str(body.get("worktree_path") or ""),
            files_touched=body.get("files_touched") if isinstance(body.get("files_touched"), list) else [],
            validation_status=str(body.get("validation_status") or "pending"),
            open_risks=body.get("open_risks") if isinstance(body.get("open_risks"), list) else [],
            next_step=str(body.get("next_step") or ""),
            stop_reason=str(body.get("stop_reason") or ""),
            resume_instructions=str(body.get("resume_instructions") or ""),
            cooldown_minutes=int(body.get("cooldown_minutes") or 30),
            blocker_class=str(body.get("blocker_class") or ""),
            approval_required=bool(body.get("approval_required", False)),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/slices/{slice_id}/handoff",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=slice_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/slices/{slice_id}/handoff",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Handed off bootstrap slice {slice_id}",
        target=slice_id,
        metadata={"from_host": result["handoff"]["from_host"], "to_host": result["handoff"]["to_host"]},
    )
    return {"status": "handed_off", **result}


@router.post("/slices/{slice_id}/complete")
async def complete_bootstrap_slice_endpoint(slice_id: str, request: Request):
    from ..bootstrap_state import complete_bootstrap_slice

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/slices/{slice_id}/complete",
        action_class="admin",
        default_reason=f"Completed bootstrap slice {slice_id}",
    )
    if denial:
        return denial

    try:
        result = await complete_bootstrap_slice(
            slice_id,
            host_id=str(body.get("host_id") or ""),
            current_ref=str(body.get("current_ref") or ""),
            worktree_path=str(body.get("worktree_path") or ""),
            files_touched=body.get("files_touched") if isinstance(body.get("files_touched"), list) else [],
            validation_status=str(body.get("validation_status") or "passed"),
            open_risks=body.get("open_risks") if isinstance(body.get("open_risks"), list) else [],
            next_step=str(body.get("next_step") or ""),
            summary=str(body.get("summary") or ""),
            integration_method=str(body.get("integration_method") or "squash_commit"),
            target_ref=str(body.get("target_ref") or "main"),
            queue_priority=int(body.get("queue_priority") or 3),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/slices/{slice_id}/complete",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=slice_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/slices/{slice_id}/complete",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Completed bootstrap slice {slice_id}",
        target=slice_id,
        metadata={"validation_status": result["slice"]["validation_status"]},
    )
    return {"status": "completed", **result}


@router.post("/integrations/{slice_id}/replay")
async def replay_bootstrap_integration_endpoint(slice_id: str, request: Request):
    from ..bootstrap_state import replay_bootstrap_integration

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/integrations/{slice_id}/replay",
        action_class="admin",
        default_reason=f"Replayed bootstrap integration for {slice_id}",
    )
    if denial:
        return denial

    try:
        integration = await replay_bootstrap_integration(
            slice_id,
            method=str(body.get("method") or "squash_commit"),
            source_ref=str(body.get("source_ref") or ""),
            target_ref=str(body.get("target_ref") or "main"),
            patch_path=str(body.get("patch_path") or ""),
            priority=int(body.get("priority") or 3),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/integrations/{slice_id}/replay",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=slice_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/integrations/{slice_id}/replay",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Queued bootstrap integration replay for {slice_id}",
        target=slice_id,
        metadata={"integration_id": integration["id"], "method": integration["method"]},
    )
    return {"status": "queued", "integration": integration}


@router.post("/programs/{program_id}/nudge")
async def nudge_bootstrap_program_endpoint(program_id: str, request: Request):
    from ..bootstrap_state import run_bootstrap_supervisor_cycle

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/programs/{program_id}/nudge",
        action_class="admin",
        default_reason=f"Nudged bootstrap supervisor for {program_id}",
    )
    if denial:
        return denial

    result = await run_bootstrap_supervisor_cycle(
        program_id=program_id,
        execute=bool(body.get("execute", False)),
        retry_blockers=bool(body.get("retry_blockers", True)),
        process_integrations=bool(body.get("process_integrations", True)),
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/programs/{program_id}/nudge",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Ran bootstrap supervisor cycle for {program_id}",
        target=program_id,
        metadata={
            "active_family": result.get("active_family", ""),
            "slice_id": (result.get("recommendation") or {}).get("slice_id", ""),
            "execute": bool(body.get("execute", False)),
        },
    )
    return {"status": "nudged", **result}


@router.post("/programs/{program_id}/approve")
async def approve_bootstrap_program_packet_endpoint(program_id: str, request: Request):
    from ..bootstrap_state import approve_bootstrap_packet

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/programs/{program_id}/approve",
        action_class="admin",
        default_reason=f"Approved bootstrap packet for {program_id}",
    )
    if denial:
        return denial

    try:
        result = await approve_bootstrap_packet(
            program_id,
            packet_id=str(body.get("packet_id") or ""),
            approved_by=str(body.get("actor") or "operator"),
            reason=str(body.get("reason") or "Approved bootstrap packet"),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/programs/{program_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=program_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/programs/{program_id}/approve",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Approved bootstrap packet {result['approved_packet_id']} for {program_id}",
        target=program_id,
        metadata={
            "packet_id": result["approved_packet_id"],
            "approved_slice_ids": result["approved_slice_ids"],
            "resolved_blocker_ids": result["resolved_blocker_ids"],
        },
    )
    return {"status": "approved", **result}


@router.post("/programs/{program_id}/promote")
async def promote_bootstrap_program_endpoint(program_id: str, request: Request):
    from ..bootstrap_state import promote_bootstrap_program

    body, action, denial = await _load_body(
        request,
        route="/v1/bootstrap/programs/{program_id}/promote",
        action_class="admin",
        default_reason=f"Promoted bootstrap program {program_id}",
    )
    if denial:
        return denial

    try:
        program = await promote_bootstrap_program(
            program_id,
            promoted_by=str(body.get("actor") or "operator"),
            reason=str(body.get("reason") or "Promoted bootstrap program"),
            force=bool(body.get("force", False)),
        )
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/bootstrap/programs/{program_id}/promote",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=program_id,
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/bootstrap/programs/{program_id}/promote",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Promoted bootstrap program {program_id}",
        target=program_id,
    )
    return {"status": "promoted", "program": program}
