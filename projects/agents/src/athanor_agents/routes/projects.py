"""Project milestone and tracking API routes."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["projects"])


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

    body = await request.json()
    title = body.get("title", "")
    description = body.get("description", "")
    criteria = body.get("acceptance_criteria", [])
    agents = body.get("assigned_agents", [])

    if not title:
        return JSONResponse(status_code=400, content={"error": "Title required"})

    milestone = await create_milestone(
        project_id=project_id,
        title=title,
        description=description,
        acceptance_criteria=criteria,
        assigned_agents=agents,
    )
    return {"milestone": milestone.to_dict()}


@router.put("/projects/{project_id}/milestones/{milestone_id}")
async def update_milestone_endpoint(project_id: str, milestone_id: str, request: Request):
    """Update a milestone."""
    from ..project_tracker import update_milestone

    body = await request.json()
    milestone = await update_milestone(project_id, milestone_id, **body)
    if not milestone:
        return JSONResponse(status_code=404,
                            content={"error": f"Milestone '{milestone_id}' not found"})
    return {"milestone": milestone.to_dict()}


@router.post("/projects/{project_id}/advance")
async def advance_project_endpoint(project_id: str):
    """Trigger project advancement check."""
    from ..project_tracker import advance_project

    result = await advance_project(project_id)
    return result


@router.post("/projects/{project_id}/supervise")
async def supervise_project_endpoint(project_id: str, request: Request):
    """Decompose a project into milestones and assign cloud managers."""
    from ..supervisor import supervise_project

    body = await request.json()
    instruction = body.get("instruction", "")
    milestones = body.get("milestones")

    if not instruction:
        return JSONResponse(status_code=400, content={"error": "Instruction required"})

    result = await supervise_project(project_id, instruction, milestones)
    return result


@router.get("/projects/{project_id}/state")
async def project_state(project_id: str):
    """Get full project state including milestones and metrics."""
    from ..project_tracker import get_project_state

    state = await get_project_state(project_id)
    return {"state": state.to_dict()}
