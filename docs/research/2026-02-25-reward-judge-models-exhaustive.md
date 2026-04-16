# Reward, Judge, and Verifier Models -- Exhaustive Survey

**Date:** 2026-02-25
**Purpose:** Identify every viable reward/judge/critic/verifier model for Athanor's quality cascade -- local models evaluate code quality before deciding whether to escalate to cloud (Claude).
**Hardware context:** Node 1 has 4x 5070 Ti (16 GB each, GPUs 0-3 used for vLLM TP=4) + 1x 4090 (24 GB, GPU 4 shared with embedding + voice). Node 2 has 5090 (32 GB) + 5060 Ti (16 GB). VAULT has 128 GB DDR5 RAM for CPU inference.

---

## Executive Summary

The reward model landscape has matured significantly. The most important release in this space is **Skywork-Reward-V2** (Jul 2025), which provides 8 model sizes from 0.6B to 8B, all achieving SOTA or near-SOTA performance. For Athanor's cascade gating, the **Skywork-Reward-V2-Qwen3-0.6B** (1.2 GB VRAM) is the clear first choice -- it nearly matches the previous SOTA 27B model's performance while fitting trivially alongside any other workload.

**Top recommendation for Athanor:** Skywork-Reward-V2-Qwen3-0.6B as the primary gate, with Skywork-Reward-V2-Qwen3-1.7B as an upgrade path. Both run on CPU or as a sliver of GPU 4.

**Strict 90-day window note:** Very few production-grade reward models were released in the Dec 2025 - Feb 2026 window specifically. The most notable is RLAnything (Feb 2026), which is an RL framework with co-trained reward models. The major wave of high-quality reward model releases occurred in the May-Sep 2025 period. This survey covers the full current landscape to be useful for architecture decisions.

---

## Table of Contents

