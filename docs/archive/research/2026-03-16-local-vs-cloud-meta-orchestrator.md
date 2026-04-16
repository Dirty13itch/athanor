# Local vs Cloud Meta-Orchestrator: Should Athanor's Brain Be Local?

**Date:** 2026-03-16
**Status:** Research complete
**Purpose:** Determine whether a local uncensored model (Qwen3.5-27B/35B) should replace or supplement Claude as Athanor's meta-orchestrator. Concrete recommendation, not a pros/cons list.

---

## Context

Athanor's current operating model (VISION.md, ADR-023) is:

```
Shaun (Owner)
  -> Constitution + Policy
    -> Governor (runtime gatekeeper, local Python code)
      -> Meta Strategy Layer (currently: Claude Code = frontier cloud)
        -> Orchestrator control stack (local: routing, tasks, scheduler, workspace, workplanner)
          -> 9 specialist agents (all local, all use local Qwen3.5 models via LiteLLM)
```

The question is about the **Meta Strategy Layer** -- the intelligence that decides *what* to do, *how* to decompose it, and *whether* the output is good enough. Today this is Claude (Opus 4.6 / Sonnet 4.6) via Claude Code and Anthropic API. Could it be a local Qwen3.5 model instead?

The system already has significant local orchestration intelligence:
- `routing.py`: regex-based task classification + model tier routing (entirely local, no LLM needed)
- `governor.py`: trust-based execution gating with presence awareness (local Python code)
- `plan_generator.py`: uses `reasoning` model alias (Qwen3.5-27B-FP8) for plan enhancement
- `work_pipeline.py`: intent mining -> dedup -> plan -> approve -> decompose -> execute (local)
- `scheduler.py`: periodic agent probes (local)
- `workspace.py`: GWT competitive workspace (local)

The actual LLM-dependent orchestration tasks are narrower than they appear.

---

## What Does a Meta-Orchestrator Actually Do?

Decomposing the role into concrete capabilities:

### Tier 1: Routine Operations (80% of orchestration time)
1. **Task routing** -- classify prompt, pick model tier, handle fallbacks
2. **Task decomposition** -- break "organize my media library" into agent-specific subtasks
3. **Plan generation** -- read intent corpus, propose work items with risk assessment
4. **Health monitoring** -- detect failures, trigger retries, escalate
5. **Schedule management** -- run probes, trigger daily work plans

**Current state:** ALL of Tier 1 already runs locally. `routing.py` uses regex patterns, not LLM. `plan_generator.py` already uses the local `reasoning` model for LLM-enhanced plans. Governor gating is pure Python logic.

### Tier 2: Quality Judgment (15% of orchestration time)
6. **Output quality evaluation** -- is this agent output good enough?
7. **Plan critique** -- is this approach sound? What's missing?
8. **Conflict resolution** -- two agents propose contradictory actions
9. **Priority re-ranking** -- given new information, what matters most?

**Current state:** Partially local. Promptfoo evals run local grader. Trust scores track success history. But sophisticated quality judgment (e.g., "this research report is missing the cost analysis") currently depends on Claude's session context.

### Tier 3: Strategic Reasoning (5% of orchestration time)
10. **Architecture decisions** -- which technology to adopt
11. **Novel problem-solving** -- approach is uncertain, multiple valid paths
12. **Cross-domain synthesis** -- connecting insights across agents
13. **Vision alignment** -- does this direction serve VISION.md?

**Current state:** Entirely Claude. This is where frontier model capability matters most.

---

## Capability Comparison: Orchestration-Relevant Benchmarks

### Instruction Following (Critical for orchestration)

| Model | IFEval | IFBench | Notes |
|-------|--------|---------|-------|
| Qwen3.5-27B | 95.0 | -- | Dense, highest per-token reasoning |
| Qwen3.5-122B-A10B | 93.4 | -- | Medium MoE, strong |
| Qwen3.5-397B-A17B | -- | 76.5 | Flagship, highest IFBench |
| Claude Opus 4.6 | -- | 58.0 | Significantly lower IFBench |
| GPT-5 mini | 93.9 | -- | Comparable to 122B |

**Finding:** Qwen3.5 models *lead* Claude on instruction following. This is the most important orchestration capability -- following structured output formats, adhering to constraints, producing valid JSON for tool calls.

### Tool Calling (BFCL-V4)

| Model | BFCL-V4 Overall | Multi-Turn | Agentic | Size |
|-------|-----------------|-----------|---------|------|
| Qwen3.5-122B-A10B | **72.2** | -- | -- | 122B MoE (10B active) |
| Claude Opus 4.6 | ~70.4 | 68.4 | -- | Closed |
| Claude Sonnet 4.0 | 70.3 | -- | -- | Closed |
| Qwen3-32B | 48.7 | 47.9 | 24.1 | 32B dense |
| Qwen3.5-27B | est. 60-65 | -- | -- | 27B dense |

