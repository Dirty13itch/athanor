"""Workflow routes -- run and inspect multi-step agent workflows."""

import logging

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["workflows"])

logger = logging.getLogger(__name__)


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


@router.post("/workflows/{name}/run")
async def run_workflow(name: str, request: Request):
    """Execute a multi-step workflow by name."""
    from ..workflows.executor import execute_workflow

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workflows/{name}/run",
        action_class="admin",
        default_reason=f"Executed workflow {name}",
    )
    if denial:
        return denial

    user_input = body.get("input", "")
    if not user_input:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workflows/{name}/run",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="'input' is required in request body",
            target=name,
        )
        return JSONResponse(status_code=400, content={"error": "'input' is required in request body"})

    initial_input = dict(body)
    initial_input.setdefault("input", user_input)

    logger.info("Workflow '%s' triggered with input: %.100s", name, user_input)
    result = await execute_workflow(name, initial_input)

    if result["status"] == "failed":
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workflows/{name}/run",
            action_class="admin",
            decision="denied",
            status_code=422,
            action=action,
            detail=f"Workflow {name} failed",
            target=name,
        )
        return JSONResponse(status_code=422, content=result)

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workflows/{name}/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Executed workflow {name}",
        target=name,
        metadata={"status": result.get("status")},
    )
    return result


@router.get("/workflows")
async def list_all_workflows():
    """List all registered workflow definitions."""
    from ..workflows.registry import list_workflows

    workflows = list_workflows()
    return {
        "workflows": [
            {
                "name": w["name"],
                "description": w["description"],
                "step_count": len(w["steps"]),
                "steps": [
                    {
                        "agent_id": s["agent_id"],
                        "action": s["action"],
                        "output_key": s["output_key"],
                    }
                    for s in w["steps"]
                ],
            }
            for w in workflows
        ],
        "count": len(workflows),
    }


@router.get("/workflows/{name}")
async def get_workflow_detail(name: str):
    """Get a single workflow definition by name."""
    from ..workflows.registry import get_workflow

    defn = get_workflow(name)
    if defn is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Workflow '{name}' not found"},
        )

    return {
        "name": defn["name"],
        "description": defn["description"],
        "steps": [
            {
                "agent_id": s["agent_id"],
                "action": s["action"],
                "input_template": s["input_template"],
                "output_key": s["output_key"],
            }
            for s in defn["steps"]
        ],
    }
