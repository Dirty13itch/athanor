# Node Roles + Hardware Allocation

> Historical note: archived research retained for ADR-004 decision history. Current node identity, hardware inventory, and placement truth lives in the registry-backed reports.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-004 (Node Roles + Hardware Allocation)
**Depends on:** ADR-001 (Base Platform), ADR-002 (Network), ADR-003 (Storage)

---

## The Question

What does each machine in Athanor actually do? Which workloads run where, given the hardware, network, and storage decisions already made?

---

## Hardware Summary (Post ADR-001 through 003)

| Machine | CPU | RAM | GPU | VRAM | Local NVMe | Network | OS |
|---------|-----|-----|-----|------|------------|---------|-----|
| **Node 1** | EPYC 7663 56C/112T | 224 GB DDR4 ECC | 4x RTX 5070 Ti | 64 GB | 16 TB (after expansion) | 5GbE + IB 56G | Ubuntu 24.04 |
| **Node 2** | Ryzen 9 9950X 16C/32T | 128 GB DDR5 | RTX 5090 + RTX 4090 | 56 GB | 4 TB | 5GbE + IB 56G | Ubuntu 24.04 |
| **VAULT** | TR 7960X 24C/48T | 128 GB DDR5 ECC | Arc A380 | 6 GB | 6.5 TB NVMe + 164 TB HDD | 5GbE | Unraid |
| **DEV** | i7-13700K 16C/24T | 64 GB DDR5 | RTX 3060 | 12 GB | 6.25 TB | 1GbE / WiFi | Windows 11 |

---

## Workloads (From VISION.md)

Everything Athanor needs to run, grouped by resource needs:

### GPU-heavy
- LLM inference — large models (70B+) across multiple GPUs
- LLM inference — small/medium models (7B-30B) for fast interactive chat
- ComfyUI — image generation (Flux, SDXL, LoRA)
- Video generation — Wan2.x and emerging models
- Fine-tuning — LoRA/QLoRA on local models
- EoBQ AI integration — real-time inference during gameplay

### CPU/RAM-heavy
- AI agent orchestration — agents making API calls, processing results, managing state
- Background processing — batch inference, scheduled tasks, data pipelines
- Home Assistant — always-on automation engine

### Storage/IO-heavy
- NFS file server — models, media, shared files
- Plex Media Server — streaming + transcoding
- *arr stack — media acquisition and organization
- Stash — adult content management and tagging
- Download clients — SABnzbd, qBittorrent

### User-facing
- Dashboard — unified web UI
- Chat interface — conversational access to the system
- EoBQ game client/server

---

## GPU Allocation Logic

The two compute nodes have complementary GPU configurations, not redundant ones.

### Node 1: 4x Identical GPUs → Tensor Parallelism

Four identical RTX 5070 Ti (16 GB each). Tensor parallelism splits a single model across all 4 GPUs, giving 64 GB effective VRAM for one model. This is how you run 70B Q4 (~40 GB) or 70B Q5/Q6 models comfortably.

EPYC's 56 cores and 224 GB RAM handle:
- KV cache overflow to CPU memory for long-context inference
- Preprocessing (tokenization, batching) for high-throughput serving
- Multiple concurrent inference requests

**Best for:** Large models, high throughput, batch processing, background workloads.

### Node 2: 2x Different GPUs → Independent Specialization

RTX 5090 (32 GB) and RTX 4090 (24 GB) are different architectures (Blackwell vs Ada Lovelace) with different VRAM sizes. Tensor parallelism between them would bottleneck at the slower card with uneven memory splits. They're best used independently:

- **5090 (32 GB):** Single-GPU tasks needing maximum performance. ComfyUI image generation, video generation, or running a large model that fits in 32 GB (e.g., 70B Q3, any 30B model at higher quantization).
- **4090 (24 GB):** Simultaneous second workload. A chat model (7B-13B) running alongside ComfyUI on the 5090. Or a second creative pipeline.

This means Node 2 can serve **two workloads simultaneously** with no contention — one per GPU.

**Best for:** Interactive/creative work, low-latency chat, running multiple concurrent GPU workloads.

### Combined (120 GB via InfiniBand)

When a model exceeds either node's capacity (e.g., 70B FP16 at ~140 GB), pipeline parallelism across InfiniBand distributes layers across both nodes. This is the exception, not the default — most workloads fit on a single node.

---

## Role Assignments

### Node 1 — "Core" (Heavy Inference + Agents)

| Service | GPU | Why Here |
|---------|-----|----------|
| **vLLM primary** — large models (70B+) | 4x 5070 Ti (tensor parallel) | Only node with enough VRAM for large models in TP |
| **Agent orchestration** — all AI agents | None (CPU) | Agents primarily call the local vLLM instance. Localhost API calls = lowest latency. |
| **Background processing** — batch inference, scheduled tasks | Shares GPUs with vLLM | 56 cores handle scheduling and preprocessing |
| **Fine-tuning** — LoRA/QLoRA | 4x 5070 Ti | Multi-GPU training needs identical cards |
| **Model management** — loading, caching, serving | None (CPU + NVMe) | 16 TB local NVMe holds the model cache |

