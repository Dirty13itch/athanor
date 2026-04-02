from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .durable_state import (
    _as_datetime,
    _as_json_value,
    _as_timestamp,
    _execute,
    _fetch_all,
)


def _row_to_idea_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("idea_id") or ""),
        "title": str(row.get("title") or ""),
        "note": str(row.get("note") or ""),
        "tags": _as_json_value(row.get("tags_json"), default=[]),
        "source": str(row.get("source") or "operator"),
        "confidence": float(row.get("confidence") or 0.5),
        "energy_class": str(row.get("energy_class") or "focused"),
        "scope_guess": str(row.get("scope_guess") or "global"),
        "status": str(row.get("status") or "seed"),
        "next_review_at": _as_timestamp(row.get("next_review_at")),
        "promoted_project_id": str(row.get("promoted_project_id") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


def _row_to_backlog_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("backlog_id") or ""),
        "title": str(row.get("title") or ""),
        "prompt": str(row.get("prompt") or ""),
        "owner_agent": str(row.get("owner_agent") or ""),
        "support_agents": _as_json_value(row.get("support_agents_json"), default=[]),
        "scope_type": str(row.get("scope_type") or "global"),
        "scope_id": str(row.get("scope_id") or "athanor"),
        "work_class": str(row.get("work_class") or "project_build"),
        "priority": int(row.get("priority") or 3),
        "status": str(row.get("status") or "captured"),
        "approval_mode": str(row.get("approval_mode") or "none"),
        "dispatch_policy": str(row.get("dispatch_policy") or "planner_eligible"),
        "preconditions": _as_json_value(row.get("preconditions_json"), default=[]),
        "blocking_reason": str(row.get("blocking_reason") or ""),
        "linked_goal_ids": _as_json_value(row.get("linked_goal_ids_json"), default=[]),
        "linked_todo_ids": _as_json_value(row.get("linked_todo_ids_json"), default=[]),
        "linked_idea_id": str(row.get("linked_idea_id") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_by": str(row.get("created_by") or "operator"),
        "origin": str(row.get("origin") or "operator"),
        "ready_at": _as_timestamp(row.get("ready_at")),
        "scheduled_for": _as_timestamp(row.get("scheduled_for")),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
    }


async def upsert_idea_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO work.idea_garden_items (
            idea_id,
            title,
            note,
            tags_json,
            source,
            confidence,
            energy_class,
            scope_guess,
            status,
            next_review_at,
            promoted_project_id,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        ON CONFLICT (idea_id) DO UPDATE SET
            title = EXCLUDED.title,
            note = EXCLUDED.note,
            tags_json = EXCLUDED.tags_json,
            source = EXCLUDED.source,
            confidence = EXCLUDED.confidence,
            energy_class = EXCLUDED.energy_class,
            scope_guess = EXCLUDED.scope_guess,
            status = EXCLUDED.status,
            next_review_at = EXCLUDED.next_review_at,
            promoted_project_id = EXCLUDED.promoted_project_id,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("title") or ""),
        str(record.get("note") or ""),
        json.dumps(record.get("tags") or []),
        str(record.get("source") or "operator"),
        float(record.get("confidence") or 0.5),
        str(record.get("energy_class") or "focused"),
        str(record.get("scope_guess") or "global"),
        str(record.get("status") or "seed"),
        _as_datetime(record.get("next_review_at")),
        str(record.get("promoted_project_id") or ""),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
    )
    return await _execute(query, params)


async def fetch_idea_record(idea_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            idea_id,
            title,
            note,
            tags_json,
            source,
            confidence,
            energy_class,
            scope_guess,
            status,
            next_review_at,
            promoted_project_id,
            metadata_json,
            created_at,
            updated_at
        FROM work.idea_garden_items
        WHERE idea_id = %s
        """,
        (idea_id,),
    )
    if not rows:
        return None
    return _row_to_idea_record(rows[0])


async def list_idea_records(*, status: str = "", limit: int | None = 50) -> list[dict[str, Any]]:
    query = """
        SELECT
            idea_id,
            title,
            note,
            tags_json,
            source,
            confidence,
            energy_class,
            scope_guess,
            status,
            next_review_at,
            promoted_project_id,
            metadata_json,
            created_at,
            updated_at
        FROM work.idea_garden_items
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC, idea_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_idea_record(row) for row in rows]


async def get_idea_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT status, COUNT(*)::integer AS count
        FROM work.idea_garden_items
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {"total": sum(by_status.values()), "by_status": by_status}


