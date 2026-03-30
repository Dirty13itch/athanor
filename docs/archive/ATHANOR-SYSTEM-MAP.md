# Athanor System Map - Complete Hardware Overview

> Atlas note: [`docs/atlas/README.md`](../atlas/README.md) is now the canonical cross-layer system map. This file remains a hardware-focused reference and historical input.

**Last Updated:** 2026-02-21
**Status:** Current (after Node 1 5-GPU installation)

---

## Quick Reference Card

```
CLUSTER RESOURCES:
  CPUs:  200 cores / 404 threads (56C+24C+16C)
  RAM:   480 GB (224 GB ECC DDR4 + 128 GB ECC DDR5 + 128 GB DDR5)
  VRAM:  142 GB across 8 GPUs (88 GB Node 1 + 48 GB Node 2 + 6 GB VAULT)
  NVMe:  19 TB installed (12 TB Node 1 + 7 TB DEV) + 3 TB loose spares
  HDD:   164 TB usable (VAULT Unraid array)

SSH ACCESS:
  Node 1:  ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244
  Node 2:  ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225
  VAULT:   python scripts/vault-ssh.py "<command>"  (vault-managed root credential or SSH key)

CRITICAL SERVICES:
  vLLM (TP=4):     http://192.168.1.244:8000  (Node 1 - Qwen3-32B-AWQ)
  Agent Server:    http://192.168.1.244:9000  (Node 1 - General + Media)
  Dashboard:       http://192.168.1.225:3001  (Node 2)
  ComfyUI:         http://192.168.1.225:8188  (Node 2 - Flux dev FP8)
  Open WebUI:      http://192.168.1.225:3000  (Node 2)
  Grafana:         http://192.168.1.203:3000  (VAULT)
  Home Assistant:  http://192.168.1.203:8123  (VAULT - not onboarded)
```

---

