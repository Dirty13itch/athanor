# Coding Models for Local Inference: March 2026 Update

**Date**: 2026-03-13
**Status**: Research complete
**Purpose**: Update coding model landscape for Athanor's GPU fleet. Identify best-in-class models that fit 3 hardware slots: 4090 (24GB), 5090 (32GB), TP=4 5070Ti (64GB).
**Supersedes**: None (supplements `2026-02-25-coding-models-exhaustive.md`)
**Related**: `ADR-005-inference-engine.md`, `docs/archive/hardware/hardware-inventory.md`, `docs/operations/HARDWARE-REPORT.md`, `.claude/rules/vllm.md`

---

## Context

The previous exhaustive survey (Feb 25) cataloged 40 models. This update focuses on:
1. What changed in the 16 days since (new releases, new quants, corrected data)
2. Specific fit analysis for the 3 hardware slots requested
3. Actionable recommendation for replacing the current Qwen3-Coder-30B-A3B-AWQ on FOUNDRY's 4090

### Hardware Slots

| Slot | GPU | VRAM | Current Model | Node | Constraints |
|------|-----|------|---------------|------|-------------|
| **A** | RTX 4090 (Ada sm_89) | 24 GB | Qwen3-Coder-30B-A3B-AWQ | FOUNDRY | No NVFP4, AWQ/FP8 only. `--quantization awq` explicit. |
| **B** | RTX 5090 (Blackwell sm_120) | 32 GB | Qwen3.5-35B-A3B-AWQ | WORKSHOP | AWQ/NVFP4/FP8. Highest bandwidth (1792 GB/s). |
| **C** | 4x RTX 5070 Ti TP=4 (Blackwell sm_120) | 64 GB | Qwen3.5-27B-FP8 | FOUNDRY | AWQ/NVFP4/FP8. `--enforce-eager` required for DeltaNet. Mixed arch TP with 4090 NOT recommended (sm_89/sm_120 mismatch). |

### Key Constraints (from `.claude/rules/vllm.md`)
- vLLM nightly 0.16.1rc1.dev32 on FOUNDRY/WORKSHOP (custom `athanor/vllm:qwen35` image)
- vLLM v0.17.1 is latest stable (March 11, 2026) -- upgrade path available
- Qwen3.5 requires `--tool-call-parser qwen3_xml`, `--enforce-eager`, `--language-model-only`, `--kv-cache-dtype auto`
- AWQ required on Blackwell (`--quantization awq`; Marlin kernel crashes)
- FP8 works on TP=4 (5070 Ti) but NOT single-GPU 5090 for large models (insufficient KV headroom)

---

## 1. What Changed Since Feb 25

### New Releases (Feb 25 - Mar 13)

| Model | Released | Key Change |
|-------|----------|------------|
| **Qwen3.5-9B/4B/2B/0.8B** | Mar 2, 2026 | Small dense models. 9B has LiveCodeBench 65.6 -- good but not competitive for coding slot. |
| **Codestral 25.08** | Aug 2025 (API); no new open-weight | API-only. No open weights. Not deployable locally. Irrelevant. |
| **Claude Opus 4.6** | Mar 2026 | SWE-bench 80.8%. Closed-source. Sets the cloud ceiling. |
| **DeepSeek V4** | NOT released | Rumored since Feb. Still no public weights as of Mar 13. Do not plan around it. |

### Updated Data Points

