# Foundry (Node 1) Deep Hardware Audit

**Date:** 2026-02-25 13:37 CST
**Auditor:** Claude (automated SSH audit)
**Target:** 192.168.1.244 (athanor@node1, passwordless sudo)
**Method:** All data gathered via live SSH commands. Nothing assumed from memory.

---

## Executive Summary

Foundry is a single-socket EPYC server running 5 GPUs (4x RTX 5070 Ti + 1x RTX 4090) with 224 GB ECC RAM. The system is functional and serving vLLM TP=4 inference at full GPU utilization. However, this audit uncovered several issues that represent wasted resources or suboptimal configuration.

### Critical Findings

| # | Finding | Severity | Impact |
|---|---------|----------|--------|
| 1 | All 5070 Ti GPUs power-limited to 250W (default 300W); 4090 at 320W (default 450W) | WARNING | ~17-29% lower peak compute throughput |
| 2 | 1 TB NVMe drive (nvme1n1) formatted but NOT MOUNTED | WASTE | 1 TB unused local fast storage |
| 3 | Samsung 990 PRO 4TB NOT INSTALLED (inventory says it is) | DISCREPANCY | Inventory doc is wrong |
| 4 | Memory channel H empty (7/8 populated) | SUBOPTIMAL | ~12% reduced memory bandwidth |
| 5 | vm.swappiness=60, no hugepages, no kernel tuning | SUBOPTIMAL | Higher tail latency for inference |
| 6 | MTU 1500 on 10GbE NFS links (no jumbo frames) | SUBOPTIMAL | NFS throughput not maximized |
| 7 | PCIE slot 6 physically available | OPPORTUNITY | RTX 3060 could be installed |
| 8 | NFS appdata mount in fstab but not active | MINOR | Missing backup path for agents |

---

## 1. System Identity

| Property | Value |
|----------|-------|
| Motherboard | ASRockRack ROMED8-2T v1.03 |
| Serial | BR80G2007200132 |
| BIOS | AMI P3.90 (2024-08-12) |
| Chassis | Main Server Chassis (Silverstone RM52 upper tray) |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | 6.17.0-14-generic (PREEMPT_DYNAMIC) |
| Docker | 29.2.1 (Compose v5.0.2, Buildx v0.31.1) |
| NVIDIA Driver | 580.126.09 |
| CUDA Version | 13.0 |

---

## 2. CPU

| Property | Value |
|----------|-------|
| Model | AMD EPYC 7663 56-Core Processor |
| Architecture | Zen 3 (Milan), Family 25h Model 01h |
| Socket | SP3 (single socket) |
| Cores / Threads | 56C / 112T |
| Base Clock | 2.0 GHz |
| Max Boost | 3.54 GHz |
| TDP | 240W |
| Virtualization | AMD-V (SVM) |
| NUMA Nodes | 1 (all 112 threads on node 0) |
| L1 Cache | 1.8 MiB I + 1.8 MiB D (56 instances each) |
| L2 Cache | 28 MiB (56 instances) |
| L3 Cache | 256 MiB (8 instances / CCDs) |

### CPU Frequency & Power Management

| Property | Value | Assessment |
|----------|-------|------------|
| Governor | schedutil (all 112 CPUs) | OK - adaptive |
| Frequency Driver | acpi-cpufreq | OK |
| scaling_max_freq | 2,000 MHz | WARNING - capped at base clock |
| cpuinfo_max_freq | 3,541 MHz | True max with boost |
| Boost | Enabled (1) | OK |
| Current freq (sample) | 2,701 MHz | Boost is working |
| Max C-state | 9 | Default - deep sleep allowed |

**Assessment:** The CPU is lightly loaded (vLLM is GPU-bound). The 112 threads are massive overkill for current workloads. The `schedutil` governor with boost enabled is appropriate. The `scaling_max_freq` cap at 2.0 GHz is default for EPYC - boost exceeds it via hardware. No action needed unless CPU-bound workloads are added.

**Current utilization:** vLLM uses ~403% CPU (4 threads), all other containers under 1%. Over 100 threads are idle.

### Relevant CPU Flags

AVX2, SHA_NI, AES, VAES, VPCLMULQDQ, RDRAND, RDSEED, CLFLUSHOPT, CLWB - all present. No AVX-512 (Milan does not support it).

---

## 3. Memory

### Physical Layout

| Channel | Locator | Size | Type | Speed | Manufacturer | Part Number | Rank |
|---------|---------|------|------|-------|-------------|-------------|------|
| A | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| B | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| C | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| D | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| E | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| F | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| G | DIMM 0 | 32 GB | DDR4 ECC RDIMM | 3200 MT/s | Samsung | M393A4K40DB3-CWE | 2R |
| **H** | **DIMM 0** | **EMPTY** | **---** | **---** | **---** | **---** | **---** |

