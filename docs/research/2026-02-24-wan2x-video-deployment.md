# Wan2.x Video Generation: Deployment Research for Athanor

**Date:** 2026-02-24
**Status:** Complete -- ready for deployment
**Updates:** Extends `2026-02-16-video-generation-models.md` with concrete deployment details
**Supports:** ADR-006 (Creative Pipeline)
**Target:** RTX 5090 (32 GB GDDR7, Blackwell sm_120) on Node 2

---

## Context

Prior research (2026-02-16) identified Wan2.2-T2V-A14B as the primary video generation model for Athanor, with Wan2.1-T2V-1.3B as the speed model. This document provides concrete deployment details: exact model files, download sizes, VRAM budgets, ComfyUI node configuration, and Blackwell compatibility status.

ComfyUI already runs on Node 2 via Docker (NGC pytorch:25.02-py3 base image, pinned to GPU 1 = RTX 5090). Models are stored on NFS at `/mnt/vault/models/comfyui/`.

---

## 1. Complete Model Inventory

### Wan2.1 Variants

| Model | Params | Mode | Resolution | HuggingFace Repo |
|-------|--------|------|------------|------------------|
| Wan2.1-T2V-1.3B | 1.3B | Text-to-Video | 480p | `Wan-AI/Wan2.1-T2V-1.3B` |
| Wan2.1-T2V-14B | 14B | Text-to-Video | 480p, 720p | `Wan-AI/Wan2.1-T2V-14B` |
| Wan2.1-I2V-14B-480P | 14B | Image-to-Video | 480p | `Wan-AI/Wan2.1-I2V-14B-480P` |
| Wan2.1-I2V-14B-720P | 14B | Image-to-Video | 720p | `Wan-AI/Wan2.1-I2V-14B-720P` |
| Wan2.1-FLF2V-14B-720P | 14B | First/Last Frame-to-Video | 720p | `Wan-AI/Wan2.1-FLF2V-14B-720P` |
| Wan2.1-VACE-1.3B | 1.3B | Video editing/inpainting | 480p | `Wan-AI/Wan2.1-VACE-1.3B` |
| Wan2.1-VACE-14B | 14B | Video editing/inpainting | 480p, 720p | `Wan-AI/Wan2.1-VACE-14B` |

### Wan2.2 Variants (current generation)

| Model | Params (total/active) | Architecture | Mode | Resolution |
|-------|----------------------|-------------|------|------------|
| Wan2.2-T2V-A14B | 27B / 14B active | MoE (2 experts) | Text-to-Video | 480p, 720p |
| Wan2.2-I2V-A14B | 27B / 14B active | MoE (2 experts) | Image-to-Video | 480p, 720p |
| Wan2.2-TI2V-5B | 5B | Dense, high-compression VAE | Text+Image-to-Video | 720p @ 24fps |
| Wan2.2-S2V-14B | 27B / 14B active | MoE | Speech-to-Video | 480p, 720p |
| Wan2.2-Animate-14B | 14B | Dense | Character animation/replacement | 720p |
| Wan2.2-Fun-Control-A14B | 27B / 14B active | MoE | Controlled video (pose, depth) | 480p, 720p |
| Wan2.2-Fun-Inpaint-A14B | 27B / 14B active | MoE | Video inpainting | 480p, 720p |
| Wan2.2-Fun-Camera-A14B | 27B / 14B active | MoE | Camera motion control | 480p, 720p |
| Wan2.2-Fun-VACE-A14B | 27B / 14B active | MoE | Video editing (enhanced VACE) | 480p, 720p |

### Key Architecture Note (MoE)

The Wan2.2 A14B models use a two-expert Mixture-of-Experts design:
- **High-noise expert** (~14B): handles early denoising steps (layout, composition)
- **Low-noise expert** (~14B): handles later steps (fine detail, texture)
- Expert switching is determined by signal-to-noise ratio threshold at step `t_moe`
- Only one expert is active at any time, so **effective VRAM is ~14B**, not 27B
- In ComfyUI, this manifests as two separate model files loaded sequentially

