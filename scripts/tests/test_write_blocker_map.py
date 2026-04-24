from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_payload_surfaces_canonical_remaining_families_and_closed_proof_gate() -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    snapshot = {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "dispatch_status": "dispatched",
        "queue_total": 12,
        "queue_dispatchable": 8,
        "queue_blocked": 2,
        "suppressed_task_count": 2,
        "finish_scoreboard": {
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 4,
            "approval_gated_runtime_packet_count": 0,
        },
        "runtime_packet_inbox": {
            "packet_count": 0,
        },
    }
    publication_queue = {
        "families": [
            {
                "id": "control-plane-proof-and-ops-follow-on",
                "title": "Control-Plane Proof and Ops Follow-on",
                "execution_class": "program_slice",
                "execution_rank": 9,
                "match_count": 22,
                "next_action": "Bound the remaining proof and ops work.",
                "sample_paths": ["scripts/run_ralph_loop_pass.py", "docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md"],
            },
            {
                "id": "control-plane-registry-and-routing",
                "title": "Control-Plane Registry and Routing",
                "execution_class": "program_slice",
                "execution_rank": 6,
                "match_count": 10,
                "next_action": "Isolate registry and routing residue.",
                "sample_paths": [
                    "config/automation-backbone/executive-kernel-registry.json",
                    "projects/agents/src/athanor_agents/backbone.py",
                ],
            },
            {
                "id": "agent-route-contract-follow-on",
                "title": "Agent Route Contract Follow-on",
                "execution_class": "program_slice",
                "execution_rank": 8,
                "match_count": 13,
                "next_action": "Split route surfaces into a bounded tranche.",
                "sample_paths": [
                    "projects/agents/src/athanor_agents/routes/operator_work.py",
                    "projects/agents/tests/test_operator_work_route_contract.py",
                ],
            },
            {
                "id": "agent-execution-kernel-follow-on",
                "title": "Agent Execution Kernel Follow-on",
                "execution_class": "program_slice",
                "execution_rank": 7,
                "match_count": 18,
                "next_action": "Bound the execution kernel tranche.",
                "sample_paths": [
                    "projects/agents/src/athanor_agents/operator_work.py",
                    "projects/agents/src/athanor_agents/scheduler.py",
                    "projects/agents/tests/test_self_improvement.py",
                ],
            },
        ]
    }
    value_throughput = {
        "result_backed_completion_count": 0,
        "review_backed_output_count": 0,
        "stale_claim_count": 1,
        "backlog_aging": {"open_item_count": 13},
        "reconciliation": {"issue_count": 1},
    }
    ralph = {
        "validation": {"ran": False, "all_passed": None, "results": []},
        "executive_brief": {
            "proof": {
                "validation_all_passed": None,
                "validation_check_count": 0,
                "validation_summary": "Validation has not been materialized for this Ralph pass yet.",
            }
        },
    }
    contract_healer = {"success": False}
    runtime_parity = {
        "drift_class": "proof_workspace_drift",
        "detail": "Foundry proof workspace hash is behind DESK.",
    }

    payload = module.build_payload(
        snapshot,
        publication_queue,
        value_throughput,
        ralph,
        contract_healer,
        runtime_parity=runtime_parity,
    )

    assert payload["objective"] == "closure_debt"
    assert payload["remaining"]["program_slice"] == 4
    assert payload["remaining"]["family_ids"] == [
        "control-plane-registry-and-routing",
        "agent-execution-kernel-follow-on",
        "agent-route-contract-follow-on",
        "control-plane-proof-and-ops-follow-on",
    ]
    assert payload["next_tranche"]["id"] == "control-plane-registry-and-routing"
    assert payload["next_tranche"]["decomposition_required"] is False
    assert payload["remaining"]["families"][1]["decomposition_required"] is True
    assert payload["proof_gate"]["open"] is False
    assert payload["proof_gate"]["blocking_check_ids"] == [
        "stable_operating_day",
        "stale_claim_failures",
        "result_backed_threshold",
        "runtime_parity",
        "validator_and_contract_healer",
    ]
    assert payload["auto_mutation"]["state"] == "repo_safe_only_runtime_and_provider_mutations_gated"


