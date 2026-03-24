"""Skill learning routes — CRUD, search, execution recording."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1", tags=["skills"])


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
async def create_skill(body: dict):
    """Add a new skill to the library."""
    from ..skill_learning import add_skill

    required = {"name", "description", "trigger_conditions", "steps"}
    if not required.issubset(body):
        raise HTTPException(status_code=422, detail=f"Required fields: {required}")
    skill_id = await add_skill(
        name=body["name"],
        description=body["description"],
        trigger_conditions=body["trigger_conditions"],
        steps=body["steps"],
        category=body.get("category", "general"),
        tags=body.get("tags"),
        created_by=body.get("created_by", "api"),
    )
    return {"skill_id": skill_id, "status": "created"}


@router.post("/skills/{skill_id}/execution")
async def record_skill_execution(skill_id: str, body: dict):
    """Record a skill execution outcome (updates success rate)."""
    from ..skill_learning import record_execution

    success = body.get("success", True)
    duration_ms = body.get("duration_ms", 0.0)
    context = body.get("context")
    ok = await record_execution(skill_id, success, float(duration_ms), context)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "recorded"}


@router.delete("/skills/{skill_id}")
async def remove_skill(skill_id: str):
    """Delete a skill from the library."""
    from ..skill_learning import delete_skill

    ok = await delete_skill(skill_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted"}
