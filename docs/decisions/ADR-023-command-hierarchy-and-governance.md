# ADR-023: Command Hierarchy and Governance

**Date:** 2026-03-12
**Status:** Accepted
**Deciders:** Shaun, Claude

## Context

The earlier Athanor hierarchy was directionally correct but still implied that Claude directly commanded the full runtime. That model is too loose for a system that must:

- stay sovereign when cloud providers refuse or throttle work
- keep constitutional policy above all non-human actors
- expose a legible chain of command in the cockpit
- prevent model lanes from bypassing runtime approval, lease, or schedule control

At the same time, current primary-source agent guidance converges on the same practical pattern:

- start with a strong manager path before adding broad peer-to-peer delegation
- keep tools narrow and non-overlapping
- evaluate the full harness, not only the model
- use layered guardrails and sandboxing

Relevant anchors:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: Beyond permission prompts: making Claude Code more secure and autonomous](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [LangGraph Supervisor reference](https://langchain-ai.github.io/langgraphjs/reference/modules/langgraph-supervisor.html)
- [AutoGen Teams guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)

## Decision

Adopt a governed, manager-first, dual-meta command system.

Canonical authority order:

1. Shaun
2. Constitution + policy registry
3. Athanor governor
4. Meta strategy layer
5. Orchestrator control stack
6. Specialist agents
7. Worker and judge planes
8. Tools and infrastructure

Hard rules:

- The constitution is the highest non-human authority.
- The Athanor governor is the policy and posture authority for routing, pause or resume automation, release tiers, presence posture, and degraded-mode choice; durable work, execution leases, and recurring schedules belong to the canonical task engine, subscription broker, and scheduler.
- Meta lanes may plan, decompose, critique, review, and recommend redirects, but may not directly mutate runtime or bypass governor policy.
- The system keeps two co-equal meta lanes under governor control:
  - frontier cloud meta lane
  - sovereign local meta lane
- Frontier cloud remains the default strategic lane for allowed workloads.
- Sovereign local is mandatory for refusal-sensitive, uncensored, private, or sovereign-only workloads.

## Resulting Model

- Shaun remains final authority.
- Claude remains the named frontier strategic lead, but no longer acts as the sole direct commander of the runtime.
- The governor becomes the runtime posture and fallback authority over the control stack rather than a duplicate durable-task store.
- The orchestrator is explicitly treated as a control stack:
  - server
  - router
  - tasks
  - scheduler
  - workspace / GWT
  - workplanner
  - alerts / escalation
  - subscription broker
  - capacity governor
- Specialist agents stay domain-scoped and tool-bounded.
- Worker lanes remain execution-only.
- Judge lanes remain scoring-only.

## Consequences

### Positive

- The system gains a legible chain of command.
- Cloud capability remains powerful without becoming sovereign dependency.
- Protected workloads can route to a local strategic lane before provider choice.
- Command rights, approvals, fallback, and degraded modes become easier to test and surface.
- The dashboard can explain who decided, which lane ran, and why.

### Negative

- More policy and contract structure must now be maintained explicitly.
- Older docs that describe Claude as direct boss of all local agents must be reconciled.
- The hierarchy now requires live reconciliation across runtime, fixture mode, atlas docs, and cockpit surfaces whenever new command layers are promoted.

## Implementation Notes

- `projects/agents/src/athanor_agents/command_hierarchy.py` is the current runtime source for authority order, rights, policy classes, and system-map snapshots.
- `projects/agents/src/athanor_agents/server.py` now exposes read-only hierarchy/backbone endpoints:
  - `/v1/system-map`
  - `/v1/activity/operator-stream`
  - `/v1/tasks/runs`
  - `/v1/tasks/scheduled`
  - `/v1/subscriptions/summary`
- The dashboard mounts a read-only system-map surface in Command Center and consumes the new hierarchy-aware APIs through existing families.

## Supersedes / Clarifies

- Clarifies the command model implied by [ADR-017-meta-orchestrator.md](./ADR-017-meta-orchestrator.md)
- Extends [ADR-022-subscription-control-layer.md](./ADR-022-subscription-control-layer.md)
- Becomes the authoritative command/governance decision for the automation-backbone phase
