# ADR-002: Network Architecture

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-network-architecture.md](../archive/research/2026-02-15-network-architecture.md)
**Depends on:** ADR-001 (Base Platform)

---

## Context

Athanor has four machines (Node 1, Node 2, VAULT, DEV) sharing a home network with WiFi clients, IoT devices, Lutron lighting, and smart home infrastructure. The existing network hardware includes a UDM Pro gateway, a USW Pro XG 10 PoE (8-port 5GbE switch — currently unused by servers), and a USW Pro 24 PoE (1GbE — all servers currently connected here).

Every server has onboard 5GbE. None are using it. This is the first problem.

The second problem: Node 1 and Node 2 together have 120 GB of VRAM across 6 GPUs. Combining them for multi-node inference requires a fast, low-latency interconnect between the two machines. 5GbE is not sufficient for tensor parallelism — InfiniBand or RoCE is the established solution.

The home network (WiFi, IoT, streaming, smart home) must continue working unchanged.

---

## Decision

### Three network planes

| Plane | Medium | Speed | Purpose |
|-------|--------|-------|---------|
| **Management / Home** | USW Pro 24 PoE (switched) | 1GbE | WiFi APs, IoT, Lutron, DEV, SSH, smart TVs, phones, guest WiFi — all existing home traffic |
| **Data** | USW Pro XG 10 PoE (switched) | 5GbE | NFS storage (VAULT ↔ nodes), service APIs, model loading, dashboard traffic |
| **GPU interconnect** | Direct point-to-point cable | 56 Gbps InfiniBand FDR | Multi-node inference (NCCL/RDMA), GPUDirect, tensor parallelism between Node 1 and Node 2 |

### Topology

```
                    Internet
                       │
                   [UDM Pro]
                       │
          ┌────────────┤
          │            │
  [USW Pro 24 PoE]    [USW Pro XG 10 PoE]
   1GbE home/mgmt      5GbE data plane
   │  │  │  │  │       │     │     │
  APs IoT Lutron DEV  Node1 Node2 VAULT
                       │     │
                       └──┬──┘
                    InfiniBand FDR
                    56 Gbps direct
```

### Specific connections

| Node | Data Plane (5GbE) | GPU Interconnect | Home/Mgmt (1GbE) |
|------|--------------------|------------------|-------------------|
| Node 1 | Intel X550 (onboard) → XG switch | ConnectX-3 FDR (add-in) → direct cable to Node 2 | Second X550 port or separate 1GbE (onboard) |
| Node 2 | Aquantia AQC113 (onboard) → XG switch | ConnectX-3 FDR (add-in, chipset PCIe 4.0 x4 slot) → direct cable to Node 1 | Intel I226-V 2.5GbE (onboard) |
| VAULT | Aquantia (onboard) → XG switch | None needed | RTL8125 2.5GbE (onboard) |
| DEV | WiFi 6 (current) or X540-T2 (add-in, low priority) | None needed | Current WiFi or 1GbE |

### InfiniBand hardware

| Item | Spec | Est. Cost (used) |
|------|------|-------------------|
| 2x Mellanox ConnectX-3 MCX354A-FCBT | Dual-port FDR InfiniBand (56 Gbps) + 40GbE, PCIe 3.0 x8 | $15-50 each |
| 1x QSFP+ DAC cable (0.5-1m) | Passive copper, short run within same chassis | $10-20 |
| **Total** | | **$40-120** |

### VLANs (start simple, extend later)

| VLAN | Subnet | Purpose | When |
|------|--------|---------|------|
| 1 (default) | 192.168.1.0/24 | Management, home devices, existing traffic | Now |
| 10 | 10.0.10.0/24 | Data plane (5GbE server traffic) | Now |
| 20 | 10.0.20.0/24 | IoT isolation | When Home Assistant work begins (ADR-010) |
| 30 | 10.0.30.0/24 | Guest WiFi | When needed |

The InfiniBand link uses its own point-to-point subnet (e.g., 10.0.100.0/30), outside the VLAN structure.

### DNS / Service Discovery

Static `/etc/hosts` managed by Ansible. Services reference each other via `node1.athanor.local`, `node2.athanor.local`, `vault.athanor.local` hostnames with ports in Docker Compose `.env` files.

Move to CoreDNS only if the number of services makes static management painful. For 3-4 nodes and dozens of services, `/etc/hosts` + env vars is sufficient.

### Implementation order

