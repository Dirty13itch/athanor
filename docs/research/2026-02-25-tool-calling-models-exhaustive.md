# Exhaustive Survey: Tool Calling & Agentic Models (Dec 2025 - Feb 2026)

**Date**: 2026-02-25
**Status**: Research complete
**Purpose**: Identify every model specialized for tool calling, function calling, and agentic workflows released or updated in the last 90 days. Find upgrades from our current Qwen3-32B-AWQ.
**Related**: `2026-02-16-tool-calling-coding-models.md` (previous survey), ADR-005 (inference engine)

---

## Current Baseline

**Model**: Qwen3-32B-AWQ on Node 1 via vLLM TP=4 (4x 5070 Ti, 64 GB total VRAM)
**BFCL V4 score**: 48.71% (FC mode) / 46.78% (Prompt mode) -- per BFCL leaderboard Dec 2025
**Multi-turn score**: 47.87% (FC mode) / 43.25% (Prompt mode)
**Agentic score**: 24.08% (FC mode) / 20.85% (Prompt mode)
**vLLM parser**: `qwen3`

Note: MEMORY.md references "BFCL 68.2" for Qwen3-32B. This likely refers to BFCL V3 or a non-live subset. The V4 leaderboard (which includes multi-turn, web search, memory, and agentic categories) shows 48.71%. The Non-Live AST accuracy alone is 88.77%, which may be the source of the higher figure.

---

## Data Sources

1. **BFCL V4 Leaderboard** — 109 models, data from `github.com/HuanzhiMao/BFCL-Result` snapshot 2025-12-16
2. **HuggingFace model cards** — self-reported benchmarks for models released after Dec 2025
3. **vLLM docs** — tool parser compatibility list
4. **HuggingFace API** — model metadata, file sizes, release dates

Caveat: Self-reported benchmarks (marked with [SR]) have not been independently verified on the BFCL leaderboard.

---

## Hardware Constraints

| Target | GPUs | VRAM | Constraint |
|--------|------|------|------------|
| Node 1 TP=4 | 4x 5070 Ti | 64 GB | Primary inference. Mixed arch (sm_120). AWQ required for models >32B params. |
| Node 1 GPU 4 | 4090 | 24 GB | Dedicated embedding + voice. Not available for main inference. |
| Node 2 GPU 0 | 5090 | 32 GB | Independent vLLM instance. Can run models up to ~30B BF16 or ~60B AWQ. |
| Node 2 GPU 1 | 5060 Ti | 16 GB | ComfyUI. Not available. |

Practical model size limits:
- **TP=4 (64 GB)**: Up to ~120B params in AWQ 4-bit, or ~32B in BF16
- **5090 (32 GB)**: Up to ~60B params in AWQ 4-bit, or ~15B in BF16
- **MoE models**: Total params must fit in VRAM regardless of active params. AWQ of the full model is required.

---

## BFCL V4 Leaderboard: Complete Self-Hostable Rankings

Source: `github.com/HuanzhiMao/BFCL-Result/2025-12-16/score/data_overall.csv` (109 models)

### Top 30 Self-Hostable Models by Overall Accuracy

