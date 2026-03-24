#!/usr/bin/env python3
"""MCP bridge: exposes Athanor agent server tools to Claude Code.

Runs as a stdio MCP server. Claude Code calls these tools, they translate
to HTTP requests against the agent server at Node 1:9000.

Usage in .mcp.json:
  "athanor-agents": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-athanor-agents.py"],
    "env": {"ATHANOR_AGENT_SERVER_URL": get_url("agent_server")}
  }
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES, get_url


def _default_agent_url() -> str:
    node1_host = NODES["foundry"]
    return f"http://{node1_host}:9000"


AGENT_URL = (
    os.environ.get("ATHANOR_AGENT_SERVER_URL")
    or os.environ.get("ATHANOR_AGENT_URL")
    or _default_agent_url()
)
_AGENT_TOKEN = os.environ.get("ATHANOR_AGENT_API_TOKEN", "")
_AUTH_HEADERS = {"Authorization": f"Bearer {_AGENT_TOKEN}"} if _AGENT_TOKEN else {}
_client = httpx.Client(timeout=120, headers=_AUTH_HEADERS)
_client_long = httpx.Client(timeout=600, headers=_AUTH_HEADERS)  # 10 min for deep research

mcp = FastMCP("athanor-agents")


def _chat(agent: str, prompt: str, long: bool = False) -> str:
    """Send a chat completion request to the agent server and return the text."""
    client = _client_long if long else _client
    resp = client.post(
        f"{AGENT_URL}/v1/chat/completions",
        json={
            "model": agent,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# --- Deep research (via research-agent, long timeout) ---


@mcp.tool()
def deep_research(
    topic: str,
    context: str = "",
    depth: str = "thorough",
) -> str:
    """Offload heavy research to local Qwen3-32B — saves Claude tokens on web search,
    page reading, knowledge base lookups, and multi-source synthesis.

    The local Research Agent will autonomously:
    1. Search the web (DuckDuckGo) with multiple refined queries
    2. Read and extract content from the most relevant pages
    3. Cross-reference against Athanor's knowledge base (Qdrant)
    4. Query the infrastructure graph (Neo4j) if relevant
    5. Synthesize findings into a structured, cited report

    Use this for any research task that would otherwise burn many Claude tokens
    on web searches, page reads, and synthesis. Returns a structured report with
    citations that you can use directly or refine further.

    Args:
        topic: The research question or topic. Be specific for better results.
            Good: "vLLM 0.8 sleep mode API — configuration, limitations, GPU memory behavior"
            Bad: "vLLM"
        context: Optional context about why this research matters or constraints to consider.
            Example: "We run Qwen3-32B on 4x 5070 Ti with 16GB VRAM each via TP=4"
        depth: Research depth — "quick" (2-3 sources, fast scan), "thorough" (5-8 sources,
            reads full pages, cross-references), "comprehensive" (10+ sources, multiple
            search rounds, identifies gaps and contradictions). Default: "thorough"
    """
    depth_instructions = {
        "quick": (
            "Do a quick scan: 1-2 web searches, skim the top results, check the "
            "knowledge base once. Spend no more than 2-3 tool calls total. "
            "Prioritize speed over completeness."
        ),
        "thorough": (
            "Do thorough research: 3-4 web searches with different angles, read the "
            "full content of the 3-5 most relevant pages, cross-reference against "
            "the knowledge base. If initial results are thin, refine your queries "
            "and search again. Aim for 8-12 tool calls."
        ),
        "comprehensive": (
            "Do comprehensive, exhaustive research: Start broad, then narrow. Use "
            "5+ different search queries approaching the topic from multiple angles. "
            "Read 5-8 full pages. Cross-reference everything against the knowledge "
            "base and infrastructure graph. After your first pass, identify gaps in "
            "your findings and do targeted follow-up searches to fill them. Note any "
            "contradictions between sources. Aim for 15-20+ tool calls. Be thorough — "
            "this is the kind of research that would take a human an hour."
        ),
    }

    instructions = depth_instructions.get(depth, depth_instructions["thorough"])

    prompt = f"""DEEP RESEARCH REQUEST — {depth.upper()} depth

