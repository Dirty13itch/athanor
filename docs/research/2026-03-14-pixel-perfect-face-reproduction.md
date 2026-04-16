# Pixel-Perfect Face Reproduction in AI-Generated Images

**Date:** 2026-03-14
**Status:** Complete -- recommendation ready
**Supports:** ADR-006 (Creative Pipeline), EoBQ game project
**Depends on:** ADR-006 (Creative Pipeline), existing ComfyUI deployment on WORKSHOP

---

## The Question

Given a set of reference photos of a specific real person, how do we generate AI images in various poses, outfits, lighting conditions, and expressions that are **indistinguishable from the real person**? What combination of technologies achieves maximum face likeness, and what is the optimal pipeline for ComfyUI on local hardware?

---

## Context

**Current Stack:**
- ComfyUI on WORKSHOP (5090 32GB + 5060Ti 16GB)
- Flux.2 dev FP8 deployed
- PuLID workflow already functional
- Stash media server with 14,547 performer profiles (photo references available)
- FOUNDRY: 4x 5070Ti (16GB each) + 4090 (24GB) available for LoRA training

**Goal:** Reproduce specific real people's faces with maximum fidelity across diverse generation scenarios.

---

## Technology Survey

### 1. PuLID (Pure and Lightning ID Customization)

**How it works:** PuLID embeds facial identity into Flux's generation process using contrastive alignment between a Lightning T2I branch and the standard diffusion branch. It extracts face embeddings via InsightFace, then injects identity features into the diffusion transformer's attention layers without fine-tuning the base model.

**Versions:**
| Version | Release | Key Change |
|---------|---------|------------|
| PuLID Flux v0.9.0 | Aug 2024 | Initial Flux port |
| PuLID Flux v0.9.1 | Oct 2024 | +5% facial similarity in quantitative metrics |
| PuLID Flux II | 2025 | TeaCache/WaveSpeed compatible, attention mask control |

**Key Parameters:**

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| `weight` | 0.9-1.0 (v0.9.1) | Higher = stronger identity. v0.9.0 uses 0.8-0.95 |
| `method` | "fidelity" | Prioritizes likeness over generation quality |
| `fusion` | "mean" (default) | "max" or "max_token" boost distinctive features but risk distortion |
| `start_at` | 0.0 | When to begin applying identity in diffusion steps |
| `end_at` | 1.0 | When to stop applying identity |
| Precision | bf16 preferred | fp8 degrades face detail slightly |
| Guidance | 2.5-3.5 | FluxGuidance setting |

**Reference Photo Requirements:**
- Minimum 1 photo, batch multiple for better results (use Batch Images node)
- **Frontal view preferred** -- output mirrors input orientation
- **Medium portrait framing** -- not too close, not too far from camera
- Well-lit, consistent lighting
- When using multiple refs: connect best photo to `prior_image` endpoint
- For `train_weight` method: <2000 steps for deep fusion

**Face Similarity Score:** 88-93% (InsightFace cosine similarity)

**Known Limitations:**
- Cannot change face angle from reference (output follows input orientation)
- Struggles with small faces in scene (loss of detail, distortion)
- Inconsistent on real photographs vs AI-generated references
- Weaker on male faces (model bias)
- Copies reference hairstyle/angle rigidly, limiting creative flexibility
- Formally discontinued by original developer (but community forks active)

**ComfyUI Nodes:**
- `PulidFluxModelLoader` -- loads model (e.g., `pulid_flux_v0.9.1.safetensors`)
- `ApplyPulidFlux` -- applies identity injection
- `LoadImage` -- reference photos
- `BatchImages` -- multiple reference photos
- `BasicGuider` -- connects to sampler

**VRAM:** ~2-4 GB additional on top of Flux model. Total pipeline: ~16-20 GB (Flux FP8 + PuLID)

