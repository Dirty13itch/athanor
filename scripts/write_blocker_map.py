#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from session_restart_brief import (
    FINISH_SCOREBOARD_PATH,
    PUBLICATION_DEFERRED_QUEUE_PATH,
    RALPH_LATEST_PATH,
    RUNTIME_PACKET_INBOX_PATH,
    _load_optional_json,
    _prefer_fresher_mapping,
    build_restart_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
VALUE_THROUGHPUT_SCORECARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"
CONTRACT_HEALER_PATH = REPO_ROOT / "audit" / "automation" / "contract-healer-latest.json"
STABLE_OPERATING_DAY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "stable-operating-day.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
COMPLETION_PASS_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "completion-pass-ledger.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"

PROGRAM_SLICE_EXECUTION_ORDER = [
    "control-plane-registry-and-routing",
    "agent-execution-kernel-follow-on",
    "agent-route-contract-follow-on",
    "control-plane-proof-and-ops-follow-on",
]
AUTO_MUTATION_APPROVAL_GATED_CLASSES = [
    "runtime_repair",
    "provider_secret_change",
    "auth_repair",
    "host_access_change",
    "network_storage_change",
    "destructive_cleanup",
]
AUTO_MUTATION_ALLOWED_AFTER_GATE = [
    "repo_safe_control_plane",
    "repo_safe_coding",
    "reversible_runtime_packet",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> None:
    rendered = _json_render(payload)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def _sync_sidecar_from_ralph(ralph: dict[str, Any], key: str, destination: Path) -> tuple[dict[str, Any], bool]:
    embedded = dict(ralph.get(key) or {}) if isinstance(ralph.get(key), dict) else {}
    sidecar = _load_optional_json(destination)
    selected = _prefer_fresher_mapping(embedded, sidecar)
    if selected:
        _write_json_if_changed(destination, selected)
    changed = bool(selected) and selected != embedded
    if changed:
        ralph[key] = selected
    return selected, changed


def _classify_path_surface(path: str) -> str | None:
    normalized = path.strip()
    if not normalized:
        return None
    if normalized.startswith("config/automation-backbone/") or "policy" in normalized:
        return "registry/policy"
    if "/routes/" in normalized or "route_contract" in normalized or "/route" in normalized:
        return "routes/contracts"
    if normalized.startswith("projects/agents/src/athanor_agents/"):
        return "agent runtime"
    if normalized.startswith("projects/agents/tests/"):
        if "route_contract" in normalized or "route" in normalized:
            return "routes/contracts"
        return "proof/ops"
    if normalized.startswith("scripts/") or normalized.startswith("docs/") or normalized.startswith("audit/"):
        return "proof/ops"
    return None


def _family_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    execution_class = str(item.get("execution_class") or "unknown")
    execution_rank = int(item.get("execution_rank") or 999)
    family_id = str(item.get("id") or "")
    class_rank = {
        "cash_now": 0,
        "bounded_follow_on": 1,
        "program_slice": 2,
        "tenant_lane": 3,
    }.get(execution_class, 99)
    explicit_program_rank = (
        PROGRAM_SLICE_EXECUTION_ORDER.index(family_id)
        if family_id in PROGRAM_SLICE_EXECUTION_ORDER
        else 999
    )
    return (class_rank, explicit_program_rank, execution_rank, family_id)


def _normalize_family(item: dict[str, Any]) -> dict[str, Any]:
    sample_paths = [
        str(entry).strip()
        for entry in item.get("sample_paths", [])
        if isinstance(entry, str) and str(entry).strip()
    ]
    fallback_paths = [
        str(entry).strip()
        for entry in item.get("path_hints", [])
        if isinstance(entry, str) and str(entry).strip()
    ]
    path_inputs = sample_paths or fallback_paths
    categories = sorted({category for path in path_inputs if (category := _classify_path_surface(path))})
    match_count = int(item.get("match_count") or 0)
    decomposition_reasons: list[str] = []
    if match_count > 12:
        decomposition_reasons.append("match_count_above_12")
    if len(categories) > 2:
        decomposition_reasons.append("spans_more_than_two_surface_categories")
    return {
        "id": str(item.get("id") or ""),
        "title": _pick_string(item.get("title"), item.get("id")) or "unknown",
        "execution_class": str(item.get("execution_class") or "unknown"),
        "execution_rank": int(item.get("execution_rank") or 999),
        "match_count": match_count,
        "next_action": _pick_string(item.get("next_action")) or "",
        "success_condition": _pick_string(item.get("success_condition")) or "",
        "categories": categories,
        "decomposition_required": bool(decomposition_reasons),
        "decomposition_reasons": decomposition_reasons,
        "sample_paths": path_inputs[:12],
    }


def _remaining_families(publication_queue: dict[str, Any]) -> list[dict[str, Any]]:
    families = publication_queue.get("families")
    if not isinstance(families, list):
        return []
    remaining = [
        _normalize_family(item)
        for item in families
        if isinstance(item, dict) and int(item.get("match_count") or 0) > 0
    ]
    remaining.sort(key=_family_sort_key)
    return remaining


def _proof_gate(
    finish_scoreboard: dict[str, Any],
    remaining_families: list[dict[str, Any]],
    value_throughput: dict[str, Any],
    ralph: dict[str, Any],
    contract_healer: dict[str, Any],
    runtime_parity: dict[str, Any],
    stable_operating_day: dict[str, Any],
    result_evidence: dict[str, Any],
    completion_pass_ledger: dict[str, Any],
    dispatch_status: str,
) -> dict[str, Any]:
    result_backed_completion_count = int(result_evidence.get("result_backed_completion_count") or 0)
    review_backed_output_count = int(result_evidence.get("review_backed_output_count") or 0)
    stale_claim_count = int(value_throughput.get("stale_claim_count") or 0)
    reconciliation_issue_count = int((value_throughput.get("reconciliation") or {}).get("issue_count") or 0)
    expected_counts = {
        "cash_now": int(finish_scoreboard.get("cash_now_remaining_count") or 0),
        "bounded_follow_on": int(finish_scoreboard.get("bounded_follow_on_remaining_count") or 0),
        "program_slice": int(finish_scoreboard.get("program_slice_remaining_count") or 0),
    }
    observed_counts = {
        "cash_now": sum(1 for item in remaining_families if item.get("execution_class") == "cash_now"),
        "bounded_follow_on": sum(1 for item in remaining_families if item.get("execution_class") == "bounded_follow_on"),
        "program_slice": sum(1 for item in remaining_families if item.get("execution_class") == "program_slice"),
    }
    validation = dict(ralph.get("validation") or {})
    proof = dict((ralph.get("executive_brief") or {}).get("proof") or {})
    validation_materialized = bool(validation.get("ran"))
    validation_passed = bool(validation.get("all_passed")) if validation_materialized else False
    contract_healer_green = bool(contract_healer.get("success"))
    stable_day_met = bool(stable_operating_day.get("met"))
    stable_day_hours = float(stable_operating_day.get("covered_window_hours") or 0.0)
    required_window_hours = int(stable_operating_day.get("required_window_hours") or 24)
    parity_drift_class = _pick_string(runtime_parity.get("drift_class")) or "unknown"
    parity_clean = parity_drift_class in {"clean", "generated_surface_drift", "unknown"}
    parity_detail = _pick_string(runtime_parity.get("detail")) or f"drift_class={parity_drift_class}"
    latest_pass = None
    passes = completion_pass_ledger.get("passes")
    if isinstance(passes, list) and passes:
        latest_candidate = passes[-1]
        latest_pass = dict(latest_candidate) if isinstance(latest_candidate, dict) else None
    latest_validator_check = dict((latest_pass or {}).get("proofs", {}).get("validator_and_contract_healer") or {})
    checks = [
        {
            "id": "stable_operating_day",
            "label": "One full operating day of stable Athanor-core runs",
            "met": stable_day_met,
            "detail": _pick_string(stable_operating_day.get("detail"))
            or f"covered_window_hours={stable_day_hours}, required_window_hours={required_window_hours}",
        },
        {
            "id": "stale_claim_failures",
            "label": "Zero unresolved stale-claim failures",
            "met": stale_claim_count == 0
            and reconciliation_issue_count == 0
            and dispatch_status not in {"failed", "stale_dispatched_task", "spin_detected"},
            "detail": f"stale_claim_count={stale_claim_count}, reconciliation_issue_count={reconciliation_issue_count}, dispatch_status={dispatch_status}",
        },
        {
            "id": "result_backed_threshold",
            "label": "At least five result-backed or review-backed Athanor-core completions",
            "met": bool(result_evidence.get("threshold_met")),
            "detail": (
                f"result_backed={result_backed_completion_count}, "
                f"review_backed={review_backed_output_count}, "
                f"threshold_progress={int(result_evidence.get('threshold_progress') or 0)}/"
                f"{int(result_evidence.get('threshold_required') or 5)}"
            ),
        },
        {
            "id": "runtime_parity",
            "label": "Repo, controller, and proof workspace parity remain clean",
            "met": parity_clean,
            "detail": parity_detail,
        },
        {
            "id": "artifact_consistency",
            "label": "Blocker map, finish scoreboard, and publication queue remain consistent",
            "met": expected_counts == observed_counts,
            "detail": f"expected={expected_counts}, observed={observed_counts}",
        },
        {
            "id": "validator_and_contract_healer",
            "label": "Validator and contract-healer remain green across consecutive runs",
            "met": (
                validation_materialized
                and validation_passed
                and contract_healer_green
                and bool(latest_validator_check.get("met"))
            ),
            "detail": (
                f"validation_materialized={validation_materialized}, "
                f"validation_passed={validation_passed}, "
                f"contract_healer_green={contract_healer_green}, "
                f"validation_summary={_pick_string(proof.get('validation_summary')) or 'none'}, "
                f"ledger_validator_detail={_pick_string(latest_validator_check.get('detail')) or 'none'}"
            ),
        },
    ]
    open_gate = all(bool(check["met"]) for check in checks)
    return {
        "open": open_gate,
        "status": "open" if open_gate else "closed",
        "checks": checks,
        "blocking_check_ids": [str(check["id"]) for check in checks if not bool(check["met"])],
    }


def _humanize_slug(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.replace("_", " ").replace("-", " ").strip().title()


def _throughput_target(value_throughput: dict[str, Any]) -> dict[str, Any] | None:
    backlog_aging = dict(value_throughput.get("backlog_aging") or {})
    scheduled_execution = dict(value_throughput.get("scheduled_execution") or {})
    open_item_count = int(backlog_aging.get("open_item_count") or 0)
    queue_backed_jobs = int(scheduled_execution.get("queue_backed_jobs") or 0)
    if open_item_count <= 0 and queue_backed_jobs <= 0:
        return None

    family_groups = backlog_aging.get("by_family") if isinstance(backlog_aging.get("by_family"), list) else []
    project_groups = backlog_aging.get("by_project") if isinstance(backlog_aging.get("by_project"), list) else []
    top_family = dict(family_groups[0]) if family_groups else {}
    top_project = dict(project_groups[0]) if project_groups else {}

    family_id = _pick_string(top_family.get("family")) or "queue-backed-throughput"
    family_title = _humanize_slug(family_id) or "Queue-Backed Throughput"
    project_id = _pick_string(top_project.get("project_id"))
    project_title = None if project_id in {None, "", "unscoped"} else _humanize_slug(project_id)

    detail_bits = [family_title]
    if project_title:
        detail_bits.append(project_title)

    return {
        "kind": "queue_backed_throughput",
        "family_id": family_id,
        "family_title": family_title,
        "subtranche_id": project_id,
        "subtranche_title": project_title,
        "execution_class": "queue_backed_throughput",
        "approval_gated": False,
        "external_blocked": False,
        "source": "value_throughput",
        "open_item_count": open_item_count,
        "queue_backed_jobs": queue_backed_jobs,
        "detail": " / ".join(detail_bits),
    }


def build_payload(
    snapshot: dict[str, Any],
    publication_queue: dict[str, Any],
    value_throughput: dict[str, Any],
    ralph: dict[str, Any],
    contract_healer: dict[str, Any],
    stable_operating_day: dict[str, Any] | None = None,
    result_evidence: dict[str, Any] | None = None,
    completion_pass_ledger: dict[str, Any] | None = None,
    runtime_parity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finish_scoreboard = dict(snapshot.get("finish_scoreboard") or {})
    runtime_packet_inbox = dict(snapshot.get("runtime_packet_inbox") or {})
    remaining_families = _remaining_families(publication_queue)
    next_tranche = remaining_families[0] if remaining_families else None
    dispatch_status = _pick_string(snapshot.get("dispatch_status"), ralph.get("dispatch_status")) or "unknown"
    runtime_parity = dict(runtime_parity or {})
    stable_operating_day = dict(stable_operating_day or {})
    result_evidence = dict(result_evidence or {})
    completion_pass_ledger = dict(completion_pass_ledger or {})
    proof_gate = _proof_gate(
        finish_scoreboard=finish_scoreboard,
        remaining_families=remaining_families,
        value_throughput=value_throughput,
        ralph=ralph,
        contract_healer=contract_healer,
        runtime_parity=runtime_parity,
        stable_operating_day=stable_operating_day,
        result_evidence=result_evidence,
        completion_pass_ledger=completion_pass_ledger,
        dispatch_status=dispatch_status,
    )
    auto_mutation_state = (
        "repo_safe_and_reversible_runtime"
        if proof_gate["open"]
        else "repo_safe_only_runtime_and_provider_mutations_gated"
    )
    throughput_target = _throughput_target(value_throughput) if not remaining_families else None

    return {
        "generated_at": _iso_now(),
        "objective": "closure_debt" if remaining_families else "result_backed_throughput",
        "active_workstream": {
            "id": _pick_string(snapshot.get("selected_workstream_id")),
            "title": _pick_string(snapshot.get("selected_workstream_title")),
            "claim_task_id": _pick_string(snapshot.get("active_claim_task_id")),
            "claim_task_title": _pick_string(snapshot.get("active_claim_task_title")),
            "claim_lane_family": _pick_string(snapshot.get("active_claim_lane_family")),
            "dispatch_status": dispatch_status,
        },
        "remaining": {
            "cash_now": int(finish_scoreboard.get("cash_now_remaining_count") or 0),
            "bounded_follow_on": int(finish_scoreboard.get("bounded_follow_on_remaining_count") or 0),
            "program_slice": int(finish_scoreboard.get("program_slice_remaining_count") or 0),
            "family_count": len(remaining_families),
            "path_count": int(sum(int(item.get("match_count") or 0) for item in remaining_families)),
            "family_ids": [str(item["id"]) for item in remaining_families],
            "families": remaining_families,
        },
        "next_tranche": {
            "id": next_tranche.get("id") if next_tranche else None,
            "title": next_tranche.get("title") if next_tranche else None,
            "execution_class": next_tranche.get("execution_class") if next_tranche else None,
            "match_count": int(next_tranche.get("match_count") or 0) if next_tranche else 0,
            "next_action": next_tranche.get("next_action") if next_tranche else None,
            "decomposition_required": bool(next_tranche.get("decomposition_required")) if next_tranche else False,
            "decomposition_reasons": list(next_tranche.get("decomposition_reasons") or []) if next_tranche else [],
            "categories": list(next_tranche.get("categories") or []) if next_tranche else [],
        },
        "throughput_target": throughput_target,
        "queue": {
            "total": int(snapshot.get("queue_total") or finish_scoreboard.get("queue_total_count") or 0),
            "dispatchable": int(
                snapshot.get("queue_dispatchable") or finish_scoreboard.get("queue_dispatchable_count") or 0
            ),
            "blocked": int(snapshot.get("queue_blocked") or finish_scoreboard.get("queue_blocked_count") or 0),
            "suppressed": int(
                snapshot.get("suppressed_task_count") or finish_scoreboard.get("suppressed_queue_count") or 0
            ),
        },
        "runtime_packets": {
            "count": int(runtime_packet_inbox.get("packet_count") or 0),
            "approval_gated_count": int(finish_scoreboard.get("approval_gated_runtime_packet_count") or 0),
        },
        "value_throughput": {
            "result_backed_completion_count": int(value_throughput.get("result_backed_completion_count") or 0),
            "review_backed_output_count": int(value_throughput.get("review_backed_output_count") or 0),
            "stale_claim_count": int(value_throughput.get("stale_claim_count") or 0),
            "reconciliation_issue_count": int((value_throughput.get("reconciliation") or {}).get("issue_count") or 0),
            "open_item_count": int((value_throughput.get("backlog_aging") or {}).get("open_item_count") or 0),
        },
        "stable_operating_day": {
            "met": bool(stable_operating_day.get("met")),
            "covered_window_hours": float(stable_operating_day.get("covered_window_hours") or 0.0),
            "required_window_hours": int(stable_operating_day.get("required_window_hours") or 24),
            "included_pass_count": int(stable_operating_day.get("included_pass_count") or 0),
            "consecutive_healthy_pass_count": int(stable_operating_day.get("consecutive_healthy_pass_count") or 0),
            "detail": _pick_string(stable_operating_day.get("detail")),
        },
        "result_evidence": {
            "threshold_required": int(result_evidence.get("threshold_required") or 5),
            "threshold_progress": int(result_evidence.get("threshold_progress") or 0),
            "threshold_met": bool(result_evidence.get("threshold_met")),
            "result_backed_completion_count": int(result_evidence.get("result_backed_completion_count") or 0),
            "review_backed_output_count": int(result_evidence.get("review_backed_output_count") or 0),
        },
        "proof_gate": proof_gate,
        "auto_mutation": {
            "state": auto_mutation_state,
            "proof_gate_open": bool(proof_gate["open"]),
            "allowed_after_gate": AUTO_MUTATION_ALLOWED_AFTER_GATE,
            "approval_gated_classes": AUTO_MUTATION_APPROVAL_GATED_CLASSES,
            "detail": (
                "Repo-safe work can continue autonomously, but runtime, provider, auth, host, network, storage, and secret mutations stay approval-gated."
                if not proof_gate["open"]
                else "Proof gate is open; repo-safe work and reversible runtime packets may auto-execute with explicit preflight, rollback, and post-verification."
            ),
        },
        "source_artifacts": {
            "finish_scoreboard": str(FINISH_SCOREBOARD_PATH),
            "publication_deferred_family_queue": str(PUBLICATION_DEFERRED_QUEUE_PATH),
            "runtime_packet_inbox": str(RUNTIME_PACKET_INBOX_PATH),
            "value_throughput_scorecard": str(VALUE_THROUGHPUT_SCORECARD_PATH),
            "stable_operating_day": str(STABLE_OPERATING_DAY_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "completion_pass_ledger": str(COMPLETION_PASS_LEDGER_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "ralph_latest": str(RALPH_LATEST_PATH),
            "contract_healer": str(CONTRACT_HEALER_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
        },
    }


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.pop("generated_at", None)
    return normalized


def _load_existing_payload() -> dict[str, Any] | None:
    if not BLOCKER_MAP_PATH.exists():
        return None
    try:
        payload = json.loads(BLOCKER_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the canonical Athanor blocker-map artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when blocker-map.json is stale.")
    args = parser.parse_args()

    ralph = _load_optional_json(RALPH_LATEST_PATH)
    _, finish_changed = _sync_sidecar_from_ralph(ralph, "finish_scoreboard", FINISH_SCOREBOARD_PATH)
    _, runtime_changed = _sync_sidecar_from_ralph(ralph, "runtime_packet_inbox", RUNTIME_PACKET_INBOX_PATH)
    if finish_changed or runtime_changed:
        _write_json_if_changed(RALPH_LATEST_PATH, ralph)
    snapshot = build_restart_snapshot()
    publication_queue = _load_optional_json(PUBLICATION_DEFERRED_QUEUE_PATH)
    value_throughput = _load_optional_json(VALUE_THROUGHPUT_SCORECARD_PATH)
    contract_healer = _load_optional_json(CONTRACT_HEALER_PATH)
    runtime_parity = _load_optional_json(RUNTIME_PARITY_PATH)
    stable_operating_day = _load_optional_json(STABLE_OPERATING_DAY_PATH)
    result_evidence = _load_optional_json(RESULT_EVIDENCE_LEDGER_PATH)
    completion_pass_ledger = _load_optional_json(COMPLETION_PASS_LEDGER_PATH)
    payload = build_payload(
        snapshot,
        publication_queue,
        value_throughput,
        ralph,
        contract_healer,
        stable_operating_day,
        result_evidence,
        completion_pass_ledger,
        runtime_parity,
    )

    existing = _load_existing_payload()
    if existing and _normalized_payload(existing) == _normalized_payload(payload):
        payload["generated_at"] = str(existing.get("generated_at") or payload["generated_at"])

    rendered = _json_render(payload)
    if args.check:
        current = BLOCKER_MAP_PATH.read_text(encoding="utf-8") if BLOCKER_MAP_PATH.exists() else ""
        if current != rendered:
            print(f"{BLOCKER_MAP_PATH} is stale")
            return 1
        return 0

    BLOCKER_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = BLOCKER_MAP_PATH.read_text(encoding="utf-8") if BLOCKER_MAP_PATH.exists() else ""
    if current != rendered:
        BLOCKER_MAP_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(BLOCKER_MAP_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
