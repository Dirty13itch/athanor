import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.persistence import (  # noqa: E402
    build_checkpointer,
    get_checkpointer_status,
    reset_checkpointer_cache,
)


class PersistenceContractTest(unittest.TestCase):
    def tearDown(self) -> None:
        reset_checkpointer_cache()

    def test_missing_postgres_url_uses_in_memory_fallback(self) -> None:
        with patch("athanor_agents.persistence.settings.postgres_url", ""):
            reset_checkpointer_cache()
            checkpointer = build_checkpointer()
            status = get_checkpointer_status()
        self.assertEqual("InMemorySaver", type(checkpointer).__name__)
        self.assertEqual("memory_fallback", status["mode"])
        self.assertFalse(status["durable"])
        self.assertFalse(status["configured"])
        self.assertEqual("langgraph.checkpoint.memory.InMemorySaver", status["driver"])
        self.assertIn("ATHANOR_POSTGRES_URL not configured", str(status["reason"]))

    def test_missing_postgres_dependency_uses_in_memory_fallback(self) -> None:
        with patch("athanor_agents.persistence.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            with patch(
                "athanor_agents.persistence.importlib.import_module",
                side_effect=ModuleNotFoundError("langgraph.checkpoint.postgres"),
            ):
                reset_checkpointer_cache()
                checkpointer = build_checkpointer()
                status = get_checkpointer_status()
        self.assertEqual("InMemorySaver", type(checkpointer).__name__)
        self.assertEqual("memory_fallback", status["mode"])
        self.assertFalse(status["durable"])
        self.assertTrue(status["configured"])
        self.assertEqual("langgraph.checkpoint.memory.InMemorySaver", status["driver"])
        self.assertIn("langgraph.checkpoint.postgres is not installed", str(status["reason"]))

    def test_postgres_checkpointer_enters_context_and_runs_setup(self) -> None:
        state: dict[str, object] = {}

        class FakeSaver:
            def __init__(self) -> None:
                self.setup_called = False

            def setup(self) -> None:
                self.setup_called = True

        class FakeContext:
            def __init__(self) -> None:
                self.saver = FakeSaver()
                self.exited = False

            def __enter__(self) -> FakeSaver:
                state["entered"] = True
                return self.saver

            def __exit__(self, exc_type, exc, tb) -> None:
                self.exited = True
                state["exited"] = True

        class FakePostgresSaver:
            @classmethod
            def from_conn_string(cls, conn_string: str) -> FakeContext:
                state["conn_string"] = conn_string
                context = FakeContext()
                state["context"] = context
                return context

        with patch("athanor_agents.persistence.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            fake_module = types.ModuleType("langgraph.checkpoint.postgres")
            fake_module.PostgresSaver = FakePostgresSaver
            with patch("athanor_agents.persistence.importlib.import_module", return_value=fake_module):
                reset_checkpointer_cache()
                saver = build_checkpointer()
                status = get_checkpointer_status()
                self.assertEqual("postgresql://athanor:test@localhost/athanor", state["conn_string"])
                self.assertTrue(state["entered"])
                self.assertTrue(saver.setup_called)
                self.assertTrue(callable(getattr(saver, "aget_tuple", None)))
                self.assertTrue(callable(getattr(saver, "aput", None)))
                self.assertTrue(callable(getattr(saver, "aput_writes", None)))
                self.assertTrue(callable(getattr(saver, "alist", None)))
                context = state["context"]
                self.assertFalse(context.exited)
                self.assertEqual("postgres", status["mode"])
                self.assertTrue(status["durable"])
                self.assertTrue(status["configured"])
                self.assertEqual("langgraph.checkpoint.postgres.PostgresSaver", status["driver"])
                reset_checkpointer_cache()
                self.assertTrue(context.exited)

    def test_postgres_checkpointer_shims_async_methods(self) -> None:
        class FakeSaver:
            def setup(self) -> None:
                return None

            def get_tuple(self, config):
                return {"config": config}

            def put(self, config, checkpoint, metadata, new_versions):
                return {"saved": checkpoint["id"], "config": config}

            def put_writes(self, config, writes, task_id, task_path=""):
                self.last_writes = (config, list(writes), task_id, task_path)

            def list(self, config, *, filter=None, before=None, limit=None):
                yield {"config": config, "filter": filter, "before": before, "limit": limit}

        class FakeContext:
            def __enter__(self):
                return FakeSaver()

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        class FakePostgresSaver:
            @classmethod
            def from_conn_string(cls, _conn_string: str) -> FakeContext:
                return FakeContext()

        with patch("athanor_agents.persistence.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            fake_module = types.ModuleType("langgraph.checkpoint.postgres")
            fake_module.PostgresSaver = FakePostgresSaver
            with patch("athanor_agents.persistence.importlib.import_module", return_value=fake_module):
                reset_checkpointer_cache()
                saver = build_checkpointer()

        checkpoint = asyncio.run(saver.aget_tuple({"configurable": {"thread_id": "t-1"}}))
        self.assertEqual({"config": {"configurable": {"thread_id": "t-1"}}}, checkpoint)

        put_result = asyncio.run(
            saver.aput(
                {"configurable": {"thread_id": "t-1"}},
                {"id": "checkpoint-1"},
                {"source": "test"},
                {},
            )
        )
        self.assertEqual("checkpoint-1", put_result["saved"])

        asyncio.run(
            saver.aput_writes(
                {"configurable": {"thread_id": "t-1"}},
                [("channel", {"value": 1})],
                "task-1",
                "path-1",
            )
        )
        self.assertEqual("task-1", saver.last_writes[2])

        async def _collect():
            return [
                item async for item in saver.alist(
                    {"configurable": {"thread_id": "t-1"}},
                    filter={"source": "test"},
                    limit=1,
                )
            ]

        listed = asyncio.run(_collect())
        self.assertEqual(1, len(listed))
        self.assertEqual({"source": "test"}, listed[0]["filter"])

    def test_postgres_checkpointer_init_failure_falls_back_to_memory(self) -> None:
        state: dict[str, object] = {}

        class FakeSaver:
            def setup(self) -> None:
                raise RuntimeError("boom")

        class FakeContext:
            def __init__(self) -> None:
                self.saver = FakeSaver()
                self.exited = False

            def __enter__(self) -> FakeSaver:
                state["entered"] = True
                return self.saver

            def __exit__(self, exc_type, exc, tb) -> None:
                self.exited = True
                state["exited"] = True

        class FakePostgresSaver:
            @classmethod
            def from_conn_string(cls, conn_string: str) -> FakeContext:
                state["conn_string"] = conn_string
                context = FakeContext()
                state["context"] = context
                return context

        fake_module = types.ModuleType("langgraph.checkpoint.postgres")
        fake_module.PostgresSaver = FakePostgresSaver

        with patch("athanor_agents.persistence.settings.postgres_url", "postgresql://athanor:test@localhost/athanor"):
            with patch("athanor_agents.persistence.importlib.import_module", return_value=fake_module):
                reset_checkpointer_cache()
                saver = build_checkpointer()
                status = get_checkpointer_status()

        self.assertEqual("InMemorySaver", type(saver).__name__)
        self.assertEqual("memory_fallback", status["mode"])
        self.assertFalse(status["durable"])
        self.assertTrue(status["configured"])
        self.assertEqual("langgraph.checkpoint.memory.InMemorySaver", status["driver"])
        self.assertIn("Postgres checkpointer init failed: boom", str(status["reason"]))
        self.assertTrue(state["entered"])
        self.assertTrue(state["exited"])


if __name__ == "__main__":
    unittest.main()
