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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from automation_records import AutomationRunRecord, emit_automation_run_record, read_recent_automation_run_records

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
BURN_REGISTRY_PATH = CONFIG_DIR / "subscription-burn-registry.json"
PROVIDER_CATALOG_PATH = CONFIG_DIR / "provider-catalog.json"
APPROVAL_MATRIX_PATH = CONFIG_DIR / "approval-matrix.json"
SAFE_SURFACE_STATE_PATH = Path("C:/Users/Shaun/.codex/control/safe-surface-state.json")
SAFE_SURFACE_QUEUE_PATH = Path("C:/Users/Shaun/.codex/control/safe-surface-queue.json")

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
    if not records:
        feedback_state = "quiet"
    elif failure_count and not success_count:
        feedback_state = "degraded"
    elif failure_count:
        feedback_state = "mixed"
    else:
        feedback_state = "healthy"

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


def _build_ranked_autonomous_queue(
    queue: dict[str, Any],
    workstream_rows: list[dict[str, Any]],
    completion_program: dict[str, Any],
    burn_registry: dict[str, Any],
    work_economy_detail: dict[str, Any],
    provider_gate_detail: dict[str, Any],
    quota_truth: dict[str, Any],
    capacity_telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = [
        *_build_workstream_autonomous_items(workstream_rows, quota_truth, capacity_telemetry),
        *_build_burn_class_autonomous_items(burn_registry, work_economy_detail),
        *_build_safe_surface_autonomous_items(queue),
        *_build_provider_gate_item(completion_program, provider_gate_detail),
    ]
    rows.sort(
        key=lambda item: (
            0 if bool(item.get("dispatchable")) else 1,
            -float(item.get("ranking_score") or 0),
            str(item.get("title") or ""),
        )
    )
    return rows[:12]


def _build_autonomous_queue_summary(ranked_autonomous_queue: list[dict[str, Any]]) -> dict[str, Any]:
    dispatchable = [item for item in ranked_autonomous_queue if bool(item.get("dispatchable"))]
    blocked = [item for item in ranked_autonomous_queue if not bool(item.get("dispatchable"))]
    top_dispatchable = dispatchable[0] if dispatchable else None
    return {
        "queue_count": len(ranked_autonomous_queue),
        "dispatchable_queue_count": len(dispatchable),
        "blocked_queue_count": len(blocked),
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
        if not bool(item.get("dispatchable")):
            continue
        approved_mutation_class = str(item.get("approved_mutation_class") or "").strip()
        if approved_mutation_class not in approved_mutation_classes:
            continue
        if approved_mutation_class == "auto_harvest" and not work_economy_ready_now:
            continue
        eligible.append(item)
    return eligible, approval_classes


def _build_governed_dispatch_claim(
    ranked_autonomous_queue: list[dict[str, Any]],
    dispatch_authority: dict[str, Any],
    approval_matrix: dict[str, Any],
    safe_surface_state: dict[str, Any],
    *,
    generated_at: str,
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
    on_deck_item = eligible_items[1] if len(eligible_items) > 1 else None

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
        "preferred_lane_family": str(top_item.get("preferred_lane_family") or "").strip() or None,
        "fallback_lane_family": str(top_item.get("fallback_lane_family") or "").strip() or None,
        "proof_command_or_eval_surface": str(top_item.get("proof_command_or_eval_surface") or "").strip() or None,
        "closure_rule": str(top_item.get("closure_rule") or "").strip() or None,
        "blocking_reason": str(top_item.get("blocking_reason") or "").strip() or None,
        "capacity_signal": dict(top_item.get("capacity_signal") or {}),
        "on_deck_task_id": str(on_deck_item.get("task_id") or "").strip() or None,
        "on_deck_task_title": str(on_deck_item.get("title") or "").strip() or None,
        "on_deck_lane_family": str(on_deck_item.get("preferred_lane_family") or "").strip() or None,
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


def _build_next_actions(
    selected_family: str,
    selected_workstream: dict[str, Any],
    ranked_autonomous_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if selected_family == "governor_scheduling":
        for item in [row for row in ranked_autonomous_queue if bool(row.get("dispatchable"))][:3]:
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
) -> dict[str, Any]:
    top_queue_item = next(
        (row for row in ranked_autonomous_queue if bool(row.get("dispatchable"))),
        ranked_autonomous_queue[0] if ranked_autonomous_queue else None,
    )
    top_task_id = (
        str(autonomous_queue_summary.get("top_dispatchable_task_id") or "").strip()
        or str((top_queue_item or {}).get("task_id") or "").strip()
        or str(selected_workstream.get("id") or "").strip()
        or None
    )
    top_task_title = (
        str(autonomous_queue_summary.get("top_dispatchable_title") or "").strip()
        or str((top_queue_item or {}).get("title") or "").strip()
        or str(selected_workstream.get("title") or "").strip()
        or None
    )
    top_task = (
        {
            "id": top_task_id,
            "title": top_task_title,
            "dispatch_ready": bool((top_queue_item or {}).get("dispatchable")),
            "preferred_lane_family": str((top_queue_item or {}).get("preferred_lane_family") or "").strip() or None,
            "approved_mutation_class": str((top_queue_item or {}).get("approved_mutation_class") or "").strip() or None,
            "value_class": str((top_queue_item or {}).get("value_class") or "").strip() or None,
            "risk_class": str((top_queue_item or {}).get("risk_class") or "").strip() or None,
            "source": "ranked_autonomous_queue" if top_queue_item else "selected_workstream",
        }
        if top_task_id or top_task_title
        else None
    )
    return {
        "loop_mode": selected_family,
        "top_task": top_task,
        "autonomous_queue": ranked_autonomous_queue,
        "dispatchable_queue_count": int(autonomous_queue_summary.get("dispatchable_queue_count") or 0),
        "provider_gate_state": str(dispatch_authority.get("provider_gate_state") or "").strip() or None,
        "work_economy_status": str(dispatch_authority.get("work_economy_status") or "").strip() or None,
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
        capacity_telemetry=capacity_telemetry,
    )
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
    generated_at = _iso_now()
    governed_dispatch_claim = _build_governed_dispatch_claim(
        ranked_autonomous_queue,
        dispatch_authority,
        approval_matrix,
        safe_surface_state,
        generated_at=generated_at,
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
        },
        **_build_operator_facing_state_aliases(
            selected_family,
            selected_workstream,
            ranked_autonomous_queue,
            autonomous_queue_summary,
            dispatch_authority,
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
    report["automation_record_persisted"] = emit_result.persisted
    report["automation_record_error"] = emit_result.error
    _write_json(REPORT_PATH, report)

    print(json.dumps(report, indent=2))
    validation_passed = report["validation"]["all_passed"]
    if validation_passed is False:
        return 1
    refresh_failed = any(result["returncode"] != 0 for result in refresh_results)
    return 1 if refresh_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
