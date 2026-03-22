# Workshop (Node 2) Deep Hardware Audit

**Date:** 2026-02-25 13:37 CST
**Auditor:** Claude (automated SSH audit)
**Target:** Workshop / Node 2 / 192.168.1.225
**Uptime:** 2 days, 4:25
**Method:** All data collected via `ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225` with passwordless sudo

---

## Executive Summary

Workshop is a Threadripper 7960X workstation running 7 Docker containers (vLLM, ComfyUI, Dashboard, EoBQ, Open WebUI, DCGM-exporter, Node-exporter) with 2 Blackwell GPUs (RTX 5090 + RTX 5060 Ti). The machine is dramatically underutilized: 93% of RAM idle, CPU load at 0.5%, and 3 TB of Gen5 NVMe storage completely unused. DDR5 is running 16.6% below rated speed due to missing EXPO BIOS setting. One inventory discrepancy found: the RTX 5060 Ti is a PCIe 5.0 x8 card, not x16 as documented.

---

## 1. CPU

### Verified Configuration

| Property | Value |
|----------|-------|
| Model | AMD Ryzen Threadripper 7960X 24-Cores |
| Architecture | Zen 4 (sTR5 socket) |
| Cores / Threads | 24C / 48T |
| Base / Max Boost | 409.8 MHz min / 5669.6 MHz max |
| L1 Cache | 1536 KiB (768 KiB D + 768 KiB I) |
| L2 Cache | 24 MiB (24 instances, 1 MiB per core) |
| L3 Cache | 128 MiB (4 instances, 32 MiB per CCD) |
| NUMA Nodes | 1 (all 48 threads on node 0) |
| Frequency Governor | powersave (all 48 threads) |
| Current Load | 0.25, 0.14, 0.05 |
| Current Frequencies | 2185-4664 MHz (mostly idle around 2186 MHz) |
| CPU Temp Range | 38-56C |
| Key ISA Extensions | AVX-512 (F/BW/VL/VNNI/BF16), AES-NI, SHA-NI, SMT |
| Virtualization | AMD-V |

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Hardware match | verified | Matches inventory: TR 7960X 24C/48T |
| Utilization | wasteful | Load 0.25 on 48 threads = 0.5% utilization |
| Governor | suboptimal | `powersave` on all 48 threads adds latency to inference requests |
| NUMA | optimal | Single node, no cross-node penalty |
| Thermals | optimal | 38-56C well within limits |

### Recommendations

1. **Switch governor to `performance` or `schedutil`** for lower inference latency. Command: `echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`. Make persistent via systemd or kernel param `amd_pstate=active`.
2. **47.5 threads are idle.** This CPU could run CPU-heavy workloads (compilation, data processing, transcoding) without impacting GPU inference.

---

## 2. Memory (DDR5)

### Verified Configuration

| Property | Value |
|----------|-------|
| Total Installed | 128 GB (4x 32 GB) |
| Available to OS | 125.3 GiB |
| Currently Used | 8.5 GiB (6.8%) |
| Available | 116 GiB (93%) |
| Swap | 8 GB (24 KiB used) |

### DIMM Details

| Slot | Locator | Size | Type | Part Number | Speed (Rated) | Speed (Running) | Manufacturer |
|------|---------|------|------|-------------|---------------|-----------------|-------------|
| DIMM 0 | P0 CHANNEL A | 32 GB | DDR5 ECC RDIMM | KF556R28-32 | 5600 MT/s | 4800 MT/s | Kingston |
| DIMM 0 | P0 CHANNEL C | 32 GB | DDR5 ECC RDIMM | KF556R28-32 | 5600 MT/s | 4800 MT/s | Kingston |
| DIMM 0 | P0 CHANNEL E | 32 GB | DDR5 ECC RDIMM | KF556R28-32 | 5600 MT/s | 4800 MT/s | Kingston |
| DIMM 0 | P0 CHANNEL G | 32 GB | DDR5 ECC RDIMM | KF556R28-32 | 5600 MT/s | 4800 MT/s | Kingston |

