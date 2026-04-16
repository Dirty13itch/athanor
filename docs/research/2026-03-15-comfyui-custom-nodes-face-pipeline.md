# ComfyUI Custom Nodes for Face Pipeline

**Date:** 2026-03-15
**Status:** Complete -- recommendation ready
**Supports:** ADR-006 (Creative Pipeline), 2026-03-14 Pixel-Perfect Face Reproduction research
**Depends on:** Existing ComfyUI deployment on WORKSHOP (.225)

---

## Context

The face reproduction pipeline (researched 2026-03-14) requires four categories of custom nodes: face swap (ReActor), face similarity gate (FaceAnalysis), identity-preserving generation (PuLID/ACE++/InfiniteYou), and face enhancement (FaceDetailer via Impact Pack). This document covers the current installation state, compatibility status, and actionable gaps for each.

**Current WORKSHOP ComfyUI State (live audit 2026-03-15):**
- **ComfyUI:** Latest main (commit `f466b066`)
- **Base image:** NGC PyTorch 25.02-py3, upgraded to PyTorch 2.10.0+cu128
- **CUDA:** 12.8, ONNX Runtime GPU 1.24.3 (TensorRT + CUDA + CPU providers available)
- **InsightFace:** 0.7.3, antelopev2 model downloaded
- **GPU assignment:** GPU 1 (RTX 5060 Ti 16GB) -- NOT the 5090 (GPU 0, 32GB)
- **ComfyUI Manager:** Installed
- **Docker volumes:** custom_nodes persisted via named volume `comfyui-custom-nodes`

**Already Installed Custom Nodes:**
| Node | Status | Version/Commit |
|------|--------|----------------|
| ComfyUI-Manager | Installed | Active |
| ComfyUI-ReActor | Installed | v0.6.2-b1 (commit a2a61fd) |
| ComfyUI-PuLID-Flux | Installed | balazik fork (commit a80912f) |
| PuLID_ComfyUI | Installed | Original, maintenance mode (commit 93e0c4c) |
| ComfyUI_InfiniteYou | Installed | ByteDance official, v1.0.1 (commit 1c97939) |
| ComfyUI-Impact-Pack | Installed | Latest (commit 6a517eb) -- includes FaceDetailer |
| ComfyUI_IPAdapter_plus | Installed | Maintenance mode (commit a0f451a) |
| ComfyUI-KJNodes | Installed | Latest |
| ComfyUI-WanVideoWrapper | Installed | Latest |

---

## 1. ReActor (Face Swap)

**GitHub:** https://github.com/Gourieff/ComfyUI-ReActor
**Installed:** Yes (v0.6.2-b1)
**Installation method:** git clone into custom_nodes (also available via ComfyUI Manager)

### Python Dependencies
```
albumentations>=1.4.16
insightface==0.7.3
onnx>=1.14.0
opencv-python>=4.7.0.72
numpy==1.26.4
segment_anything
ultralytics
```

### HyperSwap 256 Support
HyperSwap models are supported in v0.6.2-b1. Three models available:
- `hyperswap_1a_256.onnx`
- `hyperswap_1b_256.onnx`
- `hyperswap_1c_256.onnx` (recommended, highest quality)

Models go in `ComfyUI/models/hyperswap/`. **Currently NOT downloaded** -- the directory does not exist on WORKSHOP.

Download source: https://huggingface.co/FaceFusion/FaceFusion-Models (FaceFusion Labs)

### RTX 5090 / Blackwell / CUDA 12.8 Issues

| Issue | Severity | Status |
|-------|----------|--------|
| Face restore (GFPGAN/CodeFormer) falls back to CPU on 5090 | Medium | Known bug, no fix yet. GPEN-BFR-512 is faster alternative |
| HyperSwap lip distortion reported | Medium | User report on issue #205, may be model-specific |
| Sequential frame processing (no batching) | Low | By design, ReActor is image-focused not video |
| ONNX Runtime GPU works on Blackwell | OK | Confirmed: TensorRT + CUDA providers available in our container |

**Critical note:** Face restore running on CPU means the restore step takes 3-4x longer than expected. For single-image workflows this adds ~5-10 seconds; for batch/video it compounds badly. The swap itself runs on GPU fine.

### Flux Compatibility
ReActor is a **post-processing** node -- it operates on the output image, not during generation. It is model-agnostic and works with any image source including Flux outputs.

### Action Items
- Download HyperSwap models to `/opt/ComfyUI/models/hyperswap/`
- Download `inswapper_128.onnx` to `/opt/ComfyUI/models/reactor/` (if not present)
- Test HyperSwap lip distortion on our specific use case
- Consider using GPEN-BFR-512 instead of GFPGAN if CPU restore is too slow

---

## 2. FaceAnalysis (Face Similarity Gate)

