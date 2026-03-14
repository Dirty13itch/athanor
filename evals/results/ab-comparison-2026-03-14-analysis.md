# 3-Model Comparison: Reasoning vs Creative vs Coder — 2026-03-14

## Setup
- 16 test cases across 7 categories: reasoning, coding, analysis, creative, instruction-following, knowledge, practical, edge cases
- Grader: reasoning (Qwen3.5-27B-FP8) at temperature=0
- Models:
  - `reasoning`: Qwen3.5-27B-FP8 TP=4 (FOUNDRY, 4x5070Ti)
  - `creative`: Qwen3.5-35B-A3B-AWQ (WORKSHOP, 5090)
  - `coder`: Qwen3.5-35B-A3B-AWQ-4bit (FOUNDRY, 4090)

## Results

### Raw Results (affected by grading infrastructure issues)

| Model | Pass | Fail | Pass Rate |
|-------|------|------|-----------|
| reasoning | 8 | 8 | 50.0% |
| creative | 9 | 7 | 56.2% |
| coder | 7 | 9 | 43.8% |
| **Total** | **24** | **24** | **50.0%** |

### Actual Results (excluding 19 grading failures)

21 of 48 assertions failed because the grading model's thinking traces consumed max_tokens (1024) before producing the JSON verdict. These are infrastructure failures, not model quality issues.

| Model | Pass | Genuine Fail | Grading Fail | Actual Pass Rate |
|-------|------|-------------|-------------|-----------------|
| reasoning | 8 | 2 | 6 | 80.0% (8/10) |
| creative | 9 | 0 | 7 | 100.0% (9/9) |
| coder | 7 | 3 | 6 | 70.0% (7/10) |
| **Total** | **24** | **5** | **19** | **82.8% (24/29)** |

### Per-Prompt Breakdown

| Prompt | reasoning | creative | coder |
|--------|-----------|----------|-------|
| Farmer puzzle (15 animals, 44 legs) | PASS | PASS | GRADE_FAIL |
| Widget factory (5 machines) | PASS | GRADE_FAIL | PASS |
| TCP vs UDP | PASS | PASS | PASS |
| LCS algorithm | PASS | PASS | FAIL |
| Dict lookup complexity | FAIL | PASS | FAIL |
| Microservices vs monolith | GRADE_FAIL | GRADE_FAIL | PASS |
| SQLite vs PostgreSQL | GRADE_FAIL | GRADE_FAIL | GRADE_FAIL |
| Haiku (3 AM debugging) | GRADE_FAIL | PASS | FAIL |
| Mars sunset | PASS | GRADE_FAIL | GRADE_FAIL |
| Self-hosting pros/cons | PASS | PASS | PASS |
| Transformer attention | GRADE_FAIL | GRADE_FAIL | GRADE_FAIL |
| RLHF explanation | GRADE_FAIL | GRADE_FAIL | GRADE_FAIL |
| Bash find one-liner | PASS | PASS | PASS |
| JSON to markdown table | PASS | PASS | PASS |
| Suggest something interesting | GRADE_FAIL | GRADE_FAIL | GRADE_FAIL |
| Empty input | FAIL | PASS | PASS |

## Grading Infrastructure Issue

The `reasoning` model used as grader outputs thinking traces as plain text (not `<think>` tags), consuming the 1024 max_tokens before producing the required JSON verdict. This affected 19/48 assertions (40%).

**Fix applied to config (v3):**
1. `enable_thinking: false` for all providers and grader via `extra_body.chat_template_kwargs`
2. `max_tokens: 2048` for grader
3. Enhanced transform to strip both `<think>` tags and plain-text thinking traces

## Genuine Failures (5 total)

1. **reasoning — dict complexity**: Likely missing O(n) worst case detail
2. **reasoning — empty input**: Not handled gracefully
3. **coder — LCS algorithm**: Code quality issue (O(mn) DP solution expected)
4. **coder — dict complexity**: Same as reasoning
5. **coder — haiku**: Thinking trace leaked into output (format failure)

## Key Findings

1. **creative (35B-A3B-AWQ on 5090) is the strongest model** — 100% on all gradable assertions
2. **reasoning (27B-FP8 TP=4) is solid** — 80% with 2 genuine failures, both on edge cases
3. **coder (35B-A3B-AWQ on 4090) needs tuning** — 70% with 3 genuine failures, likely needs `enable_thinking: false` to prevent thinking trace leakage
4. **All 3 models handle standard tasks well** — TCP/UDP, bash, JSON, pros/cons, and practical tasks all pass across the board
5. **Routing recommendation unchanged**: Route on load/latency, not quality. creative is best for most tasks.

## Stats
- Total tokens: 43,050 eval + 86,256 grading = 129,306
- Duration: 974s (16.2 minutes)
- Zero errors (all 48 prompts completed)

## Comparison to Previous Eval (2026-03-09)

| Metric | 2026-03-09 (2 models) | 2026-03-14 (3 models) |
|--------|----------------------|----------------------|
| Models | reasoning + creative | + coder |
| Grader | fast (8B) | reasoning (27B) |
| Raw pass rate | 93.8% | 50.0% |
| Actual pass rate | ~100% (rubric bug) | 82.8% (grading infra issue) |
| Grading failures | 0 (but rubric was wrong) | 19 (thinking trace overflow) |

The v3 config fix should resolve grading issues for clean future runs.

Last updated: 2026-03-14