All DIMMs are dual-rank (Rank: 2), 80-bit total width (64-bit data + 16-bit ECC).

### Channel Population

The TRX50 platform has 4 DDR5 channels (labeled A through H for sub-channels). With 4 DIMMs across channels A, C, E, G, all 4 channels are populated. This is the correct quad-channel configuration.

### Bandwidth Analysis

| Metric | At 4800 MT/s (Current) | At 5600 MT/s (Rated) | Delta |
|--------|----------------------|---------------------|-------|
| Per-channel bandwidth | 38.4 GB/s | 44.8 GB/s | +6.4 GB/s |
| Total quad-channel bandwidth | 153.6 GB/s | 179.2 GB/s | +25.6 GB/s |
| Percentage of rated | 85.7% | 100% | +16.6% |

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Capacity match | verified | 128 GB matches inventory |
| DIMM type | verified | DDR5 ECC RDIMM as required by TRX50 |
| Channel config | optimal | Quad-channel fully populated |
| Running speed | MISMATCH | 4800 MT/s JEDEC default instead of 5600 MT/s rated |
| Utilization | wasteful | 93% idle (116 GiB available) |
| ECC | verified | Multi-bit ECC active (80-bit width) |

### Critical Finding: EXPO Not Enabled

The Kingston FURY KF556R28-32 modules are rated for 5600 MT/s but running at 4800 MT/s (JEDEC default). This confirms the blocker documented in `CLAUDE.md`: **EXPO needs to be enabled in BIOS via JetKVM at .165.** This costs 25.6 GB/s of memory bandwidth -- relevant for any memory-bound workloads, CPU-side model processing, and large data shuffling.

---

## 3. GPUs

### GPU 0: NVIDIA GeForce RTX 5090

| Property | Value |
|----------|-------|
| Architecture | Blackwell (sm_120) |
| VRAM | 32,607 MiB GDDR7 |
| VRAM Used | 31,132 MiB (95.5%) |
| Process | VLLM::EngineCore (Qwen3-14B) |
| PCIe Bus | 41:00.0 |
| PCIe Device Max | Gen 5, x16 |
| PCIe Host Max | Gen 5, x16 |
| PCIe Negotiated (Idle) | Gen 1 x16 (2.5 GT/s) -- normal idle power saving |
| PCIe Full Speed | Gen 5 x16 (32 GT/s) = ~63 GB/s bidirectional |
| Current Power | 23 W |
| Max Power Limit | 600 W |
| Temperature | 38 C (52 C headroom to T.Limit) |
| GPU Utilization | 0% |
| Memory Utilization | 0% |
| Fan Speed | 0% |
| Max Clocks | Graphics 3180 MHz, Memory 14001 MHz |
| Current Clocks | Graphics 270 MHz, Memory 405 MHz (idle) |
| VBIOS | 98.02.2E.40.0E |
| UUID | GPU-1cd6a93d-cfc7-852f-e283-fd2383c447db |
| Thermal Throttling | None (HW/SW) |
| SW Power Capping Events | 238,959 us cumulative |

### GPU 1: NVIDIA GeForce RTX 5060 Ti

| Property | Value |
|----------|-------|
| Architecture | Blackwell (sm_120) |
| VRAM | 16,311 MiB GDDR7 |
| VRAM Used | 146 MiB (0.9%) |
| Process | python3 (ComfyUI, idle) |
| PCIe Bus | 81:00.0 |
| PCIe Device Max | Gen 5, **x8** |
| PCIe Host Max | **Gen 4**, x16 (slot wider than card) |
| PCIe Negotiated (Idle) | Gen 1 x8 (2.5 GT/s) -- normal idle |
| PCIe Full Speed | Gen 4 x8 (16 GT/s) = ~15.75 GB/s bidirectional |
| Current Power | 3 W |
| Max Power Limit | 180 W (overclockable to 200 W) |
| Temperature | 31 C |
| GPU Utilization | 0% |
| Memory Utilization | 41% (likely display-related) |
| Fan Speed | 0% |
| Max Clocks | Graphics 3090 MHz, Memory 14001 MHz |
| Current Clocks | Graphics 180 MHz, Memory 405 MHz (idle) |
| VBIOS | 98.06.4E.40.B4 |
| UUID | GPU-466af313-a55a-67bf-a692-794a00c9fceb |
| Display Attached | Yes (active display output) |
| Thermal Throttling | None |

