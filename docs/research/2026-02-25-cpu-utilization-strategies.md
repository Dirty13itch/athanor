# CPU Utilization Strategies for AI Workloads

**Date:** 2026-02-25
**Status:** Research complete
**Author:** Claude (research agent)
**Scope:** Exhaustive analysis of CPU utilization opportunities across Athanor's 4-node homelab

---

## Context

Athanor's 4 nodes collectively provide 112 CPU cores / 216 threads, yet CPU utilization across all nodes sits below 10% on average. All AI inference runs on 7 GPUs via vLLM, leaving massive CPU capacity idle. This research identifies every viable way to put those CPUs to work for AI and infrastructure workloads.

### Hardware Summary

| Node | CPU | Cores/Threads | Arch | AVX-512 | RAM | Memory BW (theoretical) | Memory BW (practical) |
|------|-----|--------------|------|---------|-----|------------------------|----------------------|
| **Foundry** (Node 1) | EPYC 7663 | 56C/112T | Zen 3 (Milan) | Yes | 224 GB DDR4-3200 | 204.8 GB/s (8-ch) | ~170-180 GB/s |
| **Workshop** (Node 2) | TR 7960X | 24C/48T | Zen 4 (Storm Peak) | Yes | 128 GB DDR5-5600 | 179.2 GB/s (4-ch) | ~140-150 GB/s |
| **VAULT** | Ryzen 9950X | 16C/32T | Zen 5 (Granite Ridge) | Yes | 128 GB DDR5-5600 | 89.6 GB/s (2-ch) | ~70-80 GB/s |
| **DEV** | i7-13700K | 16C/24T | Raptor Lake | No* | 64 GB DDR5 | 89.6 GB/s (2-ch) | ~70-80 GB/s |

*Intel disabled AVX-512 on Raptor Lake via microcode. Some BIOSes can re-enable it on P-cores, but this is unsupported and may cause instability.

**Memory bandwidth is the primary bottleneck for CPU LLM inference** (token generation is memory-bound). The EPYC 7663's 8-channel DDR4 gives it the highest practical bandwidth despite using older DDR4 technology.

---

## 1. CPU LLM Inference

### 1.1 Frameworks

#### llama.cpp
The dominant CPU inference framework. Written in C/C++ with hand-tuned SIMD kernels for AVX, AVX2, AVX-512, and AMX. Supports all GGUF quantization types.

- **K-quants** (Q4_K_M, Q5_K_M, Q6_K): Best CPU performance, fully optimized for AVX-512
- **I-quants** (IQ4_XS, IQ3_XXS): Functional on CPU but slower than K-quants of comparable size (marked with a "turtle" in the feature matrix)
- **Q8_0**: Good balance of speed and quality on CPU
- **Flash Attention**: Supported on CPU backend
- **NUMA awareness**: `--numa distribute` or `--numa isolate` for multi-die CPUs like EPYC
- **Build flags**: `cmake -DGGML_AVX512=ON -DGGML_AVX512_VNNI=ON` for maximum AVX-512 utilization
- **Server mode**: `llama-server` provides OpenAI-compatible API with continuous batching

Source: https://github.com/ggml-org/llama.cpp

#### ik_llama.cpp
Fork of llama.cpp with additional CPU optimizations:
- Much faster CPU prompt processing for all non-interleaved quants
- CPU Flash Attention implementation with improved token generation
- Proprietary IQ*_KT quantization types (trellis-based) designed for reasonable CPU performance
- Tensor overrides for fine-grained CPU/GPU hybrid control
- "Graph" split mode for multi-GPU setups

Source: https://github.com/ikawrakow/ik_llama.cpp

#### llamafile (Mozilla)
Wraps llama.cpp with tinyBLAS, a custom matrix multiplication library with superior SIMD optimization:
- **2.8x faster on Zen 4 / AVX-512** for prompt processing (Threadripper Pro benchmarks)
- **5x faster float16 inference** on Intel Alderlake
- Achieves 810 GFLOPS vs Intel MKL's 295 GFLOPS on equivalent matrices
- Q8_0 weights see 500% speedup in prompt eval
- Single-file executables, zero dependencies

Source: https://justine.lol/matmul/

