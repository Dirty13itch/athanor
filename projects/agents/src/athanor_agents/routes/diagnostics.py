"""Diagnostic & utility routes â€” context preview, routing, cognitive state,
scheduling, preference models, consolidation, briefing."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["diagnostics"])


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


@router.post("/context/preview")
async def preview_context(request: Request):
    """Preview what context would be injected for a given agent + message."""
    from ..context import enrich_context

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/context/preview",
        action_class="operator",
        default_reason="Previewed routed context",
    )
    if denial:
        return denial
    agent_name = body.get("agent", "general-assistant")
    message = body.get("message", "")

    start_ms = int(time.time() * 1000)
    context_str = await enrich_context(agent_name, message)
    duration_ms = int(time.time() * 1000) - start_ms

    response = {
        "agent": agent_name,
        "message": message,
        "context": context_str,
        "context_chars": len(context_str),
        "context_tokens_est": len(context_str) // 4,
        "duration_ms": duration_ms,
    }
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/context/preview",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Previewed routed context",
        target=agent_name,
        metadata={
            "context_chars": response["context_chars"],
            "duration_ms": duration_ms,
        },
    )
    return response


@router.post("/routing/classify")
async def classify_route(request: Request):
    """Classify a prompt without invoking an agent. Diagnostic endpoint."""
    from ..router import classify_request

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/routing/classify",
        action_class="operator",
        default_reason="Classified routing diagnostics",
    )
    if denial:
        return denial
    prompt = body.get("prompt", "")
    agent_name = body.get("agent", "")
    conversation_length = body.get("conversation_length", 0)

    if not prompt:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/routing/classify",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="prompt is required",
        )
        return JSONResponse(status_code=400, content={"error": "prompt is required"})

    routing = classify_request(prompt, agent_name, conversation_length)
    response = routing.to_dict()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/routing/classify",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Classified routing diagnostics",
        target=agent_name or "routing",
        metadata={
            "task_type": response.get("task_type"),
            "policy_class": response.get("policy_class"),
            "meta_lane": response.get("meta_lane"),
        },
    )
    return response


@router.get("/cognitive/cst")
async def get_cst_state():
    """Get current Continuous State Tensor state."""
    from ..cst import get_cst

    cst = await get_cst()
    return cst.to_dict()


@router.get("/cognitive/specialists")
async def get_specialist_state():
    """Get specialist registry with inhibition and competition stats."""
    from ..specialist import get_specialists

    specialists = get_specialists()
    return {name: s.to_dict() for name, s in specialists.items()}


@router.get("/scheduling/status")
async def scheduling_status():
    """Get current inference load and agent scheduling state."""
    from ..scheduling import get_scheduling_status

    return await get_scheduling_status()


@router.get("/preferences/models")
async def get_model_preferences():
    """Get all learned model preferences, grouped by task type."""
    from ..preferences import get_all_preferences

    return await get_all_preferences()


@router.post("/consolidate")
async def run_consolidation_endpoint(request: Request):
    """Run memory consolidation pipeline on demand."""
    from ..consolidation import run_consolidation

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/consolidate",
        action_class="admin",
        default_reason="Ran consolidation",
    )
    if denial:
        return denial

    results = await run_consolidation()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/consolidate",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Ran consolidation pipeline",
        metadata={
            "activity": int(results.get("activity", 0) or 0),
            "conversations": int(results.get("conversations", 0) or 0),
            "implicit_feedback": int(results.get("implicit_feedback", 0) or 0),
            "events": int(results.get("events", 0) or 0),
        },
    )
    return results


@router.get("/consolidate/stats")
async def consolidation_stats():
    """Get current point counts for all consolidation-tracked collections."""
    from ..consolidation import get_collection_stats

    return await get_collection_stats()


@router.get("/briefing")
async def get_briefing():
    """Structured morning briefing."""
    from ..briefing import generate_briefing

    briefing = await generate_briefing()
    return briefing.to_dict()
