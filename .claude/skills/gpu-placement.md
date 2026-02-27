# GPU Placement Reference

Updated 2026-02-23 (GPU reallocation: RTX 4090 moved Node 2 → Node 1, RTX 5060 Ti added to Node 2).
Original topology audit 2026-02-15. Bus IDs for 5th GPU on Node 1 and RTX 5060 Ti on Node 2 need re-audit.

## Node 1 — core (192.168.1.244)

4x NVIDIA GeForce RTX 5070 Ti (Blackwell, sm_120) + 1x RTX 4090 (Ada Lovelace, sm_89)

| GPU | Bus ID | VRAM | Model | Brand | Notes |
|-----|--------|------|-------|-------|-------|
| 0 | 01:00.0 | 16,303 MiB | RTX 5070 Ti | MSI | NODE to GPU1 |
| 1 | 47:00.0 | 16,303 MiB | RTX 5070 Ti | MSI | NODE to GPU0 |
| 2 | 81:00.0 | 16,303 MiB | RTX 5070 Ti | Gigabyte | PHB to GPU3 |
| 3 | 82:00.0 | 16,303 MiB | RTX 5070 Ti | Gigabyte | PHB to GPU2, display attached |
| 4 | TBD | 24,564 MiB | RTX 4090 | — | Added 2026-02-21, bus ID needs audit |

Total: ~88 GB VRAM (64 GB Blackwell + 24 GB Ada)

### Topology (5070 Ti only — original 4-GPU audit)
```
      GPU0  GPU1  GPU2  GPU3
GPU0   X    NODE  NODE  NODE
GPU1  NODE   X    NODE  NODE
GPU2  NODE  NODE   X    PHB
GPU3  NODE  NODE  PHB    X
```

- All single NUMA node (NUMA 0), CPU affinity 0-111
- No NVLink — all communication via PCIe 4.0 (EPYC 7663 is Gen4)
- GPU2 and GPU3 share a PCIe host bridge (PHB)
- RTX 4090 topology relative to 5070 Ti GPUs unknown until re-audit

### Optimal Placement
- **4-GPU tensor parallelism (vLLM)**: Use 4x RTX 5070 Ti (`CUDA_VISIBLE_DEVICES=0,1,2,3`). Same architecture required for TP.
- **RTX 4090**: Independent workloads only — cannot TP with 5070 Ti (different architecture). Good for second vLLM instance, agent inference, or batch jobs.
- **Single GPU jobs**: Prefer GPU 0 or GPU 1 (no display attached, separate host bridges)
- **Power limits configured**: RTX 4090 @ 320W, RTX 5070 Ti @ 240W each

## Node 2 — interface (192.168.1.225)

| GPU | Bus ID | VRAM | Model | Architecture |
|-----|--------|------|-------|-------------|
| 0 | 03:00.0 | 32,607 MiB | RTX 5090 | Blackwell (sm_120) |
| 1 | TBD | 16,384 MiB | RTX 5060 Ti | Blackwell (sm_120) |

Total: ~48 GB VRAM

### Notes
- Both Blackwell architecture — TP theoretically possible but different GPU tiers (32 GB vs 16 GB)
- RTX 5060 Ti bus ID needs re-audit (installed after original audit)
- PHB interconnect expected (via CPU PCIe host bridge)

### Optimal Placement
- **RTX 5090 (GPU 0)**: 32 GB. ComfyUI (Flux), creative inference, large single-GPU models.
- **RTX 5060 Ti (GPU 1)**: 16 GB. vLLM (Qwen3.5-27B-AWQ via --language-model-only), fast chat, lightweight workloads.
- Use `--gpu-memory-utilization 0.85` and `--max-num-seqs 64` on 16 GB GPUs to avoid OOM.

## VAULT — no NVIDIA GPUs

- Intel Arc A380 (6 GB GDDR6) — Quick Sync transcoding for Plex only
- Not usable for CUDA/inference workloads

## DEV — not a server

- NVIDIA RTX 3060 12 GB — desktop display, light CUDA capability
- Not usable for inference

## VRAM Budget Summary

| Node | Total VRAM | GPUs | Primary Use |
|------|-----------|------|-------------|
| Node 1 | 88 GB | 4x 5070 Ti + 4090 | TP=4 inference (Qwen3-32B-AWQ) + independent 4090 |
| Node 2 | 48 GB | 5090 + 5060 Ti | ComfyUI (5090) + fast chat vLLM (5060 Ti) |
| Combined | 136 GB | 7 GPUs | Multi-node via Ray+InfiniBand (future) |
