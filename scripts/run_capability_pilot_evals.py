#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry


AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"
if str(AGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(AGENTS_SRC))

from athanor_agents.operator_tests import (
    FLOW_RUNNERS,
    _build_operator_tests_status,
    run_operator_tests,
)


OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-evals.json"
PILOT_FORMAL_PREFLIGHT_PATH = (
    REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-formal-preflight.json"
)
DEFAULT_RUN_IDS = [
    "goose-operator-shell-lane-eval-2026q2",
    "openhands-bounded-worker-lane-eval-2026q2",
    "letta-memory-plane-eval-2026q2",
    "agt-policy-plane-eval-2026q2",
    "agt-policy-plane-eval-2026q2-degraded-fallback",
]
FALLBACK_FLOW_BY_RUN = {
    "goose-operator-shell-lane-eval-2026q2": "goose_operator_shell",
    "openhands-bounded-worker-lane-eval-2026q2": "openhands_bounded_worker",
    "letta-memory-plane-eval-2026q2": "letta_memory_plane",
    "agt-policy-plane-eval-2026q2": "agt_policy_plane",
    "agt-policy-plane-eval-2026q2-degraded-fallback": "agt_policy_plane",
}


def _tooling_index(host_id: str) -> dict[str, dict[str, Any]]:
    tooling_inventory = load_registry("tooling-inventory.json")
    for host in tooling_inventory.get("hosts", []):
        if str(host.get("id") or "").strip().lower() != host_id.lower():
            continue
        return {
            str(tool.get("command") or "").strip(): dict(tool)
            for tool in host.get("tools", [])
            if isinstance(tool, dict) and str(tool.get("command") or "").strip()
        }
    return {}


def _current_local_command_state(command: str) -> dict[str, Any]:
    local_path = shutil.which(command)
    return {
        "command": command,
        "available_locally": bool(local_path),
        "local_path": local_path,
    }


