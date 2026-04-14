from __future__ import annotations

import asyncio
import importlib
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

_SCHEMA_READY = False
_SCHEMA_ATTEMPTED = False
_SCHEMA_LOCK = asyncio.Lock()
_LAST_DURABLE_STATE_STATUS: dict[str, object] = {}
_RUNTIME_FAILURE_BACKOFF_SECONDS = 30.0
_RUNTIME_FAILURE_UNTIL = 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_bootstrap_sql_path() -> Path:
    target_parts = ("sql", "bootstrap_durable_state.sql")
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return candidate
    return Path("/workspace/projects/agents/src/athanor_agents/sql/bootstrap_durable_state.sql")


def durable_state_sql_path() -> Path:
    return _default_bootstrap_sql_path()


def _set_durable_state_status(
    mode: str,
    *,
    configured: bool,
    available: bool,
    schema_ready: bool,
    reason: str | None = None,
    last_bootstrap_at: str | None = None,
) -> None:
    global _LAST_DURABLE_STATE_STATUS
    _LAST_DURABLE_STATE_STATUS = {
        "mode": mode,
        "configured": configured,
        "available": available,
        "schema_ready": schema_ready,
        "reason": reason,
        "bootstrap_sql_path": str(durable_state_sql_path()),
        "last_updated_at": _utc_now(),
        "last_bootstrap_at": last_bootstrap_at,
    }


def get_durable_state_status() -> dict[str, object]:
    if not _LAST_DURABLE_STATE_STATUS:
        configured = bool(str(settings.postgres_url or "").strip())
        _set_durable_state_status(
            "uninitialized",
            configured=configured,
            available=False,
            schema_ready=False,
            reason="Durable state has not been initialized yet",
        )
    return dict(_LAST_DURABLE_STATE_STATUS)


def reset_durable_state_cache() -> None:
    global _SCHEMA_READY, _SCHEMA_ATTEMPTED, _RUNTIME_FAILURE_UNTIL
    _SCHEMA_READY = False
    _SCHEMA_ATTEMPTED = False
    _RUNTIME_FAILURE_UNTIL = 0.0
    configured = bool(str(settings.postgres_url or "").strip())
    _set_durable_state_status(
        "uninitialized",
        configured=configured,
        available=False,
        schema_ready=False,
        reason="Durable state cache reset",
    )


def _load_psycopg_module():
    return importlib.import_module("psycopg")


def _last_bootstrap_at() -> str | None:
    return str(get_durable_state_status().get("last_bootstrap_at") or "").strip() or None


def _runtime_failure_circuit_open() -> bool:
    return _RUNTIME_FAILURE_UNTIL > time.monotonic()


def _mark_runtime_failure(exc: Exception) -> None:
    global _RUNTIME_FAILURE_UNTIL
    _RUNTIME_FAILURE_UNTIL = time.monotonic() + _RUNTIME_FAILURE_BACKOFF_SECONDS
    _set_durable_state_status(
        "degraded",
        configured=bool(str(settings.postgres_url or "").strip()),
        available=False,
        schema_ready=_SCHEMA_READY,
        reason=f"Durable-state runtime unavailable: {exc}",
        last_bootstrap_at=_last_bootstrap_at(),
    )


def _mark_runtime_ready() -> None:
    global _RUNTIME_FAILURE_UNTIL
    _RUNTIME_FAILURE_UNTIL = 0.0
    if not _SCHEMA_READY:
        return
    _set_durable_state_status(
        "ready",
        configured=True,
        available=True,
        schema_ready=True,
        reason=None,
        last_bootstrap_at=_last_bootstrap_at() or _utc_now(),
    )


def _load_bootstrap_statements() -> list[str]:
    text = durable_state_sql_path().read_text(encoding="utf-8")
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False

    for char in text:
        current.append(char)
        if char == "'":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []

    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


