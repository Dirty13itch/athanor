"""Governor API routes — matches dashboard proxy expectations."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["governor"])
logger = logging.getLogger(__name__)
GOVERNOR_SNAPSHOT_TIMEOUT_SECONDS = 8.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _titleize(value: str) -> str:
    return value.replace("_", " ").strip().title() if value else "Unknown"


def _drain_task_result(task: asyncio.Task[Any]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        return
    except Exception as exc:  # pragma: no cover - defensive cleanup
        logger.debug("Governor background task finished after cancellation: %s", exc)


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
        logger.warning("Governor route %s unavailable; using degraded snapshot: %s", label, exc)
        return await fallback_factory(str(exc))
    return result if isinstance(result, dict) else await fallback_factory(f"{label} returned invalid payload")


async def _degraded_governor_snapshot(detail: str) -> dict[str, Any]:
    from ..command_hierarchy import CONTROL_STACK
    from ..governor import get_governor_state
    from ..governor_backbone import LANE_DEFINITIONS, _release_tiers
    from ..model_governance import get_command_rights_registry

    try:
        state = await get_governor_state()
    except Exception as exc:
        logger.warning("Governor degraded snapshot could not read live state; using static fallback: %s", exc)
        state = {
            "global_mode": "active",
            "degraded_mode": "degraded",
            "reason": detail,
            "updated_at": None,
            "updated_by": "system",
            "operator_presence": "at_desk",
            "presence_mode": "auto",
            "presence_updated_at": None,
            "presence_updated_by": "system",
            "release_tier": "standard",
            "tier_updated_at": None,
            "tier_updated_by": "system",
            "paused_lanes": [],
        }
    paused = {str(item) for item in state.get("paused_lanes", [])}
    global_paused = str(state.get("global_mode") or "") == "paused"

    configured_state = str(state.get("operator_presence") or "at_desk")
    signal_state = str(state.get("presence_signal_state") or "").strip() or None
    effective_state = signal_state or configured_state or "at_desk"

    return {
        "generated_at": _now_iso(),
        "status": "degraded",
        "global_mode": str(state.get("global_mode") or "active"),
        "degraded_mode": str(state.get("degraded_mode") or "degraded"),
        "reason": str(state.get("reason") or ""),
        "updated_at": state.get("updated_at"),
        "updated_by": str(state.get("updated_by") or "system"),
        "lanes": [
            {
                "id": str(lane.get("id") or "lane"),
                "label": str(lane.get("label") or _titleize(str(lane.get("id") or "lane"))),
                "description": str(lane.get("description") or ""),
                "paused": global_paused or str(lane.get("id") or "") in paused,
                "status": "paused" if global_paused or str(lane.get("id") or "") in paused else "active",
            }
            for lane in LANE_DEFINITIONS
        ],
        "capacity": {
            "generated_at": _now_iso(),
            "posture": "degraded",
            "queue": {
                "posture": "degraded",
                "pending": 0,
                "running": 0,
                "max_concurrent": 0,
                "failed": 0,
            },
            "workspace": {
                "broadcast_items": 0,
                "capacity": 0,
                "utilization": 0.0,
            },
            "scheduler": {
                "running": False,
                "enabled_count": 0,
            },
            "provider_reserve": {
                "posture": "degraded",
                "constrained_count": 0,
            },
            "active_time_windows": [],
            "nodes": [],
            "recommendations": [f"Live governor capacity snapshot degraded: {detail[:160]}"],
        },
        "presence": {
            "state": effective_state,
            "label": _titleize(effective_state),
            "automation_posture": "degraded bounded autonomy",
            "notification_posture": "full detail",
            "approval_posture": "manual confirmation preferred",
            "updated_at": state.get("presence_updated_at") or state.get("updated_at"),
            "updated_by": str(state.get("presence_updated_by") or state.get("updated_by") or "system"),
            "mode": str(state.get("presence_mode") or "auto"),
            "configured_state": configured_state,
            "configured_label": _titleize(configured_state),
            "signal_state": signal_state,
            "signal_source": str(state.get("presence_signal_source") or "") or None,
            "signal_updated_at": state.get("presence_signal_updated_at"),
            "signal_updated_by": str(
                state.get("presence_signal_updated_by") or state.get("updated_by") or "system"
            ),
            "signal_fresh": False,
            "signal_age_seconds": None,
            "effective_reason": str(state.get("presence_signal_reason") or state.get("presence_reason") or detail),
        },
        "release_tier": {
            "state": str(state.get("release_tier") or "standard"),
            "available_tiers": [str(item) for item in _release_tiers()],
            "status": "degraded",
            "updated_at": state.get("tier_updated_at") or state.get("updated_at"),
            "updated_by": str(state.get("tier_updated_by") or state.get("updated_by") or "system"),
        },
        "command_rights_version": str(get_command_rights_registry().get("version") or "unknown"),
        "control_stack": [
            {
                "id": str(item.get("id") or "control"),
                "label": str(item.get("label") or _titleize(str(item.get("id") or "control"))),
                "status": (
                    "degraded"
                    if str(item.get("id") or "") == "capacity-governor"
                    else str(item.get("status") or "configured")
                ),
            }
            for item in CONTROL_STACK
        ],
    }


async def _degraded_operations_snapshot(detail: str) -> dict[str, Any]:
    from ..model_governance import (
        get_autonomy_activation_registry,
        get_backup_restore_readiness,
        get_current_autonomy_phase,
        get_data_lifecycle_registry,
        get_deprecation_retirement_policy,
        get_economic_governance_registry,
        get_operator_runbooks_registry,
        get_release_ritual_registry,
        get_tool_permission_registry,
        get_unmet_autonomy_prerequisites,
    )

    backup_restore = get_backup_restore_readiness()
    release_ritual = get_release_ritual_registry()
    retirement_policy = get_deprecation_retirement_policy()
    economic = get_economic_governance_registry()
    lifecycle = get_data_lifecycle_registry()
    runbooks = get_operator_runbooks_registry()
    autonomy = get_autonomy_activation_registry()
    tool_permissions = get_tool_permission_registry()
    activation, current_phase = get_current_autonomy_phase(autonomy)
    current_phase_id = str(activation.get("current_phase_id") or "").strip() or None
    unmet = get_unmet_autonomy_prerequisites(autonomy, phase_id=current_phase_id)

    runbook_items: list[dict[str, Any]] = []
    for item in runbooks.get("runbooks", []):
        if isinstance(item, dict):
            runbook_items.append(
                {
                    "id": str(item.get("id") or str(item.get("label") or "runbook").replace(" ", "-").lower()),
                    "label": str(item.get("label") or _titleize(str(item.get("id") or "runbook"))),
                    "description": str(item.get("description") or "") or None,
                    "cadence": str(item.get("cadence") or "") or None,
                    "related_surface": str(item.get("related_surface") or "") or None,
                    "support_status": "degraded",
                    "evidence_flow_ids": list(item.get("evidence_flow_ids") or []),
                }
            )
        elif str(item).strip():
            value = str(item).strip()
            runbook_items.append(
                {
                    "id": value.replace(" ", "-").lower(),
                    "label": _titleize(value),
                    "description": None,
                    "cadence": None,
                    "related_surface": None,
                    "support_status": "degraded",
                    "evidence_flow_ids": [],
                }
            )

    return {
        "generated_at": _now_iso(),
        "status": "degraded",
        "runbooks": {
            "status": "degraded",
            "items": runbook_items,
        },
        "backup_restore": {
            "status": "degraded",
            "drill_mode": str(backup_restore.get("drill_mode") or "registry_only"),
            "last_drill_at": None,
            "last_outcome": None,
            "verified_store_count": 0,
            "store_count": len(list(backup_restore.get("critical_stores", []))),
            "critical_stores": [
                {
                    "id": str(item.get("id") or "store"),
                    "label": str(item.get("label") or _titleize(str(item.get("id") or "store"))),
                    "drill_status": str(item.get("drill_status") or item.get("restore_status") or "configured"),
                    "cadence": str(item.get("cadence") or "") or None,
                    "restore_order": item.get("restore_order") or item.get("recovery_order"),
                    "verified": False,
                    "probe_status": None,
                    "probe_summary": None,
                    "last_drill_at": None,
                    "last_outcome": None,
                    "artifacts": [],
                }
                for item in backup_restore.get("critical_stores", [])
                if isinstance(item, dict)
            ],
        },
        "release_ritual": {
            "status": "degraded",
            "tiers": list(release_ritual.get("tiers", [])),
            "ritual": list(release_ritual.get("ritual", [])),
            "last_rehearsal_at": None,
            "last_outcome": None,
            "rehearsal_status": "degraded",
            "active_promotion_count": 0,
        },
        "deprecation_retirement": {
            "status": "degraded",
            "asset_classes": list(retirement_policy.get("asset_classes", [])),
            "stages": list(retirement_policy.get("stages", [])),
            "rule": str(retirement_policy.get("rule") or ""),
            "recent_retirement_count": 0,
            "active_retirement_count": 0,
            "last_rehearsal_at": None,
            "last_outcome": None,
            "recent_retirements": [],
        },
        "economic_governance": {
            "status": "degraded",
            "premium_reserve_lanes": list(economic.get("premium_reserve_lanes", [])),
            "automatic_spend_lanes": list(economic.get("automatic_spend_lanes", [])),
            "approval_required_lanes": list(economic.get("approval_required_lanes", [])),
            "downgrade_order": list(economic.get("downgrade_order", [])),
            "provider_count": int(economic.get("provider_count") or 0),
            "recent_lease_count": 0,
            "constrained_count": 0,
            "last_verified_at": None,
            "last_outcome": None,
        },
        "data_lifecycle": {
            "status": "degraded",
            "classes": list(lifecycle.get("classes", [])),
            "class_count": len(list(lifecycle.get("classes", []))),
            "run_count": 0,
            "eval_artifact_count": 0,
            "last_verified_at": None,
            "last_outcome": None,
        },
        "tool_permissions": {
            "status": "degraded",
            "default_mode": str(tool_permissions.get("default_mode") or "governor_mediated"),
            "subject_count": 0,
            "enforced_subject_count": 0,
            "denied_action_count": 0,
            "last_verified_at": None,
            "last_outcome": None,
            "subjects": [],
        },
        "autonomy_activation": {
            "status": "degraded",
            "activation_state": str(autonomy.get("activation_state") or "unknown"),
            "current_phase_id": current_phase_id,
            "current_phase_status": str(current_phase.get("status") or "unknown"),
            "current_phase_scope": str(current_phase.get("scope") or "") or None,
            "next_phase_id": None,
            "next_phase_status": None,
            "next_phase_scope": None,
            "next_phase_blocker_count": len(unmet),
            "next_phase_blocker_ids": [
                str(item.get("id") or "").strip()
                for item in unmet
                if str(item.get("id") or "").strip()
            ],
            "broad_autonomy_enabled": bool(autonomy.get("broad_autonomy_enabled")),
            "runtime_mutations_approval_gated": bool(autonomy.get("runtime_mutations_approval_gated", True)),
            "enabled_agents": [str(item) for item in current_phase.get("enabled_agents", []) if str(item).strip()],
            "allowed_workload_classes": [
                str(item) for item in current_phase.get("allowed_workload_classes", []) if str(item).strip()
            ],
            "blocked_workload_classes": [
                str(item) for item in current_phase.get("blocked_workload_classes", []) if str(item).strip()
            ],
        },
        "synthetic_operator_tests": {
            "status": "degraded",
            "last_outcome": "not_run",
            "last_run_at": None,
            "flow_count": 0,
            "flows": [],
        },
        "detail": detail[:200],
    }


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


@router.get("/governor")
async def governor_snapshot():
    """Full governor snapshot matching governorSnapshotSchema."""
    from ..governor import build_governor_snapshot

    return await _await_snapshot(
        "governor_snapshot",
        build_governor_snapshot(),
        fallback_factory=_degraded_governor_snapshot,
        timeout_seconds=GOVERNOR_SNAPSHOT_TIMEOUT_SECONDS,
    )


@router.post("/governor/pause")
async def governor_pause(request: Request):
    """Pause governor globally or a specific lane."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/pause",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    scope = body.get("scope", "global")
    actor = action.actor
    reason = action.reason

    gov = Governor.get()
    await gov.pause(scope=scope, actor=actor, reason=reason)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/pause",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Paused governor scope={scope}",
        target=scope,
    )
    return {"status": "paused", "scope": scope}