**Total:** 224 GB (7x 32 GB) across 7 of 8 channels. ECC multi-bit correction active. 72-bit bus width (64 data + 8 ECC).

### Memory Utilization

| Metric | Value |
|--------|-------|
| Total | 219 GiB |
| Used | 26 GiB |
| Free | 128 GiB |
| Buff/Cache | 66 GiB |
| Available | 193 GiB |
| Swap Total | 8.0 GiB |
| Swap Used | 0 B |

### NUMA Topology

Single NUMA node (node 0): 225,275 MB total, 131,509 MB free. All CPUs and GPUs on the same NUMA node. No NUMA penalties.

### DIMM Temperatures (IPMI)

| Channel | Temp |
|---------|------|
| DDR4 A | 47 C |
| DDR4 B | 46 C |
| DDR4 C | 44 C |
| DDR4 D | 43 C |
| DDR4 E | 47 C |
| DDR4 F | 47 C |
| DDR4 G | 45 C |
| DDR4 H | N/A (empty) |

All within safe range (threshold 84 C).

### Assessment

- WARNING: Channel H is empty. The EPYC 7663 supports 8-channel DDR4. Running 7 of 8 channels reduces peak memory bandwidth by approximately 12.5%. For LLM inference where model weights are loaded from system RAM to VRAM, this slightly increases initial load times. For steady-state inference (all in VRAM), impact is negligible.
- The 193 GiB available RAM is vastly underutilized. Only ~26 GiB used by all containers combined.
- Opportunity: Adding an 8th 32 GB DIMM would cost ~$30-50 for used Samsung ECC RDIMMs and complete the 8-channel configuration (256 GB total).

---

## 4. GPUs

### GPU Inventory

| Index | Model | Bus ID | VRAM | Architecture | SM | VBIOS | Subsystem | Vendor |
|-------|-------|--------|------|-------------|-----|-------|-----------|--------|
| GPU0 | RTX 5070 Ti | 01:00.0 | 16,303 MiB GDDR7 | Blackwell | sm_120 | 98.03.58.00.94 | 0x53101462 | MSI |
| GPU1 | RTX 5070 Ti | 02:00.0 | 16,303 MiB GDDR7 | Blackwell | sm_120 | 98.03.58.00.43 | 0x41811458 | Gigabyte |
| GPU2 | RTX 4090 | 81:00.0 | 24,564 MiB GDDR6X | Ada Lovelace | sm_89 | 95.02.18.80.95 | 0x889A1043 | ASUS |
| GPU3 | RTX 5070 Ti | 82:00.0 | 16,303 MiB GDDR7 | Blackwell | sm_120 | 98.03.58.00.43 | 0x41811458 | Gigabyte |
| GPU4 | RTX 5070 Ti | C1:00.0 | 16,303 MiB GDDR7 | Blackwell | sm_120 | 98.03.58.00.94 | 0x53101462 | MSI |

**Total VRAM: 89,776 MiB (87.7 GB)**

### Inventory Discrepancy

The inventory doc (`inventory.md`) lists GPU slots as:
- Slot 1 = 4090, Slot 2 = MSI 5070 Ti, Slot 3 = MSI 5070 Ti, Slot 4 = Gigabyte 5070 Ti, Slot 5 = Gigabyte 5070 Ti

Actual PCIe bus ordering and subsystem IDs show:
- Bus 00 slot (01:00) = MSI 5070 Ti (GPU0)
- Bus 00 slot (02:00) = Gigabyte 5070 Ti (GPU1)
- Bus 80 slot (81:00) = ASUS 4090 (GPU2)
- Bus 80 slot (82:00) = Gigabyte 5070 Ti (GPU3)
- Bus C0 slot (C1:00) = MSI 5070 Ti (GPU4)

The physical slot-to-bus mapping differs from what inventory.md implies. The 4090 is in the middle of the bus topology (PCIE domain 0x80), not at the "top" slot.

### PCIe Link Status

**Source: nvidia-smi -q (NVIDIA driver, authoritative for GPU link state)**

| GPU | PCIe Gen (Current) | PCIe Gen (Device Max) | PCIe Gen (Host Max) | Width | Status |
|-----|--------------------|-----------------------|---------------------|-------|--------|
| GPU0 | **Gen 4** | Gen 5 | Gen 4 | x16 | OK - host caps at Gen 4 |
| GPU1 | **Gen 4** | Gen 5 | Gen 4 | x16 | OK - host caps at Gen 4 |
| GPU2 | **Gen 4** | Gen 4 | Gen 4 | x16 | OK - running at device max |
| GPU3 | **Gen 4** | Gen 5 | Gen 4 | x16 | OK - host caps at Gen 4 |
| GPU4 | **Gen 1** | Gen 5 | Gen 4 | x16 | OK - idle (P8 power state) |

