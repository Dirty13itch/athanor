"""Feedback API routes — ingest gallery ratings and preferences."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


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
async def submit_gallery_rating(body: GalleryRatingRequest, request: Request):
    """Submit a gallery image rating. Updates creative-agent's core memory."""
    from ..feedback import ingest_gallery_rating

    result = await ingest_gallery_rating(
        image_id=body.image_id,
        rating=body.rating,
        approved=body.approved,
        flagged=body.flagged,
        notes=body.notes,
        prompt=body.prompt,
        queen_name=body.queen_name,
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
