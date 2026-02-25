# Exhaustive Reasoning Model Survey: Dec 2025 - Feb 2026

**Date:** 2026-02-25
**Status:** Complete
**Purpose:** Identify every reasoning-specialized, math, and thinking/chain-of-thought model released or updated in the last 90 days. Evaluate against current Qwen3-32B-AWQ deployment.

---

## Executive Summary

The reasoning model landscape has shifted dramatically since Qwen3-32B was deployed. Three developments demand attention:

1. **Qwen3.5 family** (Feb 2026) introduces hybrid DeltaNet + MoE architectures with native multimodal thinking mode. The 35B-A3B variant activates only 3B parameters and could run on a single 16GB GPU.
2. **DeepSeek-V3.2** (Dec 2025) and **GLM-5** (Feb 2026) push frontier reasoning to IMO-gold levels at 685B/744B scale, but are too large for homelab without extreme quantization.
3. **Ministral-3-14B-Reasoning** (Dec 2025) achieves AIME25 85% at 14B -- a new efficiency frontier for small reasoning models.

**Bottom line:** Qwen3.5-27B or Qwen3.5-35B-A3B should replace Qwen3-32B-AWQ on the primary inference cluster. The 35B-A3B MoE is particularly interesting -- its 3B active parameters would dramatically reduce inference latency while maintaining GPQA-Diamond 84.2%.

---

## Hardware Context (Athanor)

| GPU Group | Cards | Combined VRAM | Current Use |
|-----------|-------|---------------|-------------|
| Node 1 TP=4 | 4x RTX 5070 Ti | 64 GB | Qwen3-32B-AWQ (primary) |
| Node 1 Standalone | RTX 4090 | 24 GB | Embeddings + voice |
| Node 2 | RTX 5090 | 32 GB | vLLM + ComfyUI |
| Node 2 | RTX 5060 Ti | 16 GB | ComfyUI |

Current model: **Qwen3-32B-AWQ** on TP=4, ~42 GB VRAM, ~25-35 tok/s, 131K context.

---

## Tier 1: Frontier Reasoning Models (Too Large for Homelab, But Noteworthy)

These models define the current state of the art. They cannot run on Athanor's hardware at full precision but inform what's possible at smaller scales.

### DeepSeek-V3.2 (Dec 1, 2025)

| Property | Value |
|----------|-------|
| **Architecture** | MoE, 685B total params |
| **Active Params** | ~37B (estimated, same as V3) |
| **Base** | DeepSeek-V3.2-Exp-Base |
| **Context** | 128K+ tokens |
| **Thinking Mode** | Yes -- `<think>` blocks, "Speciale" variant for deep reasoning only |
| **License** | MIT |
| **vLLM** | Yes (requires custom encoding, no Jinja template) |
| **HuggingFace** | https://huggingface.co/deepseek-ai/DeepSeek-V3.2 |

**Key Benchmarks:**
| Benchmark | Score |
|-----------|-------|
| MathArena AIME 2026 | 94.17% |
| MathArena HMMT Feb 2026 | 84.09% |
| IMO 2025 | Gold medal |
| IOI 2025 | Gold medal |

**Variants:**
- **DeepSeek-V3.2-Speciale** -- deep reasoning only, no tool calling
- **DeepSeek-V3.2-Exp** -- experimental predecessor (Nov 2025)
- **NVFP4 quantized** -- nvidia/DeepSeek-V3.2-NVFP4 (394B effective)

**Homelab Assessment:** At 685B, requires 8x H100 80GB minimum even with FP8. NVFP4 at 394B still far exceeds 64GB TP=4 cluster. Not viable.

---

### GLM-5 (Feb 13, 2026)

| Property | Value |
|----------|-------|
| **Architecture** | MoE, 744B total / 40B active |
| **Training Data** | 28.5T tokens |
| **Context** | 202,752 tokens (for reasoning tasks) |
| **Thinking Mode** | Yes -- interleaved thinking, preserved thinking across turns |
| **License** | MIT |
| **vLLM** | Yes -- `--reasoning-parser glm45 --tool-call-parser glm47` |
| **HuggingFace** | https://huggingface.co/zai-org/GLM-5 |