async def upsert_backlog_record(record: dict[str, Any]) -> bool:
    query = """
        INSERT INTO work.agent_backlog (
            backlog_id,
            title,
            prompt,
            owner_agent,
            support_agents_json,
            scope_type,
            scope_id,
            work_class,
            priority,
            status,
            approval_mode,
            dispatch_policy,
            preconditions_json,
            blocking_reason,
            linked_goal_ids_json,
            linked_todo_ids_json,
            linked_idea_id,
            metadata_json,
            created_by,
            origin,
            ready_at,
            scheduled_for,
            created_at,
            updated_at,
            completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (backlog_id) DO UPDATE SET
            title = EXCLUDED.title,
            prompt = EXCLUDED.prompt,
            owner_agent = EXCLUDED.owner_agent,
            support_agents_json = EXCLUDED.support_agents_json,
            scope_type = EXCLUDED.scope_type,
            scope_id = EXCLUDED.scope_id,
            work_class = EXCLUDED.work_class,
            priority = EXCLUDED.priority,
            status = EXCLUDED.status,
            approval_mode = EXCLUDED.approval_mode,
            dispatch_policy = EXCLUDED.dispatch_policy,
            preconditions_json = EXCLUDED.preconditions_json,
            blocking_reason = EXCLUDED.blocking_reason,
            linked_goal_ids_json = EXCLUDED.linked_goal_ids_json,
            linked_todo_ids_json = EXCLUDED.linked_todo_ids_json,
            linked_idea_id = EXCLUDED.linked_idea_id,
            metadata_json = EXCLUDED.metadata_json,
            created_by = EXCLUDED.created_by,
            origin = EXCLUDED.origin,
            ready_at = EXCLUDED.ready_at,
            scheduled_for = EXCLUDED.scheduled_for,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            completed_at = EXCLUDED.completed_at
    """
    params = (
        str(record.get("id") or ""),
        str(record.get("title") or ""),
        str(record.get("prompt") or ""),
        str(record.get("owner_agent") or ""),
        json.dumps(record.get("support_agents") or []),
        str(record.get("scope_type") or "global"),
        str(record.get("scope_id") or "athanor"),
        str(record.get("work_class") or "project_build"),
        int(record.get("priority") or 3),
        str(record.get("status") or "captured"),
        str(record.get("approval_mode") or "none"),
        str(record.get("dispatch_policy") or "planner_eligible"),
        json.dumps(record.get("preconditions") or []),
        str(record.get("blocking_reason") or ""),
        json.dumps(record.get("linked_goal_ids") or []),
        json.dumps(record.get("linked_todo_ids") or []),
        str(record.get("linked_idea_id") or ""),
        json.dumps(record.get("metadata") or {}),
        str(record.get("created_by") or "operator"),
        str(record.get("origin") or "operator"),
        _as_datetime(record.get("ready_at")),
        _as_datetime(record.get("scheduled_for")),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("updated_at")) or datetime.now(timezone.utc),
        _as_datetime(record.get("completed_at")),
    )
    return await _execute(query, params)


async def fetch_backlog_record(backlog_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            backlog_id,
            title,
            prompt,
            owner_agent,
            support_agents_json,
            scope_type,
            scope_id,
            work_class,
            priority,
            status,
            approval_mode,
            dispatch_policy,
            preconditions_json,
            blocking_reason,
            linked_goal_ids_json,
            linked_todo_ids_json,
            linked_idea_id,
            metadata_json,
            created_by,
            origin,
            ready_at,
            scheduled_for,
            created_at,
            updated_at,
            completed_at
        FROM work.agent_backlog
        WHERE backlog_id = %s
        """,
        (backlog_id,),
    )
    if not rows:
        return None
    return _row_to_backlog_record(rows[0])


async def list_backlog_records(
    *,
    status: str = "",
    owner_agent: str = "",
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            backlog_id,
            title,
            prompt,
            owner_agent,
            support_agents_json,
            scope_type,
            scope_id,
            work_class,
            priority,
            status,
            approval_mode,
            dispatch_policy,
            preconditions_json,
            blocking_reason,
            linked_goal_ids_json,
            linked_todo_ids_json,
            linked_idea_id,
            metadata_json,
            created_by,
            origin,
            ready_at,
            scheduled_for,
            created_at,
            updated_at,
            completed_at
        FROM work.agent_backlog
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if owner_agent:
        clauses.append("owner_agent = %s")
        params.append(owner_agent)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY priority DESC, updated_at DESC, backlog_id DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(max(int(limit), 0))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_backlog_record(row) for row in rows]


async def get_backlog_stats() -> dict[str, Any]:
    rows = await _fetch_all(
        """
        SELECT status, COUNT(*)::integer AS count
        FROM work.agent_backlog
        GROUP BY status
        """
    )
    by_status = {str(row.get("status") or ""): int(row.get("count") or 0) for row in rows}
    return {"total": sum(by_status.values()), "by_status": by_status}
