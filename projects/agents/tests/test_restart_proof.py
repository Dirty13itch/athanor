from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from athanor_agents import restart_proof


class _FakeSaver:
    def __init__(self) -> None:
        self.records: dict[str, SimpleNamespace] = {}

    def put(self, config, checkpoint, metadata, new_versions):  # noqa: ARG002
        configurable = dict(config.get("configurable") or {})
        checkpoint_id = configurable.get("checkpoint_id") or "checkpoint-1"
        next_config = {
            "configurable": {
                **configurable,
                "checkpoint_id": checkpoint_id,
            }
        }
        self.records[checkpoint_id] = SimpleNamespace(
            config=next_config,
            checkpoint=checkpoint,
            metadata=dict(metadata),
            parent_config=None,
            pending_writes=[],
        )
        return next_config

    def put_writes(self, config, writes, task_id, task_path=""):  # noqa: ARG002
        checkpoint_id = str(dict(config.get("configurable") or {}).get("checkpoint_id") or "")
        record = self.records[checkpoint_id]
        for channel, value in writes:
            record.pending_writes.append((task_id, channel, value))

    def get_tuple(self, config):
        checkpoint_id = str(dict(config.get("configurable") or {}).get("checkpoint_id") or "")
        return self.records.get(checkpoint_id)


class RestartProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.artifact_path = Path(self.tempdir.name) / "reports" / "bootstrap" / "durable-restart-proof.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_prepare_writes_restart_proof_artifact(self) -> None:
        saver = _FakeSaver()
        with (
            patch("athanor_agents.restart_proof.durable_restart_proof_path", return_value=self.artifact_path),
            patch(
                "athanor_agents.restart_proof._materialize_durable_checkpointer",
                return_value=(saver, {"configured": True, "durable": True, "mode": "postgres"}),
            ),
        ):
            payload = restart_proof.prepare_durable_restart_proof(actor="codex_external", reason="unit-test")

        self.assertEqual("prepared", payload["phase"])
        self.assertFalse(payload["passed"])
        self.assertEqual(1, payload["pre_restart"]["effect_marker_count"])
        self.assertTrue(self.artifact_path.exists())

    def test_finalize_marks_restart_proof_passed_when_checkpoint_survives(self) -> None:
        saver = _FakeSaver()
        with (
            patch("athanor_agents.restart_proof.durable_restart_proof_path", return_value=self.artifact_path),
            patch(
                "athanor_agents.restart_proof._materialize_durable_checkpointer",
                return_value=(saver, {"configured": True, "durable": True, "mode": "postgres"}),
            ),
        ):
            prepared = restart_proof.prepare_durable_restart_proof(actor="codex_external", reason="unit-test")

        with (
            patch("athanor_agents.restart_proof.durable_restart_proof_path", return_value=self.artifact_path),
            patch(
                "athanor_agents.restart_proof._materialize_durable_checkpointer",
                return_value=(saver, {"configured": True, "durable": True, "mode": "postgres"}),
            ),
            patch("athanor_agents.restart_proof.reset_checkpointer_cache"),
            patch(
                "athanor_agents.restart_proof._fetch_local_health_snapshot",
                return_value={
                    "status": "degraded",
                    "persistence": {"durable": True, "mode": "postgres"},
                    "bootstrap": {"mode": "ready"},
                },
            ),
        ):
            result = restart_proof.finalize_durable_restart_proof(prepared["proof_id"], actor="codex_external", reason="unit-test")

        self.assertEqual("verified", result["phase"])
        self.assertTrue(result["passed"])
        self.assertEqual(1, result["post_restart"]["effect_marker_count"])

    def test_prepare_fails_closed_when_runtime_is_not_durable(self) -> None:
        with (
            patch("athanor_agents.restart_proof.durable_restart_proof_path", return_value=self.artifact_path),
            patch(
                "athanor_agents.restart_proof._materialize_durable_checkpointer",
                return_value=(object(), {"configured": True, "durable": False, "mode": "memory_fallback", "reason": "not durable"}),
            ),
        ):
            payload = restart_proof.prepare_durable_restart_proof(actor="codex_external", reason="unit-test")

        self.assertFalse(payload["passed"])
        self.assertEqual("prepared", payload["phase"])
        self.assertIn("not using durable persistence", payload["detail"])


if __name__ == "__main__":
    unittest.main()