**Key Benchmarks:**
| Benchmark | GLM-5 | vs. Comparison |
|-----------|-------|----------------|
| AIME 2026 I | 92.7% | Claude Opus: 93.3% |
| GPQA-Diamond | 86.0% | Gemini 3: 91.9% |
| SWE-bench Verified | 77.8% | Claude Opus: 80.9% |
| HLE (w/ Tools) | 50.4% | Kimi K2.5: 51.8% |
| BrowseComp | 62.0% | -- |

**Homelab Assessment:** 744B total. FP8 variant exists but still needs 8x high-end GPUs. Not viable for homelab.

---

### DeepSeek-Math-V2 (Nov 27, 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Based on DeepSeek-V3.2-Exp-Base, 685B |
| **Specialization** | Self-verifiable mathematical reasoning with LLM-based verifier |
| **License** | Apache 2.0 |
| **HuggingFace** | https://huggingface.co/deepseek-ai/DeepSeek-Math-V2 |

**Key Benchmarks:**
| Benchmark | Score |
|-----------|-------|
| IMO 2025 | Gold-level |
| CMO 2024 | Gold-level |
| Putnam 2024 | 118/120 (with scaled test-time compute) |

**Homelab Assessment:** Same scale as V3.2. Not viable.

---

## Tier 2: Homelab-Viable Reasoning Models (Primary Candidates)

These models can run on Athanor's hardware and represent direct upgrades or alternatives to Qwen3-32B-AWQ.

### Qwen3.5-27B (Feb 23-24, 2026) -- TOP CANDIDATE

| Property | Value |
|----------|-------|
| **Architecture** | Hybrid: Gated DeltaNet (linear attention) + Gated Attention + FFN |
| **Parameters** | 27B dense |
| **Layout** | 64 layers: 16x (3x DeltaNet->FFN + 1x Attention->FFN) |
| **Context** | 262,144 native, extendable to 1,010,000 (YaRN) |
| **Thinking Mode** | Yes -- enabled by default, `<think>` blocks, toggleable |
| **Multimodal** | Yes -- text + image + video (text-only mode via `--language-model-only`) |
| **License** | Apache 2.0 |
| **vLLM** | Yes -- `--reasoning-parser qwen3` |
| **HuggingFace** | https://huggingface.co/Qwen/Qwen3.5-27B |

**Key Benchmarks:**
| Benchmark | Qwen3.5-27B | Qwen3-32B (current) |
|-----------|-------------|---------------------|
| MMLU-Pro | 86.1 | ~82 (est.) |
| MMLU-Redux | 93.2 | -- |
| SuperGPQA | 65.6 | -- |
| IFEval | 95.0 | -- |
| SWE-bench Verified | 72.4 | -- |
| LiveCodeBench v6 | 80.7 | -- |
| C-Eval | 90.5 | -- |

**VRAM Estimate (text-only AWQ INT4):** ~16-18 GB (fits single 5070 Ti or 4090)
**VRAM Estimate (text-only FP16):** ~54 GB (fits TP=4 at 64 GB)
**VRAM Estimate (full multimodal):** ~60 GB+ (tight on TP=4)

**AWQ Quantizations Available:**
- `cyankiwi/Qwen3.5-27B-AWQ-BF16-INT4` (431 downloads) -- 12B effective
- `cyankiwi/Qwen3.5-27B-AWQ-BF16-INT8` (338 downloads) -- 14B effective
- `cyankiwi/Qwen3.5-27B-AWQ-4bit` -- 7B effective

**Why This Matters:** The Gated DeltaNet architecture is a significant innovation -- it provides linear-time attention (O(n) vs O(n^2)) for 75% of layers while maintaining full attention for every 4th layer. This means much faster long-context inference. The 27B size fits comfortably in the same VRAM envelope as Qwen3-32B-AWQ with likely better benchmarks across the board.

---

### Qwen3.5-35B-A3B (Feb 23-24, 2026) -- EFFICIENCY CHAMPION

