"""Feedback Loop — ingests ratings and preferences to improve agent behavior.

When Shaun rates gallery images, approves/rejects tasks, or provides explicit
feedback, this module updates agent core memories so future work reflects
what he actually wants.

The feedback → memory → prompt cycle:
1. Shaun rates image 5 stars → feedback.py records the prompt as "exemplar"
2. Creative agent's core memory gets updated with the approved prompt patterns
3. Next creative task includes "Reference these approved styles: ..." in context
4. Output quality improves over time

Same pattern for task feedback, code review feedback, etc.
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

FEEDBACK_KEY = "athanor:feedback:gallery"
FEEDBACK_PROMPTS_KEY = "athanor:feedback:approved_prompts"
FEEDBACK_REJECTS_KEY = "athanor:feedback:rejected_prompts"


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def ingest_gallery_rating(
    image_id: str,
    rating: int,
    approved: bool,
    flagged: bool,
    notes: str,
    prompt: str,
    queen_name: str = "",
) -> dict:
    """Ingest a gallery rating and update creative-agent's core memory.

    Args:
        image_id: The gallery item identifier
        rating: 1-5 star rating
        approved: Whether the image was approved
        flagged: Whether it was flagged for refinement
        notes: Operator notes about what's good/bad
        prompt: The generation prompt that produced this image
        queen_name: Which queen this is for (if applicable)

    Returns:
        Dict with what was updated
    """
    try:
        r = await _get_redis()
    except Exception as e:
        logger.error("Feedback: Redis unavailable: %s", e)
        return {"image_id": image_id, "updates": [], "error": "redis_unavailable"}

    updates = []

    # Store the rating
    rating_data = {
        "image_id": image_id,
        "rating": rating,
        "approved": approved,
        "flagged": flagged,
        "notes": notes,
        "prompt": prompt,
        "queen_name": queen_name,
        "timestamp": time.time(),
    }
    try:
        await r.hset(FEEDBACK_KEY, image_id, json.dumps(rating_data))
    except Exception as e:
        logger.warning("Feedback: failed to store rating: %s", e)

    # If approved or 4-5 stars: this prompt is an exemplar
    if approved or rating >= 4:
        exemplar = {
            "prompt": prompt,
            "rating": rating,
            "queen": queen_name,
            "notes": notes,
            "timestamp": time.time(),
        }
        await r.rpush(FEEDBACK_PROMPTS_KEY, json.dumps(exemplar))
        # Keep only last 50 exemplars
        await r.ltrim(FEEDBACK_PROMPTS_KEY, -50, -1)
        updates.append("added_exemplar")

        # Update creative-agent core memory
        await _update_creative_memory("approved_styles", prompt, queen_name, notes)

    # If rejected or 1-2 stars: this prompt should be avoided
    if (not approved and not flagged and rating > 0) or rating <= 2:
        rejection = {
            "prompt": prompt,
            "rating": rating,
            "queen": queen_name,
            "notes": notes,
            "timestamp": time.time(),
        }
        await r.rpush(FEEDBACK_REJECTS_KEY, json.dumps(rejection))
        await r.ltrim(FEEDBACK_REJECTS_KEY, -30, -1)
        updates.append("added_rejection")

        await _update_creative_memory("rejected_styles", prompt, queen_name, notes)

    # If flagged with notes: specific refinement guidance
    if flagged and notes:
        await _update_creative_memory("refinement_notes", prompt, queen_name, notes)
        updates.append("added_refinement")

    logger.info(
        "Gallery feedback ingested: image=%s rating=%d approved=%s updates=%s",
        image_id, rating, approved, updates,
    )

    return {"image_id": image_id, "updates": updates}


async def _update_creative_memory(category: str, prompt: str, queen: str, notes: str):
    """Update creative-agent's core memory with feedback."""
    from .core_memory import get_core_memory, update_core_memory

    memory = await get_core_memory("creative-agent")
    prefs = memory.get("learned_preferences", {})

    if category not in prefs:
        prefs[category] = []

    # Add the new entry (keep last 20 per category)
    entry = {
        "queen": queen,
        "prompt_snippet": prompt[:200] if prompt else "",
        "notes": notes[:200] if notes else "",
        "timestamp": time.time(),
    }
    prefs[category].append(entry)
    prefs[category] = prefs[category][-20:]  # Keep last 20

    await update_core_memory("creative-agent", "learned_preferences", prefs)


async def get_approved_prompts(limit: int = 10) -> list[dict]:
    """Get the most recent approved prompt exemplars."""
    r = await _get_redis()
    raw = await r.lrange(FEEDBACK_PROMPTS_KEY, -limit, -1)
    return [json.loads(item) for item in raw]


async def get_rejected_prompts(limit: int = 10) -> list[dict]:
    """Get the most recent rejected prompt patterns."""
    r = await _get_redis()
    raw = await r.lrange(FEEDBACK_REJECTS_KEY, -limit, -1)
    return [json.loads(item) for item in raw]


async def get_feedback_summary() -> dict:
    """Get a summary of all gallery feedback for the creative agent's context."""
    try:
        r = await _get_redis()
    except Exception as e:
        logger.warning("Feedback summary: Redis unavailable: %s", e)
        return {"total_ratings": 0, "approved_count": 0, "rejected_count": 0,
                "approved_keywords": [], "rejected_keywords": []}

    try:
        approved = await r.lrange(FEEDBACK_PROMPTS_KEY, 0, -1)
        rejected = await r.lrange(FEEDBACK_REJECTS_KEY, 0, -1)
        total_ratings = await r.hlen(FEEDBACK_KEY)
    except Exception as e:
        logger.warning("Feedback summary: Redis read failed: %s", e)
        return {"total_ratings": 0, "approved_count": 0, "rejected_count": 0,
                "approved_keywords": [], "rejected_keywords": []}

    # Extract patterns from approved prompts
    approved_keywords = set()
    rejected_keywords = set()

    for item in approved:
        data = json.loads(item)
        if data.get("notes"):
            for word in data["notes"].lower().split():
                if len(word) > 3:
                    approved_keywords.add(word)

    for item in rejected:
        data = json.loads(item)
        if data.get("notes"):
            for word in data["notes"].lower().split():
                if len(word) > 3:
                    rejected_keywords.add(word)

    return {
        "total_ratings": total_ratings,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "approved_keywords": list(approved_keywords)[:20],
        "rejected_keywords": list(rejected_keywords)[:20],
    }


async def format_feedback_context() -> str:
    """Format feedback data as context for the creative agent's prompts."""
    summary = await get_feedback_summary()

    if summary["total_ratings"] == 0:
        return ""

    lines = [
        f"[OWNER FEEDBACK: {summary['total_ratings']} images rated, "
        f"{summary['approved_count']} approved, {summary['rejected_count']} rejected]",
    ]

    # Get recent exemplars
    exemplars = await get_approved_prompts(5)
    if exemplars:
        lines.append("\nApproved prompt patterns (REPLICATE THESE):")
        for ex in exemplars:
            queen = ex.get("queen", "")
            notes = ex.get("notes", "")
            snippet = ex.get("prompt", "")[:100]
            lines.append(f"  - {queen}: {snippet}{'...' if len(ex.get('prompt','')) > 100 else ''}")
            if notes:
                lines.append(f"    Why good: {notes}")

    # Get recent rejections
    rejections = await get_rejected_prompts(5)
    if rejections:
        lines.append("\nRejected patterns (AVOID THESE):")
        for rej in rejections:
            queen = rej.get("queen", "")
            notes = rej.get("notes", "")
            lines.append(f"  - {queen}: {notes or 'no notes'}")

    return "\n".join(lines)
