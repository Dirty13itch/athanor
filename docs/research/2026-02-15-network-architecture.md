# Network Architecture

**Date:** 2026-02-15
**Status:** In progress
**Supports:** ADR-002 (Network Architecture)
**Depends on:** ADR-001 (Base Platform — Ubuntu + Docker Compose + Ansible)

---

## The Question

How should Athanor's nodes be connected? What network topology, speeds, VLANs, and DNS/discovery model gets the most out of the hardware?

This decision determines:
- How fast models load from VAULT to compute nodes
- Whether multi-node GPU inference is possible (splitting models across Node 1 + Node 2)
- How services on different nodes find and talk to each other
- How traffic types are isolated (GPU, storage, management, IoT)
- What Shaun's daily experience looks like (fast file transfers, responsive dashboard)

---

## Current State (Wasteful)

Right now, **every server connects at 1GbE** through the USW Pro 24 PoE, despite every server having onboard 10GbE and an 8-port 10GbE switch sitting unused in the rack.

| Node | Onboard Network | Current Connection | Switch |
|------|----------------|-------------------|--------|
| Node 1 | 2x Intel X550 10GbE | 1GbE | USW Pro 24 PoE |
| Node 2 | Aquantia AQC113 10GbE + Intel 2.5GbE + WiFi 7 | 1GbE | USW Pro 24 PoE |
| VAULT | Aquantia 10GbE + RTL8125 2.5GbE + Thunderbolt 4 | 1GbE | USW Pro 24 PoE |
| DEV | Intel I225-V 1GbE + WiFi 6 | 1GbE WiFi | USW Pro 24 PoE (WiFi via U6 AP) |

**Existing network hardware (unused or underused):**

| Device | Ports | Current Use |
|--------|-------|-------------|
| USW Pro XG 10 PoE | 8x 10GbE RJ45 + 4x 10G SFP+ | **Nothing. Powered on, no server connections.** |
| USW Pro 24 PoE | 24x 1GbE + 2x 10G SFP+ | All servers here at 1GbE |
| UDM Pro | Gateway | Routing, DHCP, firewall |
| 3x X540-T2 / clones (loose) | 6x 10GbE RJ45 total | Not installed |

This is the networking equivalent of driving a Ferrari in first gear.

---

## What Athanor Needs from Its Network

From VISION.md and the full system architecture:

### 1. Storage Traffic (Node ↔ VAULT)

Compute nodes load AI models, game assets, media, and datasets from VAULT's 164 TB array over NFS.

| Workload | Size | At 1GbE (~110 MB/s) | At 10GbE (~1.1 GB/s) | At 25GbE (~3 GB/s) |
|----------|------|---------------------|----------------------|---------------------|
| 70B model (FP16) | ~140 GB | 21 min | 2.1 min | 47 sec |
| 70B model (Q4) | ~40 GB | 6 min | 36 sec | 13 sec |
| Flux image model | ~12 GB | 1.8 min | 11 sec | 4 sec |
| ComfyUI workflow assets | ~2-5 GB | 18-45 sec | 2-5 sec | <2 sec |
| EoBQ game assets | Varies | — | — | — |

**Important caveat:** These times assume the source can feed data at full network speed. VAULT's HDD array reads at 150-250 MB/s (single drive, no striping). A 70B FP16 model on VAULT HDD takes ~9-15 min regardless of network speed. **Models must be on VAULT's NVMe cache (or local NVMe) to benefit from 10GbE.** See ADR-003 (Storage Architecture) for the full tiered storage strategy.

Models are loaded once and stay in VRAM, so this is startup latency, not sustained throughput. **10GbE makes model loading from NVMe-backed storage tolerable. Local NVMe makes it fast.** 1GbE is painful for large models.

### 2. Inter-Node GPU Traffic (Node 1 ↔ Node 2)

If we ever split a model across both nodes (multi-node inference), the interconnect between Node 1 and Node 2 becomes critical.

**vLLM multi-node parallelism options:**

