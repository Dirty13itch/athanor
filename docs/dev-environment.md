# DEV Environment — Tool Stack

*Everything installed on the DEV machine (Windows 11 IoT LTSC, WSL2 Ubuntu 24.04), how each tool fits into the Athanor workflow, and what's bookmarked for later.*

---

## Philosophy: The Fallback Chain

Claude Code (Anthropic Max subscription) is the primary agent. The stack has eight layers of fallback before hitting pay-per-token, plus local vLLM as the ninth (infinite, free). No single provider failure stops work.

```
Claude Code (Max sub) → hit quota?
  → Claude Code Router routes to GLM-5 or OpenRouter
    → GLM-5 quota exhausted?
      → Codex CLI (ChatGPT sub)
        → Kimi CLI (Kimi sub, K2.5 thinking model)
          → Gemini CLI (FREE, 1000 req/day)
            → OpenCode (any API key, 75+ providers)
              → Aider (any API key, git-native)
                → Local vLLM on Athanor (infinite, zero cost)
```

---

## Currently Installed and Working

### Claude Code (PRIMARY)

- **Auth:** Anthropic Max subscription (OAuth)
- **Alias:** `cc`
- **Config:** `--dangerously-skip-permissions` for autonomous mode. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`. Agent Teams via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- **Limitations:** Anthropic models only (without CCR). Quota resets periodically.

### Claude Code Router (CCR)

- **Alias:** `ccc` (launches `ccr code`)
- **Config:** `~/.claude-code-router/config.json` — routes default to Anthropic, background tasks to OpenRouter, reasoning to Anthropic, long-context to OpenRouter.
- **When to use:** When Max quota is exhausted, or when a different model is better for the task.

### Aider

- **Auth:** Any API key (OpenRouter, GLM, local vLLM)
- **Alias:** `aider-glm()`, `aider-or()` shell functions
- **Why for Athanor:** Local-model coding fallback. Point at `http://192.168.1.244:8000/v1` (Node 1) or `http://192.168.1.225:8000/v1` (Node 2) for zero-cloud coding. Also useful for EoBQ work with abliterated models.

### OpenCode

- **Alias:** `oc`, `opencode-glm()`, `opencode-or()` shell functions
- **Why:** Swiss Army knife. 75+ providers, LSP integration, multi-session, MCP support. 100K+ GitHub stars.

### Codex CLI

- **Auth:** ChatGPT subscription (OAuth)
- **When to use:** Third in fallback chain.

### Gemini CLI

- **Auth:** Free (shaunulrich11@gmail.com)
- **Alias:** `gc`
- **Why:** Free fallback with 1M token context window. 60 req/min, 1000 req/day.

### Kimi CLI

- **Auth:** MoonshotAI
- **Alias:** `km`
- **Why:** K2.5 is a strong reasoning model for complex architectural thinking.

---

## API Keys and Provider Configuration

In `.bashrc`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...    # Universal fallback
GLM_API_KEY=729e0074ce...           # GLM Coding Plan Pro ($10/mo)
GITHUB_TOKEN=github_pat_11B...      # GitHub MCP + repo access
GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

---

## Subscriptions

| Service | Cost | Status |
|---------|------|--------|
| Anthropic Claude Max | $200/mo | Active |
| GLM Coding Plan Pro | $10/mo | Active |
| ChatGPT (Codex CLI) | varies | Active |
| Kimi (MoonshotAI) | varies | Authenticated |
| OpenRouter | pay-per-use | Account + credits |
| Gemini CLI | **FREE** | Authenticated |

---

## Bookmarked — Install When Local vLLM Running

### Goose (Block)

First candidate for an agent running entirely on Athanor hardware. Ollama/Docker Model Runner integration → point at local vLLM for autonomous tasks (media management, home automation, system monitoring). **Install on Node 1 via Docker.**

### OpenClaw

