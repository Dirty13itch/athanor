from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.project_tracker import ProjectState, create_milestone


class _FakeRedis:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, str]] = []

    async def hset(self, key: str, field: str, value: str) -> None:
        self.writes.append((key, field, value))


class ProjectTrackerTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_milestone_accepts_named_acceptance_fields(self) -> None:
        fake_redis = _FakeRedis()
        empty_state = ProjectState(project_id="core")

        with (
            patch("athanor_agents.project_tracker._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.project_tracker.get_project_state", AsyncMock(return_value=empty_state)),
            patch("athanor_agents.project_tracker._save_project_state", AsyncMock()),
        ):
            milestone = await create_milestone(
                project_id="core",
                title="Close routing drift",
                description="Align contracts",
                acceptance_criteria=["green tests"],
                assigned_agents=["coding-agent"],
            )

        self.assertEqual(["green tests"], milestone.acceptance_criteria)
        self.assertEqual(["coding-agent"], milestone.assigned_agents)
        self.assertEqual("active", milestone.status)
        self.assertTrue(fake_redis.writes)

    async def test_create_milestone_keeps_legacy_argument_names(self) -> None:
        fake_redis = _FakeRedis()
        empty_state = ProjectState(project_id="core")

        with (
            patch("athanor_agents.project_tracker._get_redis", AsyncMock(return_value=fake_redis)),
            patch("athanor_agents.project_tracker.get_project_state", AsyncMock(return_value=empty_state)),
            patch("athanor_agents.project_tracker._save_project_state", AsyncMock()),
        ):
            milestone = await create_milestone(
                project_id="core",
                title="Close routing drift",
                description="Align contracts",
                criteria=["green tests"],
                agents=["coding-agent"],
            )

        self.assertEqual(["green tests"], milestone.acceptance_criteria)
        self.assertEqual(["coding-agent"], milestone.assigned_agents)
        self.assertEqual("active", milestone.status)
        self.assertTrue(fake_redis.writes)
