from __future__ import annotations

import asyncio
import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_payload_reports_result_backed_throughput_and_repairable_reconciliation_truth() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    now_ts = 100_000.0
    module._now_ts = lambda: now_ts

    async def _backlog_records():
        return [
            {
                "backlog_id": "backlog-result-1",
                "title": "Ship builder fix",
                "family": "builder",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "run-1",
                "review_id": "",
                "blocking_reason": "",
                "materialization_source": "operator_request",
                "created_at": now_ts - 7_200,
                "updated_at": now_ts - 3_600,
                "completed_at": now_ts,
                "metadata": {
                    "verification_passed": True,
                },
            },
            {
                "backlog_id": "backlog-review-1",
                "title": "Approve runtime packet",
                "family": "review",
                "project_id": "athanor",
                "status": "waiting_approval",
                "result_id": "",
                "review_id": "review-1",
                "blocking_reason": "",
                "materialization_source": "operator_request",
                "created_at": now_ts - 14_400,
                "updated_at": now_ts - 7_200,
                "completed_at": None,
                "metadata": {},
            },
            {
                "backlog_id": "backlog-stale-1",
                "title": "Refresh maintenance proof",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "scheduled",
                "result_id": "",
                "review_id": "",
                "blocking_reason": "",
                "materialization_source": "project_packet_cadence",
                "created_at": now_ts - 10_800,
                "updated_at": now_ts - 5_400,
                "completed_at": None,
                "metadata": {
                    "latest_task_id": "task-stale-1",
                },
            },
            {
                "backlog_id": "backlog-blocked-1",
                "title": "Investigate research packet",
                "family": "research_audit",
                "project_id": "athanor-docs",
                "status": "blocked",
                "result_id": "",
                "review_id": "",
                "blocking_reason": "",
                "materialization_source": "research_scheduler",
                "created_at": now_ts - 18_000,
                "updated_at": now_ts - 9_000,
                "completed_at": None,
                "metadata": {},
            },
            {
                "backlog_id": "backlog-missing-result-1",
                "title": "Close stale bootstrap slice",
                "family": "project_bootstrap",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "",
                "review_id": "",
                "blocking_reason": "",
                "materialization_source": "bootstrap_program",
                "created_at": now_ts - 21_600,
                "updated_at": now_ts - 10_800,
                "completed_at": now_ts - 3_600,
                "metadata": {
                    "verification_passed": True,
                },
            },
            {
                "backlog_id": "backlog-missing-review-1",
                "title": "Promotion packet needs approval",
                "family": "review",
                "project_id": "athanor",
                "status": "waiting_approval",
                "result_id": "",
                "review_id": "",
                "blocking_reason": "",
                "materialization_source": "operator_request",
                "created_at": now_ts - 25_200,
                "updated_at": now_ts - 12_600,
                "completed_at": None,
                "metadata": {},
            },
            {
                "backlog_id": "backlog-missing-proof-1",
                "title": "Synthetic maintenance closeout",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "run-proof-gap-1",
                "review_id": "",
                "blocking_reason": "",
                "verification_contract": "maintenance_proof",
                "materialization_source": "governed_dispatch_state",
                "created_at": now_ts - 9_000,
                "updated_at": now_ts - 4_500,
                "completed_at": now_ts - 1_800,
                "metadata": {
                    "auto_verification_from_task": True,
                },
            },
            {
                "backlog_id": "backlog-proposal-1",
                "title": "Prompt tuning proposal",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "waiting_approval",
                "result_id": "",
                "review_id": "review-proposal-1",
                "blocking_reason": "",
                "materialization_source": "self_improvement",
                "source_type": "improvement_proposal",
                "created_at": now_ts - 3_600,
                "updated_at": now_ts - 1_800,
                "completed_at": None,
                "metadata": {},
            },
        ]

    async def _tasks():
        return [
            {
                "id": "task-stale-1",
                "status": "completed",
            }
        ]

    async def _scheduled_jobs():
        return [
            {
                "id": "agent-schedule:coding-agent",
                "last_execution_mode": "materialized_to_backlog",
                "last_execution_plane": "queue",
                "last_admission_classification": "queue",
                "last_backlog_id": "backlog-result-1",
            },
            {
                "id": "daily-digest",
                "last_execution_mode": "executed_directly",
                "last_execution_plane": "direct_control",
                "last_admission_classification": "direct_control",
                "last_backlog_id": "",
            },
            {
                "id": "improvement-cycle",
                "last_execution_mode": "executed_directly",
                "last_execution_plane": "proposal_only",
                "last_admission_classification": "blocked_by_review_debt",
                "last_backlog_id": "",
            },
            {
                "id": "research:queue-gap",
                "last_execution_mode": "materialized_to_backlog",
                "last_execution_plane": "queue",
                "last_admission_classification": "queue",
                "last_backlog_id": "",
            },
        ]

    async def _empty_truth():
        return {}

    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _empty_truth
    module._load_governed_dispatch_truth = _empty_truth

    payload = asyncio.run(module.build_payload())

    assert payload["result_backed_completion_count"] == 1
    assert payload["review_backed_output_count"] == 2
    assert payload["stale_claim_count"] == 1
    assert payload["dispatch_to_result_latency"]["completed_count"] == 1
    assert payload["dispatch_to_result_latency"]["average_hours"] == 2.0

    assert payload["proposal_conversion"] == {
        "proposal_backlog_count": 1,
        "result_backed_completion_count": 0,
        "review_backed_output_count": 1,
    }
    assert payload["review_debt"]["count"] == 3
    assert payload["review_debt"]["oldest_age_hours"] == 7.0

    assert payload["scheduled_execution"] == {
        "queue_backed_jobs": 2,
        "direct_control_jobs": 1,
        "proposal_only_jobs": 1,
        "blocked_jobs": 1,
        "needs_sync_jobs": 1,
    }

    assert payload["reconciliation"]["issue_count"] == 5
    assert payload["reconciliation"]["repairable_count"] == 5
    assert payload["reconciliation"]["issues_by_type"] == {
        "missing_verification_evidence": 1,
        "stale_terminal_task": 1,
        "missing_blocking_reason": 1,
        "missing_result_evidence": 1,
        "missing_review_evidence": 1,
    }
    issue_types = {item["issue_type"] for item in payload["reconciliation"]["issues"]}
    assert issue_types == {
        "missing_verification_evidence",
        "stale_terminal_task",
        "missing_blocking_reason",
        "missing_result_evidence",
        "missing_review_evidence",
    }


