from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
DASHBOARD_SRC = REPO_ROOT / "projects" / "dashboard" / "src"
OPERATOR_RUNBOOKS_DOC = REPO_ROOT / "docs" / "operations" / "OPERATOR_RUNBOOKS.md"
BOOTSTRAP_SNAPSHOT = REPO_ROOT / "reports" / "bootstrap" / "latest.json"
BOOTSTRAP_COMPATIBILITY_CENSUS = REPO_ROOT / "reports" / "bootstrap" / "compatibility-retirement-census.json"
BOOTSTRAP_OPERATOR_SURFACE_CENSUS = REPO_ROOT / "reports" / "bootstrap" / "operator-surface-census.json"
BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT = REPO_ROOT / "reports" / "bootstrap" / "operator-summary-alignment.json"
BOOTSTRAP_OPERATOR_FIXTURE_PARITY = REPO_ROOT / "reports" / "bootstrap" / "operator-fixture-parity.json"
BOOTSTRAP_OPERATOR_NAV_LOCK = REPO_ROOT / "reports" / "bootstrap" / "operator-nav-lock.json"
BOOTSTRAP_DURABLE_PACKET = REPO_ROOT / "reports" / "bootstrap" / "durable-persistence-packet.json"
BOOTSTRAP_FOUNDRY_PACKET = REPO_ROOT / "reports" / "bootstrap" / "foundry-proving-packet.json"
BOOTSTRAP_GOVERNANCE_PACKETS = REPO_ROOT / "reports" / "bootstrap" / "governance-drill-packets.json"
BOOTSTRAP_TAKEOVER_PACKET = REPO_ROOT / "reports" / "bootstrap" / "takeover-promotion-packet.json"
FOUNDRY_ROUTE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "routes" / "projects.py"
FOUNDRY_STATE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "foundry_state.py"

