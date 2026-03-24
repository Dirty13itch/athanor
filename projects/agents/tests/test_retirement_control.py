import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.retirement_control import (
    build_retirement_controls_snapshot,
    stage_retirement_candidate,
    transition_retirement_candidate,
)


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}

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


class RetirementControlTests(unittest.TestCase):
    def test_retirement_controls_stage_advance_and_rollback(self) -> None:
        fake_redis = FakeRedis()

        async def scenario() -> tuple[dict, dict]:
            with patch(
                "athanor_agents.retirement_control._get_redis",
                AsyncMock(return_value=fake_redis),
            ):
                staged = await stage_retirement_candidate(
                    asset_class="models",
                    asset_id="frontier_supervisor:Claude",
                    label="Frontier supervisor champion Claude",
                    actor="test-suite",
                    reason="Rehearse governed retirement.",
                )
                retirement_id = staged["id"]

                advanced_once = await transition_retirement_candidate(
                    retirement_id,
                    action="advance",
                    actor="test-suite",
                )
                self.assertIsNotNone(advanced_once)
                self.assertEqual("deprecated", advanced_once["current_stage"])
                self.assertEqual("active", advanced_once["status"])

                advanced_twice = await transition_retirement_candidate(
                    retirement_id,
                    action="advance",
                    actor="test-suite",
                )
                self.assertIsNotNone(advanced_twice)
                self.assertEqual("retired_reference_only", advanced_twice["current_stage"])
                self.assertEqual("completed", advanced_twice["status"])

                rolled_back = await transition_retirement_candidate(
                    retirement_id,
                    action="rollback",
                    actor="test-suite",
                )
                self.assertIsNotNone(rolled_back)
                self.assertEqual("active", rolled_back["current_stage"])
                self.assertEqual("rolled_back", rolled_back["status"])

                snapshot = await build_retirement_controls_snapshot(limit=12)
                return staged, snapshot

        staged, snapshot = asyncio.run(scenario())

        self.assertEqual("live_partial", snapshot["status"])
        self.assertEqual(["active", "deprecated", "retired_reference_only"], snapshot["stages"])
        self.assertGreaterEqual(len(snapshot["recent_retirements"]), 1)
        self.assertGreaterEqual(len(snapshot["recent_events"]), 4)
        self.assertEqual(staged["id"], snapshot["recent_retirements"][0]["id"])
        self.assertIn("models", snapshot["asset_classes"])


if __name__ == "__main__":
    unittest.main()
