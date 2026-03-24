from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from redis.exceptions import RedisError

from .model_governance import get_deprecation_retirement_policy, get_model_role_registry

RETIREMENT_RECORDS_KEY = "athanor:model-governance:retirements"
RETIREMENT_EVENTS_KEY = "athanor:model-governance:retirement-events"
RETIREMENT_EVENT_LIMIT = 100


@dataclass
class RetirementRecord:
    id: str
    asset_class: str
    asset_id: str
    label: str
    current_stage: str
    target_stage: str
    status: str
    reason: str
    created_at: str
    updated_at: str
    updated_by: str
    source: str
    next_stage: str | None = None
    completed_at: str | None = None
    rollback_target: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def _get_redis():
    from .workspace import get_redis

    return await get_redis()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _retirement_stages() -> list[str]:
    stages = [
        str(item).strip()
        for item in get_deprecation_retirement_policy().get("stages", [])
        if str(item).strip()
    ]
    if stages:
        return stages
    return ["active", "deprecated", "retired_reference_only"]


def _stage_index(stage: str) -> int:
    stages = _retirement_stages()
    try:
        return stages.index(stage)
    except ValueError:
        return 0


def _next_stage(current_stage: str, target_stage: str) -> str | None:
    stages = _retirement_stages()
    current_index = _stage_index(current_stage)
    target_index = _stage_index(target_stage)
    if current_index >= target_index:
        return None
    return stages[min(current_index + 1, target_index)]


def _allowed_asset_classes() -> set[str]:
    return {
        str(item).strip()
        for item in get_deprecation_retirement_policy().get("asset_classes", [])
        if str(item).strip()
    }


def _model_retirement_candidates(limit: int = 6) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for role in get_model_role_registry().get("roles", []):
        if not isinstance(role, dict):
            continue
        champion = str(role.get("champion") or "").strip()
        role_id = str(role.get("id") or "").strip()
        if not champion or not role_id:
            continue
        label = str(role.get("label") or role_id)
        candidates.append(
            {
                "asset_class": "models",
                "asset_id": f"{role_id}:{champion}",
                "label": f"{label} champion {champion}",
                "role_id": role_id,
                "plane": str(role.get("plane") or "unclassified"),
                "current_stage": "active",
            }
        )
    return candidates[:limit]


async def _record_retirement_event(event: dict[str, Any]) -> None:
    redis = await _get_redis()
    await redis.lpush(RETIREMENT_EVENTS_KEY, json.dumps(event))
    await redis.ltrim(RETIREMENT_EVENTS_KEY, 0, RETIREMENT_EVENT_LIMIT - 1)


async def list_retirement_records(limit: int = 25, status: str = "") -> list[dict[str, Any]]:
    try:
        redis = await _get_redis()
        raw = await redis.hgetall(RETIREMENT_RECORDS_KEY)
    except RedisError:
        return []

    records = [json.loads(value) for value in raw.values()]
    if status:
        records = [record for record in records if str(record.get("status")) == status]
    records.sort(key=lambda record: str(record.get("updated_at") or record.get("created_at") or ""), reverse=True)
    return records[:limit]


async def list_retirement_events(limit: int = 25) -> list[dict[str, Any]]:
    try:
        redis = await _get_redis()
        raw = await redis.lrange(RETIREMENT_EVENTS_KEY, 0, max(limit - 1, 0))
    except RedisError:
        return []

    events = [json.loads(item) for item in raw]
    events.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    return events[:limit]


async def stage_retirement_candidate(
    *,
    asset_class: str,
    asset_id: str,
    label: str,
    target_stage: str = "retired_reference_only",
    actor: str = "operator",
    reason: str = "",
    source: str = "manual",
) -> dict[str, Any]:
    normalized_asset_class = str(asset_class or "").strip()
    normalized_asset_id = str(asset_id or "").strip()
    normalized_label = str(label or normalized_asset_id).strip()
    normalized_target = str(target_stage or "").strip()

    if not normalized_asset_class or normalized_asset_class not in _allowed_asset_classes():
        raise ValueError(f"Unsupported retirement asset class: {asset_class}")
    if not normalized_asset_id:
        raise ValueError("Asset id is required.")
    if normalized_target not in _retirement_stages():
        raise ValueError(f"Unsupported retirement target stage: {target_stage}")

    created_at = _now_iso()
    current_stage = _retirement_stages()[0]
    record = RetirementRecord(
        id=f"retirement-{uuid.uuid4().hex[:12]}",
        asset_class=normalized_asset_class,
        asset_id=normalized_asset_id,
        label=normalized_label,
        current_stage=current_stage,
        target_stage=normalized_target,
        status="staged",
        reason=reason or f"Stage {normalized_label} for governed retirement.",
        created_at=created_at,
        updated_at=created_at,
        updated_by=actor,
        source=source,
        next_stage=_next_stage(current_stage, normalized_target),
        rollback_target=current_stage,
        notes=[
            "Retirement follows the canonical active -> deprecated -> retired_reference_only ladder.",
            "Rollback restores the asset to active status without deleting historical evidence.",
        ],
    )

    redis = await _get_redis()
    await redis.hset(RETIREMENT_RECORDS_KEY, record.id, json.dumps(record.to_dict()))
    await _record_retirement_event(
        {
            "event": "retirement_staged",
            "retirement_id": record.id,
            "asset_class": normalized_asset_class,
            "asset_id": normalized_asset_id,
            "target_stage": normalized_target,
            "timestamp": created_at,
            "actor": actor,
        }
    )
    return record.to_dict()


