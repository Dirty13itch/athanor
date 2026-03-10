"""Proactive Work Engine — generates and manages autonomous work for agents.

The bridge between knowing and doing. Reads project definitions and user
profile, uses the reasoning model to generate actionable tasks, and
submits them to the task engine for execution.

Operational rhythm:
- 7:00 AM: Morning planning — generate 7-12 tasks across projects
- Every 2 hours: Queue refill — if <2 pending, generate more
- Results surfaced in daily digest and Command Center

The work planner is what makes agents proactive creators instead of
reactive health-checkers.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

import httpx

from .config import settings
from .projects import (
    get_project as get_registered_project,
    get_project_definitions as get_registered_project_definitions,
)

logger = logging.getLogger(__name__)

# Redis keys
WORKPLAN_KEY = "athanor:workplan:current"
WORKPLAN_HISTORY_KEY = "athanor:workplan:history"
WORKPLAN_LAST_RUN_KEY = "athanor:workplan:last_run"

# Planning schedule
MORNING_HOUR = 7
MORNING_MINUTE = 0
REFILL_INTERVAL = 7200  # 2 hours
MIN_PENDING_TASKS = 2  # Generate more when queue drops below this

# LLM config for planning
_LLM_URL = settings.llm_base_url + "/chat/completions"
_LLM_KEY = settings.llm_api_key
_LLM_MODEL = "reasoning"  # Qwen3.5-27B-FP8 TP=4 on FOUNDRY

# --- Project Definitions ---
# The canonical project registry now lives in athanor_agents.projects.
# The planner consumes a compatibility projection of that registry so the
# prompt structure stays stable while project identity becomes first-class.

PROJECTS = get_registered_project_definitions()

# Agent capabilities reference for the planner prompt
AGENT_CAPABILITIES = {
    "general-assistant": {
        "can_do": "System monitoring, service checks, GPU metrics, storage info, task delegation, file reading",
        "tools": "check_services, get_gpu_metrics, get_storage_info, read_file, list_directory, search_files, delegate_to_agent",
    },
    "media-agent": {
        "can_do": "Search/add TV shows (Sonarr) and movies (Radarr), check Plex activity and watch history",
        "tools": "search_tv_shows, add_tv_show, search_movies, add_movie, get_plex_activity, get_watch_history",
    },
    "creative-agent": {
        "can_do": "Generate images (Flux dev FP8 via ComfyUI), generate video (Wan2.x), check queue status",
        "tools": "generate_image, generate_video, check_queue, get_comfyui_status",
    },
    "research-agent": {
        "can_do": "Web search, fetch pages, search knowledge base, query infrastructure graph",
        "tools": "web_search, fetch_page, search_knowledge, query_infrastructure",
    },
    "knowledge-agent": {
        "can_do": "Search knowledge base, list documents, query knowledge graph, find related docs, get stats",
        "tools": "search_knowledge, list_documents, query_knowledge_graph, find_related_docs, get_knowledge_stats",
    },
    "coding-agent": {
        "can_do": "Generate/review/transform code, read/write files, list/search directories, run shell commands",
        "tools": "generate_code, review_code, transform_code, read_file, write_file, list_directory, search_files, run_command",
    },
    "home-agent": {
        "can_do": "Home Assistant entity states, services, lights, climate, automations",
        "tools": "get_ha_states, get_entity_state, call_ha_service, set_light_brightness, set_climate_temperature",
    },
    "stash-agent": {
        "can_do": "Search/browse adult content library, tag, organize, scan",
        "tools": "get_stash_stats, search_scenes, search_performers, auto_tag, scan_library",
    },
}


# Agents requiring morning approval before autonomous execution (ADR-021 hybrid autonomy)
HIGH_IMPACT_AGENTS = {"home-agent", "coding-agent"}


async def _gather_knowledge_context(focus: str = "") -> dict:
    """Query Qdrant for relevant TODO items, project docs, and preferences.

    Returns structured context the planner prompt can use.
    """
    from .config import settings

    qdrant_url = settings.qdrant_url
    embedding_url = settings.llm_base_url.replace("/v1", "") + "/v1"
    embedding_key = settings.llm_api_key

    # Build a query that captures what the planner needs
    query_text = (
        f"TODO items, project needs, work priorities, EoBQ development, "
        f"infrastructure improvements, creative content generation"
        f"{', ' + focus if focus else ''}"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        # Get embedding for our query
        try:
            resp = await client.post(
                f"{embedding_url}/embeddings",
                json={"model": "embedding", "input": query_text[:2000]},
                headers={"Authorization": f"Bearer {embedding_key}"},
            )
            resp.raise_for_status()
            vector = resp.json()["data"][0]["embedding"]
        except Exception as e:
            logger.warning("Knowledge context: embedding failed: %s", e)
            return {"knowledge": [], "preferences": [], "goals": []}

        # Query knowledge base, preferences, and goals in parallel
        async def search_collection(collection: str, limit: int, filter_dict=None):
            try:
                body = {
                    "vector": vector,
                    "limit": limit,
                    "with_payload": True,
                    "score_threshold": 0.2,
                }
                if filter_dict:
                    body["filter"] = filter_dict
                resp = await client.post(
                    f"{qdrant_url}/collections/{collection}/points/search",
                    json=body,
                )
                resp.raise_for_status()
                return resp.json().get("result", [])
            except Exception:
                return []

        knowledge_task = search_collection("knowledge", 15)
        preferences_task = search_collection("preferences", 12)

        knowledge_results, pref_results = await asyncio.gather(
            knowledge_task, preferences_task,
        )

    # Fetch active goals from Redis
    goals = []
    try:
        from .goals import list_goals
        goals = await list_goals(active_only=True)
    except Exception:
        pass

    # Fetch completed task results (what has the system already produced?)
    completed_results = []
    try:
        from .tasks import list_tasks
        completed = await list_tasks(status="completed", limit=10)
        for t in completed:
            if t.get("metadata", {}).get("source") == "work_planner" and t.get("result"):
                completed_results.append({
                    "agent": t.get("agent"),
                    "project": t.get("metadata", {}).get("project", ""),
                    "prompt": t.get("prompt", "")[:200],
                    "result": t.get("result", "")[:500],
                })
    except Exception:
        pass

    return {
        "knowledge": [
            {
                "title": r.get("payload", {}).get("title", ""),
                "source": r.get("payload", {}).get("source", ""),
                "text": r.get("payload", {}).get("text", "")[:400],
                "category": r.get("payload", {}).get("category", ""),
                "score": r.get("score", 0),
            }
            for r in knowledge_results
        ],
        "preferences": [
            {
                "content": r.get("payload", {}).get("content", ""),
                "category": r.get("payload", {}).get("category", ""),
                "signal": r.get("payload", {}).get("signal_type", ""),
            }
            for r in pref_results
            if r.get("payload", {}).get("content")
        ],
        "goals": goals,
        "completed_outputs": completed_results,
    }


def _build_planner_prompt(
    recent_tasks: list[dict],
    pending_tasks: list[dict],
    time_context: str,
    knowledge_context: dict,
    focus: str = "",
) -> str:
    """Build the LLM prompt for work plan generation."""
    projects_text = ""
    for pid, proj in PROJECTS.items():
        needs_text = "\n".join(
            f"    - [{n['priority'].upper()}] {n['description']} (agent: {n['agent']}, output: {n['output_format']})"
            for n in proj["needs"]
        )
        constraints_text = "\n".join(f"    - {c}" for c in proj["constraints"])
        projects_text += f"""
  {pid}: {proj['name']}
    Status: {proj['status']}
    Description: {proj['description']}
    Needs:
{needs_text}
    Constraints:
{constraints_text}
"""

    capabilities_text = "\n".join(
        f"  - {name}: {info['can_do']} (tools: {info['tools']})"
        for name, info in AGENT_CAPABILITIES.items()
    )

    recent_text = "None" if not recent_tasks else "\n".join(
        f"  - [{t.get('status','?')}] {t.get('agent','?')}: {t.get('prompt','')[:100]}"
        for t in recent_tasks[:10]
    )

    pending_text = "None" if not pending_tasks else "\n".join(
        f"  - {t.get('agent','?')}: {t.get('prompt','')[:100]}"
        for t in pending_tasks[:5]
    )

    # Build knowledge context sections
    knowledge_text = "None"
    if knowledge_context.get("knowledge"):
        items = []
        for k in knowledge_context["knowledge"][:12]:
            items.append(f"  - [{k['category']}] {k['title']}: {k['text'][:300]}")
        knowledge_text = "\n".join(items)

    prefs_text = "None"
    if knowledge_context.get("preferences"):
        items = []
        for p in knowledge_context["preferences"][:10]:
            items.append(f"  - [{p['category']}] {p['content'][:200]}")
        prefs_text = "\n".join(items)

    goals_text = "None"
    if knowledge_context.get("goals"):
        items = []
        for g in knowledge_context["goals"][:5]:
            text = g.get("text", "") if isinstance(g, dict) else str(g)
            items.append(f"  - {text}")
        goals_text = "\n".join(items)

    completed_text = "None"
    if knowledge_context.get("completed_outputs"):
        items = []
        for c in knowledge_context["completed_outputs"][:8]:
            items.append(f"  - [{c['project']}] {c['agent']}: {c['prompt'][:100]} → {c['result'][:300]}")
        completed_text = "\n".join(items)

    return f"""You are the Athanor Work Planner. Generate actionable tasks for the agent workforce.

