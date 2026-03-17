---
name: delegate
description: Route coding tasks to local Qwen models for free token execution. Quality gate ensures review before acceptance.
triggers:
  - "delegate"
  - "local model"
  - "offload"
---

# Delegate to Local Models

Route mechanical coding tasks to local Qwen inference (free tokens) while keeping architecture and novel reasoning in Claude.

## Task: $ARGUMENTS

## Routing Decision

Assess the task and route to the appropriate local model tool:

| Task Type | Tool | Model |
|-----------|------|-------|
| New code from spec | `coding_generate` | Qwen3.5-27B-FP8 (FOUNDRY) |
| Refactoring | `coding_transform` | Qwen3.5-27B-FP8 (FOUNDRY) |
| Code review | `coding_review` | Qwen3.5-27B-FP8 (FOUNDRY) |
| Research (3+ searches) | `deep_research` | Qwen3.5-35B-A3B (WORKSHOP) |

## Procedure

1. **Assess**: Is this task suitable for local delegation?
   - YES: Boilerplate, CRUD, type hints, docstrings, tests, format conversion, Ansible roles
   - NO: Architecture decisions, novel algorithms, security-critical code, multi-file refactoring
   - If NO: Say "Keeping this in Claude — too complex for local delegation" and do it directly

2. **Prepare**: Write a clear, complete prompt for the local model:
   - Include language, framework, and style requirements
   - Include relevant context (imports, types, interfaces)
   - Include examples of desired output format

3. **Execute**: Dispatch via the coder subagent or MCP tools:
   - Use `mcp__athanor-agents__coding_generate` for generation
   - Use `mcp__athanor-agents__coding_transform` for refactoring
   - Use `mcp__athanor-agents__coding_review` for review

4. **Quality Gate** (mandatory):
   - Review all local model output before accepting
   - Check: correctness, style, security, completeness
   - If issues found: fix them or re-generate with better prompt
   - Never accept local output without review

5. **Integrate**: Apply the accepted code to the codebase via Edit/Write tools
