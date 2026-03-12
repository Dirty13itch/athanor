# Automation Backbone Master Plan

This is the canonical future-state plan for Athanor as a governed automation backbone.

It consolidates the command hierarchy, dual-meta model, sovereign-content rules, model-proving-ground program, operator cockpit direction, safety and recovery layers, and the update/evaluation machinery that keeps Athanor current over time.

## Companion docs

Use these together:

- [command-hierarchy-governance.md](./command-hierarchy-governance.md)
- [system-constitution.md](./system-constitution.md)
- [../atlas/COMMAND_HIERARCHY_ATLAS.md](../atlas/COMMAND_HIERARCHY_ATLAS.md)
- [../atlas/MODEL_GOVERNANCE_ATLAS.md](../atlas/MODEL_GOVERNANCE_ATLAS.md)
- [../atlas/OPERATIONS_ATLAS.md](../atlas/OPERATIONS_ATLAS.md)
- [../operations/OPERATOR_RUNBOOKS.md](../operations/OPERATOR_RUNBOOKS.md)
- [automation-backbone-execution-tracker.md](./automation-backbone-execution-tracker.md)

## Current implementation snapshot

| Backbone layer | Current state |
| --- | --- |
| Command hierarchy and governor surfaces | live |
| Dual-meta routing policy classes | live |
| Provider visibility and leasing | live |
| Provider handoff lifecycle and run-ledger integration | live_partial |
| Sovereign local meta path | live |
| Model role/workload registries | live |
| Model proving-ground posture and snapshots | live |
| Continuous model-intelligence cadence | live |
| Operator cockpit integration | live, still expanding |
| Capacity governor posture | live, operator-facing |
| Presence-aware autonomy | live_partial |
| Visual redesign | planned |
| Restore drills | live_partial |
| Operator runbooks | live_partial |

## Plain-language outcome

Athanor should become:

- one governed operating system for work
- one operator cockpit that explains what the system is doing and why
- one dual-meta system with:
  - a frontier cloud lane for best-in-class strategic work when allowed
  - a sovereign local lane for private, uncensored, refusal-sensitive, or cloud-hostile work
- one local worker plane that does the bulk of execution
- one local judge plane that scores outputs, regressions, and promotion candidates
- one model proving ground that continuously measures which models, prompts, policies, and routed pipelines are best for Athanor's own workloads

## System constitution and command hierarchy

Canonical authority order:

1. Shaun
2. Constitution + policy registry
3. Athanor governor
4. Meta strategy layer
5. Orchestrator control stack
6. Specialist agents
7. Worker and judge planes
8. Tools and infrastructure

Hard rule:

- Athanor governs
- cloud supervises when allowed
- sovereign local supervises when cloud is inappropriate
- local workers execute
- local judges score

The constitution is the highest non-human authority. No meta lane, specialist, worker, judge, or tool may override it.

## Orchestrator control stack

The orchestrator is a stack, not a daemon:

- agent server
- router
- task engine
- scheduler
- workspace / GWT
- workplanner
- alerts / escalation
- subscription broker
- capacity governor

The governor is the only layer allowed to:

- create durable tasks
- issue execution leases
- own schedules
- pause or resume automation
- choose degraded mode
- approve low-risk autonomous actions inside policy bounds

Meta lanes may plan, critique, decompose, and review. They may not directly mutate infrastructure, spend premium capacity, or bypass approval policy without the governor.

## Dual-meta model

### Frontier cloud meta lane

Use for:

- architecture planning
- repo-wide planning and critique
- large-context review
- cloud-safe research synthesis
- abstracted planning for hybrid workloads

Default lead:

- Claude

Typical examples:

- Anthropic Claude Code
- OpenAI Codex
- Google Gemini
- Moonshot Kimi
- GLM-compatible premium lanes

### Sovereign local meta lane

Use for:

- private local planning
- uncensored chat
- refusal-sensitive work
- explicit or taboo creative generation
- any workload that should never depend on cloud permission

Default role:

- co-equal strategic lane for protected workloads

## Content and refusal governance