@asynccontextmanager
async def _open_connection():
    postgres_url = str(settings.postgres_url or "").strip()
    psycopg = _load_psycopg_module()
    conn = await psycopg.AsyncConnection.connect(postgres_url, autocommit=True)
    try:
        yield conn
    finally:
        await conn.close()


async def ensure_durable_state_schema(*, force: bool = False) -> bool:
    global _SCHEMA_READY, _SCHEMA_ATTEMPTED

    postgres_url = str(settings.postgres_url or "").strip()
    if not postgres_url:
        _set_durable_state_status(
            "disabled",
            configured=False,
            available=False,
            schema_ready=False,
            reason="ATHANOR_POSTGRES_URL not configured",
        )
        return False

    async with _SCHEMA_LOCK:
        if _SCHEMA_READY and not force:
            _set_durable_state_status(
                "ready",
                configured=True,
                available=True,
                schema_ready=True,
                reason=None,
                last_bootstrap_at=str(get_durable_state_status().get("last_bootstrap_at") or _utc_now()),
            )
            return True
        if _SCHEMA_ATTEMPTED and not force:
            return bool(_SCHEMA_READY)

        try:
            statements = _load_bootstrap_statements()
        except Exception as exc:
            logger.exception("Failed to load durable-state bootstrap SQL")
            _SCHEMA_ATTEMPTED = True
            _SCHEMA_READY = False
            _set_durable_state_status(
                "schema_error",
                configured=True,
                available=False,
                schema_ready=False,
                reason=f"Failed to load bootstrap SQL: {exc}",
            )
            return False

        try:
            async with _open_connection() as conn:
                async with conn.cursor() as cur:
                    for statement in statements:
                        await cur.execute(statement)
        except ModuleNotFoundError:
            logger.warning("psycopg is not installed; durable state remains disabled")
            _SCHEMA_ATTEMPTED = True
            _SCHEMA_READY = False
            _set_durable_state_status(
                "module_missing",
                configured=True,
                available=False,
                schema_ready=False,
                reason="psycopg is not installed",
            )
            return False
        except Exception as exc:
            logger.exception("Failed to bootstrap durable-state schema")
            _SCHEMA_ATTEMPTED = True
            _SCHEMA_READY = False
            _set_durable_state_status(
                "schema_error",
                configured=True,
                available=True,
                schema_ready=False,
                reason=f"Schema bootstrap failed: {exc}",
            )
            return False

        _SCHEMA_ATTEMPTED = True
        _SCHEMA_READY = True
        _set_durable_state_status(
            "ready",
            configured=True,
            available=True,
            schema_ready=True,
            reason=None,
            last_bootstrap_at=_utc_now(),
        )
        logger.info("Durable-state Postgres schema is ready")
        return True


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            pass
        else:
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    return datetime.fromtimestamp(numeric, tz=timezone.utc)


def _as_timestamp(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_json_value(value: Any, *, default: Any) -> Any:
    if value in ("", None):
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _row_to_task_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("task_id") or ""),
        "agent": str(row.get("agent") or ""),
        "prompt": str(row.get("prompt") or ""),
        "priority": str(row.get("priority") or "normal"),
        "status": str(row.get("status") or "pending"),
        "source": str(row.get("source") or "task_api"),
        "lane": str(row.get("lane") or ""),
        "result": str(row.get("result") or ""),
        "error": str(row.get("error") or ""),
        "created_at": _as_timestamp(row.get("created_at")),
        "started_at": _as_timestamp(row.get("started_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "last_heartbeat": _as_timestamp(row.get("last_heartbeat")),
        "lease": _as_json_value(row.get("lease_json"), default={}),
        "retry_lineage": _as_json_value(row.get("retry_lineage_json"), default=[]),
        "assigned_runtime": str(row.get("assigned_runtime") or ""),
        "session_id": str(row.get("session_id") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "parent_task_id": str(row.get("parent_task_id") or ""),
        "retry_count": int(row.get("retry_count") or 0),
        "previous_error": str(row.get("previous_error") or ""),
        "steps": _as_json_value(row.get("steps_json"), default=[]),
    }


def _row_to_goal_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("goal_id") or ""),
        "text": str(row.get("goal_text") or ""),
        "agent": str(row.get("agent") or "global"),
        "priority": str(row.get("priority") or "normal"),
        "created_at": _as_timestamp(row.get("created_at")),
        "active": bool(row.get("active")),
    }


