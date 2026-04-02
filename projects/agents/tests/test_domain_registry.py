import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.agent_registry import get_agent_descriptors  # noqa: E402
from athanor_agents.domain_registry import (  # noqa: E402
    get_domain_packet,
    get_live_domain_packets,
    reset_domain_packet_registry_cache,
)


class DomainRegistryContractTest(unittest.TestCase):
    def tearDown(self) -> None:
        reset_domain_packet_registry_cache()

    def test_live_domain_registry_contains_expected_domains(self) -> None:
        packets = get_live_domain_packets()
        ids = {str(item["id"]) for item in packets}
        self.assertEqual(
            {
                "operator_control",
                "product_foundry",
                "research",
                "knowledge",
                "personal_data",
                "media",
                "home",
                "creative",
                "stash",
            },
            ids,
        )

    def test_media_domain_packet_captures_full_live_stack(self) -> None:
        packet = get_domain_packet("media")
        self.assertIsNotNone(packet)
        self.assertEqual("media-agent", packet.get("owner_agent"))
        self.assertEqual(
            ["sonarr", "radarr", "prowlarr", "sabnzbd", "tautulli", "plex"],
            packet.get("systems"),
        )

    def test_agent_registry_domains_resolve_to_live_domain_packets(self) -> None:
        live_domain_ids = {packet["id"] for packet in get_live_domain_packets()}
        for descriptor in get_agent_descriptors():
            declared_domains = [
                *descriptor.get("owner_domains", []),
                *descriptor.get("support_domains", []),
            ]
            self.assertTrue(declared_domains, f"{descriptor['id']} should declare at least one domain")
            for domain_id in declared_domains:
                self.assertIn(
                    domain_id,
                    live_domain_ids,
                    f"{descriptor['id']} references unknown domain {domain_id!r}",
                )

    def test_registry_path_override_is_supported(self) -> None:
        override_path = PROJECT_ROOT / "tests" / "_tmp_domain_registry.json"
        override_path.write_text(
            json.dumps(
                {
                    "domains": [
                        {
                            "id": "test-domain",
                            "label": "Test Domain",
                            "status": "live",
                            "owner_agent": "general-assistant",
                            "support_agents": [],
                            "systems": ["dashboard"],
                            "surfaces": ["/"],
                            "description": "Temporary domain override for test coverage.",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            with patch("athanor_agents.domain_registry.settings.domain_packet_path", str(override_path)):
                reset_domain_packet_registry_cache()
                packets = get_live_domain_packets()
            self.assertEqual(["test-domain"], [packet["id"] for packet in packets])
        finally:
            override_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
