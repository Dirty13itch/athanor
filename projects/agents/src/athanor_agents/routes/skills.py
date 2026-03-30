"""Skill learning routes â€” CRUD, search, execution recording."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["skills"])


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


@router.get("/skills")
async def list_skills(
    query: str = "",
    category: str | None = None,
    min_success_rate: float = 0.0,
    limit: int = 20,
):
    """Search the skill library."""
    from ..skill_learning import search_skills

    skills = await search_skills(query=query, category=category, min_success_rate=min_success_rate, limit=limit)
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@router.get("/skills/top")
async def top_skills(limit: int = 10):
    """Get top-performing skills by proven effectiveness."""
    from ..skill_learning import get_top_skills

    skills = await get_top_skills(limit)
    return {"skills": [s.to_dict() for s in skills]}


@router.get("/skills/stats")
async def skill_stats():
    """Get skill library statistics."""
    from ..skill_learning import get_stats as get_skill_stats

    return await get_skill_stats()


@router.get("/skills/{skill_id}")
async def get_skill_by_id(skill_id: str):
    """Get a specific skill by ID."""
    from ..skill_learning import get_skill

    skill = await get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@router.post("/skills")
async def create_skill(request: Request):
    """Add a new skill to the library."""
    from ..skill_learning import add_skill

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/skills",
        action_class="operator",
        default_reason="Created skill",
    )
    if denial:
        return denial

    required = {"name", "description", "trigger_conditions", "steps"}
    if not required.issubset(body):
        detail = f"Required fields: {required}"
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/skills",
            action_class="operator",
            decision="denied",
            status_code=422,
            action=action,
            detail=detail,
        )
        raise HTTPException(status_code=422, detail=detail)
    skill_id = await add_skill(
        name=body["name"],
        description=body["description"],
        trigger_conditions=body["trigger_conditions"],
        steps=body["steps"],
        category=body.get("category", "general"),
        tags=body.get("tags"),
        created_by=body.get("created_by", "api"),
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/skills",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Created skill {skill_id}",
        target=skill_id,
        metadata={"category": body.get("category", "general")},
    )
    return {"skill_id": skill_id, "status": "created"}


@router.post("/skills/{skill_id}/execution")
async def record_skill_execution(skill_id: str, request: Request):
    """Record a skill execution outcome (updates success rate)."""
    from ..skill_learning import record_execution

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/skills/{skill_id}/execution",
        action_class="operator",
        default_reason=f"Recorded skill execution {skill_id}",
    )
    if denial:
        return denial

    success = body.get("success", True)
    duration_ms = body.get("duration_ms", 0.0)
    context = body.get("context")
    ok = await record_execution(skill_id, success, float(duration_ms), context)
    if not ok:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/skills/{skill_id}/execution",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail="Skill not found",
            target=skill_id,
        )
        raise HTTPException(status_code=404, detail="Skill not found")
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/skills/{skill_id}/execution",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded execution for skill {skill_id}",
        target=skill_id,
        metadata={"success": bool(success), "duration_ms": float(duration_ms)},
    )
    return {"status": "recorded"}


@router.delete("/skills/{skill_id}")
async def remove_skill(skill_id: str, request: Request):
    """Delete a skill from the library."""
    from ..skill_learning import delete_skill

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/skills/{skill_id}",
        action_class="admin",
        default_reason=f"Deleted skill {skill_id}",
    )
    if denial:
        return denial

    ok = await delete_skill(skill_id)
    if not ok:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/skills/{skill_id}",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail="Skill not found",
            target=skill_id,
        )
        raise HTTPException(status_code=404, detail="Skill not found")
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/skills/{skill_id}",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Deleted skill {skill_id}",
        target=skill_id,
    )
    return {"status": "deleted"}
