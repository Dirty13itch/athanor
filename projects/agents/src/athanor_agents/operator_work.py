from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .durable_state import (
    fetch_task_snapshot,
    fetch_operator_inbox_record,
    fetch_operator_todo_record,
    get_operator_inbox_stats,
    get_operator_todo_stats,
    list_operator_inbox_records,
    list_operator_todo_records,
    upsert_operator_inbox_record,
    upsert_operator_todo_record,
)
from .execution_state import (
    fetch_approval_request_record,
    get_approval_request_stats,
    get_execution_run_stats,
    list_approval_request_records,
    list_approval_request_records_for_runs,
    list_execution_run_records,
    list_run_attempt_records_for_runs,
    list_run_step_records_for_runs,
)
from .operator_state import (
    fetch_backlog_record,
    fetch_idea_record,
    get_backlog_stats,
    get_idea_stats,
    list_backlog_records,
    list_idea_records,
    upsert_backlog_record,
    upsert_idea_record,
)

TODO_STATUSES = {"open", "ready", "blocked", "delegated", "waiting", "done", "cancelled", "someday"}
INBOX_STATUSES = {"new", "acknowledged", "snoozed", "resolved", "converted"}
IDEA_STATUSES = {"seed", "sprout", "candidate", "promoted", "discarded"}
BACKLOG_STATUSES = {"captured", "triaged", "ready", "scheduled", "running", "waiting_approval", "blocked", "completed", "failed", "archived"}


def _now_ts() -> float:
    return time.time()


def _normalize_due_at(value: str | float | int | None) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return 0.0


def _todo_id() -> str:
    return f"todo-{uuid.uuid4().hex[:8]}"


def _inbox_id() -> str:
    return f"inbox-{uuid.uuid4().hex[:8]}"


def _idea_id() -> str:
    return f"idea-{uuid.uuid4().hex[:8]}"


def _backlog_id() -> str:
    return f"backlog-{uuid.uuid4().hex[:8]}"


def _priority_to_task_priority(priority: int) -> str:
    if priority >= 5:
        return "critical"
    if priority >= 4:
        return "high"
    if priority <= 2:
        return "low"
    return "normal"


def _claim_id_from_dispatch_reason(reason: str) -> str:
    prefix = "Auto-dispatched governed dispatch claim "
    normalized = str(reason or "").strip()
    if not normalized.startswith(prefix):
        return ""
    return normalized[len(prefix) :].strip()


GOVERNED_DISPATCH_TASK_CLASS_DEFAULTS = {
    "coding-agent": "async_backlog_execution",
    "research-agent": "repo_wide_audit",
}

GOVERNED_DISPATCH_WORKLOAD_ALIASES = {
    "multi_file_implementation": "coding_implementation",
    "async_backlog_execution": "coding_implementation",
    "repo_wide_audit": "repo_audit",
    "private_internal_automation": "private_automation",
}


def _governed_dispatch_task_profile(
    *,
    owner_agent: str,
    task_class: str | None = None,
    workload_class: str | None = None,
) -> dict[str, str]:
    normalized_task_class = str(task_class or "").strip()
    if not normalized_task_class or normalized_task_class == "private_automation":
        normalized_task_class = GOVERNED_DISPATCH_TASK_CLASS_DEFAULTS.get(
            str(owner_agent or "").strip(),
            "async_backlog_execution",
        )

    normalized_workload_class = str(workload_class or "").strip()
    if not normalized_workload_class or normalized_workload_class == "private_automation":
        normalized_workload_class = GOVERNED_DISPATCH_WORKLOAD_ALIASES.get(
            normalized_task_class,
            "coding_implementation",
        )

    return {
        "task_class": normalized_task_class,
        "workload_class": normalized_workload_class,
    }


