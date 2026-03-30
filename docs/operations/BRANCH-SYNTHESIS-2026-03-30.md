# Athanor Branch Synthesis 2026-03-30

## Intent

This document records the active Athanor-core branch synthesis pass. It exists because the repo accumulated many tranche and worktree branches, but only a subset represent the current Athanor system integration train.

The synthesis target is `main` plus the unmerged March 29-30, 2026 Athanor-core integration family. Historical and product-side branches are not automatic merge targets.

## Branch Classes

### Integrate First

- `codex/main-intake-20260329`
- `codex/main-command-center-ia`
- `codex/main-control-plane`
- `codex/main-runtime-deploy`
- `codex/main-truth-backbone`
- `codex/main-maturity-ci`
- `codex/main-front-door-cleanup`
- `codex/main-integration-intake-20260330`

### Selective Follow-On

- `codex/extract-service-contract-harness`
- `codex/finish-service-contract-runtime`
- `codex/finish-service-contract-scripts-v2`
- `codex/finish-truth-tooling`
- `codex/finish-agents-control-plane`
- `codex/finish-agents-provider-autonomy`
- `codex/finish-agents-readiness-v1`
- `codex/finish-agents-scheduler-hardening-v1`
- `codex/finish-dashboard-api-v2`
- `codex/finish-dashboard-operator-session`
- `codex/finish-dashboard-terminal-v2`
- `codex/finish-dashboard-workforce-actions-v1`
- `codex/finish-subscriptions-guards-v1`
- `codex/finish-governor-action-hardening-v1`
- `codex/finish-docs-authority-v1`
- `codex/finish-runtime-python-v1`
- `codex/finish-runtime-shell-v1`
- `codex/finish-front-door-truth-v1`
- `codex/finish-atlas-prune-v2`
- `codex/finish-prune-drop-v1`

### Salvage Only

- `codex/dev-ccr-provisioning`
- `codex/full-tree-sync-20260321`
- `codex/backbone-wip-sync-20260313`
- `codex/athanor-automation-backbone`
- `claude/hopeful-elgamal`

### Prune Candidates After Synthesis

- merged `codex/main-*` branches
- merged `codex/finish-*` branches
- `codex/review-bundle-intake`
- merged `worktree-agent-*` branches

## Execution Order

1. Start from clean `main`.
2. Integrate the `codex/main-*` family in dependency-aware order.
3. Validate the repo.
4. Layer only the selective follow-on branches whose delta is still missing.
5. Re-validate after each tranche.
6. Produce a keep, salvage, prune matrix once the synthesis lane stabilizes.

## Boundaries

- Focus on Athanor system core, not downstream product branches.
- Do not merge stale historical branches wholesale.
- Preserve runtime-approval boundaries; this lane is implementation-authority synthesis only.
