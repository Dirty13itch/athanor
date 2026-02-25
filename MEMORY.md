# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-25 (Session 19: Dashboard Workspace + Conversations Pages)

### What happened
- **Creative-agent fix:** Redeployed agents with correct 5-tool metadata (generate_video was missing from registry).
- **Dashboard Workspace page:** New `/workspace` page showing GWT broadcasts, agent registry, event ingestion.
- **Dashboard Conversations page:** New `/conversations` page with logged conversation history, agent filtering, semantic search.
- **MEMORY.md updated** with Sessions 16-18 history (was stale at Session 15).
- **SYSTEM-SPEC.md updated** with GWT Phase 2 features.

### Sessions 16-18 recap (previously unrecorded)
- **Session 16-17 (2026-02-25):** Tier 6 progress — Wan2.x T2V pipeline verified, Creative Agent wired with generate_video, Stash agent deployed (8 agents total), voice containers deployed (wyoming-whisper, Speaches, wyoming-piper, wyoming-openwakeword), HA voice pipeline configured, Layer 2 context injection for all agents.
- **Session 18 (2026-02-25):** Maintenance sweep — knowledge re-indexed (1203 pts), HA dashboard auth fix (26/26 UP), Neo4j graph updated (43 rels), backup script updated (14 services), agent contracts updated. GWT Phase 2 — conversation logging, agent registry, event ingestion, Redis pub/sub. Ansible convergence verified (vault.yml changed=0).

### Current blockers
- NordVPN credentials needed for qBittorrent + Gluetun (6.5)
- Tailscale needs UDM Pro SSH + Tailscale account (6.8)
- vLLM sleep mode blocked on NGC image upgrade (sleep endpoints 404)
- Sonarr/Radarr need Prowlarr indexer config via browser

### What's next
- GWT Phase 3 (agents subscribing to broadcasts, reactive behavior, semantic relevance scoring)
- GPU orchestrator Phase 3 (priority preemption, LiteLLM wake-before-route)
- Dashboard: more workspace visualizations (competition history, salience trends)
- Stash Phase 2: VLM auto-tagging, face recognition

### Git state
- Branch: main, all pushed to origin
- Latest: `97a5f31` docs: update CLAUDE.md with GWT Phase 2 state

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
| 19 | 2026-02-25 | Dashboard expansion | Workspace + Conversations dashboard pages. Creative-agent registry fix. |