#### ONNX Runtime
Microsoft's inference runtime with CPU optimizations:
- S8S8 QDQ quantization (default, balances speed and accuracy)
- AVX-512 VNNI acceleration for int8 operations
- Dynamic quantization ideal for transformer models
- Static shape compilation for maximum throughput
- No LLM-specific continuous batching

Source: https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html

#### Optimum Intel (OpenVINO)
HuggingFace integration for Intel-optimized inference:
- Works on AMD CPUs too (using generic CPU backend)
- Supports LLM inference via `OVModelForCausalLM`
- Weight quantization: fp16, 8-bit, 4-bit compression
- Static shape optimization for batch inference
- Intel-specific optimizations (AMX, VNNI) provide best results on Intel hardware
- Models >1B parameters automatically quantized to int8 on export

Source: https://huggingface.co/docs/optimum/en/intel/inference

### 1.2 Estimated CPU Inference Performance

Token generation speed (tokens/second) for Q4_K_M quantization on llama.cpp with AVX-512, measured during autoregressive decoding:

| Model Size | EPYC 7663 (56C) | TR 7960X (24C) | Ryzen 9950X (16C) | i7-13700K (16C) |
|-----------|-----------------|----------------|-------------------|-----------------|
| **0.5B** | ~80-120 tok/s | ~70-100 tok/s | ~60-90 tok/s | ~50-70 tok/s |
| **1.5B** | ~50-80 tok/s | ~40-60 tok/s | ~35-50 tok/s | ~25-40 tok/s |
| **3B** | ~30-50 tok/s | ~25-40 tok/s | ~20-35 tok/s | ~15-25 tok/s |
| **7B** | ~15-25 tok/s | ~12-20 tok/s | ~10-15 tok/s | ~8-12 tok/s |
| **14B** | ~8-14 tok/s | ~6-10 tok/s | ~5-8 tok/s | ~4-6 tok/s |
| **32B** | ~3-6 tok/s | ~2-4 tok/s | ~2-3 tok/s | ~1.5-2.5 tok/s |

**Prompt processing** (prefill) is 5-20x faster than generation due to parallelism across tokens.

**Key insight**: The EPYC 7663's 8-channel memory bandwidth (204.8 GB/s theoretical) makes it the strongest CPU inference platform in the cluster. Token generation is memory-bandwidth-bound: `tok/s ~ memory_bandwidth / model_size_bytes`. For a 7B Q4_K_M model (~4.1 GB), the theoretical maximum is ~50 tok/s on the EPYC, but overhead from KV cache reads, attention computation, and system overhead brings it to the 15-25 range.

**Note on accuracy**: These estimates are derived from community benchmarks and the memory-bandwidth model. Actual performance should be validated with `llama-bench` on each node. Numbers could be 20-30% higher with llamafile/tinyBLAS optimizations or ik_llama.cpp.

### 1.3 Viable Use Cases for CPU LLM Inference

| Use Case | Model Size | Speed Needed | Best Node | Feasible? |
|----------|-----------|-------------|-----------|-----------|
| Interactive chat (primary) | 32B+ | >20 tok/s | -- | No, use GPU |
| Background summarization | 7B-8B | >5 tok/s | Node 1 (EPYC) | **Yes** |
| Intent classification | 1.5B-3B | >10 tok/s | Any node | **Yes** |
| Content tagging/extraction | 3B-7B | >5 tok/s | Node 1/2 | **Yes** |
| Tool call routing | 0.5B-1.5B | >20 tok/s | Any node | **Yes** |
| Document QA (non-interactive) | 7B | >5 tok/s | Node 1 | **Yes** |
| Agent self-reflection | 7B | >5 tok/s | Node 1 | **Yes** |
| Fallback chat (GPU down) | 7B | >8 tok/s | Node 1/2 | **Marginal** |
| Fine-tuning evaluation | 3B-7B | >3 tok/s | Node 1 | **Yes** |
| Synthetic data generation | 7B | >5 tok/s | Node 1 | **Yes** |

---

## 2. CPU Embedding (Free GPU 4)

### 2.1 Current State

GPU 4 (RTX 5070 Ti, 16 GB) runs vLLM-embedding at 0.40 memory utilization for a ~1.2 GB embedding model. This wastes ~14.8 GB of VRAM. The embedding workload is bursty: queries come during chat/search, with long idle periods.

### 2.2 CPU Embedding Options

