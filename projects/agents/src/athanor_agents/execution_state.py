from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from .durable_state import (
    _as_datetime,
    _as_json_value,
    _as_timestamp,
    _execute,
    _fetch_all,
    _open_connection,
    ensure_durable_state_schema,
)

logger = logging.getLogger(__name__)


def _row_to_execution_run_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("run_id") or ""),
        "task_id": str(row.get("task_id") or ""),
        "backlog_id": str(row.get("backlog_id") or ""),
        "request_fingerprint": str(row.get("request_fingerprint") or ""),
        "parent_run_id": str(row.get("parent_run_id") or ""),
        "agent_id": str(row.get("agent_id") or ""),
        "workload_class": str(row.get("workload_class") or ""),
        "provider_lane": str(row.get("provider_lane") or ""),
        "runtime_lane": str(row.get("runtime_lane") or ""),
        "policy_class": str(row.get("policy_class") or ""),
        "status": str(row.get("status") or "queued"),
        "summary": str(row.get("summary") or ""),
        "artifact_refs": _as_json_value(row.get("artifact_refs_json"), default=[]),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
    }


def _row_to_run_attempt_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("attempt_id") or ""),
        "run_id": str(row.get("run_id") or ""),
        "retry_of_attempt_id": str(row.get("retry_of_attempt_id") or ""),
        "replay_of_attempt_id": str(row.get("replay_of_attempt_id") or ""),
        "lease": _as_json_value(row.get("lease_json"), default={}),
        "worker_id": str(row.get("worker_id") or ""),
        "runtime_host": str(row.get("runtime_host") or ""),
        "started_at": _as_timestamp(row.get("started_at")),
        "heartbeat_at": _as_timestamp(row.get("heartbeat_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
        "status": str(row.get("status") or "running"),
        "error": str(row.get("error") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
    }


def _row_to_run_step_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("step_id") or ""),
        "attempt_id": str(row.get("attempt_id") or ""),
        "run_id": str(row.get("run_id") or ""),
        "step_key": str(row.get("step_key") or ""),
        "kind": str(row.get("kind") or ""),
        "seq": int(row.get("seq") or 0),
        "status": str(row.get("status") or "completed"),
        "input_ref": str(row.get("input_ref") or ""),
        "output_ref": str(row.get("output_ref") or ""),
        "checkpoint_ref": str(row.get("checkpoint_ref") or ""),
        "detail": _as_json_value(row.get("detail_json"), default={}),
        "started_at": _as_timestamp(row.get("started_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
        "created_at": _as_timestamp(row.get("created_at")),
    }


def _row_to_approval_request_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("approval_id") or ""),
        "related_run_id": str(row.get("related_run_id") or ""),
        "related_attempt_id": str(row.get("related_attempt_id") or ""),
        "related_task_id": str(row.get("related_task_id") or ""),
        "requested_action": str(row.get("requested_action") or ""),
        "privilege_class": str(row.get("privilege_class") or "operator"),
        "reason": str(row.get("reason") or ""),
        "status": str(row.get("status") or "pending"),
        "requested_at": _as_timestamp(row.get("requested_at")),
        "decided_at": _as_timestamp(row.get("decided_at")),
        "decided_by": str(row.get("decided_by") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
    }


async def upsert_execution_run_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO runs.execution_runs (
            run_id,
            task_id,
            backlog_id,
            request_fingerprint,
            parent_run_id,
            agent_id,
            workload_class,
            provider_lane,
            runtime_lane,
            policy_class,
            status,
            summary,
            artifact_refs_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
            %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (run_id) DO UPDATE SET
            task_id = EXCLUDED.task_id,
            backlog_id = EXCLUDED.backlog_id,
            request_fingerprint = EXCLUDED.request_fingerprint,
            parent_run_id = EXCLUDED.parent_run_id,
            agent_id = EXCLUDED.agent_id,
            workload_class = EXCLUDED.workload_class,
            provider_lane = EXCLUDED.provider_lane,
            runtime_lane = EXCLUDED.runtime_lane,
            policy_class = EXCLUDED.policy_class,
            status = EXCLUDED.status,
            summary = EXCLUDED.summary,
            artifact_refs_json = EXCLUDED.artifact_refs_json,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            completed_at = EXCLUDED.completed_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("task_id") or ""),
        str(record.get("backlog_id") or ""),
        str(record.get("request_fingerprint") or ""),
        str(record.get("parent_run_id") or ""),
        str(record.get("agent_id") or ""),
        str(record.get("workload_class") or ""),
        str(record.get("provider_lane") or ""),
        str(record.get("runtime_lane") or ""),
        str(record.get("policy_class") or ""),
        str(record.get("status") or "queued"),
        str(record.get("summary") or ""),
        json.dumps(record.get("artifact_refs") or []),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("completed_at")),
    )
    return await _execute(query, params)


