# Athanor Ralph-Loop Program

Source of truth: `config/automation-backbone/completion-program-registry.json`, `config/automation-backbone/program-operating-system.json`, `config/automation-backbone/autonomy-activation-registry.json`, `projects/agents/config/subscription-routing-policy.yaml`, `reports/ralph-loop/latest.json`
Validated against registry version: `completion-program-registry.json@2026-04-07.6`, `program-operating-system.json@2026-03-25.1`, `autonomy-activation-registry.json@2026-04-02.4`
Mutable facts policy: runtime truth outranks stale narrative, registry truth outranks helper prose, and the Ralph-loop report is the live execution surface while this document records the standing contract.

Sources:
- `config/automation-backbone/completion-program-registry.json`
- `config/automation-backbone/program-operating-system.json`
- `config/automation-backbone/autonomy-activation-registry.json`
- `projects/agents/config/subscription-routing-policy.yaml`
- `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`

Versions:
- `completion-program-registry.json`: `2026-04-07.6`
- `program-operating-system.json`: `2026-03-25.1`
- `autonomy-activation-registry.json`: `2026-04-02.4`

Last updated: 2026-04-07

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

## Loop Families

### Governor and Scheduling

Wake on cadence, material drift, or completion of another loop and choose the highest-leverage eligible loop family.

Priority order:
1. security and auth drift
2. control-plane truth drift
3. repo contract failures
4. topology and runtime drift
5. productization and tenant follow-through

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

Promote completed work into durable truth in bounded checkpoints:
1. control-plane and truth-layer changes
2. verification hardening
3. source or tenant replay landings
4. runtime packet and report closure
5. freeze, prune, and archive follow-through

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
- Weak-evidence or governed-handoff providers remain excluded from ordinary auto-routing until catalog-backed evidence promotes them.

## Acceptance

The Ralph loop is healthy when:
- every open discrepancy is classified into an explicit workstream state
- no known runtime drift exists without either a packet or an explicit repo-truth correction
- no known source or portfolio ambiguity lacks a disposition
- no active provider lane is ordinary routing without both config and observation
- status docs, backlog, registry truth, and runtime evidence do not contradict each other
