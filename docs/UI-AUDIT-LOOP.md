# Athanor UI Audit Loop

> **Last updated:** 2026-04-15
> **Status:** UI-audit reference only.
> **Coverage evidence surfaces are tracked here:** `tests/ui-audit/surface-registry.json`, `tests/ui-audit/uncovered-surfaces.json`, `tests/ui-audit/findings-ledger.json`, `tests/ui-audit/last-run.json`, and the current restart brief.
> **Authority boundary:** proof surfaces for UI audit coverage only; this page is not runtime, queue, portfolio, or release authority.
> **Purpose:** preserve the audit loop and entrypoint commands without turning this page into the source of live coverage counts or release posture.

This page preserves the audit loop for shipped operator surfaces. Current counts, failures, and coverage posture must come from the evidence surfaces above and the restart brief, not this page.

- `projects/dashboard`
- `projects/eoq`
- `projects/ulrich-energy`

The audit evidence surfaces are tracked in:

- [tests/ui-audit/surface-registry.json](../tests/ui-audit/surface-registry.json)
- [tests/ui-audit/uncovered-surfaces.json](../tests/ui-audit/uncovered-surfaces.json)
- [tests/ui-audit/findings-ledger.json](../tests/ui-audit/findings-ledger.json)
- [tests/ui-audit/last-run.json](../tests/ui-audit/last-run.json)

## Last Recorded Baseline (Historical Snapshot)
- At the last recorded baseline, the local matrix was green from implementation authority and the dashboard smoke was expected to be green against the DEV command center. Recheck the evidence surfaces above before treating that posture as current.
- That last recorded registry snapshot tracked 111 surfaces with 0 uncovered surfaces.
- At that same baseline, all tracked surfaces were covered by automated or live checks; any current failures should be taken from the evidence surfaces above rather than inferred from this page.
- Coverage split:
  - `covered-automated`: 39
  - `covered-live`: 72

## Reference Loop
1. Regenerate the surface registry and uncovered list.
2. Run the local matrix for dashboard, EoBQ, and Ulrich.
3. Run targeted live smoke across dashboard and tenants.
4. Perform manual checks only for surfaces explicitly marked `covered-manual`.
5. Log every new finding in the ledger unless it was fixed in the same cycle.
6. Add regression coverage for every resolved bug.
7. Rerun the matrix.
8. Stop only after two consecutive passes produce no new actionable findings.

## Reference Commands
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