async def fetch_execution_run_record(run_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            run_id,
            task_id,
            backlog_id,
            request_fingerprint,
            parent_run_id,
            agent_id,
            workload_class,
            provider_lane,
            runtime_lane,
            policy_class,
            status,
            summary,
            artifact_refs_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM runs.execution_runs
        WHERE run_id = %s
        """,
        (run_id,),
    )
    if not rows:
        return None
    return _row_to_execution_run_record(rows[0])


async def list_execution_run_records(
    *,
    status: str = "",
    agent: str = "",
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            run_id,
            task_id,
            backlog_id,
            request_fingerprint,
            parent_run_id,
            agent_id,
            workload_class,
            provider_lane,
            runtime_lane,
            policy_class,
            status,
            summary,
            artifact_refs_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM runs.execution_runs
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if agent:
        clauses.append("agent_id = %s")
        params.append(agent)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC, run_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_execution_run_record(row) for row in rows]


async def get_execution_run_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT status, COUNT(*)::integer AS count
        FROM runs.execution_runs
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {"total": sum(by_status.values()), "by_status": by_status}


async def upsert_run_attempt_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO runs.run_attempts (
            attempt_id,
            run_id,
            retry_of_attempt_id,
            replay_of_attempt_id,
            lease_json,
            worker_id,
            runtime_host,
            started_at,
            heartbeat_at,
            completed_at,
            status,
            error,
            metadata_json,
            created_at
        )
        VALUES (
            %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
        )
        ON CONFLICT (attempt_id) DO UPDATE SET
            run_id = EXCLUDED.run_id,
            retry_of_attempt_id = EXCLUDED.retry_of_attempt_id,
            replay_of_attempt_id = EXCLUDED.replay_of_attempt_id,
            lease_json = EXCLUDED.lease_json,
            worker_id = EXCLUDED.worker_id,
            runtime_host = EXCLUDED.runtime_host,
            started_at = EXCLUDED.started_at,
            heartbeat_at = EXCLUDED.heartbeat_at,
            completed_at = EXCLUDED.completed_at,
            status = EXCLUDED.status,
            error = EXCLUDED.error,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("run_id") or ""),
        str(record.get("retry_of_attempt_id") or ""),
        str(record.get("replay_of_attempt_id") or ""),
        json.dumps(record.get("lease") or {}),
        str(record.get("worker_id") or ""),
        str(record.get("runtime_host") or ""),
        _as_datetime(record.get("started_at")),
        _as_datetime(record.get("heartbeat_at")),
        _as_datetime(record.get("completed_at")),
        str(record.get("status") or "running"),
        str(record.get("error") or ""),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
    )
    return await _execute(query, params)


async def list_run_attempt_records(run_id: str, *, limit: int | None = 10) -> list[dict[str, Any]]:
    query = """
        SELECT
            attempt_id,
            run_id,
            retry_of_attempt_id,
            replay_of_attempt_id,
            lease_json,
            worker_id,
            runtime_host,
            started_at,
            heartbeat_at,
            completed_at,
            status,
            error,
            metadata_json,
            created_at
        FROM runs.run_attempts
        WHERE run_id = %s
        ORDER BY created_at DESC, attempt_id DESC
    """
    params: list[Any] = [run_id]
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_run_attempt_record(row) for row in rows]


async def list_run_attempt_records_for_runs(
    run_ids: list[str],
    *,
    limit_per_run: int | None = 10,
) -> dict[str, list[dict[str, Any]]]:
    normalized_run_ids = [str(run_id).strip() for run_id in run_ids if str(run_id).strip()]
    if not normalized_run_ids:
        return {}

    query = """
        SELECT
            attempt_id,
            run_id,
            retry_of_attempt_id,
            replay_of_attempt_id,
            lease_json,
            worker_id,
            runtime_host,
            started_at,
            heartbeat_at,
            completed_at,
            status,
            error,
            metadata_json,
            created_at
        FROM (
            SELECT
                attempt_id,
                run_id,
                retry_of_attempt_id,
                replay_of_attempt_id,
                lease_json,
                worker_id,
                runtime_host,
                started_at,
                heartbeat_at,
                completed_at,
                status,
                error,
                metadata_json,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY run_id
                    ORDER BY created_at DESC, attempt_id DESC
                ) AS row_num
            FROM runs.run_attempts
            WHERE run_id = ANY(%s)
        ) ranked_attempts
    """
    params: list[Any] = [normalized_run_ids]
    if limit_per_run is not None:
        query += " WHERE row_num <= %s"
        params.append(max(int(limit_per_run), 0))
    query += " ORDER BY run_id ASC, created_at DESC, attempt_id DESC"

    rows = await _fetch_all(query, tuple(params))
    grouped: dict[str, list[dict[str, Any]]] = {run_id: [] for run_id in normalized_run_ids}
    for row in rows:
        record = _row_to_run_attempt_record(row)
        grouped.setdefault(record["run_id"], []).append(record)
    return grouped


async def replace_run_step_records(run_id: str, attempt_id: str, steps: list[dict[str, Any]]) -> bool:
    if not await ensure_durable_state_schema():
        return False
    try:
        async with _open_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM runs.run_steps WHERE attempt_id = %s", (attempt_id,))
                for step in steps:
                    await cur.execute(
                        """
                        INSERT INTO runs.run_steps (
                            step_id,
                            attempt_id,
                            run_id,
                            step_key,
                            kind,
                            seq,
                            status,
                            input_ref,
                            output_ref,
                            checkpoint_ref,
                            detail_json,
                            started_at,
                            completed_at,
                            created_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
                        )
                        """,
                        (
                            str(step.get("id") or ""),
                            attempt_id,
                            run_id,
                            str(step.get("step_key") or ""),
                            str(step.get("kind") or ""),
                            int(step.get("seq") or 0),
                            str(step.get("status") or "completed"),
                            str(step.get("input_ref") or ""),
                            str(step.get("output_ref") or ""),
                            str(step.get("checkpoint_ref") or ""),
                            json.dumps(step.get("detail") or {}),
                            _as_datetime(step.get("started_at")),
                            _as_datetime(step.get("completed_at")),
                            _as_datetime(step.get("created_at")) or datetime.now(timezone.utc),
                        ),
                    )
        return True
    except Exception as exc:
        logger.warning("Durable-state run-step replacement failed: %s", exc)
        return False


async def list_run_step_records(
    *,
    run_id: str = "",
    attempt_id: str = "",
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            step_id,
            attempt_id,
            run_id,
            step_key,
            kind,
            seq,
            status,
            input_ref,
            output_ref,
            checkpoint_ref,
            detail_json,
            started_at,
            completed_at,
            created_at
        FROM runs.run_steps
    """
    clauses: list[str] = []
    params: list[Any] = []
    if run_id:
        clauses.append("run_id = %s")
        params.append(run_id)
    if attempt_id:
        clauses.append("attempt_id = %s")
        params.append(attempt_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at ASC, seq ASC, step_id ASC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_run_step_record(row) for row in rows]


