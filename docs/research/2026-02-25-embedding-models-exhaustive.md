# Exhaustive Embedding, Reranker & RAG Model Survey (Dec 2025 - Feb 2026)

**Date:** 2026-02-25
**Status:** Complete -- exhaustive scan of all major model families
**Supersedes:** 2026-02-16-embedding-rag-models.md (baseline survey)
**Context:** Athanor currently uses Qwen3-Embedding-0.6B (MTEB 70.70, 1024-dim) with Qdrant (1024-dim Cosine). This survey covers every notable model released or updated in the last 90 days.

---

## Methodology

Searched systematically across:
- HuggingFace trending + recently modified (sentence-similarity, feature-extraction, text-ranking pipelines)
- HuggingFace API by organization: Qwen, Jina, BAAI, Alibaba-NLP, Nvidia, Snowflake, Nomic, Mixedbread, LightOn, Tencent, IBM Granite, ContextualAI, ZeroEntropy, Octen, NovaSearch/Stella
- MTEB/MMTEB/RTEB leaderboard standings
- ArXiv papers from the period
- Model-specific documentation pages

---

## Table of Contents

1. [Text Embedding Models](#1-text-embedding-models)
2. [Multimodal Embedding Models](#2-multimodal-embedding-models)
3. [ColBERT / Late Interaction Models](#3-colbert--late-interaction-models)
4. [Code Embedding Models](#4-code-embedding-models)
5. [Reranker / Cross-Encoder Models](#5-reranker--cross-encoder-models)
6. [Multimodal Rerankers](#6-multimodal-rerankers)
7. [Knowledge Graph Embedding Models](#7-knowledge-graph-embedding-models)
8. [Master Comparison Tables](#8-master-comparison-tables)
9. [MTEB Leaderboard Standings (Feb 2026)](#9-mteb-leaderboard-standings-feb-2026)
10. [Recommendations for Athanor](#10-recommendations-for-athanor)
11. [Sources](#11-sources)

---

## 1. Text Embedding Models

### 1.1 jina-embeddings-v5-text-small (NEW -- Feb 18, 2026)

The latest from Jina AI. Distilled from the 3.8B v4 teacher model into sub-1B parameters using task-targeted embedding distillation.

| Spec | Value |
|------|-------|
| Parameters | 677M |
| Dimensions | 1024 (Matryoshka: 32, 64, 128, 256, 512, 768, 1024) |
| Max Sequence Length | 32,768 tokens |
| MMTEB Score | 67.0 |
| MTEB English | 71.7 |
| Retrieval (avg 5 benchmarks) | 63.28 |
| Base Model | Qwen3-0.6B-Base |
| Pooling | Last-token |
| License | **CC BY-NC 4.0** (non-commercial; contact sales@jina.ai for commercial) |
| VRAM (BF16 est.) | ~1.5 GB |
| vLLM Support | Yes (vllm >= 0.15.1) |
| Binary Quantization | "Nearly lossless" via GOR regularization |

Key innovation: Four lightweight LoRA adapters for retrieval, text-matching, classification, and clustering tasks. Each task variant is published as a separate HuggingFace model (e.g., `jina-embeddings-v5-text-small-retrieval`).

**vs Qwen3-Embedding-0.6B:** v5-small scores 67.0 MMTEB vs Qwen3-0.6B's ~64.33 MMTEB (multilingual) and 71.7 MTEB English vs 70.70. However, Jina's model is **CC BY-NC** while Qwen3 is Apache 2.0. The MTEB English advantage of +1.0 is modest.

**FLAG: Dimensions match** current 1024-dim Qdrant setup. However, license is a hard disqualifier for commercial use.

Sources:
- https://huggingface.co/jinaai/jina-embeddings-v5-text-small-retrieval
- https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings
- https://arxiv.org/abs/2602.15547

---

### 1.2 jina-embeddings-v5-text-nano (NEW -- Feb 18, 2026)

The ultra-compact variant for edge/resource-constrained deployments.

| Spec | Value |
|------|-------|
| Parameters | 239M |
| Dimensions | 768 (Matryoshka: 32-768) |
| Max Sequence Length | 8,192 tokens |
| MMTEB Score | 65.5 |
| MTEB English | 71.0 |
| Languages | 15+ |
| License | **CC BY-NC 4.0** |
| VRAM (BF16 est.) | ~0.6 GB |

Achieves "parity with the 494M KaLM at less than half its size."

**FLAG: Max dimension is 768**, not 1024. Would require Qdrant collection recreation or Matryoshka truncation.

Sources:
- https://huggingface.co/jinaai/jina-embeddings-v5-text-nano-retrieval
- https://arxiv.org/abs/2602.15547

---

### 1.3 Octen-Embedding-8B (NEW -- Jan 12, 2026)

LoRA fine-tune of Qwen3-Embedding-8B that claims #1 on the RTEB leaderboard.

| Spec | Value |
|------|-------|
| Parameters | 7.6B |
| Dimensions | 4096 |
| Max Sequence Length | 32,768 tokens |
| RTEB Mean (Task) | 0.8045 (#1) |
| RTEB Mean (Public) | 0.7953 |
| RTEB Mean (Private) | 0.8157 |
| Base Model | Qwen3-Embedding-8B |
| License | Apache 2.0 |
| VRAM (BF16 est.) | ~16 GB |
| Languages | 100+ |

Vertical domain expertise: Legal, Finance, Healthcare, Code. Outperforms voyage-3-large (0.7812) and gemini-embedding-001 (0.7602).

**FLAG: 4096 dimensions** -- incompatible with current 1024-dim collections. Also at 7.6B would consume an entire 16 GB GPU.

Known issue: Must prefix documents with `"- "` to avoid upstream Qwen3 bug.

Sources:
- https://huggingface.co/Octen/Octen-Embedding-8B

---

### 1.4 KaLM-Embedding-Gemma3-12B-2511 (Nov 2025, still #1 MMTEB Feb 2026)

Tencent's model based on Gemma3-12B. Currently holds #1 on MMTEB overall.

| Spec | Value |
|------|-------|
| Parameters | 11.76B |
| Dimensions | 3840 (MRL: 3840, 2048, 1024, 512, 256, 128, 64) |
| Max Sequence Length | 32,768 tokens |
| MMTEB Mean (Task) | 72.32 (#1 overall) |
| MMTEB Mean (TaskType) | 62.51 |
| Retrieval | 75.66 |
| Classification | 77.88 |
| STS | 79.02 |
| Base Model | google/gemma-3-12b-pt |
| License | tencent-kalm-embedding-community (custom) |
| VRAM (BF16 est.) | ~24 GB |

**FLAG: 3840 native dims** but supports MRL down to 1024. Would be compatible with Qdrant at 1024-dim via Matryoshka truncation. However, 11.76B params requires the 4090 (24 GB) or 5090 (32 GB).

Sources:
- https://huggingface.co/tencent/KaLM-Embedding-Gemma3-12B-2511
- https://arxiv.org/abs/2506.20923

---

### 1.5 NVIDIA llama-embed-nemotron-8b (Oct 21, 2025)

NVIDIA's MTEB #1 (by Borda rank) embedding model.

| Spec | Value |
|------|-------|
| Parameters | 7.5B |
| Dimensions | 4096 |
| Max Sequence Length | 32,768 tokens |
| MTEB Mean Score | 69.46 |
| MTEB Borda Rank | #1 (39,573 votes) |
| Retrieval Score | 62.65 |
| Tasks Evaluated | 131 (MMTEB v2) |
| Languages | 1,038 |
| Base Model | Meta-Llama-3.1-8B |
| Architecture | Decoder-only with Latent-Attention pooling |
| License | **NVIDIA customized-nscl-v1** (non-commercial) |
| VRAM (BF16 est.) | ~16 GB |

**FLAG: 4096 dimensions.** Also non-commercial license and large VRAM footprint.

Sources:
- https://huggingface.co/nvidia/llama-embed-nemotron-8b
- https://arxiv.org/abs/2511.07025

---

### 1.6 NVIDIA llama-nemotron-embed-1b-v2 (Updated Feb 4, 2026)

Compact 1B embedding model with Matryoshka support.

| Spec | Value |
|------|-------|
| Parameters | 1B |
| Dimensions | 2048 (Matryoshka: 384, 512, 768, 1024, 2048) |
| Max Sequence Length | 8,192 tokens |
| Languages | 26 languages |
| Base Model | Llama-3.2-1B (bidirectional fine-tune) |
| License | NVIDIA Open Model License (commercial OK) |
| VRAM (BF16 est.) | ~2.5 GB |

**FLAG: Native 2048-dim but supports 1024 via Matryoshka** -- compatible with current Qdrant setup. This is a strong contender for an upgrade path.

Sources:
- https://huggingface.co/nvidia/llama-nemotron-embed-1b-v2

---

### 1.7 IBM Granite-Embedding-English-R2 (Aug 2025, updated Feb 25, 2026)

ModernBERT-based embedding model trained entirely on enterprise-friendly data (no MS-MARCO).

| Spec | Value |
|------|-------|
| Parameters | 149M |
| Dimensions | 768 |
| Max Sequence Length | 8,192 tokens |
| BEIR Retrieval (15) | 53.1 |
| MTEB-v2 (41) | 62.8 |
| CoIR (code, 10) | 55.3 |
| MLDR (long doc) | 40.7 |
| MTRAG (conversational) | 56.7 |
| Architecture | ModernBERT |
| License | Apache 2.0 |
| VRAM (FP16 est.) | ~0.4 GB |

Also has companion: **granite-embedding-small-english-r2** (47M params, 384-dim).

**FLAG: 768 dimensions** -- incompatible with current 1024-dim setup. Competitive for its size but lower quality than Qwen3-Embedding-0.6B.

Sources:
- https://huggingface.co/ibm-granite/granite-embedding-english-r2
- https://arxiv.org/abs/2508.21085

---

### 1.8 Alibaba-NLP/gte-modernbert-base (Late 2024)

ModernBERT-based embedding model from the GTE team. Not new but frequently referenced.

| Spec | Value |
|------|-------|
| Parameters | 149M |
| Dimensions | 768 |
| Max Sequence Length | 8,192 tokens |
| MTEB-en | 64.38 |
| BEIR | 55.33 |
| CoIR (code) | 79.31 |
| LoCo (long context) | 87.57 |
| License | Apache 2.0 |
| VRAM est. | ~0.4 GB |

Strong CoIR (code) performance at only 149M params.

**FLAG: 768 dimensions.**

Sources:
- https://huggingface.co/Alibaba-NLP/gte-modernbert-base

---

### 1.9 Existing Models -- No Updates in Window

The following established models had **no new versions** released Dec 2025 - Feb 2026:

| Model | Last Update | Notes |
|-------|-------------|-------|
| Qwen3-Embedding-0.6B | Jun 2025 | Still current, no v2 |
| Qwen3-Embedding-4B | Jun 2025 | No updates |
| Qwen3-Embedding-8B | Jul 2025 | No updates |
| nomic-embed-text-v2-moe | Feb 2025 | No v3 released |
| EmbeddingGemma-300M | Sep 2025 | No updates |
| BGE-M3 | Jul 2024 | No updates |
| Snowflake Arctic-embed-l-v2.0 | Jul 2025 | No new Arctic Embed release |
| Stella EN 400M v5 | Jan 2025 | No v6 |
| NV-Embed-v2 | May 2024 | Superseded by Nemotron series |
| E5-Mistral-7B | Old | No updates |

---

## 2. Multimodal Embedding Models

### 2.1 Qwen3-VL-Embedding-2B (NEW -- Jan 8, 2026)

First major multimodal embedding model from Qwen. Handles text, images, screenshots, and videos in a unified embedding space.

| Spec | Value |
|------|-------|
| Parameters | 2B |
| Dimensions | Up to 2048 (Matryoshka: 64-2048) |
| Max Sequence Length | 32,768 tokens |
| MMEB-v2 (Overall) | 73.2 |
| MMEB-v2 Image | 75.0 |
| MMEB-v2 Video | 61.9 |
| MMEB-v2 VisDoc | 79.2 |
| MMTEB Mean (Task) | 63.87 |
| MMTEB Retrieval | 78.50 |
| Languages | 30+ |
| Base Model | Qwen3-VL-2B-Instruct |
| License | Apache 2.0 |
| VRAM (BF16 est.) | ~4-5 GB |

**FLAG: Supports 1024-dim via Matryoshka.** This is a game-changer for image+text unified search. Apache 2.0 license.

Sources:
- https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B
- https://arxiv.org/abs/2601.04720

---

### 2.2 Qwen3-VL-Embedding-8B (NEW -- Jan 8, 2026)

Larger variant with stronger multimodal performance.

| Spec | Value |
|------|-------|
| Parameters | 8B |
| Dimensions | Up to 2048 (Matryoshka: 64-2048) |
| Max Sequence Length | 32,768 tokens |
| MMEB-v2 (Overall) | 77.8 |
| MMEB-v2 Image | 80.1 |
| MMEB-v2 Video | 67.1 |
| MMTEB Mean (Task) | 67.88 |
| Languages | 30+ |
| License | Apache 2.0 |
| VRAM (BF16 est.) | ~16-18 GB |

Sources:
- https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B
- https://arxiv.org/abs/2601.04720

---

### 2.3 Jina CLIP v2 (Nov 2024) -- No Update

865M params, 1024-dim, image+text. CC BY-NC 4.0. No v3 release found.

### 2.4 Jina Embeddings v4 (Jun 2025) -- No Recent Update

3.8B params, 2048-dim, multimodal (text+image+code). CC BY-NC 4.0. Superseded by v5 for text-only tasks.

---

## 3. ColBERT / Late Interaction Models

### 3.1 ColBERT-Zero (NEW -- Feb 19, 2026)

The first large-scale fully pre-trained ColBERT model using only public data.

| Spec | Value |
|------|-------|
| Parameters | ~100M |
| Token Embedding Dim | 128 |
| Document Length | 519 tokens |
| Query Length | 39 tokens |
| BEIR nDCG@10 | 55.43 |
| Similarity | MaxSim |
| Architecture | ModernBERT base |
| License | Apache 2.0 |
| Training | 3-phase: unsupervised + supervised + KD |
| VRAM est. | ~0.3 GB |

Three-phase training pipeline with unsupervised contrastive pre-training, supervised fine-tuning, and knowledge distillation. Achieves BEIR 55.43 using only public data, overcoming a 2.4-point data quality gap vs models trained on proprietary data.

Efficient variant: **ModernColBERT-embed-base** (supervised + KD only) achieves 55.12 at 10x lower training cost.

Sources:
- https://huggingface.co/lightonai/ColBERT-Zero
- https://arxiv.org/abs/2602.16609

---

### 3.2 GTE-ModernColBERT-v1 (NEW -- Jan 21, 2026)

ColBERT model based on Alibaba's gte-modernbert-base.

| Spec | Value |
|------|-------|
| Parameters | ~149M (ModernBERT-base) |
| Token Embedding Dim | 128 |
| Default Document Length | 300 tokens (generalizes to 32K+) |
| Query Length | 32 tokens |
| BEIR nDCG@10 | 54.67 |
| LongEmbed | 88.39 (SOTA) |
| Nano BEIR NDCG@10 | 0.6758 |
| Architecture | ModernBERT |
| License | Apache 2.0 |
| VRAM est. | ~0.4 GB |

Exceptional long-context performance: 88.39 on LongEmbed benchmark, ~10 points above previous SOTA (voyage-multilingual-2 at 79.17).

Sources:
- https://huggingface.co/lightonai/GTE-ModernColBERT-v1

---

### 3.3 mxbai-edge-colbert-v0-17m (Oct 2025)

Ultra-lightweight edge ColBERT from Mixedbread.

| Spec | Value |
|------|-------|
| Parameters | 17M |
| Token Embedding Dim | 48 |
| Max Token Length | 32,000 |
| BEIR Average | 0.490 (best in <25M class) |
| Architecture | Ettin-17M (ModernBERT) |
| License | Apache 2.0 |

Also available: **mxbai-edge-colbert-v0-32m** (32M params, better performance).

Sources:
- https://huggingface.co/mixedbread-ai/mxbai-edge-colbert-v0-17m
- https://arxiv.org/abs/2510.14880

---

## 4. Code Embedding Models

### 4.1 LateOn-Code (NEW -- Feb 2026)

State-of-the-art code retrieval model using ColBERT late interaction on ModernBERT.

| Spec | Value |
|------|-------|
| Parameters | 149M |
| Token Embedding Dim | 128 |
| Document Length | 2,048 tokens |
| Query Length | 256 tokens |
| MTEB Code v1 Average | 74.12 |
| CodeSearchNet | 90.40 |
| COIR CSNet | 86.57 |
| CosQA | 37.08 |
| Architecture | ColBERT on ModernBERT-base |
| License | Apache 2.0 |
| VRAM est. | ~0.4 GB |

Trained on 20+ code-specific datasets. Approaches C2LLM-0.5B (75.46) while being much smaller. Integrates with ColGrep for semantic code search and Claude Code.

Sources:
- https://huggingface.co/lightonai/LateOn-Code

---

### 4.2 LateOn-Code-edge (NEW -- Feb 2026)

The ultra-compact variant.

| Spec | Value |
|------|-------|
| Parameters | 17M |
| Token Embedding Dim | 48 |
| MTEB Code v1 Average | 66.64 |
| CodeSearchNet NDCG@10 | 0.8771 |
| License | Apache 2.0 |

Outperforms granite-embedding-small-english-r2 (47M, 55.84) while being nearly 3x smaller.

Sources:
- https://huggingface.co/lightonai/LateOn-Code-edge

---

### 4.3 Jina Code Embeddings 0.5b (Sep 2025)

| Spec | Value |
|------|-------|
| Parameters | 494M |
| Dimensions | 896 |
| Max Sequence Length | 32,768 tokens |
| CoIR | 73.94 (per jina-reranker-v3 comparison table) |
| License | CC BY-NC 4.0 (assumed, Jina standard) |

Sources:
- https://huggingface.co/jinaai/jina-code-embeddings-0.5b

---

### 4.4 Jina Code Embeddings 1.5b (Sep 2025)

| Spec | Value |
|------|-------|
| Parameters | 1.5B |
| Dimensions | 1536 |
| Max Sequence Length | 32,768 tokens |
| License | CC BY-NC 4.0 (assumed) |

Sources:
- https://huggingface.co/jinaai/jina-code-embeddings-1.5b

---

## 5. Reranker / Cross-Encoder Models

### 5.1 jina-reranker-v3 (Sep 29, 2025)

Novel "Last but Not Late Interaction" architecture. Processes query and up to 64 documents in a single forward pass.

| Spec | Value |
|------|-------|
| Parameters | 600M |
| Max Context Length | 131,072 tokens |
| Max Documents | 64 simultaneously |
| BEIR | 61.94 |
| MIRACL | 66.83 |
| MKQA | 67.92 |
| CoIR (code) | 70.64 |
| Base Model | Qwen3-0.6B |
| License | **CC BY-NC 4.0** |
| VRAM est. | ~1.5 GB |

Massive improvements over v2: +4.88 BEIR, +14.50 CoIR. The 131K context and 64-document simultaneous reranking is unique.

Sources:
- https://huggingface.co/jinaai/jina-reranker-v3
- https://arxiv.org/abs/2509.25085

---

### 5.2 NVIDIA llama-nemotron-rerank-1b-v2 (Updated Feb 2026)

Cross-encoder reranker fine-tuned from Llama-3.2-1B.

| Spec | Value |
|------|-------|
| Parameters | 1B |
| Max Sequence Length | 8,192 tokens |
| Architecture | Transformer cross-encoder with bidirectional attention |
| Training | Contrastive learning, CrossEntropy loss |
| Languages | 26 languages |
| License | NVIDIA Open Model License (commercial OK) |
| VRAM est. | ~2.5 GB |
| Benchmark (NQ+HotpotQA+FiQA+TechQA) | 73.64% Recall@5 (with embed-1b-v2) |
| MIRACL multilingual | 65.80% Recall@5 |

3.5x smaller than nv-rerankqa-mistral-4b-v3. Pairs naturally with llama-nemotron-embed-1b-v2.

Sources:
- https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2

---

### 5.3 ZeroEntropy zerank-2 (Nov 2025)

Open-source reranker outperforming Cohere rerank-3.5 and Gemini 2.5 Flash.

| Spec | Value |
|------|-------|
| Parameters | 4B |
| Architecture | Qwen3-4B fine-tuned |
| Average NDCG@10 | 0.6714 |
| Biomedical NDCG@10 | 0.7217 |
| Code NDCG@10 | 0.6528 |
| Legal NDCG@10 | 0.6644 |
| License | **CC BY-NC 4.0** |
| VRAM est. | ~8 GB |

Multi-domain excellence using Elo rating system for relevance scoring.

vs Competitors:
- Cohere rerank-3.5: 0.5847 avg
- Gemini 2.5 Flash: 0.5999 avg
- zerank-2: **0.6714 avg**

Sources:
- https://huggingface.co/zeroentropy/zerank-2

---

### 5.4 ContextualAI ctxl-rerank-v2-instruct-multilingual-1b (Dec 22, 2025)

First instruction-following reranker capable of handling retrieval conflicts.

| Spec | Value |
|------|-------|
| Parameters | 1B |
| Max Context Length | 32,768 tokens |
| Languages | 100+ |
| Architecture | Causal Language Model |
| License | **CC-BY-NC-SA-4.0** |
| VRAM est. | ~2.5 GB |
| vLLM Support | Yes (vllm >= 0.8.5) |

Can follow custom instructions like "prioritize recent documents" or "resolve conflicting information." Unique capability among rerankers.

Sources:
- https://huggingface.co/ContextualAI/ctxl-rerank-v2-instruct-multilingual-1b
- https://contextual.ai/blog/rerank-v2

---

### 5.5 mxbai-rerank-base-v2 (Jun 2025)

| Spec | Value |
|------|-------|
| Parameters | ~500M (est.) |
| BEIR Average | 55.57 |
| Multilingual | 28.56 |
| Code Search | 31.73 |
| Latency (A100) | 0.67s |
| License | Apache 2.0 |
| Improvements over v1 | +6.25 BEIR, 3.3x faster |

Also available: **mxbai-rerank-large-v2** (~1.5B, BEIR 61.44).

Sources:
- https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2
- https://arxiv.org/abs/2506.03487

---

### 5.6 IBM granite-embedding-reranker-english-r2 (Sep 2025)

| Spec | Value |
|------|-------|
| Parameters | 149M |
| Max Sequence Length | 8,192 tokens |
| Architecture | ModernBERT cross-encoder |
| License | Apache 2.0 |
| VRAM est. | ~0.4 GB |

Ultra-compact reranker. Pairs with granite-embedding-english-r2 for a complete 149M-param RAG pipeline.

Sources:
- https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2
- https://arxiv.org/abs/2508.21085

---

### 5.7 Existing Rerankers -- No Updates in Window

| Model | Params | MTEB-R | License | Notes |
|-------|--------|--------|---------|-------|
| Qwen3-Reranker-0.6B | 0.6B | 65.80 | Apache 2.0 | Jun 2025, no update |
| Qwen3-Reranker-4B | 4B | 69.76 | Apache 2.0 | Jun 2025, no update |
| Qwen3-Reranker-8B | 8B | 69.02 | Apache 2.0 | Jun 2025, no update |
| BGE-reranker-v2-m3 | 568M | Battle-tested | MIT | Jul 2024, no update |
| jina-reranker-v2 | 278M | 57.06 BEIR | Apache 2.0 | Jun 2024, superseded by v3 |
| BAAI Matroyshka-ReRanker (3 variants) | 7B | -- | -- | May 2025, experimental |

---

## 6. Multimodal Rerankers

### 6.1 Qwen3-VL-Reranker-2B (NEW -- Jan 8, 2026)

First major multimodal reranker. Handles text, images, screenshots, and videos.

| Spec | Value |
|------|-------|
| Parameters | 2B |
| Max Sequence Length | 32,768 tokens |
| MMEB-v2 Average | 75.1 |
| MMEB-v2 Image | 73.8 |
| MMEB-v2 Video | 52.1 |
| MMEB-v2 VisDoc | 83.4 |
| MMTEB Retrieval | 70.0 |
| Languages | 30+ |
| License | Apache 2.0 |
| VRAM est. | ~4-5 GB |

Companion to Qwen3-VL-Embedding-2B for a complete multimodal RAG pipeline.

Sources:
- https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B
- https://arxiv.org/abs/2601.04720

---

### 6.2 Qwen3-VL-Reranker-8B (NEW -- Jan 8, 2026)

Larger multimodal reranker variant. Also available: **jina-reranker-m0** (2.4B, multimodal, Apr 2025).

Sources:
- https://huggingface.co/Qwen/Qwen3-VL-Reranker-8B

---

## 7. Knowledge Graph Embedding Models

No significant new open-source knowledge graph embedding models found in the Dec 2025 - Feb 2026 window. The field remains dominated by:
- PyKEEN framework (TransE, RotatE, ComplEx implementations)
- DGL-KE (Amazon)
- GraphSAGE / GraphSAINT for GNN-based approaches

One minor release found: `iioos/knowledge-graph-embedding-model` (Dec 26, 2025) with 0 downloads -- not production-relevant.

Neo4j continues to use its own internal embedding and GDS (Graph Data Science) library rather than external KG embedding models.

---

## 8. Master Comparison Tables

### 8.1 Text Embedding Models -- Full Comparison

| Model | Params | Dims | Matryoshka | Max Seq | MTEB-En | MMTEB | License | VRAM est. | Release |
|-------|--------|------|------------|---------|---------|-------|---------|-----------|---------|
| **Qwen3-Embedding-0.6B** (current) | 0.6B | 1024 | 32-1024 | 32K | 70.70 | 64.33 | Apache 2.0 | ~1.5 GB | Jun 2025 |
| jina-embeddings-v5-text-small | 677M | 1024 | 32-1024 | 32K | 71.7 | 67.0 | CC BY-NC | ~1.5 GB | Feb 2026 |
| jina-embeddings-v5-text-nano | 239M | 768 | 32-768 | 8K | 71.0 | 65.5 | CC BY-NC | ~0.6 GB | Feb 2026 |
| Octen-Embedding-8B | 7.6B | 4096 | No | 32K | -- | -- | Apache 2.0 | ~16 GB | Jan 2026 |
| KaLM-Embedding-Gemma3-12B | 11.76B | 3840 | 64-3840 | 32K | -- | 72.32 | Custom | ~24 GB | Nov 2025 |
| llama-embed-nemotron-8b | 7.5B | 4096 | No | 32K | 69.46 | -- | Non-commercial | ~16 GB | Oct 2025 |
| llama-nemotron-embed-1b-v2 | 1B | 2048 | 384-2048 | 8K | -- | -- | NVIDIA OML | ~2.5 GB | Feb 2026 |
| Granite-Embedding-R2 | 149M | 768 | No | 8K | -- | -- | Apache 2.0 | ~0.4 GB | Aug 2025 |
| gte-modernbert-base | 149M | 768 | No | 8K | 64.38 | -- | Apache 2.0 | ~0.4 GB | Late 2024 |
| EmbeddingGemma-300M | 308M | 768 | 128-768 | 2K | 69.67 | -- | Gemma | ~0.8 GB | Sep 2025 |
| nomic-embed-text-v2-moe | 475M/305M | 768 | 256-768 | 512 | ~53 BEIR | -- | Apache 2.0 | ~1.2 GB | Feb 2025 |
| BGE-M3 | 568M | 1024 | No | 8K | ~63 est. | -- | MIT | ~1.1 GB | 2024 |

### 8.2 Reranker Models -- Full Comparison

| Model | Params | Max Ctx | BEIR | CoIR | License | VRAM est. | Release |
|-------|--------|---------|------|------|---------|-----------|---------|
| **Qwen3-Reranker-0.6B** | 0.6B | -- | 56.28 | 65.18 | Apache 2.0 | ~1.5 GB | Jun 2025 |
| Qwen3-Reranker-4B | 4B | -- | 61.16 | 73.91 | Apache 2.0 | ~8 GB | Jun 2025 |
| jina-reranker-v3 | 600M | 131K | 61.94 | 70.64 | CC BY-NC | ~1.5 GB | Sep 2025 |
| zerank-2 | 4B | -- | -- | 0.6528 | CC BY-NC | ~8 GB | Nov 2025 |
| llama-nemotron-rerank-1b-v2 | 1B | 8K | -- | -- | NVIDIA OML | ~2.5 GB | Feb 2026 |
| ctxl-rerank-v2-1b | 1B | 32K | -- | -- | CC-BY-NC-SA | ~2.5 GB | Dec 2025 |
| mxbai-rerank-base-v2 | ~500M | -- | 55.57 | 31.73 | Apache 2.0 | ~1.2 GB | Jun 2025 |
| mxbai-rerank-large-v2 | ~1.5B | -- | 61.44 | 70.87 | Apache 2.0 | ~3 GB | Jun 2025 |
| granite-reranker-english-r2 | 149M | 8K | -- | -- | Apache 2.0 | ~0.4 GB | Sep 2025 |
| BGE-reranker-v2-m3 | 568M | 8K | 56.51 | 36.28 | MIT | ~1.2 GB | 2024 |

### 8.3 ColBERT / Late Interaction Models -- Full Comparison

| Model | Params | Token Dim | BEIR nDCG@10 | LongEmbed | License | Release |
|-------|--------|-----------|--------------|-----------|---------|---------|
| ColBERT-Zero | ~100M | 128 | 55.43 | -- | Apache 2.0 | Feb 2026 |
| GTE-ModernColBERT-v1 | ~149M | 128 | 54.67 | 88.39 | Apache 2.0 | Jan 2026 |
| mxbai-edge-colbert-v0-17m | 17M | 48 | 49.0 | -- | Apache 2.0 | Oct 2025 |
| LateOn-Code | 149M | 128 | -- | -- | Apache 2.0 | Feb 2026 |
| LateOn-Code-edge | 17M | 48 | -- | -- | Apache 2.0 | Feb 2026 |
| Jina ColBERT v2 | 560M | -- | -- | -- | CC BY-NC | Aug 2024 |

---

## 9. MTEB Leaderboard Standings (Feb 2026)

### Overall (by Borda Rank, MMTEB)

| Rank | Model | Mean (Task) | Mean (TaskType) | Params |
|------|-------|-------------|-----------------|--------|
| 1 | KaLM-Embedding-Gemma3-12B-2511 | 72.32 | 62.51 | 11.76B |
| 2 | llama-embed-nemotron-8b | 69.46 | 61.09 | 7.5B |
| 3 | Qwen3-Embedding-8B | 70.58 | 61.69 | 8B |
| 4 | gemini-embedding-001 (API only) | 68.37 | 59.59 | -- |
| 5 | Qwen3-Embedding-4B | 69.45 | 60.86 | 4B |

### Sub-1B Models (Most Relevant for Athanor)

| Model | MTEB-En | MMTEB | Dims | License |
|-------|---------|-------|------|---------|
| jina-embeddings-v5-text-small | 71.7 | 67.0 | 1024 | CC BY-NC |
| **Qwen3-Embedding-0.6B** (current) | 70.70 | 64.33 | 1024 | **Apache 2.0** |
| jina-embeddings-v5-text-nano | 71.0 | 65.5 | 768 | CC BY-NC |
| EmbeddingGemma-300M | 69.67 | 61.15 | 768 | Gemma |

### RTEB Leaderboard (#1)

| Model | Mean (Task) | Params |
|-------|-------------|--------|
| Octen-Embedding-8B | 0.8045 | 7.6B |

---

## 10. Recommendations for Athanor

### Assessment: Should We Upgrade From Qwen3-Embedding-0.6B?

**Short answer: Not yet for text embedding. Yes for adding reranking and multimodal.**

#### Text Embedding -- Stay with Qwen3-Embedding-0.6B

The only model that clearly beats Qwen3-Embedding-0.6B in the sub-1B, Apache-2.0-licensed category is... nothing. The jina-embeddings-v5-text-small edges it by +1.0 MTEB English but is CC BY-NC. Everything else either:
- Requires significantly more VRAM (8B+ models)
- Uses non-commercial licenses (Jina v5, NV-Embed-v2)
- Has lower quality (Granite R2, gte-modernbert-base)
- Uses different dimensions requiring collection migration

**Qwen3-Embedding-0.6B remains the best Apache 2.0 sub-1B embedding model.** This is unchanged from the Feb 16 assessment.

#### Reranking -- Add Qwen3-Reranker-0.6B or mxbai-rerank-base-v2

No new Apache 2.0 reranker has clearly surpassed Qwen3-Reranker-0.6B in the small-model class. The jina-reranker-v3 is impressive (BEIR 61.94) but is CC BY-NC. The NVIDIA and ContextualAI rerankers also have restrictive licenses.

**Best options for Athanor (Apache 2.0, fits on shared GPU 4):**
1. **Qwen3-Reranker-0.6B** -- Same family as embedding model, ~1.5 GB VRAM, BEIR 56.28
2. **mxbai-rerank-base-v2** -- BEIR 55.57, 3.3x faster than v1, ~1.2 GB VRAM
3. **granite-embedding-reranker-english-r2** -- Only 149M/~0.4 GB, ultra-compact

#### Multimodal -- Consider Qwen3-VL-Embedding-2B for Phase 2

The Qwen3-VL-Embedding family (Jan 2026) is a significant development. The 2B model at ~4-5 GB VRAM could enable unified image+text search in Qdrant. Apache 2.0 license. Supports 1024-dim via Matryoshka, so it's compatible with existing collections.

**Use case:** Gallery search (ComfyUI outputs), document search (screenshots/PDFs), eventually Stash metadata.

This should be a separate Qdrant collection with multimodal vectors alongside the existing text-only collection.

#### Code Search -- Consider LateOn-Code

The LateOn-Code model (149M, Apache 2.0, MTEB Code v1: 74.12) is interesting for codebase search. Uses ColBERT late interaction which requires different indexing (PyLate/PLAID). At ~0.4 GB it's tiny. However, this is a "nice to have" rather than a priority -- the current Qwen3-Embedding-0.6B handles code adequately.

#### ColBERT -- Not Recommended Yet

ColBERT-Zero and GTE-ModernColBERT-v1 are architecturally interesting but add significant complexity:
- Require per-token vector storage (6-10x more storage)
- Need PyLate/PLAID indexing infrastructure
- Qdrant supports multi-vector but the tooling is less mature
- Benefits over dense retrieval + reranking are marginal for Athanor's scale

Wait until Qdrant's ColBERT support matures.

### Dimension Compatibility Summary

| Model | Native Dims | Compatible with 1024-dim Qdrant? |
|-------|-------------|----------------------------------|
| Qwen3-Embedding-0.6B (current) | 1024 | Yes (native) |
| jina-embeddings-v5-text-small | 1024 | Yes (native) |
| jina-embeddings-v5-text-nano | 768 | No -- would need 768-dim collection |
| Octen-Embedding-8B | 4096 | No -- 4096-dim |
| KaLM-Embedding-Gemma3-12B | 3840 | Yes (via MRL at 1024) |
| llama-nemotron-embed-1b-v2 | 2048 | Yes (via Matryoshka at 1024) |
| Granite-Embedding-R2 | 768 | No -- 768-dim |
| Qwen3-VL-Embedding-2B | 2048 | Yes (via Matryoshka at 1024) |

---

## 11. Sources

### Model Pages (HuggingFace)
- jina-embeddings-v5-text-small-retrieval: https://huggingface.co/jinaai/jina-embeddings-v5-text-small-retrieval
- jina-embeddings-v5-text-nano-retrieval: https://huggingface.co/jinaai/jina-embeddings-v5-text-nano-retrieval
- Octen-Embedding-8B: https://huggingface.co/Octen/Octen-Embedding-8B
- KaLM-Embedding-Gemma3-12B-2511: https://huggingface.co/tencent/KaLM-Embedding-Gemma3-12B-2511
- llama-embed-nemotron-8b: https://huggingface.co/nvidia/llama-embed-nemotron-8b
- llama-nemotron-embed-1b-v2: https://huggingface.co/nvidia/llama-nemotron-embed-1b-v2
- llama-nemotron-rerank-1b-v2: https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2
- ColBERT-Zero: https://huggingface.co/lightonai/ColBERT-Zero
- GTE-ModernColBERT-v1: https://huggingface.co/lightonai/GTE-ModernColBERT-v1
- LateOn-Code: https://huggingface.co/lightonai/LateOn-Code
- LateOn-Code-edge: https://huggingface.co/lightonai/LateOn-Code-edge
- mxbai-edge-colbert-v0-17m: https://huggingface.co/mixedbread-ai/mxbai-edge-colbert-v0-17m
- mxbai-rerank-base-v2: https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2
- Qwen3-VL-Embedding-2B: https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B
- Qwen3-VL-Embedding-8B: https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B
- Qwen3-VL-Reranker-2B: https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B
- Qwen3-Embedding-0.6B: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- zerank-2: https://huggingface.co/zeroentropy/zerank-2
- ctxl-rerank-v2-1b: https://huggingface.co/ContextualAI/ctxl-rerank-v2-instruct-multilingual-1b
- granite-embedding-english-r2: https://huggingface.co/ibm-granite/granite-embedding-english-r2
- granite-embedding-reranker-english-r2: https://huggingface.co/ibm-granite/granite-embedding-reranker-english-r2
- gte-modernbert-base: https://huggingface.co/Alibaba-NLP/gte-modernbert-base
- jina-reranker-v3: https://huggingface.co/jinaai/jina-reranker-v3
- jina-code-embeddings-0.5b: https://huggingface.co/jinaai/jina-code-embeddings-0.5b
- NV-Embed-v2: https://huggingface.co/nvidia/NV-Embed-v2

### Papers (ArXiv)
- jina-embeddings-v5-text: https://arxiv.org/abs/2602.15547
- ColBERT-Zero: https://arxiv.org/abs/2602.16609
- Qwen3-VL-Embedding: https://arxiv.org/abs/2601.04720
- KaLM-Embedding-V2: https://arxiv.org/abs/2506.20923
- llama-embed-nemotron: https://arxiv.org/abs/2511.07025
- mxbai-rerank-v2: https://arxiv.org/abs/2506.03487
- mxbai-edge-colbert: https://arxiv.org/abs/2510.14880
- Granite Embedding R2: https://arxiv.org/abs/2508.21085
- jina-reranker-v3: https://arxiv.org/abs/2509.25085

### Blog Posts
- Jina v5 announcement: https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings
- Jina models overview: https://jina.ai/models/
- ContextualAI Rerank v2: https://contextual.ai/blog/rerank-v2

### Leaderboards
- MTEB Leaderboard: https://huggingface.co/spaces/mteb/leaderboard
