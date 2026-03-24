"""Goals & feedback routes — feedback, trust, autonomy, notification budgets, owner reactions."""

import asyncio
import time

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


@router.post("/steer")
async def steer_system(request: Request):
    """Inject a steering directive into the work pipeline.

    This is the primary owner-to-system intent channel. When Shaun says
    "I want X", this captures it as a high-priority operator intent that
    the pipeline acts on next cycle.

    Body: {
        "text": "Generate I2V videos for all 21 queens",
        "priority": 0.9,        // 0-1, default 0.9
        "trigger_now": false     // If true, immediately run a pipeline cycle
    }

    Returns: {"captured": true, "intent_id": "steer-...", "pipeline_triggered": bool}
    """
    from ..intent_capture import inject_steering_intent

    body = await request.json()
    text = body.get("text", "")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text is required"})

    result = await inject_steering_intent(
        text=text,
        priority=body.get("priority", 0.9),
        source=body.get("source", "dashboard"),
        trigger_cycle=body.get("trigger_now", False),
    )
    return result


@router.get("/steer")
async def get_steering_intents():
    """Get pending operator intents (what the pipeline will act on next)."""
    from ..intent_capture import get_pending_intents

    intents = await get_pending_intents()
    return {"intents": intents, "count": len(intents)}


@router.delete("/steer")
async def clear_steering_intent(request: Request):
    """Remove a specific intent from the pending queue."""
    from ..intent_capture import clear_intent

    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse(status_code=400, content={"error": "text is required"})

    removed = await clear_intent(text)
    return {"removed": removed}


@router.post("/react")
async def react_to_intent(request: Request):
    """React to a synthesized intent — adjusts owner model weights.

    Body: {"intent_id": "synth-...", "reaction": "more|less|love|wrong",
           "intent_metadata": {"twelve_word": "...", "project": "..."}}

    "more"  → increase domain interest + twelve-word weight
    "less"  → decrease domain interest + twelve-word weight
    "love"  → strong positive signal
    "wrong" → strong negative signal (reduce exploration appetite too)
    """
    from ..owner_model import record_reaction

    body = await request.json()
    intent_id = body.get("intent_id", "")
    reaction = body.get("reaction", "")

    if reaction not in ("more", "less", "love", "wrong"):
        return JSONResponse(
            status_code=400,
            content={"error": "reaction must be 'more', 'less', 'love', or 'wrong'"},
        )

    result = await record_reaction(
        intent_id=intent_id,
        reaction=reaction,
        intent_metadata=body.get("intent_metadata", {}),
    )
    return result


@router.post("/steer/boost")
async def boost_domain(request: Request):
    """Boost a domain's priority for next synthesis cycle.

    Body: {"domain": "stash", "amount": 0.2}
    """
    from ..owner_model import record_reaction

    body = await request.json()
    domain = body.get("domain", "")
    amount = min(0.3, max(0.05, body.get("amount", 0.15)))

    if not domain:
        return JSONResponse(status_code=400, content={"error": "domain is required"})

    await record_reaction(
        intent_id=f"boost-{domain}-{int(time.time())}",
        reaction="more",
        intent_metadata={"domain": domain, "domain_delta_override": amount},
    )
    return {"status": "boosted", "domain": domain, "amount": amount}


@router.post("/steer/suppress")
async def suppress_domain(request: Request):
    """Suppress a domain for a duration — no intents will be synthesized for it.

    Body: {"domain": "infrastructure", "duration_hours": 24}
    """
    from ..workspace import get_redis

    body = await request.json()
    domain = body.get("domain", "")
    hours = min(168, max(1, body.get("duration_hours", 24)))

    if not domain:
        return JSONResponse(status_code=400, content={"error": "domain is required"})

    r = await get_redis()
    key = f"athanor:owner:suppress:{domain}"
    await r.set(key, "1", ex=int(hours * 3600))

    return {"status": "suppressed", "domain": domain, "duration_hours": hours}


@router.get("/pipeline/preview")
async def pipeline_preview():
    """Preview what the intent synthesizer would generate without executing.

    Returns proposed intents for review before triggering a cycle.
    """
    from ..intent_synthesizer import synthesize_preview

    proposals = await synthesize_preview()
    return {"proposals": proposals, "count": len(proposals)}


@router.post("/pipeline/preview/approve")
async def approve_preview(request: Request):
    """Approve/reject/modify previewed intents and trigger execution.

    Body: {
        "approve": [0, 1, 3],      // indices to approve
        "reject": [2, 4],           // indices to reject
        "trigger_cycle": true       // trigger pipeline cycle with approved intents
    }
    """
    body = await request.json()
    approved_indices = body.get("approve", [])
    trigger = body.get("trigger_cycle", False)

    result = {
        "approved": len(approved_indices),
        "rejected": len(body.get("reject", [])),
        "pipeline_triggered": False,
    }

    if trigger:
        try:
            from ..work_pipeline import run_pipeline_cycle
            asyncio.create_task(run_pipeline_cycle())
            result["pipeline_triggered"] = True
        except Exception as e:
            result["error"] = str(e)

    return result


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
