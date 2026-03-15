"""Workflow executor -- runs multi-step agent workflows sequentially."""

from __future__ import annotations

import logging
import time
import uuid

import httpx

from ..config import settings
from .registry import get_workflow

logger = logging.getLogger(__name__)

STEP_TIMEOUT = 120  # seconds per step


async def execute_workflow(
    workflow_name: str,
    initial_input: dict,
) -> dict:
    """Execute a named workflow end-to-end.

    Args:
        workflow_name: Registered workflow name.
        initial_input: Dict with at least {"input": "..."}. Additional keys
                       are available as template variables.

    Returns:
        {
            "workflow": workflow_name,
            "status": "completed" | "failed",
            "result": <final step output>,
            "steps": [<step trace dicts>],
            "duration_ms": int,
            "error": str | None,
        }
    """
    definition = get_workflow(workflow_name)
    if definition is None:
        return {
            "workflow": workflow_name,
            "status": "failed",
            "result": None,
            "steps": [],
            "duration_ms": 0,
            "error": f"Workflow '{workflow_name}' not found",
        }

    steps = definition["steps"]
    context: dict[str, str] = dict(initial_input)
    step_traces: list[dict] = []
    start = time.time()

    for i, step in enumerate(steps):
        agent_id: str = step["agent_id"]
        action: str = step["action"]
        input_template: str = step["input_template"]
        output_key: str = step["output_key"]

        # Render prompt template with accumulated context
        try:
            prompt = input_template.format(**context)
        except KeyError as e:
            error_msg = (
                f"Step {i} ({action}): missing template variable {e}"
            )
            logger.error(error_msg)
            step_traces.append(_make_trace(i, agent_id, action, "", error_msg, 0))
            return _finish(workflow_name, "failed", None, step_traces, start, error_msg)

        step_start = time.time()
        logger.info(
            "Workflow '%s' step %d/%d: agent=%s action=%s",
            workflow_name, i + 1, len(steps), agent_id, action,
        )

        try:
            result_text = await _call_agent(agent_id, prompt)
        except Exception as e:
            error_msg = f"Step {i} ({action}): agent call failed: {e}"
            logger.error(error_msg)
            step_ms = int((time.time() - step_start) * 1000)
            step_traces.append(_make_trace(i, agent_id, action, prompt, error_msg, step_ms))
            return _finish(workflow_name, "failed", None, step_traces, start, error_msg)

        step_ms = int((time.time() - step_start) * 1000)
        step_traces.append(_make_trace(i, agent_id, action, prompt, result_text, step_ms))

        # Store output for downstream steps
        context[output_key] = result_text

        logger.info(
            "Workflow '%s' step %d/%d completed in %dms",
            workflow_name, i + 1, len(steps), step_ms,
        )

    # Final result is the last step's output
    final_key = steps[-1]["output_key"]
    return _finish(workflow_name, "completed", context.get(final_key, ""), step_traces, start)


async def _call_agent(agent_id: str, prompt: str) -> str:
    """Call an agent via the local chat completions endpoint.

    Uses the same /v1/chat/completions endpoint that external clients use,
    keeping routing, context injection, and logging consistent.
    """
    base_url = settings.agent_server_url.rstrip("/")
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": agent_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "skip_cache": True,  # workflows need fresh results
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(STEP_TIMEOUT)) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Extract assistant response
    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"No choices returned from agent {agent_id}")

    return choices[0].get("message", {}).get("content", "")


def _make_trace(
    index: int,
    agent_id: str,
    action: str,
    prompt: str,
    output: str,
    duration_ms: int,
) -> dict:
    """Build a step trace dict for the response."""
    return {
        "index": index,
        "agent_id": agent_id,
        "action": action,
        "prompt": prompt[:500],
        "output": output[:2000],
        "duration_ms": duration_ms,
        "timestamp": time.time(),
    }


def _finish(
    workflow_name: str,
    status: str,
    result: str | None,
    step_traces: list[dict],
    start: float,
    error: str | None = None,
) -> dict:
    """Build the final workflow result dict."""
    return {
        "workflow": workflow_name,
        "status": status,
        "result": result,
        "steps": step_traces,
        "duration_ms": int((time.time() - start) * 1000),
        "error": error,
    }
