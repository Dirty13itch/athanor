# Claude Code Session Optimization and Context Management

**Date:** 2026-02-26
**Author:** Research Agent
**Status:** Complete
**Scope:** Practical techniques for maximizing Claude Code productivity across long sessions and complex projects

---

## Context

Athanor is a complex project with 130-line CLAUDE.md, 142-line MEMORY.md (of 200-line auto-load limit), 9 path-scoped rules (206 lines total), 12 skills (849 lines), 7 hooks, 5 MCP servers, and 10 plugins. This represents substantial baseline context overhead before any work begins. This research consolidates official documentation, community wisdom, and Athanor-specific analysis into actionable guidance.

---

## 1. Context Window Mechanics

### How the 200K Window Is Actually Divided

The 200K token context window is not fully available for conversation. As of early 2026:

| Segment | Tokens | Percentage |
|---------|--------|------------|
| System prompt + CLAUDE.md + rules + memory | ~8-15K | 4-7% |
| MCP server tool definitions (5 servers) | ~10-25K | 5-12% |
| Skill descriptions (loaded at start) | ~2-5K | 1-2.5% |
| Compaction buffer (reserved) | ~33K | 16.5% |
| **Usable for conversation + tool results** | **~120-150K** | **60-75%** |

The compaction buffer was reduced from 45K to 33K tokens in early 2026 (related to v2.1.21), giving roughly 12K more usable space than before.

**Key numbers:**
- Auto-compaction triggers at ~83.5% usage (~167K tokens)
- Previous trigger was ~77-78% (~155K tokens)
- The 33K buffer is used for the summarization process itself and is not configurable
- Only the trigger percentage is tunable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`

### What Compaction Preserves and Loses

**Preserved (high priority):**
- Completed work and key decisions
- Current file modifications in progress
- Active task state and next steps
- User constraints and preferences stated in conversation

**Often lost or degraded:**
- Detailed instructions from early in the conversation
- Behavioral framework references get paraphrased
- Specific numbers (IP addresses, port numbers, device info)
- Structured data loses fidelity with cumulative compactions
- Code snippets from early turns

**Critical warning from multiple sources:** Quality degrades with cumulative compactions. Models can "go off the rails" if auto-compact triggers mid-task. Structured prompts survive compaction at 92% fidelity versus 71% for narrative formats.

---

## 2. Compaction Strategies

### Manual vs. Automatic Compaction

**Auto-compaction (default):** Triggers at ~83.5% capacity (or whatever `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is set to). Athanor currently sets this to 80%, which means compaction fires earlier than default, giving more working space for summarization but less usable context before the first compaction.

**Manual compaction (`/compact`):** Best done at logical breakpoints (task boundaries, not mid-implementation). Accepts custom focus instructions.

### Custom Compaction Instructions

Three methods, in order of reliability:

**1. CLAUDE.md section (persistent across sessions):**
```markdown
# Compact instructions

When you are using compact, please focus on:
- Git state and uncommitted changes
- Active task progress and next steps
- Infrastructure state changes made this session
- Specific file paths, IP addresses, and port numbers mentioned
```

**2. Inline with /compact command (one-time):**
```
/compact Focus on code changes, API modifications, and deployment steps
```

**3. Pre-compaction recap message (manual technique):**
Before running `/compact`, write a message like:
```
Summary: Modified auth.ts and user.ts to add JWT validation.
Changed vLLM config on Node 1 from TP=2 to TP=4.
Next step: run ansible-playbook to deploy, then verify with curl.
Infrastructure: Node 1 at .244, Node 2 at .225, VAULT at .203.
```
This message gets preserved and guides Claude after compaction.

### Athanor's PreCompact Hook

