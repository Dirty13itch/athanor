"""Task Execution Engine — background autonomous work for agents.

Transforms agents from reactive chat endpoints to autonomous workers.
Tasks are Redis-backed, executed by a background worker, with step
logging and progress broadcasting via GWT workspace.

Architecture:
    - Tasks stored in Redis hash (athanor:tasks -> task_id => JSON record)
    - Background worker polls every 5s, picks highest-priority pending task
    - Worker streams agent execution via astream_events() to capture tool call steps
    - Completion/failure broadcast to GWT workspace
    - Max 2 concurrent tasks (inference backend can handle parallel requests)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from .config import settings
from .durable_state import (
    fetch_task_snapshot,
    get_task_snapshot_stats,
    list_task_snapshots,
    upsert_task_snapshot,
)
from .execution_state import sync_task_execution_projection
from .operator_work import sync_backlog_item_from_task
from .repo_paths import resolve_repo_root
from .task_store import (
    TASKS_UPDATED_KEY,
    TASK_STATUS_VALUES,
    backfill_task_store_indexes,
    delete_task_record,
    read_task_records_by_status,
    read_task_records_by_statuses,
    read_task_record,
    write_task_record,
)

logger = logging.getLogger(__name__)

TASKS_CHANNEL = "athanor:tasks:events"
TASK_WORKER_INTERVAL = 5.0  # seconds between polls
MAX_CONCURRENT_TASKS = 6
TASK_TIMEOUT = 600  # 10 min default per task
TASK_HEARTBEAT_INTERVAL = 5.0
TASK_CLAIM_TTL_SECONDS = 30

# Deep work agents get longer timeouts — their prompts are multi-step cycles
AGENT_TIMEOUTS = {
    "creative-agent": 1800,   # 30 min — generate + evaluate + refine loops
    "coding-agent": 1200,     # 20 min — code audit + review cycles
    "data-curator": 1200,     # 20 min — scan + parse + index cycles
    "research-agent": 900,    # 15 min — search + research + document
    "stash-agent": 900,       # 15 min — library organization
    "knowledge-agent": 900,   # 15 min — KB curation
}
MAX_TASK_RETRIES = 1  # Auto-retry failed tasks once with error context
TASK_TTL_COMPLETED = 86400  # 24h — purge completed tasks
TASK_TTL_FAILED = 604800  # 7d — keep failed tasks longer for debugging
CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

_worker_task: asyncio.Task | None = None
_running_count = 0


@dataclass
class Task:
    """A unit of autonomous work for an agent."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent: str = ""
    prompt: str = ""
    priority: str = "normal"  # critical, high, normal, low
    status: str = "pending"   # pending, pending_approval, running, stale_lease, completed, failed, cancelled
    source: str = "task_api"
    lane: str = ""
    result: str = ""
    error: str = ""
    steps: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    updated_at: float = field(default_factory=time.time)
    lease: dict = field(default_factory=dict)
    retry_lineage: list[str] = field(default_factory=list)
    assigned_runtime: str = ""
    last_heartbeat: float = 0.0
    session_id: str = ""
    metadata: dict = field(default_factory=dict)
    parent_task_id: str = ""  # For delegated sub-tasks
    retry_count: int = 0  # How many times this task has been retried
    previous_error: str = ""  # Error from previous attempt (for retry context)

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.status not in TASK_STATUS_VALUES:
            payload["status"] = "pending"
        if not payload.get("lane"):
            payload["lane"] = self.lane or self.agent or self.source or "task"
        if not payload.get("lease") and isinstance(self.metadata, dict):
            payload["lease"] = self.metadata.get("execution_lease", {}) or {}
        if not payload.get("assigned_runtime") and isinstance(payload.get("lease"), dict):
            payload["assigned_runtime"] = payload["lease"].get("provider", "")
        if not payload.get("session_id") and isinstance(self.metadata, dict):
            payload["session_id"] = self.metadata.get("session_id", "")
        if not payload.get("updated_at"):
            payload["updated_at"] = self.completed_at or self.started_at or self.created_at or time.time()
        if not payload.get("last_heartbeat"):
            payload["last_heartbeat"] = self.started_at or 0.0
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def duration_ms(self) -> int | None:
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at) * 1000)
        return None


@dataclass
class GovernedTaskSubmission:
    """Canonical result for a governor-mediated task submission."""

    task: Task
    decision: object
    held_for_approval: bool = False


PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}
ACTIVE_TASK_STATUSES = ("pending", "pending_approval", "running", "stale_lease")
# Stale leases stay visible in operator truth, but they should not block a fresh
# governed submission from re-arming the same work after restart recovery.
DEDUP_TASK_STATUSES = ("pending", "pending_approval", "running")
RETRY_TRANSIENT_METADATA_KEYS = {
    "approval_decided",
    "approval_decided_at",
    "approval_decided_by",
    "approval_reason",
    "approval_rejected",
    "approval_request_id",
    "approval_requested_at",
    "attempt_id",
    "dispatch_reason",
    "execution_claim",
    "execution_run_id",
    "failure",
    "failure_display",
    "failure_repair",
    "governor_autonomy_level",
    "governor_decision",
    "governor_level",
    "governor_reason",
    "governor_status_override",
    "last_dispatch_reason",
    "latest_run_id",
    "latest_task_id",
    "manual_dispatch",
    "recovery",
    "replay_of_attempt_id",
    "requires_approval",
    "retry_of",
    "retry_of_attempt_id",
}

# Agent-specific task capabilities for system prompt
_AGENT_TASK_HINTS = {
    "coding-agent": (
        "You have filesystem tools (read_file, write_file, list_directory, search_files) "
        "and code execution (run_command). Plan your approach, then execute step by step. "
        "Write files, run tests, fix failures, and iterate until the task is complete."
    ),
    "general-assistant": (
        "You have service monitoring tools and filesystem access. "
        "Check service health, inspect logs, and report findings with specifics."
    ),
    "research-agent": (
        "You have web search, page fetching, and knowledge base tools. "
        "Search thoroughly, cross-reference sources, and synthesize findings."
    ),
    "knowledge-agent": (
        "You have knowledge base search and document listing tools. "
        "Search the knowledge base, identify gaps, and report findings."
    ),
    "media-agent": (
        "You have Sonarr, Radarr, and Plex tools. "
        "Check media services, report notable items, and manage content."
    ),
    "home-agent": (
        "You have Home Assistant tools for entity state, services, and automations. "
        "Check states, identify anomalies, and take action when appropriate."
    ),
    "creative-agent": (
        "You have ComfyUI image and video generation tools. "
        "Generate content as requested, monitor the queue, and report results."
    ),
    "stash-agent": (
        "You have Stash library management tools. "
        "Search, browse, organize, and tag content as requested."
    ),
}

MAX_TASK_CONTEXT_CHARS = 4000
MAX_TASK_INSTRUCTION_CHARS = 4000
MAX_TASK_BODY_CHARS = 12000
MAX_TASK_MESSAGE_CHARS = 16000
BACKGROUND_TASK_EXECUTION_AGENTS = {
    "coding-agent",
    "general-assistant",
    "knowledge-agent",
    "research-agent",
}
PROVIDER_EXECUTION_TASK_CLASSES = {
    "async_backlog_execution",
    "multi_file_implementation",
    "repo_wide_audit",
    "search_heavy_planning",
}
GOVERNED_PROOF_TIMEOUT_SECONDS = 180
MAX_GOVERNED_PROOF_OUTPUT_CHARS = 4000
REPO_ROOT = resolve_repo_root(__file__)
INTERNAL_EXECUTION_PROVIDER_MODELS = {
    "google_gemini": "gemini-sub",
}
ALLOWED_GOVERNED_PROOF_SCRIPTS = {
    "scripts/run_dashboard_value_proof.py",
    "scripts/validate_platform_contract.py",
    "scripts/run_gpu_scheduler_baseline_eval.py",
    "scripts/collect_capacity_telemetry.py",
    "scripts/write_quota_truth_snapshot.py",
    "scripts/generate_documentation_index.py",
    "scripts/generate_project_maturity_report.py",
    "scripts/generate_truth_inventory_reports.py",
}


def _compact_text_block(text: str, limit: int, *, label: str) -> str:
    """Trim oversized task payload blocks without losing the fact that trimming happened."""

    normalized = str(text or "").strip()
    if limit <= 0:
        return ""
    if len(normalized) <= limit:
        return normalized

    suffix = f"\n\n[{label} truncated to stay within the task execution budget.]"
    head_limit = max(limit - len(suffix), 0)
    return normalized[:head_limit].rstrip() + suffix


def _build_task_message_content(task: Task, context_str: str, task_prompt: str) -> str:
    """Build a budget-aware HumanMessage body for autonomous task execution."""

    compact_context = _compact_text_block(
        context_str,
        MAX_TASK_CONTEXT_CHARS,
        label="Context",
    )
    compact_task_prompt = _compact_text_block(
        task_prompt,
        MAX_TASK_INSTRUCTION_CHARS,
        label="Task instructions",
    )
    compact_task_body = _compact_text_block(
        task.prompt,
        MAX_TASK_BODY_CHARS,
        label="Task prompt",
    )

    preamble_parts: list[str] = []
    if compact_context:
        preamble_parts.append(f"[Context]\n{compact_context}\n[/Context]")
    preamble_parts.append(f"[Task Instructions]\n{compact_task_prompt}\n[/Task Instructions]")
    content = "\n\n".join(preamble_parts) + "\n\n" + compact_task_body

    if len(content) <= MAX_TASK_MESSAGE_CHARS:
        return content

    compact_task_body = _compact_text_block(
        task.prompt,
        max(MAX_TASK_MESSAGE_CHARS - len("\n\n".join(preamble_parts)) - 2, 512),
        label="Task prompt",
    )
    content = "\n\n".join(preamble_parts) + "\n\n" + compact_task_body
    return _compact_text_block(content, MAX_TASK_MESSAGE_CHARS, label="Task message")


