from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .autonomous_queue import (
    backlog_sort_key,
    canonicalize_backlog_record,
    is_v1_queue_family,
    record_dispatch_event,
    redispatch_block_reason,
    validate_backlog_transition,
)
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
MATERIALIZED_BACKLOG_TERMINAL_STATUSES = {"completed", "archived"}


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


def _task_priority_to_backlog_priority(priority: str) -> int:
    normalized = str(priority or "").strip().lower()
    if normalized == "critical":
        return 5
    if normalized == "high":
        return 4
    if normalized == "low":
        return 2
    return 3


def _window_start(interval_seconds: int, *, now_ts: float | None = None) -> int:
    effective_now = int(now_ts or _now_ts())
    if interval_seconds <= 0:
        interval_seconds = 3600
    return effective_now - (effective_now % interval_seconds)


def _scheduled_source_ref(job_id: str, interval_seconds: int, *, now_ts: float | None = None) -> str:
    return f"schedule:{job_id}:{_window_start(interval_seconds, now_ts=now_ts)}"


def _research_source_ref(job_id: str, interval_seconds: int, *, now_ts: float | None = None) -> str:
    return f"research:{job_id}:{_window_start(interval_seconds, now_ts=now_ts)}"


def _pipeline_starvation_source_ref(project_id: str, *, now_ts: float | None = None) -> str:
    return f"pipeline-starvation:{project_id}:{_window_start(24 * 3600, now_ts=now_ts)}"


def _improvement_source_ref(proposal_id: str) -> str:
    return f"improvement:{str(proposal_id or '').strip()}"


