# Claude Code Parallel Execution Patterns

**Date:** 2026-02-26
**Status:** Research complete
**Author:** Research Agent (Claude)

## Context

Claude Code (as of v2.0.60+, February 2026) supports multiple mechanisms for parallel work: Agent Teams, git worktrees, custom subagents, fan-out scripting, and background tasks. This document catalogues practical patterns people are actually using, drawn from official docs, engineering blogs, and community reports.

Athanor already uses 4 custom agents (`researcher`, `coder`, `infra-auditor`, `doc-writer`) and has Agent Teams enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). This research identifies patterns we should adopt.

---

## 1. Agent Teams

### What They Are

Agent Teams coordinate multiple independent Claude Code sessions with a shared task list, inter-agent messaging, and a team lead that orchestrates. Unlike subagents (which report results back to a parent), teammates can message each other directly and self-coordinate.

### Enable

```json
// settings.json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### How TeamCreate Works

Seven tool primitives form the coordination layer:

1. **TeamCreate** -- initializes team directory and config at `~/.claude/teams/{team-name}/`
2. **TaskCreate** -- defines work units (descriptions act as prompts for teammates)
3. **TaskUpdate** -- teammates claim tasks and mark completion
4. **TaskList** -- returns all tasks with status; teammates self-claim pending work
5. **Task (with team_name)** -- spawns a teammate as a full Claude Code session
6. **SendMessage** -- direct communication between any teammates
7. **TeamDelete** -- cleans up team files after shutdown

Task claiming uses file locking to prevent race conditions. Dependencies auto-unblock when prerequisites complete.

### Display Modes

- **In-process** (default): all teammates in one terminal. Shift+Down to cycle. Works everywhere.
- **Split panes** (tmux/iTerm2): each teammate gets its own pane. Set `"teammateMode": "tmux"` in settings.

### When to Use Teams vs Subagents

| Factor | Use Subagents | Use Agent Teams |
|--------|--------------|-----------------|
| Communication | Results back to parent only | Teammates message each other |
| Coordination | Parent manages everything | Shared task list, self-coordination |
| Token cost | Lower (summaries return) | Higher (each is full instance) |
| Best for | Focused tasks, result-only | Complex work needing discussion |
| Context | Own window, results return | Own window, fully independent |

### Practical Team Patterns

**Pattern 1: Plan-First Team**
Start in plan mode (~10k tokens) to map task breakdown, then switch to agent team for parallel execution. This checkpoint prevents expensive mid-execution course corrections.

**Pattern 2: Competing Hypotheses**
```
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
```
Sequential investigation suffers from anchoring bias. Parallel adversarial investigation finds the actual root cause faster.

**Pattern 3: Parallel Code Review**
```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

**Pattern 4: Cross-Layer Feature Work**
Assign frontend, backend, and test teammates. Each owns a distinct file surface area to avoid overwrites.

**Pattern 5: Require Plan Approval**
```
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
```
The lead reviews approaches and approves/rejects before code touches. You can influence criteria: "only approve plans that include test coverage."

**Pattern 6: Delegate Mode**
Press Shift+Tab to restrict the lead to coordination only, preventing it from doing work itself instead of delegating.

### Team Sizing Guidelines

- Start with 3-5 teammates for most workflows
- Aim for 5-6 tasks per teammate (too small = overhead, too large = risk)
- Token costs scale linearly: 3-person team uses ~800k tokens vs ~200k solo
- Three focused teammates often outperform five scattered ones

### Known Limitations (February 2026)

- `/resume` does not restore in-process teammates -- spawn fresh after resuming
- Task status can lag (teammates sometimes fail to mark tasks complete)
- One team per session, no nested teams
- Lead is fixed (cannot promote teammate)
- No split panes in VS Code terminal, Windows Terminal, or Ghostty
- Shutdown can be slow (teammates finish current request first)

### Quality Gates via Hooks

```json
// TeammateIdle: runs when teammate is about to go idle
// Exit code 2 sends feedback and keeps teammate working
// TaskCompleted: runs when task is being marked complete
// Exit code 2 prevents completion and sends feedback
```

---

## 2. Git Worktrees

### What They Are

