#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from automation_records import AutomationRunRecord, emit_automation_run_record


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
REPORT_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"

REFRESH_COMMANDS: list[list[str]] = [
    [sys.executable, "scripts/collect_truth_inventory.py"],
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

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TERMINAL_EXECUTION_STATES = {"completed", "steady_state_monitoring"}
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


def _selected_loop_family(workstream_row: dict[str, Any], any_stale_evidence: bool) -> str:
    if any_stale_evidence:
        return "evidence_refresh"
    return str(workstream_row["workstream"].get("loop_family") or "governor_scheduling")


def _build_next_actions(selected_family: str, selected_workstream: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for command in LOOP_FAMILY_NEXT_COMMANDS.get(selected_family, []):
        actions.append({"type": "command", "command": command})
    for artifact in selected_workstream.get("evidence_artifacts", []):
        actions.append({"type": "artifact", "path": str(artifact)})
    return actions


def _sync_registry_loop_state(
    completion_program: dict[str, Any],
    autonomy_activation: dict[str, Any],
    selected_family: str,
    selected_workstream: dict[str, Any],
    any_stale_evidence: bool,
) -> None:
    selected_execution_state = str(selected_workstream.get("execution_state") or "")
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
        "next_action_family": str(selected_workstream.get("next_action_family") or ""),
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
    routing_policy = _load_yaml(REPO_ROOT / "projects" / "agents" / "config" / "subscription-routing-policy.yaml")
    truth_snapshot = _load_json(REPO_ROOT / "reports" / "truth-inventory" / "latest.json")
    now_ts = time.time()
    freshness_index = _artifact_freshness(now_ts)
    any_stale_evidence = any(row["stale"] for row in freshness_index.values())

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

    selected_row = _select_active_workstream(workstream_rows)
    selected_workstream = dict(selected_row["workstream"])
    selected_family = _selected_loop_family(selected_row, any_stale_evidence)
    selected_execution_state = str(selected_workstream.get("execution_state") or "")
    approval_required = bool(selected_workstream.get("approval_required"))

    _sync_registry_loop_state(
        completion_program=completion_program,
        autonomy_activation=autonomy_activation,
        selected_family=selected_family,
        selected_workstream=selected_workstream,
        any_stale_evidence=any_stale_evidence,
    )

    report = {
        "generated_at": _iso_now(),
        "source_of_truth": {
            "completion_program_registry": "config/automation-backbone/completion-program-registry.json",
            "autonomy_activation_registry": "config/automation-backbone/autonomy-activation-registry.json",
            "program_operating_system": "config/automation-backbone/program-operating-system.json",
            "routing_policy": "projects/agents/config/subscription-routing-policy.yaml",
            "status_doc": "STATUS.md",
            "backlog_doc": "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
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
            "next_action_family": str(selected_workstream.get("next_action_family") or ""),
            "execution_posture": (
                "steady_state"
                if selected_execution_state == "steady_state_monitoring"
                else "active_remediation"
            ),
        },
        "cadence": dict(operating_system.get("cadence") or {}),
        "ranking_axes": list((operating_system.get("backlog_policy") or {}).get("ranking_axes") or []),
        "provider_routing_defaults": {
            "task_classes": dict(routing_policy.get("task_classes") or {}),
            "quota_strategy": dict(routing_policy.get("quota_strategy") or {}),
        },
        "evidence_refresh": {
            "ran": not args.skip_refresh,
            "results": refresh_results,
        },
        "freshness": {
            "any_stale_evidence": any_stale_evidence,
            "artifacts": list(freshness_index.values()),
        },
        "truth_snapshot_collected_at": truth_snapshot.get("collected_at"),
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
        "next_actions": _build_next_actions(selected_family, selected_workstream),
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
    if isinstance(completion_program.get("ralph_loop"), dict):
        completion_program["ralph_loop"]["last_validation_run"] = report["generated_at"]
        _write_json(CONFIG_DIR / "completion-program-registry.json", completion_program)

    record = AutomationRunRecord(
        automation_id="ralph-loop",
        lane="ralph_loop",
        action_class="autonomous_planning",
        inputs={
            "refresh_commands": REFRESH_COMMANDS,
            "validation_commands": VALIDATION_COMMANDS,
            "report_path": str(REPORT_PATH),
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
        },
        rollback={
            "mode": "delete_artifact",
            "path": str(REPORT_PATH),
            "note": "Ralph loop pass produces planning/report artifacts only; rerun the pass after deleting the artifact if needed.",
        },
        duration=time.perf_counter() - started,
        operator_visible_summary=(
            f"Ralph loop selected {report['loop_state']['selected_workstream']} "
            f"under {report['loop_state']['current_loop_family']} "
            f"with evidence {report['loop_state']['evidence_freshness']}."
        ),
    )
    emit_result = asyncio.run(emit_automation_run_record(record))
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