**Finding:** Qwen3.5-122B-A10B matches or beats Claude on BFCL-V4. The 27B lacks published BFCL-V4 scores but Qwen3.5 architecture improvements over Qwen3 suggest significant gains over the Qwen3-32B baseline of 48.7. The gap has narrowed dramatically.

### Multi-Step Planning

| Model | Tau2-Bench | MultiChallenge | BrowseComp |
|-------|-----------|---------------|------------|
| Claude Opus 4.6 | **91.6** | 54.2 | **84.0** |
| Qwen3.5-397B | 86.7 | **67.6** | 69-79 |
| Qwen3.5-27B | -- | -- | -- |

**Finding:** Claude Opus leads on Tau2-Bench (multi-step agent tasks) and BrowseComp (web browsing agents). Qwen3.5 flagship leads on MultiChallenge. For the 27B specifically, no published data -- but the flagship's Tau2-Bench gap (86.7 vs 91.6) suggests Claude has a real edge on the longest, most complex agent chains.

### Coding / SWE-bench (Relevant for coding-agent orchestration)

| Model | SWE-bench Verified |
|-------|-------------------|
| Claude Opus 4.6 | **80.8** |
| Qwen3.5-27B | 72.4 |
| Qwen3.5-35B-A3B | 69.2 |

**Finding:** Claude leads on SWE-bench by 8-11 points. For orchestrating coding tasks specifically, this matters.

### Inference Speed (Orchestration latency budget)

| Model | Deployment | Estimated tok/s | Latency per 200-token response |
|-------|-----------|----------------|-------------------------------|
| Qwen3.5-27B-FP8 | FOUNDRY TP=4 | 30-40 | ~5-7s |
| Qwen3.5-35B-A3B-AWQ | WORKSHOP 5090 | 60-80 | ~2.5-3.5s |
| Claude Sonnet 4.6 | Cloud API | 50-100 | ~2-4s (+ network latency) |
| Claude Opus 4.6 | Cloud API | 30-50 | ~4-7s (+ network latency) |

**Finding:** Local inference is comparable in speed to cloud API when network latency is included. The 35B-A3B MoE on 5090 is particularly fast due to only 3B active parameters.

---

## The Censorship Question

The meta-orchestrator handles these NSFW-adjacent operations:
1. **Creative agent task routing** -- "generate an explicit scene for EoBQ"
2. **Stash agent coordination** -- "organize adult content library by performer"
3. **Media agent requests** -- "find and download [adult content]"
4. **EoBQ game AI orchestration** -- character dialogue, scene generation with adult themes

**Analysis:** The orchestrator does NOT need to generate NSFW content. It needs to:
- Route tasks to agents that generate NSFW content (classification)
- Evaluate whether NSFW output quality is acceptable (quality judgment)
- Plan multi-step workflows involving NSFW content (planning)

Claude handles this acceptably today -- it can classify and route NSFW tasks, it can evaluate quality of NSFW-adjacent outputs without generating them. Where Claude fails:
- It sometimes adds disclaimers or softens language in orchestration contexts
- It cannot evaluate explicit image/video content directly
- Its system prompt must include explicit NSFW permission

A local uncensored model eliminates these friction points entirely. But friction is not the same as inability -- Claude can orchestrate NSFW workflows, it just does so with slight reluctance.

**Verdict:** Censorship is a convenience factor, not a blocker. The orchestrator routes and evaluates, it does not generate. Local uncensored is nicer but not required for orchestration.

---

## The Real Question: Reliability Under Complexity

The benchmark comparison above obscures the most important dimension: **what happens when things go wrong?**

Orchestration is dominated by edge cases:
- An agent produces malformed output -- can the orchestrator recover?
- A plan has a dependency cycle -- can the orchestrator detect it?
- Queue depths spike while a critical task is running -- can the orchestrator reprioritize?
- An intent is ambiguous -- can the orchestrator make a defensible judgment call?

This is where the Tau2-Bench gap (91.6 vs 86.7 for the flagship, likely worse for 27B) manifests as real operational impact. Claude Opus 4.6's advantage is not in following instructions (where Qwen3.5 leads) but in **handling the unexpected** -- the 5% of cases that consume 50% of the debugging time.

Empirically, the 100% pass rate on Athanor's 38-test eval suite (reasoning + fast models) shows local models handle routine well. But those are synthetic, predictable tests. Real orchestration throws edge cases that are hard to benchmark.

---

## Option Analysis

### Option A: Full Local Orchestrator (Qwen3.5-27B as meta-brain)

**How it would work:**
- All orchestration intelligence runs on FOUNDRY's Qwen3.5-27B-FP8 TP=4
- Claude Code becomes an external tool, not the orchestrator
- 24/7 autonomous operation with zero cloud dependency
- Cost: $0/month incremental (hardware already allocated)

