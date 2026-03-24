# Athanor Command Center Dashboard Data Layer Exploration — Work Plan

**Status:** Session 5 — Plan mode (no executions yet)  
**Context:** 4 of 15 feature areas completed (Agents, GPU Monitoring, Models). Identified systemic disconnects in response validation.  
**Mandate:** Exhaustive feature-by-feature analysis: what data each feature expects vs. what it actually gets from backend.

---

## Completed Work (Sessions 1-4)

### Feature Areas Analyzed: 4/15
1. **Agents** — routes documented, proxyAgentJson passthrough identified
2. **GPU Monitoring** — routes documented, direct Docker socket interaction identified
3. **Models** — 11 governance routes documented, systemic lack of validation confirmed
4. **Services** — (stub; route structure known but not yet traced)

### Key Disconnects Identified
- **Disconnect #1 — agents/proxy passthrough:** agents/proxy/route.ts passes raw responses with zero schema validation
- **Disconnect #2 — GPU swap direct Docker:** gpu/swap/route.ts implements untyped Docker operations
- **Disconnect #3 — Models governance systematic lack:** All 11 Models routes use proxyAgentJson with zero response validation
- **Pattern identified:** proxyAgentJson used systematically across agents and Models, suggesting architecture of passthrough proxying without type safety

### Files Read
- src/lib/config.ts (30 MonitoredService entries, 6 InferenceBackend instances)
- src/lib/contracts.ts (2600+ lines Zod schemas)
- src/hooks/use-implicit-feedback.tsx, use-lens.tsx
- src/lib/api.ts (25+ data-fetching functions with consistent Zod validation)
- src/app/api/agents/route.ts, agents/proxy/route.ts
- src/app/api/gpu/route.ts, gpu/swap/route.ts
- src/app/api/models/route.ts + 10 governance/proving-ground routes

### Helper Functions & Patterns
- **Data fetching pattern:** async function → Zod validation → fetch (cache: "no-store")
- **Delegation pattern:** routes delegate to @/lib/dashboard-data helpers (getAgentsSnapshot, getGpuSnapshot, getModelsSnapshot, etc.)
- **Passthrough pattern:** proxyAgentJson helper used for agents/proxy and ALL Models governance routes
- **Helper module not yet traced:** @/lib/dashboard-data implementations unknown

---

## Remaining Work: 11 Feature Areas × 4 Data Points

### Remaining Features (11/15)
- [ ] **Tasks/Pipeline** (route structure unknown, likely ~5 routes)
- [ ] **Chat** (route structure unknown)
- [ ] **Media** (route structure unknown)
- [ ] **Learning** (route structure unknown)
- [ ] **Goals/Workforce** (15+ routes known from grep, most unread)
- [ ] **Activity/Operator-stream** (operator-stream route known, most unread)
- [ ] **Notifications** (route structure unknown)
- [ ] **Terminal** (route structure unknown)
- [ ] **Gallery** (route structure unknown)
- [ ] **Work Planner** (route structure unknown)
- [ ] **Personal Data** (route structure unknown)

### For Each Feature Area: Gather 4 Data Points
**a) What data does the feature expect from the backend?**
- Look at contracts.ts schemas (e.g., workforceTaskSchema, learningSectionSchema, mediaSnapshotSchema)
- Check src/hooks or src/lib/api.ts for frontend data requirements

**b) What backend endpoint does it call?**
- Identify route.ts file(s) for the feature
- Trace proxyAgentJson calls to discover /v1/... agent server endpoints
- Or trace direct helper function calls to @/lib/dashboard-data

**c) What happens if that endpoint is down or returns an error?**
- Check route.ts for error handling (try/catch, NextResponse error handling)
- Check whether proxyAgentJson catches errors or passes them through
- Identify error messages returned to frontend

**d) Whether fallback/mock states exist?**
- Search for hardcoded mock data in routes or hooks
- Check frontend components for conditional rendering on error state
- Look for default/empty state configurations in contracts.ts

---

## Systematic Reading Plan

### Phase 1: Map All Routes (Fast)
```
For each remaining feature area:
  1. Use find_file to locate all route.ts files
  2. Use get_symbols_overview to identify exports (GET, POST, PUT, DELETE)
  3. Record endpoint paths and HTTP methods
  4. Note whether routes use proxyAgentJson, delegation to helpers, or direct implementation
```

### Phase 2: Trace Implementations (Focused)
```
For each route type identified in Phase 1:
  1. If proxyAgentJson: note the /v1/... endpoint and search for response schema in contracts.ts
  2. If helper delegation: trace @/lib/dashboard-data to find actual backend call
  3. If direct implementation: read route body to understand data transformation
```

### Phase 3: Document Disconnects (Critical)
```
For each feature area:
  1. Does frontend request match what backend contract defines?
  2. Is response validated against contracts.ts schema?
  3. Are error states handled or passed through raw?
  4. Do fallback states exist?
  5. Flag any: missing endpoints, hardcoded mock data, untyped passthrough, orphaned routes
```

### Phase 4: Synthesize (Report)
```
Aggregate all 11 remaining feature areas into single comprehensive report:
  - Feature area name
  - All routes (method, path, endpoint)
  - Backend contract (schema from contracts.ts)
  - Data flow (feature request → route → backend → validation → response)
  - Disconnects identified
  - Risk assessment (what breaks if backend is down)
```

---

## Critical Modules to Trace (Before/During Phases)

**@/lib/dashboard-data** (not yet traced)
- Contains: getAgentsSnapshot(), getGpuSnapshot(), getModelsSnapshot(), getGpuHistory(), others
- Location: projects/dashboard/src/lib/dashboard-data.ts
- Why: Routes delegate to these helpers; need to understand actual backend calls and error handling

**@/lib/server-agent** (used by proxyAgentJson)
- Contains: proxyAgentJson(path, options, errorMsg, timeout?)
- Location: projects/dashboard/src/lib/server-agent.ts
- Why: Used systematically across agents/proxy and Models routes; need to understand error handling and response passthrough behavior

---

## Estimated Effort

- **Phase 1 (mapping):** 10-15 min (find_file + get_symbols_overview on ~8-10 features)
- **Phase 2 (tracing):** 20-30 min (reading @/lib/dashboard-data, @/lib/server-agent, key route implementations)
- **Phase 3 (disconnect analysis):** 15-20 min (cross-reference against contracts.ts schemas)
- **Phase 4 (reporting):** 10-15 min (synthesize into feature area summary)

**Total estimated:** 55-80 minutes of focused work

---

## Execution Order (When Ready)

1. Trace @/lib/dashboard-data and @/lib/server-agent first (foundational)
2. Then execute Phase 1 (route mapping) on remaining 11 features
3. Then Phase 2-3 in parallel (implementation + disconnect analysis)
4. Then Phase 4 (synthesis + final report)

---

## Questions for Clarity (Optional)

None required for plan; ready to execute when Shaun indicates.
