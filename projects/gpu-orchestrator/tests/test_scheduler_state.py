import asyncio
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gpu_orchestrator.main import build_scheduler_state_projection, scheduler_state


class SchedulerStateProjectionTest(unittest.TestCase):
    def test_projection_exposes_baseline_scheduler_surface(self) -> None:
        payload = build_scheduler_state_projection()

        self.assertEqual(payload["mode"], "observed_projection")
        self.assertEqual(payload["authority"], "gpu-orchestrator")
        self.assertEqual(payload["surface_status"], "baseline_projection")
        self.assertFalse(payload["scheduler_enabled"])
        self.assertEqual(payload["queue_depth"], 0)
        self.assertEqual(payload["active_transitions"], 0)
        self.assertEqual(
            payload["write_capabilities"],
            {"request": False, "preload": False, "release": False},
        )
        self.assertEqual(
            sorted(payload["zones"].keys()),
            ["coder", "coordinator", "embedding", "reranker", "vision", "worker"],
        )
        self.assertFalse(payload["zones"]["embedding"]["auto_sleep_enabled"])
        self.assertEqual(payload["zones"]["embedding"]["sleep_policy"], "always_on")

    def test_projection_collapses_shared_dev_gpu_into_single_slot(self) -> None:
        payload = build_scheduler_state_projection()

        self.assertIn("D:0", payload["gpus"])
        self.assertEqual(payload["gpus"]["D:0"]["zones"], ["embedding", "reranker"])
        self.assertEqual(payload["gpus"]["D:0"]["projection_conflict"], "shared_gpu_multiple_zones")

    def test_route_returns_same_projection_shape(self) -> None:
        payload = asyncio.run(scheduler_state())

        self.assertEqual(payload["surface_status"], "baseline_projection")
        self.assertIn("gpus", payload)
        self.assertIn("zones", payload)


if __name__ == "__main__":
    unittest.main()
