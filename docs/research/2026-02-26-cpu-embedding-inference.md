# CPU-Based Embedding Inference: Replacing vLLM-Embedding on GPU

**Date:** 2026-02-26
**Status:** Research Complete
**Author:** Research Agent (Claude)

---

## Context

Athanor currently runs Qwen3-Embedding-0.6B on vLLM on Node 1 GPU 4 (RTX 5070 Ti 16GB), consuming ~5.2 GB VRAM on a shared GPU that also hosts wyoming-whisper and Speaches (~3.6 GB combined). The embedding workload is low-throughput: single embeddings per agent request (text up to 2000 chars), context enrichment queries, and periodic knowledge indexing (batches of 20 chunks). This is a poor use of GPU resources given the bursty, low-volume nature of embedding requests.

**Goal:** Move embedding inference to CPU on Node 1 (EPYC 7663, 56 cores, 224 GB RAM), freeing 5.2 GB VRAM on GPU 4, while maintaining the same model (Qwen3-Embedding-0.6B) and 1024-dimension embeddings to avoid re-indexing Qdrant (2220 points across 4 collections).

**Constraint:** Must expose an OpenAI-compatible `/v1/embeddings` endpoint. All consumers (8 agents, `index-knowledge.py`, MCP bridge) access embedding via LiteLLM at VAULT:4000, which proxies to Node 1:8001. The replacement must be a drop-in at the API level.

---

## Options Evaluated

### Option 1: HuggingFace Text Embeddings Inference (TEI) on CPU

**What it is:** A Rust-based inference server purpose-built for embedding and reranking models. Maintained by HuggingFace. Uses the candle backend (pure Rust, no Python) with Intel MKL optimizations on CPU.

