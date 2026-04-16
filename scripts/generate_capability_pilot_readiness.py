from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry, resolve_external_path


DEVSTACK_ROOT = resolve_external_path("C:/athanor-devstack")
DEVSTACK_LANE_REGISTRY_PATH = DEVSTACK_ROOT / "configs" / "devstack-capability-lane-registry.json"
DEVSTACK_PACKET_DIR = DEVSTACK_ROOT / "docs" / "promotion-packets"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-readiness.json"
PILOT_EVALS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-evals.json"
PILOT_FORMAL_PREFLIGHT_PATH = (
    REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-formal-preflight.json"
)
GOOSE_BOUNDARY_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "goose-boundary-evidence.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tooling_index(host_id: str) -> dict[str, dict[str, Any]]:
    tooling_inventory = load_registry("tooling-inventory.json")
    for host in tooling_inventory.get("hosts", []):
        if str(host.get("id") or "").strip() != host_id:
            continue
        return {
            str(tool.get("command") or "").strip(): dict(tool)
            for tool in host.get("tools", [])
            if isinstance(tool, dict) and str(tool.get("command") or "").strip()
        }
    return {}


def _capability_run_index() -> dict[str, list[dict[str, Any]]]:
    eval_runs = load_registry("eval-run-ledger.json").get("runs", [])
    index: dict[str, list[dict[str, Any]]] = {}
    for run in eval_runs:
        if not isinstance(run, dict):
            continue
        key = str(run.get("initiative_id") or "").strip()
        if not key:
            continue
        index.setdefault(key, []).append(dict(run))
    return index


def _formal_eval_index() -> dict[str, dict[str, Any]]:
    eval_runs = load_registry("eval-run-ledger.json").get("runs", [])
    index: dict[str, dict[str, Any]] = {}
    for run in eval_runs:
        if not isinstance(run, dict):
            continue
        run_id = str(run.get("run_id") or "").strip()
        artifact_path = str(run.get("formal_eval_artifact_path") or "").strip()
        if not run_id or not artifact_path:
            continue
        path = resolve_external_path(artifact_path)
        if not path.exists():
            continue
        payload = _load_json(path)
        payload["_artifact_path"] = str(path)
        index[run_id] = payload
    return index


def _pilot_eval_index() -> dict[str, list[dict[str, Any]]]:
    if not PILOT_EVALS_PATH.exists():
        return {}
    payload = _load_json(PILOT_EVALS_PATH)
    index: dict[str, list[dict[str, Any]]] = {}
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        key = str(record.get("initiative_id") or "").strip()
        if not key:
            continue
        index.setdefault(key, []).append(dict(record))
    return index


def _pilot_capability_ids(
    run_index: dict[str, list[dict[str, Any]]],
    pilot_eval_index: dict[str, list[dict[str, Any]]],
) -> set[str]:
    capability_ids = {
        capability_id
        for capability_id in pilot_eval_index
        if capability_id.strip()
    }
    for capability_id, runs in run_index.items():
        if not capability_id.strip():
            continue
        if any(str(run.get("operator_test_flow_id") or "").strip() for run in runs):
            capability_ids.add(capability_id)
    return capability_ids


def _formal_preflight_index() -> dict[str, dict[str, Any]]:
    if not PILOT_FORMAL_PREFLIGHT_PATH.exists():
        return {}
    payload = _load_json(PILOT_FORMAL_PREFLIGHT_PATH)
    return {
        str(record.get("run_id") or "").strip(): dict(record)
        for record in payload.get("records", [])
        if isinstance(record, dict) and str(record.get("run_id") or "").strip()
    }


def _current_local_command_state(command: str) -> dict[str, Any]:
    path = shutil.which(command)
    return {
        "command": command,
        "available_locally": bool(path),
        "local_path": path,
    }


def _formal_eval_scaffold(run: dict[str, Any]) -> dict[str, Any]:
    promptfoo_path = str(run.get("promptfoo_config_path") or "").strip() or None
    benchmark_spec_path = str(run.get("benchmark_spec_path") or "").strip() or None
    if promptfoo_path:
        path = resolve_external_path(promptfoo_path)
        return {"type": "promptfoo", "path": str(path), "exists": path.exists()}
    if benchmark_spec_path:
        path = resolve_external_path(benchmark_spec_path)
        return {"type": "benchmark_spec", "path": str(path), "exists": path.exists()}
    return {"type": None, "path": None, "exists": False}