| Property | Value |
|----------|-------|
| **Architecture** | Hybrid MoE: Gated DeltaNet + Gated Attention + MoE |
| **Total Parameters** | 35B |
| **Active Parameters** | 3B (8 routed + 1 shared expert per token) |
| **Experts** | 256 total, 9 activated per token |
| **Expert Intermediate Dim** | 512 |
| **Layout** | 40 layers: 10x (3x DeltaNet->MoE + 1x Attention->MoE) |
| **Context** | 262,144 native, extendable to 1,010,000 (YaRN) |
| **Thinking Mode** | Yes -- enabled by default |
| **Multimodal** | Yes -- text + image + video |
| **License** | Apache 2.0 |
| **vLLM** | Yes -- `--reasoning-parser qwen3` |
| **HuggingFace** | https://huggingface.co/Qwen/Qwen3.5-35B-A3B |

**Key Benchmarks:**
| Benchmark | Qwen3.5-35B-A3B |
|-----------|-----------------|
| MMLU-Pro | 85.3 |
| MMLU-Redux | 93.3 |
| SuperGPQA | 63.4 |
| GPQA-Diamond | 84.2 |
| IFEval | 91.9 |
| SWE-bench Verified | 69.2 |
| HMMT Nov 25 | 89.2 |
| Codeforces | 2028 |
| LiveCodeBench v6 | implied high |

**VRAM Estimate (text-only, FP16):** ~70 GB total weights (but only ~6 GB active per forward pass!)
**VRAM Estimate (text-only, AWQ INT4):** ~18-20 GB total weights
**VRAM Estimate (single GPU, AWQ 4-bit):** Potentially fits single RTX 5070 Ti 16GB

**AWQ Quantizations Available:**
- `cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit` -- 7B effective
- `cyankiwi/Qwen3.5-35B-A3B-AWQ-8bit` -- 12B effective
- `QuantTrio/Qwen3.5-35B-A3B-AWQ` -- 36B effective (full precision MoE)

**Why This Matters:** This is potentially the most important model for Athanor. With only 3B active parameters per token, inference speed should be dramatically faster than Qwen3-32B (which activates all 32B params). The GPQA-Diamond 84.2% score is remarkable for a 3B-active model -- it approaches frontier model territory. The AWQ INT4 variant at ~7B effective size could potentially run on a SINGLE 16GB GPU while delivering near-frontier reasoning.

**Critical Question:** vLLM MoE support with AWQ on Blackwell GPUs needs verification. The standard AWQ + Marlin kernel crash on Blackwell (sm_120) is known. The `--quantization awq` flag (not Marlin) should work but MoE-specific AWQ handling needs testing.

---

### Qwen3.5-122B-A10B (Feb 23-24, 2026) -- STRETCH CANDIDATE

| Property | Value |
|----------|-------|
| **Architecture** | Hybrid MoE: Gated DeltaNet + Gated Attention + MoE |
| **Total Parameters** | 122B |
| **Active Parameters** | 10B |
| **Context** | 262,144 native, extendable to 1M |
| **Thinking Mode** | Yes |
| **Multimodal** | Yes |
| **License** | Apache 2.0 |
| **vLLM** | Yes |
| **HuggingFace** | https://huggingface.co/Qwen/Qwen3.5-122B-A10B |

**AWQ Quantizations Available:**
- `cyankiwi/Qwen3.5-122B-A10B-AWQ-4bit` -- 25B effective
- `QuantTrio/Qwen3.5-122B-A10B-AWQ` -- 125B effective

**VRAM Estimate (AWQ INT4, text-only):** ~25-30 GB -- fits TP=2 or large single GPU
**VRAM Estimate (FP8, text-only):** ~65 GB -- tight on TP=4

**Homelab Assessment:** The AWQ INT4 at 25B effective could fit on TP=2 (32 GB) or even the RTX 5090 alone (32 GB). With 10B active params, speed should be very good. This is a viable "beast mode" model.

---

### Qwen3.5-397B-A17B (Feb 22-23, 2026) -- FLAGSHIP, EXTREME QUANTIZATION ONLY

| Property | Value |
|----------|-------|
| **Architecture** | Hybrid MoE: Gated DeltaNet + Gated Attention + MoE |
| **Total Parameters** | 397B |
| **Active Parameters** | 17B |
| **Experts** | 512 total, 10 routed + 1 shared |
| **Context** | 262,144 native, extendable to 1M |
| **Thinking Mode** | Yes |
| **License** | Apache 2.0 |
| **vLLM** | Yes |
| **HuggingFace** | https://huggingface.co/Qwen/Qwen3.5-397B-A17B |

