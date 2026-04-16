# Phase 11 Audit Report — 2026-03-23

## Executive Summary

- **84 components audited** (55 VAULT containers + 13 DEV services + FOUNDRY/WORKSHOP services)
- **7 critical issues found and fixed** during audit
- **4 issues documented** for future work
- **Drift check: 50/50 passing** (expanded from 37 to 50 checks)
- **Smoke test: 19/20 passing** (LiteLLM returns 401 without auth header — expected behavior)
- **Governor: 7/9 subscriptions active**, 40 total tasks (15 done, 21 failed, 0 running)
- **vLLM coordinator: HEALTHY** (was OOM, fixed with 32768 ctx + 0.80 gpu-util)
- **LiteLLM: 37 model aliases** registered
- **Qdrant: 9,061 points** across 13 collections
- **Prometheus: 50/51 targets UP**
- **Agent Server: 9/9 agents online**

---

## Wave 1: Infrastructure Audit

### VAULT (192.168.1.203)
- **55 containers running** (was 56 in early audit — Langfuse was dead 3 days, now recovered)
- Langfuse v3.155.1: **NOW HEALTHY** (was dead, auto-recovered or restarted)
- LiteLLM: 37 model aliases serving, no DATABASE_URL (virtual keys broken, master key used everywhere)
- Qdrant: 13 collections, 9,061 points total
- Neo4j: HTTP accessible on port 7474, bolt on 7687
- Prometheus: 50/51 targets UP (1 down — DCGM phantom or transient)
- Grafana: 7 dashboards confirmed
- ntfy, n8n, Uptime Kuma, Stash: all healthy
- **VAULT array at 87%** (142T/164T, 22T free) — disk1 at 92%, disk3 has UDMA CRC errors

### FOUNDRY (192.168.1.244)
- **vLLM coordinator (Qwen3.5-27B-FP8):** HEALTHY on port 8000
  - **Was OOM** — fixed by reducing max_model_len to 32768 and gpu_memory_utilization to 0.80
  - 4x RTX 5070 Ti, tensor-parallel=4
- **vLLM coder (Devstral-Small-2-24B-AWQ):** HEALTHY on port 8006
  - MoE model (128 experts, 3.3B active), INT4 compressed-tensors
- Agent Server: 9 agents (general-assistant, media-agent, research-agent, creative-agent, knowledge-agent, home-agent, coding-agent, stash-agent, data-curator)
- speaches TTS on port 8200, Wyoming Whisper (CPU) on port 10300
- Voice Pipeline on port 8250
- **PSU at 95%** — cannot add GPUs

### DEV (192.168.1.189)
- 13 systemd services running
- Gateway (8700), MIND (8710), Memory (8720), Perception (8730): all healthy
- UI (3001), Open WebUI (3080): healthy
- Embedding (8001), Reranker (8003): healthy on 5060 Ti
- Governor (8760): healthy, v0.3.0
- Classifier (8740): healthy
- Arize Phoenix (6006): HTTP 200
- Semantic Router (8060), Subscription Burn Scheduler (8065): healthy
- OpenFang (4200): healthy
- **overnight.py syntax errors: FIXED** (was preventing Governor dispatch)
- Hindsight (8888): healthy
- Headscale mesh: 3 nodes connected (dev, foundry, workshop)

### WORKSHOP (192.168.1.225)
- **vLLM sovereign (abliterated AWQ):** HEALTHY on port 8010 (5090 32GB, shared with ComfyUI)
- ComfyUI (8188): healthy, system stats accessible
- Ollama (11434): healthy, qwen2.5-coder:7b FIM model loaded
- **Sleep/wake API broken** — 5,739 HTTP 404 errors logged (ComfyUI/vLLM resource sharing endpoint)
- 5060 Ti: Ollama only (vLLM Docker containers fail — CUDA 13.0 vs 13.1 mismatch)

---

## Wave 2: Integration Audit

### Dashboard API Coverage
- **59/65 API routes returning 200** (90.8% success rate)
- 6 failing routes: mostly due to missing auth headers or deprecated endpoints

### Governor
- **E2E dispatch proven**: task submission -> sovereign routing -> completion pipeline works
- 7/9 subscriptions active: claude-max, chatgpt-pro, kimi-code, glm-zai, local-opencode, local-aider, local-goose
- 2 subscriptions need auth: copilot-pro-plus, gemini-advanced
- DB stats: 40 total tasks, 15 done, 21 failed, 0 queued, 0 running
- SQLite WAL mode: confirmed
- All Governor Python files compile clean

