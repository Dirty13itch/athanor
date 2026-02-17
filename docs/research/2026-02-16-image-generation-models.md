# Image Generation Models for Local Inference via ComfyUI

**Date:** 2026-02-16
**Status:** Complete — recommendation ready
**Supports:** ADR-006 (Creative Pipeline)
**Depends on:** ADR-004 (Node Roles)

---

## The Question

Which image generation models should Athanor run locally via ComfyUI on Node 2? The target hardware is an RTX 5090 (32 GB) as primary and RTX 4090 (24 GB) as secondary. Models must run at interactive speed, support LoRA customization, and be capable of generating uncensored adult content for Empire of Broken Queens.

---

## Hardware Context

- **RTX 5090** — 32 GB GDDR7, Blackwell architecture (Compute Capability 12.0), native NVFP4 support, 5th-gen Tensor Cores
- **RTX 4090** — 24 GB GDDR6X, Ada Lovelace architecture, FP8 support via Tensor Cores
- ComfyUI supports NVFP4 and NVFP8 natively as of early 2026 (requires PyTorch with CUDA 13.0/cu130)
- NVFP4 on RTX 5090: ~60% VRAM reduction, ~3x inference speedup vs FP16
- FP8 on RTX 4090: ~50% VRAM reduction, ~38% speed boost vs FP16

