# Athanor Complete System Breakdown

> Atlas note: [`docs/atlas/README.md`](../atlas/README.md) is now the canonical cross-layer system map. This file remains an exhaustive hardware reference, not the primary system map.

**Last Updated:** 2026-02-21
**Purpose:** Exhaustive hardware documentation for all 4 systems

---

# System Overview - Physical Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RACK LAYOUT (Front View)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [5U] NODE 1 "Foundry" - Core Inference                            │
│       Silverstone RM52 Upper Tray                                   │
│       192.168.1.244 (eth0) / 192.168.1.246 (eth1)                   │
│       ASRock Rack ROMED8-2T + EPYC 7663                             │
│       5× GPUs (88 GB VRAM), 224 GB ECC RAM                          │
│       MSI MEG Ai1600T 1600W PSU (95% utilized)                      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [5U] NODE 2 "Workshop" - Interface Layer                          │
│       Silverstone RM52 Middle Tray                                  │
│       192.168.1.225 (eth0)                                          │
│       Gigabyte TRX50 AERO D + Threadripper 7960X                    │
│       2× GPUs (48 GB VRAM), 128 GB ECC RAM                          │
│       MSI 1600W PSU (55% utilized, 720W headroom)                   │
│       JetKVM @ 192.168.1.165 (ATX cable disconnected!)              │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [4U] VAULT "Storage" - NFS/Services/Monitoring                     │
│       Unknown Case                                                  │
│       192.168.1.203 (eth0)                                          │
│       ASUS ProArt X870E + Ryzen 9950X                               │
│       1× GPU (6 GB), 128 GB RAM, 184 TB HDD array                   │
│       Unknown PSU (~460W load)                                      │
│       JetKVM @ 192.168.1.80 (working)                               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Tower] DEV "Workstation" - Development & Testing                  │
│       Unknown Tower Case                                            │
│       192.168.1.215 (eth0)                                          │
│       Gigabyte Z690 AORUS ULTRA + i7-13700K                         │
│       1× GPU (8 GB AMD), 64 GB RAM                                  │
│       Unknown PSU                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# NODE 1 "Foundry" - Complete Hardware Map

## Physical Information
- **Location:** Rack position 1 (top), 5U Silverstone RM52 Upper Tray
- **IP Addresses:**
  - Primary: 192.168.1.244 (Intel X550 5GbE eth0)
  - Secondary: 192.168.1.246 (Intel X550 5GbE eth1)
- **SSH Access:** `ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244`
- **Role:** Heavy inference, TP pooling, agent serving

## Motherboard: ASRock Rack ROMED8-2T

**[Full specifications](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)**

### CPU Socket
- **Socket:** SP3 (LGA 4094)
- **Installed:** AMD EPYC 7663 (56 cores, 112 threads)
  - Base: 2.0 GHz, Boost: 3.5 GHz
  - TDP: 240W (running at 180W, 75% TDP)
  - 256 MB L3 cache
  - PCIe 4.0, 128 lanes total

### Memory Slots (8× DDR4 ECC RDIMM)
```
DIMM A1: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM A2: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM B1: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM B2: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM C1: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM C2: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM D1: Samsung 32GB DDR4 ECC 3200 MT/s    [POPULATED]
DIMM D2: EMPTY                               [AVAILABLE - can add 32GB+]

Total Installed: 224 GB DDR4 ECC (7× 32GB)
Max Capacity: 2 TB (8× 256GB RDIMMs)
```

### PCIe Expansion Slots (7× PCIe 4.0 x16, all CPU-direct)
```
PCIE1 [Gen4 x16]: RTX 4090 24GB Founders         [POPULATED]
                  12V-2x6 native power
                  Power: 320W (optimized from 450W)

PCIE2 [Gen4 x16]: RTX 5070 Ti 16GB               [POPULATED]
                  12V-2x6 native power
                  Power: 240W (optimized from 300W)
                  TP=4 pool member #1

PCIE3 [Gen4 x16]: RTX 5070 Ti 16GB               [POPULATED]
                  3× 8-pin → 12V-2x6 adapter
                  Power: 240W (optimized from 300W)
                  TP=4 pool member #2

PCIE4 [Gen4 x16]: RTX 5070 Ti 16GB               [POPULATED]
                  3× 8-pin → 12V-2x6 adapter
                  Power: 240W (optimized from 300W)
                  TP=4 pool member #3

PCIE5 [Gen4 x16]: RTX 5070 Ti 16GB               [POPULATED]
                  3× 8-pin → 12V-2x6 adapter
                  Power: 240W (optimized from 300W)
                  TP=4 pool member #4

PCIE6 [Gen4 x16]: ASUS Hyper M.2 X16 Gen5        [POPULATED]
                  64 Gbps bandwidth
                  4× Crucial P310 1TB NVMe (4 TB total)
                  Gen4 drives in Gen5 adapter
                  Use: Local model cache, fast scratch storage

PCIE7 [Gen4 x16]: EMPTY                          [AVAILABLE]
                  64 Gbps bandwidth
                  Candidates: InfiniBand ConnectX-3 FDR card
                            5GbE NIC (redundant, already has dual 5GbE)
                            Future: Second Hyper M.2 if storage needs grow
                  Note: Second Hyper M.2 adapter allocated to DEV for Gen5 storage

Note: PCIE2 can run at x8 via jumper (PE8_SEL/PE16_SEL) - currently set to x16
```

### M.2 NVMe Slots (2× PCIe 4.0 x4)
```
M.2_1 [Gen4 x4]: Crucial P3 4TB                  [POPULATED]
                 16 Gbps bandwidth
                 OS/system partition, Ubuntu 24.04

M.2_2 [Gen4 x4]: Samsung 990 PRO 4TB             [NOT DETECTED - ISSUE]
                 16 Gbps bandwidth
                 Intended: Hot model cache
                 Status: Physical reseating required
```

### OCuLink Ports (2× PCIe 4.0 x4)
```
OCuLink_1: Not used                              [AVAILABLE]
OCuLink_2: Not used                              [AVAILABLE]
```

### Network Interfaces
```
eth0 (Intel X550): 5GbE RJ45                    [ACTIVE - 192.168.1.244]
                   Currently on USW Pro 24 PoE (1GbE switch)
                   Target: USW Pro XG 10 PoE (5GbE switch)

eth1 (Intel X550): 5GbE RJ45                    [ACTIVE - 192.168.1.246]
                   Currently on USW Pro 24 PoE (1GbE switch)
                   Target: USW Pro XG 10 PoE (5GbE switch)

IPMI/BMC:          AMI MegaRAC @ 192.168.1.216   [CONFIGURED]
                   admin credential managed outside the repo
                   IPMI-over-LAN needs enabling
```

### USB Ports
```
Front: 2× USB 3.0
Rear:  6× USB 3.0, 2× USB 2.0
Total: 10× USB ports
```

