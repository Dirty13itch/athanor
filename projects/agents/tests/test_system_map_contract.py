from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.command_hierarchy import build_system_map_snapshot  # noqa: E402


class SystemMapContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_system_map_includes_domains_and_persistence_truth(self) -> None:
        domains = [
            {
                "id": "media",
                "label": "Media",
                "owner_agent": "media-agent",
                "support_agents": ["general-assistant"],
                "status": "live",
            }
        ]
        operational_governance = {
            "persistence": {
                "mode": "memory_fallback",
                "durable": False,
                "configured": False,
                "driver": "langgraph.checkpoint.memory.InMemorySaver",
                "reason": "ATHANOR_POSTGRES_URL not configured",
                "last_updated_at": "2026-03-31T09:00:00+00:00",
            },
            "durable_state": {
                "mode": "disabled",
                "configured": False,
                "available": False,
                "schema_ready": False,
                "reason": "ATHANOR_POSTGRES_URL not configured",
                "bootstrap_sql_path": "C:/Athanor/projects/agents/src/athanor_agents/sql/bootstrap_durable_state.sql",
                "last_updated_at": "2026-03-31T09:00:00+00:00",
                "last_bootstrap_at": None,
            },
        }

        with (
            patch("athanor_agents.command_hierarchy.get_policy_snapshot", return_value={"providers": {"athanor_local": {}, "openai": {}}}),
            patch("athanor_agents.command_hierarchy._build_constitution_snapshot", return_value={"label": "constitution"}),
            patch("athanor_agents.command_hierarchy._build_operational_governance", new=AsyncMock(return_value=operational_governance)),
            patch("athanor_agents.command_hierarchy._build_registry_versions", return_value={"platform_topology": "test"}),
            patch("athanor_agents.command_hierarchy.build_domain_metadata", return_value=domains),
            patch("athanor_agents.command_hierarchy.get_platform_topology", return_value={"nodes": []}),
            patch("athanor_agents.command_hierarchy.get_project_maturity_registry", return_value={"projects": []}),
            patch("athanor_agents.command_hierarchy.get_docs_lifecycle_registry", return_value={"docs": []}),
            patch("athanor_agents.command_hierarchy.get_program_operating_system", return_value={"name": "Athanor"}),
        ):
            payload = await build_system_map_snapshot(
                {
                    "general-assistant": {
                        "description": "Operator-facing control surface",
                        "tools": ["read_file"],
                        "type": "proactive",
                        "owner_domains": ["operator_control"],
                        "support_domains": ["media", "knowledge"],
                    }
                }
            )

        self.assertEqual(domains, payload["domains"])
        self.assertEqual(operational_governance, payload["operational_governance"])
        self.assertEqual(
            {
                "id": "general-assistant",
                "label": "General Assistant",
                "role": "read-mostly ops, status, and triage",
                "authority": "read, report, delegate",
                "tool_count": 1,
                "mode": "proactive",
                "owner_domains": ["operator_control"],
                "support_domains": ["media", "knowledge"],
                "status": "live",
            },
            payload["specialists"][0],
        )


if __name__ == "__main__":
    unittest.main()
