from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from athanor_agents import bootstrap_runtime, bootstrap_state
from bootstrap_test_harness import BootstrapStateHarness


REPORT_ONLY_SLICE_ID = "opsurf-01-shell-census"
NEXT_SLICE_ID = "foundry-02-slice-execution"
MUTATION_SLICE_ID = "foundry-02-slice-execution"


class BootstrapRuntimeTests(BootstrapStateHarness):
    @classmethod
    def additional_patches(cls, root: Path) -> list:
        return [patch("athanor_agents.bootstrap_runtime._repo_root", return_value=root / "repo")]

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        (self.root / "repo").mkdir(parents=True, exist_ok=True)

    async def test_prepare_worktree_plans_path_without_execution(self) -> None:
        slice_record = await bootstrap_state.get_bootstrap_slice(MUTATION_SLICE_ID)
        assert slice_record is not None

        result = await bootstrap_runtime.prepare_bootstrap_worktree(slice_record, execute=False)

        self.assertFalse(result["materialized"])
        self.assertFalse(result["reused"])
        self.assertEqual("HEAD", result["base_ref"])
        self.assertTrue(result["worktree_required"])
        self.assertTrue(result["worktree_path"].endswith(MUTATION_SLICE_ID))

    async def test_prepare_worktree_skips_report_only_slice(self) -> None:
        slice_record = await bootstrap_state.get_bootstrap_slice(REPORT_ONLY_SLICE_ID)
        assert slice_record is not None

        result = await bootstrap_runtime.prepare_bootstrap_worktree(slice_record, execute=False)

        self.assertFalse(result["worktree_required"])
        self.assertEqual("", result["worktree_path"])
        self.assertEqual("HEAD", result["base_ref"])

    async def test_execute_cycle_claims_ready_slice_and_writes_handoff_contract(self) -> None:
        def fake_git(args: list[str], *, cwd: Path, check: bool = False):
            if args[:2] == ["rev-parse", "HEAD"]:
                return _FakeGitResult(stdout="abc123\n")
            if args[:3] == ["worktree", "add", "--detach"]:
                Path(args[3]).mkdir(parents=True, exist_ok=True)
                return _FakeGitResult(stdout="prepared\n")
            if args[:2] == ["status", "--porcelain"]:
                return _FakeGitResult(stdout="")
            return _FakeGitResult(stdout="")

        with patch("athanor_agents.bootstrap_runtime._run_git", side_effect=fake_git):
            result = await bootstrap_runtime.advance_bootstrap_supervisor_cycle(
                program_id="launch-readiness-bootstrap",
                execute=True,
                process_integrations=False,
            )

        slice_record = await bootstrap_state.get_bootstrap_slice(NEXT_SLICE_ID)
        assert slice_record is not None
        self.assertEqual("claimed", slice_record["status"])
        self.assertEqual("codex_external", slice_record["host_id"])
        self.assertTrue(slice_record["worktree_path"].endswith(NEXT_SLICE_ID))
        contract_path = self.root / "var" / "bootstrap" / "slices" / NEXT_SLICE_ID / "handoff-contract.json"
        self.assertTrue(contract_path.exists())
        self.assertTrue(any(action.get("kind") == "claim" for action in result["actions"]))

    async def test_claim_next_bootstrap_slice_for_host_respects_execution_mode(self) -> None:
        def fake_git(args: list[str], *, cwd: Path, check: bool = False):
            if args[:2] == ["rev-parse", "HEAD"]:
                return _FakeGitResult(stdout="fedcba\n")
            if args[:3] == ["worktree", "add", "--detach"]:
                Path(args[3]).mkdir(parents=True, exist_ok=True)
                return _FakeGitResult(stdout="prepared\n")
            return _FakeGitResult(stdout="")

        with patch("athanor_agents.bootstrap_runtime._run_git", side_effect=fake_git):
            result = await bootstrap_runtime.claim_next_bootstrap_slice_for_host(
                "codex_external",
                program_id="launch-readiness-bootstrap",
                execute=True,
            )

        self.assertEqual("launch-readiness-bootstrap", result["program_id"])
        self.assertEqual("codex_external", result["slice"]["host_id"])
        self.assertEqual("claimed", result["slice"]["status"])
        self.assertEqual("fedcba", result["slice"]["current_ref"])
        self.assertTrue(result["slice"]["worktree_path"].endswith(NEXT_SLICE_ID))
        self.assertTrue(Path(result["contract_path"]).exists())
        self.assertTrue(result["worktree"]["worktree_required"])
        self.assertEqual(NEXT_SLICE_ID, result["slice"]["id"])

    async def test_execute_cycle_relays_exhausted_host(self) -> None:
        claimed = await bootstrap_state.claim_bootstrap_slice(
            MUTATION_SLICE_ID,
            host_id="codex_external",
            current_ref="abc123",
            worktree_path=str(self.root / "bootstrap-worktrees" / MUTATION_SLICE_ID),
        )
        Path(claimed["worktree_path"]).mkdir(parents=True, exist_ok=True)
        await bootstrap_state._update_host_state(
            "codex_external",
            status="quota_exhausted",
            active_slice_id=MUTATION_SLICE_ID,
            last_reason="quota_exhausted",
            cooldown_minutes=30,
        )

        with patch("athanor_agents.bootstrap_runtime._run_git", return_value=_FakeGitResult(stdout="")):
            result = await bootstrap_runtime.advance_bootstrap_supervisor_cycle(
                program_id="launch-readiness-bootstrap",
                execute=True,
                process_integrations=False,
            )

        slice_record = await bootstrap_state.get_bootstrap_slice(MUTATION_SLICE_ID)
        assert slice_record is not None
        self.assertEqual("claimed", slice_record["status"])
        self.assertEqual("claude_external", slice_record["host_id"])
        handoffs = await bootstrap_state.list_bootstrap_handoffs(limit=10)
        self.assertTrue(any(item["slice_id"] == MUTATION_SLICE_ID for item in handoffs))
        self.assertTrue(any(action.get("kind") == "relay" for action in result["actions"]))
        self.assertTrue(any(action.get("kind") == "claim" and action.get("slice_id") == MUTATION_SLICE_ID for action in result["actions"]))

    async def test_direct_relay_marks_session_exhausted_and_records_contract(self) -> None:
        claimed = await bootstrap_state.claim_bootstrap_slice(
            MUTATION_SLICE_ID,
            host_id="codex_external",
            current_ref="abc123",
            worktree_path=str(self.root / "bootstrap-worktrees" / MUTATION_SLICE_ID),
        )
        Path(claimed["worktree_path"]).mkdir(parents=True, exist_ok=True)

        result = await bootstrap_runtime.relay_bootstrap_slice_for_host(
            "codex_external",
            stop_reason="session_exhausted",
            execute=True,
        )

        self.assertEqual("relayed", result["status"])
        self.assertEqual("codex_external", result["from_host_id"])
        self.assertEqual("claude_external", result["to_host_id"])
        self.assertTrue(Path(result["contract_path"]).exists())

        slice_record = await bootstrap_state.get_bootstrap_slice(MUTATION_SLICE_ID)
        assert slice_record is not None
        self.assertEqual("ready", slice_record["status"])
        self.assertEqual("claude_external", slice_record["host_id"])

        host_states = {item["id"]: item for item in await bootstrap_state.list_bootstrap_host_states()}
        self.assertEqual("session_exhausted", host_states["codex_external"]["status"])
        self.assertEqual("", host_states["codex_external"]["active_slice_id"])

    async def test_dirty_integration_lane_creates_blocker(self) -> None:
        worktree = self.root / "bootstrap-worktrees" / MUTATION_SLICE_ID
        worktree.mkdir(parents=True, exist_ok=True)
        await bootstrap_state.complete_bootstrap_slice(
            MUTATION_SLICE_ID,
            host_id="codex_external",
            current_ref="abc123",
            worktree_path=str(worktree),
            validation_status="passed",
            summary="ready",
        )

        with patch("athanor_agents.bootstrap_runtime._run_git", return_value=_FakeGitResult(stdout=" M dirty-file\n")):
            result = await bootstrap_runtime.progress_bootstrap_integrations(execute=True)

        self.assertEqual("blocked", result["status"])
        blockers = await bootstrap_state.list_bootstrap_blockers(status="open", limit=20)
        self.assertTrue(any(item["blocker_class"] == "integration_failure" for item in blockers))

    async def test_waiting_approval_family_creates_approval_blocker(self) -> None:
        result = await bootstrap_runtime.advance_bootstrap_supervisor_cycle(
            program_id="launch-readiness-bootstrap",
            execute=False,
            process_integrations=False,
        )

        blockers = await bootstrap_state.list_bootstrap_blockers(status="open", limit=50)
        self.assertTrue(any(item["slice_id"] == "persist-04-activation-cutover" and item["approval_required"] for item in blockers))
        self.assertTrue(any(action.get("kind") == "approval_blockers" for action in result["actions"]))


class _FakeGitResult:
    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


if __name__ == "__main__":
    unittest.main()
