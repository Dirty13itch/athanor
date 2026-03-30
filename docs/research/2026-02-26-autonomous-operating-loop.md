# The Autonomous Operating Loop: Intent Mining, Human-in-the-Loop Feedback, and the Self-Feeding Furnace

**Date:** 2026-02-26
**Status:** Research complete -- ready for ADR
**Scope:** Comprehensive design for Athanor's autonomous operating model with graduated human-in-the-loop feedback
**Supports:** Intelligence Layer 3 (Pattern Recognition), Intelligence Layer 4 (Self-Optimization), BUILD-MANIFEST Tier 10+
**Depends on:** ADR-017 (Meta-Orchestrator), ADR-018 (GPU Orchestration), ADR-019 (Command Center), Intelligence Layers Design, Agent Contracts
**Synthesizes:** 7 existing research documents + 15 external sources + full analysis of existing Athanor codebase

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Already Exists](#2-what-already-exists)
3. [Intent Mining and Work Generation](#3-intent-mining-and-work-generation)
4. [Human-in-the-Loop Feedback Mechanisms](#4-human-in-the-loop-feedback-mechanisms)
5. [Trust and Autonomy Escalation](#5-trust-and-autonomy-escalation)
6. [Feedback Loop Architecture](#6-feedback-loop-architecture)
7. [The Self-Feeding Furnace Pattern](#7-the-self-feeding-furnace-pattern)
8. [Interaction Design for Human-in-the-Loop](#8-interaction-design-for-human-in-the-loop)
9. [Recommended Architecture](#9-recommended-architecture)
10. [Implementation Sequence](#10-implementation-sequence)
11. [Open Questions for Shaun](#11-open-questions-for-shaun)
12. [Sources](#12-sources)

---

## 1. Executive Summary

Athanor has all the infrastructure for autonomous operation but lacks the intelligence to decide **what** to do autonomously. The 8 agents, task engine, scheduler, GWT workspace, goals API, trust scores, context injection, and feedback storage are all deployed. What is missing is the **work planner** -- the system that reads documented intent, generates concrete tasks, routes them to agents, collects feedback, and uses that feedback to improve future work generation.

This document designs that system across seven dimensions: how to mine intent from documents, how to collect human feedback at every effort level, how to build graduated trust, how to close the feedback loop technically, how the self-feeding pattern works without runaway, what the UI looks like, and how it all maps to what already exists in Athanor.

The central design principle: **the system should require zero daily effort from Shaun to operate, but give him powerful steering controls when he chooses to engage.** The absence of correction is a positive signal. Explicit feedback is always available but never required.

Three key architectural decisions emerge:

1. **The Work Planner** runs as a Claude Code session (not a local agent), reading the full intent corpus and generating agent tasks. It runs on a cadence (daily at 6:00 AM, before the morning digest) and on-demand when intent documents change.

2. **Feedback is collected at five effort levels**, from zero-effort implicit signals (what Shaun looks at, ignores, undoes) through lightweight binary feedback (thumbs up/down) to directed natural language steering. The system weight-decays feedback over time and injects diversity to prevent filter-bubble convergence.

3. **Trust is a per-agent, per-action-type score** that starts at Level C (propose and wait) and graduates to Level A (act and log) based on track record. Regression is automatic after corrections. The daily intervention rate is the single most important metric.

---

## 2. What Already Exists

Before designing anything new, here is what Athanor already has that this system can leverage directly.

### 2.1 Infrastructure Already Deployed

| Component | Location | Status | Relevant Capability |
|-----------|----------|--------|---------------------|
| **Task Engine** | Node 1:9000 | Live | `POST /v1/tasks`, priority queue, step logging, max 2 concurrent |
| **Proactive Scheduler** | Node 1:9000 | Live | Per-agent intervals (30min/15min/5min), asyncio background loop |
| **Goals API** | Node 1:9000 | Live | CRUD goals in Redis, goals injected into agent context via `context.py` |
| **Trust Scores** | Node 1:9000 | Live | Per-agent scores (0.0-1.0) from feedback + escalation history |
| **Feedback Storage** | Node 1:9000 | Live | Thumbs up/down stored in Qdrant preferences + Redis counters |
| **Context Injection** | Node 1:9000 | Live | 1 embedding + 3 parallel Qdrant queries + goals, ~30-50ms |
| **Escalation Protocol** | Node 1:9000 | Live | 3-tier (act/notify/ask), per-agent thresholds |
| **GWT Workspace** | Node 1:9000 | Live | Redis-backed, 1Hz competition, capacity 7, pub/sub broadcast |
| **Activity Logging** | Node 1:9000 | Live | Fire-and-forget to Qdrant `activity` collection |
| **Knowledge Base** | Node 1:6333 | Live | 2220 vectors in Qdrant, 30+ Neo4j nodes |
| **Preference Store** | Node 1:6333 | Live | Qdrant `preferences` collection, 17 profile points |
| **Daily Digest** | Scheduler | Live | 6:55 AM, compiles overnight summary via general-assistant |
| **Command Center** | Node 2:3001 | Live | PWA, 17 pages, 5 lenses, SSE, generative UI, crew bar |
| **Push Notifications** | Node 2:3001 | Live (infra) | VAPID keys deployed, SW handler, `/api/push` endpoint |
| **MCP Bridge** | DEV | Live | 14 tools connecting Claude Code to local agents |
| **Rubber-stamp Detection** | Node 1:9000 | Live | Warns if >20 approvals with 0 rejections |

### 2.2 Intent Corpus Already Available

These documents encode Shaun's intent at different levels of specificity:

| Document | Path | Intent Level | Content |
|----------|------|-------------|---------|
| **VISION.md** | `docs/VISION.md` | Strategic | Philosophy, non-negotiables, what Athanor is/isn't |
| **STATUS + Live Backlog** | `STATUS.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` | Tactical | Current-state summary and ranked execution backlog |
| **TODO.md** | `memory/TODO.md` | Operational | Prioritized task list (P0/P1/P2/P3), blocked items, research questions |
| **Profile** | `memory/profile.md` | Personal | Identity, repos, starred repos, tools, work patterns, interests |
| **Agent Contracts** | `docs/design/agent-contracts.md` | Behavioral | Per-agent: purpose, tools, escalation rules, learning signals |
| **Intelligence Layers** | `docs/design/intelligence-layers.md` | Architectural | Progression from reactive to self-optimizing |
| **Command Center Design** | `docs/design/command-center.md` | UI/UX | Interface design, HITL framework, feedback mechanisms |
| **ADRs (19 total)** | `docs/decisions/ADR-*.md` | Decision | Every technology choice with rationale |
| **Research (57 files)** | `docs/research/*.md` | Informational | Deep research across all domains |
| **GitHub Starred Repos** | `memory/profile.md` | Interest signal | 50+ starred repos organized by interest |
| **SYSTEM-SPEC.md** | `docs/SYSTEM-SPEC.md` | Operational | Complete system specification |
| **SERVICES.md** | `docs/SERVICES.md` | Inventory | Live service inventory |

### 2.3 What is Missing

| Gap | What It Blocks |
|-----|---------------|
| **Work Planner** | No system reads intent docs and generates agent tasks |
| **Implicit Feedback Tracking** | Command Center doesn't track what Shaun looks at, ignores, or taps |
| **Feedback-to-Behavior Propagation** | Feedback is stored but doesn't change agent behavior beyond context injection |
| **Pattern Detection** | No jobs analyze activity logs for recurring patterns |
| **Conversation History** | `conversations` Qdrant collection exists but isn't populated |
| **Progressive Trust Automation** | Trust scores exist but don't automatically adjust autonomy levels |
| **Notification Budget Enforcement** | No daily cap on notifications per agent |
| **Work Feeds Work** | Completed tasks don't generate follow-up tasks |
| **Diversity Injection** | No mechanism to prevent recommendations from converging |

---

## 3. Intent Mining and Work Generation

### 3.1 How Autonomous Agent Systems Decompose Goals

The research on autonomous agent systems reveals three dominant patterns for goal-to-task decomposition:

**Pattern A: The BabyAGI Loop (Execution-Creation-Prioritization)**

BabyAGI, created by Yohei Nakajima (2023), implements the simplest viable autonomous loop. It uses three "agents" (all just different prompt templates for the same LLM):

1. **Execution agent** -- executes the current highest-priority task
2. **Creation agent** -- generates new tasks based on the execution result and the overall objective
3. **Prioritization agent** -- reorders the task queue based on the objective

The key insight is that task generation is an LLM call, not a rules engine. The creation agent receives the objective, the completed task, and its result, then generates 0-N new tasks. Prioritization is also an LLM call that reorders based on the objective. This is simple enough for one-person maintenance while being flexible enough to handle diverse objectives.

Source: [IBM - What is BabyAGI](https://www.ibm.com/think/topics/babyagi), [BabyAGI.org](https://babyagi.org/)

**Pattern B: AutoGPT Hierarchical Decomposition**

AutoGPT takes a high-level objective (e.g., "increase website traffic by 30%") and creates a hierarchical task structure, breaking it into subtasks like content creation, SEO optimization, social media campaigns, and performance analysis. Each subtask can be further decomposed. The hierarchy maps to the organizational structure: top-level tasks map to strategic goals, mid-level to tactical plans, leaf-level to executable agent actions.

Source: [Built In - AutoGPT Explained](https://builtin.com/artificial-intelligence/autogpt), [Axis Intelligence - AutoGPT Deep Dive](https://axis-intelligence.com/autogpt-deep-dive-use-cases-best-practices/)

**Pattern C: OKR-Agent (Objectives and Key Results)**

The academic OKR-Agent framework applies OKR methodology to AI agent systems. It uses "hierarchical OKR generation" to decompose objectives into sub-objectives, then assigns agents to key results. Each agent "elaborates on designated tasks and decomposes them as necessary, operating recursively and hierarchically." This maps naturally to Athanor's goal-agent structure.

Source: [Agents Meet OKR, arXiv:2311.16542](https://arxiv.org/abs/2311.16542)

**What Went Wrong with Early Autonomous Agents:**

AutoGPT's open-ended autonomy often results in "unreliable execution, runaway loops, and high token costs." A single unattended run can rack up hundreds of dollars in token usage if the agent doesn't stop itself. The production fix is iteration caps, step boundaries, human-in-the-loop checkpoints, and cost awareness.

Source: [ZenML - AutoGPT Alternatives](https://www.zenml.io/blog/autogpt-alternatives), [LateNode - Agentic Workflows](https://latenode.com/blog/ai-agents-autonomous-systems/ai-agent-fundamentals-architecture/agentic-workflows-transforming-automation-with-autonomous-ai-agents)

### 3.2 Recommended Work Planner Architecture for Athanor

The Work Planner is the missing piece. It reads the intent corpus and generates concrete agent tasks. Here is the recommended design:

**Who runs the Work Planner?** Claude Code (COO), not a local agent. The reason: work planning requires cross-document reasoning, understanding of the full system architecture, access to all intent documents, and judgment about what is valuable versus busy-work. Qwen3-32B-AWQ can execute tasks but lacks the reasoning depth to plan work strategically. Claude Code already has this role (COO/Meta Orchestrator) and has MCP bridge access to submit tasks.

**When does it run?**
- **Daily at 6:00 AM** (before the 6:55 AM digest): Reads the full intent corpus, generates the day's work plan, submits tasks to the queue.
- **On-demand**: When Shaun updates VISION.md, TODO.md, or goals, or when he says "replan."
- **After significant events**: When a major task completes (new ADR written, new service deployed), the planner re-evaluates whether downstream tasks are now unblocked.

**What does it read?** The full intent corpus (Section 2.2), with a priority weighting:

| Source | Weight | Signal |
|--------|--------|--------|
| Active Goals (Redis) | Highest | Explicit current intent |
| TODO.md P0 items | High | Explicit next actions |
| Recent feedback (thumbs down) | High | Things to fix or stop |
| TODO.md P1 items | Medium | Short-term backlog |
| BUILD-MANIFEST unblocked items | Medium | Roadmap execution |
| Profile starred repos | Low | Interest signals |
| VISION.md | Context | Strategic alignment filter |
| Agent contracts | Context | Capability mapping |

**How does it generate tasks?** A three-step LLM pipeline:

```
Step 1: Intent Extraction
  Input: Full intent corpus
  Output: Ranked list of 10-20 intents with priority, domain, and rationale
  Filter: Only actionable intents (skip "aspirational" items, blocked items)

Step 2: Task Decomposition
  Input: Top 5-8 intents + agent capabilities (from contracts)
  Output: Concrete tasks with: agent, prompt, priority, dependencies, estimated_duration
  Filter: Max 10 tasks per day (prevent overwhelm)
  Constraint: Each task must be completable by a single agent in one execution

Step 3: Validation and Submission
  Input: Generated tasks + current system state (running tasks, GPU load, queue depth)
  Output: Submitted tasks, deferred tasks (with reason), skipped tasks (with reason)
  Filter: Don't submit if queue > 5, don't submit GPU-intensive tasks during active use
```

**The 10-task daily cap** is critical. BabyAGI and AutoGPT fail because they generate unlimited tasks. Athanor's constraint: max 10 generated tasks per daily planning cycle, max 2 concurrent execution. This is a homelab with one operator, not an enterprise workflow engine.

### 3.3 Priority Inference from Implicit Signals

Beyond explicit prioritization in TODO.md, the system infers priority from:

| Signal | Priority Boost | Source |
|--------|---------------|--------|
| Mentioned in last 3 conversations with Shaun | +2 | Activity log |
| Referenced in recent goals | +3 | Goals API |
| Has a thumbs-down on related past output | +2 | Feedback store |
| Item has been in TODO.md for >7 days | +1 (urgency decay) | Git blame |
| Related to a starred GitHub repo | +1 | Profile |
| Mentioned in VISION.md | +1 (alignment) | Static analysis |
| Has dependencies on recently completed work | +2 (momentum) | Task history |
| Related to currently idle infrastructure | +1 | GPU orchestrator |

### 3.4 Mapping Intents to Agents

The Work Planner must map each intent to the correct agent. This mapping uses the agent contracts:

| Domain Keywords | Agent | Confidence |
|-----------------|-------|-----------|
| media, show, movie, Plex, Sonarr, Radarr, download | media-agent | High |
| lights, temperature, thermostat, automation, Home Assistant | home-agent | High |
| research, compare, evaluate, benchmark, find out | research-agent | High |
| image, video, generate, creative, ComfyUI, Flux | creative-agent | High |
| knowledge, document, ADR, what was decided | knowledge-agent | High |
| code, implement, refactor, test, debug | coding-agent | High |
| Stash, library, tag, organize, content | stash-agent | High |
| health check, status, GPU, service, deploy | general-assistant | Medium |
| Multiple domains, unclear mapping | general-assistant (with delegation) | Low |

When confidence is low, the general-assistant receives the task with delegation tools enabled, allowing it to route to the appropriate specialist.

---

## 4. Human-in-the-Loop Feedback Mechanisms

### 4.1 The Five Levels of Feedback Effort

Research across 10 domains (documented in `docs/research/2026-02-25-human-in-the-loop-patterns.md`) consistently shows that feedback quality and sustainability are inversely related to effort. The system should collect feedback at all five levels simultaneously, weighting by effort inversely:

| Level | Effort | Mechanism | Sustainability | Signal Quality | Weight |
|-------|--------|-----------|---------------|----------------|--------|
| **0: Passive** | Zero | Behavioral observation | Infinite | Medium | 1.0 |
| **1: Micro** | 0.5s | Thumbs up/down, swipe | Very high | Medium | 0.8 |
| **2: Quick** | 2-5s | Star/bookmark, "more/less of this" | High | High | 0.7 |
| **3: Directed** | 10-30s | Natural language steering, goal setting | Medium | Very high | 0.5 |
| **4: Deliberate** | 1-5min | Pairwise comparison, rubric evaluation | Low | Highest | 0.3 |

**The weight column** reflects the sustainability-adjusted signal value. Passive feedback at 1.0 means "always collect, always use." Deliberate feedback at 0.3 means "valuable when available but don't depend on it."

### 4.2 Level 0: Passive Feedback (Zero Effort)

This is the most important layer. Netflix gives 10x more weight to watched content than explicit ratings. Spotify processes "almost half a trillion data events daily" from implicit behavior. The absence of correction is a positive signal.

Source: [Netflix Recommendation Analysis](https://marketingino.com/the-netflix-recommendation-algorithm-how-personalization-drives-80-of-viewer-engagement/), [Spotify Complete Guide 2025](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide)

**What Athanor can track passively from the Command Center:**

| Signal | What It Means | Collection Method |
|--------|--------------|-------------------|
| **Page views** | What Shaun looks at | Client-side analytics (page visit events) |
| **Dwell time** | How long he looks | Time-on-page measurement |
| **Lens selection** | What mode he's in | Lens context state |
| **Agent chat frequency** | Which agents he uses | Chat completion logs (already logged to activity) |
| **Task approval latency** | How quickly he approves | Timestamp delta on escalation resolution |
| **Notification tap rate** | Which notifications matter | Push notification click tracking |
| **Notification ignore rate** | Which notifications are noise | Inverse of tap rate, time-windowed |
| **Override frequency** | When he corrects agent actions | Home Agent manual adjustments, Media Agent search-then-add |
| **Time-of-day patterns** | When he's active | Session timestamps |
| **Scroll depth** | How much detail he reads | Client-side scroll tracking on stream page |

**Implementation:** Add a lightweight analytics event system to the Command Center. Every meaningful user action emits a JSON event to `/api/feedback/implicit`:

```typescript
interface ImplicitEvent {
  type: 'page_view' | 'dwell' | 'tap' | 'ignore' | 'override' | 'scroll' | 'lens_change';
  page: string;
  agent?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
  timestamp: number;
}
```

Events are batched client-side (every 30s or on page unload) and stored in a new `implicit_feedback` Qdrant collection. This costs nothing in user effort and provides the richest behavioral signal.

### 4.3 Level 1: Micro Feedback (0.5 seconds)

Binary feedback on agent outputs. Already partially deployed (thumbs up/down in `goals.py`), but needs to be embedded inline in every agent output across the Command Center.

**Existing implementation** (`/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/goals.py`, lines 67-107):
- Stores feedback in Qdrant preferences collection
- Updates Redis counters for trust score computation
- Content includes message and response summaries

**What needs to change:**
- Every agent response in the Stream, Chat, and Activity pages should have inline thumbs up/down icons
- Every push notification should have "Helpful" / "Not helpful" action buttons
- Every generative UI component should have a micro-feedback affordance
- Swipe gestures on mobile: swipe right on a stream entry = "good", swipe left = "not helpful"

**Research support for binary over granular:** Netflix's switch from 5-star to binary thumbs improved recommendation accuracy by 200%. The simplest possible explicit signal is better than a complex one nobody uses.

Source: [Netflix Two Thumbs Up, Variety 2022](https://variety.com/2022/digital/news/netflix-two-thumbs-up-ratings-1235228641/)

### 4.4 Level 2: Quick Feedback (2-5 seconds)

Contextual feedback that goes beyond binary but stays low-effort:

| Mechanism | Implementation | Signal Produced |
|-----------|---------------|-----------------|
| **"More of this"** button | On any agent output | Positive preference with category tagging |
| **"Less of this"** button | On any agent output | Negative preference with category tagging |
| **Star/bookmark** | On stream entries | "This was particularly valuable" (stronger than thumbs up) |
| **Priority nudge** | Drag-to-reorder on task list | "This matters more than that" |
| **Quick dismiss** | Swipe-to-dismiss on notifications | "I saw this and it's not worth my time" |
| **"Stop doing this"** button | On proactive agent outputs | Hard negative signal -- agent should not repeat this type of action |

**The "stop doing this" mechanism is critical.** Research shows that negative explicit feedback is rare and powerful. Netflix observes that "if people don't like a show, they generally just stop watching it." When someone takes the effort to explicitly say "stop," the system should treat it as a very strong signal.

Source: [Netflix algorithm analysis](https://marketingino.com/the-netflix-recommendation-algorithm-how-personalization-drives-80-of-viewer-engagement/)

### 4.5 Level 3: Directed Feedback (10-30 seconds)

Natural language steering. Already partially deployed via the Goals API (`/v1/goals`).

**Existing implementation** (`/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/goals.py`, lines 143-203):
- CRUD goals in Redis
- Goals injected into agent context via `context.py` (lines 316-321)
- Goals have agent scope (agent-specific or global) and priority

**What needs to evolve:**

1. **Conversational steering** (like Spotify's Prompted Playlists, December 2025): Instead of formal goal creation, Shaun says something like "Focus on media quality this week" in the chat, and the system translates that to a goal with appropriate scope and priority. The general-assistant should recognize steering intent and route it to the Goals API.

Source: [Spotify Prompted Playlists](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)

2. **Goal suggestion**: Agents should be able to propose goal modifications based on observed patterns. "I notice you always override 68F to 70F. Should I update the target?" This is the Nest thermostat pattern applied to the goal system.

Source: [Google Nest - How thermostats learn](https://support.google.com/googlenest/answer/9247510)

3. **Constraint specification**: "Never add shows with less than 7.0 IMDB rating." "Always use 4K quality when available." These are permanent steering rules, not temporary goals. They should be stored differently (as hard constraints, not soft preferences) and enforced at the agent level before action.

### 4.6 Level 4: Deliberate Feedback (1-5 minutes)

Reserved for high-stakes calibration events. The system should request this rarely and only when it genuinely helps.

| Mechanism | When to Use | Implementation |
|-----------|------------|---------------|
| **Pairwise comparison** | "Which response was better?" | Show two agent outputs side by side, ask user to pick |
| **Weekly review** | Sunday morning digest | Summary of week's agent activity with "what to change" prompts |
| **Goal-level assessment** | Monthly or when goals feel stale | Review active goals, mark as achieved/irrelevant/needs-update |
| **Trust calibration** | After an agent makes a notable mistake | "Should this agent have more or less autonomy?" slider |

**Research on pairwise comparison** (from RLHF literature): Pairwise comparison is "generally easier and more reliable for humans to make consistently" than absolute scoring. Inter-annotator agreement is significantly higher for pairwise versus Likert scales.

Source: [Uni-RLHF, arXiv:2402.02423](https://arxiv.org/abs/2402.02423)

### 4.7 Mobile-First Feedback Design

Shaun's primary interaction is via phone (Command Center PWA). Mobile feedback must be optimized for one-handed use:

| Pattern | Gesture | Research Basis |
|---------|---------|---------------|
| Thumbs up/down | Tap (44px touch targets) | Standard mobile pattern |
| "More of this" / "Less" | Long-press reveals contextual menu | iOS/Android convention |
| Quick dismiss | Swipe left to dismiss | Tinder/email pattern, already understood |
| Approve/Reject | Notification action buttons | Push notification standard |
| Priority ordering | Drag handle on task cards | Todoist/Linear pattern |
| Natural language | Voice input via existing STT pipeline | "Athanor, focus on creative work tonight" |

**Three-level success feedback hierarchy** (from 2026 mobile design research):
- Level 1: Inline checkmark with 200ms animation, auto-dismiss after 2s
- Level 2: Bottom snackbar for 4s with swipe-to-dismiss
- Level 3: Modal only for important/irreversible actions

Source: [Mobile App Design Trends 2026](https://uxpilot.ai/blogs/mobile-app-design-trends)

### 4.8 Ambient Awareness (What Shaun Sees Without Checking)

The goal: Shaun should know what the system is doing without opening the app. Mechanisms:

| Mechanism | Content | Cadence | Effort |
|-----------|---------|---------|--------|
| **Morning push** | Daily digest summary | 6:55 AM | Zero (reads notification) |
| **Escalation push** | "Agent needs approval" with action buttons | Real-time | 2-5s (tap approve/reject) |
| **Weekly email/push** | Week in review, goal assessment, trust trends | Sunday 9 AM | 1-5 min reading |
| **PWA badge** | Unread count on home screen icon | Real-time | Zero (glance) |
| **Crew bar glow** | Agent status visible at all times in Command Center | Continuous | Zero (peripheral vision) |
| **System warmth** | Background color temperature reflects system activity | Continuous | Zero (ambient) |

**The "tea kettle principle"** (Amber Case, Calm Technology): The system is silent when working correctly. It only demands attention when something needs human intervention. The Command Center's ambient design (warm glow, agent constellation, system warmth CSS variable) already embodies this.

Source: [Calm Technology Principles](https://www.caseorganic.com/post/principles-of-calm-technology)

---

## 5. Trust and Autonomy Escalation

### 5.1 Existing Trust Infrastructure

Athanor already has trust scores per agent, computed from feedback ratio and escalation resolution history (see `goals.py` lines 209-295). The `compute_trust_scores()` function:

- Weights feedback 60% / escalation 40%
- Applies a confidence penalty for low sample counts (regress toward 0.5 with fewer than 20 samples)
- Assigns letter grades (A/B/C/D)
- Detects rubber-stamping (>20 approvals, 0 rejections)

What it **does not** do is automatically adjust autonomy levels based on trust scores.

### 5.2 Frameworks for Graduated Autonomy

**Sheridan-Verplanck 10-Level Scale (1978):**

The foundational framework for human-automation interaction. Levels 1-10 range from "human does everything" to "computer acts entirely autonomously." The critical insight: each of four automation functions (information acquisition, information analysis, decision selection, action implementation) can independently operate at a different level.

Source: [Sheridan & Verplank, 1978, via ResearchGate](https://www.researchgate.net/figure/Levels-of-Automation-From-Sheridan-Verplank-1978_tbl1_235181550), [Parasuraman, Sheridan, Wickens, 2000](https://www.researchgate.net/publication/11596569_A_model_for_types_and_levels_of_human_interaction_with_automation_IEEE_Trans_Syst_Man_Cybern_Part_A_Syst_Hum_303_286-297)

**NASA Trust Building Model:**

"Trust must be built over time, beginning with AI informing low-level system functions and iteratively growing into higher-level system capabilities as trustworthiness is demonstrated." NASA's framework requires measurement of AI teaming performance before expanding autonomy to critical operations.

Source: [NASA Framework for Ethical Use of AI](https://ntrs.nasa.gov/api/citations/20210012886/downloads/NASA-TM-20210012886.pdf), [NIST Trustworthy AI 100-5e2025](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-5e2025.pdf)

**NIST AI Trust Framework (April 2025):**

Identifies trust as "an influential predictor of operator behavior in human-automation interaction." Both over-trust (automation complacency, rubber-stamping) and under-trust (disuse, micromanagement) are failure modes. The fix: calibrate trust through transparency, track record, and meaningful communication.

Source: [NIST Human-Centered AI](https://www.nist.gov/programs-projects/human-centered-ai), [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

### 5.3 Recommended Trust Architecture for Athanor

**Four autonomy levels** (simplified from Sheridan-Verplanck, already defined in `command-center.md`):

| Level | Name | Behavior | Notification | Dashboard Treatment |
|-------|------|----------|-------------|---------------------|
| **A** | Full Auto | Act and log | None (visible on request) | Activity logged, no highlight |
| **B** | Inform | Act and notify summary | Dashboard badge + optional push | Highlighted in stream |
| **C** | Propose | Recommend and wait for approval | Push notification with action buttons | Approval card in stream |
| **D** | Manual | Gather info and present options | Full-screen prompt | Modal overlay |

**Per-agent, per-action-type matrix:**

| Agent | Read-only Actions | Routine Actions | Modifications | Deletions |
|-------|------------------|-----------------|--------------|-----------|
| general-assistant | A | A | C | D |
| media-agent | A | B | C | D |
| home-agent | A | B | C | D |
| research-agent | A | A | N/A | N/A |
| creative-agent | A | B | C | D |
| knowledge-agent | A | A | N/A | N/A |
| coding-agent | A | C | C | D |
| stash-agent | A | B | C | D |

**Trust score thresholds for level graduation:**

| Transition | Required Score | Required Samples | Additional Condition |
|------------|---------------|-----------------|---------------------|
| D -> C | 0.50+ | 10+ | No corrections in last 5 actions |
| C -> B | 0.65+ | 25+ | < 10% correction rate over 20 actions |
| B -> A | 0.80+ | 50+ | < 5% correction rate over 50 actions |

**Trust regression (automatic):**

| Trigger | Effect | Recovery |
|---------|--------|----------|
| Single thumbs-down | Score -= 0.05 | Normal feedback accumulation |
| "Stop doing this" | Level drops by 1 for that action type | Requires 10 successful actions to recover |
| 3 corrections in 24 hours | Level drops by 1 for all actions of that agent | Requires 20 successful actions to recover |
| Manual "reduce autonomy" by Shaun | Drops to specified level | Only manual re-elevation |

### 5.4 Rubber-Stamp Prevention

The existing rubber-stamp detection (>20 approvals, 0 rejections) is a good start. Additional mechanisms:

1. **Approval rate monitoring**: If approval rate exceeds 95% over 20+ requests for an agent, automatically suggest raising that agent's autonomy level. "You've approved 47 of 48 media-agent requests. Should I raise it to Level B (act and notify)?"

2. **Deliberate test cases**: Occasionally (1 in 20), present a borderline case with a "review this carefully" flag. If Shaun approves it without engaging (< 2 seconds response time), that is a rubber-stamp signal.

3. **Batch approval detection**: If Shaun approves 5+ pending items in under 30 seconds, the system should note: "You approved several items quickly. Want to review any of them, or raise these agents' autonomy?"

4. **Meaningful friction**: For Level C and D actions, show the full context: what will happen, what the alternatives were, what the risk is. Not just "Approve?"

Source: [CyberManiacs - Rubber Stamp Risk](https://cybermaniacs.com/cm-blog/rubber-stamp-risk-why-human-oversight-can-become-false-confidence), [MIT Sloan - AI Explainability](https://sloanreview.mit.edu/article/ai-explainability-how-to-avoid-rubber-stamping-recommendations/)

### 5.5 Dynamic Autonomy Based on Context

Research on adaptive automation (EEG-based studies) shows that automation levels should adjust based on operator cognitive load. Applied to Athanor:

| Context | Autonomy Adjustment | Rationale |
|---------|---------------------|-----------|
| Shaun is actively using Command Center | Lower thresholds (more interaction) | He's available, so involve him more |
| Shaun hasn't opened Command Center in 4+ hours | Raise thresholds (more independence) | He's busy, so minimize interruptions |
| Weekend morning | Normal thresholds | Primary build time |
| Weekday 8 AM - 5 PM | Raise thresholds significantly | Work hours, minimize all non-critical notifications |
| Night (11 PM - 7 AM) | Maximum autonomy (except critical) | Don't wake him up for non-critical items |

Source: [Adaptive Automation via EEG, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5080530/)

Implementation: Track `last_command_center_visit` timestamp. Calculate time since last visit. Apply autonomy multiplier to threshold checks. Store schedule preferences (work hours, sleep hours) in the Goals API as constraints.

---

## 6. Feedback Loop Architecture

### 6.1 The Closed Loop

The fundamental feedback loop:

```
Intent Corpus → Work Planner → Task Queue → Agent Execution → Output
       ↑                                                        ↓
       |              ← Preference Store ←  Feedback Collection ←
       |                      ↓
       |              Context Injection
       |                      ↓
       └──── Better Agent Behavior ──→ Better Output → Less Correction
```

This loop has six stages, each with specific infrastructure:

| Stage | What Happens | Infrastructure | Status |
|-------|-------------|---------------|--------|
| 1. Intent | User intent documented | Markdown files, Goals API, profile | **Exists** |
| 2. Planning | Intent decomposed to tasks | Work Planner (Claude Code session) | **Missing** |
| 3. Execution | Agent performs task | Task Engine, Agent Server, GWT workspace | **Exists** |
| 4. Output | Result delivered to user | Command Center, push notifications | **Exists** |
| 5. Feedback | User responds (or doesn't) | Implicit tracking, thumbs, goals, steering | **Partially exists** |
| 6. Propagation | Feedback changes behavior | Context injection + pattern detection | **Partially exists** |

### 6.2 Event Sourcing for All System Activity

Research on event-driven AI architectures (Confluent, BigDataWire, HiveMQ) shows that the event backbone should be the "central source of truth" for agent systems. Each agent "wakes up" when a relevant event appears, retrieves context, reasons, and acts.

Source: [Confluent - Future of AI Agents is Event-Driven](https://www.confluent.io/blog/the-future-of-ai-agents-is-event-driven/), [BigDataWire - Event-Driven AI Agents](https://www.bigdatawire.com/2025/02/26/the-future-of-ai-agents-is-event-driven/)

**Athanor already has most of this via Redis pub/sub and the GWT workspace.** The missing piece is **event persistence and queryability.** Currently:
- GWT workspace items have TTL and expire
- Activity logs go to Qdrant but are append-only, not easily queryable for patterns
- Feedback goes to Qdrant preferences but isn't time-series queryable
- Task history is in Redis but not indexed for analysis

**Recommended addition: Event Log collection in Qdrant.** A new `events` collection that stores every significant system event with:

```python
@dataclass
class SystemEvent:
    id: str
    type: str  # 'task_completed', 'feedback_given', 'goal_changed', 'escalation_resolved',
               # 'agent_action', 'user_interaction', 'system_alert'
    agent: str
    content: str  # Human-readable description
    metadata: dict  # Structured data specific to event type
    timestamp: float
    # Computed fields for analysis:
    outcome: str | None  # 'positive', 'negative', 'neutral', None (unknown)
    feedback_id: str | None  # Links to feedback that referenced this event
```

This event log enables:
- **Pattern detection jobs** that analyze sequences of events
- **Feedback attribution** -- linking feedback to the specific events that caused it
- **Temporal analysis** -- what happens at different times of day, days of week
- **Agent performance tracking** -- which agents produce events that lead to positive outcomes

### 6.3 Preference Evolution Over Time

Currently, preferences are stored as flat embeddings in Qdrant. There is no concept of preference change over time. A preference from day 1 has the same weight as one from today.

**The filter bubble problem** is real: "Users become trapped inside a bubble wherein only information that a personalization algorithm thinks they would like gets passed in, and as they give the system more and more data, their bubble becomes smaller and smaller, resulting in a positive feedback loop with no escape."

Source: [Shaped.ai - Explore vs Exploit](https://www.shaped.ai/blog/explore-vs-exploit), [ResearchGate - Exploring the Filter Bubble](https://www.researchgate.net/publication/261960194_Exploring_the_filter_bubble_The_effect_of_using_recommender_systems_on_content_diversity)

**Recommended approach: Time-decayed preferences with exploration budget.**

1. **Time decay**: When querying preferences for context injection, apply a recency weight. Preferences from the last 7 days get full weight. Preferences older than 30 days get 50% weight. Preferences older than 90 days get 25% weight. This ensures behavior evolves with changing preferences.

2. **Exploration budget**: 10-20% of agent actions should be "exploratory" -- slightly outside the learned preference envelope. If the media agent learns Shaun likes sci-fi, it should still occasionally surface a well-rated thriller. If the home agent learns he prefers 70F, it should occasionally suggest energy-saving adjustments.

3. **Diversity injection**: When context injection returns preferences, include at least one "contrarian" preference (the least-matched but still above relevance threshold). This prevents convergence to a single narrow behavior pattern.

4. **Preference versioning**: Store a `version` counter on preferences. When a preference is contradicted by a newer signal (e.g., old preference says "prefer 1080p," new thumbs-up on a 4K suggestion), the old preference gets a `superseded_by` pointer. This preserves history while allowing evolution.

### 6.4 Real-Time vs Batch Learning

| Type | Use Case | Implementation | Latency |
|------|----------|---------------|---------|
| **Real-time** | Thumbs down on current response | Store immediately, inject into next request | < 1 second |
| **Session-level** | "Stop doing this" during a chat session | Update agent's context for all subsequent messages | Immediate |
| **Hourly batch** | Implicit signal aggregation | Batch job: analyze last hour's implicit events, update preference weights | 1 hour |
| **Daily batch** | Pattern detection, trust score updates, diversity analysis | Daily job at 5:00 AM (before work planner at 6:00 AM) | 24 hours |
| **Weekly batch** | Goal-level assessment, autonomy level reviews, trend analysis | Weekly job, Sunday 8:00 AM | 7 days |

The critical insight: **immediate feedback is for corrections, batch feedback is for learning.** When Shaun gives a thumbs-down, that correction should affect the very next request (via context injection). But the system-wide learning (pattern detection, trust calibration, preference evolution) should happen in batch to avoid instability.

### 6.5 Preventing Boring/Repetitive Convergence

Five mechanisms to prevent the system from becoming monotonously predictable:

1. **Fatigue modeling**: Spotify research and SIGIR 2024 show that users get tired of content too similar to recent history. Track "topic saturation" -- if an agent keeps surfacing the same type of information, reduce its salience. The FRec model improved AUC by 0.026 through explicit fatigue modeling.

Source: [SIGIR 2024 - Modeling User Fatigue](https://dl.acm.org/doi/10.1145/3626772.3657802)

2. **Exploration vs exploitation**: Allocate 10-20% of agent capacity to exploratory actions. The multi-armed bandit framework (Thompson sampling or epsilon-greedy) balances known-good actions with discovery.

3. **Seasonal variation**: Different times of year, different moods, different priorities. The system should detect seasonal patterns (summer vs winter, weekday vs weekend) and adjust behavior.

4. **Serendipity injection**: Deliberately surface unexpected but potentially relevant items. If the knowledge agent finds a research paper tangentially related to an active project, surface it even if it doesn't match current preferences exactly.

5. **Periodically reset minor preferences**: Preferences older than 90 days with low confidence (few supporting signals) should be soft-deleted, forcing the system to re-learn from current behavior rather than operating on stale assumptions.

---

## 7. The Self-Feeding Furnace Pattern

### 7.1 The Core Concept

The athanor metaphor is not just branding -- it is the design pattern. A self-feeding furnace maintains its own heat by using the byproducts of combustion to sustain the reaction. In Athanor, completed work generates new work:

```
Research findings → New research questions → Deeper investigation
Code generation → Testing → Bug fixes → Documentation
Creative output → Review queue → Refinement → Portfolio building
Media organization → Gap detection → Acquisition tasks
Knowledge indexing → Contradiction detection → Resolution tasks
Home automation → Pattern learning → New automation proposals
```

### 7.2 How Work Feeds Work (Concrete Chains)

**Chain 1: Research Discovery**
```
Research agent completes a research task
  → Findings stored in knowledge base
  → Work Planner reads findings in next planning cycle
  → If findings contain open questions → new research tasks
  → If findings suggest a decision → propose ADR creation task for coding agent
  → If findings invalidate a previous decision → flag for Shaun review
```

**Chain 2: Creative Production**
```
Creative agent generates images
  → Images stored in ComfyUI output directory
  → Activity log records generation parameters + prompt
  → If image was kept (no regeneration within 5 min) → positive feedback signal
  → If regenerated → negative feedback signal on specific parameters
  → Work Planner sees "creative output accumulated" → schedule review/organize task
  → If EoBQ project active → generate character variations, scene illustrations
```

**Chain 3: Media Intelligence**
```
Media agent scans Sonarr/Radarr
  → Detects new content added
  → Activity log records genre, quality, source
  → Over time: pattern emerges (prefers sci-fi, ignores reality TV)
  → Work Planner: generate "content gap analysis" research task
  → Research agent identifies highly-rated shows in preferred genres not in library
  → Media agent proposes additions (Level C: needs approval)
```

**Chain 4: Code Improvement**
```
Coding agent completes a code generation task
  → Output stored in /output staging area
  → Claude Code reviews in next session
  → If accepted: knowledge base updated with pattern
  → If rejected: negative feedback on coding approach
  → Work Planner detects "documentation gap" → schedule doc update task
  → Knowledge agent detects stale docs → schedule re-indexing
```

**Chain 5: Home Learning**
```
Home agent monitors HA entities every 5 minutes
  → Records occupancy patterns, temperature preferences, light usage
  → After 7 days: pattern detection job identifies routines
  → Home agent proposes new automations (Level C: needs approval)
  → If approved: routine becomes autonomous (Level A)
  → If override detected: adjust parameters, re-propose
```

### 7.3 Preventing Runaway Task Generation

The AutoGPT failure mode is well-documented: "A single unattended run can rack up hundreds of dollars in token usage if the agent doesn't stop itself." Athanor must prevent this without killing the self-feeding pattern.

**Five throttling mechanisms:**

1. **Daily task cap**: Maximum 10 generated tasks per planning cycle. Maximum 20 total tasks in queue at any time. Hard limits, not soft targets.

2. **Depth limit**: Task chains have a maximum depth of 3. A task spawned by a task spawned by a task cannot spawn another task. This prevents unbounded recursion.

3. **Deduplication**: Before submitting a task, check if a substantially similar task (same agent, similar prompt, similar metadata) was completed or is pending in the last 24 hours. Use embedding similarity (threshold 0.85) for fuzzy deduplication.

4. **Energy budget**: Each agent has a daily "energy" budget measured in task executions. Default: 5 per agent per day for generated tasks (manually submitted tasks are unlimited). When an agent exhausts its energy, it cannot receive generated tasks until the next day.

5. **Human circuit breaker**: A global "pause automation" toggle in the Command Center that immediately stops all generated tasks while allowing manual tasks and in-progress work to complete. This is the algorithmic trading "kill switch" applied to a homelab -- nuanced emergency stop, not total shutdown.

Source: [FIA Best Practices for Automated Trading Risk Controls](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf)

### 7.4 Quality Gating

Not all completed work should feed new work. Quality gates prevent low-quality output from propagating:

| Gate | Trigger | Action |
|------|---------|--------|
| **Output validation** | Task completes | Check if output contains actual content (not error messages, empty results, or apologetic "I couldn't find anything") |
| **Feedback-gated propagation** | Task output receives feedback | Only tasks with positive feedback (or no negative feedback within 1 hour) feed new tasks |
| **Novelty check** | New task generated from output | Verify the new task adds something the system doesn't already know (embedding distance from existing knowledge > 0.3) |
| **Value assessment** | Daily batch | Score each completed task on outcome value (did it lead to action? was the output used?). Low-value tasks don't feed follow-up generation. |

---

## 8. Interaction Design for Human-in-the-Loop

### 8.1 The Mission Control Metaphor

The Command Center already embodies the mission control pattern. Key references:

**NASA Open MCT** is an open-source mission operations data visualization framework designed for "planning and conducting of a mission." It emphasizes real-time telemetry display, historical data playback, and configurable layouts. Athanor's Command Center achieves similar goals with a more consumer-friendly aesthetic.

Source: [NASA Open MCT](https://nasa.github.io/openmct/)

**SpaceX Crew Dragon UI**: "A dark, touch-driven interface with minimal chrome, focused on critical information display with progressive disclosure of detail." The interface uses gesture-based interaction (swipe, drag, pinch) with clear visual hierarchy.

Source: [UX Collective - SpaceX Dashboard UI](https://uxdesign.cc/how-i-recreated-crew-dragons-ui-15877eddf3ed)

### 8.2 The Oversight Dashboard Pattern

For autonomous system oversight, research identifies these essential patterns:

1. **At-a-glance health**: The home surface must answer "is everything OK?" in under 2 seconds. The Crew Bar (agent portraits with state-driven animation) and System Pulse strip already provide this.

2. **Progressive disclosure**: Surface → Card → Detail. Never overwhelm with all information at once. The three-layer depth model (Pulse Strip → Domain Cards → Detail Pages) is already designed.

3. **Intervention surfaces near the information**: When the system shows an agent's output, the feedback controls (thumbs, stop, more/less) must be immediately adjacent. Not on a separate settings page.

4. **Transparency on demand**: Every agent action should have a retrievable explanation ("I did X because Y"), hidden by default (noise reduction) but accessible with one tap.

5. **Historical comparison**: Show trends, not just snapshots. "Agent trust score this week" as a sparkline is more informative than a single number.

### 8.3 Mobile Patterns for Quick Feedback

Research on 2026 mobile UI patterns (UXPilot, Sanjay Dey, GroovyWeb) shows:

**Gesture dictionary for AI system interaction:**
- Swipe right: positive/approve (like Tinder's "like")
- Swipe left: negative/dismiss
- Swipe down: refresh/close
- Long press: context menu with "more of this" / "less of this" / "stop"
- Pull to refresh: reload data
- Tap: primary action (view detail)

Source: [Movea-tech - Gesture UI Design Guide 2026](https://www.movea-tech.com/motion-control-2026/)

**Dark AI interface pattern (2026):**
"Dark base surfaces with translucent frosted panels for AI output areas, reducing eye strain during extended AI interaction sessions and creating visual separation without rigid card borders." This aligns with Athanor's existing warm-dark design language.

Source: [GroovyWeb - UI/UX Design Trends for AI-First Apps 2026](https://www.groovyweb.co/blog/ui-ux-design-trends-ai-apps-2026)

**Notion 3.0's Agent Model (September 2025):**
Notion 3.0 introduced AI Agents that "can work autonomously for up to 20 minutes, performing multi-step tasks across hundreds of pages simultaneously." The key UX insight: users give their agent "an instructions page so it feels like a teammate who knows your work and style, telling it how you like things written, what to reference, and where to file tasks." Custom Agents "can run autonomously on a schedule or triggers, so work keeps moving even while you're asleep."

This is almost exactly Athanor's model: agent contracts define behavior, goals provide instructions, the scheduler runs on triggers/intervals, and work continues autonomously.

Source: [Notion 3.0 Agents](https://www.notion.com/releases/2025-09-18), [OpenAI - Notion's rebuild for agentic AI](https://openai.com/index/notion/)

### 8.4 Notification Design That Informs Without Overwhelming

**The attention budget** (from `command-center.md`):
- Max 5-10 Notable + 0-2 Critical per day
- 30-50% of surfaced items should require action
- Fatigue modeling: if Shaun ignores a category 3 times, suppress until weekly review
- Correlation before notification: one notification per situation, not one per agent

**Research quantification** (from `2026-02-25-human-in-the-loop-patterns.md`):
- Teams receive 2,000+ alerts weekly with only 3% requiring immediate action
- 67% of alerts are ignored daily
- 85% false positive rate across industries
- Target: 30-50% actionable notification rate

Source: [incident.io - Alert Fatigue Solutions 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)

**Recommended notification categories for Athanor:**

| Category | Examples | Delivery | Daily Budget |
|----------|---------|----------|--------------|
| **Critical** | Node down, data loss risk, security alert | Push + banner + sound | 0-2 |
| **Approval** | Agent needs permission for Level C/D action | Push with action buttons | 3-5 |
| **Informational** | Task completed, new content added, digest ready | Dashboard badge only | 5-10 |
| **Background** | Routine health checks, scheduled task logs | Activity log only | Unlimited (not pushed) |

### 8.5 Showing "What the System is Thinking"

Transparency builds trust. But constant explanation creates noise. The resolution:

1. **Reasoning traces available on demand**: Every agent action has a stored reasoning trace (the ReAct loop's tool calls and intermediate thoughts). Show a "Why?" link on every stream entry. Tap to expand the full trace.

2. **Confidence indicators**: When an agent is uncertain (confidence < 0.7), show a subtle uncertainty indicator (e.g., a "?" badge on the agent's crew bar portrait). This is the Waymo model: the system says "I'm not sure about this" before asking for help.

3. **Impact annotations**: When feedback changes behavior, annotate the next relevant output: "Based on your feedback, I'm now prioritizing 4K quality." Spotify's research shows that "users were up to four times more likely to click on recommendations accompanied by explanations."

Source: [Spotify Personalization Design](https://newsroom.spotify.com/2023-10-18/how-spotify-uses-design-to-make-personalization-features-delightful/)

4. **Work Planner transparency**: When the daily work plan is generated, show it in the morning digest: "Today I'm planning: 3 media tasks, 2 home tasks, 1 research task. Here's why." Shaun can modify, remove, or add to the plan.

---

## 9. Recommended Architecture

### 9.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTENT CORPUS                                 │
│  VISION.md  TODO.md  Goals  Profile  Agent Contracts  Research       │
│  BUILD-MANIFEST  Starred Repos  ADRs  Feedback History               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ reads daily (6:00 AM)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORK PLANNER (Claude Code)                       │
│  Intent Extraction → Task Decomposition → Validation → Submission    │
│  Max 10 tasks/day, depth limit 3, dedup, energy budget               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ submits via MCP bridge
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TASK ENGINE (Node 1:9000)                        │
│  Redis queue, max 2 concurrent, priority ordering                    │
│  Step logging, GWT workspace broadcast, activity logging             │
└──────────┬───────────────────┬───────────────────┬──────────────────┘
           │                   │                   │
     ┌─────▼──────┐     ┌────▼──────┐      ┌────▼──────┐
     │  Agent 1   │     │  Agent 2  │      │  Agent N  │
     │  Execute   │     │  Execute  │      │  Execute  │
     └─────┬──────┘     └────┬──────┘      └────┬──────┘
           │                  │                   │
           ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OUTPUT DELIVERY                                │
│  Command Center (SSE stream, push notifications, generative UI)      │
│  Activity log (Qdrant), Event log (Qdrant), Workspace (Redis)        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ PASSIVE FEEDBACK │ │  MICRO FEEDBACK  │ │ DIRECTED FEEDBACK│
│ (Zero effort)    │ │  (Thumbs, swipe) │ │ (Goals, steering)│
│ Page views       │ │  Binary signals  │ │ Natural language │
│ Dwell time       │ │  Quick dismiss   │ │ Constraints      │
│ Ignore patterns  │ │  More/less       │ │ Goal proposals   │
│ Override actions  │ │  Star/bookmark   │ │ Weekly review    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                     │
         ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FEEDBACK PROCESSING                                │
│                                                                      │
│  Real-time:  Immediate corrections → context injection               │
│  Hourly:     Implicit signal aggregation → preference weights        │
│  Daily:      Pattern detection → trust scores → preference decay     │
│  Weekly:     Goal assessment → autonomy calibration → trend reports   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ updates
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PREFERENCE STORE (Qdrant)                         │
│  preferences (explicit + implicit, time-decayed)                     │
│  events (system event log, all agent activity)                       │
│  activity (per-agent interaction logs)                                │
│  knowledge (2220 doc vectors)                                        │
│  conversations (chat history, to be populated)                       │
│  implicit_feedback (NEW: behavioral signals from Command Center)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ context injection (30-50ms)
                               ▼
                     BETTER AGENT BEHAVIOR
                               │
                               ▼
                     LESS CORRECTION NEEDED
                               │
                               ▼
                     HIGHER TRUST SCORES
                               │
                               ▼
                     MORE AUTONOMY GRANTED
                               │
                               ▼
                     LESS HUMAN EFFORT
```

### 9.2 New Components to Build

| Component | Effort | Priority | Depends On |
|-----------|--------|----------|-----------|
| **Implicit feedback tracking** (client-side events) | 1-2 days | P0 | Command Center |
| **Implicit feedback API** (`/api/feedback/implicit`) | 0.5 day | P0 | Dashboard API routes |
| **Implicit feedback Qdrant collection** | 0.5 day | P0 | Qdrant |
| **Inline micro-feedback UI** (thumbs on all outputs) | 1 day | P0 | Command Center |
| **Work Planner Claude Code command** (`/plan`) | 2-3 days | P1 | MCP bridge, intent corpus |
| **Work Planner scheduler** (daily 6:00 AM) | 0.5 day | P1 | Claude Code Claudeman |
| **Time-decayed preference queries** | 1 day | P1 | context.py modification |
| **Pattern detection batch job** | 2-3 days | P1 | Event log, activity log |
| **Autonomy auto-graduation** | 1 day | P1 | Trust scores, escalation config |
| **Trust regression triggers** | 1 day | P1 | Feedback store, trust scores |
| **Notification budget enforcement** | 1 day | P1 | Push notification system |
| **Task chain follow-up generation** | 2 days | P2 | Task engine, work planner |
| **Diversity injection in context** | 1 day | P2 | context.py modification |
| **Rubber-stamp countermeasures** | 1 day | P2 | Escalation system |
| **Dynamic autonomy (context-based)** | 1 day | P2 | Session tracking |
| **Weekly review digest** | 1 day | P2 | Scheduler, goals API |
| **Pause automation toggle** | 0.5 day | P2 | Command Center, task engine |
| **Conversational steering** (chat → goal) | 2 days | P3 | General assistant, goals API |
| **Goal suggestion by agents** | 2 days | P3 | Pattern detection, goals API |
| **Pairwise comparison UI** | 2 days | P3 | Command Center |

### 9.3 Data Model Additions

**New Qdrant collection: `implicit_feedback`**

```python
{
    "id": "uuid",
    "vector": [1024-dim embedding of page/context],
    "payload": {
        "type": "page_view" | "dwell" | "tap" | "ignore" | "override" | "scroll" | "lens_change",
        "page": "/agents",
        "agent": "media-agent",  # if applicable
        "duration_ms": 4500,
        "metadata": {},
        "timestamp": 1740000000.0,
        "timestamp_iso": "2026-02-26T12:00:00Z",
        "session_id": "abc123"
    }
}
```

**New Qdrant collection: `events`**

```python
{
    "id": "uuid",
    "vector": [1024-dim embedding of content],
    "payload": {
        "type": "task_completed" | "feedback_given" | "goal_changed" | "escalation_resolved" | ...,
        "agent": "media-agent",
        "content": "Media agent added Breaking Bad (2008) to Sonarr monitoring",
        "metadata": {
            "task_id": "task-abc123",
            "action_type": "add_tv_show",
            "outcome": "positive"
        },
        "timestamp": 1740000000.0,
        "outcome": "positive",
        "feedback_id": null
    }
}
```

**Modifications to `preferences` collection:**

Add fields to existing payloads:
- `version`: integer, incremented on update
- `superseded_by`: string (ID of newer contradicting preference), null if current
- `decay_weight`: float (1.0 = current, decays over time)
- `source_level`: integer (0-4, which feedback level generated this)

**Redis additions:**

```
athanor:autonomy:{agent}:{action_type} → "A" | "B" | "C" | "D"
athanor:notification_budget:{agent}:{date} → integer (count today)
athanor:work_planner:last_run → timestamp
athanor:work_planner:daily_plan → JSON (today's plan)
athanor:energy_budget:{agent}:{date} → integer (remaining)
athanor:session:last_visit → timestamp (last Command Center visit)
athanor:pause_automation → "0" | "1"
```

---

## 10. Implementation Sequence

### Phase 1: Foundation (1-2 weekends) -- "Close the Loop"

The minimum viable feedback loop: implicit tracking + inline micro-feedback + time-decayed preferences.

1. **Implicit feedback tracking** -- Add client-side event emission to Command Center. Every page view, tap, scroll, and lens change emits an event. Batch to `/api/feedback/implicit` every 30s.

2. **`implicit_feedback` Qdrant collection** -- Create collection, API route for ingestion, embed events with context.

3. **Inline micro-feedback** -- Add thumbs up/down to every agent output in Stream, Chat, and Activity pages. Wire to existing `store_feedback()` in `goals.py`.

4. **Time-decayed preference queries** -- Modify `context.py` `_search_collection()` to apply recency weighting. Preferences from last 7 days at full weight, decay to 25% at 90 days.

5. **Notification budget enforcement** -- Add daily counter per agent in Redis. Check before sending push notifications. Enforce the 5-10 Notable + 0-2 Critical budget.

**Verification:** After Phase 1, every interaction with the Command Center generates implicit feedback signals, every agent output has binary feedback affordance, and preferences evolve over time rather than accumulating forever.

### Phase 2: Intelligence (2-3 weekends) -- "Agents Learn"

Pattern detection, trust automation, and the daily work planner.

6. **Event log collection** -- New `events` Qdrant collection. Emit events from task engine (completion, failure), escalation system (resolved), feedback system, and goals API.

7. **Pattern detection batch job** -- Daily asyncio job at 5:00 AM. Analyzes event and activity logs. Identifies: frequently corrected agent actions, time-of-day patterns, preference trends, topic saturation. Outputs pattern records to preferences collection.

8. **Autonomy auto-graduation** -- Extend `compute_trust_scores()` to automatically adjust autonomy levels based on thresholds (Section 5.3). Store autonomy level per agent per action type in Redis.

9. **Trust regression triggers** -- On thumbs-down or "stop doing this," automatically lower trust score and potentially autonomy level (Section 5.4).

10. **Work Planner v1** -- Claude Code command (`/plan`) that reads intent corpus, generates tasks, validates, and submits via MCP bridge. Manual invocation first, scheduled later.

**Verification:** After Phase 2, agents' autonomy levels change based on their track record. Pattern detection identifies recurring behaviors. The work planner can generate a day's worth of agent tasks from documented intent.

### Phase 3: Autonomy (2-3 weekends) -- "The Furnace Feeds Itself"

Self-feeding work generation, dynamic autonomy, and human circuit breakers.

11. **Task chain follow-up generation** -- When a task completes, the task engine checks if the output warrants follow-up tasks. Rules-based initially (research → knowledge indexing, code → testing), LLM-based later.

12. **Dynamic autonomy** -- Track `last_command_center_visit`. Adjust autonomy thresholds based on presence/absence, time of day, and day of week (Section 5.5).

13. **Work Planner scheduler** -- Schedule the work planner to run daily at 6:00 AM via Claudeman. Output the plan to the morning digest.

14. **Pause automation toggle** -- Add a global "pause automation" button to Command Center. Stops all generated tasks while allowing manual tasks and in-progress work.

15. **Diversity injection** -- Modify context injection to include contrarian preferences. Add exploration budget to agent task generation.

**Verification:** After Phase 3, completed work generates follow-up work. The system adjusts its behavior based on Shaun's presence. A daily work plan is generated automatically. The circuit breaker can halt all autonomous work with one tap.

### Phase 4: Refinement (ongoing) -- "The Furnace Refines Itself"

16. **Conversational steering** -- General assistant recognizes steering intent ("focus on media quality") and routes to Goals API.

17. **Goal suggestions by agents** -- Pattern detection identifies recurring corrections and proposes goal modifications.

18. **Weekly review digest** -- Extended digest with goal assessment, trend analysis, autonomy level recommendations.

19. **Pairwise comparison UI** -- For calibration events, show two agent outputs side by side.

20. **Rubber-stamp countermeasures** -- Batch approval detection, deliberate test cases, meaningful friction.

21. **Energy budget tuning** -- Adjust per-agent daily task caps based on observed quality and throughput.

---

## 11. Open Questions for Shaun

These decisions require Shaun's input because they affect the fundamental experience of using Athanor:

1. **Work Planner autonomy level**: Should the daily work plan be generated and submitted automatically (Level A), or should Shaun review and approve the plan each morning before tasks are submitted (Level C)? Recommendation: Start at Level C (review plan in morning digest), graduate to Level A after 2 weeks of consistent approval.

2. **Notification channel preference**: For Level C approval requests, should they be (a) push notifications with inline Approve/Reject buttons, (b) push notification that links to the Command Center, or (c) both? Recommendation: (a) for simple approvals, (b) for complex ones that need context.

3. **Implicit tracking scope**: Is client-side behavioral tracking (page views, dwell time, tap patterns) acceptable? It never leaves the local network, but it does mean the system is recording browsing behavior within the Command Center.

4. **Exploration budget**: 10% or 20% of agent actions should be exploratory (outside learned preferences)? Too low and the system becomes a filter bubble. Too high and it feels random.

5. **Work hours constraint**: What are the exact hours during which the system should minimize all non-critical notifications? Current assumption: weekdays 8 AM - 5 PM (work hours), 11 PM - 7 AM (sleep). Correct?

6. **Amanda considerations**: Should the home agent's autonomy be constrained when Amanda is home (detected via HA presence)? E.g., no automated HVAC changes, reduced notification volume.

7. **Weekly review format**: Would a Sunday morning push notification with "here's your weekly review, tap to open" be the right cadence? Or would Shaun prefer it in the morning digest on Monday?

---

## 12. Sources

### Autonomous Agent Systems
- [IBM - What is BabyAGI](https://www.ibm.com/think/topics/babyagi) -- BabyAGI architecture and task decomposition
- [BabyAGI.org](https://babyagi.org/) -- Original implementation
- [Built In - AutoGPT Explained](https://builtin.com/artificial-intelligence/autogpt) -- AutoGPT hierarchical task structure
- [Axis Intelligence - AutoGPT Deep Dive](https://axis-intelligence.com/autogpt-deep-dive-use-cases-best-practices/) -- AutoGPT 2025 production readiness
- [Agents Meet OKR, arXiv:2311.16542](https://arxiv.org/abs/2311.16542) -- OKR-Agent framework
- [ZenML - AutoGPT Alternatives](https://www.zenml.io/blog/autogpt-alternatives) -- Runaway loop prevention
- [LateNode - Agentic Workflows](https://latenode.com/blog/ai-agents-autonomous-systems/ai-agent-fundamentals-architecture/agentic-workflows-transforming-automation-with-autonomous-ai-agents) -- Iteration caps, step boundaries

### Human-in-the-Loop Feedback
- [Netflix Recommendation Algorithm Analysis](https://marketingino.com/the-netflix-recommendation-algorithm-how-personalization-drives-80-of-viewer-engagement/) -- 10x behavioral signal weight, 80% engagement from recommendations
- [Netflix Two Thumbs Up, Variety 2022](https://variety.com/2022/digital/news/netflix-two-thumbs-up-ratings-1235228641/) -- Binary beats granular (200% accuracy improvement)
- [Spotify Complete Guide 2025](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide) -- Half-trillion daily events, three-pillar recommendation
- [Spotify Prompted Playlists](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/) -- Natural language algorithm control
- [Spotify Personalization Design](https://newsroom.spotify.com/2023-10-18/how-spotify-uses-design-to-make-personalization-features-delightful/) -- 4x engagement with explanations
- [GitHub Copilot Internals](https://thakkarparth007.github.io/copilot-explorer/posts/copilot-internals.html) -- Accept/reject telemetry, 15s-10min persistence checking
- [Google Nest - How Thermostats Learn](https://support.google.com/googlenest/answer/9247510) -- User correction-driven adaptation
- [Beyond Explicit and Implicit, arXiv:2502.09869v1](https://arxiv.org/html/2502.09869v1) -- Intentional implicit feedback

### Trust and Autonomy
- [Sheridan & Verplank, 1978](https://www.researchgate.net/figure/Levels-of-Automation-From-Sheridan-Verplank-1978_tbl1_235181550) -- 10-level automation scale
- [Parasuraman, Sheridan, Wickens, 2000](https://www.researchgate.net/publication/11596569_A_model_for_types_and_levels_of_human_interaction_with_automation_IEEE_Trans_Syst_Man_Cybern_Part_A_Syst_Hum_303_286-297) -- Four automation functions model
- [NASA Framework for Ethical Use of AI](https://ntrs.nasa.gov/api/citations/20210012886/downloads/NASA-TM-20210012886.pdf) -- Trust built over time, iterative autonomy expansion
- [NIST Trustworthy AI 100-5e2025](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-5e2025.pdf) -- AI teaming measurement, responsible AI
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) -- Trust as predictor of operator behavior
- [CyberManiacs - Rubber Stamp Risk](https://cybermaniacs.com/cm-blog/rubber-stamp-risk-why-human-oversight-can-become-false-confidence) -- Structural safeguards against rubber-stamping
- [MIT Sloan - AI Explainability](https://sloanreview.mit.edu/article/ai-explainability-how-to-avoid-rubber-stamping-recommendations/) -- Avoiding rubber-stamp via process design
- [PMC - Calibrating Trust in Automated Systems](https://pmc.ncbi.nlm.nih.gov/articles/PMC11573890/) -- Over-trust vs under-trust failure modes
- [PMC - Trust Calibration Survey](https://pmc.ncbi.nlm.nih.gov/articles/PMC12058881/) -- What builds and breaks trust
- [Adaptive Automation via EEG, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5080530/) -- Dynamic autonomy based on cognitive load

### Feedback Loop Architecture
- [Confluent - Future of AI Agents is Event-Driven](https://www.confluent.io/blog/the-future-of-ai-agents-is-event-driven/) -- Event backbone as source of truth
- [BigDataWire - Event-Driven AI Agents](https://www.bigdatawire.com/2025/02/26/the-future-of-ai-agents-is-event-driven/) -- Observe-decide-act loop
- [SIGIR 2024 - Modeling User Fatigue](https://dl.acm.org/doi/10.1145/3626772.3657802) -- Fatigue-aware recommendation (FRec model)
- [Shaped.ai - Explore vs Exploit](https://www.shaped.ai/blog/explore-vs-exploit) -- Exploration/exploitation framework for recommendations
- [ResearchGate - Exploring the Filter Bubble](https://www.researchgate.net/publication/261960194_Exploring_the_filter_bubble_The_effect_of_using_recommender_systems_on_content_diversity) -- Positive feedback loop convergence

### Goal-Setting and Commander's Intent
- [Wikipedia - Commander's Intent](https://en.wikipedia.org/wiki/Intent_(military)) -- Task orders vs intent specification
- [MWI - Commander's Intent for Machines](https://mwi.westpoint.edu/commanders-intent-for-machines-reimagining-unmanned-systems-control-in-communications-degraded-environments/) -- Encoding intent into autonomous systems
- [Space Doctrine Publication 6-0, Mission Command](https://www.starcom.spaceforce.mil/Portals/2/SDP%206-0%20Mission%20Command%20(Nov%202024).pdf) -- Competence, trust, shared understanding
- [USNI - Beyond Mission Command](https://www.usni.org/magazines/proceedings/2025/april/beyond-mission-command-collaborative-leadership) -- Bidirectional communication model

### Attention Management
- [incident.io - Alert Fatigue Solutions 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works) -- 2000+ weekly alerts, 3% actionable, 85% false positive rate
- [IBM - Alert Fatigue Reduction with AI](https://www.ibm.com/think/insights/alert-fatigue-reduction-with-ai-agents) -- 40% false positive reduction
- [FIA Best Practices for Automated Trading Risk Controls](https://www.fia.org/sites/default/files/2024-07/FIA_WP_AUTOMATED%20TRADING%20RISK%20CONTROLS_FINAL_0.pdf) -- Kill switches, circuit breakers, layered defense

### Interaction Design
- [NASA Open MCT](https://nasa.github.io/openmct/) -- Open-source mission operations framework
- [UX Collective - SpaceX Dashboard UI](https://uxdesign.cc/how-i-recreated-crew-dragons-ui-15877eddf3ed) -- Dark touch-driven interface pattern
- [Movea-tech - Gesture UI Design Guide 2026](https://www.movea-tech.com/motion-control-2026/) -- Gesture dictionary for AI interaction
- [GroovyWeb - UI/UX Design Trends for AI-First Apps 2026](https://www.groovyweb.co/blog/ui-ux-design-trends-ai-apps-2026) -- Dark AI interface pattern
- [UXPilot - Mobile App Design Trends 2026](https://uxpilot.ai/blogs/mobile-app-design-trends) -- Three-level success feedback
- [Notion 3.0 Agents](https://www.notion.com/releases/2025-09-18) -- AI agents working autonomously with instructions pages
- [OpenAI - Notion's Rebuild for Agentic AI](https://openai.com/index/notion/) -- Agents on schedules and triggers
- [Calm Technology Principles](https://www.caseorganic.com/post/principles-of-calm-technology) -- Tea kettle principle, peripheral awareness

### RLHF and Feedback Quality
- [Uni-RLHF, arXiv:2402.02423](https://arxiv.org/abs/2402.02423) -- Pairwise comparison reliability
- [RLHF Survey, arXiv:2312.14925](https://arxiv.org/abs/2312.14925) -- Feedback mechanism quality hierarchy
- [RLHF Survey, arXiv:2504.12501v3](https://arxiv.org/html/2504.12501v3) -- Quality-fatigue tradeoff
- [Labellerr - RLHF Tools 2025](https://www.labellerr.com/blog/top-tools-for-rlhf/) -- Rubric-based evaluation
- [Karpathy - 2025 LLM Year in Review](https://karpathy.bearblog.dev/year-in-review-2025/) -- RLVR paradigm shift

### Existing Athanor Research (previously completed)
- `docs/research/2026-02-25-human-in-the-loop-patterns.md` -- 10-domain HITL survey (64 KB)
- `docs/archive/research/2026-02-25-command-center-ui-design.md` -- SpaceX, NOC, gaming HUD, adaptive UI
- `docs/research/2026-02-25-novel-interface-patterns.md` -- Conversational UI, calm tech, spatial, generative UI
- `docs/research/2026-02-25-mobile-pwa-architecture.md` -- PWA, SSE, push notifications
- `docs/research/2026-02-25-web-development-environments.md` -- Claude Code web access, Claudeman

### Existing Athanor Code (analyzed)
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/goals.py` -- Goals API, feedback storage, trust scores, daily digest
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/context.py` -- Context injection pipeline, per-agent config
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/scheduler.py` -- Proactive scheduler, daily digest timing
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/tasks.py` -- Task engine, Redis queue
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/workspace.py` -- GWT workspace, Redis pub/sub
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/escalation.py` -- 3-tier escalation protocol
- `/home/shaun/repos/Athanor/projects/agents/src/athanor_agents/activity.py` -- Activity logging to Qdrant
