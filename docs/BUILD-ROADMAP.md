# Athanor Build Roadmap

*Research phase complete. This is the build plan.*

Last updated: 2026-02-15

---

## Phase 0: Foundation (current)

- [ ] Get DHCP IPs for Node 1 and Node 2 (check JetKVM consoles or UDM DHCP leases)
- [ ] SSH into both nodes with athanor/athanor2026
- [ ] Verify Samsung 990 PRO 4TB physical seat on Node 1 (not detected in audit)
- [ ] Reconnect JetKVM ATX power cable on Node 2
- [ ] Move Node 1 + Node 2 ethernet to USW Pro XG 10 PoE (10GbE data plane)

## Phase 1: NVIDIA + Docker (ADR-001 validation)

- [ ] Install NVIDIA driver 570+ (open modules) on Node 1 — **4x 5070 Ti validation spike**
- [ ] Install NVIDIA driver 570+ (open modules) on Node 2 — 5090 + 4090
- [ ] Install Docker Engine on both nodes
- [ ] Install NVIDIA Container Toolkit on both nodes
- [ ] Test: `docker run --gpus all nvidia/cuda:12.8.0-base nvidia-smi` on both
- [ ] Verify all 4 GPUs visible on Node 1, both GPUs visible on Node 2

## Phase 2: Storage + Network (ADR-002, ADR-003)

- [ ] Configure NFS exports on VAULT (/mnt/user/data, /mnt/user/models)
- [ ] Mount NFS shares on both nodes (fstab entries)
- [ ] Verify 10GbE throughput between nodes and VAULT (iperf3)
- [ ] Set static IPs or DHCP reservations for all nodes
- [ ] Order Mellanox ConnectX-3 FDR InfiniBand cards (2x, ~$30 each on eBay)

## Phase 3: First Services (ADR-005, ADR-006, ADR-007)

- [ ] Deploy vLLM on Node 1 — single GPU test first
- [ ] Scale vLLM to tensor-parallel-size=4 with NVFP4
- [ ] Deploy ComfyUI on Node 2 pinned to RTX 5090
- [ ] Deploy Open WebUI on Node 2 pointing to vLLM
- [ ] Test end-to-end: chat via Open WebUI → vLLM inference on Node 1
- [ ] Test image generation: ComfyUI with Flux dev on 5090

## Phase 4: Monitoring (ADR-009)

- [ ] Deploy Prometheus on VAULT
- [ ] Deploy Grafana on VAULT
- [ ] Install node_exporter on Node 1 + Node 2
- [ ] Install dcgm-exporter on Node 1 + Node 2
- [ ] Import DCGM dashboard (#12239) and Node Exporter dashboard (#1860)
- [ ] Set up critical alerts (GPU overtemp, disk full, service down)

## Phase 5: Supporting Services (ADR-010, ADR-011)

- [ ] Deploy Home Assistant on VAULT (Docker, host networking)
- [ ] Configure Lutron integration (.158)
- [ ] Configure UniFi integration (UDM Pro)
- [ ] Verify/deploy Plex with Arc A380 transcoding on VAULT
- [ ] Deploy Sonarr + Radarr + Prowlarr on VAULT
- [ ] Set up TRaSH Guides path structure on VAULT
- [ ] Deploy SABnzbd + qBittorrent (with Gluetun VPN)
- [ ] Deploy Stash on VAULT
- [ ] Deploy Tautulli on VAULT

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
