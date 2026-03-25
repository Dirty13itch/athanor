"""Core memory routes — REST API for reading and updating agent persona blocks."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["core-memory"])


@router.get("/core-memory")
async def get_all_memories():
    """Get core memories for all agents."""
    from ..core_memory import get_all_core_memories

    memories = await get_all_core_memories()
    return {"memories": memories, "count": len(memories)}


@router.get("/core-memory/{agent}")
async def get_agent_memory(agent: str):
    """Get core memory for a single agent."""
    from ..core_memory import get_core_memory

    memory = await get_core_memory(agent)
    if not memory or not memory.get("bio"):
        return JSONResponse(
            status_code=404,
            content={"error": f"No core memory found for '{agent}'"},
        )
    return {"agent": agent, "memory": memory}


@router.put("/core-memory/{agent}")
async def update_agent_memory(agent: str, request: Request):
    """Update a field in an agent's core memory.

    Body: {"field": "learned_preferences", "value": {"key": "value"}}
    """
    from ..core_memory import update_core_memory

    body = await request.json()
    field = body.get("field", "")
    value = body.get("value")

    if not field:
        return JSONResponse(
            status_code=400,
            content={"error": "field is required"},
        )
    if value is None:
        return JSONResponse(
            status_code=400,
            content={"error": "value is required"},
        )

    try:
        updated = await update_core_memory(agent, field, value)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return {"agent": agent, "memory": updated, "updated_field": field}
