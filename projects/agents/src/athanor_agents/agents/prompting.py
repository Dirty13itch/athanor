from collections.abc import Callable

from langchain_core.messages import BaseMessage, SystemMessage


def build_system_prompt(prompt: str) -> Callable[[dict], list[BaseMessage]]:
    """Ensure agent prompts stay first even when LangGraph rehydrates state."""

    def apply_prompt(state: dict) -> list[BaseMessage]:
        messages = state.get("messages", [])
        ordered_messages = [
            message for message in messages if not isinstance(message, SystemMessage)
        ]
        return [SystemMessage(content=prompt), *ordered_messages]

    return apply_prompt
