# Dashboard API Route Audit — Progress State

## Task
Exhaustive documentation of ALL API routes under C:\Athanor\projects\dashboard\src\app\api/

**Deliverable:** For each route: Path, HTTP methods, backend service proxy destination, request/response shape.

## Progress Summary

### Completed (10 routes documented)
- /api/gpu (GET) → getGpuSnapshot()
- /api/models (GET) → getModelsSnapshot()
- /api/memory (GET) → getMemorySnapshot()
- /api/stream (GET) → SSE aggregator (Prometheus + agent endpoints)
- /api/activity (GET) → /v1/activity
- /api/activity/operator-stream (GET) → /v1/activity/operator-stream
- /api/agents/proxy (GET, POST) → Universal proxy to agentServer
- /api/alerts (GET) → /v1/alerts
- /api/autonomy (GET) → /v1/autonomy
- /api/chat (POST) → /v1/chat/completions (with streaming, event normalization)

### Identified but Not Yet Read
**comfyui domain (5 routes):**
- /api/comfyui/generate/route.ts
- /api/comfyui/history/route.ts
- /api/comfyui/queue/route.ts
- /api/comfyui/stats/route.ts
- /api/comfyui/image/[...path]/route.ts

**Remaining domains (~25 areas, ~135 routes):**
consolidation, containers, context, conversations, eoq, feedback, gallery, governor, history, home, improvement, insights, intelligence, learning, media, monitoring, notification-budget, outputs, overview, personal-data, pipeline, preferences, projects, push, research, review, routing, scheduling, services, skills, stash, subscriptions, system-map, tts, workforce

## Next Actions (In Order)
1. Read 5 comfyui route files
2. Document comfyui domain summary
3. Proceed through remaining domains alphabetically
4. Compile comprehensive route inventory

## Key Patterns Observed
- Simple proxies: /api/{service} → /v1/{service}
- Complex streams: /api/stream, /api/chat with event normalization
- Universal proxy: /api/agents/proxy (generic forwarding)
- Helper pattern: buildChatUpstreamHeaders(), proxyAgentJson(), joinUrl()

## Estimated Scope
~150 total routes across ~25 domain areas
~30 routes per session typical (conservative estimate)
