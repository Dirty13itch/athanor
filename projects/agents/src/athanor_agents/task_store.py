from __future__ import annotations

import json
import time
from typing import Any


TASKS_KEY = "athanor:tasks"
TASKS_UPDATED_KEY = "athanor:tasks:updated"
TASK_STATUS_KEY_PREFIX = "athanor:tasks:status:"
TASK_LANE_KEY_PREFIX = "athanor:tasks:lane:"
TASK_SESSION_KEY_PREFIX = "athanor:tasks:session:"
TASK_STATUS_VALUES = {
    "pending",
    "pending_approval",
    "running",
    "stale_lease",
    "completed",
    "failed",
    "cancelled",
}


def _status_key(status: str) -> str:
    return f"{TASK_STATUS_KEY_PREFIX}{status}"


def _lane_key(lane: str) -> str:
    return f"{TASK_LANE_KEY_PREFIX}{lane}"


def _session_key(session_id: str) -> str:
    return f"{TASK_SESSION_KEY_PREFIX}{session_id}"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _decode_record(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, bytes):
        raw = raw.decode()
    if isinstance(raw, str):
        data = json.loads(raw)
    elif isinstance(raw, dict):
        data = raw
    else:
        data = dict(raw)
    return data if isinstance(data, dict) else {}


def normalize_task_record(record: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    normalized = dict(record)
    metadata = _as_dict(normalized.get("metadata"))
    lease = _as_dict(normalized.get("lease")) or _as_dict(metadata.get("execution_lease"))

    normalized["id"] = str(normalized.get("id") or "")
    normalized["agent"] = str(normalized.get("agent") or normalized.get("agent_id") or "")
    normalized["prompt"] = str(normalized.get("prompt") or "")
    normalized["priority"] = str(normalized.get("priority") or "normal")
    normalized["source"] = str(normalized.get("source") or metadata.get("source") or "task_api")
    normalized["lane"] = str(
        normalized.get("lane")
        or metadata.get("lane")
        or metadata.get("job_family")
        or metadata.get("control_scope")
        or normalized["agent"]
        or normalized["source"]
    )

    status = str(normalized.get("status") or "pending")
    if status == "in_progress":
        status = "running"
    if status == "error":
        status = "failed"
    if status not in TASK_STATUS_VALUES:
        status = "pending"
    normalized["status"] = status

    normalized["created_at"] = _as_float(normalized.get("created_at"), now)
    normalized["started_at"] = _as_float(normalized.get("started_at"), 0.0)
    normalized["completed_at"] = _as_float(normalized.get("completed_at"), 0.0)
    normalized["updated_at"] = _as_float(
        normalized.get("updated_at"),
        normalized["completed_at"] or normalized["started_at"] or normalized["created_at"] or now,
    )
    normalized["last_heartbeat"] = _as_float(
        normalized.get("last_heartbeat"),
        normalized["started_at"] or normalized["updated_at"] or 0.0,
    )

    normalized["metadata"] = metadata
    normalized["lease"] = lease
    normalized["assigned_runtime"] = str(
        normalized.get("assigned_runtime") or lease.get("provider") or metadata.get("assigned_runtime") or ""
    )
    normalized["session_id"] = str(normalized.get("session_id") or metadata.get("session_id") or "")
    normalized["retry_lineage"] = [
        str(item)
        for item in _as_list(normalized.get("retry_lineage"))
        if str(item).strip()
    ]
    if not normalized["retry_lineage"]:
        retry_of = str(metadata.get("retry_of") or "").strip()
        if retry_of:
            normalized["retry_lineage"] = [retry_of]

    normalized["result"] = str(normalized.get("result") or "")
    normalized["error"] = str(normalized.get("error") or "")
    normalized["steps"] = _as_list(normalized.get("steps"))
    normalized["parent_task_id"] = str(normalized.get("parent_task_id") or "")
    normalized["retry_count"] = int(normalized.get("retry_count") or 0)
    normalized["previous_error"] = str(normalized.get("previous_error") or "")
    return normalized


async def read_task_record(redis_client, task_id: str) -> dict[str, Any] | None:
    raw = await redis_client.hget(TASKS_KEY, task_id)
    if not raw:
        return None
    return normalize_task_record(_decode_record(raw))


async def read_all_task_records(redis_client) -> list[dict[str, Any]]:
    raw = await redis_client.hgetall(TASKS_KEY)
    return [normalize_task_record(_decode_record(item)) for item in raw.values()]


def _decode_task_id(raw_task_id: Any) -> str:
    return raw_task_id.decode() if isinstance(raw_task_id, bytes) else str(raw_task_id)


async def read_task_records_by_statuses(
    redis_client,
    *statuses: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    normalized_statuses = [str(status).strip() for status in statuses if str(status).strip() in TASK_STATUS_VALUES]
    if not normalized_statuses:
        return []

    task_id_sources: dict[str, set[str]] = {}
    for status in normalized_statuses:
        task_ids = await redis_client.smembers(_status_key(status))
        for raw_task_id in task_ids or set():
            task_id = _decode_task_id(raw_task_id)
            task_id_sources.setdefault(task_id, set()).add(status)

    records: list[dict[str, Any]] = []
    for task_id, source_statuses in task_id_sources.items():
        record = await read_task_record(redis_client, task_id)
        if not record:
            for status in source_statuses:
                await redis_client.srem(_status_key(status), task_id)
            continue
        canonical_status = str(record.get("status") or "")
        stale_statuses = [status for status in source_statuses if status != canonical_status]
        for status in stale_statuses:
            await redis_client.srem(_status_key(status), task_id)
        if canonical_status not in normalized_statuses:
            continue
        if canonical_status and canonical_status not in source_statuses:
            await redis_client.sadd(_status_key(canonical_status), task_id)
        records.append(record)

    records.sort(
        key=lambda record: (
            float(record.get("updated_at") or 0.0),
            str(record.get("id") or ""),
        ),
        reverse=True,
    )

    if limit is not None:
        return records[: max(int(limit), 0)]
    return records


async def read_task_records_by_status(
    redis_client,
    status: str,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return await read_task_records_by_statuses(redis_client, status, limit=limit)


async def _update_indexes(
    redis_client,
    *,
    task_id: str,
    record: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> None:
    if previous:
        if previous.get("status") and previous.get("status") != record.get("status"):
            await redis_client.srem(_status_key(str(previous["status"])), task_id)
        if previous.get("lane") and previous.get("lane") != record.get("lane"):
            await redis_client.srem(_lane_key(str(previous["lane"])), task_id)
        if previous.get("session_id") and previous.get("session_id") != record.get("session_id"):
            await redis_client.srem(_session_key(str(previous["session_id"])), task_id)

    await redis_client.sadd(_status_key(str(record["status"])), task_id)
    if record.get("lane"):
        await redis_client.sadd(_lane_key(str(record["lane"])), task_id)
    if record.get("session_id"):
        await redis_client.sadd(_session_key(str(record["session_id"])), task_id)
    await redis_client.zadd(TASKS_UPDATED_KEY, {task_id: float(record["updated_at"])})


async def write_task_record(
    redis_client,
    record: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_task_record(record)
    existing = previous if previous is not None else await read_task_record(redis_client, str(normalized["id"]))
    await redis_client.hset(TASKS_KEY, str(normalized["id"]), json.dumps(normalized))
    await _update_indexes(redis_client, task_id=str(normalized["id"]), record=normalized, previous=existing)
    return normalized


async def delete_task_record(redis_client, task_id: str) -> None:
    existing = await read_task_record(redis_client, task_id)
    await redis_client.hdel(TASKS_KEY, task_id)
    await redis_client.zrem(TASKS_UPDATED_KEY, task_id)
    if not existing:
        return
    if existing.get("status"):
        await redis_client.srem(_status_key(str(existing["status"])), task_id)
    if existing.get("lane"):
        await redis_client.srem(_lane_key(str(existing["lane"])), task_id)
    if existing.get("session_id"):
        await redis_client.srem(_session_key(str(existing["session_id"])), task_id)


async def backfill_task_store_indexes(redis_client) -> int:
    raw = await redis_client.hgetall(TASKS_KEY)
    updated = 0
    for task_id, payload in raw.items():
        record = normalize_task_record(_decode_record(payload))
        for status in TASK_STATUS_VALUES:
            await redis_client.srem(_status_key(status), str(record["id"]))
        await redis_client.hset(TASKS_KEY, str(record["id"]), json.dumps(record))
        await _update_indexes(redis_client, task_id=str(record["id"]), record=record)
        updated += 1
    return updated
