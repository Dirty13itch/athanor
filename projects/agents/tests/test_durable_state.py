from __future__ import annotations

import sys
import types
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents import durable_state as durable_state_module  # noqa: E402
from athanor_agents.durable_state import (  # noqa: E402
    _fetch_all,
    _as_datetime,
    durable_state_sql_path,
    ensure_durable_state_schema,
    get_durable_state_status,
    reset_durable_state_cache,
)


class DurableStateContractTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        reset_durable_state_cache()

    async def test_missing_postgres_url_disables_durable_state(self) -> None:
        with patch("athanor_agents.durable_state.settings.postgres_url", ""):
            reset_durable_state_cache()
            ready = await ensure_durable_state_schema()
            status = get_durable_state_status()

        self.assertFalse(ready)
        self.assertEqual("disabled", status["mode"])
        self.assertFalse(status["configured"])
        self.assertFalse(status["schema_ready"])

    async def test_missing_psycopg_marks_module_missing(self) -> None:
        with patch("athanor_agents.durable_state.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            with patch(
                "athanor_agents.durable_state.importlib.import_module",
                side_effect=ModuleNotFoundError("psycopg"),
            ):
                reset_durable_state_cache()
                ready = await ensure_durable_state_schema()
                status = get_durable_state_status()

        self.assertFalse(ready)
        self.assertEqual("module_missing", status["mode"])
        self.assertTrue(status["configured"])
        self.assertFalse(status["available"])
        self.assertFalse(status["schema_ready"])

    async def test_schema_bootstrap_executes_sql_and_reports_ready(self) -> None:
        state: dict[str, object] = {"statements": []}

        class FakeCursor:
            description = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def execute(self, statement, params=None):
                state["statements"].append((statement, params))

        class FakeConnection:
            def cursor(self):
                return FakeCursor()

            async def close(self):
                state["closed"] = True

        class FakeAsyncConnection:
            @classmethod
            async def connect(cls, conninfo: str, autocommit: bool = False):
                state["conninfo"] = conninfo
                state["autocommit"] = autocommit
                return FakeConnection()

        fake_module = types.ModuleType("psycopg")
        fake_module.AsyncConnection = FakeAsyncConnection

        with patch("athanor_agents.durable_state.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            with patch("athanor_agents.durable_state.importlib.import_module", return_value=fake_module):
                reset_durable_state_cache()
                ready = await ensure_durable_state_schema()
                status = get_durable_state_status()

        self.assertTrue(ready)
        self.assertEqual("ready", status["mode"])
        self.assertTrue(status["configured"])
        self.assertTrue(status["available"])
        self.assertTrue(status["schema_ready"])
        self.assertEqual("postgresql://athanor:test@localhost/athanor", state["conninfo"])
        self.assertTrue(state["autocommit"])
        self.assertTrue(state["closed"])
        executed = [statement for statement, _ in state["statements"]]
        self.assertTrue(any("CREATE SCHEMA IF NOT EXISTS work" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS work.operator_todos" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS work.operator_inbox" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS work.idea_garden_items" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS work.agent_backlog" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS runs.task_snapshots" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS runs.execution_runs" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS runs.run_attempts" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS runs.run_steps" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS audit.approval_requests" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS control.system_mode_history" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS control.attention_budgets" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS control.core_change_windows" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS control.agent_value_scores" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS control.domain_value_scores" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS foundry.project_packets" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS foundry.architecture_packets" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS foundry.foundry_runs" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS foundry.deploy_candidates" in statement for statement in executed))
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS foundry.rollback_events" in statement for statement in executed))

    def test_bootstrap_sql_contains_expected_tables(self) -> None:
        text = durable_state_sql_path().read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS work.goals", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS work.operator_todos", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS work.operator_inbox", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS work.idea_garden_items", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS work.agent_backlog", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS work.workplan_snapshots", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS runs.task_snapshots", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS runs.execution_runs", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS runs.run_attempts", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS runs.run_steps", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS audit.approval_requests", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS control.system_mode_history", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS control.attention_budgets", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS control.core_change_windows", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS control.agent_value_scores", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS control.domain_value_scores", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.project_packets", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.architecture_packets", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.execution_slices", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.foundry_runs", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.deploy_candidates", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.maintenance_runs", text)
        self.assertIn("CREATE TABLE IF NOT EXISTS foundry.rollback_events", text)
        self.assertIn("control.schema_versions", text)

    def test_as_datetime_accepts_isoformat_strings(self) -> None:
        parsed = _as_datetime("2026-04-01T03:14:15+00:00")
        self.assertIsNotNone(parsed)
        self.assertEqual("2026-04-01T03:14:15+00:00", parsed.isoformat())

    async def test_runtime_failure_opens_short_circuit_for_repeated_queries(self) -> None:
        attempts = {"count": 0}

        @asynccontextmanager
        async def failing_open_connection():
            attempts["count"] += 1
            raise RuntimeError("too many clients already")
            yield

        durable_state_module._SCHEMA_READY = True
        durable_state_module._SCHEMA_ATTEMPTED = True

        with (
            patch("athanor_agents.durable_state.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"),
            patch("athanor_agents.durable_state.ensure_durable_state_schema", AsyncMock(return_value=True)),
            patch("athanor_agents.durable_state._open_connection", failing_open_connection),
        ):
            first = await _fetch_all("SELECT 1")
            second = await _fetch_all("SELECT 1")
            status = get_durable_state_status()

        self.assertEqual([], first)
        self.assertEqual([], second)
        self.assertEqual(1, attempts["count"])
        self.assertEqual("degraded", status["mode"])
        self.assertFalse(status["available"])
        self.assertTrue(status["schema_ready"])
        self.assertIn("too many clients already", str(status["reason"]))


if __name__ == "__main__":
    unittest.main()
