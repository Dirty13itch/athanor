# Video Generation Models for Local Inference

**Date:** 2026-02-16
**Status:** Complete — recommendation ready
**Supports:** ADR-006 (Creative Pipeline)
**Depends on:** ADR-004 (Node Roles), `2026-02-16-image-generation-models.md`

---

## The Question

Which video generation models should Athanor run locally via ComfyUI on Node 2? The target hardware is an RTX 5090 (32 GB) as the primary creative GPU. Models must support text-to-video (T2V) and image-to-video (I2V), run at reasonable speed, and be capable of generating uncensored adult content for Empire of Broken Queens.

---

## Hardware Context

- **RTX 5090** — 32 GB GDDR7, Blackwell sm_120, native NVFP4, 1792 GB/s bandwidth
- **RTX 4090** — 24 GB GDDR6X (on Node 1 post-move, available for video gen in Beast/Training mode)
- ComfyUI is the primary framework. All models must have ComfyUI support.
- Video gen is sequential with image gen — they share the 5090, not concurrent.

---

## Model-by-Model Analysis

### 1. Wan2.1 / Wan2.2 (Alibaba Tongyi Lab) — THE PRIMARY CANDIDATE

The Wan family is the dominant open-weight video generation model as of early 2026.

#### Wan2.1

| Variant | Parameters | Modes | Resolution | Duration | License |
|---------|-----------|-------|------------|----------|---------|
| Wan2.1-T2V-1.3B | 1.3B | Text-to-Video | 480p | 5s | Apache 2.0 |
| Wan2.1-T2V-14B | 14B | Text-to-Video | 480p–720p | 5s | Apache 2.0 |
| Wan2.1-I2V-14B | 14B | Image-to-Video | 480p–720p | 5s | Apache 2.0 |
| Wan2.1-VACE-14B | 14B | Video editing, inpainting, outpainting | 480p–720p | 5s | Apache 2.0 |

#### Wan2.2 (successor, released mid-2025)

| Variant | Parameters | Architecture | Resolution | Duration | License |
|---------|-----------|-------------|------------|----------|---------|
| Wan2.2-T2V-A14B | 27B total / 14B active | MoE (2 experts) | 480p–720p | 5s | Apache 2.0 |
| Wan2.2-I2V-A14B | 27B total / 14B active | MoE (2 experts) | 480p–720p | 5s | Apache 2.0 |
| Wan2.2-TI2V-5B | 5B | Dense | 480p–720p | 5s | Apache 2.0 |

**Architecture:** Wan2.2 uses a two-expert MoE design — a high-noise expert for early denoising (overall layout/composition) and a low-noise expert for later stages (fine detail). 14B active per step, 27B total. GPU memory stays roughly the same as Wan2.1-14B since only one expert is active at a time.

**VRAM Requirements:**

| Model | FP16 | FP8 | GGUF Q4 | Fits 32 GB? | Fits 24 GB? |
|-------|------|-----|---------|-------------|-------------|
| Wan2.1-T2V-1.3B | ~8 GB | ~5 GB | ~3 GB | Yes | Yes |
| Wan2.1-T2V-14B | ~28 GB | ~16 GB | ~10 GB | Yes (FP8) | Yes (FP8, tight) |
| Wan2.2-T2V-A14B | ~28 GB* | ~16 GB* | ~10 GB | Yes (FP8) | Yes (FP8, tight) |
| Wan2.2-TI2V-5B | ~12 GB | ~7 GB | ~4 GB | Yes | Yes |

*Only one expert active at a time, so effective VRAM ≈ Wan2.1-14B despite 27B total params.

**Generation Speed (5s clip, 480p):**

| GPU | Model | Precision | Time | Clips/hour |
|-----|-------|-----------|------|------------|
| RTX 4090 | Wan2.1-T2V-1.3B | FP16 | ~4 min | ~15 |
| RTX 4090 | Wan2.1-T2V-14B | FP8 | ~4.4 min | ~13 |
| RTX 5090 | Wan2.1-T2V-14B | FP8 | ~2-2.5 min | ~25 |
| RTX 5090 | Wan2.2-T2V-A14B | FP8 | ~2-2.5 min | ~25 |

