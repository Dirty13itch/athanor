# AI Model Landscape Survey -- Q1 2026

**Date**: 2026-03-14
**Status**: Research complete
**Purpose**: Comprehensive survey of the AI model landscape as of March 2026, covering LLMs, coding models, embedding models, and inference engines. Focused on what matters for a self-hosted system with 5070 Ti (16GB), 5090 (32GB), 5060 Ti (16GB), and 4090 (24GB) GPUs.
**Supplements**: `2026-03-14-qwen35-model-landscape.md`, `2026-03-13-coding-models-march-update.md`, `2026-02-25-embedding-models-exhaustive.md`, `2026-03-14-inference-backends.md`

---

## Executive Summary

The Q1 2026 AI model landscape has seen unprecedented release velocity -- 255+ model releases tracked by LLM Stats in the first quarter alone. Key developments relevant to Athanor:

1. **No Qwen4 yet.** Qwen3.5 is the latest. The Qwen team suffered a major leadership exodus in early March 2026 (lead researcher + 3 senior figures departed). Future Qwen development is uncertain.
2. **vLLM v0.17.1 is current stable** (March 11, 2026). Significant upgrade from our nightly 0.16.1rc1.dev32 -- adds FlashAttention 4, full Qwen3.5 GDN support, MTP speculative decoding, and a `--performance-mode` flag.
3. **Coding model landscape has exploded.** MiniMax M2.5 (80.2% SWE-bench), GLM-5 (77.8%), and Kimi K2.5 (76.8%) are the new leaders -- but all require 96-256GB+ VRAM. For Athanor's hardware, Qwen3.5-35B-A3B-AWQ remains the best fit.
4. **Qwen3-Embedding-0.6B is still best-in-class** for sub-1B Apache 2.0 embedding models. No upgrade needed.
5. **GPT-OSS-120B** (OpenAI, Apache 2.0, Aug 2025) is notable -- 120B MoE with 5.1B active, fits single 80GB GPU. Too large for any single Athanor GPU but worth monitoring for TP=4 deployment.

---

## 1. Latest Qwen Models

### Current State: Qwen3.5 is Latest (No Qwen4)

As of March 14, 2026, **Qwen4 has not been released or announced.** Prediction markets (Manifold) are tracking a possible release before July 2026, but this is highly uncertain given the team upheaval.

#### Qwen3.5 Family (Released Feb 16 + Mar 1, 2026)

| Model | Type | Active Params | Total Params | VRAM AWQ 4-bit | Release |
|-------|------|---------------|--------------|----------------|---------|
| Qwen3.5-0.8B | Dense | 0.8B | 0.8B | ~0.5 GB | Mar 1, 2026 |
| Qwen3.5-2B | Dense | 2B | 2B | ~1.2 GB | Mar 1, 2026 |
| Qwen3.5-4B | Dense | 4B | 4B | ~2.5 GB | Mar 1, 2026 |
| Qwen3.5-9B | Dense | 9B | 9B | ~5 GB | Mar 1, 2026 |
| **Qwen3.5-27B** | Dense | 27B | 27B | ~14 GB | Feb 16, 2026 |
| **Qwen3.5-35B-A3B** | MoE | 3B | 35B | ~21 GB | Feb 16, 2026 |
| Qwen3.5-122B-A10B | MoE | 10B | 122B | ~74 GB | Feb 16, 2026 |
| Qwen3.5-397B-A17B | MoE | 17B | 397B | ~200 GB+ | Feb 16, 2026 |

**Architecture innovations in Qwen3.5:**
- Gated Delta Networks (GDN) hybrid attention -- linear attention layers with O(1) memory complexity for long context, interspersed with standard attention
- Native multimodal -- early fusion of text, image, and video tokens (even in small models)
- 262K native context (extensible to 1M+)
- 201 languages (up from 119 in Qwen3)
- Apache 2.0 license on all models