### GPU Topology

```
GPU0 (5090) <--NODE--> GPU1 (5060 Ti)
  Bus 0x40 domain         Bus 0x80 domain
  PCIe Root 40:01.1       PCIe Root 80:03.1
```

Connection type: NODE (traverses PCIe + Host Bridge interconnect within the same NUMA node). This means GPU-to-GPU communication goes through the CPU's Infinity Fabric. Not relevant for current usage since the GPUs are used independently.

### Inventory Discrepancy

| Field | Inventory Says | Actual |
|-------|---------------|--------|
| RTX 5060 Ti PCIe | PCIe 5.0 x16 | PCIe 5.0 **x8** (card design); slot limited to **Gen 4** |

The RTX 5060 Ti is physically an x8 card. The GB205 die uses a PCIe 5.0 x8 interface by design -- this is not an error or limitation, it is the specification of the product. The motherboard slot (80:03.1) only supports Gen 4 speeds, further limiting bandwidth to Gen4 x8 (~15.75 GB/s). For ComfyUI image/video generation where models are loaded once and compute is done on-GPU, this is adequate.

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| 5090 VRAM | verified | 32 GB matches inventory |
| 5060 Ti VRAM | verified | 16 GB matches inventory |
| 5090 PCIe | verified | Gen5 x16 capable, slot supports it |
| 5060 Ti PCIe | MISMATCH | Card is x8 (not x16), slot is Gen4 (not Gen5) |
| 5090 utilization | loaded-idle | 95% VRAM used by vLLM, 0% compute -- waiting for requests |
| 5060 Ti utilization | idle | <1% VRAM, 0% compute -- ComfyUI loaded but no active jobs |
| Thermals | optimal | Both GPUs well below thermal limits |
| Power | optimal | Both at idle power, no throttling |
| Persistence Mode | suboptimal | Off -- first CUDA call after idle has ~100ms overhead |
| Driver | verified | 580.126.09, CUDA 13.0 -- fully supports Blackwell |

---

## 4. Storage

### NVMe Drives

| Device | Model | Gen | Capacity | Link Speed (Current) | Mount | Use |
|--------|-------|-----|----------|---------------------|-------|-----|
| nvme0 | Crucial T700 (CT4000T700SSD5) | Gen5 | 4 TB | Gen5 x4 (32 GT/s) | / (LVM), /boot, /boot/efi | OS + system |
| nvme1 | Crucial T700 (CT1000T700SSD3) | Gen5 | 1 TB | Gen5 x4 (32 GT/s) | **NONE** | ZFS label "hpc_nvme" -- UNUSED |
| nvme2 | Crucial T700 (CT1000T700SSD3) | Gen5 | 1 TB | Gen5 x4 (32 GT/s) | **NONE** | ZFS label "hpc_nvme" -- UNUSED |
| nvme3 | Crucial T700 (CT1000T700SSD3) | Gen5 | 1 TB | Gen4 x4 (16 GT/s) | **NONE** | ZFS label "hpc_nvme" -- UNUSED |

### NVMe Health (SMART)

| Drive | Temp | Wear | Media Errors | Unsafe Shutdowns | Power-On Hours | Data Written |
|-------|------|------|-------------|-----------------|---------------|-------------|
| nvme0 (4TB) | 56 C | 1% | 0 | 41 | 2,906 | 52.06 TB |
| nvme1 (1TB) | 56 C | 3% | 0 | 35 | 6,928 | 20.26 TB |
| nvme2 (1TB) | 54 C | 3% | 0 | 33 | 6,972 | 19.69 TB |
| nvme3 (1TB) | 38 C | 3% | 0 | 35 | 6,977 | 19.69 TB |