---

## 2. Exact Model Files for ComfyUI

All files from the **Comfy-Org repackaged repository**: `huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged`

### Recommended Configuration for RTX 5090 (32 GB)

#### Text-to-Video (14B, FP8) -- Primary

| File | Size | Directory |
|------|------|-----------|
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | 14.3 GB | `diffusion_models/` |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | 14.3 GB | `diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.74 GB | `text_encoders/` |
| `wan_2.1_vae.safetensors` | 254 MB | `vae/` |
| **Total download:** | **35.6 GB** | |

#### Image-to-Video (14B, FP8) -- Primary I2V

| File | Size | Directory |
|------|------|-----------|
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 14.3 GB | `diffusion_models/` |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 14.3 GB | `diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | (shared) | `text_encoders/` |
| `wan_2.1_vae.safetensors` | (shared) | `vae/` |
| **Additional download:** | **28.6 GB** | |

#### Text+Image-to-Video (5B, FP16) -- Fast/Low-VRAM

| File | Size | Directory |
|------|------|-----------|
| `wan2.2_ti2v_5B_fp16.safetensors` | 10 GB | `diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | (shared) | `text_encoders/` |
| `wan2.2_vae.safetensors` | 1.41 GB | `vae/` |
| **Additional download:** | **11.4 GB** | |

Note: The 5B model uses a different, higher-compression VAE (`wan2.2_vae.safetensors`, 4x16x16 compression) than the 14B models (`wan_2.1_vae.safetensors`, standard compression). Both VAEs are needed.

#### Speed Model: Wan2.1-T2V-1.3B

From `huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged`:

| File | Size | Directory |
|------|------|-----------|
| `wan2.1_t2v_1.3B_bf16.safetensors` | 2.84 GB | `diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | (shared) | `text_encoders/` |
| `wan_2.1_vae.safetensors` | (shared) | `vae/` |
| **Additional download:** | **2.84 GB** | |

#### Total Storage Budget (all recommended models)

| Category | Files | Size |
|----------|-------|------|
| Diffusion models (T2V 14B FP8) | 2 files | 28.6 GB |
| Diffusion models (I2V 14B FP8) | 2 files | 28.6 GB |
| Diffusion models (TI2V 5B) | 1 file | 10 GB |
| Diffusion models (1.3B speed) | 1 file | 2.84 GB |
| Text encoder (shared) | 1 file | 6.74 GB |
| VAEs (2 different) | 2 files | 1.66 GB |
| **Total** | **9 files** | **~78 GB** |

### GGUF Quantized Alternatives (for tighter VRAM budgets)

From `huggingface.co/QuantStack/Wan2.2-T2V-A14B-GGUF`:

| Quant | File Size | Quality | Use Case |
|-------|-----------|---------|----------|
| Q8_0 | 15.4 GB | Near-lossless | When FP8 is too tight on VRAM |
| Q6_K | 12.0 GB | High quality | Good balance |
| Q5_K_M | 10.8 GB | Good quality | Recommended low-VRAM |
| Q4_K_M | 9.65 GB | Acceptable | When headroom is critical |
| Q3_K_M | 7.17 GB | Noticeable degradation | Last resort |

GGUF variants require the **ComfyUI-GGUF** custom node (`github.com/city96/ComfyUI-GGUF`). Place GGUF files in `ComfyUI/models/unet/`.

For the 32 GB RTX 5090, GGUF is not necessary -- FP8 scaled safetensors (14.3 GB per expert) fit comfortably with room for the text encoder and VAE.

---

## 3. VRAM Budget Analysis (RTX 5090, 32 GB)

### Wan2.2-T2V-A14B at FP8 (Primary Configuration)

