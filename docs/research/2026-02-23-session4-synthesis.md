# Athanor Session 4 Synthesis — Full State of the Union
*2026-02-23*

---

## What Was Accomplished This Session

### Infrastructure Fixed
1. **Prometheus + Grafana deployed fresh on VAULT** — All 5 scrape targets (2x node_exporter, 2x dcgm-exporter, self) UP. Grafana configured with Prometheus data source + Node Exporter Full + DCGM dashboards imported.
2. **SSH from DEV to Node 2 fixed** — Added athanor-dev ed25519 key to Node 2's authorized_keys via Node 1 jump host. Both `id_ed25519` and `athanor_mgmt` keys now work from DEV to both nodes.
3. **All 6 DHCP reservations confirmed** in UniFi Controller (completed in session start).

### Documentation Reconciled
Every major doc updated to match reality:
- **CLAUDE.md**: Model references (Qwen3-14B, not 32B-AWQ), services map, network topology, blockers, GPU allocation, key gotchas
- **BUILD-ROADMAP.md**: Physical tasks marked done, model entries corrected, blocked items updated
- **AGENTS.md**: Contract-driven architecture table corrected (Reasoning slot = Qwen3-14B pending upgrade)
- **Hardware inventory**: RTX 3060 corrected to Loose (not Node 1), GPU count summaries fixed

### Critical Discovery: VAULT ZFS Pool Destroyed
The motherboard swap destroyed the ZFS NVMe pool (`hpc_nvme`) that held ALL container appdata. The 5 NVMe drives were reformatted from ZFS to 4x btrfs single-drive pools. **1.9TB of data lost** including all media service configs, Plex watch history, and container metadata. Media files on the HDD array are intact.

---

## Current System State (Verified Live)

### Node 1 "Foundry" — 192.168.1.244 ✅ HEALTHY
| Resource | Value |
|----------|-------|
| Uptime | 10+ hours |
| Containers | 4 (vllm, athanor-agents, dcgm-exporter, node-exporter) |
| GPUs | 5: 3x 5070 Ti + 4090 (TP=4 pool) + 1x 5070 Ti (idle) |
| VRAM Used | 59.8 GB / 88 GB (GPU 4 idle) |
| vLLM Model | Qwen3-14B, TP=4, 32K context, 0.85 util |
| Temps | 28-37°C (all idle) |

### Node 2 "Workshop" — 192.168.1.225 ✅ HEALTHY
| Resource | Value |
|----------|-------|
| Uptime | ~2 hours |
| Containers | 6 (vllm-node2, open-webui, dashboard, comfyui, dcgm-exporter, node-exporter) |
| GPUs | RTX 5090 (31.1/32.6 GB, vLLM) + RTX 5060 Ti (0.1/16.3 GB, ComfyUI idle) |
| vLLM Model | Qwen3-14B, single GPU, 8K context, enforce-eager, 0.95 util |
| Temps | 31-38°C |

### VAULT — 192.168.1.203 ⚠️ PARTIAL
| Resource | Value |
|----------|-------|
| Array | Started, 164 TB HDD (146T used = 89%) |
| NFS | Working (models, data, appdata shares mounted on both nodes) |
| NVMe Pools | 4x btrfs singles (appdatacache, docker, transcode, vms) ~3.7 TB total |
| Prometheus | ✅ Running (fresh deploy) |
| Grafana | ✅ Running (dashboards imported) |
| Media Stack | ❌ ALL DOWN (Plex, Sonarr, Radarr, Prowlarr, SABnzbd, Tautulli, Stash) |
| Home Assistant | ❌ DOWN |

### NFS Models Available
| Model | Size | Used By |
|-------|------|---------|
| Qwen3-14B | ~28 GB | Both nodes (vLLM) |
| gte-Qwen2-7B-instruct | ~14 GB | Not loaded (embedding model) |
| **Qwen3-32B-AWQ** | **NOT PRESENT** | Planned for Reasoning slot |

---

