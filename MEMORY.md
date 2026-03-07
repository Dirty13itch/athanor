# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-03-07 (Session 36: System Synthesis — Doc Refresh + Cluster Audit)

### What happened
- **Full cluster audit:** SSH into all 3 nodes, captured live state vs documented state.
- **FOUNDRY model lineup changed significantly:** Now runs 3 vLLM instances — Qwen3-32B-AWQ (reasoning, TP=2, GPUs 0+1), GLM-4.7-Flash-GPTQ-4bit (creative, GPU 2/4090), Huihui-Qwen3-8B-abliterated-v2 (coding, GPU 3). GPU 4 is idle (no embedding model).
- **WORKSHOP already upgraded:** Qwen3.5-35B-A3B-AWQ-4bit running on 5090 with correct safety flags. 5060Ti running ComfyUI (5.1 GB used).
- **VAULT expanded:** 36 containers (was 14 in docs). LangFuse v3.155.1 healthy on :3030. Open WebUI on :3090. New undocumented services: Spiderfoot, Tdarr, Meilisearch, ntfy, cadvisor, field-inspect-app, Qdrant (VAULT-side), Postgres.
- **LiteLLM routes expanded:** 14 models (reasoning, coding, fast, creative, embedding, reranker, worker, claude, gpt, deepseek, gemini + aliases). Cloud cascade models added.
- **Ansible committed:** vault-langfuse + vault-open-webui roles, Workshop Qwen3.5-35B-A3B upgrade, DEV node in inventory, ops tooling (model-inventory.sh, test-endpoints.py).
- **Doc refresh:** Updated MEMORY.md, SERVICES.md, BLOCKED.md, BUILD-MANIFEST.md (Tier 11 added). All docs brought to current reality.

### Key findings from audit
- FOUNDRY reasoning model uses `--kv-cache-dtype fp8_e5m2` — should be `auto` per safety rules (OK for Qwen3, NOT for Qwen3.5)
- FOUNDRY reasoning model uses `--tool-call-parser hermes` — correct for Qwen3 (not Qwen3.5)
- Workshop missing `--max-num-batched-tokens 2096` in running process (in Ansible but not yet applied)
- VAULT disk at 88% (143TB/164TB) — not critical but worth monitoring
- GPU 4 on FOUNDRY completely idle — embedding model not running
- DNS resolution between nodes uses IPs only, hostnames don't resolve

### Current blockers
- NordVPN credentials needed for qBittorrent + Gluetun (6.5)
- Anthropic API key needed for Quality Cascade cloud escalation (8.5)
- Google Drive rclone OAuth needed (`~/.local/bin/rclone config`) for Personal Data ~40% (10.8)
- Photo Analysis blocked on Qwen3.5 multimodal + vLLM 0.17+ (10.10)

### What's next (Tier 11 priorities)
- 11.1: Port GWT Attention Allocator from Kaizen (salience scoring upgrade)
- 11.2: Port Preference Learning Engine from Hydra
- 11.3: Workspace State Machine from Kaizen
- 11.4: Agent Coalition Formation (GWT Phase 3)
- 11.5: Autonomous Research Loops from Hydra
- 11.6: Experience Memory (GWT Phase 4)

### Quick wins still open
- Restart embedding model on FOUNDRY GPU 4
- Full Ansible convergence (dry run → apply)
- Fix DNS resolution between nodes (add /etc/hosts entries via Ansible common role)

### Git state
- Branch: main, 1 commit ahead of origin
- Latest: `ad68cba` feat: add vault-langfuse + vault-open-webui roles, upgrade Workshop to Qwen3.5-35B-A3B
- DEV node: AMD 9900X + RTX 5060Ti (updated from i7-13700K + 3060)

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
