"""Model governance endpoints - extracted from backbone server.py.

These endpoints handle model promotions, retirements, and the proving ground.
Extracted from the backbone branch and reconciled into main as a router module.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(tags=["model-governance"])
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _drain_task_result(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        return
    except Exception as exc:  # pragma: no cover - defensive cleanup
        logger.debug("Model-governance background task finished after cancellation: %s", exc)


async def _await_snapshot(
    label: str,
    coroutine: Any,
    *,
    fallback_factory,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    task = asyncio.create_task(coroutine)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout_seconds)
        if task not in done:
            task.cancel()
            task.add_done_callback(_drain_task_result)
            raise TimeoutError(f"{label} timed out after {timeout_seconds:.1f}s")
        result = task.result()
    except Exception as exc:
        logger.warning("Model-governance route %s unavailable; using degraded snapshot: %s", label, exc)
        return fallback_factory(str(exc))
    return result if isinstance(result, dict) else fallback_factory(f"{label} returned invalid payload")


def _degraded_proving_ground_snapshot(detail: str) -> dict[str, Any]:
    from ..model_governance import (
        build_model_governance_snapshot,
        get_eval_corpus_registry,
        get_experiment_ledger_policy,
        get_model_role_registry,
    )

    baseline = build_model_governance_snapshot()
    registry = dict(baseline.get("proving_ground") or {})
    eval_corpus_registry = get_eval_corpus_registry()
    experiment_policy = get_experiment_ledger_policy()
    role_registry = get_model_role_registry()

    return {
        "generated_at": _now_iso(),
        "version": str(registry.get("version") or "unknown"),
        "status": "degraded",
        "purpose": str(registry.get("purpose") or ""),
        "evaluation_dimensions": list(registry.get("evaluation_dimensions", [])),
        "corpora": list(registry.get("corpora", [])),
        "pipeline_phases": list(registry.get("pipeline_phases", [])),
        "promotion_path": list(registry.get("promotion_path", [])),
        "rollback_rule": str(registry.get("rollback_rule") or ""),
        "latest_run": None,
        "recent_results": [],
        "corpus_registry_version": str(eval_corpus_registry.get("version") or "unknown"),
        "governed_corpora": list(eval_corpus_registry.get("corpora", [])),
        "experiment_ledger": {
            "version": str(experiment_policy.get("version") or "unknown"),
            "status": "degraded",
            "required_fields": list(experiment_policy.get("required_fields", [])),
            "retention": str(experiment_policy.get("retention") or "unknown"),
            "promotion_linkage": str(experiment_policy.get("promotion_linkage") or ""),
            "evidence_count": 0,
        },
        "recent_experiments": [],
        "improvement_summary": {
            "total_proposals": 0,
            "pending": 0,
            "validated": 0,
            "deployed": 0,
            "failed": 0,
            "archive_entries": 0,
            "benchmark_results": 0,
            "latest_baseline": {},
            "last_cycle": None,
            "detail": detail[:160],
        },
        "lane_coverage": [
            {
                "role_id": str(role.get("id") or "role"),
                "label": str(role.get("label") or "Role"),
                "plane": str(role.get("plane") or "unknown"),
                "status": str(role.get("status") or "configured"),
                "champion": str(role.get("champion") or "unknown"),
                "challenger_count": len(role.get("challengers", [])),
                "workload_count": len(role.get("workload_classes", [])),
            }
            for role in role_registry.get("roles", [])
            if isinstance(role, dict)
        ],
        "promotion_controls": dict(baseline.get("promotion_controls") or {}),
    }


async def _load_candidate_action(request: Request, *, default_reason: str):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}
    return build_operator_action(body, default_reason=default_reason)


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


@router.get("/v1/models/governance")
async def model_governance():
    from ..model_governance import build_live_model_governance_snapshot

    return await build_live_model_governance_snapshot()


@router.get("/v1/models/governance/promotions")
async def model_governance_promotions(limit: int = 12):
    from ..promotion_control import build_promotion_controls_snapshot

    return await build_promotion_controls_snapshot(limit=limit)


@router.post("/v1/models/governance/promotions")
async def stage_model_governance_promotion(request: Request):
    from ..promotion_control import stage_promotion_candidate

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/models/governance/promotions",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    role_id = body.get("role_id", "") if isinstance(body, dict) else ""
    candidate = body.get("candidate", "") if isinstance(body, dict) else ""
    if not role_id or not candidate:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/models/governance/promotions",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="Fields 'role_id' and 'candidate' are required",
        )
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'role_id' and 'candidate' are required"},
        )

    record = await stage_promotion_candidate(
        role_id=role_id,
        candidate=candidate,
        target_tier=body.get("target_tier", "canary") if isinstance(body, dict) else "canary",
        actor=action.actor,
        reason=action.reason,
        source=body.get("source", "manual") if isinstance(body, dict) else "manual",
        asset_class=body.get("asset_class", "models") if isinstance(body, dict) else "models",
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/models/governance/promotions",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Staged promotion {candidate} for role {role_id}",
        target=role_id,
        metadata={"candidate": candidate, "target_tier": body.get("target_tier", "canary")},
    )
    return {"promotion": record}


@router.post("/v1/models/governance/promotions/{promotion_id}/{action}")
async def transition_model_governance_promotion(promotion_id: str, action: str, request: Request):
    from ..promotion_control import transition_promotion_candidate

    if action not in {"advance", "hold", "rollback"}:
        candidate = await _load_candidate_action(request, default_reason="")
        await emit_operator_audit_event(
            service="agent-server",
            route=f"/v1/models/governance/promotions/{promotion_id}/{action}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=candidate,
            detail=f"Unsupported action '{action}'",
            target=promotion_id,
        )
        return JSONResponse(status_code=400, content={"error": f"Unsupported action '{action}'"})

    body, operator_action, denial = await _load_operator_body(
        request,
        route=f"/v1/models/governance/promotions/{promotion_id}/{action}",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    record = await transition_promotion_candidate(
        promotion_id,
        action=action,
        actor=operator_action.actor,
        reason=operator_action.reason,
    )
    if record is None:
        await emit_operator_audit_event(
            service="agent-server",
            route=f"/v1/models/governance/promotions/{promotion_id}/{action}",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=operator_action,
            detail=f"Promotion '{promotion_id}' not found",
            target=promotion_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Promotion '{promotion_id}' not found"})
    await emit_operator_audit_event(
        service="agent-server",
        route=f"/v1/models/governance/promotions/{promotion_id}/{action}",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=operator_action,
        detail=f"Applied promotion action={action} for {promotion_id}",
        target=promotion_id,
    )
    return {"promotion": record}


@router.get("/v1/models/governance/retirements")
async def model_governance_retirements(limit: int = 12):
    from ..retirement_control import build_retirement_controls_snapshot

    return await build_retirement_controls_snapshot(limit=limit)


@router.post("/v1/models/governance/retirements")
async def stage_model_governance_retirement(request: Request):
    from ..retirement_control import stage_retirement_candidate

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/models/governance/retirements",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    asset_class = body.get("asset_class", "") if isinstance(body, dict) else ""
    asset_id = body.get("asset_id", "") if isinstance(body, dict) else ""
    label = body.get("label", asset_id) if isinstance(body, dict) else asset_id
    if not asset_class or not asset_id:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/models/governance/retirements",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="Fields 'asset_class' and 'asset_id' are required",
        )
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'asset_class' and 'asset_id' are required"},
        )

    record = await stage_retirement_candidate(
        asset_class=asset_class,
        asset_id=asset_id,
        label=label,
        target_stage=body.get("target_stage", "retired_reference_only")
        if isinstance(body, dict)
        else "retired_reference_only",
        actor=action.actor,
        reason=action.reason,
        source=body.get("source", "manual") if isinstance(body, dict) else "manual",
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/models/governance/retirements",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Staged retirement {asset_id}",
        target=asset_id,
        metadata={"asset_class": asset_class, "target_stage": body.get("target_stage", "retired_reference_only")},
    )
    return {"retirement": record}


@router.post("/v1/models/governance/retirements/{retirement_id}/{action}")
async def transition_model_governance_retirement(retirement_id: str, action: str, request: Request):
    from ..retirement_control import transition_retirement_candidate

    if action not in {"advance", "hold", "rollback"}:
        candidate = await _load_candidate_action(request, default_reason="")
        await emit_operator_audit_event(
            service="agent-server",
            route=f"/v1/models/governance/retirements/{retirement_id}/{action}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=candidate,
            detail=f"Unsupported action '{action}'",
            target=retirement_id,
        )
        return JSONResponse(status_code=400, content={"error": f"Unsupported action '{action}'"})

    body, operator_action, denial = await _load_operator_body(
        request,
        route=f"/v1/models/governance/retirements/{retirement_id}/{action}",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    record = await transition_retirement_candidate(
        retirement_id,
        action=action,
        actor=operator_action.actor,
        reason=operator_action.reason,
    )
    if record is None:
        await emit_operator_audit_event(
            service="agent-server",
            route=f"/v1/models/governance/retirements/{retirement_id}/{action}",
            action_class="admin",
            decision="denied",
            status_code=404,
            action=operator_action,
            detail=f"Retirement '{retirement_id}' not found",
            target=retirement_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Retirement '{retirement_id}' not found"})
    await emit_operator_audit_event(
        service="agent-server",
        route=f"/v1/models/governance/retirements/{retirement_id}/{action}",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=operator_action,
        detail=f"Applied retirement action={action} for {retirement_id}",
        target=retirement_id,
    )
    return {"retirement": record}


@router.get("/v1/models/proving-ground")
async def model_proving_ground(limit: int = 12):
    from ..proving_ground import build_proving_ground_snapshot

    return await _await_snapshot(
        "proving_ground",
        build_proving_ground_snapshot(limit=limit),
        fallback_factory=_degraded_proving_ground_snapshot,
    )


@router.post("/v1/models/proving-ground/run")
async def run_model_proving_ground(request: Request):
    from ..proving_ground import run_proving_ground

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/models/proving-ground/run",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    limit = int(body.get("limit", 12)) if isinstance(body, dict) else 12
    result = await run_proving_ground(limit=limit)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/models/proving-ground/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Ran proving ground limit={limit}",
        metadata={"limit": limit},
    )
    return result