| Strategy | How It Works | Network Need | Source |
|----------|-------------|--------------|--------|
| **Pipeline parallelism** | Different model layers on different nodes. Data flows sequentially between stages. | Standard Ethernet works. Latency matters but bandwidth is moderate. | [vLLM docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/) |
| **Tensor parallelism** | Same layer split across GPUs on different nodes. Requires all-reduce operations every layer. | **High bandwidth + low latency required.** InfiniBand or RoCE recommended. Standard TCP sockets are "not efficient." | [vLLM docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/), [vLLM discussion #10118](https://github.com/vllm-project/vllm/discussions/10118) |
| **Data parallelism** | Same model on both nodes, different requests. No inter-node GPU communication. | Minimal. Just load balancing. | [vLLM data parallel docs](https://docs.vllm.ai/en/latest/serving/data_parallel_deployment/) |

**The recommended practice** for multi-node vLLM: tensor parallelism within a node (across its GPUs), pipeline parallelism between nodes. This works over standard Ethernet. ([ROCm blog](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html))

But if you want tensor parallelism across nodes (maximum performance), you need InfiniBand or RoCE. This is where a direct high-speed link between Node 1 and Node 2 would unlock capability that 10GbE alone can't.

**What multi-node inference unlocks:**

| Configuration | Total VRAM | Can Run |
|---------------|-----------|---------|
| Node 1 alone | 64 GB (4x 5070 Ti) | 70B Q4-Q6, multiple smaller models |
| Node 2 alone | 56 GB (5090 + 4090) | 70B Q4, large single models on 5090 |
| Node 1 + Node 2 combined | 120 GB (6 GPUs) | 70B FP16 unquantized, 120B+ models, Llama 405B at Q2-Q3 |

120 GB combined VRAM is serious capability. Whether it's worth the complexity depends on model sizes, but having the option is valuable — especially as open models keep growing.

### 3. Service-to-Service Traffic (APIs, Dashboard, Agents)

HTTP calls between containers on different nodes: agent → inference API, dashboard → all services, agent → Plex API on VAULT, etc.

**Bandwidth need: negligible.** These are small JSON payloads. 1GbE is more than enough. Even 100 Mbps would be fine.

**Latency matters slightly** for the chat interface (user waits for inference response), but network latency at 1GbE (sub-millisecond on LAN) is invisible compared to inference latency (seconds).

### 4. Media Streaming

Plex streaming from VAULT. 4K HDR Blu-ray remux = ~80-100 Mbps. **1GbE handles this easily.** 10GbE is irrelevant for streaming.

### 5. Management, IoT, Home Automation

SSH, monitoring agents, Home Assistant device communication, Lutron (.158), UniFi APs, smart devices. All tiny. 1GbE or less.

### 6. Normal Home Network Traffic

Athanor lives on a home network that also serves WiFi clients (phones, tablets, laptops), smart TVs, Lutron lighting, IoT devices, and guest WiFi. This traffic is **completely unaffected** by any server network changes because the architecture uses physically separate paths:

- **Home devices** stay on the USW Pro 24 PoE at 1GbE (or via WiFi APs). Nothing changes for them.
- **Servers** move to the USW Pro XG 10 PoE at 10GbE. Separate switch, separate cables.
- **UDM Pro routes between them.** When a TV streams from Plex on VAULT, traffic routes: VAULT (10GbE) → XG switch → SFP+ uplink → Pro 24 (1GbE) → TV. The TV's 1GbE port is the bottleneck, which is fine — 4K HDR remux is ~100 Mbps.
- **The InfiniBand link is invisible to the home network.** It's a direct point-to-point cable between two servers. No switch, no routing, no impact on anything else.

The home network doesn't need to be redesigned. It works as-is. The only physical change is plugging three new cables into the XG switch for the servers.

---

## Available PCIe Slots for Network Expansion

This constrains what NICs each node can accept.

### Node 1 (ROMED8-2T)

7x PCIe 4.0 slots total. 4 occupied by RTX 5070 Ti GPUs. **3 slots available** for expansion (NICs, HBAs, Hyper M.2 adapters, etc.). PCIe 4.0 x16 each from CPU. ([ASRock Rack ROMED8-2T specs](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T))

**Plenty of room.** Can add InfiniBand, additional 10GbE, or any other NIC.

### Node 2 (ProArt X870E-CREATOR WIFI)

3 PCIe slots total:
- 2x PCIe 5.0 x16 (from CPU) — **both occupied by RTX 5090 + RTX 4090**
- 1x PCIe 4.0 x16 (from chipset, wired at x4) — **AVAILABLE**

([ASUS ProArt X870E specs](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/))

That chipset slot runs at PCIe 4.0 x4 = ~8 GB/s = ~64 Gbps. Enough for:
- 56 Gbps InfiniBand (ConnectX-3 FDR) — fits perfectly
- 25GbE (ConnectX-4 Lx) — fits easily
- 40GbE (ConnectX-3) — fits
- 100GbE (ConnectX-5) — would be bottlenecked to ~64 Gbps by the x4 slot, but still faster than 10GbE

### VAULT (TRX50 AERO D)

Multiple PCIe slots. LSI SAS3224 occupies one. Others available. But VAULT's high-speed connection goes through its onboard Aquantia 10GbE to the switch. Adding a faster NIC to VAULT would require the switch to also be faster, or a direct link.

### DEV

1GbE + WiFi 6. Could add a loose X540-T2 for 10GbE if desired. Low priority — DEV accesses the system via browser and SSH, not bulk data transfer.

---

## Network Tiers

Three tiers of network capability, each building on the previous.

### Tier 0: Current (1GbE) — What We Have Now

All servers at 1GbE. Painful for model loading. Functional for everything else.

**Cost:** $0 (already in place)
**Model load (70B FP16):** ~21 minutes
**Multi-node inference:** Not practical

### Tier 1: 10GbE Switched — Use What's Already There

Move server connections to the USW Pro XG 10 PoE. All three servers have onboard 10GbE. Just need Cat6A cables (or existing cables if they're Cat6A).

```
[UDM Pro]
    │
[USW Pro 24 PoE] ── 1GbE: IoT, APs, Lutron, management
    │ (SFP+ uplink)
[USW Pro XG 10 PoE] ── 10GbE: Node 1, Node 2, VAULT
```

| Connection | Speed | How |
|------------|-------|-----|
| Node 1 → XG switch | 10 GbE | Intel X550 (onboard) → RJ45 |
| Node 2 → XG switch | 10 GbE | Aquantia AQC113 (onboard) → RJ45 |
| VAULT → XG switch | 10 GbE | Aquantia (onboard) → RJ45 |
| XG ↔ Pro 24 | 10G SFP+ | SFP+ uplink between switches |

**Cost:** ~$20-40 for Cat6A cables (if not already available)
**Model load (70B FP16):** ~2 minutes
**Multi-node inference:** Pipeline parallelism works. Tensor parallelism limited by 10GbE latency.

**This is the obvious first step. Do this immediately.**

### Tier 2: Direct High-Speed Link (Node 1 ↔ Node 2) — The Unlock

Add a point-to-point InfiniBand or high-speed Ethernet link directly between the two compute nodes. No switch needed — just two NICs and a cable.

**Option A: InfiniBand FDR (56 Gbps) — Best value**

| Item | Price (eBay used) | Source |
|------|-------------------|--------|
| 2x Mellanox ConnectX-3 MCX354A-FCBT (dual-port FDR IB + 40GbE) | ~$15-50 each | [eBay](https://www.ebay.com/p/1601710566), [ServeTheHome](https://www.servethehome.com/mellanox-56gbps-infiniband-40gbe-dual-port-connectx3-vpi-deal/) |
| 1x QSFP+ copper cable (1-3m) | ~$10-20 | eBay/Amazon |
| **Total** | **~$40-120** | |

- 56 Gbps with RDMA — low-latency GPU-to-GPU communication
- PCIe 3.0 x8 card fits in both nodes' available slots
- Supports GPUDirect RDMA for vLLM tensor parallelism across nodes
- Linux InfiniBand support is mature (OFED drivers, or inbox kernel modules)
- Setup is straightforward — [documented for homelabs](https://blog.patshead.com/2021/02/40-gigabit-infiniband-an-inexpensive-performance-boost-for-your-home-network.html)

**Option B: 100GbE Ethernet (ConnectX-5)**

| Item | Price (eBay used) |
|------|-------------------|
| 2x Mellanox ConnectX-5 MCX516A-CDAT (dual-port 100GbE) | ~$80-150 each |
| 1x QSFP28 DAC cable (1-3m) | ~$15-30 |
| **Total** | **~$175-330** |

- 100 Gbps Ethernet with optional RoCE (RDMA over Converged Ethernet)
- PCIe 3.0 x16 card — fits in Node 1, fits in Node 2's x4 slot but bottlenecked to ~64 Gbps
- RoCE can approximate InfiniBand performance for NCCL/vLLM when tuned properly
- Also backward compatible with 25/40/50GbE

**Option C: InfiniBand EDR (100 Gbps) — ConnectX-4/5 VPI**

| Item | Price (eBay used) |
|------|-------------------|
| 2x Mellanox ConnectX-4 MCX455A-ECAT (EDR IB 100G) | ~$50-100 each |
| 1x QSFP28 cable | ~$15-30 |
| **Total** | **~$115-230** |

- 100 Gbps InfiniBand with full RDMA
- Same Node 2 slot bottleneck as Option B (~64 Gbps effective)
- Best latency of any option

**Recommendation for Tier 2:** Option A (ConnectX-3 FDR at 56 Gbps) is the sweet spot. It's absurdly cheap ($40-120 total), provides RDMA for multi-node tensor parallelism, and fits in both nodes without bottleneck. The 56 Gbps is 5.6x faster than 10GbE and sufficient for vLLM cross-node communication. Option C (EDR 100G) is worth considering if prices are close, but Node 2's x4 slot caps effective throughput at ~64 Gbps anyway, so the extra speed of 100G vs 56G has diminishing returns.

**What this unlocks:**
- Multi-node tensor parallelism in vLLM — combine 120 GB VRAM across 6 GPUs
- GPUDirect RDMA — GPU memory on Node 1 can read/write GPU memory on Node 2 without CPU involvement
- Future flexibility — as models grow beyond what one node can handle, the interconnect is ready

### Is 56 Gbps Enough?

Mapping every bandwidth-intensive Athanor use case against the FDR InfiniBand link:

| Use Case | Bandwidth Needed | 56 Gbps Sufficient? |
|----------|-----------------|---------------------|
| Multi-node tensor parallelism (vLLM all-reduce) | ~40 Gbps effective on FDR IB (NCCL benchmarks). Data center clusters use 200-400G but those are 8-GPU DGX nodes. | **Yes** — functional for 2-node, 6-GPU inference |
| Pipeline parallelism (vLLM) | ~1-5 Gbps peak (sequential layer-to-layer) | **Easily** — even 10GbE handles this |
| Bulk model transfer between nodes | 140 GB @ 56 Gbps ≈ 20 sec | **Yes** |
| GPUDirect RDMA (GPU↔GPU memory) | Latency matters more than bandwidth. IB RDMA: ~1μs vs TCP: ~50μs | **Yes** — RDMA is the real win |
| Real-time video generation pipeline | 4K @ 60fps uncompressed ≈ 12 Gbps | **Yes** |
| LoRA/QLoRA fine-tuning | Runs on single GPU, no inter-node traffic | **N/A** |
| Large-scale distributed training (gradient sync) | 70B model gradient all-reduce: ~280 GB per step → ~40 sec per sync at 56G | **Bottleneck** — but full distributed training isn't Athanor's purpose |

**Bottom line:** 56 Gbps with RDMA covers everything Athanor is designed to do. The only scenario where it's limiting — full distributed training of 70B+ models from scratch — is a data center workload, not a homelab one.

**The real ceiling is Node 2's PCIe slot, not the InfiniBand cards.** Node 2's available slot is PCIe 4.0 x4 = ~64 Gbps max. Upgrading from FDR (56G) to EDR (100G) cards only gains ~8 Gbps effective on Node 2's side. Not worth the extra cost.

### Tier 3: Faster Storage Link (Compute ↔ VAULT) — Future

If model loading or NFS performance from VAULT becomes a bottleneck, upgrade the VAULT connection:

**Option: Direct 25GbE or 40GbE link from each compute node to VAULT**

This would require NICs in VAULT (has PCIe slots available) and in the compute nodes (Node 1 has slots; Node 2's only remaining slot may already be used by InfiniBand from Tier 2).

Alternative: Use the Hyper M.2 adapters to add fast local NVMe storage to each compute node and keep frequently-used models local rather than loading from VAULT. 11 TB of loose NVMe drives exist. This may be a better use of money than faster networking — addressed in ADR-003 (Storage).

**Not recommended yet.** 10GbE is adequate for model loading (2 min for 70B FP16). Optimize storage placement first (ADR-003) before throwing bandwidth at the problem.

---

## Network Topology: Recommended

```
                    Internet
                       │
                   [UDM Pro] ─── 192.168.1.1
                       │
          ┌────────────┤
          │            │
  [USW Pro 24 PoE]    [USW Pro XG 10 PoE]
   1GbE management     10GbE data plane
   │  │  │  │  │       │     │     │
  APs IoT Lutron DEV  Node1 Node2 VAULT
                       │     │
                       └──┬──┘
                    Direct InfiniBand
                    56 Gbps (Tier 2)
```

**Three network planes:**

| Plane | Switch | Speed | Traffic |
|-------|--------|-------|---------|
| Management/IoT | USW Pro 24 PoE | 1GbE | SSH, APs, Lutron, Home Assistant devices, DEV |
| Data | USW Pro XG 10 PoE | 10GbE | NFS storage, service APIs, model loading, dashboard |
| GPU interconnect | Direct (no switch) | 56 Gbps IB | Multi-node inference, GPUDirect RDMA |

---

## VLANs

VLANs segment traffic logically even when sharing physical switches. UniFi makes VLAN management straightforward.

| VLAN | Purpose | Subnet | Members |
|------|---------|--------|---------|
| 1 (default) | Management | 192.168.1.0/24 | All nodes (management interfaces), UDM, switches |
| 10 | Data/Storage | 10.0.10.0/24 | Node 1, Node 2, VAULT (10GbE interfaces) |
| 20 | IoT | 10.0.20.0/24 | Lutron, smart devices, sensors |
| 30 | Guest | 10.0.30.0/24 | Guest WiFi |

**The InfiniBand link is outside the VLAN structure** — it's a point-to-point connection with its own subnet (e.g., 10.0.100.0/30), not routed through any switch.

**Keep it simple initially.** VLANs can be added incrementally. Start with management and data VLANs. Add IoT/guest VLANs when Home Assistant integration begins (ADR-010).

---

## DNS and Service Discovery

Services on different nodes need to find each other. Three options, in order of simplicity:

### Option 1: Static /etc/hosts + compose environment variables

Each node's `/etc/hosts` maps hostnames to IPs. Compose files use environment variables for service URLs.

```
# /etc/hosts on all nodes
10.0.10.11  node1 node1.athanor.local
10.0.10.12  node2 node2.athanor.local
10.0.10.13  vault vault.athanor.local
```

```yaml
# compose .env
INFERENCE_URL=http://node1.athanor.local:8000
COMFYUI_URL=http://node2.athanor.local:8188
PLEX_URL=http://vault.athanor.local:32400
```

**Pros:** Dead simple. No moving parts. Ansible manages /etc/hosts across nodes.
**Cons:** Manual updates when services change. No health checking.

### Option 2: Local DNS (CoreDNS or dnsmasq)

A lightweight DNS server (on any node or VAULT) resolves `*.athanor.local` addresses. Services register by convention (hostname + port).

**Pros:** Centralized name resolution. Can add wildcard records. Easy to extend.
**Cons:** One more service to run and maintain.

### Option 3: UDM Pro as DNS

The UDM Pro can serve as the local DNS resolver with static host entries configured in the UniFi UI.

**Pros:** Uses existing hardware. UniFi UI for management.
**Cons:** Limited flexibility. UDM DNS is basic.

**Recommendation:** Start with Option 1 (static hosts + env vars). It's the simplest, it's managed by Ansible, and for a system with 3-4 nodes and dozens of services, it's perfectly adequate. Move to Option 2 (CoreDNS) if/when the number of services makes static management painful.

---

## What New Parts Could Unlock

Shaun asked to keep thinking about what purchases could unlock new capability. Here's the network-relevant list:

### High-value purchases (under $150)

| Item | Cost | What It Unlocks |
|------|------|-----------------|
| 2x ConnectX-3 FDR + QSFP+ cable | ~$50-100 | 56 Gbps direct link between compute nodes. Multi-node tensor parallelism. 120 GB combined VRAM. |
| 1x X540-T2 (loose, already owned) in DEV | $0 | 10GbE for Shaun's workstation. Faster file transfers, SSH, dashboard responsiveness. |
| Cat6A cables (3-4x) | ~$20-40 | Connect all servers to the 10GbE switch that's sitting idle. |

### Medium-value purchases ($150-400)

| Item | Cost | What It Unlocks |
|------|------|-----------------|
| 2x ConnectX-4/5 EDR + QSFP28 cable | ~$130-250 | 100 Gbps direct link (bottlenecked to ~64G on Node 2). Marginal gain over FDR for more money. |
| Managed 25GbE switch (used) | ~$200-400 | Switched 25GbE fabric for all nodes. Only worth it if direct links aren't sufficient. |

### Things NOT worth buying

| Item | Why Not |
|------|---------|
| 100GbE switch | Overkill and expensive ($1000+). Direct links between compute nodes achieve the same result for $50-100. |
| More 10GbE NICs | Every server already has onboard 10GbE. The loose X540 cards are useful for DEV but the servers don't need them. |
| WiFi upgrade for DEV | 10GbE wired (X540 card) is better and cheaper than any WiFi upgrade. |

---

## Implementation Order

1. **Now (free/cheap):** Connect Node 1, Node 2, and VAULT to USW Pro XG 10 PoE via 10GbE. Buy Cat6A cables if needed.
2. **Soon ($50-100):** Buy 2x ConnectX-3 FDR + QSFP+ cable. Install direct InfiniBand link between Node 1 and Node 2.
3. **When needed:** Install X540-T2 in DEV for 10GbE workstation access.
4. **Future:** Evaluate faster VAULT link if model loading becomes a bottleneck (may be solved by local NVMe storage instead — see ADR-003).

---

## Open Questions

1. **Cat6A cable lengths needed** — depends on physical rack layout. Node 1 and Node 2 are in the same Silverstone RM52 case (upper and middle trays), so the InfiniBand cable can be very short (0.5-1m). Distance to VAULT and the XG switch needs measurement.

2. **Node 2's chipset PCIe slot physical clearance** — will a ConnectX-3 card physically fit below the RTX 4090? Need to verify during next rack session.

3. **InfiniBand setup on Ubuntu 24.04** — ConnectX-3 mlx4 drivers ship in-kernel since ~2013. Not a risk. Setup tasks: load modules, configure IB interfaces, run OpenSM subnet manager on one node, verify NCCL sees the IB device.

4. **VAULT NFS performance over 10GbE** — Unraid's mover process can cause NFS stale handles. Systemd automount on client side is the fix. Addressed in ADR-003.

5. **Whether Node 1's X550 ports support SR-IOV** — could allow VMs/containers to each get a virtual NIC with near-native performance. Low priority but worth noting.

---

## Sources

- [vLLM Parallelism and Scaling docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- [vLLM Distributed Inference (v0.8.0)](https://docs.vllm.ai/en/v0.8.0/serving/distributed_serving.html)
- [ROCm Blog — vLLM MoE Playbook (TP, DP, PP)](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html)
- [InfiniBand vs Ethernet for AI Clusters 2025](https://vitextech.com/infiniband-vs-ethernet-for-ai-clusters-2025/)
- [40-Gigabit InfiniBand homelab guide](https://blog.patshead.com/2021/02/40-gigabit-infiniband-an-inexpensive-performance-boost-for-your-home-network.html)
- [Mellanox ConnectX-4 Lx 25GbE review (ServeTheHome)](https://www.servethehome.com/mellanox-connectx-4-lx-mini-review-ubiquitous-25gbe/)
- [Mellanox ConnectX-5 100GbE review (StorageReview)](https://www.storagereview.com/review/mellanox-connectx-5-en-dual-port-100gbe-da-sfp-nic-review)
- [ConnectX-3 FDR deal (ServeTheHome)](https://www.servethehome.com/mellanox-56gbps-infiniband-40gbe-dual-port-connectx3-vpi-deal/)
- [ASUS ProArt X870E-CREATOR WIFI specs](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)
- [ASRock Rack ROMED8-2T specs](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)
- [Unraid NFS configuration guide](https://gist.github.com/pbarone/1f783a94a69aecd2eac49d9b77df0ceb)
- [vLLM multi-node discussion #10118](https://github.com/vllm-project/vllm/discussions/10118)
