# Hardware Report

Generated from `config/automation-backbone/hardware-inventory.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-03-26.1`
- Nodes tracked: `5`

| Node | Host | Role | CPU | RAM | GPUs | Storage | Links |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `desk` | DESK | implementation-authority workstation | Intel Core i7-13700K | 64 GB | NVIDIA RTX 3060 (12 GB), Intel UHD 770 (0 GB) | 1 TB nvme, 2 TB nvme | 1 Gbps Intel I219-V |
| `dev` | DEV | runtime authority and ops center | AMD Ryzen 9 9900X | 64 GB | NVIDIA RTX 5060 Ti (16 GB) | 4 TB nvme, 1 TB nvme, 1 TB nvme | 5 Gbps primary |
| `foundry` | FOUNDRY | heavy compute and inference | AMD EPYC 7663 | 224 GB | NVIDIA RTX 4090 (24 GB), NVIDIA RTX 5070 Ti (16 GB), NVIDIA RTX 5070 Ti (16 GB), NVIDIA RTX 5070 Ti (16 GB), NVIDIA RTX 5070 Ti (16 GB) | 4 TB nvme, 4 TB nvme, 22 TB nfs | 10 Gbps primary |
| `workshop` | WORKSHOP | creative compute and dashboard-adjacent node | AMD Threadripper 7960X | 128 GB | NVIDIA RTX 5090 (32 GB), NVIDIA RTX 5060 Ti (16 GB) | 4 TB nvme, 1 TB nvme, 1 TB nvme | 10 Gbps primary |
| `vault` | VAULT | storage, monitoring, and API aggregation | AMD Ryzen 9 9950X | 128 GB | Intel Arc A380 (6 GB) | 5 x 1 TB nvme, 184 TB hdd | 10 Gbps primary |

## DESK (`desk`)

- Role: implementation-authority workstation
- Last verified: `2026-03-26T18:45:00Z`
- Evidence sources: `local runtime probe`
- Notes: `Primary implementation-authority workstation.`, `Compatibility-only provider bridge settings may still be supplied by env, but DESK no longer carries a canonical live provider-bridge service entry.`

## DEV (`dev`)

- Role: runtime authority and ops center
- Last verified: `2026-03-25T17:45:00Z`
- Evidence sources: `ssh runtime probe`
- Notes: `Current live deployment host.`, `Runtime authority includes /home/shaun/repos/athanor, /opt/athanor, /home/shaun/.athanor, systemd, cron, and /var/log/athanor.`

## FOUNDRY (`foundry`)

- Role: heavy compute and inference
- Last verified: `2026-03-26T18:50:00Z`
- Evidence sources: `ssh runtime probe`
- Notes: `Primary high-throughput inference node.`, `Observed model endpoints currently serve Qwen3.5-27B-FP8 on 8000 and qwen3-coder-30b on 8006.`

## WORKSHOP (`workshop`)

- Role: creative compute and dashboard-adjacent node
- Last verified: `2026-03-26T18:55:00Z`
- Evidence sources: `ssh runtime probe`
- Notes: `ComfyUI on 8188 is observed on the 5060 Ti lane.`, `The 8010 lane is aligned to the canonical workshop worker runtime and currently serves /models/Qwen3.5-35B-A3B-AWQ-4bit.`, `The 8012 lane is the observed Workshop vision runtime and currently serves /models/Qwen3-VL-8B-Instruct-FP8.`

## VAULT (`vault`)

- Role: storage, monitoring, and API aggregation
- Last verified: `2026-03-25T18:10:00Z`
- Evidence sources: `vault runtime probe`
- Notes: `Holds LiteLLM, Neo4j, Grafana, Prometheus, and long-lived storage surfaces.`, `LiteLLM is auth-protected; /health returned 401 during the 2026-03-25 probe, which counts as reachable and protected.`
