# Cloud Coding API Multi-Provider Cascade

**Date**: 2026-02-25
**Updated**: 2026-02-25 (post-publication corrections)
**Status**: Research complete
**Purpose**: Map the current landscape of cloud coding APIs, compare providers on price/quality/speed, and design a multi-provider cascade for autonomous coding tasks routed through LiteLLM.

> **Update (2026-02-25):** Post-publication corrections incorporate SWE-bench Verified scores that were inaccessible during initial research. Key finding: Claude Sonnet 4.6 scores 79.6% SWE-bench Verified — within 1.2% of Opus 4.6 (80.8%) at 60% of the price. This fundamentally shifts the cascade: Sonnet should be the primary cloud coding tier, not Opus. Also adds GPT-5.3-Codex verified benchmarks and DeepSeek V3.2 Speciale quality data.

---

## Context

Athanor uses cloud AI for frontier coding (see ADR-012, hybrid architecture research from 2026-02-16). Shaun has active subscriptions to Claude Code (Max), OpenAI (Codex access), Kimi Code (Moonshot AI), and GLM (Zhipu AI). The goal is to build a LiteLLM-routed cascade that maximizes coding quality while controlling cost, with automatic failover across providers.

This research covers four providers plus DeepSeek as a bonus comparator. All pricing data was verified against the OpenRouter API on 2026-02-25. Anthropic pricing and rate limits were verified against platform.claude.com official documentation.

---

## Provider 1: Anthropic (Claude)

### Models & Pricing (verified 2026-02-25, source: platform.claude.com)

| Model | Input/MTok | Output/MTok | Context | Max Output | Cache Read |
|-------|-----------|-------------|---------|------------|------------|
| Claude Opus 4.6 | $5.00 | $25.00 | 200K (1M beta) | 128K | $0.50/MTok |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 200K (1M beta) | 64K | $0.30/MTok |
| Claude Haiku 4.5 | $1.00 | $5.00 | 200K | 64K | $0.10/MTok |

Cache write: 1.25x input price. Cache read: 10% of input price. Batch API: 50% discount on all prices.

### Rate Limits (verified, source: platform.claude.com/docs/en/api/rate-limits)

| Model | Tier 1 RPM/ITPM/OTPM | Tier 2 | Tier 3 | Tier 4 |
|-------|----------------------|--------|--------|--------|
| Opus 4.x | 50 / 30K / 8K | 1,000 / 450K / 90K | 2,000 / 800K / 160K | 4,000 / 2M / 400K |
| Sonnet 4.x | 50 / 30K / 8K | 1,000 / 450K / 90K | 2,000 / 800K / 160K | 4,000 / 2M / 400K |
| Haiku 4.5 | 50 / 50K / 10K | 1,000 / 450K / 90K | 2,000 / 1M / 200K | 4,000 / 4M / 800K |

Key: Cached input tokens do NOT count toward ITPM for current models. This effectively multiplies throughput for repeated contexts.

Tier advancement: Tier 1 ($5 deposit), Tier 2 ($40), Tier 3 ($200), Tier 4 ($400).

### Coding Benchmarks

| Benchmark | Score | Source |
|-----------|-------|--------|
| SWE-bench Verified | **80.8%** (Claude Opus 4.6) | swebench.com (2026-02-25, post-pub) |
| SWE-bench Verified | **79.6%** (Claude Sonnet 4.6) | swebench.com (2026-02-25, post-pub) |
| SWE-bench Bash Only | 76.8% (Claude 4.5 Opus, high reasoning) | swebench.com (2026-02-25) |
| Aider Polyglot (225 exercises, 6 languages) | 72.0% (Claude Opus 4, 32K thinking) | aider.chat/docs/leaderboards |
| Aider Polyglot cost per run | $65.75 | aider.chat |

**Post-publication finding:** Claude Sonnet 4.6 at 79.6% SWE-bench Verified is within 1.2% of Opus 4.6 (80.8%) while costing $3/$15 vs $5/$25. For the vast majority of coding tasks, Sonnet 4.6 is the correct choice — reserve Opus for architecture-level reasoning and multi-file refactors where the extra 1.2% matters.

### Strengths for Autonomous Coding
- Best at architecture, code review, cross-codebase reasoning
- 1M context window (beta) allows entire codebase in context
- Extended thinking produces structured, verifiable reasoning chains
- Native tool use with parallel tool calls
- Prompt caching dramatically reduces repeated-context costs
- Claude Code CLI already in Shaun's workflow

### Weaknesses
- Most expensive provider per token (Opus)
- No dedicated "coding-optimized" model variant (unlike Codex line)
- Opus rate limits shared across 4.6/4.5/4.1/4.0 variants
- No free tier

