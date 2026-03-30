import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.judge import build_judge_plane_snapshot


class JudgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_judge_plane_snapshot_summarizes_recent_verdicts(self) -> None:
        runs = [
            {
                "id": "run-1",
                "status": "completed",
                "agent": "coding-agent",
                "provider": "athanor_local",
                "policy_class": "sovereign_only",
                "artifact_refs": [{"label": "patch", "href": "/tasks/run-1"}],
                "task_id": "task-1",
            },
            {
                "id": "run-2",
                "status": "failed",
                "agent": "research-agent",
                "provider": "google_gemini",
                "policy_class": "cloud_safe",
                "artifact_refs": [],
                "failure_reason": "provider timeout",
            },
            {
                "id": "run-3",
                "status": "running",
                "agent": "coding-agent",
                "provider": "athanor_local",
                "policy_class": "private_but_cloud_allowed",
                "artifact_refs": [],
            },
        ]
        with (
            patch(
                "athanor_agents.backbone.build_execution_run_records",
                AsyncMock(return_value=runs),
            ),
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"pending_approval": 7}),
            ),
            patch(
                "athanor_agents.model_governance.get_model_role_registry",
                return_value={
                    "roles": [
                        {
                            "id": "judge_verifier",
                            "label": "Judge / verifier",
                            "champion": "judge-local-v1",
                            "challengers": ["critic-local-v1"],
                            "workload_classes": [
                                "judge_verification",
                                "promotion_gating",
                                "regression_scoring",
                            ],
                        }
                    ]
                },
            ),
        ):
            snapshot = await build_judge_plane_snapshot(limit=3)

        self.assertEqual("live", snapshot["status"])
        self.assertEqual(3, snapshot["summary"]["recent_verdicts"])
        self.assertEqual(1, snapshot["summary"]["accept_count"])
        self.assertEqual(1, snapshot["summary"]["reject_count"])
        self.assertEqual(1, snapshot["summary"]["review_required"])
        self.assertEqual(7, snapshot["summary"]["pending_review_queue"])
        self.assertEqual("accept", snapshot["recent_verdicts"][0]["verdict"])
        self.assertEqual("reject", snapshot["recent_verdicts"][1]["verdict"])


if __name__ == "__main__":
    unittest.main()
