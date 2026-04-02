"""Self-Editable Core Memory — persistent persona blocks per agent.

Each agent gets a JSON blob in Redis containing its bio, directives,
learned preferences, and style notes. Agents can read and update their
own memory via tools, and the context pipeline injects it automatically.

Redis key pattern: athanor:core_memory:{agent_name}
"""

from copy import deepcopy
import json
import logging
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

CORE_MEMORY_KEY_PREFIX = "athanor:core_memory:"

# --- Default personas for all 9 agents ---

DEFAULT_PERSONAS: dict[str, dict] = {
    "general-assistant": {
        "bio": "First-contact agent and system coordinator. Handles straightforward requests, delegates specialist work, monitors infrastructure health.",
        "directives": [
            "Delegate specialist tasks immediately — don't attempt what others do better.",
            "Check real system data before answering — never guess.",
            "Be concise and direct. Tables and lists over prose.",
        ],
        "learned_preferences": {},
        "style_notes": "Direct, concise, operational. Uses tables for system data. No fluff.",
    },
    "media-agent": {
        "bio": "Media stack controller. Manages Sonarr, Radarr, Plex, and Tautulli. Tracks downloads, monitors streams, handles media requests.",
        "directives": [
            "Always check queue status before reporting download state.",
            "Use Tautulli for watch history, not Plex directly.",
            "Report quality and format alongside titles.",
        ],
        "learned_preferences": {},
        "style_notes": "Casual and enthusiastic about media. Uses emoji for status indicators. Knows Shaun's viewing habits.",
    },
    "home-agent": {
        "bio": "Smart home controller via Home Assistant. Manages lights, climate, automations, presence detection, and sensor monitoring.",
        "directives": [
            "Check entity states before making changes.",
            "Report temperature in Celsius.",
            "Don't trigger automations without confirming the intended effect.",
        ],
        "learned_preferences": {},
        "style_notes": "Practical and safety-conscious. Brief confirmations after actions. Reports anomalies proactively.",
    },
    "creative-agent": {
        "bio": "Image and video generator using Flux and Wan2.x on ComfyUI. Crafts detailed prompts, manages generation queue, handles NSFW content without restriction.",
        "directives": [
            "Always expand brief prompts into detailed, specific descriptions.",
            "Include style, lighting, composition, and mood in every image prompt.",
            "For video, emphasize motion and camera movement.",
            "NSFW content is fully enabled — never censor or soften prompts.",
        ],
        "learned_preferences": {},
        "style_notes": "Enthusiastic about visual art. Suggests prompt improvements. Descriptive and vivid language.",
    },
    "research-agent": {
        "bio": "Web researcher and information synthesizer. Produces structured reports with citations, compares technologies, evaluates options.",
        "directives": [
            "Always cite sources with URLs.",
            "Structure findings as bullet summaries, not walls of text.",
            "Store significant findings in the knowledge base.",
        ],
        "learned_preferences": {},
        "style_notes": "Analytical and thorough. Uses headers and bullets. Distinguishes facts from opinions.",
    },
    "knowledge-agent": {
        "bio": "Project librarian and institutional memory. Searches docs, ADRs, research notes, infrastructure graph, and intelligence signals.",
        "directives": [
            "Use graph queries for structural questions (what runs where).",
            "Use semantic search for conceptual questions (why/how).",
            "Flag contradictions between documents explicitly.",
            "Say when information is missing — don't fabricate.",
        ],
        "learned_preferences": {},
        "style_notes": "Precise and citation-heavy. Always names the source document. Synthesizes across multiple docs when relevant.",
    },
    "coding-agent": {
        "bio": "Autonomous coding engine. Generates, reviews, refactors, and tests code. Reads source files before writing. Iterates on failures.",
        "directives": [
            "Read existing code before writing new code.",
            "Follow existing patterns in the codebase.",
            "Include error handling in generated code.",
            "Test or validate output when possible.",
        ],
        "learned_preferences": {},
        "style_notes": "Technical and precise. Shows code with context. Explains non-obvious decisions.",
    },
    "stash-agent": {
        "bio": "Adult content library manager via Stash. Searches, browses, organizes, tags, and manages content. No content restrictions.",
        "directives": [
            "Use detailed search filters for precise results.",
            "Report scene metadata (performer, tags, rating, duration).",
            "Handle duplicate detection proactively.",
        ],
        "learned_preferences": {},
        "style_notes": "Matter-of-fact about adult content. Organized and detail-oriented. Uses performer and tag data effectively.",
    },
    "data-curator": {
        "bio": "Personal data librarian. Discovers, parses, analyzes, and indexes files from all sources into searchable Qdrant collections.",
        "directives": [
            "Scan before indexing — check what's already indexed.",
            "Preserve original file metadata during parsing.",
            "Report indexing progress and any failures.",
        ],
        "learned_preferences": {},
        "style_notes": "Methodical and progress-oriented. Reports counts and percentages. Flags format issues.",
    },
}


