"""Compatibility facade for the governor public surface."""

from __future__ import annotations

from datetime import datetime, timezone

from .governor_runtime import (
    DECISIONS_MAX,
    GOV_APPROVAL_STATS_KEY,
    GOV_DECISIONS_KEY,
    GOV_HEARTBEAT_KEY,
    GOV_PAUSED_LANES_KEY,
    GOV_PRESENCE_KEY,
    GOV_STATE_KEY,
    HEARTBEAT_STALE_SECONDS,
    HIGH_IMPACT_AGENTS,
    LANES,
    LOW_RISK_AGENTS,
    MEDIUM_RISK_AGENTS,
    PRESENCE_STATES,
    RELEASE_TIER_KEY,
    TRUST_CACHE_TTL,
    GateDecision,
    Governor,
    _compat_add_set_member,
    _compat_hgetall,
    _compat_hset,
    _compat_remove_set_member,
    _compat_replace_set,
    _compat_set_members,
    _default_governor_state,
    _ensure_backbone_governor_state,
    _get_redis,
    _job_priority_band,
)


def _governor_backbone():
    from . import governor_backbone as backbone

    backbone._get_redis = _get_redis
    return backbone


async def build_capacity_snapshot() -> dict:
    return await _governor_backbone().build_capacity_snapshot()


async def build_governor_snapshot() -> dict:
    return await _governor_backbone().build_governor_snapshot()


async def build_operations_readiness_snapshot() -> dict:
    return await _governor_backbone().build_operations_readiness_snapshot()


async def build_tool_permissions_snapshot() -> dict:
    return await _governor_backbone().build_tool_permissions_snapshot()


async def get_governor_state() -> dict:
    return await _ensure_backbone_governor_state()


async def set_operator_presence(state: str, reason: str = "", actor: str = "operator") -> dict:
    return await _governor_backbone().set_operator_presence(
        state,
        reason=reason,
        actor=actor,
        mode="manual",
    )


async def record_presence_heartbeat(source: str = "dashboard") -> dict:
    return await _governor_backbone().record_presence_heartbeat(
        "at_desk",
        source=source,
        reason="Dashboard heartbeat updated operator presence.",
        actor=source or "dashboard-heartbeat",
    )


async def set_release_tier(tier: str, reason: str = "", actor: str = "operator") -> dict:
    return await _governor_backbone().set_release_tier(tier, reason=reason, actor=actor)


async def pause_automation(scope: str = "global", reason: str = "", actor: str = "operator") -> dict:
    return await _governor_backbone().pause_automation(scope=scope, reason=reason, actor=actor)


async def resume_automation(scope: str = "global", reason: str = "", actor: str = "operator") -> dict:
    state = await _governor_backbone().resume_automation(scope=scope, actor=actor)
    if reason and scope == "global":
        state["reason"] = reason
        state["updated_by"] = actor
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await _governor_backbone()._save_governor_state(state)
    return state


async def is_automation_paused(scope: str | None = None) -> bool:
    return await _governor_backbone().is_automation_paused(scope or "global")


async def _save_governor_state(saved_state: dict) -> dict:
    return await _governor_backbone()._save_governor_state(saved_state)


async def evaluate_job_governance(
    *,
    job_id: str,
    job_family: str,
    control_scope: str | None,
    owner_agent: str,
    capacity_snapshot: dict | None = None,
) -> dict:
    return await _governor_backbone().evaluate_job_governance(
        job_id=job_id,
        job_family=job_family,
        control_scope=control_scope,
        owner_agent=owner_agent,
        capacity_snapshot=capacity_snapshot,
    )
