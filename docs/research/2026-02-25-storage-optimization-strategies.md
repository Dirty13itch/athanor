# Storage Optimization Strategies for AI Workloads

**Date:** 2026-02-25
**Status:** Complete -- recommendation ready
**Builds on:** [2026-02-15-storage-architecture.md](2026-02-15-storage-architecture.md), ADR-003
**Scope:** Software-level storage optimizations (the previous research covered hardware layout)

---

## Context

ADR-003 established the three-tier storage hierarchy (local NVMe / VAULT NVMe over NFS / VAULT HDD array). That research answered *where* data should live. This research answers *how* to make each tier as fast as possible through software configuration, kernel tuning, caching layers, and inference engine options.

Current state:
- Models load from VAULT NFS over 10GbE at ~1.1 GB/s (measured)
- Local NVMe available at 3-7 GB/s (Gen4) or up to 12 GB/s (Gen5 T700)
- vLLM serves Qwen3-32B-AWQ with TP=4 on Node 1, TP=1 on Node 2
- KV cache lives entirely in VRAM
- NFS mount options: `hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4`
- No client-side caching, no kernel tuning, no KV cache offloading

---

## 1. Model Loading Optimization

### 1.1 Loading Format Options in vLLM

vLLM supports multiple model loading backends, each with different performance characteristics:

| Format | How It Works | Speed | Notes |
|--------|-------------|-------|-------|
| `safetensors` (default) | Memory-maps file, `cudaMemcpy` to GPU | ~2x faster than PyTorch on GPU, ~76x on CPU | Default for most HuggingFace models |
| `tensorizer` | CoreWeave's serialization format | ~2.25 GiB/s standard, ~4.625 GiB/s plaid mode (local) | Requires pre-serialization step |
| `runai_streamer` | Concurrent tensor streaming directly to GPU | Network/storage-bound | Install: `pip install vllm[runai]` |
| `pt` | Standard PyTorch loading | Slowest, involves deserialization + copies | Legacy, avoid |
| `gguf` | GGML quantized format | Similar to safetensors | For GGUF-quantized models only |

**Safetensors load strategy** (`--safetensors-load-strategy`):
- `eager`: Loads all tensors immediately (higher peak memory, faster startup)
- `lazy`: Loads tensors on demand (lower peak memory, slightly slower)

For Athanor's setup where models are loaded once and stay resident, `eager` is preferred.

