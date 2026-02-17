# Athanor Model Stack: Complete Synthesis

**Date:** 2026-02-16
**Status:** Complete — master reference
**Synthesizes:** 8 research documents (uncensored LLMs, image gen, video gen, embeddings/RAG, tool-calling/coding, frontier coding, hybrid architecture, TP GPU compatibility)

---

## The Architecture in One Sentence

Cloud handles frontier coding at 50-100+ tok/s. Local handles everything uncensored, private, creative, and always-on — 6+ concurrent GPU workloads across 7 GPUs and 132 GB VRAM.

---

## Hardware Summary (Post-Move)

| Node | Role | GPUs | VRAM | RAM | CPU |
|------|------|------|------|-----|-----|
| **Node 1** | Foundry | 4x RTX 5070 Ti + RTX 4090 + RTX 3060 | 100 GB | 224 GB DDR4 ECC | EPYC 7663 56C/112T |
| **Node 2** | Workshop | RTX 5090 | 32 GB | 192 GB DDR5 | TR 7960X 24C/48T |
| **VAULT** | Storage | Arc A380 | 6 GB | 128 GB DDR5 | Ryzen 9950X 16C/32T |
| **Combined** | — | 7 NVIDIA + 1 Intel | 138 GB | 544 GB | 96C/192T |

### TP Compatibility (Critical Rule)

Only **identical GPU models** can tensor-parallel in vLLM. No mixing architectures, VRAM, or core counts.

| TP Group | Cards | Combined VRAM | Use |
|----------|-------|---------------|-----|
| 4x RTX 5070 Ti | Slot 2-5 on Node 1 | 64 GB | 70B-class models |
| RTX 4090 (standalone) | Slot 1 on Node 1 | 24 GB | Fast secondary |
| RTX 3060 (standalone) | Slot 6 on Node 1 | 12 GB | Embeddings/utility |
| RTX 5090 (standalone) | Node 2 | 32 GB | Creative pipeline + LLM |

Source: `2026-02-16-vllm-tp-gpu-compatibility.md`

---

## Complete Model Stack

### LLM Inference

| Use Case | Model | Quant | GPU(s) | VRAM Used | Speed | License |
|----------|-------|-------|--------|-----------|-------|---------|
| **Primary uncensored chat** | Llama 3.3 70B Abliterated | Q4_K_M | 4x 5070 Ti TP=4 | ~42 GB | ~25-35 tok/s | Llama Community |
| **Co-primary reasoning** | Qwen3-32B Abliterated | FP16 | 4x 5070 Ti TP=4 | ~64 GB | ~40-50 tok/s | Apache 2.0 |
| **Fast secondary / agent** | Qwen3-14B Abliterated | Q8_0 | RTX 4090 | ~16 GB | ~50-60 tok/s | Apache 2.0 |
| **Creative writing (EoBQ)** | Qwen3-32B Abliterated | Q6_K | RTX 5090 | ~27 GB | ~30-40 tok/s | Apache 2.0 |
| **Utility / lightweight** | Qwen3-8B Abliterated | Q4_K_M | RTX 3060 | ~5 GB | ~40-60 tok/s | Apache 2.0 |
| **Beast mode (local frontier)** | Qwen3-235B-A22B | Q4_K_M | All Node 1 + RAM | 100 GB VRAM + 43 GB RAM | ~20-30 tok/s | Apache 2.0 |

Source: `2026-02-16-uncensored-llm-models.md`, `2026-02-16-hybrid-system-architecture.md`

### Tool Calling & Coding (Local)

| Use Case | Model | Quant | GPU(s) | VRAM | Speed | Key Metric |
|----------|-------|-------|--------|------|-------|------------|
| **Agent backbone** | Qwen3-32B | FP8 | RTX 5090 | ~32 GB | ~35-45 tok/s | BFCL 68.2 |
| **Fast coding** | Qwen3-Coder-30B-A3B | Q4 | RTX 4090 | ~19 GB | ~73 tok/s | SWE-bench 50.3% |
| **Complex agentic (stretch)** | Qwen3-Coder-Next 80B/3B | Q4 | 4x 5070 Ti TP=4 | ~46 GB | ~30-40 tok/s | SWE-bench 70.6% |
| **Beast mode coding** | GLM-4.7 355B/32B | Q4 + offload | All Node 1 + RAM | 100 GB + 114 GB | ~15-22 tok/s | SWE-bench 74.2% |