**Small model series (Mar 1) -- key benchmark:**
- Qwen3.5-9B in thinking mode outperforms Qwen3-30B on most benchmarks (GPQA Diamond 81.7 vs 77.2)
- Qwen3.5-9B LiveCodeBench: 65.6 (not competitive for a coding slot, but strong for utility)
- Qwen3.5-4B: MMMU-Pro 66.3 (vision), practical from 8GB VRAM

#### Critical: Qwen Team Leadership Crisis

On March 3-4, 2026, the Qwen team suffered a major leadership exodus:

- **Lin Junyang** (Tech Lead, public face of Qwen) -- resigned March 3, approved by CEO March 5
- **Yu Bowen** (Head of Post-Training/RLHF) -- departed same day
- **Hui Binyuan** (Lead of Qwen-Coder) -- departed to Meta in January 2026
- **Kaixin Li** (core contributor to Qwen3.5/VL/Coder) -- departed
- Multiple junior researchers departed on the same day

The trigger was an internal restructuring where a new researcher from Google's Gemini team was placed in charge. Alibaba shares dropped 5.3% intraday.

**Impact assessment for Athanor:** Qwen3.5 is already released and will continue to be supported by the community. But future Qwen4 development is genuinely uncertain. This strengthens the case for monitoring alternative model families (GLM, Kimi, DeepSeek, Mistral) as potential replacements.

### Other Qwen-Family Models

| Model | Type | Notes |
|-------|------|-------|
| Qwen3-Coder-Next-80B-A3B | Coding MoE | Released Feb 2026. 70.6% SWE-bench. AWQ ~46GB -- too large for single Athanor GPU. |
| Qwen3-Coder-480B-A35B | Coding MoE | Flagship coder. Way too large for local deployment. |
| Qwen3-VL-Embedding-2B | Multimodal Embed | Jan 2026. Unified image+text search. Apache 2.0. 1024-dim Matryoshka. |
| Qwen3-VL-Reranker-2B | Multimodal Rerank | Jan 2026. Companion to VL-Embedding. |

---

## 2. Latest vLLM Version

### Current: v0.17.1 (March 11, 2026)

| Version | Release Date | Status |
|---------|-------------|--------|
| **v0.17.1** | March 11, 2026 | **Current stable** |
| v0.17.0 | March 6, 2026 | Previous stable |
| v0.16.0 | ~Jan 2026 | What we have installed on FOUNDRY (stable) |
| 0.16.1rc1.dev32 | Nightly | What we run as `athanor/vllm:qwen35` |

#### Key Features in v0.17.1 Relevant to Athanor

1. **FlashAttention 4** -- Default attention backend on Blackwell sm_120+ GPUs. Improves prefill throughput and speculative decode performance. No configuration required. This is a significant performance gain for our 5070 Ti and 5090 GPUs.

2. **Full Qwen3.5 GDN Support** -- Native support for Gated Delta Networks including FP8 quantization, MTP speculative decoding, and reasoning parser support. No more needing custom patches (`fix-vllm-qwen35.py`).

3. **`--performance-mode` Flag** -- New `{balanced, interactivity, throughput}` modes simplify tuning. Potentially better than our manual `--enforce-eager` + `--max-num-seqs` tuning.

4. **Pipeline Parallelism** -- Full async scheduling + PP support. 30.8% E2E throughput improvement and 31.8% TPOT improvement.

5. **WebSocket Realtime API** -- Streaming audio interactions. Relevant for future voice agent work.

6. **FP4 Kernel Optimization** -- 65% faster FP4 quantization on Blackwell using 256-bit loads. ~4% E2E throughput improvement.

7. **New `qwen35_coder` Tool Parser** -- PR #35347 merged. Fixes JSON malformation issues vs older `qwen3_coder` parser. Worth evaluating vs our current `qwen3_xml`.

8. **New Architectures** -- GLM-5, MiniMax-M2, Step-3.5-Flash, and many more now supported natively.

#### Upgrade Assessment

**The upgrade from our nightly 0.16.1rc1.dev32 to v0.17.1 stable is strongly recommended.** Key benefits:
- FlashAttention 4 on Blackwell = free performance
- Native Qwen3.5 GDN support = remove custom patches
- Better stability (stable vs nightly)
- FP4 optimization for future model deployments
- `--performance-mode` for simpler tuning