1. [Bradley-Terry Reward Models](#1-bradley-terry-reward-models)
2. [Generative Judge / Reasoning Reward Models](#2-generative-judge--reasoning-reward-models)
3. [Process Reward Models (PRM)](#3-process-reward-models-prm)
4. [Multi-Objective / Specialized Reward Models](#4-multi-objective--specialized-reward-models)
5. [Code-Specific Models](#5-code-specific-models)
6. [Safety-Specific Models](#6-safety-specific-models)
7. [Small Models for Cascade Gating](#7-small-models-for-cascade-gating)
8. [Benchmark Reference](#8-benchmark-reference)
9. [Athanor Integration Analysis](#9-athanor-integration-analysis)
10. [Recommendation](#10-recommendation)

---

## 1. Bradley-Terry Reward Models

These models output a single scalar reward score. Input is a conversation (prompt + response); output is a float. Fast, simple, ideal for cascade gating.

### Skywork-Reward-V2 Series (SOTA)

**Release:** Jul 2025 | **Paper:** [arXiv:2507.01352](https://arxiv.org/abs/2507.01352) | **License:** Apache-2.0 (Qwen variants), Llama 3.x (Llama variants)
**Training data:** 26 million preference pairs via human-LLM synergistic pipeline.
**Max context:** 16,384 tokens.

| Model | Params | Base | RBv1 | RBv2 | RM-Bench | JudgeBench | Avg (7 bench) | VRAM (fp16) | HuggingFace |
|-------|--------|------|------|------|----------|------------|---------------|-------------|-------------|
| Skywork-Reward-V2-Qwen3-0.6B | 0.6B | Qwen3-0.6B | 85.2 | 61.3 | 74.4 | 67.6 | 70.9 | ~1.2 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Qwen3-0.6B) |
| Skywork-Reward-V2-Qwen3-1.7B | 1.7B | Qwen3-1.7B | 90.3 | 68.3 | 78.7 | 72.9 | 75.2 | ~3.4 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Qwen3-1.7B) |
| Skywork-Reward-V2-Qwen3-4B | 4B | Qwen3-4B | 93.4 | 75.5 | 81.6 | 69.3 | 77.8 | ~8 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Qwen3-4B) |
| Skywork-Reward-V2-Qwen3-8B | 8B | Qwen3-8B | 93.7 | 78.2 | 82.6 | 73.4 | 79.3 | ~16 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Qwen3-8B) |
| Skywork-Reward-V2-Llama-3.2-1B | 1B | Llama-3.2-1B | 89.9 | 64.3 | 76.4 | 65.0 | 72.3 | ~2 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Llama-3.2-1B) |
| Skywork-Reward-V2-Llama-3.2-3B | 3B | Llama-3.2-3B | 93.0 | 74.7 | 81.1 | 69.2 | 77.1 | ~6 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Llama-3.2-3B) |
| Skywork-Reward-V2-Llama-3.1-8B | 8B | Llama-3.1-8B | 96.4 | 84.1 | 92.8 | 80.0 | 85.8 | ~16 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Llama-3.1-8B) |
| Skywork-Reward-V2-Llama-3.1-8B-40M | 8B | Llama-3.1-8B | **97.8** | **86.5** | **96.0** | **83.4** | **88.6** | ~16 GB | [Link](https://huggingface.co/Skywork/Skywork-Reward-V2-Llama-3.1-8B-40M) |

**Key insight:** The 0.6B Qwen3 variant scores 70.9 avg -- nearly matching the previous generation's best (Skywork-Reward-Gemma-2-27B-v0.2 at 71.6 avg). This is a 45x parameter reduction for equivalent performance.

**Usage:** `AutoModelForSequenceClassification` + `AutoTokenizer`. Input is chat-template formatted. Output is `logits[0][0].item()`. SGLang compatible with `--is-embedding` flag.

**Note on 40M variant:** Trained on full 40M pairs with 1/3 flipped labels. Authors mark it experimental/research-only. Outperforms everything on every benchmark.

### NVIDIA Nemotron Reward Models

| Model | Params | Base | RM-Bench | JudgeBench | License | HuggingFace |
|-------|--------|------|----------|------------|---------|-------------|
| Qwen-3-Nemotron-32B-Reward | 32B | Qwen3-32B | 81.9 | 72.3 | NVIDIA Open | [Link](https://huggingface.co/nvidia/Qwen-3-Nemotron-32B-Reward) |
| Llama-3.3-Nemotron-70B-Reward | 70B | Llama-3.3-70B | 79.9 | 73.7 | NVIDIA Open | [Link](https://huggingface.co/nvidia/Llama-3.3-Nemotron-70B-Reward) |
| Llama-3.3-Nemotron-70B-Reward-Multilingual | 70B | Llama-3.3-70B | 82.4 | 69.4 | NVIDIA Open | [Link](https://huggingface.co/nvidia/Llama-3.3-Nemotron-70B-Reward-Multilingual) |
| Llama-3.1-Nemotron-70B-Reward-HF | 70B | Llama-3.1-70B | -- | -- | NVIDIA Open | [Link](https://huggingface.co/nvidia/Llama-3.1-Nemotron-70B-Reward-HF) |

**Release:** Jun 2025 (32B), various dates for 70B variants.
**Training data:** HelpSteer3 (38K prompts with human preferences).
**Key detail:** Qwen-3-Nemotron-32B-Reward requires `/nothink` appended to user query and empty `<think>\n\n</think>\n\n` prefix in assistant response. Trained to preserve Qwen3's reasoning capability.
**VRAM:** 32B needs ~64 GB (fp16) or ~32 GB (int8). Too large for a single 16 GB GPU but could run on 4x 5070 Ti with TP=4 -- conflicts with generation model.
**Verdict for Athanor:** Too large for co-location. Not recommended unless dedicated GPU time is available.

### InternLM2 Reward Models

**Release:** Mar 2025 (last update) | **Paper:** [arXiv:2403.17297](https://arxiv.org/abs/2403.17297) | **License:** Other (InternLM license)
**Training data:** 2.4M preference pairs, human + AI synthesized. Multilingual (EN + ZH).

| Model | Params | RewardBench Score | VRAM (fp16) | HuggingFace |
|-------|--------|-------------------|-------------|-------------|
| InternLM2-1.8B-Reward | 1.8B | 80.6 | ~3.6 GB | [Link](https://huggingface.co/internlm/internlm2-1_8b-reward) |
| InternLM2-7B-Reward | 7B | 86.6 | ~14 GB | [Link](https://huggingface.co/internlm/internlm2-7b-reward) |
| InternLM2-20B-Reward | 20B | 89.5 | ~40 GB | [Link](https://huggingface.co/internlm/internlm2-20b-reward) |

**Usage:** Uses `trust_remote_code=True` with custom `AutoModel` (not `AutoModelForSequenceClassification`). Has `.get_score()`, `.compare()`, `.rank()` APIs built into the model class.
**Note:** 92K downloads for the 1.8B variant -- very popular. Well-tested in production.

### GRM (Generalizable Reward Model) Series

**Release:** Feb-Apr 2025 | **Paper:** [arXiv:2406.10216](https://arxiv.org/abs/2406.10216) | **License:** Apache-2.0

| Model | Params | RewardBench Score | VRAM (fp16) | HuggingFace |
|-------|--------|-------------------|-------------|-------------|
| GRM-gemma2-2B-rewardmodel-ft | 2B | 88.4 | ~4 GB | [Link](https://huggingface.co/Ray2333/GRM-gemma2-2B-rewardmodel-ft) |
| GRM-Llama3.2-3B-rewardmodel-ft | 3B | 90.9 | ~6 GB | [Link](https://huggingface.co/Ray2333/GRM-Llama3.2-3B-rewardmodel-ft) |
| GRM-Llama3-8B-rewardmodel-ft | 8B | 91.5 | ~16 GB | [Link](https://huggingface.co/Ray2333/GRM-Llama3-8B-rewardmodel-ft) |

**Key insight:** GRM-gemma2-2B achieves 88.4 on RewardBench v1 -- outperforming GPT-4o (86.7) and Gemini 1.5 Pro (88.2) with only 2B params. SOTA among sub-3B models at time of release.
**Usage:** Standard `AutoModelForSequenceClassification` pattern.

### ArmoRM (Absolute-Rating Multi-Objective RM)

**Release:** Sep 2024 (last update) | **Paper:** [arXiv:2406.12845](https://arxiv.org/abs/2406.12845) | **License:** Llama 3

| Model | Params | RewardBench Score | VRAM (fp16) | HuggingFace |
|-------|--------|-------------------|-------------|-------------|
| ArmoRM-Llama3-8B-v0.1 | 8B | 89.0 | ~16 GB | [Link](https://huggingface.co/RLHFlow/ArmoRM-Llama3-8B-v0.1) |

**Unique feature:** Outputs 19 individual reward dimensions (helpfulness, correctness, coherence, complexity, verbosity, safety, code-quality, etc.) plus a MoE-gated aggregate score. The gating is prompt-conditioned -- different prompts weight different objectives differently.
**19 objectives include:** `code-complexity`, `code-style`, `code-explanation`, `code-instruction-following`, `code-readability` -- making it uniquely suited for code quality assessment.
**Usage:** Requires `trust_remote_code=True`. Returns `.rewards` (19-dim), `.gating_output`, and `.score`.

### Older/Reference BT Models

| Model | Params | RewardBench v1 | Release | License | HuggingFace |
|-------|--------|----------------|---------|---------|-------------|
| FsfairX-LLaMA3-RM-v0.1 | 8B | 83.6 | 2024 | Apache-2.0 | [Link](https://huggingface.co/sfairXC/FsfairX-LLaMA3-RM-v0.1) |
| Llama-3-OffsetBias-RM-8B | 8B | 89.0 | Sep 2024 | Llama 3 | [Link](https://huggingface.co/NCSOFT/Llama-3-OffsetBias-RM-8B) |
| Starling-RM-7B-alpha | 7B | 74.6 | 2023 | -- | [Link](https://huggingface.co/berkeley-nest/Starling-RM-7B-alpha) |
| UltraRM-13b | 13B | 71.3 | 2023 | -- | [Link](https://huggingface.co/openbmb/UltraRM-13b) |
| Eurus-RM-7b | 7B | -- | 2024 | -- | [Link](https://huggingface.co/openbmb/Eurus-RM-7b) |

---

## 2. Generative Judge / Reasoning Reward Models

These models generate text reasoning before producing a preference judgment. Slower than BT models but often more accurate and interpretable.

### RM-R1 (Reasoning Reward Model)

**Release:** Jun 2025 | **Paper:** [arXiv:2505.02387](https://arxiv.org/abs/2505.02387) | **License:** MIT

| Model | Params | Base | RewardBench v1 | HuggingFace |
|-------|--------|------|----------------|-------------|
| RM-R1-Qwen2.5-Instruct-7B | 7B | Qwen2.5-7B-Instruct | ~92.9 | [Link](https://huggingface.co/gaotang/RM-R1-Qwen2.5-Instruct-7B) |
| RM-R1-DeepSeek-Distilled-Qwen-7B | 7B | DeepSeek-R1-Distill-Qwen-7B | -- | [Link](https://huggingface.co/gaotang/RM-R1-DeepSeek-Distilled-Qwen-7B) |
| RM-R1-DeepSeek-Distilled-Qwen-14B | 14B | DeepSeek-R1-Distill-Qwen-14B | 88.9 | [Link](https://huggingface.co/gaotang/RM-R1-DeepSeek-Distilled-Qwen-14B) |
| RM-R1-DeepSeek-Distilled-Qwen-32B | 32B | DeepSeek-R1-Distill-Qwen-32B | 90.9 | [Link](https://huggingface.co/gaotang/RM-R1-DeepSeek-Distilled-Qwen-32B) |

**Approach:** Two-stage training: (1) Distillation of 8.7K Chain-of-Rubrics reasoning traces, (2) RL with Verifiable Rewards on 64K preference pairs.
**Output format:** Pairwise comparison. Generates structured analysis with `<type>`, `<solution>`, `<rubric>`, `<eval>`, `<answer>[[A/B]]` tags. Differentiates Reasoning vs. Chat tasks automatically.
**Key strength:** Fully interpretable -- you get the reasoning for why one response is preferred.
**VRAM:** 7B variant needs ~14 GB in fp16. Can fit on a 16 GB GPU.
**GGUF available:** Yes (mradermacher quantizations, 5.5K downloads for i1 variant).

### Reward-Reasoning Model (RRM)

**Release:** May 2025 | **Paper:** [arXiv:2505.14674](https://arxiv.org/abs/2505.14674)

| Model | Params | Base | RewardBench v1 | RewardBench (voting@16) | PPE Overall | HuggingFace |
|-------|--------|------|----------------|------------------------|-------------|-------------|
| RRM-7B | 7B | DeepSeek-R1-Distill-Qwen-7B | 82.2 | 84.8 | 70.3 | [Link](https://huggingface.co/Reward-Reasoning/RRM-7B) |
| RRM-32B | 32B | DeepSeek-R1-Distill-Qwen-32B | 91.2 | 91.9 | 80.7 | [Link](https://huggingface.co/Reward-Reasoning/RRM-32B) |

**Approach:** Frames reward modeling as a reasoning task. Model generates chain-of-thought before outputting preference. Trained with RL in a rule-based reward environment (no supervised reasoning traces needed).
**Output format:** Pairwise comparison via `\boxed{Assistant 1}` or `\boxed{Assistant 2}` after reasoning.
**Key feature:** Supports voting@N for test-time compute scaling. RRM-32B with voting@5 achieves 81.7 on PPE -- SOTA among generative RMs.
**VRAM:** 7B needs ~14 GB, 32B needs ~64 GB.

### RewardAnything

**Release:** Jun 2025 | **Paper:** [arXiv:2506.03637](https://arxiv.org/abs/2506.03637) | **License:** Apache-2.0

| Model | Params | Base | HuggingFace |
|-------|--------|------|-------------|
| RewardAnything-8B-v1 | 8B | Qwen3-8B | [Link](https://huggingface.co/WisdomShell/RewardAnything-8B-v1) |

**Unique feature:** Principle-following reward model. You specify evaluation criteria in natural language at inference time. Model adapts to arbitrary evaluation rubrics without retraining.
**Usage:** Has its own Python package (`pip install rewardanything`). Supports local inference, vLLM deployment, and HuggingFace integration. Provides `.judge()` API that returns scores, ranking, and reasoning for N responses.
**Output format:** Generative -- produces reasoning and scores for each response given a principle.
**Key strength:** You can define "code correctness" as a principle, or "test coverage completeness", or any other criteria dynamically. Extremely flexible for cascade gating.
**VRAM:** ~16 GB in fp16.

### GRAM (Generative Reward Model)

**Release:** Jun 2025 | **License:** Apache-2.0

| Model | Params | Base | JudgeBench Avg | HuggingFace |
|-------|--------|------|----------------|-------------|
| GRAM-Qwen3-1.7B-RewardModel | 1.7B | Qwen3-1.7B | 65.4 | [Link](https://huggingface.co/NiuTrans/GRAM-Qwen3-1.7B-RewardModel) |
| GRAM-Qwen3-4B-RewardModel | 4B | Qwen3-4B | 65.9 | [Link](https://huggingface.co/NiuTrans/GRAM-Qwen3-4B-RewardModel) |
| GRAM-Qwen3-8B-RewardModel | 8B | Qwen3-8B | 67.8 | [Link](https://huggingface.co/NiuTrans/GRAM-Qwen3-8B-RewardModel) |
| GRAM-Qwen3-14B-RewardModel | 14B | Qwen3-14B | 71.4 | [Link](https://huggingface.co/NiuTrans/GRAM-Qwen3-14B-RewardModel) |
| GRAM-LLaMA3.2-3B-RewardModel | 3B | LLaMA3.2-3B | 69.9 | [Link](https://huggingface.co/NiuTrans/GRAM-LLaMA3.2-3B-RewardModel) |
| GRAM-RR-LLaMA-3.1-8B-RewardModel | 8B | LLaMA-3.1-8B | -- | [Link](https://huggingface.co/wangclnlp/GRAM-RR-LLaMA-3.1-8B-RewardModel) |

**Approach:** Combines generative and discriminative training. Pre-trains on unlabeled data, then fine-tunes with label smoothing and regularized ranking loss. Claims to be usable as a foundation reward model -- directly applicable to new tasks without per-task fine-tuning.
**Output format:** Generative pairwise comparison ("A" or "B").
**Key insight:** GRAM-Qwen3-1.7B (65.4 JudgeBench) outperforms nvidia/Llama-3.1-Nemotron-70B-Reward (67.2) when considering the 40x parameter efficiency.

### RISE-Judge

**Release:** Feb 2025 | **Paper:** [arXiv:2502.11689](https://arxiv.org/abs/2502.11689)

| Model | Params | Base | RewardBench Avg | HuggingFace |
|-------|--------|------|-----------------|-------------|
| RISE-Judge-Qwen2.5-7B | 7B | Qwen2.5-7B | >86.8 (claimed SOTA) | [Link](https://huggingface.co/R-I-S-E/RISE-Judge-Qwen2.5-7B) |
| RISE-Judge-Qwen2.5-32B | 32B | Qwen2.5-32B | -- | [Link](https://huggingface.co/R-I-S-E/RISE-Judge-Qwen2.5-32B) |

**Approach:** Two-stage SFT warm-up + DPO enhancement. Uses GPT-4o-generated step-by-step judgments for training. Chinese-language prompt template (but works for English content).
**Note:** Prompt template is in Chinese, which may introduce bias for English code evaluation tasks. Low download count (19) suggests limited community validation.

### Prometheus v2

**Release:** Nov 2024 | **Paper:** [arXiv:2405.01535](https://arxiv.org/abs/2405.01535) | **License:** Apache-2.0

| Model | Params | HuggingFace |
|-------|--------|-------------|
| prometheus-7b-v2.0 | 7B | [Link](https://huggingface.co/prometheus-eval/prometheus-7b-v2.0) |
| prometheus-8x7b-v2.0 | 47B (MoE) | [Link](https://huggingface.co/prometheus-eval/prometheus-8x7b-v2.0) |

**Approach:** LLM-as-a-Judge with rubric-based evaluation. Can do both pointwise scoring (1-5) and pairwise comparison. Designed specifically as an open-source alternative to GPT-4 for evaluation.
**Downloads:** 36K (7B) -- the most downloaded generative judge model.
**Note:** Pre-dates our window but included as a reference since it's the most established open-source judge model.

---

## 3. Process Reward Models (PRM)

PRMs score individual reasoning steps, not just the final answer. Critical for code verification where intermediate steps matter.

### Skywork-o1-Open-PRM

**Release:** Oct 2024 (last update Mar 2025)

| Model | Params | Base | Math Best-of-N@64 Avg | Code Eval | HuggingFace |
|-------|--------|------|----------------------|-----------|-------------|
| Skywork-o1-Open-PRM-Qwen-2.5-1.5B | 1.5B | Qwen2.5-Math-1.5B-Instruct | 63.9 | HumanEval: +5-10% over majority voting | [Link](https://huggingface.co/Skywork/Skywork-o1-Open-PRM-Qwen-2.5-1.5B) |
| Skywork-o1-Open-PRM-Qwen-2.5-7B | 7B | Qwen2.5-Math-7B-Instruct | 67.3 | HumanEval: competitive with 72B ORM | [Link](https://huggingface.co/Skywork/Skywork-o1-Open-PRM-Qwen-2.5-7B) |

**Usage:** Scores each step of a reasoning chain. Average step score used for Best-of-N selection. Evaluated on code tasks (HumanEval, MBPP, LiveCodeBench) -- making it relevant for code verification.
**Key insight for Athanor:** The 1.5B PRM can verify step-by-step reasoning in code generation, catching logic errors that outcome-only reward models miss. At 1.5B params (~3 GB VRAM), it fits alongside other workloads.

### Other PRMs of Note

| Model | Params | Focus | HuggingFace |
|-------|--------|-------|-------------|
| RLHFlow/Llama3.1-8B-PRM-Deepseek-Data | 8B | Math | [Link](https://huggingface.co/RLHFlow/Llama3.1-8B-PRM-Deepseek-Data) |
| openreasoner/Math-psa (OpenR-MATH-psa-PRM) | 7B | Math | [Link](https://huggingface.co/openreasoner/Math-psa) |
| Qwen/Qwen2.5-Math-RM-72B | 72B | Math ORM | [Link](https://huggingface.co/Qwen/Qwen2.5-Math-RM-72B) |

---

## 4. Multi-Objective / Specialized Reward Models

### DeepSeek-GRM (Generative Reward Model)

**Release:** Sep 2025 | **License:** Gemma (27B), Other (16B)

| Model | Params | RewardBench v1 | HuggingFace |
|-------|--------|----------------|-------------|
| DeepSeek-GRM-27B | 27B | 86.0 (88.5 w/ MetaRM) | [Link](https://huggingface.co/BBQGOD/DeepSeek-GRM-27B) |
| DeepSeek-GRM-16B | 16B | -- | [Link](https://huggingface.co/BBQGOD/DeepSeek-GRM-16B) |

**Key feature:** Supports MetaRM -- a meta-reward model that re-evaluates and aggregates multiple reward assessments. With MetaRM, the 27B model jumps from 86.0 to 88.5 on RewardBench v1.

### RLAnything (Feb 2026)

**Release:** Feb 2026 | **Paper:** [arXiv:2602.02488](https://arxiv.org/abs/2602.02488) | **License:** MIT

| Model | Params | Focus | HuggingFace |
|-------|--------|-------|-------------|
| RLAnything-OS-Reward-8B | 8B | OS/Agent tasks | [Link](https://huggingface.co/Gen-Verse/RLAnything-OS-Reward-8B) |
| RLAnything-Alf-Reward-14B | 14B | ALFWorld agent tasks | [Link](https://huggingface.co/Gen-Verse/RLAnything-Alf-Reward-14B) |
| RLAnything-Coder-7B | 7B | Code generation | [Link](https://huggingface.co/Gen-Verse/RLAnything-Coder-7B) |

**Approach:** RL framework that co-trains environment, policy, and reward model. The reward model is jointly optimized with consistency feedback. The Coder-7B variant is specifically trained for code tasks.
**Key feature:** This is the only model in this survey that was released within the strict 90-day window AND focuses on code. However, it's from a new group with limited community validation (24-36 downloads).
**VRAM:** 7B Coder needs ~14 GB in fp16.

### INF-ORM

**Release:** 2024 | **Params:** 70B (Llama-3.1-70B base)

| Model | Params | RewardBench v1 | PPE | HuggingFace |
|-------|--------|----------------|-----|-------------|
| INF-ORM-Llama3.1-70B | 70B | 95.1 | 64.2/64.4 (Pref/Corr) | [Link](https://huggingface.co/infly/INF-ORM-Llama3.1-70B) |

**Note:** Very strong performance but 70B is impractical for Athanor co-location.

### Co-rewarding Models

**Release:** 2025 | **Org:** TMLR-Group-HF

Multiple variants (Qwen3-4B, Qwen3-8B, Qwen2.5-7B) trained with co-rewarding framework for math. Available as GGUF quantizations. Primarily math-focused, not code.

### R1-Reward

**Release:** May 2025 | **License:** Apache-2.0

| Model | Params | HuggingFace |
|-------|--------|-------------|
| R1-Reward | Unknown | [Link](https://huggingface.co/yifanzhang114/R1-Reward) |

Limited documentation. GGUF available (102 downloads for i1 variant).

### SelfRewarded-R1

**Release:** Aug 2025 | **License:** Apache-2.0

| Model | Params | HuggingFace |
|-------|--------|-------------|
| SelfRewarded-R1-7B | 7B | [Link](https://huggingface.co/LMMs-Lab-Turtle/SelfRewarded-R1-7B) |

Self-rewarding paradigm where the model evaluates its own outputs.

---

## 5. Code-Specific Models

Models specifically designed for code quality assessment.

### RLAnything-Coder-7B
See Section 4. The only dedicated code reward model from Feb 2026. MIT license, 7B params.

### ArmoRM Code Objectives
ArmoRM-Llama3-8B-v0.1 includes 5 code-specific reward dimensions:
- `code-complexity`
- `code-style`
- `code-explanation`
- `code-instruction-following`
- `code-readability`

These can be extracted and weighted independently for code-specific evaluation.

### SecCoderX Reasoning Vulnerability Detection Reward Model
**Release:** Feb 2026 | Very niche -- focused on security vulnerability detection in code.
[Link](https://huggingface.co/SecCoderX/SecCoderX_Reasoning_Vulnerability_Detection_Reward_Model) | 9 downloads, minimal documentation.

### Using General Reward Models for Code
The Skywork-Reward-V2 benchmark includes RM-Bench Code evaluation:
- Skywork-Reward-V2-Qwen3-0.6B: Code score not separately reported but contributes to 74.4 RM-Bench avg
- Skywork-Reward-V2-Llama-3.1-8B: 92.8 RM-Bench overall
- NVIDIA Qwen-3-Nemotron-32B-Reward: 70.2 Code on RM-Bench

**Practical note:** For code quality gating in a cascade, you do not necessarily need a code-specific reward model. A general reward model evaluating "prompt: write function X" + "response: [code]" will score code quality effectively because the training data includes code preference pairs.

---

## 6. Safety-Specific Models

### Safe-Reward-Qwen3-1.7B
**Release:** 2025 | **License:** Apache-2.0 | **Base:** Qwen3-1.7B
[Link](https://huggingface.co/puwaer/Safe-Reward-Qwen3-1.7B) | 256 downloads

**Focus:** Safety quality evaluation in EN, ZH, and JP. Trained on cvalues_rlhf datasets. Specifically evaluates whether responses properly refuse harmful requests.
**VRAM:** ~3.4 GB in fp16.

### PKU-Alignment Beaver Models
- beaver-7b-v1.0-reward (6K downloads)
- beaver-7b-v2.0-reward (217 downloads)
- beaver-7b-unified-reward (557 downloads)

Focus on safety alignment. Older models but well-established.

---

## 7. Small Models for Cascade Gating

The critical question for Athanor: what can run alongside the generation model without impacting it?

### Tier 1: CPU-Runnable (< 2 GB, fast enough on EPYC 7663)

| Model | Params | VRAM/RAM | RewardBench v1 | Throughput Est. | Best For |
|-------|--------|----------|----------------|-----------------|----------|
| **Skywork-Reward-V2-Qwen3-0.6B** | 0.6B | 1.2 GB | 85.2 | ~50ms/eval on CPU | Primary cascade gate |

This is the clear winner. 0.6B params in bf16 is 1.2 GB. On the EPYC 7663 (56 cores), inference would take roughly 50-100ms per evaluation. On GPU, it would be nearly instant.

### Tier 2: Fits on GPU 4 with existing workloads (< 4 GB)

| Model | Params | VRAM | RewardBench v1 | Best For |
|-------|--------|------|----------------|----------|
| **Skywork-Reward-V2-Qwen3-1.7B** | 1.7B | 3.4 GB | 90.3 | Higher-confidence cascade gate |
| InternLM2-1.8B-Reward | 1.8B | 3.6 GB | 80.6 | Multilingual evaluation |
| Skywork-Reward-V2-Llama-3.2-1B | 1B | 2 GB | 89.9 | Alternative to Qwen3 variant |
| Skywork-o1-Open-PRM-Qwen-2.5-1.5B | 1.5B | 3 GB | -- (PRM) | Step-by-step code verification |

GPU 4 currently uses 8.8 GB / 16.3 GB (vLLM-embedding 0.40 mem + wyoming-whisper float16 + Speaches lazy). That leaves ~7.5 GB free, easily fitting any of these.

### Tier 3: Dedicated GPU required (8-16 GB)

| Model | Params | VRAM | RewardBench v1 | Best For |
|-------|--------|------|----------------|----------|
| GRM-gemma2-2B-rewardmodel-ft | 2B | 4 GB | 88.4 | Sub-3B SOTA (older) |
| Skywork-Reward-V2-Qwen3-4B | 4B | 8 GB | 93.4 | High accuracy |
| GRM-Llama3.2-3B-rewardmodel-ft | 3B | 6 GB | 90.9 | Good balance |
| ArmoRM-Llama3-8B-v0.1 | 8B | 16 GB | 89.0 | Multi-objective code scoring |
| Skywork-Reward-V2-Qwen3-8B | 8B | 16 GB | 93.7 | Near-SOTA |

---

## 8. Benchmark Reference

### RewardBench v1 Scores (selected, from Skywork-Reward-V2 paper)

| Category | Model | Score |
|----------|-------|-------|
| BT | Skywork-Reward-V2-Llama-3.1-8B-40M | **97.8** |
| BT | Skywork-Reward-V2-Llama-3.1-8B | 96.4 |
| BT | INF-ORM-Llama3.1-70B | 95.1 |
| BT | LDL-Reward-Gemma-2-27B-v0.1 | 95.0 |
| BT | Skywork-Reward-Gemma-2-27B-v0.2 | 94.3 |
| BT | Skywork-Reward-V2-Qwen3-8B | 93.7 |
| BT | Skywork-Reward-V2-Qwen3-4B | 93.4 |
| BT | Skywork-Reward-V2-Llama-3.2-3B | 93.0 |
| Generative | EvalPlanner (Llama-3.3-70B) | 93.8 |
| Generative | RM-R1-Qwen-Instruct-32B | 92.9 |
| BT | GRM-Llama3.2-3B-rewardmodel-ft | 90.9 |
| Generative | RM-R1-DeepSeek-Distill-Qwen-32B | 90.9 |
| BT | Skywork-Reward-V2-Qwen3-1.7B | 90.3 |
| BT | ArmoRM-Llama3-8B-v0.1 | 89.0 |
| BT | GRM-gemma2-2B-rewardmodel-ft | 88.4 |
| BT | Skywork-Reward-V2-Qwen3-0.6B | **85.2** (0.6B!) |

### JudgeBench Scores (from GRAM paper)

| Model | Params | JudgeBench Avg |
|-------|--------|----------------|
| GRAM-Qwen3-14B-RewardModel | 14B | 71.4 |
| GRAM-LLaMA3.2-3B-RewardModel | 3B | 69.9 |
| GRAM-Qwen3-8B-RewardModel | 8B | 67.8 |
| nvidia/Llama-3.1-Nemotron-70B-Reward | 70B | 67.2 |
| GRAM-Qwen3-4B-RewardModel | 4B | 65.9 |
| GRAM-Qwen3-1.7B-RewardModel | 1.7B | 65.4 |

---

## 9. Athanor Integration Analysis

### Architecture: Two-Stage Cascade Gate

```
User request
    |
    v
[Local Qwen3-32B-AWQ generates code] (GPUs 0-3, TP=4)
    |
    v
[Stage 1: Skywork-Reward-V2-Qwen3-0.6B] (CPU or GPU 4)
    |-- Score > threshold_high --> Accept, return to user
    |-- Score < threshold_low  --> Escalate to Claude
    |-- Score in between       --> Stage 2
    |
    v
[Stage 2: ArmoRM or RewardAnything] (GPU 4 or Node 2)
    |-- Code-specific sub-scores analyzed
    |-- Accept / Reject / Escalate
```

### Deployment Options

**Option A: Minimal (recommended first)**
- Deploy Skywork-Reward-V2-Qwen3-0.6B on CPU (VAULT or Node 1)
- Uses `AutoModelForSequenceClassification`, standard transformers
- ~50ms per evaluation on EPYC
- Zero GPU impact

**Option B: GPU Co-location**
- Deploy Skywork-Reward-V2-Qwen3-1.7B on GPU 4 alongside embedding
- GPU 4 current usage: 8.8 GB / 16.3 GB
- Model needs 3.4 GB --> fits (total ~12.2 GB)
- Near-instant inference

**Option C: Multi-objective (advanced)**
- Deploy ArmoRM-Llama3-8B-v0.1 on Node 2's 5060 Ti (16 GB)
- Gets 19-dimensional reward including 5 code-specific dimensions
- Can build custom gating logic per objective

**Option D: Principle-following (most flexible)**
- Deploy RewardAnything-8B-v1 via vLLM on Node 2
- Define evaluation principles per task type
- Generative -- slower but fully interpretable

### Serving Method

For BT reward models, SGLang supports reward model serving with `--is-embedding` flag (documented in Skywork-Reward-V2 README). This means the reward model can be served as an API endpoint, just like the generation model.

Alternatively, a simple Python service wrapping `transformers` would work for low-throughput cascade gating (evaluating one response at a time).

### Estimated VRAM Budget

| GPU | Current Usage | Available | Can Fit |
|-----|--------------|-----------|---------|
| Node 1 GPU 0-3 | vLLM TP=4 (Qwen3-32B-AWQ) | 0 | Nothing (dedicated) |
| Node 1 GPU 4 | embedding + whisper + speaches = 8.8 GB | ~7.5 GB | 0.6B (1.2 GB), 1.7B (3.4 GB), 1.5B PRM (3 GB) |
| Node 2 GPU 0 | vLLM (active) | Varies | Schedule-dependent |
| Node 2 GPU 1 | ComfyUI (on-demand) | 16 GB when idle | Any 8B model |
| VAULT CPU | 128 GB DDR5 | Ample | 0.6B on CPU (~50ms) |

---

## 10. Recommendation

### Phase 1: Immediate (this week)

Deploy **Skywork-Reward-V2-Qwen3-0.6B** as the primary cascade gate.

Rationale:
- 85.2 RewardBench v1 -- nearly matches the previous 27B SOTA
- 1.2 GB VRAM -- runs on CPU or trivially on GPU 4
- Apache-2.0 license -- no restrictions
- Standard transformers API -- no custom code needed
- Qwen3 base model -- same family as our generation model, likely better calibration
- 26M training pairs -- the most extensively trained reward model family

### Phase 2: After validation

Add **Skywork-Reward-V2-Qwen3-1.7B** as the "high-confidence" tier.
- 90.3 RewardBench v1 -- significant jump from 0.6B
- 3.4 GB VRAM -- still fits on GPU 4
- Use when Stage 1 score is ambiguous

### Phase 3: Code-specific evaluation

Add **ArmoRM-Llama3-8B-v0.1** for code-specific multi-objective scoring.
- 5 code-specific reward dimensions
- Requires dedicated GPU time (16 GB)
- Deploy on Node 2 GPU 1 when ComfyUI is idle

### Not Recommended

- **NVIDIA Nemotron 32B/70B Reward**: Too large for co-location, no significant accuracy advantage over smaller Skywork V2 models for our use case.
- **Generative judge models (RRM, RM-R1, GRAM) as primary gate**: Too slow. 7B+ generative models need seconds per evaluation. Reserve for detailed analysis when escalation decision is borderline.
- **RLAnything-Coder-7B**: Too new (Feb 2026), minimal community validation (24 downloads), and 7B is overkill for gating.

### Confidence Assessment

**High confidence** in Skywork-Reward-V2 recommendation:
- Validated across 7 benchmarks
- 8 model sizes available for scaling
- Active community (31K downloads for Llama variant)
- Paper published and peer-reviewed

**Medium confidence** in cascade architecture:
- Threshold tuning will require empirical testing with real code generation outputs
- May need domain-specific calibration (reward model trained on general preference data, not specifically code review data)

**Open questions:**
- What reward score distribution does our Qwen3-32B-AWQ generation model produce? Need to collect a calibration dataset.
- Is a single scalar score sufficient for cascade gating, or do we need ArmoRM's multi-objective scores?
- Should the reward model evaluate the code in isolation, or with the original prompt + test cases?

---

## Sources

- Skywork-Reward-V2 paper: https://arxiv.org/abs/2507.01352
- Skywork-Reward-V2 models: https://huggingface.co/collections/Skywork/skywork-reward-v2-685cc86ce5d9c9e4be500c84
- NVIDIA Qwen-3-Nemotron-32B-Reward: https://huggingface.co/nvidia/Qwen-3-Nemotron-32B-Reward
- ArmoRM paper: https://arxiv.org/abs/2406.12845
- ArmoRM model: https://huggingface.co/RLHFlow/ArmoRM-Llama3-8B-v0.1
- GRM paper: https://arxiv.org/abs/2406.10216
- RM-R1 paper: https://arxiv.org/abs/2505.02387
- RRM paper: https://arxiv.org/abs/2505.14674
- RewardAnything paper: https://arxiv.org/abs/2506.03637
- RewardAnything model: https://huggingface.co/WisdomShell/RewardAnything-8B-v1
- GRAM models: https://huggingface.co/NiuTrans/GRAM-Qwen3-1.7B-RewardModel
- RLAnything paper: https://arxiv.org/abs/2602.02488
- RLAnything models: https://huggingface.co/Gen-Verse/RLAnything-OS-Reward-8B
- InternLM2 Reward: https://huggingface.co/internlm/internlm2-1_8b-reward
- InternLM2 paper: https://arxiv.org/abs/2403.17297
- Skywork PRM: https://huggingface.co/Skywork/Skywork-o1-Open-PRM-Qwen-2.5-1.5B
- DeepSeek-GRM: https://huggingface.co/BBQGOD/DeepSeek-GRM-27B
- RISE-Judge paper: https://arxiv.org/abs/2502.11689
- Prometheus v2: https://huggingface.co/prometheus-eval/prometheus-7b-v2.0
- RewardBench: https://huggingface.co/spaces/allenai/reward-bench
- HelpSteer3: https://huggingface.co/datasets/nvidia/HelpSteer3
- Safe-Reward-Qwen3-1.7B: https://huggingface.co/puwaer/Safe-Reward-Qwen3-1.7B
- SecCoderX: https://huggingface.co/SecCoderX/SecCoderX_Reasoning_Vulnerability_Detection_Reward_Model

All HuggingFace model data verified via API on 2026-02-25.
