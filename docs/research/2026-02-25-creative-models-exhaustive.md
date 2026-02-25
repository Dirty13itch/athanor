# Creative AI Models: Exhaustive Survey (Dec 2025 - Feb 2026)

**Date:** 2026-02-25
**Status:** Complete -- comprehensive survey
**Supersedes:** `2026-02-16-image-generation-models.md`, `2026-02-16-video-generation-models.md` (which remain valid but predate many models listed here)
**Supports:** ADR-006 (Creative Pipeline), future Tier 6 build decisions

---

## Context

This is an exhaustive catalog of every notable creative AI model released or significantly updated in the 90-day window of December 2025 through February 2026. The purpose is to identify upgrade opportunities for Athanor's creative pipeline.

**Current pipeline:**
- **T2I:** Flux Dev FP8 via ComfyUI on RTX 5060 Ti 16GB
- **T2V:** Wan2.x T2V FP8 (480x320 @17 frames, 91s) on RTX 5060 Ti 16GB
- **STT:** faster-distil-whisper-large-v3 on RTX 5070 Ti 16GB (GPU 4)
- **TTS:** wyoming-piper (CPU, en_US-lessac-medium) on VAULT
- **Music/3D/SFX:** Not deployed

**Available GPUs:**
| GPU | VRAM | Location | Current Use |
|-----|------|----------|-------------|
| 4x RTX 5070 Ti | 16GB each | Node 1 | vLLM TP=4 (GPUs 0-3), embedding+STT+TTS (GPU 4) |
| RTX 4090 | 24GB | Node 1 | vLLM TP=4 member |
| RTX 5090 | 32GB | Node 2 | vLLM single-GPU |
| RTX 5060 Ti | 16GB | Node 2 | ComfyUI (Flux + Wan2.x) |

---

## Table of Contents

