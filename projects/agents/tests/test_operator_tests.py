import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.governor import get_governor_state
from athanor_agents.operator_tests import (
    _sanitize_artifact_reference,
    build_operator_tests_snapshot,
    run_operator_tests,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = value

    async def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.lists.get(key, [])
        if not values:
            return
        self.lists[key] = values[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]


class FakeHttpResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict | None = None,
        content_type: str = "application/json",
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {"content-type": content_type}

    def json(self) -> dict:
        return dict(self._payload)


class FakeRestoreDrillHttpClient:
    async def __aenter__(self) -> "FakeRestoreDrillHttpClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, headers: dict | None = None) -> FakeHttpResponse:
        if url.endswith("/collections"):
            return FakeHttpResponse(200, {"result": {"collections": [{"name": "activity"}]}})
        if url.endswith("/health"):
            return FakeHttpResponse(401, content_type="text/plain")
        if url.endswith("/api/operator/session"):
            return FakeHttpResponse(403, content_type="text/plain")
        return FakeHttpResponse(401, content_type="text/plain")


class OperatorTestsRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_sanitize_artifact_reference_redacts_embedded_credentials(self) -> None:
        self.assertEqual(
            "redis://192.168.1.203:6379/0",
            _sanitize_artifact_reference("redis://:super-secret@192.168.1.203:6379/0"),
        )
        self.assertEqual(
            "https://example.com/path",
            _sanitize_artifact_reference("https://user:pass@example.com/path"),
        )
        self.assertEqual(
            "http://dashboard/api/system-map",
            _sanitize_artifact_reference("http://dashboard/api/system-map"),
        )

    async def test_pause_resume_operator_flow_runs_and_restores_governor_state(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.governor_backbone._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["pause_resume"], actor="test-suite")
            state = await get_governor_state()

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "pause_resume")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live", flow["status"])
        self.assertEqual("active", state["global_mode"])
        self.assertNotIn("maintenance", state["paused_lanes"])

    async def test_sovereign_routing_operator_flow_prefers_local_for_protected_work(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["sovereign_routing"], actor="test-suite")
            stored = await build_operator_tests_snapshot()

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "sovereign_routing")
        stored_flow = next(flow for flow in stored["flows"] if flow["id"] == "sovereign_routing")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live", flow["status"])
        self.assertEqual("passed", stored_flow["last_outcome"])
        self.assertTrue(
            any("Sovereign path selected athanor_local" in note for note in flow["notes"])
        )

    async def test_restore_drill_operator_flow_records_live_store_evidence(self) -> None:
        fake_redis = FakeRedis()
        store_results = [
            {
                "id": "redis_critical_state",
                "label": "Redis critical state",
                "verified": True,
                "probe_status": "verified",
                "probe_summary": "Redis probe ok.",
                "checked_at": "2026-03-12T12:00:00Z",
                "artifacts": ["redis://example"],
            },
            {
                "id": "qdrant_memory",
                "label": "Qdrant memory",
                "verified": True,
                "probe_status": "verified",
                "probe_summary": "Qdrant probe ok.",
                "checked_at": "2026-03-12T12:00:00Z",
                "artifacts": ["http://qdrant/collections"],
            },
            {
                "id": "neo4j_graph",
                "label": "Neo4j graph",
                "verified": True,
                "probe_status": "verified",
                "probe_summary": "Neo4j probe ok.",
                "checked_at": "2026-03-12T12:00:00Z",
                "artifacts": ["http://neo4j"],
            },
            {
                "id": "dashboard_agent_deploy_state",
                "label": "Dashboard and agent deployment state",
                "verified": True,
                "probe_status": "verified",
                "probe_summary": "Deploy-state probe ok.",
                "checked_at": "2026-03-12T12:00:00Z",
                "artifacts": ["http://dashboard/api/operator/session"],
            },
        ]
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.operator_tests._collect_restore_store_results", AsyncMock(return_value=store_results)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["restore_drill"], actor="test-suite")
            stored = await build_operator_tests_snapshot()

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "restore_drill")
        stored_flow = next(flow for flow in stored["flows"] if flow["id"] == "restore_drill")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual(4, flow["details"]["verified_store_count"])
        self.assertEqual(4, len(flow["details"]["stores"]))
        self.assertEqual("passed", stored_flow["last_outcome"])

    async def test_restore_drill_counts_auth_protected_deploy_surfaces_as_reachable(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.operator_tests.httpx.AsyncClient",
                return_value=FakeRestoreDrillHttpClient(),
            ),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["restore_drill"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "restore_drill")
        deploy_store = next(
            store
            for store in flow["details"]["stores"]
            if store["id"] == "dashboard_agent_deploy_state"
        )
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual(4, flow["details"]["verified_store_count"])
        self.assertTrue(deploy_store["verified"])
        self.assertIn("auth-protected", deploy_store["probe_summary"])

    async def test_promotion_ladder_operator_flow_rehearses_and_rolls_back(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.promotion_control._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["promotion_ladder"], actor="test-suite")
            stored = await build_operator_tests_snapshot()

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "promotion_ladder")
        stored_flow = next(flow for flow in stored["flows"] if flow["id"] == "promotion_ladder")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual("frontier_supervisor", flow["details"]["role_id"])
        self.assertEqual("Codex", flow["details"]["candidate"])
        self.assertEqual(
            ["offline_eval", "shadow", "sandbox", "canary"],
            flow["details"]["traversed_tiers"],
        )
        self.assertEqual("Claude", flow["details"]["rollback_target"])
        self.assertEqual("passed", stored_flow["last_outcome"])

    async def test_retirement_policy_flow_rehearses_and_rolls_back(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.retirement_control._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["retirement_policy"], actor="test-suite")
            stored = await build_operator_tests_snapshot()

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "retirement_policy")
        stored_flow = next(flow for flow in stored["flows"] if flow["id"] == "retirement_policy")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual("frontier_supervisor", flow["details"]["role_id"])
        self.assertEqual(
            ["active", "deprecated", "retired_reference_only"],
            flow["details"]["traversed_stages"],
        )
        self.assertEqual("active", flow["details"]["rollback_target"])
        self.assertEqual("passed", stored_flow["last_outcome"])

    async def test_economic_governance_flow_surfaces_live_provider_evidence(self) -> None:
        fake_redis = FakeRedis()
        summary = {
            "provider_summaries": [
                {"provider": "anthropic_claude_code", "reserve_state": "premium_interactive", "availability": "available"},
                {"provider": "google_gemini", "reserve_state": "burn_early", "availability": "constrained"},
            ],
            "recent_leases": [{"id": "lease-1"}, {"id": "lease-2"}],
        }
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.backbone.build_quota_lease_summary", AsyncMock(return_value=summary)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["economic_governance"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "economic_governance")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual(2, flow["details"]["provider_count"])
        self.assertEqual(1, flow["details"]["constrained_count"])

    async def test_tool_permissions_flow_surfaces_live_enforcement_evidence(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["tool_permissions"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "tool_permissions")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertGreaterEqual(flow["details"]["subject_count"], 4)
        self.assertEqual(flow["details"]["subject_count"], flow["details"]["enforced_subject_count"])
        self.assertEqual(3, flow["details"]["denied_action_count"])

    async def test_data_lifecycle_flow_surfaces_runtime_and_eval_evidence(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.backbone.build_execution_run_records",
                AsyncMock(return_value=[{"id": "run-1"}, {"id": "run-2"}]),
            ),
            patch(
                "athanor_agents.proving_ground.build_proving_ground_snapshot",
                AsyncMock(
                    return_value={
                        "latest_run": {"timestamp": "2026-03-12T12:00:00Z"},
                        "recent_results": [{"id": "eval-1"}, {"id": "eval-2"}],
                    }
                ),
            ),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["data_lifecycle"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "data_lifecycle")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual(2, flow["details"]["run_count"])
        self.assertEqual(2, flow["details"]["eval_artifact_count"])
        self.assertEqual("sovereign_local", flow["details"]["sovereign_meta_lane"])

    async def test_provider_fallback_flow_reports_live_when_direct_or_bridge_lane_exists(self) -> None:
        fake_redis = FakeRedis()
        snapshot = {
            "adapters": [
                {
                    "provider": "athanor_local",
                    "execution_mode": "local_runtime",
                    "adapter_available": True,
                    "supports_handoff": False,
                },
                {
                    "provider": "anthropic_claude_code",
                    "execution_mode": "bridge_cli",
                    "adapter_available": True,
                    "supports_handoff": True,
                },
                {
                    "provider": "google_gemini",
                    "execution_mode": "handoff_bundle",
                    "adapter_available": False,
                    "supports_handoff": True,
                },
            ],
            "recent_leases": [{"id": "lease-1"}],
        }
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.provider_execution.build_provider_execution_snapshot", AsyncMock(return_value=snapshot)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            result = await run_operator_tests(flow_ids=["provider_fallback"], actor="test-suite")

        flow = next(flow for flow in result["flows"] if flow["id"] == "provider_fallback")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live", flow["status"])

    async def test_stuck_queue_recovery_flow_rehearses_pause_and_resume_with_lineage(self) -> None:
        fake_redis = FakeRedis()
        scheduled_jobs = [
            {
                "id": "daily-digest",
                "control_scope": "scheduler",
                "current_state": "paused",
                "paused": True,
                "deep_link": "/",
            }
        ]
        runs = [
            {
                "id": "run-1",
                "artifact_refs": [{"label": "task", "href": "/tasks?task=1"}],
            }
        ]
        capacity = {
            "queue": {
                "posture": "healthy",
                "pending": 0,
                "running": 1,
                "max_concurrent": 2,
                "failed": 0,
            }
        }
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.governor._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.governor_backbone._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.backbone.build_scheduled_job_records", AsyncMock(return_value=scheduled_jobs)),
            patch("athanor_agents.backbone.build_execution_run_records", AsyncMock(return_value=runs)),
            patch("athanor_agents.governor.build_capacity_snapshot", AsyncMock(return_value=capacity)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["stuck_queue_recovery"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "stuck_queue_recovery")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual(1, flow["details"]["scheduler_job_count"])
        self.assertEqual(1, flow["details"]["run_count"])
        self.assertEqual("healthy", flow["details"]["queue_posture"])

    async def test_incident_review_flow_surfaces_alert_stream_and_run_counts(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch(
                "athanor_agents.alerts.get_active_alerts",
                AsyncMock(return_value={"alerts": [{"name": "provider pressure"}]}),
            ),
            patch(
                "athanor_agents.alerts.get_alert_history",
                AsyncMock(return_value=[{"alertname": "provider pressure"}]),
            ),
            patch(
                "athanor_agents.backbone.build_operator_stream",
                AsyncMock(
                    return_value=[
                        {
                            "id": "event-1",
                            "severity": "warning",
                            "event_type": "alert_active",
                            "subject": "subscription-broker",
                            "summary": "Provider posture is degraded.",
                            "deep_link": "/notifications",
                        }
                    ]
                ),
            ),
            patch(
                "athanor_agents.backbone.build_execution_run_records",
                AsyncMock(return_value=[{"id": "run-1", "summary": "recent run", "provider": "athanor_local"}]),
            ),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["incident_review"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "incident_review")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual(1, flow["details"]["active_alert_count"])
        self.assertEqual(1, flow["details"]["stream_event_count"])
        self.assertEqual(1, flow["details"]["run_count"])

    async def test_goose_operator_shell_flow_passes_when_command_is_available(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.operator_tests.shutil.which", side_effect=lambda command: f"/tmp/{command}" if command == "goose" else None),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["goose_operator_shell"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "goose_operator_shell")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual("goose_wrapped", flow["details"]["wrapper_mode"])
        self.assertTrue(flow["details"]["command_probe"]["available"])
        self.assertTrue(flow["details"]["boundary_evidence"]["exists"])
        self.assertTrue(flow["details"]["boundary_evidence"]["evidence_complete"])

    async def test_openhands_bounded_worker_flow_blocks_without_command(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.operator_tests.shutil.which", return_value=None),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["openhands_bounded_worker"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "openhands_bounded_worker")
        self.assertEqual("blocked", flow["last_outcome"])
        self.assertEqual("configured", flow["status"])
        self.assertIn("missing_command:openhands", flow["details"]["blocking_reasons"])

    async def test_letta_memory_plane_flow_passes_when_command_is_available(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.operator_tests.shutil.which", side_effect=lambda command: f"/tmp/{command}" if command == "letta" else None),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["letta_memory_plane"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "letta_memory_plane")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertEqual("service_runtime", flow["details"]["wrapper_mode"])
        self.assertGreater(flow["details"]["namespace_count"], 0)

    async def test_agt_policy_plane_flow_uses_existing_governance_contracts(self) -> None:
        fake_redis = FakeRedis()
        with (
            patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.activity.log_event", AsyncMock()),
        ):
            snapshot = await run_operator_tests(flow_ids=["agt_policy_plane"], actor="test-suite")

        flow = next(flow for flow in snapshot["flows"] if flow["id"] == "agt_policy_plane")
        self.assertEqual("passed", flow["last_outcome"])
        self.assertEqual("live_partial", flow["status"])
        self.assertIn("approval_required", flow["details"]["approval_classes"])
        self.assertIn("command_decision_record", flow["details"]["contract_ids"])


if __name__ == "__main__":
    unittest.main()
