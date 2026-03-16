"""Task Execution Engine — background autonomous work for agents.

Transforms agents from reactive chat endpoints to autonomous workers.
Tasks are Redis-backed, executed by a background worker, with step
logging and progress broadcasting via GWT workspace.

Architecture:
    - Tasks stored in Redis hash (athanor:tasks:{id})
    - Background worker polls every 5s, picks highest-priority pending task
    - Worker streams agent execution via astream_events() to capture tool call steps
    - Completion/failure broadcast to GWT workspace
    - Max 2 concurrent tasks (inference backend can handle parallel requests)
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

from langchain_core.messages import HumanMessage

from .config import settings

logger = logging.getLogger(__name__)

TASKS_KEY = "athanor:tasks"
TASKS_CHANNEL = "athanor:tasks:events"
TASK_WORKER_INTERVAL = 5.0  # seconds between polls
MAX_CONCURRENT_TASKS = 6
TASK_TIMEOUT = 600  # 10 min max per task
MAX_TASK_RETRIES = 1  # Auto-retry failed tasks once with error context
TASK_TTL_COMPLETED = 86400  # 24h — purge completed tasks
TASK_TTL_FAILED = 604800  # 7d — keep failed tasks longer for debugging
CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

_worker_task: asyncio.Task | None = None
_running_count = 0


@dataclass
class Task:
    """A unit of autonomous work for an agent."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent: str = ""
    prompt: str = ""
    priority: str = "normal"  # critical, high, normal, low
    status: str = "pending"   # pending, pending_approval, running, completed, failed, cancelled
    result: str = ""
    error: str = ""
    steps: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict = field(default_factory=dict)
    parent_task_id: str = ""  # For delegated sub-tasks
    retry_count: int = 0  # How many times this task has been retried
    previous_error: str = ""  # Error from previous attempt (for retry context)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def duration_ms(self) -> int | None:
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at) * 1000)
        return None


PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}

# Agent-specific task capabilities for system prompt
_AGENT_TASK_HINTS = {
    "coding-agent": (
        "You have filesystem tools (read_file, write_file, list_directory, search_files) "
        "and code execution (run_command). Plan your approach, then execute step by step. "
        "Write files, run tests, fix failures, and iterate until the task is complete."
    ),
    "general-assistant": (
        "You have service monitoring tools and filesystem access. "
        "Check service health, inspect logs, and report findings with specifics."
    ),
    "research-agent": (
        "You have web search, page fetching, and knowledge base tools. "
        "Search thoroughly, cross-reference sources, and synthesize findings."
    ),
    "knowledge-agent": (
        "You have knowledge base search and document listing tools. "
        "Search the knowledge base, identify gaps, and report findings."
    ),
    "media-agent": (
        "You have Sonarr, Radarr, and Plex tools. "
        "Check media services, report notable items, and manage content."
    ),
    "home-agent": (
        "You have Home Assistant tools for entity state, services, and automations. "
        "Check states, identify anomalies, and take action when appropriate."
    ),
    "creative-agent": (
        "You have ComfyUI image and video generation tools. "
        "Generate content as requested, monitor the queue, and report results."
    ),
    "stash-agent": (
        "You have Stash library management tools. "
        "Search, browse, organize, and tag content as requested."
    ),
}


