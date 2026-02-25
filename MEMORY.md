# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-25 (Session 15: Tier 7 Complete — Full System Design Implementation)

### What happened
- **System design documentation** (7.1-7.4) — Created `SYSTEM-SPEC.md`, `agent-contracts.md`, `hybrid-development.md`. Expanded `intelligence-layers.md`. Committed as `5343beb`.
- **Redis deployed** (7.5) — VAULT:6379, `redis:7-alpine`, AOF persistence, 512MB maxmemory.
- **Coding Agent deployed** (7.6) — 7th agent on Node 1:9000. Tools: generate_code, review_code, explain_code, transform_code.
- **MCP bridge deployed** (7.7) — 11 tools exposed to Claude Code via `scripts/mcp-athanor-agents.py`.
- **Activity + Preferences** (7.8) — Two new Qdrant collections, activity logging, preference storage/retrieval.
- **Escalation protocol** (7.9) — 3-tier confidence system (act/notify/ask). Per-agent/per-action thresholds.
- **GWT workspace** (7.10) — Redis-backed shared workspace. 1Hz competition cycle. Salience scoring. Capacity 7 items.
- **GPU Orchestrator deployed** (7.11) — `projects/gpu-orchestrator/` on Node 1:9200. 4 GPU zones, DCGM-based metrics (7 GPUs, both nodes), vLLM sleep/wake management, TTL auto-sleep scheduler, Redis state, Prometheus metrics export. Ansible role `gpu-orchestrator`.
- **Dashboard 3 new pages** (7.12-7.14) — `/activity`, `/notifications`, `/preferences`. All deployed to Node 2:3001.
- **Phase 1 committed** as `2644f58`. GPU orchestrator is the final commit.
- **All 14/14 Tier 7 items complete.** Tiers 1-7 fully deployed.

### Current blockers
- Sonarr/Radarr/Prowlarr need indexer config via Prowlarr UI
- SABnzbd needs Usenet provider credentials
- NordVPN credentials needed for qBittorrent + Gluetun
- Tailscale needs UDM Pro SSH + Tailscale account (6.8)
- vLLM `--enable-sleep-mode` not set — GPU orchestrator sleep/wake works but instances report "unavailable"

### What's next
- Enable vLLM sleep mode on both nodes (Ansible vLLM role update + KV cache CPU offloading)
- GPU orchestrator Phase 3 (priority preemption, LiteLLM wake-before-route, flex GPU assignment, dashboard GPU page)
- Tier 6 backlog: video gen (6.1), InfiniBand (6.2), voice (6.3), mobile (6.4), VPN (6.5), Stash AI (6.6), mining enclosure (6.7), remote access (6.8)

### Git state
- Branch: main, 2 commits ahead of origin (5343beb docs, 2644f58 Phase 1-2, GPU orchestrator uncommitted)

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
