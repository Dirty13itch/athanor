"""Work planner, projects, and output file routes."""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["planning"])
OUTPUT_DIR = "/output"


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


@router.get("/workplan")
async def get_workplan():
    """Get the current work plan and queue status."""
    from ..workplanner import get_current_plan, get_plan_history, should_refill

    plan = await get_current_plan()
    history = await get_plan_history(limit=5)
    needs_refill = await should_refill()

    return {
        "current_plan": plan,
        "history": history,
        "needs_refill": needs_refill,
    }


@router.post("/workplan/generate")
async def trigger_workplan(request: Request):
    """Manually trigger work plan generation."""
    from ..workplanner import generate_work_plan

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workplan/generate",
        action_class="admin",
        default_reason="Generated work plan",
    )
    if denial:
        return denial
    focus = body.get("focus", "")

    plan = await generate_work_plan(focus=focus)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workplan/generate",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Generated work plan",
        metadata={"focus": focus, "task_count": int(plan.get("task_count", 0))},
    )
    return plan


@router.post("/workplan/redirect")
async def redirect_workplan(request: Request):
    """Steer the work planner with a preference or focus direction."""
    from ..activity import store_preference
    from ..workplanner import generate_work_plan

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workplan/redirect",
        action_class="operator",
        default_reason="Redirected work plan",
    )
    if denial:
        return denial
    direction = body.get("direction", "")

    if not direction:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workplan/redirect",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="direction is required",
        )
        return JSONResponse(status_code=400, content={"error": "direction is required"})

    await store_preference(
        agent="global",
        signal_type="work_direction",
        content=direction,
        category="work_planning",
    )

    asyncio.create_task(generate_work_plan(focus=direction))
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workplan/redirect",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Redirected work plan",
        metadata={"direction": direction},
    )
    return {"status": "redirected", "direction": direction, "message": "Preference saved, plan generating in background"}


@router.get("/projects")
async def get_projects():
    """Get canonical project registry summaries."""
    from ..projects import get_project_summaries

    projects = get_project_summaries()
    return {"projects": projects, "count": len(projects)}


@router.get("/projects/stalled")
async def stalled_projects():
    """List stalled projects."""
    stalled = await list_stalled_project_records()
    return {"stalled": stalled, "count": len(stalled)}


@router.get("/projects/{project_id}")
async def get_project_detail(project_id: str):
    """Get a detailed canonical project definition."""
    from ..projects import get_project

    project = get_project(project_id)
    if not project:
        return JSONResponse(
            status_code=404,
            content={"error": f"Project '{project_id}' not found"},
        )
    return {"project": project}


async def list_stalled_project_records(*, limit: int | None = None, threshold_hours: float = 24) -> list[dict[str, Any]]:
    """Return stalled projects as operator-facing records."""
    from ..project_tracker import get_project_state, get_stalled_projects
    from ..projects import get_project

    stalled_ids = await get_stalled_projects(threshold_hours=threshold_hours)
    records: list[dict[str, Any]] = []
    for project_id in stalled_ids:
        state = await get_project_state(project_id)
        project = get_project(project_id)
        stalled_since = float(state.stalled_since or 0.0)
        records.append(
            {
                "id": project_id,
                "name": str((project or {}).get("name") or (project or {}).get("label") or project_id),
                "reason": f"No milestone activity for more than {int(threshold_hours)} hours.",
                "stalled_since": (
                    datetime.fromtimestamp(stalled_since, tz=timezone.utc).isoformat()
                    if stalled_since > 0
                    else ""
                ),
                "total_completed": int(state.total_completed or 0),
                "total_failed": int(state.total_failed or 0),
                "avg_quality": float(state.avg_quality or 0.0),
            }
        )
    records.sort(key=lambda item: str(item.get("stalled_since") or ""))
    return records[:limit] if limit is not None else records


def _collect_output_artifacts() -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for root, dirs, filenames in os.walk(OUTPUT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, OUTPUT_DIR)
            try:
                stat = os.stat(full_path)
            except OSError:
                continue
            files.append(
                {
                    "path": rel_path,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    files.sort(key=lambda item: float(item.get("modified") or 0.0), reverse=True)
    return files


async def list_output_artifacts(*, limit: int | None = None) -> list[dict[str, Any]]:
    files = _collect_output_artifacts()
    return files[:limit] if limit is not None else files


@router.get("/outputs")
async def list_outputs():
    """List files produced by agent tasks in the output directory."""
    files = await list_output_artifacts()
    return {"outputs": files, "count": len(files)}


@router.get("/outputs/{path:path}")
async def read_output(path: str):
    """Read the contents of a specific output file."""
    full_path = os.path.join("/output", path)

    real_path = os.path.realpath(full_path)
    if not real_path.startswith("/output/"):
        return JSONResponse(status_code=403, content={"error": "Path traversal blocked"})

    if not os.path.isfile(real_path):
        return JSONResponse(status_code=404, content={"error": f"File not found: {path}"})

    try:
        stat = os.stat(real_path)
        _, ext = os.path.splitext(path)
        if ext.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"):
            return {
                "path": path,
                "type": "binary",
                "size_bytes": stat.st_size,
                "extension": ext,
                "modified": stat.st_mtime,
            }
        with open(real_path, encoding="utf-8", errors="replace") as f:
            content = f.read(50000)
        return {
            "path": path,
            "type": "text",
            "content": content,
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
