# Athanor Status

**Last updated:** 2026-03-23 23:25 CDT
**Session:** Session 58 — System Recovery + Git Convergence

## Session Results — 19 Actions Executed

### Infrastructure Fixes (10)
1. Auto_gen LLM endpoint restored (12 days dead → 3 images generated)
2. Langfuse API keys set (4 days dark → tracing active)
3. Agent Qdrant URL fixed (FOUNDRY→VAULT) + timeout 600→1800s
4. WORKSHOP models on local Gen5 NVMe (14x faster loading)
5. LiteLLM routing overhauled (24min→10s failover)
6. MCP Tool Search fixed (auto:5→true)
7. vLLM swap-space added to coder+node2 (pending restart)
8. GSD v1.26.0 installed on DEV
9. Crucible (4 containers) + old FOUNDRY Qdrant removed
10. Vision --language-model-only removed from coordinator (pending restart)

### New Deployments (9)
11. vllm-node2 stopped, 5090 freed (32GB→2MB) for creative gen
12. LiteLLM rerouted all WORKSHOP aliases to FOUNDRY
13. Whisparr deployed (VAULT:6969, adult content arr)
14. Bazarr deployed (VAULT:6767, automated subtitles)
15. Recyclarr deployed (VAULT, daily TRaSH sync)
16. Seerr deployed (VAULT:5055, request management)
17. Aesthetic Predictor V2.5 deployed (WORKSHOP:8050, image scoring)
18. JOSIEFIED-Qwen3-8B deployed via Ollama (WORKSHOP:11434)
19. LiteLLM uncensored route → JOSIEFIED via Ollama

### Documentation
- MASTER-PLAN.md (619 lines, canonical strategic reference)
- Tactical plan (2395 lines, implementation details)
- 5 guide documents (overview, daily ops, system map, workflow maps, doc index)
- CLAUDE.md updated with cloud-first subscription strategy
- All committed and pushed to GitHub

## Next Actions

### Blocked on Shaun
1. Install Roo Code in VS Code (RooVeterinaryInc.roo-cline)
2. Set up CodeRabbit (app.coderabbit.ai, GitHub OAuth)
3. Rotate 3 API keys (Mistral, Z.ai, HuggingFace)
4. Encrypt Usenet credentials on Desktop
5. Schedule vLLM coordinator restart (vision + swap-space)
6. Set up offsite backup (Duplicati → Backblaze B2)

### Next Autonomous Work
7. Set up Semantic Router service on DEV
8. Add APScheduler to LangGraph agent server
9. Update delegate skill with auto-dispatch logic
10. Set up first overnight autonomous coding run
11. Performer data merge (script ready, 801 records)
12. MEMORY.md full rewrite (14+ inaccuracies)
13. Merge automation-backbone branch (backbone.py)
14. Deploy Vaultwarden, Uptime Kuma, Headscale

## Cluster Health (verified 2026-03-23)
- FOUNDRY: 5 GPUs loaded, coordinator (Qwen3.5-27B-FP8 TP=4 :8000), coder (devstral-small-2 :8006), agents (9 agents :9000), GPU orchestrator (:9200)
- WORKSHOP: 5090 running vLLM (Qwen3.5-35B-A3B-AWQ-4bit :8010), 5060Ti ComfyUI. Dashboard:3001, EoBQ:3002, Ulrich:3003
- DEV: Embedding:8001, Reranker:8003
- VAULT: 50+ containers, LiteLLM:4000, full stack
- **Recovered this session:** Workshop vLLM (Ollama displaced), GPU orchestrator (Redis auth)
- **Ollama disabled on Workshop** (was conflicting with vLLM for GPU memory)

## Session: 2026-03-18/19 — Athanor Layer Build Execution

