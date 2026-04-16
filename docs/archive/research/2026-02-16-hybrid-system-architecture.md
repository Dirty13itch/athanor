# Hybrid System Architecture: Cloud Coding + Local Everything Else

**Date**: 2026-02-16
**Status**: Research complete
**Purpose**: Design the optimal Athanor system configuration using current hardware (no PRO 6000 Max-Q), with cloud APIs for frontier coding and local infrastructure for everything else.

---

## Core Insight

Frontier coding models (480B-1T+ parameters) run at 5-18 tok/s locally with heavy RAM offloading. The same models run at 50-100+ tok/s via cloud APIs. Meanwhile, the workloads that *require* local infrastructure — uncensored inference, image/video generation, game AI, private data processing, always-on agents — are well-served by 7B-70B class models that fit comfortably in the available VRAM.

**The hybrid approach**: Cloud handles frontier coding at speed. Local handles everything that needs to be uncensored, private, always-on, or GPU-accelerated. The hardware stops fighting the VRAM ceiling and instead excels at concurrent multi-workload serving.

This aligns with VISION.md: "Cloud AI Stays in the Mix — Claude Code, Kimi Code, and other cloud coding/AI tools remain part of Shaun's workflow. Athanor does not replace them — it complements them."

---

## Hardware Configuration (Current, No Max-Q)

### Node 1 — "Foundry" (Heavy LLM Inference)

| Component | Spec |
|-----------|------|
| CPU | AMD EPYC 7663 56C/112T |
| RAM | 224 GB DDR4 ECC |
| Motherboard | ASRock Rack ROMED8-2T |
| Chassis | Mining GPU enclosure (6-8 GPU, PCIe risers) |
| PSU | Dual PSU (1,000-1,200W ATX + 750-1,000W SFX) |

| Slot | Type | GPU | VRAM |
|------|------|-----|------|
| 1 | Gen4 x16 | RTX 4090 | 24 GB |
| 2 | Gen4 x16 | RTX 5070 Ti #1 | 16 GB |
| 3 | Gen4 x16 | RTX 5070 Ti #2 | 16 GB |
| 4 | Gen4 x8 | RTX 5070 Ti #3 | 16 GB |
| 5 | Gen4 x8 | RTX 5070 Ti #4 | 16 GB |
| 6 | Gen4 x8 | RTX 3060 | 12 GB |
| 7 | Gen4 x8 | InfiniBand (optional) | — |
| | | **Total VRAM** | **100 GB** |
| | | **Addressable (VRAM + RAM)** | **324 GB** |

RTX 4090 gets slot 1 (x16) — highest VRAM and bandwidth ceiling (1,008 GB/s). Two 5070 Ti on x16, two on x8. RTX 3060 on x8 (fine for embeddings).

### Node 2 — "Workshop" (Creative + Diverse Serving)

| Component | Spec |
|-----------|------|
| CPU | AMD Threadripper 7960X 24C/48T (post TRX50↔X870E swap) |
| RAM | 192 GB DDR5 (128 GB from VAULT + 64 GB loose kit) |
| Motherboard | Gigabyte TRX50 AERO D |
| Chassis | Silverstone RM52 (or standard ATX case) |

| Slot | Type | GPU | VRAM |
|------|------|-----|------|
| 1 | Gen5 x16 | RTX 5090 | 32 GB |
| 2 | Gen5 x16 | *(free — future Max-Q or other)* | — |
| 3 | Gen5 x16 | InfiniBand (optional) | — |
| | | **Total VRAM** | **32 GB** |
| | | **Addressable (VRAM + RAM)** | **224 GB** |

RTX 5090 at full Gen5 x16 (64 GB/s) — the highest-value card gets the best slot.

### VAULT — Storage + Services

| Component | Spec |
|-----------|------|
| CPU | Ryzen 9 9950X 16C/32T (post-swap) |
| RAM | 128 GB DDR5 |
| Motherboard | ASUS X870E CREATOR WIFI (post-swap) |
| GPU | Intel Arc A380 (Plex transcoding) |
| Storage | 164 TB HDD array (Unraid) |

