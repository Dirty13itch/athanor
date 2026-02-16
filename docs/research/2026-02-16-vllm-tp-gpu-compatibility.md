# vLLM Tensor Parallelism: GPU Compatibility Research

**Date:** 2026-02-16
**Status:** Complete
**Purpose:** Determine which NVIDIA GPUs can tensor-parallel (TP) together in vLLM, specifically for the GPUs in Athanor's inventory and potential future purchases.

---

## The Rule

vLLM's tensor parallelism requires **identical GPU models** for correct operation. The constraints, from most to least obvious:

1. **Same compute capability** — Different architectures (e.g., SM86 vs SM89) select different kernels, producing numerically incompatible results.
2. **Same VRAM amount** — vLLM allocates based on the smallest GPU's memory. Different VRAM amounts waste capacity and may cause allocation failures.
3. **Same memory bus width** — Different bus widths imply different memory controller configurations, which changes the physical GPU topology.
4. **Same CUDA core count** — Different SM counts mean different execution characteristics. While theoretically the results should be bit-identical for same-architecture SMs, vLLM detects device names and will warn or refuse to proceed with mismatched models.
5. **Same memory type** — GDDR6 vs GDDR6X vs GDDR7 have different signaling, bandwidth, and error characteristics.

**Key evidence:** [vLLM Issue #34437](https://github.com/vllm-project/vllm/issues/34437) documents mixing 3x RTX 3090 (SM86) + 1x RTX 4090 (SM89) producing inconsistent/wrong outputs with TP due to FP8 kernel mismatches and numerical drift through all-reduce operations. Even pipeline parallelism only worked with specific GPU ordering.

The [vLLM forum](https://discuss.vllm.ai/t/how-to-run-a-model-use-heterogeneous-gpus/1360) explicitly states: "vLLM's distributed inference (tensor/pipeline parallelism) requires all participating GPUs to be of the same type and architecture for correct operation and performance."

---

## Die-by-Die Analysis

### 1. GA106 (Ampere) — RTX 3060 12GB

**Your GPU:** RTX 3060 12GB — GA106-300/302, 3584 CUDA cores, 12GB GDDR6, 192-bit bus

| GPU Model | Die Variant | CUDA Cores | VRAM | Bus Width | Memory Type | TP Compatible? |
|---|---|---|---|---|---|---|
| **RTX 3060 12GB** | GA106-300/302 | 3584 | 12 GB | 192-bit | GDDR6 | **YES** (identical) |
| RTX 3060 8GB | GA106-xxx | 3584 | 8 GB | 128-bit | GDDR6 | **NO** — different VRAM, different bus width |
| RTX 3060 3840SP | GA106 (full) | 3840 | 12 GB | 192-bit | GDDR6 | **NO** — different CUDA core count |
| RTX 3060 GA104 variant | GA104 (!) | 3584 | 12 GB | 192-bit | GDDR6X | **NO** — completely different die |
| RTX 3050 (GA106 variant) | GA106-150 | 2560 | 8 GB | 128-bit | GDDR6 | **NO** — different cores, VRAM, bus |
| RTX A2000 12GB | GA106 | 3328 | 12 GB | 192-bit | GDDR6 ECC | **NO** — different CUDA cores (3328 vs 3584) |
| RTX A2000 6GB | GA106 | 3328 | 6 GB | 192-bit | GDDR6 ECC | **NO** — different cores, different VRAM |

**TP partners for RTX 3060 12GB: Only other RTX 3060 12GB cards (GA106-300/302 variant, not the 8GB, 3840SP, or GA104 variants).**

Caveat: NVIDIA shipped multiple RTX 3060 12GB SKUs. The standard GA106-300 and the LHR revision GA106-302 should be TP-compatible since they have identical specs (the LHR limiter only affects mining, not compute). Verify by checking `nvidia-smi` output matches.

Sources:
- [VideoCardz GA106 database](https://videocardz.net/gpu/nvidia-ga106)
- [Tom's Hardware — RTX 3060 3840SP variant](https://www.tomshardware.com/news/rare-nvidia-rtx-3060-emerges-with-full-ga106-die-3840-cuda-cores)
- [NVIDIA RTX A2000 datasheet](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/rtx-a2000/nvidia-rtx-a2000-datasheet.pdf)

---

### 2. AD102 (Ada Lovelace) — RTX 4090

**Your GPU:** RTX 4090 24GB — AD102-300/301, 16384 CUDA cores, 24GB GDDR6X, 384-bit bus

| GPU Model | Die Variant | CUDA Cores | VRAM | Bus Width | Memory Type | TP Compatible? |
|---|---|---|---|---|---|---|
| **RTX 4090** | AD102-300/301 | 16384 | 24 GB | 384-bit | GDDR6X | **YES** (identical) |
| RTX 6000 Ada | AD102-500 | 18176 | 48 GB | 384-bit | GDDR6 ECC | **NO** — different cores, VRAM, memory type |
| L40S | AD102 | 18176 | 48 GB | 384-bit | GDDR6 ECC | **NO** — different cores, VRAM, memory type |
| L40 | AD102 | 18176 | 48 GB | 384-bit | GDDR6 ECC | **NO** — different cores, VRAM, memory type |
| RTX 4090 Ti | AD102 (full) | 18176 | 24 GB | 384-bit | GDDR6X | **NEVER RELEASED** |

**TP partners for RTX 4090: Only other RTX 4090 cards.**

The RTX 4090 Ti was never commercially released. Even if it had been, its 18176 cores vs the 4090's 16384 would have made TP incompatible. NVIDIA updated the RTX 4090 from AD102-300 to AD102-301 — this was a minor silicon revision and both report as "RTX 4090" with identical specs, so they should TP together.

The RTX 6000 Ada is particularly misleading here. Same die family (AD102), same bus width (384-bit), but:
- Different VRAM: 48GB vs 24GB
- Different memory type: GDDR6 (with ECC) vs GDDR6X
- Different core count: 18176 vs 16384

These differences make TP impossible between RTX 4090 and RTX 6000 Ada.

Sources:
- [Tom's Hardware — AD102-301 revision](https://www.tomshardware.com/news/nvidia-quietly-rolls-out-geforce-rtx-4090-with-new-gpu-model)
- [NVIDIA RTX 6000 Ada datasheet](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/rtx-6000/proviz-print-rtx6000-datasheet-web-2504660.pdf)
- [NotebookCheck RTX 6000 Ada specs](https://www.notebookcheck.net/NVIDIA-RTX-6000-Ada-Generation-Benchmarks-and-Specs.806211.0.html)

---

### 3. GB202 (Blackwell) — RTX 5090

**Your GPU:** RTX 5090 32GB — GB202-300, 21760 CUDA cores, 32GB GDDR7, 512-bit bus

| GPU Model | Die Variant | CUDA Cores | VRAM | Bus Width | Memory Type | TP Compatible? |
|---|---|---|---|---|---|---|
| **RTX 5090** | GB202-300 | 21760 | 32 GB | 512-bit | GDDR7 | **YES** (identical) |
| RTX PRO 6000 Blackwell | GB202 | 24064 | 96 GB | 512-bit | GDDR7 ECC | **NO** — different cores, VRAM (3x!) |
| RTX PRO 5000 Blackwell | GB202 | 14080 | 48/72 GB | 512-bit | GDDR7 ECC | **NO** — different cores, different VRAM |
| RTX 5090 Ti (rumored) | GB202 (full) | ~24576 | unknown | 512-bit | GDDR7 | **NOT RELEASED** — likely different cores, possibly different VRAM |

**TP partners for RTX 5090: Only other RTX 5090 cards.**

The RTX PRO 6000 Blackwell is the closest workstation analog but has 24064 CUDA cores (vs 21760) and a massive 96GB of VRAM (vs 32GB). Completely incompatible for TP. The RTX PRO 5000 is even further off with only 14080 cores and 48-72GB VRAM.

If an RTX 5090 Ti is ever released, it would almost certainly have a different core count and potentially different VRAM, making it TP-incompatible with the standard 5090.

Sources:
- [NVIDIA RTX 5090 specs](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/)
- [NVIDIA RTX PRO 6000 Blackwell](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/)
- [Indiekings — RTX 5090 Ti rumors](https://www.indiekings.com/2025/12/nvidia-rtx-5090-ti-rumors-full-gb202.html)

---

### 4. GB203 (Blackwell) — RTX 5070 Ti

**Your GPU:** RTX 5070 Ti 16GB — GB203-300, 8960 CUDA cores, 16GB GDDR7, 256-bit bus

| GPU Model | Die Variant | CUDA Cores | VRAM | Bus Width | Memory Type | TP Compatible? |
|---|---|---|---|---|---|---|
| **RTX 5070 Ti** | GB203-300 | 8960 | 16 GB | 256-bit | GDDR7 | **YES** (identical) |
| RTX 5080 | GB203-400 | 10752 | 16 GB | 256-bit | GDDR7 | **NO** — different CUDA cores (10752 vs 8960) |
| RTX 5070 Ti Super (upcoming) | GB203-350 | 8960 | 24 GB | 256-bit | GDDR7 | **NO** — same cores but different VRAM (24 vs 16 GB) |
| RTX 5080 Super (upcoming) | GB203-450 | 10752 | 24 GB | 256-bit | GDDR7 | **NO** — different cores and VRAM |
| RTX PRO 4500 | GB203 | 10496 | 32 GB | 256-bit | GDDR7 ECC | **NO** — different cores and VRAM |
| RTX PRO 4000 | GB203 | 8960 | 24 GB | 192-bit | GDDR7 | **NO** — different VRAM AND different bus width (192 vs 256) |

**TP partners for RTX 5070 Ti: Only other RTX 5070 Ti cards.**

The GB203 die is the most crowded die family, with six current or upcoming products sharing the same silicon. None are TP-compatible with each other:

- **RTX 5080**: Same VRAM (16GB), same bus (256-bit), but 10752 cores vs 8960. The core count difference means vLLM sees them as different devices.
- **RTX 5070 Ti Super**: Same cores (8960), same bus (256-bit), but 24GB vs 16GB. The VRAM difference breaks TP allocation.
- **RTX PRO 4000**: Same cores (8960) but 192-bit bus (vs 256-bit) and 24GB VRAM. Different physical memory topology.

The RTX 5080 + RTX 5070 Ti question is the most tempting "almost works" scenario. Same die, same VRAM, same bus width, same memory type — only the core count differs. In theory, same-architecture SMs should produce bit-identical results, and TP would just be bottlenecked by the slower 5070 Ti. In practice, vLLM detects device names and treats them as heterogeneous. No one has documented forcing this to work. The risk of silent numerical errors makes it inadvisable.

Sources:
- [VideoCardz — RTX 5070 Ti specs confirmed](https://videocardz.com/newz/nvidia-confirms-full-geforce-rtx-5070-ti-specifications-featuring-gb203-and-gb205-gpus)
- [WCCFTech — RTX 5070 Ti Super leaked specs](https://wccftech.com/nvidia-geforce-rtx-5070-ti-super-to-24-gb-memory-350w-power/)
- [WCCFTech — RTX 5080 Super leaked specs](https://wccftech.com/nvidia-geforce-rtx-5080-super-specs-leak-24-gb-vram-32-gbps-10752-cores-at-400w/)
- [Central Computer — RTX PRO Blackwell lineup](https://www.centralcomputer.com/blog/post/all-nvidia-rtx-pro-blackwell-gpus-explained)

---

## Cross-Variant TP: GeForce vs Workstation (PRO)

**Can an RTX A6000 (GA102, 48GB) TP with an RTX 3090 (GA102, 24GB)?**

**No.** Despite sharing the GA102 die:
- RTX 3090: 10496 CUDA cores, 24GB GDDR6X, 384-bit bus
- RTX A6000: 10752 CUDA cores, 48GB GDDR6 ECC, 384-bit bus

Different CUDA cores, different VRAM, different memory type. Three strikes.

**Can ANY GeForce card TP with its workstation counterpart?**

In every die family examined, the workstation/PRO variant differs from the GeForce variant in at least two of: CUDA cores, VRAM amount, and memory type. NVIDIA deliberately differentiates these products:

| Die | GeForce | PRO/Workstation | Differences |
|---|---|---|---|
| GA106 | RTX 3060 (3584 cores, 12GB) | RTX A2000 (3328 cores, 12GB ECC) | Cores, memory type |
| AD102 | RTX 4090 (16384 cores, 24GB GDDR6X) | RTX 6000 Ada (18176 cores, 48GB GDDR6 ECC) | Cores, VRAM, memory type |
| GB202 | RTX 5090 (21760 cores, 32GB) | RTX PRO 6000 (24064 cores, 96GB ECC) | Cores, VRAM (3x!) |
| GB203 | RTX 5070 Ti (8960 cores, 16GB) | RTX PRO 4500 (10496 cores, 32GB ECC) | Cores, VRAM |

**Conclusion: GeForce-to-PRO TP is never possible.** The product segmentation guarantees at least one incompatible spec difference.

---

## Implications for Athanor

### Current Hardware
- **Node 1:** 4x RTX 5070 Ti 16GB — **TP-4 works.** All identical GB203-300 dies.
- **Node 2:** 1x RTX 4090 + 1x RTX 5090 — **TP-2 impossible.** Different dies, different architectures, different everything. Each GPU operates independently (separate vLLM instances or pipeline parallelism with caveats).

### If Buying More GPUs
- To expand Node 1's TP capacity: buy more RTX 5070 Ti 16GB cards only (not 5080, not 5070 Ti Super).
- To enable TP on Node 2: buy a second RTX 5090 (for 5090 TP-2) or a second RTX 4090 (for 4090 TP-2). Mixing is not an option.
- The RTX 5070 Ti is being discontinued. If you want more for future TP scaling, buy them before stock dries up.

### Pipeline Parallelism (PP) as Alternative
For Node 2's mixed GPU setup (RTX 4090 + RTX 5090), pipeline parallelism is theoretically possible — each GPU handles different layers rather than splitting tensors. However:
- vLLM's PP support with heterogeneous GPUs is poorly documented and fragile
- GPU ordering matters (issue #34437 showed wrong ordering crashes the engine)
- Performance is worse than TP due to pipeline bubbles
- Not recommended for production use with mixed consumer GPUs

### Best Strategy for Node 2
Run separate vLLM instances:
- RTX 5090 (32GB): Larger models or primary inference
- RTX 4090 (24GB): Smaller models or secondary inference
- Use a router/load balancer to distribute requests

---

## RTX PRO Blackwell Die Map (Reference)

For completeness, here is the full Blackwell PRO workstation lineup mapped to consumer dies:

| PRO Model | Die | CUDA Cores | VRAM | Bus Width | Consumer Counterpart Die |
|---|---|---|---|---|---|
| RTX PRO 6000 | GB202 | 24064 | 96 GB | 512-bit | Same as RTX 5090 |
| RTX PRO 5000 (desktop) | GB202 | 14080 | 48/72 GB | 512-bit | Same as RTX 5090 |
| RTX PRO 4500 | GB203 | 10496 | 32 GB | 256-bit | Same as RTX 5080/5070 Ti |
| RTX PRO 4000 | GB203 | 8960 | 24 GB | 192-bit | Same as RTX 5080/5070 Ti |
| RTX PRO 2000 | GB206 | 4352 | 16 GB | 128-bit | Same as RTX 5060 (unreleased) |

None of these are TP-compatible with their GeForce counterparts.