def test_main_syncs_fresher_embedded_sidecars_before_writing_blocker_map(tmp_path: Path) -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    finish_path = tmp_path / "finish-scoreboard.json"
    runtime_path = tmp_path / "runtime-packet-inbox.json"
    blocker_map_path = tmp_path / "blocker-map.json"
    finish_path.write_text(
        json.dumps({"generated_at": "2026-04-19T00:00:00+00:00", "program_slice_remaining_count": 9}),
        encoding="utf-8",
    )
    runtime_path.write_text(
        json.dumps({"generated_at": "2026-04-19T00:00:00+00:00", "packet_count": 2}),
        encoding="utf-8",
    )

    module.FINISH_SCOREBOARD_PATH = finish_path
    module.RUNTIME_PACKET_INBOX_PATH = runtime_path
    module.BLOCKER_MAP_PATH = blocker_map_path
    module.RALPH_LATEST_PATH = tmp_path / "ralph-latest.json"
    module.PUBLICATION_DEFERRED_QUEUE_PATH = tmp_path / "publication-deferred-family-queue.json"
    module.VALUE_THROUGHPUT_SCORECARD_PATH = tmp_path / "value-throughput-scorecard.json"
    module.CONTRACT_HEALER_PATH = tmp_path / "contract-healer-latest.json"

    ralph = {
        "finish_scoreboard": {
            "generated_at": "2026-04-19T01:00:00+00:00",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 4,
            "approval_gated_runtime_packet_count": 0,
        },
        "runtime_packet_inbox": {
            "generated_at": "2026-04-19T01:00:00+00:00",
            "packet_count": 0,
        },
        "validation": {"ran": False, "all_passed": None, "results": []},
        "executive_brief": {"proof": {"validation_summary": "not materialized", "validation_all_passed": None}},
    }
    publication_queue = {"families": []}
    value_throughput = {"reconciliation": {"issue_count": 0}}
    contract_healer = {"success": False}

    def fake_load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return ralph
        if path == finish_path:
            return json.loads(finish_path.read_text(encoding="utf-8"))
        if path == runtime_path:
            return json.loads(runtime_path.read_text(encoding="utf-8"))
        if path == module.PUBLICATION_DEFERRED_QUEUE_PATH:
            return publication_queue
        if path == module.VALUE_THROUGHPUT_SCORECARD_PATH:
            return value_throughput
        if path == module.CONTRACT_HEALER_PATH:
            return contract_healer
        return {}

    module._load_optional_json = fake_load_optional_json
    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "dispatch_status": "dispatched",
        "queue_total": 12,
        "queue_dispatchable": 8,
        "queue_blocked": 2,
        "suppressed_task_count": 2,
        "finish_scoreboard": ralph["finish_scoreboard"],
        "runtime_packet_inbox": ralph["runtime_packet_inbox"],
    }

    argv = sys.argv[:]
    sys.argv = ["write_blocker_map.py"]
    try:
        assert module.main() == 0
    finally:
        sys.argv = argv

    synced_finish = json.loads(finish_path.read_text(encoding="utf-8"))
    synced_runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    blocker_map = json.loads(blocker_map_path.read_text(encoding="utf-8"))

    assert synced_finish["program_slice_remaining_count"] == 4
    assert synced_runtime["packet_count"] == 0
    assert blocker_map["remaining"]["program_slice"] == 4


def test_build_payload_uses_live_sample_paths_instead_of_reexpanding_cleared_path_hints() -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    snapshot = {
        "finish_scoreboard": {
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 1,
            "approval_gated_runtime_packet_count": 0,
        },
        "runtime_packet_inbox": {"packet_count": 0},
    }
    publication_queue = {
        "families": [
            {
                "id": "control-plane-registry-and-routing",
                "title": "Control-Plane Registry and Routing",
                "execution_class": "program_slice",
                "execution_rank": 6,
                "match_count": 6,
                "next_action": "Land the remaining routing residue.",
                "sample_paths": [
                    "projects/agents/config/subscription-routing-policy.yaml",
                    "projects/agents/src/athanor_agents/backbone.py",
                ],
                "path_hints": [
                    "config/automation-backbone/docs-lifecycle-registry.json",
                    "config/automation-backbone/economic-dispatch-ledger.json",
                    "config/automation-backbone/executive-kernel-registry.json",
                    "config/automation-backbone/lane-selection-matrix.json",
                    "projects/agents/config/subscription-routing-policy.yaml",
                    "projects/agents/src/athanor_agents/backbone.py",
                ],
            }
        ]
    }

    payload = module.build_payload(snapshot, publication_queue, {}, {}, {"success": False})
    family = payload["remaining"]["families"][0]

    assert family["match_count"] == 6
    assert family["sample_paths"] == [
        "projects/agents/config/subscription-routing-policy.yaml",
        "projects/agents/src/athanor_agents/backbone.py",
    ]


