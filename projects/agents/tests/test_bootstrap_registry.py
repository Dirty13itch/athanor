from __future__ import annotations

import unittest

from athanor_agents.bootstrap_registry import (
    build_bootstrap_registry_snapshot,
    get_approval_packet_types,
    get_bootstrap_hosts,
    get_bootstrap_programs,
    get_bootstrap_slice_definitions,
    get_foundry_proving_registry,
    get_governance_drills,
    get_bootstrap_takeover_criteria,
)


class BootstrapRegistryTests(unittest.TestCase):
    def test_bootstrap_registries_load_expected_seeded_entries(self) -> None:
        hosts = get_bootstrap_hosts()
        programs = get_bootstrap_programs()
        criteria = get_bootstrap_takeover_criteria()
        slice_definitions = get_bootstrap_slice_definitions()
        drills = get_governance_drills()
        approval_packets = get_approval_packet_types()
        foundry = get_foundry_proving_registry()

        host_ids = {item["id"] for item in hosts}
        self.assertIn("codex_external", host_ids)
        self.assertIn("claude_external", host_ids)

        program_ids = {item["id"] for item in programs}
        self.assertIn("launch-readiness-bootstrap", program_ids)

        criterion_ids = {item["id"] for item in criteria}
        self.assertIn("software_core_active", criterion_ids)
        self.assertIn("external_dependency_removed", criterion_ids)

        slice_ids = {item["id"] for item in slice_definitions}
        self.assertIn("compat-01-active-usage-census", slice_ids)
        self.assertIn("takeover-03-demotion-contract", slice_ids)

        drill_ids = {item["drill_id"] for item in drills}
        self.assertIn("blocked-approval", drill_ids)

        packet_ids = {item["id"] for item in approval_packets}
        self.assertIn("db_schema_change", packet_ids)
        self.assertIn("vault_provider_auth_repair", packet_ids)

        self.assertEqual("athanor", foundry["project_id"])

    def test_registry_snapshot_includes_zero_ambiguity_control_artifacts(self) -> None:
        snapshot = build_bootstrap_registry_snapshot()

        self.assertIn("builder_hosts", snapshot)
        self.assertIn("programs", snapshot)
        self.assertIn("takeover", snapshot)
        self.assertIn("slice_catalog", snapshot)
        self.assertIn("execution_policy", snapshot)
        self.assertIn("foundry_proving", snapshot)
        self.assertIn("governance_drills", snapshot)
        self.assertIn("approval_packets", snapshot)
        self.assertGreater(snapshot["builder_hosts"]["count"], 0)
        self.assertGreater(snapshot["programs"]["family_count"], 0)
        self.assertGreater(snapshot["takeover"]["criteria_count"], 0)
        self.assertGreater(snapshot["slice_catalog"]["slice_count"], 0)
        self.assertGreater(snapshot["governance_drills"]["drill_count"], 0)
        self.assertGreater(snapshot["approval_packets"]["packet_type_count"], 0)


if __name__ == "__main__":
    unittest.main()