def _row_to_operator_todo_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("todo_id") or ""),
        "title": str(row.get("title") or ""),
        "description": str(row.get("description") or ""),
        "category": str(row.get("category") or "ops"),
        "scope_type": str(row.get("scope_type") or "global"),
        "scope_id": str(row.get("scope_id") or "athanor"),
        "priority": int(row.get("priority") or 3),
        "status": str(row.get("status") or "open"),
        "energy_class": str(row.get("energy_class") or "focused"),
        "origin": str(row.get("origin") or "operator"),
        "created_by": str(row.get("created_by") or "operator"),
        "due_at": _as_timestamp(row.get("due_at")),
        "linked_goal_ids": _as_json_value(row.get("linked_goal_ids_json"), default=[]),
        "linked_inbox_ids": _as_json_value(row.get("linked_inbox_ids_json"), default=[]),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
    }


def _row_to_operator_inbox_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("inbox_id") or ""),
        "kind": str(row.get("kind") or "operator_attention"),
        "severity": int(row.get("severity") or 1),
        "status": str(row.get("status") or "new"),
        "source": str(row.get("source") or "operator"),
        "title": str(row.get("title") or ""),
        "description": str(row.get("description") or ""),
        "requires_decision": bool(row.get("requires_decision")),
        "decision_type": str(row.get("decision_type") or ""),
        "related_run_id": str(row.get("related_run_id") or ""),
        "related_task_id": str(row.get("related_task_id") or ""),
        "related_project_id": str(row.get("related_project_id") or ""),
        "related_domain_id": str(row.get("related_domain_id") or ""),
        "snooze_until": _as_timestamp(row.get("snooze_until")),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "resolved_at": _as_timestamp(row.get("resolved_at")),
    }


def _row_to_workplan_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    plan = _as_json_value(row.get("plan_json"), default={})
    if isinstance(plan, dict):
        plan.setdefault("plan_id", str(row.get("plan_id") or ""))
        plan.setdefault("focus", str(row.get("focus") or ""))
        plan.setdefault("generated_at", _as_timestamp(row.get("generated_at")))
        plan.setdefault("task_count", int(row.get("task_count") or 0))
    return plan


async def _fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if _runtime_failure_circuit_open():
        return []
    if not await ensure_durable_state_schema():
        return []

    try:
        async with _open_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()
                columns = [str(column.name) for column in (cur.description or [])]
    except Exception as exc:
        logger.warning("Durable-state query failed: %s", exc)
        _mark_runtime_failure(exc)
        return []

    _mark_runtime_ready()
    return [dict(zip(columns, row, strict=False)) for row in rows]


async def _execute(query: str, params: tuple[Any, ...] = ()) -> bool:
    if _runtime_failure_circuit_open():
        return False
    if not await ensure_durable_state_schema():
        return False

    try:
        async with _open_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
        _mark_runtime_ready()
        return True
    except Exception as exc:
        logger.warning("Durable-state write failed: %s", exc)
        _mark_runtime_failure(exc)
        return False


