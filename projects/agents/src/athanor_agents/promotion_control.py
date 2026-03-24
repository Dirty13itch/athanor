from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from redis.exceptions import RedisError

from .model_governance import get_model_role_registry, get_release_ritual_registry

PROMOTION_RECORDS_KEY = "athanor:model-governance:promotions"
PROMOTION_EVENTS_KEY = "athanor:model-governance:promotion-events"
PROMOTION_EVENT_LIMIT = 100


@dataclass
class PromotionRecord:
    id: str
    asset_class: str
    role_id: str
    role_label: str
    plane: str
    candidate: str
    champion: str
    current_tier: str
    target_tier: str
    status: str
    reason: str
    created_at: str
    updated_at: str
    updated_by: str
    source: str
    rollout_steps: list[str] = field(default_factory=list)
    next_tier: str | None = None
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


def _release_tiers() -> list[str]:
    tiers = [str(item).strip() for item in get_release_ritual_registry().get("tiers", []) if str(item).strip()]
    if tiers:
        return tiers
    return ["offline_eval", "shadow", "sandbox", "canary", "production"]


def _tier_index(tier: str) -> int:
    tiers = _release_tiers()
    try:
        return tiers.index(tier)
    except ValueError:
        return 0


def _next_tier(current_tier: str, target_tier: str) -> str | None:
    tiers = _release_tiers()
    current_index = _tier_index(current_tier)
    target_index = _tier_index(target_tier)
    if current_index >= target_index:
        return None
    return tiers[min(current_index + 1, target_index)]


def _role_record(role_id: str) -> dict[str, Any]:
    for role in get_model_role_registry().get("roles", []):
        if str(role.get("id")) == role_id:
            return dict(role)
    raise ValueError(f"Unknown model role: {role_id}")


async def _record_promotion_event(event: dict[str, Any]) -> None:
    redis = await _get_redis()
    await redis.lpush(PROMOTION_EVENTS_KEY, json.dumps(event))
    await redis.ltrim(PROMOTION_EVENTS_KEY, 0, PROMOTION_EVENT_LIMIT - 1)


async def list_promotion_records(limit: int = 25, status: str = "") -> list[dict[str, Any]]:
    try:
        redis = await _get_redis()
        raw = await redis.hgetall(PROMOTION_RECORDS_KEY)
    except RedisError:
        return []
    records = [json.loads(value) for value in raw.values()]
    if status:
        records = [record for record in records if str(record.get("status")) == status]
    records.sort(key=lambda record: str(record.get("updated_at") or record.get("created_at") or ""), reverse=True)
    return records[:limit]


async def list_promotion_events(limit: int = 25) -> list[dict[str, Any]]:
    try:
        redis = await _get_redis()
        raw = await redis.lrange(PROMOTION_EVENTS_KEY, 0, max(limit - 1, 0))
    except RedisError:
        return []
    events = [json.loads(item) for item in raw]
    events.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    return events[:limit]


async def stage_promotion_candidate(
    *,
    role_id: str,
    candidate: str,
    target_tier: str = "canary",
    actor: str = "operator",
    reason: str = "",
    source: str = "manual",
    asset_class: str = "models",
) -> dict[str, Any]:
    role = _role_record(role_id)
    normalized_candidate = str(candidate or "").strip()
    if not normalized_candidate:
        raise ValueError("Candidate is required.")

    challengers = [str(item) for item in role.get("challengers", [])]
    champion = str(role.get("champion") or "")
    if challengers and normalized_candidate not in challengers and normalized_candidate != champion:
        raise ValueError(f"Candidate '{normalized_candidate}' is not registered for role '{role_id}'.")

    tiers = _release_tiers()
    normalized_target = str(target_tier or "").strip()
    if normalized_target not in tiers:
        raise ValueError(f"Unknown target tier: {target_tier}")

    created_at = _now_iso()
    current_tier = tiers[0]
    record = PromotionRecord(
        id=f"promotion-{uuid.uuid4().hex[:12]}",
        asset_class=asset_class,
        role_id=role_id,
        role_label=str(role.get("label") or role_id),
        plane=str(role.get("plane") or "unclassified"),
        candidate=normalized_candidate,
        champion=champion,
        current_tier=current_tier,
        target_tier=normalized_target,
        status="staged",
        reason=reason or f"Stage {normalized_candidate} for governed promotion.",
        created_at=created_at,
        updated_at=created_at,
        updated_by=actor,
        source=source,
        rollout_steps=list(get_release_ritual_registry().get("ritual", [])),
        next_tier=_next_tier(current_tier, normalized_target),
        notes=[
            "Promotion follows the canonical offline_eval -> shadow -> sandbox -> canary -> production ladder.",
            "Rollback target is the current champion until the candidate is explicitly promoted.",
        ],
    )

    redis = await _get_redis()
    await redis.hset(PROMOTION_RECORDS_KEY, record.id, json.dumps(record.to_dict()))
    await _record_promotion_event(
        {
            "event": "promotion_staged",
            "promotion_id": record.id,
            "role_id": role_id,
            "candidate": normalized_candidate,
            "target_tier": normalized_target,
            "timestamp": created_at,
            "actor": actor,
        }
    )
    return record.to_dict()


