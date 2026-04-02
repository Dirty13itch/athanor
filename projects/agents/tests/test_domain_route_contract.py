from __future__ import annotations

import unittest
from unittest.mock import patch

from athanor_agents import server


class DomainRouteContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_domains_route_returns_registry_backed_domain_metadata(self) -> None:
        domains = [
            {
                "id": "media",
                "label": "Media",
                "description": "Media stack operations.",
                "owner_agent": "media-agent",
                "support_agents": ["general-assistant"],
                "systems": ["sonarr", "radarr", "prowlarr", "sabnzbd", "tautulli", "plex"],
                "surfaces": ["/media", "/services"],
                "status": "live",
            }
        ]
        with patch("athanor_agents.server.build_domain_metadata", return_value=domains) as builder:
            payload = await server.domains_metadata()

        self.assertEqual({"domains": domains}, payload)
        builder.assert_called_once_with()

    async def test_agents_route_exposes_domain_ownership_from_registry_metadata(self) -> None:
        with (
            patch("athanor_agents.server.list_agents", return_value=["general-assistant"]),
            patch(
                "athanor_agents.server.get_agent_metadata",
                return_value={
                    "general-assistant": {
                        "description": "Operator-facing control surface",
                        "tools": ["read_file"],
                        "type": "proactive",
                        "owner_domains": ["operator_control"],
                        "support_domains": ["media", "knowledge"],
                    }
                },
            ),
        ):
            payload = await server.agents_metadata()

        self.assertEqual(
            {
                "agents": [
                    {
                        "name": "general-assistant",
                        "description": "Operator-facing control surface",
                        "tools": ["read_file"],
                        "type": "proactive",
                        "schedule": None,
                        "owner_domains": ["operator_control"],
                        "support_domains": ["media", "knowledge"],
                        "status": "online",
                        "status_note": None,
                    }
                ]
            },
            payload,
        )

    async def test_system_map_route_uses_live_agent_metadata_helper(self) -> None:
        metadata = {
            "general-assistant": {
                "description": "Operator-facing control surface",
                "tools": ["read_file"],
                "type": "proactive",
                "owner_domains": ["operator_control"],
                "support_domains": ["media", "knowledge"],
            }
        }
        with (
            patch("athanor_agents.server.get_agent_metadata", return_value=metadata) as metadata_builder,
            patch("athanor_agents.server.build_system_map_snapshot", return_value={"ok": True}) as snapshot_builder,
        ):
            payload = await server.system_map()

        self.assertEqual({"ok": True}, payload)
        metadata_builder.assert_called_once_with()
        snapshot_builder.assert_called_once_with(metadata)


if __name__ == "__main__":
    unittest.main()
