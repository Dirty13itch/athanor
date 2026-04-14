from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from time import monotonic
from unittest.mock import AsyncMock, patch

from athanor_agents import bootstrap_state
from bootstrap_test_harness import BootstrapStateHarness


REPORT_ONLY_SLICE_ID = "opsurf-01-shell-census"
NEXT_SLICE_ID = "foundry-02-slice-execution"
MUTATION_SLICE_ID = "foundry-02-slice-execution"
WAITING_APPROVAL_SLICE_ID = "persist-04-activation-cutover"


class BootstrapStateTests(BootstrapStateHarness):
    @classmethod
    def additional_patches(cls, root: Path) -> list:
        return [
            patch(
                "athanor_agents.bootstrap_state.bootstrap_durable_restart_proof_path",
                return_value=root / "reports" / "bootstrap" / "durable-restart-proof.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_approval_packet_registry_path",
                return_value=root / "config" / "automation-backbone" / "approval-packet-registry.json",
            ),
            patch(
                "athanor_agents.bootstrap_state.bootstrap_durable_state_sql_path",
                return_value=root / "projects" / "agents" / "src" / "athanor_agents" / "sql" / "bootstrap_durable_state.sql",
            ),
            patch(
                "athanor_agents.bootstrap_state.read_durable_restart_proof",
                return_value={},
            ),
        ]

    async def test_state_initializes_sqlite_ledger_and_seeds_programs(self) -> None:
        status = bootstrap_state.get_bootstrap_status()
        self.assertEqual("ready", status["mode"])
        self.assertTrue(status["sqlite_ready"])
        self.assertTrue((self.root / "var" / "bootstrap" / "ledger.sqlite").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "latest.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "compatibility-retirement-census.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "operator-surface-census.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "operator-summary-alignment.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "operator-fixture-parity.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "operator-nav-lock.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "durable-persistence-packet.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "foundry-proving-packet.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "governance-drill-packets.json").exists())
        self.assertTrue((self.root / "reports" / "bootstrap" / "takeover-promotion-packet.json").exists())

        programs = await bootstrap_state.list_bootstrap_programs()
        self.assertGreaterEqual(len(programs), 1)
        self.assertEqual("launch-readiness-bootstrap", programs[0]["id"])
        slices = await bootstrap_state.list_bootstrap_slices(limit=100)
        self.assertTrue(any(item["id"] == "persist-01-checkpointer-contract" for item in slices))
        self.assertTrue(any(item["catalog_slice_id"] == "persist-01-checkpointer-contract" for item in slices))

    async def test_claim_handoff_and_complete_update_bootstrap_ledger(self) -> None:
        claimed = await bootstrap_state.claim_bootstrap_slice(
            MUTATION_SLICE_ID,
            host_id="codex_external",
            current_ref="abc123",
            worktree_path=f"C:/Athanor/.claude/worktrees/{MUTATION_SLICE_ID}",
            files_touched=["projects/dashboard/src/features/operator/operator-console.tsx"],
            next_step="Align the operator summary surfaces.",
        )
        self.assertEqual("claimed", claimed["status"])
        self.assertEqual("codex_external", claimed["host_id"])

        handed_off = await bootstrap_state.handoff_bootstrap_slice(
            MUTATION_SLICE_ID,
            from_host="codex_external",
            to_host="claude_external",
            stop_reason="context_exhausted",
            next_step="Resume with the same worktree state.",
        )
        self.assertEqual("claude_external", handed_off["slice"]["host_id"])
        self.assertEqual("codex_external", handed_off["handoff"]["from_host"])

        completed = await bootstrap_state.complete_bootstrap_slice(
            MUTATION_SLICE_ID,
            host_id="claude_external",
            current_ref="def456",
            validation_status="passed",
            summary="Operator summary alignment is ready for integration replay.",
        )
        self.assertEqual("completed", completed["slice"]["status"])
        self.assertIsNotNone(completed["integration"])
        self.assertTrue((self.root / "var" / "bootstrap" / "integration" / "queue" / f"{MUTATION_SLICE_ID}.json").exists())

    async def test_takeover_status_reports_unmet_criteria_in_bootstrap_mode(self) -> None:
        takeover = await bootstrap_state.build_takeover_status()

        self.assertFalse(takeover["ready"])
        blocker_ids = set(takeover["blocker_ids"])
        software_core = next(item for item in takeover["criteria"] if item["id"] == "software_core_active")
        self.assertTrue(software_core["passed"])
        self.assertIn("durable_persistence_live", blocker_ids)
        self.assertIn("external_dependency_removed", blocker_ids)
        self.assertNotIn("software_core_active", blocker_ids)

    async def test_effective_checkpointer_status_materializes_configured_uninitialized_state(self) -> None:
        with (
            patch(
                "athanor_agents.bootstrap_state.get_checkpointer_status",
                side_effect=[
                    {
                        "configured": True,
                        "durable": False,
                        "mode": "uninitialized",
                        "reason": "Checkpointer has not been built yet",
                    },
                    {
                        "configured": True,
                        "durable": True,
                        "mode": "postgres",
                        "reason": None,
                    },
                ],
            ) as status_mock,
            patch("athanor_agents.bootstrap_state.build_checkpointer", return_value=object()) as build_mock,
        ):
            status = bootstrap_state._effective_checkpointer_status()

        self.assertTrue(status["configured"])
        self.assertTrue(status["durable"])
        self.assertEqual("postgres", status["mode"])
        build_mock.assert_called_once()
        self.assertEqual(2, status_mock.call_count)

    async def test_compatibility_catalog_slices_auto_complete_from_live_evidence(self) -> None:
        slices = {item["id"]: item for item in await bootstrap_state.list_bootstrap_slices(limit=100)}

        self.assertEqual("completed", slices["compat-01-active-usage-census"]["status"])
        self.assertEqual("already_satisfied", slices["compat-01-active-usage-census"]["metadata"]["completion_disposition"])
        self.assertEqual("completed", slices["compat-04-completion-detector"]["status"])

    async def test_program_detail_and_supervisor_cycle_keeps_waiting_approval_visible(self) -> None:
        detail = await bootstrap_state.get_bootstrap_program_detail("launch-readiness-bootstrap")

        self.assertIsNotNone(detail)
        self.assertIn(
            detail["current_family"],
            {"foundry_completion", "operator_surface_canonicalization"},
        )
        self.assertIn(detail["recommended_host_id"], {"", "codex_external", "claude_external"})
        self.assertNotEqual(WAITING_APPROVAL_SLICE_ID, detail["next_slice_id"])
        self.assertEqual("durable_persistence_activation", detail["waiting_on_approval_family"])
        self.assertEqual(WAITING_APPROVAL_SLICE_ID, detail["waiting_on_approval_slice_id"])
        durable_family = next(item for item in detail["families"] if item["id"] == "durable_persistence_activation")
        self.assertEqual("waiting_approval", durable_family["status"])
        self.assertGreaterEqual(durable_family["open_blockers"], 0)
        self.assertEqual(WAITING_APPROVAL_SLICE_ID, durable_family["waiting_on_approval_slice_id"])
        self.assertEqual("approval_required", durable_family["next_action"]["kind"])
        self.assertEqual(WAITING_APPROVAL_SLICE_ID, durable_family["next_action"]["slice_id"])

        cycle = await bootstrap_state.run_bootstrap_supervisor_cycle(program_id="launch-readiness-bootstrap")
        self.assertEqual("launch-readiness-bootstrap", cycle["active_program_id"])
        self.assertIn(
            cycle["active_family"],
            {"foundry_completion", "operator_surface_canonicalization"},
        )
        recommendation = cycle["recommendation"]
        if recommendation is not None:
            self.assertNotEqual(WAITING_APPROVAL_SLICE_ID, recommendation.get("slice_id"))

    async def test_runtime_snapshot_exposes_approval_context_for_waiting_slice(self) -> None:
        snapshot = await bootstrap_state.build_bootstrap_runtime_snapshot(include_snapshot_write=False)

        self.assertEqual("durable_persistence_activation", snapshot["waiting_on_approval_family"])
        self.assertEqual(WAITING_APPROVAL_SLICE_ID, snapshot["waiting_on_approval_slice_id"])
        approval_context = snapshot["approval_context"]
        self.assertEqual("approval_required", approval_context["kind"])
        self.assertEqual("db_schema_change", approval_context["packet_id"])
        self.assertEqual(WAITING_APPROVAL_SLICE_ID, approval_context["slice_id"])
        self.assertIn("persist-05-restart-proof", approval_context["follow_on_slice_id"])
        self.assertIn(
            str(self.root / "reports" / "bootstrap" / "durable-persistence-packet.json"),
            approval_context["review_artifacts"],
        )
        self.assertEqual(
            str(self.root / "config" / "automation-backbone" / "approval-packet-registry.json"),
            snapshot["control_artifacts"]["approval_packet_registry_path"],
        )
        self.assertEqual(
            str(self.root / "projects" / "agents" / "src" / "athanor_agents" / "sql" / "bootstrap_durable_state.sql"),
            snapshot["control_artifacts"]["durable_state_sql_path"],
        )
        self.assertEqual(
            str(self.root / "reports" / "bootstrap" / "durable-restart-proof.json"),
            snapshot["control_artifacts"]["durable_restart_proof_path"],
        )

    async def test_runtime_snapshot_can_return_stale_cache_while_refreshing(self) -> None:
        bootstrap_state._BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE = {
            "mode": "ready",
            "generated_at": "cached",
        }
        bootstrap_state._BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT = monotonic() - 1
        bootstrap_state._BOOTSTRAP_RUNTIME_SNAPSHOT_TASK = None
        refresh_gate = asyncio.Event()
        refreshed_snapshot = {
            "mode": "ready",
            "generated_at": "refreshed",
        }

        async def _fake_refresh(*, include_snapshot_write: bool) -> dict[str, str]:
            self.assertFalse(include_snapshot_write)
            await refresh_gate.wait()
            return refreshed_snapshot

        with patch(
            "athanor_agents.bootstrap_state._build_bootstrap_runtime_snapshot_uncached",
            AsyncMock(side_effect=_fake_refresh),
        ):
            cached = await bootstrap_state.build_bootstrap_runtime_snapshot(
                include_snapshot_write=False,
                allow_stale=True,
            )
            self.assertEqual("cached", cached["generated_at"])
            task = bootstrap_state._BOOTSTRAP_RUNTIME_SNAPSHOT_TASK
            self.assertIsNotNone(task)

            refresh_gate.set()
            await asyncio.wait_for(asyncio.shield(task), timeout=1.0)

        refreshed = await bootstrap_state.build_bootstrap_runtime_snapshot(include_snapshot_write=False)
        self.assertEqual("refreshed", refreshed["generated_at"])

    async def test_approve_bootstrap_packet_clears_waiting_approval_and_advances_next_slice(self) -> None:
        result = await bootstrap_state.approve_bootstrap_packet(
            "launch-readiness-bootstrap",
            packet_id="db_schema_change",
            approved_by="operator",
            reason="Approved durable persistence maintenance window.",
        )

        self.assertEqual("db_schema_change", result["approved_packet_id"])
        self.assertIn("persist-04-activation-cutover", result["approved_slice_ids"])
        self.assertIn("persist-05-restart-proof", result["approved_slice_ids"])

        detail = await bootstrap_state.get_bootstrap_program_detail("launch-readiness-bootstrap")
        self.assertIsNotNone(detail)
        self.assertEqual("durable_persistence_activation", detail["current_family"])
        self.assertEqual("persist-04-activation-cutover", detail["next_slice_id"])
        self.assertEqual("", detail["waiting_on_approval_family"])
        self.assertEqual("", detail["waiting_on_approval_slice_id"])
        self.assertEqual("dispatch", detail["next_action"]["kind"])
        self.assertEqual("persist-04-activation-cutover", detail["next_action"]["slice_id"])
        self.assertEqual({}, result["snapshot"]["approval_context"])

        slices = {item["id"]: item for item in await bootstrap_state.list_bootstrap_slices(limit=100)}
        approved_packets = set(slices["persist-04-activation-cutover"]["metadata"].get("approved_packets") or [])
        self.assertIn("db_schema_change", approved_packets)

        blockers = await bootstrap_state.list_bootstrap_blockers(limit=200)
        remaining_open_durable_approval_blockers = [
            blocker
            for blocker in blockers
            if blocker["family"] == "durable_persistence_activation"
            and blocker["status"] == "open"
            and blocker["approval_required"]
            and blocker.get("slice_id") in {"persist-04-activation-cutover", "persist-05-restart-proof"}
        ]
        self.assertEqual([], remaining_open_durable_approval_blockers)

    async def test_mirror_record_normalizes_blank_timestamp_fields_to_null(self) -> None:
        with (
            patch(
                "athanor_agents.bootstrap_state.get_durable_state_status",
                return_value={"configured": True, "schema_ready": True},
            ),
            patch("athanor_agents.bootstrap_state._execute", AsyncMock(return_value=True)) as execute_mock,
        ):
            await bootstrap_state._mirror_record(
                "control.bootstrap_host_state",
                {
                    "host_id": "codex_external",
                    "status": "available",
                    "cooldown_until": "",
                    "last_heartbeat": "",
                    "active_slice_id": "",
                    "last_reason": "",
                    "metadata": {"label": "Codex"},
                    "updated_at": "2026-04-01T22:08:55+00:00",
                },
            )

        _, params = execute_mock.await_args.args
        self.assertEqual("codex_external", params[0])
        self.assertEqual("available", params[1])
        self.assertIsNone(params[2])
        self.assertIsNone(params[3])
        self.assertEqual("", params[4])

    async def test_mirror_record_backfills_missing_created_and_updated_timestamps(self) -> None:
        with (
            patch(
                "athanor_agents.bootstrap_state.get_durable_state_status",
                return_value={"configured": True, "schema_ready": True},
            ),
            patch("athanor_agents.bootstrap_state._execute", AsyncMock(return_value=True)) as execute_mock,
        ):
            await bootstrap_state._mirror_record(
                "control.bootstrap_programs",
                {
                    "program_id": "launch-readiness-bootstrap",
                    "label": "Launch readiness bootstrap",
                    "family_order": ["compatibility_retirement"],
                    "objective": "Test seed",
                    "phase_scope": "software_core_phase_1",
                    "status": "active",
                    "validator_bundle": [],
                    "max_parallel_slices": 2,
                    "metadata": {"seeded_from_registry": True},
                    "created_at": "",
                    "updated_at": "",
                },
            )

        _, params = execute_mock.await_args.args
        self.assertEqual("launch-readiness-bootstrap", params[0])
        self.assertEqual("Launch readiness bootstrap", params[1])
        self.assertIsNotNone(params[8])
        self.assertIsNotNone(params[9])

    async def test_approve_bootstrap_packet_is_idempotent_after_packet_is_already_recorded(self) -> None:
        first = await bootstrap_state.approve_bootstrap_packet(
            "launch-readiness-bootstrap",
            packet_id="db_schema_change",
            approved_by="operator",
            reason="Approved durable persistence maintenance window.",
        )
        second = await bootstrap_state.approve_bootstrap_packet(
            "launch-readiness-bootstrap",
            packet_id="db_schema_change",
            approved_by="operator",
            reason="Retry stale bootstrap approval.",
        )

        self.assertFalse(first.get("already_approved", False))
        self.assertTrue(second["already_approved"])
        self.assertIn("persist-04-activation-cutover", second["approved_slice_ids"])
        self.assertEqual([], second["resolved_blocker_ids"])
        self.assertEqual("persist-04-activation-cutover", second["next_action"]["slice_id"])

    async def test_operator_surface_catalog_slice_auto_completes_from_live_evidence(self) -> None:
        slices = {item["id"]: item for item in await bootstrap_state.list_bootstrap_slices(limit=100)}

        self.assertEqual("completed", slices[REPORT_ONLY_SLICE_ID]["status"])
        self.assertEqual("already_satisfied", slices[REPORT_ONLY_SLICE_ID]["metadata"]["completion_disposition"])
        self.assertEqual("completed", slices["opsurf-02-summary-alignment"]["status"])
        self.assertEqual(
            "already_satisfied",
            slices["opsurf-02-summary-alignment"]["metadata"]["completion_disposition"],
        )
        self.assertEqual("completed", slices["opsurf-04-nav-lock"]["status"])
        self.assertEqual(
            "already_satisfied",
            slices["opsurf-04-nav-lock"]["metadata"]["completion_disposition"],
        )
        self.assertEqual("completed", slices["opsurf-05-surface-contract"]["status"])
        self.assertEqual(
            "already_satisfied",
            slices["opsurf-05-surface-contract"]["metadata"]["completion_disposition"],
        )
        self.assertEqual("completed", slices["foundry-01-proving-packet"]["status"])
        self.assertEqual(
            "already_satisfied",
            slices["foundry-01-proving-packet"]["metadata"]["completion_disposition"],
        )

    async def test_durable_restart_proof_slice_auto_completes_from_live_evidence(self) -> None:
        restart_proof_path = self.root / "reports" / "bootstrap" / "durable-restart-proof.json"
        restart_proof_path.parent.mkdir(parents=True, exist_ok=True)
        restart_proof_path.write_text("{}", encoding="utf-8")
        with patch(
            "athanor_agents.bootstrap_state._durable_persistence_packet_ready",
            return_value={
                "criterion_status": {
                    "configured": True,
                    "durable": True,
                    "schema_ready": True,
                    "restart_proof_passed": True,
                },
                "restart_proof": {"status": "passed"},
            },
        ):
            reason = bootstrap_state._auto_complete_reason(
                {
                    "id": "persist-05-restart-proof",
                    "family": "durable_persistence_activation",
                    "status": "ready",
                    "depth_level": 2,
                    "metadata": {"catalog_slice_id": "persist-05-restart-proof"},
                }
            )

        self.assertIn("restart proof artifact", reason)

    async def test_provider_and_takeover_readiness_detectors_are_live(self) -> None:
        self.assertTrue(bootstrap_state._provider_usage_evidence_ready())
        self.assertTrue(bootstrap_state._vault_litellm_env_audit_ready())
        self.assertTrue(bootstrap_state._provider_catalog_report_ready())
        self.assertTrue(bootstrap_state._secret_surface_report_ready())
        self.assertTrue(bootstrap_state._vault_litellm_auth_repair_packet_ready())
        self.assertTrue(bootstrap_state._takeover_promotion_packet_ready())
        self.assertTrue(bootstrap_state._takeover_criteria_ready())

        ready_provider_slice = {
            "id": "prov-01-read-only-reprobe",
            "family": "provider_repair_preflight",
            "status": "ready",
            "depth_level": 2,
            "metadata": {"catalog_slice_id": "prov-01-read-only-reprobe"},
        }
        ready_takeover_slice = {
            "id": "takeover-01-criteria-evaluator",
            "family": "takeover_promotion_check",
            "status": "ready",
            "depth_level": 2,
            "metadata": {"catalog_slice_id": "takeover-01-criteria-evaluator"},
        }
        self.assertTrue(bootstrap_state._auto_complete_reason(ready_provider_slice))
        self.assertTrue(bootstrap_state._auto_complete_reason(ready_takeover_slice))

    async def test_promote_program_marks_internal_builder_primary(self) -> None:
        with patch("athanor_agents.bootstrap_state.list_foundry_run_records", AsyncMock(return_value=[{"id": "run-1"}])):
            with patch("athanor_agents.bootstrap_state.get_checkpointer_status", return_value={"durable": True, "mode": "postgres"}):
                await bootstrap_state.complete_bootstrap_slice(
                    "persist-01-checkpointer-contract",
                    host_id="codex_external",
                    validation_status="passed",
                    summary="Durable persistence contract is in place.",
                    queue_integration=False,
                )
                promoted = await bootstrap_state.promote_bootstrap_program(
                    "launch-readiness-bootstrap",
                    promoted_by="operator",
                    reason="Internal builder is ready.",
                    force=True,
                )

        self.assertEqual("takeover_promoted", promoted["status"])
        self.assertTrue(promoted["metadata"]["internal_builder_primary"])

    async def test_promote_program_allows_last_external_dependency_gate_without_force(self) -> None:
        with patch(
            "athanor_agents.bootstrap_state.build_takeover_status",
            AsyncMock(
                return_value={
                    "ready": False,
                    "blocker_ids": ["external_dependency_removed"],
                }
            ),
        ):
            promoted = await bootstrap_state.promote_bootstrap_program(
                "launch-readiness-bootstrap",
                promoted_by="operator",
                reason="Internal builder is ready.",
                force=False,
            )

        self.assertEqual("takeover_promoted", promoted["status"])
        self.assertTrue(promoted["metadata"]["internal_builder_primary"])


if __name__ == "__main__":
    unittest.main()
