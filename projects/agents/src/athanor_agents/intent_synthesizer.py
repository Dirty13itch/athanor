"""Intent Synthesizer — generates strategic cross-domain intents using the owner model.

Uses the owner model + system state to produce 8-15 strategic intents every
pipeline cycle. Intents span ALL domains (not just EoBQ), connect to the
twelve words, and maintain an 80/20 exploit/explore split.

Local-first LLM call via 'reasoning' alias (Qwen3.5-27B TP=4).
Cloud escalation only if local model is unreachable.
"""

import json
import logging
import re
import time

import httpx

from .config import settings
from .intent_miner import RawIntent

logger = logging.getLogger(__name__)

SYNTHESIS_HISTORY_KEY = "athanor:synthesis:history"
SYNTHESIS_STATS_KEY = "athanor:synthesis:stats"

_LLM_URL = settings.llm_base_url + "/chat/completions"
_LLM_KEY = settings.llm_api_key
_LLM_MODEL = "reasoning"  # Qwen3.5-27B-FP8 TP=4 on FOUNDRY — 95.0 IFEval

# Agent capabilities for the synthesis prompt (what each agent can actually do)
AGENT_TOOLS = {
    "creative-agent": (
        "generate_image, generate_i2v_video, generate_with_likeness, generate_character_portrait, "
        "check_video_inventory, evaluate_video_quality, poll_video_completion, update_video_inventory, "
        "check_queue, get_comfyui_status"
    ),
    "stash-agent": (
        "get_stash_stats, search_scenes, get_scene_details, search_performers, "
        "list_tags, find_duplicates, scan_library, auto_tag, generate_content, "
        "update_scene_rating, mark_scene_organized, get_recent_scenes"
    ),
    "media-agent": (
        "search_tv_shows, add_tv_show, search_movies, add_movie, "
        "get_plex_activity, get_watch_history, get_tv_queue, get_movie_queue"
    ),
    "research-agent": "web_search, fetch_page, search_knowledge, query_infrastructure",
    "knowledge-agent": (
        "search_knowledge, search_signals, deep_search, query_knowledge_graph, "
        "find_related_docs, get_knowledge_stats, upload_document"
    ),
    "coding-agent": (
        "generate_code, review_code, transform_code, read_file, write_file, "
        "list_directory, search_files, run_command"
    ),
    "home-agent": (
        "get_ha_states, get_entity_state, call_ha_service, set_light_brightness, "
        "set_climate_temperature, list_automations, trigger_automation"
    ),
    "data-curator": (
        "scan_directory, parse_document, analyze_content, index_document, "
        "search_personal, get_scan_status, sync_gdrive"
    ),
    "general-assistant": (
        "check_services, get_gpu_metrics, get_storage_info, read_file, "
        "list_directory, search_files, delegate_to_agent"
    ),
}


