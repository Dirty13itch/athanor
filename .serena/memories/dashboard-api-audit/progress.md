# Dashboard API Audit Progress

## Completed (15 routes)
✅ gpu, models, memory, alerts, autonomy (core monitoring)
✅ stream, activity, activity/operator-stream (streaming)
✅ agents/proxy, chat (proxying)
✅ comfyui/generate, comfyui/history, comfyui/queue, comfyui/stats, comfyui/image/[...path] (comfyui)

## In Progress
- consolidation (2): consolidation/route.ts, consolidation/stats/route.ts
- containers (3): containers/route.ts, containers/[name]/logs/route.ts, containers/[name]/restart/route.ts
- context (1): context/preview/route.ts
- conversations (1): conversations/route.ts
- eoq (4): eoq/conversations/route.ts, eoq/generations/route.ts, eoq/memories/route.ts, eoq/queens/route.ts
- feedback (2): feedback/route.ts, feedback/implicit/route.ts
- gallery (2): gallery/overview/route.ts, gallery/files/route.ts
- governor (9): governor/*, governor/pause, governor/resume, governor/presence, governor/release-tier, governor/operations, governor/operator-tests, governor/heartbeat, governor/tool-permissions
- history (1): history/route.ts
- home (1+): home/overview/route.ts

## Remaining Domains (count unknown)
improvement, insights, intelligence, learning, media, monitoring, notification-budget, outputs, overview, personal-data, pipeline, preferences, projects, push, research, review, routing, scheduling, services, skills, stash, subscriptions, system-map, tts, workforce

## Strategy
Read each domain alphabetically. Capture: path, HTTP methods, backend proxy target (if applicable), request/response shape.
