"""Project milestone and tracking API routes."""

import uuid

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["projects"])


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


@router.get("/projects/{project_id}/milestones")
async def list_milestones(project_id: str):
    """List milestones for a project."""
    from ..project_tracker import get_milestones

    milestones = await get_milestones(project_id)
    return {"milestones": [m.to_dict() for m in milestones], "count": len(milestones)}


@router.post("/projects/{project_id}/milestones")
async def create_milestone_endpoint(project_id: str, request: Request):
    """Create a milestone for a project."""
    from ..project_tracker import create_milestone

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/milestones",
        action_class="operator",
        default_reason=f"Created milestone for project {project_id}",
    )
    if denial:
        return denial

    title = body.get("title", "")
    description = body.get("description", "")
    criteria = body.get("acceptance_criteria", [])
    agents = body.get("assigned_agents", [])

    if not title:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/milestones",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="Title required",
            metadata={"project_id": project_id},
        )
        return JSONResponse(status_code=400, content={"error": "Title required"})

    milestone = await create_milestone(
        project_id=project_id,
        title=title,
        description=description,
        acceptance_criteria=criteria,
        assigned_agents=agents,
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/milestones",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created milestone {milestone.id} for project {project_id}",
        target=milestone.id,
        metadata={"project_id": project_id, "title": title},
    )
    return {"milestone": milestone.to_dict()}


@router.put("/projects/{project_id}/milestones/{milestone_id}")
async def update_milestone_endpoint(project_id: str, milestone_id: str, request: Request):
    """Update a milestone."""
    from ..project_tracker import update_milestone

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/milestones/{milestone_id}",
        action_class="admin",
        default_reason=f"Updated milestone {milestone_id} for project {project_id}",
    )
    if denial:
        return denial

    milestone = await update_milestone(project_id, milestone_id, **body)
    if not milestone:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/milestones/{milestone_id}",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Milestone {milestone_id} not found",
            target=milestone_id,
            metadata={"project_id": project_id},
        )
        return JSONResponse(
            status_code=404,
            content={"error": f"Milestone '{milestone_id}' not found"},
        )

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/milestones/{milestone_id}",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Updated milestone {milestone_id} for project {project_id}",
        target=milestone_id,
        metadata={"project_id": project_id},
    )
    return {"milestone": milestone.to_dict()}


@router.post("/projects/{project_id}/advance")
async def advance_project_endpoint(project_id: str, request: Request):
    """Trigger project advancement check."""
    from ..project_tracker import advance_project

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/advance",
        action_class="admin",
        default_reason=f"Advanced project {project_id}",
    )
    if denial:
        return denial

    result = await advance_project(project_id)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/advance",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Triggered project advancement for {project_id}",
        target=project_id,
        metadata={
            "status": str(result.get("status", "")),
            "advanced": bool(result.get("advanced", False)),
        },
    )
    return result


@router.post("/projects/{project_id}/supervise")
async def supervise_project_endpoint(project_id: str, request: Request):
    """Decompose a project into milestones and assign cloud managers."""
    from ..supervisor import supervise_project

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/supervise",
        action_class="admin",
        default_reason=f"Supervised project {project_id}",
    )
    if denial:
        return denial

    instruction = body.get("instruction", "")
    milestones = body.get("milestones")

    if not instruction:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/supervise",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="Instruction required",
            target=project_id,
        )
        return JSONResponse(status_code=400, content={"error": "Instruction required"})

    result = await supervise_project(project_id, instruction, milestones)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/supervise",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Supervised project {project_id}",
        target=project_id,
        metadata={"milestones_created": int(result.get("milestones_created", 0))},
    )
    return result


@router.get("/projects/{project_id}/state")
async def project_state(project_id: str):
    """Get full project state including milestones and metrics."""
    from ..project_tracker import get_project_state

    state = await get_project_state(project_id)
    return {"state": state.to_dict()}


