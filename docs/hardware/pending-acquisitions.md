# Pending Acquisitions

**STATUS: NOT OWNED — These components are planned purchases. Do not treat as available hardware.**

Move items to `inventory.md` only after physical receipt.

---

## GPU — NVIDIA RTX PRO 6000 Blackwell Max-Q

| Spec | Value |
|------|-------|
| Full Name | NVIDIA RTX PRO 6000 Blackwell Max-Q |
| Manufacturer | PNY (workstation edition) |
| VRAM | 96 GB GDDR7 ECC |
| TDP | 300 W |
| Architecture | Blackwell |
| Interface | PCIe 5.0 x16 |

**CRITICAL NOTE:** This is an NVIDIA workstation GPU (PNY), NOT an AMD Radeon product. The "PRO" in the name refers to NVIDIA's professional line.

**Impact on system totals when acquired:**
- Total VRAM: 138 GB → 234 GB (+96 GB)
- Enables running 70B+ FP16 models without quantization
- Single-card capacity exceeds most consumer multi-GPU setups

---

## InfiniBand — EDR 100 Gb/s Fabric

Target: Mellanox EDR (Enhanced Data Rate) for tensor parallelism across nodes.

### Host Channel Adapters (HCAs)

| Component | Model Options | Qty Needed | Est. Used Price |
|-----------|---------------|------------|-----------------|
| HCA | Mellanox ConnectX-5 VPI (MCX556A) | 3–6 | $50–100 each |
| HCA (alt) | Mellanox ConnectX-6 VPI (MCX653106A) | 3–6 | $100–200 each |

### Switch

| Component | Model Options | Qty | Est. Used Price |
|-----------|---------------|-----|-----------------|
| Switch | Mellanox SB7700 (EDR, 36-port) | 1 | $200–400 |
| Switch (alt) | Mellanox SB7800 (EDR, 36-port managed) | 1 | $300–500 |

### Cables

| Component | Spec | Qty | Est. Used Price |
|-----------|------|-----|-----------------|
| Cables | QSFP56 EDR passive copper, 1–2m | 3–6 | $15–30 each |

**Estimated total: $400–1,200 depending on CX-5 vs CX-6 and switch choice.**

### What InfiniBand Unlocks
- Sub-microsecond latency between nodes (vs ~100μs for 5GbE TCP)
- RDMA — direct memory access across nodes without CPU involvement
- Enables tensor parallelism across 4× RTX 5070 Ti cards spanning multiple nodes
- NCCL native support for distributed inference
- 100 Gb/s bidirectional bandwidth per link

### FDR Fallback Option

If EDR deals don't materialize, FDR 56 Gb/s is much cheaper:

| Component | Model | Qty | Est. Used Price |
|-----------|-------|-----|-----------------|
| HCA | Mellanox ConnectX-3 VPI (MCX354A) | 3–6 | $20–30 each |
| Switch | Mellanox SX6036 (FDR, 36-port) | 1 | $100–200 |
| Cables | QSFP+ FDR passive copper | 3–6 | $10–20 each |

**FDR total: ~$200–350.** Still dramatically faster than 5GbE for NCCL traffic.

---

## Priority Order

1. **InfiniBand** — Highest impact per dollar. Unlocks distributed inference across nodes.
2. **RTX PRO 6000** — Highest single-card VRAM. Enables models that currently don't fit.

---

*Last updated: February 2026*
