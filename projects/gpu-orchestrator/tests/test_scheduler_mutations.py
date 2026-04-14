import asyncio
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import gpu_orchestrator.main as orchestrator


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hset(self, key: str, mapping: dict[str, str]) -> None:
        bucket = self.hashes.setdefault(key, {})
        bucket.update(mapping)


class SchedulerMutationContractTest(unittest.TestCase):
    def test_request_payload_requires_zone_or_model_alias(self) -> None:
        with self.assertRaises(ValidationError):
            orchestrator.SchedulerRequestPayload(
                request_id="req-1",
                request_surface="direct_cli",
                priority=1,
                request_kind="interactive",
            )

    def test_scheduler_routes_are_registered(self) -> None:
        route_index = {
            route.path: sorted(route.methods or [])
            for route in orchestrator.app.routes
            if getattr(route, "path", "").startswith("/scheduler/")
        }

        self.assertIn("/scheduler/state", route_index)
        self.assertIn("/scheduler/request", route_index)
        self.assertIn("/scheduler/preload", route_index)
        self.assertIn("/scheduler/release", route_index)
        self.assertIn("GET", route_index["/scheduler/state"])
        self.assertIn("POST", route_index["/scheduler/request"])
        self.assertIn("POST", route_index["/scheduler/preload"])
        self.assertIn("POST", route_index["/scheduler/release"])

    def test_scheduler_write_routes_reject_get_requests(self) -> None:
        client = TestClient(orchestrator.app)

        for path in (
            "/scheduler/request",
            "/scheduler/preload",
            "/scheduler/release",
        ):
            with self.subTest(path=path):
                response = client.get(path)

                self.assertEqual(response.status_code, 405)
                self.assertIn("POST", response.headers.get("allow", ""))

    def test_request_accepts_and_replays_idempotently(self) -> None:
        fake_redis = FakeRedis()

        async def fake_get_redis() -> FakeRedis:
            return fake_redis

        payload = orchestrator.SchedulerRequestPayload(
            request_id="req-vision-1",
            request_surface="goose_wrapped",
            zone="vision",
            priority=1,
            request_kind="interactive",
        )

        with patch("gpu_orchestrator.main.get_redis", new=fake_get_redis), patch.object(
            orchestrator.settings, "scheduler_mutation_enabled", True
        ):
            first = asyncio.run(orchestrator.scheduler_request(payload))
            second = asyncio.run(orchestrator.scheduler_request(payload))
            state = asyncio.run(orchestrator.scheduler_state())

        self.assertTrue(first["accepted"])
        self.assertEqual(first["scheduler_state"], "queued")
        self.assertEqual(first["queue_depth"], 1)
        self.assertTrue(second["accepted"])
        self.assertEqual(second["decision_reason"], "request_idempotent_replay")
        self.assertTrue(state["scheduler_enabled"])
        self.assertEqual(state["queue_depth"], 1)
        self.assertEqual(len(state["requests"]), 1)

    def test_shared_gpu_zone_is_rejected(self) -> None:
        fake_redis = FakeRedis()

        async def fake_get_redis() -> FakeRedis:
            return fake_redis

        payload = orchestrator.SchedulerRequestPayload(
            request_id="req-dev-shared-1",
            request_surface="litellm_routed",
            zone="embedding",
            priority=2,
            request_kind="background",
        )

        with patch("gpu_orchestrator.main.get_redis", new=fake_get_redis), patch.object(
            orchestrator.settings, "scheduler_mutation_enabled", True
        ):
            response = asyncio.run(orchestrator.scheduler_request(payload))

        self.assertEqual(response.status_code, 409)
        body = json.loads(response.body)
        self.assertFalse(body["accepted"])
        self.assertEqual(body["decision_reason"], "shared_gpu_multiple_zones")

    def test_preload_and_release_are_idempotent(self) -> None:
        fake_redis = FakeRedis()

        async def fake_get_redis() -> FakeRedis:
            return fake_redis

        preload_payload = orchestrator.SchedulerPreloadPayload(
            request_id="preload-vision-1",
            zone="vision",
            model_alias="workshop-vision",
            reason="warmup-before-batch",
        )
        release_payload = orchestrator.SchedulerReleasePayload(
            request_id="preload-vision-1",
            zone="vision",
            reason="batch-finished",
        )

        with patch("gpu_orchestrator.main.get_redis", new=fake_get_redis), patch.object(
            orchestrator.settings, "scheduler_mutation_enabled", True
        ):
            preload = asyncio.run(orchestrator.scheduler_preload(preload_payload))
            first_release = asyncio.run(orchestrator.scheduler_release(release_payload))
            second_release = asyncio.run(orchestrator.scheduler_release(release_payload))

        self.assertTrue(preload["accepted"])
        self.assertEqual(preload["scheduler_state"], "preloading")
        self.assertEqual(preload["preload_state"], "queued")
        self.assertTrue(first_release["released"])
        self.assertEqual(first_release["scheduler_state"], "released")
        self.assertEqual(first_release["queue_depth"], 0)
        self.assertTrue(second_release["released"])
        self.assertEqual(second_release["decision_reason"], "already_released")

    def test_always_on_zone_wakes_when_runtime_is_sleeping(self) -> None:
        zone = copy.deepcopy(orchestrator.ZONES["embedding"])
        zone.state = orchestrator.ZoneState.SLEEPING
        zone.last_request_at = 100.0

        with patch(
            "gpu_orchestrator.main.check_vllm_sleeping",
            new=AsyncMock(return_value=orchestrator.SleepState.SLEEPING),
        ), patch(
            "gpu_orchestrator.main.wake_vllm",
            new=AsyncMock(return_value=True),
        ) as wake_mock, patch(
            "gpu_orchestrator.main.save_zone_state",
            new=AsyncMock(),
        ) as save_mock:
            changed = asyncio.run(orchestrator.apply_zone_sleep_policy(zone, now=500.0))

        self.assertTrue(changed)
        self.assertEqual(zone.state, orchestrator.ZoneState.ACTIVE)
        self.assertEqual(zone.last_request_at, 500.0)
        wake_mock.assert_awaited_once_with(zone.vllm_url)
        save_mock.assert_awaited_once_with(zone)

    def test_always_on_zone_is_not_auto_slept_when_idle(self) -> None:
        zone = copy.deepcopy(orchestrator.ZONES["embedding"])
        zone.state = orchestrator.ZoneState.ACTIVE
        zone.last_request_at = 0.0

        with patch(
            "gpu_orchestrator.main.check_vllm_sleeping",
            new=AsyncMock(return_value=orchestrator.SleepState.AWAKE),
        ), patch(
            "gpu_orchestrator.main.sleep_vllm",
            new=AsyncMock(return_value=True),
        ) as sleep_mock, patch(
            "gpu_orchestrator.main.save_zone_state",
            new=AsyncMock(),
        ) as save_mock:
            changed = asyncio.run(orchestrator.apply_zone_sleep_policy(zone, now=5000.0))

        self.assertFalse(changed)
        self.assertEqual(zone.state, orchestrator.ZoneState.ACTIVE)
        sleep_mock.assert_not_awaited()
        save_mock.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
