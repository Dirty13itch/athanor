"""Escalation & notification routes — pending actions, approval workflow."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["notifications"])


@router.get("/notifications")
async def get_notifications(include_resolved: bool = False):
    """Get pending agent actions and notifications."""
    from ..escalation import get_pending, get_unread_count
    from ..tasks import list_tasks

    items = get_pending(include_resolved=include_resolved)

    pending_tasks = await list_tasks(status="pending_approval", limit=50)
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
        "unread": get_unread_count() + len(pending_tasks),
    }


@router.post("/notifications/{action_id}/resolve")
async def resolve_notification(action_id: str, request: Request):
    """Approve or reject a pending agent action or task."""
    body = await request.json()
    approved = body.get("approved", False)

    if action_id.startswith("task-"):
        from ..tasks import approve_task, cancel_task

        task_id = action_id[len("task-"):]
        if approved:
            ok = await approve_task(task_id)
        else:
            ok = await cancel_task(task_id)
        if ok:
            return {"status": "resolved", "id": action_id, "approved": approved}
        return JSONResponse(
            status_code=404,
            content={"error": f"Task '{task_id}' not found or not awaiting approval"},
        )

    from ..escalation import resolve_action

    if resolve_action(action_id, approved):
        return {"status": "resolved", "id": action_id, "approved": approved}
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
