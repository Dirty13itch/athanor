# Embedding & RAG Models for Local Inference

**Date:** 2026-02-16
**Status:** Complete — recommendation ready
**Supports:** RAG infrastructure for Athanor projects
**Depends on:** ADR-004 (Node Roles)

---

## The Question

Which embedding models, reranking models, and vector databases should Athanor deploy for local RAG pipelines? The embedding GPU is an RTX 3060 12 GB on Node 1, which must coexist with potentially a small utility LLM. Models will be served via sentence-transformers or vLLM.

---

## Hardware Context

- **RTX 3060 12 GB** (Node 1) — dedicated embedding/utility GPU. Ampere architecture, CUDA Compute 8.6.
- Must leave headroom for a small utility model (e.g., Qwen3-0.6B for tool calling) sharing the same GPU.
- Practical VRAM budget for embedding + reranker: **~4-6 GB** (leaving 6-8 GB for utility LLM + overhead).
- sentence-transformers and vLLM both support embedding model serving. vLLM has had embedding support since v0.4+ and continues expanding it through 2025-2026.

Sources:
- [vLLM embedding documentation](https://docs.vllm.ai/en/v0.7.0/getting_started/examples/embedding.html)
- [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models/)
- [sentence-transformers GPU efficiency](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)

---

## 1. Text Embedding Models

### Model-by-Model Analysis

#### Qwen3-Embedding-0.6B (Alibaba/Qwen)

The newest contender in the small embedding model space. Part of the Qwen3 family released June 2025.

| Spec | Value |
|------|-------|
| Parameters | 0.6B |
| Dimensions | 32-1024 (flexible via MRL) |
| Max Sequence Length | 32,768 tokens |
| VRAM (FP16 est.) | ~1.5 GB |
| MTEB English v2 | 70.70 (Mean Task) |
| MTEB Multilingual v2 | 64.33 (Mean Task) |
| MTEB Retrieval (MTEB-R) | 61.82 |
| License | Apache 2.0 |
| Multilingual | 100+ languages |
| Matryoshka | Yes (32-1024) |

Instruction-aware: supports task-specific prompts for 1-5% performance gains. The 0.6B model punches well above its weight — its MTEB English v2 score of 70.70 is competitive with models 3-5x its size. The 32K context window is exceptionally long for an embedding model this small.

Sources:
- [Qwen3-Embedding-0.6B HuggingFace](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Qwen3 Embedding blog](https://qwenlm.github.io/blog/qwen3-embedding/)
- [Qwen3-Embedding paper](https://arxiv.org/abs/2506.05176)

---

#### nomic-embed-text-v2-moe (Nomic AI)

The first MoE architecture embedding model. Released February 2025.

| Spec | Value |
|------|-------|
| Parameters | 475M total / 305M active |
| Dimensions | 256-768 (Matryoshka) |
| Max Sequence Length | 512 tokens |
| VRAM (FP16 est.) | ~1.2 GB (active), ~1.5 GB (total loaded) |
| BEIR | 52.86 |
| MIRACL | 65.80 |
| License | Apache 2.0 |
| Multilingual | ~100 languages |
| Matryoshka | Yes (256-768) |

The MoE architecture means only 305M of 475M parameters activate per inference, giving speed closer to a 300M model with quality closer to a 600M model. Strong multilingual performance via MIRACL. The 512-token context limit is the main weakness — fine for short passages but limits chunking flexibility.

Sources:
- [nomic-embed-text-v2-moe HuggingFace](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)
- [Nomic Embed v2 blog](https://www.nomic.ai/blog/posts/nomic-embed-text-v2)
- [Training paper](https://arxiv.org/abs/2502.07972)

---

#### EmbeddingGemma-300M (Google DeepMind)

Google's efficient on-device embedding model, released September 2025. Built on Gemma 3 backbone with bidirectional attention.

| Spec | Value |
|------|-------|
| Parameters | 308M |
| Dimensions | 128-768 (Matryoshka) |
| Max Sequence Length | 2,048 tokens |
| VRAM (FP16 est.) | ~0.8 GB (does NOT support FP16 — use BF16/FP32) |
| MTEB English v2 | 69.67 (Mean Task) |
| MTEB Multilingual v2 | 61.15 (Mean Task) |
| MTEB Code v1 | 68.76 |
| License | Gemma (permissive commercial, with usage policy) |
| Multilingual | 100+ languages |
| Matryoshka | Yes (128, 256, 512, 768) |

Number 1 rank among all models under 500M on MTEB across multilingual, English, and code leaderboards. Can run in under 200 MB RAM with quantization. Ideal for on-device/edge but also excellent for GPU serving. The 2K context is shorter than Qwen3's 32K but adequate for typical RAG chunks. Important caveat: float16 is NOT supported — must use bfloat16 or float32.

Sources:
- [EmbeddingGemma HuggingFace](https://huggingface.co/google/embeddinggemma-300m)
- [Google Developers Blog](https://developers.googleblog.com/introducing-embeddinggemma/)
- [EmbeddingGemma paper](https://arxiv.org/abs/2509.20354)
- [HuggingFace blog](https://huggingface.co/blog/embeddinggemma)

---

#### BGE-M3 (BAAI)

The Swiss army knife of embedding models. Multi-Functionality (dense + sparse + multi-vector), Multi-Linguality, Multi-Granularity.

| Spec | Value |
|------|-------|
| Parameters | 568M |
| Dimensions | 1024 |
| Max Sequence Length | 8,192 tokens |
| VRAM (FP16) | ~1.1 GB model + runtime overhead |
| MTEB Multilingual | ~63.0 (estimated aggregate) |
| License | MIT |
| Multilingual | 100+ languages |
| Matryoshka | No (fixed 1024-d) |

The killer feature is triple retrieval: dense vectors, sparse vectors (like learned BM25), and ColBERT-style multi-vector — all from a single model. This is uniquely valuable for hybrid search. The 8K context window handles long documents well. Downside: no Matryoshka support, so you're stuck at 1024 dimensions. Based on XLM-RoBERTa.

Sources:
- [BGE-M3 HuggingFace](https://huggingface.co/BAAI/bge-m3)
- [BGE-M3 memory requirements](https://huggingface.co/BAAI/bge-m3/discussions/64)
- [BGE documentation](https://bge-model.com/bge/bge_m3.html)

---

#### gte-Qwen2-1.5B-instruct (Alibaba)

Larger model offering higher quality at the cost of more VRAM.

| Spec | Value |
|------|-------|
| Parameters | 1.5B |
| Dimensions | 1024 (default) |
| Max Sequence Length | 32,768 tokens |
| VRAM (FP16 est.) | ~3.5 GB |
| MTEB English (Mean Task) | 67.20 |
| MTEB English Retrieval | 50.25 |
| C-MTEB Chinese (Mean Task) | 67.12 |
| License | Apache 2.0 |
| Multilingual | Yes (strong CJK) |
| Matryoshka | Yes |

The 1.5B size puts it in an awkward spot for a 12 GB GPU that must share with other models. Its MTEB English score of 67.20 is actually lower than Qwen3-Embedding-0.6B's 70.70, which means the newer 0.6B model has superseded it. Still relevant for Chinese-heavy workloads.

Sources:
- [gte-Qwen2-1.5B-instruct HuggingFace](https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct)
- [Alibaba Cloud blog](https://www.alibabacloud.com/blog/gte-multilingual-series-a-key-model-for-retrieval-augmented-generation_601776)

---

#### jina-embeddings-v3 (Jina AI)

Strong performance with task-specific LoRA adapters, but licensing is problematic.

| Spec | Value |
|------|-------|
| Parameters | 570M |
| Dimensions | 32-1024 (Matryoshka) |
| Max Sequence Length | 8,192 tokens |
| VRAM (FP16 est.) | ~1.3 GB |
| MTEB English (Mean) | 65.52 |
| Classification | 82.58 |
| STS | 85.80 |
| License | **CC BY-NC 4.0** (non-commercial) |
| Multilingual | 100+ languages |
| Matryoshka | Yes (32-1024) |

Excellent quality but the CC BY-NC license is a hard disqualifier for Athanor. Commercial self-hosted use requires a separate license agreement with Jina AI. The task LoRA approach (retrieval.query, retrieval.passage, classification, etc.) is clever but adds complexity.

Sources:
- [jina-embeddings-v3 page](https://jina.ai/models/jina-embeddings-v3/)
- [jina-embeddings-v3 paper](https://arxiv.org/abs/2409.10173)
- [HuggingFace](https://huggingface.co/jinaai/jina-embeddings-v3)

---

#### Snowflake Arctic-embed-l-v2.0

Snowflake's retrieval-focused multilingual model.

| Spec | Value |
|------|-------|
| Parameters | 303M |
| Dimensions | 1024 |
| Max Sequence Length | 8,192 tokens (via RoPE) |
| VRAM (FP16 est.) | ~0.7 GB |
| MTEB Retrieval (nDCG@10) | 0.556 |
| MIRACL | 0.649 |
| License | Apache 2.0 |
| Multilingual | Yes |
| Matryoshka | Yes (down to 128-d) |

Excellent retrieval performance for its size. The MRL + quantization-aware training means you can use 128-byte vectors with minimal quality loss. Very efficient. However, it's retrieval-focused — may underperform on classification/clustering tasks compared to general-purpose models.

Sources:
- [Arctic-embed-l-v2.0 HuggingFace](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0)
- [Arctic-Embed 2.0 paper](https://arxiv.org/html/2412.04506v2)
- [Snowflake blog](https://www.snowflake.com/en/engineering-blog/snowflake-arctic-embed-2-multilingual/)

---

#### mxbai-embed-large-v1 (Mixedbread)

BERT-large class model. SOTA for its architecture class as of early 2024.

| Spec | Value |
|------|-------|
| Parameters | ~335M (BERT-large architecture) |
| Dimensions | 1024 |
| Max Sequence Length | 512 tokens |
| VRAM (FP16 est.) | ~0.8 GB |
| MTEB English | SOTA for BERT-large class (March 2024) |
| License | Apache 2.0 |
| Multilingual | English-focused |
| Matryoshka | Yes |

Was excellent in early 2024 but has been surpassed by EmbeddingGemma, Qwen3-Embedding-0.6B, and others. The 512-token context limit and English-only focus make it less attractive for a multilingual RAG system.

Sources:
- [mxbai-embed-large-v1 HuggingFace](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1)
- [Mixedbread blog](https://www.mixedbread.com/blog/mxbai-embed-large-v1)

---

#### E5-Large-v2 (Microsoft/intfloat)

Older but still widely used baseline model.

| Spec | Value |
|------|-------|
| Parameters | 335M |
| Dimensions | 1024 |
| Max Sequence Length | 512 tokens |
| VRAM (FP16 est.) | ~0.8 GB |
| License | MIT |
| Multilingual | No (English only) |
| Matryoshka | No |

Dated. Superseded by every modern model on this list. No Matryoshka, no multilingual, 512 context. Listed for completeness only.

Sources:
- [E5-Large-v2 HuggingFace](https://huggingface.co/intfloat/e5-large-v2)

---

#### E5-Mistral-7B-instruct (Microsoft/intfloat)

LLM-based embedding model. High quality but extremely expensive.

| Spec | Value |
|------|-------|
| Parameters | 7B |
| Dimensions | 4096 |
| Max Sequence Length | 32,768 tokens |
| VRAM (FP16) | ~14 GB |
| License | MIT |
| Multilingual | Limited |
| Matryoshka | No |

Does not fit the hardware. 14 GB FP16 exceeds the entire 12 GB GPU, and even quantized would leave nothing for other models. The quality is good but the newer Qwen3-Embedding-0.6B matches or exceeds it on MTEB at 1/12th the size. **Eliminated.**

Sources:
- [E5-Mistral-7B-instruct HuggingFace](https://huggingface.co/intfloat/e5-mistral-7b-instruct)

---

#### voyage-3 variants (Voyage AI)

**Not open-weight.** API-only access. Voyage-3-large is SOTA on many retrieval benchmarks but cannot be self-hosted. **Eliminated** from consideration.

Sources:
- [Voyage AI docs](https://docs.voyageai.com/docs/embeddings)
- [voyage-3-large blog](https://blog.voyageai.com/2025/01/07/voyage-3-large/)

---

### Embedding Models Comparison Table

| Model | Params | Active | Dims | Max Seq | VRAM (FP16) | MTEB Eng | License | Matryoshka | Multilingual |
|-------|--------|--------|------|---------|-------------|----------|---------|------------|-------------|
| **Qwen3-Embedding-0.6B** | 0.6B | 0.6B | 32-1024 | 32K | ~1.5 GB | 70.70 | Apache 2.0 | Yes | 100+ |
| **nomic-embed-text-v2-moe** | 475M | 305M | 256-768 | 512 | ~1.2 GB | ~53 (BEIR) | Apache 2.0 | Yes | ~100 |
| **EmbeddingGemma-300M** | 308M | 308M | 128-768 | 2K | ~0.8 GB | 69.67 | Gemma | Yes | 100+ |
| **BGE-M3** | 568M | 568M | 1024 | 8K | ~1.1 GB | ~63 est. | MIT | No | 100+ |
| **gte-Qwen2-1.5B** | 1.5B | 1.5B | 1024 | 32K | ~3.5 GB | 67.20 | Apache 2.0 | Yes | Yes |
| **jina-embeddings-v3** | 570M | 570M | 32-1024 | 8K | ~1.3 GB | 65.52 | CC BY-NC | Yes | 100+ |
| **Arctic-embed-l-v2.0** | 303M | 303M | 1024 | 8K | ~0.7 GB | retrieval-focused | Apache 2.0 | Yes | Yes |
| **mxbai-embed-large** | 335M | 335M | 1024 | 512 | ~0.8 GB | BERT-large SOTA | Apache 2.0 | Yes | No |
| **E5-Large-v2** | 335M | 335M | 1024 | 512 | ~0.8 GB | dated | MIT | No | No |

---

## 2. Reranking Models

Rerankers process query-document pairs through a cross-encoder and output a relevance score. They improve retrieval precision by 15-40% over embedding-only retrieval but add 100-600ms latency per batch.

### Qwen3-Reranker (Alibaba/Qwen)

The newest reranker family, released alongside Qwen3-Embedding in June 2025.

| Variant | Parameters | MTEB-R | CMTEB-R | MMTEB-R | MTEB-Code | License |
|---------|-----------|--------|---------|---------|-----------|---------|
| Qwen3-Reranker-0.6B | 0.6B | 65.80 | 71.31 | 66.36 | 73.42 | Apache 2.0 |
| Qwen3-Reranker-4B | 4B | 69.76 | 75.94 | 72.74 | 81.20 | Apache 2.0 |
| Qwen3-Reranker-8B | 8B | 69.02 | 77.45 | 72.94 | 81.22 | Apache 2.0 |

The 0.6B variant is the sweet spot for our hardware. At ~1.5 GB VRAM it fits comfortably alongside the embedding model, and its MTEB-R of 65.80 is strong. The 4B variant (69.76 MTEB-R) would be better quality but at ~8 GB it would not coexist with other models on a 12 GB GPU.

Sources:
- [Qwen3-Reranker-0.6B HuggingFace](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- [Qwen3-Reranker-8B HuggingFace](https://huggingface.co/Qwen/Qwen3-Reranker-8B)
- [Qwen3 Embedding blog](https://qwenlm.github.io/blog/qwen3-embedding/)

---

### BGE-reranker-v2-m3 (BAAI)

The workhorse multilingual reranker. Part of the BGE-M3 ecosystem.

| Spec | Value |
|------|-------|
| Parameters | 568M |
| Base Model | bge-m3 (XLM-RoBERTa) |
| Max Sequence Length | 8,192 tokens |
| VRAM (FP16) | ~1.2 GB |
| License | MIT |
| Multilingual | 18+ languages |
| Cross-lingual | Yes |

Widely used, battle-tested, and lightweight. Pairs naturally with BGE-M3 embeddings. The MIT license is maximally permissive. Speed is decent but Jina's reranker is reportedly 15x faster.

Sources:
- [BGE-reranker-v2-m3 HuggingFace](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- [BGE Reranker documentation](https://bge-model.com/tutorial/5_Reranking/5.2.html)

---

### BGE-reranker-v2.5-gemma2-lightweight (BAAI)

A larger but more capable reranker with layer and token compression.

| Spec | Value |
|------|-------|
| Parameters | Based on Gemma2-9B |
| VRAM (FP16) | ~18 GB (full) but supports layerwise reduction |
| License | Gemma |
| Compression | Token compression + layerwise lightweight |

Too large for the 12 GB GPU even with compression features. **Eliminated** for this hardware.

Sources:
- [BGE-reranker-v2.5-gemma2-lightweight HuggingFace](https://huggingface.co/BAAI/bge-reranker-v2.5-gemma2-lightweight)

---

### jina-reranker-v2-base-multilingual (Jina AI)

Compact and fast multilingual reranker.

| Spec | Value |
|------|-------|
| Parameters | 278M |
| Max Sequence Length | 1,024 tokens (auto-chunks longer docs) |
| VRAM (FP16 est.) | ~0.7 GB |
| MKQA (26 languages) | 54.83 nDCG@10 |
| License | Apache 2.0 |
| Multilingual | 100+ languages |
| Speed | 15x faster than BGE-reranker-v2-m3 |

Very compact and extremely fast. The automatic long-document chunking with configurable overlap is a nice feature. The 278M size means it barely uses any VRAM. However, it appears to be slightly less capable than the Qwen3 and BGE rerankers on retrieval quality.

Sources:
- [jina-reranker-v2 HuggingFace](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual)
- [Jina Reranker v2 blog](https://jina.ai/news/jina-reranker-v2-for-agentic-rag-ultra-fast-multilingual-function-calling-and-code-search/)

---

### ColBERT v2 / Jina ColBERT v2

Late interaction retrieval model — different paradigm from cross-encoder rerankers.

| Spec | Value |
|------|-------|
| Architecture | Late interaction (per-token similarity) |
| Storage | Requires per-token vector storage (higher disk/RAM) |
| Speed | Faster than cross-encoder reranking |
| Quality | Strong retrieval, weaker at fine-grained reranking |

ColBERT stores per-token embeddings and computes MaxSim scores. This requires significantly more storage (6-10x vs. single-vector) but enables faster retrieval than cross-encoder reranking. Jina ColBERT v2 improves on original ColBERTv2 by +6.5%. More of a retrieval paradigm shift than a drop-in reranker — adds complexity without clear benefit for a one-person RAG stack.

Sources:
- [ColBERTv2 paper](https://arxiv.org/abs/2112.01488)
- [Jina ColBERT v2 blog](https://jina.ai/news/jina-colbert-v2-multilingual-late-interaction-retriever-for-embedding-and-reranking/)
- [Qdrant ColBERT docs](https://qdrant.tech/documentation/fastembed/fastembed-colbert/)

---

### ColPali

Multimodal late-interaction model that treats documents as images. Uses PaliGemma VLM backbone. Relevant for visual document retrieval (PDFs with diagrams, tables, etc.) but overkill for text-focused RAG. **Not recommended** for initial deployment.

Sources:
- [Weaviate late interaction overview](https://weaviate.io/blog/late-interaction-overview)

---

### Reranking Models Comparison Table

| Model | Params | VRAM (FP16) | MTEB-R | Speed | License | Multilingual |
|-------|--------|-------------|--------|-------|---------|-------------|
| **Qwen3-Reranker-0.6B** | 0.6B | ~1.5 GB | 65.80 | Moderate | Apache 2.0 | 100+ |
| **BGE-reranker-v2-m3** | 568M | ~1.2 GB | Battle-tested | Moderate | MIT | 18+ |
| **jina-reranker-v2** | 278M | ~0.7 GB | Good | 15x faster | Apache 2.0 | 100+ |
| **Qwen3-Reranker-4B** | 4B | ~8 GB | 69.76 | Slower | Apache 2.0 | 100+ |
| ColBERT v2 | ~110M | ~0.3 GB | Different paradigm | Fast retrieval | MIT | Limited |

---

## 3. Vector Databases

### Qdrant

Written in Rust. Purpose-built vector database with native hybrid search.

| Feature | Details |
|---------|---------|
| Language | Rust |
| Docker | `docker pull qdrant/qdrant` — single command |
| Min Resources | 0.5 CPU, 1 GB RAM |
| Sparse Vectors | Native support |
| Hybrid Search | Dense + sparse with RRF or DBSF fusion |
| Filtering | Rich payload filtering (JSON fields) |
| Quantization | Scalar, product, and binary — up to 97% RAM reduction |
| Memory-mapped | Yes (mmap for disk-based storage) |
| API | REST + gRPC + client libraries (Python, JS, Rust, Go) |
| License | Apache 2.0 |
| GitHub Stars | ~22K |

**RAM estimate for 1M vectors at 1024-d:** ~8.6 GB in-memory, ~1-2 GB with quantization + mmap.

Qdrant is the strongest choice for a single-node homelab. Native sparse vector support means you can do hybrid search (dense + BM25-style sparse) without a separate keyword index. The Rust implementation is fast and memory-efficient. Docker deployment is trivially simple. The Query API supports fusion of multiple search strategies in a single call.

Sources:
- [Qdrant installation](https://qdrant.tech/documentation/guides/installation/)
- [Qdrant memory consumption](https://qdrant.tech/articles/memory-consumption/)
- [Qdrant hybrid search](https://qdrant.tech/articles/hybrid-search/)
- [Qdrant sparse vectors](https://qdrant.tech/articles/sparse-vectors/)
- [Qdrant capacity planning](https://qdrant.tech/documentation/guides/capacity-planning/)

---

### Milvus

Enterprise-grade distributed vector database. Can run standalone via Docker.

| Feature | Details |
|---------|---------|
| Language | Go + C++ |
| Docker | Standalone mode via Docker Compose (includes etcd + MinIO) |
| Min Resources | 2 vCPU, 8 GB RAM (recommended) |
| Sparse Vectors | Yes |
| Hybrid Search | Dense + sparse |
| Filtering | Metadata filtering via expressions |
| Index Types | IVF, HNSW, DiskANN, SCANN, and more |
| License | Apache 2.0 |
| GitHub Stars | ~35K |

The standalone Docker deployment requires etcd and MinIO as dependencies (Docker Compose with 3 containers minimum). This is more infrastructure than needed for a one-person operation. The 8 GB RAM recommendation is steep for a vector DB that's just one component of the stack. Milvus excels at billion-scale but that's not our problem.

Sources:
- [Milvus Docker standalone](https://milvus.io/docs/install_standalone-docker.md)
- [Milvus prerequisites](https://milvus.io/docs/prerequisite-docker.md)
- [Milvus deployment overview](https://milvus.io/docs/install-overview.md)

---

### ChromaDB

Python-native vector database. Simplest possible setup.

| Feature | Details |
|---------|---------|
| Language | Python |
| Docker | `docker pull chromadb/chroma` — single container |
| Min Resources | 2 GB RAM |
| Sparse Vectors | No native sparse vector support |
| Hybrid Search | Limited (metadata filtering, not true sparse+dense) |
| Filtering | Basic metadata filtering |
| Index Types | HNSW |
| License | Apache 2.0 |
| GitHub Stars | ~18K |

ChromaDB is the easiest to get started with but lacks critical features for a proper RAG stack. No sparse vector support means no hybrid search. It's in-memory by default with no built-in quantization or mmap. Good for prototypes, not for production RAG infrastructure.

Sources:
- [ChromaDB Docker](https://docs.trychroma.com/guides/deploy/docker)
- [ChromaDB resource requirements](https://cookbook.chromadb.dev/core/resources/)

---

### Weaviate

GraphQL-powered vector database with built-in ML model integration.

| Feature | Details |
|---------|---------|
| Language | Go |
| Docker | Docker Compose (single container possible) |
| Min Resources | ~3 GB RAM for 1M 384-d vectors |
| Sparse Vectors | BM25 built-in |
| Hybrid Search | Yes — Hybrid Search 2.0 (2025 rewrite, 60% faster) |
| Filtering | Rich metadata + cross-references |
| Index Types | HNSW (must fit in memory) |
| Built-in ML | Can run embedding models internally |
| License | BSD-3-Clause |
| GitHub Stars | ~13K |

Weaviate's built-in BM25 + vector hybrid search is compelling. The HNSW index must be in memory, which limits dataset size. The GraphQL API is powerful but adds learning curve. The built-in ML model serving is interesting but we already have dedicated GPU infrastructure. Overall, more complex than Qdrant without clear advantages for our use case.

Sources:
- [Weaviate resource planning](https://weaviate.io/developers/weaviate/concepts/resources)
- [Weaviate Hybrid Search 2.0](https://app.ailog.fr/en/blog/news/weaviate-hybrid-search-2)
- [Weaviate Docker](https://hub.docker.com/r/semitechnologies/weaviate)

---

### pgvector (PostgreSQL extension)

Vector search as a PostgreSQL extension. Keep everything in one database.

| Feature | Details |
|---------|---------|
| Language | C (PostgreSQL extension) |
| Docker | Any PostgreSQL Docker image + extension |
| Min Resources | PostgreSQL baseline (~256 MB + vector data) |
| Sparse Vectors | Yes (up to 16K non-zeros, index up to 1K) |
| Hybrid Search | BM25 via pg_search/ParadeDB + vector via pgvector |
| Filtering | Full SQL |
| Index Types | IVF, HNSW |
| License | PostgreSQL License (MIT-like) |

The "no new infrastructure" option. If you're already running PostgreSQL, pgvector adds vector search without a separate database. Performance drops at 10M+ vectors but that's far beyond what Athanor needs. The ability to combine SQL queries with vector search is powerful. Downsides: no built-in quantization, GPU acceleration, or memory-mapped storage. Benchmark data shows Qdrant at 10x+ higher QPS than pgvector at 50M vectors, but at small scale (< 1M vectors) the difference is negligible.

Sources:
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector hybrid search](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/)
- [pgvector benchmark analysis](https://medium.com/@DataCraft-Innovations/postgres-vector-search-with-pgvector-benchmarks-costs-and-reality-check-f839a4d2b66f)

---

### Vector Database Comparison Table

| Database | Min RAM | Docker Ease | Sparse Vectors | Hybrid Search | Quantization | One-Person Scale |
|----------|---------|-------------|----------------|---------------|--------------|-----------------|
| **Qdrant** | 1 GB | Single container | Native | Dense+Sparse+Fusion | Built-in (97% reduction) | Excellent |
| **pgvector** | ~256 MB + PG | Extension on PG | Yes (16K) | Via ParadeDB/pg_search | No | Excellent (if using PG) |
| **Weaviate** | ~3 GB | Docker Compose | BM25 built-in | Hybrid Search 2.0 | PQ | Good |
| **ChromaDB** | 2 GB | Single container | No | No | No | Prototyping only |
| **Milvus** | 8 GB | 3+ containers | Yes | Yes | Yes | Overkill |

---

## Recommendations

### Best Embedding Model: Qwen3-Embedding-0.6B

The clear winner for the 12 GB GPU constraint. At ~1.5 GB VRAM it leaves ample room for a reranker and utility LLM. Its MTEB English score of 70.70 beats models 2-5x larger. The 32K context window is the longest in its class. Apache 2.0 license. Matryoshka support from 32 to 1024 dimensions. 100+ languages.

**Runner-up:** EmbeddingGemma-300M if you want even smaller footprint (~0.8 GB) with slightly lower quality (69.67 vs 70.70). The Gemma license is slightly more restrictive but still commercially permissive.

**Honorable mention:** BGE-M3 if you want native multi-retrieval (dense + sparse + multi-vector from one model) and 8K context, at the cost of larger dimensions (no Matryoshka) and slightly lower quality.

### Best Reranker: Qwen3-Reranker-0.6B

Matches the embedding model family. MTEB-R of 65.80 at only ~1.5 GB VRAM. Apache 2.0. 100+ languages. Code reranking score of 73.42 is useful for technical documentation RAG.

**Runner-up:** jina-reranker-v2-base-multilingual if speed is the priority — 15x faster than BGE-reranker-v2-m3 at only 278M parameters (~0.7 GB VRAM). Apache 2.0.

### Best Vector Database: Qdrant

Native sparse + dense hybrid search. Single Docker container. Runs on 1 GB RAM minimum. Built-in quantization reduces memory by up to 97%. Rust implementation is fast and reliable. Apache 2.0. The Query API's native fusion means you can combine multiple search strategies without application-level logic.

**Runner-up:** pgvector if you're already running PostgreSQL for application data. The "single database for everything" approach has real operational simplicity value for a one-person team.

### Complete RAG Stack Recommendation

```
Query --> Qwen3-Embedding-0.6B (embed query, ~1.5 GB VRAM)
                    |
                    v
            Qdrant (hybrid search: dense + sparse)
                    |
                    v (top-20 candidates)
          Qwen3-Reranker-0.6B (rerank, ~1.5 GB VRAM)
                    |
                    v (top-5 documents)
              LLM Generation (on main GPU cluster)
```

**Total VRAM for embedding + reranking: ~3 GB** on the RTX 3060, leaving ~9 GB for a utility LLM (e.g., Qwen3-0.6B for tool calling at ~1.5 GB, or a small coding model).

**Qdrant** runs as a Docker container on Node 1, consuming primarily RAM (not GPU). With scalar quantization and mmap, millions of vectors fit in a few GB of system RAM.

**Serving options:**
- **sentence-transformers** — simplest for embedding models, well-supported, handles batching efficiently
- **vLLM** — can serve embedding models alongside LLMs, useful if consolidating serving infrastructure
- **Infinity** (by Michael Feil) — specialized embedding/reranking server with ONNX optimization, 2-3x speedup over naive PyTorch

**Why this stack:**
1. Both models are from the same Qwen3 family — tested together, same tokenizer ecosystem
2. Combined VRAM of ~3 GB leaves the majority of the 12 GB GPU free
3. Apache 2.0 across the entire stack (models + Qdrant)
4. 100+ language support throughout
5. Matryoshka embeddings allow starting at 256-d for speed, scaling to 1024-d for quality
6. Qwen3-Embedding-0.6B's 32K context handles even very long documents
7. Qdrant's native hybrid search eliminates the need for a separate BM25 index

---

## Open Questions

1. **Sparse vector generation:** Qwen3-Embedding-0.6B produces dense vectors only. For hybrid search, we need a sparse encoder (SPLADE, BM42, or BGE-M3's sparse head). Options: (a) use Qdrant's built-in BM42/SPLADE via FastEmbed, (b) add BGE-M3 purely for sparse vector generation, (c) use BM25 keyword matching instead of learned sparse vectors.

2. **Quantization impact:** How much does INT8/INT4 quantization of Qwen3-Embedding-0.6B affect retrieval quality? Could free another ~0.5-1 GB VRAM.

3. **Serving framework:** Need to benchmark sentence-transformers vs. vLLM vs. Infinity for embedding throughput on RTX 3060 specifically. Infinity's ONNX path may be fastest for pure embedding workloads.

4. **Can Qwen3-Embedding and Qwen3-Reranker share a vLLM instance?** Both are Qwen3 architecture — may be possible to serve both from one process using vLLM's multi-model support.
