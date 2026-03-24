import json
import os
import tempfile
import unittest
import asyncio
from unittest.mock import AsyncMock, patch

import athanor_agents.model_governance as model_governance
from athanor_agents.model_governance import (
    build_model_governance_snapshot,
    build_live_model_governance_snapshot,
    get_command_rights_registry,
    get_model_intelligence_lane,
    get_model_proving_ground,
    get_model_role_registry,
    get_policy_class_registry,
    get_workload_class_registry,
)


class ModelGovernanceTests(unittest.TestCase):
    def tearDown(self):
        model_governance._load_registry.cache_clear()
        os.environ.pop("ATHANOR_REGISTRY_DIR", None)

    def test_registries_load(self):
        self.assertGreater(len(get_command_rights_registry()["profiles"]), 0)
        self.assertGreater(len(get_policy_class_registry()["classes"]), 0)
        self.assertGreater(len(get_model_role_registry()["roles"]), 0)
        self.assertGreater(len(get_workload_class_registry()["classes"]), 0)

    def test_proving_ground_has_promotion_path(self):
        proving_ground = get_model_proving_ground()
        self.assertIn("promotion_path", proving_ground)
        self.assertGreater(len(proving_ground["promotion_path"]), 0)

    def test_model_intelligence_has_cadence(self):
        intelligence = get_model_intelligence_lane()
        self.assertIn("cadence", intelligence)
        self.assertIn("weekly_horizon_scan", intelligence["cadence"])

    def test_snapshot_counts_match_registries(self):
        snapshot = build_model_governance_snapshot()
        self.assertEqual(snapshot["role_count"], len(snapshot["role_registry"]))
        self.assertEqual(snapshot["workload_count"], len(snapshot["workload_registry"]))
        self.assertEqual(len(snapshot["champion_summary"]), snapshot["role_count"])
        self.assertIn("governance_layers", snapshot)
        self.assertGreater(
            len(snapshot["governance_layers"]["contract_registry"]["contracts"]),
            0,
        )
        self.assertGreater(
            len(snapshot["governance_layers"]["eval_corpora"]["corpora"]),
            0,
        )

    def test_live_snapshot_exposes_runtime_intelligence(self):
        with patch(
            "athanor_agents.scheduler.get_model_intelligence_cadence",
            AsyncMock(return_value=[]),
        ):
            snapshot = asyncio.run(build_live_model_governance_snapshot())
        self.assertIn("proving_ground", snapshot)
        self.assertIn("promotion_controls", snapshot)
        self.assertIn("retirement_controls", snapshot)
        self.assertIn("model_intelligence", snapshot)
        self.assertIn("candidate_queue", snapshot["model_intelligence"])
        self.assertIn("next_actions", snapshot["model_intelligence"])
        self.assertIn("governance_layers", snapshot)
        self.assertIn("recent_experiments", snapshot["governance_layers"]["experiment_ledger"])
        self.assertIn("deprecation_retirement", snapshot["governance_layers"])

    def test_registry_dir_supports_env_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_dir = os.path.join(tmpdir, "custom")
            os.makedirs(registry_dir, exist_ok=True)
            target = os.path.join(registry_dir, "command-rights-registry.json")
            with open(target, "w", encoding="utf-8") as handle:
                json.dump({"version": "test", "profiles": [{"id": "sample"}]}, handle)

            os.environ["ATHANOR_REGISTRY_DIR"] = registry_dir
            model_governance._load_registry.cache_clear()

            self.assertEqual(
                model_governance._registry_dir("command-rights-registry.json"),
                model_governance.Path(registry_dir),
            )
            self.assertEqual(
                get_command_rights_registry()["profiles"][0]["id"],
                "sample",
            )


if __name__ == "__main__":
    unittest.main()
