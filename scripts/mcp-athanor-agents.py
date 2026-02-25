#!/usr/bin/env python3
"""MCP bridge: exposes Athanor agent server tools to Claude Code.

Runs as a stdio MCP server. Claude Code calls these tools, they translate
to HTTP requests against the agent server at Node 1:9000.

Usage in .mcp.json:
  "athanor-agents": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-athanor-agents.py"],
    "env": {"ATHANOR_AGENT_URL": "http://192.168.1.244:9000"}
  }
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

AGENT_URL = os.environ.get("ATHANOR_AGENT_URL", "http://192.168.1.244:9000")
_client = httpx.Client(timeout=120)

mcp = FastMCP("athanor-agents")


def _chat(agent: str, prompt: str) -> str:
    """Send a chat completion request to the agent server and return the text."""
    resp = _client.post(
        f"{AGENT_URL}/v1/chat/completions",
        json={
            "model": agent,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


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


# --- Agent metadata ---


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