Every task must be classified before lane selection:

- `cloud_safe`
- `private_but_cloud_allowed`
- `hybrid_abstractable`
- `refusal_sensitive`
- `sovereign_only`

Rules:

- `cloud_safe`: cloud or local allowed by workload policy
- `private_but_cloud_allowed`: cloud allowed only within explicit data-boundary policy
- `hybrid_abstractable`: cloud may see only abstracted or redacted structure; raw content stays local
- `refusal_sensitive`: sovereign local planning, execution, and review only
- `sovereign_only`: never leaves the cluster

The cockpit must always show why cloud was allowed, skipped, or abstracted away.

## Supervisor-worker execution model

Each important execution should support:

- one parent supervisory run
- zero or more child worker runs
- zero or one judge run

The system must record:

- which supervisor lane was used
- which worker lane executed
- whether the task used sovereign mode
- what policy class applied
- which judge scored the output
- what artifacts were produced
- what fallback or retry happened

This is the operational form of the rule:

- governor decides
- supervisor plans
- worker executes
- judge scores

## Model role registry

The system now treats model lanes as governed roles, not just endpoint aliases.

Current role families:

- frontier supervisor
- sovereign supervisor
- coding worker
- bulk worker
- creative worker
- judge / verifier
- embedding support
- reranker support
- fallback

These live in:

- `config/automation-backbone/model-role-registry.json`

Every role record must define:

- strengths
- weaknesses
- refusal posture
- privacy suitability
- latency / cost expectations
- workload coverage
- current champion / challenger state

## Workload class registry

The system must choose lanes by workload class, not generic "chat" labels.

Current workload classes include:

- architecture planning
- repo-wide audit
- coding implementation
- code review
- private automation
- research synthesis
- workplan generation
- background bulk transform
- refusal-sensitive creative generation
- explicit dialogue
- briefing / digest generation
- judge verification
- retrieval embedding
- retrieval reranking

These live in:

- `config/automation-backbone/workload-class-registry.json`

Each workload class must define:

- primary supervisor lane
- primary worker lane
- fallback lanes
- allowed cloud posture
- required judge path
- default autonomy level

## Model proving ground

The proving ground is a permanent subsystem, not a one-time benchmark sprint.

It evaluates:

- local models
- cloud supervisors
- judge models
- prompts
- routing policies
- full supervisor-worker pipelines

It measures:

- functional quality
- operational quality
- behavioral quality
- refusal / sovereignty correctness
- latency and throughput
- tool-use success
- correction rate
- operator acceptance
- judge scores

Core assets:

- `config/automation-backbone/model-proving-ground.json`
- `config/automation-backbone/model-intelligence-lane.json`

## Model intelligence lane

The system must continuously look for better models and infrastructure updates.

Default cadence:

- weekly horizon scan
- weekly candidate triage
- monthly champion rebaseline
- urgent event-triggered scan for major releases

It should output:

- candidate intake briefs
- champion / challenger queue
- promotion or retirement recommendations
- "ignore for now" decisions where hype is not relevant to Athanor's workloads

## Prompt, policy, contract, and corpus governance

Prompts, routing rules, approval thresholds, eval rubrics, and subscription policies are production assets.

They need:

- versioning
- rollout and rollback rules
- A/B comparison support
- linkage to runs and outcomes

The system also needs:

- a contract registry for shared record types
- an eval corpus registry for golden tasks and sensitive task packs
- stable baseline versions so regressions can be measured over time

Canonical sources:

- `config/automation-backbone/contract-registry.json`
- `config/automation-backbone/eval-corpus-registry.json`
- `config/automation-backbone/experiment-ledger-policy.json`
- `config/automation-backbone/deprecation-retirement-policy.json`

## Experiment ledger and provenance

Every meaningful output should know:

- which run produced it
- which model, prompt, and policy versions were active
- which lane was local, cloud, or hybrid
- which judge scored it
- whether it was accepted, corrected, retried, or rejected

Every major experiment should record:

- hypothesis
- candidate
- test pack
- result
- decision
- rationale

Canonical source:

- `config/automation-backbone/experiment-ledger-policy.json`

## Capacity governor and time-window choreography

The capacity governor arbitrates:

- GPU contention
- queue depth
- vLLM lanes
- ComfyUI load
- benchmarks and evals
- backups
- indexing
- background loops
- provider quota harvesting

Time-window choreography keeps these from competing destructively:

- backup windows
- consolidation windows
- morning planning windows
- benchmark windows
- heavy creative windows
- low-risk cloud harvest windows
- notification quiet hours

## Autonomy, approvals, and presence-aware operation

Use the existing ladder:

- `A act/log`
- `B act/notify`
- `C propose/wait`
- `D suggest only`

Apply it per agent and per action category.

Presence states should influence autonomy and notification posture:

- at desk
- active in dashboard
- away
- asleep
- phone-only

## Failure, retry, degraded mode, and recovery

The backbone is not complete without explicit recovery behavior for:

- provider lane failure
- local model failure
- Redis/Qdrant/LiteLLM degradation
- scheduler drift
- task worker failure
- judge-plane failure
- backup / restore failure

For each failure class define:

- retry policy
- fallback policy
- operator escalation policy
- pause conditions
- degraded-mode posture

## Shadow, sandbox, canary, production

Every new model, prompt, policy, or automation lane should pass through:

- offline eval
- shadow
- sandbox / rehearsal
- canary
- production

No new automation behavior should jump directly to production.

## Secrets, privacy, and economic governance

Keep secrets out of tracked docs, prompts, and handoff bundles.

The cloud-boundary policy must explicitly govern:

- raw sensitive content
- private documents
- credential-bearing material
- sovereign-only creative content

Economic governance must define:

- premium reserve lanes
- automatic spend lanes
- approval-required spend lanes
- budget downgrade rules
- quota harvesting rules

## Data lifecycle and retention

Every data class must be tagged as one of:

- ephemeral
- operational
- memory-worthy
- archival
- sovereign-only
- eval / training eligible

This applies to:

- conversations
- activity logs
- workspace items
- outputs
- generated media
- eval results
- provider usage logs
- handoff bundles

## Operator cockpit

The cockpit must make the system legible.

Core routes to deepen:

- `/`
- `/agents`
- `/tasks`
- `/workplanner`
- `/notifications`
- `/learning`
- `/personal-data`
- `/chat`

The operator must be able to see:

- who decided
- which lane was used
- why cloud was allowed or skipped
- whether sovereign mode was required
- what ran
- what failed
- what can be retried or paused
- current model-governance and proving-ground posture

## Visual system

The visual direction remains:

- premium industrial dark
- warm core
- quiet power
- controlled signals
- stronger depth and hierarchy

## Backup, restore, and runbooks

The backbone is not complete without:

- verified backup coverage for critical mutable stores
- restore drills for Qdrant, Neo4j, Redis-critical state, and deployment recovery
- operator runbooks for:
  - morning review
  - incident review
  - provider exhaustion
  - stuck automation
  - sovereign routing verification
  - restore drill
  - emergency pause

## Synthetic operator tests

The system should regularly test full operator flows, not just backend APIs:

- approve / reject
- pause / resume
- inspect routed run
- recover stuck queue
- handle provider outage
- handle local lane degradation
- restore from backup

## Deprecation and retirement

The system needs a formal retirement path for:

- models
- prompts
- policies
- routes
- agents
- corpora
- experiments

Retired items should remain as history or reference, but stop competing with active truth.

## Source anchors

- [command-hierarchy-governance.md](./command-hierarchy-governance.md)
- [intelligence-layers.md](./intelligence-layers.md)
- [agent-contracts.md](./agent-contracts.md)
- [../atlas/COMMAND_HIERARCHY_ATLAS.md](../atlas/COMMAND_HIERARCHY_ATLAS.md)
- [../atlas/MODEL_GOVERNANCE_ATLAS.md](../atlas/MODEL_GOVERNANCE_ATLAS.md)
- [automation-backbone-execution-tracker.md](./automation-backbone-execution-tracker.md)