Source: `2026-02-16-tool-calling-coding-models.md`

### Tool Calling & Coding (Cloud — Primary for Frontier)

| Tool | Model | Speed | Monthly Cost |
|------|-------|-------|-------------|
| **Claude Code** | Opus 4.6 / Sonnet 4.5 | 30-100+ tok/s | $20-200 |
| **Kimi Code** | Kimi K2.5 | 50-80 tok/s | ~$10-20 |
| **OpenRouter** | Any frontier on demand | 50-100+ tok/s | $0-100 |

Source: `2026-02-16-hybrid-system-architecture.md`

### Image Generation (Node 2 — RTX 5090 via ComfyUI)

| Use Case | Model | Params | Precision | VRAM | Speed (1024²) |
|----------|-------|--------|-----------|------|---------------|
| **Primary generation** | FLUX.1 [dev] | 12B | FP8 | ~16 GB | ~6s (5090) |
| **Speed / iteration** | Z-Image-Turbo | 6B | FP8 | ~8 GB | ~1.5s (5090) |
| **NSFW specialization** | Pony V6 XL | 3.5B | FP16 | ~12 GB | ~3s (5090) |
| **Editing / inpainting** | FLUX.1 Kontext [dev] | 12B | FP8 | ~12 GB | ~6-12s |
| **Future ceiling** | FLUX.2 [dev] | 32B | Q4 GGUF | ~18-20 GB | ~6s (5090) |

**NSFW Ecosystem Depth:** Pony V6 > Z-Image-Turbo (factory uncensored) > FLUX.1 [dev] (LoRA) > Pony V7 (growing)

**LoRA Training:** FLUX.1 via AI-Toolkit (12 GB min), Pony V6 via Kohya (8 GB min). Both fit on RTX 5090 or 4090.

Source: `2026-02-16-image-generation-models.md`

### Video Generation (Node 2 — RTX 5090 via ComfyUI)

| Use Case | Model | Params | Precision | VRAM | Speed (5s clip) |
|----------|-------|--------|-----------|------|-----------------|
| **Primary video gen** | Wan2.2-T2V-A14B | 27B/14B active (MoE) | FP8 | ~16 GB | ~2.5 min (5090) |
| **Rapid prototyping** | Wan2.1-T2V-1.3B | 1.3B | FP16 | ~8 GB | ~2 min (5090) |
| **Audio + video** | LTX-2 | 19B | FP8 | ~20 GB | ~3-5 min (5090) |
| **NSFW animation bridge** | AnimateDiff + Pony V6 | ~3.5B + motion | FP16 | ~12 GB | Short clips |

**Pipeline:** Generate still (FLUX.1) → Animate (Wan2.2 I2V) → Edit frames (Kontext) → Add audio (LTX-2)

Source: `2026-02-16-video-generation-models.md`

### Embeddings & RAG (Node 1 — RTX 3060)

| Component | Model | Params | VRAM | Key Metric |
|-----------|-------|--------|------|------------|
| **Embedding** | Qwen3-Embedding-0.6B | 0.6B | ~1.5 GB | MTEB 70.70 |
| **Reranker** | Qwen3-Reranker-0.6B | 0.6B | ~1.5 GB | MTEB-R 65.80 |
| **Vector DB** | Qdrant | — | 1 GB RAM | Native hybrid search |
| **Total GPU** | — | — | **~3 GB** | Leaves ~9 GB for utility LLM |

**RAG Pipeline:** Query → Qwen3-Embedding → Qdrant (dense + sparse search) → Qwen3-Reranker (top-20 → top-5) → LLM generation

Source: `2026-02-16-embedding-rag-models.md`

---

## GPU Allocation Map (Daily Driver Mode)

