#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"
RALPH_LOOP_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
GOVERNED_DISPATCH_PATH = REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"
COMPLETION_PASS_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "completion-pass-ledger.json"

if str(AGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(AGENTS_SRC))

try:
    from runtime_env import load_optional_runtime_env
except Exception:  # pragma: no cover - defensive import path
    load_optional_runtime_env = None

try:
    from athanor_agents.autonomous_queue import canonicalize_backlog_record
except Exception:  # pragma: no cover - defensive import path
    canonicalize_backlog_record = None

if load_optional_runtime_env is not None:
    load_optional_runtime_env(
        env_names=[
            "ATHANOR_REDIS_URL",
            "ATHANOR_REDIS_PASSWORD",
            "ATHANOR_AGENT_API_TOKEN",
            "ATHANOR_AGENT_SERVER_URL",
            "ATHANOR_POSTGRES_URL",
        ]
    )


ACTIVE_BACKLOG_STATUSES = {
    "captured",
    "triaged",
    "ready",
    "scheduled",
    "running",
    "waiting_approval",
    "blocked",
    "failed",
}
TERMINAL_BACKLOG_STATUSES = {"completed", "archived"}
TERMINAL_TASK_STATUSES = {"completed", "cancelled", "blocked"}
ACTIVE_GOVERNED_DISPATCH_BACKLOG_STATUSES = {"scheduled", "running", "waiting_approval"}
BLOCKED_ADMISSION_CLASSIFICATIONS = {
    "blocked_by_headroom",
    "blocked_by_queue_priority",
    "blocked_by_review_debt",
}
FAMILY_BY_WORK_CLASS = {
    "approval": "review",
    "approval_review": "review",
    "async_backlog_execution": "builder",
    "coding": "builder",
    "coding_implementation": "builder",
    "feature": "builder",
    "maintenance": "maintenance",
    "migration": "builder",
    "multi_file_implementation": "builder",
    "private_automation": "maintenance",
    "project_bootstrap": "project_bootstrap",
    "project_build": "project_bootstrap",
    "repo_audit": "research_audit",
    "repo_wide_audit": "research_audit",
    "research": "research_audit",
    "research_synthesis": "research_audit",
    "runtime_ops": "runtime_ops",
    "runtime_repair": "runtime_ops",
    "scaffold": "project_bootstrap",
    "system_improvement": "maintenance",
}
DEFAULT_AGENT_SERVER_URL = "http://192.168.1.244:9000"


async def _list_backlog_records() -> list[dict[str, Any]]:
    from athanor_agents.operator_state import list_backlog_records

    return await list_backlog_records(status="", owner_agent="", limit=None)


async def _list_tasks() -> list[dict[str, Any]]:
    from athanor_agents.tasks import list_tasks

    return await list_tasks(limit=None)


async def _build_scheduled_job_records() -> list[dict[str, Any]]:
    from athanor_agents.backbone import build_scheduled_job_records

    return await build_scheduled_job_records(limit=500)


async def _load_ralph_truth() -> dict[str, Any]:
    return _load_json_artifact(RALPH_LOOP_PATH)


async def _load_governed_dispatch_truth() -> dict[str, Any]:
    return _load_json_artifact(GOVERNED_DISPATCH_PATH)


async def _load_agent_route_payload(route_path: str, *, governed_truth: dict[str, Any] | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_load_agent_route_payload_sync, route_path, governed_truth or {})


async def _safe_load(
    label: str,
    loader: Any,
    *,
    fallback: Any,
    degraded_sections: list[str],
) -> Any:
    try:
        return await loader()
    except Exception as exc:
        degraded_sections.append(f"{label}:{str(exc)[:160]}")
        return fallback


def _now_ts() -> float:
    return time.time()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _hours(value: float) -> float:
    return round(value / 3600.0, 2)


