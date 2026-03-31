"""Plan and Pipeline API routes."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["plans"])


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

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/plans",
        action_class="operator",
        default_reason="Manual plan creation",
    )
    if denial:
        return denial
    intent_text = body.get("intent", body.get("text", ""))
    source = body.get("source", "operator")
    priority = body.get("priority", 0.7)

    if not intent_text:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/plans",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="Intent text required",
        )
        return JSONResponse(status_code=400, content={"error": "Intent text required"})

    plan = await generate_plan_from_intent(
        intent_source=source,
        intent_text=intent_text,
        priority_hint=priority,
        metadata=body.get("metadata", {}),
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/plans",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created plan {plan.id}",
        target=plan.id,
        metadata={"source": str(source), "priority": priority},
    )
    return {"plan": plan.to_dict()}


@router.post("/plans/{plan_id}/approve")
async def approve_plan_endpoint(plan_id: str, request: Request):
    """Approve a plan, triggering task decomposition."""
    from ..plan_generator import approve_plan

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/plans/{plan_id}/approve",
        action_class="admin",
        default_reason=f"Approved plan {plan_id}",
    )
    if denial:
        return denial

    plan = await approve_plan(plan_id, actor=action.actor)
    if not plan:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/plans/{plan_id}/approve",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Plan {plan_id} not found or not pending",
            target=plan_id,
        )
        return JSONResponse(status_code=404,
                            content={"error": f"Plan '{plan_id}' not found or not pending"})
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/plans/{plan_id}/approve",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Approved plan {plan_id}",
        target=plan_id,
    )
    return {"approved": True, "plan": plan.to_dict()}


@router.post("/plans/{plan_id}/reject")
async def reject_plan_endpoint(plan_id: str, request: Request):
    """Reject a plan with reason for learning."""
    from ..plan_generator import reject_plan

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/plans/{plan_id}/reject",
        action_class="admin",
        default_reason=f"Rejected plan {plan_id}",
    )
    if denial:
        return denial

    plan = await reject_plan(plan_id, reason=action.reason)
    if not plan:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/plans/{plan_id}/reject",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Plan {plan_id} not found or not pending",
            target=plan_id,
        )
        return JSONResponse(status_code=404,
                            content={"error": f"Plan '{plan_id}' not found or not pending"})
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/plans/{plan_id}/reject",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Rejected plan {plan_id}",
        target=plan_id,
    )
    return {"rejected": True, "plan": plan.to_dict()}


@router.post("/plans/{plan_id}/steer")
async def steer_plan_endpoint(plan_id: str, request: Request):
    """Add steering instructions to a plan."""
    from ..plan_generator import steer_plan

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/plans/{plan_id}/steer",
        action_class="admin",
        default_reason=f"Steered plan {plan_id}",
    )
    if denial:
        return denial
    instructions = body.get("instructions", "")

    if not instructions:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/plans/{plan_id}/steer",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="Instructions required",
            target=plan_id,
        )
        return JSONResponse(status_code=400, content={"error": "Instructions required"})

    plan = await steer_plan(plan_id, instructions)
    if not plan:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/plans/{plan_id}/steer",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Plan {plan_id} not found",
            target=plan_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Plan '{plan_id}' not found"})
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/plans/{plan_id}/steer",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Steered plan {plan_id}",
        target=plan_id,
    )
    return {"steered": True, "plan": plan.to_dict()}


@router.post("/plans/batch-approve")
async def batch_approve_plans_endpoint(request: Request):
    """Approve multiple plans at once."""
    from ..plan_generator import approve_plan

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/plans/batch-approve",
        action_class="admin",
        default_reason="Batch approved plans",
    )
    if denial:
        return denial
    plan_ids = body.get("plan_ids", [])

    results = []
    for pid in plan_ids:
        plan = await approve_plan(pid)
        results.append({"plan_id": pid, "approved": plan is not None})

    approved = sum(1 for r in results if r["approved"])
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/plans/batch-approve",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Batch approved {approved}/{len(results)} plans",
        metadata={"plan_ids": plan_ids},
    )
    return {"results": results, "approved": approved, "total": len(results)}


# --- Pipeline endpoints ---

@router.post("/pipeline/cycle")
async def trigger_pipeline_cycle(request: Request):
    """Trigger a pipeline cycle on-demand."""
    from ..work_pipeline import run_pipeline_cycle
    from dataclasses import asdict

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/pipeline/cycle",
        action_class="admin",
        default_reason="Manual pipeline cycle trigger",
    )
    if denial:
        return denial
    result = await run_pipeline_cycle()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/pipeline/cycle",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Triggered pipeline cycle",
        metadata={"tasks_submitted": result.tasks_submitted, "tasks_held": result.tasks_held},
    )
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