**Key Benchmarks:**
| Benchmark | Qwen3.5-397B-A17B |
|-----------|--------------------|
| MMLU-Pro | 87.8 |
| HMMT Feb 2025 | 94.8 |
| AIME 2026 | 91.3 |
| LiveCodeBench v6 | 83.6 |
| GPQA-Diamond | implied very high |
| BFCL-V4 | 72.9 |
| MathVision | 88.6 |

**VRAM Estimate (FP8):** ~400 GB -- not viable
**VRAM Estimate (AWQ INT4):** ~100+ GB -- not viable on TP=4 (64 GB)

**Homelab Assessment:** Even AWQ INT4 exceeds available VRAM. Would need GGUF offloading to system RAM (224 GB on Node 1) with KTransformers or similar, but latency would be poor.

---

### GLM-4.7 (Jan 29, 2026)

| Property | Value |
|----------|-------|
| **Architecture** | MoE (glm4_moe) |
| **Total Parameters** | ~358B (based on GGUF sizes) |
| **Context** | 131,072 tokens |
| **Thinking Mode** | Yes -- "Interleaved Thinking" + "Preserved Thinking" (retains across turns) |
| **License** | MIT |
| **vLLM** | Yes -- `--reasoning-parser glm45 --tool-call-parser glm47` |
| **HuggingFace** | https://huggingface.co/zai-org/GLM-4.7 |

**Key Benchmarks:**
| Benchmark | GLM-4.7 | GLM-4.6 |
|-----------|---------|---------|
| MMLU-Pro | 84.3 | 83.2 |
| GPQA-Diamond | 85.7 | 81.0 |
| SWE-bench Verified | 73.8 | 68.0 |
| SWE-bench Multilingual | 66.7 | 53.8 |
| Terminal Bench 2.0 | 41.0 | 24.5 |
| HLE (w/ Tools) | 42.8 | 30.4 |

**Flash Variant:** GLM-4.7-Flash -- 30B size, likely a smaller dense or MoE variant. Very popular (286K downloads for GGUF). If this is a distilled or smaller MoE version, it could be viable.

**Homelab Assessment:** Full GLM-4.7 at ~358B is too large. The Flash variant at 30B is promising but needs architecture investigation. FP8 variant exists. "Preserved Thinking" across multi-turn conversations is a unique and valuable feature for agent workloads.

---

### Ministral-3-14B-Reasoning-2512 (Dec 25, 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense transformer, 13.5B LM + 0.4B vision encoder |
| **Parameters** | 14B total |
| **Context** | 256K tokens |
| **Thinking Mode** | Yes -- reasoning traces via `reasoning_content` in streaming |
| **Multimodal** | Yes (vision) |
| **License** | Apache 2.0 |
| **vLLM** | Yes -- `--reasoning-parser mistral --tool-call-parser mistral` (v0.12.0+) |
| **HuggingFace** | https://huggingface.co/mistralai/Ministral-3-14B-Reasoning-2512 |

**Key Benchmarks:**
| Benchmark | Score |
|-----------|-------|
| AIME 2025 | 85.0% |
| AIME 2024 | 89.8% |
| GPQA-Diamond | 71.2% |
| LiveCodeBench | 64.6% |
| MATH Maj@1 | 90.4% |
| Arena Hard | 55.1% |

**VRAM Estimate:** ~28 GB (BF16), <24 GB (quantized). Fits single RTX 4090 or RTX 5090.

**Why This Matters:** AIME25 85% at 14B is extraordinary efficiency. This is the best reasoning-per-VRAM-GB model available. Could serve as a fast secondary reasoning model on the 4090 or 5090, handling tasks that don't need the full 32B-class model.

---

### Qwen3-Coder-Next (Feb 4, 2026)

| Property | Value |
|----------|-------|
| **Architecture** | Hybrid MoE: DeltaNet + Attention, 512 experts, 10 activated |
| **Total Parameters** | 80B |
| **Active Parameters** | 3B |
| **Hidden Dimension** | 2048 |
| **Layers** | 48 |
| **Context** | 262,144 tokens |
| **Thinking Mode** | Yes (via Qwen3 architecture) |
| **License** | Apache 2.0 |
| **vLLM** | Yes (v0.15.0+) -- `--tool-call-parser qwen3_coder` |
| **HuggingFace** | https://huggingface.co/Qwen/Qwen3-Coder-Next |

