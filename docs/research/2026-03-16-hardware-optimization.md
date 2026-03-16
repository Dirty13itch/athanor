# Athanor Hardware Optimization Research

*Deep research: how to use every CPU, GPU, NVMe, HDD, and RAM resource to make the Athanor AI system better.*

Last updated: 2026-03-16

---

## Current Resource Inventory & Utilization

| Node | CPU | RAM (Total/Free) | GPUs | VRAM Used/Total | NVMe | Status |
|------|-----|-------------------|------|-----------------|------|--------|
| FOUNDRY | EPYC 7663 56C/112T | 224GB / 152GB free | 4x5070Ti + 4090 | 85GB/88GB | 4TB Gen3 + 4TB Gen4 | Fully loaded |
| WORKSHOP | TR 7960X 24C/48T | 128GB / 105GB free | 5090 + 5060Ti | 32GB/48GB | 4TB Gen5 + 3x1TB Gen5 unmounted | **16GB GPU idle** |
| DEV | 9900X 12C/24T | 64GB / 44GB free | 5060Ti | 5GB/16GB | 1TB | Embedding only |
| VAULT | 9950X 16C/32T | 128GB / ~60GB free | A380 | — | 4x1TB Gen4 | 47 containers |

**Loose hardware:** i7-12700K, i5-12600K, i7-9700K, 2xRTX 3060 (12GB each), RX 5700XT (8GB), 192GB RAM, ~15TB NVMe, 3x10GbE NICs, 2x Hyper M.2 adapters, ASUS ROG 1200W PSU

---

## 1. GPU Optimization

### 1.1 Workshop 5060 Ti (IDLE — 16GB VRAM)

**Recommendation: Deploy Qwen3-VL-8B-Instruct (AWQ 4-bit) for vision capability**

This adds an entirely new modality (image/video understanding) that doesn't exist in the current system.

| Option | Model | VRAM | Capability Added | Verdict |
|--------|-------|------|-----------------|---------|
| **Vision (RECOMMENDED)** | Qwen3-VL-8B-Instruct AWQ 4-bit | ~5-6GB | Image understanding, OCR, chart analysis, video | **Best ROI — new capability** |
| Draft model | Qwen3-0.6B (already available) | ~1.5GB | Speculative decoding for Workshop 5090 | MTP built into Qwen3.5 already |
| TTS | Kokoro/Piper | <1GB | Already on FOUNDRY (Speaches :8200) | Redundant |
| Embedding redundancy | Qwen3-Embedding-0.6B | ~1.5GB | Backup embedding | Low value |
| GLM-4.1V-9B-Thinking | GLM-4.1V-9B-Thinking | ~6GB | Multimodal reasoning | Strong alternative to Qwen3-VL |

**Why Qwen3-VL-8B:** AWQ 4-bit fits comfortably in 16GB with room for 8-16K context KV cache. It adds vision to every agent — Research can analyze screenshots, Knowledge can read documents/charts, Creative can understand reference images, Home can process camera feeds. The model supports 256K context natively and understands video. Deploy via vLLM with `--max-model-len 8192 --gpu-memory-utilization 0.90`. Do NOT pass `--quantization awq` if using compressed-tensors format — let vLLM auto-detect.

**Alternative: GPT-OSS-20B (MXFP4)** — OpenAI's first open-weight model (Apache 2.0, released 2026). MoE with 20.9B total / 3.6B active params, ships in MXFP4 format for 16GB deployment (~13.7GB VRAM). Matches o3-mini on reasoning, strong function calling, 42 tok/s. vLLM v0.17.0 added MXFP4 kernel support for sm_120. This provides model diversity (not all Qwen) and a genuine "fast reasoning" tier. **However**, vision adds a new *capability* whereas GPT-OSS adds redundant *capacity* (text generation). Vision is higher ROI unless we need a non-Qwen fallback.

**LiteLLM route:** Add `vision` alias pointing to Workshop 5060Ti. Agents can then request vision capability through the existing routing infrastructure.

