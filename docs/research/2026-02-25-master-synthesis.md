# Session 19 Master Synthesis: Full-Stack Resource Optimization

**Date:** 2026-02-25
**Status:** Complete — synthesis of 24 research agents + 5 hardware audits
**Purpose:** Map every discovered model to every GPU slot, every resource optimization to every node, and create a prioritized action list

---

## Executive Summary

Session 19 launched 24 parallel research agents covering 14 model categories, 5 hardware audits, and 3 resource utilization strategies. The results reveal:

1. **The cluster is 99.13% idle.** This is a demand problem, not a hardware problem. The autonomous task engine (built this session) is the single highest-ROI fix.
2. **The 5090 is completely wasted.** Zero requests served. 32 GB VRAM holding a model nobody talks to.
3. **400+ GB of system RAM sits unused** across 4 nodes. This enables CPU inference, KV cache offloading, model caching, and MoE expert paging.
4. **112+ CPU cores are idle.** EPYC 7663 alone could run embedding, reranking, and a 7B auxiliary model at zero GPU cost.
5. **6 TB of NVMe storage is unused** (3TB Gen5 on Node 2, 1TB on Node 1, 2TB on DEV). Model preloading from local NVMe would eliminate NFS latency.
6. **6 inventory discrepancies** found across DEV and Node 1. Hardware docs need updating.
7. **~~Qdrant backups empty~~** — RESOLVED. Backups working (25 MB, 4 collections, nightly). VAULT audit was wrong (stale NFS handle).
8. **vLLM v0.15.0+ is the critical upgrade** — unlocks DeltaNet (Qwen3.5), NVFP4, SageAttention2, EAGLE-3 speculative decoding.

---

## Part 1: The Model Landscape (200+ Models Surveyed)

### 1.1 What Changed Since Last Research (Feb 16)

The Qwen3.5 family dropped Feb 16-24, 2026. This changes everything:

| Model | Params | Active | SWE-bench | BFCL V4 | Architecture | Status |
|-------|--------|--------|-----------|---------|-------------|--------|
| Qwen3.5-27B | 27B | 27B (dense) | 72.4% | ~68% | DeltaNet | **Primary upgrade target** |
| Qwen3.5-35B-A3B | 35B | 3B | 69.2% | — | DeltaNet MoE | Fast coding model |
| Qwen3.5-122B-A10B | 122B | 10B | 72.0% | — | DeltaNet MoE | Fits Node 1 TP=4 AWQ |
| Qwen3.5-397B-A17B | 397B | 17B | 76.4% | — | DeltaNet MoE | Needs expert offloading |
| Qwen3-32B-AWQ | 32B | 32B | ~55% | 48.7% (V4) | Standard | **Currently deployed** |

**BFCL V4 correction:** Our MEMORY.md listed Qwen3-32B-AWQ at 68.2% — that was V3. V4 score is 48.71%. Qwen3.5-27B scores ~68% on V4, a massive tool-calling improvement.

**CRITICAL BLOCKER:** Qwen3.5 uses Gated DeltaNet attention, which requires vLLM v0.15.0+. Current NGC image is v0.11.1. This is the single most important infrastructure upgrade.

### 1.2 Model → GPU Slot Mapping

#### Node 1: Foundry (EPYC 7663, 224 GB RAM, 5 GPUs)

| GPU | Current | Proposed | VRAM | Model | Rationale |
|-----|---------|----------|------|-------|-----------|
| GPUs 0-3 (TP=4) | Qwen3-32B-AWQ | **Qwen3.5-27B FP8** | ~54 GB across 4 | Primary backbone | 72.4% SWE-bench, 68% BFCL V4, DeltaNet saves KV cache |
| GPU 4 (5070 Ti) | Embedding + Whisper | **Embedding → CPU**, keep Whisper, add reranker | 16 GB | Whisper (2.1 GB) + Qwen3-Reranker-0.6B (1.5 GB) + Speaches | Move 0.6B embedding to EPYC CPU (FastEmbed). Free 6.7 GB for reranker + future |
| CPU (EPYC 56C) | Idle | **FastEmbed + llama.cpp 7B + anomaly detection** | — | Qwen3-8B Q4_K_M on 16 cores | 15-25 tok/s on 8-channel DDR4. Background tasks, tagging, intent classification |

