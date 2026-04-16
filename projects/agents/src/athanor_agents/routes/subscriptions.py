"""Subscription control layer â€” providers, policies, leases, quotas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["subscriptions"])


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


def _body_metadata(body: dict[str, Any]) -> dict[str, Any]:
    metadata = body.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


async def _emit_subscription_validation_denial(
    *,
    route: str,
    action_class: str,
    action,
    detail: str,
    target: str | None = None,
):
    await emit_operator_audit_event(
        service="agent-server",
        route=route,
        action_class=action_class,
        decision="denied",
        status_code=400,
        action=action,
        detail=detail,
        target=target,
    )
    return JSONResponse(status_code=400, content={"error": detail})


@router.get("/subscriptions/providers")
async def subscription_providers():
    from ..subscriptions import get_policy_snapshot, get_provider_catalog_snapshot

    policy = get_policy_snapshot()
    catalog = get_provider_catalog_snapshot(policy_only=False)
    return {
        "providers": catalog["providers"],
        "count": catalog["count"],
        "policy_source": policy["policy_source"],
        "catalog_version": catalog["version"],
        "catalog_source": catalog["source_of_truth"],
    }


@router.get("/subscriptions/policy")
async def subscription_policy():
    from ..subscriptions import get_policy_snapshot

    return get_policy_snapshot()


@router.get("/subscriptions/summary")
async def subscription_summary(limit: int = 10):
    from ..backbone import build_quota_lease_summary

    return await build_quota_lease_summary(limit=limit)


@router.get("/subscriptions/leases")
async def subscription_leases(requester: str = "", limit: int = 50):
    from ..subscriptions import list_execution_leases

    leases = await list_execution_leases(requester=requester, limit=limit)
    return {"leases": leases, "count": len(leases)}


@router.post("/subscriptions/leases")
async def create_subscription_lease(request: Request):
    from ..subscriptions import LeaseRequest, issue_execution_lease

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/subscriptions/leases",
        action_class="operator",
        default_reason="Issued provider execution lease",
    )
    if denial:
        return denial

    requester = str(body.get("requester", "")).strip()
    task_class = str(body.get("task_class", "")).strip()
    if not requester or not task_class:
        return await _emit_subscription_validation_denial(
            route="/v1/subscriptions/leases",
            action_class="operator",
            action=action,
            detail="Both 'requester' and 'task_class' are required",
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
            metadata=_body_metadata(body),
        )
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/subscriptions/leases",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Issued execution lease {lease.id}",
        target=lease.id,
        metadata={
            "requester": requester,
            "task_class": task_class,
            "provider": lease.provider,
        },
    )
    return {"lease": lease.to_dict()}


@router.post("/subscriptions/leases/{lease_id}/outcome")
async def update_subscription_outcome(lease_id: str, request: Request):
    from ..subscriptions import record_execution_outcome

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/subscriptions/leases/{lease_id}/outcome",
        action_class="admin",
        default_reason=f"Recorded execution lease outcome for {lease_id}",
    )
    if denial:
        return denial

    outcome = str(body.get("outcome", "")).strip()
    if not outcome:
        return await _emit_subscription_validation_denial(
            route="/v1/subscriptions/leases/{lease_id}/outcome",
            action_class="admin",
            action=action,
            detail="'outcome' is required",
            target=lease_id,
        )

    lease = await record_execution_outcome(
        lease_id=lease_id,
        outcome=outcome,
        throttled=bool(body.get("throttled", False)),
        notes=body.get("notes", ""),
        quality_score=body.get("quality_score"),
        latency_ms=body.get("latency_ms"),
    )
    if lease is None:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/leases/{lease_id}/outcome",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Lease '{lease_id}' not found",
            target=lease_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Lease '{lease_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/subscriptions/leases/{lease_id}/outcome",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded outcome {outcome} for execution lease {lease_id}",
        target=lease_id,
        metadata={
            "outcome": outcome,
            "throttled": bool(body.get("throttled", False)),
        },
    )
    return {"lease": lease}


@router.get("/subscriptions/execution")
async def subscription_execution(limit: int = 10):
    from ..provider_execution import build_provider_execution_snapshot

    return await build_provider_execution_snapshot(limit=limit)


@router.post("/subscriptions/execution")
async def execute_subscription_provider(request: Request):
    from ..provider_execution import execute_provider_request

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/subscriptions/execution",
        action_class="admin",
        default_reason="Executed provider request",
    )
    if denial:
        return denial

    requester = str(body.get("requester", "")).strip()
    prompt = str(body.get("prompt", "")).strip()
    task_class = str(body.get("task_class", "")).strip()
    if not requester or not prompt or not task_class:
        return await _emit_subscription_validation_denial(
            route="/v1/subscriptions/execution",
            action_class="admin",
            action=action,
            detail="'requester', 'prompt', and 'task_class' are required",
        )

    timeout_seconds = body.get("timeout_seconds", 90)
    try:
        timeout_seconds = max(int(timeout_seconds), 1)
    except (TypeError, ValueError):
        timeout_seconds = 90

    try:
        result = await execute_provider_request(
            requester=requester,
            prompt=prompt,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            metadata=_body_metadata(body),
            issue_lease=bool(body.get("issue_lease", True)),
            timeout_seconds=timeout_seconds,
            operator_action=action.to_dict(),
        )
    except PermissionError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/execution",
            action_class="admin",
            decision="denied",
            status_code=403,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=403, content={"error": str(exc)})
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/execution",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    handoff = result.get("handoff", {}) if isinstance(result.get("handoff"), dict) else {}
    target = str(handoff.get("id", "")).strip() or None
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/subscriptions/execution",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=str(result.get("message") or "Processed provider execution request"),
        target=target,
        metadata={
            "provider": str(result.get("provider", "")),
            "status": str(result.get("status", "")),
            "task_class": task_class,
            "requester": requester,
        },
    )
    return result


@router.get("/subscriptions/handoffs")
async def subscription_handoffs(requester: str = "", limit: int = 25):
    from ..provider_execution import list_handoff_bundles

    handoffs = await list_handoff_bundles(requester=requester, limit=limit)
    return {"handoffs": handoffs, "count": len(handoffs)}


@router.post("/subscriptions/handoffs")
async def create_subscription_handoff(request: Request):
    from ..provider_execution import create_handoff_bundle

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/subscriptions/handoffs",
        action_class="operator",
        default_reason="Created provider handoff bundle",
    )
    if denial:
        return denial

    requester = str(body.get("requester", "")).strip()
    prompt = str(body.get("prompt", "")).strip()
    task_class = str(body.get("task_class", "")).strip()
    if not requester or not prompt or not task_class:
        return await _emit_subscription_validation_denial(
            route="/v1/subscriptions/handoffs",
            action_class="operator",
            action=action,
            detail="'requester', 'prompt', and 'task_class' are required",
        )

    try:
        handoff = await create_handoff_bundle(
            requester=requester,
            prompt=prompt,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            metadata=_body_metadata(body),
            issue_lease=bool(body.get("issue_lease", True)),
        )
    except PermissionError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/handoffs",
            action_class="operator",
            decision="denied",
            status_code=403,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=403, content={"error": str(exc)})
    except ValueError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/handoffs",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail=str(exc),
        )
        return JSONResponse(status_code=400, content={"error": str(exc)})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/subscriptions/handoffs",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created provider handoff bundle {handoff.get('id', '')}",
        target=str(handoff.get("id", "")),
        metadata={
            "provider": str(handoff.get("provider", "")),
            "execution_mode": str(handoff.get("execution_mode", "")),
            "task_class": task_class,
            "requester": requester,
        },
    )
    return {"handoff": handoff}


@router.post("/subscriptions/handoffs/{handoff_id}/outcome")
async def update_subscription_handoff_outcome(handoff_id: str, request: Request):
    from ..provider_execution import record_handoff_outcome

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/subscriptions/handoffs/{handoff_id}/outcome",
        action_class="admin",
        default_reason=f"Recorded provider handoff outcome for {handoff_id}",
    )
    if denial:
        return denial

    outcome = str(body.get("outcome", "")).strip()
    if not outcome:
        return await _emit_subscription_validation_denial(
            route="/v1/subscriptions/handoffs/{handoff_id}/outcome",
            action_class="admin",
            action=action,
            detail="'outcome' is required",
            target=handoff_id,
        )

    handoff = await record_handoff_outcome(
        handoff_id=handoff_id,
        outcome=outcome,
        notes=str(body.get("notes", "")),
        result_summary=str(body.get("result_summary", "")),
        artifact_refs=body.get("artifact_refs") if isinstance(body.get("artifact_refs"), list) else None,
        quality_score=body.get("quality_score"),
        latency_ms=body.get("latency_ms"),
        execution_details=body.get("execution_details") if isinstance(body.get("execution_details"), dict) else None,
    )
    if handoff is None:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/subscriptions/handoffs/{handoff_id}/outcome",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Handoff '{handoff_id}' not found",
            target=handoff_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Handoff '{handoff_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/subscriptions/handoffs/{handoff_id}/outcome",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded outcome {outcome} for provider handoff {handoff_id}",
        target=handoff_id,
        metadata={"outcome": outcome},
    )
    return {"handoff": handoff}


@router.get("/subscriptions/quotas")
async def subscription_quota_summary():
    from ..subscriptions import get_quota_summary

    return await get_quota_summary()


@router.get("/subscriptions/cli-status")
async def cli_status():
    """CLI reachability and usage stats."""
    from ..cloud_manager import get_cli_status

    return await get_cli_status()


@router.get("/subscriptions/routing-log")
async def routing_log(limit: int = 30):
    """Recent dispatch/routing decisions."""
    from ..cloud_manager import get_routing_log

    entries = await get_routing_log(limit=limit)
    return {"entries": entries, "count": len(entries)}


@router.get("/subscriptions/provider-status")
async def provider_status():
    """Provider status for the routing/models dashboard."""
    from ..cloud_manager import get_provider_status

    providers = await get_provider_status()
    return {"providers": providers, "count": len(providers)}
