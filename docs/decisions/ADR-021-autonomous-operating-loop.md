# ADR-021: Autonomous Operating Loop

**Date:** 2026-02-26
**Status:** Accepted
**Deciders:** Shaun, Claude
**Research:** `docs/research/2026-02-26-autonomous-operating-loop.md`

---

## Context

Athanor has 8 agents, a task engine, scheduler, goals API, trust scores, feedback storage, and context injection — all deployed and working. But the system is reactive: it waits for human-initiated tasks. The infrastructure exists for autonomous operation, but nothing decides **what** to do autonomously.

Shaun wants a self-feeding system where completed work generates new work, with him providing steering and feedback — not task-by-task direction. The system should require zero daily effort to operate, but give powerful steering controls when he chooses to engage.

## Decision

**Three new capabilities layered on existing infrastructure:**

### 1. Work Planner

A scheduled process that reads the intent corpus (VISION.md, TODO.md, BUILD-MANIFEST.md, goals, profile, agent contracts, starred repos) and generates concrete agent tasks.

- Runs daily at 6:00 AM (before the 6:55 AM morning digest)
- Max 10 tasks/day, depth limit 3 (a task's follow-up can spawn follow-ups, but no deeper)
- Deduplication against recently completed and currently pending tasks
- Energy budget per agent (prevents one agent from monopolizing resources)
- Submits via existing `/v1/tasks` API

### 2. Five-Level Feedback Collection

Feedback at every effort level, from zero-effort to deliberate:

| Level | Effort | Example | Signal Strength |
|-------|--------|---------|-----------------|
| **Passive** | 0s | Page views, dwell time, what's ignored | Weak (weight 0.1) |
| **Micro** | 2s | Thumbs up/down, swipe approve/reject | Medium (weight 0.5) |
| **Quick** | 10s | Star, "more like this", dismiss | Medium (weight 0.5) |
| **Directed** | 1-2min | "Focus on media quality", goal adjustment | Strong (weight 1.0) |
| **Deliberate** | 5-10min | Weekly review, pairwise comparison | Strongest (weight 1.5) |

All feedback is time-decayed: full weight for 7 days, linear decay to 25% at 90 days, then stable.

### 3. Per-Agent Autonomy Graduation

Trust is a per-agent, per-action-type score that starts at Level C and graduates based on track record:

| Level | Behavior | Threshold |
|-------|----------|-----------|
| **A** (Act & Log) | Execute, log result | Trust > 0.8, 20+ successful actions |
| **B** (Act & Notify) | Execute, push notification | Trust > 0.6, 10+ successful actions |
| **C** (Propose & Wait) | Propose, wait for approval | Default starting level |
| **D** (Suggest Only) | Suggest, never execute | After trust regression |

Regression: Any thumbs-down or correction drops trust by 0.1 and autonomy by one level. Recovery requires 5 consecutive successful actions at the lower level.

### Throttling Mechanisms

1. **Daily task cap**: 10 tasks/day (global), 5/day (per agent)
2. **Depth limit**: Task follow-ups limited to 3 generations
3. **Deduplication**: 24h window against completed + pending
4. **Energy budget**: Per-agent, resets daily
5. **Human circuit breaker**: One-tap "pause automation" on Command Center

## Rationale

1. **Work Planner as scheduled process, not always-on.** Continuous intent monitoring creates noise. A daily cadence matches Shaun's engagement pattern (evening review, morning plan).

2. **Five levels, not just binary.** Research shows (Netflix, Spotify) that passive signals at scale outweigh explicit feedback. But explicit feedback provides calibration that passive can't.

3. **Time decay, not accumulation.** Without decay, month-old preferences crowd out current intent. The 7-day full / 90-day floor provides both responsiveness and memory.

4. **Per-agent, per-action autonomy.** The media agent might be Level A for monitoring shows but Level C for downloading. Granular trust prevents all-or-nothing failures.

5. **Conservative defaults.** Starting at Level C means the system proposes before acting. This builds Shaun's confidence while accumulating the track record needed for graduation.

## Implementation Phases

### Phase 1: Close the Loop (P0)
- Implicit feedback tracking (client-side events to new Qdrant collection)
- Time-decayed preference queries in context injection
- Notification budget enforcement (5-10 per agent per day)

### Phase 2: Agents Learn (P1)
- Event log collection (new `events` Qdrant collection)
- Pattern detection batch job (daily at 5:00 AM)
- Autonomy auto-graduation and trust regression triggers
- Work Planner v1 (manual invocation)

### Phase 3: The Furnace Feeds Itself (P2)
- Task chain follow-up generation
- Dynamic autonomy (adjusts based on Shaun's presence)
- Work Planner scheduler (daily 6:00 AM)
- Pause automation toggle on Command Center
- Diversity injection (10% exploration budget)

### Phase 4: Refinement (ongoing)
- Conversational steering (chat intent → goals)
- Goal suggestions by agents
- Weekly review digest
- Rubber-stamp countermeasures

## Open Questions (for Shaun)

1. Should the daily work plan auto-submit (Level A) or require morning approval (Level C)?
2. Is client-side behavioral tracking (page views, dwell, taps) acceptable?
3. 10% or 20% exploration budget?
4. Work/sleep hours for notification suppression?
5. Should home-agent autonomy decrease when Amanda is home?

## Consequences

### Positive
- System operates autonomously with zero daily effort from Shaun
- Feedback at every effort level — from passive to deliberate
- Agents improve over time via closed feedback loops
- Conservative defaults prevent runaway or undesired actions
- All existing infrastructure reused (nothing thrown away)

### Negative
- Complexity: 20+ new components across 4 phases
- Implicit tracking raises privacy considerations (mitigated: LAN-only)
- Risk of filter bubble without diversity injection
- Work Planner depends on Claude Code/Claudeman availability

### Risks
- Runaway work generation — mitigated by 5 throttling mechanisms
- Rubber-stamping approvals — mitigated by detection and countermeasures
- Stale intent corpus — mitigated by research agent indexing
- Trust gaming — unlikely with single user, but regression handles it

---

## Architecture

```
INTENT CORPUS (VISION, TODO, Goals, Profile, Contracts)
        │ reads daily
        ▼
WORK PLANNER → generates tasks → TASK ENGINE → AGENTS → OUTPUT
                                                           │
        ┌──────────────────────────────────────────────────┘
        ▼
FEEDBACK (5 levels) → PREFERENCE STORE (time-decayed)
        │                                    │
        ▼                                    ▼
TRUST SCORES → AUTONOMY LEVELS → BEHAVIOR CHANGE
        │
        ▼
LESS CORRECTION → HIGHER TRUST → MORE AUTONOMY → LESS HUMAN EFFORT
```