### Power Supply: MSI MEG Ai1600T PCIE5
```
Capacity:           1600W (80+ Titanium, 94% efficiency)
Native 12V-2x6:     2× ports (600W each)
PCIe 8-pin:         5× cables (11 total connectors via daisy-chain)

Current Load Breakdown:
  EPYC 7663:        180W (75% of 240W TDP)
  RTX 4090:         320W (optimized)
  4× RTX 5070 Ti:   960W (240W each, optimized)
  Motherboard:       40W
  RAM (224 GB):      20W
  2× NVMe:           10W
  Fans:              10W
  ─────────────────────
  TOTAL:          1,520W (95% PSU utilization, 80W headroom)

Wiring:
  - GPU Slot 1 (RTX 4090):    Native 12V-2x6 port 1
  - GPU Slot 2 (RTX 5070 Ti): Native 12V-2x6 port 2
  - GPU Slot 3 (RTX 5070 Ti): 3× PCIe 8-pin → adapter
  - GPU Slot 4 (RTX 5070 Ti): 3× PCIe 8-pin → adapter
  - GPU Slot 5 (RTX 5070 Ti): 3× PCIe 8-pin → adapter (daisy-chain optimization)
  - Motherboard: 24-pin ATX + 8-pin EPS + 8-pin EPS2

Documentation: docs/hardware/NODE1-GPU-POWER-WIRING.md
```

### Storage Summary
```
Local NVMe:   12 TB installed (16 TB when 990 PRO reseated)
  - Onboard M.2_1: Crucial P3 4TB (active)
  - Onboard M.2_2: Samsung 990 PRO 4TB (NOT DETECTED - needs reseating)
  - Slot 6 Hyper M.2: 4× Crucial P310 1TB = 4 TB (active)

NFS Mounts:   /mnt/vault/models (22 TB, from VAULT)
              /mnt/vault/data (22 TB, from VAULT)
              /mnt/vault/appdata (from VAULT)

Expansion Potential:
  - Slot 7: Install second Hyper M.2 Gen5 adapter → +4 NVMe drives
  - Available loose: 6 TB NVMe (6 drives remaining)
  - Potential total: 12 TB + 6 TB = 18 TB local NVMe (22 TB with 990 PRO)
```

### GPU Configuration Detail
```
Total VRAM: 88 GB across 5 GPUs

RTX 4090 (Slot 1):
  - VRAM: 24 GB GDDR6X
  - Bandwidth: 1,008 GB/s
  - CUDA Cores: 16,384
  - Tensor Cores: 512 (Gen 4)
  - Power: 320W (71% of 450W stock)
  - Current use: IDLE (available for workload)
  - Potential: Qwen3-14B instance, tool calling agent, separate inference

RTX 5070 Ti (Slots 2-5, TP=4 pool):
  - VRAM: 64 GB pooled (4× 16 GB GDDR7)
  - Bandwidth: 4× 672 GB/s = 2,688 GB/s aggregate
  - CUDA Cores: 4× 8,960 = 35,840 total
  - Tensor Cores: 4× 280 (Gen 5) = 1,120 total
  - Power: 960W total (240W each, 80% of stock)
  - Current use: vLLM Qwen3-32B-AWQ (TP=4, 15.6 GB/GPU)
  - NVLink: None (requires NVSwitch for Blackwell TP)
```

### Services Running
```
vLLM (port 8000):
  - Model: Qwen3-32B-AWQ (15.6 GB per GPU)
  - Backend: awq_marlin quantization
  - Config: TP=4 across GPUs 1-4 (RTX 5070 Ti)
  - Context: 32K tokens
  - Performance: ~120 tok/s

Agent Server (port 9000):
  - Framework: LangGraph + FastAPI
  - Agents: General Assistant, Media Agent, Home Agent (inactive)
  - Tools: Service health, GPU metrics, Sonarr/Radarr, Tautulli
  - Model: Calls vLLM on localhost:8000

Monitoring:
  - node_exporter (port 9100)
  - dcgm-exporter (port 9400)
```

### Storage Summary
```
NVMe Configuration:
  - Onboard M.2_1: Samsung 990 PRO 4TB Gen4 (needs reseat, not detected)
  - Onboard M.2_2: Samsung 990 PRO 4TB Gen4 ✅
  - Slot 6: ASUS Hyper M.2 X16 Gen5 (4× Crucial P310 1TB = 4 TB) ✅

  Total Local NVMe: 12 TB configured (16 TB when M.2_1 reseated)
  Performance: Gen4 drives in Gen5 adapter (run at Gen4 speeds)
  Use: Model storage, datasets, fast cache for vLLM inference

### Available Expansion Options
```
1. NVMe Storage - Slot 7 available
   - Could add InfiniBand card for node-to-node pipeline parallelism
   - Could add 5GbE NIC (redundant with onboard dual 5GbE)
   - Future: Second Hyper M.2 if model library grows beyond 12 TB

2. InfiniBand Networking (Slot 7 alternative)
   - Alternative to second Hyper M.2 adapter
   - Add Mellanox ConnectX-3 FDR card
   - 56 Gbps link to Node 2 for NCCL/pipeline parallelism
   - Cost: ~$30
   - Deferred (prioritize storage expansion first)

3. 6th GPU - RTX 3060 12GB (Phase C only - BLOCKED)
   - Slot 6 now occupied by Hyper M.2 adapter
   - Would require Slot 7 OR removing Hyper M.2 from Slot 6
   - Requires dual PSU (ASUS ROG 1200W secondary) + mining enclosure
   - Total VRAM: 100 GB (88 + 12)
   - Deferred to Phase C hardware reconfiguration
```

---

# NODE 2 "Workshop" - Complete Hardware Map

## Physical Information
- **Location:** Rack position 2 (middle), 5U Silverstone RM52 Middle Tray
- **IP Address:** 192.168.1.225 (Marvell 5GbE eth0)
- **SSH Access:** `ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225`
- **Peripherals:** JetKVM @ 192.168.1.165 (ATX power cable DISCONNECTED - needs reconnect)
- **Role:** Interface layer, creative workloads, tool calling, ComfyUI

## Motherboard: Gigabyte TRX50 AERO D Rev 1.x

**[Full specifications](https://www.gigabyte.com/Motherboard/TRX50-AERO-D-rev-1x)**

### CPU Socket
- **Socket:** sTR5 (LGA 4844)
- **Installed:** AMD Threadripper 7960X (24 cores, 48 threads)
  - Base: 4.2 GHz, Boost: 5.6 GHz
  - TDP: 350W (running at ~245W, 70% TDP)
  - 128 MB L3 cache
  - PCIe 5.0, 88 lanes total

### Memory Slots (4× DDR5 ECC RDIMM, Quad Channel)
```
DIMM A1: Kingston 32GB DDR5 ECC 5600 MT/s       [POPULATED]
                                                 (running at 4800 - EXPO not enabled!)
DIMM B1: Kingston 32GB DDR5 ECC 5600 MT/s       [POPULATED]
DIMM C1: Kingston 32GB DDR5 ECC 5600 MT/s       [POPULATED]
DIMM D1: Kingston 32GB DDR5 ECC 5600 MT/s       [POPULATED]

Total Installed: 128 GB DDR5 ECC (4× 32GB)
Current Speed: 4800 MT/s (EXPO disabled - enable in BIOS for 5600!)
Max Capacity: 1 TB (4× 256GB RDIMMs, TRX50 limit)

Note: TRX50 AERO D has ONLY 4 DIMM slots (not 8 like some TRX50 boards)
      All slots RDIMM-only (standard UDIMMs incompatible)
```

### PCIe Expansion Slots (3× PCIe 5.0 x16, all CPU-direct)
```
PCIE1 [Gen5 x16]: RTX 5090 32GB Founders         [POPULATED]
                  128 Gbps bandwidth
                  12V-2x6 native power
                  Power: 420W (optimized from 575W stock)
                  Current use: ComfyUI Flux dev FP8

