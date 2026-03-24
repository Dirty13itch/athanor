# BUILD-MANIFEST.md

Updated: 2026-03-24 00:10 CDT — Session 58+

## Current State

All services operational. Git main pushed to origin. 365-commit merge complete.

### Recently Completed (Session 58)
- Workshop vLLM restored (Ollama displaced, disabled from boot)
- GPU orchestrator Redis auth fixed
- Workshop port drift (8000→8010) fixed across 7 runtime files
- Git convergence: merged 365 commits, resolved 3 EoBQ conflicts
- Script migration to cluster_config.py: 38/38 complete
- Credential rotation: LiteLLM key, complete (commit 7450cd0)
- Stash face tagger: complete (~400 LOC, InsightFace/ArcFace)

## Remaining Work

### P0 — In Progress
- **LTX 2.3 video generation** — Model downloaded, ComfyUI-LTXVideo node not installed. Needs: install node, create workflow, test via gpu-swap.sh

### P1 — Active
- **Self-editable core memory** — Agents read/write own persona blocks in Redis. Building now.
- **EoBQ SoulForge completion** — DNA system exists, needs wiring to game engine. Building now.
- **Dashboard hardening** — TypeScript check, config update, E2E tests. Building now.
- **Agent server deploy** — Redeploy to FOUNDRY with port fixes. Pending code tracks.

### P1 — Backlog
- Dashboard route migration D.3 (from tactical plan)
- Contract freezing D.5-D.8 (from tactical plan)
- HERS Hand config for OpenFang
- Arize Phoenix (deferred — LangFuse covers tracing)

### P2 — Backlog
- Continue.dev on DESK (Windows)
- Stash face recognition pipeline (tagger complete, need auto-scheduling)
- SD WebUI Forge on DESK
- HunyuanVideo 1.5 eval (alternative to LTX 2.3)
- Custom MLP scorer training (aesthetic predictor fine-tune)
- Dia 1.6B TTS for EoBQ dialogue

### Blocked
- SABnzbd credentials (Shaun)
- Performer xlsx from DESK (Shaun)
- Google Drive rclone OAuth (Shaun)
- Hardware changes G.1-G.5 (physical)
- 5090 creative-only transition (requires LiteLLM reroute first)

## Infrastructure Running
- OpenFang: DEV:4200 (Telegram bot)
- Semantic Router: DEV:8060 (content classification)
- Subscription Burn: DEV:8065 (4 windows/day)
- Overnight Ops: systemd timer (11 PM)
- gpu-swap.sh: Workshop 5090 time-sharing

## Done: 100+ items across 58 sessions
See STATUS.md for full history.
