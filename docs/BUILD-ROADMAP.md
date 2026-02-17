# Athanor Build Roadmap

*Research phase complete. This is the build plan.*

Last updated: 2026-02-16 (Hybrid architecture planning, companion tools evaluation)

---

## Phase 0: Foundation

- [x] Get DHCP IPs for Node 1 and Node 2 — Node 1: .244/.246, Node 2: .225
- [x] SSH into both nodes with athanor/athanor2026
- [ ] Verify Samsung 990 PRO 4TB physical seat on Node 1 (not detected in audit) *(physical)*
- [ ] Reconnect JetKVM ATX power cable on Node 2 *(physical)*
- [ ] Move Node 1 + Node 2 ethernet to USW Pro XG 10 PoE (10GbE data plane) *(physical)*

## Phase 1: NVIDIA + Docker (ADR-001 validation)

### Node 1 (EPYC 7663 56C/112T, 224 GB ECC DDR4) — COMPLETE
- [x] Upgrade to HWE kernel 6.17.0-14-generic
- [x] Install NVIDIA driver 580.126.09 (open modules) — **4x 5070 Ti validation spike PASSED**
- [x] Install Docker Engine 29.2.1 + Compose v5.0.2
- [x] Install NVIDIA Container Toolkit, configure Docker runtime
- [x] Test: `docker run --gpus all nvidia/cuda:12.8.0-base nvidia-smi` — **all 4 GPUs visible**

### Node 2 (Threadripper 7960X 24C/48T, 128 GB DDR5) — COMPLETE
- [x] Upgrade to HWE kernel 6.17.0-14-generic
- [x] Install NVIDIA driver 580.126.09 (open modules) — RTX 5090 + RTX 4090
- [x] Install Docker Engine 29.2.1 + Compose v5.0.2
- [x] Install NVIDIA Container Toolkit, configure Docker runtime
- [x] Test: `docker run --gpus all nvidia/cuda:12.8.0-base nvidia-smi` — **both GPUs visible**
- [x] RTX 4090 (24,564 MiB) + RTX 5090 (32,607 MiB) = 57.2 GB VRAM confirmed

## Phase 2: Storage + Network (ADR-002, ADR-003)

- [x] Configure NFS exports on VAULT (/mnt/user/data, /mnt/user/models, /mnt/user/appdata, /mnt/user/system) — already configured
- [x] Mount NFS shares on both nodes (fstab entries) — /mnt/vault/{models,data,appdata}
- [ ] Verify 10GbE throughput between nodes and VAULT (iperf3)
- [x] Set static IPs on Node 1 (.244/.246) and Node 2 (.225) — netplan configs, dual default route fix
- [ ] Order Mellanox ConnectX-3 FDR InfiniBand cards (2x, ~$30 each on eBay)

## Phase 3: First Services (ADR-005, ADR-006, ADR-007) — COMPLETE

- [x] Deploy vLLM on Node 1 — **Qwen3-32B-AWQ, TP=4 across 4x 5070 Ti, NGC vLLM 25.12 (0.11.1)**
- [x] vLLM API serving at http://192.168.1.244:8000 (OpenAI-compatible)
- [x] Upgraded from Qwen3-14B to Qwen3-32B-AWQ — 15.6 GB/GPU, 32K context
- [x] Deploy ComfyUI on Node 2 pinned to RTX 5090 — http://192.168.1.225:8188
  - Custom image (athanor/comfyui:blackwell) built from NGC PyTorch base for Blackwell compat
  - ComfyUI 0.13.0, PyTorch 2.7.0a0, 32 GB VRAM
- [x] Deploy Open WebUI on Node 2 pointing to vLLM — http://192.168.1.225:3000
- [x] Test end-to-end: chat via Open WebUI → vLLM inference on Node 1
- [x] Download Flux models for ComfyUI — FP8 dev (12 GB), CLIP-L, T5-XXL FP8, VAE (~17 GB total)
- [x] Deploy vLLM on Node 2 RTX 4090 — **Qwen3-14B-AWQ, awq_marlin, ~92 tok/s**
  - http://192.168.1.225:8000 (OpenAI-compatible)
  - 9.4 GB model, 21.5 GB VRAM used, 32K context
  - Tool calling enabled (hermes parser)

