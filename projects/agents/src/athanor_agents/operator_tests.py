from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit

import httpx

OPERATOR_TEST_RESULTS_KEY = "athanor:governor:operator-tests:results"

FLOW_DEFINITIONS: dict[str, dict[str, Any]] = {
    "pause_resume": {
        "title": "Pause and resume automation",
        "description": "Exercises live lane pause and resume controls through the governor while restoring prior state.",
        "evidence": ["test_governor.py", "tests/e2e/operator-controls.spec.ts"],
        "status_if_pass": "live",
    },
    "presence_tier": {
        "title": "Presence and release-tier posture",
        "description": "Verifies presence-aware and release-tier-aware governance decisions with safe restore of prior posture.",
        "evidence": ["test_governor.py", "test_backbone.py", "tests/e2e/operator-controls.spec.ts"],
        "status_if_pass": "live",
    },
    "scheduled_job_governance": {
        "title": "Scheduled job posture and deferral",
        "description": "Checks that scheduled jobs expose governor-owned state, cadence, deep links, and execution posture.",
        "evidence": ["test_backbone.py", "test_scheduler.py"],
        "status_if_pass": "live",
    },
    "sovereign_routing": {
        "title": "Sovereign routing verification",
        "description": "Verifies refusal-sensitive work stays sovereign and cloud-safe work remains eligible for frontier supervision.",
        "evidence": ["test_operator_tests.py", "test_command_hierarchy.py"],
        "status_if_pass": "live",
    },
    "provider_fallback": {
        "title": "Provider fallback readiness",
        "description": "Checks governed provider fallback posture, handoff availability, and recent lease evidence without bypassing the governor.",
        "evidence": ["test_operator_tests.py", "test_provider_execution.py"],
        "status_if_pass": "live_partial",
    },
    "stuck_queue_recovery": {
        "title": "Stuck queue recovery",
        "description": "Exercises non-destructive queue recovery posture by pausing a governed lane, verifying scheduled-job state, and restoring forward progress cleanly.",
        "evidence": ["test_operator_tests.py", "test_governor.py", "test_backbone.py"],
        "status_if_pass": "live_partial",
    },
    "incident_review": {
        "title": "Incident review",
        "description": "Verifies that alerts, operator stream events, and execution-run lineage can be reviewed together without SSH or log scraping.",
        "evidence": ["test_operator_tests.py", "test_backbone.py"],
        "status_if_pass": "live_partial",
    },
    "tool_permissions": {
        "title": "Tool-permission governance",
        "description": "Verifies that meta lanes, specialists, workers, and judges are constrained by live tool-permission decisions instead of registry text alone.",
        "evidence": ["test_operator_tests.py", "test_tool_permissions.py"],
        "status_if_pass": "live_partial",
    },
    "economic_governance": {
        "title": "Economic governance verification",
        "description": "Checks that reserve lanes, approval-required spend, and downgrade posture are backed by live provider summaries and lease evidence.",
        "evidence": ["test_operator_tests.py", "subscription-routing-policy.yaml"],
        "status_if_pass": "live_partial",
    },
    "promotion_ladder": {
        "title": "Promotion ladder rehearsal",
        "description": "Stages, advances, and rolls back a challenger through the governed release ladder without leaving production state mutated.",
        "evidence": ["test_operator_tests.py", "test_promotion_control.py"],
        "status_if_pass": "live_partial",
    },
    "retirement_policy": {
        "title": "Retirement policy rehearsal",
        "description": "Stages, advances, and rolls back a governed retirement candidate so deprecation posture is backed by live evidence instead of registry text alone.",
        "evidence": ["test_operator_tests.py", "test_retirement_control.py"],
        "status_if_pass": "live_partial",
    },
    "data_lifecycle": {
        "title": "Data lifecycle verification",
        "description": "Checks that operational history, sovereign content, and eval artifacts are represented by live runtime evidence instead of registry declarations alone.",
        "evidence": ["test_operator_tests.py", "data-lifecycle-registry.json"],
        "status_if_pass": "live_partial",
    },
    "restore_drill": {
        "title": "Restore drill and recovery flow",
        "description": "Checks restore-drill readiness posture and recovery ordering for critical stores until live drill execution lands.",
        "evidence": ["OPERATOR_RUNBOOKS.md", "backup-restore-readiness.json"],
        "status_if_pass": "configured",
    },
}


@dataclass
class OperatorTestFlowRecord:
    id: str
    title: str
    description: str
    status: str
    last_outcome: str | None
    last_run_at: str | None
    last_duration_ms: int | None
    checks_passed: int
    checks_total: int
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_auth_protected_reachable(status_code: int) -> bool:
    return status_code in {200, 401, 403}


def _sanitize_artifact_reference(value: Any) -> Any:
    if not isinstance(value, str) or "://" not in value:
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    if parsed.username is None and parsed.password is None and "@" not in parsed.netloc:
        return value
    host = parsed.hostname or ""
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _sanitize_artifact_references(values: list[Any]) -> list[Any]:
    return [_sanitize_artifact_reference(value) for value in values]


