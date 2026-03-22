# Hardware Management Audit — March 2026

*Research via local Research Agent, 2026-03-14. Thorough depth.*

## GPU Thermal Management

### Throttling Thresholds
| GPU | Safe Range | Throttle Start | Max Operating |
|-----|-----------|----------------|---------------|
| RTX 5090 (575W TDP) | 70-75°C sustained | 84-87°C | 105°C (emergency) |
| RTX 5070 Ti (250-300W TDP) | 65-75°C sustained | ~83°C | ~95°C |
| RTX 4090 (320W TDP) | 68-80°C sustained | 83-85°C | ~90°C |

### Key Points
- Performance degrades ~1% per 3°C beyond 80°C
- Ambient room temperature: keep below 24°C for optimal performance
- Memory temperatures (GDDR7 on 50-series) can exceed 95°C under stress — edge/core temps are primary throttle trigger
- Liquid cooling: 15-20°C lower temps, noise from 38-42 dB to 25-32 dB
- FOUNDRY power limits already set: 5070 Ti @ 250W (min), 4090 @ 320W

### Monitoring
- DCGM exporter on FOUNDRY + WORKSHOP feeds Prometheus
- Grafana dashboard shows GPU temps
- Alert threshold: >85°C for any GPU should trigger investigation

## UPS Sizing

### Power Estimation
| Node | Idle | Load | Peak |
|------|------|------|------|
| FOUNDRY (EPYC + 5 GPUs) | ~400W | ~1000W | ~1400W |
| WORKSHOP (TR + 2 GPUs) | ~200W | ~500W | ~700W |
| VAULT (9950X, Unraid, 8 HDDs) | ~200W | ~250W | ~300W |
| DEV (9900X + 5060 Ti) | ~100W | ~200W | ~250W |
| Network (switch, SFP+) | ~50W | ~50W | ~50W |
| **Total** | **~950W** | **~2000W** | **~2700W** |

### UPS Recommendation
- Minimum: 3kVA/2400W online UPS (80% derating of peak)
- Runtime target: 10-15 minutes for graceful shutdown
- Recommended: APC Smart-UPS SRT 3000VA or CyberPower OL3000RTXL2U
- NUT (Network UPS Tools) for automated shutdown orchestration

## MTU Audit (Live — 2026-03-14)

### Results
| Node | Primary NIC | MTU | Status |
|------|-------------|-----|--------|
| FOUNDRY | enp66s0f0/f1 (5GbE SFP+) | **9000** | OK |
| WORKSHOP | eno1 (5GbE) | **9000** | OK |
| VAULT | bond0/br0 (bonded eth0+eth1) | **9000** | OK |
| DEV | enp14s0 (5GbE Realtek) | **1500** | Expected |

### Finding: NO MISMATCH
- VAULT NFS server and all compute node clients are consistently at MTU 9000
- DEV at 1500 is expected — 5GbE Realtek NIC, non-critical path (only embedding/reranker traffic)
- VAULT docker0 also at MTU 9000 — containers inherit jumbo frame support
- **No action required** — the concern from the plan was unfounded

## Sources
- https://gpubottleneckcalculator.com/blog/thermal-throttling-next-gen-hardware-rtx-5090/
- https://unanswered.io/guide/rtx-5090-thermals-temperatures-cooling-overheating
- https://www.whaleflux.com/blog/safe-gpu-temperatures-a-guide-for-ai-teams/

Last updated: 2026-03-14
