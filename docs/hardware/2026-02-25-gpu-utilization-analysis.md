# GPU Utilization Analysis -- 2026-02-25

Audited: February 25, 2026, 13:38-13:40 UTC (snapshot + 60s monitoring + 24h Prometheus history)

## Executive Summary

The Athanor cluster has 7 NVIDIA GPUs totaling 138.7 GB VRAM. At time of audit, **average compute utilization across all GPUs is under 2%**. The most expensive GPU (RTX 5090, $2000, 32 GB) has served **zero requests** since its last restart. The cluster burns $113/year in idle GPU power alone. The waste is not a hardware problem -- it is a demand problem. The GPUs are waiting for work that does not exist yet.

---

## Hardware Verified (nvidia-smi + Prometheus DCGM)

| Node | GPU Index | Card | PCI Bus | VRAM Total | VRAM Used | Util % | Power (now) | Workload |
|------|-----------|------|---------|-----------|-----------|--------|-------------|----------|
| Node 1 | 0 | RTX 5070 Ti | 01:00.0 | 16,303 MiB | 15,634 MiB | 0% | 16.95W | vLLM TP0 (Qwen3-32B-AWQ) |
| Node 1 | 1 | RTX 5070 Ti | 02:00.0 | 16,303 MiB | 15,636 MiB | 0% | 10.40W | vLLM TP1 (Qwen3-32B-AWQ) |
| Node 1 | 2 | **RTX 4090** | 81:00.0 | 24,564 MiB | 15,796 MiB | 0% | 14.83W | vLLM TP2 (Qwen3-32B-AWQ) |
| Node 1 | 3 | RTX 5070 Ti | 82:00.0 | 16,303 MiB | 15,642 MiB | 0% | 11.17W | vLLM TP3 (Qwen3-32B-AWQ) |
| Node 1 | 4 | RTX 5070 Ti | C1:00.0 | 16,303 MiB | 8,899 MiB | 0% | 12.40W | vLLM-embedding (6,742 MiB) + whisper (2,142 MiB) |
| Node 2 | 0 | **RTX 5090** | 41:00.0 | 32,607 MiB | 31,132 MiB | 0% | 23.66W | vLLM (Qwen3-14B FP16) |
| Node 2 | 1 | RTX 5060 Ti | 81:00.0 | 16,311 MiB | 146 MiB | 0% | 3.77W | ComfyUI (lazy-load, idle) |
| VAULT | -- | Arc A380 | 03:00.0 | ~6,144 MiB | N/A | N/A | N/A | Plex HW transcode (/dev/dri) |

**Totals (NVIDIA only):** 138,694 MiB (135.4 GB) VRAM, 102,885 MiB (100.5 GB) allocated, 35,809 MiB (35.0 GB) free.

---

## 60-Second Real-Time Monitoring (nvidia-smi dmon)

### Node 1 (12 samples, 5s intervals)

The monitoring captured an actual inference burst midway through the sample window:

| Sample | GPU 0 (sm%) | GPU 1 (sm%) | GPU 2 (sm%) | GPU 3 (sm%) | GPU 4 (sm%) | Notes |
|--------|-------------|-------------|-------------|-------------|-------------|-------|
| 1-7 | 0 | 0 | 0 | 0 | 0 | Completely idle |
| 8 | 0 | 99 | 0 | 0 | 0 | Request arriving, TP1 starts first |
| 9-12 | 99 | 99 | 99 | 99 | 0 | Full TP=4 burst, all 4 GPUs at 99% |

Key observations:
- **Bursty pattern**: 7 idle samples, then a request hits and all 4 GPUs spike to 99% simultaneously
- **GPU 4 never activates**: Embedding + whisper workloads register 0% compute utilization (embedding is trivial matrix math, whisper only runs during voice input)
- **Memory bandwidth during burst**: GPU 0: 31%, GPU 1: 48%, GPU 2: 31%, GPU 3: 46% -- memory-bound, not compute-bound
- **PCIe traffic during burst**: GPU 2 (4090) shows 2.5 GB/s RX -- highest because it bridges the two PCIe domains

### Node 2 (12 samples, 5s intervals)

| Sample | GPU 0 (sm%) | GPU 1 (sm%) |
|--------|-------------|-------------|
| 1-12 | 0 | 0 |

**Twelve consecutive zero-utilization samples.** The 5090 did nothing for the entire monitoring window. The 5060 Ti (ComfyUI) also idle -- models not even loaded.

---

## 24-Hour Historical Utilization (Prometheus DCGM, hourly averages)