## Visual Rack Layout

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ NODE 1 "Foundry" - Core Inference Cluster                     192.168.1.244/.246 │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Motherboard: ASRock Rack ROMED8-2T (SP3, 7× PCIe 4.0 x16, 2× M.2)               │
│ CPU: AMD EPYC 7663 (56C/112T, 2.0-3.5 GHz, 240W TDP)                             │
│ RAM: 7× Samsung 32GB DDR4 ECC RDIMM 3200 = 224 GB                                │
│                                                                                   │
│ ┌─────────────────────── PCIe SLOTS (7 total) ──────────────────────────┐       │
│ │  Slot 1 [x16 Gen4]: RTX 4090 24GB (12V-2x6 native)         [USED]     │       │
│ │  Slot 2 [x16 Gen4]: RTX 5070 Ti 16GB (12V-2x6 native)      [USED]     │       │
│ │  Slot 3 [x16 Gen4]: RTX 5070 Ti 16GB (adapter 3×8-pin)     [USED]     │       │
│ │  Slot 4 [x16 Gen4]: RTX 5070 Ti 16GB (adapter 3×8-pin)     [USED]     │       │
│ │  Slot 5 [x16 Gen4]: RTX 5070 Ti 16GB (adapter 3×8-pin)     [USED]     │       │
│ │  Slot 6 [x16 Gen4]: Hyper M.2 (4× P310 1TB = 4 TB)         [USED]     │       │
│ │  Slot 7 [x16 Gen4]: Available (InfiniBand/5GbE/storage)   [FREE]     │       │
│ └────────────────────────────────────────────────────────────────────────┘       │
│                                                                                   │
│ ┌─────────────────────── M.2 SLOTS (2 total) ────────────────────────────┐      │
│ │  M.2_1 [Gen4 x4]: Samsung 990 PRO 4TB (not detected!)      [ISSUE]     │      │
│ │  M.2_2 [Gen4 x4]: Samsung 990 PRO 4TB (working)            [USED]      │      │
│ └─────────────────────────────────────────────────────────────────────────┘      │
│                                                                                   │
│ TOTAL VRAM: 88 GB (4×16 GB + 24 GB)   |   TOTAL NVMe: 12 TB (8+4)                │
│ EXPANSION: 1× PCIe slot free (Slot 7) - 2nd Hyper M.2 allocated to DEV          │
│ NETWORK: Dual Intel X550 5GbE (.244/.246) - currently on 1GbE switch            │
│ PSU: MSI MEG Ai1600T PCIE5 (1600W, 95% utilized @ 1,520W)                        │
│                                                                                   │
│ [vLLM TP=4: Qwen3-32B-AWQ] [Agent Server] [node_exporter] [dcgm-exporter]       │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│ NODE 2 "Workshop" - Interface Layer                              192.168.1.225   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Motherboard: Gigabyte TRX50 AERO D (sTR5, 3× PCIe 5.0 x16, 4× M.2)              │
│ CPU: AMD Threadripper 7960X (24C/48T, 4.2-5.6 GHz, 350W TDP)                     │
│ RAM: 4× Kingston 32GB DDR5 ECC RDIMM 5600→4800 = 128 GB (EXPO not enabled!)     │
│                                                                                   │
│ ┌─────────────────────── PCIe SLOTS (3 total) ──────────────────────────┐       │
│ │  Slot 1 [x16 Gen5]: RTX 5090 32GB (12V-2x6 native)         [USED]     │       │
│ │  Slot 2 [x16 Gen5]: RTX 5060 Ti 16GB (12V-2x6 native)      [USED]     │       │
│ │  Slot 3 [x16 Gen5]: EMPTY - Available for expansion        [FREE]     │       │
│ └────────────────────────────────────────────────────────────────────────┘       │
│                                                                                   │
│ ┌─────────────────────── M.2 SLOTS (4 total) ────────────────────────────┐      │
│ │  M.2_1 [Gen5 x4]: Crucial T700 4TB (OS/system)             [USED]      │      │
│ │  M.2_2 [Gen5 x4]: Crucial T700 1TB (Docker)                [USED]      │      │
│ │  M.2_3 [Gen5 x4]: Crucial T700 1TB (Temp/scratch)          [USED]      │      │
│ │  M.2_4 [Gen5 x4]: Crucial T700 1TB (ComfyUI)               [USED]      │      │
│ └─────────────────────────────────────────────────────────────────────────┘      │
│                                                                                   │
│ TOTAL VRAM: 48 GB (32 GB + 16 GB)                                                │
│ EXPANSION: 1× PCIe 5.0 x16 slot available (can add Hyper M.2 Gen5 = 4 drives)   │
│ NETWORK: Marvell 5GbE (.225) + RTL8125 2.5GbE + 2× USB4 40Gbps + WiFi 7        │
│ PSU: MSI 1600W (55% utilized @ 880W)                                             │
│                                                                                   │
│ [ComfyUI: Flux FP8] [Dashboard] [Open WebUI] [node_exporter] [dcgm-exporter]    │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│ DEV "Workstation" - Development & Testing                        192.168.1.215   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Motherboard: Gigabyte Z690 AORUS ULTRA (LGA 1700, ATX)                          │
│ CPU: Intel Core i7-13700K (16C/24T, 3.4-5.4 GHz, 253W TDP)                      │
│ RAM: 2× G.Skill 32GB DDR5 5200 CL36 = 64 GB                                     │
│                                                                                   │
│ ┌─────────────────────── PCIe SLOTS ────────────────────────────────┐           │
│ │  Slot 1 [x16 Gen5]: Hyper M.2 (T700 1TB Gen5 @ 12,400 MB/s)[USED]│           │
│ │  Slot 2 [x4  Gen3]: ASUS ROG STRIX RX 5700 XT 8GB      [USED]    │           │
│ │  Slot 3 [x4  Gen3]: EMPTY - Available                  [FREE]    │           │
│ └───────────────────────────────────────────────────────────────────┘           │
│                                                                                   │
│ ┌─────────────────────── STORAGE ───────────────────────────────────┐           │
│ │  PCIe Slot 1: Hyper M.2 Gen5                                      │           │
│ │    └─ Port 1: T700 1TB Gen5 (12,400 MB/s) - OS/workspace         │           │
│ │    └─ Ports 2-4: Empty (future Gen5 expansion)                   │           │
│ │  M.2_1 [CPU]: P3 Plus 4TB Gen4 (7,400 MB/s) - Docker/repos       │           │
│ │  M.2_2 [CPU]: P310 2TB Gen4 (7,100 MB/s) - projects/cache        │           │
│ │  M.2_3/M.2_4: Empty (future expansion)                            │           │
│ │  SATA: 6× ports available                                         │           │
│ │  TOTAL: 7 TB NVMe (1 TB Gen5 + 6 TB Gen4)                         │           │
│ └───────────────────────────────────────────────────────────────────┘           │
│                                                                                   │
│ NETWORK: Intel I225-V 2.5GbE (.215)   |   GPU: Slot 2 (desktop workload OK)     │
│ PSU: Unknown (adequate for current config)                                       │
│                                                                                   │
│ [Local Development] [Testing] [Desktop Use]                                      │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│ VAULT "Storage" - NFS/Services/Monitoring                        192.168.1.203   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Motherboard: ASUS ProArt X870E-CREATOR WIFI (AM5, 3× PCIe, 4× M.2)              │
│ CPU: AMD Ryzen 9 9950X (16C/32T, 4.3-5.7 GHz, 170W TDP)                          │
│ RAM: 4× Micron 32GB DDR5 5600 = 128 GB                                           │
│                                                                                   │
│ ┌─────────────────────── PCIe SLOTS (3 total) ──────────────────────────┐       │
│ │  Slot 1 [x16 Gen5]: Intel Arc A380 6GB (Plex transcode)    [USED]     │       │
│ │  Slot 2 [x16 Gen5]: Broadcom SAS3224 HBA (10× HDDs)        [USED]     │       │
│ │  Slot 3 [x4  Gen4]: ASUS Hyper M.2 Gen5 (4× P310 1TB)      [USED]     │       │
│ └────────────────────────────────────────────────────────────────────────┘       │
│                                                                                   │
│ ┌─────────────────────── M.2 SLOTS (4 total) ────────────────────────────┐      │
│ │  M.2_1 [Gen5 x4]: Samsung 990 EVO Plus 1TB                 [USED]      │      │
│ │  M.2_2 [Gen5 x4]: Samsung 990 EVO Plus 1TB                 [USED]      │      │
│ │  M.2_3 [Gen4 x4]: Samsung 990 EVO Plus 1TB                 [USED]      │      │
│ │  M.2_4 [Gen4 x4]: Samsung 990 EVO Plus 1TB                 [USED]      │      │
│ └─────────────────────────────────────────────────────────────────────────┘      │
│                                                                                   │
│ ┌──────────────────── STORAGE ARRAY (10× HDDs) ───────────────────────┐         │
│ │  Parity:  1× WD 22TB                                                 │         │
│ │  Data:    1×16TB, 2×18TB, 6×18TB, 1×22TB                            │         │
│ │  Total:   184 TB raw, 164 TB usable (Unraid array)                  │         │
│ └──────────────────────────────────────────────────────────────────────┘         │
│                                                                                   │
│ NFS EXPORTS: /mnt/user/data (22TB), /mnt/user/models (22TB)                      │
│ EXPANSION: All PCIe slots used, all M.2 slots used                               │
│ NETWORK: Aquantia 5GbE (.203) + RTL8125 2.5GbE - currently on 1GbE switch       │
│                                                                                   │
│ [Prometheus] [Grafana] [Plex] [Sonarr] [Radarr] [Prowlarr] [SABnzbd]            │
│ [Tautulli] [Stash] [Home Assistant]                                              │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Hardware Comparison Table

