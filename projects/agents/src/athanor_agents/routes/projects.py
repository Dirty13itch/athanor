"""Project milestone and tracking API routes."""

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