| GPU | 24h Avg Util | Peak Hour | Active Hours | Avg Power |
|-----|-------------|-----------|-------------|-----------|
| N1 GPU0 (5070 Ti, TP0) | 1.9% | 13.2% | 7/21 | 19.1W |
| N1 GPU1 (5070 Ti, TP1) | 1.9% | 13.2% | 7/21 | 13.9W |
| N1 GPU2 (4090, TP2) | 1.9% | 13.2% | 7/21 | 19.9W |
| N1 GPU3 (5070 Ti, TP3) | 1.9% | 13.2% | 7/21 | 14.2W |
| N1 GPU4 (5070 Ti, shared) | 0.0% | 0.0% | 0/21 | 12.0W |
| N2 GPU0 (5090, vLLM) | 0.2% | 1.6% | 4/21 | 24.5W |
| N2 GPU1 (5060 Ti, ComfyUI) | 0.2% | 2.4% | 2/21 | 4.0W |

**Cluster-wide 24h average compute utilization: 0.87%**

The TP=4 group (GPUs 0-3) averaged 1.9% because Shaun was actively building/testing during the session. Outside active sessions, utilization drops to near 0%.

---

## vLLM Request Analysis

### Node 1: Qwen3-32B-AWQ (TP=4, GPUs 0-3)

| Metric | Value |
|--------|-------|
| Uptime | 13.6 hours |
| Total requests (successful) | 98 |
| Request rate | 7.21 req/hour |
| Prompt tokens processed | 255,636 |
| Generation tokens produced | 43,040 |
| Token throughput | ~21,982 tokens/hour |
| KV cache usage | 3.1% (nearly empty) |
| Prefix cache hit rate | 226,720 / 255,636 = 88.7% |
| Requests > 60s latency | 22/98 (22.4%) |
| Preemptions | 0 |
| Sleep state | Awake (sleep mode blocked) |

At 7.21 req/h, the TP=4 group processes one request every 8.3 minutes on average. During bursts, it saturates at 99% for 10-60 seconds. The remaining time is pure idle.

### Node 1: Qwen3-Embedding-0.6B (GPU 4, shared)

| Metric | Value |
|--------|-------|
| Uptime | 12.4 hours |
| Total requests | 1,251 |
| Request rate | 101.01 req/hour |
| Prompt tokens | 457,492 |
| VRAM used | 6,742 MiB |

Higher request volume than the main model (context injection queries every chat turn), but each request is trivial compute -- a forward pass through a 0.6B model. Zero compute utilization registered by nvidia-smi because each request completes in milliseconds.

### Node 2: Qwen3-14B FP16 (GPU 0, 5090)

| Metric | Value |
|--------|-------|
| Uptime | 4.1 hours |
| Total requests | **0** |
| Prompt tokens | **0** |
| Generation tokens | **0** |
| VRAM used | 31,132 MiB (95.5%) |

**Zero requests. Zero tokens. Complete waste.** This is a $2,000 GPU holding a 14B model in memory that nobody is talking to. The "fast" chat model exists as a LiteLLM alias but nothing routes to it.

### Node 2: ComfyUI (GPU 1, 5060 Ti)

| Metric | Value |
|--------|-------|
| Queue running | 0 |
| Queue pending | 0 |
| VRAM used | 146 MiB (lazy-loaded, efficient) |

ComfyUI properly lazy-loads models on demand. Only 146 MiB committed when idle. This is the correct pattern -- the 5060 Ti is available when needed for Flux/Wan2.x generation without wasting resources when idle.

---

## Waste Quantification

### 1. VRAM Waste

| GPU | Allocated | Actually Needed | Wasted VRAM | Notes |
|-----|-----------|----------------|-------------|-------|
| N1 GPU2 (4090) | 15,796 MiB | 15,796 MiB | 8,768 MiB unused capacity | 4090 has 24 GB but TP shard only needs 15.8 GB |
| N1 GPU4 | 8,899 MiB | 8,899 MiB | 7,404 MiB free | Room for another small model |
| N2 GPU0 (5090) | 31,132 MiB | **0 MiB** | **31,132 MiB** | Zero requests = 100% waste |
| N2 GPU1 | 146 MiB | 146 MiB | 0 MiB | Lazy-loaded, efficient |

**Total wasted VRAM: 47,304 MiB (46.2 GB)**, of which 31.1 GB is the 5090 holding a model nobody uses, 8.8 GB is the 4090's excess capacity in the TP group, and 7.4 GB is free headroom on GPU 4.

### 2. Compute Waste

