# Tool Calling & Coding Models for Local Inference

**Date**: 2026-02-16
**Status**: Research complete
**Purpose**: Identify the best open-weight models for tool calling and agentic coding on Athanor's hardware
**Related**: `2026-02-16-frontier-coding-models-local-inference.md` (covers 400B+ models), `2026-02-15-inference-engine.md` (vLLM selection)

---

## Hardware Context

| Node | GPUs | VRAM | RAM | Best Use |
|------|------|------|-----|----------|
| Node 1 | 4x RTX 5070 Ti (16 GB each) | 64 GB (TP=4) | 224 GB DDR4 ECC | Large models via TP or MoE offload |
| Node 2 | RTX 4090 (24 GB) + RTX 5090 (32 GB) | 56 GB (independent) | 128 GB DDR5 | Two independent model instances |

Key constraints:
- RTX 5070 Ti = 16 GB GDDR7 each, 896 GB/s bandwidth, Blackwell sm_120
- RTX 4090 = 24 GB GDDR6X, 1008 GB/s bandwidth, Ada Lovelace sm_89
- RTX 5090 = 32 GB GDDR7, 1792 GB/s bandwidth, Blackwell sm_120
- No NVLink on any GPU; PCIe 4.0 on Node 1, PCIe 5.0 on Node 2
- vLLM is the primary inference engine (ADR-005)

---

## Model Landscape: What Matters for Agents

Agent backbones need three capabilities that most LLMs lack or do poorly:

1. **Tool calling / function calling** — structured output of function names + arguments in a parseable format
2. **Coding ability** — writing, debugging, and reasoning about code
3. **Multi-turn reliability** — maintaining coherent state across many tool-call-response cycles (200+ turns for complex tasks)

The benchmarks that matter:
- **BFCL v3** — Berkeley Function Calling Leaderboard; tests single/multi-turn tool use, parallel calls
- **SWE-bench Verified** — real GitHub issue resolution; the gold standard for agentic coding
- **LiveCodeBench** — code generation from recent problems (not contaminated by training data)
- **HumanEval / MBPP** — code generation basics (largely saturated; most good models score 80%+)
- **Tau2-Bench** — agentic task completion with tool use

---

## Tier 1: Models That Fit Entirely in VRAM (No Offloading)

These are the practical models — they run at full GPU speed with no RAM offloading penalty.

### Qwen3-Coder-30B-A3B (MoE, 30B total / 3B active)

| Metric | Value |
|--------|-------|
| Parameters | 30B total, 3.3B active (128 experts, ~2 active per token) |
| Context | 256K native |
| Q4_K_M GGUF | ~18.6 GB |
| BF16 | ~60 GB |
| Fits on | RTX 4090 (Q4), any single 16 GB GPU (Q4), Node 1 TP=4 (BF16) |
| Speed (RTX 4090, Q4) | ~72.9 tok/s reported |
| SWE-bench Verified | 50.3% (with SWE-Agent) |
| Tool calling | Hermes-style; native MCP support; vLLM parser: `hermes` or `qwen3_xml` |
| License | Apache 2.0 |
| vLLM support | Yes; `--tool-call-parser hermes` or `--tool-call-parser qwen3_xml` |

**Assessment**: The best model for RTX 4090 single-GPU deployment. 73 tok/s at Q4 is excellent for interactive agent use. SWE-bench 50.3% is respectable for a 3B-active model. Tool calling works well through Hermes format. The MoE architecture means only 3B params are active per token, so inference is extremely fast despite the 30B total.