### Completed (Batch 1-7 + extras)
- Kilo Code CLI v7.0.50 installed, 9-mode YAML config written
- 5 MCP servers (Context7, GitHub w/ PAT, Sequential-Thinking + 2 existing)
- Tokscale + Claude Usage Monitor installed
- GSD v1.26.0 verified, claude-squad verified
- Semantic Router DEV:8060 (systemd, 5 routes, all-MiniLM-L6-v2)
- LiteLLM: uncensored→JOSIEFIED, vision→FOUNDRY, groq-llama free tier, content_policy_fallbacks, stream_timeout=10/num_retries=0
- vLLM coordinator restarted (vision enabled, swap-space 32)
- vLLM coder restarted (swap-space 16)
- Aesthetic Scorer integrated with auto_gen (Best-of-N, score_history.json)
- Stash GraphQL theme weighting (20 tag→theme boost mappings)
- Context compression pipeline (local 50K→2K→cloud, 25x savings)
- Overnight coding script + 2am cron (Claude Max + Codex + Aider + Copilot)
- Overnight queue YAML (multi-project subscription assignment)
- OpenFang v0.4.9 deployed DEV:4200, @athanor_ops_bot Telegram bot connected
- GitHub PAT wired into MCP + gh auth (Dirty13itch)
- CodeRabbit installed on GitHub
- Vaultwarden deployed VAULT:8222
- Uptime Kuma deployed VAULT:3009 (8 monitors, admin/AthanorKuma2026!)
- Headscale deployed VAULT:8443 (user: athanor, preauthkey created)
- DESK Ollama running (qwen3:8b on RTX 3060)
- Performer data merge (121/801 enriched waist/hip)
- Tdarr server restarted (was ENOSPC), node active, 1 GPU worker 520 FPS
- Cluster health check systemd timer (5-min interval)
- gpu-swap.sh copied to repo
- Aider config updated to Qwen3.5
- DEV /data partitioned (worktrees/models/rag-cache/sandbox)
- Model upgrade research: 122B NOT feasible, abliterated-35B VIABLE

### In-Progress (agents running)
- Whisparr 63TB as 3rd Tdarr library
- Alertmanager webhook on agent server
- Tdarr workdir cleanup cron

### Remaining
- PuLID Flux II upgrade (~1hr, lldacing version)
- n8n→Miniflux→agents webhook wiring (needs Miniflux creds)
- DashScope key (rejected, low priority)
- Headscale node registration (physical access)
- Backbone branch merge (71K lines, needs careful review)
- LoRA training automation (train_subject_lora.py)

## Session 3: 2026-03-19 Morning — Subscription Orchestration + P0 Fixes

### Critical Fixes (P0)
- Memory Procedural + Vault tiers: FIXED (wrong PG password + path symlinks)
- Dashboard DEV:3001: FIXED (symlinked to quarantine source, Next.js serving)

### Major Deployments
- Subscription Burn Scheduler (DEV:8065): 8 subs tracked, 4 daily windows, waste alerts
- subscription-status.sh CLI: 4 subcommands (status, waste, schedule, tasks)
- 26 initial tasks across 4 subscription task queues
- APScheduler: 25 autonomous jobs on FOUNDRY agent server
- PuLID Flux II: upgraded on WORKSHOP + pipelines.py fixed
- Stash GraphQL theme weighting: dual-source merge (performers.json + live Stash)
- LoRA training script: 730 lines, dry-run verified
- Greywall v0.2.7 + Claude Code sandbox profile
- GSD v1.26.0 installed with hooks
- Kimi CLI v1.24.0 (agent swarm access)

### Research Completed
- All 9 subscription limits, reset windows, optimal burn strategies
- All model versions current to March 2026 (GPT-5.4 released 2 days ago)
- 90+ multi-agent orchestration tools evaluated
- Top 3: Ruflo (21.6K stars, Q-learning router), multi-agent-shogun, claude-octopus
- Free tiers identified: Cerebras GPT-OSS-120B (2400 tok/s), Groq Llama 3.3 70B

### System Status After Session
- All 6 memory tiers: OK
- Dashboard: serving at DEV:3001
- 9 agents: healthy with 25 scheduled jobs
- Subscription scheduler: tracking $543/mo across 8 subscriptions
- OpenFang: running on Telegram
- All vLLM instances: healthy
- LiteLLM: 9 healthy (local + Anthropic), 20 unhealthy (missing cloud keys)