Sources:
- [Wan2.1 GitHub](https://github.com/Wan-Video/Wan2.1)
- [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- [Wan2.1 Performance Testing Across GPUs](https://www.instasd.com/post/wan2-1-performance-testing-across-gpus)
- [SaladCloud Wan2.1 Benchmarks](https://blog.salad.com/benchmarking-wan2-1/)
- [Wan2.2 ComfyUI Official Workflow](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [Wan2.2-T2V-A14B HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B)

**Quality:** State-of-the-art for open-weight video generation. Trained on 1.5 billion videos and 10 billion images. Temporal consistency and motion quality are the best available in the open-weight space. The 14B model significantly outperforms the 1.3B variant in motion coherence, detail, and prompt adherence.

**NSFW/Adult Content:** The base Wan models have minimal content filtering. The Apache 2.0 license places no restrictions on content type. Community has embraced this heavily:
- [NSFW_Wan_1.3b](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b) — dedicated NSFW fine-tune of 1.3B
- Wan2.2 Remix workflows for uncensored I2V on [Civitai](https://civitai.com/articles/24518/nsfw-image-to-video-with-wan-22-the-idiots-guide)
- LoRA fine-tunes for adult content available
- "Realistic skin textures, fluid motion, and accurate anatomy" reported for NSFW use cases

Sources:
- [Wan NSFW Video Guide](https://www.nsfwwan.video/en/blog/wan-ai-nsfw-article)
- [Wan2.2 Uncensored ComfyUI Tutorial](https://www.nextdiffusion.ai/tutorials/creating-uncensored-videos-with-wan22-remix-in-comfyui-i2v)
- [Wan 2.1 Uncensored Setup Guide](https://www.promptus.ai/blog/wan-2-1-local-ai-video-uncensored-generation-setup)

**LoRA Training:** Supported via DiffSynth-Studio. The 1.3B model is practical for consumer GPU training. 14B requires significant VRAM (48 GB+) for full fine-tuning; LoRA is more practical.

**ComfyUI:** First-class native support for both Wan2.1 and Wan2.2. Official workflows from Comfy team. GGUF quantized versions available for low-VRAM setups. Kijai custom nodes widely used.

**Verdict:** The clear primary video generation model. Wan2.2-T2V-A14B (or Wan2.1-T2V-14B) at FP8 on the RTX 5090 is the target configuration. 480p-720p, 5-second clips, ~2.5 minutes per clip. The NSFW ecosystem is the most mature of any video gen model.

---

### 2. LTX-2 (Lightricks) — 19B parameters

The first production-ready open-source model combining 4K video + synchronized audio generation.

| Spec | Value |
|------|-------|
| Parameters | 19B |
| Architecture | DiT-based audio-video foundation model |
| Resolution | Up to 4K at 50 FPS |
| Duration | Up to 20 seconds |
| Audio | Synchronized audio generation (dialogue, ambience, music) |
| License | Apache 2.0 |

**VRAM Requirements:**

| Precision | VRAM | Resolution | Notes |
|-----------|------|------------|-------|
| BF16 | ~38 GB+ | 4K | Exceeds RTX 5090 |
| FP8 | ~20-21 GB | 720p | Fits RTX 4090/5090 |
| NVFP4 | ~12-16 GB | 720p-1080p | RTX 50-series only |
| FP8 | ~12-16 GB | 480p-576p | Budget GPUs |

**Generation Speed:**

| GPU | Config | Time | Output |
|-----|--------|------|--------|
| RTX 4090 | FP8, 720p, 4s | 3-5 min | 4-second clip with audio |
| RTX 4090 | FP8, 480p, 10s | <1 min | 10-second clip |
| RTX 5090 | NVFP4, 720p | ~2-3 min (est.) | With audio sync |

Sources:
- [LTX-2 Official Site](https://ltx-2.ai/)
- [LTX-2 GitHub](https://github.com/Lightricks/LTX-2)
- [LTX-2 VRAM Requirements](https://wavespeed.ai/blog/posts/blog-ltx-2-vram-requirements/)
- [NVIDIA LTX-2 ComfyUI Guide](https://www.nvidia.com/en-us/geforce/news/rtx-ai-video-generation-guide/)
- [ComfyUI-LTXVideo Plugin](https://github.com/Lightricks/ComfyUI-LTXVideo)

**Quality:** Native 4K output is unique among open-weight models. Synchronized audio generation is the killer feature — no other open-weight model produces video + sound in one pass. Motion quality is strong but slightly below Wan2.2 for complex scenes.

**NSFW/Adult Content:** Apache 2.0 license, no content restrictions. Base model has no hard safety filters. Community modifications expected. Less mature NSFW ecosystem than Wan due to newer release (January 2026).

**LoRA Training:** Official LoRA trainer included in the repository. Training code fully open.

**ComfyUI:** Dedicated plugin (ComfyUI-LTXVideo). NVFP4 and NVFP8 quantized checkpoints available.

**Verdict:** The future of video gen. Audio sync is game-changing for cinematic content (EoBQ cutscenes). 4K output when you need it. But Wan2.2 has a more mature ecosystem and better NSFW support today. LTX-2 is the secondary model — use it when audio matters or when 4K is needed.

---

### 3. HunyuanVideo 1.5 (Tencent) — 8.3B parameters

| Spec | Value |
|------|-------|
| Parameters | 8.3B |
| Resolution | Up to 720p |
| Duration | Up to ~10s |
| Modes | T2V, I2V, step-distilled variants |
| License | Tencent Hunyuan Community License (commercial OK) |

**VRAM Requirements:**

| Config | VRAM | Notes |
|--------|------|-------|
| FP16, 720p | ~14 GB peak | With model offloading |
| Step-distilled 480p | ~10-13 GB | 8-12 steps, 75% faster |
| WanGP optimized | ~6 GB | Extreme low-VRAM option |

Sources:
- [HunyuanVideo 1.5 GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)
- [HunyuanVideo 1.5 HuggingFace](https://huggingface.co/tencent/HunyuanVideo-1.5)
- [HunyuanVideo 1.5 Consumer GPU Coverage](https://studio.aifilms.ai/blog/tencent-hunyuanvideo-1-5-lightweight-video-generation)

**Quality:** Competitive with Wan2.1 in visual quality. Step-distilled variant reduces generation time by 75% with comparable quality. The 8.3B size is a sweet spot — smaller than Wan2.1-14B but much better than 1.3B models.

**NSFW/Adult Content:** Chinese corporate origin suggests filtered training data. No established NSFW community ecosystem. Not recommended for adult content.

**ComfyUI:** Supported via Diffusers and native ComfyUI workflows.

**Verdict:** Strong mid-range option. The step-distilled variant is very fast at ~10-13 GB. Good for rapid iteration on SFW content. But the lack of NSFW ecosystem and slightly lower quality ceiling than Wan2.2-14B make it a secondary choice for Athanor.

---

### 4. CogVideoX 1.5 (ZhiPu/THUDM) — 5B parameters

| Spec | Value |
|------|-------|
| Parameters | 5B |
| Resolution | Up to 1360x720 |
| Duration | 6 seconds |
| Modes | T2V, I2V |
| License | Apache 2.0 (CogVideoX-5B) |

**VRAM Requirements:**

| Config | VRAM | Notes |
|--------|------|-------|
| FP16, no optimization | ~34 GB (transformer) + 68 GB peak (VAE) | Impractical on consumer GPUs |
| With CPU offload + VAE slicing | ~5 GB | Very slow |
| Optimized (RTX 4090) | ~16 GB | 15 minutes per video |
| PytorchAO quantized | <12 GB | Runs on T4/free Colab |

Sources:
- [CogVideoX VRAM Discussion](https://github.com/THUDM/CogVideo/issues/471)
- [CogVideoX-5B HuggingFace](https://huggingface.co/zai-org/CogVideoX-5b)
- [CogVideoX ComfyUI Guide](https://stable-diffusion-art.com/cogvideox/)

**Quality:** Good overall quality. Strong on stylized/animated content. 6-second generation at 720p. Below Wan2.2 and LTX-2 in motion coherence and photorealism.

**NSFW/Adult Content:** Apache 2.0 license. Chinese origin with moderate content filtering in training. Limited NSFW community work.

**ComfyUI:** Supported via custom nodes.

**Verdict:** Superseded by Wan2.2 and HunyuanVideo 1.5 in both quality and efficiency. The extreme VAE peak memory (68 GB) without optimization is a red flag for consumer hardware. Skip.

---

### 5. Mochi 1 (Genmo) — 10B parameters

| Spec | Value |
|------|-------|
| Parameters | 10B |
| Architecture | Asymmetric Diffusion Transformer (AsymmDiT) |
| Resolution | 480p |
| Duration | 5.4 seconds at 30 FPS |
| License | Apache 2.0 |

**VRAM Requirements:**

| Config | VRAM | Notes |
|--------|------|-------|
| Standard (single GPU) | ~60 GB | Needs H100 |
| BF16 optimized | ~22 GB | Slight quality drop |
| ComfyUI optimized | <20 GB | Fits RTX 4090 |
| Multi-GPU | Splits across GPUs | Complex setup |

Sources:
- [Mochi 1 GitHub](https://github.com/genmoai/mochi)
- [Mochi 1 HuggingFace](https://huggingface.co/genmo/mochi-1-preview)
- [Mochi 1 Complete Guide](https://apatero.com/blog/mochi-1-video-generation-complete-guide-2025)

**Quality:** Good motion quality and temporal consistency. Photorealistic focus — doesn't handle animated styles well. 480p cap limits utility for production work.

**NSFW/Adult Content:** Apache 2.0. No hard filters. Limited community NSFW work due to 480p resolution cap (not practical for high-quality adult content).

**ComfyUI:** Supported but requires optimization for consumer GPUs.

**Verdict:** Historically significant (largest openly released video model at launch) but outclassed. 480p cap, high VRAM needs, and limited style range make it inferior to Wan2.2 and LTX-2. Skip.

---

### 6. AnimateDiff (Community) — Add-on for image gen models

| Spec | Value |
|------|-------|
| Parameters | Small (motion module only) |
| Base Models | SDXL, SD1.5 |
| Resolution | Inherits from base model |
| Duration | 2-4 seconds typically |
| License | Apache 2.0 |

**VRAM:** ~8-12 GB (base model + motion module). Runs on RTX 3060+.

**How it works:** Injects temporal attention layers into existing image generation checkpoints. Uses the same LoRAs and checkpoints as the base image model, adding motion.

**Quality:** Good for short animations from existing image workflows. Motion quality below dedicated video gen models. Temporal consistency degrades quickly past 2-3 seconds.

**NSFW/Adult Content:** Inherits from base model. If using Pony V6 or uncensored SDXL checkpoints, all NSFW LoRAs work. This is the easiest path to NSFW video from an existing SDXL pipeline.

**ComfyUI:** Mature support via AnimateDiff-Evolved nodes.

Sources:
- [AnimateDiff GitHub](https://github.com/guoyww/AnimateDiff)
- [Consumer GPU Video Generation Guide](https://apatero.com/blog/consumer-gpu-video-generation-complete-guide-2025)

**Verdict:** Not a standalone video gen model, but useful as a bridge from existing SDXL/Pony V6 workflows. For EoBQ, AnimateDiff + Pony V6 can produce short NSFW animations using the massive existing LoRA ecosystem. Consider as a complement to Wan2.2, not a replacement.

---

### 7. Other Notable Models

| Model | Params | Key Feature | VRAM | Status | Why Skip |
|-------|--------|-------------|------|--------|----------|
| SkyReels V1 | ~14B | Cinematic realism | ~24 GB | Released 2026 | Too new, limited ecosystem |
| MAGI-1 (SandAI) | 24B | Long-form (>1 min) | ~48 GB+ | Released 2025 | Too large for consumer GPU |
| Open-Sora 1.2 | Various | Meta's Sora alternative | ~16-24 GB | Stale (2024) | Superseded by Wan2.2 |
| Waver 1.0 | ~8B | Fast inference | ~12 GB | Released 2026 | Early, limited ComfyUI support |

Sources:
- [Best Open Source Video Gen Models 2026](https://www.hyperstack.cloud/blog/case-study/best-open-source-video-generation-models)
- [Pixazo Top 10 Video Gen Models](https://www.pixazo.ai/blog/best-open-source-ai-video-generation-models)

---

## Comparative Analysis

### Quality Ranking (motion coherence, photorealism, temporal consistency)

1. **Wan2.2-A14B** — Best overall open-weight video quality
2. **LTX-2 19B** — Close second, with audio advantage
3. **Wan2.1-14B** — Slightly below Wan2.2 but very mature
4. **HunyuanVideo 1.5** — Strong mid-range
5. **CogVideoX 1.5 5B** — Good but outclassed
6. **Mochi 1** — Good motion but 480p cap
7. **Wan2.1-1.3B** — Usable for rapid prototyping
8. **AnimateDiff** — Short animations only

### Speed Ranking (time per 5s clip at 480p on RTX 5090)

1. **Wan2.1-T2V-1.3B** — ~2 min (fast model, lower quality)
2. **HunyuanVideo 1.5 step-distilled** — ~2-3 min
3. **Wan2.2-A14B / Wan2.1-14B** — ~2.5 min
4. **LTX-2** — ~3-5 min (more complex pipeline with audio)
5. **CogVideoX 1.5** — ~10-15 min (needs heavy optimization)
6. **Mochi 1** — ~15+ min (high VRAM, slow)

### NSFW Capability (ranked by maturity and quality)

1. **Wan2.1/2.2** — Most mature NSFW video gen ecosystem. Dedicated fine-tunes, LoRAs, community workflows. Factory-uncensored under Apache 2.0.
2. **AnimateDiff + Pony V6** — Inherits the deepest NSFW LoRA ecosystem from SDXL. Short clips only.
3. **LTX-2** — Apache 2.0, no filters. Very new — NSFW community still forming.
4. **Mochi 1** — Apache 2.0, but 480p resolution limits NSFW utility.
5. **HunyuanVideo / CogVideoX** — Chinese corporate origin, filtered training. Not NSFW-friendly.

### VRAM Efficiency (quality per GB on RTX 5090)

| Model | Best Precision | VRAM Used | Quality Tier |
|-------|---------------|-----------|-------------|
| Wan2.2-A14B FP8 | FP8 | ~16 GB | Top |
| HunyuanVideo 1.5 distilled | FP16 | ~13 GB | Strong |
| Wan2.1-1.3B FP16 | FP16 | ~8 GB | Good (fast) |
| LTX-2 FP8 | FP8 | ~20 GB | Top (with audio) |
| Wan2.2-TI2V-5B | FP8 | ~7 GB | Good |

---

## Recommendations for Athanor

### Primary: Wan2.2-T2V-A14B (FP8 on RTX 5090)

**Why:** Best overall quality, most mature NSFW ecosystem, Apache 2.0, ~16 GB VRAM at FP8 leaves headroom on the 32 GB 5090. The MoE architecture (27B total / 14B active) gives Wan2.2-level quality at Wan2.1-level VRAM cost. ~25 clips/hour at 480p.

**Use for:** Primary video generation, EoBQ cinematics, uncensored content, I2V from Flux-generated stills.

### Speed Model: Wan2.1-T2V-1.3B (FP16 on RTX 5090)

**Why:** Only ~8 GB VRAM, generates quickly. Perfect for rapid iteration, previewing compositions, and batch generation. Quality is noticeably below the 14B model but acceptable for drafts.

**Use for:** Rapid prototyping, testing prompts before committing to the 14B model.

### Audio+Video: LTX-2 (FP8 on RTX 5090)

**Why:** The only open-weight model that generates synchronized audio + video. Critical for cinematic EoBQ content where dialogue, ambience, and music matter. At FP8 (~20 GB) it fits on the 5090.

**Use for:** Cinematic content with audio, promotional material, any video where sound is integral.

### NSFW Animation Bridge: AnimateDiff + Pony V6

**Why:** Leverages the existing Pony V6 NSFW LoRA ecosystem for short animated clips. No new model download needed — uses existing ComfyUI checkpoints and LoRAs from image gen.

**Use for:** Short NSFW character animations, expression changes, simple motion from existing character LoRAs.

### Not Recommended

- **CogVideoX 1.5** — 68 GB VAE peak without optimization. Superseded by Wan2.2.
- **Mochi 1** — 480p cap, 60 GB default VRAM. No advantage over Wan2.2.
- **HunyuanVideo** — Good model, but no NSFW ecosystem. Use Wan2.2 instead.
- **Open-Sora** — Stale project, superseded.
- **MAGI-1** — 48 GB+ VRAM, too large.

---

## Pipeline Integration with Image Gen

The video gen workflow builds on the image generation pipeline:

1. **Generate still** with FLUX.1 [dev] or Z-Image-Turbo (image gen model)
2. **Animate still** with Wan2.2-I2V-A14B (image-to-video)
3. **Edit result** with FLUX.1 Kontext (if frame corrections needed)
4. **Add audio** with LTX-2 (if synchronized sound needed)

For EoBQ specifically:
- Character portraits (Flux) → animate expressions/gestures (Wan2.2 I2V) → add voice/ambience (LTX-2)
- Scene backgrounds (Flux) → animate environment (Wan2.2 T2V) → add ambient sound (LTX-2)

All models share the RTX 5090 sequentially via ComfyUI workflow orchestration.

---

## Open Questions

1. **Wan2.2 NVFP4 performance** — NVFP4 checkpoints would cut VRAM further and potentially speed up generation on Blackwell. Status unknown.
2. **LTX-2 NSFW maturity** — How quickly will the community produce NSFW-optimized LTX-2 workflows? Audio sync for adult content is a compelling feature.
3. **LoRA training for Wan2.2** — Can we train character-specific LoRAs for EoBQ on the RTX 5090 (32 GB)?
4. **Wan2.2 vs HunyuanVideo step-distilled head-to-head** — For non-NSFW content, HunyuanVideo's 75% speed improvement may be worth the quality tradeoff.
5. **Multi-clip coherence** — None of these models handle multi-clip narrative consistency. Need to evaluate agent-orchestrated approaches for longer sequences.
