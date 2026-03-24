# Athanor Daily Operations Guide

*How to use the system every day. No jargon, no theory — just what to do.*

---

## Starting Your Day

1. **Open terminal on DESK** (Windows Terminal, WSL, or SSH client)
2. **Connect to DEV:** `ssh dev` (or the tmux shortcut if configured)
3. **Launch Athanor:** `~/bin/athanor` — this opens (or reattaches) the ATHANOR tmux session with two windows: `claude` (auto-starts Claude Code) and `shell` (plain terminal)
4. **Morning check:** Type `/morning` in Claude Code — this runs a comprehensive health check showing overnight agent activity, GPU status, alerts, and what needs attention
5. **Quick check (anytime):** Type `/health` for a fast status table

## Which Tool Do I Use?

**Default: Claude Code.** You're already in it. It handles 80% of work.

**For specific patterns, Claude Code will SUGGEST the right tool:**

| What you're doing | Best tool | How to start it |
|-------------------|-----------|-----------------|
| Complex design/architecture | Stay in Claude Code | Just keep talking |
| Quick question | Gemini CLI | `gc "your question"` |
| Edit 20+ files systematically | Aider | `aider` (already configured for local models) |
| Visual IDE work with model routing | Roo Code | Open VS Code → Roo Code panel |
| Terminal-heavy debugging | Codex CLI | `codex` |
| Repeatable task you've done before | Goose | `goose run recipe-name` |
| Massive breadth research (100 parallel) | Kimi Code | `kimi "your research topic"` |
| Deep research report | Perplexity | Open perplexity.ai, use Deep Research |
| When Claude hits rate limits | Auto-switches via CCR | Transparent — `ccc` if manual |

## The Fallback Chain

If your primary tool hits a limit, the system automatically falls through:

```
Claude Code (Opus) → hit quota?
  → CCR routes to another provider
    → Codex CLI (GPT-5.4, ChatGPT Pro sub)
      → Kimi CLI (K2.5, Allegretto sub)
        → Gemini CLI (FREE, 1000/day)
          → OpenCode (any provider)
            → Aider (local models, $0)
              → Local vLLM directly ($0, infinite)
```

You never pay per-token. Every step is either a flat-rate subscription or local hardware.

## Common Commands

| Command | What it does |
|---------|-------------|
| `/morning` | Full morning standup — overnight report, health, alerts, tasks |
| `/health` | Quick cluster health table |
| `/status` | System status summary |
| `/audit` | Deep infrastructure audit |
| `/deploy` | Deploy a service or container |
| `/build` | Continue autonomous build from BUILD-MANIFEST |
| `/orient` | SOAR cycle — scan cluster, orient priorities, act |
| `/research` | Deep research with sources |
| `/decide` | Architecture decision with ADR |

## Working with Local Models ($0)

All local model work routes through LiteLLM (VAULT:4000). You don't need to know which GPU handles what — just use the alias:

| Alias | What it gives you |
|-------|-------------------|
| `reasoning` | Best local quality (Qwen3.5-27B, all 27B params active) |
| `coder` | Fast code generation (Qwen3.5-35B MoE, 3B active) |
| `worker` | General tasks (same 35B model, WORKSHOP) |
| `creative` | Uncensored creative (same model) |
| `fast` | Quick responses (same model, may change to 9B) |
| `embedding` | Text-to-vector (for search, RAG) |

**To use a local model directly:** Open a separate Claude Code session pointing at LiteLLM:
```bash
ANTHROPIC_BASE_URL=http://192.168.1.203:4000 claude
```
This gives you unlimited local inference at $0.

## The Agents (Background Robots)

9 agents run 24/7 on FOUNDRY without your input:

| Agent | Schedule | What it does |
|-------|----------|-------------|
| General Assistant | 30 min | Checks services, GPU, disk |
| Media Agent | 15 min | Manages Sonarr/Radarr/Plex |
| Home Agent | 5 min | Controls Home Assistant |
| Creative Agent | 4 hr | Generates images (auto_gen pipeline) |
| Research Agent | 2 hr | Web research tasks |
| Knowledge Agent | 1 hr | Indexes documents |
| Coding Agent | 3 hr | Background dev tasks |
| Stash Agent | 6 hr | Media library management |
| Data Curator | 6 hr | Document processing |

**Check agent status:** `/health` or `curl http://192.168.1.244:9000/health`
**See recent tasks:** `curl http://192.168.1.244:9000/v1/tasks?limit=10`

## What to Do When Something Breaks

**First:** Check if it's a known issue — type `/health` in Claude Code.

**Common issues and fixes:**

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Claude Code feels slow | LiteLLM fallback waiting 24 min | Being fixed (stream_timeout) |
| No images being generated | Auto_gen LLM endpoint dead | Fix: update LLM_API_URL in .env |
| Agents not returning results | Qdrant URL wrong | Fix: update ATHANOR_QDRANT_URL |
| Can't see what AI calls are happening | Langfuse keys empty | Fix: set keys on LiteLLM container |
| WORKSHOP model loads slowly | Loading over NFS (26 seconds) | Fix: rsync to local NVMe (1.9s) |

**If a node is down:**
```bash
ssh foundry "echo ok"   # check FOUNDRY
ssh workshop "echo ok"  # check WORKSHOP  
ssh dev "echo ok"       # check DEV (you're probably already on it)
ssh root@192.168.1.203 "echo ok"  # check VAULT
```

**Full disaster recovery:** See `docs/RECOVERY.md` — has step-by-step for every scenario.

## Key URLs (Bookmark These)

| Service | URL | What |
|---------|-----|------|
| Dashboard | http://192.168.1.225:3001 | Main Athanor web UI |
| Open WebUI | http://192.168.1.225:3000 | Chat with local models in browser |
| Grafana | http://192.168.1.203:3000 | Metrics dashboards |
| Langfuse | http://192.168.1.203:3030 | AI call tracing |
| ComfyUI | http://192.168.1.225:8188 | Image generation |
| Stash | http://192.168.1.203:9999 | Media library |
| Home Assistant | http://192.168.1.203:8123 | Home automation |
| EoBQ App | http://192.168.1.225:3002 | Empire of Broken Queens |
| Prometheus | http://192.168.1.203:9090 | Monitoring alerts |

## Subscriptions — How to Maximize Each One

All subscriptions are flat-rate. Limits reset. Use them ALL.

| Sub | Monthly | What to use it for | Limit resets |
|-----|---------|-------------------|-------------|
| Claude Max 20x | $200 | Primary everything | ~900 msgs/5hr rolling |
| ChatGPT Pro | $200 | Codex terminal, GPT-5.4 computer use | Rolling |
| Gemini Advanced | $20 | Quick questions, 1M context, research | 1000/day |
| Copilot Pro+ | $33 | IDE autocomplete, GitHub Spark | 1500 premium/mo |
| Z.ai GLM Pro | $30 | Fact-checking, classification | Monthly |
| Perplexity Pro | $20 | Deep Research (Opus-powered) | Unlimited |
| Kimi Code | $19 | Agent Swarm (100 parallel agents) | Weekly |
| Venice AI Pro | $12 | Uncensored API (cancels Jul 2026) | Credits |
| Qwen Code | $10 | DashScope access, free third-party models | 90K req/mo |
| Mistral | $0 | Codestral autocomplete (#1 ranked) | Free |
