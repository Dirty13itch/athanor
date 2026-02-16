# Athanor Build Roadmap

*Research phase complete. This is the build plan.*

Last updated: 2026-02-16 (Phase 3 vLLM deployed, Phase 4 monitoring deployed, Phase 5 media+HA deployed)

---

## Phase 0: Foundation

- [x] Get DHCP IPs for Node 1 and Node 2 — Node 1: .244/.246, Node 2: .225
- [x] SSH into both nodes with athanor/athanor2026
- [ ] Verify Samsung 990 PRO 4TB physical seat on Node 1 (not detected in audit) *(physical)*
- [ ] Reconnect JetKVM ATX power cable on Node 2 *(physical)*
- [ ] Move Node 1 + Node 2 ethernet to USW Pro XG 10 PoE (10GbE data plane) *(physical)*

## Phase 1: NVIDIA + Docker (ADR-001 validation)

### Node 1 — COMPLETE
- [x] Upgrade to HWE kernel 6.17.0-14-generic
- [x] Install NVIDIA driver 580.126.09 (open modules) — **4x 5070 Ti validation spike PASSED**
- [x] Install Docker Engine 29.2.1 + Compose v5.0.2
- [x] Install NVIDIA Container Toolkit, configure Docker runtime
- [x] Test: `docker run --gpus all nvidia/cuda:12.8.0-base nvidia-smi` — **all 4 GPUs visible**

### Node 2 — COMPLETE
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
- [ ] Set static IPs or DHCP reservations for all nodes
- [ ] Order Mellanox ConnectX-3 FDR InfiniBand cards (2x, ~$30 each on eBay)

## Phase 3: First Services (ADR-005, ADR-006, ADR-007)

- [x] Deploy vLLM on Node 1 — **Qwen3-14B, TP=4 across all 4x 5070 Ti, NVIDIA NGC vLLM 25.12 (0.11.1)**
- [x] vLLM API serving at http://192.168.1.244:8000 (OpenAI-compatible)
- [ ] Scale to Qwen3-32B-AWQ (available on VAULT NFS)
- [ ] Deploy ComfyUI on Node 2 pinned to RTX 5090
- [x] Deploy Open WebUI on Node 2 pointing to vLLM — http://192.168.1.225:3000
- [x] Test end-to-end: chat via Open WebUI → vLLM inference on Node 1
- [ ] Test image generation: ComfyUI with Flux dev on 5090

## Phase 4: Monitoring (ADR-009) — COMPLETE

- [x] Deploy Prometheus on VAULT
- [x] Deploy Grafana on VAULT — http://192.168.1.203:3000
- [x] Install node_exporter on Node 1 + Node 2
- [x] Install dcgm-exporter on Node 1 + Node 2
- [x] Import DCGM dashboard (#12239) and Node Exporter dashboard (#1860)
- [ ] Set up critical alerts (GPU overtemp, disk full, service down)

## Phase 5: Supporting Services (ADR-010, ADR-011)

- [x] Deploy Home Assistant on VAULT (Docker, host networking) — http://192.168.1.203:8123
- [ ] Configure Lutron integration (.158)
- [ ] Configure UniFi integration (UDM Pro)
- [x] Deploy Plex on VAULT — http://192.168.1.203:32400/web (needs claim)
- [x] Deploy Sonarr + Radarr + Prowlarr on VAULT
- [ ] Set up TRaSH Guides path structure on VAULT
- [x] Deploy SABnzbd on VAULT
- [ ] Deploy qBittorrent (with Gluetun VPN)
- [x] Deploy Stash on VAULT (was already running)
- [x] Deploy Tautulli on VAULT
- [x] Install Aider 0.86.2 + Goose 1.24.0 on Node 2

## Phase 6: Dashboard + Agents (ADR-007, ADR-008)

- [ ] Scaffold Next.js dashboard project
- [ ] System health panel (Prometheus API)
- [ ] GPU panel (DCGM metrics)
- [ ] Chat integration (Open WebUI embed or API)
- [ ] Set up LangGraph agent framework on Node 1
- [ ] First agent: General Assistant
- [ ] Media Agent (Sonarr/Radarr/Tautulli APIs)
- [ ] Home Agent (HA API)

## Phase 7: Ansible + Hardening

- [ ] Write Ansible inventory (Node 1, Node 2, VAULT)
- [ ] Common playbook: users, SSH keys, firewall, NFS mounts
- [ ] Node 1 playbook: NVIDIA drivers, Docker, multi-GPU config
- [ ] Node 2 playbook: NVIDIA drivers, Docker, GPU isolation
- [ ] Set static IPs, configure BMC at .216

## Phase 8: InfiniBand + Multi-Node (ADR-002, ADR-005)

- [ ] Install ConnectX-3 FDR cards in Node 1 + Node 2
- [ ] Direct cable between nodes
- [ ] Install OFED drivers, configure IPoIB
- [ ] Test NCCL over InfiniBand
- [ ] Multi-node vLLM via Ray for 120 GB combined VRAM

---

## Physical Tasks (Shaun only)

These require hands at the rack:
- Verify Samsung 990 PRO seat on Node 1
- Move ethernet cables to 10GbE switch
- Reconnect JetKVM ATX power cable on Node 2
- Install InfiniBand cards (when purchased)
- Install Hyper M.2 adapter in Node 1 (for NVMe expansion, ADR-003)

---

## Purchase List

| Item | Est. Cost | Priority | ADR |
|------|-----------|----------|-----|
| 2x Mellanox ConnectX-3 FDR (56G IB) | ~$60 | Medium | ADR-002 |
| 1x QSFP+ FDR cable (1-2m) | ~$15 | Medium | ADR-002 |
| 1-2x 24TB HDD (VAULT expansion) | ~$600-800 | Low | ADR-003 |
