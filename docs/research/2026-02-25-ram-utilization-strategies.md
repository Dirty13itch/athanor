# RAM Utilization Strategies for AI Inference

**Date:** 2026-02-25
**Updated:** 2026-02-25 (supplemental research: vLLM source code analysis, huge pages, kernel tuning, safetensors loading)
**Status:** Complete -- recommendation ready
**Supports:** Future ADR (RAM Allocation Strategy)
**Depends on:** ADR-005 (Inference Engine), ADR-004 (Node Roles)

---

## The Problem

Athanor has **544 GB of system RAM** across four nodes. Roughly **400+ GB sits unused**. This is a massive, untapped resource that could dramatically improve inference throughput, model capacity, context length, and concurrency.

| Node | Total RAM | Type | Channels | Est. Bandwidth | Used | Available |
|------|-----------|------|----------|-----------------|------|-----------|
| **Foundry** | 224 GB | DDR4-3200 ECC | 8 (octa) | ~150 GB/s practical | ~30 GB | ~190 GB |
| **Workshop** | 128 GB | DDR5-5600 | 4 (quad) | ~130 GB/s practical | ~20 GB | ~108 GB |
| **VAULT** | 128 GB | DDR5-5600 | 2 (dual) | ~65 GB/s practical | ~30 GB | ~98 GB |
| **DEV** | 64 GB | DDR5-4800 | 2 (dual) | ~55 GB/s practical | ~20 GB | ~44 GB |
| **TOTAL** | **544 GB** | | | | **~100 GB** | **~440 GB** |

### Memory Bandwidth Reality Check

Bandwidth is the critical factor for all CPU-side AI workloads. Decode speed for autoregressive LLMs is almost entirely memory-bandwidth-bound.

| Node | CPU | Architecture | Memory Config | Peak BW | Practical BW (~70-80%) |
|------|-----|-------------|---------------|---------|----------------------|
| Foundry | EPYC 7663 | Zen 3 (Milan) | 8x DDR4-3200 | 204.8 GB/s | ~145-165 GB/s |
| Workshop | TR 7960X | Zen 5 | 4x DDR5-5600 | 179.2 GB/s | ~125-145 GB/s |
| VAULT | Ryzen 9950X | Zen 5 | 2x DDR5-5600 | 89.6 GB/s | ~63-72 GB/s |
| DEV | i7-13700K | Raptor Lake | 2x DDR5-4800 | 76.8 GB/s | ~54-62 GB/s |

**Note on bandwidth calculations:**
- DDR4-3200: 3200 MT/s x 8 bytes = 25.6 GB/s per channel
- DDR5-5600: 5600 MT/s x 8 bytes = 44.8 GB/s per channel
- Practical bandwidth is 70-80% of theoretical due to refresh, scheduling, bank conflicts

### CPU Instruction Set Capabilities

| Feature | EPYC 7663 (Zen 3) | TR 7960X (Zen 5) | Ryzen 9950X (Zen 5) | i7-13700K (RPL) |
|---------|-------------------|-------------------|---------------------|-----------------|
| AVX2 | Yes | Yes | Yes | Yes |
| AVX-512 | Yes (256-bit fused) | Yes (full 512-bit) | Yes (full 512-bit) | **No** (disabled) |
| AVX-512-BF16 | **No** | Yes | Yes | **No** |
| AVX-VNNI | **No** | Yes | Yes | Yes (AVX2 only) |
| Intel AMX | **No** (AMD) | **No** (AMD) | **No** (AMD) | **No** (desktop) |
| Cores/Threads | 56C/112T | 24C/48T | 16C/32T | 16C/24T |

**Key implication:** Intel AMX, which gives KTransformers its best prefill performance (21 TFLOPS BF16), is unavailable on all Athanor nodes. KTransformers will use AVX-512 (Foundry, Workshop, VAULT) or AVX2 (DEV) backends. This means roughly **2-4x slower prefill** than the headline AMX benchmarks, but decode speed is bandwidth-limited and less affected.

---

## Strategy 1: MoE Expert Offloading to CPU RAM (KTransformers)

### What It Does

KTransformers runs MoE (Mixture-of-Experts) models by keeping expert FFN weights in CPU RAM and the attention/shared-expert layers on GPU. For each token, only the activated experts (2-8 out of 64-256 total) are loaded from RAM, computed on CPU via AVX-512/AMX kernels, then results are passed back to GPU for attention.

This is the single most impactful RAM utilization strategy because it enables running models 5-10x larger than what fits in VRAM alone.

### Performance Data

Source: KTransformers benchmarks (DeepSeek V3 671B Q4_K_M, Intel Xeon Gold 6454S + RTX 4090)

| Version | Config | Prefill (tok/s) | Decode (tok/s) | vs llama.cpp |
|---------|--------|-----------------|----------------|-------------|
| V0.2 | Single socket, 8 experts | 54.21 | 8.73 | 5.3x / 1.9x |
| V0.2 | Dual socket, 8 experts | 82.94 | 12.21 | 8.0x / 2.7x |
| V0.2 | Dual socket, 6 experts | 97.32 | 13.69 | 9.4x / 3.0x |
| V0.2.1 | Dual socket, 6 experts, 4K | 102 | 14.9 | - |
| V0.3 | Dual socket, AMX, 8 experts | 255.26 | ~12 | 24.8x / 2.7x |
| V0.3 | Dual socket, AMX, 6 experts | 286.55 | ~13.7 | 27.8x / 3.0x |
| llama.cpp | Dual socket, 2x32 cores | 10.31 | 4.51 | baseline |

Consumer CPU results (Qwen3MoE 235B-A22, i9-14900KF + DDR5-4000 + RTX 4090):
- Workstation with AMX Xeon: up to 347 tok/s prefill
- Consumer i9-14900KF: runs but slower (no AMX, lower bandwidth)
- Qwen3MoE 30B-A3B runs smoothly on "high-end gaming laptop" class hardware

### What This Means for Athanor

**Foundry (EPYC 7663, 224 GB DDR4, no AMX):**
- Uses AVX-512 llamafile backend (not AMX) -- roughly V0.2 performance level
- 56 cores is MORE than the 32 per socket in Xeon benchmarks
- 8-channel DDR4-3200 gives ~150 GB/s -- competitive with dual-socket Xeon setups
- **Estimated decode: 10-14 tok/s for DeepSeek V3 671B** (bandwidth-limited)
- **Problem: 224 GB RAM is NOT enough for DeepSeek V3 Q4 (~382 GB required)**
- **CAN run: Qwen3MoE 235B-A22 Q4 (~130 GB), Qwen3MoE 30B-A3B (~17 GB), Mixtral 8x7B (~26 GB)**

