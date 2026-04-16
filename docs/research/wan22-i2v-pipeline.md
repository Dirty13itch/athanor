# Wan 2.2 I2V Video Pipeline — Research & Implementation

## Status: Phase 1 Ready (pending model download)

### Architecture

```
Flux PuLID Portrait (832x1216)
  |
  v  crop/resize
First Frame (832x480)
  |
  v  WanVideoImageToVideoEncode
Image Embeds
  |
  + Text Embeds (WanVideoTextEncode)
  |
  v  WanVideoSampler (25 steps, cfg=1.0)
Latent Video (81 frames)
  |
  v  WanVideoDecode (tiled VAE)
Pixel Frames
  |
  v  CreateVideo + SaveVideo
MP4 (16fps, 5 seconds)
  |
  v  (optional) RIFE_VFI
32fps interpolated
```

### Model Strategy

| GPU | Model | VRAM Budget | Quality |
|-----|-------|-------------|---------|
| **5060 Ti (16GB)** | GGUF Q4_K_S (8.75GB) | Model 8.75G + text enc offloaded + VAE offloaded = fits | Good |
| **5090 (32GB)** | Remix NSFW FP8 dual | Model ~16G + text enc 4G + VAE 0.25G + LoRAs ~1G = ~21G | Best |

Default: 5060 Ti (always available, no vLLM disruption)
HQ mode: GPU swap to 5090 (stop vLLM worker, start ComfyUI on GPU 0)

### Models on VAULT NFS (/mnt/vault/models/comfyui/)

| File | Dir | Size | Status |
|------|-----|------|--------|
| wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors | unet/ | 14G | Present |
| wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors | unet/ | 14G | Present |
| Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf | unet/ | 8.75G | Present |
| Wan2.2_Remix_NSFW_i2v_14b_high_v2.0.safetensors | unet/ | ~14G | Downloading |
| Wan2.2_Remix_NSFW_i2v_14b_low_v2.0.safetensors | unet/ | ~14G | Downloading |
| umt5-xxl-enc-fp8_e4m3fn.safetensors | clip/ | 6.3G | Present |
| CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors | clip_vision/ | 2.4G | Present |
| wan_2.1_vae.safetensors | vae/ | 243M | Present |
| flux-uncensored.safetensors | loras/ | 656M | Present (Flux) |
| wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors | loras/ | 1.2G | Present |
| wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors | loras/ | 1.2G | Present |
| NSFW-22-H-e8.safetensors | loras/ | ~599M | Blocked (CivitAI auth) |

### ComfyUI Custom Nodes (Workshop container)

All installed:
- ComfyUI-WanVideoWrapper (Kijai) — I2V, T2V, LoRA, VACE, FLF2V
- ComfyUI-Impact-Pack — FaceDetailer
- ComfyUI-KJNodes — Utilities
- ComfyUI-PuLID-Flux — Face injection
- ComfyUI-ReActor — Face swap
- ComfyUI_IPAdapter_plus — IP adapter
- ComfyUI_InfiniteYou — Identity preservation
- ComfyUI-Manager — Package management
- VHS (VideoHelperSuite) — Video I/O
- ComfyUI-Frame-Interpolation — RIFE VFI, FILM VFI, AMT VFI, etc.

### Key Node Names (verified via /object_info API)

- `WanVideoModelLoader` — loads model, accepts `lora` input
- `WanVideoImageToVideoEncode` — encodes first frame (uses `start_image` + `vae`, NOT model/clip)
- `WanVideoSampler` — core generation (model + image_embeds + text_embeds)
- `WanVideoLoraSelect` — LoRA selection (output feeds ModelLoader.lora)
- `WanVideoTextEncode` — text encoding with T5
- `WanVideoDecode` — VAE decode with tiling
- `WanFirstLastFrameToVideo` — FLF2V for controlled sequences
- `RIFE_VFI` / `VHS_RIFE` — frame interpolation (16fps -> 32fps)
- `WanVideoSVIProEmbeds` — SVI 2.0 Pro for long video chaining

### Workflow Files (projects/eoq/comfyui/)

| File | Type | Notes |
|------|------|-------|
| wan-i2v.json | I2V base | GGUF Q4_K_S, RIFE 2x, quality toggle |
| wan-i2v-lora.json | I2V + NSFW | Same + NSFW LoRA at 0.75 |
| wan-flf2v.json | FLF2V | Start + end frame controlled transition |
| wan-t2v.json | T2V | Existing text-to-video |

### EoBQ Integration

- `/api/generate` route supports `type: "i2v"` with `referencePath` (anchor image)
- `nsfw: true` flag selects LoRA workflow variant
- `use-image-generation.ts` has `generatePortraitVideo()` function
- Portrait component already renders `<video>` for .mp4/.webm URLs
- 10-minute polling timeout for video generation

### Generation Tips (from "300 Hours on Wan 2.2")

- **Steps**: 6 is optimal quality/speed. Minimal improvement beyond 8.
- **LoRA strength**: Start at 0.75 for high-noise, 0.25 for low-noise
- **Stack max 2-4 LoRAs** — more causes artifacts
- **Prompt style**: Conversational, action-focused. "slowly breathing" not "a person who is breathing"
- **Resolution**: Divisible by 16. 832x480 for landscape, 480x832 for portrait
- **noise_aug_strength**: 0.025 adds motion without artifacts. Higher = more deviation from anchor.
- **NSFW LoRA works with GGUF** per community reports (untested locally)
- **Lock seed during testing** — change one variable at a time

### LightX2V 4-Step Speed Mode (5090 Only)

LightX2V distills 25-step generation to 4 steps. Requires dual I2V model architecture:
- **Two KSamplers** in sequence: high-noise model → low-noise model
- **Two LoRAs**: `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` (1.2G, present)
  and `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` (1.2G, present)
- **Requires FP8 dual models** (high + low I2V), NOT compatible with single GGUF
- Steps split: 4 total = 2+2, 8 = 4+4, 12 = 6+6
- Source: [Comfy-Org/Wan_2.2_ComfyUI_Repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)

Not usable on 5060 Ti (need two 14GB models). Phase 3 feature for 5090 HQ mode.

### Phase Plan

1. **Phase 1: Portrait Animation** — Take PuLID queen portrait, animate with subtle motion
   - Model: GGUF Q4_K_S on 5060 Ti
   - LoRA: None (base model first)
   - Output: 5-second 16fps animated portrait

2. **Phase 2: NSFW Motion** — Add NSFW LoRA for explicit content
   - Model: GGUF + NSFW-22-H LoRA
   - Output: Stage-aware animation (defiant -> broken progression)

3. **Phase 3: HQ Mode** — Swap 5090 for Remix NSFW dual model
   - Model: Wan2.2 Remix NSFW FP8 (high + low)
   - Resolution: 720p
   - Output: Cinema-quality clips

4. **Phase 4: Extended Sequences** — SVI 2.0 Pro chaining
   - Chain 3-5 clips per sequence
   - RIFE interpolation to 32fps

### Sources

- [Kijai WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [Official Wan 2.2 docs](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [WAN General NSFW LoRA](https://civitai.com/models/1307155)
- [Wan2.2 Remix NSFW](https://huggingface.co/FX-FeiHou/wan2.2-Remix)
- [GGUF Quantizations](https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF)
- [300 Hours on Wan 2.2](https://civitai.com/articles/23629)
- [NSFW I2V Guide](https://civitai.com/articles/24518)
