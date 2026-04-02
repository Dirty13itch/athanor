from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from athanor_agents.governance_state import (
    _repo_root,
    _runtime_artifact_root,
    build_governance_drill_snapshot,
    build_governance_snapshot,
    compute_attention_posture,
    rehearse_governance_drill,
)


class GovernanceStateContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _runtime_artifact_root.cache_clear()

    def tearDown(self) -> None:
        _runtime_artifact_root.cache_clear()

    def test_repo_root_falls_back_to_workspace_when_running_from_site_packages(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fake_module = Path(temp_dir) / "usr" / "local" / "lib" / "python3.12" / "site-packages" / "athanor_agents" / "governance_state.py"
            fake_module.parent.mkdir(parents=True, exist_ok=True)
            fake_module.write_text("# test", encoding="utf-8")
            with patch("athanor_agents.governance_state.__file__", str(fake_module)):
                self.assertEqual(Path("/workspace"), _repo_root())

    async def test_compute_attention_posture_flags_breaches(self) -> None:
        inbox_rows = [
            {"inbox_id": f"inbox-{index}", "severity": 3 if index < 4 else 1, "status": "new"}
            for index in range(11)
        ]
        blocked_runs = [
            {"id": f"run-{index}", "updated_at": 1.0}
            for index in range(3)
        ]
        with (
            patch("athanor_agents.governance_state.inbox_stats", AsyncMock(return_value={"by_status": {"new": 11}})),
            patch("athanor_agents.governance_state._fetch_all", AsyncMock(return_value=inbox_rows)),
            patch("athanor_agents.governance_state.list_approval_request_records", AsyncMock(return_value=[{"id": str(index)} for index in range(6)])),
            patch("athanor_agents.governance_state.list_execution_run_records", AsyncMock(return_value=blocked_runs)),
            patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
            patch("athanor_agents.governance_state.datetime") as datetime_mock,
        ):
            datetime_mock.now.return_value.timestamp.return_value = 4000.0
            posture = await compute_attention_posture()

        self.assertEqual("constrained", posture["recommended_mode"])
        self.assertIn("attention:open_inbox", posture["breaches"])
        self.assertIn("attention:urgent_inbox", posture["breaches"])
        self.assertIn("attention:pending_approvals", posture["breaches"])
        self.assertIn("attention:stale_blocked_runs", posture["breaches"])

    async def test_build_governance_snapshot_rolls_up_launch_posture(self) -> None:
        with (
            patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": ["providers:evidence_missing"], "issues": []}),
            patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
            patch("athanor_agents.governance_state.list_system_mode_records", AsyncMock(return_value=[{"mode": "normal"}])),
            patch("athanor_agents.governance_state.list_attention_budget_records", AsyncMock(return_value=[{"id": "general-assistant"}])),
            patch("athanor_agents.governance_state.list_core_change_window_records", AsyncMock(return_value=[{"id": "core-window-first-weekend"}])),
            patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"breaches": [], "recommended_mode": "normal"})),
        ):
            snapshot = await build_governance_snapshot()

        self.assertFalse(snapshot["launch_ready"])
        self.assertEqual(["providers:evidence_missing"], snapshot["launch_blockers"])
        self.assertEqual("normal", snapshot["current_mode"]["mode"])

    async def test_rehearse_governance_drill_writes_artifact_and_reports_failure_honestly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with (
                patch("athanor_agents.governance_state._repo_root", return_value=repo_root),
                patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
                patch("athanor_agents.governance_state.enter_system_mode_record", AsyncMock(side_effect=RuntimeError("mode write failed"))),
                patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"recommended_mode": "normal", "breaches": []})),
                patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": [], "issues": [], "current_phase_id": "software_core_phase_1", "current_phase_status": "active"}),
                patch("athanor_agents.bootstrap_state.list_bootstrap_blockers", AsyncMock(return_value=[])),
                patch("athanor_agents.bootstrap_state.record_bootstrap_blocker", AsyncMock(return_value={"id": "blocker-1"})),
            ):
                artifact = await rehearse_governance_drill("constrained-mode", actor="test-suite")
                snapshot = build_governance_drill_snapshot()
                self.assertTrue((repo_root / "reports" / "governance" / "drills" / "constrained-mode.json").exists())

        self.assertFalse(artifact["passed"])
        self.assertEqual("blocker-1", artifact["blocker_id"])
        self.assertFalse(snapshot["all_green"])
        self.assertFalse(snapshot["evidence_complete"])

    async def test_rehearse_constrained_mode_performs_durable_mode_change_and_restore(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            get_current_mode = AsyncMock(
                side_effect=[
                    {"mode": "normal"},
                    {"mode": "constrained"},
                    {"mode": "normal"},
                ]
            )
            enter_mode = AsyncMock(
                side_effect=[
                    {"id": "mode-constrained-rehearsal", "mode": "constrained"},
                    {"id": "mode-normal-restore", "mode": "normal"},
                ]
            )
            with (
                patch("athanor_agents.governance_state._repo_root", return_value=repo_root),
                patch("athanor_agents.governance_state.get_current_system_mode_record", get_current_mode),
                patch("athanor_agents.governance_state.enter_system_mode_record", enter_mode),
                patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"recommended_mode": "normal", "breaches": []})),
                patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": [], "issues": [], "current_phase_id": "software_core_phase_1", "current_phase_status": "active"}),
                patch("athanor_agents.bootstrap_state.list_bootstrap_blockers", AsyncMock(return_value=[])),
                patch("athanor_agents.bootstrap_state.resolve_bootstrap_blocker", AsyncMock()),
            ):
                artifact = await rehearse_governance_drill("constrained-mode", actor="test-suite")

        self.assertTrue(artifact["passed"])
        self.assertEqual("durable_rehearsal", artifact["observed_mode_change"]["reason"])
        self.assertEqual("constrained", artifact["observed_mode_change"]["to"])
        self.assertTrue(artifact["observed_mode_change"]["restored"])

    async def test_rehearse_blocked_approval_can_pass_from_live_bootstrap_posture(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with (
                patch("athanor_agents.governance_state._repo_root", return_value=repo_root),
                patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
                patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"recommended_mode": "normal", "breaches": []})),
                patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": [], "issues": [], "current_phase_id": "software_core_phase_1", "current_phase_status": "active"}),
                patch("athanor_agents.bootstrap_state.list_bootstrap_blockers", AsyncMock(return_value=[{"id": "blocker-approval", "approval_required": True}])),
                patch(
                    "athanor_agents.bootstrap_state.list_bootstrap_programs",
                    AsyncMock(
                        return_value=[
                            {
                                "families": [
                                    {"id": "durable_persistence_activation", "status": "waiting_approval"},
                                    {"id": "governance_rehearsal", "status": "active"},
                                ]
                            }
                        ]
                    ),
                ),
            ):
                artifact = await rehearse_governance_drill("blocked-approval", actor="test-suite")

        self.assertTrue(artifact["passed"])
        self.assertEqual("", artifact["blocker_id"])

    async def test_rehearse_restore_requires_green_recovery_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            recovery_dir = repo_root / "reports" / "recovery"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / "latest.json").write_text(
                """
                {
                  "success": true,
                  "snapshot": {
                    "flows": [
                      {
                        "id": "restore_drill",
                        "status": "degraded",
                        "last_outcome": "failed",
                        "details": {
                          "verified_store_count": 3,
                          "store_count": 4
                        }
                      }
                    ]
                  }
                }
                """.strip(),
                encoding="utf-8",
            )
            with (
                patch("athanor_agents.governance_state._repo_root", return_value=repo_root),
                patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
                patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"recommended_mode": "normal", "breaches": []})),
                patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": [], "issues": [], "current_phase_id": "software_core_phase_1", "current_phase_status": "active"}),
                patch("athanor_agents.bootstrap_state.list_bootstrap_blockers", AsyncMock(return_value=[])),
                patch("athanor_agents.bootstrap_state.record_bootstrap_blocker", AsyncMock(return_value={"id": "blocker-restore"})),
            ):
                artifact = await rehearse_governance_drill("restore", actor="test-suite")

        self.assertFalse(artifact["passed"])
        self.assertEqual("blocker-restore", artifact["blocker_id"])
        self.assertIn("verified_stores=3/4", artifact["detail"])

    async def test_rehearse_restore_resolves_existing_blocker_when_artifact_turns_green(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            recovery_dir = repo_root / "reports" / "recovery"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / "latest.json").write_text(
                """
                {
                  "success": true,
                  "snapshot": {
                    "flows": [
                      {
                        "id": "restore_drill",
                        "status": "passed",
                        "last_outcome": "passed",
                        "details": {
                          "verified_store_count": 4,
                          "store_count": 4
                        }
                      }
                    ]
                  }
                }
                """.strip(),
                encoding="utf-8",
            )
            resolve_blocker = AsyncMock(return_value={"id": "blocker-restore", "status": "resolved"})
            with (
                patch("athanor_agents.governance_state._repo_root", return_value=repo_root),
                patch("athanor_agents.governance_state.get_current_system_mode_record", AsyncMock(return_value={"mode": "normal"})),
                patch("athanor_agents.governance_state.compute_attention_posture", AsyncMock(return_value={"recommended_mode": "normal", "breaches": []})),
                patch("athanor_agents.governance_state.build_launch_governance_posture", return_value={"launch_blockers": [], "issues": [], "current_phase_id": "software_core_phase_1", "current_phase_status": "active"}),
                patch(
                    "athanor_agents.bootstrap_state.list_bootstrap_blockers",
                    AsyncMock(
                        return_value=[
                            {
                                "id": "blocker-restore",
                                "family": "governance_rehearsal",
                                "status": "open",
                                "blocker_class": "restore_drill_failed",
                                "metadata": {"drill_id": "restore"},
                            }
                        ]
                    ),
                ),
                patch("athanor_agents.bootstrap_state.resolve_bootstrap_blocker", resolve_blocker),
            ):
                artifact = await rehearse_governance_drill("restore", actor="test-suite")

        self.assertTrue(artifact["passed"])
        resolve_blocker.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