def _build_synthesis_prompt(owner_profile: dict) -> str:
    """Build the LLM prompt for strategic intent synthesis."""
    profile_json = json.dumps(owner_profile, indent=2, default=str)

    # Build domain gaps summary
    domain_lines = []
    for dname, dstate in owner_profile.get("domains", {}).items():
        if dstate.get("suppressed"):
            domain_lines.append(f"  {dname}: SUPPRESSED (skipped by owner request)")
            continue
        gaps = ", ".join(dstate.get("gaps", [])) or "none identified"
        domain_lines.append(
            f"  {dname}: momentum={dstate.get('momentum', '?')}, "
            f"interest={dstate.get('interest', 0):.2f}, gaps=[{gaps}]"
        )
    domains_text = "\n".join(domain_lines)

    # Build agent tools summary
    agent_lines = []
    for aname, tools in AGENT_TOOLS.items():
        agent_lines.append(f"  {aname}: {tools}")
    agents_text = "\n".join(agent_lines)

    # Idle agents and capacity
    capacity = owner_profile.get("capacity", {})
    idle_agents = ", ".join(capacity.get("agents_idle", [])) or "none"

    return f"""You are the strategic intelligence layer for Athanor, a sovereign AI system.
Generate 8-15 strategic intents across ALL domains — not just the obvious ones.

OWNER MODEL:
{profile_json}

DOMAIN STATE (what needs work):
{domains_text}

AVAILABLE AGENTS AND TOOLS:
{agents_text}

SYSTEM CAPACITY:
  GPU idle: ~{capacity.get('gpu_idle_pct', 85)}%
  Queue depth: {capacity.get('queue_depth', 0)}
  Idle agents: {idle_agents}
  Cloud models available: {capacity.get('cloud_models_available', 13)}

DOMAIN COVERAGE RULES:
- Every domain with momentum != "idle" MUST have at least 1 intent
- Stalled domains (idle/blocked) get 1 intent to unstall them
- The domain with highest interest score gets 2-3 intents
- Suppressed domains get NO intents
- At least 1 intent must use an idle agent
- 2-3 intents should be exploration (novel, uncertain, aligned with twelve words)

Generate intents that:
1. Are actionable by a specific agent with its real tools
2. Connect to one of the twelve-word principles (cite which one)
3. Explain WHY this matters now
4. Cover multiple domains
5. Include at least 2 intents that make idle resources productive

CRITICAL: ALL text MUST be in English. Never use Chinese or any other non-English language.

Respond with ONLY a JSON array (no markdown, no code blocks). Each element:
{{"text": "specific actionable task description", "priority": 0.8, "project": "domain_name", "agent": "agent-name", "twelve_word": "relevant_word", "explore": false, "reasoning": "why this matters now"}}"""


async def synthesize_strategic_intents() -> list[RawIntent]:
    """Generate cross-domain strategic intents using the owner model + LLM.

    Returns a list of RawIntent objects compatible with the existing pipeline.
    """
    from .owner_model import ensure_fresh

    # 1. Get fresh owner profile
    profile = await ensure_fresh()
    if not profile or not profile.get("domains"):
        logger.warning("Intent synthesis: no owner profile available, skipping")
        return []

    # 2. Build prompt
    prompt = _build_synthesis_prompt(profile)

    # 3. Call local LLM
    intents = await _call_llm(prompt)

    # 4. Apply twelve-word scoring adjustments
    behavioral = profile.get("behavioral_params", {})
    for intent in intents:
        tw = intent.metadata.get("twelve_word", "")
        if tw == "tuftler":
            intent.priority_hint = min(1.0, intent.priority_hint + 0.1 * behavioral.get("prefers_refinement_over_new", 0.7))
        elif tw == "zetetic":
            intent.priority_hint = min(1.0, intent.priority_hint + 0.05 * behavioral.get("exploration_appetite", 0.6))
        elif tw == "meraki":
            intent.priority_hint = min(1.0, intent.priority_hint + 0.05 * behavioral.get("aesthetic_sensitivity", 0.8))

    # 5. Enforce 80/20 exploit/explore split
    explore = [i for i in intents if i.metadata.get("explore")]
    exploit = [i for i in intents if not i.metadata.get("explore")]
    total = len(intents)
    target_explore = max(2, int(total * 0.2))
    if len(explore) > target_explore + 1:
        # Too many explore — drop lowest priority ones
        explore.sort(key=lambda x: x.priority_hint, reverse=True)
        intents = exploit + explore[:target_explore]

    # 6. Record stats
    await _record_stats(intents, profile)

    logger.info(
        "Intent synthesis: %d intents (%d explore, %d exploit) across %d domains",
        len(intents),
        sum(1 for i in intents if i.metadata.get("explore")),
        sum(1 for i in intents if not i.metadata.get("explore")),
        len(set(i.metadata.get("project", "") for i in intents)),
    )
    return intents