| Component | Node 1 "Foundry" | Node 2 "Workshop" | VAULT "Storage" | DEV "Workstation" |
|-----------|------------------|-------------------|-----------------|-------------------|
| **CPU** | EPYC 7663 (56C/112T) | TR 7960X (24C/48T) | R9 9950X (16C/32T) | i7-13700K (16C/24T) |
| **RAM** | 224 GB DDR4 ECC 3200 | 128 GB DDR5 ECC 5600 | 128 GB DDR5 5600 | 64 GB DDR5 5200 |
| **GPUs** | 5× GPU, 88 GB VRAM | 2× GPU, 48 GB VRAM | 1× GPU, 6 GB VRAM | 1× GPU, 8 GB VRAM |
| | - RTX 4090 24GB | - RTX 5090 32GB | - Arc A380 6GB | - RX 5700 XT 8GB |
| | - 4× RTX 5070 Ti 16GB | - RTX 5060 Ti 16GB | | |
| **PCIe Slots** | 7× Gen4 x16 | 3× Gen5 x16 | 3× (2× Gen5, 1× Gen4) | 3× (1× Gen5, 1× Gen4, 1× Gen3) |
| **Used Slots** | 5 (GPUs) | 2 (GPUs) | 3 (Arc + HBA + Hyper M.2) | 1 (GPU) |
| **Free Slots** | 2× Gen4 x16 | 1× Gen5 x16 | 0 | 2× (1× Gen4 x16, 1× Gen3 x4) |
| **M.2 Slots** | 2× Gen4 x4 | 4× Gen5 x4 | 4× (2× Gen5, 2× Gen4) | Unknown (needs audit) |
| **M.2 Used** | 2 (1 not detected) | 4 (all used) | 4 (all used) | Unknown |
| **M.2 Free** | 0 (1 issue) | 0 | 0 | Unknown |
| **SATA Ports** | — | — | — | 6× available |
| **Storage** | 8 TB NVMe | 7 TB NVMe | 8 TB NVMe + 164 TB HDD | Unknown + 5 TB SATA SSD available |
| **Network** | Dual 5GbE | 5GbE + 2.5GbE + WiFi 7 | 5GbE + 2.5GbE | Intel 2.5GbE |
| **PSU** | MSI 1600W (95% util) | MSI 1600W (55% util) | Unknown (~460W) | Unknown |
| **IP Address** | .244, .246 | .225 | .203 | .215 |
| **SSH** | athanor@.244 | athanor@.225 | root@.203 (Dropbear) | shaun@.215 (assumed) |

---

## Network Topology

```
                    ┌─────────────────────────┐
                    │ UniFi Dream Machine Pro │
                    │      (Gateway .1)       │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
    ┌────────▼────────┐  ┌──────▼──────┐   ┌───────▼────────┐
    │ USW Pro 24 PoE  │  │   Lutron    │   │    JetKVM      │
    │  1GbE Switch    │  │   (.158)    │   │ .80 (VAULT)    │
    │  (Management)   │  └─────────────┘   │ .165 (Node 2)  │
    └────────┬────────┘                    └────────────────┘
             │
     ┌───────┼────────┬──────────┐
     │       │        │          │
  ┌──▼──┐ ┌─▼───┐ ┌──▼───┐  ┌───▼────┐
  │Node1│ │Node2│ │VAULT │  │  DEV   │
  │.244 │ │.225 │ │.203  │  │  .215  │
  │.246 │ │     │ │      │  │        │
  └─────┘ └─────┘ └──────┘  └────────┘

    ┌─────────────────────────────────┐
    │   USW Pro XG 10 PoE             │
    │   5GbE Data Plane (UNUSED)     │
    │   Ready for migration           │
    └─────────────────────────────────┘

CURRENT STATE: All nodes on 1GbE switch
TODO: Move Node 1 (.244/.246), Node 2 (.225), VAULT (.203) to 5GbE switch
```

