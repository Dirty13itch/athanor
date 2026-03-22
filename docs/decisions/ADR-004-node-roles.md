# ADR-004: Node Roles + Hardware Allocation

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/research/2026-02-15-node-roles.md](../research/2026-02-15-node-roles.md)
**Depends on:** ADR-001 (Base Platform), ADR-002 (Network), ADR-003 (Storage)

---

## Context

Athanor has four machines with very different hardware profiles. ADR-001 through 003 decided the OS, network, and storage architecture. This ADR assigns each machine a clear role based on its hardware strengths, ensuring every workload lands on the right hardware with no overlap or wasted capability.

---

## Decision

### Node 1 — "Core" (Heavy Inference + Agents)

**Hardware:** EPYC 7663 56C/112T, 224 GB ECC RAM, 4x RTX 5070 Ti (64 GB VRAM), 16 TB NVMe

| Service | GPU | Notes |
|---------|-----|-------|
| vLLM primary — large models (70B+) | 4x 5070 Ti (tensor parallel) | 64 GB VRAM, 4 identical GPUs ideal for TP |
| AI agent orchestration | CPU only | Agents call local vLLM via localhost — zero network latency |
| Background processing / batch inference | Shares GPUs | 56 cores handle scheduling and preprocessing |
| LoRA/QLoRA fine-tuning | 4x 5070 Ti | Multi-GPU training needs identical cards |
| Model cache management | CPU + NVMe | 16 TB local cache |

**Why this role:** The 4 identical GPUs make Node 1 the only machine that can tensor-parallel large models. The EPYC's 56 cores and 224 GB RAM handle KV cache overflow and high-throughput request batching. Agents live here because they primarily consume the local LLM — localhost API calls are instant.

### Node 2 — "Interface" (Interactive + Creative)

**Hardware:** Ryzen 9 9950X 16C/32T, 128 GB DDR5, RTX 5090 (32 GB) + RTX 4090 (24 GB), 4 TB NVMe

| Service | GPU | Notes |
|---------|-----|-------|
| ComfyUI — image generation | RTX 5090 | 32 GB VRAM holds Flux dev (~24 GB) + LoRA adapters |
| Video generation (Wan2.x etc.) | RTX 5090 or 4090 | Max single-GPU performance |
| vLLM secondary — interactive chat | RTX 4090 | Fast 7B-13B models for low-latency responses |
| Dashboard — unified web UI | CPU only | User-facing, serves browser interface |
| EoBQ game server | Varies | Real-time game AI calls inference APIs |
| Agent API gateway | CPU only | Routes dashboard requests to agents on Node 1 |

**Why this role:** The 5090 is the most powerful single GPU — best for single-GPU creative workloads. The 4090 runs a chat model simultaneously with zero contention (different GPU, isolated via `NVIDIA_VISIBLE_DEVICES`). The heterogeneous GPUs work best independently, not in tensor parallel. Node 2 can serve **two GPU workloads at once**.

### VAULT — "Vault" (Storage + Media + Always-On)

**Hardware:** TR 7960X 24C/48T, 128 GB DDR5 ECC, Arc A380, 164 TB HDD + 6.5 TB NVMe, Unraid

| Service | Resource | Notes |
|---------|----------|-------|
| NFS file server | Disk I/O | Models, media, shared storage — primary job |
| Plex Media Server | Arc A380 (Quick Sync) | Intel GPU handles transcoding |
| *arr stack (Sonarr, Radarr, etc.) | CPU (minimal) | Media acquisition, always-on |
| Stash — adult content management | CPU (minimal) | Organization and tagging |
| Home Assistant | CPU (minimal) | Always-on home automation |
| Download clients (SABnzbd, qBit) | CPU + disk | Downloads land directly on VAULT storage |
| Monitoring (Prometheus/Grafana) | CPU (minimal) | Central metrics, always-on |

**Why this role:** VAULT runs 24/7 for media. Services that must be always-on (HA, Plex, monitoring, downloads) belong here — they stay available even if compute nodes are powered down. Stays on Unraid (non-negotiable per VISION.md).

### DEV — "Workstation" (Client Only)

**Hardware:** i7-13700K, 64 GB DDR5, RTX 3060, Windows 11

