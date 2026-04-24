#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry


OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "gpu-scheduler-baseline-eval.json"
CAPACITY_TELEMETRY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json"
GPU_ORCH_SRC = REPO_ROOT / "projects" / "gpu-orchestrator" / "src"
GPU_ORCH_MAIN = GPU_ORCH_SRC / "gpu_orchestrator" / "main.py"
REQUIRED_MUTATION_ENDPOINTS = {
    "request": "/scheduler/request",
    "preload": "/scheduler/preload",
    "release": "/scheduler/release",
}
NON_DESTRUCTIVE_ROUTE_STATUS_CODES = {200, 202, 400, 401, 403, 405, 409, 422}

DEFAULT_ORCHESTRATOR_BASE = "http://192.168.1.244:9200"
MODEL_ENDPOINTS = {
    "foundry-coordinator": "http://192.168.1.244:8000/v1/models",
    "foundry-coder": "http://192.168.1.244:8100/v1/models",
    "dev-embedding": "http://192.168.1.189:8001/v1/models",
    "dev-reranker": "http://192.168.1.189:8003/v1/models",
    "workshop-worker": "http://192.168.1.225:8010/v1/models",
    "workshop-vision": "http://192.168.1.225:8012/v1/models",
}
IDLE_SLOT_STATES = {"IDLE", "SLEEPING_L1"}
SSH_BATCH_OPTIONS = (
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
)


