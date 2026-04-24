#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
BLOCKER_EXECUTION_PLAN_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-execution-plan.json"
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
VALUE_THROUGHPUT_SCORECARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
COMPLETION_PASS_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "completion-pass-ledger.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
RUNTIME_PACKET_INBOX_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-packet-inbox.json"
RALPH_LATEST_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
CONTRACT_HEALER_PATH = REPO_ROOT / "audit" / "automation" / "contract-healer-latest.json"

RECENT_PASS_WINDOW = timedelta(minutes=4)
NO_DELTA_BACKOFF_THRESHOLD = 6
NO_DELTA_BACKOFF = timedelta(minutes=15)
CONTINUITY_PROCESS_MARKERS = (
    "run_continuity_supervisor.py",
    "run_steady_state_control_plane.py",
    "collect_truth_inventory.py",
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> None:
    rendered = _json_render(payload)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_pid(value: Any) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _runtime_packet_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    packets = payload.get("packets")
    if not isinstance(packets, list):
        return []
    return [dict(item) for item in packets if isinstance(item, dict)]


def _runtime_packet_target(runtime_packet_inbox: dict[str, Any]) -> dict[str, Any]:
    packets = _runtime_packet_list(runtime_packet_inbox)
    if not packets:
        return {}
    packet = packets[0]
    return {
        "kind": "runtime_packet",
        "family_id": "runtime-packet-inbox",
        "family_title": "Runtime Packet Inbox",
        "subtranche_id": _pick_string(packet.get("id")),
        "subtranche_title": _pick_string(packet.get("label"), packet.get("id")),
        "execution_class": "approval_gated_runtime_packet",
        "approval_gated": True,
        "external_blocked": False,
        "host": _pick_string(packet.get("host")),
        "approval_type": _pick_string(packet.get("approval_type")),
        "readiness_state": _pick_string(packet.get("readiness_state")) or "unknown",
        "detail": _pick_string(packet.get("goal")),
        "next_operator_action": _pick_string(packet.get("next_operator_action")),
    }


def _effective_next_target(execution_plan: dict[str, Any], runtime_packet_inbox: dict[str, Any]) -> dict[str, Any]:
    runtime_target = _runtime_packet_target(runtime_packet_inbox)
    if runtime_target:
        return runtime_target
    return dict(execution_plan.get("next_target") or {})


def _supervisor_pid_is_live(pid: Any) -> bool:
    normalized = _normalize_pid(pid)
    if normalized is None:
        return False
    try:
        cmdline = (Path("/proc") / str(normalized) / "cmdline").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "run_continuity_supervisor.py" in cmdline


def _any_continuity_process_alive(*, exclude_pids: set[int] | None = None) -> bool:
    excluded = exclude_pids or set()
    proc_root = Path("/proc")
    try:
        proc_entries = list(proc_root.iterdir())
    except OSError:
        return False
    for entry in proc_entries:
        if not entry.name.isdigit():
            continue
        pid = _normalize_pid(entry.name)
        if pid is None or pid in excluded:
            continue
        try:
            cmdline = (entry / "cmdline").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in cmdline for marker in CONTINUITY_PROCESS_MARKERS):
            return True
    return False


