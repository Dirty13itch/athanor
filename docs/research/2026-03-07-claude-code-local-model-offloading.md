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

## Strategy 8: Prompt Caching Deep-Dive — Maximizing Cache Hits

### How Claude Code Uses Prompt Caching

Claude Code automatically uses Anthropic's prompt caching. The system prompt, CLAUDE.md, rules, MCP tool definitions, and conversation history are all cached. The cache breakpoint automatically moves forward as conversations grow — each new request caches everything up to the last cacheable block, and previous content is read from cache.

**Source:** [Anthropic Prompt Caching Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

### Cache Mechanics

| Parameter | Value |
|-----------|-------|
| Default TTL | 5 minutes (refreshes on each hit) |
| Extended TTL | 1 hour (2x base input price for writes) |
| Cache read cost | 0.1x base input price |
| 5-min cache write cost | 1.25x base input price |
| 1-hour cache write cost | 2.0x base input price |
| Min cacheable tokens (Opus 4.6) | 4,096 |
| Min cacheable tokens (Sonnet 4.6) | 2,048 |
| Min cacheable tokens (Haiku 4.5) | 4,096 |

**Critical fact:** Cached input tokens do NOT count toward rate limits (ITPM). This effectively multiplies throughput capacity for sessions with stable prefixes.

### What Invalidates the Cache

Cache entries follow a hierarchy: `tools → system → messages`. Changes at any level invalidate that level and all subsequent levels.

| Change | Tools Cache | System Cache | Messages Cache |
|--------|------------|-------------|----------------|
| Tool definitions change | Invalid | Invalid | Invalid |
| Web search toggle | Valid | Invalid | Invalid |
| Citations toggle | Valid | Invalid | Invalid |
| Speed setting change | Valid | Invalid | Invalid |
| Thinking parameters change | Valid | Valid | Invalid |
| Adding/removing images | Valid | Valid | Invalid |

**Athanor-specific risks:**
- Adding/removing MCP servers mid-session invalidates the entire cache (tool definitions change)
- Timestamp injection in system prompts would invalidate the system cache on every request
- Switching models mid-session creates a completely new cache

### Maximizing Cache Hits in Athanor

1. **Keep MCP server list stable within sessions.** Don't connect/disconnect servers mid-conversation. The 5 MCP servers + deferred tools already add ~10-25K tokens to context. Every time this list changes, the full prefix is re-processed.

2. **Keep CLAUDE.md stable.** Every edit to CLAUDE.md during a session invalidates the system cache. Make edits between sessions, not during.

3. **Maintain conversation cadence.** The 5-minute TTL means pausing for >5 minutes between messages forces a full re-cache of the prefix. During active coding sessions, this is rarely a problem. During review/think/type sessions, it can be significant.

4. **Use 1-hour TTL for agent workflows.** Athanor agents that take >5 minutes between API calls should use the 1-hour cache option. The 2x write cost is recovered after just 2 cache reads vs. the ~5 re-caches that would happen in a 1-hour session with the 5-minute TTL.

### Estimated Savings from Cache Optimization

Anthropic's official docs state prompt caching can reduce input costs by up to 90% for long conversations. For Athanor specifically:

| Scenario | Without Caching | With Caching | Savings |
|----------|----------------|--------------|---------|
| 100-turn Opus session (15K system prompt) | $50-100 input | $10-19 input | 60-80% |
| Stable system prompt (8K tokens) | $0.04/msg | $0.004/msg | 90% |
| 5 MCP servers (20K tool defs) | $0.10/msg | $0.01/msg | 90% |

Caching is already active by default, but the key insight is: **avoid actions that invalidate it.** The biggest cache-busting culprits in Athanor are MCP server changes and model switches mid-session.

---

## Strategy 9: Speculative Decoding for Local Inference Speedup

### What It Does

Speculative decoding uses a small "draft" model to predict multiple tokens, which the larger "verifier" model then validates in parallel. This reduces latency (tokens/sec) without changing output quality. It doesn't offload tokens from Claude, but it makes local models fast enough that developers prefer them for more tasks.

### Available Methods in vLLM (as of 2026-03)

| Method | Status | Description | Best For |
|--------|--------|-------------|----------|
| **Eagle3** | Production | Draft model uses hidden states from 3 verifier layers. SOTA accuracy. | General speedup, 2-2.5x typical |
| **MTP** | Production (Qwen3.5) | Multi-token prediction built into model architecture | Qwen3.5-35B-A3B specifically |
| **N-gram** | Production | No draft model needed, uses prompt n-grams for speculation | Code completion, repetitive text |
| **Draft Model** | Not yet supported | Traditional small→large verification | Blocked in vLLM |

**Source:** [vLLM Speculative Decoding Docs](https://docs.vllm.ai/en/latest/features/spec_decode/), [Eagle3 Blog Post](https://developers.redhat.com/articles/2025/07/01/fly-eagle3-fly-faster-inference-vllm-speculative-decoding)

### Applicability to Athanor's Models

**Qwen3.5-35B-A3B-AWQ on Workshop 5090:**
- MTP-1 is natively supported by Qwen3.5's architecture
- For latency-sensitive workloads at low concurrency, MTP-1 reduces TPOT with high acceptance rate
- Trade-off: lower throughput under concurrent load (fine for single-user homelab)
- Enable with: `--speculative-config '{"method": "mtp", "num_speculative_tokens": 1}'`

**Qwen3-32B-AWQ on Foundry (TP=2):**
- Eagle3 is available but requires a compatible Eagle3 draft model trained for Qwen3-32B (check HuggingFace for `eagle3-qwen3-32b` variants)
- N-gram speculation works out of the box with no additional model needed
- Enable n-gram with: `--speculative-config '{"method": "ngram", "num_speculative_tokens": 3, "prompt_lookup_num_tokens": 5}'`

**Qwen3-8B on Foundry GPU 3:**
- N-gram speculation is the pragmatic choice — the model is small enough that draft model overhead would negate the benefit
- Eagle3 draft models for 8B verifiers may not exist

### Expected Speedup

| Method | Typical Speedup | VRAM Overhead | Quality Impact |
|--------|----------------|---------------|----------------|
| Eagle3 | 2.0-2.5x | 10-15% additional | None (mathematically identical output) |
| MTP-1 | 1.3-1.8x | Minimal (built-in) | None |
| N-gram | 1.2-1.5x (code), 1.0-1.1x (prose) | None | None |

### Why This Matters for Offloading

Local model latency is the #1 reason developers reach for Claude instead. If Qwen3-32B generates at 15 tok/s baseline and Eagle3 pushes it to 30-35 tok/s, the UX gap narrows significantly. Faster local inference makes the offloading strategies in Strategies 2-3 more practical because developers won't lose patience waiting for local results.

### Implementation Effort

- N-gram: Trivial (add flag to existing vLLM serve command)
- MTP for Qwen3.5: Low (add speculative-config, test stability)
- Eagle3: Medium (find/verify compatible draft model, additional VRAM)

---

## Strategy 10: Context Window Management

### Where Claude Code Spends Tokens

According to [Anthropic's official cost management docs](https://code.claude.com/docs/en/costs), Claude Code's context window is divided as follows:

| Segment | Tokens | Notes |
|---------|--------|-------|
| System prompt + CLAUDE.md + rules + memory | 8-15K | Loaded every session |
| MCP tool definitions (5 servers) | 10-25K | Present even when idle |
| Skill descriptions | 2-5K | Loaded at session start |
| Compaction buffer | ~33K | Reserved, not configurable |
| **Usable conversation space** | **120-150K** | 60-75% of 200K |

**Key stat from Anthropic:** Average Claude Code cost is $6/developer/day, with 90th percentile at $12/day. Monthly average with Sonnet 4.6: ~$100-200/developer.

### Token Waste Patterns in Athanor

1. **Re-reading files across sessions.** Claude Code has no file cache across sessions. Every `/resume` that references the same files re-reads them from scratch. Athanor's `CLAUDE.md` alone is 130+ lines; `MEMORY.md` is 142 lines; rules total 206 lines across 9 files.

2. **MCP server overhead.** 5 MCP servers + deferred tools contribute 10-25K tokens to every message's prefix. Per the official docs: "Each MCP server adds tool definitions to your context, even when idle." The `ENABLE_TOOL_SEARCH=auto:<N>` setting can defer tools that exceed N% of context, but currently defaults to 10%.

3. **Thinking token burn.** Default extended thinking budget is 31,999 tokens per response. At Opus output rates ($25/MTok), a single max-thinking response costs $0.80 in thinking tokens alone. Most routine tasks (file reads, simple edits, status checks) don't need this.

4. **Agent team multiplication.** Agent teams use ~7x more tokens than standard sessions because each teammate maintains its own context window. Each teammate loads CLAUDE.md, MCP servers, and skills independently.

5. **Compaction quality degradation.** Quality degrades with cumulative compactions. Structured prompts survive at 92% fidelity vs. 71% for narrative. Critical numbers (IPs, ports, container names) often get lost.

### Actionable Optimizations

**A. Move specialized instructions from CLAUDE.md to skills.**

Official recommendation: "Keep CLAUDE.md under ~500 lines." Athanor's CLAUDE.md is already 130 lines (reasonable), but there's an opportunity to move the hardware table, GPU assignments, and gotchas into on-demand skills that load only when relevant.

**B. Lower tool search threshold.**

Set `ENABLE_TOOL_SEARCH=auto:5` in settings. This defers MCP tool descriptions when they exceed 5% of context (default is 10%). With 5 MCP servers contributing 10-25K tokens, a lower threshold keeps more context available for actual work.

**C. Use `/clear` aggressively between tasks.**

Each `/clear` resets conversation context while preserving session identity. Between unrelated tasks, this prevents stale context from inflating prefix costs on every subsequent message.

**D. Use `/compact` with custom focus.**

```
/compact Focus on: current file paths, IP addresses, port numbers, uncommitted git changes, active task state
```

This tells the compactor to preserve the high-value structured data that tends to get lost in default compaction.

**E. Delegate verbose operations to subagents.**

Running tests, fetching docs, or processing logs should go to subagents. The verbose output stays in the subagent's context; only a summary returns to the main conversation.

**F. Write specific prompts.**

"Improve this codebase" triggers broad scanning. "Add input validation to the login function in auth.ts" targets precisely. Anthropic's docs specifically call this out as a cost optimization.

---

## Strategy 11: Hybrid Routing via LiteLLM

### Current State

LiteLLM on VAULT:4000 routes all agent inference. ADR-012 established the architecture: all consumers go through LiteLLM, engine swap = config change. Currently configured with contract-driven slots (reasoning, fast, coding, creative, embedding).

### Adding Cloud Fallback Chains

LiteLLM supports fallback configuration natively. The architecture is:

```yaml
model_list:
  # Primary: local model (free)
  - model_name: "reasoning"
    litellm_params:
      model: "openai/Qwen3-32B-AWQ"
      api_base: "http://192.168.1.244:8000/v1"
      api_key: "not-needed"
    model_info:
      order: 1  # Highest priority

  # Fallback: cloud model (paid)
  - model_name: "reasoning"
    litellm_params:
      model: "anthropic/claude-sonnet-4-6-20260217"
      api_key: "os.environ/ANTHROPIC_API_KEY"
    model_info:
      order: 2  # Lower priority

router_settings:
  routing_strategy: "usage-based-routing"
  enable_pre_call_checks: true
  # Fallback to cloud when local fails
  default_fallbacks: ["anthropic/claude-sonnet-4-6-20260217"]
```

This gives automatic cloud escalation when local models are unavailable (GPU maintenance, OOM, vLLM crash) without any consumer-side code changes.

### Intelligent Routing Beyond Fallback

LiteLLM's `usage-based-routing` strategy distributes load, but doesn't understand task complexity. For true hybrid routing:

**Option A: Custom Router Plugin**

LiteLLM supports custom routing functions. A plugin could inspect the request's system prompt or message content and route:
- Simple tasks (< 500 input tokens, no tool calls) → local fast model
- Complex tasks (architecture keywords, multi-file references) → cloud
- Cost-aware: if daily cloud spend exceeds threshold, force local

**Option B: Slot-Based Routing (Current Pattern)**

The existing slot system (reasoning, fast, coding, creative) already enables routing. Extend it:
- `reasoning-local` → Qwen3-32B (free)
- `reasoning-cloud` → Claude Sonnet (paid)
- Let the consumer (agent code) decide which slot based on task complexity
- This is simpler than automatic routing and gives agents explicit control

**Option C: Quality Cascade**

Route to local first, evaluate the response quality (using a judge model or heuristic), and re-route to cloud if quality is insufficient. This is the most sophisticated but adds latency and complexity.

### Recommendation

Option B (slot-based routing) is the right starting point. The agent code already understands task complexity — let it choose the slot. Add Option A's cost threshold as a guardrail so cloud usage can't spiral.

---

## Strategy 12: Qwen3-Coder-Next — A Potential Game-Changer

### What It Is

Released February 2026, Qwen3-Coder-Next is an 80B-total / 3B-active MoE model specifically designed for coding agents. It uses hybrid attention (Gated DeltaNet + MoE with 512 experts, 10 active per token) and supports 256K context.

**Source:** [Qwen3-Coder-Next Blog](https://qwen.ai/blog?id=qwen3-coder-next), [HuggingFace AWQ-4bit](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit)

### Benchmarks

| Benchmark | Qwen3-Coder-Next | Claude Sonnet 4.5 | Claude Opus 4.6 | Qwen3-32B |
|-----------|-------------------|-------------------|-----------------|-----------|
| SWE-Bench Pro | 44.3% | 46.1% | — | — |
| Aider Polyglot | 66.2% | — | 72.0% | 40.0% |
| SWE-Bench Verified | — | 79.6% (Sonnet 4.6) | 80.8% | — |

The 66.2% Aider score is a massive jump from Qwen3-32B's 40.0%. For the mechanical coding tasks targeted by offloading, this narrows the gap to Claude significantly.

### VRAM Requirements

| Quantization | Size | Fits On |
|-------------|------|---------|
| AWQ-4bit | 45.9 GB | FOUNDRY TP=4 (4x 5070Ti = 64GB), Workshop TP=2 (5090+5060Ti = 48GB) |
| FP8 | ~80 GB | FOUNDRY TP=4 + 4090 (88GB) |

### Deployment Options in Athanor

**Option A: Workshop TP=2 (5090 + 5060Ti)**

Replace Qwen3.5-35B-A3B + ComfyUI with Qwen3-Coder-Next AWQ-4bit on both GPUs. Requires `--tensor-parallel-size 2`. This sacrifices the fast agent slot and ComfyUI.

- Pros: Highest coding quality available locally
- Cons: Loses fast inference and image generation

**Option B: FOUNDRY TP=4 (4x 5070Ti)**

Replace the current Qwen3-32B (TP=2) + GLM-4.7 + Qwen3-8B with Qwen3-Coder-Next across all 4x 5070Ti. 45.9GB fits in 64GB.

- Pros: Best coding model on the most powerful inference node
- Cons: Loses all three current models. Single model for all tasks.

**Option C: Wait for Smaller Variant**

Qwen3-Coder (not Next) may have smaller variants coming. The MoE architecture (3B active) means a potential AWQ-4bit that fits in 16-24GB may be feasible for future releases.

### Recommendation

Don't deploy Qwen3-Coder-Next yet. The 45.9GB AWQ-4bit requires sacrificing too many existing models. The 40.0% → 66.2% Aider jump is compelling, but Athanor needs the multi-model diversity (reasoning + creative + coding + fast) more than a single excellent coding model. Monitor for a smaller variant or quantization that fits alongside existing models.

---

## Updated Benchmarks: Local Model Quality vs. Claude Code

Verified data from [Aider Leaderboard](https://aider.chat/docs/leaderboards/) (accessed 2026-03-07) and [16x Engineer Eval](https://eval.16x.engineer/blog/qwen3-coder-evaluation-results):

| Model | Aider Polyglot | SWE-bench Verified | Cost/Aider Run | Notes |
|-------|---------------|-------------------|----------------|-------|
| GPT-5 (high) | 88.0% | — | $29.08 | Top of leaderboard |
| Claude Opus 4.6 | 72.0% | 80.8% | $65.75 | Current CC model |
| Qwen3-Coder-Next | 66.2% | — | $0.00 (local) | Best open-source coding |
| Qwen3 235B A22B | 59.6% | — | $0.00 (local) | Too large for Athanor |
| Qwen3-32B | 40.0% | — | $0.76 | Current local model |
| Qwen3-32B (est. real coding) | ~6.8/10 avg | — | $0.00 (local) | 16x eval: struggles on uncommon patterns |

**Key insight:** Qwen3-32B at 40.0% Aider is adequate for boilerplate, test writing, and mechanical refactoring. It falls apart on uncommon patterns (scored 1/10 on TypeScript narrowing in 16x eval). The quality gap to Claude is real but task-dependent — for the ~40-50% of work that is mechanical, 40% Aider is "good enough" because the output is verifiable.

| Task Category | Offload to Local? | Quality Risk | Mitigation |
|--------------|-------------------|-------------|------------|
| Architecture reasoning | No | High | Claude's 80.8% SWE-bench matters here |
| Novel problem-solving | No | High | Local models fail on uncommon patterns |
| Multi-file refactoring | No | Medium-High | Requires holistic codebase understanding |
| Complex debugging | No | High | Deep reasoning required |
| Boilerplate generation | Yes | Low | Output is verifiable, spec is clear |
| Test writing | Yes | Low | Tests are self-verifying (pass/fail) |
| Single-file refactoring | Yes | Low-Medium | Mechanical, diffs are reviewable |
| Format conversion | Yes | Low | Mechanical transformation |
| Documentation | Yes | Low | Template-driven, reviewable |
| Code review (second pass) | Yes | Medium | Catches different bugs than Claude |
| Research (first pass) | Yes | Medium | Local deep_research + web tools |
| Log analysis | Yes | Low | Pattern matching, structured output |

---

## Cost Quantification

### Current Claude Code Costs (Estimated)

Based on Anthropic's published average of $6/dev/day with Sonnet ($100-200/month) and Athanor running Opus:

| Usage Level | Daily Tokens | Monthly Cost (Opus API) | Monthly Cost (Max $200 sub) |
|-------------|-------------|------------------------|----------------------------|
| Light (2-3 hrs/day) | 200-300K | $25-50 | Included, no throttling |
| Medium (4-6 hrs/day) | 400-600K | $50-100 | Included, occasional throttling |
| Heavy (8+ hrs/day) | 800K-1.5M | $100-250 | Frequent throttling |
| Intensive (multi-agent) | 2-5M | $250-750 | Severe throttling |

**Max subscription economics:** At $200/month for Max 20x, Anthropic provides roughly 20x Pro quota. Claude Code tokens are included in the subscription. The constraint is quota throttling, not direct cost. Every token saved extends the quota, reducing throttling events.

### Savings by Strategy

| Strategy | Token Reduction | Monthly Value (vs. API) | Implementation Effort |
|----------|----------------|------------------------|----------------------|
| S1: Context summarization (MCP Smart Reader) | 10-20% on file reads | $10-40 | Medium (1 day) |
| S2: Task delegation to local models | 25-40% on delegated tasks | $25-80 | Low-Medium (half day) |
| S3: Aider for test-fix loops | 15-25% on iterative tasks | $15-50 | Low (1 hour) |
| S4: Caching (Redis + file content) | 5-15% on repeated queries | $5-25 | Low-Medium (3 hours) |
| S5: Effort level optimization | 30-50% on thinking tokens | $15-60 | Trivial (1 minute) |
| S6: Goose overnight automation | 50-60K tokens/day | $10-45 | Medium (2 days) |
| S7: Claude Code hooks (advisory) | Enables S2/S3/S6 usage | Indirect | Low (2 hours) |
| S8: Prompt caching optimization | Already active, avoid invalidation | $5-15 | Zero (behavior change) |
| S9: Speculative decoding for local | 0 (speed, not tokens) | UX improvement | Low-Medium |
| S10: Context window management | 10-20% on context overhead | $10-30 | Low (behavior change) |
| S11: LiteLLM hybrid routing | Enables automatic local-first | Infrastructure | Medium (half day) |
| S12: Qwen3-Coder-Next (future) | Could replace 50-60% of CC work | $50-120 | High (GPU reallocation) |

### Combined Savings Scenarios

**Conservative (S2 + S3 + S5 + S8 + S10):**
- Strategies that require minimal implementation
- Token reduction: 35-45%
- Monthly savings: $35-100 (API) or significant throttle reduction (Max sub)
- Implementation time: 2-4 hours

**Moderate (Conservative + S1 + S4 + S7 + S11):**
- Adds infrastructure for automated routing
- Token reduction: 50-60%
- Monthly savings: $50-150 or rare throttling events
- Implementation time: 2-3 days

**Aggressive (Moderate + S6 + S9 + S12):**
- Full local-first with cloud escalation
- Token reduction: 65-75%
- Monthly savings: $80-200+ or essentially no throttling
- Implementation time: 1-2 weeks

---

## Open Questions

1. **Token counting accuracy:** Claude Code does not expose per-request token counts in hooks. The statusline shows cumulative context usage but not per-operation costs. Use `/cost` to track session totals. Better per-operation visibility would help measure strategy impact.

2. **Hook-based routing reliability:** How often does Claude follow advisory context injected via hooks vs. ignoring it? Needs empirical testing. Strong CLAUDE.md guidance is more reliable than hooks alone.

3. **Aider + Qwen3-32B diff quality:** Aider polyglot benchmark shows 40.0% for Qwen3-32B. This is adequate for single-file mechanical tasks but unreliable for complex edits. The test-fix loop mitigates this (deterministic pass/fail feedback). Needs testing on Athanor's actual codebase.

4. **Goose + vLLM tool calling stability:** The autonomous agent research flagged potential issues. Qwen3-32B-AWQ with `--tool-call-parser qwen3_coder` should work but needs testing before overnight automation.

5. **Max subscription quota mechanics:** Throttling is based on a rolling 5-hour window + weekly quota. Both Pro and Max quotas are shared between Claude web and Claude Code. Max 20x gives ~900 messages per 5-hour window. Token consumption (not just message count) determines quota usage — reducing tokens per message directly extends quota.

6. **Eagle3 draft model availability for Qwen3-32B:** Check HuggingFace for compatible Eagle3 draft models. If none exist, n-gram speculation is the practical alternative.

7. **Qwen3-Coder-Next smaller variants:** Monitor Qwen releases for a model with similar coding quality that fits in 16-24GB VRAM, enabling deployment alongside existing models.

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

### Anthropic Official Documentation
- [Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — Cache mechanics, TTL, pricing, invalidation rules
- [Manage Costs Effectively](https://code.claude.com/docs/en/costs) — Token optimization, $6/dev/day average, MCP overhead
- [Sub-agents](https://code.claude.com/docs/en/sub-agents) — Model selection (haiku/sonnet/opus), cost control
- [Model Configuration](https://code.claude.com/docs/en/model-config) — Effort levels, thinking token budgets
- [Hooks Reference](https://code.claude.com/docs/en/hooks) — Hook events, handler types, JSON schemas
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Per-model token rates, cache pricing tiers
- [Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) — Tier structure, cached tokens exemption

### Benchmark Sources
- [Aider Leaderboard](https://aider.chat/docs/leaderboards/) — Qwen3-32B: 40.0%, Qwen3-Coder-Next: 66.2%, Opus 4.6: 72.0%, GPT-5: 88.0%
- [16x Engineer Qwen3 Coder Eval](https://eval.16x.engineer/blog/qwen3-coder-evaluation-results) — 5-task coding eval, Qwen3 Coder 6.8/10 avg vs Claude Opus 4 9.05/10
- [SWE-bench](https://www.swebench.com/) — Opus 4.6: 80.8%, Sonnet 4.6: 79.6%

### vLLM / Inference
- [vLLM Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode/) — Eagle3, MTP, n-gram methods
- [Qwen3.5 vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) — MTP-1 configuration
- [Eagle3 Speculative Decoding](https://developers.redhat.com/articles/2025/07/01/fly-eagle3-fly-faster-inference-vllm-speculative-decoding) — 2-2.5x speedup benchmarks
- [Speculators v0.3.0](https://blog.vllm.ai/2025/12/13/speculators-v030.html) — Eagle3 training, draft model standardization

### LiteLLM
- [Routing & Load Balancing](https://docs.litellm.ai/docs/routing-load-balancing) — Strategies, order-based priority
- [Fallbacks](https://docs.litellm.ai/docs/proxy/reliability) — Default fallback chains, error handling
- [Auto Routing](https://docs.litellm.ai/docs/proxy/auto_routing) — Usage-based, latency-based routing

### Model Sources
- [Qwen3-Coder-Next AWQ-4bit](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit) — 45.9GB, vLLM >=0.15.0 required
- [Qwen3-Coder-Next Guide](https://dev.to/sienna/qwen3-coder-next-the-complete-2026-guide-to-running-powerful-ai-coding-agents-locally-1k95) — VRAM tables, deployment examples

---

Last updated: 2026-03-07