def _perform_request(request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
    started_at = iso_now()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body_text = response.read().decode("utf-8", errors="replace")
            try:
                parsed_body: Any = json.loads(body_text)
            except json.JSONDecodeError:
                parsed_body = body_text
            return {
                "ok": True,
                "status_code": response.status,
                "started_at": started_at,
                "completed_at": iso_now(),
                "body": parsed_body,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_body = raw_body
        return {
            "ok": False,
            "status_code": exc.code,
            "started_at": started_at,
            "completed_at": iso_now(),
            "body": parsed_body,
            "error": f"HTTPError: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "started_at": started_at,
            "completed_at": iso_now(),
            "body": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _http_get(url: str, *, timeout: int = 20) -> dict[str, Any]:
    return _perform_request(urllib.request.Request(url, method="GET"), timeout=timeout)


def _ssh_probe(host: str, command: str) -> dict[str, Any]:
    started_at = iso_now()
    try:
        completed = subprocess.run(
            ["ssh", *SSH_BATCH_OPTIONS, host, command],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "returncode": None,
            "started_at": started_at,
            "completed_at": iso_now(),
            "stdout": "",
            "stderr": "",
            "error": f"FileNotFoundError: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "returncode": None,
            "started_at": started_at,
            "completed_at": iso_now(),
            "stdout": "",
            "stderr": "",
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "started_at": started_at,
        "completed_at": iso_now(),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "error": None if completed.returncode == 0 else completed.stderr.strip() or f"ssh exited {completed.returncode}",
    }


def _normalize_model_id(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("/models/"):
        normalized = normalized[len("/models/") :]
    return normalized


def _extract_model_id(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None

    data = body.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            model_id = str(first.get("id") or "").strip()
            if model_id:
                return model_id

    models = body.get("models")
    if isinstance(models, list) and models:
        first = models[0]
        if isinstance(first, dict):
            model_id = str(first.get("id") or first.get("name") or "").strip()
            if model_id:
                return model_id

    return None


def _load_tracked_orchestrator() -> dict[str, Any]:
    if str(GPU_ORCH_SRC) not in sys.path:
        sys.path.insert(0, str(GPU_ORCH_SRC))

    config_module = importlib.import_module("gpu_orchestrator.config")
    settings = getattr(config_module, "settings")
    source_text = GPU_ORCH_MAIN.read_text(encoding="utf-8")
    zone_defs = _extract_zone_definitions(source_text)

    return {
        "zone_names": sorted(zone_defs.keys()),
        "zone_count": len(zone_defs),
        "worker_runtime": zone_defs.get("worker", {}).get("runtime"),
        "worker_vllm_url": zone_defs.get("worker", {}).get("vllm_url"),
        "worker_ollama_url": zone_defs.get("worker", {}).get("ollama_url"),
        "endpoints": {
            "coordinator": settings.vllm_node1_url,
            "coder": settings.vllm_coder_url,
            "embedding": settings.vllm_node1_embed_url,
            "reranker": settings.vllm_reranker_url,
            "vision": settings.vllm_vision_url,
            "worker": settings.vllm_node2_url,
        },
        "dcgm_urls": {
            "node1": settings.dcgm_node1_url,
            "node2": settings.dcgm_node2_url,
            "node3": settings.dcgm_node3_url,
        },
        "scheduler_endpoint_in_source": "/scheduler/state" in source_text,
    }


def _extract_zone_definitions(source_text: str) -> dict[str, dict[str, Any]]:
    parsed = ast.parse(source_text)
    for node in parsed.body:
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == "ZONES" for target in node.targets):
                continue
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name) or node.target.id != "ZONES":
                continue
            value_node = node.value
        else:
            continue

        if not isinstance(value_node, ast.Dict):
            continue

        zone_defs: dict[str, dict[str, Any]] = {}
        for key_node, zone_value_node in zip(value_node.keys, value_node.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            zone_name = key_node.value
            zone_fields: dict[str, Any] = {}
            if isinstance(zone_value_node, ast.Call):
                for keyword in zone_value_node.keywords:
                    if keyword.arg is None:
                        continue
                    if isinstance(keyword.value, ast.Constant):
                        zone_fields[keyword.arg] = keyword.value.value
            zone_defs[zone_name] = zone_fields
        return zone_defs
    return {}


def _route_exists_in_source(source_text: str, route_path: str) -> bool:
    return route_path in source_text


def _route_is_present_in_runtime(result: dict[str, Any]) -> bool:
    status_code = result.get("status_code")
    return isinstance(status_code, int) and status_code in NON_DESTRUCTIVE_ROUTE_STATUS_CODES


def _load_capacity_telemetry() -> dict[str, Any]:
    if not CAPACITY_TELEMETRY_PATH.exists():
        return {}
    try:
        return json.loads(CAPACITY_TELEMETRY_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _build_capacity_truth_check(
    capacity_telemetry: dict[str, Any],
    scheduler_state: dict[str, Any],
) -> dict[str, Any]:
    capacity_summary = dict(capacity_telemetry.get("capacity_summary") or {})
    scheduler_slot_samples = [
        dict(sample)
        for sample in capacity_telemetry.get("scheduler_slot_samples", [])
        if isinstance(sample, dict)
    ]
    scheduler_body = scheduler_state.get("body")
    scheduler_gpus = dict(scheduler_body.get("gpus") or {}) if isinstance(scheduler_body, dict) else {}
    live_slot_ids = sorted(str(slot_id).strip() for slot_id in scheduler_gpus if str(slot_id).strip())
    telemetry_slot_ids = sorted(
        str(sample.get("scheduler_slot_id") or "").strip()
        for sample in scheduler_slot_samples
        if str(sample.get("scheduler_slot_id") or "").strip()
    )
    live_idle_slot_ids = sorted(
        slot_id
        for slot_id, slot in scheduler_gpus.items()
        if str(dict(slot).get("state") or "").strip().upper() in IDLE_SLOT_STATES
    )
    telemetry_harvestable_slot_ids = sorted(
        str(sample.get("scheduler_slot_id") or "").strip()
        for sample in scheduler_slot_samples
        if bool(sample.get("idle_window_open")) and str(sample.get("scheduler_slot_id") or "").strip()
    )

    checks = {
        "telemetry_present": bool(capacity_telemetry),
        "scheduler_projection_backed": str(capacity_summary.get("sample_posture") or "") == "scheduler_projection_backed",
        "scheduler_queue_depth_matches": int(capacity_summary.get("scheduler_queue_depth") or 0)
        == int((scheduler_body or {}).get("queue_depth") or 0),
        "scheduler_slot_count_matches": int(capacity_summary.get("scheduler_slot_count") or 0) == len(live_slot_ids),
        "scheduler_slot_inventory_matches": telemetry_slot_ids == live_slot_ids,
        "harvestable_slot_count_matches": int(capacity_summary.get("harvestable_scheduler_slot_count") or 0)
        == len(telemetry_harvestable_slot_ids),
        "harvestable_slot_subset_of_live_idle": set(telemetry_harvestable_slot_ids).issubset(set(live_idle_slot_ids)),
    }
    mismatches = [label for label, passed in checks.items() if not passed]

    return {
        "status": "passed" if not mismatches else "blocked",
        "checks": checks,
        "mismatches": mismatches,
        "telemetry_generated_at": capacity_telemetry.get("generated_at"),
        "telemetry_sample_posture": capacity_summary.get("sample_posture"),
        "telemetry_scheduler_slot_count": int(capacity_summary.get("scheduler_slot_count") or 0),
        "telemetry_harvestable_scheduler_slot_count": int(
            capacity_summary.get("harvestable_scheduler_slot_count") or 0
        ),
        "telemetry_scheduler_queue_depth": int(capacity_summary.get("scheduler_queue_depth") or 0),
        "live_scheduler_slot_ids": live_slot_ids,
        "live_idle_slot_ids": live_idle_slot_ids,
        "telemetry_scheduler_slot_ids": telemetry_slot_ids,
        "telemetry_harvestable_slot_ids": telemetry_harvestable_slot_ids,
    }


def _scheduler_write_capabilities_enabled(scheduler_state: dict[str, Any]) -> bool:
    body = scheduler_state.get("body")
    if not isinstance(body, dict):
        return False
    write_capabilities = body.get("write_capabilities")
    if not isinstance(write_capabilities, dict):
        return False
    return all(bool(write_capabilities.get(capability)) for capability in ("request", "preload", "release"))


def _load_model_registry_map() -> dict[str, dict[str, Any]]:
    registry = load_registry("model-deployment-registry.json")
    return {
        str(lane.get("id") or "").strip(): dict(lane)
        for lane in registry.get("lanes", [])
        if isinstance(lane, dict) and str(lane.get("id") or "").strip()
    }


def _probe_model_endpoints() -> dict[str, dict[str, Any]]:
    probes: dict[str, dict[str, Any]] = {}
    for lane_id, url in MODEL_ENDPOINTS.items():
        result = _http_get(url, timeout=20)
        probes[lane_id] = {
            "url": url,
            "result": result,
            "observed_model_id": _extract_model_id(result.get("body")),
        }
    return probes


def _registry_check(lane_id: str, lane: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    live_ok = bool(probe["result"].get("ok"))
    live_model_id = _normalize_model_id(probe.get("observed_model_id"))
    expected_model_id = _normalize_model_id(lane.get("expected_model_id"))
    observed_model_id = _normalize_model_id(lane.get("observed_model_id"))
    drift_status = str(lane.get("drift_status") or "").strip().lower()

    if live_ok:
        model_ids_match = expected_model_id == live_model_id and observed_model_id == live_model_id
        lane_ok = model_ids_match
        if lane_ok and drift_status == "aligned":
            message = f"live model {probe.get('observed_model_id')} matched expected and observed registry ids"
        elif lane_ok:
            message = (
                "live model ids matched expected and observed registry ids; "
                f"registry drift status remains {lane.get('drift_status')} for non-model reasons"
            )
        else:
            message = (
                f"registry mismatch: expected={lane.get('expected_model_id')} "
                f"observed={lane.get('observed_model_id')} live={probe.get('observed_model_id')}"
            )
    else:
        lane_ok = drift_status == "drifted"
        message = (
            f"live probe failed and registry already records drift ({probe['result'].get('error')})"
            if lane_ok
            else f"live probe failed but registry still claims aligned deployment ({probe['result'].get('error')})"
        )

    return {
        "lane_id": lane_id,
        "passed": lane_ok,
        "registry_endpoint": lane.get("endpoint"),
        "live_endpoint": probe.get("url"),
        "registry_drift_status": lane.get("drift_status"),
        "registry_expected_model_id": lane.get("expected_model_id"),
        "registry_observed_model_id": lane.get("observed_model_id"),
        "live_observed_model_id": probe.get("observed_model_id"),
        "message": message,
    }


def _build_summary(
    tracked: dict[str, Any],
    live_status: dict[str, Any],
    live_zones: dict[str, Any],
    scheduler_state: dict[str, Any],
    capacity_truth_check: dict[str, Any],
    mutation_source_presence: dict[str, bool],
    mutation_runtime_presence: dict[str, bool],
    registry_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    live_zone_names = sorted(
        str(item.get("name") or "").strip()
        for item in live_zones.get("body", {}).get("zones", [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    )
    source_zone_names = tracked["zone_names"]

    baseline_failures: list[str] = []
    if not live_status.get("ok"):
        baseline_failures.append("orchestrator-status-unreachable")
    if not live_zones.get("ok"):
        baseline_failures.append("orchestrator-zones-unreachable")
    if source_zone_names != live_zone_names:
        baseline_failures.append("tracked-zone-map-mismatch")
    if tracked["worker_vllm_url"] is not None:
        baseline_failures.append("tracked-worker-still-points-to-vllm")
    if any(not check.get("passed") for check in registry_checks):
        baseline_failures.append("model-deployment-registry-mismatch")

    formal_eval_blockers: list[str] = []
    if not tracked.get("scheduler_endpoint_in_source"):
        formal_eval_blockers.append("scheduler-endpoint-absent-in-tracked-source")
    if scheduler_state.get("status_code") != 200:
        formal_eval_blockers.append("scheduler-state-endpoint-absent-in-live-runtime")
    if str(capacity_truth_check.get("status") or "") != "passed":
        formal_eval_blockers.append("capacity-telemetry-mismatch")
    if scheduler_state.get("status_code") == 200 and not _scheduler_write_capabilities_enabled(scheduler_state):
        formal_eval_blockers.append("scheduler-write-capabilities-disabled-in-live-runtime")
    if not all(mutation_source_presence.values()):
        formal_eval_blockers.append("scheduler-mutation-endpoints-absent-in-tracked-source")
    if not all(mutation_runtime_presence.values()):
        formal_eval_blockers.append("scheduler-mutation-endpoints-absent-in-live-runtime")
    if baseline_failures:
        formal_eval_blockers.append("baseline-alignment-incomplete")

    baseline_alignment_status = "passed" if not baseline_failures else "blocked"
    formal_eval_ready = not formal_eval_blockers

    return {
        "baseline_alignment_status": baseline_alignment_status,
        "baseline_failures": baseline_failures,
        "formal_eval_ready": formal_eval_ready,
        "formal_eval_blockers": formal_eval_blockers,
        "capacity_truth_alignment_status": capacity_truth_check.get("status"),
        "capacity_truth_alignment_mismatches": list(capacity_truth_check.get("mismatches") or []),
        "tracked_zone_count": tracked["zone_count"],
        "live_zone_count": len(live_zone_names),
        "tracked_zone_names": source_zone_names,
        "live_zone_names": live_zone_names,
        "tracked_mutation_routes_present": mutation_source_presence,
        "live_mutation_routes_present": mutation_runtime_presence,
        "next_action": (
            "advance release tier and capture governed deploy evidence"
            if formal_eval_ready
            else (
                "refresh capacity telemetry so the slot-level harvest truth matches the live scheduler surface before widening dispatch claims"
                if str(capacity_truth_check.get("status") or "") != "passed"
                else (
                "deploy the read-only scheduler-state surface through the governed Foundry packet and keep the formal eval blocked until bounded mutation endpoints exist in source and live runtime"
                if baseline_alignment_status == "passed"
                else "finish baseline source and registry reconciliation before attempting the scheduler formal eval"
                )
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a current-state baseline eval for the GPU scheduler promotion lane."
    )
    parser.add_argument("--base-url", default=DEFAULT_ORCHESTRATOR_BASE)
    parser.add_argument("--write", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    tracked = _load_tracked_orchestrator()
    capacity_telemetry = _load_capacity_telemetry()
    registry_map = _load_model_registry_map()
    source_text = GPU_ORCH_MAIN.read_text(encoding="utf-8")

    health = _http_get(f"{args.base_url}/health", timeout=20)
    status = _http_get(f"{args.base_url}/status", timeout=20)
    zones = _http_get(f"{args.base_url}/zones", timeout=20)
    scheduler_state = _http_get(f"{args.base_url}/scheduler/state", timeout=20)
    mutation_probes = {
        endpoint_name: _http_get(f"{args.base_url}{route_path}", timeout=20)
        for endpoint_name, route_path in REQUIRED_MUTATION_ENDPOINTS.items()
    }
    mutation_source_presence = {
        endpoint_name: _route_exists_in_source(source_text, route_path)
        for endpoint_name, route_path in REQUIRED_MUTATION_ENDPOINTS.items()
    }
    mutation_runtime_presence = {
        endpoint_name: _route_is_present_in_runtime(result)
        for endpoint_name, result in mutation_probes.items()
    }
    capacity_truth_check = _build_capacity_truth_check(capacity_telemetry, scheduler_state)
    model_probes = _probe_model_endpoints()

    registry_checks = [
        _registry_check(lane_id, registry_map[lane_id], model_probes[lane_id])
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

    foundry_runtime_env = _ssh_probe(
        str(os.environ.get("ATHANOR_NODE1_HOST") or "foundry").strip() or "foundry",
        "docker inspect athanor-gpu-orchestrator --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^GPU_ORCH_' | sort",
    )
    workshop_runtime = _ssh_probe(
        str(os.environ.get("ATHANOR_NODE2_HOST") or "workshop").strip() or "workshop",
        "cd /opt/athanor && docker ps --format '{{.Names}}\\t{{.Status}}\\t{{.Ports}}' | grep -E 'vllm|comfy|ollama'",
    )

    summary = _build_summary(
        tracked,
        status,
        zones,
        scheduler_state,
        capacity_truth_check,
        mutation_source_presence,
        mutation_runtime_presence,
        registry_checks,
    )
    payload = {
        "version": "2026-04-11.1",
        "generated_at": iso_now(),
        "source_of_truth": "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
        "initiative_id": "gpu-scheduler-extension",
        "run_id": "gpu-scheduler-extension-private-local-2026q1",
        "summary": summary,
        "tracked_source": tracked,
        "live_runtime": {
            "orchestrator_health": health,
            "orchestrator_status": status,
            "orchestrator_zones": zones,
            "scheduler_state": scheduler_state,
            "scheduler_mutation_probes": mutation_probes,
            "model_probes": model_probes,
            "foundry_runtime_env": foundry_runtime_env,
            "workshop_runtime": workshop_runtime,
        },
        "capacity_truth_check": capacity_truth_check,
        "tracked_mutation_routes": mutation_source_presence,
        "live_mutation_routes": mutation_runtime_presence,
        "model_registry_checks": registry_checks,
    }
    dump_json(args.write, payload)
    append_history(
        "capability-promotion-evals",
        {
            "generated_at": payload["generated_at"],
            "initiative_id": payload["initiative_id"],
            "run_id": payload["run_id"],
            "baseline_alignment_status": summary["baseline_alignment_status"],
            "formal_eval_ready": summary["formal_eval_ready"],
            "formal_eval_blockers": summary["formal_eval_blockers"],
            "baseline_failures": summary["baseline_failures"],
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