def _pipeline_spec_fingerprint(*, agent: str, prompt: str, priority: str, metadata: dict[str, Any], family: str) -> str:
    payload = {
        "agent": str(agent or "").strip(),
        "prompt": str(prompt or "").strip(),
        "priority": str(priority or "normal").strip(),
        "family": str(family or "").strip(),
        "project_id": str(metadata.get("project_id") or "").strip(),
        "task_class": str(metadata.get("task_class") or "").strip(),
        "workload_class": str(metadata.get("workload_class") or "").strip(),
        "source": str(metadata.get("source") or "").strip(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def _materialization_payload(
    *,
    backlog: dict[str, Any],
    status: str,
    execution_mode: str = "materialized_to_backlog",
) -> dict[str, Any]:
    normalized_status = str(status or "created").strip() or "created"
    return {
        "status": normalized_status,
        "execution_mode": execution_mode,
        "already_materialized": normalized_status == "refreshed",
        "backlog_id": str(backlog.get("id") or ""),
        "backlog": backlog,
    }


def _resolve_pipeline_queue_family(
    *,
    owner_agent: str,
    metadata: dict[str, Any],
) -> tuple[str, str, str]:
    explicit_family = str(metadata.get("family") or "").strip()
    if explicit_family and is_v1_queue_family(explicit_family):
        task_class = str(metadata.get("task_class") or "").strip()
        workload_class = str(metadata.get("workload_class") or "").strip()
        return explicit_family, task_class, workload_class

    task_class = str(metadata.get("task_class") or "").strip()
    workload_class = str(metadata.get("workload_class") or "").strip()
    if owner_agent in {"coding-agent", "research-agent"}:
        governed_profile = _governed_dispatch_task_profile(
            owner_agent=owner_agent,
            task_class=task_class or None,
            workload_class=workload_class or None,
        )
        task_class = governed_profile["task_class"]
        workload_class = governed_profile["workload_class"]

    candidate = canonicalize_backlog_record(
        {
            "title": str(metadata.get("title") or "").strip() or "Pipeline task spec",
            "prompt": str(metadata.get("prompt") or "").strip(),
            "owner_agent": owner_agent,
            "work_class": workload_class or task_class,
            "approval_mode": str(metadata.get("approval_mode") or "none"),
            "family": explicit_family,
            "metadata": {
                "task_class": task_class,
                "workload_class": workload_class,
            },
        }
    )
    family = str(candidate.get("family") or "").strip()
    if not is_v1_queue_family(family):
        return "", task_class, workload_class
    if owner_agent not in {"coding-agent", "research-agent"} and not explicit_family:
        return "", task_class, workload_class
    return family, task_class, workload_class


async def _find_existing_materialized_backlog(
    *,
    source_ref: str,
    materialization_source: str,
) -> dict[str, Any] | None:
    normalized_source_ref = str(source_ref or "").strip()
    normalized_materialization_source = str(materialization_source or "").strip()
    if not normalized_source_ref or not normalized_materialization_source:
        return None

    backlog = await list_backlog_records(status="", owner_agent="", limit=None)
    for item in backlog:
        canonical = canonicalize_backlog_record(item)
        if str(canonical.get("status") or "") in MATERIALIZED_BACKLOG_TERMINAL_STATUSES:
            continue
        if (
            str(canonical.get("source_ref") or "").strip() == normalized_source_ref
            and str(canonical.get("materialization_source") or "").strip() == normalized_materialization_source
        ):
            return canonical
    return None


async def _refresh_existing_materialized_backlog(
    existing: dict[str, Any],
    *,
    title: str,
    prompt: str,
    owner_agent: str,
    scope_type: str,
    scope_id: str,
    work_class: str,
    priority: int,
    approval_mode: str,
    dispatch_policy: str,
    project_id: str,
    family: str,
    source_type: str,
    source_ref: str,
    routing_class: str,
    verification_contract: str,
    closure_rule: str,
    materialization_source: str,
    materialization_reason: str,
    recurrence_program_id: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    refreshed = dict(existing)
    refreshed.update(
        {
            "title": title,
            "prompt": prompt,
            "owner_agent": owner_agent,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "work_class": work_class,
            "priority": int(priority),
            "approval_mode": approval_mode,
            "dispatch_policy": dispatch_policy,
            "family": family,
            "project_id": project_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "routing_class": routing_class,
            "verification_contract": verification_contract,
            "closure_rule": closure_rule,
            "materialization_source": materialization_source,
            "materialization_reason": materialization_reason,
            "recurrence_program_id": recurrence_program_id,
            "updated_at": _now_ts(),
        }
    )
    merged_metadata = dict(existing.get("metadata") or {})
    merged_metadata.update(metadata or {})
    refreshed["metadata"] = merged_metadata
    refreshed = canonicalize_backlog_record(refreshed)
    await upsert_backlog_record(refreshed)
    return refreshed


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


def _governed_dispatch_proof_commands(
    preferred_lane_family: str,
    *,
    autonomous_value_canary_id: str = "",
) -> list[list[str]]:
    lane = str(preferred_lane_family or "").strip()
    if lane in {"validation_and_checkpoint", "publication_freeze"}:
        return [
            [sys.executable, "scripts/validate_platform_contract.py"],
            [sys.executable, "scripts/generate_documentation_index.py", "--check"],
            [sys.executable, "scripts/generate_project_maturity_report.py", "--check"],
            [sys.executable, "scripts/generate_truth_inventory_reports.py"],
            [sys.executable, "scripts/generate_truth_inventory_reports.py", "--check"],
        ]
    if lane == "capacity_truth_repair":
        return [
            [sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
            [sys.executable, "scripts/collect_capacity_telemetry.py"],
            [sys.executable, "scripts/write_quota_truth_snapshot.py"],
        ]
    if lane == "safe_surface_execution":
        canary_id = str(autonomous_value_canary_id or "").strip()
        if canary_id == "dashboard-visible-proof":
            return [[sys.executable, "scripts/run_dashboard_value_proof.py", "--surface", "dashboard_overview"]]
        if canary_id == "builder-front-door-visible-proof":
            return [[sys.executable, "scripts/run_dashboard_value_proof.py", "--surface", "builder_operator_surface"]]
    return []


def _governed_dispatch_proof_environment(preferred_lane_family: str) -> dict[str, str]:
    lane = str(preferred_lane_family or "").strip()
    if lane in {"validation_and_checkpoint", "publication_freeze", "capacity_truth_repair", "safe_surface_execution"}:
        implementation_authority = str(os.environ.get("ATHANOR_IMPLEMENTATION_AUTHORITY") or "/workspace").strip()
        return {
            "ATHANOR_RUNTIME_PROOF_CONTEXT": "1",
            "ATHANOR_RUNTIME_ARTIFACT_ROOT": "/output",
            "ATHANOR_IMPLEMENTATION_AUTHORITY": implementation_authority or "/workspace",
            "ATHANOR_DEVSTACK_ROOT": "/workspace/_external/devstack",
        }
    return {}


def _governed_dispatch_proof_artifact_paths(
    preferred_lane_family: str,
    *,
    deliverable_refs: list[str] | None = None,
) -> list[str]:
    lane = str(preferred_lane_family or "").strip()
    if lane in {"validation_and_checkpoint", "publication_freeze"}:
        return [
            "reports/truth-inventory/steady-state-status.json",
            "reports/truth-inventory/ecosystem-master-plan.json",
            "docs/operations/REPO-ROOTS-REPORT.md",
            "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
            "reports/truth-inventory/surface-owner-matrix.json",
        ]
    if lane == "capacity_truth_repair":
        return [
            "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
            "reports/truth-inventory/capacity-telemetry.json",
            "reports/truth-inventory/quota-truth.json",
        ]
    if lane == "safe_surface_execution":
        return [str(item).strip() for item in list(deliverable_refs or []) if str(item).strip()]
    return []


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
    backlog = await list_backlog_records(status=normalized_status, owner_agent=owner_agent, limit=None)
    ranked = sorted(backlog, key=backlog_sort_key)
    return ranked[: max(int(limit), 0)] if limit is not None else ranked


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
    family: str = "",
    project_id: str = "",
    source_type: str = "",
    source_ref: str = "",
    routing_class: str = "",
    verification_contract: str = "",
    closure_rule: str = "",
    materialization_source: str = "",
    materialization_reason: str = "",
    recurrence_program_id: str = "",
    result_id: str = "",
    review_id: str = "",
    value_class: str = "",
    deliverable_kind: str = "",
    deliverable_refs: list[str] | None = None,
    beneficiary_surface: str = "",
    acceptance_mode: str = "",
    accepted_by: str = "",
    accepted_at: str = "",
    acceptance_proof_refs: list[str] | None = None,
    operator_steered: bool = False,
) -> dict[str, Any]:
    now = _now_ts()
    merged_metadata = dict(metadata or {})
    if family:
        merged_metadata["family"] = family
    if project_id:
        merged_metadata["project_id"] = project_id
    if source_type:
        merged_metadata["source_type"] = source_type
    if source_ref:
        merged_metadata["source_ref"] = source_ref
    if routing_class:
        merged_metadata["routing_class"] = routing_class
    if verification_contract:
        merged_metadata["verification_contract"] = verification_contract
    if closure_rule:
        merged_metadata["closure_rule"] = closure_rule
    if materialization_source:
        merged_metadata["materialization_source"] = materialization_source
    if materialization_reason:
        merged_metadata["materialization_reason"] = materialization_reason
    if recurrence_program_id:
        merged_metadata["recurrence_program_id"] = recurrence_program_id
    if result_id:
        merged_metadata["result_id"] = result_id
    if review_id:
        merged_metadata["review_id"] = review_id
    if value_class:
        merged_metadata["value_class"] = value_class
    if deliverable_kind:
        merged_metadata["deliverable_kind"] = deliverable_kind
    if deliverable_refs:
        merged_metadata["deliverable_refs"] = [str(item).strip() for item in deliverable_refs if str(item).strip()]
    if beneficiary_surface:
        merged_metadata["beneficiary_surface"] = beneficiary_surface
    if acceptance_mode:
        merged_metadata["acceptance_mode"] = acceptance_mode
    if accepted_by:
        merged_metadata["accepted_by"] = accepted_by
    if accepted_at:
        merged_metadata["accepted_at"] = accepted_at
    if acceptance_proof_refs:
        merged_metadata["acceptance_proof_refs"] = [
            str(item).strip() for item in acceptance_proof_refs if str(item).strip()
        ]
    merged_metadata["operator_steered"] = bool(operator_steered)
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
        "family": family,
        "project_id": project_id,
        "source_type": source_type,
        "source_ref": source_ref,
        "routing_class": routing_class,
        "verification_contract": verification_contract,
        "closure_rule": closure_rule,
        "materialization_source": materialization_source,
        "materialization_reason": materialization_reason,
        "recurrence_program_id": recurrence_program_id,
        "result_id": result_id,
        "review_id": review_id,
        "value_class": value_class,
        "deliverable_kind": deliverable_kind,
        "deliverable_refs": [str(item).strip() for item in list(deliverable_refs or []) if str(item).strip()],
        "beneficiary_surface": beneficiary_surface,
        "acceptance_mode": acceptance_mode,
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
        "acceptance_proof_refs": [
            str(item).strip() for item in list(acceptance_proof_refs or []) if str(item).strip()
        ],
        "operator_steered": bool(operator_steered),
        "metadata": merged_metadata,
        "created_by": created_by,
        "origin": origin,
        "ready_at": 0.0,
        "scheduled_for": 0.0,
        "created_at": now,
        "updated_at": now,
        "completed_at": 0.0,
    }
    record = canonicalize_backlog_record(record)
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

    if status == "blocked" and not blocking_reason:
        raise ValueError("blocked backlog items require a machine-readable blocking_reason")
    validate_backlog_transition(record, status=status, blocking_reason=blocking_reason)
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


async def sync_backlog_item_from_task(task_record: dict[str, Any]) -> dict[str, Any] | None:
    metadata = task_record.get("metadata")
    if not isinstance(metadata, dict):
        return None

    backlog_id = str(metadata.get("backlog_id") or "").strip()
    if not backlog_id:
        return None

    record = await fetch_backlog_record(backlog_id)
    if not record:
        return None

    backlog_metadata = dict(record.get("metadata") or {})
    task_id = str(task_record.get("id") or "").strip()
    run_id = str(
        metadata.get("execution_run_id")
        or metadata.get("latest_run_id")
        or metadata.get("run_id")
        or task_id
    ).strip()
    review_id = str(metadata.get("approval_request_id") or backlog_metadata.get("review_id") or "").strip()
    task_status = str(task_record.get("status") or "").strip()
    result_text = str(task_record.get("result") or "").strip()
    error_text = str(task_record.get("error") or "").strip()
    verification_contract = str(record.get("verification_contract") or backlog_metadata.get("verification_contract") or "").strip()
    verification_status = str(metadata.get("verification_status") or "").strip().lower()
    verification_passed = bool(
        metadata.get("verification_passed")
        or verification_status in {"passed", "verified", "green", "success"}
    )
    proof_artifacts = [
        str(item).strip()
        for item in list(metadata.get("proof_artifacts") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    deliverable_refs = [
        str(item).strip()
        for item in list(metadata.get("deliverable_refs") or backlog_metadata.get("deliverable_refs") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    acceptance_proof_refs = [
        str(item).strip()
        for item in list(metadata.get("acceptance_proof_refs") or backlog_metadata.get("acceptance_proof_refs") or [])
        if isinstance(item, str) and str(item).strip()
    ]

    backlog_metadata["latest_task_id"] = task_id
    backlog_metadata["latest_run_id"] = run_id
    if review_id:
        backlog_metadata["review_id"] = review_id
    if proof_artifacts:
        backlog_metadata["proof_artifacts"] = proof_artifacts
    if run_id and result_text:
        backlog_metadata["result_id"] = run_id
    for field in (
        "value_class",
        "deliverable_kind",
        "beneficiary_surface",
        "acceptance_mode",
        "accepted_by",
        "accepted_at",
    ):
        value = str(metadata.get(field) or backlog_metadata.get(field) or "").strip()
        if value:
            backlog_metadata[field] = value
    if deliverable_refs:
        backlog_metadata["deliverable_refs"] = deliverable_refs
    if acceptance_proof_refs:
        backlog_metadata["acceptance_proof_refs"] = acceptance_proof_refs
    if "operator_steered" in metadata or "operator_steered" in backlog_metadata:
        backlog_metadata["operator_steered"] = bool(
            metadata.get("operator_steered", backlog_metadata.get("operator_steered"))
        )
    if task_status == "completed":
        backlog_metadata["verification_passed"] = verification_passed
        backlog_metadata.pop("failure", None)
        backlog_metadata.pop("failure_detail", None)
        backlog_metadata.pop("recovery_posture", None)
        backlog_metadata.pop("blocking_reason", None)
        if verification_passed:
            backlog_metadata["verification_status"] = "passed"
            backlog_metadata["auto_verification_from_task"] = True
            backlog_metadata.pop("verification_pending_reason", None)
        else:
            backlog_metadata.pop("auto_verification_from_task", None)
            if verification_contract:
                backlog_metadata["verification_pending_reason"] = "verification_evidence_missing"
                backlog_metadata["verification_status"] = "needs_review" if review_id else "missing_evidence"
            elif verification_status:
                backlog_metadata["verification_status"] = verification_status
    elif metadata.get("verification_passed") is not None:
        backlog_metadata["verification_passed"] = bool(metadata.get("verification_passed"))
        if backlog_metadata["verification_passed"]:
            backlog_metadata["verification_status"] = "passed"

    if task_status == "pending_approval":
        if review_id:
            record["status"] = "waiting_approval"
            record["review_id"] = review_id
        else:
            record["status"] = "blocked"
            record["blocking_reason"] = "review_evidence_missing"
            backlog_metadata["blocking_reason"] = "review_evidence_missing"
    elif task_status == "completed":
        record["result_id"] = run_id
        backlog_metadata["result_summary"] = result_text
        if verification_contract and not verification_passed:
            if review_id:
                record["status"] = "waiting_approval"
                record["review_id"] = review_id
            else:
                record["status"] = "blocked"
                record["blocking_reason"] = "verification_evidence_missing"
                backlog_metadata["blocking_reason"] = "verification_evidence_missing"
        else:
            record["status"] = "completed"
            record["blocking_reason"] = ""
            record["completed_at"] = float(task_record.get("completed_at") or task_record.get("updated_at") or _now_ts())
    elif task_status == "failed":
        record["status"] = "failed"
        record["result_id"] = run_id
        failure = metadata.get("failure") if isinstance(metadata.get("failure"), dict) else {}
        failure_message = str(failure.get("message") or error_text or "Task execution failed").strip()
        recovery_posture = str(
            metadata.get("recovery_posture")
            or metadata.get("failure_repair")
            or metadata.get("recovery")
            or "operator_repair_required"
        ).strip()
        backlog_metadata["failure"] = failure_message
        backlog_metadata["failure_detail"] = failure_message
        backlog_metadata["recovery_posture"] = recovery_posture
        backlog_metadata["result_summary"] = result_text or failure_message
        record["completed_at"] = float(task_record.get("completed_at") or task_record.get("updated_at") or _now_ts())
    elif task_status == "stale_lease":
        record["status"] = "blocked"
        blocking_reason = str(
            metadata.get("blocking_reason")
            or metadata.get("failure")
            or error_text
            or "stale_lease"
        ).strip()
        record["blocking_reason"] = blocking_reason
        backlog_metadata["blocking_reason"] = blocking_reason
    elif task_status == "running":
        record["status"] = "running"
    elif task_status == "pending":
        record["status"] = "scheduled"

    if record.get("status") not in {"completed", "failed", "archived"}:
        record["completed_at"] = 0.0
    record["metadata"] = backlog_metadata
    record["updated_at"] = float(task_record.get("updated_at") or _now_ts())
    validate_backlog_transition(
        record,
        status=str(record.get("status") or ""),
        blocking_reason=str(record.get("blocking_reason") or ""),
    )
    record = canonicalize_backlog_record(record)
    await upsert_backlog_record(record)
    return record


async def materialize_maintenance_signal(
    *,
    project_id: str,
    title: str,
    prompt: str,
    source_ref: str,
    owner_agent: str,
    recurrence_program_id: str = "",
    approval_mode: str = "none",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scope_type = "project" if project_id else "global"
    scope_id = project_id or "athanor"
    work_class = "maintenance"
    priority = 3
    dispatch_policy = "planner_eligible"
    family = "maintenance"
    source_type = "program_signal"
    routing_class = "private_but_cloud_allowed"
    verification_contract = "maintenance_proof"
    closure_rule = "proof_or_review_required"
    materialization_source = "project_packet_cadence"
    materialization_reason = "Recurring maintenance signal emitted governed queue work."
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source=materialization_source,
    )
    if existing:
        return await _refresh_existing_materialized_backlog(
            existing,
            title=title,
            prompt=prompt,
            owner_agent=owner_agent,
            scope_type=scope_type,
            scope_id=scope_id,
            work_class=work_class,
            priority=priority,
            approval_mode=approval_mode,
            dispatch_policy=dispatch_policy,
            project_id=project_id,
            family=family,
            source_type=source_type,
            source_ref=source_ref,
            routing_class=routing_class,
            verification_contract=verification_contract,
            closure_rule=closure_rule,
            materialization_source=materialization_source,
            materialization_reason=materialization_reason,
            recurrence_program_id=recurrence_program_id,
            metadata=metadata,
        )
    return await create_backlog_item(
        title=title,
        prompt=prompt,
        owner_agent=owner_agent,
        scope_type=scope_type,
        scope_id=scope_id,
        work_class=work_class,
        priority=priority,
        approval_mode=approval_mode,
        dispatch_policy=dispatch_policy,
        family=family,
        project_id=project_id,
        source_type=source_type,
        source_ref=source_ref,
        routing_class=routing_class,
        verification_contract=verification_contract,
        closure_rule=closure_rule,
        materialization_source=materialization_source,
        materialization_reason=materialization_reason,
        recurrence_program_id=recurrence_program_id,
        metadata=metadata,
        origin="system",
        created_by="system",
    )


async def materialize_bootstrap_follow_up(
    *,
    program_id: str,
    slice_id: str,
    family: str,
    title: str,
    prompt: str,
    project_id: str,
    source_ref: str,
    owner_agent: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_metadata = dict(metadata or {})
    merged_metadata.setdefault("bootstrap_program_id", program_id)
    merged_metadata.setdefault("linked_slice_id", slice_id)
    scope_type = "project" if project_id else "global"
    scope_id = project_id or "athanor"
    work_class = "project_bootstrap"
    priority = 3
    approval_mode = "none"
    dispatch_policy = "planner_eligible"
    source_type = "bootstrap_follow_up"
    routing_class = "private_but_cloud_allowed"
    verification_contract = "scaffold_integrity"
    closure_rule = "result_or_review_required"
    materialization_source = "bootstrap_program"
    materialization_reason = "Bootstrap follow-up emitted governed queue work."
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source=materialization_source,
    )
    if existing:
        return await _refresh_existing_materialized_backlog(
            existing,
            title=title,
            prompt=prompt,
            owner_agent=owner_agent,
            scope_type=scope_type,
            scope_id=scope_id,
            work_class=work_class,
            priority=priority,
            approval_mode=approval_mode,
            dispatch_policy=dispatch_policy,
            project_id=project_id,
            family=family,
            source_type=source_type,
            source_ref=source_ref,
            routing_class=routing_class,
            verification_contract=verification_contract,
            closure_rule=closure_rule,
            materialization_source=materialization_source,
            materialization_reason=materialization_reason,
            recurrence_program_id=program_id,
            metadata=merged_metadata,
        )
    return await create_backlog_item(
        title=title,
        prompt=prompt,
        owner_agent=owner_agent,
        scope_type=scope_type,
        scope_id=scope_id,
        work_class=work_class,
        priority=priority,
        approval_mode=approval_mode,
        dispatch_policy=dispatch_policy,
        family=family,
        project_id=project_id,
        source_type=source_type,
        source_ref=source_ref,
        routing_class=routing_class,
        verification_contract=verification_contract,
        closure_rule=closure_rule,
        materialization_source=materialization_source,
        materialization_reason=materialization_reason,
        recurrence_program_id=program_id,
        metadata=merged_metadata,
        origin="bootstrap",
        created_by="bootstrap",
    )


def _improvement_queue_profile(category: str) -> dict[str, str]:
    normalized = str(category or "").strip().lower()
    if normalized in {"prompt", "config"}:
        return {
            "family": "maintenance",
            "owner_agent": "coding-agent",
            "work_class": "maintenance",
            "approval_mode": "none",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "closure_rule": "proof_or_review_required",
        }
    if normalized == "code":
        return {
            "family": "builder",
            "owner_agent": "coding-agent",
            "work_class": "coding_implementation",
            "approval_mode": "none",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
        }
    if normalized in {"routing", "policy", "benchmark", "analysis", "research"}:
        return {
            "family": "research_audit",
            "owner_agent": "research-agent",
            "work_class": "research_synthesis",
            "approval_mode": "none",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "evidence_bundle",
            "closure_rule": "result_or_review_required",
        }
    return {
        "family": "review",
        "owner_agent": "general-assistant",
        "work_class": "approval_review",
        "approval_mode": "none",
        "routing_class": "private_but_cloud_allowed",
        "verification_contract": "review_packet_present",
        "closure_rule": "review_decision_required",
    }


async def materialize_improvement_proposal(
    *,
    proposal_id: str,
    title: str,
    description: str,
    category: str,
    expected_improvement: str,
    benchmark_targets: list[str] | None = None,
    target_files: list[str] | None = None,
    proposed_changes: dict[str, str] | None = None,
    recurrence_program_id: str = "",
) -> dict[str, Any]:
    profile = _improvement_queue_profile(category)
    normalized_proposal_id = str(proposal_id or "").strip() or f"proposal-{uuid.uuid4().hex[:8]}"
    normalized_source_ref = _improvement_source_ref(normalized_proposal_id)
    materialization_source = "self_improvement"
    materialization_reason = "Self-improvement proposal emitted governed queue work."
    prompt = (
        f"{description.strip()}\n\n"
        f"Expected improvement: {str(expected_improvement or '').strip() or 'Improve runtime quality.'}"
    ).strip()
    common_kwargs = dict(
        title=title or f"Improvement proposal {normalized_proposal_id}",
        prompt=prompt,
        owner_agent=profile["owner_agent"],
        scope_type="global",
        scope_id="athanor",
        work_class=profile["work_class"],
        priority=2 if profile["family"] == "review" else 3,
        approval_mode=profile["approval_mode"],
        dispatch_policy="planner_eligible",
        family=profile["family"],
        project_id="",
        source_type="improvement_proposal",
        source_ref=normalized_source_ref,
        routing_class=profile["routing_class"],
        verification_contract=profile["verification_contract"],
        closure_rule=profile["closure_rule"],
        materialization_source=materialization_source,
        materialization_reason=materialization_reason,
        recurrence_program_id=recurrence_program_id,
        metadata={
            "proposal_id": normalized_proposal_id,
            "proposal_category": str(category or "").strip(),
            "expected_improvement": str(expected_improvement or "").strip(),
            "benchmark_targets": list(benchmark_targets or []),
            "target_files": list(target_files or []),
            "proposed_change_count": len(dict(proposed_changes or {})),
            "_autonomy_managed": True,
            "_autonomy_source": "self_improvement",
            "execution_plane": "proposal_only",
        },
    )
    existing = await _find_existing_materialized_backlog(
        source_ref=normalized_source_ref,
        materialization_source=materialization_source,
    )
    if existing:
        backlog = await _refresh_existing_materialized_backlog(existing, **common_kwargs)
        return {
            **_materialization_payload(backlog=backlog, status="refreshed"),
            "family": profile["family"],
            "review_id": str(backlog.get("review_id") or ""),
            "execution_plane": "proposal_only",
            "admission_classification": "proposal_only",
            "admission_reason": "Self-improvement proposals are governed backlog candidates and do not auto-apply in v1.",
        }

    backlog = await create_backlog_item(
        **common_kwargs,
        origin="self_improvement",
        created_by="self_improvement",
    )
    return {
        **_materialization_payload(backlog=backlog, status="created"),
        "family": profile["family"],
        "review_id": str(backlog.get("review_id") or ""),
        "execution_plane": "proposal_only",
        "admission_classification": "proposal_only",
        "admission_reason": "Self-improvement proposals are governed backlog candidates and do not auto-apply in v1.",
    }


async def materialize_scheduled_product_work(
    *,
    job_id: str,
    agent: str,
    prompt: str,
    priority: str,
    interval_seconds: int,
    metadata: dict[str, Any] | None = None,
    now_ts: float | None = None,
) -> dict[str, Any]:
    merged_metadata = dict(metadata or {})
    source_ref = _scheduled_source_ref(job_id, interval_seconds, now_ts=now_ts)
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source="scheduler",
    )
    common_kwargs = dict(
        title=f"Scheduled {agent} loop",
        prompt=prompt,
        owner_agent=agent,
        scope_type="global",
        scope_id="athanor",
        work_class=str(merged_metadata.get("workload_class") or "coding_implementation"),
        priority=_task_priority_to_backlog_priority(priority),
        approval_mode="none",
        dispatch_policy="planner_eligible",
        family="builder",
        project_id=str(merged_metadata.get("project_id") or ""),
        source_type="scheduler_signal",
        source_ref=source_ref,
        routing_class="private_but_cloud_allowed",
        verification_contract="bounded_change_verification",
        closure_rule="verified_result_required",
        materialization_source="scheduler",
        materialization_reason="Scheduled product-work emitted governed queue work.",
        metadata={
            **merged_metadata,
            "job_id": job_id,
            "interval_seconds": interval_seconds,
            "window_start": _window_start(interval_seconds, now_ts=now_ts),
        },
        origin="scheduler",
        created_by="scheduler",
    )
    if existing:
        backlog = await _refresh_existing_materialized_backlog(existing, **common_kwargs)
        return _materialization_payload(backlog=backlog, status="refreshed")
    backlog = await create_backlog_item(**common_kwargs)
    return _materialization_payload(backlog=backlog, status="created")


async def materialize_research_schedule(
    *,
    job_id: str,
    topic: str,
    prompt: str,
    schedule_hours: int,
    metadata: dict[str, Any] | None = None,
    now_ts: float | None = None,
) -> dict[str, Any]:
    merged_metadata = dict(metadata or {})
    interval_seconds = max(int(schedule_hours or 0) * 3600, 3600)
    source_ref = _research_source_ref(job_id, interval_seconds, now_ts=now_ts)
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source="research_scheduler",
    )
    common_kwargs = dict(
        title=f"Research job: {topic}",
        prompt=prompt,
        owner_agent="research-agent",
        scope_type="global",
        scope_id="athanor",
        work_class="research_synthesis",
        priority=3,
        approval_mode="none",
        dispatch_policy="planner_eligible",
        family="research_audit",
        project_id=str(merged_metadata.get("project_id") or ""),
        source_type="scheduler_signal",
        source_ref=source_ref,
        routing_class="private_but_cloud_allowed",
        verification_contract="evidence_bundle",
        closure_rule="result_or_review_required",
        materialization_source="research_scheduler",
        materialization_reason="Scheduled research job emitted governed queue work.",
        recurrence_program_id=job_id,
        metadata={
            **merged_metadata,
            "job_id": job_id,
            "schedule_hours": schedule_hours,
            "window_start": _window_start(interval_seconds, now_ts=now_ts),
        },
        origin="research_job",
        created_by="research_job",
    )
    if existing:
        backlog = await _refresh_existing_materialized_backlog(existing, **common_kwargs)
        return _materialization_payload(backlog=backlog, status="refreshed")
    backlog = await create_backlog_item(**common_kwargs)
    return _materialization_payload(backlog=backlog, status="created")


async def materialize_pipeline_starvation_recovery(
    *,
    project_id: str,
    hours_idle: float,
    now_ts: float | None = None,
) -> dict[str, Any]:
    normalized_project_id = str(project_id or "").strip()
    interval_seconds = 24 * 3600
    source_ref = _pipeline_starvation_source_ref(normalized_project_id or "athanor", now_ts=now_ts)
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source="pipeline_starvation",
    )
    idle_hours = round(float(hours_idle or 0.0), 1)
    prompt = (
        f"Project '{normalized_project_id or 'athanor'}' has had no activity for over 24 hours "
        f"({idle_hours:.1f}h idle). Review its current status, check for blockers, and suggest "
        "the next actionable step. Be specific and practical."
    )
    common_kwargs = dict(
        title=f"Pipeline starvation recovery: {normalized_project_id or 'athanor'}",
        prompt=prompt,
        owner_agent="general-assistant",
        scope_type="project" if normalized_project_id else "global",
        scope_id=normalized_project_id or "athanor",
        work_class="maintenance",
        priority=_task_priority_to_backlog_priority("low"),
        approval_mode="none",
        dispatch_policy="planner_eligible",
        family="maintenance",
        project_id=normalized_project_id,
        source_type="pipeline_signal",
        source_ref=source_ref,
        routing_class="private_but_cloud_allowed",
        verification_contract="maintenance_proof",
        closure_rule="proof_or_review_required",
        materialization_source="pipeline_starvation",
        materialization_reason="Pipeline starvation recovery emitted governed queue work.",
        recurrence_program_id="pipeline-cycle",
        metadata={
            "source": "pipeline",
            "trigger": "starvation_recovery",
            "project_id": normalized_project_id,
            "task_class": "workplan_generation",
            "workload_class": "maintenance",
            "_autonomy_managed": True,
            "_autonomy_source": "pipeline",
            "hours_idle": idle_hours,
            "window_start": _window_start(interval_seconds, now_ts=now_ts),
        },
    )
    if existing:
        backlog = await _refresh_existing_materialized_backlog(existing, **common_kwargs)
        return _materialization_payload(backlog=backlog, status="refreshed")
    backlog = await create_backlog_item(
        **common_kwargs,
        origin="pipeline",
        created_by="pipeline",
    )
    return _materialization_payload(backlog=backlog, status="created")


async def materialize_pipeline_task_spec(
    *,
    plan_id: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    metadata = dict(spec.get("metadata") or {})
    owner_agent = str(spec.get("agent") or "").strip()
    family, task_class, workload_class = _resolve_pipeline_queue_family(
        owner_agent=owner_agent,
        metadata=metadata,
    )
    if not family:
        return {
            "status": "skipped_out_of_scope",
            "reason": "Pipeline task spec does not resolve into a supported v1 queue family.",
        }

    prompt = str(spec.get("prompt") or "").strip()
    priority = str(spec.get("priority") or "normal").strip()
    effective_metadata = {
        **metadata,
        "source": "pipeline",
        "plan_id": plan_id,
        "task_class": task_class,
        "workload_class": workload_class,
        "_autonomy_managed": True,
        "_autonomy_source": "pipeline",
    }
    source_ref = f"pipeline:{plan_id}:{_pipeline_spec_fingerprint(agent=owner_agent, prompt=prompt, priority=priority, metadata=effective_metadata, family=family)}"
    existing = await _find_existing_materialized_backlog(
        source_ref=source_ref,
        materialization_source="pipeline",
    )
    project_id = str(effective_metadata.get("project_id") or "").strip()
    if not project_id and str(effective_metadata.get("scope_type") or "") == "project":
        project_id = str(effective_metadata.get("scope_id") or "").strip()
    routing_class = str(effective_metadata.get("routing_class") or "").strip()
    common_kwargs = dict(
        title=str(spec.get("title") or prompt[:120] or f"Pipeline task spec {plan_id}"),
        prompt=prompt,
        owner_agent=owner_agent,
        scope_type="project" if project_id else str(effective_metadata.get("scope_type") or "global"),
        scope_id=project_id or str(effective_metadata.get("scope_id") or "athanor"),
        work_class=workload_class or task_class or "coding_implementation",
        priority=_task_priority_to_backlog_priority(priority),
        approval_mode=str(effective_metadata.get("approval_mode") or "none"),
        dispatch_policy=str(effective_metadata.get("dispatch_policy") or "planner_eligible"),
        family=family,
        project_id=project_id,
        source_type="pipeline_plan",
        source_ref=source_ref,
        routing_class=routing_class or "private_but_cloud_allowed",
        verification_contract=str(effective_metadata.get("verification_contract") or ""),
        closure_rule=str(effective_metadata.get("closure_rule") or ""),
        materialization_source="pipeline",
        materialization_reason="Pipeline approved task spec emitted governed queue work.",
        metadata=effective_metadata,
        origin="pipeline",
        created_by="pipeline",
    )
    if existing:
        backlog = await _refresh_existing_materialized_backlog(existing, **common_kwargs)
        return _materialization_payload(backlog=backlog, status="refreshed")
    backlog = await create_backlog_item(**common_kwargs)
    return _materialization_payload(backlog=backlog, status="created")


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
    record = canonicalize_backlog_record(record)

    block_reason = redispatch_block_reason(record)
    if block_reason:
        raise ValueError(block_reason)

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
        proof_commands = _governed_dispatch_proof_commands(
            str(metadata.get("preferred_lane_family") or ""),
            autonomous_value_canary_id=str(metadata.get("autonomous_value_canary_id") or ""),
        )
        if proof_commands:
            metadata["proof_commands"] = proof_commands
            metadata.setdefault("proof_command_surface", " ".join(proof_commands[0]))
            preferred_lane_family = str(metadata.get("preferred_lane_family") or "").strip()
            if preferred_lane_family in {"validation_and_checkpoint", "publication_freeze"}:
                metadata["preferred_provider_id"] = "openai_codex"
                metadata["policy_class"] = "private_but_cloud_allowed"
                metadata["meta_lane"] = "frontier_cloud"
            if preferred_lane_family == "safe_surface_execution":
                metadata["proof_execution_stage"] = "after_agent"
                metadata["preferred_provider_id"] = "google_gemini"
                metadata["requires_mutable_implementation_authority"] = True
                metadata.setdefault("proof_timeout_seconds", 900)
            proof_artifact_paths = _governed_dispatch_proof_artifact_paths(
                preferred_lane_family,
                deliverable_refs=list(metadata.get("deliverable_refs") or []),
            )
            if proof_artifact_paths:
                metadata["proof_artifact_paths"] = proof_artifact_paths
            proof_environment = _governed_dispatch_proof_environment(preferred_lane_family)
            if proof_environment:
                metadata["proof_environment"] = proof_environment

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
    task_id = str(task.get("id") or "").strip()
    terminal_synced_statuses = {"running", "waiting_approval", "blocked", "completed", "failed", "archived"}
    freshest_record = await fetch_backlog_record(backlog_id)
    if freshest_record:
        freshest_record = canonicalize_backlog_record(freshest_record)
        freshest_metadata = dict(freshest_record.get("metadata") or {})
        freshest_latest_task_id = str(freshest_metadata.get("latest_task_id") or "").strip()
        if freshest_latest_task_id == task_id and str(freshest_record.get("status") or "").strip() in terminal_synced_statuses:
            record = freshest_record
            metadata = freshest_metadata

    metadata.update(
        {
            "latest_task_id": task_id,
            "latest_run_id": task_id,
            "last_dispatch_reason": reason,
            "governor_reason": submission.decision.reason,
            "governor_level": submission.decision.autonomy_level,
        }
    )
    record["metadata"] = metadata
    if str(record.get("status") or "").strip() not in terminal_synced_statuses:
        record["scheduled_for"] = _now_ts()
        record["updated_at"] = record["scheduled_for"]
        record["status"] = {
            "pending_approval": "waiting_approval",
            "pending": "scheduled",
            "running": "running",
        }.get(str(task.get("status") or "pending"), "scheduled")
    else:
        record["updated_at"] = max(float(record.get("updated_at") or 0.0), _now_ts())
    record = record_dispatch_event(record, reason=reason)
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
