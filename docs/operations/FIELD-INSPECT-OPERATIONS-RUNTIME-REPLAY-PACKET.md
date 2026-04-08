# Field Inspect Operations Runtime Replay Packet

Source of truth:
- `reports/reconciliation/field-inspect-operations-runtime-replay-latest.json`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`
- `docs/operations/ATHANOR-RECONCILIATION-LEDGER.md`

## Purpose

Turn `C:\Field Inspect-operations-runtime` from a reviewed sibling lane into a bounded selective replay packet against the primary root at `C:\Field Inspect`.

This packet exists because the lane still carries real product value, but direct branch replay is unsafe.

## Current Facts

- Regenerate `reports/reconciliation/field-inspect-operations-runtime-replay-latest.json` before execution. The report owns the live execution posture; this prose only explains how to use it.
- Primary root: `C:\Field Inspect`
- Primary branch: `codex/perpetual-coo-loop`
- Replay lane: `codex/reconcile-operations-runtime`
- Replay lane divergence: `+26` ahead over the current primary root lineage
- The generated replay report now declares an explicit `execution_posture`:
  - `ready_for_safe_replay` when `overlap_count` is `0`
  - `ready_for_safe_runtime_only` when overlap still exists, but `safe_runtime_overlap_count` is `0` and the remaining overlap is quarantined to shared-project or docs/meta surfaces
  - `blocked_by_overlap` only when the report still finds overlap inside the safe operations-runtime tranche itself
- Read `execution_posture`, `dirty_primary_count`, and `overlap_count` directly from the generated report at execution time. Do not hardcode those values in follow-up docs or branch notes.
- Even when `execution_posture` is ready, the shared-project and report-delivery surfaces remain a coordinated second tranche. They are not promoted into the first landing just because the current overlap set is empty.
- A dedicated review worktree now exists at `C:\Field Inspect-ops-safe-review` on branch `codex/replay-operations-runtime-safe`, and that review branch already passes `npm run typecheck` plus the targeted replay tests without touching the dirty primary root.
- The safe operations-runtime tranche plus its minimum support set was replayed into `C:\Field Inspect` on 2026-04-07, and the packet validation commands now pass in the authority root as well.

The replay lane therefore stays valid, but it must be applied as file-bucketed cherry-picks, not as a wholesale branch merge.

## Replay Buckets

### 1. Safe Operations Runtime Replay

These are the first tranche and the reason this lane remains active:

- `src/app/(dashboard)/operations/*`
- `src/app/api/work-intake/*`
- `src/app/api/site-visits/*`
- `src/components/dispatch/*`
- `src/components/operations/*`
- `src/components/schedules/*`
- operations-focused libs and tests:
  - `src/lib/operations-*`
  - `src/lib/ops-task-*`
  - `src/lib/owner-queue-state.ts`
  - `src/lib/tomorrow-prep.ts`
  - `src/lib/visit-execution-state.ts`
  - `src/lib/work-intake-*`
  - `src/lib/finance-closure-state.ts`

Why this bucket survives:
- it adds real operations dashboards, dispatch surfaces, work-intake flows, and state logic
- it is the only sibling lane with broad product-code value still worth replaying

### 2. Shared Project Follow-Through Hold

Do not include these in the first replay tranche:

- `src/app/(dashboard)/projects/*`
- `src/app/api/shared-projects/*`
- `src/components/projects/*`
- `src/components/reports/*`
- `src/app/shared-reports/*`
- `src/lib/shared-project*`
- `src/lib/report-*`
- `src/lib/shared-report-links.ts`

Reason:
- these paths sit on the shared-project and report-delivery surface, which needs one coordinated review and landing
- even when the current overlap set is empty, this cluster should still be treated as a second tranche instead of being mixed into the first operations landing

### 3. Secondary Cross-Surface Review

These should be reviewed after the safe operations replay but before any archive/freeze decision:

- `src/app/api/admin/test-email/*`
- `src/app/api/comments/*`
- `src/app/api/organization/members/*`
- `src/app/api/search/*`
- `src/app/(dashboard)/reports/*`
- `src/app/(dashboard)/settings/*`
- `src/components/comments/*`
- `src/components/layout/*`
- `src/components/settings/*`
- cross-surface libs:
  - `src/lib/google-report-jobs.ts`
  - `src/lib/observability-proof.ts`
  - `src/lib/office-handoff-acceptance.ts`
  - `src/lib/validators.ts`

Reason:
- these are real code changes, but they are not the core reason the lane survives
- they should land only if they still match the primary product direction after the safe operations replay

### 4. Docs And Meta Reference

Do not treat these as first-pass replay material:

- `.gitattributes`
- `docs/README.md`
- `docs/engineering/*`
- `package-lock.json`

Reason:
- these are reference, release, or documentation artifacts, not the first replay objective
- the product code should land before docs and lockfile churn are reconsidered
- they stay blocked from early replay even when the current overlap set is empty

## Execution Rules

- Do not merge `codex/reconcile-operations-runtime` wholesale.
- Regenerate the replay report immediately before execution and honor its `execution_posture`.
- Start with the safe operations-runtime tranche when the report says `ready_for_safe_replay` or `ready_for_safe_runtime_only`.
- Keep every shared-project and report-delivery file in a coordinated second tranche, regardless of whether the current overlap count is zero.
- Build the replay as a dedicated review branch or worktree from the current primary root.
- Treat this packet as product-tenant execution guidance for `Field Inspect`, not as Athanor-core import work.

## Targeted Validation

Run these in `C:\Field Inspect` after the safe operations-runtime tranche is replayed:

```powershell
npm run typecheck
npm run test:run -- src/lib/__tests__/operations-assignment-guidance.test.ts src/lib/__tests__/operations-orchestration.test.ts src/components/dispatch/__tests__/operations-work-intake-board.test.tsx src/components/operations/today/__tests__/today-view.test.tsx src/components/operations/week/__tests__/week-view.test.tsx
```

If shared-project follow-through is replayed later, add the shared-project and report-delivery test files before treating that second tranche as complete.

## Completion Condition

This packet is complete only when one of these becomes true:

- the safe operations-runtime tranche is replayed into the primary root with targeted validation green, and the remaining branch content is reclassified to freeze or archive
- or the lane is explicitly retired after the primary root independently absorbs the same capability

Current state:
- the first condition is now partially satisfied: the safe operations-runtime tranche is landed and green in `C:\Field Inspect`
- the remaining open work is reclassifying or freezing the residual branch content outside that first tranche