**TP=4 VRAM math:** Qwen3.5-27B FP8 = ~27 GB total. Distributed across 4 GPUs = ~6.75 GB each. But TP overhead + KV cache means ~13-14 GB per GPU. Fits the 3x 16 GB + 1x 24 GB TP group with room for longer contexts.

**Alternative if vLLM v0.15.0 is delayed:** Stay on Qwen3-32B-AWQ but add speculative decoding with Qwen3-0.6B draft model (~1.2 GB extra VRAM). Estimated 2-3x throughput improvement for free.

#### Node 2: Workshop (TR 7960X, 128 GB RAM, 2 GPUs)

| GPU | Current | Proposed | VRAM | Model | Rationale |
|-----|---------|----------|------|-------|-----------|
| GPU 0 (5090) | Qwen3-14B FP16 (0 requests) | **Qwen3.5-27B FP8 (secondary)** or **dedicated coding model** | 32 GB | Qwen3.5-27B FP8 (~14 GB) + Qwen2.5-VL-7B AWQ (~4 GB) | Frees 14 GB for VLM. Or: Qwen3.5-35B-A3B for fast coding |
| GPU 1 (5060 Ti) | ComfyUI (lazy) | **ComfyUI + dedicated FIM completion** | 16 GB | Flux/Wan2.x on demand + Qwen2.5-Coder-1.5B FP16 (3 GB) via Tabby | Code completion for IDE. Models share via lazy loading |
| CPU (TR 24C) | Idle | **CI runner + build server** | — | Gitea Actions runner, distcc node | 24 Zen 4 cores with AVX-512 |

**The 5090 problem solved:** Replace zero-request Qwen3-14B FP16 with either:
- **Option A:** Qwen3.5-27B FP8 (~14 GB) + Qwen2.5-VL-7B AWQ (~4 GB) = secondary backbone + vision. 14 GB free.
- **Option B:** Qwen3.5-35B-A3B AWQ (~10 GB) = dedicated fast coding agent. 22 GB free for batch work.
- **Option C:** Magnum-v4-72B Q4 (~40 GB total, but only 32 GB available) — doesn't fit without offloading. Use Magnum-v4-12B instead for EoBQ creative work.

#### VAULT (9950X, 128 GB RAM, Arc A380)

| Resource | Current | Proposed | Rationale |
|----------|---------|----------|-----------|
| Arc A380 | Plex transcode only | + OpenVINO small classifier | Stash auto-tagging when library populated |
| CPU | 99% idle | + Piper TTS (already CPU) | No change needed |
| RAM | 93% filesystem cache | Keep as-is | Already optimal for NFS serving |

#### DEV (i7-13700K, 64 GB RAM, RTX 3060 12GB)

| Resource | Current | Proposed | Rationale |
|----------|---------|----------|-----------|
| RTX 3060 | Idle (not even known to be there!) | **Local inference for dev testing** | Run Qwen3-8B Q4 (~5 GB) for local testing without hitting cluster |
| WSL2 | 8 CPU / 16 GB RAM | **Increase to 16 CPU / 32 GB RAM** | Currently wastes 16 threads and 48 GB RAM |
| Ethernet | 100 Mbps (BAD CABLE) | **Replace cable** | 10x throughput for all SSH/rsync/Ansible |

### 1.3 Specialized Model Deployments

| Use Case | Model | Where | VRAM/Resources | Priority |
|----------|-------|-------|---------------|----------|
| **Speculative decoding** | Qwen3-0.6B (draft) | Node 1 TP=4 | ~1.2 GB shared | HIGH — 2-3x throughput, zero cost |
| **RAG reranking** | Qwen3-Reranker-0.6B | Node 1 CPU or GPU 4 | ~1.5 GB or CPU | HIGH — dramatically improves retrieval |
| **Cascade quality gate** | Skywork-Reward-V2-Qwen3-0.6B | Node 1 CPU | ~1.2 GB | MEDIUM — enables auto-approval for local tasks |
| **Code completion (FIM)** | Qwen2.5-Coder-1.5B | Node 2 GPU 1 via Tabby | ~3 GB | MEDIUM — IDE integration |
| **Vision/OCR** | Qwen2.5-VL-7B + GOT-OCR-2.0 | Node 2 GPU 0 | ~4 GB + 0.6 GB | MEDIUM — document understanding, Stash |
| **TTS upgrade** | Qwen3-TTS-1.7B | Node 1 GPU 4 | ~3.4 GB | LOW — replaces CPU Piper with neural TTS |
| **Creative writing (EoBQ)** | Cydonia-24B-v4.3 Q6_K | Node 2 GPU 0 | ~18 GB | LOW — EoBQ-specific |
| **Uncensored (Stash)** | Qwen3-VL-8B-abliterated | Node 2 GPU 0 | ~8 GB AWQ | LOW — needs Stash library content first |
| **Time-series forecasting** | IBM TinyTimeMixer | Any CPU | 805K params | LOW — Prometheus metric prediction |
| **Music generation** | ACE-Step v1.5 Turbo | Node 2 GPU 1 | <4 GB | LOW — EoBQ soundtracks |

