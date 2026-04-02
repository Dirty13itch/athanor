"""Judge-plane and review visibility routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["review"])


@router.get("/review/judges")
async def get_judge_plane(limit: int = 12):
    """Return an honest judge-plane snapshot for operator surfaces.

    The live runtime does not yet persist dedicated judge verdict lineage. Until
    that lands, the route stays truthful by projecting pending review pressure
    from the canonical task-engine approval queue while leaving verdict history
    empty instead of 404ing.
    """

    from ..tasks import get_task_stats

    _ = max(min(int(limit), 50), 0)
    stats = await get_task_stats()
    pending_review_queue = int(stats.get("pending_approval", 0) or 0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "limited",
        "role_id": "judge_verifier",
        "label": "Judge / verifier",
        "champion": "judge-local-v1",
        "challengers": ["critic-local-v1"],
        "workload_classes": [
            "judge_verification",
            "promotion_gating",
            "regression_scoring",
        ],
        "summary": {
            "recent_verdicts": 0,
            "accept_count": 0,
            "reject_count": 0,
            "review_required": pending_review_queue,
            "acceptance_rate": 0.0,
            "pending_review_queue": pending_review_queue,
        },
        "guardrails": [
            "Judge lanes score and gate; they do not execute production actions.",
            "Pending review pressure is projected from canonical task approvals until dedicated verdict lineage is stored.",
            "Protected workloads stay local when policy is refusal-sensitive or sovereign-only.",
        ],
        "recent_verdicts": [],
    }