async def synthesize_preview() -> list[dict]:
    """Generate a preview of what synthesis WOULD produce, without side effects.

    Returns raw intent dicts for review before approval.
    """
    from .owner_model import ensure_fresh

    profile = await ensure_fresh()
    if not profile or not profile.get("domains"):
        return []

    prompt = _build_synthesis_prompt(profile)
    raw_proposals = await _call_llm_raw(prompt)
    return raw_proposals


async def _call_llm(prompt: str) -> list[RawIntent]:
    """Call the LLM and parse response into RawIntent objects."""
    raw_proposals = await _call_llm_raw(prompt)
    intents = []

    for p in raw_proposals:
        text = p.get("text", "")
        if not text or not p.get("agent"):
            continue

        intents.append(RawIntent(
            source="synthesis",
            text=text,
            metadata={
                "project": p.get("project", ""),
                "agent": p.get("agent", ""),
                "twelve_word": p.get("twelve_word", ""),
                "explore": p.get("explore", False),
                "reasoning": p.get("reasoning", ""),
                "synthesis_ts": time.time(),
            },
            priority_hint=min(1.0, max(0.1, p.get("priority", 0.5))),
        ))

    return intents


async def _call_llm_raw(prompt: str) -> list[dict]:
    """Call LLM and return parsed JSON proposals."""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                _LLM_URL,
                json={
                    "model": _LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                headers={"Authorization": f"Bearer {_LLM_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error("Intent synthesis LLM call timed out (180s)")
        return []
    except Exception as e:
        logger.error("Intent synthesis LLM call failed: %s", e)
        return []

    raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Strip <think> blocks (Qwen3.5 reasoning)
    clean = re.sub(r"<think>.*?</think>\s*", "", raw_text, flags=re.DOTALL).strip()

    return _parse_proposals(clean)


def _parse_proposals(text: str) -> list[dict]:
    """Parse JSON array of intent proposals from LLM output."""
    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Extract from code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Find JSON array anywhere
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Recover individual objects from truncated output
    if start >= 0:
        partial = text[start:]
        objects = []
        i = 0
        while i < len(partial):
            if partial[i] == "{":
                depth = 0
                in_string = False
                escape = False
                for j in range(i, len(partial)):
                    ch = partial[j]
                    if escape:
                        escape = False
                        continue
                    if ch == "\\":
                        escape = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                obj = json.loads(partial[i:j + 1])
                                if obj.get("text") and obj.get("agent"):
                                    objects.append(obj)
                            except json.JSONDecodeError:
                                pass
                            i = j + 1
                            break
                else:
                    break
            else:
                i += 1
        if objects:
            logger.info("Recovered %d intents from truncated synthesis output", len(objects))
            return objects

    logger.warning("Intent synthesis: failed to parse LLM output (%d chars)", len(text))
    return []


async def _record_stats(intents: list[RawIntent], profile: dict):
    """Record synthesis statistics for health monitoring."""
    try:
        from .workspace import get_redis
        r = await get_redis()

        stats = {
            "ts": time.time(),
            "intent_count": len(intents),
            "explore_count": sum(1 for i in intents if i.metadata.get("explore")),
            "domains_covered": list(set(i.metadata.get("project", "") for i in intents)),
            "agents_used": list(set(i.metadata.get("agent", "") for i in intents)),
            "avg_priority": round(sum(i.priority_hint for i in intents) / max(len(intents), 1), 2),
            "profile_age_s": round(time.time() - profile.get("refreshed_at", 0)),
        }
        await r.set(SYNTHESIS_STATS_KEY, json.dumps(stats))

        # Also push to history for trend analysis
        await r.lpush(SYNTHESIS_HISTORY_KEY, json.dumps(stats))
        await r.ltrim(SYNTHESIS_HISTORY_KEY, 0, 49)
    except Exception as e:
        logger.debug("Synthesis stats recording failed: %s", e)


async def get_synthesis_stats() -> dict:
    """Return latest synthesis stats for health endpoint."""
    try:
        from .workspace import get_redis
        r = await get_redis()
        raw = await r.get(SYNTHESIS_STATS_KEY)
        if raw:
            return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:
        pass
    return {}