def _build_task_prompt(task: Task) -> str:
    """Build a task-mode system prompt for autonomous execution."""
    parts = [
        "You are executing an autonomous task. Work independently to completion.",
        "",
        f"Task ID: {task.id}",
        f"Priority: {task.priority}",
    ]

    # Add retry context if this is a retry
    if task.retry_count > 0 and task.previous_error:
        parts.extend([
            "",
            f"IMPORTANT: This is retry #{task.retry_count}. The previous attempt failed with:",
            f"  Error: {task.previous_error}",
            "",
            "Analyze what went wrong and try a different approach. Do NOT repeat the same steps that caused the failure.",
        ])

    # Add agent-specific hints
    hint = _AGENT_TASK_HINTS.get(task.agent, "")
    if hint:
        parts.extend(["", hint])

    lease = (task.metadata or {}).get("execution_lease", {})
    if lease:
        fallback = ", ".join(lease.get("fallback", [])) or "none"
        parts.extend([
            "",
            "Execution lease:",
            f"- Approved provider lane: {lease.get('provider', 'unknown')}",
            f"- Surface: {lease.get('surface', 'unknown')}",
            f"- Privacy: {lease.get('privacy', 'unknown')}",
            f"- Parallel allowance: {lease.get('max_parallel_children', 1)}",
            f"- Fallback: {fallback}",
            f"- Reason: {lease.get('reason', '')}",
            "- Treat this as policy guidance for escalation or handoff work.",
            "- If the approved external lane is not directly callable from your current runtime, produce an exact handoff bundle or execution plan for it.",
        ])

    parts.extend([
        "",
        "Instructions:",
        "1. Plan your approach before acting",
        "2. Execute steps one at a time using your tools",
        "3. After each step, assess progress",
        "4. If stuck on a step, try an alternative approach",
        "5. When complete, provide a clear summary of what you accomplished",
        "6. If you cannot complete the task, explain exactly what blocked you",
    ])

    return "\n".join(parts)


