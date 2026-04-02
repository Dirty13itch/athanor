from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class GoalsDurableStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_goal_dual_writes_to_durable_store(self) -> None:
        from athanor_agents.goals import create_goal

        redis_client = AsyncMock()
        with (
            patch("athanor_agents.goals._get_redis", AsyncMock(return_value=redis_client)),
            patch("athanor_agents.goals.upsert_goal_record", AsyncMock(return_value=True)) as upsert_goal_record,
        ):
            goal = await create_goal("Keep media healthy", agent="media-agent", priority="high")

        redis_client.hset.assert_awaited_once()
        upsert_goal_record.assert_awaited_once()
        self.assertEqual(goal["id"], upsert_goal_record.await_args.args[0]["id"])
        self.assertEqual("media-agent", goal["agent"])

    async def test_list_goals_falls_back_to_durable_store(self) -> None:
        from athanor_agents.goals import list_goals

        durable_goals = [
            {
                "id": "goal-1",
                "text": "Keep media healthy",
                "agent": "media-agent",
                "priority": "high",
                "created_at": 1000.0,
                "active": True,
            }
        ]

        with (
            patch("athanor_agents.goals._get_redis", AsyncMock(side_effect=RuntimeError("redis unavailable"))),
            patch("athanor_agents.goals.list_goal_records", AsyncMock(return_value=durable_goals)) as list_goal_records,
        ):
            goals = await list_goals(agent="media-agent", active_only=True)

        self.assertEqual(durable_goals, goals)
        list_goal_records.assert_awaited_once_with(agent="media-agent", active_only=True)

    async def test_delete_goal_soft_deletes_durable_store(self) -> None:
        from athanor_agents.goals import delete_goal

        redis_client = AsyncMock()
        redis_client.hdel = AsyncMock(return_value=0)

        with (
            patch("athanor_agents.goals._get_redis", AsyncMock(return_value=redis_client)),
            patch("athanor_agents.goals.soft_delete_goal_record", AsyncMock(return_value=True)) as soft_delete_goal_record,
        ):
            removed = await delete_goal("goal-123")

        self.assertTrue(removed)
        soft_delete_goal_record.assert_awaited_once_with("goal-123")


if __name__ == "__main__":
    unittest.main()