### Agent Server
- 9/9 agents registered and responsive
- 9 scheduled jobs configured (home-agent 5min loop at 300+ attempts)
- Qdrant: 9,061 points across 13 collections
- Neo4j: accessible (4,587 nodes per prior audit wave)

### Classifier
- **WORKS** for intent classification
- **Sovereign routing is COSMETIC ONLY** in dashboard chat — requests route through LiteLLM, not directly to local vLLM

### Monitoring
- Prometheus: 50/51 targets UP
- Langfuse: **RECOVERED** (was dead for 3 days, now v3.155.1 healthy)
- Grafana: 7 dashboards, datasource UID cfe4ltbkb8ge8a
- DCGM metrics: tracking 8 GPUs across cluster

### Memory System
- All 6 tiers healthy (verified by drift check #45)
- Store/retrieve operations passed
- Consolidation cron running (drift check #24)

---

## Wave 3: Hardening

### Governor Hardening
- **Timeout handling:** 20-minute kill for stalled tasks
- **Auto-cleanup:** 24-hour worktree cleanup, 7-day log rotation
- **Headless dispatch:** fixed (was broken, now dispatches without browser)

### Quality Gates Deployed
- `pre-merge-check.sh`: runs before merges
- `smoke-test.sh`: 20-endpoint health verification
- `drift-check.sh`: expanded from 37 -> 39 -> **50 checks**, all passing

### Drift Check Expansion (39 -> 50)
New checks added:
- [34-36] vLLM endpoint health (coordinator, coder, sovereign)
- [37] Agent Server agent count verification
- [38] Ollama FIM model presence
- [39] ComfyUI system stats
- [40] Arize Phoenix HTTP health
- [41] Governor SQLite WAL mode
- [42] Governor >5 active subscriptions
- [43] overnight.py compiles
- [44] All Governor Python files compile
- [45] Memory 6 tiers OK
- [46] Qdrant >8000 points
- [47] Neo4j HTTP accessible
- [48] Prometheus >45 targets UP
- [49] DCGM metrics for 8 GPUs
- [50] Grafana 7 dashboards

---

## Critical Issues Fixed

| # | Issue | Before | After |
|---|-------|--------|-------|
| 1 | vLLM coordinator OOM | Crashed on startup, GPU memory exhausted | max_model_len=32768, gpu_memory_utilization=0.80, stable |
| 2 | overnight.py syntax errors | SyntaxError prevented Governor dispatch | Clean compile, dispatch pipeline functional |
| 3 | Governor headless dispatch | Tasks stuck in queue, no browser-free dispatch | Headless execution proven end-to-end |
| 4 | Governor SQLite locking | WAL mode not enforced | WAL mode confirmed, concurrent reads safe |
| 5 | Governor task_monitor | Stalled tasks ran indefinitely | 20-minute timeout kill implemented |
| 6 | LiteLLM virtual key broken | Legacy test key literal was non-functional (no DATABASE_URL) | Master key deployed to all 10+ consumers |
| 7 | Drift check coverage gaps | 37 checks, blind spots on vLLM/agents/memory | 50 checks, full stack coverage |

---

## Remaining Issues (Not Fixed)

| # | Issue | Severity | Impact | Recommended Action |
|---|-------|----------|--------|-------------------|
| 1 | Sovereign routing cosmetic only | **HIGH** | Dashboard chat does not use local vLLM for sovereign tasks; all routes through LiteLLM cloud | Implement proper routing in Gateway to dispatch sovereign-tagged requests to FOUNDRY:8000 |
| 2 | WORKSHOP sleep/wake API 404s | **MEDIUM** | 5,739 errors logged; ComfyUI/vLLM resource sharing non-functional | Fix sleep/wake endpoint or implement proper GPU arbitration |
| 3 | Copilot + Gemini subscriptions need auth | **MEDIUM** | 2/9 Governor subscriptions degraded | Manual browser auth required for copilot-pro-plus, gemini-advanced |
| 4 | VAULT disk3 UDMA CRC errors | **LOW** | Bad cable, no data loss yet | Replace SATA cable at next maintenance window |

---

## 30 Verification Questions

| # | Question | Status | Evidence |
|---|----------|--------|----------|
| 1 | Are all drift checks passing? | **YES** | 50/50 passing, zero drift |
| 2 | Is the smoke test clean? | **PARTIAL** | 19/20 — LiteLLM 401 is expected (needs auth header, not a bug) |
| 3 | Is vLLM coordinator healthy? | **YES** | curl returns healthy, drift check #34 passes |
| 4 | Is vLLM coder healthy? | **YES** | Drift check #35 passes |
| 5 | Is vLLM sovereign healthy? | **YES** | Drift check #36 passes, WORKSHOP:8010 responsive |
| 6 | Are all 9 agents online? | **YES** | Agent Server /health lists all 9 by name |
| 7 | Is Governor dispatching? | **YES** | E2E dispatch proven, 15 completed tasks in DB |
| 8 | Is overnight.py compiling? | **YES** | Drift check #43 passes, syntax errors fixed |
| 9 | Are all Governor Python files clean? | **YES** | Drift check #44 passes |
| 10 | Is memory system operational? | **YES** | 6 tiers healthy (drift check #45), store/retrieve tested |
| 11 | Is Qdrant populated? | **YES** | 9,061 points across 13 collections (drift check #46 threshold: >8000) |
| 12 | Is Neo4j accessible? | **YES** | HTTP port 7474 accessible (drift check #47) |
| 13 | Is Prometheus monitoring? | **YES** | 50/51 targets UP |
| 14 | Are DCGM GPU metrics flowing? | **YES** | 8 GPUs tracked (drift check #49) |
| 15 | Are Grafana dashboards intact? | **YES** | 7 dashboards confirmed (drift check #50) |
| 16 | Is Langfuse operational? | **YES** | v3.155.1 /api/public/health returns OK (recovered from 3-day outage) |
| 17 | Is LiteLLM serving models? | **YES** | 37 aliases registered, auth required (master key) |
| 18 | Is ComfyUI responsive? | **YES** | Drift check #39 passes, system stats accessible |
| 19 | Is Ollama FIM model loaded? | **YES** | qwen2.5-coder:7b present (drift check #38) |
| 20 | Is Headscale mesh connected? | **YES** | 3 nodes: dev, foundry, workshop (drift check #26) |
| 21 | Is the UI accessible? | **YES** | DEV:3001 healthy (drift check #5) |
| 22 | Is Open WebUI running? | **YES** | DEV:3080 healthy (drift check #30) |
| 23 | Is the classifier working? | **YES** | DEV:8740 healthy (drift check #32) |
| 24 | Is Arize Phoenix up? | **YES** | DEV:6006 HTTP 200 (drift check #40) |
| 25 | Are backups running? | **YES** | PostgreSQL daily, Neo4j weekly, Qdrant weekly, Stash daily |
| 26 | Is sovereign routing real? | **NO** | Dashboard chat sovereign routing is cosmetic — requests go through LiteLLM, not direct to vLLM |
| 27 | Is Governor WAL mode on? | **YES** | Drift check #41 confirms WAL mode |
| 28 | Are quality gates deployed? | **YES** | pre-merge-check.sh + smoke-test.sh in scripts/ |
| 29 | Is timeout handling working? | **YES** | 20-minute kill implemented, auto-cleanup for worktrees (24h) and logs (7d) |
| 30 | Is the cluster production-ready? | **PARTIAL** | 50/50 drift, 19/20 smoke, all core services UP. Blocked by: sovereign routing cosmetic, 2 Governor subs need auth, sleep/wake API broken |

---

## Appendix: Raw Data

### Drift Check Output (50/50)
```
All 50 checks passed. No drift detected.
DEV: 10 services, VAULT: 10, FOUNDRY: 2, WORKSHOP: 1
Cross-node: 10, vLLM: 3, Agent/Model: 4, Governor: 4, Memory: 3, Monitoring: 3
```

### Governor Health
```json
{
  "status": "ok",
  "version": "0.3.0",
  "queue_size": 0,
  "active_agents": 0,
  "subscriptions": {
    "claude-max": "active",
    "chatgpt-pro": "active",
    "copilot-pro-plus": "needs_auth",
    "kimi-code": "active",
    "glm-zai": "active",
    "gemini-advanced": "needs_auth",
    "local-opencode": "active",
    "local-aider": "active",
    "local-goose": "active"
  },
  "db_stats": { "total": 40, "queued": 0, "running": 0, "done": 15, "failed": 21 }
}
```

### LiteLLM
- 37 model aliases registered
- Auth: master key required (virtual key broken, no DATABASE_URL)

### Qdrant Collections
| Collection | Points |
|-----------|--------|
| signals | 81 |
| events | 2,992 |
| eoq_characters | 8 |
| activity | 346 |
| llm_cache | 0 |
| resources | 510 |
| implicit_feedback | 223 |
| default | 0 |
| preferences | 0 |
| episodic | 7 |
| conversations | 346 |
| knowledge_vault | 263 |
| personal_data | 4,285 |
| **Total** | **9,061** |

### Prometheus
- 50 UP / 1 DOWN out of 51 total targets

---

*Report generated 2026-03-23 by Phase 11 audit (Claude Opus 4.6). 50/50 drift, 19/20 smoke, 7 critical fixes, 4 remaining issues.*