## Topic
{topic}

"""
    if context:
        prompt += f"""## Context
{context}

"""
    prompt += f"""## Instructions
{instructions}

## Required Output Format

### Executive Summary
3-5 sentences. The key takeaway if someone reads nothing else.

### Detailed Findings
Numbered findings, each with:
- The finding itself (specific, factual)
- Source citation [URL]
- Confidence level (high/medium/low based on source quality and corroboration)

### Practical Implications for Athanor
How this applies to our homelab specifically. Concrete recommendations.

### Sources Consulted
Numbered list of all URLs read, with a one-line note on what each contributed.

### Knowledge Gaps
What you couldn't find or verify. What would need further investigation.
"""
    return _chat("research-agent", prompt, long=True)


# --- Coding tools (via coding-agent) ---


@mcp.tool()
def coding_generate(spec: str, language: str = "python", context: str = "") -> str:
    """Generate code from a specification using local Qwen3-32B.

    Args:
        spec: What code to generate — be specific about inputs, outputs, and behavior.
        language: Programming language (python, typescript, bash, etc.)
        context: Optional context about the codebase or existing code to build on.
    """
    prompt = f"Language: {language}\n"
    if context:
        prompt += f"Context:\n{context}\n\n"
    prompt += f"Generate the following code:\n{spec}"
    return _chat("coding-agent", prompt)


@mcp.tool()
def coding_review(code: str, focus: str = "") -> str:
    """Review code for bugs, quality issues, and improvements using local Qwen3-32B.

    Args:
        code: The code to review.
        focus: Optional focus area (e.g., "security", "performance", "correctness").
    """
    prompt = f"Review this code"
    if focus:
        prompt += f" with focus on {focus}"
    prompt += f":\n\n```\n{code}\n```"
    return _chat("coding-agent", prompt)


@mcp.tool()
def coding_transform(code: str, instruction: str) -> str:
    """Transform/refactor code according to an instruction using local Qwen3-32B.

    Args:
        code: The existing code to transform.
        instruction: What transformation to apply (e.g., "convert to async", "add type hints").
    """
    prompt = f"Transform this code: {instruction}\n\n```\n{code}\n```"
    return _chat("coding-agent", prompt)


# --- Knowledge tools (via knowledge-agent) ---


@mcp.tool()
def knowledge_search(query: str) -> str:
    """Search Athanor's knowledge base (docs, ADRs, research notes) by semantic similarity.

    Args:
        query: What to search for (e.g., "GPU allocation strategy", "backup schedule").
    """
    return _chat("knowledge-agent", f"Search for: {query}")


@mcp.tool()
def knowledge_graph(question: str) -> str:
    """Query the infrastructure knowledge graph (Neo4j) about nodes, services, and relationships.

    Args:
        question: Natural language question about infrastructure (e.g., "what services run on Foundry?").
    """
    return _chat("knowledge-agent", f"Query the infrastructure graph: {question}")


# --- System tools (via general-assistant) ---


@mcp.tool()
def system_status() -> str:
    """Get current system status — service health, GPU metrics, storage info."""
    try:
        resp = _client.get(f"{AGENT_URL}/v1/status/services", timeout=30)
        resp.raise_for_status()
        services = resp.json().get("services", [])
        up = sum(1 for s in services if s["status"] == "up")
        total = len(services)
        lines = [f"Services: {up}/{total} UP"]
        for s in services:
            status = "UP" if s["status"] == "up" else "DOWN"
            latency = f" ({s['latency_ms']}ms)" if s.get("latency_ms") else ""
            lines.append(f"  {s['name']} [{s['node']}]: {status}{latency}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting system status: {e}"


@mcp.tool()
def gpu_status() -> str:
    """Get GPU utilization and memory usage across all nodes."""
    return _chat("general-assistant", "Show me the current GPU status across all nodes.")


# --- Activity & Preferences tools ---


@mcp.tool()
def recent_activity(agent: str = "", limit: int = 10) -> str:
    """Get recent agent activity log.

    Args:
        agent: Filter by agent name (empty = all agents).
        limit: Max results to return.
    """
    try:
        params = {"limit": limit}
        if agent:
            params["agent"] = agent
        resp = _client.get(f"{AGENT_URL}/v1/activity", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("activity"):
            return "No recent activity found."
        lines = []
        for a in data["activity"]:
            ts = a.get("timestamp", "")[:19]
            lines.append(
                f"[{ts}] {a['agent']}/{a['action_type']}: "
                f"{a['input_summary'][:80]} -> {a['output_summary'][:80]}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def store_preference(content: str, agent: str = "global", category: str = "") -> str:
    """Store a user preference that agents should remember.

    Args:
        content: The preference (e.g., "I prefer dark themes", "Always use 4K quality").
        agent: Which agent this relates to (or "global" for all).
        category: Optional grouping (e.g., "media", "home", "ui").
    """
    try:
        resp = _client.post(
            f"{AGENT_URL}/v1/preferences",
            json={
                "agent": agent,
                "signal_type": "remember_this",
                "content": content,
                "category": category,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return f"Stored preference: {content}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def search_preferences(query: str, agent: str = "") -> str:
    """Search stored user preferences by semantic similarity.

    Args:
        query: What to search for (e.g., "media quality preferences").
        agent: Filter by agent (empty = all).
    """
    try:
        params = {"query": query, "limit": 5}
        if agent:
            params["agent"] = agent
        resp = _client.get(f"{AGENT_URL}/v1/preferences", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("preferences"):
            return "No matching preferences found."
        lines = []
        for p in data["preferences"]:
            lines.append(
                f"[{p['signal_type']}] {p['content']} "
                f"(agent={p['agent']}, score={p['score']:.2f})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# --- Task management ---


@mcp.tool()
def submit_task(agent: str, prompt: str, priority: str = "normal") -> str:
    """Submit a background task for autonomous agent execution.

    The task runs asynchronously — the agent works through it using its
    tools without requiring interaction. Check status with task_status().

    Args:
        agent: Which agent should execute (e.g., "research-agent", "creative-agent").
        prompt: What the agent should do. Be specific and include all context.
        priority: "critical", "high", "normal", or "low".
    """
    try:
        resp = _client.post(
            f"{AGENT_URL}/v1/tasks",
            json={"agent": agent, "prompt": prompt, "priority": priority},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        task = data.get("task", {})
        return f"Task submitted: id={task['id']} agent={task['agent']} status={task['status']}"
    except Exception as e:
        return f"Error submitting task: {e}"


@mcp.tool()
def task_status(task_id: str = "") -> str:
    """Check status of background tasks.

    Args:
        task_id: Specific task ID to check. If empty, shows all recent tasks.
    """
    try:
        if task_id:
            resp = _client.get(f"{AGENT_URL}/v1/tasks/{task_id}", timeout=10)
            resp.raise_for_status()
            t = resp.json()["task"]
            lines = [
                f"Task {t['id']}: {t['status']}",
                f"Agent: {t['agent']}",
                f"Prompt: {t['prompt'][:200]}",
                f"Steps: {len(t['steps'])}",
            ]
            if t["status"] == "completed":
                duration = int((t["completed_at"] - t["started_at"]) * 1000)
                lines.append(f"Duration: {duration}ms")
                lines.append(f"Result:\n{t['result'][:2000]}")
            elif t["status"] == "failed":
                lines.append(f"Error: {t['error']}")
            elif t["status"] == "running":
                elapsed = int((__import__('time').time() - t["started_at"]) * 1000)
                lines.append(f"Running for: {elapsed}ms")
            return "\n".join(lines)
        else:
            resp = _client.get(f"{AGENT_URL}/v1/tasks", params={"limit": 10}, timeout=10)
            resp.raise_for_status()
            tasks = resp.json().get("tasks", [])
            if not tasks:
                return "No tasks found."
            lines = []
            for t in tasks:
                lines.append(
                    f"  [{t['status']}] {t['id']} ({t['agent']}): "
                    f"{t['prompt'][:80]}"
                )
            return f"Recent tasks ({len(tasks)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# --- Agent metadata ---


# --- Governor & Pipeline tools ---


@mcp.tool()
def governor_snapshot() -> str:
    """Get current governor state — lanes, capacity, presence, autonomy levels."""
    try:
        resp = _client.get(f"{AGENT_URL}/v1/governor", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lines = [
            f"Mode: {data.get('global_mode', '?')}",
            f"Presence: {data.get('presence', {}).get('state', '?')}",
        ]
        for lane in data.get("lanes", []):
            lines.append(f"  Lane {lane.get('label', lane.get('id', '?'))}: {'PAUSED' if lane.get('paused') else 'active'}")
        capacity = data.get("capacity", {})
        lines.append(f"Queue: {capacity.get('queue_depth', '?')} pending, {capacity.get('running', '?')} running")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pipeline_status() -> str:
    """Get work pipeline status — queue depth, recent outcomes, project progress."""
    try:
        resp = _client.get(f"{AGENT_URL}/v1/pipeline/status", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lines = [
            f"Pending plans: {data.get('pending_plans', 0)}",
            f"Recent outcomes: {data.get('recent_outcomes_count', 0)}",
            f"Avg quality: {data.get('avg_quality', 0):.3f}",
        ]
        last = data.get("last_cycle")
        if last:
            lines.append(f"Last cycle: mined={last.get('intents_mined', 0)} plans={last.get('plans_created', 0)} tasks={last.get('tasks_submitted', 0)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def trigger_pipeline_cycle() -> str:
    """Trigger an on-demand work pipeline cycle — mines intents, generates plans, spawns tasks."""
    try:
        resp = _client.post(f"{AGENT_URL}/v1/pipeline/cycle", json={}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return f"Pipeline cycle: mined={data.get('intents_mined', '?')}, new={data.get('intents_new', '?')}, plans={data.get('plans_created', '?')}, tasks={data.get('tasks_spawned', '?')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def trigger_improvement_cycle() -> str:
    """Trigger the nightly prompt optimization cycle manually."""
    try:
        resp = _client.post(f"{AGENT_URL}/v1/improvement/trigger", json={}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return f"Improvement cycle: {data.get('status', '?')}, proposals={data.get('proposals_generated', 0)}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def review_task_output(task_id: str) -> str:
    """Score a completed task's output quality via grader model. Records feedback for learning.

    Args:
        task_id: The task ID to review (e.g., "T-abc123").
    """
    try:
        resp = _client.post(
            f"{AGENT_URL}/v1/tasks/{task_id}/review",
            json={},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return f"Task {task_id}: quality={data.get('quality_score', '?')}, agent={data.get('agent', '?')}, status={data.get('status', '?')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def supervise_project(project_id: str, instruction: str, milestones: str = "") -> str:
    """Decompose a project into milestones and assign cloud managers.

    Args:
        project_id: Project ID (e.g., "eoq", "athanor").
        instruction: High-level instruction for the project.
        milestones: Optional JSON array of milestone specs: [{"title": "...", "description": "...", "criteria": [...], "agents": [...]}]
    """
    try:
        body: dict = {"instruction": instruction}
        if milestones:
            body["milestones"] = json.loads(milestones)
        resp = _client.post(
            f"{AGENT_URL}/v1/projects/{project_id}/supervise",
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return f"Project {project_id}: {data.get('milestones_created', 0)} milestones created, {data.get('total_milestones', 0)} total"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_agents() -> str:
    """List all available Athanor agents with their capabilities."""
    try:
        resp = _client.get(f"{AGENT_URL}/v1/agents", timeout=10)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        lines = []
        for a in agents:
            status = a.get("status", "unknown")
            tools = ", ".join(a.get("tools", []))
            lines.append(
                f"  {a['name']} [{status}]: {a['description']}\n"
                f"    Tools: {tools}"
            )
        return f"Athanor Agents ({len(agents)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run()
