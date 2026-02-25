---
name: Local Coding Dispatch
description: When to use local Qwen3 vs cloud Claude for coding tasks
---

# Local Coding Dispatch

The Athanor agent server at Node 1:9000 runs a coding agent powered by Qwen3-32B-AWQ. Use the MCP bridge tools (`mcp__athanor-agents__*`) to dispatch work locally when appropriate.

## Use Local Qwen3 When

- Generating boilerplate from a clear, specific specification
- Writing tests from a described test plan
- Applying a known refactoring pattern across files
- Transforming code (sync→async, add type hints, rename variables)
- Generating Ansible tasks, Docker configs, or similar templated code
- Bulk mechanical edits where the pattern is already established

## Keep in Cloud (Claude) When

- Designing architecture or APIs
- Reviewing code for subtle logic bugs
- Solving novel problems without clear patterns
- Working across multiple large files simultaneously
- Making judgment calls about trade-offs
- Anything requiring understanding of *why*, not just *what*

## The Heuristic

**If the task requires understanding *why* → cloud. If the task requires executing *what* (already specified) → local.**

## How to Dispatch

Use the MCP tools directly:
- `coding_generate(spec, language, context)` — generate new code
- `coding_review(code, focus)` — review code quality
- `coding_transform(code, instruction)` — refactor existing code

Or spawn the Local Coder agent for multi-step coding tasks that need iterative generation + review.
