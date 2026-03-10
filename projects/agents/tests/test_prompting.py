import unittest

from langchain_core.messages import HumanMessage, SystemMessage

from athanor_agents.agents.prompting import build_system_prompt


class BuildSystemPromptTests(unittest.TestCase):
    def test_prepends_system_prompt_to_existing_messages(self):
        prompt = build_system_prompt("System first")

        result = prompt({"messages": [HumanMessage(content="hello")]})

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], SystemMessage)
        self.assertEqual(result[0].content, "System first")
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
        self.assertEqual(result[0].content, "Canonical system")
        self.assertEqual(result[1].content, "older user")
        self.assertEqual(result[2].content, "latest user")


if __name__ == "__main__":
    unittest.main()
