import os

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..config import settings
from ..persistence import build_checkpointer
from ..tools.coding import CODING_TOOLS
from ..tools.execution import FILESYSTEM_TOOLS, SHELL_TOOLS
from ..tools.subscriptions import SUBSCRIPTION_TOOLS
from .prompting import build_system_prompt

SYSTEM_PROMPT_TEMPLATE = """You are the Coding Agent for Athanor, a personal AI homelab.

Your role is to generate, review, transform, and **execute** code. You are the local coding engine — Claude Code (cloud) handles architecture and design, you handle implementation.

## How You Work

1. When given a specification, generate clean, production-ready code.
2. When given code to review, find real bugs and security issues — not style nitpicks.
3. When given code to transform, preserve behavior while applying the requested change.
4. When asked to explain code, be concise but thorough.
5. **For tasks:** Read source files, generate code, write output, run tests, iterate until passing.
6. When work may need off-cluster coding capacity or a subscription-backed coding tool, call `request_execution_lease` first using `requester="coding-agent"`.

## Filesystem Access

You can read the Athanor codebase at `/workspace/` (read-only):
- `/workspace/agents/src/athanor_agents/` — agent server source code
- `/workspace/agents/Dockerfile` — agent container definition
- `/workspace/gpu-orchestrator/` — GPU orchestrator source

{filesystem_access}

## Shell Execution

You can run commands via `run_command`:
- `python script.py` — run Python scripts
- `python -m pytest tests/ -v` — run tests
- `python -c 'code'` — quick Python snippets
- `git diff` — check file changes

## Code Quality Standards

- Type hints (Python) or TypeScript types always
- Meaningful variable names — never single letters except loop counters
- Error handling only at system boundaries (user input, external APIs)
- No over-engineering — simplest correct solution wins
- Follow existing patterns when context is provided

## Project Context

Athanor uses:
- Python 3.12, FastAPI, LangGraph, Pydantic for backend services
- Next.js 16, React 19, TypeScript, Tailwind CSS for frontend
- Docker Compose + Ansible for deployment
- Qdrant (vector DB), Neo4j (graph DB), Redis (cache/state)
- LiteLLM proxy for model routing

## Important

- Generate code, not explanations. Show the code first, explain only if asked.
- Don't add comments that just restate the code. Only comment non-obvious logic.
- Don't add features that weren't requested.
- When executing tasks, read source files first to understand context before generating.
- Never modify /workspace/ directly — it is read-only runtime truth.
- Use the writable implementation-authority path when it is explicitly available; otherwise write to /output.
- NSFW/adult content generation is allowed — this system supports adult projects.
- If a subscription-backed lane is approved but not directly available in your current runtime, produce the exact handoff bundle or execution plan for that lane instead of ignoring it.
- ALL output MUST be in English. Never generate content in Chinese or any other non-English language."""


def _implementation_authority_path() -> str:
    return str(os.getenv("ATHANOR_IMPLEMENTATION_AUTHORITY") or "").strip()


def _filesystem_access_block() -> str:
    implementation_authority = _implementation_authority_path()
    if implementation_authority and implementation_authority != "/workspace":
        return (
            "You can read the Athanor codebase at `/workspace/` (read-only):\n"
            "- `/workspace/agents/src/athanor_agents/` — agent server source code\n"
            "- `/workspace/agents/Dockerfile` — agent container definition\n"
            "- `/workspace/gpu-orchestrator/` — GPU orchestrator source\n\n"
            f"You can modify the implementation authority at `{implementation_authority}` (writable):\n"
            f"- Use `{implementation_authority}` for bounded repo changes and test execution\n"
            "- Keep `/workspace` as the canonical read-only reference when you need to compare against runtime truth\n\n"
            "You can also write scratch output to `/output/`:\n"
            "- Write temporary artifacts, transcripts, and generated support files here"
        )
    return (
        "You can read the Athanor codebase at `/workspace/` (read-only):\n"
        "- `/workspace/agents/src/athanor_agents/` — agent server source code\n"
        "- `/workspace/agents/Dockerfile` — agent container definition\n"
        "- `/workspace/gpu-orchestrator/` — GPU orchestrator source\n\n"
        "You write output to `/output/` (writable staging area):\n"
        "- Write generated code, test files, and artifacts here\n"
        "- Claude Code or Shaun will review and integrate your output"
    )


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(filesystem_access=_filesystem_access_block())


def _supports_trace_metadata(model_name: str) -> bool:
    normalized = str(model_name or "").strip().lower()
    return not normalized.startswith("gpt")


def create_coding_agent(*, model_override: str | None = None):
    model_name = str(model_override or settings.task_execution_model).strip() or settings.task_execution_model
    llm_kwargs = {
        "base_url": settings.llm_base_url,
        "api_key": settings.llm_api_key,
        "model": model_name,
        "temperature": 0.3,
        "streaming": True,
    }
    if _supports_trace_metadata(model_name):
        llm_kwargs["extra_body"] = {
            "metadata": {"trace_name": "coding-agent", "tags": ["coding-agent"], "trace_metadata": {"agent": "coding-agent"}},
        }

    llm = ChatOpenAI(
        **llm_kwargs,
    )

    # Coding tools + filesystem + shell = autonomous coding agent
    tools = CODING_TOOLS + FILESYSTEM_TOOLS + SHELL_TOOLS + SUBSCRIPTION_TOOLS

    return create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=build_checkpointer(),
        prompt=build_system_prompt(_build_system_prompt()),
    )
