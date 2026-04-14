# Athanor Ralph-Loop Program

Source of truth: `config/automation-backbone/completion-program-registry.json`, `config/automation-backbone/program-operating-system.json`, `config/automation-backbone/autonomy-activation-registry.json`, `projects/agents/config/subscription-routing-policy.yaml`, `reports/ralph-loop/latest.json`, `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`
Validated against registry version: `completion-program-registry.json@2026-04-13.0`, `program-operating-system.json@2026-03-25.1`, `autonomy-activation-registry.json@2026-04-02.4`
Mutable facts policy: runtime truth outranks stale narrative, registry truth outranks helper prose, and the Ralph-loop report is the live execution surface while this document records the standing contract.

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

The live dispatch surface is the ranked autonomous queue in `reports/ralph-loop/latest.json`, not the safe-surface queue alone.
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

The Ralph loop is healthy when:
- every open discrepancy is classified into an explicit workstream state
- no known runtime drift exists without either a packet or an explicit repo-truth correction
- no known source or portfolio ambiguity lacks a disposition
- no active provider lane is ordinary routing without both config and observation
- status docs, backlog, registry truth, and runtime evidence do not contradict each other

The Ralph report now also carries `reconciliation_end_state`, which mirrors the machine-readable exit-gate posture from `completion-program-registry.json` and tracks the current clean-cycle count for steady-state eligibility.
