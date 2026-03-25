# Athanor Status

**Last updated:** 2026-03-24 22:10 CDT
**Session:** 60h — The Self-Feeding Furnace

---

## System Health: 9/10

| Node | Status | GPUs | Load |
|------|--------|------|------|
| **FOUNDRY** (.244) | UP | 4x5070Ti TP=4 (99%), 4090 (coder idle) | 9 agents, 6/6 deps |
| **WORKSHOP** (.225) | UP | 5090 (vLLM worker), 5060Ti (ComfyUI 36%) | Dashboard, EoBQ, ComfyUI |
| **VAULT** (.203) | UP | Arc A380 | 55 containers, Redis, Qdrant, LiteLLM |
| **DEV** (.189) | UP | 5060Ti (embedding+reranker) | Ops center, claude-squad |

**Services:** 28/29 healthy (HA degraded — needs auth token)
**Agents:** 9/9 healthy, scheduler active, deep work prompts deployed
**Tasks:** 504 completed, 0 running, avg 142s duration
**Gallery:** 378 EoBQ assets (portraits, scenes, videos), pipeline producing ~40/hr
**Dashboard:** 35 pages, all 200, mission control v2 live

---

## What Was Built (Sessions 58-60h)

### Infrastructure
- Qdrant URL fix (.244→.203) — root cause of 74% failure rate
- LiteLLM routing fix — 6 dead Ollama routes → Workshop vLLM
- Scheduler fix — loop died after first tick, now running perpetually
- ComfyUI PyTorch sm_120 — Blackwell GPU kernels working
- PuLID face injection on Blackwell — first ever on 5060 Ti
- LTX 2.3 video gen — GGUF bypasses sm_120, <30s per clip
- MCP 401 fix — API token added to .mcp.json
- Per-agent timeouts — deep work agents get 15-30 min (was 10)

### Dashboard
- Mission control homepage v2 — cockpit instrument panel
- Gallery feedback system — rate, approve, flag, refine, compare
- Gallery UX — sorting, character filter, batch ops, enhanced lightbox
- RightNowCard, LensTabs, ClusterCompact, SubscriptionBurn components
- Gallery cap increased from 100 to 500 items
- Proactive attention system (Codex session)

### Agents
- Deep work prompts for all 9 agents (Phase 1)
- Scheduler tasks bypass approval gating (Phase 2)
- Quality cascade chains — generate → evaluate → refine (Phase 3)
- Overnight furnace script for claude-squad (Phase 4)
- Think tag stripping fix for clean task output

### Creative Pipeline
- 378 EoBQ assets generated autonomously
- Per-queen physical blueprints from master doc
- Body skew: fit + busty ("tits on a stick") baseline
- Stash reference photos pulled for 12/21 queens
- LTX 2.3 T2V tool added to creative-agent

### Operational
- Kaizen skill — perpetual improvement loop with depth mandate
- Design refinement loop — color semantics, typography, contrast rules
- B2 backup script + research doc
- Stash face tagger Ansible role
- 113 GB stale models cleaned from FOUNDRY
- 13 stale worktrees removed

---

## Active Now
- 2 design agents building in worktrees (responsive + visual refinement)
- ComfyUI generating EoBQ portraits at ~40/hr
- Agent scheduler running deep work cycles every 10-30 min
- Quality cascades scheduled every 4h (creative) and 6h (code)

---

## Next Actions
1. Merge design agent results when complete
2. Deploy responsive + design fixes to Workshop
3. Shaun: activate overnight cron (`0 2 * * *`) on DEV
4. Shaun: review gallery at workshop:3001/gallery — rate images
5. Continue kaizen loop — next weakest link after design agents merge

---

## Blocked on Shaun
- Overnight cron activation (uses --dangerously-skip-permissions)
- Backblaze B2 account creation (backup script ready)
- 10GbE network (physical switch rack)
- n8n Signal Pipeline QR code scan

---

## Session Log

| Session | Summary |
|---------|---------|
| 60h | Self-feeding furnace: 5 phases (deep prompts, autonomous execution, cascades, overnight, burn rate). Kaizen skill. MCP 401 fix. Gallery cap fix. Per-agent timeouts. |
| 60g | Mission control v2 (937-line cockpit). LTX video tool. Design refinement loop. |
| 60f | LTX 2.3 unblocked. Face tagger built. n8n research. Dashboard 19/19 APIs. |
| 60 | PuLID on Blackwell. 98→378 EoBQ assets. Gallery feedback. Body skew. |
| 59 | Deep audit: Qdrant URL, LiteLLM routing, dashboard creds, scheduler fix. |
| 58 | System recovery: vLLM worker, GPU orchestrator, service mesh, git convergence. |
