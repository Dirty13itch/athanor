"""Governor API routes — matches dashboard proxy expectations."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["governor"])


@router.get("/governor")
async def governor_snapshot():
    """Full governor snapshot matching governorSnapshotSchema."""
    from ..governor import Governor

    gov = Governor.get()
    return await gov.snapshot()


@router.post("/governor/pause")
async def governor_pause(request: Request):
    """Pause governor globally or a specific lane."""
    from ..governor import Governor

    body = await request.json()
    scope = body.get("scope", "global")
    actor = body.get("actor", "operator")
    reason = body.get("reason", "")

    gov = Governor.get()
    await gov.pause(scope=scope, actor=actor, reason=reason)
    return {"status": "paused", "scope": scope}


@router.post("/governor/resume")
async def governor_resume(request: Request):
    """Resume governor globally or a specific lane."""
    from ..governor import Governor

    body = await request.json()
    scope = body.get("scope", "global")
    actor = body.get("actor", "operator")
    reason = body.get("reason", "")

    gov = Governor.get()
    await gov.resume(scope=scope, actor=actor, reason=reason)
    return {"status": "resumed", "scope": scope}


@router.post("/governor/heartbeat")
async def governor_heartbeat(request: Request):
    """Record a heartbeat from the dashboard."""
    from ..governor import Governor

    body = await request.json()
    source = body.get("source", "dashboard")

    gov = Governor.get()
    await gov.record_heartbeat(source=source)
    return {"status": "ok", "source": source}


@router.post("/governor/presence")
async def governor_presence(request: Request):
    """Set presence mode and state."""
    from ..governor import Governor

    body = await request.json()
    mode = body.get("mode", "auto")
    state = body.get("state", "at_desk")
    reason = body.get("reason", "")
    actor = body.get("actor", "operator")

    gov = Governor.get()
    await gov.set_presence(mode=mode, state=state, reason=reason, actor=actor)
    return {"status": "ok", "mode": mode, "state": state}


@router.post("/governor/release-tier")
async def governor_release_tier(request: Request):
    """Set the release tier for cloud provider access."""
    from ..governor import Governor

    body = await request.json()
    tier = body.get("tier", "standard")
    reason = body.get("reason", "")
    actor = body.get("actor", "operator")

    gov = Governor.get()
    await gov.set_release_tier(tier=tier, reason=reason, actor=actor)
    return {"status": "ok", "tier": tier}


@router.get("/governor/operations")
async def governor_operations():
    """Operations readiness check."""
    from ..governor import Governor

    gov = Governor.get()
    snapshot = await gov.snapshot()
    capacity = snapshot.get("capacity", {})

    return {
        "status": "operational",
        "capacity_posture": capacity.get("posture", "unknown"),
        "queue": capacity.get("queue", {}),
        "scheduler": capacity.get("scheduler", {}),
        "nodes": capacity.get("nodes", []),
    }


@router.get("/governor/operator-tests")
async def governor_operator_tests():
    """List available operator tests."""
    return {
        "tests": [
            {"id": "redis_ping", "label": "Redis connectivity", "status": "available"},
            {"id": "qdrant_ping", "label": "Qdrant connectivity", "status": "available"},
            {"id": "litellm_ping", "label": "LiteLLM health", "status": "available"},
            {"id": "agent_health", "label": "Agent server health", "status": "available"},
        ]
    }


@router.post("/governor/operator-tests/run")
async def governor_run_operator_tests(request: Request):
    """Run operator tests."""
    import httpx
    from ..config import settings

    results = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Redis
        try:
            from ..workspace import get_redis
            r = await get_redis()
            await r.ping()
            results.append({"id": "redis_ping", "passed": True})
        except Exception as e:
            results.append({"id": "redis_ping", "passed": False, "error": str(e)[:100]})

        # Qdrant
        try:
            resp = await client.get(f"{settings.qdrant_url}/collections")
            results.append({"id": "qdrant_ping", "passed": resp.status_code == 200})
        except Exception as e:
            results.append({"id": "qdrant_ping", "passed": False, "error": str(e)[:100]})

        # LiteLLM
        try:
            resp = await client.get(f"{settings.litellm_url}/health")
            results.append({"id": "litellm_ping", "passed": resp.status_code == 200})
        except Exception as e:
            results.append({"id": "litellm_ping", "passed": False, "error": str(e)[:100]})

        # Agent health (self)
        results.append({"id": "agent_health", "passed": True})

    passed = sum(1 for r in results if r["passed"])
    return {
        "results": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }


@router.get("/governor/tool-permissions")
async def governor_tool_permissions():
    """Get tool permission matrix for agents."""
    from ..server import AGENT_METADATA

    permissions = {}
    for agent_name, meta in AGENT_METADATA.items():
        permissions[agent_name] = {
            "tools": meta["tools"],
            "type": meta["type"],
        }
    return {"permissions": permissions}


# --- Task approval extensions ---

@router.post("/tasks/{task_id}/reject")
async def reject_task_endpoint(task_id: str, request: Request):
    """Reject a pending_approval task."""
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
    """Approve multiple tasks at once."""
    from ..tasks import approve_task

    body = await request.json()
    task_ids = body.get("task_ids", [])

    results = []
    for tid in task_ids:
        ok = await approve_task(tid)
        results.append({"task_id": tid, "approved": ok})

    approved = sum(1 for r in results if r["approved"])
    return {"results": results, "approved": approved, "total": len(results)}