@router.get("/projects/{project_id}/packet")
async def get_project_packet_endpoint(project_id: str):
    """Get the governed foundry project packet for a project."""
    from ..foundry_state import fetch_project_packet_record

    packet = await fetch_project_packet_record(project_id)
    if not packet:
        return JSONResponse(
            status_code=404,
            content={"error": f"Project packet '{project_id}' not found"},
        )
    return {"packet": packet}


@router.post("/projects/{project_id}/packet")
async def upsert_project_packet_endpoint(project_id: str, request: Request):
    """Create or update a governed project packet."""
    from ..foundry_state import fetch_project_packet_record, upsert_project_packet_record

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/packet",
        action_class="admin",
        default_reason=f"Updated packet for project {project_id}",
    )
    if denial:
        return denial

    existing = await fetch_project_packet_record(project_id)
    packet = {
        **(existing or {"id": project_id}),
        **body,
        "id": project_id,
    }
    await upsert_project_packet_record(packet)
    saved = await fetch_project_packet_record(project_id)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/packet",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Updated project packet for {project_id}",
        target=project_id,
        metadata={"stage": str(saved.get("stage") if saved else packet.get("stage") or "")},
    )
    return {"status": "updated", "packet": saved or packet}


@router.get("/projects/{project_id}/architecture")
async def get_architecture_packet_endpoint(project_id: str):
    """Get the governed architecture packet for a project."""
    from ..foundry_state import fetch_architecture_packet_record

    packet = await fetch_architecture_packet_record(project_id)
    if not packet:
        return JSONResponse(
            status_code=404,
            content={"error": f"Architecture packet '{project_id}' not found"},
        )
    return {"architecture": packet}


@router.post("/projects/{project_id}/architecture")
async def upsert_architecture_packet_endpoint(project_id: str, request: Request):
    """Create or update a governed architecture packet."""
    from ..foundry_state import fetch_architecture_packet_record, fetch_project_packet_record, upsert_architecture_packet_record

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/architecture",
        action_class="admin",
        default_reason=f"Updated architecture packet for project {project_id}",
    )
    if denial:
        return denial

    project_packet = await fetch_project_packet_record(project_id)
    if not project_packet:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/architecture",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Project packet {project_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Project packet '{project_id}' not found"})

    existing = await fetch_architecture_packet_record(project_id)
    record = {
        **(existing or {"project_id": project_id}),
        **body,
        "project_id": project_id,
    }
    await upsert_architecture_packet_record(record)
    saved = await fetch_architecture_packet_record(project_id)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/architecture",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Updated architecture packet for {project_id}",
        target=project_id,
    )
    return {"status": "updated", "architecture": saved or record}


@router.post("/projects/{project_id}/proving")
async def materialize_project_proving_stage_endpoint(project_id: str, request: Request):
    """Materialize the governed proving flow for the configured Athanor proving project."""
    from ..foundry_state import materialize_foundry_proving_stage

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/proving",
        action_class="admin",
        default_reason=f"Materialized proving stage for project {project_id}",
    )
    if denial:
        return denial

    stage = str(body.get("stage") or "slice_execution").strip() or "slice_execution"
    try:
        proving = await materialize_foundry_proving_stage(project_id, stage=stage)
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/proving",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
            target=project_id,
            metadata={"stage": stage},
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/proving",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Materialized proving stage {stage} for {project_id}",
        target=project_id,
        metadata={"stage": stage, "storage_mode": str((proving.get("storage") or {}).get("storage_mode") or "")},
    )
    return {"status": "recorded", "proving": proving}


