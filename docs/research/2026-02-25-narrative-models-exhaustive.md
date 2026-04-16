# Exhaustive Survey: Creative Writing, Narrative, and Roleplay Models

**Date:** 2026-02-25
**Status:** Complete
**Supports:** EoBQ (Empire of Broken Queens) model selection, ADR-005 (AI Inference Engine)
**Depends on:** `docs/research/2026-02-16-uncensored-llm-models.md`, `docs/projects/eoq/ARCHITECTURE.md`

---

## Context

Empire of Broken Queens requires models that excel at: character dialogue with distinct personalities, cinematic narrative prose, sensory-rich scene description, plot branching with consequence tracking, world-building consistency, and explicit adult content generation. This survey covers every creative writing model family discovered through systematic search of HuggingFace, community resources, and model maker profiles.

**Scope:** Models released or actively maintained December 2025 through February 2026, plus foundational models still considered state-of-the-art for creative writing.

**Key finding:** The creative writing model ecosystem is dominated by a small number of prolific fine-tuners (TheDrummer, Sao10K, Doctor-Shotgun, anthracite-org, DavidAU, Undi95/NeverSleep, Epiculous, PygmalionAI) who produce specialized variants of Llama 3.3 70B, Mistral Nemo 12B, Mistral Small 24B, and Qwen2.5-72B. No Qwen3-based creative writing fine-tunes exist yet as of this writing -- the community has not caught up to the Qwen3 architecture for creative writing.

---

## Hardware Context (Athanor)

| Slot | GPU | VRAM | Best Fit |
|------|-----|------|----------|
| Node 1 TP=4 | 4x RTX 5070 Ti | 64 GB | 70B models at Q4_K_M (~42 GB) |
| Node 1 standalone | RTX 4090 | 24 GB | 24B-36B models at Q4-Q6 |
| Node 2 primary | RTX 5090 | 32 GB | 32B-49B models at Q4-Q6 |
| Node 2 secondary | RTX 5060 Ti | 16 GB | 12B models at Q6-Q8 |

---

## Part 1: Specialized Creative Writing Models

### 1.1 The 70B Tier (Node 1 TP=4)

#### Midnight Miqu 70B v1.5 (sophosympatheia)