PCIE2 [Gen5 x16]: RTX 5060 Ti 16GB               [POPULATED]
                  128 Gbps bandwidth
                  12V-2x6 native power
                  Power: 200W (optimized from 300W stock)
                  Current use: vLLM Qwen3-14B-AWQ

PCIE3 [Gen5 x16]: EMPTY                          [AVAILABLE]
                  128 Gbps bandwidth (full Gen5 speed)
                  Candidates: RTX 3060 12GB (RECOMMENDED - 720W PSU headroom!)
                            Hyper M.2 Gen5 adapter (+4 NVMe)
                            InfiniBand ConnectX-3 FDR card
```

### M.2 NVMe Slots (4× PCIe 5.0, all populated)
```
M.2_1 [Gen5 x4]: Crucial T700 4TB                [POPULATED]
                 32 Gbps bandwidth
                 OS/system, Ubuntu 24.04

M.2_2 [Gen5 x4]: Crucial T700 1TB                [POPULATED]
                 32 Gbps bandwidth
                 Docker volumes, containers

M.2_3 [Gen5 x4]: Crucial T700 1TB                [POPULATED]
                 32 Gbps bandwidth
                 Temp/scratch workspace

M.2_4 [Gen5 x4]: Crucial T700 1TB                [POPULATED]
                 32 Gbps bandwidth
                 ComfyUI output, workflows

Total: 7 TB local NVMe Gen5 (all slots used)
```

### Network Interfaces
```
eth0 (Marvell AQC113CS): 5GbE RJ45              [ACTIVE - 192.168.1.225]
                         Currently on USW Pro 24 PoE (1GbE switch)
                         Target: USW Pro XG 10 PoE (5GbE switch)

eth1 (Realtek RTL8125):  2.5GbE RJ45             [AVAILABLE]

WiFi 7 (802.11be):       WiFi 7 wireless         [AVAILABLE]

2× USB4 Type-C:          40 Gbps each            [AVAILABLE]
                         Can be used for 5GbE via adapter
```

### USB Ports
```
Rear:  8× USB 3.2 Gen2 (10 Gbps)
       2× USB4 Type-C (40 Gbps)
Front: Via case headers
Total: 10+ USB ports
```

### Power Supply: MSI 1600W
```
Capacity:           1600W (80+ Platinum, 92% efficiency)
Native 12V-2x6:     Likely 2× ports (600W each)
PCIe 8-pin:         Multiple cables

Current Load Breakdown:
  TR 7960X:         245W (70% of 350W TDP)
  RTX 5090:         420W (optimized)
  RTX 5060 Ti:      200W (optimized)
  Motherboard:       60W
  RAM (128 GB):      20W
  4× Gen5 NVMe:      25W (6-7W each under load)
  Fans:              10W
  ─────────────────────
  TOTAL:            980W (61% PSU utilization, 620W headroom)

With RTX 3060 added:
  + RTX 3060:       170W (at 170W TDP)
  ─────────────────────
  NEW TOTAL:      1,150W (72% PSU utilization, 450W headroom still!)

Conclusion: RTX 3060 easily fits in Slot 3 with 450W remaining headroom
```

### Storage Summary
```
Local NVMe:   7 TB (4× Gen5, all M.2 slots populated)
NFS Mounts:   /mnt/vault/models (22 TB, from VAULT)
              /mnt/vault/data (22 TB, from VAULT)
              /mnt/vault/appdata (from VAULT)

Expansion Potential:
  - Slot 3: Install Hyper M.2 Gen5 adapter → +4 NVMe drives
  - Available loose: 13 TB NVMe (7 drives)
  - Potential total: 7 TB + 4-5 TB = 11-12 TB local NVMe
```

### GPU Configuration Detail
```
Total VRAM: 48 GB (can be 60 GB with RTX 3060 added)

RTX 5090 (Slot 1):
  - VRAM: 32 GB GDDR7
  - Bandwidth: 1,792 GB/s
  - CUDA Cores: 21,760 (Blackwell architecture)
  - Tensor Cores: 680 (Gen 5, FP4 support)
  - Power: 420W (73% of 575W stock)
  - Current use: ComfyUI Flux dev FP8 (12 GB model, 20 GB VRAM used)
  - Utilization: ~60% VRAM used, ~40% idle capacity

RTX 5060 Ti (Slot 2):
  - VRAM: 16 GB GDDR7
  - Bandwidth: 672 GB/s
  - CUDA Cores: 8,960 (Blackwell architecture)
  - Tensor Cores: 280 (Gen 5)
  - Power: 200W (67% of 300W stock)
  - Current use: vLLM Qwen3-14B-AWQ (9.4 GB model, 21.5 GB VRAM used)
  - Utilization: IDLE most of time (tool calling only, low throughput)

RTX 3060 (Slot 3, if added):
  - VRAM: 12 GB GDDR6
  - Bandwidth: 360 GB/s
  - CUDA Cores: 3,584 (Ampere architecture)
  - Tensor Cores: 112 (Gen 3)
  - Power: 170W stock
  - Potential use: Local training, fine-tuning, secondary inference, CUDA dev
```

### Services Running
```
ComfyUI (port 8188):
  - GPU: RTX 5090 (pinned via CUDA_VISIBLE_DEVICES=0)
  - Models: Flux dev FP8 (12 GB), CLIP-L, T5-XXL FP8, VAE
  - Container: athanor/comfyui:blackwell (NGC PyTorch 2.7.0a0 base)
  - Output: /mnt/vault/data/comfyui/output

vLLM (port 8000):
  - Model: Qwen3-14B-AWQ (9.4 GB)
  - GPU: RTX 5060 Ti (pinned via CUDA_VISIBLE_DEVICES=1)
  - Backend: awq_marlin quantization
  - Context: 32K tokens
  - Performance: ~92 tok/s
  - Use: Tool calling, secondary inference (low traffic)

Open WebUI (port 3000):
  - Frontend for vLLM on Node 1
  - No GPU required

Dashboard (port 3001):
  - Next.js 16 monitoring UI
  - No GPU required

Monitoring:
  - node_exporter (port 9100)
  - dcgm-exporter (port 9400)
```

### Available Expansion Options
```
1. RTX 3060 12GB GPU (Slot 3) **RECOMMENDED**
   - Add 12 GB VRAM (→ 60 GB total)
   - 170W power draw (450W headroom available)
   - Use: Local training, fine-tuning, CUDA development, secondary inference
   - Cost: $0 (already owned)
   - Action: Move from loose inventory → Slot 3

2. NVMe Storage (Slot 3 via Hyper M.2 adapter)
   - Alternative to RTX 3060
   - Add Hyper M.2 Gen5 adapter → +4 NVMe drives
   - Populate with loose NVMe (4-5 TB potential)
   - Total: 11-12 TB local NVMe

3. InfiniBand Networking (Slot 3)
   - Alternative option
   - Mellanox ConnectX-3 FDR card
   - 56 Gbps link to Node 1 for NCCL/pipeline parallelism
   - Cost: ~$30

