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
from collections import deque

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

# Latency tracking — ring buffer of recent enrichment timings
_LATENCY_BUFFER_SIZE = 500
_latency_records: deque[dict] = deque(maxlen=_LATENCY_BUFFER_SIZE)

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
        "personal_limit": 3,
        "conversations_limit": 3,
        "pref_boost": "system monitoring detail level verbosity",
    },
    "media-agent": {
        "prefs_limit": 5,
        "activity_limit": 5,
        "knowledge_limit": 0,  # media agent doesn't need doc knowledge
        "personal_limit": 0,
        "conversations_limit": 2,
        "pref_boost": "media content quality viewing genre preferences",
    },
    "home-agent": {
        "prefs_limit": 5,
        "activity_limit": 5,
        "knowledge_limit": 0,
        "personal_limit": 2,
        "conversations_limit": 2,
        "pref_boost": "home comfort temperature lighting schedule preferences",
    },
    "research-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 3,  # research benefits from prior docs
        "personal_limit": 3,
        "conversations_limit": 3,
        "pref_boost": "research depth format citation preferences",
    },
    "creative-agent": {
        "prefs_limit": 5,
        "activity_limit": 3,
        "knowledge_limit": 0,
        "personal_limit": 0,
        "conversations_limit": 2,
        "pref_boost": "image style creative visual artistic preferences",
    },
    "knowledge-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 0,  # knowledge agent has its own search tools
        "personal_limit": 5,
        "conversations_limit": 2,
        "pref_boost": "knowledge format detail preferences",
    },
    "coding-agent": {
        "prefs_limit": 3,
        "activity_limit": 3,
        "knowledge_limit": 2,
        "personal_limit": 2,
        "conversations_limit": 3,
        "pref_boost": "coding conventions style technology stack preferences",
    },
    "data-curator": {
        "prefs_limit": 3,
        "activity_limit": 5,  # needs history to avoid re-indexing
        "knowledge_limit": 0,  # has its own search tools
        "personal_limit": 5,
        "conversations_limit": 2,
        "pref_boost": "personal data files documents organization indexing preferences",
    },
}

