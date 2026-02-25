# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-25 (Session 15: System Design Layer + Phase 1 Implementation)

### What happened
- **System design documentation** (7.1-7.4) — Created `SYSTEM-SPEC.md` (460 lines, complete operational specification), `agent-contracts.md` (formal contracts for all 8 agents), `hybrid-development.md` (cloud/local coding architecture with MCP bridge design). Expanded `intelligence-layers.md` with preference learning, escalation protocol, feedback signals.
- **Redis deployed** (7.5) — VAULT:6379, `redis:7-alpine`, AOF persistence, 512MB maxmemory. Ansible role `vault-redis`. Verified: PONG.
- **Coding Agent deployed** (7.6) — 7th agent on Node 1:9000. Tools: generate_code, review_code, explain_code, transform_code. Uses reasoning model at temp 0.3. Verified: generates working Python.
- **Activity + Preferences infrastructure** (7.8) — Two new Qdrant collections (activity, preferences, 1024-dim Cosine). Activity logging module (`activity.py`) with fire-and-forget asyncio logging on all chat completions. Three new API endpoints: `GET /v1/activity`, `GET /v1/preferences`, `POST /v1/preferences`. Semantic preference retrieval working.
- **Bug fix:** Removed unsupported `order_by` parameter from Qdrant scroll endpoint (400 Bad Request). Sorting done in Python.
- **Stash investigation:** Appdata exists but is empty (fresh container). Backup is empty too. No data to restore.
- **7 agents now live**: general-assistant, media-agent, research-agent, creative-agent, knowledge-agent, home-agent, coding-agent
- **MCP bridge deployed** — 11 tools exposed to Claude Code via `scripts/mcp-athanor-agents.py`. `.claude/agents/coder.md` + `.claude/skills/local-coding.md` created.
- **Escalation protocol deployed** — 3-tier confidence system (act/notify/ask). Per-agent/per-action thresholds. Notification queue with approve/reject.
- **Dashboard 3 new pages** — `/activity` (timeline with agent filters), `/notifications` (pending actions + escalation config), `/preferences` (store + semantic search). All deployed to Node 2:3001.
- **GWT workspace deployed** — Redis-backed shared workspace. 1Hz competition cycle. Salience scoring (urgency x relevance x recency). Capacity 7 items.

### Current blockers
- Sonarr/Radarr/Prowlarr need indexer config via Prowlarr UI
- SABnzbd needs Usenet provider credentials
- NordVPN credentials needed for qBittorrent + Gluetun
- Tailscale needs UDM Pro SSH + Tailscale account (6.8)

### What's next
- 7.11 — GPU orchestrator (FastAPI on Node 1, pynvml, vLLM sleep/wake, priority scheduling) — last Tier 7 item
- Tier 6 backlog: video gen (6.1), InfiniBand (6.2), voice (6.3), mobile (6.4), VPN (6.5), Stash AI (6.6), mining enclosure (6.7), remote access (6.8)

### Git state
- Branch: main, uncommitted changes (Phase 0 docs committed as 5343beb, Phase 1 implementation uncommitted)

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
| 15 | 2026-02-25 | System design + Phase 1 | SYSTEM-SPEC, agent contracts, hybrid-dev docs. Redis, Coding Agent, activity/preferences Qdrant collections deployed |