def _build_task_prompt(task: Task) -> str:
    """Build a task-mode system prompt for autonomous execution."""
    parts = [
        "You are executing an autonomous task. Work independently to completion.",
        "",
        f"Task ID: {task.id}",
        f"Priority: {task.priority}",
    ]

    # Add retry context if this is a retry
    if task.retry_count > 0 and task.previous_error:
        parts.extend([
            "",
            f"IMPORTANT: This is retry #{task.retry_count}. The previous attempt failed with:",
            f"  Error: {task.previous_error}",
            "",
            "Analyze what went wrong and try a different approach. Do NOT repeat the same steps that caused the failure.",
        ])

    # Add agent-specific hints
    hint = _AGENT_TASK_HINTS.get(task.agent, "")
    if hint:
        parts.extend(["", hint])

    lease = (task.metadata or {}).get("execution_lease", {})
    if lease:
        fallback = ", ".join(lease.get("fallback", [])) or "none"
        parts.extend([
            "",
            "Execution lease:",
            f"- Approved provider lane: {lease.get('provider', 'unknown')}",
            f"- Surface: {lease.get('surface', 'unknown')}",
            f"- Privacy: {lease.get('privacy', 'unknown')}",
            f"- Parallel allowance: {lease.get('max_parallel_children', 1)}",
            f"- Fallback: {fallback}",
            f"- Reason: {lease.get('reason', '')}",
            "- Treat this as policy guidance for escalation or handoff work.",
            "- If the approved external lane is not directly callable from your current runtime, produce an exact handoff bundle or execution plan for it.",
        ])

    parts.extend([
        "",
        "Instructions:",
        "1. Plan your approach before acting",
        "2. Execute steps one at a time using your tools",
        "3. After each step, assess progress",
        "4. If stuck on a step, try an alternative approach",
        "5. When complete, provide a clear summary of what you accomplished",
        "6. If you cannot complete the task, explain exactly what blocked you",
    ])

    return "\n".join(parts)


async def _maybe_retry(task: Task):
    """Auto-retry a failed task if under the retry limit.

    Creates a new task with the same parameters plus error context
    from the failed attempt. The retry gets bumped priority.
    """
    if task.retry_count >= MAX_TASK_RETRIES:
        logger.info(
            "Task %s exhausted retries (%d/%d), not retrying",
            task.id, task.retry_count, MAX_TASK_RETRIES,
        )
        return

    try:
        retry = Task(
            agent=task.agent,
            prompt=task.prompt,
            priority=task.priority,
            metadata={**task.metadata, "retry_of": task.id, "source": "auto-retry"},
            parent_task_id=task.parent_task_id,
            retry_count=task.retry_count + 1,
            previous_error=task.error[:2000],
        )

        r = await _get_redis()
        await r.hset(TASKS_KEY, retry.id, json.dumps(retry.to_dict()))

        logger.info(
            "Task %s auto-retry submitted as %s (attempt %d/%d)",
            task.id, retry.id, retry.retry_count, MAX_TASK_RETRIES,
        )

        await r.publish(TASKS_CHANNEL, json.dumps({
            "event": "task_retried",
            "task_id": retry.id,
            "original_task_id": task.id,
            "retry_count": retry.retry_count,
            "timestamp": time.time(),
        }))

    except Exception as e:
        logger.warning("Failed to auto-retry task %s: %s", task.id, e)