**Risk:** Need to rebuild `athanor/vllm:qwen35` Docker image from v0.17.1 base. Test on DEV/WORKSHOP first.

---

## 3. Best Open-Source Coding Models

### The New Frontier (Too Large for Athanor)

| Model | SWE-bench V | Architecture | Active Params | Total Params | Min VRAM | License |
|-------|-------------|-------------|---------------|--------------|----------|---------|
| **MiniMax M2.5** | **80.2%** | MoE 256E/8A | 10B | 229B | 96 GB (Q2) | Apache 2.0 |
| **GLM-5** | **77.8%** | MoE | 40B | 744B | 176 GB (Q1.8) | MIT |
| **Kimi K2.5** | **76.8%** | MoE | 32B | 1T | 240 GB (Q1.8) | Modified MIT |
| IQuest-Coder-V1-40B | 76.2% | Dense | 40B | 40B | ~40 GB (FP8) | Custom |
| GPT-OSS-120B | ~75% est. | MoE 128E | 5.1B | 120B | 80 GB (MXFP4) | Apache 2.0 |
| Step-3.5-Flash | 74.4% | MoE 288E/8A | 11B | 196B | ~98 GB (FP8) | Apache 2.0 |

**None of these fit in Athanor's VRAM without CPU offloading.** The M2.5 would need 96GB minimum (Q2) -- our TP=4 is 64GB. GLM-5 and Kimi K2.5 are even larger.

However, **GPT-OSS-120B** deserves special mention:
- 120B total, only 5.1B active per token
- Apache 2.0 license
- Runs on single 80GB GPU with MXFP4
- At AWQ 4-bit, weight size would be ~60GB -- potentially fits TP=4 (64GB) with minimal KV headroom
- Outstanding tool calling and reasoning

### Models That Fit Athanor Hardware

| Model | SWE-bench V | Fits On | VRAM | License | Our Deployment |
|-------|-------------|---------|------|---------|----------------|
| **Qwen3.5-27B FP8** | 72.4% | 5090 (32GB), TP=4 (64GB) | 27 GB | Apache 2.0 | **Coordinator on TP=4** |
| **Qwen3.5-35B-A3B AWQ** | 69.2% | 4090 (24GB), 5090 (32GB) | 21 GB | Apache 2.0 | **Coder on 4090, Worker on 5090** |
| Devstral Small 2 24B | 68.0% | 4090 (24GB, FP8) | 24 GB | Apache 2.0 | Not deployed |
| Qwen3.5-122B-A10B AWQ | 72.0% | TP=4 (64GB) | 37 GB | Apache 2.0 | Not deployed |

**Assessment: Our current deployment is correct.** Qwen3.5-27B-FP8 on TP=4 and Qwen3.5-35B-A3B-AWQ on the coder/worker slots represent the best quality-to-fit ratio available. The only meaningful upgrade path is:

1. **GPT-OSS-120B on TP=4** -- if an AWQ quant under 60GB exists, this could replace the coordinator. Needs investigation.
2. **Qwen3.5-122B-A10B AWQ on TP=4** -- 72.0% SWE-bench, same as 27B, but better tool calling (BFCL-V4 72.2%). Uses 37GB/64GB.
3. **IQuest-Coder-V1-40B FP8 on TP=4** -- 76.2% SWE-bench. Custom license concern. 40GB/64GB.

### DeepSeek V4 Status

As of March 14, 2026, **DeepSeek V4 has still not been released.** Five release windows have been missed. A "V4 Lite" (~200B params) appeared on March 9 without official announcement. Expected to be 1T MoE with 1M context and multimodal. If released under Apache 2.0, it would be significant, but it cannot be planned around.

---

## 4. Best Open-Source Embedding Models

### MTEB Leaderboard (March 2026)