Priority: RTX 3060 in Slot 3 (maximizes GPU compute, plenty of PSU headroom)
```

---

# VAULT "Storage" - Complete Hardware Map

## Physical Information
- **Location:** Rack position 3 (lower), 4U unknown case
- **IP Address:** 192.168.1.203 (Aquantia 5GbE eth0)
- **SSH Access:** `python scripts/vault-ssh.py "<command>"` (vault-managed root credential or SSH key, Dropbear SSH)
- **Peripherals:** JetKVM @ 192.168.1.80 (working)
- **Role:** NFS storage, media services, monitoring stack, Home Assistant

## Motherboard: ASUS ProArt X870E-CREATOR WIFI

**[Full specifications](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)**

### CPU Socket
- **Socket:** AM5 (LGA 1718)
- **Installed:** AMD Ryzen 9 9950X (16 cores, 32 threads)
  - Base: 4.3 GHz, Boost: 5.7 GHz
  - TDP: 170W (running at ~140W, 82% TDP)
  - 64 MB L3 cache
  - PCIe 5.0, 28 lanes

### Memory Slots (4× DDR5 UDIMM, Dual Channel)
```
DIMM A1: Micron 32GB DDR5 5600 MT/s CL40        [POPULATED]
DIMM A2: Micron 32GB DDR5 5600 MT/s CL40        [POPULATED]
DIMM B1: Micron 32GB DDR5 5600 MT/s CL40        [POPULATED]
DIMM B2: Micron 32GB DDR5 5600 MT/s CL40        [POPULATED]

Total Installed: 128 GB DDR5 (4× 32GB)
Current Speed: 5600 MT/s
Max Capacity: 192 GB (4× 48GB UDIMMs, AM5 limit)

Note: X870E supports standard DDR5 UDIMMs (not RDIMM/ECC)
```

### PCIe Expansion Slots
```
PCIE1 [Gen5 x16]: Intel Arc A380 6GB              [POPULATED]
                  128 Gbps bandwidth
                  Low-profile single-slot card
                  Power: 75W (from slot, no external power)
                  Current use: Plex hardware transcoding (AV1, HEVC)

PCIE2 [Gen5 x16]: Broadcom SAS3224 HBA           [POPULATED]
                  128 Gbps bandwidth (slot capable)
                  Actually uses PCIe 3.0 x8 (card limitation)
                  Manages 10× HDDs (184 TB array)
                  No power connectors (powered via slot)

PCIE3 [Gen4 x4]:  ASUS Hyper M.2 X16 Gen5        [POPULATED]
                  32 Gbps bandwidth (slot limited to x4)
                  Hosts 4× Crucial P310 1TB NVMe drives
                  Total: 4 TB NVMe via this adapter

ALL SLOTS OCCUPIED - No PCIe expansion available without removing something
```

### M.2 NVMe Slots (4× onboard, all populated)
```
M.2_1 [Gen5 x4]: Samsung 990 EVO Plus 1TB        [POPULATED]
                 32 Gbps bandwidth
                 Unraid USB boot (USB stick) + Docker appdata

M.2_2 [Gen5 x4]: Samsung 990 EVO Plus 1TB        [POPULATED]
                 32 Gbps bandwidth
                 Cache pool member 1

M.2_3 [Gen4 x4]: Samsung 990 EVO Plus 1TB        [POPULATED]
                 16 Gbps bandwidth
                 Cache pool member 2

M.2_4 [Gen4 x4]: Samsung 990 EVO Plus 1TB        [POPULATED]
                 16 Gbps bandwidth
                 Cache pool member 3

Total: 4 TB NVMe onboard (all slots used)

Note: M.2_2 shares bandwidth with PCIEX16_2 slot (both used, runs x8/x4 split)
```

### SATA Ports (via Broadcom SAS3224 HBA)
```
HDD Array (10× HDDs via SAS HBA, Unraid managed):

Parity Disk:
  WD Red Pro 22TB (WD221KFGX)                    7,200 RPM, 512 MB cache

Data Disks:
  Disk 1:  Seagate IronWolf 16TB                 7,200 RPM, 256 MB cache
  Disk 2:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 3:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 4:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 5:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 6:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 7:  WD Red Pro 18TB                       7,200 RPM, 512 MB cache
  Disk 8:  Seagate IronWolf 16TB                 7,200 RPM, 256 MB cache
  Disk 9:  WD Red Pro 22TB                       7,200 RPM, 512 MB cache

Total Raw:     184 TB (10 disks)
Parity:        22 TB (1 disk)
Usable:        164 TB (after parity)

Unraid Array Mounts:
  /mnt/user/data      → 22 TB share (media, downloads, bulk storage)
  /mnt/user/models    → 22 TB share (AI models, checkpoints)
  /mnt/user/appdata   → Docker persistent volumes
  /mnt/user/system    → System backups, configs
```

### Network Interfaces
```
eth0 (Aquantia AQC113CS): 5GbE RJ45             [ACTIVE - 192.168.1.203]
                          Currently on USW Pro 24 PoE (1GbE switch)
                          Target: USW Pro XG 10 PoE (5GbE switch)

eth1 (Realtek RTL8125):   2.5GbE RJ45            [AVAILABLE]

WiFi 7 (802.11be):        WiFi 7 wireless        [AVAILABLE]

2× USB4 Type-C:           40 Gbps each           [AVAILABLE]
```

### USB Ports
```
Rear:  8× USB 3.2 Gen2 (10 Gbps)
       2× USB4 Type-C (40 Gbps)
Front: Via case headers
Total: 10+ USB ports
```

### Power Supply: Unknown (adequate for load)
```
Estimated Load:
  Ryzen 9950X:      140W (82% of 170W TDP)
  Arc A380:          75W
  10× HDDs:          80W (8W each spinning)
  Motherboard:       30W
  RAM (128 GB):      15W
  8× NVMe:           50W (6-7W each)
  SAS HBA:           20W
  Fans:              20W
  ─────────────────────
  TOTAL:           ~430W

Recommended PSU: 650W+ (gives headroom for drive spinup, future expansion)
```

### Storage Summary
```
NVMe:             8 TB (4 TB onboard + 4 TB via Hyper M.2 adapter)
HDD Array:        164 TB usable (184 TB raw, 1-disk parity)
Total:            172 TB

NFS Exports:
  /mnt/user/data      → Node 1:/mnt/vault/data, Node 2:/mnt/vault/data
  /mnt/user/models    → Node 1:/mnt/vault/models, Node 2:/mnt/vault/models
  /mnt/user/appdata   → Node 1:/mnt/vault/appdata, Node 2:/mnt/vault/appdata
```

### Services Running (12+ containers on Unraid)
```
Monitoring Stack:
  - Prometheus (port 9090): Metrics collection from Node 1 + Node 2
  - Grafana (port 3000): Visualization, dashboards, alerts

Media Stack:
  - Plex (port 32400): Media server, Arc A380 transcoding
  - Sonarr (port 8989): TV show management
  - Radarr (port 7878): Movie management
  - Prowlarr (port 9696): Indexer management
  - SABnzbd (port 8080): Usenet downloader
  - Tautulli (port 8181): Plex activity tracking
  - Stash (port 9999): Media organization

Home Automation:
  - Home Assistant (port 8123): NOT ONBOARDED (needs browser setup)

Planned:
  - qBittorrent + Gluetun (VPN): Awaiting NordVPN credentials
```

### Available Expansion Options
```
NONE - All PCIe and M.2 slots occupied

To add expansion:
1. Remove Hyper M.2 adapter from PCIE3
   - Loses 4 TB NVMe (4× P310 drives)
   - Opens 1× Gen4 x4 slot
   - Could add: 5GbE NIC (redundant), other utility card

2. Upgrade to larger HDDs
   - Replace 16TB/18TB drives with 22TB+ drives
   - Gradual expansion without adding slots

3. Add external DAS (Direct Attached Storage)
   - Via USB 3.2 or USB4
   - Not ideal for Unraid array (needs HBA connection)