async def _collect_restore_store_results(
    probes: list[Callable[[], Awaitable[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    return await asyncio.gather(*(probe() for probe in probes))


async def _get_redis():
    from .workspace import get_redis

    return await get_redis()


def _finalize_flow(
    *,
    flow_id: str,
    last_outcome: str,
    checks_passed: int,
    checks_total: int,
    started_at: float,
    status: str | None = None,
    notes: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> OperatorTestFlowRecord:
    definition = FLOW_DEFINITIONS[flow_id]
    effective_status = status or (
        definition["status_if_pass"] if last_outcome == "passed" else "degraded"
    )
    return OperatorTestFlowRecord(
        id=flow_id,
        title=str(definition["title"]),
        description=str(definition["description"]),
        status=effective_status,
        last_outcome=last_outcome,
        last_run_at=_now_iso(),
        last_duration_ms=max(int((time.perf_counter() - started_at) * 1000), 1),
        checks_passed=checks_passed,
        checks_total=checks_total,
        evidence=list(definition["evidence"]),
        notes=list(notes or []),
        details=details,
    )


def _build_operator_tests_status(flows: list[dict[str, Any]]) -> tuple[str, str]:
    if not flows:
        return "configured", "not_run"

    outcomes = {str(flow.get("last_outcome") or "") for flow in flows}
    statuses = {str(flow.get("status") or "configured") for flow in flows}

    if "failed" in outcomes or "degraded" in statuses:
        return "degraded", "failed"
    if statuses == {"live"}:
        return "live", "passed"
    if any(status in {"live", "live_partial"} for status in statuses):
        return "live_partial", "partial"
    return "configured", "partial"


async def _run_pause_resume_flow() -> OperatorTestFlowRecord:
    from .governor import (
        _save_governor_state,
        get_governor_state,
        is_automation_paused,
        pause_automation,
        resume_automation,
    )
    from .model_governance import get_command_rights_registry

    started_at = time.perf_counter()
    saved_state = await get_governor_state()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 4

    try:
        governor_profile = next(
            (
                profile
                for profile in get_command_rights_registry().get("profiles", [])
                if str(profile.get("subject")) == "Athanor Governor"
            ),
            {},
        )
        rights = set(governor_profile.get("can", []))
        if {
            "route work",
            "pause or resume automation",
            "choose fallback or degraded mode",
        } <= rights:
            checks_passed += 1
        else:
            notes.append("Governor rights profile is missing one or more control rights.")

        paused = await pause_automation(
            scope="maintenance",
            reason="Synthetic operator test pause/resume check",
            actor="operator-tests",
        )
        if "maintenance" in paused.get("paused_lanes", []):
            checks_passed += 1
        else:
            notes.append("Maintenance lane did not enter paused state.")

        if await is_automation_paused("maintenance"):
            checks_passed += 1
        else:
            notes.append("Paused lane was not reported as paused by the governor.")

        await resume_automation(scope="maintenance", actor="operator-tests")
        if not await is_automation_paused("maintenance"):
            checks_passed += 1
        else:
            notes.append("Maintenance lane did not resume correctly.")
    finally:
        await _save_governor_state(saved_state)

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="pause_resume",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        notes=notes,
    )


async def _run_presence_tier_flow() -> OperatorTestFlowRecord:
    from .governor import (
        _save_governor_state,
        evaluate_job_governance,
        get_governor_state,
        set_operator_presence,
        set_release_tier,
    )

    started_at = time.perf_counter()
    saved_state = await get_governor_state()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 4

    try:
        await set_operator_presence("asleep", reason="Synthetic operator test", actor="operator-tests")
        await set_release_tier("offline_eval", reason="Synthetic operator test", actor="operator-tests")

        benchmark = await evaluate_job_governance(
            job_id="benchmark-cycle",
            job_family="benchmarks",
            control_scope="benchmark_cycle",
            owner_agent="system",
        )
        research = await evaluate_job_governance(
            job_id="research:scheduler",
            job_family="research_jobs",
            control_scope="research_jobs",
            owner_agent="research-agent",
        )
        digest = await evaluate_job_governance(
            job_id="daily-digest",
            job_family="daily_digest",
            control_scope="scheduler",
            owner_agent="system",
        )

        if benchmark.get("allowed") and benchmark.get("release_tier") == "offline_eval":
            checks_passed += 1
        else:
            notes.append("Benchmark cycle did not remain allowed inside offline-eval posture.")

        if not research.get("allowed") and research.get("status") == "deferred":
            checks_passed += 1
        else:
            notes.append("Research jobs were not deferred under asleep posture.")

        if not digest.get("allowed") and digest.get("status") == "deferred":
            checks_passed += 1
        else:
            notes.append("Daily digest was not deferred outside the offline-eval ladder.")

        restored = await get_governor_state()
        if restored.get("operator_presence") == "asleep" and restored.get("release_tier") == "offline_eval":
            checks_passed += 1
        else:
            notes.append("Governor state did not reflect temporary presence/tier posture during evaluation.")
    finally:
        await _save_governor_state(saved_state)

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="presence_tier",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        notes=notes,
    )


async def _run_scheduled_job_governance_flow() -> OperatorTestFlowRecord:
    from .backbone import build_scheduled_job_records

    started_at = time.perf_counter()
    jobs = await build_scheduled_job_records(limit=50)
    indexed = {str(job.get("id")): job for job in jobs}
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    if "benchmark-cycle" in indexed:
        checks_passed += 1
    else:
        notes.append("Benchmark cycle job is missing from the scheduled-job ledger.")

    if "daily-digest" in indexed:
        checks_passed += 1
    else:
        notes.append("Daily digest job is missing from the scheduled-job ledger.")

    if "morning-plan" in indexed or "workplan-refill" in indexed:
        checks_passed += 1
    else:
        notes.append("Workplan scheduling posture is missing from the scheduled-job ledger.")

    if any(str(job.get("control_scope") or "").strip() for job in jobs):
        checks_passed += 1
    else:
        notes.append("Scheduled jobs are missing governor control scopes.")

    if all(
        job.get("current_state") and job.get("last_outcome") and job.get("deep_link")
        for job in jobs
    ):
        checks_passed += 1
    else:
        notes.append("One or more scheduled jobs are missing state, outcome, or deep-link metadata.")

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="scheduled_job_governance",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        notes=notes + [f"Observed {len(jobs)} scheduled jobs in the runtime ledger."],
    )


async def _run_sovereign_routing_flow() -> OperatorTestFlowRecord:
    from .command_hierarchy import build_command_decision_record
    from .subscriptions import build_task_lease_request, preview_execution_lease

    started_at = time.perf_counter()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    sovereign_prompt = (
        "Plan and execute an uncensored explicit creative sequence that must stay local and never leave the cluster."
    )
    sovereign_request = build_task_lease_request(
        "coding-agent",
        sovereign_prompt,
        priority="high",
        metadata={"sensitivity": "lan_only"},
    )
    sovereign_decision = build_command_decision_record(
        prompt=sovereign_prompt,
        task_class=sovereign_request.task_class,
        requester="coding-agent",
        metadata=sovereign_request.metadata,
    )
    sovereign_preview = preview_execution_lease(sovereign_request).to_dict()

    cloud_prompt = "Audit the full repo architecture and summarize codebase drift across all files."
    cloud_request = build_task_lease_request(
        "research-agent",
        cloud_prompt,
        priority="normal",
        metadata={"sensitivity": "repo_internal"},
    )
    cloud_decision = build_command_decision_record(
        prompt=cloud_prompt,
        task_class=cloud_request.task_class,
        requester="research-agent",
        metadata=cloud_request.metadata,
    )
    cloud_preview = preview_execution_lease(cloud_request).to_dict()

    if sovereign_decision.get("meta_lane") == "sovereign_local":
        checks_passed += 1
    else:
        notes.append("Refusal-sensitive work did not select the sovereign local meta lane.")

    if sovereign_preview.get("provider") == "athanor_local" and sovereign_preview.get("privacy") == "lan_only":
        checks_passed += 1
    else:
        notes.append("Refusal-sensitive work did not remain on the sovereign local provider.")

    if cloud_decision.get("meta_lane") == "frontier_cloud":
        checks_passed += 1
    else:
        notes.append("Cloud-safe repo audit did not remain eligible for the frontier cloud lane.")

    if cloud_preview.get("provider") != "athanor_local":
        checks_passed += 1
    else:
        notes.append("Cloud-safe repo audit unexpectedly collapsed to local-only routing.")

    if sovereign_request.metadata.get("policy_class") in {"refusal_sensitive", "sovereign_only"}:
        checks_passed += 1
    else:
        notes.append("Sovereign preview did not carry a protected policy class.")

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="sovereign_routing",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        notes=notes
        + [
            f"Sovereign path selected {sovereign_preview.get('provider')} with policy {sovereign_request.metadata.get('policy_class')}.",
            f"Cloud-safe path selected {cloud_preview.get('provider')} with policy {cloud_request.metadata.get('policy_class')}.",
        ],
    )


async def _run_provider_fallback_flow() -> OperatorTestFlowRecord:
    from .provider_execution import build_provider_execution_snapshot

    started_at = time.perf_counter()
    snapshot = await build_provider_execution_snapshot(limit=10)
    adapters = list(snapshot.get("adapters", []))
    notes: list[str] = []
    checks_passed = 0
    checks_total = 4

    local_adapter = next((adapter for adapter in adapters if adapter.get("provider") == "athanor_local"), None)
    non_local = [adapter for adapter in adapters if adapter.get("provider") != "athanor_local"]

    if local_adapter and local_adapter.get("execution_mode") == "local_runtime" and local_adapter.get("adapter_available"):
        checks_passed += 1
    else:
        notes.append("Sovereign local adapter is not surfaced as an available runtime lane.")

    if non_local and all(adapter.get("supports_handoff") for adapter in non_local):
        checks_passed += 1
    else:
        notes.append("One or more frontier providers are missing governed handoff capability.")

    if all(
        str(adapter.get("execution_mode")) in {"direct_cli", "bridge_cli", "handoff_bundle", "local_runtime"}
        for adapter in adapters
    ):
        checks_passed += 1
    else:
        notes.append("Adapter execution modes include an unknown or unsupported state.")

    if snapshot.get("recent_leases"):
        checks_passed += 1
    else:
        notes.append("Provider execution snapshot did not surface recent lease evidence.")

    direct_count = sum(
        1 for adapter in non_local if adapter.get("execution_mode") in {"direct_cli", "bridge_cli"}
    )
    if direct_count == 0:
        notes.append("Frontier providers are currently handoff-first; direct or bridge execution remains partial.")

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="provider_fallback",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live" if outcome == "passed" and direct_count > 0 else ("live_partial" if outcome == "passed" else "degraded"),
        notes=notes + [f"Observed {len(adapters)} provider adapters and {len(snapshot.get('recent_leases', []))} recent leases."],
    )