| Property | Value |
|----------|-------|
| **Parameters** | 70B |
| **Base** | 152334H/miqu-1-70b-sf (leaked Mistral weights) |
| **Method** | DARE Linear merge of Midnight-Miqu-70B-v1.0 + Tess-70B-v1.6 |
| **Context** | 32K |
| **License** | Personal use only (based on leaked Mistral weights) |
| **NSFW** | Yes -- explicitly designed for roleplay/ERP |
| **Prompt format** | Vicuna or Mistral v3 |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Downloads** | 9,212/month (base); new quants still appearing Feb 2026 |
| **HuggingFace** | [sophosympatheia/Midnight-Miqu-70B-v1.5](https://huggingface.co/sophosympatheia/Midnight-Miqu-70B-v1.5) |

**Strengths:** Widely considered the single best model for creative prose quality and roleplay. The Watson Out Sovereign Stack article (Dec 2025) calls it "the benchmark" that newer models still fail to surpass. Excellent at character voice, atmospheric description, and emotional nuance.

**Weaknesses:** Based on leaked Mistral weights -- license is legally ambiguous. Cannot be used commercially. The model sometimes requires "warming up" with few-shot examples. Traditional benchmarks are poor (avg 25.22 on Open LLM Leaderboard) because it was not optimized for those tasks.

**Recommended settings:** temp 1.0, min_p 0.12, rep_pen 1.05, smoothing_factor 0.23.

**Recent activity (Dec 2025 - Feb 2026):** ChatML format variant by Sicarius-Prototyping (Feb 2026), new GGUF quants by mradermacher (Feb 2026), MLX quants by AiAF (Feb 2026), FP8 by sh0ck0r (Dec 2025). Very much alive.

Source: [HuggingFace model card](https://huggingface.co/sophosympatheia/Midnight-Miqu-70B-v1.5), [Watson Out](https://www.watsonout.com/editorials/the-sovereign-stack-best-uncensored-llms-for-local-inference-dec-2025/)

---

#### L3.3-70B-Euryale-v2.3 (Sao10K)

| Property | Value |
|----------|-------|
| **Parameters** | 71B |
| **Base** | meta-llama/Llama-3.3-70B-Instruct |
| **Method** | Full fine-tune via Axolotl + DeepSpeed ZeRO-3 (LoRA r=128, alpha=16) |
| **Context** | 16,384 tokens |
| **License** | Llama 3.3 Community License |
| **NSFW** | Yes -- trained on unalignment data + RP-filtered datasets |
| **Prompt format** | Llama 3 Instruct |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Downloads** | 2,288/month |
| **HuggingFace** | [Sao10K/L3.3-70B-Euryale-v2.3](https://huggingface.co/Sao10K/L3.3-70B-Euryale-v2.3) |

**Strengths:** Clean license (Llama 3.3), strong community adoption (81 merge derivatives, 26 quant variants). Trained on curated RP/creative datasets including Hesperus-v2 data. Full fine-tune approach gives deeper integration than LoRA.

**Training data:** amoral-full-sys-prompt.json (unalignment), mimi-superfix-RP-filtered-fixed.json (RP/creative), hespera-smartshuffle.json (Hesperus-v2 instruct).

**Recommended settings:** temp 1.1, min_p 0.1.

**Release:** December 8, 2024.

Source: [HuggingFace model card](https://huggingface.co/Sao10K/L3.3-70B-Euryale-v2.3)

---

#### L3.3-70B-Magnum-Diamond (Doctor-Shotgun)

| Property | Value |
|----------|-------|
| **Parameters** | 71B |
| **Base** | meta-llama/Llama-3.3-70B-Instruct |
| **Method** | rsLoRA adapter (rank 128, alpha 16), Axolotl v0.9.2 |
| **Context** | 32,768 tokens |
| **License** | Llama 3.3 |
| **NSFW** | Yes -- trained on Claude conversation logs + creative writing data |
| **Prompt format** | Llama 3 Instruct |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Training data** | anthracite-core/magnum-v5-sft-proto-llama3-rev1-32k |
| **Downloads** | 284/month (base); 628 GGUF |
| **HuggingFace** | [Doctor-Shotgun/L3.3-70B-Magnum-Diamond](https://huggingface.co/Doctor-Shotgun/L3.3-70B-Magnum-Diamond) |

**Strengths:** Designed to emulate Claude 3 Sonnet/Opus prose quality. Multi-character dialogue, NPC management, emotional expressions, onomatopoeia. Includes SillyTavern presets. The "Magnum Diamond" line is specifically about achieving Claude-level creative writing at open-weight scale.

**Weaknesses:** Not designed for factual tasks. May exhibit "Claude-isms" in output.

**Recommended settings:** temp 1.0, min_p 0.1.

Source: [HuggingFace model card](https://huggingface.co/Doctor-Shotgun/L3.3-70B-Magnum-Diamond)

---

#### Llama-3.3-70B-Vulpecula-r1 (Sao10K + GradientPutri)

| Property | Value |
|----------|-------|
| **Parameters** | 71B |
| **Base** | meta-llama/Llama-3.3-70B-Instruct |
| **Method** | SFT + RL, ~270M tokens (210M trainable), 2 epochs |
| **Context** | Not specified (likely 128K from base) |
| **License** | Llama 3.3 Community License |
| **NSFW** | Yes -- unrestricted outputs |
| **Prompt format** | Llama 3 Instruct |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Downloads** | 112/month |
| **HuggingFace** | [Sao10K/Llama-3.3-70B-Vulpecula-r1](https://huggingface.co/Sao10K/Llama-3.3-70B-Vulpecula-r1) |

**Strengths:** Unique combination of SFT + RL training. Supports thinking mode (`<think>`) for deliberative creative choices. Trained on semi-synthetic + human-based RP datasets, diverse instruct data, and DeepSeek-R1 reasoning traces. This is one of few creative writing models with explicit reasoning capability.

**Release:** March 2025.

Source: [HuggingFace model card](https://huggingface.co/Sao10K/Llama-3.3-70B-Vulpecula-r1)

---

#### Magnum-v4-72B (anthracite-org)

| Property | Value |
|----------|-------|
| **Parameters** | 73B |
| **Base** | Qwen2.5-72B-Instruct |
| **Method** | Full-parameter fine-tuning (FFT), 8x MI300X GPUs, 2 epochs |
| **Context** | 32,768 tokens |
| **License** | Apache 2.0 |
| **NSFW** | Yes -- trained on kalo-opus-instruct-22k-no-refusal |
| **Prompt format** | ChatML |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Downloads** | 707/month (base); 1,774 GGUF |
| **HuggingFace** | [anthracite-org/magnum-v4-72b](https://huggingface.co/anthracite-org/magnum-v4-72b) |

**Strengths:** Apache 2.0 license (best in class). Full-parameter FFT on MI300X hardware means deep training. Designed to replicate Claude 3 Sonnet/Opus prose. Uses the Magnum curated dataset (c2_logs_32k, kalo-opus-instruct, claude_writing_fixed). SillyTavern compatible.

**Training datasets:** c2_logs_32k_llama3_qwen2_v1.2, kalo-opus-instruct-22k-no-refusal, kalo_opus_misc_240827, nopm_claude_writing_fixed, kalo_misc_part2.

**Weaknesses:** Qwen2.5 base, not Qwen3. Large download (~42 GB for Q4).

Source: [HuggingFace model card](https://huggingface.co/anthracite-org/Magnum-v4-72B)

---

#### Anubis-70B-v1.2 (TheDrummer)

| Property | Value |
|----------|-------|
| **Parameters** | 71B |
| **Base** | meta-llama/Llama-3.1-70B / Llama-3.3-70B-Instruct |
| **Method** | Fine-tuned |
| **License** | Llama 3 |
| **NSFW** | Yes -- reduced alignment by design |
| **Prompt format** | Llama 3 |
| **VRAM (Q4_K_M)** | ~42 GB |
| **Downloads** | 42/month (base); 1,460 GGUF |
| **HuggingFace** | [TheDrummer/Anubis-70B-v1.2](https://huggingface.co/TheDrummer/Anubis-70B-v1.2) |

**Strengths:** TheDrummer's philosophy prioritizes creativity, dynamism, and reduced corporate alignment. Good writing quality, pleasant sentence construction.

**Release:** February 2026 (v1.2 update).

Source: [HuggingFace model card](https://huggingface.co/TheDrummer/Anubis-70B-v1.2)

---

### 1.2 The 30-50B Tier (Node 1 4090 or Node 2 5090)

#### Valkyrie-49B-v2.1 (TheDrummer)

| Property | Value |
|----------|-------|
| **Parameters** | 50B |
| **Base** | nvidia/Llama-3.3-Nemotron-Super-49B-v1.5 |
| **Method** | Fine-tuned |
| **License** | Llama 3 |
| **NSFW** | Yes |
| **Prompt format** | Llama 3 |
| **VRAM (Q4_K_M)** | ~28 GB |
| **Downloads** | 157/month (base); 1,770 GGUF |
| **HuggingFace** | [TheDrummer/Valkyrie-49B-v2.1](https://huggingface.co/TheDrummer/Valkyrie-49B-v2.1) |

**Strengths:** Based on NVIDIA's Nemotron-Super which has distilled knowledge. Fits on RTX 5090 at Q4. Creative writing focus with reduced alignment.

**Release:** February 2026.

Source: [HuggingFace model card](https://huggingface.co/TheDrummer/Valkyrie-49B-v2.1)

---

#### Hermes-4.3-36B (NousResearch)

| Property | Value |
|----------|-------|
| **Parameters** | 36B |
| **Base** | ByteDance-Seed/Seed-OSS-36B-Base |
| **Method** | SFT + RL, ~5M samples / ~60B tokens, decentralized (Psyche network) |
| **Context** | Not specified (likely 32K+) |
| **License** | Apache 2.0 |
| **NSFW** | Reduced refusal rates; steerability improvements |
| **Prompt format** | ChatML with `<think>` tags |
| **VRAM (Q4_K_M)** | ~22 GB |
| **Downloads** | 5,144/month |
| **HuggingFace** | [NousResearch/Hermes-4.3-36B](https://huggingface.co/NousResearch/Hermes-4.3-36B) |

**Benchmarks:** AIME 24: 71.9%, MATH-500: 93.8%, MMLU: 87.7%, BBH: 86.4%.

**Strengths:** Not a pure creative writing model, but explicitly improved for creative writing and creativity. Hybrid reasoning mode. Apache 2.0 license. Strong tool calling. Very well-rounded -- could serve as both a narrative AI and a game logic engine.

**Release:** December 2025.

Source: [HuggingFace model card](https://huggingface.co/NousResearch/Hermes-4.3-36B)

---

#### Skyfall-31B-v4.1 (TheDrummer)

| Property | Value |
|----------|-------|
| **Parameters** | 31B |
| **Base** | Mistral-Small-3.1-24B-Base-2503 / Magistral-Small-2509 |
| **Method** | Fine-tuned |
| **License** | Mistral (check specific terms) |
| **NSFW** | Yes -- reduced alignment |
| **Prompt format** | Mistral v7 Tekken |
| **VRAM (Q4_K_M)** | ~18 GB |
| **Downloads** | 56/month (base); 3,300 GGUF |
| **HuggingFace** | [TheDrummer/Skyfall-31B-v4.1](https://huggingface.co/TheDrummer/Skyfall-31B-v4.1) |

**Strengths:** Compact but creative. Fits easily on RTX 4090 or 5090. Entertainment-first design.

**Release:** February 2026.

Source: [HuggingFace model card](https://huggingface.co/TheDrummer/Skyfall-31B-v4.1)

---

#### 32B-Qwen2.5-Kunou-v1 (Sao10K)

| Property | Value |
|----------|-------|
| **Parameters** | 33B |
| **Base** | Qwen/Qwen2.5-32B-Instruct |
| **Method** | QLoRA (rank 32, alpha 64), Axolotl v0.5.2, 1 epoch |
| **Context** | 16,384 tokens |
| **License** | Qwen |
| **NSFW** | Yes -- includes unalignment training data |
| **Prompt format** | ChatML |
| **VRAM (Q4_K_M)** | ~20 GB |
| **Downloads** | 17/month |
| **HuggingFace** | [Sao10K/32B-Qwen2.5-Kunou-v1](https://huggingface.co/Sao10K/32B-Qwen2.5-Kunou-v1) |

**Training data:** Same curated RP/creative datasets as Euryale (amoral, mimi-superfix, hespera).

**Strengths:** Spiritual successor to Euryale for the Qwen architecture. Qwen2.5-32B base means strong reasoning + creative capability.

**Release:** December 30, 2024.

Source: [HuggingFace model card](https://huggingface.co/Sao10K/32B-Qwen2.5-Kunou-v1)

---

### 1.3 The 22-24B Tier (Node 2 5090 or Node 1 4090)

#### Cydonia-24B-v4.3 (TheDrummer)

| Property | Value |
|----------|-------|
| **Parameters** | 24B |
| **Base** | Mistral-Small-3.1-24B-Base-2503 / Mistral-Small-3.2-24B-Instruct-2506 |
| **Method** | Fine-tuned |
| **Context** | 32,768 tokens (effectively handles 20K+) |
| **License** | Mistral |
| **NSFW** | Yes -- minimal refusals |
| **Prompt format** | Mistral v7 Tekken, supports `<thinking>` tags |
| **VRAM (Q4_K_M)** | ~14 GB |
| **Downloads** | 1,220/month (base); 18,739 GGUF (v4.3), 39,268 GGUF (v4.2) |
| **HuggingFace** | [TheDrummer/Cydonia-24B-v4.3](https://huggingface.co/TheDrummer/Cydonia-24B-v4.3) |

**Strengths:** Exceptional roleplay with strong character distinction. Maintains consistent character voices in multi-character scenarios. Natural response pacing. Much improved v4.3 over earlier versions. One of the most popular creative writing models by download count.

**Release:** December 2025.

Source: [HuggingFace model card](https://huggingface.co/TheDrummer/Cydonia-24B-v4.3)

---

#### MS3.2-24B-Magnum-Diamond (Doctor-Shotgun)

| Property | Value |
|----------|-------|
| **Parameters** | 24B |
| **Base** | mistralai/Mistral-Small-3.2-24B-Instruct-2506 |
| **Method** | rsLoRA adapter, Axolotl v0.9.2, Magnum v5 SFT data |
| **Context** | 32,768 tokens |
| **License** | Apache 2.0 |
| **NSFW** | Yes -- Claude conversation log training |
| **Prompt format** | Mistral v7 Tekken |
| **VRAM (Q4_K_M)** | ~14 GB |
| **Downloads** | 355/month (base); 3,282 GGUF |
| **HuggingFace** | [Doctor-Shotgun/MS3.2-24B-Magnum-Diamond](https://huggingface.co/Doctor-Shotgun/MS3.2-24B-Magnum-Diamond) |

**Strengths:** Claude-style prose at 24B. Consumer-friendly VRAM requirements. Custom loss masking for improved output quality. Works with and without character name prepending.

Source: [HuggingFace model card](https://huggingface.co/Doctor-Shotgun/MS3.2-24B-Magnum-Diamond)

---

#### Cydonia-v1.3-Magnum-v4-22B (knifeayumu)

| Property | Value |
|----------|-------|
| **Parameters** | 22B |
| **Base** | Merge of Cydonia + Magnum-v4 components |
| **Method** | mergekit merge |
| **License** | Inherited from components |
| **NSFW** | Yes |
| **VRAM (Q4_K_M)** | ~13 GB |
| **Downloads** | 150,207/month |
| **HuggingFace** | [knifeayumu/Cydonia-v1.3-Magnum-v4-22B](https://huggingface.co/knifeayumu/Cydonia-v1.3-Magnum-v4-22B) |

**Strengths:** The most downloaded creative writing model on HuggingFace by a wide margin. Combines the best of Cydonia (roleplay) and Magnum (prose quality).

Source: [HuggingFace](https://huggingface.co/knifeayumu/Cydonia-v1.3-Magnum-v4-22B)

---

### 1.4 The 12B Tier (Node 2 5060 Ti or any GPU)

#### Rocinante-X-12B-v1 (TheDrummer)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | mistralai/Mistral-Nemo-Instruct-2407 |
| **Method** | Fine-tuned |
| **Context** | Large (Nemo supports 128K, effective varies) |
| **License** | Apache 2.0 |
| **NSFW** | Yes -- non-restrictive by design |
| **Prompt format** | Mistral v3 Tekken (NOT v7) or Metharme |
| **VRAM (Q6_K)** | ~10 GB |
| **Downloads** | 740/month (base); 7,130 GGUF (official); 7,540 bartowski GGUF |
| **HuggingFace** | [TheDrummer/Rocinante-X-12B-v1](https://huggingface.co/TheDrummer/Rocinante-X-12B-v1) |

**Strengths:** "Punches above its weight class -- performs like larger 24B models." Robust character adherence after 40+ interactions. Smooth SFW/NSFW transitions. Dynamic dialogue without incoherence. Very popular with active community creating variants.

**Community variants (Feb 2026):**
- Rocinante-X-12B-v1-absolute-heresy (MuXodious) -- more uncensored
- Rocinante-X-12B-v1-Heretic-Uncensored (DavidAU) -- fully uncensored
- Rocinante-X-12B-v1c/v1d (BeaverAI) -- iterative improvements

**Release:** January 2026.

Source: [HuggingFace model card](https://huggingface.co/TheDrummer/Rocinante-X-12B-v1)

---

#### Magnum-v4-12B (anthracite-org)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | Mistral Nemo |
| **Method** | FFT with Magnum curated dataset |
| **Context** | 32K |
| **License** | Apache 2.0 |
| **NSFW** | Yes |
| **Prompt format** | ChatML |
| **VRAM (Q6_K)** | ~10 GB |
| **Downloads** | 603/month (base); 2,044 GGUF |
| **HuggingFace** | [anthracite-org/magnum-v4-12b](https://huggingface.co/anthracite-org/magnum-v4-12b) |

**Strengths:** Same Claude-emulating dataset as the 72B variant. Apache 2.0. Compact and efficient.

Source: [HuggingFace](https://huggingface.co/anthracite-org/magnum-v4-12b)

---

#### Lumimaid-Magnum-v4-12B (Undi95)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | DELLA merge of Lumimaid-v0.2-12B + LocalC-12B + magnum-v4-12b + Mistral-Nemo-Instruct-2407 |
| **Method** | DELLA merge via mergekit |
| **Context** | 16K |
| **License** | Inherited (mixed) |
| **NSFW** | Yes -- Lumimaid component is NSFW-focused |
| **Prompt format** | Mistral Instruct |
| **VRAM (Q6_K)** | ~10 GB |
| **Downloads** | 119/month (base); 2,994 bartowski GGUF |
| **HuggingFace** | [Undi95/Lumimaid-Magnum-v4-12B](https://huggingface.co/Undi95/Lumimaid-Magnum-v4-12B) |

**Strengths:** Best-of-both merge: Lumimaid's NSFW capability + Magnum's prose quality. DELLA merge method is more sophisticated than SLERP/TIES.

Source: [HuggingFace](https://huggingface.co/Undi95/Lumimaid-Magnum-v4-12B)

---

#### Lumimaid-v0.2-12B (NeverSleep)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | Mistral-based |
| **License** | CC-BY-NC-4.0 |
| **NSFW** | Yes -- primary design focus |
| **Downloads** | 2,830/month |
| **HuggingFace** | [NeverSleep/Lumimaid-v0.2-12B](https://huggingface.co/NeverSleep/Lumimaid-v0.2-12B) |

**Recent variant (Feb 2026):** Lumimaid-v0.2-8B-Heretic (0xA50C1A1) -- 8B version with enhanced uncensoring.

**Strengths:** The Lumimaid line is the most well-known NSFW-focused model family. Strong at character adherence in intimate scenarios.

**Weaknesses:** CC-BY-NC license restricts commercial use. Lumimaid v0.2 series dates from July 2024 but remains actively used.

Source: [HuggingFace](https://huggingface.co/NeverSleep/Lumimaid-v0.2-12B)

---

#### Pygmalion-3-12B (PygmalionAI)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | Mistral Nemo Base (2407) |
| **Method** | Rank-32 LoRA, 8x NVIDIA A40, hundreds of millions of tokens |
| **License** | Apache 2.0 |
| **NSFW** | Yes -- explicitly not safety-tuned |
| **Prompt format** | ChatML |
| **Downloads** | 229/month |
| **HuggingFace** | [PygmalionAI/Pygmalion-3-12B](https://huggingface.co/PygmalionAI/Pygmalion-3-12B) |

**Training data:** Custom roleplay forum data, PIPPA dataset, conversation and creative writing corpora.

**Strengths:** Historic roleplay model family. Open data pipeline. Known `<|im_end|>` token issue -- requires custom token ban.

Source: [HuggingFace model card](https://huggingface.co/PygmalionAI/Pygmalion-3-12B)

---

#### Violet Twilight v0.2 (Epiculous)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | SLERP merge of Azure_Dusk-v0.2 + Crimson_Dawn-v0.2 (both Nemo-based) |
| **Method** | SLERP merge via mergekit |
| **License** | Apache 2.0 |
| **NSFW** | Trained on kalo-opus-instruct-22k-no-refusal |
| **Prompt format** | ChatML |
| **VRAM (Q6_K)** | ~10 GB |
| **Downloads** | 349/month (base); 14,919 GGUF |
| **HuggingFace** | [Epiculous/Violet_Twilight-v0.2](https://huggingface.co/Epiculous/Violet_Twilight-v0.2) |

**Training data (components):** Gryphe/Sonnet3.5-Charcard-Roleplay, anthracite-org/nopm_claude_writing_fixed, anthracite-org/kalo-opus-instruct-22k-no-refusal.

Source: [HuggingFace model card](https://huggingface.co/Epiculous/Violet_Twilight-v0.2)

---

#### NemoMix-Unleashed-12B (MarinaraSpaghetti)

| Property | Value |
|----------|-------|
| **Parameters** | 12B |
| **Base** | Nemo architecture |
| **License** | Check original |
| **NSFW** | Yes -- "Unleashed" |
| **Downloads** | 14,009/month (GGUF) |
| **HuggingFace** | [MarinaraSpaghetti/NemoMix-Unleashed-12B](https://huggingface.co/MarinaraSpaghetti/NemoMix-Unleashed-12B) |

**Strengths:** Very high download count suggests strong community validation. Uncensored variant of NemoMix.

Source: [HuggingFace](https://huggingface.co/MarinaraSpaghetti/NemoMix-Unleashed-12B)

---

#### Gemma-The-Writer-N-Restless-Quill-10B (DavidAU)

| Property | Value |
|----------|-------|
| **Parameters** | 10B |
| **Base** | Google Gemma-2-9B |
| **Method** | DARE TIES merge (168-point layer-level), enhanced with Brainstorm 5X Adapter |
| **Context** | 8K (extendable to 32K via RoPE) |
| **License** | Apache 2.0 |
| **NSFW** | Yes -- prompt-controlled uncensoring |
| **VRAM (Q4_K_M)** | ~6 GB |
| **Downloads** | 11,459/month |
| **HuggingFace** | [DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF](https://huggingface.co/DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF) |

**Merge components:** Gemma-2-Ataraxy-9B, Gemma-2-9B-It-SPPO-Iter3, Gemma-2-Ifable-9B, Gemma-2-9B-It-SimPO. Brainstorm adapter: gemma2-gutenberg-9B, Tiger-Gemma-9B-v2, Ellaria-9B.

**Unique feature:** "Brainstorm 5X Adapter" splits and expands the reasoning center 5X, reducing GPTisms and cliches while increasing output length and prose variety.

Source: [HuggingFace model card](https://huggingface.co/DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF)

---

### 1.5 The 8B Tier (Lightweight / Draft)

#### L3-8B-Stheno-v3.2 / v3.4 (Sao10K)

| Property | Value |
|----------|-------|
| **Parameters** | 8B |
| **Base** | Llama 3 8B / Llama 3.1 8B |
| **License** | Llama 3 |
| **NSFW** | Yes |
| **Downloads** | 6,136/month (v3.2 base); 13,966 (v3.2 GGUF); 2,753 (v3.4 GGUF) |
| **HuggingFace** | [Sao10K/L3-8B-Stheno-v3.2](https://huggingface.co/Sao10K/L3-8B-Stheno-v3.2) |

**Strengths:** The most downloaded 8B creative writing model. Good for fast iteration or when VRAM is constrained.

Source: [HuggingFace](https://huggingface.co/Sao10K/L3-8B-Stheno-v3.2)

---

### 1.6 Additional Size Variants

#### Magnum-v4-123B (anthracite-org)

| Property | Value |
|----------|-------|
| **Parameters** | 123B (Mistral Large based) |
| **License** | Mistral Research |
| **NSFW** | Yes |
| **Downloads** | 253/month |
| **HuggingFace** | [anthracite-org/magnum-v4-123b](https://huggingface.co/anthracite-org/magnum-v4-123b) |

Too large for Athanor's single-node VRAM. Listed for completeness.

#### ML2-123B-Magnum-Diamond (Doctor-Shotgun)

| Property | Value |
|----------|-------|
| **Parameters** | 123B |
| **Base** | Mistral Large 2 |
| **Downloads** | 476 GGUF |
| **HuggingFace** | [Doctor-Shotgun/ML2-123B-Magnum-Diamond](https://huggingface.co/Doctor-Shotgun/ML2-123B-Magnum-Diamond) |

Same approach as the 24B/70B Diamond variants. Too large for comfortable operation on Athanor.

---

### 1.7 Legacy Models (Still Referenced, Mostly Outdated)

| Model | Params | Base | Status |
|-------|--------|------|--------|
| MythoMax-L2-13B (Gryphe) | 13B | Llama 2 | Classic RP model, outdated architecture |
| StellarBright 70B (sequelbox) | 70B | Llama 2 | Good prose, outdated Llama 2 base |
| Fimbulvetr-11B-v2 | 11B | Unknown | Creative writing, recent quants but old model |
| Noromaid v0.1-v0.4 (NeverSleep) | 7-47B | Various | NSFW-focused, older Mistral/Llama 2 base |
| Mythalion-13B (PygmalionAI) | 13B | Llama 2 | MythoMax + Pygmalion merge |

These are not recommended for new deployments. Modern 12B Nemo-based models significantly outperform Llama 2 13B models.

---

## Part 2: Creative Writing Enhancement Tools

### Creative Writing Control Vectors v3.0 (jukofyork)

| Property | Value |
|----------|-------|
| **Type** | Control vectors for llama.cpp |
| **Downloads** | 15,678/month |
| **Models supported** | 50+ models across all sizes |
| **HuggingFace** | [jukofyork/creative-writing-control-vectors-v3.0](https://huggingface.co/jukofyork/creative-writing-control-vectors-v3.0) |

**Controllable axes:**
1. **Language:** Simple to Ornate
2. **Storytelling:** Explicit to Descriptive
3. **Character Focus:** Narration to Dialogue
4. **Dark Tetrad:** Empathy/Sociopathy, Honesty/Machiavellianism, Humility/Narcissism, Compassion/Sadism
5. **Outlook:** Optimism to Nihilism

**How it works:** Pre-computed direction vectors in GGUF format. Applied at inference time via `--control-vector` flags in llama.cpp. Each axis has a debias vector (neutralizes the default bias) and endpoint vectors (pushes toward one end). Scale factors allow fine-tuned control.

**For EoBQ:** This is extremely relevant. Different characters could have different control vector configurations. A cruel queen could use Machiavellianism + Narcissism + Ornate vectors. A street urchin could use Simple + Dialogue + Empathy vectors. This creates distinct character voices without needing separate models.

**Limitation:** Only works with llama.cpp GGUF models, not vLLM. Would require switching inference backend for this feature, or using llama.cpp alongside vLLM.

Source: [HuggingFace model card](https://huggingface.co/jukofyork/creative-writing-control-vectors-v3.0)

---

### DavidAU Brainstorm Adapter Technique

Not a standalone tool but a repeatable technique. DavidAU's models use a "Brainstorm 5X Adapter" that expands the reasoning center of merged models, reducing GPTisms and increasing prose variety. The technique is documented on individual model cards.

Source: [Gemma-The-Writer model card](https://huggingface.co/DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF)

---

## Part 3: Writing Quality Benchmarks

### WritingBench (arXiv:2503.05244)

| Property | Value |
|----------|-------|
| **Paper** | "WritingBench: A Comprehensive Benchmark for Generative Writing" |
| **Authors** | Yuning Wu, Jiahao Mei, Ming Yan, et al. |
| **Published** | March 2025, updated November 2025 |
| **Domains** | 6 core writing domains, 100 subdomains |
| **Critic model** | WritingBench-Critic-Model-Qwen-7B |

**Methodology:** Query-dependent evaluation framework that generates instance-specific assessment criteria. Evaluates style, format, and length. Found that their 7B critic model outperformed GPT-4o for writing evaluation.

**Relevance:** The critic model could be used for automated quality evaluation of EoBQ dialogue output. The benchmark itself could be used to compare candidate models.

**Critic model:** [AQuarterMile/WritingBench-Critic-Model-Qwen-7B](https://huggingface.co/AQuarterMile/WritingBench-Critic-Model-Qwen-7B) (47 downloads, 8B params)

Source: [arXiv:2503.05244](https://arxiv.org/abs/2503.05244)

---

### Ayumi ERP Rating

| Property | Value |
|----------|-------|
| **URL** | [rentry.org/ayumi_erp_rating](https://rentry.org/ayumi_erp_rating) |
| **Models rated** | 495 |
| **Last updated** | November 2023 |
| **Metrics** | ALC-IQ3 (character comprehension), ERP3 (explicit word ratio) |

**Critical limitation:** Explicitly states "Writing quality is not covered!" Only measures character adherence and willingness to generate NSFW content. Does not evaluate prose quality, coherence, creativity, or narrative ability.

**Verdict:** Useful for confirming a model is willing to produce NSFW content, but not for comparing writing quality.

Source: [Ayumi Rating](https://rentry.org/ayumi_erp_rating)

---

## Part 4: Model Architecture Approaches for Game Narrative

### Fine-Tuning vs Prompting vs RAG

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Specialized fine-tune** (Magnum, Euryale, etc.) | Best prose quality, consistent style | Locked to one model, retraining needed | Primary dialogue generation |
| **Prompting general model** (Qwen3-32B + system prompt) | Flexible, easy to change, reasoning capability | Prose can be generic, "assistant-brain" | Game logic, plot decisions, state management |
| **RAG** (Qdrant + character sheets) | Dynamic context, unlimited character memory | Retrieval latency, prompt engineering required | Character memory, lore consistency |
| **Control vectors** (jukofyork) | Per-character style control without retraining | Only works with llama.cpp GGUF | Character voice differentiation |
| **Multi-model pipeline** | Best of each model's strengths | Complex orchestration, latency | Production game architecture |

### Recommended EoBQ Architecture: Multi-Model Pipeline

```
Player input
  -> Qwen3-32B (Node 1 TP=4): Parse intent, determine narrative consequences
  -> RAG lookup: Character state, lore context, relationship scores
  -> Creative model (Node 1 4090 or Node 2): Generate dialogue + scene description
  -> WritingBench-Critic (Node 2 5060 Ti): Quality gate
  -> Update state store
  -> Return to player
```

### Structured Narrative Output

No models specifically support structured narrative output (scene graphs, character state JSON). However, several approaches work:

1. **Hermes 4.3 and Qwen3**: Native JSON/structured output via tool calling. Use the reasoning model for structured decisions, creative model for prose.
2. **Two-pass generation:** First pass generates structured plot decisions (JSON), second pass generates prose based on those decisions.
3. **SillyTavern-style character cards:** Community standard for character definition that all RP models understand. Use this format for character state injection into prompts.

### Multi-Character Dialogue Management

The Magnum Diamond models (Doctor-Shotgun) explicitly support multi-character dialogue and NPC management. Their SillyTavern presets include variants for character name prepending. For EoBQ, this means:

- Each character gets a name-prepended dialogue section
- Character personality vectors are injected as system prompt context
- The model maintains distinct voices per character within a single generation

---

## Part 5: Comprehensive Model Matrix

### Models Released or Updated Dec 2025 - Feb 2026

| Model | Params | Base | License | NSFW | VRAM (Q4) | Best For | Downloads/mo |
|-------|--------|------|---------|------|-----------|----------|-------------|
| **Anubis-70B-v1.2** | 71B | Llama 3.1/3.3 | Llama 3 | Yes | ~42 GB | Prose + RP | 1,502 |
| **Valkyrie-49B-v2.1** | 50B | Nemotron-Super-49B | Llama 3 | Yes | ~28 GB | Creative writing | 1,927 |
| **Hermes-4.3-36B** | 36B | Seed-36B | Apache 2.0 | Reduced refusals | ~22 GB | General + creative | 5,144 |
| **Skyfall-31B-v4.1** | 31B | Mistral Small 3.1 | Mistral | Yes | ~18 GB | Creative writing | 3,356 |
| **Cydonia-24B-v4.3** | 24B | Mistral Small 3.1/3.2 | Mistral | Yes | ~14 GB | RP + character | 59,007* |
| **Rocinante-X-12B-v1** | 12B | Mistral Nemo | Apache 2.0 | Yes | ~7 GB | RP + prose | 15,410 |
| **Lumimaid-v0.2-8B-Heretic** | 8B | Lumimaid-v0.2-8B | Mixed | Yes | ~5 GB | NSFW RP | 6,520 |
| **Midnight Miqu 70B v1.5** (new quants) | 70B | Miqu (Mistral) | Personal use | Yes | ~42 GB | Prose quality | 9,212+ |
| **L3.3-70B-Euryale-v2.3** | 71B | Llama 3.3 70B | Llama 3.3 | Yes | ~42 GB | RP + creative | 2,288 |
| **L3.3-70B-Magnum-Diamond** | 71B | Llama 3.3 70B | Llama 3.3 | Yes | ~42 GB | Claude-style prose | 912 |
| **Magnum-v4-72B** | 73B | Qwen2.5-72B | Apache 2.0 | Yes | ~42 GB | Claude-style prose | 2,481 |

*Downloads include all quant versions.

### All Sizes Available

| Size Tier | Best Options | Fits On |
|-----------|-------------|---------|
| **70B** | Midnight Miqu v1.5, Euryale v2.3, Magnum-Diamond, Magnum-v4-72B | Node 1 TP=4 (64 GB) |
| **49B** | Valkyrie-49B-v2.1 | Node 2 5090 (32 GB) at Q4 |
| **36B** | Hermes 4.3 36B | Node 2 5090 (32 GB) at Q4 |
| **31B** | Skyfall-31B-v4.1 | Node 1 4090 (24 GB) at Q4 |
| **24B** | Cydonia-24B-v4.3, MS3.2-24B-Magnum-Diamond | Node 1 4090 (24 GB) at Q4-Q6 |
| **22B** | Cydonia-v1.3-Magnum-v4-22B | Node 1 4090 (24 GB) at Q6 |
| **12B** | Rocinante-X-12B-v1, Magnum-v4-12B, Lumimaid-Magnum-v4-12B | Any GPU (7-10 GB) |
| **10B** | Gemma-Writer-Restless-Quill-10B | Node 2 5060 Ti at Q8 |
| **8B** | Stheno-v3.2/v3.4, Lumimaid-v0.2-8B-Heretic | Any GPU (5 GB) |

---

## Part 6: Key Observations

### 1. The Qwen3 Gap

There are ZERO Qwen3-based creative writing fine-tunes as of February 2026. The creative writing community has not yet caught up to Qwen3. All specialized models are based on:
- Mistral Nemo 12B (most popular target)
- Mistral Small 24B (growing)
- Llama 3.3 70B (premium tier)
- Qwen2.5-72B (used by anthracite-org Magnum)

**Implication for Athanor:** Running Qwen3-32B-AWQ for general tasks + a specialized creative model for EoBQ dialogue is the right approach. When Qwen3 creative fine-tunes appear, this gap will close.

### 2. The Magnum Dataset is Central

The anthracite-org datasets (kalo-opus-instruct-22k-no-refusal, c2_logs_32k, nopm_claude_writing_fixed) are the most commonly used training data across creative writing models. These are distilled from Claude 3 Sonnet/Opus conversations. This means most top creative writing models are essentially "distilled Claude" at various scales and architectures.

### 3. TheDrummer Dominates the Consumer Space

TheDrummer (213 models) produces the most popular creative writing models across multiple size tiers: Cydonia (24B), Skyfall (31B), Valkyrie (49B), Anubis (70B), and Rocinante (12B). His design philosophy of "creativity over alignment" directly aligns with EoBQ requirements.

### 4. License Landscape

| License | Models |
|---------|--------|
| **Apache 2.0** (best) | Magnum-v4-72B, Hermes 4.3, Rocinante, Magnum-v4-12B, Pygmalion-3 |
| **Llama 3.3** (commercial OK <700M MAU) | Euryale, Magnum-Diamond-70B, Anubis, Valkyrie, Vulpecula |
| **Mistral** (varies) | Cydonia, Skyfall, MS3.2-Magnum-Diamond |
| **CC-BY-NC** (non-commercial) | Lumimaid v0.2 |
| **Personal use only** | Midnight Miqu (leaked weights) |

### 5. Context Length Trade-off

Most creative writing models cap at 16K-32K context despite base models supporting 128K. This is because training at longer contexts is exponentially more expensive. For EoBQ, 32K is sufficient -- character state and recent dialogue rarely exceed 8K tokens with proper RAG.

---

## Part 7: Recommendation for EoBQ

### Primary Recommendation: EoBQ Production Mode

```
Node 1 (4x 5070 Ti TP=4, 64 GB):
  Magnum-v4-72B (Q4_K_M, ~42 GB)
  -- Apache 2.0 license
  -- Claude-quality prose
  -- Handles all narrative tasks: dialogue, description, plot decisions
  -- 32K context

  OR for best pure prose quality:
  Midnight Miqu 70B v1.5 (Q4_K_M, ~42 GB)
  -- Personal use only (acceptable for EoBQ)
  -- Community consensus: best creative prose
  -- 32K context

Node 1 4090 (24 GB):
  Cydonia-24B-v4.3 (Q6_K, ~18 GB)
  -- Real-time character dialogue
  -- Strong multi-character distinction
  -- Fast enough for interactive gameplay

Node 2 5060 Ti (16 GB):
  Rocinante-X-12B-v1 (Q8, ~12 GB)
  -- Draft generation / fast iteration
  -- "Punches above its weight"
  -- Also usable as WritingBench critic host

Node 2 5090 (32 GB):
  ComfyUI (image/video generation for scenes)
  -- OR Valkyrie-49B-v2.1 (Q4, ~28 GB) when not generating visuals
```

### Alternative: Simpler Architecture

If running multiple models is too complex, a single Magnum-v4-72B on Node 1 TP=4 handles everything. Use the Qwen3-32B on Node 2 5090 for game logic and state management that doesn't need creative prose quality.

### Creative Writing Control Vectors

If using llama.cpp instead of vLLM for the creative model, apply jukofyork control vectors per-character:

| Character Archetype | Vector Configuration |
|--------------------|---------------------|
| Cruel aristocrat | Ornate + Machiavellianism + Narcissism + Descriptive |
| Street survivor | Simple + Dialogue + Empathy debias + Nihilism |
| Seductive spy | Ornate + Machiavellianism + Descriptive + Sadism debias |
| Naive scholar | Ornate + Narration + Empathy + Optimism |

This creates distinct character voices from a single model without fine-tuning.

### Quality Gate

Deploy WritingBench-Critic-Model-Qwen-7B on the 5060 Ti (alongside Rocinante or standalone) to automatically score generated dialogue before presenting to the player. Reject and regenerate outputs below threshold.

---

## Part 8: Open Questions

1. **Qwen3 creative fine-tunes:** When will the community produce Magnum/Euryale equivalents on Qwen3-32B? This would let Athanor consolidate on one architecture.

2. **Control vectors in vLLM:** Can control vectors be ported to vLLM, or does EoBQ need llama.cpp for per-character voice control?

3. **Head-to-head prose comparison:** Need blind comparison of Midnight Miqu v1.5 vs Magnum-v4-72B vs L3.3-70B-Magnum-Diamond vs Qwen3-32B-abliterated on EoBQ-specific prompts (character dialogue, scene description, plot progression).

4. **Magnum v5 training data:** Doctor-Shotgun's Magnum-Diamond models reference "magnum-v5-sft-proto" data. Is v5 data publicly available? It could be used for custom EoBQ fine-tuning.

5. **Multi-model latency:** What is the added latency of routing through a quality gate model vs single-model generation? Is it acceptable for interactive gameplay?

6. **WritingBench on creative models:** Has anyone run WritingBench on the specialized creative writing models listed here? Standard benchmarks (MMLU, etc.) are meaningless for this use case.

---

## Source Summary

| Source Type | URLs |
|-------------|------|
| HuggingFace model cards | 20+ individual model pages cited inline |
| HuggingFace API | `huggingface.co/api/models` queries for model discovery |
| Watson Out | [Sovereign Stack article](https://www.watsonout.com/editorials/the-sovereign-stack-best-uncensored-llms-for-local-inference-dec-2025/) |
| arXiv | [WritingBench (2503.05244)](https://arxiv.org/abs/2503.05244) |
| Community benchmark | [Ayumi ERP Rating](https://rentry.org/ayumi_erp_rating) |
| Existing Athanor research | `docs/research/2026-02-16-uncensored-llm-models.md` |
| Existing Athanor architecture | `docs/projects/eoq/ARCHITECTURE.md` |

---

## Key Model Makers (Follow for Updates)

| Creator | Profile | Specialty | Models |
|---------|---------|-----------|--------|
| **TheDrummer** | [HF](https://huggingface.co/TheDrummer) | Creative writing fine-tunes | 213 models: Cydonia, Skyfall, Valkyrie, Anubis, Rocinante |
| **Sao10K** | [HF](https://huggingface.co/Sao10K) | RP fine-tunes | 34 models: Euryale, Stheno, Kunou, Vulpecula, Freya |
| **Doctor-Shotgun** | [HF](https://huggingface.co/Doctor-Shotgun) | Claude-style prose | Magnum Diamond (24B, 70B, 123B) |
| **anthracite-org** | [HF](https://huggingface.co/anthracite-org) | FFT creative models | Magnum v1-v4 (9B to 123B) |
| **DavidAU** | [HF](https://huggingface.co/DavidAU) | Creative merges + adapters | 100+ models: Gemma-Writer, MOE hybrids, Heretic variants |
| **Undi95** | [HF](https://huggingface.co/Undi95) | Creative merges | 293 models: Lumimaid-Magnum, MistralThinker, QwQ-RP |
| **NeverSleep** | [HF](https://huggingface.co/NeverSleep) | NSFW models | Lumimaid, Noromaid |
| **Epiculous** | [HF](https://huggingface.co/Epiculous) | Nemo creative merges | Violet Twilight, Crimson Dawn, Azure Dusk |
| **PygmalionAI** | [HF](https://huggingface.co/PygmalionAI) | Roleplay foundation | Pygmalion-3, Mythalion |
| **jukofyork** | [HF](https://huggingface.co/jukofyork) | Control vectors + writer models | Creative Writing Control Vectors v3.0, command-r-writer |
| **NousResearch** | [HF](https://huggingface.co/NousResearch) | General + creative | Hermes 4.3, Hermes 4 |