| Rank | Model | Overall | Non-Live AST | Live Acc | Multi-Turn | Agentic | License | Params | Architecture |
|------|-------|---------|-------------|----------|------------|---------|---------|--------|-------------|
| 4 | **GLM-4.6 (FC thinking)** | **72.38%** | 87.56% | 80.90% | 68.00% | 66.60% | MIT | ~266B MoE | Glm4MoeForCausalLM |
| 11 | Kimi-K2-Instruct (FC) | 59.06% | 81.60% | 78.68% | 50.63% | 47.77% | modified-MIT | ~1T MoE | DeepseekV3 arch |
| 14 | DeepSeek-V3.2-Exp (Prompt+Think) | 56.73% | 85.52% | 76.02% | 44.88% | 51.04% | MIT | ~671B MoE | API-only |
| 18 | **xLAM-2-32b-fc-r (FC)** | **54.66%** | 89.60% | 75.50% | 69.50% | 23.18% | CC-BY-NC-4.0 | 32B dense | Qwen2ForCausalLM |
| 22 | xLAM-2-70b-fc-r (FC) | 53.07% | 88.44% | 72.17% | 77.38% | 14.70% | CC-BY-NC-4.0 | 70B dense | LlamaForCausalLM |
| 23 | Qwen3-235B-A22B (Prompt) | 52.15% | 90.33% | 78.68% | 44.62% | 34.93% | Apache-2.0 | 235B MoE / 22B active | Qwen2MoeForCausalLM |
| 25 | Nanbeige4-3B-Thinking (FC) | 51.40% | 81.58% | 79.42% | 51.12% | 29.14% | Apache-2.0 | 3B dense | LlamaForCausalLM |
| 29 | **Qwen3-32B (FC)** | **48.71%** | 88.77% | 82.01% | 47.87% | 24.08% | Apache-2.0 | 32B dense | Qwen2ForCausalLM |
| 31 | Qwen3-235B-A22B (FC) | 47.99% | 37.40% | 68.91% | 45.38% | 38.94% | Apache-2.0 | 235B MoE | Qwen2MoeForCausalLM |
| 32 | Nanbeige3.5-Pro-Thinking (FC) | 47.68% | 38.35% | 69.95% | 40.00% | 43.58% | Apache-2.0 | Unknown | LlamaForCausalLM |
| 34 | xLAM-2-8b-fc-r (FC) | 46.68% | 84.58% | 67.95% | 70.00% | 10.24% | CC-BY-NC-4.0 | 8B dense | LlamaForCausalLM |
| 36 | **BitAgent-Bounty-8B** | **46.23%** | 81.60% | 93.12% | 62.38% | 0.75% | Apache-2.0 | 8B dense | LlamaForCausalLM |
| 37 | **Arch-Agent-32B** | **45.37%** | 88.92% | 80.68% | 54.25% | 9.81% | katanemo-research | 33B dense | Qwen2ForCausalLM |
| 39 | Qwen3-8B (FC) | 42.57% | 87.58% | 80.53% | 41.75% | 13.31% | Apache-2.0 | 8B dense | Qwen2ForCausalLM |
| 40 | **ToolACE-2-8B (FC)** | **42.44%** | 87.10% | 77.42% | 38.38% | 13.50% | Apache-2.0 | 8B dense | LlamaForCausalLM |
| 41 | Qwen3-30B-A3B (FC) | 41.39% | 85.77% | 77.94% | 30.00% | 20.07% | Apache-2.0 | 30B MoE / 3B active | Qwen2MoeForCausalLM |
| 42 | xLAM-2-3b-fc-r (FC) | 41.22% | 82.96% | 62.92% | 58.38% | 6.95% | CC-BY-NC-4.0 | 3B dense | Qwen2ForCausalLM |
| 43 | Qwen3-14B (FC) | 41.03% | 84.94% | 80.01% | 34.75% | 14.78% | Apache-2.0 | 14B dense | Qwen2ForCausalLM |
| 46 | mistral-large-2411 (FC) | 38.37% | 84.65% | 81.87% | 14.12% | 26.47% | Proprietary | ~123B dense | API-only |
| 50 | Llama-4-Maverick (FC) | 37.29% | 88.65% | 73.65% | 20.25% | 23.46% | Meta Llama 4 | 400B MoE / 17B active | LlamaForCausalLM |
| 55 | Arch-Agent-3B | 35.36% | 86.67% | 72.91% | 34.88% | 3.69% | katanemo-research | 3B dense | Qwen2ForCausalLM |
| 60 | Arch-Agent-1.5B | 32.14% | 82.67% | 67.73% | 26.62% | 4.09% | katanemo-research | 1.5B dense | Qwen2ForCausalLM |
| 62 | Llama-3.3-70B-Instruct (FC) | 31.90% | 88.02% | 76.61% | 21.50% | 9.09% | Meta Llama 3 | 70B dense | LlamaForCausalLM |
| 64 | Hammer2.1-7b (FC) | 31.67% | 85.50% | 69.50% | 23.87% | 0.00% | CC-BY-NC-4.0 | 7B dense | Qwen2ForCausalLM |
| 68 | Hammer2.1-3b (FC) | 29.71% | 84.96% | 70.54% | 16.50% | 1.51% | qwen-research | 3B dense | Qwen2ForCausalLM |
| 74 | CoALM-70B | 27.99% | 83.44% | 67.28% | 10.62% | 2.90% | CC-BY-NC-4.0 | 70B dense | LlamaForCausalLM |
| 81 | Granite-3.1-8B (FC) | 27.10% | 78.33% | 60.33% | 7.50% | 7.45% | Apache-2.0 | 8B dense | GraniteForCausalLM |
| 83 | Granite-3.2-8B (FC) | 26.87% | 79.77% | 60.33% | 7.38% | 6.49% | Apache-2.0 | 8B dense | GraniteForCausalLM |

