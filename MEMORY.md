# Athanor Session Memory

> **Status:** Historical working memory only.
> **Current truth lives here:** `STATUS.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`, `python scripts/session_restart_brief.py --refresh`, `reports/ralph-loop/latest.json`, `reports/truth-inventory/finish-scoreboard.json`, `reports/truth-inventory/runtime-packet-inbox.json`, and `reports/truth-inventory/`.
> **Purpose:** preserve older session notes and context without presenting live runtime, provider, or queue truth.
> **Hard boundary:** do not reuse runtime facts, provider posture, blocker state, credentials notes, or operational steps below without rechecking current canonical surfaces first.

*Historical working memory. Prefer `C:\Athanor\STATUS.md` and current truth-inventory artifacts when they disagree. Lightly corrected on 2026-04-14 to avoid stale runtime assumptions.*

---

## System State (verified via SSH March 18)

### Cluster
| Node | IP | Role | GPUs | Key Services |
|------|-----|------|------|-------------|
| FOUNDRY | .244 | Heavy compute | 4x5070Ti (TP=4) + 4090 | vllm-coordinator:8000 (degraded secondary lineage), dolphin text lane:8100, agents:9000, gpu-orch:9200 |
| WORKSHOP | .225 | Creative | 5090 + 5060Ti | workshop-vision:8012, ComfyUI:8188, EoBQ:3002 |
| DEV | .189 | Ops center | 5060Ti | Gateway:8700, Embedding:8001, Reranker:8003, all coding CLIs |
| VAULT | .203 | Storage | ARC A380 | LiteLLM:4000, 51+ containers, Langfuse:3030, full media stack |
| DESK | .50 | Windows | 3060 12GB | SSH terminal to DEV, VS Code Remote |

### Models Running (verified 2026-03-23)
- FOUNDRY legacy coordinator: Qwen3.5-27B-FP8 at port 8000 now lists models but is completion-degraded; treat as secondary lineage, not the primary text lane
- FOUNDRY 4090: devstral-small-2 (coder, port 8006)
- WORKSHOP 5090 worker lineage at 8010 is historical/retired until a future bounded restore ships with a real model directory
- WORKSHOP 5060Ti: ComfyUI (image gen)
- DEV: Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B
- **Ollama DISABLED on Workshop** (was conflicting with vLLM for GPU memory)

### Key Ports
LiteLLM:4000 | Agents:9000 | GPU-Orch:9200 | Gateway:8700 | ComfyUI:8188
Langfuse:3030 | Grafana:3000 | Prometheus:9090 | Stash:9999 | ntfy:8880
Scorer:8050 | Ollama:11434 | Dashboard:3001 | Seerr:5055 | Whisparr:6969

### vLLM
- Version: v0.16.1rc1.dev32 (custom NVIDIA build, NOT v0.13.0)
- Tool parser: qwen3_xml (NOT hermes)
- All Qwen3.5 models are natively multimodal VLMs

## Last Session: 2026-03-23 (Session 58 — System Recovery + Git Convergence)

### What happened
1. Workshop vLLM was down — Ollama displaced it from both GPUs. Stopped Ollama, disabled from boot, restarted vLLM.
2. GPU orchestrator crash-looping — Redis auth required but not configured. Fixed with password in URL.
3. Merged 365 commits from origin/main into local main. Resolved 3 EoBQ conflicts (accepted origin).
4. Re-applied Redis auth + Workshop port fixes on merged main.
5. All 10 service endpoints verified healthy. Pushed to GitHub.

### What's next
- **LTX 2.3: BLOCKED on Blackwell sm_120** — CUDA kernel error "no kernel image available". Wan2.x works. Need GGUF path or upstream fix.
- EoBQ SoulForge page built + TTS voice wired (Kokoro at :8200, 54 voices)
- Core memory system deployed (465 LOC, Redis-backed)
- ComfyUI models on Gen5 NVMe (208 GB), DEV models local
- All blocked items need Shaun (credentials, decisions, physical)

---

## Prior Session: 2026-03-18 (COO Architecture + Execution)

### Executed (19 actions)
1. Auto_gen LLM endpoint fixed (dead 12 days → 3 images generated)
2. Langfuse API keys set (dark 4 days → tracing active)
3. Agent Qdrant URL fixed (FOUNDRY→VAULT:6333) + timeout 600→1800s
4. WORKSHOP models rsynced to local Gen5 NVMe (14x faster)
5. LiteLLM routing overhauled (24min→10s failover, coding→:8006, vision→:8000)
6. MCP Tool Search fixed (auto:5→true)
7. vLLM swap-space added (pending restart)
8. GSD v1.26.0 installed
9. Crucible (4 containers) + old FOUNDRY Qdrant removed
10. Vision --language-model-only removed (pending restart)
11. vllm-node2 stopped, 5090 freed (32GB→2MB)
12. LiteLLM rerouted WORKSHOP→FOUNDRY
13-16. Whisparr, Bazarr, Recyclarr, Seerr deployed on VAULT
17. Aesthetic Predictor V2.5 deployed (WORKSHOP:8050, tested)
18. JOSIEFIED-Qwen3-8B deployed via Ollama (WORKSHOP:11434)
19. LiteLLM uncensored route → JOSIEFIED