```

---

# DEV "Workstation" - Complete Hardware Map

## Physical Information
- **Location:** Desktop tower (not rack-mounted)
- **IP Address:** 192.168.1.215 (Intel 2.5GbE eth0)
- **SSH Access:** `ssh shaun@192.168.1.215` (assumed)
- **Role:** Development, testing, desktop use, local builds

## Motherboard: Gigabyte Z690 AORUS ULTRA

**[Full specifications](https://www.gigabyte.com/Motherboard/Z690-AORUS-ULTRA-rev-1x/sp)**

### CPU Socket
- **Socket:** LGA 1700
- **Installed:** Intel Core i7-13700K (16 cores, 24 threads)
  - P-cores: 8× (up to 5.4 GHz)
  - E-cores: 8× (up to 4.2 GHz)
  - Base: 3.4 GHz
  - TDP: 253W (PL2), 125W (PL1)
  - 30 MB L3 cache
  - PCIe 5.0, 20 lanes (16+4)

### Memory Slots (4× DDR5 UDIMM, Dual Channel)
```
DIMM A1: G.Skill 32GB DDR5 5200 CL36             [POPULATED]
DIMM A2: EMPTY                                    [AVAILABLE]
DIMM B1: G.Skill 32GB DDR5 5200 CL36             [POPULATED]
DIMM B2: EMPTY                                    [AVAILABLE]

Total Installed: 64 GB DDR5 (2× 32GB)
Current Speed: 5200 MT/s
Max Capacity: 128 GB (4× 32GB, Z690 limit for stability)

Upgrade Path:
  - Add 2× G.Skill Ripjaws S5 32GB DDR5 5600 (from loose inventory)
  - Total: 128 GB DDR5
  - Cost: $0 (already owned)
```

### PCIe Expansion Slots
```
PCIE1 [Gen5 x16]: ASUS Hyper M.2 X16 Gen5        [POPULATED]
                  128 Gbps bandwidth
                  1× Crucial T700 1TB Gen5 NVMe (12,400/11,800 MB/s)
                  Ports 2-4: EMPTY (available for future Gen5 NVMe)
                  Use: OS, active workspace, Docker hot cache
                  Note: Only T700 benefits from Gen5 - Gen4 drives
                        perform identically in M.2 slots (lower latency)

PCIE2 [Gen3 x16]: ASUS ROG STRIX RX 5700 XT 8GB  [POPULATED]
                  Runs at Gen3 x4 (slot keyed x16, wired x4)
                  32 Gbps bandwidth (4 GB/s)
                  AMD Radeon RX 5700 XT
                  VRAM: 8 GB GDDR6
                  Power: 225W (2× 8-pin connectors)
                  Compute: 9.8 TFLOPS FP32, 40 CUs
                  Current use: Primary display, 3-monitor desktop
                  Performance: Zero impact for desktop workload
                               (research confirmed Gen3 x4 adequate)

PCIE3 [Gen3 x4]:  EMPTY                          [AVAILABLE]
                  32 Gbps bandwidth
                  Candidates: 5GbE NIC
                            Sound card, capture card
                            Expansion cards

Note: GPU moved to Slot 2 to free Slot 1 for Gen5 NVMe storage
      Gen3 x4 bandwidth (4 GB/s) is 8× more than desktop workload needs
```

### M.2 NVMe Slots
```
Z690 AORUS ULTRA configuration (4× Gen4 x4 slots):

  M.2_1 [Gen4 x4]: Crucial P3 Plus 4TB Gen4      [POPULATED]
                   8 GB/s bandwidth
                   CPU-attached, lowest latency (~1-2 µs)
                   Performance: 7,400/6,400 MB/s
                   Use: Docker data, git repos, builds

  M.2_2 [Gen4 x4]: Crucial P310 2TB Gen4         [POPULATED]
                   8 GB/s bandwidth
                   CPU-attached, low latency (~1-2 µs)
                   Performance: 7,100/6,000 MB/s
                   Use: Projects, cache, scratch space

  M.2_3 [Gen4 x4]: EMPTY                         [AVAILABLE]
                   8 GB/s bandwidth
                   Chipset-attached (~2-3 µs latency)
                   Future expansion

  M.2_4 [Gen4 x4 or SATA]: EMPTY                 [AVAILABLE]
                           Chipset-attached
                           Shares lanes with SATA ports 2/3
                           Future expansion

Total Motherboard NVMe: 6 TB (all Gen4, CPU-attached)
Total System NVMe: 7 TB (1 TB Gen5 in PCIe Slot 1 + 6 TB Gen4 in M.2)
Expansion: 2 M.2 slots + 3 Hyper M.2 ports available
```

### SATA Ports (6× SATA III 6Gb/s)
```
SATA 0: Unknown                                  [UNKNOWN STATUS]
SATA 1: Unknown                                  [UNKNOWN STATUS]
SATA 2: AVAILABLE (unless M.2_4 occupied)        [LIKELY AVAILABLE]
SATA 3: AVAILABLE (unless M.2_4 occupied)        [LIKELY AVAILABLE]
SATA 4: Unknown                                  [UNKNOWN STATUS]
SATA 5: Unknown                                  [UNKNOWN STATUS]

Note: SATA ports 2/3 share bandwidth with M.2_4 slot
      If M.2_4 is populated, SATA 2/3 are disabled