@router.post("/governor/resume")
async def governor_resume(request: Request):
    """Resume governor globally or a specific lane."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/resume",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    scope = body.get("scope", "global")
    actor = action.actor
    reason = action.reason

    gov = Governor.get()
    await gov.resume(scope=scope, actor=actor, reason=reason)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/resume",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Resumed governor scope={scope}",
        target=scope,
    )
    return {"status": "resumed", "scope": scope}


@router.post("/governor/heartbeat")
async def governor_heartbeat(request: Request):
    """Record a heartbeat from the dashboard."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/heartbeat",
        action_class="operator",
        default_reason="Dashboard heartbeat acknowledgement",
    )
    if denial:
        return denial
    source = body.get("source", "dashboard")
    state = str(body.get("state") or "at_desk")

    gov = Governor.get()
    await gov.record_heartbeat(source=source, state=state)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/heartbeat",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded heartbeat source={source}",
        target=source,
    )
    return {"status": "ok", "source": source}


@router.post("/governor/presence")
async def governor_presence(request: Request):
    """Set presence mode and state."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/presence",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    mode = body.get("mode", "auto")
    state = body.get("state", "at_desk")
    reason = action.reason
    actor = action.actor

    gov = Governor.get()
    await gov.set_presence(mode=mode, state=state, reason=reason, actor=actor)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/presence",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Set operator presence mode={mode} state={state}",
        target=state,
        metadata={"mode": mode},
    )
    return {"status": "ok", "mode": mode, "state": state}


@router.post("/governor/release-tier")
async def governor_release_tier(request: Request):
    """Set the release tier for cloud provider access."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/release-tier",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    tier = body.get("tier", "standard")
    reason = action.reason
    actor = action.actor

    gov = Governor.get()
    await gov.set_release_tier(tier=tier, reason=reason, actor=actor)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/release-tier",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Set release tier={tier}",
        target=tier,
    )
    return {"status": "ok", "tier": tier}


