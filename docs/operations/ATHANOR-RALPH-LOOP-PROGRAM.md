# Athanor Ralph-Loop Program

Source of truth: `config/automation-backbone/completion-program-registry.json`, `config/automation-backbone/program-operating-system.json`, `config/automation-backbone/autonomy-activation-registry.json`, `projects/agents/config/subscription-routing-policy.yaml`, `reports/ralph-loop/latest.json`, `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`
Validated against registry version: `completion-program-registry.json@2026-04-13.0`, `program-operating-system.json@2026-03-25.1`, `autonomy-activation-registry.json@2026-04-02.4`
Mutable facts policy: runtime truth outranks stale narrative, registry truth outranks helper prose, and the Ralph-loop report is the current execution surface while this document records the contract snapshot.

Sources:
- `config/automation-backbone/completion-program-registry.json`
- `config/automation-backbone/program-operating-system.json`
- `config/automation-backbone/autonomy-activation-registry.json`
- `projects/agents/config/subscription-routing-policy.yaml`
- `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`

Versions:
- `completion-program-registry.json`: `2026-04-13.0`
- `program-operating-system.json`: `2026-03-25.1`
- `autonomy-activation-registry.json`: `2026-04-02.4`

Last updated: 2026-04-12

## Purpose

The Ralph loop is Athanor's continuous autonomous control system for truth convergence and completion work.

It is not a second planning framework. It is the recurring execution layer that sits on top of the existing:
- completion program registry
- program operating system cadence and role model
- autonomy activation scope and approval gates
- routing policy and provider posture
- backlog and status truth

The live controller is `scripts/run_ralph_loop_pass.py`.
The live artifact is `reports/ralph-loop/latest.json`.
The standard source-truth refresh bundle is `python scripts/refresh_validation_publication_loop.py`.
Use `python scripts/preflight_burn_class.py <burn_class_id> --json` when the next unblocked tranche is a burn-class lane and the operator or loop needs a compact queue/capacity preflight.
The standard refresh bundle now writes `reports/truth-inventory/next-rotation-preflight.json` so the on-deck burn-class handoff is visible as a live artifact instead of only a command hint.
The live continuity artifact is `reports/truth-inventory/ralph-continuity-state.json`.
The live governed-dispatch artifact is `reports/truth-inventory/governed-dispatch-state.json`.
The reconciliation closure contract it mirrors is `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`.

## Loop Families

### Governor and Scheduling

Wake on cadence, material drift, or completion of another loop and choose the highest-leverage eligible loop family.

Priority order:
1. provider and auth drift that blocks routing elasticity
2. capacity-truth and dispatch-truth drift
3. promotion-wave closure for force-multiplier lanes
4. failing evals, validators, and repo contract failures
5. repo-safe system hardening and tenant follow-through

The current dispatch surface is the ranked autonomous queue in `reports/ralph-loop/latest.json`, not the safe-surface queue alone.
Safe-surface remains one input, but the loop now ranks work from live workstream truth, provider-gate posture, and safe-surface state together.
The governed-dispatch claim is also persisted separately in `reports/truth-inventory/governed-dispatch-state.json` so the active self-improvement item has a durable machine-readable execution surface without pretending that the separate safe-surface executor has already started a run.

### Evidence Refresh

Refresh:
- `scripts/collect_truth_inventory.py`
- `scripts/run_contract_healer.py`
- `scripts/sync_github_portfolio_registry.py`
- `scripts/discover_reconciliation_sources.py`
- `scripts/generate_tenant_family_audit.py`
- packet/report generators whose source evidence changed

No classification or publication should proceed on stale evidence unless the lane is explicitly blocked on an external dependency.

### Classification and Backlog

Force every open discrepancy into one governed bucket:
- repo-authority drift
- governed runtime drift
- provider and secret remediation
- portfolio or tenant or source reconciliation
- archive, prune, or freeze follow-through
- external dependency or approval block

Nothing reviewed may remain in a `maybe important` state.

### Repo-safe Repair Planning

Advance only implementation-authority work:
- registry normalization
- validators and generators
- packet generation
- startup and status truth
- shared extraction and tenant follow-through
- prune and archive discipline

This lane stays autonomous only while it remains inside `C:\Athanor` and inside the standing approval rules.

## Ranked Autonomous Queue

Each ranked item now carries:
- value class
- risk class
- approved mutation class
- preferred lane family
- fallback lane family
- proof command or eval surface
- closure rule