def _stamp_task_execution_metadata(
    agent: str,
    prompt: str,
    priority: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Align governed background tasks with canonical subscription-policy hints."""

    task_metadata = dict(metadata or {})
    if agent not in BACKGROUND_TASK_EXECUTION_AGENTS:
        return task_metadata

    try:
        from . import subscriptions as subscriptions_module
    except Exception:
        return task_metadata

    build_task_lease_request = getattr(subscriptions_module, "build_task_lease_request", None)
    if build_task_lease_request is None:
        return task_metadata

    lease_request = build_task_lease_request(
        requester=agent,
        prompt=prompt,
        priority=priority,
        metadata=task_metadata,
    )
    task_metadata.setdefault("task_class", lease_request.task_class)
    task_metadata.setdefault("sensitivity", lease_request.sensitivity)
    task_metadata.setdefault("interactive", lease_request.interactive)
    task_metadata.setdefault("expected_context", lease_request.expected_context)
    task_metadata.setdefault("parallelism", lease_request.parallelism)
    return task_metadata


def _describe_exception(exc: BaseException) -> dict[str, str]:
    """Render exceptions into durable task-safe strings.

    Some runtime exceptions stringify to an empty string, which makes failed task
    records impossible to diagnose. This helper guarantees a non-empty message and
    preserves a compact type/repr trail for later analysis.
    """

    exc_type = type(exc).__name__ or "Exception"
    raw_message = str(exc).strip()
    repr_text = repr(exc).strip()
    args = getattr(exc, "args", ()) or ()

    if raw_message:
        message = raw_message
    else:
        arg_messages = [str(arg).strip() for arg in args if str(arg).strip()]
        if arg_messages:
            message = "; ".join(arg_messages)
        elif repr_text and repr_text != f"{exc_type}()":
            message = repr_text
        else:
            message = exc_type

    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        cause_type = type(cause).__name__ or "Exception"
        cause_message = str(cause).strip() or repr(cause).strip() or cause_type
        if cause_message and cause_message != message:
            message = f"{message} (cause: {cause_type}: {cause_message})"

    return {
        "type": exc_type,
        "message": message[:2000],
        "repr": repr_text[:2000],
    }


def _stamp_task_failure(
    task: Task,
    *,
    error_message: str,
    failure_type: str,
    retry_eligible: bool,
    exception_repr: str = "",
    stage: str = "",
    now: float | None = None,
) -> float:
    """Apply consistent failed-task state and structured failure metadata."""

    completed_at = now or time.time()
    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    failure = {
        "type": failure_type,
        "message": error_message[:2000],
        "recorded_at": completed_at,
        "retry_eligible": retry_eligible,
    }
    if stage:
        failure["stage"] = stage
    if exception_repr:
        failure["repr"] = exception_repr[:2000]

    task.status = "failed"
    task.error = error_message[:2000]
    task.completed_at = completed_at
    task.metadata = {
        **metadata,
        "failure": failure,
    }
    return completed_at


def _get_task_failure_context(task: Task) -> str:
    """Return the best available human-readable failure context for retries."""

    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    failure = metadata.get("failure", {}) if isinstance(metadata.get("failure"), dict) else {}
    failure_message = str(failure.get("message") or "").strip()
    if failure_message:
        return failure_message[:2000]

    task_error = str(task.error or "").strip()
    if task_error:
        return task_error[:2000]

    failure_type = str(failure.get("type") or "").strip()
    if failure_type:
        return failure_type[:2000]

    return "Task execution failed"


LEGACY_FAILED_TASK_DETAIL = "Legacy failed task missing recorded failure detail"
LEGACY_FAILURE_REPAIR_SOURCE = "startup_legacy_failed_task_backfill"


def _build_failure_display(task: Task) -> dict[str, object] | None:
    """Return operator-facing failure context for read models and stats.

    Older failed-task rows can have blank ``error`` values and no structured
    failure metadata. That makes dashboards report a failure count without any
    actionable detail. This helper keeps current task execution semantics
    unchanged while synthesizing an explicit read-model message for legacy rows.
    """

    if task.status != "failed":
        return None

    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    failure = metadata.get("failure", {}) if isinstance(metadata.get("failure"), dict) else {}

    message = str(failure.get("message") or "").strip()
    source = ""
    if message:
        source = "metadata.failure.message"
    else:
        task_error = str(task.error or "").strip()
        if task_error:
            message = task_error
            source = "task.error"
        else:
            failure_type = str(failure.get("type") or "").strip()
            if failure_type:
                message = failure_type
                source = "metadata.failure.type"
            else:
                message = LEGACY_FAILED_TASK_DETAIL
                source = "synthetic_legacy_gap"

    failure_display: dict[str, object] = {
        "message": message[:2000],
        "source": source,
        "missing_detail": source == "synthetic_legacy_gap",
        "legacy_record": source == "synthetic_legacy_gap" or bool(failure.get("historical_residue")),
        "historical_residue": bool(failure.get("historical_residue")),
        "repaired": bool(failure.get("synthetic")) or isinstance(metadata.get("failure_repair"), dict),
    }

    failure_type = str(failure.get("type") or "").strip()
    if failure_type:
        failure_display["type"] = failure_type[:2000]

    return failure_display


def _normalize_task_for_read(task: Task) -> Task:
    """Return a safe read-model copy with operator-facing failure context."""

    normalized = Task.from_dict(task.to_dict())
    failure_display = _build_failure_display(normalized)
    if not failure_display:
        return normalized

    metadata = dict(normalized.metadata or {})
    metadata["failure_display"] = failure_display
    normalized.metadata = metadata
    if not str(normalized.error or "").strip():
        normalized.error = str(failure_display.get("message") or "")[:2000]
    return normalized


def _build_retry_metadata(task: Task) -> dict[str, object]:
    source_metadata = task.metadata if isinstance(task.metadata, dict) else {}
    retry_metadata = {
        key: value
        for key, value in source_metadata.items()
        if key not in RETRY_TRANSIENT_METADATA_KEYS
    }
    retry_metadata["retry_of"] = task.id
    retry_metadata["source"] = "auto-retry"
    return retry_metadata


async def _sync_retry_backlog_record(original_task: Task, retry_task: Task) -> None:
    backlog_id = str((retry_task.metadata or {}).get("backlog_id") or "").strip()
    if not backlog_id:
        return

    try:
        from .operator_state import fetch_backlog_record, upsert_backlog_record

        record = await fetch_backlog_record(backlog_id)
        if not record:
            return

        metadata = dict(record.get("metadata") or {})
        metadata["latest_task_id"] = retry_task.id
        metadata["latest_run_id"] = retry_task.id
        metadata["last_dispatch_reason"] = (
            f"Auto-retried task {original_task.id} as {retry_task.id}"
        )

        governor_reason = str(
            (retry_task.metadata or {}).get("governor_reason")
            or (retry_task.metadata or {}).get("governor_decision")
            or ""
        ).strip()
        if governor_reason:
            metadata["governor_reason"] = governor_reason

        governor_level = str(
            (retry_task.metadata or {}).get("governor_level")
            or (retry_task.metadata or {}).get("governor_autonomy_level")
            or ""
        ).strip()
        if governor_level:
            metadata["governor_level"] = governor_level

        record["metadata"] = metadata
        if retry_task.status == "pending_approval":
            record["status"] = "waiting_approval"
        elif str(record.get("status") or "") not in {"completed", "failed", "archived"}:
            record["status"] = "scheduled"
        record["updated_at"] = retry_task.created_at or time.time()
        await upsert_backlog_record(record)
    except Exception as exc:
        logger.warning(
            "Failed to sync retry backlog lineage for task %s (backlog=%s): %s",
            retry_task.id,
            backlog_id,
            exc,
        )


def _needs_legacy_failed_task_repair(task: Task) -> bool:
    failure_display = _build_failure_display(task)
    return bool(isinstance(failure_display, dict) and failure_display.get("source") == "synthetic_legacy_gap")


def _apply_legacy_failed_task_repair(task: Task) -> Task:
    repaired = Task.from_dict(task.to_dict())
    metadata = dict(repaired.metadata or {})
    failure = dict(metadata.get("failure") or {})
    repaired_at = time.time()
    if not str(failure.get("message") or "").strip():
        failure["message"] = LEGACY_FAILED_TASK_DETAIL
    if not str(failure.get("type") or "").strip():
        failure["type"] = "historical_failure_detail_missing"
    failure["synthetic"] = True
    failure["historical_residue"] = True
    failure["repair_source"] = LEGACY_FAILURE_REPAIR_SOURCE
    failure["repaired_at"] = repaired_at
    metadata["failure"] = failure
    metadata["failure_repair"] = {
        "source": LEGACY_FAILURE_REPAIR_SOURCE,
        "repaired_at": repaired_at,
        "preserved_updated_at": repaired.updated_at,
    }
    repaired.metadata = metadata
    if not str(repaired.error or "").strip():
        repaired.error = LEGACY_FAILED_TASK_DETAIL
    return repaired


async def _maybe_retry(task: Task):
    """Auto-retry a failed task if under the retry limit.

    Creates a new task with the same parameters plus error context
    from the failed attempt. The retry gets bumped priority.
    """
    if task.retry_count >= MAX_TASK_RETRIES:
        logger.info(
            "Task %s exhausted retries (%d/%d), not retrying",
            task.id, task.retry_count, MAX_TASK_RETRIES,
        )
        return

    try:
        from .governor import Governor

        retry_metadata = _build_retry_metadata(task)
        decision = await Governor.get().gate_task_submission(
            agent=task.agent,
            prompt=task.prompt,
            priority=task.priority,
            metadata=retry_metadata,
            source="auto-retry",
        )
        retry_metadata["governor_decision"] = decision.reason
        retry_metadata["governor_autonomy_level"] = decision.autonomy_level
        retry_metadata["governor_status_override"] = decision.status_override
        if decision.status_override == "pending_approval":
            retry_metadata["requires_approval"] = True

        retry = Task(
            agent=task.agent,
            prompt=task.prompt,
            priority=task.priority,
            status=decision.status_override if decision.status_override in {"pending", "pending_approval"} else "pending",
            metadata=retry_metadata,
            parent_task_id=task.parent_task_id,
            retry_count=task.retry_count + 1,
            previous_error=_get_task_failure_context(task),
            source="auto-retry",
            lane=task.lane or task.agent,
            retry_lineage=[*task.retry_lineage, task.id],
            lease=task.lease,
            assigned_runtime=task.assigned_runtime,
            session_id=task.session_id,
        )

        await persist_task_state(retry)
        await _sync_retry_backlog_record(task, retry)

        logger.info(
            "Task %s auto-retry submitted as %s (attempt %d/%d)",
            task.id, retry.id, retry.retry_count, MAX_TASK_RETRIES,
        )

        await publish_task_event(
            {
                "event": "task_retried",
                "task_id": retry.id,
                "original_task_id": task.id,
                "retry_count": retry.retry_count,
                "timestamp": time.time(),
            }
        )

    except Exception as e:
        logger.warning("Failed to auto-retry task %s: %s", task.id, e)


async def _cleanup_old_tasks():
    """Purge completed/failed tasks past their TTL."""
    try:
        r = await _get_redis()
        now = time.time()
        removed = 0
        seen_task_ids: set[str] = set()

        for record in await read_task_records_by_statuses(r, "completed", "failed", "cancelled"):
            t = Task.from_dict(record)
            if t.id in seen_task_ids:
                continue
            seen_task_ids.add(t.id)
            if not t.completed_at:
                continue

            age = now - t.completed_at
            if t.status == "completed" and age > TASK_TTL_COMPLETED:
                await delete_task_record(r, t.id)
                removed += 1
            elif t.status in ("failed", "cancelled") and age > TASK_TTL_FAILED:
                await delete_task_record(r, t.id)
                removed += 1

        if removed:
            logger.info("Cleaned up %d expired tasks", removed)
    except Exception as e:
        logger.warning("Task cleanup error: %s", e)


async def _get_redis():
    """Reuse workspace Redis connection."""
    from .workspace import get_redis
    return await get_redis()


def _task_claim_key(task_id: str) -> str:
    return f"athanor:tasks:claim:{task_id}"


async def _release_task_claim(task_id: str) -> None:
    try:
        r = await _get_redis()
        await r.delete(_task_claim_key(task_id))
    except Exception as e:
        logger.debug("Task claim release skipped for %s: %s", task_id, e)


async def _claim_pending_task(task_id: str, *, trigger: str) -> Task | None:
    try:
        r = await _get_redis()
        claim_key = _task_claim_key(task_id)
        claimed = await r.set(claim_key, trigger, ex=TASK_CLAIM_TTL_SECONDS, nx=True)
        if not claimed:
            return None

        record = await read_task_record(r, task_id)
        if not record:
            await r.delete(claim_key)
            return None

        task = Task.from_dict(record)
        if task.status != "pending":
            await r.delete(claim_key)
            return None

        claimed_at = time.time()
        existing_metadata = task.metadata if isinstance(task.metadata, dict) else {}
        task.status = "running"
        task.started_at = claimed_at
        task.last_heartbeat = claimed_at
        task.updated_at = claimed_at
        task.metadata = {
            **existing_metadata,
            "execution_claim": {
                "trigger": trigger,
                "claimed_at": claimed_at,
            },
        }
        if trigger != "worker":
            task.metadata["manual_dispatch"] = {
                "trigger": trigger,
                "dispatched_at": claimed_at,
            }
        await persist_task_state(task)
        return task
    except Exception as e:
        logger.warning("Failed to claim task %s for %s: %s", task_id, trigger, e)
        await _release_task_claim(task_id)
        return None


async def _publish_task_event(payload: dict[str, object]) -> None:
    try:
        r = await _get_redis()
        await r.publish(TASKS_CHANNEL, json.dumps(payload))
    except Exception as e:
        logger.debug("Task event publish skipped: %s", e)


async def publish_task_event(payload: dict[str, object]) -> None:
    """Publish a task event through the canonical task-event seam."""
    await _publish_task_event(payload)


def _derive_task_source(metadata: dict | None) -> str:
    metadata = metadata if isinstance(metadata, dict) else {}
    return str(metadata.get("source") or "task_api")


def _derive_task_lane(agent: str, metadata: dict | None) -> str:
    metadata = metadata if isinstance(metadata, dict) else {}
    return str(
        metadata.get("lane")
        or metadata.get("job_family")
        or metadata.get("control_scope")
        or metadata.get("domain")
        or agent
        or _derive_task_source(metadata)
    )


async def _record_task_heartbeat(task: Task, *, force: bool = False):
    now = time.time()
    if not force and task.last_heartbeat and now - task.last_heartbeat < TASK_HEARTBEAT_INTERVAL:
        return
    task.last_heartbeat = now
    task.updated_at = now
    await persist_task_state(task)


def _task_dedup_key(agent: str, prompt: str) -> str:
    """Generate a dedup key from agent + normalized prompt prefix."""
    # Use first 200 chars of prompt for dedup (captures intent without exact match)
    normalized = prompt.strip().lower()[:200]
    h = hashlib.sha256(f"{agent}:{normalized}".encode()).hexdigest()[:16]
    return h


async def _has_duplicate_pending(agent: str, prompt: str) -> Task | None:
    """Check if there's already a pending/in-progress task for the same agent+prompt."""
    dedup_key = _task_dedup_key(agent, prompt)
    r = await _get_redis()
    for record in await read_task_records_by_statuses(r, *DEDUP_TASK_STATUSES):
        try:
            task = Task.from_dict(record)
            if task.agent != agent:
                continue
            existing_key = _task_dedup_key(task.agent, task.prompt)
            if existing_key == dedup_key:
                return task
        except Exception:
            continue
    return None


async def submit_task(
    agent: str,
    prompt: str,
    priority: str = "normal",
    metadata: dict | None = None,
    parent_task_id: str = "",
) -> Task:
    """Submit a new task for background execution.

    Returns the created Task (status=pending). The background worker
    will pick it up and execute it through the specified agent.
    Deduplicates: if a pending/in-progress task exists for the same
    agent with a similar prompt, returns the existing task instead.
    """
    from .agents import list_agents

    available = list_agents()
    if agent not in available:
        raise ValueError(f"Agent '{agent}' not found. Available: {available}")

    # Dedup check — return existing task if duplicate found
    existing = await _has_duplicate_pending(agent, prompt)
    if existing:
        logger.info(
            "Task dedup: reusing existing task %s for agent=%s (prompt=%.80s)",
            existing.id, agent, prompt,
        )
        return existing

    task_metadata = _stamp_task_execution_metadata(agent, prompt, priority, metadata)
    is_scheduler_task = task_metadata.get("source") == "scheduler"

    # Scheduler-tagged tasks usually stay on local inference to avoid unnecessary lease churn.
    # Approval and phase scope still belong to the governor-mediated submission path.
    if not is_scheduler_task and agent in BACKGROUND_TASK_EXECUTION_AGENTS:
        from .subscriptions import attach_task_execution_lease

        try:
            task_metadata = await attach_task_execution_lease(
                requester=agent,
                prompt=prompt,
                priority=priority,
                metadata=task_metadata,
            )
        except Exception as e:
            logger.warning("Failed to attach execution lease to task for %s: %s", agent, e)

    task = Task(
        agent=agent,
        prompt=prompt,
        priority=priority if priority in PRIORITY_ORDER else "normal",
        metadata=task_metadata,
        parent_task_id=parent_task_id,
        source=_derive_task_source(task_metadata),
        lane=_derive_task_lane(agent, task_metadata),
        lease=task_metadata.get("execution_lease", {}) if isinstance(task_metadata, dict) else {},
        assigned_runtime=(
            (task_metadata.get("execution_lease", {}) or {}).get("provider", "")
            if isinstance(task_metadata, dict)
            else ""
        ),
        session_id=task_metadata.get("session_id", "") if isinstance(task_metadata, dict) else "",
    )

    # Any governed caller can force an approval hold via metadata.
    if task_metadata.get("requires_approval"):
        task.status = "pending_approval"

    await persist_task_state(task)

    logger.info(
        "Task %s submitted: agent=%s priority=%s prompt=%.80s",
        task.id, agent, priority, prompt,
    )

    # Publish event for any listeners
    await publish_task_event(
        {
            "event": "task_submitted",
            "task_id": task.id,
            "agent": agent,
            "timestamp": time.time(),
        }
    )

    return task


async def submit_governed_task(
    agent: str,
    prompt: str,
    *,
    priority: str = "normal",
    metadata: dict | None = None,
    source: str,
    parent_task_id: str = "",
) -> GovernedTaskSubmission:
    """Gate and submit a task through the canonical governor-mediated path."""
    from .governor import Governor

    task_metadata = dict(metadata or {})
    task_metadata.setdefault("source", source)

    decision = await Governor.get().gate_task_submission(
        agent=agent,
        prompt=prompt,
        priority=priority,
        metadata=task_metadata,
        source=source,
    )
    task_metadata["governor_decision"] = decision.reason
    task_metadata["governor_autonomy_level"] = decision.autonomy_level
    task_metadata["governor_status_override"] = decision.status_override
    if decision.status_override == "pending_approval":
        task_metadata["requires_approval"] = True

    task = await submit_task(
        agent=agent,
        prompt=prompt,
        priority=priority,
        metadata=task_metadata,
        parent_task_id=parent_task_id,
    )
    held_for_approval = decision.status_override == "pending_approval"
    if held_for_approval and task.status != "pending_approval":
        task.status = "pending_approval"
        await persist_task_state(task)

    return GovernedTaskSubmission(
        task=task,
        decision=decision,
        held_for_approval=held_for_approval,
    )


async def get_task(task_id: str) -> Task | None:
    """Get a task by ID."""
    try:
        r = await _get_redis()
        record = await read_task_record(r, task_id)
        if record:
            return _normalize_task_for_read(Task.from_dict(record))
    except Exception as e:
        logger.warning("Failed to get task %s: %s", task_id, e)
    try:
        record = await fetch_task_snapshot(task_id)
        if record:
            return _normalize_task_for_read(Task.from_dict(record))
    except Exception as e:
        logger.warning("Durable fallback failed for task %s: %s", task_id, e)
    return None


async def list_tasks(
    status: str = "",
    agent: str = "",
    limit: int = 50,
    statuses: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict]:
    """List tasks with optional filters."""
    try:
        r = await _get_redis()
        normalized_statuses = [
            str(item).strip()
            for item in (statuses or [])
            if str(item).strip()
        ]
        if status:
            normalized_statuses.insert(0, str(status).strip())
        query_statuses = list(dict.fromkeys(normalized_statuses))
        store_limit = None if agent else limit

        if not query_statuses:
            records = await read_task_records_by_statuses(r, *TASK_STATUS_VALUES, limit=store_limit)
        elif len(query_statuses) == 1:
            records = await read_task_records_by_status(r, query_statuses[0], limit=store_limit)
        else:
            records = await read_task_records_by_statuses(r, *query_statuses, limit=store_limit)
        tasks = [Task.from_dict(record) for record in records]

        if agent:
            tasks = [t for t in tasks if t.agent == agent]

        # Sort: pending first (by priority then created_at), then recent first
        def sort_key(t):
            if t.status == "pending":
                return (0, PRIORITY_ORDER.get(t.priority, 2), t.created_at)
            return (1, 0, -t.created_at)

        tasks.sort(key=sort_key)
        tasks = [_normalize_task_for_read(t) for t in tasks]
        if limit is None:
            return [t.to_dict() for t in tasks]
        return [t.to_dict() for t in tasks[: max(int(limit), 0)]]
    except Exception as e:
        logger.warning("Failed to list tasks: %s", e)
    try:
        records = await list_task_snapshots(
            statuses=query_statuses if 'query_statuses' in locals() else statuses,
            agent=agent,
            limit=limit,
        )
        tasks = [Task.from_dict(record) for record in records]

        def sort_key(t):
            if t.status == "pending":
                return (0, PRIORITY_ORDER.get(t.priority, 2), t.created_at)
            return (1, 0, -t.created_at)

        tasks.sort(key=sort_key)
        tasks = [_normalize_task_for_read(t) for t in tasks]
        if limit is None:
            return [t.to_dict() for t in tasks]
        return [t.to_dict() for t in tasks[: max(int(limit), 0)]]
    except Exception as e:
        logger.warning("Durable fallback failed while listing tasks: %s", e)
        return []


async def list_recent_tasks(
    *,
    agent: str = "",
    limit: int | None = 50,
    statuses: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict]:
    """List tasks by recent activity using the canonical updated index."""
    try:
        r = await _get_redis()
        normalized_statuses = {
            str(item).strip()
            for item in (statuses or [])
            if str(item).strip() in TASK_STATUS_VALUES
        }
        if limit is not None and int(limit) <= 0:
            return []

        target = None if limit is None else max(int(limit), 0)
        batch_size = 100 if target is None else max(target * 3, 100)
        start = 0
        tasks: list[Task] = []
        seen_ids: set[str] = set()

        while True:
            raw_ids = await r.zrevrange(TASKS_UPDATED_KEY, start, start + batch_size - 1)
            if not raw_ids:
                break

            for raw_task_id in raw_ids:
                task_id = raw_task_id.decode() if isinstance(raw_task_id, bytes) else str(raw_task_id)
                if not task_id or task_id in seen_ids:
                    continue
                seen_ids.add(task_id)

                record = await read_task_record(r, task_id)
                if not record:
                    await r.zrem(TASKS_UPDATED_KEY, task_id)
                    continue

                task = Task.from_dict(record)
                if normalized_statuses and task.status not in normalized_statuses:
                    continue
                if agent and task.agent != agent:
                    continue

                tasks.append(task)
                if target is not None and len(tasks) >= target:
                    break

            if target is not None and len(tasks) >= target:
                break
            if len(raw_ids) < batch_size:
                break
            start += len(raw_ids)

        tasks.sort(
            key=lambda task: (
                task.updated_at or task.completed_at or task.started_at or task.created_at,
                task.id,
            ),
            reverse=True,
        )
        tasks = [_normalize_task_for_read(task) for task in tasks]
        if target is None:
            return [task.to_dict() for task in tasks]
        return [task.to_dict() for task in tasks[:target]]
    except Exception as e:
        logger.warning("Failed to list recent tasks: %s", e)
    try:
        records = await list_task_snapshots(statuses=statuses, agent=agent, limit=limit)
        tasks = [Task.from_dict(record) for record in records]
        tasks.sort(
            key=lambda task: (
                task.updated_at or task.completed_at or task.started_at or task.created_at,
                task.id,
            ),
            reverse=True,
        )
        tasks = [_normalize_task_for_read(task) for task in tasks]
        return [task.to_dict() for task in tasks]
    except Exception as durable_error:
        logger.warning("Durable fallback failed while listing recent tasks: %s", durable_error)
        return []


async def get_active_task_counts_by_agent() -> dict[str, int]:
    """Return active task counts per agent from canonical active-status indexes."""
    try:
        r = await _get_redis()
        counts: dict[str, int] = {}
        for record in await read_task_records_by_statuses(r, *ACTIVE_TASK_STATUSES):
            task = Task.from_dict(record)
            if not task.agent:
                continue
            counts[task.agent] = counts.get(task.agent, 0) + 1
        return counts
    except Exception as e:
        logger.warning("Failed to get active task counts by agent: %s", e)
        return {}


async def cancel_task(task_id: str) -> bool:
    """Cancel a pending or running task."""
    try:
        r = await _get_redis()
        record = await read_task_record(r, task_id)
        if not record:
            return False

        task = Task.from_dict(record)
        if task.status not in ACTIVE_TASK_STATUSES:
            return False

        task.status = "cancelled"
        task.completed_at = time.time()
        task.updated_at = task.completed_at
        await persist_task_state(task)
        await _release_task_claim(task_id)

        logger.info("Task %s cancelled", task_id)
        return True
    except Exception as e:
        logger.warning("Failed to cancel task %s: %s", task_id, e)
        return False


async def persist_task_state(task: Task, *, preserve_updated_at: bool = False):
    """Persist task state through the canonical durable task store."""
    redis_error = None
    try:
        r = await _get_redis()
        if not preserve_updated_at:
            task.updated_at = time.time()
        elif not task.updated_at:
            task.updated_at = task.completed_at or task.started_at or task.created_at or time.time()
        stored = await write_task_record(r, task.to_dict())
        task.__dict__.update(Task.from_dict(stored).__dict__)
    except Exception as e:
        redis_error = e
        logger.warning("Failed to update task %s in Redis: %s", task.id, e)

    try:
        await upsert_task_snapshot(task.to_dict())
        await sync_task_execution_projection(task.to_dict())
        await sync_backlog_item_from_task(task.to_dict())
    except Exception as e:
        logger.warning("Failed to update task %s in durable store: %s", task.id, e)
        if redis_error is not None:
            logger.warning("Task %s lost both Redis and durable-state persistence paths", task.id)


async def repair_legacy_failed_task_details(*, limit: int | None = None) -> int:
    """Backfill structured failure detail onto legacy blank-error failed rows.

    This preserves the original timestamps so repaired historical residue does
    not show up as a fresh operational failure wave.
    """

    try:
        r = await _get_redis()
        failed_records = await read_task_records_by_status(r, "failed", limit=limit)
    except Exception as exc:
        logger.warning("Failed to scan legacy failed tasks for repair: %s", exc)
        return 0

    repaired_count = 0
    for record in failed_records:
        task = Task.from_dict(record)
        if not _needs_legacy_failed_task_repair(task):
            continue
        repaired_task = _apply_legacy_failed_task_repair(task)
        await persist_task_state(repaired_task, preserve_updated_at=True)
        repaired_count += 1

    if repaired_count:
        logger.info("Repaired %d legacy failed task records with durable failure metadata", repaired_count)
    return repaired_count


async def _get_next_pending() -> Task | None:
    """Get the highest-priority pending task."""
    try:
        r = await _get_redis()
        pending = [Task.from_dict(record) for record in await read_task_records_by_status(r, "pending")]

        if not pending:
            return None

        # Sort by priority (critical first), then by created_at (oldest first)
        pending.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 2), t.created_at))
        return pending[0]
    except Exception as e:
        logger.warning("Failed to get next pending task: %s", e)
        return None