All drives healthy. Zero media errors. Low wear. The 1 TB drives have more power-on hours (6,900+) than the 4 TB boot drive (2,900), suggesting they were previously used in a different system.

### NFS Mounts

| Source | Mount Point | Size | Used | Free | Use% |
|--------|------------|------|------|------|------|
| 192.168.1.203:/mnt/user/models | /mnt/vault/models | 932 GB | 121 GB | 810 GB | 13% |
| 192.168.1.203:/mnt/user/data | /mnt/vault/data | 165 TB | 147 TB | 19 TB | 89% |

NFS options: NFSv4.2, rsize/wsize=131072, soft mount, TCP. Performance: **703 MB/s** sequential read (excellent for 5GbE).

### Root Filesystem

| Filesystem | Type | Size | Used | Free | Use% |
|------------|------|------|------|------|------|
| /dev/mapper/ubuntu--vg-ubuntu--lv | ext4 (LVM) | 3.6 TB | 152 GB | 3.3 TB | 5% |

### Docker Storage

| Resource | Size | Reclaimable |
|----------|------|-------------|
| Images | 135.2 GB | 134.8 GB (99%) |
| Containers | 132.7 MB | 0 B |
| Volumes | 1.428 GB | 0 B |
| Build Cache | 107.8 GB | **84.8 GB** |

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Boot drive | verified | T700 4TB Gen5, matches inventory |
| 3x 1TB drives | UNUSED | ZFS pool "hpc_nvme" exists but ZFS not installed/imported. **3 TB wasted.** |
| nvme3 link speed | degraded | Running Gen4 instead of Gen5 -- may be slot BIOS config or physical issue |
| Root filesystem | underutilized | 3.3 TB free on boot drive |
| Docker build cache | reclaimable | 84.8 GB can be freed with `docker builder prune` |
| NFS health | verified | Both mounts active, good performance |
| VAULT data array | warning | 89% full (19 TB remaining) |

### Critical Finding: 3 TB NVMe Unused

Three Crucial T700 1TB Gen5 NVMe drives carry ZFS labels for pool "hpc_nvme" but:
- ZFS userspace tools are not installed
- The pool is not imported
- No mount point exists

The inventory documents these as allocated for "Docker", "Temp/scratch", and "ComfyUI" but none of these functions are using them. All Docker data and ComfyUI output live on the 4TB boot drive's LVM volume. These drives could provide:
- A high-speed scratch pool for ComfyUI temp files and video rendering
- A dedicated Docker storage backend
- A fast local cache for NFS-served models

---

## 5. Network

### Interfaces

| Interface | Chip | Speed | MTU | IP | Status | Role |
|-----------|------|-------|-----|-----|--------|------|
| eno1 | Aquantia AQC113C | 10 Gbps | 9000 | 192.168.1.225 (static) | UP | Primary (data plane) |
| enp71s0 | Realtek RTL8125 | 2.5 Gbps | 1500 | 192.168.1.205 (DHCP) | UP | Secondary |
| wlp70s0 | Qualcomm WCN785x (WiFi 7) | -- | 1500 | -- | DOWN | Unused |
| docker0 | Virtual bridge | -- | 1500 | 172.17.0.1/16 | UP | Docker |

### Routing

```
default via 192.168.1.1 dev eno1 proto static          <-- primary default
default via 192.168.1.1 dev enp71s0 proto dhcp metric 200  <-- secondary (higher metric)
```

The primary default route correctly uses eno1 (5GbE). The secondary route via enp71s0 has metric 200 so it serves as a fallback. ARP shows VAULT traffic flows over eno1 (REACHABLE state).

### 5GbE NIC Details (eno1)

| Property | Value |
|----------|-------|
| Chip | Aquantia/Marvell AQC113C |
| Supported Speeds | 100M/1G/2.5G/5G/10G |
| Negotiated Speed | 10000 Mb/s Full Duplex |
| MTU | 9000 (jumbo frames) |
| Wake-on-LAN | Disabled |
| Auto-negotiation | On |

