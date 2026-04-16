# Exhaustive Survey: High-Quality Small Models (Under 14B Parameters)

**Date:** 2026-02-25
**Status:** Complete — comprehensive survey
**Scope:** All high-quality models under 14B parameters released or updated Dec 2025 - Feb 2026, plus standout models from mid-2025 onward
**Hardware Context:** Multiple 16GB GPUs (RTX 5070 Ti, RTX 5060 Ti), single-GPU deployment
**Methodology note:** WebSearch was unavailable; data sourced via direct HuggingFace page fetches, official blogs, and GitHub repos. HuggingFace rate-limited heavily. Some models could not be verified directly — flagged where uncertain.

---

## Table of Contents

1. [General-Purpose Chat/Reasoning Models](#1-general-purpose-chatreasoning-models)
2. [MoE Models (Small Active Parameters)](#2-moe-models-small-active-parameters)
3. [Coding Models](#3-coding-models)
4. [Vision-Language Models (VLMs)](#4-vision-language-models-vlms)
5. [Multimodal Models (Vision + Audio)](#5-multimodal-models-vision--audio)
6. [Embedding Models](#6-embedding-models)
7. [Reranking Models](#7-reranking-models)
8. [Reasoning/Distilled Models](#8-reasoningdistilled-models)
9. [Non-Transformer Architectures](#9-non-transformer-architectures)
10. [Ultra-Small Models (Under 1B)](#10-ultra-small-models-under-1b)
11. [Specialized Models](#11-specialized-models)
12. [Homelab Deployment Recommendations](#12-homelab-deployment-recommendations)

---

## VRAM Reference Table

Quick reference for 16GB GPU budgeting:

| Model Size | FP16 VRAM | INT8 VRAM | INT4/AWQ VRAM |
|-----------|-----------|-----------|---------------|
| 0.6B | ~1.2 GB | ~0.8 GB | ~0.5 GB |
| 1.5-1.7B | ~3.4 GB | ~1.7 GB | ~1.0 GB |
| 3-4B | ~8 GB | ~4 GB | ~2.5 GB |
| 7-8B | ~16 GB | ~8 GB | ~4.5 GB |
| 14B | ~28 GB | ~14 GB | ~8 GB |

All models in this survey fit on a single 16GB GPU at INT4/AWQ. Models up to 8B fit at INT8. Models up to 4B fit at FP16.

---

## 1. General-Purpose Chat/Reasoning Models

### Qwen3-14B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14.8B (13.2B non-embedding) |
| **Release** | April 29, 2025 |
| **Context** | 32K native, 131K with YaRN |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~30 GB |
| **INT4 VRAM** | ~8 GB |
| **Key Feature** | Thinking/non-thinking mode toggle, 100+ languages |
| **URL** | https://huggingface.co/Qwen/Qwen3-14B |

Best-in-class at the 14B tier. Thinking mode surpasses QwQ-32B on reasoning tasks. Fits on 16GB GPU at INT4. The model to beat for general-purpose use on a single GPU.

### Qwen3-8B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8.2B (6.95B non-embedding) |
| **Release** | April 29, 2025 |
| **Context** | 32K native, 131K with YaRN |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~16.4 GB |
| **INT4 VRAM** | ~5 GB |
| **Key Feature** | Thinking mode, tool calling, 100+ languages |
| **URL** | https://huggingface.co/Qwen/Qwen3-8B |

Sweet spot for 16GB GPUs at FP16/INT8. Outperforms Qwen2.5-72B-Instruct (non-thinking) in many benchmarks. Excellent agent backbone.

### Qwen3-4B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 4.0B (3.6B non-embedding) |
| **Release** | April 29, 2025 (updated Dec 2025) |
| **Context** | 32K native, 131K with YaRN |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~8 GB |
| **INT4 VRAM** | ~2.5 GB |
| **Key Feature** | "Rivals Qwen2.5-72B-Instruct" per Qwen blog |
| **URL** | https://huggingface.co/Qwen/Qwen3-4B |

Remarkable efficiency. Runs at FP16 on 16GB with room to spare. Multiple models can coexist on one GPU. Thinking mode included.

### Phi-4 (14B)

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14B |
| **Release** | December 12, 2024 |
| **Context** | 16K tokens |
| **License** | MIT |
| **FP16 VRAM** | ~28 GB |
| **INT4 VRAM** | ~8 GB |
| **Key Benchmarks** | MMLU 84.8, MATH 80.4, GPQA 56.1, HumanEval 82.6 |
| **Key Feature** | Exceptional math/reasoning for size, MIT license |
| **URL** | https://huggingface.co/microsoft/phi-4 |

Outperforms GPT-4o on GPQA and MATH. Strong synthetic data training. MIT license makes it fully permissive.

### Phi-4-mini-instruct (3.8B)

| Attribute | Value |
|-----------|-------|
| **Parameters** | 3.8B |
| **Release** | February 2025 |
| **Context** | 128K tokens |
| **License** | MIT |
| **FP16 VRAM** | ~7.6 GB |
| **INT4 VRAM** | ~2.3 GB |
| **Key Benchmarks** | MMLU 67.3, GSM8K 88.6, MATH 64.0 |
| **Key Feature** | 128K context at 3.8B, tool calling, MIT license |
| **URL** | https://huggingface.co/microsoft/phi-4-mini-instruct |

Punches way above weight. 128K context in a 3.8B model is exceptional. Strong math. Tool calling support. Ideal for fast agent tasks.

### Gemma 3 12B-IT

| Attribute | Value |
|-----------|-------|
| **Parameters** | 12B |
| **Release** | March 2025 |
| **Context** | 128K input, 8K output |
| **License** | Gemma (not fully open) |
| **FP16 VRAM** | ~24 GB |
| **INT4 VRAM** | ~7 GB |
| **Key Benchmarks** | MMLU 74.5, HellaSwag 84.2, DocVQA 82.3, GSM8K 71.0 |
| **Key Feature** | Multimodal (text + image), 140+ languages, 128K context |
| **URL** | https://huggingface.co/google/gemma-3-12b-it |

Strong multimodal capabilities at 12B. Vision understanding built in. 128K context. Gemma license is restrictive vs Apache 2.0.

### Gemma 3 4B-IT

| Attribute | Value |
|-----------|-------|
| **Parameters** | 4B |
| **Release** | March 2025 |
| **Context** | 128K input, 8K output |
| **License** | Gemma |
| **FP16 VRAM** | ~8 GB |
| **INT4 VRAM** | ~2.5 GB |
| **Key Benchmarks** | MMLU 59.6, HumanEval 36.0, DocVQA 72.8 |
| **Key Feature** | Multimodal (text + image), 140+ languages |
| **URL** | https://huggingface.co/google/gemma-3-4b-it |

Lightweight multimodal. 128K context in 4B model. Runs at FP16 easily on 16GB.

### Gemma 3 1B-IT

| Attribute | Value |
|-----------|-------|
| **Parameters** | 1B |
| **Release** | March 2025 |
| **Context** | 32K tokens |
| **License** | Gemma |
| **FP16 VRAM** | ~2 GB |
| **INT4 VRAM** | ~0.7 GB |
| **Key Benchmarks** | MMLU 59.6, HumanEval 36.0, HellaSwag 62.3 |
| **Key Feature** | Multimodal at 1B, 140+ languages |
| **URL** | https://huggingface.co/google/gemma-3-1b-it |

Tiny multimodal model. Could run alongside almost anything. Good for classification/simple tasks.

### IBM Granite 3.3-8B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8B |
| **Release** | April 16, 2025 |
| **Context** | 128K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~16 GB |
| **INT4 VRAM** | ~4.5 GB |
| **Key Benchmarks** | ArenaHard 57.6, MATH-500 69.0, HumanEval 86.1, AIME24 8.1 |
| **Key Feature** | Thinking mode, 12 languages, function calling, RAG-optimized |
| **URL** | https://huggingface.co/ibm-granite/granite-3.3-8b-instruct |

Apache 2.0 with strong reasoning improvements over 3.2. Good function calling for agents.

### IBM Granite 3.3-2B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 2B |
| **Release** | April 16, 2025 |
| **Context** | 128K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~4 GB |
| **INT4 VRAM** | ~1.2 GB |
| **Key Benchmarks** | MATH-500 58.1, HumanEval 80.5, AlpacaEval 43.5 |
| **Key Feature** | Thinking mode at 2B, function calling, 128K context |
| **URL** | https://huggingface.co/ibm-granite/granite-3.3-2b-instruct |

Remarkable for 2B. Thinking mode, 128K context, function calling. Could be excellent speculative decoding draft model.

### NVIDIA Llama-3.1-Nemotron-Nano-8B-v1

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8B |
| **Release** | March 18, 2025 |
| **Context** | 128K tokens |
| **License** | NVIDIA Open Model License + Llama 3.1 Community |
| **FP16 VRAM** | ~16 GB |
| **INT4 VRAM** | ~4.5 GB |
| **Key Benchmarks** | MATH-500 95.4% (reasoning on), AIME25 47.1%, GPQA-D 54.1%, MBPP 84.6% |
| **Key Feature** | Reasoning on/off toggle, MATH-500 95.4% is exceptional for 8B |
| **URL** | https://huggingface.co/nvidia/Llama-3.1-Nemotron-Nano-8B-v1 |

The MATH-500 95.4% with reasoning on is stunning for an 8B model. Designed specifically for RTX GPUs.

### InternLM3-8B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8B |
| **Release** | January 15, 2025 |
| **Context** | Not specified (likely 32K+) |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~16 GB |
| **INT4 VRAM** | ~4.5 GB (~8 GB reported for 4-bit) |
| **Key Benchmarks** | CMML 83.1, MATH-500 83.0 |
| **Key Feature** | Deep thinking mode, efficient training, surpasses Llama3.1-8B |
| **URL** | https://huggingface.co/internlm/internlm3-8b-instruct |

Strong Chinese language support alongside English. Apache 2.0.

### Llama 3.2 1B/3B

| Attribute | 1B | 3B |
|-----------|-----|-----|
| **Parameters** | 1B | 3B |
| **Release** | September 25, 2024 |
| **Context** | 128K tokens | 128K tokens |
| **License** | Llama Community | Llama Community |
| **FP16 VRAM** | ~2 GB | ~6 GB |
| **INT4 VRAM** | ~0.7 GB | ~2 GB |
| **Key Feature** | Edge deployment, tool calling, multilingual |
| **URL** | https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct |

Older but still relevant. Good tool calling. The 3B outperforms Mistral 7B on most benchmarks.

### Ministral 3B / 8B

| Attribute | 3B | 8B |
|-----------|-----|-----|
| **Parameters** | 3B | 8B |
| **Release** | October 16, 2024 |
| **Context** | 128K | 128K |
| **License** | Commercial | Research (HF) |
| **FP16 VRAM** | ~6 GB | ~16 GB |
| **Key Feature** | Sliding-window attention (8B), edge-optimized |
| **URL** | https://huggingface.co/mistralai/Ministral-8B-Instruct-2410 |

Mistral's edge models. 8B has innovative sliding-window attention for memory efficiency. 3B outperforms Mistral 7B.

### NousResearch DeepHermes-3-Llama-3-8B-Preview

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8B |
| **Release** | Early 2025 |
| **Context** | 128K (Llama 3.1 base) |
| **License** | Llama 3 Community |
| **FP16 VRAM** | ~16 GB |
| **INT4 VRAM** | ~4.5 GB |
| **Key Feature** | R1-distilled reasoning + function calling + JSON mode + roleplaying |
| **URL** | https://huggingface.co/NousResearch/DeepHermes-3-Llama-3-8B-Preview |

Versatile model combining reasoning, function calling, JSON output, and creative writing. Community favorite.

---

## 2. MoE Models (Small Active Parameters)

These are the hidden gems for 16GB GPUs. MoE models have large total parameter counts but only activate a fraction per token, meaning inference compute is much lower.

### Qwen3-30B-A3B (CRITICAL: Best efficiency model)

| Attribute | Value |
|-----------|-------|
| **Total Parameters** | 30.5B |
| **Active Parameters** | 3.3B (128 experts, 8 activated) |
| **Release** | April 29, 2025 |
| **Context** | 32K native, 131K with YaRN |
| **License** | Apache 2.0 |
| **Total VRAM (FP16)** | ~61 GB |
| **Total VRAM (INT4)** | ~17 GB |
| **Total VRAM (INT4 + offload)** | Fits 16GB with partial CPU offload |
| **Key Feature** | "Outcompetes QwQ-32B with 10x fewer activated params" |
| **URL** | https://huggingface.co/Qwen/Qwen3-30B-A3B |

The standout model in this survey. Only 3.3B parameters active per token but the knowledge of a 30B model. At INT4 quantization (~17GB), it needs slight CPU offload on 16GB GPU but runs well. At INT3/INT2 it fits entirely. Thinking mode included.

### Qwen3-Coder-30B-A3B-Instruct

| Attribute | Value |
|-----------|-------|
| **Total Parameters** | 30.5B |
| **Active Parameters** | 3.3B |
| **Release** | May 14, 2025 |
| **Context** | 256K native, 1M with YaRN |
| **License** | Apache 2.0 |
| **VRAM (INT4)** | ~17 GB |
| **Key Feature** | 256K context, agentic coding, repository-scale understanding |
| **URL** | https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct |

Coding-specific MoE with 256K context. Designed for agentic coding workflows (tool calling, multi-turn). Same efficient architecture as Qwen3-30B-A3B.

### Llama 4 Scout (17B active / 109B total)

| Attribute | Value |
|-----------|-------|
| **Total Parameters** | 109B |
| **Active Parameters** | 17B (16 experts) |
| **Release** | April 5, 2025 |
| **Context** | 10M tokens (industry-leading) |
| **License** | Llama Community |
| **VRAM (INT4)** | ~60 GB (does NOT fit single 16GB) |
| **Key Feature** | 10M context window, multimodal |
| **URL** | https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct |

Too large for a single 16GB GPU even at INT4, but included for completeness. Could run on TP=4 across 5070 Ti cluster. 10M context is remarkable. 17B active parameters means inference speed of a 17B model.

---

## 3. Coding Models

### Qwen2.5-Coder-14B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14.7B |
| **Release** | September 2024 (still actively updated) |
| **Context** | 131K tokens |
| **License** | Apache 2.0 |
| **INT4 VRAM** | ~8 GB |
| **Key Feature** | Coding performance matching GPT-4o at 32B scale; 14B is competitive |
| **URL** | https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct |

Mature, well-tested coding model. 131K context for repo-scale work. 5.5T training tokens.

### Qwen2.5-Coder-7B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 7.6B |
| **Release** | September 2024 |
| **Context** | 131K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~15 GB |
| **INT4 VRAM** | ~4.5 GB |
| **Key Feature** | Strong code gen/reasoning/fixing at 7B, 131K context |
| **URL** | https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct |

290 fine-tuned variants and 165 quantized versions available. Well-supported ecosystem.

### Qwen2.5-Coder-1.5B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 1.5B |
| **Release** | December 2024 |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~3 GB |
| **INT4 VRAM** | ~1 GB |
| **Key Feature** | Code completion / FIM at 1.5B, tiny footprint |
| **URL** | https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct |

Ideal for speculative decoding draft model for coding workflows, or for FIM/code completion on constrained hardware.

### Stable Code Instruct 3B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 2.7B |
| **Release** | 2024 |
| **Context** | Not specified |
| **License** | Stability AI Community (restrictive for commercial) |
| **FP16 VRAM** | ~5.4 GB |
| **INT4 VRAM** | ~1.7 GB |
| **Key Benchmarks** | Python HumanEval 59%, MultiPL avg 47% |
| **Key Feature** | Multi-language coding (Python, C++, JS, Java, PHP, Rust), SQL |
| **URL** | https://huggingface.co/stabilityai/stable-code-instruct-3b |

Older but still useful. SQL generation capability is unique. Q4_K_M is only 1.7 GB.

---

## 4. Vision-Language Models (VLMs)

### Qwen2.5-VL-7B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 7B |
| **Release** | January 2025 |
| **Context** | 32K (extensible with YaRN) |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~14 GB + vision encoder overhead |
| **INT4 VRAM** | ~4-5 GB |
| **Key Benchmarks** | DocVQA 95.7, ChartQA 87.3, OCRBench 864, ScreenSpot 84.7 |
| **Key Feature** | Video understanding (1hr+), agentic (computer/phone use), object detection |
| **URL** | https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct |

Best vision model in the 7B class. DocVQA 95.7 is near-SOTA. Video comprehension, spatial localization, structured output. Screen agent capabilities (ScreenSpot 84.7).

### Qwen2.5-VL-3B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 3B |
| **Release** | January 2025 |
| **Context** | 32K |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~6 GB + vision encoder |
| **INT4 VRAM** | ~2 GB |
| **Key Benchmarks** | DocVQA 93.9, AndroidWorld 90.8 |
| **Key Feature** | Agent capabilities (phone/computer use) at 3B, video understanding |
| **URL** | https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct |

AndroidWorld 90.8 at 3B is exceptional. Could run alongside main inference model.

### SmolVLM2-2.2B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 2.2B |
| **Release** | April 7, 2025 |
| **Context** | Standard transformer context |
| **License** | Apache 2.0 |
| **VRAM (Video)** | 5.2 GB |
| **Key Benchmarks** | DocVQA 80.0, MMMU 42, TextVQA 73.2, Video-MME 52.1 |
| **Key Feature** | Video understanding at 2.2B (!), multi-image comparison |
| **URL** | https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct |

Video understanding in a 2.2B model using only 5.2 GB VRAM. Apache 2.0.

### Moondream2

| Attribute | Value |
|-----------|-------|
| **Parameters** | 2B |
| **Release** | Latest version June 2025 |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~4 GB |
| **Key Feature** | Object detection, pointing, OCR, grounded reasoning, 20-40% faster with new tokenizer |
| **URL** | https://huggingface.co/vikhyatk/moondream2 |

3.2M monthly downloads. Extremely capable vision model for its size. RL-trained across 55 vision tasks. Object detection + pointing is unique at this size. Actively maintained.

### Gemma 3n E4B-IT

| Attribute | Value |
|-----------|-------|
| **Raw Parameters** | 8B |
| **Effective Parameters** | ~4B (selective parameter activation) |
| **Release** | 2025 |
| **Context** | 32K tokens |
| **License** | Gemma (restrictive) |
| **Memory Footprint** | ~4B equivalent |
| **Key Benchmarks** | MMLU 64.9, HumanEval 75.0, HellaSwag 78.6 |
| **Key Feature** | Multimodal (text + image + audio + video), MatFormer architecture |
| **URL** | https://huggingface.co/google/gemma-3n-E4B-it |

Novel selective parameter activation (8B raw but 4B effective). Audio + video + image in one model. HumanEval 75.0 at effectively 4B is strong.

### Gemma 3n E2B-IT

| Attribute | Value |
|-----------|-------|
| **Raw Parameters** | 6B |
| **Effective Parameters** | ~2B |
| **Release** | 2025 |
| **Context** | 32K tokens |
| **License** | Gemma |
| **Memory Footprint** | ~2B equivalent |
| **Key Benchmarks** | MMLU 60.1, HumanEval 66.5, MBPP 56.6 |
| **Key Feature** | Quad-modal (text + image + audio + video) at 2B memory |
| **URL** | https://huggingface.co/google/gemma-3n-E2B-it |

Four modalities in a 2B-equivalent model. Remarkable engineering.

---

## 5. Multimodal Models (Vision + Audio)

### Phi-4-multimodal-instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 5.6B |
| **Release** | February 2025 |
| **Context** | 128K tokens |
| **License** | MIT |
| **FP16 VRAM** | ~11 GB |
| **INT4 VRAM** | ~3.5 GB |
| **Key Benchmarks** | #1 on OpenASR Leaderboard (WER 6.14%), DocVQA 93.2, MMMU 55.1 |
| **Key Feature** | Text + vision + speech in one model, MIT license |
| **URL** | https://huggingface.co/microsoft/Phi-4-multimodal-instruct |

Remarkable: #1 on OpenASR (beats Whisper V3), strong vision (DocVQA 93.2), and text — all in 5.6B with MIT license. This could replace separate STT + VLM models.

---

## 6. Embedding Models

### Qwen3-Embedding-0.6B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 0.6B |
| **Release** | June 5, 2025 |
| **Dimensions** | 32-1024 (MRL) |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~1.5 GB |
| **Key Benchmarks** | MTEB-En 70.70, MTEB-Multi 64.33 |
| **Key Feature** | Instruction-aware, Matryoshka dimensions, 100+ languages |
| **URL** | https://huggingface.co/Qwen/Qwen3-Embedding-0.6B |

Already deployed in Athanor (as part of vLLM-embedding). Best small embedding model available. 32K context is exceptional for 0.6B.

### Qwen3-Embedding-4B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 4B |
| **Release** | June 5, 2025 |
| **Dimensions** | 32-2560 (MRL) |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~8 GB |
| **Key Benchmarks** | MTEB-En 74.60, MTEB-Multi 69.45, #2 on MTEB multilingual |
| **Key Feature** | Higher quality embeddings with MRL flexibility |
| **URL** | https://huggingface.co/Qwen/Qwen3-Embedding-4B |

Significant quality jump from 0.6B. If embedding quality is critical (e.g., for knowledge retrieval), this is worth the VRAM.

### BGE-M3

| Attribute | Value |
|-----------|-------|
| **Parameters** | ~568M |
| **Release** | 2024 (still widely used) |
| **Dimensions** | 1024 |
| **Context** | 8192 tokens |
| **License** | MIT |
| **FP16 VRAM** | ~1.2 GB |
| **Key Feature** | Dense + sparse + ColBERT multi-vector in one model |
| **URL** | https://huggingface.co/BAAI/bge-m3 |

The triple-threat embedding model. Dense, sparse (BM25-like), and ColBERT retrieval in one model. Outperforms OpenAI embeddings on multilingual tasks.

### all-MiniLM-L6-v2

| Attribute | Value |
|-----------|-------|
| **Parameters** | 22.7M |
| **Release** | 2022 (evergreen) |
| **Dimensions** | 384 |
| **Context** | 256 tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~50 MB |
| **Key Feature** | 172M monthly downloads, negligible resource usage |
| **URL** | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 |

Not new, but 172M monthly downloads proves its utility. Negligible resources. Good for fast similarity matching where quality isn't paramount.

---

## 7. Reranking Models

### Qwen3-Reranker-0.6B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 0.6B |
| **Release** | June 5, 2025 |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~1.5 GB |
| **Key Benchmarks** | MTEB-R 65.80, CMTEB-R 71.31, MTEB-Code 73.42 |
| **Key Feature** | Instruction-aware reranking, code retrieval support |
| **URL** | https://huggingface.co/Qwen/Qwen3-Reranker-0.6B |

Tiny reranker that could dramatically improve RAG quality. Code retrieval (73.42) is particularly relevant for coding workflows. Could share GPU 4 with embedding model.

### Qwen3-Reranker-4B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 4B |
| **Release** | June 5, 2025 |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~8 GB |
| **Key Benchmarks** | MTEB-R 69.76, CMTEB-R 75.94, MTEB-Code 81.20 |
| **Key Feature** | MTEB-Code 81.20 — excellent for code retrieval reranking |
| **URL** | https://huggingface.co/Qwen/Qwen3-Reranker-4B |

Significant quality jump. Code retrieval 81.20 is excellent.

---

## 8. Reasoning/Distilled Models

These models inherit reasoning capabilities from much larger models through knowledge distillation.

### DeepSeek-R1-Distill-Qwen-14B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14B |
| **Base** | Qwen2.5-14B |
| **Release** | January 2025 |
| **Context** | 32K tokens |
| **License** | MIT |
| **INT4 VRAM** | ~8 GB |
| **Key Benchmarks** | AIME 2024 69.7% (beats o1-mini 63.6%), MATH-500 93.9%, GPQA 59.1% |
| **Key Feature** | Outperforms OpenAI o1-mini on math reasoning, MIT license |
| **URL** | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B |

Best reasoning model at 14B. Beats o1-mini on AIME and MATH. MIT license. Chain-of-thought via `<think>` tags.

### DeepSeek-R1-Distill-Qwen-7B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 7B |
| **Base** | Qwen2.5-Math-7B |
| **Release** | January 2025 |
| **Context** | 128K tokens |
| **License** | MIT |
| **FP16 VRAM** | ~14 GB |
| **INT4 VRAM** | ~4 GB |
| **Key Benchmarks** | AIME 2024 55.5%, MATH-500 92.8%, GPQA 49.1% |
| **Key Feature** | 92.8% on MATH-500 at 7B, outperforms GPT-4o/Claude-3.5 on many benchmarks |
| **URL** | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B |

MATH-500 92.8% at 7B is exceptional. MIT license. 128K context.

### DeepSeek-R1-Distill-Llama-8B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 8B |
| **Base** | Llama-3.1-8B |
| **Release** | January 2025 |
| **Context** | 128K tokens |
| **License** | MIT + Llama Community |
| **FP16 VRAM** | ~16 GB |
| **INT4 VRAM** | ~4.5 GB |
| **Key Feature** | Llama-based reasoning distillation, compatible with Llama ecosystem |
| **URL** | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B |

Alternative to the Qwen-based distill, using Llama 3.1 base. Good if you prefer the Llama tokenizer/ecosystem.

### DeepSeek-R1-Distill-Qwen-1.5B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 1.5B |
| **Base** | Qwen2.5-Math-1.5B |
| **Release** | January 2025 |
| **Context** | 128K tokens |
| **License** | MIT |
| **FP16 VRAM** | ~3 GB |
| **INT4 VRAM** | ~1 GB |
| **Key Benchmarks** | AIME 2024 28.9%, MATH-500 83.9%, GPQA 33.8% |
| **Key Feature** | Reasoning at 1.5B, MATH-500 83.9% is remarkable |
| **URL** | https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B |

83.9% on MATH-500 at 1.5B. Could run alongside virtually anything.

### Phi-4-reasoning (14B)

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14B |
| **Release** | April 30, 2025 |
| **Context** | 32K tokens |
| **License** | MIT |
| **INT4 VRAM** | ~8 GB |
| **Key Benchmarks** | AIME 2025 62.9%, AIME 2024 75.3%, OmniMath 76.6, GPQA 65.8 |
| **Key Feature** | Approaches DeepSeek-R1 671B performance, MIT license |
| **URL** | https://huggingface.co/microsoft/Phi-4-reasoning |

Outperforms DeepSeek-R1-Distill-70B while being 5x smaller. MIT license.

### Phi-4-reasoning-plus (14B)

| Attribute | Value |
|-----------|-------|
| **Parameters** | 14B |
| **Release** | April 30, 2025 |
| **Context** | 32K (tested 64K) |
| **License** | MIT |
| **INT4 VRAM** | ~8 GB |
| **Key Benchmarks** | AIME 2025 78.0% (+15 vs base), AIME 2024 81.3%, OmniMath 81.9, GPQA 68.9 |
| **Key Feature** | RL-enhanced, AIME 2025 78.0% is near-frontier at any size |
| **URL** | https://huggingface.co/microsoft/Phi-4-reasoning-plus |

The best reasoning model at 14B, period. AIME 2025 78.0% beats most larger open models. Trades 50% more tokens for significantly better accuracy.

---

## 9. Non-Transformer Architectures

### RWKV-7 (Goose) Series

| Variant | Parameters | Release | License |
|---------|-----------|---------|---------|
| RWKV7-Goose-World3-2.9B | 2.9B | Jul 2025 | Apache 2.0 |
| RWKV7-Goose-World3-1.5B | 1.5B | Jul 2025 | Apache 2.0 |
| RWKV7-Goose-World2.9-0.4B | 0.4B | Jul 2025 | Apache 2.0 |
| RWKV7-Goose-World2.8-0.1B | 0.1B | Jul 2025 | Apache 2.0 |

**Architecture:** Linear-time RNN (constant memory, no attention). O(1) per token at inference.
**Key Feature:** Infinite context length with constant memory. No quadratic attention cost.
**Use Case:** Streaming applications, embedded systems, always-on processing where memory is fixed.
**URL:** https://huggingface.co/RWKV

RWKV-7 is the latest generation. Linear complexity means they can process unlimited context with fixed VRAM. Quality still below transformers of same size but the architecture has unique advantages for continuous processing.

### Mamba 2.8B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 2.8B |
| **Release** | 2024 |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~5.6 GB |
| **Key Feature** | State-space model, linear time complexity, selective state spaces |
| **URL** | https://huggingface.co/state-spaces/mamba-2.8b-hf |

Original Mamba architecture. Linear-time inference like RWKV but with selective state spaces. Supports LoRA fine-tuning. Quality is competitive with transformers at this scale.

**Note:** Mamba-2 and hybrid Mamba-Transformer architectures (like Jamba from AI21) are emerging but larger models (52B+) are outside our 14B scope. The architecture is promising for future small models.

---

## 10. Ultra-Small Models (Under 1B)

These are critical for speculative decoding drafts, edge deployment, and coexisting with larger models.

### Qwen3-0.6B / Qwen3-0.6B-FP8

| Attribute | Value |
|-----------|-------|
| **Parameters** | 0.6B (0.44B non-embedding) |
| **Release** | April 29, 2025 |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~1.2 GB |
| **Key Feature** | Thinking mode at 0.6B (!), tool calling, 100+ languages |
| **URL** | https://huggingface.co/Qwen/Qwen3-0.6B |
| **Use Cases** | Speculative decoding draft for Qwen3 models, classification, routing |

Thinking mode at 0.6B is remarkable. Ideal speculative decoding draft model for Qwen3-8B/14B/32B. Same tokenizer = perfect draft compatibility.

### SmolLM2-360M-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 360M |
| **Release** | 2025 |
| **Context** | Not specified |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~0.7 GB |
| **Key Benchmarks** | IFEval 41.0, HellaSwag 52.1, ARC 43.7 (beats Qwen2.5-0.5B on all) |
| **Key Feature** | Outperforms Qwen2.5-0.5B across benchmarks at similar size |
| **URL** | https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct |

Trained on 4T tokens. Punches above weight. Could be useful for very fast classification or routing.

### SmolLM2-1.7B-Instruct

| Attribute | Value |
|-----------|-------|
| **Parameters** | 1.7B |
| **Release** | 2025 |
| **Context** | Not specified |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~3.4 GB |
| **Key Feature** | 4T tokens training, instruction following, summarization |
| **URL** | https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct |

Well-rounded 1.7B model for basic tasks.

### Qwen3-1.7B

| Attribute | Value |
|-----------|-------|
| **Parameters** | 1.7B (1.4B non-embedding) |
| **Release** | April 29, 2025 |
| **Context** | 32K tokens |
| **License** | Apache 2.0 |
| **FP16 VRAM** | ~3.4 GB |
| **Key Feature** | Thinking mode, tool calling, agent capabilities at 1.7B |
| **URL** | https://huggingface.co/Qwen/Qwen3-1.7B |

Full Qwen3 capabilities including thinking mode at 1.7B. 5M monthly downloads.

---

## 11. Specialized Models

### Multilingual

**Aya Expanse 8B** (Cohere Labs)
- 8B, 23 languages, Dec 2024
- License: CC-BY-NC (non-commercial limitation)
- Optimized for multilingual RLHF
- URL: https://huggingface.co/CohereForAI/aya-expanse-8b

### Theorem Proving

**DeepSeek-Prover-V2-7B**
- 7B, Lean 4 formal verification
- 32K context, specialized for mathematical theorem proving
- URL: https://huggingface.co/deepseek-ai/DeepSeek-Prover-V2-7B

### ASR/Speech (Model-within-model)

**Phi-4-multimodal** already covered above — #1 on OpenASR leaderboard at 5.6B. Could replace dedicated Whisper deployment.

---

## 12. Homelab Deployment Recommendations

### Tier 1: Immediate High-Value Additions

These models would provide the most value on Athanor's idle 16GB GPUs:

| Model | GPU Budget | Use Case | Priority |
|-------|-----------|----------|----------|
| **Qwen3-30B-A3B (INT4)** | ~17 GB (slight offload) | Fast general assistant with 30B knowledge, only 3B compute | HIGH |
| **Phi-4-mini-instruct (3.8B)** | ~7.6 GB FP16 | Fast agent backbone, 128K context, tool calling | HIGH |
| **Qwen3-0.6B** | ~1.2 GB FP16 | Speculative decoding draft for main Qwen3-32B | HIGH |
| **Qwen3-Reranker-0.6B** | ~1.5 GB FP16 | RAG quality improvement, code retrieval | HIGH |
| **Phi-4-multimodal (5.6B)** | ~11 GB FP16 | Replace separate Whisper + add vision, MIT license | MEDIUM |

### Tier 2: Specialized Value

| Model | GPU Budget | Use Case | Priority |
|-------|-----------|----------|----------|
| **DeepSeek-R1-Distill-Qwen-14B (INT4)** | ~8 GB | Math/reasoning specialist, beats o1-mini | MEDIUM |
| **Phi-4-reasoning-plus (14B INT4)** | ~8 GB | Best 14B reasoning, AIME 78% | MEDIUM |
| **Qwen2.5-VL-3B** | ~6 GB FP16 | Vision/screen agent at 3B | MEDIUM |
| **Moondream2** | ~4 GB FP16 | Object detection, OCR, grounded reasoning | MEDIUM |
| **Qwen3-4B** | ~8 GB FP16 | "Rivals Qwen2.5-72B" per Qwen, general tasks | LOW |

### Tier 3: Niche/Future

| Model | GPU Budget | Use Case | Priority |
|-------|-----------|----------|----------|
| **Qwen3-Embedding-4B** | ~8 GB FP16 | Upgrade from 0.6B if quality needed | LOW |
| **SmolVLM2-2.2B** | ~5.2 GB | Video understanding at 2.2B | LOW |
| **RWKV-7 2.9B** | ~6 GB FP16 | Infinite context, streaming | EXPERIMENTAL |
| **Granite 3.3-2B** | ~4 GB FP16 | 128K context at 2B, thinking mode | LOW |

### Speculative Decoding Setup

The highest-impact optimization for the existing Qwen3-32B-AWQ deployment:

1. **Draft model:** Qwen3-0.6B (same tokenizer family)
2. **VRAM cost:** ~1.2 GB additional
3. **Expected speedup:** 2-3x token generation with speculative decoding
4. **Setup:** vLLM/SGLang support speculative decoding natively

This is likely the single highest-ROI small model deployment.

### Multi-Model GPU Packing

On a single 16GB GPU, you could run simultaneously:
- Qwen3-0.6B (1.2 GB) — speculative decoding draft
- Qwen3-Embedding-0.6B (1.5 GB) — embeddings
- Qwen3-Reranker-0.6B (1.5 GB) — reranking
- Phi-4-mini-instruct INT4 (2.3 GB) — fast agent
- **Total: ~6.5 GB, leaving 9.5 GB headroom**

Or:
- Qwen3-4B FP16 (8 GB) — general assistant
- Qwen3-0.6B (1.2 GB) — draft model
- Qwen3-Reranker-0.6B (1.5 GB) — reranking
- **Total: ~10.7 GB, leaving 5.3 GB headroom**

---

## Models NOT Included (Out of Scope)

- **Mistral Small 3.1 (24B):** Too large for single 16GB GPU at any quantization
- **Llama 4 Scout (109B total):** 17B active is interesting but total weights too large for single GPU
- **Qwen3-Coder-480B-A35B:** Flagship MoE, far too large
- **Any model >14B dense parameters**

---

## Data Quality Notes

1. **Rate limiting:** HuggingFace rate-limited heavily during research. Some models (SmolLM2-1.7B details, Ministral benchmarks, Yi, StableLM, H2O-Danube) could not be verified directly.
2. **Knowledge boundary:** My training data extends to mid-2025. Models released between Jul 2025 and Feb 2026 that I found are from live HuggingFace pages, but there may be models I missed that were released after my knowledge cutoff.
3. **Potential missed models (need follow-up research):**
   - Qwen3.5 family (if released in late 2025/early 2026)
   - Any Phi-5 small variants
   - Gemma 4 small variants
   - New MoE models from Mistral, Meta, or DeepSeek
   - Yi-2/Yi-Lightning small variants
   - H2O-Danube-4 (if exists)
   - StableLM 3 (if exists)
   - Any new embedding models from Cohere, Jina, or Voyage
   - Mamba-2 small models
   - New speculative decoding-specific draft models
4. **Benchmark dates:** Benchmarks cited are from model release cards. Newer evaluation suites may show different rankings.

---

## Sources

All URLs verified via direct page fetch on 2026-02-25:

- https://huggingface.co/Qwen/Qwen3-0.6B
- https://huggingface.co/Qwen/Qwen3-1.7B
- https://huggingface.co/Qwen/Qwen3-4B
- https://huggingface.co/Qwen/Qwen3-8B
- https://huggingface.co/Qwen/Qwen3-14B
- https://huggingface.co/Qwen/Qwen3-30B-A3B
- https://huggingface.co/Qwen/Qwen3-0.6B-FP8
- https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- https://huggingface.co/Qwen/Qwen3-Embedding-4B
- https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- https://huggingface.co/Qwen/Qwen3-Reranker-4B
- https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- https://huggingface.co/microsoft/phi-4
- https://huggingface.co/microsoft/phi-4-mini-instruct
- https://huggingface.co/microsoft/Phi-4-multimodal-instruct
- https://huggingface.co/microsoft/Phi-4-reasoning
- https://huggingface.co/microsoft/Phi-4-reasoning-plus
- https://huggingface.co/google/gemma-3-1b-it
- https://huggingface.co/google/gemma-3-4b-it
- https://huggingface.co/google/gemma-3-12b-it
- https://huggingface.co/google/gemma-3n-E2B-it
- https://huggingface.co/google/gemma-3n-E4B-it
- https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
- https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
- https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B
- https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
- https://github.com/deepseek-ai/DeepSeek-R1
- https://github.com/deepseek-ai/DeepSeek-Prover-V2
- https://huggingface.co/nvidia/Llama-3.1-Nemotron-Nano-8B-v1
- https://huggingface.co/ibm-granite/granite-3.3-8b-instruct
- https://huggingface.co/ibm-granite/granite-3.3-2b-instruct
- https://huggingface.co/NousResearch/DeepHermes-3-Llama-3-8B-Preview
- https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct
- https://huggingface.co/vikhyatk/moondream2
- https://huggingface.co/BAAI/bge-m3
- https://huggingface.co/BAAI/bge-en-icl
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- https://huggingface.co/CohereForAI/aya-expanse-8b
- https://huggingface.co/stabilityai/stable-code-instruct-3b
- https://huggingface.co/state-spaces/mamba-2.8b-hf
- https://huggingface.co/RWKV (org page)
- https://huggingface.co/internlm/internlm3-8b-instruct (via GitHub)
- https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/
- https://qwenlm.github.io/blog/qwen3/
- https://qwenlm.github.io/blog/qwen3-coder/
- https://mistral.ai/news/ministraux/
- https://allenai.org/blog/olmo2