**What improves:**
- Always-on: orchestration never waits for cloud API
- Zero cost: no API tokens consumed for orchestration
- No censorship friction: routes NSFW tasks without qualification
- Lower latency for routine operations (no network roundtrip)
- Sovereignty: system operates fully autonomously during internet outages

**What degrades:**
- Strategic reasoning quality drops (Tau2-Bench 86.7 vs 91.6, likely worse for 27B)
- Novel problem-solving (architecture decisions) loses Claude's depth
- Multi-step agent chain reliability decreases for complex workflows
- SWE-bench quality gap (72.4 vs 80.8) affects coding orchestration
- Claude Code's unique capabilities (Agent Teams, parallel sub-agents, 1M context) lost for system development

**Risk:** The orchestrator makes subtly worse decisions that compound over time. Each individual decision looks fine, but the aggregate quality drift is invisible until something breaks badly.

### Option B: Full Cloud Orchestrator (Status Quo, Claude as meta-brain)

**How it would work:**
- Claude Code / Opus API drives all strategic decisions
- Local models execute agent tasks only
- Cloud dependency for all non-routine orchestration

**What's good:**
- Highest quality strategic reasoning
- Best multi-step planning and error recovery
- Claude Code ecosystem (Agent Teams, hooks, MCP) for development
- 1M context window for large-scale reasoning

**What's bad:**
- $20-200/month ongoing cost for orchestration intelligence
- Internet dependency for strategic decisions
- Rate limiting during heavy usage
- Cannot run 24/7 autonomously (API quotas, network interruptions)
- Slight censorship friction on NSFW-adjacent orchestration
- Cloud provider can change pricing, terms, or capabilities

**Risk:** System stops working when cloud is unavailable. Shaun's sovereignty goal (VISION.md #4) is compromised.

### Option C: Layered Hybrid (Local for routine, Cloud for strategic)

**How it would work:**
- **Governor + routing + scheduling + workspace** remain local Python (no change)
- **Plan generation + task decomposition** use local `reasoning` model (already happening)
- **Quality evaluation + output scoring** use local `reasoning` model (new)
- **Strategic planning + architecture + novel reasoning** escalate to cloud Claude
- **24/7 autonomous loop** runs entirely on local intelligence
- **Shaun's interactive sessions** use Claude Code for system development

**Escalation triggers (local -> cloud):**
- Task involves >3 agents coordinating simultaneously
- Plan risk is "high" and estimated duration >2 hours
- Quality evaluation confidence <0.6
- Explicit `prefer_quality: true` flag
- Architecture or design decisions
- Coding tasks with >5 file changes

**What improves over status quo:**
- 24/7 autonomous operation without cloud dependency
- Zero cost for 80%+ of orchestration decisions
- No censorship friction on routine NSFW routing
- Faster response for routine operations
- Graceful degradation: system keeps working during cloud outages

**What improves over full-local:**
- Strategic reasoning retains Claude-tier quality
- Complex multi-agent chains get frontier model oversight
- Architecture decisions benefit from 1M context + Agent Teams
- Novel problems get the best available reasoning

**What's new:**
- Escalation logic must be built and tuned
- Two code paths for orchestration (adds complexity)
- Must track which decisions were local vs cloud (observability)

---

## Recommendation

**Option C: Layered Hybrid.** But with an important caveat about what this actually means in practice.

### The system is already 90% there.

Look at what currently runs locally:
- `routing.py` -- task classification and model selection (regex, no LLM)
- `governor.py` -- execution gating with trust scores and presence (Python logic)
- `plan_generator.py` -- already calls local `reasoning` model for plan enhancement
- `work_pipeline.py` -- full intent->plan->task pipeline (local)
- `scheduler.py` -- periodic agent probes (local)
- `workspace.py` -- GWT competitive workspace (local)

The only orchestration function that *actually* depends on Claude is:
1. **Shaun's interactive sessions** -- system development, architecture decisions, complex debugging
2. **Quality judgment on novel outputs** -- when the eval suite can't score it
3. **Cross-domain synthesis** -- connecting insights that span multiple agent domains

These are real, important functions. But they are Tier 3 (5% of orchestration time). The system already orchestrates itself locally for 95% of operations.

### What to build

The hybrid is not a new system. It is three additions to the existing infrastructure:

1. **Quality scorer using local model** -- `quality_judge.py` that runs the local `reasoning` model to evaluate agent outputs with a rubric. Falls back to cloud when confidence is low. This replaces the implicit dependency on Claude reviewing outputs during Shaun's sessions.

2. **Escalation classifier** -- extend `routing.py` with an `escalation_needed()` function that identifies when a task exceeds local orchestration capability. Triggers: high risk, multi-agent coordination, architecture decisions, low-confidence quality scores.