# Default config for unknown agents
_DEFAULT_CONFIG = {
    "prefs_limit": 3,
    "activity_limit": 3,
    "knowledge_limit": 2,
    "personal_limit": 0,
    "conversations_limit": 2,
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


async def _hybrid_search_collection(
    collection: str,
    vector: list[float],
    query_text: str,
    limit: int,
    filter_dict: dict | None = None,
) -> list[dict]:
    """Search a Qdrant collection using hybrid search (vector + keyword + RRF).

    Falls back to vector-only search if hybrid module fails.
    """
    if limit <= 0:
        return []
    try:
        from .hybrid_search import hybrid_search

        return await hybrid_search(
            client=_async_client,
            collection=collection,
            vector=vector,
            query_text=query_text,
            limit=limit,
            score_threshold=SCORE_THRESHOLD,
            filter_dict=filter_dict,
        )
    except Exception as e:
        logger.debug("Hybrid search failed for %s, falling back to vector: %s", collection, e)
        return await _search_collection(collection, vector, limit, filter_dict)


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


def _format_graph_related(results: list[dict]) -> list[str]:
    """Format graph-expanded related documents into context text."""
    lines = []
    for r in results:
        title = r.get("title", r.get("source", "unknown"))
        category = r.get("category", "")
        source = r.get("source", "")
        if title and source:
            cat_tag = f"[{category}] " if category else ""
            lines.append(f"- {cat_tag}**{title}** (`{source}`)")
    return lines


def _format_personal_data(results: list[dict]) -> list[str]:
    """Format personal data results into context text."""
    lines = []
    for r in results:
        payload = r.get("payload", {})
        title = payload.get("title", payload.get("source_file", "unknown"))
        text = payload.get("text", "")[:300]
        dtype = payload.get("data_type", "")
        score = r.get("score", 0)
        if text:
            prefix = f"[{dtype}] " if dtype else ""
            lines.append(f"- {prefix}**{title}** (relevance: {score:.2f}): {text}")
    return lines


def _format_conversations(results: list[dict]) -> list[str]:
    """Format conversation history results into context text."""
    lines = []
    for r in results:
        payload = r.get("payload", {})
        ts = payload.get("timestamp", "")[:16]
        user_msg = payload.get("user_message", "")[:150]
        assistant_msg = payload.get("assistant_response", "")[:150]
        if user_msg:
            lines.append(f"- [{ts}] User: {user_msg}")
            if assistant_msg:
                lines.append(f"  Response: {assistant_msg}")
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
    convention_lines: list[str] | None = None,
    personal_data_lines: list[str] | None = None,
    conversation_lines: list[str] | None = None,
    cst_line: str = "",
    graph_related_lines: list[str] | None = None,
    skill_context: str = "",
) -> str:
    """Assemble the final context injection string."""
    sections = []

    if cst_line:
        sections.append(f"## Cognitive State\n{cst_line}")

    if goal_lines:
        sections.append(
            "## Active Goals\n"
            "The user has set these steering goals. Align your actions accordingly:\n"
            + "\n".join(goal_lines)
        )

    if skill_context:
        sections.append(skill_context)

    if convention_lines:
        sections.append(
            "## Learned Conventions\n"
            "These rules have been confirmed from observed patterns. Follow them:\n"
            + "\n".join(convention_lines)
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

    if graph_related_lines:
        sections.append(
            "## Related Documentation (graph)\n"
            "Other documents in the same categories, found via knowledge graph traversal:\n"
            + "\n".join(graph_related_lines)
        )

    if personal_data_lines:
        sections.append(
            "## Personal Data\n"
            "Relevant personal data from the user's indexed files:\n"
            + "\n".join(personal_data_lines)
        )

    if conversation_lines:
        sections.append(
            f"## Previous Conversations ({agent_name})\n"
            "Relevant past conversations with this agent:\n"
            + "\n".join(conversation_lines)
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


async def enrich_context(agent_name: str, user_message: str, max_chars: int = 0) -> str:
    """Build context injection for a request.

    Computes one embedding from the user message, then queries preferences,
    activity, and knowledge collections in parallel. Returns a formatted
    context string ready for injection into the conversation.

    Returns empty string if no relevant context found or on any error.

    Args:
        agent_name: Which agent is handling the request
        user_message: The user's message text
        max_chars: Override MAX_CONTEXT_CHARS budget (0 = use default)
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
    personal_limit = config.get("personal_limit", 0)
    conversations_limit = config.get("conversations_limit", 2)

    # Build preference filter (agent-specific OR global)
    pref_filter = None
    if agent_name:
        pref_filter = {
            "should": [
                {"key": "agent", "match": {"value": agent_name}},
                {"key": "agent", "match": {"value": "global"}},
            ]
        }

    # Build conversation filter (agent-specific)
    conv_filter = None
    if agent_name and conversations_limit > 0:
        conv_filter = {
            "must": [{"key": "agent", "match": {"value": agent_name}}]
        }

    tasks = [
        _search_preferences_with_decay(vector, prefs_limit, pref_filter),
        _scroll_activity(agent_name, activity_limit),
        _hybrid_search_collection("knowledge", vector, user_message, knowledge_limit),
        _hybrid_search_collection("personal_data", vector, user_message, personal_limit),
        _search_collection("conversations", vector, conversations_limit, conv_filter),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    prefs = results[0] if not isinstance(results[0], BaseException) else []
    activity = results[1] if not isinstance(results[1], BaseException) else []
    knowledge = results[2] if not isinstance(results[2], BaseException) else []
    personal_data = results[3] if not isinstance(results[3], BaseException) else []
    conversations = results[4] if not isinstance(results[4], BaseException) else []

    # Step 2b: Graph expansion — find related docs via Neo4j (fast, ~10ms)
    graph_related: list[dict] = []
    if knowledge and knowledge_limit > 0:
        try:
            from .graph_context import expand_knowledge_graph
            sources = [
                r.get("payload", {}).get("source", "")
                for r in knowledge
                if r.get("payload", {}).get("source")
            ]
            if sources:
                graph_related = await expand_knowledge_graph(_async_client, sources, limit=3)
        except Exception as e:
            logger.debug("Graph expansion failed: %s", e)

    # Step 2c: Fetch CST state (Redis, fast)
    cst_line = ""
    try:
        from .cst import get_cst
        cst = await get_cst()
        if cst.cycle_count > 0:
            cst_line = cst.to_context_string()
    except Exception as e:
        logger.debug("CST fetch failed: %s", e)

    # Step 2d: Fetch active goals + patterns (Redis, fast)
    goal_lines = []
    try:
        from .goals import get_goals_for_agent
        goal_texts = await get_goals_for_agent(agent_name)
        goal_lines = [f"- {t}" for t in goal_texts]
    except Exception as e:
        logger.debug("Goals fetch failed: %s", e)

    pattern_lines = []
    try:
        from .patterns import get_agent_patterns
        agent_patterns = await get_agent_patterns(agent_name)
        pattern_lines = _format_patterns(agent_patterns)
    except Exception as e:
        logger.debug("Patterns fetch failed: %s", e)

    convention_lines = []
    try:
        from .conventions import get_agent_conventions
        convention_rules = await get_agent_conventions(agent_name)
        convention_lines = [f"- {rule}" for rule in convention_rules]
    except Exception as e:
        logger.debug("Conventions fetch failed: %s", e)

    skill_context = ""
    try:
        from .skill_learning import search_skills_for_context
        skill_context = await search_skills_for_context(agent_name, user_message, limit=3)
    except Exception as e:
        logger.debug("Skill search failed: %s", e)

    # Step 2e: Deduplicate across collections
    # Knowledge and personal_data can return overlapping content. Dedup by
    # comparing the first 200 chars of text payloads.
    if knowledge and personal_data:
        seen_prefixes: set[str] = set()
        for r in knowledge:
            prefix = r.get("payload", {}).get("text", "")[:200].strip()
            if prefix:
                seen_prefixes.add(prefix)
        deduped_personal: list[dict] = []
        for r in personal_data:
            prefix = r.get("payload", {}).get("text", "")[:200].strip()
            if prefix and prefix in seen_prefixes:
                continue
            deduped_personal.append(r)
        if len(deduped_personal) < len(personal_data):
            logger.debug(
                "Context dedup: removed %d duplicate(s) from personal_data",
                len(personal_data) - len(deduped_personal),
            )
            personal_data = deduped_personal

    # Conversations and activity can also overlap — dedup by user message prefix
    if conversations and activity:
        activity_prefixes: set[str] = set()
        for p in activity:
            prefix = p.get("payload", {}).get("input_summary", "")[:100].strip()
            if prefix:
                activity_prefixes.add(prefix)
        deduped_convos: list[dict] = []
        for r in conversations:
            prefix = r.get("payload", {}).get("user_message", "")[:100].strip()
            if prefix and prefix in activity_prefixes:
                continue
            deduped_convos.append(r)
        if len(deduped_convos) < len(conversations):
            logger.debug(
                "Context dedup: removed %d duplicate(s) from conversations",
                len(conversations) - len(deduped_convos),
            )
            conversations = deduped_convos

    # Step 3: Format
    pref_lines = _format_preferences(prefs)
    activity_lines = _format_activity(activity, agent_name)
    knowledge_lines = _format_knowledge(knowledge)
    personal_data_lines = _format_personal_data(personal_data)
    conversation_lines = _format_conversations(conversations)
    graph_related_lines = _format_graph_related(graph_related)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    total_hits = len(pref_lines) + len(activity_lines) // 2 + len(knowledge_lines) + len(personal_data_lines) + len(conversation_lines) // 2
    skill_count = skill_context.count("###")

    _latency_records.append({
        "agent": agent_name,
        "elapsed_ms": elapsed_ms,
        "hits": total_hits,
        "ts": time.time(),
    })

    if total_hits > 0 or goal_lines or pattern_lines or convention_lines or skill_count:
        logger.info(
            "Context enrichment for %s: %d prefs, %d activity, %d knowledge (+%d graph), %d personal, %d convos, %d goals, %d patterns, %d conventions, %d skills (%dms)",
            agent_name,
            len(pref_lines),
            len(activity_lines) // 2,
            len(knowledge_lines),
            len(graph_related_lines),
            len(personal_data_lines),
            len(conversation_lines) // 2,
            len(goal_lines),
            len(pattern_lines),
            len(convention_lines),
            skill_count,
            elapsed_ms,
        )

    result = _build_context_message(
        pref_lines, activity_lines, knowledge_lines, agent_name,
        goal_lines, pattern_lines, convention_lines, personal_data_lines,
        conversation_lines, cst_line, graph_related_lines, skill_context,
    )

    # Apply caller-specified budget override (e.g. task mode uses less context)
    if max_chars > 0 and len(result) > max_chars:
        result = result[:max_chars].rsplit("\n", 1)[0] + "\n\n[context truncated]"

    return result


def get_latency_stats() -> dict:
    """Return context enrichment latency statistics from the ring buffer."""
    if not _latency_records:
        return {"count": 0}

    latencies = [r["elapsed_ms"] for r in _latency_records]
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)

    per_agent: dict[str, list[int]] = {}
    for r in _latency_records:
        per_agent.setdefault(r["agent"], []).append(r["elapsed_ms"])

    agent_stats = {}
    for agent, vals in per_agent.items():
        sv = sorted(vals)
        agent_stats[agent] = {
            "count": len(sv),
            "avg_ms": round(sum(sv) / len(sv), 1),
            "p50_ms": sv[len(sv) // 2],
            "p95_ms": sv[int(len(sv) * 0.95)],
            "max_ms": sv[-1],
        }

    return {
        "count": n,
        "avg_ms": round(sum(latencies) / n, 1),
        "p50_ms": latencies_sorted[n // 2],
        "p95_ms": latencies_sorted[int(n * 0.95)],
        "p99_ms": latencies_sorted[int(n * 0.99)],
        "max_ms": latencies_sorted[-1],
        "by_agent": agent_stats,
    }
