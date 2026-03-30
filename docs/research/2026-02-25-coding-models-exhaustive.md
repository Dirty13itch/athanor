# Exhaustive Coding Model Survey: December 2025 - February 2026

**Date**: 2026-02-25
**Status**: Research complete
**Purpose**: Comprehensive catalog of EVERY coding-specialized model released or significantly updated in the 90-day window (Dec 2025 - Feb 2026), with deployment feasibility for Athanor's GPU fleet.
**Supersedes**: `2026-02-16-frontier-coding-models-local-inference.md`, `2026-02-16-tool-calling-coding-models.md`, `2026-02-25-local-coding-models-update.md`
**Related**: `ADR-005-inference-engine.md`, `docs/archive/hardware/hardware-inventory.md`, `docs/operations/HARDWARE-REPORT.md`

---

## Hardware Context

| Node | CPU | RAM | GPUs | VRAM | Bandwidth per GPU |
|------|-----|-----|------|------|-------------------|
| **Foundry (Node 1)** | EPYC 7663 56C/112T | 224 GB DDR4 ECC | 4x RTX 5070 Ti (16 GB) + 1x RTX 4090 (24 GB) | **88 GB** | 5070 Ti: 896 GB/s, 4090: 1008 GB/s |
| **Workshop (Node 2)** | TR 7960X 24C/48T | 128 GB DDR5 | 1x RTX 5090 (32 GB) + 1x RTX 5060 Ti (16 GB) | **48 GB** | 5090: 1792 GB/s, 5060 Ti: 448 GB/s |
| **Combined** | | 352 GB | 7 GPUs | **136 GB** | |

Key constraints:
- Node 1 PCIe 4.0, Node 2 PCIe 5.0. No NVLink anywhere.
- 5070 Ti / 5060 Ti / 5090 = Blackwell sm_120. 4090 = Ada sm_89.
- TP=4 on Node 1 (64 GB across 5070 Ti x4). 4090 (24 GB) independent.
- TP=2 on Node 2 (48 GB) possible but 5060 Ti bandwidth is bottleneck.
- Node 1 can offload to 224 GB DDR4 RAM (~51 GB/s quad-channel).

---

## 1. Master Catalog

### Tier S: Frontier Coding Models (SWE-bench > 75%)

| # | Model | Org | Released | Arch | Total | Active | SWE-bench V | LCBv6 | TB2 | BFCL-V4 | License | Q4 Size | Fits VRAM? |
|---|-------|-----|----------|------|-------|--------|-------------|-------|-----|---------|---------|---------|------------|
| 1 | **MiniMax-M2.5** | MiniMax | Feb 2026 | MoE ~229B | ~229B | ~10B? | **80.2** | -- | -- | -- | Modified-MIT | ~140 GB | Offload only |
| 2 | **GLM-5** | Zhipu AI | Feb 2026 | MoE | 744B | 40B | **77.8** | -- | -- | -- | MIT | ~473 GB | Too large |
| 3 | **Kimi K2.5** | Moonshot | Jan 2026 | MoE | 1,040B | 32B | **76.8** | 85.0 | -- | -- | Custom | ~628 GB | Too large |
| 4 | **Qwen3.5-397B-A17B** | Alibaba | Feb 2026 | MoE+DeltaNet | 397B | 17B | **76.4** | 83.6 | 52.5 | 72.9 | Apache 2.0 | ~240 GB | Offload (tight) |
| 5 | **IQuest-Coder-V1-40B** | IQuestLab | Dec 2025 | Dense | 40B | 40B | **76.2** | 81.1 | -- | -- | Custom | ~24 GB | 4090/5090 AWQ |

### Tier A: Strong Coding Models (SWE-bench 70-75%)

| # | Model | Org | Released | Arch | Total | Active | SWE-bench V | LCBv6 | TB2 | BFCL-V4 | License | Q4 Size | Fits VRAM? |
|---|-------|-----|----------|------|-------|--------|-------------|-------|-----|---------|---------|---------|------------|
| 6 | **Step-3.5-Flash** | StepFun | Feb 2026 | MoE+MTP-3 | 196B | 11B | **74.4** | **86.4** | 51.0 | -- | Apache 2.0 | ~120 GB | Offload |
| 7 | **GLM-4.7** | Zhipu AI | Dec 2025 | MoE | 355B | 32B | **73.8** | 84.9 | -- | -- | MIT | ~214 GB | Offload |
| 8 | **MiMo-V2-Flash** | Xiaomi | Dec 2025 | MoE+MTP | 309B | 15B | **73.4** | 80.6 | -- | -- | Apache 2.0 | ~186 GB | Offload |
| 9 | **DeepSeek-V3.2** | DeepSeek | Dec 2025 | MoE | 685B | ~37B | **73.1*** | -- | 46.4* | -- | MIT | ~404 GB | Too large |
| 10 | **Qwen3.5-27B** | Alibaba | Feb 2026 | Dense+DeltaNet | 27B | 27B | **72.4** | 80.7 | 41.6 | -- | Apache 2.0 | ~17 GB | Any single GPU |
| 11 | **Devstral 2 123B** | Mistral | Dec 2025 | Dense | 123B | 123B | **72.2** | -- | 32.6 | -- | Modified-MIT | ~74 GB | TP=4 FP8 (tight) |
| 12 | **Qwen3.5-122B-A10B** | Alibaba | Feb 2026 | MoE+DeltaNet | 122B | 10B | **72.0** | 78.9 | 49.4 | 72.2 | Apache 2.0 | ~74 GB | Offload |
| 13 | **Qwen3-Coder-Next** | Alibaba | Feb 2026 | MoE+DeltaNet | 80B | 3B | **70.6** | -- | -- | -- | Apache 2.0 | ~46 GB | TP=4 Q4 |

*DeepSeek-V3.2 benchmarks from model card comparison table, not self-reported for coding.

### Tier B: Solid Coding Models (SWE-bench 60-70%)

