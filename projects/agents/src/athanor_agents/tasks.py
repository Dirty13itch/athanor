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

from langchain_core.messages import HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger(__name__)

TASKS_KEY = "athanor:tasks"
TASKS_CHANNEL = "athanor:tasks:events"
TASK_WORKER_INTERVAL = 5.0  # seconds between polls
MAX_CONCURRENT_TASKS = 2
TASK_TIMEOUT = 600  # 10 min max per task

_worker_task: asyncio.Task | None = None
_running_count = 0


@dataclass
class Task:
    """A unit of autonomous work for an agent."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent: str = ""
    prompt: str = ""
    priority: str = "normal"  # critical, high, normal, low
    status: str = "pending"   # pending, running, completed, failed, cancelled
    result: str = ""
    error: str = ""
    steps: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict = field(default_factory=dict)
    parent_task_id: str = ""  # For delegated sub-tasks

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

    task = Task(
        agent=agent,
        prompt=prompt,
        priority=priority if priority in PRIORITY_ORDER else "normal",
        metadata=metadata or {},
        parent_task_id=parent_task_id,
    )

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
        if task.status not in ("pending", "running"):
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


async def _execute_task(task: Task):
    """Execute a task through its agent, capturing tool call steps."""
    from .agents import get_agent
    from .context import enrich_context
    from .activity import log_activity
    from .workspace import post_item

    global _running_count
    _running_count += 1

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

        # Build messages with context injection
        messages = []
        try:
            context_str = await enrich_context(task.agent, task.prompt)
            if context_str:
                messages.append(SystemMessage(content=context_str))
        except Exception:
            pass

        # Add task-mode system prompt
        messages.append(SystemMessage(content=(
            "You are executing a background task autonomously. "
            "Work through the task step by step using your tools. "
            "Be thorough and report your findings clearly."
        )))
        messages.append(HumanMessage(content=task.prompt))

        thread_id = f"task-{task.id}"
        config = {"configurable": {"thread_id": thread_id}}

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

        logger.info(
            "Task %s completed: agent=%s steps=%d duration=%dms",
            task.id, task.agent, len(task.steps), task.duration_ms or 0,
        )

        # Log activity
        asyncio.create_task(log_activity(
            agent=task.agent,
            action_type="task",
            input_summary=task.prompt[:500],
            output_summary=result_text[:500],
            tools_used=tools_used,
            duration_ms=task.duration_ms,
        ))

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
        logger.error("Task %s failed: %s", task.id, e, exc_info=True)

        # Broadcast failure
        from .workspace import post_item
        asyncio.create_task(post_item(
            source_agent=task.agent,
            content=f"Task failed: {task.prompt[:80]} — {str(e)[:100]}",
            priority="high",
            ttl=600,
            metadata={"task_id": task.id, "status": "failed", "error": str(e)},
        ))

    finally:
        _running_count -= 1


async def _recover_stale_tasks():
    """On startup, reset any tasks stuck in 'running' state (from prior crash)."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(TASKS_KEY)
        recovered = 0
        for v in raw.values():
            t = Task.from_dict(json.loads(v))
            if t.status == "running":
                t.status = "failed"
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
    """
    logger.info(
        "Task worker started (interval=%.1fs, max_concurrent=%d)",
        TASK_WORKER_INTERVAL, MAX_CONCURRENT_TASKS,
    )

    while True:
        try:
            if _running_count < MAX_CONCURRENT_TASKS:
                task = await _get_next_pending()
                if task:
                    # Launch task execution as a background coroutine
                    asyncio.create_task(_execute_task(task))
                    logger.info(
                        "Task %s picked up by worker (agent=%s, running=%d)",
                        task.id, task.agent, _running_count + 1,
                    )
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