### NFS Mounts (VAULT → Nodes)

```
VAULT (NFS Server):
  /mnt/user/data    → Node 1: /mnt/vault/data
                    → Node 2: /mnt/vault/data

  /mnt/user/models  → Node 1: /mnt/vault/models
                    → Node 2: /mnt/vault/models

  /mnt/user/appdata → Node 1: /mnt/vault/appdata
                    → Node 2: /mnt/vault/appdata
```

---

## Service Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│  Browser → Dashboard (Node 2:3001) → vLLM API (Node 1:8000)        │
│  Browser → Open WebUI (Node 2:3000) → vLLM API (Node 1:8000)       │
│  Browser → ComfyUI (Node 2:8188) → RTX 5090 (Flux gen)             │
│  API calls → Agent Server (Node 1:9000) → vLLM tool calling        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      INFERENCE LAYER (Node 1)                       │
│  vLLM (port 8000):      Qwen3-32B-AWQ (TP=4, 4× RTX 5070 Ti)       │
│  Agent Server (9000):   General Assistant + Media Agent            │
│  Metrics (9100):        node_exporter → Prometheus                  │
│  GPU Metrics (9400):    dcgm-exporter → Prometheus                  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   INTERFACE LAYER (Node 2)                          │
│  ComfyUI (8188):        Flux dev FP8 on RTX 5090 (32 GB)           │
│  Dashboard (3001):      Next.js monitoring UI                       │
│  Open WebUI (3000):     Chat frontend for vLLM                      │
│  Metrics (9100):        node_exporter → Prometheus                  │
│  GPU Metrics (9400):    dcgm-exporter → Prometheus                  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STORAGE/SERVICES LAYER (VAULT)                     │
│  Monitoring:     Prometheus (9090), Grafana (3000)                  │
│  Media:          Plex (32400), Sonarr (8989), Radarr (7878)        │
│  Downloaders:    Prowlarr (9696), SABnzbd (8080)                   │
│  Tracking:       Tautulli (8181), Stash (9999)                     │
│  Home:           Home Assistant (8123) - not onboarded              │
│  Storage:        NFS exports (models, data, appdata)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. vLLM Inference Flow

```
Dashboard (Node 2) ──┐
Open WebUI (Node 2) ─┼─→ vLLM API (Node 1:8000) ──→ TP=4 Pool
Agent Server (Node 1)─┘                               ├─ RTX 5070 Ti Slot 2
                                                       ├─ RTX 5070 Ti Slot 3
                                                       ├─ RTX 5070 Ti Slot 4
                                                       └─ RTX 5070 Ti Slot 5
                                                       (64 GB VRAM pooled)
```

### 2. NFS Storage Flow

```
VAULT (/mnt/user/models, 22TB)
  │
  ├─→ Node 1 (/mnt/vault/models) ─→ vLLM model cache
  │                                  └─ Qwen3-32B-AWQ (15.6 GB)
  │
  └─→ Node 2 (/mnt/vault/models) ─→ ComfyUI model cache
                                     ├─ Flux dev FP8 (12 GB)
                                     ├─ CLIP-L (1.4 GB)
                                     └─ T5-XXL FP8 (3.8 GB)

VAULT (/mnt/user/data, 22TB)
  │
  ├─→ Node 1 (/mnt/vault/data) ─→ Agent workspace
  └─→ Node 2 (/mnt/vault/data) ─→ ComfyUI output
```

### 3. Monitoring Flow

```
Node 1 ─┬─ node_exporter (9100) ──┐
        └─ dcgm-exporter (9400) ──┤
                                  │
Node 2 ─┬─ node_exporter (9100) ──┼─→ Prometheus (VAULT:9090)
        └─ dcgm-exporter (9400) ──┘           │
                                              ▼
                                       Grafana (VAULT:3000)
                                       ├─ DCGM GPU Dashboard
                                       ├─ Node Exporter Dashboard
                                       └─ Athanor Overview Dashboard
```

### 4. Media Pipeline Flow

```
Prowlarr (VAULT) ──→ Indexers ──→ Search results
                                       │
                                       ▼
Sonarr/Radarr (VAULT) ──→ SABnzbd (VAULT) ──→ /mnt/user/data/usenet/
                                       │
                                       ▼
                              Post-processing ──→ /mnt/user/data/media/
                                       │
                                       ▼
                                  Plex (VAULT) ──→ Streaming
                                       │
                                       ▼
                              Tautulli (VAULT) ──→ Activity tracking
```

---

## Loose Inventory & Compatibility Matrix

### Available CPUs (3 total)

| CPU | Socket | Cores/Threads | TDP | Compatible Systems | Notes |
|-----|--------|---------------|-----|-------------------|-------|
| **Intel i7-12700K** | LGA 1700 | 12C/20T | 190W | Z690 boards (loose) | Alder Lake, DDR5 |
| **Intel i5-12600K** | LGA 1700 | 10C/16T | 150W | Z690 boards (loose) | Alder Lake, DDR5 |
| **Intel i7-9700K** | LGA 1151 | 8C/8T | 95W | Z390/Z370 boards (loose) | Coffee Lake, DDR4 |