Each Claude session gets its own copy of the codebase via `git worktree`. Changes in one worktree cannot collide with another.

### Usage

```bash
# Named worktree
claude --worktree feature-auth
# Creates .claude/worktrees/feature-auth/ with branch worktree-feature-auth

# Auto-named
claude --worktree
# Generates random name like "bright-running-fox"

# Second parallel session
claude --worktree bugfix-123
```

Worktrees branch from the default remote branch. Add `.claude/worktrees/` to `.gitignore`.

### Subagent Worktrees

Add `isolation: worktree` to agent frontmatter:

```yaml
---
name: my-agent
description: Does isolated work
isolation: worktree
---
```

Each subagent gets its own worktree, auto-cleaned if no changes made.

### Cleanup Behavior

- **No changes**: worktree and branch removed automatically
- **Changes exist**: Claude prompts to keep or remove

### Migration Pattern

Update 50 files? Spawn 5 agents, each handling 10 files in their own worktree. They run in parallel without stepping on each other.

---

## 3. Custom Subagents

### Configuration

Subagents are Markdown files with YAML frontmatter in `.claude/agents/` (project) or `~/.claude/agents/` (user). Project wins on name collision.

### Full Frontmatter Reference

```yaml
---
name: code-reviewer          # Required: unique identifier
description: Reviews code     # Required: when Claude delegates
tools: Read, Grep, Glob      # Optional: tool allowlist (inherits all if omitted)
disallowedTools: Write, Edit  # Optional: tool denylist
model: sonnet                 # Optional: sonnet|opus|haiku|inherit (default: inherit)
permissionMode: default       # Optional: default|acceptEdits|dontAsk|bypassPermissions|plan
maxTurns: 10                  # Optional: max agentic turns
skills:                       # Optional: skills to inject at startup
  - api-conventions
mcpServers:                   # Optional: MCP servers available
  - slack
hooks:                        # Optional: lifecycle hooks
  PreToolUse: [...]
memory: user                  # Optional: user|project|local persistent memory
background: true              # Optional: run as background task
isolation: worktree           # Optional: worktree isolation
---
```

### CLI-Defined Subagents (Session-Only)

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

### Restricting Subagent Spawning

When an agent runs as main thread with `claude --agent`, control which subagents it can spawn:

```yaml
tools: Task(worker, researcher), Read, Bash
# Only worker and researcher subagents can be spawned
```

### Persistent Memory

The `memory` field gives a subagent persistent storage across conversations:

| Scope | Location | Use |
|-------|----------|-----|
| user | `~/.claude/agent-memory/<name>/` | Knowledge across all projects |
| project | `.claude/agent-memory/<name>/` | Project-specific, version controlled |
| local | `.claude/agent-memory-local/<name>/` | Project-specific, not committed |

When enabled, the first 200 lines of `MEMORY.md` in the memory directory are injected into context.

### Cost Optimization: Model Splitting

Run main session on Opus for complex reasoning, subagents on Sonnet for focused tasks:

```yaml
# Expensive reasoning agent
---
name: architect
model: opus
---

# Cost-effective worker
---
name: test-runner
model: haiku
---
```

The built-in Explore subagent already runs on Haiku by default. Limit `maxTurns` to 5-10 for most search tasks to prevent runaway costs.

### The 9-Agent Parallel Code Review Pattern

From hamy.xyz, a single message spawns 9 specialized subagents simultaneously:

1. Test Runner
2. Linter & Static Analysis
3. Code Reviewer (5 ranked improvements)
4. Security Reviewer
5. Quality & Style Reviewer
6. Test Quality Reviewer
7. Performance Reviewer
8. Dependency & Deployment Safety
9. Simplification & Maintainability

All 9 run in parallel, results synthesized into prioritized categories. Reports ~75% useful suggestions. Implemented as a `/code-review` command.

---

## 4. Fan-Out Patterns with `claude -p`

### Basic Fan-Out

```bash
# Generate task list
claude -p "List all Python files needing migration" > files.txt

# Process in parallel
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)" &
done
wait
```

### Pipeline Integration

