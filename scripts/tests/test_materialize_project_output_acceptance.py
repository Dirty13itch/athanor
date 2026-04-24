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


def test_materialize_hybrid_candidate_writes_pending_acceptance_and_updates_candidate(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_project_output_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_project_output_acceptance.py",
    )
    module.ACCEPTANCE_OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T21:00:00+00:00"
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(base_url, token, path, *, method="GET", payload=None, timeout=20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {"backlog": []}
        assert method == "POST"
        return 200, {"backlog": {"id": "backlog-review-eoq-alpha"}}

    module._request_agent_json = fake_request

    candidate_path = tmp_path / "eoq-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "candidate_id": "eoq-courtyard-alpha",
                "project_id": "eoq",
                "title": "EOQ courtyard alpha",
                "approval_posture": "hybrid",
                "acceptance_state": "pending_materialization",
                "deliverable_kind": "content_artifact",
                "deliverable_refs": ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
                "beneficiary_surface": "eoq",
            }
        ),
        encoding="utf-8",
    )

    result = module.materialize_candidate_acceptance(candidate_path)

    assert result["status"] == "pending_approval"
    assert result["acceptance_backlog_id"] == "backlog-review-eoq-alpha"
    updated_candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert updated_candidate["acceptance_state"] == "pending_acceptance"
    assert updated_candidate["acceptance_backlog_id"] == "backlog-review-eoq-alpha"
    assert updated_candidate["accepted_by"] is None
    assert len(updated_candidate["acceptance_proof_refs"]) == 1
    acceptance_artifact = tmp_path / "acceptance" / "eoq-courtyard-alpha.json"
    assert acceptance_artifact.exists()
    acceptance_payload = json.loads(acceptance_artifact.read_text(encoding="utf-8"))
    assert acceptance_payload["accepted"] is False
    assert acceptance_payload["project_id"] == "eoq"
    assert calls[0][0] == "GET"
    assert calls[0][1] == "/v1/operator/backlog?limit=200"
    assert calls[1][0] == "POST"
    assert calls[1][1] == "/v1/operator/backlog"
    assert calls[1][2]["approval_mode"] == "operator"
    assert calls[1][2]["dispatch_policy"] == "manual_only"


def test_approve_hybrid_candidate_creates_completed_acceptance_and_updates_candidate(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_project_output_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_project_output_acceptance.py",
    )
    module.ACCEPTANCE_OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T23:20:00+00:00"
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(base_url, token, path, *, method="GET", payload=None, timeout=20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {
                "backlog": [
                    {
                        "id": "backlog-review-eoq-alpha",
                        "source_ref": "project-output-candidate:eoq-courtyard-alpha",
                        "status": "captured",
                        "metadata": {"source_ref": "project-output-candidate:eoq-courtyard-alpha"},
                    }
                ]
            }
        if method == "POST" and path == "/v1/operator/backlog":
            return 200, {"backlog": {"id": "backlog-accept-eoq-alpha"}}
        if method == "POST" and path == "/v1/operator/backlog/backlog-accept-eoq-alpha/transition":
            return 200, {"backlog": {"id": "backlog-accept-eoq-alpha", "status": "completed"}}
        if method == "POST" and path == "/v1/operator/backlog/backlog-review-eoq-alpha/transition":
            return 200, {"backlog": {"id": "backlog-review-eoq-alpha", "status": "archived"}}
        raise AssertionError((method, path, payload))

    module._request_agent_json = fake_request

    candidate_path = tmp_path / "eoq-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "candidate_id": "eoq-courtyard-alpha",
                "project_id": "eoq",
                "title": "EOQ courtyard alpha",
                "approval_posture": "hybrid",
                "acceptance_state": "pending_acceptance",
                "acceptance_backlog_id": "backlog-review-eoq-alpha",
                "verification_status": "passed",
                "deliverable_kind": "content_artifact",
                "deliverable_refs": ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
                "beneficiary_surface": "eoq",
            }
        ),
        encoding="utf-8",
    )

    result = module.materialize_candidate_acceptance(candidate_path, approve_hybrid=True, accepted_by="Shaun")

    assert result["status"] == "completed"
    assert result["acceptance_backlog_id"] == "backlog-accept-eoq-alpha"
    assert result["acceptance_review_backlog_id"] == "backlog-review-eoq-alpha"
    updated_candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert updated_candidate["acceptance_state"] == "accepted"
    assert updated_candidate["accepted_by"] == "Shaun"
    assert updated_candidate["accepted_at"] == "2026-04-20T23:20:00+00:00"
    assert updated_candidate["acceptance_backlog_id"] == "backlog-accept-eoq-alpha"
    assert updated_candidate["acceptance_review_backlog_id"] == "backlog-review-eoq-alpha"
    acceptance_artifact = tmp_path / "acceptance" / "eoq-courtyard-alpha.json"
    assert acceptance_artifact.exists()
    acceptance_payload = json.loads(acceptance_artifact.read_text(encoding="utf-8"))
    assert acceptance_payload["accepted"] is True
    assert acceptance_payload["accepted_by"] == "Shaun"
    assert acceptance_payload["accepted_at"] == "2026-04-20T23:20:00+00:00"
    create_call = calls[1]
    assert create_call[0] == "POST"
    assert create_call[1] == "/v1/operator/backlog"
    assert create_call[2]["source_ref"] == "project-output-accepted:eoq-courtyard-alpha"
    assert create_call[2]["acceptance_mode"] == "hybrid"
    assert create_call[2]["accepted_by"] == "Shaun"
    assert create_call[2]["operator_steered"] is False
    assert create_call[2]["metadata"]["result_id"] == "eoq-courtyard-alpha"
    assert create_call[2]["metadata"]["project_id"] == "eoq"
    assert create_call[2]["metadata"]["source_ref"] == "project-output-accepted:eoq-courtyard-alpha"


