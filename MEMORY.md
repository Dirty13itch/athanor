# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-02-24 (Session 7: VAULT Media Stack + Claude Code Autonomy)

### What happened
- Deployed all 10 VAULT containers via Ansible (Prometheus, Grafana, Plex, Sonarr, Radarr, Prowlarr, SABnzbd, Tautulli, Stash, Home Assistant)
- Resolved 7 deployment blockers: vault secrets, SSH keys, Python on Unraid (OpenSSL compat), node IP vars, Docker SDK version pinning
- Plex claimed and libraries configured by Shaun
- Fixed Claude Code non-interactive mode — added broad tool permissions to `.claude/settings.local.json`
- Created BUILD-MANIFEST.md for autonomous build execution
- Created `/build` command for self-directed build sessions
- All services verified healthy via `docker ps`

### Key decisions made
- Python 3.12.12 installed to `/boot/extra/` on VAULT for persistence across reboots
- Docker SDK pinned to `<7` and requests to `<2.32` for transport adapter compatibility on VAULT
- Ansible vault password: AthanorVault2026 (stored in `ansible/vault-password`)
- Broad tool permissions in `.claude/settings.local.json` — all Bash, Read, Write, Edit, MCP tools pre-approved

### Current blockers
- DEV/WSL cannot SSH to Node 1 (192.168.1.244) or Node 2 (192.168.1.225) — needs diagnosis
- HA onboarding requires Shaun in browser (http://192.168.1.203:8123)
- NordVPN credentials needed for qBittorrent + Gluetun

### What's next (from BUILD-MANIFEST.md)
- P0: Fix DEV→Node SSH access (item 1.1)
- P0: LiteLLM routing layer (item 1.2)
- P0: Verify/deploy embedding model (item 1.3)
- P0: Deploy Qdrant (item 1.4)

### Git state
- Branch: main
- Unpushed commits: 2 (media stack deploy + autonomy fix)
- No uncommitted changes

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