Sources: [Qwen3-Coder 30B Hardware Guide](https://www.arsturn.com/blog/running-qwen3-coder-30b-at-full-context-memory-requirements-performance-tips), [Qwen3-Coder GitHub](https://github.com/QwenLM/Qwen3-Coder), [HF Model Card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)

---

### Qwen3-14B (Dense, 14B)

| Metric | Value |
|--------|-------|
| Parameters | 14B (dense) |
| Context | 128K |
| Q4_K_M GGUF | ~9.5 GB |
| BF16 | ~28 GB |
| Fits on | Any single 16 GB GPU (Q4 or Q8), RTX 4090 (BF16), RTX 5090 (BF16) |
| Speed (RTX 4090, BF16) | ~40-50 tok/s estimated |
| BFCL v3 | ~58-62 (estimated from technical report comparisons) |
| Tau2-Bench (agent) | 65.1 |
| LiveCodeBench v5 | Competitive with Qwen3-30B-A3B (within 5%) |
| ArenaHard | 85.5 (rivals Qwen2.5-32B) |
| Tool calling | Hermes-style; vLLM parser: `hermes` or `qwen` |
| License | Apache 2.0 |
| vLLM support | Yes; `--tool-call-parser hermes` |

**Assessment**: The density of this model means more consistent quality per token than MoE models. At Q4, it fits on a single 16 GB GPU with room to spare. For tool calling specifically, the Tau2-Bench score of 65.1 indicates solid agentic capability. Rivals Qwen2.5-32B on ArenaHard despite being less than half the size.

Sources: [Qwen3-14B HF](https://huggingface.co/Qwen/Qwen3-14B), [Qwen3 Blog](https://qwenlm.github.io/blog/qwen3/), [Apidog Best Qwen Models](https://apidog.com/blog/best-qwen-models/)

---

### Qwen3-32B (Dense, 32B)

| Metric | Value |
|--------|-------|
| Parameters | 32B (dense) |
| Context | 128K |
| Q4_K_M GGUF | ~19.8 GB |
| FP8 | ~32 GB |
| BF16 | ~64 GB |
| Fits on | RTX 4090 (Q4), RTX 5090 (FP8), Node 1 TP=4 (BF16 with 64 GB total) |
| BFCL v3 | 68.2 (leads among Qwen3 sub-flagship models) |
| LiveCodeBench v5 | 70.7 |
| CodeForces | 1974 ELO |
| Tool calling | Hermes-style; vLLM parser: `hermes` or `qwen` |
| License | Apache 2.0 |
| vLLM support | Yes; `--tool-call-parser hermes` |

**Assessment**: The strongest dense model that fits on Athanor hardware. At Q4 it fits on a single RTX 4090 (20 GB). At FP8 it fits on the RTX 5090 (32 GB). At BF16 it could theoretically run on Node 1's 4x 16 GB GPUs with TP=4 (64 GB), though KV cache would be tight. BFCL 68.2 is the best tool-calling score in the Qwen3 sub-flagship range. This is the model to run for tool calling quality.

Sources: [Qwen3 Technical Report](https://arxiv.org/pdf/2505.09388), [bestcodes Qwen3 Benchmarks](https://bestcodes.dev/blog/qwen-3-what-you-need-to-know)

---

### Qwen3-Coder-Next (MoE, 80B total / 3B active)

| Metric | Value |
|--------|-------|
| Parameters | 80B total, 3B active (ultra-sparse MoE) |
| Context | 256K native (1M with YaRN) |
| Q4 | ~46 GB |
| FP8 | ~85 GB |
| Fits on | Node 1 TP=2-4 (Q4, 46 GB); NOT RTX 4090 alone; CPU offload possible |
| SWE-bench Verified | 70.6% (beats DeepSeek-V3.2's 70.2%) |
| SWE-bench Pro | 44.3% |
| SWE-bench Multilingual | 62.8% |
| Speed (CPU offload, 8 GB GPU + 32 GB RAM) | ~12 tok/s |
| Tool calling | XML-style; vLLM parser: `qwen3_coder` |
| License | Apache 2.0 |
| vLLM support | Yes; `--tool-call-parser qwen3_coder` |
| Released | February 2, 2026 |

**Assessment**: Extraordinary SWE-bench performance for a 3B-active model. Beats DeepSeek-V3.2 (37B active) on SWE-bench while using 0.4% of the active parameters. The catch: 80B total params means ~46 GB at Q4, which exceeds any single GPU on Athanor. On Node 1 with TP=4 it fits (46 GB across 64 GB), but only at Q4 with limited KV cache. On Node 2, the RTX 5090 alone (32 GB) can't hold it. CPU offloading works but drops to ~12 tok/s. This is the best coding model that *almost* fits.

Sources: [marc0.dev Review](https://www.marc0.dev/en/blog/qwen3-coder-next-70-swe-bench-with-3b-active-params-local-ai-just-got-real-1770197534528), [VentureBeat](https://venturebeat.com/technology/qwen3-coder-next-offers-vibe-coders-a-powerful-open-source-ultra-sparse), [MarkTechPost](https://www.marktechpost.com/2026/02/03/qwen-team-releases-qwen3-coder-next-an-open-weight-language-model-designed-specifically-for-coding-agents-and-local-development/), [HF Model Card](https://huggingface.co/Qwen/Qwen3-Coder-Next)

---

### MiMo-V2-Flash (MoE, 309B total / 15B active)

| Metric | Value |
|--------|-------|
| Parameters | 309B total, 15B active |
| Context | 32K native, 256K extended |
| Q4_K_M | ~186 GB (too large for VRAM-only) |
| INT8 | ~309 GB |
| Q3/IQ3_XS | Fits on RTX 4090 (24 GB) with heavy offloading |
| Speed (RTX 4090, quantized) | 20-37 tok/s |
| SWE-bench Verified | 80.2% (#3 overall, #1 open-weight as of Feb 2026) |
| Tool calling | Multi-turn tool calls with reasoning; custom parser needed |
| MTP (Multi-Token Prediction) | 2-2.6x decoding speedup |
| License | Apache 2.0 |
| vLLM support | Yes (vLLM recipe available); SGLang recommended for optimal speed |
| Released | December 2025 |

**Assessment**: The SWE-bench champion among open-weight models (80.2%). But 309B total params means it does NOT fit in VRAM without massive offloading. On RTX 4090 with heavy quantization + RAM offloading, you get 20-37 tok/s. The 6x KV-cache reduction from sliding window attention helps, but this is primarily a model for systems with 512+ GB RAM or multiple datacenter GPUs. Not practical as an always-on agent backbone for Athanor.

Sources: [MiMo-V2-Flash GitHub](https://github.com/XiaomiMiMo/MiMo-V2-Flash), [vLLM Recipe](https://docs.vllm.ai/projects/recipes/en/latest/MiMo/MiMo-V2-Flash.html), [AdwaitX Review](https://www.adwaitx.com/xiaomi-mimo-v2-flash-review-benchmarks/)

---

### Llama 3.3 70B (Dense, 70B)

| Metric | Value |
|--------|-------|
| Parameters | 70B (dense) |
| Context | 128K |
| Q4_K_M GGUF | ~40 GB |
| AWQ INT4 | ~35 GB (weights only, +10-20% for KV cache) |
| NVFP4 | ~35 GB |
| Fits on | Node 1 TP=4 (BF16 tight, NVFP4 comfortable); RTX 4090 Q4 (tight w/ offload) |
| Function calling | 84.8% accuracy; excels at parallel multi-function calling |
| HumanEval | ~80% |
| Tool calling | JSON schema; vLLM parser: `llama3_json` |
| License | Llama 3.3 Community License (permissive with use limits) |
| vLLM support | Yes; `--tool-call-parser llama3_json` |

**Assessment**: The classic 70B workhorse. At NVFP4 (~35 GB), Node 1's 64 GB VRAM can hold it with room for KV cache. Tool calling is solid at 84.8% and notably excels at parallel multi-function calling, which is important for agent tasks that dispatch multiple tools simultaneously. The main weakness vs. Qwen3-32B: slightly lower coding benchmark scores and much higher VRAM requirement for comparable quality. But the 70B size gives it better general reasoning.

Sources: [Llama 3.3 70B Guide](https://llamaimodel.com/3-70b/), [Llama 3.3 70B HF](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct), [Novita Function Calling](https://medium.com/@marketing_novita.ai/llama-3-3-70b-function-calling-seamless-integration-for-better-performance-3de25ebab7c9)

---

### Llama 4 Scout (MoE, 109B total / 17B active)

| Metric | Value |
|--------|-------|
| Parameters | 109B total, 17B active (16 experts, 2 active) |
| Context | 10M tokens (!) |
| INT4 | Fits on single H100 (80 GB); ~55-65 GB estimated for INT4 |
| Q4_K_M GGUF | ~65 GB estimated |
| Fits on | Node 1 TP=4 (64 GB, INT4, tight); not single consumer GPU |
| LiveCodeBench | Competitive; 43.4% for Maverick (Scout lower) |
| Tool calling | Llama tool calling format |
| License | Llama 4 Community License |
| vLLM support | Yes; `--tool-call-parser llama3_json` |

**Assessment**: The 10M token context window is unprecedented, but the 109B total params make it harder to deploy locally than Llama 3.3 70B. At INT4 it barely fits on Node 1's 64 GB. The coding performance is weaker than Qwen3-32B and the tool calling story is less mature than Qwen3's. Skip unless the extreme context window is needed.

Sources: [Llama 4 Official](https://www.llama.com/models/llama-4/), [Llama 4 Scout VRAM](https://apxml.com/models/llama-4-scout), [Llama 4 Benchmarks](https://apidog.com/blog/llama-4-api/)

---

### GLM-4.7 (MoE, 355B total / 32B active)

| Metric | Value |
|--------|-------|
| Parameters | 355B total, 32B active |
| Context | 128K |
| Q4_K_M GGUF | ~214 GB (too large for VRAM-only) |
| FP8 | ~30 GB (per the MoE active-param serving pathway) |
| Q4 (15 GB reported for quantized serving) | Possible on single GPU with offload |
| SWE-bench Verified | 74.2% |
| Tool calling | Excellent; vLLM parser: `glm47` |
| Agentic coding | "Matches or surpasses Claude Sonnet 4.5 and GPT-5.1" on agentic tasks |
| License | MIT |
| vLLM support | Yes; `--tool-call-parser glm47` |
| Released | December 2025 |

**Assessment**: Impressive benchmarks and MIT license. But 355B total params means ~214 GB at Q4 — cannot fit in VRAM. With MoE offloading (32B active params in VRAM, rest in RAM), it becomes viable on Node 1 (64 GB VRAM + 224 GB RAM). Speed would be in the 8-15 tok/s range with offloading. The tool calling is reportedly excellent with a dedicated vLLM parser. Best large model option if you're willing to accept offloading speed.

Sources: [GLM-4.7 HF](https://huggingface.co/zai-org/GLM-4.7), [GLM-4.7 Benchmarks](https://llm-stats.com/models/glm-4.7), [GLM-4.7 Flash Guide](https://medium.com/@zh.milo/glm-4-7-flash-the-ultimate-2026-guide-to-local-ai-coding-assistant-93a43c3f8db3)

---

### Codestral 22B (Dense, 22B)

| Metric | Value |
|--------|-------|
| Parameters | 22B (dense) |
| Context | 256K |
| Q4_K_M GGUF | ~12.6 GB |
| BF16 | ~44 GB |
| Fits on | Any single 16 GB GPU (Q4), RTX 4090 (Q6/FP8), RTX 5090 (BF16) |
| HumanEval | 86.6% |
| MBPP | 91.2% |
| Tool calling | Basic; Mistral function calling format |
| License | **MNPL (Non-Production License)** — research/non-commercial only |
| vLLM support | Yes; `--tool-call-parser mistral` |

**Assessment**: Strong coding benchmarks, but the MNPL license is a dealbreaker for any commercial or production use. Codestral 25.01 improved speed (2x faster tokenizer) but kept the restrictive license. For Athanor's purposes, Qwen3-14B or Qwen3-32B match or exceed its capabilities with a permissive Apache 2.0 license. Skip.

Sources: [Codestral 22B HF](https://huggingface.co/mistralai/Codestral-22B-v0.1), [Mistral Codestral Announcement](https://mistral.ai/news/codestral), [Index.dev Codestral Review](https://www.index.dev/blog/mistral-ai-coding-challenges-tests)

---

### Phi-4-Reasoning (Dense, 14B)

| Metric | Value |
|--------|-------|
| Parameters | 14B (dense) |
| Context | 16K (extendable to 64K) |
| Q4_K_M GGUF | ~9 GB |
| BF16 | ~28 GB |
| Fits on | Any single 16 GB GPU (Q4), RTX 4090 (BF16) |
| Coding | 25%+ improvement over base Phi-4 on LiveCodeBench |
| Tool calling | Function calling supported in Phi-4-mini (3.8B) |
| License | MIT |
| vLLM support | Yes (standard HF format) |

**Assessment**: Strong reasoning model at 14B, but the 16K context window is a significant limitation for agentic coding tasks (SWE-bench scenarios often need 32K+). Tool calling support is present but less mature than Qwen3's Hermes-format implementation. The MIT license is attractive. Worth considering as a fast reasoning model, but Qwen3-14B is better for tool-calling-heavy agent workloads.

Sources: [Phi-4-mini HF](https://huggingface.co/microsoft/Phi-4-mini-instruct), [Phi-4 Technical Report](https://www.microsoft.com/en-us/research/uploads/prod/2024/12/P4TechReport.pdf), [Phi-4-Reasoning Report](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/04/phi_4_reasoning.pdf)

---

### DeepSeek-Coder-V2-Lite (MoE, 16B total / 2.4B active)

| Metric | Value |
|--------|-------|
| Parameters | 16B total, 2.4B active |
| Context | 128K |
| BF16 | ~32 GB |
| Q4 | ~10 GB |
| Fits on | Any single GPU easily |
| HumanEval | ~80% (inferred from V2 family) |
| Tool calling | Limited; not designed for agent workflows |
| License | MIT |
| vLLM support | Yes |

**Assessment**: Superseded by Qwen3-Coder-30B-A3B in every dimension. The Qwen model has more active parameters (3.3B vs 2.4B), better coding benchmarks, better tool calling, and similar VRAM requirements. Skip.

Sources: [DeepSeek-Coder-V2 GitHub](https://github.com/deepseek-ai/DeepSeek-Coder-V2), [DeepSeek-Coder-V2 Paper](https://arxiv.org/pdf/2406.11931)

---

### StarCoder2-15B (Dense, 15B)

| Metric | Value |
|--------|-------|
| Parameters | 15B (dense) |
| Context | 16K |
| Q4_K_M GGUF | ~10 GB |
| HumanEval | 44.2% |
| Tool calling | None — pure code completion model |
| License | BigCode OpenRAIL-M |
| vLLM support | Yes |

**Assessment**: Outdated. HumanEval 44.2% was good when it released but Qwen3-14B and even smaller models now exceed 80%. No tool calling capability. 16K context. Skip entirely.

Sources: [StarCoder2 HF](https://huggingface.co/docs/transformers/en/model_doc/starcoder2), [StarCoder2 15B Ollama](https://ollama.com/library/starcoder2:15b)

---

### Command R+ (Dense, 104B)

| Metric | Value |
|--------|-------|
| Parameters | 104B (dense) |
| Context | 128K |
| BF16 | ~193 GB |
| Q4 | ~52 GB |
| Fits on | Node 1 TP=4 (Q4, 52 GB in 64 GB VRAM, tight) |
| Tool calling | Trained for zero-shot multi-step tool use; outperforms GPT-4-turbo on public benchmarks |
| Coding | General-purpose, not specialized for coding |
| License | CC-BY-NC (non-commercial) |
| vLLM support | Yes |

**Assessment**: Excellent tool calling but the CC-BY-NC license restricts commercial use. At 104B dense, it needs Q4 to fit on Node 1 (52 GB out of 64 GB). General-purpose model, not specialized for coding. For Athanor, Qwen3-32B provides better coding + tool calling in a smaller, Apache-licensed package. Skip.

Sources: [Command R+ HF](https://huggingface.co/CohereLabs/c4ai-command-r-plus), [Command R+ Analysis](https://newsletter.ruder.io/p/command-r)

---

## Tier 2: Models Requiring Offloading (Usable But Slower)

These models exceed Athanor's VRAM but work with MoE offloading (active params in VRAM, inactive experts in system RAM).

| Model | Total | Active | Q4 Size | Speed (est.) | SWE-bench | Why Consider |
|-------|-------|--------|---------|-------------|-----------|-------------|
| Qwen3-235B-A22B | 235B | 22B | 143 GB | 8-12 tok/s | N/A (not coding-specific) | Best general-purpose MoE at this tier |
| GLM-4.7 | 355B | 32B | 214 GB | 8-15 tok/s | 74.2% | Best tool calling with offloading |
| Qwen3-Coder-480B-A35B | 480B | 35B | 290 GB | 5-8 tok/s | Leading open-source | Best coding-specific model |
| MiMo-V2-Flash | 309B | 15B | 186 GB | 20-37 tok/s | 80.2% | SWE-bench champion |

Node 1 (64 GB VRAM + 224 GB DDR4 RAM) can handle all of these with offloading. Speed depends on DDR4 bandwidth (~51 GB/s for quad-channel ECC) which is the bottleneck for MoE expert swapping.

---

## vLLM Tool Calling Parser Support

Complete list of supported parsers (as of Feb 2026):

| Parser | Models | Notes |
|--------|--------|-------|
| `hermes` | Qwen3, Hermes-family | Most widely compatible; recommended for Qwen3 |
| `qwen` | Qwen models | Qwen-specific format |
| `qwen3_xml` | Qwen3-Coder | XML-style tool calling for code-heavy args |
| `qwen3_coder` | Qwen3-Coder-Next | New parser for agentic coding |
| `llama3_json` | Llama 3.x, Llama 4 | JSON-schema tool calls |
| `mistral` | Mistral/Codestral | Mistral function calling format |
| `deepseek_v3` | DeepSeek V3 | DeepSeek tool format |
| `deepseek_v31` | DeepSeek V3.1 | Updated parser |
| `glm45` | GLM-4.5 | GLM tool calling |
| `glm47` | GLM-4.7 | Updated GLM parser |
| `kimi_k2` | Kimi K2/K2.5 | Kimi tool format |
| `minimax_m1` | MiniMax M1/M2.5 | MiniMax format |
| `granite` | IBM Granite | IBM format |
| `internlm` | InternLM | InternLM format |
| `xlam` | xLAM | Salesforce xLAM format |
| `functiongemma` | FunctionGemma (270M) | Lightweight edge tool calling |
| `pythonic` | Various | Python-style tool calls |

All Qwen3, Llama 3.x/4, GLM-4.x, DeepSeek V3.x, and Kimi K2 models have first-class vLLM tool calling support.

Source: [vLLM Tool Calling Docs](https://docs.vllm.ai/en/latest/features/tool_calling/)

---

## Structured Output / JSON Mode

vLLM supports structured output through guided decoding for all models:

- `guided_json` — validates output against a JSON schema
- `guided_regex` — matches a regex pattern
- `guided_choice` — restricts to predefined options
- `guided_grammar` — enforces a context-free grammar

Backends: `xgrammar` (default, fast) or `guidance` (more flexible).

**Known issue (resolved)**: Qwen3 models had broken structured output when `enable_thinking=False` in vLLM 0.8.5. Fixed in vLLM 0.9.0+ with the `qwen3` reasoning parser.

All models listed in this document support structured output through vLLM's guided decoding. This is a framework feature, not a model feature.

Source: [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/)

---

## Key Questions Answered

### What's the best tool-calling model at 14B class for 24 GB VRAM?

**Qwen3-14B** at BF16 (28 GB, fits on RTX 4090 or RTX 5090) or Q8 (fits on any 16 GB GPU).

- Tau2-Bench 65.1 for agentic tasks
- ArenaHard 85.5 (rivals 32B models)
- Hermes-format tool calling with first-class vLLM support
- 128K context
- Apache 2.0 license

Runner-up: **Qwen3-Coder-30B-A3B** at Q4 (18.6 GB). Technically a 30B MoE but only activates 3B params, so it's in the same VRAM class. Better at pure coding (SWE-bench 50.3%) but the 14B dense model may be more reliable for general tool calling.

### What's the best coding model at 70B class for 64 GB VRAM?

**Qwen3-32B** at BF16 (64 GB on Node 1 TP=4) or FP8 (32 GB on RTX 5090).

- LiveCodeBench 70.7, BFCL 68.2
- Best quality-per-VRAM for a dense coding model
- At BF16 on Node 1, uses all 64 GB with minimal KV cache room — FP8 or Q4 recommended for production

Alternative: **Llama 3.3 70B** at NVFP4 (~35 GB on Node 1 TP=4, with ~29 GB headroom for KV cache). Better parallel function calling, more general-purpose, but weaker on coding benchmarks.

For maximum coding quality: **Qwen3-Coder-Next** (80B/3B active) at Q4 (~46 GB on Node 1 TP=4). SWE-bench 70.6% but leaves only ~18 GB for KV cache across 4 GPUs.

### How does local tool calling compare to Claude/GPT for agent tasks?

| Model | SWE-bench Verified | BFCL v3 | Notes |
|-------|-------------------|---------|-------|
| Claude Opus 4.5 | 80.9% | ~70% | Best overall |
| GPT-5 | ~75% | 59.2% | Strong coding, weaker BFCL |
| Qwen3-Coder-Next (3B active) | 70.6% | N/A | 87% of Opus quality, runs local |
| GLM-4.7 (32B active) | 74.2% | N/A | Matches Sonnet 4.5 on agentic tasks |
| MiMo-V2-Flash (15B active) | 80.2% | N/A | Matches/exceeds Opus on SWE-bench |
| Qwen3-32B | N/A | 68.2 | Best local BFCL score at this size |
| Qwen3-Coder-30B-A3B | 50.3% | N/A | Good for 3B active |

**The gap is closing fast.** Open-weight models are roughly 6 months behind frontier closed models. The best local model (MiMo-V2-Flash at 80.2%) already matches Opus 4.5 (80.9%) on SWE-bench. The catch is VRAM: models that match frontier quality (MiMo, GLM-4.7, Qwen3-Coder-480B) need 200-600 GB and require offloading on consumer hardware.

For models that fit in VRAM without offloading, expect 50-70% of frontier quality on complex agentic tasks. Qwen3-32B's BFCL 68.2 vs Claude's ~70 shows the tool-calling gap is nearly closed at the pure function-calling level.

### Which models support structured output (JSON mode)?

All of them, through vLLM's guided decoding. This is not a model-level feature — vLLM enforces JSON schema compliance during generation regardless of the model. Every model in this document works with `guided_json`, `guided_regex`, `guided_choice`, and `guided_grammar`.

### What's the state of local agentic coding (SWE-bench performance)?

The frontier is 80%+ on SWE-bench Verified (Claude Opus 4.5 at 80.9%, MiMo-V2-Flash at 80.2%). The performance gap is heavily influenced by the agent scaffold (SWE-Agent, OpenHands, Claude Code, etc.) — the same model can score 10-20% differently depending on the framework.

For Athanor's hardware:
- **In-VRAM models**: Qwen3-Coder-Next at 70.6% SWE-bench is the best you can get without offloading (though it's tight at 46 GB Q4)
- **With offloading**: GLM-4.7 at 74.2% or MiMo-V2-Flash at 80.2% are viable but at 8-37 tok/s
- **The practical choice**: Qwen3-Coder-30B-A3B at 50.3% runs at 73 tok/s on a single RTX 4090, making it the best speed/quality tradeoff for interactive agent use

---

## Recommendations for Athanor

### Primary Agent Backbone: Qwen3-32B (FP8 on RTX 5090)

- **Why**: Best BFCL score (68.2) and LiveCodeBench (70.7) of any model that fits cleanly in VRAM
- **Where**: RTX 5090 at FP8 (32 GB, fits with headroom), or Node 1 TP=4 at NVFP4/Q4
- **Use for**: Tool-calling-heavy agent tasks, general assistant, MCP integration
- **Speed**: Fast dense inference; no MoE routing overhead

### Coding Agent: Qwen3-Coder-30B-A3B (Q4 on RTX 4090)

- **Why**: 73 tok/s, SWE-bench 50.3%, Apache 2.0, 18.6 GB at Q4
- **Where**: RTX 4090 at Q4 (18.6 GB, plenty of room for KV cache)
- **Use for**: Code generation, debugging, fast interactive coding tasks
- **Speed**: ~73 tok/s — fastest practical coding model

### Stretch Goal: Qwen3-Coder-Next (Q4 on Node 1 TP=4)

- **Why**: SWE-bench 70.6%, 20 percentage points above the 30B-A3B variant
- **Where**: Node 1 TP=4 at Q4 (~46 GB in 64 GB); tight but workable
- **Use for**: Complex multi-turn agentic coding, SWE-bench-grade tasks
- **Tradeoff**: KV cache limited to ~18 GB total across 4 GPUs; context window constrained in practice

### Future / Offloading: GLM-4.7 or MiMo-V2-Flash

- **When**: For tasks where quality matters more than speed and you can wait 5-15 seconds per response
- **How**: MoE offloading with KTransformers, llama.cpp, or vLLM CPU offload on Node 1

### Skip List

| Model | Reason |
|-------|--------|
| Codestral 22B | MNPL non-production license |
| Command R+ | CC-BY-NC license + 104B dense is excessive |
| StarCoder2-15B | Outdated, no tool calling, 16K context |
| DeepSeek-Coder-V2-Lite | Superseded by Qwen3-Coder-30B-A3B |
| Phi-4 | 16K context too short for agentic coding |
| Llama 4 Scout | Tight VRAM fit, weaker coding than Qwen3 |

---

## Deployment Plan

```
# Primary: Qwen3-32B on RTX 5090 (tool calling agent backbone)
vllm serve Qwen/Qwen3-32B --port 8001 \
  --dtype auto --quantization fp8 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --max-model-len 32768

# Secondary: Qwen3-Coder-30B-A3B on RTX 4090 (fast coding)
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct --port 8002 \
  --dtype auto --quantization awq \
  --enable-auto-tool-choice --tool-call-parser qwen3_xml \
  --max-model-len 65536

# Stretch: Qwen3-Coder-Next on Node 1 TP=4 (complex agentic coding)
vllm serve Qwen/Qwen3-Coder-Next --port 8003 \
  --tensor-parallel-size 4 --quantization awq \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder \
  --max-model-len 32768
```

All three instances serve an OpenAI-compatible API, so agent frameworks (Qwen-Agent, LangChain, custom) can route to the appropriate model based on task complexity.
