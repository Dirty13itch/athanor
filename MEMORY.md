# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-03-08 (Session 40: Tiers 12-14 Execution Sprint)

### What happened
- **Tier 12 COMPLETE (all 8 items):** Gitea CI (first green run), n8n deployed (VAULT:5678, signal pipeline workflow), Miniflux + feeds, overnight ops timer, promptfoo evals, backup fix, DNS resolution, LangFuse wiring verified.
- **Tier 13 COMPLETE (all 5 items):** GA delegation rewrite, inference-aware scheduling (GPU util + queue depth checks), behavioral pattern detection, A/B eval suite (36 total cases), embedding location decision (stay on DEV).
- **Tier 14 progress:** EoBQ portraits (14.1✅), dialogue verified (14.2✅), HA tools expanded (14.3 — needs Shaun for Lutron/UniFi), Ulrich requirements (14.4✅), Kindred (14.5 — awaiting Shaun).
- **Agent deploy:** All 8 modified files rsync'd to FOUNDRY, container rebuilt, 9 agents healthy. New: scheduling endpoint, search_signals tool, character portraits, home scene/history/network tools.
- **Qdrant `signals` collection:** Created on FOUNDRY:6333 (1024-dim, Cosine). Knowledge Agent can query via search_signals tool.
- **n8n signal pipeline:** 7-node workflow (Miniflux poll → LLM classify → embed → Qdrant store → mark read). Needs manual UI activation at http://192.168.1.203:5678.
- **3 commits pushed** to both origin (GitHub) and gitea remotes. CI green on first run.
- **Token offloading research:** Comprehensive analysis in progress — strategies for reducing Anthropic API costs via local model routing.

### Current blockers
- NordVPN credentials needed for qBittorrent + Gluetun (6.5)
- Anthropic API key needed for Quality Cascade cloud escalation (8.5)
- Google Drive rclone OAuth needed for Personal Data ~40% (10.8)
- Photo Analysis blocked on Qwen3.5 multimodal + vLLM 0.17+ (10.10)
- n8n workflow activation requires Shaun to click Activate in UI (v2.10 API limitation)
- HA integrations (14.3) require Shaun to configure Lutron + UniFi in HA

### What's next (priority order)
1. **Token offloading analysis** — deliver comprehensive strategies doc (research agent running)
2. **n8n workflow activation** — Shaun: visit http://192.168.1.203:5678, activate "Intelligence Signal Pipeline"
3. **14.3 — HA depth** — blocked on Shaun (Lutron/UniFi config, ESP32-S3 order)
4. **14.5 — Kindred** — awaiting Shaun's decision to start
5. **Eval baseline run** — execute promptfoo against live LiteLLM to record first scores
6. **FOUNDRY GPU4** — still idle, candidate for Qwen3.5-9B utility model

### Git state
- Branch: main
- Latest: `fe9d670` docs: Tiers 12-14 tracking, evals, Ulrich requirements, research

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
| 12-14 | 2026-02-24 | Hardening + EoBQ + Remote access | 10GbE verified, backups deployed, EoBQ wired + deployed, ADR-016 (superseded) |
| 15 | 2026-02-25 | System design + full Tier 7 | SYSTEM-SPEC, agent contracts, hybrid-dev docs. All 14/14 Tier 7 items complete. |
| 16-17 | 2026-02-25 | Tier 6 + Voice + Context | Wan2.x T2V, Creative Agent video tools, Stash agent, voice pipeline, Layer 2 context injection. |
| 18 | 2026-02-25 | Maintenance + GWT Phase 2 | Knowledge re-index, HA auth fix, GWT Phase 2 (conversation logging, agent registry, pub/sub). |
| 19 | 2026-02-25 | Autonomous Workforce + Research Sweep | Task Engine (8.1), Scheduler (8.2), Exec Tools (8.3). 26-agent research sweep. |
| 20 | 2026-02-26 | Command Center (Tier 9) | PWA, Cmd+K, Agent Crew Bar, SSE streaming, Furnace Home, Lens Modes, Goals/Feedback, Push Notifications, Generative UI. All 9.1-9.10 complete. |
| 33-35 | 2026-02-26 | Personal Data System (Tier 10) | Bookmarks (727), GitHub repos (82), entity extraction (3095 nodes), file indexer (2304 pts), Data Curator agent, Terminal page, Claudeman. 8/10 complete. |
| 36 | 2026-03-07 | System Synthesis | Full cluster audit, doc refresh, Tier 11 defined, Ansible work committed. |
| 37-39 | 2026-03-07 | Tiers 11-14 Sprint | All Tier 11 (8 cognitive synthesis), Tier 12 (8 ops autonomy), Tier 13 (5 agent intelligence). |
| 40 | 2026-03-08 | Tiers 12-14 Completion | n8n deployed, signal pipeline, agent deploy, CI green, 3 commits pushed. |
