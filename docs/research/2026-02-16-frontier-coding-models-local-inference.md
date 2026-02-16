# Frontier Coding Models: Local Inference Requirements

**Date**: 2026-02-16
**Status**: Research complete
**Purpose**: Evaluate VRAM and deployment requirements for frontier open-weight coding models on Athanor hardware

---

## Hardware Context (Athanor)

| Node | GPUs | Total VRAM |
|------|------|-----------|
| Node 1 | 4x RTX 5070 Ti (16 GB each) | 64 GB |
| Node 2 | RTX 4090 (24 GB) + RTX 5090 (32 GB) | 56 GB |
| Combined | 6 GPUs | 120 GB |

---

## Model Summary Table

| Model | Total Params | Active Params | Architecture | Context | License | Release |
|-------|-------------|---------------|-------------|---------|---------|---------|
| **Kimi K2.5** | 1,040B | 32B | MoE (384 experts, 8 active) | 256K | Open weight | Jan 2026 |
| **GLM-5** | 744B | 40B | MoE | 200K | MIT | Feb 2026 |
| **DeepSeek V3.1** | 671B | 37B | MoE (256 experts) | 128K | MIT | 2025 |
| **Qwen3-Coder-480B** | 480B | 35B | MoE (160 experts, 8 active) | 256K | Apache 2.0 | Aug 2025 |
| **Mistral Large 3** | 675B | 41B | MoE | 128K | Apache 2.0 | Dec 2025 |
| **Qwen3-235B** | 235B | 22B | MoE | 32K (131K w/ YaRN) | Apache 2.0 | May 2025 |

All are open-weight and available on HuggingFace.

---

## VRAM Requirements by Quantization (Weights Only)

VRAM formula: `Total_Params * bytes_per_param`. Actual deployment needs +10-20% for KV cache, activations, and framework overhead.

### Kimi K2.5 (1,040B total / 32B active)

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16 | 1,040B x 2 bytes | ~2,080 GB | Not distributed — model released natively in INT4 |
| FP8 | 1,040B x 1 byte | ~1,040 GB | Official HF weights are block-FP8 format |
| FP4 / INT4 (native) | 1,040B x 0.5 bytes | ~595 GB | **Native release format** — QAT during training |
| Q4_K_M (GGUF) | ~4.83 bpw | ~628 GB | Unsloth UD-Q4_K_XL: 588 GB |
| Q2_K (GGUF) | ~2 bpw | ~381 GB | Unsloth UD-Q2_K_XL recommended |
| IQ1_M (GGUF) | ~1.8 bpw | ~240 GB | Single 24 GB GPU + 256 GB RAM (offload), ~5-6 tok/s |

