# Truth Drift Report

Generated from the truth-layer registries by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Drift items tracked: `3`

| Severity | Count |
| --- | --- |
| `low` | 1 |
| `medium` | 2 |

## Drift Items

- `additional-operator-clients-hostname-rollout-gap` on `athanor_command_center`: DESK now resolves the canonical command-center and node-host aliases, but any additional operator clients still need the same scripted hosts-file rollout or internal DNS before athanor.local and the *.athanor.local deep links work there.
- `implementation-runtime-split` on `authority model`: Implementation truth, runtime authority, and deployed runtime state still live in different roots. The runtime-ownership contract now governs that split explicitly, so it remains governed maintenance debt rather than a full-system autonomy blocker.
- `workshop-runtime-surface-drift` on `runtime ownership`: Workshop runtime compose surfaces are now explicit roots, but several live configs under /opt/athanor still drift from implementation authority and require governed per-surface reconciliation instead of ad hoc node memory.

## Retired Runtime Migration Seams

The DEV governor-facade cutover is verified. Keep [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) as the audit trail and reopen the seam only if live drift reappears.
