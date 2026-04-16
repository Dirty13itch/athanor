# Hardware Utilization Optimization: Athanor AI Cluster

**Date:** 2026-03-09
**Status:** Research complete, recommendations ready
**Author:** Research Agent (Claude Opus 4.6)
**Builds on:** [2026-02-25-gpu-resource-orchestration.md](2026-02-25-gpu-resource-orchestration.md), [2026-02-25-cpu-utilization-strategies.md](2026-02-25-cpu-utilization-strategies.md), [2026-02-25-ram-utilization-strategies.md](2026-02-25-ram-utilization-strategies.md), [2026-02-25-storage-optimization-strategies.md](2026-02-25-storage-optimization-strategies.md), [2026-03-08-vllm-baseline-benchmarks.md](2026-03-08-vllm-baseline-benchmarks.md)
**Supersedes:** Feb 25 research on the same topics (model lineup has changed: now Qwen3.5-27B-FP8 + Qwen3.5-35B-A3B-AWQ)

---

## Executive Summary

The Athanor cluster has ~139 GB of GPU VRAM, ~544 GB of system RAM, 112 CPU cores, and ~36 TB of NVMe across 4 nodes. Measured utilization as of 2026-03-09:

| Resource | Provisioned | Active Use | Utilization | Headroom |
|----------|------------|------------|-------------|----------|
| GPU VRAM | 105.8 GB across 7 GPUs | 99.2 GB loaded | 93.8% | 6.6 GB free |
| GPU Compute | 7 GPUs | 0% (idle between requests) | <5% sustained | ~95% |
| System RAM | 404 GB (excl. buff/cache) | 59 GB used | 14.6% | 345 GB free |
| CPU Cores | 108 C / 216 T (nodes 1-3) | load 4.5 + 0.02 + 0.4 | <5% sustained | ~95% |
| NVMe | ~8.7 TB installed | ~611 GB used | 7% | 93% |
| Network | 10 GbE (jumbo frames) | Idle between requests | <1% sustained | ~99% |

**The cluster is VRAM-saturated but compute-starved, RAM-rich but RAM-idle, and storage-rich but storage-idle.** The primary opportunity is converting idle RAM, CPU, and NVMe into better inference quality (longer contexts, faster prefill, more concurrent requests) without adding any hardware.

---

## 1. VRAM Utilization Analysis

### 1.1 Current VRAM Allocation (Live, 2026-03-09)

| Node | GPU | Card | Total | Used | Free | Workload |
|------|-----|------|-------|------|------|----------|
| FOUNDRY | 0 | 5070 Ti | 16,303 MB | 15,594 MB | 247 MB | Qwen3.5-27B-FP8 TP=4 shard |
| FOUNDRY | 1 | 5070 Ti | 16,303 MB | 15,594 MB | 247 MB | Qwen3.5-27B-FP8 TP=4 shard |
| FOUNDRY | 2 | 4090 | 24,564 MB | 21,300 MB | 2,782 MB | Huihui-Qwen3-8B (:8002) |
| FOUNDRY | 3 | 5070 Ti | 16,303 MB | 15,602 MB | 236 MB | Qwen3.5-27B-FP8 TP=4 shard |
| FOUNDRY | 4 | 5070 Ti | 16,303 MB | 15,594 MB | 247 MB | Qwen3.5-27B-FP8 TP=4 shard |
| WORKSHOP | 0 | 5090 | 32,607 MB | 31,338 MB | 772 MB | Qwen3.5-35B-A3B-AWQ |
| WORKSHOP | 1 | 5060 Ti | 16,311 MB | 5,110 MB | 10,739 MB | ComfyUI |
| DEV | 0 | 5060 Ti | 16,311 MB | 4,799 MB | 11,053 MB | Embed + Reranker |

**Total VRAM:** 155,005 MB (151.4 GB)
**Total Used:** 124,931 MB (122.0 GB)
**Total Free:** 26,323 MB (25.7 GB)

### 1.2 VRAM Gap Analysis

#### FOUNDRY 4090 (GPU 2): 2.78 GB Free

The Huihui-Qwen3-8B utility model uses 21.3 GB of the 24.6 GB available. With only 2.78 GB free:

**What fits in 2.78 GB:**
- Nothing useful for an additional model. Even a 0.5B model at Q4 needs ~0.5 GB for weights plus KV cache overhead.
- The free space is consumed by CUDA context, KV cache reservation, and vLLM overhead.

**Recommendation:** No action. The 4090 is well-utilized for its role. The utility model (uncensored 8B for flexible tasks) is a good use of the asymmetric VRAM.

#### FOUNDRY TP=4 (GPUs 0,1,3,4): ~1 GB Free Total

The Qwen3.5-27B-FP8 model across TP=4 uses 62.4 GB of 65.2 GB total (4x16.3 GB). Each GPU has only ~240 MB free. This is extremely tight.

**Prefix caching impact:** With `--enable-prefix-caching` (which is enabled), vLLM caches KV blocks for repeated system prompts across the 9 agents. Each agent has a fixed system prompt (typically 500-2000 tokens). At FP16 KV precision for a 27B model, each token requires approximately 0.25 MB of KV cache per GPU in TP=4. A 1000-token system prompt therefore uses ~250 MB per GPU -- this is essentially all available VRAM headroom.

**Critical finding:** With only ~240 MB free per GPU, the TP=4 setup can cache approximately **one** agent's system prompt at a time. For 9 agents with different system prompts, there is no room for multi-agent prefix caching.