async def list_run_step_records_for_runs(
    run_ids: list[str],
    *,
    limit_per_run: int | None = 100,
) -> dict[str, list[dict[str, Any]]]:
    normalized_run_ids = [str(run_id).strip() for run_id in run_ids if str(run_id).strip()]
    if not normalized_run_ids:
        return {}

    query = """
        SELECT
            step_id,
            attempt_id,
            run_id,
            step_key,
            kind,
            seq,
            status,
            input_ref,
            output_ref,
            checkpoint_ref,
            detail_json,
            started_at,
            completed_at,
            created_at
        FROM (
            SELECT
                step_id,
                attempt_id,
                run_id,
                step_key,
                kind,
                seq,
                status,
                input_ref,
                output_ref,
                checkpoint_ref,
                detail_json,
                started_at,
                completed_at,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY run_id
                    ORDER BY created_at ASC, seq ASC, step_id ASC
                ) AS row_num
            FROM runs.run_steps
            WHERE run_id = ANY(%s)
        ) ranked_steps
    """
    params: list[Any] = [normalized_run_ids]
    if limit_per_run is not None:
        query += " WHERE row_num <= %s"
        params.append(max(int(limit_per_run), 0))
    query += " ORDER BY run_id ASC, created_at ASC, seq ASC, step_id ASC"

    rows = await _fetch_all(query, tuple(params))
    grouped: dict[str, list[dict[str, Any]]] = {run_id: [] for run_id in normalized_run_ids}
    for row in rows:
        record = _row_to_run_step_record(row)
        grouped.setdefault(record["run_id"], []).append(record)
    return grouped