**Sources:**
- [PuLID GitHub (official)](https://github.com/ToTheBeginning/PuLID)
- [PuLID for Flux docs](https://github.com/ToTheBeginning/PuLID/blob/main/docs/pulid_for_flux.md)
- [PuLID Flux II workflow](https://www.runcomfy.com/comfyui-workflows/pulid-flux-ii-in-comfyui-consistent-character-ai-generation)
- [ComfyUI-PuLID-Flux-Enhanced](https://github.com/sipie800/ComfyUI-PuLID-Flux-Enhanced)
- [PuLID Flux + Chroma](https://github.com/PaoloC68/ComfyUI-PuLID-Flux-Chroma)

---

### 2. IP-Adapter FaceID

**How it works:** IP-Adapter encodes reference images through CLIP vision and injects the embeddings into the diffusion model's cross-attention layers. FaceID variants specifically use InsightFace embeddings for face identity.

**Face Similarity Score:** 76-82% (InsightFace cosine similarity)

**Strengths:**
- Broadest model compatibility (works with any IP-Adapter-compatible checkpoint)
- Simplest setup -- part of the IP-Adapter ecosystem
- Works with custom fine-tuned models, merged checkpoints, community models
- Fast iteration speed

**Weaknesses:**
- Lowest face similarity among the three main methods
- Moderate detail preservation
- General image-based conditioning rather than identity-specific targeting

**ComfyUI Nodes:**
- `IPAdapterFaceID` (from ComfyUI_IPAdapter_plus)
- `IPAdapterModelLoader`
- `CLIPVisionEncode`

**VRAM:** ~1-2 GB additional. Lightweight.

**Verdict:** **Not recommended as primary method** for pixel-perfect work. Useful as a fast iteration/previewing tool during workflow development.

**Sources:**
- [IP-Adapter FaceID HuggingFace](https://huggingface.co/h94/IP-Adapter-FaceID)
- [PuLID vs InstantID vs FaceID comparison](https://myaiforce.com/pulid-vs-instantid-vs-faceid/)
- [IPAdapterFaceID node](https://www.runcomfy.com/comfyui-nodes/ComfyUI_IPAdapter_plus/IPAdapterFaceID)

---

### 3. ACE++ (Alibaba) -- Emerging Leader

**How it works:** ACE++ uses instruction-based image editing powered by the Flux Fill model, enabling natural language-driven face swaps with context-aware content filling.

**Face Similarity Score:** Up to 99% consistency (when combined with Redux)

**Strengths:**
- Highest reported face consistency of any method tested
- Handles obstructed faces, extreme angles
- Natural language instruction interface
- Environmental sync and contextual interaction preservation
- Handles angled faces smoothly

**Weaknesses:**
- Not designed for full-body shots (medium portrait / close portrait only)
- Newer, less battle-tested community tooling
- Dependent on Flux Fill model

**ComfyUI Nodes:**
- ACE++ nodes available via ComfyUI custom node manager
- Often combined with Redux for style anchoring

**VRAM:** Requires Flux Fill model loaded alongside -- ~20-24 GB total

**Verdict:** **Strong contender for the identity injection step.** The 99% consistency claim (with Redux) significantly exceeds PuLID's 88-93%. Worth testing as a replacement or complement to PuLID.

**Sources:**
- [ACE++ Face Swap workflow](https://www.runcomfy.com/comfyui-workflows/ace-plus-plus-face-swap)
- [99% face consistency with ACE Plus + Redux](https://myaiforce.com/ace-plus-redux-portrait-bg-swap/)
- [4-way comparison: HyperLoRA vs InstantID vs PuLID vs ACE Plus](https://myaiforce.com/hyperlora-vs-instantid-vs-pulid-vs-ace-plus/)

---

### 4. ReActor / Face Swap (Post-Generation Refinement)

**How it works:** ReActor performs face detection on a generated image, then swaps the detected face with a source face using the inswapper_128 model. Face restoration (GFPGANv1.4, CodeFormer) refines the result. This is a **post-processing** step, not a generation-time injection.

**Models Supported:**

| Model | Resolution | Notes |
|-------|-----------|-------|
| inswapper_128.onnx | 128px | Original, well-tested |
| hyperswap_1a/1b/1c_256.onnx | 256px | 2x resolution, newer (FaceFusion Labs) |
| reswapper_128/256.onnx | 128/256px | Alternative option |

**Face Restoration Options:**
- **CodeFormer** -- Best quality, weight parameter controls intensity
- **GFPGANv1.4** -- Good quality, faster
- **GPEN** -- Alternative
- **RestoreFormer** -- Alternative

**Key Parameters:**

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| Face swap model | hyperswap_1c_256.onnx | Best quality, 256px |
| Face detection | RetinaFace (retinaface_resnet50) | Most accurate detection |
| Face restoration | CodeFormer | Highest quality restoration |
| Restore visibility | 0.7 | Blends restored face naturally |
| CodeFormer weight | 0.5-0.7 | Higher = stronger restoration |
| Interpolation | bicubic | Best quality scaling |

**ReActorMaskHelper for Pixel-Perfect Control:**
- Bounding box, segmentation, and SAM masking
- Morphological controls: dilation, erosion, opening, closing
- Gaussian blur at mask edges for smooth transitions
- Auto cut-and-paste of swapped region

**Known Limitations:**
- Face similarity limited to ~68% on identity recognition tests (alone)
- Can introduce artifacts at face boundaries
- Skin tone mismatch possible without careful parameter tuning
- InsightFace models require non-commercial license

**VRAM:** ~1-2 GB (runs on CPU or GPU, lightweight)

**ComfyUI Nodes:**
- `ReActorFaceSwap` -- main swap node
- `ReActorSetWeight` -- swap strength 0-100%
- `ReActorLoadFaceModel` / `ReActorSaveFaceModel` -- model management
- `ReActorMaskHelper` -- pixel-perfect masking
- Face restoration nodes (built-in)

**Sources:**
- [ComfyUI-ReActor GitHub](https://github.com/Gourieff/ComfyUI-ReActor)
- [HyperSwap support issue](https://github.com/Gourieff/ComfyUI-ReActor/issues/143)
- [ReActor professional workflow](https://www.runcomfy.com/comfyui-workflows/comfyui-reactor-face-swap-professional-ai-face-animation)
- [Face Swap + SeedVR2 + Qwen Edit pipeline](https://seedvr2.net/blog/tutorials/seedvr2-face-swap-qwen-edit-upscale-workflow-2026)

---

### 5. Custom Face LoRA Training

**How it works:** Train a LoRA adapter on 15-30 images of a specific person's face. The model learns bone structure, skin texture patterns, facial asymmetries, expression characteristics, and lighting responses. This becomes the **base identity layer** that other methods refine.

**Face Similarity Score:** 97% identity recognition when combined with FaceDetailer (vs 68% for ReActor alone)

**Tools:**

| Tool | Min VRAM | Config Complexity | Community | Best For |
|------|----------|-------------------|-----------|----------|
| ai-toolkit (Ostris) | 24 GB | Low (YAML config) | Growing | FLUX-focused, sensible defaults |
| Kohya SS | 12-24 GB | High (many params) | Largest | Maximum control |
| FluxGym | 12 GB | Minimal (UI) | Growing | Beginners, quick runs |
| SimpleTuner | 20 GB | Medium | Medium | Multi-architecture |

**Optimal Training Parameters for Face LoRA (FLUX):**

| Parameter | Value | Notes |
|-----------|-------|-------|
| Rank (network_dim) | 64 | 32 for styles, 64 for faces, 128 for max detail |
| Alpha (network_alpha) | 32 | Half of rank for character LoRAs |
| Learning rate | 1e-4 to 4e-4 | Lower = smoother, more generalizable |
| Optimizer | AdamW8bit | Standard for FLUX |
| Precision | bf16 | Mixed precision |
| Quantize base model | true | Required for 24GB GPUs |
| Steps | 1,000-2,000 | ~40 steps per image minimum |
| Batch size | 1-2 | Larger if VRAM allows |
| Resolution | 1024x1024 | Standard for FLUX |
| Trigger word | "ohwx [name]" | Unique token for each person |

**Dataset Preparation (Critical -- 90% of quality):**

| Aspect | Requirement |
|--------|-------------|
| Quantity | 15-30 images (20 ideal). Quality > quantity |
| Resolution | Minimum 1024x1024, auto-crop to focus on face |
| Variety | Multiple angles (front, 3/4, profile), expressions, lighting conditions |
| Clothing | Varied (unless clothing is part of the LoRA) |
| Backgrounds | Varied to prevent background leakage |
| Clean | No watermarks, logos, text overlays, heavy filters |
| Captioning | Per-image .txt files with descriptive captions |
| Captioning tool | JoyCaption (2025+) or BLIP for auto-captioning, manual review recommended |
| Trigger word | Include in every caption: "[trigger] man/woman, description..." |
| Regularization | 20-30% contextual images to prevent overfitting |

**Training Time on Athanor Hardware:**

| GPU | Estimated Time (2000 steps) | Notes |
|-----|-----------------------------|-------|
| RTX 5090 (32GB) | ~2 hours | Best option, full VRAM headroom |
| RTX 4090 (24GB) | ~2-4 hours | Tight but works with quantization |
| RTX 5070Ti (16GB) | ~4-6 hours | Possible with FluxGym, aggressive quant |
| RTX 5060Ti (16GB) | ~4-6 hours | Possible with FluxGym |

**Using the Trained LoRA:**

The trained LoRA produces consistent identity when used as a generation-time weight. Combined with FaceDetailer:

```
FaceDetailer settings:
- denoise: 0.40-0.45
- face_margin: 1.6
- feather: 16-32
- LoRA strength: 0.8-1.0
```

FaceDetailer detects faces in the generated image, re-generates just the face region using the LoRA, and composites it back -- producing highly accurate face reproduction while maintaining the overall image composition.

**Sources:**
- [ai-toolkit GitHub](https://github.com/ostris/ai-toolkit)
- [Flux LoRA training Kohya guide](https://learn.thinkdiffusion.com/flux-lora-training-with-kohya/)
- [Flux 2 LoRA training guide 2026](https://apatero.com/blog/flux-2-pro-lora-training-character-consistency-2026)
- [Kohya SS LoRA training complete guide 2025](https://www.apatero.com/blog/kohya-ss-lora-training-complete-guide-2025)
- [Ultimate LoRA training guide 2025](https://sanj.dev/post/lora-training-2025-ultimate-guide)
- [FaceDetailer + LoRA method](https://apatero.com/blog/professional-face-swap-facedetailer-lora-method-comfyui-2025)
- [Flux LoRA training from zero to hero (Kohya)](https://github.com/FurkanGozukara/Stable-Diffusion/wiki/FLUX-LoRA-Training-Simplified-From-Zero-to-Hero-with-Kohya-SS-GUI-8GB-GPU-Windows-Tutorial-Guide)
- [FluxGym GitHub](https://github.com/cocktailpeanut/fluxgym)
- [HuggingFace LoRA training discussion](https://discuss.huggingface.co/t/perfect-lora-training-parameters-human-character/147211)
- [Qwen-Image LoRA with ai-toolkit](https://www.kombitz.com/2025/09/15/how-to-train-a-qwen-image-lora-with-ai-toolkit-with-ai-toolkit/)

---

### 6. Flux Kontext (Instruction-Based Editing)

**How it works:** FLUX.1 Kontext provides character-preserving edits via natural language instructions. When combined with PuLID, it adds another identity preservation layer.

**Kontext + PuLID Workflow:**
- PuLID provides identity injection
- Kontext provides instruction-based scene/pose control
- Downsampling factor: 3-4 (1=identical to original, 5=more prompt-following)
- Achieves 80-93% face consistency per test results
- Limited to medium portrait / close portrait shots

**VRAM:** Kontext FP8 ~12 GB, combined with PuLID ~16-18 GB total

**Limitation:** Face direction cannot be changed from reference -- designed for consistency within a pose context.

**Sources:**
- [Flux Kontext PuLID workflow](https://www.runcomfy.com/comfyui-workflows/flux-kontext-pulid-consistent-character-generation)
- [Kontext + PuLID experimental (Civitai)](https://civitai.com/models/1803573/flux-kontext-pulid-experimental)
- [FLUX.1 Kontext dev HuggingFace](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)

---

## Comparative Analysis

### Face Similarity Scores (InsightFace Cosine Similarity)

| Method | Similarity | Natural Appearance | Training Required | Speed |
|--------|------------|-------------------|-------------------|-------|
| Custom LoRA + FaceDetailer | **97%** | 9.6/10 | **Yes** (2-4 hrs) | Medium |
| ACE++ + Redux | **99%** | High | No | Medium |
| PuLID v0.9.1 | 88-93% | Good | No | Fast |
| InstantID | 82-86% | Good | No | Medium |
| IP-Adapter FaceID | 76-82% | Moderate | No | Fast |
| ReActor (alone) | ~68% | 6.2/10 | No | Very fast |

### What Each Method Handles Best

| Facial Aspect | Best Method | Why |
|---------------|-------------|-----|
| Bone structure / face shape | **LoRA** | Learned from training data |
| Skin texture / pores | **LoRA** + FaceDetailer | Encoded in weights |
| Eye color/shape | **LoRA** + PuLID | LoRA for shape, PuLID for color |
| Lip shape | **LoRA** | Subtle feature, needs training |
| Nose bridge / jawline | **LoRA** + ACE++ | Structure from LoRA, refinement from ACE++ |
| Hair style flexibility | **LoRA** (Hyper variant) | PuLID copies reference hair rigidly |
| Expression range | **LoRA** | Trained across expressions |
| Lighting adaptation | **ACE++** / CodeFormer | Context-aware blending |
| Final pixel accuracy | **ReActor** (HyperSwap) | Post-process correction at 256px |

---

## Recommended Multi-Method Pipeline

### The Ultimate Pipeline (Maximum Likeness)

```
Stage 1: IDENTITY ENCODING (one-time per person)
  Train custom face LoRA (15-30 reference photos)
  ~2 hours on 5090, reusable for all future generations

Stage 2: GENERATION (per image)
  Flux.2 dev + LoRA → Base image with correct identity
  + PuLID/ACE++ injection → Reinforce face structure from reference
  + FaceDetailer → Re-generate face region with LoRA for sharp detail

Stage 3: POST-PROCESSING (per image)
  ReActor (HyperSwap 256) → Pixel-level face swap correction
  + CodeFormer → Face restoration and enhancement
  + ReActorMaskHelper → Clean mask edges

Stage 4: QUALITY ASSESSMENT (per image)
  ComfyUI_FaceAnalysis → Cosine similarity score vs reference
  Target: cosine similarity >= 0.85 (baseline from real photos ~0.90)
```

### ComfyUI Workflow Architecture

```
[Load Reference Photos]
    |
    ├─ [Train LoRA] (one-time, offline)
    |
    v
[CheckpointLoader: Flux.2 dev FP8]
    |
    ├─ [LoRA Loader: person_lora.safetensors] (strength 0.8-1.0)
    |
    ├─ [PulidFluxModelLoader → ApplyPulidFlux]
    |   ├─ weight: 0.9
    |   ├─ method: "fidelity"
    |   ├─ fusion: "mean"
    |   └─ reference: best frontal photo
    |
    ├─ [CLIPTextEncode: "ohwx woman, description..."]
    |
    v
[KSampler] → [VAEDecode]
    |
    v
[FaceDetailer]
    ├─ denoise: 0.40-0.45
    ├─ face_margin: 1.6
    ├─ feather: 16-32
    ├─ LoRA: person_lora (strength 0.8-1.0)
    |
    v
[ReActorFaceSwap]
    ├─ model: hyperswap_1c_256.onnx
    ├─ face_detect: retinaface_resnet50
    ├─ restore_face: CodeFormer (weight 0.6)
    ├─ restore_visibility: 0.7
    |
    v
[FaceEmbedDistance] (ComfyUI_FaceAnalysis)
    ├─ similarity_metric: cosine
    ├─ reference_image: original_photo
    ├─ filter_thresh: 0.80
    |
    v
[SaveImage] (if passes threshold)
```

### Simplified Pipeline (No Training)

For performers where you don't have time/resources to train a LoRA:

```
[Flux.2 dev FP8] + [PuLID v0.9.1 (fidelity mode)]
    → [ReActor HyperSwap 256 + CodeFormer]
    → [FaceAnalysis check]
```

Expected similarity: 85-90% (vs 95%+ with the full pipeline).

### Alternative: ACE++ Path (Emerging, No Training)

```
[Flux Fill model] + [ACE++ instruction-based swap]
    → [Redux style anchor]
    → [FaceAnalysis check]
```

Expected similarity: up to 99% (per claims, needs verification on our hardware).

---

## Face Similarity Evaluation

### ComfyUI_FaceAnalysis Node

The primary tool for automated quality assessment:

**Installation:** `ComfyUI Manager → Install Custom Nodes → "FaceAnalysis"`

**Node: FaceEmbedDistance**
- `similarity_metric`: "cosine" (recommended) or "L2_norm"
- `filter_thresh`: 0.80 (reject images below this)
- `generate_image_overlay`: true (visual feedback)

**Establishing Baseline:**
1. Send 3 reference photos of the person to FaceEmbedDistance
2. Compare against a 4th real photo
3. The resulting score is your baseline (typically 0.85-0.92 for real photos)
4. Generated images should approach this baseline

**Backend Options:**
| Backend | License | Quality | Speed |
|---------|---------|---------|-------|
| InsightFace (buffalo_l) | Non-commercial | Best | Fast |
| AuraFace | Free | Good | Fast |
| DLib | Open | Moderate | Slower |

**Additional Metrics (for research/comparison):**
- SSIM: structural similarity (target >= 0.95 for "visually safe")
- LPIPS: perceptual similarity (target < 0.10, lower = better)
- FID: distributional realism (for batch evaluation)

**Sources:**
- [ComfyUI_FaceAnalysis GitHub](https://github.com/cubiq/ComfyUI_FaceAnalysis)
- [FaceEmbedDistance node docs](https://www.runcomfy.com/comfyui-nodes/ComfyUI_FaceAnalysis/FaceEmbedDistance)
- [Face Comparator alternative](https://github.com/fr0nky0ng/ComfyUI-Face-Comparator)
- [AI image quality metrics guide](https://unifiedimagetools.com/en/articles/ai-image-quality-metrics-lpips-ssim-2025)

---

## Hardware Requirements & Mapping

### Per-Method VRAM

| Method | Additional VRAM | Runs On |
|--------|----------------|---------|
| Flux.2 dev FP8 (base) | ~16 GB | 5090, 4090 |
| + PuLID v0.9.1 | +2-4 GB | 5090 (total ~20 GB) |
| + LoRA | +0.5 GB | Any (negligible) |
| + FaceDetailer | +0 (reuses model) | Same GPU |
| + ReActor | +1-2 GB (CPU OK) | CPU or any GPU |
| + FaceAnalysis | +0.5 GB | CPU or any GPU |
| **Full pipeline peak** | **~22 GB** | **5090 (32 GB) only** |

### Recommended GPU Assignment

| Task | GPU | Why |
|------|-----|-----|
| **Full generation pipeline** | 5090 (32 GB) on WORKSHOP | Only GPU with headroom for Flux + PuLID + LoRA |
| **LoRA training** | 5090 or 4090 on FOUNDRY | 24-32 GB needed; 2-4 hours per person |
| **Batch ReActor post-processing** | CPU or 5060Ti | Lightweight, can run on secondary GPU |
| **FaceAnalysis evaluation** | CPU | InsightFace runs on CPU efficiently |

### Can This Run on 4x5070Ti TP=4?

**No.** The pipeline requires single-GPU execution (ComfyUI doesn't support tensor parallelism). The 5090's 32 GB is the only GPU that fits the full pipeline at FP8. The 4090 (24 GB) can run the simplified pipeline (Flux FP8 + PuLID, no LoRA overhead) but is tight.

### Inference Speed Estimates (5090)

| Step | Time | Notes |
|------|------|-------|
| Flux.2 dev FP8 generation (1024x1024, 20 steps) | ~6 sec | SageAttention ~35% faster |
| PuLID identity injection | +1-2 sec | Added to generation time |
| FaceDetailer pass | ~3-5 sec | Face-only re-generation |
| ReActor face swap | ~1-2 sec | Very fast |
| CodeFormer restoration | ~0.5-1 sec | Lightweight |
| FaceAnalysis check | ~0.5 sec | InsightFace embedding comparison |
| **Total per image** | **~12-17 sec** | Full pipeline end-to-end |

### Batch Processing for Consistency

For generating multiple images of the same person:
1. Load LoRA once (stays in VRAM)
2. Load PuLID model once (stays in VRAM)
3. Batch prompts with different poses/scenes
4. ReActor + FaceAnalysis as post-pipeline filter
5. Reject images below cosine similarity threshold

Estimated throughput: **~3-5 images/minute** on 5090 with full pipeline.

---

## Stash Integration Opportunity

With 14,547 performer profiles in Stash, each containing multiple reference photos:

1. **Automated reference extraction:** Stash API can retrieve performer photos
2. **Auto-captioning pipeline:** JoyCaption or BLIP to generate .txt files
3. **Batch LoRA training queue:** Train face LoRAs for high-priority performers
4. **LoRA library management:** Store trained LoRAs in `/mnt/vault/models/loras/faces/`
5. **Generation API:** ComfyUI API endpoint accepts performer ID → retrieves LoRA + reference → generates

This creates a **programmatic face reproduction pipeline** where any Stash performer can be generated in any scene.

---

## Open Questions

1. **ACE++ vs LoRA+FaceDetailer:** ACE++ claims 99% similarity without training. Need to verify this on our hardware against the LoRA+FaceDetailer 97% benchmark. If ACE++ holds up, it eliminates the training step entirely.

2. **InsightFace licensing:** InsightFace models (buffalo_l, inswapper_128) are non-commercial only. For personal use this is fine, but AuraFace provides a free alternative with slightly lower quality. Need to decide which backend to standardize on.

3. **Flux.2 dev vs Flux.1 dev for face LoRAs:** Flux.2 at 32B requires Q4 quantization on 5090. The face detail loss from quantization may offset the quality gain from the larger model. Need side-by-side comparison.

4. **PuLID vs ACE++ for the identity injection step:** PuLID is proven but formally discontinued. ACE++ is newer, potentially better, but less battle-tested. Running both side-by-side on 5-10 reference faces would resolve this.

5. **HyperSwap quality vs inswapper:** The 256px HyperSwap models should produce sharper results than 128px inswapper, but comparison grids from the community are limited. Need to test on our hardware.

6. **LoRA training on Blackwell GPUs:** Kohya and ai-toolkit may need cu128 torch nightly and updated bitsandbytes for RTX 5090. FluxGym has explicit 50-series installation instructions.

---

## Recommendation

### Phase 1: Deploy Now (No Training Required)
1. Install `ComfyUI-ReActor`, `ComfyUI_FaceAnalysis`, and `ComfyUI-PuLID-Flux-Enhanced` nodes
2. Download `hyperswap_1c_256.onnx` and `pulid_flux_v0.9.1.safetensors`
3. Build the simplified PuLID + ReActor workflow on WORKSHOP (5090)
4. Establish baseline cosine similarity scores for test subjects
5. Test ACE++ as potential PuLID replacement

### Phase 2: LoRA Training Pipeline
1. Set up ai-toolkit (Ostris) on WORKSHOP or FOUNDRY 4090
2. Create dataset preparation workflow (auto-crop, auto-caption, folder structure)
3. Train face LoRA for 1-2 test performers (20 images each)
4. Build full pipeline: LoRA + PuLID + FaceDetailer + ReActor + FaceAnalysis
5. Compare similarity scores vs Phase 1 simplified pipeline
6. If significant improvement, scale to more performers

### Phase 3: Production Pipeline
1. Stash API integration for automated reference photo extraction
2. Batch LoRA training queue (overnight on FOUNDRY)
3. ComfyUI workflow templates for various scene types
4. Quality gate: reject images below 0.85 cosine similarity
5. LoRA library management at `/mnt/vault/models/loras/faces/`

### What "Pixel Perfect" Actually Means

True pixel-level reproduction is not achievable with current AI generation technology. What IS achievable:
- **97%+ identity recognition** (machine metrics) via LoRA + FaceDetailer
- **85-93%+ cosine similarity** (face embedding distance) for most subjects
- Images that pass casual human inspection as the same person
- Consistent identity across varied poses, lighting, and scenes

The remaining gap (typically subtle asymmetries, exact mole placement, fine wrinkle patterns) can be addressed by the ReActor post-processing step, which directly transplants these details from the source photo.

**The recommended pipeline achieves the closest thing to "pixel perfect" that is currently possible with local hardware: LoRA (identity foundation) + PuLID/ACE++ (structure reinforcement) + FaceDetailer (detail sharpening) + ReActor HyperSwap (pixel-level correction) + FaceAnalysis (quality gate).**

---

*Last updated: 2026-03-14*
