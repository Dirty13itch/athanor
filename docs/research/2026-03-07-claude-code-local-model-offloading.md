# Claude Code Local Model Offloading: Reducing Anthropic API Token Consumption

**Date:** 2026-03-07
**Status:** Research complete
**Purpose:** Identify every practical method for offloading token-intensive work from Claude Code (Anthropic API) to local models running on the Athanor cluster, while maintaining quality for tasks that require it.

---

## Context

Claude Code runs on DEV (192.168.1.189) under a $200/month Anthropic Max subscription. Max subscriptions have periodic quota throttling, and every token consumed is a token that could have been handled locally for free. The cluster already runs:

| Slot | Model | Node | Endpoint | Strength |
|------|-------|------|----------|----------|
| `reasoning` | Qwen3-32B-AWQ (TP=2) | Foundry (.244) | LiteLLM :4000 | Complex reasoning, tool calling, architecture |
| `fast` | Qwen3.5-35B-A3B-AWQ-4bit | Workshop (.225) | LiteLLM :4000 | Fast MoE inference, general coding |
| `coding` | Huihui-Qwen3-8B-abliterated-v2 | Foundry (.244) | LiteLLM :4000 | Quick code generation, uncensored |
| `creative` | GLM-4.7-Flash-GPTQ-4bit | Foundry (.244) | LiteLLM :4000 | Creative writing, narrative |
| `embedding` | Qwen3-Embedding-0.6B | DEV (.189) | LiteLLM :4000 | Semantic search |

LiteLLM proxy at VAULT (192.168.1.203:4000) routes all of these. The MCP bridge at `scripts/mcp-athanor-agents.py` already exposes `deep_research`, `coding_generate`, `coding_review`, `coding_transform`, `knowledge_search`, and `knowledge_graph` tools to Claude Code via the agent server at Foundry:9000.

Existing tools on DEV: Claude Code (primary), Aider (local model fallback), Claude Code Router (CCR, routes to non-Anthropic providers), OpenCode, Codex CLI, Gemini CLI, Kimi CLI.

### What This Research Covers

Seven offloading strategies, each analyzed for: what it offloads, how to implement it with existing infrastructure, estimated token savings, quality tradeoffs, and implementation effort.

---

## Strategy 1: Pre-Processing — Context Summarization Before Claude

### What It Offloads

When Claude Code reads large files, long git diffs, test outputs, or log files, those tokens flow through the Anthropic API. A local model can summarize or compress this content before it reaches Claude's context window.

### Implementation Options

**Option A: UserPromptSubmit Hook with Local Summarization**

A `UserPromptSubmit` hook could detect when the user is about to ask Claude to analyze something large, and pre-summarize it locally. However, hooks fire on user prompts, not on tool results, so this only works for content the user pastes directly.

**Option B: PostToolUse Hook for Large Read/Bash Results**

More promising. A `PostToolUse` hook fires after every tool call. When `Read` or `Bash` returns large output (>5K tokens), the hook could:
1. Pipe the output to a local model via `curl http://192.168.1.203:4000/v1/chat/completions`
2. Return a structured summary
3. Inject the summary as additional context

The problem: PostToolUse hooks cannot currently modify the tool output that Claude sees. They can only add feedback or block. The tool output is already in context by the time the hook fires. This is a fundamental limitation.

**Option C: MCP Proxy for Smart File Reading**

Build an MCP server that wraps file reading with summarization:
- `smart_read(file, max_tokens=2000)` — reads a file, and if it exceeds `max_tokens`, sends it to the local `reasoning` model for summarization before returning
- `smart_diff(branch)` — runs `git diff`, summarizes if large
- `smart_log(file, lines=1000)` — reads log, extracts key events

This is the most viable approach. Claude Code would call `mcp__smart_reader__smart_read` instead of the native `Read` tool. It requires Claude to prefer the MCP tool over native, which can be encouraged via CLAUDE.md instructions.

**Option D: Pre-Compact Context Compression**

Before context compaction triggers, use the `PreCompact` hook to:
1. Dump current conversation to a temp file
2. Send it to the local `reasoning` model with instructions to create a dense summary
3. Write the summary to `/tmp/athanor-session-state.md`

This already partially exists in `pre-compact-save.sh`, but it only saves git state and infra health. Adding LLM-driven conversation summarization would preserve more signal through compaction.