def _load_json_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _best_historical_result_evidence(completion_pass_ledger: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    passes = completion_pass_ledger.get("passes")
    if not isinstance(passes, list):
        return {}, None

    best_entry: dict[str, Any] | None = None
    best_progress = 0
    for entry in passes:
        if not isinstance(entry, dict):
            continue
        result_evidence = dict(entry.get("result_evidence") or {})
        progress = int(result_evidence.get("threshold_progress") or 0)
        if progress <= 0:
            continue
        if progress >= best_progress:
            best_progress = progress
            best_entry = entry

    if not best_entry:
        return {}, None

    return dict(best_entry.get("result_evidence") or {}), {
        "source": "completion_pass_ledger",
        "pass_id": str(best_entry.get("pass_id") or ""),
        "finished_at": best_entry.get("finished_at"),
        "healthy": bool(best_entry.get("healthy")),
    }


def _agent_server_base_url(governed_truth: dict[str, Any]) -> str:
    execution = dict(governed_truth.get("execution") or {})
    return (
        _text(os.environ.get("ATHANOR_AGENT_SERVER_URL"))
        or _text(execution.get("agent_server_base_url"))
        or DEFAULT_AGENT_SERVER_URL
    )


def _agent_auth_headers() -> dict[str, str]:
    token = _text(os.environ.get("ATHANOR_AGENT_API_TOKEN"))
    return {"Authorization": f"Bearer {token}"} if token else {}


def _load_agent_route_payload_sync(route_path: str, governed_truth: dict[str, Any]) -> dict[str, Any]:
    base_url = _agent_server_base_url(governed_truth).rstrip("/")
    request = Request(f"{base_url}{route_path}", headers=_agent_auth_headers())
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover - exercised through async wrapper tests
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {route_path}: {detail[:160]}") from exc
    except URLError as exc:  # pragma: no cover - exercised through async wrapper tests
        raise RuntimeError(f"{route_path} unavailable: {exc.reason}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"{route_path} unavailable: {exc}") from exc
    return payload if isinstance(payload, dict) else {}


def _append_degraded(degraded_sections: list[str], detail: str) -> None:
    if detail not in degraded_sections:
        degraded_sections.append(detail)


def _clear_degraded_prefixes(degraded_sections: list[str], *prefixes: str) -> None:
    if not prefixes:
        return
    degraded_sections[:] = [
        detail
        for detail in degraded_sections
        if not any(detail.startswith(prefix) for prefix in prefixes)
    ]


def _verification_passed(record: dict[str, Any]) -> bool:
    metadata = dict(record.get("metadata") or {})
    return bool(
        metadata.get("verification_passed")
        or _text(metadata.get("verification_status")).lower() in {"passed", "verified", "green", "success"}
    )


def _canonical_backlog_record(record: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(record)
    if canonicalize_backlog_record is not None:
        try:
            canonical = canonicalize_backlog_record(dict(record))
        except Exception:
            canonical = dict(record)

    metadata = dict(canonical.get("metadata") or {})
    project_id = _text(canonical.get("project_id") or metadata.get("project_id"))
    if not project_id and _text(canonical.get("scope_type") or metadata.get("scope_type")) == "project":
        project_id = _text(canonical.get("scope_id") or metadata.get("scope_id"))

    primary_work_class = _text(canonical.get("work_class"))
    metadata_work_class = _text(
        metadata.get("workload_class") or metadata.get("task_class") or metadata.get("work_class")
    )
    work_class = metadata_work_class or primary_work_class
    if primary_work_class and primary_work_class not in {"system_improvement", "private_automation"}:
        work_class = primary_work_class
    family = _text(canonical.get("family") or metadata.get("family"))
    if primary_work_class in {"system_improvement", "private_automation"} and metadata_work_class:
        family = ""
    if not family:
        family = FAMILY_BY_WORK_CLASS.get(work_class, "")
    if not family:
        lane_family = _text(metadata.get("preferred_lane_family"))
        family = FAMILY_BY_WORK_CLASS.get(lane_family, "")

    canonical["project_id"] = project_id
    canonical["family"] = family
    canonical["result_id"] = _text(canonical.get("result_id") or metadata.get("result_id"))
    canonical["review_id"] = _text(
        canonical.get("review_id") or metadata.get("review_id") or metadata.get("approval_request_id")
    )
    canonical["materialization_source"] = _text(
        canonical.get("materialization_source") or metadata.get("materialization_source")
    )
    canonical["metadata"] = metadata
    return canonical


def _classify_scheduled_execution_plane(job: dict[str, Any]) -> str:
    explicit = _text(job.get("last_execution_plane"))
    if explicit in {"queue", "direct_control", "proposal_only"}:
        return explicit

    explicit_mode = _text(job.get("last_execution_mode"))
    if explicit_mode == "materialized_to_backlog":
        return "queue"

    job_id = _text(job.get("id"))
    if job_id in {"benchmark-cycle", "improvement-cycle", "nightly-optimization"}:
        return "proposal_only"
    return "direct_control"


def _scheduled_job_needs_sync(job: dict[str, Any]) -> bool:
    return (
        _classify_scheduled_execution_plane(job) == "queue"
        and _text(job.get("last_execution_mode")) == "materialized_to_backlog"
        and not _text(job.get("last_backlog_id"))
    )


def _governed_dispatch_counts_as_queue_job(governed_truth: dict[str, Any]) -> bool:
    execution = dict(governed_truth.get("execution") or {})
    materialization = dict(governed_truth.get("materialization") or {})
    execution_status = _text(execution.get("status")).lower()
    dispatch_outcome = _text(execution.get("dispatch_outcome") or governed_truth.get("dispatch_outcome")).lower()
    backlog_status = _text(execution.get("backlog_status") or materialization.get("backlog_status")).lower()
    task_status = _text(execution.get("task_status")).lower()
    backlog_id = _text(execution.get("backlog_id") or materialization.get("backlog_id"))

    if not backlog_id:
        return False
    if backlog_status in ACTIVE_GOVERNED_DISPATCH_BACKLOG_STATUSES:
        return True
    if execution_status in {"dispatched", "already_dispatched"} and task_status not in TERMINAL_TASK_STATUSES:
        return True
    return dispatch_outcome == "success" and backlog_status not in TERMINAL_BACKLOG_STATUSES


def _queue_summary_counts(ralph_truth: dict[str, Any], governed_truth: dict[str, Any]) -> tuple[int, int, int]:
    summary = dict(ralph_truth.get("autonomous_queue_summary") or {})
    queue_count = _int(summary.get("queue_count"))
    dispatchable_count = _int(summary.get("dispatchable_queue_count"))
    blocked_count = _int(summary.get("blocked_queue_count"))

    if queue_count <= 0:
        dispatchable_count = max(dispatchable_count, _int(governed_truth.get("dispatchable_queue_count")))
        blocked_count = max(blocked_count, _int(governed_truth.get("blocked_queue_count")))
        queue_count = max(_int(governed_truth.get("queue_total_count")), dispatchable_count + blocked_count)

    return queue_count, dispatchable_count, blocked_count


def _repo_label(repo_value: Any) -> str:
    repo_text = _text(repo_value)
    if not repo_text:
        return "unscoped"
    name = Path(repo_text).name
    return name or repo_text


def _build_fallback_aging(
    ralph_truth: dict[str, Any],
    governed_truth: dict[str, Any],
) -> dict[str, Any]:
    queue_count, _, _ = _queue_summary_counts(ralph_truth, governed_truth)
    queue_items = [dict(item) for item in ralph_truth.get("autonomous_queue", []) if isinstance(item, dict)]
    if not queue_items:
        return {
            "open_item_count": queue_count,
            "by_family": [],
            "by_project": [],
        }

    family_counts: dict[str, int] = {}
    project_counts: dict[str, int] = {}
    for item in queue_items:
        family = (
            _text(item.get("preferred_lane_family"))
            or _text(item.get("value_class"))
            or _text(item.get("source_type"))
            or "unknown"
        )
        family_counts[family] = family_counts.get(family, 0) + 1

        project_id = _repo_label(item.get("repo") or item.get("source_repo"))
        project_counts[project_id] = project_counts.get(project_id, 0) + 1

    by_family = [
        {
            "family": family,
            "count": count,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
        for family, count in family_counts.items()
    ]
    by_family.sort(key=lambda item: (-item["count"], item["family"]))

    by_project = [
        {
            "project_id": project_id,
            "count": count,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
        for project_id, count in project_counts.items()
    ]
    by_project.sort(key=lambda item: (-item["count"], item["project_id"]))

    return {
        "open_item_count": queue_count or len(queue_items),
        "by_family": by_family,
        "by_project": by_project,
    }


async def _load_backlog_via_api(governed_truth: dict[str, Any]) -> list[dict[str, Any]]:
    query = urlencode({"limit": 500})
    payload = await _load_agent_route_payload(f"/v1/operator/backlog?{query}", governed_truth=governed_truth)
    return [dict(item) for item in payload.get("backlog", []) if isinstance(item, dict)]


async def _load_tasks_via_api(governed_truth: dict[str, Any]) -> list[dict[str, Any]]:
    query = urlencode({"limit": 500})
    payload = await _load_agent_route_payload(f"/v1/tasks?{query}", governed_truth=governed_truth)
    return [dict(item) for item in payload.get("tasks", []) if isinstance(item, dict)]


async def _load_scheduled_jobs_via_api(governed_truth: dict[str, Any]) -> list[dict[str, Any]]:
    query = urlencode({"limit": 500})
    payload = await _load_agent_route_payload(f"/v1/tasks/scheduled?{query}", governed_truth=governed_truth)
    return [dict(item) for item in payload.get("jobs", []) if isinstance(item, dict)]


def _build_reconciliation(
    records: list[dict[str, Any]],
    tasks_by_id: dict[str, dict[str, Any]],
    *,
    governed_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for record in records:
        backlog_id = _text(record.get("backlog_id") or record.get("id"))
        status = _text(record.get("status")).lower()
        latest_task_id = _text(dict(record.get("metadata") or {}).get("latest_task_id"))
        latest_task_status = _text(tasks_by_id.get(latest_task_id, {}).get("status")).lower() if latest_task_id else ""
        result_id = _text(record.get("result_id"))
        review_id = _text(record.get("review_id"))
        blocking_reason = _text(record.get("blocking_reason") or dict(record.get("metadata") or {}).get("blocking_reason"))

        issue_type = ""
        repair_action = ""
        detail = ""
        if status in {"scheduled", "running", "waiting_approval"} and latest_task_id and latest_task_status in TERMINAL_TASK_STATUSES:
            issue_type = "stale_terminal_task"
            repair_action = "reopen_to_ready"
            detail = f"Latest task {latest_task_id} ended {latest_task_status} while backlog remained {status}."
        elif status == "waiting_approval" and not review_id:
            issue_type = "missing_review_evidence"
            repair_action = "transition_to_blocked"
            detail = "waiting_approval backlog item has no linked review_id."
        elif status in {"completed", "failed"} and not result_id:
            issue_type = "missing_result_evidence"
            repair_action = "reopen_to_ready" if status == "completed" else "transition_to_failed"
            detail = f"{status} backlog item has no linked result_id."
        elif status == "completed" and _text(record.get("verification_contract")) and not _verification_passed(record):
            issue_type = "missing_verification_evidence"
            repair_action = "transition_to_waiting_approval" if review_id else "transition_to_blocked"
            detail = "completed backlog item has result evidence but no passed verification contract."
        elif status == "blocked" and not blocking_reason:
            issue_type = "missing_blocking_reason"
            repair_action = "transition_to_failed"
            detail = "blocked backlog item has no machine-readable blocking_reason."

        if issue_type:
            issues.append(
                {
                    "backlog_id": backlog_id,
                    "title": _text(record.get("title")) or backlog_id,
                    "family": _text(record.get("family")),
                    "project_id": _text(record.get("project_id")),
                    "status": status,
                    "issue_type": issue_type,
                    "repair_action": repair_action,
                    "detail": detail,
                }
            )

    execution = dict((governed_truth or {}).get("execution") or {})
    execution_status = _text(execution.get("status")).lower()
    execution_outcome = _text(execution.get("dispatch_outcome") or (governed_truth or {}).get("dispatch_outcome")).lower()
    repair_reason = _text(execution.get("repair_reason"))
    if (
        not issues
        and (
            execution_status == "stale_dispatched_task"
            or (execution_outcome == "failed" and repair_reason == "stale_terminal_dispatch")
        )
    ):
        task_title = _text(execution.get("current_task_title") or (governed_truth or {}).get("current_task_title"))
        task_id = _text(execution.get("current_task_id") or (governed_truth or {}).get("current_task_id"))
        issues.append(
            {
                "backlog_id": _text(execution.get("backlog_id")) or task_id or "unknown",
                "title": task_title or task_id or "Governed dispatch task",
                "family": _text(execution.get("task_source") or (governed_truth or {}).get("current_source_type")) or "operator_backlog",
                "project_id": _repo_label(REPO_ROOT),
                "status": execution_status or execution_outcome or "failed",
                "issue_type": "stale_terminal_task",
                "repair_action": "reopen_to_ready",
                "detail": "Governed dispatch is still reporting a stale terminal task without canonical backlog reconciliation.",
            }
        )

    issues.sort(key=lambda item: (item["issue_type"], item["backlog_id"]))
    issues_by_type: dict[str, int] = {}
    for issue in issues:
        issues_by_type[issue["issue_type"]] = issues_by_type.get(issue["issue_type"], 0) + 1
    return {
        "issue_count": len(issues),
        "repairable_count": len(issues),
        "issues_by_type": issues_by_type,
        "issues": issues,
    }


def _aging_summary(records: list[dict[str, Any]], now_ts: float) -> dict[str, Any]:
    by_family: dict[str, list[float]] = {}
    by_project: dict[str, list[float]] = {}
    open_item_count = 0

    for record in records:
        status = _text(record.get("status")).lower()
        if status in TERMINAL_BACKLOG_STATUSES:
            continue
        open_item_count += 1
        source_ts = _float(record.get("created_at") or record.get("updated_at"))
        age_seconds = max(now_ts - source_ts, 0.0) if source_ts > 0 else 0.0
        family = _text(record.get("family")) or "unknown"
        project_id = _text(record.get("project_id")) or "unscoped"
        by_family.setdefault(family, []).append(age_seconds)
        by_project.setdefault(project_id, []).append(age_seconds)

    def _build_rows(groups: dict[str, list[float]], key_name: str) -> list[dict[str, Any]]:
        rows = []
        for key, ages in groups.items():
            rows.append(
                {
                    key_name: key,
                    "count": len(ages),
                    "oldest_age_hours": _hours(max(ages) if ages else 0.0),
                    "average_age_hours": _hours(statistics.fmean(ages) if ages else 0.0),
                }
            )
        rows.sort(key=lambda item: (-item["oldest_age_hours"], -item["count"], item[key_name]))
        return rows

    return {
        "open_item_count": open_item_count,
        "by_family": _build_rows(by_family, "family"),
        "by_project": _build_rows(by_project, "project_id"),
    }


async def build_payload() -> dict[str, Any]:
    now_ts = _now_ts()
    degraded_sections: list[str] = []
    ralph_truth, governed_truth = await asyncio.gather(
        _safe_load("ralph_truth", _load_ralph_truth, fallback={}, degraded_sections=degraded_sections),
        _safe_load("governed_dispatch", _load_governed_dispatch_truth, fallback={}, degraded_sections=degraded_sections),
    )
    completion_pass_ledger = _load_json_artifact(COMPLETION_PASS_LEDGER_PATH)
    backlog_records, task_records, scheduled_jobs = await asyncio.gather(
        _safe_load("backlog", _list_backlog_records, fallback=[], degraded_sections=degraded_sections),
        _safe_load("tasks", _list_tasks, fallback=[], degraded_sections=degraded_sections),
        _safe_load("scheduled_jobs", _build_scheduled_job_records, fallback=[], degraded_sections=degraded_sections),
    )
    if not backlog_records:
        backlog_records = await _safe_load(
            "backlog_api",
            lambda: _load_backlog_via_api(governed_truth),
            fallback=[],
            degraded_sections=degraded_sections,
        )
    if backlog_records:
        _clear_degraded_prefixes(degraded_sections, "backlog:", "backlog_api:")
    if not task_records:
        task_records = await _safe_load(
            "tasks_api",
            lambda: _load_tasks_via_api(governed_truth),
            fallback=[],
            degraded_sections=degraded_sections,
        )
    if task_records:
        _clear_degraded_prefixes(degraded_sections, "tasks:", "tasks_api:")
    if not scheduled_jobs:
        scheduled_jobs = await _safe_load(
            "scheduled_jobs_api",
            lambda: _load_scheduled_jobs_via_api(governed_truth),
            fallback=[],
            degraded_sections=degraded_sections,
        )
    if scheduled_jobs:
        _clear_degraded_prefixes(degraded_sections, "scheduled_jobs:", "scheduled_jobs_api:")
    backlog_records = [_canonical_backlog_record(record) for record in backlog_records if isinstance(record, dict)]
    tasks_by_id = {_text(task.get("id")): dict(task) for task in task_records if _text(task.get("id"))}

    result_backed_completion_count = 0
    review_backed_output_count = 0
    dispatch_latencies: list[float] = []
    review_debt_ages: list[float] = []
    review_debt_by_family: dict[str, list[float]] = {}
    proposal_backlog_count = 0
    proposal_result_backed_completion_count = 0
    proposal_review_backed_output_count = 0

    for record in backlog_records:
        status = _text(record.get("status")).lower()
        family = _text(record.get("family")) or "unknown"
        result_id = _text(record.get("result_id"))
        review_id = _text(record.get("review_id"))
        created_at = _float(record.get("created_at"))
        completed_at = _float(record.get("completed_at"))
        updated_at = _float(record.get("updated_at"))

        if status == "completed" and result_id and _verification_passed(record):
            result_backed_completion_count += 1
            if completed_at > 0 and created_at > 0 and completed_at >= created_at:
                dispatch_latencies.append(completed_at - created_at)

        if status == "waiting_approval":
            age_seconds = max(now_ts - created_at, 0.0)
            review_debt_ages.append(age_seconds)
            review_debt_by_family.setdefault(family, []).append(age_seconds)
            if review_id:
                review_backed_output_count += 1

        if _text(record.get("materialization_source")) == "self_improvement":
            proposal_backlog_count += 1
            if status == "completed" and result_id and _verification_passed(record):
                proposal_result_backed_completion_count += 1
            if status == "waiting_approval" and review_id:
                proposal_review_backed_output_count += 1

    scheduled_execution = {
        "queue_backed_jobs": 0,
        "direct_control_jobs": 0,
        "proposal_only_jobs": 0,
        "blocked_jobs": 0,
        "needs_sync_jobs": 0,
    }
    for job in scheduled_jobs:
        plane = _classify_scheduled_execution_plane(job)
        if plane == "queue":
            scheduled_execution["queue_backed_jobs"] += 1
        elif plane == "proposal_only":
            scheduled_execution["proposal_only_jobs"] += 1
        else:
            scheduled_execution["direct_control_jobs"] += 1
        if _text(job.get("last_admission_classification")) in BLOCKED_ADMISSION_CLASSIFICATIONS:
            scheduled_execution["blocked_jobs"] += 1
        if _scheduled_job_needs_sync(job):
            scheduled_execution["needs_sync_jobs"] += 1

    if scheduled_execution["queue_backed_jobs"] == 0 and _governed_dispatch_counts_as_queue_job(governed_truth):
        scheduled_execution["queue_backed_jobs"] = 1

    reconciliation = _build_reconciliation(backlog_records, tasks_by_id, governed_truth=governed_truth)

    if backlog_records:
        backlog_aging = _aging_summary(backlog_records, now_ts)
    else:
        backlog_aging = _build_fallback_aging(ralph_truth, governed_truth)
        if backlog_aging["open_item_count"] > 0:
            _append_degraded(degraded_sections, "backlog:fallback_to_ralph_queue_truth")

    review_debt_rows = [
        {
            "family": family,
            "count": len(ages),
            "oldest_age_hours": _hours(max(ages) if ages else 0.0),
            "average_age_hours": _hours(statistics.fmean(ages) if ages else 0.0),
        }
        for family, ages in review_debt_by_family.items()
    ]
    review_debt_rows.sort(key=lambda item: (-item["oldest_age_hours"], -item["count"], item["family"]))

    historical_carry_forward = None
    if result_backed_completion_count <= 0 and review_backed_output_count <= 0:
        historical_result_evidence, historical_carry_forward = _best_historical_result_evidence(completion_pass_ledger)
        historical_progress = int(historical_result_evidence.get("threshold_progress") or 0)
        if historical_progress > 0:
            result_backed_completion_count = int(historical_result_evidence.get("result_backed_completion_count") or 0)
            review_backed_output_count = int(historical_result_evidence.get("review_backed_output_count") or 0)

    latency_average = round(statistics.fmean(dispatch_latencies) / 3600.0, 2) if dispatch_latencies else 0.0

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts)),
        "degraded_sections": degraded_sections,
        "result_backed_completion_count": result_backed_completion_count,
        "review_backed_output_count": review_backed_output_count,
        "result_evidence_basis": "historical_carry_forward" if historical_carry_forward else "live_backlog",
        "result_evidence_carry_forward": historical_carry_forward,
        "stale_claim_count": reconciliation["issues_by_type"].get("stale_terminal_task", 0),
        "backlog_aging": backlog_aging,
        "dispatch_to_result_latency": {
            "completed_count": len(dispatch_latencies),
            "average_hours": latency_average,
        },
        "proposal_conversion": {
            "proposal_backlog_count": proposal_backlog_count,
            "result_backed_completion_count": proposal_result_backed_completion_count,
            "review_backed_output_count": proposal_review_backed_output_count,
        },
        "review_debt": {
            "count": len(review_debt_ages),
            "oldest_age_hours": _hours(max(review_debt_ages) if review_debt_ages else 0.0),
            "by_family": review_debt_rows,
        },
        "scheduled_execution": scheduled_execution,
        "reconciliation": reconciliation,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the Athanor value-throughput scorecard from canonical backlog truth.",
    )
    parser.add_argument("--json", action="store_true", help="Print the scorecard payload to stdout after writing it.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = asyncio.run(build_payload())
    _write_json(OUTPUT_PATH, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