| Rank | Model | MTEB-En | MMTEB | Params | Dims | License | Fits Qdrant 1024? |
|------|-------|---------|-------|--------|------|---------|-------------------|
| 1 | KaLM-Embedding-Gemma3-12B | -- | 72.32 | 11.76B | 3840 | Custom | Yes (MRL 1024) |
| 2 | llama-embed-nemotron-8b | 69.46 | -- | 7.5B | 4096 | Non-commercial | No |
| 3 | Qwen3-Embedding-8B | 70.58 | -- | 8B | 1024 | Apache 2.0 | Yes |
| 4 | Qwen3-Embedding-4B | 69.45 | -- | 4B | 1024 | Apache 2.0 | Yes |
| -- | **Qwen3-Embedding-0.6B (ours)** | **70.70** | **64.33** | **0.6B** | **1024** | **Apache 2.0** | **Yes** |
| -- | jina-embeddings-v5-text-small | 71.7 | 67.0 | 677M | 1024 | CC BY-NC | Yes |

### Assessment: No Upgrade Needed

**Qwen3-Embedding-0.6B remains the best Apache 2.0 sub-1B embedding model.** Nothing has changed since the February 25 exhaustive survey:

- Jina v5-text-small edges it by +1.0 MTEB-En but is CC BY-NC (non-commercial)
- Everything higher quality requires 4B-12B parameters (would consume a GPU slot)
- 1024 dimensions match our Qdrant collections exactly
- ~1.5 GB VRAM, co-hosts easily on DEV's 5060 Ti with the reranker

**Future upgrade path if/when we want multimodal search:**
- Qwen3-VL-Embedding-2B (Jan 2026) -- unified text+image+video search
- Apache 2.0, 1024-dim via Matryoshka, ~4-5 GB VRAM
- Would enable image search in ComfyUI outputs, document screenshots, etc.

---

## 5. Notable Model Releases (Jan-Mar 2026)

### Tier 1: Game-Changers (But Too Large for Athanor Single-GPU)

| Model | Org | Released | Key Stats | Why It Matters |
|-------|-----|----------|-----------|----------------|
| **MiniMax M2.5** | MiniMax | Feb 2026 | 229B/10B MoE, 80.2% SWE-bench, Apache 2.0 | First open-weight frontier model. Needs 96GB minimum. |
| **GLM-5** | Z.ai | Feb 11, 2026 | 744B/40B MoE, 77.8% SWE-bench, MIT | #1 open-weight on Artificial Analysis. 200K context. |
| **Kimi K2.5** | Moonshot AI | Jan 27, 2026 | 1T/32B MoE, 76.8% SWE-bench, Modified MIT | Native multimodal. Can self-direct 100 sub-agents. |
| **Claude Opus 4.6** | Anthropic | Feb 5, 2026 | Closed. 65.4% Terminal-Bench 2.0 | Cloud ceiling for agentic workflows. |
| **Gemini 3.1 Pro** | Google | Feb 19, 2026 | Closed. 80.6% SWE-bench, 94.3% GPQA Diamond | Highest reported GPQA Diamond ever. |

### Tier 2: Relevant for Athanor Hardware

| Model | Org | Released | Key Stats | Relevance |
|-------|-----|----------|-----------|-----------|
| **Qwen3.5 (full family)** | Alibaba | Feb 16 + Mar 1 | 8 models, 0.8B-397B, Apache 2.0 | We deploy 27B-FP8 + 35B-A3B-AWQ. Best in-VRAM option. |
| **Qwen3.5-9B** | Alibaba | Mar 1, 2026 | 9B dense, LiveCodeBench 65.6 | Potential utility model on DEV 5060 Ti (BF16 ~18GB). |
| **Qwen3-VL-Embedding-2B** | Alibaba | Jan 8, 2026 | Multimodal embed, 1024-dim MRL, Apache 2.0 | Future multimodal search upgrade. |
| **GPT-OSS-120B** | OpenAI | Aug 2025 | 120B/5.1B MoE, Apache 2.0 | Potential TP=4 coordinator if AWQ fits. |
| **Devstral Small 2 24B** | Mistral | ~Feb 2026 | 24B dense, 68% SWE-bench, Apache 2.0 | Alternative coder for 4090 slot. |