def _select_runs(selected_run_ids: list[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    eval_ledger = load_registry("eval-run-ledger.json")
    capability_registry = load_registry("capability-adoption-registry.json")
    capability_map = {
        str(capability.get("id") or "").strip(): dict(capability)
        for capability in capability_registry.get("capabilities", [])
        if isinstance(capability, dict) and str(capability.get("id") or "").strip()
    }
    run_ids = set(selected_run_ids or DEFAULT_RUN_IDS)
    runs = [
        dict(run)
        for run in eval_ledger.get("runs", [])
        if isinstance(run, dict) and str(run.get("run_id") or "").strip() in run_ids
    ]
    return runs, capability_map


def _flow_id_for_run(run: dict[str, Any]) -> str:
    configured = str(run.get("operator_test_flow_id") or "").strip()
    if configured:
        return configured
    return FALLBACK_FLOW_BY_RUN.get(str(run.get("run_id") or "").strip(), "")


def _formal_eval_scaffold(run: dict[str, Any]) -> dict[str, Any]:
    promptfoo_path = str(run.get("promptfoo_config_path") or "").strip() or None
    benchmark_spec_path = str(run.get("benchmark_spec_path") or "").strip() or None
    if promptfoo_path:
        return {
            "type": "promptfoo",
            "path": promptfoo_path,
            "exists": Path(promptfoo_path).exists(),
        }
    if benchmark_spec_path:
        return {
            "type": "benchmark_spec",
            "path": benchmark_spec_path,
            "exists": Path(benchmark_spec_path).exists(),
        }
    return {"type": None, "path": None, "exists": False}


def _formal_preflight_index() -> dict[str, dict[str, Any]]:
    if not PILOT_FORMAL_PREFLIGHT_PATH.exists():
        return {}
    payload = json.loads(PILOT_FORMAL_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    return {
        str(record.get("run_id") or "").strip(): dict(record)
        for record in payload.get("records", [])
        if isinstance(record, dict) and str(record.get("run_id") or "").strip()
    }


def _find_flow(snapshot: dict[str, Any], flow_id: str) -> dict[str, Any]:
    return next(
        (
            dict(flow)
            for flow in snapshot.get("flows", [])
            if isinstance(flow, dict) and str(flow.get("id") or "").strip() == flow_id
        ),
        {},
    )


def _pilot_eval_status(flow: dict[str, Any], blocking_reasons: list[str]) -> str:
    if not flow:
        return "not_run"
    outcome = str(flow.get("last_outcome") or "").strip().lower()
    if outcome == "passed":
        return "passed"
    if outcome == "blocked" or blocking_reasons:
        return "blocked"
    return "failed"


async def _run_operator_snapshot(flow_ids: list[str], actor: str) -> dict[str, Any]:
    try:
        snapshot = await run_operator_tests(flow_ids=flow_ids, actor=actor)
        snapshot["runner_mode"] = "persistent"
        return snapshot
    except Exception as exc:
        exc_module = str(type(exc).__module__).lower()
        if "redis" not in exc_module and "authentication required" not in str(exc).lower():
            raise

        flows: list[dict[str, Any]] = []
        for flow_id in flow_ids:
            result = await FLOW_RUNNERS[flow_id]()
            flows.append(result.to_dict())
        flows.sort(key=lambda item: str(item.get("title") or ""))
        status, last_outcome = _build_operator_tests_status(flows)
        last_run_at = max(
            (str(flow.get("last_run_at") or "") for flow in flows if str(flow.get("last_run_at") or "").strip()),
            default=None,
        )
        return {
            "generated_at": iso_now(),
            "status": status,
            "last_outcome": last_outcome,
            "last_run_at": last_run_at,
            "flow_count": len(flows),
            "flows": flows,
            "runner_mode": "non_persistent_fallback",
            "runner_error": f"{type(exc).__name__}: {exc}",
            "actor": actor,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run capability-pilot operator tests and write machine-readable eval evidence."
    )
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--host-id", default="desk")
    parser.add_argument("--actor", default="capability-pilot-evals")
    parser.add_argument("--write", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    runs, capability_map = _select_runs([str(item).strip() for item in args.run_id if str(item).strip()])
    flow_ids = [
        flow_id
        for flow_id in (_flow_id_for_run(run) for run in runs)
        if flow_id
    ]
    snapshot = asyncio.run(_run_operator_snapshot(sorted(set(flow_ids)), args.actor)) if flow_ids else {
        "generated_at": iso_now(),
        "status": "configured",
        "last_outcome": "not_run",
        "flow_count": 0,
        "flows": [],
    }

    tooling_index = _tooling_index(args.host_id)
    preflight_index = _formal_preflight_index()
    promptfoo_command_available = bool(shutil.which("promptfoo") or shutil.which("npx"))
    records: list[dict[str, Any]] = []

    for run in runs:
        run_id = str(run.get("run_id") or "").strip()
        capability_id = str(run.get("initiative_id") or "").strip()
        capability = capability_map.get(capability_id, {})
        execution_requirements = dict(run.get("execution_requirements") or {})
        required_commands = [
            str(item).strip()
            for item in execution_requirements.get("required_commands", [])
            if str(item).strip()
        ]
        command_checks: list[dict[str, Any]] = []
        for command in required_commands:
            inventory_tool = tooling_index.get(command)
            local_state = _current_local_command_state(command)
            command_checks.append(
                {
                    "command": command,
                    "inventory_status": str(inventory_tool.get("status") or "missing") if inventory_tool else "missing",
                    "inventory_version": (
                        str(inventory_tool.get("version") or "") or None
                        if inventory_tool
                        else None
                    ),
                    "available_locally": local_state["available_locally"],
                    "local_path": local_state["local_path"],
                }
            )

        flow_id = _flow_id_for_run(run)
        flow = _find_flow(snapshot, flow_id)
        blocking_reasons = [
            str(item).strip()
            for item in dict(flow.get("details") or {}).get("blocking_reasons", [])
            if str(item).strip()
        ]
        formal_eval_scaffold = _formal_eval_scaffold(run)
        formal_preflight = preflight_index.get(run_id, {})
        preflight_status = str(formal_preflight.get("preflight_status") or "not_run")
        preflight_blockers = [
            str(item).strip()
            for item in formal_preflight.get("blocking_reasons", [])
            if str(item).strip()
        ]
        eval_status = _pilot_eval_status(flow, blocking_reasons)
        proof_tier = (
            "operator_smoke_plus_formal_preflight"
            if eval_status == "passed" and formal_eval_scaffold["exists"] and preflight_status == "ready"
            else "operator_smoke_plus_formal_scaffold"
            if eval_status == "passed" and formal_eval_scaffold["exists"]
            else "operator_smoke_only"
            if eval_status == "passed"
            else "blocked"
            if eval_status == "blocked"
            else "not_run"
            if eval_status == "not_run"
            else "failed"
        )

        records.append(
            {
                "run_id": run_id,
                "initiative_id": capability_id,
                "capability_label": str(capability.get("label") or capability_id),
                "task_class": str(run.get("task_class") or ""),
                "corpus_id": str(run.get("corpus_id") or ""),
                "wrapper_mode": str(run.get("wrapper_mode") or ""),
                "operator_test_flow_id": flow_id or None,
                "pilot_eval_status": eval_status,
                "last_outcome": str(flow.get("last_outcome") or "not_run"),
                "operator_test_status": str(flow.get("status") or "configured"),
                "captured_at": str(flow.get("last_run_at") or snapshot.get("generated_at") or iso_now()),
                "blocking_reasons": blocking_reasons,
                "required_commands": required_commands,
                "command_checks": command_checks,
                "preferred_hosts": [
                    str(item).strip()
                    for item in execution_requirements.get("preferred_hosts", [])
                    if str(item).strip()
                ],
                "request_surface_hint": str(execution_requirements.get("request_surface_hint") or "").strip() or None,
                "linked_promotion_packet": str(run.get("linked_promotion_packet") or "").strip() or None,
                "evidence_artifacts": list(run.get("evidence_artifacts") or []),
                "formal_eval_scaffold_type": formal_eval_scaffold["type"],
                "formal_eval_scaffold_path": formal_eval_scaffold["path"],
                "formal_eval_scaffold_exists": formal_eval_scaffold["exists"],
                "formal_preflight_status": preflight_status,
                "formal_preflight_blocking_reasons": preflight_blockers,
                "formal_preflight_captured_at": str(formal_preflight.get("captured_at") or "") or None,
                "promptfoo_command_available": promptfoo_command_available,
                "proof_tier": proof_tier,
                "operator_test_record": flow,
                "runner_mode": str(snapshot.get("runner_mode") or "unknown"),
            }
        )

    summary = {
        "total": len(records),
        "passed": sum(1 for item in records if item["pilot_eval_status"] == "passed"),
        "blocked": sum(1 for item in records if item["pilot_eval_status"] == "blocked"),
        "failed": sum(1 for item in records if item["pilot_eval_status"] == "failed"),
        "not_run": sum(1 for item in records if item["pilot_eval_status"] == "not_run"),
        "operator_smoke_only": sum(1 for item in records if item["proof_tier"] == "operator_smoke_only"),
        "ready_for_formal_eval": sum(
            1 for item in records if item["proof_tier"] == "operator_smoke_plus_formal_preflight"
        ),
    }
    payload = {
        "version": "2026-04-11.1",
        "generated_at": iso_now(),
        "host_id": args.host_id,
        "source_of_truth": "reports/truth-inventory/capability-pilot-evals.json",
        "summary": summary,
        "records": records,
    }
    dump_json(args.write, payload)
    append_history(
        "capability-pilot-evals",
        {
            "generated_at": payload["generated_at"],
            "source_of_truth": payload["source_of_truth"],
            "host_id": args.host_id,
            "summary": summary,
            "run_ids": [record["run_id"] for record in records],
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
