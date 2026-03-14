"""Goals & feedback routes — feedback, trust, autonomy, notification budgets."""

import asyncio

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["goals"])


@router.post("/feedback")
async def post_feedback(request: Request):
    """Store feedback (thumbs up/down) on an agent response.

    Body: {"agent": "general-assistant", "feedback_type": "thumbs_up",
           "message_content": "the user message", "response_content": "the agent response"}
    """
    from ..goals import store_feedback

    body = await request.json()
    agent = body.get("agent", "general-assistant")
    feedback_type = body.get("feedback_type", "thumbs_up")
    message_content = body.get("message_content", "")
    response_content = body.get("response_content", "")

    if feedback_type not in ("thumbs_up", "thumbs_down"):
        return JSONResponse(
            status_code=400,
            content={"error": "feedback_type must be 'thumbs_up' or 'thumbs_down'"},
        )

    result = await store_feedback(
        agent=agent,
        message_content=message_content,
        feedback_type=feedback_type,
        response_content=response_content,
    )

    # Record preference learning outcome
    from ..preferences import record_outcome as record_pref_outcome
    from ..router import classify_request
    pref_feedback = "positive" if feedback_type == "thumbs_up" else "negative"
    task_type = classify_request(message_content, agent).task_type.value
    model = body.get("model", "reasoning")  # Default to reasoning if not specified
    asyncio.create_task(record_pref_outcome(
        model=model, task_type=task_type, feedback=pref_feedback,
    ))

    # Log feedback event for pattern detection
    from ..activity import log_event
    asyncio.create_task(log_event(
        event_type="feedback_received",
        agent=agent,
        description=f"{feedback_type}: {message_content[:200]}",
        data={"feedback_type": feedback_type},
    ))

    # Immediate trust regression on negative feedback
    if feedback_type == "thumbs_down":
        from ..escalation import get_all_adjustments, set_autonomy_adjustment
        current = await get_all_adjustments()
        key = f"{agent}:routine"
        current_adj = current.get(key, 0.0)
        asyncio.create_task(set_autonomy_adjustment(agent, "routine", current_adj + 0.03))

    return result


@router.post("/feedback/implicit")
async def post_implicit_feedback(request: Request):
    """Store batched implicit feedback events from the dashboard client.

    Body: {"session_id": "abc123", "events": [
        {"type": "page_view", "page": "/", "timestamp": 1740000000000},
        {"type": "dwell", "page": "/agents", "duration_ms": 15000, "timestamp": 1740000015000},
        {"type": "tap", "page": "/chat", "agent": "media-agent", "metadata": {"target": "send"}, "timestamp": 1740000020000}
    ]}
    """
    from ..activity import store_implicit_events

    body = await request.json()
    session_id = body.get("session_id", "")
    events = body.get("events", [])

    if not events:
        return {"stored": 0}

    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})

    stored = await store_implicit_events(session_id=session_id, events=events)
    return {"stored": stored, "received": len(events)}


@router.get("/notification-budget")
async def get_notification_budget(agent: str = ""):
    """Get notification budget status for agents.

    Optionally filter by agent name. Returns daily limits, used counts, and remaining budget.
    """
    from ..goals import check_notification_budget, get_notification_budgets

    if agent:
        budget = await check_notification_budget(agent)
        return {"agent": agent, **budget}
    return {"budgets": await get_notification_budgets()}


@router.get("/goals")
async def get_goals(agent: str = "", active_only: bool = True):
    """List active steering goals."""
    from ..goals import list_goals

    goals = await list_goals(agent=agent, active_only=active_only)
    return {"goals": goals, "count": len(goals)}


@router.post("/goals")
async def create_goal_endpoint(request: Request):
    """Create a new steering goal.

    Body: {"text": "Keep GPU utilization above 50%", "agent": "global", "priority": "normal"}
    """
    from ..goals import create_goal

    body = await request.json()
    text = body.get("text", "")
    agent = body.get("agent", "global")
    priority = body.get("priority", "normal")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text is required"})

    goal = await create_goal(text=text, agent=agent, priority=priority)
    return {"status": "created", "goal": goal}


@router.delete("/goals/{goal_id}")
async def delete_goal_endpoint(goal_id: str):
    """Delete a steering goal."""
    from ..goals import delete_goal

    if await delete_goal(goal_id):
        return {"status": "deleted", "id": goal_id}
    return JSONResponse(status_code=404, content={"error": f"Goal '{goal_id}' not found"})


@router.get("/trust")
async def get_trust_scores():
    """Get trust scores per agent (derived from feedback + escalation history)."""
    from ..goals import compute_trust_scores

    return await compute_trust_scores()


@router.get("/autonomy")
async def get_autonomy_adjustments():
    """Get current autonomy threshold adjustments per agent.

    Positive = less autonomy (higher thresholds).
    Negative = more autonomy (lower thresholds).
    """
    from ..escalation import get_all_adjustments

    adjustments = await get_all_adjustments()
    return {"adjustments": adjustments, "max_adjustment": 0.15}


@router.post("/autonomy/reset")
async def reset_autonomy(request: Request):
    """Reset autonomy adjustments for an agent (or all agents).

    Body: {"agent": "media-agent"} or {} for all.
    """
    from ..workspace import get_redis
    from ..escalation import AUTONOMY_ADJUSTMENTS_KEY, refresh_adjustment_cache

    body = await request.json()
    agent = body.get("agent", "")

    r = await get_redis()
    if agent:
        # Remove all adjustments for this agent
        all_keys = await r.hkeys(AUTONOMY_ADJUSTMENTS_KEY)
        removed = 0
        for k in all_keys:
            key = k.decode() if isinstance(k, bytes) else k
            if key.startswith(f"{agent}:"):
                await r.hdel(AUTONOMY_ADJUSTMENTS_KEY, key)
                removed += 1
        await refresh_adjustment_cache()
        return {"status": "reset", "agent": agent, "removed": removed}
    else:
        await r.delete(AUTONOMY_ADJUSTMENTS_KEY)
        await refresh_adjustment_cache()
        return {"status": "reset", "agent": "all"}
