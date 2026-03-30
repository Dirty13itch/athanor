"""Execution tools — enable agents to do autonomous work.

These tools give agents capabilities beyond chat: delegating work to
other agents, reading/writing files, and running commands.

Phase 1: Agent delegation (works within current container).
Phase 2: Filesystem + shell (requires Docker volume mounts).

Security model:
    - READ allowed from /workspace (read-only codebase), /data/personal (read-only personal data)
    - WRITE allowed only to /output (staging area)
    - Commands run in /output with timeout, blocklist enforced
    - Path traversal prevented (resolved paths must stay in allowed dirs)
"""

import asyncio
import logging
import os
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# --- Path security ---

WORKSPACE_DIR = Path("/workspace")   # Read-only mount of /opt/athanor
OUTPUT_DIR = Path("/output")         # Writable staging area
PERSONAL_DIR = Path("/data/personal")  # Read-only mount of personal data

READ_ALLOWED = [WORKSPACE_DIR, OUTPUT_DIR, PERSONAL_DIR]
WRITE_ALLOWED = [OUTPUT_DIR]

# Allowlist: only these command prefixes are permitted.
# Anything not matching is rejected. This is safer than a blocklist.
COMMAND_ALLOWLIST_PREFIXES = [
    # Python execution
    "python", "python3", "python -", "python3 -",
    # Testing
    "pytest", "python -m pytest", "python3 -m pytest",
    # File inspection (read-only)
    "cat ", "head ", "tail ", "less ", "wc ", "file ",
    "ls", "find ", "tree ", "du ", "df ",
    "grep ", "rg ", "awk ", "sed ",  # sed is read-safe in pipeline context
    "diff ", "sort ", "uniq ", "cut ",
    # Git (read-only operations)
    "git log", "git diff", "git status", "git show", "git blame",
    "git ls-files", "git rev-parse", "git branch",
    # Build/lint tools
    "npm run", "npx ", "node ",
    "pip list", "pip show",
    "mypy ", "ruff ", "black --check", "flake8",
    # System info (read-only)
    "echo ", "date", "env ", "printenv", "whoami", "pwd", "id",
    "uname", "hostname",
    # Curl for API checks (no piping to shell)
    "curl ",
]

# Even within allowed commands, these patterns are always blocked
COMMAND_DENY_PATTERNS = [
    "curl | sh", "curl | bash", "wget | sh", "wget | bash",
    "| sh", "| bash",  # No piping into shell interpreters
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){ :|:&",
    "> /dev/sd", "chmod -R 777", "shutdown", "reboot", "poweroff",
]

MAX_COMMAND_TIMEOUT = 300  # 5 minutes max
DEFAULT_COMMAND_TIMEOUT = 60


def _validate_read_path(path_str: str) -> Path:
    """Validate and resolve a path for reading. Raises ValueError if not allowed."""
    path = Path(path_str).resolve()
    for allowed in READ_ALLOWED:
        try:
            path.relative_to(allowed)
            return path
        except ValueError:
            continue
    raise ValueError(
        f"Path '{path_str}' is outside allowed read directories. "
        f"Allowed: {', '.join(str(d) for d in READ_ALLOWED)}"
    )


def _validate_write_path(path_str: str) -> Path:
    """Validate and resolve a path for writing. Raises ValueError if not allowed."""
    path = Path(path_str).resolve()
    for allowed in WRITE_ALLOWED:
        try:
            path.relative_to(allowed)
            return path
        except ValueError:
            continue
    raise ValueError(
        f"Path '{path_str}' is outside allowed write directories. "
        f"Writable: {', '.join(str(d) for d in WRITE_ALLOWED)}"
    )


def _check_command_safety(command: str) -> str | None:
    """Check if a command is allowed. Returns reason if blocked, None if ok.

    Uses an allowlist approach: command must start with an allowed prefix.
    Even allowed commands are checked against deny patterns for safety.
    """
    cmd_stripped = command.strip()
    cmd_lower = cmd_stripped.lower()

    # Check deny patterns first (absolute blocks)
    for denied in COMMAND_DENY_PATTERNS:
        if denied in cmd_lower:
            return f"Command contains blocked pattern: '{denied}'"

    # Check allowlist — command must start with an allowed prefix
    allowed = any(cmd_stripped.startswith(prefix) or cmd_lower.startswith(prefix.lower())
                   for prefix in COMMAND_ALLOWLIST_PREFIXES)
    if not allowed:
        return (
            f"Command not in allowlist. Allowed prefixes: "
            f"{', '.join(sorted(set(p.strip() for p in COMMAND_ALLOWLIST_PREFIXES[:10])))}... "
            f"({len(COMMAND_ALLOWLIST_PREFIXES)} total)"
        )

    return None


