"""Plan and Pipeline API routes."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["plans"])


@router.get("/plans")
async def list_plans_endpoint(status: str = ""):
    """List plans with optional status filter."""
    from ..plan_generator import list_plans

    plans = await list_plans(status=status)
    return {"plans": plans, "count": len(plans)}


@router.get("/plans/{plan_id}")
async def get_plan_endpoint(plan_id: str):
    """Get plan detail."""
    from ..plan_generator import get_plan

    plan = await get_plan(plan_id)
    if not plan:
        return JSONResponse(status_code=404, content={"error": f"Plan '{plan_id}' not found"})
    return {"plan": plan.to_dict()}


@router.post("/plans")
async def create_plan_endpoint(request: Request):
    """Create a plan from operator input."""
    from ..plan_generator import generate_plan_from_intent

    body = await request.json()
    intent_text = body.get("intent", body.get("text", ""))
    source = body.get("source", "operator")
    priority = body.get("priority", 0.7)

    if not intent_text:
        return JSONResponse(status_code=400, content={"error": "Intent text required"})

    plan = await generate_plan_from_intent(
        intent_source=source,
        intent_text=intent_text,
        priority_hint=priority,
        metadata=body.get("metadata", {}),
    )
    return {"plan": plan.to_dict()}


@router.post("/plans/{plan_id}/approve")
async def approve_plan_endpoint(plan_id: str, request: Request):
    """Approve a plan, triggering task decomposition."""
    from ..plan_generator import approve_plan

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    actor = body.get("actor", "shaun")

    plan = await approve_plan(plan_id, actor=actor)
    if not plan:
        return JSONResponse(status_code=404,
                            content={"error": f"Plan '{plan_id}' not found or not pending"})
    return {"approved": True, "plan": plan.to_dict()}


@router.post("/plans/{plan_id}/reject")
async def reject_plan_endpoint(plan_id: str, request: Request):
    """Reject a plan with reason for learning."""
    from ..plan_generator import reject_plan

    body = await request.json()
    reason = body.get("reason", "")

    plan = await reject_plan(plan_id, reason=reason)
    if not plan:
        return JSONResponse(status_code=404,
                            content={"error": f"Plan '{plan_id}' not found or not pending"})
    return {"rejected": True, "plan": plan.to_dict()}


@router.post("/plans/{plan_id}/steer")
async def steer_plan_endpoint(plan_id: str, request: Request):
    """Add steering instructions to a plan."""
    from ..plan_generator import steer_plan

    body = await request.json()
    instructions = body.get("instructions", "")

    if not instructions:
        return JSONResponse(status_code=400, content={"error": "Instructions required"})

    plan = await steer_plan(plan_id, instructions)
    if not plan:
        return JSONResponse(status_code=404, content={"error": f"Plan '{plan_id}' not found"})
    return {"steered": True, "plan": plan.to_dict()}


@router.post("/plans/batch-approve")
async def batch_approve_plans_endpoint(request: Request):
    """Approve multiple plans at once."""
    from ..plan_generator import approve_plan

    body = await request.json()
    plan_ids = body.get("plan_ids", [])

    results = []
    for pid in plan_ids:
        plan = await approve_plan(pid)
        results.append({"plan_id": pid, "approved": plan is not None})

    approved = sum(1 for r in results if r["approved"])
    return {"results": results, "approved": approved, "total": len(results)}


# --- Pipeline endpoints ---

@router.post("/pipeline/cycle")
async def trigger_pipeline_cycle():
    """Trigger a pipeline cycle on-demand."""
    from ..work_pipeline import run_pipeline_cycle
    from dataclasses import asdict

    result = await run_pipeline_cycle()
    return {"cycle": asdict(result)}


@router.get("/pipeline/status")
async def pipeline_status():
    """Get pipeline status."""
    from ..work_pipeline import get_pipeline_status

    return await get_pipeline_status()


@router.get("/pipeline/outcomes")
async def pipeline_outcomes(limit: int = 20):
    """Get recent pipeline outcomes."""
    from ..work_pipeline import get_recent_outcomes

    outcomes = await get_recent_outcomes(limit)
    return {"outcomes": outcomes, "count": len(outcomes)}


@router.get("/pipeline/intents")
async def pipeline_intents():
    """Mine intents without generating plans (preview)."""
    from ..intent_miner import mine_all_sources

    intents = await mine_all_sources()
    return {
        "intents": [
            {
                "source": i.source,
                "text": i.text[:300],
                "priority_hint": i.priority_hint,
                "metadata": i.metadata,
            }
            for i in intents
        ],
        "count": len(intents),
    }
