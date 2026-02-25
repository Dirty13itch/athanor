# Hybrid Development Architecture

*How cloud AI (Claude Code) and local AI (Qwen3 on Athanor) work together.*

Last updated: 2026-02-25

---

## The Core Idea

Claude Code is the brain. Local coding agents are the hands.

Cloud AI excels at architecture, code review, novel problem solving, and cross-codebase reasoning. Local AI excels at boilerplate, pattern application, bulk edits, and execution tasks that don't need frontier-model intelligence. The hybrid model uses each where it's strongest.

```
Claude Code (DEV/WSL2, Opus 4.6)
  ├── Plans architecture, reviews code, makes decisions
  ├── Dispatches execution to local agents via MCP bridge
  ├── Uses Agent Teams for parallel workstreams
  └── Runs autonomous builds via /build + manifest
         │
         │  MCP bridge (scripts/mcp-athanor-agents.py)
         │
         ▼
Agent Server (Node 1:9000, Qwen3-32B-AWQ)
  ├── Coding Agent: generates code, refactors, runs linters
  ├── Knowledge Agent: provides codebase context
  └── Research Agent: checks docs, searches for patterns
```

---

## When Cloud vs Local

| Task | Cloud (Claude/Kimi) | Local (Qwen3) | Why |
|------|---------------------|---------------|-----|
| Architecture design | Yes | — | Needs frontier reasoning + broad knowledge |
| Code review | Yes | — | Needs context window + nuanced judgment |
| Novel algorithms | Yes | — | Needs creative problem solving |
| Cross-codebase refactoring | Yes | — | Needs to hold multiple large files in context |
| Boilerplate generation | — | Yes | Pattern application, no novel reasoning needed |
| Test writing from spec | — | Yes | Mechanical translation of spec to test code |
| Bulk find-and-replace | — | Yes | Repetitive pattern application |
| Linting/type-checking | — | Yes | Tool execution, not generation |
| Documentation from code | Either | Either | Depends on complexity |
| Bug investigation | Yes | Local for data | Cloud reasons, local provides system context |

**The dispatch heuristic:** If the task requires understanding *why*, use cloud. If the task requires executing *what* (where "what" is already specified), use local.

---

## Implementation Components

### 1. MCP Bridge (`scripts/mcp-athanor-agents.py`)

A lightweight MCP (Model Context Protocol) server that exposes the Athanor agent server's capabilities as tools in Claude Code. ~350 lines of Python.

**Tools exposed (12):**

```python
# Deep research (via Research Agent, 10-min timeout)
deep_research(topic: str, context: str, depth: str) -> str  # quick/thorough/comprehensive

# Coding tools (via Coding Agent)
coding_generate(spec: str, language: str, context: str) -> str
coding_review(code: str, focus: str) -> str
coding_transform(code: str, instruction: str) -> str

# Knowledge tools (via Knowledge Agent)
knowledge_search(query: str) -> str
knowledge_graph(question: str) -> str

# System tools (via General Assistant)
system_status() -> str
gpu_status() -> str

# Activity & Preferences
recent_activity(agent: str, limit: int) -> str
store_preference(content: str, agent: str, category: str) -> str
search_preferences(query: str, agent: str) -> str

# Agent metadata
list_agents() -> str
```

**Protocol:** The MCP bridge receives tool calls from Claude Code, translates them to chat completions requests to the agent server (Node 1:9000), and returns the results.

**Configuration:** Added to `.mcp.json`:
```json
{
  "mcpServers": {
    "athanor-agents": {
      "command": "python3",
      "args": ["scripts/mcp-athanor-agents.py"],
      "env": {
        "ATHANOR_AGENT_URL": "http://192.168.1.244:9000"
      }
    }
  }
}
```

### 2. Agent Teams (`.claude/agents/coder.md`)

Claude Code's Agent Teams feature allows spawning specialized sub-agents. A `coder.md` agent definition creates a local coding specialist that Claude Code can delegate to:

```markdown
---
name: Local Coder
description: Dispatches coding tasks to local Qwen3 via MCP bridge
tools: [mcp__athanor-agents__coding_generate, mcp__athanor-agents__coding_refactor]
---

You are a coding agent that uses local Qwen3 inference for code generation.
When given a coding task, use the MCP tools to generate code locally.
Review the output for correctness before returning it.
```

### 3. Coding Agent (`projects/agents/src/athanor_agents/agents/coding.py`)

A new LangGraph agent on the agent server with tools for:
- Reading project files
- Searching codebases (grep, find)
- Running linters and type checkers
- Generating code from specifications
- Applying refactoring patterns

Uses the `reasoning` model (Qwen3-32B-AWQ) with low temperature (0.3) for deterministic code generation.

### 4. Dispatch Skill (`.claude/skills/local-coding.md`)

A Claude Code skill that codifies when to dispatch to local vs handle in cloud:

```markdown
# Local Coding Dispatch

When to use local Qwen3 (via MCP bridge):
- Generating boilerplate from a clear specification
- Writing tests from a described test plan
- Applying a known refactoring pattern across files
- Running linters or type checkers

When to keep in cloud (Claude Code):
- Designing architecture or APIs
- Reviewing code for subtle bugs
- Solving novel problems without clear patterns
- Working across multiple large files simultaneously

Dispatch command: Use the `coding_generate` MCP tool with a clear spec.
```

---

## Workflow Examples

### Example 1: Adding a new dashboard page

**Claude Code (cloud) handles:**
1. Reads existing dashboard pages to understand patterns
2. Designs the component architecture (layout, data flow, state)
3. Specifies what the page needs (components, API routes, types)

**Local Qwen3 handles (via MCP bridge):**
4. Generates the page component from Claude's spec
5. Generates the API route handler
6. Generates TypeScript types

**Claude Code reviews and integrates:**
7. Reviews generated code for correctness
8. Makes adjustments for edge cases
9. Commits and updates manifest

### Example 2: Bulk refactoring agent tools

**Claude Code:**
1. Identifies the refactoring pattern (e.g., sync → async for all tool functions)
2. Specifies the transformation rule

**Local Qwen3:**
3. Applies the transformation to each file
4. Runs linters to verify

**Claude Code:**
5. Reviews the diff
6. Commits

### Example 3: Autonomous build session

```
Claude Code reads BUILD-MANIFEST.md
  → Picks next unblocked item
  → If item is "write new agent": Claude Code designs it (cloud)
  → If item is "add health check": dispatches to local Qwen3 (mechanical)
  → Reviews all output
  → Commits and updates manifest
```

---

## Infrastructure Requirements

| Component | Where | Dependencies | Status |
|-----------|-------|-------------|--------|
| MCP bridge script | DEV (local) | Python 3.11+, mcp, httpx | **Deployed** |
| Coding Agent | Node 1:9000 | Agent server, Qwen3-32B | **Deployed** |
| Agent Teams config | `.claude/agents/coder.md` | Claude Code | **Deployed** |
| Dispatch skill | `.claude/skills/local-coding.md` | Claude Code | **Deployed** |
| Coding tools | `projects/agents/src/athanor_agents/tools/coding.py` | Agent server | **Deployed** |

### Future: Dedicated Coding Model

When a coding-specialized model is available (e.g., Qwen3-Coder), deploy it on Node 2 as a third vLLM instance. Route `coding` alias through LiteLLM. This separates coding inference from general reasoning, preventing coding tasks from competing with chat for the 32B model.

---

## Verification

1. `curl Node1:9000/v1/models` includes `coding-agent`
2. Claude Code `ToolSearch` finds `mcp__athanor-agents__coding_generate`
3. End-to-end: Claude Code calls `coding_generate` → MCP bridge → Agent Server → Qwen3 → code returned
4. Generated code compiles/passes linting
5. Round-trip latency < 30s for typical code generation tasks