### Estimated Token Savings

- File reads: 30-60% reduction on files >500 lines (average file read is ~1K tokens, large files can be 5-20K)
- Git diffs: 50-80% reduction on multi-file diffs
- Log analysis: 70-90% reduction (logs are extremely verbose)
- Compaction quality improvement is harder to quantify but addresses the "quality degrades with cumulative compactions" problem documented in session-optimization research

### Quality Tradeoffs

- Summarization loses detail. If Claude later needs a specific line from a summarized file, it has to re-read.
- Qwen3-32B's summarization quality is strong for structured content (code, configs, logs) but may miss subtle context in prose.
- Latency: local summarization adds 2-10 seconds per call depending on input size.

### Implementation Effort

- MCP Smart Reader: Medium (new MCP server, ~200 lines Python)
- Enhanced PreCompact: Low (extend existing hook, ~50 lines)
- PostToolUse approach: Not viable with current hook API

---

## Strategy 2: Task Delegation — Route Entire Tasks to Local Models

### What It Offloads

Complete, well-defined tasks where the specification is clear but execution is mechanical. The existing Local Coder subagent (`.claude/agents/coder.md`) and MCP bridge tools already implement this pattern.

### Current State

The Local Coder subagent dispatches via four MCP tools:
- `coding_generate` — new code from spec
- `coding_review` — code review
- `coding_transform` — refactoring
- `knowledge_search` — project pattern lookup

These route through the agent server at Foundry:9000, which uses Qwen3-32B-AWQ.

### Gaps in Current Implementation

**1. Claude Code rarely invokes the Local Coder subagent automatically.**

The subagent exists, but Claude Code defaults to doing everything itself. There is no mechanism that automatically routes appropriate tasks to the Local Coder. It only fires when the user explicitly requests it or when Claude decides to delegate (which it almost never does without prompting).

**Fix: Add routing guidance to CLAUDE.md.** Add a section like:
```markdown
## Local Model Delegation

For these tasks, use the Local Coder subagent instead of doing them yourself:
- Boilerplate generation (new files from templates, CRUD endpoints, data models)
- Adding type hints to existing Python code
- Writing unit tests for existing functions
- Converting between formats (JS to TS, class to functional, sync to async)
- Generating Ansible tasks/roles from specifications
- Code review of generated code (use coding_review for a second opinion)

For these tasks, use deep_research instead of WebSearch/WebFetch:
- Any research that would require 3+ web searches
- Comparing technologies, benchmarks, or pricing
- Investigating error messages or obscure configs

Keep in Claude Code: architecture decisions, novel problem-solving, multi-file refactoring
where the "how" is uncertain, creative writing, anything requiring judgment about tradeoffs.
```

**2. No test-writing delegation.**

The MCP bridge has `coding_generate` but no test-specific tool. Test writing is highly mechanical and perfect for local models.

**Fix: Add `coding_write_tests` tool to MCP bridge** that receives the source code and generates pytest/vitest tests.

**3. No batch mode.**

Claude Code processes tasks one at a time. For bulk operations (add type hints to 20 files, generate tests for a module), it serially processes each file, burning tokens on context for each iteration.

**Fix: Add `coding_batch` tool** that accepts a list of files + transformation and processes them all locally in parallel, returning a summary of changes.

### Task Categories and Routing Recommendations

| Task Category | Estimated % of CC Work | Route To | Quality Impact |
|--------------|----------------------|----------|----------------|
| Boilerplate generation | 15-20% | Local `coding_generate` | Negligible — spec is clear |
| Test writing | 10-15% | Local `coding_write_tests` | Low — tests are verifiable |
| Code review (second pass) | 5-10% | Local `coding_review` | Medium — catches different bugs |
| Format conversion | 5-8% | Local `coding_transform` | Low — mechanical transformation |
| Documentation generation | 5-10% | Local `coding_generate` | Low — docstrings/READMEs are template-driven |
| Research/web search | 10-15% | Local `deep_research` | Medium — Qwen3-32B good but not Claude-tier |
| Architecture/design | 15-20% | Keep in Claude Code | N/A — this is where Claude excels |
| Complex debugging | 10-15% | Keep in Claude Code | N/A — requires deep reasoning |
| Multi-file refactoring | 5-10% | Keep in Claude Code | N/A — needs holistic understanding |