1. [Image Generation (T2I)](#1-image-generation-t2i)
2. [Image Editing & Conditioning](#2-image-editing--conditioning)
3. [Video Generation (T2V / I2V)](#3-video-generation-t2v--i2v)
4. [Audio / Speech: Text-to-Speech](#4-text-to-speech-tts)
5. [Audio / Speech: Speech-to-Text](#5-speech-to-text-stt)
6. [Music Generation](#6-music-generation)
7. [Sound Effects](#7-sound-effects)
8. [3D Generation](#8-3d-generation)
9. [Singing Voice Synthesis](#9-singing-voice-synthesis)
10. [Recommendations for Athanor](#10-recommendations-for-athanor)

---

## 1. Image Generation (T2I)

### 1.1 Z-Image / Z-Image-Turbo (Alibaba Tongyi-MAI)

| Field | Value |
|-------|-------|
| **Release** | ~Nov 2025 (Z-Image), ~Jan 2026 (Z-Image-Turbo) |
| **Type** | Text-to-Image |
| **Architecture** | Scalable Single-Stream DiT (S3-DiT), 6B params |
| **Resolution** | Up to 1024x1024 |
| **Steps** | 8 NFEs (Turbo), ~25-50 (base) |
| **VRAM** | Fits in 16GB consumer GPUs |
| **Speed** | Sub-second on H800; fast on consumer GPUs |
| **License** | Apache 2.0 |
| **ComfyUI** | Via `diffusers` pipeline (ZImagePipeline) |
| **Quality** | State-of-the-art among open-source per Alibaba AI Arena Elo |
| **Key features** | Bilingual text rendering (EN/CN), 8-step generation, strong instruction adherence |
| **HuggingFace** | [Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo), [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) |
| **vs Flux Dev** | Faster (8 vs 20+ steps), smaller (6B vs 12B), bilingual text, fits 16GB. Quality competitive. |

**Verdict:** Strong upgrade candidate. Fits the 5060 Ti at 16GB, faster than Flux, bilingual text rendering. Worth testing side-by-side with Flux Dev.

---

### 1.2 Qwen-Image-2512 (Alibaba Qwen)

| Field | Value |
|-------|-------|
| **Release** | Dec 31, 2025 (HF update) |
| **Type** | Text-to-Image |
| **Architecture** | Diffusion Pipeline (diffusers-based) |
| **Resolution** | Multiple aspect ratios: 1328x1328 (1:1), 1664x928 (16:9), 928x1664 (9:16), etc. |
| **Steps** | 50 |
| **VRAM** | Not specified; bfloat16 inference, likely 16-24GB |
| **License** | Apache 2.0 |
| **ComfyUI** | Via DiffusionPipeline (diffusers); ComfyUI node likely forthcoming |
| **Quality** | "Strongest open-source model" per 10K+ blind evaluations on AI Arena |
| **Key features** | Enhanced human realism (facial detail, skin texture), improved text rendering, fine natural detail |
| **HuggingFace** | [Qwen/Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) |
| **GitHub** | [QwenLM/Qwen-Image](https://github.com/QwenLM/Qwen-Image) |
| **vs Flux Dev** | Claims superior human realism and text rendering. Model size unknown. |

**Verdict:** Promising but model size/VRAM unknown. If it fits 16GB, strong contender. Needs testing.

---

### 1.3 BitDance-14B (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.14041) |
| **Type** | Text-to-Image (discrete autoregressive) |
| **Architecture** | Fine-tuned from Qwen3-14B-Base + binary diffusion head, 15B params |
| **Resolution** | 512px and 1024px |
| **Steps** | 50 (can reduce to 25) |
| **VRAM** | ~30GB in BF16 (15B params) |
| **License** | Apache 2.0 |
| **ComfyUI** | Custom pipeline, no ComfyUI node yet |
| **Quality** | DPG-Bench: 88.28 (vs Flux Dev 83.84), GenEval: 0.86 (vs Flux 0.66) |
| **Key features** | Parallel multi-token prediction (up to 64 tokens/step), AR-based (not diffusion) |
| **HuggingFace** | [shallowdream204/BitDance-14B-16x](https://huggingface.co/shallowdream204/BitDance-14B-16x), [BitDance-14B-64x](https://huggingface.co/shallowdream204/BitDance-14B-64x) |
| **vs Flux Dev** | Significantly outperforms on benchmarks. Too large for 16GB GPU. |

**Verdict:** Benchmark king but at 30GB VRAM, only fits the 5090. AR-based architecture is novel. No ComfyUI support yet. Watch but don't deploy yet.

---

### 1.4 DeepGen-1.0 (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.12205) |
| **Type** | Text-to-Image + Image Editing (unified) |
| **Architecture** | 3B VLM + 2B DiT = 5B total, based on Qwen2.5-VL-3B |
| **Resolution** | Not specified |
| **VRAM** | Estimated 8-16GB (5B params) |
| **License** | Apache 2.0 |
| **ComfyUI** | No ComfyUI node yet |
| **Quality** | Competitive with models 3-16x larger on benchmarks; first place on reasoning image editing |
| **Key features** | 5 functions: general gen, general edit, reasoning gen, reasoning edit, text rendering |
| **HuggingFace** | [deepgenteam/DeepGen-1.0](https://huggingface.co/deepgenteam/DeepGen-1.0) |
| **vs Flux Dev** | Different category -- unified gen+edit model. Smaller but less raw image quality. |

**Verdict:** Interesting as a unified generation+editing model. 5B params likely fits 16GB. No ComfyUI node yet limits immediate usability. Niche use case.

---

### 1.5 HiDream-I1 (May 2025, updated Jul 2025)

| Field | Value |
|-------|-------|
| **Release** | May 28, 2025 (report); Jul 17, 2025 (HF full model) |
| **Type** | Text-to-Image |
| **Architecture** | Sparse Diffusion Transformer, 17B params. Text encoders: Llama-3.1-8B + T5-XXL. VAE from FLUX.1 |
| **Resolution** | Not specified (likely 1024x1024+) |
| **VRAM** | Not specified; 17B params suggests 24-34GB in FP16 |
| **License** | MIT |
| **ComfyUI** | Likely supported (shares FLUX VAE) |
| **Quality** | DPG-Bench: 85.89 (vs Flux 83.79), GenEval: 0.83 (vs Flux 0.66), HPSv2.1: 33.82 (vs 32.47) |
| **Variants** | Full (17B), Dev (distilled), Fast (distilled) |
| **HuggingFace** | [HiDream-ai/HiDream-I1-Full](https://huggingface.co/HiDream-ai/HiDream-I1-Full) |
| **vs Flux Dev** | Outperforms across all benchmarks. MIT license. But 17B params needs 24GB+ |

**Verdict:** Strong contender for the 5090 (32GB). MIT license is ideal. Outperforms Flux on all benchmarks. The Fast variant may fit smaller GPUs. Worth testing.

---

### 1.6 FHDR_Uncensored (Nov 2025)

| Field | Value |
|-------|-------|
| **Release** | November 19, 2025 |
| **Type** | Text-to-Image (uncensored fine-tune) |
| **Architecture** | Fine-tuned FLUX.1-dev, 12B params |
| **Resolution** | 1024x1024 default |
| **VRAM** | 12.7GB (Q8_0 GGUF); ~24GB full BF16 |
| **License** | Custom (requires agreement) |
| **ComfyUI** | Yes (Flux-compatible) |
| **Quality** | Flux-quality with uncensored content |
| **HuggingFace** | [kpsss34/FHDR_Uncensored](https://huggingface.co/kpsss34/FHDR_Uncensored) |

**Verdict:** Relevant for EoBQ (uncensored Flux fine-tune). GGUF Q8 at 12.7GB fits the 5060 Ti. Already Flux-compatible so ComfyUI works.

---

### 1.7 Qwen Image Edit Rapid AIO (Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | Iterating through Jan 2026 (v19-v23) |
| **Type** | Image Editing + Text-to-Image |
| **Architecture** | Merged Qwen Image Edit + accelerators + VAE + CLIP |
| **VRAM** | Not specified; FP8, 4 steps |
| **License** | Apache 2.0 |
| **ComfyUI** | Yes (primary usage via ComfyUI nodes) |
| **Key features** | 4-step image editing, NSFW/SFW variants, multi-image input |
| **HuggingFace** | [Phr00t/Qwen-Image-Edit-Rapid-AIO](https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO) |

**Verdict:** Useful for image editing workflows in ComfyUI. Creator is winding down updates.

---

## 2. Image Editing & Conditioning

### 2.1 Flux ControlNet Upscaler (jasperai)

| Field | Value |
|-------|-------|
| **Updated** | Mar 2025 (still actively used) |
| **Type** | Image upscaling via ControlNet |
| **Architecture** | Flux.1-dev + ControlNet conditioning |
| **HuggingFace** | [jasperai/Flux.1-dev-Controlnet-Upscaler](https://huggingface.co/jasperai/Flux.1-dev-Controlnet-Upscaler) |
| **Downloads** | 3.23K/month, 857 likes |

### 2.2 Qwen-Based Upscalers (Dec 2025 - Jan 2026)

Several Qwen-Image-Edit-based upscaling models emerged:
- `valiantcat/Qwen-Image-Edit-2511-Upscale2K` (Dec 29, 2025)
- `starsfriday/Qwen-Image-Edit-2511-Upscale2K` (Dec 29, 2025)
- `vafipas663/Qwen-Edit-2509-Upscale-LoRA` (Nov 17, 2025)
- `prithivMLmods/Qwen-Image-Edit-2511-Unblur-Upscale` (Jan 15, 2025)

These are fine-tuned for 2K upscaling and deblurring tasks.

### 2.3 HiDream-E1 (Jul 2025) -- Image Editing

| Field | Value |
|-------|-------|
| **Release** | Jul 17, 2025 |
| **Type** | Any-to-Any image editing |
| **License** | Not specified |
| **HuggingFace** | [HiDream-ai/HiDream-E1-Full](https://huggingface.co/HiDream-ai/HiDream-E1-Full) |

### 2.4 HiDream VAREdit (Feb 2026) -- Image Editing

| Field | Value |
|-------|-------|
| **Release** | ~Feb 4, 2026 |
| **Type** | Image-to-Image editing |
| **HuggingFace** | [HiDream-ai/VAREdit](https://huggingface.co/HiDream-ai/VAREdit) |

---

## 3. Video Generation (T2V / I2V)

### 3.1 Wan2.2 (Alibaba Wan-AI, Jul 2025)

| Field | Value |
|-------|-------|
| **Release** | July 28, 2025 |
| **Type** | T2V, I2V, TI2V |
| **Architecture** | MoE (2 experts): 27B total, 14B active. New: Wan2.2-VAE with 16x16x4 compression |
| **Resolution** | 480p, 720p (1280x704) |
| **FPS** | 24 |
| **Duration** | 5 seconds |
| **VRAM** | TI2V-5B: 24GB min (offloading). A14B: 80GB+ recommended |
| **License** | Apache 2.0 |
| **ComfyUI** | Pending (on Wan2.2 roadmap), Wan2.1 nodes work for some variants |
| **Models** | T2V-A14B (MoE), I2V-A14B (MoE), TI2V-5B (dense) |
| **HuggingFace** | [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B), [Wan-AI/Wan2.2-T2V-A14B](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) |
| **GitHub** | [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2) |
| **vs Wan2.1** | +65.6% more training images, +83.2% more training videos, MoE architecture, cinematic aesthetics, improved motion |

**Verdict:** Major upgrade over current Wan2.x deployment. TI2V-5B is the consumer-friendly option (24GB min). A14B models need multi-GPU. ComfyUI integration pending. The 5060 Ti (16GB) cannot run TI2V-5B without heavy offloading. The 5090 (32GB) or 4090 (24GB) could.

---

### 3.2 Wan2.2-Lightning (Aug 2025)

| Field | Value |
|-------|-------|
| **Release** | Aug 4-8, 2025 |
| **Type** | Distilled Wan2.2 for fast inference |
| **Architecture** | LoRA adapters on Wan2.2-A14B (T2V and I2V) |
| **Speed** | 20x faster than base Wan2.2, only 4 inference steps |
| **Resolution** | 480p, 720p |
| **VRAM** | 80GB+ (same base model size) |
| **License** | Apache 2.0 |
| **ComfyUI** | Native ComfyUI workflows released Aug 8, 2025 |
| **HuggingFace** | [lightx2v/Wan2.2-Lightning](https://huggingface.co/lightx2v/Wan2.2-Lightning) |
| **GitHub** | [ModelTC/Wan2.2-Lightning](https://github.com/ModelTC/Wan2.2-Lightning) |

**Verdict:** Impressive speed (4 steps) but requires 80GB VRAM for the A14B base. Not viable on current hardware without heavy offloading.

---

### 3.3 Wan2.2-14B-Rapid-AllInOne (Phr00t, Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | ~Feb 19, 2026 |
| **Type** | Merged all-in-one T2V + I2V + VACE |
| **Architecture** | Merged Wan2.2 variants, FP8 |
| **VRAM** | As low as 8GB (confirmed working) |
| **Steps** | 4 steps, CFG=1 |
| **License** | Not specified |
| **ComfyUI** | Primary usage via ComfyUI ("Load Checkpoint" node) |
| **Status** | Deprecated by creator |
| **HuggingFace** | [Phr00t/WAN2.2-14B-Rapid-AllInOne](https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne) |

**Verdict:** Compelling for the 5060 Ti (16GB) -- claims 8GB min VRAM. FP8, 4 steps, all-in-one. Despite being deprecated, it's a practical option for consumer hardware.

---

### 3.4 HunyuanVideo-1.5 (Tencent, Nov 2025)

| Field | Value |
|-------|-------|
| **Release** | November 20, 2025 |
| **Type** | T2V + I2V |
| **Architecture** | 8.3B-parameter DiT with 3D causal VAE + SSTA attention |
| **Resolution** | 480p, 720p (upscalable to 1080p via built-in VSR) |
| **FPS** | 24 |
| **Duration** | ~5 seconds (121 frames) |
| **VRAM** | 14GB minimum (with offloading); 480p I2V step-distilled: ~75s on single RTX 4090 |
| **License** | Tencent-Hunyuan Community License |
| **ComfyUI** | Diffusers integration available |
| **Speed** | 1.87x speedup via SSTA; 75% speedup with step-distilled model (8-12 steps) |
| **Key features** | FP8 GEMM, training code + LoRA fine-tuning, diffusers integration, VSR upscaling |
| **HuggingFace** | [tencent/HunyuanVideo-1.5](https://huggingface.co/tencent/HunyuanVideo-1.5) |
| **GitHub** | [Tencent-Hunyuan/HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) |

**Verdict:** Strong contender. 14GB minimum VRAM means it fits the 5060 Ti with offloading. Step-distilled 480p I2V model is fast (75s on 4090). Built-in 1080p upscaling is a differentiator. Tencent community license may be restrictive for some uses.

---

### 3.5 LTX-2 (Lightricks, Jan 2025)

| Field | Value |
|-------|-------|
| **Release** | January 6, 2025 (arXiv: 2601.03233) |
| **Type** | Joint audio-video generation (T2V, I2V, V2V, T2A, A2V) |
| **Architecture** | 19B-parameter DiT |
| **Resolution** | Width/height divisible by 32, frames divisible by 8+1 |
| **VRAM** | FP8 and FP4 quantized variants available |
| **License** | LTX-2 Community License |
| **ComfyUI** | Built-in LTXVideo nodes in ComfyUI Manager |
| **Key features** | Joint audio+video generation, spatial+temporal upscalers, LoRA training (<1hr) |
| **Variants** | ltx-2-19b-dev, ltx-2-19b-dev-fp8, ltx-2-19b-dev-fp4, ltx-2-19b-distilled, spatial-upscaler-x2, temporal-upscaler-x2 |
| **HuggingFace** | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) |

**Verdict:** Unique joint audio+video generation. FP4 variant could fit smaller GPUs. ComfyUI supported natively. The upscaler models are valuable standalone. License may be restrictive.

---

### 3.6 MOVA (OpenMOSS, Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.08794) |
| **Type** | Simultaneous video + audio generation (T2VA, IT2VA) |
| **Architecture** | Asymmetric Dual-Tower (MoE): 32B total, 18B active |
| **Resolution** | 360p (MOVA-360p), 720p (MOVA-720p) |
| **License** | Apache 2.0 |
| **Key features** | Synchronized video+audio, lip-sync, sound FX, LoRA fine-tuning |
| **HuggingFace** | [OpenMOSS-Team/MOVA-360p](https://huggingface.co/OpenMOSS-Team/MOVA-360p), [OpenMOSS-Team/MOVA-720p](https://huggingface.co/OpenMOSS-Team/MOVA-720p) |
| **GitHub** | [OpenMOSS/MOVA](https://github.com/OpenMOSS/MOVA) |

**Verdict:** First open-source synchronized video+audio model. 18B active params means 36GB+ VRAM at BF16. 360p variant might fit 24GB with quantization. Groundbreaking but likely too large for current hardware at quality resolutions.

---

### 3.7 Mirage-T2V-14B-MoE (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | ~Feb 21, 2026 |
| **Type** | T2V |
| **Architecture** | MoE: 27B total, 14B active |
| **Resolution** | 480p, 720p |
| **Duration** | 5 seconds |
| **VRAM** | 24GB+ recommended |
| **License** | Apache 2.0 |
| **HuggingFace** | [gomirageai/Mirage-T2V-14B-MoE](https://huggingface.co/gomirageai/Mirage-T2V-14B-MoE) |

**Verdict:** Yet another Wan2.2-class MoE video model. Likely based on or inspired by Wan2.2. 24GB+ VRAM needed.

---

### 3.8 LongCat-Video (Meituan, Oct 2025)

| Field | Value |
|-------|-------|
| **Release** | October 25, 2025 (arXiv: 2510.22200) |
| **Type** | T2V, I2V, Video Continuation |
| **Architecture** | 13.6B dense (not MoE), FlashAttention-2 |
| **Resolution** | 720p |
| **FPS** | 30 |
| **Duration** | Minutes-long videos without quality degradation |
| **VRAM** | Not specified (13.6B dense = ~27GB BF16) |
| **License** | MIT |
| **Key features** | Long video generation (minutes), video continuation, block sparse attention |
| **HuggingFace** | [meituan-longcat/LongCat-Video](https://huggingface.co/meituan-longcat/LongCat-Video) |

**Verdict:** Unique long-form video capability. 30 FPS. MIT license. 13.6B dense likely needs 24-32GB. The video continuation feature is valuable for EoBQ cinematics.

---

## 4. Text-to-Speech (TTS)

### 4.1 Qwen3-TTS (Alibaba Qwen, Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | January 22, 2026 (arXiv: 2601.15621) |
| **Type** | TTS (multilingual, instruction-controllable) |
| **Architecture** | End-to-end discrete multi-codebook LM, 1.7B / 0.6B params |
| **Sample Rate** | 12Hz tokenizer (12.5 FPS acoustic) |
| **Languages** | 10 (CN, EN, JA, KO, DE, FR, RU, PT, ES, IT) |
| **Latency** | 97ms streaming (first packet) |
| **VRAM** | ~3-4GB (1.7B BF16), ~1.5-2GB (0.6B) |
| **License** | Apache 2.0 |
| **Key features** | 9 premium voices, voice cloning (3s ref audio), voice design from text description, instruction control (emotion/tone), streaming |
| **Variants** | CustomVoice (1.7B/0.6B), VoiceDesign (1.7B), Base (1.7B/0.6B) |
| **HuggingFace** | [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) |
| **Benchmarks** | SEED-TTS WER (EN): 1.24 (best-in-class); streaming latency: 97ms |
| **vs Piper** | Vastly superior: multilingual, voice cloning, emotion control, GPU-accelerated |
| **vs XTTS-v2** | Superior streaming (97ms), better instruction control, voice design from text |

**Verdict:** MASSIVE upgrade over current Piper deployment. 3-4GB VRAM fits easily on GPU 4 alongside other services. Voice cloning, emotion control, 10 languages, 97ms streaming. Apache 2.0. This should be the next TTS deployment.

---

### 4.2 MOSS-TTS (OpenMOSS, Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 |
| **Type** | TTS (production-grade) |
| **Architecture** | Delay Pattern (8B) or Global Latent + Local Transformer (1.7B) |
| **Languages** | 20 languages |
| **VRAM** | ~20-40GB (8B), ~8-16GB (1.7B) |
| **License** | Apache 2.0 |
| **Key features** | Zero-shot voice cloning, 1-hour stable generation, duration control, phoneme control (Pinyin/IPA), code-switching |
| **Variants** | MossTTSDelay-8B (production), MossTTSLocal-1.7B (research), MOSS-TTS-Realtime (2B) |
| **HuggingFace** | [OpenMOSS-Team/MOSS-TTS](https://huggingface.co/OpenMOSS-Team/MOSS-TTS) |
| **GitHub** | [OpenMOSS/MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS) |

**Verdict:** Strong contender. 20 languages, 1-hour generation, voice cloning. The 1.7B model fits 16GB GPU. The 8B production model is too large for consumer GPUs. More languages than Qwen3-TTS but larger models.

---

### 4.3 Microsoft VibeVoice-Realtime-0.5B (Dec 2025)

| Field | Value |
|-------|-------|
| **Release** | December 2025 |
| **Type** | Real-time TTS |
| **Architecture** | Qwen2.5-0.5B backbone + sigma-VAE tokenizer + diffusion head |
| **VRAM** | ~2-4GB estimated |
| **Latency** | ~300ms first audible |
| **Duration** | Up to ~10 minutes per generation |
| **Languages** | English only (9 others with limited support) |
| **License** | MIT |
| **Key features** | Real-time streaming text input, zero-shot speaker adaptation, watermarking |
| **Variants** | 0.5B (8K ctx), 1.5B (64K ctx, ~90min), Large (32K ctx, ~45min) |
| **HuggingFace** | [microsoft/VibeVoice-Realtime-0.5B](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B) |
| **GitHub** | [microsoft/VibeVoice](https://github.com/microsoft/VibeVoice) |

**Verdict:** Very lightweight, MIT license, real-time streaming. But English-only limits usefulness vs Qwen3-TTS. The 0.5B model at 2-4GB VRAM is extremely efficient.

---

### 4.4 Kokoro-82M (Jan 2025, still highly popular)

| Field | Value |
|-------|-------|
| **Release** | January 27, 2025 (v1.0) |
| **Type** | TTS |
| **Architecture** | StyleTTS 2 + ISTFTNet vocoder, 82M params |
| **VRAM** | ~2-4GB estimated |
| **Sample Rate** | 24 kHz |
| **Languages** | 8 languages, 54 voices |
| **License** | Apache 2.0 |
| **Cost** | <$1 per million characters |
| **HuggingFace** | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) |
| **Downloads** | 9.37M/month |

**Verdict:** Extremely lightweight, wide adoption. Good edge/CPU option. Lower quality than Qwen3-TTS but trivial resource usage.

---

### 4.5 Fish Audio S1-mini (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | ~Feb 2026 |
| **Type** | TTS with voice cloning and emotion control |
| **Architecture** | Distilled from S1 (4B), 0.5B params |
| **Languages** | 13 languages |
| **License** | CC-BY-NC-SA-4.0 (non-commercial) |
| **Key features** | 47+ emotion markers, voice cloning, RLHF training |
| **HuggingFace** | [fishaudio/s1-mini](https://huggingface.co/fishaudio/s1-mini) |

**Verdict:** Non-commercial license disqualifies it for most uses. Emotion marker support is impressive but Qwen3-TTS has similar capabilities with Apache 2.0.

---

### 4.6 Kani-TTS-2-EN (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 |
| **Type** | Real-time TTS |
| **Architecture** | LiquidAI LFM2 350M + NanoCodec, 400M total |
| **VRAM** | 3GB (RTX 5080) |
| **Sample Rate** | 22 kHz |
| **Languages** | English only |
| **License** | lfm1.0 (restrictive) |
| **RTF** | ~0.2 (real-time) |
| **HuggingFace** | [nineninesix/kani-tts-2-en](https://huggingface.co/nineninesix/kani-tts-2-en) |

**Verdict:** Lightweight, real-time, English-only. Novel LFM2 backbone. Restrictive license limits adoption.

---

### 4.7 MOSS-TTSD v1.0 -- Spoken Dialogue Generation (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 |
| **Type** | Text-to-Spoken-Dialogue |
| **Architecture** | 8B params |
| **License** | Apache 2.0 |
| **HuggingFace** | [OpenMOSS-Team/MOSS-TTSD-v1.0](https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0) |

**Verdict:** Novel -- generates multi-speaker dialogue audio. Could be interesting for EoBQ voice acting. 8B params needs 16-20GB VRAM.

---

## 5. Speech-to-Text (STT)

### 5.1 Qwen3-ASR (Alibaba Qwen, Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | ~January 29, 2026 (arXiv: 2601.21337) |
| **Type** | ASR (streaming + offline) |
| **Architecture** | Derived from Qwen3-Omni, 1.7B / 0.6B params |
| **Languages** | 30 languages + 22 Chinese dialects |
| **VRAM** | ~12-16GB (1.7B BF16), ~6-8GB (0.6B) |
| **License** | Apache 2.0 |
| **Key features** | Unified streaming/offline, language ID (97.9% accuracy), timestamps via Qwen3-ForcedAligner, singing voice support, vLLM backend |
| **HuggingFace** | [Qwen/Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B), [Qwen/Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) |
| **Benchmarks** | LibriSpeech Clean: 1.63 WER (vs Whisper-v3: 1.51); LibriSpeech Other: 3.38 (vs 3.97); Chinese WenetSpeech: 4.97/5.88 (vs Whisper 9.86/19.11) |
| **vs Whisper** | Better multilingual (especially Chinese/dialects), better language ID, similar English, streaming support, vLLM deployable |

**Verdict:** Strong Whisper alternative. The 0.6B model at 6-8GB VRAM is very efficient. vLLM deployment means it can share the existing vLLM infrastructure. 30 languages vs Whisper's 99 is the main tradeoff. For English + Chinese, it's better than Whisper. Worth deploying the 0.6B alongside current Whisper.

---

### 5.2 Voxtral-Mini-4B-Realtime (Mistral, Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.11298) |
| **Type** | Real-time streaming ASR |
| **Architecture** | 3.4B LLM + 970M audio encoder = 4B total |
| **Languages** | 13 (AR, DE, EN, ES, FR, HI, IT, NL, PT, ZH, JA, KO, RU) |
| **VRAM** | 16GB+ |
| **Latency** | <500ms (configurable 80ms-2.4s delay) |
| **License** | Apache 2.0 |
| **Key features** | Natively streaming, sliding window attention for infinite streaming, vLLM deployable |
| **HuggingFace** | [mistralai/Voxtral-Mini-4B-Realtime-2602](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602) |
| **Benchmarks** | FLEURS avg WER: 8.72% (vs offline 5.90%), TEDLIUM: 3.17% |

**Verdict:** First-class streaming ASR from Mistral. 16GB VRAM is steep for ASR. Apache 2.0. The configurable latency-accuracy tradeoff is unique. vLLM deployable. Good for real-time assistant interactions.

---

### 5.3 Microsoft VibeVoice-ASR (Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | ~January 27, 2026 (arXiv: 2601.18184) |
| **Type** | Unified ASR + diarization + timestamps |
| **Architecture** | 9B params |
| **Languages** | 50+ with code-switching |
| **VRAM** | ~18GB+ (9B BF16) |
| **License** | MIT |
| **Key features** | 60-min single-pass, speaker diarization, timestamps, hotword support |
| **HuggingFace** | [microsoft/VibeVoice-ASR](https://huggingface.co/microsoft/VibeVoice-ASR) |

**Verdict:** Impressive all-in-one (ASR + diarization + timestamps in one pass). But 9B params / 18GB VRAM is large. MIT license. Best for meeting transcription use cases, not real-time assistant STT.

---

### 5.4 NVIDIA Canary-Qwen-2.5B (Dec 2025)

| Field | Value |
|-------|-------|
| **Release** | December 15, 2025 |
| **Type** | ASR + LLM post-processing |
| **Architecture** | FastConformer encoder + Qwen3-1.7B LLM = 2.5B total |
| **Languages** | English only |
| **VRAM** | Not specified; 2.5B params suggests ~5-8GB |
| **License** | CC-BY-4.0 |
| **Speed** | 418 RTFx (extremely fast) |
| **Key features** | Native punctuation/capitalization, LLM mode for transcript summarization, noise-robust |
| **HuggingFace** | [nvidia/canary-qwen-2.5b](https://huggingface.co/nvidia/canary-qwen-2.5b) |
| **Benchmarks** | LibriSpeech Clean: 1.60 WER, Other: 3.10, TEDLIUM: 2.72 |

**Verdict:** English-only but extremely fast (418x realtime). Built-in LLM for transcript post-processing is unique. CC-BY-4.0. Good for English-focused deployments. Requires NeMo framework.

---

### 5.5 NVIDIA Parakeet-TDT-0.6B-v3 (Nov 2025)

| Field | Value |
|-------|-------|
| **Release** | November 27, 2025 |
| **Type** | ASR |
| **Architecture** | 0.6B params |
| **License** | CC-BY-4.0 |
| **HuggingFace** | [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) |

---

## 6. Music Generation

### 6.1 ACE-Step v1.5 (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.00744) |
| **Type** | Text-to-Music |
| **Architecture** | Hybrid LM (0.6B-4B) + DiT (2B) |
| **VRAM** | <4GB |
| **Speed** | <2s on A100, <10s on RTX 3090 |
| **Languages** | 50+ |
| **License** | MIT |
| **Key features** | Commercial-grade, cover generation, repainting/editing, vocal-to-BGM, Chain-of-Thought composition, fine-tuning support |
| **Variants** | Base (50 steps), SFT (50 steps), Turbo (8 steps), Turbo-RL (8 steps); LM: 0.6B/1.7B/4B |
| **HuggingFace** | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5), [ACE-Step/acestep-v15-base](https://huggingface.co/ACE-Step/acestep-v15-base) |
| **Training data** | Licensed music, royalty-free, synthetic MIDI-to-audio |

**Verdict:** Extremely compelling. <4GB VRAM, MIT license, commercial-grade, <10s on 3090. This could easily run on any GPU in the cluster. Turbo variant (8 steps) is fastest. Perfect for EoBQ soundtrack generation. Deploy immediately.

---

### 6.2 HeartMuLa-oss-3B (Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | January 15, 2026 (arXiv: 2601.10547) |
| **Type** | Text-to-Music |
| **Architecture** | 4B params (F32) |
| **Languages** | 5 |
| **License** | Apache 2.0 |
| **Components** | HeartMuLa-oss-3B (gen), HeartCodec-oss (codec), HeartTranscriptor-oss (transcription) |
| **HuggingFace** | [HeartMuLa/HeartMuLa-oss-3B](https://huggingface.co/HeartMuLa/HeartMuLa-oss-3B) |
| **GitHub** | [HeartMuLa/heartlib](https://github.com/HeartMuLa/heartlib) |

**Verdict:** Larger than ACE-Step with fewer features. Apache 2.0 license. The music transcription component is unique and useful. 4B params at F32 = ~16GB VRAM, or ~8GB at FP16.

---

### 6.3 AudioX (HKUST, accepted ICLR 2026)

| Field | Value |
|-------|-------|
| **Release** | March 2025 (paper), ongoing updates |
| **Type** | Anything-to-Audio and Music |
| **Architecture** | Diffusion Transformer on Stable Audio Tools |
| **License** | CC-BY-NC-4.0 |
| **Key features** | Multimodal input (text, video, image, music, audio), 250 steps, stereo output |
| **HuggingFace** | [HKUSTAudio/AudioX](https://huggingface.co/HKUSTAudio/AudioX), [HKUSTAudio/AudioX-MAF-MMDiT](https://huggingface.co/HKUSTAudio/AudioX-MAF-MMDiT) |
| **GitHub** | [ZeyueT/AudioX](https://github.com/ZeyueT/AudioX) |

**Verdict:** Non-commercial license limits use. The video-to-audio capability is interesting for adding soundtracks to generated videos. 250 inference steps is slow.

---

## 7. Sound Effects

### 7.1 MOSS-SoundEffect (OpenMOSS, Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 |
| **Type** | Text-to-Sound Effects |
| **Architecture** | MossTTSDelay, 8B params |
| **VRAM** | ~16GB+ (8B BF16) |
| **License** | Apache 2.0 |
| **Output** | 16 kHz |
| **Key features** | Natural environments, urban sounds, animal sounds, human actions |
| **HuggingFace** | [OpenMOSS-Team/MOSS-SoundEffect](https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect) |

**Verdict:** Useful for EoBQ environmental audio and game SFX. 8B params is large (16GB+ VRAM). Apache 2.0.

---

## 8. 3D Generation

### 8.1 TRELLIS.2-4B (Microsoft, Dec 2025)

| Field | Value |
|-------|-------|
| **Release** | December 16, 2025 (arXiv: 2512.14692) |
| **Type** | Image-to-3D |
| **Architecture** | Flow-Matching Transformer + Sparse Voxel 3D VAE (O-Voxel), 4B params |
| **VRAM** | 24GB minimum |
| **Speed** | 512^3: ~3s, 1024^3: ~17s, 1536^3: ~60s (on H100) |
| **License** | MIT |
| **Output** | GLB mesh with PBR materials (including transparency) |
| **Key features** | Arbitrary topology, sharp features, PBR with opacity, optimization-free mesh conversion |
| **HuggingFace** | [microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| **GitHub** | [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) |

**Verdict:** Best-in-class open 3D generation. MIT license. 24GB VRAM means it fits the 4090 or 5090. PBR materials are production-quality. Useful for EoBQ assets and future game dev.

---

### 8.2 Hunyuan3D-2.1 (Tencent, Jun 2025)

| Field | Value |
|-------|-------|
| **Release** | June 18, 2025 |
| **Type** | Image-to-3D, Text-to-3D |
| **Architecture** | Diffusion + DINOv2 |
| **License** | Tencent-Hunyuan Community License |
| **Key features** | PBR material generation, high-fidelity textures |
| **HuggingFace** | [tencent/Hunyuan3D-2.1](https://huggingface.co/tencent/Hunyuan3D-2.1) |
| **GitHub** | [Tencent-Hunyuan/Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) |

**Verdict:** Good but Tencent community license is more restrictive than TRELLIS.2's MIT. Less detailed data available.

---

### 8.3 Meta ShapeR (Jan 2026)

| Field | Value |
|-------|-------|
| **Release** | January 16, 2026 (arXiv: 2601.11514) |
| **Type** | Multi-view Image-to-3D |
| **Architecture** | Rectified flow transformer + VecSet latents |
| **License** | CC-BY-NC-4.0 |
| **Key features** | Metric reconstruction from casual captures, multi-view input, SLAM-based |
| **HuggingFace** | [facebook/ShapeR](https://huggingface.co/facebook/ShapeR) |
| **GitHub** | [facebookresearch/ShapeR](https://github.com/facebookresearch/ShapeR) |

**Verdict:** Research-oriented. Requires SLAM preprocessing. Non-commercial license. Less practical than TRELLIS.2 for game asset creation.

---

## 9. Singing Voice Synthesis

### 9.1 SoulX-Singer (Feb 2026)

| Field | Value |
|-------|-------|
| **Release** | February 2026 (arXiv: 2602.07803) |
| **Type** | Zero-shot Singing Voice Synthesis |
| **Languages** | English, Chinese |
| **License** | Apache 2.0 |
| **Key features** | Zero-shot voice cloning for singing, melody-conditioned (F0), score-conditioned (MIDI) |
| **HuggingFace** | [Soul-AILab/SoulX-Singer](https://huggingface.co/Soul-AILab/SoulX-Singer) |
| **GitHub** | [Soul-AILab/SoulX-Singer](https://github.com/Soul-AILab/SoulX-Singer) |

**Verdict:** Niche but interesting for EoBQ audio. Zero-shot singing voice with MIDI control. Apache 2.0.

---

## 10. Recommendations for Athanor

### Priority 1: Deploy Now (High Value, Low Effort)

| Model | Category | Why | GPU | VRAM |
|-------|----------|-----|-----|------|
| **Qwen3-TTS-12Hz-1.7B-CustomVoice** | TTS | Massive upgrade over Piper. 10 languages, voice cloning, 97ms streaming, emotion control. Apache 2.0. | GPU 4 (Node 1) or any | ~3-4GB |
| **ACE-Step v1.5 Turbo** | Music | <4GB VRAM, <10s per song, MIT license. Perfect for EoBQ soundtracks. | Any GPU | <4GB |
| **Z-Image-Turbo** | T2I | 8-step generation, 16GB VRAM, Apache 2.0. Fast Flux alternative. | 5060 Ti | 16GB |

### Priority 2: Test and Evaluate

| Model | Category | Why | GPU | VRAM |
|-------|----------|-----|-----|------|
| **Qwen-Image-2512** | T2I | Claims strongest open-source. Test alongside Flux. | 5060 Ti or 5090 | TBD |
| **HunyuanVideo-1.5 (step-distilled 480p)** | I2V | 14GB VRAM with offloading, 75% faster. | 5060 Ti | 14GB+ |
| **Qwen3-ASR-0.6B** | STT | Better Chinese/dialect support than Whisper, 6-8GB VRAM, vLLM deployable. | Any | 6-8GB |
| **WAN2.2-14B-Rapid-AllInOne** | T2V/I2V | 8GB min VRAM, 4-step, ComfyUI native. Test quality vs current Wan2.x. | 5060 Ti | 8-16GB |
| **LTX-2 (FP4 or distilled)** | A/V | Joint audio+video, ComfyUI native. Test FP4 VRAM on 5060 Ti. | 5060 Ti | TBD |

### Priority 3: When Hardware Allows

| Model | Category | Why | Needs |
|-------|----------|-----|-------|
| **Wan2.2-TI2V-5B** | T2V/I2V | Proper Wan2.2 upgrade. Needs 24GB+ GPU. | 4090 or 5090 |
| **TRELLIS.2-4B** | 3D | MIT, best open 3D, PBR output. For EoBQ assets. | 24GB GPU |
| **HiDream-I1-Full** | T2I | MIT, outperforms Flux on all benchmarks. | 24-32GB GPU |
| **BitDance-14B** | T2I | Benchmark leader, novel AR approach. | 30GB GPU |
| **LongCat-Video** | T2V | Minutes-long video, 30 FPS, MIT. For EoBQ cinematics. | 24-32GB GPU |
| **MOVA-720p** | A/V | Synchronized audio+video. | 32GB+ GPU |

### Not Recommended

| Model | Reason |
|-------|--------|
| Fish Audio S1-mini | CC-BY-NC-SA (non-commercial) |
| AudioX | CC-BY-NC (non-commercial) |
| ShapeR | CC-BY-NC + complex preprocessing |
| Kani-TTS-2 | lfm1.0 restrictive license, English only |
| MOSS-TTS 8B | Too large for consumer GPUs (the 1.7B variant is OK) |
| Wan2.2-Lightning | Needs 80GB VRAM base model |

---

## Summary Statistics

| Category | Models Surveyed | New (Dec 2025 - Feb 2026) | Recommended |
|----------|----------------|---------------------------|-------------|
| T2I | 7 | 5 (Z-Image-Turbo, Qwen-Image-2512, BitDance, DeepGen, FHDR) | Z-Image-Turbo, Qwen-Image-2512 |
| Image Edit | 4 | 2 (HiDream VAREdit, Qwen Edit Rapid AIO) | Qwen Edit Rapid AIO |
| T2V / I2V | 8 | 6 (Wan2.2, Wan2.2-Lightning, Rapid-AIO, HunyuanVideo-1.5, LTX-2, MOVA, Mirage, LongCat) | HunyuanVideo-1.5, Rapid-AIO |
| TTS | 7 | 5 (Qwen3-TTS, MOSS-TTS, VibeVoice, S1-mini, Kani-TTS-2) | Qwen3-TTS |
| STT | 5 | 4 (Qwen3-ASR, Voxtral-Mini, VibeVoice-ASR, Canary-Qwen) | Qwen3-ASR-0.6B |
| Music | 3 | 2 (ACE-Step 1.5, HeartMuLa) | ACE-Step 1.5 |
| Sound FX | 1 | 1 (MOSS-SoundEffect) | MOSS-SoundEffect (when GPU allows) |
| 3D | 3 | 2 (TRELLIS.2, ShapeR) | TRELLIS.2 |
| Singing | 1 | 1 (SoulX-Singer) | SoulX-Singer (niche) |
| **Total** | **39** | **28** | **9 primary** |

---

## Sources

All model cards referenced directly from HuggingFace Hub:
- https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- https://huggingface.co/Tongyi-MAI/Z-Image
- https://huggingface.co/Qwen/Qwen-Image-2512
- https://huggingface.co/shallowdream204/BitDance-14B-16x
- https://huggingface.co/deepgenteam/DeepGen-1.0
- https://huggingface.co/HiDream-ai/HiDream-I1-Full
- https://huggingface.co/kpsss34/FHDR_Uncensored
- https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO
- https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- https://huggingface.co/lightx2v/Wan2.2-Lightning
- https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne
- https://huggingface.co/tencent/HunyuanVideo-1.5
- https://huggingface.co/Lightricks/LTX-2
- https://huggingface.co/OpenMOSS-Team/MOVA-360p
- https://huggingface.co/gomirageai/Mirage-T2V-14B-MoE
- https://huggingface.co/meituan-longcat/LongCat-Video
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
- https://huggingface.co/OpenMOSS-Team/MOSS-TTS
- https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B
- https://huggingface.co/hexgrad/Kokoro-82M
- https://huggingface.co/fishaudio/s1-mini
- https://huggingface.co/nineninesix/kani-tts-2-en
- https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0
- https://huggingface.co/Qwen/Qwen3-ASR-1.7B
- https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602
- https://huggingface.co/microsoft/VibeVoice-ASR
- https://huggingface.co/nvidia/canary-qwen-2.5b
- https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
- https://huggingface.co/ACE-Step/Ace-Step1.5
- https://huggingface.co/HeartMuLa/HeartMuLa-oss-3B
- https://huggingface.co/HKUSTAudio/AudioX
- https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect
- https://huggingface.co/microsoft/TRELLIS.2-4B
- https://huggingface.co/tencent/Hunyuan3D-2.1
- https://huggingface.co/facebook/ShapeR
- https://huggingface.co/Soul-AILab/SoulX-Singer
- https://huggingface.co/jasperai/Flux.1-dev-Controlnet-Upscaler
- https://huggingface.co/HiDream-ai (org page)
- https://huggingface.co/OpenMOSS-Team (org page)
