import importlib.util
import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Mock langchain_core before importing — not installed on DEV
if "langchain_core" not in sys.modules:
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

# Import prompting.py directly to avoid agents/__init__.py pulling in
# langchain_openai and other heavy deps not installed on DEV.
_spec = importlib.util.spec_from_file_location(
    "athanor_agents.agents.prompting",
    SRC_ROOT / "athanor_agents" / "agents" / "prompting.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_system_prompt = _mod.build_system_prompt
PREFERENCE_PREAMBLE = _mod.PREFERENCE_PREAMBLE


class BuildSystemPromptTests(unittest.TestCase):
    @staticmethod
    def _expected_prompt(prompt: str) -> str:
        return prompt + "\n" + PREFERENCE_PREAMBLE

    def test_prepends_system_prompt_to_existing_messages(self):
        prompt = build_system_prompt("System first")

        result = prompt({"messages": [HumanMessage(content="hello")]})

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], SystemMessage)
        self.assertEqual(result[0].content, self._expected_prompt("System first"))
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
        self.assertEqual(result[0].content, self._expected_prompt("Canonical system"))
        self.assertEqual(result[1].content, "older user")
        self.assertEqual(result[2].content, "latest user")


if __name__ == "__main__":
    unittest.main()
