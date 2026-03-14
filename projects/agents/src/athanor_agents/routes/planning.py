"""Work planner, projects, and output file routes."""

import asyncio
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["planning"])


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

    body = await request.json()
    focus = body.get("focus", "")

    plan = await generate_work_plan(focus=focus)
    return plan


@router.post("/workplan/redirect")
async def redirect_workplan(request: Request):
    """Steer the work planner with a preference or focus direction."""
    from ..activity import store_preference
    from ..workplanner import generate_work_plan

    body = await request.json()
    direction = body.get("direction", "")

    if not direction:
        return JSONResponse(status_code=400, content={"error": "direction is required"})

    await store_preference(
        agent="global",
        signal_type="work_direction",
        content=direction,
        category="work_planning",
    )

    asyncio.create_task(generate_work_plan(focus=direction))
    return {"status": "redirected", "direction": direction, "message": "Preference saved, plan generating in background"}


@router.get("/projects")
async def get_projects():
    """Get canonical project registry summaries."""
    from ..projects import get_project_summaries

    projects = get_project_summaries()
    return {"projects": projects, "count": len(projects)}


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


@router.get("/outputs")
async def list_outputs():
    """List files produced by agent tasks in the output directory."""
    output_dir = "/output"
    files = []

    for root, dirs, filenames in os.walk(output_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, output_dir)
            try:
                stat = os.stat(full_path)
                files.append({
                    "path": rel_path,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except OSError:
                continue

    files.sort(key=lambda f: f["modified"], reverse=True)
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