**Model support:** Explicitly lists Qwen3-Embedding-0.6B as a supported model (MTEB rank #4 in their docs). Also supports Qwen3-Embedding-4B, Qwen3-Embedding-8B, and dozens of other architectures (BERT, RoBERTa, Nomic, GTE, Mistral, ModernBERT, Gemma3).

**CPU Docker image:** `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9`

**API compatibility:** Native OpenAI-compatible `/v1/embeddings` endpoint. Drop-in replacement for vLLM's embedding endpoint.

**Known issues:** GitHub issue #667 documented Qwen3-Embedding-0.6B failing on CPU in TEI v1.7.3 (Intel MKL SGEMM error). Resolved in v1.7.4 with `--revision refs/pr/27`. The current version is 1.9, which should have this fix merged upstream.

**Deployment:**
```bash
docker run -p 8001:80 \
  -v /mnt/vault/models:/data \
  ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 \
  --model-id /data/Qwen3-Embedding-0.6B \
  --dtype float32
```

**Performance estimate:**
- CPU benchmark data (Intel Xeon 8480+, 56 cores, similar to EPYC 7663): BGE-large (355M params, 1024-dim) achieves <20ms latency at batch size 1, and with INT8 quantization, 500M param models achieve ~10ms.
- Qwen3-Embedding-0.6B is 509M params. Expect **15-30ms per single embedding** on EPYC 7663 in FP32, potentially **10-15ms with quantization**.
- For knowledge indexing batches of 20: ~300-600ms per batch (vs near-instant on GPU).
- For Athanor's usage pattern (sporadic single queries), this latency is imperceptible.

**Pros:**
- Same model, same embeddings, zero re-indexing
- Purpose-built for embedding workloads (not a general LLM server)
- Native OpenAI-compatible API, no wrapper needed
- Small Docker image, fast startup
- Dynamic batching built in
- Active maintenance by HuggingFace
- Frees 5.2 GB VRAM on GPU 4

**Cons:**
- CPU inference is inherently slower than GPU (10-50x for high throughput)
- No GPU acceleration option without a different Docker image
- Candle backend on CPU is less battle-tested than GPU path
- MKL dependency means AMD EPYC may not get full optimization (Intel-specific instructions)
- New service to maintain

---

### Option 2: Qdrant FastEmbed (Library + Custom Server)

**What it is:** A Python library by Qdrant that runs ONNX-based embedding models on CPU. Uses ONNX Runtime instead of PyTorch.

**Model support:** Does NOT natively support Qwen3-Embedding-0.6B. Supported 1024-dim models: `mxbai-embed-large-v1`, `snowflake-arctic-embed-l`, `gte-large`, `bge-large-en-v1.5`, `multilingual-e5-large`. However, custom models can be added via `TextEmbedding.add_custom_model()`.

**Community ONNX model:** `electroglyph/Qwen3-Embedding-0.6B-onnx-uint8` exists on HuggingFace. Dynamic uint8 quantization, 624 MiB, ~25% faster than FP32 on CPU (Ryzen benchmark: 34.6s vs 46.1s for 10 large chunks). NDCG@10 within ~1% of FP32. However, this requires custom pooling/normalization handling.

**Critical limitation:** FastEmbed is a library, NOT a server. It has no built-in HTTP API. To use it as a vLLM replacement, you would need to:
1. Write a FastAPI wrapper exposing `/v1/embeddings`
2. Handle batching, error handling, health checks
3. Containerize and deploy
4. Maintain this custom code

**Embedding compatibility concern:** Using the uint8 quantized ONNX model would produce slightly different embeddings than the FP32 model on vLLM. The ~1% NDCG difference suggests embeddings are close but not identical. This may or may not require re-indexing depending on tolerance.

**Pros:**
- ONNX Runtime is well-optimized for CPU
- Uint8 quantization available for faster inference
- Lightweight (no Rust compilation)
- Qdrant has built-in FastEmbed integration for direct embedding

**Cons:**
- No server component -- requires custom wrapper code
- Qwen3-Embedding-0.6B not natively supported (custom model setup)
- Community ONNX model may drift from upstream
- Uint8 quantization produces different embeddings (possible re-index)
- More moving parts to maintain
- Less mature than TEI for production serving

---

### Option 3: Infinity Embedding Server

**What it is:** A high-throughput embedding server by Michael Feil, built on FastAPI with ONNX/TensorRT/CTranslate2 backends. OpenAI-compatible API.

**Model support:** Supports sentence-transformers models and many HuggingFace models. Qwen3 architecture support is not explicitly documented. The project primarily targets BERT-family and sentence-transformer models.

**CPU support:** Available with int8 quantization via ONNX or CTranslate2 backends.

**Pros:**
- OpenAI-compatible API out of the box
- Multiple backend options (ONNX, CTranslate2)
- CPU int8 quantization support
- Active development

**Cons:**
- Qwen3 architecture support uncertain (Qwen3 uses RoPE positions, different from BERT-family)
- Smaller community than TEI
- Less documentation for CPU deployment
- Would need testing to confirm Qwen3-Embedding-0.6B works
- If Qwen3 unsupported, would require different model = re-index

---

### Option 4: Ollama Embedding

**What it is:** Ollama's embedding capability using `qwen3-embedding:0.6b` GGUF model. Runs on llama.cpp backend.

**Model support:** Has `qwen3-embedding:0.6b` in its library. OpenAI-compatible `/v1/embeddings` endpoint available.

**Pros:**
- Same model (Qwen3-Embedding), likely no re-index needed
- Simple deployment (Ollama already containerized)
- CPU-native (llama.cpp)
- OpenAI-compatible API

**Cons:**
- Ollama is primarily an LLM chat server; embedding is secondary
- GGUF quantization may produce different embeddings than FP32 vLLM (re-index risk)
- Less optimized for pure embedding workloads (no dynamic batching)
- Resource overhead of running full Ollama stack for just embeddings
- Performance characteristics for embedding poorly documented

---

### Option 5: Keep vLLM on GPU (Status Quo)

**Pros:**
- Working, proven, fast
- No migration risk
- GPU utilization is technically "free" (the VRAM would otherwise be idle)

**Cons:**
- 5.2 GB VRAM wasted on low-throughput workload
- GPU 4 is constrained (8.8/16.3 GB used)
- vLLM is overkill for embedding (documented <40% GPU utilization for embedding tasks)
- Blocks potential use of GPU 4 for other workloads

---

## Analysis

### Question 1: Does FastEmbed support Qwen3-Embedding-0.6B?

**No, not natively.** FastEmbed has a fixed list of ~25 supported models, none of which are Qwen3. However, custom model support exists via `add_custom_model()` with ONNX models, and a community uint8 ONNX conversion exists at `electroglyph/Qwen3-Embedding-0.6B-onnx-uint8`. This path is viable but requires custom setup and produces slightly different embeddings.

### Question 2: Performance difference (GPU vLLM vs CPU)?

| Metric | GPU (vLLM, RTX 5070 Ti) | CPU (TEI, EPYC 7663 est.) |
|--------|------------------------|---------------------------|
| Single embedding latency | ~2-5ms | ~15-30ms (FP32) |
| Batch of 20 embeddings | ~10-20ms | ~300-600ms |
| Knowledge re-index (2220 pts) | ~2-3 min | ~5-10 min |
| Max throughput (sustained) | ~5000+ emb/sec | ~100-300 emb/sec |

For Athanor's actual workload (sporadic single queries, occasional batch indexing), the CPU latency difference is negligible. The context enrichment target is <300ms total (1 embedding + 3 parallel Qdrant queries); a 15-30ms embedding on CPU still fits well within budget.

### Question 3: Deployment approach?

**TEI on CPU** is the clear winner for deployment simplicity:

```yaml
# docker-compose.yml for TEI CPU
services:
  tei-embedding:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.9
    container_name: tei-embedding
    ports:
      - "8001:80"
    volumes:
      - /mnt/vault/models/Qwen3-Embedding-0.6B:/data/Qwen3-Embedding-0.6B
    command: --model-id /data/Qwen3-Embedding-0.6B --dtype float32
    restart: unless-stopped
    environment:
      - TZ=America/Chicago
    deploy:
      resources:
        limits:
          cpus: '16'
          memory: 4G
```

No code changes needed in agents or LiteLLM config. Same port (8001), same API, same model.

### Question 4: Re-indexing Qdrant?

**No re-index needed if using the same model (Qwen3-Embedding-0.6B) in FP32.** TEI running Qwen3-Embedding-0.6B in FP32 will produce identical embeddings to vLLM running the same model. The model weights are the same; only the inference engine differs. Floating-point rounding differences between backends are negligible for cosine similarity.

**Re-index IS needed if:**
- Switching to a different model (e.g., bge-large-en-v1.5)
- Using quantized inference (uint8/int8) that changes embedding values
- Using a GGUF conversion (Ollama) that may alter precision

### Question 5: Alternatives to FastEmbed?

| Solution | Qwen3-0.6B Support | OpenAI API | CPU Native | Server Component | Maturity |
|----------|-------------------|------------|------------|-----------------|----------|
| **TEI** | Yes (explicit) | Yes (/v1) | Yes | Yes (built-in) | High |
| FastEmbed | Custom only | No (library) | Yes (ONNX) | No (need wrapper) | Medium |
| Infinity | Uncertain | Yes | Yes | Yes | Medium |
| Ollama | Yes (GGUF) | Yes (/v1) | Yes | Yes | High |
| vLLM CPU | Yes | Yes (/v1) | Partial | Yes | High |

---

## Recommendation

**Deploy HuggingFace TEI (Text Embeddings Inference) on CPU on Node 1.**

Rationale:
1. **Same model, zero re-indexing.** TEI explicitly supports Qwen3-Embedding-0.6B and will produce identical FP32 embeddings.
2. **Drop-in replacement.** Same port, same OpenAI-compatible API. Zero code changes in agents or LiteLLM.
3. **Purpose-built.** TEI is designed specifically for embedding inference, unlike vLLM (general LLM) or Ollama (chat-focused).
4. **Adequate performance.** 15-30ms per embedding on EPYC is well within Athanor's latency budget.
5. **Frees 5.2 GB VRAM.** GPU 4 drops from 8.8 GB to 3.6 GB used, opening room for future workloads.
6. **Minimal operational overhead.** Single Docker container, well-maintained by HuggingFace, no custom code.

**Migration plan:**
1. Deploy TEI CPU container on Node 1 on a test port (e.g., 8002)
2. Verify embeddings match by comparing a sample against vLLM output
3. Run `index-knowledge.py` against TEI to verify batch indexing works
4. Switch port to 8001 (or update LiteLLM config)
5. Stop vLLM-embedding container
6. Monitor agent context enrichment latency for a few days

**Risk:** The one concern is MKL optimization on AMD EPYC. Intel MKL is optimized for Intel CPUs; on AMD, it may fall back to a slower code path. OpenBLAS or BLIS would be better for AMD. TEI's candle backend uses MKL by default. If performance is unexpectedly poor, the fallback is to use the ONNX backend instead (`cargo install --path router -F ort`), though this would require building from source. The pre-built CPU Docker image should still be adequate for Athanor's low-throughput workload even without optimal BLAS tuning.

---

## Sources

- [TEI Supported Models and Hardware](https://huggingface.co/docs/text-embeddings-inference/en/supported_models)
- [TEI Quick Tour (deployment examples)](https://huggingface.co/docs/text-embeddings-inference/en/quick_tour)
- [TEI GitHub Repository](https://github.com/huggingface/text-embeddings-inference)
- [TEI Issue #667: Qwen3-0.6B on CPU fix](https://github.com/huggingface/text-embeddings-inference/issues/667)
- [Qwen3-Embedding-0.6B Model Card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [FastEmbed Supported Models](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- [FastEmbed GitHub](https://github.com/qdrant/fastembed)
- [FastEmbed Custom Model: Qwen3-Embedding-0.6B-onnx-uint8](https://huggingface.co/electroglyph/Qwen3-Embedding-0.6B-onnx-uint8)
- [CPU Optimized Embeddings with Optimum Intel (benchmark data)](https://huggingface.co/blog/intel-fast-embedding)
- [Infinity Embedding Server](https://github.com/michaelfeil/infinity)
- [Ollama qwen3-embedding](https://ollama.com/library/qwen3-embedding)
- [vLLM Low GPU Utilization with Embedding (Issue #27479)](https://github.com/vllm-project/vllm/issues/27479)
