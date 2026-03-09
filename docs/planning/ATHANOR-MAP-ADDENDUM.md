# ATHANOR-MAP ADDENDUM — March 7, 2026 (Late Session)

**Append this to ATHANOR-MAP.md on DEV. These sections were developed after the initial map.**

---

## 17. VERIFIED CLUSTER STATE (Live, March 7 2026 ~3:00 PM CT)

| Node | SSH | User | GPUs Confirmed | Services Running | Services NOT Running |
|------|-----|------|----------------|-----------------|---------------------|
| FOUNDRY (.244) | OK | athanor | 4x5070Ti + 4090 | vLLM on :8000 | :8001 (utility slot empty) |
| WORKSHOP (.225) | OK | athanor | 5090 + 5060Ti | Dashboard on :3001 | vLLM :8100/:8101 CLOSED |
| VAULT (.203) | OK | root | Intel A380 | LiteLLM :4000, Qdrant :6333, Redis :6379 | LangFuse :3030 NOT deployed |
| DEV (.189) | local | shaun | 5060Ti | Claude Code + dev tools | N/A |

Corrections: DEV IP=.189 (was TBD), DEV NIC=5GbE Realtek (not 10GbE), SSH users: DEV=shaun FOUNDRY/WORKSHOP=athanor VAULT=root, both keys (id_ed25519 + athanor_mgmt) needed on all nodes.

---

## 18. MOBILE OPS STACK (Permanent)

Phone (S21 Ultra) via Tailscale to VAULT services:
- Open WebUI :3080 (chat, RAG with Qdrant, MCP tools, voice, PWA) - connects to LiteLLM :4000
- Grafana :3000 (GPU/service dashboards, push alerts to Telegram)
- LangFuse :3030 (agent traces, prompt versioning)
- Termux+Mosh to DEV (full Claude Code terminal, survives network drops)
- GitHub Mobile (PR review for overnight runs)

DEV needs: mosh installed. Open WebUI connects to existing LiteLLM+Qdrant on VAULT.

---

## 19. BLEEDING-EDGE TOOLS (Evaluated)

Install now: claude-tmux (session TUI), claude-esp (hidden output viewer), parry (injection scanner).
Evaluate Week 2: OpenClaw (messaging gateway), DeerFlow 2.0 (study middleware patterns), Composio Orchestrator (just-in-time tools).
Skip: CrewAI, AutoGen, MetaGPT, Dify, Langflow, any cloud-dependent tool.

---

## 20. THREE-AGENT COGNITIVE ARCHITECTURE

Prometheus (27B-FP8, FOUNDRY TP=4) = coordinator, only voice user hears.
Worker Pool (35B-A3B-AWQ, WORKSHOP 5090) = undifferentiated, role prompts per task.
Sentinel (9B, FOUNDRY 4090) = always-on monitoring, classification, embedding.

Existing 8 agents: don't consolidate, enhance. Three-agent is future delegation logic.
Autonomy gradient: Level 0 (now) through Level 4 (future). Start with intelligence pipeline.

---

## 21. CORRECTED SPRINT PLAN

Week 0 (DONE): DEV bootstrapped, all tools+configs+repos, SSH verified.
Week 1: Fix SSH config, install mosh, deploy Open WebUI + LangFuse on VAULT, vLLM v0.17.0 + Qwen3.5-35B-A3B on WORKSHOP 5090, update LiteLLM, test harness.
Week 2: FOUNDRY upgrade (only after 7 days stable), Hydra module porting, n8n workflows, Grafana dashboards.
Week 3: Intelligence pipeline (Miniflux+n8n), Telegram bot, Grafana alerts, accelerated eval.
Week 4: Autonomous tasks, overnight claude-squad, steady-state rhythm.
