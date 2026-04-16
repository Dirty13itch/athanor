# RFI HERS Duplicate Evidence Packet

Source of truth:
- `reports/reconciliation/rfi-hers-duplicate-evidence-packet-latest.json`
- `reports/reconciliation/tenant-family-audit-latest.json`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`

## Purpose

Turn the three `C:\CodexBuild\rfi-hers-rater-assistant*` trees into bounded archive-evidence lanes instead of leaving them as shadow product roots beside `C:\RFI & HERS Rater Assistant`.

## Current Facts

- Root authority candidate: `C:\RFI & HERS Rater Assistant`
- Duplicate variants:
  - `C:\CodexBuild\rfi-hers-rater-assistant`
  - `C:\CodexBuild\rfi-hers-rater-assistant-safe`
  - `C:\CodexBuild\rfi-hers-rater-assistant-v2`
- The generated packet report owns the exact preservation set for each duplicate tree.
- Only SQLite and drizzle artifacts survive as archive evidence.
- Plain-variant `src/features/*` files are already superseded by the root workspace's current namespaced feature tree.
- Disposable build residue such as `tsconfig.tsbuildinfo` is not preservation material.

## Preservation Tranches

### 1. Plain Variant Archive Evidence

Preserve only:
- `data/rfi-hers.sqlite`
- `drizzle/0000_curious_moira_mactaggert.sql`

Do not promote:
- `src/features/project-export.ts`
- `src/features/service.ts`
- `src/features/visit-form.tsx`

### 2. Safe Variant Archive Evidence

Preserve only:
- `data/empty-build-check.sqlite`
- `data/empty-build-check.sqlite-shm`
- `data/empty-build-check.sqlite-wal`
- `data/rfi-hers.sqlite`

### 3. V2 Variant Archive Evidence

Preserve only:
- `data/migrate-repro.sqlite`
- `data/rfi-hers.sqlite`
- `data/rfi-hers.sqlite-shm`
- `data/rfi-hers.sqlite-wal`
- `drizzle/0000_oval_impossible_man.sql`

## Execution Rules

- Do not treat any `C:\CodexBuild\rfi-hers-rater-assistant*` tree as an authority candidate or replay lane.
- Preserve only the artifacts listed under `preserve_archive_evidence` in the generated report.
- Treat the root workspace as the only repo-backed authority candidate unless later evidence proves otherwise.
- If the generated report ever shows unclassified artifacts, review those before widening or deleting the archive lane.

## Completion Condition

This packet is complete only when both are true:

- the root workspace remains the only governed authority candidate for the product family
- each duplicate variant is preserved only for its bounded archive evidence and no longer treated as a parallel project root