def test_build_payload_uses_stable_day_and_result_evidence_artifacts_for_proof_gate() -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    snapshot = {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "family:agent-execution-kernel-follow-on",
        "active_claim_task_title": "Agent Execution Kernel Follow-on",
        "active_claim_lane_family": "validation_and_checkpoint",
        "dispatch_status": "success",
        "queue_total": 7,
        "queue_dispatchable": 4,
        "queue_blocked": 1,
        "suppressed_task_count": 2,
        "finish_scoreboard": {
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "approval_gated_runtime_packet_count": 0,
        },
        "runtime_packet_inbox": {
            "packet_count": 0,
        },
    }
    publication_queue = {"families": []}
    value_throughput = {
        "result_backed_completion_count": 0,
        "review_backed_output_count": 0,
        "stale_claim_count": 0,
        "reconciliation": {"issue_count": 0},
    }
    stable_operating_day = {
        "required_window_hours": 24,
        "covered_window_hours": 24.6,
        "included_pass_count": 9,
        "consecutive_healthy_pass_count": 9,
        "validator_contract_healer_streak": 9,
        "stale_claim_streak": 9,
        "artifact_consistency_streak": 9,
        "met": True,
        "detail": "Stable operating-day window is satisfied.",
    }
    result_evidence = {
        "threshold_required": 5,
        "threshold_progress": 5,
        "threshold_met": True,
        "result_backed_completion_count": 3,
        "review_backed_output_count": 2,
    }
    completion_pass_ledger = {
        "pass_count": 9,
        "passes": [
            {
                "pass_id": "continuity-pass-001",
                "finished_at": "2026-04-19T04:00:00+00:00",
                "proofs": {
                    "validator_and_contract_healer": {
                        "met": True,
                        "detail": "Validation and contract-healer were green on this pass.",
                    }
                },
            }
        ],
    }
    ralph = {
        "validation": {"ran": True, "all_passed": True, "results": []},
        "executive_brief": {
            "proof": {
                "validation_all_passed": True,
                "validation_check_count": 3,
                "validation_summary": "Validation materialized and passed.",
            }
        },
    }
    contract_healer = {"success": True}

    payload = module.build_payload(
        snapshot,
        publication_queue,
        value_throughput,
        ralph,
        contract_healer,
        stable_operating_day,
        result_evidence,
        completion_pass_ledger,
    )

    assert payload["proof_gate"]["open"] is True
    assert payload["proof_gate"]["blocking_check_ids"] == []
    assert payload["stable_operating_day"]["met"] is True
    assert payload["stable_operating_day"]["covered_window_hours"] == 24.6
    assert payload["result_evidence"]["threshold_progress"] == 5
    assert payload["result_evidence"]["threshold_met"] is True
    assert payload["auto_mutation"]["proof_gate_open"] is True


def test_build_payload_surfaces_throughput_target_when_closure_debt_is_zero() -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    snapshot = {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "dispatch_status": "success",
        "finish_scoreboard": {
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "approval_gated_runtime_packet_count": 0,
        },
        "runtime_packet_inbox": {"packet_count": 0},
    }
    publication_queue = {"families": []}
    value_throughput = {
        "backlog_aging": {
            "open_item_count": 15,
            "by_family": [{"family": "builder", "count": 15, "oldest_age_hours": 10.0, "average_age_hours": 4.0}],
            "by_project": [{"project_id": "unscoped", "count": 15, "oldest_age_hours": 10.0, "average_age_hours": 4.0}],
        },
        "scheduled_execution": {"queue_backed_jobs": 2},
        "reconciliation": {"issue_count": 0},
    }

    payload = module.build_payload(snapshot, publication_queue, value_throughput, {}, {"success": True})

    assert payload["objective"] == "result_backed_throughput"
    assert payload["remaining"]["family_count"] == 0
    assert payload["throughput_target"] == {
        "kind": "queue_backed_throughput",
        "family_id": "builder",
        "family_title": "Builder",
        "subtranche_id": "unscoped",
        "subtranche_title": None,
        "execution_class": "queue_backed_throughput",
        "approval_gated": False,
        "external_blocked": False,
        "source": "value_throughput",
        "open_item_count": 15,
        "queue_backed_jobs": 2,
        "detail": "Builder",
    }