#### FastEmbed (Qdrant)
- Uses ONNX Runtime internally, optimized for CPU
- Supports BGE, E5, Nomic, GTE, and multilingual models
- Built-in data parallelism for batch encoding
- Supports dense, sparse (SPLADE++), late interaction (ColBERT), and image embeddings
- Reranker support included (cross-encoder models)
- Lightweight: no PyTorch dependency
- Install: `pip install fastembed`

Source: https://github.com/qdrant/fastembed

#### sentence-transformers with ONNX/OpenVINO Backend
- Export models to ONNX: `backend="onnx"`
- Dynamic int8 quantization: `export_dynamic_quantized_onnx_model()`
- AVX-512 VNNI optimization targets: `"avx512"`, `"avx512_vnni"`
- ~3x speedup for short texts (<128 tokens) with int8 quantization
- OpenVINO backend available: `backend="openvino"` (best on Intel, works on AMD)
- Longer texts may not see the same speedup due to compute overhead

Source: https://sbert.net/docs/sentence_transformer/usage/efficiency.html

### 2.3 Expected CPU Embedding Performance

For a typical embedding model (384-1024 dim, ~100M parameters) on ONNX Runtime with int8 quantization:

| Text Length | EPYC 7663 (16 cores) | Ryzen 9950X (8 cores) | GPU (5070 Ti) |
|-------------|----------------------|----------------------|---------------|
| 32 tokens | ~800-1500 emb/s | ~400-800 emb/s | ~3000-5000 emb/s |
| 128 tokens | ~300-600 emb/s | ~150-300 emb/s | ~1500-2500 emb/s |
| 512 tokens | ~80-150 emb/s | ~40-80 emb/s | ~500-800 emb/s |

**Verdict**: CPU embedding at 300-600 embeddings/sec for typical RAG queries (128 tokens) is more than sufficient. Athanor's actual embedding load is probably <10 queries/second peak. **Moving embedding to CPU is the single highest-impact change in this document** because it frees GPU 4 (16 GB VRAM) for:
- A second vLLM instance (7B-14B model)
- Dedicated whisper/STT processing
- Additional creative compute
- Batch inference jobs

### 2.4 Implementation Plan

```python
# FastEmbed service on Node 1
from fastembed import TextEmbedding

model = TextEmbedding(
    model_name="BAAI/bge-small-en-v1.5",  # or current model
    providers=["CPUExecutionProvider"],
    threads=16  # Dedicate 16 of 56 cores
)

# Wrap in FastAPI for OpenAI-compatible endpoint
@app.post("/v1/embeddings")
async def embed(request: EmbedRequest):
    embeddings = list(model.embed(request.input))
    return {"data": [{"embedding": e.tolist()} for e in embeddings]}
```

Alternatively, use Qdrant's built-in FastEmbed integration directly, or point LiteLLM at a CPU embedding endpoint.

---

## 3. CPU Reranking for RAG Quality

### 3.1 What It Does

Cross-encoder reranking takes the top-N retrieved documents from vector search and re-scores them using a more powerful model that sees both the query and document together. This dramatically improves retrieval precision.

### 3.2 CPU Performance

Cross-encoder reranking is a classification task (input: query + document, output: relevance score). On CPU with ONNX int8 quantization:

| Candidates | EPYC 7663 (4 cores) | Latency Budget |
|-----------|---------------------|----------------|
| 20 docs | ~50-100 ms | Acceptable (<200ms) |
| 50 docs | ~120-250 ms | Acceptable |
| 100 docs | ~250-500 ms | Marginal |

### 3.3 Implementation

FastEmbed includes reranker support:
```python
from fastembed import TextCrossEncoder

reranker = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
scores = list(reranker.rerank(query, documents))
```

Or use sentence-transformers:
```python
from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", backend="onnx")
scores = model.predict([(query, doc) for doc in documents])
```

**Impact**: Reranking the top 20-50 Qdrant results before passing to the LLM can improve answer quality by 10-30% on retrieval benchmarks, at negligible CPU cost (~4 cores, ~100ms latency).

---

## 4. Speculative Decoding (CPU Draft + GPU Target)

### 4.1 How It Works

Speculative decoding uses a small "draft" model to generate candidate tokens, then the large "target" model verifies them in a single forward pass. If the draft model predicts correctly, multiple tokens are validated at once, reducing the number of expensive GPU forward passes.

