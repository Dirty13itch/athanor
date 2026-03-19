# BUILD-MANIFEST.md — Autonomous Build Queue

Updated: 2026-03-19 12:00 PDT

## Queue

### P1 — High Value (unblocked)
- [ ] Auto_gen Best-of-N: increase AUTO_PORTRAITS from 3 to 4
- [ ] Integrate CLI router into subscription-burn.py (register_router_endpoints)
- [ ] Overnight coding dry run test
- [ ] Headscale node registration (install tailscale on DEV, FOUNDRY, WORKSHOP, VAULT)
- [ ] Continue.dev on DESK for free local autocomplete via Ollama
- [ ] VAULT shareCacheFloor fix (reduce from 2TB to 50GB in /boot/config/share.cfg)

### P2 — Nice-to-Have
- [ ] Claude Code plugins install (7 identified)
- [ ] Performer data enrichment from DESK xlsx sources
- [ ] DashScope key regeneration (sk- prefix)
- [ ] LTX 2.3 test video generation (workflow loaded, model downloaded)

### Blocked (need Shaun)
- [ ] Free API keys: Groq (console.groq.com), Cerebras, Codestral (codestral.mistral.ai)
- [ ] Optional paid: DeepSeek, Venice API keys

## Done (80+ items across 3 sessions)
- [x] Full CLI tool stack (11 tools: claude, codex, gemini, kimi, aider, kilo, GSD, greywall, openfang, claude-squad, gh)
- [x] Subscription burn scheduler DEV:8065 (8 subs, 4 windows, waste alerts)
- [x] CLI routing layer (861 lines, embedding classification, self-learning)
- [x] n8n workflows (Morning Briefing 7am + Health Digest 6hr)
- [x] APScheduler (25 autonomous agent jobs on FOUNDRY)
- [x] LiteLLM cleaned (19 models, zero Anthropic API, local-only fallbacks)
- [x] PuLID Flux II upgraded + workflow templates fixed + verified (92s on 5090)
- [x] LTX-Video 2.3 installed (90 nodes, 43GB model + upscalers)
- [x] Stash GraphQL theme weighting (dual-source merge)
- [x] Auto_gen scorer integrated (Best-of-N scoring)
- [x] LoRA training script (730 lines) + ai-toolkit installed
- [x] Backbone cherry-pick (63 files, 9,627 lines) + reconciliation (1,802 lines)
- [x] Memory tiers ALL 6 OK (PG password + symlinks)
- [x] Dashboard DEV:3001 serving
- [x] OpenFang Telegram bot + Athanor system prompt + systemd service
- [x] Semantic Router DEV:8060 (5 content governance routes)
- [x] RECOVERY.md (577 lines disaster recovery)
- [x] MEMORY.md restructured (247->136 lines + 5 topic files)
- [x] All systemd services hardened with restart policies
- [x] Cluster health timer (5-min), Uptime Kuma (8 monitors)
- [x] Vaultwarden, Headscale deployed on VAULT
- [x] ComfyUI moved to GPU 0 (5090 32GB, was OOM on GPU 1)
- [x] Abliterated-35B evaluated (keeping JOSIEFIED, VRAM constraint)
- [x] Overnight coding script + 2am cron
- [x] Alertmanager webhook on agent server
- [x] Whisparr 63TB Tdarr library + cleanup crons
- [x] Deep research: 90+ orchestrators, Ruflo rejected (facade)