async def upsert_task_snapshot(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO runs.task_snapshots (
            task_id,
            agent,
            prompt,
            priority,
            status,
            source,
            lane,
            result,
            error,
            created_at,
            started_at,
            completed_at,
            updated_at,
            last_heartbeat,
            lease_json,
            retry_lineage_json,
            assigned_runtime,
            session_id,
            metadata_json,
            parent_task_id,
            retry_count,
            previous_error,
            steps_json
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb
        )
        ON CONFLICT (task_id) DO UPDATE SET
            agent = EXCLUDED.agent,
            prompt = EXCLUDED.prompt,
            priority = EXCLUDED.priority,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            lane = EXCLUDED.lane,
            result = EXCLUDED.result,
            error = EXCLUDED.error,
            created_at = EXCLUDED.created_at,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            updated_at = EXCLUDED.updated_at,
            last_heartbeat = EXCLUDED.last_heartbeat,
            lease_json = EXCLUDED.lease_json,
            retry_lineage_json = EXCLUDED.retry_lineage_json,
            assigned_runtime = EXCLUDED.assigned_runtime,
            session_id = EXCLUDED.session_id,
            metadata_json = EXCLUDED.metadata_json,
            parent_task_id = EXCLUDED.parent_task_id,
            retry_count = EXCLUDED.retry_count,
            previous_error = EXCLUDED.previous_error,
            steps_json = EXCLUDED.steps_json
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("agent") or ""),
        str(record.get("prompt") or ""),
        str(record.get("priority") or "normal"),
        str(record.get("status") or "pending"),
        str(record.get("source") or "task_api"),
        str(record.get("lane") or ""),
        str(record.get("result") or ""),
        str(record.get("error") or ""),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("started_at")),
        _as_datetime(record.get("completed_at")),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("last_heartbeat")),
        json.dumps(record.get("lease") or {}),
        json.dumps(record.get("retry_lineage") or []),
        str(record.get("assigned_runtime") or ""),
        str(record.get("session_id") or ""),
        json.dumps(record.get("metadata") or {}),
        str(record.get("parent_task_id") or ""),
        int(record.get("retry_count") or 0),
        str(record.get("previous_error") or ""),
        json.dumps(record.get("steps") or []),
    )
    return await _execute(query, params)


