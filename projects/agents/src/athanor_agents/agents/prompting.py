from collections.abc import Callable

from langchain_core.messages import BaseMessage, SystemMessage

PREFERENCE_PREAMBLE = """
IMPORTANT — User preferences and past corrections may be injected into your context.
When you see preference data, adapt your behavior accordingly:
- If a preference says "always use 4K" — prefer 4K options without asking.
- If a preference corrects a past action — don't repeat the corrected behavior.
- If a preference expresses a like/dislike — factor it into recommendations.
Preferences represent learned owner intent. Honor them silently — don't announce that you're following a preference unless asked.
"""


def build_system_prompt(prompt: str) -> Callable[[dict], list[BaseMessage]]:
    """Ensure agent prompts stay first even when LangGraph rehydrates state."""

    full_prompt = prompt + "\n" + PREFERENCE_PREAMBLE

    def apply_prompt(state: dict) -> list[BaseMessage]:
        messages = state.get("messages", [])
        ordered_messages = [
            message for message in messages if not isinstance(message, SystemMessage)
        ]
        return [SystemMessage(content=full_prompt), *ordered_messages]

    return apply_prompt
