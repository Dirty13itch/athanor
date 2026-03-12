# Automation Backbone Execution Tracker

This is the implementation-status tracker for the full Athanor automation-backbone program.

Use it with:

- [automation-backbone-master-plan.md](./automation-backbone-master-plan.md)
- [command-hierarchy-governance.md](./command-hierarchy-governance.md)
- [../atlas/COMMAND_HIERARCHY_ATLAS.md](../atlas/COMMAND_HIERARCHY_ATLAS.md)
- [../atlas/MODEL_GOVERNANCE_ATLAS.md](../atlas/MODEL_GOVERNANCE_ATLAS.md)

## Status meanings

- `live`: implemented, mounted, and part of the current runtime or cockpit
- `live_partial`: implemented and useful, but not yet the final finished version
- `configured`: design and config are present, but the recurring loop or operational cadence is not fully active yet
- `planned`: captured in canonical docs, but not yet implemented as a live system behavior

## Backbone status

| Layer | Status | What is true now | What is left |
| --- | --- | --- | --- |
| Canonical guardrail | `live` | completion audit, runtime probe, live smoke, vitest, and Playwright are green from the canonical root | keep green during future merges |
| Command hierarchy | `live` | system map, authority order, rights registry, policy classes, governor posture, and operator stream are live | keep extending operator visibility as new lanes appear |
| Dual-meta routing | `live` | frontier and sovereign meta lanes are explicit in policy classes, system map, and routing helpers | deepen lane selection in more execution paths |
| Content and refusal governance | `live_partial` | policy classes and routing reasons exist | finish more end-to-end sovereign and hybrid flow coverage and operator explanations |
| Governor and capacity posture | `live` | `/v1/governor` and cockpit governor cards are live | add richer time-window and capacity arbitration over more background loops |
| Provider plane visibility | `live` | providers, leases, quotas, execution posture, handoffs, handoff-status counts, and summaries are surfaced | continue direct adapter coverage and reserve-aware harvesting |
| Provider handoff lifecycle | `live_partial` | governed handoff bundles can now issue real leases, persist status, record outcomes, and flow into the run ledger and operator stream | deepen adapter-originated outcome recording and richer artifact lineage |
| Provider direct execution adapters | `live_partial` | execution posture, lease-backed handoffs, and bundle lifecycle are represented in runtime | deepen real adapter execution success paths and fallback bundles |
| Sovereign local meta plane | `live` | command hierarchy, policy classes, workload registry, and system map all treat it as a first-class lane | harden more workload-specific sovereign defaults |
| Local worker plane | `live` | coding, bulk, creative, embedding, and reranker roles are registered and live | continue champion/challenger measurement by workload |
| Judge plane | `live` | judge snapshot, recent verdicts, guardrails, and challenger posture are surfaced | deepen gating on more automated pipelines |
| Model role registry | `live` | canonical model-role registry exists and is surfaced | keep current as champions change |
| Workload class registry | `live` | canonical workload taxonomy exists and is surfaced | expand if new workload families appear |
| Model proving ground | `live` | proving-ground posture, benchmark history, lane coverage, and trigger surface are live | keep adding richer Athanor-native evaluation packs |
| Model intelligence lane | `live` | horizon-scan cadence, challenger queues, next actions, and improvement-cycle evidence are live in runtime snapshots | keep enriching candidate intake, canary promotion, and operator review posture |
| Prompt / policy / contract governance | `live_partial` | command-rights, policy, model-role, workload, proving-ground, constitution, and contract registries are versioned | expand to more prompt, rubric, and contract assets |
| Eval corpus governance | `configured` | proving-ground corpora classes and canonical eval-corpus registry are declared | turn them into fuller governed corpora with version history and more task packs |
| Experiment ledger and provenance | `live_partial` | execution records, verdicts, and governance snapshots exist | expand to deeper artifact lineage across more outputs |
| Orchestrator control stack map | `live` | command hierarchy and runtime atlas map the control stack explicitly | keep runtime docs aligned as new loops are promoted |
| Scheduler and autonomy loops | `live_partial` | scheduling status, research jobs, consolidation, and workplan loops are surfaced | deepen pause/resume, bounded retry, and idempotent background lanes |
| Research jobs | `live` | queued research jobs and execution surfaces exist | mature evals and operator runbooks around them |
| Skills lane | `live` | skills library and stats are surfaced | deepen execution, learning, and review flows |
| Consolidation lane | `live` | consolidation stats and trigger surface exist | mature retention and operator review flows |
| Backup and restore readiness | `live_partial` | critical stores, cadence, recovery order, and non-destructive live restore-drill evidence are operator-visible | deepen from non-destructive rehearsal into fuller restore drills with persisted evidence artifacts |
| Presence-aware autonomy | `live_partial` | manual posture plus automatic dashboard-heartbeat posture are now live; effective presence, signal freshness, and auto/manual precedence are surfaced in the governor snapshot and cockpit | broaden presence inputs beyond dashboard activity and apply posture more deeply across notifications and approvals |
| Sandbox / shadow / canary ladder | `configured` | the canonical release ritual and promotion tiers are now registry-backed | implement runtime promotion tiers and operator controls |
| Economic governance | `live_partial` | reserves, quotas, and provider posture are visible | deepen policy-backed budgeting and downgrade rules |
| Data lifecycle and retention | `configured` | canonical lifecycle classes now exist for runtime, memory, sovereign content, and eval artifacts | implement retention posture in runtime and docs |
| Operator cockpit | `live_partial` | command center, agents, tasks, workplanner, learning/review, and notifications now surface core backbone posture | continue AAA polish, deep-link quality, and richer explanations |
| Operator system map | `live` | command-center system-map card and `/api/system-map` are live | continue simplifying and refining operator comprehension |
| Visual redesign | `planned` | direction is fixed: premium industrial dark, warm core, quiet power, controlled signals | implement the actual token and shell and route redesign |
| Operator runbooks | `live_partial` | canonical runbooks exist, are registry-backed, and surface through operations-readiness snapshots | wire deeper cockpit links and attach live drill evidence |
| Synthetic operator tests | `live_partial` | operator-test registries, runtime snapshots, trigger surfaces, and live restore-drill evidence are active | expand from governance-focused synthetic flows into broader incident, outage, and fallback rehearsals |
| Deprecation and retirement policy | `configured` | canonical retirement stages and governed asset classes now exist | implement retirement handling for models, prompts, policies, and experiments |

## Next implementation frontier

The next high-value engineering work is:

1. finish the provider plane beyond visibility by hardening real adapter execution and adapter-owned outcome recording
2. deepen autonomy loops with richer pause/resume, bounded retries, and stronger background-job lineage
3. move restore posture, release tiers, and retirement policy from registry-backed readiness into live drills and controls
4. expand synthetic operator tests from governance posture into restore, outage, and fallback rehearsals
5. implement the visual redesign and AAA polish pass on the active cockpit routes

## Canonical invariant

Do not treat any of the above as complete if the canonical guardrail is not green from `C:\Athanor`.
