from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def checked_at_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def dependency_record(
    dependency_id: str,
    *,
    status: str,
    detail: str,
    required: bool = True,
    last_checked_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": dependency_id,
        "status": status,
        "required": required,
        "last_checked_at": last_checked_at or checked_at_utc(),
        "detail": detail,
    }


def build_health_snapshot(
    *,
    service: str,
    version: str,
    auth_class: str,
    dependencies: list[dict[str, Any]],
    started_at: str,
    actions_allowed: list[str],
    network_scope: str = "internal_only",
    last_error: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    degraded_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.get("required", True) and dependency.get("status") != "healthy"
    ]
    status = "degraded" if degraded_dependencies else "healthy"
    if last_error is None and degraded_dependencies:
        last_error = str(degraded_dependencies[0].get("detail") or "") or None

    return {
        "service": service,
        "version": version,
        "status": status,
        "auth_class": auth_class,
        "dependencies": dependencies,
        "last_error": last_error,
        "started_at": started_at,
        "actions_allowed": actions_allowed,
        "network_scope": network_scope,
        **extra,
    }
