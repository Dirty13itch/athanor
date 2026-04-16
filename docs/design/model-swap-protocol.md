# Model Swap Protocol — Node 2 GPU Time-Sharing

*How vLLM and ComfyUI share the RTX 5090 on Node 2.*

---

## The Problem

The RTX 5090 (32 GB) on Node 2 is the only GPU with enough VRAM for both large LLM inference and high-resolution image generation. ComfyUI and vLLM both want it. They can't run at full capacity simultaneously.

---

## Current Swap Pattern

1. **Idle state:** vLLM has Qwen3.5-35B-A3B-AWQ-4bit loaded on the 5090 (GPU 0). ComfyUI has no model loaded on GPU 1 (5060 Ti is dedicated to Flux dev FP8).

2. **Creative request arrives:** ComfyUI loads diffusion model on the 5090 (Flux dev FP8 ~12 GB). vLLM's model stays loaded if combined VRAM fits, or gets offloaded if combined exceeds 32 GB.

3. **Generation completes:** ComfyUI releases diffusion model VRAM. vLLM model reloads if it was offloaded (~2-5 sec from local NVMe).

4. **Concurrent chat during generation:** Routes to Node 1 (TP=4 Qwen3.5-27B-FP8) instead. The supervisor knows the 5090 is busy and diverts interactive chat to Node 1.

---

## GPU Pinning

Docker Compose `deploy.resources.reservations.devices` pins each container to specific GPUs:

- vLLM container → GPU 0 (RTX 5090)
- ComfyUI container → GPU 1 (RTX 5060 Ti) primary, GPU 0 (RTX 5090) for heavy workloads
- The swap is orchestrated by which containers are running and what the supervisor routes

---

## Current Allocation (Node 2)

| GPU | Device | Current Use | VRAM |
|-----|--------|-------------|------|
| 0 | RTX 5090 | vLLM (Qwen3.5-35B-A3B-AWQ-4bit) | 32 GB |
| 1 | RTX 5060 Ti | ComfyUI (Flux dev FP8) | 16 GB |

---

## Future Resolution

If a PRO 6000 (96 GB) is acquired:
- LLM gets the PRO 6000 permanently — single card runs any model without contention
- RTX 5090 becomes dedicated creative GPU
- No time-sharing, no model swaps, no routing workarounds
- Changes LiteLLM/routing config, nothing else in the architecture changes