async def approve_task(task_id: str, *, decided_by: str = "operator") -> bool:
    """Approve a pending_approval task, moving it to pending for execution."""
    task = await get_task(task_id)
    if not task:
        return False
    if task.status != "pending_approval":
        return False
    task.metadata = {
        **dict(task.metadata or {}),
        "approval_decided": True,
        "approval_decided_at": time.time(),
        "approval_decided_by": decided_by,
        "approval_rejected": False,
    }
    task.status = "pending"
    await persist_task_state(task)
    logger.info("Task %s approved for execution (agent=%s)", task_id, task.agent)
    return True


async def reject_task(task_id: str, reason: str = "Rejected by operator", *, decided_by: str = "operator") -> bool:
    """Reject a pending_approval task."""
    task = await get_task(task_id)
    if not task:
        return False
    if task.status != "pending_approval":
        return False
    task.metadata = {
        **dict(task.metadata or {}),
        "approval_decided": True,
        "approval_decided_at": time.time(),
        "approval_decided_by": decided_by,
        "approval_rejected": True,
        "approval_reason": reason,
    }
    task.status = "cancelled"
    task.result = reason
    await persist_task_state(task)
    logger.info("Task %s rejected (agent=%s): %s", task_id, task.agent, reason)
    return True


async def _record_skill_execution_for_task(task: Task, success: bool):
    """Fire-and-forget: record task outcome against the best matching skill.

    Only records if the task prompt matches a skill above the 0.3 relevance
    threshold. Silently skips if no match or skill library is unavailable.
    """
    try:
        from .skill_learning import find_matching_skill, record_execution
        match = await find_matching_skill(task.prompt, threshold=0.3)
        if match:
            skill_id, relevance = match
            await record_execution(
                skill_id=skill_id,
                success=success,
                duration_ms=float(task.duration_ms or 0),
                context={"task_id": task.id, "agent": task.agent, "relevance": round(relevance, 2)},
            )
            logger.debug(
                "Skill execution recorded: skill=%s success=%s relevance=%.2f task=%s",
                skill_id, success, relevance, task.id,
            )
    except Exception as e:
        logger.debug("Skill recording skipped for task %s: %s", task.id, e)