async def _cleanup_old_tasks():
    """Purge completed/failed tasks past their TTL."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        now = time.time()
        removed = 0

        for task_id, v in raw.items():
            t = Task.from_dict(json.loads(v))
            if not t.completed_at:
                continue

            age = now - t.completed_at
            if t.status == "completed" and age > TASK_TTL_COMPLETED:
                await r.hdel(TASKS_KEY, task_id)
                removed += 1
            elif t.status in ("failed", "cancelled") and age > TASK_TTL_FAILED:
                await r.hdel(TASKS_KEY, task_id)
                removed += 1

        if removed:
            logger.info("Cleaned up %d expired tasks", removed)
    except Exception as e:
        logger.warning("Task cleanup error: %s", e)


async def _get_redis():
    """Reuse workspace Redis connection."""
    from .workspace import get_redis
    return await get_redis()


async def submit_task(
    agent: str,
    prompt: str,
    priority: str = "normal",
    metadata: dict | None = None,
    parent_task_id: str = "",
) -> Task:
    """Submit a new task for background execution.

    Returns the created Task (status=pending). The background worker
    will pick it up and execute it through the specified agent.
    """
    from .agents import list_agents

    available = list_agents()
    if agent not in available:
        raise ValueError(f"Agent '{agent}' not found. Available: {available}")

    task_metadata = metadata or {}
    if agent in {"coding-agent", "research-agent"}:
        from .subscriptions import attach_task_execution_lease

        try:
            task_metadata = await attach_task_execution_lease(
                requester=agent,
                prompt=prompt,
                priority=priority,
                metadata=task_metadata,
            )
        except Exception as e:
            logger.warning("Failed to attach execution lease to task for %s: %s", agent, e)

    task = Task(
        agent=agent,
        prompt=prompt,
        priority=priority if priority in PRIORITY_ORDER else "normal",
        metadata=task_metadata,
        parent_task_id=parent_task_id,
    )

    # Work-planner tasks for high-impact agents require morning approval
    if task_metadata.get("requires_approval"):
        task.status = "pending_approval"

    r = await _get_redis()
    await r.hset(TASKS_KEY, task.id, json.dumps(task.to_dict()))

    logger.info(
        "Task %s submitted: agent=%s priority=%s prompt=%.80s",
        task.id, agent, priority, prompt,
    )

    # Publish event for any listeners
    await r.publish(TASKS_CHANNEL, json.dumps({
        "event": "task_submitted",
        "task_id": task.id,
        "agent": agent,
        "timestamp": time.time(),
    }))

    return task


async def get_task(task_id: str) -> Task | None:
    """Get a task by ID."""
    try:
        r = await _get_redis()
        raw = await r.hget(TASKS_KEY, task_id)
        if raw:
            return Task.from_dict(json.loads(raw))
    except Exception as e:
        logger.warning("Failed to get task %s: %s", task_id, e)
    return None


async def list_tasks(
    status: str = "",
    agent: str = "",
    limit: int = 50,
) -> list[dict]:
    """List tasks with optional filters."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        tasks = [Task.from_dict(json.loads(v)) for v in raw.values()]

        if status:
            tasks = [t for t in tasks if t.status == status]
        if agent:
            tasks = [t for t in tasks if t.agent == agent]

        # Sort: pending first (by priority then created_at), then recent first
        def sort_key(t):
            if t.status == "pending":
                return (0, PRIORITY_ORDER.get(t.priority, 2), t.created_at)
            return (1, 0, -t.created_at)

        tasks.sort(key=sort_key)
        return [t.to_dict() for t in tasks[:limit]]
    except Exception as e:
        logger.warning("Failed to list tasks: %s", e)
        return []


async def cancel_task(task_id: str) -> bool:
    """Cancel a pending or running task."""
    try:
        r = await _get_redis()
        raw = await r.hget(TASKS_KEY, task_id)
        if not raw:
            return False

        task = Task.from_dict(json.loads(raw))
        if task.status not in ("pending", "running", "pending_approval"):
            return False

        task.status = "cancelled"
        task.completed_at = time.time()
        await r.hset(TASKS_KEY, task_id, json.dumps(task.to_dict()))

        logger.info("Task %s cancelled", task_id)
        return True
    except Exception as e:
        logger.warning("Failed to cancel task %s: %s", task_id, e)
        return False


async def _update_task(task: Task):
    """Persist task state to Redis."""
    try:
        r = await _get_redis()
        await r.hset(TASKS_KEY, task.id, json.dumps(task.to_dict()))
    except Exception as e:
        logger.warning("Failed to update task %s: %s", task.id, e)


