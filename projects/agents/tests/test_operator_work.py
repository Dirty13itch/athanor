from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents import operator_work


class OperatorWorkTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_todo_persists_durable_record(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_operator_todo_record",
            AsyncMock(return_value=True),
        ) as upsert_operator_todo_record:
            todo = await operator_work.create_todo(
                title="Review provider auth repair packet",
                category="ops",
                scope_type="global",
                scope_id="athanor",
                priority=4,
            )

        self.assertTrue(todo["id"].startswith("todo-"))
        self.assertEqual("Review provider auth repair packet", todo["title"])
        self.assertEqual("open", todo["status"])
        upsert_operator_todo_record.assert_awaited_once()
        stored = upsert_operator_todo_record.await_args.args[0]
        self.assertEqual(todo["id"], stored["id"])
        self.assertEqual(4, stored["priority"])

    async def test_transition_todo_updates_status(self) -> None:
        record = {
            "id": "todo-123",
            "title": "Follow up",
            "description": "",
            "category": "ops",
            "scope_type": "global",
            "scope_id": "athanor",
            "priority": 3,
            "status": "open",
            "energy_class": "focused",
            "origin": "operator",
            "created_by": "operator",
            "due_at": 0.0,
            "linked_goal_ids": [],
            "linked_inbox_ids": [],
            "metadata": {},
            "created_at": 1.0,
            "updated_at": 1.0,
            "completed_at": 0.0,
        }
        with (
            patch("athanor_agents.operator_work.fetch_operator_todo_record", AsyncMock(return_value=dict(record))),
            patch("athanor_agents.operator_work.upsert_operator_todo_record", AsyncMock(return_value=True)) as upsert_operator_todo_record,
        ):
            updated = await operator_work.transition_todo("todo-123", status="done", note="Handled")

        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual("done", updated["status"])
        self.assertGreater(updated["completed_at"], 0.0)
        self.assertEqual("Handled", updated["metadata"]["last_note"])
        upsert_operator_todo_record.assert_awaited_once()

    async def test_create_inbox_item_persists_durable_record(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_operator_inbox_record",
            AsyncMock(return_value=True),
        ) as upsert_operator_inbox_record:
            item = await operator_work.create_inbox_item(
                kind="approval_request",
                title="Approve repair pass",
                severity=3,
                source="system",
            )

        self.assertTrue(item["id"].startswith("inbox-"))
        self.assertEqual("new", item["status"])
        self.assertEqual(3, item["severity"])
        upsert_operator_inbox_record.assert_awaited_once()

    async def test_convert_inbox_item_creates_linked_todo_and_marks_inbox_converted(self) -> None:
        item = {
            "id": "inbox-123",
            "kind": "blocked_run",
            "severity": 2,
            "status": "new",
            "source": "system",
            "title": "Resolve blocked run",
            "description": "A run needs operator intervention.",
            "requires_decision": True,
            "decision_type": "approval",
            "related_run_id": "run-1",
            "related_task_id": "",
            "related_project_id": "",
            "related_domain_id": "media",
            "snooze_until": 0.0,
            "metadata": {},
            "created_at": 1.0,
            "updated_at": 1.0,
            "resolved_at": 0.0,
        }
        todo = {"id": "todo-777", "title": "Resolve blocked run"}
        with (
            patch("athanor_agents.operator_work.fetch_operator_inbox_record", AsyncMock(return_value=dict(item))),
            patch("athanor_agents.operator_work.create_todo", AsyncMock(return_value=todo)) as create_todo,
            patch("athanor_agents.operator_work.upsert_operator_inbox_record", AsyncMock(return_value=True)) as upsert_operator_inbox_record,
        ):
            payload = await operator_work.convert_inbox_item_to_todo("inbox-123", category="decision", priority=4)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("todo-777", payload["todo"]["id"])
        self.assertEqual("converted", payload["inbox"]["status"])
        self.assertEqual("todo-777", payload["inbox"]["metadata"]["converted_todo_id"])
        create_todo.assert_awaited_once()
        create_kwargs = create_todo.await_args.kwargs
        self.assertEqual(["inbox-123"], create_kwargs["linked_inbox_ids"])
        self.assertEqual("domain", create_kwargs["scope_type"])
        self.assertEqual("media", create_kwargs["scope_id"])
        upsert_operator_inbox_record.assert_awaited_once()

    async def test_create_idea_persists_durable_record(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_idea_record",
            AsyncMock(return_value=True),
        ) as upsert_idea_record:
            idea = await operator_work.create_idea(
                title="Foundry promotion cockpit",
                note="Track rollback evidence before promotion.",
                tags=["foundry"],
            )

        self.assertTrue(idea["id"].startswith("idea-"))
        self.assertEqual("seed", idea["status"])
        upsert_idea_record.assert_awaited_once()

    async def test_promote_idea_to_backlog_marks_idea_promoted(self) -> None:
        idea = {
            "id": "idea-1",
            "title": "Promote run ledger",
            "note": "Move this into active implementation work.",
            "tags": [],
            "source": "operator",
            "confidence": 0.8,
            "energy_class": "focused",
            "scope_guess": "project",
            "status": "candidate",
            "next_review_at": 0.0,
            "promoted_project_id": "",
            "metadata": {},
            "created_at": 1.0,
            "updated_at": 1.0,
        }
        backlog = {"id": "backlog-9", "title": "Promote run ledger"}
        with (
            patch("athanor_agents.operator_work.fetch_idea_record", AsyncMock(return_value=dict(idea))),
            patch("athanor_agents.operator_work.create_backlog_item", AsyncMock(return_value=backlog)) as create_backlog_item,
            patch("athanor_agents.operator_work.upsert_idea_record", AsyncMock(return_value=True)) as upsert_idea_record,
        ):
            payload = await operator_work.promote_idea("idea-1", target="backlog", owner_agent="coding-agent")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("promoted", payload["idea"]["status"])
        self.assertEqual("backlog-9", payload["idea"]["metadata"]["promoted_backlog_id"])
        create_backlog_item.assert_awaited_once()
        upsert_idea_record.assert_awaited_once()

    async def test_create_backlog_item_persists_durable_record(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_backlog_record",
            AsyncMock(return_value=True),
        ) as upsert_backlog_record:
            backlog = await operator_work.create_backlog_item(
                title="Finish durable run ledger",
                prompt="Extend the execution ledger.",
                owner_agent="coding-agent",
                work_class="migration",
                priority=5,
            )

        self.assertTrue(backlog["id"].startswith("backlog-"))
        self.assertEqual("captured", backlog["status"])
        upsert_backlog_record.assert_awaited_once()

    async def test_dispatch_backlog_item_submits_task_and_updates_status(self) -> None:
        backlog = {
            "id": "backlog-1",
            "title": "Finish durable run ledger",
            "prompt": "Extend the execution ledger.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "migration",
            "priority": 5,
            "status": "ready",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "metadata": {
                "latest_task_id": "task-old",
                "latest_run_id": "task-old",
                "last_dispatch_reason": "Dispatch old",
                "governor_reason": "Old governor reason",
                "governor_level": "C",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 1.0,
            "completed_at": 0.0,
        }
        submission = type(
            "Submission",
            (),
            {
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-1", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "B"})(),
            },
        )()
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            payload = await operator_work.dispatch_backlog_item("backlog-1", reason="Dispatch now")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("scheduled", payload["backlog"]["status"])
        submit_governed_task.assert_awaited_once()
        upsert_backlog_record.assert_awaited_once()
        submit_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertNotIn("latest_task_id", submit_metadata)
        self.assertNotIn("latest_run_id", submit_metadata)
        self.assertNotIn("last_dispatch_reason", submit_metadata)
        self.assertNotIn("governor_reason", submit_metadata)
        self.assertNotIn("governor_level", submit_metadata)
        self.assertEqual("task-1", payload["backlog"]["metadata"]["latest_task_id"])
        self.assertEqual("task-1", payload["backlog"]["metadata"]["latest_run_id"])

    async def test_dispatch_backlog_item_marks_governed_dispatch_records_autonomy_managed(self) -> None:
        backlog = {
            "id": "backlog-2",
            "title": "Capacity and Harvest Truth",
            "prompt": "Refresh scheduler-backed harvest truth.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
            "priority": 5,
            "status": "captured",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "metadata": {
                "materialization_source": "governed_dispatch_state",
                "claim_id": "ralph-claim-2",
                "task_class": "private_automation",
                "workload_class": "private_automation",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 1.0,
            "completed_at": 0.0,
        }
        submission = type(
            "Submission",
            (),
            {
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-2", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            payload = await operator_work.dispatch_backlog_item("backlog-2", reason="Dispatch governed work")

        self.assertIsNotNone(payload)
        assert payload is not None
        submit_governed_task.assert_awaited_once()
        submit_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertTrue(submit_metadata["_autonomy_managed"])
        self.assertEqual("pipeline", submit_metadata["_autonomy_source"])
        self.assertEqual("async_backlog_execution", submit_metadata["task_class"])
        self.assertEqual("coding_implementation", submit_metadata["workload_class"])

    async def test_dispatch_backlog_item_refreshes_claim_id_from_governed_dispatch_reason(self) -> None:
        backlog = {
            "id": "backlog-3",
            "title": "Dispatch and Work-Economy Closure",
            "prompt": "Advance the governed dispatch claim.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
            "priority": 5,
            "status": "captured",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "metadata": {
                "materialization_source": "governed_dispatch_state",
                "claim_id": "ralph-claim-old",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 1.0,
            "completed_at": 0.0,
        }
        submission = type(
            "Submission",
            (),
            {
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-3", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            payload = await operator_work.dispatch_backlog_item(
                "backlog-3",
                reason="Auto-dispatched governed dispatch claim ralph-claim-new",
            )

        self.assertIsNotNone(payload)
        assert payload is not None
        submit_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertEqual("ralph-claim-new", submit_metadata["claim_id"])
        self.assertEqual("ralph-claim-new", payload["backlog"]["metadata"]["claim_id"])

    async def test_list_backlog_normalizes_all_status_to_unfiltered_query(self) -> None:
        with patch(
            "athanor_agents.operator_work.list_backlog_records",
            AsyncMock(return_value=[{"id": "backlog-1"}]),
        ) as list_backlog_records:
            backlog = await operator_work.list_backlog(status="all", owner_agent="coding-agent", limit=12)

        self.assertEqual([{"id": "backlog-1"}], backlog)
        list_backlog_records.assert_awaited_once_with(status="", owner_agent="coding-agent", limit=12)

    async def test_list_runs_enriches_with_attempts_and_approvals(self) -> None:
        run = {
            "id": "run-1",
            "task_id": "task-1",
            "backlog_id": "backlog-1",
            "agent_id": "coding-agent",
            "workload_class": "migration",
            "provider_lane": "athanor_local",
            "runtime_lane": "coding-agent",
            "policy_class": "private",
            "status": "waiting_approval",
            "summary": "Waiting",
            "artifact_refs": [],
            "metadata": {},
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        attempt = {"id": "attempt-1", "run_id": "run-1", "status": "waiting_approval"}
        approval = {"id": "approval-1", "related_run_id": "run-1", "status": "pending"}
        with (
            patch("athanor_agents.operator_work.list_execution_run_records", AsyncMock(return_value=[run])),
            patch(
                "athanor_agents.operator_work.list_run_attempt_records_for_runs",
                AsyncMock(return_value={"run-1": [attempt]}),
            ),
            patch(
                "athanor_agents.operator_work.list_run_step_records_for_runs",
                AsyncMock(return_value={"run-1": [{"id": "step-1"}]}),
            ),
            patch(
                "athanor_agents.operator_work.list_approval_request_records_for_runs",
                AsyncMock(return_value={"run-1": [approval]}),
            ),
        ):
            runs = await operator_work.list_runs(status="waiting_approval")

        self.assertEqual(1, len(runs))
        self.assertTrue(runs[0]["approval_pending"])
        self.assertEqual(attempt["id"], runs[0]["latest_attempt"]["id"])

    async def test_list_runs_returns_empty_without_batch_queries_when_no_runs(self) -> None:
        with (
            patch("athanor_agents.operator_work.list_execution_run_records", AsyncMock(return_value=[])),
            patch("athanor_agents.operator_work.list_run_attempt_records_for_runs", AsyncMock()) as attempts,
            patch("athanor_agents.operator_work.list_run_step_records_for_runs", AsyncMock()) as steps,
            patch("athanor_agents.operator_work.list_approval_request_records_for_runs", AsyncMock()) as approvals,
        ):
            runs = await operator_work.list_runs()

        self.assertEqual([], runs)
        attempts.assert_not_awaited()
        steps.assert_not_awaited()
        approvals.assert_not_awaited()

    async def test_list_approvals_enriches_with_related_task_snapshot(self) -> None:
        approval = {
            "id": "approval-1",
            "related_task_id": "task-1",
            "status": "pending",
            "reason": "Needs approval",
        }
        task = {
            "id": "task-1",
            "agent": "coding-agent",
            "prompt": "Finish foundry migration",
            "priority": "high",
            "status": "pending_approval",
            "created_at": 5.0,
        }
        with (
            patch("athanor_agents.operator_work.list_approval_request_records", AsyncMock(return_value=[approval])),
            patch("athanor_agents.operator_work.fetch_task_snapshot", AsyncMock(return_value=task)),
        ):
            approvals = await operator_work.list_approvals(status="pending")

        self.assertEqual(1, len(approvals))
        self.assertEqual("Finish foundry migration", approvals[0]["task_prompt"])
        self.assertEqual("coding-agent", approvals[0]["task_agent_id"])
        self.assertEqual("high", approvals[0]["task_priority"])


if __name__ == "__main__":
    unittest.main()