### Thunderbolt 4

The TRX50 AERO D has Intel Maple Ridge Thunderbolt 4 controllers detected at bus 48-5d. These are functional but unused. Could potentially be used for direct Thunderbolt networking to another machine (40 Gbps).

### TCP Tuning

| Parameter | Current | Recommended for 5GbE |
|-----------|---------|-----------------------|
| net.core.rmem_max | 212,992 | 16,777,216 |
| net.core.wmem_max | 212,992 | 16,777,216 |
| net.ipv4.tcp_rmem | 4096 131072 33554432 | OK (max already 32 MB) |
| net.ipv4.tcp_wmem | 4096 16384 4194304 | 4096 65536 16777216 |

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| 5GbE link | optimal | Full 10 Gbps, jumbo frames enabled |
| NFS performance | good | 703 MB/s read -- 64% of theoretical 5GbE max |
| MTU match | verified | eno1 at MTU 9000, consistent with 5GbE data plane |
| Secondary NIC | informational | enp71s0 at 2.5G -- usable for management traffic |
| WiFi 7 | unused | wlp70s0 DOWN -- not needed for server role |
| TCP buffers | suboptimal | Core buffer limits too small for 5GbE saturation |
| Routing | acceptable | Dual default routes but metric ordering is correct |

---

## 6. PCIe Topology

### Full Topology Map

```
[0000:00] Root Complex (CPU PCIe Domain 0)
  +-- 01.1 [01] nvme0n1: Crucial T700 4TB -- Gen5 x4 (32 GT/s) -- BOOT
  +-- 01.2 [02] nvme1n1: Crucial T700 1TB -- Gen5 x4 (32 GT/s) -- UNUSED
  +-- 01.3 [03] nvme2n1: Crucial T700 1TB -- Gen5 x4 (32 GT/s) -- UNUSED

[0000:40] Root Complex (CPU PCIe Domain 1)
  +-- 01.1 [41] NVIDIA RTX 5090    -- Gen5 x16 capable -- OK
  +-- 03.1 [42] nvme3n1: Crucial T700 1TB -- Gen5 x4 (running Gen4!) -- DEGRADED
  +-- 03.3 [43-5f] TRX50 Chipset Bridge:
        +-- [45] Aquantia AQC113C 5GbE
        +-- [46] Qualcomm WCN785x WiFi 7
        +-- [47] Realtek RTL8125 2.5GbE
        +-- [48-5d] Intel Maple Ridge Thunderbolt 4
        +-- [5e] AMD 600 Series USB 3.2
        +-- [5f] AMD 600 Series SATA

[0000:80] Root Complex (CPU PCIe Domain 2)
  +-- 03.1 [81] NVIDIA RTX 5060 Ti -- Gen4 x8 (host limit Gen4, card limit x8)

[0000:c0] Root Complex (CPU PCIe Domain 3)
  (empty -- no devices attached)
```

### PCIe Bandwidth Summary

| Device | Capable | Negotiated (Active) | Bandwidth |
|--------|---------|-------------------|-----------|
| RTX 5090 | Gen5 x16 | Gen5 x16 | ~63 GB/s |
| RTX 5060 Ti | Gen5 x8 | Gen4 x8 | ~15.75 GB/s |
| T700 4TB (boot) | Gen5 x4 | Gen5 x4 | ~15.75 GB/s |
| T700 1TB (nvme1) | Gen5 x4 | Gen5 x4 | ~15.75 GB/s |
| T700 1TB (nvme2) | Gen5 x4 | Gen5 x4 | ~15.75 GB/s |
| T700 1TB (nvme3) | Gen5 x4 | **Gen4 x4** | ~7.88 GB/s (degraded) |

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| 5090 PCIe | optimal | Full Gen5 x16 to CPU |
| 5060 Ti PCIe | limited | Gen4 x8 -- host slot caps at Gen4, card is x8 by design |
| NVMe drives (3/4) | optimal | Gen5 x4 at full speed |
| NVMe nvme3 | degraded | Running Gen4 x4, losing half its bandwidth |
| Domain c0 | empty | PCIe domain 3 has no devices -- an expansion slot is available |