### Multi-Turn Champions (Critical for Agents)

Multi-turn performance matters most for agentic workflows with extended tool-call chains.

| Rank | Model | Multi-Turn | Overall | Notes |
|------|-------|-----------|---------|-------|
| 1 | xLAM-2-70b-fc-r | **77.38%** | 53.07% | Best multi-turn of ANY model |
| 2 | xLAM-2-8b-fc-r | **70.00%** | 46.68% | Best multi-turn at 8B scale |
| 3 | xLAM-2-32b-fc-r | **69.50%** | 54.66% | Best multi-turn at 32B scale |
| 4 | Claude-Opus-4-5 (FC) | 68.38% | 77.47% | Proprietary |
| 5 | GLM-4.6 (FC thinking) | **68.00%** | 72.38% | Best open-source overall |
| 6 | Gemini-3-Pro (FC) | 63.12% | 68.14% | Proprietary |
| 7 | BitAgent-Bounty-8B | 62.38% | 46.23% | But 0% agentic score |
| 12 | xLAM-2-3b-fc-r | 58.38% | 41.22% | Best at 3B scale |
| 13 | Arch-Agent-32B | 54.25% | 45.37% | Decent multi-turn |
| 18 | **Qwen3-32B (FC)** | **47.87%** | 48.71% | Our current model |

### Agentic Task Champions (Web Search + Memory)

| Rank | Model | Agentic | Overall | Notes |
|------|-------|---------|---------|-------|
| 1 | Claude-Opus-4-5 (FC) | 79.13% | 77.47% | Proprietary |
| 7 | **GLM-4.6 (FC thinking)** | **66.60%** | 72.38% | Best open-source |
| 8 | GPT-5-mini (FC) | 63.15% | 55.46% | Proprietary |
| 22 | Kimi-K2-Instruct (FC) | 47.77% | 59.06% | modified-MIT |
| 36 | **Qwen3-32B (FC)** | **24.08%** | 48.71% | Our current model |
| 38 | xLAM-2-32b-fc-r (FC) | 23.18% | 54.66% | Weak agentic despite good multi-turn |

---

## Models Released Dec 2025 - Feb 2026

### Qwen3.5 Family (Released Feb 16-25, 2026) -- BRAND NEW

The Qwen3.5 family landed this week. All models are multimodal (text + vision + video) with native tool calling. Architecture uses a novel hybrid of Gated DeltaNet + Gated Attention, a departure from the standard Transformer.

| Model | Total Params | Active Params | BFCL-V4 [SR] | TAU2-Bench [SR] | SWE-bench Verified | Context | License |
|-------|-------------|---------------|------------|-------------|------------------|---------|---------|
| **Qwen3.5-397B-A17B** | 397B | 17B | **72.9%** | **86.7%** | 76.4% | 262K | Apache-2.0 |
| **Qwen3.5-122B-A10B** | 122B | 10B | **72.2%** | 79.5% | N/A | 262K | Apache-2.0 |
| **Qwen3.5-27B** | 27B | 27B (dense) | **68.5%** | **79.0%** | 72.4% | 262K | Apache-2.0 |
| **Qwen3.5-35B-A3B** | 35B | 3B | 67.3% | **81.2%** | 69.2% | 262K | Apache-2.0 |

[SR] = Self-reported, not yet on BFCL leaderboard.

Key details:
- **Architecture**: `Qwen3_5ForConditionalGeneration` (dense) / `Qwen3_5MoeForConditionalGeneration` (MoE)
- **vLLM tool parser**: `qwen3_coder` (confirmed in model card)
- **vLLM reasoning parser**: `qwen3`
- **Thinking mode**: Built-in, toggleable per-request via `enable_thinking: false`
- **Parallel tool calls**: Yes (inherited from Qwen3 architecture)
- **AWQ quantizations**: Appearing today (Feb 25) from QuantTrio and cyankiwi
  - `QuantTrio/Qwen3.5-122B-A10B-AWQ` -- just uploaded
  - `QuantTrio/Qwen3.5-35B-A3B-AWQ` -- just uploaded
  - `cyankiwi/Qwen3.5-27B-AWQ-BF16-INT4` -- 431 downloads

