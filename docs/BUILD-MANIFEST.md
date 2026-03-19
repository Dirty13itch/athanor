# BUILD-MANIFEST.md — Autonomous Build Queue

Updated: 2026-03-19 09:00 PDT

## Queue

### P0 — Blocking
- [ ] LiteLLM cloud API keys: 20+ unhealthy endpoints need OPENAI, MISTRAL, CODESTRAL, VENICE, OPENROUTER, GOOGLE, ZAI, MOONSHOT, DEEPSEEK, GROQ, CEREBRAS keys
- [ ] n8n API key: generate via VAULT:5678 web UI

### P1 — High Value
- [ ] Auto_gen Best-of-N: increase AUTO_PORTRAITS from 3 to 4, keep highest scoring
- [ ] Backbone branch merge: codex/backbone-wip-sync-20260313 (71K lines, needs cherry-pick)
- [ ] Headscale node registration: install tailscale on all nodes
- [ ] ai-toolkit install on WORKSHOP for LoRA training execution
- [ ] n8n workflows: morning briefing, RSS processor, health digest (needs API key)

### P2 — Nice-to-Have
- [ ] Continue.dev on DESK for free local autocomplete
- [ ] Superset desktop on DESK (built, needs install)
- [ ] Claude Code plugins (7 identified, install from active session)
- [ ] Performer data enrichment from DESK xlsx sources
- [ ] Model eval: abliterated-35B on WORKSHOP
- [ ] DashScope key regeneration

## Done (This Session — 2026-03-19)
- [x] APScheduler: 25 autonomous jobs on FOUNDRY agent server
- [x] PuLID Flux II: upgraded on WORKSHOP + workflow templates fixed
- [x] OpenFang: provider fix + Athanor system prompt + Telegram working
- [x] LoRA training script: 730 lines, dry-run verified
- [x] Greywall v0.2.7 + Claude Code sandbox profile
- [x] GSD v1.26.0 + Claude Code hooks
- [x] Kimi CLI v1.24.0 (agent swarm access)
- [x] WORKSHOP vLLM restarted (was down 2 days)
- [x] BUILD-MANIFEST.md created
- [x] CLAUDE.md + MEMORY.md updated
- [x] Stash GraphQL theme weighting (agent in progress)

## Done (Previous Session — 2026-03-18)
- [x] Kilo Code CLI v7.0.50 + 9-mode config
- [x] 5 MCP servers (Context7, GitHub, Sequential-Thinking + 2 existing)
- [x] Semantic Router DEV:8060 (5 routes)
- [x] LiteLLM overhaul (uncensored, vision, fallbacks, timeouts)
- [x] vLLM coordinator + coder restarts
- [x] Aesthetic Scorer integrated with auto_gen
- [x] Overnight coding script + 2am cron
- [x] Alertmanager webhook on agent server
- [x] Vaultwarden, Uptime Kuma, Headscale deployed
- [x] DESK Ollama (qwen3:8b on RTX 3060)
- [x] Performer merge (121/801 enriched)
- [x] Whisparr 63TB Tdarr library + cleanup cron
- [x] Cluster health check (5-min timer)
- [x] GitHub PAT + CodeRabbit
- [x] Tdarr server restarted (was ENOSPC)
