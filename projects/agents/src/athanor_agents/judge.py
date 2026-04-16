from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_run(run: dict[str, Any]) -> dict[str, Any]:
    status = str(run.get("status") or "pending")
    failure_reason = run.get("failure_reason")
    provider = str(run.get("provider") or "athanor_local")
    policy_class = str(run.get("policy_class") or "")
    artifact_refs = list(run.get("artifact_refs") or [])

    if status == "failed":
        score = 0.12
        verdict = "reject"
        rationale = failure_reason or "Execution failed before a usable result was recorded."
    elif status in {"pending", "running"}:
        score = 0.55
        verdict = "review_required"
        rationale = "Execution is still in progress or waiting for a final outcome."
    else:
        score = 0.82
        verdict = "accept"
        rationale = "Execution completed with a durable run record."
        if provider == "athanor_local" and policy_class in {"sovereign_only", "refusal_sensitive"}:
            score += 0.08
            rationale = "Execution completed on the sovereign local lane for protected work."
        if not artifact_refs:
            score -= 0.08
            rationale = "Execution completed but did not publish any artifact references."

    score = max(0.0, min(round(score, 2), 1.0))
    return {
        "run_id": run.get("id"),
        "agent": run.get("agent"),
        "provider": provider,
        "policy_class": policy_class or None,
        "score": score,
        "verdict": verdict,
        "rationale": rationale,
        "deep_link": "/tasks" if run.get("task_id") else "/agents",
    }


async def build_judge_plane_snapshot(limit: int = 12) -> dict[str, Any]:
    from .backbone import build_execution_run_records
    from .model_governance import get_model_role_registry
    from .tasks import get_task_stats

    role_registry = get_model_role_registry()
    judge_role = next(
        (role for role in role_registry.get("roles", []) if role.get("id") == "judge_verifier"),
        {
            "id": "judge_verifier",
            "label": "Judge / verifier",
            "champion": "judge-local-v1",
            "challengers": ["critic-local-v1"],
            "status": "implemented_not_live",
            "workload_classes": ["judge_verification"],
        },
    )

    runs = await build_execution_run_records(limit=max(limit * 2, 20))
    verdicts = [_score_run(run) for run in runs[:limit]]
    stats = await get_task_stats()
    pending_reviews = int(stats.get("pending_approval", 0) or 0)

    accept_count = sum(1 for verdict in verdicts if verdict["verdict"] == "accept")
    reject_count = sum(1 for verdict in verdicts if verdict["verdict"] == "reject")
    review_required = sum(1 for verdict in verdicts if verdict["verdict"] == "review_required")
    acceptance_rate = round(accept_count / len(verdicts), 2) if verdicts else 0.0

    return {
        "generated_at": _now_iso(),
        "status": "live",
        "role_id": judge_role.get("id", "judge_verifier"),
        "label": judge_role.get("label", "Judge / verifier"),
        "champion": judge_role.get("champion", "judge-local-v1"),
        "challengers": list(judge_role.get("challengers", [])),
        "workload_classes": list(judge_role.get("workload_classes", [])),
        "summary": {
            "recent_verdicts": len(verdicts),
            "accept_count": accept_count,
            "reject_count": reject_count,
            "review_required": review_required,
            "acceptance_rate": acceptance_rate,
            "pending_review_queue": pending_reviews,
        },
        "guardrails": [
            "Judge lanes score and gate; they do not execute production actions.",
            "Protected workloads keep review local when policy is refusal-sensitive or sovereign-only.",
            "Failed runs are not auto-accepted into promotion or automation history.",
        ],
        "recent_verdicts": verdicts,
    }