3. **Autonomous night mode** -- when presence is "asleep" or "away", the system operates fully on local intelligence. Plans are generated, tasks are executed, quality is scored, all without cloud. Results queue for Shaun's morning review. This already mostly works via the governor's presence-based autonomy.

### What NOT to build

- Do not replace Claude Code as the development tool. There is no local equivalent to Claude Code's Agent Teams, 1M context, and deep codebase understanding. Shaun's development sessions are the highest-value use of cloud intelligence.
- Do not build an "AI orchestrator supervisor" that uses LLM to manage the orchestrator. The governor is deterministic Python code. It should stay that way. LLM judgment is for content decisions, not control flow.
- Do not route all orchestration through a single LLM call. The current pattern (regex classification + Python gating + LLM enhancement) is faster, more reliable, and more debuggable than "send everything to the orchestrator LLM."

### Cost-benefit summary

| Dimension | Full Local | Full Cloud | Hybrid (Recommended) |
|-----------|-----------|-----------|---------------------|
| Monthly cost | $0 | $20-200 | $10-50 (90% reduction) |
| 24/7 autonomy | Yes | No | Yes |
| Strategic quality | Lower | Highest | High (cloud for hard stuff) |
| Censorship friction | None | Slight | None (local handles NSFW) |
| Cloud dependency | None | Full | Minimal (graceful degradation) |
| Implementation effort | Low (already there) | None (status quo) | Low (3 modules) |
| VISION.md alignment | Strong (#4 sovereignty) | Weak (#4 compromised) | Strong (all priorities) |

### The decisive argument

VISION.md says: "Cloud AI (Claude Code) handles architecture, reasoning, coordination, and novel problem-solving. Local AI (LiteLLM-routed inference plus 9 agents) handles always-on operations, uncensored inference, private data, and autonomous task execution."

The hybrid approach is not a compromise. It is the operating model VISION.md already describes. The gap is not architectural -- it is that the quality scoring and escalation classification modules have not been built yet. Those are small, well-defined engineering tasks.

The question "should the orchestrator be local?" has a false premise. The orchestrator is *already* mostly local. The right question is: "what are the remaining cloud dependencies in the orchestration path, and which of them can be moved local without quality loss?" The answer is: routine quality scoring and autonomous night-mode operation. Everything else should stay where it is.

---

## Implementation Priority

1. **quality_judge.py** (2-3 hours) -- local model scores agent outputs on a 1-5 rubric. Stores scores in Redis. Flags low-confidence results for cloud review.
2. **Escalation classifier** (1-2 hours) -- extend `routing.py` with `needs_escalation()`. Pattern match + complexity heuristics.
3. **Autonomous night mode** (1-2 hours) -- governor presence integration. When "asleep", force `prefer_local: True` on all routing, accumulate results for morning digest.

Total: 4-7 hours of engineering. No architecture changes. No new services. No new dependencies.

---

## Sources

- [Qwen3.5-27B HuggingFace Model Card](https://huggingface.co/Qwen/Qwen3.5-27B)
- [Qwen3.5 Medium Series Benchmarks](https://www.digitalapplied.com/blog/qwen-3-5-medium-model-series-benchmarks-pricing-guide)
- [BFCL V4 Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [Claude Opus 4.6 Deep Dive](https://claude5.com/news/claude-opus-4-6-review-benchmarks-features-2026)
- [Claude Opus 4.6 — Anthropic](https://www.anthropic.com/claude/opus)
- [Qwen3.5 Architecture & Benchmarks (DataCamp)](https://www.datacamp.com/blog/qwen3-5)
- [Qwen3.5 Complete Guide (Techie007)](https://techie007.substack.com/p/qwen-35-the-complete-guide-benchmarks)
- [Artificial Analysis: Qwen3.5-27B vs Claude Sonnet 4.6](https://artificialanalysis.ai/models/comparisons/qwen3-5-27b-vs-claude-sonnet-4-6)
- [VentureBeat: Qwen3.5 Medium Models](https://venturebeat.com/technology/alibabas-new-open-source-qwen3-5-medium-models-offer-sonnet-4-5-performance)
- [GPT-5.4 vs Claude Opus 4.6 (DataCamp)](https://www.datacamp.com/blog/gpt-5-4-vs-claude-opus-4-6)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Athanor ADR-017 (GWT Meta-Orchestrator)
- Athanor ADR-021 (Autonomous Operating Loop)
- Athanor ADR-022 (Subscription Control Layer)
- Athanor ADR-023 (Command Hierarchy and Governance)
- Athanor `routing.py`, `governor.py`, `plan_generator.py`, `work_pipeline.py` (live code review)
- Athanor eval suite: 38 tests, 100% pass rate on local models (session 60o)

Last updated: 2026-03-16
