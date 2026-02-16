# Loose Hardware Inventory

All hardware listed below is uninstalled and available for allocation.
Cables, risers, adapters, coolers, fans, and cases are excluded — treat these as available on demand (buy as needed).
All NVIDIA GPUs are installed in existing nodes. One AMD GPU is loose.

---

## GPUs

| GPU | VRAM | Interface | Notes |
|-----|------|-----------|-------|
| ASUS ROG STRIX RX 5700 XT 8G Gaming | 8GB GDDR6 | PCIe 4.0 x16 | RDNA 1, no CUDA/tensor cores. Useful for display output, VM passthrough, or ROCm compute (limited support). Not suitable for LLM inference. |

## CPUs

| CPU | Socket | Cores/Threads | Base Clock | Notes |
|-----|--------|---------------|------------|-------|
| Intel Core i7-12700K (SRL4N) | LGA 1700 | 12C/20T (8P+4E) | 3.6 GHz | Alder Lake, DDR4/DDR5 |
| Intel Core i5-12600K (SRL4T) | LGA 1700 | 10C/16T (6P+4E) | 3.7 GHz | Alder Lake, DDR4/DDR5 |
| Intel Core i7-9700K (SRG15) | LGA 1151 | 8C/8T | 3.6 GHz | Coffee Lake, DDR4 only |

## Motherboards

| Motherboard | Socket | Chipset | RAM Type | PCIe Slots | M.2 Slots | Notes |
|-------------|--------|---------|----------|------------|-----------|-------|
| Gigabyte Z690 AORUS ELITE AX DDR4 | LGA 1700 | Z690 | DDR4 | 1x PCIe 5.0 x16, 1x PCIe 3.0 x16, 1x PCIe 3.0 x1 | 4x M.2 | WiFi 6E, 2.5GbE |
| Gigabyte Z390 AORUS PRO WIFI | LGA 1151 | Z390 | DDR4 | 2x PCIe 3.0 x16, 1x PCIe 3.0 x1 | 2x M.2 | WiFi, 1GbE |
| Gigabyte Z370 AORUS Gaming 5 | LGA 1151 | Z370 | DDR4 | 3x PCIe 3.0 x16, 1x PCIe 3.0 x1 | 2x M.2 | 1GbE, Killer E2500 |
| Gigabyte B365M DS3H | LGA 1151 | B365 | DDR4 | 1x PCIe 3.0 x16, 1x PCIe 3.0 x1 | 1x M.2 | Micro-ATX, 1GbE |

## Compatible Pairings

- **i7-12700K or i5-12600K** → Z690 AORUS ELITE AX DDR4 (LGA 1700)
- **i7-9700K** → Z390 AORUS PRO WIFI or Z370 AORUS Gaming 5 (LGA 1151)
- **B365M DS3H** → needs an LGA 1151 CPU (9th/8th gen); i7-9700K compatible

## RAM

| Kit | Type | Capacity | Speed | Latency | Compatible With |
|-----|------|----------|-------|---------|-----------------|
| G.Skill Ripjaws S5 (F5-5600J4040D32GX2-RS5K) | DDR5 | 64GB (2x32GB) | DDR5-5600 | CL40-40-40-89 | **None of the loose boards** (no DDR5 board available) |
| Crucial Ballistix (BL32G32C16U4B.M16FB1) | DDR4 | 64GB (2x32GB) | DDR4-3200 | CL16-18-18-36 | Z690, Z390, Z370, B365M |
| G.Skill Ripjaws V (F4-4000C18D-32GVK) | DDR4 | 32GB (2x16GB) | DDR4-4000 | CL18-22-22-42 | Z690, Z390, Z370 |
| G.Skill TridentZ RGB (F4-3200C16D-32GTZR) | DDR4 | 32GB (2x16GB) | DDR4-3200 | CL16-18-18-38 | Z690, Z390, Z370, B365M |
| G.Skill TridentZ RGB (F4-3200C16D-16GTZR) | DDR4 | 16GB (2x8GB) | DDR4-3200 | CL16-18-18-38 | Z690, Z390, Z370, B365M |