@router.get("/projects/{project_id}/foundry/runs")
async def list_foundry_runs_endpoint(project_id: str, limit: int = 50):
    """List foundry runs for a project."""
    from ..foundry_state import list_foundry_run_records

    runs = await list_foundry_run_records(project_id, limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/projects/{project_id}/slices")
async def list_execution_slices_endpoint(project_id: str, limit: int = 50):
    """List execution slices for a project."""
    from ..foundry_state import list_execution_slice_records

    slices = await list_execution_slice_records(project_id, limit=limit)
    return {"slices": slices, "count": len(slices)}


@router.post("/projects/{project_id}/slices")
async def create_execution_slice_endpoint(project_id: str, request: Request):
    """Create or update an execution slice for a project."""
    from ..foundry_state import (
        fetch_project_packet_record,
        list_execution_slice_records,
        upsert_execution_slice_record,
    )

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/slices",
        action_class="operator",
        default_reason=f"Recorded execution slice for project {project_id}",
    )
    if denial:
        return denial

    project_packet = await fetch_project_packet_record(project_id)
    if not project_packet:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/slices",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Project packet {project_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Project packet '{project_id}' not found"})

    record = {
        "id": body.get("id"),
        "project_id": project_id,
        "owner_agent": str(body.get("owner_agent") or ""),
        "lane": str(body.get("lane") or ""),
        "base_sha": str(body.get("base_sha") or ""),
        "worktree_path": str(body.get("worktree_path") or ""),
        "acceptance_target": str(body.get("acceptance_target") or ""),
        "status": str(body.get("status") or "planned"),
        "metadata": dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
        "created_at": body.get("created_at"),
        "updated_at": body.get("updated_at"),
    }
    await upsert_execution_slice_record(record)
    saved = await list_execution_slice_records(project_id, limit=1)
    latest = saved[0] if saved else record
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/slices",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded execution slice for {project_id}",
        target=str(latest.get("id") or ""),
        metadata={"project_id": project_id, "status": str(latest.get("status") or "")},
    )
    return {"status": "created", "slice": latest}


@router.post("/projects/{project_id}/foundry/runs")
async def create_foundry_run_endpoint(project_id: str, request: Request):
    """Create or update a foundry run record for a project."""
    from ..foundry_state import list_foundry_run_records, upsert_foundry_run_record

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/foundry/runs",
        action_class="operator",
        default_reason=f"Recorded foundry run for project {project_id}",
    )
    if denial:
        return denial

    record = {
        "id": body.get("id"),
        "project_id": project_id,
        "slice_id": str(body.get("slice_id") or ""),
        "execution_run_id": str(body.get("execution_run_id") or ""),
        "status": str(body.get("status") or "queued"),
        "summary": str(body.get("summary") or ""),
        "artifact_refs": body.get("artifact_refs") if isinstance(body.get("artifact_refs"), list) else [],
        "review_refs": body.get("review_refs") if isinstance(body.get("review_refs"), list) else [],
        "metadata": dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
        "created_at": body.get("created_at"),
        "updated_at": body.get("updated_at"),
        "completed_at": body.get("completed_at"),
    }
    await upsert_foundry_run_record(record)
    saved = await list_foundry_run_records(project_id, limit=1)
    latest = saved[0] if saved else record
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/foundry/runs",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded foundry run for {project_id}",
        target=str(latest.get("id") or ""),
        metadata={"project_id": project_id, "status": str(latest.get("status") or "")},
    )
    return {"status": "created", "run": latest}


@router.get("/projects/{project_id}/maintenance")
async def list_maintenance_runs_endpoint(project_id: str, limit: int = 50):
    """List maintenance runs for a project."""
    from ..foundry_state import list_maintenance_run_records

    runs = await list_maintenance_run_records(project_id, limit=limit)
    return {"maintenance_runs": runs, "count": len(runs)}


@router.post("/projects/{project_id}/maintenance")
async def create_maintenance_run_endpoint(project_id: str, request: Request):
    """Create or update a maintenance run for a project."""
    from ..foundry_state import (
        fetch_project_packet_record,
        list_maintenance_run_records,
        upsert_maintenance_run_record,
    )

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/maintenance",
        action_class="operator",
        default_reason=f"Recorded maintenance run for project {project_id}",
    )
    if denial:
        return denial

    project_packet = await fetch_project_packet_record(project_id)
    if not project_packet:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/maintenance",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Project packet {project_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Project packet '{project_id}' not found"})

    record = {
        "id": body.get("id"),
        "project_id": project_id,
        "kind": str(body.get("kind") or ""),
        "trigger": str(body.get("trigger") or ""),
        "status": str(body.get("status") or "queued"),
        "evidence_ref": str(body.get("evidence_ref") or ""),
        "metadata": dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
        "created_at": body.get("created_at"),
        "updated_at": body.get("updated_at"),
        "completed_at": body.get("completed_at"),
    }
    await upsert_maintenance_run_record(record)
    saved = await list_maintenance_run_records(project_id, limit=1)
    latest = saved[0] if saved else record
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/maintenance",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded maintenance run for {project_id}",
        target=str(latest.get("id") or ""),
        metadata={"project_id": project_id, "status": str(latest.get("status") or "")},
    )
    return {"status": "created", "maintenance_run": latest}


