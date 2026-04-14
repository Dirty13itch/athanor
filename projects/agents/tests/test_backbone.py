import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import athanor_agents.governor_backbone as governor_backbone
from athanor_agents.backbone import (
    build_execution_run_records,
    build_quota_lease_summary,
    build_scheduled_job_records,
)
from athanor_agents.governor_backbone import build_capacity_snapshot
from athanor_agents.governor import set_operator_presence, set_release_tier


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


class BackboneOperatorFlowTests(unittest.IsolatedAsyncioTestCase):
    def test_load_truth_inventory_payload_uses_existing_candidate_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            truth_dir = Path(temp_dir)
            payload_path = truth_dir / "capacity-telemetry.json"
            payload_path.write_text(json.dumps({"capacity_summary": {"scheduler_slot_count": 5}}), encoding="utf-8")
            with patch(
                "athanor_agents.governor_backbone._candidate_truth_inventory_dirs",
                return_value=[truth_dir],
            ):
                payload = governor_backbone._load_truth_inventory_payload("capacity-telemetry.json")

        self.assertEqual(5, payload["capacity_summary"]["scheduler_slot_count"])

    async def test_quota_summary_for_capacity_falls_back_to_truth_inventory(self) -> None:
        with patch(
            "athanor_agents.backbone.build_quota_lease_summary",
            AsyncMock(side_effect=TimeoutError("slow provider posture")),
        ), patch(
            "athanor_agents.governor_backbone._load_truth_inventory_payload",
            return_value={
                "records": [
                    {
                        "provider_id": "zai_api",
                        "remaining_units": 3,
                        "usage_mode": "metered_api",
                        "harvest_priority": "glm_api_overflow",
                        "last_observed_at": "2026-04-14T04:34:49Z",
                    }
                ]
            },
        ):
            summary = await governor_backbone._build_quota_summary_for_capacity(limit=5, timeout_seconds=0.01)

        self.assertEqual("truth_inventory_fallback", summary["policy_source"])
        self.assertEqual("zai_api", summary["provider_summaries"][0]["provider"])
        self.assertEqual("available", summary["provider_summaries"][0]["availability"])

    async def test_capacity_snapshot_includes_slot_aware_local_compute_truth(self) -> None:
        with (
            patch(
                "athanor_agents.governor_backbone._load_local_compute_truth",
                return_value={
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 5,
                    "harvestable_scheduler_slot_count": 2,
                    "idle_harvest_slots_open": True,
                    "open_harvest_slots": [
                        {
                            "id": "F:TP4",
                            "zone_id": "F",
                            "harvest_intent": "primary_sovereign_bulk",
                            "harvestable_gpu_count": 4,
                            "node_ids": ["foundry"],
                        },
                        {
                            "id": "W:1",
                            "zone_id": "W",
                            "harvest_intent": "creative_batch_support",
                            "harvestable_gpu_count": 1,
                            "node_ids": ["workshop"],
                        },
                    ],
                    "scheduler_queue_depth": 0,
                    "scheduler_source": "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                    "scheduler_observed_at": "2026-04-14T04:33:59.706521+00:00",
                },
            ),
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"by_status": {"pending": 1, "failed": 0}, "currently_running": 1, "max_concurrent": 2}),
            ),
            patch(
                "athanor_agents.scheduler.get_schedule_status",
                AsyncMock(return_value={"scheduler_running": True, "schedules": [{"enabled": True}]}),
            ),
            patch(
                "athanor_agents.workspace.get_stats",
                AsyncMock(return_value={"broadcast_items": 0, "capacity": 0, "utilization": 0.0}),
            ),
            patch("athanor_agents.workspace.get_cluster_capacity", AsyncMock(return_value={})),
            patch("athanor_agents.backbone.build_quota_lease_summary", AsyncMock(return_value={"provider_summaries": []})),
        ):
            snapshot = await build_capacity_snapshot()

        self.assertEqual(5, snapshot["local_compute"]["scheduler_slot_count"])
        self.assertEqual(2, snapshot["local_compute"]["harvestable_scheduler_slot_count"])
        self.assertTrue(snapshot["local_compute"]["idle_harvest_slots_open"])
        self.assertEqual(5, snapshot["workspace"]["capacity"])
        self.assertAlmostEqual(0.6, snapshot["workspace"]["utilization"])
        self.assertTrue(any("F:TP4" in item for item in snapshot["recommendations"]))

    async def test_deferred_scheduled_jobs_reflect_governor_presence_and_tier(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.governor_backbone._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.governor_backbone.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "posture": "healthy",
                        "queue": {
                            "posture": "healthy",
                        },
                        "provider_reserve": {
                            "posture": "healthy",
                        },
                        "active_time_windows": [],
                    }
                ),
            ),
            patch(
                "athanor_agents.backbone.get_schedule_status",
                AsyncMock(
                    return_value={
                        "scheduler_running": True,
                        "schedules": [
                            {
                                "agent": "research-agent",
                                "interval_seconds": 7200,
                                "interval_human": "2h",
                                "enabled": True,
                                "last_run": None,
                                "next_run_in": 3600,
                                "priority": "low",
                            }
                        ],
                    }
                ),
            ),
            patch("athanor_agents.backbone.query_events", AsyncMock(return_value=[])),
            patch("athanor_agents.backbone.list_jobs", AsyncMock(return_value=[])),
            patch("athanor_agents.backbone._read_schedule_marker", AsyncMock(return_value=None)),
        ):
            await set_operator_presence("asleep", actor="test-suite")
            await set_release_tier("offline_eval", actor="test-suite")
            jobs = await build_scheduled_job_records(limit=50)

        indexed = {job["id"]: job for job in jobs}
        self.assertEqual("deferred", indexed["agent-schedule:research-agent"]["current_state"])
        self.assertIn("Deferred", indexed["agent-schedule:research-agent"]["governor_reason"])
        self.assertEqual("healthy", indexed["agent-schedule:research-agent"]["capacity_posture"])
        self.assertEqual("healthy", indexed["agent-schedule:research-agent"]["queue_posture"])
        self.assertEqual("healthy", indexed["agent-schedule:research-agent"]["provider_posture"])
        self.assertEqual("presence", indexed["agent-schedule:research-agent"]["deferred_by"])
        self.assertEqual("wait_for_presence_change", indexed["agent-schedule:research-agent"]["next_action"])
        self.assertEqual("scheduled", indexed["benchmark-cycle"]["current_state"])
        self.assertEqual("benchmark", indexed["benchmark-cycle"]["priority_band"])
        for job_id in (
            "pipeline-cycle",
            "owner-model",
            "nightly-optimization",
            "knowledge-refresh",
            "weekly-dpo-training",
            "creative-cascade",
            "code-cascade",
            "research:scheduler",
        ):
            self.assertIn(job_id, indexed)

    async def test_execution_runs_expose_lineage_and_governance_versions(self) -> None:
        task = {
            "id": "task-123",
            "agent": "coding-agent",
            "status": "completed",
            "prompt": "Implement governed proving-ground lineage",
            "created_at": 1_700_000_000,
            "started_at": 1_700_000_030,
            "completed_at": 1_700_000_090,
            "parent_task_id": "task-parent",
            "metadata": {
                "source": "task",
                "execution_lease": {
                    "id": "lease-123",
                    "provider": "openai_codex",
                    "metadata": {
                        "policy_class": "cloud_safe",
                        "approval_mode": "act_notify",
                        "meta_lane": "frontier_cloud",
                        "command_decision_id": "decision-123",
                    },
                },
                "command_decision": {
                    "id": "decision-123",
                    "authority_layer": "governor",
                    "policy_class": "cloud_safe",
                    "meta_lane": "frontier_cloud",
                    "policy_version": "2026-03-12",
                    "prompt_version": "inline-unversioned",
                },
                "plan_packet": {
                    "id": "packet-123",
                    "approval_mode": "act_notify",
                    "supervisor_lane": "frontier_supervisor",
                    "worker_lane": "coding_worker",
                    "judge_lane": "judge_verifier",
                    "prompt_version": "inline-unversioned",
                },
                "governance_versions": {
                    "prompt_version": "inline-unversioned",
                    "policy_version": "2026-03-12",
                    "corpus_version": "2026-q1",
                },
            },
        }
        with (
            patch("athanor_agents.backbone.list_recent_tasks", AsyncMock(return_value=[task])),
            patch("athanor_agents.backbone.list_handoff_bundles", AsyncMock(return_value=[])),
        ):
            runs = await build_execution_run_records(limit=5)

        self.assertEqual(1, len(runs))
        run = runs[0]
        self.assertEqual("run-task-123", run["id"])
        self.assertEqual("frontier_supervisor", run["supervisor_lane"])
        self.assertEqual("coding_worker", run["worker_lane"])
        self.assertEqual("judge_verifier", run["judge_lane"])
        self.assertEqual("inline-unversioned", run["prompt_version"])
        self.assertEqual("2026-03-12", run["policy_version"])
        self.assertEqual("2026-q1", run["corpus_version"])
        self.assertEqual("run-task-parent", run["lineage"]["parent_run_id"])
        self.assertEqual("linked", run["artifact_provenance"]["status"])
        self.assertGreaterEqual(run["artifact_provenance"]["artifact_ref_count"], 1)

    async def test_quota_summary_uses_standardized_provider_posture(self) -> None:
        with (
            patch(
                "athanor_agents.backbone.build_provider_posture_records",
                AsyncMock(
                    return_value=[
                        {
                            "provider": "openai_codex",
                            "lane": "async_cloud_executor",
                            "availability": "degraded",
                            "provider_state": "degraded",
                            "state_reasons": ["adapter_or_recent_execution_degraded"],
                            "reserve_state": "premium_async",
                            "privacy": "cloud",
                            "limit": 0,
                            "remaining": 0,
                            "throttle_events": 0,
                            "recent_outcomes": [{"outcome": "fallback_to_handoff", "count": 1}],
                            "last_issued_at": None,
                            "last_outcome_at": None,
                            "direct_execution_ready": False,
                            "governed_handoff_ready": True,
                            "execution_mode": "handoff_bundle",
                            "bridge_status": "degraded",
                            "recent_execution_state": "degraded",
                            "recent_execution_detail": "Recent adapter failure.",
                            "next_action": "investigate_adapter",
                            "pending_handoffs": 1,
                            "completed_handoffs": 0,
                            "failed_handoffs": 0,
                            "fallback_handoffs": 1,
                            "direct_execution_count": 0,
                            "handoff_bundle_count": 1,
                        }
                    ]
                ),
            ),
            patch(
                "athanor_agents.backbone.list_execution_leases",
                AsyncMock(
                    return_value=[
                        {
                            "id": "lease-xyz",
                            "requester": "coding-agent",
                            "provider": "openai_codex",
                            "task_class": "async_backlog_execution",
                            "surface": "cloud_task",
                            "created_at": 1_700_000_000,
                            "metadata": {
                                "meta_lane": "frontier_cloud",
                                "policy_class": "cloud_safe",
                                "approval_mode": "act_notify",
                                "command_decision_id": "decision-xyz",
                            },
                        }
                    ]
                ),
            ),
        ):
            summary = await build_quota_lease_summary(limit=5)

        self.assertEqual(1, summary["count"])
        provider = summary["provider_summaries"][0]
        self.assertEqual("degraded", provider["provider_state"])
        self.assertEqual("investigate_adapter", provider["next_action"])
        self.assertEqual(1, provider["fallback_handoffs"])


if __name__ == "__main__":
    unittest.main()
