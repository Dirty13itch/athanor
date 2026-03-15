"""Workflow routes -- run and inspect multi-step agent workflows."""

import asyncio
import logging

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["workflows"])

logger = logging.getLogger(__name__)


@router.post("/workflows/{name}/run")
async def run_workflow(name: str, request: Request):
    """Execute a multi-step workflow by name.

    Body: {"input": "research topic or request", ...extra context keys...}

    The workflow runs each step sequentially, passing outputs forward.
    Returns the final result plus per-step traces.
    """
    from ..workflows.executor import execute_workflow

    body = await request.json()
    user_input = body.get("input", "")
    if not user_input:
        return JSONResponse(
            status_code=400,
            content={"error": "'input' is required in request body"},
        )

    # Pass entire body as initial_input so extra keys are available as
    # template variables alongside {input}
    initial_input = dict(body)
    initial_input.setdefault("input", user_input)

    logger.info("Workflow '%s' triggered with input: %.100s", name, user_input)
    result = await execute_workflow(name, initial_input)

    if result["status"] == "failed":
        return JSONResponse(status_code=422, content=result)
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
