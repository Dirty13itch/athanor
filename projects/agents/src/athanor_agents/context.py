"""Context injection — enrich agent requests with preferences, activity, and knowledge.

Queries Qdrant collections in parallel and formats context for injection
into the agent's message stream as a system message prefix.

This is the bridge between Layer 2 (accumulated knowledge) and agent behavior.
Without this, agents treat every request as if they've never seen the user before.
With this, agents get relevant preferences, recent activity, and knowledge context
before they start their ReAct loop.

Performance target: <300ms total enrichment time (1 embedding + 3 parallel queries).
"""

import asyncio
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url
_EMBEDDING_URL = settings.llm_base_url.replace("/v1", "") + "/v1"
_EMBEDDING_KEY = settings.llm_api_key

# Budget: ~1500 tokens of injected context (~4 chars/token)
MAX_CONTEXT_CHARS = 6000
QUERY_TIMEOUT = 3.0
SCORE_THRESHOLD = 0.25  # minimum relevance for inclusion

# Time-decay constants for preference weighting (ADR-021 Phase 1)
# Full weight for 7 days, linear decay to 25% at 90 days
_FULL_WEIGHT_DAYS = 7
_DECAY_HORIZON_DAYS = 90
_MIN_WEIGHT = 0.25

# Shared async client — connection pooling across all context queries
_async_client = httpx.AsyncClient(timeout=QUERY_TIMEOUT)

# Per-agent context strategy — controls what each agent sees
AGENT_CONTEXT_CONFIG = {
    "general-assistant": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 2,
        "pref_boost": "system monitoring detail level verbosity",
    },
    "media-agent": {
        "prefs_limit": 5,
        "activity_limit": 5,
        "knowledge_limit": 0,  # media agent doesn't need doc knowledge
        "pref_boost": "media content quality viewing genre preferences",
    },
    "home-agent": {
        "prefs_limit": 5,
        "activity_limit": 5,
        "knowledge_limit": 0,
        "pref_boost": "home comfort temperature lighting schedule preferences",
    },
    "research-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 3,  # research benefits from prior docs
        "pref_boost": "research depth format citation preferences",
    },
    "creative-agent": {
        "prefs_limit": 5,
        "activity_limit": 3,
        "knowledge_limit": 0,
        "pref_boost": "image style creative visual artistic preferences",
    },
    "knowledge-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 0,  # knowledge agent has its own search tools
        "pref_boost": "knowledge format detail preferences",
    },
    "coding-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 2,
        "pref_boost": "coding conventions style technology stack preferences",
    },
}

# Default config for unknown agents
_DEFAULT_CONFIG = {
    "prefs_limit": 3,
    "activity_limit": 3,
    "knowledge_limit": 2,
    "pref_boost": "",
}