**Total DDR4:** 144GB across 4 kits (8 sticks)
**Total DDR5:** 64GB, 1 kit (2 sticks) — no compatible loose motherboard

## NVMe Storage

| Drive | Interface | Capacity | Qty | Notes |
|-------|-----------|----------|-----|-------|
| Crucial T700 | PCIe Gen5 x4 | 1TB | 4 | ~12,400 MB/s read; needs Gen5 M.2 or Hyper M.2 Gen5 adapter |
| Crucial P310 | PCIe Gen4 x4 | 1TB | 5 | ~7,100 MB/s read |
| Samsung 970 EVO Plus | PCIe Gen3 x4 | 1TB | 1 | ~3,500 MB/s read |
| WD Black SN750 | PCIe Gen3 x4 | 1TB | 1 | ~3,470 MB/s read |

**Total NVMe:** 11TB across 11 drives

## PCIe Expansion Cards

| Card | Interface | Function | Qty | Notes |
|------|-----------|----------|-----|-------|
| ASUS Hyper M.2 X16 Gen5 | PCIe 5.0 x16 | 4x M.2 NVMe carrier | 3 | Holds 4x M.2 drives each; full bandwidth needs PCIe 5.0 x16 slot |
| Intel X540-T2 | PCIe 2.1 x8 | Dual-port 10GbE RJ45 | 1 | 10GBASE-T copper |
| SR-PT02-X540 (X540-T2 clone) | PCIe 2.1 x8 | Dual-port 10GbE RJ45 | 2 | 10GBASE-T copper, X540 chipset |
| LSI SAS9300-16i | PCIe 3.0 x8 | 16-port SAS/SATA HBA | 1 | 12 Gb/s SAS3, no drives/JBODs currently |

**Total 10GbE NICs:** 3 cards = 6 ports

## PSUs

| PSU | Wattage | Efficiency | Form Factor | Notes |
|-----|---------|------------|-------------|-------|
| Corsair SF1000L | 1000W | 80+ Gold | SFX-L | Compact builds |
| ASUS ROG 1200W | 1200W | 80+ Platinum (likely) | ATX | High-draw GPU rigs |
| Corsair RM750 | 750W | 80+ Gold | ATX | Mid-range |
| EVGA 600B | 600W | 80+ Bronze | ATX | Low-draw / basic node |

---

## Key Observations for Allocation

1. **DDR5 orphan:** 64GB DDR5-5600 kit has no compatible loose motherboard. Only useful if installed in an existing DDR5 node or if a DDR5 board is acquired.

2. **10GbE mesh potential:** 3x dual-port X540 adapters = 6 ports. Enough for a 3-node 10GbE mesh or switch-based 10GbE fabric. No InfiniBand cards in loose inventory.

3. **Gen5 NVMe + Hyper M.2 combo:** 4x T700 Gen5 drives + 3x Hyper M.2 Gen5 adapters. Only the Z690 board has a PCIe 5.0 x16 slot to run them at full speed. In Gen3/Gen4 slots they'll work but bandwidth-limited.

4. **Potential additional nodes:** Loose CPUs + boards can build up to 3 additional machines:
   - **Node A:** i7-12700K + Z690 (strongest — 12C/20T, PCIe 5.0, 4x M.2 native)
   - **Node B:** i7-9700K + Z390 (mid-tier — 8C/8T, WiFi, 2x M.2)
   - **Node C:** i7-9700K-compatible + Z370 or B365M (if another CPU is sourced, or repurpose 9700K)
   - Only 2 CPUs fit LGA 1151, and only 1 (9700K) is available, so max 2 nodes from loose parts without buying more.

5. **SAS HBA:** LSI 9300-16i is a passthrough HBA (no RAID). Useful for JBOD/ZFS/Unraid direct-attach storage expansion if SAS drives or enclosures are added later.

6. **Storage capacity:** 11TB NVMe total. Combined with existing node storage, this is substantial for a homelab cluster.
