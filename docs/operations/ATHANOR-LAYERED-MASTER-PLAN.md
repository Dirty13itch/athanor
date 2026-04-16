# Athanor Layered Master Plan

This document is the canonical plan-of-plans for Athanor. It routes operators and agents to the right authority layer without duplicating volatile queue state.

## Layer Map

### 1. Live execution

- Primary surfaces:
  - `STATUS.md`
  - `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
  - `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
  - `reports/ralph-loop/latest.json`
  - `config/automation-backbone/completion-program-registry.json`
- Ownership:
  - current work ordering
  - publication debt posture
  - recovery drill due state
  - adopted-system follow-through

### 2. Build and promotion

- Primary surfaces:
  - `C:/athanor-devstack/STATUS.md`
  - `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`
  - `C:/athanor-devstack/reports/master-atlas/latest.json`
  - `C:/athanor-devstack/configs/devstack-capability-lane-registry.json`
  - `C:/athanor-devstack/docs/promotion-packets/`
- Ownership:
  - concept, prototype, and proved capability work
  - promotion packets and shadow evidence
  - forge queue ordering

### 3. Ecosystem and tenant governance

- Primary surfaces:
  - `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
  - `docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md`
  - `docs/operations/ATHANOR-TENANT-QUEUE.md`
  - `config/automation-backbone/project-packet-registry.json`
  - `config/automation-backbone/reconciliation-source-registry.json`
- Ownership:
  - repo and tenant classification
  - execution modes
  - extraction boundaries

### 4. Codex/operator control plane

- Primary surfaces:
  - `C:/Codex System Config/STATUS.md`
  - `C:/Codex System Config/docs/CORE-ROLLOUT-STATUS.md`
  - `C:/Codex System Config/docs/CODEX-NEXT-STEPS.md`
  - `C:/Codex System Config/docs/WORKTREE-LANES-LATEST.md`
- Ownership:
  - machine and worktree hygiene
  - rollout audits
  - WSL-first operator posture

### 5. Strategic reservoir

- Primary surfaces:
  - `C:/athanor-devstack/MASTER-PLAN.md`
  - bounded `designs/`
  - bounded `research/`
- Ownership:
  - long-horizon intent only
  - no live queue authority

## Arbitration

1. Runtime breakage, validator red, and explicit runtime-ownership drift outrank everything.
2. Athanor adopted-system work outranks devstack work when both touch the same capability.
3. Publication debt outranks new pilot or strategic expansion once threshold is exceeded.
4. Devstack leads only for `concept`, `prototype`, and `proved` capabilities with no adopted-system blocker.
5. Ecosystem and tenant work enters the live queue only through explicit registry-backed or packet-backed reopening.
6. Codex/operator control-plane contradictions outrank optional pilot breadth and optional tenant work.
7. Strategic reservoir docs never arbitrate live queue state.

## Control Contracts

- Execution authority is governed by `config/automation-backbone/execution-lease-policy.json`.
- Operator posture is governed by `config/automation-backbone/operator-mode-policy.json`.
- Sensitive handling rules are governed by `config/automation-backbone/data-handling-policy.json`.
- Retention and archive rules are governed by `config/automation-backbone/retention-policy-registry.json`.
- Commitment, externalization, and follow-through are governed by `config/automation-backbone/commitment-governance.json`.
- Assumption, inference, and supersession are governed by `config/automation-backbone/assumption-governance.json`.
- Specialist review gates are governed by `config/automation-backbone/specialist-review-gates.json`.
- Party, entity, and account boundaries are governed by `config/automation-backbone/party-boundary-registry.json` together with `config/automation-backbone/project-packet-registry.json`.
- Canonical vocabulary and alias control are governed by `config/automation-backbone/canonical-vocabulary-registry.json`.
- Protocol, telemetry, session resumption, retry/expiry, and portability interop are governed by `config/automation-backbone/protocol-interop-registry.json`.
- Compatibility shims must be explicit, owned, and expiring under `config/automation-backbone/compatibility-alias-policy.json`.
- Architecture freeze and rewrite-budget discipline are governed by `config/automation-backbone/architecture-freeze-policy.json`.
- Document volatility, ownership, and allowed content classes are governed by `config/automation-backbone/docs-lifecycle-registry.json` and rendered in `docs/operations/SURFACE-OWNER-MATRIX.md`.
- Publication provenance and debt posture are rendered in `docs/operations/PUBLICATION-PROVENANCE-REPORT.md`.

## Finish Line

The planning system is complete only when:

- live execution truth is coherent
- build and promotion truth is coherent
- ecosystem classifications and execution modes are frozen
- Codex/operator control-plane truth is accurate
- publication debt is explicit and governable
- anti-spin and anti-limbo rules are enforced
- sensitive data handling and retention are governed end to end
- external commitments are typed, reviewable, and closed with proof
- inferred or assumed claims cannot masquerade as observed truth
- specialist-required domains cannot externalize without review evidence
- party, entity, and account boundaries are machine-readable on governed projects
- compatibility aliases are explicit, owned, and expiring
- architecture-freeze gates block speculative canon rewrites while publication debt is blocking
- recovery drills are current
- no active-looking ghost control surfaces remain
- strategic documents cannot impersonate the live queue

## Read Rules

- Do not duplicate live queue state here.
- Do not narrate packet readiness or pilot posture here.
- Use this file to route to the right authority layer, not to summarize every moving part.