---

## 7. Docker Containers

### Running Containers

| Container | Image | GPU | Port(s) | CPU% | RAM | Status |
|-----------|-------|-----|---------|------|-----|--------|
| vllm-node2 | nvcr.io/nvidia/vllm:25.12-py3 | 0 (5090) | 8000 (host net) | 2.85% | 2.0 GiB | Up 4h |
| comfyui | athanor/comfyui:blackwell | 1 (5060 Ti) | 8188 | 0.07% | 840 MiB | Up 4h |
| athanor-dashboard | athanor/dashboard:latest | -- | 3001 | 0.00% | 35 MiB | Up 1h |
| athanor-eoq | athanor/eoq:latest | -- | 3002 | 0.00% | 27 MiB | Up 3h |
| open-webui | ghcr.io/open-webui/open-webui:main | -- | 3000 | 0.16% | 917 MiB | Up 2d |
| dcgm-exporter | nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9 | -- | 9400 | 0.01% | 487 MiB | Up 2d |
| node-exporter | prom/node-exporter:latest | -- | 9100 | 0.00% | 14 MiB | Up 2d |

### vLLM Configuration

```
Model: Qwen3-14B
Tensor Parallel: 1
Context Length: 8192
GPU Memory Utilization: 0.95
Max Concurrent: 32
Dtype: float16
Tool Calling: hermes parser, auto-tool-choice
Mode: enforce-eager (no CUDA graphs)
Network: host mode
```

VRAM consumption: 31,122 MiB / 32,607 MiB (95.5%). The 5090 is essentially a dedicated Qwen3-14B inference card.

### Assessment

| Aspect | Status | Detail |
|--------|--------|--------|
| Container health | verified | All 7 containers running |
| GPU assignment | correct | 5090 -> vLLM, 5060 Ti -> ComfyUI |
| Total container RAM | 4.3 GiB | 3.4% of system RAM |
| Total container CPU | ~3% | Negligible |
| vLLM config | reasonable | 0.95 util on 32GB is tight but appropriate for single model |
| ComfyUI | idle | Models offloaded, 128 MiB resident |

---

## 8. OS / Kernel / BIOS

### System Info

| Property | Value |
|----------|-------|
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | 6.17.0-14-generic (HWE, PREEMPT_DYNAMIC) |
| Motherboard | Gigabyte TRX50 AERO D |
| BIOS | AMI, version FA3e, dated 2025-10-30 |
| SMBIOS | 3.7.0 |
| Boot params | `BOOT_IMAGE=/vmlinuz-6.17.0-14-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro` |
| Docker | overlay2 storage driver, root at /var/lib/docker |
| NVIDIA Driver | 580.126.09 (Open Kernel Module) |
| CUDA | 13.0 |
| GSP Firmware | 580.126.09 |

### Kernel Tuning

| Parameter | Current | Optimal | Notes |
|-----------|---------|---------|-------|
| vm.swappiness | 60 | 10 | Default is too aggressive for a server with 128 GB RAM |
| HugePages | 0 | 0 | Not configured -- could help vLLM if CUDA uses system memory |
| IOMMU | not detected in dmesg | -- | Not enabled in kernel params |
| CPU governor | powersave | performance | See CPU section |
| TCP rmem_max | 212,992 | 16,777,216 | Limits 5GbE throughput |
| TCP wmem_max | 212,992 | 16,777,216 | Limits 5GbE throughput |
| sunrpc.tcp_max_slot_table_entries | 65,536 | 65,536 | Already optimal for NFS |

### Services

| Service | Status | Notes |
|---------|--------|-------|
| docker | running | Active, all containers healthy |
| containerd | running | |
| nvidia-persistenced | running | BUT launched with `--no-persistence-mode` |
| sshd | running | Port 22 |
| rpcbind | running | For NFS |
| smartmontools | running | Drive monitoring |
| ModemManager | running | Unnecessary -- can be disabled |
| upower | running | Unnecessary for server |

