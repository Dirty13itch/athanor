"""Supervisor — CLI supervisor → local worker task decomposition.

Bridges cloud CLI managers (Claude Code, Codex, Gemini, Aider) with
local agent workforce. Routes tasks based on policy class and task type.

All cloud interaction is via headless CLI dispatch (subscription-covered),
NOT via LiteLLM API calls. The supervisor sets task metadata and the
multi-cli-dispatch daemon handles actual CLI invocation.
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

# Redis keys
SUPERVISOR_QUEUE_KEY = "athanor:supervisor:queue"
SUPERVISOR_RESULTS_KEY = "athanor:supervisor:results"
SUPERVISOR_SESSIONS_KEY = "athanor:supervisor:sessions"

RESULTS_MAX = 200
SESSIONS_MAX = 100

# CLI target mapping by task class
CLI_ROUTING = {
    "interactive_architecture": {"primary": "claude_code", "fallback": "local_reasoning"},
    "multi_file_implementation": {"primary": "claude_code_sonnet", "fallback": "codex_cli"},
    "async_backlog_execution": {"primary": "codex_cli", "fallback": "aider"},
    "repo_wide_audit": {"primary": "gemini_cli", "fallback": "claude_code"},
    "code_review": {"primary": "codex_cli", "fallback": "gemini_cli"},
    "automated_debugging": {"primary": "codex_cli", "fallback": "claude_code"},
    "consensus_review": {"primary": "all_cli", "fallback": "claude_code"},
    "search_heavy_planning": {"primary": "gemini_cli", "fallback": "local_reasoning"},
    "cheap_bulk_transform": {"primary": "aider", "fallback": "local_worker"},
    "quota_harvest": {"primary": "gemini_cli", "fallback": None},
    "security_audit": {"primary": "all_cli", "fallback": None},
    "creative_uncensored": {"primary": "local_creative", "fallback": None},
    "private_internal": {"primary": "local_reasoning", "fallback": None},
}

# Task type inference from prompt content
TASK_TYPE_KEYWORDS = {
    "interactive_architecture": ["architecture", "design", "system design", "tradeoff"],
    "multi_file_implementation": ["implement", "build", "create", "feature"],
    "code_review": ["review", "audit code", "check code"],
    "automated_debugging": ["debug", "fix bug", "error", "failing"],
    "repo_wide_audit": ["full audit", "codebase scan", "repo-wide"],
    "search_heavy_planning": ["research", "investigate", "compare", "evaluate"],
    "cheap_bulk_transform": ["bulk", "docstring", "format", "rename"],
    "creative_uncensored": ["creative", "fiction", "story", "portrait", "nsfw"],
    "private_internal": ["personal", "home", "private", "iot"],
}


@dataclass
class SupervisionRequest:
    """A request for CLI supervision of a task."""
    id: str
    task_id: str
    task_class: str
    cli_target: str
    fallback: str | None
    prompt: str
    agent: str
    priority: str
    delegation_pattern: str  # local_only | local_with_cli_review | cli_execute | cli_consensus
    status: str = "pending"  # pending | dispatched | completed | failed
    result: dict = field(default_factory=dict)
    created_at: float = 0.0
    completed_at: float | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


def classify_task_type(prompt: str, agent: str, metadata: dict | None = None) -> str:
    """Classify a task into a task class based on content and agent."""
    metadata = metadata or {}

    # Check metadata override
    if "task_class" in metadata:
        return metadata["task_class"]

    prompt_lower = prompt.lower()

    # Agent-based defaults
    agent_defaults = {
        "creative-agent": "creative_uncensored",
        "stash-agent": "creative_uncensored",
        "home-agent": "private_internal",
        "knowledge-agent": "private_internal",
        "data-curator": "private_internal",
    }
    if agent in agent_defaults:
        return agent_defaults[agent]

    # Keyword matching
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            return task_type

    # Default based on agent
    if agent == "coding-agent":
        return "multi_file_implementation"
    if agent == "research-agent":
        return "search_heavy_planning"

    return "async_backlog_execution"


def get_cli_routing(task_class: str) -> dict:
    """Get CLI routing for a task class."""
    return CLI_ROUTING.get(task_class, CLI_ROUTING["async_backlog_execution"])


async def create_supervision_request(
    task_id: str,
    prompt: str,
    agent: str,
    priority: str = "normal",
    metadata: dict | None = None,
) -> SupervisionRequest:
    """Create a supervision request for a task.

    Classifies the task, determines CLI target and delegation pattern,
    and queues for the multi-cli-dispatch daemon.
    """
    from .policy_router import classify_policy, get_execution_lane

    task_class = classify_task_type(prompt, agent, metadata)
    routing = get_cli_routing(task_class)
    policy = classify_policy(agent, prompt, metadata)
    lane = get_execution_lane(policy)

    # Determine delegation pattern
    if lane == "LOCAL_ONLY":
        pattern = "local_only"
    elif routing["primary"] == "all_cli":
        pattern = "cli_consensus"
    elif routing["primary"] in ("local_reasoning", "local_worker", "local_creative"):
        pattern = "local_only"
    elif lane == "CLI_MANAGED":
        pattern = "cli_execute"
    else:
        pattern = "local_with_cli_review"

    request = SupervisionRequest(
        id=f"sup-{uuid.uuid4().hex[:12]}",
        task_id=task_id,
        task_class=task_class,
        cli_target=routing["primary"],
        fallback=routing.get("fallback"),
        prompt=prompt,
        agent=agent,
        priority=priority,
        delegation_pattern=pattern,
    )

    # Queue for dispatch (only if not local-only)
    if pattern != "local_only":
        r = await _get_redis()
        await r.lpush(SUPERVISOR_QUEUE_KEY, json.dumps(asdict(request)))

    logger.info(
        "Supervision request %s: task=%s class=%s cli=%s pattern=%s",
        request.id, task_id, task_class, routing["primary"], pattern,
    )
    return request


async def record_supervision_result(
    request_id: str,
    cli_tool: str,
    success: bool,
    output: str = "",
    quality_score: float = 0.0,
):
    """Record the result of a CLI supervision action."""
    r = await _get_redis()
    result = json.dumps({
        "request_id": request_id,
        "cli_tool": cli_tool,
        "success": success,
        "output": output[:2000],
        "quality_score": quality_score,
        "ts": time.time(),
    })
    await r.lpush(SUPERVISOR_RESULTS_KEY, result)
    await r.ltrim(SUPERVISOR_RESULTS_KEY, 0, RESULTS_MAX - 1)


async def get_pending_supervision() -> list[dict]:
    """Get pending supervision requests."""
    r = await _get_redis()
    raw = await r.lrange(SUPERVISOR_QUEUE_KEY, 0, 20)
    results = []
    for item in raw:
        text = item.decode() if isinstance(item, bytes) else item
        try:
            results.append(json.loads(text))
        except json.JSONDecodeError:
            pass
    return results


async def get_supervision_stats() -> dict:
    """Get supervision statistics."""
    r = await _get_redis()

    queue_len = await r.llen(SUPERVISOR_QUEUE_KEY)
    results_raw = await r.lrange(SUPERVISOR_RESULTS_KEY, 0, 49)

    total = len(results_raw)
    successes = 0
    for item in results_raw:
        text = item.decode() if isinstance(item, bytes) else item
        try:
            data = json.loads(text)
            if data.get("success"):
                successes += 1
        except json.JSONDecodeError:
            pass

    return {
        "queue_depth": queue_len,
        "recent_results": total,
        "success_rate": round(successes / total, 3) if total else 0,
    }


async def supervise_project(
    project_id: str,
    instruction: str,
    milestones: list[dict] | None = None,
) -> dict:
    """Decompose a project into milestones and assign cloud managers.

    Called from MCP bridge or Claude Code manager session.
    """
    from .project_tracker import create_milestone, get_milestones

    created = []
    if milestones:
        for m in milestones:
            milestone = await create_milestone(
                project_id=project_id,
                title=m.get("title", ""),
                description=m.get("description", ""),
                acceptance_criteria=m.get("criteria", []),
                assigned_agents=m.get("agents", []),
            )
            created.append(milestone.to_dict())

    existing = await get_milestones(project_id)

    return {
        "project_id": project_id,
        "instruction": instruction,
        "milestones_created": len(created),
        "total_milestones": len(existing),
        "created": created,
    }


async def review_task_output(task_id: str) -> dict:
    """Score a completed task output for quality.

    Uses the grader model via LiteLLM to evaluate output quality.
    Records feedback for the learning loop.
    """
    from .tasks import get_task

    task = await get_task(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    if task.status != "completed":
        return {"error": f"Task {task_id} not completed (status={task.status})"}

    # Score with grader model
    quality_score = 0.5  # Default
    try:
        import httpx
        from .config import settings

        prompt = f"""Rate the quality of this task output on a scale of 0.0 to 1.0.

Task prompt: {task.prompt[:500]}
Task result: {task.result[:1000] if task.result else 'No result'}

Respond with ONLY a number between 0.0 and 1.0."""

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.litellm_url}/v1/chat/completions",
                json={
                    "model": "grader",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,
                    "temperature": 0.0,
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                # Strip thinking tags
                if "<think>" in content:
                    content = content.split("</think>")[-1].strip()
                try:
                    quality_score = max(0.0, min(1.0, float(content)))
                except ValueError:
                    pass
    except Exception as e:
        logger.debug("Task quality scoring failed: %s", e)

    # Record outcome
    from .work_pipeline import record_outcome
    await record_outcome(
        task_id=task_id,
        agent=task.agent,
        prompt=task.prompt[:500],
        quality_score=quality_score,
        success=task.status == "completed",
        plan_id=task.metadata.get("plan_id", "") if task.metadata else "",
        project_id=task.metadata.get("project", "") if task.metadata else "",
    )

    return {
        "task_id": task_id,
        "quality_score": quality_score,
        "agent": task.agent,
        "status": task.status,
    }