# --- Delegation tools ---


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
        from ..tasks import submit_governed_task

        submission = await submit_governed_task(
            agent=agent_name,
            prompt=prompt,
            priority=priority,
            metadata={
                "source": "delegation",
                "delegation": {
                    "submitted_via": "delegate_to_agent",
                    "target_agent": agent_name,
                },
            },
            source="delegation",
        )
        task = submission.task
        if submission.held_for_approval or task.status == "pending_approval":
            return (
                f"Task delegated to {agent_name} (task_id={task.id}, priority={priority}) "
                "but it is currently held for approval. "
                f"Check status at GET /v1/tasks/{task.id}"
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


# --- Filesystem tools ---


@tool
async def read_file(path: str) -> str:
    """Read a file from the workspace or output directory.

    Use this to examine source code, configuration files, or previously
    generated output. The workspace (/workspace) contains the Athanor
    codebase (read-only). The output directory (/output) contains files
    you've written.

    Common paths:
        /workspace/agents/src/athanor_agents/ — agent server source code
        /workspace/gpu-orchestrator/ — GPU orchestrator source
        /output/ — your generated files

    Args:
        path: Absolute path to the file (must be under /workspace, /output, or /data/personal)
    """
    try:
        resolved = _validate_read_path(path)
        if not resolved.exists():
            return f"File not found: {path}"
        if not resolved.is_file():
            return f"Not a file: {path} (use list_directory for directories)"
        content = resolved.read_text(encoding="utf-8", errors="replace")
        if len(content) > 50000:
            content = content[:50000] + f"\n\n... [truncated, {len(content)} chars total]"
        return content
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error reading {path}: {e}"


@tool
async def write_file(path: str, content: str) -> str:
    """Write content to a file in the output directory.

    Use this to save generated code, test files, configuration, or other
    artifacts. Files are written to /output/ which is the writable staging
    area. Claude Code or Shaun will review and integrate your output.

    The parent directory is created automatically if it doesn't exist.

    Args:
        path: Absolute path starting with /output/ (e.g., /output/tests/test_media.py)
        content: The file content to write
    """
    try:
        resolved = _validate_write_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        size = resolved.stat().st_size
        return f"Written {size} bytes to {path}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error writing {path}: {e}"


@tool
async def list_directory(path: str, pattern: str = "*") -> str:
    """List files and directories at a given path.

    Use this to explore the codebase structure or check your output files.

    Args:
        path: Directory path to list (must be under /workspace, /output, or /data/personal)
        pattern: Glob pattern to filter results (default: "*", e.g., "*.py", "test_*")
    """
    try:
        resolved = _validate_read_path(path)
        if not resolved.exists():
            return f"Directory not found: {path}"
        if not resolved.is_dir():
            return f"Not a directory: {path}"

        entries = sorted(resolved.glob(pattern))
        if not entries:
            return f"No matches for pattern '{pattern}' in {path}"

        lines = []
        for entry in entries[:200]:  # Cap at 200 entries
            rel = entry.relative_to(resolved)
            suffix = "/" if entry.is_dir() else f"  ({entry.stat().st_size} bytes)"
            lines.append(f"  {rel}{suffix}")

        result = f"{path} ({len(entries)} items):\n" + "\n".join(lines)
        if len(entries) > 200:
            result += f"\n  ... and {len(entries) - 200} more"
        return result
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error listing {path}: {e}"


@tool
async def search_files(directory: str, pattern: str, file_glob: str = "*.py") -> str:
    """Search for a text pattern across files in a directory (like grep).

    Use this to find function definitions, class names, import statements,
    or any text pattern across the codebase.

    Args:
        directory: Directory to search in (must be under /workspace, /output, or /data/personal)
        pattern: Text pattern to search for (case-insensitive substring match)
        file_glob: Glob pattern for files to search (default: "*.py")
    """
    try:
        resolved = _validate_read_path(directory)
        if not resolved.is_dir():
            return f"Not a directory: {directory}"

        matches = []
        pattern_lower = pattern.lower()

        for filepath in resolved.rglob(file_glob):
            if not filepath.is_file():
                continue
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern_lower in line.lower():
                        rel = filepath.relative_to(resolved)
                        matches.append(f"  {rel}:{i}: {line.strip()[:200]}")
                        if len(matches) >= 100:
                            break
            except Exception:
                continue
            if len(matches) >= 100:
                break

        if not matches:
            return f"No matches for '{pattern}' in {directory} ({file_glob})"

        result = f"Found {len(matches)} matches for '{pattern}':\n" + "\n".join(matches)
        if len(matches) >= 100:
            result += "\n  ... (results capped at 100)"
        return result
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error searching {directory}: {e}"


# --- Shell execution ---


@tool
async def run_command(command: str, working_dir: str = "/output", timeout: int = 60) -> str:
    """Execute a shell command in the output directory.

    Use this to run Python scripts, pytest, git commands, or other CLI tools.
    Commands run in a subprocess with a timeout. Working directory defaults
    to /output (the writable staging area).

    Examples:
        - run_command("python test_media.py")
        - run_command("python -m pytest tests/ -v")
        - run_command("python -c 'print(1+1)'")
        - run_command("ls -la /workspace/agents/src/")
        - run_command("git diff", working_dir="/workspace/agents")

    Args:
        command: The shell command to execute
        working_dir: Working directory (default: /output). Must be /workspace or /output.
        timeout: Max seconds to run (default: 60, max: 300)
    """
    try:
        # Validate working directory
        _validate_read_path(working_dir)

        # Safety check
        reason = _check_command_safety(command)
        if reason:
            return f"Command blocked: {reason}"

        # Clamp timeout
        timeout = min(max(timeout, 5), MAX_COMMAND_TIMEOUT)

        # Ensure output dir exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"Command timed out after {timeout}s: {command}"

        stdout_str = stdout.decode("utf-8", errors="replace")[:20000]
        stderr_str = stderr.decode("utf-8", errors="replace")[:10000]

        parts = [f"Exit code: {proc.returncode}"]
        if stdout_str.strip():
            parts.append(f"stdout:\n{stdout_str}")
        if stderr_str.strip():
            parts.append(f"stderr:\n{stderr_str}")
        if not stdout_str.strip() and not stderr_str.strip():
            parts.append("(no output)")

        return "\n".join(parts)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error running command: {e}"


# --- Tool groups ---

DELEGATION_TOOLS = [delegate_to_agent, check_task_status]
FILESYSTEM_TOOLS = [read_file, write_file, list_directory, search_files]
SHELL_TOOLS = [run_command]

EXECUTION_TOOLS = DELEGATION_TOOLS + FILESYSTEM_TOOLS + SHELL_TOOLS
