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
- The local matrix is green from implementation authority, and the live dashboard smoke should now be green against the DEV command center. Remaining front-door drift is operator-desktop hostname resolution for `athanor.local`, not WORKSHOP split-brain or missing `/_next/static` assets.
- The registry currently tracks 111 surfaces with 0 uncovered surfaces.
- All tracked surfaces are covered by automated or live checks; the current live failures are runtime/operator-surface drift, not uncovered UI.
- Coverage split:
  - `covered-automated`: 39
  - `covered-live`: 72

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
- Dashboard live smoke should be pointed at the current topology-owned dashboard deployment through `ATHANOR_COMMAND_CENTER_URL`, `ATHANOR_DASHBOARD_URL`, or `--base-url`; do not treat any older WORKSHOP-hosted URL as canonical truth.
- The live dashboard smoke is front-door focused: sampled `/_next/static` failures, missing safe operator-context/session APIs, and broken live chat or handoff lanes are failures; expected locked-session write gating is not.
- EoBQ live smoke defaults to `http://interface.athanor.local:3002/` unless `ATHANOR_EOQ_LINK_URL` or `--base-url` overrides it.
- Ulrich live smoke defaults to `http://interface.athanor.local:3003/` unless `ATHANOR_ULRICH_LINK_URL` or `--base-url` overrides it.
- EoBQ generation and Ulrich mutation smokes are opt-in in the live runners so the default cycle stays low-impact.