async def _auto_extract_skill(task: Task):
    """Fire-and-forget: extract a reusable skill from a successful task's tool sequence."""
    try:
        from .skill_learning import extract_skill_from_task
        skill_id = await extract_skill_from_task(
            task_id=task.id,
            agent=task.agent,
            prompt=task.prompt,
            steps=task.steps,
            quality_score=0.8,  # default for completed tasks; overridden by judge if available
        )
        if skill_id:
            logger.info("Auto-extracted skill %s from task %s", skill_id, task.id)
    except Exception as e:
        logger.debug("Skill extraction skipped for task %s: %s", task.id, e)


def _task_execution_lease(task: Task) -> dict[str, Any]:
    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    lease = metadata.get("execution_lease", {})
    return dict(lease) if isinstance(lease, dict) else {}


def _task_execution_model_override(task: Task) -> str | None:
    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    explicit_override = str(metadata.get("task_execution_model_override") or "").strip()
    if explicit_override:
        return explicit_override

    lease = _task_execution_lease(task)
    provider = str(lease.get("provider") or "").strip()
    return INTERNAL_EXECUTION_PROVIDER_MODELS.get(provider)


def _should_use_provider_execution(task: Task) -> bool:
    metadata = task.metadata if isinstance(task.metadata, dict) else {}
    lease = _task_execution_lease(task)
    provider = str(lease.get("provider") or "").strip()
    task_class = str(metadata.get("task_class") or lease.get("task_class") or "").strip()
    if not provider or provider == "athanor_local":
        return False
    if _task_execution_model_override(task):
        return False
    if task.agent not in BACKGROUND_TASK_EXECUTION_AGENTS:
        return False
    if bool(metadata.get("interactive", False)):
        return False
    return task_class in PROVIDER_EXECUTION_TASK_CLASSES


def _normalize_governed_proof_commands(metadata: dict[str, Any]) -> list[list[str]]:
    commands = metadata.get("proof_commands")
    if not isinstance(commands, list):
        return []
    normalized: list[list[str]] = []
    for command in commands:
        if not isinstance(command, (list, tuple)):
            return []
        parts = [str(part).strip() for part in command if str(part).strip()]
        if len(parts) < 2:
            return []
        script_path = parts[1].replace("\\", "/")
        if script_path not in ALLOWED_GOVERNED_PROOF_SCRIPTS:
            return []
        normalized.append(parts)
    return normalized


def _should_use_governed_proof_execution(task: Task) -> bool:
    metadata = dict(task.metadata or {})
    if task.agent != "coding-agent":
        return False
    if str(metadata.get("source") or "").strip() != "operator_backlog":
        return False
    if str(metadata.get("materialization_source") or "").strip() != "governed_dispatch_state":
        return False
    if not bool(metadata.get("_autonomy_managed")):
        return False
    if bool(metadata.get("interactive", False)):
        return False
    return bool(_normalize_governed_proof_commands(metadata))


def _governed_proof_execution_stage(task: Task) -> str:
    metadata = dict(task.metadata or {})
    explicit_stage = str(metadata.get("proof_execution_stage") or "").strip().lower()
    if explicit_stage in {"before_agent", "after_agent"}:
        return explicit_stage
    if not _should_use_governed_proof_execution(task):
        return ""
    if str(metadata.get("preferred_lane_family") or "").strip() == "safe_surface_execution":
        return "after_agent"
    return "before_agent"


def _truncate_governed_proof_output(text: str, *, limit: int = MAX_GOVERNED_PROOF_OUTPUT_CHARS) -> str:
    normalized = str(text or "")
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n...[truncated]"


