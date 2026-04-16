# Athanor Complete Hardware Inventory

Archived historical owned-hardware ledger.
Current hardware truth is tracked in `config/automation-backbone/hardware-inventory.json`
and the generated `docs/operations/HARDWARE-REPORT.md`.
Keep this file only as detailed owned-hardware history and audit evidence.

Everything Shaun owns that could go into Athanor, listed as a flat parts list.
Treat this as the starting point — as if every node were disassembled and every part
laid on the table. Current node assignments are noted but carry no weight for future
allocation decisions.

Last updated: 2026-02-25. (Corrections from deep hardware audits)

---

## CPUs

| # | CPU | Socket | Cores/Threads | Base/Boost | TDP | Arch | Currently In |
|---|-----|--------|---------------|------------|-----|------|-------------|
| 1 | AMD EPYC 7663 | SP3 | 56C/112T | 2.0/3.54 GHz | 240W | Zen 3 (Milan) | Node 1 |
| 2 | AMD Ryzen 9 9950X | AM5 | 16C/32T | 4.3/5.75 GHz | 170W | Zen 5 | VAULT |
| 3 | AMD Threadripper 7960X | sTR5 | 24C/48T | 4.2/5.665 GHz | 350W | Zen 4 | Node 2 |
| 4 | AMD Ryzen 9 9900X | AM5 | 12C/24T | 4.4/5.6 GHz | 120W | Zen 5 | DEV |
| 5 | Intel Core i7-12700K | LGA 1700 | 12C/20T (8P+4E) | 3.6 GHz | 190W | Alder Lake | Loose |
| 6 | Intel Core i5-12600K | LGA 1700 | 10C/16T (6P+4E) | 3.7 GHz | 150W | Alder Lake | Loose |
| 7 | Intel Core i7-9700K | LGA 1151 | 8C/8T | 3.6 GHz | 95W | Coffee Lake | Loose |

**Total: 7 CPUs, 138 cores / 260 threads**

---

## GPUs

| # | GPU | VRAM | Interface | CUDA Cores | Tensor Cores | Currently In |
|---|-----|------|-----------|------------|-------------|-------------|
| 1 | NVIDIA RTX 5070 Ti (MSI) | 16 GB GDDR7 | PCIe 5.0 x16 | Yes | Yes | Node 1 (Slot 2, TP=4 pool) |
| 2 | NVIDIA RTX 5070 Ti (MSI) | 16 GB GDDR7 | PCIe 5.0 x16 | Yes | Yes | Node 1 (Slot 3, TP=4 pool) |
| 3 | NVIDIA RTX 5070 Ti (Gigabyte) | 16 GB GDDR7 | PCIe 5.0 x16 | Yes | Yes | Node 1 (Slot 4, TP=4 pool) |
| 4 | NVIDIA RTX 5070 Ti (Gigabyte) | 16 GB GDDR7 | PCIe 5.0 x16 | Yes | Yes | Node 1 (Slot 5, TP=4 pool) |
| 5 | NVIDIA RTX 5090 (PNY) | 32 GB GDDR7 | PCIe 5.0 x16 | Yes | Yes | Node 2 (Slot 1, ComfyUI primary) |
| 6 | NVIDIA RTX 4090 (ASUS) | 24 GB GDDR6X | PCIe 4.0 x16 | Yes | Yes | Node 1 (Slot 1, fast agent serving) |
| 7 | NVIDIA RTX 5060 Ti | 16 GB GDDR7 | PCIe 5.0 x8 electrical | Yes | Yes | Node 2 (Slot 2, tool calling) |
| 8 | NVIDIA RTX 3060 | 12 GB GDDR6 | PCIe 4.0 x16 | Yes | Yes | Loose (×2 — one was in DEV before 5060 Ti upgrade) |
| 9 | Intel Arc A380 | 6 GB GDDR6 | PCIe 4.0 x16 | No | No | VAULT (Plex transcoding) |
| 10 | NVIDIA RTX 5060 Ti | 16 GB GDDR7 | PCIe 5.0 x8 electrical | Yes | Yes | DEV (embedding + reranker) |
| 11 | ASUS ROG STRIX RX 5700 XT 8G | 8 GB GDDR6 | PCIe 4.0 x16 | No | No | Loose (was listed as DEV, audit confirmed RTX 3060 instead) |

