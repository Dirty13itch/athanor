# Exhaustive Uncensored/NSFW-Capable Model Survey (Dec 2025 - Feb 2026)

**Date:** 2026-02-25
**Status:** Complete
**Supersedes:** 2026-02-16-uncensored-llm-models.md (which remains valid but covered fewer models)
**Supports:** ADR-005 (AI Inference Engine), Stash AI (6.6), Empire of Broken Queens

---

## Context

Athanor needs uncensored models for two distinct use cases:

1. **Stash AI Agent** -- Adult content management, tagging, description generation, and image understanding for an adult media library. Requires both text generation and vision models that will not refuse to process adult content.
2. **Empire of Broken Queens** -- AI-driven interactive cinematic adult game. Requires creative writing models capable of generating explicit fiction without refusal.

This survey covers EVERY uncensored, abliterated, unfiltered, or NSFW-capable model released or substantially updated between December 1, 2025 and February 25, 2026. Data was collected directly from the HuggingFace API.

### Hardware Targets (updated)

| Node | GPUs | Total VRAM | Primary Use |
|------|------|------------|-------------|
| Foundry (Node 1) | 4x RTX 5070 Ti + RTX 4090 | 88 GB | Inference TP=4 (GPUs 0-3) + embedding/voice (GPU 4) |
| Workshop (Node 2) | RTX 5090 + RTX 5060 Ti | 48 GB | Creative (GPU 0) + ComfyUI (GPU 1) |
| VAULT | Arc A380 | -- | No ML workloads |
| DEV | RX 5700 XT | -- | No CUDA |

**Currently running:** Qwen3-32B-AWQ via vLLM TP=4 on Node 1 (GPUs 0-3).

---

## Part 1: Abliteration Techniques (State of the Art, Feb 2026)

### 1.1 Standard Abliteration (huihui-ai method)

