# ADR-023: Automation Backbone Program

## Status

Accepted

## Context

Athanor already had major pieces of the operator cockpit, autonomy loops, and subscription-control layer implemented, but they were not sharing one normalized operational model. The dashboard mounted cards such as `DailyBriefing`, `UnifiedStream`, `WorkPlan`, `AgentCrewBar`, `ResearchJobsCard`, `SkillsLane`, `ConsolidationCard`, and `RoutingContextCard`, while the agent server already exposed subscriptions, tasks, schedules, research jobs, alerts, and consolidation endpoints.

The gap was not raw feature count. The gap was the lack of one backbone contract tying these areas together:

- execution history and provider-lane visibility
- schedule visibility across agent loops and system jobs
- operator event streaming
- quota and reserve posture for subscription-backed execution

This phase also needs a branch model that allows parallel cockpit, autonomy, and provider-plane work without destabilizing `main`.

## Decision

Use an Athanor-first automation-backbone program with:

- `main` as the only releasable branch
- `codex/athanor-automation-backbone` as the integration branch
- `codex/athanor-provider-plane`, `codex/athanor-autonomy`, and `codex/athanor-cockpit` as isolated implementation branches/worktrees

Normalize the backbone around four shared record types:

1. execution run record
2. scheduled job record
3. operator stream event
4. quota/lease summary

Expose those records through existing route families instead of adding a parallel API/UI namespace:

- `/v1/subscriptions/summary`
- `/v1/tasks/runs`
- `/v1/tasks/scheduled`
- `/v1/activity/operator-stream`

Proxy them through the dashboard as:

- `/api/subscriptions/summary`
- `/api/workforce/runs`
- `/api/workforce/scheduled`
- `/api/activity/operator-stream`

Use those normalized records to strengthen existing cockpit surfaces rather than create new shells:

- `SubscriptionControlCard` becomes the provider-plane summary surface
- `ResearchJobsCard` surfaces scheduled lanes alongside research jobs
- `UnifiedStream` becomes the operator event feed
- `AgentDetailPanel` surfaces recent provider/execution runs per agent

## Consequences

### Positive

- Cockpit, autonomy, and provider-plane work can converge on one event/run model.
- Existing mounted routes gain deeper runtime truth without route sprawl.
- The dashboard can show lease outcomes, schedule posture, and operator events using stable contracts.
- The worktree program reduces parallel-implementation collisions while keeping `main` clean.

### Negative

- Some existing dashboard fixture and static type lanes still contain pre-existing debt unrelated to this backbone slice.
- The integration worktree may require local dependency setup separate from `C:\\Athanor`.
- Full provider execution adapters and harvesting loops remain later slices on top of this backbone foundation.

## Notes

- Portfolio repos stay maintenance-only during this phase.
- Historical lineage repos remain frozen as reference-only.
- Guardrail remains mandatory before any merge into integration and before integration lands on `main`.