### Available GPUs (1 total, 12 GB VRAM)

| GPU | VRAM | TDP | Compatible Nodes | Notes |
|-----|------|-----|------------------|-------|
| **NVIDIA RTX 3060** | 12 GB | 170W | Node 1 Slot 6 or 7, DEV Slot 2 | Node 1: Requires dual PSU. DEV: Immediate fit |

### Available RAM (8 sticks, 256 GB total)

| Type | Capacity | Speed | Quantity | Compatible Systems | Notes |
|------|----------|-------|----------|-------------------|-------|
| **G.Skill Ripjaws S5 DDR5** | 32 GB | 5600 CL40 | 2× | DEV (Z690), loose Z690 boards | +64 GB to DEV possible |
| **Crucial Ballistix DDR4** | 32 GB | 3200 CL16 | 2× | Loose LGA1151 boards | 64 GB kit |
| **G.Skill Ripjaws V DDR4** | 16 GB | 4000 CL18 | 2× | Loose LGA1151 boards | 32 GB kit |
| **G.Skill TridentZ RGB DDR4** | 16 GB | 3200 CL16 | 2× | Loose LGA1151 boards | 32 GB kit |
| **G.Skill TridentZ RGB DDR4** | 8 GB | 3200 CL16 | 2× | Loose LGA1151 boards | 16 GB kit |

### Available 2.5" SATA SSDs (3 total, 5 TB)

| Drive | Capacity | Speed | Interface | Compatible Systems | Recommended Use |
|-------|----------|-------|-----------|-------------------|-----------------|
| **Samsung 870 EVO** | 2 TB | 560/530 MB/s | SATA III | DEV, loose builds | DEV primary storage (fastest) |
| **Samsung 860 QVO** | 2 TB | 550/520 MB/s | SATA III | DEV, loose builds | DEV secondary storage (QLC, good for bulk) |
| **Lexar NS100** | 1 TB | 550/450 MB/s | SATA III | DEV, loose builds | DEV tertiary storage or testing |

**Total: 5 TB SATA SSD storage available for DEV or loose builds**

### Available Motherboards (4 total)

| Motherboard | Socket | Chipset | RAM Support | PCIe Slots | M.2 Slots | Use Case |
|-------------|--------|---------|-------------|------------|-----------|----------|
| **Gigabyte Z690 AORUS ELITE AX DDR4** | LGA 1700 | Z690 | 4× DDR4 | 3× | 4× | Build with i7-12700K/i5-12600K + DDR4 |
| **Gigabyte Z390 AORUS PRO WIFI** | LGA 1151 | Z390 | 4× DDR4 | 3× | 2× | Build with i7-9700K |
| **Gigabyte Z370 AORUS Gaming 5** | LGA 1151 | Z370 | 4× DDR4 | 4× | 2× | Build with i7-9700K |
| **Gigabyte B365M DS3H** | LGA 1151 | B365 | 2× DDR4 | 2× | 1× | Low-end build or testing |

### Available PSUs (4 total)

| PSU | Wattage | Efficiency | Form Factor | Use Case |
|-----|---------|------------|-------------|----------|
| **Corsair SF1000L** | 1000W | 80+ Gold | SFX-L | SFF build or secondary PSU |
| **ASUS ROG** | 1200W | 80+ Platinum | ATX | Node 1 dual PSU (Phase C) |
| **Corsair RM750** | 750W | 80+ Gold | ATX | Mid-range build |
| **EVGA 600B** | 600W | 80+ Bronze | ATX | Low-end build or testing |

### Available Expansion Cards (7 total)

| Card | Type | Ports/Slots | Interface | Use Case |
|------|------|-------------|-----------|----------|
| **Intel X540-T2** | 5GbE NIC | 2× RJ45 | PCIe 2.1 x8 | Add 5GbE to any node |
| **2× SR-PT02-X540** | 5GbE NIC | 2× RJ45 each | PCIe 2.1 x8 | Add 5GbE to any node (6 ports total) |
| **2× ASUS Hyper M.2 X16 Gen5** | NVMe adapter | 4× M.2 each | PCIe 5.0 x16 | Node 1 Slot 6/7, Node 2 Slot 3, DEV Slot 2 |
| **LSI SAS9300-16i** | SAS/SATA HBA | 16× SATA/SAS | PCIe 3.0 x8 | Massive storage expansion |

### Available NVMe Drives (7 drives, 13 TB)

| Drive | Size | Gen | Compatible Slots | Recommended Location |
|-------|------|-----|------------------|----------------------|
| **Crucial T700** | 1 TB | Gen5 | Node 2 Slot 3 (via Hyper M.2), Node 1 Slot 6/7 | Node 2: Add Hyper M.2 to Slot 3 |
| **Crucial P3 Plus** | 4 TB | Gen4 | Node 1 Slot 6/7, Node 2 Slot 3 | Node 1: Add Hyper M.2 to Slot 6 |
| **Crucial P310** | 2 TB | Gen4 | Any Hyper M.2 adapter | Node 1 or Node 2 expansion |
| **4× Crucial P310** | 1 TB each | Gen4 | Any Hyper M.2 adapter | Node 1: Slots 6 & 7 = 8 drives total |
| **Samsung 970 EVO Plus** | 1 TB | Gen3 | Any M.2 or Hyper adapter | Low priority, Gen3 |
| **WD Black SN750** | 1 TB | Gen3 | Any M.2 or Hyper adapter | Low priority, Gen3 |

