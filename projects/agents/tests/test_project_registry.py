import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.config import Settings
from athanor_agents.projects import (
    build_project_registry,
    get_project,
    get_project_definitions,
    get_project_summaries,
)


class ProjectRegistryTest(unittest.TestCase):
    def test_registry_exposes_active_core_and_first_tenant(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_EOQ_URL": "http://workshop.internal:3002",
                "ATHANOR_PLEX_URL": "http://vault.internal:32400",
            },
            clear=True,
        ):
            registry = build_project_registry(Settings())

        self.assertEqual(
            {"athanor", "eoq", "kindred", "ulrich-energy", "media"},
            set(registry),
        )
        self.assertTrue(registry["athanor"].first_class)
        self.assertTrue(registry["eoq"].first_class)
        self.assertFalse(registry["kindred"].first_class)
        self.assertEqual("http://workshop.internal:3002", registry["eoq"].external_url)
        self.assertEqual("http://vault.internal:32400/web", registry["media"].external_url)

    def test_workplanner_projection_preserves_task_generation_fields(self) -> None:
        definitions = get_project_definitions()

        self.assertIn("needs", definitions["athanor"])
        self.assertGreaterEqual(len(definitions["eoq"]["needs"]), 3)
        self.assertIn("creative-agent", definitions["eoq"]["agents"])
        self.assertEqual("projects/eoq/ (Workshop app lane)", definitions["eoq"]["location"])

    def test_api_summary_and_detail_contracts_include_platform_metadata(self) -> None:
        summaries = get_project_summaries()
        detail = get_project("ulrich-energy")

        self.assertEqual("tenant", summaries["eoq"]["kind"])
        self.assertEqual("eoq", summaries["eoq"]["lens"])
        self.assertEqual("/projects?project=ulrich-energy", summaries["ulrich-energy"]["primary_route"])
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual("archive", detail["kind"])
        self.assertEqual("retired", detail["status"])
        self.assertEqual(0, len(detail["needs"]))
        self.assertIn("knowledge-agent", detail["operators"])


if __name__ == "__main__":
    unittest.main()