### Tier 3: Notable But Not Directly Actionable

| Model | Why Notable | Why Not Actionable |
|-------|------------|-------------------|
| **DeepSeek V4** | Potentially transformative if released | Not released as of March 14. 5 windows missed. |
| **GPT-5.3 Codex** | Specialist for terminal-heavy coding | Closed-source, API only |
| **Grok 4.20** | Multi-agent architecture | Closed-source, API only |
| **Step-3.5-Flash** | 86.4% LiveCodeBench, Apache 2.0 | 196B/11B MoE -- ~98GB FP8, too large for VRAM |
| **MiMo-V2-Flash** | Competitive with DeepSeek V3.2 at half size | Still too large for single-GPU deployment |

### Key Industry Trends (Q1 2026)

1. **Open-weight models have reached frontier parity.** MiniMax M2.5 at 80.2% SWE-bench is competitive with Claude Opus 4.6. The gap between open and closed has effectively vanished for coding/reasoning.

2. **MoE is the winning architecture.** Every top model is MoE with low active-param counts. The era of dense frontier models is over. This is good news for VRAM-constrained deployments.

3. **SWE-bench contamination crisis.** OpenAI has stopped reporting SWE-bench Verified scores. SWE-bench Pro (1,865 tasks, multi-language) is emerging as replacement. Most open-weight models lack Pro evaluations yet.

4. **Chinese AI leadership crisis.** Qwen's team exodus, DeepSeek's repeated delays, and geopolitical pressure create uncertainty for the two most important open-weight model families. Diversify model pipeline monitoring.

5. **Agentic capabilities are now table stakes.** Tool calling, multi-step reasoning, environment interaction -- every major release emphasizes these. Athanor's LangGraph agent architecture is well-positioned.

---

## 6. Recommendations for Athanor

### Immediate Actions

| Priority | Action | Impact | Risk |
|----------|--------|--------|------|
| **HIGH** | Upgrade vLLM to v0.17.1 stable | FlashAttention 4 on Blackwell, native Qwen3.5 GDN, remove custom patches | Requires Docker image rebuild. Test on DEV first. |
| **MEDIUM** | Evaluate `qwen35_coder` tool parser vs current `qwen3_xml` | May fix edge cases in tool-call generation | Low risk -- parser swap only |
| **LOW** | Test Qwen3.5-9B on DEV 5060 Ti | Free utility inference endpoint for simple tasks | Shares GPU with embedding model |

### No Change Needed

| Component | Current | Assessment |
|-----------|---------|------------|
| Coordinator model | Qwen3.5-27B-FP8 on TP=4 | Best in-VRAM option. 72.4% SWE-bench. |
| Coder model | Qwen3.5-35B-A3B-AWQ on 4090 | Best fit for 24GB. +18.9pp over old Qwen3-Coder. |
| Worker model | Qwen3.5-35B-A3B-AWQ on 5090 | Correct deployment. |
| Embedding | Qwen3-Embedding-0.6B on DEV | Best sub-1B Apache 2.0 model. |

### Monitor (Not Yet Actionable)

| Item | Trigger to Act |
|------|---------------|
| DeepSeek V4 | If released under Apache 2.0 with claimed specs |
| GPT-OSS-120B AWQ quant | If community produces <60GB AWQ, test on TP=4 |
| Qwen4 (or successor) | If Alibaba's new leadership delivers a successor family |
| MiniMax M2.5 offloading | If llama.cpp/vLLM offloading matures for 229B models on 64GB VRAM |
| SWE-bench Pro evaluations | When open-weight models get Pro scores, re-rank |

---

## 7. Sources

