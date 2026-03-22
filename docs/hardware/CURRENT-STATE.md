# Athanor Current State - Complete Hardware Map
**Updated:** 2026-02-21 (after Node 1 5-GPU installation)

---

## Node 1 - "Foundry" (192.168.1.244 / .246)

**Role:** Heavy inference cluster, agent serving, TP pooling

```
┌─────────────────────────────────────────────────────────────────┐
│ Silverstone RM52 Upper Tray - 5U Rackmount                      │
│                                                                  │
│ Motherboard: ASRock Rack ROMED8-2T (SP3, 7 PCIe slots)         │
│ CPU: AMD EPYC 7663 (56C/112T, 2.0-3.5 GHz, 240W TDP)           │
│ RAM: 7× Samsung 32GB DDR4 ECC RDIMM 3200 MT/s = 224 GB         │
│                                                                  │
│ GPUs (5 total, 88 GB VRAM):                                     │
│   Slot 1: RTX 4090 24GB (12V-2x6 native)            [24GB]     │
│   Slot 2: RTX 5070 Ti 16GB (12V-2x6 native)         [16GB]     │
│   Slot 3: RTX 5070 Ti 16GB (adapter, 3× 8-pin)      [16GB]     │
│   Slot 4: RTX 5070 Ti 16GB (adapter, 3× 8-pin)      [16GB]     │
│   Slot 5: RTX 5070 Ti 16GB (adapter, 3× 8-pin)      [16GB]     │
│   Slot 6: Empty                                                 │
│   Slot 7: Empty                                                 │
│                                                                  │
│ Storage:                                                         │
│   M.2_1: Crucial P3 4TB Gen3 (OS/system)            [4TB]      │
│   M.2_2: Samsung 990 PRO 4TB Gen4 (hot models)      [4TB]      │
│   NFS: /mnt/vault/models (22 TB array on VAULT)                │
│                                                                  │
│ Network:                                                         │
│   eth0: Intel X550 5GbE (.244) - currently on 1GbE switch     │
│   eth1: Intel X550 5GbE (.246) - currently on 1GbE switch     │
│                                                                  │
│ PSU: MSI MEG Ai1600T PCIE5 (1600W, 80+ Titanium)               │
│   Power Budget: 1,520W optimized (95% utilization)             │
│   - EPYC 7663: 180W (75% TDP)                                  │
│   - RTX 4090: 320W (optimized from 450W)                       │
│   - 4× RTX 5070 Ti: 960W (240W each, optimized from 300W)     │
│   - Motherboard + RAM + NVMe: 60W                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Services Running:**
- vLLM: Qwen3-32B-AWQ (TP=4 on GPUs 1-4, port 8000)
- Agent Server: General Assistant, Media Agent (port 9000)
- node_exporter: Prometheus metrics (port 9100)
- dcgm-exporter: GPU metrics (port 9400)

---

## Node 2 - "Workshop" (192.168.1.225)

**Role:** Interface layer, creative workloads, tool calling

```
┌─────────────────────────────────────────────────────────────────┐
│ Silverstone RM52 Middle Tray - 5U Rackmount                     │
│                                                                  │
│ Motherboard: Gigabyte TRX50 AERO D Rev 1.x (sTR5, E-ATX)       │
│   - 3× PCIe 5.0 x16 slots (full x16 lanes each)                │
│   - 4× M.2 PCIe 5.0 slots (onboard)                            │
│   - 4× DDR5 RDIMM slots (quad channel, RDIMM only)             │
│   - Marvell 5GbE + RTL8125 2.5GbE (dual LAN)                  │
│   - 2× USB4 Type-C (40 Gbps each)                              │
│   - WiFi 7                                                      │
│                                                                  │
│ CPU: AMD Threadripper 7960X (24C/48T, 4.2-5.6 GHz, 350W TDP)   │
│ RAM: 4× Kingston 32GB DDR5 ECC RDIMM 5600→4800 = 128 GB        │
│       (EXPO not enabled, running at 4800 MT/s)                  │
│                                                                  │
│ GPUs (2 total, 48 GB VRAM):                                     │
│   Slot 1: RTX 5090 32GB (12V-2x6 native)            [32GB]     │
│   Slot 2: RTX 5060 Ti 16GB (12V-2x6 native)         [16GB]     │
│                                                                  │
│ Storage (4× M.2 onboard slots):                                 │
│   M.2_1: Crucial T700 4TB Gen5 (OS/system)          [4TB]      │
│   M.2_2: Crucial T700 1TB Gen5 (Docker)             [1TB]      │
│   M.2_3: Crucial T700 1TB Gen5 (Temp/scratch)       [1TB]      │
│   M.2_4: Crucial T700 1TB Gen5 (ComfyUI)            [1TB]      │
│   All M.2 slots used (0 available onboard)                     │
│   NFS: /mnt/vault/data, /mnt/vault/models                      │
│                                                                  │
│ PCIe Slot Usage:                                                │
│   Slot 1: RTX 5090 32GB (PCIe 5.0 x16)              [32GB]     │
│   Slot 2: RTX 5060 Ti 16GB (PCIe 5.0 x16)           [16GB]     │
│   Slot 3: EMPTY (PCIe 5.0 x16 available)                       │
│                                                                  │
│ Network:                                                         │
│   Marvell 5GbE (.225) - currently on 1GbE switch              │
│   RTL8125 2.5GbE - unused                                       │
│   WiFi 7 - unused                                               │
│   2× USB4 Type-C (40 Gbps each) - available                    │
│                                                                  │
│ PSU: MSI 1600W                                                  │
│   Power Budget: 880W optimized (55% utilization)               │
│   - Ryzen 9950X: 140W (82% TDP)                                │
│   - RTX 5090: 420W (optimized from 575W)                       │
│   - RTX 5060 Ti: 200W (optimized from 300W)                    │
│   - Motherboard + RAM + 4× Gen5 NVMe: 120W                     │
│                                                                  │
│ Peripherals:                                                     │
│   JetKVM (.165) - ATX power cable disconnected                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Services Running:**
- ComfyUI: Flux dev FP8 on RTX 5090 (port 8188)
- vLLM: Qwen3-14B-AWQ on RTX 4090 (port 8000) **← GPU MOVED TO NODE 1**
- Open WebUI: Frontend for vLLM (port 3000)
- Dashboard: Next.js monitoring UI (port 3001)
- node_exporter: Prometheus metrics (port 9100)
- dcgm-exporter: GPU metrics (port 9400)

