"""Plan Generator — converts raw intents into researched execution plans.

The critical bridge between intent discovery and task execution.
Raw intents don't become tasks directly — they become ExecutionPlans
with research, approach, risk assessment, and agent assignments.
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

# Redis keys
PLANS_PENDING_KEY = "athanor:plans:pending"  # Sorted set: plan_id → priority
PLANS_ACTIVE_KEY = "athanor:plans:active"  # Hash: plan_id → JSON
PLANS_HISTORY_KEY = "athanor:plans:history"  # List (500 cap)
PLANS_REJECTED_REASONS_KEY = "athanor:plans:rejected_reasons"  # List for learning
KNOWN_INTENTS_KEY = "athanor:pipeline:known_intents"  # Hash: hash → JSON

HISTORY_MAX = 500
KNOWN_INTENTS_MAX = 500


@dataclass
class ExecutionPlan:
    """A researched, detailed execution proposal."""
    id: str
    intent_source: str
    intent_text: str
    title: str
    research_summary: str
    approach: str
    estimated_tasks: int
    assigned_agents: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high
    status: str = "draft"  # draft | pending_approval | approved | rejected | executing | completed
    created_at: float = 0.0
    approved_at: float | None = None
    approved_by: str | None = None
    rejection_reason: str | None = None
    priority_score: float = 0.5
    autonomy_managed: bool = False
    autonomy_phase_id: str | None = None
    autonomy_scope_note: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionPlan":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def generate_plan_from_intent(
    intent_source: str,
    intent_text: str,
    priority_hint: float = 0.5,
    metadata: dict | None = None,
) -> ExecutionPlan:
    """Generate an ExecutionPlan from a raw intent.

    Uses local reasoning model to research feasibility and create approach.
    Low-risk plans with governor Level A may auto-approve.
    """
    metadata = metadata or {}

    # Determine agent assignments based on intent content
    agents = _suggest_agents(intent_text, metadata)
    autonomy_managed = _is_autonomy_managed_plan(metadata)
    agents, autonomy_phase_id, autonomy_scope_note = _apply_autonomy_scope_to_agents(agents, metadata)

    # Estimate task count from complexity
    est_tasks = _estimate_task_count(intent_text)

    # Assess risk
    risk = _assess_risk(intent_text, agents)

    # Generate title from intent
    title = _generate_title(intent_text)

    plan = ExecutionPlan(
        id=f"plan-{uuid.uuid4().hex[:12]}",
        intent_source=intent_source,
        intent_text=intent_text,
        title=title,
        research_summary=f"Intent from {intent_source}: {intent_text[:200]}",
        approach=f"Execute via {', '.join(agents)} with {est_tasks} tasks",
        estimated_tasks=est_tasks,
        assigned_agents=agents,
        risk_level=risk,
        status="pending_approval" if risk != "low" else "draft",
        priority_score=priority_hint,
        autonomy_managed=autonomy_managed,
        autonomy_phase_id=autonomy_phase_id,
        autonomy_scope_note=autonomy_scope_note,
    )

    # Try LLM-enhanced plan generation (non-blocking)
    try:
        enhanced = await _enhance_plan_with_llm(plan)
        if enhanced:
            plan.research_summary = enhanced.get("research_summary", plan.research_summary)
            plan.approach = enhanced.get("approach", plan.approach)
            plan.estimated_tasks = enhanced.get("estimated_tasks", plan.estimated_tasks)
            plan.risk_level = enhanced.get("risk_level", plan.risk_level)
    except Exception as e:
        logger.debug("LLM plan enhancement failed, using heuristics: %s", e)

    if autonomy_scope_note:
        plan.research_summary = f"{plan.research_summary.rstrip()} Autonomy scope: {autonomy_scope_note}".strip()
        plan.approach = f"{plan.approach.rstrip()} Autonomy scope: {autonomy_scope_note}".strip()

    # Store in Redis
    await _store_plan(plan)

    logger.info("Generated plan %s: %s (risk=%s, tasks=%d, agents=%s)",
                plan.id, plan.title, plan.risk_level, plan.estimated_tasks, plan.assigned_agents)
    return plan


async def _enhance_plan_with_llm(plan: ExecutionPlan) -> dict | None:
    """Use local reasoning model to enhance plan with research and approach."""
    try:
        import httpx
        from .config import settings

        prompt = f"""Analyze this intent and create a brief execution plan.

