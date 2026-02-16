# GPU Placement Reference

Actual GPU topology from live audit (2026-02-15).

## Node 1 — core (192.168.1.244)

4x NVIDIA GeForce RTX 5070 Ti (Blackwell, sm_120)

| GPU | Bus ID | VRAM | Brand | Interconnect |
|-----|--------|------|-------|-------------|
| 0 | 01:00.0 | 16,303 MiB | MSI | NODE to GPU1, NODE to GPU2/3 |
| 1 | 47:00.0 | 16,303 MiB | MSI | NODE to GPU0, NODE to GPU2/3 |
| 2 | 81:00.0 | 16,303 MiB | Gigabyte | NODE to GPU0/1, PHB to GPU3 |
| 3 | 82:00.0 | 16,303 MiB | Gigabyte | NODE to GPU0/1, PHB to GPU2 |

Total: 65,212 MiB (~63.7 GB)

### Topology Matrix
```
      GPU0  GPU1  GPU2  GPU3
GPU0   X    NODE  NODE  NODE
GPU1  NODE   X    NODE  NODE
GPU2  NODE  NODE   X    PHB
GPU3  NODE  NODE  PHB    X
```

- All single NUMA node (NUMA 0), CPU affinity 0-111
- GPU2 and GPU3 share a PCIe host bridge (PHB) — slightly better P2P between them
- GPU0 and GPU1 are on separate PCIe root complexes (NODE)
- No NVLink — all communication via PCIe 4.0 (EPYC 7663 is Gen4)
- **GPU 3 (82:00.0) has display attached** — use for console output, not primary compute if possible

### Optimal Placement
- **4-GPU tensor parallelism**: Use all GPUs (`--gpus all`). NCCL handles topology automatically.
- **Single GPU jobs**: Prefer GPU 0 or GPU 1 (no display attached, separate host bridges)
- **2-GPU pairs**: GPU 2+3 (PHB, best interconnect) or GPU 0+1 (separate bridges, least contention)

## Node 2 — interface (192.168.1.225)

| GPU | Bus ID | VRAM | Model | Architecture |
|-----|--------|------|-------|-------------|
| 0 | 01:00.0 | 24,564 MiB | RTX 4090 | Ada Lovelace (sm_89) |
| 1 | 03:00.0 | 32,607 MiB | RTX 5090 | Blackwell (sm_120) |

Total: 57,171 MiB (~55.8 GB)

### Topology Matrix
```
      GPU0  GPU1
GPU0   X    PHB
GPU1  PHB    X
```

- Single NUMA node (NUMA 0), CPU affinity 0-31
- PHB interconnect (via CPU PCIe host bridge)
- Different architectures — cannot do tensor parallelism across them

### Optimal Placement
- **RTX 5090 (GPU 1)**: NVFP4-capable, 32 GB. Use for large models, creative inference, ComfyUI.
- **RTX 4090 (GPU 0)**: 24 GB, Ada. Use for fast chat (7B-13B FP16), concurrent workloads, no NVFP4.
- **Never TP across these GPUs** — different architectures.

## VAULT — no NVIDIA GPUs

- Intel Arc A380 (6 GB GDDR6) — Quick Sync transcoding for Plex only
- Not usable for CUDA/inference workloads

## DEV — not a server

- RTX 3060 12 GB — local development/testing only

## VRAM Budget Summary

| Node | Total VRAM | Primary Use |
|------|-----------|-------------|
| Node 1 | 63.7 GB | 4-GPU TP inference (70B models via NVFP4) |
| Node 2 | 55.8 GB | Dual independent: 5090 (creative/large) + 4090 (chat) |
| Combined | 119.5 GB | Multi-node via Ray+InfiniBand (future) |