**Installed NVIDIA VRAM: 152 GB** (8 cards: Node 1 88GB + Node 2 48GB + DEV 16GB) | **Loose NVIDIA: 24 GB** (2x RTX 3060) | **Loose AMD: 8 GB** | **Total all GPU VRAM: 190 GB** (12 cards including loose + A380)

**Note:** DEV upgraded from i7-13700K + RTX 3060 → Ryzen 9 9900X + RTX 5060 Ti (confirmed 2026-03-24). Previous i7-13700K is now loose.

---

## Motherboards

| # | Board | Socket | RAM Type | DIMM Slots | PCIe Slots | M.2 Slots | Onboard Network | Currently In |
|---|-------|--------|----------|------------|------------|-----------|----------------|-------------|
| 1 | ASRock Rack ROMED8-2T | SP3 | DDR4 ECC RDIMM | 8 | 7 (3x x16 + 4x x8) | 2 | 2x Intel X550 5GbE | Node 1 |
| 2 | ASUS ProArt X870E-CREATOR WIFI | AM5 | DDR5 | 4 | 2 (1x 5.0 x16, 1x 4.0 x16) | 2+ | Aquantia 5GbE + Intel 2.5GbE + WiFi 7 | VAULT |
| 3 | Gigabyte TRX50 AERO D | sTR5 | DDR5 ECC RDIMM only | 4 | Multiple | Multiple | Aquantia 5GbE + RTL8125 2.5GbE + TB4 | Node 2 |
| 4 | Gigabyte Z690 AORUS ULTRA | LGA 1700 | DDR5 | 4 | Multiple | Multiple | Intel I225-V 1GbE + WiFi 6 | DEV |
| 5 | Gigabyte Z690 AORUS ELITE AX DDR4 | LGA 1700 | DDR4 | 4 | 3 (1x 5.0 x16, 1x 3.0 x16, 1x 3.0 x1) | 4 | 2.5GbE + WiFi 6E | Loose |
| 6 | Gigabyte Z390 AORUS PRO WIFI | LGA 1151 | DDR4 | 4 | 3 (2x 3.0 x16, 1x 3.0 x1) | 2 | 1GbE + WiFi | Loose |
| 7 | Gigabyte Z370 AORUS Gaming 5 | LGA 1151 | DDR4 | 4 | 4 (3x 3.0 x16, 1x 3.0 x1) | 2 | 1GbE | Loose |
| 8 | Gigabyte B365M DS3H | LGA 1151 | DDR4 | 2 | 2 (1x 3.0 x16, 1x 3.0 x1) | 1 | 1GbE | Loose |

**Total: 8 motherboards**

---

## RAM

| # | Module | Type | Capacity | Speed | Latency | Currently In |
|---|--------|------|----------|-------|---------|-------------|
| 1–7 | Samsung M393A4K40DB3-CWE (x7) | DDR4 ECC RDIMM | 224 GB (7x32GB) | 3200 MT/s | — | Node 1 (7/8 channels populated, channel H empty) |
| 8–11 | Micron CP32G60C40U5B.M8B3 (x4) | DDR5 UDIMM | 128 GB (4x32GB) | 5600 MT/s | CL40 | VAULT |
| 12–15 | Kingston KF556R28RBE2-32 (x4) | DDR5 ECC RDIMM | 128 GB (4x32GB) | 5600 MT/s (EXPO enabled) | CL28 | Node 2 |
| 16–17 | G.Skill Ripjaws S5 F5-5600J4040D32GX2 (x2) | DDR5 UDIMM | 64 GB (2x32GB) | 5600 MT/s | CL40 | DEV (audit confirmed 5600/CL40) |
| 18–19 | G.Skill F5-5200J3636D32G (x2) | DDR5 UDIMM | 64 GB (2x32GB) | 5200 MT/s | CL36 | Loose |
| 20–21 | Crucial Ballistix BL32G32C16U4B (x2) | DDR4 UDIMM | 64 GB (2x32GB) | 3200 MT/s | CL16 | Loose |
| 22–23 | G.Skill Ripjaws V F4-4000C18D-32GVK (x2) | DDR4 UDIMM | 32 GB (2x16GB) | 4000 MT/s | CL18 | Loose |
| 24–25 | G.Skill TridentZ RGB F4-3200C16D-32GTZR (x2) | DDR4 UDIMM | 32 GB (2x16GB) | 3200 MT/s | CL16 | Loose |
| 26–27 | G.Skill TridentZ RGB F4-3200C16D-16GTZR (x2) | DDR4 UDIMM | 16 GB (2x8GB) | 3200 MT/s | CL16 | Loose |