| Item | Previous | Updated | Source |
|------|----------|---------|--------|
| Qwen3-Coder-Next AWQ size | ~46 GB (estimated) | **45.9 GB** (confirmed) | [cyankiwi HF model card](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit) |
| Qwen3-Coder-Next AWQ min VRAM | "fits TP=4" | **33 GB minimum** single GPU; TP=2 or TP=4 recommended | HF discussion, community reports |
| Step-3.5-Flash vLLM tool parser | "needs testing" | **`step3p5` parser confirmed**, `--tool-call-parser step3p5 --reasoning-parser step3p5` | [vLLM Recipes](https://docs.vllm.ai/projects/recipes/en/latest/StepFun/Step-3.5-Flash.html) |
| Step-3.5-Flash MTP3 in vLLM | Unknown | **Not yet merged**. PR in progress. Use v0.15.1 + patch. | [Step-3.5-Flash GitHub](https://github.com/stepfun-ai/Step-3.5-Flash) |
| Devstral Small 2 NVFP4 | Available | **Does not load in vLLM** currently (compatibility issue) | [HF discussion](https://huggingface.co/Firworks/Devstral-Small-2-24B-Instruct-2512-nvfp4) |
| IQuest-Coder AWQ | Unknown | **Community AWQ exists** (`cyankiwi/IQuest-Coder-V1-40B-Loop-Instruct-AWQ-4bit`). Loop architecture has known AWQ/GPTQ compatibility issues. | [HF model](https://huggingface.co/cyankiwi/IQuest-Coder-V1-40B-Loop-Instruct-AWQ-4bit) |
| vLLM stable version | v0.16.0 | **v0.17.1** (Mar 11, 2026). Full Qwen3.5 GDN support. | [vLLM releases](https://github.com/vllm-project/vllm/releases) |
| Qwen3.5 tool parser | `hermes` (Feb doc) | **`qwen3_xml` preferred** over `qwen3_coder`. Fixes infinite-token bug on long inputs with tool calls. | [vLLM tool calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/) |
| SWE-bench contamination | Not flagged | **OpenAI has stopped reporting Verified scores** due to contamination. SWE-bench Pro (1865 tasks, multi-lang) is the emerging replacement. | [SWE-bench Pro](https://labs.scale.com/leaderboard/swe_bench_pro_public) |

### Corrections to Previous Research

1. **Tool parser for Qwen3.5**: Previous doc listed `hermes`. Correct parser is `qwen3_xml` (which Athanor already uses per `.claude/rules/vllm.md`). The `qwen3_coder` parser has a known bug causing infinite `!!!!!` generation on long tool-call inputs; `qwen3_xml` resolves this.

2. **Qwen3-Coder-Next AWQ does NOT fit on 5090**: Previous doc suggested "tight but workable" on 32 GB. Confirmed: minimum 33 GB VRAM. Single 5090 (32 GB) cannot run it. Requires TP=2 or TP=4.

3. **IQuest-Coder-V1-40B SWE-bench**: Some sources now report 81% (with Loop architecture + optimized scaffold). The base Instruct model is 76.2%. The Loop variant's AWQ compatibility is problematic. Treat with caution.

---

## 2. Model Candidates by Hardware Slot

### Slot A: RTX 4090 (24 GB, Ada sm_89)

Only AWQ or FP8 quantization. No NVFP4 (requires Blackwell sm_120).

| Model | Format | Weight Size | KV Headroom | SWE-bench V | Tool Parser | Speed Est. | Verdict |
|-------|--------|-------------|-------------|-------------|-------------|------------|---------|
| **Qwen3.5-35B-A3B** | AWQ | ~21 GB | ~3 GB | 69.2% | `qwen3_xml` | 70-100 t/s | Fits, but KV tight |
| **Qwen3-Coder-30B-A3B** | AWQ | ~18.6 GB | ~5.4 GB | 50.3% | `qwen3_xml` | ~73 t/s | Current model. Works. |
| **Devstral Small 2 24B** | FP8 | ~24 GB | ~0 GB | 68.0% | `mistral` | ~40-60 t/s | Model fills VRAM. No KV room at FP8. |
| **Devstral Small 2 24B** | AWQ | ~12 GB | ~12 GB | 65-68% | `mistral` | ~50-70 t/s | Good fit if AWQ quant available |
| **GLM-4.7-Flash 30B** | AWQ | ~18 GB | ~6 GB | 59.2% | `glm47` | ~70 t/s | Lower SWE-bench than Qwen3.5-35B |
| **Qwen3.5-27B** | AWQ | ~17 GB | ~7 GB | 72.4% | `qwen3_xml` | ~50-60 t/s | Strong. Dense. Good KV room. |
| **IQuest-Coder-V1-40B** | AWQ | ~24 GB | ~0 GB | 76.2% | `qwen3` | ~30-40 t/s | Fills VRAM. AWQ compat uncertain. Custom license. |
| **Qwen3.5-9B** | BF16 | ~18 GB | ~6 GB | N/A (est. 40-50%) | `qwen3_xml` | ~80-100 t/s | Fast but coding perf not competitive |

**Best candidates for Slot A:**
1. **Qwen3.5-35B-A3B AWQ** -- 69.2% SWE-bench, 3B active (fast MoE), fits with 3 GB KV. The +19 percentage point upgrade over current Qwen3-Coder-30B-A3B (50.3%).
2. **Qwen3.5-27B AWQ** -- 72.4% SWE-bench, but dense 27B = slower than 3B-active MoE on 4090. Better quality, worse throughput.
3. **Devstral Small 2 AWQ** -- 68.0% SWE-bench, 24B dense with Mistral tool parser. Needs community AWQ quant.

### Slot B: RTX 5090 (32 GB, Blackwell sm_120)

AWQ, NVFP4, and FP8 available. Highest memory bandwidth (1792 GB/s).

| Model | Format | Weight Size | KV Headroom | SWE-bench V | Tool Parser | Speed Est. | Verdict |
|-------|--------|-------------|-------------|-------------|-------------|------------|---------|
| **Qwen3.5-35B-A3B** | AWQ | ~21 GB | ~11 GB | 69.2% | `qwen3_xml` | 100-130 t/s | Excellent fit. Current model. |
| **Qwen3.5-35B-A3B** | NVFP4 | ~9 GB | ~23 GB | ~66-68% (est.) | `qwen3_xml` | 130-170 t/s | Massive KV room. Quality loss ~3-5%. |
| **Qwen3.5-27B** | FP8 | ~27 GB | ~5 GB | 72.4% | `qwen3_xml` | 60-80 t/s | Good fit. Higher quality. |
| **Qwen3.5-27B** | AWQ | ~17 GB | ~15 GB | ~70-71% (est.) | `qwen3_xml` | 70-90 t/s | More KV room, slight quality loss. |
| **Qwen3-Coder-Next** | AWQ | ~46 GB | -14 GB | 70.6% | `qwen3_coder` | N/A | **DOES NOT FIT.** Min 33 GB, model is 46 GB. |
| **IQuest-Coder-V1-40B** | FP8 | ~40 GB | -8 GB | 76.2% | `qwen3` | N/A | **DOES NOT FIT.** |
| **Devstral 2 123B** | NVFP4 | ~31 GB | ~1 GB | 72.2% | `mistral` | ~20-30 t/s | Theoretically fits. Untested. No KV room. |
| **Devstral Small 2 24B** | FP8 | ~24 GB | ~8 GB | 68.0% | `mistral` | 60-80 t/s | Good alternative fit. |
| **Qwen3.5-122B-A10B** | AWQ | ~37 GB | -5 GB | 72.0% | `qwen3_xml` | N/A | **DOES NOT FIT.** |

**Best candidates for Slot B:**
1. **Qwen3.5-27B FP8** -- 72.4% SWE-bench at near-lossless quality. Dense model on highest-bandwidth GPU. Current recommendation (already in Feb doc).
2. **Qwen3.5-35B-A3B AWQ** -- Current deployment. 69.2% SWE-bench. Fast MoE. More KV room than the 27B FP8.
3. **Devstral Small 2 24B FP8** -- 68.0% SWE-bench. Different architecture (Mistral). Tool calling via `mistral` parser. Apache 2.0.

### Slot C: 4x RTX 5070 Ti TP=4 (64 GB, Blackwell sm_120)

AWQ, NVFP4, FP8 available. Currently runs Qwen3.5-27B-FP8 (coordinator).

| Model | Format | Weight Size | KV Headroom | SWE-bench V | Tool Parser | Speed Est. | Verdict |
|-------|--------|-------------|-------------|-------------|-------------|------------|---------|
| **Qwen3.5-27B** | FP8 | ~27 GB | ~37 GB | 72.4% | `qwen3_xml` | 40-60 t/s | Current model. Excellent fit. Massive KV headroom. |
| **Qwen3-Coder-Next** | AWQ | ~46 GB | ~18 GB | 70.6% | `qwen3_coder` | 40-60 t/s | Fits. SWE-bench LOWER than 27B. |
| **IQuest-Coder-V1-40B** | FP8 | ~40 GB | ~24 GB | 76.2% | `qwen3` | 30-50 t/s | Good fit if scores verified. Custom license. |
| **Qwen3.5-122B-A10B** | AWQ | ~37 GB | ~27 GB | 72.0% | `qwen3_xml` | 40-60 t/s | Same SWE-bench as 27B. Higher BFCL (72.2 vs N/A). |
| **Devstral 2 123B** | AWQ | ~62 GB | ~2 GB | 72.2% | `mistral` | 20-30 t/s | Fits but no KV room. Impractical. |
| **Step-3.5-Flash** | FP8 | ~98 GB | -34 GB | 74.4% | `step3p5` | N/A | **DOES NOT FIT in VRAM.** Offload only. |
| **Qwen3.5-35B-A3B** | AWQ | ~21 GB | ~43 GB | 69.2% | `qwen3_xml` | 60-80 t/s | Fits easily but wastes TP=4. |
| **Nemotron 3 Nano 30B** | BF16 | ~60 GB | ~4 GB | 38.8% | Custom | 30-40 t/s | Coding too weak (38.8% SWE-bench). |

**Best candidates for Slot C:**
1. **Qwen3.5-27B FP8** -- Current deployment. 72.4% SWE-bench. 37 GB KV headroom. Proven stable.
2. **IQuest-Coder-V1-40B FP8** -- 76.2% SWE-bench (+3.8 over current). Fits with 24 GB headroom. BUT: custom license, unknown lab, AWQ issues on Loop variant. FP8 on base Instruct model should work.
3. **Qwen3.5-122B-A10B AWQ** -- 72.0% SWE-bench, 72.2% BFCL-V4. Trades throughput for better tool calling. 10B active params, MoE.

---

## 3. Comprehensive Model Profiles

### Qwen3-Coder-Next (80B/3B MoE) -- Clarified

Previous research left ambiguity about fit. Now confirmed:

- **Architecture**: 80B total, 3B active. 512 experts, 10 active/token. Gated DeltaNet + MoE hybrid.
- **AWQ 4-bit size**: 45.9 GB (confirmed via [cyankiwi/Qwen3-Coder-Next-AWQ-4bit](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit))
- **Minimum single-GPU VRAM**: 33 GB (community confirmed). Does NOT fit 4090 (24GB) or 5090 (32GB) alone.
- **Fits on**: TP=4 on FOUNDRY (45.9 in 64 GB = 18 GB KV headroom). TP=2 on 2x 5090 or 5090+5060Ti.
- **SWE-bench Verified**: 70.6%
- **Tool parser**: `qwen3_coder` (but `qwen3_xml` reported to fix infinite-token bug)
- **MTP support in vLLM**: Method `qwen3_next_mtp`, speculate 2 tokens. Supported in v0.15.0+.
- **Quantization**: AWQ via llm-compressor (cyankiwi). FP8 via Unsloth. GGUF via Unsloth (Q4_K_M = 48.4 GB).
- **License**: Apache 2.0

**Verdict for Athanor**: Qwen3-Coder-Next on TP=4 scores LOWER than Qwen3.5-27B FP8 on SWE-bench (70.6% vs 72.4%) while using 3x more VRAM. Its advantage is only in ultra-long context scenarios where DeltaNet's O(1) KV cache matters. Not recommended as primary.

Source: [HF model card](https://huggingface.co/Qwen/Qwen3-Coder-Next), [cyankiwi AWQ](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit), [Unsloth guide](https://unsloth.ai/docs/models/qwen3-coder-next)

### Devstral Small 2 24B -- Viable Alternative

- **Architecture**: 24B dense transformer. Based on Mistral Small 3.1.
- **SWE-bench Verified**: 68.0%
- **SWE-bench Multilingual**: 55.7%
- **Terminal-Bench 2**: 22.5%
- **Context**: 256K tokens
- **License**: Apache 2.0
- **Vision**: Yes (new in Small 2)
- **Tool calling**: Mistral format, `--tool-call-parser mistral`
- **VRAM**: FP8 native (~24 GB), fits 4090. AWQ quants exist but no official one. NVFP4 exists but **does not load in vLLM** currently.
- **vLLM**: `vllm serve mistralai/Devstral-Small-2-24B-Instruct-2512 --tool-call-parser mistral --enable-auto-tool-choice`

**Verdict for Athanor**: Competitive on Slot A (4090 FP8) or Slot B (5090 FP8 with 8 GB headroom). Lower SWE-bench than Qwen3.5-35B-A3B (68.0% vs 69.2%) but brings Mistral ecosystem diversity. Vision capability is a plus. NVFP4 broken in vLLM is a negative.

Source: [HF model card](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512), [VentureBeat](https://venturebeat.com/ai/mistral-launches-powerful-devstral-2-coding-model-including-open-source)

### Codestral 25.08 -- Not Deployable Locally

- **Status**: API-only. No open weights released.
- **License**: Enterprise/API only
- **HumanEval**: 81.1%
- **Size**: Undisclosed (less than 100B). 256K context.
- **Pricing**: $0.30/$0.90 per M tokens

**Verdict**: Not deployable on Athanor. The open-weight Codestral 22B (v0.1) has MNPL non-production license. Skip entirely for local inference.

Source: [Mistral announcement](https://mistral.ai/news/codestral-25-08)

### DeepSeek V4 -- Vaporware (as of Mar 13)

- **Status**: Not released. Multiple leaked dates have passed (mid-Feb, late-Feb, early-Mar).
- **Rumored specs**: ~1T MoE, ~37B active, 1M context, multimodal
- **Rumored SWE-bench**: 80%+ (unverified)
- **Rumored VRAM**: Dual 4090 or single 5090 (if true, would be remarkable)

**Verdict**: Do not plan around this. No weights exist. May release this month or may not. When/if it drops, it deserves immediate evaluation, but it would likely be too large for single-GPU Athanor slots (1T params even at Q4 = ~600 GB).

Source: [evolink.ai summary](https://evolink.ai/blog/deepseek-v4-release-window-prep), [nxcode.io](https://www.nxcode.io/resources/news/deepseek-v4-release-specs-benchmarks-2026)

### IQuest-Coder-V1-40B -- High Potential, High Risk

- **Architecture**: 40B dense. 80 layers, GQA. Code-Flow training (learns from repo evolution).
- **SWE-bench Verified**: 76.2% (Instruct), up to 81% claimed (Loop variant + optimized scaffold)
- **LiveCodeBench v6**: 81.1
- **Context**: 128K
- **License**: Custom "iquestcoder" (NOT Apache/MIT)
- **VRAM**: FP8 ~40 GB (fits TP=4). AWQ ~24 GB (fits 4090, barely).
- **AWQ compatibility**: Known issues with Loop architecture. Base Instruct AWQ untested.
- **Tool parser**: `qwen3` (Instruct), `qwen3_coder` (Thinking)
- **Org**: IQuestLab (AI division of Ubiquant, a Chinese quant trading firm)

**Verdict**: The SWE-bench score is exceptional for 40B dense. FP8 on TP=4 (40/64 GB) would leave 24 GB for KV -- practical. BUT: custom license needs legal review, unknown long-term support, SWE-bench scores are scaffold-dependent and should be independently verified. Consider as a high-risk/high-reward option for Slot C.

Source: [HF model card](https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Instruct), [aicybr review](https://aicybr.com/blog/iquest-coder-v1)

### Step-3.5-Flash (196B/11B MoE) -- Offload Only

- **Architecture**: 196B total, 11B active. 288 routed experts + 1 shared, top-8. MTP-3 (4 tokens/pass).
- **SWE-bench Verified**: 74.4%
- **LiveCodeBench v6**: 86.4% (highest open-weight)
- **tau2-Bench**: 88.2% (highest agentic score)
- **Context**: 256K
- **License**: Apache 2.0
- **Tool parser**: `step3p5` (confirmed working in vLLM)
- **Reasoning parser**: `step3p5`
- **VRAM**: FP8 ~98 GB (does NOT fit TP=4 64 GB). Q4 ~120 GB (offload only).
- **MTP3 in vLLM**: PR in progress, not yet merged. Use v0.15.1 + patch.

**Verdict**: Cannot fit any hardware slot in VRAM. Outstanding for offloading on FOUNDRY (120 GB Q4 in 312 GB capacity). Best offloading candidate due to 11B active params + MTP-3 = fastest offloading speed. Tool calling confirmed working. Best overnight/batch coding model.

Source: [HF model card](https://huggingface.co/stepfun-ai/Step-3.5-Flash), [vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/StepFun/Step-3.5-Flash.html), [GitHub](https://github.com/stepfun-ai/Step-3.5-Flash)

### Qwen3.5-9B -- Too Weak for Coding Slot

- **Architecture**: 9B dense. Gated DeltaNet hybrid. 262K context.
- **LiveCodeBench**: 65.6 (vs gpt-oss-120b's 82.7)
- **SWE-bench**: No reported score. Estimated 40-50% based on size class.
- **VRAM**: BF16 ~18 GB. AWQ ~5 GB. Fits anywhere.
- **License**: Apache 2.0

**Verdict**: Strong generalist for its size but not competitive for a dedicated coding slot. LiveCodeBench 65.6 is 15 points below Qwen3.5-27B (80.7). Use for utility tasks, not coding.

Source: [HF model card](https://huggingface.co/Qwen/Qwen3.5-9B), [XDA Developers](https://www.xda-developers.com/qwen-3-5-9b-tops-ai-benchmarks-not-how-pick-model/)

---

## 4. vLLM Compatibility Matrix (Updated March 2026)

| Model | vLLM Version | Tool Parser | Reasoning Parser | AWQ | FP8 | NVFP4 | Notes |
|-------|-------------|-------------|-----------------|-----|-----|-------|-------|
| **Qwen3.5-27B** | v0.17.0+ (full GDN support) | `qwen3_xml` | `qwen3` | Yes | Yes | Yes (Blackwell) | `--enforce-eager --language-model-only` required |
| **Qwen3.5-35B-A3B** | v0.17.0+ | `qwen3_xml` | `qwen3` | Yes | Yes | Yes (Blackwell) | `--kv-cache-dtype auto` required |
| **Qwen3.5-122B-A10B** | v0.17.0+ | `qwen3_xml` | `qwen3` | Yes | Yes | Yes (Blackwell) | Same constraints as 35B |
| **Qwen3-Coder-Next** | v0.15.0+ | `qwen3_coder` or `qwen3_xml` | N/A (no thinking) | Yes (community) | Yes (Unsloth) | Planned | `qwen3_xml` recommended to avoid infinite-token bug |
| **Qwen3-Coder-30B-A3B** | v0.15.0+ | `qwen3_xml` or `hermes` | N/A | Yes (official) | Yes | Yes (Blackwell) | Current deployment on 4090 |
| **Devstral Small 2 24B** | v0.17.0+ | `mistral` | N/A | Community | Yes (official) | **Broken in vLLM** | NVFP4 loads fail |
| **IQuest-Coder-V1-40B** | v0.15.0+ | `qwen3` / `qwen3_coder` | `qwen3` (Thinking) | Community (Loop only) | Untested | Untested | AWQ compat issues on Loop arch |
| **Step-3.5-Flash** | v0.15.1+ patch | `step3p5` | `step3p5` | Untested | Yes (official) | Untested | MTP3 not yet in mainline vLLM |
| **GLM-4.7-Flash** | v0.17.0+ (main branch) | `glm47` | `glm45` | Yes | Yes | Untested | Needs latest vLLM |
| **Devstral 2 123B** | v0.17.0+ | `mistral` | N/A | Untested | Yes | Community | Fits 5090 at NVFP4 (~31 GB) -- untested |

---

## 5. SWE-bench Verification Status

**Important caveat**: OpenAI has stopped reporting SWE-bench Verified scores due to training data contamination across all frontier models. SWE-bench Pro (1,865 tasks across Python/Go/TypeScript/JavaScript) is the emerging replacement benchmark. However, most open-weight models have NOT been evaluated on SWE-bench Pro yet, so Verified remains the primary comparison metric.

SWE-bench scores are scaffold-dependent (10-20% variation). All scores are model-reported unless noted.

### SWE-bench Verified Rankings (Open-Weight, Fits Athanor)

| Rank | Model | SWE-bench V | Active Params | Best Fit Slot | Format |
|------|-------|-------------|---------------|---------------|--------|
| 1 | IQuest-Coder-V1-40B | 76.2% | 40B (dense) | C (TP=4 FP8) | FP8 |
| 2 | Qwen3.5-27B | 72.4% | 27B (dense) | B (5090 FP8) or C | FP8 |
| 3 | Qwen3.5-122B-A10B | 72.0% | 10B (MoE) | C (TP=4 AWQ) | AWQ |
| 4 | Qwen3-Coder-Next | 70.6% | 3B (MoE) | C (TP=4 AWQ) | AWQ |
| 5 | Qwen3.5-35B-A3B | 69.2% | 3B (MoE) | A (4090 AWQ), B | AWQ |
| 6 | Devstral Small 2 24B | 68.0% | 24B (dense) | A (4090 FP8), B | FP8 |
| 7 | GLM-4.7-Flash | 59.2% | 3B (MoE) | A (4090 AWQ) | AWQ |
| 8 | Qwen3-Coder-30B-A3B | 50.3% | 3.3B (MoE) | A (4090 AWQ) | AWQ |

### Offload-Only Models (Not in VRAM)

| Model | SWE-bench V | LiveCodeBench v6 | tau2-Bench | Q4 Size | Active Params |
|-------|-------------|------------------|------------|---------|---------------|
| Step-3.5-Flash | 74.4% | **86.4** | **88.2** | ~120 GB | 11B |
| Qwen3.5-397B-A17B | 76.4% | 83.6 | 86.7 | ~240 GB | 17B |
| MiMo-V2-Flash | 73.4% | 80.6 | -- | ~186 GB | 15B |
| GLM-4.7 | 73.8% | 84.9 | 87.4 | ~214 GB | 32B |

---

## 6. Recommendation

### What to Change (and What Not To)

**Slot C (TP=4, Coordinator) -- DO NOT CHANGE.**
Qwen3.5-27B-FP8 at 72.4% SWE-bench with 37 GB KV headroom is the optimal coordinator model. Nothing that fits this slot scores meaningfully higher. IQuest-Coder-V1-40B (76.2%) is the only candidate with better SWE-bench, but it has custom licensing and unverified reproducibility. The coordinator role requires reliability over raw coding score.

**Slot B (5090, Worker) -- DO NOT CHANGE.**
Qwen3.5-35B-A3B-AWQ at 69.2% SWE-bench is the right model for the worker/general role. It's the best all-around model for tool calling (tau2-Bench leader in its class) and fits with generous KV headroom. Swapping to Qwen3.5-27B FP8 would trade fast MoE inference for 3.2 more SWE-bench points -- not worth it for the worker role.

**Slot A (4090, Coder) -- UPGRADE.**
The current Qwen3-Coder-30B-A3B-AWQ at 50.3% SWE-bench is the weakest link. Two upgrade paths:

#### Option 1 (Recommended): Qwen3.5-35B-A3B AWQ on 4090

| Metric | Current (Qwen3-Coder-30B) | Proposed (Qwen3.5-35B-A3B) | Delta |
|--------|---------------------------|-----------------------------|-------|
| SWE-bench Verified | 50.3% | 69.2% | **+18.9 pp** |
| Architecture | MoE 30B/3.3B active | MoE 35B/3B active | Similar |
| AWQ size | ~18.6 GB | ~21 GB | +2.4 GB |
| KV headroom (24 GB) | ~5.4 GB | ~3 GB | -2.4 GB |
| Tool parser | `qwen3_xml` | `qwen3_xml` | Same |
| Speed | ~73 t/s | ~70-100 t/s | Similar |
| Context limit | 256K | 262K | Similar |
| License | Apache 2.0 | Apache 2.0 | Same |

**Why**: Near-20-point SWE-bench improvement with the same architecture class, same tool parser, same license. The 3 GB KV headroom is tight but workable with `--max-model-len 32768`. The model is already deployed on WORKSHOP's 5090, so it's proven to work with our vLLM image. Only change: download AWQ quant and update Ansible vars.

**Risk**: 3 GB KV headroom may limit practical context to ~16-32K tokens. For coding tasks this is usually sufficient (most code edits fit in 16K), but for large codebase exploration it's a constraint.

#### Option 2 (Alternative): Devstral Small 2 24B FP8 on 4090

| Metric | Current (Qwen3-Coder-30B) | Proposed (Devstral Small 2) | Delta |
|--------|---------------------------|-----------------------------|-------|
| SWE-bench Verified | 50.3% | 68.0% | **+17.7 pp** |
| Architecture | MoE 30B/3.3B active | Dense 24B | Different |
| FP8 size | ~30 GB (doesn't fit) | ~24 GB | Fits at FP8 |
| KV headroom (24 GB, FP8) | N/A | ~0 GB | Very tight |
| AWQ size | ~18.6 GB | ~12 GB | Smaller |
| KV headroom (24 GB, AWQ) | ~5.4 GB | ~12 GB | **+6.6 GB** |
| Tool parser | `qwen3_xml` | `mistral` | Different |
| Speed | ~73 t/s | ~50-70 t/s | Slower (dense) |
| Vision | No | Yes | Added capability |
| License | Apache 2.0 | Apache 2.0 | Same |

**Why**: Brings Mistral architecture diversity, vision capability, and slightly lower SWE-bench (68.0% vs 69.2%) compared to Qwen3.5-35B-A3B. At AWQ it has MORE KV headroom (12 GB vs 3 GB). The `mistral` tool parser is well-tested in vLLM.

**Risk**: Needs community AWQ quant (official FP8 only). NVFP4 broken in vLLM. Dense 24B is slower than 3B-active MoE. Different tool parser means LiteLLM routing config changes.

### Recommended Action

**Upgrade Slot A to Qwen3.5-35B-A3B AWQ.** This is the lowest-risk, highest-impact change:
- Same model family as coordinator and worker (Qwen3.5)
- Same tool parser (`qwen3_xml`)
- Same vLLM image (`athanor/vllm:qwen35`)
- Same quantization method (AWQ)
- +18.9 percentage points on SWE-bench
- No Ansible changes beyond model path and `--max-model-len`
- Can test on DEV first (5060 Ti 16 GB at NVFP4 ~9 GB)

### Future Considerations

1. **DeepSeek V4**: Monitor for release. If it ships as claimed (1T MoE, ~37B active, fits dual 4090), evaluate immediately. Likely too large for single-GPU Athanor slots but could replace TP=4 coordinator.

2. **Step-3.5-Flash offloading**: When MTP3 support lands in vLLM mainline, test offloading on FOUNDRY for overnight batch coding. 74.4% SWE-bench + 86.4% LiveCodeBench + tool calling confirmed.

3. **vLLM v0.17.1 upgrade**: The current nightly (0.16.1rc1.dev32) works but v0.17.1 has full Qwen3.5 GDN support, FP8 quantization, and MTP speculative decoding baked in. Upgrade path: rebuild `athanor/vllm:qwen35` from v0.17.1 base.

4. **SWE-bench Pro**: As Verified scores become unreliable due to contamination, track models on SWE-bench Pro. Currently only GPT/Claude models have scores. Open-weight evaluations expected Q2 2026.

5. **IQuest-Coder-V1-40B**: If independent SWE-bench reproduction confirms 76.2%, and license review is acceptable, this becomes the strongest TP=4 candidate. Monitor for community validation.

---

## 7. Sources

### Model Cards
- [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next)
- [cyankiwi/Qwen3-Coder-Next-AWQ-4bit](https://huggingface.co/cyankiwi/Qwen3-Coder-Next-AWQ-4bit)
- [Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B)
- [Qwen3.5-35B-A3B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)
- [Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B)
- [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
- [Devstral-Small-2-24B-Instruct-2512](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512)
- [Devstral-Small-2 NVFP4 (Firworks)](https://huggingface.co/Firworks/Devstral-Small-2-24B-Instruct-2512-nvfp4)
- [IQuest-Coder-V1-40B-Instruct](https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Instruct)
- [Step-3.5-Flash](https://huggingface.co/stepfun-ai/Step-3.5-Flash)
- [Step-3.5-Flash FP8](https://huggingface.co/stepfun-ai/Step-3.5-Flash-FP8)
- [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash)

### Leaderboards
- [SWE-bench Verified](https://www.swebench.com/)
- [SWE-bench Pro (Scale AI)](https://labs.scale.com/leaderboard/swe_bench_pro_public)
- [SWE-rebench (independent)](https://swe-rebench.com)
- [Vellum LLM Leaderboard](https://www.vellum.ai/best-llm-for-coding)
- [llm-stats SWE-bench](https://llm-stats.com/benchmarks/swe-bench-verified)
- [marc0.dev Leaderboard (March 2026)](https://www.marc0.dev/en/leaderboard)
- [Onyx Coding LLM Rankings](https://onyx.app/best-llm-for-coding)

### vLLM Documentation
- [vLLM v0.17.1 Release](https://github.com/vllm-project/vllm/releases)
- [vLLM Tool Calling](https://docs.vllm.ai/en/latest/features/tool_calling/)
- [vLLM qwen3_xml parser](https://docs.vllm.ai/en/latest/api/vllm/tool_parsers/qwen3xml_tool_parser/)
- [Qwen3.5 vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [Qwen3-Next vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Next.html)
- [Step-3.5-Flash vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/StepFun/Step-3.5-Flash.html)
- [vLLM Quantization](https://docs.vllm.ai/en/latest/features/quantization/)
- [LLM Compressor](https://docs.vllm.ai/projects/llm-compressor/en/0.8.1/)

### Guides and Reviews
- [Qwen3-Coder-Next local guide (DEV Community)](https://dev.to/sienna/qwen3-coder-next-the-complete-2026-guide-to-running-powerful-ai-coding-agents-locally-1k95)
- [Qwen3-Coder-Next (Unsloth)](https://unsloth.ai/docs/models/qwen3-coder-next)
- [Qwen3-Coder-Next (kaitchup)](https://kaitchup.substack.com/p/qwen3-coder-next-how-to-run-qwens)
- [IQuest-Coder-V1 review (aicybr)](https://aicybr.com/blog/iquest-coder-v1)
- [Mistral Devstral 2 (VentureBeat)](https://venturebeat.com/ai/mistral-launches-powerful-devstral-2-coding-model-including-open-source)
- [Codestral 25.08 (Mistral)](https://mistral.ai/news/codestral-25-08)
- [DeepSeek V4 rumors (evolink)](https://evolink.ai/blog/deepseek-v4-release-window-prep)
- [Qwen3.5-9B benchmarks (XDA)](https://www.xda-developers.com/qwen-3-5-9b-tops-ai-benchmarks-not-how-pick-model/)
- [SWE-bench contamination (Simon Willison)](https://simonwillison.net/2026/Feb/19/swe-bench/)

### Data Quality Notes
- SWE-bench Verified scores are scaffold-dependent (10-20% variation) and increasingly contaminated
- LiveCodeBench v6 is NOT comparable to v5 or earlier
- VRAM estimates include model weights only; add 2-4 GB for KV cache and framework overhead
- Speed estimates assume AWQ on 4090 with `--max-model-len 32768`
- IQuest-Coder scores are self-reported by an unknown lab; independent verification pending
- DeepSeek V4 information is entirely from leaks/rumors; nothing is confirmed

---

*Last updated: 2026-03-13*
