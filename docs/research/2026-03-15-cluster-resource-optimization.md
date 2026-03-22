# Cluster Resource Optimization: Full Hardware Utilization Analysis

**Date:** 2026-03-15
**Status:** Active — context window fix implementing now, larger items queued

---

## Executive Summary

The Athanor cluster has 166 GB of GPU VRAM, 752 GB of RAM, 216 CPU threads, and 29 TB of NVMe across 4 nodes. Current utilization is far below capacity: all 3 vLLM instances are artificially capped at 32K context despite having VRAM for 131K+, two GPUs (WORKSHOP 5060 Ti, FOUNDRY nvme1n1) sit completely idle, 154 GB of FOUNDRY RAM is unused, and 2.8 TB of NVMe on WORKSHOP is unmounted.

The immediate high-impact fix: raise vLLM context windows to match hardware capacity. This eliminates the need for quality-degrading workarounds (truncated context, reduced recursion limits) when agents hit context limits.

---

## 1. Current State Audit (Live Data, 2026-03-15)

### GPU Allocation

| Node | GPU | VRAM Used/Total | Compute Util | Service | Context |
|------|-----|----------------|-------------|---------|---------|
| FOUNDRY | 4x 5070 Ti (TP=4) | 62.5/65.2 GB | 82-99% | Coordinator (Qwen3.5-27B-FP8) | 32K |
| FOUNDRY | 4090 | 23.0/24.6 GB | 0% | Coder (Qwen3.5-35B-A3B-AWQ-4bit) | 32K |
| WORKSHOP | 5090 | 32.1/32.6 GB | 0% | Worker (Qwen3.5-35B-A3B-AWQ-4bit) | 32K |
| WORKSHOP | 5060 Ti | 0.15/16.3 GB | 0% | **IDLE** | — |
| DEV | 5060 Ti | 4.8/16.3 GB | 0% | Embedding + Reranker | — |

### RAM Utilization

| Node | Total | Used | Available | Notes |
|------|-------|------|-----------|-------|
| FOUNDRY | 220 GB | 65 GB | 154 GB | 151 GB in page cache (model files) |
| WORKSHOP | 126 GB | 19 GB | 105 GB | 36 GB in page cache |
| VAULT | 124 GB | 10 GB | 113 GB | 113 GB page cache (media) |
| DEV | 61 GB | 11 GB | 48 GB | |

**Total: 531 GB RAM across 4 nodes. 420 GB available.**

### NVMe Storage

| Node | Device | Size | Mounted | Used |
|------|--------|------|---------|------|
| FOUNDRY | nvme0n1 | 3.6 TB | / (LVM) | 426 GB (13%) |
| FOUNDRY | nvme1n1 | 931 GB | **unmounted** (btrfs) | — |
| FOUNDRY | nvme2n1 | 3.6 TB | /mnt/local-fast | 264 GB (8%) |
| WORKSHOP | nvme0n1 | 3.6 TB | / (LVM) | 314 GB (10%) |
| WORKSHOP | nvme1n1 | 931 GB | **unmounted** (ZFS) | — |
| WORKSHOP | nvme2n1 | 931 GB | **unmounted** (ZFS) | — |
| DEV | nvme2n1 | 912 GB | / | 113 GB (14%) |

**Total: 14.5 TB NVMe. 2.8 TB unmounted on WORKSHOP, 931 GB unmounted on FOUNDRY.**

### CPU Cores

| Node | CPU | Cores/Threads | Load |
|------|-----|--------------|------|
| FOUNDRY | EPYC 7663 | 56C/112T | Light (model serving) |
| WORKSHOP | TR 7960X | 24C/48T | Light |
| VAULT | 9950X | 16C/32T | Light (47 containers) |
| DEV | 9900X | 12C/24T | Light |

**Total: 108 cores / 216 threads. Massively underutilized.**

---

## 2. Critical Fix: vLLM Context Windows

### Why Everything is at 32K

The Ansible default `vllm_max_model_len: 32768` was set conservatively when Qwen3 (pure transformer) was the primary model. It was never updated for Qwen3.5's hybrid architecture, which uses dramatically less KV cache per token.