Typical speedup: **1.5-3x** for interactive generation, depending on:
- Draft-target agreement rate (80% with similar model families)
- Draft model speed relative to target
- Number of speculative tokens (typically 3-8)

Source: https://huggingface.co/blog/assisted-generation

### 4.2 vLLM Speculative Decoding

vLLM supports speculative decoding with these methods:
1. **Draft model**: Small model generates candidates, target verifies
2. **N-gram matching**: Uses prompt n-grams as candidates (no draft model needed)
3. **MLP speculators**: Trained lightweight predictors
4. **EAGLE**: Enhanced draft model architecture

Configuration:
```python
llm = LLM(
    model="Qwen/Qwen3-32B-AWQ",
    speculative_model="Qwen/Qwen2.5-0.5B",
    num_speculative_tokens=5,
    speculative_draft_tensor_parallel_size=1,
)
```

**Critical limitation**: vLLM does NOT currently support running the draft model on CPU while the target runs on GPU. Both models must be on GPU. The `speculative_draft_tensor_parallel_size=1` flag puts the draft on a single GPU, but not on CPU.

Source: https://docs.vllm.ai (spec_decode feature docs), https://github.com/vllm-project/vllm/issues/4630

### 4.3 llama.cpp Speculative Decoding

llama.cpp supports CPU-based speculative decoding natively:
```bash
llama-speculative \
  --model large-model.gguf \
  --model-draft small-draft.gguf \
  --draft 8 \
  --threads 56
```

