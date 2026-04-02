from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.control_plane_registry import (  # noqa: E402
    build_control_plane_registry_snapshot,
    get_attention_budgets_registry_entries,
    get_coding_lanes,
    get_core_change_windows,
    get_memory_namespaces,
    get_project_packet,
    get_project_packets,
    get_source_policies,
    get_system_modes,
)


class ControlPlaneRegistryContractTests(unittest.TestCase):
    def test_coding_lane_registry_contains_expected_live_lanes(self) -> None:
        lanes = {entry["id"]: entry for entry in get_coding_lanes()}
        self.assertTrue(
            {
                "sovereign_supervisor",
                "sovereign_coder",
                "sovereign_bulk",
                "codex_cloudsafe",
                "responses_background_cloudsafe",
                "public_edge_async",
            }
            <= set(lanes)
        )
        self.assertEqual("local_only", lanes["sovereign_supervisor"]["privacy"])
        self.assertEqual("public_product_only", lanes["public_edge_async"]["privacy"])

    def test_memory_namespace_registry_marks_sensitive_namespaces_local_only(self) -> None:
        namespaces = {entry["id"]: entry for entry in get_memory_namespaces()}
        self.assertIn("operator.inbox", namespaces)
        self.assertIn("creative.assets", namespaces)
        self.assertFalse(namespaces["operator.inbox"]["cloud_allowed"])
        self.assertFalse(namespaces["creative.assets"]["cloud_allowed"])

    def test_source_policy_registry_filters_enabled_sources(self) -> None:
        enabled = {entry["id"] for entry in get_source_policies(enabled_only=True)}
        all_sources = {entry["id"] for entry in get_source_policies()}
        self.assertEqual({"crawl_miniflux_internal"}, enabled)
        self.assertIn("adult_finder_source_template", all_sources)

    def test_project_packet_registry_exposes_foundry_seed_packets(self) -> None:
        packets = {entry["id"]: entry for entry in get_project_packets()}
        self.assertTrue({"athanor", "eoq", "kindred", "ulrich-energy", "media"} <= set(packets))
        athanor = get_project_packet("athanor")
        self.assertIsNotNone(athanor)
        assert athanor is not None
        self.assertEqual("internal_operator_app", athanor["template"])
        self.assertEqual("active_build", athanor["stage"])

    def test_governance_registries_expose_modes_budgets_and_windows(self) -> None:
        modes = {entry["id"]: entry for entry in get_system_modes()}
        budgets = {entry["id"]: entry for entry in get_attention_budgets_registry_entries()}
        windows = {entry["id"]: entry for entry in get_core_change_windows()}

        self.assertTrue({"normal", "constrained", "degraded", "recovery_only"} <= set(modes))
        self.assertEqual(12, budgets["general-assistant"]["daily_limit"])
        self.assertIn("security_alert", budgets["home-agent"]["urgent_bypass"])
        self.assertIn("core-window-first-weekend", windows)
        self.assertEqual("first_weekend", windows["core-window-first-weekend"]["schedule"])

    def test_control_plane_registry_snapshot_rolls_up_counts(self) -> None:
        snapshot = build_control_plane_registry_snapshot()
        self.assertGreaterEqual(snapshot["coding_lanes"]["count"], 6)
        self.assertGreaterEqual(snapshot["memory_namespaces"]["count"], 5)
        self.assertGreaterEqual(snapshot["source_policies"]["count"], 3)
        self.assertGreaterEqual(snapshot["project_packets"]["count"], 5)
        self.assertEqual("normal", snapshot["system_modes"]["default_mode"])
        self.assertGreaterEqual(snapshot["attention_budgets"]["count"], 5)
        self.assertGreaterEqual(snapshot["core_change_windows"]["count"], 2)


if __name__ == "__main__":
    unittest.main()