### Estimated Token Savings

If 40-50% of tasks can be routed locally, and those tasks average 5K tokens each (input + output), that is 2-2.5K tokens saved per delegated task. Over a heavy day of 100 tasks, that is ~200K-250K tokens saved.

### Implementation Effort

- CLAUDE.md routing guidance: Low (add 20 lines to CLAUDE.md)
- New MCP tools (tests, batch): Medium (extend mcp-athanor-agents.py, ~100 lines)
- Automatic routing via hook: Not recommended — too brittle, better to let Claude decide with strong guidance

---

## Strategy 3: Tool Augmentation via Aider

### What It Offloads

Aider is purpose-built for pair programming with LLMs. It understands git, manages diffs, handles multi-file edits, and runs test-fix loops. Critically, it can use local models via LiteLLM.

### Current State

Aider is installed on DEV with shell functions for different backends:
- `aider-glm()` — routes to GLM-4.7 API
- `aider-or()` — routes to OpenRouter

But there is **no `aider-local()` function pointing at local vLLM** despite the infrastructure being ready.

### Implementation Options

**Option A: Aider as Claude Code Subagent via Bash**

Claude Code can invoke Aider in headless mode:
```bash
aider --model openai/Qwen3-32B-AWQ \
  --openai-api-base http://192.168.1.203:4000/v1 \
  --openai-api-key not-needed \
  --message "Add type hints to all functions in agents/server.py" \
  --yes \
  --no-auto-commits \
  --file agents/server.py
```

This runs Aider with a local model, makes the edit, and returns. Claude Code sees the file changes and can review them.

**Pros:** Aider handles the full edit cycle (read file, plan changes, apply diff, handle errors). Claude Code only spends tokens reviewing the result.
**Cons:** Aider with local models produces lower-quality diffs than with Claude/GPT-5. Qwen3-32B scores ~40-55% on Aider benchmarks vs. 72-88% for frontier models. May need a review pass.

**Option B: Aider for Test-Fix Loops**

This is Aider's strongest use case. The loop is:
1. Claude Code identifies a failing test or writes a test spec
2. Claude Code invokes Aider: `aider --message "Fix failing test in test_auth.py" --test-cmd "pytest test_auth.py" --yes`
3. Aider iterates with the local model until tests pass
4. Claude Code reviews the final diff

The test-fix loop is particularly well-suited to local models because the feedback signal (pass/fail) is deterministic. The model can iterate cheaply.

**Option C: Add `aider-local` Shell Function**

Add to `.bashrc`:
```bash
aider-local() {
  aider --model "openai/reasoning" \
    --openai-api-base http://192.168.1.203:4000/v1 \
    --openai-api-key not-needed \
    "$@"
}
```

This is the simplest integration — just use Aider directly for tasks that don't need Claude-tier intelligence.

### Estimated Token Savings

- Each Aider session that replaces a Claude Code session saves 100% of those tokens (5K-50K per task)
- Test-fix loops can burn 10-30K tokens in Claude Code due to multiple iterations. Offloading saves all of it.
- Realistic savings: 15-25% of total daily token usage for mechanical coding tasks

### Quality Tradeoffs

- Aider + Qwen3-32B is weaker at complex multi-file edits. It works well for single-file changes.
- The test-fix loop is self-correcting, so quality converges regardless of initial model strength.
- Aider's diff format sometimes produces malformed patches with local models. Needs monitoring.

### Implementation Effort

- Shell function: Trivial (1 line)
- Claude Code integration via Bash tool: Low (CLAUDE.md guidance + bash commands)
- Automated dispatch: Medium (would need a PreToolUse hook or similar)

---

## Strategy 4: Caching — Avoid Re-Processing Entirely

### What It Offloads

Repeated operations that produce the same result: re-reading unchanged files, re-analyzing the same codebase structure, re-summarizing the same documentation.

### Implementation Options

**Option A: Anthropic Prompt Caching (Already Active)**

Prompt caching is enabled by default and saves 90% on cached input tokens. The system prompt, CLAUDE.md, rules, and skill descriptions are all candidates for caching. This is already working but worth understanding the mechanics:
- Cache TTL: 5 minutes (resets on each use)
- Cache hit rate depends on how much the conversation prefix is stable
- With Athanor's large system prompt (~8-15K tokens), this saves $0.50-1.50/MTok vs. uncached reads