---

## Part 2: Hardware Optimization Plan

### 2.1 Critical Fixes (P0 — Data Loss Risk)

| # | Issue | Action | Node | Impact |
|---|-------|--------|------|--------|
| 1 | ~~Qdrant backups EMPTY~~ **RESOLVED** | Backups are working (25 MB, 4 collections, nightly at 03:00). VAULT audit was wrong due to stale NFS handle on parent dir. | Node 1 → VAULT | No data loss risk |
| 2 | **DEV ethernet at 100 Mbps** | Replace ethernet cable (bad cable causing 10x slower SSH/rsync) | DEV | All cluster management workflows |

### 2.2 High-Impact Quick Wins (P1 — Do This Week)

| # | Action | Node | Effort | Impact |
|---|--------|------|--------|--------|
| 1 | **Replace 5090 workload** — Stop Qwen3-14B FP16, deploy useful model | Node 2 | 30 min | Reclaim $2000 GPU doing zero work |
| 2 | **Mount Node 1 nvme1n1** — `mount /dev/nvme1n1p1 /mnt/local-fast` + add to fstab | Node 1 | 5 min | 1 TB fast local storage for model cache |
| 3 | **Add speculative decoding** — Download Qwen3-0.6B, add `--speculative-model` to vLLM | Node 1 | 15 min | 2-3x inference throughput |
| 4 | **Enable EXPO on Node 2** — BIOS setting via JetKVM | Node 2 | 10 min | DDR5 4800→5600 MT/s (16.7% memory bandwidth) |
| 5 | **Move embedding to CPU** — Deploy FastEmbed on EPYC, free GPU 4 VRAM | Node 1 | 1 hr | Free 6.7 GB VRAM, negligible latency impact |
| 6 | **Increase WSL2 resources** — Edit `.wslconfig`: `processors=16`, `memory=32GB` | DEV | 5 min | 2x CPU, 2x RAM for development |
| 7 | **Switch Node 2 governor** — `performance` instead of `powersave` | Node 2 | 5 min | Lower inference latency |
| 8 | **Deploy Qwen3-Reranker-0.6B** — CPU or GPU 4, integrate with RAG pipeline | Node 1 | 1 hr | Major retrieval quality improvement |
| 9 | **Update hardware inventory** — Fix 6 discrepancies found by audits | All | 30 min | Accurate documentation |

### 2.3 Medium-Impact Optimizations (P2 — This Month)

| # | Action | Node | Effort | Impact |
|---|--------|------|--------|--------|
| 1 | **vLLM NGC upgrade** to v0.15.0+ | Node 1, 2 | 2 hrs | Unlocks Qwen3.5, DeltaNet, NVFP4, SageAttention2 |
| 2 | **Deploy Qwen3.5-27B** on TP=4 (replacing Qwen3-32B) | Node 1 | 1 hr | 72.4% vs ~55% SWE-bench, 68% vs 49% BFCL V4 |
| 3 | **Jumbo frames** (MTU 9000) on 5GbE links | All nodes + VAULT | 1 hr | ~15-30% NFS throughput improvement |
| 4 | **KV cache CPU offloading** — Use 200+ GB free Node 1 RAM | Node 1 | 1 hr | 2-4x effective context length |
| 5 | **llama.cpp auxiliary model** — Qwen3-8B Q4_K_M on EPYC | Node 1 | 2 hrs | Free background inference (tagging, summarization) |
| 6 | **NVMe model preloading** — Copy hot models to Node 1/2 local NVMe | Node 1, 2 | 1 hr | Instant model loading vs NFS |
| 7 | **Deploy code completion** — Tabby + Qwen2.5-Coder-1.5B on Node 2 | Node 2 | 2 hrs | IDE autocomplete for Shaun |
| 8 | **Kernel tuning** — hugepages, vm.swappiness=10, readahead for NVMe | Node 1, 2 | 30 min | Lower tail latency |
| 9 | **GPU power limits** — Raise 5070 Ti from 250W to 300W, 4090 from 320W to 450W | Node 1 | 5 min | ~17-29% higher peak throughput |