Sources:
- [NVIDIA TensorRT FP4 blog](https://developer.nvidia.com/blog/nvidia-tensorrt-unlocks-fp4-image-generation-for-nvidia-blackwell-geforce-rtx-50-series-gpus/)
- [ComfyUI NVFP4 optimizations](https://blog.comfy.org/p/new-comfyui-optimizations-for-nvidia)
- [NVIDIA CES 2026 ComfyUI announcements](https://blogs.nvidia.com/blog/rtx-ai-garage-ces-2026-open-models-video-generation/)

---

## Model-by-Model Analysis

### 1. FLUX.1 Family (Black Forest Labs) — 12B parameters

The original Flux generation. Still the most mature ecosystem for consumer GPU inference.

| Variant | Parameters | Steps | License | VRAM (FP16) | VRAM (FP8) |
|---------|-----------|-------|---------|-------------|-------------|
| FLUX.1 [dev] | 12B | 20-30 | Non-Commercial (outputs can be commercial) | ~24 GB | ~16 GB |
| FLUX.1 [schnell] | 12B | 4 | Apache 2.0 | ~24 GB | ~16 GB |
| FLUX.1 [pro] | 12B | — | API only | — | — |

**Architecture:** Rectified flow transformer. Dual text encoders (CLIP-L + T5-XXL).

**Generation Speed (1024x1024):**
- RTX 4090 FP16: ~15 seconds (20 steps)
- RTX 4090 FP8: ~9-10 seconds
- RTX 5090 FP8: ~6.2 seconds
- RTX 5090 FP4: ~5 seconds

**Quality:** Top-tier photorealism, excellent prompt adherence, best-in-class hand rendering, reliable text rendering for short phrases. Consistently renders all specified elements in complex multi-object scenes.

**NSFW/Adult:** Base model has soft safety training but no hard filter. Community LoRAs (Flux-Uncensored-V2, Flux Lustly Uncensored, NSFW FLUX LoRA on Civitai) bypass remaining restrictions effectively. Full nudity and explicit content achievable.

**LoRA Training:**
- Kohya: 24 GB minimum, well-documented
- AI-Toolkit (Ostris): 12-24 GB, simplest option
- SimpleTuner: 20 GB with Optimum-Quanto, down to 9 GB with NF4-BNB
- FluxGym: 12-20 GB, dead simple UI
- Training time: 40 min to 4 hours depending on dataset size and VRAM

**Inpainting/Outpainting:** Supported via standard ComfyUI inpaint workflows. Not specialized but functional.

**Text Rendering:** Good for short text. Far more consistent than SDXL. Struggles with longer multi-line text.

**ComfyUI:** First-class native support. Massive workflow ecosystem.

Sources:
- [FLUX.1 dev HuggingFace](https://huggingface.co/black-forest-labs/FLUX.1-dev)
- [ComfyUI Flux benchmarks discussion](https://github.com/comfyanonymous/ComfyUI/discussions/4571)
- [RTX 5090 Flux benchmarks](https://github.com/Comfy-Org/ComfyUI/discussions/9002)
- [FLUX licensing](https://bfl.ai/licensing)
- [LoRA training guide 2025](https://sanj.dev/post/lora-training-2025-ultimate-guide)
- [Flux Uncensored V2](https://huggingface.co/Ryouko65777/Flux-Uncensored-V2)

---

### 2. FLUX.1 Kontext [dev] (Black Forest Labs) — 12B parameters

Not a generation model per se but critical for the editing pipeline. Instruction-based image editing.

| Variant | License | VRAM (FP16) | VRAM (FP8) | VRAM (FP4) |
|---------|---------|-------------|-------------|-------------|
| Kontext [dev] | Non-Commercial | ~24 GB | ~12 GB | ~8 GB |

**What it does:** Character-preserving edits, inpainting, outpainting, iterative refinement, style transfer — all via natural language instructions. No masks required.

**Speed:** 6-12 seconds per edit on RTX 4090+.

**Quality:** Outperforms Gemini-Flash Image, Bytedance Bagel, and HiDream-E1-Full in independent evals for character preservation and editing accuracy.

**ComfyUI:** Native day-0 support. BF16, FP8, and FP4 TensorRT variants available.

Sources:
- [FLUX.1 Kontext dev announcement](https://bfl.ai/announcements/flux-1-kontext-dev)
- [Kontext HuggingFace](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)
- [NVIDIA Kontext optimization blog](https://developer.nvidia.com/blog/optimizing-flux-1-kontext-for-image-editing-with-low-precision-quantization)

---

### 3. FLUX.2 Family (Black Forest Labs) — 32B / 9B / 4B parameters

The next generation. Released November 2025. Unified generation + editing in a single checkpoint.

| Variant | Parameters | Steps | License | VRAM (FP16) | VRAM (FP8) | VRAM (FP4/GGUF) |
|---------|-----------|-------|---------|-------------|-------------|------------------|
| FLUX.2 [dev] | 32B | 20-30 | Non-Commercial | ~64 GB+ | ~32 GB | ~18-20 GB (Q4) |
| FLUX.2 [klein] 9B | 9B | 4 | Non-Commercial | ~20 GB | ~12 GB | ~8 GB |
| FLUX.2 [klein] 4B | 4B | 4 | **Apache 2.0** | ~13 GB | ~8 GB | ~5 GB |

**Architecture:** 32B flow matching transformer (dev). Klein variants are step-distilled with Qwen3 text embedder.

**Generation Speed (1024x1024):**
- FLUX.2 [dev] RTX 5090 FP8: ~6.2 seconds
- FLUX.2 [klein] 4B: sub-second on RTX 5090

**Quality:** FLUX.2 [dev] at 32B represents the current ceiling for open-weight image generation quality. Klein 4B is impressive for its size but noticeably below the full model. Klein 9B is a strong middle ground.

**NSFW/Adult:** Same situation as FLUX.1 — safety-trained but not hard-filtered. Community modifications expected to follow quickly. The 4B klein under Apache 2.0 is the most modification-friendly.

**LoRA Training:** SimpleTuner supports FLUX.2 LoRA training. AI-Toolkit support expected. The 32B model requires significant VRAM for training (48 GB+). Klein 4B/9B are more practical for consumer GPU training.

**Key Consideration:** FLUX.2 [dev] at 32B is too large for FP16 on any consumer GPU. Viable on RTX 5090 only with Q4 quantization (~18-20 GB). The quality vs FLUX.1 [dev] at 12B when both are quantized to fit in VRAM is not yet clearly benchmarked by the community.

**ComfyUI:** Native support. NVFP4 and NVFP8 checkpoints available.

Sources:
- [FLUX.2 GitHub](https://github.com/black-forest-labs/flux2)
- [FLUX.2 klein announcement](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence)
- [FLUX.2 klein 4B HuggingFace](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)
- [FLUX.2 dev HuggingFace](https://huggingface.co/black-forest-labs/FLUX.2-dev)
- [VentureBeat FLUX.2 klein coverage](https://venturebeat.com/technology/black-forest-labs-launches-open-source-flux-2-klein-to-generate-ai-images-in/)
- [FLUX.2 LoRA training guide](https://apatero.com/blog/flux-2-lora-training-complete-guide-2025)

---

### 4. Z-Image-Turbo (Alibaba Tongyi Lab) — 6B parameters

Released November 2025. The speed king. Uncensored out of the box.

| Metric | Value |
|--------|-------|
| Parameters | 6B |
| Architecture | S3-DiT (Scalable Single-Stream DiT) with Qwen 3 4B text encoder |
| Steps | 8 (distilled) |
| License | **Apache 2.0** |
| VRAM (BF16) | ~16 GB |
| VRAM (FP8) | ~6-8 GB |
| VRAM (GGUF Q4) | ~4-6 GB |

**Generation Speed (1024x1024):**
- RTX 4090: ~2.3 seconds (8 steps)
- Sub-second claimed on enterprise GPUs
- Low-end 8 GB GPUs: ~13 seconds

**Quality:** Matches or exceeds FLUX.2 [dev], HunyuanImage 3.0, and Imagen 4 in benchmarks despite being 5x smaller. Photorealistic output with strong prompt adherence. The quality-per-parameter ratio is exceptional.

**NSFW/Adult:** Fully uncensored from the factory. No safety filters. Celebrities, fictional characters, explicit content — all work out of the box. This is the most NSFW-friendly model available at this quality tier.

**LoRA Training:** Early but growing. Supports standard training workflows. The 6B size makes it very practical for consumer GPU training.

**Inpainting/Outpainting:** Supported via ComfyUI standard workflows.

**Text Rendering:** Moderate. Better than SDXL, comparable to FLUX.1, below Playground v3 and Ideogram.

**ComfyUI:** Native support. GGUF, FP8, and BF16 variants available. Workflows widely shared.

Sources:
- [Z-Image-Turbo HuggingFace](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
- [ComfyUI Z-Image-Turbo tutorial](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)
- [Z-Image-Turbo announcement](https://comfyui-wiki.com/en/news/2025-11-27-alibaba-z-image-turbo-release)
- [Next Diffusion Z-Image-Turbo guide](https://www.nextdiffusion.ai/tutorials/z-image-turbo-fast-uncensored-image-generation-comfyui)
- [Decrypt coverage](https://decrypt.co/350572/chinas-z-image-dethrones-flux-king-of-ai-art)
- [Civitai NSFW low VRAM workflow](https://civitai.com/models/2190716/nsfw-uncensored-z-image-turbo-with-extremely-low-vram4-6-gb)

---

### 5. HiDream-I1 (HiDream AI) — 17B parameters (MoE)

Released April 2025. Top-tier quality with Mixture-of-Experts efficiency.

| Variant | Steps | VRAM (FP16) | VRAM (FP8) | VRAM (NF4) | VRAM (GGUF Q4) |
|---------|-------|-------------|-------------|-------------|-----------------|
| HiDream-I1-Full | 50 | ~27 GB | ~24 GB | ~15-23 GB* | ~8-10 GB |
| HiDream-I1-Dev | 28 | ~27 GB | ~20 GB | ~15 GB | ~8 GB |
| HiDream-I1-Fast | 16 | ~27 GB | ~16 GB | ~15 GB | ~8 GB |

*NF4 spikes to ~23 GB during inference even though model size is ~15 GB.

**Architecture:** Sparse DiT with dynamic MoE. Dual-stream decoupled design. 17B total parameters but only a fraction active per token.

**Generation Speed (RTX 4090, FP8):**
- Full: ~60-85 seconds (10 steps, optimized)
- Dev: ~20 seconds (second generation onwards)
- Fast: ~10-15 seconds

**Quality:** State-of-the-art at release. Excellent prompt adherence, sharp detail, diverse styles (photorealistic, artistic, cartoon). Strong competitor to FLUX.1 [dev] in quality.

**NSFW/Adult:** Base model filters explicit content from training data. Does not hard-block outputs but has guardrails in the CLIP model that prevent full nudity. Community FP8 uncensored versions exist on Civitai (v0.33 alpha) — can reliably render topless content but full nudity remains inconsistent as of early 2026.

**LoRA Training:**
- AI-Toolkit: Supports HiDream-I1 LoRA training (added April 2025)
- SimpleTuner: MoE support included
- Diffusion-pipe: Only framework for fully local training
- **Major limitation:** Currently requires 48 GB VRAM for training. 24 GB support expected but not yet available.

**License:** **MIT** — fully permissive for personal, research, and commercial use.

**Text Rendering:** Good. On par with FLUX.1 in accuracy.

**ComfyUI:** Native support. FP8, NF4, and GGUF variants all work.

Sources:
- [HiDream-I1 GitHub](https://github.com/HiDream-ai/HiDream-I1)
- [HiDream-I1-Full HuggingFace](https://huggingface.co/HiDream-ai/HiDream-I1-Full)
- [HiDream VRAM discussion](https://github.com/HiDream-ai/HiDream-I1/issues/7)
- [HiDream performance benchmarks](https://www.instasd.com/post/hidream-performance-benchmarks-in-comfyui)
- [HiDream uncensored Civitai](https://civitai.com/models/1498292/hidream-i1-fp8-uncensored-fulldevfast)
- [HiDream unfiltered guide](https://www.stablediffusiontutorials.com/2025/04/hidream-model.html)
- [AI-Toolkit HiDream support](https://www.kombitz.com/2025/04/18/ai-toolkit-adds-hidream-i1-lora-training-support/)

---

### 6. Stable Diffusion 3.5 (Stability AI) — 2.5B / 8B parameters

Released October 2024. Stability AI's response to FLUX.

| Variant | Parameters | Steps | License | VRAM (FP16) | VRAM (FP8) |
|---------|-----------|-------|---------|-------------|-------------|
| SD3.5 Medium | 2.5B | 30-50 | Community License* | ~8 GB | ~5 GB |
| SD3.5 Large | 8B | 30-50 | Community License* | ~18 GB | ~11 GB |
| SD3.5 Large Turbo | 8B | 4 | Community License* | ~18 GB | ~6 GB (aggressive quant) |

*Community License: Free for research, non-commercial, and commercial use for orgs/individuals under $1M annual revenue.

**Architecture:** MMDiT (Multimodal DiT). Triple text encoder (CLIP-L, CLIP-G, T5-XXL).

**Generation Speed (RTX 4090):**
- SD3.5 Large: ~58 seconds (unoptimized), ~25 seconds (TensorRT optimized)
- SD3.5 Large Turbo: ~4-6 seconds (4 steps)
- SD3.5 Medium: ~3-5 seconds

**Quality:** Decent but generally considered below FLUX.1 [dev] for photorealism and prompt adherence. SD3.5 Large is better for illustration, concept art, and stylized work. Medium is surprisingly capable for its size.

**NSFW/Adult:** Not censored the way SD3 was. The base models can generate detailed NSFW without modifications, a significant improvement over SD3. The Community License is more permissive than SD3's original license.

**LoRA Training:**
- AI-Toolkit: 24 GB GPU, 8-bit quantization
- Kohya: Supported
- SimpleTuner: Supported
- Civitai on-site trainer: SD3.5 Medium and Large as base models
- **Growing but smaller ecosystem than SDXL or FLUX.1**

**Inpainting/Outpainting:** Standard ComfyUI inpaint workflows. No specialized inpainting checkpoint yet.

**Text Rendering:** Below FLUX.1. Better than SDXL but not a strength.

**ComfyUI:** Full native support.

Sources:
- [SD3.5 Large HuggingFace](https://huggingface.co/stabilityai/stable-diffusion-3.5-large)
- [SD3.5 introduction](https://stability.ai/news/introducing-stable-diffusion-3-5)
- [SD3.5 TensorRT optimization](https://stability.ai/news/stable-diffusion-35-models-optimized-with-tensorrt-deliver-2x-faster-performance-and-40-less-memory-on-nvidia-rtx-gpus)
- [Stability AI Community License](https://stability.ai/license)
- [SD3.5 NSFW guide](https://apatero.com/blog/stable-diffusion-nsfw-settings-guide-2025)
- [SD3.5 LoRA training](https://x.com/ostrisai/status/1848808090730131488)

---

### 7. SDXL / Pony Diffusion V6 (Stability AI / PurpleSmart) — 2.6B / 3.5B parameters

The old guard. Still deeply relevant for specific use cases.

| Variant | Parameters | Steps | License | VRAM (FP16) | VRAM (FP8) |
|---------|-----------|-------|---------|-------------|-------------|
| SDXL 1.0 | 2.6B | 20-30 | Stability AI License | ~10 GB | ~7 GB |
| Pony Diffusion V6 XL | ~3.5B | 20-30 | Apache 2.0 | ~12 GB | ~8 GB |

**Architecture:** UNet-based latent diffusion. Dual CLIP text encoders.

**Generation Speed (1024x1024, RTX 4090):** ~3-5 seconds (20 steps). About 4x faster than FLUX.1 [dev].

**Quality:** Below FLUX.1 and most newer models for photorealism. Still excellent for stylized art, anime, illustration. Pony V6 specifically excels at character consistency and stylized content.

**NSFW/Adult:** The most mature NSFW ecosystem in existence. Pony V6 was explicitly trained on 2.6M images including explicit content. Thousands of specialized NSFW LoRAs on Civitai. Characters, poses, styles — everything is covered. No model comes close to this depth of adult content customization.

**LoRA Training:**
- The most documented training pipeline of any model
- Kohya, AI-Toolkit, SimpleTuner, FluxGym all support SDXL
- 8-12 GB VRAM sufficient for training
- Thousands of community LoRAs for every conceivable style and subject

**Inpainting/Outpainting:** Dedicated inpainting checkpoints available (JuggernautXL Inpaint, Realistic Vision Inpainting). Fooocus inpaint integration via comfyui-inpaint-nodes. Mature and reliable.

**Text Rendering:** Poor. Cannot reliably produce legible text.

**ComfyUI:** Fully mature. Largest workflow ecosystem. ControlNet, IPAdapter, AnimateDiff all have SDXL support.

**Relevance in 2026:** Still relevant for stylized art, anime, and scenarios requiring extensive LoRA customization. The ecosystem depth is unmatched. Being progressively superseded for photorealistic work.

Sources:
- [Flux vs SDXL 2026 comparison](https://pxz.ai/blog/flux-vs-sdxl)
- [Pony Diffusion V6 Civitai](https://civitai.com/models/257749/pony-diffusion-v6-xl)
- [SDXL vs Flux comparison](https://stable-diffusion-art.com/sdxl-vs-flux/)
- [Flux vs SDXL vs Pony for NSFW](https://tripleminds.co/blogs/technology/flux-vs-sdxl-vs-pony/)

---

### 8. Pony Diffusion V7 (PurpleSmart) — 7B parameters

Released November 2025. Complete rebuild on AuraFlow architecture.

| Metric | Value |
|--------|-------|
| Parameters | 7B |
| Architecture | AuraFlow-based (flow matching DiT) |
| Training Data | ~8.5-10M images (25% anime, 25% realism, 20% western cartoon, 10% pony, 10% furry, 10% misc) |
| License | Likely permissive (following V6 Apache 2.0 tradition) |
| VRAM | ~16-24 GB (AuraFlow's architectural complexity) |

**Quality:** Major upgrade from V6. Nearly triples parameter count. Better photorealism while maintaining stylized strengths.

**NSFW/Adult:** Explicitly trained on mixed SFW/NSFW content like V6. Expected to inherit the same permissive NSFW capability.

**LoRA Ecosystem:** Very new. Community building from V6 migration. Not yet comparable to V6's depth.

**ComfyUI:** Supported via AuraFlow pipeline.

Sources:
- [Pony V7 Civitai](https://civitai.com/models/1901521/pony-v7-base)
- [Pony V7 HuggingFace](https://huggingface.co/purplesmartai/pony-v7-base)
- [Pony V7 AuraFlow guide](https://apatero.com/blog/pony-diffusion-v7-auraflow-complete-guide-2025)

---

### 9. AuraFlow v0.3 (fal.ai) — 6.8B parameters

The foundation for Pony V7. A fully open competitor to SD3.

| Metric | Value |
|--------|-------|
| Parameters | 6.8B |
| Architecture | Optimized DiT with Maximal Update Parametrization, flow matching |
| License | **Apache 2.0** |
| VRAM (FP16) | ~16-24 GB |
| VRAM (FP8) | ~12 GB |
| Steps | 30-50 |

**Quality:** State-of-the-art on GenEval benchmark. Strong semantic coherence for complex multi-object compositions. Below FLUX.1 in raw photorealism but competitive in prompt adherence.

**NSFW/Adult:** Apache 2.0 means no usage restrictions. No built-in safety filters. Uncensored by design.

**LoRA Training:** Standard diffusers training. Supported by SimpleTuner.

**Text Rendering:** Moderate. Below FLUX.1.

**ComfyUI:** Supported via ComfyUI_ExtraModels and native ModelSamplingAuraFlow node. Not as seamlessly integrated as FLUX or SDXL.

**Relevance:** More important as the foundation for Pony V7 than as a standalone model. The Pony V7 fine-tune is where most users will encounter this architecture.

Sources:
- [AuraFlow HuggingFace](https://huggingface.co/fal/AuraFlow)
- [AuraFlow introduction](https://blog.fal.ai/auraflow/)
- [AuraFlow v0.3 Open Laboratory](https://openlaboratory.ai/models/auraflow-v0_3)

---

### 10. PixArt-Sigma (PixArt Team) — ~0.6B parameters

Lightweight DiT model. Released 2024. Efficient but outclassed.

| Metric | Value |
|--------|-------|
| Parameters | ~600M |
| Architecture | DiT with T5-XXL text encoder |
| License | Open (research-focused) |
| VRAM | ~6 GB (with T5 on CPU) |
| Steps | 20-30 |

**Quality:** Decent for its size. Good prompt understanding. Not competitive with FLUX, Z-Image, or HiDream in 2026.

**NSFW/Adult:** Not explicitly filtered but trained on cleaner data. Limited NSFW LoRA ecosystem.

**LoRA Training:** Minimal community support.

**ComfyUI:** Supported via ComfyUI_ExtraModels custom node. 512, 1024, and 2K checkpoints available.

**Verdict:** Historically significant as an efficient DiT pioneer but superseded by Z-Image-Turbo, FLUX.2 [klein] 4B, and SD3.5 Medium for the "small model" role.

Sources:
- [ComfyUI ExtraModels (PixArt support)](https://github.com/city96/ComfyUI_ExtraModels)
- [PixArt-Sigma ComfyUI guide](https://civitai.com/articles/5355/installing-comfyui-for-use-with-pixart-sigma)

---

### 11. Kolors (Kuaishou / Kling Team) — SDXL-scale

| Metric | Value |
|--------|-------|
| Parameters | SDXL-scale (~2.6B UNet + ChatGLM 256 text encoder) |
| Architecture | SDXL-based latent diffusion with ChatGLM text encoder |
| License | Apache 2.0 (commercial requires registration) |
| VRAM (FP16) | ~19 GB (with text encoder) |
| VRAM (Quant8) | ~8-9 GB |
| Bilingual | Chinese + English |

**Quality:** Strong photorealism and text rendering in both Chinese and English. Competitive with SDXL-class models.

**NSFW/Adult:** Not documented. Likely filtered given Chinese corporate origin.

**LoRA Training:** Supported. LoRA training code released August 2024. ControlNet, IPAdapter support included.

**ComfyUI:** Supported. One-click deployment available.

**Verdict:** Niche. Strong bilingual text rendering but not compelling enough to displace FLUX.1 or Z-Image-Turbo for English-only use. The VRAM overhead of the ChatGLM encoder is significant.

Sources:
- [Kolors GitHub](https://github.com/Kwai-Kolors/Kolors)
- [Kolors HuggingFace](https://huggingface.co/Kwai-Kolors/Kolors)

---

### 12. Playground v3 (Playground AI) — Not open-weight

**Status: NOT AVAILABLE FOR LOCAL INFERENCE.**

Playground v3 is API/platform only. No open weights released. Playground v2.5 was open-sourced but v3 is proprietary.

Text rendering score of 82% (highest among image models at time of release). Excellent quality overall. But irrelevant for Athanor since we cannot run it locally.

Sources:
- [Playground V3 technical report](https://playground.com/pg-v3)

---

### 13. Ideogram — Not open-weight

**Status: NOT AVAILABLE FOR LOCAL INFERENCE.**

Ideogram 3.0 (released May 2025) achieves 90% text rendering accuracy — the best in class. API-only access. No downloadable weights.

Irrelevant for Athanor.

Sources:
- [Ideogram 3.0 features](https://ideogram.ai/features/3.0)

---

## Comparative Analysis

### Quality Ranking (photorealism, prompt adherence, overall image quality)

1. **FLUX.2 [dev] 32B** — Current ceiling for open-weight quality (but requires aggressive quantization on consumer hardware)
2. **FLUX.1 [dev] 12B** — Battle-tested, excellent quality at FP8 on 24 GB
3. **HiDream-I1 Full 17B** — Matches FLUX.1 in quality, strong detail
4. **Z-Image-Turbo 6B** — Punches far above its weight class
5. **SD3.5 Large 8B** — Good for illustration/stylized, below FLUX for photorealism
6. **FLUX.2 [klein] 9B** — Strong middle ground
7. **Pony V7 7B** — Best for stylized/character work
8. **SDXL / Pony V6** — Dated but ecosystem compensates
9. **FLUX.2 [klein] 4B** — Impressive for 4B but visible quality gap
10. **SD3.5 Medium 2.5B** — Punchy for size, limited ceiling

### Speed Ranking (time to generate 1024x1024 on RTX 4090)

1. **Z-Image-Turbo** — ~2.3 seconds (8 steps)
2. **SDXL / Pony V6** — ~3-5 seconds (20 steps)
3. **SD3.5 Medium** — ~3-5 seconds
4. **SD3.5 Large Turbo** — ~4-6 seconds (4 steps)
5. **FLUX.2 [klein] 4B** — ~2-3 seconds (4 steps, estimated)
6. **FLUX.1 [schnell]** — ~4-5 seconds (4 steps, FP8)
7. **FLUX.1 [dev]** — ~9-15 seconds (20 steps)
8. **FLUX.2 [klein] 9B** — ~5-8 seconds (4 steps, estimated)
9. **HiDream-I1 Fast** — ~10-15 seconds
10. **HiDream-I1 Full** — ~60-85 seconds
11. **SD3.5 Large** — ~25-58 seconds

### NSFW/Adult Content Capability (ranked by ease and quality)

1. **Z-Image-Turbo** — Uncensored from factory. No mods needed. High quality NSFW.
2. **SDXL / Pony V6** — Deepest NSFW ecosystem. Thousands of specialized LoRAs. Mature.
3. **Pony V7** — Inherits NSFW training from V6 on new architecture.
4. **FLUX.1 [dev]** — Requires uncensored LoRA but works well. Growing NSFW LoRA ecosystem.
5. **SD3.5 (all variants)** — Base models handle NSFW without mods. Less community customization than SDXL.
6. **AuraFlow** — No restrictions (Apache 2.0). Limited NSFW-specific community work.
7. **HiDream-I1** — Partial. Community uncensored versions exist but full nudity still inconsistent.
8. **FLUX.2 [klein] 4B** — Apache 2.0, most modification-friendly. Community mods still early.
9. **Kolors** — Unknown/limited NSFW capability.
10. **PixArt-Sigma** — Minimal NSFW ecosystem.

### Quality-per-VRAM Ratio (best bang for your memory)

**On RTX 5090 (32 GB):**
1. **Z-Image-Turbo FP8** (~8 GB used, top-tier quality) — Leaves 24 GB free
2. **FLUX.1 [dev] FP8** (~16 GB used, top-tier quality) — Sweet spot
3. **FLUX.2 [klein] 9B FP8** (~12 GB used, strong quality)
4. **SD3.5 Large Turbo FP8** (~6-11 GB used, good quality, 4 steps)

**On RTX 4090 (24 GB):**
1. **Z-Image-Turbo FP8** (~8 GB used) — Best efficiency play
2. **FLUX.1 [dev] FP8** (~16 GB used) — Fits comfortably
3. **FLUX.2 [klein] 9B FP8** (~12 GB used)
4. **SD3.5 Medium** (~8 GB used) — Lightweight but capable

### Text Rendering (best to worst for in-image typography)

1. Playground v3 (82% accuracy — but API only)
2. Ideogram 3.0 (90% accuracy — but API only)
3. FLUX.1 [dev] / FLUX.2 [dev] — Best open-weight text rendering
4. Z-Image-Turbo — Good, below FLUX
5. HiDream-I1 — On par with FLUX
6. SD3.5 Large — Below FLUX
7. Kolors — Strong bilingual text
8. SDXL — Poor, mostly gibberish

### LoRA Training Ecosystem (maturity, tooling, community resources)

1. **SDXL / Pony V6** — Largest ecosystem. Thousands of LoRAs. Every tool supports it. 8-12 GB VRAM.
2. **FLUX.1 [dev]** — Second largest. Growing rapidly. Kohya, AI-Toolkit, SimpleTuner, FluxGym. 12-24 GB VRAM.
3. **SD3.5** — Supported by major tools. Growing but smaller community. 24 GB VRAM.
4. **HiDream-I1** — AI-Toolkit, SimpleTuner, diffusion-pipe. **Requires 48 GB for training** (deal-breaker on consumer GPUs for now).
5. **Z-Image-Turbo** — Early. Standard workflows apply but limited community resources.
6. **FLUX.2** — Very new. SimpleTuner support. Community still forming.
7. **Kolors** — LoRA training code available. Small community.
8. **AuraFlow / Pony V7** — New architecture. Ecosystem still building.

### Inpainting/Outpainting

- **FLUX.1 Kontext** — Best overall editing tool. Instruction-based, no masks needed. FP8 fits in 12 GB.
- **SDXL** — Most mature inpainting ecosystem. Dedicated inpainting checkpoints (JuggernautXL Inpaint). Fooocus integration. LanPaint support.
- **FLUX.2 [dev]** — Built-in editing capabilities including inpainting/outpainting.
- **FLUX.1 [dev]** — Standard inpaint workflows work. LanPaint supports Flux.
- **SD3.5** — Standard workflows, no specialized inpainting checkpoints yet.

---

## Recommendations for Athanor

### Primary Generation Model: FLUX.1 [dev] (FP8)

**Why:** Best balance of quality, speed, VRAM efficiency, LoRA ecosystem maturity, and NSFW capability. At FP8 (~16 GB), it runs comfortably on both the RTX 5090 and RTX 4090 with room to spare for other pipeline components. The 12B parameter sweet spot delivers excellent photorealism without requiring the aggressive quantization that FLUX.2 [dev]'s 32B demands. The uncensored LoRA ecosystem is well-established.

**RTX 5090:** ~6 seconds per image (FP8). Even faster with NVFP4 (~5 seconds).
**RTX 4090:** ~9-10 seconds per image (FP8).

### Speed Model: Z-Image-Turbo (FP8)

**Why:** When iterating fast matters more than peak quality. At ~2.3 seconds per image on RTX 4090 with only 8 GB VRAM, this is perfect for rapid prototyping, batch generation, and low-priority work. The fact that it's uncensored out of the box eliminates NSFW workflow friction entirely. Apache 2.0 license means zero commercial concerns.

### NSFW Specialization: Pony Diffusion V6 XL (or V7 as it matures)

**Why:** For EoBQ specifically, the depth of the Pony/SDXL NSFW LoRA ecosystem is unmatched. Thousands of character LoRAs, pose LoRAs, style LoRAs — all trained specifically for adult content. V6 runs on ~12 GB VRAM. When V7's LoRA ecosystem catches up, transition to it for higher quality on the same use cases.

### Editing/Inpainting: FLUX.1 Kontext [dev] (FP8)

**Why:** The best instruction-based editing model available. Character preservation across edits is critical for game asset workflows. At FP8 (~12 GB), it coexists with generation models on either GPU.

### Future Watch: FLUX.2 [dev] and Z-Image-Turbo

Z-Image-Turbo is the dark horse. If its LoRA ecosystem matures and uncensored fine-tunes multiply, it could replace FLUX.1 as the primary model — same quality tier, 5x faster, 2x less VRAM. FLUX.2 [dev] is the quality ceiling but needs community benchmarking of quantized quality vs FLUX.1 before committing.

### Not Recommended

- **HiDream-I1:** Quality is excellent but 48 GB LoRA training requirement is a deal-breaker. NSFW capability still immature. Slow generation. Revisit when 24 GB training is supported and uncensored mods improve.
- **SD3.5 Large:** Below FLUX.1 in photorealism. The Community License revenue cap is awkward. SD3.5 Medium is more interesting as a lightweight option but still below Z-Image-Turbo.
- **PixArt-Sigma:** Superseded.
- **Kolors:** Niche bilingual use case, not compelling for Athanor.
- **AuraFlow (standalone):** Use Pony V7 instead, which is a fine-tune of this architecture with better training.
- **Playground v3, Ideogram:** Not available for local inference.

---

## RTX 5090 NVFP4 Advantage

The RTX 5090's native NVFP4 support is a material advantage. Models that have NVFP4 checkpoints available as of February 2026:

- FLUX.1 (all variants)
- FLUX.2 (all variants)
- Z-Image (Qwen-Image family)
- LTX-2 (video, not image)

Running FLUX.1 [dev] in NVFP4 on the RTX 5090 could bring VRAM down to ~10 GB and speed to ~3-4 seconds — making it nearly as fast as Z-Image-Turbo while maintaining FLUX.1's superior quality. This is the best-case scenario for primary generation.

---

## LoRA Training Strategy

| Target Architecture | Best Tool | Min VRAM | Training Time | Notes |
|--------------------|-----------|-----------|--------------:|-------|
| FLUX.1 [dev] | AI-Toolkit or FluxGym | 12 GB | 40 min - 4 hrs | Best balance. FluxGym for simplicity. |
| SDXL / Pony V6 | Kohya | 8 GB | 30 min - 2 hrs | Most documented. Largest community. |
| Z-Image-Turbo | SimpleTuner | ~12 GB (est.) | TBD | Early. Standard DiT training should work. |
| SD3.5 Large | AI-Toolkit | 24 GB | 1-3 hrs | 8-bit quant fits on 24 GB. |
| HiDream-I1 | AI-Toolkit / diffusion-pipe | **48 GB** | 2-6 hrs | Not viable on consumer GPUs yet. |
| FLUX.2 [klein] 4B | SimpleTuner | ~12 GB (est.) | TBD | New. Apache 2.0 makes it training-friendly. |

For EoBQ specifically: Train character LoRAs on FLUX.1 [dev] via AI-Toolkit for photorealistic content, and on Pony V6 via Kohya for stylized/anime content. Both fit within RTX 4090's 24 GB.

---

## Open Questions

1. **FLUX.2 [dev] quantized quality:** How much quality degrades at Q4 vs FLUX.1 [dev] at FP8 needs community benchmarks. If the quantized 32B is clearly better, it changes the primary model recommendation.
2. **Z-Image-Turbo LoRA maturity:** How fast will the training ecosystem develop? If Alibaba releases official fine-tuning code, this model becomes much more compelling.
3. **HiDream 24 GB training:** When will this ship? It would unlock HiDream as a serious contender for LoRA-heavy workflows.
4. **Pony V7 NSFW LoRA migration:** How quickly will the V6 NSFW LoRA ecosystem rebuild on V7's AuraFlow architecture?
5. **NVFP4 real-world quality:** Are NVFP4 checkpoints genuinely equivalent to FP8 in quality, or is there meaningful degradation? Needs testing on our hardware.