**Workshop (TR 7960X, 128 GB DDR5, AVX-512-BF16):**
- Zen 5 AVX-512-BF16 could be ~2x over Zen 3 AVX-512 for BF16 ops
- 4-channel DDR5-5600 gives ~130 GB/s -- excellent for decode
- 24 cores limits prefill parallelism vs EPYC's 56
- **Can run: Qwen3MoE 30B-A3B easily, larger models with quantization**

### RAM Requirements by Model

| Model | Parameters | Active | Q4 RAM | FP8 RAM | Fits Foundry? | Fits Workshop? |
|-------|-----------|--------|--------|---------|---------------|----------------|
| DeepSeek V3/R1 | 671B | 37B | ~382 GB | ~644 GB | No (224 GB) | No (128 GB) |
| Qwen3MoE 235B-A22 | 235B | 22B | ~130 GB | ~240 GB | Yes (Q4) | No |
| Qwen3MoE 30B-A3B | 30B | 3B | ~17 GB | ~32 GB | Yes | Yes |
| Mixtral 8x22B | 176B | 44B | ~100 GB | ~180 GB | Yes (Q4) | No |
| Mixtral 8x7B | 46.7B | 12.9B | ~26 GB | ~47 GB | Yes | Yes |
| MiniMax-M2.5 | varies | varies | TBD | TBD | Likely | TBD |

### NUMA Considerations (Critical for Foundry)

EPYC 7663 Milan supports NPS1 (1 NUMA node), NPS2, NPS4. KTransformers is NUMA-aware:
- In NUMA mode: duplicates critical matrices on each NUMA node (uses more RAM but faster access)
- `numactl -N 1 -m 1` for single-NUMA binding
- For Foundry: **check BIOS setting** -- NPS1 is simplest, NPS2 may benefit KTransformers

### SGLang Integration

As of Oct 2025, KTransformers' `kt-kernel` module integrates with SGLang:
- GPU Tensor Parallelism + CPU/GPU Hybrid Expert Parallelism
- Dense layers on GPU (multi-GPU TP), experts on CPU
- CUDA Graph scheduling reduces GPU launch overhead to near zero
- Performance: 21.3 TFLOPS CPU MoE kernel (4x PyTorch baseline)
- **Status: marked "inactive" on GitHub** -- experimental, not production-ready

### Supported Models

DeepSeek V3/R1, Qwen3MoE, MiniMax M2.1/M2.5, GLM-4/5 MoE, Kimi K2/K2.5/K2-Thinking, SmallThinker, LLaMA 4 (experimental), Mixtral 8x7B/8x22B.

### Sources