### 2.4 Architecture Upgrades (P3 — When Ready)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **EAGLE-3 speculative decoding** — When vLLM supports it, 5.6x throughput | Depends on vLLM | Massive throughput increase |
| 2 | **SageAttention2** — INT8/FP8 attention kernels, 2-5x attention speedup | vLLM flag | Major latency reduction |
| 3 | **MoE expert offloading** — KTransformers for Qwen3.5-397B-A17B on Node 1 | 4 hrs | 76.4% SWE-bench at zero API cost |
| 4 | **Distributed TP across nodes** — Pipeline parallelism Node 1 + Node 2 | Research | Run 70B+ models across both nodes |
| 5 | **NVMe-oF** — Export Node 2's 3TB Gen5 NVMe to Node 1 over TCP | 2 hrs | Fast remote storage |

---

## Part 3: Resource Utilization Plan

### 3.1 GPU Utilization (Currently 0.87%)

**Current state:** 7 GPUs, 138.7 GB VRAM, 99.13% idle. The autonomous task engine + scheduler (built this session) is the primary fix.

**Target:** 20-40% average utilization within one month via:
- Scheduled agent tasks (general-assistant 30min, media-agent 15min, home-agent 5min)
- Autonomous coding tasks (overnight batch work)
- Creative pipeline generation (EoBQ scene assets, batch image generation)
- Knowledge base maintenance (continuous re-indexing)

**Longer-term target:** 40-60% via:
- Dedicated coding model doing continuous test generation
- Vision model processing Stash library (when populated)
- Real-time HA anomaly detection
- Proactive research synthesis

### 3.2 CPU Utilization (Currently ~5%)

| Node | Total Cores | Currently Used | Proposed Use |
|------|-------------|---------------|--------------|
| Node 1 (EPYC 56C) | 112T | ~4T (vLLM) | +16T embedding, +16T llama.cpp, +4T reranker, +2T anomaly |
| Node 2 (TR 24C) | 48T | ~2T (vLLM+dashboard) | +8T CI runner, +4T llama.cpp fallback, +4T builds |
| VAULT (9950X 16C) | 32T | ~3T (containers) | No change — CPU serves NFS/containers well |
| DEV (13700K 16C) | 24T | ~8T (WSL2) | +8T (increase WSL2 allocation) |

**Expected utilization lift:** 5% → 20-40% sustained, 60-80% burst.

### 3.3 RAM Utilization (Currently ~30 GB / 544 GB = 5.5%)

| Node | Total | Used | Free | Proposed Use |
|------|-------|------|------|-------------|
| Node 1 | 224 GB | ~8 GB | 216 GB | KV cache offload (64 GB), llama.cpp model (8 GB), tmpfs model cache (32 GB), huge pages (64 GB) |
| Node 2 | 128 GB | ~8.5 GB | 119 GB | llama.cpp fallback (8 GB), tmpfs model cache (16 GB), build cache |
| VAULT | 128 GB | ~7.4 GB | 120 GB | Keep as filesystem cache (already optimal) |
| DEV | 64 GB | ~16 GB | 48 GB | Increase WSL2 to 32 GB |

### 3.4 Storage Utilization

| Node | Unused Storage | Proposed Use |
|------|---------------|-------------|
| Node 1 | 1 TB NVMe (unmounted!) | Model cache, agent workspace, Docker overlay |
| Node 2 | 3 TB Gen5 NVMe (untouched) | Video scratch (RAID0), model preloading, CI artifacts |
| VAULT | Array at 90% (19 TB free) | Monitor, alert at 95%, plan expansion |
| DEV | 7 TB total, most free | Dev workspace, local model cache |

---

