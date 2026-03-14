"""Convention library routes — CRUD, confirm/reject."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["conventions"])


@router.get("/conventions")
async def get_conventions(status: str = "confirmed", agent: str = ""):
    """Get conventions filtered by status and optionally by agent."""
    from ..conventions import get_conventions as _get_conventions

    conventions = await _get_conventions(status=status, agent=agent or None)
    return {
        "conventions": [c.to_dict() for c in conventions],
        "count": len(conventions),
        "status": status,
    }


@router.post("/conventions")
async def propose_convention_endpoint(request: Request):
    """Propose a new convention manually."""
    from ..conventions import propose_convention

    body = await request.json()
    conv_type = body.get("type", "behavior")
    agent = body.get("agent", "global")
    description = body.get("description", "")
    rule = body.get("rule", "")
    source = body.get("source", "manual")

    if not description or not rule:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'description' and 'rule' are required"},
        )

    conv = await propose_convention(
        convention_type=conv_type,
        agent=agent,
        description=description,
        rule=rule,
        source=source,
    )
    return {"status": conv.status, "convention": conv.to_dict()}


@router.post("/conventions/{convention_id}/confirm")
async def confirm_convention_endpoint(convention_id: str):
    """Confirm a proposed convention."""
    from ..conventions import confirm_convention

    conv = await confirm_convention(convention_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    return {"status": "confirmed", "convention": conv.to_dict()}


@router.post("/conventions/{convention_id}/reject")
async def reject_convention_endpoint(convention_id: str):
    """Reject a proposed convention."""
    from ..conventions import reject_convention

    conv = await reject_convention(convention_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    return {"status": "rejected", "convention": conv.to_dict()}
