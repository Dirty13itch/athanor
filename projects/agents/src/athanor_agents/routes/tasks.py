"""Task routes — CRUD, scheduling, approval."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["tasks"])


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


@router.post("/tasks")
async def create_task(request: Request):
    """Submit a task for background autonomous execution.

    Body: {"agent": "research-agent", "prompt": "Research vLLM updates",
           "priority": "normal", "metadata": {}}
    """
    body, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks",
        action_class="operator",
        default_reason="Manual task submission",
    )
    if denial:
        return denial
    agent = body.get("agent", "")
    prompt = body.get("prompt", "")
    priority = body.get("priority", "normal")
    metadata = body.get("metadata", {})

    if not agent or not prompt:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="Both 'agent' and 'prompt' are required",
            metadata={"agent": str(agent or ""), "priority": str(priority or "normal")},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'agent' and 'prompt' are required"},
        )

    try:
        from ..tasks import submit_governed_task

        submission = await submit_governed_task(
            agent=agent,
            prompt=prompt,
            priority=priority,
            metadata=metadata,
            source="manual",
        )
        task = submission.task
        decision = submission.decision
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks",
            action_class="operator",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Submitted task {task.id} for agent={agent}",
            target=task.id,
            metadata={"agent": agent, "priority": priority},
        )
        return {"status": "submitted", "task": task.to_dict(), "governor": {
            "level": decision.autonomy_level,
            "reason": decision.reason,
        }}
    except ValueError as e:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(e),
            metadata={"agent": str(agent or ""), "priority": str(priority or "normal")},
        )
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


@router.get("/tasks/scheduled")
async def scheduled_jobs(limit: int = 50):
    """Get scheduled job posture records for operator surfaces."""
    from ..backbone import build_scheduled_job_records

    jobs = await build_scheduled_job_records(limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/tasks/dispatch")
async def dispatch_next_task(request: Request):
    """Dispatch the next pending task immediately through the canonical task engine."""
    from ..tasks import dispatch_next_pending_task

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/dispatch",
        action_class="operator",
        default_reason="Manual task dispatch",
    )
    if denial:
        return denial

    result = await dispatch_next_pending_task(trigger="dashboard")
    detail = {
        "dispatched": "Dispatched the next pending task",
        "deferred": "Deferred next pending task",
        "busy": "Task engine already at max concurrency",
        "empty": "No pending tasks available for dispatch",
    }.get(result.get("status"), "Processed manual task dispatch request")

    target = None
    if isinstance(result.get("task"), dict):
        target = result["task"].get("id")

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/dispatch",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=detail,
        target=target,
        metadata={
            "result_status": result.get("status"),
            "currently_running": result.get("currently_running"),
            "max_concurrent": result.get("max_concurrent"),
        },
    )
    return result


@router.post("/tasks/scheduled/{job_id}/run")
async def run_scheduled_job_endpoint(job_id: str, request: Request):
    """Trigger a governed scheduled job run."""
    from ..scheduler import run_scheduled_job

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/scheduled/{job_id}/run",
        action_class="admin",
        default_reason=f"Triggered scheduled job {job_id}",
    )
    if denial:
        return denial

    force = bool(body.get("force", False))
    actor = str(body.get("actor") or action.actor or "operator")

    try:
        result = await run_scheduled_job(job_id, actor=actor, force=force)
    except KeyError:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks/scheduled/{job_id}/run",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Scheduled job '{job_id}' not found",
            target=job_id,
            metadata={"force": force},
        )
        return JSONResponse(
            status_code=404,
            content={"error": f"Scheduled job '{job_id}' not found"},
        )

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/scheduled/{job_id}/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Triggered scheduled job {job_id}",
        target=job_id,
        metadata={
            "force": force,
            "result_status": result.get("status"),
            "override_available": result.get("override_available"),
        },
    )
    return result


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
async def cancel_task_endpoint(task_id: str, request: Request):
    """Cancel a pending or running task."""
    from ..tasks import cancel_task

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/{task_id}/cancel",
        action_class="admin",
        default_reason=f"Cancelled task {task_id}",
    )
    if denial:
        return denial

    if await cancel_task(task_id):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks/{task_id}/cancel",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Cancelled task {task_id}",
            target=task_id,
        )
        return {"status": "cancelled", "task_id": task_id}
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/{task_id}/cancel",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Task {task_id} not found or already completed",
        target=task_id,
    )
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or already completed"},
    )


@router.post("/tasks/{task_id}/approve")
async def approve_task_endpoint(task_id: str, request: Request):
    """Approve a pending_approval task (high-impact agents require morning approval)."""
    from ..tasks import approve_task

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/{task_id}/approve",
        action_class="admin",
        default_reason=f"Approved task {task_id}",
    )
    if denial:
        return denial

    if await approve_task(task_id):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks/{task_id}/approve",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Approved task {task_id}",
            target=task_id,
        )
        return {"approved": True, "task_id": task_id}
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/{task_id}/approve",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Task {task_id} not found or not pending approval",
        target=task_id,
    )
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or not pending approval"},
    )


@router.post("/tasks/{task_id}/reject")
async def reject_task_endpoint(task_id: str, request: Request):
    """Reject a pending_approval task with reason."""
    from ..tasks import reject_task

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/{task_id}/reject",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    reason = action.reason

    if await reject_task(task_id, reason=reason):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks/{task_id}/reject",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Rejected task {task_id}",
            target=task_id,
        )
        return {"rejected": True, "task_id": task_id}
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/{task_id}/reject",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Task {task_id} not found or not pending approval",
        target=task_id,
    )
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or not pending approval"},
    )


@router.post("/tasks/batch-approve")
async def batch_approve_tasks(request: Request):
    """Approve multiple pending_approval tasks at once."""
    from ..tasks import approve_task

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/batch-approve",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    task_ids = body.get("task_ids", [])

    results = []
    for tid in task_ids:
        approved = await approve_task(tid)
        results.append({"task_id": tid, "approved": approved})

    approved_count = sum(1 for r in results if r["approved"])
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/batch-approve",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Batch approved {approved_count}/{len(results)} tasks",
        metadata={"task_ids": task_ids},
    )
    return {"results": results, "approved": approved_count, "total": len(results)}


@router.post("/tasks/{task_id}/review")
async def review_task_endpoint(task_id: str, request: Request):
    """Score a completed task's output quality via grader model."""
    from ..supervisor import review_task_output

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/tasks/{task_id}/review",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    result = await review_task_output(task_id)
    if "error" in result:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/tasks/{task_id}/review",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(result.get("error", "Task review failed")),
            target=task_id,
        )
        return JSONResponse(status_code=400, content=result)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/tasks/{task_id}/review",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Reviewed task {task_id}",
        target=task_id,
        metadata={"quality_score": result.get("quality_score"), "agent": result.get("agent")},
    )
    return result