**VRAM Estimate (AWQ INT4):** ~40-45 GB -- fits TP=4

**Why This Matters:** Coding-specialized reasoning with only 3B active params. 550K downloads in first month indicates strong community adoption. The 80B total / 3B active architecture means expert knowledge is distributed across 512 experts while keeping inference fast.

---

### DeepSeek-R1-Distill-Qwen-32B (Jan 22, 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense transformer (Qwen2.5-32B base) |
| **Parameters** | 32.5B |
| **Context** | 32,768 tokens |
| **Thinking Mode** | Yes -- `<think>` blocks (must enforce at start) |
| **License** | MIT |
| **vLLM** | Yes |
| **HuggingFace** | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B |

**Key Benchmarks:**
| Benchmark | Score |
|-----------|-------|
| AIME 2024 | 72.6% |
| MATH-500 | 94.3% |
| GPQA-Diamond | 62.1% |
| LiveCodeBench | 57.2% |
| Codeforces Rating | 1691 |

**Homelab Assessment:** Outperforms o1-mini on multiple benchmarks. However, Qwen3-32B (current) and especially Qwen3.5-27B are likely superior given their later training. The 32K context is a significant limitation vs. 131K (Qwen3) or 262K (Qwen3.5).

---

### Cohere Command-A-Reasoning-08-2025 (Aug 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense transformer with sliding window (4096) + global attention |
| **Parameters** | 111B |
| **Context** | 256K input / 32K output |
| **Thinking Mode** | Yes -- `<START_THINKING>` / `<END_THINKING>` tags |
| **License** | CC-BY-NC (non-commercial) |
| **Languages** | 23 |
| **HuggingFace** | https://huggingface.co/CohereLabs/command-a-reasoning-08-2025 |

**Homelab Assessment:** Non-commercial license (CC-BY-NC) and 111B dense make this impractical. Included for completeness only.

---

## Tier 3: Small Reasoning Models (<14B)

### Phi-4-reasoning / Phi-4-reasoning-plus (Apr 30, 2025)

| Property | Phi-4-reasoning | Phi-4-reasoning-plus |
|----------|-----------------|----------------------|
| **Architecture** | Dense transformer | Dense transformer |
| **Parameters** | 14B | 14B |
| **Context** | 32K | 32K |
| **Thinking Mode** | Yes (CoT traces) | Yes (1.5x longer traces) |
| **License** | MIT | MIT |
| **Training** | SFT on o3-mini traces | SFT + outcome-based RL |
| **AIME 2024** | 75.3% | 81.3% |
| **AIME 2025** | 62.9% | 78.0% |
| **GPQA-Diamond** | 65.8% | 68.9% |
| **OmniMath** | 76.6% | 81.9% |
| **LiveCodeBench** | 53.8% | 53.1% |
| **HuggingFace** | https://huggingface.co/microsoft/Phi-4-reasoning | https://huggingface.co/microsoft/Phi-4-reasoning-plus |

**Homelab Assessment:** Good 14B reasoning models but Ministral-3-14B-Reasoning (AIME25: 85%) significantly outperforms on math. Phi-4's 32K context limit is also restrictive. MIT license is attractive.

---

### Phi-4-mini-reasoning (Apr 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense transformer |
| **Parameters** | 3.8B |
| **License** | MIT |
| **HuggingFace** | https://huggingface.co/microsoft/Phi-4-mini-reasoning |

**Homelab Assessment:** Tiny reasoning model. Could be useful for edge/phone deployment but not competitive for primary inference.

---

### ZAYA1-reasoning-base (Nov 26, 2025)

| Property | Value |
|----------|-------|
| **Architecture** | MoE with Compressed Convolutional Attention (CCA) |
| **Total Parameters** | 8.3B |
| **Active Parameters** | 800M |
| **Tokenizer** | Gemma3 |
| **License** | Apache 2.0 |
| **Innovation** | First model trained end-to-end on AMD hardware/software |
| **HuggingFace** | https://huggingface.co/Zyphra/ZAYA1-reasoning-base |

