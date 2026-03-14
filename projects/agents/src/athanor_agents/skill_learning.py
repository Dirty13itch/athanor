"""Skill Learning — procedural knowledge library for agents.

Ported from reference/hydra/src/hydra_tools/skill_learning.py.
Adapted for Athanor: async, Redis-backed (no file I/O), no agent-file format.

Agents accumulate skills over time — named procedures with trigger conditions,
step-by-step instructions, and empirical success tracking. Skills are retrieved
by keyword relevance and injected into agent context before task execution.

Storage: Redis HSET at `athanor:skills:library` (skill_id → JSON).
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

import redis.asyncio as aioredis

from .config import settings

logger = logging.getLogger(__name__)

SKILLS_KEY = "athanor:skills:library"

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """A named, learnable procedure in the shared skill library."""
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    category: str = "general"
    trigger_conditions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_by: str = ""          # Agent name that created the skill
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # Learning metrics
    execution_count: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    # Recent examples (last 10)
    examples: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------

async def add_skill(
    name: str,
    description: str,
    trigger_conditions: list[str],
    steps: list[str],
    category: str = "general",
    tags: list[str] | None = None,
    created_by: str = "",
) -> str:
    """Add a new skill to the library. Returns skill_id."""
    skill = Skill(
        name=name,
        description=description,
        category=category,
        trigger_conditions=trigger_conditions,
        steps=steps,
        tags=tags or [],
        created_by=created_by,
    )
    r = await _get_redis()
    await r.hset(SKILLS_KEY, skill.skill_id, json.dumps(skill.to_dict()))
    logger.info("Skill added: '%s' (id=%s, by=%s)", name, skill.skill_id, created_by)
    return skill.skill_id


async def get_skill(skill_id: str) -> Skill | None:
    """Get a skill by ID."""
    try:
        r = await _get_redis()
        raw = await r.hget(SKILLS_KEY, skill_id)
        if raw:
            return Skill.from_dict(json.loads(raw))
    except Exception as e:
        logger.warning("Failed to get skill %s: %s", skill_id, e)
    return None


async def get_all_skills() -> list[Skill]:
    """Get all skills from the library."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(SKILLS_KEY)
        return [Skill.from_dict(json.loads(v)) for v in raw.values()]
    except Exception as e:
        logger.warning("Failed to get skills: %s", e)
        return []


async def delete_skill(skill_id: str) -> bool:
    """Remove a skill from the library."""
    try:
        r = await _get_redis()
        removed = await r.hdel(SKILLS_KEY, skill_id)
        return removed > 0
    except Exception as e:
        logger.warning("Failed to delete skill %s: %s", skill_id, e)
        return False


# ---------------------------------------------------------------------------
# Learning — success/failure tracking
# ---------------------------------------------------------------------------

async def record_execution(
    skill_id: str,
    success: bool,
    duration_ms: float,
    context: dict | None = None,
) -> bool:
    """Record a skill execution outcome to update the success rate.

    Uses running average for success_rate and avg_duration_ms.
    Stores up to 10 recent examples for reference.
    """
    try:
        skill = await get_skill(skill_id)
        if skill is None:
            return False

        skill.execution_count += 1
        if success:
            skill.success_count += 1
        skill.success_rate = skill.success_count / skill.execution_count

        # Running average of duration
        prev_total = skill.avg_duration_ms * (skill.execution_count - 1)
        skill.avg_duration_ms = (prev_total + duration_ms) / skill.execution_count

        skill.updated_at = time.time()

        if context:
            skill.examples.append({
                "success": success,
                "duration_ms": duration_ms,
                "context": context,
                "timestamp": time.time(),
            })
            skill.examples = skill.examples[-10:]  # Keep last 10

        r = await _get_redis()
        await r.hset(SKILLS_KEY, skill_id, json.dumps(skill.to_dict()))
        logger.debug(
            "Skill %s execution recorded: success=%s rate=%.2f count=%d",
            skill_id, success, skill.success_rate, skill.execution_count,
        )
        return True
    except Exception as e:
        logger.warning("Failed to record skill execution %s: %s", skill_id, e)
        return False


# ---------------------------------------------------------------------------
# Search and retrieval
# ---------------------------------------------------------------------------

def _compute_relevance(skill: Skill, query: str) -> float:
    """Score how relevant a skill is to a text query (0.0–1.0).

    Matches against trigger_conditions, name, description, and tags.
    """
    query_lower = query.lower()
    words = set(query_lower.split())

    # Trigger condition matching (strongest signal)
    trigger_score = 0.0
    for cond in skill.trigger_conditions:
        cond_lower = cond.lower()
        if cond_lower in query_lower:
            trigger_score = max(trigger_score, 0.6)
        elif any(w in cond_lower for w in words if len(w) > 3):
            trigger_score = max(trigger_score, 0.3)

    # Name + description matching
    name_score = 0.0
    name_lower = skill.name.lower()
    desc_lower = skill.description.lower()
    word_hits = sum(1 for w in words if len(w) > 3 and (w in name_lower or w in desc_lower))
    if word_hits:
        name_score = min(0.4, word_hits * 0.15)

    # Tag matching
    tag_score = 0.0
    for tag in skill.tags:
        if tag.lower() in query_lower:
            tag_score = max(tag_score, 0.2)

    return min(1.0, trigger_score + name_score + tag_score)