### Available Hyper M.2 Adapters (2 cards)

| Card | Capacity | Compatible Slots | Best Use |
|------|----------|------------------|----------|
| **2× ASUS Hyper M.2 X16 Gen5** | 4× NVMe each | Node 1 Slots 6 & 7, Node 2 Slot 3 | Node 1: +8 drives = 16 TB<br>Node 2: +4 drives = 4-8 TB |

### NVMe Expansion Scenarios

#### Option A: Node 1 Slot 6 Only (+4 drives)
```
Slot 6: ASUS Hyper M.2 Gen5
  ├─ Crucial P310 2TB
  ├─ Crucial P310 1TB
  ├─ Crucial P310 1TB
  └─ Crucial P310 1TB
Total: +5 TB to Node 1
```

#### Option B: Node 1 Slots 6 & 7 (+8 drives)
```
Slot 6: ASUS Hyper M.2 Gen5        Slot 7: ASUS Hyper M.2 Gen5
  ├─ Crucial P310 2TB                ├─ Crucial P3 Plus 4TB
  ├─ Crucial P310 1TB                ├─ Samsung 970 EVO Plus 1TB
  ├─ Crucial P310 1TB                ├─ WD Black SN750 1TB
  └─ Crucial P310 1TB                └─ [Future drive slot]

Total: +10 TB to Node 1 (or +12 TB with full population)
```

#### Option C: Node 2 Slot 3 (+4 drives)
```
Slot 3: ASUS Hyper M.2 Gen5
  ├─ Crucial T700 1TB Gen5
  ├─ Crucial P310 1TB
  ├─ Crucial P310 1TB
  └─ Crucial P310 1TB
Total: +4 TB to Node 2 (all Gen5/Gen4 fast drives)
```

**Recommendation:** Option B (Node 1 Slots 6 & 7) maximizes local NVMe storage for inference and agent workloads, reducing NFS dependency.

### DEV Upgrade Scenarios

#### Option D1: Storage Expansion Only
```
Add 3× 2.5" SATA SSDs to existing SATA ports:
  - Samsung 870 EVO 2TB (primary OS/apps)
  - Samsung 860 QVO 2TB (bulk storage)
  - Lexar NS100 1TB (scratch/temp)
Total: +5 TB storage
Cost: $0 (already owned)
```

#### Option D2: Storage + GPU Upgrade
```
Move RTX 3060 12GB from loose → DEV Slot 2
Add 3× 2.5" SATA SSDs (5 TB total)
Total: +12 GB VRAM (20 GB total GPU memory)
       +5 TB storage
Use: Local AI testing, CUDA development, dual-GPU workflows
Cost: $0 (already owned)
```

#### Option D3: Storage + RAM Upgrade
```
Add 2× G.Skill Ripjaws S5 32GB DDR5 5600 → 128 GB total
Add 3× 2.5" SATA SSDs (5 TB total)
Total: +64 GB RAM (128 GB total DDR5)
       +5 TB storage
Use: Large dataset work, VM testing, Docker builds
Cost: $0 (already owned)
```

#### Option D4: Full Upgrade (Storage + GPU + RAM)
```
Add RTX 3060 12GB → Slot 2
Add 2× G.Skill Ripjaws S5 32GB DDR5 5600 → 128 GB RAM
Add 3× 2.5" SATA SSDs (5 TB total):
  - Samsung 870 EVO 2TB (OS/apps)
  - Samsung 860 QVO 2TB (project files)
  - Lexar NS100 1TB (scratch)
Total: +12 GB VRAM (20 GB total)
       +64 GB RAM (128 GB total)
       +5 TB storage
Use: Fully equipped dev/test workstation with GPU compute
Cost: $0 (already owned)
```

**Recommendation:** Option D4 (Full Upgrade) maximizes DEV utility as a standalone development node with GPU compute and ample RAM/storage.

---

## Detailed Node Specifications

### Node 1: ASRock Rack ROMED8-2T

**[Specifications from ASRock Rack official docs](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)**

