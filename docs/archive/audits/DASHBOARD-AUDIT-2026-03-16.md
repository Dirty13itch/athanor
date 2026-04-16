# Athanor Dashboard Audit Report

> **Archived audit snapshot.**
> This dated audit is retained for historical review only. It is not current authority for provider counts, route status, or live dashboard/runtime truth.

**Date: 2026-03-16 03:58 UTC**
**Target: http://192.168.1.225:3001 (WORKSHOP dashboard)**

---

## EXECUTIVE SUMMARY

**Status: MOSTLY WORKING with significant API route misalignment**

- ✅ **31/31 Dashboard Pages**: All return HTTP 200 with proper HTML
- ✅ **Agent Server Health**: All 9 agents healthy, dependencies up
- ✅ **Working Data Routes**: 10 API routes return real, live data
- ⚠️ **Missing API Routes**: 13 routes return 404 (route names don't match source code)
- 🔴 **Critical Issue**: Dashboard tests expect `/api/` routes that don't exist in codebase

---

## DASHBOARD PAGES (All Working)

All 31 pages return HTTP 200 with proper Next.js HTML:

| Category | Pages | Status |
|----------|-------|--------|
| Core | `/`, `/agents`, `/chat`, `/workspace` | ✅ 200 |
| Workforce | `/tasks`, `/goals` | ✅ 200 |
| System | `/services`, `/monitoring`, `/activity` | ✅ 200 |
| Data | `/conversations`, `/preferences`, `/personal-data` | ✅ 200 |
| Media/Gallery | `/media`, `/gallery`, `/learning`, `/insights` | ✅ 200 |
| Infrastructure | `/terminal`, `/outputs`, `/gpu` | ✅ 200 |
| Phase 5 (New) | `/governor`, `/pipeline`, `/projects`, `/digest`, `/operator`, `/improvement`, `/routing`, `/topology`, `/models`, `/workplanner`, `/review` | ✅ 200 |

---

## API ROUTES STATUS

### WORKING (HTTP 200, Live Data)

1. ✅ `/api/governor` - Returns live governor state with lanes, capacity, posture
2. ✅ `/api/pipeline/status` - Returns pipeline cycles, intents mined, plans created
3. ✅ `/api/projects` - Returns 7 projects (Athanor core, EoBQ, Kindred, Ulrich Energy, etc.)
4. ✅ `/api/agents` - Returns 9 agents with live status, tools, types
5. ✅ `/api/activity` - Returns live conversation logs with tool calls and timestamps
6. ✅ `/api/subscriptions/providers` - Returns 6 provider configs with routing policy
7. ✅ `/api/containers` - Returns live Docker container state on all nodes
8. ✅ `/api/conversations` - Returns agent-user conversation history with full transcripts
9. ✅ `/api/preferences` - Returns preference data (empty but valid)
10. ✅ `/api/improvement/proposals` - Returns improvement proposals (empty but valid)

**Total data volume**: Containers ~50, agents 9, projects 7, conversations 1+, providers 6

---

## MISSING/BROKEN API ROUTES (HTTP 404)

These routes are expected by the audit spec but return HTML 404 pages (route not implemented):

| Route Tested | Actual Route in Code | Status | Note |
|--------------|---------------------|--------|------|
| `/api/plans` | `/api/pipeline/plans` | ⚠️ Wrong path | Exists but audit used wrong prefix |
| `/api/tasks` | `/api/workforce/tasks` | ⚠️ Wrong path | Exists but audit used wrong prefix |
| `/api/goals` | `/api/workforce/goals` | ⚠️ Wrong path | Exists but audit used wrong prefix |
| `/api/workspace` | `/api/workforce/workspace/...` | ⚠️ No root endpoint | Sub-routes exist, no root |
| `/api/models/local` | `/api/models` | ⚠️ Wrong path | `/api/models` works, `/api/models/local` doesn't |
| `/api/subscriptions/cli-status` | NOT FOUND | 🔴 Missing | No equivalent in codebase |
| `/api/subscriptions/routing-log` | `/api/routing/log` | ⚠️ Wrong path | Exists at different prefix |
| `/api/subscriptions/provider-status` | NOT FOUND | 🔴 Missing | No equivalent in codebase |
| `/api/events` | NOT FOUND | 🔴 Missing | No events endpoint exists |
| `/api/metrics` | NOT FOUND | 🔴 Missing | No metrics endpoint exists |
| `/api/notifications` | `/api/workforce/notifications/...` | ⚠️ No root endpoint | Sub-routes exist, no root |
| `/api/briefing` | NOT FOUND | 🔴 Missing | No briefing endpoint exists |
| `/api/improvement/nightly` | NOT FOUND | 🔴 Missing | Only `/api/improvement/proposals` exists |
| `/api/improvement/benchmarks` | NOT FOUND | 🔴 Missing | Only `/api/improvement/proposals` exists |

---

## AGENT SERVER HEALTH (FOUNDRY:9000)

### Health Check
```
GET /health → HTTP 200
Status: healthy
Agents: 9 (all ready)
Dependencies: ALL UP
  - Redis: latency 0ms ✅
  - Qdrant: latency 35ms ✅
  - LiteLLM: latency 24ms ✅
  - Coordinator (FOUNDRY:8000): latency 15ms ✅
  - Worker (WORKSHOP:8000): latency 10ms ✅
  - Embedding (DEV:8001): latency 4ms ✅
```

### Models Endpoint (Agent Server)
```
GET /v1/models/local → HTTP 200
Returns 5 models with live URLs and context windows:
  - coordinator (Qwen3.5-27B-FP8) @ FOUNDRY:8000
  - coder (Qwen3.5-35B-A3B-AWQ-4bit) @ FOUNDRY:8006
  - worker (Qwen3.5-35B-A3B-AWQ) @ WORKSHOP:8000
  - embedding (Qwen3-Embedding-0.6B) @ DEV:8001
  - reranker (Qwen3-Reranker-0.6B) @ DEV:8003
Status: ALL ONLINE
```

### Subscriptions Endpoint (Agent Server)
```
GET /v1/subscriptions/cli-status → HTTP 200
CLI availability:
  - Claude Code: available=false, tasks_today=0
  - Codex CLI: available=false, tasks_today=0
  - Gemini CLI: available=false, quota=1000
  - Aider: available=true, tasks_today=0
```

---

## CRITICAL FINDINGS

### 1. API Route Naming Mismatch
The test spec expected routes like `/api/plans`, `/api/tasks`, `/api/goals` but the codebase implements them under `/api/pipeline/` and `/api/workforce/` prefixes. This suggests either:
- Dashboard source code follows different naming conventions than tests expected
- Tests were written against an older or different API contract
- Routes were refactored but test specs weren't updated

**Impact**: Pages that depend on these routes may fail to load data or display static/fixture content.

### 2. Missing Endpoints (No Code Found)
These routes have no equivalent anywhere in the codebase:
- `/api/subscriptions/cli-status` (but exists at agent server: `/v1/subscriptions/cli-status`)
- `/api/subscriptions/provider-status` 
- `/api/events`
- `/api/metrics`
- `/api/briefing`
- `/api/improvement/nightly`
- `/api/improvement/benchmarks`

**Impact**: Pages needing these endpoints (`/improvement`, `/digest` possibly others) are likely showing empty state or stale data.

### 3. Root Endpoints Missing
Some routes exist as parameterized sub-routes but lack root endpoints:
- `/api/workspace` (exists as `/api/workforce/workspace/[itemId]/endorse`)
- `/api/notifications` (exists as `/api/workforce/notifications/[notificationId]/resolve`)

**Impact**: Pages trying to fetch all items from these routes will fail.

---

## DATA QUALITY CHECK

### Real Data Verified
- ✅ Agents: 9 unique agents with real tools
- ✅ Containers: 50+ real containers on 2 nodes (dashboard, vllm, comfyui, etc.)
- ✅ Projects: 7 real projects (Athanor, EoBQ, Kindred, Ulrich Energy, etc.)
- ✅ Conversations: Real conversation history with timestamps
- ✅ Governor: Real state with lanes, capacity, posture metrics
- ✅ Subscriptions: Real provider configs with routing policy

### Likely Fixture/Placeholder Data
- `/api/preferences` returns empty array (valid but no user preferences set)
- `/api/improvement/proposals` returns empty array (valid, no proposals yet)
- `/api/pipeline/plans` returns empty array (valid, no pending plans)
- `/api/workforce/tasks` returns real tasks (1351b4e332f4 is legit)

---

## PAGES LIKELY BROKEN (Due to Missing API Routes)

Pages that attempt to use missing API routes will show loading spinners or errors:

| Page | Expected API | Status | Issue |
|------|--------------|--------|-------|
| `/digest` | `/api/briefing` | ❌ | Route doesn't exist |
| `/improvement` | `/api/improvement/nightly`, `/api/improvement/benchmarks` | ❌ | Routes don't exist |
| `/notifications` | `/api/notifications` | ⚠️ | No root endpoint |
| `/chat` | Unknown dep | ? | Check page source |
| `/learning` | `/api/learning/...` exists | ✅ | Should work |

---

## RECOMMENDATIONS (Priority Order)

1. **IMMEDIATE**: Check which pages actually use the missing routes
   - Search `/projects/dashboard/src` for API calls to `/api/plans`, `/api/tasks`, etc.
   - If they exist, update the page code to use correct prefixes

2. **HIGH**: Implement missing root endpoints if they're needed
   - Consider if `/api/workspace`, `/api/notifications` root routes are necessary
   - If so, implement aggregate endpoints or redirect to list sub-routes

3. **MEDIUM**: Implement missing endpoints if they're referenced by pages
   - `/api/events` - needed by event stream features
   - `/api/metrics` - needed by monitoring pages
   - `/api/briefing` - needed by digest pages

4. **LOW**: Update test specs to match actual API surface
   - If routes are intentionally named differently, update audit checklist
   - Document the actual API contract

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Dashboard pages | 31/31 ✅ |
| Working APIs | 10/24 (42%) |
| Missing APIs | 14/24 (58%) |
| Agent server health | 9/9 agents ✅ |
| Data quality | Real (not fixtures) ✅ |
| Critical blockers | 0 (system is operational) |
| Usability impact | Medium (some pages show empty) |

