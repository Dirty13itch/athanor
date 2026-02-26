---
paths:
  - "projects/dashboard/**"
---

# Command Center (Dashboard) Conventions

- Next.js 16 + React 19 + Tailwind + shadcn/ui + oklch colors
- Deploy: rsync `src/` to Node 2, `docker compose up -d --build`
- SSE at `/api/stream` (5s interval) — all real-time data goes through this
- Agent proxy at `/api/agents/proxy` — GET + POST, forwards to Node 1:9000
- 5 lenses: default/system/media/creative/eoq — URL param `?lens=X`
- Design language: dark, minimal, oklch, `--furnace-glow` ambient warmth
- Mobile and desktop equally important — both must be polished
- No Vercel AI SDK — our SSE has custom events the SDK doesn't handle
- LensProvider wraps layout inside Suspense
- Bottom nav on mobile, sidebar on desktop