**Option B: Local Semantic Cache via Redis**

Build a cache layer in the MCP bridge:
1. Before sending a request to a local model, hash the prompt
2. Check Redis for a cached response
3. If hit, return immediately (0 tokens, 0 latency)
4. If miss, call the model and cache the result with a TTL

This is most valuable for `knowledge_search` and `coding_review` where the same queries recur across sessions. Redis is already running on VAULT.

**Option C: File Content Cache for MCP Smart Reader**

If Strategy 1's Smart Reader is built, add content-addressed caching:
- Hash file path + modification time + summarization parameters
- Cache the summary in Redis with a long TTL (hours/days)
- Invalidate on file modification (inotify or mtime check)

Repeated reads of the same file across sessions return instantly.

**Option D: Session State Persistence (Enhanced MEMORY.md)**

Many tokens are burned re-establishing context after session starts, compactions, or `/clear`. The more context that persists in MEMORY.md and topic files, the fewer tokens Claude spends re-discovering it.

Current MEMORY.md is at 142/200 lines. The researcher agent's MEMORY.md is empty. Systematically populating agent memories with stable patterns would reduce per-session context-building cost.

### Estimated Token Savings

- Prompt caching: Already active, 30-50% reduction on system prompt tokens
- Redis semantic cache: 5-15% reduction on repeated MCP calls
- File content cache: 10-20% on frequently-read files across sessions
- Better MEMORY.md: 5-10% on session-start context building

### Implementation Effort

- Redis cache in MCP bridge: Low-Medium (~50 lines Python, Redis already available)
- File content cache: Medium (needs hash-based cache + invalidation logic)
- MEMORY.md population: Ongoing discipline, no code required

---

## Strategy 5: Effort Level Optimization

### What It Offloads

Not offloading to a different model, but reducing token consumption within Claude Code itself by controlling how much Claude "thinks."

### Current State

Athanor does not set `CLAUDE_CODE_EFFORT_LEVEL`. Default is `high`, which uses maximum thinking budget (up to 31,999 tokens per response). Many tasks don't need this.

### Implementation Options

**Option A: Per-Session Effort Setting**

When launching Claude Code for routine tasks (service restarts, log reading, simple edits), start with:
```bash
CLAUDE_CODE_EFFORT_LEVEL=medium claude
```

This reduces thinking tokens by ~50% for tasks that don't need deep reasoning.

**Option B: Dynamic Effort via UserPromptSubmit Hook**

A hook that analyzes the user's prompt and sets effort level:
```bash
# Detect simple commands and suggest lower effort
if echo "$prompt" | grep -qiE '^(restart|check|read|show|list|cat|ls)'; then
  echo "Consider using /effort medium for this routine task."
fi
```

This is advisory only — hooks cannot currently change effort level mid-session. But it raises awareness.

**Option C: Subagent Effort Configuration**

Set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` for agent team members doing focused tasks. Haiku 4.5 costs ~$1/$5 per MTok vs. Opus at $5/$25. For subagents doing focused work (reading files, running tests, checking status), Haiku is sufficient.

This is the single highest-impact effort optimization for agent teams.

### Estimated Token Savings

- Medium effort default: 30-50% reduction in thinking tokens (~10K-15K saved per response)
- Haiku subagents: 80% cost reduction on subagent tokens
- Combined: 20-40% overall cost reduction for sessions that use both

### Quality Tradeoffs

- Medium effort may miss subtle reasoning steps on complex problems
- Haiku subagents are less capable at code generation but adequate for file reading, test running, status checking
- Risk: some tasks that seem simple turn out to need deep reasoning. Starting at medium and escalating to high is the safe pattern.

### Implementation Effort

- Per-session effort: Trivial (environment variable)
- Haiku subagents: Low (one setting change)
- Dynamic effort hook: Low-Medium (needs prompt classification, advisory only)

---

## Strategy 6: Goose for Scheduled/Overnight Automation

### What It Offloads

Scheduled, repetitive tasks that Claude Code currently handles interactively: security audits, dependency updates, code quality scans, infrastructure health reports, documentation freshness checks.

### Current State

Goose is bookmarked for installation but not yet deployed. The `docs/dev-environment.md` identifies it as the "first candidate for an agent running entirely on Athanor hardware."

### What Goose Can Handle (Zero API Cost)

Goose Recipes (YAML-based workflows) running on local vLLM:

1. **Nightly code quality scan:** Goose reads the codebase, runs linters, identifies TODO/FIXME comments, reports issues
2. **Documentation drift detection:** Compare docs to code, flag stale references
3. **Dependency audit:** Check for outdated packages, known vulnerabilities
4. **Infrastructure health report:** SSH into nodes, collect metrics, generate daily summary
5. **Test coverage analysis:** Run test suites, report gaps
6. **Pre-morning briefing:** Generate a status report before Shaun starts work

Each of these currently burns 5-20K Claude Code tokens when done interactively. Running them overnight on local models costs nothing.

### Implementation Path

1. Install Goose on DEV or Foundry
2. Configure it to use local vLLM: `GOOSE_PROVIDER=openai OPENAI_HOST=http://192.168.1.203:4000`
3. Write Recipes for each scheduled task
4. Schedule via cron or systemd timers
5. Output to a `/reports/` directory that Claude Code can read on-demand

