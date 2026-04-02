import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.agent_registry import (  # noqa: E402
    build_agent_metadata,
    get_agent_descriptor,
    get_live_agent_descriptors,
    reset_agent_descriptor_registry_cache,
)
from athanor_agents.tools import GENERAL_ASSISTANT_TOOLS  # noqa: E402
from athanor_agents.tools.coding import CODING_TOOLS  # noqa: E402
from athanor_agents.tools.core_memory import CORE_MEMORY_TOOLS  # noqa: E402
from athanor_agents.tools.creative import CREATIVE_TOOLS  # noqa: E402
from athanor_agents.tools.data_curator import DATA_CURATOR_TOOLS  # noqa: E402
from athanor_agents.tools.execution import FILESYSTEM_TOOLS, SHELL_TOOLS  # noqa: E402
from athanor_agents.tools.home import HOME_TOOLS  # noqa: E402
from athanor_agents.tools.knowledge import KNOWLEDGE_TOOLS  # noqa: E402
from athanor_agents.tools.media import MEDIA_TOOLS  # noqa: E402
from athanor_agents.tools.research import RESEARCH_TOOLS  # noqa: E402
from athanor_agents.tools.stash import STASH_TOOLS  # noqa: E402
from athanor_agents.tools.subscriptions import SUBSCRIPTION_TOOLS  # noqa: E402


class AgentRegistryContractTest(unittest.TestCase):
    def tearDown(self) -> None:
        reset_agent_descriptor_registry_cache()

    def test_live_registry_contains_expected_agents(self) -> None:
        descriptors = get_live_agent_descriptors()
        ids = {str(item["id"]) for item in descriptors}
        self.assertEqual(
            {
                "general-assistant",
                "media-agent",
                "home-agent",
                "creative-agent",
                "research-agent",
                "knowledge-agent",
                "coding-agent",
                "stash-agent",
                "data-curator",
            },
            ids,
        )

    def test_general_assistant_registry_removes_write_file(self) -> None:
        descriptor = get_agent_descriptor("general-assistant")
        self.assertIsNotNone(descriptor)
        tools = {str(tool) for tool in descriptor.get("tools", [])}
        self.assertNotIn("write_file", tools)
        self.assertIn("search_knowledge", tools)
        self.assertIn("query_infrastructure", tools)

    def test_build_agent_metadata_preserves_schedule_for_cadenced_agents(self) -> None:
        metadata = build_agent_metadata()
        self.assertEqual("every 15 min", metadata["media-agent"]["schedule"])
        self.assertEqual("every 5 min", metadata["home-agent"]["schedule"])
        self.assertEqual("every 6 hours", metadata["data-curator"]["schedule"])
        self.assertNotIn("schedule", metadata["general-assistant"])
        self.assertEqual(["operator_control"], metadata["general-assistant"]["owner_domains"])
        self.assertIn("knowledge", metadata["research-agent"]["support_domains"])

    def test_media_agent_registry_includes_indexer_and_downloader_tools(self) -> None:
        descriptor = get_agent_descriptor("media-agent")
        self.assertIsNotNone(descriptor)
        tools = {str(tool) for tool in descriptor.get("tools", [])}
        self.assertTrue(
            {
                "get_prowlarr_health",
                "get_sabnzbd_queue",
                "pause_sabnzbd_queue",
                "resume_sabnzbd_queue",
            }
            <= tools
        )

    def test_registry_path_override_is_supported(self) -> None:
        override_path = PROJECT_ROOT / "tests" / "_tmp_agent_registry.json"
        override_path.write_text(
            json.dumps(
                {
                    "agents": [
                        {
                            "id": "test-agent",
                            "label": "Test Agent",
                            "description": "Test descriptor",
                            "icon": "terminal",
                            "status": "live",
                            "type": "reactive",
                            "cadence": "on-demand",
                            "tools": ["read_file"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            with patch("athanor_agents.agent_registry.settings.agent_descriptor_path", str(override_path)):
                reset_agent_descriptor_registry_cache()
                descriptors = get_live_agent_descriptors()
            self.assertEqual(["test-agent"], [descriptor["id"] for descriptor in descriptors])
        finally:
            override_path.unlink(missing_ok=True)

    def test_registry_tool_lists_match_runtime_agent_bundles(self) -> None:
        expected_tool_bundles = {
            "general-assistant": GENERAL_ASSISTANT_TOOLS + CORE_MEMORY_TOOLS,
            "media-agent": MEDIA_TOOLS,
            "home-agent": HOME_TOOLS,
            "creative-agent": CREATIVE_TOOLS + CORE_MEMORY_TOOLS,
            "research-agent": RESEARCH_TOOLS + SUBSCRIPTION_TOOLS,
            "knowledge-agent": KNOWLEDGE_TOOLS + CORE_MEMORY_TOOLS,
            "coding-agent": CODING_TOOLS + FILESYSTEM_TOOLS + SHELL_TOOLS + SUBSCRIPTION_TOOLS,
            "stash-agent": STASH_TOOLS,
            "data-curator": DATA_CURATOR_TOOLS,
        }

        for agent_id, tools in expected_tool_bundles.items():
            descriptor = get_agent_descriptor(agent_id)
            self.assertIsNotNone(descriptor, f"Missing registry descriptor for {agent_id}")
            expected_names = [tool.name for tool in tools]
            self.assertEqual(expected_names, descriptor.get("tools", []), f"Tool drift detected for {agent_id}")


if __name__ == "__main__":
    unittest.main()
