from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents import server  # noqa: E402


class ServerHealthContractTests(unittest.TestCase):
    def test_health_livez_stays_healthy_without_dependency_probes(self) -> None:
        with patch("athanor_agents.server.list_agents", return_value=["general-assistant", "coding-agent"]):
            payload = asyncio.run(server.health_livez())

        self.assertEqual("agent-server", payload["service"])
        self.assertEqual("healthy", payload["status"])
        self.assertEqual(2, payload["agent_count"])
        self.assertEqual("liveness_only", payload["mode"])
        self.assertTrue(payload["launch_ready"])

    def test_health_livez_reports_degraded_when_agent_roster_is_empty(self) -> None:
        with patch("athanor_agents.server.list_agents", return_value=[]):
            payload = asyncio.run(server.health_livez())

        self.assertEqual("degraded", payload["status"])
        self.assertEqual(0, payload["agent_count"])

    def test_health_uses_stale_tolerant_bootstrap_snapshot(self) -> None:
        redis_dep = {"id": "redis", "status": "healthy", "required": True}
        fake_bootstrap = {"mode": "ready"}
        fake_governance = {"launch_blockers": [], "issues": []}
        fake_persistence = {
            "mode": "postgres",
            "durable": True,
            "configured": True,
            "driver": "postgres",
            "reason": None,
        }
        fake_durable = {
            "mode": "ready",
            "configured": True,
            "available": True,
            "schema_ready": True,
            "reason": None,
        }

        class _FakeResponse:
            def __init__(self, latency_ms: int = 5) -> None:
                self.elapsed = type("Elapsed", (), {"total_seconds": lambda self: latency_ms / 1000})()

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None):
                return _FakeResponse()

        with patch("athanor_agents.server.list_agents", return_value=["general-assistant"]):
            with patch("athanor_agents.server.get_checkpointer_status", return_value=fake_persistence):
                with patch("athanor_agents.server.get_durable_state_status", return_value=fake_durable):
                    with patch("athanor_agents.server._probe_redis_dependency", new=AsyncMock(return_value=redis_dep)):
                        with patch("athanor_agents.governance_state.build_governance_snapshot", new=AsyncMock(return_value=fake_governance)):
                            with patch("athanor_agents.server.build_bootstrap_runtime_snapshot", new=AsyncMock(return_value=fake_bootstrap)) as bootstrap:
                                with patch("httpx.AsyncClient", return_value=_FakeClient()):
                                    payload = asyncio.run(server.health())

        bootstrap.assert_awaited_once_with(include_snapshot_write=False, allow_stale=True)
        self.assertEqual(fake_bootstrap, payload["bootstrap"])

    def test_load_governor_runtime_continues_when_governor_load_fails(self) -> None:
        class _FakeGovernor:
            async def load(self) -> None:
                raise RuntimeError("redis unavailable")

        with patch("athanor_agents.governor.Governor.get", return_value=_FakeGovernor()):
            with self.assertLogs("athanor_agents.server", level="WARNING") as logs:
                result = asyncio.run(server._load_governor_runtime())

        self.assertFalse(result)
        self.assertTrue(any("continuing in degraded mode" in entry for entry in logs.output))

    def test_probe_redis_dependency_uses_real_ping(self) -> None:
        class _FakeRedisClient:
            def ping(self) -> None:
                return None

        with patch("redis.from_url", return_value=_FakeRedisClient()) as from_url:
            result = asyncio.run(server._probe_redis_dependency("2026-04-01T00:00:00Z"))

        self.assertEqual("redis", result["id"])
        self.assertEqual("healthy", result["status"])
        self.assertTrue(result["required"])
        from_url.assert_called_once()

    def test_probe_redis_dependency_reports_ping_failure(self) -> None:
        with patch("redis.from_url", side_effect=RuntimeError("MISCONF")):
            result = asyncio.run(server._probe_redis_dependency("2026-04-01T00:00:00Z"))

        self.assertEqual("redis", result["id"])
        self.assertEqual("down", result["status"])
        self.assertIn("MISCONF", result["detail"])

    def test_health_summary_marks_memory_fallback_as_launch_blocker(self) -> None:
        deps = [
            {"id": "redis", "status": "healthy"},
            {"id": "qdrant", "status": "healthy"},
            {"id": "litellm", "status": "healthy"},
            {"id": "worker", "status": "down"},
        ]
        persistence = {
            "mode": "memory_fallback",
            "durable": False,
            "configured": False,
            "driver": "langgraph.checkpoint.memory.InMemorySaver",
            "reason": "ATHANOR_POSTGRES_URL not configured",
        }
        durable_state = {
            "mode": "disabled",
            "configured": False,
            "available": False,
            "schema_ready": False,
            "reason": "ATHANOR_POSTGRES_URL not configured",
        }

        summary = server._build_health_summary(
            deps=deps,
            active_agents=["general-assistant", "media-agent"],
            persistence=persistence,
            durable_state=durable_state,
        )

        self.assertEqual("healthy", summary["status"])
        self.assertFalse(summary["launch_ready"])
        self.assertEqual(["persistence:memory_fallback"], summary["launch_blockers"])
        self.assertEqual(
            ["worker", "persistence:memory_fallback"],
            summary["issues"],
        )
        self.assertEqual(persistence, summary["persistence"])
        self.assertEqual(durable_state, summary["durable_state"])
        self.assertEqual("ATHANOR_POSTGRES_URL not configured", summary["last_error"])

    def test_health_summary_marks_core_dependency_outage_as_degraded(self) -> None:
        deps = [
            {"id": "redis", "status": "down"},
            {"id": "qdrant", "status": "healthy"},
            {"id": "litellm", "status": "healthy"},
        ]
        persistence = {
            "mode": "postgres",
            "durable": True,
            "configured": True,
            "driver": "langgraph.checkpoint.postgres.PostgresSaver",
            "reason": None,
        }
        durable_state = {
            "mode": "ready",
            "configured": True,
            "available": True,
            "schema_ready": True,
            "reason": None,
        }

        summary = server._build_health_summary(
            deps=deps,
            active_agents=["general-assistant"],
            persistence=persistence,
            durable_state=durable_state,
        )

        self.assertEqual("degraded", summary["status"])
        self.assertFalse(summary["launch_ready"])
        self.assertEqual(["dependency:redis"], summary["launch_blockers"])
        self.assertEqual(["redis"], summary["issues"])
        self.assertEqual("redis", summary["last_error"])

    def test_health_summary_marks_durable_state_schema_failure_as_launch_blocker(self) -> None:
        deps = [
            {"id": "redis", "status": "healthy"},
            {"id": "qdrant", "status": "healthy"},
            {"id": "litellm", "status": "healthy"},
        ]
        persistence = {
            "mode": "postgres",
            "durable": True,
            "configured": True,
            "driver": "langgraph.checkpoint.postgres.PostgresSaver",
            "reason": None,
        }
        durable_state = {
            "mode": "schema_error",
            "configured": True,
            "available": True,
            "schema_ready": False,
            "reason": "Schema bootstrap failed: permission denied",
        }

        summary = server._build_health_summary(
            deps=deps,
            active_agents=["general-assistant"],
            persistence=persistence,
            durable_state=durable_state,
        )

        self.assertEqual("healthy", summary["status"])
        self.assertFalse(summary["launch_ready"])
        self.assertEqual(["durable_state:schema_error"], summary["launch_blockers"])
        self.assertEqual(["durable_state:schema_error"], summary["issues"])
        self.assertEqual("Schema bootstrap failed: permission denied", summary["last_error"])

    def test_health_summary_merges_governance_launch_blockers(self) -> None:
        deps = [
            {"id": "redis", "status": "healthy"},
            {"id": "qdrant", "status": "healthy"},
            {"id": "litellm", "status": "healthy"},
        ]
        persistence = {
            "mode": "postgres",
            "durable": True,
            "configured": True,
            "driver": "langgraph.checkpoint.postgres.PostgresSaver",
            "reason": None,
        }
        durable_state = {
            "mode": "ready",
            "configured": True,
            "available": True,
            "schema_ready": True,
            "reason": None,
        }
        governance = {
            "launch_blockers": [
                "autonomy:next_phase:vault_provider_auth_repair",
                "runbook:degraded-mode",
            ],
            "issues": [
                "autonomy:next_phase:vault_provider_auth_repair",
                "runbook:degraded-mode",
            ],
            "current_phase_id": "software_core_phase_1",
        }

        summary = server._build_health_summary(
            deps=deps,
            active_agents=["general-assistant"],
            persistence=persistence,
            durable_state=durable_state,
            governance=governance,
        )

        self.assertEqual("healthy", summary["status"])
        self.assertFalse(summary["launch_ready"])
        self.assertEqual(
            [
                "autonomy:next_phase:vault_provider_auth_repair",
                "runbook:degraded-mode",
            ],
            summary["launch_blockers"],
        )
        self.assertEqual(
            [
                "autonomy:next_phase:vault_provider_auth_repair",
                "runbook:degraded-mode",
            ],
            summary["issues"],
        )
        self.assertEqual(governance, summary["governance"])
        self.assertEqual("autonomy:next_phase:vault_provider_auth_repair", summary["last_error"])


if __name__ == "__main__":
    unittest.main()