### DEV — Client Workstation

| Component | Spec |
|-----------|------|
| CPU | i7-13700K |
| RAM | 64 GB DDR5 |
| GPU | RX 5700 XT (display only, moved from loose inventory) |
| Role | Daily driver, Claude Code, dashboard access |

### Combined System

| Metric | Node 1 | Node 2 | VAULT | Total |
|--------|--------|--------|-------|-------|
| GPUs | 6 | 1 | 1 (Arc) | 8 |
| VRAM | 100 GB | 32 GB | 6 GB | 138 GB |
| System RAM | 224 GB | 192 GB | 128 GB | 544 GB |
| CPU Cores | 56C/112T | 24C/48T | 16C/32T | 96C/192T |

---

## Why Hybrid Beats All-Local

### The Speed Gap

| Model | Local Speed | Cloud API Speed | Multiplier |
|-------|------------|-----------------|------------|
| Kimi K2.5 (1,040B) | 5-8 tok/s (Titan mode, all GPUs) | 50-80 tok/s | **10x** |
| Qwen3-Coder-480B | 12-18 tok/s (Beast mode) | 60-100 tok/s | **5-6x** |
| DeepSeek V3.1 (671B) | 8-12 tok/s (Beast mode) | 50-80 tok/s | **5-7x** |
| Claude Opus 4.6 | N/A (closed model) | 30-50 tok/s | **∞** |

### The Opportunity Cost

Running a frontier model locally in Beast/Titan mode consumes ALL GPUs on Node 1 (and possibly Node 2). While running Kimi K2.5 locally at 5 tok/s, you lose:
- Fast uncensored chat (50-70 tok/s Llama 70B on TP=4)
- Secondary model serving (80-100 tok/s on 4090)
- RAG embeddings (3060)
- Image generation (if Titan mode takes 5090)
- Video generation (same)

The hybrid approach: cloud handles coding at 10x the speed, and ALL local GPUs serve workloads that actually need to be local.

### What Requires Local

| Workload | Why It Must Be Local |
|----------|---------------------|
| Uncensored chat | Cloud censors — VISION.md non-negotiable #1 |
| EoBQ game AI | Adult content, responsive, personalized, always-on |
| Image generation (ComfyUI) | No API latency/cost, LoRA fine-tuning, uncensored |
| Video generation (Wan2.1) | Same — local models, no API cost per generation |
| LoRA training | Requires GPU compute, can't do on cloud |
| Adult content curation (Stash ML) | Private by nature — can't send to cloud |
| Knowledge agent (RAG) | Private data — 1,173+ bookmarks, personal docs |
| Always-on agents | 24/7 operation, no API rate limits or costs |
| Home automation AI | Local network, real-time, no cloud dependency |
| Media agent | Interacts with local services (Sonarr, Radarr, Plex) |

### What Works Better on Cloud

| Workload | Why Cloud Wins |
|----------|---------------|
| Frontier coding (480B+) | 5-10x faster, no VRAM ceiling, latest models instantly |
| Large-context reasoning (200K+) | Cloud models handle 200K+ context natively |
| Agentic coding (Claude Code, Kimi Code) | Tool use, multi-file editing, already in workflow |
| One-off complex tasks | Pay-per-use, no GPU allocation needed |

### Cost Analysis

| Cloud Option | Monthly Cost | Capability |
|-------------|-------------|------------|
| Claude Pro | $20 | Sonnet 4.5 with generous limits |
| Claude Max | $200 | Opus 4.6, highest limits |
| Kimi Code subscription | ~$10-20 | Kimi K2.5 via API |
| OpenRouter (pay-per-token) | $50-200 | Any frontier model on demand |
| **Total (heavy use)** | **$100-300/month** | All frontier coding you want |

Compare to PRO 6000 Max-Q: **$8,000 one-time**. That's 27-80 months (2-7 years) of cloud API costs. And cloud models improve continuously while hardware depreciates.