**Claims:** Competitive with Qwen3 at comparable scale, outperforms SmolLM3 and Phi4, nearly matches Qwen3 thinking models on math/coding.

**Homelab Assessment:** Interesting architecture but 800M active params is too small for primary reasoning. The CCA innovation (attention in latent space) is worth watching for future models.

---

### Seed-Coder-8B-Reasoning (May 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense transformer |
| **Parameters** | 8B |
| **Developer** | ByteDance |
| **HuggingFace** | https://huggingface.co/ByteDance-Seed/Seed-Coder-8B-Reasoning |

**Homelab Assessment:** Coding-focused 8B reasoning model. Outclassed by Ministral-3-14B and newer models.

---

### DeepSeek-R1 Distilled Small Models (Jan 2025)

| Model | Base | AIME 2024 | MATH-500 | GPQA | License |
|-------|------|-----------|----------|------|---------|
| R1-Distill-Qwen-1.5B | Qwen2.5-Math-1.5B | 28.9% | 83.9% | 33.8% | MIT |
| R1-Distill-Qwen-7B | Qwen2.5-Math-7B | 55.5% | 92.8% | 49.1% | MIT |
| R1-Distill-Qwen-14B | Qwen2.5-14B | 69.7% | 93.9% | 59.1% | MIT |
| R1-Distill-Llama-8B | Llama-3.1-8B | 50.4% | 89.1% | 49.0% | MIT |
| R1-Distill-Llama-70B | Llama-3.3-70B | 70.0% | 94.5% | 65.2% | MIT |

**Homelab Assessment:** R1-Distill-Qwen-14B is reasonable at 14B but Ministral-3-14B-Reasoning beats it handily (AIME25 85% vs AIME24 69.7%). R1-Distill-Llama-70B needs too much VRAM without heavy quantization.

---

### Older/Legacy Models (Not Recommended)

| Model | Size | Release | Status |
|-------|------|---------|--------|
| Marco-o1 (AIDC-AI) | 8B | Nov 2024 | Outdated, outperformed |
| Skywork-o1-Open-Llama-3.1-8B | 8B | Nov 2024 | PRM-based, outdated |
| NuminaMath-7B-TIR/CoT | 7B | Jul 2024 | Outdated |
| QwQ-32B | 32.5B | Mar 2025 | Superseded by Qwen3/3.5 |
| K0-Math variants | 15B | Aug 2025 | Competition fine-tunes, not general |

---

## Tier 4: Non-Reasoning Models With Thinking Mode

These are not reasoning-specialized but support thinking/chain-of-thought mode:

### Llama 4 Maverick (Apr 2025)

| Property | Value |
|----------|-------|
| **Architecture** | MoE, 17B active / 400B total, 128 experts |
| **Context** | 1M tokens |
| **GPQA-Diamond** | 69.8% |
| **MATH** | 61.2% |
| **License** | Llama 4 Community License |
| **HuggingFace** | https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct |

**Homelab Assessment:** 400B total is too large. GPQA 69.8% is uncompetitive for a reasoning task. Llama license is more restrictive than Apache 2.0.

### Gemma 3 27B-IT (2025)

| Property | Value |
|----------|-------|
| **Architecture** | Dense, 27B |
| **MATH** | 50.0% |
| **GPQA** | 24.3% |
| **License** | Gemma (Google terms) |

**Homelab Assessment:** Reasoning scores are not competitive. Not a reasoning model.

---

## Comparative Analysis: Models That Fit Athanor

### GPQA-Diamond Comparison (Higher = Better)

| Model | GPQA-Diamond | Active Params | VRAM (AWQ) | License |
|-------|-------------|---------------|------------|---------|
| **Qwen3.5-35B-A3B** | **84.2%** | **3B** | ~18 GB | Apache 2.0 |
| Qwen3.5-27B | ~80%+ (est.) | 27B | ~16-18 GB | Apache 2.0 |
| GLM-4.7 | 85.7% | unknown | ~180 GB | MIT |
| Ministral-3-14B-R | 71.2% | 14B | <24 GB | Apache 2.0 |
| Phi-4-reasoning-plus | 68.9% | 14B | ~28 GB | MIT |
| DeepSeek-R1-Distill-32B | 62.1% | 32B | ~20 GB | MIT |
| Qwen3-32B (current) | ~60% (est.) | 32B | ~20 GB | Apache 2.0 |