| Activity | How |
|----------|-----|
| Dashboard access | Browser → Node 2 |
| Chat with AI | Dashboard chat → agents on Node 1 |
| SSH management | Terminal → any node |
| Development | Claude Code, VS Code, IDEs |

DEV runs no persistent Athanor services. It's Shaun's desk. The RTX 3060 could run small local models for development testing but this is not a primary use case.

---

## GPU Allocation Summary

| GPU | Node | VRAM | Primary Workload | Secondary |
|-----|------|------|-------------------|-----------|
| 4x RTX 5070 Ti | Node 1 | 64 GB | vLLM tensor parallel (large models) | Fine-tuning |
| RTX 5090 | Node 2 | 32 GB | ComfyUI / video gen | Large single-model inference |
| RTX 4090 | Node 2 | 24 GB | vLLM chat (small/medium models) | Overflow creative work |
| Arc A380 | VAULT | 6 GB | Plex transcoding (Quick Sync) | — |
| RTX 3060 | DEV | 12 GB | — (optional dev testing) | — |

**Combined via InfiniBand: 120 GB** across 6 NVIDIA GPUs (pipeline parallelism for models too large for either node alone).

---

## Simultaneous Operation

Everything below runs at the same time with no contention:

```
Node 1:  vLLM serving 70B Q4 (4-GPU TP) + agents querying it + background jobs
Node 2:  ComfyUI on 5090 + Mistral 7B chat on 4090 + dashboard serving
VAULT:   NFS + Plex streaming + HA automations + *arr processing
DEV:     Browser open to dashboard, Claude Code building features
```

Six GPUs, four machines, all working. No resource conflicts.

---

## What This Enables

- **Large model inference** (70B+) on Node 1 while Node 2 handles creative work — simultaneously
- **Interactive chat** with a dedicated GPU (4090) that never competes with image generation (5090)
- **Always-on home services** (Plex, HA, monitoring) independent of compute node availability
- **Creative pipeline** (ComfyUI → 5090) that doesn't degrade inference performance
- **Multi-node inference** (120 GB VRAM) when needed, via InfiniBand
- **Agent autonomy** — agents on Node 1 have localhost access to the primary LLM, no network dependency

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| All inference on Node 2 (most powerful single GPUs) | Wastes Node 1's 4-GPU tensor parallelism. Can't run 70B+ models on a single 5090. |
| All creative work on Node 1 | Wastes the 5090's superior single-GPU performance. ComfyUI uses one GPU — tying up 4 is wasteful. |
| Agents on VAULT | Adds network latency to every agent → LLM call. Agents make thousands of inference calls. Localhost is faster. |
| Agents on Node 2 | Agent → LLM calls go over 5GbE to Node 1 instead of localhost. Works but adds latency for no benefit. |
| Dashboard on VAULT | Would be always-on (good), but VAULT's Unraid Docker environment is less flexible than Ubuntu. Dashboard likely needs to talk to many services. Node 2 is fine. |
| HA on Node 2 | HA needs to be always-on. Compute nodes might be powered down when Shaun isn't working. VAULT never sleeps. |
| Split agents across nodes | Adds complexity with no gain. Agents are lightweight (CPU, not GPU). Centralizing them on one node keeps orchestration simple. |

---

## Risks

- **Node 1 is a single point of failure for inference.** If Node 1 goes down, large model inference and agents are unavailable. Mitigation: Node 2's 4090 can serve medium models as a fallback. Full redundancy isn't worth the cost for a one-person system.
- **Node 2 is a single point of failure for creative work.** If Node 2 goes down, no ComfyUI or dashboard. Mitigation: ComfyUI could temporarily run on Node 1 (just less efficient). Dashboard is just a web app — could be quickly redeployed.
- **VAULT dependency.** If VAULT goes down, NFS mounts fail and media stops. Mitigation: hot models cached on local NVMe (ADR-003) mean inference continues without VAULT. Media and always-on services wait for VAULT to return.

---

## Sources

- Hardware specs from [docs/hardware/inventory.md](../hardware/inventory.md) and per-node audits
- GPU allocation logic from [vLLM parallelism docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- NVIDIA container toolkit GPU isolation: `NVIDIA_VISIBLE_DEVICES` environment variable
- Unraid Docker for always-on services: established community practice
