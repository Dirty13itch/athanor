# BUILD-MANIFEST.md — Autonomous Build Queue

Items for overnight coding agents and autonomous sessions.
Priority: P0 (blocking) > P1 (high value) > P2 (nice-to-have)

## Queue

### P0 — Blocking / Broken
- [ ] **LiteLLM cloud API keys**: 25 unhealthy endpoints. Need OPENAI, MISTRAL, CODESTRAL, VENICE, OPENROUTER, GOOGLE, ZAI, MOONSHOT, DEEPSEEK, GROQ, CEREBRAS keys added to container env on VAULT
- [ ] **n8n API key**: Generate via web UI at VAULT:5678 → Settings → API → Create key

### P1 — High Value
- [ ] **APScheduler in agent server**: Add scheduled autonomous agent execution to FOUNDRY:9000 (IN PROGRESS via agent)
- [ ] **PuLID Flux II upgrade**: Swap balazik→lldacing on WORKSHOP ComfyUI (IN PROGRESS via agent)
- [ ] **Stash GraphQL theme weighting**: Content-weighted theme selection in auto_gen scheduler (IN PROGRESS via agent)
- [ ] **Auto_gen Best-of-N**: Generate 4 images per prompt, keep highest scoring (scorer is integrated, need to increase AUTO_PORTRAITS from 3 to 4)
- [ ] **Workflow templates for PuLID Flux II**: Update pipelines.py after node swap (new loader nodes: PulidFluxModelLoader, PulidFluxInsightFaceLoader, PulidFluxEvaClipLoader)
- [ ] **Backbone branch merge**: codex/backbone-wip-sync-20260313 has 71K lines. Needs careful review, likely cherry-pick not full merge
- [ ] **Headscale node registration**: Install tailscale on DEV, FOUNDRY, WORKSHOP, VAULT. Register with preauthkey

### P2 — Nice-to-Have
- [ ] **Continue.dev**: Install on DESK VS Code for free local autocomplete via Ollama
- [ ] **Superset desktop**: Install built Electron app on DESK for parallel agent GUI
- [ ] **Claude Code plugins**: Install from active session: code-review, feature-dev, code-simplifier, commit-commands, claude-md-management, context7, playwright
- [ ] **n8n workflows**: Morning briefing, RSS processor, health digest (needs API key first)
- [ ] **Performer data enrichment**: Run build_performers_db.py from DESK xlsx sources to fill remaining 680 empty waist/hip records
- [ ] **Model eval: abliterated-35B**: Test Huihui-Qwen3.5-35B-A3B-abliterated on WORKSHOP as uncensored replacement
- [ ] **DashScope key**: Regenerate proper API key (sk- prefix) from dashscope.console.aliyun.com
- [ ] **Tdarr Whisparr scan**: Trigger initial scan of 63TB library (weekly cron set for Sunday 3:30am)

## Completed This Session
- [x] OpenFang fix (provider default→ollama) + Athanor system prompt
- [x] Greywall v0.2.7 + Claude Code sandbox profile
- [x] Kimi CLI v1.24.0, GSD v1.26.0
- [x] LoRA training script (730 lines)
- [x] Auto_gen scorer verified integrated
- [x] WORKSHOP vLLM restarted
- [x] CLAUDE.md + MEMORY.md updated
- [x] Gemini gc alias, claude-squad configured
- [x] Superset built (for DESK)

## Overnight Coding Assignments
| Project | Tool | Subscription | Task File |
|---------|------|-------------|-----------|
| athanor | Claude Code (GSD) | Max 20x | .claude/tasks/next-overnight.md |
| Field_Inspect | Codex CLI | ChatGPT Pro | .tasks/next.md |
| ulrich-energy-auditing | Aider | Local Qwen | .tasks/next.md |
| amanda-med-tracker | Aider | Local Qwen | .tasks/next.md |
