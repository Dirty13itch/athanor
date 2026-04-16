# Local Coding Models: State of the Art (February 2026)

**Date**: 2026-02-25
**Status**: Research complete
**Purpose**: Comprehensive evaluation of local coding models for Athanor's GPU fleet, updating and superseding the Feb 16 research
**Updates**: Corrects hardware inventory, adds GLM-5/Kimi K2.5 benchmarks, revises MiMo-V2-Flash scores, adds Qwen3-Coder-Next architecture details
**Related**: `2026-02-16-frontier-coding-models-local-inference.md`, `2026-02-16-tool-calling-coding-models.md`, `ADR-005-inference-engine.md`

> **UPDATE 2026-02-25 (post-publication correction):** The Qwen3.5 model family (released Feb 16-24, 2026) was missed during initial research. This is a significant oversight — **Qwen3.5-27B (dense, SWE-bench 72.4%) replaces Qwen3-Coder-Next as the primary local coding recommendation.** It achieves higher benchmark scores at 3x less VRAM. Qwen3.5-35B-A3B and Qwen3.5-122B-A10B also added. Cloud comparison updated with Claude Sonnet 4.6 and GPT-5.3-Codex. All additions marked with [2026-02-25 UPDATE] inline.

---

## Hardware Context (Corrected)

The Feb 16 research docs had incorrect GPU assignments. Corrected inventory from `docs/archive/hardware/hardware-inventory.md` and the current hardware report:

| Node | CPU | RAM | GPUs | VRAM | Bandwidth per GPU |
|------|-----|-----|------|------|-------------------|
| **Foundry (Node 1)** | EPYC 7663 56C/112T | 224 GB DDR4 ECC | 4x RTX 5070 Ti (16 GB) + 1x RTX 4090 (24 GB) | **88 GB** | 5070 Ti: 896 GB/s, 4090: 1008 GB/s |
| **Workshop (Node 2)** | TR 7960X 24C/48T | 128 GB DDR5 | 1x RTX 5090 (32 GB) + 1x RTX 5060 Ti (16 GB) | **48 GB** | 5090: 1792 GB/s, 5060 Ti: 448 GB/s |
| **Combined** | | 352 GB | 7 GPUs | **136 GB** | |

Key constraints:
- Node 1: PCIe 4.0 (32 GB/s per x16 slot). 5070 Ti is Blackwell sm_120, 4090 is Ada sm_89.
- Node 2: PCIe 5.0 (64 GB/s per x16 slot). Both GPUs are Blackwell sm_120.
- No NVLink on any GPU.
- Network between nodes: 5GbE (~1.25 GB/s sustained). InfiniBand EDR planned (~6.25 GB/s).
- Current deployment: Qwen3-32B-AWQ on Node 1 TP=4 (5070 Ti x4), Qwen3-14B FP16 on Node 2 5090.

---

## 1. Benchmark Comparison Table

All scores are SWE-bench Verified (%) unless noted. Agent scaffold varies by submission and significantly affects scores (10-20% spread for the same model is normal).

### Cloud vs Local: SWE-bench Verified

