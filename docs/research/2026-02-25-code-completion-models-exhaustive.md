# Code Completion & FIM Models: Exhaustive Survey

**Date:** 2026-02-25
**Author:** Research Agent (Claude Opus 4.6)
**Status:** Complete
**Scope:** All code completion, Fill-in-the-Middle (FIM), and IDE-integration models available as of February 2026, with focus on releases from the last 90 days (Dec 2025 - Feb 2026).

---

## Context

Code completion is fundamentally different from code generation:
- **Code generation**: "Write a function that does X" produces a complete function
- **Code completion/FIM**: Given a cursor position in existing code (with prefix and suffix context), the model predicts what goes in the middle
- FIM requires specialized training with prefix-suffix-middle (PSM) or suffix-prefix-middle (SPM) objectives

For IDE inline suggestions, latency under 200ms is critical. This means small, fast models on dedicated GPUs, not the same large models used for chat.

---

## Table of Contents

1. [Models Released/Updated Dec 2025 - Feb 2026](#new-releases)
2. [Complete FIM Model Inventory](#complete-inventory)
3. [FIM Token Formats Reference](#fim-formats)
4. [Benchmark Comparison](#benchmarks)
5. [VRAM Requirements](#vram)
6. [Self-Hosted Code Completion Tools](#tools)
7. [Latency Analysis](#latency)
8. [Recommendation for Athanor](#recommendation)
9. [Sources](#sources)

---

## <a name="new-releases"></a>1. Models Released/Updated Dec 2025 - Feb 2026

### Qwen3-Coder-Next-80B-A3B-Base (February 2026)

| Property | Value |
|----------|-------|
| **Organization** | Qwen (Alibaba) |
| **Parameters** | 80B total, **3B active** (MoE) |
| **Architecture** | Hybrid: Gated DeltaNet (linear attention) + Gated Attention + MoE (512 experts, 10 active) |
| **FIM Support** | Yes: `<\|fim_prefix\|>`, `<\|fim_suffix\|>`, `<\|fim_middle\|>` |
| **Context Length** | 256K native, 1M with YaRN |
| **Languages** | 370+ |
| **License** | Apache 2.0 |
| **Release** | ~February 3, 2026 |
| **HuggingFace** | [Qwen/Qwen3-Coder-Next-Base](https://huggingface.co/Qwen/Qwen3-Coder-Next-Base) |

**Why it matters:** Only 3B active parameters despite 80B total. The hybrid attention architecture (DeltaNet + standard) is novel. If inference engines support the architecture efficiently, this could offer strong quality at low latency. Base model is suitable for FIM. FP8 and GGUF quantizations available.

**Caveats:** Novel architecture may have limited inference engine support (needs vLLM/SGLang validation). 80B total params means large disk/memory footprint despite low active params.

### Qwen3-Coder-30B-A3B-Instruct (May 2025, actively maintained)

| Property | Value |
|----------|-------|
| **Parameters** | 30.5B total, **3.3B active** (MoE, 128 experts, 8 active) |
| **FIM Support** | Yes (same format as Qwen3-Coder family) |
| **Context Length** | 256K native |
| **License** | Apache 2.0 |
| **HuggingFace** | [Qwen/Qwen3-Coder-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct) |

**Why it matters:** 3.3B active params on a smaller total footprint (30B vs 80B). Available on Ollama (19GB download). Instruct-tuned but FIM still supported per Qwen docs.

### IQuest-Coder-V1-40B-Base (December 2025)

| Property | Value |
|----------|-------|
| **Organization** | IQuestLab |
| **Parameters** | 40B (dense) |
| **Architecture** | GQA, 80 layers |
| **FIM Support** | Not documented |
| **Context Length** | 128K native |
| **Benchmarks** | SWE-Bench Verified: 76.2%, BigCodeBench: 49.9%, LiveCodeBench v6: 81.1% |
| **License** | Custom (`iquestcoder`) |
| **HuggingFace** | [IQuestLab/IQuest-Coder-V1-40B-Base](https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Base) |

**Why it matters:** Strong agentic coding benchmarks (76.2% SWE-Bench Verified). However, no documented FIM support makes it unsuitable for inline code completion. Better for code generation tasks.

### Devstral-2-123B-Instruct-2512 (December 2025)

| Property | Value |
|----------|-------|
| **Organization** | Mistral AI |
| **Parameters** | 123B |
| **FIM Support** | Not documented (agentic coding focus) |
| **Context Length** | Not specified |
| **License** | Not specified |
| **HuggingFace** | [mistralai/Devstral-2-123B-Instruct-2512](https://huggingface.co/mistralai/Devstral-2-123B-Instruct-2512) |

**Assessment:** Agentic coding model (SWE-bench focused), not a code completion model. Too large and wrong modality for inline completion.

### Devstral-Small-2-24B-Instruct-2512 (December 2025)

| Property | Value |
|----------|-------|
| **Organization** | Mistral AI |
| **Parameters** | 24B |
| **FIM Support** | Not documented |
| **Benchmarks** | SWE-Bench Verified: 46.8%+ (Devstral family claim) |
| **License** | Apache 2.0 |
| **HuggingFace** | [mistralai/Devstral-Small-2-24B-Instruct-2512](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512) |

**Assessment:** Small enough to run locally on a 4090, but designed for agentic coding (multi-file edits, GitHub issues), not inline FIM completion.

### Tabby v0.32.0 (January 25, 2026)

Self-hosted code completion server update. See [Tools section](#tools).

### Continue.dev v1.2.16-vscode (February 17, 2026)

IDE extension update. See [Tools section](#tools).

### Community FIM Fine-tunes (Feb 2026)

| Model | Base | Parameters | Updated |
|-------|------|------------|---------|
| jolovicdev/Qwen2.5-Coder-1.5B-LF-FIM-Heavy | Qwen2.5-Coder-1.5B | 1.5B | ~Feb 16, 2026 |
| lllqaq/R2EGym-32B-Agent-Coder-Instruct-fim | Qwen? | 32B | ~Feb 21, 2026 |

These are community fine-tunes optimizing FIM behavior on existing base models. The LF-FIM-Heavy variant targets improved line-feed handling in completions.

---

## <a name="complete-inventory"></a>2. Complete FIM Model Inventory

### Tier 1: Purpose-Built FIM Models (Recommended for Code Completion)

#### Qwen2.5-Coder Family (November 2024, updated Jan 2025)

| Size | Params | FIM | Context | HumanEval | License | VRAM (FP16) | VRAM (Q4) |
|------|--------|-----|---------|-----------|---------|-------------|-----------|
| 0.5B | 0.5B | Yes | 32K | ~25%* | Apache 2.0 | ~1 GB | ~0.5 GB |
| 1.5B | 1.5B | Yes | 32K | ~35%* | Apache 2.0 | ~3 GB | ~1.5 GB |
| 3B | 3B | Yes | 32K | ~40%* | Qwen Research | ~6 GB | ~2.5 GB |
| 7B | 7.6B | Yes | 128K | ~55%* | Apache 2.0 | ~15 GB | ~5 GB |
| 14B | 14.7B | Yes | 128K | ~65%* | Apache 2.0 | ~29 GB | ~9 GB |
| 32B | 32.5B | Yes | 128K | ~75%* | Apache 2.0 | ~65 GB | ~20 GB |

*Approximate HumanEval scores from technical report aggregate data.

**FIM Format:** `<|fim_prefix|>` + prefix + `<|fim_suffix|>` + suffix + `<|fim_middle|>`
**Training:** 5.5T tokens, code + text-code grounding + synthetic data
**Code Completion Benchmarks:** SOTA on HumanEval-Infilling, CrossCodeEval, CrossCodeLongEval, RepoEval, SAFIM (5 completion benchmarks, per Qwen blog)
**Languages:** 40+ with strong multi-language performance
**HuggingFace:** [Qwen/Qwen2.5-Coder-{size}](https://huggingface.co/collections/Qwen/qwen25-coder-66eaa22e6f99801bf65b0c2f)

**Assessment:** The current gold standard for open-source FIM code completion. The 1.5B and 7B sizes offer the best speed/quality tradeoff for inline completion.

#### Codestral 25.01 (January 2025)

| Property | Value |
|----------|-------|
| **Parameters** | ~22B (not officially disclosed for 25.01) |
| **FIM Support** | Yes - SOTA FIM performance |
| **Context Length** | 256K tokens (8x increase over v0.1) |
| **HumanEval** | 86.6% |
| **HumanEval FIM** | 85.9% average, 95.3% FIM pass@1 |
| **Languages** | 80+ |
| **License** | Mistral AI Non-Production License (research/testing only) |
| **API FIM Endpoint** | `https://api.mistral.ai/v1/fim/completions` |

**Assessment:** Best raw FIM performance numbers of any model. But the non-production license and lack of open weights (API-only or gated) limits self-hosted use. The 256K context is excellent for repo-level completion.

#### Codestral 22B v0.1 (May 2024)

| Property | Value |
|----------|-------|
| **Parameters** | 22B |
| **FIM Support** | Yes |
| **Context Length** | 32K tokens |
| **Languages** | 80+ |
| **License** | Mistral AI Non-Production License |
| **Ollama Size** | 13 GB (Q4) |
| **HuggingFace** | [mistralai/Codestral-22B-v0.1](https://huggingface.co/mistralai/Codestral-22B-v0.1) |

**Assessment:** Superseded by Codestral 25.01 in quality. Still available on Ollama. Non-production license is the main blocker.

#### StarCoder2 (February 2024)

| Size | Params | FIM | Context | HumanEval | RepoBench | License | VRAM (FP16) | VRAM (Q4) |
|------|--------|-----|---------|-----------|-----------|---------|-------------|-----------|
| 3B | 3B | Yes | 16K | 31.7% | 71.19 (edit-sim) | OpenRAIL-M | ~6.3 GB | ~2.0 GB |
| 7B | 7B | Yes | 16K | ~35% | ~72 | OpenRAIL-M | ~14 GB | ~4.0 GB |
| 15B | 15B | Yes | 16K | 46.3% | 74.08 (edit-sim) | OpenRAIL-M | ~32 GB | ~9.2 GB |

**FIM Format:** Trained with FIM objective per [Bavarian et al. 2022](https://arxiv.org/abs/2207.14255). Tokens: `<fim_prefix>`, `<fim_suffix>`, `<fim_middle>`
**Training:** 3-4T+ tokens from The Stack v2 (600+ languages for 15B, 17 for 3B/7B)
**HuggingFace:** [bigcode/starcoder2-{size}](https://huggingface.co/bigcode/starcoder2-3b)

**Assessment:** Solid workhorse models with well-tested FIM. The 3B is an excellent small model for fast completion. Outclassed by Qwen2.5-Coder on most benchmarks but very well-supported across tools.

#### CodeGemma (April 2024)

| Size | Params | FIM | Context | HumanEval | HE Single-Line | HE Multi-Line | License |
|------|--------|-----|---------|-----------|----------------|---------------|---------|
| 2B | 2B | Yes | 8K | 31.1% | 78.41% | 51.44% | Gemma License |
| 7B | 7B | Yes | 8K | ~45% | ~85% | ~60% | Gemma License |

**FIM Format:** PSM/SPM (50-50 split), 80% FIM rate during training
**Tokens:** `<|fim_prefix|>`, `<|fim_suffix|>`, `<|fim_middle|>`, `<|file_separator|>` (multi-file)
**Languages:** Python, JavaScript, Java, C++, C#, Go, Kotlin, Rust
**Training:** 500B additional tokens on Gemma base; TPUv5e
**HuggingFace:** [google/codegemma-{size}](https://huggingface.co/google/codegemma-2b)

**Assessment:** The 2B model is specifically optimized for fast completion (2x faster than 7B). Multi-file FIM support via `<|file_separator|>` token is unique. 8K context is limiting.

#### JetBrains Mellum-4B (2025)

| Property | Value |
|----------|-------|
| **Parameters** | 4B |
| **Architecture** | LLaMA-style |
| **FIM Support** | Yes: `<fim_prefix>`, `<fim_suffix>`, `<fim_middle>`, `<filename>` (multi-file) |
| **Context Length** | 8,192 tokens |
| **HE Infilling (Single-Line)** | 80.45% (SFT-Python) |
| **HE Infilling (Multi-Line)** | 48.19% (SFT-Python) |
| **RepoBench (Python, avg <=8k)** | 29.87% (SFT-Python) |
| **SAFIM (Average)** | 42.12% (SFT-Python) |
| **Training** | 4.2T tokens on 256x H200 GPUs |
| **License** | Apache 2.0 |
| **VRAM** | ~8-10 GB (FP16), ~4 GB (Q4) |
| **Variants** | base, sft-python, sft-kotlin, sft-all |
| **HuggingFace** | [JetBrains/Mellum-4b-base](https://huggingface.co/JetBrains/Mellum-4b-base) |
| **Ollama** | `JetBrains/Mellum-4b-sft-all` |

**Assessment:** Purpose-built for IDE code completion by JetBrains (makers of IntelliJ). Strong single-line infilling (80.45%). Multi-file context via `<filename>` token. The sft-all variant covers all languages. 4B params means fast inference. Excellent candidate for self-hosted completion.

#### DeepSeek-Coder-V2-Lite (June 2024)

| Property | Value |
|----------|-------|
| **Parameters** | 16B total, **2.4B active** (MoE) |
| **FIM Support** | Yes: `<\|fim_begin\|>`, `<\|fim_hole\|>`, `<\|fim_end\|>` |
| **Context Length** | 128K tokens |
| **HumanEval** | 81.1% (Instruct) |
| **Languages** | 338 |
| **License** | DeepSeek License (permissive) |
| **Ollama Size** | 8.9 GB |
| **HuggingFace** | [deepseek-ai/DeepSeek-Coder-V2-Lite-Base](https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Base) |

**Assessment:** MoE architecture means only 2.4B params active per token despite 16B total. 128K context and 338 languages are impressive. Good FIM support with unique token format. The MoE efficiency makes this competitive with smaller dense models on latency.

#### Stable Code 3B (2024)

| Property | Value |
|----------|-------|
| **Parameters** | 2.7B |
| **FIM Support** | Yes: `<fim_prefix>`, `<fim_suffix>`, `<fim_middle>` |
| **Context Length** | 16,384 tokens |
| **HumanEval (Python)** | 32.4% |
| **Languages** | 18 (C, C++, Java, JS, CSS, Go, HTML, Ruby, Rust, Markdown, Shell, PHP, SQL, R, TS, Python, Jupyter, RST) |
| **License** | Stability AI Community License (commercial license separate) |
| **VRAM** | ~6 GB (FP16), ~2 GB (Q4) |
| **HuggingFace** | [stabilityai/stable-code-3b](https://huggingface.co/stabilityai/stable-code-3b) |

**Assessment:** Compact and fast. Outperformed by Qwen2.5-Coder-3B on most metrics. Limited language support. Community license adds friction.

#### Refact-1.6B-fim (August 2023)

| Property | Value |
|----------|-------|
| **Parameters** | 1.6B |
| **FIM Support** | Yes: `<fim_prefix>`, `<fim_suffix>`, `<fim_middle>` |
| **Context Length** | 4,096 tokens |
| **HumanEval** | 32.0% (pass@1) |
| **Architecture** | LLaMA-like, Multi-Query Attention, ALiBi |
| **License** | BigScience OpenRAIL-M v1 |
| **VRAM** | ~3.2 GB (FP16), ~1.5 GB (Q4) |
| **HuggingFace** | [smallcloudai/Refact-1_6B-fim](https://huggingface.co/smallcloudai/Refact-1_6B-fim) |

**Assessment:** Dated model. Outclassed by Qwen2.5-Coder-1.5B on every metric. 4K context is severely limiting. Only relevant as historical reference.

#### CodeLlama (August 2023)

| Size | FIM | Context | HumanEval | License |
|------|-----|---------|-----------|---------|
| 7B | Yes | 16K (100K with RoPE scaling) | ~33% | Llama 2 |
| 13B | Yes | 16K | ~36% | Llama 2 |
| 34B | No | 16K | ~48% | Llama 2 |
| 70B | No | 16K | ~53% | Llama 2 |

**FIM Format:** SPM format with `<PRE>`, `<SUF>`, `<MID>` tokens (7B and 13B only)
**Languages:** Python + many others
**HuggingFace:** [codellama/CodeLlama-7b-hf](https://huggingface.co/codellama/CodeLlama-7b-hf)

**Assessment:** Legacy model. FIM only on 7B and 13B variants. Outclassed by all newer models. Not recommended for new deployments.

### Tier 2: General Code Models (Not Purpose-Built for FIM)

#### DeepSeek-V3 (December 2024)

| Property | Value |
|----------|-------|
| **Parameters** | 671B total, 37B active (MoE) |
| **FIM Support** | Not documented |
| **Context** | 128K |
| **HumanEval** | 65.2% (base) |
| **License** | Model Agreement (proprietary) |

**Assessment:** Powerful general model but not designed for inline FIM completion. Too large for dedicated completion service.

#### Yi-Coder-9B (March 2024)

| Property | Value |
|----------|-------|
| **Parameters** | 9B |
| **FIM Support** | Not documented |
| **Context** | 128K |
| **Languages** | 52 |
| **License** | Apache 2.0 |
| **HuggingFace** | [01-ai/Yi-Coder-9B](https://huggingface.co/01-ai/Yi-Coder-9B) |

**Assessment:** Strong coding model but no documented FIM support. Better for code generation than inline completion.

#### IBM Granite Code (September 2024)

| Size | Context | FIM | License |
|------|---------|-----|---------|
| 3B | 2K-128K | Not documented | Apache 2.0 |
| 8B | 4K-128K | Not documented | Apache 2.0 |
| 20B | 8K | Not documented | Apache 2.0 |
| 34B | 8K | Not documented | Apache 2.0 |

**Assessment:** IBM enterprise focus. No documented FIM support. Granite 3.0/3.3 are general-purpose, not code-specific.

#### Qwen3-Coder-480B-A35B-Instruct (May 2025)

| Property | Value |
|----------|-------|
| **Parameters** | 480B total, 35B active (MoE, 160 experts, 8 active) |
| **FIM Support** | Yes per Qwen docs |
| **Context** | 256K native, 1M extended |
| **License** | Apache 2.0 |

**Assessment:** Far too large for dedicated completion. Designed for agentic coding tasks. The 30B-A3B variant is the right size from this family.

---

## <a name="fim-formats"></a>3. FIM Token Formats Reference

| Model Family | Format | Prefix Token | Suffix Token | Middle Token | Multi-file |
|-------------|--------|-------------|-------------|-------------|------------|
| Qwen2.5-Coder | PSM | `<\|fim_prefix\|>` | `<\|fim_suffix\|>` | `<\|fim_middle\|>` | No |
| Qwen3-Coder | PSM | `<\|fim_prefix\|>` | `<\|fim_suffix\|>` | `<\|fim_middle\|>` | No |
| StarCoder2 | PSM | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` | No |
| CodeGemma | PSM/SPM | `<\|fim_prefix\|>` | `<\|fim_suffix\|>` | `<\|fim_middle\|>` | `<\|file_separator\|>` |
| CodeLlama | SPM | `<PRE>` | `<SUF>` | `<MID>` | No |
| DeepSeek-Coder-V2 | PSM | `<\|fim_begin\|>` | `<\|fim_hole\|>` | `<\|fim_end\|>` | No |
| Mellum | SPM | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` | `<filename>` |
| Stable Code | PSM | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` | No |
| Refact | PSM | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` | No |
| Codestral | API | N/A (uses `prompt`/`suffix` params) | | | No |

**PSM** = Prefix-Suffix-Middle (most common): prefix code, then suffix code, then model generates middle
**SPM** = Suffix-Prefix-Middle: suffix first, then prefix, then generate middle

---

## <a name="benchmarks"></a>4. Benchmark Comparison

### HumanEval Pass@1 (Code Generation)

| Model | Size | HumanEval |
|-------|------|-----------|
| Codestral 25.01 | 22B | **86.6%** |
| DeepSeek-Coder-V2-Lite-Instruct | 16B (2.4B active) | 81.1% |
| Qwen2.5-Coder-32B-Instruct | 32B | ~75%* |
| IQuest-Coder-V1-40B | 40B | ~70%* |
| StarCoder2-15B | 15B | 46.3% |
| CodeGemma-7B | 7B | ~45%* |
| Qwen2.5-Coder-7B | 7B | ~55%* |
| Mellum-4B-sft-python | 4B | ~40%* |
| StarCoder2-3B | 3B | 31.7% |
| Qwen2.5-Coder-1.5B | 1.5B | ~35%* |
| CodeGemma-2B | 2B | 31.1% |
| Refact-1.6B | 1.6B | 32.0% |

*Approximate from aggregated data.

### HumanEval Infilling (FIM-Specific)

| Model | Single-Line | Multi-Line | Random Span |
|-------|-------------|------------|-------------|
| Codestral 25.01 | **~95%** | N/A | N/A |
| Mellum-4B-sft-python | 80.45% | 48.19% | 37.68% |
| CodeGemma-2B | 78.41% | 51.44% | N/A |
| Mellum-4B-base | 66.21% | 38.52% | 29.70% |

### RepoBench v1.1 (Repository-Level Completion)

| Model | Edit Similarity |
|-------|----------------|
| StarCoder2-15B | **74.08** |
| StarCoder2-3B | 71.19 |
| Mellum-4B-sft-python (Avg <=8K) | 29.87 (EM) |

Note: RepoBench uses different metrics (edit similarity vs exact match) across papers, making direct comparison difficult.

---

## <a name="vram"></a>5. VRAM Requirements

### For Athanor Hardware (5070 Ti = 16 GB, 4090 = 24 GB)

| Model | FP16 | Q8 | Q4 | Fits 5070 Ti? | Fits 4090? |
|-------|------|----|----|---------------|------------|
| Qwen2.5-Coder-0.5B | ~1 GB | ~0.7 GB | ~0.4 GB | Yes | Yes |
| Qwen2.5-Coder-1.5B | ~3 GB | ~2 GB | ~1.2 GB | Yes | Yes |
| CodeGemma-2B | ~4 GB | ~3 GB | ~1.6 GB | Yes | Yes |
| Stable Code 3B | ~6 GB | ~4 GB | ~2 GB | Yes | Yes |
| StarCoder2-3B | ~6.3 GB | ~3.4 GB | ~2 GB | Yes | Yes |
| Mellum-4B | ~8 GB | ~5 GB | ~3 GB | Yes | Yes |
| Qwen2.5-Coder-7B | ~15 GB | ~8 GB | ~5 GB | Yes (Q8) | Yes |
| StarCoder2-7B | ~14 GB | ~8 GB | ~4 GB | Yes (Q8) | Yes |
| CodeGemma-7B | ~14 GB | ~8 GB | ~5 GB | Yes (Q8) | Yes |
| Qwen2.5-Coder-14B | ~29 GB | ~16 GB | ~9 GB | No | Q8 tight |
| StarCoder2-15B | ~32 GB | ~17 GB | ~9.2 GB | No | Q4 only |
| DeepSeek-Coder-V2-Lite (16B) | ~32 GB* | ~9 GB* | ~5 GB* | Yes (Q4)** | Yes (Q8)** |
| Codestral 22B | ~44 GB | ~24 GB | ~13 GB | No | Q4 only |
| Qwen2.5-Coder-32B | ~65 GB | ~35 GB | ~20 GB | No | No (need TP) |
| Qwen3-Coder-30B-A3B | ~60 GB* | ~20 GB* | ~12 GB* | No | Q4 only** |
| Qwen3-Coder-Next-80B-A3B | ~160 GB* | ~85 GB* | ~50 GB* | No | No (need TP) |

*MoE models: total weights are large but active computation uses fewer params.
**MoE models need all weights in memory despite low active params.

### Key Takeaway for 5070 Ti (16 GB)

Models that fit comfortably on a single 5070 Ti in FP16:
- Qwen2.5-Coder-0.5B, 1.5B, 3B
- StarCoder2-3B
- CodeGemma-2B
- Stable Code 3B
- Mellum-4B
- Refact-1.6B

Models that fit in Q8 on a single 5070 Ti:
- Qwen2.5-Coder-7B
- StarCoder2-7B
- CodeGemma-7B

---

## <a name="tools"></a>6. Self-Hosted Code Completion Tools

### Tabby (v0.32.0, January 2026)

| Property | Value |
|----------|-------|
| **Architecture** | Rust-based server |
| **IDE Support** | VSCode, Vim/Neovim, JetBrains |
| **Supported Models** | StarCoder 1B/3B/7B, StarCoder2 3B/7B, CodeLlama 7B/13B, CodeGemma 2B/7B, Qwen2.5-Coder 0.5B-14B, Codestral 22B, DeepSeek-Coder-V2-Lite |
| **Features** | Repository-context RAG, Answer Engine, code browser, team management |
| **FIM** | Built-in FIM support for all listed models |
| **Self-Contained** | No external DBMS needed |
| **GPU** | Consumer GPUs supported, Metal on Apple Silicon |
| **License** | Apache 2.0 |
| **GitHub** | [TabbyML/tabby](https://github.com/TabbyML/tabby) (32.9K stars) |

**Assessment:** Most mature self-hosted option. Repository-context RAG is a differentiator (goes beyond single-file FIM). Active development with January 2026 release.

### Continue.dev (v1.2.16, February 2026)

| Property | Value |
|----------|-------|
| **Architecture** | TypeScript, Node.js 20+ |
| **IDE Support** | VSCode, JetBrains, Neovim |
| **Autocomplete Backend** | Ollama, OpenAI-compatible, HF Inference API |
| **Features** | AI checks in CI, inline editing, @-mention files for context |
| **Model Configuration** | User-configurable (any model via Ollama or API) |
| **License** | Apache 2.0 |
| **GitHub** | [continuedev/continue](https://github.com/continuedev/continue) (31.5K stars) |

**Assessment:** Very actively developed (801 releases). More of a full AI coding platform than just completion. Supports any model through Ollama/OpenAI-compatible APIs. The CI checks feature is unique.

### Refact.ai (v1.11.2, June 2025)

| Property | Value |
|----------|-------|
| **Architecture** | Rust + TypeScript |
| **IDE Support** | VSCode, JetBrains |
| **Default Model** | Qwen2.5-Coder-1.5B with RAG |
| **Features** | Context-aware completion, RAG, GitHub/GitLab integration, Docker execution |
| **FIM** | RAG-powered completion (goes beyond basic FIM) |
| **Self-Hosting** | Docker container available |
| **License** | BSD-3-Clause |
| **GitHub** | [smallcloudai/refact](https://github.com/smallcloudai/refact) (3.5K stars) |

**Assessment:** Bundles its own model (Qwen2.5-Coder-1.5B). RAG-enhanced completion adds context awareness. Less flexible than Tabby for model choice.

### llm-ls (v0.5.3, May 2024)

| Property | Value |
|----------|-------|
| **Architecture** | LSP server |
| **IDE Support** | Neovim (llm.nvim), VSCode (llm-vscode), JetBrains (llm-intellij), Jupyter |
| **Backends** | HF Inference API, text-generation-inference, Ollama, OpenAI-compatible |
| **FIM** | Supports both FIM and standard completion modes |
| **License** | Apache 2.0 |
| **GitHub** | [huggingface/llm-ls](https://github.com/huggingface/llm-ls) |

**Assessment:** Lightweight LSP approach. Less batteries-included than Tabby but more composable. "Work in progress" status noted. Good for Neovim-first users.

### Commercial/Proprietary (Not Self-Hostable)

| Tool | Context | Latency | IDE Support | Self-Host? |
|------|---------|---------|-------------|------------|
| **Supermaven** | 1M tokens | ~250ms | VSCode, JetBrains, Neovim | No |
| **GitHub Copilot** | Unknown | ~300ms typical | All major | No |
| **Cody (Sourcegraph)** | Repo-level | Varies | VSCode, JetBrains | Enterprise only |
| **Windsurf (Codeium)** | Unknown | ~200ms | VSCode, JetBrains | No |

---

## <a name="latency"></a>7. Latency Analysis

For inline code completion, **latency under 200ms is the threshold** for a seamless user experience. This is time from keystroke to suggestion appearing.

### Latency Budget Breakdown

| Component | Budget |
|-----------|--------|
| Network (local) | ~1ms |
| Tokenization | ~5ms |
| Prefill (context processing) | 50-100ms |
| Generation (first token) | 10-50ms |
| Generation (~20 tokens) | 20-100ms |
| Detokenization + UI | ~5ms |
| **Total** | **~100-260ms** |

### Estimated Tokens/Second by Model Size on Single GPU

Based on general inference benchmarks for decoder-only models with vLLM/SGLang:

| Model Size | 5070 Ti (FP16) | 5070 Ti (Q4) | 4090 (FP16) | 4090 (Q4) |
|------------|----------------|--------------|-------------|-----------|
| 0.5B | ~200 tok/s | ~300 tok/s | ~250 tok/s | ~350 tok/s |
| 1.5B | ~120 tok/s | ~200 tok/s | ~150 tok/s | ~250 tok/s |
| 3B | ~80 tok/s | ~150 tok/s | ~100 tok/s | ~180 tok/s |
| 4B | ~60 tok/s | ~120 tok/s | ~80 tok/s | ~150 tok/s |
| 7B | ~40 tok/s | ~80 tok/s | ~50 tok/s | ~100 tok/s |
| 7B (Q8) | ~50 tok/s | N/A | ~65 tok/s | N/A |

**Note:** These are rough estimates. Actual performance depends on batch size, context length, attention implementation, and GPU memory bandwidth. The 5070 Ti and 4090 have different memory bandwidth profiles (512 GB/s vs 1 TB/s for 4090).

### Time to Generate 20 Tokens (Typical Completion)

| Model | 5070 Ti (FP16) | 4090 (FP16) |
|-------|----------------|-------------|
| Qwen2.5-Coder-0.5B | ~100ms | ~80ms |
| Qwen2.5-Coder-1.5B | ~165ms | ~135ms |
| StarCoder2-3B | ~250ms | ~200ms |
| Mellum-4B | ~330ms | ~250ms |
| Qwen2.5-Coder-7B | ~500ms | ~400ms |
| Qwen2.5-Coder-7B (Q4) | ~250ms | ~200ms |

**For <200ms total latency on a 5070 Ti (FP16):** Only 0.5B and 1.5B models reliably meet this.
**For <200ms on 4090 (FP16):** 0.5B, 1.5B, and possibly 3B models.
**With Q4 quantization:** 3B-4B models become viable on both GPUs.

### MoE Model Latency Consideration

MoE models (DeepSeek-Coder-V2-Lite with 2.4B active, Qwen3-Coder-30B with 3.3B active) process each token through only the active parameters. This means:
- **Compute cost** is similar to a 2-3B dense model
- **Memory bandwidth cost** is much higher because all expert weights must be in memory
- **Effective throughput** falls between the active param count and total param count
- Net result: faster than dense equivalent of total params, slower than dense equivalent of active params

For a 16GB GPU, MoE models that require >16GB weights won't fit regardless of active param count.

---

## <a name="recommendation"></a>8. Recommendation for Athanor

### Architecture: Dedicated Completion GPU

Given that Athanor has 4x 5070 Ti (16GB) + 1x 4090 (24GB):

**Option A: Qwen2.5-Coder-1.5B on a 5070 Ti** (Recommended)
- VRAM: ~3 GB (FP16), leaves 13 GB for other services
- Latency: ~165ms for 20 tokens on 5070 Ti
- Quality: SOTA among sub-2B models, trained on 5.5T tokens
- FIM: Full support with standard tokens
- License: Apache 2.0
- Tradeoff: Good quality but not amazing for complex completions

**Option B: Qwen2.5-Coder-7B (Q4_K_M) on a 5070 Ti**
- VRAM: ~5 GB quantized
- Latency: ~250ms for 20 tokens (slightly over budget)
- Quality: Significantly better than 1.5B, approaches GPT-4o class on code
- FIM: Full support
- Tradeoff: Slightly over latency budget, quantization may reduce quality marginally

**Option C: Mellum-4B-sft-all on a 5070 Ti**
- VRAM: ~8 GB (FP16) or ~3 GB (Q4)
- Latency: ~250ms (FP16) or ~160ms (Q4) for 20 tokens
- Quality: Purpose-built for IDE completion by JetBrains, 80.45% single-line infilling
- FIM: Full support with multi-file `<filename>` context
- License: Apache 2.0
- Tradeoff: Limited benchmarks outside JetBrains' own evaluation; newer than Qwen but less proven

**Option D: Qwen2.5-Coder-7B (FP16) on 4090**
- VRAM: ~15 GB
- Latency: ~135ms for 20 tokens (well within budget)
- Quality: Best quality that fits a single GPU
- Tradeoff: Uses the 4090, which is currently part of the TP=4+1 vLLM cluster

### Recommended Approach

1. **Deploy Qwen2.5-Coder-1.5B** on one of the 5070 Ti GPUs (GPU 4 on Node 1 already runs embedding + voice, so use a different GPU or Node 2)
2. **Use Tabby** as the completion server (most mature, has repo-context RAG)
3. **Connect via Continue.dev** VSCode extension (or Tabby's own extension)
4. **Alternative:** Run vLLM with the completion model on a dedicated port, use the `/v1/completions` endpoint with FIM tokens

### Serving Stack Options

**Option 1: Tabby + Built-in Model Serving**
```
Tabby (port 8080) → built-in inference → Qwen2.5-Coder-1.5B
IDE Extension → Tabby API
```
Pros: Single container, repository-aware RAG
Cons: Less control over inference engine, can't share GPU easily

**Option 2: vLLM + Continue.dev**
```
vLLM (port 8001) → Qwen2.5-Coder-1.5B (OpenAI-compatible /v1/completions)
Continue.dev IDE Extension → vLLM endpoint
```
Pros: Familiar stack (already running vLLM), flexible model swapping
Cons: Need to configure FIM token handling in Continue.dev

**Option 3: Ollama + Continue.dev**
```
Ollama → qwen2.5-coder:1.5b
Continue.dev IDE Extension → Ollama endpoint
```
Pros: Simplest setup, one command to start
Cons: Less efficient than vLLM for dedicated serving, no batching

### Model Comparison Matrix for Athanor

| Criteria | Qwen2.5-Coder-1.5B | Qwen2.5-Coder-7B (Q4) | Mellum-4B | StarCoder2-3B |
|----------|---------------------|------------------------|-----------|---------------|
| Quality (FIM) | Good | Very Good | Good (single-line) | Decent |
| Latency (<200ms) | Yes | Marginal | Marginal | Yes |
| VRAM | 3 GB | 5 GB | 8/3 GB | 6/2 GB |
| Languages | 40+ | 40+ | All (sft-all) | 17 |
| Context | 32K | 128K | 8K | 16K |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 | OpenRAIL-M |
| Ecosystem | Excellent | Excellent | Growing | Good |
| Repo-level | No | No (needs RAG) | Multi-file tokens | No |

### What About Qwen3-Coder-Next-80B-A3B?

This model has only 3B active parameters (like a 3B dense model in compute), but requires ~50 GB+ for weights even quantized. It would need TP=4 across four 5070 Ti GPUs just to hold the weights, which defeats the purpose of a lightweight completion service. Not recommended until inference engines optimize MoE weight loading further.

The Qwen3-Coder-30B-A3B has the same problem at a smaller scale: 30B weights need ~12 GB at Q4, fitting on a 4090 but awkward on 5070 Ti. The quality improvement over Qwen2.5-Coder-7B for inline completion is unclear.

---

## <a name="sources"></a>9. Sources

### Model Pages

- Qwen2.5-Coder Collection: https://huggingface.co/collections/Qwen/qwen25-coder-66eaa22e6f99801bf65b0c2f
- Qwen2.5-Coder Blog: https://qwenlm.github.io/blog/qwen2.5-coder-family/
- Qwen3-Coder GitHub: https://github.com/QwenLM/Qwen3-Coder
- Qwen3-Coder Blog: https://qwenlm.github.io/blog/qwen3-coder/
- Qwen3-Coder-Next-Base: https://huggingface.co/Qwen/Qwen3-Coder-Next-Base
- Qwen3-Coder-30B-A3B: https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- StarCoder2-3B: https://huggingface.co/bigcode/starcoder2-3b
- StarCoder2-15B: https://huggingface.co/bigcode/starcoder2-15b
- CodeGemma-2B: https://huggingface.co/google/codegemma-2b
- Codestral v0.1: https://huggingface.co/mistralai/Codestral-22B-v0.1
- Codestral 25.01: https://mistral.ai/news/codestral-2501
- Mistral FIM Docs: https://docs.mistral.ai/capabilities/code_generation/
- DeepSeek-Coder-V2: https://github.com/deepseek-ai/DeepSeek-Coder-V2
- DeepSeek-V3: https://github.com/deepseek-ai/DeepSeek-V3
- JetBrains Mellum-4B: https://huggingface.co/JetBrains/Mellum-4b-base
- Stable Code 3B: https://huggingface.co/stabilityai/stable-code-3b
- Refact-1.6B-fim: https://huggingface.co/smallcloudai/Refact-1_6B-fim
- CodeLlama: https://huggingface.co/codellama/CodeLlama-7b-hf
- Yi-Coder-9B: https://huggingface.co/01-ai/Yi-Coder-9B
- IQuest-Coder-V1-40B: https://huggingface.co/IQuestLab/IQuest-Coder-V1-40B-Base
- IBM Granite Code: https://github.com/ibm-granite/granite-code-models
- Devstral: https://mistral.ai/news/devstral

### Tools

- Tabby: https://github.com/TabbyML/tabby
- Tabby Model Registry: https://tabby.tabbyml.com/docs/models/
- Continue.dev: https://github.com/continuedev/continue
- Refact.ai: https://github.com/smallcloudai/refact
- llm-ls: https://github.com/huggingface/llm-ls
- Supermaven: https://supermaven.com
- Cody: https://sourcegraph.com/cody

### Papers

- StarCoder2: https://arxiv.org/abs/2402.19173
- Qwen2.5-Coder: https://arxiv.org/abs/2409.12186
- Code Llama: https://arxiv.org/abs/2308.12950
- FIM Training: https://arxiv.org/abs/2207.14255

### Ollama Model Library

- Qwen2.5-Coder: https://ollama.com/library/qwen2.5-coder
- Codestral: https://ollama.com/library/codestral
- StarCoder2: https://ollama.com/library/starcoder2
- CodeGemma: https://ollama.com/library/codegemma
- DeepSeek-Coder-V2: https://ollama.com/library/deepseek-coder-v2
- Qwen3-Coder: https://ollama.com/library/qwen3-coder

---

## Appendix: Models NOT Suitable for FIM Code Completion

These models appeared in searches but are **not designed for inline FIM completion**:

| Model | Why Not |
|-------|---------|
| Devstral-2-123B | Agentic coding (SWE-bench), not FIM. Too large. |
| Devstral-Small-24B | Agentic coding, no FIM. |
| Qwen3-Coder-480B | Agentic coding. Way too large for completion. |
| DeepSeek-V3 (671B) | General model, no FIM documented. Enormous. |
| IQuest-Coder-V1-40B | No FIM documented. 40B dense too large for dedicated completion. |
| NVIDIA Nemotron-Nano-8B | General reasoning model, not code-completion focused. |
| GPT-5.2-Codex | Proprietary, API-only. |
| SWE-1.5 (Windsurf) | Proprietary agent model. |
| Granite Code | No FIM documented. Enterprise focus. |