Sources:
- [Unsloth Kimi K2.5 GGUF](https://huggingface.co/unsloth/Kimi-K2.5-GGUF)
- [Kimi K2.5 HuggingFace](https://huggingface.co/moonshotai/Kimi-K2.5)
- [NVIDIA Kimi K2.5 NVFP4](https://huggingface.co/nvidia/Kimi-K2.5-NVFP4)
- [Unsloth Run Locally Guide](https://unsloth.ai/docs/models/kimi-k2.5)

### GLM-5 (744B total / 40B active)

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16/BF16 | 744B x 2 bytes | ~1,490 GB | Official BF16 release: ~1.51 TB |
| FP8 | 744B x 1 byte | ~744 GB | Official FP8 on HF; deployment needs ~860 GB+ |
| FP4 | 744B x 0.5 bytes | ~372 GB | — |
| Q4_K_M (GGUF) | ~4.83 bpw | ~473 GB | Confirmed by Unsloth GGUF |
| Q2_K (GGUF) | ~2 bpw | ~241 GB | Fits on 256 GB unified memory Mac |
| IQ1_M (GGUF) | ~1.8 bpw | ~176 GB | Minimum viable for consumer hardware |

Sources:
- [Unsloth GLM-5 GGUF](https://huggingface.co/unsloth/GLM-5-GGUF)
- [zai-org/GLM-5 HuggingFace](https://huggingface.co/zai-org/GLM-5)
- [zai-org/GLM-5-FP8](https://huggingface.co/zai-org/GLM-5-FP8)
- [GLM-5 Everything You Need to Know](https://artificialanalysis.ai/articles/glm-5-everything-you-need-to-know)

### DeepSeek V3.1 (671B total / 37B active)

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16/BF16 | 671B x 2 bytes | ~1,342 GB | Confirmed ~1.34 TB |
| FP8 | 671B x 1 byte | ~671 GB | On-disk: ~715 GB |
| FP4 | 671B x 0.5 bytes | ~336 GB | — |
| Q4_K_M (GGUF) | ~4.83 bpw | ~404 GB | Confirmed by Unsloth GGUF |
| Q2_K (GGUF) | ~2 bpw | ~245 GB | Unsloth UD-Q2_K_XL |
| IQ1_M (GGUF) | ~1.8 bpw | ~170 GB | 80% size reduction |

Sources:
- [Unsloth DeepSeek V3.1 GGUF](https://huggingface.co/unsloth/DeepSeek-V3.1-GGUF)
- [DeepSeek V3.1 Run Locally](https://unsloth.ai/blog/deepseek-v3.1)
- [DeepSeek V3.1 VRAM Requirements](https://apxml.com/models/deepseek-v3-1)

### Qwen3-Coder-480B (480B total / 35B active)

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16/BF16 | 480B x 2 bytes | ~960 GB | Confirmed |
| FP8 | 480B x 1 byte | ~480 GB | Official FP8 on HF |
| FP4 | 480B x 0.5 bytes | ~240 GB | — |
| Q4_K_M (GGUF) | ~4.83 bpw | ~290 GB | Unsloth UD-Q4_K_XL: 276 GB |
| Q2_K (GGUF) | ~2 bpw | ~150 GB | — |
| IQ1_M (GGUF) | ~1.8 bpw | ~120 GB | Smallest practical quant |

Sources:
- [Unsloth Qwen3-Coder GGUF](https://huggingface.co/unsloth/Qwen3-Coder-480B-A35B-Instruct-GGUF)
- [Qwen3-Coder HuggingFace](https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct)
- [Qwen3-Coder FP8](https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8)
- [KodekX Local Inference Guide](https://www.kodekx.com/blog/local-qwen3-coder-480b-setup-guide-hardware-quant-2025)

### Qwen3-235B-A22B (235B total / 22B active) — Smallest Frontier MoE

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16/BF16 | 235B x 2 bytes | ~470 GB | — |
| FP8 | 235B x 1 byte | ~235 GB | — |
| FP4 | 235B x 0.5 bytes | ~118 GB | Fits in 120 GB (6-GPU Athanor) — barely |
| Q4_K_M (GGUF) | ~4.83 bpw | ~143 GB | Confirmed |
| Q2_K (GGUF) | ~2 bpw | ~75 GB | Could fit in Node 1 (64 GB) + some RAM |

Sources:
- [Qwen3-235B HuggingFace](https://huggingface.co/Qwen/Qwen3-235B-A22B)
- [Qwen3 Hardware Requirements](https://www.hardware-corner.net/guides/qwen3-hardware-requirements/)

### Mistral Large 3 (675B total / 41B active)

| Format | Calculation | Weight Size | Notes |
|--------|------------|-------------|-------|
| FP16/BF16 | 675B x 2 bytes | ~1,350 GB | — |
| FP8 | 675B x 1 byte | ~675 GB | Deployable on single node with B200/H200 |
| FP4 / NVFP4 | 675B x 0.5 bytes | ~338 GB | Official NVFP4 on HF |
| Q4_K_M (GGUF) | ~4.83 bpw | ~407 GB | — |

Sources:
- [Mistral Large 3 HuggingFace](https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512)
- [Mistral Large 3 NVFP4](https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512-NVFP4)
- [Unsloth Mistral Large 3 GGUF](https://huggingface.co/unsloth/Mistral-Large-3-675B-Instruct-2512-GGUF)

---

## GLM Model Family (Smaller Sizes)

| Model | Total Params | Active Params | Architecture | Context |
|-------|-------------|---------------|-------------|---------|
| GLM-5 | 744B | 40B | MoE | 200K |
| GLM-4.7 | 355B | 32B | MoE | 128K |
| GLM-4.7-Flash | 30B | 3B | MoE | 128K |
| GLM-4-9B | 9B | 9B (dense) | Dense | 128K (1M variant exists) |

GLM-4.7 is the interesting midpoint: 355B total / 32B active. In Q4_K_M that would be ~214 GB. In Q2_K, ~89 GB. In IQ1_M, ~80 GB.

Sources:
- [GLM-4.7 HuggingFace](https://huggingface.co/zai-org/GLM-4.7)
- [GLM-4.7-Flash GGUF](https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF)

---

## Inference Framework Support

| Model | vLLM | SGLang | llama.cpp | Ollama | KTransformers |
|-------|------|--------|-----------|--------|---------------|
| Kimi K2.5 | Yes (nightly+, NVFP4) | Yes | Yes (GGUF) | Yes | Yes |
| GLM-5 | Yes | Yes | Yes (GGUF) | Yes | — |
| DeepSeek V3.1 | Yes | Yes | Yes (GGUF) | Yes | Yes |
| Qwen3-Coder-480B | Yes | Yes | Yes (GGUF) | Yes | — |
| Mistral Large 3 | Yes | Yes | Yes (GGUF) | Yes | — |
| Qwen3-235B | Yes | Yes | Yes (GGUF) | Yes | — |

---

## Consumer GPU Performance (MoE Offloading)

For these massive MoE models on consumer hardware, the only viable approach is **MoE expert offloading** — keeping active experts in VRAM and parking inactive ones in system RAM (or NVMe).

| Setup | Expected Speed | Notes |
|-------|---------------|-------|
| 1x 24 GB GPU + 256 GB RAM | ~5-6 tok/s | Kimi K2 at IQ2 quant, 16K context |
| 1x 32 GB GPU + 256 GB RAM | ~7-8 tok/s | Estimated for RTX 5090 (77% more bandwidth) |
| 4x 16 GB GPU (64 GB) + 256 GB RAM | ~8-12 tok/s | Node 1: depends on NVLink/PCIe bandwidth |
| Mac M3 Ultra 192 GB unified | ~10-15 tok/s | Best consumer unified memory option |

These are rough estimates from community benchmarks. MoE offloading performance is dominated by **system RAM bandwidth** (DDR5 ~77 GB/s) and **PCIe bandwidth** (~32 GB/s per x16 slot), not GPU compute.

Sources:
- [KTransformers Kimi K2.5 RTX 4090](https://github.com/kvcache-ai/ktransformers/issues/1817)
- [RTX 5090 LLM Memory Bandwidth Impact](https://blog.neevcloud.com/the-impact-of-rtx-5090s-memory-bandwidth-on-llms)

---

## Feasibility for Athanor

### What fits in pure VRAM (120 GB combined, no offloading)?

| Model | Q4_K_M | FP4 | Fits? |
|-------|--------|-----|-------|
| Kimi K2.5 | 628 GB | 520 GB | **No** |
| GLM-5 | 473 GB | 372 GB | **No** |
| DeepSeek V3.1 | 404 GB | 336 GB | **No** |
| Qwen3-Coder-480B | 290 GB | 240 GB | **No** |
| Qwen3-235B | 143 GB | 118 GB | **Barely** (FP4 only, 2 GB headroom) |
| Mistral Large 3 | 407 GB | 338 GB | **No** |
| GLM-4.7 | 214 GB | 178 GB | **No** |
| GLM-4.7-Flash (30B) | ~18 GB | ~15 GB | **Yes** — trivially |

**Bottom line**: None of the frontier 100B+ coding models fit in Athanor's 120 GB VRAM at any reasonable quantization. The only exception is Qwen3-235B at FP4, which would leave essentially zero headroom for KV cache.

### What works with offloading?

With Node 1's 256 GB DDR5 ECC RAM + 64 GB VRAM, or Node 2's RAM + 56 GB VRAM, MoE offloading becomes viable:

- **Qwen3-235B at Q4_K_M** (143 GB): Fits in Node 1 RAM + VRAM. Active 22B params in VRAM, rest in RAM. Usable speed.
- **GLM-4.7 at Q2_K** (~89 GB): Fits in VRAM + RAM easily. 32B active params.
- **DeepSeek V3.1 at IQ2** (245 GB): Fits in 256 GB RAM + VRAM. Slow but functional.
- **Qwen3-Coder-480B at IQ1_M** (120 GB): Fits, but 1-bit quality is questionable.

### Realistic recommendation

For **local coding model inference** on Athanor:

1. **Best quality that fits**: Qwen3-235B-A22B at Q4_K_M (143 GB) with MoE offloading on Node 1
2. **Best speed/quality tradeoff**: GLM-4.7 at Q4_K_M (~214 GB) or Q3 (~160 GB) with offloading
3. **Maximum model size**: DeepSeek V3.1 at Q2_K (245 GB) with full offloading — slow but works
4. **Fast and practical**: GLM-4.7-Flash (30B, 3B active) — fits entirely in a single GPU, dense-like speed

For frontier-class coding, **API access** to Kimi K2.5, GLM-5, or Qwen3-Coder-480B will outperform any local setup on this hardware. The VRAM gap is 3-5x what Athanor has.

---

## Key Takeaways

1. **All frontier coding models are MoE with 400B-1T+ total params.** They need hundreds of GB even at INT4.
2. **Active parameters are small (22-41B)** — the compute is manageable, but you still need to store all expert weights.
3. **Native INT4/FP4 is becoming standard** — Kimi K2.5 ships in INT4, Blackwell GPUs support FP4 natively.
4. **MoE offloading is the consumer path** — tools like KTransformers, llama.cpp MoE offload, and vLLM with CPU offload make it work, but at 5-15 tok/s.
5. **120 GB VRAM is not enough** for any 400B+ model without offloading. It barely fits Qwen3-235B at FP4.
6. **256 GB system RAM** is the real enabler for local MoE inference on consumer hardware.