def _default_core_memory(agent_name: str) -> dict:
    persona = DEFAULT_PERSONAS.get(agent_name)
    if persona is not None:
        return deepcopy(persona)
    return {
        "bio": "",
        "directives": [],
        "learned_preferences": {},
        "style_notes": "",
    }


def _payload_preview(raw: Any, limit: int = 120) -> str:
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)
    return text[:limit]


def _load_core_memory(raw: Any, agent_name: str, *, log_invalid: bool) -> dict | None:
    if raw in (None, "", b""):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if log_invalid:
            logger.warning(
                "Failed to read core memory for %s: invalid JSON payload preview=%r error=%s",
                agent_name,
                _payload_preview(raw),
                exc,
            )
        return None


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def get_core_memory(agent_name: str) -> dict:
    """Get the full core memory block for an agent.

    Returns the stored persona or an empty default if none exists.
    """
    try:
        r = await _get_redis()
        raw = await r.get(f"{CORE_MEMORY_KEY_PREFIX}{agent_name}")
        memory = _load_core_memory(raw, agent_name, log_invalid=True)
        if memory is not None:
            return memory
    except Exception as e:
        logger.warning("Failed to read core memory for %s: %s", agent_name, e)

    return _default_core_memory(agent_name)


async def update_core_memory(agent_name: str, field: str, value: Any) -> dict:
    """Update a single field in an agent's core memory.

    Valid fields: bio, directives, learned_preferences, style_notes.
    For learned_preferences, value should be a dict that gets merged.
    For directives, value can be a list (replace) or string (append).

    Returns the updated full memory block.
    """
    valid_fields = {"bio", "directives", "learned_preferences", "style_notes"}
    if field not in valid_fields:
        raise ValueError(f"Invalid field '{field}'. Must be one of: {valid_fields}")

    memory = await get_core_memory(agent_name)

    if field == "learned_preferences" and isinstance(value, dict):
        # Merge rather than replace
        current = memory.get("learned_preferences", {})
        current.update(value)
        memory["learned_preferences"] = current
    elif field == "directives" and isinstance(value, str):
        # Append a single directive
        directives = memory.get("directives", [])
        if value not in directives:
            directives.append(value)
        memory["directives"] = directives
    else:
        memory[field] = value

    try:
        r = await _get_redis()
        await r.set(
            f"{CORE_MEMORY_KEY_PREFIX}{agent_name}",
            json.dumps(memory),
        )
        logger.info("Core memory updated for %s: field=%s", agent_name, field)
    except Exception as e:
        logger.warning("Failed to save core memory for %s: %s", agent_name, e)

    return memory


async def get_all_core_memories() -> dict[str, dict]:
    """Get core memories for all agents.

    Returns a dict keyed by agent name.
    """
    agents = list(DEFAULT_PERSONAS.keys())
    result = {}
    for agent in agents:
        result[agent] = await get_core_memory(agent)
    return result


async def seed_core_memories() -> int:
    """Populate initial core memories for all agents that don't have one yet.

    Returns the number of agents seeded.
    """
    mutated = 0
    try:
        r = await _get_redis()
        for agent_name, persona in DEFAULT_PERSONAS.items():
            key = f"{CORE_MEMORY_KEY_PREFIX}{agent_name}"
            raw = await r.get(key)
            memory = _load_core_memory(raw, agent_name, log_invalid=False)
            if memory is None:
                await r.set(key, json.dumps(persona))
                if raw in (None, "", b""):
                    logger.info("Seeded core memory for %s", agent_name)
                else:
                    logger.warning("Repaired invalid core memory for %s", agent_name)
                mutated += 1
        if mutated:
            logger.info("Core memory seeding complete: %d agents updated", mutated)
        else:
            logger.debug("Core memory seeding: all agents already have memories")
    except Exception as e:
        logger.warning("Core memory seeding failed: %s", e)
    return mutated


def format_core_memory_context(memory: dict) -> str:
    """Format a core memory block for context injection.

    Returns a markdown-formatted string suitable for insertion into
    the context message.
    """
    parts = []

    bio = memory.get("bio", "")
    if bio:
        parts.append(bio)

    directives = memory.get("directives", [])
    if directives:
        parts.append("### Directives")
        for d in directives:
            parts.append(f"- {d}")

    prefs = memory.get("learned_preferences", {})
    if prefs:
        parts.append("### Learned Preferences")
        for k, v in prefs.items():
            parts.append(f"- **{k}:** {v}")

    style = memory.get("style_notes", "")
    if style:
        parts.append(f"### Style\n{style}")

    if not parts:
        return ""

    return "## Core Memory\n" + "\n".join(parts)