| Component | VRAM | Notes |
|-----------|------|-------|
| Diffusion model (1 expert active) | ~14.3 GB | Only high-noise OR low-noise loaded at once |
| UMT5-XXL text encoder (FP8) | ~6.7 GB | Can offload to CPU after encoding |
| VAE decoder | ~0.3 GB | Small footprint |
| KV cache + activations | ~4-6 GB | Depends on resolution and frame count |
| **Total (text encoder in VRAM)** | **~26-28 GB** | Fits 32 GB with headroom |
| **Total (text encoder offloaded)** | **~19-21 GB** | Comfortable margin |

With ComfyUI's automatic model management, the text encoder is loaded for prompt encoding then offloaded before the diffusion model loads. Effective peak VRAM is ~19-21 GB for 480p generation, ~24-28 GB for 720p.

### Wan2.2-TI2V-5B at FP16

| Component | VRAM | Notes |
|-----------|------|-------|
| Diffusion model | ~10 GB | Dense 5B model |
| UMT5-XXL text encoder (FP8) | ~6.7 GB | Offloaded after encoding |
| Wan2.2 VAE | ~1.5 GB | Higher compression VAE |
| KV cache + activations | ~3-5 GB | |
| **Total (with offloading)** | **~15-17 GB** | Very comfortable on 32 GB |

### Wan2.1-T2V-1.3B at BF16

| Component | VRAM | Notes |
|-----------|------|-------|
| Diffusion model | ~2.8 GB | Tiny |
| Text encoder (FP8) | ~6.7 GB | Dominates VRAM |
| VAE | ~0.3 GB | |
| KV cache + activations | ~2-3 GB | |
| **Total** | **~12-13 GB** | Runs on anything |

### Maximum Resolution/Duration on RTX 5090

| Model | Resolution | Duration | VRAM Est. | Feasible? |
|-------|-----------|----------|-----------|-----------|
| Wan2.2-T2V-A14B FP8 | 480p (848x480) | 5s (81 frames) | ~20 GB | Yes |
| Wan2.2-T2V-A14B FP8 | 720p (1280x720) | 5s (81 frames) | ~28 GB | Yes, tight |
| Wan2.2-T2V-A14B FP8 | 720p (1280x720) | 10s (161 frames) | ~32 GB+ | Risky, may OOM |
| Wan2.2-TI2V-5B FP16 | 720p | 5s | ~16 GB | Yes, very comfortable |
| Wan2.1-T2V-1.3B BF16 | 480p | 5s | ~12 GB | Yes |
| Wan2.1-T2V-1.3B BF16 | 720p | 5s | ~16 GB | Yes but quality suffers |

**Practical recommendation:** 480p at 5 seconds is the sweet spot for the 14B model on 32 GB. 720p is possible but leaves no headroom for LoRA or complex workflows. Use the 5B model for 720p when quality can trade down slightly.

---

## 4. ComfyUI Integration

### Option A: Native ComfyUI Nodes (Recommended)

ComfyUI has **first-class native support** for Wan2.2 as of the official Comfy-Org repackaged models. No custom nodes required for basic T2V and I2V.

**Required nodes (built into ComfyUI):**
1. `Load Diffusion Model` -- loads each expert safetensors
2. `Load CLIP` -- loads UMT5-XXL text encoder
3. `Load VAE` -- loads appropriate VAE
4. `CLIP Text Encoder` -- positive/negative prompts
5. `EmptyHunyuanLatentVideo` -- creates latent space (14B models)
6. `Wan22ImageToVideoLatent` -- creates latent from image (5B I2V)
7. `KSampler` -- standard sampling
8. `VAE Decode` -- latents to pixels
9. `Video Combine` -- frames to video file

**Workflow templates** available via ComfyUI: `Workflow > Browse Templates > Video`

Official example workflows at: `comfyanonymous.github.io/ComfyUI_examples/wan22/`

### Option B: Kijai WanVideoWrapper (Advanced Features)