```
NODE 1 — Foundry (100 GB VRAM, 224 GB RAM)
┌─────────────────────────────────────────────────────────┐
│ Slot 1 │ RTX 4090 (24 GB)  │ vLLM: Qwen3-14B Q8 (16 GB) │
│ Slot 2 │ RTX 5070 Ti (16 GB)│                             │
│ Slot 3 │ RTX 5070 Ti (16 GB)│ vLLM TP=4: Llama 70B Q4     │
│ Slot 4 │ RTX 5070 Ti (16 GB)│      (42 GB across 4 GPUs)  │
│ Slot 5 │ RTX 5070 Ti (16 GB)│                             │
│ Slot 6 │ RTX 3060 (12 GB)  │ Embeddings (3 GB) + Utility │
└─────────────────────────────────────────────────────────┘

NODE 2 — Workshop (32 GB VRAM, 192 GB RAM)
┌─────────────────────────────────────────────────────────┐
│ Slot 1 │ RTX 5090 (32 GB)  │ ComfyUI: FLUX.1 / Wan2.2   │
│         │                   │ (or vLLM when idle)         │
└─────────────────────────────────────────────────────────┘

VAULT — Storage
┌─────────────────────────────────────────────────────────┐
│ Arc A380 (6 GB) │ Plex HW transcoding                   │
│ Qdrant (Docker)  │ Vector DB — ~1 GB RAM                 │
└─────────────────────────────────────────────────────────┘
```

### Concurrent in Daily Driver Mode
- Uncensored chat at ~25-35 tok/s (Llama 70B, TP=4)
- Fast agent/secondary at ~50-60 tok/s (Qwen3-14B, 4090)
- RAG queries (embeddings on 3060)
- Image generation (FLUX.1/Z-Image on 5090)
- Video generation (Wan2.2 on 5090, sequential with image)
- Frontier coding via cloud (50-100+ tok/s)
- All agents running (media, home, creative, knowledge)
- Plex streaming (VAULT Arc A380)

---

## Operating Modes (Switch via Docker Containers)

### Mode 1: Daily Driver (Default)
As above. 5+ GPU workloads + cloud coding simultaneously.

### Mode 2: Beast Mode (Node 1 — All 6 GPUs Pooled)
Stop vLLM instances. Start llama.cpp/KTransformers with 100 GB VRAM + 224 GB RAM = 324 GB.

| Model | Quant | Total Size | Speed |
|-------|-------|-----------|-------|
| Qwen3-235B-A22B | Q4_K_M | 143 GB | ~20-30 tok/s |
| GLM-4.7 | Q4_K_M | 214 GB | ~15-22 tok/s |
| DeepSeek V3.1 | Q2_K | 245 GB | ~8-12 tok/s |

Node 2 creative pipeline unaffected.

### Mode 3: EoBQ Production
- 4x 5070 Ti TP=4 → 70B Director AI (game logic, narrative orchestration)
- RTX 4090 → 14B Character Dialogue (real-time player-facing)
- RTX 3060 → Embeddings (lore retrieval RAG)
- RTX 5090 → ComfyUI (character art, scenes, Wan2.2 cinematics)

### Mode 4: Titan Mode (Cross-Node, Requires InfiniBand)
All 7 NVIDIA GPUs: 132 GB VRAM + 416 GB RAM = 548 GB addressable.

| Model | Quant | Size | Speed |
|-------|-------|------|-------|
| Qwen3-Coder-480B | FP4 | 240 GB | ~15-22 tok/s |
| GLM-5 | Q4_K_M | 473 GB | ~6-10 tok/s |
| Kimi K2.5 | Q2_K | 381 GB | ~7-10 tok/s |

Everything else stops. This is "throw the entire system at one problem" mode.

### Mode 5: Training Mode
- RTX 5090 → LoRA training (FLUX, SDXL, video models)
- RTX 4090 → QLoRA fine-tuning (LLMs up to 70B)
- 4x 5070 Ti → Continue serving vLLM (chat stays online)
- RTX 3060 → Embeddings (knowledge indexing)

---

## Why Qwen3 Dominates the Local Stack

The Qwen3 family holds 7 of 10 primary model slots:

| Slot | Model | Why Qwen3 |
|------|-------|-----------|
| Co-primary chat | Qwen3-32B Abliterated | Matches 72B quality at 32B size |
| Fast agent | Qwen3-14B Abliterated | Best 14B tool calling (Tau2-Bench 65.1) |
| Creative writing | Qwen3-32B Abliterated | Thinking/non-thinking toggle |
| Utility | Qwen3-8B Abliterated | Best 8B-class all-rounder |
| Agent backbone | Qwen3-32B | Best BFCL (68.2) at this size |
| Embedding | Qwen3-Embedding-0.6B | MTEB 70.70 at 1.5 GB |
| Reranker | Qwen3-Reranker-0.6B | MTEB-R 65.80, same ecosystem |

**Common factors:** Apache 2.0 license, clean abliteration, thinking/non-thinking toggle, strong tool calling, size-efficient, massive GGUF/AWQ/GPTQ ecosystem.

The non-Qwen3 picks exist because they genuinely outperform in their niche:
- **Llama 3.3 70B** — Best-understood 70B, proven community, strongest at pure reasoning scale
- **FLUX.1 [dev]** — Largest image gen ecosystem, best balance of quality/speed/LoRA maturity
- **Wan2.2** — Dominant open-weight video gen, most mature NSFW video ecosystem

---

## The Hybrid Gap Analysis

### What Cloud Does Better
| Capability | Cloud | Local | Gap |
|------------|-------|-------|-----|
| Frontier coding (Opus 4.6) | 30-50 tok/s | N/A (closed) | ∞ |
| 480B+ coding models | 50-100 tok/s | 12-18 tok/s (Beast) | 4-6x |
| 200K+ context reasoning | Native | KV cache limited | Significant |

### What Local Does That Cloud Can't
| Capability | Why Local Only |
|------------|---------------|
| Uncensored chat | Cloud censors — non-negotiable |
| NSFW image/video generation | No cloud API allows this |
| EoBQ game AI | Adult content, real-time, always-on |
| Private data RAG | Can't send to cloud |
| LoRA fine-tuning | Requires GPU compute |
| Adult content curation | Private by nature |
| Always-on agents | 24/7, no API costs |

### Monthly Cloud Cost: $50-300
vs. PRO 6000 Max-Q at $8,000 = 27-80 months of cloud API. The Max-Q is a future upgrade when EoBQ needs MIG or a specific model needs 96 GB single-GPU.

---

## Deployment Commands (Daily Driver)

```bash
# Node 1: Primary uncensored (4x 5070 Ti TP=4)
vllm serve huihui-ai/Llama-3.3-70B-Instruct-abliterated \
  --port 8001 --tensor-parallel-size 4 \
  --quantization awq --max-model-len 8192 \
  --gpu-memory-utilization 0.90

# Node 1: Fast secondary (RTX 4090)
vllm serve huihui-ai/Qwen3-14B-abliterated \
  --port 8002 --dtype auto --quantization awq \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --max-model-len 32768

# Node 1: Embeddings (RTX 3060)
# Use sentence-transformers or vLLM embedding mode
python -m sentence_transformers.server \
  --model Qwen/Qwen3-Embedding-0.6B --port 8003

# Node 2: ComfyUI (RTX 5090) — no vLLM command, GUI-driven
# Load FLUX.1 [dev] FP8, Z-Image-Turbo FP8, Wan2.2 FP8 as needed

# VAULT: Qdrant
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v /mnt/user/appdata/qdrant:/qdrant/storage \
  qdrant/qdrant
```

---

## VRAM Budget Summary

| GPU | Total VRAM | Primary Model | VRAM Used | Headroom |
|-----|-----------|---------------|-----------|----------|
| 4x 5070 Ti (TP=4) | 64 GB | Llama 70B Q4 | ~42 GB | 22 GB (KV cache) |
| RTX 4090 | 24 GB | Qwen3-14B Q8 | ~16 GB | 8 GB |
| RTX 3060 | 12 GB | Embedding + Reranker + Utility | ~5 GB | 7 GB |
| RTX 5090 | 32 GB | FLUX.1 FP8 / Wan2.2 FP8 | ~16-20 GB | 12-16 GB |
| **Total** | **132 GB** | — | **~79-83 GB** | **~49-53 GB** |