def _governed_proof_artifact_candidates(relative_path: str, proof_environment: dict[str, str]) -> list[Path]:
    normalized = str(relative_path or "").strip()
    if not normalized:
        return []

    path = Path(normalized)
    candidates = [REPO_ROOT / path]

    implementation_authority = str(
        proof_environment.get("ATHANOR_IMPLEMENTATION_AUTHORITY")
        or os.environ.get("ATHANOR_IMPLEMENTATION_AUTHORITY")
        or ""
    ).strip()
    if implementation_authority:
        candidates.append(Path(implementation_authority) / path)

    runtime_artifact_root = str(
        proof_environment.get("ATHANOR_RUNTIME_ARTIFACT_ROOT")
        or os.environ.get("ATHANOR_RUNTIME_ARTIFACT_ROOT")
        or ""
    ).strip()
    if runtime_artifact_root:
        candidates.append(Path(runtime_artifact_root) / path)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _hash_governed_proof_artifact(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_governed_proof_artifact_state(
    relative_paths: list[str],
    proof_environment: dict[str, str],
) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for artifact_path in relative_paths:
        normalized = str(artifact_path or "").strip()
        if not normalized or normalized in snapshots:
            continue

        snapshot: dict[str, Any] = {"exists": False}
        for candidate in _governed_proof_artifact_candidates(normalized, proof_environment):
            if not candidate.exists():
                continue
            stat = candidate.stat()
            snapshot = {
                "exists": True,
                "candidate": str(candidate),
                "sha256": _hash_governed_proof_artifact(candidate),
                "size_bytes": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
            }
            break
        snapshots[normalized] = snapshot
    return snapshots


def _governed_proof_artifact_deltas(
    baseline: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> list[str]:
    changed: list[str] = []
    for relative_path, current_state in current.items():
        baseline_state = dict(baseline.get(relative_path) or {})
        if baseline_state.get("exists") != current_state.get("exists"):
            changed.append(relative_path)
            continue
        if not current_state.get("exists"):
            continue
        if baseline_state.get("candidate") != current_state.get("candidate"):
            changed.append(relative_path)
            continue
        if baseline_state.get("sha256") != current_state.get("sha256"):
            changed.append(relative_path)
            continue
    return changed


def _governed_proof_working_root(task: Task, proof_environment: dict[str, str]) -> Path:
    metadata = dict(task.metadata or {})
    implementation_authority = str(
        proof_environment.get("ATHANOR_IMPLEMENTATION_AUTHORITY")
        or os.environ.get("ATHANOR_IMPLEMENTATION_AUTHORITY")
        or ""
    ).strip()
    if implementation_authority:
        candidate = Path(implementation_authority)
        if candidate.exists() and (
            str(metadata.get("proof_execution_stage") or "").strip().lower() == "after_agent"
            or str(metadata.get("preferred_lane_family") or "").strip() == "safe_surface_execution"
            or bool(metadata.get("requires_mutable_implementation_authority"))
        ):
            return candidate
    return REPO_ROOT


async def _execute_task_via_governed_proof_bundle(task: Task) -> bool:
    metadata = dict(task.metadata or {})
    commands = _normalize_governed_proof_commands(metadata)
    if not commands:
        return False

    proof_results: list[dict[str, Any]] = []
    artifact_refs: list[str] = []
    report_path = str(metadata.get("report_path") or "").strip()
    timeout_seconds = int(metadata.get("proof_timeout_seconds") or GOVERNED_PROOF_TIMEOUT_SECONDS)
    proof_environment = {
        str(key): str(value)
        for key, value in dict(metadata.get("proof_environment") or {}).items()
        if str(key).strip()
    }
    proof_artifact_paths = [
        str(item).strip()
        for item in list(metadata.get("proof_artifact_paths") or [])
        if str(item).strip()
    ]
    working_root = _governed_proof_working_root(task, proof_environment)

    for command in commands:
        started_at = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(working_root),
                env={**os.environ, **proof_environment},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            result = {
                "command": command,
                "exit_code": process.returncode,
                "duration_ms": max(int((time.time() - started_at) * 1000), 1),
                "stdout": _truncate_governed_proof_output(stdout_text),
                "stderr": _truncate_governed_proof_output(stderr_text, limit=2000),
            }
        except asyncio.TimeoutError:
            result = {
                "command": command,
                "exit_code": None,
                "duration_ms": max(int((time.time() - started_at) * 1000), 1),
                "stdout": "",
                "stderr": f"Governed proof command timed out after {timeout_seconds}s.",
            }
        proof_results.append(result)
        task.steps.append(
            {
                "index": len(task.steps),
                "type": "governed_proof_command",
                "command": command,
                "exit_code": result["exit_code"],
                "duration_ms": result["duration_ms"],
                "timestamp": time.time(),
            }
        )
        if result["exit_code"] != 0:
            metadata["verification_passed"] = False
            metadata["verification_status"] = "failed"
            metadata["proof_command_results"] = proof_results
            task.metadata = metadata
            _stamp_task_failure(
                task,
                error_message=result["stderr"] or f"Governed proof command failed: {' '.join(command)}",
                failure_type="governed_proof_failed",
                retry_eligible=task.retry_count < MAX_TASK_RETRIES,
                stage="governed_proof",
            )
            await persist_task_state(task)
            await _maybe_retry(task)
            return True

    if report_path:
        for candidate in _governed_proof_artifact_candidates(report_path, proof_environment):
            if candidate.exists():
                artifact_refs.append(report_path)
                break
    for artifact_path in proof_artifact_paths:
        normalized = str(artifact_path or "").strip()
        if not normalized or normalized in artifact_refs:
            continue
        for candidate in _governed_proof_artifact_candidates(normalized, proof_environment):
            if candidate.exists():
                artifact_refs.append(normalized)
                break

    baseline_artifact_state = {
        str(key): dict(value)
        for key, value in dict(metadata.get("proof_artifact_baseline") or {}).items()
        if str(key).strip()
    }
    current_artifact_state = _snapshot_governed_proof_artifact_state(proof_artifact_paths, proof_environment)
    proof_artifact_deltas = _governed_proof_artifact_deltas(baseline_artifact_state, current_artifact_state)
    metadata["proof_artifact_state"] = current_artifact_state
    metadata["proof_artifact_deltas"] = proof_artifact_deltas

    if (
        str(metadata.get("proof_execution_stage") or "").strip().lower() == "after_agent"
        and proof_artifact_paths
        and not proof_artifact_deltas
    ):
        metadata["verification_passed"] = False
        metadata["verification_status"] = "failed"
        metadata["proof_command_results"] = proof_results
        task.metadata = metadata
        _stamp_task_failure(
            task,
            error_message=(
                "Governed proof bundle passed, but no delta was observed on required proof artifacts: "
                + ", ".join(proof_artifact_paths)
            ),
            failure_type="governed_proof_missing_delta",
            retry_eligible=task.retry_count < MAX_TASK_RETRIES,
            stage="governed_proof",
        )
        await persist_task_state(task)
        await _maybe_retry(task)
        return True

    metadata["verification_passed"] = True
    metadata["verification_status"] = "passed"
    metadata["proof_command_results"] = proof_results
    metadata.pop("failure", None)
    metadata.pop("failure_detail", None)
    metadata.pop("failure_repair", None)
    if artifact_refs:
        metadata["proof_artifacts"] = artifact_refs
    task.metadata = metadata
    task.status = "completed"
    task.error = ""
    task.result = json.dumps(
        {
            "status": "success",
            "message": "Governed proof bundle executed successfully.",
            "proof_command_surface": str(metadata.get("proof_command_surface") or ""),
            "commands": proof_results,
            "artifacts": artifact_refs,
        },
        indent=2,
        sort_keys=True,
    )
    task.completed_at = time.time()
    await persist_task_state(task)
    return True


def _build_provider_execution_metadata(provider_result: dict[str, Any]) -> dict[str, Any]:
    handoff = dict(provider_result.get("handoff") or {})
    adapter = dict(provider_result.get("adapter") or {})
    execution = dict(provider_result.get("execution") or {})
    payload: dict[str, Any] = {
        "status": str(provider_result.get("status") or ""),
        "provider": str(provider_result.get("provider") or handoff.get("provider") or ""),
        "message": str(provider_result.get("message") or ""),
        "recorded_at": time.time(),
        "handoff_id": str(handoff.get("id") or ""),
        "lease_id": str(handoff.get("lease_id") or ""),
        "handoff_status": str(handoff.get("status") or ""),
        "handoff_execution_mode": str(handoff.get("execution_mode") or ""),
        "handoff_result_summary": str(handoff.get("result_summary") or ""),
        "fallback_from_execution_mode": str(handoff.get("fallback_from_execution_mode") or ""),
        "fallback_reason": str(handoff.get("fallback_reason") or ""),
        "artifact_refs": list(handoff.get("artifact_refs") or []),
        "adapter": {
            "execution_mode": str(adapter.get("execution_mode") or ""),
            "adapter_available": bool(adapter.get("adapter_available")),
            "availability_state": str(adapter.get("availability_state") or ""),
            "bridge_status": str(adapter.get("bridge_status") or ""),
            "probe_status": str(adapter.get("probe_status") or ""),
        },
    }
    if execution:
        payload["execution"] = {
            "summary": str(execution.get("summary") or ""),
            "duration_ms": int(execution.get("duration_ms", 0) or 0),
            "exit_code": execution.get("exit_code"),
            "stderr": str(execution.get("stderr") or "")[:2000],
        }
    return payload


def _render_provider_execution_result(provider_result: dict[str, Any]) -> str:
    metadata = _build_provider_execution_metadata(provider_result)
    adapter_meta = dict(metadata.get("adapter") or {})
    execution_meta = dict(metadata.get("execution") or {})
    summary = (
        str(metadata.get("handoff_result_summary") or "").strip()
        or str(execution_meta.get("summary") or "").strip()
        or str(metadata.get("message") or "").strip()
    )
    execution_mode = str(
        adapter_meta.get("execution_mode")
        or metadata.get("handoff_execution_mode")
        or ""
    ).strip()
    lines = [
        f"Provider lane: {metadata.get('provider') or 'unknown'}",
        f"Outcome: {metadata.get('status') or 'unknown'}",
    ]
    if metadata.get("handoff_id"):
        lines.append(f"Handoff bundle: {metadata['handoff_id']}")
    if execution_mode:
        lines.append(f"Execution mode: {execution_mode}")
    if summary:
        lines.append(f"Summary: {summary}")
    if metadata.get("fallback_reason"):
        lines.append(f"Fallback reason: {metadata['fallback_reason']}")
    return "\n".join(lines)


def _provider_execution_failure_message(provider_result: dict[str, Any]) -> str:
    metadata = _build_provider_execution_metadata(provider_result)
    execution_meta = dict(metadata.get("execution") or {})
    for candidate in (
        str(execution_meta.get("stderr") or "").strip(),
        str(execution_meta.get("summary") or "").strip(),
        str(metadata.get("fallback_reason") or "").strip(),
        str(metadata.get("message") or "").strip(),
    ):
        if candidate:
            return candidate[:2000]
    status = str(metadata.get("status") or "failed").strip() or "failed"
    provider = str(metadata.get("provider") or "provider").strip() or "provider"
    return f"{provider} execution {status}"


async def _execute_task_via_provider(task: Task) -> bool:
    from .provider_execution import execute_provider_request

    metadata = dict(task.metadata or {})
    lease = _task_execution_lease(task)
    provider = str(lease.get("provider") or "").strip()
    provider_meta = dict(lease.get("metadata") or {})
    task_class = str(metadata.get("task_class") or lease.get("task_class") or "").strip()

    provider_result = await execute_provider_request(
        requester=task.agent,
        prompt=task.prompt,
        task_class=task_class,
        sensitivity=str(metadata.get("sensitivity") or "repo_internal"),
        interactive=bool(metadata.get("interactive", False)),
        expected_context=str(
            metadata.get("expected_context")
            or provider_meta.get("expected_context")
            or "medium"
        ),
        parallelism=str(
            metadata.get("parallelism")
            or provider_meta.get("parallelism")
            or "low"
        ),
        metadata=metadata,
        issue_lease=False,
    )

    provider_execution = _build_provider_execution_metadata(provider_result)
    metadata["provider_execution"] = provider_execution
    task.metadata = metadata
    task.steps.append(
        {
            "index": len(task.steps),
            "type": "provider_execution",
            "provider": provider or provider_execution.get("provider") or "unknown",
            "status": provider_execution.get("status") or "unknown",
            "execution_mode": str(
                (provider_execution.get("adapter") or {}).get("execution_mode")
                or provider_execution.get("handoff_execution_mode")
                or ""
            ),
            "handoff_id": provider_execution.get("handoff_id") or "",
            "timestamp": time.time(),
        }
    )

    status = str(provider_execution.get("status") or "").strip()
    if status == "local_runtime":
        return False

    if status in {"completed", "handoff_created", "fallback_to_handoff"}:
        task.status = "completed"
        task.result = _render_provider_execution_result(provider_result)
        task.completed_at = time.time()
        await persist_task_state(task)
        logger.info(
            "Task %s closed via provider execution: provider=%s status=%s handoff=%s",
            task.id,
            provider_execution.get("provider") or provider or "unknown",
            status,
            provider_execution.get("handoff_id") or "none",
        )
        return True

    _stamp_task_failure(
        task,
        error_message=_provider_execution_failure_message(provider_result),
        failure_type=f"provider_execution_{status or 'failed'}",
        retry_eligible=task.retry_count < MAX_TASK_RETRIES,
        stage="provider_execution",
    )
    await persist_task_state(task)
    logger.warning(
        "Task %s provider execution failed: provider=%s status=%s",
        task.id,
        provider_execution.get("provider") or provider or "unknown",
        status or "failed",
    )
    await _maybe_retry(task)
    return True


async def _execute_task(task: Task):
    """Execute a task through its agent, capturing tool call steps."""
    from .agents import get_agent
    from .context import enrich_context
    from .activity import log_activity
    from .workspace import post_item
    from .circuit_breaker import get_circuit_breakers

    global _running_count
    _running_count += 1

    _breakers = get_circuit_breakers()
    _agent_breaker = _breakers.get_or_create(task.agent)

    try:
        if task.status != "running" or not task.started_at or not task.last_heartbeat:
            task.status = "running"
            task.started_at = task.started_at or time.time()
            task.last_heartbeat = task.started_at
            await persist_task_state(task)

        proof_execution_stage = _governed_proof_execution_stage(task)
        if proof_execution_stage == "before_agent":
            if await _execute_task_via_governed_proof_bundle(task):
                return

        if _should_use_provider_execution(task):
            if await _execute_task_via_provider(task):
                return

        model_override = _task_execution_model_override(task)
        agent = get_agent(task.agent, model_override=model_override) if model_override else get_agent(task.agent)
        if agent is None:
            _stamp_task_failure(
                task,
                error_message=f"Agent '{task.agent}' not available",
                failure_type="agent_unavailable",
                retry_eligible=False,
                stage="agent_lookup",
            )
            await persist_task_state(task)
            return

        # Circuit breaker check — if this agent has failed too many times recently, skip
        if not await _agent_breaker.can_execute():
            _stamp_task_failure(
                task,
                error_message=f"Circuit breaker open for {task.agent} — cooling down after repeated failures",
                failure_type="circuit_breaker_open",
                retry_eligible=False,
                stage="circuit_breaker",
            )
            await persist_task_state(task)
            logger.warning("Task %s skipped — circuit open for %s", task.id, task.agent)
            return

        # Build messages — inject context and task prompt into HumanMessage
        # to avoid multiple SystemMessages (vLLM rejects mid-conversation system msgs,
        # and create_react_agent already has its own system prompt)
        context_str = ""
        try:
            context_str = await enrich_context(task.agent, task.prompt) or ""
        except Exception as e:
            logger.debug("Context enrichment failed, proceeding without: %s", e)

        messages = [
            HumanMessage(
                content=_build_task_message_content(
                    task,
                    context_str,
                    _build_task_prompt(task),
                )
            ),
        ]

        if proof_execution_stage == "after_agent":
            metadata = dict(task.metadata or {})
            proof_environment = {
                str(key): str(value)
                for key, value in dict(metadata.get("proof_environment") or {}).items()
                if str(key).strip()
            }
            proof_artifact_paths = [
                str(item).strip()
                for item in list(metadata.get("proof_artifact_paths") or [])
                if str(item).strip()
            ]
            metadata["proof_artifact_baseline"] = _snapshot_governed_proof_artifact_state(
                proof_artifact_paths,
                proof_environment,
            )
            task.metadata = metadata
            await persist_task_state(task)

        thread_id = f"task-{task.id}"
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
            "metadata": {"agent": task.agent, "task_id": task.id},
            "tags": [task.agent],
        }

        step_index = 0
        collected_text = []
        tools_used = []

        # Stream execution to capture steps
        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            # Check for cancellation
            refreshed = await get_task(task.id)
            if refreshed and refreshed.status == "cancelled":
                logger.info("Task %s cancelled during execution", task.id)
                return

            # Check timeout (per-agent override for deep work agents)
            agent_timeout = AGENT_TIMEOUTS.get(task.agent, TASK_TIMEOUT)
            if time.time() - task.started_at > agent_timeout:
                _stamp_task_failure(
                    task,
                    error_message=f"Task timed out after {agent_timeout}s",
                    failure_type="task_timeout",
                    retry_eligible=False,
                    stage="execution",
                )
                await persist_task_state(task)
                return

            await _record_task_heartbeat(task)

            kind = event["event"]

            if kind == "on_tool_start":
                name = event.get("name", "unknown")
                run_id = str(event.get("run_id") or "").strip()
                args = event.get("data", {}).get("input", {})
                tools_used.append(name)
                step = {
                    "index": step_index,
                    "type": "tool_call",
                    "tool_name": name,
                    "tool_input": args,
                    "timestamp": time.time(),
                }
                if run_id:
                    step["tool_run_id"] = run_id
                task.steps.append(step)
                step_index += 1
                # Persist steps after every tool call for real-time visibility
                await persist_task_state(task)

            elif kind == "on_tool_end":
                name = event.get("name", "unknown")
                run_id = str(event.get("run_id") or "").strip()
                output = str(event.get("data", {}).get("output", ""))[:2000]
                matched_step = None
                if run_id:
                    for step in reversed(task.steps):
                        if step.get("tool_run_id") == run_id:
                            matched_step = step
                            break
                if matched_step is None:
                    for step in reversed(task.steps):
                        if step.get("tool_name") == name and "tool_output" not in step:
                            matched_step = step
                            break
                if matched_step is not None:
                    matched_step["tool_output"] = output

            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                text = chunk.content if hasattr(chunk, "content") else ""
                if text:
                    collected_text.append(text)

        # Task completed successfully — strip thinking artifacts from result
        import re
        result_text = "".join(collected_text)

        # Layer 1: If </think> exists, everything before it is CoT
        last_think_close = result_text.rfind("</think>")
        if last_think_close >= 0:
            result_text = result_text[last_think_close + len("</think>"):]

        # Layer 2: Strip orphaned <think> tags
        result_text = re.sub(r"</?think>\s*", "", result_text)

        # Layer 3: Strip untagged CoT preamble (Qwen3.5 dumps reasoning as plain text)
        # Pattern: "The user wants...", "Let me...", "I need to..." followed by plan/analysis
        # then the actual response. Look for the transition point.
        cot_patterns = [
            # "The user wants X. [analysis...] \n\n[actual response]"
            r"^(?:The user (?:wants|is asking|asked).*?\n\n)",
            # "Let me [think/plan/check]...\n\n[actual response]"
            r"^(?:Let me (?:think|plan|check|analyze|look|start|review).*?\n\n)",
            # "I need to [do X]...\n\n[actual response]"
            r"^(?:I need to .*?\n\n)",
            # "</think>\n" leftover
            r"^</think>\s*",
        ]
        for pattern in cot_patterns:
            result_text = re.sub(pattern, "", result_text, count=1, flags=re.DOTALL)

        result_text = result_text.strip()

        if proof_execution_stage == "after_agent":
            if not any(step.get("type") == "tool_call" for step in task.steps):
                _stamp_task_failure(
                    task,
                    error_message="Task produced no execution evidence before governed proof.",
                    failure_type="no_execution_evidence",
                    retry_eligible=task.retry_count < MAX_TASK_RETRIES,
                    stage="execution",
                )
                await persist_task_state(task)
                await _maybe_retry(task)
                return

            metadata = dict(task.metadata or {})
            if result_text:
                metadata["implementation_result_summary"] = result_text[:2000]
            task.metadata = metadata
            proof_executed = await _execute_task_via_governed_proof_bundle(task)
            if proof_executed:
                if task.status != "completed":
                    return
                result_text = str(task.result or "").strip()
            else:
                task.status = "completed"
                task.result = result_text
                task.completed_at = time.time()
                await persist_task_state(task)
        else:
            task.status = "completed"
            task.result = result_text
            task.completed_at = time.time()
            await persist_task_state(task)
        await _agent_breaker.record_success()

        logger.info(
            "Task %s completed: agent=%s steps=%d duration=%dms",
            task.id, task.agent, len(task.steps), task.duration_ms or 0,
        )

        # Log activity + conversation + event
        asyncio.create_task(log_activity(
            agent=task.agent,
            action_type="task",
            input_summary=task.prompt[:500],
            output_summary=result_text[:500],
            tools_used=tools_used,
            duration_ms=task.duration_ms,
        ))
        from .activity import log_conversation
        asyncio.create_task(log_conversation(
            agent=task.agent,
            user_message=task.prompt,
            assistant_response=result_text,
            tools_used=tools_used,
            duration_ms=task.duration_ms,
            thread_id=task.id,
        ))
        from .activity import log_event
        asyncio.create_task(log_event(
            event_type="task_completed",
            agent=task.agent,
            description=task.prompt[:200],
            data={"task_id": task.id, "steps": len(task.steps), "duration_ms": task.duration_ms, "tools": tools_used},
        ))

        # Record skill execution outcome (learning feedback loop)
        asyncio.create_task(_record_skill_execution_for_task(task, success=True))

        # Auto-extract skills from successful task traces (Layer 3)
        asyncio.create_task(_auto_extract_skill(task))

        # Notify on notable completions (skip routine health/home checks)
        prompt_lower = (task.prompt or "").lower()
        is_routine = any(kw in prompt_lower for kw in ["health check", "entities", "queue items", "check for any active"])
        task_source = task.metadata.get("source", "")
        if not is_routine and task_source not in ("scheduler", "auto_retry"):
            from .escalation import add_notification
            add_notification(
                agent=task.agent,
                action=f"Task completed ({task.duration_ms or 0}ms)",
                category="routine",
                confidence=1.0,
                description=f"{task.prompt[:120]}\n\nResult: {result_text[:150]}",
            )

        # Broadcast completion to GWT workspace
        asyncio.create_task(post_item(
            source_agent=task.agent,
            content=f"Task completed: {task.prompt[:100]}",
            priority="normal",
            ttl=300,
            metadata={
                "task_id": task.id,
                "status": "completed",
                "steps": len(task.steps),
                "duration_ms": task.duration_ms,
            },
        ))

    except Exception as e:
        failure = _describe_exception(e)
        _stamp_task_failure(
            task,
            error_message=failure["message"],
            failure_type=failure["type"],
            retry_eligible=task.retry_count < MAX_TASK_RETRIES,
            exception_repr=failure["repr"],
            stage="execution_exception",
        )
        await persist_task_state(task)
        await _agent_breaker.record_failure()
        logger.error("Task %s failed: %s", task.id, failure["message"], exc_info=True)

        # Log failure event
        from .activity import log_event
        asyncio.create_task(log_event(
            event_type="task_failed",
            agent=task.agent,
            description=f"{task.prompt[:150]} — {failure['message'][:100]}",
            data={
                "task_id": task.id,
                "error": failure["message"][:500],
                "error_type": failure["type"],
            },
        ))

        # Notify on task failures (always — failures need attention)
        from .escalation import add_notification
        add_notification(
            agent=task.agent,
            action=f"Task failed (retry={task.retry_count})",
            category="routine",
            confidence=0.6,
            description=f"{task.prompt[:120]}\n\nError: {failure['message'][:150]}",
        )

        # Broadcast failure
        from .workspace import post_item
        asyncio.create_task(post_item(
            source_agent=task.agent,
            content=f"Task failed: {task.prompt[:80]} — {failure['message'][:100]}",
            priority="high",
            ttl=600,
            metadata={
                "task_id": task.id,
                "status": "failed",
                "error": failure["message"],
                "error_type": failure["type"],
            },
        ))

        # Record skill execution failure (learning feedback loop)
        asyncio.create_task(_record_skill_execution_for_task(task, success=False))

        # Auto-retry if under retry limit
        await _maybe_retry(task)

    finally:
        await _release_task_claim(task.id)
        _running_count -= 1


async def _recover_stale_tasks():
    """On startup, convert any in-flight tasks into durable stale-lease records.

    Stale running tasks remain queryable and may spawn one bounded retry with
    explicit lineage instead of silently disappearing into a server restart.
    """
    try:
        r = await _get_redis()
        recovered = 0
        retried = 0
        for record in await read_task_records_by_status(r, "running"):
            t = Task.from_dict(record)
            now = time.time()
            t.status = "stale_lease"
            t.error = "Execution lease expired during server restart"
            t.completed_at = now
            t.updated_at = now
            t.metadata = {
                **t.metadata,
                "recovery": {
                    "event": "stale_lease_recovered",
                    "recovered_at": now,
                    "reason": "server_restart",
                },
            }
            await persist_task_state(t)
            recovered += 1
            if t.retry_count < MAX_TASK_RETRIES:
                await _maybe_retry(t)
                retried += 1
        if recovered:
            logger.info(
                "Recovered %d stale tasks from prior crash (%d queued for retry)",
                recovered,
                retried,
            )
    except Exception as e:
        logger.warning("Failed to recover stale tasks: %s", e)


async def _evaluate_dispatch_gate(task: Task) -> tuple[bool, str]:
    """Check whether a pending task should execute right now."""
    try:
        from .scheduling import get_inference_load, should_execute_task

        load = await get_inference_load()
        allowed, reason = should_execute_task(task.agent, load)
        if not allowed:
            logger.info(
                "Task %s deferred (agent=%s): %s",
                task.id,
                task.agent,
                reason,
            )
        return allowed, reason
    except Exception as e:
        logger.debug("Scheduling check failed, allowing task: %s", e)
        return True, ""


async def dispatch_next_pending_task(*, trigger: str = "manual") -> dict:
    """Dispatch the next pending task immediately through the canonical task engine."""
    if _running_count >= MAX_CONCURRENT_TASKS:
        return {
            "status": "busy",
            "message": "Task engine is already at max concurrency",
            "currently_running": _running_count,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "worker_running": _worker_task is not None and not _worker_task.done(),
        }

    task = await _get_next_pending()
    if not task:
        return {
            "status": "empty",
            "message": "No pending tasks available for dispatch",
            "currently_running": _running_count,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "worker_running": _worker_task is not None and not _worker_task.done(),
        }

    allowed, reason = await _evaluate_dispatch_gate(task)
    if not allowed:
        return {
            "status": "deferred",
            "message": reason,
            "task": task.to_dict(),
            "currently_running": _running_count,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "worker_running": _worker_task is not None and not _worker_task.done(),
        }

    claimed_task = await _claim_pending_task(task.id, trigger=trigger)
    if claimed_task is None:
        return {
            "status": "claimed_elsewhere",
            "message": "Task was claimed before dispatch could reserve it",
            "task": task.to_dict(),
            "currently_running": _running_count,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "worker_running": _worker_task is not None and not _worker_task.done(),
        }

    asyncio.create_task(_execute_task(claimed_task))
    logger.info(
        "Task %s manually dispatched (agent=%s trigger=%s)",
        claimed_task.id,
        claimed_task.agent,
        trigger,
    )
    return {
        "status": "dispatched",
        "task": claimed_task.to_dict(),
        "currently_running": _running_count + 1,
        "max_concurrent": MAX_CONCURRENT_TASKS,
        "worker_running": _worker_task is not None and not _worker_task.done(),
    }


async def _task_worker_loop():
    """Background worker — polls for pending tasks, executes them.

    Runs continuously. Picks up to MAX_CONCURRENT_TASKS simultaneously.
    Priority ordering: critical > high > normal > low, then FIFO.
    Runs cleanup every CLEANUP_INTERVAL seconds.
    """
    logger.info(
        "Task worker started (interval=%.1fs, max_concurrent=%d)",
        TASK_WORKER_INTERVAL, MAX_CONCURRENT_TASKS,
    )

    last_cleanup = time.time()

    while True:
        try:
            if _running_count < MAX_CONCURRENT_TASKS:
                task = await _get_next_pending()
                if task:
                    allowed, _ = await _evaluate_dispatch_gate(task)
                    if allowed:
                        claimed_task = await _claim_pending_task(task.id, trigger="worker")
                        if claimed_task:
                            asyncio.create_task(_execute_task(claimed_task))
                            logger.info(
                                "Task %s picked up by worker (agent=%s, running=%d)",
                                claimed_task.id, claimed_task.agent, _running_count + 1,
                            )

            # Periodic cleanup of expired tasks
            if time.time() - last_cleanup > CLEANUP_INTERVAL:
                await _cleanup_old_tasks()
                last_cleanup = time.time()

        except Exception as e:
            logger.warning("Task worker poll error: %s", e)

        await asyncio.sleep(TASK_WORKER_INTERVAL)


async def start_task_worker():
    """Start the background task worker."""
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        logger.info("Task worker already running")
        return

    try:
        r = await _get_redis()
        indexed = await backfill_task_store_indexes(r)
        if indexed:
            logger.info("Task store index backfill complete for %d tasks", indexed)
        repaired = await repair_legacy_failed_task_details()
        if repaired:
            logger.info("Legacy failed-task repair complete for %d tasks", repaired)
        await _recover_stale_tasks()
        _worker_task = asyncio.create_task(_task_worker_loop())
        logger.info("Task execution engine started")
    except Exception as e:
        logger.warning("Failed to start task worker: %s", e)


async def stop_task_worker():
    """Stop the background task worker."""
    global _worker_task
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
        logger.info("Task execution engine stopped")


async def get_task_stats() -> dict:
    """Get task execution statistics."""
    redis_error: Exception | None = None
    try:
        r = await _get_redis()
        tasks = [Task.from_dict(record) for record in await read_task_records_by_statuses(r, *TASK_STATUS_VALUES)]

        by_status = {}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1

        by_agent = {}
        for t in tasks:
            by_agent[t.agent] = by_agent.get(t.agent, 0) + 1

        completed = [t for t in tasks if t.status == "completed" and t.duration_ms]
        avg_duration = (
            sum(t.duration_ms for t in completed) / len(completed)
            if completed else 0
        )
        failed_displays = [_build_failure_display(t) for t in tasks if t.status == "failed"]
        failed_historical_repaired = sum(
            1 for display in failed_displays if isinstance(display, dict) and bool(display.get("historical_residue"))
        )
        failed_missing_detail = sum(
            1 for display in failed_displays if isinstance(display, dict) and bool(display.get("missing_detail"))
        )
        failed_with_detail = sum(
            1 for display in failed_displays if isinstance(display, dict) and not bool(display.get("missing_detail"))
        )
        failed_actionable = max(failed_with_detail - failed_historical_repaired, 0)
        stale_lease_total = int(by_status.get("stale_lease", 0) or 0)
        stale_lease_recovered_historical = sum(
            1
            for t in tasks
            if t.status == "stale_lease"
            and isinstance(t.metadata, dict)
            and isinstance(t.metadata.get("recovery"), dict)
            and t.metadata["recovery"].get("event") == "stale_lease_recovered"
        )
        stale_lease_actionable = max(stale_lease_total - stale_lease_recovered_historical, 0)

        currently_running = int(by_status.get("running", 0) or 0)
        worker_running = bool(
            currently_running > 0
            or int(by_status.get("pending", 0) or 0) > 0
            or (_worker_task is not None and not _worker_task.done())
        )

        return {
            "total": len(tasks),
            "by_status": by_status,
            "by_agent": by_agent,
            **{status: int(by_status.get(status, 0) or 0) for status in TASK_STATUS_VALUES},
            "currently_running": currently_running,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "avg_duration_ms": int(avg_duration),
            "worker_running": worker_running,
            "failed_with_detail": failed_with_detail,
            "failed_actionable": failed_actionable,
            "failed_historical_repaired": failed_historical_repaired,
            "failed_missing_detail": failed_missing_detail,
            "stale_lease_actionable": stale_lease_actionable,
            "stale_lease_recovered_historical": stale_lease_recovered_historical,
            "failure_detail_quality": {
                "failed_with_detail": failed_with_detail,
                "failed_actionable": failed_actionable,
                "failed_historical_repaired": failed_historical_repaired,
                "failed_missing_detail": failed_missing_detail,
            },
        }
    except Exception as e:
        redis_error = e
        logger.warning("Failed to get task stats: %s", e)
    try:
        snapshot = await get_task_snapshot_stats()
        by_status = {
            status: int(snapshot.get("by_status", {}).get(status, 0) or 0)
            for status in TASK_STATUS_VALUES
        }
        currently_running = int(by_status.get("running", 0) or 0)
        worker_running = bool(
            currently_running > 0
            or int(by_status.get("pending", 0) or 0) > 0
            or (_worker_task is not None and not _worker_task.done())
        )
        return {
            "total": int(snapshot.get("total", 0) or 0),
            "by_status": dict(snapshot.get("by_status", {})),
            "by_agent": {},
            **by_status,
            "currently_running": currently_running,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "avg_duration_ms": 0,
            "worker_running": worker_running,
            "failed_with_detail": max(int(by_status.get("failed", 0) or 0), 0),
            "failed_actionable": max(int(by_status.get("failed", 0) or 0), 0),
            "failed_historical_repaired": 0,
            "failed_missing_detail": 0,
            "stale_lease_actionable": max(int(by_status.get("stale_lease", 0) or 0), 0),
            "stale_lease_recovered_historical": 0,
            "failure_detail_quality": {
                "failed_with_detail": max(int(by_status.get("failed", 0) or 0), 0),
                "failed_actionable": max(int(by_status.get("failed", 0) or 0), 0),
                "failed_historical_repaired": 0,
                "failed_missing_detail": 0,
            },
            "source": "durable_state_fallback",
        }
    except Exception as durable_error:
        logger.warning("Durable fallback failed while computing task stats: %s", durable_error)
        return {"error": str(redis_error or durable_error)}