The **ComfyUI-WanVideoWrapper** by Kijai (`github.com/kijai/ComfyUI-WanVideoWrapper`) adds:
- Context windows for long-form generation (tested up to 1025 frames)
- Block swapping for fine-grained VRAM management
- LoRA support (unmerged, preserves base weights)
- GGUF model loading
- VACE, Phantom, ReCamMaster integration
- Camera motion control (SteadyDancer, Fun-Camera)
- Pose control (ATI, Uni3C)
- FP8 scaled model support
- `torch.compile` optimization

**Installation:** Clone into `custom_nodes/`, run `pip install -r requirements.txt`.

**Block swapping** is the key VRAM optimization: offloads N of 40 transformer blocks to CPU during inference. Example: with 20/40 blocks offloaded, the 14B model uses ~16 GB VRAM on an RTX 5090.

**Recommendation:** Install WanVideoWrapper for its block swapping, LoRA, and long-form capabilities. Use native ComfyUI nodes for simple T2V/I2V.

### Option C: ComfyUI-GGUF (For Quantized Models)

If using GGUF quantized models, install `github.com/city96/ComfyUI-GGUF`. Place GGUF files in `ComfyUI/models/unet/`. The GGUF loader replaces the standard diffusion model loader.

### Required Custom Nodes Summary

| Node Pack | Purpose | Required? |
|-----------|---------|-----------|
| ComfyUI-Manager | Node management | Already installed |
| ComfyUI-WanVideoWrapper | Advanced Wan features, block swap, LoRA | Strongly recommended |
| ComfyUI-GGUF | GGUF quantized model loading | Only if using GGUF |
| KJNodes | SageAttention patch (prevents black output) | Recommended |

### Model Directory Mapping

For the existing `extra_model_paths.yaml` on Node 2:

```yaml
vault_nfs:
    base_path: /mnt/vault/models/comfyui/
    diffusion_models: unet/
    clip: clip/
    vae: vae/
    checkpoints: checkpoints/
```

Place files as:
- `/mnt/vault/models/comfyui/unet/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`
- `/mnt/vault/models/comfyui/unet/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`
- `/mnt/vault/models/comfyui/unet/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`
- `/mnt/vault/models/comfyui/unet/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`
- `/mnt/vault/models/comfyui/unet/wan2.2_ti2v_5B_fp16.safetensors`
- `/mnt/vault/models/comfyui/unet/wan2.1_t2v_1.3B_bf16.safetensors`
- `/mnt/vault/models/comfyui/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors`
- `/mnt/vault/models/comfyui/vae/wan_2.1_vae.safetensors`
- `/mnt/vault/models/comfyui/vae/wan2.2_vae.safetensors`

---

## 5. Generation Speed Estimates

### Wan2.2-T2V-A14B (FP8) on RTX 5090

| Resolution | Duration | Est. Time | Clips/Hour |
|-----------|----------|-----------|------------|
| 480p (848x480) | 5s (81 frames) | ~2-3 min | ~20-30 |
| 720p (1280x720) | 5s (81 frames) | ~8-12 min | ~5-7 |

### Wan2.2-TI2V-5B (FP16) on RTX 5090

| Resolution | Duration | Est. Time | Clips/Hour |
|-----------|----------|-----------|------------|
| 720p | 5s @ 24fps | ~5-7 min | ~8-12 |

### Wan2.1-T2V-1.3B (BF16) on RTX 5090

| Resolution | Duration | Est. Time | Clips/Hour |
|-----------|----------|-----------|------------|
| 480p | 5s | ~1-2 min | ~30-60 |

**Reference benchmarks:**
- SaladCloud (2026): RTX 5090 generates Wan2.1-1.3B 480p 5s clips in 2.4 min
- RTX 4090 generates Wan2.1-T2V-14B 480p in ~4.7 min (FP16 with offloading)
- RTX 5090 is ~35% faster than RTX 4090 for diffusion sampling (ComfyUI community reports)