| # | Model | Org | Released | Arch | Total | Active | SWE-bench V | LCBv6 | TB2 | BFCL-V4 | License | Q4 Size | Fits VRAM? |
|---|-------|-----|----------|------|-------|--------|-------------|-------|-----|---------|---------|---------|------------|
| 14 | **Qwen3.5-35B-A3B** | Alibaba | Feb 2026 | MoE+DeltaNet | 35B | 3B | **69.2** | 74.6 | 40.5 | 67.3 | Apache 2.0 | ~21 GB | Any single GPU |
| 15 | **Devstral Small 2 24B** | Mistral | Dec 2025 | Dense | 24B | 24B | **65.8-68.0** | -- | 22.5-32.0 | -- | Apache 2.0 | ~15 GB | Any single GPU |
| 16 | **DeepSeek-V3.1** | DeepSeek | Sep 2025 | MoE | 671B | 37B | **66.0** | 74.8 | -- | -- | MIT | ~404 GB | Too large |

### Tier C: Useful Coding Models (SWE-bench 40-60%)

| # | Model | Org | Released | Arch | Total | Active | SWE-bench V | LCBv6 | TB2 | BFCL-V4 | License | Q4 Size | Fits VRAM? |
|---|-------|-----|----------|------|-------|--------|-------------|-------|-----|---------|---------|---------|------------|
| 17 | **GLM-4.7-Flash** | Zhipu AI | Jan 2026 | MoE | 30B | 3B | **59.2** | 64.0 | -- | -- | MIT | ~18 GB | Any single GPU |
| 18 | **Qwen3-Coder-30B-A3B** | Alibaba | Aug 2025 | MoE | 30B | 3.3B | **50.3** | -- | -- | -- | Apache 2.0 | ~18.6 GB | Any single GPU |
| 19 | **Qwen3-32B** | Alibaba | May 2025 | Dense | 32B | 32B | ~55-65 est. | 70.7(v5) | -- | **68.2** | Apache 2.0 | ~19.8 GB | Any single GPU |
| 20 | **NVIDIA Nemotron 3 Nano** | NVIDIA | Dec 2025 | Mamba2+MoE | 30B | 3.5B | **38.8** | 68.3 | 8.5(hard) | 53.8 | Nemotron | ~18 GB | Any single GPU |

### Tier D: Small/Niche Coding Models

| # | Model | Org | Released | Arch | Total | Active | Key Bench | License | Q4 Size | Fits VRAM? |
|---|-------|-----|----------|------|-------|--------|-----------|---------|---------|------------|
| 21 | **Seed-Coder-8B-Reasoning** | ByteDance | Jun 2025 | Dense | 8B | 8B | Surpasses QwQ-32B on IOI'24 | MIT | ~5 GB | Any single GPU |
| 22 | **Moonlight-16B-A3B** | Moonshot | Jan 2026 | MoE | 16B | 3B | -- | MIT | ~10 GB | Any single GPU |
| 23 | **Ministral 3 14B** | Mistral | Jan 2026 | Dense | 14B | 14B | -- | Apache 2.0 | ~9 GB | Any single GPU |
| 24 | **Ministral 3 8B** | Mistral | Jan 2026 | Dense | 8B | 8B | -- | Apache 2.0 | ~5 GB | Any single GPU |
| 25 | **Phi-4-mini-Reasoning** | Microsoft | Dec 2025 | Dense | 14B | 14B | 25%+ over Phi-4 on LCB | MIT | ~9 GB | Any single GPU |
| 26 | **Qwen2.5-Coder-32B-Instruct** | Alibaba | Nov 2024 | Dense | 32B | 32B | Aider: 16.4% | Apache 2.0 | ~19.8 GB | Any single GPU |
| 27 | **Qwen2.5-Coder-14B-Instruct** | Alibaba | Nov 2024 | Dense | 14B | 14B | -- | Apache 2.0 | ~9.5 GB | Any single GPU |
| 28 | **GPT-OSS-20B** | OpenAI | Aug 2025 | Dense | 20B | 20B | Aider: 41.8%(120B) | Apache 2.0 | ~12 GB | Any single GPU |
| 29 | **Jan-v3-4B** | janhq | Jan 2026 | Dense | 4B | 4B | -- | Apache 2.0 | ~2.5 GB | Any single GPU |

### Models With Insufficient Coding Benchmarks (General-Purpose but Code-Capable)

| # | Model | Org | Released | Arch | Total | Active | Notes | License |
|---|-------|-----|----------|------|-------|--------|-------|---------|
| 30 | **Mistral Large 3 675B** | Mistral | Dec 2025 | MoE | 675B | 41B | General frontier, not coding-specialized | Apache 2.0 |
| 31 | **DeepSeek-V3.2-Speciale** | DeepSeek | Dec 2025 | MoE | 685B | ~37B | Reasoning-focused, NO tool calling | MIT |
| 32 | **Llama 4 Scout 109B** | Meta | Apr 2025 | MoE | 109B | 17B | 10M context, weak coding vs Qwen | Llama 4 |
| 33 | **Llama 3.3 70B** | Meta | 2024 | Dense | 70B | 70B | Solid tool calling (84.8%), aging | Llama 3.3 |
| 34 | **Codestral 22B** | Mistral | 2024 | Dense | 22B | 22B | HumanEval 86.6%, MNPL license | Non-production |

### Community Fine-Tunes and Variants

| # | Model | Base | Notes | Downloads |
|---|-------|------|-------|-----------|
| 35 | **Qwen3-Coder-Next-REAM (60B)** | Qwen3-Coder-Next | Expert-merged compression, 60B total (25% smaller) | 357 |
| 36 | **GPT-OSS-20B Coding Distill** | GPT-OSS-20B | Community fine-tune with GPT-5.1/Claude data | 972 |
| 37 | **GLM-4.7-Flash-Claude-Opus-4.5-Distill** | GLM-4.7-Flash | Distilled from Claude Opus 4.5 reasoning | 75.4k |
| 38 | **Strand-Rust-Coder-14B** | Qwen2.5-Coder-14B | Rust-specialized fine-tune | 1.5k |
| 39 | **IQuest-Coder-V1-40B-Loop** | IQuest-Coder | Recurrent transformer variant (2 iterations) | 6.6k |
| 40 | **OpenHands-LM-32B** | Qwen2.5-32B | Agentic coding specialist | 578 |

---

## 2. Detailed Model Profiles

