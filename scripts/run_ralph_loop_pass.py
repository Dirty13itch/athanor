#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from automation_records import AutomationRunRecord, emit_automation_run_record, read_recent_automation_run_records
from closure_finish_common import build_finish_scoreboard, build_runtime_packet_inbox
from layered_master_plan import build_publication_debt_summary, build_recovery_drill_summary
from truth_inventory import resolve_external_path

try:
    from scripts._cluster_config import get_url
except ModuleNotFoundError:
    from _cluster_config import get_url

try:
    from scripts.runtime_env import load_optional_runtime_env
except ModuleNotFoundError:
    from runtime_env import load_optional_runtime_env


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
REPORT_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
GOVERNED_DISPATCH_REPORT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"
GOVERNED_DISPATCH_MATERIALIZATION_REPORT_PATH = (
    REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-materialization.json"
)
GOVERNED_DISPATCH_EXECUTION_REPORT_PATH = (
    REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-execution.json"
)
PUBLICATION_DEFERRED_QUEUE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "publication-deferred-family-queue.json"
RALPH_CONTINUITY_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "ralph-continuity-state.json"
BURN_REGISTRY_PATH = CONFIG_DIR / "subscription-burn-registry.json"
PROVIDER_CATALOG_PATH = CONFIG_DIR / "provider-catalog.json"
APPROVAL_MATRIX_PATH = CONFIG_DIR / "approval-matrix.json"
RUNTIME_PACKETS_PATH = CONFIG_DIR / "runtime-ownership-packets.json"
SAFE_SURFACE_STATE_PATH = resolve_external_path("C:/Users/Shaun/.codex/control/safe-surface-state.json")
SAFE_SURFACE_QUEUE_PATH = resolve_external_path("C:/Users/Shaun/.codex/control/safe-surface-queue.json")
WINDOWS_GIT_CANDIDATES = [
    Path('/mnt/c/Program Files/Git/cmd/git.exe'),
    Path('/mnt/c/Program Files/Git/bin/git.exe'),
    Path('/mnt/c/Program Files/Git/mingw64/bin/git.exe'),
]
GIT_PROBE_TIMEOUT_SECONDS = 20

REFRESH_COMMANDS: list[list[str]] = [
    [sys.executable, "scripts/collect_truth_inventory.py"],
    [sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
    [sys.executable, "scripts/collect_capacity_telemetry.py"],
    [sys.executable, "scripts/write_quota_truth_snapshot.py"],
    [sys.executable, "scripts/sync_github_portfolio_registry.py"],
    [sys.executable, "scripts/discover_reconciliation_sources.py"],
    [sys.executable, "scripts/generate_tenant_family_audit.py"],
    [sys.executable, "scripts/generate_field_inspect_operations_runtime_replay_packet.py"],
    [sys.executable, "scripts/generate_rfi_hers_duplicate_evidence_packet.py"],
    [sys.executable, "scripts/generate_rfi_hers_primary_root_stabilization_packet.py"],
    [sys.executable, "scripts/generate_wan2gp_remote_only_watch_packet.py"],
    [sys.executable, "scripts/generate_truth_inventory_reports.py"],
    [sys.executable, "scripts/generate_documentation_index.py"],
    [sys.executable, "scripts/run_contract_healer.py"],
]

VALIDATION_COMMANDS: list[list[str]] = [
    [sys.executable, "scripts/validate_platform_contract.py"],
    [sys.executable, "scripts/generate_documentation_index.py", "--check"],
    [sys.executable, "scripts/generate_project_maturity_report.py", "--check"],
    [sys.executable, "scripts/generate_truth_inventory_reports.py", "--check"],
]

LOOP_FAMILY_NEXT_COMMANDS: dict[str, list[list[str]]] = {
    "evidence_refresh": REFRESH_COMMANDS,
    "classification_backlog": [
        [sys.executable, "scripts/sync_github_portfolio_registry.py"],
        [sys.executable, "scripts/discover_reconciliation_sources.py"],
        [sys.executable, "scripts/generate_tenant_family_audit.py"],
    ],
    "repo_safe_repair_planning": VALIDATION_COMMANDS,
    "governed_runtime_packets": [
        [sys.executable, "scripts/collect_truth_inventory.py"],
        [sys.executable, "scripts/generate_truth_inventory_reports.py", "--report", "runtime_ownership", "--report", "runtime_ownership_packets"],
    ],
    "publication_freeze": VALIDATION_COMMANDS,
    "steady_state_maintenance": [
        [sys.executable, "scripts/run_contract_healer.py"],
        [sys.executable, "scripts/generate_documentation_index.py", "--check"],
    ],
    "governor_scheduling": [],
}
NEXT_ACTION_FAMILY_COMMANDS: dict[str, list[list[str]]] = {
    "repo_safe_repair": VALIDATION_COMMANDS,
    "deployment_truth_narrowing": [
        [sys.executable, "scripts/collect_truth_inventory.py"],
        [sys.executable, "scripts/generate_truth_inventory_reports.py"],
    ],
    "packet_reprobe_and_governed_maintenance": [
        [sys.executable, "scripts/collect_truth_inventory.py"],
        [
            sys.executable,
            "scripts/generate_truth_inventory_reports.py",
            "--report",
            "runtime_ownership",
            "--report",
            "runtime_ownership_packets",
        ],
    ],
    "provider_auth_repair_or_demotion": [
        [
            sys.executable,
            "scripts/generate_truth_inventory_reports.py",
            "--report",
            "providers",
            "--report",
            "secret_surfaces",
            "--report",
            "vault_litellm_repair_packet",
        ]
    ],
    "classification_and_disposition_followthrough": [
        [sys.executable, "scripts/sync_github_portfolio_registry.py"],
        [sys.executable, "scripts/discover_reconciliation_sources.py"],
        [sys.executable, "scripts/generate_tenant_family_audit.py"],
    ],
    "shared_extraction_and_ledger_updates": [
        [sys.executable, "scripts/generate_truth_inventory_reports.py"],
    ],
    "tenant_locking_and_followthrough": [
        [sys.executable, "scripts/discover_reconciliation_sources.py"],
        [sys.executable, "scripts/generate_tenant_family_audit.py"],
    ],
    "steady_state_prune_followthrough": [
        [sys.executable, "scripts/generate_documentation_index.py"],
    ],
    "dispatch_truth_and_queue_replenishment": [
        [sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
        [sys.executable, "scripts/collect_capacity_telemetry.py"],
        [sys.executable, "scripts/write_quota_truth_snapshot.py"],
        [sys.executable, "scripts/run_ralph_loop_pass.py", "--skip-refresh"],
        [sys.executable, "scripts/validate_platform_contract.py"],
    ],
    "graphrag_hybrid_timeout_hardening": [
        [sys.executable, "scripts/run_graphrag_promotion_eval.py"],
    ],
    "goose_boundary_and_evidence_capture": [
        [sys.executable, "scripts/generate_goose_operator_shell_boundary_evidence.py"],
        [sys.executable, "scripts/run_capability_pilot_evals.py"],
        [sys.executable, "scripts/generate_capability_pilot_readiness.py"],
    ],
    "validation_and_checkpoint": VALIDATION_COMMANDS,
    "monitoring_truth_narrowing": [
        [sys.executable, "scripts/collect_truth_inventory.py"],
        [sys.executable, "scripts/generate_truth_inventory_reports.py"],
    ],
    "capacity_truth_and_harvest_admission": [
        [sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
        [sys.executable, "scripts/collect_capacity_telemetry.py"],
        [sys.executable, "scripts/write_quota_truth_snapshot.py"],
    ],
    "ranked_autonomous_dispatch": [],
}
AUTONOMOUS_VALUE_CLASS_ORDER = {
    "provider_auth_drift": 1000,
    "capacity_truth_drift": 950,
    "dispatch_truth_drift": 900,
    "promotion_wave_closure": 850,
    "failing_eval_or_validator": 800,
    "repo_safe_system_hardening": 700,
    "secondary_tenant_or_product_work": 600,
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TERMINAL_EXECUTION_STATES = {"completed", "steady_state_monitoring"}
TERMINAL_RECONCILIATION_GATE_STATES = {
    "completed",
    "ready_for_operator_approval",
    "external_dependency_blocked",
    "steady_state_monitoring",
}
ACTIVE_PROVIDER_GATE_BLOCKER_CLASSIFICATIONS = {
    "missing_required_env",
    "present_key_invalid",
    "auth_surface_mismatch",
    "auth_failed_unknown",
}
EXCLUDED_PROVIDER_GATE_POSTURES = {
    "optional_elasticity_demoted",
    "governed_handoff_only",
}
READY_PROVIDER_USAGE_STATUSES = {"observed"}
READY_ROUTING_POSTURES = {"ordinary_auto"}
DISPATCH_ELIGIBLE_BACKLOG_STATUSES = {"captured", "triaged", "ready"}
DISPATCH_ACTIVE_BACKLOG_STATUSES = {"scheduled", "running", "waiting_approval"}
DISPATCH_TERMINAL_BACKLOG_STATUSES = {"completed", "failed", "archived", "blocked"}
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
FRESHNESS_TARGETS: dict[str, dict[str, Any]] = {
    "truth_snapshot": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "latest.json",
        "max_age_seconds": 24 * 3600,
        "kind": "core_evidence",
    },
    "contract_healer": {
        "path": REPO_ROOT / "audit" / "automation" / "contract-healer-latest.json",
        "max_age_seconds": 24 * 3600,
        "kind": "core_evidence",
    },
    "github_portfolio": {
        "path": REPO_ROOT / "reports" / "reconciliation" / "github-portfolio-latest.json",
        "max_age_seconds": 24 * 3600,
        "kind": "portfolio_evidence",
    },
    "reconciliation_discovery": {
        "path": REPO_ROOT / "reports" / "reconciliation" / "discovery-latest.json",
        "max_age_seconds": 24 * 3600,
        "kind": "portfolio_evidence",
    },
    "tenant_family_audit": {
        "path": REPO_ROOT / "reports" / "reconciliation" / "tenant-family-audit-latest.json",
        "max_age_seconds": 24 * 3600,
        "kind": "portfolio_evidence",
    },
    "provider_usage_evidence": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json",
        "max_age_seconds": 72 * 3600,
        "kind": "provider_evidence",
    },
    "quota_truth": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "quota-truth.json",
        "max_age_seconds": 6 * 3600,
        "kind": "routing_evidence",
    },
    "capacity_telemetry": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json",
        "max_age_seconds": 15 * 60,
        "kind": "capacity_evidence",
    },
    "active_overrides": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "active-overrides.json",
        "max_age_seconds": 24 * 3600,
        "kind": "governor_evidence",
    },
    "routing_proof": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "routing-proof.json",
        "max_age_seconds": 24 * 3600,
        "kind": "routing_evidence",
    },
    "vault_litellm_env_audit": {
        "path": REPO_ROOT / "reports" / "truth-inventory" / "vault-litellm-env-audit.json",
        "max_age_seconds": 48 * 3600,
        "kind": "provider_evidence",
    },
    "runtime_ownership_packets": {
        "path": REPO_ROOT / "docs" / "operations" / "RUNTIME-OWNERSHIP-PACKETS.md",
        "max_age_seconds": 48 * 3600,
        "kind": "runtime_packet_surface",
    },
}