---

## 9. Power and Thermals

### Current Power Draw

| Component | Power | Limit | Headroom |
|-----------|-------|-------|----------|
| RTX 5090 | 23 W | 600 W | 577 W |
| RTX 5060 Ti | 3 W | 180 W | 177 W |
| CPU (est.) | ~50 W | 350 W | ~300 W |
| **System Total (est.)** | **~100 W idle** | -- | -- |
| **System Peak (est.)** | **~1,100 W** | **PSU: 1,600 W** | **~500 W** |

### Thermal Summary

| Component | Temperature | Status |
|-----------|-------------|--------|
| CPU (Tctl) | 45 C | Cool |
| CPU (Tdie) | 54-56 C | Normal |
| GPU 0 (5090) | 38 C | Cool |
| GPU 1 (5060 Ti) | 31 C | Cold |
| NVMe 0 (4TB boot) | 56 C | Normal |
| NVMe 1 (1TB) | 56 C | Normal |
| NVMe 2 (1TB) | 54 C | Normal |
| NVMe 3 (1TB) | 38 C | Cool |

No thermal throttling detected on any component. Both GPUs at 0% fan speed (fanless at idle). The MSI 1600W PSU has ample headroom for peak loads even with both GPUs at full power simultaneously (600 + 180 + 350 = 1,130 W theoretical max).

### Is the 5090 Thermally Throttling?

**No.** The 5090 is at 38 C with 52 C headroom to its T.Limit. GPU Slowdown and HW Thermal Slowdown are both "Not Active". The 238,959 us of SW Power Capping events are cumulative since boot and represent brief transients, not sustained throttling.

---

## 10. Answers to Key Questions

### Q1: Is the DDR5 running at full speed or JEDEC default?

**JEDEC default.** All 4 DIMMs are running at 4800 MT/s instead of their rated 5600 MT/s. Kingston FURY KF556R28-32 modules support AMD EXPO profiles for 5600 MT/s CL28 operation, but EXPO has not been enabled in the Gigabyte TRX50 AERO D BIOS. This requires a BIOS change via JetKVM (.165). This leaves **25.6 GB/s of memory bandwidth** on the table.

### Q2: Are both GPUs getting full PCIe bandwidth?

**The 5090 is. The 5060 Ti is not, but this is by design.**

- RTX 5090: Gen5 x16 capable, host supports Gen5 x16. Full ~63 GB/s bidirectional. Verified.
- RTX 5060 Ti: The card itself is PCIe 5.0 **x8** (not x16 as documented in inventory). The motherboard slot (80:03.1) caps at Gen4. So effective bandwidth is Gen4 x8 = ~15.75 GB/s. This is an inherent limitation of the 5060 Ti's GB205 die and the specific motherboard slot, not a misconfiguration.

### Q3: Is the 5090 being fully utilized or sitting mostly idle?

**Loaded but idle.** The 5090 has Qwen3-14B consuming 31.1 GB of its 32 GB VRAM (95.5%), but GPU compute utilization is 0%. The model is loaded and ready but no inference requests were active at audit time. The card is doing its job -- it is a dedicated inference server waiting for work. Whether it receives enough traffic to justify a 32 GB card is a utilization planning question.

### Q4: How much of the 128GB RAM is actually being used?

**8.5 GiB (6.8%).** 116 GiB is available. The system buffer/cache is using 110 GiB (which is the OS efficiently caching disk data and is reclaimable). Actual process memory consumption is tiny -- all the heavy compute happens on GPUs with their own VRAM.

### Q5: Is there unused compute capacity on the TR 7960X?

**Massively.** The CPU is at 0.5% utilization (load average 0.25 on 48 threads). It has:
- 24 cores / 48 threads of Zen 4 with AVX-512
- 128 MB L3 cache
- Essentially zero workload