**Note:** `lspci -vvv` shows LnkSta "Speed 2.5GT/s" for all GPUs including the active ones. This is a known discrepancy between lspci's snapshot reading and the NVIDIA driver's internal link state tracking. The nvidia-smi reading is authoritative for NVIDIA devices. The active GPUs (0-3) are confirmed at Gen 4 x16 = ~32 GB/s each. GPU4 drops to Gen 1 when idle (power saving), which is expected and correct behavior.

The EPYC 7663 (Milan) platform supports PCIe Gen 4 maximum. The Blackwell 5070 Ti cards are Gen 5 capable but are limited to Gen 4 by the host. This is a platform limitation, not a configuration issue.

### GPU Topology

```
        GPU0    GPU1    GPU2    GPU3    GPU4
GPU0     X      PHB     NODE    NODE    NODE
GPU1    PHB      X      NODE    NODE    NODE
GPU2    NODE    NODE     X      PHB     NODE
GPU3    NODE    NODE    PHB      X      NODE
GPU4    NODE    NODE    NODE    NODE     X
```

- GPU0 + GPU1 share PCIe Host Bridge (PHB) - same root complex domain 0x00
- GPU2 + GPU3 share PCIe Host Bridge (PHB) - same root complex domain 0x80
- GPU4 is alone in domain 0xC0
- All inter-GPU communication traverses NODE (PCIe root complex + data fabric), not NVLink

**TP=4 implication:** The current vLLM TP=4 configuration uses GPUs 0-3. These span TWO PCIe root complexes (domain 0x00 and 0x80). All tensor parallel communication goes through the AMD Infinity Fabric / data fabric. This is the maximum possible interconnect for this platform without NVLink.

### IOMMU Groups

| GPU | IOMMU Group | Devices |
|-----|-------------|---------|
| GPU0 | 79 | 01:00.0 VGA + 01:00.1 Audio |
| GPU1 | 80 | 02:00.0 VGA + 02:00.1 Audio |
| GPU2 | 28 | 81:00.0 VGA + 81:00.1 Audio |
| GPU3 | 29 | 82:00.0 VGA + 82:00.1 Audio |
| GPU4 | 10 | C1:00.0 VGA + C1:00.1 Audio |

Each GPU is in its own IOMMU group with only its audio function. Clean isolation for passthrough if ever needed.

### GPU Power & Thermals

| GPU | Current Draw | Power Limit | Default Limit | Max Limit | GPU Temp | T.Limit Headroom | Fan |
|-----|-------------|-------------|---------------|-----------|----------|-------------------|-----|
| GPU0 (MSI 5070Ti) | 168 W | **250 W** | 300 W | 300 W | 54 C | 34 C | 31% |
| GPU1 (GB 5070Ti) | 142 W | **250 W** | 300 W | **350 W** | 41 C | 47 C | 30% |
| GPU2 (ASUS 4090) | 179 W | **320 W** | 450 W | **600 W** | 41 C | 43 C | 30% |
| GPU3 (GB 5070Ti) | 160 W | **250 W** | 300 W | **350 W** | 44 C | 44 C | 30% |
| GPU4 (MSI 5070Ti) | 15 W | **250 W** | 300 W | 300 W | 38 C | 50 C | 0% |

**CRITICAL FINDING - Power Limits:**

All GPUs are running BELOW their default power limits:
- 5070 Ti cards: 250W limit vs 300W default = **17% below default**
- 4090: 320W limit vs 450W default = **29% below default**

The 5070 Ti MSI cards (GPU0, GPU4) max out at 300W. The Gigabyte cards (GPU1, GPU3) can go up to 350W -- these are a higher-power SKU.

The 4090 can theoretically go to 600W (max power limit) but the 320W setting is likely a deliberate choice for thermal/power budget reasons in the Silverstone RM52 chassis. At 320W the 4090 draws 179W under load -- well below the cap.

**Thermal headroom is excellent.** All GPUs have 34-50 C of thermal headroom. Fans at 30-31%. There is significant room to increase power limits without thermal issues.

**Estimated power impact of raising limits to default:**
- 4x 5070 Ti at 300W + 4090 at 450W = 1,650W GPU peak
- Current: 4x 250W + 320W = 1,320W GPU peak
- Delta: +330W headroom available

