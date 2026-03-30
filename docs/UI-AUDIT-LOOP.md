# Athanor UI Audit Loop

This is the permanent audit loop for the shipped operator surfaces:

- `projects/dashboard`
- `projects/eoq`
- `projects/ulrich-energy`

The audit truth lives in:

- [tests/ui-audit/surface-registry.json](../tests/ui-audit/surface-registry.json)
- [tests/ui-audit/uncovered-surfaces.json](../tests/ui-audit/uncovered-surfaces.json)
- [tests/ui-audit/findings-ledger.json](../tests/ui-audit/findings-ledger.json)
- [tests/ui-audit/last-run.json](../tests/ui-audit/last-run.json)

## Current Baseline
- Two consecutive full audit runs are green with no actionable findings.
- The registry currently tracks 99 surfaces with 0 uncovered surfaces.
- All tracked surfaces are now covered by automated or live checks.
- Coverage split:
  - `covered-automated`: 29
  - `covered-live`: 70

## Loop
1. Regenerate the surface registry and uncovered list.
2. Run the local matrix for dashboard, EoBQ, and Ulrich.
3. Run targeted live smoke across dashboard and tenants.
4. Perform manual checks only for surfaces explicitly marked `covered-manual`.
5. Log every new finding in the ledger unless it was fixed in the same cycle.
6. Add regression coverage for every resolved bug.
7. Rerun the matrix.
8. Stop only after two consecutive passes produce no new actionable findings.

## Commands
- Full loop:
  - `python scripts/tests/run-ui-audit.py`
- Local-only loop:
  - `python scripts/tests/run-ui-audit.py --skip-live`
- Live-only smoke:
  - `python scripts/tests/run-ui-audit.py --live-only`
- Direct live smoke runner:
  - `python scripts/tests/run-live-ui-smoke.py`
- Registry regeneration:
  - `python scripts/tests/generate-ui-surface-registry.py`
- Coverage check:
  - `python scripts/tests/check-ui-coverage.py`

## Notes
- Dashboard live smoke defaults to the canonical front door at `https://athanor.local/`; use `ATHANOR_COMMAND_CENTER_URL`, `ATHANOR_DASHBOARD_URL`, or `--base-url` to target the runtime fallback or another command-center path explicitly.
- EoBQ live smoke defaults to `http://interface.athanor.local:3002/` unless `ATHANOR_EOQ_LINK_URL` or `--base-url` overrides it.
- Ulrich live smoke defaults to `http://interface.athanor.local:3003/` unless `ATHANOR_ULRICH_LINK_URL` or `--base-url` overrides it.
- EoBQ generation and Ulrich mutation smokes are opt-in in the live runners so the default cycle stays low-impact.
