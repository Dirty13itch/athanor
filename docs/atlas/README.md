# Athanor Atlas

The Athanor Atlas is now a narrow reference layer. It no longer owns live topology, UI, API, or completion-audit inventory truth. Those moved into the registry-backed control plane, generated reports, and the repo-native completion-audit toolchain.

## Authority Order

Use this order whenever sources disagree:

1. Running code, configs, route definitions, and deployed manifests
2. Operational specs and current inventory docs
3. Design docs and ADRs
4. Planning docs and archived build-manifest context
5. Older system-map documents

The atlas keeps older docs as source material, but it no longer lets them compete as equal truth.

## Status Tags

| Tag | Meaning |
| --- | --- |
| `live` | Implemented and part of the current active system. |
| `implemented_not_live` | Present in repo or runtime code, but not fully mounted or not currently part of the primary live path. |
| `planned` | Explicitly designed or documented, but not implemented as current repo/runtime behavior. |
| `deprecated` | Still present, but on the way out and not the preferred future path. |
| `legacy` | Historical or superseded behavior kept only for context or drift analysis. |

## Atlas Layout

- [`RUNTIME_ATLAS.md`](./RUNTIME_ATLAS.md) - runtime-oriented synthesis across task/workspace/control subsystems.
- [`COMMAND_HIERARCHY_ATLAS.md`](./COMMAND_HIERARCHY_ATLAS.md) - command and execution-path synthesis.
- [`MODEL_GOVERNANCE_ATLAS.md`](./MODEL_GOVERNANCE_ATLAS.md) - promotion, retirement, and proving-ground synthesis.
- [`OPERATIONS_ATLAS.md`](./OPERATIONS_ATLAS.md) - operational loops and governance synthesis.
- [`SOURCE_RECONCILIATION.md`](./SOURCE_RECONCILIATION.md) - which sources still own truth and which atlas surfaces are archived.

Retired atlas inventory artifacts now live under [`../archive/atlas/`](../archive/atlas/):

- atlas inventory JSON/schema files
- historical completion-audit schemas
- earlier atlas planning leftovers retained only for archive review

## Current Truth Layer

Use these instead of the retired atlas inventory layer:

- [`../../config/automation-backbone/platform-topology.json`](../../config/automation-backbone/platform-topology.json)
- [`../../config/automation-backbone/runtime-subsystem-registry.json`](../../config/automation-backbone/runtime-subsystem-registry.json)
- [`../../config/automation-backbone/model-deployment-registry.json`](../../config/automation-backbone/model-deployment-registry.json)
- [`../../projects/dashboard/src/lib/navigation.ts`](../../projects/dashboard/src/lib/navigation.ts)
- [`../../projects/dashboard/docs/OPERATOR-ROUTE-CONTRACTS.md`](../../projects/dashboard/docs/OPERATOR-ROUTE-CONTRACTS.md)
- [`../../reports/completion-audit/latest/inventory/`](../../reports/completion-audit/latest/inventory/)

## Validation

The atlas-specific validator is retired. Keep the remaining atlas docs synchronized by validating the real truth layer and checking atlas links:

- `python scripts/validate_platform_contract.py`
- `python scripts/check-doc-refs.py docs/atlas`

## Completion Audit Execution

The completion audit is now a repo-native program, not a manual checklist.

Primary entrypoint:

- `python scripts/run-completion-audit.py`

Core census and probe scripts:

- `python scripts/census-dashboard-routes.py`
- `python scripts/census-dashboard-api.py`
- `python scripts/census-dashboard-components.py`
- `python scripts/find-mounted-ui.py`
- `python scripts/map-agent-endpoints.py`
- `python scripts/census-env-contracts.py`
- `python scripts/audit-deployment-ownership.py`
- `python scripts/probe-agent-runtime.py`
- `python scripts/tests/live-dashboard-smoke.py`

Run outputs land in the `reports/completion-audit/` directory (created on first run).

### Historical Gate Snapshot

The old atlas-owned gate snapshot is retired. For current readiness, use:

- [`../../reports/completion-audit/latest/summary.md`](../../reports/completion-audit/latest/summary.md)
- `python scripts/run-completion-audit.py`

## Source Anchors

These remain the main upstream sources the atlas reconciles:

- [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) - operational architecture and system behavior.
- [`../SERVICES.md`](../SERVICES.md) - live service placement and model routing.
- [`../../STATUS.md`](../../STATUS.md) and [`../operations/CONTINUOUS-COMPLETION-BACKLOG.md`](../operations/CONTINUOUS-COMPLETION-BACKLOG.md) - current execution state and ranked work order.
- [`../design/command-hierarchy-governance.md`](../design/command-hierarchy-governance.md) - current command hierarchy and authority split.
- [`../decisions/ADR-023-command-hierarchy-and-governance.md`](../decisions/ADR-023-command-hierarchy-and-governance.md) - formal hierarchy decision.
- [`../../projects/dashboard/README.md`](../../projects/dashboard/README.md) - dashboard platform overview.
- [`../../projects/dashboard/docs/UI_AUDIT.md`](../../projects/dashboard/docs/UI_AUDIT.md) - route quality baseline.

## Reconciled Older Map Docs

These older map documents remain useful as historical or planning context, but they are no longer the canonical map:

- [`../archive/planning-era/ATHANOR-MAP.md`](../archive/planning-era/ATHANOR-MAP.md)
- [`../archive/planning-era/ATHANOR-MAP-ADDENDUM.md`](../archive/planning-era/ATHANOR-MAP-ADDENDUM.md)
- [`../archive/ATHANOR-SYSTEM-MAP.md`](../archive/ATHANOR-SYSTEM-MAP.md)
- [`../archive/COMPLETE-SYSTEM-BREAKDOWN.md`](../archive/COMPLETE-SYSTEM-BREAKDOWN.md)
- [`../archive/atlas/COMPLETION_AUDIT_PLAN.md`](../archive/atlas/COMPLETION_AUDIT_PLAN.md)

## How to Use This

- Start here when you need synthesis and source precedence.
- Drop to the retained runtime/governance atlas docs only for cross-layer narrative context.
- Use registries, generated reports, and completion-audit inventories for machine-readable truth.
- Use archived atlas docs only for historical comparison or migration context.