async def _run_stuck_queue_recovery_flow() -> OperatorTestFlowRecord:
    from .backbone import build_execution_run_records, build_scheduled_job_records
    from .governor import (
        _save_governor_state,
        build_capacity_snapshot,
        get_governor_state,
        is_automation_paused,
        pause_automation,
        resume_automation,
    )

    started_at = time.perf_counter()
    saved_state = await get_governor_state()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    try:
        await pause_automation(
            scope="scheduler",
            reason="Synthetic operator test queue-recovery check",
            actor="operator-tests",
        )
        scheduled_jobs = await build_scheduled_job_records(limit=50)
        scheduler_jobs = [
            job for job in scheduled_jobs if str(job.get("control_scope") or "") == "scheduler"
        ]
        if scheduler_jobs:
            checks_passed += 1
        else:
            notes.append("No scheduler-governed jobs were visible during queue-recovery rehearsal.")

        if any(job.get("current_state") == "paused" and job.get("paused") for job in scheduler_jobs):
            checks_passed += 1
        else:
            notes.append("Scheduler-governed jobs did not reflect the paused recovery posture.")

        capacity = await build_capacity_snapshot()
        queue = dict(capacity.get("queue") or {})
        if queue.get("posture") in {"healthy", "constrained", "degraded"} and "pending" in queue:
            checks_passed += 1
        else:
            notes.append("Capacity governor did not expose queue posture during recovery rehearsal.")

        runs = await build_execution_run_records(limit=12)
        if runs and all(run.get("artifact_refs") for run in runs[: min(len(runs), 3)]):
            checks_passed += 1
        else:
            notes.append("Execution runs were missing artifact lineage during queue-recovery rehearsal.")

        await resume_automation(scope="scheduler", actor="operator-tests")
        if not await is_automation_paused("scheduler"):
            checks_passed += 1
        else:
            notes.append("Scheduler lane did not resume cleanly after queue-recovery rehearsal.")
    finally:
        await _save_governor_state(saved_state)

    notes.append(
        f"Queue-recovery rehearsal observed {len(scheduler_jobs)} scheduler-governed jobs and {len(runs) if 'runs' in locals() else 0} recent runs."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="stuck_queue_recovery",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "scheduler_job_count": len(scheduler_jobs) if "scheduler_jobs" in locals() else 0,
            "run_count": len(runs) if "runs" in locals() else 0,
            "queue_posture": str((queue if "queue" in locals() else {}).get("posture") or "unknown"),
        },
    )


