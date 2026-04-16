"""Core memory tools — agents read and update their own persona blocks.

These tools give agents self-awareness and the ability to learn from
interactions by updating their own core memory in Redis.
"""

import asyncio
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async function from sync tool context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an event loop — use a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@tool
def read_my_memory(agent_name: str) -> str:
    """Read your own core memory — your bio, directives, learned preferences, and style notes.

    Use this to recall what you know about yourself and how you should behave.
    Pass your own agent name (e.g., 'general-assistant', 'knowledge-agent').
    """
    from ..core_memory import get_core_memory

    try:
        memory = _run_async(get_core_memory(agent_name))
    except Exception as e:
        return f"Error reading core memory: {e}"

    if not memory or not memory.get("bio"):
        return f"No core memory found for {agent_name}."

    lines = [f"Core Memory for {agent_name}:"]
    lines.append(f"\nBio: {memory.get('bio', '')}")

    directives = memory.get("directives", [])
    if directives:
        lines.append("\nDirectives:")
        for d in directives:
            lines.append(f"  - {d}")

    prefs = memory.get("learned_preferences", {})
    if prefs:
        lines.append("\nLearned Preferences:")
        for k, v in prefs.items():
            lines.append(f"  - {k}: {v}")

    style = memory.get("style_notes", "")
    if style:
        lines.append(f"\nStyle: {style}")

    return "\n".join(lines)


@tool
def update_my_memory(agent_name: str, field: str, value: str) -> str:
    """Update a field in your own core memory. Use this to learn and remember.

    Pass your own agent name, the field to update, and the new value.

    Fields:
    - 'bio': Your role description (string)
    - 'directives': A new directive to add (string, gets appended to list)
    - 'learned_preferences': A key=value preference to remember (format: 'key=value')
    - 'style_notes': How you communicate (string, replaces current)

    Examples:
    - update_my_memory('knowledge-agent', 'learned_preferences', 'citation_style=APA')
    - update_my_memory('general-assistant', 'directives', 'Always check GPU temps before reporting all-clear')
    - update_my_memory('media-agent', 'learned_preferences', 'preferred_quality=1080p')
    """
    from ..core_memory import update_core_memory

    valid_fields = {"bio", "directives", "learned_preferences", "style_notes"}
    if field not in valid_fields:
        return f"Invalid field '{field}'. Must be one of: {', '.join(sorted(valid_fields))}"

    # Parse learned_preferences from 'key=value' format
    parsed_value: str | dict = value
    if field == "learned_preferences":
        if "=" in value:
            k, v = value.split("=", 1)
            parsed_value = {k.strip(): v.strip()}
        else:
            return "For learned_preferences, use 'key=value' format (e.g., 'preferred_quality=1080p')"

    try:
        updated = _run_async(update_core_memory(agent_name, field, parsed_value))
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error updating core memory: {e}"

    return f"Core memory updated for {agent_name}. Field '{field}' has been {'appended to' if field == 'directives' else 'updated'}."


CORE_MEMORY_TOOLS = [read_my_memory, update_my_memory]
