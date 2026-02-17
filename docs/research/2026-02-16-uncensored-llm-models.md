# Uncensored Open-Weight LLM Models for Local Inference

**Date:** 2026-02-16
**Status:** Complete
**Supports:** ADR-005 (AI Inference Engine), future model selection decisions
**Depends on:** ADR-004 (Node Roles + Hardware Allocation)

---

## Context

Athanor needs uncensored or uncensorable LLMs for local inference across its hardware. "Uncensored" means either: (a) base models with no instruct-tuning refusals, (b) fine-tunes that have had refusals removed (e.g., Dolphin, abliterated variants), or (c) models with weak enough safety layers that system prompts can bypass them. The use case includes creative writing (Empire of Broken Queens), agentic coding, general-purpose reasoning, and tool calling.

### Hardware Targets

| Node | GPUs | Total VRAM | Primary Use |
|------|------|------------|-------------|
| Node 1 (Core) | 4x RTX 5070 Ti | 64 GB | 70B-class models via TP=4 |
| Node 2 (Interface) | RTX 4090 + RTX 5090 | 24 + 32 GB | 14B fast agent + 32B creative |
| VAULT | No GPU | 224 GB RAM | CPU-offload for giant MoE models |
| DEV | RTX 3060 12GB | 12 GB | Embeddings, small utility models |

### VRAM Estimation Formula

For all calculations below:

```
Model VRAM = Parameters (B) x Bytes_per_weight + KV_cache + Overhead (~20%)

Bytes per weight by quantization:
  FP16/BF16:  2.0 bytes/param
  Q8_0:       1.0 bytes/param
  Q6_K:       0.78 bytes/param
  Q5_K_M:     0.68 bytes/param
  Q4_K_M:     0.57 bytes/param
  AWQ INT4:   ~0.5 bytes/param (model only, no KV cache)
  GPTQ INT4:  ~0.5 bytes/param

KV cache at 2K context, GQA: ~1-2 GB for 70B class
KV cache at 32K context, GQA: ~8-16 GB for 70B class
```

