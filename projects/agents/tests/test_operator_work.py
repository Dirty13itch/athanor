from __future__ import annotations

import sys
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
                family="builder",
                project_id="kindred",
                source_type="operator_request",
                source_ref="request-1",
                routing_class="private_but_cloud_allowed",
                verification_contract="bounded_change_verification",
                closure_rule="verified_result_required",
                materialization_source="operator_request",
                materialization_reason="manual backlog capture",
                recurrence_program_id="program-1",
                value_class="operator_value",
                deliverable_kind="code_patch",
                deliverable_refs=["reports/proof/operator-value.json"],
                beneficiary_surface="athanor_core",
                acceptance_mode="hybrid",
            )

        self.assertTrue(backlog["id"].startswith("backlog-"))
        self.assertEqual("captured", backlog["status"])
        self.assertEqual("builder", backlog["family"])
        self.assertEqual("kindred", backlog["project_id"])
        self.assertEqual("operator_request", backlog["source_type"])
        self.assertEqual("request-1", backlog["source_ref"])
        self.assertEqual("private_but_cloud_allowed", backlog["routing_class"])
        self.assertEqual("bounded_change_verification", backlog["verification_contract"])
        self.assertEqual("verified_result_required", backlog["closure_rule"])
        self.assertEqual("operator_request", backlog["materialization_source"])
        self.assertEqual("manual backlog capture", backlog["materialization_reason"])
        self.assertEqual("program-1", backlog["recurrence_program_id"])
        self.assertEqual("operator_value", backlog["value_class"])
        self.assertEqual("code_patch", backlog["deliverable_kind"])
        self.assertEqual(["reports/proof/operator-value.json"], backlog["deliverable_refs"])
        self.assertEqual("athanor_core", backlog["beneficiary_surface"])
        self.assertEqual("hybrid", backlog["acceptance_mode"])
        self.assertEqual("", backlog["result_id"])
        self.assertEqual("", backlog["review_id"])
        upsert_backlog_record.assert_awaited_once()
        stored = upsert_backlog_record.await_args.args[0]
        self.assertEqual("builder", stored["family"])
        self.assertEqual("kindred", stored["project_id"])
        self.assertEqual("operator_request", stored["metadata"]["materialization_source"])
        self.assertEqual("request-1", stored["metadata"]["source_ref"])
        self.assertEqual("operator_value", stored["metadata"]["value_class"])
        self.assertEqual("code_patch", stored["metadata"]["deliverable_kind"])

    async def test_transition_backlog_item_requires_closure_evidence(self) -> None:
        record = {
            "id": "backlog-closure",
            "title": "Finish durable run ledger",
            "prompt": "Extend the execution ledger.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "kindred",
            "work_class": "migration",
            "priority": 5,
            "status": "running",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "builder",
            "project_id": "kindred",
            "source_type": "operator_request",
            "source_ref": "request-1",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
            "materialization_source": "operator_request",
            "materialization_reason": "manual backlog capture",
            "recurrence_program_id": "",
            "result_id": "",
            "review_id": "",
            "metadata": {
                "failure": "old failure",
                "failure_detail": "old failure detail",
                "blocking_reason": "verification_evidence_missing",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 2.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        with patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(record))):
            with self.assertRaisesRegex(ValueError, "result evidence"):
                await operator_work.transition_backlog_item("backlog-closure", status="completed")
            with self.assertRaisesRegex(ValueError, "review evidence"):
                await operator_work.transition_backlog_item("backlog-closure", status="waiting_approval")
            with self.assertRaisesRegex(ValueError, "blocking_reason"):
                await operator_work.transition_backlog_item("backlog-closure", status="blocked")
            with self.assertRaisesRegex(ValueError, "failure detail"):
                await operator_work.transition_backlog_item("backlog-closure", status="failed")

    async def test_sync_backlog_item_from_task_links_review_and_result_evidence(self) -> None:
        backlog = {
            "id": "backlog-sync",
            "title": "Finish durable run ledger",
            "prompt": "Extend the execution ledger.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "kindred",
            "work_class": "migration",
            "priority": 5,
            "status": "scheduled",
            "approval_mode": "operator",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "builder",
            "project_id": "kindred",
            "source_type": "operator_request",
            "source_ref": "request-1",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
            "materialization_source": "operator_request",
            "materialization_reason": "manual backlog capture",
            "recurrence_program_id": "",
            "result_id": "",
            "review_id": "",
            "metadata": {},
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 2.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        pending_approval_task = {
            "id": "task-1",
            "status": "pending_approval",
            "error": "",
            "result": "",
            "created_at": 1.0,
            "updated_at": 3.0,
            "completed_at": 0.0,
            "metadata": {
                "backlog_id": "backlog-sync",
                "approval_request_id": "approval-1",
                "execution_run_id": "run-1",
            },
        }
        completed_task = {
            "id": "task-1",
            "status": "completed",
            "error": "",
            "result": "Implementation landed cleanly.",
            "created_at": 1.0,
            "updated_at": 4.0,
            "completed_at": 4.0,
            "metadata": {
                "backlog_id": "backlog-sync",
                "approval_request_id": "approval-1",
                "execution_run_id": "run-1",
                "verification_passed": True,
            },
        }
        with (
            patch(
                "athanor_agents.operator_work.fetch_backlog_record",
                AsyncMock(side_effect=[dict(backlog), {**dict(backlog), "review_id": "approval-1"}]),
            ),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            approval_payload = await operator_work.sync_backlog_item_from_task(pending_approval_task)
            completed_payload = await operator_work.sync_backlog_item_from_task(completed_task)

        self.assertIsNotNone(approval_payload)
        self.assertEqual("waiting_approval", approval_payload["status"])
        self.assertEqual("approval-1", approval_payload["review_id"])
        self.assertIsNotNone(completed_payload)
        self.assertEqual("completed", completed_payload["status"])
        self.assertEqual("run-1", completed_payload["result_id"])
        self.assertEqual("task-1", completed_payload["metadata"]["latest_task_id"])
        self.assertEqual("run-1", completed_payload["metadata"]["latest_run_id"])
        self.assertNotIn("failure", completed_payload["metadata"])
        self.assertNotIn("failure_detail", completed_payload["metadata"])
        self.assertEqual("", completed_payload["blocking_reason"])
        self.assertEqual(2, upsert_backlog_record.await_count)

    async def test_sync_backlog_item_from_task_carries_autonomous_value_acceptance_metadata(self) -> None:
        backlog = {
            "id": "backlog-value-proof",
            "title": "Ship accepted operator value",
            "prompt": "Land and verify a bounded fix.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "athanor",
            "work_class": "migration",
            "priority": 4,
            "status": "running",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "builder",
            "project_id": "athanor",
            "source_type": "operator_request",
            "source_ref": "request-value-proof-1",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
            "materialization_source": "operator_request",
            "materialization_reason": "manual backlog capture",
            "recurrence_program_id": "",
            "result_id": "",
            "review_id": "",
            "value_class": "operator_value",
            "deliverable_kind": "code_patch",
            "deliverable_refs": [],
            "beneficiary_surface": "athanor_core",
            "acceptance_mode": "hybrid",
            "accepted_by": "",
            "accepted_at": "",
            "acceptance_proof_refs": [],
            "operator_steered": False,
            "metadata": {
                "value_class": "operator_value",
                "deliverable_kind": "code_patch",
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "hybrid",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 2.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        completed_task = {
            "id": "task-value-proof",
            "status": "completed",
            "error": "",
            "result": "Bounded fix landed cleanly.",
            "created_at": 1.0,
            "updated_at": 7.0,
            "completed_at": 7.0,
            "metadata": {
                "backlog_id": "backlog-value-proof",
                "execution_run_id": "run-value-proof",
                "verification_passed": True,
                "value_class": "operator_value",
                "deliverable_kind": "code_patch",
                "deliverable_refs": ["reports/proof/operator-value.json"],
                "beneficiary_surface": "athanor_core",
                "acceptance_mode": "hybrid",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T04:10:00+00:00",
                "acceptance_proof_refs": ["reports/proof/operator-value-acceptance.json"],
                "operator_steered": False,
            },
        }
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            payload = await operator_work.sync_backlog_item_from_task(completed_task)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("completed", payload["status"])
        self.assertEqual("operator_value", payload["value_class"])
        self.assertEqual("code_patch", payload["deliverable_kind"])
        self.assertEqual(["reports/proof/operator-value.json"], payload["deliverable_refs"])
        self.assertEqual("athanor_core", payload["beneficiary_surface"])
        self.assertEqual("hybrid", payload["acceptance_mode"])
        self.assertEqual("Shaun", payload["accepted_by"])
        self.assertEqual("2026-04-20T04:10:00+00:00", payload["accepted_at"])
        self.assertEqual(
            ["reports/proof/operator-value-acceptance.json"],
            payload["acceptance_proof_refs"],
        )
        self.assertFalse(payload["operator_steered"])
        self.assertEqual("Shaun", payload["metadata"]["accepted_by"])
        self.assertEqual("2026-04-20T04:10:00+00:00", payload["metadata"]["accepted_at"])
        upsert_backlog_record.assert_awaited_once()

    async def test_sync_backlog_item_from_task_blocks_unverified_completed_result_without_review_evidence(self) -> None:
        backlog = {
            "id": "backlog-unverified",
            "title": "Validation and Publication",
            "prompt": "Close the governed validation tranche.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
            "priority": 5,
            "status": "scheduled",
            "approval_mode": "operator",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "builder",
            "project_id": "athanor",
            "source_type": "operator_request",
            "source_ref": "request-closure-1",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
            "materialization_source": "operator_request",
            "materialization_reason": "manual backlog capture",
            "recurrence_program_id": "",
            "result_id": "run-old",
            "review_id": "",
            "metadata": {
                "latest_task_id": "task-old",
                "latest_run_id": "run-old",
                "verification_passed": True,
                "auto_verification_from_task": True,
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 2.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        completed_task = {
            "id": "task-2",
            "status": "completed",
            "error": "",
            "result": '{"summary":"Validation and Publication task executed successfully."}',
            "created_at": 1.0,
            "updated_at": 5.0,
            "completed_at": 5.0,
            "metadata": {
                "backlog_id": "backlog-unverified",
                "execution_run_id": "run-2",
            },
        }
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            payload = await operator_work.sync_backlog_item_from_task(completed_task)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("blocked", payload["status"])
        self.assertEqual("verification_evidence_missing", payload["blocking_reason"])
        self.assertEqual("run-2", payload["result_id"])
        self.assertEqual("task-2", payload["metadata"]["latest_task_id"])
        self.assertEqual("run-2", payload["metadata"]["latest_run_id"])
        self.assertFalse(payload["metadata"]["verification_passed"])
        self.assertNotIn("auto_verification_from_task", payload["metadata"])
        self.assertEqual("missing_evidence", payload["metadata"]["verification_status"])
        upsert_backlog_record.assert_awaited_once()

    async def test_sync_backlog_item_from_task_routes_unverified_completed_result_with_review_evidence_to_waiting_approval(self) -> None:
        backlog = {
            "id": "backlog-review-needed",
            "title": "Review governed closure packet",
            "prompt": "Route the governed closure through review.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
            "priority": 5,
            "status": "running",
            "approval_mode": "operator",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "builder",
            "project_id": "athanor",
            "source_type": "operator_request",
            "source_ref": "request-closure-2",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "bounded_change_verification",
            "closure_rule": "verified_result_required",
            "materialization_source": "operator_request",
            "materialization_reason": "manual backlog capture",
            "recurrence_program_id": "",
            "result_id": "",
            "review_id": "",
            "metadata": {},
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 2.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        completed_task = {
            "id": "task-3",
            "status": "completed",
            "error": "",
            "result": "Work finished, operator review still required.",
            "created_at": 1.0,
            "updated_at": 6.0,
            "completed_at": 6.0,
            "metadata": {
                "backlog_id": "backlog-review-needed",
                "execution_run_id": "run-3",
                "approval_request_id": "approval-3",
            },
        }
        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            payload = await operator_work.sync_backlog_item_from_task(completed_task)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("waiting_approval", payload["status"])
        self.assertEqual("approval-3", payload["review_id"])
        self.assertEqual("run-3", payload["result_id"])
        self.assertFalse(payload["metadata"]["verification_passed"])
        self.assertNotIn("auto_verification_from_task", payload["metadata"])
        self.assertEqual("needs_review", payload["metadata"]["verification_status"])
        upsert_backlog_record.assert_awaited_once()

    async def test_materialize_maintenance_signal_creates_canonical_backlog_item(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_backlog_record",
            AsyncMock(return_value=True),
        ):
            backlog = await operator_work.materialize_maintenance_signal(
                project_id="kindred",
                title="Weekly packet maintenance",
                prompt="Refresh project maintenance evidence for Kindred.",
                source_ref="project-packet:kindred:weekly",
                owner_agent="coding-agent",
            )

        self.assertEqual("maintenance", backlog["family"])
        self.assertEqual("kindred", backlog["project_id"])
        self.assertEqual("program_signal", backlog["source_type"])
        self.assertEqual("project_packet_cadence", backlog["materialization_source"])
        self.assertEqual("private_but_cloud_allowed", backlog["routing_class"])
        self.assertEqual("maintenance_proof", backlog["verification_contract"])
        self.assertEqual("proof_or_review_required", backlog["closure_rule"])

    async def test_materialize_bootstrap_follow_up_creates_canonical_backlog_item(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_backlog_record",
            AsyncMock(return_value=True),
        ):
            backlog = await operator_work.materialize_bootstrap_follow_up(
                program_id="launch-readiness-bootstrap",
                slice_id="slice-foundry-completion",
                family="project_bootstrap",
                title="Follow up foundry completion slice",
                prompt="Convert the foundry completion bootstrap slice into governed queue work.",
                project_id="athanor",
                source_ref="bootstrap:launch-readiness-bootstrap:slice-foundry-completion",
                owner_agent="coding-agent",
            )

        self.assertEqual("project_bootstrap", backlog["family"])
        self.assertEqual("athanor", backlog["project_id"])
        self.assertEqual("bootstrap_follow_up", backlog["source_type"])
        self.assertEqual("bootstrap_program", backlog["materialization_source"])
        self.assertEqual("launch-readiness-bootstrap", backlog["recurrence_program_id"])

    async def test_materialize_maintenance_signal_reuses_existing_nonterminal_backlog(self) -> None:
        existing = {
            "id": "backlog-maint-existing",
            "title": "Old maintenance title",
            "prompt": "Old maintenance prompt",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "kindred",
            "work_class": "maintenance",
            "priority": 3,
            "status": "captured",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "maintenance",
            "project_id": "kindred",
            "source_type": "program_signal",
            "source_ref": "project-packet:kindred:weekly",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "closure_rule": "proof_or_review_required",
            "materialization_source": "project_packet_cadence",
            "materialization_reason": "old",
            "recurrence_program_id": "weekly-kindred-maintenance",
            "result_id": "",
            "review_id": "",
            "metadata": {"dispatch_history": [{"timestamp": 1.0}]},
            "created_by": "system",
            "origin": "system",
            "ready_at": 0.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        with (
            patch("athanor_agents.operator_work.list_backlog_records", AsyncMock(return_value=[dict(existing)])),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            backlog = await operator_work.materialize_maintenance_signal(
                project_id="kindred",
                title="Weekly packet maintenance",
                prompt="Refresh project maintenance evidence for Kindred.",
                source_ref="project-packet:kindred:weekly",
                owner_agent="coding-agent",
                recurrence_program_id="weekly-kindred-maintenance",
                metadata={"evidence_ref": "reports/maintenance/kindred.json"},
            )

        self.assertEqual("backlog-maint-existing", backlog["id"])
        self.assertEqual("Weekly packet maintenance", backlog["title"])
        self.assertEqual(
            "Recurring maintenance signal emitted governed queue work.",
            backlog["materialization_reason"],
        )
        self.assertEqual("reports/maintenance/kindred.json", backlog["metadata"]["evidence_ref"])
        upsert_backlog_record.assert_awaited_once()

    async def test_materialize_bootstrap_follow_up_reuses_existing_nonterminal_backlog(self) -> None:
        existing = {
            "id": "backlog-bootstrap-existing",
            "title": "Old bootstrap title",
            "prompt": "Old bootstrap prompt",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "athanor",
            "work_class": "project_bootstrap",
            "priority": 3,
            "status": "ready",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "project_bootstrap",
            "project_id": "athanor",
            "source_type": "bootstrap_follow_up",
            "source_ref": "bootstrap:launch-readiness-bootstrap:slice-foundry-completion",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "scaffold_integrity",
            "closure_rule": "result_or_review_required",
            "materialization_source": "bootstrap_program",
            "materialization_reason": "old",
            "recurrence_program_id": "launch-readiness-bootstrap",
            "result_id": "",
            "review_id": "",
            "metadata": {"linked_slice_id": "slice-foundry-completion"},
            "created_by": "bootstrap",
            "origin": "bootstrap",
            "ready_at": 1.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        with (
            patch("athanor_agents.operator_work.list_backlog_records", AsyncMock(return_value=[dict(existing)])),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            backlog = await operator_work.materialize_bootstrap_follow_up(
                program_id="launch-readiness-bootstrap",
                slice_id="slice-foundry-completion",
                family="project_bootstrap",
                title="Follow up foundry completion slice",
                prompt="Convert the foundry completion bootstrap slice into governed queue work.",
                project_id="athanor",
                source_ref="bootstrap:launch-readiness-bootstrap:slice-foundry-completion",
                owner_agent="coding-agent",
                metadata={"recommended_host_id": "codex_external"},
            )

        self.assertEqual("backlog-bootstrap-existing", backlog["id"])
        self.assertEqual("Follow up foundry completion slice", backlog["title"])
        self.assertEqual(
            "Bootstrap follow-up emitted governed queue work.",
            backlog["materialization_reason"],
        )
        self.assertEqual("codex_external", backlog["metadata"]["recommended_host_id"])
        upsert_backlog_record.assert_awaited_once()

    async def test_materialize_improvement_proposal_creates_canonical_backlog_item(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_backlog_record",
            AsyncMock(return_value=True),
        ):
            payload = await operator_work.materialize_improvement_proposal(
                proposal_id="proposal-123",
                title="Tighten handoff prompt",
                description="Reduce handoff ambiguity in coding-agent transitions.",
                category="prompt",
                expected_improvement="Fewer failed handoffs",
                benchmark_targets=["agent_health"],
                target_files=["projects/agents/prompts/coding-agent.md"],
                proposed_changes={"projects/agents/prompts/coding-agent.md": "updated prompt delta"},
                recurrence_program_id="improvement-cycle",
            )

        backlog = payload["backlog"]
        self.assertEqual("created", payload["status"])
        self.assertEqual("maintenance", payload["family"])
        self.assertEqual("proposal_only", payload["execution_plane"])
        self.assertEqual("proposal_only", payload["admission_classification"])
        self.assertEqual("improvement_proposal", backlog["source_type"])
        self.assertEqual("self_improvement", backlog["materialization_source"])
        self.assertEqual("improvement:proposal-123", backlog["source_ref"])
        self.assertEqual("improvement-cycle", backlog["recurrence_program_id"])

    async def test_materialize_improvement_proposal_refreshes_existing_nonterminal_backlog(self) -> None:
        existing = {
            "id": "backlog-improvement-existing",
            "title": "Old improvement title",
            "prompt": "Old improvement prompt",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "maintenance",
            "priority": 3,
            "status": "captured",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "maintenance",
            "project_id": "",
            "source_type": "improvement_proposal",
            "source_ref": "improvement:proposal-123",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "closure_rule": "proof_or_review_required",
            "materialization_source": "self_improvement",
            "materialization_reason": "old",
            "recurrence_program_id": "improvement-cycle",
            "result_id": "",
            "review_id": "",
            "metadata": {"proposal_id": "proposal-123"},
            "created_by": "self_improvement",
            "origin": "self_improvement",
            "ready_at": 0.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        with (
            patch("athanor_agents.operator_work.list_backlog_records", AsyncMock(return_value=[dict(existing)])),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            payload = await operator_work.materialize_improvement_proposal(
                proposal_id="proposal-123",
                title="Tighten handoff prompt",
                description="Reduce handoff ambiguity in coding-agent transitions.",
                category="prompt",
                expected_improvement="Fewer failed handoffs",
                benchmark_targets=["agent_health"],
                target_files=["projects/agents/prompts/coding-agent.md"],
                proposed_changes={"projects/agents/prompts/coding-agent.md": "updated prompt delta"},
                recurrence_program_id="improvement-cycle",
            )

        backlog = payload["backlog"]
        self.assertEqual("refreshed", payload["status"])
        self.assertEqual("backlog-improvement-existing", backlog["id"])
        self.assertEqual("Tighten handoff prompt", backlog["title"])
        self.assertEqual(
            "Self-improvement proposal emitted governed queue work.",
            backlog["materialization_reason"],
        )
        upsert_backlog_record.assert_awaited_once()

    async def test_materialize_pipeline_starvation_recovery_creates_canonical_backlog_item(self) -> None:
        with patch(
            "athanor_agents.operator_work.upsert_backlog_record",
            AsyncMock(return_value=True),
        ):
            payload = await operator_work.materialize_pipeline_starvation_recovery(
                project_id="project-alpha",
                hours_idle=25.3,
                now_ts=1713415200.0,
            )

        backlog = payload["backlog"]
        self.assertEqual("created", payload["status"])
        self.assertEqual("maintenance", backlog["family"])
        self.assertEqual("project-alpha", backlog["project_id"])
        self.assertEqual("pipeline_signal", backlog["source_type"])
        self.assertEqual("pipeline_starvation", backlog["materialization_source"])
        self.assertEqual("maintenance_proof", backlog["verification_contract"])
        self.assertEqual("proof_or_review_required", backlog["closure_rule"])
        self.assertEqual("pipeline-starvation:project-alpha:1713398400", backlog["source_ref"])
        self.assertEqual("pipeline-cycle", backlog["recurrence_program_id"])

    async def test_materialize_pipeline_starvation_recovery_refreshes_same_window(self) -> None:
        existing = {
            "id": "backlog-starvation-existing",
            "title": "Old starvation title",
            "prompt": "Old starvation prompt",
            "owner_agent": "general-assistant",
            "support_agents": [],
            "scope_type": "project",
            "scope_id": "project-alpha",
            "work_class": "maintenance",
            "priority": 2,
            "status": "captured",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "family": "maintenance",
            "project_id": "project-alpha",
            "source_type": "pipeline_signal",
            "source_ref": "pipeline-starvation:project-alpha:1713398400",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "closure_rule": "proof_or_review_required",
            "materialization_source": "pipeline_starvation",
            "materialization_reason": "old",
            "recurrence_program_id": "pipeline-cycle",
            "result_id": "",
            "review_id": "",
            "metadata": {"hours_idle": 24.0},
            "created_by": "pipeline",
            "origin": "pipeline",
            "ready_at": 0.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 2.0,
            "completed_at": 0.0,
        }
        with (
            patch("athanor_agents.operator_work.list_backlog_records", AsyncMock(return_value=[dict(existing)])),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
        ):
            payload = await operator_work.materialize_pipeline_starvation_recovery(
                project_id="project-alpha",
                hours_idle=26.1,
                now_ts=1713416200.0,
            )

        backlog = payload["backlog"]
        self.assertEqual("refreshed", payload["status"])
        self.assertEqual("backlog-starvation-existing", backlog["id"])
        self.assertEqual("pipeline-starvation:project-alpha:1713398400", backlog["source_ref"])
        self.assertEqual(26.1, backlog["metadata"]["hours_idle"])
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

    async def test_dispatch_backlog_item_preserves_terminal_backlog_sync_when_task_finishes_during_dispatch(self) -> None:
        initial_backlog = {
            "id": "backlog-race-1",
            "title": "Validation and Publication",
            "prompt": "Advance the governed dispatch claim.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
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
                "materialization_source": "governed_dispatch_state",
                "workload_class": "coding_implementation",
            },
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 1.0,
            "scheduled_for": 0.0,
            "created_at": 1.0,
            "updated_at": 1.0,
            "completed_at": 0.0,
        }
        synced_backlog = {
            **initial_backlog,
            "status": "completed",
            "result_id": "task-race-1",
            "completed_at": 10.0,
            "updated_at": 10.0,
            "metadata": {
                **initial_backlog["metadata"],
                "latest_task_id": "task-race-1",
                "latest_run_id": "task-race-1",
                "verification_passed": True,
                "auto_verification_from_task": True,
                "result_id": "task-race-1",
            },
        }
        submission = type(
            "Submission",
            (),
            {
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-race-1", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()
        with (
            patch(
                "athanor_agents.operator_work.fetch_backlog_record",
                AsyncMock(side_effect=[dict(initial_backlog), dict(synced_backlog)]),
            ) as fetch_backlog_record,
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)) as upsert_backlog_record,
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)),
        ):
            payload = await operator_work.dispatch_backlog_item("backlog-race-1", reason="Dispatch now")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual("completed", payload["backlog"]["status"])
        self.assertEqual("task-race-1", payload["backlog"]["result_id"])
        self.assertEqual("task-race-1", payload["backlog"]["metadata"]["latest_task_id"])
        self.assertEqual("Allowed", payload["backlog"]["metadata"]["governor_reason"])
        self.assertEqual("A", payload["backlog"]["metadata"]["governor_level"])
        self.assertEqual(2, fetch_backlog_record.await_count)
        upsert_backlog_record.assert_awaited_once()

    async def test_dispatch_backlog_item_derives_governed_proof_commands_for_validation_lane(self) -> None:
        initial_backlog = {
            "id": "backlog-proof-dispatch-1",
            "title": "Validation and Publication",
            "prompt": "Advance the governed validation claim.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
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
                "materialization_source": "governed_dispatch_state",
                "preferred_lane_family": "validation_and_checkpoint",
                "workload_class": "coding_implementation",
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
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-proof-1", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()

        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(initial_backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            await operator_work.dispatch_backlog_item("backlog-proof-dispatch-1", reason="Dispatch validation")

        submitted_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertEqual(
            [
                [sys.executable, "scripts/validate_platform_contract.py"],
                [sys.executable, "scripts/generate_documentation_index.py", "--check"],
                [sys.executable, "scripts/generate_project_maturity_report.py", "--check"],
                [sys.executable, "scripts/generate_truth_inventory_reports.py"],
                [sys.executable, "scripts/generate_truth_inventory_reports.py", "--check"],
            ],
            submitted_metadata["proof_commands"],
        )
        self.assertEqual(
            f"{sys.executable} scripts/validate_platform_contract.py",
            submitted_metadata["proof_command_surface"],
        )
        self.assertEqual(
            [
                "reports/truth-inventory/steady-state-status.json",
                "reports/truth-inventory/ecosystem-master-plan.json",
                "docs/operations/REPO-ROOTS-REPORT.md",
                "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
                "reports/truth-inventory/surface-owner-matrix.json",
            ],
            submitted_metadata["proof_artifact_paths"],
        )
        self.assertEqual("openai_codex", submitted_metadata["preferred_provider_id"])
        self.assertEqual("private_but_cloud_allowed", submitted_metadata["policy_class"])
        self.assertEqual("frontier_cloud", submitted_metadata["meta_lane"])

    async def test_dispatch_backlog_item_derives_governed_proof_commands_for_capacity_lane(self) -> None:
        initial_backlog = {
            "id": "backlog-proof-dispatch-2",
            "title": "Capacity and Harvest Truth",
            "prompt": "Advance the governed capacity claim.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
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
                "materialization_source": "governed_dispatch_state",
                "preferred_lane_family": "capacity_truth_repair",
                "workload_class": "coding_implementation",
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
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-proof-2", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()

        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(initial_backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            await operator_work.dispatch_backlog_item("backlog-proof-dispatch-2", reason="Dispatch capacity")

        submitted_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertEqual(
            [
                [sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
                [sys.executable, "scripts/collect_capacity_telemetry.py"],
                [sys.executable, "scripts/write_quota_truth_snapshot.py"],
            ],
            submitted_metadata["proof_commands"],
        )
        self.assertEqual(
            f"{sys.executable} scripts/run_gpu_scheduler_baseline_eval.py",
            submitted_metadata["proof_command_surface"],
        )
        self.assertEqual(
            [
                "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                "reports/truth-inventory/capacity-telemetry.json",
                "reports/truth-inventory/quota-truth.json",
            ],
            submitted_metadata["proof_artifact_paths"],
        )

    async def test_dispatch_backlog_item_marks_safe_surface_claims_for_after_agent_proof(self) -> None:
        initial_backlog = {
            "id": "backlog-proof-dispatch-3",
            "title": "Dashboard visible proof",
            "prompt": "Ship the dashboard-visible-proof canary.",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
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
                "materialization_source": "governed_dispatch_state",
                "preferred_lane_family": "safe_surface_execution",
                "autonomous_value_canary_id": "dashboard-visible-proof",
                "deliverable_refs": ["projects/dashboard/src/features/overview/command-center.tsx"],
                "workload_class": "coding_implementation",
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
                "task": type("TaskRecord", (), {"to_dict": lambda self: {"id": "task-proof-3", "status": "pending"}})(),
                "decision": type("Decision", (), {"reason": "Allowed", "autonomy_level": "A"})(),
            },
        )()

        with (
            patch("athanor_agents.operator_work.fetch_backlog_record", AsyncMock(return_value=dict(initial_backlog))),
            patch("athanor_agents.operator_work.upsert_backlog_record", AsyncMock(return_value=True)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            await operator_work.dispatch_backlog_item("backlog-proof-dispatch-3", reason="Dispatch dashboard proof")

        submitted_metadata = submit_governed_task.await_args.kwargs["metadata"]
        self.assertEqual(
            [[sys.executable, "scripts/run_dashboard_value_proof.py", "--surface", "dashboard_overview"]],
            submitted_metadata["proof_commands"],
        )
        self.assertEqual("after_agent", submitted_metadata["proof_execution_stage"])
        self.assertEqual(900, submitted_metadata["proof_timeout_seconds"])
        self.assertEqual("google_gemini", submitted_metadata["preferred_provider_id"])
        self.assertTrue(submitted_metadata["requires_mutable_implementation_authority"])

    async def test_list_backlog_normalizes_all_status_to_unfiltered_query(self) -> None:
        with patch(
            "athanor_agents.operator_work.list_backlog_records",
            AsyncMock(return_value=[{"id": "backlog-1"}]),
        ) as list_backlog_records:
            backlog = await operator_work.list_backlog(status="all", owner_agent="coding-agent", limit=12)

        self.assertEqual([{"id": "backlog-1"}], backlog)
        list_backlog_records.assert_awaited_once_with(status="", owner_agent="coding-agent", limit=None)

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
