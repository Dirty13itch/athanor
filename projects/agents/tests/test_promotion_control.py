import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.promotion_control import (
    build_promotion_controls_snapshot,
    stage_promotion_candidate,
    transition_promotion_candidate,
)


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

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


class PromotionControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_stage_advance_and_rollback_candidate(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.promotion_control._get_redis", AsyncMock(return_value=fake_redis)):
            staged = await stage_promotion_candidate(
                role_id="frontier_supervisor",
                candidate="Gemini",
                target_tier="canary",
                actor="test-suite",
                reason="fixture promotion",
            )
            self.assertEqual("staged", staged["status"])
            self.assertEqual("offline_eval", staged["current_tier"])

            advanced = await transition_promotion_candidate(
                staged["id"],
                action="advance",
                actor="test-suite",
            )
            self.assertIsNotNone(advanced)
            self.assertEqual("shadow", advanced["current_tier"])
            self.assertEqual("active", advanced["status"])

            rolled_back = await transition_promotion_candidate(
                staged["id"],
                action="rollback",
                actor="test-suite",
            )
            self.assertIsNotNone(rolled_back)
            self.assertEqual("rolled_back", rolled_back["status"])
            self.assertEqual("Claude", rolled_back["rollback_target"])

    async def test_promotion_controls_snapshot_becomes_live_partial_once_records_exist(self) -> None:
        fake_redis = FakeRedis()
        with patch("athanor_agents.promotion_control._get_redis", AsyncMock(return_value=fake_redis)):
            await stage_promotion_candidate(
                role_id="coding_worker",
                candidate="coder",
                target_tier="sandbox",
                actor="test-suite",
            )
            snapshot = await build_promotion_controls_snapshot(limit=10)

        self.assertEqual("live_partial", snapshot["status"])
        self.assertEqual(1, len(snapshot["active_promotions"]))
        self.assertEqual("coding_worker", snapshot["active_promotions"][0]["role_id"])


if __name__ == "__main__":
    unittest.main()
