# Portfolio Registry

This document mirrors the current project maturity assignments from [`project-maturity-registry.json`](../../config/automation-backbone/project-maturity-registry.json).

| Project | Class | Reason |
| --- | --- | --- |
| `agents` | `platform-core` | Primary control-plane runtime. |
| `dashboard` | `production-product` | Main authenticated operator surface. |
| `gpu-orchestrator` | `platform-core` | Privileged GPU control surface. |
| `ws-pty-bridge` | `platform-core` | Supporting operator and agent infrastructure. |
| `eoq` | `active-scaffold` | Active product lane, not yet under full production contract. |
| `comfyui-workflows` | `active-scaffold` | Reusable creative workflow scaffold. |
| `kindred` | `incubation` | Incubating product concept. |
| `ulrich-energy` | `incubation` | Incubating product concept. |
| `reports` | `archive` | Output archive, not an active runtime. |

Projects should move classes only when the contract in the registry changes with evidence, not because they feel important.