async def _get_embedding_async(text: str) -> list[float]:
    """Get embedding vector via LiteLLM (async)."""
    resp = await _async_client.post(
        f"{_EMBEDDING_URL}/embeddings",
        json={"model": "embedding", "input": text[:2000]},
        headers={"Authorization": f"Bearer {_EMBEDDING_KEY}"},
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


async def _search_collection(
    collection: str,
    vector: list[float],
    limit: int,
    filter_dict: dict | None = None,
) -> list[dict]:
    """Search a Qdrant collection with a pre-computed vector."""
    if limit <= 0:
        return []
    try:
        body: dict = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
            "score_threshold": SCORE_THRESHOLD,
        }
        if filter_dict:
            body["filter"] = filter_dict

        resp = await _async_client.post(
            f"{_QDRANT_URL}/collections/{collection}/points/search",
            json=body,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        logger.debug("Collection %s search failed: %s", collection, e)
        return []


def _time_decay_weight(timestamp_unix: int) -> float:
    """Compute time-decay weight for a preference result.

    Full weight (1.0) for first 7 days, then linear decay to 0.25 at 90 days.
    Anything older than 90 days gets minimum weight.
    """
    age_seconds = time.time() - timestamp_unix
    age_days = age_seconds / 86400

    if age_days <= _FULL_WEIGHT_DAYS:
        return 1.0
    if age_days >= _DECAY_HORIZON_DAYS:
        return _MIN_WEIGHT

    # Linear decay from 1.0 at 7 days to 0.25 at 90 days
    decay_range = _DECAY_HORIZON_DAYS - _FULL_WEIGHT_DAYS
    progress = (age_days - _FULL_WEIGHT_DAYS) / decay_range
    return 1.0 - progress * (1.0 - _MIN_WEIGHT)


async def _search_preferences_with_decay(
    vector: list[float],
    limit: int,
    filter_dict: dict | None = None,
) -> list[dict]:
    """Search preferences with time-decay re-ranking.

    Fetches 3x the requested limit, applies time-decay to scores,
    re-sorts by decayed score, and returns top N.
    """
    if limit <= 0:
        return []

    # Fetch extra to compensate for decay dropping some results
    fetch_limit = min(limit * 3, 30)
    raw_results = await _search_collection("preferences", vector, fetch_limit, filter_dict)

    if not raw_results:
        return []

    # Apply time-decay weighting
    for result in raw_results:
        ts = result.get("payload", {}).get("timestamp_unix", 0)
        original_score = result.get("score", 0)
        decay = _time_decay_weight(ts) if ts > 0 else _MIN_WEIGHT
        result["decayed_score"] = original_score * decay

    # Re-sort by decayed score and take top N
    raw_results.sort(key=lambda r: r.get("decayed_score", 0), reverse=True)
    return raw_results[:limit]


async def _scroll_activity(agent: str, limit: int) -> list[dict]:
    """Get recent activity for an agent via scroll (no embedding needed)."""
    if limit <= 0:
        return []
    try:
        body: dict = {
            "limit": limit,
            "with_payload": True,
        }
        if agent:
            body["filter"] = {
                "must": [{"key": "agent", "match": {"value": agent}}]
            }

        resp = await _async_client.post(
            f"{_QDRANT_URL}/collections/activity/points/scroll",
            json=body,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])
        # Sort by timestamp descending (scroll doesn't guarantee order)
        points.sort(
            key=lambda p: p.get("payload", {}).get("timestamp_unix", 0),
            reverse=True,
        )
        return points[:limit]
    except Exception as e:
        logger.debug("Activity scroll failed: %s", e)
        return []


def _format_preferences(results: list[dict]) -> list[str]:
    """Format preference results into context text."""
    lines = []
    for r in results:
        payload = r.get("payload", {})
        content = payload.get("content", "")
        signal = payload.get("signal_type", "")
        if content:
            lines.append(f"- [{signal}] {content}")
    return lines


def _format_activity(results: list[dict], agent_name: str) -> list[str]:
    """Format activity results into context text."""
    lines = []
    for p in results:
        payload = p.get("payload", {})
        ts = payload.get("timestamp", "")[:16]
        inp = payload.get("input_summary", "")[:120]
        out = payload.get("output_summary", "")[:120]
        if inp:
            lines.append(f"- [{ts}] Q: {inp}")
            if out:
                lines.append(f"  A: {out}")
    return lines


def _format_knowledge(results: list[dict]) -> list[str]:
    """Format knowledge results into context text."""
    lines = []
    for r in results:
        payload = r.get("payload", {})
        title = payload.get("title", payload.get("source", "unknown"))
        text = payload.get("text", "")[:300]
        score = r.get("score", 0)
        if text:
            lines.append(f"- **{title}** (relevance: {score:.2f}): {text}")
    return lines


def _format_patterns(patterns: list[dict]) -> list[str]:
    """Format detected patterns into context text."""
    lines = []
    for p in patterns:
        ptype = p.get("type", "")
        severity = p.get("severity", "info")
        if ptype == "failure_cluster":
            lines.append(f"- ⚠ You failed {p.get('count', 0)} tasks recently. Review your approach.")
        elif ptype == "negative_feedback_trend":
            lines.append(
                f"- ⚠ Negative feedback trend: {p.get('thumbs_down', 0)} negative vs "
                f"{p.get('thumbs_up', 0)} positive. Adjust your responses."
            )
        elif ptype == "high_escalation_rate":
            lines.append(
                f"- Note: {p.get('count', 0)} escalations triggered. "
                f"Try to handle more tasks autonomously when confident."
            )
        elif ptype == "task_throughput":
            rate = p.get("success_rate", 1.0)
            if rate < 1.0:
                lines.append(f"- System task success rate: {rate:.0%}")
    return lines


