# Command Hierarchy and Governance

This document is the design-level explanation of how Athanor should make decisions, route work, and preserve sovereignty.

It is the full design companion to [ADR-023](../decisions/ADR-023-command-hierarchy-and-governance.md).

## Plain-language model

In plain English:

- Shaun owns the system.
- The constitution sets hard limits.
- Athanor governs runtime decisions.
- Claude leads the frontier cloud strategy lane.
- A sovereign local strategy lane handles protected work and is now part of the live command path for refusal-sensitive and sovereign-only routing.
- Specialist agents execute bounded domain work.
- Local worker lanes do most of the actual execution.
- Local judge lanes score quality and promotion safety.

That means Athanor is not:

- a flat swarm
- a Claude-only hierarchy
- a browser-driven orchestration layer

It is a governed system with one runtime commander and two strategic lanes.

## Canonical authority order

1. Shaun
2. Constitution + policy registry
3. Athanor governor
4. Meta strategy layer
5. Orchestrator control stack
6. Specialist agents
7. Worker / judge planes
8. Tools and infrastructure

## Dual-meta model

The system keeps two strategic lanes under the governor:

### Frontier cloud meta lane

Purpose:

- architecture
- large-context planning
- critique
- review
- broad decomposition for allowed workloads

Default lead:

- Claude

Typical examples:

- Anthropic Claude
- OpenAI Codex
- Google Gemini
- other frontier-capable subscription lanes as policy allows

### Sovereign local meta lane

Purpose:

- private planning
- refusal-sensitive work
- uncensored chat
- taboo or explicit creative work
- cloud-hostile domains

Typical examples:

- best local reasoning lane
- best local coding lane
- local uncensored lane

## Policy classes

The governor chooses a policy class before provider selection:

| Policy class | Cloud allowed | Sovereign required | Meaning |
| --- | --- | --- | --- |
| `cloud_safe` | yes | no | ordinary allowed work |
| `private_but_cloud_allowed` | yes | no | private work allowed in cloud only if policy permits |
| `hybrid_abstractable` | yes | yes | cloud sees abstracted structure, raw content stays local |
| `refusal_sensitive` | no | yes | likely provider-refused or fragile content |
| `sovereign_only` | no | yes | never leaves the cluster |

## Manager-first flow

Default flow:

`operator -> governor -> selected meta lane -> control stack -> specialists/workers -> judge -> operator surfaces`

Why this is the default:

- it keeps the system legible
- it keeps rights centralized
- it prevents agents from inventing their own authority
- it matches current best-practice guidance to start with a strong manager path before broad peer delegation

Decentralized handoffs are allowed only for bounded cases:

- conversation triage
- specialist takeover of a narrow task
- breadth-first research or synthesis

## Rights matrix

| Layer | Allowed | Forbidden |
| --- | --- | --- |
| Shaun | approvals, overrides, policy change, destructive authorization | none |
| Constitution + policy | hard-block, soft-block, approval class definition | direct runtime mutation |
| Governor | routing, durable tasks, leases, schedules, fallback, low-risk automation control | overriding constitution |
| Meta lanes | planning, review, critique, decomposition, redirects | direct tool use, lease issuance, schedule ownership |
| Specialists | scoped execution | self-expanding authority |
| Workers | generation and execution | approvals, scheduling, routing |
| Judges | scoring and gating | production mutation |
| Tools / infra | serve requests | discretionary decision-making |

## Orchestrator control stack

The orchestrator is a stack, not a single daemon:

- agent server
- router
- task engine
- scheduler
- workspace / GWT
- workplanner
- alerts / escalation
- subscription broker
- capacity governor

### What each sublayer does

- `server`: runtime boundary and API front door
- `router`: workload triage and lane selection hints
- `tasks`: durable execution and approvals
- `scheduler`: recurring work and timing
- `workspace`: shared attention and broadcast
- `workplanner`: goal-to-work decomposition
- `alerts`: operator escalation and notification posture
- `subscription broker`: provider leasing and cloud-boundary enforcement
- `capacity governor`: live arbitration posture for GPU, queue, benchmark, and provider-reserve contention

## Supervisor-worker rule

Hard rule:

- Athanor governs
- cloud supervises when allowed
- local sovereign supervises when cloud is inappropriate
- local workers execute
- local judges score

Every important run should eventually support:

- one parent supervisory run
- zero or more child worker runs
- zero or one judge run

## Operator visibility requirements

The cockpit must show:

- who decided
- which meta lane was used
- whether sovereign mode was required
- which worker lane executed
- whether a judge scored the result
- why cloud was skipped or allowed

This is why the command-center system map is required.

## Evaluation and safety implications

The system should not only evaluate models. It should evaluate the whole command harness:

- correct lane selection
- refusal/private routing correctness
- approval posture
- bounded retries
- fallback behavior
- command-rights violations

Boundary enforcement rules:

- meta lanes do not execute tools directly
- execution lanes remain sandboxed
- cloud handoff bundles never include sovereign-only raw content
- judge failure downgrades automation confidence
- frontier failure falls back to sovereign local when possible

## Research anchors

This design follows the practical overlap in current primary-source agent guidance:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: Beyond permission prompts: making Claude Code more secure and autonomous](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [LangGraph Supervisor reference](https://langchain-ai.github.io/langgraphjs/reference/modules/langgraph-supervisor.html)
- [AutoGen Teams guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)