def test_approve_hybrid_candidate_repairs_existing_unready_acceptance_in_place(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_project_output_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_project_output_acceptance.py",
    )
    module.ACCEPTANCE_OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T23:26:10.914431+00:00"
    calls: list[tuple[str, str, dict[str, object] | None]] = []
    repaired_records: list[dict[str, object]] = []

    def fake_request(base_url, token, path, *, method="GET", payload=None, timeout=20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {
                "backlog": [
                    {
                        "id": "backlog-review-eoq-alpha",
                        "source_ref": "project-output-candidate:eoq-courtyard-alpha",
                        "status": "captured",
                        "metadata": {"source_ref": "project-output-candidate:eoq-courtyard-alpha"},
                    },
                    {
                        "id": "backlog-accept-eoq-alpha",
                        "title": "Accepted project output: EOQ courtyard alpha",
                        "status": "completed",
                        "work_class": "project_output",
                        "scope_type": "project",
                        "scope_id": "eoq",
                        "owner_agent": "coding-agent",
                        "approval_mode": "none",
                        "dispatch_policy": "planner_eligible",
                        "created_at": 10.0,
                        "updated_at": 20.0,
                        "completed_at": 20.0,
                        "metadata": {"candidate_id": "eoq-courtyard-alpha"},
                    },
                ]
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-review-eoq-alpha/transition":
            return 200, {"backlog": {"id": "backlog-review-eoq-alpha", "status": "archived"}}
        raise AssertionError((method, path, payload))

    module._request_agent_json = fake_request
    module._upsert_backlog_record_direct = lambda record: repaired_records.append(dict(record)) or True

    candidate_path = tmp_path / "eoq-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "candidate_id": "eoq-courtyard-alpha",
                "project_id": "eoq",
                "title": "EOQ courtyard alpha",
                "approval_posture": "hybrid",
                "acceptance_state": "pending_acceptance",
                "acceptance_backlog_id": "backlog-review-eoq-alpha",
                "verification_status": "passed",
                "deliverable_kind": "content_artifact",
                "deliverable_refs": ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
                "beneficiary_surface": "eoq",
            }
        ),
        encoding="utf-8",
    )

    result = module.materialize_candidate_acceptance(candidate_path, approve_hybrid=True, accepted_by="Shaun")

    assert result["status"] == "completed"
    assert result["acceptance_backlog_id"] == "backlog-accept-eoq-alpha"
    assert repaired_records[0]["result_id"] == "eoq-courtyard-alpha"
    assert repaired_records[0]["source_ref"] == "project-output-accepted:eoq-courtyard-alpha"
    assert repaired_records[0]["project_id"] == "eoq"
    assert repaired_records[0]["metadata"]["candidate_id"] == "eoq-courtyard-alpha"
    assert not any(call[1] == "/v1/operator/backlog" for call in calls if call[0] == "POST")


def test_materialize_candidate_acceptance_archives_duplicate_accepted_backlogs(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_project_output_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_project_output_acceptance.py",
    )
    module.ACCEPTANCE_OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T23:30:00+00:00"
    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(base_url, token, path, *, method="GET", payload=None, timeout=20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {
                "backlog": [
                    {
                        "id": "backlog-accept-stale",
                        "title": "Accepted project output: EOQ courtyard alpha",
                        "status": "completed",
                        "work_class": "project_output",
                        "scope_type": "project",
                        "scope_id": "eoq",
                        "owner_agent": "coding-agent",
                        "created_at": 10.0,
                        "updated_at": 20.0,
                        "completed_at": 20.0,
                        "metadata": {"candidate_id": "eoq-courtyard-alpha"},
                    },
                    {
                        "id": "backlog-accept-canonical",
                        "title": "Accepted project output: EOQ courtyard alpha",
                        "status": "completed",
                        "work_class": "project_output",
                        "project_id": "eoq",
                        "result_id": "eoq-courtyard-alpha",
                        "source_ref": "project-output-accepted:eoq-courtyard-alpha",
                        "created_at": 11.0,
                        "updated_at": 30.0,
                        "completed_at": 30.0,
                        "metadata": {
                            "candidate_id": "eoq-courtyard-alpha",
                            "project_id": "eoq",
                            "result_id": "eoq-courtyard-alpha",
                            "source_ref": "project-output-accepted:eoq-courtyard-alpha",
                            "accepted_by": "Shaun",
                            "accepted_at": "2026-04-20T23:28:36.213889+00:00",
                        },
                    },
                ]
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-accept-stale/transition":
            return 200, {"backlog": {"id": "backlog-accept-stale", "status": "archived"}}
        raise AssertionError((method, path, payload))

    module._request_agent_json = fake_request

    candidate_path = tmp_path / "eoq-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "candidate_id": "eoq-courtyard-alpha",
                "project_id": "eoq",
                "title": "EOQ courtyard alpha",
                "approval_posture": "hybrid",
                "acceptance_state": "accepted",
                "verification_status": "passed",
                "deliverable_kind": "content_artifact",
                "deliverable_refs": ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
                "beneficiary_surface": "eoq",
            }
        ),
        encoding="utf-8",
    )

    result = module.materialize_candidate_acceptance(candidate_path)

    assert result["status"] == "already_completed"
    assert result["acceptance_backlog_id"] == "backlog-accept-canonical"
    assert result["archived_duplicate_backlog_ids"] == ["backlog-accept-stale"]