async def _run_incident_review_flow() -> OperatorTestFlowRecord:
    from .alerts import get_active_alerts, get_alert_history
    from .backbone import build_execution_run_records, build_operator_stream

    started_at = time.perf_counter()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    active_alerts = await get_active_alerts()
    alert_history = await get_alert_history(limit=10)
    operator_stream = await build_operator_stream(limit=20)
    runs = await build_execution_run_records(limit=12)

    if isinstance(active_alerts, dict) and isinstance(active_alerts.get("alerts"), list):
        checks_passed += 1
    else:
        notes.append("Active-alert snapshot did not return the expected alert list.")

    if isinstance(alert_history, list):
        checks_passed += 1
    else:
        notes.append("Alert-history snapshot did not return the expected history list.")

    if operator_stream:
        checks_passed += 1
    else:
        notes.append("Operator stream did not expose any incident-review events.")

    if runs:
        checks_passed += 1
    else:
        notes.append("Execution-run lineage was not available for incident review.")

    incident_like_events = [
        event
        for event in operator_stream
        if str(event.get("severity") or "") in {"warning", "error"}
        or str(event.get("event_type") or "").startswith("alert_")
        or str(event.get("deep_link") or "") in {"/notifications", "/tasks", "/agents"}
    ]
    if incident_like_events and all(
        event.get("deep_link") and event.get("summary") and event.get("subject")
        for event in incident_like_events[: min(len(incident_like_events), 5)]
    ):
        checks_passed += 1
    else:
        notes.append("Incident-review events were missing a deep link, subject, or summary.")

    if not active_alerts.get("alerts"):
        notes.append("No active alerts were present; incident review relied on stream and run-history posture.")

    notes.append(
        f"Incident review observed {len(active_alerts.get('alerts', []))} active alerts, {len(alert_history)} history items, {len(operator_stream)} stream events, and {len(runs)} recent runs."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="incident_review",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "active_alert_count": len(active_alerts.get("alerts", [])),
            "alert_history_count": len(alert_history),
            "stream_event_count": len(operator_stream),
            "run_count": len(runs),
        },
    )


async def _run_tool_permissions_flow() -> OperatorTestFlowRecord:
    from .tool_permissions import build_tool_permission_snapshot, evaluate_tool_permission

    started_at = time.perf_counter()
    snapshot = build_tool_permission_snapshot()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 6

    meta_deny = evaluate_tool_permission("frontier_cloud", "shell mutation")
    meta_allow = evaluate_tool_permission("frontier_cloud", "planning helpers")
    specialist_allow = evaluate_tool_permission("coding-agent", "bounded execution")
    specialist_lease = evaluate_tool_permission("research-agent", "lease requests")
    worker_deny = evaluate_tool_permission("coding_worker", "lease issuance")
    judge_deny = evaluate_tool_permission("judge", "deployment actions")

    if not meta_deny["allowed"] and meta_deny["matched_deny"]:
        checks_passed += 1
    else:
        notes.append("Frontier meta lane was not denied direct shell mutation.")

    if meta_allow["allowed"] and meta_allow["matched_allow"]:
        checks_passed += 1
    else:
        notes.append("Frontier meta lane was not allowed to use planning helpers.")

    if specialist_allow["allowed"] and specialist_allow["direct_execution"]:
        checks_passed += 1
    else:
        notes.append("Specialist agents were not allowed bounded execution through scoped execution.")

    if specialist_lease["allowed"]:
        checks_passed += 1
    else:
        notes.append("Specialist agents were not allowed to request governed leases.")

    if not worker_deny["allowed"] and worker_deny["matched_deny"]:
        checks_passed += 1
    else:
        notes.append("Worker lanes were not denied lease issuance.")

    if not judge_deny["allowed"] and judge_deny["matched_deny"]:
        checks_passed += 1
    else:
        notes.append("Judge lanes were not denied deployment actions.")

    denied_action_count = sum(
        1
        for decision in [meta_deny, worker_deny, judge_deny]
        if not decision["allowed"]
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="tool_permissions",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "subject_count": int(snapshot.get("subject_count", 0) or 0),
            "enforced_subject_count": int(snapshot.get("subject_count", 0) or 0),
            "mode_counts": dict(snapshot.get("mode_counts") or {}),
            "denied_action_count": denied_action_count,
        },
    )