### Known Issue

The autonomous coding agent research (`2026-02-26-autonomous-coding-agent-options.md`) identifies that Goose + vLLM tool calling can be unreliable with some models. Qwen3-32B-AWQ with `--tool-call-parser qwen3_coder` should work but needs testing.

### Estimated Token Savings

- 5-6 automated tasks * 10K tokens avg = 50-60K tokens/day
- Over a month: 1.5-1.8M tokens saved
- At Opus rates ($5/$25 per MTok): $10-45/month saved

### Implementation Effort

- Goose installation: Low
- Recipe writing: Medium (one per task, 20-50 lines YAML each)
- Cron scheduling: Low
- Total: 1-2 days of work

---

## Strategy 7: Claude Code Hooks for Intelligent Routing

### What It Offloads

Use the hook system to intercept Claude Code's operations and route appropriate ones to local infrastructure automatically, without requiring Claude to explicitly delegate.

### Implementation Options

**Option A: PreToolUse Hook for WebSearch/WebFetch Interception**

When Claude Code is about to do a web search or fetch a URL, intercept and route to the local research agent:

```bash
#!/bin/bash
# PreToolUse hook: intercept web operations and offer local alternative
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL" = "WebSearch" ] || [ "$TOOL" = "WebFetch" ]; then
  QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // .tool_input.url // ""')
  # Don't block, but inject guidance
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"Consider using deep_research() for this query instead — it uses local Qwen3-32B with web search, knowledge base lookup, and multi-source synthesis, saving Claude tokens.\"}}"
fi
exit 0
```

This is advisory — it reminds Claude that a local alternative exists without blocking the operation. True interception would require exit code 2 to block + redirect, which risks breaking the workflow.

**Option B: SubagentStart Hook for Model Selection**

When Claude spawns a subagent, inject model selection guidance:
```bash
#!/bin/bash
INPUT=$(cat)
echo "Reminder: For this subagent, consider whether Haiku or the Local Coder would be sufficient. Only use Opus/Sonnet for tasks requiring complex reasoning."
exit 0
```

**Option C: PostToolUse Token Counter**

Track cumulative token usage and inject warnings:
```bash
#!/bin/bash
INPUT=$(cat)
# Append tool usage to session log
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
echo "$(date +%s) $TOOL" >> /tmp/claude-token-tracker.log

# Count operations this session
COUNT=$(wc -l < /tmp/claude-token-tracker.log 2>/dev/null || echo 0)
if [ "$COUNT" -gt 50 ]; then
  echo "Note: $COUNT tool calls this session. Consider delegating remaining mechanical tasks to local models via the Local Coder subagent or Aider."
fi
exit 0
```

**Option D: UserPromptSubmit Smart Router**

Analyze the user's prompt and suggest local routing:
```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // ""')

# Detect tasks suitable for local delegation
if echo "$PROMPT" | grep -qiE '(write tests|add type hints|generate boilerplate|convert to|refactor|rename)'; then
  echo '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"This task appears mechanical. Consider delegating to the Local Coder subagent (coding_generate or coding_transform) to save tokens."}}'
fi
exit 0
```

### Estimated Token Savings