**NOTE:** RTX 4090 was moved from Node 2 to Node 1 during this session.

---

## VAULT - Storage/Services Node (192.168.1.203)

**Role:** NFS storage, media services, monitoring stack

```
┌─────────────────────────────────────────────────────────────────┐
│ Case: Unknown                                                    │
│                                                                  │
│ Motherboard: ASUS ProArt X870E-CREATOR WIFI (AM5, 2 PCIe)      │
│ CPU: AMD Ryzen 9 9950X (16C/32T, 4.3-5.7 GHz, 170W TDP)        │
│ RAM: 4× Micron 32GB DDR5 5600 MT/s CL40 = 128 GB               │
│                                                                  │
│ GPU:                                                             │
│   Slot 1: Intel Arc A380 6GB (Plex transcoding)     [6GB]      │
│                                                                  │
│ PCIe Expansion:                                                  │
│   Slot 2: Broadcom SAS3224 HBA (SAS-3, for HDDs)               │
│   Slot 3: ASUS Hyper M.2 Gen5 (4× P310 1TB NVMe)               │
│                                                                  │
│ Storage:                                                         │
│   M.2 (mobo): 4× Samsung 990 EVO Plus 1TB          [4TB]       │
│   Hyper M.2:  4× Crucial P310 1TB                  [4TB]       │
│   HDDs (SAS): 10× drives, 184TB raw, 164TB usable              │
│     - Parity: WD 22TB                                           │
│     - Data: 1×16TB, 1×18TB, 6×18TB, 1×16TB, 1×18TB, 1×22TB     │
│   Unraid array: /mnt/user/data, /mnt/user/models               │
│                                                                  │
│ Network:                                                         │
│   Aquantia 5GbE (.203) - currently on 1GbE switch             │
│   RTL8125 2.5GbE - management                                   │
│                                                                  │
│ PSU: Unknown (adequate for current load)                        │
│   Power Budget: ~460W                                           │
│   - TR 7960X: 245W (70% TDP)                                   │
│   - Arc A380: 75W                                               │
│   - 10× HDDs: 80W (8W each spinning)                           │
│   - Motherboard + 8× NVMe: 60W                                 │
│                                                                  │
│ Peripherals:                                                     │
│   JetKVM (.80) - connected, working                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Services Running:**
- Unraid OS (storage management)
- Prometheus (port 9090)
- Grafana (port 3000)
- Home Assistant (port 8123, deployed but not onboarded)
- Plex (port 32400, claimed)
- Sonarr (port 8989)
- Radarr (port 7878)
- Prowlarr (port 9696)
- SABnzbd (port 8080)
- Tautulli (port 8181)
- Stash (port 9999)

---

## DEV - Shaun's Workstation (192.168.1.215)

**Role:** Development, testing, desktop use

```
┌─────────────────────────────────────────────────────────────────┐
│ Case: Unknown                                                    │
│                                                                  │
│ Motherboard: Gigabyte Z690 AORUS ULTRA (LGA 1700)              │
│ CPU: Intel Core i7-13700K (16C/24T, 3.4 GHz, 253W TDP)         │
│ RAM: 2× G.Skill 32GB DDR5 5200 CL36 = 64 GB                    │
│                                                                  │
│ GPU:                                                             │
│   Slot 1: ASUS ROG STRIX RX 5700 XT 8GB          [8GB]         │
│                                                                  │
│ Storage: Unknown (assumed local drives)                         │
│                                                                  │
│ PSU: Unknown                                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Services:** Local development only (not managed by Athanor)