### Model Announcements & Cards
- [Qwen3.5 Small Model Series (Alibaba)](https://x.com/Alibaba_Qwen/status/2028460046510965160) -- March 1, 2026
- [Qwen3.5 on HuggingFace](https://huggingface.co/Qwen) -- February 16, 2026
- [MiniMax M2.5](https://www.minimax.io/news/minimax-m25) -- February 2026
- [MiniMax M2.5 on HuggingFace](https://huggingface.co/MiniMaxAI/MiniMax-M2.5)
- [GLM-5 on HuggingFace](https://huggingface.co/zai-org/GLM-5) -- February 11, 2026
- [GLM-5 blog (mlabonne)](https://huggingface.co/blog/mlabonne/glm-5)
- [Kimi K2.5 on HuggingFace](https://huggingface.co/moonshotai/Kimi-K2.5) -- January 27, 2026
- [GPT-OSS-120B on HuggingFace](https://huggingface.co/openai/gpt-oss-120b) -- August 5, 2025
- [GPT-OSS-120B announcement (OpenAI)](https://openai.com/index/introducing-gpt-oss/)
- [Step-3.5-Flash on HuggingFace](https://huggingface.co/stepfun-ai/Step-3.5-Flash)
- [Devstral Small 2 (Mistral)](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512)

### vLLM
- [vLLM v0.17.1 Release](https://github.com/vllm-project/vllm/releases) -- March 11, 2026
- [vLLM Qwen3.5 Recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- [vLLM Releases Page](https://vllm.ai/releases)

### Embedding Models
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)

### Qwen Team Departures
- [Alibaba's Qwen tech lead steps down (TechCrunch)](https://techcrunch.com/2026/03/03/alibabas-qwen-tech-lead-steps-down-after-major-ai-push/)
- [Bloomberg: Alibaba Qwen head steps down](https://www.bloomberg.com/news/articles/2026-03-04/alibaba-qwen-head-who-warned-of-openai-gap-steps-down)
- [Simon Willison: Something is afoot in the land of Qwen](https://simonwillison.net/2026/Mar/4/qwen/)
- [VentureBeat: Key figures depart Qwen](https://venturebeat.com/technology/did-alibaba-just-kneecap-its-powerful-qwen-ai-team-key-figures-depart-in)

### DeepSeek V4
- [DeepSeek V4 release window (evolink)](https://evolink.ai/blog/deepseek-v4-release-window-prep)
- [DeepSeek V4 specs (NxCode)](https://www.nxcode.io/resources/news/deepseek-v4-release-specs-benchmarks-2026)
- [TechNode: DeepSeek plans V4 release](https://technode.com/2026/03/02/deepseek-plans-v4-multimodal-model-release-this-week-sources-say/)

### Industry Overviews
- [AI Updates (LLM Stats)](https://llm-stats.com/llm-updates)
- [Best AI Models 2026 (Pluralsight)](https://www.pluralsight.com/resources/blog/ai-and-data/best-ai-models-2026-list)
- [Best LLM for Coding (Onyx)](https://onyx.app/best-llm-for-coding)
- [Open Source LLM Leaderboard 2026 (Onyx)](https://onyx.app/open-llm-leaderboard)
- [Unsloth MiniMax M2.5 Guide](https://unsloth.ai/docs/models/minimax-m25)
- [Unsloth GLM-5 Guide](https://unsloth.ai/docs/models/glm-5)
- [Kimi K2.5 Guide (Unsloth)](https://unsloth.ai/docs/models/kimi-k2.5)

### Leaderboards
- [SWE-bench Verified](https://www.swebench.com/)
- [SWE-bench Pro (Scale AI)](https://labs.scale.com/leaderboard/swe_bench_pro_public)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Onyx Self-Hosted LLM Leaderboard](https://onyx.app/self-hosted-llm-leaderboard)
- [Qwen4 prediction market (Manifold)](https://manifold.markets/Bayesian/when-will-alibaba-release-qwen-4)

### Data Quality Notes
- SWE-bench Verified scores are scaffold-dependent (10-20% variation) and increasingly contaminated
- MTEB scores are self-reported by model providers -- no independent verification step
- DeepSeek V4 information is entirely from leaks/rumors
- MiniMax M2.5 VRAM requirements are from community testing, not official specs
- GLM-5 VRAM figures use Unsloth GGUF quants, not native formats

---

*Last updated: 2026-03-14*
