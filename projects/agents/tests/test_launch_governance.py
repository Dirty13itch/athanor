from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import athanor_agents.launch_governance as launch_governance
from athanor_agents.launch_governance import build_launch_governance_posture


class LaunchGovernanceTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("ATHANOR_REPORTS_DIR", None)
        os.environ.pop("ATHANOR_RUNTIME_ARTIFACT_ROOT", None)

    def test_build_launch_governance_posture_reads_provider_evidence_from_runtime_reports_dir(self) -> None:
        with TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports" / "truth-inventory"
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "provider-usage-evidence.json").write_text(
                json.dumps(
                    {
                        "captures": [
                            {"provider": "deepseek_api", "status": "observed"},
                            {"provider": "openai_api", "status": "auth_failed"},
                            {"provider": "moonshot_api", "status": "auth_failed"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            os.environ["ATHANOR_REPORTS_DIR"] = str(reports_dir)

            with (
                patch(
                    "athanor_agents.launch_governance.get_current_autonomy_phase",
                    return_value=(
                        {"activation_state": "software_core_active", "current_phase_id": "software_core_phase_1"},
                        {"status": "active"},
                    ),
                ),
                patch("athanor_agents.launch_governance.get_next_autonomy_phase", return_value={"id": "expanded_core_phase_2", "status": "blocked"}),
                patch("athanor_agents.launch_governance.get_unmet_autonomy_prerequisites", side_effect=[[], [{"id": "vault_provider_auth_repair"}]]),
                patch(
                    "athanor_agents.launch_governance.get_operator_runbooks_registry",
                    return_value={"runbooks": [{"id": item} for item in launch_governance.REQUIRED_LAUNCH_RUNBOOK_IDS]},
                ),
            ):
                posture = build_launch_governance_posture()

        self.assertTrue(posture["provider_evidence"]["exists"])
        self.assertEqual(3, posture["provider_evidence"]["capture_count"])
        self.assertEqual(1, posture["provider_evidence"]["observed_count"])
        self.assertEqual(2, posture["provider_evidence"]["auth_failed_count"])
        self.assertEqual([], posture["missing_runbook_ids"])
        self.assertNotIn("providers:evidence_missing", posture["launch_blockers"])
        self.assertEqual(["vault_provider_auth_repair"], posture["next_phase_blockers"])

    def test_build_launch_governance_posture_uses_registry_truth_for_runbooks(self) -> None:
        with (
            patch(
                "athanor_agents.launch_governance.get_current_autonomy_phase",
                return_value=(
                    {"activation_state": "software_core_active", "current_phase_id": "software_core_phase_1"},
                    {"status": "active"},
                ),
            ),
            patch("athanor_agents.launch_governance.get_next_autonomy_phase", return_value={}),
            patch("athanor_agents.launch_governance.get_unmet_autonomy_prerequisites", return_value=[]),
            patch(
                "athanor_agents.launch_governance.get_operator_runbooks_registry",
                return_value={"runbooks": [{"id": "constrained-mode"}, {"id": "degraded-mode"}]},
            ),
            patch(
                "athanor_agents.launch_governance._provider_usage_evidence_path",
                return_value=Path("Z:/definitely-missing/provider-usage-evidence.json"),
            ),
        ):
            posture = build_launch_governance_posture()

        self.assertIn("providers:evidence_missing", posture["launch_blockers"])
        self.assertEqual(
            sorted(launch_governance.REQUIRED_LAUNCH_RUNBOOK_IDS - {"constrained-mode", "degraded-mode"}),
            posture["missing_runbook_ids"],
        )

