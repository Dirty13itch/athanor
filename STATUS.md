# Athanor Status

**Last updated:** 2026-03-29 20:00 PDT
**Session:** Evening Review

---

## Evening Review — 2026-03-29

### Score: 4/10 — Pipeline dark day 8, Dashboard DOWN (new), media-agent runaway loop, home-agent stuck loop day 4

**What happened:** Day 8 with the scheduler fix undeployed. Pipeline mined 148 signals, generated 8 more plans (14 total queued), dispatched zero tasks — same outcome. New regression: **Dashboard is DOWN** (24/25 services, was 25/25). Agent activity was higher than yesterday — general-assistant returned with a full deep cycle, research-agent ran its first real deep research cycle in days (10 intelligence signals), knowledge-agent produced 4 tasks. But media-agent ran 3 identical deep cycles (03:18, 19:11, and past midnight) all flagging the same critical issues with zero resolution — it's now a runaway loop burning capacity. Home-agent ran 2 more stuck-loop cycles (day 4). Lucky-crafting-swing modules still built but never executed in production.

**What ran (March 29):**
- knowledge-agent: Qdrant collection audit (00:30) — success
- home-agent: HA monitoring cycle (14:29) — stuck loop, unavailable entities (day 4)
- knowledge-agent: deep curation cycle (16:11) — Knowledge Health Report produced
- knowledge-agent: last 10 tasks lookup (16:45) — success
- general-assistant: deep operational cycle (16:42) — ran (recovery from yesterday's regression)
- research-agent: deep research cycle (20:14) — 10 high-relevance intelligence signals found
- knowledge-agent: RSS ingest llama.cpp (19:33) — success
- media-agent: deep media cycle (19:11) — CRITICAL ISSUES (3rd cycle, unresolved)
- home-agent: HA monitoring cycle (00:30) — stuck loop
- media-agent: deep media cycle (03:18) — CRITICAL ISSUES
- coding-agent: Qdrant collection check (01:42) — success

**Infrastructure:** 24/25 services. **Dashboard DOWN** (new regression).

---

## Active Plan

**lucky-crafting-swing.md** — "The System That Knows What Shaun Wants"

- Module 1: owner_model.py — BUILT (425 lines, on main)
- Module 2: intent_synthesizer.py — BUILT (376 lines, on main)
- Module 3: quality evaluation via Gemini vision — BUILT (auto_grade_image, commit 845bb52)
- Module 4: feedback loop endpoints — BUILT (feedback.py, commit c68caf8)
- **BLOCKER:** Scheduler fix coded (day 8) but NOT DEPLOYED. Pipeline has never run these modules.

---

## Cluster Health

| Node | Status | GPUs | Notes |
|------|--------|------|-------|
| FOUNDRY | UP | 4x5070Ti + 4090 loaded | All services healthy |
| WORKSHOP | UP | 5090 99% (worker), 5060Ti (ComfyUI) | **Dashboard DOWN** |
| VAULT | UP | 55 containers | — |
| DEV | UP | Embedding + Reranker OK | — |

---

## Alerts (5 firing — all backup-related)

| Alert | Status | Action |
|-------|--------|--------|
| BackupAgeCritical (Qdrant) | REAL — 16 days stale | Blocked on Shaun (Backblaze B2 creds) |
| BackupAgeWarning x3 (stash, athanor, postgres) | REAL | Same |
| BackupAgeWarning (Qdrant) | REAL | Same |

---

## Pipeline Status

**BROKEN — FIX CODED (DAY 8), NOT DEPLOYED**

- Queue depth: 0
- Pending plans: 14 (sitting idle, up from 8)
- Last successful cycle: March 22
- Owner model: never populated Redis (`athanor:owner:profile` missing)
- Fix ready: `projects/agents/src/athanor_agents/scheduler.py` — timeout 120s→600s, TimeoutError handler, CASCADE_TIMEOUT import
- Deploy command:
  ```bash
  rsync -av projects/agents/src/ foundry:/opt/athanor/agents/src/
  ssh foundry "cd /opt/athanor/agents && docker compose build --no-cache && docker compose up -d"
  ssh foundry "docker logs athanor-agents --tail=100 | grep -E 'pipeline|timeout|cycle|owner'"
  ```

---

## Next Actions

### P0 — Deploy scheduler fix (FIRST ACTION, no exceptions, day 8)
```bash
rsync -av projects/agents/src/ foundry:/opt/athanor/agents/src/
ssh foundry "cd /opt/athanor/agents && docker compose build --no-cache && docker compose up -d"
ssh foundry "docker logs athanor-agents --tail=100 | grep -E 'pipeline|timeout|cycle|owner'"
```

### P0 — Diagnose and restore Dashboard (new regression)
```bash
ssh workshop "docker ps | grep dashboard"
ssh workshop "docker logs athanor-dashboard --tail=50"
```

### P0 — Raise MAX_QUEUE_DEPTH 20→100 before unfreezing
- Pipeline will immediately reblock on 14 queued plans otherwise

### P0 — Verify pipeline end-to-end after deploy
- Trigger manual cycle via MCP `trigger_pipeline_cycle`
- Confirm `athanor:owner:profile` populates in Redis
- Confirm intents generated → plans submitted → tasks run

### P1 — Media-agent suppression logic (runaway loop)
- 3 identical cycles today, all critical issues, zero resolution
- Root cause: almost certainly Radarr library root path
- SSH VAULT, check Radarr container logs and library root path config
- Add: after 3 identical critical-issue cycles → suppress, flag for human review

### P1 — Home-agent suppression logic (stuck loop day 4)
- After 3+ identical cycles reporting same entities → suppress, flag for human review
- SSH VAULT, check HA entity state directly — are they genuinely offline or are tools broken?

### P1 — Stash-agent diagnostic
- Last run was empty (silent fail March 28)
- Retry with minimal probe (single tool call: `get_performers`)
- Check Stash API auth/connectivity separately

### P2 — Update lucky-crafting-swing.md (all 4 modules built, plan shows stale status)
### P2 — Dedupe Qdrant knowledge collection
### P2 — Investigate general-assistant scheduling reliability (intermittent runs)

### Blocked on Shaun
- Backblaze B2 credentials (5 backup alerts, Qdrant 16 days stale)
- VAULT storage decision (83%)

---

## Session Log

| Date | Summary |
|------|---------|
| 2026-03-29 EVE | Score 4/10. Pipeline dark day 8 — fix still not deployed. Dashboard DOWN (new). media-agent runaway loop (3x critical issues, 0 resolution). home-agent stuck loop day 4. general-assistant + research-agent recovered. knowledge-agent solid (4 tasks). 14 plans queued, 0 dispatched. |
| 2026-03-28 EVE | Score 3/10. Pipeline dark day 7 — fix still not deployed. home-agent 12x stuck loop in 48h. stash-agent silent fail (repeat). knowledge-agent solid (RSS + curation). media-agent ran with critical issues. general-assistant 0 tasks (regression). |
| 2026-03-27 EVE | Score 4/10. Pipeline dark day 6 — fix still not deployed. general-assistant recovered (quality 0.5). creative + knowledge ran solid cycles. home-agent 6x stuck loop. 4 agents idle. |
| 2026-03-26 EVE | Score 3/10. Fix not deployed — day 5 of dark pipeline. knowledge-agent ran (curation + 2 RSS). media-agent ran. home-agent 9 cycles (stuck loop). general-assistant silent failure. |
| 2026-03-26 AM | Score 5/10. Pipeline broken 4 days (120s timeout death spiral). Fixed scheduler: 600s timeout, TimeoutError handler, CASCADE_TIMEOUT import. Redis MCP auth added. Owner model + synthesizer confirmed built but never ran. Deploy needed. |
| 2026-03-25 EVE | Score 7/10. 10 agent tasks. MCP 401 fixed. Dashboard deployed. Pipeline blocked (51>20). Radarr broken. Knowledge duplicates. Plan day 3 unstarted. |
| 2026-03-24 EVE | Score 6/10. Proactive attention API + banner. Creative 8 tasks. MCP 401 unresolved. |
| 2026-03-24 AM | 401 diagnosed (3-layer). 13 coding tasks pending. |
| 2026-03-23 EVE | Score 6/10. APScheduler fix. 401 unresolved. |
| 2026-03-23 PM | Brain 7 layers, Sentinel 56/56, Governor hardened, APScheduler fix. |
| 2026-03-23 AM | Dashboard DOWN, pipeline DORMANT, 7 alerts. |