---

## 6. Blackwell (sm_120) Compatibility

### Status: Working, with Caveats

**ComfyUI + Blackwell is stable as of February 2026.** The existing Dockerfile uses `nvcr.io/nvidia/pytorch:25.02-py3` which ships with CUDA 12.8 -- this is the minimum required version for Blackwell.

**Known issues and mitigations:**

| Issue | Status | Mitigation |
|-------|--------|------------|
| PyTorch CUDA 12.8+ required | Resolved | NGC container already provides this |
| SageAttention black output on Wan models | Active bug | Do NOT use `--use-sage-attention` CLI flag. Instead use KJNodes "Patch Sage Attention" node in workflow |
| TensorRT compilation fails on sm_120 | Known issue | Not a blocker -- PyTorch native inference works fine |
| xformers compatibility | Resolved | xformers 0.0.30+ works with CUDA 12.8 |
| FlashAttention | Resolved | FA 2.7.4+ works |
| Triton cache issues (Windows) | N/A | We run Linux containers |
| Custom node Python version mismatches | Resolved | NGC container uses Python 3.12 |

**Critical: AWQ Marlin kernels do NOT work on Blackwell.** This is an LLM inference issue (vLLM), not a diffusion issue. Wan2.x models use standard FP16/FP8/BF16 weights, not AWQ quantization. No conflict.

**FP8 on Blackwell:** The RTX 5090's tensor cores have native FP8 support. The `_fp8_scaled` model variants from Comfy-Org are the optimal format -- they use FP8 E4M3FN with per-tensor scaling, which maps directly to Blackwell's FP8 tensor core instructions. This gives both a VRAM reduction and a speed improvement vs FP16.

**Recommendation:** No changes needed to the existing Dockerfile or ComfyUI deployment. The current NGC pytorch:25.02-py3 base + Blackwell GPU works out of the box for Wan2.x inference.

---

## 7. Competitor Comparison (Updated February 2026)

### For 32 GB VRAM (RTX 5090)

| Model | Params | VRAM (best config) | Quality | Speed (5s 480p) | NSFW | ComfyUI | Audio |
|-------|--------|-------------------|---------|-----------------|------|---------|-------|
| **Wan2.2-T2V-A14B** | 27B/14B | ~20 GB (FP8) | Best open-weight | ~2-3 min | Mature ecosystem | Native + Kijai | No |
| **LTX-2** | 19B | ~20 GB (FP8) | Very good | ~3-5 min | Forming | ComfyUI-LTXVideo | **Yes** |
| **HunyuanVideo 1.5** | 8.3B | ~13 GB (distilled) | Strong | ~2-3 min | Minimal | Yes | No |
| **CogVideoX 1.5** | 5B | ~16 GB (optimized) | Good | ~10-15 min | Limited | Yes | No |
| **Mochi 1** | 10B | ~22 GB (BF16) | Good motion | ~15+ min | Limited | Yes | No |
| **Wan2.2-TI2V-5B** | 5B | ~15 GB (FP16) | Good | ~5-7 min | Inherits base | Native | No |

### Verdict (unchanged from prior research)

**Wan2.2-T2V-A14B remains the clear winner** for Athanor's use case:
- Best video quality in the open-weight space
- Most mature NSFW ecosystem (critical for EoBQ)
- Apache 2.0 license
- FP8 fits comfortably on 32 GB
- First-class ComfyUI support (both native and Kijai wrapper)
- MoE architecture means 14B effective compute at 14B VRAM cost

**LTX-2 is the secondary model** for when synchronized audio matters. Worth deploying alongside Wan2.2 for cinematic content.

**HunyuanVideo 1.5 step-distilled** is worth considering as a fast-iteration model (75% faster than standard, ~13 GB), but its Chinese corporate origin and lack of NSFW ecosystem make it a poor fit for EoBQ.

---

## 8. Deployment Plan