def _hash_payload(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _load_or_build_execution_plan(blocker_map: dict[str, Any]) -> dict[str, Any]:
    module_path = REPO_ROOT / "scripts" / "write_blocker_execution_plan.py"
    spec = importlib.util.spec_from_file_location("write_blocker_execution_plan", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["write_blocker_execution_plan"] = module
    spec.loader.exec_module(module)
    existing = _load_optional_json(BLOCKER_EXECUTION_PLAN_PATH)
    payload = module.build_payload(blocker_map)
    comparable_existing = dict(existing) if isinstance(existing, dict) else {}
    comparable_existing.pop("generated_at", None)
    comparable_payload = dict(payload)
    comparable_payload.pop("generated_at", None)
    if comparable_existing == comparable_payload and existing:
        payload["generated_at"] = _pick_string(existing.get("generated_at")) or payload["generated_at"]
    _write_json_if_changed(BLOCKER_EXECUTION_PLAN_PATH, payload)
    return payload


def _validator_snapshot(ralph: dict[str, Any], contract_healer: dict[str, Any]) -> dict[str, Any]:
    executive_brief = dict(ralph.get("executive_brief") or {})
    proof = dict(executive_brief.get("proof") or {})
    validation = dict(ralph.get("validation") or {})
    return {
        "contract_healer": contract_healer,
        "ralph_validation": validation,
        "validation_summary": _pick_string(proof.get("validation_summary")) or "",
    }


def _default_state(
    *,
    now_iso: str,
    blocker_map_hash: str,
    validator_hash: str,
    value_throughput_hash: str,
) -> dict[str, Any]:
    return {
        "generated_at": now_iso,
        "controller_host": "dev",
        "controller_mode": "closure_debt",
        "controller_status": "idle",
        "controller_pid": None,
        "active_pass_id": None,
        "active_family_id": None,
        "active_subtranche_id": None,
        "active_objective": "closure_debt",
        "typed_brake": None,
        "workspace_drift_status": "unknown",
        "started_at": None,
        "finished_at": None,
        "last_successful_pass_at": None,
        "last_meaningful_delta_at": None,
        "last_skip_reason": None,
        "backoff_until": None,
        "consecutive_no_delta_passes": 0,
        "last_blocker_map_hash": blocker_map_hash,
        "last_validator_hash": validator_hash,
        "last_value_throughput_hash": value_throughput_hash,
        "source_artifacts": {
            "blocker_map": str(BLOCKER_MAP_PATH),
            "blocker_execution_plan": str(BLOCKER_EXECUTION_PLAN_PATH),
            "value_throughput_scorecard": str(VALUE_THROUGHPUT_SCORECARD_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "ralph_latest": str(RALPH_LATEST_PATH),
            "contract_healer": str(CONTRACT_HEALER_PATH),
            "completion_pass_ledger": str(COMPLETION_PASS_LEDGER_PATH),
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
        },
    }


def _normalized_objective(blocker_map: dict[str, Any]) -> str:
    objective = _pick_string(blocker_map.get("objective")) or "closure_debt"
    if objective == "result_backed_throughput":
        return "queue_backed_throughput"
    return objective


def _typed_brake_from_runtime_parity(runtime_parity: dict[str, Any]) -> str | None:
    drift_class = _pick_string(runtime_parity.get("drift_class"))
    if drift_class in {"proof_workspace_drift", "runtime_ownership_drift"}:
        return drift_class
    return None


def _controller_mode(blocker_map: dict[str, Any], runtime_parity: dict[str, Any]) -> str:
    objective = _normalized_objective(blocker_map)
    if objective == "closure_debt":
        return "closure_debt"
    proof_gate = dict(blocker_map.get("proof_gate") or {})
    if objective == "queue_backed_throughput" and not bool(proof_gate.get("open")):
        return "proof_hold"
    return objective


def _normalized_existing_state(
    existing_state: dict[str, Any],
    *,
    blocker_map: dict[str, Any],
    runtime_parity: dict[str, Any],
    now_iso: str,
    blocker_map_hash: str,
    validator_hash: str,
    value_throughput_hash: str,
) -> dict[str, Any]:
    state = _default_state(
        now_iso=now_iso,
        blocker_map_hash=blocker_map_hash,
        validator_hash=validator_hash,
        value_throughput_hash=value_throughput_hash,
    )
    if isinstance(existing_state, dict):
        state.update(existing_state)
    state["controller_host"] = _pick_string(state.get("controller_host")) or "dev"
    state["controller_mode"] = _controller_mode(blocker_map, runtime_parity)
    state["active_objective"] = _normalized_objective(blocker_map)
    state["workspace_drift_status"] = _pick_string(runtime_parity.get("drift_class")) or "unknown"
    state["typed_brake"] = _typed_brake_from_runtime_parity(runtime_parity)
    state["controller_pid"] = _normalize_pid(state.get("controller_pid"))
    state["generated_at"] = now_iso
    state["last_blocker_map_hash"] = _pick_string(state.get("last_blocker_map_hash")) or blocker_map_hash
    state["last_validator_hash"] = _pick_string(state.get("last_validator_hash")) or validator_hash
    state["last_value_throughput_hash"] = _pick_string(state.get("last_value_throughput_hash")) or value_throughput_hash
    state["consecutive_no_delta_passes"] = int(state.get("consecutive_no_delta_passes") or 0)
    return state


def _hashes_changed(state: dict[str, Any], blocker_map_hash: str, validator_hash: str, value_throughput_hash: str) -> bool:
    return any(
        [
            blocker_map_hash != _pick_string(state.get("last_blocker_map_hash")),
            validator_hash != _pick_string(state.get("last_validator_hash")),
            value_throughput_hash != _pick_string(state.get("last_value_throughput_hash")),
        ]
    )


def _blocked_reason(blocker_map: dict[str, Any], execution_plan: dict[str, Any], ralph: dict[str, Any]) -> str | None:
    stop_state = _pick_string(ralph.get("current_stop_state"), ralph.get("stop_state")) or "none"
    runtime_packets = dict(blocker_map.get("runtime_packets") or {})
    next_target = dict(execution_plan.get("next_target") or {})

    if bool(next_target.get("external_blocked")) or stop_state == "external_block":
        return "external_dependency_blocked"
    if (
        bool(next_target.get("approval_gated"))
        or int(runtime_packets.get("approval_gated_count") or 0) > 0
        or stop_state == "approval_required"
    ):
        return "approval_gated_runtime_packet"
    return None


def evaluate_begin(
    *,
    existing_state: dict[str, Any],
    blocker_map: dict[str, Any],
    execution_plan: dict[str, Any],
    value_throughput: dict[str, Any],
    validator_snapshot: dict[str, Any],
    ralph: dict[str, Any],
    now_iso: str,
    runtime_parity: dict[str, Any] | None = None,
    runtime_packet_inbox: dict[str, Any] | None = None,
    process_is_live: Callable[[Any], bool] = _supervisor_pid_is_live,
    continuity_process_is_alive: Callable[..., bool] = _any_continuity_process_alive,
) -> dict[str, Any]:
    runtime_parity = dict(runtime_parity or {})
    blocker_map_hash = _hash_payload(blocker_map)
    validator_hash = _hash_payload(validator_snapshot)
    value_throughput_hash = _hash_payload(value_throughput)
    state = _normalized_existing_state(
        existing_state,
        blocker_map=blocker_map,
        runtime_parity=runtime_parity,
        now_iso=now_iso,
        blocker_map_hash=blocker_map_hash,
        validator_hash=validator_hash,
        value_throughput_hash=value_throughput_hash,
    )
    now_dt = _parse_iso(now_iso) or datetime.now(timezone.utc)
    next_target = _effective_next_target(execution_plan, dict(runtime_packet_inbox or {}))

    if state.get("controller_status") == "running":
        controller_pid = _normalize_pid(state.get("controller_pid"))
        other_continuity_work_alive = continuity_process_is_alive(exclude_pids={os.getpid()})
        if process_is_live(controller_pid) or other_continuity_work_alive:
            state["controller_status"] = "skipped"
            state["last_skip_reason"] = "pass_active"
            return state
        state["controller_status"] = "idle"
        state["controller_pid"] = None
        state["active_pass_id"] = None
        state["active_family_id"] = None
        state["active_subtranche_id"] = None
        state["started_at"] = None

    backoff_until = _parse_iso(state.get("backoff_until"))
    if backoff_until and now_dt < backoff_until:
        state["controller_status"] = "skipped"
        state["last_skip_reason"] = "backoff_active"
        return state

    blocker_reason = _typed_brake_from_runtime_parity(runtime_parity) or _blocked_reason(blocker_map, execution_plan, ralph)
    if blocker_reason:
        state["controller_status"] = "blocked"
        state["active_pass_id"] = None
        state["active_family_id"] = next_target.get("family_id")
        state["active_subtranche_id"] = next_target.get("subtranche_id")
        state["started_at"] = None
        state["finished_at"] = now_iso
        state["last_skip_reason"] = blocker_reason
        state["typed_brake"] = blocker_reason if blocker_reason in {"proof_workspace_drift", "runtime_ownership_drift"} else state.get("typed_brake")
        state["controller_mode"] = "typed_brake" if state.get("typed_brake") else state.get("controller_mode")
        return state

    finished_at = _parse_iso(state.get("finished_at"))
    if finished_at and now_dt - finished_at < RECENT_PASS_WINDOW and not _hashes_changed(
        state, blocker_map_hash, validator_hash, value_throughput_hash
    ):
        state["controller_status"] = "skipped"
        state["last_skip_reason"] = "recent_pass_no_new_evidence"
        return state

    if next_target.get("kind") == "none":
        state["controller_status"] = "running"
        state["controller_pid"] = os.getpid()
        state["active_pass_id"] = f"continuity-pass-{uuid.uuid4().hex[:12]}"
        state["active_family_id"] = None
        state["active_subtranche_id"] = None
        state["started_at"] = now_iso
        state["last_skip_reason"] = None
        state["controller_mode"] = _controller_mode(blocker_map, runtime_parity)
        state["active_objective"] = _normalized_objective(blocker_map)
        state["workspace_drift_status"] = _pick_string(runtime_parity.get("drift_class")) or "unknown"
        state["typed_brake"] = _typed_brake_from_runtime_parity(runtime_parity)
        return state

    state["controller_status"] = "running"
    state["controller_pid"] = os.getpid()
    state["active_pass_id"] = f"continuity-pass-{uuid.uuid4().hex[:12]}"
    state["active_family_id"] = next_target.get("family_id")
    state["active_subtranche_id"] = next_target.get("subtranche_id")
    state["started_at"] = now_iso
    state["last_skip_reason"] = None
    state["controller_mode"] = _controller_mode(blocker_map, runtime_parity)
    state["active_objective"] = _normalized_objective(blocker_map)
    state["workspace_drift_status"] = _pick_string(runtime_parity.get("drift_class")) or "unknown"
    state["typed_brake"] = _typed_brake_from_runtime_parity(runtime_parity)
    return state


def evaluate_finish(
    *,
    existing_state: dict[str, Any],
    blocker_map: dict[str, Any],
    value_throughput: dict[str, Any],
    validator_snapshot: dict[str, Any],
    now_iso: str,
    pass_id: str | None = None,
    runtime_parity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_parity = dict(runtime_parity or {})
    blocker_map_hash = _hash_payload(blocker_map)
    validator_hash = _hash_payload(validator_snapshot)
    value_throughput_hash = _hash_payload(value_throughput)
    state = _normalized_existing_state(
        existing_state,
        blocker_map=blocker_map,
        runtime_parity=runtime_parity,
        now_iso=now_iso,
        blocker_map_hash=blocker_map_hash,
        validator_hash=validator_hash,
        value_throughput_hash=value_throughput_hash,
    )
    if pass_id and _pick_string(state.get("active_pass_id")) and _pick_string(state.get("active_pass_id")) != pass_id:
        state["controller_status"] = "skipped"
        state["last_skip_reason"] = "pass_id_mismatch"
        return state

    meaningful_delta = _hashes_changed(state, blocker_map_hash, validator_hash, value_throughput_hash)
    if meaningful_delta:
        consecutive_no_delta_passes = 0
        backoff_until = None
        last_meaningful_delta_at = now_iso
    else:
        consecutive_no_delta_passes = int(state.get("consecutive_no_delta_passes") or 0) + 1
        backoff_until = state.get("backoff_until")
        if consecutive_no_delta_passes >= NO_DELTA_BACKOFF_THRESHOLD:
            now_dt = _parse_iso(now_iso) or datetime.now(timezone.utc)
            backoff_until = (now_dt + NO_DELTA_BACKOFF).isoformat()
        last_meaningful_delta_at = state.get("last_meaningful_delta_at")

    state.update(
        {
            "controller_host": "dev",
            "controller_mode": _controller_mode(blocker_map, runtime_parity),
            "controller_status": "idle",
            "controller_pid": None,
            "active_pass_id": None,
            "active_family_id": None,
            "active_subtranche_id": None,
            "active_objective": _normalized_objective(blocker_map),
            "typed_brake": _typed_brake_from_runtime_parity(runtime_parity),
            "workspace_drift_status": _pick_string(runtime_parity.get("drift_class")) or "unknown",
            "started_at": None,
            "finished_at": now_iso,
            "last_successful_pass_at": now_iso,
            "last_meaningful_delta_at": last_meaningful_delta_at,
            "last_skip_reason": None,
            "backoff_until": backoff_until,
            "consecutive_no_delta_passes": consecutive_no_delta_passes,
            "last_blocker_map_hash": blocker_map_hash,
            "last_validator_hash": validator_hash,
            "last_value_throughput_hash": value_throughput_hash,
        }
    )
    return state


def build_status(
    *,
    existing_state: dict[str, Any],
    blocker_map: dict[str, Any],
    execution_plan: dict[str, Any],
    value_throughput: dict[str, Any],
    validator_snapshot: dict[str, Any],
    now_iso: str,
    runtime_parity: dict[str, Any] | None = None,
    runtime_packet_inbox: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_parity = dict(runtime_parity or {})
    blocker_map_hash = _hash_payload(blocker_map)
    validator_hash = _hash_payload(validator_snapshot)
    value_throughput_hash = _hash_payload(value_throughput)
    state = _normalized_existing_state(
        existing_state,
        blocker_map=blocker_map,
        runtime_parity=runtime_parity,
        now_iso=now_iso,
        blocker_map_hash=blocker_map_hash,
        validator_hash=validator_hash,
        value_throughput_hash=value_throughput_hash,
    )
    state["controller_host"] = "dev"
    state["controller_mode"] = _controller_mode(blocker_map, runtime_parity)
    state["active_objective"] = _normalized_objective(blocker_map)
    state["workspace_drift_status"] = _pick_string(runtime_parity.get("drift_class")) or "unknown"
    state["typed_brake"] = _typed_brake_from_runtime_parity(runtime_parity)
    state["controller_pid"] = _normalize_pid(state.get("controller_pid"))
    state["next_target"] = _effective_next_target(execution_plan, dict(runtime_packet_inbox or {}))
    return state


def _write_state(payload: dict[str, Any]) -> None:
    _write_json_if_changed(CONTINUITY_CONTROLLER_STATE_PATH, payload)


def _proof_check_lookup(blocker_map: dict[str, Any], check_id: str) -> dict[str, Any]:
    checks = blocker_map.get("proof_gate", {}).get("checks", [])
    if not isinstance(checks, list):
        return {}
    for check in checks:
        if isinstance(check, dict) and _pick_string(check.get("id")) == check_id:
            return dict(check)
    return {}


def append_pass_ledger(
    *,
    existing_state: dict[str, Any],
    finished_state: dict[str, Any],
    blocker_map: dict[str, Any],
    result_evidence: dict[str, Any],
    validator_snapshot: dict[str, Any],
) -> dict[str, Any]:
    pass_id = _pick_string(existing_state.get("active_pass_id"))
    if not pass_id:
        return {}

    stale_claim_check = _proof_check_lookup(blocker_map, "stale_claim_failures")
    artifact_consistency_check = _proof_check_lookup(blocker_map, "artifact_consistency")
    validator_check = _proof_check_lookup(blocker_map, "validator_and_contract_healer")
    ralph_validation = dict(validator_snapshot.get("ralph_validation") or {})
    contract_healer = dict(validator_snapshot.get("contract_healer") or {})
    validation_summary = _pick_string(validator_snapshot.get("validation_summary")) or _pick_string(validator_check.get("detail")) or "none"
    validator_met = bool(ralph_validation.get("ran")) and bool(ralph_validation.get("all_passed")) and bool(contract_healer.get("success"))
    validator_detail = (
        f"validation_materialized={bool(ralph_validation.get('ran'))}, "
        f"validation_passed={bool(ralph_validation.get('all_passed'))}, "
        f"contract_healer_green={bool(contract_healer.get('success'))}, "
        f"validation_summary={validation_summary}"
    )
    healthy = all(
        bool(check.get("met"))
        for check in (stale_claim_check, artifact_consistency_check)
        if check
    ) and validator_met
    entry = {
        "pass_id": pass_id,
        "family_id": _pick_string(existing_state.get("active_family_id")),
        "subtranche_id": _pick_string(existing_state.get("active_subtranche_id")),
        "started_at": _pick_string(existing_state.get("started_at")),
        "finished_at": _pick_string(finished_state.get("finished_at")),
        "meaningful_delta": bool(finished_state.get("last_meaningful_delta_at") == finished_state.get("finished_at")),
        "healthy": healthy,
        "remaining": {
            "family_count": int((blocker_map.get("remaining") or {}).get("family_count") or 0),
            "path_count": int((blocker_map.get("remaining") or {}).get("path_count") or 0),
        },
        "proofs": {
            "stale_claim_failures": {
                "met": bool(stale_claim_check.get("met")),
                "detail": _pick_string(stale_claim_check.get("detail")),
            },
            "artifact_consistency": {
                "met": bool(artifact_consistency_check.get("met")),
                "detail": _pick_string(artifact_consistency_check.get("detail")),
            },
            "validator_and_contract_healer": {
                "met": validator_met,
                "detail": validator_detail,
            },
        },
        "result_evidence": {
            "threshold_required": int(result_evidence.get("threshold_required") or 5),
            "threshold_progress": int(result_evidence.get("threshold_progress") or 0),
            "threshold_met": bool(result_evidence.get("threshold_met")),
            "result_backed_completion_count": int(result_evidence.get("result_backed_completion_count") or 0),
            "review_backed_output_count": int(result_evidence.get("review_backed_output_count") or 0),
        },
    }

    existing_ledger = _load_optional_json(COMPLETION_PASS_LEDGER_PATH)
    passes = [dict(item) for item in existing_ledger.get("passes", []) if isinstance(item, dict)]
    passes = [item for item in passes if _pick_string(item.get("pass_id")) != pass_id]
    passes.append(entry)
    ledger = {
        "generated_at": _iso_now(),
        "pass_count": len(passes),
        "latest_pass_id": pass_id,
        "latest_pass_at": _pick_string(entry.get("finished_at")),
        "passes": passes,
    }
    _write_json_if_changed(COMPLETION_PASS_LEDGER_PATH, ledger)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or update the Athanor continuity controller pass.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Write the current continuity controller state without acquiring a pass lock.")
    status_parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")

    begin_parser = subparsers.add_parser("begin", help="Acquire the next bounded continuity pass if no skip or block rule applies.")
    begin_parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")

    finish_parser = subparsers.add_parser("finish", help="Release the active continuity pass and update no-delta/backoff state.")
    finish_parser.add_argument("--pass-id", help="Optional active pass id to finish.")
    finish_parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")

    args = parser.parse_args()

    now_iso = _iso_now()
    blocker_map = _load_optional_json(BLOCKER_MAP_PATH)
    execution_plan = _load_or_build_execution_plan(blocker_map)
    value_throughput = _load_optional_json(VALUE_THROUGHPUT_SCORECARD_PATH)
    ralph = _load_optional_json(RALPH_LATEST_PATH)
    contract_healer = _load_optional_json(CONTRACT_HEALER_PATH)
    validator_snapshot = _validator_snapshot(ralph, contract_healer)
    existing_state = _load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH)
    result_evidence = _load_optional_json(RESULT_EVIDENCE_LEDGER_PATH)
    runtime_parity = _load_optional_json(RUNTIME_PARITY_PATH)
    runtime_packet_inbox = _load_optional_json(RUNTIME_PACKET_INBOX_PATH)

    if args.command == "status":
        payload = build_status(
            existing_state=existing_state,
            blocker_map=blocker_map,
            execution_plan=execution_plan,
            value_throughput=value_throughput,
            validator_snapshot=validator_snapshot,
            runtime_parity=runtime_parity,
            runtime_packet_inbox=runtime_packet_inbox,
            now_iso=now_iso,
        )
    elif args.command == "begin":
        payload = evaluate_begin(
            existing_state=existing_state,
            blocker_map=blocker_map,
            execution_plan=execution_plan,
            value_throughput=value_throughput,
            validator_snapshot=validator_snapshot,
            runtime_parity=runtime_parity,
            runtime_packet_inbox=runtime_packet_inbox,
            ralph=ralph,
            now_iso=now_iso,
        )
        payload["next_target"] = _effective_next_target(execution_plan, runtime_packet_inbox)
    else:
        pre_finish_state = dict(existing_state)
        payload = evaluate_finish(
            existing_state=existing_state,
            blocker_map=blocker_map,
            value_throughput=value_throughput,
            validator_snapshot=validator_snapshot,
            runtime_parity=runtime_parity,
            now_iso=now_iso,
            pass_id=getattr(args, "pass_id", None),
        )
        payload["next_target"] = _effective_next_target(execution_plan, runtime_packet_inbox)
        append_pass_ledger(
            existing_state=pre_finish_state,
            finished_state=payload,
            blocker_map=blocker_map,
            result_evidence=result_evidence,
            validator_snapshot=validator_snapshot,
        )

    _write_state(payload)
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(str(CONTINUITY_CONTROLLER_STATE_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