Intent: {plan.intent_text}
Source: {plan.intent_source}

Respond with JSON only:
{{
    "research_summary": "Brief feasibility analysis (2-3 sentences)",
    "approach": "Recommended implementation approach (2-3 sentences)",
    "estimated_tasks": <number 1-20>,
    "risk_level": "low|medium|high"
}}"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.litellm_url}/v1/chat/completions",
                json={
                    "model": "reasoning",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # Strip thinking tags if present
                if "<think>" in content:
                    content = content.split("</think>")[-1].strip()
                # Try to parse JSON
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
    except Exception as e:
        logger.debug("LLM plan enhancement error: %s", e)
    return None


async def _store_plan(plan: ExecutionPlan):
    """Store plan in Redis."""
    r = await _get_redis()
    await r.hset(PLANS_ACTIVE_KEY, plan.id, json.dumps(plan.to_dict()))
    if plan.status == "pending_approval":
        await r.zadd(PLANS_PENDING_KEY, {plan.id: plan.priority_score})


async def get_plan(plan_id: str) -> ExecutionPlan | None:
    """Get a plan by ID."""
    r = await _get_redis()
    raw = await r.hget(PLANS_ACTIVE_KEY, plan_id)
    if not raw:
        return None
    text = raw.decode() if isinstance(raw, bytes) else raw
    return ExecutionPlan.from_dict(json.loads(text))


async def list_plans(status: str = "") -> list[dict]:
    """List plans with optional status filter."""
    r = await _get_redis()
    all_plans = await r.hgetall(PLANS_ACTIVE_KEY)
    result = []
    for _pid, raw in all_plans.items():
        text = raw.decode() if isinstance(raw, bytes) else raw
        try:
            plan_data = json.loads(text)
            if not status or plan_data.get("status") == status:
                result.append(plan_data)
        except json.JSONDecodeError:
            pass
    result.sort(key=lambda p: p.get("priority_score", 0), reverse=True)
    return result


async def approve_plan(plan_id: str, actor: str = "shaun") -> ExecutionPlan | None:
    """Approve a plan, triggering task decomposition."""
    plan = await get_plan(plan_id)
    if not plan or plan.status not in ("pending_approval", "draft"):
        return None

    plan.status = "approved"
    plan.approved_at = time.time()
    plan.approved_by = actor

    r = await _get_redis()
    await r.hset(PLANS_ACTIVE_KEY, plan.id, json.dumps(plan.to_dict()))
    await r.zrem(PLANS_PENDING_KEY, plan.id)

    logger.info("Plan %s approved by %s", plan_id, actor)
    return plan


async def reject_plan(plan_id: str, reason: str = "", actor: str = "shaun") -> ExecutionPlan | None:
    """Reject a plan with a reason for future learning."""
    plan = await get_plan(plan_id)
    if not plan or plan.status not in ("pending_approval", "draft"):
        return None

    plan.status = "rejected"
    plan.rejection_reason = reason

    r = await _get_redis()
    await r.hset(PLANS_ACTIVE_KEY, plan.id, json.dumps(plan.to_dict()))
    await r.zrem(PLANS_PENDING_KEY, plan.id)

    # Store rejection reason for learning
    if reason:
        rejection_entry = json.dumps({
            "plan_id": plan_id,
            "intent": plan.intent_text[:200],
            "reason": reason,
            "ts": time.time(),
        })
        await r.lpush(PLANS_REJECTED_REASONS_KEY, rejection_entry)
        await r.ltrim(PLANS_REJECTED_REASONS_KEY, 0, 99)

    # Move to history
    await _archive_plan(plan)

    logger.info("Plan %s rejected: %s", plan_id, reason)
    return plan


async def steer_plan(plan_id: str, instructions: str) -> ExecutionPlan | None:
    """Add steering instructions to a plan before approval."""
    plan = await get_plan(plan_id)
    if not plan:
        return None

    plan.approach = f"{plan.approach}\n\nSteering: {instructions}"

    r = await _get_redis()
    await r.hset(PLANS_ACTIVE_KEY, plan.id, json.dumps(plan.to_dict()))

    logger.info("Plan %s steered: %s", plan_id, instructions[:100])
    return plan


async def complete_plan(plan_id: str):
    """Mark a plan as completed and archive it."""
    plan = await get_plan(plan_id)
    if not plan:
        return

    plan.status = "completed"
    await _archive_plan(plan)

    r = await _get_redis()
    await r.hdel(PLANS_ACTIVE_KEY, plan.id)


async def _archive_plan(plan: ExecutionPlan):
    """Move plan to history list."""
    r = await _get_redis()
    await r.lpush(PLANS_HISTORY_KEY, json.dumps(plan.to_dict()))
    await r.ltrim(PLANS_HISTORY_KEY, 0, HISTORY_MAX - 1)


async def decompose_plan_to_tasks(plan: ExecutionPlan) -> list[dict]:
    """Decompose an approved plan into task specifications.

    Returns list of task specs ready for governor.gate_task_submission().
    """
    if plan.status != "approved":
        return []

    assigned_agents = list(plan.assigned_agents)
    if plan.autonomy_managed:
        assigned_agents, autonomy_phase_id, autonomy_scope_note = _apply_autonomy_scope_to_agents(
            assigned_agents,
            {"_autonomy_managed": True},
        )
        if autonomy_phase_id:
            plan.autonomy_phase_id = autonomy_phase_id
        if autonomy_scope_note:
            plan.autonomy_scope_note = autonomy_scope_note
            if autonomy_scope_note not in plan.approach:
                plan.approach = f"{plan.approach.rstrip()} Autonomy scope: {autonomy_scope_note}".strip()

    plan.status = "executing"
    r = await _get_redis()
    await r.hset(PLANS_ACTIVE_KEY, plan.id, json.dumps(plan.to_dict()))

    tasks = []
    # Simple decomposition: one task per agent assignment
    for i, agent in enumerate(assigned_agents):
        task_spec = {
            "agent": agent,
            "prompt": f"{plan.approach}\n\nContext: {plan.intent_text[:500]}",
            "priority": "high" if plan.priority_score > 0.7 else "normal",
            "metadata": {
                "source": "pipeline",
                "plan_id": plan.id,
                "plan_title": plan.title,
                "task_index": i,
            },
        }
        tasks.append(task_spec)

    # If more tasks estimated than agents, create additional task specs
    remaining = plan.estimated_tasks - len(assigned_agents)
    if remaining > 0 and assigned_agents:
        primary = assigned_agents[0]
        for i in range(remaining):
            tasks.append({
                "agent": primary,
                "prompt": f"Continue work on: {plan.title}\n\n{plan.approach}",
                "priority": "normal",
                "metadata": {
                    "source": "pipeline",
                    "plan_id": plan.id,
                    "plan_title": plan.title,
                    "task_index": len(assigned_agents) + i,
                },
            })

    logger.info("Decomposed plan %s into %d tasks", plan.id, len(tasks))
    return tasks


async def get_pending_count() -> int:
    """Get count of plans pending approval."""
    r = await _get_redis()
    return await r.zcard(PLANS_PENDING_KEY)


async def record_intent_hash(intent_text: str, plan_id: str):
    """Record a known intent to prevent duplicates."""
    r = await _get_redis()
    # Use simple hash for dedup
    import hashlib
    h = hashlib.md5(intent_text.encode()).hexdigest()[:16]
    await r.hset(KNOWN_INTENTS_KEY, h, json.dumps({
        "plan_id": plan_id,
        "text": intent_text[:200],
        "ts": time.time(),
    }))
    # Prune if too large
    count = await r.hlen(KNOWN_INTENTS_KEY)
    if count > KNOWN_INTENTS_MAX:
        # Remove oldest entries (not efficient but rare)
        all_entries = await r.hgetall(KNOWN_INTENTS_KEY)
        entries = []
        for k, v in all_entries.items():
            key = k.decode() if isinstance(k, bytes) else k
            val = v.decode() if isinstance(v, bytes) else v
            try:
                data = json.loads(val)
                entries.append((key, data.get("ts", 0)))
            except json.JSONDecodeError:
                entries.append((key, 0))
        entries.sort(key=lambda x: x[1])
        to_remove = entries[:count - KNOWN_INTENTS_MAX + 50]
        if to_remove:
            await r.hdel(KNOWN_INTENTS_KEY, *[k for k, _ in to_remove])


async def is_duplicate_intent(intent_text: str) -> bool:
    """Check if an intent is already known."""
    import hashlib
    h = hashlib.md5(intent_text.encode()).hexdigest()[:16]
    r = await _get_redis()
    return await r.hexists(KNOWN_INTENTS_KEY, h)


# --- Heuristic helpers ---

def _is_autonomy_managed_plan(metadata: dict | None) -> bool:
    return bool(dict(metadata or {}).get("_autonomy_managed"))


def _load_active_autonomy_phase_scope() -> tuple[str | None, list[str]]:
    from .model_governance import get_current_autonomy_policy

    policy = get_current_autonomy_policy()
    if not policy.is_active:
        return None, []
    return policy.phase_id, sorted(policy.enabled_agents)


def _apply_autonomy_scope_to_agents(
    agents: list[str],
    metadata: dict | None,
) -> tuple[list[str], str | None, str | None]:
    if not _is_autonomy_managed_plan(metadata):
        return list(agents), None, None

    phase_id, enabled_agents = _load_active_autonomy_phase_scope()
    if not enabled_agents:
        return list(agents), phase_id, None

    requested_agents = [str(agent).strip() for agent in agents if str(agent).strip()]
    filtered_agents = [agent for agent in requested_agents if agent in enabled_agents]
    blocked_agents = [agent for agent in requested_agents if agent not in enabled_agents]

    if filtered_agents:
        if not blocked_agents:
            return filtered_agents, phase_id, None
        note = (
            f"Filtered blocked agents {blocked_agents} under autonomy phase "
            f"{phase_id or 'unknown'}; kept {filtered_agents}."
        )
        return filtered_agents, phase_id, note

    fallback_agent = "general-assistant" if "general-assistant" in enabled_agents else enabled_agents[0]
    if blocked_agents:
        note = (
            f"Filtered blocked agents {blocked_agents} under autonomy phase "
            f"{phase_id or 'unknown'}; fell back to {fallback_agent}."
        )
    else:
        note = (
            f"No eligible autonomous agent matched under autonomy phase "
            f"{phase_id or 'unknown'}; fell back to {fallback_agent}."
        )
    return [fallback_agent], phase_id, note

def _suggest_agents(text: str, metadata: dict) -> list[str]:
    """Suggest agents based on intent content."""
    text_lower = text.lower()

    # Check metadata override
    if "agent" in metadata:
        return [metadata["agent"]]

    agents = []
    if any(w in text_lower for w in ("code", "implement", "refactor", "test", "bug", "fix")):
        agents.append("coding-agent")
    if any(w in text_lower for w in ("research", "investigate", "analyze", "compare")):
        agents.append("research-agent")
    if any(w in text_lower for w in ("media", "sonarr", "radarr", "plex", "movie", "tv")):
        agents.append("media-agent")
    if any(w in text_lower for w in ("home", "light", "climate", "automation", "ha ")):
        agents.append("home-agent")
    if any(w in text_lower for w in ("creative", "image", "generate", "comfyui", "portrait")):
        agents.append("creative-agent")
    if any(w in text_lower for w in ("knowledge", "document", "search", "qdrant")):
        agents.append("knowledge-agent")
    if any(w in text_lower for w in ("stash", "scene", "performer", "adult")):
        agents.append("stash-agent")
    if any(w in text_lower for w in ("data", "index", "embed", "personal")):
        agents.append("data-curator")

    return agents if agents else ["general-assistant"]


def _estimate_task_count(text: str) -> int:
    """Estimate number of tasks from intent complexity."""
    words = len(text.split())
    if words < 20:
        return 1
    elif words < 50:
        return 2
    elif words < 100:
        return 3
    else:
        return min(5, words // 30)


def _assess_risk(text: str, agents: list[str]) -> str:
    """Assess risk level of a plan."""
    high_risk_agents = {"coding-agent", "home-agent"}
    high_risk_words = {"delete", "remove", "drop", "destroy", "reset", "overwrite", "production"}

    text_lower = text.lower()
    if any(w in text_lower for w in high_risk_words):
        return "high"
    if any(a in high_risk_agents for a in agents):
        return "medium"
    return "low"


def _generate_title(text: str) -> str:
    """Generate a short title from intent text."""
    # Take first sentence or first 60 chars
    sentences = text.split(".")
    title = sentences[0].strip()
    if len(title) > 60:
        title = title[:57] + "..."
    # Remove markdown/formatting
    title = title.lstrip("#-*[ ]")
    return title.strip() or "Untitled plan"
