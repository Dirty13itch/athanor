# Athanor Project

## Purpose

Athanor is Shaun's sovereign local AI system: control plane, operator dashboard, agent runtime, knowledge layer, and the supporting infrastructure for personal, professional, and creative work.

This repo is the implementation authority for that system. It is not a generic homelab repo and it is not the runtime authority.

## Truth Order

Use this order when reorienting:
1. `STATUS.md`
2. `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
3. targeted live checks and generated operations reports
4. `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
5. `docs/operations/REPO-STRUCTURE-RULES.md` for file placement and cleanup decisions
6. `config/automation-backbone`
7. historical or reference-only material

Runtime truth and current registry truth outrank memory and historical prose when they disagree.

For a fast re-entry into the live system, start with:
- `python scripts/session_restart_brief.py --refresh`

## Current Program Boundary

The active meta-program is full reconciliation and ecosystem normalization:
- `C:\Athanor` is the only implementation-authority root
- GitHub `Dirty13itch/athanor` `origin/main` is the only remote mainline
- `/home/shaun/repos/athanor` on `DEV` remains runtime authority
- `C:\athanor-devstack` is the build-system lane for future Athanor capabilities and promotions must land through the capability-adoption registry plus a promotion packet instead of narrative merge
- `athanor-next` and `C:\Reconcile` are harvest lanes, not competing truth
- the broader Dirty13itch GitHub portfolio is governed as part of the Athanor ecosystem, not merged blindly into core

Use these control artifacts for that work:
- `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
- `docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`
- `docs/operations/ATHANOR-RECONCILIATION-LEDGER.md`

## Structure Invariants

Use these as the default structure rules:
- `config/automation-backbone/` is the only mutable control-plane truth layer.
- `projects/*` is where first-class implementation runtimes and products belong.
- `reports/` is the generated machine-truth sink.
- `docs/operations/` is the operator-facing narrative layer over current truth.
- `services/` is transitional and should be treated as no-growth unless a deliberate migration decision says otherwise.
- `projects/reports/` is a compatibility shim, not a canonical reports root.

For the deeper keep or separate or transitional decisions, use:
- `docs/operations/REPO-STRUCTURE-RULES.md`

## Required Live-Check Surfaces

- generated operations reports under `docs/operations`
- cluster and service probes owned by current runbooks and scripts
- VAULT operator access through `python C:\Athanor\scripts\vault-ssh.py`

## Success

- one implementation authority
- one clear publication line
- runtime authority tracked explicitly without polluting code authority
- devstack work graduates through explicit promotion instead of shadow authority
- side roots harvested selectively instead of merged wholesale
- portfolio repos classified into core, shared-module, tenant, lineage, operator-tooling, reference, or archive without ambiguity

## Failure

- stale narrative docs outrank current status or runtime evidence
- side roots or product repos compete with Athanor core
- portfolio repos remain in an ambiguous “important maybe” state
- generic startup scaffolding overrides Athanor-native truth