| GPU Group | 24h Avg Util | Theoretical Capacity | Effective Use |
|-----------|-------------|---------------------|---------------|
| N1 GPUs 0-3 (TP=4) | 1.9% | 100% | 1.9% |
| N1 GPU 4 | 0.0% | 100% | 0.0% |
| N2 GPU 0 (5090) | 0.2% | 100% | 0.2% |
| N2 GPU 1 (5060 Ti) | 0.2% | 100% | 0.2% |
| **Cluster** | **0.87%** | **100%** | **0.87%** |

**99.13% of all GPU compute cycles go unused.**

### 3. Power Waste

| Item | Watts | Annual kWh | Annual Cost ($0.12/kWh) |
|------|-------|-----------|------------------------|
| N1 GPUs 0-3 idle baseline | 53.4W | 467.8 | $56.13 |
| N1 GPU 4 idle | 12.0W | 105.1 | $12.61 |
| N2 GPU 0 (5090) idle | 24.5W | 214.6 | $25.75 |
| N2 GPU 1 (5060 Ti) idle | 4.0W | 35.0 | $4.20 |
| **Total GPU idle power** | **93.9W** | **822.6** | **$98.71** |
| Burst overhead (estimated 2% duty cycle) | +12W avg | +105.1 | +$12.61 |
| **Total GPU power** | **~106W** | **~928** | **~$111** |

The 5090 alone accounts for $25.75/year in idle power with zero productive output.

### 4. Opportunity Cost

At conservative cloud GPU rates ($0.50/hr for a 16 GB GPU):
- 7 GPUs x 24h x 365d x $0.50 = **$30,660/year** in equivalent cloud compute
- At 0.87% utilization, effective value extracted: **$267/year**
- Idle waste in cloud-equivalent terms: **$30,393/year**

This is a homelab, not a business -- the cloud comparison is illustrative, not prescriptive. But it underscores that **the hardware exists to do 100x more work than it currently does**.

### 5. GPU 4 Sharing Efficiency

GPU 4 runs three services:

| Service | VRAM | Compute Impact |
|---------|------|---------------|
| vLLM-embedding (Qwen3-Embedding-0.6B) | 6,742 MiB | Near-zero (ms-level forward passes) |
| wyoming-whisper (faster-distil-whisper-large-v3) | 2,142 MiB | Near-zero (only during voice input) |
| Speaches (lazy GPU) | 0 MiB (lazy) | Zero until invoked |
| **Total** | **8,884 MiB / 16,303 MiB** | **< 1%** |

These services are not fighting -- they peacefully coexist because none of them do sustained compute. The 0.6B embedding model is embarrassingly cheap. Whisper only activates for brief STT bursts. Speaches is truly lazy. **7,404 MiB (45.4%) of GPU 4 is free and available.**

### 6. The 5090 Problem

The RTX 5090 represents the most acute waste:

| Metric | Value |
|--------|-------|
| Purchase price | ~$2,000 |
| VRAM | 32 GB GDDR7 |
| Memory bandwidth | 1,792 GB/s |
| Current workload | Qwen3-14B FP16 (zero requests) |
| VRAM utilization | 95.5% (31.1 GB locked) |
| Compute utilization | 0.2% |
| Idle power cost | $25.75/year |
| Requests served since last restart | 0 |

This GPU could run a 70B AWQ model, serve as a single-GPU Qwen3-32B endpoint, process batch workloads, or host a vision-language model. Instead it holds a 14B model that nothing routes to.

### 7. What Changes With Autonomous Agents (24/7 Task Execution)

Projected utilization with GWT Phase 3 + scheduled tasks:

| Workload | GPU Target | Est. Duty Cycle | Est. Utilization Lift |
|----------|-----------|----------------|---------------------|
| Scheduled research synthesis (Research Agent) | N1 GPUs 0-3 | 6-8 tasks/day, 5-15 min each | +5-15% |
| Proactive knowledge re-indexing | N1 GPU 4 | Continuous background | +2-5% |
| Scheduled creative generation (images/video) | N2 GPU 1 | 4-10 jobs/day | +5-10% |
| Home monitoring analysis | N1 GPUs 0-3 | Periodic checks | +1-2% |
| Stash content analysis (when library populated) | N1 GPUs 0-3 | Batch processing | +5-10% |
| **Total projected lift** | | | **+18-42%** |

Autonomous agents could push cluster utilization from under 1% to 20-40% -- a **20-40x improvement** without any hardware changes. This is the highest-ROI optimization available.

---

## Optimization Recommendations

