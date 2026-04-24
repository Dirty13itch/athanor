from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from athanor_agents.research_jobs import JobStatus, ResearchJob, execute_job, materialize_due_jobs


class ResearchJobsQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_job_materializes_backlog_queue_work(self) -> None:
        job = ResearchJob(
            id="rj-1234",
            topic="Provider drift remediation",
            description="Collect fresh external evidence and summarize the delta.",
            schedule_hours=6,
        )
        redis = AsyncMock()

        with (
            patch("athanor_agents.research_jobs.get_job", AsyncMock(return_value=job)),
            patch("athanor_agents.research_jobs._get_redis", AsyncMock(return_value=redis)),
            patch(
                "athanor_agents.operator_work.materialize_research_schedule",
                AsyncMock(
                    return_value={
                        "status": "created",
                        "backlog_id": "backlog-research-1",
                        "backlog": {"id": "backlog-research-1"},
                        "already_materialized": False,
                    }
                ),
            ) as materialize_research_schedule,
        ):
            result = await execute_job("rj-1234")

        self.assertEqual("queued", result["status"])
        self.assertEqual("backlog-research-1", result["backlog_id"])
        self.assertEqual("created", result["materialization_status"])
        materialize_research_schedule.assert_awaited_once()
        stored_payload = json.loads(redis.hset.await_args_list[-1].args[2])
        self.assertEqual("queued", stored_payload["status"])
        self.assertEqual("backlog-research-1", stored_payload["last_backlog_id"])

    async def test_materialize_due_jobs_reports_created_and_refreshed_counts(self) -> None:
        due_job = ResearchJob(
            id="rj-due",
            topic="Runtime packet drift",
            schedule_hours=4,
            last_run=0.0,
        )

        with (
            patch("athanor_agents.research_jobs.list_jobs", AsyncMock(return_value=[due_job.to_dict()])),
            patch(
                "athanor_agents.research_jobs.execute_job",
                AsyncMock(
                    return_value={
                        "job_id": "rj-due",
                        "status": "queued",
                        "backlog_id": "backlog-rj-due",
                        "materialization_status": "refreshed",
                        "already_materialized": True,
                    }
                ),
            ) as execute_job_mock,
        ):
            summary = await materialize_due_jobs()

        self.assertEqual(1, summary["triggered"])
        self.assertEqual(0, summary["created"])
        self.assertEqual(1, summary["refreshed"])
        self.assertEqual(["backlog-rj-due"], summary["backlog_ids"])
        execute_job_mock.assert_awaited_once_with("rj-due", autonomy_managed=False)

    def test_research_job_source_no_longer_direct_submits_product_work(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src" / "athanor_agents" / "research_jobs.py").read_text(encoding="utf-8")
        self.assertNotIn("submit_governed_task(", source)
