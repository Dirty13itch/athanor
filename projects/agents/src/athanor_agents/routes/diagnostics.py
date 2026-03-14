"""Diagnostic & utility routes — context preview, routing, cognitive state,
scheduling, preference models, consolidation, briefing."""

import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["diagnostics"])


@router.post("/context/preview")
async def preview_context(request: Request):
    """Preview what context would be injected for a given agent + message."""
    from ..context import enrich_context

    body = await request.json()
    agent_name = body.get("agent", "general-assistant")
    message = body.get("message", "")

    start_ms = int(time.time() * 1000)
    context_str = await enrich_context(agent_name, message)
    duration_ms = int(time.time() * 1000) - start_ms

    return {
        "agent": agent_name,
        "message": message,
        "context": context_str,
        "context_chars": len(context_str),
        "context_tokens_est": len(context_str) // 4,
        "duration_ms": duration_ms,
    }


@router.post("/routing/classify")
async def classify_route(request: Request):
    """Classify a prompt without invoking an agent. Diagnostic endpoint."""
    from ..router import classify_request

    body = await request.json()
    prompt = body.get("prompt", "")
    agent_name = body.get("agent", "")
    conversation_length = body.get("conversation_length", 0)

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "prompt is required"})

    routing = classify_request(prompt, agent_name, conversation_length)
    return routing.to_dict()


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
    return {
        name: s.to_dict()
        for name, s in specialists.items()
    }


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
async def run_consolidation_endpoint():
    """Run memory consolidation pipeline on demand."""
    from ..consolidation import run_consolidation

    results = await run_consolidation()
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
