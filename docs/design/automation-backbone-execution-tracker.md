# Automation Backbone Execution Tracker

This is the implementation-status tracker for the full Athanor automation-backbone program.

Use it with:

- [../archive/design/automation-backbone-master-plan.md](../archive/design/automation-backbone-master-plan.md)
- [command-hierarchy-governance.md](./command-hierarchy-governance.md)

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
| Prompt / policy / contract governance | `live_partial` | command-rights, policy, model-role, workload, proving-ground, constitution, and contract registries are versioned, surfaced in runtime governance snapshots, and linked into command decisions and plan packets | expand to more prompt, rubric, and contract assets and deepen enforcement beyond the current backbone records |
| Eval corpus governance | `live_partial` | governed corpora, sensitivity classes, corpus versions, and proving-ground coverage now surface in runtime and cockpit snapshots | turn them into fuller governed corpora with richer version history and more Athanor-native task packs |
| Experiment ledger and provenance | `live_partial` | execution runs, handoffs, verdicts, command decisions, and proving-ground/governance snapshots now carry richer prompt/policy/corpus lineage and artifact provenance | expand to deeper artifact lineage across more outputs and promotion flows |
| Orchestrator control stack map | `live` | command hierarchy and runtime atlas map the control stack explicitly | keep runtime docs aligned as new loops are promoted |
| Scheduler and autonomy loops | `live_partial` | scheduling status, research jobs, consolidation, and workplan loops are surfaced, and manual scheduled-job execution now routes through governor posture with explicit operator override instead of silently bypassing it | deepen pause/resume, bounded retry, and idempotent background lanes |
| Research jobs | `live` | queued research jobs and execution surfaces exist | mature evals and operator runbooks around them |
| Skills lane | `live` | skills library and stats are surfaced | deepen execution, learning, and review flows |
| Consolidation lane | `live` | consolidation stats and trigger surface exist | mature retention and operator review flows |
| Backup and restore readiness | `live_partial` | critical stores, cadence, recovery order, and non-destructive live restore-drill evidence are operator-visible | deepen from non-destructive rehearsal into fuller restore drills with persisted evidence artifacts |
| Presence-aware autonomy | `live_partial` | manual posture plus automatic dashboard-heartbeat posture are now live; effective presence, signal freshness, and auto/manual precedence are surfaced in the governor snapshot and cockpit | broaden presence inputs beyond dashboard activity and apply posture more deeply across notifications and approvals |
| Sandbox / shadow / canary ladder | `live_partial` | release ritual, promotion tiers, and live promotion-ladder rehearsal evidence are now surfaced together | deepen from rehearsal into stricter runtime promotion controls and richer canary evidence |
| Economic governance | `live_partial` | reserves, quotas, and provider posture are visible | deepen policy-backed budgeting and downgrade rules |
| Data lifecycle and retention | `live_partial` | lifecycle classes are declared and now verified against live runtime runs, eval artifacts, and sovereign routing posture | implement deeper retention enforcement and lifecycle-aware cleanup controls |
| Operator cockpit | `live_partial` | command center, agents, tasks, workplanner, learning/review, and notifications now surface core backbone posture, and the shared left-rail attention ladder is live across desktop/mobile navigation with urgent spectral sweep, action pulse, and watch markers driven by overview state | continue AAA polish, deep-link quality, richer explanations, and broader route attention coverage where the signal source is truly trustworthy |
| Operator system map | `live` | command-center system-map card and `/api/system-map` are live | continue simplifying and refining operator comprehension |
| Visual redesign | `live_partial` | the full staged redesign has been implemented and validated in the canonical repo, rebuilt on WORKSHOP, and smoke-verified live: token layer, shell chrome, shared primitives, core routes, telemetry routes, intelligence/memory/chat routes, and domain/history routes now share one governed visual system; desktop/mobile baselines and full Playwright are green; left-rail operator attention now uses governed urgent/action/watch semantics with acknowledgment decay | close any residual route-level polish found in optional live screenshot review |
| Operator runbooks | `live_partial` | canonical runbooks exist, are registry-backed, surface through operations-readiness snapshots, and now link to evidence-backed rehearsal flows including stuck-queue recovery and incident review | wire deeper cockpit links and broaden live drill evidence |
| Synthetic operator tests | `live_partial` | operator-test registries, runtime snapshots, trigger surfaces, restore-drill evidence, and live stuck-queue/incident-review rehearsals are active | expand into broader outage, fallback, and command-boundary rehearsals |
| Tool-permission governance | `live_partial` | tool-permission registry is now normalized into runtime decisions, surfaced through governor snapshots, and backed by a live synthetic enforcement flow | deepen from governed evaluation into broader runtime enforcement over more execution paths |
| Deprecation and retirement policy | `live_partial` | governed retirement registries, runtime retirement snapshots, advance/hold/rollback controls, synthetic retirement rehearsals, and cockpit/API visibility are now live | deepen retirement handling across prompts, policies, corpora, experiments, and richer operator-led retirement flows |

## Next implementation frontier

The next high-value engineering work is:

1. finish the provider plane beyond visibility by hardening real adapter execution and adapter-owned outcome recording
2. deepen autonomy loops with richer pause/resume, bounded retries, and stronger background-job lineage
3. move restore posture and release tiers from registry-backed readiness into deeper live drills and controls
4. expand synthetic operator tests from restore and queue/incident rehearsals into broader outage, fallback, and command-boundary drills
5. continue the visual redesign with route-by-route polish, chart harmonization, and visual-baseline refinement on the active cockpit routes

## Canonical invariant

Do not treat any of the above as complete if the canonical guardrail is not green from `C:\Athanor`.
