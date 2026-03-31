"""Research job routes - CRUD, execution."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["research"])


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


@router.post("/research/jobs")
async def create_research_job(request: Request):
    """Create a new autonomous research job."""
    from ..research_jobs import create_job

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/research/jobs",
        action_class="operator",
        default_reason="Manual research job creation",
    )
    if denial:
        return denial

    topic = body.get("topic", "")
    if not topic:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/research/jobs",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="topic is required",
        )
        return JSONResponse(status_code=400, content={"error": "topic is required"})

    job = await create_job(
        topic=topic,
        description=body.get("description", ""),
        sources=body.get("sources"),
        schedule_hours=body.get("schedule_hours", 0),
        max_duration_minutes=body.get("max_duration_minutes", 60),
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/research/jobs",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created research job {job.id}",
        target=job.id,
        metadata={
            "topic": topic,
            "schedule_hours": body.get("schedule_hours", 0),
            "max_duration_minutes": body.get("max_duration_minutes", 60),
        },
    )
    return job.to_dict()


@router.get("/research/jobs")
async def list_research_jobs(status: str = ""):
    """List all research jobs, optionally filtered by status."""
    from ..research_jobs import list_jobs

    return await list_jobs(status=status)


@router.get("/research/jobs/{job_id}")
async def get_research_job(job_id: str):
    """Get a specific research job by ID."""
    from ..research_jobs import get_job

    job = await get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})
    return job.to_dict()


@router.post("/research/jobs/{job_id}/execute")
async def execute_research_job(job_id: str, request: Request):
    """Execute a research job immediately."""
    from ..research_jobs import execute_job

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/research/jobs/{job_id}/execute",
        action_class="admin",
        default_reason=f"Executed research job {job_id}",
    )
    if denial:
        return denial

    result = await execute_job(job_id)
    if "error" in result:
        status_code = 404 if "not found" in str(result["error"]).lower() else 400
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/research/jobs/{job_id}/execute",
            action_class="admin",
            decision="denied",
            status_code=status_code,
            action=action,
            detail=str(result["error"]),
            target=job_id,
        )
        return JSONResponse(status_code=status_code, content=result)

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/research/jobs/{job_id}/execute",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Executed research job {job_id}",
        target=job_id,
        metadata={"task_id": result.get("task_id", "")},
    )
    return result


@router.delete("/research/jobs/{job_id}")
async def delete_research_job(job_id: str, request: Request):
    """Delete a research job."""
    from ..research_jobs import delete_job

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/research/jobs/{job_id}",
        action_class="admin",
        default_reason=f"Deleted research job {job_id}",
    )
    if denial:
        return denial

    if await delete_job(job_id):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/research/jobs/{job_id}",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Deleted research job {job_id}",
            target=job_id,
        )
        return {"status": "deleted", "job_id": job_id}

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/research/jobs/{job_id}",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Job {job_id} not found",
        target=job_id,
    )
    return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})
