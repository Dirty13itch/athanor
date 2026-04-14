# Athanor Codex Next Steps

Last updated: 2026-04-06

This file is a short continuity layer for Codex sessions. It supplements `STATUS.md` and the live backlog; it does not replace them.

## Immediate

1. Keep `STATUS.md` as the first current-state source.
2. Keep `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` as the live execution queue.
3. Start new sessions with `python scripts/session_restart_brief.py --refresh` before choosing a lane.
4. Treat publication as a triage task first, not a blind commit:
   - the current working tree is intentionally dirty on `codex/reconciliation-completion`
   - the branch is already pushed, but the large local modified and untracked tranche is not on GitHub yet
   - separate intended publication slices from ambient generated/runtime/workstation churn before any staging
3. Treat the new reconciliation control surface as canonical for cross-repo and side-root work:
   - `config/automation-backbone/reconciliation-source-registry.json`
   - `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
   - `docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md`
   - `docs/operations/ATHANOR-TENANT-QUEUE.md`
   - `docs/operations/ATHANOR-RECONCILIATION-LEDGER.md`
5. Land reconciliation work in phased checkpoints rather than one giant sync dump.
6. Treat `docs/operations/REPO-STRUCTURE-RULES.md` as the durable structure-placement memo; do not reopen top-level folder authority casually, and do not let `services/` or `projects/reports/` quietly grow into shadow authority.

## Next

1. Publication-triage the current dirty tranche by candidate checkpoint slice:
   - control-plane and registry truth
   - agent-runtime and queue truth
   - dashboard/control-surface rebuild
   - gpu-orchestrator and capacity substrate
   - generated reports and ledgers
2. Exclude workstation-local and incidental churn from publication unless explicitly intended:
   - `.letta/`
   - `evals/.letta/`
   - `output/`
   - any other purely local runtime residue
3. Align local Athanor with current `origin/main` before publication work.
4. Harvest `athanor-next` selectively:
   - continuity docs
   - still-useful operator/startup language
   - no regressions against Athanor-native topology-backed scripts
5. Harvest `C:\Reconcile` selectively:
   - GitHub portfolio governance
   - artifact triage decisions that still match current truth
   - reusable reconciliation tooling only if it belongs inside Athanor long-term
6. Move through GitHub repo roles in batches:
   - Batch 1: core and lineage
   - Batch 2: shared-module candidates
   - Batch 3: tenant products
   - Batch 4: archive and low-priority edges

## Avoid

- publishing from stale local history
- treating runtime authority as implementation authority
- reviving `athanor-next`, `C:\Reconcile`, or quarantined clones as active truth
- merging entire side repos when the real need is a narrow extraction