Hooks are enablers, not direct savings. They increase the probability that other strategies (2, 3, 6) are actually used. Estimated indirect savings: 10-20% of total usage if hooks successfully redirect even a fraction of delegatable tasks.

### Quality Tradeoffs

- Advisory hooks (exit 0 with context injection) are safe but Claude may ignore them
- Blocking hooks (exit 2) are deterministic but risk breaking workflows when the local alternative fails
- The best approach is advisory with strong CLAUDE.md guidance

### Implementation Effort

- Advisory hooks: Low (simple bash scripts, 15-30 lines each)
- Token tracking: Low
- Smart router: Medium (needs prompt classification, risk of false positives)

---

## Synthesis: Prioritized Implementation Plan

### Tier 1: Do Now (High Impact, Low Effort)

| Action | What | Token Savings | Effort |
|--------|------|---------------|--------|
| **Add delegation guidance to CLAUDE.md** | Tell Claude when to use Local Coder vs. doing it itself | 15-25% | 30 min |
| **Set CLAUDE_CODE_SUBAGENT_MODEL=haiku** | Use Haiku for agent team subagents | 80% on subagent tokens | 1 min |
| **Add `aider-local` shell function** | Enable Aider with local vLLM for pair programming | 100% on delegated tasks | 5 min |
| **Set CLAUDE_CODE_EFFORT_LEVEL=medium** for routine sessions | Reduce thinking tokens for simple tasks | 30-50% thinking reduction | 1 min |

### Tier 2: Do This Week (Medium Impact, Medium Effort)

| Action | What | Token Savings | Effort |
|--------|------|---------------|--------|
| **Add `coding_write_tests` MCP tool** | Dedicated test generation via local model | 10-15% on test tasks | 2 hours |
| **Add `coding_batch` MCP tool** | Batch file transformations locally | 5-10% on bulk operations | 2 hours |
| **Add UserPromptSubmit smart router hook** | Advisory prompt classification for delegation | Enables other savings | 1 hour |
| **Add Redis semantic cache to MCP bridge** | Cache repeated knowledge_search/review calls | 5-15% on repeated queries | 3 hours |
| **Populate agent MEMORY.md files** | Reduce per-session context building tokens | 5-10% on session starts | 2 hours |

### Tier 3: Do This Month (High Impact, Higher Effort)

| Action | What | Token Savings | Effort |
|--------|------|---------------|--------|
| **Build MCP Smart Reader** | Summarize large files/diffs before returning to Claude | 10-20% on file reads | 1 day |
| **Deploy Goose with local model recipes** | Overnight automation of scheduled tasks | 50-60K tokens/day | 2 days |
| **Enhanced PreCompact with local summarization** | Better context preservation through compaction | Quality improvement > token savings | 4 hours |
| **Aider integration as Claude Code Bash tool** | Claude invokes Aider for test-fix loops | 15-25% on iterative tasks | 4 hours |

### Tier 4: Evaluate Later

