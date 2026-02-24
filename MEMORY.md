# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-24 (Session 8: Post-Deployment Hardening)

### What happened
- Pushed 3 unpushed commits to origin/main (media stack, autonomy fix, build system)
- Fixed git remote: switched from SSH to HTTPS (gh credential helper) — SSH key not registered with GitHub
- Verified full monitoring pipeline: Prometheus 5/5 targets UP, Grafana healthy (v12.3.3)
- Verified all 7 GPUs reporting via DCGM (Node 1: 5 GPUs 28-40°C, Node 2: 2 GPUs 30-38°C)
- Verified all 10 VAULT containers have `restart=unless-stopped`
- Verified NFS mounts healthy: Node 1 (models+data+appdata), Node 2 (models+data)
- Updated BUILD-ROADMAP.md: marked Phase 5 items complete, added remaining config tasks
- Node memory confirmed: Node 1 = 220 GB, Node 2 = 125 GB

### Key findings
- DEV→Node SSH now works (athanor_mgmt key, via ssh-agent) — blocker from Session 7 resolved
- Git SSH to GitHub does NOT work — id_ed25519 key not added to GitHub. Using HTTPS via gh auth instead
- Node 2 missing `/mnt/vault/appdata` mount — not critical (models+data are the important ones)
- VAULT data array at 89% capacity (146T/165T) — worth monitoring

### Current blockers
- HA onboarding requires Shaun in browser (http://192.168.1.203:8123)
- Sonarr/Radarr/Prowlarr need indexer config via Prowlarr UI
- SABnzbd needs Usenet provider credentials
- NordVPN credentials needed for qBittorrent + Gluetun
- Grafana MCP tool needs permission approval in Claude Code settings

### What's next (from BUILD-MANIFEST.md)
- P0: LiteLLM routing layer (item 1.2)
- P0: Deploy Qdrant vector DB (item 1.4)
- P1: Add GitHub SSH key to account (or keep using HTTPS)
- P1: Monitor VAULT data array capacity (89% full)

### Git state
- Branch: main
- All commits pushed to origin
- No uncommitted changes (pending: roadmap + memory updates)

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