@router.get("/projects/{project_id}/deployments")
async def list_deploy_candidates_endpoint(project_id: str, limit: int = 50):
    """List governed deploy candidates for a project."""
    from ..foundry_state import list_deploy_candidate_records

    candidates = await list_deploy_candidate_records(project_id, limit=limit)
    return {"deployments": candidates, "count": len(candidates)}


@router.get("/projects/{project_id}/rollbacks")
async def list_rollback_events_endpoint(project_id: str, limit: int = 20):
    """List rollback events recorded for a project."""
    from ..foundry_state import list_rollback_event_records

    events = await list_rollback_event_records(project_id, limit=limit)
    return {"rollbacks": events, "count": len(events)}


@router.post("/projects/{project_id}/deployments")
async def create_deploy_candidate_endpoint(project_id: str, request: Request):
    """Create or update a governed deploy candidate."""
    from ..foundry_state import fetch_project_packet_record, list_deploy_candidate_records, upsert_deploy_candidate_record

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/deployments",
        action_class="admin",
        default_reason=f"Recorded deploy candidate for project {project_id}",
    )
    if denial:
        return denial

    project_packet = await fetch_project_packet_record(project_id)
    if not project_packet:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/deployments",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Project packet {project_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Project packet '{project_id}' not found"})

    record = {
        "id": body.get("id"),
        "project_id": project_id,
        "channel": str(body.get("channel") or "internal_preview"),
        "artifact_refs": body.get("artifact_refs") if isinstance(body.get("artifact_refs"), list) else [],
        "env_contract": dict(body.get("env_contract") or {}) if isinstance(body.get("env_contract"), dict) or body.get("env_contract") is None else {},
        "smoke_results": dict(body.get("smoke_results") or {}) if isinstance(body.get("smoke_results"), dict) or body.get("smoke_results") is None else {},
        "rollback_target": dict(body.get("rollback_target") or {}) if isinstance(body.get("rollback_target"), dict) or body.get("rollback_target") is None else {},
        "promotion_status": str(body.get("promotion_status") or "pending"),
        "metadata": dict(body.get("metadata") or {}) if isinstance(body.get("metadata"), dict) or body.get("metadata") is None else {},
        "created_at": body.get("created_at"),
        "updated_at": body.get("updated_at"),
        "promoted_at": body.get("promoted_at"),
    }
    await upsert_deploy_candidate_record(record)
    saved = await list_deploy_candidate_records(project_id, limit=1)
    latest = saved[0] if saved else record
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/deployments",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded deploy candidate for {project_id}",
        target=str(latest.get("id") or ""),
        metadata={"channel": str(latest.get("channel") or ""), "project_id": project_id},
    )
    return {"status": "created", "deployment": latest}