async def _run_economic_governance_flow() -> OperatorTestFlowRecord:
    from .backbone import build_quota_lease_summary
    from .model_governance import get_economic_governance_registry

    started_at = time.perf_counter()
    registry = get_economic_governance_registry()
    summary = await build_quota_lease_summary(limit=10)
    provider_summaries = list(summary.get("provider_summaries") or [])
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    if list(registry.get("premium_reserve_lanes") or []):
        checks_passed += 1
    else:
        notes.append("Economic-governance registry is missing premium reserve lanes.")

    if list(registry.get("automatic_spend_lanes") or []):
        checks_passed += 1
    else:
        notes.append("Economic-governance registry is missing automatic-spend lanes.")

    if list(registry.get("approval_required_lanes") or []) and list(registry.get("downgrade_order") or []):
        checks_passed += 1
    else:
        notes.append("Approval-required or downgrade-order posture is incomplete.")

    if provider_summaries and all(
        str(item.get("reserve_state") or "").strip() and str(item.get("availability") or "").strip()
        for item in provider_summaries
    ):
        checks_passed += 1
    else:
        notes.append("Live provider summaries are missing reserve or availability posture.")

    recent_leases = list(summary.get("recent_leases") or [])
    if recent_leases:
        checks_passed += 1
    else:
        notes.append("Quota and lease summary did not surface recent lease evidence.")

    constrained_count = sum(
        1 for item in provider_summaries if str(item.get("availability") or "") == "constrained"
    )
    notes.append(
        f"Economic posture observed {len(provider_summaries)} providers, {len(recent_leases)} recent leases, and {constrained_count} constrained reserve lane(s)."
    )

    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="economic_governance",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "provider_count": len(provider_summaries),
            "recent_lease_count": len(recent_leases),
            "constrained_count": constrained_count,
            "reserve_lane_count": len(list(registry.get("premium_reserve_lanes") or [])),
            "automatic_spend_count": len(list(registry.get("automatic_spend_lanes") or [])),
        },
    )


async def _run_promotion_ladder_flow() -> OperatorTestFlowRecord:
    from .model_governance import get_model_role_registry
    from .promotion_control import (
        build_promotion_controls_snapshot,
        stage_promotion_candidate,
        transition_promotion_candidate,
    )

    started_at = time.perf_counter()
    notes: list[str] = []
    checks_passed = 0
    checks_total = 6

    role = next(
        (
            entry
            for entry in get_model_role_registry().get("roles", [])
            if isinstance(entry, dict) and entry.get("challengers")
        ),
        None,
    )
    if not role:
        return _finalize_flow(
            flow_id="promotion_ladder",
            last_outcome="failed",
            checks_passed=0,
            checks_total=checks_total,
            started_at=started_at,
            status="degraded",
            notes=["Model role registry has no challenger candidates available for release-ladder rehearsal."],
        )

    role_id = str(role.get("id") or "role")
    candidate = str(list(role.get("challengers") or [])[0])
    staged = await stage_promotion_candidate(
        role_id=role_id,
        candidate=candidate,
        target_tier="canary",
        actor="operator-tests",
        reason="Synthetic operator-test rehearsal for the governed release ladder.",
        source="operator_test",
    )
    promotion_id = str(staged.get("id") or "")

    if staged.get("status") == "staged" and staged.get("current_tier") == "offline_eval":
        checks_passed += 1
    else:
        notes.append("Promotion ladder did not stage the candidate at the offline-eval tier.")

    traversed_tiers = [str(staged.get("current_tier") or "offline_eval")]
    current_record = staged
    while current_record.get("status") != "completed":
        next_record = await transition_promotion_candidate(
            promotion_id,
            action="advance",
            actor="operator-tests",
            reason="Synthetic ladder rehearsal advance.",
        )
        if next_record is None:
            notes.append("Promotion ladder advance did not return an updated record.")
            break
        current_record = next_record
        traversed_tiers.append(str(current_record.get("current_tier") or "unknown"))
        if len(traversed_tiers) > 8:
            notes.append("Promotion ladder exceeded the expected tier count during rehearsal.")
            break

    expected_path = ["offline_eval", "shadow", "sandbox", "canary"]
    if traversed_tiers[: len(expected_path)] == expected_path:
        checks_passed += 1
    else:
        notes.append(
            f"Promotion ladder traversed {', '.join(traversed_tiers)} instead of the expected {' -> '.join(expected_path)}."
        )

    if current_record.get("status") == "completed" and current_record.get("current_tier") == "canary":
        checks_passed += 1
    else:
        notes.append("Promotion ladder did not reach the target canary tier cleanly.")

    rolled_back = await transition_promotion_candidate(
        promotion_id,
        action="rollback",
        actor="operator-tests",
        reason="Synthetic ladder rehearsal rollback.",
    )
    if rolled_back and rolled_back.get("status") == "rolled_back":
        checks_passed += 1
    else:
        notes.append("Promotion ladder rollback did not complete.")

    if rolled_back and str(rolled_back.get("rollback_target") or "") == str(role.get("champion") or ""):
        checks_passed += 1
    else:
        notes.append("Promotion ladder did not preserve the prior champion as the rollback target.")

    controls = await build_promotion_controls_snapshot(limit=20)
    recent_promotions = list(controls.get("recent_promotions") or [])
    matching = next((record for record in recent_promotions if str(record.get("id")) == promotion_id), None)
    if matching and str(matching.get("status") or "") == "rolled_back":
        checks_passed += 1
    else:
        notes.append("Promotion ladder rehearsal was not visible in the promotion-controls snapshot.")

    notes.append(
        f"Promotion ladder rehearsed {role_id} using challenger {candidate} across {' -> '.join(traversed_tiers)} before rollback."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="promotion_ladder",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "promotion_id": promotion_id,
            "role_id": role_id,
            "candidate": candidate,
            "target_tier": "canary",
            "traversed_tiers": traversed_tiers,
            "final_status": str(rolled_back.get("status") if rolled_back else current_record.get("status") or "unknown"),
            "rollback_target": str(rolled_back.get("rollback_target") if rolled_back else role.get("champion") or ""),
        },
    )


