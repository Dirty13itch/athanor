from __future__ import annotations

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


def test_build_payload_flags_missing_shared_projection_and_second_clean_pass() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={"summary": {}},
        operator_mobile_summary={"project_factory": {"top_priority_project_id": "eoq"}},
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 1, "pending_candidate_count": 1, "stage_status": {"met": False}},
        previous_status=None,
        ui_audit_last_run={"generatedAt": "2026-04-20T21:00:00+00:00", "failures": [], "results": [{"label": "dashboard", "returncode": 0}]},
        live_dashboard_smoke={},
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source="export function ProjectsConsole() { return null }",
        operator_console_source="export function OperatorConsole() { return null }",
        root_command_center_source="export function CommandCenter() { return null }",
        project_factory_api_source="",
        operator_mobile_summary_api_source="",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "shared-project-factory-summary" in gap_ids
    assert "ui-audit-clean-pass-streak" in gap_ids
    assert payload["summary"]["consecutive_clean_ui_audit_pass_count"] == 1
    assert payload["status"] == "in_progress"


def test_build_payload_clears_contract_gaps_when_routes_and_projection_exist() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={
            "summary": {
                "project_factory_operating_mode": "core_runtime_hold",
                "project_factory_top_priority_project_id": "eoq",
                "project_factory_top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_project_output_candidate_count": 1,
                "pending_hybrid_project_output_count": 1,
                "project_factory_latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        operator_mobile_summary={
            "project_factory": {
                "factory_operating_mode": "core_runtime_hold",
                "top_priority_project_id": "eoq",
                "top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_candidate_count": 1,
                "pending_hybrid_acceptance_count": 1,
                "latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 1, "pending_candidate_count": 1, "stage_status": {"met": False}},
        previous_status=None,
        ui_audit_last_run={"generatedAt": "2026-04-20T21:00:00+00:00", "failures": [], "results": [{"label": "dashboard", "returncode": 0}]},
        live_dashboard_smoke={},
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source='const url = "/api/projects/factory"; const title = "Project Factory"; const copy = "First-class governed lanes";',
        operator_console_source='const section = "Project-output review"; const link = <Link href="/projects" />;',
        root_command_center_source='const label = "Project factory"; const owned = { href: "/projects" }; const next = "Next governed move";',
        project_factory_api_source="import { loadProjectFactorySnapshot } from '@/lib/project-factory';",
        operator_mobile_summary_api_source="import { loadOperatorMobileSummary } from '@/lib/operator-mobile-summary';",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "shared-project-factory-summary" not in gap_ids
    assert "projects-project-factory-console" not in gap_ids
    assert "operator-project-review-surface" not in gap_ids
    assert payload["route_status"]["/projects"]["status"] == "ready"
    assert payload["summary"]["top_priority_project_label"] == "Empire of Broken Queens"


def test_build_payload_increments_clean_ui_audit_streak_for_new_clean_run() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={
            "summary": {
                "project_factory_operating_mode": "core_runtime_hold",
                "project_factory_top_priority_project_id": "eoq",
                "project_factory_top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_project_output_candidate_count": 1,
                "pending_hybrid_project_output_count": 1,
                "project_factory_latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        operator_mobile_summary={
            "project_factory": {
                "factory_operating_mode": "core_runtime_hold",
                "top_priority_project_id": "eoq",
                "top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_candidate_count": 1,
                "pending_hybrid_acceptance_count": 1,
                "latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 1, "pending_candidate_count": 1, "stage_status": {"met": False}},
        previous_status={
            "summary": {
                "consecutive_clean_ui_audit_pass_count": 1,
                "latest_ui_audit_generated_at": "2026-04-20T21:00:00+00:00",
                "latest_ui_audit_clean": True,
            }
        },
        ui_audit_last_run={"generatedAt": "2026-04-20T22:00:00+00:00", "failures": [], "results": [{"label": "dashboard", "returncode": 0}]},
        live_dashboard_smoke={},
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source='const url = "/api/projects/factory"; const title = "Project Factory"; const copy = "First-class governed lanes";',
        operator_console_source='const section = "Project-output review"; const link = <Link href="/projects" />;',
        root_command_center_source='const label = "Project factory"; const owned = { href: "/projects" }; const next = "Next governed move";',
        project_factory_api_source="import { loadProjectFactorySnapshot } from '@/lib/project-factory';",
        operator_mobile_summary_api_source="import { loadOperatorMobileSummary } from '@/lib/operator-mobile-summary';",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "ui-audit-clean-pass-streak" not in gap_ids
    assert payload["summary"]["consecutive_clean_ui_audit_pass_count"] == 2


def test_build_payload_flags_live_runtime_mismatch_for_new_api_routes() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={
            "summary": {
                "project_factory_operating_mode": "core_runtime_hold",
                "project_factory_top_priority_project_id": "eoq",
                "project_factory_top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_project_output_candidate_count": 1,
                "pending_hybrid_project_output_count": 1,
                "project_factory_latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        operator_mobile_summary={
            "project_factory": {
                "factory_operating_mode": "core_runtime_hold",
                "top_priority_project_id": "eoq",
                "top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 0,
                "pending_candidate_count": 1,
                "pending_hybrid_acceptance_count": 1,
                "latest_pending_project_id": "eoq",
                "project_output_stage_met": False,
            }
        },
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 1, "pending_candidate_count": 1, "stage_status": {"met": False}},
        previous_status=None,
        ui_audit_last_run={"generatedAt": "2026-04-20T22:00:00+00:00", "failures": [], "results": []},
        live_dashboard_smoke={
            "generatedAt": "2026-04-20T22:30:00+00:00",
            "failures": [
                "api /api/operator/mobile-summary failed: HTTP Error 404: Not Found",
                "api /api/projects/factory failed: HTTP Error 404: Not Found",
            ],
        },
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source='const url = "/api/projects/factory"; const title = "Project Factory"; const copy = "First-class governed lanes";',
        operator_console_source='const section = "Project-output review"; const link = <Link href="/projects" />;',
        root_command_center_source='const label = "Project factory"; const owned = { href: "/projects" }; const next = "Next governed move";',
        project_factory_api_source="import { loadProjectFactorySnapshot } from '@/lib/project-factory';",
        operator_mobile_summary_api_source="import { loadOperatorMobileSummary } from '@/lib/operator-mobile-summary';",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "operator-mobile-summary-live-runtime-mismatch" in gap_ids
    assert "projects-factory-live-runtime-mismatch" in gap_ids
    assert payload["route_status"]["/api/operator/mobile-summary"]["status"] == "blocked"
    assert payload["route_status"]["/api/projects/factory"]["status"] == "blocked"
    assert payload["summary"]["live_dashboard_api_failure_count"] == 2


def test_build_payload_flags_live_semantic_runtime_mismatch_for_command_center_apis() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={
            "summary": {
                "project_factory_operating_mode": "core_runtime_hold",
                "project_factory_top_priority_project_id": "eoq",
                "project_factory_top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 3,
                "pending_project_output_candidate_count": 0,
                "pending_hybrid_project_output_count": 0,
                "project_factory_latest_pending_project_id": "none",
                "project_output_stage_met": True,
            }
        },
        operator_mobile_summary={
            "project_factory": {
                "factory_operating_mode": "core_runtime_hold",
                "top_priority_project_id": "eoq",
                "top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 3,
                "pending_candidate_count": 0,
                "pending_hybrid_acceptance_count": 0,
                "latest_pending_project_id": "none",
                "project_output_stage_met": True,
            }
        },
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 0, "pending_candidate_count": 0, "stage_status": {"met": True}},
        previous_status=None,
        ui_audit_last_run={"generatedAt": "2026-04-21T03:00:00+00:00", "failures": [], "results": []},
        live_dashboard_smoke={
            "generatedAt": "2026-04-21T03:10:00+00:00",
            "failures": [],
            "apiRuntimeStatus": {
                "/api/operator/mobile-summary": {
                    "semanticStatus": "missing_summary",
                    "detail": "Operator mobile summary returned no canonical summary payload.",
                },
                "/api/projects/factory": {
                    "semanticStatus": "degraded_summary",
                    "detail": "Project factory snapshot is degraded.",
                },
            },
        },
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source='const url = "/api/projects/factory"; const title = "Project Factory"; const copy = "First-class governed lanes";',
        operator_console_source='const section = "Project-output review"; const link = <Link href="/projects" />;',
        root_command_center_source='const label = "Project factory"; const owned = { href: "/projects" }; const next = "Next governed move";',
        project_factory_api_source="import { loadProjectFactorySnapshot } from '@/lib/project-factory';",
        operator_mobile_summary_api_source="import { loadOperatorMobileSummary } from '@/lib/operator-mobile-summary';",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "operator-mobile-summary-live-semantic-mismatch" in gap_ids
    assert "projects-factory-live-semantic-mismatch" in gap_ids
    assert payload["route_status"]["/api/operator/mobile-summary"]["verification_state"] == "missing_summary"
    assert payload["route_status"]["/api/projects/factory"]["verification_state"] == "degraded_summary"


def test_build_payload_flags_live_semantic_runtime_mismatch_for_master_atlas_api() -> None:
    module = _load_module(
        f"write_command_center_final_form_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_command_center_final_form_status.py",
    )

    payload = module.build_payload(
        master_atlas={
            "summary": {
                "project_factory_operating_mode": "core_runtime_hold",
                "project_factory_top_priority_project_id": "eoq",
                "project_factory_top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 3,
                "pending_project_output_candidate_count": 0,
                "pending_hybrid_project_output_count": 0,
                "project_factory_latest_pending_project_id": "none",
                "project_output_stage_met": True,
            }
        },
        operator_mobile_summary={
            "project_factory": {
                "factory_operating_mode": "core_runtime_hold",
                "top_priority_project_id": "eoq",
                "top_priority_project_label": "Empire of Broken Queens",
                "accepted_project_output_count": 3,
                "pending_candidate_count": 0,
                "pending_hybrid_acceptance_count": 0,
                "latest_pending_project_id": "none",
                "project_output_stage_met": True,
            }
        },
        project_output_readiness={"top_priority_project_id": "eoq", "top_priority_project_label": "Empire of Broken Queens"},
        project_output_proof={"pending_hybrid_acceptance_count": 0, "pending_candidate_count": 0, "stage_status": {"met": True}},
        previous_status=None,
        ui_audit_last_run={"generatedAt": "2026-04-21T03:00:00+00:00", "failures": [], "results": []},
        live_dashboard_smoke={
            "generatedAt": "2026-04-21T03:10:00+00:00",
            "failures": [],
            "apiRuntimeStatus": {
                "/api/master-atlas": {
                    "semanticStatus": "stale_payload",
                    "detail": "Command-center API payload is stale by 384 minute(s).",
                },
            },
        },
        ui_audit_findings_ledger={"findings": []},
        ui_audit_uncovered_surfaces={"surfaces": []},
        projects_console_source='const url = "/api/projects/factory"; const title = "Project Factory"; const copy = "First-class governed lanes";',
        operator_console_source='const section = "Project-output review"; const link = <Link href="/projects" />;',
        root_command_center_source='const label = "Project factory"; const owned = { href: "/projects" }; const next = "Next governed move";',
        master_atlas_api_source="import { readGeneratedMasterAtlas, pickMasterAtlasRelationshipMap } from '@/lib/master-atlas';",
        project_factory_api_source="import { loadProjectFactorySnapshot } from '@/lib/project-factory';",
        operator_mobile_summary_api_source="import { loadOperatorMobileSummary } from '@/lib/operator-mobile-summary';",
    )

    gap_ids = {gap["id"] for gap in payload["open_gaps"]}
    assert "master-atlas-live-semantic-mismatch" in gap_ids
    assert payload["route_status"]["/api/master-atlas"]["status"] == "blocked"
    assert payload["route_status"]["/api/master-atlas"]["verification_state"] == "stale_payload"