async def transition_retirement_candidate(
    retirement_id: str,
    *,
    action: str,
    actor: str = "operator",
    reason: str = "",
) -> dict[str, Any] | None:
    redis = await _get_redis()
    raw = await redis.hget(RETIREMENT_RECORDS_KEY, retirement_id)
    if not raw:
        return None

    record = json.loads(raw)
    updated_at = _now_iso()
    normalized_action = str(action or "").strip().lower()

    if normalized_action == "advance":
        if record.get("status") in {"rolled_back", "completed"}:
            return record
        next_stage = _next_stage(str(record.get("current_stage") or ""), str(record.get("target_stage") or ""))
        if next_stage is None:
            record["status"] = "completed"
            record["completed_at"] = updated_at
            record.setdefault("notes", []).append(
                "Retirement target already reached; no further stage advancement required."
            )
        else:
            record["current_stage"] = next_stage
            record["status"] = "completed" if next_stage == record.get("target_stage") else "active"
            record["completed_at"] = updated_at if record["status"] == "completed" else None
        record["next_stage"] = _next_stage(
            str(record.get("current_stage") or ""),
            str(record.get("target_stage") or ""),
        )
        event_name = "retirement_advanced"
    elif normalized_action == "hold":
        if record.get("status") != "rolled_back":
            record["status"] = "held"
        event_name = "retirement_held"
    elif normalized_action == "rollback":
        record["status"] = "rolled_back"
        record["completed_at"] = updated_at
        record["current_stage"] = _retirement_stages()[0]
        record["next_stage"] = None
        record["rollback_target"] = _retirement_stages()[0]
        record.setdefault("notes", []).append("Retirement rehearsal rolled back to active posture.")
        event_name = "retirement_rolled_back"
    else:
        raise ValueError(f"Unsupported retirement action: {action}")

    record["updated_at"] = updated_at
    record["updated_by"] = actor
    if reason:
        record["reason"] = reason

    await redis.hset(RETIREMENT_RECORDS_KEY, retirement_id, json.dumps(record))
    await _record_retirement_event(
        {
            "event": event_name,
            "retirement_id": retirement_id,
            "asset_class": record.get("asset_class"),
            "asset_id": record.get("asset_id"),
            "stage": record.get("current_stage"),
            "status": record.get("status"),
            "timestamp": updated_at,
            "actor": actor,
        }
    )
    return record


async def build_retirement_controls_snapshot(limit: int = 12) -> dict[str, Any]:
    registry = get_deprecation_retirement_policy()
    records = await list_retirement_records(limit=limit)
    events = await list_retirement_events(limit=limit)
    stages = _retirement_stages()

    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status") or "staged")
        counts[status] = counts.get(status, 0) + 1

    active = [
        record
        for record in records
        if str(record.get("status")) in {"staged", "active", "held"}
    ]
    candidate_queue = _model_retirement_candidates(limit=limit)
    status = "live_partial" if records or events else str(registry.get("status", "configured"))

    next_actions: list[str] = []
    if active:
        next_actions.append(
            f"{len(active)} retirement candidate(s) are active or held across the governed ladder."
        )
    elif candidate_queue:
        first = candidate_queue[0]
        next_actions.append(
            f"Stage {first['label']} to move the retirement ladder from registry posture into live rehearsal."
        )
    else:
        next_actions.append("No governed retirement candidates are currently available for rehearsal.")

    return {
        "generated_at": _now_iso(),
        "status": status,
        "asset_classes": list(registry.get("asset_classes", [])),
        "stages": stages,
        "rule": str(registry.get("rule") or ""),
        "counts": counts,
        "active_retirements": active,
        "recent_retirements": records,
        "recent_events": events,
        "candidate_queue": candidate_queue,
        "next_actions": next_actions,
    }