async def _run_retirement_policy_flow() -> OperatorTestFlowRecord:
    from .model_governance import get_model_role_registry
    from .retirement_control import (
        build_retirement_controls_snapshot,
        stage_retirement_candidate,
        transition_retirement_candidate,
    )

    started_at = time.perf_counter()
    role = next(
        (
            item
            for item in get_model_role_registry().get("roles", [])
            if str(item.get("id")) == "frontier_supervisor" and str(item.get("champion") or "").strip()
        ),
        None,
    )
    if role is None:
        return _finalize_flow(
            flow_id="retirement_policy",
            last_outcome="failed",
            checks_passed=0,
            checks_total=6,
            started_at=started_at,
            status="degraded",
            notes=["Unable to find a governed champion asset for the retirement rehearsal."],
        )

    role_id = str(role.get("id") or "role")
    champion = str(role.get("champion") or "")
    label = f"{str(role.get('label') or role_id)} champion {champion}"
    staged = await stage_retirement_candidate(
        asset_class="models",
        asset_id=f"{role_id}:{champion}",
        label=label,
        target_stage="retired_reference_only",
        actor="operator-tests",
        reason="Synthetic operator-test rehearsal for the governed retirement ladder.",
        source="operator_test",
    )
    retirement_id = str(staged.get("id") or "")

    notes: list[str] = []
    checks_passed = 0
    checks_total = 6

    if staged.get("status") == "staged" and staged.get("current_stage") == "active":
        checks_passed += 1
    else:
        notes.append("Retirement ladder did not stage the asset at the active baseline stage.")

    traversed_stages = [str(staged.get("current_stage") or "active")]
    current_record = staged
    while current_record.get("status") != "completed":
        next_record = await transition_retirement_candidate(
            retirement_id,
            action="advance",
            actor="operator-tests",
            reason="Synthetic retirement rehearsal advance.",
        )
        if next_record is None:
            notes.append("Retirement ladder advance did not return an updated record.")
            break
        current_record = next_record
        traversed_stages.append(str(current_record.get("current_stage") or "unknown"))
        if len(traversed_stages) > 6:
            notes.append("Retirement ladder exceeded the expected stage count during rehearsal.")
            break

    expected_path = ["active", "deprecated", "retired_reference_only"]
    if traversed_stages[: len(expected_path)] == expected_path:
        checks_passed += 1
    else:
        notes.append(
            f"Retirement ladder traversed {', '.join(traversed_stages)} instead of the expected {' -> '.join(expected_path)}."
        )

    if current_record.get("status") == "completed" and current_record.get("current_stage") == "retired_reference_only":
        checks_passed += 1
    else:
        notes.append("Retirement ladder did not reach retired-reference-only posture cleanly.")

    rolled_back = await transition_retirement_candidate(
        retirement_id,
        action="rollback",
        actor="operator-tests",
        reason="Synthetic retirement rehearsal rollback.",
    )
    if rolled_back and rolled_back.get("status") == "rolled_back":
        checks_passed += 1
    else:
        notes.append("Retirement ladder rollback did not complete.")

    if rolled_back and str(rolled_back.get("current_stage") or "") == "active":
        checks_passed += 1
    else:
        notes.append("Retirement ladder did not restore the asset to active posture after rollback.")

    controls = await build_retirement_controls_snapshot(limit=20)
    recent_retirments = list(controls.get("recent_retirements") or [])
    matching = next((record for record in recent_retirments if str(record.get("id")) == retirement_id), None)
    if matching and str(matching.get("status") or "") == "rolled_back":
        checks_passed += 1
    else:
        notes.append("Retirement rehearsal was not visible in the retirement-controls snapshot.")

    notes.append(
        f"Retirement ladder rehearsed {label} across {' -> '.join(traversed_stages)} before rollback."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="retirement_policy",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "retirement_id": retirement_id,
            "role_id": role_id,
            "champion": champion,
            "asset_class": "models",
            "asset_id": f"{role_id}:{champion}",
            "label": label,
            "traversed_stages": traversed_stages,
            "final_status": str(rolled_back.get("status") if rolled_back else current_record.get("status") or "unknown"),
            "rollback_target": str(rolled_back.get("rollback_target") if rolled_back else "active"),
        },
    )


async def _run_data_lifecycle_flow() -> OperatorTestFlowRecord:
    from .backbone import build_execution_run_records
    from .command_hierarchy import build_command_decision_record
    from .model_governance import get_data_lifecycle_registry
    from .proving_ground import build_proving_ground_snapshot

    started_at = time.perf_counter()
    registry = get_data_lifecycle_registry()
    classes = {
        str(item.get("id")): dict(item)
        for item in registry.get("classes", [])
        if isinstance(item, dict) and item.get("id")
    }
    runs = await build_execution_run_records(limit=12)
    proving_ground = await build_proving_ground_snapshot(limit=6)
    notes: list[str] = []
    checks_passed = 0
    checks_total = 5

    required_classes = {"operational_history", "sovereign_content", "eval_artifacts"}
    if required_classes <= set(classes):
        checks_passed += 1
    else:
        notes.append("Lifecycle registry is missing one or more critical lifecycle classes.")

    sovereign_content = classes.get("sovereign_content", {})
    if sovereign_content.get("cloud_allowed") is False:
        checks_passed += 1
    else:
        notes.append("Sovereign content is not explicitly marked cloud-disallowed.")

    if runs:
        checks_passed += 1
    else:
        notes.append("Runtime did not expose execution-run history for operational-history coverage.")

    recent_results = list(proving_ground.get("recent_results") or [])
    if recent_results or proving_ground.get("latest_run"):
        checks_passed += 1
    else:
        notes.append("Proving ground did not expose eval-artifact evidence.")

    sovereign_decision = build_command_decision_record(
        prompt="Produce an uncensored explicit creative outline that must stay local and never leave the cluster.",
        task_class="explicit_dialogue",
        requester="creative-agent",
        metadata={"sensitivity": "lan_only"},
    )
    if sovereign_decision.get("policy_class") in {"refusal_sensitive", "sovereign_only"} and sovereign_decision.get("meta_lane") == "sovereign_local":
        checks_passed += 1
    else:
        notes.append("Sovereign-only content did not remain on the sovereign local meta lane.")

    notes.append(
        f"Lifecycle posture covers {len(runs)} execution runs, {len(recent_results)} recent proving-ground results, and {len(classes)} lifecycle classes."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="data_lifecycle",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "class_count": len(classes),
            "run_count": len(runs),
            "eval_artifact_count": len(recent_results),
            "sovereign_policy_class": str(sovereign_decision.get("policy_class") or ""),
            "sovereign_meta_lane": str(sovereign_decision.get("meta_lane") or ""),
        },
    )