async def _get_next_pending() -> Task | None:
    """Get the highest-priority pending task."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        pending = []
        for v in raw.values():
            t = Task.from_dict(json.loads(v))
            if t.status == "pending":
                pending.append(t)

        if not pending:
            return None

        # Sort by priority (critical first), then by created_at (oldest first)
        pending.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 2), t.created_at))
        return pending[0]
    except Exception as e:
        logger.warning("Failed to get next pending task: %s", e)
        return None


async def approve_task(task_id: str) -> bool:
    """Approve a pending_approval task, moving it to pending for execution."""
    task = await get_task(task_id)
    if not task:
        return False
    if task.status != "pending_approval":
        return False
    task.status = "pending"
    await _update_task(task)
    logger.info("Task %s approved for execution (agent=%s)", task_id, task.agent)
    return True


async def reject_task(task_id: str, reason: str = "Rejected by operator") -> bool:
    """Reject a pending_approval task."""
    task = await get_task(task_id)
    if not task:
        return False
    if task.status != "pending_approval":
        return False
    task.status = "cancelled"
    task.result = reason
    await _update_task(task)
    logger.info("Task %s rejected (agent=%s): %s", task_id, task.agent, reason)
    return True


async def _record_skill_execution_for_task(task: Task, success: bool):
    """Fire-and-forget: record task outcome against the best matching skill.

    Only records if the task prompt matches a skill above the 0.3 relevance
    threshold. Silently skips if no match or skill library is unavailable.
    """
    try:
        from .skill_learning import find_matching_skill, record_execution
        match = await find_matching_skill(task.prompt, threshold=0.3)
        if match:
            skill_id, relevance = match
            await record_execution(
                skill_id=skill_id,
                success=success,
                duration_ms=float(task.duration_ms or 0),
                context={"task_id": task.id, "agent": task.agent, "relevance": round(relevance, 2)},
            )
            logger.debug(
                "Skill execution recorded: skill=%s success=%s relevance=%.2f task=%s",
                skill_id, success, relevance, task.id,
            )
    except Exception as e:
        logger.debug("Skill recording skipped for task %s: %s", task.id, e)


async def _auto_extract_skill(task: Task):
    """Fire-and-forget: extract a reusable skill from a successful task's tool sequence."""
    try:
        from .skill_learning import extract_skill_from_task
        skill_id = await extract_skill_from_task(
            task_id=task.id,
            agent=task.agent,
            prompt=task.prompt,
            steps=task.steps,
            quality_score=0.8,  # default for completed tasks; overridden by judge if available
        )
        if skill_id:
            logger.info("Auto-extracted skill %s from task %s", skill_id, task.id)
    except Exception as e:
        logger.debug("Skill extraction skipped for task %s: %s", task.id, e)


