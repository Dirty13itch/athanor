from __future__ import annotations

from athanor_agents.autonomous_queue import redispatch_block_reason


def test_redispatch_block_reason_ignores_task_and_result_ids_without_evidence_delta(monkeypatch) -> None:
    monkeypatch.setattr(
        "athanor_agents.autonomous_queue.get_completion_program_registry",
        lambda: {
            "automation_anti_spin_policy": {
                "require_new_artifact_or_state_delta": True,
                "same_task_claims_12h_threshold": 1,
                "same_task_claims_24h_threshold": 1,
            }
        },
    )
    monkeypatch.setattr("athanor_agents.autonomous_queue.time.time", lambda: 1000.0)

    record = {
        "id": "backlog-1",
        "status": "blocked",
        "blocking_reason": "verification_evidence_missing",
        "result_id": "run-new",
        "review_id": "",
        "metadata": {
            "latest_run_id": "task-new",
            "verification_status": "missing_evidence",
            "verification_passed": False,
            "dispatch_history": [
                {
                    "timestamp": 995.0,
                    "reason": "old",
                    "evidence_signature": "blocked|||verification_evidence_missing|missing_evidence|false||",
                }
            ],
        },
    }

    assert "no new evidence" in redispatch_block_reason(record)


def test_redispatch_block_reason_allows_new_proof_artifact_delta(monkeypatch) -> None:
    monkeypatch.setattr(
        "athanor_agents.autonomous_queue.get_completion_program_registry",
        lambda: {
            "automation_anti_spin_policy": {
                "require_new_artifact_or_state_delta": True,
                "same_task_claims_12h_threshold": 1,
                "same_task_claims_24h_threshold": 1,
            }
        },
    )
    monkeypatch.setattr("athanor_agents.autonomous_queue.time.time", lambda: 1000.0)

    record = {
        "id": "backlog-1",
        "status": "blocked",
        "blocking_reason": "verification_evidence_missing",
        "result_id": "run-new",
        "review_id": "",
        "metadata": {
            "latest_run_id": "task-new",
            "verification_status": "missing_evidence",
            "verification_passed": False,
            "proof_artifacts": ["reports/truth-inventory/quota-truth.json"],
            "dispatch_history": [
                {
                    "timestamp": 995.0,
                    "reason": "old",
                    "evidence_signature": "blocked|||verification_evidence_missing|missing_evidence|false||",
                }
            ],
        },
    }

    assert redispatch_block_reason(record) == ""