### AIME Performance (Higher = Better)

| Model | AIME Score | Test Year | Active Params |
|-------|-----------|-----------|---------------|
| **Ministral-3-14B-R** | **89.8%** | **AIME 2024** | **14B** |
| **Ministral-3-14B-R** | **85.0%** | **AIME 2025** | **14B** |
| Qwen3.5-35B-A3B | 89.2% | HMMT Nov 25 | 3B |
| Phi-4-reasoning-plus | 81.3% | AIME 2024 | 14B |
| Phi-4-reasoning-plus | 78.0% | AIME 2025 | 14B |
| Phi-4-reasoning | 75.3% | AIME 2024 | 14B |
| DeepSeek-R1-Distill-32B | 72.6% | AIME 2024 | 32B |

### Coding Performance (SWE-bench Verified, Higher = Better)

| Model | SWE-bench | Active Params |
|-------|-----------|---------------|
| Qwen3.5-27B | 72.4% | 27B |
| Qwen3.5-35B-A3B | 69.2% | 3B |
| Ministral-3-14B-R | ~64.6% (LCB) | 14B |
| DeepSeek-R1-Distill-32B | 57.2% (LCB) | 32B |

### Inference Efficiency (Lower Active Params = Faster)

| Model | Total Params | Active Params | Expected tok/s (est.) |
|-------|-------------|---------------|-----------------------|
| **Qwen3.5-35B-A3B** | 35B | **3B** | **~80-120 tok/s** |
| Qwen3.5-122B-A10B | 122B | 10B | ~40-60 tok/s |
| Ministral-3-14B-R | 14B | 14B | ~50-60 tok/s |
| Qwen3.5-27B | 27B | 27B | ~30-40 tok/s |
| Qwen3-32B (current) | 32B | 32B | ~25-35 tok/s |

---

## Architecture Innovation: Gated DeltaNet

The Qwen3.5 family introduces a significant architectural change worth understanding:

**Traditional Transformer:** Every layer uses full quadratic attention (O(n^2) in sequence length).

**Qwen3.5 Hybrid:** 75% of layers use **Gated DeltaNet** (linear attention, O(n) in sequence length), and 25% use **Gated Attention** (standard attention). The layout repeats: 3x DeltaNet -> 1x Attention.

**Implications:**
- Long-context inference is dramatically faster (most layers are O(n))
- The periodic full-attention layers maintain reasoning quality
- MoE variants combine this with sparse expert selection for even more efficiency
- This is why Qwen3.5-35B-A3B can achieve GPQA 84.2% with only 3B active params

---

## Quantization Compatibility Notes

### AWQ on Blackwell (sm_120)
- Standard AWQ with Marlin kernels **crashes** on Blackwell
- Must use `--quantization awq` explicitly (not Marlin)
- MoE AWQ quantization is newer and may have additional compatibility issues
- **Qwen3.5 MoE AWQ needs testing** before production deployment

### FP8 Quantization
- Qwen3.5 FP8 variants are officially released (e.g., Qwen3.5-27B-FP8, Qwen3.5-35B-A3B-FP8)
- FP8 is natively supported on Blackwell (sm_120)
- Likely the safer quantization choice for initial deployment

### GPTQ
- `Kbenkhaled/Qwen3.5-27B-W4A16-GPTQ` exists (11B effective)
- GPTQ generally works well with vLLM on Blackwell

---

## Recommendations for Athanor

### Immediate Action: Test Qwen3.5-35B-A3B-FP8

**Why:** 3B active params with GPQA 84.2% is a paradigm shift. If this model works on the TP=4 cluster with FP8 quantization, it delivers frontier-class reasoning at 3-4x the speed of Qwen3-32B.

**Test Plan:**
1. Pull `Qwen/Qwen3.5-35B-A3B-FP8` from HuggingFace
2. Deploy via vLLM with `--reasoning-parser qwen3 --language-model-only` (text-only mode)
3. Benchmark: GPQA sample questions, coding tasks, agent tool-calling
4. Compare tok/s and quality against current Qwen3-32B-AWQ

