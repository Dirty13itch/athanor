# Reference and Archive Prune Packet

## Objective

Bind the remaining top-level reference and archive cleanup into an explicit owned packet so dirty doctrine, design, portfolio, and retired-lineage surfaces stop reading like anonymous deferred debt while stable-day accrues.

## Scope

- `docs/SERVICES.md`
- `docs/SYSTEM-SPEC.md`
- `docs/design/project-platform-architecture.md`
- `docs/operations/PROJECT-MATURITY-REPORT.md`
- `docs/projects/PORTFOLIO-REGISTRY.md`
- `docs/projects/ulrich-energy/REQUIREMENTS.md`
- `docs/projects/ulrich-energy/WORKFLOWS.md`
- `docs/archive/plans/2026-04-19-athanor-blocker-closure-program.md` as the archived antecedent that triggered this prune lane

## Why This Exists

- Publication triage was still surfacing seven dirty top-level docs under `reference-and-archive-prune` with no explicit slice ownership.
- Most of the content changes are correct, but without an owned slice they still look like anonymous closure debt.
- The retired `ulrich-energy` lineage surfaces must stay clearly subordinate to the external `Ulrich Energy Auditing Website` authority root.
- Active operator truth must live in current reports, registries, and operating docs, not in stale or ambiguous reference surfaces.

## Validation

- `python scripts/generate_project_maturity_report.py --check`
- `python scripts/triage_publication_tranche.py --write docs/operations/PUBLICATION-TRIAGE-REPORT.md`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_steady_state_status.py --json`
- `python scripts/validate_platform_contract.py`

## Success Condition

- The seven dirty doctrine/reference docs are owned by an explicit publication slice instead of anonymous deferred-family debt.
- The design and retired-lineage docs carry explicit authority boundaries.
- `reference-and-archive-prune` drops to `match_count = 0` because the remaining dirty surfaces are now packet-backed owned work instead of floating prune debt.

## Rollback

- Restore the listed docs and lifecycle/registry entries if the ownership split proves incorrect.
- Re-run project-maturity generation, publication triage, the deferred-family queue, blocker-map writing, steady-state writing, and platform validation.
