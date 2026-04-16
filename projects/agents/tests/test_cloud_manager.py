import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.cloud_manager import get_provider_status


class CloudManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_status_projects_catalog_backed_subscription_metadata(self) -> None:
        policy = {
            "providers": {
                "athanor_local": {"role": "sovereign_local", "category": "local"},
                "anthropic_claude_code": {"role": "frontier_supervisor", "category": "subscription"},
                "google_gemini": {"role": "repo_audit_supervisor", "category": "subscription"},
                "moonshot_kimi": {"role": "search_heavy_planning", "category": "subscription"},
                "zai_glm_coding": {"role": "cheap_bulk_transform", "category": "subscription"},
            }
        }
        catalog = {
            "providers": [
                {
                    "id": "athanor_local",
                    "label": "Athanor Local",
                    "subscription_product": "Sovereign local cluster",
                    "monthly_cost_usd": 0,
                    "official_pricing_status": "not_applicable",
                    "category": "local",
                },
                {
                    "id": "anthropic_claude_code",
                    "label": "Claude Code",
                    "subscription_product": "Claude Max",
                    "monthly_cost_usd": 200,
                    "official_pricing_status": "official_verified",
                    "category": "subscription",
                },
                {
                    "id": "google_gemini",
                    "label": "Gemini CLI",
                    "subscription_product": "Google AI Pro / Gemini CLI",
                    "monthly_cost_usd": 20,
                    "official_pricing_status": "official_verified",
                    "category": "subscription",
                },
                {
                    "id": "moonshot_kimi",
                    "label": "Kimi Code",
                    "subscription_product": "Kimi Membership / Kimi Code",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "official-source-present-cost-unverified",
                    "category": "subscription",
                },
                {
                    "id": "zai_glm_coding",
                    "label": "Z.ai GLM Coding",
                    "subscription_product": "GLM Coding Plan",
                    "monthly_cost_usd": None,
                    "official_pricing_status": "official-source-present-cost-unverified",
                    "category": "subscription",
                },
            ]
        }
        posture_records = [
            {
                "provider": "athanor_local",
                "provider_state": "available",
                "availability": "available",
                "execution_mode": "local_runtime",
                "direct_execution_ready": True,
                "governed_handoff_ready": False,
                "lane": "sovereign_local",
                "state_reasons": ["direct_or_local_path_ready"],
            },
            {
                "provider": "anthropic_claude_code",
                "provider_state": "available",
                "availability": "available",
                "execution_mode": "bridge_cli",
                "direct_execution_ready": True,
                "governed_handoff_ready": True,
                "lane": "frontier_supervisor",
                "state_reasons": ["direct_or_local_path_ready"],
            },
            {
                "provider": "google_gemini",
                "provider_state": "available",
                "availability": "available",
                "execution_mode": "direct_cli",
                "direct_execution_ready": True,
                "governed_handoff_ready": True,
                "lane": "repo_audit_supervisor",
                "state_reasons": ["direct_or_local_path_ready"],
            },
            {
                "provider": "moonshot_kimi",
                "provider_state": "available",
                "availability": "available",
                "execution_mode": "direct_cli",
                "direct_execution_ready": True,
                "governed_handoff_ready": True,
                "lane": "search_heavy_planning",
                "state_reasons": ["direct_or_local_path_ready"],
            },
            {
                "provider": "zai_glm_coding",
                "provider_state": "handoff_only",
                "availability": "handoff_only",
                "execution_mode": "handoff_bundle",
                "direct_execution_ready": False,
                "governed_handoff_ready": True,
                "lane": "cheap_bulk_transform",
                "state_reasons": ["handoff_only_execution_path"],
            },
        ]
        cli_stats = {
            "claude_code": {"tasks_today": 2, "last_used": 111.0, "available": True},
            "gemini_cli": {"tasks_today": 4, "quota_remaining": 11, "last_used": 222.0, "available": True},
            "moonshot_kimi": {"tasks_today": 1, "last_used": 333.0, "available": True},
            "zai_glm_coding": {"tasks_today": 0, "last_used": None, "available": False},
        }

        with (
            patch("athanor_agents.cloud_manager.get_cli_status", AsyncMock(return_value=cli_stats)),
            patch("athanor_agents.subscriptions.get_policy_snapshot", return_value=policy),
            patch("athanor_agents.model_governance.get_provider_catalog_registry", return_value=catalog),
            patch(
                "athanor_agents.provider_execution.build_provider_posture_records",
                AsyncMock(return_value=posture_records),
            ),
        ):
            providers = await get_provider_status()

        by_id = {entry["id"]: entry for entry in providers}
        self.assertEqual(
            ["Athanor Local", "Claude Code", "Gemini CLI", "Kimi Code", "Z.ai GLM Coding"],
            [entry["name"] for entry in providers],
        )
        self.assertEqual(200, by_id["anthropic_claude_code"]["monthly_cost"])
        self.assertEqual("official_verified", by_id["anthropic_claude_code"]["pricing_status"])
        self.assertEqual("Claude Max", by_id["anthropic_claude_code"]["subscription"])
        self.assertEqual(4, by_id["google_gemini"]["tasks_today"])
        self.assertEqual(11, by_id["google_gemini"]["quota_remaining"])
        self.assertIsNone(by_id["moonshot_kimi"]["monthly_cost"])
        self.assertEqual(
            "official-source-present-cost-unverified",
            by_id["moonshot_kimi"]["pricing_status"],
        )
        self.assertEqual("handoff_only", by_id["zai_glm_coding"]["provider_state"])
        self.assertFalse(by_id["zai_glm_coding"]["direct_execution_ready"])
        self.assertTrue(by_id["zai_glm_coding"]["governed_handoff_ready"])