## Part 4: The Cascade Architecture

### 4.1 Five-Tier Inference Cascade

```
Tier 1: Local Draft  → Qwen3-0.6B speculative (free, ~100 tok/s)
Tier 2: Local Coder  → Qwen3.5-27B on TP=4 (free, 25-35 tok/s, 72.4% SWE-bench)
Tier 3: Cloud Budget → Claude Sonnet 4.6 ($3/$15 per M, 79.6% SWE-bench)
Tier 4: Cloud Strong → Kimi K2.5 ($3/$9 per M, top-tier)
Tier 5: Cloud Frontier → Claude Opus 4.6 ($15/$75 per M, ~80%+ SWE-bench)
```

### 4.2 Quality Gate (Skywork-Reward-V2)

Every local generation passes through Skywork-Reward-V2-Qwen3-0.6B (1.2 GB, 85.2 RewardBench) on CPU:
- Score > 0.8 → auto-approve (no cloud cost)
- Score 0.5-0.8 → human review or Claude Sonnet review ($0.02)
- Score < 0.5 → auto-escalate to Claude Sonnet for retry

**Expected cloud cost reduction:** 70-90% of current usage stays local (zero cost). Only novel/complex problems hit the cloud.

### 4.3 LiteLLM Routing Config

```yaml
model_list:
  # Tier 2: Local backbone (Qwen3.5-27B when deployed, Qwen3-32B until then)
  - model_name: reasoning
    litellm_params:
      model: openai/Qwen/Qwen3.5-27B  # or current Qwen3-32B-AWQ
      api_base: http://192.168.1.244:8000/v1
      api_key: dummy

  # Fast local (Node 2 — replace 14B with useful model)
  - model_name: fast
    litellm_params:
      model: openai/Qwen/Qwen3.5-35B-A3B
      api_base: http://192.168.1.225:8000/v1
      api_key: dummy

  # Tier 3: Cloud budget
  - model_name: cloud-budget
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY

  # Tier 5: Cloud frontier
  - model_name: cloud-frontier
    litellm_params:
      model: anthropic/claude-opus-4-6
      api_key: os.environ/ANTHROPIC_API_KEY

  # Embedding (CPU after migration)
  - model_name: embedding
    litellm_params:
      model: openai/Qwen/Qwen3-Embedding-0.6B
      api_base: http://192.168.1.244:8001/v1
      api_key: dummy

  # Code completion (Node 2, Tabby)
  - model_name: completion
    litellm_params:
      model: openai/Qwen/Qwen2.5-Coder-1.5B
      api_base: http://192.168.1.225:8087/v1
      api_key: dummy
```

---

## Part 5: EoBQ Creative Pipeline

The narrative models research found a rich ecosystem of creative-specialist models. For EoBQ:

| Role | Model | Location | Quality |
|------|-------|----------|---------|
| Scene direction + prose | Magnum-v4-72B Q4_K_M (or Qwen3.5-27B) | Node 1 TP=4 | Claude-quality prose, Apache 2.0 |
| Character dialogue | Cydonia-24B-v4.3 Q6_K | Node 2 5090 | Best character distinction at size |
| Fast draft/iteration | Rocinante-X-12B-v1 Q8 | Node 2 5060 Ti | Above-weight performance |
| Quality gate | WritingBench-Critic-7B | CPU or GPU 4 | First real creative writing benchmark |
| Image generation | Flux Dev FP8 or Z-Image-Turbo | Node 2 5060 Ti | Z-Image is faster (8 steps vs 20+) |
| Video generation | Wan2.x T2V (current) → Wan2.2 when available | Node 2 5060 Ti | MoE architecture in Wan2.2 |
| TTS (voice acting) | Qwen3-TTS-1.7B (upgrade from Piper) | Node 1 GPU 4 | Voice cloning, emotion control |
| Music/soundtrack | ACE-Step v1.5 Turbo | Node 2 5060 Ti | <4 GB, <10s per song |
| Sound effects | MOSS-SoundEffect | Node 2 5060 Ti | First open-source text-to-SFX |

---

## Part 6: Inventory Corrections Required