```bash
# Pipe data through Claude
cat build-error.txt | claude -p 'explain the root cause' > analysis.txt

# Structured output
claude -p "List all API endpoints" --output-format json | jq '.endpoints'

# Streaming for real-time processing
claude -p "Analyze this log file" --output-format stream-json
```

### CI/CD Linting

```json
{
  "scripts": {
    "lint:claude": "claude -p 'you are a linter. look at changes vs main and report issues related to typos. report filename:line on one line, description on second. no other text.'"
  }
}
```

### Writer/Reviewer Pattern

| Session A (Writer) | Session B (Reviewer) |
|-------|---------|
| `Implement a rate limiter` | |
| | `Review the rate limiter at @src/middleware/rateLimiter.ts for edge cases and race conditions` |
| `Address this feedback: [Session B output]` | |

---

## 5. Background Agents

### How They Work

Subagents can run in foreground (blocking) or background (concurrent):

- **Foreground**: blocks main conversation. Permission prompts pass through.
- **Background**: runs while you continue working. Permissions pre-approved at launch. Auto-denies unapproved operations.

Set `background: true` in agent frontmatter, or ask Claude to "run this in the background."

Press **Ctrl+B** to background a running task.

### Resume Failed Background Agents

If a background subagent fails due to missing permissions, resume it in foreground to retry with interactive prompts.

### Known Issues (February 2026)

- Sessions can freeze when launching multiple background agents with `run_in_background: true` and then calling TaskOutput with `block: true`
- Sessions can get stuck in "Channelling..." state after agents complete
- **Workaround**: spawn multiple agents in a single message without the `run_in_background` flag -- achieves parallel execution via synchronous completion path
- Max concurrent background agents: 5-10

### Disabling Background Tasks

```bash
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
```

---

## 6. The Task Tool

### Built-in Subagent Types

| Agent | Model | Purpose |
|-------|-------|---------|
| **Explore** | Haiku | Read-only codebase search. Three thoroughness levels: quick, medium, very thorough |
| **Plan** | Inherit | Research for plan mode. Read-only. |
| **General-purpose** | Inherit | Complex multi-step tasks requiring read + write |
| **Bash** | Inherit | Running terminal commands in separate context |

### Context Isolation Benefits

Subagents' primary value is context isolation. A test suite producing 50,000 chars of output stays in the subagent's context; only the summary returns to main conversation. This is critical for managing the context window.

### No Nesting

Subagents cannot spawn other subagents. For multi-step workflows, chain subagents from the main conversation or use Skills.

---

## 7. Lessons from Carlini's C Compiler Project

Nicholas Carlini built a 100,000-line Rust C compiler using 16 parallel Claude agents over ~2,000 sessions at ~$20,000 cost. Key lessons:

### What Worked

- **File-based task locking**: agents create lock files in `current_tasks/` dir; git sync prevents duplicate work
- **Oracle-based debugging**: for monolithic targets (Linux kernel), use GCC as known-good oracle, randomly compile files with GCC to enable parallel debugging
- **Tests as navigation**: high-quality tests served as the primary guidance system
- **Agent-optimized environment**: error messages include "ERROR" on same line as explanation for easy grep; logs pre-computed statistics
- **No central orchestrator**: agents autonomously identified "next most obvious" work, maintaining docs of attempted approaches

### What Failed

- **Monolithic parallelization**: 16 agents all hitting same bug simultaneously, overwriting each other's fixes
- **Regression**: new features frequently broke prior work; required CI with strict enforcement
- **Time blindness**: agents can't self-regulate test duration; needed `--fast` mode running 1-10% random samples

### Scaling Insight

No orchestrator was needed initially. Agents picking up autonomous work with good docs and lock files scaled better than centralized coordination for this kind of project.

---

## 8. Cost Analysis

### Token Consumption by Pattern

| Pattern | Approximate Cost |
|---------|-----------------|
| Solo session | ~200k tokens |
| 3 subagents (from solo) | ~440k tokens |
| 3-person agent team | ~800k tokens |
| 9-agent code review | ~1M+ tokens |
| Carlini C compiler | 2B input + 140M output (~$20k) |

### Cost Reduction Strategies

