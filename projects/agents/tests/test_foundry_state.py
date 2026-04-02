from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents import foundry_state  # noqa: E402


class FoundryStateFallbackTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        foundry_state._runtime_artifact_root.cache_clear()

    async def test_upsert_execution_slice_uses_local_fallback_when_durable_state_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with (
                patch("athanor_agents.foundry_state._repo_root", return_value=repo_root),
                patch("athanor_agents.foundry_state._execute", AsyncMock(return_value=False)),
                patch("athanor_agents.foundry_state._fetch_all", AsyncMock(return_value=[])),
            ):
                saved = await foundry_state.upsert_execution_slice_record(
                    {
                        "id": "athanor-bootstrap-zero-ambiguity",
                        "project_id": "athanor",
                        "owner_agent": "coding-agent",
                        "lane": "software_core_phase_1",
                        "base_sha": "HEAD",
                        "worktree_path": "C:\\Athanor",
                        "acceptance_target": "Foundry packet and deploy candidate path",
                        "status": "completed",
                    }
                )
                records = await foundry_state.list_execution_slice_records("athanor", limit=10)

            self.assertTrue(saved)
            self.assertEqual(1, len(records))
            self.assertEqual("athanor-bootstrap-zero-ambiguity", records[0]["id"])
            self.assertTrue((repo_root / "var" / "foundry" / "projects" / "athanor.json").exists())

    async def test_materialize_proving_stage_writes_local_foundry_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            with (
                patch("athanor_agents.foundry_state._repo_root", return_value=repo_root),
                patch("athanor_agents.foundry_state._execute", AsyncMock(return_value=False)),
                patch("athanor_agents.foundry_state._fetch_all", AsyncMock(return_value=[])),
                patch("athanor_agents.foundry_state._current_git_ref", return_value="HEAD"),
            ):
                proving = await foundry_state.materialize_foundry_proving_stage(
                    "athanor",
                    stage="rollback_record",
                )
                architecture = await foundry_state.fetch_architecture_packet_record("athanor")
                slices = await foundry_state.list_execution_slice_records("athanor", limit=10)
                runs = await foundry_state.list_foundry_run_records("athanor", limit=10)
                candidates = await foundry_state.list_deploy_candidate_records("athanor", limit=10)
                rollbacks = await foundry_state.list_rollback_event_records("athanor", limit=10)

            self.assertEqual("local_fallback", proving["storage"]["storage_mode"])
            self.assertIsNotNone(architecture)
            self.assertEqual(1, len(slices))
            self.assertEqual(1, len(runs))
            self.assertEqual(1, len(candidates))
            self.assertEqual(1, len(rollbacks))
            self.assertTrue(candidates[0]["rollback_target"])

    async def test_foundry_fallback_uses_output_when_repo_root_is_not_writable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "output"
            output_root.mkdir(parents=True, exist_ok=True)
            with (
                patch("athanor_agents.foundry_state._runtime_artifact_root", return_value=output_root),
                patch("athanor_agents.foundry_state._execute", AsyncMock(return_value=False)),
                patch("athanor_agents.foundry_state._fetch_all", AsyncMock(return_value=[])),
                patch("athanor_agents.foundry_state._current_git_ref", return_value="HEAD"),
            ):
                proving = await foundry_state.materialize_foundry_proving_stage("athanor", stage="rollback_record")

            self.assertEqual("local_fallback", proving["storage"]["storage_mode"])
            self.assertTrue((output_root / "var" / "foundry" / "projects" / "athanor.json").exists())


if __name__ == "__main__":
    unittest.main()