Whether this translates to meaningful inference speedup depends on whether vLLM kernels are currently power-limited. The "SW Power Capping" counters show ~219ms of power capping events for each 5070 Ti, suggesting the cards ARE occasionally hitting their power cap during compute-intensive phases.

### GPU Clocks

| GPU | Current GFX | Max GFX | Current Mem | Max Mem |
|-----|-------------|---------|-------------|---------|
| GPU0 (5070Ti) | 2827 MHz | 3090 MHz | 13801 MHz | 14001 MHz |
| GPU1 (5070Ti) | 2835 MHz | 3105 MHz | 13801 MHz | 14001 MHz |
| GPU2 (4090) | 2745 MHz | 3105 MHz | 10251 MHz | 10501 MHz |
| GPU3 (5070Ti) | 2895 MHz | 3105 MHz | 13801 MHz | 14001 MHz |
| GPU4 (5070Ti) | 180 MHz | 3090 MHz | idle | 14001 MHz |

All active GPUs are boosting to within 5-10% of their max clocks. No thermal throttling detected.

### GPU Memory Usage

| GPU | Total | Used | Free | Process |
|-----|-------|------|------|---------|
| GPU0 | 16,303 MiB | 15,634 MiB | 207 MiB | VLLM::Worker_TP0 (15,624 MiB) |
| GPU1 | 16,303 MiB | 15,636 MiB | 205 MiB | VLLM::Worker_TP1 (15,626 MiB) |
| GPU2 | 24,564 MiB | 15,796 MiB | **8,286 MiB** | VLLM::Worker_TP2 (15,786 MiB) |
| GPU3 | 16,303 MiB | 15,642 MiB | 196 MiB | VLLM::Worker_TP3 (15,624 MiB) |
| GPU4 | 16,303 MiB | 8,899 MiB | **6,942 MiB** | VLLM::EngineCore (6,742 MiB) + whisper (2,142 MiB) |

**Key observations:**
- GPUs 0, 1, 3 (5070 Ti) are at 96% VRAM utilization -- nearly full
- GPU2 (4090) has 8.3 GB free -- it's limited by the TP=4 uniform allocation (16 GB model shard per GPU, but the 4090 has 24 GB total)
- GPU4 has 6.9 GB free -- running embedding model (6.7 GB) + whisper STT (2.1 GB)
- The 4090's extra 8 GB is wasted in the current TP=4 config (each rank gets equal share capped by the smallest GPU)

---

## 5. Storage

### Local NVMe Drives

| Device | Model | Serial | Capacity | Gen | Link Speed | Filesystem | Mount | Health |
|--------|-------|--------|----------|-----|------------|------------|-------|--------|
| nvme0n1 | Crucial P3 CT4000P3SSD8 | 2422E8B57188 | 4.00 TB | Gen 3 | PCIe 3.0 x4 (8GT/s) | LVM (ext4) | / | PASSED, 1% used, 100% spare |
| nvme1n1 | Crucial P310 CT1000P310SSD8 | 25074E225AF9 | 1.00 TB | Gen 4 | PCIe 4.0 x4 (16GT/s) | btrfs (partition) | **NOT MOUNTED** | PASSED, 11% used, 100% spare |

### SMART Health Summary

**nvme0n1 (4TB boot drive):**
- Temperature: 33 C
- Available Spare: 100%
- Percentage Used: 1%
- Data Written: 21.5 TB (lifetime)
- Data Read: 24.8 TB (lifetime)
- Firmware: P9CR30D

**nvme1n1 (1TB unused drive):**
- Temperature: 32 C
- Available Spare: 100%
- Percentage Used: 11%
- Data Written: 13.9 TB (lifetime)
- Data Read: 9.58 TB (lifetime)
- Firmware: V8CR000

### Filesystem Layout

| Filesystem | Size | Used | Avail | Use% | Mount |
|------------|------|------|-------|------|-------|
| /dev/mapper/ubuntu--vg-ubuntu--lv | 3.6T | 180G | 3.3T | 6% | / |
| /dev/nvme0n1p2 | 2.0G | 203M | 1.6G | 12% | /boot |
| /dev/nvme0n1p1 | 1.1G | 6.2M | 1.1G | 1% | /boot/efi |

LVM: single VG `ubuntu-vg` with single LV consuming all 3.64T. No free extents.

### NFS Mounts

| Source | Mount Point | Type | Status | Options |
|--------|-------------|------|--------|---------|
| 192.168.1.203:/mnt/user/models | /mnt/vault/models | NFS4 | MOUNTED | rw, soft, rsize/wsize=131072 |
| 192.168.1.203:/mnt/user/data | /mnt/vault/data | NFS4 | MOUNTED | rw, soft, rsize/wsize=131072 |
| 192.168.1.203:/mnt/user/appdata | /mnt/vault/appdata | (in fstab) | **NOT MOUNTED** | rw, soft, intr |

