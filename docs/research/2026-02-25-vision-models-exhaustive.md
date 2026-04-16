# Vision-Language Models: Exhaustive Survey (Dec 2025 - Feb 2026)

**Date:** 2026-02-25
**Status:** Research complete
**Purpose:** Catalog every VLM, multimodal model, image understanding model, and OCR model relevant to Athanor's homelab deployment.

---

## Context

Athanor needs a vision model for:
1. **Screenshot understanding** for UI development
2. **Image analysis** for the creative pipeline (ComfyUI)
3. **Document/PDF understanding** for knowledge ingestion
4. **Video understanding** for media analysis
5. **Visual coding** (generate code from UI mockups)
6. **OCR** for document processing

**Hardware constraints:**
- Node 1: 4x 5070 Ti (16 GB each, TP=4 for text LLM) + 4090 (24 GB)
- Node 2: 5090 (32 GB) + 5060 Ti (16 GB)
- vLLM is the inference engine (NGC-based for Blackwell sm_120 GPUs)

**Key question:** Which VLM gives the best bang-for-VRAM across all six use cases, while fitting on available hardware and being vLLM-compatible?

---

## Table of Contents

1. [Tier 1: Fits on 16 GB GPU (Single Card)](#tier-1-fits-on-16-gb-gpu)
2. [Tier 2: Fits on 24-32 GB GPU or With Quantization](#tier-2-fits-on-24-32-gb-gpu)
3. [Tier 3: Requires Multi-GPU (72B+ class)](#tier-3-requires-multi-gpu)
4. [OCR Specialists](#ocr-specialists)
5. [Benchmark Comparison Table](#benchmark-comparison-table)
6. [vLLM Compatibility Matrix](#vllm-compatibility-matrix)
7. [Recommendation](#recommendation)
8. [Sources](#sources)

---

## Tier 1: Fits on 16 GB GPU

These models can run on a single 5070 Ti (16 GB), 5060 Ti (16 GB), or 4090 (24 GB) in BF16 or with light quantization.

### Qwen3-VL-4B-Instruct ★★★★★

| Field | Value |
|-------|-------|
| **Release** | May 2025 |
| **Org** | Qwen (Alibaba) |
| **Parameters** | 4B dense |
| **Architecture** | ViT + Qwen3-4B, Interleaved-MRoPE, DeepStack multi-level ViT fusion |
| **VRAM (BF16)** | ~10 GB |
| **Inputs** | Image, multi-image, video (hours-long), text |
| **Max Resolution** | Dynamic (configurable min/max pixels) |
| **Context** | 256K native (expandable to 1M) |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`Qwen3VLForConditionalGeneration`) |
| **HuggingFace** | `Qwen/Qwen3-VL-4B-Instruct` |

**Key improvements over Qwen2.5-VL:** Visual agent (GUI interaction), visual coding (HTML/CSS/JS from images), 32-language OCR (up from 19), improved spatial perception, 3D grounding, broader recognition (celebrities, anime, products, landmarks). The best efficiency-to-capability ratio in its class.

**Benchmark highlights:** Strong across all categories -- matches or exceeds many 7-8B models. Specific scores available in model card performance charts.

---

### Qwen2.5-VL-7B-Instruct ★★★★★

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Org** | Qwen (Alibaba) |
| **Parameters** | 7B |
| **Architecture** | Streamlined ViT (window attention, SwiGLU, RMSNorm) + Qwen2.5-7B |
| **VRAM (BF16)** | ~16 GB |
| **Inputs** | Image, multi-image, video (1+ hour), text |
| **Max Resolution** | Dynamic (configurable) |
| **Context** | 32K (extendable to 64K with YaRN) |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`Qwen2_5_VLForConditionalGeneration`) |
| **HuggingFace** | `Qwen/Qwen2.5-VL-7B-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU (val) | ~55 (estimated from family scaling) |
| DocVQA | **95.7** |
| ChartQA | **87.3** |
| TextVQA | **84.9** |
| OCRBench | **864** |
| MathVista | **68.2** |
| ScreenSpot | **84.7** |
| Video-MME (w/ subs) | **71.6** |

**Why it matters:** Exceptional OCR (864) and document understanding (95.7 DocVQA) make it the best document/screenshot model in the 7B class. Agent capabilities (ScreenSpot 84.7) enable UI interaction workflows.

---

### Qwen2.5-VL-3B-Instruct

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Parameters** | 3B |
| **VRAM (BF16)** | ~8 GB |
| **License** | Apache 2.0 (assumed, same family) |
| **vLLM** | Yes |
| **HuggingFace** | `Qwen/Qwen2.5-VL-3B-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| DocVQA | **93.9** |
| TextVQA | 79.3 |
| MMBench v1.1 | 77.6 |
| AndroidWorld SR | **90.8** |

**Why it matters:** Surprisingly strong DocVQA (93.9) at only 3B params. Ideal for dedicated OCR/document workloads on constrained hardware.

---

### InternVL3-8B

| Field | Value |
|-------|-------|
| **Release** | April 2025 |
| **Org** | OpenGVLab (Shanghai AI Lab) |
| **Parameters** | ~8B (InternViT-300M + Qwen2.5-7B) |
| **Architecture** | ViT-MLP-LLM, V2PE (Variable Visual Position Encoding) |
| **VRAM (BF16)** | ~16 GB |
| **Inputs** | Image, multi-image, video, text |
| **Max Resolution** | Dynamic 448x448 tiles |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`InternVLChatModel`) |
| **HuggingFace** | `OpenGVLab/InternVL3-8B` |

**Key features:** Mixed Preference Optimization (MPO), test-time scaling with VisualPRM-8B, native multimodal pre-training. Supports LMDeploy for optimized inference.

---

### InternVL2.5-8B

| Field | Value |
|-------|-------|
| **Release** | December 2024 |
| **Parameters** | ~8B (InternViT-300M + InternLM2.5-7B) |
| **VRAM (BF16)** | ~16 GB |
| **License** | MIT + Apache 2.0 |
| **vLLM** | Yes (`InternVLChatModel`) |
| **HuggingFace** | `OpenGVLab/InternVL2_5-8B` |

**Notable:** Trained on only 120B tokens (vs 1.4T for competitors). Very efficient training. Pixel unshuffle reduces visual tokens to 1/4.

---

### Phi-4-Multimodal-Instruct ★★★★★

| Field | Value |
|-------|-------|
| **Release** | February 2025 |
| **Org** | Microsoft |
| **Parameters** | 5.6B |
| **Architecture** | Phi-4-Mini backbone + vision encoder + speech encoder (Whisper-medium-300M) |
| **VRAM (BF16)** | ~12 GB |
| **Inputs** | Image, multi-image, video, **audio/speech** |
| **Context** | 128K tokens |
| **License** | **MIT** |
| **vLLM** | Yes (`Phi4MMForCausalLM`) |
| **HuggingFace** | `microsoft/Phi-4-multimodal-instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU | 55.1 |
| MMBench (dev-en) | **86.7** |
| DocVQA | **93.2** |
| TextVQA | **75.6** |
| OCRBench | **84.4** |
| AI2D | 82.3 |

**Why it matters:** Three modalities (vision + speech + text) in 5.6B params with MIT license. Best-in-class for combined vision+audio workloads. Function calling support. Could replace both a VLM and a speech model.

---

### MiniCPM-o-2_6 (Omni)

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Org** | OpenBMB |
| **Parameters** | 8B (SigLIP-400M + Whisper-medium-300M + ChatTTS-200M + Qwen2.5-7B) |
| **Architecture** | End-to-end omni-modal with TDM streaming |
| **VRAM (BF16)** | ~16 GB (int4: ~7 GB) |
| **Inputs** | Image, multi-image, video, **audio**, real-time streaming |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`MiniCPMO`) |
| **HuggingFace** | `openbmb/MiniCPM-o-2_6` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| OpenCompass (avg) | **70.2** |
| OCRBench | **897** (SOTA <25B) |
| Video-MME (w/ subs) | 67.9 |
| StreamingBench | **66.0** (beats GPT-4o) |

**Why it matters:** Full omni-modal (vision + audio + speech gen) in 8B params. OCRBench 897 is exceptional. Real-time streaming capability for live video understanding. Strongest omni model in its class.

---

### MiniCPM-V-4_5 ★★★★★

| Field | Value |
|-------|-------|
| **Release** | September 2025 |
| **Org** | OpenBMB |
| **Parameters** | 8B (SigLIP2-400M + Qwen3-8B) |
| **Architecture** | Unified 3D-Resampler, LLaVA-UHD |
| **VRAM** | ~28 GB for video (BF16), ~16 GB for image-only |
| **Inputs** | Image (1.8M pixels), multi-image, high-FPS video (10 FPS, 180+ frames), documents/PDFs |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`MiniCPMV`) |
| **HuggingFace** | `openbmb/MiniCPM-V-4_5` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| OpenCompass (avg) | **77.0** (SOTA <30B, surpasses GPT-4o-latest) |
| Video-MME | **73.5** |
| OCRBench | Leading (surpasses GPT-4o-latest) |
| OmniDocBench | **SOTA** |

**Why it matters:** The most capable 8B VLM as of this writing. Surpasses GPT-4o-latest on OpenCompass. 96x video compression enables efficient long-video understanding. Hybrid fast/deep thinking mode. However, video mode needs ~28 GB (fits 5090 only).

---

### Eagle2.5-8B

| Field | Value |
|-------|-------|
| **Release** | April 2025 |
| **Org** | NVIDIA |
| **Parameters** | 8B (SigLIP2-So400m + Qwen2.5-7B) |
| **VRAM (BF16)** | ~16 GB |
| **Inputs** | Image (4K HD), multi-image, video (**512 frames**), multi-page documents |
| **License** | NSCLv1 (academic/non-profit research only) |
| **vLLM** | Yes (`Eagle2_5_VLForConditionalGeneration`) |
| **HuggingFace** | `nvidia/Eagle2.5-8B` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU (val) | 55.8 |
| DocVQA (test) | **94.1** |
| OCRBench (test) | **869** |
| ChartQA (test) | **87.5** |
| MathVista | 67.8 |
| MMBench v1.1 | 81.7 |

**Why it matters:** Matches Qwen2.5-VL-72B average image benchmark at 8B params. 512-frame video support is industry-leading. However, the NSCLv1 license restricts commercial use.

---

### Pixtral-12B-2409

| Field | Value |
|-------|-------|
| **Release** | September 2024 |
| **Org** | Mistral AI |
| **Parameters** | 12.4B (12B decoder + 400M vision encoder) |
| **Architecture** | Natively multimodal decoder with interleaved training |
| **VRAM (BF16)** | ~24 GB |
| **Inputs** | Image (variable sizes), multi-image, text |
| **Context** | 128K tokens |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`PixtralForConditionalGeneration`, native Mistral format) |
| **HuggingFace** | `mistralai/Pixtral-12B-2409` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU (CoT) | 52.5 |
| MathVista (CoT) | 58.0 |
| ChartQA (CoT) | 81.8 |
| DocVQA (ANLS) | 90.7 |
| VQAv2 | 78.6 |
| MMLU (5-shot) | 69.2 |

---

### Gemma 3 4B-IT

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Org** | Google |
| **Parameters** | 4B |
| **Architecture** | SigLIP-So400m vision encoder + Gemma 3 4B decoder |
| **VRAM (BF16)** | ~10 GB |
| **Inputs** | Image (896x896, 256 tokens), text |
| **Context** | 128K tokens |
| **License** | Gemma (permissive with use restrictions) |
| **vLLM** | Yes (`Gemma3ForConditionalGeneration`) |
| **HuggingFace** | `google/gemma-3-4b-it` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| DocVQA (val) | 72.8 |
| TextVQA (val) | 58.9 |
| ChartQA | 63.6 |
| AI2D | 63.2 |

---

### Gemma 3 12B-IT

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Parameters** | 12B |
| **VRAM (BF16)** | ~24 GB |
| **License** | Gemma |
| **vLLM** | Yes |
| **HuggingFace** | `google/gemma-3-12b-it` |

**Benchmarks:** DocVQA 82.3, TextVQA 66.5, ChartQA 74.7, AI2D 75.2, MMLU 74.5.

---

### Kimi-VL-A3B-Instruct

| Field | Value |
|-------|-------|
| **Release** | April 2025 |
| **Org** | Moonshot AI |
| **Parameters** | 16B total / **2.8B active** (MoE) |
| **Architecture** | MoonViT (native-resolution) + MoE LLM |
| **VRAM** | ~32 GB BF16 (fits 5090) |
| **Inputs** | Image, multi-image, video, long documents |
| **Context** | 128K tokens |
| **License** | **MIT** |
| **vLLM** | Yes (`KimiVLForConditionalGeneration`) |
| **HuggingFace** | `moonshotai/Kimi-VL-A3B-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU (val) | 57.0 |
| MathVista | 68.7 |
| OCRBench | **867** |
| InfoVQA | 83.2 |
| MMBench v1.1 | 83.1 |
| LongVideoBench | 64.5 |

**Why it matters:** Only 2.8B active params with MoE but achieves 8B+ performance. MIT license. Native resolution vision encoder avoids information loss from resizing.

---

### Llama 3.2 11B Vision Instruct

| Field | Value |
|-------|-------|
| **Release** | September 2024 |
| **Org** | Meta |
| **Parameters** | 11B |
| **Architecture** | Llama 3.1 + cross-attention vision adapter |
| **VRAM (BF16)** | ~22 GB |
| **Inputs** | Image + text (English only for vision) |
| **Context** | 128K tokens |
| **License** | Llama 3.2 Community (commercial, EU restrictions on multimodal) |
| **vLLM** | Yes (via `MllamaForConditionalGeneration`) |
| **HuggingFace** | `meta-llama/Llama-3.2-11B-Vision-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU | 50.7 |
| DocVQA | 88.4 |
| ChartQA | 83.4 |
| MathVista | 51.5 |
| AI2D | **91.1** |

---

### SmolVLM2-2.2B-Instruct

| Field | Value |
|-------|-------|
| **Release** | April 2025 |
| **Org** | HuggingFace |
| **Parameters** | 2.2B (SigLIP-So400m + SmolLM2-1.7B) |
| **VRAM** | **5.2 GB** |
| **Inputs** | Image, multi-image, **video** |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`SmolVLMForConditionalGeneration`) |
| **HuggingFace** | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU | 42.0 |
| MathVista | 51.5 |
| OCRBench | 72.9 |
| DocVQA (val) | 79.98 |
| Video-MME | 52.1 |

**Why it matters:** Video-capable at only 5 GB VRAM. Could run alongside other models on any GPU in the cluster.

---

### Moondream2

| Field | Value |
|-------|-------|
| **Release** | Continuously updated (latest: June 2025) |
| **Org** | vikhyatk |
| **Parameters** | 2B |
| **VRAM** | ~4 GB |
| **Inputs** | Image |
| **License** | Apache 2.0 |
| **vLLM** | No (custom inference only) |
| **HuggingFace** | `vikhyatk/moondream2` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| ChartQA | 77.5 (82.2 with PoT) |
| ScreenSpot (UI) | **80.4** |
| DocVQA | 79.3 |
| TextVQA | 76.3 |
| OCRBench | 61.2 |

**Why it matters:** Object detection, pointing, grounded reasoning at 2B params. ScreenSpot 80.4 is strong for UI understanding. No vLLM support limits deployment flexibility.

---

### Phi-3.5-Vision-Instruct

| Field | Value |
|-------|-------|
| **Release** | August 2024 |
| **Org** | Microsoft |
| **Parameters** | 4.2B |
| **VRAM (BF16)** | ~10 GB |
| **Inputs** | Image, multi-image |
| **License** | MIT |
| **vLLM** | Yes (`Phi3VForCausalLM`) |
| **HuggingFace** | `microsoft/Phi-3.5-vision-instruct` |

**Note:** Superseded by Phi-4-multimodal-instruct but still useful as a smaller alternative.

---

### MiniCPM-V-2_6

| Field | Value |
|-------|-------|
| **Release** | August 2024 (updated January 2025) |
| **Parameters** | 8B (SigLIP-400M + Qwen2-7B) |
| **VRAM** | ~16 GB (int4: ~7 GB) |
| **Inputs** | Image (1.8M pixels), multi-image, video |
| **License** | Apache 2.0 (code), MiniCPM Model License (weights) |
| **vLLM** | Yes (`MiniCPMV`) |
| **HuggingFace** | `openbmb/MiniCPM-V-2_6` |

**Benchmarks:** OpenCompass avg 65.2, OCRBench SOTA (<25B), surpasses GPT-4V on Video-MME.

---

### Molmo-7B-D-0924

| Field | Value |
|-------|-------|
| **Release** | September 2024 |
| **Org** | Allen AI |
| **Parameters** | 7B (CLIP ViT-L + Qwen2-7B) |
| **VRAM (BF16)** | ~14 GB |
| **Inputs** | Image (RGB only) |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`MolmoForCausalLM`) |
| **HuggingFace** | `allenai/Molmo-7B-D-0924` |

**Benchmarks:** Avg 77.3 across 11 benchmarks (vs GPT-4o 78.5). Human preference Elo 1056.

---

### GLM-4V-9B

| Field | Value |
|-------|-------|
| **Release** | August 2024 |
| **Org** | Z.ai (Tsinghua) |
| **Parameters** | 14B (includes vision params) |
| **VRAM (BF16)** | ~28 GB |
| **Inputs** | Image (1120x1120), text (Chinese/English) |
| **License** | GLM-4 Custom |
| **vLLM** | Yes (`GLM4VForCausalLM`) |
| **HuggingFace** | `THUDM/glm-4v-9b` |

**Benchmarks:** MMBench-EN 81.1, OCRBench 786, SEEDBench 76.8.

---

## Tier 2: Fits on 24-32 GB GPU

### Mistral Small 3.1 24B Instruct

| Field | Value |
|-------|-------|
| **Release** | March 2025 |
| **Org** | Mistral AI |
| **Parameters** | 24B |
| **VRAM (BF16)** | ~55 GB (needs quantization for 32 GB GPU) |
| **Inputs** | Image (up to 10), text |
| **Context** | 128K tokens |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`Mistral3ForConditionalGeneration` or `PixtralForConditionalGeneration`) |
| **HuggingFace** | `mistralai/Mistral-Small-3.1-24B-Instruct-2503` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU | **64.0** |
| DocVQA | **94.08** |
| ChartQA | **86.24** |
| MathVista | **68.91** |
| AI2D | **93.72** |

**Why it matters:** Best vision benchmarks in the 24B class. With AWQ/GPTQ quantization could fit on 5090 (32 GB). Apache 2.0 license.

---

### Gemma 3 27B-IT

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Org** | Google |
| **Parameters** | 27B |
| **VRAM (BF16)** | ~54 GB (needs quantization for 32 GB) |
| **Inputs** | Image (896x896, 256 tokens each), text |
| **Context** | 128K tokens |
| **License** | Gemma |
| **vLLM** | Yes (`Gemma3ForConditionalGeneration`) |
| **HuggingFace** | `google/gemma-3-27b-it` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| DocVQA (val) | 85.6 |
| TextVQA (val) | 68.6 |
| ChartQA | 76.3 |
| AI2D | 79.0 |
| MMLU (5-shot) | 78.6 |

---

### Llama 4 Scout 17B-16E-Instruct

| Field | Value |
|-------|-------|
| **Release** | April 2025 |
| **Org** | Meta |
| **Parameters** | 109B total / **17B active** (16 experts) |
| **Architecture** | MoE with early fusion for native multimodality |
| **VRAM** | Fits single H100 with int4 quantization |
| **Inputs** | Image (up to 5), text |
| **Context** | **10M tokens** |
| **License** | Llama 4 Community |
| **vLLM** | Yes (`Llama4ForConditionalGeneration`) |
| **HuggingFace** | `meta-llama/Llama-4-Scout-17B-16E-Instruct` |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU | **73.4** |
| DocVQA | **94.4** |
| ChartQA | **90.0** |
| MathVista | **73.7** |

**Why it matters:** Exceptional benchmarks. 10M token context is unprecedented. However, 109B total params means full model is ~218 GB in BF16. Even with only 17B active, all expert weights must be loaded. Likely needs significant quantization to fit on available hardware. VRAM behavior with vLLM MoE on consumer GPUs is untested territory.

---

### InternVL3.5-14B ★★★★

| Field | Value |
|-------|-------|
| **Release** | August 2025 |
| **Org** | OpenGVLab |
| **Parameters** | 15.1B (InternViT-300M + Qwen3-14.8B) |
| **Architecture** | ViT-MLP-LLM + Visual Resolution Router (ViR) + Cascade RL |
| **VRAM (BF16)** | ~30 GB (fits 5090) |
| **Inputs** | Image, multi-image, video, text |
| **License** | Apache 2.0 |
| **vLLM** | Yes (`InternVLChatModel`) |
| **HuggingFace** | `OpenGVLab/InternVL3_5-14B` |

**Key innovations:**
- **Cascade RL:** +16% improvement on reasoning benchmarks
- **Visual Resolution Router:** 50% token reduction with ~100% performance retained
- **Decoupled Vision-Language Deployment:** 4.05x inference speedup
- **Deep Thinking mode:** step-by-step reasoning with `<think>` tags
- **MMBench v1.1:** 84.1

**Why it matters:** The latest open-source VLM with the strongest reasoning capabilities in the <20B class. Fits on 5090. Cascade RL and deep thinking are state-of-the-art training techniques.

---

### PaliGemma 2 28B

| Field | Value |
|-------|-------|
| **Release** | December 2024 |
| **Org** | Google |
| **Parameters** | 28B (SigLIP-So400m + Gemma 2 27B) |
| **VRAM (BF16)** | ~56 GB |
| **Inputs** | Image (896x896) + text prompt |
| **License** | Gemma |
| **vLLM** | Yes (`PaliGemmaForConditionalGeneration`) |
| **HuggingFace** | `google/paligemma2-28b-pt-896` |

**Note:** Pre-trained model designed for fine-tuning. Not a chatbot. Single-turn inference only. VQAv2 85.8%, ChartQA 85.1%.

---

### QVQ-72B-Preview (Visual Reasoning)

| Field | Value |
|-------|-------|
| **Release** | December 2024 |
| **Org** | Qwen |
| **Parameters** | 73B |
| **Architecture** | Based on Qwen2-VL-72B |
| **Inputs** | Single images only (no video) |
| **License** | Qwen |
| **vLLM** | Yes (`Qwen2VLForConditionalGeneration`) |
| **HuggingFace** | `Qwen/QVQ-72B-Preview` |

**Benchmarks:** MMMU 70.3, MathVista 71.4, MathVision 35.9. Specialized for visual mathematical reasoning.

---

## Tier 3: Requires Multi-GPU (72B+ class)

These models are documented for completeness. They would require TP across multiple GPUs or the entire Node 1 TP=4 setup, displacing the text LLM.

### Qwen2.5-VL-72B-Instruct

| Field | Value |
|-------|-------|
| **Release** | January 2025 |
| **Parameters** | 72B |
| **VRAM (BF16)** | ~144 GB (TP=4 minimum) |
| **License** | Qwen License |
| **vLLM** | Yes |

**Benchmarks:**

| Benchmark | Score |
|-----------|-------|
| MMMU (val) | **70.2** |
| DocVQA (val) | **96.4** |
| ChartQA | **89.5** |
| OCRBench-V2 (en) | **61.5** |
| MathVista | **74.8** |
| Video-MME (w/ subs) | **79.1** |
| ScreenSpot | **87.1** |

The gold standard for open-source VLMs but requires TP=4 on 80 GB GPUs. Would need heavy quantization for Athanor hardware.

### InternVL3-78B

| Release | April 2025 | Parameters | 78B | License | Qwen + MIT | vLLM | Yes |

### InternVL2.5-78B

| Release | December 2024 | Parameters | 78B | License | Qwen | vLLM | Yes |

### LLaVA-OneVision-72B

| Release | August 2024 | Parameters | 73B | License | Apache 2.0 | vLLM | Yes |

### Molmo-72B

| Release | September 2024 | Parameters | 73B | License | Apache 2.0 | vLLM | Yes |

### NVLM-D-72B

| Release | September 2024 | Parameters | 72B | License | CC-BY-NC-4.0 (non-commercial) | vLLM | Yes |

### Llama 3.2 90B Vision

| Release | September 2024 | Parameters | 90B | License | Llama 3.2 Community | vLLM | Yes |
| MMMU | 60.3 | DocVQA | 90.1 | ChartQA | 85.5 | MathVista | 57.3 |

---

## OCR Specialists

### DeepSeek-OCR ★★★★

| Field | Value |
|-------|-------|
| **Release** | October 2025 |
| **Org** | DeepSeek |
| **License** | **MIT** |
| **vLLM** | Yes (`DeepseekOCRForCausalLM`) |
| **HuggingFace** | `deepseek-ai/DeepSeek-OCR` |

**Capabilities:** Document-to-Markdown, math formula recognition, table extraction, multi-column handling, historical document scanning. Overall benchmark: 75.70% on olmOCR-bench. Available in Tiny/Small/Base/Large/Gundam sizes.

### DeepSeek-OCR-2

vLLM: Yes (`DeepseekOCR2ForCausalLM`). Second generation, `deepseek-ai/DeepSeek-OCR-2`.

### GOT-OCR-2.0-hf

| Field | Value |
|-------|-------|
| **Release** | September 2024 |
| **Org** | StepFun |
| **Parameters** | 0.6B |
| **VRAM** | ~1.2 GB |
| **License** | Apache 2.0 |
| **vLLM** | No (custom transformers only) |
| **HuggingFace** | `stepfun-ai/GOT-OCR-2.0-hf` |

**Capabilities:** Plain/formatted OCR, LaTeX, Markdown, tables, charts, math formulas, geometric shapes, molecular formulas, sheet music (MEI format). Region-based OCR with bounding boxes. Multi-page processing.

### Florence-2-Large

| Field | Value |
|-------|-------|
| **Release** | November 2023 (updated) |
| **Org** | Microsoft |
| **Parameters** | 0.77B |
| **VRAM** | ~2 GB |
| **License** | **MIT** |
| **vLLM** | No (custom transformers only) |
| **HuggingFace** | `microsoft/Florence-2-large` |

**Capabilities:** Multi-task: captioning, object detection, phrase grounding, dense region captioning, OCR, OCR with bounding boxes. Trained on FLD-5B (5.4B annotations across 126M images). Extremely versatile for a sub-1B model.

### GLM-OCR

| vLLM | Yes (`GlmOcrForConditionalGeneration`) | HuggingFace | `zai-org/GLM-OCR` |

### HunyuanOCR

| vLLM | Yes (`HunYuanVLForConditionalGeneration`) | HuggingFace | `tencent/HunyuanOCR` |

### LightOnOCR-1B

| vLLM | Yes (`LightOnOCRForConditionalGeneration`) | HuggingFace | `lightonai/LightOnOCR-1B` |

### PaddleOCR-VL

| vLLM | Yes (`PaddleOCRVLForConditionalGeneration`) | HuggingFace | `PaddlePaddle/PaddleOCR-VL` |

---

## Additional Notable Models (from vLLM supported list)

These were found in the vLLM supported models list but not individually detailed above:

| Model | Org | vLLM Arch | Modalities | HuggingFace |
|-------|-----|-----------|------------|-------------|
| Aya Vision 8B/32B | Cohere | `AyaVisionForConditionalGeneration` | T + I | `CohereLabs/aya-vision-8b` |
| BAGEL-7B-MoT | ByteDance | `BagelForConditionalGeneration` | T + I | `ByteDance-Seed/BAGEL-7B-MoT` |
| Bee-8B | Open-Bee | `BeeForConditionalGeneration` | T + I | `Open-Bee/Bee-8B-RL` |
| Command A Vision | Cohere | `Cohere2VisionForConditionalGeneration` | T + I | `CohereLabs/command-a-vision-07-2025` |
| GLM-4.1V-9B-Thinking | Z.ai | `Glm4vForConditionalGeneration` | T + I + V | `zai-org/GLM-4.1V-9B-Thinking` |
| GLM-4.5V | Z.ai | `Glm4vMoeForConditionalGeneration` | T + I + V | `zai-org/GLM-4.5V` |
| Gemma 3n (E2B/E4B) | Google | `Gemma3nForConditionalGeneration` | T + I + A | `google/gemma-3n-E2B-it` |
| Intern-S1 / S1-Pro | InternLM | `InternS1ForConditionalGeneration` | T + I + V | `internlm/Intern-S1` |
| Keye-VL-8B | Kwai | `KeyeForConditionalGeneration` | T + I + V | `Kwai-Keye/Keye-VL-8B-Preview` |
| Kimi-K2.5 | Moonshot | `KimiK25ForConditionalGeneration` | T + I | `moonshotai/Kimi-K2.5` |
| LFM2-VL (450M/3B/8B) | Liquid AI | `Lfm2VlForConditionalGeneration` | T + I | `LiquidAI/LFM2-VL-3B` |
| Llama Nemotron Nano VL | NVIDIA | `Llama_Nemotron_Nano_VL` | T + I | `nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1` |
| MiniMax-VL-01 | MiniMax | `MiniMaxVL01ForConditionalGeneration` | T + I | `MiniMaxAI/MiniMax-VL-01` |
| Molmo2 (4B/8B) | Allen AI | `Molmo2ForConditionalGeneration` | T + I / V | `allenai/Molmo2-8B` |
| OpenCUA-7B | xLang | `OpenCUAForConditionalGeneration` | T + I | `xlangai/OpenCUA-7B` |
| Ovis2/2.5/2.6 | AIDC-AI | `Ovis` / `Ovis2_5` / `Ovis2_6ForCausalLM` | T + I + V | `AIDC-AI/Ovis2.5-9B` |
| Qwen2.5-Omni-7B | Qwen | `Qwen2_5OmniThinkerForConditionalGeneration` | T + I + V + A | `Qwen/Qwen2.5-Omni-7B` |
| Qwen3.5-9B | Qwen | `Qwen3_5ForConditionalGeneration` | T + I + V | `Qwen/Qwen3.5-9B-Instruct` |
| Qwen3.5-35B-A3B (MoE) | Qwen | `Qwen3_5MoeForConditionalGeneration` | T + I + V | `Qwen/Qwen3.5-35B-A3B-Instruct` |
| Qwen3-VL-30B-A3B (MoE) | Qwen | `Qwen3VLMoeForConditionalGeneration` | T + I + V | `Qwen/Qwen3-VL-30B-A3B-Instruct` |
| Qwen3-Omni-30B-A3B | Qwen | `Qwen3OmniMoeThinkerForConditionalGeneration` | T + I + V + A | `Qwen/Qwen3-Omni-30B-A3B-Instruct` |
| R-VL-4B | YannQi | `RForConditionalGeneration` | T + I | `YannQi/R-4B` |
| Skywork-R1V-38B | Skywork | `SkyworkR1VChatModel` | T + I | `Skywork/Skywork-R1V-38B` |
| Step3-VL / Step3-VL-10B | StepFun | `Step3VLForConditionalGeneration` | T + I | `stepfun-ai/Step3-VL-10B` |
| Tarsier2 | Omni-Research | `Tarsier2ForConditionalGeneration` | T + I + V | `omni-research/Tarsier2-7b-0115` |
| ERNIE 4.5-VL | Baidu | `Ernie4_5_VLMoeForConditionalGeneration` | T + I / V | `baidu/ERNIE-4.5-VL-28B-A3B-PT` |

---

## Benchmark Comparison Table

Top models by benchmark, filtered to models that fit on Athanor hardware (<=32 GB single GPU or <=88 GB TP=4):

| Model | Params | VRAM | MMMU | DocVQA | OCRBench | ChartQA | MathVista | Video-MME | License |
|-------|--------|------|------|--------|----------|---------|-----------|-----------|---------|
| MiniCPM-V-4_5 | 8B | ~16-28 GB | -- | -- | SOTA | -- | -- | **73.5** | Apache 2.0 |
| MiniCPM-o-2_6 | 8B | ~16 GB | -- | -- | **897** | -- | -- | 67.9 | Apache 2.0 |
| Eagle2.5-8B | 8B | ~16 GB | 55.8 | **94.1** | **869** | **87.5** | 67.8 | -- | NSCLv1 |
| Qwen2.5-VL-7B | 7B | ~16 GB | ~55 | **95.7** | **864** | **87.3** | **68.2** | 71.6 | Apache 2.0 |
| Kimi-VL-A3B | 16B/2.8B | ~32 GB | 57.0 | -- | **867** | -- | **68.7** | -- | MIT |
| Qwen3-VL-4B | 4B | ~10 GB | -- | -- | -- | -- | -- | -- | Apache 2.0 |
| InternVL3.5-14B | 15B | ~30 GB | -- | -- | -- | -- | -- | -- | Apache 2.0 |
| Mistral Small 3.1 | 24B | ~55 GB* | **64.0** | **94.08** | -- | **86.24** | **68.91** | -- | Apache 2.0 |
| Phi-4-multimodal | 5.6B | ~12 GB | 55.1 | **93.2** | **84.4** | -- | -- | -- | MIT |
| Llama 4 Scout | 109B/17B | Large* | **73.4** | **94.4** | -- | **90.0** | **73.7** | -- | Llama 4 |
| Gemma 3 27B | 27B | ~54 GB* | -- | 85.6 | -- | 76.3 | -- | -- | Gemma |
| Pixtral-12B | 12.4B | ~24 GB | 52.5 | 90.7 | -- | 81.8 | 58.0 | -- | Apache 2.0 |
| Llama 3.2 11B | 11B | ~22 GB | 50.7 | 88.4 | -- | 83.4 | 51.5 | -- | Llama 3.2 |

*Needs quantization for available hardware.

---

## vLLM Compatibility Matrix

All models confirmed in vLLM's official supported models list as of Feb 2026:

| Model Family | vLLM Architecture | Multi-Image | Video | Audio | LoRA |
|-------------|-------------------|-------------|-------|-------|------|
| Qwen2.5-VL | `Qwen2_5_VLForConditionalGeneration` | Yes | Yes | No | Yes |
| Qwen3-VL | `Qwen3VLForConditionalGeneration` | Yes | Yes | No | Yes |
| Qwen3-VL-MoE | `Qwen3VLMoeForConditionalGeneration` | Yes | Yes | No | Yes |
| Qwen3.5 | `Qwen3_5ForConditionalGeneration` | Yes | Yes | No | Yes |
| Qwen2.5-Omni | `Qwen2_5OmniThinkerForConditionalGeneration` | Yes | Yes | Yes | Yes |
| Qwen3-Omni | `Qwen3OmniMoeThinkerForConditionalGeneration` | Yes | Yes | Yes | Yes |
| InternVL 2.0/2.5/3.0/3.5 | `InternVLChatModel` | Yes | Yes* | No | Yes |
| InternVL 3.0 HF | `InternVLForConditionalGeneration` | Yes | Yes | No | Yes |
| Phi-4-multimodal | `Phi4MMForCausalLM` | Yes | No | Yes | Yes |
| Phi-3.5-Vision | `Phi3VForCausalLM` | Yes | No | No | No |
| MiniCPM-O | `MiniCPMO` | Yes | Yes | Yes | Yes |
| MiniCPM-V | `MiniCPMV` | Yes | Yes | No | Yes |
| Gemma 3 | `Gemma3ForConditionalGeneration` | Yes | No | No | Yes |
| Gemma 3n | `Gemma3nForConditionalGeneration` | Image | No | Yes | No |
| Pixtral/Mistral 3 | `PixtralForConditionalGeneration` | Yes | No | No | Yes |
| Mistral 3 HF | `Mistral3ForConditionalGeneration` | Yes | No | No | Yes |
| Llama 4 | `Llama4ForConditionalGeneration` | Yes | No | No | Yes |
| Llama 3.2 Vision | `MllamaForConditionalGeneration` | No | No | No | Yes |
| LLaVA-OneVision | `LlavaOnevisionForConditionalGeneration` | Yes | Yes | No | No |
| DeepSeek-VL2 | `DeepseekVLV2ForCausalLM` | Yes | No | No | No |
| DeepSeek-OCR/OCR-2 | `DeepseekOCRForCausalLM` | Yes | No | No | Yes |
| Eagle2.5 | `Eagle2_5_VLForConditionalGeneration` | Yes | No | No | Yes |
| Molmo / Molmo2 | `MolmoForCausalLM` / `Molmo2ForConditionalGeneration` | Yes | Yes* | No | Yes |
| SmolVLM2 | `SmolVLMForConditionalGeneration` | No | No | No | Yes |
| Kimi-VL | `KimiVLForConditionalGeneration` | Yes | No | No | No |
| GLM-4V | `GLM4VForCausalLM` | No | No | No | Yes |
| GLM-4.1V / GLM-4.5V | `Glm4vForConditionalGeneration` / `Glm4vMoeForConditionalGeneration` | Yes | Yes | No | Yes |
| GLM-OCR | `GlmOcrForConditionalGeneration` | Yes | No | No | Yes |
| NVLM-D | `NVLM_D_Model` | Yes | No | No | No |
| PaliGemma 2 | `PaliGemmaForConditionalGeneration` | No | No | No | Yes |
| Fuyu-8B | `FuyuForCausalLM` | No | No | No | No |

*Video support varies by version; InternVL2.5+ with Qwen2.5 backbone and Molmo2 confirmed.

Source: https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md

---

## Recommendation

### Primary VLM: Qwen2.5-VL-7B-Instruct

**Rationale:**
1. **Best overall benchmark profile** in the 7B class: DocVQA 95.7, OCRBench 864, ChartQA 87.3, ScreenSpot 84.7
2. **All six use cases covered**: screenshot understanding (ScreenSpot 84.7), image analysis, document/PDF (DocVQA 95.7), video (1+ hour support, Video-MME 71.6), visual coding (agent capabilities), OCR (864)
3. **Fits on a single 5070 Ti** (16 GB) or 4090 (24 GB) in BF16
4. **Apache 2.0 license** -- no restrictions
5. **Native vLLM support** with LoRA, multi-image, and video
6. **Mature ecosystem**: well-documented, widely deployed, strong community
7. **Same family as text LLM** (Qwen3-32B-AWQ) -- consistent tokenizer/chat format reduces integration friction

**Deployment plan:** Run on Node 1 GPU 4 (4090, 24 GB) alongside embedding model, or on Node 2 5090 (32 GB) for maximum headroom. Alternatively, run AWQ-quantized version on any 16 GB GPU.

### Upgrade Path: Qwen3-VL-4B-Instruct

When benchmarks are confirmed, Qwen3-VL-4B may supersede Qwen2.5-VL-7B due to:
- Smaller footprint (~10 GB)
- Visual coding capabilities (HTML/CSS/JS from images)
- 32-language OCR
- 256K native context
- Same vLLM architecture class

### OCR Specialist: DeepSeek-OCR or GOT-OCR-2.0

For heavy document processing pipelines, a dedicated OCR model alongside the general VLM:
- **DeepSeek-OCR**: MIT license, vLLM native, document-to-Markdown, multi-size variants
- **GOT-OCR-2.0**: 0.6B params (trivial VRAM), Apache 2.0, LaTeX/Markdown output, region-based OCR

### Video Understanding: MiniCPM-V-4_5

If video understanding becomes a priority:
- 8B params, 73.5 Video-MME, 96x compression, 10 FPS / 180+ frames
- Apache 2.0, vLLM native
- Image-only mode fits 16 GB, video mode needs ~28 GB (5090)

### Omni-Modal: Phi-4-Multimodal or MiniCPM-o-2_6

If vision + audio in a single model is desired:
- **Phi-4-multimodal**: 5.6B, MIT, vision + speech + text, 12 GB
- **MiniCPM-o-2_6**: 8B, Apache 2.0, real-time streaming, OCRBench 897

### Future Watch

Models to track for next evaluation:
- **InternVL3.5** series (Cascade RL, 4x faster inference)
- **Qwen3.5** multimodal variants
- **MiniCPM-V-4_5** (if benchmarks hold, could be the new king)
- **Llama 4 Scout** (if VRAM requirements become manageable with better quantization)
- **GLM-4.1V-Thinking** (reasoning-focused VLM)

---

## Sources

All information sourced from:
- HuggingFace model cards (fetched 2026-02-25)
- vLLM official supported models documentation: https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md
- Individual model papers cited in each entry (arXiv links in model cards)

**Models verified against vLLM main branch as of 2026-02-25.**

**Note on dates:** Some models listed as "released" in Dec 2025 - Feb 2026 per the mission scope were actually released earlier but had significant updates in this window. Models like MiniCPM-V-4_5 (Sep 2025) and InternVL3.5 (Aug 2025) are included because they represent the current state-of-the-art even if slightly outside the 90-day window. The vLLM compatibility data is current as of today.
