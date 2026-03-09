# A/B Comparison: Reasoning vs Creative — 2026-03-09

## Setup
- 16 test cases across 7 categories: reasoning, coding, analysis, creative, instruction-following, knowledge, practical
- Grader: fast (Qwen3-8B) for cost efficiency
- Models: Qwen3.5-27B-FP8 TP=4 (reasoning) vs Qwen3.5-35B-A3B-AWQ (creative)

## Results

| Model | Pass Rate | Avg Latency |
|-------|-----------|-------------|
| Qwen3.5-27B-FP8 (reasoning, FOUNDRY TP=4) | 15/16 (94%) | 50.8s |
| Qwen3.5-35B-A3B-AWQ (creative, WORKSHOP 5090) | 15/16 (94%) | **4.2s** |

## Key Finding

**Both models are equal quality. The creative/MoE model is 12× faster.**

This is the expected result for MoE models: 35B-A3B activates only ~3B parameters per forward pass,
giving dense-model quality at sparse-model inference cost. The reasoning model's 50.8s latency is
partly due to generating `<think>...</think>` tokens that get stripped before delivery.

## The One Failure (Both Models)

The farmer puzzle (15 animals, 44 legs → 8 chickens + 7 cows) was failed by both models.
This turned out to be a **rubric bug** — the rubric said "7 chickens and 8 cows" but the correct
answer is 8 chickens and 7 cows (2×8 + 4×7 = 44 ✓). Both models actually answered correctly.
**True pass rate: 16/16 (100%) for both models.**

## Routing Implications

Given equal quality, route by latency/use case:
- **Fast tasks** (chat, most agent work): use `creative` (35B-A3B-AWQ) — 4.2s avg
- **Deep reasoning** (complex analysis, math, debugging): `reasoning` (27B-FP8) only if needed
- Current routing in LiteLLM: `fast` slot → Qwen3-8B (utility), `reasoning` → 27B-FP8, `worker` → 35B-A3B
- Most agent tasks go to `fast` or `reasoning`. Consider adding `worker` as fallback for load balancing.

## Stats
- Total tokens: 28,896 (graded by 43,643 tokens)
- Duration: 291s (both providers in parallel)
- Zero errors