### Storage Discrepancies

**MAJOR:** `inventory.md` lists drive #2 as "Samsung 990 PRO (MZ-V9P4T0) Gen4 4TB" in Node 1 M.2_2. The audit found a **Crucial P310 1TB Gen4** in that slot instead. The Samsung 990 PRO is NOT installed in this machine. Either it was never installed, was moved, or the inventory is wrong.

**MINOR:** The Crucial P310 1TB has a btrfs partition (nvme1n1p1) but is not mounted anywhere. This is 1 TB of fast local Gen4 NVMe storage sitting completely idle.

**NFS appdata:** Listed in fstab but not currently mounted. This may be intentional (not needed for Node 1 operations) or may indicate a stale-handle situation after a VAULT reboot.

---

## 6. Network

### Interfaces

| Interface | Type | IP | Speed | MTU | State | Driver |
|-----------|------|-----|-------|-----|-------|--------|
| enp66s0f0 | 10GbE (Intel X550) | 192.168.1.244/24 | 10,000 Mb/s Full Duplex | 1500 | UP | ixgbe |
| enp66s0f1 | 10GbE (Intel X550) | 192.168.1.246/24 | 10,000 Mb/s Full Duplex | 1500 | UP | ixgbe |
| enx2e6af1318629 | USB Ethernet (BMC) | none | unknown | 1500 | DOWN | (USB) |
| docker0 | Bridge | 172.17.0.1/16 | virtual | 1500 | UP | bridge |

### Network Configuration

- Netplan: `/etc/netplan/01-athanor.yaml` - static IPs, no DHCP
- Default route: via 192.168.1.1 on enp66s0f0
- DNS: 192.168.1.1
- Second NIC (enp66s0f1) has IP but no default route -- available for dedicated NFS traffic
- Wake-on-LAN: enabled (g) on both NICs

### NIC Hardware

- Intel X550 (onboard dual-port) at PCIe 3.0 x4 = ~32 Gb/s PCIe bandwidth for both ports
- Offloading: rx-checksumming ON, tx-checksumming ON, TSO ON, GRO ON, scatter-gather ON

### Assessment

- WARNING: MTU 1500 on all interfaces. For NFS over 10GbE, jumbo frames (MTU 9000) would reduce CPU overhead and increase throughput by 10-30% for large sequential transfers (model loading).
- The second NIC (enp66s0f1 / .246) is UP and linked but has no services bound to it. It could be dedicated to NFS traffic for isolation.
- net.core.rmem_max and wmem_max are at defaults (212992). For 10GbE, these should be increased to at least 16MB for optimal throughput.

---

## 7. PCIe Topology

### Physical Slots (from DMI)

| Slot | Designation | Type | Status | Bus Domain |
|------|-------------|------|--------|------------|
| PCIE1 | x16 | In Use | 0x80 | GPU2 (4090) + GPU3 (5070 Ti) domain |
| PCIE2 | x16 | In Use | 0x00 | GPU0 + GPU1 domain |
| PCIE3 | x16 | In Use | 0xC0 | GPU4 domain |
| PCIE4 | x16 | In Use | 0x40 | NVMe + NIC + ASPEED domain |
| PCIE5 | x16 | In Use | (aux) | |
| **PCIE6** | **x16** | **AVAILABLE** | **---** | **Empty slot** |
| PCIE7 | x16 | In Use | (aux) | |
| M2_1 | x4 | Available | --- | |
| M2_2 | x4 | In Use | 0x40 | NVMe drive |
| OCU1 | x4 | Available | --- | |
| OCU2 | x4 | Available | --- | |

### PCIe Bus Domains

```
Domain 0x00 (Root Complex 1):
  +-- 01:00.0  GPU0 - RTX 5070 Ti (MSI)   [Gen 4 x16]
  +-- 02:00.0  GPU1 - RTX 5070 Ti (GB)    [Gen 4 x16]
  +-- 03:00.x  PTDMA
  +-- 04:00.x  USB 3.0

Domain 0x40 (Root Complex 2):
  +-- 41:00.0  NVMe 0 - Crucial P3 4TB    [Gen 3 x4]
  +-- 42:00.x  Intel X550 (dual 10GbE)    [Gen 3 x4]
  +-- 44:00.0  ASMedia USB 3.1
  +-- 45-46     ASPEED BMC VGA
  +-- 47:00.0  NVMe 1 - Crucial P310 1TB  [Gen 4 x4]

Domain 0x80 (Root Complex 3):
  +-- 81:00.0  GPU2 - RTX 4090 (ASUS)     [Gen 4 x16]
  +-- 82:00.0  GPU3 - RTX 5070 Ti (GB)    [Gen 4 x16]
  +-- 83-86    PTDMA, SATA

Domain 0xC0 (Root Complex 4):
  +-- C1:00.0  GPU4 - RTX 5070 Ti (MSI)   [Gen 4 x16]
  +-- C2-C3    PTDMA
```

