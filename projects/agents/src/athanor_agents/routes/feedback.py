"""Feedback API routes â€” ingest gallery ratings and preferences."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


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


class GalleryRatingRequest(BaseModel):
    image_id: str
    rating: int = Field(ge=0, le=5)
    approved: bool = False
    flagged: bool = False
    notes: str = ""
    prompt: str = ""
    queen_name: str = ""


class FeedbackResponse(BaseModel):
    status: str
    updates: list[str] = []


@router.post("/gallery", response_model=FeedbackResponse)
async def submit_gallery_rating(request: Request):
    """Submit a gallery image rating. Updates creative-agent's core memory."""
    from ..feedback import ingest_gallery_rating

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/feedback/gallery",
        action_class="operator",
        default_reason="Submitted gallery rating",
    )
    if denial:
        return denial

    try:
        rating = GalleryRatingRequest.model_validate(body)
    except ValidationError as exc:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/feedback/gallery",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="Invalid gallery rating payload",
            metadata={"issues": exc.errors()},
        )
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid gallery rating payload", "issues": exc.errors()},
        )

    result = await ingest_gallery_rating(
        image_id=rating.image_id,
        rating=rating.rating,
        approved=rating.approved,
        flagged=rating.flagged,
        notes=rating.notes,
        prompt=rating.prompt,
        queen_name=rating.queen_name,
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/feedback/gallery",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Submitted gallery rating for {rating.image_id}",
        target=rating.image_id,
        metadata={
            "rating": rating.rating,
            "approved": rating.approved,
            "flagged": rating.flagged,
            "queen_name": rating.queen_name,
        },
    )
    return FeedbackResponse(status="ok", updates=result.get("updates", []))


@router.get("/summary")
async def get_feedback_summary():
    """Get feedback summary for the operator dashboard."""
    from ..feedback import get_feedback_summary as _get_summary
    return await _get_summary()


@router.get("/approved-prompts")
async def get_approved_prompts(limit: int = 10):
    """Get recently approved prompt exemplars."""
    from ..feedback import get_approved_prompts as _get_approved
    return {"prompts": await _get_approved(limit)}


@router.get("/rejected-prompts")
async def get_rejected_prompts(limit: int = 10):
    """Get recently rejected prompt patterns."""
    from ..feedback import get_rejected_prompts as _get_rejected
    return {"prompts": await _get_rejected(limit)}