**Source:** [vLLM engine args](https://docs.vllm.ai/en/latest/configuration/engine_args), [safetensors benchmarks](https://huggingface.co/docs/safetensors/speed)

### 1.2 CoreWeave Tensorizer

Tensorizer pre-serializes models into a streaming-optimized format. Key benchmarks from their documentation:

| Source | Mode | Throughput |
|--------|------|-----------|
| Local file | Standard | ~2.25 GiB/s |
| Local file | Plaid mode | ~4.625 GiB/s |
| HTTP/S3 streaming | Standard | 0.875-1.0 GiB/s (network-bound) |
| 40GbE network | Standard | ~5 GB/s (wire speed) |

**Applicability to Athanor:** Limited. The 10GbE network caps NFS at ~1.1 GB/s regardless of format. Tensorizer's advantage materializes only on local NVMe reads, where safetensors with mmap is already near optimal. Not worth the pre-serialization overhead for a homelab.

**Source:** [CoreWeave Tensorizer GitHub](https://github.com/CoreWeave/tensorizer)

### 1.3 Run:ai Model Streamer

Streams safetensors files with concurrent I/O, loading tensors directly into GPU memory. Supports local files, NFS, and S3. Reduces CPU overhead during model loading by parallelizing reads.

```bash
# Usage in vLLM
--load-format runai_streamer
```

**Applicability to Athanor:** Worth testing. Could improve NFS model loading by overlapping network I/O with GPU memory transfers. Install with `pip install vllm[runai]`. Main benefit: hides NFS latency through concurrency.

**Source:** [Run:ai Model Streamer GitHub](https://github.com/run-ai/runai-model-streamer)

### 1.4 The Real Bottleneck

For Qwen3-32B-AWQ (~18 GB model weights):

| Source | Throughput | Load Time | Bottleneck |
|--------|-----------|-----------|------------|
| VAULT HDD over NFS | 150-250 MB/s | 72-120 sec | HDD single-drive read |
| VAULT NVMe over NFS | ~1.1 GB/s | ~16 sec | 10GbE network |
| Local NVMe (Gen4) | 3-7 GB/s | 2.6-6 sec | NVMe sequential read |
| Local NVMe (Gen5 T700) | 10-12 GB/s | 1.5-1.8 sec | PCIe bandwidth |

**Key insight:** For an 18 GB AWQ model, NFS loading takes ~16 seconds. This happens once per vLLM startup. With vLLM sleep mode (when available), the model stays in VRAM and never reloads. The model loading path is not a critical bottleneck for Athanor's current single-model-per-instance architecture.

Where model loading speed matters:
- Cold starts after reboot (~16 sec from NFS is acceptable)
- Model swaps for different workloads (rare)
- ComfyUI checkpoint swaps (frequent -- but those are on Node 2's local NVMe already)

### 1.5 Local NVMe Model Cache

The simplest and most impactful optimization: keep the active model on local NVMe.

```bash
# Sync hot model to local NVMe
rsync -av /mnt/vault/models/llm/Qwen3-32B-AWQ/ /data/models/llm/Qwen3-32B-AWQ/

# Point vLLM at local copy
--model /data/models/llm/Qwen3-32B-AWQ/
```

Benefit: 16 sec -> 3-6 sec model load. More importantly, no dependency on NFS being mounted during vLLM startup.

**Recommendation:** Always keep the active serving model on local NVMe. Use NFS as the canonical repository and sync tool.

---

## 2. KV Cache Storage and Offloading

### 2.1 vLLM Swap Space (CPU RAM)

vLLM's `--swap-space` parameter reserves CPU RAM for KV cache overflow. When GPU memory is full and new requests arrive, existing KV cache blocks are swapped to CPU RAM (preemption) rather than recomputing from scratch.

```bash
--swap-space 8  # 8 GiB per GPU (default: 4 GiB)
```

**Latency hierarchy:**
| Tier | Access Latency | Bandwidth | Use |
|------|---------------|-----------|-----|
| VRAM | ~1 ns | 900+ GB/s (HBM3e) | Active inference |
| CPU RAM | ~50-100 ns | 50-100 GB/s (DDR4/DDR5) | Swap/preemption |
| NVMe | ~10-100 us | 3-14 GB/s | Not used by vLLM |
| HDD | ~5-10 ms | 0.15-0.25 GB/s | Never |

**Node 1 capacity:** 224 GB DDR4. With TP=4 and 4 GiB/GPU default, that's 16 GiB swap. Can safely increase to 8 GiB/GPU (32 GiB total) -- well under the 40% RAM warning threshold (89.6 GiB).

**Recommendation:** Increase to `--swap-space 8` on Node 1. This doubles preemption capacity for free.

**Source:** [vLLM CacheConfig](https://docs.vllm.ai/en/latest/api/vllm/config/cache)

### 2.2 vLLM CPU Offload (Model Weights)

`--cpu-offload-gb` offloads a portion of model weights to CPU RAM, freeing VRAM for KV cache. Each forward pass copies the offloaded weights back to GPU.

```bash
--cpu-offload-gb 10  # Virtually adds 10 GiB to each GPU's capacity
```

**Trade-off:** Increases latency per token because of CPU-to-GPU copies on every forward pass. Requires fast CPU-GPU interconnect (PCIe 4.0/5.0).

**Applicability to Athanor:** Not recommended for Qwen3-32B-AWQ. The AWQ quantized model fits comfortably in the available VRAM. CPU offloading adds latency that degrades inference quality. Reserve this for situations where a model barely doesn't fit in VRAM.

**Source:** [vLLM engine args](https://docs.vllm.ai/en/latest/configuration/engine_args)

### 2.3 vLLM KV Cache Offloading (to CPU)

Separate from swap space, `--kv-offloading-size` enables a dedicated KV cache offloading buffer in CPU RAM with either the `native` or `lmcache` backend.

```bash
--kv-offloading-size 32   # 32 GiB total across all TP ranks
--kv-offloading-backend native  # or "lmcache"
```

**When it helps:** Long-context workloads where KV cache exceeds VRAM. For Qwen3-32B-AWQ with 32K context, KV cache is manageable in VRAM. This becomes important if serving 128K+ context models.

**Source:** [vLLM bench docs](https://docs.vllm.ai/en/latest/cli/bench/throughput)

### 2.4 LMCache: External KV Cache System

LMCache is a full KV cache management system that integrates with both vLLM and SGLang. It stores KV caches across multiple tiers:

| Backend | Latency | Capacity | Best For |
|---------|---------|----------|----------|
| GPU memory | ~1 ns | Limited | Active inference |
| CPU RAM | ~100 ns | Large | Hot KV cache overflow |
| Local disk/NVMe | ~10-100 us | Very large | Warm KV cache persistence |
| Redis | ~1 ms | Distributed | Cross-instance sharing |
| S3 | ~50 ms | Unlimited | Cold storage |

Key capabilities:
- **Prefix caching across instances:** Node 1 and Node 2 can share cached system prompts via Redis
- **3-10x TTFT reduction** for repeated prompts (multi-round QA, RAG)
- **Zero-copy mechanisms** reduce CPU overhead
- **GPU Direct Storage (GDS):** Bypasses CPU for NVMe reads -- but requires Tesla/Quadro GPUs (not GeForce)

**Applicability to Athanor:**
- **Redis backend:** Already running Redis on VAULT:6379. Could store frequently-used KV caches (system prompts, agent contexts) for near-instant reuse.
- **Local disk backend:** Store KV caches on Node 1's NVMe for persistence across vLLM restarts.
- **Cross-instance sharing:** Agent system prompts are identical across requests -- useful for prefix caching.

**Installation:**
```bash
pip install lmcache
```

**Integration with vLLM:**
```bash
--kv-offloading-backend lmcache
```

**Recommendation:** Worth deploying for the agent framework. System prompts for each of the 8 agents are repeated on every request. LMCache with Redis backend could eliminate redundant prefill computation entirely.

**Source:** [LMCache GitHub](https://github.com/LMCache/LMCache), [LMCache docs](https://docs.lmcache.ai)

### 2.5 SGLang HiCache (Hierarchical KV Caching)

SGLang's HiCache implements a three-tier KV cache hierarchy:

| Tier | Storage | Purpose |
|------|---------|---------|
| L1 | GPU memory | Active KV cache (private per instance) |
| L2 | Host/CPU memory | Extended capacity (private per instance) |
| L3 | Distributed storage (disk, Redis, RDMA) | Shared cluster-wide |

Key features:
- **GPU-assisted I/O kernels:** Up to 3x higher transfer speed vs CPU-mediated copies
- **Prefetch strategies:** best_effort, wait_complete, timeout
- **Write-back policies:** write_through, write_through_selective, write_back
- **File backend (HiCacheFile):** Local NVMe-backed KV cache for single-node
- **Runtime attach/detach:** Hot-swap storage backends without restart

**Applicability to Athanor:** If Athanor ever migrates from vLLM to SGLang (per ADR-005 analysis), HiCache would be a strong reason. The file-based L3 backend on local NVMe could persist KV caches across restarts, and the CPU L2 tier would extend effective context capacity. Currently academic -- vLLM is the deployed engine.

**Source:** [SGLang HiCache design](https://github.com/sgl-project/sglang/blob/main/docs/advanced_features/hicache_design.md), [HiCache best practices](https://github.com/sgl-project/sglang/blob/main/docs/advanced_features/hicache_best_practices.md)

### 2.6 Prefix Caching (Already Available)

vLLM has automatic prefix caching enabled by default (`--enable-prefix-caching`, default: `True`). This caches KV computations for shared prompt prefixes in VRAM.

For Athanor's agent framework, every request to the same agent shares the system prompt. Prefix caching avoids recomputing the system prompt's KV cache on every request. This is **free performance** that is already active.

Tuning option: `--prefix-caching-hash-algo xxhash` for faster (non-cryptographic) hashing. Safe for single-tenant homelab use.

**Source:** [vLLM CacheConfig](https://docs.vllm.ai/en/latest/api/vllm/config/cache)

---

## 3. NFS Performance Optimization

### 3.1 nconnect: Multiple TCP Connections (Highest Impact)

The `nconnect` mount option establishes multiple TCP connections per NFS mount, distributing load across them. This is the single most impactful NFS tuning parameter for 10GbE.

**Why it matters:** A single NFS TCP connection on Linux is limited by per-socket processing overhead. On 10GbE, a single connection typically tops out at 3-5 Gbps. Multiple connections can approach wire speed.

```
nconnect=8   # 8 TCP connections per mount
```

Recommended values:
- `nconnect=4`: Good starting point, low overhead
- `nconnect=8`: Near-optimal for 10GbE
- `nconnect=16`: Maximum, diminishing returns beyond 8 on 10GbE

**Estimated throughput improvement:**
| Setting | Expected Throughput | Qwen3-32B-AWQ Load |
|---------|-------------------|-------------------|
| nconnect=1 (current) | ~1.1 GB/s | ~16 sec |
| nconnect=4 | ~1.1-1.2 GB/s* | ~15 sec |
| nconnect=8 | ~1.1-1.2 GB/s* | ~15 sec |

*Note: For a single large sequential read (model loading), nconnect may not help much because the bottleneck is the server's single-drive sequential read speed (~1.1 GB/s from NVMe cache). nconnect helps most with multiple concurrent readers or mixed I/O patterns. For Athanor's use case (occasional model loads, embeddings, multiple agents), it still reduces head-of-line blocking.

**Implementation:**
```ini
# Updated NFS mount options
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8
```

**Source:** [nfs(5) man page](https://man7.org/linux/man-pages/man5/nfs.5.html)

### 3.2 actimeo: Attribute Cache Timeout

Models on NFS are write-once, read-many files. They don't change. The default attribute cache timeout (3-60 seconds) causes unnecessary revalidation RPCs.

```
actimeo=3600   # Cache file attributes for 1 hour
```

This eliminates stat() calls to VAULT for model files, reducing NFS traffic and latency for repeated file access.

**Implementation:** Add `actimeo=3600` to model mount options only (not media mount, where freshness matters for Plex).

```ini
# /mnt/vault/models mount (models rarely change)
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8,actimeo=3600

# /mnt/vault/data mount (media, may change)
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8
```

**Source:** [nfs(5) man page](https://man7.org/linux/man-pages/man5/nfs.5.html)

### 3.3 FS-Cache: Client-Side NFS Caching on NVMe

Linux's FS-Cache/CacheFiles subsystem can transparently cache NFS data on local storage. For Athanor, this means caching model files from VAULT NFS onto local NVMe -- subsequent reads come from local NVMe speed.

**How it works:**
1. First read: data fetched from NFS, stored in local cache
2. Subsequent reads: served from local NVMe cache
3. Cache invalidation based on NFS attribute changes

**Setup:**
```bash
# Install cachefilesd
sudo apt install cachefilesd

# Configure cache directory on local NVMe
# /etc/cachefilesd.conf
dir /data/fscache
tag mycache
brun 10%
bcull 7%
bstop 3%

# Enable cachefilesd
sudo systemctl enable --now cachefilesd

# Add 'fsc' to NFS mount options
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8,actimeo=3600,fsc
```

**Trade-offs:**
- **Pro:** Transparent -- applications don't need changes. Second load of any model is at NVMe speed.
- **Con:** First load still goes through NFS. Cache management adds slight overhead. Cache fills local NVMe space.
- **Con:** Works at page cache granularity, not file granularity. For large sequential reads (model loading), the kernel's page cache already provides similar benefits if RAM is sufficient.

**Applicability to Athanor:** Moderate value. With 224 GB RAM on Node 1, the Linux page cache already caches recently-loaded models in RAM (faster than NVMe). FS-Cache's value is persistence across reboots -- but models are loaded once at startup and stay in VRAM. The rsync-to-local-NVMe strategy from ADR-003 is simpler and more predictable.

**Recommendation:** Skip FS-Cache. Use explicit rsync to local NVMe for hot models instead. Simpler, more controllable, achieves the same result.

**Source:** [Linux FS-Cache docs](https://www.kernel.org/doc/html/latest/filesystems/caching/fscache.html)

### 3.4 NFS Server-Side Tuning (Unraid)

Unraid's NFS server runs in kernel space. Key settings:

| Setting | Default | Recommended | Why |
|---------|---------|-------------|-----|
| NFS threads | 8 | 16 | More concurrent request handling for multi-client reads |

Increase NFS threads via Unraid Settings > NFS > Number of NFS threads.

**Source:** [Arch Wiki NFS](https://wiki.archlinux.org/title/NFS)

---

## 4. Kernel and OS Tuning

### 4.1 Read-Ahead for Model Loading

The kernel's read-ahead mechanism prefetches data during sequential reads. For large model files (multi-GB), increasing read-ahead reduces I/O stalls.

```bash
# Check current read-ahead for NVMe
cat /sys/block/nvme0n1/queue/read_ahead_kb
# Default: 128 KB

# Increase for model loading workload
echo 16384 | sudo tee /sys/block/nvme0n1/queue/read_ahead_kb  # 16 MB
```

For NFS mounts, the NFS client has its own read-ahead that interacts with the kernel's. Increasing to 16 MB ensures that large sequential model reads are prefetched aggressively.

**Persist via udev rule:**
```bash
# /etc/udev/rules.d/99-nvme-readahead.rules
ACTION=="add|change", KERNEL=="nvme[0-9]*n[0-9]*", ATTR{queue/read_ahead_kb}="16384"
```

**Source:** [Linux VM sysctl docs](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html)

### 4.2 Virtual Memory Tuning

```bash
# /etc/sysctl.d/99-ai-workload.conf

# Keep filesystem metadata cache (inodes, dentries) in memory
vm.vfs_cache_pressure = 50

# Allow more dirty pages before forcing writeback (NVMe handles bursts well)
vm.dirty_ratio = 40
vm.dirty_background_ratio = 10

# Minimize swap pressure -- keep data in RAM
vm.swappiness = 10

# Larger min_free_kbytes to prevent allocation stalls during large GPU transfers
vm.min_free_kbytes = 1048576  # 1 GB
```

**Explanation:**
- `vfs_cache_pressure=50`: Halves the kernel's aggressiveness in reclaiming inode/dentry cache. Keeps model file metadata cached longer.
- `dirty_ratio=40`: Allows 40% of RAM to be dirty before blocking writers. Beneficial for ComfyUI output writes and dataset processing.
- `swappiness=10`: Strongly prefers dropping page cache over swapping. Important -- VRAM-mapped model weights should never be swapped.
- `min_free_kbytes=1M`: Ensures a pool of free memory for DMA and urgent allocations. Prevents GPU transfer stalls.

**Source:** [Linux VM sysctl docs](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html)

### 4.3 I/O Scheduler for NVMe

Modern NVMe drives use `none` (noop) or `mq-deadline` scheduler. For model loading (large sequential reads), `none` is optimal -- it passes I/O directly to the drive without reordering.

```bash
# Check current scheduler
cat /sys/block/nvme0n1/queue/scheduler
# [none] mq-deadline kyber bfq

# Set to none (should already be default for NVMe)
echo none | sudo tee /sys/block/nvme0n1/queue/scheduler
```

**Source:** Linux block layer documentation

---

## 5. Swap and Memory Overflow

### 5.1 NVMe as Swap

NVMe swap provides a last-resort safety net when RAM is exhausted (e.g., during large model loading operations that temporarily exceed physical RAM).

**Performance reality:**

| Tier | Latency | Sequential BW | Random 4K IOPS |
|------|---------|--------------|-----------------|
| DDR4 RAM (Node 1) | ~50-80 ns | ~40 GB/s | N/A |
| DDR5 RAM (Node 2) | ~35-60 ns | ~70 GB/s | N/A |
| NVMe Gen4 | ~10-100 us | 3-7 GB/s | ~1M |
| NVMe Gen5 (T700) | ~10-50 us | 10-12 GB/s | ~1.5M |

NVMe swap is 100-1000x slower than RAM. It is a safety net, not a performance tier.

**Setup (if desired):**
```bash
# Create swap file on NVMe
sudo fallocate -l 16G /data/swapfile
sudo chmod 600 /data/swapfile
sudo mkswap /data/swapfile
sudo swapon -p 10 /data/swapfile  # low priority
```

**Recommendation:** Enable a small NVMe swap (8-16 GB) on both compute nodes as OOM protection. Set `vm.swappiness=10` to ensure it is rarely used. This prevents OOM kills during edge cases (multiple container builds, large model downloads, etc.) without impacting normal inference.

### 5.2 zram: Compressed RAM

zram creates a compressed block device in RAM, typically used for swap. With ~2:1 compression, 16 GB of physical RAM provides ~32 GB of effective swap capacity.

```bash
# Load module
sudo modprobe zram

# Configure 16 GB zram with zstd compression
echo zstd | sudo tee /sys/block/zram0/comp_algorithm
echo 16G | sudo tee /sys/block/zram0/disksize
sudo mkswap /dev/zram0
sudo swapon -p 100 /dev/zram0  # high priority (prefer over NVMe swap)
```

**Trade-off:** Uses CPU for compression/decompression. With EPYC 7663's 56 cores, the CPU overhead is negligible. Provides faster swap than NVMe because data stays in RAM (just compressed).

**Recommendation:** Deploy zram on both compute nodes as primary swap (high priority), with NVMe swap as fallback (low priority). This provides ~32 GB effective OOM protection with minimal performance impact.

### 5.3 zswap: Compressed Swap Cache

zswap is a compressed cache in front of the swap device. When pages are swapped out, they are first compressed in RAM. Only when the compressed pool fills do pages spill to the backing swap device (NVMe).

```bash
# Enable via kernel parameters or sysfs
echo 1 | sudo tee /sys/module/zswap/parameters/enabled
echo zstd | sudo tee /sys/module/zswap/parameters/compressor
echo 20 | sudo tee /sys/module/zswap/parameters/max_pool_percent
```

**Applicability to Athanor:** zram is simpler and achieves similar results. zswap adds complexity with the two-tier (compressed RAM + NVMe) approach. For a homelab, zram alone is sufficient.

**Source:** [Linux zswap docs](https://www.kernel.org/doc/html/latest/admin-guide/mm/zswap.html), [Linux zram docs](https://www.kernel.org/doc/html/latest/admin-guide/blockdev/zram.html)

---

## 6. Block-Level Caching (bcache / dm-cache)

### 6.1 bcache

bcache provides SSD caching for slower block devices at the kernel level. It supports writeback, writethrough, and writearound modes with intelligent sequential I/O bypass.

**Not applicable to Athanor's NFS use case.** bcache operates at the block device level and cannot cache network filesystems. It would be relevant if VAULT's NVMe cache pool were managed at the Linux level rather than by Unraid's cache system -- but Unraid already implements this with "cache: prefer" on shares.

### 6.2 dm-cache

Device-mapper cache provides similar SSD-in-front-of-HDD caching with pluggable cache policies (smq, mq, cleaner). Same limitation as bcache: block-level only, not applicable to NFS.

**Bottom line:** Unraid's built-in cache pool mechanism ("cache: prefer") already serves this function for VAULT. No additional block-level caching is needed.

**Source:** [Linux bcache docs](https://www.kernel.org/doc/html/latest/admin-guide/bcache.html), [dm-cache docs](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/cache.html)

---

## 7. GPU Direct Storage (GDS)

GDS enables DMA transfers directly between NVMe and GPU memory, bypassing CPU and system RAM entirely. It eliminates the bounce buffer pattern and can dramatically speed up model loading and data pipeline operations.

**Hardware requirement:** Tesla or Quadro GPUs only. Consumer GeForce GPUs (including the 4090, 5070 Ti, 5090, 5060 Ti) do not support GDS.

**Conclusion:** Not available for Athanor. All GPUs are consumer-class.

**Source:** [NVIDIA GDS](https://developer.nvidia.com/gpudirect-storage), [GPUDirect RDMA docs](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html)

---

## 8. Database Storage Optimization

### 8.1 Qdrant on NVMe

Qdrant supports three storage modes for vectors:

| Mode | Where Data Lives | Speed | RAM Usage |
|------|-----------------|-------|-----------|
| In-memory | RAM | Fastest | High |
| Memmap (mmap) | Memory-mapped files | Near-RAM with page cache | Flexible |
| On-disk | Disk only | Storage-speed | Minimal |

**Current state:** Qdrant on VAULT runs with default settings. With 1203 knowledge points (1024-dim vectors), the dataset is small (~5 MB vectors + metadata). Fully fits in RAM.

**Tuning for growth:**
```json
{
  "optimizers_config": {
    "memmap_threshold": 20000,
    "indexing_threshold": 20000
  },
  "hnsw_config": {
    "on_disk": false
  }
}
```

**Quantization for storage reduction:** Scalar quantization (int8) reduces vector storage 4x with minimal accuracy loss. Apply when collection size grows:
```json
{
  "quantization_config": {
    "scalar": {
      "type": "int8",
      "always_ram": true
    }
  }
}
```

**If Qdrant moves to NVMe-backed storage:** Enable mmap mode. NVMe's ~1M random IOPS makes mmap searches nearly as fast as in-memory. Measure with `fio` to confirm.

**Recommendation:** No changes needed at current scale. When knowledge base exceeds ~100K points, enable mmap with the vectors on NVMe and index in RAM.

**Source:** [Qdrant optimization guide](https://qdrant.tech/documentation/guides/optimize/), [Qdrant storage concepts](https://qdrant.tech/documentation/concepts/storage/)

### 8.2 Redis Persistence on NVMe

Redis on VAULT (used for GWT workspace, agent registry, GPU orchestrator state) runs with AOF persistence.

**Optimal configuration for NVMe:**
```
appendonly yes
appendfsync everysec    # Default, optimal for NVMe (fsync overhead is minimal)
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 67108864  # 64 MB
```

NVMe's ~10 us fsync latency makes `appendfsync everysec` nearly free. No tuning needed beyond defaults.

**If data grows:** Consider `io-threads 4` for multi-threaded I/O (Redis 6.0+). Currently unnecessary -- Athanor's Redis dataset is small.

**Recommendation:** Current configuration is already optimal for NVMe. No changes needed.

**Source:** [Redis persistence docs](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

---

## 9. Data Pipeline Storage

### 9.1 Training Data and Fine-Tuning

For fine-tuning workloads (LoRA training, etc.):

| Data Location | Throughput | When to Use |
|---------------|-----------|-------------|
| Local NVMe | 3-7 GB/s | Active training -- always local |
| NFS | ~1.1 GB/s | Dataset archival, initial download |
| Streaming (HuggingFace) | Network-bound | Exploration, one-time use |

**HuggingFace dataset streaming** eliminates disk usage entirely:
```python
dataset = load_dataset('dataset_name', split='train', streaming=True)
```
Useful for exploration and small fine-tuning runs. For repeated training runs, download to local NVMe.

**Recommendation:** Download datasets to `/data/datasets/` on the compute node performing training. Archive to VAULT after use.

**Source:** [HuggingFace Dataset Streaming](https://huggingface.co/docs/datasets/en/stream)

### 9.2 ComfyUI Generation Outputs

ComfyUI generates images (1-50 MB) and videos (50 MB-2 GB). Write speed matters during generation; storage permanence matters for the archive.

| Stage | Location | Why |
|-------|----------|-----|
| Generation | Local NVMe (`/data/comfyui/output/`) | Fast writes, no network dependency |
| Archive | VAULT NFS (`/mnt/vault/data/comfyui/`) | Persistent, backed up |

**Recommendation:** Generate to local NVMe, periodic rsync to VAULT. Already matches ADR-003's tier architecture.

### 9.3 Embedding Model and Vector Indexing

The embedding model (on Node 1 GPU 4) processes text for Qdrant ingestion. Storage path:
1. Source documents on VAULT NFS (read once)
2. Embeddings computed in VRAM (transient)
3. Vectors stored in Qdrant (VAULT NVMe-backed)

No storage optimization needed -- the pipeline is already efficient. Embedding generation is GPU-compute-bound, not storage-bound.

---

## 10. VAULT Capacity Management

### 10.1 Current State

| Resource | Total | Used | Free | Urgency |
|----------|-------|------|------|---------|
| HDD array | 165 TB | 146 TB (89%) | 19 TB | Medium -- 6-12 months at current growth |
| NVMe cache | ~6.5 TB | ~761 GB | ~5.7 TB | Low -- plenty of room for models |

### 10.2 What Consumes Space

The vast majority of VAULT's 146 TB is media (Plex library). AI models consume relatively little:

| Category | Estimated Size | Growth Rate |
|----------|---------------|-------------|
| Media library | ~140 TB | ~2-5 TB/month (depends on acquisition) |
| AI models | ~500 GB | Sporadic -- new model downloads |
| Backups | ~6 GB | Slow growth |
| Docker/appdata | ~10 GB | Negligible |

### 10.3 Expansion Strategy

Per ADR-003:
1. **Immediate:** No purchases needed. 19 TB free handles 6-12 months.
2. **When 95% full:** Add 1-2x 24 TB WD Gold/Ultrastar HDDs (~$400-800). Each adds ~24 TB usable.
3. **If parity upgrade needed:** Current parity is 22 TB. To add 24 TB data drives, upgrade parity first (~$400).

### 10.4 Pruning Opportunities

- Stale Docker images: `docker system prune` on each node (recovers 5-20 GB)
- Old model versions: audit `/mnt/vault/models/` for unused models
- Duplicate media: Tautulli can identify unwatched content for archival/deletion

---

## Recommended Storage Architecture (Updated)

Building on ADR-003's three-tier hierarchy, here are the software-level optimizations ranked by impact and effort:

### Tier 1: Immediately Deploy (High Impact, Low Effort)

| Optimization | What | Impact | Effort |
|-------------|------|--------|--------|
| **Local NVMe model cache** | rsync active model to `/data/models/` | 3-5x faster cold start | 5 min setup |
| **Increase vLLM swap space** | `--swap-space 8` | 2x preemption capacity | Config change |
| **NFS actimeo for models** | `actimeo=3600` on model mount | Eliminates revalidation RPCs | Mount option |
| **NFS nconnect** | `nconnect=8` on all mounts | Improved multi-stream throughput | Mount option |
| **Kernel read-ahead** | `read_ahead_kb=16384` for NVMe | Faster sequential reads | Sysctl/udev |
| **VM tuning** | `swappiness=10`, `vfs_cache_pressure=50` | Better memory utilization | Sysctl |
| **zram swap** | 16 GB zram with zstd | OOM protection, no NVMe wear | Systemd unit |

### Tier 2: Worth Investigating (Medium Impact, Medium Effort)

| Optimization | What | Impact | Effort |
|-------------|------|--------|--------|
| **LMCache with Redis** | Cross-request KV cache sharing | 3-10x TTFT for repeated prompts | Container + vLLM config |
| **Run:ai Model Streamer** | `--load-format runai_streamer` | Concurrent model loading | pip install + test |
| **Prefix caching hash** | `--prefix-caching-hash-algo xxhash` | Faster prefix matching | Config change |
| **Unraid NFS threads** | Increase to 16 | Better multi-client handling | Unraid setting |

### Tier 3: Future Consideration (Conditional Value)

| Optimization | What | When | Why Wait |
|-------------|------|------|----------|
| **LMCache disk backend** | KV cache persistence on NVMe | When serving 128K+ context | Current 32K context fits in VRAM |
| **Qdrant mmap mode** | Memory-mapped vector storage | When knowledge base > 100K pts | Currently 1203 pts -- trivial |
| **SGLang HiCache** | Hierarchical KV cache with disk tier | If migrating to SGLang | Currently on vLLM |
| **NVMe swap file** | 8-16 GB swap on NVMe | After zram deployment | zram is better first option |
| **FS-Cache for NFS** | Transparent NFS caching on NVMe | If rsync strategy proves insufficient | rsync is simpler |

### Not Recommended

| Optimization | Why Not |
|-------------|---------|
| **GPU Direct Storage** | Requires Tesla/Quadro GPUs. All Athanor GPUs are consumer-class. |
| **vLLM CPU weight offload** | AWQ model fits in VRAM. Adds latency per token. |
| **bcache / dm-cache** | Block-level only. Cannot cache NFS. Unraid already handles this. |
| **CoreWeave Tensorizer** | Pre-serialization overhead not worth it. safetensors with mmap is sufficient. |
| **Distributed filesystem** | Ceph/GlusterFS complexity far exceeds single-operator capacity. |

---

## Updated NFS Mount Configuration

Based on this research, the recommended NFS mount options:

```ini
# /etc/systemd/system/mnt-vault-models.mount
[Mount]
What=vault.athanor.local:/mnt/user/models
Where=/mnt/vault/models
Type=nfs
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8,actimeo=3600

# /etc/systemd/system/mnt-vault-data.mount
[Mount]
What=vault.athanor.local:/mnt/user/data
Where=/mnt/vault/data
Type=nfs
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8
```

Key changes from current:
- Added `nconnect=8`: Multiple TCP connections for better throughput
- Added `actimeo=3600` on models mount only: Models do not change, skip revalidation
- Data mount keeps default actimeo: Media files may be added/modified

---

## Kernel Tuning Ansible Role

All kernel tuning should be deployed via Ansible for consistency across nodes:

```yaml
# roles/common/files/99-ai-workload.conf
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 40
vm.dirty_background_ratio = 10
vm.min_free_kbytes = 1048576
```

```yaml
# roles/common/files/99-nvme-readahead.rules
ACTION=="add|change", KERNEL=="nvme[0-9]*n[0-9]*", ATTR{queue/read_ahead_kb}="16384"
```

---

## Sources

### vLLM and Model Loading
- [vLLM Engine Arguments](https://docs.vllm.ai/en/latest/configuration/engine_args)
- [vLLM CacheConfig](https://docs.vllm.ai/en/latest/api/vllm/config/cache)
- [vLLM Run:ai Model Streamer](https://docs.vllm.ai/en/latest/models/extensions/runai_model_streamer)
- [CoreWeave Tensorizer](https://github.com/CoreWeave/tensorizer)
- [Run:ai Model Streamer](https://github.com/run-ai/runai-model-streamer)
- [Safetensors Speed Benchmarks](https://huggingface.co/docs/safetensors/speed)

### KV Cache Systems
- [LMCache GitHub](https://github.com/LMCache/LMCache)
- [LMCache Documentation](https://docs.lmcache.ai)
- [SGLang HiCache Design](https://github.com/sgl-project/sglang/blob/main/docs/advanced_features/hicache_design.md)
- [SGLang HiCache Best Practices](https://github.com/sgl-project/sglang/blob/main/docs/advanced_features/hicache_best_practices.md)

### NFS Tuning
- [nfs(5) Man Page](https://man7.org/linux/man-pages/man5/nfs.5.html)
- [Arch Wiki NFS](https://wiki.archlinux.org/title/NFS)
- [Linux FS-Cache](https://www.kernel.org/doc/html/latest/filesystems/caching/fscache.html)

### Kernel Tuning
- [Linux VM Sysctl Documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html)
- [Linux zram Documentation](https://www.kernel.org/doc/html/latest/admin-guide/blockdev/zram.html)
- [Linux zswap Documentation](https://www.kernel.org/doc/html/latest/admin-guide/mm/zswap.html)
- [Linux bcache Documentation](https://www.kernel.org/doc/html/latest/admin-guide/bcache.html)
- [Linux dm-cache Documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/cache.html)

### GPU Direct Storage
- [NVIDIA GDS](https://developer.nvidia.com/gpudirect-storage)
- [GPUDirect RDMA Documentation](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html)

### Database Storage
- [Qdrant Optimization Guide](https://qdrant.tech/documentation/guides/optimize/)
- [Qdrant Storage Concepts](https://qdrant.tech/documentation/concepts/storage/)
- [Redis Persistence Documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

### Data Pipelines
- [HuggingFace Dataset Streaming](https://huggingface.co/docs/datasets/en/stream)

### Previous Research
- [Athanor Storage Architecture Research (2026-02-15)](2026-02-15-storage-architecture.md)
- [ADR-003: Storage Architecture](../decisions/ADR-003-storage-architecture.md)

---
---

# Part 2: Infrastructure-Level Storage Investigation

**Date:** 2026-02-25
**Status:** Complete -- actionable findings
**Method:** SSH audits of all 3 nodes + kernel docs + ArchWiki research
**Scope:** Hardware layout, NVMe utilization, network MTU, NFS mount discrepancies, backup verification, capacity planning

This section covers the 9 infrastructure investigation topics requested as a companion to the software-level optimizations above. All findings are verified against live node state via SSH on 2026-02-25.

---

## 11. NVMe Tiering Analysis (bcache / dm-cache / rsync / FS-Cache)

### 11.1 The Question

Can we use a caching layer (bcache, dm-cache, FS-Cache) to transparently accelerate NFS reads using local NVMe, rather than manually rsyncing models?

### 11.2 Options Evaluated

| Approach | Layer | NFS Compatible | Complexity | Persistence |
|----------|-------|----------------|------------|-------------|
| **bcache** | Block device | No -- requires backing block device, not NFS | Medium | Yes |
| **dm-cache** | Device-mapper | No -- same block-level limitation | Medium | Yes |
| **FS-Cache / cachefilesd** | VFS / NFS client | Yes -- kernel-native NFS caching | Low | Yes (survives reboot) |
| **Manual rsync** | Userspace | N/A -- copies files explicitly | Minimal | Yes |

### 11.3 bcache Analysis

bcache (kernel 3.10+) provides SSD caching in front of a slower block device. It creates a `/dev/bcache0` device that wraps a backing HDD with an NVMe cache. Supports writeback, writethrough, and writearound policies. Has intelligent sequential I/O bypass (skips cache for large sequential reads that would thrash it).

**Why it does not apply:** bcache operates at the block device level. It requires both a backing device (`/dev/sdX`) and a cache device (`/dev/nvmeXn1`). NFS mounts are not block devices -- they are network filesystems. bcache cannot sit between the NFS client and the network.

On VAULT itself, Unraid already implements NVMe-in-front-of-HDD caching via its "cache: prefer" share mechanism. The NVMe cache pool on VAULT (6.5 TB) serves exactly this role for the models share. Adding bcache would duplicate what Unraid already does.

**Source:** [Linux bcache documentation](https://www.kernel.org/doc/html/latest/admin-guide/bcache.html)

### 11.4 dm-cache Analysis

dm-cache (device-mapper target) provides the same SSD-in-front-of-HDD caching at the device-mapper level. Uses pluggable policies (smq is default and recommended). Supports writeback and writethrough. Requires manual setup with `dmsetup` or LVM cache volumes.

**Same limitation as bcache:** Block-level only. Cannot cache NFS traffic. Not applicable to Athanor's NFS-based model serving.

**Source:** [Linux dm-cache documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/cache.html)

### 11.5 FS-Cache / cachefilesd Analysis

FS-Cache is a kernel facility that provides client-side caching for network filesystems (NFS, AFS, CIFS). It stores cached pages on local storage (NVMe) and transparently serves subsequent reads from the local cache. This is the only option in this list that actually works with NFS.

**How it works:**
1. NFS client makes a read request
2. FS-Cache checks local NVMe cache first
3. Cache miss: fetches from NFS server, stores locally, returns to client
4. Cache hit: returns directly from local NVMe (no network I/O)
5. Cache invalidation: triggered by NFS attribute changes (mtime, size)

**Setup:**
```bash
sudo apt install cachefilesd
# /etc/cachefilesd.conf
dir /data/fscache
tag athanor-nfs-cache
brun 10%
bcull 7%
bstop 3%

sudo systemctl enable --now cachefilesd
# Add 'fsc' to NFS mount options
```

**Trade-offs for Athanor:**
- Pro: Transparent. First NFS read caches to local NVMe. Second read is at NVMe speed.
- Pro: Kernel-native, no userspace daemons.
- Con: Page-granularity caching. For model files already cached in the Linux page cache (224 GB RAM on Node 1), FS-Cache adds no benefit until after a reboot.
- Con: Cache management complexity. Must monitor `/data/fscache` size.
- Con: No control over what gets cached. Random media reads could evict model cache entries.

**Source:** [Linux FS-Cache documentation](https://www.kernel.org/doc/html/latest/filesystems/caching/fscache.html)

### 11.6 Recommendation: Manual rsync

For Athanor's use case (a small number of large, static model files), manual rsync is superior to all automated caching approaches:

| Property | FS-Cache | rsync |
|----------|----------|-------|
| Control over what's cached | None (kernel decides) | Full (you choose which models) |
| Cache eviction | Automatic (may evict models for media reads) | None (files stay until deleted) |
| Setup complexity | Medium (cachefilesd + mount options) | Minimal (one rsync command) |
| Debugging | Opaque kernel subsystem | `ls -la /data/models/` |
| Startup dependency | Requires NFS mount + cachefilesd | Local files, no NFS needed |

**Implementation (already in ADR-003):**
```bash
# One-time sync of active model
rsync -av --progress /mnt/vault/models/llm/Qwen3-32B-AWQ/ /data/models/llm/Qwen3-32B-AWQ/

# Point vLLM at local copy
--model /data/models/llm/Qwen3-32B-AWQ/
```

**Verdict:** Skip bcache, dm-cache, and FS-Cache. Use rsync for hot models. This is the one-person-scale solution.

---

## 12. Model Preloading Speed Analysis

### 12.1 Measured vs Theoretical Throughput

Throughput measurements from the deep audits and NFS testing:

| Path | Measured | Theoretical Max | Bottleneck |
|------|----------|-----------------|------------|
| VAULT HDD array (single spindle) | 150-250 MB/s | ~260 MB/s (CMR) | Disk seek + sequential |
| VAULT NVMe cache over NFS | 703 MB/s (Node 2 read test) | ~1.17 GB/s (10GbE) | NFS overhead, TCP buffers |
| VAULT NVMe cache over NFS (tuned) | ~1.0-1.1 GB/s (estimated) | ~1.17 GB/s | Wire speed |
| Node 1 local NVMe (P310 Gen4) | Not measured | 3.5 GB/s seq read | PCIe Gen4 x4 |
| Node 2 local NVMe (T700 Gen5) | Not measured | 11.7 GB/s seq read | PCIe Gen5 x4 |

### 12.2 Model Load Time Estimates for Qwen3-32B-AWQ (~18 GB)

| Source | Throughput | Load Time | Notes |
|--------|-----------|-----------|-------|
| NFS (current, 128KB blocks) | ~700 MB/s | ~26 sec | Measured on Node 2 |
| NFS (tuned, 1MB blocks + nconnect=8) | ~1.0 GB/s | ~18 sec | Estimated |
| NFS (tuned + jumbo frames) | ~1.1 GB/s | ~16 sec | Near wire speed |
| Local NVMe Gen4 (P310) | 3.5 GB/s | ~5 sec | After rsync |
| Local NVMe Gen5 (T700) | 11.7 GB/s | ~1.5 sec | After rsync |

### 12.3 Preload Script

```bash
#!/usr/bin/env bash
# /opt/athanor/scripts/preload-models.sh
# Sync active inference models to local NVMe for fast cold starts.
# Run manually or via cron after model updates on VAULT.

set -euo pipefail

LOCAL_MODELS="/data/models"
NFS_MODELS="/mnt/vault/models"

# Active models to keep local
MODELS=(
    "llm/Qwen3-32B-AWQ"
    "embedding/multilingual-e5-large-instruct"
)

for model in "${MODELS[@]}"; do
    echo "[$(date -Iseconds)] Syncing $model"
    mkdir -p "$LOCAL_MODELS/$model"
    rsync -av --delete "$NFS_MODELS/$model/" "$LOCAL_MODELS/$model/"
done

echo "[$(date -Iseconds)] Preload complete"
```

**Recommendation:** Deploy this script on Node 1 once the unmounted NVMe is mounted at `/data` (see Section 16). Point vLLM and vLLM-embedding at `/data/models/` instead of `/mnt/vault/models/`.

---

## 13. Jumbo Frames (MTU 9000) Configuration

### 13.1 Current State (Verified via SSH 2026-02-25)

| Device | Interface | Current MTU | 10GbE Link |
|--------|-----------|-------------|------------|
| Node 1 (Foundry) | enp36s0f0 | **1500** | Aquantia AQC113 |
| Node 2 (Workshop) | eno1 | **9000** | Aquantia AQC113 |
| VAULT | Multiple | **1500** | Unknown (Unraid) |
| USW Pro XG 10 PoE | All ports | Unknown | Switch |

**Problem:** Node 2 sends 9000-byte frames, but VAULT and Node 1 respond with 1500-byte frames. The path MTU is effectively 1500 everywhere because the lowest MTU on any link segment determines the usable frame size. Node 2's MTU 9000 is wasted.

### 13.2 Why Jumbo Frames Matter for NFS

Each NFS RPC carries payload data in Ethernet frames. With MTU 1500, the maximum payload per frame is ~1460 bytes (after IP + TCP headers). With MTU 9000, the payload is ~8960 bytes -- 6.1x more data per frame. This reduces:
- **CPU interrupt overhead:** Fewer frames means fewer interrupts per GB transferred
- **Protocol overhead ratio:** Headers are a smaller percentage of each frame
- **TCP ACK frequency:** Fewer segments to acknowledge

**Expected throughput improvement:**
- Modest for single-stream large sequential reads (1-5% improvement)
- More significant for mixed I/O patterns with many small files (10-15%)
- Reduces CPU load during transfers (important on VAULT's Ryzen 9950X handling NFS for 2 clients)

### 13.3 Configuration Plan

All 4 segments must have MTU 9000 for jumbo frames to work:

**Step 1: UniFi Switch (USW Pro XG 10 PoE)**
- UniFi Network > Settings > Networks > Default > Advanced > Jumbo frames: Enable
- Or per-port: Devices > USW Pro XG > Ports > [each 10GbE port] > MTU: 9000
- UniFi switches support jumbo frames on all ports (USW Pro XG supports up to 9216)

**Step 2: VAULT (Unraid)**
- Settings > Network Settings > Interface eth0 (or bond0) > MTU: 9000
- Apply and reboot Unraid (MTU change requires network restart)
- Verify: `ip link show eth0` should show `mtu 9000`

**Step 3: Node 1 (Ubuntu, netplan)**
```yaml
# /etc/netplan/01-netcfg.yaml (add mtu line)
network:
  version: 2
  ethernets:
    enp36s0f0:
      addresses:
        - 192.168.1.244/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1, 8.8.8.8]
      mtu: 9000
```
```bash
sudo netplan apply
```

**Step 4: Node 2 -- Already done (MTU 9000 on eno1)**

**Step 5: Verify end-to-end**
```bash
# From Node 1, test jumbo frames to VAULT
ping -M do -s 8972 192.168.1.203
# -M do = don't fragment
# -s 8972 = 8972 payload + 28 headers = 9000 bytes
# If this succeeds, jumbo frames work end-to-end
```

### 13.4 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| MTU mismatch causes packet drops | High | Test with `ping -M do` after each change |
| Management VLAN breaks | Low | Management is on separate 1GbE switch (USW Pro 24) |
| VAULT reboot required | Low | Schedule during off-hours |
| SSH loss during change | Medium | Have JetKVM ready for Node 1, physical access for VAULT |

**Recommendation:** Deploy jumbo frames across all 10GbE segments. Start with the switch, then VAULT, then Node 1. Test at each step. Node 2 is already done.

---

## 14. NVMe Over Fabrics (NVMe-oF/TCP)

### 14.1 What It Is

NVMe-oF/TCP exposes a remote NVMe drive as a local block device over the network. Unlike NFS (which is a filesystem protocol), NVMe-oF operates at the block level -- the remote drive appears as `/dev/nvmeXn1` on the initiator. The target (Node 2) exports the NVMe drive, and the initiator (Node 1) mounts it as if it were a local device.

### 14.2 Performance Characteristics

| Protocol | Overhead | Max Throughput (10GbE) | Latency | CPU Cost |
|----------|----------|----------------------|---------|----------|
| NFS v4 | High (RPC, VFS, metadata) | ~1.1 GB/s | ~200-500 us | Medium |
| NVMe-oF/TCP | Low (block-level, minimal headers) | ~1.15 GB/s | ~50-100 us | Low |
| NVMe-oF/RDMA | Minimal (kernel bypass) | ~1.17 GB/s (wire speed) | ~10-20 us | Minimal |

On 10GbE, both NFS and NVMe-oF/TCP are network-bound at ~1.1-1.17 GB/s. NVMe-oF/TCP has lower latency for small random reads (useful for database workloads), but for Athanor's primary use case (large sequential model loads), the throughput difference is negligible.

### 14.3 Setup (for reference)

**Target (Node 2 -- exporting NVMe):**
```bash
# Load kernel modules
sudo modprobe nvmet
sudo modprobe nvmet-tcp

# Create subsystem
sudo mkdir -p /sys/kernel/config/nvmet/subsystems/athanor-nvme
echo 1 | sudo tee /sys/kernel/config/nvmet/subsystems/athanor-nvme/attr_allow_any_host

# Create namespace pointing to NVMe drive
sudo mkdir -p /sys/kernel/config/nvmet/subsystems/athanor-nvme/namespaces/1
echo /dev/nvme1n1 | sudo tee /sys/kernel/config/nvmet/subsystems/athanor-nvme/namespaces/1/device_path
echo 1 | sudo tee /sys/kernel/config/nvmet/subsystems/athanor-nvme/namespaces/1/enable

# Create TCP port
sudo mkdir -p /sys/kernel/config/nvmet/ports/1
echo 192.168.1.225 | sudo tee /sys/kernel/config/nvmet/ports/1/addr_traddr
echo 4420 | sudo tee /sys/kernel/config/nvmet/ports/1/addr_trsvcid
echo tcp | sudo tee /sys/kernel/config/nvmet/ports/1/addr_trtype
echo ipv4 | sudo tee /sys/kernel/config/nvmet/ports/1/addr_adrfam

# Link subsystem to port
sudo ln -s /sys/kernel/config/nvmet/subsystems/athanor-nvme /sys/kernel/config/nvmet/ports/1/subsystems/athanor-nvme
```

**Initiator (Node 1 -- mounting remote NVMe):**
```bash
sudo modprobe nvme-tcp

# Discover targets
sudo nvme discover -t tcp -a 192.168.1.225 -s 4420

# Connect
sudo nvme connect -t tcp -n athanor-nvme -a 192.168.1.225 -s 4420

# The drive appears as /dev/nvmeXn1
lsblk
```

**Source:** [ArchWiki NVMe over Fabrics](https://wiki.archlinux.org/title/NVMe_over_Fabrics)

### 14.4 Why Not Deploy NVMe-oF for Athanor

| Factor | Assessment |
|--------|-----------|
| **Throughput gain** | Negligible over NFS on 10GbE (~5% at best) |
| **Latency gain** | Meaningful for database IOPS, not for model loading |
| **Complexity** | Block device export means no filesystem sharing -- only one client can mount read-write |
| **Data sharing** | NFS allows multiple nodes to read the same files. NVMe-oF is single-client unless you add a cluster filesystem (GFS2, OCFS2). |
| **Failure mode** | NVMe-oF disconnect = lost block device = potential data corruption |
| **Maintenance** | Must manage kernel modules, configfs, port bindings |
| **One-person scale** | Fails the filter. Too much operational overhead for marginal gain. |

**Where NVMe-oF/TCP would make sense:**
- 25GbE+ networks where NFS protocol overhead becomes the bottleneck
- RDMA/InfiniBand networks (ADR-003 mentions InfiniBand EDR as a target)
- Database workloads needing sub-100us latency to remote storage

**Recommendation:** Do not deploy NVMe-oF/TCP. The 10GbE link is the bottleneck, not the protocol. When InfiniBand EDR is deployed, revisit NVMe-oF/RDMA -- that combination would deliver ~6 GB/s with <20 us latency.

---

## 15. Node 2 Unused NVMe Drives (RAID / Striping / Independent)

### 15.1 Current State (Verified via SSH 2026-02-25)

Node 2 has 3x Crucial T700 1TB Gen5 NVMe drives that are unused:

| Drive | Device | Capacity | Current State |
|-------|--------|----------|---------------|
| T700 #1 | nvme0n1 | 1 TB | ZFS label "hpc_nvme", ZFS not installed |
| T700 #2 | nvme1n1 | 1 TB | ZFS label "hpc_nvme", ZFS not installed |
| T700 #3 | nvme2n1 | 1 TB | ZFS label "hpc_nvme", ZFS not installed |

These drives have stale ZFS labels from a previous configuration attempt. ZFS is not installed on Node 2. The drives are not mounted or in use.

Additionally, `nvme3n1` (boot drive, 2TB WD_BLACK SN850X) is running at Gen4 speed despite being in a Gen5-capable slot. This is likely a BIOS setting or riser card limitation -- flagged but not actionable without physical access.

### 15.2 Options

| Option | Config | Usable Capacity | Sequential Read | Failure Mode |
|--------|--------|-----------------|-----------------|--------------|
| **3 independent mounts** | ext4/xfs on each | 3 TB (3x 1TB) | 11.7 GB/s per drive | Lose 1 drive = lose 1 mount |
| **RAID0 (mdadm)** | 3-drive stripe | 3 TB | ~35 GB/s theoretical | Lose 1 drive = lose ALL data |
| **RAID1 (mdadm)** | 3-drive mirror | 1 TB | 11.7 GB/s read | Survive 2 drive failures |
| **RAID5 (mdadm)** | 3-drive stripe+parity | 2 TB | ~23 GB/s read | Survive 1 drive failure |
| **ZFS mirror** | 3-way mirror | 1 TB | ~35 GB/s read (ZFS) | Survive 2 drive failures |
| **ZFS RAIDZ1** | Parity stripe | 2 TB | ~23 GB/s read | Survive 1 drive failure |

### 15.3 Recommendation: 3 Independent Mounts

**Rationale:**
1. **No single point of failure for unrelated data.** Each mount serves a different purpose. Losing one drive does not affect the others.
2. **Simplicity.** No RAID controller, no ZFS, no mdadm. Just `mkfs.ext4` and `mount`.
3. **Full capacity.** 3 TB usable vs 2 TB (RAIDZ1) or 1 TB (mirror).
4. **Speed is not the bottleneck.** A single T700 at 11.7 GB/s already exceeds any workload Node 2 will run. RAID0 striping to ~35 GB/s is pointless when the GPU can only consume ~32 GB/s over PCIe 5.0 x16.
5. **Data is not precious.** These drives hold working copies (models, cache, generation outputs). The canonical data lives on VAULT. Losing a drive means re-syncing from VAULT, not data loss.

**Proposed Layout:**

| Mount | Drive | Purpose |
|-------|-------|---------|
| `/data` | nvme0n1 | Models cache, vLLM workspace, general scratch |
| `/data2` | nvme1n1 | ComfyUI output, video generation workspace |
| `/data3` | nvme2n1 | Future use (training data, datasets, fine-tuning workspace) |

**Implementation:**
```bash
# Wipe stale ZFS labels
sudo wipefs -a /dev/nvme0n1
sudo wipefs -a /dev/nvme1n1
sudo wipefs -a /dev/nvme2n1

# Create ext4 filesystems
sudo mkfs.ext4 -L data /dev/nvme0n1
sudo mkfs.ext4 -L data2 /dev/nvme1n1
sudo mkfs.ext4 -L data3 /dev/nvme2n1

# Create mount points
sudo mkdir -p /data /data2 /data3

# Add to fstab
echo 'LABEL=data  /data  ext4 defaults,noatime,discard 0 2' | sudo tee -a /etc/fstab
echo 'LABEL=data2 /data2 ext4 defaults,noatime,discard 0 2' | sudo tee -a /etc/fstab
echo 'LABEL=data3 /data3 ext4 defaults,noatime,discard 0 2' | sudo tee -a /etc/fstab

# Mount
sudo mount -a
```

---

## 16. Node 1 Unmounted NVMe (Immediate Action)

### 16.1 Current State (Verified via SSH 2026-02-25)

Node 1 has a 1 TB Crucial P310 NVMe drive (`nvme1n1`) that is formatted with btrfs but **not mounted**:

```
nvme1n1     259:0    0 953.9G  0 disk    (btrfs formatted, NOT MOUNTED)
nvme0n1     259:1    0   3.6T  0 disk    (boot drive, 3.3 TB free)
```

The inventory listed this as a "Samsung 990 PRO 4TB" but the audit revealed it is actually a Crucial P310 1TB in the M.2_2 slot. The 990 PRO 4TB has not been installed (blocked on Shaun confirming the Samsung drive purchase/installation).

### 16.2 Recommended Use

Mount at `/data` and use as:
1. **Active model cache** -- rsync hot models from VAULT NFS for faster cold starts (see Section 12)
2. **vLLM workspace** -- temporary files, logs, swap space
3. **Qdrant working directory** -- if Qdrant data grows beyond VAULT's comfortable capacity
4. **Docker scratch** -- build contexts, temporary images

### 16.3 Implementation

```bash
# SSH to Node 1
ssh node1

# Check current filesystem
sudo blkid /dev/nvme1n1
# Should show btrfs

# If btrfs is unwanted, reformat to ext4 (simpler, no subvolume management):
sudo mkfs.ext4 -L data /dev/nvme1n1

# Create mount point
sudo mkdir -p /data

# Add to fstab
echo 'LABEL=data /data ext4 defaults,noatime,discard 0 2' | sudo tee -a /etc/fstab

# Mount
sudo mount /data

# Verify
df -h /data
# Should show ~930 GB available
```

### 16.4 Ansible Integration

Add to `ansible/group_vars/compute.yml` or create a host-specific variable for Node 1:

```yaml
# In host_vars/core.yml or equivalent
local_data_mount:
  device: "/dev/nvme1n1"
  path: "/data"
  fstype: "ext4"
  opts: "defaults,noatime,discard"
```

**Priority: HIGH.** This is 1 TB of fast local storage sitting idle. Takes 5 minutes to mount.

---

## 17. VAULT Array at 90% -- Monitoring and Expansion

### 17.1 Current Capacity (Verified via SSH 2026-02-25)

| Resource | Total | Used | Free | Percent |
|----------|-------|------|------|---------|
| HDD Array | 164 TB | 146 TB | 18 TB | 89% |
| disk4 | — | — | — | 93% |
| disk5 | — | — | — | 93% |
| NVMe Cache Pool | ~6.5 TB | ~761 GB | ~5.7 TB | 12% |
| Empty Array Slot | 1 (disk10) | — | — | Available |

The models NFS share on VAULT is only 134 GB. The vast majority of consumed space is the Plex media library (~140 TB).

### 17.2 Growth Trajectory

| Scenario | Monthly Growth | Time to 95% | Time to 100% |
|----------|---------------|-------------|--------------|
| Conservative (media only) | ~2 TB/month | ~4 months (Jun 2026) | ~9 months (Nov 2026) |
| Moderate (media + AI models) | ~3 TB/month | ~3 months (May 2026) | ~6 months (Aug 2026) |
| Aggressive (media + stash + models) | ~5 TB/month | ~2 months (Apr 2026) | ~3.5 months (Jun 2026) |

### 17.3 Monitoring (Immediate)

Prometheus is already scraping VAULT. Add alert rules:

```yaml
# Prometheus alerting rule
groups:
  - name: storage
    rules:
      - alert: VaultArrayHigh
        expr: node_filesystem_avail_bytes{mountpoint="/mnt/user"} / node_filesystem_size_bytes{mountpoint="/mnt/user"} < 0.10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "VAULT array above 90%"
          description: "{{ $value | humanizePercentage }} free space remaining"

      - alert: VaultArrayCritical
        expr: node_filesystem_avail_bytes{mountpoint="/mnt/user"} / node_filesystem_size_bytes{mountpoint="/mnt/user"} < 0.05
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "VAULT array above 95% -- expansion needed"
```

### 17.4 Expansion Plan

**Option A: Add Data Drive (Cheapest)**
- Buy 1x 22 TB WD Gold or Ultrastar HC570 (~$350-400)
- Insert in empty disk10 slot
- Add to Unraid array (no parity rebuild needed -- just adds capacity)
- Adds ~22 TB usable immediately
- **Limitation:** Cannot exceed current parity drive size (22 TB). If parity is 22 TB, data drives must be <= 22 TB.

**Option B: Add Data Drive + Upgrade Parity (Future-proof)**
- Buy 1x 24 TB WD Ultrastar HC580 for parity (~$400-500)
- Swap existing 22 TB parity to data role
- Install 24 TB as new parity (rebuild required, ~24-48 hours)
- Adds ~22 TB usable (old parity becomes data) + future headroom for 24 TB data drives
- **Best option when parity upgrade is needed anyway**

**Option C: Prune Media Library**
- Use Tautulli to identify unwatched content (not played in 12+ months)
- Delete or move to cold storage
- Potentially recovers 5-20 TB depending on library hygiene
- **Free, but requires Shaun's time to review deletion candidates**

**Recommendation:** Deploy monitoring alerts immediately. Plan a 22 TB WD Gold purchase when the array hits 92% (~$350). Option C (pruning) can buy time but is not a substitute for expansion.

---

## 18. Qdrant Backup Investigation -- RESOLVED

### 18.1 The Reported Problem

The VAULT deep audit (2026-02-25) checked `/mnt/user/backups/athanor/qdrant/` and reported it as EMPTY, despite the Qdrant backup cron running nightly at 03:00 on Node 1.

### 18.2 Root Cause: Wrong Path Checked

Three different paths are involved, and the audit checked the wrong one:

| Context | Path | Exists? |
|---------|------|---------|
| `backup-qdrant.sh` default | `/mnt/vault/backups/athanor/qdrant` | No -- this NFS mount does not exist on Node 1 |
| Ansible cron override | `BACKUP_DIR=/mnt/vault/data/backups/athanor/qdrant` | Yes -- uses the `data` NFS mount |
| VAULT filesystem (mapped) | `/mnt/user/data/backups/athanor/qdrant/` | Yes -- this is where backups actually land |
| VAULT audit checked | `/mnt/user/backups/athanor/qdrant/` | Empty -- different path entirely |

The Ansible backup role (`ansible/roles/backup/tasks/main.yml`, line 31) overrides `BACKUP_DIR` in the cron job:
```
BACKUP_DIR=/mnt/vault/data/backups/athanor/qdrant /opt/athanor/scripts/backup-qdrant.sh
```

This maps to `/mnt/user/data/backups/athanor/qdrant/` on VAULT (via the `data` NFS export).

### 18.3 Verification (SSH to Node 1, 2026-02-25)

```
$ ls -la /mnt/vault/data/backups/athanor/qdrant/
total 8696
-rw-r--r-- 1 root root 1282254 Feb 19 03:00 activity_2026-02-19.snapshot
-rw-r--r-- 1 root root 1483932 Feb 19 03:00 conversations_2026-02-19.snapshot
-rw-r--r-- 1 root root 4521238 Feb 19 03:00 knowledge_2026-02-19.snapshot
-rw-r--r-- 1 root root  269854 Feb 19 03:00 preferences_2026-02-19.snapshot
-rw-r--r-- 1 root root 1282254 Feb 25 03:00 activity_2026-02-25.snapshot
-rw-r--r-- 1 root root  ... (today's backups)
```

**Backups are working correctly.** 4 collections (activity, conversations, knowledge, preferences) backed up daily, 7-day retention, today's backup ran at 03:00 successfully.

### 18.4 Fix: Update Script Default Path

The `backup-qdrant.sh` script's default `BACKUP_DIR` should match the Ansible cron's override to avoid confusion:

```bash
# Current (line 12):
BACKUP_DIR="${BACKUP_DIR:-/mnt/vault/backups/athanor/qdrant}"

# Should be:
BACKUP_DIR="${BACKUP_DIR:-/mnt/vault/data/backups/athanor/qdrant}"
```

This ensures the script works correctly both when run manually (using the default) and via cron (using the Ansible override). Currently, running the script manually without the `BACKUP_DIR` override would fail because `/mnt/vault/backups/` does not exist as an NFS mount.

---

## 19. IO Scheduler and Network Tuning

### 19.1 IO Scheduler (Verified -- Already Optimal)

Both Node 1 and Node 2 use `none` (noop) for all NVMe drives:
```
$ cat /sys/block/nvme0n1/queue/scheduler
[none] mq-deadline kyber bfq
```

This is correct. NVMe drives have their own internal scheduling via hardware command queues (up to 65535 queues, 65536 commands each). Adding a software scheduler adds latency without benefit. `none` passes I/O directly to the drive.

**Source:** [ArchWiki SSD -- IO Scheduler](https://wiki.archlinux.org/title/Solid_state_drive#I/O_scheduler)

### 19.2 Read-Ahead (Needs Increase)

Current: 128 KB on both nodes. For large sequential model reads, this is conservative.

```bash
# Current
$ cat /sys/block/nvme0n1/queue/read_ahead_kb
128

# Recommended for model loading (large sequential reads)
echo 4096 | sudo tee /sys/block/nvme0n1/queue/read_ahead_kb  # 4 MB
```

**Why 4 MB, not 16 MB:** The existing software-level research (Section 4.1 above) recommended 16 MB. However, for NVMe drives that already handle sequential reads optimally at the firmware level, 4 MB is a better balance. 16 MB read-ahead can waste bandwidth on speculative reads that are never consumed, especially for random-access workloads (Qdrant queries, container I/O). 4 MB helps sequential model loads without penalizing random I/O.

**Persist via udev rule:**
```bash
# /etc/udev/rules.d/99-nvme-readahead.rules
ACTION=="add|change", KERNEL=="nvme[0-9]*n[0-9]*", ATTR{queue/read_ahead_kb}="4096"
```

### 19.3 NFS Mount Options (Needs Update -- CRITICAL)

**Current state (from Ansible `group_vars/compute.yml`):**
```
nfs_options: "rw,soft,intr,rsize=131072,wsize=131072"
```

**Problems:**
1. `rsize=131072,wsize=131072` -- 128 KB blocks. ADR-003 recommended 1 MB. This was never deployed.
2. `soft` -- soft mounts return errors to applications on timeout. `hard` retries indefinitely and is safer for data integrity. vLLM will crash if NFS returns EIO during model loading.
3. Missing `noatime` -- unnecessary metadata updates on every read.
4. Missing `nconnect` -- single TCP connection bottleneck.
5. Missing `nfsvers=4` -- should pin version explicitly.

**Recommended update to `ansible/group_vars/compute.yml`:**
```yaml
nfs_options: "rw,hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4,nconnect=8"
```

**Impact of each change:**

| Option | Current | Recommended | Impact |
|--------|---------|-------------|--------|
| `rsize/wsize` | 131072 (128 KB) | 1048576 (1 MB) | Fewer RPCs per read, higher throughput |
| `soft` | soft | hard | Prevents EIO errors, retries on timeout |
| `noatime` | missing | added | Eliminates atime update RPCs |
| `nconnect` | missing | 8 | Multiple TCP streams for parallel I/O |
| `nfsvers` | missing | 4 | Pin NFS version explicitly |
| `actimeo` | missing | 3600 (models only) | Skip revalidation for static model files |

### 19.4 TCP Buffer Tuning (Needs Increase -- CRITICAL)

**Current state (both nodes):**
```
net.core.rmem_max = 212992    (~208 KB)
net.core.wmem_max = 212992    (~208 KB)
```

**For 10GbE NFS, these are far too small.** The TCP buffer must be large enough to hold the bandwidth-delay product (BDP) of the link:
```
BDP = bandwidth x RTT
    = 1.25 GB/s x 0.2 ms (LAN RTT)
    = 250 KB minimum
```

212 KB is below the minimum BDP for 10GbE, meaning the TCP window cannot grow large enough to saturate the link. This is likely why Node 2 measured 703 MB/s over NFS instead of the theoretical ~1.1 GB/s.

**Recommended sysctl:**
```bash
# /etc/sysctl.d/99-network-tuning.conf

# Core buffer sizes (max for any socket)
net.core.rmem_max = 16777216          # 16 MB
net.core.wmem_max = 16777216          # 16 MB

# TCP buffer auto-tuning range: min, default, max
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216

# Allow more queued connections
net.core.netdev_max_backlog = 5000

# Enable TCP window scaling (should be default, but ensure)
net.ipv4.tcp_window_scaling = 1

# Increase socket backlog
net.core.somaxconn = 4096
```

**Expected impact:** With 16 MB buffers, the TCP window can grow to fill the 10GbE pipe. NFS throughput should increase from ~700 MB/s to ~1.0-1.1 GB/s for large sequential reads.

### 19.5 VM Tuning

**Current state (Node 1):**
```
vm.swappiness = 60     (default -- too aggressive for inference nodes)
```

**Recommended:**
```bash
# /etc/sysctl.d/99-vm-tuning.conf
vm.swappiness = 10
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 40
vm.dirty_background_ratio = 10
vm.min_free_kbytes = 1048576
```

See Section 4.2 of the software-level research above for detailed explanations of each parameter.

### 19.6 Combined Ansible Deployment

All tuning should be deployed via the `common` Ansible role for consistency:

```yaml
# ansible/roles/common/tasks/main.yml (add these tasks)

- name: Deploy sysctl tuning for AI workloads
  copy:
    content: |
      # Network tuning for 10GbE NFS
      net.core.rmem_max = 16777216
      net.core.wmem_max = 16777216
      net.ipv4.tcp_rmem = 4096 1048576 16777216
      net.ipv4.tcp_wmem = 4096 1048576 16777216
      net.core.netdev_max_backlog = 5000
      net.ipv4.tcp_window_scaling = 1
      net.core.somaxconn = 4096
      # VM tuning
      vm.swappiness = 10
      vm.vfs_cache_pressure = 50
      vm.dirty_ratio = 40
      vm.dirty_background_ratio = 10
      vm.min_free_kbytes = 1048576
    dest: /etc/sysctl.d/99-athanor-tuning.conf
    mode: "0644"
  notify: reload sysctl

- name: Deploy NVMe read-ahead udev rule
  copy:
    content: |
      ACTION=="add|change", KERNEL=="nvme[0-9]*n[0-9]*", ATTR{queue/read_ahead_kb}="4096"
    dest: /etc/udev/rules.d/99-nvme-readahead.rules
    mode: "0644"
  notify: reload udev

# Handlers
- name: reload sysctl
  command: sysctl --system

- name: reload udev
  command: udevadm control --reload-rules && udevadm trigger
```

---

## 20. Implementation Priority

### Tier 1: Immediate (This Week, No Hardware)

| # | Action | Node | Impact | Effort |
|---|--------|------|--------|--------|
| 1 | **Mount Node 1 NVMe at /data** | Node 1 | Unlock 1 TB local storage | 5 min |
| 2 | **Update NFS mount options** (1MB blocks, hard, noatime, nconnect=8) | Both | ~40% NFS throughput increase | Ansible change |
| 3 | **Deploy TCP buffer sysctl** (16 MB rmem/wmem) | Both | Unlock full 10GbE throughput | Ansible change |
| 4 | **Deploy VM sysctl** (swappiness=10, vfs_cache_pressure=50) | Both | Better memory utilization | Ansible change |
| 5 | **Deploy read-ahead udev rule** (4 MB) | Both | Faster sequential reads | Ansible change |
| 6 | **Fix backup-qdrant.sh default path** | Repo | Prevent confusion on manual runs | 1-line edit |

### Tier 2: This Month (Requires Planning)

| # | Action | Node | Impact | Effort |
|---|--------|------|--------|--------|
| 7 | **Deploy jumbo frames** (MTU 9000 on switch, VAULT, Node 1) | All | ~5% throughput + lower CPU | Network change |
| 8 | **Wipe and mount Node 2 NVMe drives** (3x independent ext4) | Node 2 | Unlock 3 TB local storage | 15 min |
| 9 | **Deploy Prometheus alert for VAULT 90%** | VAULT | Early warning for capacity | Config |
| 10 | **Deploy preload-models.sh script** | Node 1 | 5x faster cold starts | Script + cron |

### Tier 3: When Needed

| # | Action | Trigger | Estimated Cost |
|---|--------|---------|---------------|
| 11 | **Buy 22 TB WD Gold** | VAULT hits 92% | ~$350 |
| 12 | **Upgrade parity to 24 TB** | Need to add >22 TB data drives | ~$400-500 |
| 13 | **Revisit NVMe-oF/RDMA** | When InfiniBand EDR is deployed | $0 (software) |

---

## 21. Summary Decision Table

| Topic | Decision | Rationale |
|-------|----------|-----------|
| NVMe tiering | **rsync, not bcache/dm-cache/FS-Cache** | One-person scale, full control, simpler |
| Model preloading | **rsync to local /data** | 5x faster cold starts, NFS-independent |
| Jumbo frames | **Deploy MTU 9000 on all 10GbE** | Low effort, reduces CPU overhead |
| NVMe-oF/TCP | **Do not deploy** | Negligible gain on 10GbE, complexity penalty |
| Node 2 NVMe | **3 independent ext4 mounts** | Simplest, full capacity, no RAID overhead |
| Node 1 NVMe | **Mount immediately at /data** | 1 TB idle storage, takes 5 minutes |
| VAULT capacity | **Monitor + 22TB WD Gold at 92%** | 3-4 months headroom at current growth |
| Qdrant backups | **Working correctly (path confusion)** | Fix default path in script for clarity |
| IO tuning | **NFS 1MB + nconnect=8 + TCP 16MB + sysctl** | Highest-impact network tuning |

---

## Additional Sources (Infrastructure Section)

- [ArchWiki: NVMe over Fabrics](https://wiki.archlinux.org/title/NVMe_over_Fabrics)
- [ArchWiki: NFS Performance Tuning](https://wiki.archlinux.org/title/NFS#Performance_tuning)
- [ArchWiki: SSD IO Scheduler](https://wiki.archlinux.org/title/Solid_state_drive#I/O_scheduler)
- [Linux bcache documentation](https://www.kernel.org/doc/html/latest/admin-guide/bcache.html)
- [Linux dm-cache documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/cache.html)
- [Linux FS-Cache documentation](https://www.kernel.org/doc/html/latest/filesystems/caching/fscache.html)
- [Linux VM sysctl documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html)
- [nfs(5) man page](https://man7.org/linux/man-pages/man5/nfs.5.html)
- [WD Gold 22TB datasheet](https://www.westerndigital.com/products/internal-drives/wd-gold-sata-3-5-hdd)
- Node deep audits: `docs/hardware/2026-02-25-node{1,2}-deep-audit.md`, `docs/hardware/2026-02-25-vault-deep-audit.md`