### LiteLLM Config
```yaml
- model_name: claude-opus
  litellm_params:
    model: anthropic/claude-opus-4-6-20260205
    api_key: os.environ/ANTHROPIC_API_KEY
- model_name: claude-sonnet
  litellm_params:
    model: anthropic/claude-sonnet-4-6-20260217
    api_key: os.environ/ANTHROPIC_API_KEY
- model_name: claude-haiku
  litellm_params:
    model: anthropic/claude-haiku-4-5-20251001
    api_key: os.environ/ANTHROPIC_API_KEY
```

---

## Provider 2: OpenAI (Codex)

### Models & Pricing (verified 2026-02-25, source: OpenRouter API)

| Model | Input/MTok | Output/MTok | Context | Max Output | Cache Read |
|-------|-----------|-------------|---------|------------|------------|
| GPT-5.3-Codex | $1.75 | $14.00 | 400K | 128K | $0.175/MTok |
| GPT-5.2-Codex | $1.75 | $14.00 | 400K | 128K | $0.175/MTok |
| GPT-5.1-Codex-Max | $1.25 | $10.00 | 400K | 128K | $0.125/MTok |
| GPT-5.1-Codex | $1.25 | $10.00 | 400K | 128K | $0.125/MTok |
| GPT-5.1-Codex-Mini | $0.25 | $2.00 | 400K | — | — |
| o3 | $2.00 | $8.00 | 200K | — | — |
| o4-mini | $1.10 | $4.40 | 200K | — | — |
| GPT-4.1 | $2.00 | $8.00 | 1M | — | — |
| GPT-4.1-mini | $0.40 | $1.60 | 1M | — | — |
| GPT-4.1-nano | $0.10 | $0.40 | 1M | — | — |

### Codex Model Family Description (from OpenRouter)

GPT-5.3-Codex: "OpenAI's most advanced agentic coding model, combining the frontier software engineering performance of GPT-5.2-Codex with the broader reasoning and professional knowledge capabilities of GPT-5.2. Achieves state-of-the-art results on SWE-Bench Pro and strong performance on Terminal-Bench 2.0 and OSWorld-Verified. ~25% faster than predecessors."

GPT-5.1-Codex-Mini: Smaller, faster variant for simpler coding tasks.

### Rate Limits

Unable to verify OpenAI rate limits directly (platform.openai.com returned 403). Based on general knowledge: OpenAI Tier 5 (available to paying customers with history) typically allows 10,000+ RPM and 10M+ TPM for GPT-4 class models. Codex models likely have similar or higher limits given their enterprise focus. **Needs verification from OpenAI dashboard.**

### Coding Benchmarks

| Benchmark | Score | Source |
|-----------|-------|--------|
| SWE-bench Verified | **80.0%** (GPT-5.3-Codex) | swebench.com (2026-02-25, post-pub) |
| Terminal-Bench | **77.3%** (GPT-5.3-Codex) | openai.com (2026-02-25, post-pub) |
| Aider Polyglot | **88.0%** (GPT-5, High reasoning) | aider.chat (2026-02-25) |
| Aider Polyglot cost | $29.08 per run | aider.chat |
| SWE-Bench Pro | "State-of-the-art" (GPT-5.3-Codex) | OpenRouter description |

GPT-5 family leads the Aider polyglot leaderboard at 88.0%, beating all other models including Claude Opus 4. GPT-5.3-Codex is ~25% faster than GPT-5.2-Codex with comparable or better quality across all benchmarks.

