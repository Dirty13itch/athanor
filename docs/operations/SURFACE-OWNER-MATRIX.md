# Surface Owner Matrix

Generated from `config/automation-backbone/docs-lifecycle-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-16.1`
- Total tracked surfaces: `151`
- Generated surfaces: `12`

## Layer Counts

| Layer | Count |
| --- | --- |
| `architecture_reference` | 1 |
| `archive_reference` | 46 |
| `ecosystem_governance` | 5 |
| `historical_working_memory` | 2 |
| `live_execution` | 7 |
| `operator_control` | 12 |
| `startup_doctrine` | 4 |
| `startup_reference` | 1 |
| `strategic_reference` | 1 |
| `unspecified` | 72 |

## Top-entry and Plan Surfaces

| Path | Layer | Authority | Volatility | Content class | Generated | Validator |
| --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | `startup_doctrine` | `adopted_system` | `stable` | `startup_doctrine` | no | `scripts/validate_platform_contract.py` |
| `PROJECT.md` | `startup_doctrine` | `adopted_system` | `stable` | `startup_doctrine` | no | `scripts/validate_platform_contract.py` |
| `README.md` | `startup_doctrine` | `adopted_system` | `stable` | `startup_doctrine` | no | `scripts/validate_platform_contract.py` |
| `STATUS.md` | `live_execution` | `adopted_system` | `curated_current` | `live_execution` | no | `scripts/validate_platform_contract.py` |
| `docs/CODEX-NEXT-STEPS.md` | `startup_doctrine` | `adopted_system` | `stable_tranche_intent` | `startup_doctrine` | no | `scripts/validate_platform_contract.py` |
| `docs/MASTER-PLAN.md` | `strategic_reference` | `adopted_system` | `strategic` | `strategic_reference` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md` | `ecosystem_governance` | `ecosystem_governance` | `curated_current` | `ecosystem_governance` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md` | `live_execution` | `adopted_system` | `stable_navigation` | `live_execution` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/ATHANOR-OPERATING-SYSTEM.md` | `live_execution` | `adopted_system` | `stable_operating_doctrine` | `live_execution` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md` | `ecosystem_governance` | `ecosystem_governance` | `curated_current` | `ecosystem_governance` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/ATHANOR-TENANT-QUEUE.md` | `ecosystem_governance` | `ecosystem_governance` | `curated_current` | `ecosystem_governance` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` | `live_execution` | `adopted_system` | `live_queue_curated` | `live_execution` | no | `scripts/validate_platform_contract.py` |
| `docs/operations/PUBLICATION-PROVENANCE-REPORT.md` | `live_execution` | `adopted_system` | `generated_current` | `live_execution` | yes | `python scripts/generate_truth_inventory_reports.py --check --report publication_provenance` |
| `docs/operations/SURFACE-OWNER-MATRIX.md` | `operator_control` | `adopted_system` | `generated_current` | `operator_control` | yes | `python scripts/generate_truth_inventory_reports.py --check --report surface_owner_matrix` |