### Documents Created
- docs/MASTER-PLAN.md (619 lines, canonical strategic reference)
- docs/superpowers/specs/2026-03-18-athanor-coo-architecture-FULL.md (tactical)
- docs/guides/ (4 guide documents)
- CLAUDE.md updated with cloud-first subscription strategy
- .claude/skills/delegate/SKILL.md updated with full routing matrix

## Blockers
- Install Roo Code (VS Code ext OR CLI headless mode)
- Set up CodeRabbit (app.coderabbit.ai)
- Schedule vLLM coordinator restart (vision + swap-space)
- Set up offsite backup (Duplicati → Backblaze B2)

## Next Actions
1. Set up Semantic Router on DEV (semantic-router installed, needs config)
2. Add APScheduler to LangGraph agent server
3. Set up first overnight autonomous coding run
4. Performer data merge (script ready)
5. Deploy Vaultwarden, Uptime Kuma, Headscale
6. LTX 2.3 video gen on WORKSHOP 5090
7. Merge automation-backbone branch

## Key Facts
- SSH WORKSHOP: user is athanor, NOT shaun
- VAULT SSH: use root@192.168.1.203
- LiteLLM auth: Bearer sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d
- Memory port: 8720 (NOT 8702)
- DEV NIC: 5GbE (NOT 5GbE)
- FOUNDRY PSU at 95% (cannot add GPUs)
- Design: cloud-first with local backbone (NOT local-first)

## Session 2026-03-19 Additions

### New Services Deployed
| Service | Location | Port | Status |
|---------|----------|------|--------|
| OpenFang v0.4.9 | DEV | 4200 | Running, Telegram @athanor_ops_bot |
| Semantic Router | DEV | 8060 | 5 routes, all-MiniLM-L6-v2 |
| Aesthetic Scorer | WORKSHOP | 8050 | V2.5, RTX 5060 Ti |
| Uptime Kuma | VAULT | 3009 | 8 monitors, admin/AthanorKuma2026\! |
| Vaultwarden | VAULT | 8222 | Password manager |
| Headscale | VAULT | 8443 | Mesh networking (needs node registration) |
| Alertmanager webhook | FOUNDRY | 9000 | /webhook/alertmanager on agent server |
| Cluster health timer | DEV | systemd | Every 5 min, ntfy alerts |

### OpenFang Config
- Binary: /usr/local/bin/openfang (Rust, not Docker)
- Config: ~/.openfang/config.toml (provider=ollama, model=qwen3:8b)
- CRITICAL: Per-agent config at ~/.openfang/agents/assistant/agent.toml OVERRIDES global. Must set valid provider there.
- Boot: /etc/cron.d/openfang-boot (nohup, TELEGRAM_BOT_TOKEN env)
- Ollama models on DEV: qwen3:8b, nomic-embed-text, dolphin-mistral:7b

### Greywall v0.2.7
- Binary: ~/.local/bin/greywall
- Deps: bubblewrap, socat (apt installed)
- Profile: ~/.config/greywall/claude-code.json
- Usage: `greywall --settings ~/.config/greywall/claude-code.json -- claude`

### Superset
- Cloned to ~/tools/superset, built with bun
- Electron desktop app — needs display, install on DESK not DEV
- For headless parallel agents: use claude-squad instead

### Keys Deployed
- Telegram bot: 8139170372 (@athanor_ops_bot) — token in /etc/cron.d/openfang-boot
- GitHub PAT: in ~/.secrets/github-pat, gh authed as Dirty13itch
- CodeRabbit: installed on GitHub repo
- DashScope: key rejected (LTAI5t... is AccessKey, not API key)

### LiteLLM Status (VAULT:4000)
- 9 healthy endpoints: 3x Qwen3.5-27B, embedding, coder, 4x Anthropic
- 25 unhealthy: all cloud models (missing API keys in container env)
- Cloud keys needed: OPENAI, MISTRAL, CODESTRAL, VENICE, OPENROUTER, GOOGLE, ZAI, MOONSHOT, DEEPSEEK, GROQ, CEREBRAS
- Only Anthropic key is set in container

### WORKSHOP vLLM (vllm-vision container)
- Stopped by gpu-swap.sh 2 days ago, restarted 2026-03-19
- Container name: vllm-vision (NOT vllm-node2)
- Model: Qwen3.5-35B-A3B-AWQ-4bit on RTX 5090
