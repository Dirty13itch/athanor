# Truth Drift Report

Generated from the truth-layer registries by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Drift items tracked: `2`

| Severity | Count |
| --- | --- |
| `high` | 1 |
| `medium` | 1 |

## Drift Items

- `desk-operator-hostname-resolution-gap` on `athanor_command_center`: DEV now serves the command center cleanly through Caddy, but operator desktops still need athanor.local hostname resolution before the canonical URL is reachable without host overrides.
- `implementation-runtime-split` on `authority model`: Implementation truth and runtime authority still live in different roots. Drift must reconcile from DEV back into C:/Athanor until deployment becomes a strict mirror.

## Retired Runtime Migration Seams

The DEV governor-facade cutover is verified. Keep [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) as the audit trail and reopen the seam only if live drift reappears.