1. **Tier 1 (now, ~$30):** Cat6A cables. Plug Node 1, Node 2, VAULT into USW Pro XG 10 PoE. SFP+ uplink between XG switch and Pro 24 PoE. Instant 10x improvement.
2. **Tier 2 (soon, ~$50-120):** Buy ConnectX-3 FDR cards + QSFP+ cable. Install in both nodes. Configure IB subnet manager and NCCL. Unlocks multi-node 120 GB VRAM inference.
3. **Tier 3 (if needed, deferred to ADR-003):** Faster VAULT link or local NVMe caching. 5GbE may be sufficient for storage traffic — evaluate after measuring actual model loading times.

---

## Home Network Impact

**None.** The home network is unchanged. All WiFi, IoT, Lutron, streaming, and guest devices remain on the USW Pro 24 PoE at 1GbE. The UDM Pro routes between the two switches. When a TV streams from Plex on VAULT, traffic routes through the XG switch's SFP+ uplink to the Pro 24 — the TV's 1GbE port is the bottleneck, which is fine (4K HDR remux peaks at ~100 Mbps).

The InfiniBand link is invisible to the home network — a direct physical cable between two servers.

---

## Why 56 Gbps (Not 100)

The available PCIe slot on Node 2 is chipset-wired at PCIe 4.0 x4, capping effective throughput at ~64 Gbps regardless of the card installed. Upgrading from FDR (56 Gbps) to EDR (100 Gbps) cards gains only ~8 Gbps effective — marginal improvement for 2-3x the cost.

56 Gbps with RDMA handles every Athanor workload:

- Multi-node tensor parallelism for inference: ~40 Gbps effective (NCCL over IB)
- Pipeline parallelism: 1-5 Gbps (trivial)
- GPUDirect RDMA: ~1μs latency vs ~50μs TCP — the latency win matters more than raw bandwidth
- Real-time video generation: 4K@60fps uncompressed ≈ 12 Gbps

The one case where 56G is limiting — distributed training of 70B+ models from scratch — is a data center workload, not a homelab one. LoRA/QLoRA fine-tuning runs on a single GPU and doesn't need the interconnect.

---

## What This Enables

- **120 GB combined VRAM** across 6 GPUs for running larger models than either node can handle alone
- **2-minute model loads** from VAULT instead of 21 minutes (5GbE vs 1GbE for 70B FP16)
- **GPUDirect RDMA** between nodes — GPU memory transfers without CPU involvement
- **Clean traffic separation** — GPU traffic, storage traffic, and home traffic on independent paths
- **Future growth** — adding nodes or upgrading links doesn't require redesigning the network

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Stay at 1GbE | 21-minute model loads. Multi-node inference impractical. Wastes existing 5GbE hardware. |
| 5GbE only (no InfiniBand) | Works for storage and APIs but tensor parallelism over TCP is inefficient. Leaves 56 GB of Node 2 VRAM stranded from Node 1 for large models. |
| 100GbE switched fabric | $1000+ for a switch. Direct point-to-point achieves the same result for $50-120. Overkill for 2 compute nodes. |
| EDR InfiniBand (100G) | Node 2's x4 slot caps at ~64 Gbps. Marginal gain over FDR at 2-3x the cost. Upgrade path exists if FDR proves insufficient. |
| 25GbE Ethernet (ConnectX-4 Lx) | Cheaper than 100G but no native RDMA (needs RoCE config). InfiniBand FDR is the same price and has native RDMA. |

---

## Risks

- **Physical clearance in Node 2:** ConnectX-3 card must fit below the RTX 4090 in the chipset PCIe slot. Verify during install — if it doesn't fit, a low-profile ConnectX-3 variant exists.
- **Used hardware DOA:** ConnectX-3 cards are $15-50 used. Buy from a seller with returns. At these prices, buying a spare is cheap insurance.
- **Subnet manager setup:** InfiniBand requires an SM (OpenSM). One node runs it. Straightforward on Ubuntu but it's a configuration step that doesn't exist for Ethernet.

---

## Sources

- [vLLM Parallelism and Scaling docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- [vLLM multi-node discussion #10118](https://github.com/vllm-project/vllm/discussions/10118)
- [ROCm Blog — vLLM MoE Playbook](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html)
- [InfiniBand homelab guide (40G)](https://blog.patshead.com/2021/02/40-gigabit-infiniband-an-inexpensive-performance-boost-for-your-home-network.html)
- [ConnectX-3 FDR deal (ServeTheHome)](https://www.servethehome.com/mellanox-56gbps-infiniband-40gbe-dual-port-connectx3-vpi-deal/)
- [ASUS ProArt X870E-CREATOR WIFI specs](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)
- [ASRock Rack ROMED8-2T specs](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)
