from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from athanor_agents import owner_model


class _FakePrometheusResponse:
    status_code = 200

    def json(self) -> dict:
        return {"data": {"result": [{"value": [0, "15"]}]}}


class _FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return _FakePrometheusResponse()


class OwnerModelCapacityTests(unittest.IsolatedAsyncioTestCase):
    def test_load_capacity_telemetry_summary_uses_existing_candidate_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            truth_dir = Path(temp_dir)
            (truth_dir / "capacity-telemetry.json").write_text(
                json.dumps({"capacity_summary": {"scheduler_slot_count": 5}}),
                encoding="utf-8",
            )
            with patch(
                "athanor_agents.owner_model._candidate_truth_inventory_dirs",
                return_value=[truth_dir],
            ):
                summary = owner_model._load_capacity_telemetry_summary()

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(5, summary["scheduler_slot_count"])

    async def test_gather_capacity_uses_complete_active_task_read(self) -> None:
        with (
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"by_status": {"pending": 80}}),
            ),
            patch(
                "athanor_agents.tasks.list_tasks",
                AsyncMock(
                    return_value=[
                        {"agent": "general-assistant", "status": "pending"},
                        {"agent": "research-agent", "status": "running"},
                    ]
                ),
            ) as list_tasks,
            patch("athanor_agents.owner_model.httpx.AsyncClient", return_value=_FakeAsyncClient()),
        ):
            capacity = await owner_model._gather_capacity()

        list_tasks.assert_awaited_once_with(statuses=["pending", "running"], limit=None)
        self.assertEqual(80, capacity["queue_depth"])
        self.assertNotIn("general-assistant", capacity["agents_idle"])
        self.assertNotIn("research-agent", capacity["agents_idle"])
        self.assertIn("coding-agent", capacity["agents_idle"])

    async def test_gather_capacity_exposes_slot_aware_capacity_truth(self) -> None:
        with (
            patch(
                "athanor_agents.owner_model._load_capacity_telemetry_summary",
                return_value={
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 5,
                    "harvestable_scheduler_slot_count": 2,
                    "scheduler_queue_depth": 0,
                    "scheduler_backed_gpu_count": 8,
                    "harvestable_gpu_count": 5,
                },
            ),
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"by_status": {"pending": 3}}),
            ),
            patch("athanor_agents.tasks.list_tasks", AsyncMock(return_value=[])),
            patch("athanor_agents.owner_model.httpx.AsyncClient", return_value=_FakeAsyncClient()),
        ):
            capacity = await owner_model._gather_capacity()

        self.assertEqual("scheduler_projection_backed", capacity["sample_posture"])
        self.assertEqual(5, capacity["scheduler_slot_count"])
        self.assertEqual(2, capacity["harvestable_scheduler_slot_count"])
        self.assertTrue(capacity["idle_harvest_slots_open"])
        self.assertEqual(62, capacity["gpu_idle_pct"])