OWNER PROFILE:
Shaun Ulrich. Autotelic builder — the craft of building is the reward. He cares about:
- EoBQ (his passion game project — highest creative priority)
- A well-maintained, self-improving infrastructure
- Media library that grows intelligently
- Systems that produce real value, not busywork
- Uncensored creative AI content (Flux + LoRA, NSFW is intentional)
- Optimizing and refining his homelab (7 GPUs, 99% idle — the demand problem)

TIME CONTEXT: {time_context}
{f"FOCUS: {focus}" if focus else ""}

ACTIVE GOALS (set by Shaun):
{goals_text}

USER PREFERENCES (from interaction history):
{prefs_text}

RELEVANT DOCUMENTATION (from knowledge base):
{knowledge_text}

RECENTLY COMPLETED OUTPUTS (build on these):
{completed_text}

PROJECTS:
{projects_text}

AGENT CAPABILITIES:
{capabilities_text}

RECENT TASKS (last 24h):
{recent_text}

CURRENTLY PENDING:
{pending_text}

INSTRUCTIONS:
Generate 7-12 specific, actionable tasks. You MUST generate at least 7. Each task MUST:
1. Target a specific project
2. Assign to a specific agent that has the right tools
3. Have a detailed, executable prompt (the agent will receive ONLY this prompt — include ALL context it needs)
4. Be something the agent can actually accomplish with its available tools
5. Create tangible output — code, content, images, research, not just "check" or "review"