VRAM estimates (AWQ 4-bit):
- Qwen3.5-397B-A17B AWQ: ~200 GB -- **does not fit** our hardware
- Qwen3.5-122B-A10B AWQ: ~65 GB -- **tight fit** on TP=4 (64 GB), may need reduced context
- Qwen3.5-35B-A3B AWQ: ~18 GB -- **fits easily** on single 5090 (32 GB)
- Qwen3.5-27B AWQ: ~14 GB -- **fits easily** on single 5090 (32 GB)

HuggingFace URLs:
- `https://huggingface.co/Qwen/Qwen3.5-397B-A17B`
- `https://huggingface.co/Qwen/Qwen3.5-122B-A10B`
- `https://huggingface.co/Qwen/Qwen3.5-27B`
- `https://huggingface.co/Qwen/Qwen3.5-35B-A3B`
- FP8 variants: `Qwen/Qwen3.5-27B-FP8`, `Qwen/Qwen3.5-122B-A10B-FP8`, `Qwen/Qwen3.5-35B-A3B-FP8`

---

### GLM-4.7 (Released Dec 22, 2025) and GLM-4.7-Flash (Released Jan 19, 2026)

Major upgrade to the #4 BFCL model (GLM-4.6). GLM-4.7 shows massive improvements especially on agentic tasks.

