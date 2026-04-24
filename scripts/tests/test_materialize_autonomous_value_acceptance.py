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


def test_stage_acceptance_creates_backlog_with_explicit_value_fields(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_autonomous_value_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_autonomous_value_acceptance.py",
    )
    module.OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T05:10:00+00:00"

    rows = [
        {
            "id": "backlog-source-1",
            "title": "Reference and Archive Prune",
            "family": "research_audit",
            "project_id": "athanor",
            "scope_type": "global",
            "scope_id": "athanor",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "evidence_bundle",
            "status": "completed",
            "result_id": "result-1",
            "source_ref": "deferred_family:reference-and-archive-prune",
            "metadata": {
                "verification_status": "passed",
                "latest_task_id": "task-1",
                "latest_run_id": "result-1",
                "proof_artifacts": ["docs/operations/REPO-ROOTS-REPORT.md"],
            },
        }
    ]
    plan = {
        "source_backlog_id": "backlog-source-1",
        "title": "Accepted operator-value proof: Reference and Archive Prune",
        "owner_agent": "research-agent",
        "work_class": "repo_audit",
        "family": "research_audit",
        "value_class": "operator_value",
        "deliverable_kind": "report",
        "deliverable_refs": ["docs/operations/REPO-ROOTS-REPORT.md"],
        "beneficiary_surface": "athanor_core",
        "acceptance_summary": "Accepted operator-value proof.",
    }

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if path == "/v1/operator/backlog":
            return 200, {"backlog": {"id": "backlog-accept-1", "status": "captured"}}
        if path == "/v1/operator/backlog/backlog-accept-1/transition":
            return 200, {"backlog": {"id": "backlog-accept-1", "status": "completed"}}
        raise AssertionError(f"unexpected request {method} {path}")

    module._request_agent_json = fake_request

    result = module._stage_acceptance(
        base_url="http://agent.local",
        token="",
        rows=rows,
        plan=plan,
    )

    assert result["status"] == "completed"
    create_payload = calls[0][2] or {}
    assert create_payload["family"] == "research_audit"
    assert create_payload["result_id"] == "result-1"
    assert create_payload["value_class"] == "operator_value"
    assert create_payload["deliverable_kind"] == "report"
    assert create_payload["deliverable_refs"] == ["docs/operations/REPO-ROOTS-REPORT.md"]
    assert create_payload["beneficiary_surface"] == "athanor_core"
    assert create_payload["acceptance_mode"] == "automated"
    assert create_payload["accepted_by"] == "system"
    assert create_payload["accepted_at"] == "2026-04-20T05:10:00+00:00"
    assert len(create_payload["acceptance_proof_refs"]) == 1
    assert create_payload["acceptance_proof_refs"][0].endswith("backlog-source-1.json")
    assert create_payload["operator_steered"] is False
    artifact = tmp_path / "acceptance" / "backlog-source-1.json"
    assert artifact.exists()
    artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert artifact_payload["value_class"] == "operator_value"
    assert artifact_payload["source_result_id"] == "result-1"


def test_stage_acceptance_reuses_existing_incomplete_acceptance_backlog(tmp_path: Path) -> None:
    module = _load_module(
        f"materialize_autonomous_value_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_autonomous_value_acceptance.py",
    )
    module.OUTPUT_DIR = tmp_path / "acceptance"
    module._iso_now = lambda: "2026-04-20T05:15:00+00:00"

    rows = [
        {
            "id": "backlog-source-1",
            "title": "Local Bulk Sovereign",
            "family": "maintenance",
            "project_id": "athanor",
            "scope_type": "global",
            "scope_id": "athanor",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "status": "completed",
            "result_id": "result-2",
            "source_ref": "burn_class:local_bulk_sovereign",
            "metadata": {
                "verification_status": "passed",
                "latest_task_id": "task-2",
                "latest_run_id": "result-2",
            },
        },
        {
            "id": "backlog-accept-existing",
            "title": "Accepted operator-value proof: Local Bulk Sovereign",
            "status": "captured",
            "source_ref": "autonomous-value-acceptance:backlog-source-1",
            "metadata": {
                "source_ref": "autonomous-value-acceptance:backlog-source-1",
            },
        },
    ]
    plan = {
        "source_backlog_id": "backlog-source-1",
        "title": "Accepted operator-value proof: Local Bulk Sovereign",
        "owner_agent": "coding-agent",
        "work_class": "maintenance",
        "family": "maintenance",
        "value_class": "operator_value",
        "deliverable_kind": "report",
        "deliverable_refs": ["reports/truth-inventory/quota-truth.json"],
        "beneficiary_surface": "athanor_core",
        "acceptance_summary": "Accepted operator-value proof.",
    }

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if path == "/v1/operator/backlog/backlog-accept-existing/transition":
            return 200, {"backlog": {"id": "backlog-accept-existing", "status": "completed"}}
        raise AssertionError(f"unexpected request {method} {path}")

    module._request_agent_json = fake_request

    result = module._stage_acceptance(
        base_url="http://agent.local",
        token="",
        rows=rows,
        plan=plan,
    )

    assert result["status"] == "completed"
    assert result["acceptance_backlog_id"] == "backlog-accept-existing"
    assert len(calls) == 1
    method, path, payload = calls[0]
    assert method == "POST"
    assert path == "/v1/operator/backlog/backlog-accept-existing/transition"
    assert payload["reason"] == "Finalize autonomous value acceptance for backlog-source-1"
    assert payload["status"] == "completed"
    assert payload["note"] == "Automated acceptance materialized from a verified autonomous completion."


def test_build_plan_from_source_backlog_infers_product_value_fields() -> None:
    module = _load_module(
        f"materialize_autonomous_value_acceptance_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "materialize_autonomous_value_acceptance.py",
    )

    rows = [
        {
            "id": "backlog-product-1",
            "title": "Produce a visible builder front-door value proof",
            "owner_agent": "coding-agent",
            "work_class": "system_improvement",
            "family": "builder",
            "value_class": "product_value",
            "deliverable_kind": "ui_change",
            "deliverable_refs": ["projects/dashboard/src/features/operator/operator-console.tsx"],
            "beneficiary_surface": "builder",
            "metadata": {
                "family": "builder",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/features/operator/operator-console.tsx"],
                "beneficiary_surface": "builder",
            },
        }
    ]

    plan = module._build_plan_from_source_backlog(
        rows,
        source_backlog_id="backlog-product-1",
    )

    assert plan == {
        "source_backlog_id": "backlog-product-1",
        "title": "Accepted product-value proof: Produce a visible builder front-door value proof",
        "owner_agent": "coding-agent",
        "work_class": "system_improvement",
        "family": "builder",
        "value_class": "product_value",
        "deliverable_kind": "ui_change",
        "deliverable_refs": ["projects/dashboard/src/features/operator/operator-console.tsx"],
        "beneficiary_surface": "builder",
        "acceptance_summary": "Accepted product-value proof for builder with deliverable refs: projects/dashboard/src/features/operator/operator-console.tsx.",
    }