DISTRIBUTION REQUIREMENTS:
- At least 3 tasks for EoBQ (highest priority project — needs constant momentum)
- At least 2 different agents must be used
- Spread work across agents that are available — don't let any agent sit idle
- creative-agent should ALWAYS have at least 1 image generation task
- coding-agent should ALWAYS have at least 1 code/content creation task

PRIORITIZE:
- EoBQ content creation (characters, scenes, art, code) — HIGHEST PRIORITY, always the biggest chunk of tasks
- Active goals (see above) — these are direct instructions from the owner
- Building on completed outputs (see above) — continue the thread, don't restart
- Tasks that produce real artifacts (files, images, research docs)
- Tasks that maximize GPU utilization (image gen, video gen, embeddings)
- Quick wins that complete in one agent session (<10 min)

DO NOT generate:
- Duplicate tasks (check pending queue above)
- Vague tasks ("work on X", "improve Y")
- Tasks the assigned agent can't do with its tools
- Pure monitoring tasks (the scheduler already handles those)
- More than 1 infrastructure/monitoring task — focus on creative and project work

CRITICAL: ALL content, prompts, and output MUST be in English. Never use Chinese or any other non-English language in task prompts or expected output.

Respond with ONLY a JSON array (no markdown, no code blocks, no explanation). Each element:
{{
  "project": "project_id",
  "agent": "agent-name",
  "prompt": "Detailed task prompt the agent will execute",
  "priority": "high|normal|low",
  "rationale": "Why this task matters right now"
}}"""


async def generate_work_plan(focus: str = "") -> dict:
    """Generate a work plan using the reasoning model.

    Args:
        focus: Optional focus area (e.g., "eoq", "infrastructure")

    Returns: {plan_id, tasks, generated_at, task_count}
    """
    from .tasks import submit_task, list_tasks

    # Gather context
    recent = await list_tasks(limit=20)
    recent_dicts = [t if isinstance(t, dict) else t for t in recent]
    pending = [t for t in recent_dicts if isinstance(t, dict) and t.get("status") == "pending"]

    now = datetime.now()
    hour = now.hour
    if hour < 12:
        time_context = f"Morning ({now.strftime('%I:%M %p')}). Good time for planning and creative work."
    elif hour < 17:
        time_context = f"Afternoon ({now.strftime('%I:%M %p')}). Good time for focused execution."
    elif hour < 21:
        time_context = f"Evening ({now.strftime('%I:%M %p')}). Shaun may be checking in. Surface results."
    else:
        time_context = f"Night ({now.strftime('%I:%M %p')}). Autonomous mode — Shaun is likely away. Execute freely."

    # Gather knowledge context from Qdrant (docs, preferences, goals, completed outputs)
    knowledge_context = await _gather_knowledge_context(focus=focus)
    logger.info(
        "Work planner context: %d knowledge, %d prefs, %d goals, %d completed",
        len(knowledge_context.get("knowledge", [])),
        len(knowledge_context.get("preferences", [])),
        len(knowledge_context.get("goals", [])),
        len(knowledge_context.get("completed_outputs", [])),
    )

    prompt = _build_planner_prompt(
        recent_tasks=recent_dicts,
        pending_tasks=pending,
        time_context=time_context,
        knowledge_context=knowledge_context,
        focus=focus,
    )

    # Call LLM for planning. Use /no_think to skip extended reasoning
    # (Qwen3 feature) since we want structured JSON output, not deliberation.
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                _LLM_URL,
                json={
                    "model": _LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt + "\n\n/no_think"}],
                    "temperature": 0.7,
                    "max_tokens": 8192,
                },
                headers={"Authorization": f"Bearer {_LLM_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        logger.error("Work planner LLM call timed out (180s)")
        return {"error": "LLM timeout", "tasks": [], "task_count": 0}
    except Exception as e:
        logger.error("Work planner LLM call failed: %s (type=%s)", e, type(e).__name__)
        return {"error": str(e), "tasks": [], "task_count": 0}

    # Extract response text
    raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Strip <think> blocks (Qwen3 reasoning)
    import re
    clean_text = re.sub(r"<think>.*?</think>\s*", "", raw_text, flags=re.DOTALL).strip()

    # Parse JSON from response
    task_proposals = _parse_proposals(clean_text)

    if not task_proposals:
        logger.warning(
            "Work planner produced no valid tasks. Response length: %d chars. Raw (first 1000): %s",
            len(clean_text), clean_text[:1000],
        )
        return {"error": "No tasks generated", "raw": clean_text[:1000], "tasks": [], "task_count": 0}

    logger.info("Work planner parsed %d task proposals from %d char response", len(task_proposals), len(clean_text))

    # Submit tasks to the task engine
    plan_id = f"wp-{int(time.time())}"
    submitted = []

    for proposal in task_proposals:
        agent = proposal.get("agent", "")
        task_prompt = proposal.get("prompt", "")
        project = proposal.get("project", "")
        priority = proposal.get("priority", "normal")
        rationale = proposal.get("rationale", "")

        if not agent or not task_prompt:
            continue

        # Validate agent exists
        if agent not in AGENT_CAPABILITIES:
            logger.warning("Work planner proposed unknown agent: %s", agent)
            continue

        try:
            task = await submit_task(
                agent=agent,
                prompt=task_prompt,
                priority=priority,
                metadata={
                    "source": "work_planner",
                    "plan_id": plan_id,
                    "project": project,
                    "rationale": rationale,
                    "requires_approval": agent in HIGH_IMPACT_AGENTS,
                },
            )
            submitted.append({
                "task_id": task.id if hasattr(task, "id") else str(task),
                "agent": agent,
                "project": project,
                "prompt": task_prompt[:200],
                "priority": priority,
                "rationale": rationale,
            })
            logger.info(
                "Work planner submitted: [%s] %s → %s: %s",
                priority, project, agent, task_prompt[:80],
            )
        except Exception as e:
            logger.warning("Failed to submit planned task: %s", e)

    # Store plan in Redis
    plan = {
        "plan_id": plan_id,
        "generated_at": time.time(),
        "time_context": time_context,
        "focus": focus,
        "tasks": submitted,
        "task_count": len(submitted),
    }

    try:
        from .workspace import get_redis

        r = await get_redis()
        await r.set(WORKPLAN_KEY, json.dumps(plan))
        await r.lpush(WORKPLAN_HISTORY_KEY, json.dumps(plan))
        await r.ltrim(WORKPLAN_HISTORY_KEY, 0, 29)  # Keep last 30 plans
        await r.set(WORKPLAN_LAST_RUN_KEY, str(time.time()))
    except Exception as e:
        logger.warning("Failed to store work plan: %s", e)

    # Log event
    from .activity import log_event

    asyncio.create_task(
        log_event(
            event_type="work_plan_generated",
            agent="system",
            description=f"Generated {len(submitted)} tasks across {len(set(t['project'] for t in submitted))} projects",
            data={"plan_id": plan_id, "task_count": len(submitted)},
        )
    )

    return plan


def _parse_proposals(text: str) -> list[dict]:
    """Parse task proposals from LLM response.

    Handles JSON array, markdown code blocks, and truncated output.
    """
    import re

    # Try direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Try finding a JSON array anywhere in the text
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start >= 0 and bracket_end > bracket_start:
        try:
            result = json.loads(text[bracket_start : bracket_end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Handle truncated JSON — find complete {...} objects by brace matching
    if bracket_start >= 0:
        partial = text[bracket_start:]
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
                                obj = json.loads(partial[i : j + 1])
                                if obj.get("agent") and obj.get("prompt"):
                                    objects.append(obj)
                            except json.JSONDecodeError:
                                pass
                            i = j + 1
                            break
                else:
                    break  # Unclosed brace — truncated object, skip it
            else:
                i += 1
        if objects:
            logger.info("Recovered %d tasks from truncated JSON output", len(objects))
            return objects

    return []


async def get_current_plan() -> dict | None:
    """Get the most recent work plan."""
    try:
        from .workspace import get_redis

        r = await get_redis()
        raw = await r.get(WORKPLAN_KEY)
        if raw:
            return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:
        pass
    return None


async def get_plan_history(limit: int = 10) -> list[dict]:
    """Get recent work plan history."""
    try:
        from .workspace import get_redis

        r = await get_redis()
        entries = await r.lrange(WORKPLAN_HISTORY_KEY, 0, limit - 1)
        return [json.loads(e.decode() if isinstance(e, bytes) else e) for e in entries]
    except Exception:
        return []


async def should_refill() -> bool:
    """Check if the task queue needs refilling."""
    from .tasks import list_tasks

    try:
        tasks = await list_tasks(status="pending", limit=10)
        pending_count = len(tasks)

        # Don't refill if we have enough pending work
        if pending_count >= MIN_PENDING_TASKS:
            return False

        # Don't refill if we just generated a plan recently (< 30 min)
        from .workspace import get_redis

        r = await get_redis()
        last_run = await r.get(WORKPLAN_LAST_RUN_KEY)
        if last_run:
            ts = float(last_run.decode() if isinstance(last_run, bytes) else last_run)
            if time.time() - ts < 1800:  # 30 min minimum between plans
                return False

        return True
    except Exception:
        return False


def get_project_definitions() -> dict:
    """Return all project definitions."""
    return get_registered_project_definitions()


def get_project(project_id: str) -> dict | None:
    """Return a specific project definition."""
    return get_registered_project(project_id)