This CPU could handle significant additional tasks without impacting GPU inference: compilation jobs, data preprocessing, CPU-based inference, transcoding, database workloads, or additional containers.

---

## 11. Inventory Discrepancies

| Item | Inventory (inventory.md) | Actual | Severity |
|------|-------------------------|--------|----------|
| RTX 5060 Ti PCIe | "PCIe 5.0 x16" | PCIe 5.0 x8 (card design), running Gen4 x8 (slot limit) | Medium -- doc error |
| 3x 1TB NVMe use | "Docker", "Temp/scratch", "ComfyUI" | ZFS label "hpc_nvme", NOT MOUNTED, unused | High -- 3 TB wasted |
| nvme3 link speed | Gen5 (implied) | Running Gen4 x4 (degraded) | Low -- possible BIOS/slot issue |
| GPU persistence mode | Not documented | Off (daemon runs with --no-persistence-mode) | Informational |
| Node 2 IP in inventory notes | .225 (5090 "ComfyUI primary") | 5090 is running vLLM, not ComfyUI. 5060 Ti runs ComfyUI. | Medium -- role description outdated |

---

## 12. Optimization Recommendations (Priority Order)

### High Priority

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | **Enable EXPO in BIOS** via JetKVM (.165) | +25.6 GB/s memory bandwidth (+16.6%) | 5 min BIOS change |
| 2 | **Import/mount 3x 1TB NVMe pool** | Reclaim 3 TB Gen5 storage for scratch/Docker/cache | 15 min ZFS setup |
| 3 | **Set CPU governor to performance** | Lower inference latency, faster burst response | 2 min sysctl |
| 4 | **Clean Docker build cache** | Reclaim 84.8 GB disk space | 1 min command |

### Medium Priority

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 5 | **Tune TCP buffers for 5GbE** | Better NFS throughput under concurrent load | 5 min sysctl |
| 6 | **Set vm.swappiness=10** | Reduce unnecessary swap pressure | 1 min sysctl |
| 7 | **Enable GPU persistence mode** | Eliminate first-request latency overhead | 2 min systemd |
| 8 | **Disable ModemManager/upower** | Remove unnecessary services | 2 min systemctl |
| 9 | **Investigate nvme3 Gen4 degradation** | May recover 2x bandwidth on that drive | BIOS check |

### Low Priority / Planning

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 10 | **Plan workloads for idle CPU/RAM** | 116 GB RAM and 47 threads sitting idle | Architecture decision |
| 11 | **Update inventory.md** | Fix 5060 Ti PCIe spec and GPU role descriptions | 5 min doc edit |
| 12 | **Install lm-sensors** | Better thermal monitoring | 1 min apt install |
| 13 | **Consider Thunderbolt 4 networking** | 40 Gbps direct link to another node (if useful) | Hardware planning |

---

## 13. Raw Data Reference

### Listening Ports

| Port | Service | Binding |
|------|---------|---------|
| 22 | sshd | 0.0.0.0 + [::] |
| 53 | systemd-resolved | 127.0.0.53 + 127.0.0.54 |
| 111 | rpcbind | 0.0.0.0 + [::] |
| 3000 | Open WebUI | 0.0.0.0 + [::] |
| 3001 | Athanor Dashboard | 0.0.0.0 + [::] |
| 3002 | Athanor EoBQ | 0.0.0.0 + [::] |
| 8000 | vLLM API (host net) | 0.0.0.0 |
| 8188 | ComfyUI | 0.0.0.0 + [::] |
| 9100 | Node Exporter | * |
| 9400 | DCGM Exporter | 0.0.0.0 |

### CPU Flags (Notable)

`avx512f avx512dq avx512bw avx512vl avx512_bf16 avx512vbmi avx512_vnni avx512_vpopcntdq sha_ni aes vaes vpclmulqdq gfni svm`

### Kernel

```
Linux interface 6.17.0-14-generic #14~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Jan 15 15:52:10 UTC 2 x86_64
NVIDIA Open Kernel Module 580.126.09
```