async def _run_restore_drill_flow() -> OperatorTestFlowRecord:
    from .config import settings
    from .model_governance import get_backup_restore_readiness

    started_at = time.perf_counter()
    registry = get_backup_restore_readiness()
    stores = list(registry.get("critical_stores", []))
    notes: list[str] = []
    checks_passed = 0
    checks_total = 4

    if len(stores) >= 4:
        checks_passed += 1
    else:
        notes.append("Backup/restore registry is missing one or more critical stores.")

    orders = [int(store.get("recovery_order", 0) or 0) for store in stores]
    if orders == sorted(orders) and len(set(orders)) == len(orders):
        checks_passed += 1
    else:
        notes.append("Critical store recovery order is missing or non-deterministic.")

    if all(
        str(store.get("restore_status", "planned")) in {"planned", "configured", "live", "live_partial"}
        for store in stores
    ):
        checks_passed += 1
    else:
        notes.append("One or more restore statuses are invalid.")

    async def probe_redis_store() -> dict[str, Any]:
        redis = await _get_redis()
        probe_key = f"athanor:restore-drill:probe:{int(time.time())}"
        artifacts = _sanitize_artifact_references([settings.redis_url])
        summary = "Redis restore rehearsal did not complete."
        verified = False
        try:
            ping_ok = True
            if hasattr(redis, "ping"):
                ping_result = await redis.ping()
                ping_ok = bool(ping_result)

            try:
                await redis.set(probe_key, "restore-drill-ok", ex=60)
            except TypeError:
                await redis.set(probe_key, "restore-drill-ok")
            stored = await redis.get(probe_key)
            if hasattr(redis, "delete"):
                await redis.delete(probe_key)

            verified = ping_ok and stored in {"restore-drill-ok", b"restore-drill-ok"}
            summary = (
                "Redis ping and synthetic write/read/delete rehearsal succeeded."
                if verified
                else "Redis rehearsal could not confirm ping plus write/read/delete."
            )
        except Exception as exc:  # pragma: no cover - exercised in live runtime
            summary = f"Redis rehearsal failed: {exc}"
        return {
            "id": "redis_critical_state",
            "label": "Redis critical state",
            "verified": verified,
            "probe_status": "verified" if verified else "degraded",
            "probe_summary": summary,
            "checked_at": _now_iso(),
            "artifacts": artifacts,
        }

    async def probe_qdrant_store() -> dict[str, Any]:
        artifacts = _sanitize_artifact_references([f"{settings.qdrant_url.rstrip('/')}/collections"])
        summary = "Qdrant restore rehearsal did not complete."
        verified = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.qdrant_url.rstrip('/')}/collections")
                if response.status_code == 200:
                    payload = response.json()
                    collections = list(payload.get("result", {}).get("collections", []))
                    verified = True
                    summary = f"Qdrant collections endpoint is healthy with {len(collections)} collections visible."
                else:
                    summary = f"Qdrant collections endpoint returned {response.status_code}."
        except Exception as exc:  # pragma: no cover - exercised in live runtime
            summary = f"Qdrant rehearsal failed: {exc}"
        return {
            "id": "qdrant_memory",
            "label": "Qdrant memory",
            "verified": verified,
            "probe_status": "verified" if verified else "degraded",
            "probe_summary": summary,
            "checked_at": _now_iso(),
            "artifacts": artifacts,
        }

    async def probe_neo4j_store() -> dict[str, Any]:
        base_url = settings.neo4j_url.rstrip("/")
        artifacts = _sanitize_artifact_references([base_url])
        summary = "Neo4j restore rehearsal did not complete."
        verified = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if settings.neo4j_password:
                    response = await client.post(
                        f"{base_url}/db/neo4j/tx/commit",
                        auth=(settings.neo4j_user, settings.neo4j_password),
                        json={"statements": [{"statement": "RETURN 1 AS ok"}]},
                    )
                    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    errors = list(payload.get("errors", [])) if isinstance(payload, dict) else []
                    verified = response.status_code == 200 and not errors
                    summary = (
                        "Neo4j authenticated probe succeeded with a minimal read-only transaction."
                        if verified
                        else f"Neo4j transaction probe returned {response.status_code}."
                    )
                    artifacts = _sanitize_artifact_references(
                        [*artifacts, f"{base_url}/db/neo4j/tx/commit"]
                    )
                else:
                    response = await client.get(base_url)
                    verified = response.status_code in {200, 401}
                    summary = (
                        "Neo4j endpoint is reachable; authenticated restore drill remains password-gated."
                        if verified
                        else f"Neo4j endpoint returned {response.status_code}."
                    )
        except Exception as exc:  # pragma: no cover - exercised in live runtime
            summary = f"Neo4j rehearsal failed: {exc}"
        return {
            "id": "neo4j_graph",
            "label": "Neo4j graph",
            "verified": verified,
            "probe_status": "verified" if verified else "degraded",
            "probe_summary": summary,
            "checked_at": _now_iso(),
            "artifacts": artifacts,
        }

    async def probe_deploy_state_store() -> dict[str, Any]:
        agent_url = f"{settings.agent_server_url.rstrip('/')}/v1/governor"
        dashboard_url = f"{settings.dashboard_url.rstrip('/')}/api/system-map"
        artifacts = _sanitize_artifact_references([agent_url, dashboard_url])
        summary = "Deployment-state restore rehearsal did not complete."
        verified = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                agent_headers = (
                    {"Authorization": f"Bearer {settings.api_bearer_token}"}
                    if settings.api_bearer_token
                    else None
                )
                agent_response = await client.get(agent_url, headers=agent_headers)
                dashboard_response = await client.get(dashboard_url)
                verified = _is_auth_protected_reachable(
                    agent_response.status_code
                ) and _is_auth_protected_reachable(dashboard_response.status_code)
                if verified:
                    if agent_response.status_code == 200 and dashboard_response.status_code == 200:
                        summary = "Agent and dashboard deployment surfaces are reachable for ordered recovery."
                    else:
                        summary = (
                            "Agent and dashboard deployment surfaces are reachable and "
                            "auth-protected for ordered recovery."
                        )
                else:
                    summary = (
                        f"Agent/dashboard deploy probes returned "
                        f"{agent_response.status_code}/{dashboard_response.status_code}."
                    )
        except Exception as exc:  # pragma: no cover - exercised in live runtime
            summary = f"Deployment-state rehearsal failed: {exc}"
        return {
            "id": "dashboard_agent_deploy_state",
            "label": "Dashboard and agent deployment state",
            "verified": verified,
            "probe_status": "verified" if verified else "degraded",
            "probe_summary": summary,
            "checked_at": _now_iso(),
            "artifacts": artifacts,
        }

    store_results = await _collect_restore_store_results(
        [
            probe_redis_store,
            probe_qdrant_store,
            probe_neo4j_store,
            probe_deploy_state_store,
        ]
    )
    verified_store_count = sum(1 for store in store_results if store.get("verified"))
    if verified_store_count == len(store_results):
        checks_passed += 1
    else:
        notes.append(
            f"Only {verified_store_count}/{len(store_results)} critical stores passed the live non-destructive restore rehearsal."
        )

    notes.append(
        "Restore drill now captures live non-destructive evidence against critical stores while preserving the governed recovery order."
    )
    outcome = "passed" if checks_passed == checks_total else "failed"
    return _finalize_flow(
        flow_id="restore_drill",
        last_outcome=outcome,
        checks_passed=checks_passed,
        checks_total=checks_total,
        started_at=started_at,
        status="live_partial" if outcome == "passed" else "degraded",
        notes=notes,
        details={
            "drill_mode": "non_destructive_live_probe",
            "verified_store_count": verified_store_count,
            "store_count": len(store_results),
            "stores": store_results,
        },
    )


