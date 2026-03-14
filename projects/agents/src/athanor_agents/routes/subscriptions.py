"""Subscription control layer — providers, policies, leases, quotas."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["subscriptions"])


@router.get("/subscriptions/providers")
async def subscription_providers():
    from ..subscriptions import get_policy_snapshot

    policy = get_policy_snapshot()
    return {
        "providers": policy["providers"],
        "count": len(policy["providers"]),
        "policy_source": policy["policy_source"],
    }


@router.get("/subscriptions/policy")
async def subscription_policy():
    from ..subscriptions import get_policy_snapshot

    return get_policy_snapshot()


@router.get("/subscriptions/leases")
async def subscription_leases(requester: str = "", limit: int = 50):
    from ..subscriptions import list_execution_leases

    leases = await list_execution_leases(requester=requester, limit=limit)
    return {"leases": leases, "count": len(leases)}


@router.post("/subscriptions/leases")
async def create_subscription_lease(request: Request):
    from ..subscriptions import LeaseRequest, issue_execution_lease

    body = await request.json()
    requester = body.get("requester", "")
    task_class = body.get("task_class", "")
    if not requester or not task_class:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'requester' and 'task_class' are required"},
        )

    lease = await issue_execution_lease(
        LeaseRequest(
            requester=requester,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            priority=body.get("priority", "normal"),
            metadata=body.get("metadata", {}),
        )
    )
    return {"lease": lease.to_dict()}


@router.post("/subscriptions/leases/{lease_id}/outcome")
async def update_subscription_outcome(lease_id: str, request: Request):
    from ..subscriptions import record_execution_outcome

    body = await request.json()
    outcome = body.get("outcome", "")
    if not outcome:
        return JSONResponse(status_code=400, content={"error": "'outcome' is required"})

    lease = await record_execution_outcome(
        lease_id=lease_id,
        outcome=outcome,
        throttled=bool(body.get("throttled", False)),
        notes=body.get("notes", ""),
        quality_score=body.get("quality_score"),
        latency_ms=body.get("latency_ms"),
    )
    if lease is None:
        return JSONResponse(status_code=404, content={"error": f"Lease '{lease_id}' not found"})
    return {"lease": lease}


@router.get("/subscriptions/quotas")
async def subscription_quota_summary():
    from ..subscriptions import get_quota_summary

    return await get_quota_summary()
