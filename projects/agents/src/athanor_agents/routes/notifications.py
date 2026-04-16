"""Escalation & notification routes — pending actions, approval workflow."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["notifications"])


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


@router.get("/notifications")
async def get_notifications(include_resolved: bool = False):
    """Get pending agent actions and notifications."""
    from ..escalation import get_pending, get_unread_count
    from ..tasks import get_task_stats, list_tasks

    items = get_pending(include_resolved=include_resolved)

    preview_limit = 50
    pending_tasks = await list_tasks(status="pending_approval", limit=preview_limit)
    stats = await get_task_stats()
    pending_review_queue = int(stats.get("pending_approval", 0) or 0)
    for t in pending_tasks:
        meta = t.get("metadata", {})
        category = meta.get("category", "routine")
        prompt = t.get("prompt", "")
        items.append({
            "id": f"task-{t['id']}",
            "tier": "ask",
            "agent": t["agent"],
            "action": prompt[:120],
            "category": category,
            "confidence": 0.0,
            "description": f"Auto-generated task (priority: {t.get('priority', 'normal')}). Approve to queue for execution.",
            "created_at": t.get("created_at", 0),
            "resolved": False,
            "resolution": "",
        })

    return {
        "notifications": items,
        "count": len(items),
        "approval_preview_count": len(pending_tasks),
        "approval_preview_limit": preview_limit,
        "approval_total_count": pending_review_queue,
        "approval_preview_truncated": pending_review_queue > len(pending_tasks),
        "unread": get_unread_count() + pending_review_queue,
    }


@router.post("/notifications/{action_id}/resolve")
async def resolve_notification(action_id: str, request: Request):
    """Approve or reject a pending agent action or task."""
    body, action, denial = await _load_operator_body(
        request,
        route="/v1/notifications/{action_id}/resolve",
        action_class="admin",
        default_reason=f"Resolved notification {action_id}",
    )
    if denial:
        return denial
    approved = body.get("approved", False)

    if action_id.startswith("task-"):
        from ..tasks import approve_task, cancel_task

        task_id = action_id[len("task-"):]
        if approved:
            ok = await approve_task(task_id)
        else:
            ok = await cancel_task(task_id)
        if ok:
            await emit_operator_audit_event(
                service="agent-server",
                route="/v1/notifications/{action_id}/resolve",
                action_class="admin",
                decision="accepted",
                status_code=200,
                action=action,
                detail=f"Resolved task notification {action_id}",
                target=action_id,
                metadata={"approved": bool(approved)},
            )
            return {"status": "resolved", "id": action_id, "approved": approved}
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/notifications/{action_id}/resolve",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Task {task_id} not found or not awaiting approval",
            target=action_id,
            metadata={"approved": bool(approved)},
        )
        return JSONResponse(
            status_code=404,
            content={"error": f"Task '{task_id}' not found or not awaiting approval"},
        )

    from ..escalation import resolve_action

    if resolve_action(action_id, approved):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/notifications/{action_id}/resolve",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Resolved escalation action {action_id}",
            target=action_id,
            metadata={"approved": bool(approved)},
        )
        return {"status": "resolved", "id": action_id, "approved": approved}
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/notifications/{action_id}/resolve",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Action {action_id} not found or already resolved",
        target=action_id,
        metadata={"approved": bool(approved)},
    )
    return JSONResponse(
        status_code=404,
        content={"error": f"Action '{action_id}' not found or already resolved"},
    )


@router.get("/escalation/config")
async def get_escalation_config():
    """Get escalation threshold configuration."""
    from ..escalation import get_thresholds_config

    return {"thresholds": get_thresholds_config()}


@router.post("/escalation/evaluate")
async def evaluate_escalation(request: Request):
    """Evaluate an action against escalation thresholds."""
    from ..escalation import ActionCategory, evaluate

    body = await request.json()
    agent = body.get("agent", "")
    action = body.get("action", "")
    category_str = body.get("category", "read")
    confidence = body.get("confidence", 0.5)

    try:
        category = ActionCategory(category_str)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid category '{category_str}'. Valid: {[c.value for c in ActionCategory]}"},
        )

    tier = evaluate(agent, action, category, confidence)

    if tier.value in ("notify", "ask"):
        from ..activity import log_event

        asyncio.create_task(log_event(
            event_type="escalation_triggered",
            agent=agent,
            description=f"{tier.value}: {action[:200]}",
            data={"category": category_str, "confidence": confidence, "tier": tier.value},
        ))

    return {
        "agent": agent,
        "action": action,
        "category": category_str,
        "confidence": confidence,
        "tier": tier.value,
    }
