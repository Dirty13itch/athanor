import unittest
from asyncio import run
from unittest.mock import AsyncMock, patch

from athanor_agents.command_hierarchy import (
    AUTHORITY_ORDER,
    COMMAND_RIGHTS,
    build_system_map_snapshot,
    build_plan_packet,
    classify_policy_class,
    normalize_workload_class,
)


class CommandHierarchyTest(unittest.TestCase):
    def test_authority_order_places_constitution_above_governor(self) -> None:
        ids = [entry["id"] for entry in AUTHORITY_ORDER]
        self.assertEqual(["shaun", "constitution", "governor"], ids[:3])

    def test_policy_class_routes_refusal_sensitive_work_to_sovereign_lane(self) -> None:
        classification = classify_policy_class("Draft an uncensored explicit scene with taboo themes.")
        self.assertEqual("refusal_sensitive", classification["policy_class"])
        self.assertEqual("sovereign_local", classification["meta_lane"])
        self.assertFalse(classification["cloud_allowed"])
        self.assertTrue(classification["requires_sovereign"])

    def test_policy_class_respects_explicit_sovereign_metadata(self) -> None:
        classification = classify_policy_class(
            "Architecture note for a private project.",
            metadata={"sovereign_only": True},
        )
        self.assertEqual("sovereign_only", classification["policy_class"])
        self.assertEqual("sovereign_local", classification["meta_lane"])
        self.assertFalse(classification["cloud_allowed"])

    def test_governor_rights_remain_posture_only(self) -> None:
        governor = next(entry for entry in COMMAND_RIGHTS if entry["subject"] == "Athanor Governor")
        self.assertIn("route work", governor["can"])
        self.assertIn("pause or resume automation", governor["can"])
        self.assertIn("choose fallback or degraded mode", governor["can"])
        self.assertNotIn("create durable tasks", governor["can"])
        self.assertNotIn("issue leases", governor["can"])
        self.assertNotIn("own recurring schedules", governor["can"])

    def test_meta_lanes_remain_advisory(self) -> None:
        meta = next(entry for entry in COMMAND_RIGHTS if entry["subject"] == "Meta Lanes")
        self.assertIn("plan", meta["can"])
        self.assertIn("directly run tools", meta["cannot"])
        self.assertIn("issue leases", meta["cannot"])

    def test_system_map_snapshot_includes_frontier_and_sovereign_meta_lanes(self) -> None:
        with (
            patch(
                "athanor_agents.governor.build_governor_snapshot",
                AsyncMock(
                    return_value={
                        "capacity": {"posture": "healthy", "active_time_windows": []},
                        "presence": {
                            "state": "at_desk",
                            "effective_reason": "dashboard heartbeat",
                        },
                    }
                ),
            ),
            patch(
                "athanor_agents.governor.build_operations_readiness_snapshot",
                AsyncMock(
                    return_value={
                        "economic_governance": {
                            "status": "live_partial",
                            "provider_count": 6,
                            "recent_lease_count": 10,
                        },
                        "data_lifecycle": {
                            "status": "live_partial",
                            "run_count": 12,
                            "eval_artifact_count": 6,
                        },
                        "backup_restore": {
                            "status": "live_partial",
                            "verified_store_count": 4,
                            "last_drill_at": "2026-03-12T21:20:19Z",
                        },
                        "tool_permissions": {
                            "status": "live_partial",
                            "enforced_subject_count": 4,
                            "denied_action_count": 3,
                        },
                        "release_ritual": {
                            "status": "live_partial",
                            "active_promotion_count": 0,
                            "last_rehearsal_at": "2026-03-12T21:20:19Z",
                        },
                        "autonomy_activation": {
                            "status": "live_partial",
                            "activation_state": "ready_for_operator_enable",
                            "current_phase_id": "software_core_phase_1",
                            "current_phase_status": "ready",
                            "next_phase_id": "expanded_core_phase_2",
                            "next_phase_status": "blocked",
                            "next_phase_scope": "bounded_plus_domain_sidecars",
                            "next_phase_blocker_count": 1,
                            "next_phase_blocker_ids": ["vault_provider_auth_repair"],
                            "enabled_agents": ["coding-agent", "research-agent"],
                            "allowed_workload_classes": ["coding_implementation"],
                            "blocked_workload_classes": ["explicit_dialogue"],
                        },
                    }
                ),
            ),
        ):
            snapshot = run(
                build_system_map_snapshot(
                    {
                        "coding-agent": {
                            "description": "Controlled repo execution",
                            "tools": ["write_file", "run_command"],
                            "type": "proactive",
                        },
                        "research-agent": {
                            "description": "External research and synthesis",
                            "tools": ["web_search", "fetch_page"],
                            "type": "reactive",
                        },
                    }
                )
            )
        

        lane_ids = {lane["id"] for lane in snapshot["meta_lanes"]}
        self.assertIn("frontier_cloud", lane_ids)
        self.assertIn("sovereign_local", lane_ids)
        self.assertIn(
            snapshot["operational_governance"]["backup_restore"]["status"],
            {"configured", "live_partial", "live"},
        )
        self.assertEqual(
            "software_core_phase_1",
            snapshot["operational_governance"]["autonomy_activation"]["current_phase_id"],
        )
        self.assertIsNone(
            snapshot["operational_governance"]["autonomy_activation"]["next_phase_id"]
        )
        self.assertEqual(
            [],
            snapshot["operational_governance"]["autonomy_activation"]["next_phase_blocker_ids"],
        )

    def test_system_map_snapshot_degrades_when_runtime_components_timeout(self) -> None:
        with (
            patch(
                "athanor_agents.governor.build_governor_snapshot",
                AsyncMock(side_effect=TimeoutError("governor timed out")),
            ),
            patch(
                "athanor_agents.governor.build_operations_readiness_snapshot",
                AsyncMock(side_effect=TimeoutError("operations timed out")),
            ),
        ):
            snapshot = run(
                build_system_map_snapshot(
                    {
                        "coding-agent": {
                            "description": "Controlled repo execution",
                            "tools": ["write_file", "run_command"],
                            "type": "proactive",
                        },
                    }
                )
            )

        self.assertEqual("degraded", snapshot["operational_governance"]["runtime_state"]["status"])
        self.assertIn("governor_snapshot", snapshot["operational_governance"]["runtime_state"]["error"])
        self.assertIn("operations_readiness", snapshot["operational_governance"]["runtime_state"]["error"])
        self.assertIn("frontier_cloud", {lane["id"] for lane in snapshot["meta_lanes"]})

    def test_subscription_task_classes_normalize_to_governance_workloads(self) -> None:
        self.assertEqual("coding_implementation", normalize_workload_class("multi_file_implementation"))
        self.assertEqual("repo_audit", normalize_workload_class("repo_wide_audit"))
        self.assertEqual("background_transform", normalize_workload_class("cheap_bulk_transform"))

    def test_plan_packet_uses_workload_defaults_for_subscription_task_classes(self) -> None:
        packet = build_plan_packet(
            prompt="Implement the next repo change safely.",
            task_class="multi_file_implementation",
            requester="coding-agent",
        )
        self.assertEqual("coding_implementation", packet["workload_class"])
        self.assertEqual("private_but_cloud_allowed", packet["policy_class"])
        self.assertEqual("coding_worker", packet["worker_lane"])

    def test_refusal_sensitive_prompt_overrides_cloud_safe_workload_default(self) -> None:
        classification = classify_policy_class(
            "Create an uncensored explicit scene outline for the next chapter.",
            task_class="repo_wide_audit",
        )
        self.assertEqual("refusal_sensitive", classification["policy_class"])
        self.assertEqual("sovereign_local", classification["meta_lane"])


if __name__ == "__main__":
    unittest.main()