@router.get("/governor/operations")
async def governor_operations():
    """Operations readiness check."""
    from ..governor import build_operations_readiness_snapshot

    return await _await_snapshot(
        "governor_operations",
        build_operations_readiness_snapshot(),
        fallback_factory=_degraded_operations_snapshot,
    )


@router.get("/governor/operator-tests")
async def governor_operator_tests():
    """List available operator tests."""
    from ..operator_tests import build_operator_tests_snapshot

    return await build_operator_tests_snapshot()


@router.post("/governor/operator-tests/run")
async def governor_run_operator_tests(request: Request):
    """Run operator tests."""
    from ..operator_tests import run_operator_tests

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/operator-tests/run",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial

    flow_ids = body.get("flow_ids")
    if isinstance(flow_ids, list):
        selected_flow_ids = [str(flow_id) for flow_id in flow_ids if str(flow_id).strip()]
    else:
        selected_flow_ids = None

    snapshot = await run_operator_tests(flow_ids=selected_flow_ids, actor=action.actor)
    passed = sum(
        1 for flow in snapshot.get("flows", []) if str(flow.get("last_outcome") or "").strip().lower() == "passed"
    )
    total = int(snapshot.get("flow_count", len(snapshot.get("flows", []))) or 0)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/operator-tests/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Executed operator tests passed={passed}/{total}",
        metadata={
            "source": body.get("source", "dashboard"),
            "flow_ids": selected_flow_ids or [],
        },
    )
    return snapshot


@router.get("/governor/tool-permissions")
async def governor_tool_permissions():
    """Get the canonical tool-permission governance snapshot."""
    from ..governor import build_tool_permissions_snapshot

    return await build_tool_permissions_snapshot()

