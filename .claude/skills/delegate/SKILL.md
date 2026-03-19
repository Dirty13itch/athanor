---
name: delegate
description: Auto-route tasks to the optimal tool, model, and subscription. Cloud-first with local backbone. Content governance enforced.
triggers:
  - "delegate"
  - "local model"
  - "offload"
  - "route"
  - "which tool"
---

# Smart Task Routing

Automatically pick the best tool, model, and subscription for any task. The user never decides manually.

## Task: $ARGUMENTS

## Step 1: Content Classification

| Class | Route | Examples |
|-------|-------|---------|
| cloud_safe | Any tool/sub | Open-source code, docs, public data |
| private_but_cloud_allowed | Trusted cloud or local | Business data, client info |
| hybrid_abstractable | Cloud sees structure only, raw stays local | Sensitive designs |
| refusal_sensitive | LOCAL ONLY (JOSIEFIED/Dolphin) | NSFW, adult content, EoBQ |
| sovereign_only | LOCAL ONLY | Pen testing, credentials, hacking |

If refusal_sensitive or sovereign_only → skip to Step 3 (local routing).

## Step 2: Cloud Subscription Routing (burn free tiers first)

| Task Pattern | Best Tool | Subscription |
|---|---|---|
| Quick factual question | Gemini CLI | FREE (1000/day) |
| IDE autocomplete | Codestral | FREE (Mistral) |
| Complex architecture | Claude Code (Opus) | Max 20x |
| Multi-file reasoning | Claude Code Agent Teams | Max 20x |
| Terminal debugging | Codex CLI | ChatGPT Pro |
| Computer-use/visual | Codex CLI | ChatGPT Pro (GPT-5.4) |
| Hard math/algorithm | o3-pro via ChatGPT | ChatGPT Pro |
| Deep research report | Perplexity Deep Research | Perplexity Pro |
| Massive breadth search | Kimi Agent Swarm | Kimi Allegretto |
| Fact checking | Z.ai GLM | GLM Pro |
| Visual dev (IDE) | Roo Code | Per-mode routing |
| Structured file edits | Aider | LiteLLM → local ($0) |
| PR review | CodeRabbit | FREE |
| Repeatable recipe | Goose | LiteLLM → local ($0) |

Use Sonnet 80% of the time in Claude Code (3x less quota than Opus).

## Step 3: Local Model Routing ($0, unlimited)

| Task Type | Tool | Model | Endpoint |
|---|---|---|---|
| General/reasoning | LiteLLM | Qwen3.5-27B-FP8 | FOUNDRY:8000 |
| Code generation | LiteLLM | Qwen3.5-35B-A3B | FOUNDRY:8006 |
| NSFW/uncensored | LiteLLM | JOSIEFIED-Qwen3-8B | WORKSHOP:11434 |
| Embedding/search | Direct | Qwen3-Embedding-0.6B | DEV:8001 |
| Image scoring | Direct | Aesthetic Predictor V2.5 | WORKSHOP:8050 |
| Image generation | ComfyUI | FLUX + PuLID | WORKSHOP:8188 |

## Step 4: Autonomous Agent Routing

For background/autonomous tasks, route to LangGraph agents via MCP:
- `mcp__athanor-agents__coding_generate` — code tasks
- `mcp__athanor-agents__coding_review` — review
- `mcp__athanor-agents__deep_research` — research
- Health/monitoring → general-assistant agent (runs on schedule)

## Quality Gate (always)

Review all delegated output before accepting. Check: correctness, style, security, completeness.