### Qwen3.5 Hybrid Architecture — KV Cache Math

Qwen3.5 uses DeltaNet (linear attention) for most layers, with full quadratic attention every 4th layer only. This means KV cache is stored only for full-attention layers.

**Qwen3.5-27B-FP8 (Coordinator):**
- 64 layers, full_attention_interval=4 → 16 full attention layers
- 4 KV heads × 256 head_dim × 2 (K+V) × 2 bytes (BF16) = 4 KB per token per layer
- Total: 16 layers × 4 KB = **64 KB per token**
- VRAM budget: 64 GB × 0.85 - 27 GB model = **27.4 GB for KV cache**
- Max tokens: 27.4 GB / 64 KB = **~437K tokens**
- Qwen3.5-27B native max: 262K. Safely run at **131K** with massive headroom.

**Qwen3.5-35B-A3B-AWQ-4bit (Worker on 5090):**
- 40 layers, full_attention_interval=4 → 10 full attention layers
- 2 KV heads × 256 head_dim × 2 × 2 bytes = 2 KB per token per layer
- Total: 10 layers × 2 KB = **20 KB per token**
- VRAM budget: 32 GB × 0.85 - ~19 GB model = **~8 GB for KV cache**
- Max tokens: 8 GB / 20 KB = **~419K tokens**
- Safely run at **131K** with massive headroom.

**Qwen3.5-35B-A3B-AWQ-4bit (Coder on 4090):**
- Same 20 KB per token
- VRAM budget: 24 GB × 0.92 - ~19 GB model = **~3 GB for KV cache**
- Max tokens: 3 GB / 20 KB = **~157K tokens**
- Safely run at **65K** (conservative) or **131K** (should fit, needs testing).

### Action: Increase Context Windows

| Instance | Current | New | Rationale |
|----------|---------|-----|-----------|
| Coordinator (FOUNDRY TP=4) | 32,768 | **131,072** | 27 GB KV budget, only needs ~8 GB for 131K |
| Worker (WORKSHOP 5090) | 32,768 | **131,072** | 8 GB KV budget, only needs ~2.5 GB for 131K |
| Coder (FOUNDRY 4090) | 32,768 | **65,536** | 3 GB KV budget, needs ~1.3 GB for 65K. Test 131K later. |

### Consequence: Revert Quality Degradation Band-aids

With all instances at 65K+ context:
- **Revert `recursion_limit`** from 25 back to 50 (tasks can use 25 tool steps again)
- **Revert `max_chars` context budget** from 2000 back to 6000 (full context injection restored)
- Fallback chain `reasoning → worker → deepseek → claude` now works without overflow — both local models have 131K context

---

## 3. Idle GPU Utilization

### WORKSHOP 5060 Ti (16 GB) — Completely Idle

Options ranked by value:

1. **STT/TTS endpoint** — Whisper + Piper are already on FOUNDRY. Moving them here frees FOUNDRY CPU/RAM for inference. ComfyUI already uses this GPU slot via `comfyui_gpu_device: "1"` in Ansible — check if it actually uses the 5060 Ti or 5090.

2. **Small fast model** — Qwen3-8B-abliterated or GLM-4.7-Flash-GPTQ-4bit (~8 GB). Would serve as local "fast" tier — lower latency than the 35B MoE models for simple queries. Could handle utility/grader/fast slots.

3. **Vision model** — Qwen3.5-27B (with VLM encoder, not `--language-model-only`) for image understanding. Would need ~14 GB. Enables photo analysis for Stash agent, image description for Knowledge agent.

4. **Move embedding/reranker from DEV** — Currently on DEV 5060 Ti using only 4.8 GB. Moving to WORKSHOP 5060 Ti keeps them closer to the inference stack (5GbE vs 5GbE on DEV). Frees DEV GPU entirely.

**Recommendation:** Option 2 (small fast model) has highest immediate value — reduces latency for simple agent queries and provides a true "fast" tier distinct from the 35B worker.

### DEV 5060 Ti (16 GB) — 4.8 GB Used

