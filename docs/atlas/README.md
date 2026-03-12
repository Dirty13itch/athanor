# Athanor Atlas

The Athanor Atlas is the canonical cross-layer system map for Athanor. It does not replace [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) or [`../SERVICES.md`](../SERVICES.md); it sits above them and tells you where truth lives, which surfaces are live, and how the pieces connect.

## Authority Order

Use this order whenever sources disagree:

1. Running code, configs, route definitions, and deployed manifests
2. Operational specs and current inventory docs
3. Design docs and ADRs
4. Planning docs and build-manifest context
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

- [`TOPOLOGY_ATLAS.md`](./TOPOLOGY_ATLAS.md) - nodes, services, models, stores, network paths, and deployment truth.
- [`RUNTIME_ATLAS.md`](./RUNTIME_ATLAS.md) - agents, task/workspace systems, control loops, subscriptions, and adaptive subsystems.
- [`UI_ATLAS.md`](./UI_ATLAS.md) - shell, every dashboard route, shared console families, dormant UI systems, and cross-route dependencies.
- [`API_ATLAS.md`](./API_ATLAS.md) - dashboard API families, agent-server endpoint families, contract ownership, and UI/API consumer mapping.
- [`COMPLETION_AUDIT_PLAN.md`](./COMPLETION_AUDIT_PLAN.md) - the exhaustive program for finding unfinished, partial, dormant, broken, and legacy surfaces across every layer.
- [`SOURCE_RECONCILIATION.md`](./SOURCE_RECONCILIATION.md) - which documents and code/config layers still own truth, and which older docs are now reference-only.

## Machine-readable Inventory Layer

The atlas inventory lives beside the prose docs and uses one record schema across all layers:

- [`inventory/atlas-record.schema.json`](./inventory/atlas-record.schema.json)
- [`inventory/topology-inventory.json`](./inventory/topology-inventory.json)
- [`inventory/runtime-inventory.json`](./inventory/runtime-inventory.json)
- [`inventory/ui-inventory.json`](./inventory/ui-inventory.json)
- [`inventory/api-inventory.json`](./inventory/api-inventory.json)

The inventory is internal documentation structure, not a product API.

### Completion Audit Inventory

The completion-audit layer extends the atlas with code-derived and runtime-derived audit artifacts:

- [`inventory/completion/completion-status.schema.json`](./inventory/completion/completion-status.schema.json)
- [`inventory/completion/route-audit-record.schema.json`](./inventory/completion/route-audit-record.schema.json)
- [`inventory/completion/api-audit-record.schema.json`](./inventory/completion/api-audit-record.schema.json)
- [`inventory/completion/runtime-subsystem-audit-record.schema.json`](./inventory/completion/runtime-subsystem-audit-record.schema.json)
- [`inventory/completion/deployment-ownership-record.schema.json`](./inventory/completion/deployment-ownership-record.schema.json)
- [`inventory/completion/release-readiness-report.schema.json`](./inventory/completion/release-readiness-report.schema.json)
- [`inventory/completion/dashboard-route-census.json`](./inventory/completion/dashboard-route-census.json)
- [`inventory/completion/dashboard-api-census.json`](./inventory/completion/dashboard-api-census.json)
- [`inventory/completion/dashboard-component-census.json`](./inventory/completion/dashboard-component-census.json)
- [`inventory/completion/dashboard-mount-graph.json`](./inventory/completion/dashboard-mount-graph.json)
- [`inventory/completion/agent-endpoint-census.json`](./inventory/completion/agent-endpoint-census.json)
- [`inventory/completion/runtime-subsystem-census.json`](./inventory/completion/runtime-subsystem-census.json)
- [`inventory/completion/env-contract-census.json`](./inventory/completion/env-contract-census.json)
- [`inventory/completion/deployment-ownership-matrix.json`](./inventory/completion/deployment-ownership-matrix.json)

## Validation

Keep the atlas synchronized with the repo by running:

- `python scripts/validate-atlas.py`
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

Run outputs land in:

- [`../../reports/completion-audit/latest/summary.md`](../../reports/completion-audit/latest/summary.md)
- [`../../reports/completion-audit/latest/release-readiness.json`](../../reports/completion-audit/latest/release-readiness.json)
- [`../../reports/completion-audit/latest/remediation-backlog.json`](../../reports/completion-audit/latest/remediation-backlog.json)
- timestamped runs under [`../../reports/completion-audit`](../../reports/completion-audit)

### Current Gate State

As of `2026-03-11`, the completion gate is passing in `ready` state.

- `25` dashboard routes are inventoried and audited.
- `30` support surfaces are inventoried with direct automated render coverage.
- `54` dashboard APIs are inventoried; only `/api/stash/stats` remains unresolved as an orphan candidate.
- the deterministic fixture lane and live-runtime lane both pass with `0` failed jobs.
- the remaining warnings are deliberate dormant/unmounted surfaces plus known deployment drift on `agent-server`, `LiteLLM`, and `VAULT` monitoring.

## Source Anchors

These remain the main upstream sources the atlas reconciles:

- [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) - operational architecture and system behavior.
- [`../SERVICES.md`](../SERVICES.md) - live service placement and model routing.
- [`../BUILD-MANIFEST.md`](../BUILD-MANIFEST.md) - execution queue and current deployment notes.
- [`../design/agent-contracts.md`](../design/agent-contracts.md) - agent behavior contracts.
- [`../../projects/dashboard/README.md`](../../projects/dashboard/README.md) - dashboard platform overview.
- [`../../projects/dashboard/docs/UI_AUDIT.md`](../../projects/dashboard/docs/UI_AUDIT.md) - route quality baseline.

## Reconciled Older Map Docs

These older map documents remain useful as historical or planning context, but they are no longer the canonical map:

- [`../planning/ATHANOR-MAP.md`](../planning/ATHANOR-MAP.md)
- [`../planning/ATHANOR-MAP-ADDENDUM.md`](../planning/ATHANOR-MAP-ADDENDUM.md)
- [`../hardware/ATHANOR-SYSTEM-MAP.md`](../hardware/ATHANOR-SYSTEM-MAP.md)
- [`../hardware/COMPLETE-SYSTEM-BREAKDOWN.md`](../hardware/COMPLETE-SYSTEM-BREAKDOWN.md)

## How to Use This

- Start here when you need the full shape of Athanor.
- Drop to the subsystem atlas that matches the question.
- Use the inventory JSON when you need systematic coverage checks or machine-readable linking.
- Drop to the operational/design docs only when the atlas points you there as the higher-detail source.
