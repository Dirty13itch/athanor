# VRAM Budgets and Workload Profiles

*Real VRAM accounting and concurrent workload scenarios. What the system must handle simultaneously.*

---

## Real VRAM Budget

Raw VRAM ≠ usable for model weights. Each GPU loses capacity to CUDA context, vLLM overhead, and KV cache reserve for concurrent requests.

| GPU | Node | Raw VRAM | CUDA + vLLM Overhead | KV Cache Reserve | Usable for Weights |
|-----|------|----------|---------------------|-----------------|-------------------|
| 3x RTX 5070 Ti (TP=4 group) | Node 1 | 48 GB | ~4 GB | ~12 GB | ~32 GB pooled |
| RTX 4090 (TP=4 group) | Node 1 | 24 GB | ~1.5 GB | ~5 GB | ~17 GB pooled |
| RTX 5070 Ti (GPU 4) | Node 1 | 16 GB | ~1 GB | ~0.5 GB | ~14.5 GB (embedding) |
| RTX 5090 | Node 2 | 32 GB | ~1.5 GB | ~6 GB | ~24 GB |
| RTX 5060 Ti | Node 2 | 16 GB | ~1 GB | ~3 GB | ~12 GB |

**Total usable for weights: ~100 GB across 7 GPUs (5 inference + 1 embedding + 1 creative).**

**KV cache explained:** Each concurrent request consumes KV cache proportional to sequence length × hidden dimension × layers. A 14B model at 32K context consumes ~2 GB KV cache per concurrent request. Reserve allows 2 concurrent requests per GPU without OOM. Higher concurrency = more reserve needed = less weight capacity.

---

## Current GPU Allocation

| GPU | Node | Current Workload | VRAM Used |
|-----|------|-----------------|-----------|
| GPUs 0-3 (3x 5070 Ti + 4090) | Node 1 | vLLM TP=4, Qwen3.5-27B-FP8 | ~15.6 GB each |
| GPU 4 (5070 Ti) | Node 1 | vLLM Embedding, Qwen3-Embedding-0.6B | ~14.6 GB |
| GPU 0 (RTX 5090) | Node 2 | vLLM, Qwen3.5-35B-A3B-AWQ-4bit | ~28 GB |
| GPU 1 (RTX 5060 Ti) | Node 2 | ComfyUI, Flux dev FP8 | ~12 GB (when loaded) |

---

## Workload Scenarios

### Typical Evening (Shaun coding, home running)

```
Node 1:8000 — vLLM TP=4, Qwen3.5-27B-FP8 serving agent requests
Node 1:8001 — Embedding model idle (used on-demand)
Node 2:8000 — vLLM Qwen3.5-35B-A3B-AWQ-4bit for fast interactive chat
Node 2:8188 — ComfyUI idle or running Flux
VAULT — NFS serving, Plex idle, HA running, Media Agent polling

~70 GB VRAM active / 136 GB total. Plenty of headroom.
```

### Peak Load (EoBQ + background agent + home event + Plex stream)

```
Node 1:8000 — vLLM TP=4 running Research Agent background task
Node 1:9000 — Agent server routing requests
Node 2:8000 — RTX 5090 time-sharing: abliterated LLM (EoBQ dialogue) ↔ ComfyUI (scene images)
Node 2:8188 — ComfyUI on 5060 Ti for dedicated diffusion
VAULT — Plex transcoding (Arc A380), NFS, HA processing motion event

~100-110 GB VRAM active. 5090 is the bottleneck (time-sharing LLM + diffusion).
```

### Creative Session (image/video generation batch)

```
Node 2 GPU 0 — 5090 dedicated to ComfyUI (Flux/Wan), LLM unloaded
Node 2 GPU 1 — 5060 Ti also running ComfyUI diffusion
Node 1 — TP=4 available for any agent work
VAULT — normal operations

Creative workloads tolerate higher latency — batch, not interactive.
```

---

## Bottleneck: Node 2 GPU 0 Contention

The RTX 5090 (32 GB) is time-shared between vLLM inference and ComfyUI diffusion. They can't run simultaneously at full capacity.

**Current mitigation:** Docker Compose `deploy.resources.reservations.devices` pins containers to specific GPUs. Model loading from local NVMe takes ~2-5 seconds.

**Future resolution:** If a PRO 6000 (96 GB) is acquired, LLM gets the PRO 6000 permanently, 5090 becomes dedicated creative. No time-sharing, no model swaps, no contention.