| # | Item | Current Doc | Reality | Action |
|---|------|------------|---------|--------|
| 1 | DEV GPU | RX 5700 XT 8 GB | **RTX 3060 12 GB** | Update inventory.md |
| 2 | DEV RAM | DDR5-5200 CL36 | **DDR5-5600 CL40** | Update inventory.md |
| 3 | DEV Storage | "Unknown" | 3 NVMe (4TB+2TB+1TB = 7TB) | Update inventory.md |
| 4 | 990 PRO 4TB | "In Node 1" | **NOT in Node 1** | Locate physically |
| 5 | VAULT containers | 13 | **15** | Update SERVICES.md |
| 6 | 5060 Ti PCIe | x16 | **x8** | Update inventory.md |
| 7 | BFCL score | 68.2% | **48.71% (V4)** | Update MEMORY.md |
| 8 | Node 2 DDR5 speed | 5600 MT/s | **4800 MT/s (no EXPO)** | Update inventory.md + enable EXPO |
| 9 | VAULT has iGPU | Not documented | **AMD Radeon (Granite Ridge)** | Add to inventory.md |
| 10 | DEV Samsung 970 EVO | Listed as loose | **No longer in DEV** | Track location |

---

## Part 7: Prioritized Action Plan

### This Session (Before Sleep)

- [x] Complete task execution engine (tasks.py) — `_build_task_prompt`, `_maybe_retry`, `_cleanup_old_tasks`
- [x] Launch 24 research agents covering all model categories + hardware audits
- [ ] **Deploy tasks.py** to Node 1 (rsync + rebuild)
- [x] ~~Investigate Qdrant backup failure~~ (RESOLVED — backups working)

### This Week

1. Replace DEV ethernet cable (100 Mbps → 1 Gbps)
2. Mount Node 1 nvme1n1 (1 TB free storage)
3. Replace 5090 workload (Qwen3-14B → useful model)
4. Add speculative decoding (Qwen3-0.6B draft)
5. Enable EXPO on Node 2 (DDR5 4800 → 5600)
6. Increase WSL2 resources (8 CPU → 16, 16 GB → 32 GB)
7. Update hardware inventory with all corrections
8. Move embedding to CPU (FastEmbed on EPYC)
9. Deploy Qwen3-Reranker-0.6B

### This Month

1. Upgrade vLLM NGC to v0.15.0+
2. Deploy Qwen3.5-27B on Node 1 TP=4
3. Jumbo frames on 5GbE
4. KV cache CPU offloading
5. Deploy llama.cpp 7B on EPYC
6. Deploy code completion (Tabby + Qwen2.5-Coder-1.5B)
7. NVMe model preloading
8. Kernel tuning (hugepages, swappiness, readahead)
9. Raise GPU power limits on Node 1

### Next Quarter

1. EAGLE-3 speculative decoding
2. SageAttention2
3. MoE expert offloading (Qwen3.5-397B-A17B)
4. EoBQ creative pipeline (Cydonia + Rocinante + ACE-Step)
5. Stash AI Phase 2 (when library populated)
6. Distributed TP across nodes
7. NVMe-oF from Node 2 to Node 1

---

## Part 8: Research Index

All research produced this session, stored in `docs/research/`:

### Model Research (14 categories)
| File | Models | Key Finding |
|------|--------|------------|
| `2026-02-25-coding-models-exhaustive.md` | 40 | Qwen3.5-27B (72.4% SWE-bench) replaces Qwen3-32B |
| `2026-02-25-tool-calling-models-exhaustive.md` | 109 | BFCL V4 correction: 48.71% not 68.2% |
| `2026-02-25-embedding-models-exhaustive.md` | — | Qwen3-VL-Embedding-2B for multimodal |
| `2026-02-25-uncensored-models-exhaustive.md` | 60+ | Qwen3-VL-8B-abliterated for Stash |
| `2026-02-25-reasoning-models-exhaustive.md` | — | vLLM v0.15.0+ BLOCKER for DeltaNet |
| `2026-02-25-vision-models-exhaustive.md` | 60+ | Qwen2.5-VL-7B primary, GOT-OCR-2.0 |
| `2026-02-25-specialized-domain-models-exhaustive.md` | — | TinyTimeMixer (805K), Home-LLM, XiYan-SQL |
| `2026-02-25-small-models-exhaustive.md` | 50+ | Qwen3-0.6B draft = 2-3x speedup |
| `2026-02-25-code-completion-models-exhaustive.md` | 14 families | Qwen2.5-Coder-1.5B + Tabby |
| `2026-02-25-reward-judge-models-exhaustive.md` | — | Skywork-Reward 0.6B for cascade gating |
| `2026-02-25-creative-models-exhaustive.md` | 39 | Qwen3-TTS, ACE-Step, Z-Image-Turbo |
| `2026-02-25-narrative-models-exhaustive.md` | 30+ | Magnum-v4-72B, Cydonia-24B for EoBQ |
| `2026-02-25-architecture-innovations-exhaustive.md` | — | vLLM v0.15.1: 65% faster FP4, EAGLE-3 5.6x |
| `2026-02-25-local-coding-models-update.md` | — | Qwen3.5 family deployment tables |
| `2026-02-25-cloud-coding-api-cascade.md` | — | Sonnet 4.6 as primary cloud tier |