The existing hook at `.claude/hooks/pre-compact-save.sh` captures git state, uncommitted changes, and infrastructure status to `/tmp/athanor-session-state.md`. This is good but has a gap: the saved file is not automatically re-injected into context after compaction (PostCompact hooks do not exist yet -- they are still a feature request per GitHub issue #14258 and #17237).

**Recommendation:** Add a note in the "Compact Instructions" section of CLAUDE.md telling Claude to read `/tmp/athanor-session-state.md` after compaction occurs.

---

## 3. Auto-Memory Optimization

### How Auto-Memory Works

- `MEMORY.md` is loaded into the system prompt at session start
- **Only the first 200 lines are loaded** -- content beyond 200 lines is silently ignored
- Topic files (e.g., `debugging.md`, `infrastructure.md`) are NOT loaded at startup -- Claude reads them on demand
- Each project gets its own memory directory at `~/.claude/projects/<project>/memory/`
- Git worktrees get separate memory directories

### Current Athanor State

MEMORY.md is at 142 lines of the 200-line limit, leaving 58 lines of headroom. The total memory directory is 1,036 lines across 8 files, with detailed content properly split into topic files.

**Assessment:** The current structure is well-optimized. The MEMORY.md acts as an index with references to topic files, which is exactly the recommended pattern. However, 142/200 lines means any significant additions will hit the limit.

### Optimization Techniques

1. **Audit for redundancy:** After 10+ sessions, MEMORY.md typically contains ~30% redundant entries. Review and consolidate.
2. **Move details to topic files:** If MEMORY.md approaches 180 lines, move detailed sections to new topic files and replace with one-line references.
3. **Explicit memorization:** Tell Claude directly: "remember that X" or "save to memory that Y". This is more reliable than hoping auto-memory captures what matters.
4. **Disable for CI:** Set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` in CI/automation environments.

---

## 4. Session Management Patterns

### When to /clear vs. Continue

| Situation | Action | Rationale |
|-----------|--------|-----------|
| Switching to unrelated task | `/rename` then `/clear` | Stale context wastes tokens on every subsequent message |
| Continuing same feature | Just keep going | Context is relevant |
| Context at 60%+ on a new subtask | `/compact` with focus | Preserve what matters, reclaim space |
| Debugging a session-specific issue | `--continue` | Picks up exact state |
| Want to try alternative approach | `--fork-session` | Branches conversation without affecting original |
| Returning after hours/days | `--resume` (interactive picker) | Choose by name/branch |

### Session Naming Conventions

Name sessions early with `/rename` for easy retrieval:
- Feature work: `vllm-tp4-migration`, `agent-memory-refactor`
- Infrastructure: `node1-gpu-setup`, `vault-backup-config`
- Research: `research-infiniband-edr`, `research-model-comparison`
- Debugging: `debug-qdrant-timeout`, `debug-comfyui-oom`

### Resume Strategies

- `claude --continue`: Instantly loads most recent session (interrupted work)
- `claude --resume`: Interactive picker, shows all sessions for current directory
- `/resume` inside a session: Switch between conversations without exiting
- `--fork-session`: Creates new session ID while preserving conversation history up to that point

**Keyboard shortcuts in `/resume` picker:** `R` to rename, `P` to preview.

### Parallel Sessions with Worktrees

Claude Code has built-in worktree support via `--worktree`:
- Each agent gets its own checkout of the repository
- Subagents can use `isolation: worktree` in their frontmatter
- Worktrees are automatically cleaned up when subagents finish
- Athanor already uses this (the current working directory is a worktree)

---

## 5. Token Efficiency

### Token-Heavy Operations (Avoid or Minimize)

| Operation | Token Cost | Mitigation |
|-----------|-----------|------------|
| MCP server tool definitions | ~2-5K per server, always loaded | Disable unused servers; use CLI tools instead |
| Reading large files without line limits | Thousands of tokens per file | Use `--lines` or specify range |
| Full test suite output | Can be 10K+ tokens | Use hooks to filter to failures only |
| Vague prompts ("improve this codebase") | Triggers broad scanning | Be specific about files and goals |
| Agent teams | ~7x standard token usage | Keep teams small, tasks focused |
| Extended thinking at default budget | 31,999 tokens per turn | Reduce with `MAX_THINKING_TOKENS=8000` for simple tasks |

### Token-Light Operations (Prefer These)

| Operation | Why It's Efficient |
|-----------|-------------------|
| Specific file references in prompts | No scanning needed |
| Plan mode (Shift+Tab) | 50% fewer tokens than execution mode |
| Structured prompts over narrative | 30% fewer tokens (280 vs 450 typical) |
| CLI tools (gh, docker, git) over MCP | No persistent tool definitions |
| Skills (on-demand loading) | Full content only loads when invoked |
| Subagents for verbose operations | Output stays in subagent context |

### MCP Server Token Overhead

Each MCP server contributes ~2-5K tokens just by being connected. With 5 servers, that is 10-25K tokens of overhead before any work begins.

**Athanor's current MCP load (5 servers):**
- sequential-thinking
- context7
- filesystem
- grafana
- athanor-agents

**Mitigation:** When tool descriptions exceed 10% of context, Claude Code automatically defers them via tool search (loading on-demand). This threshold is configurable: `ENABLE_TOOL_SEARCH=auto:5` triggers deferral at 5% instead of 10%.

---

## 6. Model Switching Strategy

### Model Aliases Available

| Alias | Model | Best For | Relative Cost |
|-------|-------|----------|--------------|
| `sonnet` | Sonnet 4.6 | Daily coding, most tasks | 1x (baseline) |
| `opus` | Opus 4.6 | Complex reasoning, architecture, debugging | ~5x |
| `haiku` | Haiku 3.5 | Simple tasks, boilerplate, formatting | ~0.3x |
| `opusplan` | Opus for planning, Sonnet for execution | Complex features needing both depth and throughput | ~2-3x |
| `sonnet[1m]` | Sonnet 4.6 with 1M context | Long sessions, large codebases | Higher beyond 200K |

### When to Use Each

**Haiku** -- Quick fixes, variable renaming, import updates, boilerplate generation, simple formatting. Specify `model: haiku` in subagent configurations for routine tasks.

**Sonnet** -- Default for 90% of work. Writing logic, managing state, connecting APIs, multi-file edits. Reliable and consistent.

**Opus** -- Architecture decisions, complex debugging, multi-step reasoning, final review passes. Use when quality matters more than speed.

**OpusPlan** -- Best hybrid: Opus reasons through the plan, Sonnet executes it. Good for complex features where you want deep analysis but efficient implementation.

**Sonnet[1m]** -- When you know a session will be long (large refactors, multi-file migrations). Standard rates apply until 200K tokens; beyond that, long-context pricing applies. Proportionally increases the compaction buffer and usable space.

### Switching Commands

```bash
# At startup
claude --model opus

# Mid-session
/model sonnet

# For subagents (environment variable)
export CLAUDE_CODE_SUBAGENT_MODEL=haiku

# Pin specific versions (for stability)
export ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
export ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
```

### Default Model Behavior

- **Max subscribers** (Athanor's plan): Default is Opus 4.6
- Claude Code may automatically fall back to Sonnet if you hit a usage threshold with Opus
- The `/fast` toggle uses the same model with faster output -- it does NOT switch models

---

## 7. Effort Levels

### What They Actually Do

The effort parameter controls how much internal reasoning (thinking tokens) Claude allocates per response.

| Level | Behavior | Token Impact | Use When |
|-------|----------|-------------|----------|
| **High** (default) | Full extended thinking on every response | Highest (31,999 thinking budget) | Complex reasoning, architecture, debugging |
| **Medium** | Balanced thinking, may skip for simple problems | Moderate | General coding, mixed complexity |
| **Low** | Minimal thinking, optimizes for speed | Lowest, may skip thinking entirely | Simple lookups, quick fixes, classification |

### Configuration

```bash
# Environment variable
export CLAUDE_CODE_EFFORT_LEVEL=medium

# In /model UI: use left/right arrow keys on effort slider

# In settings.json
{ "effortLevel": "medium" }

# Disable adaptive reasoning entirely (revert to fixed budget)
export CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1
```

### Practical Guidance

For Athanor's workload profile (infrastructure management, multi-node deployment, agent architecture), **high effort is appropriate as the default**. The complex multi-system reasoning benefits from full thinking budgets.

For routine operations (restarting services, reading logs, simple file edits), temporarily switching to medium saves tokens without meaningful quality loss.

---

## 8. Output Format and Piping

### Available Output Formats

```bash
# Human-readable (default)
claude "fix the bug"

# JSON (for programmatic processing)
claude --output-format json "analyze this function"

# Stream JSON (real-time NDJSON with every token, turn, tool interaction)
claude --output-format stream-json "refactor auth module"

# With JSON schema validation
claude --output-format json --json-schema '{"type":"object","properties":{"files":{"type":"array","items":{"type":"string"}}}}' "list modified files"

# Pipe to jq for extraction
claude --output-format json "explain the bug" | jq '.result'
```

### Stream Chaining (Multi-Agent Pipelines)

```bash
# Chain Claude instances: one analyzes, next implements
claude --output-format stream-json "plan the refactor" | \
  claude --input-format stream-json "implement this plan"
```

### Max Output Tokens

```bash
# Default: 32,000 tokens. Max: 64,000.
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000
```

This controls response length only. It does NOT affect compaction buffer or trigger threshold.

---

## 9. Environment Variables Reference (Athanor-Relevant)

### Currently Set in Athanor

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "0"
  }
}
```

### Recommended Additions to Evaluate

| Variable | Value | Rationale |
|----------|-------|-----------|
| `ENABLE_TOOL_SEARCH` | `auto:5` | Defer MCP tool definitions earlier (5% vs default 10%), saving ~5-10K tokens of baseline overhead |
| `MAX_THINKING_TOKENS` | `16000` | Halve thinking budget for routine sessions while keeping quality (current default is 31,999) |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `64000` | Prevent truncation on long code generation |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | (default is fine) | Only adjust if large file reads are truncating |
| `MAX_MCP_OUTPUT_TOKENS` | `25000` | Default is 25K, sufficient for most MCP responses |

### Variables NOT to Change

| Variable | Current | Why Keep It |
|----------|---------|------------|
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `80` | Already well-tuned. Lower values (60-70) compact too aggressively; higher values (90+) risk running out of space mid-task |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | `0` | Auto-memory is essential for Athanor's cross-session continuity |
| `DISABLE_PROMPT_CACHING` | (not set = enabled) | Prompt caching saves significant cost on repeated system prompt content |

---

## 10. Athanor-Specific Recommendations

### Immediate Wins

**1. Add Compact Instructions to CLAUDE.md:**
```markdown
# Compact instructions

When compacting, preserve:
- All IP addresses, port numbers, and node names (Foundry .244, Workshop .225, VAULT .203, DEV .215)
- Git state and uncommitted changes
- Active task progress, file paths being modified, and next steps
- Any infrastructure state changes made this session
- Read /tmp/athanor-session-state.md after compaction for pre-compaction snapshot
```

**2. Enable Earlier Tool Search Deferral:**
Add to settings.json env:
```json
"ENABLE_TOOL_SEARCH": "auto:5"
```
This reduces baseline MCP overhead from 10-25K tokens to whatever is actually needed per task.

**3. Add `/context` Checks to Session Start Hook:**
The existing `session-start-health.sh` could log context usage to help track overhead trends.

### Memory Optimization

- MEMORY.md is at 142/200 lines. Audit for entries that are now covered by topic files (infrastructure.md, operational-knowledge.md) and can be replaced with one-line references.
- The operational-knowledge.md (342 lines) is loaded on-demand, which is correct -- it should stay as a topic file, not merged into MEMORY.md.

### Session Workflow for Complex Tasks

1. Start with `/rename` to name the session descriptively
2. Use plan mode (Shift+Tab) for analysis before implementation
3. At ~60% context, write a recap message then `/compact` with focus
4. For multi-step infrastructure work, use the pre-compaction recap technique
5. If context gets exhausted, `/clear` and start a new named session with a clear handoff prompt
6. For truly long work, consider `sonnet[1m]` to avoid compaction entirely

### Model Strategy for Athanor

- **Default (Opus 4.6):** Appropriate for architecture, debugging, multi-system reasoning
- **Switch to Sonnet:** For routine ansible runs, simple file edits, documentation updates
- **Haiku for subagents:** Set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` for agent team members doing focused tasks
- **OpusPlan for features:** Best for complex new features (deep analysis + efficient execution)

---

## Sources

### Official Documentation
- [Manage Claude's Memory](https://code.claude.com/docs/en/memory) -- Memory hierarchy, auto-memory, CLAUDE.md structure
- [Model Configuration](https://code.claude.com/docs/en/model-config) -- Model aliases, effort levels, environment variables
- [Manage Costs Effectively](https://code.claude.com/docs/en/costs) -- Token optimization, MCP overhead, context management
- [How Claude Code Works](https://code.claude.com/docs/en/how-claude-code-works) -- Agentic loop, context window, checkpoints
- [Claude Code Settings](https://code.claude.com/docs/en/settings) -- Complete environment variable reference
- [Effort Parameter](https://platform.claude.com/docs/en/build-with-claude/effort) -- Effort level behavior and impact
- [Hooks Reference](https://code.claude.com/docs/en/hooks) -- PreCompact and other hook events
- [Best Practices](https://code.claude.com/docs/en/best-practices) -- Official best practices

### Community and Analysis
- [Context Buffer: The 33K-45K Token Problem](https://claudefa.st/blog/guide/mechanics/context-buffer-management) -- Buffer mechanics and tuning
- [Context Management Optimization](https://institute.sfeir.com/en/claude-code/claude-code-context-management/optimization/) -- 10-technique ranking with savings percentages
- [Claude Code for Advanced Users](https://cuttlesoft.com/blog/2026/02/03/claude-code-for-advanced-users/) -- Power user tips
- [Context Compaction Research](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f) -- Cross-tool comparison (Claude Code, Codex CLI, OpenCode, Amp)
- [Named Sessions](https://dev.to/rajeshroyal/named-sessions-your-git-branches-have-names-why-shouldnt-your-claude-sessions-43oc) -- Session naming patterns
- [Worktree Support](https://claudefa.st/blog/guide/development/worktree-guide) -- Parallel session guide
- [Token Optimization Techniques](https://deepwiki.com/FlorianBruniaux/claude-code-ultimate-guide/10.4-token-optimization-techniques) -- Token budget management
- [Stop Wasting Tokens (60% Reduction)](https://medium.com/@jpranav97/stop-wasting-tokens-how-to-optimize-claude-code-context-by-60-bfad6fd477e5) -- Context optimization guide
- [54% Token Reduction](https://gist.github.com/johnlindquist/849b813e76039a908d962b2f0923dc9a) -- Practical reduction techniques

### Feature Requests (Gaps)
- [PostCompact Hook (Issue #14258)](https://github.com/anthropics/claude-code/issues/14258) -- Not yet implemented
- [Custom Compaction Control (Issue #25528)](https://github.com/anthropics/claude-code/issues/25528) -- Requested, not implemented
- [Custom Auto-Compact Instructions (Issue #14160)](https://github.com/anthropics/claude-code/issues/14160) -- Requested
