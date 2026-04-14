#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import run_gpu_scheduler_baseline_eval as baseline
from routing_contract_support import append_history, dump_json, iso_now


OUTPUT_PATH = (
    baseline.REPO_ROOT / "reports" / "truth-inventory" / "gpu-scheduler-promotion-eval.json"
)


def _promotion_status(
    *,
    scheduler_state_result: dict[str, Any],
    mutation_source_presence: dict[str, bool],
    mutation_runtime_presence: dict[str, bool],
    baseline_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if scheduler_state_result.get("status_code") != 200:
        blockers.append("scheduler-state-endpoint-absent-in-live-runtime")
    if scheduler_state_result.get("status_code") == 200 and not baseline._scheduler_write_capabilities_enabled(
        scheduler_state_result
    ):
        blockers.append("scheduler-write-capabilities-disabled-in-live-runtime")
    if not all(mutation_source_presence.values()):
        blockers.append("bounded-mutation-surface-absent-in-tracked-source")
    if not all(mutation_runtime_presence.values()):
        blockers.append("bounded-mutation-surface-absent-in-live-runtime")
    if list(baseline_summary.get("baseline_failures") or []):
        blockers.append("baseline-alignment-incomplete")
    status = "passed" if not blockers else "blocked"
    return status, blockers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded GPU scheduler promotion eval contract without mutating live runtime."
    )
    parser.add_argument("--base-url", default=baseline.DEFAULT_ORCHESTRATOR_BASE)
    parser.add_argument("--write", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    tracked = baseline._load_tracked_orchestrator()
    source_text = baseline.GPU_ORCH_MAIN.read_text(encoding="utf-8")
    live_status = baseline._http_get(f"{args.base_url}/status", timeout=20)
    live_zones = baseline._http_get(f"{args.base_url}/zones", timeout=20)
    scheduler_state = baseline._http_get(f"{args.base_url}/scheduler/state", timeout=20)
    mutation_probes = {
        endpoint_name: baseline._http_get(f"{args.base_url}{route_path}", timeout=20)
        for endpoint_name, route_path in baseline.REQUIRED_MUTATION_ENDPOINTS.items()
    }
    mutation_source_presence = {
        endpoint_name: baseline._route_exists_in_source(source_text, route_path)
        for endpoint_name, route_path in baseline.REQUIRED_MUTATION_ENDPOINTS.items()
    }
    mutation_runtime_presence = {
        endpoint_name: baseline._route_is_present_in_runtime(result)
        for endpoint_name, result in mutation_probes.items()
    }
    capacity_telemetry = baseline._load_capacity_telemetry()
    capacity_truth_check = baseline._build_capacity_truth_check(capacity_telemetry, scheduler_state)

    registry_map = baseline._load_model_registry_map()
    model_probes = baseline._probe_model_endpoints()
    registry_checks = [
        baseline._registry_check(lane_id, registry_map[lane_id], model_probes[lane_id])
        for lane_id in (
            "foundry-coordinator",
            "foundry-coder",
            "dev-embedding",
            "dev-reranker",
            "workshop-worker",
            "workshop-vision",
        )
        if lane_id in registry_map
    ]
    baseline_summary = baseline._build_summary(
        tracked,
        live_status,
        live_zones,
        scheduler_state,
        capacity_truth_check,
        mutation_source_presence,
        mutation_runtime_presence,
        registry_checks,
    )
    promotion_status, blockers = _promotion_status(
        scheduler_state_result=scheduler_state,
        mutation_source_presence=mutation_source_presence,
        mutation_runtime_presence=mutation_runtime_presence,
        baseline_summary=baseline_summary,
    )

    payload = {
        "version": "2026-04-11.1",
        "generated_at": iso_now(),
        "source_of_truth": "reports/truth-inventory/gpu-scheduler-promotion-eval.json",
        "initiative_id": "gpu-scheduler-extension",
        "run_id": "gpu-scheduler-extension-formal-eval-2026q2",
        "promotion_eval_status": promotion_status,
        "promotion_validity": (
            "valid" if promotion_status == "passed" else "requires_formal_eval_run"
        ),
        "blocking_reasons": blockers,
        "baseline_summary": baseline_summary,
        "capacity_truth_check": capacity_truth_check,
        "tracked_mutation_routes": mutation_source_presence,
        "live_scheduler_state": scheduler_state,
        "live_mutation_routes": mutation_runtime_presence,
        "live_mutation_probes": mutation_probes,
        "next_action": (
            "advance release tier and capture governed deploy evidence"
            if promotion_status == "passed"
            else "deploy /scheduler/state through the governed Foundry packet and keep the formal eval blocked until bounded mutation endpoints exist in tracked source and live runtime"
        ),
    }
    dump_json(args.write, payload)
    append_history(
        "capability-promotion-evals",
        {
            "generated_at": payload["generated_at"],
            "initiative_id": payload["initiative_id"],
            "run_id": payload["run_id"],
            "promotion_eval_status": payload["promotion_eval_status"],
            "promotion_validity": payload["promotion_validity"],
            "blocking_reasons": payload["blocking_reasons"],
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