- **Socket:** SP3 (LGA 4094) for AMD EPYC 7003/7002 series
- **PCIe Slots:** [7× PCIe 4.0 x16 slots](https://www.servethehome.com/asrock-rack-romed8-2t-review-an-atx-amd-epyc-platform/) (all from CPU, full x16 lanes each)
  - Note: PCIE2 can run at x8 via jumper (PE8_SEL/PE16_SEL)
- **M.2 Slots:** 2× M.2 (PCIe 4.0 x4 or SATA 6Gb/s)
- **OCuLink:** 2× OCuLink (PCIe 4.0 x4 each)
- **Network:** Dual Intel X550 5GbE (RJ45)
- **RAM:** 8× DDR4 ECC RDIMM slots, supports up to 2TB
- **Form Factor:** ATX (12" × 9.6")
- **Current Usage:**
  - 5× PCIe slots (GPUs)
  - 2× M.2 slots (OS + hot models)
  - 7× DDR4 RDIMM (224 GB, 1 slot empty)

### Node 2: Gigabyte TRX50 AERO D

**[Specifications from ASUS ProArt page](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)** *(Note: This is TRX50 AERO D, not ProArt)*

- **Socket:** sTR5 (LGA 4844) for AMD Threadripper 7000 series
- **PCIe Slots:** 3× PCIe 5.0 x16 (all from CPU, full x16 lanes each)
- **M.2 Slots:** 4× M.2 PCIe 5.0 x4 (onboard)
- **Network:** Marvell AQC113CS 5GbE + Realtek RTL8125 2.5GbE
- **USB:** 2× USB4 Type-C (40 Gbps each)
- **WiFi:** WiFi 7 (802.11be)
- **RAM:** 4× DDR5 RDIMM slots (quad channel, RDIMM-only)
- **Form Factor:** E-ATX
- **Current Usage:**
  - 2× PCIe slots (GPUs)
  - 4× M.2 slots (all used: OS, Docker, scratch, ComfyUI)
  - 4× DDR5 RDIMM (128 GB, all slots full)

### VAULT: ASUS ProArt X870E-CREATOR WIFI

**[Specifications from ASUS official page](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)**

- **Socket:** AM5 (LGA 1718) for AMD Ryzen 9000/7000 series
- **PCIe Slots:**
  - 2× PCIe 5.0 x16 (from CPU) - can run x16 or x8/x8 or x8/x4/x4
  - 1× PCIe 4.0 x16 (from chipset) - runs at x4 mode
- **M.2 Slots:** 4× M.2 (2× Gen5, 2× Gen4)
  - M.2_1: PCIe 5.0 x4 (CPU)
  - M.2_2: PCIe 5.0 x4 (CPU) - shares bandwidth with PCIEX16(G5)_2
  - M.2_3: PCIe 4.0 x4 (Chipset)
  - M.2_4: PCIe 4.0 x4 (Chipset)
- **Network:** Aquantia AQC113CS 5GbE + Realtek RTL8125 2.5GbE
- **WiFi:** WiFi 7 (802.11be)
- **USB:** 2× USB4 Type-C (40 Gbps each)
- **RAM:** 4× DDR5 UDIMM slots (dual channel)
- **Form Factor:** ATX
- **Current Usage:**
  - 3× PCIe slots (Arc A380, SAS HBA, Hyper M.2 Gen5)
  - 4× M.2 slots (all used: 4× Samsung 990 EVO Plus 1TB)
  - 4× DDR5 UDIMM (128 GB, all slots full)

### DEV: Gigabyte Z690 AORUS ULTRA

- **Socket:** LGA 1700 for Intel 12th/13th gen
- **PCIe Slots:**
  - 1× PCIe 5.0 x16 (from CPU)
  - 1× PCIe 4.0 x16 (from CPU) - runs at x4 mode
  - 1× PCIe 3.0 x4 (from chipset)
- **M.2 Slots:** Likely 4× M.2 (needs audit for exact config)
- **SATA Ports:** 6× SATA III 6Gb/s (from chipset)
- **Network:** Intel I225-V 2.5GbE
- **RAM:** 4× DDR5 UDIMM slots (dual channel)
- **Form Factor:** ATX
- **Current Usage:**
  - 1× PCIe slot (RX 5700 XT 8GB)
  - Storage: Unknown (needs audit)
  - 2× DDR5 UDIMM (64 GB, 2 slots available)
- **Expansion Potential:**
  - 2× DDR5 slots available (+64 GB possible with loose RAM)
  - 2× PCIe slots available (RTX 3060, 5GbE NIC, or Hyper M.2)
  - 6× SATA ports available (3× 2.5" SSDs pending install)
  - Unknown M.2 availability (needs audit)

---

## System Integration Notes

### GPU Pooling Strategy
- **Node 1:** 4× RTX 5070 Ti (Slots 2-5) pooled via Tensor Parallelism (TP=4)
  - Combined: 64 GB VRAM, 32K context window
  - Model: Qwen3-32B-AWQ (15.6 GB, replicated 4×)
- **Node 1:** RTX 4090 (Slot 1) available for separate workload
  - 24 GB VRAM, could run Qwen3-14B or tool-calling agent
  - Currently unused (idle GPU)

### Power Budget Analysis
- **Node 1:** 1,520W / 1,600W (95% utilization) - no headroom for RTX 3060
- **Node 2:** 880W / 1,600W (55% utilization) - 720W headroom available
- **VAULT:** ~460W total (adequate PSU)

### Network Performance
- **Current:** All nodes on 1GbE management switch (bottleneck for NFS)
- **Available:** USW Pro XG 10 PoE switch (5GbE ports ready)
- **Upgrade Path:** Move all nodes to 5GbE for 10× faster NFS throughput

### Storage Tiers
1. **Tier 1 (Hot):** Node-local Gen5 NVMe (Node 2: 7 TB, fastest)
2. **Tier 2 (Warm):** Node-local Gen4 NVMe (Node 1: 8 TB, fast)
3. **Tier 3 (Cold):** NFS over 5GbE from VAULT (22 TB models + 22 TB data)
4. **Tier 4 (Archive):** VAULT HDD array (164 TB, media/backups)

---

## Complete Loose Hardware Inventory Summary

### Total Loose Resources Available

```
COMPUTE:
  CPUs:         3× (2× LGA1700, 1× LGA1151)
  GPUs:         1× RTX 3060 12GB
  RAM:          256 GB (128 GB DDR5 + 128 GB DDR4)
  Motherboards: 4× (1× Z690, 1× Z390, 1× Z370, 1× B365M)

STORAGE:
  NVMe Spares:  3 TB (3× Gen3: 970 EVO Plus 1TB, SN750 1TB, 970 EVO 250GB)
  SATA SSD:     5 TB (3× 2.5": 870 EVO 2TB, 860 QVO 2TB, NS100 1TB)
  Total:        8 TB loose storage (down from 18 TB - 10 TB allocated)

NETWORKING:
  5GbE NICs:   3 cards (6× 5GbE RJ45 ports total)

EXPANSION:
  M.2 Adapters: 0 (both used: Node 1 Slot 6 + DEV Slot 1)
  HBAs:         1× LSI SAS9300-16i (16-port SAS/SATA)

POWER:
  PSUs:         4× (1600W equiv: 1200W, 1000W, 750W, 600W)
```

### Quick Allocation Guide

**DEV - ✅ CONFIGURED:**
- PCIe Slot 1: Hyper M.2 with T700 1TB Gen5 (12,400 MB/s)
- PCIe Slot 2: RX 5700 XT GPU (desktop workload)
- M.2_1: P3 Plus 4TB Gen4
- M.2_2: P310 2TB Gen4
- Total: 7 TB NVMe storage
- Expansion: 3× Hyper M.2 ports, 2× M.2 slots, SATA for bulk if needed

**Node 1 - ✅ STORAGE ADEQUATE:**
- Slot 6: Hyper M.2 with 4× P310 1TB (4 TB)
- Onboard: 2× 990 PRO 4TB (8 TB)
- Total: 12 TB (sufficient for model storage)
- Slot 7 available for InfiniBand or future expansion

**Node 2:**
- Slot 3 available for expansion if needed
- Network: Already has 5GbE + 2.5GbE + WiFi 7

**Want to build a new system?**
- Option 1: i7-12700K + Z690 ELITE + 2× DDR4 32GB + RTX 3060 (gaming/dev)
- Option 2: i7-9700K + Z390 PRO + 2× DDR4 32GB (budget build)
- Option 3: i5-12600K + Z690 ELITE + 2× DDR5 32GB (modern budget)

**Want to add storage to VAULT?**
- Use LSI SAS9300-16i HBA → +16 HDDs possible (needs HDDs purchased)
- VAULT already full on PCIe slots (need to remove something first)

---

## Pending Physical Work

### Immediate (Rack Session ~30 min)
- [ ] **Reseat Samsung 990 PRO 4TB** on Node 1 M.2_1 slot (not detected in audit)
- [ ] **Move all nodes to 5GbE switch** (Node 1, Node 2, VAULT)
- [ ] **Reconnect JetKVM ATX power cable** on Node 2 (.165)
- [ ] **Enable EXPO in Node 2 BIOS** (DDR5 4800→5600 MT/s, +16% RAM speed)

### Completed
- [x] **Install Hyper M.2 adapter in Node 1 Slot 6** (4× P310 1TB)
- [x] **Install Hyper M.2 adapter in DEV Slot 1** (T700 1TB Gen5)
- [x] **Install P3 Plus 4TB + P310 2TB in DEV** (M.2_1 + M.2_2)
- [x] **Move RX 5700 XT to DEV Slot 2** (frees Slot 1 for Gen5 storage)

### Phase C: Dual PSU + 6th GPU (After Parts Purchase)
- [ ] Purchase mining enclosure (6-8 GPU capacity)
- [ ] Purchase 7× PCIe Gen4 riser cables
- [ ] Purchase Add2PSU adapter (~$15)
- [ ] Install ASUS ROG 1200W PSU as secondary
- [ ] Move Node 1 GPUs to enclosure with risers
- [ ] Add RTX 3060 12GB to Node 1 (Slot 6, 6th GPU)

---

## Sources

- [ASRock Rack ROMED8-2T Specifications](https://www.asrockrack.com/general/productdetail.asp?Model=ROMED8-2T)
- [ASRock Rack ROMED8-2T Review - ServeTheHome](https://www.servethehome.com/asrock-rack-romed8-2t-review-an-atx-amd-epyc-platform/)
- [ASUS ProArt X870E-CREATOR WIFI Tech Specs](https://www.asus.com/us/motherboards-components/motherboards/proart/proart-x870e-creator-wifi/techspec/)
- [Gigabyte TRX50 AERO D Product Page](https://www.gigabyte.com/Motherboard/TRX50-AERO-D-rev-1x)

---

**Document Status:** CURRENT
**Last Updated:** 2026-02-21 22:00
**Next Update:** After rack session or hardware changes