However, this requires running the TARGET model on llama.cpp too (losing vLLM's continuous batching, which is essential for concurrent agent requests).

### 4.4 N-gram Speculation (No Draft Model)

The most practical option for Athanor today. vLLM's n-gram matching uses the prompt itself to predict next tokens:
```python
llm = LLM(
    model="Qwen/Qwen3-32B-AWQ",
    speculative_model="[ngram]",
    num_speculative_tokens=5,
    ngram_prompt_lookup_max=4,
)
```

This uses CPU for the n-gram lookup (trivial compute) and can provide 1.2-1.5x speedup on repetitive or structured outputs. Zero additional memory or model required.

### 4.5 Verdict

- **N-gram speculation in vLLM**: Deploy now, free speedup, trivial CPU usage
- **CPU draft model in vLLM**: Not supported yet. Monitor vLLM roadmap.
- **CPU draft in llama.cpp**: Possible but sacrifices continuous batching. Not recommended for production.
- **Future**: When vLLM adds CPU draft model support, a 0.5B Qwen model on 8 EPYC cores + 32B target on 4 GPUs could yield 1.5-2x speedup.

---

## 5. Data Processing and ETL on CPU

### 5.1 Tokenization

HuggingFace tokenizers (Rust-based) achieve ~100K-500K tokens/second on a single CPU core. Tokenization is never a bottleneck, but can be parallelized across cores for batch processing.

### 5.2 Document Processing Pipeline

For knowledge base ingestion (Qdrant), all steps can run on CPU:

1. **Document parsing**: unstructured, PyMuPDF, beautifulsoup4 (~1-10 docs/sec depending on complexity)
2. **Text chunking**: langchain text splitters, semantic chunking (~10K chunks/sec)
3. **Embedding**: FastEmbed on CPU (~300-600 emb/sec for 128-token chunks)
4. **Optional reranking**: Cross-encoder quality scoring (~200-500 scores/sec)
5. **Qdrant upsert**: Batch insertion (~1000-5000 points/sec)

A full pipeline on 16 EPYC cores can process ~100-300 documents/minute (depending on document length), which exceeds any realistic ingestion rate.

### 5.3 Text Preprocessing

CPU-native tasks that currently have no dedicated allocation:
- HTML stripping and cleaning
- Language detection
- PII detection/redaction
- Deduplication (MinHash, SimHash)
- Metadata extraction
- Structured data extraction (regex, spaCy NER)

All of these are CPU-bound and can run on spare cores.

---

## 6. Build Infrastructure

### 6.1 Distributed Compilation (distcc)

distcc distributes C/C++ compilation across networked machines. Key facts:
- Machines need compatible compilers, not shared filesystems
- "Pump mode" (distcc 3.0+) distributes preprocessing too
- Typical speedup: **2.6x with 3 machines**, near-linear scaling
- Works with `make -j` for parallel builds

Source: https://github.com/distcc/distcc

**Athanor setup**: 4-node distcc cluster with ~112 compiler jobs:
```bash
# On each node
sudo apt install distcc
distccd --daemon --allow 192.168.1.0/24

# On build node
export DISTCC_HOSTS="192.168.1.244/56 192.168.1.225/24 192.168.1.203/16 192.168.1.215/16"
make -j112 CC=distcc CXX=distcc
```

**Use cases**:
- Building vLLM from source (significant compile time)
- Building PyTorch wheels
- Compiling llama.cpp with custom flags
- Building Docker images with compiled dependencies

**Impact**: Low (builds are infrequent), but saves 30-60 minutes per major build. Setup cost: ~30 minutes.

### 6.2 Docker Image Builds

Node 1's EPYC with 56 cores can dramatically speed up multi-stage Docker builds. Enable BuildKit parallelism:
```bash
DOCKER_BUILDKIT=1 docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t image .
```

### 6.3 ccache

Compiler cache across all nodes via NFS-shared cache directory:
```bash
# Shared ccache on NFS
export CCACHE_DIR=/mnt/vault/data/ccache
export CCACHE_MAXSIZE=10G
```

Combines with distcc for distributed cached builds.

---

## 7. Testing and CI/CD

### 7.1 Gitea Actions

Self-hosted CI/CD compatible with GitHub Actions workflows. Runs `act_runner` as the execution daemon.

**Setup**:
1. Deploy Gitea on VAULT (lightweight Git hosting)
2. Deploy `act_runner` on each node
3. Mirror Athanor repo to local Gitea
4. Run tests, linting, builds on every push

**Resource allocation per runner**:
- Node 1: 8-16 cores (largest workloads, Docker builds)
- Node 2: 4-8 cores (lighter tests)
- DEV: 4-8 cores (development tests)

Source: https://docs.gitea.com/usage/actions/overview

### 7.2 Parallel Test Execution

Python test suites can parallelize across cores:
```bash
# pytest-xdist: distribute tests across workers
pytest -n 16 tests/  # Use 16 cores

# pytest-parallel for thread-based parallelism
pytest --workers 16 tests/
```

### 7.3 Pre-commit Hooks

CPU-bound linting and formatting across all cores:
- `ruff` (Python linting): Already fast, but parallelizes across cores
- `mypy` (type checking): Daemon mode + parallel workers
- `black` (formatting): Processes files in parallel

---

## 8. Model Fine-Tuning on CPU

### 8.1 Full Fine-Tuning

Not practical on CPU for models above ~100M parameters. Training is compute-bound (matrix multiplications during backpropagation), and CPUs are orders of magnitude slower than GPUs for this.

### 8.2 LoRA/QLoRA

For small models (<3B parameters), CPU LoRA training is theoretically possible but extremely slow:
- 1.5B model LoRA training on 56 EPYC cores: ~0.1-0.5 samples/sec (vs ~10-50 samples/sec on a single GPU)
- A training run that takes 1 hour on GPU would take 20-500 hours on CPU

**Verdict**: Not recommended. Use GPU for all training.

### 8.3 Dataset Preparation (CPU-appropriate)

Pre-training and fine-tuning dataset preparation is CPU-bound and can leverage all cores:
- **Tokenization**: Convert text to token IDs (~500K tokens/sec/core)
- **Filtering**: Quality scoring, deduplication, language detection
- **Formatting**: Convert to chat template, add system prompts
- **Validation**: Check token lengths, verify formatting
- **Evaluation**: Run inference on test set (using CPU LLM for small models)

On 56 EPYC cores, dataset preparation that takes hours on a single core completes in minutes.

---

## 9. Classical ML and Analysis

### 9.1 Anomaly Detection on Infrastructure Metrics

Use scikit-learn, stumpy (matrix profiles), or Prophet to analyze Prometheus time series:

**Targets**:
- GPU utilization patterns (detect degraded performance)
- NFS latency spikes (predict stale handles before they cause failures)
- Container restart frequency (detect flapping services)
- Memory usage trends (predict OOM before it happens)
- Disk I/O patterns on VAULT (predict array issues)

**Implementation**:
```python
# Isolation Forest for anomaly detection
from sklearn.ensemble import IsolationForest
import requests

# Query Prometheus
resp = requests.get("http://192.168.1.203:9090/api/v1/query_range", params={
    "query": "node_filesystem_avail_bytes",
    "start": "2026-02-24T00:00:00Z",
    "end": "2026-02-25T00:00:00Z",
    "step": "60"
})

# Train anomaly detector
clf = IsolationForest(n_estimators=100, contamination=0.01, n_jobs=-1)
clf.fit(time_series_data)
anomalies = clf.predict(new_data)
```

**Resource**: 2-4 cores, runs as cron (every 5-15 minutes) or daemon.

### 9.2 Time Series Forecasting

Prophet or statsforecast for capacity planning:
- Predict VAULT array fill rate (currently 89%)
- Forecast GPU utilization trends
- Predict peak usage times for agent load

### 9.3 Log Analysis

scikit-learn clustering on log patterns:
- TF-IDF vectorization of log messages
- HDBSCAN clustering to identify anomalous log patterns
- Automated log classification (error categories)

### 9.4 User Behavior Analysis

When agent usage data accumulates:
- Collaborative filtering for content recommendations (media agent)
- Usage pattern clustering (which agents at what times)
- Session length prediction

---

## 10. Cryptography and Security

### 10.1 Hardware Acceleration

The EPYC 7663 includes:
- **AES-NI**: Hardware AES encryption/decryption
- **SHA extensions**: Hardware SHA-256/SHA-512
- **SM3/SM4**: Chinese cryptographic standards (if needed)
- **CLMUL**: Carry-less multiplication for GCM mode

### 10.2 Use Cases

- **NFS encryption**: Encrypt NFS traffic between nodes (currently unencrypted on LAN)
- **Backup encryption**: Encrypt backups at rest on VAULT
- **TLS termination**: Handle HTTPS for all services via nginx/Caddy
- **VPN**: WireGuard uses minimal CPU but benefits from hardware crypto (if remote access is ever needed)

**Impact**: Low incremental benefit (encryption on modern CPUs is already fast), but enables security improvements at negligible CPU cost.

---

## 11. Storage and Caching

### 11.1 VAULT Optimization

The Ryzen 9950X on VAULT is primarily serving NFS and running 13 containers. Opportunities:
- **Redis maxmemory increase**: Currently 512 MB. Could expand to 2-4 GB for more aggressive caching of GWT workspace, agent state, and session data.
- **Qdrant memory mapping**: Qdrant can map collections into RAM for faster search. With 128 GB RAM, dedicate more to Qdrant mmap.
- **NFS read-ahead tuning**: Increase NFS read-ahead buffer for model loading.

### 11.2 Node 1 RAM Disk

224 GB RAM on Node 1 is mostly unused. Options:
- **tmpfs for inference scratch**: Mount a 32-64 GB tmpfs for temporary model files, KV cache overflow
- **Model preloading**: Load frequently-used GGUF models into page cache

---

## 12. Distributed Compute Frameworks

### 12.1 Ray Cluster

Ray can distribute Python workloads across all 4 nodes. Each node runs a Ray worker with its allocated CPU cores.

**Use cases for Athanor**:
- Batch embedding of large document sets
- Parallel data processing pipelines
- Distributed hyperparameter tuning (if fine-tuning)
- Batch inference with llama.cpp across nodes

**Setup**:
```bash
# Node 1 (head)
ray start --head --port=6379 --num-cpus=40

# Node 2 (worker)
ray start --address=192.168.1.244:6379 --num-cpus=16

# VAULT (worker)
ray start --address=192.168.1.244:6379 --num-cpus=8

# DEV (worker, optional)
ray start --address=192.168.1.244:6379 --num-cpus=8
```

Source: https://docs.ray.io

**Verdict**: Overkill for current workloads. Deploy when batch processing demands exceed single-node capacity. The setup overhead is justified only if running regular distributed jobs.

### 12.2 Dask

Alternative to Ray for data-focused distributed computing. Better integration with pandas/numpy ecosystems. Similar multi-node architecture.

**Verdict**: Choose Ray or Dask when needed, not both. Ray has better ML ecosystem integration.

---

## 13. Additional CPU Workloads

### 13.1 Web Scraping / Data Collection

For knowledge base expansion, web scraping is CPU and I/O bound:
- Scrapy or httpx-based crawlers on Node 1
- 8-16 concurrent workers
- Feed scraped content into document processing pipeline

### 13.2 Image Preprocessing

CPU-based image operations for the creative pipeline:
- Thumbnail generation for ComfyUI outputs
- Image metadata extraction (EXIF)
- Image deduplication (perceptual hashing)
- Batch image resizing/conversion

### 13.3 Media Transcoding (Plex)

VAULT's Ryzen 9950X handles Plex transcoding. The CPU can handle 3-5 simultaneous 1080p software transcodes, though hardware transcoding (Arc A380 QuickSync) is preferred.

### 13.4 Piper TTS (Already Deployed)

wyoming-piper on VAULT CPU is already using a few cores for text-to-speech. This is appropriately placed on CPU (TTS models are small and CPU-efficient).

### 13.5 Whisper STT on CPU (Fallback)

Currently wyoming-whisper runs on GPU 4. A CPU fallback using faster-whisper with CTranslate2:
- `float16` compute on EPYC: ~2-5x slower than GPU
- Useful as failover if GPU 4 is reassigned
- `faster-whisper-large-v3` on 16 EPYC cores: ~0.3-0.5x realtime (i.e., 10 seconds of audio takes 20-30 seconds)
- Smaller models (`small`, `medium`) achieve near-realtime on CPU

---

## 14. What NOT to Do on CPU

| Workload | Why Not |
|----------|---------|
| Primary chat inference (32B+) | Too slow for interactive use. vLLM on GPU is 10-50x faster. |
| Image generation | CPU Stable Diffusion takes 5-30 minutes per image. Unusable. |
| Video generation | Hours per clip on CPU. Absurd. |
| Full model training | 20-500x slower than GPU. Not practical. |
| LoRA fine-tuning (>3B) | Still 10-50x slower than GPU. Use GPU. |
| Real-time STT (primary) | CPU can't match GPU latency for voice interaction. Keep on GPU. |
| Large batch embedding (>10K/min) | CPU can handle most workloads but GPU is needed for very high throughput. |

---

## Recommended CPU Allocation Plan

### Node 1: EPYC 7663 (56 cores / 112 threads)

| Allocation | Cores | Purpose | Priority |
|-----------|-------|---------|----------|
| **FastEmbed CPU embedding** | 16 | Replace vLLM-embedding on GPU 4. ONNX Runtime + AVX-512. | P0 (do first) |
| **CPU reranker** | 4 | Cross-encoder reranking for RAG quality improvement. | P0 |
| **llama.cpp 7B auxiliary** | 16 | Background tasks: summarization, tagging, classification, extraction. Qwen2.5-7B-Q4_K_M. | P1 |
| **Document processing pipeline** | 4 | Chunking, preprocessing, metadata extraction for knowledge ingestion. | P1 |
| **Anomaly detection** | 2 | scikit-learn on Prometheus metrics, cron every 5 min. | P2 |
| **CI runner** | 8 (burst) | Gitea Actions runner for builds and tests. Idle most of the time. | P3 |
| **System + Docker + vLLM overhead** | 6 | OS, container runtime, existing services. | Always |
| **Total** | **56** | | |

**Key outcome**: GPU 4 freed (16 GB VRAM) for a second vLLM instance, dedicated STT, or other GPU workloads.

### Node 2: TR 7960X (24 cores / 48 threads)

| Allocation | Cores | Purpose | Priority |
|-----------|-------|---------|----------|
| **llama.cpp 7B fallback** | 8 | Secondary chat endpoint. Qwen2.5-7B-Q4_K_M. Provides redundancy if Node 1 vLLM goes down. | P2 |
| **CI runner** | 4 (burst) | Lighter test workloads. | P3 |
| **Dashboard + ComfyUI overhead** | 4 | Existing services. | Always |
| **System + Docker** | 4 | OS, container runtime. | Always |
| **Reserve** | 4 | Burst capacity for creative pipeline, builds. | -- |
| **Total** | **24** | | |

### VAULT: Ryzen 9950X (16 cores / 32 threads)

| Allocation | Cores | Purpose | Priority |
|-----------|-------|---------|----------|
| **NFS + storage** | 4 | File serving, array management. | Always |
| **Containers (13)** | 4 | Plex, Qdrant, Neo4j, Redis, Prometheus, etc. | Always |
| **Piper TTS** | 2 | wyoming-piper CPU TTS. | Always |
| **Enhanced Redis caching** | 1 | Expand maxmemory to 2-4 GB. | P2 |
| **Media processing** | 2 | Plex transcoding fallback, Sonarr/Radarr processing. | On-demand |
| **System** | 3 | OS, monitoring. | Always |
| **Total** | **16** | | |

### DEV: i7-13700K (16 cores / 24 threads)

| Allocation | Cores | Purpose | Priority |
|-----------|-------|---------|----------|
| **Development workstation** | 8 | IDE, terminals, Docker, WSL2. | Always |
| **Local testing** | 4 | pytest, linting, type checking. | On-demand |
| **CI runner** | 4 (burst) | Local development testing. | P3 |
| **Total** | **16** | | |

---

## Implementation Priority

### Phase 1: Free GPU 4 (Week 1)
1. Deploy FastEmbed CPU embedding service on Node 1
2. Deploy CPU reranker service on Node 1
3. Update LiteLLM routing to use CPU embedding endpoint
4. Stop vLLM-embedding on GPU 4
5. Validate embedding quality and latency

### Phase 2: CPU Intelligence (Week 2)
6. Deploy llama.cpp server on Node 1 with Qwen2.5-7B-Q4_K_M
7. Wire auxiliary LLM to agent framework for background tasks
8. Deploy n-gram speculative decoding in vLLM (config change only)

### Phase 3: Operations (Week 3-4)
9. Deploy anomaly detection daemon on Node 1
10. Set up Gitea + Gitea Actions for CI/CD
11. Configure distcc across all nodes
12. Deploy llama.cpp fallback on Node 2

### Phase 4: Optimization (Ongoing)
13. Tune CPU embedding model (try different models, quantization levels)
14. Expand anomaly detection to more metrics
15. Set up Ray cluster when batch workloads demand it
16. Monitor and rebalance CPU allocations based on actual usage

---

## Summary

| Strategy | Cores Used | Impact | Effort |
|----------|-----------|--------|--------|
| CPU embedding (free GPU 4) | 16 | **Very High** | Medium |
| CPU reranking | 4 | **High** | Low |
| llama.cpp auxiliary LLM | 16 | **High** | Medium |
| N-gram speculation in vLLM | 0 (trivial) | **Medium** | Very Low |
| Document processing pipeline | 4 | **Medium** | Low |
| Anomaly detection | 2 | **Medium** | Medium |
| CI/CD (Gitea Actions) | 8-16 (burst) | **Medium** | Medium |
| llama.cpp fallback chat | 8 | **Low-Medium** | Low |
| Distributed compilation | All (burst) | **Low** | Low |
| Dataset preparation | On-demand | **Low** (until fine-tuning) | Low |
| Ray/Dask cluster | Variable | **Low** (until needed) | High |

**Total cores put to active use: ~66 of 112 dedicated, remaining available for burst.** This takes overall CPU utilization from <5% to an estimated 20-40% sustained, with burst to 60-80% during active processing.

---

## Sources

- llama.cpp repository and wiki: https://github.com/ggml-org/llama.cpp
- ik_llama.cpp (optimized fork): https://github.com/ikawrakow/ik_llama.cpp
- llamafile tinyBLAS performance: https://justine.lol/matmul/
- FastEmbed (Qdrant): https://github.com/qdrant/fastembed
- sentence-transformers ONNX/OpenVINO efficiency: https://sbert.net/docs/sentence_transformer/usage/efficiency.html
- ONNX Runtime quantization: https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html
- Optimum Intel (OpenVINO): https://huggingface.co/docs/optimum/en/intel/inference
- vLLM speculative decoding: https://docs.vllm.ai (spec_decode feature docs)
- vLLM spec decode optimization tracker: https://github.com/vllm-project/vllm/issues/4630
- HuggingFace assisted generation: https://huggingface.co/blog/assisted-generation
- distcc distributed compilation: https://github.com/distcc/distcc
- Gitea Actions: https://docs.gitea.com/usage/actions/overview
- Ray distributed computing: https://docs.ray.io
- Intel Extension for PyTorch (retired): https://github.com/intel/intel-extension-for-pytorch
- Intel Neural Speed (archived): https://github.com/intel/neural-speed
- OPEA (Open Platform for Enterprise AI): https://opea-project.github.io