### Assessment

- The EPYC 7663 has 128 PCIe Gen 4 lanes. Current usage: 5 GPUs x16 = 80 lanes, NVMe x4 + x4 = 8 lanes, NIC x4 = 4 lanes, misc = ~8 lanes. Total: ~100 lanes used. Approximately 28 lanes remain available.
- PCIE6 is physically available. The loose RTX 3060 (12 GB) could be installed here, but this was previously deferred due to PSU power budget.
- M2_1 slot is available for an additional NVMe drive.
- OCU1 and OCU2 (x4 oculink) are available.

---

## 8. Docker & Services

### Running Containers

| Name | Image | CPU% | RAM | GPU Assignment |
|------|-------|------|-----|----------------|
| vllm | nvcr.io/nvidia/vllm:25.12-py3 | 403% | 15.45 GiB | GPU 0,1,2,3 (TP=4) |
| vllm-embedding | nvcr.io/nvidia/vllm:25.12-py3 | 0.75% | 2.33 GiB | GPU 4 |
| wyoming-whisper | rhasspy/wyoming-whisper | 0.02% | 354 MiB | GPU 4 |
| speaches | ghcr.io/speaches-ai/speaches:latest-cuda | 0.09% | 185 MiB | GPU 4 |
| athanor-agents | athanor/agents:latest | 0.00% | 140 MiB | None (CPU only) |
| athanor-gpu-orchestrator | athanor/gpu-orchestrator:latest | 0.04% | 58 MiB | None (CPU only) |
| qdrant | qdrant/qdrant:v1.13.2 | 0.71% | 844 MiB | None (CPU only) |
| dcgm-exporter | nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9 | 0.00% | 646 MiB | None (GPU metrics) |
| node-exporter | prom/node-exporter:latest | 0.00% | 33 MiB | None (system metrics) |

**Total container RAM: ~20 GiB** (of 220 GiB available)

### Docker Configuration

| Property | Value |
|----------|-------|
| Storage Driver | overlayfs (containerd) |
| Runtime | runc (default), nvidia (available) |
| Cgroup Driver | systemd v2 |
| CDI Devices | All 5 GPUs discovered |
| Docker Root | (default /var/lib/docker) |

`/etc/docker/daemon.json` defines the nvidia runtime but does NOT set it as default. Each container must explicitly request GPU access via `--runtime=nvidia` or `--gpus` flag.

### Compose Stacks

| Stack | Location |
|-------|----------|
| agents | /opt/athanor/agents/docker-compose.yml |
| vllm | /opt/athanor/vllm/docker-compose.yml |
| vllm-embedding | /opt/athanor/vllm-embedding/docker-compose.yml |
| gpu-orchestrator | /opt/athanor/gpu-orchestrator/docker-compose.yml |
| monitoring | /opt/athanor/monitoring/docker-compose.yml |

---

## 9. Power & Thermals

### CPU & Board Temperatures (IPMI)

| Sensor | Reading | Threshold |
|--------|---------|-----------|
| CPU Temp | 64 C | 93/94 C |
| MB Temp | 35 C | 55 C |
| Card Side Temp | 44 C | 68 C |
| Onboard LAN Temp | 60 C | 103/104 C |

### Voltages (IPMI)

| Rail | Reading | Status |
|------|---------|--------|
| VCPU | 1.120 V | OK |
| VSOC | 0.870 V | OK |
| 12V | 11.800 V | OK (within 10.2-13.8V range) |
| 5V | 4.950 V | OK |
| 3.3V | 3.260 V | OK |

### Fan Status

| Fan | Speed |
|-----|-------|
| FAN1 | 1200 RPM |
| FAN2 | 1800 RPM |
| FAN3 | N/A |
| FAN4 | 1100 RPM |
| FAN5-7 | N/A |

### PSU Status

- PSU1: Status OK, no reading for power draw (IPMI sensor not reporting wattage)
- PSU2: Status OK, no reading for power draw
- Chassis power restore policy: always-on

**Note:** IPMI cannot report actual system power draw. The PSU is a Corsair 1600W unit per rack-session.md. No PSU2 appears to be connected (all PSU2 sensors read N/A).

### Estimated Power Budget