@router.post("/projects/{project_id}/promote")
async def promote_project_candidate_endpoint(project_id: str, request: Request):
    """Promote a deploy candidate after packet, smoke, and rollback checks."""
    from ..foundry_state import (
        fetch_deploy_candidate_record,
        record_rollback_event,
        upsert_deploy_candidate_record,
    )

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/promote",
        action_class="admin",
        default_reason=f"Promoted deploy candidate for project {project_id}",
    )
    if denial:
        return denial

    candidate_id = str(body.get("candidate_id") or "").strip()
    channel = str(body.get("channel") or "").strip()
    reason = str(body.get("reason") or "").strip()
    if not candidate_id or not channel:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/promote",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="candidate_id and channel are required",
            target=project_id,
        )
        return JSONResponse(status_code=400, content={"error": "candidate_id and channel are required"})

    candidate = await fetch_deploy_candidate_record(project_id, candidate_id)
    if not candidate:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/promote",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Deploy candidate {candidate_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Deploy candidate '{candidate_id}' not found"})

    rollback_target = dict(candidate.get("rollback_target") or {})
    if not rollback_target:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/promote",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=f"Deploy candidate {candidate_id} is missing rollback_target",
            target=candidate_id,
        )
        return JSONResponse(status_code=400, content={"error": "Deploy candidate must record rollback_target before promotion"})

    candidate["channel"] = channel
    candidate["promotion_status"] = "promoted"
    candidate["metadata"] = {
        **dict(candidate.get("metadata") or {}),
        "promotion_reason": reason,
    }
    from time import time as _time

    candidate["promoted_at"] = _time()
    candidate["updated_at"] = candidate["promoted_at"]
    await upsert_deploy_candidate_record(candidate)
    await record_rollback_event(
        {
            "project_id": project_id,
            "candidate_id": candidate_id,
            "reason": reason or f"Promotion rollback anchor for {channel}",
            "rollback_target": rollback_target,
            "status": "recorded",
            "metadata": {"channel": channel},
        }
    )

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/promote",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Promoted deploy candidate {candidate_id} for {project_id}",
        target=candidate_id,
        metadata={"channel": channel},
    )
    return {"status": "promoted", "candidate": candidate}


@router.post("/projects/{project_id}/rollback")
async def rollback_project_candidate_endpoint(project_id: str, request: Request):
    """Record and execute a governed rollback for a promoted candidate."""
    from time import time as _time

    from ..foundry_state import (
        fetch_deploy_candidate_record,
        record_rollback_event,
        upsert_deploy_candidate_record,
    )

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/projects/{project_id}/rollback",
        action_class="destructive-admin",
        default_reason=f"Rolled back deploy candidate for project {project_id}",
    )
    if denial:
        return denial

    candidate_id = str(body.get("candidate_id") or "").strip()
    if not candidate_id:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/rollback",
            action_class="destructive-admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="candidate_id is required",
            target=project_id,
        )
        return JSONResponse(status_code=400, content={"error": "candidate_id is required"})

    candidate = await fetch_deploy_candidate_record(project_id, candidate_id)
    if not candidate:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/rollback",
            action_class="destructive-admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Deploy candidate {candidate_id} not found",
            target=project_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Deploy candidate '{candidate_id}' not found"})

    rollback_target = dict(candidate.get("rollback_target") or {})
    if not rollback_target:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/projects/{project_id}/rollback",
            action_class="destructive-admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=f"Deploy candidate {candidate_id} is missing rollback_target",
            target=candidate_id,
        )
        return JSONResponse(status_code=400, content={"error": "Deploy candidate must record rollback_target before rollback"})

    rollback_event_id = f"rollback-{uuid.uuid4().hex[:8]}"
    rollback_reason = str(body.get("reason") or "").strip() or f"Rollback executed for {candidate_id}"
    rollback_event = {
        "id": rollback_event_id,
        "project_id": project_id,
        "candidate_id": candidate_id,
        "reason": rollback_reason,
        "rollback_target": rollback_target,
        "status": "executed",
        "metadata": {
            "channel": str(candidate.get("channel") or ""),
            "previous_status": str(candidate.get("promotion_status") or ""),
        },
        "created_at": _time(),
    }
    await record_rollback_event(rollback_event)

    candidate["promotion_status"] = "rolled_back"
    candidate["metadata"] = {
        **dict(candidate.get("metadata") or {}),
        "rollback_reason": rollback_reason,
        "rollback_event_id": rollback_event_id,
    }
    candidate["updated_at"] = rollback_event["created_at"]
    await upsert_deploy_candidate_record(candidate)

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/projects/{project_id}/rollback",
        action_class="destructive-admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Rolled back deploy candidate {candidate_id} for {project_id}",
        target=candidate_id,
        metadata={"channel": str(candidate.get("channel") or "")},
    )
    return {
        "status": "rolled_back",
        "candidate": candidate,
        "rollback_event": rollback_event,
    }