async def _execute_task(task: Task):
    """Execute a task through its agent, capturing tool call steps."""
    from .agents import get_agent
    from .context import enrich_context
    from .activity import log_activity
    from .workspace import post_item
    from .circuit_breaker import get_circuit_breakers

    global _running_count
    _running_count += 1

    _breakers = get_circuit_breakers()
    _agent_breaker = _breakers.get_or_create(task.agent)

    try:
        task.status = "running"
        task.started_at = time.time()
        await _update_task(task)

        agent = get_agent(task.agent)
        if agent is None:
            task.status = "failed"
            task.error = f"Agent '{task.agent}' not available"
            task.completed_at = time.time()
            await _update_task(task)
            return

        # Circuit breaker check — if this agent has failed too many times recently, skip
        if not await _agent_breaker.can_execute():
            task.status = "failed"
            task.error = f"Circuit breaker open for {task.agent} — cooling down after repeated failures"
            task.completed_at = time.time()
            await _update_task(task)
            logger.warning("Task %s skipped — circuit open for %s", task.id, task.agent)
            return

        # Build messages — inject context and task prompt into HumanMessage
        # to avoid multiple SystemMessages (vLLM rejects mid-conversation system msgs,
        # and create_react_agent already has its own system prompt)
        context_str = ""
        try:
            context_str = await enrich_context(task.agent, task.prompt) or ""
        except Exception as e:
            logger.debug("Context enrichment failed, proceeding without: %s", e)

        task_prompt = _build_task_prompt(task)
        preamble_parts = []
        if context_str:
            preamble_parts.append(f"[Context]\n{context_str}\n[/Context]")
        preamble_parts.append(f"[Task Instructions]\n{task_prompt}\n[/Task Instructions]")

        messages = [
            HumanMessage(content="\n\n".join(preamble_parts) + "\n\n" + task.prompt),
        ]

        thread_id = f"task-{task.id}"
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
            "metadata": {"agent": task.agent, "task_id": task.id},
            "tags": [task.agent],
        }

        step_index = 0
        collected_text = []
        tools_used = []

        # Stream execution to capture steps
        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            # Check for cancellation
            refreshed = await get_task(task.id)
            if refreshed and refreshed.status == "cancelled":
                logger.info("Task %s cancelled during execution", task.id)
                return

            # Check timeout
            if time.time() - task.started_at > TASK_TIMEOUT:
                task.status = "failed"
                task.error = f"Task timed out after {TASK_TIMEOUT}s"
                task.completed_at = time.time()
                await _update_task(task)
                return

            kind = event["event"]

            if kind == "on_tool_start":
                name = event.get("name", "unknown")
                args = event.get("data", {}).get("input", {})
                tools_used.append(name)
                task.steps.append({
                    "index": step_index,
                    "type": "tool_call",
                    "tool_name": name,
                    "tool_input": args,
                    "timestamp": time.time(),
                })
                step_index += 1
                # Persist steps after every tool call for real-time visibility
                await _update_task(task)

            elif kind == "on_tool_end":
                name = event.get("name", "unknown")
                output = str(event.get("data", {}).get("output", ""))[:2000]
                # Update the last step with output
                for step in reversed(task.steps):
                    if step.get("tool_name") == name and "tool_output" not in step:
                        step["tool_output"] = output
                        break

            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                text = chunk.content if hasattr(chunk, "content") else ""
                if text:
                    collected_text.append(text)

        # Task completed successfully — strip think tags from full result
        import re
        result_text = "".join(collected_text)
        result_text = re.sub(r"<think>.*?</think>\s*", "", result_text, flags=re.DOTALL).strip()

        task.status = "completed"
        task.result = result_text
        task.completed_at = time.time()
        await _update_task(task)
        await _agent_breaker.record_success()

        logger.info(
            "Task %s completed: agent=%s steps=%d duration=%dms",
            task.id, task.agent, len(task.steps), task.duration_ms or 0,
        )

        # Log activity + conversation + event
        asyncio.create_task(log_activity(
            agent=task.agent,
            action_type="task",
            input_summary=task.prompt[:500],
            output_summary=result_text[:500],
            tools_used=tools_used,
            duration_ms=task.duration_ms,
        ))
        from .activity import log_conversation
        asyncio.create_task(log_conversation(
            agent=task.agent,
            user_message=task.prompt,
            assistant_response=result_text,
            tools_used=tools_used,
            duration_ms=task.duration_ms,
            thread_id=task.id,
        ))
        from .activity import log_event
        asyncio.create_task(log_event(
            event_type="task_completed",
            agent=task.agent,
            description=task.prompt[:200],
            data={"task_id": task.id, "steps": len(task.steps), "duration_ms": task.duration_ms, "tools": tools_used},
        ))

        # Record skill execution outcome (learning feedback loop)
        asyncio.create_task(_record_skill_execution_for_task(task, success=True))

        # Auto-extract skills from successful task traces (Layer 3)
        asyncio.create_task(_auto_extract_skill(task))

        # Notify on notable completions (skip routine health/home checks)
        prompt_lower = (task.prompt or "").lower()
        is_routine = any(kw in prompt_lower for kw in ["health check", "entities", "queue items", "check for any active"])
        task_source = task.metadata.get("source", "")
        if not is_routine and task_source not in ("scheduler", "auto_retry"):
            from .escalation import add_notification
            add_notification(
                agent=task.agent,
                action=f"Task completed ({task.duration_ms or 0}ms)",
                category="routine",
                confidence=1.0,
                description=f"{task.prompt[:120]}\n\nResult: {result_text[:150]}",
            )

        # Broadcast completion to GWT workspace
        asyncio.create_task(post_item(
            source_agent=task.agent,
            content=f"Task completed: {task.prompt[:100]}",
            priority="normal",
            ttl=300,
            metadata={
                "task_id": task.id,
                "status": "completed",
                "steps": len(task.steps),
                "duration_ms": task.duration_ms,
            },
        ))

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        task.completed_at = time.time()
        await _update_task(task)
        await _agent_breaker.record_failure()
        logger.error("Task %s failed: %s", task.id, e, exc_info=True)

        # Log failure event
        from .activity import log_event
        asyncio.create_task(log_event(
            event_type="task_failed",
            agent=task.agent,
            description=f"{task.prompt[:150]} — {str(e)[:100]}",
            data={"task_id": task.id, "error": str(e)[:500]},
        ))

        # Notify on task failures (always — failures need attention)
        from .escalation import add_notification
        add_notification(
            agent=task.agent,
            action=f"Task failed (retry={task.retry_count})",
            category="routine",
            confidence=0.6,
            description=f"{task.prompt[:120]}\n\nError: {str(e)[:150]}",
        )

        # Broadcast failure
        from .workspace import post_item
        asyncio.create_task(post_item(
            source_agent=task.agent,
            content=f"Task failed: {task.prompt[:80]} — {str(e)[:100]}",
            priority="high",
            ttl=600,
            metadata={"task_id": task.id, "status": "failed", "error": str(e)},
        ))

        # Record skill execution failure (learning feedback loop)
        asyncio.create_task(_record_skill_execution_for_task(task, success=False))

        # Auto-retry if under retry limit
        await _maybe_retry(task)

    finally:
        _running_count -= 1