async def search_skills(
    query: str = "",
    category: str | None = None,
    tags: list[str] | None = None,
    min_success_rate: float = 0.0,
    limit: int = 10,
) -> list[Skill]:
    """Search the skill library by query, category, tags, or success rate.

    Results sorted by relevance (query) or by proven effectiveness (success_rate × count).
    """
    skills = await get_all_skills()

    results = []
    for skill in skills:
        if category and skill.category != category:
            continue
        if tags and not any(t in skill.tags for t in tags):
            continue
        if skill.execution_count > 0 and skill.success_rate < min_success_rate:
            continue

        if query:
            relevance = _compute_relevance(skill, query)
            if relevance < 0.1:
                continue
            results.append((relevance, skill))
        else:
            results.append((0.0, skill))

    if query:
        results.sort(key=lambda x: x[0], reverse=True)
    else:
        # Sort by proven effectiveness: success_rate * min(count, 100) for unqueried
        results.sort(
            key=lambda x: x[1].success_rate * min(x[1].execution_count, 100),
            reverse=True,
        )

    return [skill for _, skill in results[:limit]]


async def search_skills_for_context(
    agent: str,
    task_text: str,
    limit: int = 3,
) -> str:
    """Find relevant skills and format them as a context injection string.

    Returns empty string if no relevant skills found. Called by context.py.
    """
    try:
        skills = await search_skills(query=task_text, limit=limit)
        if not skills:
            return ""

        lines = ["## Relevant Skills"]
        for skill in skills:
            lines.append(f"\n### {skill.name} [{skill.category}]")
            lines.append(f"*When to use:* {'; '.join(skill.trigger_conditions[:3])}")
            for i, step in enumerate(skill.steps, 1):
                lines.append(f"{i}. {step}")
            if skill.execution_count > 0:
                lines.append(
                    f"*Reliability:* {skill.success_rate:.0%} success "
                    f"({skill.execution_count} uses, avg {skill.avg_duration_ms:.0f}ms)"
                )

        result = "\n".join(lines)
        logger.debug(
            "Skills context for %s: %d skills found for query '%s'",
            agent, len(skills), task_text[:60],
        )
        return result
    except Exception as e:
        logger.warning("Skills context injection failed for %s: %s", agent, e)
        return ""


async def find_matching_skill(
    prompt: str,
    threshold: float = 0.3,
) -> tuple[str, float] | None:
    """Find the best matching skill for a task prompt.

    Returns (skill_id, relevance) if the best match exceeds threshold, else None.
    Used by the task engine to auto-record skill executions.
    """
    skills = await get_all_skills()
    if not skills:
        return None

    best_skill = None
    best_relevance = 0.0

    for skill in skills:
        relevance = _compute_relevance(skill, prompt)
        if relevance > best_relevance:
            best_relevance = relevance
            best_skill = skill

    if best_skill and best_relevance >= threshold:
        return best_skill.skill_id, best_relevance
    return None


async def get_top_skills(limit: int = 10) -> list[Skill]:
    """Get top-performing skills ranked by proven effectiveness."""
    skills = await get_all_skills()
    skills.sort(
        key=lambda s: s.success_rate * min(s.execution_count, 100),
        reverse=True,
    )
    return skills[:limit]


async def get_stats() -> dict:
    """Get summary statistics for the skill library."""
    skills = await get_all_skills()
    if not skills:
        return {"total": 0, "categories": [], "avg_success_rate": 0.0}

    executed = [s for s in skills if s.execution_count > 0]
    categories = list(set(s.category for s in skills))
    avg_rate = sum(s.success_rate for s in executed) / len(executed) if executed else 0.0

    return {
        "total": len(skills),
        "executed": len(executed),
        "categories": categories,
        "avg_success_rate": round(avg_rate, 3),
        "total_executions": sum(s.execution_count for s in skills),
    }


# ---------------------------------------------------------------------------
# Seed initial skills for the 9 core agents
# ---------------------------------------------------------------------------