Currently hosts embedding (Qwen3-Embedding-0.6B) and reranker (Qwen3-Reranker-0.6B) — tiny models using minimal VRAM. If these move to WORKSHOP, DEV GPU becomes fully available for:
- Development/testing of new models
- CI inference testing
- On-demand model evaluation

### FOUNDRY 4090 (24 GB) — Loaded but Idle

The coder model is loaded but rarely used (0% compute utilization). Consider:
- **Time-sharing**: Load Qwen3-Coder-30B-A3B when coding tasks arrive, swap to a different model otherwise. vLLM doesn't support hot-swapping, but could use Docker container cycling.
- **Keep as-is**: Having a dedicated coding model available instantly has value for agent tasks. The VRAM cost is already paid.

---

## 4. RAM Optimization

### FOUNDRY — 154 GB Available

- **Model file caching**: The 151 GB page cache is already serving model files — NFS reads from VAULT are cached in RAM. This is working correctly.
- **Swap space**: 16 GB `--swap-space` on coordinator enables vLLM to handle burst KV cache overflow to system RAM. With 154 GB available, could increase to 32 GB for even more burst capacity.
- **CPU inference**: llama.cpp or vLLM CPU backend could run a model on the 56-core EPYC for overflow. Qwen3-14B at ~28 GB in RAM would give 2-4 tok/s — not fast, but usable for background tasks.

### WORKSHOP — 105 GB Available

- Same NFS caching pattern. No changes needed.

### VAULT — 113 GB Available

- Running 47 containers but only using 10 GB. Healthy state.

---

## 5. Storage Optimization

### Unmounted NVMe Drives

**WORKSHOP nvme1n1 + nvme2n1 (2x 931 GB, ZFS members):**
These are formatted as ZFS but unmounted. Options:
- Mount as ZFS pool for local model cache (faster than NFS from VAULT)
- Use as local scratch for ComfyUI output, training data
- RAID-0 for 1.8 TB fast local storage

**FOUNDRY nvme1n1 (931 GB, btrfs):**
Formatted but unmounted. Could serve as:
- Secondary model cache (supplement /mnt/local-fast)
- Triton cache persistence (currently in home dir)
- Container volume storage

### NFS Performance

WORKSHOP reads models from VAULT NFS (932 GB share, 85% full). The `--safetensors-load-strategy eager` flag already optimizes this by converting random page faults to sequential reads. With 5GbE, model loading takes ~30s for 20 GB models. Local NVMe cache would reduce this to ~5s.

**Recommendation:** Mount WORKSHOP ZFS pool and rsync frequently-used models locally. Saves 25s on every model load/restart.

---

## 6. Workload Expansion Opportunities

With current idle resources, these workloads could run without displacing anything:

| Workload | GPU | VRAM | Node | Value |
|----------|-----|------|------|-------|
| Fast inference (Qwen3-8B) | 5060 Ti | ~8 GB | WORKSHOP | Low-latency agent queries |
| Vision model (Qwen3.5-27B VLM) | 5060 Ti | ~14 GB | WORKSHOP | Photo/image analysis |
| CPU inference (Qwen3-14B) | None | ~28 GB RAM | FOUNDRY | Background overflow |
| Training/fine-tuning | 5060 Ti | 16 GB | DEV | Model customization |
| Local model cache | None | 1.8 TB NVMe | WORKSHOP | Faster model loading |

---

## 7. Implementation Priority

### Immediate (This Session)
1. Increase coordinator context: 32K → 131K
2. Increase worker context: 32K → 131K
3. Increase coder context: 32K → 65K
4. Revert agent recursion_limit and context budget to original values
5. Deploy via Ansible

### Short-term (Next 1-2 Sessions)
6. Deploy small fast model on WORKSHOP 5060 Ti
7. Mount WORKSHOP ZFS pool, create local model cache
8. Increase coder to 131K after testing 65K

### Medium-term (Next Week)
9. Move embedding/reranker from DEV → WORKSHOP 5060 Ti
10. Mount FOUNDRY nvme1n1 for secondary storage
11. Evaluate CPU inference on FOUNDRY for overflow
12. Consider vision model for Stash/Knowledge agents

---

*Last updated: 2026-03-15*
