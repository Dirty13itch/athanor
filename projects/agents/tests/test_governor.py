import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.governor import (
    build_operations_readiness_snapshot,
    build_governor_snapshot,
    evaluate_job_governance,
    get_governor_state,
    pause_automation,
    record_presence_heartbeat,
    resume_automation,
    set_operator_presence,
    set_release_tier,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


class GovernorTests(unittest.IsolatedAsyncioTestCase):
    async def test_pause_and_resume_global_mode_round_trip(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)):
            paused = await pause_automation(reason="maintenance", actor="test-suite")
            self.assertEqual("paused", paused["global_mode"])
            self.assertEqual("maintenance", paused["reason"])

            resumed = await resume_automation(actor="test-suite")
            self.assertEqual("active", resumed["global_mode"])
            self.assertEqual("", resumed["reason"])

            state = await get_governor_state()
            self.assertEqual("active", state["global_mode"])

    async def test_pause_and_resume_lane_round_trip(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)):
            paused = await pause_automation(scope="research_jobs", reason="quota pressure", actor="test-suite")
            self.assertIn("research_jobs", paused["paused_lanes"])

            resumed = await resume_automation(scope="research_jobs", actor="test-suite")
            self.assertNotIn("research_jobs", resumed["paused_lanes"])

    async def test_build_governor_snapshot_reports_live_capacity_governor(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "generated_at": "2026-03-12T08:00:00Z",
                        "posture": "healthy",
                        "queue": {
                            "posture": "healthy",
                            "pending": 1,
                            "running": 1,
                            "max_concurrent": 2,
                            "failed": 0,
                        },
                        "workspace": {
                            "broadcast_items": 2,
                            "capacity": 5,
                            "utilization": 0.4,
                        },
                        "scheduler": {
                            "running": True,
                            "enabled_count": 6,
                        },
                        "provider_reserve": {
                            "posture": "healthy",
                            "constrained_count": 0,
                        },
                        "nodes": [],
                        "recommendations": ["healthy"],
                    }
                ),
            ),
        ):
            snapshot = await build_governor_snapshot()

        self.assertEqual("live", snapshot["status"])
        capacity = next(
            item for item in snapshot["control_stack"] if item["id"] == "capacity-governor"
        )
        self.assertEqual("live", capacity["status"])
        self.assertEqual("healthy", snapshot["capacity"]["posture"])
        self.assertEqual("away", snapshot["presence"]["state"])
        self.assertEqual("auto", snapshot["presence"]["mode"])
        self.assertEqual("production", snapshot["release_tier"]["state"])

    async def test_presence_and_release_tier_round_trip(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)):
            state = await set_operator_presence(
                "phone_only",
                reason="mobile review",
                actor="test-suite",
                mode="manual",
            )
            self.assertEqual("phone_only", state["operator_presence"])
            self.assertEqual("manual", state["presence_mode"])

            state = await set_release_tier("shadow", reason="shadow verification", actor="test-suite")
            self.assertEqual("shadow", state["release_tier"])

            persisted = await get_governor_state()
            self.assertEqual("phone_only", persisted["operator_presence"])
            self.assertEqual("shadow", persisted["release_tier"])

    async def test_presence_and_release_rules_defer_benchmark_jobs(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)):
            await set_operator_presence("asleep", actor="test-suite", mode="manual")
            await set_release_tier("offline_eval", actor="test-suite")

            benchmark = await evaluate_job_governance(
                job_id="benchmark-cycle",
                job_family="benchmarks",
                control_scope="benchmark_cycle",
                owner_agent="system",
            )
            research = await evaluate_job_governance(
                job_id="research:scheduler",
                job_family="research_jobs",
                control_scope="research_jobs",
                owner_agent="research-agent",
            )

        self.assertTrue(benchmark["allowed"])
        self.assertEqual("offline_eval", benchmark["release_tier"])
        self.assertFalse(research["allowed"])
        self.assertEqual("deferred", research["status"])
        self.assertEqual("presence", research["deferred_by"])

    async def test_capacity_and_active_windows_defer_low_priority_jobs(self) -> None:
        fake_redis = FakeRedis()
        capacity_snapshot = {
            "posture": "constrained",
            "queue": {"posture": "constrained"},
            "provider_reserve": {"posture": "healthy"},
            "active_time_windows": [
                {
                    "id": "morning-briefing",
                    "window": "06:30-08:30",
                    "protects": ["daily briefing", "workplan refresh", "notifications"],
                    "status": "active",
                }
            ],
        }
        with patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)):
            await set_operator_presence("at_desk", actor="test-suite", mode="manual")
            deferred = await evaluate_job_governance(
                job_id="benchmark-cycle",
                job_family="benchmarks",
                control_scope="benchmark_cycle",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            )
            allowed = await evaluate_job_governance(
                job_id="daily-digest",
                job_family="daily_digest",
                control_scope="scheduler",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            )

        self.assertFalse(deferred["allowed"])
        self.assertEqual("time_window", deferred["deferred_by"])
        self.assertEqual(["morning-briefing"], deferred["active_window_ids"])
        self.assertEqual("benchmark", deferred["priority_band"])
        self.assertEqual("deferred", deferred["status"])
        self.assertTrue(allowed["allowed"])
        self.assertEqual("governor_critical", allowed["priority_band"])
        self.assertEqual("run", allowed["next_action"])

    async def test_auto_presence_uses_recent_heartbeat(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "generated_at": "2026-03-12T08:00:00Z",
                        "posture": "healthy",
                        "queue": {
                            "posture": "healthy",
                            "pending": 0,
                            "running": 0,
                            "max_concurrent": 2,
                            "failed": 0,
                        },
                        "workspace": {
                            "broadcast_items": 0,
                            "capacity": 5,
                            "utilization": 0.0,
                        },
                        "scheduler": {
                            "running": True,
                            "enabled_count": 6,
                        },
                        "provider_reserve": {
                            "posture": "healthy",
                            "constrained_count": 0,
                        },
                        "active_time_windows": [],
                        "nodes": [],
                        "recommendations": ["healthy"],
                    }
                ),
            ),
        ):
            await record_presence_heartbeat(
                "at_desk",
                source="dashboard_heartbeat",
                reason="Visible dashboard heartbeat",
                actor="dashboard-heartbeat",
            )
            snapshot = await build_governor_snapshot()

        self.assertEqual("auto", snapshot["presence"]["mode"])
        self.assertEqual("at_desk", snapshot["presence"]["state"])
        self.assertTrue(snapshot["presence"]["signal_fresh"])
        self.assertEqual("dashboard_heartbeat", snapshot["presence"]["signal_source"])

    async def test_manual_presence_override_beats_heartbeat(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "generated_at": "2026-03-12T08:00:00Z",
                        "posture": "healthy",
                        "queue": {
                            "posture": "healthy",
                            "pending": 0,
                            "running": 0,
                            "max_concurrent": 2,
                            "failed": 0,
                        },
                        "workspace": {
                            "broadcast_items": 0,
                            "capacity": 5,
                            "utilization": 0.0,
                        },
                        "scheduler": {
                            "running": True,
                            "enabled_count": 6,
                        },
                        "provider_reserve": {
                            "posture": "healthy",
                            "constrained_count": 0,
                        },
                        "active_time_windows": [],
                        "nodes": [],
                        "recommendations": ["healthy"],
                    }
                ),
            ),
        ):
            await record_presence_heartbeat(
                "at_desk",
                source="dashboard_heartbeat",
                actor="dashboard-heartbeat",
            )
            await set_operator_presence(
                "asleep",
                reason="Sleeping hours",
                actor="test-suite",
                mode="manual",
            )
            snapshot = await build_governor_snapshot()

        self.assertEqual("manual", snapshot["presence"]["mode"])
        self.assertEqual("asleep", snapshot["presence"]["state"])
        self.assertEqual("at_desk", snapshot["presence"]["signal_state"])

    async def test_operations_readiness_snapshot_exposes_live_layers(self) -> None:
        with patch(
            "athanor_agents.operator_tests.build_operator_tests_snapshot",
            AsyncMock(
                return_value={
                    "generated_at": "2026-03-12T08:00:00Z",
                    "status": "live_partial",
                    "last_outcome": "partial",
                    "last_run_at": "2026-03-12T08:00:00Z",
                    "flow_count": 7,
                    "flows": [
                        {
                            "id": "pause_resume",
                            "title": "Pause and resume automation",
                            "description": "Synthetic operator test",
                            "status": "live",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:00:00Z",
                            "last_duration_ms": 42,
                            "checks_passed": 4,
                            "checks_total": 4,
                            "evidence": ["test_governor.py"],
                            "notes": [],
                        },
                        {
                            "id": "presence_tier",
                            "title": "Presence and release-tier posture",
                            "description": "Synthetic operator test",
                            "status": "live",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:00:00Z",
                            "last_duration_ms": 41,
                            "checks_passed": 4,
                            "checks_total": 4,
                            "evidence": ["test_governor.py"],
                            "notes": [],
                        },
                        {
                            "id": "scheduled_job_governance",
                            "title": "Scheduled job posture and deferral",
                            "description": "Synthetic operator test",
                            "status": "live",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:00:00Z",
                            "last_duration_ms": 40,
                            "checks_passed": 5,
                            "checks_total": 5,
                            "evidence": ["test_backbone.py"],
                            "notes": [],
                        },
                        {
                            "id": "economic_governance",
                            "title": "Economic governance verification",
                            "description": "Synthetic operator test",
                            "status": "live_partial",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:03:00Z",
                            "last_duration_ms": 22,
                            "checks_passed": 5,
                            "checks_total": 5,
                            "evidence": ["test_operator_tests.py"],
                            "notes": [],
                            "details": {
                                "provider_count": 3,
                                "recent_lease_count": 4,
                                "constrained_count": 1,
                            },
                        },
                        {
                            "id": "restore_drill",
                            "title": "Restore drill and recovery flow",
                            "description": "Synthetic operator test",
                            "status": "configured",
                            "last_outcome": "ready_for_drill",
                            "last_run_at": "2026-03-12T08:00:00Z",
                            "last_duration_ms": 17,
                            "checks_passed": 3,
                            "checks_total": 3,
                            "evidence": ["OPERATOR_RUNBOOKS.md"],
                            "notes": [],
                        },
                        {
                            "id": "promotion_ladder",
                            "title": "Promotion ladder rehearsal",
                            "description": "Synthetic operator test",
                            "status": "live_partial",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:05:00Z",
                            "last_duration_ms": 31,
                            "checks_passed": 6,
                            "checks_total": 6,
                            "evidence": ["test_promotion_control.py"],
                            "notes": [],
                        },
                        {
                            "id": "data_lifecycle",
                            "title": "Data lifecycle verification",
                            "description": "Synthetic operator test",
                            "status": "live_partial",
                            "last_outcome": "passed",
                            "last_run_at": "2026-03-12T08:06:00Z",
                            "last_duration_ms": 25,
                            "checks_passed": 5,
                            "checks_total": 5,
                            "evidence": ["test_operator_tests.py"],
                            "notes": [],
                            "details": {
                                "class_count": 5,
                                "run_count": 6,
                                "eval_artifact_count": 3,
                            },
                        },
                    ],
                }
            ),
            patch(
                "athanor_agents.governor.build_promotion_controls_snapshot",
                AsyncMock(
                    return_value={
                        "generated_at": "2026-03-12T08:05:00Z",
                        "status": "live_partial",
                        "tiers": ["offline_eval", "shadow", "sandbox", "canary", "production"],
                        "ritual": [],
                        "counts": {"rolled_back": 1},
                        "active_promotions": [],
                        "recent_promotions": [],
                        "recent_events": [],
                        "candidate_queue": [],
                        "next_actions": [],
                    }
                ),
            ),
        ):
            snapshot = await build_operations_readiness_snapshot()

        self.assertEqual("live_partial", snapshot["status"])
        self.assertGreaterEqual(len(snapshot["runbooks"]["items"]), 4)
        self.assertGreaterEqual(len(snapshot["backup_restore"]["critical_stores"]), 4)
        self.assertGreaterEqual(len(snapshot["synthetic_operator_tests"]["flows"]), 4)
        self.assertEqual("live_partial", snapshot["release_ritual"]["status"])
        self.assertEqual("passed", snapshot["release_ritual"]["last_outcome"])
        self.assertEqual("live_partial", snapshot["runbooks"]["status"])
        self.assertEqual("live_partial", snapshot["economic_governance"]["status"])
        self.assertEqual("live_partial", snapshot["data_lifecycle"]["status"])
        self.assertEqual(3, snapshot["economic_governance"]["provider_count"])
        self.assertEqual(6, snapshot["data_lifecycle"]["run_count"])
        self.assertEqual("governor_mediated", snapshot["tool_permissions"]["default_mode"])


if __name__ == "__main__":
    unittest.main()