The Max-Q makes sense later when:
1. Local model quality/size catches up to where 96 GB runs them well
2. MIG mode is needed for EoBQ production (4 independent game AIs)
3. Fine-tuning large models requires the VRAM
4. Cloud API costs increase significantly

Sources:
- [Claude Pricing](https://www.anthropic.com/pricing)
- [OpenRouter Pricing](https://openrouter.ai/docs/models)
- [Kimi K2.5 API](https://platform.moonshot.ai/pricing)

---

## Complete Workload Map

### Always-On Services (CPU, no GPU contention)

These run 24/7 regardless of mode. All on VAULT or Node CPUs.

| Service | Runs On | Status |
|---------|---------|--------|
| Athanor Dashboard (Next.js) | Node 2 | Running |
| Prometheus + Grafana | VAULT | Running |
| Home Assistant | VAULT | Deployed, pending onboarding |
| Plex + Tautulli | VAULT (Arc A380 transcode) | Deployed, pending claim |
| Sonarr + Radarr + Prowlarr + SABnzbd | VAULT | Running |
| qBittorrent + Gluetun VPN | VAULT | Pending NordVPN creds |
| Stash (adult content management) | VAULT | Running |
| LangGraph agent framework | Node 1 (CPU) | Running |

### AI Agents (Call LLM APIs, Don't Need Own GPU)

| Agent | LLM Endpoint | Tools | Status |
|-------|-------------|-------|--------|
| General assistant | Node 1 vLLM (uncensored) | Service health, GPU metrics, storage | Built |
| Media agent | Node 1 vLLM | Sonarr, Radarr, Tautulli APIs | Built |
| Home agent | Node 1 vLLM | Home Assistant API | Not yet built |
| Creative agent | Node 1 vLLM + ComfyUI | Image gen triggers, prompt engineering | Not yet built |
| Knowledge agent | Node 1 vLLM + embeddings | Vector DB, bookmark index, doc retrieval | Not yet built |
| Adult content curator | Node 1 vLLM + Stash | Stash API, scene detection, tagging | Not yet built |
| Research agent | Node 1 vLLM or cloud | Web search, summarization | Not yet built |

Key insight: agents are orchestration layers. They call LLM APIs and tool APIs. They don't consume GPU — the models they call do. Any agent can be pointed at local or cloud endpoints depending on the task.

### GPU Workloads

#### Node 1 — Always Loaded (Daily Driver)

| GPU(s) | Framework | Model | Purpose | Speed |
|--------|-----------|-------|---------|-------|
| 4× 5070 Ti (TP=4, 64 GB) | vLLM | Llama 3.3 70B Q4 (~40 GB) | Primary uncensored chat/reasoning | ~50-70 tok/s |
| RTX 4090 (24 GB) | vLLM | Qwen3-14B-AWQ (~9 GB) | Fast secondary chat, tool calling | ~80-100 tok/s |
| RTX 3060 (12 GB) | vLLM or sentence-transformers | e5-large (1.3 GB) or Phi-4 Mini (3.8B) | RAG embeddings or tiny utility model | Real-time |

Three concurrent LLM endpoints. Open WebUI routes by model name. Agents call whichever endpoint fits their task.

The 70B model on TP=4 is the workhorse — uncensored, fast, handles complex reasoning. It does what cloud can't: answer anything without filters.

#### Node 2 — Creative Pipeline

| GPU | Framework | Model/Tool | Purpose | Notes |
|-----|-----------|-----------|---------|-------|
| RTX 5090 (32 GB) | ComfyUI | Flux FP8 (~12 GB) | Image generation | SDXL, Flux, LoRA, uncensored |
| RTX 5090 (32 GB) | ComfyUI | Wan2.1-T2V-14B (~28 GB) | Video generation | Sequential with image gen |
| RTX 5090 (32 GB) | vLLM (when idle) | Qwen3-14B or Mistral 7B | Secondary LLM during creative downtime | Shares VRAM with ComfyUI |

The 5090 is the creative powerhouse. 32 GB VRAM handles even large diffusion pipelines. Wan2.1-14B for text-to-video fits alongside basic workflows. When not generating, it can serve a secondary LLM.

#### VAULT — Media Transcoding

| GPU | Purpose |
|-----|---------|
| Arc A380 (6 GB) | Plex hardware transcoding (2-3 simultaneous streams) |

---

## Operating Modes

The system has modes that switch by starting/stopping Docker containers. No hardware changes needed.

### Mode 1: "Daily Driver" (Default)

The always-on configuration. All workloads run concurrently.

**Node 1:**
- vLLM #1: 4× 5070 Ti TP=4 → Llama 70B Q4 (primary uncensored)
- vLLM #2: RTX 4090 → Qwen3-14B-AWQ (fast secondary)
- vLLM #3: RTX 3060 → embedding model (RAG)

**Node 2:**
- ComfyUI: RTX 5090 → Flux FP8 + Wan2.1 (image/video gen)

**Cloud:**
- Claude Code / Kimi Code → frontier coding tasks
- OpenRouter → on-demand access to any frontier model

**Concurrent capabilities:**
- Uncensored chat at 50-70 tok/s (Llama 70B)
- Fast chat at 80-100 tok/s (Qwen3-14B)
- RAG/knowledge queries (embeddings on 3060)
- Image generation (Flux on 5090)
- Video generation (Wan2.1 on 5090, sequential with image)
- All agents running (media, home, creative, knowledge)
- Frontier coding via cloud (50-100+ tok/s)
- Plex streaming (VAULT Arc A380)
- Home automation (VAULT CPU)

**This is 5+ GPU workloads + cloud coding simultaneously.** Nothing competes, nothing waits.

### Mode 2: "Beast Mode" (Node 1 Frontier Model)

For when you want to run a large local model — uncensored reasoning, private data processing, or just because you can.

Stop the three vLLM instances on Node 1. Start llama.cpp with all 6 GPUs pooled (100 GB VRAM + 224 GB RAM = 324 GB).

| Model | Quant | Size | In VRAM | RAM Overflow | Speed |
|-------|-------|------|---------|-------------|-------|
| Qwen3-235B-A22B | Q4_K_M | 143 GB | 100 GB | 43 GB | 20-30 tok/s |
| Qwen3-Coder-480B | FP4 | 240 GB | 100 GB | 140 GB | 12-18 tok/s |
| DeepSeek V3.1 | Q2_K | 245 GB | 100 GB | 145 GB | 8-12 tok/s |
| GLM-4.7 | Q4_K_M | 214 GB | 100 GB | 114 GB | 15-22 tok/s |
| GLM-5 | Q2_K | 241 GB | 100 GB | 141 GB | 8-12 tok/s |

Node 2 continues normally — image/video gen on 5090 unaffected.

Use case: "I need an uncensored 235B model to process sensitive documents" or "I want to evaluate GLM-5 locally before paying for API access."

### Mode 3: "EoBQ Production" (Game AI Pipeline)

Optimized for Empire of Broken Queens development and testing.

**Node 1:**
| GPU(s) | Role | Model |
|--------|------|-------|
| 4× 5070 Ti (TP=4) | Director AI / large reasoning | Llama 70B Q4 — orchestrates game logic |
| RTX 4090 | Player-facing dialogue | Fine-tuned 14B character model — real-time responses |
| RTX 3060 | Lore retrieval | Embedding model — game knowledge base RAG |

**Node 2:**
| GPU | Role | Tool |
|-----|------|------|
| RTX 5090 | Visual pipeline | ComfyUI — character portraits, scenes, expressions, Wan2.1 cinematics |

**What this enables:**
- Director AI on 70B manages game state, branching narratives, consequence tracking
- Character dialogue model responds in real-time to player input
- Lore retrieval keeps world-building consistent via RAG
- Visual pipeline generates character art, scene backgrounds, emotional expressions, and short cinematic video clips
- All uncensored — adult content is central to EoBQ
- Cloud handles none of this — it all MUST be local

### Mode 4: "Titan Mode" (All GPUs Pooled, Cross-Node)

Everything contributes to one model. Requires InfiniBand between nodes.

| Resource | Node 1 | Node 2 | Total |
|----------|--------|--------|-------|
| VRAM | 100 GB | 32 GB | **132 GB** |
| RAM | 224 GB | 192 GB | **416 GB** |
| Addressable | 324 GB | 224 GB | **548 GB** |

Distribution via llama.cpp (heterogeneous GPU support) or exo (multi-node):

| Model | Quant | Size | In VRAM (132 GB) | RAM Overflow | Fits? | Speed |
|-------|-------|------|-------------------|-------------|-------|-------|
| Qwen3-Coder-480B | FP4 | 240 GB | 132 GB (55%) | 108 GB | **Yes** | ~15-22 tok/s |
| Qwen3-Coder-480B | Q4_K_M | 290 GB | 132 GB (46%) | 158 GB | **Yes** | ~12-18 tok/s |
| DeepSeek V3.1 | FP4 | 336 GB | 132 GB (39%) | 204 GB | **Yes** | ~10-15 tok/s |
| GLM-5 | FP4 | 372 GB | 132 GB (35%) | 240 GB | **Yes** | ~8-12 tok/s |
| DeepSeek V3.1 | Q4_K_M | 404 GB | 132 GB (33%) | 272 GB | **Yes** | ~8-12 tok/s |
| GLM-5 | Q4_K_M | 473 GB | 132 GB (28%) | 341 GB | **Yes** | ~6-10 tok/s |
| Kimi K2.5 | Q2_K | 381 GB | 132 GB (35%) | 249 GB | **Yes** | ~7-10 tok/s |
| Kimi K2.5 | INT4 | 595 GB | 132 GB (22%) | 463 GB | **No** (548 < 595) | — |

**Largest model that fits comfortably: GLM-5 at Q4_K_M (473 GB)** — 132 GB in VRAM, 341 GB in RAM, 75 GB headroom for KV cache.

**Largest model at any quality: Kimi K2.5 at Q2_K (381 GB)** — fits with 167 GB headroom. 1.04 trillion parameters running locally. Slow (~7-10 tok/s), reduced quality at Q2, but it runs.

**Best speed/quality: Qwen3-Coder-480B at FP4 (240 GB)** — 55% in VRAM, MoE offloading handles the rest. 15-22 tok/s. Genuinely usable for coding.

Note: Titan mode without the Max-Q gives 132 GB VRAM instead of 228 GB. Kimi K2.5 at INT4 (595 GB) no longer fits. The Max-Q upgrade recovers this capability.

**Everything else stops in Titan mode.** No image gen, no fast chat, no agents. This is the "throw the entire system at one problem" mode.

### Mode 5: "Training Mode" (LoRA Fine-Tuning)

Overnight or dedicated sessions for model customization.

| GPU | Task | Notes |
|-----|------|-------|
| RTX 5090 (32 GB) | LoRA training (Flux, SDXL) | Largest batch sizes, fastest training |
| RTX 4090 (24 GB) | LoRA training (LLM fine-tuning) | QLoRA on 14B-70B models |
| 4× 5070 Ti | Continue serving vLLM | Chat stays available during training |
| RTX 3060 | Embeddings | Knowledge agent indexing |

Training and inference can coexist: training happens on 5090/4090, serving continues on 5070 Ti cluster.

---

## Power Analysis

### Node 1 (6 GPUs, Mining Enclosure)

| Component | TDP | Undervolted Inference (~55%) |
|-----------|-----|------------------------------|
| 4× RTX 5070 Ti | 1,200W | 550W |
| RTX 4090 | 450W | 200W |
| RTX 3060 | 170W | 80W |
| System (EPYC + RAM + NVMe) | 200W | 200W |
| **Total** | **2,020W** | **~1,030W** |

All GPUs undervolted via `nvidia-smi -pl`:
- 5070 Ti: 250W (from 300W) — <3% throughput loss
- 4090: 350W (from 450W) — <5% throughput loss
- 3060: 140W (from 170W) — <3% throughput loss

PSU: Dual PSU setup. 1,200W ATX primary + 750-1,000W SFX secondary. Or single 1,600W+ mining/server PSU. Mining PSUs (HP server pulls, 2,400W) cost $50-80 and are purpose-built for multi-GPU rigs.

### Node 2 (1 GPU, Standard Case)

| Component | TDP | Inference |
|-----------|-----|-----------|
| RTX 5090 | 575W | ~300W |
| System (TR 7960X + RAM) | 150W | 150W |
| **Total** | **725W** | **~450W** |

Single 750-850W ATX PSU. No dual PSU needed.

### Combined System

| | TDP | Inference Draw |
|--|-----|----------------|
| Node 1 | 2,020W | ~1,030W |
| Node 2 | 725W | ~450W |
| VAULT | ~300W | ~250W |
| **Total** | **3,045W** | **~1,730W** |

Two of three rack circuits handle this easily (20A circuit = 2,400W max continuous per NEC 80% rule).

---

## InfiniBand: Cheap Future-Proofing

| Item | Cost (used eBay) |
|------|-----------------|
| 2× Mellanox ConnectX-3 FDR (56 Gbps) | ~$30 each |
| 1× QSFP+ FDR cable (1-2m) | ~$15 |
| **Total** | **~$75** |

Already on the purchase list (BUILD-ROADMAP Phase 8). Provides:
- 56 Gbps (7 GB/s) point-to-point — 5.6x faster than 5GbE
- RDMA for zero-copy cross-node transfers
- Enables Mode 4 (Titan) for cross-node model distribution
- Future-proofs for distributed inference as models grow

Not required for Daily Driver mode. Install opportunistically.

---

## Cloud Coding Strategy

### Tools Already in Workflow

| Tool | Model | Use Case |
|------|-------|----------|
| Claude Code (CLI) | Opus 4.6 / Sonnet 4.5 | Primary coding assistant, Athanor development |
| Kimi Code | Kimi K2.5 | Secondary coding, alternative perspective |
| Open WebUI → cloud APIs | Any via OpenRouter | On-demand access to any frontier model |

### Cost Projection

| Subscription | Monthly | Capability |
|-------------|---------|------------|
| Claude Pro/Max | $20-200 | Opus 4.6 for coding, Sonnet 4.5 for speed |
| Kimi Code | ~$10-20 | Kimi K2.5 coding tasks |
| OpenRouter (pay-per-token) | $0-100 | On-demand GLM-5, DeepSeek V3.1, etc. |
| **Total** | **$50-300/month** | All frontier coding you need |

### vs. Local Frontier Inference

| Approach | Speed | Cost | Availability |
|----------|-------|------|-------------|
| Cloud API (Kimi K2.5) | 50-80 tok/s | ~$50-200/month | Rate limited, needs internet |
| Local Beast Mode (Qwen3-480B) | 12-18 tok/s | $0 ongoing (hardware amortized) | Always available, takes all GPUs |
| Local Titan Mode (GLM-5 Q4) | 6-10 tok/s | $0 ongoing | Everything else stops |

Cloud wins on speed. Local wins on sovereignty and zero marginal cost. The hybrid uses both: cloud for speed-sensitive coding, local for everything else + occasional Beast/Titan mode when needed.

---

## System Quality Assessment

| Capability | Rating | Notes |
|------------|--------|-------|
| **Uncensored chat (70B)** | **Excellent** | 50-70 tok/s on TP=4, always available, the core value prop |
| **Frontier coding** | **Excellent** (cloud) | 50-100+ tok/s via Claude/Kimi/OpenRouter |
| **Fast secondary chat** | **Excellent** | 80-100 tok/s on 4090, tool calling enabled |
| **Image generation** | **Top tier** | 5090 32 GB, Flux + SDXL + LoRA training |
| **Video generation** | **Strong** | Wan2.1-14B on 5090, 480p/5s clips |
| **EoBQ game AI** | **Strong** | 70B director + 14B dialogue + embeddings + visuals |
| **RAG / knowledge** | **Good** | Dedicated 3060 for embeddings, always available |
| **Concurrent workloads** | **Excellent** | 4+ GPU workloads simultaneously in Daily Driver |
| **Agent infrastructure** | **Strong** | LangGraph running, 2 agents built, extensible |
| **Media/home automation** | **Solid** | VAULT handles everything independently |
| **Local frontier models** | **Functional** | Beast mode: 12-18 tok/s for 480B. Titan: 7-10 tok/s for 1T |
| **LoRA training** | **Good** | 5090 or 4090, coexists with vLLM serving |

### What's Missing Without the Max-Q

| Capability | With Max-Q | Without |
|-----------|-----------|---------|
| 96 GB single-GPU model (70B FP8, 235B Q2) | PRO 6000 serves natively | Must use TP=4 or offloading |
| MIG mode (4× independent game AIs) | 4× 24 GB instances | Not available — use separate GPUs |
| Titan mode Kimi K2.5 INT4 (595 GB) | Fits (228 + 416 = 644 GB) | Doesn't fit (132 + 416 = 548 GB) |
| Concurrent large + creative | PRO 6000 LLM + 5090 creative | Must choose: 5090 does LLM OR creative |

The Max-Q is a powerful upgrade, but the system is fully functional without it. The cloud hybrid strategy eliminates the most acute gap (frontier coding speed).

---

## Recommendation

**Build and operate the system in Daily Driver mode without the Max-Q.** Use cloud APIs for frontier coding. The local system handles uncensored inference, creative pipelines, game AI, agents, media, and home automation — all concurrently, all at good speed.

The PRO 6000 Max-Q becomes a strategic upgrade when:
1. EoBQ enters production and needs MIG for parallel game AIs
2. A specific local-only model requires 96 GB single-GPU VRAM
3. Cloud API costs become prohibitive
4. Desire to run Kimi K2.5 at INT4 locally (Titan mode, 644 GB)

Until then, the $8,000 is better left unspent. The hardware you have, combined with cloud coding, covers every workload in VISION.md.

---

## Open Questions

1. **TRX50↔X870E swap timing**: Required for Node 2 to get Gen5 slots for 5090. Physical task — schedule with next rack session.
2. **Node 2 RAM**: After swap, verify 128 GB VAULT RAM + 64 GB loose kit = 192 GB is compatible in TRX50 (speed/timing match). If not, 128 GB alone is still functional.
3. **Mining enclosure selection**: Need to verify SSI EEB (12"×13") ROMED8-2T fits. Most frames support ATX/E-ATX with adjustable standoffs.
4. **Dual PSU adapter**: Add2PSU (~$15) or similar for syncing power-on signals between primary and secondary PSUs.
5. ~~**EPYC 7402P vs 7663**~~: Confirmed EPYC 7663 (56C/112T). Significant headroom for MoE expert routing, concurrent vLLM instances, and agent framework.
6. **5070 Ti discontinuation**: ASUS confirmed discontinuation. Buy spares before stock dries up if TP=4+ expansion is ever desired.

---

## Key Takeaways

1. **Cloud coding + local everything else is the right architecture.** It plays to each platform's strengths.
2. **The system serves 20+ workloads** with current hardware. No capability gap requires immediate spending.
3. **Modes give flexibility** without hardware changes. Daily Driver for concurrent serving, Beast for local frontier, Titan for maximum model size, EoBQ for game production.
4. **The Max-Q is a future upgrade, not a current need.** Cloud APIs cover frontier coding at 10x local speed for $50-300/month.
5. **InfiniBand at $75 is obvious.** Install it. Even if rarely used, it enables Titan mode when needed.
6. **Uncensored local inference is the irreplaceable capability.** It justifies the entire local investment. Cloud can't do it. That's the system's core value.