| Action | What | Why Wait |
|--------|------|----------|
| **PostToolUse output compression** | Summarize large tool outputs | Requires Claude Code API changes (hooks can't modify output) |
| **Automatic task routing via PreToolUse blocks** | Block Claude from doing tasks locally possible | Too brittle; advisory approach is safer |
| **Fine-tuned local models for Athanor patterns** | Train Qwen3-8B on Athanor's codebase | Requires significant training data and infrastructure |

---

## Estimated Total Impact

### Conservative Scenario (Tier 1 + Tier 2)

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Avg daily Claude Code tokens | 500K | 325K | 35% |
| Monthly cost impact (Max sub) | Quota usage | Quota lasts longer | Fewer throttling events |
| Tasks handled locally | 0% | 25-35% | Meaningful |

### Aggressive Scenario (All Tiers)

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Avg daily Claude Code tokens | 500K | 200K | 60% |
| Monthly cost impact | Quota usage | Significantly reduced | Rare throttling |
| Tasks handled locally | 0% | 50-60% | Transformative |

### Where Claude Code MUST Stay

These categories should never be offloaded:

1. **Architecture decisions** — Claude's reasoning about system design, tradeoffs, and multi-component interactions is significantly better than Qwen3-32B
2. **Novel problem-solving** — Tasks where the approach itself is uncertain
3. **Cross-codebase refactoring** — Multi-file changes requiring holistic understanding
4. **Security-critical code review** — Where missing a vulnerability has real consequences
5. **Complex debugging** — Reproducing and fixing subtle bugs requiring deep reasoning
6. **User interaction design** — Where judgment about human experience matters
7. **Final review of locally-generated code** — Claude as quality gate, not generator

---

## Open Questions

1. **Token counting accuracy:** Claude Code does not expose per-request token counts in hooks. The statusline shows cumulative context usage but not per-operation costs. Better visibility would help measure the impact of these strategies.

2. **Hook-based routing reliability:** How often does Claude follow advisory context injected via hooks vs. ignoring it? Needs empirical testing.

3. **Aider + Qwen3-32B diff quality:** The Aider polyglot benchmark shows ~40-55% for 30B-class models. Is this good enough for the mechanical tasks we want to offload? Needs testing on Athanor's actual codebase.

4. **Goose + vLLM tool calling stability:** The autonomous agent research flagged potential issues. Needs testing before relying on it for overnight automation.

5. **Max subscription quota mechanics:** Does Anthropic throttle based on total tokens or request count? This affects which optimization strategies have the most impact on quota longevity.

6. **Claude Code Router (CCR) effectiveness:** CCR can route background tasks to non-Anthropic providers (GLM, OpenRouter). How does this interact with the local model strategies? Could CCR route to local vLLM directly?

---

## Comparison: Local Model Quality vs. Claude Code

Based on available benchmarks and the existing model stack:

| Task Type | Claude (Opus 4.6) | Qwen3-32B-AWQ | Quality Gap | Offload? |
|-----------|-------------------|---------------|-------------|----------|
| Architecture reasoning | 80.8% SWE-bench | ~50-55% (est.) | Large | No |
| Standard coding | 79.6% (Sonnet) | ~50-55% (est.) | Moderate | Selective |
| Test writing | High | Moderate | Moderate | Yes (verifiable) |
| Boilerplate | High | Good | Small | Yes |
| Code review | Excellent | Good (catches different bugs) | Moderate | Yes (complementary) |
| Refactoring | Excellent | Adequate for mechanical | Moderate | Yes (single-file) |
| Research/synthesis | Excellent | Good (with web tools) | Moderate | Yes (first pass) |
| Documentation | Excellent | Good | Small | Yes |
| Log analysis | Excellent | Good (pattern matching) | Small | Yes |

Note: Qwen3-32B benchmark scores on Aider are not directly available. The ~50-55% estimate is based on similar-class models (DeepSeek V3 at 70-74% is a much larger model; 32B models typically score 40-55%). This needs empirical validation on Athanor's workloads.

---

## Sources

### Existing Athanor Research
- `docs/research/2026-02-26-claude-code-hooks-and-power-user-patterns.md` — Hook system reference, all 17 events
- `docs/research/2026-02-26-claude-code-session-optimization.md` — Context window mechanics, compaction, token efficiency
- `docs/research/2026-02-25-cloud-coding-api-cascade.md` — Multi-provider cascade, model benchmarks, cost analysis
- `docs/research/2026-02-26-claude-code-thinking-mechanisms.md` — Effort levels, thinking token budgets
- `docs/research/2026-02-26-autonomous-coding-agent-options.md` — Goose, Aider, local agent evaluation
- `docs/research/2026-02-26-claude-code-plugin-mcp-ecosystem.md` — Plugin/MCP landscape, LSP plugins
- `docs/dev-environment.md` — Current tool stack, fallback chain, subscriptions

### Claude Code Documentation
- [Hooks Reference](https://code.claude.com/docs/en/hooks) — Hook events, handler types, JSON schemas
- [Sub-agents](https://code.claude.com/docs/en/sub-agents) — Subagent configuration, isolation, memory
- [Model Configuration](https://code.claude.com/docs/en/model-config) — Effort levels, model aliases, environment variables
- [Manage Costs Effectively](https://code.claude.com/docs/en/costs) — Token optimization, MCP overhead

### External
- [Aider Leaderboard](https://aider.chat/docs/leaderboards/) — Model coding benchmarks
- [LiteLLM Provider Docs](https://docs.litellm.ai/docs/providers) — Routing configuration
- [Goose Documentation](https://block.github.io/goose/) — Recipes, headless mode, provider setup

---

Last updated: 2026-03-07