async def _recover_stale_tasks():
    """On startup, cancel any tasks stuck in 'running' state (from prior crash).

    Uses 'cancelled' status (not 'failed') so server restarts don't pollute
    failure metrics. These aren't real agent failures.
    """
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        recovered = 0
        for v in raw.values():
            t = Task.from_dict(json.loads(v))
            if t.status == "running":
                t.status = "cancelled"
                t.error = "Server restarted during execution"
                t.completed_at = time.time()
                await r.hset(TASKS_KEY, t.id, json.dumps(t.to_dict()))
                recovered += 1
        if recovered:
            logger.info("Recovered %d stale tasks from prior crash", recovered)
    except Exception as e:
        logger.warning("Failed to recover stale tasks: %s", e)


async def _task_worker_loop():
    """Background worker — polls for pending tasks, executes them.

    Runs continuously. Picks up to MAX_CONCURRENT_TASKS simultaneously.
    Priority ordering: critical > high > normal > low, then FIFO.
    Runs cleanup every CLEANUP_INTERVAL seconds.
    """
    logger.info(
        "Task worker started (interval=%.1fs, max_concurrent=%d)",
        TASK_WORKER_INTERVAL, MAX_CONCURRENT_TASKS,
    )

    last_cleanup = time.time()

    while True:
        try:
            if _running_count < MAX_CONCURRENT_TASKS:
                task = await _get_next_pending()
                if task:
                    # Inference-aware scheduling check
                    should_run = True
                    try:
                        from .scheduling import get_inference_load, should_execute_task
                        load = await get_inference_load()
                        allowed, reason = should_execute_task(task.agent, load)
                        if not allowed:
                            logger.info(
                                "Task %s deferred (agent=%s): %s",
                                task.id, task.agent, reason,
                            )
                            should_run = False
                    except Exception as e:
                        logger.debug("Scheduling check failed, allowing task: %s", e)

                    if should_run:
                        asyncio.create_task(_execute_task(task))
                        logger.info(
                            "Task %s picked up by worker (agent=%s, running=%d)",
                            task.id, task.agent, _running_count + 1,
                        )

            # Periodic cleanup of expired tasks
            if time.time() - last_cleanup > CLEANUP_INTERVAL:
                await _cleanup_old_tasks()
                last_cleanup = time.time()

        except Exception as e:
            logger.warning("Task worker poll error: %s", e)

        await asyncio.sleep(TASK_WORKER_INTERVAL)


async def start_task_worker():
    """Start the background task worker."""
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        logger.info("Task worker already running")
        return

    try:
        await _recover_stale_tasks()
        _worker_task = asyncio.create_task(_task_worker_loop())
        logger.info("Task execution engine started")
    except Exception as e:
        logger.warning("Failed to start task worker: %s", e)


async def stop_task_worker():
    """Stop the background task worker."""
    global _worker_task
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
        logger.info("Task execution engine stopped")


async def get_task_stats() -> dict:
    """Get task execution statistics."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        tasks = [Task.from_dict(json.loads(v)) for v in raw.values()]

        by_status = {}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1

        by_agent = {}
        for t in tasks:
            by_agent[t.agent] = by_agent.get(t.agent, 0) + 1

        completed = [t for t in tasks if t.status == "completed" and t.duration_ms]
        avg_duration = (
            sum(t.duration_ms for t in completed) / len(completed)
            if completed else 0
        )

        return {
            "total": len(tasks),
            "by_status": by_status,
            "by_agent": by_agent,
            "currently_running": _running_count,
            "max_concurrent": MAX_CONCURRENT_TASKS,
            "avg_duration_ms": int(avg_duration),
            "worker_running": _worker_task is not None and not _worker_task.done(),
        }
    except Exception as e:
        logger.warning("Failed to get task stats: %s", e)
        return {"error": str(e)}