The human-facing layer of Athanor. Always-on interface: WhatsApp, Discord, Slack, Telegram, Signal, iMessage. Routes requests to specialist agents. "Hey Athanor, what's playing on Plex?" → OpenClaw → Media Agent → answer. **Install on VAULT or Node 1.** Trigger: when vLLM + 6 LangGraph agents are operational.

### OpenWork

WhatsApp bridge + skill system. Evaluate against OpenClaw as alternative human interface.

### Eigent

Multi-agent orchestration platform. Reference architecture for the specialist dispatch pattern. Evaluate whether its patterns are worth stealing for LangGraph agents.

---

## Bookmarked — Install When Specific Need Arises

| Tool | Trigger | Why |
|------|---------|-----|
| **Cipher** | 3+ coding agents active simultaneously | Cross-tool memory layer (MCP-based). Dual memory (System 1 + System 2). Supports Ollama embeddings + Neo4j. |
| **Plandex** | Single task touching 50+ files | 2M token context, self-hosted Docker, tree-sitter indexing, cumulative diff sandbox. |
| **Deep Trilogy** | Starting major new component (EoBQ engine, Kindred) | `/deep-project` → `/deep-plan` → `/deep-implement`. Multi-LLM review catches blind spots. |
| **Continue.dev** | Automation pipelines need code execution | Headless async agent mode for CI/CD. |

---

## Decided Against (Don't Revisit)

| Tool | Why Not |
|------|---------|
| Claude Squad | Agent Teams (built-in to Claude Code) replaces it |
| Claude Flow | Overkill orchestration for one person |
| Amp (Sourcegraph) | Cloud-locked, no local model support |
| Kilo Code | Redundant with Roo Code |
| Kiro (AWS) | Separate IDE, doesn't fit terminal-first workflow |
| OhMyOpenCode | ToS issues, excessive token burn ($15-20 in 30 min) |
| 1Code | Claude-only UI wrapper, no unique value |
| Dify / n8n / Flowise | Agent GUIs that replace LangGraph, don't complement it |
| AutoGen Studio | Own framework — would replace LangGraph, not sit on top |
| CrewAI Studio | Same problem — own framework. Also has telemetry. |
| Droid (Factory) | Model-locked after trial. Incompatible with sovereignty. |
| Copilot CLI | GitHub/MS ecosystem lock |
| Amazon Q CLI | AWS ecosystem lock-in |

---

## Patterns to Steal (Don't Install, Take the Design)

| Tool | Pattern |
|------|---------|
| Roo Code Custom Modes | Specialist personas as modes → agent role definitions |
| CCPM | PRD → Epic → Task → Code traceability chain |
| Continuous-Claude | Ledger-based context handoffs — write state to disk before compaction |
| Kiro spec-driven dev | requirements.md → design.md → tasks automatic decomposition |
| Eigent orchestrator | Orchestrator → specialist dispatch with task routing |
| Cipher dual memory | System 1 (knowledge) + System 2 (reasoning traces) |
| Letta three-tier memory | Core + archival + recall — maps to Knowledge Agent design |

---

## Cross-Cutting Observations

- **MCP is the integration standard.** Block and Anthropic co-developed it. Now under Linux Foundation AAIF. LangGraph agents should expose MCP interfaces.
- **AGENTS.md is the configuration standard.** Supported by Cursor, Windsurf, Kilo, and growing. Athanor uses both CLAUDE.md (project-specific) and AGENTS.md (cross-tool portable).
- **Model-agnostic is the critical filter.** If a tool can't point at `localhost:8000` (vLLM), it's incompatible with production Athanor. ~60% of the landscape fails this test.
- **The ecosystem is consolidating:** Coding agents (Aider, OpenCode, Claude Code, Goose), Frameworks (LangGraph won), Standards (MCP, AGENTS.md, Agent File .af).

---

## VS Code Extensions

| Extension | Purpose |
|-----------|---------|
| Remote-WSL | Connect VS Code to WSL2 Ubuntu |
| Roo Code | Multi-model AI agent in VS Code |
| GitLens | Enhanced git visualization |
| Docker | Container management UI |