async def transition_promotion_candidate(
    promotion_id: str,
    *,
    action: str,
    actor: str = "operator",
    reason: str = "",
) -> dict[str, Any] | None:
    redis = await _get_redis()
    raw = await redis.hget(PROMOTION_RECORDS_KEY, promotion_id)
    if not raw:
        return None

    record = json.loads(raw)
    updated_at = _now_iso()
    normalized_action = str(action or "").strip().lower()

    if normalized_action == "advance":
        if record.get("status") in {"rolled_back", "completed"}:
            return record
        next_tier = _next_tier(str(record.get("current_tier") or ""), str(record.get("target_tier") or ""))
        if next_tier is None:
            record["status"] = "completed"
            record["completed_at"] = updated_at
            record["notes"] = list(record.get("notes", [])) + [
                "Promotion target already reached; no further tier advancement required."
            ]
        else:
            record["current_tier"] = next_tier
            record["status"] = "completed" if next_tier == record.get("target_tier") else "active"
            record["completed_at"] = updated_at if record["status"] == "completed" else None
        record["next_tier"] = _next_tier(
            str(record.get("current_tier") or ""),
            str(record.get("target_tier") or ""),
        )
        event_name = "promotion_advanced"
    elif normalized_action == "hold":
        if record.get("status") != "rolled_back":
            record["status"] = "held"
        event_name = "promotion_held"
    elif normalized_action == "rollback":
        record["status"] = "rolled_back"
        record["completed_at"] = updated_at
        record["rollback_target"] = str(record.get("champion") or "")
        record["next_tier"] = None
        record["notes"] = list(record.get("notes", [])) + [
            f"Rollback target remains {record['rollback_target'] or 'the prior champion'}."
        ]
        event_name = "promotion_rolled_back"
    else:
        raise ValueError(f"Unsupported promotion action: {action}")

    record["updated_at"] = updated_at
    record["updated_by"] = actor
    if reason:
        record["reason"] = reason

    await redis.hset(PROMOTION_RECORDS_KEY, promotion_id, json.dumps(record))
    await _record_promotion_event(
        {
            "event": event_name,
            "promotion_id": promotion_id,
            "role_id": record.get("role_id"),
            "candidate": record.get("candidate"),
            "tier": record.get("current_tier"),
            "status": record.get("status"),
            "timestamp": updated_at,
            "actor": actor,
        }
    )
    return record


async def build_promotion_controls_snapshot(limit: int = 12) -> dict[str, Any]:
    records = await list_promotion_records(limit=limit)
    events = await list_promotion_events(limit=limit)
    tiers = _release_tiers()
    registry = get_release_ritual_registry()

    counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("status") or "staged")
        counts[status] = counts.get(status, 0) + 1

    active = [
        record
        for record in records
        if str(record.get("status")) in {"staged", "active", "held"}
    ]
    recent = records[:limit]
    candidate_queue = [
        {
            "role_id": str(role.get("id") or ""),
            "label": str(role.get("label") or role.get("id") or "role"),
            "champion": str(role.get("champion") or ""),
            "challengers": [str(item) for item in role.get("challengers", [])],
            "plane": str(role.get("plane") or "unclassified"),
        }
        for role in get_model_role_registry().get("roles", [])
        if role.get("challengers")
    ]

    status = "live_partial" if records or events else str(registry.get("status", "configured"))
    next_actions: list[str] = []
    if active:
        next_actions.append(
            f"{len(active)} promotion candidate(s) are active or held across the governed ladder."
        )
    elif candidate_queue:
        first = candidate_queue[0]
        next_actions.append(
            f"Stage {first['challengers'][0]} for {first['label']} to move the release ladder from registry posture into live promotion control."
        )
    else:
        next_actions.append("No challenger lanes are currently available for governed promotion.")

    return {
        "generated_at": _now_iso(),
        "status": status,
        "tiers": tiers,
        "ritual": list(registry.get("ritual", [])),
        "counts": counts,
        "active_promotions": active,
        "recent_promotions": recent,
        "recent_events": events,
        "candidate_queue": candidate_queue,
        "next_actions": next_actions,
    }