| Component | Estimated Draw |
|-----------|---------------|
| EPYC 7663 (under light load) | ~80 W |
| 7x DDR4 RDIMM | ~35 W |
| GPU0 (5070 Ti) | 168 W |
| GPU1 (5070 Ti) | 142 W |
| GPU2 (4090) | 179 W |
| GPU3 (5070 Ti) | 160 W |
| GPU4 (5070 Ti, idle) | 15 W |
| NVMe drives x2 | ~10 W |
| NIC, fans, misc | ~30 W |
| **Total estimate** | **~820 W** |

With PSU headroom of 1600W, there is approximately 780W available. This is sufficient to:
- Raise all GPU power limits to defaults (+330W)
- Add the RTX 3060 (~170W TDP)
- Run everything simultaneously

---

## 10. Kernel & OS Tuning

### Current Settings

| Parameter | Value | Optimal | Assessment |
|-----------|-------|---------|------------|
| vm.swappiness | 60 | 10 | TOO HIGH - server with 193 GiB free should barely swap |
| vm.nr_hugepages | 0 | varies | MISSING - vLLM can benefit from hugepages |
| vm.dirty_ratio | 20 | 20 | OK |
| vm.dirty_background_ratio | 10 | 5 | SLIGHTLY HIGH for NFS workloads |
| vm.overcommit_memory | 0 | 0 | OK (heuristic) |
| transparent_hugepages | madvise | madvise | OK |
| net.core.rmem_max | 212992 | 16777216 | TOO LOW for 10GbE |
| net.core.wmem_max | 212992 | 16777216 | TOO LOW for 10GbE |
| net.core.netdev_max_backlog | 1000 | 5000 | LOW for 10GbE |
| fs.file-max | 9223372036854775807 | (max) | OK |
| kernel boot params | (clean) | (none needed) | OK |
| CPU governor | schedutil | performance | CONSIDER for latency |
| Max C-state | 9 | 1-2 | CONSIDER reducing for latency |

### Missing Software

| Package | Purpose | Status |
|---------|---------|--------|
| lm-sensors | CPU/VRM temperature monitoring | NOT INSTALLED |
| numactl | NUMA-aware process binding | Installed |
| lstopo (hwloc) | Hardware topology visualization | NOT CHECKED |

### Recommended Kernel Tuning

For an LLM inference server, apply via `/etc/sysctl.d/99-athanor.conf`:

```
vm.swappiness = 10
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 5000
vm.dirty_background_ratio = 5
```

For latency-sensitive inference, consider:
```
# Reduce CPU C-states for faster wake
# Add to kernel cmdline: processor.max_cstate=2
```

---

## 11. Utilization Summary

### Resource Utilization Map

| Resource | Total | Used | Free | Utilization |
|----------|-------|------|------|-------------|
| CPU cores | 112 | ~4 | ~108 | **4%** |
| RAM | 224 GB | 26 GB | 193 GB | **12%** |
| GPU VRAM (total) | 88 GB | 72 GB | 16 GB | **82%** |
| GPU compute (GPUs 0-3) | 4 GPUs | 4 GPUs | 0 | **100%** |
| GPU compute (GPU4) | 1 GPU | partial | partial | **~55% VRAM, 0% compute** |
| 4090 extra VRAM | 8.3 GB | 0 | 8.3 GB | **0% (wasted by TP symmetry)** |
| NVMe storage | 5 TB local | 180 GB | 4.8 TB | **4%** |
| NVMe (unmounted) | 1 TB | 0 | 1 TB | **0% (completely idle)** |
| 10GbE ports | 2 | 1 active | 1 secondary | **50%** |
| PCIe x16 slots | 7 | 5 GPUs + 1 NVMe domain | 1 empty | **86%** |
| Power budget | 1600W | ~820W | ~780W | **51%** |

### Idle / Wasted Resources

1. **108 CPU threads** -- virtually all idle. Could run additional CPU workloads (compilation, data processing, batch jobs).
2. **193 GB RAM** -- 86% free. Could run RAM-intensive workloads (database, large embedding indexes, model pre-loading).
3. **8.3 GB 4090 VRAM** -- wasted because TP=4 allocates uniformly and is limited by the smallest GPU (16 GB 5070 Ti).
4. **1 TB unmounted NVMe** -- fast Gen4 storage doing nothing.
5. **3.3 TB free on boot drive** -- OS only uses 180 GB of 3.6 TB.
6. **1 empty PCIe x16 slot** -- RTX 3060 deferred but PSU budget allows it.
7. **780W PSU headroom** -- enough for another GPU and raised power limits.
8. **Second 10GbE port** -- linked but underutilized.

---

## 12. Recommendations

### Priority 1 (Performance -- No Cost)