**GitHub:** https://github.com/cubiq/ComfyUI_FaceAnalysis
**Installed:** NO
**Installation method:** git clone into custom_nodes, or via ComfyUI Manager

### Python Dependencies
```
# requirements.txt (minimal)
insightface  # already installed
onnxruntime-gpu  # already installed
```
Optional: `dlib` (alternative backend, requires separate model downloads)

### Backends

| Backend | License | Quality | Already Available |
|---------|---------|---------|-------------------|
| InsightFace (buffalo_l) | Non-commercial | Best | Need to download buffalo_l model |
| AuraFace | Free/open | Good | Not installed |
| DLib | Open | Moderate | Not installed |

InsightFace `antelopev2` is already downloaded (used by InfiniteYou), but FaceAnalysis uses `buffalo_l` model by default. These are different model packages.

### Key Node: FaceEmbedDistance
- `similarity_metric`: "cosine" (recommended), "L2_norm", or "euclidean"
- `filter_thresh`: 0.80 (reject images below threshold)
- `generate_image_overlay`: visual feedback with similarity scores

### Maintenance Status
Repository in **maintenance-only mode** since April 2025. Developer no longer uses ComfyUI. Crucial PRs may be merged but no active development. The code is stable and functional.

### RTX 5090 / Blackwell Issues
No known issues. InsightFace embedding computation is lightweight and works fine with ONNX Runtime GPU on Blackwell (confirmed by our container having CUDA provider).

### Flux Compatibility
Model-agnostic post-processing node. Works with any generated image.

### Alternatives Considered

| Alternative | GitHub | Notes |
|-------------|--------|-------|
| ComfyUI-Face-Comparator | https://github.com/fr0nky0ng/ComfyUI-Face-Comparator | Default threshold 0.65, simpler API |
| ComfyUI_FaceSimilarity | https://github.com/chflame163/ComfyUI_FaceSimilarity | Outputs 0-100 float scale |
| ComfyUI-ImageSimilarity | https://github.com/ngosset/ComfyUI-ImageSimilarity | ResNet-based, not face-specific |

**Recommendation:** Use ComfyUI_FaceAnalysis (cubiq). Despite maintenance mode, it is the most mature and well-documented option with flexible backend choices.

### Action Items
- Clone into custom_nodes volume
- Download buffalo_l model pack to `models/insightface/models/buffalo_l/`
- Consider AuraFace as license-safe alternative

---

## 3. Identity-Preserving Generation (PuLID / ACE++ / InfiniteYou)

Three options are installed or available. Here is the current state of each:

### 3a. PuLID (Two installations present)

**ComfyUI-PuLID-Flux** (balazik fork, then forked by sipie800 as "Enhanced")
- GitHub: https://github.com/sipie800/ComfyUI-PuLID-Flux-Enhanced (sipie800, **DISCONTINUED**)
- GitHub: https://github.com/balazik/ComfyUI-PuLID-Flux (balazik, active fork)
- **Installed:** Yes (the balazik version, commit a80912f)
- Developer recommends migration to Flux Kontext or Qwen image edit as replacements

**PuLID_ComfyUI** (original)
- GitHub: https://github.com/ToTheBeginning/PuLID
- **Installed:** Yes, in **maintenance mode** (commit 93e0c4c)

**Python Dependencies:**
```
facexlib, insightface, onnxruntime, onnxruntime-gpu, ftfy, timm
```
All already installed in container.

**Model files needed:** `pulid_flux_v0.9.1.safetensors` -- **NOT downloaded** (models/pulid/ directory does not exist).