1. **Model splitting**: Opus for lead/complex reasoning, Sonnet/Haiku for focused subagent work
2. **maxTurns limits**: cap at 5-10 for search/review tasks
3. **Cache optimization**: aim for 60-80% cache read ratio; 30-60 min focused blocks; load all relevant files at session start
4. **Subagent scope**: limit to 3-4 active subagents to balance effectiveness vs overhead
5. **Context hygiene**: `/clear` between unrelated tasks; use subagents to isolate verbose output

---

## 9. Recommendations for Athanor

### Already In Place
- 4 custom agents with appropriate configs
- Agent Teams enabled
- Researcher agent uses `background: true` and `isolation: worktree`

### Should Adopt

1. **Persistent Memory for agents**: Add `memory: project` to `coder`, `infra-auditor`, and `doc-writer` agents. The researcher already has it. This builds institutional knowledge across sessions.

2. **Model splitting for cost**: Set `model: haiku` for `infra-auditor` (mostly read-only checks) and `model: sonnet` for `doc-writer` (prose generation). Keep `researcher` on `opus` and `coder` on inherited model.

3. **9-agent code review command**: Create `.claude/commands/code-review.md` using the hamy.xyz pattern for comprehensive PR review before committing.

4. **Fan-out for knowledge indexing**: When re-indexing knowledge base, use `claude -p` fan-out to process files in parallel batches rather than sequentially.

5. **Worktree isolation for build tasks**: Use `--worktree` when running `/build` mode to prevent interference with main working tree.

6. **TeammateIdle/TaskCompleted hooks**: Add quality gates that verify test passage before marking tasks complete.

7. **Writer/Reviewer pattern**: For significant changes, use two sessions -- one writes code, a fresh one reviews it (avoiding confirmation bias from the writing context).

### Avoid

- Running more than 5 background agents simultaneously (known stability issues)
- Nested team spawning (not supported)
- Using `run_in_background: true` with TaskOutput `block: true` (freezing bug)
- Over-relying on agent teams for sequential/simple work (cost overhead not justified)

---

## Sources

### Official Documentation
- [Agent Teams](https://code.claude.com/docs/en/agent-teams) -- full team coordination docs
- [Custom Subagents](https://code.claude.com/docs/en/sub-agents) -- subagent configuration reference
- [Common Workflows](https://code.claude.com/docs/en/common-workflows) -- worktrees, fan-out, Plan Mode
- [Best Practices](https://code.claude.com/docs/en/best-practices) -- scaling, context management, parallel sessions

### Engineering & Community
- [Building a C Compiler with Parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) -- Anthropic engineering blog, Carlini's 100k-line compiler
- [Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/) -- Addy Osmani's agent team patterns
- [From Tasks to Swarms](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/) -- 7 primitives, QA swarm example, cost data
- [9 Parallel AI Agents for Code Reviews](https://hamy.xyz/blog/2026-02_code-reviews-claude-subagents) -- 9-agent review setup
- [Claude Code Worktrees Guide](https://claudefa.st/blog/guide/development/worktree-guide) -- worktree patterns and migration use case
- [Sub-Agent Best Practices](https://claudefa.st/blog/guide/agents/sub-agent-best-practices) -- parallel vs sequential patterns
- [Mastering Git Worktrees with Claude Code](https://medium.com/@dtunai/mastering-git-worktrees-with-claude-code-for-parallel-development-workflow-41dc91e645fe) -- parallel development workflow
- [How to Set Up Agent Teams](https://darasoba.medium.com/how-to-set-up-and-use-claude-code-agent-teams-and-actually-get-great-results-9a34f8648f6d) -- practical setup guide
- [Agent Teams Complete Guide](https://claudefa.st/blog/guide/agents/agent-teams) -- comprehensive reference
- [Claude Code Background Tasks](https://apidog.com/blog/claude-code-background-tasks/) -- async workflow patterns
- [Background Agent Issues](https://github.com/anthropics/claude-code/issues/20679) -- known freezing bug
- [Cost-Controlled Workflow Workshop](https://dev.to/software_mvp-factory/workshop-build-a-cost-controlled-claude-code-workflow-save-40-60-on-ai-tokens-p6b) -- 40-60% token savings
- [Awesome Claude Code Subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) -- 100+ specialized subagent examples
