"""Intent Capture — extracts actionable directives from owner messages.

When Shaun talks to the Command Center, this module scans his message for
actionable intent and writes it to Redis athanor:intents:operator, where
_mine_operator_intents() picks it up on the next pipeline cycle.

Two modes:
1. Heuristic extraction (fast, no LLM call) — catches explicit directives
2. LLM-assisted extraction (async, fire-and-forget) — catches implicit intent

Also provides a direct steering API for explicit goal/priority injection.
"""

import json
import logging
import re
import time

logger = logging.getLogger(__name__)

# Patterns that indicate the user is giving a directive, not just chatting
DIRECTIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(?:i want|i need|i'd like|make sure|please|go ahead and|start|begin|do|build|create|generate|deploy|fix|update|add|remove|set up|configure|research|find|check|verify|ensure)\b",
        r"\b(?:should always|should never|from now on|going forward|priority is|focus on|work on|don't bother with|stop doing|keep doing)\b",
        r"\b(?:all queens|every queen|all agents|the system should|the pipeline should)\b",
        r"\b(?:highest priority|top priority|urgent|asap|right now|immediately|before anything else)\b",
    ]
]

# Patterns that indicate this is just a question, not a directive
QUESTION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(?:what|how|why|when|where|who|can you|could you|is there|are there|do you|does|did|has|have|should)\b.*\?$",
        r"^(?:tell me|explain|describe|show me|what's|how's)\b",
    ]
]


def extract_directive(message: str) -> str | None:
    """Fast heuristic extraction — returns the actionable text if found, else None."""
    text = message.strip()
    if not text or len(text) < 10:
        return None

    # Skip pure questions
    for pattern in QUESTION_PATTERNS:
        if pattern.search(text):
            return None

    # Check for directive patterns
    for pattern in DIRECTIVE_PATTERNS:
        if pattern.search(text):
            return text

    return None


async def capture_intent_from_chat(
    user_message: str,
    agent_response: str = "",
    agent_name: str = "general-assistant",
) -> bool:
    """Extract and store operator intents from a Command Center chat message.

    Called as fire-and-forget after chat response is delivered.
    Returns True if an intent was captured.
    """
    directive = extract_directive(user_message)
    if not directive:
        return False

    try:
        from .workspace import get_redis
        r = await get_redis()

        intent_entry = json.dumps({
            "text": directive[:500],
            "source": "command_center_chat",
            "agent": agent_name,
            "captured_at": time.time(),
        })

        # Push to the operator intents list (capped at 50)
        await r.lpush("athanor:intents:operator", directive[:500])
        await r.ltrim("athanor:intents:operator", 0, 49)

        logger.info("Captured operator intent from chat: %s", directive[:100])
        return True

    except Exception as e:
        logger.debug("Intent capture failed: %s", e)
        return False


async def inject_steering_intent(
    text: str,
    priority: float = 0.9,
    source: str = "direct_steering",
    trigger_cycle: bool = False,
) -> dict:
    """Directly inject a high-priority intent into the pipeline.

    This is the explicit steering mechanism — when Shaun says
    "do this" through the dashboard or API.

    Args:
        text: The directive text.
        priority: Priority hint (0-1). Default 0.9 (very high).
        source: Where this came from (dashboard, api, mobile, etc.)
        trigger_cycle: If True, immediately trigger a pipeline cycle.

    Returns: {"captured": True, "intent_id": ..., "pipeline_triggered": bool}
    """
    from .workspace import get_redis
    r = await get_redis()

    intent_id = f"steer-{int(time.time())}"

    # Store as operator intent for the miner
    await r.lpush("athanor:intents:operator", text[:500])
    await r.ltrim("athanor:intents:operator", 0, 49)

    # Also store structured metadata for richer processing
    meta = json.dumps({
        "id": intent_id,
        "text": text[:500],
        "priority": priority,
        "source": source,
        "injected_at": time.time(),
    })
    await r.lpush("athanor:intents:steering_log", meta)
    await r.ltrim("athanor:intents:steering_log", 0, 99)

    logger.info("Steering intent injected: [%.1f] %s", priority, text[:100])

    # Optionally trigger immediate pipeline cycle
    pipeline_triggered = False
    if trigger_cycle:
        try:
            from .work_pipeline import run_pipeline_cycle
            import asyncio
            asyncio.create_task(run_pipeline_cycle())
            pipeline_triggered = True
        except Exception as e:
            logger.warning("Failed to trigger pipeline cycle: %s", e)

    return {
        "captured": True,
        "intent_id": intent_id,
        "priority": priority,
        "pipeline_triggered": pipeline_triggered,
    }


async def get_pending_intents() -> list[dict]:
    """Return current pending operator intents (what the pipeline will act on next)."""
    from .workspace import get_redis
    r = await get_redis()

    raw = await r.lrange("athanor:intents:operator", 0, 20)
    intents = []
    for item in raw:
        text = item.decode() if isinstance(item, bytes) else item
        intents.append({"text": text})

    return intents


async def clear_intent(text: str) -> bool:
    """Remove a specific intent from the pending list (after execution or manual dismissal)."""
    from .workspace import get_redis
    r = await get_redis()

    removed = await r.lrem("athanor:intents:operator", 1, text)
    return removed > 0