def test_main_rewrites_stale_ralph_embedded_finish_scoreboard_from_fresher_sidecar(tmp_path: Path) -> None:
    module = _load_module(
        f"write_blocker_map_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_map.py",
    )

    finish_path = tmp_path / "finish-scoreboard.json"
    runtime_path = tmp_path / "runtime-packet-inbox.json"
    blocker_map_path = tmp_path / "blocker-map.json"
    ralph_path = tmp_path / "ralph-latest.json"
    publication_queue_path = tmp_path / "publication-deferred-family-queue.json"
    value_throughput_path = tmp_path / "value-throughput-scorecard.json"
    contract_healer_path = tmp_path / "contract-healer-latest.json"
    stable_day_path = tmp_path / "stable-operating-day.json"
    result_evidence_path = tmp_path / "result-evidence-ledger.json"
    completion_pass_ledger_path = tmp_path / "completion-pass-ledger.json"

    finish_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T04:30:00+00:00",
                "cash_now_remaining_count": 0,
                "bounded_follow_on_remaining_count": 0,
                "program_slice_remaining_count": 3,
                "approval_gated_runtime_packet_count": 0,
            }
        ),
        encoding="utf-8",
    )
    runtime_path.write_text(
        json.dumps({"generated_at": "2026-04-19T04:30:00+00:00", "packet_count": 0}),
        encoding="utf-8",
    )
    ralph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T04:10:00+00:00",
                "finish_scoreboard": {
                    "generated_at": "2026-04-19T04:00:00+00:00",
                    "cash_now_remaining_count": 0,
                    "bounded_follow_on_remaining_count": 0,
                    "program_slice_remaining_count": 4,
                    "approval_gated_runtime_packet_count": 0,
                },
                "runtime_packet_inbox": {
                    "generated_at": "2026-04-19T04:00:00+00:00",
                    "packet_count": 0,
                },
                "validation": {"ran": False, "all_passed": None, "results": []},
                "executive_brief": {"proof": {"validation_summary": "not materialized", "validation_all_passed": None}},
            }
        ),
        encoding="utf-8",
    )
    publication_queue_path.write_text(json.dumps({"families": []}), encoding="utf-8")
    value_throughput_path.write_text(json.dumps({"reconciliation": {"issue_count": 0}}), encoding="utf-8")
    contract_healer_path.write_text(json.dumps({"success": False}), encoding="utf-8")
    stable_day_path.write_text(
        json.dumps({"met": False, "covered_window_hours": 0, "required_window_hours": 24}),
        encoding="utf-8",
    )
    result_evidence_path.write_text(
        json.dumps(
            {
                "threshold_required": 5,
                "threshold_progress": 0,
                "threshold_met": False,
                "result_backed_completion_count": 0,
                "review_backed_output_count": 0,
            }
        ),
        encoding="utf-8",
    )
    completion_pass_ledger_path.write_text(json.dumps({"pass_count": 0, "passes": []}), encoding="utf-8")

    module.FINISH_SCOREBOARD_PATH = finish_path
    module.RUNTIME_PACKET_INBOX_PATH = runtime_path
    module.BLOCKER_MAP_PATH = blocker_map_path
    module.RALPH_LATEST_PATH = ralph_path
    module.PUBLICATION_DEFERRED_QUEUE_PATH = publication_queue_path
    module.VALUE_THROUGHPUT_SCORECARD_PATH = value_throughput_path
    module.CONTRACT_HEALER_PATH = contract_healer_path
    module.STABLE_OPERATING_DAY_PATH = stable_day_path
    module.RESULT_EVIDENCE_LEDGER_PATH = result_evidence_path
    module.COMPLETION_PASS_LEDGER_PATH = completion_pass_ledger_path

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "dispatch_status": "dispatched",
        "queue_total": 12,
        "queue_dispatchable": 8,
        "queue_blocked": 2,
        "suppressed_task_count": 2,
        "finish_scoreboard": json.loads(finish_path.read_text(encoding="utf-8")),
        "runtime_packet_inbox": json.loads(runtime_path.read_text(encoding="utf-8")),
    }

    argv = sys.argv[:]
    sys.argv = ["write_blocker_map.py"]
    try:
        assert module.main() == 0
    finally:
        sys.argv = argv

    synced_ralph = json.loads(ralph_path.read_text(encoding="utf-8"))
    assert synced_ralph["finish_scoreboard"]["program_slice_remaining_count"] == 3
