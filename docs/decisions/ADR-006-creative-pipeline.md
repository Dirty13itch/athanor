# ADR-006: Creative Pipeline

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-creative-pipeline.md](../archive/research/2026-02-15-creative-pipeline.md)
**Depends on:** ADR-004 (Node Roles), ADR-005 (Inference Engine)

---

## Context

Athanor needs image generation (for EoBQ, creative projects, on-demand generation), video generation (cinematic sequences, content creation), and a pipeline that absorbs future creative AI models as they emerge. ADR-004 assigns creative work to Node 2's RTX 5090 (32 GB) with the RTX 4090 (24 GB) as overflow.

---

## Decision

### ComfyUI as the unified creative platform.

ComfyUI runs all generative visual workloads — image, video, and future models — in a single node-based interface.

**Deployment:**
- Docker container on Node 2, pinned to RTX 5090 via `NVIDIA_VISIBLE_DEVICES`
- Port 8188 (ComfyUI default)
- Model storage: `/data/models/diffusion/` (local NVMe) + `/mnt/vault/models/diffusion/` (NFS read-only)

**Primary models:**

| Workload | Model | Precision | VRAM | Notes |
|----------|-------|-----------|------|-------|
| Image generation | Flux dev | FP16 | ~24 GB | Full quality, room for LoRA |
| Image generation | Flux dev | FP8 | ~12 GB | When running complex pipelines |
| Image generation | SDXL | FP16 | ~6.5 GB | Legacy, still useful |
| Video generation | Wan 2.2 14B | FP16 | ~28 GB | Highest quality open-source video |
| Video generation | Wan 2.2 14B | FP8 | ~14 GB | Good quality, more headroom |
| Video generation | Wan 2.1 1.3B | FP16 | ~8 GB | Fast previews, low VRAM |

**RTX 5090 advantages:**
- Flux dev at FP16 with LoRA adapters — no quantization compromises
- Wan 2.2 14B at FP16 — full quality video generation in ~6 min per 4-sec clip
- FP8 quantization reduces VRAM 40% and improves throughput 40% on Blackwell tensor cores
- 50-70% faster than RTX 4090 for diffusion workloads

**RTX 4090 as overflow:**
When the 5090 is occupied (e.g., long video generation), the 4090 can run:
- Image generation with quantized models (Flux FP8, SDXL FP16)
- Wan 2.2 at FP8 or GGUF quantization
- Smaller/faster models for preview iterations

This requires a second ComfyUI instance pinned to device 1, or switching the primary instance's device. Defer the exact mechanism to implementation — the hardware supports it either way.

---

## EoBQ Integration

Empire of Broken Queens needs:
- **Dynamic character portraits** — ComfyUI generates character images with consistent style via LoRA
- **Scene generation** — environments and backgrounds from text prompts
- **Cinematic sequences** — Wan 2.2 video generation for story moments
- **Real-time responsiveness** — images generated in response to player actions

ComfyUI's API (REST + WebSocket) allows EoBQ's game engine to submit generation requests programmatically. The game server on Node 2 calls ComfyUI on localhost:8188 — no network latency.

Workflow files (JSON) define the generation pipeline. EoBQ can have custom workflows for character generation, scene generation, and video sequences, each optimized for their use case.

---

## What This Enables

- **Flux dev at full precision** — no quality compromises on the 5090's 32 GB
- **Video generation** — Wan 2.2 14B produces cinematic-quality open-source video locally
- **Simultaneous creative + chat** — ComfyUI on 5090 while vLLM chat runs on 4090
- **EoBQ integration** — programmatic image/video generation via ComfyUI API
- **Future-proof** — new models plug into ComfyUI as custom nodes without rearchitecting
- **LoRA training** — can train style-consistent LoRAs for EoBQ characters (on 5090 or Node 1)

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Automatic1111 (A1111) | Legacy. Slower, less flexible than ComfyUI. Community has largely migrated to ComfyUI. |
| Forge (A1111 fork) | Better than A1111 but still single-pipeline. ComfyUI's node graph is more powerful for complex workflows. |
| Direct API (diffusers library) | More control but no UI, no workflow management, no community nodes. ComfyUI wraps diffusers and adds everything needed. |
| InvokeAI | Good UI but smaller community, fewer custom nodes, less flexibility than ComfyUI's node graph. |
| Separate tools per workload | Unnecessary fragmentation. ComfyUI handles image and video gen in one interface with shared model loading. |

---

## Risks

- **Blackwell custom node compatibility.** Some ComfyUI custom nodes haven't been updated for CUDA 12.8/sm_120. Workaround: use core nodes until custom nodes catch up. Most critical workflows use core nodes.
- **TensorRT broken on Blackwell.** TRT engine compilation fails for Flux/SDXL on sm_120. Not a blocker — PyTorch inference works fine, TRT is an optional optimization. Will be fixed upstream.
- **Video generation is GPU-bound.** Wan 2.2 14B at 720p takes ~6 minutes per 4-second clip on the 5090. For EoBQ's real-time needs, pre-generation or lower-resolution previews may be necessary.

---

## Sources

- [ComfyUI GitHub](https://github.com/Comfy-Org/ComfyUI)
- [ComfyUI Blackwell support](https://github.com/Comfy-Org/ComfyUI/discussions/6643)
- [ComfyUI RTX 5090 setup](https://blog.comfy.org/p/how-to-get-comfyui-running-on-your)
- [Wan 2.2 ComfyUI workflow](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [Wan 2.2 VRAM guide](https://blogs.novita.ai/wan-2-2-vram-find-the-best-gpu-setup-for-deployment/)
- [FLUX.2 NVIDIA RTX optimization](https://blogs.nvidia.com/blog/rtx-ai-garage-flux-2-comfyui/)
- [RTX 5090 AI generation benchmarks](https://apatero.com/blog/rtx-5090-5080-blackwell-ai-image-video-generation-guide-2025)