**Tool:** [Sumandora/remove-refusals-with-transformers](https://github.com/Sumandora/remove-refusals-with-transformers) (1,553 stars)

**Method:** Identifies the "refusal direction" in the model's residual stream by contrasting activations on harmful vs. harmless prompts. Orthogonalizes model weights against this direction, removing the refusal behavior without retraining. Pure HuggingFace Transformers implementation -- no TransformerLens required.

**Quality:** KL divergence typically ~0.98 (minimal degradation). Refusal rate drops from ~97% to ~2-19% depending on model family.

**Creator:** huihui-ai is the most prolific abliterator, having released 50+ abliterated models across every major architecture. Their models are the community standard.

Source: https://huggingface.co/blog/mlabonne/abliteration

### 1.2 Heretic (Automated Abliteration with Optuna Optimization)

**Tool:** [p-e-w/heretic](https://github.com/p-e-w/heretic) (9,638 stars)

**Method:** Fully automatic censorship removal. Uses Optuna multi-objective optimization to find the best abliteration parameters. Evaluates multiple trials (typically 50) to minimize both KL divergence AND refusal rate simultaneously, producing Pareto-optimal abliterations.

**Quality:** Best results seen: KL = 0.0003 with ~2.1% refusals (SA-SWE-32B). This is substantially better than standard single-pass abliteration.

**Example:** nitrox/SA-SWE-32B-abliterated used 50 Optuna trials, best trial #27 achieved KL=0.0003.

Source: https://github.com/p-e-w/heretic

### 1.3 Norm-Preserving Biprojected Abliteration (ArliAI/grimjim method)

**Tool:** Custom implementation by Jim Lai (grimjim), deployed by ArliAI.

**Method:** Three-step refinement over standard abliteration:
1. **Biprojection (Targeting):** Refines the refusal direction to be mathematically orthogonal to "harmless" directions, preventing collateral damage to benign capabilities.
2. **Weight Decomposition:** Decomposes model weights into **magnitude** and **direction** components.
3. **Norm Preservation:** Removes refusal component solely from the *directional* aspect, then recombines with **original magnitudes**.

**Why it matters:** Standard abliteration alters neuron magnitudes ("loudness"), destroying feature norms learned during training. This causes degraded logic and hallucinations. Norm-preserving abliteration avoids this entirely.

**Quality:** ArliAI claims this method avoids the "Safety Tax" and may actually IMPROVE reasoning over the base model, since the model no longer wastes compute on suppressing outputs.

**Models using this method:** ArliAI/GLM-4.6-Derestricted-v3, YanLabs/gemma-3-27b-it-abliterated-normpreserve

Source: https://huggingface.co/blog/grimjim/norm-preserving-biprojected-abliteration

### 1.4 SFT + GRPO (Reinforcement Learning Uncensoring)

**Creator:** puwaer

**Method:** Two-stage training process:
1. **SFT Stage:** 12,000 samples (10k jailbreak + 1.5k general + 0.5k logic). Teaches uncensored behavior format.
2. **GRPO Stage:** 60,000 samples with custom reward model ([puwaer/Unsafe-Reward-Qwen3-1.7B](https://huggingface.co/puwaer/Unsafe-Reward-Qwen3-1.7B)). Optimizes for natural, detailed uncensored responses.

**Quality:** On Sorry Bench, refusal rate drops from 88.86% (base) to 4.09% (GRPO). MT-Bench scores RECOVER from SFT degradation after GRPO stage -- indicating RL can restore intelligence lost during SFT.

**Advantage over abliteration:** Produces more naturally uncensored responses. Abliteration can leave artifacts (stilted phrasing, sudden topic shifts). GRPO-trained models respond fluidly.

**Disadvantage:** Requires actual training (GPU hours), not just weight manipulation. Cannot be applied to arbitrary models without training infrastructure.

Source: https://huggingface.co/puwaer/Qwen3-Next-80B-A3B-Thinking-GRPO-Uncensored

### 1.5 Hermes 4 (NousResearch -- Alignment Without Censorship)

**Creator:** NousResearch

**Method:** Purpose-built uncensored training pipeline:
- ~5M samples / ~60B tokens post-training corpus
- RefusalBench evaluation -- measures helpfulness across commonly-censored scenarios
- "Aligned to you" philosophy -- model follows user values, not hardcoded restrictions

**Quality:** SOTA on RefusalBench across all popular closed AND open models. Maintains full reasoning capability with hybrid thinking mode.

**Key insight:** Hermes 4 is NOT abliterated -- it was TRAINED to be uncensored from the start. This produces fundamentally better results than post-hoc abliteration.

Source: https://huggingface.co/NousResearch/Hermes-4-14B

### 1.6 Can We Abliterate Qwen3-32B-AWQ Ourselves?

**Yes.** The process is straightforward:

1. Install `remove-refusals-with-transformers` or `heretic`
2. Load the BF16 base model (Qwen3-32B-Instruct, not AWQ)
3. Run abliteration
4. Re-quantize to AWQ using AutoAWQ

**Better option:** Use a pre-abliterated model. huihui-ai already provides:
- `huihui-ai/Qwen3-32B-abliterated` (standard abliteration)
- Various GGUF quants from mradermacher and bartowski

For AWQ specifically, you would need to quantize from the abliterated BF16 weights yourself. This is a ~2 hour process on Node 1.

**Recommendation:** Use `heretic` for best quality (Optuna optimization), or simply use huihui-ai's pre-abliterated BF16 and quantize to AWQ.

### Abliteration Difficulty by Model Family (Updated Feb 2026)

| Model Family | Difficulty | Quality Preservation | Notes |
|-------------|------------|---------------------|-------|
| Qwen 3.x | Easy | Excellent | Best abliteration target. Minimal degradation. |
| Qwen 3 Next | Easy | Excellent | Same architecture as Qwen3, abliterates cleanly. |
| GLM 4.x/5 | Easy | Excellent | Chinese models with moderate initial safety. |
| Llama 3.x/4 | Easy | Excellent | Well-studied, many abliterated variants. |
| Mistral/Magistral | Easy-Moderate | Good | Historically less filtered to begin with. |
| GPT-OSS | Easy | Good | OpenAI's open model, abliterates well. |
| Kimi K2.5 | Moderate | Good | Moonshot AI, newer architecture. |
| Gemma 3 | **Hard** | Acceptable | Google's safety is structurally resilient. Requires norm-preserving techniques. |
| DeepSeek | Moderate | Good | Chinese safety alignment, bypassable. |
| Phi-4 | Moderate | Unknown | Few abliterated variants exist. |

---

## Part 2: Text Generation Models (Exhaustive Catalog)

### 2.1 Tier 1: Large Models (60B+ params, Node 1 TP=4 target)

#### Qwen3-Next-80B-A3B (MoE, 3B active) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Qwen3-Next-80B-A3B-Thinking-abliterated |
| **Parameters** | 80B total, 3B active (MoE) |
| **Base model** | Qwen/Qwen3-Next-80B-A3B-Thinking |
| **Release** | 2025-12-10 |
| **Method** | Standard abliteration (remove-refusals-with-transformers) |
| **License** | MIT |
| **Downloads** | 1,219 |
| **VRAM** | ~40 GB FP16 (all experts loaded), ~20 GB Q4 |
| **Capabilities** | Text generation, thinking mode, tool calling |
| **How uncensored** | Fully unrestricted via abliteration |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Qwen3-Next-80B-A3B-Thinking-abliterated |

**Also available as GRPO-uncensored:**
- puwaer/Qwen3-Next-80B-A3B-Thinking-GRPO-Uncensored (dl:1,149, likes:18) -- trained with RL, higher quality uncensoring
- puwaer/Qwen3-Next-80B-A3B-Thinking-SFT-Uncensored (dl:83) -- SFT only stage

**GGUF quants:** mradermacher (8,715 dl), puwaer (2,503 dl)

**Verdict:** Extremely interesting MoE model. Only 3B active parameters means fast inference, but 80B total gives broad knowledge. The GRPO variant from puwaer is the best-quality uncensoring.

---

#### Qwen3-235B-A22B (MoE, 22B active) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Qwen3-235B-A22B-Instruct-2507-abliterated-Q4_K_M-GGUF |
| **Parameters** | 235B total, 22B active (MoE, 128 experts, 8 active) |
| **Base model** | Qwen/Qwen3-235B-A22B-Instruct-2507 |
| **Release** | 2025-12-15 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 429 (GGUF), 33 (safetensors) |
| **VRAM** | ~110 GB Q4_K_M (needs GPU + CPU offload) |
| **Capabilities** | Flagship reasoning, tool calling (BFCL v3: 70.8) |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Qwen3-235B-A22B-Instruct-2507-abliterated-Q4_K_M-GGUF |

**Verdict:** Frontier-class abliterated model. Requires KTransformers or similar for GPU+CPU hybrid inference on Athanor hardware. Beast mode candidate.

---

#### GPT-OSS-120B (MoE, 5.1B active) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-gpt-oss-120b-BF16-abliterated |
| **Parameters** | 117B total, 5.1B active (MoE) |
| **Base model** | OpenAI GPT-OSS-120B |
| **Release** | 2025-08-16 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 4,251 |
| **VRAM** | 80-96 GB MXFP4 |
| **Capabilities** | General reasoning, MMLU-Pro 90.0 |
| **How uncensored** | Fully unrestricted via abliteration |
| **URL** | https://huggingface.co/huihui-ai/Huihui-gpt-oss-120b-BF16-abliterated |

**Community favorite GGUF:** DavidAU/OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf (99,961 downloads, 449 likes)

---

#### GPT-OSS-20B (MoE, active params vary by expert selection) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated |
| **Parameters** | 20B (smaller MoE variant) |
| **Base model** | OpenAI GPT-OSS-20B |
| **Release** | 2025-08-06 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 16,581 (base), 99,961 (DavidAU GGUF) |
| **VRAM** | ~10-12 GB Q4 |
| **Capabilities** | General assistant, reasoning |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-gpt-oss-20b-BF16-abliterated |

**Verdict:** The most downloaded abliterated model on HuggingFace. Small enough to run on a single 16 GB GPU. Quality is good for size but cannot compete with Qwen3-32B.

---

#### GLM-5 (745B, 44B active) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | skyblanket/GLM-5-abliterated |
| **Parameters** | 745B total, 44B active (256 experts, 8 active) |
| **Base model** | zai-org/GLM-5 |
| **Release** | 2026-02-19 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 179 |
| **VRAM** | Too large for Athanor at any quant |
| **Capabilities** | SWE-bench 77.8, GPQA Diamond 86.0 |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/skyblanket/GLM-5-abliterated |

**Also:** legendbl/glm5-abliterated-fp8 (FP8 quantized)

**Verdict:** Impressive but impractical. 745B total params exceeds Athanor's combined memory even at aggressive quantization.

---

#### Devstral-2-123B (Mistral, coding-focused) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Devstral-2-123B-Instruct-2512-abliterated-GGUF |
| **Parameters** | 123B |
| **Base model** | mistralai/Devstral-2-123B-Instruct-2512 |
| **Release** | 2026-01-16 |
| **Method** | Standard abliteration |
| **License** | Other (Mistral license) |
| **Downloads** | 162 |
| **VRAM** | ~62 GB Q4_K_M -- tight fit on Node 1 TP=4 |
| **Capabilities** | Coding, software engineering |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Devstral-2-123B-Instruct-2512-abliterated-GGUF |

---

#### Llama 3.1 70B Uncensored

| Property | Value |
|----------|-------|
| **Full name** | AlSamCur123/Llama3.1-70b-Uncensored |
| **Parameters** | 70B dense |
| **Base model** | Meta Llama 3.1 70B |
| **Release** | 2026-02-19 (re-upload) |
| **Method** | Fine-tuned on uncensored dataset |
| **License** | Llama Community License |
| **Downloads** | 15,046 (mradermacher GGUF) |
| **VRAM** | ~40 GB Q4_K_M |
| **URL** | https://huggingface.co/mradermacher/Llama3.1-70b-Uncensored-i1-GGUF |

---

#### Kimi-K2.5 (MoE, multimodal) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Kimi-K2.5-BF16-abliterated-GGUF |
| **Parameters** | Large MoE (Moonshot AI) |
| **Base model** | moonshotai/Kimi-K2.5 |
| **Release** | 2026-02-22 |
| **Method** | Standard abliteration |
| **License** | Other (Moonshot license) |
| **Downloads** | 734 |
| **Capabilities** | Multimodal (image-text-to-text), reasoning |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Kimi-K2.5-BF16-abliterated-GGUF |

**NOTE:** Very new (Feb 22). First abliterated multimodal Kimi model.

---

#### Kimi-Linear-48B-A3B -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | mradermacher/Huihui-Kimi-Linear-48B-A3B-Instruct-abliterated-GGUF |
| **Parameters** | 48B total, 3B active (MoE) |
| **Release** | 2026-02-19 |
| **Downloads** | 7,705 |
| **License** | Other |
| **URL** | https://huggingface.co/mradermacher/Huihui-Kimi-Linear-48B-A3B-Instruct-abliterated-i1-GGUF |

---

#### Qwen3-Coder-480B-A35B (MoE, coding) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Qwen3-Coder-480B-A35B-Instruct-abliterated-GGUF |
| **Parameters** | 480B total, 35B active (MoE) |
| **Base model** | Qwen/Qwen3-Coder-480B-A35B-Instruct |
| **Release** | 2026-01-12 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 190 |
| **VRAM** | Way too large for Athanor |
| **Capabilities** | Coding specialist |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Qwen3-Coder-480B-A35B-Instruct-abliterated-GGUF |

---

#### MiroThinker-v1.5-235B -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-MiroThinker-v1.5-235B-abliterated-GGUF |
| **Parameters** | 235B (MoE, Qwen3-based) |
| **Base model** | miromind-ai/MiroThinker-v1.5-235B |
| **Release** | 2026-01-16 |
| **License** | MIT |
| **Downloads** | 120 |
| **Capabilities** | Deep research, agentic, thinking |
| **URL** | https://huggingface.co/huihui-ai/Huihui-MiroThinker-v1.5-235B-abliterated-GGUF |

---

### 2.2 Tier 2: Medium Models (24B-36B, single GPU target)

#### GLM-4.7-Flash (MoE) -- ABLITERATED [RECOMMENDED]

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-GLM-4.7-Flash-abliterated |
| **Parameters** | ~4.7B active (MoE, GLM architecture) |
| **Base model** | zai-org/GLM-4.7-Flash |
| **Release** | 2026-01-25 |
| **Method** | Standard abliteration |
| **License** | MIT |
| **Downloads** | 9,353 |
| **Likes** | 74 |
| **VRAM** | ~12-16 GB (MoE, small active params) |
| **Capabilities** | Fast reasoning, chat |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-GLM-4.7-Flash-abliterated |

**GGUF:** huihui-ai/Huihui-GLM-4.7-abliterated-GGUF (1,702 dl)

**Verdict:** High-quality MoE model with MIT license. Small active parameter count makes it fast. Strong community adoption (9,353 downloads).

---

#### GLM-4.6 -- DERESTRICTED (ArliAI, Norm-Preserving) [RECOMMENDED]

| Property | Value |
|----------|-------|
| **Full name** | ArliAI/GLM-4.6-Derestricted-v3 |
| **Parameters** | Dense (GLM-4.6 scale) |
| **Base model** | cerebras/GLM-4.6 |
| **Release** | 2025-12-10 |
| **Method** | Norm-Preserving Biprojected Abliteration |
| **License** | MIT |
| **Downloads** | 66 |
| **Likes** | 25 |
| **Capabilities** | Reasoning, chat, potentially improved over base |
| **How uncensored** | Fully unrestricted, higher quality than standard abliteration |
| **URL** | https://huggingface.co/ArliAI/GLM-4.6-Derestricted-v3 |

**Also:** ArliAI/GLM-4.5-Air-Derestricted (dl:171, likes:92) -- lighter variant

**Verdict:** The gold standard for abliteration quality. Norm-preserving method avoids the "lobotomy" effect. If you care about reasoning quality post-abliteration, this is the technique to follow.

---

#### SA-SWE-32B -- ABLITERATED (Coding specialist)

| Property | Value |
|----------|-------|
| **Full name** | nitrox/SA-SWE-32B-abliterated |
| **Parameters** | 33B dense (Qwen3-based) |
| **Base model** | NovaSky-AI/SA-SWE-32B |
| **Release** | 2026-02-23 |
| **Method** | Heretic (Optuna 50 trials, best: KL=0.0003, 2.1% refusals) |
| **License** | Apache 2.0 |
| **Downloads** | 2,494 (combined GGUF variants) |
| **VRAM** | ~18 GB Q4, ~34 GB Q8 |
| **Capabilities** | Software engineering, SWE-bench optimized, thinking mode |
| **How uncensored** | Fully unrestricted (2.1% residual refusals) |
| **URL** | https://huggingface.co/nitrox/SA-SWE-32B-abliterated |

**Verdict:** Best abliteration quality metric we have seen (KL=0.0003). Uses heretic tool. Coding specialist though -- not ideal for creative writing.

---

#### Devstral-Small-2-24B -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Devstral-Small-2-24B-Instruct-2512-abliterated |
| **Parameters** | 24B (Mistral architecture, multimodal) |
| **Base model** | mistralai/Devstral-Small-2-24B-Instruct-2512 |
| **Release** | 2025-12-12 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 299 |
| **VRAM** | ~14 GB Q4, ~24 GB Q8 |
| **Capabilities** | Coding, multimodal (image-text-to-text) |
| **How uncensored** | Fully unrestricted |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Devstral-Small-2-24B-Instruct-2512-abliterated |

---

#### MiroThinker-v1.5-30B -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-MiroThinker-v1.5-30B-abliterated |
| **Parameters** | 30B (Qwen3-MoE based) |
| **Base model** | miromind-ai/MiroThinker-v1.5-30B |
| **Release** | 2026-01-10 |
| **Method** | Standard abliteration |
| **License** | MIT |
| **Downloads** | 222 |
| **Capabilities** | Deep research, agentic thinking |
| **URL** | https://huggingface.co/huihui-ai/Huihui-MiroThinker-v1.5-30B-abliterated |

---

#### Gemma-3-27b-it -- ABLITERATED (Multiple variants)

| Variant | Creator | Method | Downloads | Likes | URL |
|---------|---------|--------|-----------|-------|-----|
| gemma-3-27b-it-abliterated | mlabonne | Standard | 13,018 | 292 | https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated |
| gemma-3-27b-it-abliterated-GGUF | mlabonne | Standard | 27,756 | 230 | https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated-GGUF |
| gemma-3-27b-it-abliterated-normpreserve | YanLabs | Norm-preserving | 10,823 | 13 | https://huggingface.co/YanLabs/gemma-3-27b-it-abliterated-normpreserve-GGUF |
| Gemma3-27B-it-vl-GLM-4.7-Uncensored-Heretic-Deep-Reasoning | DavidAU | Merge + Heretic | 1,879 | 18 | https://huggingface.co/DavidAU/Gemma3-27B-it-vl-GLM-4.7-Uncensored-Heretic-Deep-Reasoning |
| Gemma-3-27b-it-Uncensored-HERETIC-Gemini-Deep-Reasoning | DavidAU | Merge | 435 | 8 | https://huggingface.co/DavidAU/Gemma-3-27b-it-Uncensored-HERETIC-Gemini-Deep-Reasoning |
| Gemma-3-27b-it-vl-SuperBrain7x-High-Reasoning-ULTRAMIND-Heretic-Uncensored | DavidAU | Merge | 154 | 7 | https://huggingface.co/DavidAU/Gemma-3-27b-it-vl-SuperBrain7x-High-Reasoning-ULTRAMIND-Heretic-Uncensored |

**Key note:** Gemma 3 is hard to abliterate. mlabonne's variant is the most popular but has known quality issues. The YanLabs norm-preserving variant is likely better quality. DavidAU's "Heretic" merges combine Gemma with other model weights to overcome abliteration resistance.

---

#### Magistral-Small-2506 (Mistral) -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Magistral-Small-2506-abliterated |
| **Parameters** | ~24B (Mistral Small) |
| **Base model** | mistralai/Magistral-Small-2506 |
| **Method** | Standard abliteration |
| **License** | Other (Mistral) |
| **Downloads** | 392 (mradermacher GGUF) |
| **URL** | https://huggingface.co/mradermacher/Magistral-Small-2506-abliterated-i1-GGUF |

**Also:** DavidAU/MistralAI-Magistral-Small-2507-Heretic-Uncensored (mradermacher GGUF: 6,851 dl)

---

#### Ministral-3-14B-Reasoning -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Ministral-3-14B-Reasoning-2512-abliterated |
| **Parameters** | 14B (Mistral 3 architecture) |
| **Base model** | mistralai/Ministral-3-14B-Reasoning-2512 |
| **Release** | 2025-12-06 |
| **License** | Apache 2.0 |
| **Downloads** | 566 |
| **Capabilities** | Reasoning, multilingual (12 languages) |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Ministral-3-14B-Reasoning-2512-abliterated |

**Also:** 8B and 3B variants available from huihui-ai.

---

#### Hermes 4 14B (NousResearch) [RECOMMENDED -- Natively Uncensored]

| Property | Value |
|----------|-------|
| **Full name** | NousResearch/Hermes-4-14B |
| **Parameters** | 14B (Qwen3-14B base) |
| **Release** | 2026-01-09 |
| **Method** | Trained uncensored (not abliterated) |
| **License** | Apache 2.0 |
| **Downloads** | 4,530 |
| **Likes** | 119 |
| **VRAM** | ~14 GB Q8, ~8 GB Q4 |
| **Capabilities** | Hybrid reasoning (thinking mode), tool calling, structured outputs, SOTA RefusalBench |
| **How uncensored** | Natively -- trained to follow user values without censorship |
| **URL** | https://huggingface.co/NousResearch/Hermes-4-14B |

**Verdict:** The single best "uncensored by design" model in the 14B class. No abliteration artifacts. SOTA on RefusalBench. Thinking mode. Apache 2.0. Drop-in replacement for Qwen3-14B with better uncensored behavior.

---

#### Hermes 4.3 36B (NousResearch) [RECOMMENDED -- Natively Uncensored]

| Property | Value |
|----------|-------|
| **Full name** | NousResearch/Hermes-4.3-36B |
| **Parameters** | 36B |
| **Release** | 2025-12-06 |
| **Method** | Trained uncensored |
| **License** | Apache 2.0 |
| **Downloads** | 5,144 |
| **Likes** | 130 |
| **VRAM** | ~18 GB Q4, ~36 GB Q8 |
| **URL** | https://huggingface.co/NousResearch/Hermes-4.3-36B |

**Verdict:** Larger variant of Hermes 4. Could run on Node 2 5090 (32 GB) at Q6_K or on Node 1 TP=4 at Q8/FP16 for maximum quality.

---

#### Qwen3-Coder-Next -- ABLITERATED (Coding)

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Qwen3-Coder-Next-abliterated |
| **Parameters** | Qwen3-Next architecture (likely 30-32B range) |
| **Base model** | Qwen/Qwen3-Coder-Next |
| **Release** | 2026-02-07 |
| **Method** | Standard abliteration |
| **License** | Apache 2.0 |
| **Downloads** | 1,675 |
| **Likes** | 37 |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Qwen3-Coder-Next-abliterated |

**GGUF:** bartowski (11,038 dl), mradermacher (25,153 dl)

**Verdict:** Very popular abliterated coding model. Qwen3-Next architecture.

---

### 2.3 Tier 3: Small Models (7B-14B, fast inference)

#### Qwen3-8B -- ABLITERATED

Already covered in previous research. huihui-ai/Qwen3-8B-abliterated remains the primary source.

---

#### Lumimaid-v0.2-8B-Heretic (NSFW RP specialist)

| Property | Value |
|----------|-------|
| **Full name** | 0xA50C1A1/Lumimaid-v0.2-8B-Heretic |
| **Parameters** | 8B |
| **Base model** | NeverSleep/Lumimaid-v0.2-8B (fine-tuned from Llama 3.1 on NSFW RP data) |
| **Release** | 2026-02-14 |
| **Method** | Merge with Heretic abliteration |
| **Downloads** | 5,406 (mradermacher GGUF) |
| **Capabilities** | Roleplay, NSFW creative writing |
| **URL** | https://huggingface.co/0xA50C1A1/Lumimaid-v0.2-8B-Heretic |

**Verdict:** The Lumimaid line is specifically trained for NSFW roleplay. The Heretic variant adds stronger uncensoring. Relevant for EoBQ character interactions.

---

#### DarkIdol-Llama-3.1-8B-Instruct-1.3-Uncensored

| Property | Value |
|----------|-------|
| **Full name** | aifeifei798/DarkIdol-Llama-3.1-8B-Instruct-1.3-Uncensored |
| **Parameters** | 8B |
| **Base model** | Llama 3.1 8B |
| **Method** | Fine-tuned uncensored |
| **License** | Llama Community |
| **Downloads** | 2,545 |
| **Capabilities** | General chat, uncensored assistance |
| **URL** | https://huggingface.co/aifeifei798/DarkIdol-Llama-3.1-8B-Instruct-1.3-Uncensored |

---

#### NVIDIA Nemotron-Nano-9B-v2 -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-NVIDIA-Nemotron-Nano-9B-v2-abliterated |
| **Parameters** | 9B |
| **Base model** | NVIDIA/Nemotron-Nano-9B-v2 |
| **Release** | 2025-12-29 |
| **License** | NVIDIA Open |
| **Downloads** | 173 |
| **URL** | https://huggingface.co/huihui-ai/Huihui-NVIDIA-Nemotron-Nano-9B-v2-abliterated |

---

#### Dolphin-Mistral-GLM-4.7-Flash-24B-Venice-Uncensored (Merge)

| Property | Value |
|----------|-------|
| **Full name** | DavidAU/Dolphin-Mistral-GLM-4.7-Flash-24B-Venice-Edition-Thinking-Uncensored |
| **Parameters** | 24B (merge) |
| **Release** | 2026-01-30 |
| **Method** | Model merge (Dolphin + Mistral + GLM-4.7-Flash + Venice uncensored) |
| **Downloads** | 856 (base), 13,816 (mradermacher GGUF) |
| **Capabilities** | Thinking mode, uncensored chat |
| **URL** | https://huggingface.co/DavidAU/Dolphin-Mistral-GLM-4.7-Flash-24B-Venice-Edition-Thinking-Uncensored |

---

### 2.4 Tier 4: Tiny Models (1B-4B)

#### Qwen3-4B-Thinking -- Various Uncensored Variants

| Variant | Method | Downloads | URL |
|---------|--------|-----------|-----|
| puwaer/Qwen3-4B-Thinking-2507-SFT-Uncensored | SFT | 62 | https://huggingface.co/puwaer/Qwen3-4B-Thinking-2507-SFT-Uncensored |
| Maronik/Qwen3-4B-Thinking-2507-SFT-Uncensored | SFT | 5 | https://huggingface.co/Maronik/Qwen3-4B-Thinking-2507-SFT-Uncensored |
| nitrox/Qwen3-4B-abliterated-v2 | Abliteration | 12 | https://huggingface.co/nitrox/Qwen3-4B-abliterated-v2 |
| Aimin12/Qwen3-4B-Thinking-2507-Distill-Claude-Opus-4.6-Reasoning-Abliterated | Distill + Abliterate | 68 | https://huggingface.co/Aimin12/Qwen3-4B-Thinking-2507-Distill-Claude-Opus-4.6-Reasoning-Abliterated |

---

#### Uncensored Nanbeige-4.1-3B

| Property | Value |
|----------|-------|
| **Full name** | NeshVerse/Uncensored_Nanbeige-4.1-3B |
| **Parameters** | 3B |
| **Release** | 2026-02-20 |
| **Downloads** | 58 |
| **URL** | https://huggingface.co/NeshVerse/Uncensored_Nanbeige-4.1-3B |

---

### 2.5 DavidAU's "Heretic" Uncensored Series (Gemma 3 merges)

DavidAU is prolific, producing dozens of uncensored Gemma 3 merges per week. These combine Gemma 3 with weights from other models (GLM, GPT, DeepSeek, etc.) to overcome Gemma's abliteration resistance. Key recent models:

| Model | Params | Modality | Downloads | URL |
|-------|--------|----------|-----------|-----|
| gemma-3-12b-it-vl-GLM-4.7-Flash-Heretic-Uncensored-Thinking | 12B | Vision+Text | 491 | https://huggingface.co/DavidAU/gemma-3-12b-it-vl-GLM-4.7-Flash-Heretic-Uncensored-Thinking |
| gemma-3-12b-it-vl-Deepseek-v3.1-Heretic-Uncensored-Thinking | 12B | Vision+Text | 184 | https://huggingface.co/DavidAU/gemma-3-12b-it-vl-Deepseek-v3.1-Heretic-Uncensored-Thinking |
| Gemma3-27B-it-vl-GLM-4.7-Uncensored-Heretic-Deep-Reasoning | 27B | Vision+Text | 1,879 | https://huggingface.co/DavidAU/Gemma3-27B-it-vl-GLM-4.7-Uncensored-Heretic-Deep-Reasoning |
| Gemma-3-4B-VL-it-Gemini-Pro-Heretic-Uncensored-Thinking | 4B | Vision+Text | 267 | https://huggingface.co/DavidAU/Gemma-3-4B-VL-it-Gemini-Pro-Heretic-Uncensored-Thinking |
| gemma-3-12b-it-vl-Polaris-Heretic-Uncensored-Thinking | 12B | Vision+Text | 59 | https://huggingface.co/DavidAU/gemma-3-12b-it-vl-Polaris-Heretic-Uncensored-Thinking |

**Andycurrent GGUF of Gemma-3-4B-VL-it-Gemini-Pro-Heretic-Uncensored-Thinking:** 18,256 downloads, 19 likes -- one of the most popular small uncensored VLMs.

**Verdict:** DavidAU's merges are experimental but popular. Quality varies significantly between variants. The GLM-4.7+Gemma merges tend to be the best.

---

### 2.6 Specialized: Erotic/NSFW-Focused Models

#### NSFW RP Models (Recent)

| Model | Params | Date | Downloads | URL |
|-------|--------|------|-----------|-----|
| Leviathan_NSFW_Roleplay-3.2-1B | 1B | 2025-12-22 | 1,410 (GGUF) | https://huggingface.co/Novaciano/Leviathan_NSFW_Roleplay-3.2-1B |
| NSFW-RP-RolePlay-LoRA-ArliAI-Llama-3.1-8B | 8B (LoRA) | 2025-12-26 | 57 | https://huggingface.co/mirazrafi/NSFW-RP-RolePlay-LoRA-ArliAI-Llama-3.1-8B |
| Uncensored-1b-Creative_Writing_RP-GGUF | 1B | 2026-02-17 | 1,035 | https://huggingface.co/pancho101/Uncensored-1b-Creative_Writing_RP-GGUF |
| Qwen3-30B-A3B-abliterated-erotic | 30B MoE | 2026-02-22 | 8 | https://huggingface.co/TheHighKage/Qwen3-30B-A3B-abliterated-erotic |

#### Lumimaid / NeverSleep Line (NSFW RP heritage)

The NeverSleep/Lumimaid models were the gold standard for NSFW roleplay but haven't received new BASE releases since July 2024. However, community variants continue:

| Model | Params | Date | Downloads | URL |
|-------|--------|------|-----------|-----|
| Lumimaid-v0.2-8B-Heretic | 8B | 2026-02-14 | 5,406 (GGUF) | https://huggingface.co/0xA50C1A1/Lumimaid-v0.2-8B-Heretic |
| Lumimaid-v0.2-123B-NVFP4 | 123B | 2026-02-14 | 44 | https://huggingface.co/Shifusen/Lumimaid-v0.2-123B-NVFP4 |
| Lumimaid-Magnum-v4-12B | 12B | 2025-07-31 | 99 | https://huggingface.co/mradermacher/Lumimaid-Magnum-v4-12B-GGUF |

#### Noromaid / Kunoichi (Legacy NSFW RP lines)

No new releases in the Dec 2025 - Feb 2026 window. These are Mistral-7B-era models (13B max) that are outdated by current standards. The community has moved to abliterated Qwen3/Llama 3 models.

#### Midnight Miqu 70B (Creative writing benchmark)

| Property | Value |
|----------|-------|
| **Full name** | sophosympatheia/Midnight-Miqu-70B-v1.5 |
| **Parameters** | 70B |
| **Downloads** | 9,212 |
| **Likes** | 245 |
| **Capabilities** | Creative writing, long-form fiction |
| **URL** | https://huggingface.co/sophosympatheia/Midnight-Miqu-70B-v1.5 |

No new versions, but remains the community gold standard for creative writing.

---

## Part 3: Vision/Multimodal Models (VLMs) -- UNCENSORED

Critical for Stash AI -- needs to understand and describe adult images without refusing.

### 3.1 Qwen3-VL Series -- ABLITERATED [TOP RECOMMENDATION]

| Model | Params | Downloads | Likes | URL |
|-------|--------|-----------|-------|-----|
| **Huihui-Qwen3-VL-8B-Instruct-abliterated** | 8B | 7,420 | 155 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated |
| Huihui-Qwen3-VL-8B-Thinking-abliterated | 8B | 508 | 28 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Thinking-abliterated |
| Huihui-Qwen3-VL-4B-Instruct-abliterated | 4B | 5,611 | 55 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated |
| Huihui-Qwen3-VL-4B-Thinking-abliterated | 4B | 488 | 27 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-4B-Thinking-abliterated |
| Huihui-Qwen3-VL-2B-Instruct-abliterated | 2B | 1,005 | 15 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-2B-Instruct-abliterated |
| **Huihui-Qwen3-VL-32B-Instruct-abliterated** | 32B | 836 | 25 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-32B-Instruct-abliterated |
| Huihui-Qwen3-VL-32B-Thinking-abliterated | 32B | 1,548 | 25 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-32B-Thinking-abliterated |
| **Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated** | 30B MoE | 1,273 | 84 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated |
| Huihui-Qwen3-VL-30B-A3B-Thinking-abliterated | 30B MoE | 716 | 14 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-30B-A3B-Thinking-abliterated |
| Huihui-Qwen3-VL-235B-A22B-Instruct-abliterated-GGUF | 235B MoE | 931 | 21 | https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-235B-A22B-Instruct-abliterated-GGUF |

**All Apache 2.0 licensed.**

**Top pick for Stash:** Qwen3-VL-8B-Instruct-abliterated. 7,420 downloads, 155 likes. Fits on a single 16 GB GPU. Can describe images including adult content without refusal.

**Premium pick:** Qwen3-VL-32B for higher quality descriptions (runs on 5090 at Q4).

---

### 3.2 Qwen2.5-VL Series -- ABLITERATED

| Model | Params | Downloads | URL |
|-------|--------|-----------|-----|
| Qwen2.5-VL-3B-Instruct-abliterated | 3B | 29,574 | https://huggingface.co/huihui-ai/Qwen2.5-VL-3B-Instruct-abliterated |
| Qwen2.5-VL-7B-Instruct-abliterated | 7B | 2,637 | https://huggingface.co/huihui-ai/Qwen2.5-VL-7B-Instruct-abliterated |
| Qwen2.5-VL-7B-Abliterated-Caption-it | 7B | 4,332 | https://huggingface.co/prithivMLmods/Qwen2.5-VL-7B-Abliterated-Caption-it |
| Qwen2.5-VL-32B-Instruct-abliterated | 32B | 1,132 | https://huggingface.co/huihui-ai/Qwen2.5-VL-32B-Instruct-abliterated |
| Qwen2.5-VL-72B-Instruct-abliterated-deep | 72B | 76 | https://huggingface.co/rvncto/Qwen2.5-VL-72B-Instruct-abliterated-deep |

**Note:** "Caption-it" models from prithivMLmods are specifically fine-tuned for image captioning -- potentially useful for Stash auto-tagging.

---

### 3.3 Step3-VL-10B -- ABLITERATED

| Property | Value |
|----------|-------|
| **Full name** | huihui-ai/Huihui-Step3-VL-10B-abliterated |
| **Parameters** | 10B |
| **Base model** | stepfun-ai/Step3-VL-10B |
| **Release** | 2026-01-17 |
| **License** | Apache 2.0 |
| **Downloads** | 963 |
| **Likes** | 20 |
| **URL** | https://huggingface.co/huihui-ai/Huihui-Step3-VL-10B-abliterated |

**Verdict:** Alternative to Qwen3-VL. Step3 is a strong vision model, abliterated variant could be useful for Stash.

---

### 3.4 Kimi K2.5 -- ABLITERATED (Multimodal)

Already listed above in text models. The GGUF version supports image-text-to-text tasks.

---

### 3.5 Gemma 3 Multimodal Merges (DavidAU Heretic series)

Already listed above. The gemma-3-12b-it-vl variants include vision capability.

---

## Part 4: Embedding Models

### Uncensored Embeddings

There are **no dedicated uncensored embedding models** on HuggingFace. This is because embedding models do not "refuse" -- they simply encode text into vectors. Standard embedding models will encode adult content text the same as any other text.

**Current Athanor setup (nomic-embed-text via vLLM-embedding) works fine for adult content.** No change needed.

If you encounter embedding models that produce degraded vectors for adult content terms, the issue is typically in the training data distribution (underrepresented NSFW vocabulary), not in safety filtering.

---

## Part 5: Model Family Natural Filtering Levels

Some model families are inherently less filtered, reducing or eliminating the need for abliteration:

| Model Family | Natural Filtering Level | Notes |
|-------------|------------------------|-------|
| **Mistral/Mistral-based** | Low | Historically the least filtered major model family. Easy to bypass with system prompts alone. |
| **GLM (Zhipu)** | Low-Medium | Chinese safety focus (politics, not sex). Adult content often passes without modification. |
| **Qwen 3** | Medium | Moderate refusals. Abliterates cleanly. Base (non-instruct) models are essentially unfiltered. |
| **DeepSeek** | Medium | Chinese safety alignment. Easily bypassed or abliterated. |
| **Llama 3/4** | Medium-High | Meta's safety training is meaningful but abliterates cleanly. |
| **GPT-OSS** | Medium | OpenAI safety, but abliterates well given open weights. |
| **Gemma 3** | **High** | Google's safety is structurally resilient. Requires norm-preserving techniques or model merging. |
| **Phi-4** | High | Microsoft's safety. Few abliterated variants exist. |

---

## Part 6: Recommendations for Athanor

### For Stash AI Agent (Adult Content Management)

**Primary: Qwen3-VL-8B-Instruct-abliterated** (huihui-ai)
- Fits on a single 16 GB GPU (Node 1 GPU 4 or Node 2 GPU 1)
- 7,420 downloads, community-proven
- Can describe, tag, and categorize adult images without refusal
- Apache 2.0 license

**Premium: Qwen3-VL-32B-Instruct-abliterated** (huihui-ai)
- Higher quality descriptions
- Runs on Node 2 5090 (32 GB) at Q4_K_M
- Or on Node 1 TP=4 for maximum quality

### For Empire of Broken Queens (Adult Interactive Fiction)

**Primary: NousResearch/Hermes-4-14B**
- Natively uncensored (no abliteration artifacts)
- SOTA RefusalBench
- Hybrid thinking mode for complex narrative branching
- Apache 2.0, 14B fits on single 24 GB GPU
- Strong tool calling for game mechanics

**Premium: NousResearch/Hermes-4.3-36B**
- Same philosophy as Hermes 4, larger
- Richer creative writing
- Fits on Node 2 5090 (32 GB) at Q6_K

**Alternative: Qwen3-32B-abliterated (current model, just abliterate it)**
- Already deployed on Node 1
- AWQ quantization would need to be re-done from abliterated BF16 weights
- Or swap to huihui-ai's BF16 abliterated and re-quantize

**NSFW specialist: Lumimaid-v0.2-8B-Heretic**
- Purpose-built for NSFW roleplay
- Very good at character voice and explicit content
- Only 8B, so weaker at complex reasoning/plotting

### For General Uncensored Use

**Primary (no change): Qwen3-32B-AWQ** -- abliterate it with heretic
**Alternative: puwaer/Qwen3-Next-80B-A3B-Thinking-GRPO-Uncensored** -- best RL-uncensored model

### Model Swap Strategy

Run two models in rotation on Node 1:
1. **Default:** Qwen3-32B-AWQ (abliterated) for general use + EoBQ
2. **When needed:** Swap to Qwen3-VL-32B-Instruct-abliterated for Stash image processing

GPU orchestrator can manage this swap via vLLM sleep/wake (when NGC image is upgraded).

---

## Part 7: New Developments Since Feb 16 Research

| What | When | Impact |
|------|------|--------|
| **GLM-4.7-Flash abliterated** | Jan 25 | New MoE model with MIT license, fast inference, 9K+ downloads |
| **Hermes 4 14B** | Jan 9 | Purpose-built uncensored model, SOTA RefusalBench |
| **Hermes 4.3 36B** | Dec 6 | Larger variant with enhanced reasoning |
| **Qwen3-Next-80B-A3B GRPO Uncensored** | Feb 17 | RL-based uncensoring, best quality method |
| **GLM-5 abliterated** | Feb 19 | 745B model, too large but shows technique works at scale |
| **Kimi K2.5 abliterated** | Feb 22 | First abliterated Kimi multimodal model |
| **SA-SWE-32B abliterated (heretic)** | Feb 23 | Best KL divergence ever: 0.0003 |
| **Heretic tool reaches 9.6K stars** | Feb 25 | Automated abliteration becoming mainstream |
| **Norm-preserving abliteration matures** | Dec-Feb | ArliAI and YanLabs demonstrating quality improvements |
| **Qwen3-VL full abliterated family** | Dec 15 | 2B through 235B, all abliterated, all VLM-capable |
| **DavidAU Heretic Gemma merges explode** | Feb | Dozens of variants overcoming Gemma's abliteration resistance |
| **GPT-OSS abliterated** | Ongoing | 99K+ downloads on DavidAU's GGUF, community favorite |
| **Qwen3-Coder-Next abliterated** | Feb 7 | Latest Qwen coding model, abliterated |

---

## Open Questions

1. **Qwen3.5 (397B MoE):** Announced but no HuggingFace release yet. When it drops, huihui-ai will abliterate it within days. Watch for it.
2. **vLLM VLM support:** Can vLLM serve abliterated VLMs (Qwen3-VL) for Stash agent? Need to test.
3. **Multi-model serving:** Can we run a text model AND a VLM simultaneously on Node 1's 88 GB VRAM? Potentially: Qwen3-32B-AWQ on GPUs 0-3 (TP=4, ~35 GB) + Qwen3-VL-8B on GPU 4 (~8 GB Q4).
4. **Hermes 4 on vLLM:** NousResearch models use Qwen3 base -- should work with existing vLLM setup. Need to verify tool calling compatibility.
5. **GRPO vs abliteration quality for creative writing:** No head-to-head benchmarks exist. Would need manual evaluation.
6. **AWQ quant of abliterated models:** Need to verify that AutoAWQ can quantize huihui-ai's abliterated BF16 weights without issues on Blackwell.

---

## Sources

### Models (HuggingFace)
- huihui-ai collection: https://huggingface.co/huihui-ai (50+ abliterated models)
- NousResearch Hermes 4: https://huggingface.co/NousResearch/Hermes-4-14B
- NousResearch Hermes 4.3: https://huggingface.co/NousResearch/Hermes-4.3-36B
- puwaer GRPO uncensored: https://huggingface.co/puwaer/Qwen3-Next-80B-A3B-Thinking-GRPO-Uncensored
- ArliAI GLM-4.6 Derestricted: https://huggingface.co/ArliAI/GLM-4.6-Derestricted-v3
- DavidAU Heretic series: https://huggingface.co/DavidAU
- mlabonne Gemma abliterated: https://huggingface.co/mlabonne/gemma-3-27b-it-abliterated
- NeverSleep Lumimaid: https://huggingface.co/NeverSleep/Lumimaid-v0.2-8B
- nitrox SA-SWE-32B abliterated: https://huggingface.co/nitrox/SA-SWE-32B-abliterated

### Tools
- Heretic (automated abliteration): https://github.com/p-e-w/heretic
- remove-refusals-with-transformers: https://github.com/Sumandora/remove-refusals-with-transformers
- Abliteration blog: https://huggingface.co/blog/mlabonne/abliteration
- Norm-preserving abliteration: https://huggingface.co/blog/grimjim/norm-preserving-biprojected-abliteration

### Data Source
- All model data retrieved from HuggingFace API (https://huggingface.co/api/models) on 2026-02-25
- Download counts and likes are point-in-time snapshots
