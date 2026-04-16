# Claude Code Thinking Mechanisms: Ultrathink, Effort, and Extended Thinking

**Date:** 2026-02-26
**Status:** Complete
**Purpose:** Determine what "ultrathink" and related thinking keywords actually do in Claude Code, what mechanisms control Claude's reasoning depth, and what the current best practices are.

---

## Executive Summary

"Ultrathink" was a real, functional feature in Claude Code from mid-2025 through January 16, 2026. It was a keyword detected by Claude Code's client-side JavaScript that set the API's `budget_tokens` parameter to 31,999 (the maximum thinking budget). **It has been deprecated.** Extended thinking is now enabled by default at maximum budget for all supported models.

The current control mechanism is the **`/effort` command** (or `effortLevel` setting), which maps to Anthropic's new **adaptive thinking** API (`thinking: {type: "adaptive"}`). This replaced the old `budget_tokens` system for Opus 4.6 and Sonnet 4.6. The keywords "think", "think hard", "ultrathink", etc. are now treated as regular prompt text and do not allocate thinking tokens.

---

## 1. Did "Ultrathink" Actually Do Something?

**Yes, it was real and verified.** It was not a community myth.

### How It Worked (Pre-Deprecation)

The Claude Code npm package contained obfuscated JavaScript that scanned user prompts for specific keywords. When detected, it called an internal function (`tengu_thinking`) to set the thinking token budget before sending the API request.

The code mapped keywords to three tiers:

| Tier | Trigger Keywords | Token Budget |
|------|-----------------|--------------|
| Low | "think" | 4,000 tokens |
| Medium | "think hard", "think about it", "think a lot", "think deeply", "megathink" | 10,000 tokens |
| High | "think harder", "think intensely", "think longer", "think really hard", "think super hard", "think very hard", "ultrathink" | 31,999 tokens |

Source: Reverse-engineered from Claude Code client JS, confirmed by Anthropic's engineering blog ("Claude Code: Best practices for agentic coding") which states: "These specific phrases are mapped directly to increasing levels of thinking budget: 'think' < 'think hard' < 'think harder' < 'ultrathink.'"

**Discrepancy noted:** Anthropic's documentation claimed four levels, but code analysis showed only three distinct budget values (4K, 10K, 31,999). The "think hard" and "think harder" levels mapped to medium (10K) and high (31,999) respectively.

### Timeline

| Date | Event |
|------|-------|
| ~Mid 2025 | Keywords first discovered in Claude Code source |
| May 2025 | Anthropic's engineering blog acknowledges the feature |
| Nov 2025 | Claude Code v2.0 adds Tab toggle for thinking; keyword levels deprecated |
| Jan 16, 2026 | Ultrathink officially deprecated; thinking enabled by default |
| Feb 2026 | `/effort` command and adaptive thinking are the current mechanism |

Sources:
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://news.ycombinator.com/item?id=43739997
- https://decodeclaude.com/ultrathink-deprecated/

---

## 2. Current Mechanisms for Controlling Thinking Depth

### 2.1 The `/effort` Command (Claude Code)

The primary control surface in Claude Code as of February 2026.

| Level | Behavior | Use Case |
|-------|----------|----------|
| `low` | Minimizes thinking; skips for simple tasks | Syntax fixes, linting, simple refactors |
| `medium` | Moderate thinking; may skip for trivial queries | Agentic coding, tool-heavy workflows |
| `high` (default) | Deep thinking on most tasks | Complex reasoning, architecture decisions |
| `max` | No constraints on thinking depth (Opus 4.6 only) | Deepest possible reasoning |

**How to set it:**
- Interactive: `/model` then use left/right arrow keys on the effort slider
- Environment variable: `CLAUDE_CODE_EFFORT_LEVEL=low|medium|high`
- Settings file: `"effortLevel": "high"` in `~/.claude/settings.json`

### 2.2 Adaptive Thinking (API Level)

The underlying API mechanism. For Opus 4.6 and Sonnet 4.6, `thinking: {type: "adaptive"}` replaces the old `thinking: {type: "enabled", budget_tokens: N}`.

Key differences from manual/budget-based thinking:
- Claude decides **whether and how much** to think based on query complexity
- At `high`/`max` effort, Claude almost always thinks
- At `low` effort, Claude may skip thinking entirely for simple queries
- Automatically enables **interleaved thinking** (thinking between tool calls)
- No need to manually pass thinking blocks back in multi-turn conversations

```python
# Current recommended approach (API)
client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
    messages=[{"role": "user", "content": "..."}],
)
```

### 2.3 MAX_THINKING_TOKENS (Environment Variable)

Still exists but behavior has changed:

- **On Opus 4.6 / Sonnet 4.6:** Ignored entirely, EXCEPT when set to `0` (which disables thinking)
- **On older models (Opus 4.5, Sonnet 4.5, etc.):** Controls the fixed thinking budget (1,024 to 31,999 tokens)
- **Known bug:** When set, every request becomes a thinking request, even trivial ones (GitHub issue #5257)

To disable adaptive thinking and revert to fixed budget behavior:
```bash
export CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1
```
Then MAX_THINKING_TOKENS controls the budget again.

### 2.4 Toggle Thinking On/Off

- Keyboard shortcut: `Option+T` (macOS) / `Alt+T` (Windows/Linux)
- `/config` menu: toggle `alwaysThinkingEnabled`
- Settings: `"alwaysThinkingEnabled": true` in `~/.claude/settings.json`

### 2.5 Summary of All Environment Variables

| Variable | Effect |
|----------|--------|
| `CLAUDE_CODE_EFFORT_LEVEL` | Set effort: `low`, `medium`, `high` |
| `MAX_THINKING_TOKENS` | Limit thinking budget (ignored on 4.6 models unless 0) |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | Set to `1` to revert to fixed budget thinking |

---

## 3. Do Prompt Phrases Trigger Deeper Reasoning?

### In Claude Code: No (as of January 2026)

From the official Claude Code documentation (code.claude.com):

> "Phrases like 'think', 'think hard', 'ultrathink', and 'think more' are interpreted as regular prompt instructions and don't allocate thinking tokens."

This is definitive. The keywords no longer trigger any special behavior in the client-side code.

### In the API / Claude Chat: Never Did

The keyword system was always a Claude Code client-side feature. It never worked in:
- claude.ai (web interface)
- The Messages API directly
- Third-party tools using the API

### What Does Work for Prompt-Based Reasoning Control

According to Anthropic's official prompt engineering documentation:

1. **"Think thoroughly"** -- As a prompt instruction (not a keyword trigger), telling Claude to "think thoroughly" often produces better reasoning than prescribing step-by-step plans. Claude's reasoning frequently exceeds what a human would prescribe.

2. **Do NOT say "think step by step" when thinking is enabled** -- This is explicitly called out as redundant and wasteful. When extended thinking is active, the model manages its own reasoning budget.

3. **Self-check instructions** -- Appending "Before you finish, verify your answer against [test criteria]" reliably catches errors in coding and math.

4. **`<thinking>` tags in few-shot examples** -- Using `<thinking>` tags in examples teaches Claude the reasoning pattern it should follow.

5. **Adaptive thinking is promptable** -- You can add system prompt guidance like:
   ```
   Extended thinking adds latency and should only be used when it
   will meaningfully improve answer quality -- typically for problems
   that require multi-step reasoning. When in doubt, respond directly.
   ```

6. **Word sensitivity note:** When thinking is DISABLED, Claude Opus 4.5 is "particularly sensitive to the word 'think' and its variants." Use alternatives like "consider," "evaluate," or "reason through."

Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices
- https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking
- https://code.claude.com/docs/en/common-workflows

---

## 4. MAX_THINKING_TOKENS: Details and Optimal Values

### What It Does

Sets the maximum number of tokens Claude can use for internal reasoning before producing a visible response. The thinking tokens are:
- Charged as output tokens
- Not visible in the final response (Claude 4 models show summarized thinking, not full thinking)
- Subject to a minimum of 1,024 tokens

### Values and Context

| Setting | Budget | Use Case |
|---------|--------|----------|
| 0 | Disabled | No thinking at all |
| 1,024 | Minimum | Very simple tasks |
| 4,000 | Low (old "think") | Basic debugging |
| 10,000 | Medium (old "megathink") | Moderate reasoning |
| 31,999 | Maximum (old "ultrathink") | Complex architecture, multi-file |
| 63,999 | Extended max (64K output models) | Extreme reasoning (unofficial) |

**Important:** The budget is a **target, not a strict limit**. Actual token usage may vary.

### On Current Models (4.6)

MAX_THINKING_TOKENS is effectively irrelevant for Opus 4.6 and Sonnet 4.6 unless:
- Set to `0` (disables thinking)
- Combined with `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` (reverts to fixed budget)

The `/effort` parameter is the intended replacement.

### Cost Implications

One Hacker News commenter noted that setting MAX_THINKING_TOKENS=10000 provided "roughly a 70% reduction in hidden thinking cost per request" compared to the default 31,999. However, this was for pre-4.6 models. With Opus 4.6's adaptive thinking, the model self-allocates, so the cost savings from lower effort levels are more natural.

Sources:
- https://code.claude.com/docs/en/common-workflows
- https://code.claude.com/docs/en/model-config
- https://github.com/anthropics/claude-code/issues/376

---

## 5. Evidence That Thinking Depth Affects Quality

### Anthropic's Published Benchmarks

**GPQA (Graduate-level reasoning):**
- Without extended thinking: 78.2%
- With extended thinking: 84.8%
- Improvement: +6.6 percentage points

**Math (AIME):**
- Claude's accuracy improves **logarithmically** with thinking token budget
- Confirmed by Anthropic: more tokens = better results, but with diminishing returns

**SWE-bench Verified (real-world software bugs):**
- Claude 3.7 Sonnet: 62.3% with extended thinking
- Significant improvement over non-thinking mode

### Third-Party A/B Tests

**Qodo (400 real PRs, code review):**
- Thinking vs. non-thinking showed measurable quality improvements
- Haiku 4.5 with thinking outperformed Sonnet 4.5 with thinking in 58% of comparisons (quality score 7.29 vs 6.60)
- Takeaway: thinking helps, but model choice matters more than thinking budget alone

**Anthropic's "think" tool study:**
- The "think" tool (a structured pause mechanism) combined with optimized prompting delivered the strongest performance "by a significant margin" over extended thinking mode alone for customer service tasks
- Suggests that **how** Claude thinks matters as much as **how much**

### Community Reports (Anecdotal but Consistent)

GitHub issue #19098 documented widespread quality complaints after ultrathink was deprecated:
- Users reported "92% of sessions requiring explicit thinking correction"
- "7+ redundant operations per task before root cause analysis"
- Some attributed this to automatic thinking being less effective than explicit maximum budget

However, the issue was closed as "Completed" on Feb 4, 2026, suggesting Anthropic addressed the underlying concerns (possibly through the `/effort` system).

Sources:
- https://www.anthropic.com/news/visible-extended-thinking
- https://www.qodo.ai/blog/thinking-vs-thinking-benchmarking-claude-haiku-4-5-and-sonnet-4-5-on-400-real-prs/
- https://www.anthropic.com/engineering/claude-think-tool
- https://github.com/anthropics/claude-code/issues/19098

---

## 6. Verified Facts vs. Community Speculation

### Verified (Official Sources)

1. Ultrathink WAS a real feature that set budget_tokens to 31,999
2. It was deprecated January 16, 2026
3. Extended thinking is now on by default for supported models
4. `/effort` (low/medium/high/max) is the current control mechanism
5. Adaptive thinking (`thinking: {type: "adaptive"}`) is the recommended API mode for 4.6 models
6. The `effort` parameter affects ALL tokens: thinking, text, and tool calls
7. `max` effort is Opus 4.6 only
8. Thinking tokens are billed at output token rates even though summaries are shown
9. Mathematical accuracy improves logarithmically with thinking budget
10. "Think step by step" is redundant when extended thinking is enabled

### Community Speculation (Unverified)

1. **"Smart routing" / model substitution theory** -- Some users believe Claude Code routes "simple" requests to cheaper models (Haiku) even when Opus is selected. Anthropic has not confirmed this for the main model, though subagent routing to Haiku is documented and intentional.

2. **"Ultrathink forces full Opus engagement"** -- The theory that ultrathink bypassed hypothetical model routing. No evidence beyond correlation with better subjective results.

3. **"63,999 thinking tokens on 64K output models"** -- One source claims setting MAX_THINKING_TOKENS=63999 doubles thinking capacity on 64K-output models. This is plausible given the API's max_tokens constraint but not confirmed in official docs.

4. **"Stacking keywords compounds thinking"** -- Confirmed FALSE. Only the highest-tier keyword detected is used; multiple keywords do not stack.

---

## 7. Recommendations for Athanor

### For Claude Code Usage (Current)

1. **Do not use "ultrathink" or thinking keywords in prompts.** They are dead. They are parsed as regular text. They waste prompt tokens.

2. **Use `/effort` to control thinking depth:**
   - Default (`high`) for most work
   - `max` for complex architecture decisions, multi-file refactors, deep debugging
   - `medium` for routine coding tasks where speed matters
   - `low` for simple lookups, quick fixes

3. **Set effort in settings for agents:**
   ```json
   {
     "effortLevel": "high",
     "alwaysThinkingEnabled": true
   }
   ```

4. **For agent subagents / automated tasks**, consider `medium` to reduce cost and latency.

5. **Use self-check prompts** instead of thinking keywords: "Before finalizing, verify your solution against [criteria]."

### For LiteLLM / API Integration

The effort parameter is passed via `output_config`:
```python
output_config={"effort": "high"}
```

LiteLLM supports this as `reasoning_effort` per their Anthropic provider docs:
- https://docs.litellm.ai/docs/providers/anthropic_effort

### For Custom Agent Prompts

Do NOT include instructions like "think step by step" or "think deeply" in system prompts when thinking mode is enabled. Instead:
- Provide clear success criteria
- Use "verify your answer against [criteria]" patterns
- Use `<thinking>` tags in few-shot examples if you want to model reasoning patterns

---

## Open Questions

1. **Does effort=max on Opus 4.6 genuinely outperform effort=high for complex tasks?** No public benchmarks compare these two levels specifically. Worth testing on our own workloads.

2. **What is the actual token cost difference between effort levels?** Anthropic provides no hard numbers. We could measure this by monitoring usage at different effort settings.

3. **Will the `max` effort level be extended to Sonnet 4.6?** Currently Opus-only. No public timeline.

---

Last updated: 2026-02-26