async def upsert_approval_request_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO audit.approval_requests (
            approval_id,
            related_run_id,
            related_attempt_id,
            related_task_id,
            requested_action,
            privilege_class,
            reason,
            status,
            requested_at,
            decided_at,
            decided_by,
            metadata_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (approval_id) DO UPDATE SET
            related_run_id = EXCLUDED.related_run_id,
            related_attempt_id = EXCLUDED.related_attempt_id,
            related_task_id = EXCLUDED.related_task_id,
            requested_action = EXCLUDED.requested_action,
            privilege_class = EXCLUDED.privilege_class,
            reason = EXCLUDED.reason,
            status = EXCLUDED.status,
            requested_at = EXCLUDED.requested_at,
            decided_at = EXCLUDED.decided_at,
            decided_by = EXCLUDED.decided_by,
            metadata_json = EXCLUDED.metadata_json
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("related_run_id") or ""),
        str(record.get("related_attempt_id") or ""),
        str(record.get("related_task_id") or ""),
        str(record.get("requested_action") or ""),
        str(record.get("privilege_class") or "operator"),
        str(record.get("reason") or ""),
        str(record.get("status") or "pending"),
        _as_datetime(record.get("requested_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("decided_at")),
        str(record.get("decided_by") or ""),
        json.dumps(record.get("metadata") or {}),
    )
    return await _execute(query, params)


async def list_approval_request_records(*, status: str = "", limit: int | None = 50) -> list[dict[str, Any]]:
    query = """
        SELECT
            approval_id,
            related_run_id,
            related_attempt_id,
            related_task_id,
            requested_action,
            privilege_class,
            reason,
            status,
            requested_at,
            decided_at,
            decided_by,
            metadata_json
        FROM audit.approval_requests
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY requested_at DESC, approval_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_approval_request_record(row) for row in rows]


async def list_approval_request_records_for_runs(run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    normalized_run_ids = [str(run_id).strip() for run_id in run_ids if str(run_id).strip()]
    if not normalized_run_ids:
        return {}

    rows = await _fetch_all(
        """
        SELECT
            approval_id,
            related_run_id,
            related_attempt_id,
            related_task_id,
            requested_action,
            privilege_class,
            reason,
            status,
            requested_at,
            decided_at,
            decided_by,
            metadata_json
        FROM audit.approval_requests
        WHERE related_run_id = ANY(%s)
        ORDER BY related_run_id ASC, requested_at DESC, approval_id DESC
        """,
        (normalized_run_ids,),
    )
    grouped: dict[str, list[dict[str, Any]]] = {run_id: [] for run_id in normalized_run_ids}
    for row in rows:
        record = _row_to_approval_request_record(row)
        grouped.setdefault(record["related_run_id"], []).append(record)
    return grouped


async def fetch_approval_request_record(approval_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            approval_id,
            related_run_id,
            related_attempt_id,
            related_task_id,
            requested_action,
            privilege_class,
            reason,
            status,
            requested_at,
            decided_at,
            decided_by,
            metadata_json
        FROM audit.approval_requests
        WHERE approval_id = %s
        """,
        (approval_id,),
    )
    if not rows:
        return None
    return _row_to_approval_request_record(rows[0])


async def get_approval_request_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT status, COUNT(*)::integer AS count
        FROM audit.approval_requests
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {"total": sum(by_status.values()), "by_status": by_status}


