from __future__ import annotations

import asyncio
import importlib.util
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


def test_build_payload_tracks_operator_and_product_value_with_concrete_entries() -> None:
    module = _load_module(
        f"write_autonomous_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomous_value_proof.py",
    )

    async def _backlog_records():
        return [
            {
                "id": "backlog-operator-1",
                "title": "Land bounded repo-safe fix",
                "family": "builder",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "result-1",
                "review_id": "",
                "value_class": "operator_value",
                "deliverable_kind": "code_patch",
                "deliverable_refs": ["reports/proof/operator-fix.json"],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "hybrid",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T04:10:00+00:00",
                "acceptance_proof_refs": ["reports/proof/operator-fix-acceptance.json"],
                "source_ref": "task-operator-1",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
            {
                "id": "backlog-operator-2",
                "title": "Publish runtime packet report",
                "family": "runtime_ops",
                "project_id": "athanor",
                "status": "waiting_approval",
                "result_id": "",
                "review_id": "review-2",
                "value_class": "operator_value",
                "deliverable_kind": "report",
                "deliverable_refs": ["docs/operations/runtime-packet.md"],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "operator_acceptance",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T04:11:00+00:00",
                "acceptance_proof_refs": ["reports/proof/runtime-packet-acceptance.json"],
                "source_ref": "task-operator-2",
                "metadata": {
                    "verification_status": "needs_review",
                    "operator_steered": False,
                },
            },
            {
                "id": "backlog-product-1",
                "title": "Ship dashboard value proof",
                "family": "builder",
                "project_id": "dashboard",
                "status": "completed",
                "result_id": "result-3",
                "review_id": "",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/app/page.tsx"],
                "beneficiary_surface": "dashboard",
                "acceptance_mode": "hybrid",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T04:12:00+00:00",
                "acceptance_proof_refs": ["reports/proof/dashboard-acceptance.json"],
                "source_ref": "task-product-1",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
            {
                "id": "backlog-rejected-1",
                "title": "Bookkeeping refresh",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "result-4",
                "review_id": "",
                "value_class": "control_plane",
                "deliverable_kind": "report",
                "deliverable_refs": ["reports/truth-inventory/steady-state-status.json"],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "automated",
                "accepted_by": "",
                "accepted_at": "",
                "acceptance_proof_refs": [],
                "source_ref": "task-control-plane-1",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
        ]

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return await _backlog_records()

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    payload = asyncio.run(module.build_payload())

    assert payload["accepted_operator_value_count"] == 2
    assert payload["accepted_product_value_count"] == 1
    assert payload["stage_status"]["operator_value"]["met"] is False
    assert payload["stage_status"]["product_value"]["met"] is False
    assert [entry["packet_id"] for entry in payload["accepted_entries"]] == [
        "result-1",
        "review-2",
        "result-3",
    ]
    assert payload["accepted_entries"][0]["deliverable_refs"] == ["reports/proof/operator-fix.json"]
    assert payload["accepted_entries"][2]["beneficiary_surface"] == "dashboard"
    assert payload["disqualified_entries"][0]["disqualification_reason"] == "control_plane_only"


def test_build_payload_does_not_reject_capacity_truth_artifacts_as_bookkeeping_only() -> None:
    module = _load_module(
        f"write_autonomous_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomous_value_proof.py",
    )

    async def _backlog_records():
        return [
            {
                "id": "backlog-operator-capacity-1",
                "title": "Accepted operator-value proof: Local Bulk Sovereign",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "result-capacity-1",
                "review_id": "",
                "value_class": "operator_value",
                "deliverable_kind": "report",
                "deliverable_refs": [
                    "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                    "reports/truth-inventory/capacity-telemetry.json",
                    "reports/truth-inventory/quota-truth.json",
                ],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "automated",
                "accepted_by": "system",
                "accepted_at": "2026-04-20T04:15:00+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-capacity.json"],
                "source_ref": "task-capacity-1",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
        ]

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return await _backlog_records()

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    payload = asyncio.run(module.build_payload())

    assert payload["accepted_operator_value_count"] == 1
    assert payload["accepted_entries"][0]["packet_id"] == "result-capacity-1"
    assert payload["failure_counts"]["bookkeeping_only"] == 0


def test_build_payload_merges_live_backlog_acceptance_over_local_pending_record() -> None:
    module = _load_module(
        f"write_autonomous_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomous_value_proof.py",
    )

    async def _backlog_records():
        return [
            {
                "id": "backlog-dashboard-proof",
                "title": "Produce a visible dashboard value proof",
                "family": "builder",
                "project_id": "dashboard",
                "status": "completed",
                "result_id": "result-dashboard-1",
                "review_id": "",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/features/overview/command-center.tsx"],
                "beneficiary_surface": "dashboard",
                "acceptance_mode": "hybrid",
                "accepted_by": "",
                "accepted_at": "",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-proof.json"],
                "source_ref": "task-dashboard-proof",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
        ]

    async def _governed_truth():
        return {"execution": {"agent_server_base_url": "http://example.test:9000"}}

    async def _backlog_api(_governed_truth):
        return [
            {
                "id": "backlog-dashboard-proof-acceptance",
                "title": "Accepted product-value proof: Dashboard command center autonomous value card",
                "family": "builder",
                "project_id": "dashboard",
                "status": "completed",
                "result_id": "result-dashboard-1",
                "review_id": "",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/features/overview/command-center.tsx"],
                "beneficiary_surface": "dashboard",
                "acceptance_mode": "automated",
                "accepted_by": "system",
                "accepted_at": "2026-04-20T14:38:01.139818+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-dashboard-proof.json"],
                "source_ref": "autonomous-value-acceptance:backlog-dashboard-proof",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
        ]

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    payload = asyncio.run(module.build_payload())

    assert payload["accepted_product_value_count"] == 1
    assert payload["stage_status"]["product_value"]["accepted_count"] == 1
    assert payload["accepted_entries"][0]["packet_id"] == "result-dashboard-1"
    assert payload["accepted_entries"][0]["accepted_by"] == "system"
    assert payload["failure_counts"]["deliverable_present_but_not_accepted"] == 0


def test_build_payload_uses_latest_accepted_timestamp_for_latest_entry() -> None:
    module = _load_module(
        f"write_autonomous_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomous_value_proof.py",
    )

    async def _backlog_records():
        return [
            {
                "id": "backlog-product-proof",
                "title": "Accepted product-value proof: Later dashboard proof",
                "family": "builder",
                "project_id": "dashboard",
                "status": "completed",
                "result_id": "result-product-1",
                "review_id": "",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/features/overview/command-center.tsx"],
                "beneficiary_surface": "dashboard",
                "acceptance_mode": "automated",
                "accepted_by": "system",
                "accepted_at": "2026-04-20T14:38:01.139818+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-product-proof.json"],
                "source_ref": "autonomous-value-acceptance:backlog-product-proof",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
            {
                "id": "backlog-operator-proof",
                "title": "Accepted operator-value proof: Earlier report",
                "family": "research_audit",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "result-operator-1",
                "review_id": "",
                "value_class": "operator_value",
                "deliverable_kind": "report",
                "deliverable_refs": ["docs/operations/earlier-report.md"],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "automated",
                "accepted_by": "system",
                "accepted_at": "2026-04-20T04:37:54.505907+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-operator-proof.json"],
                "source_ref": "autonomous-value-acceptance:backlog-operator-proof",
                "metadata": {
                    "verification_passed": True,
                    "operator_steered": False,
                },
            },
        ]

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return await _backlog_records()

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    payload = asyncio.run(module.build_payload())

    assert payload["latest_accepted_entry"]["packet_id"] == "result-product-1"
    assert payload["latest_accepted_entry"]["value_class"] == "product_value"


def test_render_against_existing_preserves_generated_at_for_staleness_checks() -> None:
    module = _load_module(
        f"write_autonomous_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomous_value_proof.py",
    )

    async def _backlog_records():
        return []

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return []

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    times = iter(
        [
            "2026-04-20T20:30:00+00:00",
            "2026-04-20T20:31:00+00:00",
        ]
    )
    module._iso_now = lambda: next(times)
    first_payload = asyncio.run(module.build_payload())
    first_json = module._json_render(first_payload)
    first_md = module._markdown(first_payload)

    second_payload = asyncio.run(module.build_payload())
    comparable_json, comparable_md = module._render_against_existing(second_payload, first_json)

    assert comparable_json == first_json
    assert comparable_md == first_md