async def list_todos(*, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    return await list_operator_todo_records(status=status, limit=limit)


async def get_todo(todo_id: str) -> dict[str, Any] | None:
    return await fetch_operator_todo_record(todo_id)


async def create_todo(
    *,
    title: str,
    description: str = "",
    category: str = "ops",
    scope_type: str = "global",
    scope_id: str = "athanor",
    priority: int = 3,
    energy_class: str = "focused",
    due_at: str | float | int | None = None,
    linked_goal_ids: list[str] | None = None,
    linked_inbox_ids: list[str] | None = None,
    origin: str = "operator",
    created_by: str = "operator",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ts()
    record = {
        "id": _todo_id(),
        "title": title,
        "description": description,
        "category": category,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "priority": int(priority),
        "status": "open",
        "energy_class": energy_class,
        "origin": origin,
        "created_by": created_by,
        "due_at": _normalize_due_at(due_at),
        "linked_goal_ids": linked_goal_ids or [],
        "linked_inbox_ids": linked_inbox_ids or [],
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
        "completed_at": 0.0,
    }
    await upsert_operator_todo_record(record)
    return record


async def transition_todo(todo_id: str, *, status: str, note: str = "") -> dict[str, Any] | None:
    if status not in TODO_STATUSES:
        raise ValueError(f"Invalid todo status: {status}")

    record = await fetch_operator_todo_record(todo_id)
    if not record:
        return None

    metadata = dict(record.get("metadata") or {})
    if note:
        metadata["last_note"] = note

    record["status"] = status
    record["metadata"] = metadata
    record["updated_at"] = _now_ts()
    record["completed_at"] = record["updated_at"] if status == "done" else 0.0
    await upsert_operator_todo_record(record)
    return record


async def todo_stats() -> dict[str, Any]:
    return await get_operator_todo_stats()


async def list_inbox(*, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    return await list_operator_inbox_records(status=status, limit=limit)


async def get_inbox_item(inbox_id: str) -> dict[str, Any] | None:
    return await fetch_operator_inbox_record(inbox_id)


async def create_inbox_item(
    *,
    kind: str,
    title: str,
    description: str = "",
    severity: int = 1,
    source: str = "operator",
    requires_decision: bool = False,
    decision_type: str = "",
    related_run_id: str = "",
    related_task_id: str = "",
    related_project_id: str = "",
    related_domain_id: str = "",
    snooze_until: str | float | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ts()
    record = {
        "id": _inbox_id(),
        "kind": kind,
        "severity": int(severity),
        "status": "new",
        "source": source,
        "title": title,
        "description": description,
        "requires_decision": bool(requires_decision),
        "decision_type": decision_type,
        "related_run_id": related_run_id,
        "related_task_id": related_task_id,
        "related_project_id": related_project_id,
        "related_domain_id": related_domain_id,
        "snooze_until": _normalize_due_at(snooze_until),
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
        "resolved_at": 0.0,
    }
    await upsert_operator_inbox_record(record)
    return record


async def acknowledge_inbox_item(inbox_id: str) -> dict[str, Any] | None:
    record = await fetch_operator_inbox_record(inbox_id)
    if not record:
        return None
    record["status"] = "acknowledged"
    record["updated_at"] = _now_ts()
    await upsert_operator_inbox_record(record)
    return record


async def snooze_inbox_item(inbox_id: str, *, until: str | float | int | None = None) -> dict[str, Any] | None:
    record = await fetch_operator_inbox_record(inbox_id)
    if not record:
        return None
    snooze_until = _normalize_due_at(until)
    if snooze_until <= 0:
        snooze_until = _now_ts() + 3600
    record["status"] = "snoozed"
    record["snooze_until"] = snooze_until
    record["updated_at"] = _now_ts()
    await upsert_operator_inbox_record(record)
    return record


async def resolve_inbox_item(inbox_id: str, *, note: str = "") -> dict[str, Any] | None:
    record = await fetch_operator_inbox_record(inbox_id)
    if not record:
        return None
    metadata = dict(record.get("metadata") or {})
    if note:
        metadata["resolution_note"] = note
    record["metadata"] = metadata
    record["status"] = "resolved"
    record["updated_at"] = _now_ts()
    record["resolved_at"] = record["updated_at"]
    await upsert_operator_inbox_record(record)
    return record


async def convert_inbox_item_to_todo(
    inbox_id: str,
    *,
    category: str = "decision",
    priority: int = 3,
    energy_class: str = "quick",
) -> dict[str, Any] | None:
    record = await fetch_operator_inbox_record(inbox_id)
    if not record:
        return None

    todo = await create_todo(
        title=record.get("title") or "Inbox follow-up",
        description=record.get("description") or "",
        category=category,
        scope_type="domain" if record.get("related_domain_id") else "global",
        scope_id=record.get("related_domain_id") or "athanor",
        priority=priority,
        energy_class=energy_class,
        linked_inbox_ids=[inbox_id],
        origin="operator_inbox",
        created_by="operator",
        metadata={
            "converted_from_inbox_id": inbox_id,
            "source_kind": record.get("kind", ""),
        },
    )

    metadata = dict(record.get("metadata") or {})
    metadata["converted_todo_id"] = todo["id"]
    record["metadata"] = metadata
    record["status"] = "converted"
    record["updated_at"] = _now_ts()
    record["resolved_at"] = record["updated_at"]
    await upsert_operator_inbox_record(record)
    return {"inbox": record, "todo": todo}


async def inbox_stats() -> dict[str, Any]:
    return await get_operator_inbox_stats()


async def list_ideas(*, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    return await list_idea_records(status=status, limit=limit)


async def get_idea(idea_id: str) -> dict[str, Any] | None:
    return await fetch_idea_record(idea_id)


async def create_idea(
    *,
    title: str,
    note: str = "",
    tags: list[str] | None = None,
    source: str = "operator",
    confidence: float = 0.5,
    energy_class: str = "focused",
    scope_guess: str = "global",
    next_review_at: str | float | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ts()
    record = {
        "id": _idea_id(),
        "title": title,
        "note": note,
        "tags": tags or [],
        "source": source,
        "confidence": float(confidence),
        "energy_class": energy_class,
        "scope_guess": scope_guess,
        "status": "seed",
        "next_review_at": _normalize_due_at(next_review_at),
        "promoted_project_id": "",
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    await upsert_idea_record(record)
    return record


async def promote_idea(
    idea_id: str,
    *,
    target: str = "backlog",
    owner_agent: str = "coding-agent",
    project_id: str = "",
) -> dict[str, Any] | None:
    idea = await fetch_idea_record(idea_id)
    if not idea:
        return None

    payload: dict[str, Any] = {"idea": idea, "target": target}
    metadata = dict(idea.get("metadata") or {})
    metadata["promotion_target"] = target

    if target == "todo":
        todo = await create_todo(
            title=idea.get("title") or "Promoted idea",
            description=idea.get("note") or "",
            category="research",
            scope_type="global",
            scope_id="athanor",
            priority=3,
            energy_class=str(idea.get("energy_class") or "focused"),
            origin="idea_garden",
            created_by="operator",
            metadata={"promoted_from_idea_id": idea_id},
        )
        metadata["promoted_todo_id"] = todo["id"]
        payload["todo"] = todo
    elif target == "project":
        if not project_id:
            project_id = str(idea.get("promoted_project_id") or f"project-{idea_id}")
        idea["promoted_project_id"] = project_id
        metadata["promoted_project_id"] = project_id
        payload["project"] = {"id": project_id}
    else:
        backlog = await create_backlog_item(
            title=idea.get("title") or "Promoted idea",
            prompt=idea.get("note") or idea.get("title") or "",
            owner_agent=owner_agent,
            scope_type="global",
            scope_id="athanor",
            work_class="research",
            priority=3,
            linked_idea_id=idea_id,
            metadata={"promoted_from_idea_id": idea_id},
        )
        metadata["promoted_backlog_id"] = backlog["id"]
        payload["backlog"] = backlog

    idea["metadata"] = metadata
    idea["status"] = "promoted"
    idea["updated_at"] = _now_ts()
    await upsert_idea_record(idea)
    payload["idea"] = idea
    return payload


async def idea_stats() -> dict[str, Any]:
    return await get_idea_stats()


async def list_backlog(*, status: str = "", owner_agent: str = "", limit: int = 50) -> list[dict[str, Any]]:
    normalized_status = ""
    if status and status.strip().lower() != "all":
        normalized_status = status
    return await list_backlog_records(status=normalized_status, owner_agent=owner_agent, limit=limit)


async def get_backlog_item(backlog_id: str) -> dict[str, Any] | None:
    return await fetch_backlog_record(backlog_id)


async def create_backlog_item(
    *,
    title: str,
    prompt: str,
    owner_agent: str,
    support_agents: list[str] | None = None,
    scope_type: str = "global",
    scope_id: str = "athanor",
    work_class: str = "project_build",
    priority: int = 3,
    approval_mode: str = "none",
    dispatch_policy: str = "planner_eligible",
    preconditions: list[str] | None = None,
    linked_goal_ids: list[str] | None = None,
    linked_todo_ids: list[str] | None = None,
    linked_idea_id: str = "",
    created_by: str = "operator",
    origin: str = "operator",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now_ts()
    record = {
        "id": _backlog_id(),
        "title": title,
        "prompt": prompt,
        "owner_agent": owner_agent,
        "support_agents": support_agents or [],
        "scope_type": scope_type,
        "scope_id": scope_id,
        "work_class": work_class,
        "priority": int(priority),
        "status": "captured",
        "approval_mode": approval_mode,
        "dispatch_policy": dispatch_policy,
        "preconditions": preconditions or [],
        "blocking_reason": "",
        "linked_goal_ids": linked_goal_ids or [],
        "linked_todo_ids": linked_todo_ids or [],
        "linked_idea_id": linked_idea_id,
        "metadata": metadata or {},
        "created_by": created_by,
        "origin": origin,
        "ready_at": 0.0,
        "scheduled_for": 0.0,
        "created_at": now,
        "updated_at": now,
        "completed_at": 0.0,
    }
    await upsert_backlog_record(record)
    return record


async def transition_backlog_item(
    backlog_id: str,
    *,
    status: str,
    note: str = "",
    blocking_reason: str = "",
) -> dict[str, Any] | None:
    if status not in BACKLOG_STATUSES:
        raise ValueError(f"Invalid backlog status: {status}")

    record = await fetch_backlog_record(backlog_id)
    if not record:
        return None

    metadata = dict(record.get("metadata") or {})
    if note:
        metadata["last_note"] = note

    record["status"] = status
    record["blocking_reason"] = blocking_reason if status == "blocked" else ""
    record["metadata"] = metadata
    record["updated_at"] = _now_ts()
    if status == "ready" and not record.get("ready_at"):
        record["ready_at"] = record["updated_at"]
    if status in {"completed", "failed", "archived"}:
        record["completed_at"] = record["updated_at"]
    await upsert_backlog_record(record)
    return record


async def dispatch_backlog_item(
    backlog_id: str,
    *,
    lane_override: str = "",
    reason: str = "",
) -> dict[str, Any] | None:
    from .tasks import submit_governed_task

    record = await fetch_backlog_record(backlog_id)
    if not record:
        return None

    metadata = dict(record.get("metadata") or {})
    if str(metadata.get("materialization_source") or "").strip() == "governed_dispatch_state":
        governed_profile = _governed_dispatch_task_profile(
            owner_agent=str(record.get("owner_agent") or "").strip(),
            task_class=str(metadata.get("task_class") or "").strip() or None,
            workload_class=str(metadata.get("workload_class") or "").strip() or None,
        )
        metadata.setdefault("_autonomy_managed", True)
        metadata.setdefault("_autonomy_source", "pipeline")
        metadata["task_class"] = governed_profile["task_class"]
        metadata["workload_class"] = governed_profile["workload_class"]
        claim_id = _claim_id_from_dispatch_reason(reason)
        if claim_id:
            metadata["claim_id"] = claim_id

    submission_metadata = {
        **metadata,
        "backlog_id": backlog_id,
        "work_class": str(record.get("work_class") or ""),
        "scope_type": str(record.get("scope_type") or "global"),
        "scope_id": str(record.get("scope_id") or "athanor"),
        "lane_override": lane_override,
        "dispatch_reason": reason,
    }
    for transient_key in (
        "latest_task_id",
        "latest_run_id",
        "last_dispatch_reason",
        "governor_reason",
        "governor_level",
    ):
        submission_metadata.pop(transient_key, None)

    submission = await submit_governed_task(
        agent=str(record.get("owner_agent") or ""),
        prompt=str(record.get("prompt") or record.get("title") or ""),
        priority=_priority_to_task_priority(int(record.get("priority") or 3)),
        metadata=submission_metadata,
        source="operator_backlog",
    )

    task = submission.task.to_dict()
    metadata.update(
        {
            "latest_task_id": task.get("id", ""),
            "latest_run_id": task.get("id", ""),
            "last_dispatch_reason": reason,
            "governor_reason": submission.decision.reason,
            "governor_level": submission.decision.autonomy_level,
        }
    )
    record["metadata"] = metadata
    record["scheduled_for"] = _now_ts()
    record["updated_at"] = record["scheduled_for"]
    record["status"] = {
        "pending_approval": "waiting_approval",
        "pending": "scheduled",
        "running": "running",
    }.get(str(task.get("status") or "pending"), "scheduled")
    await upsert_backlog_record(record)
    return {"backlog": record, "task": task, "governor": {"reason": submission.decision.reason, "level": submission.decision.autonomy_level}}


async def backlog_stats() -> dict[str, Any]:
    return await get_backlog_stats()


async def list_runs(*, status: str = "", agent: str = "", limit: int = 50) -> list[dict[str, Any]]:
    runs = await list_execution_run_records(status=status, agent=agent, limit=limit)
    if not runs:
        return []

    run_ids = [str(run.get("id") or "").strip() for run in runs if str(run.get("id") or "").strip()]
    attempts_by_run, steps_by_run, approvals_by_run = await asyncio.gather(
        list_run_attempt_records_for_runs(run_ids, limit_per_run=3),
        list_run_step_records_for_runs(run_ids, limit_per_run=20),
        list_approval_request_records_for_runs(run_ids),
    )
    enriched: list[dict[str, Any]] = []
    for run in runs:
        run_id = str(run.get("id") or "")
        attempts = attempts_by_run.get(run_id, [])
        latest_attempt = attempts[0] if attempts else None
        steps = steps_by_run.get(run_id, [])
        run_approvals = approvals_by_run.get(run_id, [])
        enriched.append(
            {
                **run,
                "attempts": attempts,
                "latest_attempt": latest_attempt,
                "step_count": len(steps),
                "steps_preview": steps[:5],
                "approvals": run_approvals,
                "approval_pending": any(approval.get("status") == "pending" for approval in run_approvals),
            }
        )
    return enriched


async def run_stats() -> dict[str, Any]:
    return await get_execution_run_stats()


async def _enrich_approval_record(approval: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(approval)
    task_id = str(approval.get("related_task_id") or "")
    if not task_id:
        return enriched

    task = await fetch_task_snapshot(task_id)
    if not task:
        return enriched

    enriched["task_prompt"] = str(task.get("prompt") or "")
    enriched["task_agent_id"] = str(task.get("agent") or "")
    enriched["task_priority"] = str(task.get("priority") or "")
    enriched["task_status"] = str(task.get("status") or "")
    enriched["task_created_at"] = float(task.get("created_at") or 0.0)
    return enriched


async def list_approvals(*, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    approvals = await list_approval_request_records(status=status, limit=limit)
    return [await _enrich_approval_record(approval) for approval in approvals]


async def get_approval(approval_id: str) -> dict[str, Any] | None:
    approval = await fetch_approval_request_record(approval_id)
    if not approval:
        return None
    return await _enrich_approval_record(approval)


async def approval_stats() -> dict[str, Any]:
    return await get_approval_request_stats()


async def digest_summary() -> dict[str, Any]:
    from .routes.digests import load_latest_digest_snapshot

    digest = await load_latest_digest_snapshot()
    return {
        "type": str(digest.get("type") or "auto"),
        "generated_at": str(digest.get("generated_at") or ""),
        "period": str(digest.get("period") or "24h"),
        "summary": str(digest.get("summary") or ""),
        "task_count": int(digest.get("task_count") or 0),
        "completed_count": int(digest.get("completed_count") or 0),
        "failed_count": int(digest.get("failed_count") or 0),
        "recent_completions": list(digest.get("recent_completions") or [])[:5],
        "recent_failures": list(digest.get("recent_failures") or [])[:5],
    }


async def project_summary(*, stalled_limit: int = 8) -> dict[str, Any]:
    from .routes.planning import list_stalled_project_records

    stalled = await list_stalled_project_records()
    return {
        "stalled_total": len(stalled),
        "stalled_preview": stalled[:stalled_limit],
        "threshold_hours": 24,
    }


async def output_summary(*, limit: int = 5) -> dict[str, Any]:
    from .routes.planning import list_output_artifacts

    outputs = await list_output_artifacts()
    return {
        "total": len(outputs),
        "recent": outputs[:limit],
    }


async def pattern_summary(*, pattern_limit: int = 5, recommendation_limit: int = 3) -> dict[str, Any]:
    from .patterns import get_latest_report

    report = await get_latest_report()
    if not isinstance(report, dict):
        return {
            "available": False,
            "generated_at": "",
            "warning_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "patterns": [],
            "recommendations": [],
        }

    patterns = [item for item in list(report.get("patterns") or []) if isinstance(item, dict)]
    warnings = [item for item in patterns if str(item.get("severity") or "") in {"high", "medium"}]
    return {
        "available": True,
        "generated_at": str(report.get("timestamp") or ""),
        "warning_count": len(warnings),
        "high_count": sum(1 for item in warnings if str(item.get("severity") or "") == "high"),
        "medium_count": sum(1 for item in warnings if str(item.get("severity") or "") == "medium"),
        "patterns": warnings[:pattern_limit],
        "recommendations": [
            str(item)
            for item in list(report.get("recommendations") or [])[:recommendation_limit]
            if str(item).strip()
        ],
    }