## Phase 4: Monitoring (ADR-009) — COMPLETE

- [x] Deploy Prometheus on VAULT
- [x] Deploy Grafana on VAULT — http://192.168.1.203:3000
- [x] Install node_exporter on Node 1 + Node 2
- [x] Install dcgm-exporter on Node 1 + Node 2
- [x] Import DCGM dashboard (#12239) and Node Exporter dashboard (#1860)
- [x] Set up critical alerts (GPU overtemp >85C, disk >90%, service down)

## Phase 5: Supporting Services (ADR-010, ADR-011)

- [x] Deploy Home Assistant on VAULT (Docker, host networking) — http://192.168.1.203:8123
- [x] Complete HA onboarding
- [ ] Configure Lutron (.158) + UniFi integrations in HA
- [x] Deploy Plex on VAULT — http://192.168.1.203:32400/web (needs claim)
- [x] Deploy Sonarr + Radarr + Prowlarr on VAULT
- [x] Set up TRaSH Guides path structure — /mnt/user/data/{torrents,usenet,media}/{movies,tv,music}
- [x] Configure Sonarr root folder (/data/media/tv) + Radarr root folder (/data/media/movies)
- [x] Deploy SABnzbd on VAULT
- [ ] Deploy qBittorrent (with Gluetun VPN) — compose ready, NordVPN credentials need update
- [x] Deploy Stash on VAULT (was already running)
- [x] Deploy Tautulli on VAULT
- [x] Install Aider 0.86.2 + Goose 1.24.0 on Node 2

## Phase 6: Dashboard + Agents (ADR-007, ADR-008)

- [x] Scaffold Next.js 16 dashboard project — projects/dashboard/
  - App Router, TypeScript, Tailwind v4, shadcn/ui
  - Dark theme, sidebar navigation
- [x] Dashboard home page — node cards, service health summary, GPU utilization bars
- [x] GPU metrics page — per-GPU temp/util/memory/power from Prometheus/DCGM
- [x] Chat page — streaming SSE chat with vLLM via API proxy
- [x] Services page — health checks for all running services
- [x] API routes: /api/chat (vLLM proxy), /api/services, /api/models
- [x] Deploy dashboard to Node 2 — http://192.168.1.225:3001 (Docker standalone)
- [x] Set up LangGraph agent framework on Node 1 — http://192.168.1.244:9000
  - FastAPI server, OpenAI-compatible API, Docker with host networking
  - vLLM tool calling enabled (hermes parser)
- [x] First agent: General Assistant — tools: service health, GPU metrics, vLLM models, storage
- [x] Media Agent — tools: TV search/add/calendar/queue (Sonarr), movie search/add/calendar/queue (Radarr), Plex activity/history/libraries (Tautulli)
- [ ] Home Agent (HA API)

## Phase 7: Ansible + Hardening

- [x] Set static IPs on both nodes (netplan, removed cloud-init DHCP)
- [x] Write Ansible inventory (Node 1, Node 2, VAULT) with host/group vars
- [x] Common role: packages, NFS mounts, timezone, UFW firewall
- [x] NVIDIA role: driver install, GPU count validation
- [x] Docker role: Docker CE, Compose, NVIDIA Container Toolkit, daemon.json
- [x] Monitoring role: node_exporter + dcgm-exporter containers
- [x] Playbooks: site.yml, common.yml, node1.yml, node2.yml
- [ ] Configure BMC at .216 (set static IP, change default creds)

## Phase 8: Hardware Reconfiguration (Hybrid Architecture)

See `docs/research/2026-02-16-hybrid-system-architecture.md` for full design.

**Strategy**: Cloud APIs for frontier coding models (50-100+ tok/s). Local for everything that needs to be uncensored, private, always-on, or GPU-accelerated.

### Node 1 → "Foundry" (6 GPUs, 100 GB VRAM) *(physical)*
- [ ] Move RTX 3060 from DEV → Node 1 (slot 6)
- [ ] Move Node 1 into mining GPU enclosure with PCIe risers
- [ ] Install dual PSU (parts available: SF1000L + one of RM750/EVGA 600B)
- [ ] Wire Add2PSU adapter for sync start
- [ ] Validate all 6 GPUs visible: 4x 5070 Ti (64 GB) + 4090 (24 GB) + 3060 (12 GB)

### Node 2 → "Workshop" (5090, 32 GB VRAM)
- [ ] Keep RTX 5090 on Node 2 (sole GPU until future Max-Q)
- [ ] Swap X870E ↔ TRX50 motherboard between DEV and Node 2 *(physical, future)*
- [ ] Install 64 GB loose DDR5 kit → 192 GB total *(physical)*

### InfiniBand (optional, $75)
- [ ] Install ConnectX-3 FDR cards in Node 1 + Node 2
- [ ] Direct cable between nodes
- [ ] Install OFED drivers, configure IPoIB
- [ ] Test NCCL over InfiniBand
- [ ] Pipeline parallelism across nodes for large MoE models

## Phase 9: Claude Code Companion Tools — COMPLETE

- [x] **Grafana MCP** (`@leval/mcp-grafana`) — added to `.mcp.json`, needs Grafana password verification
- [x] **ccusage** — works via `npx ccusage@latest`. $117.34 across first 4 days of Athanor build.
- [x] **Docker MCP** — skipped (local-only, useless for remote nodes)
- [x] **Home Assistant MCP** — skipped (HA onboarding not complete yet)
- [x] **Homelab MCP** — skipped (Python-only, local Docker socket, overlaps with Desktop Commander)
- [x] **ccflare** — skipped (full proxy server, overkill for single user — ccusage sufficient)
- [x] **Skill collections** — all skipped (obra/superpowers, Claude Command Suite, cc-devops-skills). Our 5 custom commands + 7 skills + 4 hooks are better tailored. Generic frameworks add context bloat and risk conflicting with CLAUDE.md workflow.

---

## Physical Tasks (Shaun only)

These require hands at the rack:
- Verify Samsung 990 PRO seat on Node 1
- Move ethernet cables to 10GbE switch
- Reconnect JetKVM ATX power cable on Node 2
- Move RTX 3060 from DEV → Node 1
- Move Node 1 into mining GPU enclosure with risers + dual PSU
- Install 64 GB DDR5 kit in Node 2 (or VAULT donor RAM after swap)
- Install InfiniBand cards (when purchased)
- Install Hyper M.2 adapter in Node 1 (for NVMe expansion, ADR-003)
- Future: Swap X870E ↔ TRX50 motherboard between DEV and Node 2

---

## Blocked / Needs Shaun

- **HA onboarding**: Navigate to http://192.168.1.203:8123 in a browser to complete initial setup
- ~~**Grafana MCP auth**~~: Done — password reset to newpass123, compose + .mcp.json updated
- **HA MCP**: Install after HA onboarding is complete (needs long-lived access token)
- **qBittorrent VPN**: NordVPN token/credentials need updating in Gluetun config
- ~~**Plex claim**~~: Done — claimed with token, healthy on host networking
- ~~**Flux models**~~: Done — FP8 dev + text encoders + VAE downloaded

---

## Purchase List

| Item | Est. Cost | Priority | Notes |
|------|-----------|----------|-------|
| Mining GPU enclosure (6-8 slot) | ~$100-200 | High | For Node 1 6-GPU build |
| Add2PSU adapter | ~$10-15 | High | Sync dual PSUs |
| PCIe riser cables (6x) | ~$30-50 | High | For mining enclosure |
| 2x Mellanox ConnectX-3 FDR (56G IB) | ~$60 | Medium | ADR-002, pipeline parallelism |
| 1x QSFP+ FDR cable (1-2m) | ~$15 | Medium | ADR-002 |
| 1-2x 24TB HDD (VAULT expansion) | ~$600-800 | Low | ADR-003 |
| NVIDIA PRO 6000 Max-Q (96 GB) | ~$4,500-8,000 | Deferred | Node 2 second GPU — revisit when pricing stabilizes |