### Phase 1: Download Models to VAULT

```bash
# On VAULT (or any node with NFS write access)
# Total: ~78 GB download

# Create directory structure
mkdir -p /mnt/vault/models/comfyui/unet
mkdir -p /mnt/vault/models/comfyui/clip
mkdir -p /mnt/vault/models/comfyui/vae

# Download from HuggingFace (Comfy-Org repackaged)
# T2V 14B FP8 (primary)
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors \
  split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors \
  --local-dir /tmp/wan22 --local-dir-use-symlinks False

# I2V 14B FP8
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors \
  split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors \
  --local-dir /tmp/wan22 --local-dir-use-symlinks False

# TI2V 5B FP16
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
  --local-dir /tmp/wan22 --local-dir-use-symlinks False

# Text encoder (shared)
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  --local-dir /tmp/wan22 --local-dir-use-symlinks False

# VAEs (both needed)
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/vae/wan_2.1_vae.safetensors \
  split_files/vae/wan2.2_vae.safetensors \
  --local-dir /tmp/wan22 --local-dir-use-symlinks False

# Wan2.1-1.3B speed model
huggingface-cli download Comfy-Org/Wan_2.1_ComfyUI_repackaged \
  split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors \
  --local-dir /tmp/wan21 --local-dir-use-symlinks False

# Move to NFS model directory
mv /tmp/wan22/split_files/diffusion_models/*.safetensors /mnt/vault/models/comfyui/unet/
mv /tmp/wan21/split_files/diffusion_models/*.safetensors /mnt/vault/models/comfyui/unet/
mv /tmp/wan22/split_files/text_encoders/*.safetensors /mnt/vault/models/comfyui/clip/
mv /tmp/wan22/split_files/vae/*.safetensors /mnt/vault/models/comfyui/vae/

# Fix NFS permissions (root_squash)
chmod 777 /mnt/vault/models/comfyui/unet/*.safetensors
chmod 777 /mnt/vault/models/comfyui/clip/*.safetensors
chmod 777 /mnt/vault/models/comfyui/vae/*.safetensors
```

### Phase 2: Install Custom Nodes

Inside the ComfyUI container or via Ansible:

```bash
# WanVideoWrapper (advanced features, block swapping, LoRA)
cd /opt/ComfyUI/custom_nodes
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git
cd ComfyUI-WanVideoWrapper && pip install -r requirements.txt

# ComfyUI-GGUF (optional, for quantized models)
cd /opt/ComfyUI/custom_nodes
git clone https://github.com/city96/ComfyUI-GGUF.git

# KJNodes (SageAttention patch for Blackwell)
cd /opt/ComfyUI/custom_nodes
git clone https://github.com/kijai/ComfyUI-KJNodes.git
cd ComfyUI-KJNodes && pip install -r requirements.txt
```

### Phase 3: Test Workflow

1. Open ComfyUI at `http://192.168.1.225:8188`
2. Load template: `Workflow > Browse Templates > Video > Wan2.2 T2V 14B`
3. Select `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` and `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`
4. Set resolution to 848x480, 81 frames (5 seconds)
5. Enter test prompt
6. Queue and verify output

---

## 9. Wan2.2 Capabilities Beyond Basic T2V/I2V

### Speech-to-Video (S2V-14B)
- Input: audio file + reference image + optional text prompt
- Output: lip-synced, gesture-matched video
- VRAM: 80 GB minimum (single GPU) -- **does not fit RTX 5090**
- Could work with aggressive offloading or on Node 1 with TP across multiple GPUs
- ComfyUI support available via Comfy-Org repackaged (audio encoder: `wav2vec2_large_english_fp16.safetensors`, 631 MB)
- **Verdict:** Compelling for EoBQ character dialogue, but VRAM is a hard blocker on single 32 GB card. Park for now.