async def fetch_task_snapshot(task_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            task_id,
            agent,
            prompt,
            priority,
            status,
            source,
            lane,
            result,
            error,
            created_at,
            started_at,
            completed_at,
            updated_at,
            last_heartbeat,
            lease_json,
            retry_lineage_json,
            assigned_runtime,
            session_id,
            metadata_json,
            parent_task_id,
            retry_count,
            previous_error,
            steps_json
        FROM runs.task_snapshots
        WHERE task_id = %s
        """,
        (task_id,),
    )
    if not rows:
        return None
    return _row_to_task_record(rows[0])


async def list_task_snapshots(
    *,
    statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    agent: str = "",
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    normalized_statuses = [str(item).strip() for item in (statuses or []) if str(item).strip()]

    if normalized_statuses:
        clauses.append("status = ANY(%s)")
        params.append(normalized_statuses)
    if agent:
        clauses.append("agent = %s")
        params.append(agent)

    query = """
        SELECT
            task_id,
            agent,
            prompt,
            priority,
            status,
            source,
            lane,
            result,
            error,
            created_at,
            started_at,
            completed_at,
            updated_at,
            last_heartbeat,
            lease_json,
            retry_lineage_json,
            assigned_runtime,
            session_id,
            metadata_json,
            parent_task_id,
            retry_count,
            previous_error,
            steps_json
        FROM runs.task_snapshots
    """
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC, task_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))

    rows = await _fetch_all(query, tuple(params))
    return [_row_to_task_record(row) for row in rows]


async def get_task_snapshot_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT
            status,
            COUNT(*)::integer AS count
        FROM runs.task_snapshots
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
    }


async def upsert_goal_record(goal: dict[str, Any]) -> bool:
    active = bool(goal.get("active", True))
    query = """
        INSERT INTO work.goals (
            goal_id,
            goal_text,
            agent,
            priority,
            created_at,
            active,
            deleted_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (goal_id) DO UPDATE SET
            goal_text = EXCLUDED.goal_text,
            agent = EXCLUDED.agent,
            priority = EXCLUDED.priority,
            created_at = EXCLUDED.created_at,
            active = EXCLUDED.active,
            deleted_at = EXCLUDED.deleted_at
    """
    params = (
        str(goal.get("id") or ""),
        str(goal.get("text") or ""),
        str(goal.get("agent") or "global"),
        str(goal.get("priority") or "normal"),
        _as_datetime(goal.get("created_at")) or datetime.now(timezone.utc),
        active,
        None if active else datetime.now(timezone.utc),
    )
    return await _execute(query, params)


async def list_goal_records(*, agent: str = "", active_only: bool = True) -> list[dict[str, Any]]:
    query = """
        SELECT
            goal_id,
            goal_text,
            agent,
            priority,
            created_at,
            active,
            deleted_at
        FROM work.goals
    """
    clauses: list[str] = []
    params: list[Any] = []
    if active_only:
        clauses.append("active = TRUE")
    if agent:
        clauses.append("(agent = %s OR agent = 'global')")
        params.append(agent)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, goal_id DESC"
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_goal_record(row) for row in rows]


async def soft_delete_goal_record(goal_id: str) -> bool:
    query = """
        UPDATE work.goals
        SET active = FALSE, deleted_at = now()
        WHERE goal_id = %s
    """
    return await _execute(query, (goal_id,))


async def upsert_operator_todo_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO work.operator_todos (
            todo_id,
            title,
            description,
            category,
            scope_type,
            scope_id,
            priority,
            status,
            energy_class,
            origin,
            created_by,
            due_at,
            linked_goal_ids_json,
            linked_inbox_ids_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (todo_id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            scope_type = EXCLUDED.scope_type,
            scope_id = EXCLUDED.scope_id,
            priority = EXCLUDED.priority,
            status = EXCLUDED.status,
            energy_class = EXCLUDED.energy_class,
            origin = EXCLUDED.origin,
            created_by = EXCLUDED.created_by,
            due_at = EXCLUDED.due_at,
            linked_goal_ids_json = EXCLUDED.linked_goal_ids_json,
            linked_inbox_ids_json = EXCLUDED.linked_inbox_ids_json,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            completed_at = EXCLUDED.completed_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("title") or ""),
        str(record.get("description") or ""),
        str(record.get("category") or "ops"),
        str(record.get("scope_type") or "global"),
        str(record.get("scope_id") or "athanor"),
        int(record.get("priority") or 3),
        str(record.get("status") or "open"),
        str(record.get("energy_class") or "focused"),
        str(record.get("origin") or "operator"),
        str(record.get("created_by") or "operator"),
        _as_datetime(record.get("due_at")),
        json.dumps(record.get("linked_goal_ids") or []),
        json.dumps(record.get("linked_inbox_ids") or []),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("completed_at")),
    )
    return await _execute(query, params)


async def fetch_operator_todo_record(todo_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            todo_id,
            title,
            description,
            category,
            scope_type,
            scope_id,
            priority,
            status,
            energy_class,
            origin,
            created_by,
            due_at,
            linked_goal_ids_json,
            linked_inbox_ids_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM work.operator_todos
        WHERE todo_id = %s
        """,
        (todo_id,),
    )
    if not rows:
        return None
    return _row_to_operator_todo_record(rows[0])


async def list_operator_todo_records(*, status: str = "", limit: int | None = 50) -> list[dict[str, Any]]:
    query = """
        SELECT
            todo_id,
            title,
            description,
            category,
            scope_type,
            scope_id,
            priority,
            status,
            energy_class,
            origin,
            created_by,
            due_at,
            linked_goal_ids_json,
            linked_inbox_ids_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM work.operator_todos
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY priority DESC, updated_at DESC, todo_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_operator_todo_record(row) for row in rows]


async def get_operator_todo_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT
            status,
            COUNT(*)::integer AS count
        FROM work.operator_todos
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
    }


async def upsert_operator_inbox_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO work.operator_inbox (
            inbox_id,
            kind,
            severity,
            status,
            source,
            title,
            description,
            requires_decision,
            decision_type,
            related_run_id,
            related_task_id,
            related_project_id,
            related_domain_id,
            snooze_until,
            metadata_json,
            created_at,
            updated_at,
            resolved_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (inbox_id) DO UPDATE SET
            kind = EXCLUDED.kind,
            severity = EXCLUDED.severity,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            requires_decision = EXCLUDED.requires_decision,
            decision_type = EXCLUDED.decision_type,
            related_run_id = EXCLUDED.related_run_id,
            related_task_id = EXCLUDED.related_task_id,
            related_project_id = EXCLUDED.related_project_id,
            related_domain_id = EXCLUDED.related_domain_id,
            snooze_until = EXCLUDED.snooze_until,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            resolved_at = EXCLUDED.resolved_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("kind") or "operator_attention"),
        int(record.get("severity") or 1),
        str(record.get("status") or "new"),
        str(record.get("source") or "operator"),
        str(record.get("title") or ""),
        str(record.get("description") or ""),
        bool(record.get("requires_decision", False)),
        str(record.get("decision_type") or ""),
        str(record.get("related_run_id") or ""),
        str(record.get("related_task_id") or ""),
        str(record.get("related_project_id") or ""),
        str(record.get("related_domain_id") or ""),
        _as_datetime(record.get("snooze_until")),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("resolved_at")),
    )
    return await _execute(query, params)


async def fetch_operator_inbox_record(inbox_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            inbox_id,
            kind,
            severity,
            status,
            source,
            title,
            description,
            requires_decision,
            decision_type,
            related_run_id,
            related_task_id,
            related_project_id,
            related_domain_id,
            snooze_until,
            metadata_json,
            created_at,
            updated_at,
            resolved_at
        FROM work.operator_inbox
        WHERE inbox_id = %s
        """,
        (inbox_id,),
    )
    if not rows:
        return None
    return _row_to_operator_inbox_record(rows[0])