**Why agents on Node 1:** Agents are primarily LLM consumers. They send prompts to the inference API and process responses. Putting them on the same machine as the primary inference engine means their API calls are `localhost:8000` — zero network latency, zero bandwidth concern. The dashboard on Node 2 talks to agents over 5GbE, which is fine for small JSON payloads.

### Node 2 — "Interface" (Interactive + Creative)

| Service | GPU | Why Here |
|---------|-----|----------|
| **ComfyUI** — image generation | RTX 5090 (32 GB) | Needs max single-GPU VRAM + perf for Flux/SDXL |
| **Video generation** — Wan2.x etc. | RTX 5090 or 4090 | Same — max single-GPU performance |
| **vLLM secondary** — small/medium chat models | RTX 4090 (24 GB) | Fast interactive responses, runs alongside ComfyUI |
| **Dashboard** — unified web UI | None (CPU) | User-facing service, serves the browser interface |
| **EoBQ game server** | Varies | Real-time game AI uses inference APIs on Node 1 or local vLLM |
| **Agent API gateway** | None (CPU) | Routes dashboard requests to agents on Node 1 |

**Why creative workloads on Node 2:** ComfyUI and video gen are single-GPU workloads that benefit from the largest, fastest individual GPU. The 5090's 32 GB VRAM holds Flux dev (~24 GB) with room for LoRA adapters. Running ComfyUI on Node 1 would waste 3 of its 4 GPUs and compete with inference.

**GPU isolation:** Docker containers with `NVIDIA_VISIBLE_DEVICES` pins each service to its GPU. ComfyUI sees only the 5090. vLLM chat sees only the 4090. No contention.

### VAULT — "Vault" (Storage + Media + Always-On)

| Service | Resource | Why Here |
|---------|----------|----------|
| **NFS server** — models, media, shared | Disk I/O | It's the storage server. This is its primary job. |
| **Plex Media Server** | Arc A380 (Quick Sync) | Transcoding uses Intel iGPU. Media library lives here. |
| **\*arr stack** — Sonarr, Radarr, Prowlarr, etc. | CPU (minimal) | Manages media on local storage. Always-on. |
| **Stash** — adult content management | CPU (minimal) | Organizes content on local storage. |
| **Home Assistant** | CPU (minimal) | Always-on requirement. HA on Unraid Docker is well-established. |
| **Download clients** — SABnzbd, qBittorrent | CPU + disk | Downloads go directly to VAULT storage. |
| **Monitoring collector** — Prometheus/Grafana | CPU (minimal) | Central metrics collection. Always-on. |

**Why VAULT for always-on services:** VAULT runs 24/7 for media duties. Home Assistant, monitoring, and media services need to be available even if compute nodes are off (e.g., overnight, away from home). No reason to put always-on services on compute nodes that might be powered down.

### DEV — "Workstation" (Client Only)

| Activity | How |
|----------|-----|
| Access dashboard | Browser → Node 2 dashboard URL |
| Chat with AI | Browser → dashboard chat panel → agents on Node 1 |
| SSH to nodes | Terminal → SSH to any node |
| Development | Claude Code, VS Code, IDEs — all local |
| Quick local inference (optional) | RTX 3060 could run small models for testing, but this is not a primary use case |

DEV runs no persistent Athanor services. It's a client.

---

## Simultaneous Workload Example

Everything running at once, no contention:

```
Node 1 (core):
  └─ vLLM: Llama 70B Q4 across 4x 5070 Ti (tensor parallel)
  └─ Agents: research agent querying vLLM, media agent checking *arr
  └─ Background: scheduled knowledge indexing job

Node 2 (interface):
  └─ ComfyUI: Generating images on RTX 5090 (Flux dev)
  └─ vLLM: Mistral 7B on RTX 4090 (interactive chat)
  └─ Dashboard: Serving web UI to Shaun's browser

VAULT:
  └─ NFS: Serving model files to Node 1/2
  └─ Plex: Streaming 4K to living room TV
  └─ Home Assistant: Running lighting automations
  └─ *arr: Processing a download queue

DEV:
  └─ Browser: Athanor dashboard open
  └─ Claude Code: Building the next feature
```

All of this runs simultaneously. No GPU, CPU, or storage contention between nodes.

---

## Open Questions

1. **Compute node power management** — Should Node 1 and Node 2 run 24/7, or power on/off based on need? Wake-on-LAN from VAULT or DEV could bring them up on demand. Tradeoff: power savings vs. always-available AI. Defer to user preference.

2. **Agent orchestration framework** — ADR-008 will decide this. For now, "agents run as Docker containers on Node 1" is sufficient placement.

3. **EoBQ specifics** — The game engine choice (ADR-012+) affects whether EoBQ's server component runs on Node 2 or is a static client served from VAULT. Placeholder placement on Node 2 for now.

---

## Recommendation

| Machine | Role | Identity |
|---------|------|----------|
| **Node 1** | Heavy inference, agents, background processing | The engine. Always working. |
| **Node 2** | Interactive chat, creative pipelines, dashboard, game dev | The interface. User-facing. |
| **VAULT** | Storage, media, always-on services | The vault. Reliable, always on. |
| **DEV** | Workstation, development, client access | The desk. Shaun sits here. |

No overlap. No wasted capability. Each machine has a clear identity that matches its hardware strengths.