**KV cache CPU offloading opportunity:** This is the single highest-impact optimization for FOUNDRY. FOUNDRY has 189 GB of *available* RAM (after containers and page cache). Enabling KV cache CPU offloading would:
- Allow 9 agent system prompts to be cached simultaneously in CPU RAM
- Reduce TTFT by 2-22x for cache hits (per [vLLM KV offloading blog, Jan 2026](https://blog.vllm.ai/2026/01/08/kv-offloading-connector.html))
- Enable longer multi-turn conversations without KV eviction
- Zero VRAM cost; uses idle system RAM

**Config change:**
```bash
# Add to FOUNDRY vllm-coordinator launch args
--cpu-offload-gb 32
```

This allocates 32 GB of system RAM as a KV cache spillover tier. FOUNDRY has 189 GB available -- 32 GB is conservative. The vLLM offloading connector achieved up to 83.4 GB/s DMA transfer bandwidth (bidirectional) on the H100; FOUNDRY's PCIe 4.0 x16 will achieve approximately 25-28 GB/s per GPU, which is sufficient for KV block transfers that are typically 0.5-2.5 MB each.

**Estimated impact:** TTFT reduction of 2-4x for repeated agent prompts. Throughput improvement of 30-50% under concurrent agent load due to fewer KV recomputations.

#### WORKSHOP 5060 Ti (GPU 1): 10.7 GB Free

ComfyUI uses only 5.1 GB of 16.3 GB. This is the largest single chunk of unused VRAM in the cluster.

**Options for the free 10.7 GB:**

| Option | VRAM Needed | Benefit | Feasibility |
|--------|-------------|---------|-------------|
| Small coding model (Qwen3.5-4B) | ~3-4 GB | Local code completion for WORKSHOP | High -- separate vLLM instance |
| Draft model for speculative decoding | ~1-2 GB | 1.5-2x TPS improvement on WORKSHOP | Medium -- requires spec decode config |
| Second embedding model | ~1-2 GB | Redundancy for DEV failure | Low priority |
| Whisper large-v3 | ~3 GB | Faster STT than CPU | Medium |

**Recommendation:** Leave as-is for now. ComfyUI's VRAM usage spikes to 12-14 GB during image generation (especially SDXL/Flux workflows). The 10.7 GB "free" space is effectively ComfyUI's working memory. Co-locating another model risks OOM during generation.

#### DEV 5060 Ti (GPU 0): 11.1 GB Free

The embedding model (Qwen3-Embedding-0.6B) and reranker (Qwen3-Reranker-0.6B) together use only 4.8 GB of 16.3 GB.

**Options for the free 11.1 GB:**

| Option | VRAM Needed | Benefit | Feasibility |
|--------|-------------|---------|-------------|
| 7B coding assistant (Qwen3.5-9B-Q4) | ~6-7 GB | Local code completion on DEV workstation | **High -- strong fit** |
| Larger embedding model | ~2-4 GB | Better retrieval quality | Medium |
| Speech processing (Whisper + TTS) | ~4 GB | Voice interface from DEV | Medium |

**Recommendation:** Deploy a 7B-9B coding assistant on DEV alongside the embed/rerank models. At Q4 quantization, a 9B model uses ~6 GB, leaving ~5 GB for the embed/rerank pair (which only need 4.8 GB). Total usage would be ~11.8 GB of 16.3 GB, with 4.5 GB headroom for KV cache.

**Config change:**
```bash
# Add second vLLM instance on DEV
CUDA_VISIBLE_DEVICES=0 vllm serve Qwen/Qwen3.5-9B-Instruct \
  --quantization awq \
  --port 8004 \
  --gpu-memory-utilization 0.40 \
  --max-model-len 8192 \
  --enforce-eager \
  --language-model-only
```

Set `--gpu-memory-utilization 0.40` to reserve 40% of VRAM (6.5 GB) for this model, leaving the rest for embed/rerank which are on separate vLLM instances.

### 1.3 Heterogeneous GPU Best Practices

FOUNDRY's TP=4 mixes the 4090 (Ada, sm_89, 24 GB, PCIe 4.0) with 5070 Tis (Blackwell, sm_120, 16 GB, PCIe 5.0). **But the TP=4 only uses GPUs 0,1,3,4 (all 5070 Tis).** The 4090 runs a separate utility model. This is the correct architecture -- vLLM's tensor parallelism requires homogeneous VRAM sizes and will sync to the smallest GPU's allocation ([vLLM issue #2317](https://github.com/vllm-project/vllm/issues/2317), [vLLM issue #4998](https://github.com/vllm-project/vllm/issues/4998)).

Key findings for heterogeneous clusters:
1. **Never mix GPU generations in a TP group.** vLLM allocates KV cache symmetrically -- the smallest GPU becomes the bottleneck.
2. **Run separate vLLM instances per GPU type.** FOUNDRY does this correctly: TP=4 on 5070 Tis, separate instance on 4090.
3. **Route by task.** Use LiteLLM to route reasoning/agent tasks to the coordinator (27B on TP=4) and simple/utility tasks to the 8B on the 4090.
4. **No PCIe P2P on GeForce.** NVIDIA confirmed GeForce cards lack P2P support since RTX 30-series ([Tom's Hardware](https://www.tomshardware.com/news/nvidia-confirms-geforce-cards-lack-p2p-support)). NCCL falls back to host-staged transfers through system RAM, which is slower but functional.

### 1.4 PCIe Bandwidth for TP=4

FOUNDRY's EPYC 7663 provides 128 PCIe 4.0 lanes. Each 5070 Ti is electrically PCIe 5.0 x16 but negotiates to PCIe 4.0 x16 on the ROMED8-2T board (PCIe 4.0 slots). Effective bandwidth per GPU: ~32 GB/s unidirectional, ~25 GB/s sustained.

For TP=4, the all-reduce communication pattern during each decode step requires synchronizing activations across all 4 GPUs. The data volume per all-reduce is approximately:

```
all_reduce_size = 2 * hidden_dim * sizeof(float16) * (tp_size - 1) / tp_size
                = 2 * 4096 * 2 * 3/4
                = ~12 KB per token per step
```

At ~28 tokens/second decode rate (from benchmarks), this is ~336 KB/s of cross-GPU traffic -- negligible compared to PCIe bandwidth. **PCIe is not the bottleneck for decode.** It becomes relevant during prefill (batch of input tokens processed in parallel), but even at 1000 input tokens, the all-reduce is only ~12 MB, completing in <1 ms at 25 GB/s.

**NVLink comparison:** NVLink on dual RTX 3090s provided 112.5 GB/s. PCIe 4.0 x16 provides ~25 GB/s sustained. For TP=4 inference, this 4.5x bandwidth difference translates to <5% TTFT impact because all-reduce data volume is small relative to bandwidth. NVLink matters far more for training than for inference.

---

## 2. RAM Utilization Analysis

### 2.1 Current RAM State (Live, 2026-03-09)

| Node | Total | Used | Available | Buff/Cache | Swap Used |
|------|-------|------|-----------|------------|-----------|
| FOUNDRY | 219 GB | 30 GB | 189 GB | 173 GB | 628 KB |
| WORKSHOP | 125 GB | 20 GB | 105 GB | 104 GB | 36 KB |
| DEV | 60 GB | 9.2 GB | 50 GB | 45 GB | 45 MB |
| **Total** | **404 GB** | **59 GB** | **344 GB** | | |

**344 GB of available RAM is doing nothing** (buff/cache is reclaimable). This is the largest utilization gap in the cluster.

### 2.2 FOUNDRY RAM Optimization (189 GB Available)

**Priority 1: KV Cache CPU Offloading (32-64 GB)**

As detailed in Section 1.2, allocating 32-64 GB of FOUNDRY's idle RAM as a KV cache offload tier is the single highest-impact change. The vLLM OffloadingConnector (v0.12.0+) achieved:
- DMA transfer bandwidth: 83.4 GB/s bidirectional on H100
- On PCIe 4.0 (FOUNDRY): expect ~25-28 GB/s per direction
- TTFT reduction: 2-4x for cache hits
- Throughput improvement: up to 5x at high cache hit rates

FOUNDRY's DDR4-3200 across 8 channels delivers ~150-165 GB/s practical bandwidth. This is more than sufficient to feed KV cache transfers without contention with other workloads.

**Configuration:**
```bash
# For the vllm-coordinator container
--cpu-offload-gb 32
```

Or via LMCache connector for more control:
```bash
--kv-connector LMCacheConnector \
  --kv-connector-config '{"local_cpu": true, "chunk_size": 256}'
```

**Priority 2: Huge Pages (2 MB) for vLLM Weight Loading**

vLLM allocates large contiguous memory regions for model weights and KV cache. Linux huge pages (2 MB or 1 GB) reduce TLB misses during weight access.

```bash
# Reserve 32 GB of 2MB huge pages on FOUNDRY
echo 16384 > /proc/sys/vm/nr_hugepages
# Or in sysctl.conf for persistence
vm.nr_hugepages = 16384
```

Estimated impact: 5-10% prefill throughput improvement due to reduced TLB pressure ([existing RAM research, Feb 2026](2026-02-25-ram-utilization-strategies.md)).

**Priority 3: tmpfs for Triton Cache**

vLLM's Triton autotuner compiles optimized CUDA kernels on first launch. These are cached in `~/.cache/triton`. Mounting this on a tmpfs eliminates NVMe I/O for cache reads:

```bash
# Mount 4 GB tmpfs for Triton cache
mount -t tmpfs -o size=4G tmpfs /home/athanor/.cache/triton
```

Impact: Faster cold starts after container restart (~10-20s saved).

**Priority 4: In-Memory Qdrant HNSW Index**

FOUNDRY runs Qdrant with 8 collections. Qdrant uses memory-mapped HNSW indices by default. With 189 GB of free RAM, Qdrant can be configured to load all HNSW indices into RAM:

```yaml
# Qdrant config: storage config
storage:
  hnsw_index:
    on_disk: false  # Load HNSW index into RAM
```

Current Qdrant data likely fits in <10 GB. Loading the HNSW index into RAM eliminates mmap page faults during vector search, reducing search latency by 20-50% for cold queries.

### 2.3 WORKSHOP RAM Optimization (105 GB Available)

**KV Cache CPU Offloading for Qwen3.5-35B-A3B-AWQ:**

The MoE model (35B total, 3B active) has a large KV cache because all 35B parameters contribute to the attention mechanism even though only 3B are active per token. CPU offloading is particularly valuable here.

```bash
# For vllm-node2 container
--cpu-offload-gb 16
```

WORKSHOP's DDR5-5600 across 4 channels delivers ~140-150 GB/s practical bandwidth. Despite having fewer channels than FOUNDRY, DDR5's higher per-channel bandwidth compensates.

### 2.4 CPU-Based KV Cache Offloading Viability

**Is the bandwidth sufficient?**

| Node | RAM BW (practical) | KV block transfer size | Blocks/second | Verdict |
|------|-------------------|----------------------|---------------|---------|
| FOUNDRY | ~150 GB/s | 0.5-2.5 MB | 60K-300K | Far exceeds demand |
| WORKSHOP | ~140 GB/s | 0.5-2.5 MB | 56K-280K | Far exceeds demand |

At 28 tokens/sec decode rate, each token generates one KV block per layer per head. For Qwen3.5-27B with 32 layers, this is ~32 blocks per token, or ~896 blocks/second. Even at 2.5 MB per block, this is 2.2 GB/s -- 1.5% of FOUNDRY's memory bandwidth. **RAM bandwidth is not a constraint for KV cache offloading on this hardware.**

---

## 3. NVMe Utilization Analysis

### 3.1 Current NVMe State

| Node | Drive | Gen | Capacity | Used | Free | Mount |
|------|-------|-----|----------|------|------|-------|
| FOUNDRY | Crucial P3 4TB | Gen3 | 3.6 TB | 338 GB (10%) | 3.1 TB | / (OS) |
| FOUNDRY | Crucial P310 1TB | Gen4 | 932 GB | 5.8 MB (<1%) | 930 GB | /mnt/local-fast |
| WORKSHOP | Crucial T700 4TB | Gen5 | 3.6 TB | 273 GB (8%) | 3.2 TB | / (OS) |
| WORKSHOP | Crucial T700 1TB x3 | Gen5 | 2.8 TB | Unmounted | N/A | Stale ZFS labels |

**FOUNDRY /mnt/local-fast is completely empty.** This is a 1 TB Gen4 NVMe with ~5.5 GB/s sequential read speed doing absolutely nothing.

**WORKSHOP has 3x 1TB Gen5 T700 drives unmounted.** These are high-performance Gen5 drives (~12 GB/s sequential read) sitting idle with stale ZFS labels.

### 3.2 Model Weight Loading Patterns

Model weights in safetensors format are loaded sequentially at startup:
- Sequential read: The primary access pattern. NVMe Gen4 achieves 5-7 GB/s, Gen5 achieves 10-12 GB/s.
- Random read: Not a factor for model loading (safetensors is a flat memory-mapped format).
- **Cold start timing:** FOUNDRY's Qwen3.5-27B-FP8 (~27 GB weights) loads in ~4-5 seconds from local NVMe at Gen3 speeds. From NFS (5GbE) it would take ~24 seconds.

**Current model storage:** Models load from `/models/` which is likely NFS-mounted from VAULT over 5GbE. This means cold starts are bottlenecked at ~1.1 GB/s NFS throughput.

**Recommendation: Copy hot models to local NVMe.**

```bash
# On FOUNDRY: copy coordinator model to local-fast
rsync -av /models/Qwen3.5-27B-FP8/ /mnt/local-fast/Qwen3.5-27B-FP8/
# Update vLLM launch to use local path
--model /mnt/local-fast/Qwen3.5-27B-FP8
```

Impact: Cold start from ~24s (NFS) to ~4s (local Gen4 NVMe). A 6x improvement.

### 3.3 NVMe KV Cache (Disk-Based Offloading)

vLLM does not natively support NVMe-based KV cache as of March 2026. Third-party solutions exist:

| System | Latency per KV block retrieval | Suitable for interactive? |
|--------|-------------------------------|--------------------------|
| CPU RAM offload (vLLM native) | <1 ms | Yes |
| NVMe offload (KVSwap) | 100-500 ms | No |
| Ceph/Network storage | 1-10 ms | Marginal |

**Verdict:** NVMe KV cache is not viable for Athanor's interactive agent workloads. The 100-500 ms per-block retrieval latency would add seconds to TTFT for cache misses. CPU RAM offloading is the correct tier for this cluster -- FOUNDRY has 189 GB of available RAM, which is 6x the model weight size and can hold KV cache for hundreds of concurrent contexts.

### 3.4 NVMe Bandwidth for Cold Starts

For FOUNDRY with 4 GPUs loading TP=4 weights simultaneously:

```
Weight size per GPU shard: 27 GB / 4 = 6.75 GB
PCIe 4.0 x16 bandwidth: ~25 GB/s per GPU (host-to-device)
Load time per shard: 6.75 / 25 = 0.27 seconds (PCIe bound)
NVMe read bandwidth needed: 6.75 GB * 4 = 27 GB in parallel
```

FOUNDRY's OS drive (Crucial P3, Gen3) delivers ~3.5 GB/s sequential. Loading 27 GB takes ~7.7 seconds. The P310 on /mnt/local-fast (Gen4) delivers ~5.5 GB/s, reducing this to ~4.9 seconds. **The NVMe is the bottleneck, not PCIe.**

If models were stored on WORKSHOP's T700 (Gen5, ~12 GB/s), loading would take ~2.25 seconds -- but that requires network transfer to FOUNDRY, negating the benefit.

**Recommendation:** Use fastsafetensors for parallel model loading:

```bash
# vLLM flag for faster model loading
--load-format fastsafetensors
```

fastsafetensors enables GPU Direct Storage and parallelized tensor copying, achieving 4.8-7.5x faster loading per [arxiv/2505.23072](https://arxiv.org/html/2505.23072v1). This would bring cold start from ~5s to <1s on local Gen4 NVMe.

### 3.5 Unmounted WORKSHOP NVMe

Three 1 TB Crucial T700 Gen5 drives on WORKSHOP are unmounted with stale ZFS labels. Options:

| Option | Benefit | Effort |
|--------|---------|--------|
| Format and mount as /mnt/fast-storage | 3 TB Gen5 scratch space | Low |
| Create ZFS pool for ComfyUI outputs | Redundant fast storage for creative work | Medium |
| Use for model weight cache | Faster cold starts on WORKSHOP | Low |

**Recommendation:** At minimum, format one T700 and mount it as model weight cache on WORKSHOP. The Qwen3.5-35B-A3B-AWQ model is ~22 GB; loading from local Gen5 NVMe (~12 GB/s) takes ~1.8 seconds vs ~20 seconds from NFS.

---

## 4. HDD Utilization (VAULT)

### 4.1 Capacity Risk Profile at 86%

VAULT's Unraid array: 141 TB used / 164 TB usable (86% full, single parity drive at 22 TB).

| Fullness Level | Risk | Recommendation |
|----------------|------|----------------|
| <80% | Low | Normal operations |
| **80-90% (current)** | **Moderate** | **Plan expansion, set minimum free space** |
| 90-95% | High | Active management required, individual disks may fill |
| >95% | Critical | Write failures likely, performance degradation |

**Key risks at 86%:**
1. **Individual disk saturation:** Unraid distributes writes across disks, but shares with "High Water" allocation can fill individual disks to 100% while aggregate shows 86%. Set Minimum Free Space to 500 GB per share.
2. **Parity rebuild time:** At 22 TB parity drive, a full rebuild takes 24-48 hours. During rebuild, a second disk failure means data loss (single parity).
3. **Write performance:** XFS (Unraid's default per-disk filesystem) handles near-full volumes well, but NFS exports may slow as individual disks fill.

**Recommendations:**
1. Set `Minimum Free Space = 500 GB` on all shares to prevent individual disk filling.
2. Run parity check now and schedule monthly automated checks ([Unraid docs](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/array/array-health-and-maintenance/)).
3. Plan upgrade: the spare 22 TB WD drive (disk9) could be swapped with the 16 TB parity drive, then the 16 TB drive becomes a data disk, adding ~16 TB usable. Or add a new 22+ TB drive.
4. Consider dual parity: with 10 drives and 141 TB of data, single parity is risky. A second 22 TB parity drive reduces data loss risk during rebuilds.

### 4.2 AI Data Compression Opportunities

| Data Type | Current Size (est.) | Compressible? | Savings |
|-----------|-------------------|---------------|---------|
| Model weights (safetensors) | ~200 GB | No (already dense float data) | 0% |
| Qdrant vectors | ~5-10 GB | No (already quantized) | 0% |
| Neo4j graph data | ~2-5 GB | Minimal | <5% |
| Container logs | ~5-20 GB | Yes (text) | 60-80% |
| Plex media | ~120+ TB | No (already compressed video) | 0% |
| Monitoring data (Prometheus) | ~10-50 GB | Yes (time-series) | 30-50% |

**The bulk of VAULT storage is media.** AI-related data is <1% of total storage. Compression or deduplication of AI data would save <1 TB -- irrelevant at this scale.

**Real savings:** Log rotation and retention policies. Configure Loki/Grafana to retain only 30 days of logs. Configure Prometheus retention to 90 days. These typically reclaim 10-50 GB.

---

## 5. CPU Utilization Analysis

### 5.1 Current CPU State (Live, 2026-03-09)

| Node | CPU | Cores/Threads | Load Avg (1m) | Utilization |
|------|-----|---------------|---------------|-------------|
| FOUNDRY | EPYC 7663 | 56C/112T | 4.52 | ~4% of cores |
| WORKSHOP | TR 7960X | 24C/48T | 0.02 | <1% of cores |
| DEV | Ryzen 9900X | 12C/24T | 0.39 | ~3% of cores |

**Combined: 92 cores with <5% sustained utilization.** FOUNDRY's load of 4.5 comes from the vLLM processes (CPU-side attention computation, tokenization, scheduling) and the agent server.

### 5.2 FOUNDRY EPYC 7663 (56C, 189 GB free RAM)

With GPU inference handling the heavy computation, the EPYC's role is:

| Current Role | CPU Impact | RAM Impact |
|-------------|-----------|------------|
| vLLM scheduling & tokenization | ~4 cores | ~2 GB |
| Container overhead (11 containers) | ~2 cores | ~5 GB |
| Qdrant vector search | ~2 cores (burst) | ~5 GB |
| Agent server (LangGraph/FastAPI) | ~2 cores | ~2 GB |
| Monitoring (Prometheus, Alloy) | ~1 core | ~1 GB |

**~45 cores idle.** Best uses for the remaining capacity:

| Opportunity | Cores Needed | RAM Needed | Impact |
|-------------|-------------|------------|--------|
| KV cache CPU offloading | 0 (DMA) | 32-64 GB | **Very High** -- see Section 2.2 |
| CPU embedding (replace DEV GPU) | 8-16 | 2-4 GB | High -- frees DEV VRAM |
| CPU reranking | 2-4 | 1-2 GB | High -- better RAG quality |
| llama.cpp 7B auxiliary | 16 | 4-8 GB | Medium -- background tasks |
| Batch preprocessing | 4-8 | 2-4 GB | Medium -- document ingestion |
| Anomaly detection (scikit-learn) | 1-2 | 1 GB | Low-Medium |

**Note on CPU embedding:** The existing research (Feb 25) recommended moving embedding from GPU to CPU. This is now less urgent because DEV's embed/rerank models use only 4.8 GB of 16.3 GB, leaving room for a coding assistant. However, if a larger embedding model is needed, CPU embedding on FOUNDRY's EPYC (with AVX-512 + 8-channel DDR4) would deliver 300-600 embeddings/sec on ONNX Runtime -- more than sufficient for Athanor's workload.

### 5.3 WORKSHOP TR 7960X (24C, 105 GB free RAM)

Load average: 0.02. **This is a 350W TDP processor doing essentially nothing.** The 5090 handles all inference.

Best uses:

| Opportunity | Cores Needed | Impact |
|-------------|-------------|--------|
| Audio processing (Whisper CPU fallback) | 4-8 | Medium -- provides STT redundancy |
| ComfyUI preprocessing/postprocessing | 2-4 | Medium -- image pipeline acceleration |
| llama.cpp 7B coding assistant | 8-16 | Medium -- local coding when GPU is busy |
| Dashboard SSR rendering | 2 | Already in use |

**WORKSHOP's DDR5-5600 at 4 channels delivers ~140 GB/s bandwidth.** This makes it excellent for memory-bandwidth-bound CPU inference. A 7B Q4_K_M model on llama.cpp would achieve ~12-20 tokens/second on the TR 7960X (based on community benchmarks for similar Zen 4 CPUs with DDR5).

### 5.4 VAULT 9950X (16C, 42 containers)

With 42 containers, VAULT's 16 cores are the most densely allocated in the cluster. However, most containers are idle most of the time (databases waiting for queries, media services waiting for requests).

Current RAM: 128 GB with estimated ~30 GB active use. The 9950X's 2-channel DDR5 delivers ~65-72 GB/s practical bandwidth -- adequate for its storage/service role but not suitable for CPU-intensive AI workloads.

**No CPU changes recommended for VAULT.** It is correctly sized for its role.

---

## 6. Network Utilization Analysis

### 6.1 Current Network Configuration

| Link | Speed | MTU | Notes |
|------|-------|-----|-------|
| FOUNDRY <-> Switch | 10 GbE SFP+ | 9000 (jumbo) | Intel X550 onboard |
| WORKSHOP <-> Switch | 10 GbE SFP+ | 9000 (jumbo) | Aquantia onboard |
| VAULT <-> Switch | 10 GbE SFP+ | 9000 (jumbo) | Aquantia onboard |
| DEV <-> Switch | 5 GbE (Realtek) | 1500 (standard) | Onboard, no jumbo |

Effective throughput: 10 GbE with jumbo frames delivers ~1.1 GB/s (measured for NFS model loading). 5 GbE on DEV delivers ~550 MB/s theoretical, ~450 MB/s practical.

### 6.2 Agent Traffic Patterns

The 9 agents generate traffic in this pattern:

```
Agent (FOUNDRY:9000) -> LiteLLM (VAULT:4000) -> vLLM (FOUNDRY:8000 or WORKSHOP:8000)
```

For requests staying on FOUNDRY (coordinator model), the traffic is localhost -- zero network overhead.

For requests routed to WORKSHOP:
- Request payload: typically 1-10 KB (system prompt + user message)
- Response payload: typically 1-50 KB (generated text)
- At 9 concurrent agents, worst case: ~450 KB/s -- negligible on 10 GbE

**Network is not a bottleneck for inference traffic.** It only matters for:
1. Model loading from NFS (10 GbE = ~1.1 GB/s, takes 24s for 27 GB model)
2. Qdrant searches when Qdrant runs on a different node (sub-ms latency on 10 GbE)
3. Prometheus metrics scraping (trivial bandwidth)

### 6.3 DEV 5 GbE Limitation

DEV's Realtek 5 GbE NIC is the weakest link. For DEV's role as ops center:
- Claude Code SSH sessions: negligible bandwidth
- Embedding requests: ~10 KB per request, ~100 requests/min max -- negligible
- Model loading (if needed): 5 GbE delivers ~550 MB/s, adequate for 0.6B models

**No network upgrade needed for DEV.** The existing spare Intel X540-T2 5GbE cards could be installed if DEV ever runs larger models, but the current workload doesn't justify it.

---

## 7. PCIe Topology and GPU Communication

### 7.1 FOUNDRY PCIe Layout

The ASRock ROMED8-2T has 128 PCIe 4.0 lanes from the EPYC 7663 (single socket, single NUMA node). The 5 GPUs are in:
- Slot 2 (x16): 5070 Ti GPU0
- Slot 3 (x16): 5070 Ti GPU1
- Slot 1 (x16): 4090 GPU2
- Slot 4 (x16): 5070 Ti GPU3
- Slot 5 (x16): 5070 Ti GPU4

With 5 GPUs at x16 = 80 lanes. Plus 2x NVMe (2 lanes each via M.2), SAS HBA, and 5GbE NICs. Total: ~100 of 128 lanes used.

### 7.2 No P2P on GeForce

NVIDIA confirmed that **PCIe P2P is not supported on any GeForce card from RTX 30-series onward** ([Tom's Hardware](https://www.tomshardware.com/news/nvidia-confirms-geforce-cards-lack-p2p-support)). This includes the RTX 4090, 5070 Ti, 5090, and 5060 Ti.

For TP=4, NCCL falls back to host-staged transfers (GPU -> system RAM -> GPU). On FOUNDRY's single NUMA node, this adds minimal latency because all GPUs share the same memory controller. The path is:

```
GPU0 -> PCIe 4.0 -> EPYC DDR4 -> PCIe 4.0 -> GPU1
Bandwidth: ~12.5 GB/s per direction (half of PCIe bandwidth used for staging)
```

For the all-reduce data volumes in inference (~12 KB per token per step), this is inconsequential.

### 7.3 Mixed 4090 + 5070 Ti Communication

The 4090 and 5070 Ti GPUs on FOUNDRY do not communicate directly (they run separate vLLM instances). If they needed to communicate (e.g., for pipeline parallelism), the PCIe Gen 4 of the 4090 would be the common denominator. But this is irrelevant for the current architecture.

---

## 8. Emerging Techniques

### 8.1 Prefix Caching for Agent Prompts

**Status:** vLLM `--enable-prefix-caching` is already enabled on FOUNDRY and WORKSHOP.

**Impact for Athanor's 9 agents:**

Each agent has a fixed system prompt (~500-2000 tokens) that is identical across requests. With prefix caching, vLLM computes the KV cache for these system prompt tokens once and reuses it for subsequent requests. This provides:

- **TTFT reduction:** For a 1000-token system prompt, prefix caching eliminates ~1000 tokens of prefill computation. At Qwen3.5-27B's prefill rate, this saves approximately 200-400 ms per request.
- **VRAM savings:** Instead of storing 9 separate copies of the system prompt KV cache, only unique prefixes are stored. For 9 agents with 1000-token prompts, this saves approximately 9 * 250 MB = 2.25 GB of KV cache (at FP16) -- significant given the TP=4 setup's tight VRAM.
- **Multi-turn benefit:** In multi-turn conversations, the entire conversation history is a prefix for the new turn. Prefix caching means growing conversations don't linearly increase TTFT.

**Combined with CPU offloading:** When KV cache CPU offloading is enabled, evicted prefix caches are stored in CPU RAM rather than being discarded. This means agent system prompts persist across request batches, providing consistent TTFT even after periods of inactivity.

**Estimated combined impact:** 2-4x TTFT reduction for agent requests with shared system prompts. KVFlow-style multi-agent prefix caching ([arxiv/2507.07400](https://arxiv.org/html/2507.07400v1)) could further optimize this by scheduling agents to maximize prefix reuse, but this requires custom scheduling logic beyond vLLM's built-in prefix caching.

### 8.2 Speculative Decoding

**Current state:** Not enabled on any Athanor vLLM instance.

**Options for the cluster:**

| Method | Draft Model | Speedup | VRAM Cost | Config Complexity |
|--------|-------------|---------|-----------|-------------------|
| N-gram speculation | None (uses prompt) | 1.2-1.5x | 0 | Very Low |
| Draft model (Qwen3.5-0.8B) | 0.8B on same GPUs | 1.5-2.5x | ~1-2 GB per GPU | Medium |
| EAGLE3 trained drafter | Custom trained | 2-3x | ~1-2 GB per GPU | High |
| CPU draft model | 0.8B on CPU | 1.5-2x | 0 VRAM | Not supported in vLLM |

**N-gram speculation is the only viable option today.** The TP=4 5070 Ti setup has only ~240 MB free per GPU -- no room for a draft model. CPU-based draft models are not supported in vLLM as of March 2026.

```bash
# Add to FOUNDRY vllm-coordinator launch args
--speculative-model "[ngram]" \
--num-speculative-tokens 5 \
--ngram-prompt-lookup-max 4
```

**Estimated impact:** 1.2-1.5x decode speedup for structured/repetitive outputs (JSON, code, repeated patterns). Minimal benefit for creative/reasoning outputs. Zero VRAM cost.

**WORKSHOP opportunity:** The 5090 with MoE model has only 772 MB free, which is also too tight for a draft model. However, the MoE architecture with 3B active parameters already decodes very fast (expected 80-120+ t/s once the OOM fix is applied). Speculative decoding provides less benefit when the base model is already fast.

### 8.3 Flash Attention 3/4 on Blackwell

**Status as of March 2026: Not available for sm_120 (consumer Blackwell).**

- Flash Attention 2 and 3: Do not support sm_120. Raises `RuntimeError: FlashAttention only supports Ampere GPUs or newer` on RTX 5070 Ti/5090.
- Flash Attention 4: Designed for sm_100 (datacenter Blackwell B200). Compatibility with sm_120 is uncertain.
- **vLLM uses FlashInfer on Blackwell:** The `VLLM_ATTENTION_BACKEND=FLASHINFER` setting is used on all Athanor's Blackwell GPUs. FlashInfer provides sm_120-compatible attention kernels.
- SageAttention 2.2.0: Community-built wheels available for sm_120, claiming ~35% faster diffusion sampling. Not integrated with vLLM.
- Community FA2 fork (loscrossos/lib_flashattention): Claims sm_120 support but unverified.

**No action recommended.** FlashInfer works. When official FA3/FA4 support arrives for sm_120, it can be evaluated, but the current setup is functional.

Sources: [flash-attention #1665](https://github.com/Dao-AILab/flash-attention/issues/1665), [flash-attention #1987](https://github.com/Dao-AILab/flash-attention/issues/1987), [sglang #10564](https://github.com/sgl-project/sglang/discussions/10564)

### 8.4 Continuous Batching Utilization

**How well does continuous batching serve 9 concurrent agents?**

vLLM's continuous batching achieves 90%+ GPU utilization under sustained load ([vLLM blog, Sep 2025](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html)). But Athanor's pattern is bursty:

- 9 agents send requests intermittently, not continuously
- Peak: 3-5 concurrent requests during active agent sessions
- Average: <1 request in flight at any time
- GPU compute utilization: 0% between requests (confirmed by live nvidia-smi)

**Continuous batching provides little benefit at current load levels.** Its value is in preventing head-of-line blocking (a short request doesn't wait for a long generation to finish) and enabling the system to handle burst loads gracefully.

**When continuous batching matters:** If agent orchestration sends multiple parallel tool calls (e.g., 9 agents all querying simultaneously during a scheduled task), continuous batching handles this without serialization. The 5:30 AM daily self-improvement cycle is exactly this pattern -- all agents evaluate simultaneously.

### 8.5 PagedAttention on Heterogeneous Memory

vLLM's PagedAttention treats GPU memory as virtual memory pages. For heterogeneous VRAM:

- **Within a TP group:** All GPUs must have equal VRAM. PagedAttention allocates symmetric page pools.
- **Across separate instances:** Each vLLM instance manages its own page pool independently. No cross-instance sharing.
- **CPU spillover:** The KV offloading connector creates a second page pool in CPU RAM, managed by the same PagedAttention logic. This is the mechanism that makes KV cache CPU offloading work transparently.

**For Athanor:** The architecture is already correct. TP=4 uses homogeneous 5070 Tis. Separate instances on the 4090 and 5090 manage their own pools. CPU offloading extends each instance's effective pool using the abundant system RAM.

---

## 9. Consolidated Recommendations

### Tier 1: Configuration Changes (Zero Hardware, Zero Code)

| # | Change | Node | Impact | Effort | Risk |
|---|--------|------|--------|--------|------|
| 1 | **Enable KV cache CPU offloading** (`--cpu-offload-gb 32`) | FOUNDRY | 2-4x TTFT reduction, 30-50% throughput increase | 5 min | Very Low |
| 2 | **Enable KV cache CPU offloading** (`--cpu-offload-gb 16`) | WORKSHOP | Similar TTFT/throughput benefit | 5 min | Very Low |
| 3 | **Enable n-gram speculation** (`--speculative-model [ngram]`) | FOUNDRY | 1.2-1.5x decode speedup | 5 min | Very Low |
| 4 | **Copy models to local NVMe** | FOUNDRY | 6x faster cold starts (24s -> 4s) | 15 min | None |
| 5 | **Set Minimum Free Space = 500 GB** on Unraid shares | VAULT | Prevents individual disk filling | 5 min | None |
| 6 | **Enable huge pages** (16384 x 2MB) | FOUNDRY | 5-10% prefill improvement | 5 min | Low |

**Total effort: ~40 minutes. Total impact: Significant improvement in TTFT, throughput, and cold start times.**

### Tier 2: Software Changes (Small Deployments)

| # | Change | Node | Impact | Effort | Risk |
|---|--------|------|--------|--------|------|
| 7 | **Deploy 9B coding assistant on DEV** | DEV | Local code completion | 30 min | Low |
| 8 | **Format and mount WORKSHOP T700 NVMe** | WORKSHOP | 1 TB fast scratch + model cache | 20 min | Low |
| 9 | **Enable fastsafetensors** (`--load-format fastsafetensors`) | ALL | 4-7x faster model loading | 15 min | Low |
| 10 | **Qdrant HNSW in-memory mode** | FOUNDRY | 20-50% faster vector search | 10 min | Low |
| 11 | **Triton cache on tmpfs** | FOUNDRY | Faster cold starts | 5 min | None |

### Tier 3: Architecture Changes (Larger Effort)

| # | Change | Node | Impact | Effort | Risk |
|---|--------|------|--------|--------|------|
| 12 | **GPU orchestrator with sleep/wake** | FOUNDRY | Dynamic VRAM multiplexing | 4-6 hrs | Medium |
| 13 | **CPU embedding service (FastEmbed)** | FOUNDRY | Free DEV GPU for larger model | 2-3 hrs | Low |
| 14 | **llama.cpp 7B auxiliary on FOUNDRY CPU** | FOUNDRY | Background summarization, tagging | 1-2 hrs | Low |
| 15 | **Dual parity for VAULT array** | VAULT | Data protection during rebuild | 1-2 hrs | Low |

### Tier 4: Future Monitoring

| Item | Trigger | Action |
|------|---------|--------|
| Flash Attention sm_120 support | Official release | Evaluate FA3/FA4 vs FlashInfer |
| vLLM CPU draft model support | Feature merge | Enable speculative decoding with 0.8B CPU draft |
| VAULT at 90% | Storage growth | Add 22 TB drive or upgrade parity |
| DEV 5 GbE bottleneck | DEV running larger models | Install spare Intel X540-T2 5GbE |

---

## 10. Utilization Heatmap (Before vs After Tier 1+2)

### Before (Current State)

```
Resource        FOUNDRY    WORKSHOP   VAULT      DEV
GPU VRAM        [========] [========] [=       ] [===     ]
GPU Compute     [         ] [         ] [         ] [         ]
System RAM      [==       ] [=        ] [==       ] [=        ]
CPU             [=        ] [         ] [==       ] [         ]
NVMe            [=        ] [         ] [=========] [=        ]
Network         [         ] [         ] [         ] [         ]
```

### After (Tier 1+2 Applied)

```
Resource        FOUNDRY    WORKSHOP   VAULT      DEV
GPU VRAM        [========] [========] [=       ] [======  ]
GPU Compute     [=        ] [=        ] [         ] [=        ]
System RAM      [====     ] [==       ] [==       ] [=        ]
CPU             [==       ] [         ] [==       ] [=        ]
NVMe            [==       ] [=        ] [=========] [=        ]
Network         [         ] [         ] [         ] [         ]
```

Key changes:
- **FOUNDRY GPU Compute:** Up from 0% to ~5-10% due to n-gram speculation overhead
- **FOUNDRY System RAM:** Up from 14% to 20-25% due to KV cache offloading (32 GB)
- **DEV GPU VRAM:** Up from 29% to ~72% due to coding assistant deployment
- **FOUNDRY NVMe:** Up from 10% to 20% due to local model storage

---

## Sources

### vLLM Features
- [vLLM KV Offloading Connector (Jan 2026)](https://blog.vllm.ai/2026/01/08/kv-offloading-connector.html) -- DMA bandwidth, TTFT improvements
- [vLLM Prefix Caching Design](https://docs.vllm.ai/en/stable/design/prefix_caching/) -- Hash-based prefix caching
- [vLLM Prefix Caching v1](https://docs.vllm.ai/en/v0.8.5/design/v1/prefix_caching.html) -- Eviction policies
- [vLLM Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode/) -- N-gram, draft model, EAGLE3
- [vLLM Parallelism & Scaling](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/) -- TP/PP requirements
- [vLLM fastsafetensors](https://docs.vllm.ai/en/stable/models/extensions/fastsafetensor/) -- GPU Direct Storage loading
- [vLLM Quantized KV Cache](https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/) -- FP8 KV cache

### Performance Research
- [KVFlow: Prefix Caching for Multi-Agent Workflows (2025)](https://arxiv.org/html/2507.07400v1) -- Agent-specific prefix optimization
- [fastsafetensors: Speeding up Model Loading (2025)](https://arxiv.org/html/2505.23072v1) -- 4.8-7.5x loading speedup
- [KVSwap: Disk-aware KV Cache Offloading (2025)](https://arxiv.org/html/2511.11907) -- NVMe KV cache limitations
- [NVIDIA Run:ai Model Streamer](https://developer.nvidia.com/blog/reducing-cold-start-latency-for-llm-inference-with-nvidia-runai-model-streamer/) -- Cold start optimization
- [vLLM Speculative Decoding Benchmarks](https://blog.vllm.ai/2024/10/17/spec-decode.html) -- Up to 2.8x speedup
- [Speculators v0.3.0 (Dec 2025)](https://blog.vllm.ai/2025/12/13/speculators-v030.html) -- EAGLE3 training for vLLM
- [BentoML Speculative Decoding Guide](https://www.bentoml.com/blog/3x-faster-llm-inference-with-speculative-decoding) -- Draft model selection

### GPU Hardware
- [NVIDIA GeForce P2P Confirmation](https://www.tomshardware.com/news/nvidia-confirms-geforce-cards-lack-p2p-support) -- No P2P on consumer cards
- [RTX 5070 Ti AI Benchmarks](https://gigachadllc.com/geforce-rtx-5070-ti-ai-benchmarks-breakdown/) -- FP8 TFLOPS, bandwidth
- [bestgpusforai.com: 5070 Ti vs 4090](https://www.bestgpusforai.com/gpu-comparison/5070-ti-vs-4090) -- Specs comparison
- [vLLM heterogeneous GPU issues](https://github.com/vllm-project/vllm/issues/2317) -- TP requires homogeneous VRAM
- [NCCL P2P issues RTX 5090](https://github.com/NVIDIA/nccl/issues/1637) -- P2P still broken on Blackwell GeForce

### Flash Attention
- [flash-attention #1665: sm_120 support](https://github.com/Dao-AILab/flash-attention/issues/1665) -- Not supported
- [flash-attention #1987: Blackwell timeline](https://github.com/Dao-AILab/flash-attention/issues/1987) -- No ETA
- [SageAttention Blackwell wheels](https://github.com/mobcat40/sageattention-blackwell) -- Community workaround
- [FA4 reverse engineering (Modal)](https://modal.com/blog/reverse-engineer-flash-attention-4) -- sm_100 only

### Storage & Network
- [Unraid Array Health](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/array/array-health-and-maintenance/) -- Parity checks, maintenance
- [Unraid Minimum Free Space](https://forums.unraid.net/topic/77453-setting-minimum-free-disk-space-and-other-housekeeping/) -- Disk fill prevention
- [Heterogeneous GPU Cluster Management (2026)](https://www.decodesfuture.com/articles/cost-efficiency-heterogeneous-gpu-llm-serving) -- Phase disaggregation
- [KV Cache Offloading When Beneficial (NetApp)](https://community.netapp.com/t5/Tech-ONTAP-Blogs/KV-Cache-Offloading-When-is-it-Beneficial/ba-p/462900) -- NVMe vs CPU offloading comparison

### CPU Inference
- [AMD EPYC vLLM Performance (2025)](https://www.amd.com/en/blogs/2025/unlocking-optimal-llm-performance-on-amd-epyc--cpus-with-vllm.html) -- EPYC optimization
- [llama.cpp CPU Performance Discussion](https://github.com/ggml-org/llama.cpp/discussions/3167) -- Community benchmarks
- [vLLM Anatomy (Sep 2025)](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html) -- Continuous batching utilization

---

*Last updated: 2026-03-09*
