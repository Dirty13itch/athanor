"""Task routes — CRUD, scheduling, approval."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["tasks"])


@router.post("/tasks")
async def create_task(request: Request):
    """Submit a task for background autonomous execution.

    Body: {"agent": "research-agent", "prompt": "Research vLLM updates",
           "priority": "normal", "metadata": {}}
    """
    from ..tasks import submit_task

    body = await request.json()
    agent = body.get("agent", "")
    prompt = body.get("prompt", "")
    priority = body.get("priority", "normal")
    metadata = body.get("metadata", {})

    if not agent or not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'agent' and 'prompt' are required"},
        )

    try:
        from ..governor import Governor
        gov = Governor.get()
        decision = await gov.gate_task_submission(
            agent=agent, prompt=prompt, priority=priority,
            metadata=metadata, source="manual",
        )
        task = await submit_task(
            agent=agent,
            prompt=prompt,
            priority=priority,
            metadata={**(metadata or {}), "governor_decision": decision.reason},
        )
        if decision.status_override == "pending_approval":
            task.status = "pending_approval"
            from ..tasks import _update_task
            await _update_task(task)
        return {"status": "submitted", "task": task.to_dict(), "governor": {
            "level": decision.autonomy_level,
            "reason": decision.reason,
        }}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.get("/tasks")
async def get_tasks(
    status: str = "",
    agent: str = "",
    limit: int = 50,
):
    """List tasks with optional filters."""
    from ..tasks import list_tasks

    tasks = await list_tasks(status=status, agent=agent, limit=limit)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/tasks/stats")
async def task_stats():
    """Get task execution statistics."""
    from ..tasks import get_task_stats

    return await get_task_stats()


@router.get("/tasks/schedules")
async def task_schedules():
    """Get proactive agent schedule status."""
    from ..scheduler import get_schedule_status

    return await get_schedule_status()


@router.get("/scheduler/health")
async def scheduler_health():
    """Scheduler subsystem health — running state, last-run timestamps, overdue agents."""
    from ..scheduler import get_scheduler_health

    return await get_scheduler_health()


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """Get detailed task status including execution steps."""
    from ..tasks import get_task

    task = await get_task(task_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task '{task_id}' not found"},
        )
    return {"task": task.to_dict()}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task_endpoint(task_id: str):
    """Cancel a pending or running task."""
    from ..tasks import cancel_task

    if await cancel_task(task_id):
        return {"status": "cancelled", "task_id": task_id}
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or already completed"},
    )


@router.post("/tasks/{task_id}/approve")
async def approve_task_endpoint(task_id: str):
    """Approve a pending_approval task (high-impact agents require morning approval)."""
    from ..tasks import approve_task

    if await approve_task(task_id):
        return {"approved": True, "task_id": task_id}
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or not pending approval"},
    )


@router.post("/tasks/{task_id}/reject")
async def reject_task_endpoint(task_id: str, request: Request):
    """Reject a pending_approval task with reason."""
    from ..tasks import reject_task

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    reason = body.get("reason", "Rejected by operator")

    if await reject_task(task_id, reason=reason):
        return {"rejected": True, "task_id": task_id}
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or not pending approval"},
    )


@router.post("/tasks/batch-approve")
async def batch_approve_tasks(request: Request):
    """Approve multiple pending_approval tasks at once."""
    from ..tasks import approve_task

    body = await request.json()
    task_ids = body.get("task_ids", [])

    results = []
    for tid in task_ids:
        approved = await approve_task(tid)
        results.append({"task_id": tid, "approved": approved})

    approved_count = sum(1 for r in results if r["approved"])
    return {"results": results, "approved": approved_count, "total": len(results)}


@router.post("/tasks/{task_id}/review")
async def review_task_endpoint(task_id: str):
    """Score a completed task's output quality via grader model."""
    from ..supervisor import review_task_output

    result = await review_task_output(task_id)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result
