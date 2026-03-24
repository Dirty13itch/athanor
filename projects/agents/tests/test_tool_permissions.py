import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.tool_permissions import (
    build_tool_permission_snapshot,
    evaluate_tool_permission,
)


class ToolPermissionTests(unittest.TestCase):
    def test_meta_lane_cannot_mutate_shell(self) -> None:
        decision = evaluate_tool_permission("frontier_cloud", "shell mutation")
        self.assertFalse(decision["allowed"])
        self.assertEqual("meta_lanes", decision["subject_class"])
        self.assertTrue(decision["matched_deny"])

    def test_specialist_agent_can_request_bounded_execution(self) -> None:
        decision = evaluate_tool_permission("coding-agent", "bounded execution")
        self.assertTrue(decision["allowed"])
        self.assertEqual("specialist_agents", decision["subject_class"])
        self.assertEqual("scoped_execution", decision["mode"])

    def test_worker_lane_cannot_issue_leases(self) -> None:
        decision = evaluate_tool_permission("coding_worker", "lease issuance")
        self.assertFalse(decision["allowed"])
        self.assertEqual("workers", decision["subject_class"])
        self.assertTrue(decision["matched_deny"])

    def test_snapshot_reports_normalized_subjects_and_modes(self) -> None:
        snapshot = build_tool_permission_snapshot()
        self.assertGreaterEqual(snapshot["subject_count"], 4)
        self.assertIn("subjects", snapshot)
        self.assertIn("mode_counts", snapshot)
        self.assertIn("governor_mediated", snapshot["mode_counts"])


if __name__ == "__main__":
    unittest.main()