AUTOMATION_FEEDBACK_RECENT_LIMIT = 8


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": round(self.duration_seconds, 3),
        }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(loaded) if isinstance(loaded, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _load_agent_runtime() -> tuple[str, str]:
    load_optional_runtime_env(env_names=["ATHANOR_AGENT_API_TOKEN"])
    base_url = _clean_str(os.environ.get("ATHANOR_AGENT_SERVER_URL")) or _clean_str(get_url("agent_server"))
    token = _clean_str(os.environ.get("ATHANOR_AGENT_API_TOKEN"))
    return base_url.rstrip("/"), token


def _request_agent_json(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = Request(f"{base_url}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload_data = {"error": body or str(exc)}
        return exc.code, payload_data
    except (TimeoutError, socket.timeout) as exc:
        return 598, {"error": f"timeout: {exc}", "type": type(exc).__name__}
    except URLError as exc:
        return 599, {"error": str(exc)}


def _run_command(command: list[str]) -> CommandResult:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    max_chars = 1200
    if len(stdout) > max_chars:
        stdout = stdout[:max_chars] + "\n...[truncated]..."
    if len(stderr) > max_chars:
        stderr = stderr[:max_chars] + "\n...[truncated]..."
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.perf_counter() - started,
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _shift_iso_window(
    observed_at: str | None,
    stale_after: str | None,
    replacement_observed_at: str | None,
) -> str | None:
    observed_dt = _parse_iso_datetime(observed_at)
    stale_dt = _parse_iso_datetime(stale_after)
    replacement_dt = _parse_iso_datetime(replacement_observed_at)
    if observed_dt is None or stale_dt is None or replacement_dt is None:
        return None
    freshness_window = stale_dt - observed_dt
    if freshness_window.total_seconds() <= 0:
        return None
    return (replacement_dt + freshness_window).isoformat()



def _continuity_policy(completion_program: dict[str, Any]) -> dict[str, Any]:
    policy = dict(completion_program.get("continuity_policy") or {})
    feeder_precedence = [
        str(item).strip()
        for item in policy.get("feeder_precedence", [])
        if str(item).strip()
    ]
    hard_brakes = [
        str(item).strip()
        for item in policy.get("hard_brakes", [])
        if str(item).strip()
    ]
    material_repo_delta_prefixes = [
        str(item).strip()
        for item in policy.get("material_repo_delta_prefixes", [])
        if str(item).strip()
    ]
    workstream_continuity: dict[str, dict[str, Any]] = {}
    for raw_workstream_id, raw_entry in dict(policy.get("workstream_continuity") or {}).items():
        workstream_id = str(raw_workstream_id or "").strip()
        if not workstream_id or not isinstance(raw_entry, dict):
            continue
        no_delta = dict(raw_entry.get("no_delta_closure_criteria") or {})
        reopen_scope = dict(raw_entry.get("reopen_scope") or {})
        workstream_continuity[workstream_id] = {
            "no_delta_closure_criteria": {
                "required_evidence_refs": [
                    str(item).strip()
                    for item in no_delta.get("required_evidence_refs", [])
                    if str(item).strip()
                ],
                "summary": str(no_delta.get("summary") or "").strip() or None,
            },
            "reopen_scope": {
                "reason_scope": str(reopen_scope.get("reason_scope") or "").strip() or None,
                "repo_delta_prefixes": [
                    str(item).strip()
                    for item in reopen_scope.get("repo_delta_prefixes", [])
                    if str(item).strip()
                ],
            },
        }
    if "validation-and-publication" not in workstream_continuity:
        workstream_continuity["validation-and-publication"] = {
            "no_delta_closure_criteria": {
                "required_evidence_refs": [],
                "summary": None,
            },
            "reopen_scope": {
                "reason_scope": "material_repo_delta_any",
                "repo_delta_prefixes": [],
            },
        }
    return {
        "no_delta_suppression_ttl_hours": max(1, int(policy.get("no_delta_suppression_ttl_hours") or 12)),
        "feeder_precedence": feeder_precedence
        or ["workstream", "cash_now_deferred_family", "burn_class", "safe_surface", "provider_gate"],
        "hard_brakes": hard_brakes
        or ["approval_required", "external_block", "destructive_ambiguity", "queue_exhausted"],
        "cash_now_deferred_families_are_autonomous_inputs": bool(
            policy.get("cash_now_deferred_families_are_autonomous_inputs", True)
        ),
        "cash_now_requires_no_unsuppressed_workstream": bool(
            policy.get("cash_now_requires_no_unsuppressed_workstream", True)
        ),
        "green_not_stop_condition": bool(policy.get("green_not_stop_condition", True)),
        "claim_history_limit": max(1, int(policy.get("claim_history_limit") or 12)),
        "executive_reporting_contract": dict(policy.get("executive_reporting_contract") or {}),
        "material_repo_delta_reopens_validation_publication": bool(
            policy.get("material_repo_delta_reopens_validation_publication", True)
        ),
        "material_repo_delta_prefixes": material_repo_delta_prefixes
        or ["STATUS.md", "docs/", "config/", "scripts/", "projects/", "ansible/", "services/", "tests/", "evals/", "recipes/"],
        "workstream_continuity": workstream_continuity,
    }


def _active_continuity_suppression(
    previous_continuity_state: dict[str, Any],
    automation_feedback_summary: dict[str, Any],
    *,
    generated_at: str,
    continuity_policy: dict[str, Any],
) -> dict[str, Any]:
    generated_dt = _parse_iso_datetime(generated_at) or datetime.now(timezone.utc)
    suppressed_until_by_task: dict[str, str] = {}
    previous_suppressed = dict(previous_continuity_state.get("suppressed_until_by_task") or {})
    for raw_task_id, raw_expiry in previous_suppressed.items():
        task_id = str(raw_task_id or "").strip()
        expiry_dt = _parse_iso_datetime(raw_expiry)
        if not task_id or expiry_dt is None or expiry_dt <= generated_dt:
            continue
        suppressed_until_by_task[task_id] = expiry_dt.isoformat()

    ttl_hours = int(continuity_policy.get("no_delta_suppression_ttl_hours") or 12)
    expiry_at = (generated_dt + timedelta(hours=ttl_hours)).isoformat()
    for raw_task_id in automation_feedback_summary.get("recent_no_delta_task_ids") or []:
        task_id = str(raw_task_id or "").strip()
        if not task_id:
            continue
        suppressed_until_by_task[task_id] = expiry_at

    return {
        "recent_no_delta_task_ids": sorted(suppressed_until_by_task.keys()),
        "suppressed_until_by_task": suppressed_until_by_task,
        "last_real_delta_task_id": str(automation_feedback_summary.get("last_real_delta_task_id") or "").strip() or None,
        "last_real_delta_at": str(automation_feedback_summary.get("last_real_delta_at") or "").strip() or None,
    }


def _queue_item_effectively_dispatchable(item: dict[str, Any]) -> bool:
    return bool(item.get("dispatchable")) and not bool(item.get("suppressed_by_continuity"))


def _queue_source_precedence_key(item: dict[str, Any], continuity_policy: dict[str, Any]) -> int:
    feeder_precedence = [
        str(entry).strip()
        for entry in continuity_policy.get("feeder_precedence", [])
        if str(entry).strip()
    ]
    precedence_index = {entry: index for index, entry in enumerate(feeder_precedence)}
    source_type = str(item.get("source_type") or "").strip()
    source_family = {
        "workstream": "workstream",
        "burn_class": "burn_class",
        "safe_surface_queue": "safe_surface",
        "provider_gate": "provider_gate",
        "publication_deferred_family": "cash_now_deferred_family",
    }.get(source_type, source_type)
    return precedence_index.get(source_family, len(precedence_index))


def _queue_candidate_ref(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(item, dict) or not item:
        return None
    task_id = str(item.get("task_id") or "").strip() or None
    title = str(item.get("title") or "").strip() or None
    if not task_id and not title:
        return None
    return {
        "task_id": task_id,
        "title": title,
        "preferred_lane_family": str(item.get("preferred_lane_family") or "").strip() or None,
        "source_type": str(item.get("source_type") or "").strip() or None,
        "approved_mutation_class": str(item.get("approved_mutation_class") or "").strip() or None,
        "blocking_reason": str(item.get("blocking_reason") or "").strip() or None,
    }


def _path_matches_prefixes(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes if prefix)


def _load_optional_repo_json(relative_path: str) -> dict[str, Any]:
    if not relative_path:
        return {}
    path = REPO_ROOT / relative_path
    if not path.is_file():
        return {}
    try:
        payload = _load_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _repo_material_worktree_delta_paths(continuity_policy: dict[str, Any]) -> list[str]:
    prefixes = [
        str(item).strip()
        for item in continuity_policy.get("material_repo_delta_prefixes", [])
        if str(item).strip()
    ]
    if not prefixes:
        return []
    command, repo_path = _repo_git_probe_context(REPO_ROOT)
    try:
        completed = subprocess.run(
            [*command, '-C', repo_path, 'status', '--short', '--untracked-files=normal', '--no-renames'],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    matched_paths: list[str] = []
    for raw_line in completed.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        candidate = line[3:].strip() if len(line) > 3 else line.strip()
        if ' -> ' in candidate:
            candidate = candidate.split(' -> ', 1)[1].strip()
        if _path_matches_prefixes(candidate, prefixes):
            matched_paths.append(candidate)
    return matched_paths


def _workstream_continuity_entry(continuity_policy: dict[str, Any], workstream_id: str) -> dict[str, Any]:
    workstream_continuity = dict(continuity_policy.get("workstream_continuity") or {})
    return dict(workstream_continuity.get(workstream_id) or {})


def _continuity_repo_delta_reopen_detail(
    item: dict[str, Any],
    *,
    enabled: bool,
    continuity_policy: dict[str, Any],
    repo_delta_paths: list[str],
) -> dict[str, Any]:
    task_id = str(item.get("task_id") or "").strip()
    source_type = str(item.get("source_type") or "").strip()
    if not enabled:
        return {
            "reopened": False,
            "reopen_reason_scope": None,
            "matched_repo_delta_paths": [],
        }
    if source_type == "publication_deferred_family":
        return {
            "reopened": bool(repo_delta_paths),
            "reopen_reason_scope": "material_repo_delta_any",
            "matched_repo_delta_paths": list(repo_delta_paths),
        }
    if source_type != "workstream":
        return {
            "reopened": False,
            "reopen_reason_scope": None,
            "matched_repo_delta_paths": [],
        }
    workstream_id = str(item.get("workstream_id") or task_id.removeprefix("workstream:"))
    continuity_entry = _workstream_continuity_entry(continuity_policy, workstream_id)
    reopen_scope = dict(continuity_entry.get("reopen_scope") or {})
    reason_scope = str(reopen_scope.get("reason_scope") or "").strip() or None
    prefixes = [
        str(entry).strip()
        for entry in reopen_scope.get("repo_delta_prefixes", [])
        if str(entry).strip()
    ]
    if reason_scope == "material_repo_delta_any":
        matched_paths = list(repo_delta_paths)
    elif prefixes:
        matched_paths = [path for path in repo_delta_paths if _path_matches_prefixes(path, prefixes)]
    else:
        matched_paths = []
    return {
        "reopened": bool(matched_paths),
        "reopen_reason_scope": reason_scope,
        "matched_repo_delta_paths": matched_paths,
    }


def _dispatch_repo_side_no_delta_detail(
    continuity_entry: dict[str, Any],
    matched_repo_delta_paths: list[str],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    no_delta = dict(continuity_entry.get("no_delta_closure_criteria") or {})
    evidence_refs = [
        str(item).strip()
        for item in no_delta.get("required_evidence_refs", [])
        if str(item).strip()
    ]
    baseline = _load_optional_repo_json("reports/truth-inventory/gpu-scheduler-baseline-eval.json")
    baseline_summary = dict(baseline.get("summary") or {})
    baseline_ok = (
        str(baseline_summary.get("baseline_alignment_status") or "").strip() == "passed"
        and str(baseline_summary.get("capacity_truth_alignment_status") or "").strip() == "passed"
        and bool(baseline_summary.get("formal_eval_ready"))
    )
    capacity_summary = dict((capacity_telemetry or {}).get("capacity_summary") or (capacity_telemetry or {}))
    capacity_ok = (
        int(capacity_summary.get("scheduler_slot_count") or 0) > 0
        and str(capacity_summary.get("sample_posture") or "").strip() == "scheduler_projection_backed"
    )
    quota_records = [record for record in quota_truth.get("records", []) if isinstance(record, dict)]
    quota_ok = bool(quota_records) and all(not str(record.get("degraded_reason") or "").strip() for record in quota_records)
    repo_side_no_delta = baseline_ok and capacity_ok and quota_ok and not matched_repo_delta_paths
    return {
        "repo_side_no_delta": repo_side_no_delta,
        "rotation_ready": repo_side_no_delta,
        "no_delta_evidence_refs": evidence_refs,
        "no_delta_summary": str(no_delta.get("summary") or "").strip() or None,
    }


def _workstream_repo_side_no_delta_detail(
    item: dict[str, Any],
    continuity_policy: dict[str, Any],
    matched_repo_delta_paths: list[str],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    task_id = str(item.get("task_id") or "").strip()
    source_type = str(item.get("source_type") or "").strip()
    if source_type != "workstream":
        return {
            "repo_side_no_delta": False,
            "rotation_ready": False,
            "no_delta_evidence_refs": [],
            "no_delta_summary": None,
        }
    workstream_id = str(item.get("workstream_id") or task_id.removeprefix("workstream:"))
    continuity_entry = _workstream_continuity_entry(continuity_policy, workstream_id)
    no_delta = dict(continuity_entry.get("no_delta_closure_criteria") or {})
    evidence_refs = [
        str(entry).strip()
        for entry in no_delta.get("required_evidence_refs", [])
        if str(entry).strip()
    ]
    detail = {
        "repo_side_no_delta": False,
        "rotation_ready": False,
        "no_delta_evidence_refs": evidence_refs,
        "no_delta_summary": str(no_delta.get("summary") or "").strip() or None,
    }
    if workstream_id == "dispatch-and-work-economy-closure":
        detail.update(
            _dispatch_repo_side_no_delta_detail(
                continuity_entry,
                matched_repo_delta_paths,
                quota_truth,
                capacity_telemetry,
            )
        )
    return detail


def _stop_state_from_queue_item(item: dict[str, Any] | None) -> tuple[str, str | None]:
    if not isinstance(item, dict) or not item:
        return "queue_exhausted", "No dispatchable or blocked tranche remains."
    blocking_reason = str(item.get("blocking_reason") or "").strip()
    title = str(item.get("title") or item.get("task_id") or "queue item").strip() or "queue item"
    if blocking_reason == "approval_required":
        return "approval_required", f"{title} requires approval before autonomous continuation."
    if blocking_reason in {"external_dependency_blocked", "no_eligible_provider"}:
        return "external_block", f"{title} is blocked on an external dependency or unavailable provider."
    if blocking_reason == "destructive_ambiguity":
        return "destructive_ambiguity", f"{title} needs disambiguation before destructive cleanup can proceed."
    return "queue_exhausted", "No unblocked autonomous tranche remains after continuity suppression."


def _artifact_freshness(now_ts: float) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for artifact_id, config in FRESHNESS_TARGETS.items():
        path = Path(config["path"])
        exists = path.exists()
        age_seconds = None
        stale = True
        mtime_iso = None
        if exists:
            mtime = path.stat().st_mtime
            age_seconds = max(0, int(now_ts - mtime))
            stale = age_seconds > int(config["max_age_seconds"])
            mtime_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        results[artifact_id] = {
            "id": artifact_id,
            "path": str(path.relative_to(REPO_ROOT).as_posix()),
            "kind": str(config["kind"]),
            "exists": exists,
            "stale": stale,
            "max_age_seconds": int(config["max_age_seconds"]),
            "age_seconds": age_seconds,
            "modified_at": mtime_iso,
        }
    return results


def _dependency_state(workstream: dict[str, Any], workstreams_by_id: dict[str, dict[str, Any]]) -> str:
    dependencies = [str(item).strip() for item in workstream.get("dependencies", []) if str(item).strip()]
    if not dependencies:
        return "satisfied"
    for dependency_id in dependencies:
        dependency = workstreams_by_id.get(dependency_id)
        if dependency is None:
            return "blocked_missing_dependency"
        dependency_state = str(dependency.get("execution_state") or "")
        dependency_status = str(dependency.get("status") or "")
        if dependency_status == "planned":
            return "blocked_planned_dependency"
        if dependency_state == "external_dependency_blocked":
            return "blocked_external_dependency"
    return "satisfied"


def _evidence_state_for_workstream(
    workstream: dict[str, Any],
    artifact_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    workstream_artifacts = [str(item).strip() for item in workstream.get("evidence_artifacts", []) if str(item).strip()]
    artifact_rows: list[dict[str, Any]] = []
    stale_count = 0
    for artifact in workstream_artifacts:
        artifact_path = str(Path(artifact).as_posix())
        freshness_match = next(
            (
                row
                for row in artifact_index.values()
                if row["path"] == artifact_path
            ),
            None,
        )
        if freshness_match is None:
            row = {
                "path": artifact_path,
                "tracked": False,
                "exists": (REPO_ROOT / artifact).exists(),
                "stale": False,
            }
        else:
            row = {
                "path": artifact_path,
                "tracked": True,
                "exists": freshness_match["exists"],
                "stale": freshness_match["stale"],
                "age_seconds": freshness_match["age_seconds"],
                "kind": freshness_match["kind"],
            }
        if row.get("stale"):
            stale_count += 1
        artifact_rows.append(row)
    return {
        "artifacts": artifact_rows,
        "stale_count": stale_count,
        "fresh_count": sum(1 for row in artifact_rows if row.get("tracked") and not row.get("stale")),
        "state": "stale_evidence" if stale_count else "fresh",
    }


def _rank_workstream(workstream: dict[str, Any], dependency_state: str, evidence_state: str, order_index: int) -> tuple[int, int, int, int]:
    priority_value = PRIORITY_ORDER.get(str(workstream.get("priority") or ""), 99)
    status_bonus = 0
    execution_state = str(workstream.get("execution_state") or "")
    if execution_state == "ready_for_operator_approval":
        status_bonus = 1
    elif execution_state == "external_dependency_blocked":
        status_bonus = 2
    elif execution_state == "steady_state_monitoring":
        status_bonus = 4
    dependency_bonus = 0 if dependency_state == "satisfied" else 5
    evidence_bonus = 0 if evidence_state == "fresh" else -1
    return (priority_value, dependency_bonus, status_bonus, order_index + evidence_bonus)


def _select_active_workstream(workstreams: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        workstreams,
        key=lambda row: _rank_workstream(
            row["workstream"],
            str(row["dependency_state"]),
            str(row["evidence_state"]["state"]),
            int(row["order_index"]),
        ),
    )
    for row in ranked:
        execution_state = str(row["workstream"].get("execution_state") or "")
        if execution_state not in TERMINAL_EXECUTION_STATES:
            return row
    return ranked[0]


def _provider_gate_state(completion_program: dict[str, Any]) -> str:
    end_state = dict(completion_program.get("reconciliation_end_state") or {})
    for gate in end_state.get("project_exit_gates", []):
        if not isinstance(gate, dict):
            continue
        if str(gate.get("id") or "").strip() == "provider_gate":
            return str(gate.get("status") or "").strip() or "unknown"
    return "unknown"


def _provider_gate_detail(provider_catalog: dict[str, Any]) -> dict[str, Any]:
    blocking_entries: list[dict[str, str]] = []
    excluded_entries: list[dict[str, str]] = []
    ignored_entries: list[dict[str, str]] = []
    classification_counts: dict[str, int] = {}
    critical_provider_ids = {
        str(family.get(field) or "").strip()
        for family in provider_catalog.get("routing_families", [])
        if isinstance(family, dict)
        for field in ("primary_provider_id", "overflow_provider_id")
        if str(family.get(field) or "").strip()
    }

    for provider in provider_catalog.get("providers", []):
        if not isinstance(provider, dict):
            continue
        provider_id = str(provider.get("id") or "").strip()
        if not provider_id:
            continue
        category = str(provider.get("category") or "").strip().lower()
        state_classes = {str(item).strip().lower() for item in provider.get("state_classes", [])}
        classification = str(dict(provider.get("vault_remediation") or {}).get("classification") or "none").strip()
        provider_gate_posture = str(provider.get("provider_gate_posture") or "").strip()
        entry = {
            "id": provider_id,
            "label": str(provider.get("label") or provider_id),
            "classification": classification or "none",
            "provider_gate_posture": provider_gate_posture or "default",
        }

        if category != "api" or "active-api" not in state_classes:
            ignored_entries.append(entry)
            continue

        provider_specific_usage = dict(dict(provider.get("evidence") or {}).get("provider_specific_usage") or {})
        probe_status = str(provider_specific_usage.get("status") or "").strip().lower()
        if probe_status != "auth_failed":
            ignored_entries.append(entry)
            continue

        observed_runtime = dict(provider.get("observed_runtime") or {})
        if provider_gate_posture in EXCLUDED_PROVIDER_GATE_POSTURES:
            excluded_entries.append(entry)
            continue
        if (
            provider_id not in critical_provider_ids
            and not bool(observed_runtime.get("routing_policy_enabled"))
            and not bool(observed_runtime.get("active_burn_observed"))
            and provider_gate_posture != "turnover_critical_overflow"
        ):
            excluded_entries.append(
                {
                    **entry,
                    "provider_gate_posture": provider_gate_posture or "optional_non_routed_api_lane",
                }
            )
            continue
        if classification in ACTIVE_PROVIDER_GATE_BLOCKER_CLASSIFICATIONS or not classification:
            blocking_entries.append(entry)
            classification_key = classification or "unclassified_auth_failed"
            classification_counts[classification_key] = classification_counts.get(classification_key, 0) + 1
            continue

        excluded_entries.append(entry)

    return {
        "status": "blocked" if blocking_entries else "clear",
        "blocking_provider_count": len(blocking_entries),
        "blocking_provider_ids": [entry["id"] for entry in blocking_entries],
        "blocking_provider_labels": [entry["label"] for entry in blocking_entries],
        "classification_counts": classification_counts,
        "excluded_provider_ids": [entry["id"] for entry in excluded_entries],
        "excluded_provider_labels": [entry["label"] for entry in excluded_entries],
        "excluded_provider_classifications": {
            entry["id"]: entry["classification"] for entry in excluded_entries
        },
        "excluded_provider_postures": {
            entry["id"]: entry["provider_gate_posture"] for entry in excluded_entries
        },
        "ignored_provider_ids": [entry["id"] for entry in ignored_entries],
    }


def _sync_provider_gate_registry_state(
    completion_program: dict[str, Any],
    provider_gate_detail: dict[str, Any],
) -> None:
    blocker_count = int(provider_gate_detail.get("blocking_provider_count") or 0)
    gate_status = "external_dependency_blocked" if blocker_count else "completed"
    gate_blocker_type = "external_dependency" if blocker_count else "none"

    end_state = dict(completion_program.get("reconciliation_end_state") or {})
    gate_rows: list[dict[str, Any]] = []
    for gate in end_state.get("project_exit_gates", []):
        if not isinstance(gate, dict):
            continue
        gate_row = dict(gate)
        if str(gate_row.get("id") or "").strip() == "provider_gate":
            gate_row["status"] = gate_status
            gate_row["blocker_type"] = gate_blocker_type
            gate_row["blocking_provider_count"] = blocker_count
            gate_row["blocking_provider_ids"] = list(provider_gate_detail.get("blocking_provider_ids") or [])
            gate_row["excluded_provider_ids"] = list(provider_gate_detail.get("excluded_provider_ids") or [])
            gate_row["classification_counts"] = dict(provider_gate_detail.get("classification_counts") or {})
        gate_rows.append(gate_row)
    end_state["project_exit_gates"] = gate_rows
    completion_program["reconciliation_end_state"] = end_state

    synced_workstreams: list[dict[str, Any]] = []
    for workstream in completion_program.get("workstreams", []):
        if not isinstance(workstream, dict):
            continue
        workstream_row = dict(workstream)
        if str(workstream_row.get("id") or "").strip() == "provider-and-secret-remediation":
            workstream_row["status"] = "blocked" if blocker_count else "continuous"
            workstream_row["execution_state"] = (
                "external_dependency_blocked" if blocker_count else "steady_state_monitoring"
            )
            workstream_row["blocker_type"] = gate_blocker_type
        synced_workstreams.append(workstream_row)
    completion_program["workstreams"] = synced_workstreams


def _provider_chain_entry_state(
    provider_id: str,
    providers_by_id: dict[str, dict[str, Any]],
    routing_provider_defs: dict[str, Any],
) -> dict[str, Any]:
    provider = providers_by_id.get(provider_id)
    if not isinstance(provider, dict):
        return {
            "provider_id": provider_id,
            "label": provider_id,
            "category": "unknown",
            "ready": False,
            "blocking_reason": "unknown_provider",
        }

    category = str(provider.get("category") or "").strip().lower()
    label = str(provider.get("label") or provider_id).strip() or provider_id
    if category == "api":
        usage = dict(dict(provider.get("evidence") or {}).get("provider_specific_usage") or {})
        usage_status = str(usage.get("status") or "").strip().lower()
        if usage_status in READY_PROVIDER_USAGE_STATUSES:
            return {
                "provider_id": provider_id,
                "label": label,
                "category": category,
                "ready": True,
                "blocking_reason": None,
                "evidence_status": usage_status,
            }
        classification = str(dict(provider.get("vault_remediation") or {}).get("classification") or "").strip()
        return {
            "provider_id": provider_id,
            "label": label,
            "category": category,
            "ready": False,
            "blocking_reason": classification or usage_status or "provider_evidence_missing",
            "evidence_status": usage_status or None,
        }

    routing_record = dict(routing_provider_defs.get(provider_id) or {})
    if category == "local":
        return {
            "provider_id": provider_id,
            "label": label,
            "category": category,
            "ready": True,
            "blocking_reason": None,
            "routing_posture": str(routing_record.get("routing_posture") or "ordinary_auto"),
        }

    enabled = routing_record.get("enabled")
    routing_posture = str(routing_record.get("routing_posture") or "").strip()
    if enabled is False:
        blocking_reason = "disabled"
    elif routing_posture in READY_ROUTING_POSTURES:
        blocking_reason = None
    else:
        blocking_reason = routing_posture or "not_dispatchable"
    return {
        "provider_id": provider_id,
        "label": label,
        "category": category or "unknown",
        "ready": blocking_reason is None,
        "blocking_reason": blocking_reason,
        "routing_posture": routing_posture or None,
    }


def _local_compute_capacity_detail(
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = [dict(record) for record in quota_truth.get("records", []) if isinstance(record, dict)]
    local_record = next(
        (
            record
            for record in records
            if str(record.get("family_id") or record.get("product_id") or "").strip() == "athanor_local_compute"
        ),
        {},
    )
    telemetry_summary = dict((capacity_telemetry or {}).get("capacity_summary") or {})
    capacity_breakdown = dict(local_record.get("capacity_breakdown") or {})
    harvestable_by_zone = {
        str(zone_id).strip(): int(count or 0)
        for zone_id, count in dict(
            telemetry_summary.get("harvestable_by_zone") or capacity_breakdown.get("harvestable_by_zone") or {}
        ).items()
        if str(zone_id).strip()
    }
    harvestable_by_slot = {
        str(slot_id).strip(): int(count or 0)
        for slot_id, count in dict(
            telemetry_summary.get("harvestable_by_slot") or capacity_breakdown.get("harvestable_by_slot") or {}
        ).items()
        if str(slot_id).strip()
    }
    slot_samples = [
        dict(sample)
        for sample in ((capacity_telemetry or {}).get("scheduler_slot_samples") or capacity_breakdown.get("scheduler_slot_samples", []))
        if isinstance(sample, dict)
    ]
    open_slot_ids: list[str] = []
    open_slot_target_ids: list[str] = []
    protected_reserve_slot_count = 0
    for sample in slot_samples:
        blocked_by = {
            str(reason).strip()
            for reason in sample.get("blocked_by", [])
            if str(reason).strip()
        }
        if "protected_reserve" in blocked_by:
            protected_reserve_slot_count += 1
        if int(sample.get("harvestable_gpu_count") or 0) <= 0:
            continue
        slot_id = str(sample.get("scheduler_slot_id") or "").strip()
        slot_target_id = str(sample.get("slot_target_id") or "").strip()
        if slot_id:
            open_slot_ids.append(slot_id)
        if slot_target_id:
            open_slot_target_ids.append(slot_target_id)

    queue_depth = int(telemetry_summary.get("scheduler_queue_depth") or capacity_breakdown.get("scheduler_queue_depth") or 0)
    harvestable_slot_count = int(
        telemetry_summary.get("harvestable_scheduler_slot_count")
        or capacity_breakdown.get("harvestable_scheduler_slot_count")
        or 0
    )
    scheduler_slot_count = int(
        telemetry_summary.get("scheduler_slot_count") or capacity_breakdown.get("scheduler_slot_count") or 0
    )
    sample_posture = str(
        telemetry_summary.get("sample_posture") or capacity_breakdown.get("sample_posture") or "unknown"
    )
    scheduler_observed_at = str(
        telemetry_summary.get("scheduler_observed_at") or capacity_breakdown.get("scheduler_observed_at") or ""
    ).strip() or None
    record_observed_at = str(local_record.get("last_observed_at") or "").strip() or None
    record_stale_after = str(local_record.get("stale_after") or "").strip() or None
    scheduler_backed = sample_posture == "scheduler_projection_backed" and scheduler_observed_at is not None
    if scheduler_backed:
        observed_at = scheduler_observed_at
        stale_after = _shift_iso_window(record_observed_at, record_stale_after, scheduler_observed_at)
    else:
        observed_at = record_observed_at
        stale_after = record_stale_after
    slot_ready = harvestable_slot_count > 0
    if slot_ready:
        slot_pressure_state = "open_harvest_window"
    elif scheduler_slot_count > 0:
        slot_pressure_state = "reserve_or_busy"
    else:
        slot_pressure_state = "no_scheduler_projection"

    return {
        "present": bool(local_record),
        "observed_at": observed_at,
        "stale_after": stale_after,
        "sample_posture": sample_posture,
        "scheduler_observed_at": scheduler_observed_at,
        "remaining_units": int(local_record.get("remaining_units") or 0),
        "scheduler_queue_depth": queue_depth,
        "scheduler_slot_count": scheduler_slot_count,
        "harvestable_scheduler_slot_count": harvestable_slot_count,
        "harvestable_by_zone": harvestable_by_zone,
        "harvestable_zone_ids": sorted(harvestable_by_zone),
        "harvestable_by_slot": harvestable_by_slot,
        "provisional_harvest_candidate_count": int(
            telemetry_summary.get("provisional_harvest_candidate_count")
            or capacity_breakdown.get("provisional_harvest_candidate_count")
            or 0
        ),
        "provisional_harvestable_by_node": {
            str(node_id).strip(): int(count or 0)
            for node_id, count in dict(
                capacity_breakdown.get("provisional_harvestable_by_node") or {}
            ).items()
            if str(node_id).strip()
        },
        "protected_reserve_slot_count": protected_reserve_slot_count,
        "open_harvest_slot_ids": open_slot_ids,
        "open_harvest_slot_target_ids": open_slot_target_ids,
        "idle_harvest_slots_open": slot_ready,
        "slot_pressure_state": slot_pressure_state,
    }


def _build_capacity_harvest_summary(local_compute_capacity: dict[str, Any]) -> dict[str, Any]:
    observed_at = (
        str(local_compute_capacity.get("scheduler_observed_at") or "").strip()
        or str(local_compute_capacity.get("observed_at") or "").strip()
        or None
    )
    observed_dt = _parse_iso_datetime(observed_at)
    sample_age_seconds = (
        max(0, int((datetime.now(timezone.utc) - observed_dt).total_seconds()))
        if observed_dt is not None
        else None
    )
    scheduler_slot_count = int(local_compute_capacity.get("scheduler_slot_count") or 0)
    queue_depth = int(local_compute_capacity.get("scheduler_queue_depth") or 0)
    harvestable_slot_count = int(local_compute_capacity.get("harvestable_scheduler_slot_count") or 0)
    if not bool(local_compute_capacity.get("present")):
        admission_state = "no_scheduler_projection"
    elif harvestable_slot_count > 0 and queue_depth > 0:
        admission_state = "harvest_open_queue_present"
    elif harvestable_slot_count > 0:
        admission_state = "open_harvest_window"
    elif queue_depth > 0:
        admission_state = "queued_work_waiting_on_capacity"
    elif scheduler_slot_count > 0:
        admission_state = "reserve_or_busy"
    else:
        admission_state = "no_scheduler_projection"

    return {
        "observed_at": observed_at,
        "sample_age_seconds": sample_age_seconds,
        "sample_posture": str(local_compute_capacity.get("sample_posture") or "unknown"),
        "scheduler_queue_depth": queue_depth,
        "scheduler_slot_count": scheduler_slot_count,
        "harvestable_scheduler_slot_count": harvestable_slot_count,
        "harvestable_zone_count": len(list(local_compute_capacity.get("harvestable_zone_ids") or [])),
        "harvestable_zone_ids": list(local_compute_capacity.get("harvestable_zone_ids") or []),
        "provisional_harvest_candidate_count": int(
            local_compute_capacity.get("provisional_harvest_candidate_count") or 0
        ),
        "protected_reserve_slot_count": int(local_compute_capacity.get("protected_reserve_slot_count") or 0),
        "admission_state": admission_state,
        "ready_for_harvest_now": harvestable_slot_count > 0,
    }


def _work_economy_detail(
    provider_catalog: dict[str, Any],
    routing_policy: dict[str, Any],
    burn_registry: dict[str, Any],
    provider_gate_detail: dict[str, Any],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    providers_by_id = {
        str(provider.get("id") or "").strip(): dict(provider)
        for provider in provider_catalog.get("providers", [])
        if isinstance(provider, dict) and str(provider.get("id") or "").strip()
    }
    routing_provider_defs = dict(routing_policy.get("providers") or {})
    burn_class_records: list[dict[str, Any]] = []
    blocked_burn_class_ids: list[str] = []
    degraded_burn_class_ids: list[str] = []
    selected_provider_ids: set[str] = set()
    blocking_provider_ids: set[str] = set()
    degraded_provider_ids: set[str] = set()

    for burn_class in burn_registry.get("burn_classes", []):
        if not isinstance(burn_class, dict):
            continue
        burn_class_id = str(burn_class.get("id") or "").strip()
        if not burn_class_id:
            continue
        routing_chain = [
            str(provider_id).strip()
            for provider_id in burn_class.get("routing_chain", [])
            if str(provider_id).strip()
        ]
        chain_states = [
            _provider_chain_entry_state(provider_id, providers_by_id, routing_provider_defs)
            for provider_id in routing_chain
        ]
        selected_entry = next((entry for entry in chain_states if entry.get("ready")), None)
        primary_entry = chain_states[0] if chain_states else None
        burn_status = "ready"
        if selected_entry is None:
            burn_status = "blocked"
            blocked_burn_class_ids.append(burn_class_id)
            blocking_provider_ids.update(
                str(entry.get("provider_id") or "").strip()
                for entry in chain_states
                if not bool(entry.get("ready")) and str(entry.get("provider_id") or "").strip()
            )
        elif primary_entry and not bool(primary_entry.get("ready")):
            burn_status = "degraded"
            degraded_burn_class_ids.append(burn_class_id)
            degraded_provider_ids.add(str(primary_entry.get("provider_id") or "").strip())

        if selected_entry and str(selected_entry.get("provider_id") or "").strip():
            selected_provider_ids.add(str(selected_entry.get("provider_id") or "").strip())

        burn_class_records.append(
            {
                "burn_class_id": burn_class_id,
                "status": burn_status,
                "selected_provider_id": str(selected_entry.get("provider_id") or "").strip() if selected_entry else None,
                "selected_provider_label": str(selected_entry.get("label") or "").strip() if selected_entry else None,
                "primary_provider_id": str(primary_entry.get("provider_id") or "").strip() if primary_entry else None,
                "primary_provider_ready": bool(primary_entry.get("ready")) if primary_entry else False,
                "blocking_reason": None
                if burn_status == "ready"
                else (str(primary_entry.get("blocking_reason") or "").strip() if primary_entry else "no_eligible_provider"),
                "chain": chain_states,
            }
        )

    blocked_count = len(blocked_burn_class_ids)
    degraded_count = len(degraded_burn_class_ids)
    ready_count = sum(1 for record in burn_class_records if record["status"] == "ready")
    local_compute_capacity = _local_compute_capacity_detail(quota_truth, capacity_telemetry)
    if blocked_count:
        status = "blocked"
    elif degraded_count:
        status = "degraded"
    else:
        status = "ready"

    return {
        "status": status,
        "ready_for_live_compounding": blocked_count == 0,
        "provider_elasticity_limited": int(provider_gate_detail.get("blocking_provider_count") or 0) > 0,
        "burn_class_count": len(burn_class_records),
        "ready_burn_class_count": ready_count,
        "degraded_burn_class_count": degraded_count,
        "blocked_burn_class_count": blocked_count,
        "blocking_burn_class_ids": blocked_burn_class_ids,
        "degraded_burn_class_ids": degraded_burn_class_ids,
        "selected_provider_ids": sorted(selected_provider_ids),
        "blocking_provider_ids": sorted(provider_id for provider_id in blocking_provider_ids if provider_id),
        "degraded_provider_ids": sorted(provider_id for provider_id in degraded_provider_ids if provider_id),
        "slot_aware_ready_for_harvest": bool(local_compute_capacity.get("idle_harvest_slots_open")),
        "local_compute_capacity": local_compute_capacity,
        "capacity_harvest_summary": _build_capacity_harvest_summary(local_compute_capacity),
        "records": burn_class_records,
    }


def _is_dispatchable_queue_item(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "").strip().lower()
    closure_state = str(item.get("closure_state") or "").strip().lower()
    remote_contract = dict(item.get("remote_contract") or {})
    approval_state = str(remote_contract.get("approval_state") or "").strip().lower()
    mutation_allowed = bool(remote_contract.get("mutation_allowed"))
    lane = str(item.get("lane") or "").strip().lower()
    if status in {"done", "cancelled"}:
        return False
    if closure_state in {"parked", "externally-blocked", "closed"}:
        return False
    if lane not in {"execution", "verification"}:
        return False
    return approval_state == "approved" and mutation_allowed


def _build_safe_surface_summary(state: dict[str, Any], queue: dict[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in queue.get("items", []) if isinstance(item, dict)]
    dispatchable = [item for item in items if _is_dispatchable_queue_item(item)]
    approval_gated = [
        item
        for item in items
        if str(dict(item.get("remote_contract") or {}).get("approval_state") or "").strip().lower() != "approved"
    ]
    blocked = [
        item
        for item in items
        if str(item.get("closure_state") or "").strip().lower() in {"parked", "externally-blocked", "closed"}
    ]
    dispatchable_sorted = sorted(
        dispatchable,
        key=lambda item: (
            -float(dict(item.get("ranking") or {}).get("score") or 0),
            -int(item.get("priority") or 0),
            str(item.get("title") or ""),
        ),
    )
    top_item = dispatchable_sorted[0] if dispatchable_sorted else None
    governed_dispatch = dict(state.get("governed_dispatch") or {})
    return {
        "last_outcome": state.get("last_outcome"),
        "last_success_at": state.get("last_success_at"),
        "current_task_id": state.get("current_task_id"),
        "on_deck_task_id": dict(state.get("on_deck") or {}).get("task_id"),
        "queue_count": len(items),
        "dispatchable_queue_count": len(dispatchable),
        "approval_gated_queue_count": len(approval_gated),
        "blocked_queue_count": len(blocked),
        "current_task_threads": len(dict(state.get("task_threads") or {})),
        "top_dispatchable_task_id": str(top_item.get("id") or "").strip() if top_item else None,
        "top_dispatchable_title": str(top_item.get("title") or "").strip() if top_item else None,
        "governed_dispatch_status": str(governed_dispatch.get("status") or "").strip() or "idle",
        "governed_current_task_id": str(governed_dispatch.get("current_task_id") or "").strip() or None,
        "governed_on_deck_task_id": str(governed_dispatch.get("on_deck_task_id") or "").strip() or None,
    }


def _build_dispatch_authority(
    completion_program: dict[str, Any],
    burn_registry: dict[str, Any],
    routing_policy: dict[str, Any],
    provider_gate_detail: dict[str, Any],
    safe_surface_summary: dict[str, Any],
    autonomous_queue_summary: dict[str, Any],
    provider_catalog: dict[str, Any],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shadow_rollout = dict(burn_registry.get("shadow_rollout") or {})
    dispatch_policy = dict(burn_registry.get("dispatch_policy") or {})
    provider_gate_state = _provider_gate_state(completion_program)
    work_economy_detail = _work_economy_detail(
        provider_catalog=provider_catalog,
        routing_policy=routing_policy,
        burn_registry=burn_registry,
        provider_gate_detail=provider_gate_detail,
        quota_truth=quota_truth,
        capacity_telemetry=capacity_telemetry,
    )
    blockers: list[str] = []
    advisory_blockers: list[str] = []
    if int(shadow_rollout.get("phase") or 0) < 1:
        blockers.append("burn_dispatch_recommend_only")
    if not bool(dispatch_policy.get("ranked_dispatch_enabled")):
        blockers.append("ranked_dispatch_disabled")
    if int(autonomous_queue_summary.get("dispatchable_queue_count") or 0) <= 0:
        blockers.append("no_dispatchable_autonomous_work")
    if provider_gate_state == "external_dependency_blocked":
        advisory_blockers.append(
            f"provider_elasticity_limited:{int(provider_gate_detail.get('blocking_provider_count') or 0)}"
        )
    return {
        "phase": int(shadow_rollout.get("phase") or 0),
        "phase_label": str(shadow_rollout.get("phase_label") or "").strip() or "recommend_only",
        "queue_source": "reports/ralph-loop/latest.json#ranked_autonomous_queue",
        "safe_surface_queue_source": str(dispatch_policy.get("queue_source") or "").strip() or str(SAFE_SURFACE_QUEUE_PATH),
        "ranked_dispatch_enabled": bool(dispatch_policy.get("ranked_dispatch_enabled")),
        "approved_mutation_classes": list(dispatch_policy.get("approved_mutation_classes") or []),
        "approved_work_classes": list(dispatch_policy.get("approved_work_classes") or []),
        "provider_gate_state": provider_gate_state,
        "provider_gate_detail": provider_gate_detail,
        "work_economy_status": str(work_economy_detail.get("status") or "unknown"),
        "work_economy_ready_now": bool(work_economy_detail.get("ready_for_live_compounding")),
        "work_economy_detail": work_economy_detail,
        "capacity_harvest_summary": dict(work_economy_detail.get("capacity_harvest_summary") or {}),
        "dispatchable_queue_count": int(autonomous_queue_summary.get("dispatchable_queue_count") or 0),
        "safe_surface_dispatchable_queue_count": int(safe_surface_summary.get("dispatchable_queue_count") or 0),
        "autonomous_queue_count": int(autonomous_queue_summary.get("queue_count") or 0),
        "top_dispatchable_task_id": autonomous_queue_summary.get("top_dispatchable_task_id"),
        "top_dispatchable_title": autonomous_queue_summary.get("top_dispatchable_title"),
        "governed_dispatch_ready": not blockers,
        "blockers": blockers,
        "advisory_blockers": advisory_blockers,
    }


def _automation_run_outcome(record: dict[str, Any]) -> str:
    result = dict(record.get("result") or {})
    for field in ("validation_passed", "all_passed", "success", "passed"):
        if field in result:
            return "success" if bool(result.get(field)) else "failure"

    if "returncode" in result:
        try:
            return "success" if int(result.get("returncode") or 0) == 0 else "failure"
        except (TypeError, ValueError):
            pass

    status = str(result.get("status") or record.get("status") or "").strip().lower()
    if status in {"passed", "success", "completed", "healthy", "ok"}:
        return "success"
    if status in {"failed", "failure", "blocked", "degraded", "error"}:
        return "failure"
    return "unknown"


def _parse_automation_timestamp(raw_timestamp: str) -> datetime | None:
    value = str(raw_timestamp or '').strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        pass
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _build_automation_feedback_summary(recent_records: list[dict[str, Any]]) -> dict[str, Any]:
    records = [dict(record) for record in recent_records if isinstance(record, dict)]
    outcomes = [_automation_run_outcome(record) for record in records]
    dispatch_feedback = _summarize_recent_dispatch_outcomes(records)
    success_count = sum(1 for outcome in outcomes if outcome == "success")
    failure_count = sum(1 for outcome in outcomes if outcome == "failure")
    recognized_count = success_count + failure_count

    last_success_at = next((record.get("timestamp") for record, outcome in zip(records, outcomes) if outcome == "success"), None)
    last_failure_at = next((record.get("timestamp") for record, outcome in zip(records, outcomes) if outcome == "failure"), None)
    last_record = records[0] if records else {}

    ralph_claims: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("automation_id") or "").strip() != "ralph-loop":
            continue
        result = dict(record.get("result") or {})
        claimed_task_id = str(result.get("claimed_task_id") or "").strip()
        if not claimed_task_id:
            continue
        raw_timestamp = str(record.get("timestamp") or "").strip()
        parsed_timestamp = _parse_automation_timestamp(raw_timestamp)
        dispatch_execution_status = str(result.get("dispatch_execution_status") or "").strip()
        dispatch_outcome = str(result.get("dispatch_outcome") or "").strip()
        no_new_delta = dispatch_execution_status in {"already_dispatched", "spin_detected"} or (dispatch_outcome == "claimed" and not str(result.get("dispatched_task_id") or "").strip())
        ralph_claims.append(
            {
                "task_id": claimed_task_id,
                "timestamp": parsed_timestamp,
                "dispatch_outcome": dispatch_outcome,
                "dispatch_execution_status": dispatch_execution_status,
                "no_new_delta": no_new_delta,
            }
        )

    latest_claim = ralph_claims[0] if ralph_claims else {}
    latest_task_id = str(latest_claim.get("task_id") or "").strip() or None
    latest_timestamp = latest_claim.get("timestamp") if isinstance(latest_claim.get("timestamp"), datetime) else None
    same_task_claims_24h = 0
    same_task_claims_12h = 0
    consecutive_no_change_runs = 0
    if latest_task_id and latest_timestamp:
        for claim in ralph_claims:
            if claim.get("task_id") != latest_task_id:
                continue
            claim_ts = claim.get("timestamp")
            if not isinstance(claim_ts, datetime):
                continue
            age_seconds = (latest_timestamp - claim_ts).total_seconds()
            if age_seconds <= 24 * 3600 and claim.get("no_new_delta"):
                same_task_claims_24h += 1
            if age_seconds <= 12 * 3600 and claim.get("no_new_delta"):
                same_task_claims_12h += 1
        for claim in ralph_claims:
            if claim.get("task_id") == latest_task_id and claim.get("no_new_delta"):
                consecutive_no_change_runs += 1
                continue
            break

    anti_spin_state = "spin_detected" if (same_task_claims_24h >= 3 or same_task_claims_12h >= 2) else "clear"
    changed_last_run = None if not ralph_claims else (not bool(latest_claim.get("no_new_delta")))

    if not records:
        feedback_state = "quiet"
    elif anti_spin_state == "spin_detected":
        feedback_state = "spin_detected"
    elif failure_count and not success_count:
        feedback_state = "degraded"
    elif failure_count:
        feedback_state = "mixed"
    else:
        feedback_state = "healthy"

    recent_no_delta_task_ids: list[str] = []
    seen_task_ids: set[str] = set()
    for claim in ralph_claims:
        task_id = str(claim.get("task_id") or "").strip()
        if not task_id or not claim.get("no_new_delta") or task_id in seen_task_ids:
            continue
        seen_task_ids.add(task_id)
        recent_no_delta_task_ids.append(task_id)

    last_real_delta_claim = next((claim for claim in ralph_claims if not claim.get("no_new_delta")), {})
    last_real_delta_timestamp = last_real_delta_claim.get("timestamp")

    return {
        "source_stream": "athanor:automation:runs",
        "recent_run_count": len(records),
        "recognized_run_count": recognized_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "unknown_count": len(records) - recognized_count,
        "last_outcome": outcomes[0] if outcomes else "unknown",
        "last_recorded_at": last_record.get("timestamp"),
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "last_automation_id": last_record.get("automation_id"),
        "last_lane": last_record.get("lane"),
        "last_action_class": last_record.get("action_class"),
        "feedback_state": feedback_state,
        "dispatch_last_outcome": dispatch_feedback.get("last_outcome"),
        "dispatch_last_success_at": dispatch_feedback.get("last_success_at"),
        "recent_dispatch_outcome_count": dispatch_feedback.get("recent_dispatch_outcome_count", 0),
        "recent_dispatch_outcomes": dispatch_feedback.get("recent_dispatch_outcomes", []),
        "recent_no_delta_task_ids": recent_no_delta_task_ids,
        "last_real_delta_task_id": str(last_real_delta_claim.get("task_id") or "").strip() or None,
        "last_real_delta_at": last_real_delta_timestamp.isoformat() if isinstance(last_real_delta_timestamp, datetime) else None,
        "consecutive_no_change_runs": consecutive_no_change_runs,
        "changed_last_run": changed_last_run,
        "anti_spin_state": anti_spin_state,
        "anti_spin_same_task_id": latest_task_id,
        "anti_spin_same_task_claims_12h": same_task_claims_12h,
        "anti_spin_same_task_claims_24h": same_task_claims_24h,
        "anti_spin_escalation": "redirect_or_require_review" if anti_spin_state == "spin_detected" else None,
    }


async def _capture_automation_feedback_and_emit(
    record: AutomationRunRecord,
    *,
    limit: int = AUTOMATION_FEEDBACK_RECENT_LIMIT,
) -> tuple[dict[str, Any], Any]:
    emit_result = await emit_automation_run_record(record)
    recent_records = await read_recent_automation_run_records(limit=limit)
    summary = _build_automation_feedback_summary(recent_records)
    return summary, emit_result


def _commands_for_workstream(workstream: dict[str, Any]) -> list[list[str]]:
    next_action_family = str(workstream.get("next_action_family") or "").strip()
    if next_action_family in NEXT_ACTION_FAMILY_COMMANDS:
        return NEXT_ACTION_FAMILY_COMMANDS[next_action_family]
    loop_family = str(workstream.get("loop_family") or "").strip()
    return LOOP_FAMILY_NEXT_COMMANDS.get(loop_family, [])


def _command_surface_label(command: list[str]) -> str | None:
    if not command:
        return None
    return subprocess.list2cmdline(command)


def _workstream_value_class(workstream_id: str, blocker_type: str, next_action_family: str) -> str:
    if blocker_type == "external_dependency" or workstream_id == "provider-and-secret-remediation":
        return "provider_auth_drift"
    if workstream_id in {
        "authority-and-mainline",
        "deployment-authority-reconciliation",
        "dispatch-and-work-economy-closure",
    }:
        return "dispatch_truth_drift"
    if workstream_id == "capacity-and-harvest-truth":
        return "capacity_truth_drift"
    if workstream_id == "validation-and-publication":
        return "failing_eval_or_validator"
    if workstream_id in {
        "runtime-sync-and-governed-packets",
        "graphrag-operational-hardening",
        "goose-shell-boundary-evidence",
    }:
        return "promotion_wave_closure"
    if workstream_id in {"portfolio-and-source-reconciliation", "tenant-architecture-and-classification"}:
        return "secondary_tenant_or_product_work"
    if next_action_family in {"monitoring_truth_narrowing", "capacity_truth_and_harvest_admission"}:
        return "capacity_truth_drift"
    return "repo_safe_system_hardening"


def _preferred_lane_family(value_class: str, workstream: dict[str, Any]) -> str:
    mapping = {
        "provider_auth_drift": "provider_truth_repair",
        "capacity_truth_drift": "capacity_truth_repair",
        "dispatch_truth_drift": "dispatch_truth_repair",
        "promotion_wave_closure": "promotion_wave_closure",
        "failing_eval_or_validator": "validation_and_checkpoint",
        "repo_safe_system_hardening": "repo_safe_repair",
        "secondary_tenant_or_product_work": "classification_followthrough",
    }
    return mapping.get(value_class, str(workstream.get("loop_family") or "repo_safe_repair_planning"))


def _approved_mutation_class(workstream: dict[str, Any], commands: list[list[str]]) -> str:
    if bool(workstream.get("approval_required")):
        return "approval_required"
    if commands and any("--check" in token for command in commands for token in command):
        return "auto_read_only"
    if str(workstream.get("next_action_family") or "").strip() == "validation_and_checkpoint":
        return "auto_read_only"
    return "auto_harvest"


def _autonomous_ranking_score(
    *,
    value_class: str,
    priority: str,
    evidence_state: str,
    dispatchable: bool,
    blocker_type: str,
    slot_capacity_bonus: float = 0.0,
) -> float:
    priority_bonus = {"critical": 120, "high": 80, "medium": 45, "low": 20}.get(priority, 20)
    evidence_bonus = {"stale_evidence": 120, "missing_evidence": 140, "fresh": 35}.get(evidence_state, 35)
    dispatch_bonus = 75 if dispatchable else 0
    blocker_penalty = 40 if blocker_type == "external_dependency" else 0
    return float(
        AUTONOMOUS_VALUE_CLASS_ORDER.get(value_class, 500)
        + priority_bonus
        + evidence_bonus
        + dispatch_bonus
        + slot_capacity_bonus
        - blocker_penalty
    )


def _slot_capacity_bonus_for_workstream(workstream_id: str, local_compute_capacity: dict[str, Any]) -> float:
    if not bool(local_compute_capacity.get("present")):
        return 0.0
    sample_posture = str(local_compute_capacity.get("sample_posture") or "").strip()
    harvestable_slot_count = int(local_compute_capacity.get("harvestable_scheduler_slot_count") or 0)
    scheduler_slot_count = int(local_compute_capacity.get("scheduler_slot_count") or 0)
    queue_depth = int(local_compute_capacity.get("scheduler_queue_depth") or 0)
    active_zones = sum(
        1 for count in dict(local_compute_capacity.get("harvestable_by_zone") or {}).values() if int(count or 0) > 0
    )
    if scheduler_slot_count <= 0:
        return 0.0
    if workstream_id == "capacity-and-harvest-truth":
        bonus = 35.0
        if harvestable_slot_count > 0:
            if sample_posture == "scheduler_projection_backed":
                bonus += 80.0 + float(min(active_zones, 3) * 8)
            else:
                bonus += 140.0 + float(min(active_zones, 3) * 10)
        if queue_depth == 0 and harvestable_slot_count > 0:
            bonus += 5.0 if sample_posture == "scheduler_projection_backed" else 20.0
        return bonus
    if workstream_id == "dispatch-and-work-economy-closure":
        bonus = 25.0
        if harvestable_slot_count > 0:
            bonus += 125.0 + float(min(active_zones, 3) * 12)
        if queue_depth == 0 and harvestable_slot_count > 0:
            bonus += 30.0
        if sample_posture == "scheduler_projection_backed" and harvestable_slot_count > 0:
            bonus += 35.0
        return bonus
    return 0.0


def _build_workstream_autonomous_items(
    workstream_rows: list[dict[str, Any]],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    local_compute_capacity = _local_compute_capacity_detail(quota_truth, capacity_telemetry)
    for row in workstream_rows:
        workstream = dict(row.get("workstream") or {})
        workstream_id = str(workstream.get("id") or "").strip()
        if not workstream_id:
            continue
        execution_state = str(workstream.get("execution_state") or "").strip()
        if execution_state in TERMINAL_EXECUTION_STATES:
            continue
        blocker_type = str(workstream.get("blocker_type") or "none").strip()
        commands = _commands_for_workstream(workstream)
        proof_surface = _command_surface_label(commands[0]) if commands else None
        evidence_artifacts = [str(item) for item in workstream.get("evidence_artifacts") or [] if str(item).strip()]
        if not proof_surface and evidence_artifacts:
            proof_surface = evidence_artifacts[0]
        value_class = _workstream_value_class(
            workstream_id=workstream_id,
            blocker_type=blocker_type,
            next_action_family=str(workstream.get("next_action_family") or "").strip(),
        )
        dispatchable = not bool(workstream.get("approval_required")) and blocker_type != "external_dependency"
        blocking_reason = None if dispatchable else (
            "external_dependency_blocked" if blocker_type == "external_dependency" else "approval_required"
        )
        slot_capacity_bonus = _slot_capacity_bonus_for_workstream(workstream_id, local_compute_capacity)
        ranking_score = _autonomous_ranking_score(
            value_class=value_class,
            priority=str(workstream.get("priority") or "low").strip().lower(),
            evidence_state=str(dict(row.get("evidence_state") or {}).get("state") or "fresh"),
            dispatchable=dispatchable,
            blocker_type=blocker_type,
            slot_capacity_bonus=slot_capacity_bonus,
        )
        capacity_signal = (
            local_compute_capacity
            if workstream_id in {"capacity-and-harvest-truth", "dispatch-and-work-economy-closure"}
            and bool(local_compute_capacity.get("present"))
            else None
        )
        rows.append(
            {
                "id": f"workstream:{workstream_id}",
                "task_id": f"workstream:{workstream_id}",
                "title": str(workstream.get("title") or workstream_id),
                "repo": str(REPO_ROOT),
                "source_type": "workstream",
                "workstream_id": workstream_id,
                "value_class": value_class,
                "risk_class": "medium" if blocker_type == "external_dependency" else "low",
                "approved_mutation_class": _approved_mutation_class(workstream, commands),
                "preferred_lane_family": _preferred_lane_family(value_class, workstream),
                "fallback_lane_family": "operator_follow_through",
                "proof_command_or_eval_surface": proof_surface,
                "closure_rule": (
                    f"Advance {workstream_id} until {str(workstream.get('next_action_family') or 'the next action family')} is no longer leading."
                ),
                "ranking_score": ranking_score,
                "status": str(workstream.get("status") or execution_state or "active"),
                "dispatchable": dispatchable,
                "blocking_reason": blocking_reason,
                "evidence_state": str(dict(row.get("evidence_state") or {}).get("state") or "fresh"),
                "priority": str(workstream.get("priority") or "low").strip().lower(),
                "capacity_signal": capacity_signal,
            }
        )
    return rows


def _build_provider_gate_item(
    completion_program: dict[str, Any],
    provider_gate_detail: dict[str, Any],
) -> list[dict[str, Any]]:
    provider_gate_state = _provider_gate_state(completion_program)
    blocker_count = int(provider_gate_detail.get("blocking_provider_count") or 0)
    if provider_gate_state != "external_dependency_blocked" or blocker_count <= 0:
        return []
    blocking_provider_ids = list(provider_gate_detail.get("blocking_provider_ids") or [])
    blocker_suffix = (
        f"{blocker_count} active provider lane{'s' if blocker_count != 1 else ''}"
        if blocker_count
        else "provider gate"
    )
    return [
        {
            "id": "gate:provider_gate",
            "task_id": "gate:provider_gate",
            "title": f"Repair or explicitly demote {blocker_suffix}",
            "repo": str(REPO_ROOT),
            "source_type": "reconciliation_gate",
            "workstream_id": "provider-and-secret-remediation",
            "value_class": "provider_auth_drift",
            "risk_class": "high",
            "approved_mutation_class": "approval_required",
            "preferred_lane_family": "provider_truth_repair",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "reports/truth-inventory/provider-usage-evidence.json",
            "closure_rule": "Move provider_gate out of external_dependency_blocked or explicitly demote every failing active API lane.",
            "ranking_score": float(AUTONOMOUS_VALUE_CLASS_ORDER["provider_auth_drift"] + 60),
            "status": "blocked",
            "dispatchable": False,
            "blocking_reason": (
                "external_dependency_blocked:" + ",".join(blocking_provider_ids)
                if blocking_provider_ids
                else "external_dependency_blocked"
            ),
            "evidence_state": "stale_evidence",
            "priority": "critical",
            "blocking_provider_ids": blocking_provider_ids,
            "excluded_provider_ids": list(provider_gate_detail.get("excluded_provider_ids") or []),
        }
    ]


def _build_safe_surface_autonomous_items(queue: dict[str, Any]) -> list[dict[str, Any]]:
    items = [dict(item) for item in queue.get("items", []) if isinstance(item, dict)]
    candidates = [item for item in items if _is_dispatchable_queue_item(item)]
    rows: list[dict[str, Any]] = []
    for item in candidates:
        remote_contract = dict(item.get("remote_contract") or {})
        approved_mutation_classes = list(remote_contract.get("approved_mutation_classes") or [])
        rows.append(
            {
                "id": str(item.get("id") or "").strip(),
                "task_id": str(item.get("id") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "repo": str(item.get("repo") or "").strip(),
                "source_type": "safe_surface_queue",
                "value_class": str(item.get("kind") or "").strip() or "bounded_implementation",
                "risk_class": str(item.get("risk") or "").strip() or "unknown",
                "approved_mutation_class": approved_mutation_classes[0] if approved_mutation_classes else "auto_read_only",
                "preferred_lane_family": "safe_surface_execution",
                "fallback_lane_family": "operator_follow_through",
                "proof_command_or_eval_surface": str(item.get("proof_cmd") or "").strip() or None,
                "closure_rule": (
                    list(item.get("acceptance") or [])[0]
                    if list(item.get("acceptance") or [])
                    else str(item.get("closure_policy") or "").strip() or None
                ),
                "ranking_score": float(dict(item.get("ranking") or {}).get("score") or 0),
                "status": str(item.get("status") or "").strip(),
                "dispatchable": True,
                "blocking_reason": None,
                "evidence_state": "fresh",
                "priority": "medium",
            }
        )
    return rows


def _burn_class_value_class(burn_class_id: str) -> str:
    if burn_class_id in {"local_bulk_sovereign", "overnight_harvest"}:
        return "capacity_truth_drift"
    if burn_class_id == "promotion_eval":
        return "promotion_wave_closure"
    return "dispatch_truth_drift"


def _burn_class_lane_family(burn_class_id: str) -> str:
    if burn_class_id in {"local_bulk_sovereign", "overnight_harvest"}:
        return "capacity_truth_repair"
    if burn_class_id == "promotion_eval":
        return "promotion_wave_closure"
    return "dispatch_truth_repair"


def _build_burn_class_autonomous_items(
    burn_registry: dict[str, Any],
    work_economy_detail: dict[str, Any],
) -> list[dict[str, Any]]:
    burn_class_defs = {
        str(item.get("id") or "").strip(): dict(item)
        for item in burn_registry.get("burn_classes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    local_compute_capacity = dict(work_economy_detail.get("local_compute_capacity") or {})
    harvestable_slots = int(local_compute_capacity.get("harvestable_scheduler_slot_count") or 0)
    rows: list[dict[str, Any]] = []

    for record in work_economy_detail.get("records", []):
        if not isinstance(record, dict):
            continue
        burn_class_id = str(record.get("burn_class_id") or "").strip()
        if not burn_class_id:
            continue
        burn_class = burn_class_defs.get(burn_class_id, {})
        status = str(record.get("status") or "blocked").strip().lower()
        dispatchable = status in {"ready", "degraded"}
        value_class = _burn_class_value_class(burn_class_id)
        slot_capacity_bonus = 0.0
        if burn_class_id in {"local_bulk_sovereign", "overnight_harvest", "promotion_eval"} and harvestable_slots > 0:
            slot_capacity_bonus = float(min(harvestable_slots, 3) * 12)
        ranking_score = _autonomous_ranking_score(
            value_class=value_class,
            priority="medium" if dispatchable else "high",
            evidence_state="fresh",
            dispatchable=dispatchable,
            blocker_type="none" if dispatchable else "external_dependency",
            slot_capacity_bonus=slot_capacity_bonus,
        ) - 120.0
        rows.append(
            {
                "id": f"burn_class:{burn_class_id}",
                "task_id": f"burn_class:{burn_class_id}",
                "title": str(burn_class.get("label") or burn_class_id.replace("_", " ").title()),
                "repo": str(REPO_ROOT),
                "source_type": "burn_class",
                "burn_class_id": burn_class_id,
                "value_class": value_class,
                "risk_class": "low" if dispatchable else "medium",
                "approved_mutation_class": "auto_harvest" if dispatchable else "approval_required",
                "preferred_lane_family": _burn_class_lane_family(burn_class_id),
                "fallback_lane_family": "operator_follow_through",
                "proof_command_or_eval_surface": (
                    "reports/truth-inventory/capacity-telemetry.json"
                    if burn_class_id in {"local_bulk_sovereign", "overnight_harvest", "promotion_eval"}
                    else "reports/truth-inventory/quota-truth.json"
                ),
                "closure_rule": (
                    f"Keep burn class {burn_class_id} on an eligible routed lane and record ordinary execution evidence."
                ),
                "ranking_score": ranking_score,
                "status": status,
                "dispatchable": dispatchable,
                "blocking_reason": None if dispatchable else str(record.get("blocking_reason") or "no_eligible_provider"),
                "evidence_state": "fresh",
                "priority": "medium" if dispatchable else "high",
                "selected_provider_id": str(record.get("selected_provider_id") or "").strip() or None,
                "selected_provider_label": str(record.get("selected_provider_label") or "").strip() or None,
                "max_concurrency": int(burn_class.get("max_concurrency") or 0) or None,
                "approved_task_families": [
                    str(item).strip()
                    for item in burn_class.get("approved_task_families", [])
                    if str(item).strip()
                ],
                "reserve_rule": str(burn_class.get("reserve_rule") or "").strip() or None,
                "capacity_signal": local_compute_capacity if burn_class_id in {"local_bulk_sovereign", "overnight_harvest"} else None,
            }
        )
    return rows



def _build_publication_deferred_family_items(publication_queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in publication_queue.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("id") or "").strip()
        execution_class = str(family.get("execution_class") or "").strip()
        if not family_id or execution_class != "cash_now":
            continue
        sample_paths = [str(item).strip() for item in family.get("sample_paths", []) if str(item).strip()]
        path_hints = [str(item).strip() for item in family.get("path_hints", []) if str(item).strip()]
        owner_workstreams = [str(item).strip() for item in family.get("owner_workstreams", []) if str(item).strip()]
        title = str(family.get("title") or family_id).strip()
        proof_surface = sample_paths[0] if sample_paths else (path_hints[0] if path_hints else "docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md")
        preferred_lane_family = "publication_freeze" if "validation-and-publication" in owner_workstreams else "steady_state_maintenance"
        rows.append(
            {
                "task_id": f"deferred_family:{family_id}",
                "title": title,
                "repo": str(REPO_ROOT),
                "source_type": "publication_deferred_family",
                "deferred_family_id": family_id,
                "workstream_id": owner_workstreams[0] if owner_workstreams else None,
                "value_class": "repo_safe_system_hardening",
                "risk_class": "medium",
                "approved_mutation_class": "auto_read_only",
                "preferred_lane_family": preferred_lane_family,
                "fallback_lane_family": "publication_freeze",
                "proof_command_or_eval_surface": proof_surface,
                "closure_rule": str(family.get("next_action") or family.get("success_condition") or "").strip() or None,
                "success_condition": str(family.get("success_condition") or "").strip() or None,
                "ranking_score": _autonomous_ranking_score(
                    value_class="repo_safe_system_hardening",
                    priority="high",
                    evidence_state="fresh",
                    dispatchable=True,
                    blocker_type="none",
                ) + float(max(0, 12 - int(family.get("execution_rank") or 12))),
                "status": "deferred_ready",
                "dispatchable": True,
                "blocking_reason": None,
                "evidence_state": "fresh",
                "priority": "high",
                "match_count": int(family.get("match_count") or 0),
                "path_hints": path_hints,
                "sample_paths": sample_paths,
                "disposition": str(family.get("disposition") or "").strip() or None,
                "next_action": str(family.get("next_action") or "").strip() or None,
            }
        )
    return rows


def _repo_git_probe_context(path: Path) -> tuple[list[str], str]:
    normalized = path.as_posix()
    if normalized.startswith('/mnt/c/'):
        windows_path = 'C:\\' + normalized.removeprefix('/mnt/c/').replace('/', '\\')
        for candidate in WINDOWS_GIT_CANDIDATES:
            if candidate.exists():
                return [str(candidate)], windows_path
    return ['git'], normalized
def _repo_has_material_worktree_delta(continuity_policy: dict[str, Any]) -> bool:
    return bool(_repo_material_worktree_delta_paths(continuity_policy))


def _apply_continuity_suppression(
    rows: list[dict[str, Any]],
    continuity_state: dict[str, Any],
    *,
    material_repo_delta_reopens_live_tranches: bool,
    continuity_policy: dict[str, Any],
    repo_delta_paths: list[str],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    suppressed_until_by_task = {
        str(task_id).strip(): str(expiry).strip()
        for task_id, expiry in dict(continuity_state.get("suppressed_until_by_task") or {}).items()
        if str(task_id).strip() and str(expiry).strip()
    }
    updated_rows: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        task_id = str(item.get("task_id") or "").strip()
        suppressed_until = suppressed_until_by_task.get(task_id)
        reopen_detail = _continuity_repo_delta_reopen_detail(
            item,
            enabled=material_repo_delta_reopens_live_tranches,
            continuity_policy=continuity_policy,
            repo_delta_paths=repo_delta_paths,
        )
        no_delta_detail = _workstream_repo_side_no_delta_detail(
            item,
            continuity_policy,
            list(reopen_detail.get("matched_repo_delta_paths") or []),
            quota_truth,
            capacity_telemetry,
        )
        reopened_by_repo_delta = bool(reopen_detail.get("reopened"))
        if reopened_by_repo_delta:
            suppressed_until = None
        repo_side_no_delta = bool(no_delta_detail.get("repo_side_no_delta"))
        repo_side_no_delta_suppressed = repo_side_no_delta and not reopened_by_repo_delta
        item.update(no_delta_detail)
        item["reopened_by_repo_delta"] = reopened_by_repo_delta
        item["reopen_reason_scope"] = reopen_detail.get("reopen_reason_scope")
        item["reopen_reason_paths"] = list(reopen_detail.get("matched_repo_delta_paths") or [])
        item["suppressed_by_continuity"] = bool(suppressed_until) or repo_side_no_delta_suppressed
        item["suppressed_until"] = suppressed_until
        item["suppression_reason"] = (
            "repo_side_no_delta"
            if repo_side_no_delta_suppressed
            else "recent_no_delta_ttl" if suppressed_until else None
        )
        if repo_side_no_delta_suppressed:
            item["rotation_ready"] = True
        updated_rows.append(item)
    return updated_rows


def _build_ranked_autonomous_queue(
    queue: dict[str, Any],
    workstream_rows: list[dict[str, Any]],
    completion_program: dict[str, Any],
    burn_registry: dict[str, Any],
    work_economy_detail: dict[str, Any],
    provider_gate_detail: dict[str, Any],
    quota_truth: dict[str, Any],
    publication_queue: dict[str, Any],
    continuity_state: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    workstream_items = _build_workstream_autonomous_items(workstream_rows, quota_truth, capacity_telemetry)
    continuity_policy = _continuity_policy(completion_program)
    repo_delta_paths = (
        _repo_material_worktree_delta_paths(continuity_policy)
        if bool(continuity_policy.get("material_repo_delta_reopens_validation_publication"))
        else []
    )
    material_repo_delta_reopens_live_tranches = bool(repo_delta_paths)
    workstream_items = _apply_continuity_suppression(
        workstream_items,
        continuity_state,
        material_repo_delta_reopens_live_tranches=material_repo_delta_reopens_live_tranches,
        continuity_policy=continuity_policy,
        repo_delta_paths=repo_delta_paths,
        quota_truth=quota_truth,
        capacity_telemetry=capacity_telemetry,
    )
    has_unsuppressed_dispatchable_workstream = any(
        _queue_item_effectively_dispatchable(item) for item in workstream_items
    )
    rows = [
        *_build_burn_class_autonomous_items(burn_registry, work_economy_detail),
        *_build_safe_surface_autonomous_items(queue),
        *_build_provider_gate_item(completion_program, provider_gate_detail),
    ]
    validation_publication_is_unsuppressed_dispatchable = any(
        isinstance(item, dict)
        and _queue_item_effectively_dispatchable(item)
        and (
            str(item.get("workstream_id") or "").strip() == "validation-and-publication"
            or str(item.get("id") or "").strip() in {"validation-and-publication", "workstream:validation-and-publication"}
        )
        for item in workstream_items
    )
    if (
        continuity_policy.get("cash_now_deferred_families_are_autonomous_inputs")
        and (
            not continuity_policy.get("cash_now_requires_no_unsuppressed_workstream")
            or not has_unsuppressed_dispatchable_workstream
            or validation_publication_is_unsuppressed_dispatchable
        )
    ):
        rows.extend(_build_publication_deferred_family_items(publication_queue))
    rows = _apply_continuity_suppression(
        rows,
        continuity_state,
        material_repo_delta_reopens_live_tranches=material_repo_delta_reopens_live_tranches,
        continuity_policy=continuity_policy,
        repo_delta_paths=repo_delta_paths,
        quota_truth=quota_truth,
        capacity_telemetry=capacity_telemetry,
    )
    rows = [*workstream_items, *rows]
    rows.sort(
        key=lambda item: (
            0 if _queue_item_effectively_dispatchable(item) else 1,
            _queue_source_precedence_key(item, continuity_policy),
            -float(item.get("ranking_score") or 0),
            str(item.get("title") or ""),
        )
    )
    return rows[:12]


def _build_autonomous_queue_summary(ranked_autonomous_queue: list[dict[str, Any]]) -> dict[str, Any]:
    dispatchable = [item for item in ranked_autonomous_queue if _queue_item_effectively_dispatchable(item)]
    suppressed = [item for item in ranked_autonomous_queue if bool(item.get("suppressed_by_continuity"))]
    blocked = [
        item
        for item in ranked_autonomous_queue
        if not bool(item.get("dispatchable")) and not bool(item.get("suppressed_by_continuity"))
    ]
    top_dispatchable = dispatchable[0] if dispatchable else None
    return {
        "queue_count": len(ranked_autonomous_queue),
        "dispatchable_queue_count": len(dispatchable),
        "blocked_queue_count": len(blocked),
        "suppressed_queue_count": len(suppressed),
        "top_dispatchable_task_id": str(top_dispatchable.get("task_id") or "").strip() if top_dispatchable else None,
        "top_dispatchable_title": str(top_dispatchable.get("title") or "").strip() if top_dispatchable else None,
        "top_dispatchable_value_class": str(top_dispatchable.get("value_class") or "").strip() if top_dispatchable else None,
        "top_dispatchable_lane_family": (
            str(top_dispatchable.get("preferred_lane_family") or "").strip() if top_dispatchable else None
        ),
    }


def _approval_matrix_classes(approval_matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    classes: dict[str, dict[str, Any]] = {}
    for entry in approval_matrix.get("classes", []):
        if not isinstance(entry, dict):
            continue
        class_id = str(entry.get("id") or "").strip()
        if not class_id:
            continue
        classes[class_id] = dict(entry)
    return classes


def _eligible_governed_dispatch_items(
    ranked_autonomous_queue: list[dict[str, Any]],
    dispatch_authority: dict[str, Any],
    approval_matrix: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    approval_classes = _approval_matrix_classes(approval_matrix)
    approved_mutation_classes = {
        str(item).strip()
        for item in dispatch_authority.get("approved_mutation_classes") or []
        if str(item).strip() and str(item).strip() in approval_classes
    }
    if not bool(dispatch_authority.get("governed_dispatch_ready")) or not approved_mutation_classes:
        return [], approval_classes

    eligible: list[dict[str, Any]] = []
    work_economy_ready_now = bool(dispatch_authority.get("work_economy_ready_now"))
    for row in ranked_autonomous_queue:
        item = dict(row)
        if not _queue_item_effectively_dispatchable(item):
            continue
        approved_mutation_class = str(item.get("approved_mutation_class") or "").strip()
        if approved_mutation_class not in approved_mutation_classes:
            continue
        if approved_mutation_class == "auto_harvest" and not work_economy_ready_now:
            continue
        eligible.append(item)
    return eligible, approval_classes


def _prior_spin_redirect_task_id(
    previous_ralph_report: dict[str, Any],
    *,
    current_task_id: str | None,
) -> str | None:
    report = dict(previous_ralph_report or {})
    previous_claim = dict(report.get("governed_dispatch_claim") or {})
    automation_feedback = dict(report.get("automation_feedback_summary") or {})
    dispatch_authority = dict(report.get("dispatch_authority") or {})

    anti_spin_state = (
        str(automation_feedback.get("anti_spin_state") or "").strip()
        or str(dispatch_authority.get("anti_spin_state") or "").strip()
    )
    if anti_spin_state != "spin_detected":
        return None

    previous_task_id = str(previous_claim.get("current_task_id") or "").strip() or None
    if current_task_id and previous_task_id and previous_task_id != current_task_id:
        return None

    redirect_task_id = (
        str(dispatch_authority.get("anti_spin_next_action") or "").strip()
        or str(previous_claim.get("on_deck_task_id") or "").strip()
    )
    if not redirect_task_id or redirect_task_id in {current_task_id, "operator_review_required"}:
        return None
    return redirect_task_id


def _build_governed_dispatch_claim(
    ranked_autonomous_queue: list[dict[str, Any]],
    dispatch_authority: dict[str, Any],
    approval_matrix: dict[str, Any],
    safe_surface_state: dict[str, Any],
    *,
    generated_at: str,
    previous_ralph_report: dict[str, Any] | None = None,
    automation_feedback_summary: dict[str, Any] | None = None,
    continuity_state: dict[str, Any] | None = None,
    reopened_task_ids: set[str] | None = None,
) -> dict[str, Any]:
    eligible_items, approval_classes = _eligible_governed_dispatch_items(
        ranked_autonomous_queue,
        dispatch_authority,
        approval_matrix,
    )
    dispatch_allowed_classes = sorted(
        {
            str(item).strip()
            for item in dispatch_authority.get("approved_mutation_classes") or []
            if str(item).strip() and str(item).strip() in approval_classes
        }
    )
    existing_claim = dict(safe_surface_state.get("governed_dispatch") or {})
    top_item = eligible_items[0] if eligible_items else None
    top_task_id = str((top_item or {}).get("task_id") or "").strip() or None
    suppressed_task_ids = {
        str(task_id).strip()
        for task_id in (
            dict(continuity_state or {}).get("recent_no_delta_task_ids")
            or dict(automation_feedback_summary or {}).get("recent_no_delta_task_ids")
            or []
        )
        if str(task_id).strip()
    }
    suppressed_task_ids.difference_update(
        {
            str(task_id).strip()
            for task_id in (reopened_task_ids or set())
            if str(task_id).strip()
        }
    )
    claim_rotation_reason = None
    if any(
        bool(item.get("dispatchable")) and str(item.get("task_id") or "").strip() in suppressed_task_ids
        for item in ranked_autonomous_queue
    ):
        claim_rotation_reason = "recent_no_delta_suppressed"

    top_task_id = str((top_item or {}).get("task_id") or "").strip() or None
    redirect_task_id = _prior_spin_redirect_task_id(
        dict(previous_ralph_report or {}),
        current_task_id=top_task_id,
    )
    if redirect_task_id and not claim_rotation_reason:
        redirect_index = next(
            (
                index
                for index, item in enumerate(eligible_items)
                if str(item.get("task_id") or "").strip() == redirect_task_id
            ),
            None,
        )
        if redirect_index is not None:
            top_item = eligible_items[redirect_index]
            claim_rotation_reason = "prior_spin_detected"

    remaining_items = [
        item
        for item in eligible_items
        if str(item.get("task_id") or "").strip()
        != str((top_item or {}).get("task_id") or "").strip()
    ]
    on_deck_item = remaining_items[0] if remaining_items else None

    if not top_item:
        return {
            "status": "idle",
            "dispatch_outcome": "idle",
            "claim_source": "reports/ralph-loop/latest.json#ranked_autonomous_queue",
            "observed_at": generated_at,
            "eligible_queue_count": 0,
            "approved_mutation_classes": dispatch_allowed_classes,
            "current_task_id": None,
            "current_task_title": None,
            "current_lane_family": None,
            "repo_side_no_delta": False,
            "rotation_ready": False,
            "reopen_reason_scope": None,
            "no_delta_evidence_refs": [],
            "on_deck_task_id": None,
            "on_deck_task_title": None,
            "claimed_at": None,
            "claim_id": None,
        }

    task_id = str(top_item.get("task_id") or "").strip() or None
    existing_task_id = str(existing_claim.get("current_task_id") or "").strip() or None
    claimed_at = (
        str(existing_claim.get("claimed_at") or "").strip()
        if existing_task_id and existing_task_id == task_id
        else generated_at
    )
    claim_id = (
        str(existing_claim.get("claim_id") or "").strip()
        if existing_task_id and existing_task_id == task_id
        else f"ralph-claim-{generated_at.replace(':', '').replace('-', '').replace('.', '')}-{(task_id or 'task').replace(':', '-').replace('/', '-')}"
    )
    approved_mutation_class = str(top_item.get("approved_mutation_class") or "").strip()
    approval_class = dict(approval_classes.get(approved_mutation_class) or {})
    on_deck = dict(on_deck_item or {})

    return {
        "status": "claimed",
        "dispatch_outcome": "claimed",
        "claim_source": "reports/ralph-loop/latest.json#ranked_autonomous_queue",
        "claim_id": claim_id,
        "claimed_at": claimed_at,
        "observed_at": generated_at,
        "eligible_queue_count": len(eligible_items),
        "approved_mutation_classes": dispatch_allowed_classes,
        "current_task_id": task_id,
        "current_task_title": str(top_item.get("title") or "").strip() or None,
        "current_repo": str(top_item.get("repo") or "").strip() or None,
        "current_source_type": str(top_item.get("source_type") or "").strip() or None,
        "current_workstream_id": str(top_item.get("workstream_id") or "").strip() or None,
        "value_class": str(top_item.get("value_class") or "").strip() or None,
        "risk_class": str(top_item.get("risk_class") or "").strip() or None,
        "approved_mutation_class": approved_mutation_class or None,
        "approved_mutation_label": str(approval_class.get("label") or "").strip() or None,
        "approved_actions": list(approval_class.get("allowed_actions") or []),
        "current_lane_family": str(top_item.get("preferred_lane_family") or "").strip() or None,
        "preferred_lane_family": str(top_item.get("preferred_lane_family") or "").strip() or None,
        "fallback_lane_family": str(top_item.get("fallback_lane_family") or "").strip() or None,
        "proof_command_or_eval_surface": str(top_item.get("proof_command_or_eval_surface") or "").strip() or None,
        "closure_rule": str(top_item.get("closure_rule") or "").strip() or None,
        "blocking_reason": str(top_item.get("blocking_reason") or "").strip() or None,
        "capacity_signal": dict(top_item.get("capacity_signal") or {}),
        "repo_side_no_delta": bool(top_item.get("repo_side_no_delta")),
        "rotation_ready": bool(top_item.get("rotation_ready")),
        "reopen_reason_scope": str(top_item.get("reopen_reason_scope") or "").strip() or None,
        "no_delta_evidence_refs": [
            str(item).strip()
            for item in top_item.get("no_delta_evidence_refs", [])
            if str(item).strip()
        ],
        "on_deck_task_id": str(on_deck.get("task_id") or "").strip() or None,
        "on_deck_task_title": str(on_deck.get("title") or "").strip() or None,
        "on_deck_lane_family": str(on_deck.get("preferred_lane_family") or "").strip() or None,
        "claim_rotation_reason": claim_rotation_reason,
        "claim_rotation_source_task_id": top_task_id if claim_rotation_reason else None,
    }


def _sync_governed_dispatch_state(
    safe_surface_state: dict[str, Any],
    claim: dict[str, Any],
) -> dict[str, Any]:
    updated_state = dict(safe_surface_state)
    updated_state["governed_dispatch"] = dict(claim)
    if str(claim.get("status") or "").strip() == "claimed":
        updated_state["last_governed_dispatch_claimed_task_id"] = claim.get("current_task_id")
        updated_state["last_governed_dispatch_claimed_at"] = claim.get("claimed_at")
    return updated_state


def _build_governed_dispatch_runtime_state(
    claim: dict[str, Any],
    dispatch_authority: dict[str, Any],
    autonomous_queue_summary: dict[str, Any],
    safe_surface_summary: dict[str, Any],
    governed_dispatch_materialization: dict[str, Any],
    governed_dispatch_execution: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    claim_row = dict(claim)
    return {
        "generated_at": generated_at,
        "source_of_truth": "scripts/run_ralph_loop_pass.py",
        "report_path": "reports/truth-inventory/governed-dispatch-state.json",
        "claim_source": str(claim_row.get("claim_source") or "").strip()
        or "reports/ralph-loop/latest.json#ranked_autonomous_queue",
        "status": str(claim_row.get("status") or "").strip() or "idle",
        "dispatch_outcome": (
            str(governed_dispatch_execution.get("dispatch_outcome") or "").strip()
            or str(claim_row.get("dispatch_outcome") or "").strip()
            or "idle"
        ),
        "dispatch_phase_label": str(dispatch_authority.get("phase_label") or "").strip() or None,
        "governed_dispatch_ready": bool(dispatch_authority.get("governed_dispatch_ready")),
        "provider_gate_state": str(dispatch_authority.get("provider_gate_state") or "").strip() or "unknown",
        "work_economy_status": str(dispatch_authority.get("work_economy_status") or "").strip() or "unknown",
        "work_economy_ready_now": bool(dispatch_authority.get("work_economy_ready_now")),
        "capacity_harvest_summary": dict(dispatch_authority.get("capacity_harvest_summary") or {}),
        "queue_count": int(autonomous_queue_summary.get("queue_count") or 0),
        "dispatchable_queue_count": int(autonomous_queue_summary.get("dispatchable_queue_count") or 0),
        "blocked_queue_count": int(autonomous_queue_summary.get("blocked_queue_count") or 0),
        "safe_surface_queue_count": int(safe_surface_summary.get("queue_count") or 0),
        "safe_surface_dispatchable_queue_count": int(safe_surface_summary.get("dispatchable_queue_count") or 0),
        "current_task_id": claim_row.get("current_task_id"),
        "current_task_title": claim_row.get("current_task_title"),
        "current_workstream_id": claim_row.get("current_workstream_id"),
        "current_repo": claim_row.get("current_repo"),
        "current_source_type": claim_row.get("current_source_type"),
        "value_class": claim_row.get("value_class"),
        "risk_class": claim_row.get("risk_class"),
        "approved_mutation_class": claim_row.get("approved_mutation_class"),
        "approved_mutation_label": claim_row.get("approved_mutation_label"),
        "approved_actions": list(claim_row.get("approved_actions") or []),
        "proof_command_or_eval_surface": claim_row.get("proof_command_or_eval_surface"),
        "preferred_lane_family": claim_row.get("preferred_lane_family"),
        "fallback_lane_family": claim_row.get("fallback_lane_family"),
        "closure_rule": claim_row.get("closure_rule"),
        "blocking_reason": claim_row.get("blocking_reason"),
        "claim_id": claim_row.get("claim_id"),
        "claimed_at": claim_row.get("claimed_at"),
        "observed_at": claim_row.get("observed_at"),
        "eligible_queue_count": int(claim_row.get("eligible_queue_count") or 0),
        "on_deck_task_id": claim_row.get("on_deck_task_id"),
        "on_deck_task_title": claim_row.get("on_deck_task_title"),
        "on_deck_lane_family": claim_row.get("on_deck_lane_family"),
        "capacity_signal": dict(claim_row.get("capacity_signal") or {}),
        "repo_side_no_delta": bool(claim_row.get("repo_side_no_delta")),
        "rotation_ready": bool(claim_row.get("rotation_ready")),
        "reopen_reason_scope": str(claim_row.get("reopen_reason_scope") or "").strip() or None,
        "no_delta_evidence_refs": [
            str(item).strip()
            for item in claim_row.get("no_delta_evidence_refs", [])
            if str(item).strip()
        ],
        "top_dispatchable_task_id": autonomous_queue_summary.get("top_dispatchable_task_id"),
        "top_dispatchable_title": autonomous_queue_summary.get("top_dispatchable_title"),
        "top_dispatchable_lane_family": autonomous_queue_summary.get("top_dispatchable_lane_family"),
        "recent_dispatch_outcome_count": int(autonomous_queue_summary.get("recent_dispatch_outcome_count") or 0),
        "last_dispatch_outcome": autonomous_queue_summary.get("last_outcome"),
        "last_dispatch_success_at": autonomous_queue_summary.get("last_success_at"),
        "recent_dispatch_outcomes": list(autonomous_queue_summary.get("recent_dispatch_outcomes") or []),
        "advisory_blockers": list(governed_dispatch_execution.get("advisory_blockers") or []),
        "materialization": dict(governed_dispatch_materialization or {}),
        "execution": dict(governed_dispatch_execution or {}),
        "governed_dispatch_claim": claim_row,
    }


def _matches_governed_dispatch_materialization(
    item: dict[str, Any],
    claim_id: str,
    task_id: str,
    title: str,
) -> bool:
    metadata = dict(item.get("metadata") or {})
    metadata_claim_id = _clean_str(metadata.get("claim_id"))
    metadata_task_id = _clean_str(metadata.get("current_task_id"))
    metadata_source = _clean_str(metadata.get("materialization_source"))
    item_title = _clean_str(item.get("title"))
    prompt = _clean_str(item.get("prompt"))

    if metadata_source == "governed_dispatch_state" and metadata_claim_id and metadata_claim_id == claim_id:
        return True
    if metadata_source == "governed_dispatch_state" and metadata_task_id and metadata_task_id == task_id:
        return True
    return bool(item_title) and item_title == title and prompt.startswith('Advance the governed dispatch claim for "')


def _task_lookup_fields(task_row: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(task_row.get("metadata") or {})
    recovery = dict(metadata.get("recovery") or {})
    retry_lineage = [
        _clean_str(item)
        for item in task_row.get("retry_lineage") or []
        if _clean_str(item)
    ]
    task_source = _clean_str(task_row.get("source")) or _clean_str(metadata.get("source"))
    retry_of_task_id = _clean_str(metadata.get("retry_of")) or (retry_lineage[-1] if retry_lineage else None)
    recovery_event = _clean_str(recovery.get("event")) or None
    recovery_reason = _clean_str(recovery.get("reason")) or None
    previous_error = _clean_str(task_row.get("previous_error"))
    task_status = _clean_str(task_row.get("status")) or None
    restart_recovered = recovery_reason == "server_restart" or "server restart" in previous_error.lower()
    if restart_recovered and _clean_str(task_status).lower() == "stale_lease":
        resilience_state = "restart_interfering"
    elif restart_recovered:
        resilience_state = "restart_recovered"
    else:
        resilience_state = None
    return {
        "task_id": _clean_str(task_row.get("id")) or None,
        "task_status": task_status,
        "task_source": task_source or None,
        "retry_of_task_id": retry_of_task_id or None,
        "retry_count": int(task_row.get("retry_count") or (len(retry_lineage) if retry_lineage else 0) or 0),
        "retry_lineage_depth": len(retry_lineage),
        "recovery_event": recovery_event,
        "recovery_reason": recovery_reason,
        "resilience_state": resilience_state,
        "governor_reason": _clean_str(metadata.get("governor_decision")) or None,
        "governor_level": (
            _clean_str(metadata.get("governor_autonomy_level"))
            or _clean_str(metadata.get("governor_level"))
            or None
        ),
    }


def _governed_dispatch_task_profile(
    *,
    owner_agent: str,
    task_class: str | None = None,
    workload_class: str | None = None,
) -> dict[str, str]:
    normalized_task_class = _clean_str(task_class)
    if not normalized_task_class or normalized_task_class == "private_automation":
        normalized_task_class = GOVERNED_DISPATCH_TASK_CLASS_DEFAULTS.get(
            _clean_str(owner_agent),
            "async_backlog_execution",
        )

    normalized_workload_class = _clean_str(workload_class)
    if not normalized_workload_class or normalized_workload_class == "private_automation":
        normalized_workload_class = GOVERNED_DISPATCH_WORKLOAD_ALIASES.get(
            normalized_task_class,
            "coding_implementation",
        )

    return {
        "task_class": normalized_task_class,
        "workload_class": normalized_workload_class,
    }


def _governed_dispatch_task_requires_repair(task_row: dict[str, Any]) -> bool:
    metadata = dict(task_row.get("metadata") or {})
    if _clean_str(metadata.get("materialization_source")) != "governed_dispatch_state":
        return False
    task_status = _clean_str(task_row.get("status")).lower()
    if task_status == "stale_lease":
        return True
    if task_status == "failed":
        failure = dict(metadata.get("failure") or {})
        if bool(metadata.get("_autonomy_managed")) and bool(failure.get("retry_eligible")):
            return True
        lease = dict(metadata.get("execution_lease") or {})
        provider = _clean_str(lease.get("provider")).lower()
        fallback = [_clean_str(item).lower() for item in lease.get("fallback") or [] if _clean_str(item)]
        task_class = _clean_str(metadata.get("task_class")).lower()
        workload_class = _clean_str(metadata.get("workload_class")).lower()
        return (
            task_class == "private_automation"
            or workload_class == "private_automation"
            or (provider == "athanor_local" and not fallback)
        )
    if task_status != "pending_approval":
        return False
    if bool(metadata.get("_autonomy_managed")):
        return False
    governor_level = (
        _clean_str(metadata.get("governor_autonomy_level"))
        or _clean_str(metadata.get("governor_level"))
    ).upper()
    return governor_level == "C" or not governor_level


def _governed_dispatch_failure_repair_reason(task_row: dict[str, Any]) -> str | None:
    metadata = dict(task_row.get("metadata") or {})
    task_status = _clean_str(task_row.get("status")).lower()
    if task_status == "stale_lease":
        return "stale_lease"
    if task_status == "pending_approval":
        return "stale_waiting_approval"
    if task_status != "failed":
        return None

    lease = dict(metadata.get("execution_lease") or {})
    provider = _clean_str(lease.get("provider")).lower()
    fallback = [_clean_str(item).lower() for item in lease.get("fallback") or [] if _clean_str(item)]
    task_class = _clean_str(metadata.get("task_class")).lower()
    workload_class = _clean_str(metadata.get("workload_class")).lower()
    if (
        task_class == "private_automation"
        or workload_class == "private_automation"
        or (provider == "athanor_local" and not fallback)
    ):
        return "failed_private_local_dispatch"

    failure = dict(metadata.get("failure") or {})
    if bool(metadata.get("_autonomy_managed")) and bool(failure.get("retry_eligible")):
        return "retry_eligible_failed_dispatch"
    return None


def _build_governed_dispatch_materialization_prompt(
    claim: dict[str, Any],
    dispatch_authority: dict[str, Any],
) -> str:
    current_task_title = _clean_str(claim.get("current_task_title")) or "Governed dispatch follow-through"
    current_task_id = _clean_str(claim.get("current_task_id"))
    lane_family = _clean_str(claim.get("preferred_lane_family")) or "unknown_lane_family"
    mutation_label = _clean_str(claim.get("approved_mutation_label")) or "Unknown mutation class"
    proof_surface = _clean_str(claim.get("proof_command_or_eval_surface"))
    claim_id = _clean_str(claim.get("claim_id"))
    provider_gate_state = _clean_str(dispatch_authority.get("provider_gate_state")) or "unknown"
    work_economy_status = _clean_str(dispatch_authority.get("work_economy_status")) or "unknown"

    lines = [
        f'Advance the governed dispatch claim for "{current_task_title}".',
        f"Current task id: {current_task_id}" if current_task_id else None,
        f"Claim id: {claim_id}" if claim_id else None,
        f"Preferred lane family: {lane_family}",
        f"Approved mutation class: {mutation_label}",
        f"Provider gate: {provider_gate_state}",
        f"Work economy: {work_economy_status}",
        f"Proof surface: {proof_surface}" if proof_surface else None,
        "Dispatch artifact: reports/truth-inventory/governed-dispatch-state.json",
        "Stay within repo-safe, non-runtime work unless a governed approval surface explicitly widens scope.",
    ]
    return "\n".join(line for line in lines if line)


def _materialize_governed_dispatch_claim(
    claim: dict[str, Any],
    dispatch_authority: dict[str, Any],
    *,
    generated_at: str,
    request_json: Any | None = None,
) -> dict[str, Any]:
    claim_row = dict(claim or {})
    materialization = {
        "generated_at": generated_at,
        "source_of_truth": "scripts/run_ralph_loop_pass.py",
        "report_path": "reports/truth-inventory/governed-dispatch-materialization.json",
        "status": "idle",
        "claim_id": claim_row.get("claim_id"),
        "current_task_id": claim_row.get("current_task_id"),
        "current_task_title": claim_row.get("current_task_title"),
        "backlog_id": None,
        "backlog_status": None,
        "latest_task_id": None,
        "materialization_source": "governed_dispatch_state",
        "operator_backlog_path": "/v1/operator/backlog",
        "query_status_code": None,
        "post_status_code": None,
        "error": None,
        "task_source": None,
        "retry_of_task_id": None,
        "retry_count": 0,
        "retry_lineage_depth": 0,
        "recovery_event": None,
        "recovery_reason": None,
        "resilience_state": None,
        "advisory_blockers": [],
    }
    if _clean_str(claim_row.get("status")) != "claimed":
        materialization["status"] = "no_claim"
        return materialization

    claim_id = _clean_str(claim_row.get("claim_id"))
    task_id = _clean_str(claim_row.get("current_task_id"))
    title = _clean_str(claim_row.get("current_task_title"))
    if not claim_id or not task_id or not title:
        materialization["status"] = "claim_incomplete"
        materialization["error"] = "claim_id, current_task_id, and current_task_title are required"
        return materialization

    base_url, token = _load_agent_runtime()
    materialization["agent_server_base_url"] = base_url or None
    if not base_url:
        materialization["status"] = "agent_server_unavailable"
        materialization["error"] = "ATHANOR agent server URL is unavailable"
        return materialization

    request_fn = request_json or _request_agent_json
    query_status, query_payload = request_fn(base_url, token, "/v1/operator/backlog?limit=120", timeout=20)
    materialization["query_status_code"] = query_status
    if query_status != 200:
        materialization["status"] = "query_failed"
        materialization["error"] = _clean_str(query_payload.get("error")) or f"operator backlog query failed with {query_status}"
        return materialization

    backlog_rows = [
        dict(item)
        for item in list(query_payload.get("backlog") or [])
        if isinstance(item, dict)
    ]
    existing = next(
        (
            item
            for item in backlog_rows
            if _matches_governed_dispatch_materialization(item, claim_id, task_id, title)
        ),
        None,
    )
    if existing is not None:
        existing_metadata = dict(existing.get("metadata") or {})
        materialization["status"] = "already_materialized"
        materialization["backlog_id"] = _clean_str(existing.get("id")) or None
        materialization["backlog_status"] = _clean_str(existing.get("status")) or None
        materialization["latest_task_id"] = (
            _clean_str(existing_metadata.get("latest_task_id"))
            or _clean_str(existing_metadata.get("latest_run_id"))
            or None
        )
        return materialization

    owner_agent = "coding-agent"
    governed_profile = _governed_dispatch_task_profile(owner_agent=owner_agent)
    payload = {
        "actor": "ralph-loop",
        "session_id": "ralph-loop",
        "correlation_id": uuid.uuid4().hex,
        "reason": f"Materialized governed dispatch claim {claim_id}",
        "title": title,
        "prompt": _build_governed_dispatch_materialization_prompt(claim_row, dispatch_authority),
        "owner_agent": owner_agent,
        "support_agents": [],
        "scope_type": "global",
        "scope_id": "athanor",
        "work_class": "system_improvement",
        "priority": 1,
        "approval_mode": "none",
        "dispatch_policy": "planner_eligible",
        "preconditions": ["governed_dispatch_state_present"],
        "metadata": {
            "materialization_source": "governed_dispatch_state",
            "_autonomy_managed": True,
            "_autonomy_source": "pipeline",
            "task_class": governed_profile["task_class"],
            "workload_class": governed_profile["workload_class"],
            "claim_id": claim_id,
            "current_task_id": task_id,
            "current_task_title": title,
            "preferred_lane_family": _clean_str(claim_row.get("preferred_lane_family")) or None,
            "approved_mutation_class": _clean_str(claim_row.get("approved_mutation_class")) or None,
            "approved_mutation_label": _clean_str(claim_row.get("approved_mutation_label")) or None,
            "provider_gate_state": _clean_str(dispatch_authority.get("provider_gate_state")) or None,
            "work_economy_status": _clean_str(dispatch_authority.get("work_economy_status")) or None,
            "report_path": "reports/truth-inventory/governed-dispatch-state.json",
        },
    }
    post_status, post_payload = request_fn(
        base_url,
        token,
        "/v1/operator/backlog",
        method="POST",
        payload=payload,
        timeout=20,
    )
    materialization["post_status_code"] = post_status
    if post_status != 200:
        materialization["status"] = "materialization_failed"
        materialization["error"] = _clean_str(post_payload.get("error")) or f"operator backlog create failed with {post_status}"
        return materialization

    created_backlog = dict(post_payload.get("backlog") or {})
    materialization["status"] = "materialized"
    materialization["backlog_id"] = _clean_str(created_backlog.get("id")) or None
    materialization["backlog_status"] = _clean_str(created_backlog.get("status")) or None
    return materialization


def _dispatch_governed_dispatch_claim(
    claim: dict[str, Any],
    dispatch_authority: dict[str, Any],
    governed_dispatch_materialization: dict[str, Any],
    *,
    generated_at: str,
    request_json: Any | None = None,
) -> dict[str, Any]:
    claim_row = dict(claim or {})
    materialization = dict(governed_dispatch_materialization or {})
    execution = {
        "generated_at": generated_at,
        "source_of_truth": "scripts/run_ralph_loop_pass.py",
        "report_path": "reports/truth-inventory/governed-dispatch-execution.json",
        "status": "idle",
        "dispatch_outcome": "idle",
        "claim_id": claim_row.get("claim_id"),
        "current_task_id": claim_row.get("current_task_id"),
        "current_task_title": claim_row.get("current_task_title"),
        "backlog_id": materialization.get("backlog_id"),
        "backlog_status": materialization.get("backlog_status"),
        "task_id": None,
        "task_status": None,
        "governor_reason": None,
        "governor_level": None,
        "dispatch_path": None,
        "dispatch_status_code": None,
        "lookup_task_status_code": None,
        "repair_status_code": None,
        "repair_reason": None,
        "repaired_task_id": None,
        "repaired_stale_task_id": None,
        "error": None,
    }
    if _clean_str(claim_row.get("status")) != "claimed":
        execution["status"] = "no_claim"
        return execution

    claim_id = _clean_str(claim_row.get("claim_id"))
    task_id = _clean_str(claim_row.get("current_task_id"))
    title = _clean_str(claim_row.get("current_task_title"))
    if not claim_id or not task_id or not title:
        execution["status"] = "claim_incomplete"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        execution["error"] = "claim_id, current_task_id, and current_task_title are required"
        return execution

    backlog_id = _clean_str(materialization.get("backlog_id"))
    backlog_status = _clean_str(materialization.get("backlog_status")).lower()
    latest_task_id = _clean_str(materialization.get("latest_task_id"))
    execution["backlog_id"] = backlog_id or None
    execution["backlog_status"] = backlog_status or None
    if not backlog_id:
        execution["status"] = "no_materialization"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        return execution

    approved_mutation_classes = {
        _clean_str(item)
        for item in dispatch_authority.get("approved_mutation_classes") or []
        if _clean_str(item)
    }
    approved_mutation_class = _clean_str(claim_row.get("approved_mutation_class"))
    if approved_mutation_classes and approved_mutation_class not in approved_mutation_classes:
        execution["status"] = "mutation_class_not_permitted"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        execution["error"] = f"approved mutation class '{approved_mutation_class or 'unknown'}' is not dispatchable"
        return execution

    base_url, token = _load_agent_runtime()
    execution["agent_server_base_url"] = base_url or None
    if not base_url:
        execution["status"] = "agent_server_unavailable"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        execution["error"] = "ATHANOR agent server URL is unavailable"
        return execution

    request_fn = request_json or _request_agent_json
    existing_task: dict[str, Any] | None = None
    if latest_task_id:
        lookup_status, lookup_payload = request_fn(
            base_url,
            token,
            f"/v1/tasks/{latest_task_id}",
            timeout=20,
        )
        execution["lookup_task_status_code"] = lookup_status
        if lookup_status == 200:
            existing_task = dict(lookup_payload.get("task") or {})
            execution.update(_task_lookup_fields(existing_task))
            if execution.get("resilience_state") == "restart_interfering":
                execution["advisory_blockers"] = ["agent_runtime_restart_interfering"]
            elif execution.get("resilience_state") == "restart_recovered":
                execution["advisory_blockers"] = ["agent_runtime_restart_recovered"]

    if existing_task and _governed_dispatch_task_requires_repair(existing_task):
        existing_task_status = _clean_str(existing_task.get("status")).lower()
        repair_reason = _governed_dispatch_failure_repair_reason(existing_task)
        if existing_task_status == "pending_approval":
            reject_status, reject_payload = request_fn(
                base_url,
                token,
                f"/v1/tasks/{latest_task_id}/reject",
                method="POST",
                payload={
                    "actor": "ralph-loop",
                    "session_id": "ralph-loop",
                    "correlation_id": uuid.uuid4().hex,
                    "reason": "Superseded stale governed dispatch task before autonomy-managed redispatch",
                },
                timeout=20,
            )
            execution["repair_status_code"] = reject_status
            if reject_status != 200:
                execution["status"] = "repair_failed"
                execution["dispatch_outcome"] = "failed"
                execution["error"] = _clean_str(reject_payload.get("error")) or f"task reject failed with {reject_status}"
                return execution
        execution["repaired_task_id"] = latest_task_id or None
        execution["repair_reason"] = repair_reason or (
            "stale_waiting_approval"
            if existing_task_status == "pending_approval"
            else "stale_lease"
            if existing_task_status == "stale_lease"
            else "failed_governed_dispatch"
        )
        if existing_task_status in {"pending_approval", "stale_lease"}:
            execution["repaired_stale_task_id"] = latest_task_id or None
        backlog_status = "ready"
        execution["backlog_status"] = backlog_status
    elif existing_task and _clean_str(existing_task.get("status")).lower() == "failed":
        execution["status"] = "failed_existing_task"
        execution["dispatch_outcome"] = "failed"
        execution["advisory_blockers"] = [
            "governed_dispatch_failed_task",
            *[
                blocker
                for blocker in list(execution.get("advisory_blockers") or [])
                if blocker != "governed_dispatch_failed_task"
            ],
        ]
        return execution
    elif backlog_status == "waiting_approval":
        if existing_task:
            execution["status"] = "already_dispatched"
            execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
            return execution
        backlog_status = "ready"
        execution["backlog_status"] = backlog_status

    if backlog_status in DISPATCH_ACTIVE_BACKLOG_STATUSES:
        execution["status"] = "already_dispatched"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        return execution
    if backlog_status in DISPATCH_TERMINAL_BACKLOG_STATUSES:
        execution["status"] = "dispatch_not_eligible"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        execution["error"] = f"backlog item is already {backlog_status}"
        return execution
    if backlog_status and backlog_status not in DISPATCH_ELIGIBLE_BACKLOG_STATUSES:
        execution["status"] = "dispatch_not_ready"
        execution["dispatch_outcome"] = _clean_str(claim_row.get("dispatch_outcome")) or "claimed"
        execution["error"] = f"backlog status '{backlog_status}' is not eligible for auto-dispatch"
        return execution

    dispatch_path = f"/v1/operator/backlog/{backlog_id}/dispatch"
    execution["dispatch_path"] = dispatch_path
    post_status, post_payload = request_fn(
        base_url,
        token,
        dispatch_path,
        method="POST",
        payload={
            "actor": "ralph-loop",
            "session_id": "ralph-loop",
            "correlation_id": uuid.uuid4().hex,
            "reason": f"Auto-dispatched governed dispatch claim {claim_id}",
        },
        timeout=20,
    )
    execution["dispatch_status_code"] = post_status
    if post_status != 200:
        execution["status"] = "dispatch_failed"
        execution["dispatch_outcome"] = "failed"
        execution["error"] = _clean_str(post_payload.get("error")) or f"operator backlog dispatch failed with {post_status}"
        return execution

    dispatched_backlog = dict(post_payload.get("backlog") or {})
    dispatched_task = dict(post_payload.get("task") or {})
    governor = dict(post_payload.get("governor") or {})
    execution["status"] = "dispatched"
    execution["dispatch_outcome"] = "success"
    execution["backlog_id"] = _clean_str(dispatched_backlog.get("id")) or backlog_id or None
    execution["backlog_status"] = _clean_str(dispatched_backlog.get("status")) or backlog_status or None
    execution["task_id"] = _clean_str(dispatched_task.get("id")) or None
    execution["task_status"] = _clean_str(dispatched_task.get("status")) or None
    execution["governor_reason"] = _clean_str(governor.get("reason")) or None
    execution["governor_level"] = _clean_str(governor.get("level")) or None
    if execution.get("resilience_state") == "restart_interfering":
        execution["advisory_blockers"] = ["agent_runtime_restart_interfering"]
    elif execution.get("resilience_state") == "restart_recovered":
        execution["advisory_blockers"] = ["agent_runtime_restart_recovered"]
    return execution


def _refresh_governed_dispatch_materialization_after_execution(
    claim: dict[str, Any],
    dispatch_authority: dict[str, Any],
    governed_dispatch_materialization: dict[str, Any],
    governed_dispatch_execution: dict[str, Any],
    *,
    generated_at: str,
    request_json: Any | None = None,
) -> dict[str, Any]:
    execution = dict(governed_dispatch_execution or {})
    if _clean_str(execution.get("status")) not in {"dispatched", "already_dispatched"}:
        return dict(governed_dispatch_materialization or {})
    if not _clean_str(execution.get("backlog_id")):
        return dict(governed_dispatch_materialization or {})
    refreshed = _materialize_governed_dispatch_claim(
        claim,
        dispatch_authority,
        generated_at=generated_at,
        request_json=request_json,
    )
    if _clean_str(refreshed.get("status")) in {"materialized", "already_materialized"}:
        return refreshed
    return dict(governed_dispatch_materialization or {})


def _summarize_recent_dispatch_outcomes(records: list[dict[str, Any]]) -> dict[str, Any]:
    recent_dispatch_outcomes: list[dict[str, Any]] = []
    last_outcome: str | None = None
    last_success_at: str | None = None

    for record in records:
        result = dict(record.get("result") or {})
        inputs = dict(record.get("inputs") or {})
        dispatch_outcome = str(result.get("dispatch_outcome") or "").strip().lower()
        if dispatch_outcome not in {"success", "failed", "partial", "claimed"}:
            continue

        completed_at = (
            str(result.get("completed_at") or "").strip()
            or str(result.get("generated_at") or "").strip()
            or str(record.get("timestamp") or "").strip()
            or None
        )
        outcome = {
            "automation_id": str(record.get("automation_id") or "").strip() or None,
            "lane": str(record.get("lane") or "").strip() or None,
            "action_class": str(record.get("action_class") or "").strip() or None,
            "dispatch_outcome": dispatch_outcome,
            "success": True if dispatch_outcome == "success" else False if dispatch_outcome == "failed" else None,
            "completed_at": completed_at,
            "subscription": str(result.get("subscription") or inputs.get("subscription") or "").strip() or None,
            "task_id": str(result.get("claimed_task_id") or inputs.get("task_id") or "").strip() or None,
            "task_title": str(result.get("claimed_task_title") or inputs.get("task_title") or "").strip() or None,
            "summary": str(record.get("operator_visible_summary") or "").strip() or None,
        }
        recent_dispatch_outcomes.append(outcome)
        if last_outcome is None:
            last_outcome = dispatch_outcome
        if last_success_at is None and dispatch_outcome == "success":
            last_success_at = completed_at

    return {
        "last_outcome": last_outcome,
        "last_success_at": last_success_at,
        "recent_dispatch_outcomes": recent_dispatch_outcomes,
        "recent_dispatch_outcome_count": len(recent_dispatch_outcomes),
    }


def _selected_loop_family(
    workstream_row: dict[str, Any],
    any_stale_evidence: bool,
    dispatch_authority: dict[str, Any],
    autonomous_queue_summary: dict[str, Any],
) -> str:
    if any_stale_evidence:
        return "evidence_refresh"
    if bool(dispatch_authority.get("governed_dispatch_ready")) and int(
        autonomous_queue_summary.get("dispatchable_queue_count") or 0
    ) > 0:
        return "governor_scheduling"
    return str(workstream_row["workstream"].get("loop_family") or "governor_scheduling")


def _build_loop_continuity_status(
    ranked_autonomous_queue: list[dict[str, Any]],
    governed_dispatch_claim: dict[str, Any],
    publication_next_family: dict[str, Any],
) -> dict[str, Any]:
    dispatchable_rows = [row for row in ranked_autonomous_queue if _queue_item_effectively_dispatchable(row)]
    current_task_id = str(governed_dispatch_claim.get("current_task_id") or "").strip() or None
    next_unblocked_row = None
    for row in dispatchable_rows:
        task_id = str(row.get("task_id") or "").strip() or None
        if current_task_id and task_id == current_task_id:
            continue
        next_unblocked_row = row
        break
    if next_unblocked_row is None and dispatchable_rows and not current_task_id:
        next_unblocked_row = dispatchable_rows[0]

    claim_active = str(governed_dispatch_claim.get("status") or "").strip() == "claimed" and current_task_id is not None
    if claim_active or dispatchable_rows:
        stop_state = "none"
        stop_reason = None
        continue_allowed = True
    else:
        blocked_rows = [
            row
            for row in ranked_autonomous_queue
            if not _queue_item_effectively_dispatchable(row) and not bool(row.get("suppressed_by_continuity"))
        ]
        stop_state, stop_reason = _stop_state_from_queue_item(blocked_rows[0] if blocked_rows else None)
        continue_allowed = False

    return {
        "continue_allowed": continue_allowed,
        "stop_state": stop_state,
        "stop_reason": stop_reason,
        "next_unblocked_candidate": _queue_candidate_ref(next_unblocked_row),
        "next_deferred_family_id": str(publication_next_family.get("id") or "").strip() or None,
        "next_deferred_family_title": str(publication_next_family.get("title") or "").strip() or None,
        "next_deferred_family_class": str(publication_next_family.get("execution_class") or "").strip() or None,
    }


def _build_ralph_continuity_state(
    previous_continuity_state: dict[str, Any],
    automation_feedback_summary: dict[str, Any],
    governed_dispatch_claim: dict[str, Any],
    continuity_status: dict[str, Any],
    *,
    generated_at: str,
    continuity_policy: dict[str, Any],
    reopened_task_ids: set[str] | None = None,
) -> dict[str, Any]:
    continuity_state = _active_continuity_suppression(
        previous_continuity_state,
        automation_feedback_summary,
        generated_at=generated_at,
        continuity_policy=continuity_policy,
    )
    reopened_task_ids = {
        str(task_id).strip()
        for task_id in (reopened_task_ids or set())
        if str(task_id).strip()
    }
    if reopened_task_ids:
        suppressed_until_by_task = {
            str(task_id).strip(): str(expiry).strip()
            for task_id, expiry in dict(continuity_state.get("suppressed_until_by_task") or {}).items()
            if str(task_id).strip() and str(expiry).strip() and str(task_id).strip() not in reopened_task_ids
        }
        continuity_state["suppressed_until_by_task"] = suppressed_until_by_task
        continuity_state["recent_no_delta_task_ids"] = sorted(suppressed_until_by_task.keys())
    prior_history = [
        dict(entry)
        for entry in previous_continuity_state.get("claim_history", [])
        if isinstance(entry, dict)
    ]
    claim_entry = None
    current_task_id = str(governed_dispatch_claim.get("current_task_id") or "").strip() or None
    if current_task_id:
        claim_entry = {
            "task_id": current_task_id,
            "title": str(governed_dispatch_claim.get("current_task_title") or "").strip() or None,
            "claim_id": str(governed_dispatch_claim.get("claim_id") or "").strip() or None,
            "claimed_at": str(governed_dispatch_claim.get("claimed_at") or generated_at).strip(),
            "source_type": str(governed_dispatch_claim.get("current_source_type") or "").strip() or None,
            "lane_family": str(governed_dispatch_claim.get("current_lane_family") or "").strip() or None,
            "rotation_reason": str(governed_dispatch_claim.get("claim_rotation_reason") or "").strip() or None,
        }
    claim_history: list[dict[str, Any]] = []
    if claim_entry is not None:
        claim_history.append(claim_entry)
    for entry in prior_history:
        claim_id = str(entry.get("claim_id") or "").strip()
        if claim_entry is not None and claim_id and claim_id == claim_entry.get("claim_id"):
            continue
        if claim_entry is not None and not claim_id and str(entry.get("task_id") or "").strip() == claim_entry.get("task_id"):
            continue
        claim_history.append(entry)
    claim_history = claim_history[: int(continuity_policy.get("claim_history_limit") or 12)]

    previous_stop_state = str(previous_continuity_state.get("current_stop_state") or "none").strip() or "none"
    queue_exhausted_at = None
    if continuity_status.get("stop_state") == "queue_exhausted":
        queue_exhausted_at = str(previous_continuity_state.get("queue_exhausted_at") or "").strip() or generated_at
    elif previous_stop_state == "queue_exhausted":
        queue_exhausted_at = str(previous_continuity_state.get("queue_exhausted_at") or "").strip() or None

    continuity_state.update(
        {
            "generated_at": generated_at,
            "state_path": "reports/truth-inventory/ralph-continuity-state.json",
            "continue_allowed": bool(continuity_status.get("continue_allowed")),
            "current_stop_state": str(continuity_status.get("stop_state") or "none"),
            "current_stop_reason": str(continuity_status.get("stop_reason") or "").strip() or None,
            "next_unblocked_candidate": dict(continuity_status.get("next_unblocked_candidate") or {}),
            "next_deferred_family_id": str(continuity_status.get("next_deferred_family_id") or "").strip() or None,
            "claim_history": claim_history,
            "active_claim_history": claim_history,
            "queue_exhausted_at": queue_exhausted_at,
        }
    )
    return continuity_state


def _build_next_actions(
    selected_family: str,
    selected_workstream: dict[str, Any],
    ranked_autonomous_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if selected_family == "governor_scheduling":
        for item in [row for row in ranked_autonomous_queue if _queue_item_effectively_dispatchable(row)][:3]:
            actions.append({"type": "queue_item", **item})
        selected_next_action_family = str(selected_workstream.get("next_action_family") or "").strip()
        if selected_next_action_family:
            for command in NEXT_ACTION_FAMILY_COMMANDS.get(selected_next_action_family, []):
                actions.append({"type": "command", "command": command})
    for command in LOOP_FAMILY_NEXT_COMMANDS.get(selected_family, []):
        actions.append({"type": "command", "command": command})
    for artifact in selected_workstream.get("evidence_artifacts", []):
        actions.append({"type": "artifact", "path": str(artifact)})
    return actions


def _build_operator_facing_state_aliases(
    selected_family: str,
    selected_workstream: dict[str, Any],
    ranked_autonomous_queue: list[dict[str, Any]],
    autonomous_queue_summary: dict[str, Any],
    dispatch_authority: dict[str, Any],
    governed_dispatch_claim: dict[str, Any],
    continuity_status: dict[str, Any],
    publication_next_family: dict[str, Any],
    *,
    any_stale_evidence: bool,
) -> dict[str, Any]:
    top_queue_item = next(
        (row for row in ranked_autonomous_queue if _queue_item_effectively_dispatchable(row)),
        ranked_autonomous_queue[0] if ranked_autonomous_queue else None,
    )
    active_claim_task_id = str(governed_dispatch_claim.get("current_task_id") or "").strip() or None
    active_claim_task_title = str(governed_dispatch_claim.get("current_task_title") or "").strip() or None
    top_task_id = (
        active_claim_task_id
        or str(autonomous_queue_summary.get("top_dispatchable_task_id") or "").strip()
        or str((top_queue_item or {}).get("task_id") or "").strip()
        or str(selected_workstream.get("id") or "").strip()
        or None
    )
    top_task_title = (
        active_claim_task_title
        or str(autonomous_queue_summary.get("top_dispatchable_title") or "").strip()
        or str((top_queue_item or {}).get("title") or "").strip()
        or str(selected_workstream.get("title") or "").strip()
        or None
    )
    top_task = (
        {
            "id": top_task_id,
            "title": top_task_title,
            "dispatch_ready": bool((top_queue_item or {}).get("dispatchable")) if not active_claim_task_id else True,
            "preferred_lane_family": (
                str(governed_dispatch_claim.get("current_lane_family") or "").strip()
                or str((top_queue_item or {}).get("preferred_lane_family") or "").strip()
                or None
            ),
            "approved_mutation_class": (
                str(governed_dispatch_claim.get("approved_mutation_class") or "").strip()
                or str((top_queue_item or {}).get("approved_mutation_class") or "").strip()
                or None
            ),
            "value_class": (
                str(governed_dispatch_claim.get("value_class") or "").strip()
                or str((top_queue_item or {}).get("value_class") or "").strip()
                or None
            ),
            "risk_class": (
                str(governed_dispatch_claim.get("risk_class") or "").strip()
                or str((top_queue_item or {}).get("risk_class") or "").strip()
                or None
            ),
            "source": "governed_dispatch_claim" if active_claim_task_id else ("ranked_autonomous_queue" if top_queue_item else "selected_workstream"),
        }
        if top_task_id or top_task_title
        else None
    )
    selected_execution_state = str(selected_workstream.get("execution_state") or "").strip()
    next_action_family = str(selected_workstream.get("next_action_family") or "").strip() or None
    repo_side_no_delta = bool(
        governed_dispatch_claim.get("repo_side_no_delta")
        if active_claim_task_id
        else (top_queue_item or {}).get("repo_side_no_delta")
    )
    rotation_ready = bool(
        governed_dispatch_claim.get("rotation_ready")
        if active_claim_task_id
        else (top_queue_item or {}).get("rotation_ready")
    )
    reopen_reason_scope = (
        str(governed_dispatch_claim.get("reopen_reason_scope") or "").strip()
        if active_claim_task_id
        else str((top_queue_item or {}).get("reopen_reason_scope") or "").strip()
    ) or None
    no_delta_evidence_refs = [
        str(item).strip()
        for item in (
            governed_dispatch_claim.get("no_delta_evidence_refs")
            if active_claim_task_id
            else (top_queue_item or {}).get("no_delta_evidence_refs", [])
        ) or []
        if str(item).strip()
    ]
    return {
        "status": "active",
        "loop_mode": selected_family,
        "current_loop_family": selected_family,
        "selected_workstream": str(selected_workstream.get("id") or "").strip() or None,
        "selected_workstream_id": str(selected_workstream.get("id") or "").strip() or None,
        "selected_workstream_title": str(selected_workstream.get("title") or "").strip() or None,
        "active_claim_task_id": active_claim_task_id,
        "active_claim_task_title": active_claim_task_title,
        "active_claim_lane_family": str(governed_dispatch_claim.get("current_lane_family") or "").strip() or None,
        "active_claim_rotation_reason": str(governed_dispatch_claim.get("claim_rotation_reason") or "").strip() or None,
        "repo_side_no_delta": repo_side_no_delta,
        "rotation_ready": rotation_ready,
        "reopen_reason_scope": reopen_reason_scope,
        "no_delta_evidence_refs": no_delta_evidence_refs,
        "next_action_family": next_action_family,
        "execution_posture": "steady_state" if selected_execution_state == "steady_state_monitoring" else "active_remediation",
        "evidence_freshness": "stale" if any_stale_evidence else "fresh",
        "top_task": top_task,
        "autonomous_queue": ranked_autonomous_queue,
        "dispatchable_queue_count": int(autonomous_queue_summary.get("dispatchable_queue_count") or 0),
        "provider_gate_state": str(dispatch_authority.get("provider_gate_state") or "").strip() or None,
        "work_economy_status": str(dispatch_authority.get("work_economy_status") or "").strip() or None,
        "continue_allowed": bool(continuity_status.get("continue_allowed")),
        "stop_state": str(continuity_status.get("stop_state") or "none"),
        "stop_reason": str(continuity_status.get("stop_reason") or "").strip() or None,
        "next_unblocked_candidate": dict(continuity_status.get("next_unblocked_candidate") or {}),
        "next_deferred_family_id": str(publication_next_family.get("id") or "").strip() or None,
        "next_deferred_family_title": str(publication_next_family.get("title") or "").strip() or None,
    }


def _build_executive_brief(report: dict[str, Any], continuity_policy: dict[str, Any]) -> dict[str, Any]:
    contract = dict(continuity_policy.get("executive_reporting_contract") or {})

    def pick_string(*values: Any) -> str | None:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    validation = dict(report.get("validation") or {})
    validation_results = [
        dict(result)
        for result in validation.get("results", [])
        if isinstance(result, dict)
    ]
    validation_total = len(validation_results)
    validation_passing = sum(1 for result in validation_results if int(result.get("returncode") or 0) == 0)
    if validation.get("all_passed") is True:
        validation_summary = f"{validation_passing}/{validation_total} validation checks passed."
    elif validation.get("all_passed") is False:
        validation_summary = f"{validation_passing}/{validation_total} validation checks passed; at least one validation command failed."
    else:
        validation_summary = "Validation has not been materialized for this Ralph pass yet."

    freshness = dict(report.get("freshness") or {})
    stale_artifacts = [
        pick_string(artifact.get("id"), artifact.get("path"))
        for artifact in freshness.get("artifacts", [])
        if isinstance(artifact, dict) and bool(artifact.get("stale"))
    ]
    stale_artifacts = [artifact for artifact in stale_artifacts if artifact]

    dispatch_authority = dict(report.get("dispatch_authority") or {})
    governed_execution = dict(dispatch_authority.get("governed_dispatch_execution") or report.get("governed_dispatch_runtime_state") or {})
    governed_claim = dict(report.get("governed_dispatch_claim") or {})
    queue_summary = dict(report.get("autonomous_queue_summary") or {})
    publication_debt = dict(report.get("publication_debt") or {})
    finish_scoreboard = dict(report.get("finish_scoreboard") or {})
    runtime_packet_inbox = dict(report.get("runtime_packet_inbox") or {})
    next_unblocked_candidate = dict(report.get("next_unblocked_candidate") or {})
    advisory_blockers = [
        str(blocker).strip()
        for blocker in list(dispatch_authority.get("advisory_blockers") or [])
        if str(blocker).strip()
    ]

    stop_state = pick_string(report.get("stop_state")) or "none"
    stop_reason = pick_string(report.get("stop_reason"))
    active_claim_task_id = pick_string(report.get("active_claim_task_id"), governed_claim.get("current_task_id"))
    active_claim_task_title = pick_string(report.get("active_claim_task_title"), governed_claim.get("current_task_title"), report.get("selected_workstream_title")) or "unknown"
    active_claim_lane_family = pick_string(report.get("active_claim_lane_family"), governed_claim.get("current_lane_family"))
    rotation_reason = pick_string(report.get("active_claim_rotation_reason"), governed_claim.get("claim_rotation_reason"))
    repo_side_no_delta = bool(report.get("repo_side_no_delta"))
    rotation_ready = bool(report.get("rotation_ready"))
    reopen_reason_scope = pick_string(report.get("reopen_reason_scope"))
    no_delta_evidence_refs = [
        pick_string(item)
        for item in report.get("no_delta_evidence_refs", [])
        if pick_string(item)
    ]
    selected_workstream_title = pick_string(report.get("selected_workstream_title"), dict(report.get("loop_state") or {}).get("selected_workstream_title")) or "unknown"
    dispatch_status = pick_string(governed_execution.get("status"), report.get("dispatch_status"), governed_claim.get("dispatch_outcome")) or "unknown"
    next_deferred_family_id = pick_string(report.get("next_deferred_family_id"))
    next_deferred_family_title = pick_string(report.get("next_deferred_family_title"))
    next_checkpoint_slice_id = pick_string(publication_debt.get("next_checkpoint_slice_id"), report.get("next_checkpoint_slice_id"))
    next_checkpoint_slice_title = pick_string(publication_debt.get("next_checkpoint_slice_title"), report.get("next_checkpoint_slice_title"))
    closure_state = pick_string(finish_scoreboard.get("closure_state")) or "closure_in_progress"
    approval_gated_runtime_packet_count = int(finish_scoreboard.get("approval_gated_runtime_packet_count") or runtime_packet_inbox.get("packet_count") or 0)
    cash_now_remaining_count = int(finish_scoreboard.get("cash_now_remaining_count") or 0)

    risks: list[dict[str, Any]] = []
    if stop_state != "none":
        risks.append({
            "id": "typed_brake",
            "severity": "high",
            "summary": stop_reason or f"Ralph is paused behind stop state {stop_state}.",
        })
    if validation.get("all_passed") is False:
        risks.append({
            "id": "validation_red",
            "severity": "high",
            "summary": validation_summary,
        })
    if stale_artifacts:
        risks.append({
            "id": "stale_evidence",
            "severity": "medium",
            "summary": f"Stale evidence still exists for {', '.join(stale_artifacts[:4])}.",
        })
    if publication_debt.get("blocking_debt"):
        risks.append({
            "id": "publication_debt",
            "severity": "medium",
            "summary": f"Publication debt remains blocking through {pick_string(publication_debt.get('blocking_workstream_id')) or 'validation-and-publication'} with {int(publication_debt.get('ready_for_checkpoint') or 0)} ready checkpoint slices.",
        })
    if approval_gated_runtime_packet_count:
        risks.append({
            "id": "runtime_packets_queued",
            "severity": "low",
            "summary": f"{approval_gated_runtime_packet_count} approval-gated runtime packets remain ready but intentionally unexecuted.",
        })
    if rotation_ready:
        risks.append({
            "id": "rotation_due",
            "severity": "medium",
            "summary": f"{selected_workstream_title} is verified repo-side no-delta and should rotate instead of being reclaimed on ambient churn.",
        })
    blocked_queue_count = int(queue_summary.get("blocked_queue_count") or 0)
    dispatchable_queue_count = int(queue_summary.get("dispatchable_queue_count") or report.get("dispatchable_queue_count") or 0)
    if blocked_queue_count:
        risks.append({
            "id": "queue_pressure",
            "severity": "medium",
            "summary": f"{blocked_queue_count} queue items remain blocked while {dispatchable_queue_count} are currently dispatchable.",
        })
    suppressed_queue_count = int(queue_summary.get("suppressed_queue_count") or 0)
    if suppressed_queue_count:
        risks.append({
            "id": "suppressed_queue_items",
            "severity": "low",
            "summary": f"{suppressed_queue_count} queue items are continuity-suppressed rather than blocked.",
        })
    if advisory_blockers:
        risks.append({
            "id": "advisory_blockers",
            "severity": "medium",
            "summary": f"Advisory blockers present: {', '.join(advisory_blockers[:3])}.",
        })
    risks = risks[:5]

    latest_delta_summary = f"Active claim {active_claim_task_title} is {dispatch_status}."
    if rotation_reason:
        latest_delta_summary += f" Rotation reason: {rotation_reason}."
    if repo_side_no_delta:
        latest_delta_summary += f" {selected_workstream_title} is verified repo-side no-delta."
    if validation.get("all_passed") is True:
        latest_delta_summary += " Validators stayed green on this pass."
    elif validation.get("all_passed") is False:
        latest_delta_summary += " Validators are not green on this pass."

    delegate_now: list[str] = []
    next_unblocked_task_id = pick_string(next_unblocked_candidate.get("task_id"), next_unblocked_candidate.get("id"))
    if next_unblocked_candidate:
        delegate_now.append(
            f"Bounded read-only verification or feeder prep for {pick_string(next_unblocked_candidate.get('title'), next_unblocked_task_id) or 'unknown'} before the next claim rotation."
        )
    if next_unblocked_task_id and next_unblocked_task_id.startswith("burn_class:"):
        burn_class_id = next_unblocked_task_id.split(":", 1)[1]
        delegate_now.append(
            f"Inspect burn-class readiness with `python scripts/preflight_burn_class.py {burn_class_id} --json` before the next rotation."
        )
    if next_checkpoint_slice_id:
        delegate_now.append(
            f"Prepare checkpoint slice {next_checkpoint_slice_title or next_checkpoint_slice_id} for publication proof and artifact review."
        )
    if next_deferred_family_id:
        delegate_now.append(
            f"Publication-triage inventory for {next_deferred_family_title or next_deferred_family_id} once no unsuppressed workstream remains."
        )
    if approval_gated_runtime_packet_count:
        delegate_now.append(
            "Keep the runtime packet inbox current so approval-gated host mutations stay decision-complete without stalling repo-safe closure."
        )

    next_moves: list[str] = [
        (
            f"Rotate from {selected_workstream_title} to {pick_string(next_unblocked_candidate.get('title'), next_unblocked_candidate.get('task_id')) or 'the next unblocked tranche'} because repo-side no-delta is already verified."
            if rotation_ready and next_unblocked_candidate
            else f"Keep {active_claim_task_title} active until it yields a typed brake or a verified no-delta outcome."
        ),
    ]
    if stale_artifacts:
        next_moves.append(f"Refresh stale evidence for {', '.join(stale_artifacts[:3])} before opening more speculative work.")
    if next_unblocked_candidate:
        next_moves.append(
            f"Rotate to {pick_string(next_unblocked_candidate.get('title'), next_unblocked_task_id) or 'unknown'} if the current claim yields no new delta."
        )
        if next_unblocked_task_id and next_unblocked_task_id.startswith("burn_class:"):
            burn_class_id = next_unblocked_task_id.split(":", 1)[1]
            next_moves.append(
                f"Next burn-class rotation on deck: `{next_unblocked_task_id}`; preflight it with `python scripts/preflight_burn_class.py {burn_class_id} --json`."
            )
    elif next_checkpoint_slice_id:
        next_moves.append(
            f"Cash checkpoint slice {next_checkpoint_slice_title or next_checkpoint_slice_id} while validation-and-publication owns the active claim."
        )
    elif next_deferred_family_id:
        next_moves.append(f"Cash deferred family {next_deferred_family_id} when no unsuppressed workstream remains.")
    if publication_debt.get("blocking_debt"):
        next_moves.append("Reduce publication debt instead of inventing new architecture or reopening closed canon questions.")
    if cash_now_remaining_count:
        next_moves.append(
            f"Cash `cash_now` deferred families before rotating into generic burn-class work; remaining cash_now families=`{cash_now_remaining_count}`."
        )
    if approval_gated_runtime_packet_count:
        next_moves.append(
            "Keep approval-gated runtime packets queued and visible in the runtime packet inbox; do not execute them without explicit approval."
        )

    decision_needed: dict[str, Any] | None = None
    if stop_state != "none":
        decision_needed = {
            "stop_state": stop_state,
            "reason": stop_reason or f"Operator attention is required for stop state {stop_state}.",
        }

    return {
        "contract": {
            "required_sections": list(contract.get("required_sections") or []),
            "trigger_points": list(contract.get("required_trigger_points") or []),
            "use_active_claim_for_current_task": bool(contract.get("use_active_claim_for_current_task", True)),
        },
        "program_state": {
            "loop_mode": pick_string(report.get("loop_mode"), report.get("current_loop_family"), dict(report.get("loop_state") or {}).get("current_loop_family")) or "unknown",
            "selected_workstream": pick_string(report.get("selected_workstream"), dict(report.get("loop_state") or {}).get("selected_workstream")),
            "selected_workstream_title": pick_string(report.get("selected_workstream_title"), dict(report.get("loop_state") or {}).get("selected_workstream_title")),
            "active_claim_task_id": active_claim_task_id,
            "active_claim_task_title": active_claim_task_title,
            "active_claim_lane_family": active_claim_lane_family,
            "repo_side_no_delta": repo_side_no_delta,
            "rotation_ready": rotation_ready,
            "reopen_reason_scope": reopen_reason_scope,
            "next_checkpoint_slice_id": next_checkpoint_slice_id,
            "next_checkpoint_slice_title": next_checkpoint_slice_title,
            "closure_state": closure_state,
            "cash_now_remaining_count": cash_now_remaining_count,
            "approval_gated_runtime_packet_count": approval_gated_runtime_packet_count,
            "next_action_family": pick_string(report.get("next_action_family"), dict(report.get("loop_state") or {}).get("next_action_family")),
            "execution_posture": pick_string(report.get("execution_posture"), dict(report.get("loop_state") or {}).get("execution_posture")) or "unknown",
            "continue_allowed": bool(report.get("continue_allowed")),
            "stop_state": stop_state,
        },
        "landed_or_delta": {
            "summary": latest_delta_summary,
            "dispatch_status": dispatch_status,
            "dispatch_outcome": pick_string(governed_claim.get("dispatch_outcome"), report.get("dispatch_status")),
            "rotation_reason": rotation_reason,
            "repo_side_no_delta": repo_side_no_delta,
            "rotation_ready": rotation_ready,
        },
        "proof": {
            "validation_all_passed": validation.get("all_passed"),
            "validation_summary": validation_summary,
            "validation_check_count": validation_total,
            "evidence_freshness": pick_string(report.get("evidence_freshness"), dict(report.get("loop_state") or {}).get("evidence_freshness")) or "unknown",
            "dispatch_status": dispatch_status,
            "governed_dispatch_ready": bool(dispatch_authority.get("governed_dispatch_ready")),
            "no_delta_evidence_refs": no_delta_evidence_refs,
        },
        "risks": risks,
        "delegation": {
            "main_agent_focus": f"{active_claim_task_title} ({active_claim_task_id})" if active_claim_task_id else active_claim_task_title,
            "delegation_posture": "Keep truth arbitration, final integration, and destructive cleanup local; delegate bounded read-only verification, feeder prep, and sidecar inventory only.",
            "delegate_now": delegate_now,
        },
        "next_moves": next_moves[:4],
        "decision_needed": decision_needed,
    }


def _summarize_reconciliation_end_state(
    completion_program: dict[str, Any],
    provider_gate_detail: dict[str, Any],
    *,
    validation_passed: bool | None,
    any_stale_evidence: bool,
) -> dict[str, Any]:
    end_state = dict(completion_program.get("reconciliation_end_state") or {})
    gate_rows = [
        dict(entry) for entry in end_state.get("project_exit_gates", []) if isinstance(entry, dict)
    ]
    gate_summary = {
        "total": len(gate_rows),
        "active": 0,
        "ready_for_operator_approval": 0,
        "external_dependency_blocked": 0,
        "steady_state_monitoring": 0,
        "completed": 0,
        "all_non_steady_state_gates_terminal": True,
    }
    active_non_steady_state_gate_ids: list[str] = []
    for gate in gate_rows:
        gate_id = str(gate.get("id") or "")
        if gate_id == "provider_gate":
            gate["blocking_provider_count"] = int(provider_gate_detail.get("blocking_provider_count") or 0)
            gate["blocking_provider_ids"] = list(provider_gate_detail.get("blocking_provider_ids") or [])
            gate["excluded_provider_ids"] = list(provider_gate_detail.get("excluded_provider_ids") or [])
            gate["classification_counts"] = dict(provider_gate_detail.get("classification_counts") or {})
        gate_status = str(gate.get("status") or "active")
        if gate_status in gate_summary:
            gate_summary[gate_status] += 1
        if gate_id != "steady_state_gate" and gate_status not in TERMINAL_RECONCILIATION_GATE_STATES:
            gate_summary["all_non_steady_state_gates_terminal"] = False
            active_non_steady_state_gate_ids.append(gate_id)

    steady_state_acceptance = dict(end_state.get("steady_state_acceptance") or {})
    required_clean_cycles = int(steady_state_acceptance.get("required_consecutive_clean_cycles") or 2)
    previous_clean_cycles = int(steady_state_acceptance.get("current_consecutive_clean_cycles") or 0)
    if validation_passed is None:
        clean_cycle_observed = False
        current_clean_cycles = previous_clean_cycles
        ready_to_transition = bool(steady_state_acceptance.get("ready_to_transition"))
        last_clean_cycle_at = steady_state_acceptance.get("last_clean_cycle_at")
    else:
        clean_cycle_observed = bool(
            validation_passed
            and not any_stale_evidence
            and gate_summary["all_non_steady_state_gates_terminal"]
        )
        current_clean_cycles = previous_clean_cycles + 1 if clean_cycle_observed else 0
        ready_to_transition = current_clean_cycles >= required_clean_cycles
        last_clean_cycle_at = _iso_now() if clean_cycle_observed else None
    steady_state_acceptance["current_consecutive_clean_cycles"] = current_clean_cycles
    steady_state_acceptance["last_clean_cycle_at"] = last_clean_cycle_at
    steady_state_acceptance["ready_to_transition"] = ready_to_transition
    end_state["steady_state_acceptance"] = steady_state_acceptance
    end_state["project_exit_gates"] = gate_rows
    end_state["gate_summary"] = gate_summary
    end_state["active_non_steady_state_gate_ids"] = active_non_steady_state_gate_ids
    end_state["status"] = (
        "steady_state_monitoring"
        if str(next((gate.get("status") for gate in gate_rows if str(gate.get("id") or "") == "steady_state_gate"), "active"))
        == "steady_state_monitoring"
        else "active_remediation"
    )
    return end_state


def _sync_registry_loop_state(
    completion_program: dict[str, Any],
    autonomy_activation: dict[str, Any],
    selected_family: str,
    selected_workstream: dict[str, Any],
    any_stale_evidence: bool,
) -> None:
    selected_execution_state = str(selected_workstream.get("execution_state") or "")
    next_action_family = str(selected_workstream.get("next_action_family") or "").strip()
    if selected_family == "governor_scheduling":
        next_action_family = next_action_family or "ranked_autonomous_dispatch"
    completion_program["ralph_loop"] = {
        "status": "active",
        "current_phase_scope": str(autonomy_activation.get("current_phase_id") or ""),
        "controller_script": "scripts/run_ralph_loop_pass.py",
        "report_path": "reports/ralph-loop/latest.json",
        "current_loop_family": selected_family,
        "selected_workstream": str(selected_workstream.get("id") or ""),
        "evidence_freshness": "stale" if any_stale_evidence else "fresh",
        "approval_status": "required" if bool(selected_workstream.get("approval_required")) else "not_required",
        "blocker_type": str(selected_workstream.get("blocker_type") or "none"),
        "next_action_family": next_action_family,
        "last_validation_run": _iso_now(),
        "execution_posture": (
            "steady_state"
            if selected_execution_state == "steady_state_monitoring"
            else "active_remediation"
        ),
    }
    _write_json(CONFIG_DIR / "completion-program-registry.json", completion_program)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Ralph-loop control-plane pass.")
    parser.add_argument(
        "--skip-refresh",
        action="store_true",
        help="Do not run evidence refresh commands before computing the Ralph-loop report.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Do not run the validation gate after computing the Ralph-loop report.",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    refresh_results: list[dict[str, Any]] = []
    if not args.skip_refresh:
        for command in REFRESH_COMMANDS:
            refresh_results.append(_run_command(command).to_dict())

    completion_program = _load_json(CONFIG_DIR / "completion-program-registry.json")
    continuity_policy = _continuity_policy(completion_program)
    autonomy_activation = _load_json(CONFIG_DIR / "autonomy-activation-registry.json")
    operating_system = _load_json(CONFIG_DIR / "program-operating-system.json")
    burn_registry = _load_json(BURN_REGISTRY_PATH)
    provider_catalog = _load_json(PROVIDER_CATALOG_PATH)
    approval_matrix = _load_json(APPROVAL_MATRIX_PATH)
    provider_gate_detail = _provider_gate_detail(provider_catalog)
    _sync_provider_gate_registry_state(completion_program, provider_gate_detail)
    routing_policy = _load_yaml(REPO_ROOT / "projects" / "agents" / "config" / "subscription-routing-policy.yaml")
    quota_truth = _load_json(REPO_ROOT / "reports" / "truth-inventory" / "quota-truth.json")
    capacity_telemetry = _load_json(REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json")
    truth_snapshot = _load_json(REPO_ROOT / "reports" / "truth-inventory" / "latest.json")
    safe_surface_state = _load_json(SAFE_SURFACE_STATE_PATH) if SAFE_SURFACE_STATE_PATH.exists() else {}
    safe_surface_queue = _load_json(SAFE_SURFACE_QUEUE_PATH) if SAFE_SURFACE_QUEUE_PATH.exists() else {}
    publication_deferred_queue = _load_json(PUBLICATION_DEFERRED_QUEUE_PATH) if PUBLICATION_DEFERRED_QUEUE_PATH.exists() else {}
    runtime_packets_payload = _load_json(RUNTIME_PACKETS_PATH)
    previous_continuity_state = _load_json(RALPH_CONTINUITY_STATE_PATH) if RALPH_CONTINUITY_STATE_PATH.exists() else {}
    now_ts = time.time()
    freshness_index = _artifact_freshness(now_ts)
    any_stale_evidence = any(row["stale"] for row in freshness_index.values())
    work_economy_detail = _work_economy_detail(
        provider_catalog=provider_catalog,
        routing_policy=routing_policy,
        burn_registry=burn_registry,
        provider_gate_detail=provider_gate_detail,
        quota_truth=quota_truth,
        capacity_telemetry=capacity_telemetry,
    )
    generated_at = _iso_now()
    previous_ralph_report = _load_json(REPORT_PATH) if REPORT_PATH.exists() else {}
    preexisting_automation_feedback_summary = _build_automation_feedback_summary(
        asyncio.run(read_recent_automation_run_records(limit=AUTOMATION_FEEDBACK_RECENT_LIMIT))
    )
    preexisting_continuity_state = _active_continuity_suppression(
        previous_continuity_state,
        preexisting_automation_feedback_summary,
        generated_at=generated_at,
        continuity_policy=continuity_policy,
    )

    workstreams = [
        dict(entry)
        for entry in completion_program.get("workstreams", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]
    workstreams_by_id = {str(entry["id"]): entry for entry in workstreams}
    workstream_rows: list[dict[str, Any]] = []
    for order_index, workstream in enumerate(workstreams):
        dependency_state = _dependency_state(workstream, workstreams_by_id)
        evidence_state = _evidence_state_for_workstream(workstream, freshness_index)
        workstream_rows.append(
            {
                "order_index": order_index,
                "workstream": workstream,
                "dependency_state": dependency_state,
                "evidence_state": evidence_state,
            }
        )

    safe_surface_summary = _build_safe_surface_summary(safe_surface_state, safe_surface_queue)
    ranked_autonomous_queue = _build_ranked_autonomous_queue(
        queue=safe_surface_queue,
        workstream_rows=workstream_rows,
        completion_program=completion_program,
        burn_registry=burn_registry,
        work_economy_detail=work_economy_detail,
        provider_gate_detail=provider_gate_detail,
        quota_truth=quota_truth,
        publication_queue=publication_deferred_queue,
        continuity_state=preexisting_continuity_state,
        capacity_telemetry=capacity_telemetry,
    )
    reopened_task_ids = {
        str(item.get("task_id") or "").strip()
        for item in ranked_autonomous_queue
        if bool(item.get("reopened_by_repo_delta")) and str(item.get("task_id") or "").strip()
    }
    autonomous_queue_summary = _build_autonomous_queue_summary(ranked_autonomous_queue)
    dispatch_authority = _build_dispatch_authority(
        completion_program=completion_program,
        burn_registry=burn_registry,
        routing_policy=routing_policy,
        provider_gate_detail=provider_gate_detail,
        safe_surface_summary=safe_surface_summary,
        autonomous_queue_summary=autonomous_queue_summary,
        provider_catalog=provider_catalog,
        quota_truth=quota_truth,
        capacity_telemetry=capacity_telemetry,
    )
    governed_dispatch_claim = _build_governed_dispatch_claim(
        ranked_autonomous_queue,
        dispatch_authority,
        approval_matrix,
        safe_surface_state,
        generated_at=generated_at,
        previous_ralph_report=previous_ralph_report,
        automation_feedback_summary=preexisting_automation_feedback_summary,
        continuity_state=preexisting_continuity_state,
        reopened_task_ids=reopened_task_ids,
    )
    safe_surface_state = _sync_governed_dispatch_state(safe_surface_state, governed_dispatch_claim)
    safe_surface_state_write_error: str | None = None
    try:
        SAFE_SURFACE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _write_json(SAFE_SURFACE_STATE_PATH, safe_surface_state)
    except Exception as exc:
        safe_surface_state_write_error = str(exc)
    safe_surface_summary = _build_safe_surface_summary(safe_surface_state, safe_surface_queue)
    dispatch_authority["governed_dispatch_claim"] = governed_dispatch_claim
    dispatch_authority["governed_dispatch_report_path"] = "reports/truth-inventory/governed-dispatch-state.json"
    governed_dispatch_materialization = _materialize_governed_dispatch_claim(
        governed_dispatch_claim,
        dispatch_authority,
        generated_at=generated_at,
    )
    governed_dispatch_execution = _dispatch_governed_dispatch_claim(
        governed_dispatch_claim,
        dispatch_authority,
        governed_dispatch_materialization,
        generated_at=generated_at,
    )
    governed_dispatch_materialization = _refresh_governed_dispatch_materialization_after_execution(
        governed_dispatch_claim,
        dispatch_authority,
        governed_dispatch_materialization,
        governed_dispatch_execution,
        generated_at=generated_at,
    )
    _write_json(GOVERNED_DISPATCH_MATERIALIZATION_REPORT_PATH, governed_dispatch_materialization)
    dispatch_authority["governed_dispatch_materialization"] = governed_dispatch_materialization
    dispatch_authority["governed_dispatch_materialization_report_path"] = (
        "reports/truth-inventory/governed-dispatch-materialization.json"
    )
    _write_json(GOVERNED_DISPATCH_EXECUTION_REPORT_PATH, governed_dispatch_execution)
    dispatch_authority["governed_dispatch_execution"] = governed_dispatch_execution
    dispatch_authority["governed_dispatch_execution_report_path"] = (
        "reports/truth-inventory/governed-dispatch-execution.json"
    )
    dispatch_authority["safe_surface_dispatchable_queue_count"] = int(safe_surface_summary.get("dispatchable_queue_count") or 0)
    governed_dispatch_runtime_state = _build_governed_dispatch_runtime_state(
        governed_dispatch_claim,
        dispatch_authority,
        autonomous_queue_summary,
        safe_surface_summary,
        governed_dispatch_materialization,
        governed_dispatch_execution,
        generated_at=generated_at,
    )
    _write_json(GOVERNED_DISPATCH_REPORT_PATH, governed_dispatch_runtime_state)
    publication_next_family = dict(publication_deferred_queue.get("next_recommended_family") or {})
    continuity_status = _build_loop_continuity_status(
        ranked_autonomous_queue,
        governed_dispatch_claim,
        publication_next_family,
    )
    pre_validation_continuity_state = _build_ralph_continuity_state(
        previous_continuity_state,
        preexisting_automation_feedback_summary,
        governed_dispatch_claim,
        continuity_status,
        generated_at=generated_at,
        continuity_policy=continuity_policy,
        reopened_task_ids=reopened_task_ids,
    )
    RALPH_CONTINUITY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(RALPH_CONTINUITY_STATE_PATH, pre_validation_continuity_state)
    selected_row = _select_active_workstream(workstream_rows)
    selected_workstream = dict(selected_row["workstream"])
    selected_family = _selected_loop_family(
        selected_row,
        any_stale_evidence,
        dispatch_authority,
        autonomous_queue_summary,
    )
    selected_execution_state = str(selected_workstream.get("execution_state") or "")
    approval_required = bool(selected_workstream.get("approval_required"))
    next_action_family = str(selected_workstream.get("next_action_family") or "").strip()
    if selected_family == "governor_scheduling":
        next_action_family = next_action_family or "ranked_autonomous_dispatch"

    _sync_registry_loop_state(
        completion_program=completion_program,
        autonomy_activation=autonomy_activation,
        selected_family=selected_family,
        selected_workstream=selected_workstream,
        any_stale_evidence=any_stale_evidence,
    )
    automation_feedback_summary: dict[str, Any] = {}

    report = {
        "generated_at": generated_at,
        "source_of_truth": {
            "completion_program_registry": "config/automation-backbone/completion-program-registry.json",
            "autonomy_activation_registry": "config/automation-backbone/autonomy-activation-registry.json",
            "program_operating_system": "config/automation-backbone/program-operating-system.json",
            "routing_policy": "projects/agents/config/subscription-routing-policy.yaml",
            "reconciliation_end_state_doc": "docs/operations/ATHANOR-RECONCILIATION-END-STATE.md",
            "status_doc": "STATUS.md",
            "backlog_doc": "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
            "governed_dispatch_state": "reports/truth-inventory/governed-dispatch-state.json",
            "governed_dispatch_materialization": "reports/truth-inventory/governed-dispatch-materialization.json",
            "publication_deferred_queue": "reports/truth-inventory/publication-deferred-family-queue.json",
            "continuity_state": "reports/truth-inventory/ralph-continuity-state.json",
        },
        "controller": {
            "script": "scripts/run_ralph_loop_pass.py",
            "phase_scope": str(autonomy_activation.get("current_phase_id") or ""),
            "activation_state": str(autonomy_activation.get("activation_state") or ""),
            "broad_autonomy_enabled": bool(autonomy_activation.get("broad_autonomy_enabled")),
            "runtime_mutations_approval_gated": bool(autonomy_activation.get("runtime_mutations_approval_gated")),
        },
        "loop_state": {
            "current_loop_family": selected_family,
            "selected_workstream": str(selected_workstream.get("id") or ""),
            "selected_workstream_id": str(selected_workstream.get("id") or ""),
            "selected_workstream_title": str(selected_workstream.get("title") or ""),
            "selected_execution_state": selected_execution_state,
            "evidence_freshness": "stale" if any_stale_evidence else "fresh",
            "approval_status": "required" if approval_required else "not_required",
            "blocker_type": str(selected_workstream.get("blocker_type") or "none"),
            "next_action_family": next_action_family,
            "execution_posture": (
                "steady_state"
                if selected_execution_state == "steady_state_monitoring"
                else "active_remediation"
            ),
            "continue_allowed": bool(continuity_status.get("continue_allowed")),
            "stop_state": str(continuity_status.get("stop_state") or "none"),
            "stop_reason": str(continuity_status.get("stop_reason") or "").strip() or None,
            "active_claim_task_id": str(governed_dispatch_claim.get("current_task_id") or "").strip() or None,
            "active_claim_task_title": str(governed_dispatch_claim.get("current_task_title") or "").strip() or None,
        },
        **_build_operator_facing_state_aliases(
            selected_family,
            selected_workstream,
            ranked_autonomous_queue,
            autonomous_queue_summary,
            dispatch_authority,
            governed_dispatch_claim,
            continuity_status,
            publication_next_family,
            any_stale_evidence=any_stale_evidence,
        ),
        "cadence": dict(operating_system.get("cadence") or {}),
        "ranking_axes": list((operating_system.get("backlog_policy") or {}).get("ranking_axes") or []),
        "autonomous_queue_policy": dict(operating_system.get("autonomous_queue_policy") or {}),
        "provider_routing_defaults": {
            "task_classes": dict(routing_policy.get("task_classes") or {}),
            "quota_strategy": dict(routing_policy.get("quota_strategy") or {}),
        },
        "dispatch_authority": dispatch_authority,
        "safe_surface_summary": safe_surface_summary,
        "autonomous_queue_summary": autonomous_queue_summary,
        "automation_feedback_summary": automation_feedback_summary,
        "continuity": dict(pre_validation_continuity_state),
        "publication_debt": build_publication_debt_summary(completion_program),
        "recovery_drills": build_recovery_drill_summary(),
        "governed_dispatch_claim": governed_dispatch_claim,
        "governed_dispatch_runtime_state": governed_dispatch_runtime_state,
        "governed_dispatch_materialization": governed_dispatch_materialization,
        "safe_surface_state_write": {
            "path": str(SAFE_SURFACE_STATE_PATH),
            "persisted": safe_surface_state_write_error is None,
            "error": safe_surface_state_write_error,
        },
        "ranked_autonomous_queue": ranked_autonomous_queue,
        "evidence_refresh": {
            "ran": not args.skip_refresh,
            "results": refresh_results,
        },
        "freshness": {
            "any_stale_evidence": any_stale_evidence,
            "artifacts": list(freshness_index.values()),
        },
        "truth_snapshot_collected_at": truth_snapshot.get("collected_at"),
        "reconciliation_end_state": dict(completion_program.get("reconciliation_end_state") or {}),
        "workstreams": [
            {
                "id": str(row["workstream"].get("id") or ""),
                "title": str(row["workstream"].get("title") or ""),
                "priority": str(row["workstream"].get("priority") or ""),
                "status": str(row["workstream"].get("status") or ""),
                "loop_family": str(row["workstream"].get("loop_family") or ""),
                "execution_state": str(row["workstream"].get("execution_state") or ""),
                "blocker_type": str(row["workstream"].get("blocker_type") or ""),
                "approval_required": bool(row["workstream"].get("approval_required")),
                "next_action_family": str(row["workstream"].get("next_action_family") or ""),
                "dependency_state": str(row["dependency_state"]),
                "evidence_state": dict(row["evidence_state"]),
                "execution_binding": dict((completion_program.get("workstream_execution_bindings") or {}).get(str(row["workstream"].get("id") or ""), {})),
            }
            for row in workstream_rows
        ],
        "next_actions": _build_next_actions(selected_family, selected_workstream, ranked_autonomous_queue),
        "validation": {
            "ran": not args.skip_validation,
            "results": [],
            "all_passed": None,
        },
    }
    report["next_checkpoint_slice_id"] = _clean_str(dict(report.get("publication_debt") or {}).get("next_checkpoint_slice_id"))
    report["next_checkpoint_slice_title"] = _clean_str(dict(report.get("publication_debt") or {}).get("next_checkpoint_slice_title"))
    report["next_checkpoint_slice_status"] = _clean_str(dict(report.get("publication_debt") or {}).get("next_checkpoint_slice_status"))
    report["loop_state"]["next_checkpoint_slice_id"] = report["next_checkpoint_slice_id"]
    report["loop_state"]["next_checkpoint_slice_title"] = report["next_checkpoint_slice_title"]
    report["loop_state"]["next_checkpoint_slice_status"] = report["next_checkpoint_slice_status"]

    report["executive_brief"] = _build_executive_brief(report, continuity_policy)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_PATH, report)

    validation_results: list[dict[str, Any]] = []
    if not args.skip_validation:
        for command in VALIDATION_COMMANDS:
            validation_results.append(_run_command(command).to_dict())
    report["validation"] = {
        "ran": not args.skip_validation,
        "results": validation_results,
        "all_passed": all(result["returncode"] == 0 for result in validation_results) if validation_results else None,
    }
    completion_program = _load_json(CONFIG_DIR / "completion-program-registry.json")
    end_state_summary = _summarize_reconciliation_end_state(
        completion_program,
        provider_gate_detail,
        validation_passed=report["validation"]["all_passed"],
        any_stale_evidence=any_stale_evidence,
    )
    completion_program["reconciliation_end_state"] = end_state_summary
    if isinstance(completion_program.get("ralph_loop"), dict):
        completion_program["ralph_loop"]["last_validation_run"] = report["generated_at"]
        completion_program["ralph_loop"]["execution_posture"] = (
            "steady_state" if end_state_summary.get("status") == "steady_state_monitoring" else "active_remediation"
        )
        _write_json(CONFIG_DIR / "completion-program-registry.json", completion_program)
    report["reconciliation_end_state"] = end_state_summary
    report["loop_state"]["execution_posture"] = str(
        dict(completion_program.get("ralph_loop") or {}).get("execution_posture") or report["loop_state"]["execution_posture"]
    )
    report["execution_posture"] = report["loop_state"]["execution_posture"]
    report["evidence_freshness"] = report["loop_state"]["evidence_freshness"]

    effective_dispatch_outcome = (
        _clean_str(governed_dispatch_execution.get("dispatch_outcome"))
        or _clean_str(governed_dispatch_claim.get("dispatch_outcome"))
        or "idle"
    )

    record = AutomationRunRecord(
        automation_id="ralph-loop",
        lane="ralph_loop",
        action_class="autonomous_planning",
        inputs={
            "refresh_commands": REFRESH_COMMANDS,
            "validation_commands": VALIDATION_COMMANDS,
            "report_path": str(REPORT_PATH),
            "governed_dispatch_state_path": str(SAFE_SURFACE_STATE_PATH),
            "skip_refresh": bool(args.skip_refresh),
            "skip_validation": bool(args.skip_validation),
        },
        result={
            "selected_loop_family": report["loop_state"]["current_loop_family"],
            "selected_workstream": report["loop_state"]["selected_workstream"],
            "selected_workstream_id": report["loop_state"]["selected_workstream"],
            "selected_execution_state": report["loop_state"]["selected_execution_state"],
            "any_stale_evidence": report["freshness"]["any_stale_evidence"],
            "validation_passed": report["validation"]["all_passed"],
            "report_path": str(REPORT_PATH),
            "dispatch_outcome": effective_dispatch_outcome,
            "claimed_task_id": governed_dispatch_claim.get("current_task_id"),
            "claimed_task_title": governed_dispatch_claim.get("current_task_title"),
            "claimed_mutation_class": governed_dispatch_claim.get("approved_mutation_class"),
            "materialization_status": governed_dispatch_materialization.get("status"),
            "materialized_backlog_id": governed_dispatch_materialization.get("backlog_id"),
            "dispatch_execution_status": governed_dispatch_execution.get("status"),
            "dispatched_backlog_status": governed_dispatch_execution.get("backlog_status"),
            "dispatched_task_id": governed_dispatch_execution.get("task_id"),
            "dispatched_task_status": governed_dispatch_execution.get("task_status"),
            "claim_state_path": str(SAFE_SURFACE_STATE_PATH),
            "governed_dispatch_state_path": str(GOVERNED_DISPATCH_REPORT_PATH),
            "governed_dispatch_materialization_path": str(GOVERNED_DISPATCH_MATERIALIZATION_REPORT_PATH),
            "governed_dispatch_execution_path": str(GOVERNED_DISPATCH_EXECUTION_REPORT_PATH),
            "continue_allowed": report.get("continue_allowed"),
            "stop_state": report.get("stop_state"),
            "stop_reason": report.get("stop_reason"),
            "next_deferred_family_id": report.get("next_deferred_family_id"),
        },
        rollback={
            "mode": "delete_artifact",
            "path": str(REPORT_PATH),
            "note": "Ralph loop pass produces planning/report artifacts plus governed dispatch claim state; rerun the pass after deleting the artifacts if needed.",
        },
        duration=time.perf_counter() - started,
        operator_visible_summary=(
            f"Ralph loop selected {report['loop_state']['selected_workstream']} "
            f"under {report['loop_state']['current_loop_family']} "
            f"with evidence {report['loop_state']['evidence_freshness']} "
            f"and claim {governed_dispatch_claim.get('current_task_id') or 'idle'} "
            f"via {governed_dispatch_execution.get('status') or 'idle'}."
        ),
    )
    automation_feedback_summary, emit_result = asyncio.run(
        _capture_automation_feedback_and_emit(record)
    )
    autonomous_queue_summary.update(
        {
            "last_outcome": automation_feedback_summary.get("dispatch_last_outcome"),
            "last_success_at": automation_feedback_summary.get("dispatch_last_success_at"),
            "recent_dispatch_outcome_count": int(automation_feedback_summary.get("recent_dispatch_outcome_count") or 0),
            "recent_dispatch_outcomes": list(automation_feedback_summary.get("recent_dispatch_outcomes") or []),
        }
    )
    dispatch_authority["automation_feedback_state"] = automation_feedback_summary["feedback_state"]
    report["automation_feedback_summary"] = automation_feedback_summary
    final_continuity_state = _build_ralph_continuity_state(
        previous_continuity_state,
        automation_feedback_summary,
        governed_dispatch_claim,
        continuity_status,
        generated_at=generated_at,
        continuity_policy=continuity_policy,
        reopened_task_ids=reopened_task_ids,
    )
    RALPH_CONTINUITY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(RALPH_CONTINUITY_STATE_PATH, final_continuity_state)
    report["continuity"] = final_continuity_state
    report["continue_allowed"] = bool(final_continuity_state.get("continue_allowed"))
    report["stop_state"] = str(final_continuity_state.get("current_stop_state") or "none")
    report["stop_reason"] = str(final_continuity_state.get("current_stop_reason") or "").strip() or None
    report["next_unblocked_candidate"] = dict(final_continuity_state.get("next_unblocked_candidate") or {})
    report["next_deferred_family_id"] = str(final_continuity_state.get("next_deferred_family_id") or "").strip() or None
    report["loop_state"]["continue_allowed"] = report["continue_allowed"]
    report["loop_state"]["stop_state"] = report["stop_state"]
    report["loop_state"]["stop_reason"] = report["stop_reason"]
    if automation_feedback_summary.get("anti_spin_state") == "spin_detected":
        dispatch_authority_block = report.setdefault("dispatch_authority", {})
        governed_claim_block = report.setdefault("governed_dispatch_claim", {})
        governed_execution_block = report.setdefault("governed_dispatch_execution", {})
        dispatch_authority_block["anti_spin_state"] = "spin_detected"
        dispatch_authority_block["anti_spin_next_action"] = (
            governed_claim_block.get("on_deck_task_id") or "operator_review_required"
        )
        governed_claim_block["anti_spin_state"] = "spin_detected"
        governed_execution_block["anti_spin_state"] = "spin_detected"
        if str(governed_execution_block.get("status") or "") == "already_dispatched":
            governed_execution_block["status"] = "spin_detected"
    report["automation_record_persisted"] = emit_result.persisted
    report["automation_record_error"] = emit_result.error
    report["runtime_packet_inbox"] = build_runtime_packet_inbox(runtime_packets_payload)
    report["finish_scoreboard"] = build_finish_scoreboard(
        report,
        publication_deferred_queue,
        report["runtime_packet_inbox"],
    )
    report["executive_brief"] = _build_executive_brief(report, continuity_policy)
    _write_json(REPORT_PATH, report)

    print(json.dumps(report, indent=2))
    validation_passed = report["validation"]["all_passed"]
    if validation_passed is False:
        return 1
    refresh_failed = any(result["returncode"] != 0 for result in refresh_results)
    return 1 if refresh_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