| Model | TAU2-Bench [SR] | SWE-bench Verified | HLE w/ Tools | BrowseComp | License | AWQ Size |
|-------|-------------|------------------|-------------|------------|---------|----------|
| **GLM-4.7** | **87.4%** | 73.8% | 42.8% | 52.0% | MIT | ~194 GB |
| GLM-4.7-Flash | N/A | N/A | N/A | N/A | MIT | ~20 GB |
| GLM-4.6 (BFCL #4) | 75.2% (old) | 68.0% | 30.4% | 45.1% | MIT | ~197 GB |

[SR] = Self-reported from model card, comparing to previous GLM-4.6.

Key details:
- **Architecture**: `Glm4MoeForCausalLM` (MoE), param count undisclosed but AWQ ~194 GB implies ~776B total params
- **GLM-4.7-Flash**: `Glm4MoeLiteForCausalLM`, ~81B total from AWQ size (~20 GB AWQ-4bit)
- **vLLM tool parser**: `glm47` (confirmed in model card)
- **vLLM reasoning parser**: `glm45` (docs reference)
- **Tool calling**: Interleaved thinking with tool use. Thinks before every tool call.
- **Parallel tool calls**: Supported
- **AWQ quantizations available**:
  - `QuantTrio/GLM-4.7-AWQ` — 9,571 downloads
  - `QuantTrio/GLM-4.6-AWQ` — 6,306 downloads
  - `cyankiwi/GLM-4.7-Flash-AWQ-4bit` — 238,091 downloads (very popular)

VRAM estimates (AWQ 4-bit):
- GLM-4.7 AWQ: ~194 GB -- **does not fit** (even TP=4 is only 64 GB)
- GLM-4.7-Flash AWQ: ~20 GB -- **fits on single 5090** or TP=2 on 5070 Ti
- GLM-4.6 AWQ: ~197 GB -- **does not fit**

HuggingFace URLs:
- `https://huggingface.co/zai-org/GLM-4.7`
- `https://huggingface.co/zai-org/GLM-4.7-Flash`
- `https://huggingface.co/zai-org/GLM-4.7-FP8`

---

### Qwen3-Coder-Next (Released Jan 30, 2026)

Coding-focused MoE model with strong tool calling.

| Metric | Value |
|--------|-------|
| Total params | 80B |
| Active params | 3B |
| Architecture | `Qwen3NextForCausalLM` (Hybrid DeltaNet + MoE, 512 experts) |
| Context length | 262,144 |
| License | Apache-2.0 |
| Tool calling | Yes, native |
| vLLM parser | `qwen3_coder` (likely, shares Qwen3 format) |
| Downloads | 549,875 |
| AWQ VRAM (est.) | ~40 GB |

HuggingFace: `https://huggingface.co/Qwen/Qwen3-Coder-Next`

---

### xLAM-2 Family (Released ~April 2025, on BFCL Dec 2025)

Salesforce's Large Action Models, specifically designed for function calling and multi-turn agent tasks. These are the multi-turn champions.

| Model | BFCL Overall | Multi-Turn | Agentic | Base Model | License | VRAM (BF16) |
|-------|-------------|-----------|---------|-----------|---------|-------------|
| xLAM-2-70b-fc-r | 53.07% | **77.38%** | 14.70% | Llama-3.1-70B | CC-BY-NC-4.0 | ~140 GB |
| **xLAM-2-32b-fc-r** | **54.66%** | **69.50%** | 23.18% | Qwen2.5-32B | CC-BY-NC-4.0 | ~64 GB |
| xLAM-2-8b-fc-r | 46.68% | **70.00%** | 10.24% | Llama-3.1-8B | CC-BY-NC-4.0 | ~16 GB |
| xLAM-2-3b-fc-r | 41.22% | 58.38% | 6.95% | Qwen2.5-3B | CC-BY-NC-4.0 | ~6 GB |
| xLAM-2-1b-fc-r | 30.44% | 36.00% | 1.94% | Qwen2.5-1B | CC-BY-NC-4.0 | ~2 GB |

Key details:
- **vLLM tool parser**: `xlam` (custom plugin: `xlam_tool_call_parser.py`, download from HF)
- **Parallel tool calls**: Yes
- **Training data**: APIGen-MT-5k + xlam-function-calling-60k
- **AWQ available**: `emelaz/xLAM-2-32b-fc-r-AWQ` (community quant)

HuggingFace URLs:
- `https://huggingface.co/Salesforce/xLAM-2-32b-fc-r`
- `https://huggingface.co/Salesforce/Llama-xLAM-2-70b-fc-r`
- `https://huggingface.co/Salesforce/Llama-xLAM-2-8b-fc-r`
- `https://huggingface.co/Salesforce/xLAM-2-3b-fc-r`

---

### Arch-Agent Family (Released ~June 2025, on BFCL Dec 2025)

Katanemo's agentic models built on Qwen2.5-Coder.

| Model | BFCL Overall | Multi-Turn | Base Model | License |
|-------|-------------|-----------|-----------|---------|
| Arch-Agent-32B | 45.37% | 54.25% | Qwen2.5-Coder-32B | katanemo-research |
| Arch-Agent-3B | 35.36% | 34.88% | Qwen2.5-Coder-3B | katanemo-research |
| Arch-Agent-1.5B | 32.14% | 26.62% | Qwen2.5-Coder-1.5B | katanemo-research |

Key details:
- **Tool calling format**: XML-wrapped JSON (`<tool_call>{...}</tool_call>`)
- **64K context** with YaRN scaling
- **vLLM parser**: Not built-in; requires custom template
- **License restriction**: katanemo-research (not Apache/MIT)

HuggingFace: `https://huggingface.co/katanemo/Arch-Agent-32B`

---

### ToolACE-2-8B (Released ~Sept 2024, on BFCL Dec 2025)

Huawei Noah & USTC's dedicated tool calling model.

| Metric | Value |
|--------|-------|
| BFCL Overall | 42.44% |
| Multi-Turn | 38.38% |
| Base model | Llama-3.1-8B-Instruct |
| License | Apache-2.0 |
| Tool format | Python-style: `[func_name(param=value)]` |
| vLLM parser | No built-in; custom template required |

HuggingFace: `https://huggingface.co/Team-ACE/ToolACE-2-8B`

---

### Hammer2.1 Family (Released Dec 2024, on BFCL Dec 2025)

MadeAgents' tool calling models built on Qwen2.5-Coder.

| Model | BFCL Overall | Multi-Turn | License |
|-------|-------------|-----------|---------|
| Hammer2.1-7b | 31.67% | 23.87% | CC-BY-NC-4.0 |
| Hammer2.1-3b | 29.71% | 16.50% | qwen-research |
| Hammer2.1-1.5b | 27.88% | 15.62% | CC-BY-NC-4.0 |
| Hammer2.1-0.5b | 21.22% | 2.88% | CC-BY-NC-4.0 |

HuggingFace: `https://huggingface.co/MadeAgents/Hammer2.1-7b`

---

### Other Notable Models on BFCL

| Model | BFCL | Multi-Turn | Notes |
|-------|------|-----------|-------|
| BitAgent-Bounty-8B | 46.23% | 62.38% | Bittensor ecosystem. 93% Live Acc (suspiciously high). 0% agentic. Apache-2.0 |
| Nanbeige4-3B-Thinking | 51.40% | 51.12% | Tiny model, strong thinking. Apache-2.0. Released Nov 2025. |
| Nanbeige3.5-Pro-Thinking | 47.68% | 40.00% | Apache-2.0. Unknown param count. |
| CoALM-70B | 27.99% | 10.62% | UIUC research. Based on Llama-3.3-70B. CC-BY-NC-4.0 |
| CoALM-8B | 26.81% | 8.00% | Same series, 8B variant |
| RZN-T | 22.25% | 2.88% | Phronetic AI. Apache-2.0 |
| Granite-3.2-8B | 26.87% | 7.38% | IBM. Apache-2.0. Granite tool parser in vLLM |
| Granite-4.0-350m | 18.98% | 2.50% | Tiny. IBM. Apache-2.0 |
| Phi-4 | 28.79% | 3.88% | Microsoft. MIT. Not tool-calling focused |
| Falcon3-10B | 27.01% | 6.50% | TII UAE. falcon-llm-license |

---

### Models NOT on BFCL but Worth Noting

| Model | Released | Params | Notes | Status |
|-------|---------|--------|-------|--------|
| Kimi-K2-Instruct | Jul 2025 | ~1T MoE | On BFCL at 59.06%. Too large for self-hosting. | API only |
| MeetKai Functionary v3.2 | 2024 | 8B | No new versions since. Older format. | Stale |
| NexusRaven V2 | Dec 2023 | 13B | No new versions. | Abandoned |
| Hermes-3-Llama-3.1-8B | 2024 | 8B | Hermes parser in vLLM. No major updates. | Mature |
| DeepSeek-V3.2 | May 2025 | ~671B MoE | On BFCL at 56.73%. Too large for self-hosting. | API only |

---

## vLLM Tool Parser Compatibility

Complete list of built-in tool parsers as of vLLM latest:

| Parser Name | Supported Models | Notes |
|-------------|-----------------|-------|
| `hermes` | NousResearch Hermes, compatible models | Widely used format |
| `llama3_json` | Llama 3.x models | JSON format |
| `mistral` | Mistral models | Proprietary format |
| `qwen3` | Qwen3 family | Native support |
| `qwen3_xml` | Qwen3-Coder, Qwen3.5 | XML-based tool calls |
| `qwen3_coder` | Qwen3-Coder, Qwen3.5 | **Recommended for Qwen3.5** |
| `xlam` | Salesforce xLAM-2 family | Requires plugin download |
| `internlm` | InternLM models | |
| `jamba` | Jamba models | |
| `deepseek_v3` | DeepSeek V3 | |
| `deepseek_v31` | DeepSeek V3.1 | |
| `kimi_k2` | Kimi K2 | |
| `glm45` | GLM-4.5, GLM-4.6 | |
| `glm47` | **GLM-4.7, GLM-4.7-Flash** | New |
| `minimax_m1` | MiniMax models | |
| `hunyuan_a13b` | Hunyuan | |
| `longcat` | LongCat-Flash | |
| `functiongemma` | FunctionGemma | |
| `olmo3` | Olmo 3 | |
| `gigachat3` | Gigachat 3 | |
| `pythonic` | Python-style tool calls | |
| `openai` | OpenAI OSS format | |
| (custom plugin) | Any model | User-defined parser |

---

## Comparative Analysis: Upgrade Candidates for Athanor

### Tier 1: Drop-in Replacements (Fits Current TP=4 Setup)

These models can replace Qwen3-32B-AWQ on Node 1's 4x 5070 Ti (64 GB).

| Model | BFCL | Multi-Turn | Agentic | TAU2 | AWQ VRAM | vLLM Parser | License | Improvement vs Current |
|-------|------|-----------|---------|------|----------|------------|---------|----------------------|
| **Qwen3.5-27B AWQ** | 68.5% [SR] | N/A | N/A | 79.0% [SR] | ~14 GB | `qwen3_coder` | Apache-2.0 | +19.8 pt BFCL |
| **Qwen3.5-35B-A3B AWQ** | 67.3% [SR] | N/A | N/A | 81.2% [SR] | ~18 GB | `qwen3_coder` | Apache-2.0 | +18.6 pt BFCL |
| **xLAM-2-32b-fc-r AWQ** | 54.66% | 69.50% | 23.18% | N/A | ~17 GB | `xlam` | CC-BY-NC-4.0 | +6.0 pt BFCL, +21.6 pt multi-turn |
| Qwen3-Coder-Next AWQ | N/A [SR] | N/A | N/A | N/A | ~40 GB | `qwen3_coder` | Apache-2.0 | Unknown |
| Qwen3.5-122B-A10B AWQ | 72.2% [SR] | N/A | N/A | 79.5% [SR] | ~65 GB | `qwen3_coder` | Apache-2.0 | +23.5 pt BFCL (may not fit) |

### Tier 2: Node 2 (5090, 32 GB) Deployment Options

These can run as a secondary or replacement on Node 2.

| Model | BFCL | Multi-Turn | AWQ VRAM | vLLM Parser | License |
|-------|------|-----------|----------|------------|---------|
| **GLM-4.7-Flash AWQ** | Unknown | Unknown | ~20 GB | `glm47` | MIT |
| **Qwen3.5-27B AWQ** | 68.5% [SR] | N/A | ~14 GB | `qwen3_coder` | Apache-2.0 |
| **Qwen3.5-35B-A3B AWQ** | 67.3% [SR] | N/A | ~18 GB | `qwen3_coder` | Apache-2.0 |
| xLAM-2-8b-fc-r | 46.68% | 70.00% | ~16 GB BF16 | `xlam` | CC-BY-NC-4.0 |

### Tier 3: Too Large for Current Hardware

| Model | BFCL | TAU2 | AWQ VRAM | Notes |
|-------|------|------|----------|-------|
| GLM-4.6 AWQ | 72.38% | 75.2% | ~197 GB | Best BFCL open-source but needs 8x H100 |
| GLM-4.7 AWQ | Unknown (>72.38%) | 87.4% | ~194 GB | Likely BFCL champion but massive |
| Qwen3.5-397B-A17B AWQ | 72.9% [SR] | 86.7% [SR] | ~200 GB | Way too large |
| xLAM-2-70b-fc-r AWQ | 53.07% | N/A | ~35 GB | Could fit TP=4 if AWQ'd |
| Kimi-K2-Instruct | 59.06% | N/A | ~500+ GB | API only |

---

## Recommendation

### Top Pick: Qwen3.5-27B AWQ (or FP8)

**Why**: BFCL-V4 68.5% (self-reported) vs our current 48.71% -- a potential 20-point upgrade. Dense 27B means AWQ fits in ~14 GB VRAM, leaving ample room for KV cache. Native tool calling with the `qwen3_coder` vLLM parser. Apache-2.0 license. Multimodal bonus (vision + video). Released 2 days ago.

**Risk**: Self-reported scores. The actual BFCL V4 leaderboard evaluation may differ. The architecture (`Qwen3_5ForConditionalGeneration`) is brand new and vLLM support may have rough edges. Requires latest vLLM with Qwen3.5 support.

**Action**: Wait 1-2 weeks for community validation, then test.

### Runner-Up: xLAM-2-32b-fc-r AWQ

**Why**: Independently verified BFCL 54.66% (+6 pts) with exceptional multi-turn 69.50% (+22 pts). Multi-turn is arguably more important than overall score for agentic workflows. Based on Qwen2.5-32B so very similar VRAM profile to what we run now.

**Risk**: CC-BY-NC-4.0 license (non-commercial). Weak agentic score (23.18%). No thinking mode.

**Action**: Can test immediately as a multi-turn specialist.

### Dark Horse: GLM-4.7-Flash AWQ

**Why**: If GLM-4.7 inherits even a fraction of GLM-4.6's BFCL 72.38%, the Flash variant at ~20 GB AWQ could be transformative. GLM-4.7 reports TAU2-Bench 87.4% which is the highest of any model tested. MIT license. Built-in thinking with tool use.

**Risk**: No independent BFCL scores for 4.7 or 4.7-Flash. Unknown how much capability the Flash variant loses. Requires `glm47` parser which is newer.

**Action**: Test GLM-4.7-Flash AWQ on Node 2's 5090. Compare against Qwen3-32B on real agent tasks.

### Watch List

1. **Qwen3.5-122B-A10B AWQ** -- If the AWQ quant lands at ~60 GB, it could fit TP=4. BFCL 72.2% [SR] would be a massive upgrade. Monitor quant quality.
2. **GLM-4.7 FP8** -- At ~390 GB FP8 it doesn't fit, but if a 4-bit GPTQ appears...
3. **xLAM-3 family** -- Salesforce's next generation. No release date known.

---

## Open Questions

1. **Qwen3.5 vLLM compatibility**: Does the new `Qwen3_5ForConditionalGeneration` architecture work with our NGC-based vLLM container? Almost certainly needs a container upgrade.
2. **Qwen3.5 AWQ + Blackwell**: Will AWQ Marlin kernels work on sm_120 for Qwen3.5? Same gotcha as Qwen3-32B -- need `--quantization awq` flag.
3. **GLM-4.7-Flash benchmarks**: No public BFCL scores yet. Community benchmarks needed.
4. **MoE routing overhead**: For MoE models, what's the actual throughput impact of expert routing vs dense models at the same active param count?
5. **BFCL V4 vs V3**: The score gap between BFCL versions makes cross-version comparison unreliable. Should we retest our current Qwen3-32B-AWQ on V4 to establish a true baseline?

---

## Sources

- BFCL V4 Leaderboard Data: `https://github.com/HuanzhiMao/BFCL-Result/tree/main/2025-12-16`
- BFCL Website: `https://gorilla.cs.berkeley.edu/leaderboard.html`
- Qwen3.5 Model Card: `https://huggingface.co/Qwen/Qwen3.5-27B`
- Qwen3.5 MoE Model Card: `https://huggingface.co/Qwen/Qwen3.5-397B-A17B`
- Qwen3.5-35B-A3B Model Card: `https://huggingface.co/Qwen/Qwen3.5-35B-A3B`
- Qwen3.5-122B-A10B Model Card: `https://huggingface.co/Qwen/Qwen3.5-122B-A10B`
- GLM-4.7 Model Card: `https://huggingface.co/zai-org/GLM-4.7`
- GLM-4.7-Flash: `https://huggingface.co/zai-org/GLM-4.7-Flash`
- GLM-4.6 Model Card: `https://huggingface.co/zai-org/GLM-4.6`
- xLAM-2 Model Card: `https://huggingface.co/Salesforce/xLAM-2-32b-fc-r`
- xLAM-2 Paper: `arXiv:2504.03601`
- Arch-Agent-32B: `https://huggingface.co/katanemo/Arch-Agent-32B`
- ToolACE-2: `https://huggingface.co/Team-ACE/ToolACE-2-8B`
- Hammer2.1: `https://huggingface.co/MadeAgents/Hammer2.1-7b`
- Kimi-K2: `https://huggingface.co/moonshotai/Kimi-K2-Instruct`
- Qwen3-Coder-Next: `https://huggingface.co/Qwen/Qwen3-Coder-Next`
- vLLM Tool Calling Docs: `https://docs.vllm.ai/en/latest/features/tool_calling.html`
- Nanbeige4: `https://huggingface.co/Nanbeige/Nanbeige4-3B-Thinking-2511`
- BitAgent: `https://huggingface.co/BitAgent/BitAgent-Bounty-8B`
- CoALM: `https://huggingface.co/uiuc-convai/CoALM-70B`
- GLM-4.7 AWQ: `https://huggingface.co/QuantTrio/GLM-4.7-AWQ`
- GLM-4.7-Flash AWQ: `https://huggingface.co/cyankiwi/GLM-4.7-Flash-AWQ-4bit`
- Qwen3.5 AWQ: `https://huggingface.co/QuantTrio/Qwen3.5-122B-A10B-AWQ`
