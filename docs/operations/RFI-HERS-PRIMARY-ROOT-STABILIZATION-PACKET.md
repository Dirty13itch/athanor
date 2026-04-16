# RFI HERS Primary Root Stabilization Packet

Source of truth:
- `reports/reconciliation/rfi-hers-primary-root-stabilization-latest.json`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`
- `docs/operations/RFI-HERS-DUPLICATE-EVIDENCE-PACKET.md`

## Purpose

Turn `C:\RFI & HERS Rater Assistant` from a vaguely dirty primary workspace into a governed stabilization lane with explicit dirty-file buckets, ordered execution, and validation.

This packet exists because the duplicate-tree variants are now already bounded by the duplicate-evidence packet. What remains open in the family is the real git-backed root itself.

## Current Facts

- Regenerate `reports/reconciliation/rfi-hers-primary-root-stabilization-latest.json` before acting. The report owns the live dirty-file set and execution posture.
- Root authority candidate: `C:\RFI & HERS Rater Assistant`
- Current branch: `master`
- Origin remote: none configured
- Duplicate-tree variants under `C:\CodexBuild\*` are not replay sources. They stay governed only by `RFI-HERS-DUPLICATE-EVIDENCE-PACKET.md`.
- The generated report now treats the root as `ready_for_ordered_stabilization` whenever the dirty surface is fully bucketed into governed tranches; it should no longer read like one undifferentiated dirty workspace.
- A dedicated review worktree now exists at `C:\RFI & HERS Rater Assistant-stabilization-review` on branch `codex/stabilize-settlers-ridge-root`, seeded with the first four tranches. Because native npm install breaks under the spaced workspace path, the same branch is currently validated from the safe mirror at `C:\CodexBuild\rfi-hers-stabilization-review`.
- The review-branch-only stabilization fixes for `scripts/db-seed.ts`, `src/features/unit-types/library.ts`, and `tests/domain-validation.test.ts` were landed into the authority root on 2026-04-07.
- The root currently carries dirty work across:
  - repo contracts and plan files
  - canonical Settlers Ridge project data
  - spreadsheet generators/importers
  - generated workbook outputs
  - repo docs and field runbooks

## Stabilization Tranches

### 1. Repo Contracts And Plan

Use first:
- `AGENTS.md`
- `PROJECT.md`
- `package.json`
- `.gitignore`
- `.agents/system.md`
- `plans/active/*`

Reason:
- this tranche defines what the root is, how it validates, and how the field workflow should resume
- it keeps the product loop explicit before broader data/output churn is normalized

### 2. Canonical Project Data

Treat as the highest-value dirty product truth:
- `data/projects/settlers-ridge/*`

Reason:
- these files are the canonical operator truth behind the split workbook surfaces
- if these are wrong or unreviewed, workbook outputs and derived docs are downstream noise

### 3. Generators And Importers

Review next:
- `scripts/build_settlers_ridge_project_data.py`
- `scripts/generate_settlers_ridge_part2_packet.py`
- `scripts/import_settlers_ridge_field_data.py`
- `scripts/settlers_ridge_project_data.py`
- `scripts/validate_settlers_ridge_packet.py`
- related spreadsheet formatter helpers

Reason:
- these scripts define how canonical data becomes field workbooks and how field capture returns to repo truth
- they should be stabilized before generated workbook outputs are treated as final artifacts

### 4. Workbook Outputs

Review only after canonical data and generators are understood:
- `output/spreadsheet/Settlers-Ridge-Project-Master.xlsx`
- `output/spreadsheet/Settlers-Ridge-Active-Visit.xlsx`
- `output/spreadsheet/Settlers-Ridge-Closeout-Handoff.xlsx`
- `output/spreadsheet/Settlers-Ridge-Full-Packet.xlsx`
- other generated workbook outputs found in the report

Reason:
- these are operator-facing deliverables, but they are downstream artifacts
- do not bless them independently of the canonical data and script layers that generated them

### 5. Docs And Runbooks

Review after the product-bearing surfaces are stable:
- `docs/*`

Reason:
- this repo depends heavily on docs for resume-after-compaction continuity
- but the docs should follow stabilized product/data/script truth, not lead it

### 6. Operator Residue If Present

Leave for the last tranche:
- any future `agents/*` residue reported outside the governed repo-contract files

Reason:
- this residue is not part of the current product-bearing authority surface
- they should be preserved or reconciled only after the canonical data, generators, workbooks, and docs are already stable

## Execution Rules

- Treat `C:\RFI & HERS Rater Assistant` as the only repo-backed authority candidate in the family.
- Do not treat any `C:\CodexBuild\rfi-hers-rater-assistant*` tree as an authority candidate or replay lane.
- Regenerate the primary-root stabilization report before execution and honor its dirty-file buckets.
- Stabilize canonical data plus generators before treating workbook outputs as final.
- Use `scripts/codex/validate-safe.ps1` or an equivalent safe mirror path when Windows path behavior blocks clean local validation in the root workspace.

## Targeted Validation

Run these in `C:\RFI & HERS Rater Assistant` after the relevant tranche is stabilized:

```powershell
npm run typecheck
npm run test
python scripts/validate_settlers_ridge_packet.py
powershell -ExecutionPolicy Bypass -File scripts/codex/validate-safe.ps1
```

Use the safe-path validation helper when local Windows path handling prevents a clean direct run in the repo root.

Current state:
- `python scripts/validate_settlers_ridge_packet.py` passes in `C:\RFI & HERS Rater Assistant`
- `powershell -ExecutionPolicy Bypass -File scripts/codex/validate-safe.ps1` passes and syncs generated artifacts back into the authority root
- direct `npm run typecheck` and `npm run test` are still blocked in the spaced root because the local Node toolchain is not usable there, so the safe-path lane remains part of the normal governed validation contract

## Completion Condition

This packet is complete only when both are true:

- the root remains the only governed repo-backed authority candidate for the family
- the dirty root changes are bucketed, preserved, and validated through the documented stabilization sequence instead of remaining as an unstructured dirty workspace
