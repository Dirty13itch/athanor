# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-25 (Session 19: Autonomous Workforce — Task Engine + Scheduler)

### What happened
- **Task Execution Engine (8.1):** `tasks.py` — Redis-backed queue, background worker (5s poll, max 2 concurrent), step logging, GWT broadcasting. Delegation tools. API: POST/GET /v1/tasks, stats, cancel. MCP bridge: 14 tools. Dashboard Task Board page.
- **Proactive Agent Scheduler (8.2):** `scheduler.py` — asyncio-based per-agent intervals. Redis-tracked last-run. API: GET /v1/tasks/schedules.
- **Execution Tools (8.3):** `read_file`, `write_file`, `list_directory`, `search_files`, `run_command`. Coding Agent 9 tools, General Assistant 9 tools.
- **Task quality improvements:** `_build_task_prompt()`, `_maybe_retry()`, `_cleanup_old_tasks()` added to tasks.py.
- **Massive research sweep:** 26 parallel agents (14 model categories + 5 hardware audits + 3 resource strategies + 4 cloud/cascade). 21 research docs + 5 hardware audits + master synthesis (docs/research/2026-02-25-master-synthesis.md).
- **Key findings:** Qwen3.5-27B (72.4% SWE-bench) replaces Qwen3-32B-AWQ. vLLM v0.15.0+ critical blocker for DeltaNet. BFCL V4 correction: 48.71% not 68.2%. 99.13% GPU idle. 5090 zero requests. DEV has RTX 3060 12GB (not RX 5700 XT). Qdrant backups working (VAULT audit was wrong). VAULT Hyper M.2 card has 4 empty slots. MTU mismatch Node 2 (9000) vs Node 1/VAULT (1500).
- **Backup script fix:** `backup-qdrant.sh` default path corrected to `/mnt/vault/data/backups/`.

### Current blockers
- NordVPN credentials needed for qBittorrent + Gluetun (6.5)
- Tailscale needs UDM Pro SSH + Tailscale account (6.8)
- **vLLM v0.15.0+ needed** — unlocks DeltaNet (Qwen3.5), NVFP4, SageAttention2, EAGLE-3 (NGC image currently v0.11.1)
- 3 Crucial P310 NVMe drives location unknown (VAULT Hyper M.2 card empty)

### What's next (P1 quick wins from synthesis)
- Replace DEV ethernet cable (100 Mbps → 1 Gbps)
- Mount Node 1 nvme1n1 (1 TB Crucial P310 unused)
- Repurpose 5090 (zero-request Qwen3-14B → useful workload)
- Add speculative decoding (Qwen3-0.6B draft model)
- Fix MTU mismatch (Node 2 at 9000, Node 1/VAULT at 1500)
- Tune TCP buffers for 10GbE (208 KB → 16 MB)
- Move embedding to CPU (FastEmbed on EPYC, free GPU 4 VRAM)
- Deploy Qwen3-Reranker-0.6B on GPU 4
- Update hardware inventory with 6 corrections found by audits

### Git state
- Branch: main, all pushed to origin
- Latest: `49b2aaf` feat: P1 quick wins — kernel tuning, Qdrant ulimit, inventory corrections

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
| 19 | 2026-02-25 | Autonomous Workforce + Research Sweep | Task Engine (8.1), Scheduler (8.2), Exec Tools (8.3). 26-agent research sweep: 21 research + 5 hardware audit docs. Master synthesis. 6 inventory corrections. |
