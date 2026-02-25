"""Execution tools — enable agents to do autonomous work.

These tools give agents capabilities beyond chat: delegating work to
other agents, reading/writing files, and running commands.

Phase 1: Agent delegation (works within current container).
Phase 2: Filesystem + shell (requires Docker volume mounts).
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def delegate_to_agent(agent_name: str, prompt: str, priority: str = "normal") -> str:
    """Delegate a task to another specialized agent for background execution.

    Use this when the task requires a different agent's expertise.
    The task runs asynchronously — you'll get a task ID to track progress.

    Examples:
        - delegate_to_agent("research-agent", "Research vLLM sleep mode support in latest releases")
        - delegate_to_agent("creative-agent", "Generate a thumbnail image for the Athanor dashboard")
        - delegate_to_agent("knowledge-agent", "Find all ADRs related to GPU management")

    Args:
        agent_name: The agent to delegate to (e.g., "research-agent", "creative-agent")
        prompt: What the agent should do — be specific and include all context needed
        priority: Task priority — "critical", "high", "normal", or "low"
    """
    try:
        from ..tasks import submit_task

        task = await submit_task(
            agent=agent_name,
            prompt=prompt,
            priority=priority,
            metadata={"source": "delegation"},
        )
        return (
            f"Task delegated to {agent_name} (task_id={task.id}, priority={priority}). "
            f"The task is queued for background execution. "
            f"Check status at GET /v1/tasks/{task.id}"
        )
    except ValueError as e:
        return f"Delegation failed: {e}"
    except Exception as e:
        logger.error("Delegation to %s failed: %s", agent_name, e)
        return f"Delegation failed: {e}"


@tool
async def check_task_status(task_id: str) -> str:
    """Check the status and result of a previously submitted task.

    Use this to follow up on delegated tasks or check background work progress.

    Args:
        task_id: The task ID returned when the task was submitted
    """
    try:
        from ..tasks import get_task

        task = await get_task(task_id)
        if not task:
            return f"Task '{task_id}' not found."

        parts = [
            f"Task {task.id}: {task.status}",
            f"Agent: {task.agent}",
            f"Prompt: {task.prompt[:200]}",
        ]

        if task.status == "completed":
            parts.append(f"Result: {task.result[:1000]}")
            parts.append(f"Steps: {len(task.steps)}")
            if task.duration_ms:
                parts.append(f"Duration: {task.duration_ms}ms")
        elif task.status == "failed":
            parts.append(f"Error: {task.error}")
        elif task.status == "running":
            parts.append(f"Steps completed: {len(task.steps)}")
            elapsed = int(((__import__('time').time()) - task.started_at) * 1000)
            parts.append(f"Running for: {elapsed}ms")

        return "\n".join(parts)
    except Exception as e:
        return f"Failed to check task: {e}"


EXECUTION_TOOLS = [delegate_to_agent, check_task_status]