### Priority 1: Reclaim the RTX 5090 (immediate, high impact)

**Problem:** 32 GB GPU running a model with zero demand.

**Action:** Stop the Qwen3-14B FP16 vLLM instance on Node 2. Replace with one of:

a. **Qwen3-32B-AWQ on 5090** (~18 GB, single GPU) -- Gives a second "reasoning" endpoint with lower latency than TP=4. Could serve as the "fast" model with better quality than 14B. Frees 14 GB for a secondary model.

b. **Qwen3-14B-AWQ** (~7 GB) instead of FP16 -- If the "fast" model is still wanted, AWQ cuts VRAM from 31 GB to 7 GB, freeing 25 GB for other models on the same GPU.

c. **Nothing** -- If nobody needs "fast" chat, shut it down. The 5090 becomes available for batch processing, creative AI, or a dedicated vision-language model.

**Savings:** If shut down, saves ~24.5W idle power ($25.75/year) and frees 32 GB VRAM.

### Priority 2: Deploy Autonomous Agent Tasks (near-term, highest ROI)

**Problem:** GPUs are idle because there is no automated demand.

**Action:** Complete GWT Phase 3 (agent subscription + reactive behavior) and deploy scheduled tasks:
- Research Agent: daily research synthesis on tracked topics
- Knowledge Agent: continuous re-indexing as new docs appear
- Creative Agent: scheduled image/video generation queue
- Home Agent: periodic HA state analysis and anomaly detection

**Impact:** 20-40x utilization improvement, no hardware changes needed.

### Priority 3: Unblock vLLM Sleep Mode (medium-term)

**Problem:** GPUs 0-3 hold 62 GB VRAM even when idle. Sleep mode would offload weights to CPU RAM, freeing VRAM and reducing power.

**Action:** Upgrade NGC vLLM image when a version with working `/sleep` and `/wake` REST endpoints ships. The GPU orchestrator already has sleep/wake logic ready.

**Impact:** Could reduce idle power from 53W to ~25W for the TP group (~$15/year savings) and temporarily free 62 GB VRAM during idle periods.

### Priority 4: Fill GPU 4 Headroom (low priority)

**Problem:** 7.4 GB free on GPU 4 doing nothing.

**Action:** Deploy a small reranker model (e.g., bge-reranker-v2-m3, ~1.5 GB) or a classifier for agent routing. This improves RAG quality without affecting existing services.

**Impact:** Better retrieval quality, negligible additional power.

### Priority 5: Use VAULT Arc A380 for More Than Transcoding (low priority)

**Problem:** Arc A380 only serves Plex HW transcoding, which happens infrequently.

**Action:** Intel GPUs support OpenVINO inference. Could run a small model for VAULT-local tasks (e.g., metadata extraction, image classification for Stash). However, the 6 GB VRAM and limited compute make this low-value.

**Impact:** Marginal. Only pursue if a specific VAULT-local workload emerges.

### Priority 6: Evaluate TP=4 vs. TP=2 + Independent GPUs (research needed)

**Problem:** The 4090 contributes 24 GB but only uses 15.8 GB in the TP group. Mixed architectures (sm_89 + sm_120) add complexity.

**Action:** Research whether Qwen3-32B-AWQ can run on TP=2 (two 5070 Ti cards, 32 GB combined) or even a single 5090 (32 GB). If so, the 4090 + two 5070 Ti cards become available for independent workloads.

**Risk:** TP=2 may reduce throughput. Mixed-arch TP is fragile. Requires careful benchmarking before changing production.

---

## Appendix: Raw Data Sources

- `nvidia-smi` snapshots: Node 1 and Node 2 at 13:38 UTC
- `nvidia-smi dmon -s uct -d 5 -c 12`: 60-second monitoring on both nodes
- `nvidia-smi pmon -c 5`: Process-level GPU monitoring
- `nvidia-smi --query-gpu`: Structured CSV data
- `nvidia-smi --query-compute-apps`: Per-process VRAM allocation
- Prometheus DCGM metrics: `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`, `DCGM_FI_DEV_POWER_USAGE`, `DCGM_FI_DEV_MEM_COPY_UTIL`
- Prometheus 24h range query: `avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h])` from 2026-02-24T00:00:00Z to 2026-02-25T14:00:00Z
- vLLM `/metrics` endpoints: Node 1 ports 8000 (main) and 8001 (embedding), Node 2 port 8000
- ComfyUI `/queue` endpoint: Node 2 port 8188
- VAULT: `lspci`, `/dev/dri/`, Docker container inspection