Sources:
- [Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL)
- [vLLM Qwen3-VL Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-VL.html)
- [Best Multimodal Models 2026](https://blog.roboflow.com/best-multimodal-models/)

### 1.2 MTP Speculative Decoding (Already Built In)

Qwen3.5 includes Multi-Token Prediction (MTP) heads. This is NOT traditional speculative decoding with a separate draft model — the MTP weights are part of the model itself.

**Configuration:**
```bash
vllm serve Qwen/Qwen3.5-27B-FP8 \
  --speculative-config '{"method": "mtp", "num_speculative_tokens": 1}' \
  ...existing flags...
```

**Trade-offs:**
- Reduces time-per-output-token (TPOT) at low concurrency — good for interactive chat
- Speculative tokens consume KV cache, reducing effective batch size under load
- Only `num_speculative_tokens: 1` works for Qwen3.5-27B (2+ crashes)
- Known bugs with tool calling in speculative mode (vllm#35800)

**CRITICAL caveat (from GPU research agent):** MTP-1 is **incompatible with prefix caching** and requires `max-num-seqs 1` for decent acceptance rates. For a 9-agent system, disabling prefix caching to gain ~16% ITL improvement is a net loss.

**Revised recommendation:** Enable MTP-1 only on the **Coder** model (FOUNDRY 4090, single-user, prefix caching less critical). Do NOT enable on Coordinator or Worker. Also consider n-gram speculation (zero cost, works everywhere) on all instances.

Sources:
- [vLLM Qwen3.5 Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [vLLM Forum: Qwen3.5-27B Speculative Decoding](https://discuss.vllm.ai/t/qwen3-5-27b-fp8-speculative-decoding/2447)
- [vLLM Speculative Decoding Docs](https://docs.vllm.ai/en/latest/features/speculative_decoding/)

### 1.3 GPU Undervolting (Free Performance)

Blackwell GPUs (5060 Ti, 5070 Ti, 5090) benefit significantly from undervolting for sustained AI workloads:

- **14% AI performance increase** observed on RTX 5070 after undervolting (sustained higher clocks without thermal throttling)
- **37% power reduction** with only ~5% peak performance loss
- Critical for 24/7 inference where sustained thermal load causes throttling
- RTX 5070 Ti: 95% performance at 85% power draw is typical

**Action:** Apply undervolt profiles via `nvidia-smi` persistence or MSI Afterburner on all Blackwell GPUs. For the 4x5070Ti on FOUNDRY, even a 10% power reduction saves ~120W continuously.

```bash
# Example: Set power limit to 85% on FOUNDRY 5070 Ti cards (300W -> 255W each)
nvidia-smi -i 0,1,3,4 -pl 255
# 4090 (450W -> 380W)
nvidia-smi -i 2 -pl 380
```

Sources:
- [Undervolting RTX 5070 AI Performance +14%](https://en.gamegpu.com/News/zhelezo/andervolting-uskoril-rtx-5070-v-zadachakh-ii-na-14)
- [MSI RTX 5070/5060Ti Undervolting Guide](https://www.msi.com/blog/rtx-5070-5060ti-overclocking-undervolting-guide-with-msi-afterburner-part-1)

### 1.4 Loose RTX 3060s (2x 12GB)

**Verdict: Build a 5th node (see Section 6) or use one in DEV**

12GB VRAM in 2026 can run:
- Qwen3.5-9B MoE variants (if they fit — the current 9B OOMs on 4090 24GB due to MoE expansion, so likely not)
- Qwen3-8B dense at Q4 quantization (~5GB)
- Qwen3-VL-4B at full precision (~8GB)
- Small specialized models: coding assistants, function callers
- 40-80 tok/s on 7B models per RTX 5060 Ti benchmarks (3060 will be slower, ~30-50 tok/s estimated)

Not worth deploying individually. Best value is in a dedicated 5th node with both cards.

### 1.5 vLLM v0.17.1 Upgrade

Current system runs nightly 0.16.1rc1. Stable v0.17.1 (March 11, 2026) adds:

- `--performance-mode throughput|interactivity` — automatic tuning presets
- SM120 FP8 GEMM optimization for Blackwell consumer GPUs
- NVFP4 MoE kernel fixes for RTX Blackwell
- Pipeline Parallel async send/recv (2.9% throughput gain)
- Detokenizer optimization

**Risk:** CRITICAL — do not upgrade until confirming RMSNormGated.activation regression is fixed (see MEMORY.md). Test on DEV first with a throwaway model.

Sources:
- [vLLM v0.17.0 Release](https://toolnavs.com/en/article/1164-vllm-released-v0170-the-high-performance-large-model-inference-framework-continu)
- [vLLM GitHub Releases](https://github.com/vllm-project/vllm/releases)

---

## 2. CPU Optimization

### 2.1 CPU Offloading (vLLM --cpu-offload-gb)

**Verdict: NOT recommended for current setup**

The traditional `--cpu-offload-gb` uses UVA (Unified Virtual Addressing) which transfers model weights CPU→GPU on every forward pass over PCIe. On PCIe 4.0/5.0 (not NVLink), this is very slow.

Expert warning: "Don't use CPU offloading unless you are 100% sure that your model won't fit on your GPU. Once activated, vLLM will be super slow even if you have enough GPU memory."

**Exception:** vLLM's newer weight offloading v2 (async prefetch) is better but still PCIe-bound. Only useful if you need to run a model that's 5-10% over GPU capacity.

**Also note:** `--cpu-offload-gb` is incompatible with `--enable-prefix-caching` (Python assertion error). Since prefix caching is more valuable than CPU offloading for our workloads, this is a non-starter.

Sources:
- [Benjamin Marie on CPU Offloading](https://substack.com/@bnjmnmarie/note/c-173125440)
- [vLLM KV Offloading Blog](https://vllm.ai/blog/kv-offloading-connector)
- [Red Hat vLLM Performance Tuning](https://developers.redhat.com/articles/2026/03/03/practical-strategies-vllm-performance-tuning)

### 2.2 KV Cache Offloading to CPU RAM

**Verdict: PROMISING — worth testing**

Unlike weight offloading, KV cache offloading stores computed attention states in CPU RAM and fetches them back on cache hits. This is read-on-hit, not read-every-forward-pass.

- TTFT reduction: **2x-22x** depending on prompt size when cache hits
- Throughput increase: **up to 9x** at high cache hit rates
- Uses async DMA transfers parallel to computation
- Minimal overhead on cache misses

**Configuration (vLLM v0.14+):**
```bash
--kv_offloading_backend native --kv_offloading_size 50
```

This would use 50GB of FOUNDRY's 152GB free RAM as a KV cache overflow tier. For repeated prompts (system prompts, common agent prefixes), cache hit rates should be very high.

**Action:** Test on FOUNDRY Coordinator with 50GB offload. Measure TTFT and throughput vs baseline.

Sources:
- [vLLM KV Offloading Connector Blog](https://vllm.ai/blog/kv-offloading-connector)

### 2.3 llama.cpp CPU-Only Inference

**Verdict: Viable for background/batch tasks on FOUNDRY**

Key insight: LLM inference on CPU is **memory-bandwidth bound**, not compute bound. Only ~5 threads saturate a memory channel.

EPYC 7663 specs:
- 8 memory channels (7 populated with DDR4-3200)
- Theoretical bandwidth: 7 × 25.6 GB/s = ~179 GB/s
- Practical: ~140 GB/s (accounting for overhead)

Estimated performance (Q4_K_M quantization):
| Model | Size (Q4) | Est. tok/s | Usable? |
|-------|-----------|-----------|---------|
| Qwen3-8B | ~5GB | ~25-30 | Yes — batch summarization, classification |
| Qwen3-14B | ~8GB | ~15-18 | Yes — slower, but adequate for async tasks |
| Qwen3.5-27B | ~16GB | ~8-10 | Marginal — too slow for interactive, OK for batch |

**Use cases:**
- Background document processing / summarization queue
- Bulk classification (RSS signals, email triage)
- Evaluation/grading (promptfoo evals without burning GPU)
- Synthetic data generation overnight

**Implementation:** Run llama.cpp server on FOUNDRY, bind to NUMA node 0, expose on a port, add as `cpu-batch` route in LiteLLM. Agent scheduler can route low-priority tasks there.

**Important:** Disable SMT for llama.cpp workloads (use physical cores only). Set `GOMP_CPU_AFFINITY` or use `numactl --cpunodebind=0 --membind=0`.

Sources:
- [llama.cpp CPU Performance Discussion](https://github.com/ggml-org/llama.cpp/discussions/3167)
- [Dual EPYC Performance Discussion](https://github.com/ggml-org/llama.cpp/discussions/11733)
- [OpenBenchmarking llama.cpp](https://openbenchmarking.org/test/pts/llama-cpp)

### 2.4 CPU-Based Embedding (Free Up DEV GPU)

**Verdict: Not worth it — GPU is 12-14x faster**

Recent benchmark (March 2026, Tunbury.org): ONNX Runtime on AMD EPYC 9965 (192 cores) vs NVIDIA L4 GPU — GPU was **12-14x faster** across all tests.

Int8 quantization on CPU gives ~3x speedup, but that still leaves CPU at ~4-5x slower than GPU. For Qwen3-Embedding-0.6B (tiny model), the DEV 5060Ti uses only ~1.5GB VRAM and runs at effectively zero latency.

**Better approach:** Keep embedding on DEV GPU. If you need the DEV GPU for something else, move embedding to Workshop 5060Ti alongside the vision model (both are small enough to share 16GB).

Sources:
- [GPU vs CPU ONNX Inference Benchmark](https://www.tunbury.org/2026/03/11/gpu-vs-cpu/)
- [ONNX Embedding Quantization](https://medium.com/nixiesearch/how-to-compute-llm-embeddings-3x-faster-with-model-quantization-25523d9b4ce5)

### 2.5 NUMA Topology Optimization (FOUNDRY)

EPYC 7663 has 8 NUMA nodes (1 per CCD). With 7 DIMMs across 7 channels, memory access is non-uniform.

**Actions:**
1. Pin vLLM coordinator process to NUMA nodes closest to the PCIe slots holding the GPUs
2. Use `numactl --cpunodebind=0-3 --membind=0-3` for vLLM (adjust based on actual GPU NUMA affinity)
3. Check GPU NUMA affinity: `nvidia-smi topo -m`
4. Pin Qdrant to a different NUMA node from vLLM to avoid contention
5. If running llama.cpp, pin to the remaining NUMA nodes

**Expected impact:** 5-15% improvement in memory-bound operations (KV cache management, model loading).

---

## 3. Storage Optimization

### 3.1 Workshop T700 Drives (3x 1TB Gen5 NVMe — UNMOUNTED)

**Recommendation: Individual mounts (not RAID0)**

Storage research agent analysis: each T700 delivers ~11.7 GB/s sequential, which already exceeds any single workload's need. RAID0 adds complexity without real benefit. Individual mounts allow flexible allocation.

**Configuration:**
```bash
# Clear stale ZFS labels
wipefs -a /dev/nvme1n1 /dev/nvme2n1 /dev/nvme3n1
# Format individually
mkfs.ext4 /dev/nvme1n1 && mount /dev/nvme1n1 /data/models
mkfs.ext4 /dev/nvme2n1 && mount /dev/nvme2n1 /data/scratch
mkfs.ext4 /dev/nvme3n1 && mount /dev/nvme3n1 /data/docker
```

**Uses:**
- `/data/models`: Local model cache (rsync from VAULT NFS). Cold start: seconds instead of minutes.
- `/data/scratch`: ComfyUI scratch space (Flux/Wan2.x intermediate files)
- `/data/docker`: Docker data directory (images, volumes) — faster container builds

**Note:** T700 throttles at 181F — monitor thermals, especially under sustained write.

### 3.2 Model Loading Optimization

Current flow: VAULT HDD array → NFS over 10GbE → compute node → GPU

**Bottlenecks:**
- VAULT HDD array: ~200 MB/s sequential read (limited by Unraid parity)
- 10GbE: ~1.1 GB/s theoretical
- A 27GB FP8 model takes ~25 seconds over 10GbE, ~135 seconds from cold HDD

**Fix:** Local NVMe model caches on compute nodes.

FOUNDRY already has Samsung 990 PRO 4TB at `/mnt/local-fast` — models should be cached there. Workshop needs the T700 RAID0 (above) to do the same.

**Implementation:**
1. Mount T700 RAID0 on Workshop as `/mnt/local-fast`
2. Create Ansible role `model-cache` that rsyncs models from VAULT NFS to local NVMe
3. Point vLLM `--model` at local path instead of NFS
4. Schedule nightly rsync to keep caches fresh

### 3.3 VAULT NFS Tuning

Current NFS is default settings. Improvements:

```bash
# Client-side mount options (compute nodes)
192.168.1.203:/mnt/user/models /mnt/vault/models nfs rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,nconnect=4 0 0
```

Key changes:
- `rsize/wsize=1048576` — 1MB read/write blocks (default is often 32K)
- `nconnect=4` — multiple TCP connections, utilizes more of 10GbE bandwidth
- Already using `hard` mount (good for reliability)

**Expected improvement:** 2-3x NFS throughput for large sequential reads (model loading).

### 3.4 NVMe over Fabrics (NVMe-oF/TCP)

**Verdict: Overkill for current needs, but interesting for future**

NVMe-oF/TCP achieves 20-30 microsecond latency vs NFS's millisecond latency. No special hardware needed (works over standard TCP/IP). Linux kernel has native nvme-tcp client and nvmet-tcp target.

**When it makes sense:** If model loading from VAULT becomes a bottleneck even with local caches, or if we implement distributed KV cache that needs fast remote storage access.

**Not needed now** because local NVMe caches solve the model loading problem, and KV cache stays in GPU/CPU RAM.

Sources:
- [NVMe-oF TCP vs RDMA](https://intelligentvisibility.com/nvme-over-fabrics-ethernet-comparison)
- [Western Digital NVMe-oF Brief](https://documents.westerndigital.com/content/dam/doc-library/en_us/assets/public/western-digital/collateral/tech-brief/tech-brief-nvme-of-accelerating-data-center-innovation-in-ai-era.pdf)

### 3.5 Qdrant on Fast NVMe

Qdrant on FOUNDRY (34K+ points, 9 collections) — check if it's using mmap or in-memory mode.

**Action:**
- If collection size < available RAM, use `on_disk: false` (fully in-memory) — FOUNDRY has 152GB free
- If using mmap, ensure data directory is on the Samsung 990 PRO, not the Gen3 OS drive
- For 34K points with typical 768-1536 dim vectors, total size is ~200MB-400MB — easily fits in RAM

### 3.6 Loose NVMe Utilization

~15TB of loose NVMe drives. Best uses:

| Drive | Capacity | Best Use |
|-------|----------|----------|
| Crucial P3 Plus Gen4 | 4TB | 5th node OS + model cache |
| Crucial P310 Gen4 | 2TB | 5th node secondary storage |
| 4x Crucial P310 Gen4 | 4x1TB | VAULT Hyper M.2 adapter (NVMe cache pool upgrade) |
| Crucial T700 Gen5 | 1TB | DEV fast scratch or spare |
| Samsung 970 EVO+ Gen3 | 1TB | Spare / test node |
| WD Black SN750 Gen3 | 1TB | Spare |

**Highest impact:** Put the 4x P310 1TB into the VAULT Hyper M.2 adapter (currently confirmed empty) as additional NVMe cache for the Unraid array. This would dramatically speed up NFS reads for frequently-accessed models.

---

## 4. Network Optimization

### 4.1 FOUNDRY NIC Bonding

FOUNDRY's ROMED8-2T has 2x Intel X550 10GbE onboard. Currently only one is used.

**Action:** Bond both NICs for redundancy and aggregate bandwidth.

```bash
# /etc/netplan/01-bond.yaml
network:
  bonds:
    bond0:
      interfaces: [enp65s0f0, enp65s0f1]
      parameters:
        mode: 802.3ad  # LACP
        lacp-rate: fast
        transmit-hash-policy: layer3+4
      addresses: [192.168.1.244/24]
```

**Requires:** LACP support on the UniFi USW Pro XG 10 PoE switch (supported).

**Important caveat (from network research agent):** LACP hashes by flow — a single NFS mount = a single TCP flow = a single link. LACP will NOT give 20Gbps for a single NFS stream. Use NFS `nconnect=2` mount option to distribute across both links. Main value is redundancy (immediate failover if one NIC fails).

### 4.2 Disaggregated Prefill/Decode

**Verdict: Not recommended for current setup**

vLLM supports disaggregated prefill/decode where one instance handles prompt processing and another handles token generation, connected via KV cache transfer.

**Why not now:**
- Requires fast KV transfer between nodes (RDMA ideal, TCP adds latency)
- 10GbE is marginal — KV cache for 131K context is multiple GB
- Doesn't improve throughput, only tail latency separation
- Current single-node serving is simpler and adequate
- Bug surface area is large (bidirectional KV transfer just proposed Jan 2026)

**When it makes sense:** If we scale to multiple model replicas and need to separate latency-sensitive interactive requests from throughput-oriented batch processing.

Sources:
- [vLLM Disaggregated Prefill Docs](https://docs.vllm.ai/en/latest/features/disagg_prefill/)
- [PyTorch + vLLM Disaggregated Inference](https://pytorch.org/blog/disaggregated-inference-at-scale-with-pytorch-vllm/)

### 4.3 DEV Network Upgrade

DEV has 5GbE Realtek — slowest in the cluster. With 3 loose dual-port 10GbE NICs available:

**Action:** Install one Intel X540-T2 in DEV for 10GbE.

**Benefit:** Faster rsync deployments, better access to NFS models, consistent cluster networking.

**Note:** Z690 AORUS ULTRA has PCIe 3.0 x16 and 4.0 x16 slots available. X540-T2 is PCIe 2.1 x8 — fits any slot.

### 4.4 25GbE/100GbE Upgrade Path

For future reference, used Mellanox ConnectX-4 25GbE cards are ~$30-50 on eBay in 2026. ConnectX-5 100GbE are ~$80-120. Would need a compatible switch (used Mellanox SN2100 32-port 100GbE ~$200-400).

**Not urgent** — 10GbE with bonding (20Gbps on FOUNDRY) is sufficient for current workloads. Worth revisiting if distributed inference or training becomes a priority.

---

## 5. Orchestration & Operations

### 5.1 Container Orchestration

**Verdict: Stay with Docker Compose + Ansible**

| Option | Complexity | Benefit | Verdict |
|--------|-----------|---------|---------|
| Docker Compose (current) | Low | Works, Shaun understands it | **Keep** |
| Docker Swarm | Medium | Multi-node scheduling | Stagnant since 2019 |
| Nomad | Medium | Single binary, mixed workloads | Interesting but adds complexity |
| Kubernetes | High | Enterprise features | Way overkill for homelab |

The current setup (Docker Compose per node + Ansible for deployment) is the right level of complexity for a one-person system. Adding Nomad/Swarm would help with automatic failover but adds operational overhead Shaun would need to understand and debug.

**If anything:** Portainer (already Docker-native) could provide a UI for cross-node container management without changing the underlying orchestration.

### 5.2 Power Management

Current idle power draw (estimated):
- FOUNDRY: ~400W (EPYC 240W TDP + 5 GPUs)
- WORKSHOP: ~350W (TR 350W TDP + 2 GPUs)
- VAULT: ~150W (9950X + 10 HDDs spinning)
- DEV: ~100W

**Quick wins:**
1. GPU power limiting (Section 1.3) — saves ~120W on FOUNDRY
2. EPYC power profile: `cpupower frequency-set -g powersave` when idle, `performance` on demand
3. HDD spindown on VAULT for rarely-accessed drives (Unraid supports per-disk spindown)
4. GPU persistence mode with lower power states when idle: `nvidia-smi -pm 1`

### 5.3 Monitoring Enhancements

Already have Prometheus + Grafana + Loki. Add inference-specific dashboards:

**vLLM metrics to track** (exposed at `:8000/metrics`):
- `vllm:num_requests_running` — current batch size
- `vllm:num_requests_waiting` — queue depth
- `vllm:gpu_cache_usage_perc` — KV cache utilization
- `vllm:avg_generation_throughput_toks_per_s` — throughput
- `vllm:e2e_request_latency_seconds` — end-to-end latency histogram
- `vllm:time_to_first_token_seconds` — TTFT histogram

**Alerts to add:**
- KV cache > 90% sustained → model is memory-bound, reduce max_num_seqs
- Queue depth > 10 sustained → add capacity or route to another node
- TTFT p99 > 5s → investigate prefill bottleneck

---

## 6. Building a 5th Node

### Parts Available

| Component | Part | Notes |
|-----------|------|-------|
| CPU | Intel i7-12700K | 12C/20T, LGA 1700 |
| Motherboard | Gigabyte Z690 AORUS ELITE AX DDR4 | DDR4, 3 PCIe slots, 4 M.2 slots |
| RAM | 2x32GB Crucial Ballistix DDR4-3200 CL16 | 64GB total |
| GPU 1 | RTX 3060 12GB | From loose inventory |
| GPU 2 | RTX 3060 12GB | From loose inventory (currently in DEV) |
| NVMe | 4TB Crucial P3 Plus Gen4 | OS + storage |
| NVMe 2 | 2TB Crucial P310 Gen4 | Model cache |
| PSU | ASUS ROG 1200W 80+ Platinum | Overkill but available |
| NIC | Intel X540-T2 10GbE | From loose inventory |
| Case | — | Need to source or use open frame |

**Total cost: $0** (all parts on hand) + time to assemble

### Potential Roles

**Option A: Dedicated Vision/Multimodal Node**
- 2x RTX 3060 (24GB aggregate, not TP — different model per GPU)
- GPU 0: Qwen3-VL-8B AWQ (~5GB)
- GPU 1: Small utility model or second vision model
- Frees Workshop 5060Ti for other use
- 64GB RAM for llama.cpp batch processing

**Option B: Batch Processing / Eval Node**
- 2x RTX 3060 running small models for bulk tasks
- llama.cpp on CPU (i7-12700K, 8 P-cores, DDR4-3200 dual channel ~51 GB/s)
- Dedicated to promptfoo evals, synthetic data generation, document processing
- Keeps GPU-heavy nodes free for interactive serving

**Option C: VAULT Offload Node**
- Move non-GPU services off VAULT (Neo4j, Qdrant-secondary, n8n)
- VAULT's 47 containers are a lot for one machine
- Reduces VAULT load, improves HDD throughput for media workloads

**Agent disagreement on this decision:**
- CPU/RAM agent says **don't build** — 24GB slow VRAM (360 GB/s vs 896-1008 GB/s on existing GPUs), no AVX-512, management overhead exceeds value. Keep parts as hot spares.
- Network agent says **build** — 24GB additional VRAM for batch/eval, CI pipeline runner, model testing sandbox.
- GPU agent says **sell the 3060s** — vLLM V1 engine has known OOM crashes on 12GB consumer cards. Two 3060s ($500-600 resale) would fund a new RTX 5060 Ti 16GB ($450).

**My assessment:** The sell-and-upgrade path is most compelling. Two aging 12GB Ampere cards with OOM issues vs one 16GB Blackwell card with modern tensor cores is a clear win. But building costs $0 and selling requires effort, so this is a priority call for Shaun.

### Build Decision Matrix

| Factor | Build ($0) | Sell 3060s + Buy 5060Ti (~+$0 net) | Keep as Spares |
|--------|------------|-------------------------------------|----------------|
| VRAM gained | +24GB (slow) | +16GB (fast, Blackwell) | 0 |
| Effort | 4hrs build | Selling/shipping time | None |
| Power | +200W idle | +180W idle | None |
| Compatibility | Needs separate vLLM image (sm_86) | Same image as cluster | N/A |
| Risk | OOM issues on 12GB | Proven hardware | Parts depreciate |

---

## 7. Priority Action Plan

### Tier 1 — Quick Wins (< 1 hour each, high impact)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | Deploy Qwen3-VL-8B on Workshop 5060Ti | New vision capability | 30 min |
| 2 | Undervolt all Blackwell GPUs | -120W, better sustained perf | 15 min |
| 3 | Mount Workshop T700 drives individually | 3TB fast local storage | 30 min |
| 4 | Tune NFS mount options (rsize/wsize/nconnect) | 2-3x NFS throughput | 15 min |
| 5 | Install 10GbE NIC in DEV | Consistent cluster networking | 20 min (physical) |

### Tier 2 — Medium Effort (hours, significant impact)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 6 | Test KV cache offloading on Coordinator | Better cache hit rates, lower TTFT | 2 hrs |
| 7 | Test MTP-1 speculative decoding on Coder only | Lower TPOT for coding (NOT Coordinator — breaks prefix cache) | 2 hrs |
| 8 | Bond FOUNDRY NICs (LACP) | Redundancy + nconnect=2 for NFS | 1 hr |
| 9 | Deploy llama.cpp on FOUNDRY for batch route | Free CPU inference for low-priority | 2 hrs |
| 10 | Add vLLM Prometheus dashboards to Grafana | Inference observability | 1 hr |

### Tier 3 — Projects (days, strategic impact)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 11 | Decide: build 5th node, sell 3060s for 5060Ti, or keep as spares | GPU capacity decision (Shaun call) | — |
| 12 | Install 4x P310 in VAULT Hyper M.2 | Faster NFS cache pool | 1 hr (physical) |
| 13 | Test vLLM v0.17.1 upgrade on DEV | Performance mode, SM120 optimizations | 4 hrs |
| 14 | NUMA pinning optimization on FOUNDRY | 5-15% memory perf improvement | 2 hrs |
| 15 | Evaluate Portainer for cluster UI | Operational visibility | 2 hrs |

---

## Appendix: Sub-Agent Research Reports

Four research agents produced detailed reports on specific domains. These are available in worktree branches:

1. **GPU Optimization** — GPT-OSS-20B recommendation, RTX 3060 sell analysis, MTP-1/prefix-cache incompatibility
2. **CPU/RAM Optimization** — KV cache offloading config, llama.cpp benchmarks, TEI CPU embedding, NUMA pinning
3. **Storage Optimization** — Individual T700 mounts, FOUNDRY model path verification, VAULT NFS `nconnect=8`
4. **Network/Infrastructure** — LACP flow-hashing caveat, Komodo container management, power management, 25GbE upgrade pricing

---

## Sources

- [vLLM Qwen3.5 Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [vLLM Speculative Decoding Docs](https://docs.vllm.ai/en/latest/features/speculative_decoding/)
- [vLLM Disaggregated Prefill](https://docs.vllm.ai/en/latest/features/disagg_prefill/)
- [vLLM KV Offloading Blog](https://vllm.ai/blog/kv-offloading-connector)
- [vLLM Forum: Qwen3.5-27B Spec Decoding](https://discuss.vllm.ai/t/qwen3-5-27b-fp8-speculative-decoding/2447)
- [vLLM v0.17.0 Release](https://github.com/vllm-project/vllm/releases)
- [Red Hat vLLM Performance Tuning](https://developers.redhat.com/articles/2026/03/03/practical-strategies-vllm-performance-tuning)
- [Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL)
- [Best Multimodal Models 2026](https://blog.roboflow.com/best-multimodal-models/)
- [Best LLMs for 16GB VRAM](https://localllm.in/blog/best-local-llms-16gb-vram)
- [Best Local Coding Models 2026](https://insiderllm.com/guides/best-local-coding-models-2026/)
- [GPU vs CPU ONNX Inference](https://www.tunbury.org/2026/03/11/gpu-vs-cpu/)
- [llama.cpp CPU Performance](https://github.com/ggml-org/llama.cpp/discussions/3167)
- [Dual EPYC llama.cpp Performance](https://github.com/ggml-org/llama.cpp/discussions/11733)
- [RTX 5070 Undervolting +14% AI](https://en.gamegpu.com/News/zhelezo/andervolting-uskoril-rtx-5070-v-zadachakh-ii-na-14)
- [MSI Undervolting Guide](https://www.msi.com/blog/rtx-5070-5060ti-overclocking-undervolting-guide-with-msi-afterburner-part-1)
- [NVMe-oF TCP vs RDMA](https://intelligentvisibility.com/nvme-over-fabrics-ethernet-comparison)
- [PyTorch Disaggregated Inference](https://pytorch.org/blog/disaggregated-inference-at-scale-with-pytorch-vllm/)
- [PrefillShare Paper](https://arxiv.org/html/2602.12029)
- [Container Orchestration Comparison](https://www.index.dev/skill-vs-skill/devops-kubernetes-vs-docker-swarm-vs-nomad)
- [Benjamin Marie on CPU Offloading](https://substack.com/@bnjmnmarie/note/c-173125440)