LEGACY_ALLOWED_PREFIXES = (
    "projects/dashboard/src/features/workforce/",
)
LEGACY_ALLOWED_FILES = {
    "projects/dashboard/src/lib/api.ts",
}
WORKFORCE_PATTERNS = (
    "getWorkforce(",
    "getScheduledJobs(",
    '"/api/workforce',
    "'/api/workforce",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class BootstrapZeroAmbiguityContractTests(unittest.TestCase):
    def test_zero_ambiguity_registries_exist_with_required_top_level_keys(self) -> None:
        slice_catalog = _read_json(CONFIG_DIR / "bootstrap-slice-catalog.json")
        execution_policy = _read_json(CONFIG_DIR / "bootstrap-execution-policy.json")
        foundry_proving = _read_json(CONFIG_DIR / "foundry-proving-registry.json")
        governance_drills = _read_json(CONFIG_DIR / "governance-drill-registry.json")
        approval_packets = _read_json(CONFIG_DIR / "approval-packet-registry.json")

        self.assertIn("families", slice_catalog)
        self.assertIn("slices", slice_catalog)
        self.assertIn("worktree", execution_policy)
        self.assertIn("integration", execution_policy)
        self.assertEqual("athanor", foundry_proving.get("project_id"))
        self.assertIn("drills", governance_drills)
        self.assertIn("packet_types", approval_packets)

    def test_governance_drill_registry_maps_to_real_runbooks(self) -> None:
        governance_drills = _read_json(CONFIG_DIR / "governance-drill-registry.json")
        operator_runbooks = _read_json(CONFIG_DIR / "operator-runbooks.json")
        runbook_ids = {
            str(item.get("id") or "")
            for item in operator_runbooks.get("runbooks", [])
            if isinstance(item, dict)
        }
        drill_runbook_ids = {
            str(item.get("runbook_id") or "")
            for item in governance_drills.get("drills", [])
            if isinstance(item, dict)
        }

        self.assertIn("blocked-approval", runbook_ids)
        self.assertTrue(drill_runbook_ids.issubset(runbook_ids))
        self.assertIn("## Blocked approval", OPERATOR_RUNBOOKS_DOC.read_text(encoding="utf-8"))

    def test_active_bootstrap_program_has_snapshot_artifact(self) -> None:
        snapshot = _read_json(BOOTSTRAP_SNAPSHOT)
        self.assertIn("generated_at", snapshot)
        self.assertIn("status", snapshot)
        self.assertIn("registry_snapshot", snapshot)

    def test_required_bootstrap_packet_artifacts_exist(self) -> None:
        for path in (
            BOOTSTRAP_COMPATIBILITY_CENSUS,
            BOOTSTRAP_OPERATOR_SURFACE_CENSUS,
            BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT,
            BOOTSTRAP_OPERATOR_FIXTURE_PARITY,
            BOOTSTRAP_OPERATOR_NAV_LOCK,
            BOOTSTRAP_DURABLE_PACKET,
            BOOTSTRAP_FOUNDRY_PACKET,
            BOOTSTRAP_GOVERNANCE_PACKETS,
            BOOTSTRAP_TAKEOVER_PACKET,
        ):
            self.assertTrue(path.exists(), msg=f"missing bootstrap artifact: {path}")

    def test_operator_surface_census_is_green_for_first_class_shell(self) -> None:
        census = _read_json(BOOTSTRAP_OPERATOR_SURFACE_CENSUS)

        self.assertEqual(0, census.get("first_class_drift_count"))
        self.assertGreater(census.get("canonical_hit_count", 0), 0)
        self.assertTrue(census.get("complete"))

    def test_operator_summary_alignment_is_green_for_first_class_digest_surfaces(self) -> None:
        report = _read_json(BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT)

        self.assertEqual(0, report.get("drift_count"))
        self.assertEqual(0, report.get("missing_canonical_hit_count"))
        self.assertGreater(report.get("canonical_hit_count", 0), 0)
        self.assertTrue(report.get("complete"))

    def test_operator_fixture_parity_is_green_for_canonical_operator_and_bootstrap_routes(self) -> None:
        report = _read_json(BOOTSTRAP_OPERATOR_FIXTURE_PARITY)

        self.assertEqual(0, report.get("missing_file_count"))
        self.assertEqual(0, report.get("missing_pattern_count"))
        self.assertGreater(report.get("satisfied_target_count", 0), 0)
        self.assertTrue(report.get("complete"))

    def test_operator_nav_lock_is_green_for_first_class_routes(self) -> None:
        report = _read_json(BOOTSTRAP_OPERATOR_NAV_LOCK)

        self.assertEqual(0, report.get("missing_file_count"))
        self.assertEqual(0, report.get("missing_pattern_count"))
        self.assertEqual(0, report.get("forbidden_pattern_count"))
        self.assertGreater(report.get("satisfied_target_count", 0), 0)
        self.assertTrue(report.get("complete"))

    def test_durable_persistence_packet_locks_runtime_contract(self) -> None:
        packet = _read_json(BOOTSTRAP_DURABLE_PACKET)

        self.assertEqual("durable_persistence_live", packet.get("criterion_id"))
        self.assertEqual("ATHANOR_POSTGRES_URL", packet.get("contract", {}).get("env_contract", {}).get("name"))
        self.assertEqual("db_schema_change", packet.get("approval_packet", {}).get("id"))
        self.assertEqual(
            "langgraph.checkpoint.postgres.PostgresSaver.setup()",
            packet.get("schema_authority", {}).get("checkpoint_setup_authority"),
        )
        self.assertTrue(packet.get("runtime_dependency_packet", {}).get("required_packages"))
        self.assertTrue(packet.get("restart_proof", {}).get("steps"))

    def test_foundry_proving_packet_locks_proving_contract(self) -> None:
        packet = _read_json(BOOTSTRAP_FOUNDRY_PACKET)

        self.assertEqual("athanor", packet.get("project_id"))
        self.assertTrue(packet.get("project_packet_ref"))
        self.assertTrue(packet.get("architecture_packet_ref"))
        self.assertEqual("athanor-bootstrap-zero-ambiguity", packet.get("first_proving_slice_id"))
        self.assertEqual("coding-agent", packet.get("first_proving_slice_packet", {}).get("owner_agent"))
        self.assertEqual("software_core_phase_1", packet.get("first_proving_slice_packet", {}).get("lane"))
        self.assertTrue(packet.get("acceptance_evidence_requirements"))
        self.assertTrue(packet.get("candidate_evidence_requirements"))
        self.assertTrue(packet.get("rollback_target_requirements"))
        self.assertTrue(packet.get("validator_bundle"))
        self.assertTrue(packet.get("promotion_gate", {}).get("require_foundry_run"))
        self.assertTrue(packet.get("promotion_gate", {}).get("require_candidate"))
        self.assertTrue(packet.get("promotion_gate", {}).get("require_rollback_target"))
        self.assertTrue(packet.get("promotion_gate", {}).get("require_acceptance_evidence"))
        self.assertFalse(packet.get("promotion_gate", {}).get("allow_direct_ad_hoc_bypass"))

    def test_athanor_proving_flow_is_packet_backed_and_not_ad_hoc(self) -> None:
        route_source = FOUNDRY_ROUTE.read_text(encoding="utf-8")
        state_source = FOUNDRY_STATE.read_text(encoding="utf-8")

        self.assertIn('/projects/{project_id}/proving', route_source)
        self.assertIn("materialize_foundry_proving_stage", route_source)
        self.assertIn("async def materialize_foundry_proving_stage", state_source)
        self.assertIn("upsert_architecture_packet_record", state_source)
        self.assertIn("upsert_execution_slice_record", state_source)
        self.assertIn("upsert_foundry_run_record", state_source)
        self.assertIn("upsert_deploy_candidate_record", state_source)
        self.assertIn("record_rollback_event", state_source)

    def test_first_class_dashboard_surfaces_do_not_depend_on_workforce_compatibility_helpers(self) -> None:
        offending_paths: list[str] = []
        for path in DASHBOARD_SRC.rglob("*.ts*"):
            if not path.is_file():
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            if any(relative.startswith(prefix) for prefix in LEGACY_ALLOWED_PREFIXES):
                continue
            if relative in LEGACY_ALLOWED_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if any(pattern in text for pattern in WORKFORCE_PATTERNS):
                offending_paths.append(relative)

        self.assertEqual([], offending_paths)


if __name__ == "__main__":
    unittest.main()