def _build_context_message(
    pref_lines: list[str],
    activity_lines: list[str],
    knowledge_lines: list[str],
    agent_name: str,
    goal_lines: list[str] | None = None,
    pattern_lines: list[str] | None = None,
) -> str:
    """Assemble the final context injection string."""
    sections = []

    if goal_lines:
        sections.append(
            "## Active Goals\n"
            "The user has set these steering goals. Align your actions accordingly:\n"
            + "\n".join(goal_lines)
        )

    if pattern_lines:
        sections.append(
            "## Performance Patterns\n"
            "Recent patterns detected about your performance:\n"
            + "\n".join(pattern_lines)
        )

    if pref_lines:
        sections.append(
            "## Your Stored Preferences\n"
            "The user has previously expressed these preferences:\n"
            + "\n".join(pref_lines)
        )

    if activity_lines:
        sections.append(
            f"## Recent Interactions ({agent_name})\n"
            "Recent conversations with this agent:\n"
            + "\n".join(activity_lines)
        )

    if knowledge_lines:
        sections.append(
            "## Relevant Documentation\n"
            "Potentially relevant knowledge base entries:\n"
            + "\n".join(knowledge_lines)
        )

    if not sections:
        return ""

    context = (
        "# Contextual Memory (auto-injected)\n"
        "Use this context to personalize your response. "
        "Don't repeat this information unless asked.\n\n"
        + "\n\n".join(sections)
    )

    # Enforce budget
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS].rsplit("\n", 1)[0] + "\n\n[context truncated]"

    return context


async def enrich_context(agent_name: str, user_message: str) -> str:
    """Build context injection for a request.

    Computes one embedding from the user message, then queries preferences,
    activity, and knowledge collections in parallel. Returns a formatted
    context string ready for injection as a SystemMessage.

    Returns empty string if no relevant context found or on any error.

    Args:
        agent_name: Which agent is handling the request
        user_message: The user's message text
    """
    # Skip for very short messages (greetings, etc.)
    if len(user_message.strip()) < 5:
        return ""

    config = AGENT_CONTEXT_CONFIG.get(agent_name, _DEFAULT_CONFIG)
    start = time.monotonic()

    # Step 1: Compute embedding (one call, reused for preferences + knowledge)
    try:
        # Boost with agent-specific preference terms for better preference matching
        boost = config.get("pref_boost", "")
        embed_text = f"{user_message[:800]} {boost}".strip()
        vector = await _get_embedding_async(embed_text)
    except Exception as e:
        logger.warning("Context enrichment: embedding failed: %s", e)
        return ""

    # Step 2: Query all sources in parallel
    prefs_limit = config.get("prefs_limit", 3)
    activity_limit = config.get("activity_limit", 3)
    knowledge_limit = config.get("knowledge_limit", 2)

    # Build preference filter (agent-specific OR global)
    pref_filter = None
    if agent_name:
        pref_filter = {
            "should": [
                {"key": "agent", "match": {"value": agent_name}},
                {"key": "agent", "match": {"value": "global"}},
            ]
        }

    tasks = [
        _search_preferences_with_decay(vector, prefs_limit, pref_filter),
        _scroll_activity(agent_name, activity_limit),
        _search_collection("knowledge", vector, knowledge_limit),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    prefs = results[0] if not isinstance(results[0], BaseException) else []
    activity = results[1] if not isinstance(results[1], BaseException) else []
    knowledge = results[2] if not isinstance(results[2], BaseException) else []

    # Step 3: Fetch active goals + patterns (Redis, fast)
    goal_lines = []
    try:
        from .goals import get_goals_for_agent
        goal_texts = await get_goals_for_agent(agent_name)
        goal_lines = [f"- {t}" for t in goal_texts]
    except Exception:
        pass

    pattern_lines = []
    try:
        from .patterns import get_agent_patterns
        agent_patterns = await get_agent_patterns(agent_name)
        pattern_lines = _format_patterns(agent_patterns)
    except Exception:
        pass

    # Step 4: Format
    pref_lines = _format_preferences(prefs)
    activity_lines = _format_activity(activity, agent_name)
    knowledge_lines = _format_knowledge(knowledge)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    total_hits = len(pref_lines) + len(activity_lines) // 2 + len(knowledge_lines)

    if total_hits > 0 or goal_lines or pattern_lines:
        logger.info(
            "Context enrichment for %s: %d prefs, %d activity, %d knowledge, %d goals, %d patterns (%dms)",
            agent_name,
            len(pref_lines),
            len(activity_lines) // 2,  # 2 lines per activity item
            len(knowledge_lines),
            len(goal_lines),
            len(pattern_lines),
            elapsed_ms,
        )

    return _build_context_message(
        pref_lines, activity_lines, knowledge_lines, agent_name, goal_lines, pattern_lines
    )