**Total: 27 sticks, 752 GB**
- DDR4: 368 GB (224 GB ECC RDIMM + 144 GB UDIMM)
- DDR5: 384 GB (128 + 128 + 64 + 64 GB)

---

## NVMe Storage

| # | Drive | Gen | Capacity | Currently In |
|---|-------|-----|----------|-------------|
| 1 | Crucial P3 (CT4000P3SSD8) | Gen3 | 4 TB | Node 1 (M.2_1, OS/system) |
| 2 | Crucial P310 | Gen4 | 1 TB | Node 1 (M.2_2, spare — replaced by Samsung 990 PRO 4TB as model store) |
| 3–6 | Samsung 990 EVO Plus (x4) | Gen4 | 4 TB (4x1TB) | VAULT (X870E M.2 slots) |
| 7 | Crucial T700 | Gen5 | 4 TB | Node 2 (M.2 Slot 1, OS/system) |
| 8 | Samsung 990 PRO (MZ-V9P4T0) | Gen4 | 4 TB | Node 1 (M.2_1, /mnt/local-fast — model store, PE8_SEL jumper moved to pins 1-2) |
| 9 | Crucial P3 Plus (CT4000P3PSSD8) | Gen4 | 4 TB | Loose |
| 10 | Crucial P310 (CT2000P310SSD8) | Gen4 | 2 TB | Loose |
| 11 | Samsung 970 EVO | Gen3 | 250 GB | Loose |
| 12 | Crucial T700 | Gen5 | 1 TB | Node 2 (M.2 Slot 2, unmounted, stale ZFS label) |
| 13 | Crucial T700 | Gen5 | 1 TB | Node 2 (M.2 Slot 3, unmounted, stale ZFS label) |
| 14 | Crucial T700 | Gen5 | 1 TB | Node 2 (M.2 Slot 4, unmounted, stale ZFS label) |
| 15 | Crucial T700 | Gen5 | 1 TB | Loose |
| 16–19 | Crucial P310 (x4) | Gen4 | 4 TB (4x1TB) | Loose (were incorrectly listed as VAULT Hyper M.2 — card slots confirmed empty) |
| 20 | Samsung 970 EVO Plus | Gen3 | 1 TB | Loose |
| 21 | WD Black SN750 | Gen3 | 1 TB | Loose |

**Total: 21 NVMe drives, 33.25 TB** (corrected: removed duplicate VAULT Hyper M.2 entries, Node 1 M.2_2 is P310 1TB not 990 PRO 4TB)

---

## HDDs

| # | Drive | Capacity | Currently In |
|---|-------|----------|-------------|
| 1 | WDC WD241KFGX-68CNGN0 | 22 TB | VAULT (parity) |
| 2 | WDC WD241KFGX-68CNGN0 | 22 TB | VAULT (disk9) |
| 3 | WDC WD181KFGX-68AFPN0 | 16 TB | VAULT (disk1) |
| 4 | ST20000VE002-3G9101 | 18 TB | VAULT (disk2) |
| 5 | WDC WD201KFGX-68BKJN0 | 18 TB | VAULT (disk3) |
| 6 | WDC WD201KFGX-68BKJN0 | 18 TB | VAULT (disk4) |
| 7 | WDC WD201KFGX-68BKJN0 | 18 TB | VAULT (disk5) |
| 8 | WDC WD201KFGX-68BKJN0 | 18 TB | VAULT (disk6) |
| 9 | WDC WD181KFGX-68AFPN0 | 16 TB | VAULT (disk7) |
| 10 | WDC WD201KFGX-68BKJN0 | 18 TB | VAULT (disk8) |