FLOW_RUNNERS = {
    "pause_resume": _run_pause_resume_flow,
    "presence_tier": _run_presence_tier_flow,
    "scheduled_job_governance": _run_scheduled_job_governance_flow,
    "sovereign_routing": _run_sovereign_routing_flow,
    "provider_fallback": _run_provider_fallback_flow,
    "stuck_queue_recovery": _run_stuck_queue_recovery_flow,
    "incident_review": _run_incident_review_flow,
    "tool_permissions": _run_tool_permissions_flow,
    "economic_governance": _run_economic_governance_flow,
    "promotion_ladder": _run_promotion_ladder_flow,
    "retirement_policy": _run_retirement_policy_flow,
    "data_lifecycle": _run_data_lifecycle_flow,
    "restore_drill": _run_restore_drill_flow,
}


async def build_operator_tests_snapshot() -> dict[str, Any]:
    try:
        redis = await _get_redis()
        raw = await redis.hgetall(OPERATOR_TEST_RESULTS_KEY)
        stored = {
            key: value if isinstance(value, dict) else json.loads(value)
            for key, value in raw.items()
        }
    except Exception:
        stored = {}

    flows: list[dict[str, Any]] = []
    for flow_id, definition in FLOW_DEFINITIONS.items():
        latest = dict(stored.get(flow_id) or {})
        flows.append(
            {
                "id": flow_id,
                "title": str(definition["title"]),
                "description": str(definition["description"]),
                "status": str(latest.get("status") or "configured"),
                "last_outcome": latest.get("last_outcome"),
                "last_run_at": latest.get("last_run_at"),
                "last_duration_ms": latest.get("last_duration_ms"),
                "checks_passed": int(latest.get("checks_passed", 0) or 0),
                "checks_total": int(latest.get("checks_total", 0) or 0),
                "evidence": list(latest.get("evidence") or definition["evidence"]),
                "notes": list(latest.get("notes") or []),
                "details": dict(latest.get("details") or {}),
            }
        )

    flows.sort(key=lambda item: item["title"])
    status, last_outcome = _build_operator_tests_status(flows)
    dated_flows = [flow for flow in flows if flow.get("last_run_at")]
    last_run_at = max((flow["last_run_at"] for flow in dated_flows), default=None)

    return {
        "generated_at": _now_iso(),
        "status": status,
        "last_outcome": last_outcome,
        "last_run_at": last_run_at,
        "flow_count": len(flows),
        "flows": flows,
    }


async def run_operator_tests(
    *,
    flow_ids: list[str] | None = None,
    actor: str = "operator-tests",
) -> dict[str, Any]:
    from .activity import log_event

    selected_ids = [
        flow_id for flow_id in (flow_ids or list(FLOW_DEFINITIONS.keys())) if flow_id in FLOW_RUNNERS
    ]
    redis = await _get_redis()

    for flow_id in selected_ids:
        result = await FLOW_RUNNERS[flow_id]()
        await redis.hset(OPERATOR_TEST_RESULTS_KEY, flow_id, json.dumps(result.to_dict()))
        await log_event(
            event_type=f"operator_test_{result.last_outcome or 'unknown'}",
            agent="governor",
            data={
                "flow_id": flow_id,
                "status": result.status,
                "checks_passed": result.checks_passed,
                "checks_total": result.checks_total,
                "actor": actor,
            },
            description=f"{result.title}: {result.last_outcome or 'unknown'}",
        )

    return await build_operator_tests_snapshot()