async def list_operator_inbox_records(*, status: str = "", limit: int | None = 50) -> list[dict[str, Any]]:
    query = """
        SELECT
            inbox_id,
            kind,
            severity,
            status,
            source,
            title,
            description,
            requires_decision,
            decision_type,
            related_run_id,
            related_task_id,
            related_project_id,
            related_domain_id,
            snooze_until,
            metadata_json,
            created_at,
            updated_at,
            resolved_at
        FROM work.operator_inbox
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY severity DESC, created_at DESC, inbox_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_operator_inbox_record(row) for row in rows]


async def get_operator_inbox_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT
            status,
            COUNT(*)::integer AS count
        FROM work.operator_inbox
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
    }


async def store_workplan_snapshot(plan: dict[str, Any]) -> bool:
    query = """
        INSERT INTO work.workplan_snapshots (
            plan_id,
            focus,
            generated_at,
            task_count,
            plan_json
        )
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (plan_id) DO UPDATE SET
            focus = EXCLUDED.focus,
            generated_at = EXCLUDED.generated_at,
            task_count = EXCLUDED.task_count,
            plan_json = EXCLUDED.plan_json
    """
    params = (
        str(plan.get("plan_id") or ""),
        str(plan.get("focus") or ""),
        _as_datetime(plan.get("generated_at")) or datetime.now(timezone.utc),
        int(plan.get("task_count") or 0),
        json.dumps(plan),
    )
    return await _execute(query, params)


async def fetch_latest_workplan_snapshot() -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            plan_id,
            focus,
            generated_at,
            task_count,
            plan_json
        FROM work.workplan_snapshots
        ORDER BY generated_at DESC, plan_id DESC
        LIMIT 1
        """
    )
    if not rows:
        return None
    return _row_to_workplan_snapshot(rows[0])


async def list_workplan_snapshots(*, limit: int | None = 10) -> list[dict[str, Any]]:
    query = """
        SELECT
            plan_id,
            focus,
            generated_at,
            task_count,
            plan_json
        FROM work.workplan_snapshots
        ORDER BY generated_at DESC, plan_id DESC
    """
    params: list[Any] = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_workplan_snapshot(row) for row in rows]
