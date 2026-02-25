# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-25 (Session 19: Autonomous Workforce — Task Engine + Scheduler)

### What happened
- **Task Execution Engine (8.1):** `tasks.py` — Redis-backed queue, background worker (5s poll, max 2 concurrent), step logging via astream_events, priority ordering, crash recovery, GWT broadcasting. Delegation tools (`delegate_to_agent`, `check_task_status`). API: POST/GET /v1/tasks, stats, cancel. MCP bridge: 14 tools. Dashboard Task Board page.
- **Proactive Agent Scheduler (8.2):** `scheduler.py` — asyncio-based with per-agent intervals. general-assistant (30min), media-agent (15min), home-agent (5min), knowledge-agent (24h, disabled). Redis-tracked last-run. API: GET /v1/tasks/schedules. First scheduled batch verified working.
- **Dashboard updates:** Workspace page, Conversations page, Task Board page (16 pages total).
- **Creative-agent fix:** 5-tool metadata corrected.
- **Think-tag fix:** Task results stripped of `<think>` tags via regex.
- **Step persistence fix:** Every tool call persisted (was every 3).

### Current blockers
- NordVPN credentials needed for qBittorrent + Gluetun (6.5)
- Tailscale needs UDM Pro SSH + Tailscale account (6.8)
- vLLM sleep mode blocked on NGC image upgrade (sleep endpoints 404)
- Sonarr/Radarr need Prowlarr indexer config via browser
- DuckDuckGo web search unreliable from Docker container (research-agent limitation)

### What's next
- **8.3 Execution Tools:** Filesystem read/write (scoped), shell execution (Docker sandbox), git ops — gives agents actual coding ability
- **8.4 Dedicated Coding Model:** Deploy Qwen3-Coder-30B-A3B on RTX 4090
- **8.5 Quality Gating & Cascade:** Local generates → tests → escalate to cloud on failure
- GWT Phase 3 (agent subscriptions + reactive behavior)

### Git state
- Branch: main, all pushed to origin
- Latest: `f2272c5` feat: Execution tools — agents can read, write, and run code

---

## Session History

| Session | Date | Focus | Key Outcomes |
|---------|------|-------|-------------|
| 1-2 | 2026-02-15 | Research + ADRs | 20 research docs, 11 ADRs, hardware audit |
| 3 | 2026-02-16 | Physical rack work | Motherboard swap, 10GbE, JetKVM, DHCP |
| 4 | 2026-02-17 | Node deployment | NVIDIA drivers, Docker, NFS, vLLM, ComfyUI, Open WebUI |
| 5 | 2026-02-23 | Full convergence | Ansible site.yml, Qwen3-32B-AWQ, embeddings, dashboard, agents |
| 6 | 2026-02-23 | Refinement | Embedding model, speculative decoding, UFW, NFS hardening |
| 7 | 2026-02-24 | VAULT + Autonomy | 10 VAULT containers, Claude Code autonomy, BUILD-MANIFEST |
| 8 | 2026-02-24 | Post-deploy hardening | Git push, monitoring verified, NFS verified, restart policies confirmed |
| 9 | 2026-02-24 | SSH + LiteLLM + Qdrant | Fixed WSL SSH keys, LiteLLM on VAULT:4000, Qdrant on Node 1:6333 |
| 10 | 2026-02-24 | Context reconciliation + Agent routing | 15 docs extracted, agents wired to LiteLLM, 16/16 services verified |
| 11 | 2026-02-24 | Neo4j + Design + Agents + Monitoring | Neo4j, design system, Research + Creative agents, monitoring page, Flux model |
| 12-14 | 2026-02-24 | Hardening + EoBQ + Remote access | 10GbE verified, backups deployed, EoBQ wired + deployed, ADR-016 Tailscale |
| 15 | 2026-02-25 | System design + full Tier 7 | SYSTEM-SPEC, agent contracts, hybrid-dev docs. Redis, Coding Agent, MCP bridge, escalation, GWT workspace, GPU orchestrator, 3 dashboard pages. **All 14/14 Tier 7 items complete.** |
| 16-17 | 2026-02-25 | Tier 6 + Voice + Context | Wan2.x T2V verified, Creative Agent video tools, Stash agent, 4 voice containers, HA voice pipeline, Layer 2 context injection. |
| 18 | 2026-02-25 | Maintenance + GWT Phase 2 | Knowledge re-index (1203 pts), HA auth fix (26/26 UP), Neo4j 43 rels, backup 14 svcs. GWT Phase 2: conversation logging, agent registry, event ingestion, pub/sub. |
| 19 | 2026-02-25 | Autonomous Workforce | Task Execution Engine (8.1), Proactive Scheduler (8.2), Task Board dashboard, delegation tools, MCP bridge 14 tools. Workspace + Conversations pages. |