## Session 3: 2026-03-19 Morning

### P0 Fixes
- Memory tiers: ALL 6 OK (PG password + symlinks)
- Dashboard: DEV:3001 serving (symlinked source)

### Deployed
- Subscription Burn Scheduler DEV:8065 (8 subs, 4 windows, waste alerts)
- APScheduler 25 jobs on FOUNDRY agent server
- PuLID Flux II on WORKSHOP + workflow fix
- Stash GraphQL theme weighting (dual-source)
- LoRA training script (730 lines)
- Greywall v0.2.7 + GSD v1.26.0 + Kimi CLI v1.24.0

### Research
- 90+ multi-agent orchestrators evaluated, top pick: Ruflo (21.6K stars)
- All subscription limits/windows documented
- All model versions verified current (GPT-5.4 released Mar 17)

## Session 3 Final (2026-03-19) — Complete Build Summary

### Total items deployed across 3 sessions: 75+

### Session 3 Morning Highlights
- Subscription burn scheduler (DEV:8065): 8 subs, 4 daily windows, waste alerts
- CLI routing layer (861 lines): intelligent task→subscription matching, self-learning
- n8n workflows: Morning Briefing (7am) + Health Digest (6hr) → ntfy
- ai-toolkit installed on WORKSHOP (ready for LoRA training)
- Memory Procedural + Vault tiers FIXED
- Dashboard FIXED (DEV:3001)
- Anthropic API removed from LiteLLM (zero per-token spending)
- PuLID II end-to-end VERIFIED (92s generation on RTX 5090)
- ComfyUI moved to GPU 0 (5090 32GB, was OOM on GPU 1)
- Backbone cherry-pick: 63 files, 9,627 lines of governance framework
- RECOVERY.md: 577-line disaster recovery playbook
- MEMORY.md restructured: 247→136 lines + 5 topic files
- All systemd services hardened with restart policies
- OpenFang: proper systemd service (was nohup hack)
- Ruflo evaluated and REJECTED (source audit: Claude-only facade)
- 90+ multi-agent orchestrators researched
- All subscription limits/windows documented
- All model versions verified current (March 2026)

### System Status: ~90%
- All 6 memory tiers: OK
- Dashboard: serving
- 25 APScheduler agent jobs active
- Subscription scheduler: tracking $543/mo
- CLI router: 10 task types, 6 CLIs, self-learning
- n8n: 2 active workflows
- PuLID II: verified working
- ai-toolkit: ready for LoRA training
- LiteLLM: 19 models, zero surprise spending

## Session 4: 2026-03-19 Evening — System Audit Batch D

### D.4: Agent Documentation Alignment
- Created `docs/AGENTS.md` — canonical agent roster document
- 9/9 agents verified online via FOUNDRY:9000/health
- All agent schedules, trust classes, tools, and content policies documented
- APScheduler: 25 background jobs documented (14 global + per-agent schedules)
- Governor autonomy levels (A-D) and inference-aware scheduling documented
- Dependencies: Redis UP, Qdrant UP, LiteLLM UP, coordinator UP, embedding UP
- Issue: worker dependency DOWN ("All connection attempts failed")

### D.9: MCP Permission Cleanup
- Reviewed `.mcp.json`: 5 MCP servers (docker, athanor-agents, context7, github, sequential-thinking)
- Reviewed `settings.json` permissions: `allow: [Bash, Read, Write, WebFetch, mcp__*]`
- No orphaned permissions found — `mcp__*` wildcard covers all MCP tools
- All 5 configured MCP servers have valid scripts/packages
- Hooks verified: gsd-check-update.js, gsd-context-monitor.js, gsd-statusline.js

### D.10: MCP Server Additions
- Added `filesystem` MCP server (direct file access across cluster via allowed paths)
- Added `memory` MCP server (persistent cross-session knowledge)
- Existing servers retained: docker, athanor-agents, context7, github, sequential-thinking
- Total: 7 MCP servers configured
- Not added: brave-search (requires paid API key), playwright (already available via plugins)