async def sync_task_execution_projection(task_record: dict[str, Any]) -> bool:
    metadata = dict(task_record.get("metadata") or {})
    lease = dict(task_record.get("lease") or {})
    run_id = str(metadata.get("execution_run_id") or task_record.get("id") or "")
    if not run_id:
        return False

    attempt_id = str(metadata.get("attempt_id") or f"{run_id}:attempt:{int(task_record.get('retry_count') or 0)}")
    backlog_id = str(metadata.get("backlog_id") or "")
    run_record = {
        "id": run_id,
        "task_id": str(task_record.get("id") or ""),
        "backlog_id": backlog_id,
        "request_fingerprint": str(metadata.get("request_fingerprint") or task_record.get("id") or ""),
        "parent_run_id": str(metadata.get("parent_run_id") or task_record.get("parent_task_id") or ""),
        "agent_id": str(task_record.get("agent") or ""),
        "workload_class": str(metadata.get("work_class") or task_record.get("source") or ""),
        "provider_lane": str(lease.get("provider") or task_record.get("assigned_runtime") or ""),
        "runtime_lane": str(task_record.get("lane") or task_record.get("agent") or ""),
        "policy_class": str(metadata.get("policy_class") or lease.get("privacy") or ""),
        "status": str(task_record.get("status") or "pending"),
        "summary": str(task_record.get("result") or task_record.get("error") or task_record.get("prompt") or "")[:400],
        "artifact_refs": metadata.get("artifact_refs") if isinstance(metadata.get("artifact_refs"), list) else [],
        "metadata": metadata,
        "created_at": task_record.get("created_at"),
        "updated_at": task_record.get("updated_at"),
        "completed_at": task_record.get("completed_at"),
    }
    attempt_record = {
        "id": attempt_id,
        "run_id": run_id,
        "retry_of_attempt_id": str(metadata.get("retry_of_attempt_id") or ""),
        "replay_of_attempt_id": str(metadata.get("replay_of_attempt_id") or ""),
        "lease": lease,
        "worker_id": str(task_record.get("agent") or ""),
        "runtime_host": str(metadata.get("runtime_host") or task_record.get("assigned_runtime") or ""),
        "started_at": task_record.get("started_at"),
        "heartbeat_at": task_record.get("last_heartbeat"),
        "completed_at": task_record.get("completed_at"),
        "status": str(task_record.get("status") or "running"),
        "error": str(task_record.get("error") or ""),
        "metadata": metadata,
        "created_at": task_record.get("started_at") or task_record.get("created_at"),
    }
    steps: list[dict[str, Any]] = []
    for seq, raw_step in enumerate(task_record.get("steps") or []):
        if not isinstance(raw_step, dict):
            continue
        steps.append(
            {
                "id": str(raw_step.get("id") or f"{attempt_id}:step:{seq}"),
                "step_key": str(raw_step.get("step_key") or raw_step.get("tool_name") or raw_step.get("type") or f"step-{seq}"),
                "kind": str(raw_step.get("type") or raw_step.get("kind") or "step"),
                "seq": int(raw_step.get("index") or raw_step.get("seq") or seq),
                "status": str(raw_step.get("status") or "completed"),
                "input_ref": str(raw_step.get("input_ref") or ""),
                "output_ref": str(raw_step.get("output_ref") or ""),
                "checkpoint_ref": str(raw_step.get("checkpoint_ref") or ""),
                "detail": raw_step,
                "started_at": raw_step.get("started_at") or task_record.get("started_at"),
                "completed_at": raw_step.get("completed_at") or task_record.get("updated_at"),
                "created_at": raw_step.get("created_at") or task_record.get("started_at") or task_record.get("created_at"),
            }
        )

    if not await upsert_execution_run_record(run_record):
        return False
    await upsert_run_attempt_record(attempt_record)
    await replace_run_step_records(run_id, attempt_id, steps)

    approval_status = ""
    if str(task_record.get("status") or "") == "pending_approval":
        approval_status = "pending"
    elif bool(metadata.get("approval_rejected")):
        approval_status = "rejected"
    elif bool(metadata.get("approval_decided")):
        approval_status = "approved"
    if approval_status:
        await upsert_approval_request_record(
            {
                "id": str(metadata.get("approval_request_id") or f"approval:{task_record.get('id') or run_id}"),
                "related_run_id": run_id,
                "related_attempt_id": attempt_id,
                "related_task_id": str(task_record.get("id") or ""),
                "requested_action": str(metadata.get("approval_action") or "approve_task"),
                "privilege_class": str(metadata.get("approval_privilege_class") or "admin"),
                "reason": str(metadata.get("governor_decision") or metadata.get("approval_reason") or "Task requires operator approval"),
                "status": approval_status,
                "requested_at": metadata.get("approval_requested_at") or task_record.get("updated_at") or task_record.get("created_at"),
                "decided_at": metadata.get("approval_decided_at") if approval_status != "pending" else 0.0,
                "decided_by": str(metadata.get("approval_decided_by") or ""),
                "metadata": {"task_status": str(task_record.get("status") or ""), **metadata},
            }
        )
    return True
