# Local AI Productivity Patterns: What Actually Works (March 2026)

**Date:** 2026-03-09
**Status:** Research complete
**Researcher:** Claude (Research Agent, Opus 4.6)
**Purpose:** Identify practical patterns that make local AI systems maximally productive for a single-operator homelab. Community-sourced findings, not academic papers.
**Context:** Athanor cluster -- 150GB+ VRAM, 6 GPUs, Claude Code + Aider + claude-squad, LiteLLM proxy, 9 specialized agents

---

## Table of Contents

1. [What the Most Productive Local AI Setups Look Like](#1-what-the-most-productive-local-ai-setups-look-like)
2. [The Claude Code + Local Model Hybrid Pattern](#2-the-claude-code--local-model-hybrid-pattern)
3. [Aider + Local Models](#3-aider--local-models)
4. [claude-squad / Parallel Sessions](#4-claude-squad--parallel-sessions)
5. [Goose + Local Models](#5-goose--local-models)
6. [Multi-Agent Patterns That Ship](#6-multi-agent-patterns-that-ship)
7. [Continuous Improvement Loops in Practice](#7-continuous-improvement-loops-in-practice)
8. [The Productivity Cliff](#8-the-productivity-cliff)
9. [Tool Use Reliability](#9-tool-use-reliability)
10. [Most Valuable Daily Agent Workflows](#10-most-valuable-daily-agent-workflows)

---

## 1. What the Most Productive Local AI Setups Look Like

### Hardware Sweet Spots (Community Consensus)

The community has converged on clear hardware tiers for productive local AI [1][2][3]:

| VRAM | Typical Setup | Model Tier | Token/s (4090) | Reality Check |
|------|--------------|------------|----------------|---------------|
| 16 GB | Single 4060 Ti or 5060 Ti | 7-14B models, Q4-Q8 | 55-62 tok/s | "Rough experience, more wrong edits + more retries" |
| 24 GB | Single 3090/4090 | 27-32B dense, 70B Q4 | 34 tok/s (32B dense), 196 tok/s (30B MoE) | Entry point for serious work |
| 32 GB | Single 5090 | 32B+ FP8, 70B Q4-Q6 | ~40-60 tok/s (32B) | "Changes the game for home servers" |
| 48 GB | Dual 3090s or 4090+3090 | 70B comfortable, 100B+ Q4 | Depends on TP/PP | Most common "serious" multi-GPU config |
| 88-150 GB | 4-6 consumer GPUs | 70B full precision, 100B+ models | Varies with TP | Athanor's tier; very few community setups this large |

**Key finding:** Memory bandwidth is the defining constraint, not compute. Token generation is memory-bound. This is why MoE models (3B active) on a single GPU generate 196 tok/s while dense 32B models generate 34 tok/s on the same GPU [2].

### What People with 100GB+ VRAM Actually Run

Most homelabbers at this tier run:
- **Primary reasoning model:** Qwen3-32B or Qwen3.5-27B (TP=2 or TP=4)
- **Fast agent model:** MoE variant (Qwen3.5-35B-A3B or Qwen3-30B-A3B)
- **Coding model:** Qwen2.5-Coder-32B or Qwen3-Coder-Next-80B-A3B
- **Utility model:** Small 7-9B for chat, triage, quick tasks
- **Embedding + reranker:** Running on CPU or a small GPU

The software stack that has standardized: **Ollama or vLLM** for serving, **Open WebUI** for chat interface, **n8n or LangGraph** for workflows, **LiteLLM** as a unified proxy [4].

### Athanor vs. Community Norms

Athanor's setup (4x 5070 Ti TP=4 for coordinator, 5090 for worker, 5060 Ti for utility/creative, 4090 for utility) is well above the community median. Most local AI setups run 1-2 GPUs. Having 6 GPUs with dedicated role assignment is rare but architecturally sound -- the key question is whether the operational complexity is worth the capability gain.

### Source Assessment

This data comes from hardware benchmarking sites and community guides, not direct Reddit scraping (reddit.com blocks Anthropic's crawler). The patterns are consistent across multiple independent sources.

---

## 2. The Claude Code + Local Model Hybrid Pattern

### How It Works

Claude Code speaks the Anthropic Messages API. To route it to local models, you need either:

1. **Native Anthropic API compatibility:** Ollama v0.14.0+ and LM Studio 0.4.1+ now natively support `/v1/messages` [5][6]
2. **Translation proxy:** Claude Code Router (CCR), LiteLLM, or custom middleware [7][8]

Configuration is simple:
```bash
export ANTHROPIC_BASE_URL=http://localhost:11434  # Ollama
# or
export ANTHROPIC_BASE_URL=http://vault.lan:4000   # LiteLLM
export ANTHROPIC_AUTH_TOKEN=<ATHANOR_LITELLM_API_KEY>
```

### What Works

- **Demos and MVPs:** "For building demos and MVPs and, importantly, for learning Claude Code, [local models] will be more than good enough" [9]
- **Cost elimination:** Zero API costs for routine coding tasks
- **Privacy:** All data stays on-premises
- **Fallback:** When Anthropic API quota runs out, local models keep you productive [10]

### What Breaks (The Real Problems)

**1. Tool calling is the #1 failure mode.** Users report being "left confused when many of the models I was trying didn't work. Tool calling seems unsupported by models other than the ones listed in the documentation." Error messages are unhelpful -- "API errors" that are actually model capability limits [9].

**2. Context window defaults are too small.** Ollama defaults to 4K tokens even for models supporting more. Claude Code is context-heavy (25K+ minimum recommended). Tool definitions + system prompts + conversation can consume 20-40K tokens before you've done anything [9][11].

**3. Quality gap is real and persistent.** Even on "beefy 128GB+ RAM machines," local models "get nowhere close to the sheer intelligence of Claude/Gemini." At worst, local models "will move you backwards and just increase the amount of work Claude has to do when your limits reset" [9].

**4. File operations fail silently.** Some local models fail at basic file writes -- asked to create a Python file, they respond with unrelated content instead [9].

**5. Configuration bugs.** Fresh installs don't honor `~/.claude/settings.json`. Workaround: set environment variables in shell or manually edit `~/.claude.json` with `"hasCompletedOnboarding": true` [9].

### Recommended Local Models for Claude Code

| Model | VRAM | Quality Assessment |
|-------|------|--------------------|
| Qwen3-Coder 30B-A3B | ~18 GB AWQ | Best balance of quality/speed |
| Qwen2.5-Coder 32B | ~20 GB AWQ | Strong coding, mature |
| Devstral Small 2 (24B) | ~14 GB | Good starting point |
| GLM4.7-Flash Q8 | ~16 GB | Strong value/latency tradeoff |

### Implication for Athanor

Athanor already has LiteLLM at VAULT:4000 with Anthropic API compatibility. The infrastructure is ready. The question is whether to route overflow Claude Code sessions to Qwen3.5-27B-FP8 on FOUNDRY. Based on community reports, this will work for:
- Boilerplate generation
- Test writing
- Simple refactoring
- Documentation

It will NOT work well for:
- Complex multi-file architecture changes
- Novel problem-solving
- Security-critical code review
- Long agentic tool-calling chains (error compounding)

**Recommendation:** Use the hybrid pattern with explicit task routing. Keep Claude Code (Anthropic) for architecture/reasoning. Route mechanical tasks to local Qwen3.5-27B via LiteLLM. Do not expect equivalent quality.

---

## 3. Aider + Local Models

### The Aider Leaderboard (March 2026)

Aider's polyglot benchmark tests code editing across 225 Exercism exercises in 6 languages. The scores reveal a stark quality hierarchy [12][13]:

**Top tier (70%+) -- API-only models dominate:**
| Model | Aider Score | Format | Local? |
|-------|-------------|--------|--------|
| GPT-5 (high) | 88.0% | diff | No |
| GPT-5 (medium) | 86.7% | diff | No |
| Gemini 2.5 Pro | 83.1% | diff-fenced | No |
| Grok 4 (high) | 79.6% | diff | No |
| DeepSeek V3.2-Exp (Reasoner) | **74.2%** | diff | **Yes** |
| Claude Opus 4 (32k thinking) | 72.0% | diff | No |
| DeepSeek R1 (0528) | **71.4%** | diff | **Yes** |
| DeepSeek V3.2-Exp (Chat) | **70.2%** | diff | **Yes** |

**Mid tier (55-70%) -- Open-source competitive:**
| Model | Aider Score | Format | Local? |
|-------|-------------|--------|--------|
| Qwen3-235B-A22B | **59.6%** | diff | Yes |
| DeepSeek R1 | **56.9%** | diff | Yes |
| DeepSeek V3 (0324) | **55.1%** | diff | Yes |

**Key finding:** No Qwen3.5 models appear on the Aider leaderboard yet (as of March 2026). The Qwen3-235B-A22B at 59.6% is the best Qwen entry. DeepSeek V3.2-Exp leads open-source at 74.2% -- but this is a cloud-hosted model, not practically runnable on consumer hardware.

### What Local Models Actually Work for Aider

For models that fit on Athanor's hardware:
- **Qwen2.5-Coder-32B:** 73.7% on Aider's older benchmark. Still the most battle-tested local coding model for Aider [14].
- **Qwen3.5-27B-FP8:** No Aider benchmark published yet, but SWE-bench 72.4% and LiveCodeBench 80.7 suggest strong performance. Worth testing.
- **Qwen3-Coder-Next 80B MoE (3B active):** SWE-bench 70.6%, likely ~60-65% on Aider polyglot. Fits on a single GPU but may struggle with Aider's diff format.

### Diff vs. Whole Edit Format

Models that score well on Aider's "diff" format (surgical edits) consistently outperform those using "whole" format (rewriting entire files). The diff format is harder -- the model must precisely specify line changes. MoE models with small active parameters (3B) often struggle more with diff precision than dense models.

For Aider with local models: use `--edit-format whole` with smaller/MoE models and `--edit-format diff` only with dense 27B+ models that have been validated.

### Implication for Athanor

Aider + Qwen3.5-27B-FP8 via LiteLLM is a strong pairing for:
- Test-fix loops (run tests, fix failures iteratively)
- Single-file edits with clear specifications
- Adding type hints, docstrings, error handling

The limiting factor is Aider's architecture: it's a pair programmer, not an autonomous agent. No daemon mode, no task queue, no persistent worker. Each `--message` invocation is one-shot. For autonomous overnight work, Aider is the wrong tool -- use Goose or the existing coding-agent.

---

## 4. claude-squad / Parallel Sessions

### Current State of the Ecosystem

Multiple tools now manage parallel Claude Code sessions [15][16][17][18]:

| Tool | Approach | Isolation | Agent Support |
|------|----------|-----------|---------------|
| **claude-squad** | tmux + git worktrees | Per-branch | Claude Code, Aider, Codex, OpenCode, Amp |
| **claude-tmux** | tmux popup | Per-session | Claude Code only |
| **CCManager** | Standalone TUI | Per-session | Claude Code, Gemini CLI, Codex, Cursor, Copilot |
| **parallel-cc** | git worktrees + E2B cloud | Per-worktree | Claude Code |
| **muxtree** | bash script + tmux + worktrees | Per-worktree | Any agent |
| **Agent Teams** (native) | Claude Opus 4.6 built-in | Per-agent (1M context each) | Claude Code |

### What Works for Autonomous Overnight Builds

**The C Compiler Experiment** is the most documented case [19]: 16 agents, nearly 2,000 Claude Code sessions, $20,000 in API costs, produced a 100,000-line Rust C compiler that can build Linux 6.9 on x86/ARM/RISC-V. The harness: a bare git repo, Docker containers per agent, a locking mechanism to prevent two agents solving the same problem.

**Key patterns from successful autonomous builds:**

1. **Simple loop harness:** When an agent finishes one task, it immediately picks up the next. No complex orchestration -- just a loop [19].
2. **Lock files prevent collision:** Agents claim tasks via filesystem locks. If two try the same task, one backs off.
3. **Small teams work better:** Start with 2-4 agents. Token consumption scales superlinearly -- "agent swarms burn through subscription limits faster than anyone predicted" [20].
4. **Pre-approve common operations:** Teammate permission requests bubble up to the lead, creating friction. Configure permission settings before spawning teammates [17].

### What Fails

**1. tmux sessions exit immediately.** Known bug (#27562) -- `claude --tmux --worktree` creates the worktree but the tmux session exits without starting Claude. Leaves orphaned worktrees requiring manual cleanup [21].

**2. Agent teams don't isolate worktrees.** Bug (#28175) -- requesting agents in separate worktrees results in all agents editing the same worktree, overwriting each other's files [22].

**3. Teammates stop on errors.** Instead of recovering, they halt and wait for human intervention. The lead may also declare the team "finished" prematurely [17].

**4. Path assumptions break in worktrees.** Absolute paths in CLAUDE.md or config files point to the main worktree, not the copy. Agents read wrong files or write to wrong locations.

**5. Token economics are harsh.** Agent teams consume significantly more tokens than single sessions. For serious overnight builds, the $100/month Max plan may not suffice.

### Practical Recipe for Athanor

Given these failure modes, the most reliable autonomous overnight pattern is:

```
1. Use claude-squad with explicit single-task prompts (not open-ended)
2. Each session gets one well-defined task with clear acceptance criteria
3. Use --yes (auto-accept) for known-safe operations
4. Run 2-3 sessions max in parallel (not 5+)
5. Each session works in its own git worktree
6. Morning: review diffs, cherry-pick good work, discard bad
```

Agent Teams (native Claude feature) are more powerful but buggier. Wait for the worktree isolation fix before depending on them for overnight runs.

---

## 5. Goose + Local Models

### Current State (March 2026)

Goose has matured significantly: 30,000+ GitHub stars, 350+ contributors, donated to Linux Foundation's Agentic AI Foundation in December 2025 [23][24].

### LiteLLM Integration

Goose natively supports LiteLLM as a provider [25]:
```bash
export GOOSE_PROVIDER=litellm
export LITELLM_HOST=http://vault.lan:4000
export LITELLM_API_KEY=<ATHANOR_LITELLM_API_KEY>
```

Automatic prompt caching is enabled when using Claude via LiteLLM. Custom headers and timeouts are configurable.

### What Goose Can Do That Others Can't

1. **Recipes:** Reusable YAML workflows with parameters, sub-recipes, retry logic, and extension configuration. Think "saved macros for AI agent behavior" [24].
2. **Headless mode:** First-class `goose run` for cron-scheduled autonomous tasks [26].
3. **MCP ecosystem:** Over 3,000 MCP servers covering developer tools, productivity suites, and specialized services [24].
4. **Multi-IDE integration:** VS Code, Cursor, Windsurf, JetBrains via Agent Client Protocol [24].

### The Blocking Issue: vLLM Tool Calling

**The vLLM tool calling bug remains unresolved.** Goose sees available tools but cannot invoke them when connected to a vLLM endpoint. The same endpoint works correctly with `mcphost`, indicating a Goose-specific issue [27].

**Workarounds that have been reported:**
1. Ensure `--enable-auto-tool-choice` and correct `--tool-call-parser` flags on vLLM [28]
2. Increase `--max-model-len` to 128K (tool definitions consume massive context) [28]
3. Use Candle-vLLM instead of vLLM (different OpenAI-compatible implementation) [29]
4. Route through Ollama instead of direct vLLM (Ollama handles tool calling differently)

### Security Concern

Block's own security team successfully hacked Goose in January 2026 ("Operation Pale Fire"). A poisoned recipe with malicious instructions hidden in invisible Unicode characters tricked both the developer and the AI into running an infostealer. The vulnerability has been patched, but it demonstrates the risk surface of recipe-based automation [24].

### Implication for Athanor

**Do not deploy Goose as the primary autonomous agent until the vLLM tool calling issue is confirmed fixed.** The best path forward:

1. Test Goose with Ollama backend (not vLLM) for a subset of recipes
2. Monitor [Discussion #5914](https://github.com/block/goose/discussions/5914) for resolution
3. If tool calling works via Ollama, deploy Goose for scheduled recipes (nightly code review, security audit, dependency updates)
4. Keep the existing LangGraph coding-agent as the primary autonomous worker

Goose's recipe system is the most mature automation format in the ecosystem. When tool calling works with vLLM, it becomes the top choice for scheduled, unattended tasks.

---

## 6. Multi-Agent Patterns That Ship

### The Failure Mode Reality

The MAST taxonomy (1,600+ traces, peer-reviewed) found that **79% of multi-agent failures are coordination failures, not model quality** [30]. This is already documented in our `2026-03-09-local-ai-architecture-synthesis.md` but bears repeating:

- 40% are system design failures (bad task decomposition, ignored constraints)
- 35% are inter-agent misalignment (context loss, schema mismatches)
- 25% are task verification failures (hallucinated success, premature termination)

### The Five Patterns That Actually Work in Production

From multiple enterprise guides and production case studies [31][32][33]:

**1. Plan-and-Execute (cost winner):**
A capable model creates a strategy that cheaper models execute. Reduces costs by 90% vs. using frontier models everywhere. This is exactly Athanor's architecture: Claude as COO/planner, Qwen3.5 agents as executors.

**2. Hub-and-Spoke (reliability winner):**
Central orchestrator manages all agent interactions. Predictable, debuggable, but potential bottleneck. Best for compliance-heavy or safety-critical workflows. Athanor uses this via the FastAPI orchestrator on FOUNDRY:9000.

**3. Bounded Autonomy (the practical middle ground):**
Agents handle routine execution. Escalation paths are explicit -- if the issue falls outside predefined criteria, the agent pauses and routes to a human with full context. Most organizations deploying in 2026 use this pattern [33].

**4. Specialization over Generalization:**
"Just as monolithic applications gave way to distributed service architectures, single all-purpose agents are being replaced by orchestrated teams of specialized agents" [31]. Athanor's 9 specialized agents are architecturally aligned with this trend.

**5. Human-on-the-Loop (not in-the-loop):**
Agents work autonomously for routine decisions. Humans monitor dashboards and get alerts for unusual patterns. Track: time saved, error reduction, throughput increase [33].

### The Minimal Viable Multi-Agent Setup

Based on production reports, the minimum that produces measurable value [31][33]:

```
1. ONE capable coordinator model (27B+ dense or frontier API)
2. TWO specialized agents (one for your primary workflow, one for review/validation)
3. A task queue (Redis, filesystem locks, or simple database)
4. Structured handoff schema: {status, result, next_agent, context}
5. Circuit breakers: 3 failures in 5 minutes = route to fallback
```

Going from 2 agents to 9 agents increases reliability concerns exponentially. The sweet spot for a single operator is 2-4 agents with clear boundaries, not 9 agents with overlapping responsibilities.

### Surprising Finding

Organizations report **45% faster problem resolution** and **60% more accurate outcomes** with multi-agent vs. single-agent, but **over 40% of agentic AI projects get canceled** due to escalating costs, unclear value, or inadequate risk controls [33][34]. The projects that succeed are the ones that start narrow and validate before scaling.

---

## 7. Continuous Improvement Loops in Practice

### What "The System Improved Itself" Actually Looks Like

The ICLR 2026 Workshop on Recursive Self-Improvement crystallized the state of the art [35]: "Recursive self-improvement is no longer speculative -- it is becoming a concrete systems problem." What's missing is not ambition, but principled methods, system designs, and evaluations that make self-improvement measurable, reliable, and deployable.

Practitioners emphasize [36]: "The key isn't full autonomy -- it's structured loops. The agent logs errors, identifies patterns, creates new skills, but humans still set the boundaries. The improvement is real but bounded."

### What Works in Practice

**1. Promptfoo + CI (eval-driven loop):**
The most commonly implemented pattern. YAML-based eval configs with assertions (contains, regex, LLM-graded, similarity). Run evals on prompt changes automatically in CI. Native vLLM support [37].

**2. LLM-as-Judge scoring:**
Use a capable model to score a cheaper model's outputs. Collect traces from production (LangFuse), identify bottom 10% by score, categorize failure modes, generate improved prompts, test with Promptfoo [38].

**3. The harness pattern:**
"What makes these systems functional is the agent harness -- the infrastructure that wraps around the model and governs how it operates" [36]. The harness manages loops, tool calls, context, and results. Self-improvement means improving the harness, not just the model.

**4. Monthly governance cadence:**
Successful teams implement monthly reviews covering model refresh candidates, quantization retesting, cost reviews, and incident analysis -- treating model serving as SRE-managed infrastructure [39].

### What Doesn't Work

- **Unstructured self-modification:** Agents modifying their own prompts without evaluation gates leads to oscillation or regression.
- **Full autonomy without guardrails:** "Rewards must be logged in real time, adaptations must stay within guardrails, and memories must remain auditable" [35].
- **Optimizing for benchmarks instead of production metrics:** "Benchmark theater" -- celebrating impressive metrics without testing real-world conditions [39].

### Athanor's Self-Improvement Status

Our existing research (`2026-03-07-autonomous-self-improvement.md`) covers this comprehensively with the nightly improvement cycle, Goose recipes, EvoAgentX, and Promptfoo. The key gap is **eval dataset bootstrapping** -- we need 20+ test cases per agent to start the cycle. This is the cold start problem: you need eval data to optimize, but good eval data requires understanding failure modes.

**Practical next step:** Manually curate 20 test cases per agent from LangFuse traces. Start the Promptfoo loop. Don't wait for a perfect eval dataset -- iterate.

---

## 8. The Productivity Cliff

### When Does Complexity Overwhelm Benefit?

The productivity cliff is real and documented from multiple angles [40][41][42][43]:

**Stack Overflow's "Complexity Cliff":** As AI systems grow more complex, organizations hit a wall where added complexity no longer translates to productivity gains. "AI tools make writing code faster but increase the cognitive cost of owning it" [40][42].

**Wharton's "Efficiency Trap":** AI-driven productivity gains paradoxically create perpetual pressure. "Deadlines compress, project volumes expand, and complexity increases while maintaining existing headcount." The efficiency gains become permanently incorporated into performance standards [41].

**MIT's sobering data:** 95% of respondents said their organizations are getting zero return from their AI investments [43].

### Where the Cliff Hits for Homelabs

Based on community reports and practitioner blogs [39][43][44]:

**Anti-patterns that create maintenance burden:**
1. **Model churn addiction:** Swapping models weekly without controlled evaluation. Every swap requires retesting prompts, checking tool calling, verifying quantization quality.
2. **Benchmark hero culture:** One person owns opaque scripts no one else can run. (In a solo homelab, this means "you can't debug your own system 3 months later.")
3. **Vendor absolutism:** Assuming either "all local" or "all cloud." Hybrid is always the answer.
4. **Premature multi-agent scaling:** Going from 1 agent to 9 before validating that 2 work reliably.

**The specific complexity threshold:** Self-hosting AI adds operational burden in proportion to the number of:
- Models being served (each needs monitoring, updates, VRAM management)
- Agents running (each needs prompt maintenance, eval datasets, error handling)
- Integration points (each MCP server, webhook, API is a failure surface)
- Automation loops (each scheduled task can fail silently)

### Simplification Patterns That Work

**1. Standardize one runtime.** Reddit operators converged on either llama.cpp or vLLM -- not both. Maintaining multiple serving engines multiplies operational complexity [39].

**2. Treat context length as a budgeted resource.** Don't default to maximum context. Explicitly justify long-context usage. At 64K context, throughput drops 40% [44].

**3. Consolidate models.** Better to run 2 excellent models than 5 adequate ones. Each model is a maintenance liability (updates, quantization changes, prompt adjustments).

**4. The n8n test:** "Local AI stops being a toy and becomes a workflow tool when n8n connects your LLM to everything: email, webhooks, APIs, databases" [4]. If a capability isn't wired into an actual workflow, it's overhead.

### Athanor-Specific Assessment

Athanor currently runs:
- 2 vLLM instances on FOUNDRY (coordinator + utility)
- 1 vLLM instance on WORKSHOP (worker)
- 1 embedding + 1 reranker on DEV
- 9 specialized agents
- 13 MCP servers
- 42 containers on VAULT

This is past the complexity cliff for a single operator. The question is whether the value justifies the maintenance cost.

**Honest assessment:** The 9 agents are probably 4 more than produce regular value. The top-value agents (General Assistant, Coding, Research, Media) justify their existence. The lower-use agents (Home, Creative, Knowledge, Stash, Data Curator) may be creating maintenance burden without proportional value.

**Recommendation:** Audit agent usage from LangFuse traces. If an agent is invoked fewer than 5 times per week, consider merging its capabilities into a more general agent rather than maintaining it independently.

---

## 9. Tool Use Reliability

### The Hard Numbers

Tool calling reliability is the make-or-break capability for agentic AI. Here's the quantitative data [45][46][47][48]:

**BFCL V4 Leaderboard (Berkeley Function Calling, updated Dec 2025):**

| Model | BFCL Score | Notes |
|-------|-----------|-------|
| Qwen3.5-122B-A10B | **72.2%** | Strongest open-source function-calling model |
| DeepSeek R1 | 93.25% | Very strong (may be BFCL V3, scores not directly comparable) |
| GLM-4.5 (FC) | 70.85% | Strong |
| Claude Opus 4.1 | 70.36% | Leading commercial model on BFCL |
| Claude Sonnet 4 | 70.29% | Close to Opus |
| Qwen3-235B-A22B | 70.8% (BFCL V3) | Flagship open-source |
| GPT-5 | 59.22% | Surprisingly low on BFCL despite other strengths |

**MCPMark Benchmark (More Stringent Real-World Testing):**

| Model | Pass@1 | Pass@4 | Cost/Run |
|-------|--------|--------|----------|
| GPT-5 Medium | 52.6% | 68.5% | $127 |
| Claude Sonnet 4 | 28.1% | 44.9% | $252 |
| Claude Opus 4.1 | 29.9% | -- | $1,165 |
| Qwen-3-Coder | 24.8% | 40.9% | $36 |

MCPMark tasks average **16.2 execution turns and 17.4 tool calls per task**. This reveals a massive gap between single-call accuracy (70%+ on BFCL) and real agentic workflows (25-53% on MCPMark).

### The Compound Reliability Problem

Even 95% single-call accuracy degrades rapidly in chains [48]:
- 5 sequential calls at 95% each: 77% overall success
- 10 sequential calls at 95% each: 60% overall success
- 5 sequential calls at 80% each: 33% overall success

**This is the fundamental constraint on local model agent quality.** A model with 80% tool calling accuracy will fail 2 out of 3 times on a 5-step workflow. This explains why "the model matters more than the framework."

### Model-Specific Failure Patterns

**Qwen3-Coder:** Strong on simple calls (~81.7% live_simple, ~80.9% live_multiple) but drops to ~37.5% on live_parallel tasks. Parallel tool calling is a major weakness [49].

**DeepSeek V3:** Scores 81.5% on agent tests but has systematic failure modes: "When a tool returns an error or truncated output, DeepSeek doesn't accept the result. Instead, it tries alternative commands repeatedly" -- a model-level behavior, not fixable by prompting [50].

**Llama models:** Not among top performers in tool-calling benchmarks. Strengths are in consistent formatting and structured writing, not function calling [46].

### Common Error Types (ToolScan Taxonomy)

The most common tool calling errors [48]:
1. **Insufficient API Calls (IAC):** Model doesn't make enough calls to complete the task (most common)
2. **Hallucinated function names:** Model invents tools that don't exist
3. **Hallucinated argument names:** Model uses wrong parameter names
4. **Missing required parameters:** Model omits mandatory arguments
5. **Wrong parameter types:** String instead of integer, etc.

Models specifically fine-tuned for API calling are less likely to hallucinate function/argument names. Chat-optimized models have higher inaccuracy rates on tool use [48].

### Implication for Athanor

Qwen3.5-27B-FP8 on FOUNDRY is likely in the 70-80% range for single tool calls (extrapolating from Qwen3.5-122B-A10B at 72.2% BFCL V4 and Qwen3-235B at 70.8% BFCL V3). This means:

- **2-3 step workflows:** ~50-60% success rate. Acceptable with retry logic.
- **5+ step workflows:** ~30-40% success rate. Needs circuit breakers and fallbacks.
- **10+ step workflows:** Unreliable without a frontier model in the loop.

**Design implication:** Keep agent workflows short (2-4 tool calls per turn). Use the coordinator model for planning and short action sequences. Don't chain 10 tool calls in a single agent turn.

---

## 10. Most Valuable Daily Agent Workflows

### What People Actually Use Every Day

Cutting through the hype, these are the workflows that produce daily, measurable time savings [51][52][53][54]:

**Tier 1: Clearly worth the effort (25-50% time savings on these specific tasks)**

1. **AI-assisted code editing in IDE.** Continue.dev, Copilot, or Cursor with local model. Autocomplete, inline suggestions, "explain this function." This is the #1 use case for local LLMs in 2026. Zero latency with local inference [1].

2. **Test generation.** After implementing a feature, ask the AI to generate unit tests. "AI excels at generating the tedious test cases developers skip" [54]. Generated tests need review (AI sometimes tests implementation details instead of behavior), but even imperfect test generation saves 30-50% of testing time.

3. **Code review first-pass.** AI catches common issues -- security vulnerabilities, performance anti-patterns, style violations, missing error handling -- before human review. Feeding CI failure logs back to the AI creates a collaborative bug-fixing loop [54].

4. **Email/notification triage.** Local AI categorizes, prioritizes, and drafts responses. UK government study: workers saved 26 minutes per day on routine tasks with AI assistants [52].

5. **Spec-to-code generation.** Start with a `spec.md` file that defines requirements, edge cases, and architecture. Feed it to the AI. "Waterfall in 15 minutes" -- ensures both human and AI understand what's being built [51].

**Tier 2: Worth it if properly automated (significant setup but real ongoing value)**

6. **Documentation generation.** AI generates API docs, README updates, changelog entries from code diffs and commit history.

7. **Dependency audit.** Weekly scan of dependencies for vulnerabilities, updates, and license compliance.

8. **Media management.** Agent-driven media library management (Sonarr/Radarr queries, quality comparisons, organization).

9. **RSS/news intelligence.** Local model processes RSS feeds, extracts key information, summarizes into morning briefing.

10. **Commit message generation.** AI reads diffs and writes descriptive commit messages. Small time saver, but eliminates a friction point.

**Tier 3: Impressive but low daily value (setup cost exceeds time saved for most people)**

11. Complex multi-agent research workflows
12. Autonomous code refactoring without clear specs
13. Creative writing pipelines
14. Home automation AI control (voice + reasoning)
15. Self-improving agent prompt optimization

### The Honest Productivity Assessment

"The people winning with agentic AI right now are not the ones who automated everything -- they are the ones who automated the right small things, learned from the failures, and built from there" [53].

One practitioner's key metric [53]: Went from 45 minutes building a client briefing document to 12 minutes reviewing an agent-prepared draft. "The document is better because time is spent on the part only the human can contribute."

### The Anti-Pattern

"AI tools make writing code faster but increase the cognitive cost of owning it" [42]. A 20,000x SQLite slowdown was found in LLM-written code [42]. "LLMs optimize for plausibility, not correctness."

Addy Osmani's principle [51]: "Never trust AI output blindly. Running tests after each generation. Manual code review. Using a secondary AI model to critique first model's work."

### Workflow Recommendation for Athanor

Based on Athanor's actual usage patterns (9 agents, 6 GPUs, single operator), the highest-ROI workflows to prioritize:

1. **Continue IDE integration with Qwen3.5-27B** -- Zero-latency autocomplete and code chat. Uses existing vLLM endpoint. Daily value.
2. **Automated test generation via coding-agent** -- Scheduled nightly test coverage expansion.
3. **Morning intelligence briefing** -- Miniflux RSS + local model summarization. Already have the pieces (Miniflux MCP, 17 feeds).
4. **Code review on PRs** -- Gitea webhook triggers local model review before human review.
5. **Spec-to-code pipeline** -- Write spec.md, feed to Claude Code/Aider for implementation.

---

## Cross-Cutting Findings

### The Three Laws of Local AI Productivity

From synthesizing all 10 topics, three principles emerge:

**1. The Model Quality Threshold.**
Below ~70% on BFCL (tool calling) or ~70% on Aider polyglot (code editing), autonomous agent work produces more cleanup than value. Qwen3.5-27B-FP8 is right at this threshold. This means it works for well-defined tasks but fails on open-ended autonomous work. Use Claude Code (Anthropic) for anything requiring novel reasoning.

**2. The Complexity Budget.**
Every model served, every agent running, every MCP server connected, and every automation loop is a maintenance liability. The most productive setups are not the ones with the most capabilities -- they're the ones where every component earns its keep. Audit ruthlessly. Merge underused agents. Consolidate models.

**3. The Hybrid Pattern Is Not Optional.**
Zero successful local-AI practitioners run 100% local. The winning pattern is: local models for volume/privacy/cost, cloud APIs for quality/reasoning/complexity. The question is not "local vs. cloud" but "which tasks go where."

### Surprising Findings

1. **MoE models are faster than you think.** Qwen3-30B-A3B generates at 196 tok/s on a 4090 vs. 34 tok/s for a dense 32B. For interactive use, MoE feels dramatically more responsive.

2. **The Aider leaderboard has no Qwen3.5 entries yet.** Despite Qwen3.5's strong SWE-bench (72.4%) and LiveCodeBench (80.7%) scores, nobody has benchmarked it on Aider polyglot. This is a testing gap worth filling.

3. **MCPMark vs. BFCL reveals a 2-3x reliability drop** in real-world agentic tasks compared to single-call benchmarks. Plan for this.

4. **Agent Teams (native Claude) are still buggy.** Worktree isolation doesn't work, sessions crash, teammates stop on errors. claude-squad with single-task prompts is more reliable.

5. **The biggest daily time saver isn't agents -- it's autocomplete.** IDE-integrated local inference with zero latency and zero cost is the highest-ROI use of local GPU VRAM.

---

## Recommendations for Athanor

### Immediate Actions (This Week)

1. **Benchmark Qwen3.5-27B-FP8 on Aider polyglot.** No one has done this yet. Run the benchmark, publish results, fill a gap in community knowledge.

2. **Set up Continue.dev on DEV workstation** pointing at FOUNDRY:8000 (Qwen3.5-27B-FP8). This is the single highest-ROI local AI action.

3. **Audit agent usage from LangFuse.** Which agents get invoked daily? Weekly? Never? Consolidate underused agents.

4. **Create 20 eval test cases per top-3 agent** (General Assistant, Coding, Research). Bootstrap the Promptfoo improvement loop.

### Short-Term (2 Weeks)

5. **Test Goose with Ollama backend** (not vLLM) for a subset of recipes. If tool calling works, deploy for scheduled tasks.

6. **Implement 2-3 step maximum tool calling chains** for local model agents. Redesign any workflow that chains 5+ tool calls into multiple 2-step sub-tasks with validation between.

7. **Morning intelligence briefing pipeline.** Wire Miniflux RSS feeds through local model summarization. Low complexity, daily value.

### Medium-Term (1 Month)

8. **Claude Code hybrid routing.** Configure LiteLLM to route Claude Code overflow to Qwen3.5-27B-FP8. Use for mechanical tasks only; keep Anthropic API for architecture and reasoning.

9. **Code review webhook.** Gitea PR creation triggers local model first-pass review. Results posted as PR comment. Human reviews after.

10. **Agent consolidation.** Merge low-usage agents. Target: 5 active agents (General, Coding, Research, Media, Home) instead of 9.

---

## Sources

[1] [Best GPU for Local LLM Homelab - HomelabSec](https://homelabsec.com/posts/best-gpu-for-local-llm-homelab/)
[2] [Home GPU LLM Leaderboard - Awesome Agents](https://awesomeagents.ai/leaderboards/home-gpu-llm-leaderboard/)
[3] [Best GPUs for Local LLM Inference 2026 - CoreLab](https://corelab.tech/llmgpu/)
[4] [Homelab AI Stack 2026 - DEV Community](https://dev.to/signal-weekly/homelab-ai-stack-2026-what-to-run-and-in-what-order-4cn)
[5] [Claude Code with Anthropic API compatibility - Ollama Blog](https://ollama.com/blog/claude)
[6] [LM Studio + Claude Code](https://lmstudio.ai/blog/claudecode)
[7] [Claude Code Router - GitHub](https://github.com/musistudio/claude-code-router)
[8] [Claude Code + LiteLLM - LiteLLM Docs](https://docs.litellm.ai/docs/tutorials/claude_responses_api)
[9] [Running Claude Code with Local Models via Ollama - HuggingFace Blog](https://huggingface.co/blog/GhostScientist/claude-code-with-local-models)
[10] [Claude Code: connect to a local model when your quota runs out - HN](https://news.ycombinator.com/item?id=46845845)
[11] [vLLM Tool Calling Guide - HuggingFace](https://huggingface.co/joshuaeric/vllm-tool-calling-guide)
[12] [Aider LLM Leaderboards](https://aider.chat/docs/leaderboards/)
[13] [Aider Polyglot - Price Per Token](https://pricepertoken.com/leaderboards/benchmark/aider)
[14] [Best Local Coding Models 2026 - InsiderLLM](https://www.insiderllm.com/guides/best-local-coding-models-2026/)
[15] [claude-squad - GitHub](https://github.com/smtg-ai/claude-squad)
[16] [claude-tmux - GitHub](https://github.com/nielsgroen/claude-tmux)
[17] [Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams)
[18] [muxtree - DEV Community](https://dev.to/b-d055/introducing-muxtree-dead-simple-worktree-tmux-sessions-for-ai-coding-2kf2)
[19] [Building a C Compiler with Parallel Claudes - Anthropic](https://www.anthropic.com/engineering/building-c-compiler)
[20] [You're Not a 10x Developer - Implicator](https://www.implicator.ai/youre-not-a-10x-developer-youre-managing-five-expensive-ai-interns/)
[21] [Bug: claude --tmux --worktree exits immediately - GitHub #27562](https://github.com/anthropics/claude-code/issues/27562)
[22] [Bug: Agent teams don't create agents on own worktree - GitHub #28175](https://github.com/anthropics/claude-code/issues/28175)
[23] [Goose - GitHub](https://github.com/block/goose)
[24] [Goose AI Review 2026 - AI Tool Analysis](https://aitoolanalysis.com/goose-ai-review/)
[25] [Goose Provider Configuration](https://block.github.io/goose/docs/getting-started/providers/)
[26] [Goose Headless Mode](https://block.github.io/goose/docs/tutorials/headless-goose/)
[27] [Goose unable to tool call with vLLM - GitHub Discussion #5914](https://github.com/block/goose/discussions/5914)
[28] [vLLM Tool Calling Docs](https://docs.vllm.ai/en/latest/features/tool_calling/)
[29] [Candle-vLLM + Goose Guide - GitHub](https://github.com/EricLBuehler/candle-vllm/blob/master/docs/goose.md)
[30] [MAST Multi-Agent Failure Taxonomy - arXiv 2503.13657](https://arxiv.org/abs/2503.13657)
[31] [How to Build Multi-Agent Systems 2026 - DEV Community](https://dev.to/eira-wexford/how-to-build-multi-agent-systems-complete-2026-guide-1io6)
[32] [Multi-Agent AI Orchestration - Neomanex](https://neomanex.com/posts/multi-agent-ai-systems-orchestration)
[33] [Agentic AI Trends 2026 - EMA](https://www.ema.co/additional-blogs/addition-blogs/agentic-ai-trends-predictions-2025)
[34] [2026 Will Be the Year of Multi-Agent Systems - AI Agents Directory](https://aiagentsdirectory.com/blog/2026-will-be-the-year-of-multi-agent-systems)
[35] [ICLR 2026 Workshop on Recursive Self-Improvement](https://recursive-workshop.github.io/)
[36] [Closing the Loop: Coding Agents, Telemetry, Self-Improvement - Arize](https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/)
[37] [Promptfoo - GitHub](https://github.com/promptfoo/promptfoo)
[38] [Self-Evolving Agents Cookbook - OpenAI](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining/)
[39] [Local-First AI 2026: What Reddit Operators Got Right - CloudAI](https://cloudai.pt/local-first-ai-in-2026-what-reddit-operators-got-right-and-what-most-teams-still-miss/)
[40] [AI's Complexity Cliff - Computing.co.uk](https://www.computing.co.uk/interview/2025/ai-complexity-cliff-stack-overflow-prashanth-chandrasekar)
[41] [The AI Efficiency Trap - Wharton](https://knowledge.wharton.upenn.edu/article/the-ai-efficiency-trap-when-productivity-tools-create-perpetual-pressure/)
[42] [The AI Engineering Paradox - ModelsLab](https://modelslab.com/blog/llm/ai-engineering-paradox-developers-2026)
[43] [Self-Hosted LLM Guide 2026 - PremAI](https://blog.premai.io/self-hosted-llm-guide-setup-tools-cost-comparison-2026/)
[44] [Consumer Blackwell LLM Benchmarks - arXiv 2601.09527](https://arxiv.org/abs/2601.09527)
[45] [Function Calling and Agentic AI in 2025 - Klavis AI](https://www.klavis.ai/blog/function-calling-and-agentic-ai-in-2025-what-the-latest-benchmarks-tell-us-about-model-performance)
[46] [BFCL V4 - Berkeley](https://gorilla.cs.berkeley.edu/leaderboard.html)
[47] [DeepSeek V3 Function Calling Performance - GitHub Issue #1108](https://github.com/deepseek-ai/DeepSeek-V3/issues/1108)
[48] [ToolScan: Benchmark for Characterizing Errors in Tool-Use LLMs - arXiv](https://arxiv.org/html/2411.13547v2)
[49] [Evaluating Qwen3-Coder Tool Calling - EvalScope](https://evalscope.readthedocs.io/en/latest/best_practice/qwen3_coder.html)
[50] [DeepSeek V3 Agent Evaluation - GitHub Issue #1108](https://github.com/deepseek-ai/DeepSeek-V3/issues/1108)
[51] [My LLM Coding Workflow Going Into 2026 - Addy Osmani](https://addyosmani.com/blog/ai-coding-workflow/)
[52] [Best AI Tools 2026 - Sachin Artani](https://sachinartani.com/blog/best-ai-tools-2026-productivity)
[53] [AI Agents in 2026: I Broke Three Workflows Before One Finally Stuck - Medium](https://medium.com/@taka-alliance-bd/ai-agents-in-2026-i-broke-three-workflows-before-one-finally-stuck-290e87167b24)
[54] [AI Coding Agents 2026 - CodeAgni](https://codeagni.com/blog/ai-coding-agents-2026-the-new-frontier-of-intelligent-development-workflows)

---

Last updated: 2026-03-09
