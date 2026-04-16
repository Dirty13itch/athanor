# Creative Pipeline

> Historical note: archived research retained for ADR-006 decision history. Current creative-service, model, and node truth is tracked in the canonical registries and reports.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-006 (Creative Pipeline)
**Depends on:** ADR-004 (Node Roles), ADR-005 (Inference Engine)

---

## The Question

What tools run Athanor's image generation, video generation, and future creative workloads? How do they map to the GPU allocation from ADR-004?

---

## Hardware (from ADR-004)

Creative workloads run on **Node 2 (Interface)**:
- **RTX 5090 (32 GB)** — primary creative GPU. Blackwell architecture, NVFP4 support.
- **RTX 4090 (24 GB)** — secondary. Can run creative work when 5090 is occupied, but primarily serves chat inference (ADR-005).

Node 1's 4x 5070 Ti are reserved for LLM inference. Creative work does NOT go on Node 1 (wastes 3 GPUs on single-GPU workloads).

---

## Workloads

### Image Generation

**ComfyUI** is the only serious candidate. It's the standard node-based interface for Stable Diffusion, Flux, and related models. No other tool offers its flexibility, model support, and community ecosystem.

**Current state on Blackwell (Feb 2026):**
- ComfyUI has day-1 Blackwell support via PyTorch nightly (2.7.0+ or 2.9.0+cu128)
- Portable package v0.3.30 includes updated PyTorch for RTX 5090/5080
- Some custom nodes haven't been updated for CUDA 12.8 — expect occasional issues
- TensorRT acceleration for image gen is broken on Blackwell (SDXL/Flux TRT engines won't build)

**Models and VRAM:**

| Model | FP16 VRAM | FP8 VRAM | Fits 5090 (32 GB)? |
|-------|-----------|----------|---------------------|
| Flux dev | ~24 GB | ~12 GB | Yes (FP16 with LoRA headroom) |
| Flux dev + LoRA | ~26-28 GB | ~14 GB | Yes (FP16, tight) |
| SDXL base | ~6.5 GB | ~4 GB | Easily |
| SDXL + refiner | ~13 GB | ~8 GB | Easily |
| SD 3.5 Large | ~16 GB | ~8 GB | Yes |

The 5090's 32 GB comfortably runs Flux dev at FP16 with room for LoRA adapters and control nets. This is the primary advantage of the 5090 over smaller GPUs — Flux dev at full precision without compromises.

FP8 quantization (available on Blackwell) reduces VRAM by ~40% and improves performance by ~40%. At FP8, Flux runs in ~12 GB, leaving 20 GB free for complex pipelines with multiple models loaded.

**Sources:**
- [ComfyUI Blackwell support thread](https://github.com/Comfy-Org/ComfyUI/discussions/6643)
- [ComfyUI on RTX 5090 setup guide](https://blog.comfy.org/p/how-to-get-comfyui-running-on-your)
- [FLUX.2 optimized for NVIDIA RTX (NVIDIA blog)](https://blogs.nvidia.com/blog/rtx-ai-garage-flux-2-comfyui/)
- [Running Flux on low VRAM (Civitai)](https://civitai.com/articles/6846/running-flux-on-68-gb-vram-using-comfyui)

### Video Generation

**Wan 2.1/2.2** is the current leading open-source video generation model family. ComfyUI has native support.

**Models and VRAM:**

| Model | Precision | VRAM | Resolution | Speed (5090) |
|-------|-----------|------|------------|--------------|
| Wan 2.1 1.3B (T2V) | FP16 | ~8 GB | 480p | Fast |
| Wan 2.2 14B (T2V/I2V) | FP16 | ~28 GB | 720p | ~6 min / 4 sec video |
| Wan 2.2 14B | FP8 | ~14 GB | 720p | Faster |
| Wan 2.2 14B | GGUF Q4 | ~7.5 GB | 720p | Slower but fits anywhere |

The 5090 runs Wan 2.2 14B at FP16 (28 GB) with room to spare. At FP8 (14 GB), it's comfortable. The RTX 5090 generates 720p video roughly 50-70% faster than the 4090.

GGUF quantized versions (Q4-Q8) allow video generation on GPUs with as little as 6 GB VRAM — useful for the 4090 if the 5090 is busy with image gen.

**Emerging models:** HunyuanVideo, LTX Video, CogVideoX are also supported in ComfyUI. The node-based architecture means new video models plug in as custom nodes without changing the pipeline.

**Sources:**
- [Wan 2.2 ComfyUI workflow](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [Wan 2.2 GGUF low VRAM guide](https://www.nextdiffusion.ai/tutorials/how-to-run-wan22-image-to-video-gguf-models-in-comfyui-low-vram)
- [Wan2GP for GPU-poor setups](https://github.com/deepbeepmeep/Wan2GP)
- [Wan 2.2 VRAM requirements](https://blogs.novita.ai/wan-2-2-vram-find-the-best-gpu-setup-for-deployment/)
- [RTX 5090 Blackwell AI generation guide](https://apatero.com/blog/rtx-5090-5080-blackwell-ai-image-video-generation-guide-2025)

### Future Creative Workloads

ComfyUI's node-based architecture absorbs new models and techniques without architectural changes:
- 3D generation (when models mature)
- Audio generation
- Style transfer, upscaling, inpainting
- LoRA training (via ComfyUI or standalone tools)
- Any new diffusion/transformer-based generative model

This is why ComfyUI is the right choice — it's a platform, not a single-model tool.

---

## GPU Isolation on Node 2

Docker containers with `NVIDIA_VISIBLE_DEVICES` pin each service:

```yaml
# docker-compose.yml (Node 2)
services:
  comfyui:
    image: comfyui:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']  # RTX 5090
              capabilities: [gpu]
    ports:
      - "8188:8188"
    volumes:
      - /data/models/diffusion:/models
      - /mnt/vault/models/diffusion:/vault-models:ro

  vllm-chat:
    image: vllm:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']  # RTX 4090
              capabilities: [gpu]
    ports:
      - "8001:8000"
```

ComfyUI sees only the 5090. vLLM chat sees only the 4090. No contention.

---

## Model Storage

From ADR-003:
- **Hot models** on Node 2's local NVMe (`/data/models/diffusion/`) — Flux dev, active LoRAs, Wan 2.2
- **Full repository** on VAULT NFS (`/mnt/vault/models/diffusion/`) — all checkpoints, LoRA library
- Load time from local NVMe: 2-4 seconds for Flux. From VAULT NVMe over NFS: ~11 seconds. Both are fine.

---

## Recommendation

1. **ComfyUI** as the unified creative interface — image gen, video gen, future models
2. **RTX 5090** as the primary creative GPU — Flux FP16 with headroom, Wan 2.2 14B FP16
3. **RTX 4090** as overflow — can run creative work when 5090 is busy, otherwise serves chat
4. **Docker isolation** — ComfyUI pinned to 5090, vLLM pinned to 4090
5. **No alternatives needed** — ComfyUI is the industry standard, no competing tool offers comparable flexibility