| Model | Type | Active Params | SWE-bench Verified | SWE-bench Pro | LiveCodeBench v6 | Tau2-Bench | Source |
|-------|------|---------------|-------------------|---------------|-------------------|------------|--------|
| **Claude Sonnet 4.5** | Cloud | -- | **82.0** | -- | -- | -- | Vellum Leaderboard |
| **Claude Opus 4.5** | Cloud | -- | **80.9** | -- | -- | -- | Vellum Leaderboard |
| **GPT-5.3-Codex** | Cloud | -- | **80.0** | -- | -- | -- | Vellum Leaderboard [2026-02-25 UPDATE] |
| **Claude Sonnet 4.6** | Cloud | -- | **79.6** | -- | -- | -- | Vellum Leaderboard [2026-02-25 UPDATE] |
| **GPT 5.2** | Cloud | -- | **80.0** | -- | -- | -- | Vellum Leaderboard |
| **Qwen3.5-397B-A17B** | Open (MoE) | 17B | **76.4** | -- | -- | -- | [HF model card](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) [2026-02-25 UPDATE] |
| **GPT 5.1** | Cloud | -- | **76.3** | -- | -- | -- | Vellum Leaderboard |
| **Gemini 3 Pro** | Cloud | -- | **76.2** | -- | -- | -- | Vellum Leaderboard |
| **GLM-5** | Open (MoE) | 40B | **77.8** | -- | -- | 89.7 | [HF model card](https://huggingface.co/zai-org/GLM-5) |
| **Kimi K2.5** | Open (MoE) | 32B | **76.8** | 50.7 | 85.0 | -- | [HF model card](https://huggingface.co/moonshotai/Kimi-K2.5) |
| **GLM-4.7** | Open (MoE) | 32B | **73.8** | -- | 84.9 | 87.4 | [HF model card](https://huggingface.co/zai-org/GLM-4.7), [llm-stats](https://llm-stats.com/models/glm-4.7) |
| **MiMo-V2-Flash** | Open (MoE) | 15B | **73.4** | -- | 80.6 | -- | [HF model card](https://huggingface.co/XiaomiMiMo/MiMo-V2-Flash) |
| **Qwen3.5-27B** | Open (Dense) | 27B | **72.4** | -- | -- | -- | [HF model card](https://huggingface.co/Qwen/Qwen3.5-27B) [2026-02-25 UPDATE] |
| **Qwen3.5-122B-A10B** | Open (MoE) | 10B | -- | -- | -- | -- | BFCL-V4: 72.2 [HF model card](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) [2026-02-25 UPDATE] |
| **Qwen3-Coder-Next** | Open (MoE) | 3B | **70.6** | 44.3 | -- | -- | [marc0.dev review](https://www.marc0.dev/en/blog/qwen3-coder-next-70-swe-bench-with-3b-active-params-local-ai-just-got-real-1770197534528) |
| **Qwen3.5-35B-A3B** | Open (MoE) | 3B | -- | -- | -- | TAU2 leader | [HF model card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) [2026-02-25 UPDATE] |
| **DeepSeek-V3.1** | Open (MoE) | 37B | **66.0** | -- | 74.8 (thinking) | -- | [HF model card](https://huggingface.co/deepseek-ai/DeepSeek-V3.1) |
| **Qwen3-Coder-30B-A3B** | Open (MoE) | 3B | **50.3** | -- | -- | -- | [HF model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) |
| **DeepSeek-R1** | Open (MoE) | 37B | **49.2** | -- | 65.9 | -- | [HF model card](https://huggingface.co/deepseek-ai/DeepSeek-R1) |
| **Qwen3-32B** | Open (Dense) | 32B | N/A | -- | 70.7 | -- | [Qwen3 tech report](https://arxiv.org/abs/2505.09388) |

Notes:
1. **MiMo-V2-Flash 73.4% vs previously reported 80.2%**: The 80.2% appears in some reviews but the official HF model card reports 73.4%. The difference is the agent scaffold used. The higher number may reflect an optimized evaluation setup not reproducible in standard deployment.
2. **Qwen3-Coder-480B**: No specific SWE-bench number extracted. Alibaba claims "comparable to Claude Sonnet" which would put it ~75-82%.
3. **SWE-bench scores are scaffold-dependent.** The same model can score 10-20% differently depending on whether you use SWE-Agent, OpenHands, Claude Code, or a custom scaffold. These numbers represent reported results, not guaranteed performance.
4. LiveCodeBench v6 is a different problem set than v5. Scores across versions are not directly comparable.
5. **[2026-02-25 UPDATE] Qwen3.5 family (released Feb 16-24, 2026)**: Dense and MoE models. Qwen3.5-27B is a dense 27B that achieves 72.4% SWE-bench Verified — higher than the MoE Qwen3-Coder-Next (70.6%) at 3x less VRAM. Qwen3.5-35B-A3B leads TAU2-Bench for agentic tool-calling. Qwen3.5-122B-A10B scores BFCL-V4 72.2 for knowledge-heavy tasks.
6. **[2026-02-25 UPDATE] Claude Sonnet 4.6 (Feb 17, 2026)**: SWE-bench 79.6% at $3/$15 per M tokens. Within 1.2% of Opus 4.5 (80.9% at $5/$25). Significantly changes the cloud cost model — near-Opus quality at 60% the price.
7. **[2026-02-25 UPDATE] GPT-5.3-Codex**: SWE-bench 80.0%, Terminal-Bench 77.3%, Aider Polyglot 88.0%. OpenAI's coding-specialized variant.

### Dense Model Coding Benchmarks

| Model | Params | BFCL v3 | LiveCodeBench v5 | CodeForces ELO | HumanEval | Context |
|-------|--------|---------|------------------|----------------|-----------|---------|
| **Qwen3.5-27B** | 27B | -- | -- | -- | -- | 128K | [2026-02-25 UPDATE] |
| **Qwen3-32B** | 32B | **68.2** | 70.7 | 1974 | ~85%+ | 128K |
| **Qwen3-14B** | 14B | ~58-62 | ~65 (est.) | -- | ~82%+ | 128K |
| **Llama 3.3 70B** | 70B | ~60 | -- | -- | ~80% | 128K |
| **Codestral 22B** | 22B | -- | -- | -- | 86.6 | 256K |
| **DeepSeek-R1-Distill-Qwen-32B** | 32B | -- | -- | 1691 | -- | 128K |

Sources: [Qwen3 tech report](https://arxiv.org/abs/2505.09388), [HF model cards]

---

## 2. What Fits on Athanor's GPUs

### Node 1: 4x RTX 5070 Ti (64 GB TP=4) + RTX 4090 (24 GB)

| Model | Format | Weight Size | Fits TP=4 (64 GB)? | Fits 4090 (24 GB)? | KV Cache Room |
|-------|--------|------------|---------------------|---------------------|---------------|
| Qwen3.5-27B | AWQ (4-bit) | ~14 GB | Yes, plenty | Yes | ~50 GB / ~10 GB | [2026-02-25 UPDATE] |
| Qwen3.5-27B | FP8 | ~27 GB | Yes | Yes (tight) | ~37 GB / -- | [2026-02-25 UPDATE] |
| Qwen3.5-27B | BF16 | ~54 GB | Yes (10 GB headroom) | No | ~10 GB | [2026-02-25 UPDATE] |
| Qwen3.5-35B-A3B (MoE) | AWQ (4-bit) | ~17 GB | Yes, plenty | Yes | ~47 GB / ~7 GB | [2026-02-25 UPDATE] |
| Qwen3.5-122B-A10B (MoE) | Q4_K_M | ~61 GB | **Yes** (tight) | No | ~3 GB | [2026-02-25 UPDATE] |
| Qwen3.5-397B-A17B (MoE) | Q4_K_M | ~214 GB | **No** (offload) | No | -- | [2026-02-25 UPDATE] |
| Qwen3-32B | AWQ (4-bit) | ~19.8 GB | Yes, plenty | Yes (tight) | ~44 GB / ~4 GB |
| Qwen3-32B | FP8 | ~32 GB | Yes | No | ~32 GB |
| Qwen3-32B | BF16 | ~64 GB | Barely (0 GB headroom) | No | None |
| Qwen3-Coder-Next (80B/3B) | Q4_K_M | ~46 GB | **Yes** | No | ~18 GB |
| Qwen3-Coder-Next (80B/3B) | FP8 | ~80 GB | No | No | -- |
| Qwen3-Coder-30B-A3B | AWQ (4-bit) | ~18.6 GB | Yes | Yes | ~45 GB / ~5 GB |
| Llama 3.3 70B | NVFP4 | ~35 GB | Yes (Blackwell only) | No (Ada) | ~29 GB |
| Llama 3.3 70B | AWQ (4-bit) | ~40 GB | Yes | No | ~24 GB |
| MiMo-V2-Flash (309B/15B) | Q4_K_M | ~186 GB | **No** (offload) | No | -- |
| GLM-4.7 (355B/32B) | Q4_K_M | ~214 GB | **No** (offload) | No | -- |

### Node 2: RTX 5090 (32 GB) + RTX 5060 Ti (16 GB)

| Model | Format | Weight Size | Fits 5090 (32 GB)? | Fits 5060 Ti (16 GB)? | Fits TP=2 (48 GB)? |
|-------|--------|------------|---------------------|-----------------------|---------------------|
| Qwen3.5-27B | AWQ (4-bit) | ~14 GB | Yes (18 GB room) | Yes (2 GB room) | Yes | [2026-02-25 UPDATE] |
| Qwen3.5-27B | FP8 | ~27 GB | Yes (5 GB room) | No | Yes | [2026-02-25 UPDATE] |
| Qwen3.5-27B | BF16 | ~54 GB | No | No | No | [2026-02-25 UPDATE] |
| Qwen3.5-35B-A3B (MoE) | AWQ (4-bit) | ~17 GB | Yes | Yes (tight) | Yes | [2026-02-25 UPDATE] |
| Qwen3-32B | FP8 | ~32 GB | **Exact fit** | No | Yes |
| Qwen3-32B | AWQ (4-bit) | ~19.8 GB | Yes | Yes (tight) | Yes |
| Qwen3-14B | FP16 | ~28 GB | Yes | No | Yes |
| Qwen3-14B | AWQ (4-bit) | ~9.5 GB | Yes | Yes | Yes |
| Qwen3-Coder-Next (80B/3B) | Q4_K_M | ~46 GB | No | No | **Barely** (2 GB headroom) |
| Qwen3-Coder-30B-A3B | AWQ (4-bit) | ~18.6 GB | Yes | Yes (tight) | Yes |

### With MoE Offloading on Node 1 (64-88 GB VRAM + 224 GB DDR4 RAM = 312 GB capacity)

| Model | Q4_K_M Size | Active Params | Fits? | Expected Speed | SWE-bench |
|-------|-------------|---------------|-------|----------------|-----------|
| **Qwen3.5-122B-A10B** | ~61 GB | 10B | **Yes (VRAM only)** | 50-80 tok/s | -- (BFCL-V4: 72.2) | [2026-02-25 UPDATE] |
| **Qwen3.5-397B-A17B** | ~214 GB | 17B | Yes (offload) | 10-20 tok/s | 76.4% | [2026-02-25 UPDATE] |
| **GLM-4.7** | 214 GB | 32B | Yes | 8-15 tok/s | 73.8% |
| **MiMo-V2-Flash** | 186 GB | 15B | Yes | 15-25 tok/s | 73.4% |
| **Qwen3-Coder-480B** | 290 GB | 35B | **Barely** | 5-8 tok/s | ~75-82% (est.) |
| **Kimi K2.5** | 628 GB | 32B | No | -- | 76.8% |
| **GLM-5** | 473 GB | 40B | No | -- | 77.8% |
| **DeepSeek-V3.1** | 404 GB | 37B | No | -- | 66.0% |

Speed estimates assume KTransformers with hot experts in VRAM, cold experts in DDR4 RAM. DDR4 quad-channel bandwidth (~51 GB/s) is the bottleneck. Actual throughput depends heavily on expert locality (how often the same experts are reused across tokens).

---

## 3. Quantization Analysis for Coding Tasks

### Quality vs Speed vs VRAM

| Method | Bits/Weight | VRAM Savings vs BF16 | Quality Loss (general) | Quality Loss (coding est.) | Speed Impact | GPU Support |
|--------|-------------|----------------------|----------------------|---------------------------|--------------|-------------|
| **BF16** | 16 | Baseline | Baseline | Baseline | Baseline | All |
| **FP8** | 8 | 2x | 1-3% | 2-4% | ~1.3x faster | Blackwell (native), Ada (emulated) |
| **NVFP4** | 4 | 4x | 2-4% | 3-5% | **1.6x faster** | **Blackwell only** (sm_120) |
| **AWQ** | 4 | 4x | 3-5% | 4-7% | ~1.2-1.4x faster | All (explicit flag on Blackwell) |
| **GPTQ** | 4 | 4x | 3-5% | 4-7% | ~1.2-1.4x faster | All |
| **INT4 W4A16** | 4 | 4x | 3-6% | 4-8% | ~1.3x faster | All |
| **Q4_K_M (GGUF)** | ~4.83 | 3.3x | 2-4% | 3-6% | Depends on backend | All (llama.cpp, KTransformers) |
| **Q2_K (GGUF)** | ~2 | 8x | 8-15% | **15-25%** | Depends on backend | All |

### Coding-Specific Observations

1. **Code generation is more sensitive to quantization than chat/reasoning.** A single wrong token in code (wrong variable name, missing semicolon, wrong operator) breaks functionality. Quantization that adds 3% noise to general text may add 7% errors to code.

2. **FP8 is the sweet spot for coding quality.** Minimal quality loss (2-4%), 2x VRAM savings, native Blackwell support. If your model fits at FP8, use FP8.

3. **AWQ at 4-bit is the practical fallback.** When FP8 doesn't fit, AWQ provides an additional 2x savings with acceptable quality loss (4-7% on coding). This is what Athanor runs now with Qwen3-32B-AWQ.

4. **NVFP4 is the Blackwell advantage.** Hardware-native 4-bit float on tensor cores. Same 4x savings as AWQ but with better quality preservation (2-4% vs 4-7%) AND 1.6x throughput boost. Only available on sm_120 GPUs (5070 Ti, 5060 Ti, 5090). The 4090 cannot use this.

5. **Below 4 bits, coding quality degrades rapidly.** Q2_K and lower quantizations are not recommended for coding tasks. The error rate on complex multi-step code generation becomes unacceptable (15-25% quality loss).

6. **MoE models are more robust to quantization** because only active expert weights affect output quality, and MoE routing is relatively quantization-tolerant. A 480B MoE at Q4 may perform comparably to a 32B dense at FP8 because the routing precision matters more than individual expert weight precision.

### Recommendation per GPU

| GPU | Best Quant for Dense Models | Best Quant for MoE Models |
|-----|----------------------------|---------------------------|
| RTX 5070 Ti (16 GB, Blackwell) | NVFP4 or AWQ | NVFP4 (if fits), Q4_K_M for offloading |
| RTX 4090 (24 GB, Ada) | FP8 or AWQ | AWQ, Q4_K_M for offloading |
| RTX 5090 (32 GB, Blackwell) | FP8 (preferred), NVFP4 | FP8 or NVFP4 |
| RTX 5060 Ti (16 GB, Blackwell) | NVFP4 or AWQ | NVFP4 (if fits), Q4_K_M for offloading |

Sources:
- [NVFP4 throughput analysis](https://kaitchup.substack.com/p/nvfp4-same-accuracy-with-23-higher)
- [Private LLM Inference on Consumer Blackwell GPUs](https://arxiv.org/html/2601.09527v1)
- [Qwen3-Coder 30B hardware guide](https://www.arsturn.com/blog/running-qwen3-coder-30b-at-full-context-memory-requirements-performance-tips)

---

## 4. MoE Models on Consumer Hardware

### Architecture Overview

All frontier coding models as of Feb 2026 are MoE (Mixture of Experts). The key insight: **total parameters determine storage/VRAM needs, but active parameters determine compute speed.**

| Model | Total Params | Active Params | Experts | Active per Token | Sparsity |
|-------|-------------|---------------|---------|-----------------|----------|
| Kimi K2.5 | 1,040B | 32B | 384 | 8 | 97% |
| GLM-5 | 744B | 40B | -- | -- | ~95% |
| DeepSeek-V3.1 | 671B | 37B | 256 | -- | ~95% |
| Qwen3-Coder-480B | 480B | 35B | 160 | 8 | 93% |
| GLM-4.7 | 355B | 32B | -- | -- | ~91% |
| MiMo-V2-Flash | 309B | 15B | -- | -- | ~95% |
| Qwen3-Coder-Next | 80B | 3B | 512 | 10 | 96% |
| Qwen3-Coder-30B-A3B | 30B | 3.3B | 128 | ~2 | 89% |

### Consumer GPU Deployment Strategies

**Strategy 1: Full VRAM (best speed, limited model size)**
- Load all experts into GPU VRAM
- Speed: Full GPU decode speed (40-100+ tok/s depending on model and GPU)
- Limitation: Model must fit entirely in available VRAM
- Best for: Qwen3-Coder-Next Q4 on TP=4 (46 GB in 64 GB), Qwen3-Coder-30B-A3B on single GPU

**Strategy 2: MoE Expert Offloading via KTransformers (best for large models)**
- Hot experts (frequently activated) stay in VRAM
- Cold experts loaded from system RAM on demand
- Active computation happens on GPU at full speed
- Expert swapping bottlenecked by DDR4/DDR5 bandwidth
- Speed: 8-25 tok/s depending on model, RAM bandwidth, and expert locality
- Best for: GLM-4.7, MiMo-V2-Flash, Qwen3-Coder-480B on Node 1

**Strategy 3: CPU+GPU Hybrid via llama.cpp (most flexible)**
- Model layers split between GPU and CPU
- GPU handles as many layers as VRAM allows
- CPU handles remaining layers
- Speed: Dominated by CPU speed, typically 5-15 tok/s
- Best for: Quick experimentation, models that don't have KTransformers support

### Throughput Expectations

| Model | Strategy | Node | Expected Speed | Latency (first token) |
|-------|----------|------|----------------|----------------------|
| Qwen3-Coder-30B-A3B Q4 | Full VRAM, 4090 | Node 1 | **~73 tok/s** | <500ms |
| Qwen3-Coder-30B-A3B Q4 | Full VRAM, 5090 | Node 2 | **~100+ tok/s** | <300ms |
| Qwen3-Coder-Next Q4 | Full VRAM, TP=4 | Node 1 | **~40-60 tok/s** | <800ms |
| Qwen3-32B AWQ | Full VRAM, TP=4 | Node 1 | **~35-50 tok/s** | <600ms |
| Qwen3-32B FP8 | Full VRAM, 5090 | Node 2 | **~60-80 tok/s** | <400ms |
| GLM-4.7 Q4_K_M | KTransformers offload | Node 1 | **~8-15 tok/s** | 1-3s |
| MiMo-V2-Flash Q4_K_M | KTransformers offload | Node 1 | **~15-25 tok/s** | 1-2s |
| Qwen3-Coder-480B Q4_K_M | KTransformers offload | Node 1 | **~5-8 tok/s** | 2-5s |

Speed estimates are approximate. MoE offloading speeds depend heavily on expert locality (how often the same experts are reused), which varies by task and prompt. Coding tasks tend to have better expert locality than general chat because code tokens are more predictable.

Sources:
- [KTransformers GitHub](https://github.com/kvcache-ai/ktransformers) - DeepSeek-R1 FP8 benchmarks: 87.58 tok/s output on 8x L20
- [Qwen3-Coder 30B performance](https://www.arsturn.com/blog/running-qwen3-coder-30b-at-full-context-memory-requirements-performance-tips) - 72.9 tok/s on RTX 4090 Q4
- [Unsloth GGUF guides](https://unsloth.ai) - GGUF size calculations

---

## 5. Multi-GPU Strategies

### Can We Combine Node 1 + Node 2 (136 GB)?

**Short answer: No, not for interactive use. Marginally viable for batch workloads over InfiniBand.**

### Tensor Parallelism (TP) Across Network

TP requires all-reduce operations at every transformer layer. This is bandwidth-intensive.

| Network | Bandwidth | All-reduce per layer (32B) | Per-token overhead (48 layers) | Verdict |
|---------|-----------|---------------------------|-------------------------------|---------|
| 5GbE | ~1.25 GB/s | ~25 ms | ~1.2 s | **Not viable** |
| IB EDR (56 Gbps) | ~6.25 GB/s | ~5 ms | ~240 ms | **Marginally viable** |
| IB HDR (200 Gbps) | ~25 GB/s | ~1.3 ms | ~62 ms | Viable for batch |
| PCIe 4.0 (intra-node) | ~32 GB/s | ~1 ms | ~48 ms | Standard (Node 1) |
| PCIe 5.0 (intra-node) | ~64 GB/s | ~0.5 ms | ~24 ms | Fast (Node 2) |

**Cross-node TP is 5-25x slower than intra-node TP.** For interactive coding assistance (where you want <1s latency), this is unacceptable.

### Pipeline Parallelism (PP) Across Network

PP only transfers activations between pipeline stages (once per token, not per layer). More latency-tolerant.

| Network | Activation Transfer | Per-token overhead | Viable? |
|---------|--------------------|--------------------|---------|
| 5GbE | ~8 ms | ~8 ms | **Marginal** (adds 8ms per token) |
| IB EDR | ~1.6 ms | ~1.6 ms | **Yes** (minimal overhead) |

PP with InfiniBand is viable but introduces pipeline bubble (~30-50% throughput loss with 2 stages). Combined with TP within each node:
- Node 1: TP=4 across 5070 Ti (64 GB)
- Node 2: Single 5090 (32 GB) or TP=2 (48 GB)
- PP=2 across nodes
- Total effective VRAM: 96-112 GB
- But: 30-50% throughput penalty from pipeline bubble

**This enables models up to ~100 GB at Q4**, which opens up:
- Qwen3-235B-A22B at Q4_K_M (143 GB) -- still too large
- Qwen3-Coder-Next FP8 (80 GB) -- fits with PP=2
- Llama 3.3 70B BF16 (140 GB) -- too large
- Llama 3.3 70B FP8 (70 GB) -- fits with PP=2

### Recommendation: Don't Cross the Network

**MoE offloading to system RAM is strictly superior to cross-network inference for Athanor.**

| Factor | Cross-Network PP | MoE Offloading (KTransformers) |
|--------|------------------|-------------------------------|
| Bandwidth bottleneck | 1.25-6.25 GB/s (network) | **51-77 GB/s (DDR4/DDR5 RAM)** |
| Latency overhead | 8ms+ per token | <1ms per expert swap |
| Throughput penalty | 30-50% from pipeline bubble | 0% for active params |
| Complexity | Ray cluster, NCCL config, network tuning | Single process, single node |
| Model size limit | ~100 GB (PP=2 over IB) | **312 GB** (Node 1 RAM + VRAM) |
| Debugging | Distributed system debugging | Single-node debugging |

The only scenario where cross-network makes sense: **dense models larger than system RAM** (e.g., a 200B dense model at FP8 = 200 GB, which exceeds Node 1's 224 GB RAM but could be split across nodes). No current coding model needs this -- they're all MoE.

---

## 6. Model-by-Model Analysis

### Qwen3.5-27B (27B Dense) -- STRONGEST RECOMMENDATION [2026-02-25 UPDATE]

**The best coding model that fits on Athanor's hardware. Replaces Qwen3-Coder-Next as primary recommendation.**

- Architecture: Dense 27B transformer
- SWE-bench Verified: **72.4%** (beats Qwen3-Coder-Next 70.6% by 1.8 points)
- Released: February 16-24, 2026
- License: Apache 2.0
- vLLM reasoning parser: `qwen3` (uses `--reasoning-parser qwen3`)
- AWQ and FP8 pre-quantized versions available on HuggingFace

Why this changes everything:
1. **72.4% > 70.6%** — higher SWE-bench than Qwen3-Coder-Next
2. **~14 GB AWQ vs ~46 GB Q4** — 3x less VRAM
3. **Dense model** — no MoE routing overhead, simpler deployment, more predictable performance
4. **Fits on ANY single GPU** — even the 5060 Ti (16 GB) with 2 GB room for KV cache at AWQ
5. **FP8 on 5090 (~27 GB)** — runs at maximum quality with 5 GB room on the fastest single GPU

Deployment on Athanor:
```
# Option A: Node 1, TP=4 across 5070 Ti GPUs (overkill but maximum KV cache)
AWQ: ~14 GB in 64 GB → 50 GB for KV cache → massive context window
FP8: ~27 GB in 64 GB → 37 GB for KV cache

# Option B: Node 2, 5090 single GPU (RECOMMENDED — highest bandwidth)
FP8: ~27 GB in 32 GB → 5 GB KV cache → practical for coding
AWQ: ~14 GB in 32 GB → 18 GB KV cache → generous context

# Option C: Node 1, 4090 single GPU
AWQ: ~14 GB in 24 GB → 10 GB KV cache
FP8: ~27 GB — does NOT fit (24 GB VRAM)

# Option D: Node 2, 5060 Ti single GPU (smallest viable)
AWQ: ~14 GB in 16 GB → 2 GB KV cache → tight but works for short context
```

The key insight: Qwen3-Coder-Next required TP=4 (Node 1's entire 5070 Ti cluster) for a single model load. Qwen3.5-27B fits on a single GPU, freeing 3 GPUs for other tasks. This dramatically improves Athanor's multi-model deployment flexibility.

### Qwen3.5-35B-A3B (35B/3B MoE) -- BEST AGENTIC TOOL-CALLING [2026-02-25 UPDATE]

**TAU2-Bench leader for agent tasks. The best model for tool-calling and agentic workflows.**

- Architecture: MoE, 35B total / 3B active params
- TAU2-Bench: Leader (specific score TBD — claimed #1 on leaderboard)
- Released: February 16-24, 2026
- License: Apache 2.0
- Specialization: Tool-calling, agentic workflows, multi-step task execution

Deployment on Athanor:
```
# AWQ: ~17 GB — fits on ANY single GPU except 5060 Ti (tight)
# Node 1 4090: 17/24 GB → 7 GB KV cache
# Node 2 5090: 17/32 GB → 15 GB KV cache
# Node 1 5070 Ti (single): 17/16 GB → does NOT fit (needs AWQ optimization or 5070 Ti TP=2)
```

Best use: Agent backbone for Athanor's agent framework. If tool-calling quality is more important than raw coding ability, this model may outperform Qwen3.5-27B for agentic tasks specifically. Consider as the agent framework's primary model while Qwen3.5-27B handles coding.

### Qwen3-Coder-Next (80B/3B MoE) -- ~~STRONGEST RECOMMENDATION~~ SUPERSEDED BY Qwen3.5-27B

**The best coding model that fits entirely in Athanor's VRAM.**

- Architecture: 48 layers, 512 experts, 10 activated per token, Gated DeltaNet + MoE hybrid
- Unique: Uses linear attention (DeltaNet) for 75% of layers, standard attention for 25% -- reduces KV cache
- SWE-bench Verified: 70.6% (beats DeepSeek-V3.2's 70.2% with 12x fewer active params)
- Released: February 2, 2026
- License: Apache 2.0
- Non-thinking mode only (no `<think>` blocks)
- vLLM tool call parser: `qwen3_coder`

Deployment on Athanor:
```
# Node 1, TP=4 across 5070 Ti GPUs
Q4_K_M: ~46 GB (fits in 64 GB with 18 GB KV cache headroom)
FP8: ~80 GB (does NOT fit in 64 GB)
```

Tradeoff: 18 GB KV cache across 4 GPUs = 4.5 GB per GPU. At 256K context this is tight. Recommend `--max-model-len 32768` for practical use.

Source: [HF model card](https://huggingface.co/Qwen/Qwen3-Coder-Next)

### GLM-4.7 (355B/32B MoE) -- BEST QUALITY WITH OFFLOADING

- SWE-bench Verified: 73.8%, LiveCodeBench v6: 84.9%, Tau2-Bench: 87.4%
- License: MIT
- vLLM tool call parser: `glm47`
- The Tau2-Bench score of 87.4 is exceptionally strong for agentic tool use

Deployment on Athanor:
```
# Node 1, KTransformers MoE offloading
Q4_K_M: ~214 GB (32B active in VRAM, rest in 224 GB DDR4)
Expected speed: 8-15 tok/s
```

Best for batch/complex coding tasks where quality matters more than speed.

Source: [HF model card](https://huggingface.co/zai-org/GLM-4.7)

### MiMo-V2-Flash (309B/15B MoE) -- BEST SPEED/QUALITY WITH OFFLOADING

- SWE-bench Verified: 73.4%, LiveCodeBench v6: 80.6%
- License: MIT
- Unique: Hybrid sliding window attention (6x KV cache reduction), Multi-Token Prediction (2-3x decode speedup)
- Only 15B active params -- less VRAM needed for active compute, faster expert swapping

Deployment on Athanor:
```
# Node 1, KTransformers or SGLang MoE offloading
Q4_K_M: ~186 GB (15B active in VRAM, rest in 224 GB DDR4)
Expected speed: 15-25 tok/s (faster than GLM-4.7 due to smaller active params + MTP)
```

The MTP (Multi-Token Prediction) is a significant advantage -- it generates 2-3 tokens per forward pass, effectively doubling throughput. SGLang has native MTP support (`--enable-mtp`).

Source: [HF model card](https://huggingface.co/XiaomiMiMo/MiMo-V2-Flash)

### Kimi K2.5 (1040B/32B MoE) -- TOO LARGE

- SWE-bench Verified: 76.8%, LiveCodeBench v6: 85.0%, SWE-bench Pro: 50.7%
- License: Open weight
- Q4_K_M: ~628 GB -- far exceeds Node 1's 312 GB (VRAM + RAM)
- IQ1_M: ~240 GB -- fits but 1-bit quality is unacceptable for coding
- Q2_K: ~381 GB -- still exceeds capacity

Verdict: Cannot run locally at acceptable quality. Use via API.

Source: [HF model card](https://huggingface.co/moonshotai/Kimi-K2.5)

### GLM-5 (744B/40B MoE) -- TOO LARGE

- SWE-bench Verified: 77.8%, Terminal-Bench 2.0: 56.2%, Tau2-Bench: 89.7%
- License: MIT
- Q4_K_M: ~473 GB -- far exceeds capacity
- IQ1_M: ~176 GB -- fits but quality unacceptable

Verdict: Cannot run locally at acceptable quality. GLM-4.7 is the realistic alternative.

Source: [HF model card](https://huggingface.co/zai-org/GLM-5)

### DeepSeek-V3.1 (671B/37B MoE) -- POSSIBLE BUT NOT RECOMMENDED

- SWE-bench Verified: 66.0% (non-thinking), LiveCodeBench: 74.8% (thinking)
- License: MIT
- Q4_K_M: ~404 GB -- exceeds capacity
- Q2_K: ~245 GB -- fits in Node 1 RAM + VRAM but quality degraded
- IQ2: ~245 GB -- similar

Lower SWE-bench than GLM-4.7 (66.0% vs 73.8%) despite similar active params. Not worth the effort.

Source: [HF model card](https://huggingface.co/deepseek-ai/DeepSeek-V3.1)

### DeepSeek-R1 (671B/37B MoE) -- SKIP

- SWE-bench Verified: 49.2% -- significantly below competition
- LiveCodeBench: 65.9%
- Same VRAM challenges as V3.1 with worse coding performance
- The reasoning capability doesn't translate to SWE-bench advantage

Source: [HF model card](https://huggingface.co/deepseek-ai/DeepSeek-R1)

### Qwen3-Coder-480B (480B/35B MoE) -- STRETCH GOAL

- SWE-bench: "comparable to Claude Sonnet" (~75-82% estimated)
- License: Apache 2.0
- Q4_K_M: ~290 GB -- barely fits in Node 1 (224 GB RAM + 88 GB VRAM = 312 GB)
- Speed: ~5-8 tok/s with offloading (slow)
- Would be the strongest local coding model but at painfully slow speed

Deployment would require:
```
# Node 1, KTransformers, very tight memory budget
Q4_K_M: 290 GB
Available: 312 GB (224 GB DDR4 + 88 GB VRAM)
Headroom: 22 GB for KV cache and OS overhead -- VERY tight
```

Not recommended as a primary model. Consider for batch overnight runs or specific high-stakes tasks.

Source: [HF model card](https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8)

### Qwen3-32B (32B Dense) -- CURRENT MODEL, STILL EXCELLENT

- BFCL v3: 68.2, LiveCodeBench v5: 70.7, CodeForces: 1974 ELO
- License: Apache 2.0
- Currently deployed as AWQ on Node 1 TP=4
- Best tool-calling benchmark (BFCL 68.2) of any model that fits cleanly in VRAM
- No SWE-bench score available -- but likely ~55-65% based on comparable models

Source: [Qwen3 tech report](https://arxiv.org/abs/2505.09388)

### Qwen3-Coder-30B-A3B (30B/3B MoE) -- FAST ASSISTANT

- SWE-bench Verified: 50.3%
- License: Apache 2.0
- Q4: ~18.6 GB -- fits on ANY single GPU with room to spare
- Speed: ~73 tok/s on 4090, ~100+ tok/s on 5090
- 256K native context

Best use: Fast interactive coding assistant, code completion, quick questions. Not for complex multi-file refactors.

Source: [HF model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)

---

## 7. Deployment Recommendations

### Recommended Configuration [2026-02-25 UPDATE — Qwen3.5-27B replaces Qwen3-Coder-Next]

| Slot | Model | GPU(s) | Format | VRAM Used | Speed | Use Case |
|------|-------|--------|--------|-----------|-------|----------|
| **Primary Coding** | **Qwen3.5-27B** | Node 2 5090 | FP8 | 27/32 GB | 60-80 tok/s | Agentic coding, SWE-bench tasks, complex refactors |
| **General Assistant** | Qwen3-32B | Node 1 TP=4 (5070 Ti x4) | AWQ | 20/64 GB | 35-50 tok/s | Tool calling, general chat, agent backbone |
| **Agent Backbone** | Qwen3.5-35B-A3B | Node 1 4090 | AWQ | 17/24 GB | 60-80 tok/s | Tool-calling, agentic workflows (TAU2-Bench leader) |
| **Embedding** | Current setup | Node 1 GPU 4 | -- | ~8 GB | -- | RAG, knowledge search |
| **Creative** | ComfyUI | Node 2 5060 Ti | -- | 16 GB | -- | Image/video generation |

**Why Qwen3.5-27B replaces Qwen3-Coder-Next as primary:**
- **Higher quality:** SWE-bench 72.4% vs 70.6% (+1.8 points)
- **3x less VRAM:** ~14 GB AWQ / ~27 GB FP8 vs ~46 GB Q4
- **Dense model:** No MoE routing overhead. Simpler deployment. More predictable latency and throughput.
- **Frees TP=4 cluster:** Qwen3-Coder-Next required all 4x 5070 Ti. Qwen3.5-27B fits on a single 5090, freeing Node 1's 4-GPU cluster for the general assistant + agent backbone.
- **Maximum quality path:** FP8 on 5090 (1792 GB/s bandwidth) — the fastest single GPU in the fleet running at near-lossless precision.

This configuration:
- Maximizes coding capability: Qwen3.5-27B (SWE-bench 72.4%) on the fastest GPU at FP8
- Maintains general assistant quality: Qwen3-32B (BFCL 68.2) on Node 1 TP=4 with massive KV cache
- Adds dedicated agent backbone: Qwen3.5-35B-A3B (TAU2-Bench leader) on the 4090 for tool-calling
- Preserves existing embedding and creative workloads
- Uses all 7 GPUs
- **Net improvement over previous recommendation:** +1.8% SWE-bench on primary, dedicated agent model added, better GPU utilization

### Previous Recommended Configuration (superseded, kept for reference)

| Slot | Model | GPU(s) | Format | VRAM Used | Speed | Use Case |
|------|-------|--------|--------|-----------|-------|----------|
| **Primary Coding** | Qwen3-Coder-Next | Node 1 TP=4 (5070 Ti x4) | Q4/AWQ | 46/64 GB | 40-60 tok/s | Agentic coding, SWE-bench tasks, complex refactors |
| **General Assistant** | Qwen3-32B | Node 2 5090 | FP8 | 32/32 GB | 60-80 tok/s | Tool calling, general chat, agent backbone |
| **Fast Coding** | Qwen3-Coder-30B-A3B | Node 1 4090 | AWQ | 19/24 GB | 73 tok/s | Quick coding tasks, completions, simple fixes |
| **Embedding** | Current setup | Node 1 GPU 4 | -- | ~8 GB | -- | RAG, knowledge search |
| **Creative** | ComfyUI | Node 2 5060 Ti | -- | 16 GB | -- | Image/video generation |

### Alternative: Maximum Quality (Offloading)

For tasks where quality matters more than speed (overnight batch runs, critical code reviews):

```
# Option 1: Qwen3.5-397B-A17B via KTransformers offloading [2026-02-25 UPDATE]
# SWE-bench 76.4%, Q4 ~214 GB, 17B active params
# Expected: 10-20 tok/s (faster than GLM-4.7 due to smaller active params)
# This is now the highest-quality local option that fits on Node 1

# Option 2: GLM-4.7 or MiMo-V2-Flash via KTransformers offloading
# Stop primary models, start offloading model
# Expected: 8-25 tok/s, SWE-bench 73.4-73.8%
```

This could be automated via the GPU Orchestrator's zone management.

### What NOT To Do

1. **Don't try cross-node TP over 5GbE.** The latency penalty makes it worse than just using a smaller model that fits on one node.
2. **Don't run DeepSeek-R1 for coding.** Its SWE-bench 49.2% is worse than Qwen3-Coder-30B-A3B (50.3%) despite being 22x larger.
3. **Don't quantize below Q4 for coding tasks.** The quality degradation below 4 bits is disproportionately severe for code generation.
4. **Don't run Kimi K2.5 or GLM-5 locally.** They exceed your hardware capacity at any viable quantization. Use them via API for the handful of tasks where 76-78% SWE-bench matters.
5. **[2026-02-25 UPDATE] Don't default to Qwen3-Coder-Next over Qwen3.5-27B.** The MoE model uses 3x more VRAM for 1.8% less SWE-bench. The only scenario where Qwen3-Coder-Next wins: if its DeltaNet attention gives meaningfully better long-context coding (untested).

---

## 8. Gap Analysis: Local vs Cloud

### Original Gap Analysis (pre-Qwen3.5)

| Capability | Best Local (in VRAM) | Best Local (offloading) | Best Cloud | Gap |
|------------|---------------------|------------------------|------------|-----|
| SWE-bench Verified | 70.6% (Qwen3-Coder-Next) | 73.8% (GLM-4.7) | 82.0% (Sonnet 4.5) | **8-12 pts** |
| LiveCodeBench v6 | ~70.7 (Qwen3-32B, v5) | 84.9 (GLM-4.7) | 85.0+ (Kimi K2.5) | **0-15 pts** |
| Tool Calling (BFCL) | 68.2 (Qwen3-32B) | 87.4 (GLM-4.7, Tau2) | ~70+ (Claude) | **~0-2 pts** |
| Speed | 40-100 tok/s | 8-25 tok/s | ~50-80 tok/s | **Local wins in-VRAM** |
| Cost | $0 (electricity) | $0 (electricity) | $3-60/M tokens | **Local wins** |
| Privacy | Full local | Full local | Data sent to cloud | **Local wins** |

### Revised Gap Analysis [2026-02-25 UPDATE — with Qwen3.5 + Sonnet 4.6 + GPT-5.3-Codex]

| Capability | Best Local (in VRAM) | Best Local (offloading) | Best Cloud | Gap |
|------------|---------------------|------------------------|------------|-----|
| SWE-bench Verified | **72.4% (Qwen3.5-27B)** | **76.4% (Qwen3.5-397B-A17B)** | 82.0% (Sonnet 4.5) | **6-10 pts** |
| SWE-bench (cost-adjusted) | 72.4% ($0) | 76.4% ($0) | **79.6% (Sonnet 4.6, $3/$15)** | **3-7 pts** |
| LiveCodeBench v6 | ~70.7 (Qwen3-32B, v5) | 84.9 (GLM-4.7) | 85.0+ (Kimi K2.5) | **0-15 pts** |
| Tool Calling | **TAU2 leader (Qwen3.5-35B-A3B)** | 87.4 (GLM-4.7, Tau2) | ~70+ (Claude) | **Local leads** |
| BFCL-V4 | **72.2 (Qwen3.5-122B-A10B)** | -- | ~70+ (Claude) | **Local leads** |
| Speed | 40-100 tok/s | 8-25 tok/s | ~50-80 tok/s | **Local wins in-VRAM** |
| Cost | $0 (electricity) | $0 (electricity) | $3-60/M tokens | **Local wins** |
| Privacy | Full local | Full local | Data sent to cloud | **Local wins** |

**Key finding (updated):** The Qwen3.5 family narrows the SWE-bench gap significantly:
- **In-VRAM gap:** 72.4% vs 82.0% = **9.6 points** (was 11.4 with Qwen3-Coder-Next)
- **Offloading gap:** 76.4% vs 82.0% = **5.6 points** (was 8.2 with GLM-4.7)
- **Cost-adjusted gap:** 72.4% (free) vs 79.6% (Sonnet 4.6 at $3/$15) = **7.2 points** — but Sonnet 4.6's price is low enough that the cost argument weakens for high-stakes tasks

**The 6-10 point SWE-bench gap translates roughly to:** Cloud models solve ~80-82 out of 100 real GitHub issues; local models solve ~72-76. The gap has closed by ~2-3 points compared to pre-Qwen3.5 analysis.

**New cloud cost dynamics [2026-02-25 UPDATE]:** Claude Sonnet 4.6 at 79.6% SWE-bench and $3/$15 per M tokens is within 1.2% of Opus 4.5 (80.9% at $5/$25). GPT-5.3-Codex hits 80.0% with Aider Polyglot 88.0%. For tasks where the 7-10 point quality gap matters (complex multi-file refactors, unfamiliar codebases), Sonnet 4.6 is now the cost-effective cloud option — near-Opus quality at 60% the price. The hybrid strategy (local for 90% of tasks, cloud for the hard 10%) becomes even more compelling.

---

## 9. Open Questions

1. **Qwen3-Coder-480B exact SWE-bench score?** Alibaba's model card only says "comparable to Claude Sonnet." If it's genuinely 80%+, running it at Q4 with offloading (290 GB on Node 1) would match cloud quality despite slow speed.

2. **KTransformers on EPYC 7663?** All published benchmarks use Intel Xeon with DDR5. AMD EPYC with DDR4 quad-channel may have different performance characteristics, particularly for NUMA-aware expert placement.

3. **vLLM MoE offloading maturity?** KTransformers is proven for this use case, but vLLM is the production inference engine. vLLM's CPU offload support for MoE models needs testing on Athanor's hardware.

4. **NVFP4 quality specifically for coding?** The 2-4% general benchmark loss claim needs coding-specific validation. Running Qwen3-32B at NVFP4 vs AWQ on a coding benchmark would provide Athanor-specific data.

5. **Mixed-architecture TP on Node 2?** The 5090 (32 GB) and 5060 Ti (16 GB) are both Blackwell sm_120 but have very different memory bandwidth (1792 vs 448 GB/s). TP=2 across them may be bottlenecked by the slower GPU.

---

## 10. Sources

### Model Cards (Official)
- [GLM-4.7](https://huggingface.co/zai-org/GLM-4.7)
- [GLM-5](https://huggingface.co/zai-org/GLM-5)
- [Kimi K2.5](https://huggingface.co/moonshotai/Kimi-K2.5)
- [MiMo-V2-Flash](https://huggingface.co/XiaomiMiMo/MiMo-V2-Flash)
- [Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B) [2026-02-25 UPDATE]
- [Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) [2026-02-25 UPDATE]
- [Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) [2026-02-25 UPDATE]
- [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) [2026-02-25 UPDATE]
- [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next)
- [Qwen3-Coder-480B-A35B-Instruct-FP8](https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8)
- [Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)
- [DeepSeek-V3.1](https://huggingface.co/deepseek-ai/DeepSeek-V3.1)
- [DeepSeek-V3-0324](https://huggingface.co/deepseek-ai/DeepSeek-V3-0324)
- [DeepSeek-R1](https://huggingface.co/deepseek-ai/DeepSeek-R1)

### Leaderboards
- [Vellum LLM Leaderboard](https://www.vellum.ai/llm-leaderboard) - Cloud model SWE-bench scores
- [llm-stats GLM-4.7](https://llm-stats.com/models/glm-4.7) - Multi-benchmark rankings
- [SWE-bench](https://www.swebench.com/) - Official SWE-bench leaderboard

### Technical Reports
- [Qwen3 Technical Report](https://arxiv.org/abs/2505.09388)
- [Private LLM Inference on Consumer Blackwell GPUs](https://arxiv.org/html/2601.09527v1)

### Guides and Reviews
- [marc0.dev Qwen3-Coder-Next review](https://www.marc0.dev/en/blog/qwen3-coder-next-70-swe-bench-with-3b-active-params-local-ai-just-got-real-1770197534528)
- [Qwen3-Coder 30B hardware guide](https://www.arsturn.com/blog/running-qwen3-coder-30b-at-full-context-memory-requirements-performance-tips)
- [KTransformers GitHub](https://github.com/kvcache-ai/ktransformers)
- [Unsloth GGUF guides](https://unsloth.ai)
- [NVFP4 throughput analysis](https://kaitchup.substack.com/p/nvfp4-same-accuracy-with-23-higher)
- [vLLM quantization docs](https://docs.vllm.ai/en/latest/features/quantization/index.html)
- [vLLM tool calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/)

### Data Quality Notes
- SWE-bench scores are scaffold-dependent (10-20% variation for the same model under different evaluation setups)
- LiveCodeBench v6 scores are not comparable to v5 or earlier versions
- MoE offloading speed estimates are approximate and depend on expert locality patterns
- Quantization quality loss percentages are from general benchmarks; coding-specific losses may differ