- [KTransformers GitHub README](https://github.com/kvcache-ai/ktransformers)
- [KTransformers DeepSeek R1/V3 Tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepseekR1_V3_tutorial.md)
- [KTransformers AMX Documentation](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/AMX.md)
- [SGLang + KTransformers Integration Blog](https://lmsys.org/blog/2025-10-22-KTransformers/)
- [SGLang + KTransformers GitHub Issue](https://github.com/sgl-project/sglang/issues/11425)
- [KTransformers SOSP 2025 Paper](https://dl.acm.org/doi/10.1145/3731569.3764843)

---

## Strategy 2: KV Cache Offloading to CPU RAM

### What It Does

Offloads the KV (key-value) cache from GPU VRAM to system RAM. The KV cache grows linearly with sequence length and batch size, often becoming the primary VRAM consumer for long-context or high-concurrency workloads. Moving it (or a portion) to CPU RAM frees VRAM for more concurrent requests or longer contexts.

### vLLM KV Offloading (Source Code Verified)

vLLM has THREE distinct parameters that use CPU RAM, each serving a different purpose. This is a common source of confusion. All field definitions verified against `vllm/config/cache.py` on the main branch (2026-02-25).

**1. `--swap-space N` (GiB, default: 4 per GPU)** -- preemption swap buffer
- Reserves `swap_space * num_gpus` bytes of pinned CPU memory at startup
- Used when vLLM preempts a lower-priority request (swaps KV blocks GPU -> CPU)
- NOT the same as KV offloading -- this is for temporary eviction during scheduling
- **Validation limit:** vLLM enforces `swap_space * tp_size < 0.7 * total_cpu_memory`
- For Node 1 (224 GB, TP=4): max swap_space = 0.7 * 224 / 4 = **39.2 GiB per GPU**
- At 0.4 * total CPU memory, vLLM logs a warning
- Latency: PCIe 4.0 async memcpy, ~25 GB/s practical. A full 32K sequence (8 GB bf16) swaps in ~320ms
- **Current default on Node 1:** 4 * 4 = 16 GiB total. Increasing to 16 * 4 = 64 GiB is safe and beneficial.

**2. `--kv-offloading-size N` (GiB, default: None/disabled)** -- persistent KV cache tier
- NEW feature in recent vLLM (v0.7+). Total buffer size across all TP ranks.
- Backends: `native` (OffloadingConnector) or `lmcache` (LMCache integration)
- Native backend: `kv_connector = "OffloadingConnector"`, passes `cpu_bytes_to_use` config
- LMCache backend: `kv_connector = "LMCacheConnectorV1"`, divides size across TP ranks
- Unlike swap_space, this EXTENDS total KV capacity by treating CPU RAM as a slower tier
- Works synergistically with prefix caching: cached prefixes stored in CPU can be shared across requests
- **Critical: check NGC image compatibility.** NGC vllm:25.12-py3 (v0.11.1) may predate this feature.

**3. `--cpu-offload-gb N` (GiB, default: 0)** -- model WEIGHT offloading
- Offloads model weights, NOT KV cache, from GPU to CPU
- Part of model transferred CPU <-> GPU on EVERY forward pass
- Useful only when model is too large for VRAM. NOT useful for Qwen3-32B-AWQ (fits in 64 GB TP=4).
- `cpu_offload_params` field allows selective offloading by parameter name segments

**4. LMCache integration** -- external KV cache management
- Tiered storage: GPU -> CPU RAM -> Disk -> S3
- "3-10x delay savings" by reusing KV caches across requests
- Supports CPU KV cache offloading, disaggregated prefill, peer-to-peer sharing
- Apache 2.0 licensed, 6.9k GitHub stars

Source: vLLM `vllm/config/cache.py` and `vllm/config/vllm.py` (verified 2026-02-25)

### SGLang HiCache (Hierarchical Cache)

SGLang has a sophisticated 3-tier hierarchical KV cache system:

```bash
--enable-hierarchical-cache      # Enable HiCache
--hicache-ratio 2                # Host RAM = 2x GPU KV cache
--hicache-size 100               # Or set explicit GB (overrides ratio)
--hicache-io-backend kernel      # CPU<->GPU transfer backend
--hicache-write-policy write_through   # GPU->CPU write policy
--hicache-storage-backend file   # L3 tier: file, mooncake, hf3fs, nixl
```

Features:
- L1 (GPU) -> L2 (CPU RAM) -> L3 (disk/network storage)
- Async prefetching with configurable policies (best_effort, wait_complete, timeout)
- Page-based management (configurable page size)
- Multiple memory layouts: layer_first, page_first, page_first_direct
- Designed for multi-turn conversation KV reuse and disaggregated prefill/decode

### KV Cache Sizing Math

For Qwen3-32B-AWQ (current primary model):
- 64 layers, 8 KV heads (GQA), 128 head_dim, FP16 KV
- KV per token = 2 (K+V) x 64 layers x 8 heads x 128 dim x 2 bytes = 262,144 bytes = **256 KB/token**
- 32K context = 8 GB per sequence
- 10 concurrent 32K sequences = **80 GB KV cache** (exceeds 64 GB total VRAM on Foundry 5070 Ti array)

**Impact of offloading:**

| Scenario | KV on GPU | KV on CPU | Max Concurrent 32K Seqs | VRAM Saved |
|----------|-----------|-----------|------------------------|------------|
| No offloading | 100% | 0% | ~5-6 (limited by VRAM) | 0 |
| 50% offload | 50% | 50% | ~10-12 | ~40 GB |
| 80% offload | 20% | 80% | ~25-30 | ~64 GB |

With 80 GB CPU KV buffer on Foundry: could support **~10 additional 32K-context sequences** that would otherwise not fit.

### Performance Impact

KV offloading adds latency for CPU<->GPU transfers:
- PCIe 4.0 x16: ~25 GB/s practical
- KV fetch per token per layer: a few KB -- negligible individually
- But multiplied across layers and batch: can add 1-5ms per step
- For throughput-oriented workloads: acceptable tradeoff
- For ultra-low-latency single-request: noticeable

### Sources

- [vLLM CacheConfig Documentation](https://docs.vllm.ai/en/latest/api/vllm/config/cache_q=)
- [vLLM KV Offloading CLI Args](https://docs.vllm.ai/en/latest/cli/bench/throughput)
- [SGLang HiCache Design](https://docs.sglang.io/advanced_features/hicache_design)
- [SGLang HiCache Best Practices](https://docs.sglang.io/_sources/advanced_features/hicache_best_practices)
- [LMCache GitHub](https://github.com/LMCache/LMCache)

---

## Strategy 3: Model Weight Offloading to CPU RAM (vLLM cpu_offload_gb)

### What It Does

vLLM's `--cpu-offload-gb N` parameter offloads model weights to CPU RAM, effectively "expanding" GPU memory. Each forward pass transfers the offloaded weights from CPU to GPU.

### Configuration

```bash
vllm serve model --cpu-offload-gb 10  # Offload 10 GB of weights to CPU per GPU
```

### How It Works

From vLLM docs: "This argument can be seen as a virtual way to increase the GPU memory size. For example, if you have one 24 GB GPU and set this to 10, virtually you can think of it as a 34 GB GPU. Then you can load a 13B model with BF16 weight, which requires at least 26GB GPU memory."

**Critical caveat:** "This requires fast CPU-GPU interconnect, as part of the model is loaded from CPU memory to GPU memory on the fly in each model forward pass."

### Performance Impact Analysis

| Offload | Transfer/step | Latency Overhead | Use Case |
|---------|--------------|------------------|----------|
| 2 GB/GPU | ~80ms @ 25 GB/s | Minor | Worth it for fitting larger model |
| 5 GB/GPU | ~200ms @ 25 GB/s | Moderate | Acceptable for throughput workloads |
| 10 GB/GPU | ~400ms @ 25 GB/s | Significant | Only if no other option |
| 20 GB/GPU | ~800ms @ 25 GB/s | Severe | Defeats purpose for interactive use |

**Recommendation:** Keep cpu_offload_gb small (2-5 GB per GPU). It's most useful for fitting a model that's slightly too large for VRAM, not for general RAM utilization.

### What It Enables

- Load a 70B FP16 model on 4x 16GB GPUs (64 GB VRAM + 20 GB CPU offload = 84 GB "virtual")
- Serve larger quantization formats (FP8 vs Q4) by offloading the extra weight bytes
- Not applicable to current Qwen3-32B-AWQ (already fits comfortably in 64 GB)

### Sources

- [vLLM LLM Class API](https://docs.vllm.ai/en/latest/api/vllm/entrypoints/llm)
- [vLLM CacheConfig](https://docs.vllm.ai/en/latest/api/vllm/config/cache_q=)

---

## Strategy 4: tmpfs Model Weight Caching (RAM Disk)

### What It Does

Mount a tmpfs filesystem backed by RAM to cache model weights. Models loaded from tmpfs benefit from ~150 GB/s bandwidth vs ~1 GB/s over NFS (10GbE).

### Current State

Models are served from NFS: `/mnt/vault/models/` mounted via 10GbE from VAULT.

| Source | Read Bandwidth | 18 GB Model Load Time |
|--------|---------------|----------------------|
| NFS (10GbE) | ~1 GB/s | ~18 seconds |
| NVMe (local) | ~5-7 GB/s | ~2.5-3.5 seconds |
| tmpfs (RAM) | ~100-150 GB/s | **<0.2 seconds** |

### Implementation

```bash
# On Foundry (Node 1)
sudo mount -t tmpfs -o size=60G tmpfs /mnt/ram-models

# Pre-populate with frequently used models
cp /mnt/vault/models/vllm/Qwen3-32B-AWQ/* /mnt/ram-models/qwen3-32b-awq/
cp /mnt/vault/models/embedding/gte-large-en-v1.5/* /mnt/ram-models/embedding/
```

Or via Ansible/fstab:
```
tmpfs /mnt/ram-models tmpfs size=60G,noatime 0 0
```

### Why This Matters

1. **GPU Orchestrator model hot-swap:** When the GPU orchestrator swaps models (e.g., switching from Qwen3-32B to a coding model), load time drops from 18s (NFS) to <0.2s (tmpfs).
2. **vLLM startup time:** vLLM spends significant time loading model weights. From tmpfs, the CPU->GPU transfer at PCIe speeds (~25 GB/s per GPU) becomes the bottleneck, not storage.
3. **Multiple model staging:** Keep 2-3 models warm in RAM, swap them into VRAM on demand.

### RAM Cost by Model

| Model | Size on Disk | tmpfs Cost |
|-------|-------------|-----------|
| Qwen3-32B-AWQ | ~18 GB | 18 GB |
| GTE-Large embedding | ~0.6 GB | 0.6 GB |
| Whisper large-v3 | ~1.5 GB | 1.5 GB |
| Qwen3MoE 30B-A3B Q4 | ~17 GB | 17 GB |
| Flux Dev FP8 | ~12 GB | 12 GB |
| Total (common models) | ~50 GB | **50 GB** |

### Sources

- Linux tmpfs documentation (kernel.org)
- NFS 10GbE throughput measured empirically

---

## Strategy 5: CPU-Only Inference

### What It Does

Run LLM inference entirely on CPU, using RAM for model weights and KV cache. No GPU required.

### vLLM CPU Backend

vLLM supports CPU-only inference:
- Requires building with `VLLM_TARGET_DEVICE=cpu`
- Supports AVX-512, BF16, FP16, FP32
- Continuous batching works on CPU
- OpenAI-compatible API same as GPU version
- Performance tuning: block-size multiples of 32, thread binding
- Limitations: No MLA, no sparse attention

### llama.cpp CPU Performance

llama.cpp with CPU-only inference using quantized models:
- AVX-512 kernels support K-quants, I-quants, Flash Attention, MoE
- `--mlock` keeps model locked in RAM (prevents swap)
- `--threads N` controls parallelism

### Estimated CPU Performance

Decode speed for autoregressive LLMs is approximately: `bandwidth / (model_size_bytes)`

| Model | Quant | Size | Foundry (150 GB/s) | Workshop (130 GB/s) | VAULT (65 GB/s) |
|-------|-------|------|--------------------|---------------------|-----------------|
| Llama 3.1 8B | Q4_K_M | 4.9 GB | ~30 tok/s | ~26 tok/s | ~13 tok/s |
| Qwen2.5 14B | Q4_K_M | 8.5 GB | ~17 tok/s | ~15 tok/s | ~7 tok/s |
| Qwen2.5 32B | Q4_K_M | 18 GB | ~8 tok/s | ~7 tok/s | ~3.5 tok/s |
| Phi-4 14B | Q4_K_M | 8 GB | ~18 tok/s | ~16 tok/s | ~8 tok/s |

**These are rough estimates.** Actual performance depends on model architecture, quantization efficiency, batch size, and memory access patterns. Prefill is typically much faster (compute-bound, scales with core count).

### Use Cases for Athanor

1. **Foundry background model:** Run a 7-8B model purely on CPU for low-priority agent tasks while GPUs handle the main workload
2. **VAULT utility inference:** Small model for local media metadata tagging, no GPU needed
3. **Draft model for speculative decoding:** Small CPU model generates candidates, GPU model verifies (see Strategy 7)

### Sources

- [vLLM CPU Installation](https://docs.vllm.ai/en/latest/getting_started/installation/cpu)
- [vLLM CPU Platform](https://docs.vllm.ai/en/latest/api/vllm/platforms/cpu)
- [llama.cpp Feature Matrix](https://github.com/ggml-org/llama.cpp/wiki/Feature-matrix)

---

## Strategy 6: llama.cpp Unified Memory (GPU+CPU Hybrid)

### What It Does

llama.cpp can split model layers between GPU and CPU, and also provides a unified memory mode where VRAM overflow spills to system RAM automatically.

### Configuration

```bash
# Offload 40 of 64 layers to GPU, rest stay in CPU RAM
./llama-cli -m model.gguf -ngl 40

# Enable unified memory (CUDA): automatic spill to system RAM
export GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
./llama-cli -m model.gguf -ngl 999  # Try to offload everything, overflow to RAM
```

### Layer Offloading Performance

Each layer on GPU runs at GPU speed; each layer on CPU runs at CPU speed. The total throughput is a weighted average:

- 100% GPU layers: maximum speed
- 50% GPU / 50% CPU: roughly 2-3x slower than full GPU (CPU layers dominate)
- 100% CPU: slowest (see Strategy 5 estimates)

The `-ngl` parameter allows fine-tuning the split. More GPU layers = faster, but more VRAM used.

### When to Use

- Testing models that are slightly too large for VRAM
- Quick experiments before committing to quantization choices
- Not for production serving (no continuous batching in llama.cpp)

### Sources

- [llama.cpp build documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)
- [llama.cpp performance tips](https://github.com/ggml-org/llama.cpp/blob/master/docs/development/token_generation_performance_tips.md)

---

## Strategy 7: Speculative Decoding with CPU Draft Model

### What It Does

A small "draft" model generates N candidate tokens quickly, then the large "target" model verifies them in a single forward pass. If the draft model is accurate, this yields up to Nx speedup since verification is parallel while generation is sequential.

### vLLM Support

vLLM supports multiple speculative decoding methods:
- **Standard draft models:** e.g., `facebook/opt-125m` as draft for a larger model
- **N-gram matching:** `speculative_model="[ngram]"` -- no separate model needed
- **MLP speculators:** IBM's accelerator models (e.g., `llama3-70b-accelerator`)
- **EAGLE models:** Extrapolation-based drafts

**Critical limitations (current state):**
- "Speculative decoding in vLLM is not yet optimized"
- Draft model must run with TP=1 (no tensor parallelism for draft)
- Incompatible with pipeline parallelism
- **No explicit CPU draft model support** -- draft runs on GPU

### CPU Draft Model Opportunity

In theory, a small draft model (1-3B parameters, Q4) could run entirely on CPU RAM:
- 1.5B Q4 model: ~1 GB RAM, ~100+ tok/s on EPYC 7663
- Draft quality matters -- higher acceptance rate = more speedup
- CPU draft avoids consuming any GPU VRAM

**Current status:** Neither vLLM nor SGLang explicitly support CPU-based draft models. This would require custom implementation or waiting for upstream support.

### Sources

- [vLLM Speculative Decoding Docs](https://docs.vllm.ai/en/stable/features/spec_decode.html)

---

## Strategy 8: In-Memory Database and Cache Expansion

### Qdrant In-Memory Mode

Current state: Qdrant uses mmap (disk-backed, OS caches in RAM).

Full in-memory mode: `storage: InMemory` in collection config.

Current collections are small (~5 MB vectors for knowledge, conversations, activity, preferences). Already effectively in RAM via OS cache. Explicit in-memory mode would guarantee zero-disk-latency but offers minimal improvement at current scale.

**When it matters:** If Qdrant grows to millions of points (e.g., full document ingestion, comprehensive conversation history), explicit RAM allocation prevents cache eviction.

### Redis Expansion

Current: 512 MB maxmemory on VAULT.

Potential uses with more RAM:
- **Semantic response caching:** Cache LLM responses keyed by embedding similarity. Hit rate depends on query distribution.
- **Full conversation history:** Keep all conversation turns in Redis (not just recent) for instant retrieval.
- **GWT workspace expansion:** Larger capacity for workspace items, agent state.
- **Model metadata cache:** Precomputed model configs, tokenizer data.

Estimate: 2-4 GB Redis would be generous for current workloads. Could grow to 10-20 GB for semantic caching.

### Neo4j Heap Expansion

Current: Default heap (likely 1 GB).

With 43 relationships and a small graph, heap is not a bottleneck. But if the knowledge graph grows to thousands of nodes and complex queries: expanding heap to 4-8 GB helps.

### Sources

- [Qdrant Storage Configuration](https://qdrant.tech/documentation/concepts/storage/)
- Redis maxmemory documentation

---

## Strategy 9: NUMA-Aware Inference (Foundry)

### EPYC 7663 NUMA Topology

The EPYC 7663 (Milan/Zen 3) can be configured for different NPS (NUMA-Per-Socket) modes in BIOS:
- **NPS1:** 1 NUMA domain. All 56 cores see all 224 GB uniformly. Simplest.
- **NPS2:** 2 NUMA domains. Each sees half the cores and half the RAM. Cross-domain access is slower.
- **NPS4:** 4 NUMA domains. Most granular, highest local bandwidth.

### Impact on AI Workloads

| NPS Mode | Pros | Cons | Best For |
|----------|------|------|----------|
| NPS1 | Simple, no NUMA binding needed | Slightly lower local BW | vLLM (multi-GPU TP) |
| NPS2 | Higher local BW per domain | Must bind processes | KTransformers (NUMA-aware) |
| NPS4 | Highest local BW | Complex binding | Expert offloading with tight locality |

### Recommendations

- **For vLLM with TP=4:** NPS1 is best. vLLM manages GPU memory; CPU RAM is used for swap/offload, not compute.
- **For KTransformers:** NPS2 with NUMA binding (`numactl -N 0 -m 0`) gives highest bandwidth per NUMA domain.
- **Check current setting:** `numactl --hardware` on Foundry.

### GPU-to-NUMA Affinity

Each PCIe slot on EPYC connects to a specific NUMA domain. For optimal CPU offloading:

```bash
# Check GPU NUMA affinity
cat /sys/bus/pci/devices/0000:XX:00.0/numa_node
```

When using KV offloading, bind the vLLM process to the NUMA node closest to the GPUs.

### Sources

- AMD EPYC 7003 Series Tuning Guide
- KTransformers NUMA documentation

---

## Strategy 10: Swap and Overflow (NVMe + zswap)

### zswap (Compressed Swap in RAM)

zswap compresses pages before writing to swap, effectively increasing usable RAM:

```bash
echo 1 > /sys/module/zswap/parameters/enabled
echo lz4 > /sys/module/zswap/parameters/compressor
echo 20 > /sys/module/zswap/parameters/max_pool_percent  # Use up to 20% of RAM
```

**Impact:** With LLM weights (low entropy quantized data), compression ratios are poor (~1.1-1.3x). Not useful for model weights. More useful for general OS pages.

### NVMe Swap for Model Overflow

NVMe swap can catch models that slightly exceed RAM:

| Tier | Bandwidth | Latency | vs VRAM |
|------|-----------|---------|---------|
| GPU VRAM (HBM/GDDR6X) | ~1000 GB/s | ~100 ns | baseline |
| System RAM (DDR4/DDR5) | 65-165 GB/s | ~80-100 ns | 6-15x slower |
| NVMe SSD | 5-7 GB/s | ~10-100 us | 150-200x slower |
| SATA SSD | ~0.5 GB/s | ~50-100 us | 2000x slower |

**Performance cliff is steep.** RAM -> NVMe is a 20-30x bandwidth drop. Any LLM inference that regularly hits NVMe swap will be impractically slow.

### Recommendation

- Use NVMe swap only as a safety net (prevent OOM kills), not as a performance strategy
- Set `vm.swappiness=10` on inference nodes (minimize swap unless truly OOM)
- zswap on VAULT (many small containers) may help with general memory pressure

### Sources

- Linux kernel zswap documentation
- NVMe bandwidth specifications

---

## Strategy 11: mmap Model Loading

### What It Does

Memory-mapped file access (`mmap`) lets the OS manage model weight loading. Pages are loaded on demand and cached in RAM. The OS evicts pages under memory pressure.

### Current Usage

- **llama.cpp:** Uses mmap by default for GGUF files. Model pages loaded on demand, cached in available RAM.
- **vLLM:** Loads weights into GPU VRAM directly. CPU-side mmap not relevant.
- **Qdrant:** Uses mmap for vector storage by default.

### Implications

With 190 GB free RAM on Foundry, the OS will aggressively cache mmap'd files. If you run llama.cpp with a 100 GB GGUF model, the OS will cache as much as possible in free RAM.

**`--mlock`** forces the entire model into RAM immediately (no page faults during inference). Costs startup time but eliminates latency spikes.

**`--no-mmap`** loads the entire model into private memory. More RAM used but eliminates the complexity of OS page management.

For production llama.cpp workloads: use `--mlock` to prevent the OS from evicting model pages.

### Sources

- [llama.cpp Performance Tuning](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md)

---

## Strategy 12: Huge Pages for vLLM and Inference

### Does vLLM Support Huge Pages?

**No.** A search of the entire vLLM codebase (all branches, 2026-02-25) reveals zero references to `MAP_HUGETLB`, `hugepage`, or `huge_page`. vLLM allocates GPU memory through PyTorch's CUDA allocator and CPU memory through standard malloc/mmap. Neither explicitly requests huge pages.

### Transparent Huge Pages (THP)

Linux's THP can automatically promote 4 KB pages to 2 MB pages for large contiguous allocations without application changes:

```bash
# Check current THP setting
cat /sys/kernel/mm/transparent_hugepage/enabled
# [always] madvise never

# Ensure THP is enabled
echo always > /sys/kernel/mm/transparent_hugepage/enabled
echo always > /sys/kernel/mm/transparent_hugepage/defrag
```

**TLB pressure analysis for large KV offloading:**
- 100 GB of KV cache with 4 KB pages: 26.2 million page table entries (~100 MB of page tables)
- 100 GB with 2 MB THP: 51,200 entries (~0.2 MB of page tables) -- 512x reduction
- THP can provide ~2-5% throughput improvement for memory-intensive workloads

### Explicit Huge Pages

Pre-allocating explicit 2 MB or 1 GB huge pages is possible but NOT recommended:

```bash
# Allocate 51200 2MB pages (100 GB) -- NOT recommended
echo 51200 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
```

**Why not:** Explicit huge pages cannot be swapped or reclaimed. They permanently reserve RAM even if unused. The RAM is better allocated flexibly between tmpfs, KV offloading, and swap space. THP provides most of the TLB benefits without the inflexibility.

### Recommendation

1. **Enable THP** on Node 1 and Node 2 -- free ~2-5% improvement
2. **Do NOT use explicit huge pages** unless `perf stat -e dTLB-load-misses` shows significant TLB pressure after deploying KV offloading
3. NUMA-aware THP: on EPYC, THP will automatically allocate from the local NUMA node

Source: Linux hugepages documentation at https://www.kernel.org/doc/html/latest/admin-guide/mm/hugetlbpage.html

---

## Strategy 13: Kernel Tuning for Inference Workloads

### Page Cache and VM Tunings

**Node 1 (Foundry) -- inference-optimized:**
```bash
# /etc/sysctl.d/99-athanor-inference.conf

# Minimize swappiness -- keep inference data in RAM
vm.swappiness = 10                     # Default 60; lower = prefer dropping cache over swapping

# Optimize for large memory allocations (vLLM, PyTorch)
vm.overcommit_memory = 1               # Always allow overcommit (PyTorch needs this)
vm.max_map_count = 1048576             # Increase for large mmap regions (default: 65530)

# NUMA -- don't reclaim from local node for remote allocations
vm.zone_reclaim_mode = 0               # Default on most distros; keep 0 for EPYC

# Write coalescing for NFS
vm.dirty_ratio = 40                    # % of RAM for dirty pages before sync (default: 20)
vm.dirty_background_ratio = 10         # % of RAM before background writeback (default: 10)
```

**VAULT -- storage/NFS-optimized:**
```bash
# /etc/sysctl.d/99-athanor-vault.conf
vm.swappiness = 1                      # Almost never swap; RAM is precious for file cache
vm.vfs_cache_pressure = 50             # Lower = keep inode/dentry cache longer (default: 100)
vm.dirty_ratio = 60                    # Let NFS writes accumulate in RAM
vm.dirty_background_ratio = 20
```

### NFS Client Tuning

For model loading over NFS on Node 1 and Node 2:

```bash
# Increase read-ahead buffer (default 128 KB)
echo 16384 > /sys/block/sda/queue/read_ahead_kb    # 16 MB read-ahead

# NFS mount options in /etc/fstab
192.168.1.203:/mnt/user/models /mnt/vault/models nfs rsize=1048576,wsize=1048576,async,noatime 0 0
```

The `rsize=1048576` (1 MB) maximizes NFS transfer unit. `noatime` prevents access time writes on reads.

### vLLM-Specific: safetensors_load_strategy

This is a critical but non-obvious vLLM parameter discovered in `vllm/config/load.py`:

```bash
--safetensors-load-strategy lazy    # Default: mmap from file. Good for local NVMe. BAD for NFS.
--safetensors-load-strategy eager   # Read entire file into CPU RAM first. GOOD for NFS.
```

From vLLM source: "eager: The entire file is read into CPU memory upfront before loading. This is recommended for models on network filesystems (e.g., Lustre, NFS) as it avoids inefficient random reads, significantly speeding up model initialization."

**When models are on NFS:** Use `--safetensors-load-strategy eager`
**When models are on tmpfs:** Use `--safetensors-load-strategy lazy` (mmap from RAM is ideal)

This single flag change can reduce NFS model load time by 2-5x by converting random page faults into sequential reads.

Source: vLLM `vllm/config/load.py` (LoadConfig class, verified 2026-02-25)

### Page Cache Prewarming

Instead of or in addition to tmpfs, prewarm the page cache:

```bash
# Read entire model into page cache without tmpfs
cat /mnt/vault/models/Qwen3-32B-AWQ/*.safetensors > /dev/null

# Or more efficiently with vmtouch
vmtouch -t /mnt/vault/models/Qwen3-32B-AWQ/
vmtouch -v /mnt/vault/models/Qwen3-32B-AWQ/  # Verify cache residency
```

With 200+ GB free RAM, the 17 GB model stays cached indefinitely after first read. Subsequent vLLM restarts load at RAM speed (~50+ GB/s) rather than NFS speed (~1.1 GB/s). The difference vs tmpfs: page cache CAN be evicted under memory pressure; tmpfs cannot.

Source: vmtouch at https://github.com/hoytech/vmtouch

---

## Strategies NOT Currently Viable

### Speculative Decoding with CPU Draft (Strategy 7)
Not supported in vLLM or SGLang. Would need custom implementation. Worth revisiting when upstream adds CPU device support for draft models.

### RWKV / Mamba CPU Inference
Linear-complexity models (RWKV, Mamba) are theoretically more CPU-friendly due to lack of quadratic attention. However:
- Model quality still behind transformer MoE models for general tasks
- vLLM/SGLang support is limited
- Would need separate serving infrastructure
- Not worth the complexity for Athanor today

### Intel AMX Acceleration
None of Athanor's CPUs support AMX (requires Intel Sapphire Rapids or newer Xeon). The EPYC has AVX-512, and the Zen 5 chips have AVX-512-BF16, but AMX's 8x speedup over AVX-512 for matrix ops is unavailable.

### Cross-Node RAM Pooling
No practical way to pool RAM across nodes for per-token inference operations:

| Technology | Bandwidth | Latency | vs Local DDR4 |
|-----------|-----------|---------|---------------|
| 10GbE (current) | ~1.1 GB/s | ~100 us | ~150x slower |
| RDMA/RoCE v2 | ~1.1 GB/s | ~5-10 us | ~150x BW / ~50x latency |
| InfiniBand EDR (target) | ~12 GB/s | ~1 us | ~14x BW / ~10x latency |
| Local DDR4 (Node 1) | ~170 GB/s | ~100 ns | baseline |

Even InfiniBand EDR at 12 GB/s is 14x slower than local RAM. For KV cache access (millions of bytes per attention step), this adds unacceptable latency.

**What DOES work over network:**
- Pipeline parallelism (small activations between stages, amortized over compute)
- LMCache cross-instance KV sharing (for reuse, not real-time access)
- Redis shared state (agent state, orchestration -- already deployed)

The exo project (https://github.com/exo-explore/exo) enables distributed inference but currently has CPU-only on Linux (GPU acceleration is macOS/MLX only). Not suitable for our Linux GPU cluster.

---

## Recommended RAM Allocation Plan

### Foundry (224 GB total, ~190 GB available)

| Allocation | Size | Purpose | Priority |
|-----------|------|---------|----------|
| vLLM KV cache offloading | **80 GB** | `--kv-offloading-size 80` -- extend effective KV cache for higher concurrency/longer contexts | P0: Immediate |
| tmpfs model cache | **50 GB** | `/mnt/ram-models` -- stage primary + hot-swap models for fast GPU orchestrator swaps | P0: Immediate |
| vLLM cpu_offload_gb | **20 GB** | 5 GB per GPU x 4 -- minor VRAM extension for fitting larger quantizations | P1: When needed |
| KTransformers MoE workspace | **30 GB** | Reserved for MoE expert computation when running Qwen3MoE or Mixtral | P1: When MoE models deployed |
| Headroom | **10 GB** | OS/Docker growth, burst allocations | - |

**Note:** KV offloading and KTransformers are mutually exclusive workloads (different serving modes). The 80 GB KV offload applies when running vLLM with dense models. The 30 GB KTransformers workspace applies when running MoE models. Total real peak use: ~160 GB.

**Hardware note:** Channel H (8th memory channel) is empty. Populating it with a matching 32 GB DDR4-3200 ECC RDIMM (~$40-60 used) would increase total RAM to 256 GB and restore full 8-channel bandwidth (204.8 GB/s theoretical vs current ~179 GB/s). This is the cheapest performance upgrade for ALL CPU-side RAM strategies: KV offloading throughput, CPU inference speed, and page cache efficiency all improve by ~12.5%.

### Workshop (128 GB total, ~108 GB available)

| Allocation | Size | Purpose | Priority |
|-----------|------|---------|----------|
| vLLM/SGLang KV cache offloading | **40 GB** | KV overflow for 5090/5060 Ti workloads | P0: Immediate |
| tmpfs model cache | **30 GB** | ComfyUI models (Flux, Wan2.x), vLLM hot-swap models | P0: Immediate |
| KTransformers MoE workspace | **20 GB** | Qwen3MoE 30B-A3B on CPU + 5090 GPU | P1: When MoE deployed |
| vLLM cpu_offload_gb | **10 GB** | 5 GB per GPU x 2 | P2: When needed |
| Headroom | **8 GB** | OS/Docker growth | - |

### VAULT (128 GB total, ~98 GB available)

| Allocation | Size | Purpose | Priority |
|-----------|------|---------|----------|
| Redis expansion | **8 GB** | Semantic caching, expanded GWT workspace, conversation history | P1: Incremental |
| Qdrant memory | **8 GB** | Ensure vector collections stay resident as they grow | P1: Incremental |
| Neo4j heap | **4 GB** | Knowledge graph query performance | P2: When graph grows |
| CPU inference (llama.cpp) | **30 GB** | Small utility model (7-8B Q4) for media tagging, low-priority tasks | P2: Experimental |
| tmpfs model cache | **20 GB** | Pre-stage models for fast VAULT-local access | P2: When needed |
| zswap pool | **10 GB** | Compressed swap for 13+ containers | P1: Easy win |
| Headroom | **18 GB** | Container growth, burst | - |

### DEV (64 GB total, ~44 GB available)

| Allocation | Size | Purpose | Priority |
|-----------|------|---------|----------|
| WSL2 allocation | **32 GB** | Development environment | Existing |
| llama.cpp model testing | **8 GB** | Quick model evaluation without starting vLLM | P2: Ad hoc |
| Headroom | **4 GB** | Development flexibility | - |

### Total RAM Utilization Summary

| Node | Total | Allocated | Utilization |
|------|-------|-----------|-------------|
| Foundry | 224 GB | ~190 GB | **85%** (up from ~13%) |
| Workshop | 128 GB | ~108 GB | **84%** (up from ~16%) |
| VAULT | 128 GB | ~98 GB | **77%** (up from ~23%) |
| DEV | 64 GB | ~44 GB | **69%** (up from ~31%) |
| **TOTAL** | **544 GB** | **~440 GB** | **81%** (up from ~18%) |

---

## Concrete vLLM Configuration (Ready to Deploy)

### Current vLLM Flags (Node 1)

```bash
vllm serve Qwen/Qwen3-32B-AWQ \
  --tensor-parallel-size 4 \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 128
```

### Proposed vLLM Flags (Node 1, RAM-Optimized)

```bash
vllm serve /mnt/ram-models/Qwen3-32B-AWQ \
  --tensor-parallel-size 4 \
  --quantization awq \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 128 \
  --max-model-len 32768 \
  --swap-space 16 \
  --kv-offloading-size 80 \
  --kv-offloading-backend native \
  --enable-prefix-caching \
  --safetensors-load-strategy lazy \
  --cache-dtype fp8
```

**What changes and why:**
| Flag | Old | New | Impact |
|------|-----|-----|--------|
| Model path | NFS | tmpfs | ~100x faster model loading |
| safetensors_load_strategy | (default: lazy) | lazy (but on tmpfs) | Optimal for RAM-backed storage |
| swap_space | 4 (default) | 16 | 4x preemption buffer (64 GB total) |
| kv_offloading_size | None | 80 | 80 GB CPU KV cache tier |
| cache_dtype | auto (bf16) | fp8 | 2x KV cache capacity |
| gpu_memory_utilization | 0.85 | 0.90 | More VRAM for KV cache |
| prefix_caching | (default: True) | True (explicit) | Confirm prefix caching active |

**Expected Node 1 RAM budget:**
| Component | GB |
|-----------|------|
| System + Docker | 10 |
| tmpfs (/mnt/ram-models) | 25 |
| vLLM swap (16 * 4 GPUs) | 64 |
| vLLM KV offloading | 80 |
| Page cache + buffers | 45 |
| **Total** | **224** |

**Expected capacity with FP8 KV cache:**
- GPU KV: ~36 GB / 128 KB per token = ~281K tokens
- CPU KV: 80 GB / 128 KB per token = ~625K tokens
- Swap: 64 GB / 128 KB per token = ~500K tokens (preemption buffer)
- **Total active: ~906K tokens** (vs ~140K today with bf16 GPU-only)
- Practical: ~28 concurrent 32K-context conversations (vs ~4 today)

**CRITICAL BLOCKER:** Verify `--kv-offloading-size` is supported in the current NGC image (v0.11.1). If not, this flag will error and must wait for NGC image upgrade. The `--swap-space`, `--cache-dtype fp8`, and `--safetensors-load-strategy` flags should work on v0.11.1+.

---

## Implementation Priority

### Phase 0: Zero-risk config changes (30 minutes)

1. **`--safetensors-load-strategy eager`** on current NFS-backed vLLM -- 2-5x faster model load
2. **`--swap-space 16`** on vLLM -- increase preemption buffer from 16 GB to 64 GB total
3. **Kernel sysctl tunings** on Node 1, Node 2, VAULT (see Strategy 13)
4. **Enable THP** on Node 1 and Node 2 (see Strategy 12)
5. **Redis maxmemory increase** -- change from 512 MB to 4 GB on VAULT

### Phase 1: tmpfs and model loading (1 hour)

6. **tmpfs mount on Foundry** -- `/mnt/ram-models`, 25 GB, Ansible role
7. **Model preload script** -- rsync from NFS at boot
8. **Switch vLLM model path** to tmpfs + `--safetensors-load-strategy lazy`
9. **Check NUMA topology** on Foundry (`numactl --hardware`)

### Phase 2: KV cache offloading (requires NGC image check)

10. **Verify NGC image version** supports `--kv-offloading-size`
11. **Deploy `--kv-offloading-size 80`** on Node 1 vLLM
12. **Test `--cache-dtype fp8`** for 2x KV capacity
13. **Benchmark** concurrent request capacity before/after

### Phase 3: New capabilities

14. **KTransformers deployment** -- Docker container on Foundry for MoE model serving
15. **SGLang HiCache evaluation** -- if migrating to SGLang, this is a major advantage
16. **VAULT CPU inference** -- llama.cpp container for utility model
17. **llama.cpp on Node 1** -- Qwen3-8B Q4_K_M for background agent tasks

### Phase 4: Optimization

18. **NUMA tuning** on Foundry based on workload profiling
19. **LMCache evaluation** for cross-request KV cache sharing
20. **Channel H population** -- 1x 32 GB DDR4-3200 ECC RDIMM (~$40-60) for 12.5% bandwidth gain
21. **Speculative decoding** -- revisit when vLLM/SGLang mature CPU draft support

---

## Open Questions

1. **What NPS mode is Foundry currently running?** Check BIOS or `numactl --hardware`. This affects all CPU-side strategies.
2. **DDR5 speed on Workshop and VAULT?** CLAUDE.md says DDR5 but not speed. XMP/EXPO profile matters for bandwidth. Node 2 currently at 4800 MT/s due to missing EXPO, reducing effective bandwidth by ~14% (153.6 vs 179.2 GB/s).
3. **Would Qwen3MoE 235B-A22 via KTransformers outperform Qwen3-32B-AWQ on vLLM?** The 235B model with 22B active parameters may produce better quality than a dense 32B model, at comparable speed on KTransformers. This needs benchmarking.
4. **SGLang HiCache vs vLLM native KV offloading:** Which performs better for Athanor's agent workloads (many concurrent short conversations)? Needs A/B testing.
5. **Is the vLLM `--kv-offloading-size` feature in the NGC image?** NGC vllm:25.12-py3 is v0.11.1. The `kv_offloading_size` field exists in recent vLLM main branch (`vllm/config/cache.py`). Run `vllm serve --help | grep kv-offloading` inside the container to check. If absent, this is blocked on NGC image upgrade (same blocker as sleep mode).
6. **Channel H memory module:** What RDIMM model/speed are the existing 7 DIMMs on Node 1? Need an exact match (vendor, speed, rank) for the 8th channel. Run `dmidecode -t memory` on Foundry.
7. **FP8 KV cache quality impact:** Does `--cache-dtype fp8` cause noticeable quality degradation for Qwen3-32B-AWQ? Test with agent conversation quality benchmarks before deploying to production.
8. **Node 1 EPYC bandwidth with 7/8 channels:** Is the 12.5% bandwidth loss from the empty channel confirmed, or does the memory controller interleave differently? Run `mlc` (Intel Memory Latency Checker) or `stream` benchmark on Foundry to measure actual bandwidth.

---

## Sources (Complete)

**KTransformers:**
- [GitHub Repository](https://github.com/kvcache-ai/ktransformers) -- README, benchmarks, model support
- [DeepSeek R1/V3 Tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepseekR1_V3_tutorial.md) -- performance numbers
- [AMX Documentation](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/AMX.md) -- Intel AMX kernel details
- [SOSP 2025 Paper](https://dl.acm.org/doi/10.1145/3731569.3764843) -- academic reference
- [SGLang Integration](https://lmsys.org/blog/2025-10-22-KTransformers/) -- kt-kernel in SGLang

**vLLM:**
- [CacheConfig Source](https://github.com/vllm-project/vllm) -- `vllm/config/cache.py`: swap_space, kv_offloading_size, cpu_offload_gb, cache_dtype (verified 2026-02-25)
- [LoadConfig Source](https://github.com/vllm-project/vllm) -- `vllm/config/load.py`: safetensors_load_strategy (lazy/eager), load_format (verified 2026-02-25)
- [VllmConfig Source](https://github.com/vllm-project/vllm) -- `vllm/config/vllm.py`: OffloadingConnector/LMCacheConnectorV1 setup (verified 2026-02-25)
- [CacheConfig API](https://docs.vllm.ai/en/latest/api/vllm/config/cache_q=) -- cpu_offload_gb, swap_space, kv_offloading_size
- [Engine Arguments](https://docs.vllm.ai/en/latest/cli/bench/throughput) -- KV offloading configuration
- [Speculative Decoding](https://docs.vllm.ai/en/stable/features/spec_decode.html) -- draft model options
- [CPU Installation](https://docs.vllm.ai/en/latest/getting_started/installation/cpu) -- CPU backend
- [CPU Platform](https://docs.vllm.ai/en/latest/api/vllm/platforms/cpu) -- CPU capabilities
- [PagedAttention Blog](https://blog.vllm.ai/2023/06/20/vllm.html) -- KV block architecture, memory waste reduction
- [PagedAttention Paper](https://arxiv.org/abs/2309.06180) -- academic reference

**SGLang:**
- [HiCache Design](https://docs.sglang.io/advanced_features/hicache_design) -- hierarchical cache architecture
- [HiCache Best Practices](https://docs.sglang.io/_sources/advanced_features/hicache_best_practices) -- configuration examples
- [Hyperparameter Tuning](https://docs.sglang.io/advanced_features/hyperparameter_tuning) -- mem_fraction_static

**llama.cpp:**
- [Feature Matrix](https://github.com/ggml-org/llama.cpp/wiki/Feature-matrix) -- CPU/GPU capabilities
- [Build Documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) -- unified memory, AVX-512 flags
- [Performance Tips](https://github.com/ggml-org/llama.cpp/blob/master/docs/development/token_generation_performance_tips.md)
- [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) -- optimized fork with CPU Flash Attention
- [llamafile tinyBLAS](https://justine.lol/matmul/) -- 2.8x faster on Zen 4 AVX-512

**LMCache:**
- [GitHub Repository](https://github.com/LMCache/LMCache) -- KV cache tiering, Apache 2.0, 6.9k stars
- Supports GPU -> CPU RAM -> Disk -> S3 tiering, cross-instance sharing

**Model References:**
- [Qwen3-32B config.json](https://huggingface.co/Qwen/Qwen3-32B/blob/main/config.json) -- 64 layers, 8 KV heads, 128 head_dim
- [Qwen3-235B-A22B model card](https://huggingface.co/Qwen/Qwen3-235B-A22B) -- 94 layers, 128 experts, 8 active
- [KV Cache Arithmetic](https://kipp.ly/transformer-inference-arithmetic/) -- bytes per token formula
- [HuggingFace MoE Blog](https://huggingface.co/blog/moe) -- MoE architecture and memory requirements

**Linux / System:**
- [Huge Pages](https://www.kernel.org/doc/html/latest/admin-guide/mm/hugetlbpage.html) -- 2MB/1GB pages, THP, configuration
- [sysctl VM](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html) -- swappiness, dirty_ratio, overcommit
- [vmtouch](https://github.com/hoytech/vmtouch) -- page cache management tool
- [exo](https://github.com/exo-explore/exo) -- distributed inference (Linux GPU not yet supported)
- AMD EPYC 7003 Series Tuning Guide -- NUMA configuration, NPS modes