### Step-3.5-Flash (NEW DISCOVERY)

**This model was not in any previous Athanor research and is a major find.**

- **Organization**: StepFun
- **Released**: February 2026
- **Architecture**: 196B total, 11B active per token. MoE with 288 routed experts + 1 shared, top-8 selection. 45-layer Transformer with 3:1 sliding window attention ratio.
- **Multi-Token Prediction**: MTP-3 predicts 4 tokens per forward pass, yielding 100-350 tok/s generation.
- **Benchmarks**:
  - SWE-bench Verified: **74.4%** (higher than Qwen3.5-27B, GLM-4.7, MiMo-V2-Flash)
  - LiveCodeBench v6: **86.4%** (highest of ANY open-weight model)
  - Terminal-Bench 2.0: **51.0%**
  - tau2-Bench: **88.2%** (highest agentic score in survey)
  - AIME 2025: 97.3%
- **Context**: 256K tokens
- **License**: Apache 2.0
- **VRAM**: Q4_K_M ~120 GB. Does NOT fit in Node 1 VRAM (64 GB) or Node 2 VRAM (48 GB).
- **Deployment**: With MoE offloading on Node 1 (88 GB VRAM + 224 GB RAM = 312 GB), Q4 at 120 GB fits easily with 192 GB headroom. 11B active params means expert swapping is fast.
- **vLLM**: Yes, supported. Also SGLang, Transformers, llama.cpp.
- **Speed estimate with offloading**: 20-40 tok/s (small active params + MTP-3 boost, good expert locality)
- **Source**: [HF model card](https://huggingface.co/stepfun-ai/Step-3.5-Flash), [arXiv:2602.10604](https://arxiv.org/abs/2602.10604)

**Why this matters**: Step-3.5-Flash has the highest LiveCodeBench v6 score (86.4%) and highest tau2-Bench score (88.2%) of any open-weight model. At 11B active params with MTP-3, it should be faster than GLM-4.7 (32B active) or MiMo-V2-Flash (15B active) with offloading. The 120 GB Q4 size fits comfortably in Node 1's offloading capacity.

### Qwen3.5-27B (DENSE MODEL RECOMMENDATION)

**Replaces Qwen3-32B as the primary dense model recommendation.**

- **Organization**: Alibaba/Qwen
- **Released**: February 2026
- **Architecture**: 27B dense. 64 layers. Hybrid Gated DeltaNet (75% layers) + Gated Attention (25% layers). NOT a traditional transformer -- uses linear attention for most layers, reducing KV cache dramatically.
- **Benchmarks**:
  - SWE-bench Verified: **72.4%** (vs Qwen3-32B's estimated ~55-65%)
  - LiveCodeBench v6: **80.7** (vs Qwen3-32B's 70.7 on v5)
  - Terminal-Bench 2: **41.6**
  - CodeForces: 1,899 ELO
  - IFEval: 95.0
  - MMLU-Pro: 86.1
- **Context**: 262K native, 1M+ with YaRN
- **License**: Apache 2.0
- **VRAM**:
  - BF16: ~54 GB (fits Node 1 TP=4 with 10 GB headroom, or Node 2 TP=2)
  - FP8: ~27 GB (fits single 5090 with 5 GB headroom)
  - AWQ: ~17 GB (fits ANY single GPU)
  - NVFP4: ~14 GB (fits any Blackwell GPU)
- **Thinking mode**: Default. Generates `<think>...</think>` blocks. Can be disabled.
- **Tool calling**: Yes, Qwen-style with Hermes format
- **Multimodal**: Yes, vision-language (images + video)
- **MTP**: Supports multi-token prediction for speculative decoding
- **vLLM**: Yes, fully supported with `--reasoning-parser qwen3`
- **Source**: [HF model card](https://huggingface.co/Qwen/Qwen3.5-27B)

**Key advantage over Qwen3-32B**: The Gated DeltaNet architecture means 75% of layers use linear attention with O(1) KV cache per token instead of O(n). This dramatically reduces memory pressure at long contexts. A 27B DeltaNet model at 128K context uses less KV cache memory than a 32B standard transformer at 32K context.

### Qwen3.5-35B-A3B (SMALL MOE CHAMPION)

- **Organization**: Alibaba/Qwen
- **Released**: February 2026
- **Architecture**: 35B total, 3B active. MoE with 256 experts, 8 routed + 1 shared. 40 layers. Gated DeltaNet + MoE hybrid.
- **Benchmarks**:
  - SWE-bench Verified: **69.2%**
  - LiveCodeBench v6: **74.6**
  - Terminal-Bench 2: **40.5**
  - BFCL-V4: **67.3**
  - CodeForces: **2028** ELO (highest in survey for models <100B)
  - tau2-Bench: **81.2**
- **Context**: 262K native, 1M+ with YaRN
- **License**: Apache 2.0
- **VRAM**:
  - BF16: ~70 GB (offload)
  - AWQ: ~21 GB (fits 4090, 5090; tight on 16 GB)
  - NVFP4: ~9 GB (fits any Blackwell GPU trivially)
- **vLLM**: Yes, fully supported
- **Source**: [HF model card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)

**Why this matters**: SWE-bench 69.2% in a model that fits on a single 24 GB GPU at AWQ or a single 16 GB GPU at NVFP4. This is within 1.4 points of Qwen3-Coder-Next (70.6%) which needs 46 GB at Q4. Replaces Qwen3-Coder-30B-A3B (50.3%) as the small-MoE recommendation.

### Qwen3.5-122B-A10B (MID-SIZE MOE)

- **Organization**: Alibaba/Qwen
- **Released**: February 2026
- **Architecture**: 122B total, 10B active. MoE with 256 experts, 8 routed + 1 shared. 48 layers. Gated DeltaNet + MoE hybrid.
- **Benchmarks**:
  - SWE-bench Verified: **72.0%**
  - LiveCodeBench v6: **78.9**
  - Terminal-Bench 2: **49.4**
  - BFCL-V4: **72.2**
  - CodeForces: **2100** ELO
  - tau2-Bench: **79.5**
- **Context**: 262K native, 1M+ with YaRN
- **License**: Apache 2.0
- **VRAM**:
  - Q4_K_M: ~74 GB (offload on Node 1)
  - AWQ: ~37 GB (fits Node 1 TP=4 or single 5090 + small headroom)
- **vLLM**: Yes
- **Source**: [HF model card](https://huggingface.co/Qwen/Qwen3.5-122B-A10B)

### Qwen3.5-397B-A17B (FLAGSHIP MOE)

- **Organization**: Alibaba/Qwen
- **Released**: February 2026
- **Architecture**: 397B total, 17B active. MoE with 512 experts, 10 routed + 1 shared. 60 layers. Gated DeltaNet + MoE hybrid.
- **Benchmarks**:
  - SWE-bench Verified: **76.4%**
  - LiveCodeBench v6: **83.6**
  - Terminal-Bench 2: **52.5**
  - BFCL-V4: **72.9**
  - tau2-Bench: **86.7**
- **Context**: 262K native, 1M+ with YaRN
- **License**: Apache 2.0
- **VRAM**: Q4_K_M ~240 GB. Fits Node 1 with heavy offloading (312 GB total, 72 GB headroom).
- **Speed estimate with offloading**: 10-20 tok/s (17B active, DDR4 bandwidth bottleneck)
- **vLLM**: Yes
- **Source**: [HF model card](https://huggingface.co/Qwen/Qwen3.5-397B-A17B)

### Devstral 2 123B (MISTRAL'S CODING FLAGSHIP)

- **Organization**: Mistral AI
- **Released**: December 9, 2025
- **Architecture**: 123B dense transformer. Based on Mistral architecture.
- **Benchmarks**:
  - SWE-bench Verified: **72.2%**
  - SWE-bench Multilingual: **61.3%**
  - Terminal-Bench 2: **32.6%**
- **Context**: 256K tokens
- **License**: Modified MIT (no IP infringement clause)
- **Tool calling**: Yes, `--tool-call-parser mistral`
- **VRAM**:
  - BF16: ~246 GB (offload)
  - FP8: ~123 GB (offload, or barely fits Node 1 TP=5 with 4090: 88 GB)
  - AWQ: ~62 GB (fits Node 1 TP=4 with 2 GB headroom -- very tight)
  - NVFP4: ~31 GB (fits single 5090)
- **vLLM**: Yes, recommended deployment. `--tool-call-parser mistral --enable-auto-tool-choice --tensor-parallel-size 8`
- **Source**: [HF model card](https://huggingface.co/mistralai/Devstral-2-123B-Instruct-2512)

**Deployment note**: At NVFP4 (~31 GB), Devstral 2 could theoretically run on a single 5090 (32 GB). This would be Blackwell-only and needs testing. At AWQ (~62 GB), it fits on Node 1 TP=4 but with essentially zero KV cache headroom -- impractical.

### Devstral Small 2 24B (COMPACT CODING MODEL)

- **Organization**: Mistral AI
- **Released**: December 9, 2025
- **Architecture**: 24B dense. Based on Mistral Small 3.1.
- **Benchmarks**:
  - SWE-bench Verified: **65.8-68.0%** (varies by source -- 68.0% from HF comparison, 65.8% from Ollama)
  - SWE-bench Multilingual: 51.6-55.7%
  - Terminal-Bench 2: 22.5-32.0%
- **Context**: 256-384K tokens
- **License**: Apache 2.0
- **Tool calling**: Yes, Mistral format
- **VRAM**:
  - FP8: ~24 GB (fits 4090 or 5090)
  - AWQ: ~12 GB (fits any GPU)
  - NVFP4: ~6 GB (fits any Blackwell GPU trivially)
- **vLLM**: Yes
- **Source**: [HF model card](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512)

### IQuest-Coder-V1-40B (SLEEPER HIT)

- **Organization**: IQuestLab
- **Released**: December 2025
- **Architecture**: 40B dense. 80 layers, GQA. Code-Flow training paradigm (learns from repository evolution, commit transitions, dynamic code transformations).
- **Benchmarks**:
  - SWE-bench Verified: **76.2%** (top 5 open-weight)
  - LiveCodeBench v6: **81.1**
  - BigCodeBench: 49.9
- **Context**: 128K native
- **License**: Custom "iquestcoder" license (not standard open-source)
- **Variants**: 7B, 14B, 40B (Instruct and Thinking), Loop variants (recurrent)
- **VRAM**:
  - BF16: ~80 GB (offload)
  - FP8: ~40 GB (fits Node 1 TP=4 with 24 GB headroom)
  - AWQ: ~24 GB (fits 4090 or 5090)
- **vLLM**: Yes. `vllm serve IQuestLab/IQuest-Coder-V1-40B-Instruct --tensor-parallel-size 8`
- **Source**: [HF model card](https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Instruct)

**Caution**: Custom license. Read before deploying. Unknown lab with limited track record. SWE-bench scores are scaffold-dependent -- independently verify.

### MiniMax M2.5 (HIGHEST SWE-BENCH OPEN-WEIGHT)

- **Organization**: MiniMax
- **Released**: February 2026
- **Architecture**: MoE, exact architecture details not fully disclosed. ~229B total.
- **Benchmarks**:
  - SWE-bench Verified: **80.2%** (matches Claude Opus 4.5)
  - Multi-SWE-Bench: 51.3%
  - Droid Harness: 79.7%
  - OpenCode Harness: 76.1%
  - BrowseComp: 76.3%
  - AIME25: 86.3%
- **License**: Modified-MIT
- **VRAM**: Q4_K_M estimated ~140 GB. Architecture details unclear for precise sizing.
- **vLLM**: Yes, supported. SGLang recommended.
- **Source**: [HF model card](https://huggingface.co/MiniMaxAI/MiniMax-M2.5)

**Caution**: Architecture not fully disclosed. Weight format and exact parameter count unclear from public docs. Offloading feasibility uncertain.

### NVIDIA Nemotron 3 Nano 30B-A3B (HYBRID ARCHITECTURE)

- **Organization**: NVIDIA
- **Released**: December 2025
- **Architecture**: Hybrid Mamba-2 + Transformer MoE. 30B total, 3.5B active. 52 layers (23 Mamba-2 + 23 MoE + 6 Attention). 128 routed experts + 1 shared, 6 active per token.
- **Benchmarks**:
  - SWE-bench (OpenHands): **38.8%**
  - LiveCodeBench v6: **68.3**
  - BFCL v4: **53.8**
  - tau2-Bench V2: 49.0
  - RULER-100 @ 1M: 86.3 (long-context champion)
  - AIME25 (with tools): **99.2%**
- **Context**: 1M tokens (!)
- **License**: NVIDIA Nemotron Open Model License (commercial use OK)
- **Supported languages**: 19+ languages, 43 programming languages
- **VRAM**:
  - BF16: ~60 GB (Node 1 TP=4)
  - FP8: ~30 GB (fits 5090)
  - NVFP4: available from NVIDIA (fits any Blackwell GPU)
- **vLLM**: Yes, with custom reasoning parser. Also TRT-LLM, SGLang.
- **Source**: [HF model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16), [arXiv:2512.20848](https://arxiv.org/abs/2512.20848)

**Notable**: The Mamba-2 hybrid architecture means sub-quadratic attention for long contexts. 1M token context with 86.3% RULER score is unmatched. However, SWE-bench 38.8% is weak for coding -- this is more of a long-context reasoning model than a coding specialist.

### GLM-4.7-Flash (SMALL AGENTIC MODEL)

- **Organization**: Zhipu AI
- **Released**: January 2026
- **Architecture**: 30B total, 3B active. MoE. Described as "ARC Foundation Model" (Agentic, Reasoning, Coding).
- **Benchmarks**:
  - SWE-bench Verified: **59.2%**
  - LiveCodeBench v6: **64.0**
  - tau2-Bench: **79.5** (outstanding for 3B active)
  - BrowseComp: 42.8
  - AIME 25: 91.6
- **Context**: 131K tokens
- **License**: MIT
- **Tool calling**: Yes, `--tool-call-parser glm47`
- **Speculative decoding**: Supported
- **VRAM**: AWQ ~18 GB, NVFP4 available. Fits any single GPU.
- **vLLM**: Yes (main branch required), SGLang
- **Source**: [HF model card](https://huggingface.co/zai-org/GLM-4.7-Flash)

**Notable**: tau2-Bench 79.5 is the highest agentic score among models under 5B active params. SWE-bench 59.2% vs Qwen3-Coder-30B-A3B 50.3% makes it the strongest small agentic model.

---

## 3. VRAM Fit Analysis

### What Fits Where

#### Single GPU Deployment (no TP, no offload)

| Model | AWQ/Q4 Size | Fits 16 GB? | Fits 24 GB? | Fits 32 GB? | FP8 Size | FP8 on 5090? |
|-------|-------------|-------------|-------------|-------------|----------|--------------|
| **Qwen3.5-35B-A3B** | ~21 GB | No | Yes | Yes | ~35 GB | Yes |
| **Qwen3.5-27B** | ~17 GB | Yes (tight) | Yes | Yes | ~27 GB | Yes |
| **Devstral Small 2 24B** | ~15 GB | Yes (tight) | Yes | Yes | ~24 GB | Yes |
| **GLM-4.7-Flash 30B** | ~18 GB | No | Yes | Yes | ~30 GB | Yes |
| **Nemotron 3 Nano 30B** | ~18 GB | No | Yes | Yes | ~30 GB | Yes |
| **Qwen3-Coder-30B-A3B** | ~18.6 GB | No | Yes | Yes | ~30 GB | Yes |
| **Qwen3-32B** | ~19.8 GB | No | Yes | Yes | ~32 GB | Yes (exact) |
| **Seed-Coder-8B** | ~5 GB | Yes | Yes | Yes | ~8 GB | Yes |
| **Qwen3-14B** | ~9.5 GB | Yes | Yes | Yes | ~14 GB | Yes |
| **Moonlight-16B-A3B** | ~10 GB | Yes | Yes | Yes | ~16 GB | Yes |
| **Phi-4-Reasoning** | ~9 GB | Yes | Yes | Yes | ~14 GB | Yes |

**NVFP4 (Blackwell sm_120 only -- 5070 Ti, 5060 Ti, 5090)**:

| Model | NVFP4 Size | Fits 16 GB? |
|-------|------------|-------------|
| **Qwen3.5-35B-A3B** | ~9 GB | Yes |
| **Qwen3.5-27B** | ~14 GB | Yes (tight) |
| **Devstral Small 2 24B** | ~6 GB | Yes |
| **GLM-4.7-Flash 30B** | ~8 GB | Yes |
| **Qwen3-Coder-30B-A3B** | ~9 GB | Yes |
| **Qwen3-32B** | ~10 GB | Yes |
| **Devstral 2 123B** | ~31 GB | No (5090 only) |

#### Node 1 TP=4 (64 GB across 5070 Ti x4)

| Model | Format | Weight Size | KV Headroom | Verdict |
|-------|--------|------------|-------------|---------|
| **Qwen3-Coder-Next 80B** | Q4 | ~46 GB | ~18 GB | Tight but workable |
| **IQuest-Coder 40B** | FP8 | ~40 GB | ~24 GB | Good fit |
| **Devstral 2 123B** | AWQ | ~62 GB | ~2 GB | Too tight |
| **Qwen3.5-122B-A10B** | AWQ | ~37 GB | ~27 GB | Good fit |
| **Nemotron 3 Nano 30B** | BF16 | ~60 GB | ~4 GB | Tight |

#### Node 1 Offloading (88 GB VRAM + 224 GB DDR4 = 312 GB)

| Model | Q4_K_M Size | Active Params | Est. Speed | SWE-bench |
|-------|-------------|---------------|-----------|-----------|
| **Step-3.5-Flash** | ~120 GB | 11B | **20-40 tok/s** | 74.4% |
| **MiMo-V2-Flash** | ~186 GB | 15B | **15-25 tok/s** | 73.4% |
| **GLM-4.7** | ~214 GB | 32B | **8-15 tok/s** | 73.8% |
| **Qwen3.5-397B-A17B** | ~240 GB | 17B | **10-20 tok/s** | 76.4% |
| **Qwen3.5-122B-A10B** | ~74 GB | 10B | **25-40 tok/s** | 72.0% |
| **MiniMax M2.5** | ~140 GB | ~10B? | **15-30 tok/s** | 80.2% |

---

## 4. Benchmark Cross-Reference

### SWE-bench Verified Rankings (Open-Weight Only)

| Rank | Model | SWE-bench V | Active Params | Fits in VRAM? |
|------|-------|-------------|---------------|---------------|
| 1 | MiniMax M2.5 | 80.2% | ~10B? | Offload |
| 2 | GLM-5 | 77.8% | 40B | Too large |
| 3 | Kimi K2.5 | 76.8% | 32B | Too large |
| 4 | Qwen3.5-397B-A17B | 76.4% | 17B | Offload (tight) |
| 5 | **IQuest-Coder-V1-40B** | **76.2%** | **40B** | **FP8 TP=4** |
| 6 | Step-3.5-Flash | 74.4% | 11B | Offload |
| 7 | GLM-4.7 | 73.8% | 32B | Offload |
| 8 | MiMo-V2-Flash | 73.4% | 15B | Offload |
| 9 | DeepSeek-V3.2 | 73.1% | ~37B | Too large |
| 10 | **Qwen3.5-27B** | **72.4%** | **27B** | **Any single GPU** |
| 11 | **Devstral 2 123B** | **72.2%** | **123B** | **TP=4 AWQ (tight)** |
| 12 | **Qwen3.5-122B-A10B** | **72.0%** | **10B** | **AWQ TP=4 or offload** |
| 13 | **Qwen3-Coder-Next** | **70.6%** | **3B** | **Q4 TP=4** |
| 14 | **Qwen3.5-35B-A3B** | **69.2%** | **3B** | **AWQ any 24GB GPU** |
| 15 | Devstral Small 2 24B | 65.8-68.0% | 24B | Any single GPU |
| 16 | DeepSeek-V3.1 | 66.0% | 37B | Too large |
| 17 | GLM-4.7-Flash | 59.2% | 3B | Any single GPU |
| 18 | Qwen3-Coder-30B-A3B | 50.3% | 3.3B | Any single GPU |

Models in **bold** fit on Athanor hardware (in VRAM or TP=4).

### LiveCodeBench v6 Rankings

| Rank | Model | LCBv6 | Active Params |
|------|-------|-------|---------------|
| 1 | **Step-3.5-Flash** | **86.4** | 11B |
| 2 | Kimi K2.5 | 85.0 | 32B |
| 3 | GLM-4.7 | 84.9 | 32B |
| 4 | Qwen3.5-397B-A17B | 83.6 | 17B |
| 5 | IQuest-Coder-V1-40B | 81.1 | 40B |
| 6 | **Qwen3.5-27B** | **80.7** | 27B |
| 7 | MiMo-V2-Flash | 80.6 | 15B |
| 8 | Qwen3.5-122B-A10B | 78.9 | 10B |
| 9 | Qwen3.5-35B-A3B | 74.6 | 3B |
| 10 | Nemotron 3 Nano | 68.3 | 3.5B |
| 11 | GLM-4.7-Flash | 64.0 | 3B |

### Aider Leaderboard (Open-Weight Only)

| Rank | Model | Aider % | Notes |
|------|-------|---------|-------|
| 1 | DeepSeek-V3.2-Exp (Reasoner) | 74.2% | MoE, too large for local |
| 2 | DeepSeek-V3.2-Exp (Chat) | 70.2% | MoE, too large for local |
| 3 | Qwen3-235B-A22B | 59.6% | Offloadable |
| 4 | Kimi K2 | 59.1% | Too large |
| 5 | DeepSeek R1 | 56.9% | Too large |
| 6 | Qwen3-32B | 40.0% | Fits any GPU |
| 7 | Qwen2.5-Coder-32B-Instruct | 16.4% | Fits any GPU |

**Note**: The Aider leaderboard lags behind SWE-bench and LCB for open-weight model testing. Qwen3.5, Step-3.5-Flash, GLM-4.7, and many other models have NOT been benchmarked on Aider yet.

### BFCL-V4 (Tool Calling)

| Rank | Model | BFCL-V4 |
|------|-------|---------|
| 1 | Qwen3.5-397B-A17B | 72.9 |
| 2 | Qwen3.5-122B-A10B | 72.2 |
| 3 | Qwen3-32B (BFCL v3) | 68.2 |
| 4 | Qwen3.5-35B-A3B | 67.3 |
| 5 | Nemotron 3 Nano 30B | 53.8 |

### tau2-Bench (Agentic)

| Rank | Model | tau2 |
|------|-------|------|
| 1 | GLM-5 | 89.7 |
| 2 | Step-3.5-Flash | 88.2 |
| 3 | GLM-4.7 | 87.4 |
| 4 | Qwen3.5-397B-A17B | 86.7 |
| 5 | Qwen3.5-35B-A3B | 81.2 |
| 6 | Qwen3.5-122B-A10B | 79.5 |
| 7 | GLM-4.7-Flash | 79.5 |
| 8 | Nemotron 3 Nano | 49.0 |

---

## 5. What Changed Since Last Research (Feb 16 / Feb 25)

### New Models Not In Previous Research

| Model | SWE-bench | Why Missed |
|-------|-----------|-----------|
| **Step-3.5-Flash** | 74.4% | StepFun is a Chinese AI lab (less visibility). Released Feb 2026. |
| **Qwen3.5-35B-A3B** | 69.2% | Qwen3.5 family released Feb 16-24. |
| **Qwen3.5-122B-A10B** | 72.0% | Same. |
| **Qwen3.5-397B-A17B** | 76.4% | Same. Partially noted in Feb 25 update. |
| **IQuest-Coder-V1-40B** | 76.2% | Unknown lab. Released Dec 2025. Very low visibility. |
| **Devstral 2 123B** | 72.2% | Released Dec 9 2025, was after the Feb 16 research. |
| **Devstral Small 2 24B** | 65.8-68.0% | Same. |
| **Nemotron 3 Nano 30B** | 38.8% | Coding performance was poor, so overlooked. |
| **MiniMax M2.5** | 80.2% | Released Feb 2026. Architecture details limited. |
| **DeepSeek-V3.2** | 73.1% | Released Dec 2025. Was after initial research. |

### Corrections to Previous Research

1. **MiMo-V2-Flash SWE-bench**: Previous doc listed both 80.2% and 73.4%. The 73.4% is from the official model card. The 80.2% appears to be from an optimized scaffold not reproducible in standard deployment. **Use 73.4% as the baseline.**

2. **Qwen3-Coder-Next**: vLLM tool call parser is `qwen3_coder`, not `qwen3_xml` as stated in earlier doc.

3. **DeepSeek-V3.2 exists and is different from V3.1**: V3.2 (685B, Dec 2025) is newer and stronger than V3.1 (671B, Sep 2025). Terminal-Bench 2: 46.4% vs unknown for V3.1. Both are MIT licensed.

---

## 6. Revised Deployment Recommendations

### Primary Configuration (Maximize Quality Per GPU)

| Slot | Model | GPU(s) | Format | VRAM | Speed | SWE-bench | Use Case |
|------|-------|--------|--------|------|-------|-----------|----------|
| **Primary Coding** | Qwen3.5-27B | Node 2 5090 | FP8 | 27/32 GB | 60-80 tok/s | **72.4%** | Complex coding, thinking mode, SWE-grade |
| **Fast Coding** | Qwen3.5-35B-A3B | Node 1 4090 | AWQ | 21/24 GB | 70-100 tok/s | **69.2%** | Interactive coding, tool calling, fast |
| **General Agent** | Qwen3.5-27B or Qwen3-32B | Node 1 TP=4 | AWQ/NVFP4 | 17/64 GB | 40-60 tok/s | 72.4% / 55-65% | Agent backbone, general assistant |
| **Embedding** | Current setup | Node 1 GPU 4 | -- | ~8 GB | -- | -- | RAG, knowledge search |
| **Creative** | ComfyUI | Node 2 5060 Ti | -- | 16 GB | -- | -- | Image/video generation |

**Alternative: Agentic Coding Focus**

| Slot | Model | GPU(s) | Format | VRAM | Speed | SWE-bench | tau2 |
|------|-------|--------|--------|------|-------|-----------|------|
| **Primary** | Qwen3-Coder-Next | Node 1 TP=4 | Q4 | 46/64 GB | 40-60 tok/s | 70.6% | -- |
| **Agentic** | GLM-4.7-Flash | Node 1 4090 | AWQ | 18/24 GB | 70+ tok/s | 59.2% | **79.5** |
| **General** | Qwen3.5-27B | Node 2 5090 | FP8 | 27/32 GB | 60-80 tok/s | 72.4% | -- |

### Offloading Configuration (Maximum Quality)

For batch/overnight workloads where speed is less important:

| Model | Q4 Size | Active Params | Est. Speed | SWE-bench | LiveCodeBench |
|-------|---------|---------------|-----------|-----------|---------------|
| **Step-3.5-Flash** | 120 GB | 11B | 20-40 tok/s | **74.4%** | **86.4** |
| **MiMo-V2-Flash** | 186 GB | 15B | 15-25 tok/s | 73.4% | 80.6 |
| **GLM-4.7** | 214 GB | 32B | 8-15 tok/s | 73.8% | 84.9 |
| **Qwen3.5-397B-A17B** | 240 GB | 17B | 10-20 tok/s | **76.4%** | 83.6 |

**Step-3.5-Flash is the recommended offloading model.** It has:
- The highest LiveCodeBench v6 score of any open-weight model (86.4)
- The 2nd highest tau2-Bench score (88.2)
- SWE-bench 74.4% (higher than GLM-4.7 and MiMo-V2-Flash)
- Only 11B active params (fastest offloading speed)
- MTP-3 for additional throughput boost
- Q4 at 120 GB fits comfortably in Node 1's 312 GB capacity
- Apache 2.0 license

---

## 7. vLLM Compatibility Matrix

| Model | vLLM | Tool Parser | Reasoning Parser | Notes |
|-------|------|-------------|-----------------|-------|
| Qwen3.5-27B | Yes | `hermes` | `qwen3` | Full support |
| Qwen3.5-35B-A3B | Yes | `hermes` | `qwen3` | Full support |
| Qwen3.5-122B-A10B | Yes | `hermes` | `qwen3` | Full support |
| Qwen3.5-397B-A17B | Yes | `hermes` | `qwen3` | Full support |
| Qwen3-Coder-Next | Yes | `qwen3_coder` | -- | Non-thinking only |
| Qwen3-Coder-30B-A3B | Yes | `hermes`/`qwen3_xml` | -- | Full support |
| Qwen3-32B | Yes | `hermes` | `qwen3` | Full support |
| Step-3.5-Flash | Yes | -- | -- | Needs testing |
| GLM-4.7 | Yes | `glm47` | `glm45` | Full support |
| GLM-4.7-Flash | Yes | `glm47` | `glm45` | Needs main branch |
| Devstral 2 123B | Yes | `mistral` | -- | Full support |
| Devstral Small 2 24B | Yes | `mistral` | -- | Full support |
| Nemotron 3 Nano 30B | Yes | Custom | Custom | Custom parser needed |
| IQuest-Coder 40B | Yes | -- | `qwen3` (Thinking) | Needs testing |
| MiMo-V2-Flash | Yes | Custom | -- | SGLang recommended |
| MiniMax M2.5 | Yes | `minimax_m1` | -- | Needs testing |
| DeepSeek-V3.2 | Yes | `deepseek_v31` | -- | Custom template |
| Kimi K2.5 | Yes | `kimi_k2` | -- | Full support |

---

## 8. Architecture Innovation Highlights

### Gated DeltaNet (Qwen3.5 family)

The Qwen3.5 family introduces a hybrid architecture where 75% of layers use **Gated DeltaNet** (linear attention) and 25% use standard **Gated Attention**. This has two major implications:

1. **KV cache reduction**: Linear attention layers have O(1) KV cache per token vs O(n) for standard attention. At 128K context, this reduces KV cache by roughly 3-4x compared to a pure transformer of the same size.

2. **Inference efficiency**: Linear attention is O(n) per token vs O(n^2) for standard attention. This matters most at long contexts.

The practical result: Qwen3.5-27B at 128K context uses roughly the same KV cache memory as Qwen3-32B at 32K context. This is a significant advantage for agentic coding tasks that need long context.

### Multi-Token Prediction (MTP)

Both Step-3.5-Flash (MTP-3, 4 tokens/pass) and MiMo-V2-Flash (MTP, 2-3 tokens/pass) use multi-token prediction heads. This effectively multiplies throughput by 2-4x at the cost of slightly higher per-token compute.

SGLang has native MTP support via `--enable-mtp`. vLLM support varies by model.

### Hybrid Mamba-Transformer (Nemotron 3 Nano)

NVIDIA's approach uses Mamba-2 (state-space model) for 44% of layers, reducing the attention computation for long sequences. This enables 1M token context with 86.3% accuracy on RULER, the best long-context score in the survey. However, the Mamba layers may contribute to weaker coding performance (SWE-bench 38.8%) compared to pure transformer models.

---

## 9. License Summary

| License | Models | Commercial Use |
|---------|--------|---------------|
| **Apache 2.0** | Qwen3.5-*, Qwen3-*, Step-3.5-Flash, MiMo-V2-Flash, Devstral Small 2, Seed-Coder, GPT-OSS, Ministral 3 | Yes |
| **MIT** | GLM-5, GLM-4.7, GLM-4.7-Flash, DeepSeek-V3.x, Phi-4 | Yes |
| **Modified-MIT** | Devstral 2 123B, MiniMax M2.5 | Yes (with IP clause) |
| **Nemotron Open** | Nemotron 3 Nano | Yes |
| **Custom** | IQuest-Coder, Kimi K2.5 | Read license |
| **Non-production** | Codestral 22B | No |
| **Llama** | Llama 3.3 70B, Llama 4 Scout | Yes (with limits) |

---

## 10. Open Questions

1. **Step-3.5-Flash on EPYC 7663**: No benchmarks exist for MoE offloading on DDR4. The MTP-3 feature needs SGLang or compatible vLLM version. Test before committing.

2. **IQuest-Coder SWE-bench reproducibility**: Unknown lab, SWE-bench 76.2% is an extraordinary claim for a 40B dense model. Independently verify with OpenHands or SWE-Agent before trusting.

3. **MiniMax M2.5 local deployment**: Architecture details not fully public. Weight format and expert structure need confirmation. Can it run with standard MoE offloading?

4. **Qwen3.5 DeltaNet vLLM support**: The Gated DeltaNet architecture is non-standard. Verify that vLLM handles the linear attention layers correctly and that KV cache savings materialize in practice.

5. **Devstral 2 at NVFP4 on 5090**: At ~31 GB NVFP4, this model could theoretically run on a single RTX 5090 (32 GB). This would be groundbreaking for a 123B model. Needs testing.

6. **Step-3.5-Flash vLLM tool calling**: The model supports tool calling per the chat template, but no specific vLLM tool parser is documented. May need custom parser or fall back to regex/guided decoding.

---

## 11. Sources

### Model Cards (Official)
- [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B)
- [Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B)
- [Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)
- [Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B)
- [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next)
- [Step-3.5-Flash](https://huggingface.co/stepfun-ai/Step-3.5-Flash)
- [Devstral-2-123B-Instruct-2512](https://huggingface.co/mistralai/Devstral-2-123B-Instruct-2512)
- [Devstral-Small-2-24B-Instruct-2512](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512)
- [NVIDIA-Nemotron-3-Nano-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16)
- [GLM-4.7](https://huggingface.co/zai-org/GLM-4.7)
- [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash)
- [GLM-5](https://huggingface.co/zai-org/GLM-5)
- [MiMo-V2-Flash](https://huggingface.co/XiaomiMiMo/MiMo-V2-Flash)
- [MiniMax-M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5)
- [Kimi-K2.5](https://huggingface.co/moonshotai/Kimi-K2.5)
- [DeepSeek-V3.2](https://huggingface.co/deepseek-ai/DeepSeek-V3.2)
- [IQuest-Coder-V1-40B-Instruct](https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Instruct)
- [Seed-Coder-8B-Reasoning](https://huggingface.co/ByteDance-Seed/Seed-Coder-8B-Reasoning)
- [Moonlight-16B-A3B-Instruct](https://huggingface.co/moonshotai/Moonlight-16B-A3B-Instruct)

### Leaderboards
- [Aider LLM Leaderboard](https://aider.chat/docs/leaderboards/) - Exercism coding exercises
- [SWE-bench](https://www.swebench.com/) - GitHub issue resolution
- [Vellum LLM Leaderboard](https://www.vellum.ai/llm-leaderboard) - Multi-benchmark aggregation
- [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html) - Berkeley Function Calling

### Technical Papers
- [Step 3.5 Flash: Open Frontier-Level Intelligence with 11B Active Parameters](https://arxiv.org/abs/2602.10604)
- [Nemotron 3 Nano Technical Report](https://arxiv.org/abs/2512.20848)
- [Qwen3 Technical Report](https://arxiv.org/abs/2505.09388)
- [IQuest-Coder: Scaling Laws for Code](https://arxiv.org/abs/2512.13472)

### Inference Frameworks
- [vLLM Tool Calling Docs](https://docs.vllm.ai/en/latest/features/tool_calling/)
- [vLLM Quantization Docs](https://docs.vllm.ai/en/latest/features/quantization/index.html)
- [KTransformers GitHub](https://github.com/kvcache-ai/ktransformers)

### Data Quality Notes
- SWE-bench scores are scaffold-dependent (10-20% variation). All scores are reported by model authors unless noted.
- LiveCodeBench v6 is NOT comparable to v5 or earlier.
- VRAM estimates use rule of thumb: Q4 ~ 0.6 bytes/param, AWQ ~ 0.6 bytes/param, FP8 ~ 1 byte/param, BF16 ~ 2 bytes/param. Actual VRAM includes KV cache and framework overhead.
- Offloading speed estimates assume KTransformers on Node 1 with DDR4 quad-channel (~51 GB/s).
- Models marked "Too large" exceed 312 GB (Node 1 VRAM + RAM) at Q4_K_M.