Source: [How To Calculate GPU VRAM Requirements](https://apxml.com/posts/how-to-calculate-vram-requirements-for-an-llm), [VRAM Calculator](https://localllm.in/blog/interactive-vram-calculator)

---

## Category 1: 70B+ Class Models (Node 1 — 4x RTX 5070 Ti, 64 GB VRAM)

These models must fit in ~60 GB usable VRAM (reserving ~4 GB for KV cache at short context).

### 1.1 Llama 3.3 70B Instruct (Abliterated)

| Property | Value |
|----------|-------|
| **Parameters** | 70B dense |
| **Architecture** | Transformer, GQA, 128K context |
| **License** | Llama 3.3 Community License (commercial OK, <700M MAU, must prefix "Llama" in derivative names) |
| **Tool calling** | Yes (native in instruct, may degrade in abliterated) |
| **Censorship** | Official instruct has moderate refusals; **abliterated versions fully uncensored** |
| **Abliterated variant** | [huihui-ai/Llama-3.3-70B-Instruct-abliterated](https://huggingface.co/huihui-ai/Llama-3.3-70B-Instruct-abliterated) |
| **GGUF quants** | [bartowski/Llama-3.3-70B-Instruct-abliterated-GGUF](https://huggingface.co/bartowski/Llama-3.3-70B-Instruct-abliterated-GGUF) |

**VRAM by quantization (model weights only):**

| Quant | Weight Size | + KV (2K ctx) | + KV (32K ctx) | Fits 64 GB? |
|-------|-------------|---------------|----------------|-------------|
| FP16 | ~140 GB | ~142 GB | ~156 GB | No |
| Q8_0 | ~70 GB | ~72 GB | ~86 GB | No |
| Q6_K | ~55 GB | ~57 GB | ~71 GB | Tight at short ctx |
| Q5_K_M | ~48 GB | ~50 GB | ~64 GB | Yes (short ctx) |
| Q4_K_M | ~40 GB | ~42 GB | ~56 GB | **Yes** |
| AWQ INT4 | ~35 GB | ~37 GB | ~51 GB | **Yes** |

**Benchmarks (base Llama 3.3 70B Instruct):**

| Benchmark | Score |
|-----------|-------|
| MMLU | 86.0 |
| MMLU-Pro | 69.0 |
| GPQA | 51.0 |
| HumanEval | 88.4-89.0 |
| IFEval | 92.1 |

Source: [Llama 3.3 70B Specs](https://apxml.com/models/llama-3-3-70b), [Unsloth Fine-tune Guide](https://unsloth.ai/blog/llama3-3)

**Estimated tok/s on 4x RTX 5070 Ti TP=4 (PCIe, no NVLink):**
- AWQ INT4: ~25-35 tok/s single-user (extrapolated from 4x A6000 benchmark at ~420-470 TPS throughput)
- Q4_K_M via llama.cpp: ~20-30 tok/s single-user
- PCIe TP penalty: expect ~40-60% of theoretical NVLink performance due to 32 GB/s PCIe bottleneck

Source: [4x A6000 vLLM Benchmark](https://www.databasemart.com/blog/vllm-gpu-benchmark-a6000-4), [vLLM Parallelism Docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)

**Verdict:** The workhorse. Best-understood 70B architecture, massive community support, proven abliteration. Q4_K_M fits comfortably in 64 GB with room for KV cache. This is your primary 70B candidate.

---

### 1.2 Qwen3-32B (Abliterated)

| Property | Value |
|----------|-------|
| **Parameters** | 32B dense |
| **Architecture** | Transformer, GQA, 128K context, thinking/non-thinking modes |
| **License** | Apache 2.0 (full commercial, no restrictions) |
| **Tool calling** | Yes (native Hermes-style, BFCL score 68.2) |
| **Censorship** | Moderate refusals in instruct; **abliterated versions available** |
| **Abliterated variant** | [huihui-ai/Qwen3-32B-abliterated](https://huggingface.co/huihui-ai/Qwen3-32B-abliterated), [roslein/Qwen3-32B-abliterated](https://huggingface.co/roslein/Qwen3-32B-abliterated) |
| **GGUF quants** | [mradermacher/Qwen3-32B-abliterated-GGUF](https://huggingface.co/mradermacher/Qwen3-32B-abliterated-GGUF) |

**VRAM by quantization:**

| Quant | Weight Size | + KV (2K ctx) | Fits 64 GB? | Fits 24 GB? |
|-------|-------------|---------------|-------------|-------------|
| FP16 | ~64 GB | ~66 GB | Tight | No |
| Q8_0 | ~32 GB | ~34 GB | **Yes** | Tight |
| Q6_K | ~25 GB | ~27 GB | **Yes** | **Yes** |
| Q5_K_M | ~22 GB | ~24 GB | **Yes** | **Yes (tight)** |
| Q4_K_M | ~18 GB | ~20 GB | **Yes** | **Yes** |

**Benchmarks (base model):**

| Benchmark | Score |
|-----------|-------|
| MMLU | 83.61 |
| MMLU-Pro | 65.54 |
| GPQA | 49.49 |
| EvalPlus | 72.05 |
| MATH | 61.62 |
| ArenaHard | 89.5 |

Source: [Qwen3 Technical Report](https://arxiv.org/html/2505.09388v1), [Qwen Blog](https://qwenlm.github.io/blog/qwen3/)

**Key insight:** Qwen3-32B base performs comparably to Qwen2.5-72B-Base (MMLU 83.61 vs 86.06). This means you get near-72B quality at half the parameters. At Q8 it runs on a single GPU with room to spare. At FP16 on 4x TP it gives you the best possible quality in 64 GB.

**Estimated tok/s:**
- FP16 on 4x RTX 5070 Ti TP=4: ~40-50 tok/s (32B is much faster than 70B)
- Q4_K_M on single RTX 5070 Ti: ~45-60 tok/s
- Q4_K_M on RTX 4090: ~50-70 tok/s

**Verdict:** Outstanding value. Apache 2.0 license is the best in class. Matches 72B quality at 32B size. Abliterated versions work well. Strong tool calling. Consider this over Llama 70B if you want better license terms and faster inference with marginal quality trade-off.

---

### 1.3 Llama 4 Scout 109B (MoE, 17B active)

| Property | Value |
|----------|-------|
| **Parameters** | 109B total, 17B active per token (16 experts) |
| **Architecture** | MoE, GQA, 10M context window, multimodal |
| **License** | Llama 4 Community License (similar to 3.3, <700M MAU) |
| **Tool calling** | Yes |
| **Censorship** | Moderate refusals; [abliterated versions exist](https://huggingface.co/jiangchengchengNLP/Llama-4-Scout-17B-16E-Instruct-abliterated-v2) |

**VRAM by quantization (all experts must be in memory):**

| Quant | Weight Size | Fits 64 GB? |
|-------|-------------|-------------|
| FP16 | ~218 GB | No |
| Q8_0 | ~109 GB | No |
| Q4_K_M | ~62 GB | **Barely** (no room for KV cache) |
| Q3_K_M | ~48 GB | **Yes** |
| 1.78-bit (unsloth) | ~24 GB | Yes (single GPU, ~20 tok/s) |

Source: [Llama 4 System Requirements](https://apxml.com/posts/llama-4-system-requirements), [Unsloth Llama 4 Guide](https://docs.unsloth.ai/models/tutorials-how-to-fine-tune-and-run-llms/llama-4-how-to-run-and-fine-tune)

**Benchmarks:** Scout outperforms Llama 3.3 70B on most benchmarks despite lower active parameter count. However, benchmark reception has been mixed — community reports suggest real-world performance does not always match claimed numbers.

**Verdict:** Interesting MoE architecture, but 109B total parameters make it a tight fit at Q4 on 64 GB. The 10M context window is unique but irrelevant for most Athanor workloads. The mixed reception and the fact that Qwen3-32B matches its quality at a fraction of the size makes Scout a secondary option. Consider if multimodality is needed.

---

### 1.4 Mistral Large 2 (123B)

| Property | Value |
|----------|-------|
| **Parameters** | 123B dense |
| **License** | Mistral Research License (non-commercial by default; commercial requires separate agreement) |
| **Tool calling** | Yes (strong native support) |
| **Censorship** | Light to moderate; Mistral models are historically less restrictive than Llama/Qwen |

**VRAM by quantization:**

| Quant | Weight Size | Fits 64 GB? |
|-------|-------------|-------------|
| FP16 | ~246 GB | No |
| Q4_K_M | ~73 GB | No |
| Q3_K_L | ~65 GB | **Barely** |
| Q3_K_M | ~56 GB | Yes (tight with KV) |

Source: [Mistral Hardware Requirements](https://www.hardware-corner.net/llm-database/Mistral/), [Mistral Large 2](https://mistral.ai/news/mistral-large-2407)

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMLU | 84.0 |
| MATH | 71.5 |
| HumanEval | Competitive with Llama 3.1 405B |

**Verdict:** Too large for comfortable 64 GB operation. The restrictive license makes it a non-starter vs. Apache 2.0 Qwen3. Skip.

---

## Category 2: 14B Class Models (Node 2 — RTX 4090, 24 GB VRAM)

Fast agent backbone: must fit in 24 GB with room for KV cache, achieve 50+ tok/s.

### 2.1 Qwen3-14B (Abliterated) -- RECOMMENDED

| Property | Value |
|----------|-------|
| **Parameters** | 14B dense |
| **Architecture** | Transformer, GQA, 128K context, thinking/non-thinking |
| **License** | Apache 2.0 |
| **Tool calling** | Yes (Hermes-style, Tau2-Bench 65.1) |
| **Censorship** | Abliterated versions fully uncensored |
| **Abliterated variant** | [huihui-ai/Qwen3-14B-abliterated](https://huggingface.co/huihui-ai/Qwen3-14B-abliterated), [mlabonne/Qwen3-14B-abliterated](https://huggingface.co/mlabonne/Qwen3-14B-abliterated) |
| **GGUF quants** | [bartowski/huihui-ai_Qwen3-14B-abliterated-GGUF](https://huggingface.co/bartowski/huihui-ai_Qwen3-14B-abliterated-GGUF) |

**VRAM by quantization:**

| Quant | Weight Size | + KV (2K) | Fits 24 GB? | Fits 12 GB? |
|-------|-------------|-----------|-------------|-------------|
| FP16 | ~28 GB | ~30 GB | No | No |
| Q8_0 | ~14 GB | ~16 GB | **Yes** | Tight |
| Q6_K | ~11 GB | ~13 GB | **Yes** | **Yes** |
| Q5_K_M | ~10 GB | ~12 GB | **Yes** | **Yes (tight)** |
| Q4_K_M | ~8 GB | ~10 GB | **Yes** | **Yes** |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMLU | 81.05 |
| MMLU-Pro | 61.03 |
| GPQA | 39.90 |
| EvalPlus | 72.23 |
| MATH | 62.02 |
| ArenaHard | 85.5 |

Source: [Qwen3 Technical Report](https://arxiv.org/html/2505.09388v1)

**Abliteration quality:**
Refusal rate drops from ~97/100 to ~19/100 while KL divergence remains at ~0.98, confirming fundamental reasoning abilities are preserved.

Source: [huihui-ai Abliteration](https://huggingface.co/huihui-ai/Qwen3-14B-abliterated)

**Estimated tok/s on RTX 4090:**
- FP16: not feasible (28 GB > 24 GB)
- Q8_0: ~50-60 tok/s
- Q4_K_M: ~80-100 tok/s
- vLLM throughput at concurrency: 5,358 tok/s at 4K context (batch inference)

Source: [RTX 4090 vLLM Benchmark](https://www.databasemart.com/blog/vllm-gpu-benchmark-rtx4090), [RTX 4090 LLM Benchmarks](https://www.hardware-corner.net/rtx-4090-llm-benchmarks/)

**Verdict:** The clear winner for fast agent work. Apache 2.0 license, strong tool calling, excellent abliterated variants, fits comfortably in 24 GB at Q8. The thinking/non-thinking mode is perfect for agent workloads — use thinking mode for complex planning, non-thinking for rapid tool calls.

---

### 2.2 Phi-4 14B

| Property | Value |
|----------|-------|
| **Parameters** | 14B dense |
| **Architecture** | Transformer, 16K context |
| **License** | MIT |
| **Tool calling** | Limited |
| **Censorship** | Moderate refusals; no well-known abliterated variant |

**VRAM:** Similar to Qwen3-14B (~28 GB FP16, ~14 GB Q8).

**Benchmarks:** Beats GPT-4o on MATH and GPQA, strong at reasoning. But short context window (16K) and weak tool calling make it inferior to Qwen3-14B for agent use.

Source: [Phi-4 Specs](https://apxml.com/models/phi-4)

**Verdict:** Strong reasoning but short context, limited tool calling, no good uncensored variants. Qwen3-14B is better in every dimension that matters for Athanor.

---

### 2.3 Gemma 3 27B (Abliterated)

| Property | Value |
|----------|-------|
| **Parameters** | 27B dense |
| **Architecture** | Transformer, 128K context, multimodal |
| **License** | Gemma Terms of Use (permissive, commercial OK) |
| **Tool calling** | Limited |
| **Censorship** | **Heavy refusals** in base; abliteration is harder than other models |

**VRAM:**

| Quant | Weight Size | Fits 24 GB? |
|-------|-------------|-------------|
| FP16 | ~54 GB | No |
| Q8_0 | ~27 GB | No |
| Q4_K_M | ~15 GB | **Yes** |
| INT4 QAT | ~14 GB | **Yes** |

Source: [Gemma 3 27B VRAM](https://apxml.com/models/gemma-3-27b)

**Benchmarks:** Elo 1339 on LMSys Chatbot Arena (top 10 overall).

**Key issue:** Gemma 3 is "much more resilient to abliteration than other models like Qwen 2.5" — its safety mechanisms are structurally different and harder to remove.

Source: [mlabonne/gemma-3-27b-it-abliterated](https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated)

**Verdict:** Excellent model quality but the hardest to uncensor of all candidates. At 27B it also needs aggressive quantization to fit in 24 GB. Not recommended over Qwen3-14B for uncensored use.

---

### 2.4 Dolphin 3.0 (Llama 3.1 8B / Mistral 24B)

| Property | Value |
|----------|-------|
| **Parameters** | 8B (Llama 3.1) or 24B (Mistral) |
| **License** | Inherits base model license |
| **Tool calling** | Yes (designed for agentic use) |
| **Censorship** | **Uncensored by design** — no abliteration needed |

Source: [Dolphin 3.0](https://huggingface.co/dphn/Dolphin3.0-Llama3.1-8B)

**Verdict:** Good as a pre-built uncensored option if you don't want to deal with abliteration. But the 8B variant is weaker than Qwen3-14B, and the 24B Mistral variant is not as well-tested. Use as a fallback.

---

## Category 3: 7B and Smaller (DEV — RTX 3060, 12 GB VRAM)

### 3.1 Qwen3-8B (Abliterated)

| Property | Value |
|----------|-------|
| **Parameters** | 8.2B dense |
| **License** | Apache 2.0 |
| **Tool calling** | Yes |
| **Censorship** | [Abliterated variant available](https://huggingface.co/huihui-ai/Qwen3-8B-abliterated) |

**VRAM:** ~16 GB FP16, ~8 GB Q8, ~5 GB Q4. Fits 12 GB at Q8.

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMLU | 76.89 |
| MMLU-Pro | 56.73 |
| EvalPlus | 67.65 |
| MATH | 60.80 |

Source: [Qwen3 Technical Report](https://arxiv.org/html/2505.09388v1)

**Estimated tok/s on RTX 3060 12GB:** ~40-60 tok/s at Q4_K_M (memory-bandwidth limited on GDDR6).

**Verdict:** Best 8B-class model for general utility. Fast, uncensorable, tool-calling capable.

---

### 3.2 Qwen3-4B

| Property | Value |
|----------|-------|
| **Parameters** | 4B dense |
| **License** | Apache 2.0 |
| **VRAM** | ~8 GB FP16, ~4 GB Q8, ~2.5 GB Q4 |

**Benchmarks:** MMLU 72.99, EvalPlus 63.53.

**Verdict:** Good for constrained environments or as a speculative decoding draft model.

---

### 3.3 Embedding Models for RAG

| Model | Parameters | VRAM (FP16) | MTEB Score | Notes |
|-------|------------|-------------|------------|-------|
| **nomic-embed-text-v2** | MoE (~140M active) | <1 GB | Top-tier multilingual | Apache 2.0, first MoE embedding model |
| **gte-Qwen2-1.5B-instruct** | 1.5B | ~3 GB | Very strong | Apache 2.0, bilingual EN/ZH |
| **BGE-M3** | 568M | ~1 GB | Strong multilingual | MIT license |
| **EmbeddingGemma** | 308M | <200 MB (quantized) | Top open multilingual <500M | Based on Gemma 3 |

Source: [BentoML Embedding Guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models), [Nomic Blog](https://www.nomic.ai/blog/posts/nomic-embed-text-v2)

**Verdict:** nomic-embed-text-v2 or gte-Qwen2-1.5B-instruct. Both fit easily in 12 GB alongside Qwen3-8B.

---

## Category 4: Large MoE Models (Beast Mode — 76 GB VRAM + 224 GB RAM)

For occasional use when you need maximum intelligence. These require MoE expert offloading (GPU handles attention/KV cache, CPU handles expert layers via KTransformers or llama.cpp).

### 4.1 Qwen3-235B-A22B

| Property | Value |
|----------|-------|
| **Parameters** | 235B total, 22B active per token (128 experts, 8 active) |
| **Architecture** | MoE, 128K context |
| **License** | Apache 2.0 |
| **Tool calling** | Yes (BFCL v3: 70.8) |
| **Censorship** | Moderate refusals; base model can be used without instruct safety |

**VRAM + RAM requirements:**

| Quant | Total Size | VRAM (attention) | RAM (experts) | Feasible? |
|-------|------------|-------------------|---------------|-----------|
| Q4_K_M | ~110 GB | ~24-32 GB | ~80-90 GB | **Yes** (GPU + RAM hybrid) |
| Q2_K_XL | ~55-60 GB | ~16 GB | ~45 GB | **Yes** (single GPU + RAM) |
| Q8_0 | ~235 GB | ~48 GB | ~190 GB | **Yes** (needs most of 224 GB RAM) |

Source: [ubergarm/Qwen3-235B-A22B-GGUF](https://huggingface.co/ubergarm/Qwen3-235B-A22B-GGUF)

**Benchmarks (flagship):**

| Benchmark | Score |
|-----------|-------|
| MMLU | 87.81 |
| MMLU-Pro | 68.18 |
| GPQA | 47.47 |
| EvalPlus | 77.60 |
| MATH | 71.84 |
| AIME'24 | 85.7 |
| LiveCodeBench | 70.7 |
| BFCL v3 | 70.8 |

Source: [Qwen3 Technical Report](https://arxiv.org/html/2505.09388v1)

**Estimated tok/s (KTransformers hybrid, GPU attention + CPU experts):**
- Q4_K_M with 24 GB GPU + 128 GB RAM: ~8-14 tok/s generation, ~100+ tok/s prefill
- Using all 76 GB VRAM across nodes + 224 GB RAM: potentially faster expert loading

Source: [KTransformers DeepSeek Tutorial](https://kvcache-ai.github.io/ktransformers/en/DeepseekR1_V3_tutorial.html) (similar MoE architecture)

**Verdict:** The best open-weight model you can actually run. Apache 2.0 license, MoE architecture is perfect for CPU offloading, and 22B active parameters means you get near-frontier quality at reasonable inference cost. Primary beast-mode candidate.

---

### 4.2 DeepSeek V3.2 (671B, 37B active)

| Property | Value |
|----------|-------|
| **Parameters** | 671B total, 37B active per token |
| **License** | MIT (DeepSeek License) |
| **Tool calling** | Yes |
| **Censorship** | Chinese safety alignment; bypassed by system prompts or base model |

**VRAM + RAM requirements:**

| Quant | Total Size | Feasible on Athanor? |
|-------|------------|---------------------|
| FP16 | ~1.3 TB | No |
| Q4_K_M | ~382 GB | **Marginal** (76 GB VRAM + 224 GB RAM = 300 GB, short) |
| Q2_K | ~180 GB | **Yes** (significant quality loss) |

**Benchmarks (V3.2):**

| Benchmark | Score |
|-----------|-------|
| MMLU-Pro | 90.2 |
| GPQA Diamond | 84.5 |
| MATH-500 | 91.6 |
| HumanEval | 92.3 |

Source: [DeepSeek V3.2 Specs](https://apxml.com/models/deepseek-v32)

**Performance via KTransformers:**
- Q4_K_M with 14 GB VRAM + 382 GB DRAM: ~14 tok/s generation, ~286 tok/s prefill
- Requires 382 GB total memory — Athanor has ~300 GB total (76 + 224). Tight at Q4, needs Q3 or lower.

Source: [KTransformers DeepSeek Tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepseekR1_V3_tutorial.md)

**Verdict:** The highest benchmark scores of any open model. But 671B total parameters means even Q4 barely fits Athanor's combined memory. Use Q3 or lower if you want to experiment. Qwen3-235B is more practical.

---

### 4.3 GLM-5 (745B, 44B active)

| Property | Value |
|----------|-------|
| **Parameters** | 745B total, 44B active (256 experts, 8 active) |
| **License** | MIT |
| **Tool calling** | Yes |
| **Censorship** | Chinese safety alignment; similar to DeepSeek |

**VRAM + RAM requirements:**

| Quant | Total Size | Feasible on Athanor? |
|-------|------------|---------------------|
| Q4_K_M | ~425 GB | No (exceeds 300 GB total) |
| Q2_K_XL | ~241 GB | **Marginal** (fits but tight) |
| 1-bit | ~180 GB | **Yes** (significant quality loss) |

Source: [GLM-5 Guide](https://unsloth.ai/docs/models/glm-5)

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| SWE-bench Verified | 77.8 (#1 open-source) |
| GPQA Diamond | 86.0 |
| AIME 2026 | 92.7 |

Source: [GLM-5 Analysis](https://www.digitalapplied.com/blog/zhipu-ai-glm-5-release-744b-moe-model-analysis)

**Verdict:** Impressive benchmarks, especially SWE-bench, but too large even for aggressive quantization on Athanor. Skip unless you add more RAM.

---

### 4.4 GPT-OSS 120B (OpenAI, 5.1B active)

| Property | Value |
|----------|-------|
| **Parameters** | 117B total, 5.1B active per token (MoE) |
| **License** | Apache 2.0 |
| **Tool calling** | Yes (native, strong) |
| **Censorship** | OpenAI safety alignment; moderate refusals; no abliterated variants yet |

**VRAM:** 80-96 GB for MXFP4 (native quantization). Fits on Athanor with multi-node VRAM + RAM offloading.

Source: [GPT-OSS Hardware Requirements](https://www.cognativ.com/blogs/post/essential-gpt-oss-120b-hardware-requirements-for-effective-deployment/332)

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMLU-Pro | 90.0 |
| AIME 2024 | 96.6 |
| AIME 2025 | 97.9 |

Source: [OpenAI GPT-OSS](https://openai.com/index/introducing-gpt-oss/)

**Verdict:** Very high quality, Apache 2.0, tiny active parameter count. But native MXFP4 format requires Blackwell-specific support, and no abliterated variants exist. The safety alignment is likely hard-baked. Watch for community abliteration efforts.

---

## Comparison Matrix: Primary Recommendations

### Node 1 (4x RTX 5070 Ti, 64 GB) — Primary Reasoning Engine

| Model | Quant | VRAM | MMLU | License | Uncensored? | Tool Call | Recommendation |
|-------|-------|------|------|---------|-------------|-----------|----------------|
| **Llama 3.3 70B abliterated** | Q4_K_M | ~42 GB | 86.0 | Llama Community | Yes (abliterated) | Yes | **Primary** |
| **Qwen3-32B abliterated** | FP16 | ~66 GB | 83.6 | Apache 2.0 | Yes (abliterated) | Yes (strong) | **Co-primary** |
| **Qwen3-32B abliterated** | Q8_0 | ~34 GB | 83.6 | Apache 2.0 | Yes (abliterated) | Yes (strong) | Best quality/VRAM |
| Llama 4 Scout 109B | Q3_K_M | ~48 GB | ~86+ | Llama Community | Abliterated exists | Yes | Secondary |
| Mistral Large 123B | Q3_K_M | ~56 GB | 84.0 | Research License | Moderate | Yes | Skip (license) |

### Node 2 (RTX 4090, 24 GB) — Fast Agent

| Model | Quant | VRAM | MMLU | License | Uncensored? | Tool Call | Recommendation |
|-------|-------|------|------|---------|-------------|-----------|----------------|
| **Qwen3-14B abliterated** | Q8_0 | ~16 GB | 81.0 | Apache 2.0 | Yes (abliterated) | Yes (strong) | **Primary** |
| Qwen3-32B abliterated | Q4_K_M | ~20 GB | 83.6 | Apache 2.0 | Yes (abliterated) | Yes | Alt (more quality) |
| Phi-4 14B | Q8_0 | ~14 GB | ~80 | MIT | Limited | Limited | Skip |
| Gemma 3 27B abliterated | Q4_K_M | ~15 GB | ~78 | Gemma Terms | Difficult | Limited | Skip |

### Node 2 (RTX 5090, 32 GB) — Creative / Heavy Agent

| Model | Quant | VRAM | Notes |
|-------|-------|------|-------|
| **Qwen3-32B abliterated** | Q8_0 | ~34 GB | Tight fit, best quality at this size |
| **Qwen3-32B abliterated** | Q6_K | ~27 GB | Good quality, comfortable fit |
| Qwen3-14B abliterated | FP16 | ~30 GB | Maximum quality for 14B |

### Beast Mode (76 GB VRAM + 224 GB RAM)

| Model | Quant | Total Size | tok/s (est.) | Quality | Recommendation |
|-------|-------|------------|-------------|---------|----------------|
| **Qwen3-235B-A22B** | Q4_K_M | ~110 GB | ~8-14 | Top-tier | **Primary** |
| DeepSeek V3.2 | Q3_K | ~280 GB | ~8-14 | Highest benchmarks | Experimental |
| GPT-OSS 120B | MXFP4 | ~80 GB | ~10-20 | Very strong | When uncensored variant exists |

---

## Uncensoring Techniques Summary

| Technique | How It Works | Quality Impact | Models |
|-----------|-------------|----------------|--------|
| **Abliteration** | Identifies refusal direction vector in weight space, orthogonalizes it out | KL divergence ~0.98 (minimal) | Llama 3.3 70B, Qwen3 32B/14B/8B, Gemma 3 27B |
| **Dolphin fine-tune** | Retrained on filtered dataset with refusals removed | Varies; generally good | Dolphin 3.0 (Llama 8B, Mistral 24B) |
| **Base model use** | Use non-instruct base model; no safety RLHF applied | No degradation but no instruct following | Any base model |
| **System prompt bypass** | Aggressive system prompts that override safety | Fragile, model-dependent | Qwen (moderate), Mistral (easier) |

Source: [Abliteration Blog](https://huggingface.co/blog/mlabonne/abliteration), [The Sovereign Stack](https://www.watsonout.com/editorials/the-sovereign-stack-best-uncensored-llms-for-local-inference-dec-2025/)

### Abliteration Difficulty by Model Family

| Model Family | Abliteration Difficulty | Quality Preservation |
|-------------|------------------------|---------------------|
| Qwen 2.5/3 | Easy | Excellent |
| Llama 3.x/4 | Easy | Excellent |
| Mistral | Easy-Moderate | Good |
| Gemma 3 | **Hard** (resilient to abliteration) | Acceptable |
| Phi-4 | Moderate | Unknown |
| DeepSeek | Moderate | Good |

Source: [mlabonne/gemma-3-27b-it-abliterated](https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated)

---

## PCIe Tensor Parallelism Performance Note

Node 1 uses 4x RTX 5070 Ti over PCIe 4.0 (no NVLink). Key performance implications:

- PCIe 4.0 x16 provides ~32 GB/s per direction per GPU
- NVLink (not available on consumer Blackwell) provides 600+ GB/s
- **Expected TP overhead on PCIe: 40-60% penalty vs. NVLink**
- At TP=4, expect ~1.4-2.0x speedup over single GPU (not 4x)
- For 70B models, PCIe TP is still worthwhile because a single 16GB GPU can't fit the model at all
- For 32B models, consider running on a single GPU at lower quantization vs. TP=4 at higher quantization — the single-GPU path avoids PCIe overhead entirely

Source: [vLLM Parallelism Docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/), [Blackwell Consumer GPU Paper](https://arxiv.org/html/2601.09527v1)

---

## Recommendation

### Immediate Deploy Stack

1. **Node 1 primary:** Llama 3.3 70B Instruct Abliterated (Q4_K_M via vLLM TP=4) — maximum reasoning quality
2. **Node 1 alternate:** Qwen3-32B Abliterated (Q8_0 or FP16 via vLLM TP=4) — better license, faster, nearly as smart
3. **Node 2 agent:** Qwen3-14B Abliterated (Q8_0 on RTX 4090 via vLLM) — fast tool-calling agent backbone
4. **Node 2 creative:** Qwen3-32B Abliterated (Q6_K on RTX 5090 via vLLM) — creative writing, EoBQ
5. **DEV utility:** Qwen3-8B Abliterated (Q4_K_M) + nomic-embed-text-v2 — embeddings and lightweight tasks
6. **Beast mode:** Qwen3-235B-A22B (Q4_K_M via KTransformers, GPU attention + CPU experts) — when you need frontier quality

### Why Qwen3 Dominates

- **Apache 2.0 license** — no strings attached, full commercial use, no naming requirements
- **Abliteration works cleanly** — easy to uncensor with minimal quality loss
- **Thinking/non-thinking modes** — built-in CoT toggle perfect for agent workloads
- **Strong tool calling** — native Hermes-style function calling
- **Size-efficient** — Qwen3-32B matches Qwen2.5-72B, meaning you get 70B quality at 32B cost
- **Full ecosystem** — GGUF, AWQ, GPTQ, EXL2 quants all available from community

### Models to Watch

- **Qwen3.5 (397B, MoE)** — announced Feb 2026, native multimodal, could be the next beast-mode king
- **GPT-OSS abliterated** — when the community abliterates it, this becomes a strong contender
- **Dolphin 3.0 on Qwen3-32B** — if Eric Hartford releases a Dolphin fine-tune on Qwen3-32B, it would combine Dolphin's uncensored training with Qwen3's quality

---

## Open Questions

1. **vLLM Blackwell support timeline** — Can we run vLLM with sm_120 natively yet, or do we still need source builds?
2. **KTransformers on Athanor** — Need to test multi-node expert offloading for Qwen3-235B
3. **Abliteration quality validation** — Should run evals on abliterated models vs. base to quantify any degradation
4. **NVFP4 on RTX 5070 Ti** — Blackwell-native FP4 should give 1.6x throughput over BF16 but needs vLLM support
5. **Qwen3-32B vs Llama 3.3 70B head-to-head** — Which actually produces better creative writing output? Benchmarks don't capture this well.