~40% headroom across the system for KV cache, batch inference, model swapping, and future additions.

---

## Model Download Sizes (Approximate)

| Model | Format | Download Size |
|-------|--------|--------------|
| Llama 3.3 70B Abliterated | AWQ INT4 | ~35 GB |
| Qwen3-32B Abliterated | Q6_K GGUF | ~25 GB |
| Qwen3-14B Abliterated | AWQ INT4 | ~9 GB |
| Qwen3-8B Abliterated | Q4_K_M GGUF | ~5 GB |
| FLUX.1 [dev] | FP8 safetensors | ~12 GB |
| Z-Image-Turbo | FP8 | ~6 GB |
| Pony V6 XL | FP16 safetensors | ~7 GB |
| FLUX.1 Kontext [dev] | FP8 | ~12 GB |
| Wan2.2-T2V-A14B | FP8 | ~16 GB |
| LTX-2 | FP8 | ~20 GB |
| Qwen3-Embedding-0.6B | FP16 | ~1.2 GB |
| Qwen3-Reranker-0.6B | FP16 | ~1.2 GB |
| Qwen3-Coder-30B-A3B | AWQ INT4 | ~19 GB |
| **Total initial stack** | — | **~170 GB** |

---

## Models to Watch

| Model | Why | When |
|-------|-----|------|
| **Qwen3.5 (397B MoE)** | Native multimodal, next beast-mode king | Announced Feb 2026 |
| **GPT-OSS 120B Abliterated** | Apache 2.0, 5.1B active, when community uncensors | Waiting on abliteration |
| **Dolphin 3.0 on Qwen3-32B** | Dolphin uncensored training + Qwen3 quality | If Eric Hartford builds it |
| **FLUX.2 [dev] quantized benchmarks** | May dethrone FLUX.1 as primary image gen | Needs community testing |
| **Z-Image-Turbo LoRA maturity** | Could replace FLUX.1 if ecosystem grows | 3-6 months |
| **Pony V7 NSFW LoRAs** | V6 ecosystem rebuilding on AuraFlow arch | 3-6 months |
| **Wan2.2 NVFP4** | Further VRAM reduction on Blackwell | Unknown timeline |

---

## Open Questions (Cross-Cutting)

1. **vLLM Blackwell sm_120 support** — Can we run vLLM natively or still need source builds?
2. **NVFP4 quality validation** — Are FP4 checkpoints equivalent to FP8 in practice?
3. **Qwen3-32B vs Llama 70B creative writing** — Which produces better EoBQ prose? Benchmarks don't capture this.
4. **Sparse vector generation for hybrid RAG** — Qwen3-Embedding only produces dense vectors. Need SPLADE/BM42 via Qdrant FastEmbed or BGE-M3 sparse head.
5. **Cross-node InfiniBand validation** — Test RDMA throughput before committing to Titan mode workloads.
6. **Concurrent vLLM + ComfyUI on Node 2** — When 5090 isn't doing image/video gen, can we dynamically load a vLLM instance?
7. **KTransformers multi-GPU** — Does it handle heterogeneous GPU layouts for MoE offloading?

---

## Source Documents

| Document | Scope |
|----------|-------|
| `2026-02-16-uncensored-llm-models.md` | 16 LLMs evaluated, abliteration analysis, VRAM tables |
| `2026-02-16-image-generation-models.md` | 13 image gen models, NSFW ranking, LoRA training strategy |
| `2026-02-16-video-generation-models.md` | 7 video gen models, pipeline integration with image gen |
| `2026-02-16-embedding-rag-models.md` | 9 embedding models, 5 rerankers, 5 vector databases |
| `2026-02-16-tool-calling-coding-models.md` | 12 coding/agent models, vLLM parser support matrix |
| `2026-02-16-frontier-coding-models-local-inference.md` | 6 frontier models, VRAM requirements, offloading speeds |
| `2026-02-16-hybrid-system-architecture.md` | 5 operating modes, GPU allocation, power analysis, cloud strategy |
| `2026-02-16-vllm-tp-gpu-compatibility.md` | Die-level TP analysis for all Athanor GPUs |
