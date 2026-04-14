# Model Deployment Report

Generated from `config/automation-backbone/model-deployment-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-11.1`
- Deployment lanes tracked: `6`
- Stored artifacts tracked: `3`

| Lane | Service | Node | State | Expected | Observed | Drift |
| --- | --- | --- | --- | --- | --- | --- |
| `foundry-coordinator` | `vllm_coordinator` | `foundry` | `degraded` | `/models/Qwen3.5-27B-FP8` | `/models/Qwen3.5-27B-FP8` | `drifted` |
| `foundry-coder` | `vllm_coder` | `foundry` | `historical` | `dolphin3-r1-24b` | `dolphin3-r1-24b` | `aligned` |
| `dev-embedding` | `embedding` | `dev` | `deployed` | `qwen3-embed-8b` | `qwen3-embed-8b` | `aligned` |
| `dev-reranker` | `reranker` | `dev` | `deployed` | `Qwen3-Reranker-0.6B` | `Qwen3-Reranker-0.6B` | `aligned` |
| `workshop-worker` | `vllm_worker` | `workshop` | `deployed` | `/models/Qwen3.5-35B-A3B-AWQ-4bit` | unset | `drifted` |
| `workshop-vision` | `vllm_vision` | `workshop` | `deployed` | `/models/Qwen3-VL-8B-Instruct-FP8` | `/models/Qwen3-VL-8B-Instruct-FP8` | `aligned` |

## Stored Model Artifacts

| Artifact | Node | State | Verified | Evidence |
| --- | --- | --- | --- | --- |
| `Qwen3.5-35B-A3B-AWQ-4bit` | `foundry` | `stored_local` | `2026-03-25T18:00:00Z` | observed model directory listing |
| `Qwen3-Coder-30B-A3B-Instruct-AWQ` | `foundry` | `stored_local` | `2026-03-25T18:00:00Z` | observed model directory listing |
| `Qwen2.5-VL-*` | `foundry` | `stored_local` | `2026-03-25T18:00:00Z` | observed model directory listing |

## Known Drift

- `foundry-coordinator-completion-degraded-2026-04-14` (medium): None

## Retired Drift

- `workshop-worker-lane-missing-2026-04-11` (medium): None