def _goose_boundary_evidence_summary() -> dict[str, Any]:
    if not GOOSE_BOUNDARY_EVIDENCE_PATH.exists():
        return {
            "path": str(GOOSE_BOUNDARY_EVIDENCE_PATH),
            "present": False,
            "complete": False,
            "missing_sections": [
                "## Dashboard-Routed Shell Evidence",
                "## MCP Allowlist Proof",
                "## Failure-Fallback Proof",
                "## Closure Status",
            ],
        }
    text = GOOSE_BOUNDARY_EVIDENCE_PATH.read_text(encoding="utf-8")
    required_sections = [
        "## Dashboard-Routed Shell Evidence",
        "## MCP Allowlist Proof",
        "## Failure-Fallback Proof",
        "## Closure Status",
    ]
    missing_sections = [section for section in required_sections if section not in text]
    return {
        "path": str(GOOSE_BOUNDARY_EVIDENCE_PATH),
        "present": True,
        "complete": not missing_sections,
        "missing_sections": missing_sections,
    }


def _formal_preflight_details(blocking_reasons: list[str], scaffold_type: str | None) -> dict[str, Any]:
    missing_commands = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("missing_command:") and ":" in reason
        }
    )
    missing_env_vars = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("missing_env:") and ":" in reason
        }
    )
    missing_fixture_files = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("missing_fixture:") and ":" in reason
        }
    )
    invalid_fixture_files = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("invalid_fixture:") and ":" in reason
        }
    )
    missing_result_files = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("missing_result:") and ":" in reason
        }
    )
    runtime_probe_blockers = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if (
                reason.startswith("probe_timeout:")
                or reason.startswith("probe_failed:")
                or reason.startswith("probe_unexpected_output:")
            )
            and ":" in reason
        }
    )
    promptfoo_runtime_blockers = sorted(
        {
            reason.split(":", 1)[1]
            for reason in blocking_reasons
            if reason.startswith("unsupported_promptfoo_node_runtime:") and ":" in reason
        }
    )

    blocker_class = None
    next_gate = None
    runner_support = (
        "promptfoo_supported"
        if scaffold_type == "promptfoo"
        else "benchmark_spec_manual_review_supported"
    )
    if missing_commands:
        blocker_class = "missing_command"
        next_gate = f"Install or expose {', '.join(f'`{item}`' for item in missing_commands)} on the preferred pilot host."
    elif promptfoo_runtime_blockers:
        blocker_class = "runtime_dependency_blocked"
        next_gate = (
            f"Upgrade the local Node.js runtime to a Promptfoo-supported version before treating this lane as formal-eval-ready. Current runtime: {', '.join(f'`{item}`' for item in promptfoo_runtime_blockers)}."
        )
    elif runtime_probe_blockers:
        blocker_class = "runtime_probe_blocked"
        next_gate = (
            f"Fix the headless pilot command probe for {', '.join(f'`{item}`' for item in runtime_probe_blockers)} before treating the lane as formal-eval-ready."
        )
        if missing_env_vars:
            next_gate += f" Missing envs still recorded: {', '.join(f'`{item}`' for item in missing_env_vars)}."
    elif missing_env_vars:
        blocker_class = "env_wiring"
        next_gate = f"Wire the required formal-eval env vars: {', '.join(f'`{item}`' for item in missing_env_vars)}."
    elif missing_fixture_files:
        blocker_class = "fixture_required"
        next_gate = f"Capture real fixture artifacts at {', '.join(f'`{item}`' for item in missing_fixture_files)}."
    elif invalid_fixture_files:
        blocker_class = "fixture_contract_invalid"
        next_gate = f"Fix the recorded fixture contract violations in {', '.join(f'`{item}`' for item in invalid_fixture_files)}."
    elif missing_result_files:
        blocker_class = "result_artifact_missing"
        next_gate = f"Capture the required result artifacts at {', '.join(f'`{item}`' for item in missing_result_files)}."
    elif blocking_reasons:
        blocker_class = "other_preflight_blocker"
        next_gate = "Clear the recorded formal-preflight blockers before attempting formal eval."

    return {
        "blocker_class": blocker_class,
        "missing_commands": missing_commands,
        "missing_env_vars": missing_env_vars,
        "missing_fixture_files": missing_fixture_files,
        "invalid_fixture_files": invalid_fixture_files,
        "missing_result_files": missing_result_files,
        "runtime_probe_blockers": runtime_probe_blockers,
        "promptfoo_runtime_blockers": promptfoo_runtime_blockers,
        "next_gate": next_gate,
        "runner_support": runner_support,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build capability pilot readiness from lane, packet, eval, and tooling truth.")
    parser.add_argument("--host-id", default="desk")
    parser.add_argument("--write", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    lane_registry = _load_json(DEVSTACK_LANE_REGISTRY_PATH)
    capability_registry = load_registry("capability-adoption-registry.json")
    capability_map = {
        str(cap.get("id") or "").strip(): dict(cap)
        for cap in capability_registry.get("capabilities", [])
        if isinstance(cap, dict) and str(cap.get("id") or "").strip()
    }
    run_index = _capability_run_index()
    formal_eval_index = _formal_eval_index()
    pilot_eval_index = _pilot_eval_index()
    formal_preflight_index = _formal_preflight_index()
    pilot_capability_ids = _pilot_capability_ids(run_index, pilot_eval_index)
    tooling_index = _tooling_index(args.host_id)

    records: list[dict[str, Any]] = []
    for lane in lane_registry.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        capability_id = str(lane.get("linked_capability_id") or "").strip()
        if not capability_id:
            continue
        lane_status = str(lane.get("lane_status") or "").strip()
        if lane_status != "drafting_packet" and capability_id not in pilot_capability_ids:
            continue
        capability = capability_map.get(capability_id, {})
        runs = run_index.get(capability_id, [])
        pilot_evals = pilot_eval_index.get(capability_id, [])
        latest_pilot_eval = pilot_evals[-1] if pilot_evals else {}
        packet_path = Path(str(lane.get("promotion_packet_path") or "").strip()) if lane.get("promotion_packet_path") else None

        execution_requirements = dict(runs[0].get("execution_requirements") or {}) if runs else {}
        formal_eval_scaffold = _formal_eval_scaffold(runs[0]) if runs else {"type": None, "path": None, "exists": False}
        configured_run_id = str(runs[-1].get("run_id") or "").strip() if runs else ""
        latest_run_id = str(latest_pilot_eval.get("run_id") or configured_run_id).strip() if (latest_pilot_eval or configured_run_id) else ""
        formal_preflight = formal_preflight_index.get(latest_run_id, {}) if latest_run_id else {}
        formal_eval = formal_eval_index.get(latest_run_id, {}) if latest_run_id else {}
        goose_boundary_evidence = _goose_boundary_evidence_summary() if capability_id == "goose-operator-shell" else {}
        required_commands = [
            str(item).strip()
            for item in execution_requirements.get("required_commands", [])
            if str(item).strip()
        ]

        command_records = []
        blockers: list[str] = []
        for command in required_commands:
            inventory_tool = tooling_index.get(command)
            local_state = _current_local_command_state(command)
            installed_in_inventory = str(inventory_tool.get("status") or "") == "installed" if inventory_tool else False
            if not installed_in_inventory and not local_state["available_locally"]:
                blockers.append(f"missing_command:{command}")
            command_records.append(
                {
                    "command": command,
                    "inventory_status": str(inventory_tool.get("status") or "missing") if inventory_tool else "missing",
                    "inventory_version": str(inventory_tool.get("version") or "") or None if inventory_tool else None,
                    "available_locally": local_state["available_locally"],
                    "local_path": local_state["local_path"],
                }
            )

        if packet_path is None or not packet_path.exists():
            blockers.append("missing_packet")
        if not runs:
            blockers.append("missing_eval_run")

        latest_eval_status = str(latest_pilot_eval.get("pilot_eval_status") or "").strip()
        proof_tier = str(latest_pilot_eval.get("proof_tier") or "").strip() or None
        formal_preflight_status = str(formal_preflight.get("preflight_status") or "").strip() or None
        formal_eval_status = str(formal_eval.get("status") or "").strip() or None
        formal_eval_decision_reason = str(formal_eval.get("decision_reason") or "").strip() or None
        formal_eval_primary_failure_hint = str(formal_eval.get("promptfoo_primary_failure_hint") or "").strip() or None
        formal_eval_promptfoo_summary = dict(formal_eval.get("promptfoo_summary") or {}) if isinstance(formal_eval.get("promptfoo_summary"), dict) else {}
        manual_review_outcome = str(formal_eval.get("manual_review_outcome") or "").strip() or None
        manual_review_summary = str(formal_eval.get("manual_review_summary") or "").strip() or None
        manual_review_note_path = str(formal_eval.get("manual_review_note_path") or "").strip() or None
        formal_preflight_blockers = [
            str(item).strip()
            for item in formal_preflight.get("blocking_reasons", [])
            if str(item).strip()
        ]
        formal_preflight_details = _formal_preflight_details(
            formal_preflight_blockers,
            formal_eval_scaffold["type"],
        )
        surfaced_blockers = list(dict.fromkeys([*blockers, *formal_preflight_blockers]))
        if blockers or latest_eval_status in {"failed", "blocked"}:
            readiness_state = "blocked"
        elif formal_eval_status == "passed":
            readiness_state = "formal_eval_complete"
        elif formal_eval_status == "manual_review_pending":
            readiness_state = "manual_review_pending"
        elif formal_eval_status == "failed":
            readiness_state = "formal_eval_failed"
        elif latest_eval_status == "passed" and formal_eval_scaffold["exists"] and formal_preflight_status == "ready":
            readiness_state = "ready_for_formal_eval"
        elif latest_eval_status == "passed":
            readiness_state = "operator_smoke_only"
        else:
            readiness_state = "scaffold_only"

        if formal_eval_status == "passed":
            proof_tier = "formal_eval_complete"
        elif formal_eval_status == "manual_review_pending":
            proof_tier = "formal_eval_materialized_pending_review"
        elif formal_eval_status == "failed":
            proof_tier = "formal_eval_failed"

        next_formal_gate = formal_preflight_details["next_gate"]
        if formal_eval_status == "passed":
            next_formal_gate = "Formal eval is complete; move this lane to promotion or bounded retention decision."
        elif formal_eval_status == "manual_review_pending":
            next_formal_gate = "Complete the required manual contract review before counting this lane as formally evaluated."
        elif formal_eval_status == "failed":
            if manual_review_outcome == "rejected_as_redundant_for_current_stack":
                next_formal_gate = (
                    "Keep this lane below adapter work unless a second protocol-boundary scenario shows non-duplicative value over native Athanor policy."
                )
            elif formal_eval_primary_failure_hint:
                next_formal_gate = f"Resolve the recorded formal eval miss: {formal_eval_primary_failure_hint}"
            else:
                next_formal_gate = (
                    f"Resolve the recorded formal eval failure (`{formal_eval_decision_reason or 'formal_eval_failed'}`) and rerun the scaffold."
                )
        elif (
            formal_eval_scaffold["type"] == "benchmark_spec"
            and formal_preflight_status == "blocked"
            and next_formal_gate
        ):
            next_formal_gate = (
                f"{next_formal_gate} After the fixtures are valid, this lane still needs manual contract review of the emitted benchmark-spec artifact before it counts as formally evaluated."
            )
        elif formal_eval_scaffold["type"] == "benchmark_spec" and formal_preflight_status == "ready":
            next_formal_gate = (
                "Run manual contract-and-trace review or add benchmark-spec runner support before claiming formal eval readiness."
            )

        next_action = str(lane.get("next_action") or "")
        if formal_eval_status == "passed":
            next_action = "Advance this lane into packet review, promotion, or explicit bounded retention."
        elif formal_eval_status == "manual_review_pending":
            next_action = "Complete the benchmark-spec manual review and record the resulting keep, promote, or demote decision."
        elif formal_eval_status == "failed":
            if manual_review_outcome == "rejected_as_redundant_for_current_stack":
                next_action = (
                    "Leave this lane below adapter work on the current manual review, and only reopen it if a second protocol-boundary scenario proves unique value over native Athanor policy."
                )
            elif formal_eval_primary_failure_hint:
                next_action = f"Fix the remaining formal eval miss ({formal_eval_primary_failure_hint}) and rerun the formal comparison."
            else:
                next_action = (
                    f"Fix the current formal eval failure (`{formal_eval_decision_reason or 'formal_eval_failed'}`) and rerun the formal comparison."
                )

        records.append(
            {
                "capability_id": capability_id,
                "label": str(capability.get("label") or lane.get("title") or capability_id),
                "lane_status": str(lane.get("lane_status") or ""),
                "capability_stage": str(capability.get("stage") or lane.get("capability_stage") or ""),
                "host_id": args.host_id,
                "readiness_state": readiness_state,
                "blocking_reasons": surfaced_blockers,
                "required_commands": required_commands,
                "command_checks": command_records,
                "packet_path": str(packet_path) if packet_path else None,
                "eval_run_ids": [str(run.get("run_id") or "") for run in runs if str(run.get("run_id") or "").strip()],
                "latest_eval_run_id": str(latest_pilot_eval.get("run_id") or "").strip() or None,
                "latest_eval_status": latest_eval_status or None,
                "latest_eval_outcome": str(latest_pilot_eval.get("last_outcome") or "").strip() or None,
                "latest_eval_at": str(latest_pilot_eval.get("captured_at") or "").strip() or None,
                "proof_tier": proof_tier,
                "formal_eval_scaffold_type": formal_eval_scaffold["type"],
                "formal_eval_scaffold_path": formal_eval_scaffold["path"],
                "formal_eval_scaffold_exists": formal_eval_scaffold["exists"],
                "formal_eval_status": formal_eval_status,
                "formal_eval_decision_reason": formal_eval_decision_reason,
                "formal_eval_primary_failure_hint": formal_eval_primary_failure_hint,
                "formal_eval_promptfoo_summary": formal_eval_promptfoo_summary or None,
                "formal_eval_at": str(formal_eval.get("generated_at") or "").strip() or None,
                "formal_eval_result_path": str(formal_eval.get("_artifact_path") or "").strip() or None,
                "manual_review_outcome": manual_review_outcome,
                "manual_review_summary": manual_review_summary,
                "manual_review_note_path": manual_review_note_path,
                "formal_preflight_status": formal_preflight_status,
                "formal_preflight_blocking_reasons": formal_preflight_blockers,
                "formal_preflight_blocker_class": formal_preflight_details["blocker_class"],
                "formal_preflight_missing_commands": formal_preflight_details["missing_commands"],
                "formal_preflight_missing_env_vars": formal_preflight_details["missing_env_vars"],
                "formal_preflight_missing_fixture_files": formal_preflight_details["missing_fixture_files"],
                "formal_preflight_missing_result_files": formal_preflight_details["missing_result_files"],
                "formal_runner_support": formal_preflight_details["runner_support"],
                "formal_preflight_at": str(formal_preflight.get("captured_at") or "").strip() or None,
                "pilot_evidence_path": PILOT_EVALS_PATH.as_posix().replace("\\", "/") if latest_pilot_eval else None,
                "boundary_evidence_path": goose_boundary_evidence.get("path"),
                "boundary_evidence_present": goose_boundary_evidence.get("present"),
                "boundary_evidence_complete": goose_boundary_evidence.get("complete"),
                "boundary_evidence_missing_sections": goose_boundary_evidence.get("missing_sections"),
                "preferred_hosts": [
                    str(item).strip()
                    for item in execution_requirements.get("preferred_hosts", [])
                    if str(item).strip()
                ],
                "request_surface_hint": str(execution_requirements.get("request_surface_hint") or "").strip() or None,
                "next_action": next_action,
                "next_formal_gate": next_formal_gate,
            }
        )

    summary = {
        "total": len(records),
        "formal_eval_complete": sum(1 for item in records if item["readiness_state"] == "formal_eval_complete"),
        "formal_eval_failed": sum(1 for item in records if item["readiness_state"] == "formal_eval_failed"),
        "manual_review_pending": sum(1 for item in records if item["readiness_state"] == "manual_review_pending"),
        "ready_for_formal_eval": sum(1 for item in records if item["readiness_state"] == "ready_for_formal_eval"),
        "operator_smoke_only": sum(1 for item in records if item["readiness_state"] == "operator_smoke_only"),
        "scaffold_only": sum(1 for item in records if item["readiness_state"] == "scaffold_only"),
        "blocked": sum(1 for item in records if item["readiness_state"] == "blocked"),
    }
    payload = {
        "version": "2026-04-12.1",
        "generated_at": iso_now(),
        "host_id": args.host_id,
        "source_of_truth": "reports/truth-inventory/capability-pilot-readiness.json",
        "summary": summary,
        "records": records,
    }
    dump_json(args.write, payload)
    append_history(
        "capability-pilot-readiness",
        {
            "generated_at": payload["generated_at"],
            "source_of_truth": payload["source_of_truth"],
            "summary": summary,
            "host_id": args.host_id,
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
