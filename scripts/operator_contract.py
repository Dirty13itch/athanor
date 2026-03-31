from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Mapping

import redis.asyncio as aioredis
from fastapi import HTTPException

try:
    from scripts._cluster_config import get_url
except ModuleNotFoundError:
    from _cluster_config import get_url
from runtime_env import load_optional_runtime_env


OPERATOR_AUDIT_STREAM = "athanor:operator:audit"

_redis: aioredis.Redis | None = None

load_optional_runtime_env(env_names=["ATHANOR_REDIS_URL", "ATHANOR_REDIS_PASSWORD"])


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _as_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _body_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, Mapping) else {}


@dataclass(frozen=True, slots=True)
class OperatorActionRequest:
    actor: str
    session_id: str
    correlation_id: str
    reason: str = ""
    dry_run: bool = False
    protected_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_operator_action(
    payload: Mapping[str, Any] | None,
    *,
    default_actor: str = "operator",
    default_reason: str = "",
) -> OperatorActionRequest:
    body = _body_dict(payload)
    return OperatorActionRequest(
        actor=_as_str(body.get("actor")) or default_actor,
        session_id=_as_str(body.get("session_id")) or "",
        correlation_id=_as_str(body.get("correlation_id")) or uuid.uuid4().hex,
        reason=_as_str(body.get("reason")) or default_reason,
        dry_run=_as_bool(body.get("dry_run")),
        protected_mode=_as_bool(body.get("protected_mode")),
    )


def require_operator_action(
    payload: Mapping[str, Any] | None,
    *,
    action_class: str,
    default_actor: str = "operator",
    default_reason: str = "",
) -> OperatorActionRequest:
    action = build_operator_action(
        payload,
        default_actor=default_actor,
        default_reason=default_reason,
    )
    missing = [
        field
        for field, value in (
            ("actor", action.actor),
            ("session_id", action.session_id),
            ("correlation_id", action.correlation_id),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Operator action envelope missing required fields: {', '.join(missing)}",
        )

    if action_class in {"admin", "destructive-admin"} and not action.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="reason is required for admin and destructive-admin actions",
        )

    if action_class == "destructive-admin" and not action.protected_mode:
        raise HTTPException(
            status_code=400,
            detail="protected_mode=true is required for destructive-admin actions",
        )

    return action


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        redis_url = os.getenv("ATHANOR_REDIS_URL", "").strip() or os.getenv("REDIS_URL", "").strip() or get_url("redis")
        redis_password = os.getenv("ATHANOR_REDIS_PASSWORD", "").strip() or None
        _redis = aioredis.from_url(redis_url, password=redis_password, decode_responses=True)
    return _redis


async def emit_operator_audit_event(
    *,
    service: str,
    route: str,
    action_class: str,
    decision: str,
    status_code: int,
    action: OperatorActionRequest,
    detail: str | None = None,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    event = {
        "timestamp": f"{time.time():.6f}",
        "service": service,
        "route": route,
        "action_class": action_class,
        "decision": decision,
        "status_code": str(status_code),
        "actor": action.actor,
        "session_id": action.session_id,
        "correlation_id": action.correlation_id,
        "reason": action.reason,
        "dry_run": "1" if action.dry_run else "0",
        "protected_mode": "1" if action.protected_mode else "0",
        "detail": detail or "",
        "target": target or "",
        "metadata": json.dumps(dict(metadata or {}), sort_keys=True),
    }

    try:
        redis_client = await _get_redis()
        await redis_client.xadd(
            OPERATOR_AUDIT_STREAM,
            event,
            maxlen=5000,
            approximate=True,
        )
    except Exception:
        return