---

## Loose Inventory (Available for Reallocation)

### CPUs (3 total)
```
Intel Core i7-12700K    LGA 1700   12C/20T   Alder Lake      190W
Intel Core i5-12600K    LGA 1700   10C/16T   Alder Lake      150W
Intel Core i7-9700K     LGA 1151    8C/8T    Coffee Lake      95W
```

### GPUs (1 total, 12 GB VRAM)
```
NVIDIA RTX 3060         12 GB GDDR6   PCIe 4.0 x16   170W TDP
  (Available for Node 1 Slot 6 when dual PSU installed)
```

### Motherboards (4 total)
```
Gigabyte Z690 AORUS ELITE AX DDR4    LGA 1700   4× DDR4   3 PCIe   4 M.2
Gigabyte Z390 AORUS PRO WIFI          LGA 1151   4× DDR4   3 PCIe   2 M.2
Gigabyte Z370 AORUS Gaming 5          LGA 1151   4× DDR4   4 PCIe   2 M.2
Gigabyte B365M DS3H                   LGA 1151   2× DDR4   2 PCIe   1 M.2
```

### RAM (8 sticks, 256 GB total)
```
DDR5:
  2× G.Skill Ripjaws S5 32GB 5600 CL40              = 64 GB

DDR4:
  2× Crucial Ballistix 32GB 3200 CL16               = 64 GB
  2× G.Skill Ripjaws V 16GB 4000 CL18               = 32 GB
  2× G.Skill TridentZ RGB 16GB 3200 CL16            = 32 GB
  2× G.Skill TridentZ RGB 8GB 3200 CL16             = 16 GB

Total: 128 GB DDR5 + 128 GB DDR4 = 256 GB
```

### NVMe Drives (7 total, 13 TB)
```
Gen5 (1 TB):
  Crucial T700 1TB                                  [1TB]

Gen4 (10 TB):
  Crucial P3 Plus 4TB                               [4TB]
  Crucial P310 2TB                                  [2TB]
  4× Crucial P310 1TB                               [4TB]

Gen3 (2 TB):
  Samsung 970 EVO Plus 1TB                          [1TB]
  WD Black SN750 1TB                                [1TB]
  Samsung 970 EVO 250GB                             [250GB]
```