## Prioritized Action Plan

### Tier 1 — Critical (Requires Shaun)
These need hands-on Unraid UI work that can't be automated:

| # | Action | Time | Impact |
|---|--------|------|--------|
| 1 | **Redeploy VAULT media stack** via Unraid Community Apps | 30-45 min | Restores Plex, *arr stack, Stash |
| 2 | **Configure each service** — root folders, indexers, API keys | 20-30 min | Media stack functional |
| 3 | **HA onboarding** at http://192.168.1.203:8123 | 5 min | Unblocks Home Agent |
| 4 | **Enable EXPO on Node 2** via JetKVM BIOS | 5 min | DDR5 4800→5600 MT/s |

### Tier 2 — High Value (Claude Can Execute Autonomously)
| # | Action | Impact | Complexity |
|---|--------|--------|-----------|
| 1 | **Download Qwen3-32B-AWQ** to NFS, upgrade Node 1 vLLM | Reasoning slot upgrade — better agent quality | Medium |
| 2 | **Write VAULT Ansible roles** for media services | Reproducible deploys, never lose configs again | Medium |
| 3 | **Download Qwen3-0.6B** draft model for speculative decoding | 1.5-2.5x throughput on Node 1 | Low |
| 4 | **Download Qwen3-Embedding-0.6B** for future RAG | Fills Embedding contract slot | Low |
| 5 | **Create custom Athanor Overview Grafana dashboard** | System-at-a-glance (lost in ZFS wipe) | Low |
| 6 | **Add agent routing to Dashboard** | Agents accessible from web UI | Medium |

### Tier 3 — Valuable but Non-Urgent
| # | Action | Notes |
|---|--------|-------|
| 1 | **Upgrade vLLM to v0.16.0** | CUDA 13.0 native Blackwell, released 2026-02-13 |
| 2 | **LiteLLM proxy** | Multi-backend load balancing (ADR-012) |
| 3 | **Research Agent** | Web search + summarization |
| 4 | **Creative Agent** | ComfyUI workflow triggering |
| 5 | **Knowledge Agent** | Index bookmarks, docs, research |
| 6 | **EoBQ pipeline development** | ComfyUI workflows + LLM integration |
| 7 | **Data share capacity planning** | 89% full, 19TB free, growth trajectory |

### Tier 4 — Future
| # | Action | Prerequisite |
|---|--------|-------------|
| 1 | InfiniBand between nodes | ConnectX-3 cards ($60) |
| 2 | Video generation (Wan2.2) | GPU budget planning |
| 3 | Full RAG pipeline | Embedding + Reranker models + vector DB |
| 4 | Voice interface | Research needed |
| 5 | Remote access (Tailscale/WireGuard) | Security audit needed |

---

## Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Total VRAM (installed) | 136 GB (7 NVIDIA GPUs) | ✅ |
| VRAM in use | ~91 GB (67%) | Good — GPU 4 idle |
| HDD Storage | 146T / 165T (89%) | ⚠️ Approaching capacity |
| NVMe (NFS models) | 20G / 932G (2%) | ✅ Plenty of room |
| Services Running | 12 / 20 | ⚠️ VAULT stack down |
| Ansible Idempotent | ✅ Both nodes pass | ✅ |
| Documentation | ✅ Reconciled this session | ✅ |

---

## Idle GPU — GPU 4 (RTX 5070 Ti, 16 GB)

Node 1 GPU 4 is completely idle. Options:
1. **Speculative decoding draft model** — Qwen3-0.6B as draft for Qwen3-14B/32B, runs on dedicated GPU
2. **Embedding model** — gte-Qwen2-7B already on NFS, or Qwen3-Embedding-0.6B
3. **Second vLLM instance** — Run a smaller model for fast agent tasks
4. **Future ComfyUI** — Image generation on Node 1 for batch processing

Recommendation: Start with embedding model (enables RAG pipeline), then add speculative decoding when we upgrade to Qwen3-32B-AWQ.
