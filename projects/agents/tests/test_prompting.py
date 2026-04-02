import importlib.util
import sys
import types
import unittest
from pathlib import Path

# Mock langchain_core only when the package is genuinely unavailable.
if "langchain_core" not in sys.modules and importlib.util.find_spec("langchain_core") is None:
    class BaseMessage:
        def __init__(self, content=""):
            self.content = content

    class SystemMessage(BaseMessage):
        pass

    class HumanMessage(BaseMessage):
        pass

    _lc = types.ModuleType("langchain_core")
    _lc_msgs = types.ModuleType("langchain_core.messages")
    _lc_msgs.BaseMessage = BaseMessage
    _lc_msgs.SystemMessage = SystemMessage
    _lc_msgs.HumanMessage = HumanMessage
    _lc.messages = _lc_msgs
    sys.modules["langchain_core"] = _lc
    sys.modules["langchain_core.messages"] = _lc_msgs

from langchain_core.messages import HumanMessage, SystemMessage

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "athanor_agents" / "agents" / "prompting.py"

# Import prompting.py directly to avoid agents/__init__.py pulling in
# langchain_openai and other heavy deps not installed on DEV.
_spec = importlib.util.spec_from_file_location(
    "athanor_agents.agents.prompting",
    MODULE_PATH,
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_system_prompt = _mod.build_system_prompt
PREFERENCE_PREAMBLE = _mod.PREFERENCE_PREAMBLE


class BuildSystemPromptTests(unittest.TestCase):
    def test_prepends_system_prompt_to_existing_messages(self):
        prompt = build_system_prompt("System first")

        result = prompt({"messages": [HumanMessage(content="hello")]})

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], SystemMessage)
        self.assertEqual(result[0].content, f"System first\n{PREFERENCE_PREAMBLE}")
        self.assertEqual(result[1].content, "hello")

    def test_strips_rehydrated_system_messages(self):
        prompt = build_system_prompt("Canonical system")

        result = prompt(
            {
                "messages": [
                    HumanMessage(content="older user"),
                    SystemMessage(content="stale system"),
                    HumanMessage(content="latest user"),
                ]
            }
        )

        self.assertEqual(
            [type(message).__name__ for message in result],
            ["SystemMessage", "HumanMessage", "HumanMessage"],
        )
        self.assertEqual(result[0].content, f"Canonical system\n{PREFERENCE_PREAMBLE}")
        self.assertEqual(result[1].content, "older user")
        self.assertEqual(result[2].content, "latest user")


if __name__ == "__main__":
    unittest.main()