def test_build_payload_degrades_soft_when_live_side_channels_are_unavailable() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        raise RuntimeError("task feed unavailable")

    async def _scheduled_jobs():
        raise RuntimeError("scheduled feed unavailable")

    async def _empty_truth():
        return {}

    async def _empty_agent_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        return {}

    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _empty_truth
    module._load_governed_dispatch_truth = _empty_truth
    module._load_agent_route_payload = _empty_agent_payload
    module.COMPLETION_PASS_LEDGER_PATH = Path("/nonexistent/completion-pass-ledger.json")

    payload = asyncio.run(module.build_payload())

    assert payload["result_backed_completion_count"] == 0
    assert payload["scheduled_execution"] == {
        "queue_backed_jobs": 0,
        "direct_control_jobs": 0,
        "proposal_only_jobs": 0,
        "blocked_jobs": 0,
        "needs_sync_jobs": 0,
    }
    assert payload["degraded_sections"] == ["tasks:task feed unavailable", "scheduled_jobs:scheduled feed unavailable"]


def test_build_payload_falls_back_to_ralph_queue_truth_when_canonical_queue_feed_is_empty() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        return []

    async def _scheduled_jobs():
        raise RuntimeError("scheduled feed unavailable")

    async def _ralph_truth():
        return {
            "autonomous_queue_summary": {
                "queue_count": 3,
                "dispatchable_queue_count": 2,
                "blocked_queue_count": 1,
            },
            "autonomous_queue": [
                {
                    "id": "workstream:validation-and-publication",
                    "preferred_lane_family": "validation_and_checkpoint",
                    "repo": "/mnt/c/Athanor",
                    "value_class": "failing_eval_or_validator",
                },
                {
                    "id": "capability:policy-plane",
                    "preferred_lane_family": "promotion_wave_closure",
                    "repo": "/mnt/c/Athanor",
                    "value_class": "promotion_wave_closure",
                },
                {
                    "id": "burn_class:local_bulk_sovereign",
                    "preferred_lane_family": "capacity_truth_repair",
                    "repo": "/mnt/c/Athanor",
                    "value_class": "capacity_truth_drift",
                },
            ],
        }

    async def _governed_truth():
        return {
            "dispatch_outcome": "failed",
            "current_task_id": "workstream:validation-and-publication",
            "current_task_title": "Validation and Publication",
            "current_source_type": "workstream",
            "execution": {
                "status": "stale_dispatched_task",
                "backlog_id": "backlog-live-1",
                "current_task_id": "workstream:validation-and-publication",
                "current_task_title": "Validation and Publication",
                "task_source": "operator_backlog",
                "dispatch_outcome": "failed",
                "repair_reason": "stale_terminal_dispatch",
            },
        }

    async def _empty_agent_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        return {}

    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _ralph_truth
    module._load_governed_dispatch_truth = _governed_truth
    module._load_agent_route_payload = _empty_agent_payload
    module.COMPLETION_PASS_LEDGER_PATH = Path("/nonexistent/completion-pass-ledger.json")

    payload = asyncio.run(module.build_payload())

    assert payload["backlog_aging"]["open_item_count"] == 3
    assert payload["backlog_aging"]["by_family"] == [
        {
            "family": "capacity_truth_repair",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        },
        {
            "family": "promotion_wave_closure",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        },
        {
            "family": "validation_and_checkpoint",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        },
    ]
    assert payload["backlog_aging"]["by_project"] == [
        {
            "project_id": "Athanor",
            "count": 3,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
    ]


def test_build_payload_carries_forward_historical_result_evidence_when_live_queue_truth_is_empty(tmp_path: Path) -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        return []

    async def _scheduled_jobs():
        return []

    async def _empty_truth():
        return {}

    async def _empty_agent_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        return {}

    completion_pass_ledger_path = tmp_path / "completion-pass-ledger.json"
    completion_pass_ledger_path.write_text(
        """
        {
          "passes": [
            {
              "pass_id": "continuity-pass-1",
              "finished_at": "2026-04-21T09:00:00+00:00",
              "healthy": true,
              "result_evidence": {
                "threshold_required": 5,
                "threshold_progress": 29,
                "threshold_met": true,
                "result_backed_completion_count": 29,
                "review_backed_output_count": 0
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _empty_truth
    module._load_governed_dispatch_truth = _empty_truth
    module._load_agent_route_payload = _empty_agent_payload
    module.COMPLETION_PASS_LEDGER_PATH = completion_pass_ledger_path

    payload = asyncio.run(module.build_payload())

    assert payload["result_backed_completion_count"] == 29
    assert payload["review_backed_output_count"] == 0
    assert payload["result_evidence_basis"] == "historical_carry_forward"
    assert payload["result_evidence_carry_forward"] == {
        "source": "completion_pass_ledger",
        "pass_id": "continuity-pass-1",
        "finished_at": "2026-04-21T09:00:00+00:00",
        "healthy": True,
    }
    assert payload["stale_claim_count"] == 0
    assert payload["reconciliation"]["issue_count"] == 0
    assert payload["reconciliation"]["issues"] == []
    assert payload["degraded_sections"] == []


def test_build_payload_normalizes_compatibility_backlog_records_from_agent_api() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        return []

    async def _scheduled_jobs():
        return []

    async def _empty_truth():
        return {}

    async def _agent_route_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        if route_path.startswith("/v1/operator/backlog?"):
            return {
                "backlog": [
                    {
                        "id": "backlog-api-compat-1",
                        "title": "Builder queue work",
                        "scope_type": "project",
                        "scope_id": "athanor-core",
                        "work_class": "coding_implementation",
                        "status": "ready",
                        "metadata": {
                            "materialization_source": "operator_request",
                            "verification_passed": False,
                        },
                    }
                ]
            }
        if route_path.startswith("/v1/tasks?"):
            return {"tasks": []}
        if route_path.startswith("/v1/tasks/scheduled?"):
            return {"jobs": []}
        raise AssertionError(route_path)

    module._now_ts = lambda: 100_000.0
    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _empty_truth
    module._load_governed_dispatch_truth = _empty_truth
    module._load_agent_route_payload = _agent_route_payload

    payload = asyncio.run(module.build_payload())

    assert payload["backlog_aging"]["open_item_count"] == 1
    assert payload["backlog_aging"]["by_family"] == [
        {
            "family": "builder",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
    ]
    assert payload["backlog_aging"]["by_project"] == [
        {
            "project_id": "athanor-core",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
    ]
    assert payload["degraded_sections"] == []


def test_build_payload_prefers_metadata_workload_class_over_generic_system_improvement() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        return []

    async def _scheduled_jobs():
        return []

    async def _empty_truth():
        return {}

    async def _agent_route_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        if route_path.startswith("/v1/operator/backlog?"):
            return {
                "backlog": [
                    {
                        "id": "backlog-api-compat-2",
                        "title": "Validation and Publication",
                        "scope_type": "global",
                        "scope_id": "athanor",
                        "work_class": "system_improvement",
                        "status": "scheduled",
                        "metadata": {
                            "task_class": "async_backlog_execution",
                            "workload_class": "coding_implementation",
                            "materialization_source": "governed_dispatch_state",
                        },
                    }
                ]
            }
        if route_path.startswith("/v1/tasks?"):
            return {"tasks": []}
        if route_path.startswith("/v1/tasks/scheduled?"):
            return {"jobs": []}
        raise AssertionError(route_path)

    module._now_ts = lambda: 100_000.0
    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _empty_truth
    module._load_governed_dispatch_truth = _empty_truth
    module._load_agent_route_payload = _agent_route_payload

    payload = asyncio.run(module.build_payload())

    assert payload["backlog_aging"]["by_family"] == [
        {
            "family": "builder",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
    ]


def test_build_payload_uses_agent_api_fallback_before_declaring_queue_truth_degraded() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        return []

    async def _scheduled_jobs():
        return []

    async def _ralph_truth():
        return {
            "autonomous_queue_summary": {
                "queue_count": 2,
                "dispatchable_queue_count": 1,
                "blocked_queue_count": 1,
            }
        }

    async def _governed_truth():
        return {
            "execution": {
                "agent_server_base_url": "http://agent.internal",
            }
        }

    async def _agent_route_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        if route_path.startswith("/v1/operator/backlog?"):
            return {
                "backlog": [
                    {
                        "id": "backlog-api-1",
                        "title": "Validation and Publication",
                        "family": "builder",
                        "project_id": "athanor",
                        "status": "completed",
                        "result_id": "run-api-1",
                        "review_id": "",
                        "created_at": 100_000.0 - 3_600,
                        "updated_at": 100_000.0 - 1_800,
                        "completed_at": 100_000.0,
                        "metadata": {"verification_passed": True},
                    }
                ]
            }
        if route_path.startswith("/v1/tasks?"):
            return {
                "tasks": [
                    {
                        "id": "task-api-1",
                        "status": "completed",
                    }
                ]
            }
        if route_path.startswith("/v1/tasks/scheduled?"):
            return {
                "jobs": [
                    {
                        "id": "agent-schedule:coding-agent",
                        "last_execution_mode": "materialized_to_backlog",
                        "last_execution_plane": "queue",
                        "last_admission_classification": "queue",
                        "last_backlog_id": "backlog-api-1",
                    }
                ]
            }
        raise AssertionError(route_path)

    module._now_ts = lambda: 100_000.0
    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _ralph_truth
    module._load_governed_dispatch_truth = _governed_truth
    module._load_agent_route_payload = _agent_route_payload

    payload = asyncio.run(module.build_payload())

    assert payload["result_backed_completion_count"] == 1
    assert payload["backlog_aging"]["open_item_count"] == 0
    assert payload["scheduled_execution"] == {
        "queue_backed_jobs": 1,
        "direct_control_jobs": 0,
        "proposal_only_jobs": 0,
        "blocked_jobs": 0,
        "needs_sync_jobs": 0,
    }
    assert payload["degraded_sections"] == []


def test_build_payload_clears_primary_feed_errors_when_agent_api_fallback_succeeds() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        return []

    async def _tasks():
        raise RuntimeError("No module named 'langchain_core'")

    async def _scheduled_jobs():
        raise RuntimeError("No module named 'langgraph'")

    async def _ralph_truth():
        return {}

    async def _governed_truth():
        return {}

    async def _agent_route_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        if route_path.startswith("/v1/operator/backlog?"):
            return {
                "backlog": [
                    {
                        "id": "backlog-api-1",
                        "title": "Maintenance queue work",
                        "scope_type": "project",
                        "scope_id": "athanor",
                        "work_class": "maintenance",
                        "status": "ready",
                        "metadata": {
                            "materialization_source": "project_packet_cadence",
                        },
                    }
                ]
            }
        if route_path.startswith("/v1/tasks?"):
            return {"tasks": [{"id": "task-api-1", "status": "running"}]}
        if route_path.startswith("/v1/tasks/scheduled?"):
            return {
                "jobs": [
                    {
                        "id": "research:scheduler",
                        "last_execution_mode": "materialized_to_backlog",
                        "last_execution_plane": "queue",
                        "last_admission_classification": "queue",
                        "last_backlog_id": "backlog-api-1",
                    }
                ]
            }
        raise AssertionError(route_path)

    module._now_ts = lambda: 100_000.0
    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _ralph_truth
    module._load_governed_dispatch_truth = _governed_truth
    module._load_agent_route_payload = _agent_route_payload

    payload = asyncio.run(module.build_payload())

    assert payload["scheduled_execution"] == {
        "queue_backed_jobs": 1,
        "direct_control_jobs": 0,
        "proposal_only_jobs": 0,
        "blocked_jobs": 0,
        "needs_sync_jobs": 0,
    }
    assert payload["backlog_aging"]["by_family"] == [
        {
            "family": "maintenance",
            "count": 1,
            "oldest_age_hours": 0.0,
            "average_age_hours": 0.0,
        }
    ]
    assert payload["degraded_sections"] == []


def test_build_payload_counts_governed_dispatch_queue_job_when_scheduled_feeds_are_degraded() -> None:
    module = _load_module(
        f"write_value_throughput_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_value_throughput_scorecard.py",
    )

    async def _backlog_records():
        raise RuntimeError("No module named 'langchain_core'")

    async def _tasks():
        raise RuntimeError("No module named 'langgraph'")

    async def _scheduled_jobs():
        raise RuntimeError("scheduled feed unavailable")

    async def _ralph_truth():
        return {}

    async def _governed_truth():
        return {
            "dispatch_outcome": "success",
            "execution": {
                "status": "dispatched",
                "backlog_id": "backlog-live-1",
                "backlog_status": "scheduled",
                "task_id": "task-live-1",
                "task_status": "pending",
            },
            "materialization": {
                "backlog_id": "backlog-live-1",
                "backlog_status": "scheduled",
            },
        }

    async def _agent_route_payload(route_path: str, *, governed_truth: dict[str, object] | None = None):
        raise RuntimeError(f"{route_path} unavailable: timed out")

    module._now_ts = lambda: 100_000.0
    module._list_backlog_records = _backlog_records
    module._list_tasks = _tasks
    module._build_scheduled_job_records = _scheduled_jobs
    module._load_ralph_truth = _ralph_truth
    module._load_governed_dispatch_truth = _governed_truth
    module._load_agent_route_payload = _agent_route_payload

    payload = asyncio.run(module.build_payload())

    assert payload["scheduled_execution"] == {
        "queue_backed_jobs": 1,
        "direct_control_jobs": 0,
        "proposal_only_jobs": 0,
        "blocked_jobs": 0,
        "needs_sync_jobs": 0,
    }
    assert "scheduled_jobs:scheduled feed unavailable" in payload["degraded_sections"]