### Secondary: Test Qwen3.5-27B-FP8

**Why:** Dense 27B with DeltaNet hybrid architecture. If the MoE 35B-A3B has vLLM compatibility issues, the dense 27B is the safer upgrade. Higher SWE-bench (72.4%) than the MoE variant.

### Tertiary: Add Ministral-3-14B-Reasoning on 4090

**Why:** AIME25 85% at 14B fits comfortably on the 4090's 24GB. Could serve as a fast math/reasoning specialist alongside the primary model. Apache 2.0 license, vLLM compatible.

### Stretch: Qwen3.5-122B-A10B-AWQ on TP=4

**Why:** 10B active params with 122B total knowledge could be the "beast mode" reasoning model. The AWQ INT4 at ~25B effective might fit in 64 GB TP=4. Needs testing.

---

## What NOT To Do

1. **Don't chase DeepSeek-V3.2 or GLM-5** -- they require datacenter-scale hardware
2. **Don't use DeepSeek-R1-Distill-Qwen-32B** -- Qwen3-32B and Qwen3.5 variants are strictly better
3. **Don't bother with Marco-o1, Skywork-o1, or NuminaMath** -- outdated, outperformed
4. **Don't use Llama 4 Maverick for reasoning** -- 400B total for mediocre GPQA 69.8%
5. **Don't assume AWQ MoE works on Blackwell** -- test before committing

---

## Open Questions

1. **vLLM MoE + AWQ + Blackwell compatibility:** Does `--quantization awq` work with Qwen3.5 MoE models on sm_120? This is the critical path blocker.
2. **Qwen3.5 text-only VRAM:** The `--language-model-only` flag strips the vision encoder. How much VRAM does this actually save for the 35B-A3B variant?
3. **DeltaNet support in vLLM:** Gated DeltaNet is a new architecture. Is it supported in the NGC vLLM image we're using (v0.11.1)? Likely needs a newer vLLM version.
4. **GLM-4.7-Flash architecture:** Is this a 30B dense model or a smaller MoE? If dense, it's a strong competitor at 30B with GPQA 85.7%.
5. **Qwen3.5 thinking budget control:** Can thinking token budget be controlled (like Anthropic's extended thinking)? The docs only show on/off, not budget limits.
6. **FP8 vs AWQ quality loss:** For MoE models, FP8 may have different quality characteristics than AWQ. Need benchmark comparison.

---

## Sources

- Qwen3.5 model cards: https://huggingface.co/Qwen/Qwen3.5-35B-A3B, https://huggingface.co/Qwen/Qwen3.5-27B, https://huggingface.co/Qwen/Qwen3.5-397B-A17B-FP8
- DeepSeek-V3.2: https://huggingface.co/deepseek-ai/DeepSeek-V3.2
- DeepSeek-R1: https://huggingface.co/deepseek-ai/DeepSeek-R1
- DeepSeek-Math-V2: https://huggingface.co/deepseek-ai/DeepSeek-Math-V2
- GLM-5: https://huggingface.co/zai-org/GLM-5
- GLM-4.7: https://huggingface.co/zai-org/GLM-4.7
- Ministral-3-14B-Reasoning: https://huggingface.co/mistralai/Ministral-3-14B-Reasoning-2512
- Phi-4-reasoning: https://huggingface.co/microsoft/Phi-4-reasoning
- Qwen3-Coder-Next: https://huggingface.co/Qwen/Qwen3-Coder-Next
- ZAYA1: https://huggingface.co/Zyphra/ZAYA1-reasoning-base
- Qwen3-32B: https://huggingface.co/Qwen/Qwen3-32B
- QwQ-32B: https://huggingface.co/Qwen/QwQ-32B
- Llama 4 Maverick: https://huggingface.co/meta-llama/Llama-4-Maverick-17B-128E-Instruct
- Cohere Command-A-Reasoning: https://huggingface.co/CohereLabs/command-a-reasoning-08-2025
- AWQ quantizations: https://huggingface.co/cyankiwi, https://huggingface.co/QuantTrio
- Microsoft Phi-4 blog: https://www.microsoft.com/en-us/research/blog/phi-4-reasoning/