### Hardware Audits (5 nodes)
| File | Key Finding |
|------|------------|
| `docs/hardware/2026-02-25-node1-deep-audit.md` | GPU power caps, unmounted NVMe, channel H empty |
| `docs/hardware/2026-02-25-node2-deep-audit.md` | DDR5 at 4800, 3TB Gen5 unused, 5060 Ti x8 |
| `docs/hardware/2026-02-25-vault-deep-audit.md` | ~~Qdrant backups EMPTY~~ (RESOLVED), array 90%, 15 containers |
| `docs/hardware/2026-02-25-dev-network-audit.md` | RTX 3060 (not RX 5700 XT!), 100Mbps ethernet |
| `docs/hardware/2026-02-25-gpu-utilization-analysis.md` | 99.13% idle, 0 requests on 5090 |

### Resource Optimization
| File | Key Finding |
|------|------------|
| `2026-02-25-cpu-utilization-strategies.md` | Move embedding to CPU, llama.cpp 7B on EPYC |
| `2026-02-25-ram-utilization-strategies.md` | KV offload (80 GB on Node 1), KTransformers for 235B MoE, tmpfs model cache (<0.2s load), 18%→81% RAM util |
| `2026-02-25-storage-optimization-strategies.md` | Local NVMe model cache (16s→3s cold start), nconnect=8, LMCache for KV sharing, vLLM swap-space, zram |

---

## Appendix: Full VRAM Budget (Proposed)

### Node 1 (4x 5070 Ti 16 GB + 4090 24 GB = 88 GB total)

| GPU | Model | VRAM | Free |
|-----|-------|------|------|
| GPU 0 (5070 Ti) | Qwen3.5-27B FP8 shard 0 + Qwen3-0.6B draft | ~14.5 GB | 1.8 GB |
| GPU 1 (5070 Ti) | Qwen3.5-27B FP8 shard 1 | ~13.5 GB | 2.8 GB |
| GPU 2 (4090) | Qwen3.5-27B FP8 shard 2 | ~13.5 GB | 11.1 GB |
| GPU 3 (5070 Ti) | Qwen3.5-27B FP8 shard 3 | ~13.5 GB | 2.8 GB |
| GPU 4 (5070 Ti) | Whisper (2.1 GB) + Reranker (1.5 GB) + Speaches (lazy) + TTS (3.4 GB) | ~7 GB | 9.3 GB |
| **Totals** | | **~62 GB** | **27.8 GB free** |

### Node 2 (5090 32 GB + 5060 Ti 16 GB = 48 GB total)

**Option A (Secondary Backbone + Vision):**
| GPU | Model | VRAM | Free |
|-----|-------|------|------|
| GPU 0 (5090) | Qwen3.5-27B FP8 (14 GB) + Qwen2.5-VL-7B AWQ (4 GB) | ~18 GB | 14.6 GB |
| GPU 1 (5060 Ti) | ComfyUI lazy + Qwen2.5-Coder-1.5B (3 GB) | ~3 GB idle | 13.3 GB |

**Option B (Fast Coding + Creative):**
| GPU | Model | VRAM | Free |
|-----|-------|------|------|
| GPU 0 (5090) | Qwen3.5-35B-A3B AWQ (10 GB) + Cydonia-24B Q4 (14 GB) | ~24 GB | 8.6 GB |
| GPU 1 (5060 Ti) | ComfyUI lazy + Rocinante-12B Q8 (12 GB) | ~12 GB active | 4.3 GB |
