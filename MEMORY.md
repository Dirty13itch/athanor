# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-24 (Session 11: Neo4j + Design System + Agents + Monitoring)

### What happened
- **Fixed DEV PATH** — Removed broken Windows-style PATH from `~/.bashrc`, replaced with proper Linux PATH (`/usr/bin:/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH`)
- **Neo4j deployed** (manifest 1.5) — VAULT:7474/7687, v5.26.21 community. Seeded graph: 4 Nodes, 16 Services, 3 Agents, 3 Projects, 29 relationships. Ansible role: `vault-neo4j`
- **Dashboard design system** (manifest 3.1) — Created `DESIGN.md` formalizing the dark+amber OKLCh palette, 3-font typography scale, spacing system, component library. Added semantic color tokens (`--success`, `--warning`, `--info`). Fixed Next.js 16 global-error bug. Deployed.
- **Research Agent** (manifest 2.1) — 4 tools: web_search (DuckDuckGo), fetch_page (HTTP+HTML extraction), search_knowledge (Qdrant), query_infrastructure (Neo4j Cypher). Deployed to Node 1:9000. Tested end-to-end.
- **Creative Agent** (manifest 2.3) — 4 tools: generate_image (Flux via ComfyUI API), check_queue, get_generation_history, get_comfyui_status. Deployed. Flux dev FP8 model download complete (17GB).
- **Monitoring page** (manifest 3.3) — Full `/monitoring` page with live Prometheus data. Per-node cards: CPU (1hr sparkline), memory (sparkline), disk, network. Cluster summary. Grafana deep-links. Auto-refresh 15s. Deployed.
- **Knowledge Agent** (manifest 2.2) — 5 tools: search_knowledge, list_documents, query_knowledge_graph, find_related_docs, get_knowledge_stats. Indexer script indexed 81 docs → 922 chunks in Qdrant. Deployed to Node 1:9000.
- **Neo4j graph names fixed** — Renamed node1→Foundry, node2→Workshop, vault→VAULT, dev→DEV. Added knowledge-agent + research-agent + creative-agent entities.
- **5 agents now live**: general-assistant, media-agent, research-agent, creative-agent, knowledge-agent

### Current blockers
- HA onboarding requires Shaun in browser (http://192.168.1.203:8123)
- Sonarr/Radarr/Prowlarr need indexer config via Prowlarr UI
- SABnzbd needs Usenet provider credentials
- NordVPN credentials needed for qBittorrent + Gluetun
- Tailscale install needs sudo password on DEV

### What's next (from BUILD-MANIFEST.md)
- P2: EoBQ scaffold (item 4.1) — game engine ADR, project structure
- P2: Backup strategy (item 5.3) — needs ADR
- P2: Ansible full convergence test (item 5.2)
- P2: CLAUDE.md optimization (item 5.5)
- P2: 10GbE throughput verification (item 5.1)

### Git state
- Branch: main, uncommitted changes (this session's work)

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