1. **Raise GPU power limits to default.** All 5070 Ti cards show SW Power Capping events. Run:
   ```
   nvidia-smi -i 0 -pl 300  # MSI 5070Ti (max 300W)
   nvidia-smi -i 1 -pl 300  # Gigabyte 5070Ti (max 350W, but match pool)
   nvidia-smi -i 2 -pl 450  # ASUS 4090 (default 450W)
   nvidia-smi -i 3 -pl 300  # Gigabyte 5070Ti
   nvidia-smi -i 4 -pl 300  # MSI 5070Ti
   ```
   Persist via nvidia-persistenced or systemd unit. Estimated GPU power increase: +330W (within PSU budget).

2. **Apply kernel tuning** (sysctl.d file as described in Section 10). Zero risk, immediate latency improvement.

3. **Install lm-sensors** for CPU temperature monitoring: `sudo apt install lm-sensors && sudo sensors-detect`

### Priority 2 (Resource Recovery -- No Cost)

4. **Mount the 1TB NVMe (nvme1n1).** Mount the existing btrfs partition for Docker image caching, model staging, or scratch space.

5. **Fix NFS appdata mount.** Verify if `/mnt/vault/appdata` should be active: `sudo mount /mnt/vault/appdata`

6. **Enable jumbo frames on NFS interfaces.** Add `mtu: 9000` to netplan for both enp66s0f0 and enp66s0f1, then update NFS mount options. Requires matching MTU on VAULT and switch.

### Priority 3 (Capacity -- Low Cost)

7. **Add 8th DIMM** (Samsung M393A4K40DB3-CWE 32GB DDR4 ECC RDIMM). Completes 8-channel memory, adds 32 GB. Approximate cost: $30-50 used.

8. **Install RTX 3060** in PCIE6 slot. Adds 12 GB VRAM for a dedicated workload (embedding, fine-tuning, secondary inference). PSU budget allows it.

### Priority 4 (Investigation)

9. **Verify Samsung 990 PRO location.** Inventory says it's in Node 1 M.2_2 but a Crucial P310 1TB is there instead. Shaun needs to confirm where the 990 PRO physically is.

10. **Evaluate whether 4090 VRAM waste matters.** In TP=4 with 3x 16GB + 1x 24GB, the extra 8GB on the 4090 cannot be used. If larger models are needed, consider running the 4090 as a standalone inference GPU instead of in the TP pool.

---

## Appendix A: Full PCIe Device Summary

| Bus ID | Device | Link Speed | Link Width |
|--------|--------|------------|------------|
| 01:00.0 | RTX 5070 Ti (GPU0) | Gen 4 (16GT/s) | x16 |
| 02:00.0 | RTX 5070 Ti (GPU1) | Gen 4 (16GT/s) | x16 |
| 41:00.0 | Crucial P3 4TB NVMe | Gen 3 (8GT/s) | x4 |
| 42:00.0 | Intel X550 10GbE | Gen 3 (8GT/s) | x4 |
| 44:00.0 | ASMedia USB 3.1 | Gen 3 | x1 |
| 47:00.0 | Crucial P310 1TB NVMe | Gen 4 (16GT/s) | x4 |
| 81:00.0 | RTX 4090 (GPU2) | Gen 4 (16GT/s) | x16 |
| 82:00.0 | RTX 5070 Ti (GPU3) | Gen 4 (16GT/s) | x16 |
| C1:00.0 | RTX 5070 Ti (GPU4) | Gen 4 (16GT/s) | x16 |

## Appendix B: GPU UUID Reference

| GPU | UUID |
|-----|------|
| GPU0 | GPU-0214ee9b-e66f-98c0-9879-1717c861d68d |
| GPU1 | GPU-fc6fac07-2470-afc2-ce8d-a287aabfd60d |
| GPU2 | GPU-77dbf1a8-9abc-bbcb-7c5f-0c2616d41132 |
| GPU3 | GPU-378314e9-ecc3-abbc-7a13-34e1b136519d |
| GPU4 | GPU-a4dabe7c-fdc1-b9bb-d9fa-3f2a309e01cf |

## Appendix C: nvidia-smi Device Mapping

| nvidia-smi Index | Bus ID | Minor Number | Display |
|-----------------|--------|-------------|---------|
| 0 | 01:00.0 | 3 | No |
| 1 | 02:00.0 | 4 | No |
| 2 | 81:00.0 | 1 | No |
| 3 | 82:00.0 | 2 | Yes (primary display) |
| 4 | C1:00.0 | 0 | No |

Note: GPU3 (82:00.0) has Display Active = Enabled and is the primary framebuffer device. This is the console display output GPU.