Dispatch readiness now follows the ranked autonomous queue for approved work classes.
The provider gate still matters, but once turnover-critical providers are proven it becomes an advisory elasticity surface rather than a reason to shut down local-safe self-improvement lanes.
Workstreams in `completed` or `steady_state_monitoring` execution state stay visible in the Ralph report for auditability, but they are excluded from the ranked autonomous queue until fresh drift reopens them.
When convergence pushes most legacy workstreams into `steady_state_monitoring`, the next compounding tranche must be registered explicitly in `completion-program-registry.json` rather than assumed to emerge from safe-surface residue or historical chat memory.

### Governed Runtime Packets

This loop never improvises host mutation.

Every runtime discrepancy must become exactly one of:
- repo truth correction
- confirmed runtime drift with packet
- `ready_for_operator_approval`
- `external_dependency_blocked`
- `executed_and_pending_reprobe`

Approval gates still apply to:
- runtime mutations
- VAULT LiteLLM config or env changes
- database schema changes
- systemd, cron, or host reconfiguration

### Publication and Freeze

Promote completed work into durable truth in bounded checkpoints.

The legacy reconciliation checkpoints remain in `completion-program-registry.json` `checkpoints`, but the active publication order now lives in `completion-program-registry.json` `publication_slices`.

Follow the machine-readable publication-slice order instead of batching one large sync.

### Steady-state Maintenance

Once active debt is reduced, the Ralph loop continues as the permanent maintenance layer:
- daily health, auth drift, backlog, cleanup posture
- twice-weekly subsystem lens audits
- weekly architecture, portfolio, dependency, and docs-freshness review
- biweekly maturity review
- monthly security, recovery, topology, and artifact debt review
- quarterly reset and dead-system removal

## Current Contract

- `C:\Athanor` remains implementation authority.
- `/home/shaun/repos/athanor` on `DEV` remains runtime authority until the governed sync lane closes.
- Full-system autonomy remains active through `full_system_phase_3`.
- Runtime mutations remain approval-gated even inside full-system autonomy.
- Weak-evidence, optional-elasticity-demoted, or governed-handoff providers remain excluded from ordinary auto-routing until catalog-backed evidence promotes them.

## Acceptance

## Continuity Rule

Ralph continues until a typed brake, not until a green check.

A validator-green pass only means the next tranche is eligible to run. It is not the stop condition.

The loop keeps two concepts separate at all times:
- `selected_workstream` for the strategic highest-leverage lane
- `active_claim_task` for the concrete tranche currently being claimed or handed off

Once continuity suppression removes the currently-spinning workstreams, `cash_now` deferred publication families preempt generic burn-class lanes. That keeps the next autonomous pass anchored on a concrete repo tranche instead of drifting into abstract capacity posture.
Dispatch and Work-Economy Closure reopens only on dispatch-scoped repo delta, Validation and Publication reopens on any material repo delta, and verified repo-side no-delta must rotate to the next eligible tranche instead of reclaiming the same workstream.

The only valid stop states are:
- `approval_required`
- `external_block`
- `destructive_ambiguity`
- `queue_exhausted`

The durable anti-spin and stop-state memory lives in `reports/truth-inventory/ralph-continuity-state.json`.

The Ralph loop is healthy when:
- every open discrepancy is classified into an explicit workstream state
- no known runtime drift exists without either a packet or an explicit repo-truth correction
- no known source or portfolio ambiguity lacks a disposition
- no active provider lane is ordinary routing without both config and observation
- status docs, backlog, registry truth, and runtime evidence do not contradict each other

The Ralph report now also carries `reconciliation_end_state`, which mirrors the machine-readable exit-gate posture from `completion-program-registry.json` and tracks the current clean-cycle count for steady-state eligibility.

The Ralph control plane now also materializes two finish artifacts:
- `reports/truth-inventory/finish-scoreboard.json` for repo-safe closure posture, deferred-family counts, and typed-brake status
- `reports/truth-inventory/runtime-packet-inbox.json` for approval-gated runtime packet readiness

Steady-state doctrine is split intentionally:
- always refresh Ralph, continuity state, and the truth/report surfaces needed to keep queue truth honest
- refresh publication triage, deferred-family counts, and burn-class preflight when source drift changes them
- keep runtime host mutations, secret/config mutation on live nodes, and destructive cleanup approval-gated forever

## Executive Brief Contract

Every material tranche must also materialize a COO brief in Ralph state and render it in the restart helper.

The required sections are:
- `program_state`
- `landed_or_delta`
- `proof`
- `risks`
- `delegation`
- `next_moves`
- `decision_needed`

Ownership stays split by role:
- `completion-program-registry.json` owns the machine policy
- `run_ralph_loop_pass.py` owns the generated executive state schema
- `session_restart_brief.py` owns the human-facing condensation
- this doc owns the doctrine
- `SESSION-RESTART-RUNBOOK.md` owns operator consumption

Green validation is proof, not a handoff. A material tranche is not fully landed until the executive brief is also current.