**Total: 10 HDDs, ~184 TB raw** (164 TB usable after parity)

---

## PCIe Expansion Cards

| # | Card | Function | Interface | Currently In |
|---|------|----------|-----------|-------------|
| 1 | Broadcom/LSI SAS3224 | SAS-3 HBA | PCIe 3.0 x8 | VAULT |
| 2 | ASUS Hyper M.2 X16 Gen5 | 4x NVMe carrier (ALL SLOTS EMPTY — confirmed by PCIe enumeration) | PCIe 5.0 x16 | VAULT |
| 3–4 | ASUS Hyper M.2 X16 Gen5 (x2) | 4x NVMe carrier | PCIe 5.0 x16 | Loose |
| 5 | Intel X540-T2 | Dual-port 5GbE RJ45 | PCIe 2.1 x8 | Loose |
| 6–7 | SR-PT02-X540 / X540 clone (x2) | Dual-port 5GbE RJ45 | PCIe 2.1 x8 | Loose |
| 8 | LSI SAS9300-16i | 16-port SAS/SATA HBA | PCIe 3.0 x8 | Loose |

**Loose 5GbE: 3 cards, 6 ports** | **Hyper M.2 adapters: 2 loose, 1 in VAULT**

---

## PSUs

| # | PSU | Wattage | Rating | Form Factor | Currently In |
|---|-----|---------|--------|-------------|-------------|
| 1 | Corsair | 1600W | — | ATX | Node 1 |
| 2 | MSI | 1600W | — | ATX | Node 2 |
| 3 | (unidentified) | ? | ? | ? | VAULT |
| 4 | (unidentified) | ? | ? | ? | DEV |
| 5 | Corsair SF1000L | 1000W | 80+ Gold | SFX-L | Loose |
| 6 | ASUS ROG | 1200W | 80+ Platinum | ATX | Loose |
| 7 | Corsair RM750 | 750W | 80+ Gold | ATX | Loose |
| 8 | EVGA 600B | 600W | 80+ Bronze | ATX | Loose |

**Total: 8 PSUs** (4 installed unidentified + 4 loose)

---

## Network Infrastructure (not per-node)

| Device | Type | Ports | Notes |
|--------|------|-------|-------|
| UniFi Dream Machine Pro | Router/Gateway | — | Core router |
| USW Pro 24 PoE | Switch | 24x 1GbE + 2x 10G SFP+ | JetKVMs, BMC, home devices |
| USW Pro XG 10 PoE | Switch | 8x 5GbE RJ45 + 4x 10G SFP+ | All server 5GbE links |
| USW Flex | Switch | 5x 1GbE | Garage |
| U6 APs (x6) | WiFi 6 | — | Whole-home coverage |
| Lutron controller | Lighting | — | .158 |
| USP PDU Pro | Power | — | Rack power management |
| JetKVM (.165) | KVM | — | Connected to Node 2 |
| JetKVM (.80) | KVM | — | Connected to VAULT |

---

## Cases

| # | Case | Form Factor | Currently In |
|---|------|-------------|-------------|
| 1 | Silverstone RM52 (upper tray) | 5U rackmount | Node 1 |
| 2 | Silverstone RM52 (middle tray) | 5U rackmount | Node 2 |
| 3 | (unidentified) | — | VAULT |
| 4 | (unidentified) | — | DEV |

---

## Summary Totals

| Resource | Count | Total Capacity |
|----------|-------|---------------|
| CPUs | 7 | 138 cores / 260 threads |
| GPUs | 12 | 190 GB VRAM (176 GB NVIDIA) |
| RAM sticks | 27 | 752 GB |
| NVMe drives | 21 | 33.25 TB |
| HDDs | 10 | 184 TB raw |
| Motherboards | 8 | — |
| PSUs | 8 | — |
| 5GbE ports (all hardware) | 10 | — |
| Hyper M.2 adapters | 3 | 12 NVMe slots |
| HBAs | 2 | — |