### Character Animation (Animate-14B)
- Input: motion reference video + character image
- Modes: animation (mimic motion) or replacement (swap character)
- VRAM: ~24 GB on RTX 4090 (reported), fits RTX 5090
- Generation: ~180s on 4090, ~120s estimated on 5090
- **Verdict:** Very relevant for EoBQ character animation. Deploy after basic T2V/I2V is proven.

### Fun-Camera (camera motion control)
- Controls camera movement in generated videos
- FP8 variant: 15.3 GB per expert (two files)
- **Verdict:** Useful for cinematic shots. Lower priority than core T2V/I2V.

### Fun-Control (pose/depth-guided)
- Generates video following pose or depth maps
- 5B dense variant available (10 GB, fits easily)
- 14B MoE variant available (14.3 GB FP8 per expert)
- **Verdict:** Valuable for controlled character animation. Medium priority.

### Fun-Inpaint (video inpainting)
- Edit specific regions of existing video
- Same size as Fun-Control variants
- **Verdict:** Useful for post-production. Lower priority.

---

## 10. Open Questions

1. **SageAttention on Blackwell with Wan2.x:** The ComfyUI community reports black output when using `--use-sage-attention` with Wan/Qwen models. The KJNodes workaround (Patch Sage Attention node) reportedly fixes this. Needs testing on our specific setup.

2. **Block swapping performance impact:** WanVideoWrapper's block swapping trades VRAM for speed. At 20/40 blocks offloaded, VRAM drops to ~16 GB but generation time increases significantly. Need to benchmark the sweet spot on RTX 5090.

3. **NFS latency for model loading:** Models are served from VAULT via 5GbE NFS. First-load time for 14.3 GB files over 5GbE is ~12 seconds. ComfyUI caches loaded models in GPU VRAM between generations, so this is a one-time cost per session.

4. **LoRA training feasibility:** Wan2.2 LoRA training for EoBQ character consistency is possible via DiffSynth-Studio. The 5B model is trainable on 32 GB; the 14B requires 48 GB+ or aggressive optimization.

5. **Wan2.2 S2V on Node 1:** Could S2V-14B run on Node 1's 4x 5070 Ti (64 GB total) via FSDP? The multi-GPU inference code supports this but hasn't been tested with FSDP on mixed architectures. Node 1's GPUs are all sm_120 (Blackwell), so architecture mismatch is not an issue.

---

## Sources

### Official Repositories
- [Wan2.1 GitHub](https://github.com/Wan-Video/Wan2.1)
- [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- [Wan2.2-T2V-A14B HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B)
- [Wan2.2-S2V-14B HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-S2V-14B)
- [Wan2.2-Animate-14B HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B)

### ComfyUI Resources
- [Comfy-Org Wan2.2 Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)
- [Comfy-Org Wan2.1 Repackaged](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged)
- [Official Wan2.2 ComfyUI Tutorial](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [Wan2.2 Example Workflows](https://comfyanonymous.github.io/ComfyUI_examples/wan22/)
- [ComfyUI-WanVideoWrapper (Kijai)](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)
- [ComfyUI Blackwell Discussion](https://github.com/comfyanonymous/ComfyUI/discussions/6643)
- [ComfyUI RTX 5090 Setup](https://blog.comfy.org/p/how-to-get-comfyui-running-on-your)

### GGUF Quantizations
- [QuantStack Wan2.2-T2V-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-T2V-A14B-GGUF)
- [city96 Wan2.1-T2V-14B-GGUF](https://huggingface.co/city96/Wan2.1-T2V-14B-gguf)

### Benchmarks
- [SaladCloud Wan2.1 Benchmarks](https://blog.salad.com/benchmarking-wan2-1/)
- [InstaSD Wan2.1 GPU Performance](https://www.instasd.com/post/wan2-1-performance-testing-across-gpus)
- [Novita Wan2.2 VRAM Guide](https://blogs.novita.ai/wan-2-2-vram-find-the-best-gpu-setup-for-deployment/)
