"""Research job routes — CRUD, execution."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["research"])


@router.post("/research/jobs")
async def create_research_job(request: Request):
    """Create a new autonomous research job.

    Body: {"topic": "latest vLLM optimizations", "description": "...",
           "sources": ["web_search", "knowledge_base"],
           "schedule_hours": 0, "max_duration_minutes": 60}
    """
    from ..research_jobs import create_job

    body = await request.json()
    topic = body.get("topic", "")
    if not topic:
        return JSONResponse(status_code=400, content={"error": "topic is required"})

    job = await create_job(
        topic=topic,
        description=body.get("description", ""),
        sources=body.get("sources"),
        schedule_hours=body.get("schedule_hours", 0),
        max_duration_minutes=body.get("max_duration_minutes", 60),
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
async def execute_research_job(job_id: str):
    """Execute a research job immediately."""
    from ..research_jobs import execute_job

    result = await execute_job(job_id)
    if "error" in result:
        return JSONResponse(status_code=404, content=result)
    return result


@router.delete("/research/jobs/{job_id}")
async def delete_research_job(job_id: str):
    """Delete a research job."""
    from ..research_jobs import delete_job

    if await delete_job(job_id):
        return {"status": "deleted", "job_id": job_id}
    return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})