Planned Addition (3× 2.5" SATA SSDs):
  - Samsung 870 EVO 2TB (primary OS/apps, fastest)
  - Samsung 860 QVO 2TB (project files, bulk storage)
  - Lexar NS100 1TB (scratch/temp)
  Total: 5 TB SATA SSD storage
```

### Network Interfaces
```
eth0 (Intel I225-V): 2.5GbE RJ45                 [ACTIVE - 192.168.1.215]
                     Currently on USW Pro 24 PoE (1GbE switch)

WiFi 6E (AX210):     WiFi 6E wireless            [AVAILABLE]

Upgrade Option:
  - Add Intel X540-T2 or SR-PT02-X540 5GbE NIC to PCIE2/3
  - Connect to USW Pro XG 10 PoE (5GbE switch)
  - Cost: $0 (3 cards, 6 ports available in loose inventory)
```

### USB Ports (per Z690 AORUS ULTRA specs)
```
Rear:  4× USB 3.2 Gen2 (10 Gbps)
       2× USB 3.2 Gen1 (5 Gbps)
       4× USB 2.0
       1× USB 3.2 Gen2x2 Type-C (20 Gbps)

Front: Via case headers (varies by case)

Total: 11+ USB ports on rear I/O
```

### Power Supply: Unknown
```
Current Load Estimate:
  i7-13700K:        180W (PL2 typical gaming load)
  RX 5700 XT:       225W
  Motherboard:       40W
  RAM (64 GB):       10W
  Storage:           20W (unknown config)
  Fans/RGB:          25W
  ─────────────────────
  TOTAL:           ~500W

Recommended: 750W+ PSU for headroom and efficiency
```

### Storage Summary
```
Current NVMe: 7 TB ✅ ALL CONFIGURED
  PCIe Slot 1 (Hyper M.2):
    - Crucial T700 1TB Gen5 → 12,400 MB/s (OS, hot workspace, Docker cache)

  Motherboard M.2 Slots:
    - M.2_1: Crucial P3 Plus 4TB Gen4 → 7,400 MB/s (Docker, repos, builds)
    - M.2_2: Crucial P310 2TB Gen4 → 7,100 MB/s (projects, cache, scratch)

Performance Tier Summary:
  - Tier 1 (Gen5): 1 TB @ 12,400 MB/s - Interactive work
  - Tier 2 (Gen4): 6 TB @ 7,100-7,400 MB/s - Development assets
  - Total: 7 TB all-fast storage

Available Expansion:
  - Hyper M.2 Ports 2-4: 3 empty (for future Gen5 NVMe)
  - M.2_3 and M.2_4: 2 empty (for future Gen4 NVMe or SATA)
  - SATA: 6 ports available (for 2.5" SSDs if needed)

Loose Spares:
  - Samsung 970 EVO Plus 1TB Gen3
  - WD Black SN750 1TB Gen3
  - Samsung 970 EVO 250GB Gen3

Network Storage:
  - VAULT NFS shares accessible at 1GbE (future 5GbE)
  - /mnt/vault/models, /mnt/vault/data, /mnt/vault/appdata
```

### GPU Configuration Detail
```
Current: AMD Radeon RX 5700 XT 8GB
  - VRAM: 8 GB GDDR6
  - Bandwidth: 448 GB/s
  - Compute: 9.8 TFLOPS FP32, 40 CUs (2,560 cores)
  - Power: 225W (2× 8-pin)
  - Architecture: RDNA 1.0
  - Use: Primary display, desktop GPU, light gaming
  - Encoding: H.264/H.265 (VCN 2.0)
  - No tensor cores (AMD doesn't have dedicated AI cores in RDNA 1.0)

Potential Addition: NVIDIA RTX 3060 12GB
  - VRAM: 12 GB GDDR6
  - Compute: 13 TFLOPS FP32, 3,584 CUDA cores
  - Tensor Cores: 112 (Gen 3)
  - Power: 170W
  - Use: CUDA development, local AI training, secondary inference
  - Note: PCIE2 runs at Gen3 x4 (limits bandwidth to 4 GB/s)
  - Recommendation: Put RTX 3060 in Node 2 Slot 3 instead (full Gen5 x16)
```

### Services Running
```
LOCAL ONLY - Not managed by Athanor infrastructure

Likely:
  - Windows 11 or Linux desktop environment
  - Development tools (VS Code, IDEs)
  - Docker Desktop (local containers)
  - Web browsers, communication tools

Potential Future:
  - Local LLM inference (if RTX 3060 added, but better on Node 2)
  - AI development/testing
  - Video editing with GPU acceleration
```

### Available Expansion Options
```
1. Storage Expansion (IMMEDIATE - $0)
   - Add 3× 2.5" SATA SSDs (5 TB total)
   - Samsung 870 EVO 2TB → SATA port 0 (OS/apps)
   - Samsung 860 QVO 2TB → SATA port 1 (bulk)
   - Lexar NS100 1TB → SATA port 4 (scratch)
   - Action: Install drives, format, mount

2. RAM Upgrade (IMMEDIATE - $0)
   - Add 2× G.Skill Ripjaws S5 32GB DDR5 5600
   - Slots: DIMM A2, DIMM B2
   - Total: 128 GB DDR5
   - Use: Large datasets, VMs, Docker builds
   - Cost: $0 (already owned)

3. 5GbE Networking (EASY - $0)
   - Add Intel X540-T2 or SR-PT02-X540 to PCIE2 or PCIE3
   - Connect to USW Pro XG 10 PoE
   - Bandwidth: 10 Gbps to Node 1/Node 2/VAULT
   - Cost: $0 (already owned)

4. NVMe Expansion (if M.2 slots available)
   - Audit current M.2 usage first
   - Add loose NVMe drives to available slots
   - OR: Add Hyper M.2 adapter to PCIE2 (+4 NVMe drives)

Priority Recommendation:
  1. Add 3× SATA SSDs (5 TB storage boost)
  2. Add 2× DDR5 32GB (→ 128 GB RAM)
  3. Optional: Add 5GbE NIC if frequent large file transfers to cluster
```

---

# Network Topology - Complete Interconnection Map

```
                    ┌──────────────────────────────────────┐
                    │   UniFi Dream Machine Pro (Gateway)  │
                    │          192.168.1.1                 │
                    │   Routing, Firewall, DHCP, DNS       │
                    └───────────────┬──────────────────────┘
                                    │
                                    │ 1GbE Uplink
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        │                           │                           │
┌───────▼────────┐      ┌───────────▼──────────┐    ┌──────────▼─────────┐
│ USW Pro 24 PoE │      │   Lutron Controller  │    │     JetKVMs        │
│  1GbE Switch   │      │    192.168.1.158     │    │  .80 (VAULT)       │
│ (MANAGEMENT)   │      │  Caseta wireless     │    │  .165 (Node 2)     │
│                │      └──────────────────────┘    └────────────────────┘
│ 24× 1GbE ports │
│ Currently:     │
│ - Node 1 eth0  │  .244  ┐
│ - Node 1 eth1  │  .246  │  BOTH 5GbE interfaces bottlenecked at 1GbE!
│ - Node 2 eth0  │  .225  │  Need to move to USW Pro XG 10 PoE
│ - VAULT eth0   │  .203  │
│ - DEV eth0     │  .215  ┘
└────────────────┘

        ┌──────────────────────────────────────────────────┐
        │         USW Pro XG 10 PoE (AVAILABLE)            │
        │          5GbE Data Plane                        │
        │      8× 5GbE SFP+, 4× 5GbE RJ45               │
        │                                                  │
        │  TARGET MIGRATION:                               │
        │    - Node 1 eth0/eth1 → 5GbE (dual 10G)        │
        │    - Node 2 eth0 → 5GbE                         │
        │    - VAULT eth0 → 5GbE                          │
        │    - Optional: DEV eth0 via 5GbE NIC            │
        │                                                  │
        │  BENEFITS:                                       │
        │    - NFS performance: 125 MB/s → 1,250 MB/s     │
        │    - Model downloads 10× faster                  │
        │    - vLLM distributed inference support          │
        └──────────────────────────────────────────────────┘

CURRENT STATE: All nodes on 1GbE management switch
ACTION REQUIRED: Move ethernet cables to 5GbE switch (5 min physical task)
```

## NFS Storage Flows (Current: 1GbE, Target: 5GbE)

```
                    ┌─────────────────────────────────────┐
                    │  VAULT (.203) - Storage Server      │
                    │  Unraid NFS Exports:                │
                    │    /mnt/user/data      (22 TB)      │
                    │    /mnt/user/models    (22 TB)      │
                    │    /mnt/user/appdata               │
                    └──────────┬──────────────────────────┘
                               │
                               │ 5GbE (currently limited to 1GbE!)
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼────────┐  ┌──────▼──────┐   ┌──────▼──────┐
    │  Node 1 (.244) │  │ Node 2(.225)│   │  DEV (.215) │
    │ /mnt/vault/    │  │/mnt/vault/  │   │ (no mounts) │
    │   models       │  │  models     │   │             │
    │   data         │  │  data       │   │             │
    │   appdata      │  │  appdata    │   │             │
    └────────────────┘  └─────────────┘   └─────────────┘

READ PATTERNS:
  - vLLM model loading: Node 1 ← VAULT models (15.6 GB Qwen3-32B-AWQ)
  - ComfyUI model loading: Node 2 ← VAULT models (17 GB Flux + encoders)
  - Agent workspace: Node 1 ← VAULT data

WRITE PATTERNS:
  - ComfyUI output: Node 2 → VAULT data/comfyui/output
  - Download completion: VAULT → local HDD array → NFS share

BOTTLENECK: 1GbE = 125 MB/s max (shared across all NFS traffic)
TARGET: 5GbE = 1,250 MB/s (10× faster, dedicated bandwidth per node)
```

## Service Dependencies & Data Flows

```
┌──────────────────────────────────────────────────────────────────────┐
│                     CLIENT / BROWSER LAYER                           │
│  https://athanor.local/     →  Athanor Command Center               │
│  http://192.168.1.225:3000  →  Open WebUI (chat frontend)           │
│  http://192.168.1.225:8188  →  ComfyUI (Flux image gen)             │
│  http://192.168.1.203:3000  →  Grafana (monitoring)                 │
│  http://192.168.1.203:32400 →  Plex (media streaming)               │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│              NODE 2 "Workshop" - Interface Layer (.225)              │
│                                                                      │
│  Command Center    ─────┐                                           │
│  Open WebUI (3000) ─────┼──→  HTTP API calls                        │
│                         │     to Node 1 vLLM                         │
│                         │                                            │
│  ComfyUI (8188) ────────┼──→  RTX 5090 (Flux FP8)                   │
│    - Reads models from VAULT NFS                                    │
│    - Writes output to VAULT NFS                                     │
│                         │                                            │
│  vLLM (8000) ───────────┘──→  RTX 5060 Ti (Qwen3-14B)               │
│    - Tool calling, low traffic                                      │
│    - Reads models from VAULT NFS                                    │
│                                                                      │
│  Monitoring:                                                         │
│    - node_exporter (9100) ──→ Prometheus (VAULT)                    │
│    - dcgm-exporter (9400) ──→ Prometheus (VAULT)                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼  HTTP API calls
┌──────────────────────────────────────────────────────────────────────┐
│              NODE 1 "Foundry" - Core Inference (.244)                │
│                                                                      │
│  vLLM (8000) ←────────── Dashboard, Open WebUI, Agent Server        │
│    Model: Qwen3-32B-AWQ                                             │
│    Backend: TP=4 across 4× RTX 5070 Ti (64 GB pooled)               │
│    Performance: ~120 tok/s                                           │
│    Reads models from VAULT NFS                                      │
│                                                                      │
│  RTX 4090 (Slot 1): IDLE ─→ Available for workload                  │
│                                                                      │
│  Agent Server (9000) ←───── API clients                              │
│    - Calls vLLM localhost:8000 for inference                        │
│    - Tools: Sonarr, Radarr, Tautulli (VAULT services)               │
│    - Tools: GPU metrics, service health                             │
│                                                                      │
│  Monitoring:                                                         │
│    - node_exporter (9100) ──→ Prometheus (VAULT)                    │
│    - dcgm-exporter (9400) ──→ Prometheus (VAULT)                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼  Service queries, metrics scraping
┌──────────────────────────────────────────────────────────────────────┐
│              VAULT "Storage" - Services Layer (.203)                 │
│                                                                      │
│  Prometheus (9090) ←──── Scrapes Node 1 + Node 2 metrics            │
│    - node_exporter from both nodes                                  │
│    - dcgm-exporter from both nodes                                  │
│    - Retention: 15 days                                             │
│                                                                      │
│  Grafana (3000) ←──────── Queries Prometheus                        │
│    - DCGM GPU Dashboard (#12239)                                    │
│    - Node Exporter Dashboard (#1860)                                │
│    - Athanor Overview Dashboard (custom)                            │
│                                                                      │
│  Media Stack:                                                        │
│    Prowlarr (9696) ──→ Indexers ──→ Results                         │
│    Sonarr (8989) ────→ Prowlarr ──→ SABnzbd (8080)                  │
│    Radarr (7878) ────→ Prowlarr ──→ SABnzbd (8080)                  │
│    SABnzbd ──→ Downloads ──→ /mnt/user/data/usenet/                 │
│    Completed ──→ /mnt/user/data/media/{tv,movies}/                  │
│    Plex (32400) ──→ Scans /mnt/user/data/media/ ──→ Streaming       │
│    Tautulli (8181) ──→ Monitors Plex activity                       │
│                                                                      │
│  Home Assistant (8123): Deployed, NOT ONBOARDED                     │
│    - Awaiting browser setup at http://192.168.1.203:8123            │
│                                                                      │
│  NFS Server:                                                         │
│    - Exports /mnt/user/{data,models,appdata} to Node 1 + Node 2     │
│    - 164 TB usable (10× HDDs, single parity)                        │
│    - 8 TB NVMe cache                                                │
└──────────────────────────────────────────────────────────────────────┘

DEV (.215): Local development only, no managed services
```

---

# Power Budget Analysis - All Systems

```
┌────────────────────────────────────────────────────────────────────┐
│  NODE 1 (.244) - MSI MEG Ai1600T 1600W PSU                         │
├────────────────────────────────────────────────────────────────────┤
│  EPYC 7663:          180W  (75% of 240W TDP)                       │
│  RTX 4090:           320W  (optimized from 450W stock)             │
│  4× RTX 5070 Ti:     960W  (240W each, optimized from 300W)       │
│  Motherboard:         40W                                          │
│  RAM (224 GB):        20W                                          │
│  2× NVMe:             10W                                          │
│  Fans:                10W                                          │
│  ──────────────────────────                                        │
│  TOTAL:            1,520W  (95% utilization, 80W headroom)         │
│                                                                    │
│  STATUS: At PSU limit - cannot add RTX 3060 without dual PSU      │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  NODE 2 (.225) - MSI 1600W PSU                                     │
├────────────────────────────────────────────────────────────────────┤
│  TR 7960X:           245W  (70% of 350W TDP)                       │
│  RTX 5090:           420W  (optimized from 575W stock)             │
│  RTX 5060 Ti:        200W  (optimized from 300W stock)             │
│  Motherboard:         60W                                          │
│  RAM (128 GB):        20W                                          │
│  4× Gen5 NVMe:        25W                                          │
│  Fans:                10W                                          │
│  ──────────────────────────                                        │
│  CURRENT:            980W  (61% utilization, 620W headroom)        │
│                                                                    │
│  WITH RTX 3060 ADDED:                                              │
│  + RTX 3060:         170W  (at stock TDP)                          │
│  ──────────────────────────                                        │
│  NEW TOTAL:        1,150W  (72% utilization, 450W headroom)        │
│                                                                    │
│  STATUS: RTX 3060 fits easily! 450W headroom remaining             │
│  RECOMMENDATION: Add RTX 3060 to Slot 3 (PCIe 5.0 x16)             │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  VAULT (.203) - Unknown PSU (estimated ~650W)                      │
├────────────────────────────────────────────────────────────────────┤
│  Ryzen 9950X:        140W  (82% of 170W TDP)                       │
│  Arc A380:            75W                                          │
│  10× HDDs:            80W  (8W each spinning)                      │
│  Motherboard:         30W                                          │
│  RAM (128 GB):        15W                                          │
│  8× NVMe:             50W  (6-7W each)                             │
│  SAS HBA:             20W                                          │
│  Fans:                20W                                          │
│  ──────────────────────────                                        │
│  TOTAL:              430W  (~66% of estimated 650W PSU)            │
│                                                                    │
│  STATUS: Adequate headroom for current config                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  DEV (.215) - Unknown PSU (needs audit)                            │
├────────────────────────────────────────────────────────────────────┤
│  i7-13700K:          180W  (gaming load, PL2)                      │
│  RX 5700 XT:         225W                                          │
│  Motherboard:         40W                                          │
│  RAM (64 GB):         10W                                          │
│  Storage:             20W  (unknown config)                        │
│  Fans/RGB:            25W                                          │
│  ──────────────────────────                                        │
│  TOTAL:              500W  (estimated)                             │
│                                                                    │
│  RECOMMENDED PSU: 750W+ for headroom and efficiency                │
└────────────────────────────────────────────────────────────────────┘

TOTAL CLUSTER POWER: 1,520W + 980W + 430W + 500W = 3,430W
WITH RTX 3060 ON NODE 2: 3,600W total
```

---

# RTX 3060 Allocation Recommendation

## Analysis: Node 1 vs Node 2

### Option A: RTX 3060 → Node 1 Slot 6
```
PROS:
  - Co-located with primary vLLM instance
  - Could run secondary model instance

CONS:
  - PSU at 95% (1,520W / 1,600W) - NO HEADROOM
  - Adding 170W → 1,690W (106% of PSU capacity) = EXCEEDS LIMIT
  - Requires dual PSU installation (ASUS ROG 1200W)
  - Requires mining GPU enclosure with risers
  - Deferred to Phase C (hardware reconfiguration)

STATUS: BLOCKED until dual PSU + enclosure installed
```

### Option B: RTX 3060 → Node 2 Slot 3 ✅ **RECOMMENDED**
```
PROS:
  - PSU at 61% (980W / 1,600W) - 620W HEADROOM
  - Adding 170W → 1,150W (72% of PSU capacity) = 450W HEADROOM REMAINS
  - Slot 3 is PCIe 5.0 x16 (full 128 Gbps bandwidth, vs Gen3 x4 on DEV)
  - Immediate installation (no additional hardware required)
  - Node 2 already has vLLM instance (can expand GPU pool)
  - Complements RTX 5090 + 5060 Ti (3-GPU config)
  - Total VRAM: 60 GB (32 + 16 + 12)

CONS:
  - None (optimal placement)

USE CASES:
  - Local AI training/fine-tuning (12 GB VRAM sufficient for LoRA)
  - Secondary vLLM instance (Qwen3-14B or smaller)
  - CUDA development and testing
  - ComfyUI secondary pipeline (while 5090 busy)
  - Parallel inference (3 models simultaneously)

STATUS: READY TO INSTALL
ACTION: Move RTX 3060 from loose inventory → Node 2 Slot 3
```

### Option C: RTX 3060 → DEV Slot 2
```
PROS:
  - Local CUDA development on workstation
  - Separate from cluster infrastructure

CONS:
  - PCIE2 runs at Gen3 x4 (only 4 GB/s bandwidth vs 16 GB/s on x16)
  - Bandwidth bottleneck for GPU-heavy workloads
  - Less useful than on Node 2 (cluster infrastructure)
  - PSU unknown (may need upgrade)

STATUS: SUBOPTIMAL compared to Node 2
```

## Final Recommendation

**Install RTX 3060 12GB in Node 2 Slot 3 (PCIe 5.0 x16)**

### Immediate Benefits:
1. **60 GB total VRAM** on Node 2 (32 + 16 + 12)
2. **450W PSU headroom** remaining
3. **3-GPU flexibility** for parallel workloads
4. **Full Gen5 bandwidth** (128 Gbps, vs 4 GB/s on DEV)
5. **$0 cost** (already owned)

### Installation Steps:
1. Power down Node 2
2. Install RTX 3060 in Slot 3 (bottom PCIe 5.0 x16 slot)
3. Connect power (1× or 2× 8-pin from PSU)
4. Power on, verify nvidia-smi shows 3 GPUs
5. Update vLLM or add secondary service to use GPU 2

---

# Pending Physical Tasks Summary

## Immediate (Rack Session ~30 min)

1. **Move all nodes to 5GbE switch** (5 min)
   - Node 1 eth0 (.244) → USW Pro XG 10 PoE
   - Node 1 eth1 (.246) → USW Pro XG 10 PoE
   - Node 2 eth0 (.225) → USW Pro XG 10 PoE
   - VAULT eth0 (.203) → USW Pro XG 10 PoE
   - Verify network connectivity after move

2. **Reseat Samsung 990 PRO 4TB on Node 1** (10 min)
   - Power down Node 1
   - Remove M.2 heatsink
   - Reseat M.2_2 Samsung 990 PRO 4TB
   - Reinstall heatsink
   - Power on, verify detection in BIOS and `lsblk`

3. **Reconnect JetKVM ATX power cable on Node 2** (2 min)
   - Locate disconnected ATX power cable on Node 2
   - Connect to JetKVM @ .165
   - Test power button control via JetKVM web UI

4. **Enable EXPO in Node 2 BIOS** (5 min)
   - Boot Node 2 into BIOS
   - Enable EXPO profile (DDR5 4800 → 5600 MT/s, +16% speed)
   - Save and reboot
   - Verify: `sudo dmidecode -t memory | grep Speed`

5. **Install RTX 3060 in Node 2 Slot 3** (10 min)
   - Power down Node 2
   - Install RTX 3060 12GB in PCIE3 (bottom slot)
   - Connect 8-pin power (or 2× 8-pin depending on model)
   - Power on
   - Verify: `nvidia-smi` shows 3 GPUs (5090, 5060 Ti, 3060)
   - Update dcgm-exporter config to monitor GPU 2

## DEV Upgrades (Local, ~30 min)

1. **Audit DEV storage configuration**
   - Check M.2 slots: `lsblk -d -o NAME,SIZE,TYPE,TRAN`
   - Check SATA usage: `ls -la /dev/sd*`
   - Document current config

2. **Install 3× 2.5" SATA SSDs in DEV** (15 min)
   - Samsung 870 EVO 2TB → SATA port 0
   - Samsung 860 QVO 2TB → SATA port 1
   - Lexar NS100 1TB → SATA port 4
   - Connect SATA data + power cables
   - Boot, format drives, create mount points

3. **Install 2× DDR5 32GB in DEV** (5 min)
   - G.Skill Ripjaws S5 32GB DDR5 5600 → DIMM A2
   - G.Skill Ripjaws S5 32GB DDR5 5600 → DIMM B2
   - Total: 128 GB DDR5
   - Boot, verify: `free -h`

## Phase C (Deferred - Requires Purchases)

- Purchase mining GPU enclosure (6-8 GPU capacity)
- Purchase 7× PCIe Gen4 riser cables
- Purchase Add2PSU adapter (~$15)
- Install ASUS ROG 1200W PSU as secondary in Node 1
- Move Node 1 GPUs to enclosure with risers
- This enables 6th GPU (RTX 3060) in Node 1

---

**Sources:**
- [ASRock Rack ROMED8-2T](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)
- [Gigabyte Z690 AORUS ULTRA](https://www.gigabyte.com/Motherboard/Z690-AORUS-ULTRA-rev-1x/sp)
- [Gigabyte Z690 AORUS ULTRA Review - Tom's Hardware](https://www.tomshardware.com/reviews/gigabyte-z690-aorus-ultra)
- [ASUS ProArt X870E-CREATOR WIFI](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)
- [Gigabyte TRX50 AERO D](https://www.gigabyte.com/Motherboard/TRX50-AERO-D-rev-1x)

**Document Status:** CURRENT
**Last Updated:** 2026-02-21
**Next Update:** After rack session or hardware audit