**RTX 5090 Issues:** A specific tutorial exists for ONNX/InsightFace setup on RTX 50-series (https://github.com/deepinsight/insightface/issues/2779). Our container already has working ONNX Runtime GPU with CUDA provider, so this should work.

**Face Similarity Score:** 88-93% (InsightFace cosine similarity)

### 3b. ACE++ (Alibaba)

**GitHub:** https://github.com/ali-vilab/ACE_plus
**Installed:** NO
**Installation method:** Copy `workflow/ComfyUI-ACE_Plus` folder from repo into custom_nodes

**Python Dependencies:**
```
pip install -r repo_requirements.txt  # from the ACE_plus repo
```

**Model Files Needed:**
- FLUX.1-Fill-dev model (separate download, ~24GB)
- Portrait LoRA: `comfyui_portrait_lora64.safetensors` (from `ali-vilab/ACE_Plus` on HuggingFace)
- Optional: Subject LoRA, Local Editing LoRA, FFT model

**Key Limitation:** Development on FLUX-based ACE++ has been **suspended** by Alibaba. They identified instability in post-training on FLUX foundation due to dataset heterogeneity. Future work will use Wan-series models instead.

**Face Similarity Score:** Up to 99% (with Redux, per community claims -- needs verification)

**VRAM:** ~20-24GB total (requires Flux Fill model loaded). Would NOT fit on current GPU assignment (5060 Ti 16GB). Requires 5090 (32GB).

### 3c. InfiniteYou (ByteDance) -- ICCV 2025 Highlight

**GitHub:** https://github.com/bytedance/ComfyUI_InfiniteYou
**Installed:** Yes (v1.0.1, commit 1c97939)
**Installation method:** git clone + pip install -r requirements.txt (also via ComfyUI Manager)

**Python Dependencies:**
```
facexlib>=0.3.0
onnxruntime>=1.19.2
insightface>=0.7.3
opencv-python>=4.11.0.86
huggingface_hub
```
All already installed.

**Model Files:**
- Auto-downloads on first run to `models/infinite_you/`
- Requires antelopev2 InsightFace model -- **already downloaded**
- Requires FLUX model (FP8 or FP16)

**VRAM:**
- BF16 full precision: ~43GB peak (does NOT fit any single GPU)
- FP8 precision: ~24GB peak (fits 5090 only, NOT 5060 Ti)

**Key Advantage over PuLID:**
- Official ByteDance support, ICCV 2025 paper
- InfuseNet architecture injects identity via residual connections (more robust than PuLID's attention injection)
- Better text-image alignment while preserving identity
- Actively maintained

**RTX 5090 Issues:** No known Blackwell-specific issues. Requires FP8 mode to fit 32GB VRAM.

### Comparison

| Feature | PuLID v0.9.1 | ACE++ | InfiniteYou |
|---------|-------------|-------|-------------|
| Face Similarity | 88-93% | Up to 99% (unverified) | Not benchmarked yet |
| Training Required | No | No | No |
| VRAM (with Flux FP8) | ~20 GB | ~24 GB | ~24 GB |
| Fits 5060 Ti (16GB) | Tight, possible | No | No |
| Fits 5090 (32GB) | Yes | Yes | Yes (FP8) |
| Flux compatibility | Native | Via Flux Fill | Native (Flux dev/schnell) |
| Maintenance status | Discontinued/forks | Suspended (Flux version) | Active |
| Installation complexity | Low | Medium | Low |

### Action Items
- Download `pulid_flux_v0.9.1.safetensors` for PuLID
- Consider ACE++ only if switching to 5090 GPU assignment
- InfiniteYou is already installed but needs 5090 to run at FP8
- **Critical: Current GPU 1 (5060 Ti) cannot run the full identity pipeline. Must switch to GPU 0 (5090).**

---

## 4. FaceDetailer (Face Enhancement/Inpainting)

**Part of:** ComfyUI-Impact-Pack
**GitHub:** https://github.com/ltdrdata/ComfyUI-Impact-Pack
**Installed:** Yes (latest, commit 6a517eb)
**Installation method:** git clone + subpack installation (also via ComfyUI Manager)

### Python Dependencies
```
# Main
segment-anything, scikit-image, piexif, transformers
opencv-python-headless, scipy, numpy, dill, matplotlib
sam2 (facebook)

# Subpack
matplotlib, ultralytics>=8.3.162, numpy, opencv-python-headless, dill
```
Requires YOLO models for face detection (auto-downloads on first use).

### Key Nodes
- **FaceDetailer** -- Detects faces, re-generates face region with denoise, composites back
- **FaceDetailerPipe** -- Pipeline version for complex workflows
- **DetailerForEachDebug** -- Debug view of each face region
- **SAMDetector** -- Segment Anything Model for precise face masking

### FaceDetailer Settings (from pixel-perfect research)
```
denoise: 0.40-0.45
face_margin: 1.6
feather: 16-32
LoRA strength: 0.8-1.0 (when using face LoRA)
```

### RTX 5090 / Blackwell Issues
No specific Blackwell issues reported. Impact Pack is one of the most widely used ComfyUI extensions and receives regular updates. The RTX 5090 with 32GB VRAM is described as the "gold standard" for Impact Pack workflows.

Basic FaceDetailer: ~6GB VRAM additional (YOLO detection + re-generation of face region)
Advanced two-pass: ~12GB+ additional

### Flux Compatibility
Fully compatible with Flux models. FaceDetailer uses the loaded checkpoint model to re-generate the face region -- whatever model is loaded (including Flux) is used for the detail pass.

### Action Items
- Already installed and functional
- Verify YOLO face detection model auto-downloads correctly
- Ensure SAM2 model is accessible

---

## Critical Finding: GPU Assignment

**ComfyUI is currently assigned to GPU 1 (RTX 5060 Ti, 16GB).** The Ansible default is `comfyui_gpu_device: "1"`.

This has major implications for the face pipeline:

| Pipeline | Min VRAM | Fits 5060 Ti (16GB)? | Fits 5090 (32GB)? |
|----------|----------|----------------------|---------------------|
| Flux FP8 alone | ~16 GB | Barely | Yes |
| Flux FP8 + PuLID | ~20 GB | No | Yes |
| Flux FP8 + InfiniteYou | ~24 GB | No | Yes |
| Flux FP8 + ACE++ | ~24 GB | No | Yes |
| Full pipeline (Flux + identity + FaceDetailer + ReActor) | ~22-26 GB | No | Yes |

**The creative face pipeline REQUIRES the 5090.** The 5060 Ti can only run Flux FP8 for basic generation without identity injection.

The Ansible default of GPU 1 was presumably set because GPU 0 (5090) is used by vLLM worker. This is a resource contention issue that needs architectural resolution (time-sharing, dedicated scheduling, or service swapping).

---

## Missing Model Files Summary

| Model | Path | Download Source | Size |
|-------|------|-----------------|------|
| hyperswap_1a/1b/1c_256.onnx | models/hyperswap/ | HuggingFace FaceFusion | ~500MB each |
| inswapper_128.onnx | models/reactor/ | HuggingFace | ~500MB |
| pulid_flux_v0.9.1.safetensors | models/pulid/ | HuggingFace ToTheBeginning/PuLID | ~1GB |
| buffalo_l model pack | models/insightface/models/buffalo_l/ | InsightFace | ~300MB |
| FLUX.1-Fill-dev (for ACE++) | diffusion_models/ or checkpoints/ | HuggingFace black-forest-labs | ~24GB |
| AuraFace (optional) | models/insightface/models/auraface/ | HuggingFace | ~200MB |

---

## Missing Custom Node: FaceAnalysis

**Not installed.** This is the quality gate for the pipeline.

Installation:
```bash
docker exec comfyui bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/cubiq/ComfyUI_FaceAnalysis.git"
```
No additional pip dependencies beyond what is already installed (insightface, onnxruntime-gpu).

---

## Recommendation

### Immediate (can do now, no GPU change needed)
1. Install ComfyUI_FaceAnalysis custom node
2. Download buffalo_l InsightFace model
3. Download HyperSwap 256 models for ReActor
4. Download pulid_flux_v0.9.1.safetensors
5. Remove duplicate PuLID installation (keep balazik `ComfyUI-PuLID-Flux`, remove `PuLID_ComfyUI` which is in maintenance mode)

### Requires GPU Reassignment (5090)
6. Change `comfyui_gpu_device` from "1" to "0" in Ansible vars (or resolve vLLM worker contention)
7. Test InfiniteYou with Flux FP8 (~24GB, fits 5090)
8. Test full pipeline: Flux FP8 + InfiniteYou/PuLID + FaceDetailer + ReActor + FaceAnalysis
9. Evaluate ACE++ if FLUX.1-Fill-dev model is downloaded

### Skip for Now
- ACE++ FLUX version (development suspended by Alibaba, future on Wan models)
- DLib backend for FaceAnalysis (InsightFace is better, already installed)
- sipie800 PuLID Enhanced (discontinued, developer recommends alternatives)

---

## Sources

- [ComfyUI-ReActor GitHub](https://github.com/Gourieff/ComfyUI-ReActor)
- [ReActor Issue #205: Face Restore on CPU with 5090](https://github.com/Gourieff/ComfyUI-ReActor/issues/205)
- [ComfyUI_FaceAnalysis GitHub](https://github.com/cubiq/ComfyUI_FaceAnalysis)
- [ACE++ GitHub](https://github.com/ali-vilab/ACE_plus)
- [InfiniteYou GitHub (ByteDance Official)](https://github.com/bytedance/ComfyUI_InfiniteYou)
- [ComfyUI-PuLID-Flux-Enhanced (sipie800, discontinued)](https://github.com/sipie800/ComfyUI-PuLID-Flux-Enhanced)
- [ComfyUI-PuLID-Flux (balazik fork)](https://github.com/balazik/ComfyUI-PuLID-Flux)
- [InsightFace ONNX Setup for RTX 50-series](https://github.com/deepinsight/insightface/issues/2779)
- [ComfyUI Impact Pack Guide](https://www.apatero.com/blog/comfyui-impact-pack-complete-guide-professional-face-enhancement-2025)
- [ComfyUI Blackwell Support Thread](https://github.com/Comfy-Org/ComfyUI/discussions/6643)
- [99% Face Consistency with ACE Plus + Redux](https://myaiforce.com/ace-plus-redux-portrait-bg-swap/)
- [ComfyUI-Face-Comparator (alternative)](https://github.com/fr0nky0ng/ComfyUI-Face-Comparator)

*Last updated: 2026-03-15*