### PCIe Expansion Cards (7 total)
```
Networking:
  Intel X540-T2 (dual 5GbE RJ45)                   PCIe 2.1 x8
  2× SR-PT02-X540 clone (dual 5GbE RJ45 each)     PCIe 2.1 x8
    Total: 6 ports of 5GbE available

Storage:
  2× ASUS Hyper M.2 X16 Gen5 (4× NVMe each)        PCIe 5.0 x16
  LSI SAS9300-16i (16-port SAS/SATA HBA)           PCIe 3.0 x8
```

### PSUs (4 total)
```
Corsair SF1000L         1000W   80+ Gold      SFX-L
ASUS ROG                1200W   80+ Platinum  ATX  (for dual PSU Phase C)
Corsair RM750           750W    80+ Gold      ATX
EVGA 600B               600W    80+ Bronze    ATX
```

### Miscellaneous
```
Cases: None (all in use or unidentified)
```

---

## Summary Statistics

### Installed Across All Nodes
```
CPUs:        4 (142 cores / 260 threads installed)
GPUs:        9 (154 GB VRAM across all nodes)
  - Node 1:  5 GPUs, 88 GB VRAM
  - Node 2:  2 GPUs, 48 GB VRAM (RTX 4090 moved to Node 1)
  - VAULT:   1 GPU, 6 GB VRAM
  - DEV:     1 GPU, 8 GB VRAM (AMD)
RAM:         544 GB installed (224+128+128+64)
NVMe:        23 TB installed across all nodes
HDDs:        184 TB raw (164 TB usable) on VAULT
```

### Loose/Available
```
CPUs:        3 (Intel, all LGA 1700 or LGA 1151)
GPUs:        1 (RTX 3060 12GB, available for Node 1)
Motherboards: 4 (all Intel-compatible)
RAM:         256 GB (128 GB DDR5 + 128 GB DDR4)
NVMe:        13 TB (1× Gen5, 6× Gen4, 3× Gen3)
5GbE NICs:  3 cards, 6 ports total
PSUs:        4 (1000W SFX-L, 1200W ATX, 750W ATX, 600W ATX)
```

---

## Hardware Moves Completed This Session

1. ✅ **RTX 4090:** Node 2 → Node 1 (Slot 1)
2. ✅ **4× RTX 5070 Ti:** All installed in Node 1 (Slots 2-5)
3. ✅ **Power wiring:** MSI MEG Ai1600T configured with 2× native + 9× PCIe cables
4. ✅ **Power limits:** All GPUs set to optimized levels (320W, 240W×4)

**Net result:**
- Node 1: +5 GPUs (+88 GB VRAM)
- Node 2: -1 GPU (-24 GB VRAM)
- Loose: No change (RTX 3060 still loose)

---

## Pending Physical Work

### Immediate (Rack Session Required)
- [ ] Reseat Samsung 990 PRO 4TB on Node 1 (M.2_2 not detected)
- [ ] Move all nodes to 5GbE switch (USW Pro XG 10 PoE)
- [ ] Reconnect JetKVM ATX power cable on Node 2
- [ ] Enable EXPO in VAULT BIOS (DDR5 4800→5600 MT/s)

### Phase C - Dual PSU Expansion (After Parts Arrive)
- [ ] Purchase mining enclosure (6-8 GPU)
- [ ] Purchase 7× PCIe Gen4 risers
- [ ] Purchase Add2PSU adapter
- [ ] Install ASUS ROG 1200W PSU as secondary
- [ ] Move Node 1 GPUs to enclosure
- [ ] Add RTX 3060 to Node 1 (Slot 6, 6th GPU)

### Future Consideration (TRX50 Swap)
- [ ] Swap TRX50 AERO D from VAULT → Node 2
- [ ] Swap X870E from Node 2 → VAULT
- [ ] Benefit: Node 2 gets 24C/48T CPU (vs current 16C/32T)
- [ ] Trade-off: Node 2 RAM limited to 128 GB ECC (TRX50 has 4 DIMM slots only)

---

**Document Status:** CURRENT
**Last Updated:** 2026-02-21 21:00
**Next Update:** After next hardware change or rack session
