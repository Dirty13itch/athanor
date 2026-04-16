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
                            {"provider_id": "deepseek_api", "status": "observed", "observed_at": "2026-04-01T03:38:18Z"},
                            {
                                "provider_id": "openai_api",
                                "status": "observed",
                                "observed_at": "2026-03-31T03:38:18Z",
                            },
                            {
                                "provider_id": "openai_api",
                                "status": "auth_failed",
                                "observed_at": "2026-04-02T03:38:18Z",
                                "requested_model": "gpt",
                                "error_snippet": "AuthenticationError: incorrect api key provided",
                            },
                            {"provider_id": "moonshot_api", "status": "auth_failed", "observed_at": "2026-04-01T03:38:18Z"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (reports_dir / "vault-litellm-env-audit.json").write_text(
                json.dumps(
                    {
                        "container_missing_env_names": [],
                        "container_present_env_names": ["OPENAI_API_KEY"],
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
                patch(
                    "athanor_agents.launch_governance.get_provider_catalog_snapshot",
                    return_value={
                        "providers": [
                            {
                                "id": "deepseek_api",
                                "label": "DeepSeek API",
                                "evidence_posture": "vault_provider_specific_api_observed",
                                "pricing_truth_label": "metered_api",
                                "env_contracts": ["DEEPSEEK_API_KEY"],
                                "evidence": {"proxy": {"alias": "deepseek"}},
                            },
                            {
                                "id": "openai_api",
                                "label": "OpenAI API",
                                "evidence_posture": "vault_provider_specific_auth_failed",
                                "pricing_truth_label": "metered_api",
                                "env_contracts": ["OPENAI_API_KEY"],
                                "evidence": {"proxy": {"alias": "gpt"}},
                            },
                            {
                                "id": "moonshot_kimi",
                                "label": "Kimi Code",
                                "evidence_posture": "live_burn_observed_cost_unverified",
                                "pricing_truth_label": "flat_rate_unverified",
                                "verification_steps": [
                                    "Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.",
                                    "Keep this lane cost-unverified until the billing tier is proven from a current runtime-visible or operator-visible surface.",
                                ],
                            },
                        ]
                    },
                ),
            ):
                posture = build_launch_governance_posture()

        self.assertTrue(posture["provider_evidence"]["exists"])
        self.assertEqual(4, posture["provider_evidence"]["capture_count"])
        self.assertEqual(3, posture["provider_evidence"]["latest_provider_capture_count"])
        self.assertEqual(1, posture["provider_evidence"]["observed_count"])
        self.assertEqual(2, posture["provider_evidence"]["auth_failed_count"])
        self.assertEqual(2, posture["provider_evidence"]["weak_lane_count"])
        self.assertEqual(
            ["moonshot_kimi", "openai_api"],
            [item["provider_id"] for item in posture["provider_evidence"]["verification_queue"]],
        )
        self.assertEqual(["openai_api"], posture["provider_evidence"]["auth_failed_provider_ids"])
        self.assertEqual(["moonshot_kimi"], posture["provider_evidence"]["cost_unverified_provider_ids"])
        self.assertIn("OPENAI_API_KEY", posture["provider_evidence"]["verification_queue"][1]["next_verification"])
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
            patch(
                "athanor_agents.launch_governance.get_provider_catalog_snapshot",
                return_value={"providers": []},
            ),
        ):
            posture = build_launch_governance_posture()

        self.assertIn("providers:evidence_missing", posture["launch_blockers"])
        self.assertEqual(
            sorted(launch_governance.REQUIRED_LAUNCH_RUNBOOK_IDS - {"constrained-mode", "degraded-mode"}),
            posture["missing_runbook_ids"],
        )