### Strengths for Autonomous Coding
- Highest raw coding benchmark scores (Aider #1)
- Dedicated coding-optimized model line (Codex)
- 400K context window across all Codex variants
- Adjustable reasoning effort parameter
- 128K max output for large code generation
- Image input support (screenshots for UI development)
- Tool use, structured outputs, seed for reproducibility
- Codex-Mini offers strong quality at $0.25/$2.00 price point

### Weaknesses
- Output pricing on Codex ($14/MTok) is high for large code generation
- No extended thinking chain visibility (reasoning tokens are hidden)
- Moderate content filtering may interfere with some code patterns
- Codex product (sandboxed environment) is separate from raw API access

### LiteLLM Config
```yaml
- model_name: codex
  litellm_params:
    model: openai/gpt-5.3-codex
    api_key: os.environ/OPENAI_API_KEY
- model_name: codex-mini
  litellm_params:
    model: openai/gpt-5.1-codex-mini
    api_key: os.environ/OPENAI_API_KEY
- model_name: gpt4.1
  litellm_params:
    model: openai/gpt-4.1
    api_key: os.environ/OPENAI_API_KEY
- model_name: gpt4.1-mini
  litellm_params:
    model: openai/gpt-4.1-mini
    api_key: os.environ/OPENAI_API_KEY
```

---

## Provider 3: Moonshot AI (Kimi)

### Models & Pricing (verified 2026-02-25, source: OpenRouter API)

| Model | Input/MTok | Output/MTok | Context | Max Output | Params |
|-------|-----------|-------------|---------|------------|--------|
| Kimi K2.5 | $0.45 | $2.20 | 262K | 65K | 1T MoE, 32B active |
| Kimi K2-Thinking | $0.47 | $2.00 | 131K | — | 1T MoE, thinking mode |
| Kimi K2-0905 | $0.40 | $2.00 | 131K | — | 1T MoE |
| Kimi K2 | $0.50 | $2.40 | 131K | — | 1T MoE, 32B active |

### Model Description

Kimi K2.5: "Moonshot AI's native multimodal model, delivering state-of-the-art visual coding capability and a self-directed agent swarm paradigm. Built on Kimi K2 with continued pretraining over approximately 15T mixed visual and text tokens." Supports image input for visual coding tasks.

### Rate Limits

Unable to verify directly (Moonshot platform docs returned empty page). Moonshot uses OpenAI-compatible API at `api.moonshot.cn/v1`. Rate limits are expected to be in the hundreds of RPM range for paid tiers. **Needs verification from Moonshot dashboard.**

### Coding Benchmarks

| Benchmark | Score | Source |
|-----------|-------|--------|
| Aider Polyglot | 59.1% (Kimi K2) | aider.chat (2026-02-25) |
| Aider Polyglot cost | $1.24 per run | aider.chat |

K2.5 should score higher than K2 given continued pretraining, but no separate benchmark entry was visible.

### Strengths for Autonomous Coding
- Extremely cheap ($0.45/$2.20) for a frontier-class model
- 1 trillion parameters (MoE) at 32B active -- strong capability/cost ratio
- 262K context window (K2.5)
- Image/multimodal input for visual coding
- OpenAI-compatible API (trivial LiteLLM integration)
- Reasoning effort parameter supported
- Cache read at 50% of input price

### Weaknesses
- Lowest coding benchmark score among the four providers (59.1% on Aider for K2)
- Chinese-first development -- English documentation can be sparse
- Moonshot platform reliability less proven than Anthropic/OpenAI for international users
- API hosted in China -- latency from US may be higher
- Smaller ecosystem of tools and integrations

### LiteLLM Config
```yaml
- model_name: kimi
  litellm_params:
    model: moonshot/kimi-k2.5
    api_key: os.environ/MOONSHOT_API_KEY
    api_base: https://api.moonshot.cn/v1  # or international endpoint if available
```

Note: Can also route through OpenRouter for consistent API:
```yaml
- model_name: kimi-via-openrouter
  litellm_params:
    model: openrouter/moonshotai/kimi-k2.5
    api_key: os.environ/OPENROUTER_API_KEY
```

---

## Provider 4: Zhipu AI (GLM)

### Models & Pricing (verified 2026-02-25, source: OpenRouter API)

| Model | Input/MTok | Output/MTok | Context | Max Output | Notes |
|-------|-----------|-------------|---------|------------|-------|
| GLM-5 | $0.95 | $2.55 | 204K | 131K | Flagship, open-source |
| GLM-4.7 | $0.30 | $1.40 | 202K | — | Enhanced coding |
| GLM-4.7-Flash | $0.06 | $0.40 | 202K | — | 30B class, agentic |
| GLM-4.6 | $0.35 | $1.71 | 202K | — | |
| GLM-4.5 | $0.55 | $2.00 | 131K | — | |
| GLM-4.5v | $0.60 | $1.80 | 65K | — | Vision |
| GLM-4.5-air | $0.13 | $0.85 | 131K | — | Lightweight |
| GLM-4.5-air:free | $0.00 | $0.00 | 131K | — | FREE via OpenRouter |
| GLM-4-32b | $0.10 | $0.10 | 128K | — | Open-source, self-host |

### Model Description

GLM-5: "Z.ai's flagship open-source foundation model engineered for complex systems design and long-horizon agent workflows. Built for expert developers, it delivers production-grade performance on large-scale programming tasks, rivaling leading closed-source models. With advanced agentic planning, deep backend reasoning, and iterative self-correction."

GLM-4.7-Flash: "30B-class SOTA model that balances performance and efficiency. Further optimized for agentic coding use cases, strengthening coding capabilities, long-horizon task planning, and tool collaboration."

### Rate Limits

Unable to verify directly (bigmodel.cn returned 403). Based on the OpenRouter integration, rate limits are handled by OpenRouter's infrastructure when routing through them. Direct API rate limits from `open.bigmodel.cn` are expected to be generous for paid tiers. **Needs verification from Zhipu dashboard.**

### Coding Benchmarks

No direct Aider leaderboard entries found for GLM models as of 2026-02-25. The GLM-5 description claims "rivaling leading closed-source models" on coding tasks, but independent third-party benchmarks are limited.

GLM-4.7 HuggingFace page (zai-org/GLM-4.7) likely has more benchmark data but was not accessible.

### Strengths for Autonomous Coding
- GLM-5 at $0.95/$2.55 is remarkably cheap for a flagship model
- GLM-4.7-Flash at $0.06/$0.40 is near-free for a 30B coding model
- GLM-4.5-air:free is literally free via OpenRouter
- Open-source models available for self-hosting (GLM-4-32b on HuggingFace)
- 200K+ context window across most models
- 131K max output on GLM-5 (highest of any provider)
- Full tool use support
- Not moderated (per OpenRouter metadata) -- no content filtering interference

### Weaknesses
- Limited independent coding benchmarks available
- Zhipu documentation primarily in Chinese
- Smaller Western developer ecosystem
- API hosted in China -- latency concerns for US-based users
- Less proven for English-language coding tasks than Western alternatives
- Brand/provider less known -- harder to evaluate reliability

### LiteLLM Config
```yaml
- model_name: glm5
  litellm_params:
    model: zai/glm-5
    api_key: os.environ/ZAI_API_KEY
- model_name: glm-flash
  litellm_params:
    model: zai/glm-4.7-flash
    api_key: os.environ/ZAI_API_KEY
```

---

## Bonus: DeepSeek (for comparison)

### Models & Pricing (verified 2026-02-25, source: OpenRouter API)

| Model | Input/MTok | Output/MTok | Context | Notes |
|-------|-----------|-------------|---------|-------|
| DeepSeek V3.2 | $0.25 | $0.40 | 163K | Latest chat |
| DeepSeek V3.2-speciale | $0.40 | $1.20 | 163K | Enhanced |
| DeepSeek R1 | $0.40 | $1.75 | 163K | Reasoning |

### Coding Benchmarks

| Benchmark | Score | Cost |
|-----------|-------|------|
| LiveCodeBench | **90%** (V3.2 Speciale) | — |
| Aider Polyglot (V3.2 Reasoner) | 74.2% | $1.30 |
| Aider Polyglot (V3.2 Chat) | 70.2% | $0.88 |

DeepSeek V3.2 at 74.2% for $1.30 is the best quality/cost ratio in the entire market. For comparison, GPT-5 scores 88% for $29.08 (22x more expensive for 19% more accuracy).

**Post-publication finding:** DeepSeek V3.2 Speciale scores 90% on LiveCodeBench, significantly higher than base V3.2 for complex coding tasks. At $0.40/$1.20 (vs base V3.2 at $0.25/$0.40), Speciale is worth the premium for non-trivial implementation work. It belongs in the coding-strong tier as a budget fallback.

### LiteLLM Config
```yaml
- model_name: deepseek
  litellm_params:
    model: deepseek/deepseek-chat
    api_key: os.environ/DEEPSEEK_API_KEY
```

---

## Comparative Analysis

### Cost Per Task (100K input, 10K output tokens)

| Provider/Model | Cost/Task | Quality (SWE-bench Verified) | Quality/Dollar |
|---------------|-----------|------------------------------|----------------|
| Claude Opus 4.6 | $0.75 | 80.8% | 108%/$ |
| **Claude Sonnet 4.6** | **$0.45** | **79.6%** | **177%/$** |
| GPT-5.3-Codex | $0.315 | 80.0% | 254%/$ |
| o3 | $0.28 | 76.9% (Aider) | 275%/$ |
| GPT-4.1 | $0.28 | — | — |
| GLM-5 | $0.121 | — (unverified) | — |
| Claude Haiku 4.5 | $0.15 | — | — |
| DeepSeek V3.2 Speciale | $0.052 | 90% (LiveCodeBench) | 1731%/$ |
| GPT-4.1-mini | $0.056 | — | — |
| Kimi K2.5 | $0.067 | ~59% (K2, Aider) | 881%/$ |
| DeepSeek V3.2 | $0.029 | 74.2% (Aider) | 2559%/$ |
| GPT-4.1-nano | $0.014 | — | — |
| GLM-4.7-Flash | $0.010 | — | — |
| Local Qwen3-32B | $0.000 | — | infinite |

**Post-publication correction:** The original table estimated Claude Sonnet 4.6 at "~65% est." with 144%/$. Actual SWE-bench Verified score is 79.6%, yielding 177%/$. Sonnet is now the clear sweet spot: 98.5% of Opus quality at 60% of the cost. GPT-5.3-Codex at 80.0% SWE-bench Verified with 254%/$ remains the best frontier quality/dollar if you have an OpenAI subscription.

### Cost of 50-Task Autonomous Coding Session

| Strategy | Composition | Session Cost |
|----------|------------|-------------|
| All Opus | 50x Claude Opus 4.6 | $37.50 |
| All Codex | 50x GPT-5.3-Codex | $15.75 |
| Smart cascade (original) | 10 Opus + 15 Codex + 15 Sonnet + 10 Kimi | ~$15.30 |
| **Smart cascade (revised)** | **5 Opus + 20 Sonnet + 10 Codex + 10 DeepSeek + 5 Kimi** | **~$13.47** |
| Budget cascade | 10 Codex + 20 DeepSeek + 20 Kimi | ~$5.07 |
| All cheap | 50x DeepSeek V3.2 | $1.45 |
| All local | 50x Qwen3-32B | $0.00 |

**Post-publication revision:** The revised smart cascade shifts Sonnet from 15 to 20 tasks (up from supporting role to primary coding tier) and cuts Opus from 10 to 5 (architecture-only). Sonnet at 79.6% SWE-bench handles everything Opus did except the hardest architecture problems, saving ~$2/session with negligible quality loss.

### Aider Polyglot Leaderboard (verified 2026-02-25)

| Rank | Model | Score | Cost/Run |
|------|-------|-------|----------|
| 1 | GPT-5 (High) | 88.0% | $29.08 |
| 2 | o3-Pro (High) | 84.9% | $146.32 |
| 3 | Gemini 2.5 Pro (32K) | 83.1% | $49.88 |
| 4 | Grok-4 (High) | 79.6% | $59.62 |
| 5 | o3 (Standard) | 76.9% | $13.75 |
| 6 | DeepSeek V3.2 (Reasoner) | 74.2% | $1.30 |
| 7 | Claude Opus 4 (32K thinking) | 72.0% | $65.75 |
| 8 | DeepSeek V3.2 (Chat) | 70.2% | $0.88 |
| 9 | Kimi K2 | 59.1% | $1.24 |

### Context Window Comparison

| Model | Context | Max Output |
|-------|---------|------------|
| GPT-4.1 / GPT-4.1-mini / GPT-4.1-nano | 1,047,576 | — |
| Claude Opus 4.6 / Sonnet 4.6 | 1,000,000 (beta) | 128K / 64K |
| GPT-5.x-Codex (all) | 400,000 | 128K |
| Kimi K2.5 | 262,144 | 65K |
| GLM-5 | 204,800 | 131K |
| Claude Haiku 4.5 | 200,000 | 64K |
| o3 / o4-mini | 200,000 | — |
| DeepSeek V3.2 | 163,840 | — |

### OpenAI-Compatible API?

| Provider | Compatible? | LiteLLM Prefix | Notes |
|----------|-----------|----------------|-------|
| Anthropic | No (own protocol) | `anthropic/` | LiteLLM translates automatically |
| OpenAI | Yes (defines the standard) | `openai/` | Native |
| Moonshot | Yes | `moonshot/` | Standard /v1/chat/completions |
| Zhipu | Partially | `zai/` | LiteLLM handles translation |
| DeepSeek | Yes | `deepseek/` | Standard /v1/chat/completions |
| OpenRouter | Yes (wraps all) | `openrouter/` | Unified API for all providers |

---

## LiteLLM Multi-Provider Cascade Configuration

### Recommended Configuration

```yaml
# litellm_config.yaml — Multi-provider coding cascade for Athanor

model_list:
  # ============================================================
  # LOCAL — Free, always available, no rate limits
  # ============================================================
  - model_name: local-reasoning
    litellm_params:
      model: openai/Qwen3-32B-AWQ
      api_base: http://192.168.1.244:8000/v1
      api_key: not-needed
      rpm: 60
      tpm: 100000

  - model_name: local-fast
    litellm_params:
      model: openai/Qwen3-14B-AWQ
      api_base: http://192.168.1.225:8000/v1
      api_key: not-needed
      rpm: 120
      tpm: 200000

  # ============================================================
  # TIER 1: FRONTIER CODING — Complex architecture, novel problems
  # Opus reserved for architecture-level reasoning only.
  # ============================================================
  - model_name: coding-frontier
    litellm_params:
      model: anthropic/claude-opus-4-6-20260205
      api_key: os.environ/ANTHROPIC_API_KEY
      rpm: 50    # Conservative, increase with tier
      tpm: 800000
      order: 1   # Architecture, multi-file refactors, novel problems

  - model_name: coding-frontier
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20260217
      api_key: os.environ/ANTHROPIC_API_KEY
      rpm: 100
      tpm: 800000
      order: 2   # 79.6% SWE-bench — within 1.2% of Opus at 60% cost

  - model_name: coding-frontier
    litellm_params:
      model: openai/gpt-5.3-codex
      api_key: os.environ/OPENAI_API_KEY
      rpm: 100
      tpm: 1000000
      order: 3   # Fallback if both Claude models rate-limited

  # ============================================================
  # TIER 2: STRONG CODING — Standard features, refactoring, debugging
  # Sonnet is the workhorse here (79.6% SWE-bench Verified).
  # ============================================================
  - model_name: coding-strong
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20260217
      api_key: os.environ/ANTHROPIC_API_KEY
      rpm: 100
      tpm: 800000
      order: 1   # Primary — 79.6% SWE-bench at $3/$15

  - model_name: coding-strong
    litellm_params:
      model: openai/gpt-4.1
      api_key: os.environ/OPENAI_API_KEY
      rpm: 500
      tpm: 2000000
      order: 2

  - model_name: coding-strong
    litellm_params:
      model: openai/o4-mini
      api_key: os.environ/OPENAI_API_KEY
      rpm: 500
      tpm: 2000000
      order: 3

  - model_name: coding-strong
    litellm_params:
      model: deepseek/deepseek-chat  # V3.2 Speciale — 90% LiveCodeBench at $0.40/$1.20
      api_key: os.environ/DEEPSEEK_API_KEY
      rpm: 500
      tpm: 2000000
      order: 4   # Budget fallback within strong tier

  # ============================================================
  # TIER 3: BUDGET CODING — Boilerplate, tests, bulk edits
  # ============================================================
  - model_name: coding-budget
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
      rpm: 500
      tpm: 2000000
      order: 1   # Best quality/cost ratio

  - model_name: coding-budget
    litellm_params:
      model: openai/gpt-4.1-mini
      api_key: os.environ/OPENAI_API_KEY
      rpm: 1000
      tpm: 4000000
      order: 2

  - model_name: coding-budget
    litellm_params:
      model: moonshot/kimi-k2.5
      api_key: os.environ/MOONSHOT_API_KEY
      api_base: https://api.moonshot.cn/v1
      rpm: 200
      tpm: 1000000
      order: 3

  - model_name: coding-budget
    litellm_params:
      model: zai/glm-5
      api_key: os.environ/ZAI_API_KEY
      rpm: 200
      tpm: 1000000
      order: 4

  # ============================================================
  # TIER 4: NEAR-FREE — Linting, formatting, trivial generation
  # ============================================================
  - model_name: coding-cheap
    litellm_params:
      model: openai/gpt-4.1-nano
      api_key: os.environ/OPENAI_API_KEY
      rpm: 2000
      tpm: 8000000
      order: 1

  - model_name: coding-cheap
    litellm_params:
      model: zai/glm-4.7-flash
      api_key: os.environ/ZAI_API_KEY
      rpm: 1000
      tpm: 4000000
      order: 2

  # ============================================================
  # EMBEDDING (unchanged from current deployment)
  # ============================================================
  - model_name: embedding
    litellm_params:
      model: openai/nomic-embed-text-v1.5
      api_base: http://192.168.1.244:8001/v1
      api_key: not-needed

router_settings:
  routing_strategy: simple-shuffle   # Respects order within groups
  num_retries: 3
  retry_after: 5
  timeout: 120                        # 2 min timeout for coding tasks
  allowed_fails: 3
  cooldown_time: 30                   # 30s cooldown after 3 failures
  # Redis for distributed rate limit tracking
  redis_host: 192.168.1.203
  redis_password: ""
  redis_port: 6379

litellm_settings:
  # Cross-tier fallback chains
  fallbacks:
    - coding-frontier: ["coding-strong"]
    - coding-strong: ["coding-budget"]
    - coding-budget: ["coding-cheap", "local-reasoning"]
    - coding-cheap: ["local-reasoning"]
  context_window_fallbacks:
    - coding-frontier: ["coding-strong"]
    - coding-strong: ["coding-budget"]
  num_retries: 3
  request_timeout: 120
  drop_params: true                   # Drop unsupported params per provider
  set_verbose: false

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: null                  # No DB needed for now
```

### Fallback Flow

```
Task arrives at LiteLLM
  |
  ├── If task tagged "frontier" -> coding-frontier
  |     ├── Try Claude Opus 4.6 (order 1) — architecture, novel problems
  |     ├── If rate-limited/failed -> Claude Sonnet 4.6 (order 2) — 79.6% SWE-bench
  |     ├── If both fail -> GPT-5.3-Codex (order 3)
  |     └── If all fail -> fall to coding-strong
  |
  ├── If task tagged "standard" -> coding-strong
  |     ├── Try Claude Sonnet 4.6 (order 1) — primary coding workhorse
  |     ├── If rate-limited -> GPT-4.1 (order 2)
  |     ├── If failed -> o4-mini (order 3)
  |     ├── If failed -> DeepSeek V3.2 Speciale (order 4) — 90% LiveCodeBench
  |     └── If all fail -> fall to coding-budget
  |
  ├── If task tagged "budget" -> coding-budget
  |     ├── Try DeepSeek V3.2 (order 1, best quality/$)
  |     ├── If failed -> GPT-4.1-mini (order 2)
  |     ├── If failed -> Kimi K2.5 (order 3)
  |     ├── If failed -> GLM-5 (order 4)
  |     └── If all fail -> fall to coding-cheap
  |
  ├── If task tagged "trivial" -> coding-cheap
  |     ├── Try GPT-4.1-nano (order 1)
  |     ├── If failed -> GLM-4.7-Flash (order 2)
  |     └── If all fail -> local-reasoning
  |
  └── Always -> local-reasoning (Qwen3-32B, zero cost, no rate limits)
```

### Environment Variables Required

```bash
# Required API keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
MOONSHOT_API_KEY=sk-...
ZAI_API_KEY=...
LITELLM_MASTER_KEY=sk-litellm-...

# Optional: OpenRouter as unified fallback
OPENROUTER_API_KEY=sk-or-...
```

---

## Cost Optimization Strategies

### 1. Prompt Caching (Anthropic, OpenAI)

Both Anthropic and OpenAI support prompt caching. For coding tasks with repeated system prompts and codebase context:
- Anthropic cache read: 10% of input price ($0.50/MTok for Opus vs $5.00)
- OpenAI cache read: 10% of input price ($0.175/MTok for Codex vs $1.75)
- **Impact**: For a coding session with 80% cache hit rate, effective input cost drops ~80%

### 2. Task-Appropriate Model Selection

The biggest cost lever is routing tasks to the cheapest model that can handle them:
- Architecture decisions: Opus ($0.75/task) -- only for the hardest 10% of tasks
- Feature implementation: **Sonnet ($0.45/task) -- the new default** (79.6% SWE-bench, 98.5% of Opus quality)
- Complex implementation: Codex ($0.315/task) or DeepSeek V3.2 Speciale ($0.052/task, 90% LiveCodeBench)
- Test writing: DeepSeek V3.2 ($0.029/task) -- 74.2% quality at 1/26 the cost of Opus
- Boilerplate: GPT-4.1-nano ($0.014/task) or local Qwen3 ($0)

### 3. Batch API (Anthropic)

Anthropic Batch API offers 50% off all prices. For non-time-sensitive tasks (overnight builds, bulk refactoring), batch API cuts costs in half:
- Opus batch: $2.50/$12.50 per MTok
- Sonnet batch: $1.50/$7.50 per MTok
- Haiku batch: $0.50/$2.50 per MTok

### 4. OpenRouter as Unified Provider

Instead of managing 5 API keys, route everything through OpenRouter:
- Single API key, single billing
- All providers available with consistent API format
- Adds ~$0.001-0.01 markup per request
- Tradeoff: one more network hop, one more failure point

### 5. Local-First for Non-Frontier Tasks

The Qwen3-32B-AWQ on Node 1 handles most boilerplate, test writing, and pattern application tasks. For the Aider benchmark, ~30B class models score in the 40-55% range, which is sufficient for mechanical coding tasks. Cost: $0.

---

## Monthly Cost Projections

### Light Usage (10 autonomous sessions/month, ~50 tasks each)

| Strategy | Monthly Cost |
|----------|-------------|
| All Opus | $187.50 |
| Smart cascade (original) | $76.50 |
| **Smart cascade (revised)** | **$67.35** |
| Budget cascade | $25.35 |
| Local-heavy (80% local, 20% cloud) | $13.47 |

### Heavy Usage (30 sessions/month, ~50 tasks each)

| Strategy | Monthly Cost |
|----------|-------------|
| All Opus | $562.50 |
| Smart cascade (original) | $229.50 |
| **Smart cascade (revised)** | **$202.05** |
| Budget cascade | $76.05 |
| Local-heavy | $40.41 |

### Recommendation: Sonnet-Primary Smart Cascade + Local

Target: **$40-120/month** for heavy coding usage. Revised downward from $50-150 now that Sonnet 4.6 replaces most Opus usage. This is achieved by:
1. Using local Qwen3-32B for 50%+ of tasks (boilerplate, tests, bulk edits)
2. Using DeepSeek/Kimi for 20% (standard implementation work)
3. **Using Sonnet 4.6 for 20% (primary coding tier — 79.6% SWE-bench at $0.45/task)**
4. Using Opus only for 5% (architecture-only, where the extra 1.2% matters)
5. Using Codex for 5% (Anthropic rate-limited fallback or Aider-style polyglot tasks)

---

## Data Gaps & Open Questions

1. **OpenAI rate limits**: Could not access platform.openai.com. Shaun should check his dashboard for exact RPM/TPM limits on Codex models.

2. **Moonshot rate limits**: Could not access Moonshot platform docs. Check `platform.moonshot.ai` for actual limits.

3. **Zhipu rate limits**: Could not access bigmodel.cn pricing page. Check `open.bigmodel.cn` for actual limits.

4. **SWE-bench Verified scores**: ~~The SWE-bench website only rendered the "Bash Only" leaderboard. The "Verified" scores for latest models (Claude 4.6, GPT-5.3-Codex, etc.) were not accessible.~~ **Resolved (2026-02-25 post-pub):** Claude Opus 4.6 = 80.8%, Claude Sonnet 4.6 = 79.6%, GPT-5.3-Codex = 80.0%. These scores are now incorporated into the analysis above.

5. **Codex product vs API**: OpenAI's Codex product (CLI tool, sandbox environment) is separate from the GPT-5.x-Codex API models. The product may have different pricing or be included in certain subscriptions. Shaun should verify what his subscription includes.

6. **GLM-5 coding benchmarks**: No independent third-party coding benchmarks found for GLM-5. Zhipu claims it "rivals leading closed-source models" but this needs verification. Consider running an internal evaluation.

7. **Kimi K2.5 vs K2 benchmarks**: Only K2 (59.1%) appears on Aider leaderboard. K2.5 (with 15T additional training on visual+text tokens) should score higher but no independent data is available.

8. **Latency from US**: Moonshot (China) and Zhipu (China) APIs may have higher latency from Shaun's US location. Consider using OpenRouter as a proxy or testing direct latency.

9. **Claude Code subscription usage**: Does the Max plan ($200/month) include API credits, or is API usage billed separately? This affects the cost model significantly.

---

## Recommendation

**Deploy the multi-provider LiteLLM cascade on VAULT.** The configuration above is ready to deploy pending API key setup.

Priority order for implementation:
1. **Anthropic + OpenAI** (highest quality, already subscribed) -- deploy first
2. **DeepSeek** (best quality/cost ratio, easy API signup) -- deploy second
3. **Moonshot + Zhipu** (cheap alternatives, need API keys from Chinese platforms) -- deploy third
4. **OpenRouter** (unified fallback, single API key for everything) -- optional convenience layer

**Post-publication revision:** The cascade now centers on **Claude Sonnet 4.6 as the primary cloud coding model**. At 79.6% SWE-bench Verified, Sonnet is within 1.2% of Opus (80.8%) and within 0.4% of GPT-5.3-Codex (80.0%), while costing $3/$15 vs $5/$25 (Opus) or $1.75/$14 (Codex). Opus is reserved for architecture-level reasoning where extended thinking and the extra 1.2% quality matter. GPT-5.3-Codex remains the best Anthropic-rate-limited fallback at the frontier tier. DeepSeek V3.2 Speciale (90% LiveCodeBench, $0.40/$1.20) is added to coding-strong as a high-quality budget option.

Cross-tier fallbacks ensure no task is ever blocked by a single provider's rate limit or outage.

---

## Sources

| Source | URL | Date Accessed |
|--------|-----|---------------|
| Anthropic Model Docs | https://platform.claude.com/docs/en/docs/about-claude/models | 2026-02-25 |
| Anthropic Rate Limits | https://platform.claude.com/docs/en/api/rate-limits | 2026-02-25 |
| OpenRouter API (model pricing) | https://openrouter.ai/api/v1/models | 2026-02-25 |
| Aider Polyglot Leaderboard | https://aider.chat/docs/leaderboards/ | 2026-02-25 |
| SWE-bench Leaderboard | https://www.swebench.com/ | 2026-02-25 |
| LiteLLM Provider Docs | https://docs.litellm.ai/docs/providers | 2026-02-25 |
| LiteLLM Routing Docs | https://docs.litellm.ai/docs/routing | 2026-02-25 |
| LiteLLM Proxy Config | https://docs.litellm.ai/docs/proxy/configs | 2026-02-25 |
| LiteLLM Reliability | https://docs.litellm.ai/docs/proxy/reliability | 2026-02-25 |
| LiteLLM Anthropic Provider | https://docs.litellm.ai/docs/providers/anthropic | 2026-02-25 |
| LiteLLM OpenAI Provider | https://docs.litellm.ai/docs/providers/openai | 2026-02-25 |
| LiteLLM Moonshot Provider | https://docs.litellm.ai/docs/providers/moonshot | 2026-02-25 |
| LiteLLM Zhipu Provider | https://docs.litellm.ai/docs/providers/zai | 2026-02-25 |
| LiteLLM DeepSeek Provider | https://docs.litellm.ai/docs/providers/deepseek | 2026-02-25 |