INITIAL_SKILLS: list[dict] = [
    {
        "name": "Search then Synthesize",
        "description": "Web search followed by structured synthesis of findings",
        "category": "research",
        "trigger_conditions": [
            "research", "find information about", "what is", "compare", "investigate",
        ],
        "steps": [
            "Use web_search with a specific, focused query (not vague)",
            "Fetch the top 2–3 result pages with fetch_page",
            "Check knowledge base with search_knowledge for existing Athanor docs",
            "Synthesize: key findings, contradictions, Athanor relevance",
            "Return structured report: Summary / Key Findings / Sources / Athanor Relevance",
        ],
        "tags": ["research", "web", "synthesis"],
        "created_by": "system",
    },
    {
        "name": "Media Request Workflow",
        "description": "Handle a request to add or find media in the stack",
        "category": "media",
        "trigger_conditions": [
            "add movie", "add show", "add series", "download", "watchlist",
            "sonarr", "radarr", "plex",
        ],
        "steps": [
            "Identify media type: movie (Radarr) or TV series (Sonarr)",
            "Search Radarr/Sonarr for existing entry before adding",
            "If not found: search by title, select best match, add with quality profile",
            "Confirm addition and report expected delivery time",
            "Optionally check Plex if media may already be available locally",
        ],
        "tags": ["media", "sonarr", "radarr"],
        "created_by": "system",
    },
    {
        "name": "Image Generation Pipeline",
        "description": "Generate an image via ComfyUI with quality prompt engineering",
        "category": "creative",
        "trigger_conditions": [
            "generate image", "create image", "make a picture", "draw", "illustrate",
            "portrait of", "scene of",
        ],
        "steps": [
            "Craft a detailed positive prompt: subject, style, lighting, quality modifiers",
            "Add negative prompt: blurry, low quality, deformed, watermark",
            "Choose model: Flux for photorealistic/detailed, Pony for anime/stylized",
            "Call generate_image with the crafted prompts and appropriate dimensions",
            "Return the generated image path and ComfyUI job ID",
        ],
        "tags": ["creative", "comfyui", "flux", "image"],
        "created_by": "system",
    },
    {
        "name": "Knowledge Indexing",
        "description": "Index new documentation into the knowledge base",
        "category": "knowledge",
        "trigger_conditions": [
            "index document", "add to knowledge base", "store this", "remember this doc",
            "update knowledge",
        ],
        "steps": [
            "Verify the document exists and is readable",
            "Classify the document category (research/adr/design/hardware/general)",
            "Extract the title from the first heading",
            "The knowledge indexer (index-knowledge.py) handles chunking and embedding",
            "After indexing: verify with search_knowledge to confirm retrieval",
        ],
        "tags": ["knowledge", "qdrant", "indexing"],
        "created_by": "system",
    },
    {
        "name": "Infrastructure Diagnosis",
        "description": "Diagnose a service or node health issue",
        "category": "infrastructure",
        "trigger_conditions": [
            "not working", "down", "failed", "error", "health check", "diagnose",
            "service issue", "container",
        ],
        "steps": [
            "Check Prometheus alerts for active firing rules",
            "Query Loki logs for the service in the last 30 minutes",
            "SSH to the affected node and check container status (docker ps)",
            "Check GPU/CPU/memory utilization (nvidia-smi, docker stats)",
            "Identify root cause: OOM, crash loop, config error, or network issue",
            "Report: symptom → root cause → recommended fix",
        ],
        "tags": ["infrastructure", "monitoring", "diagnosis"],
        "created_by": "system",
    },
    {
        "name": "Code Generation from Spec",
        "description": "Generate code from a specification or description",
        "category": "coding",
        "trigger_conditions": [
            "write a function", "implement", "generate code", "create a script",
            "write a class", "build an API",
        ],
        "steps": [
            "Read any relevant existing code files first (understand the context)",
            "Clarify: language, framework, constraints (async? typed? tested?)",
            "Write the implementation, following existing patterns in the codebase",
            "Add type hints and docstrings if the file uses them",
            "Verify with py_compile or tsc if applicable",
            "Return the complete code with usage example",
        ],
        "tags": ["coding", "generation"],
        "created_by": "system",
    },
    {
        "name": "Home Automation Query",
        "description": "Query or control Home Assistant entities",
        "category": "home",
        "trigger_conditions": [
            "turn on", "turn off", "what is the temperature", "is the door",
            "home assistant", "light", "thermostat", "sensor",
        ],
        "steps": [
            "Identify the relevant entity in Home Assistant",
            "For queries: call get_ha_state for the entity",
            "For controls: call set_ha_state with the desired state/attributes",
            "Confirm the action completed and report the new state",
        ],
        "tags": ["home", "home-assistant"],
        "created_by": "system",
    },
    {
        "name": "Stash Content Discovery",
        "description": "Search and retrieve content from the Stash media library",
        "category": "stash",
        "trigger_conditions": [
            "stash", "find scene", "performer", "studio", "search library",
        ],
        "steps": [
            "Use GraphQL search with filters: title, performer, studio, tags",
            "Return results with: title, performer, duration, studio, tags",
            "For ambiguous queries: ask for clarification before searching",
        ],
        "tags": ["stash", "media"],
        "created_by": "system",
    },
]


async def ensure_initial_skills() -> int:
    """Seed the library with initial skills if empty. Returns count added."""
    try:
        r = await _get_redis()
        existing = await r.hlen(SKILLS_KEY)
        if existing > 0:
            return 0

        added = 0
        for skill_def in INITIAL_SKILLS:
            await add_skill(**skill_def)
            added += 1

        logger.info("Seeded skill library with %d initial skills", added)
        return added
    except Exception as e:
        logger.warning("Failed to seed skills: %s", e)
        return 0
