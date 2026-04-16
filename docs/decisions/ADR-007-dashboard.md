# ADR-007: Dashboard + Unified Interface

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-dashboard.md](../archive/research/2026-02-15-dashboard.md)
**Depends on:** ADR-004 (Node Roles), ADR-005 (Inference Engine)

---

## Context

VISION.md describes Athanor's dashboard as a "unified command center" — a single web UI showing system health, AI status, media, home automation, chat, and quick actions. This needs both a conversational AI interface (chat with LLMs) and a custom system dashboard (the command center itself). These are different problems with different solutions.

---

## Decision

### Two components: Open WebUI for chat, custom Next.js dashboard for the command center.

#### Open WebUI — Chat Interface

Deploy Open WebUI as a Docker container on Node 2, connecting to all vLLM instances:

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_BASE_URLS=http://node1:8000/v1;http://localhost:8001/v1
      - OPENAI_API_KEYS=none;none
    volumes:
      - /data/open-webui:/app/backend/data
```

Open WebUI provides:
- Chat with any model on any vLLM instance
- Conversation history with semantic search
- Document upload and RAG with inline citations
- Multi-user auth (admin/user roles)
- Voice input/output
- Prompt templates and sharing
- Dark theme, mobile-responsive

**Why not build this:** Open WebUI (58k+ GitHub stars) has years of development. Replicating its feature set would take months and produce an inferior result. Use it.

#### Custom Dashboard — Athanor Command Center

Build a custom web application for the unified system view:

**Tech stack:**
- **Next.js 15+** with React Server Components
- **shadcn/ui** component library (dark theme, customizable)
- **Tailwind CSS v4** (utility-first, dark mode)
- **TypeScript** throughout

**Runs on:** Node 2, port 3000. Docker container, no GPU needed.

**Panels:**

| Panel | Data Source | Update Method |
|-------|------------|---------------|
| System Health | Prometheus API | Polling (10s) |
| GPU Status | DCGM metrics via Prometheus | Polling (10s) |
| Agent Activity | Agent API on Node 1 | WebSocket |
| Media | Plex/Tautulli API on VAULT | Polling (30s) |
| Home Automation | Home Assistant API on VAULT | WebSocket |
| Chat | Embedded Open WebUI (iframe/link) | Real-time |
| Creative | Link to ComfyUI | On-demand |
| Quick Actions | Agent API triggers | On-click |

The dashboard is a thin orchestration layer. It doesn't duplicate any service's functionality — it provides a unified view with links to the full UI of each service.

---

## Design Language

From VISION.md: "Dark, minimal, clean. Cormorant Garamond, subtle warmth, no clutter."

| Element | Choice |
|---------|--------|
| Heading font | Cormorant Garamond |
| Body font | Inter |
| Background | #0a0a0a to #1a1a1a |
| Accent | Warm amber/gold (#d4a574) |
| Borders | Subtle, low contrast |
| Components | shadcn/ui (dark variant) |
| Philosophy | Every element earns its space |

The design system is refined during implementation, but the direction is clear: this is a crafted instrument, not a generic admin panel.

---

## What This Enables

- **One browser tab** to see everything Athanor is doing
- **Chat without context-switching** — Open WebUI is a click (or iframe) away
- **Real-time GPU monitoring** — see what models are loaded, VRAM usage, inference throughput
- **Agent visibility** — see what agents are doing, trigger them manually
- **Media awareness** — what's streaming, what's been added, library health
- **Home status** — lights, climate, presence at a glance
- **Mobile access** — responsive design works on phones (future, not immediate priority)

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Build chat UI from scratch | Open WebUI has 58k stars and years of development. Rebuilding it is months of work for an inferior result. |
| Grafana as the dashboard | Grafana is metrics-focused. It can't integrate chat, agents, media, home automation, and quick actions. Use Grafana for detailed metrics, not as the primary UI. |
| Homepage / Dashy | Bookmark dashboards. No dynamic data, no chat, no agent integration. Fine as a link page, not as Athanor's face. |
| SvelteKit | Smaller ecosystem, fewer component libraries. Next.js has more examples, more templates, and shadcn/ui. |
| Python backend (FastAPI + HTMX) | Limited interactivity for real-time dashboard. WebSocket support is manual. Less polished UI components. |
| Single monolithic app | Combining chat UI and dashboard into one app duplicates Open WebUI's work. Better to compose than to build monolithic. |

---

## Risks

- **Custom dashboard is a significant build.** This is the first piece of Athanor that requires substantial original code. Mitigated by: using shadcn/ui for components (don't build from scratch), starting with 2-3 panels and iterating, keeping it thin (API proxying, not business logic).
- **Open WebUI updates may break.** Pinning Docker image tags mitigates this. Test upgrades before deploying.
- **Design system scope creep.** The dashboard "is never finished" (VISION.md). That's fine — but keep early versions minimal. Ship the MVP, then refine.

---

## Implementation Order

1. **Deploy Open WebUI** — immediate value, connects to existing vLLM instances
2. **Scaffold Next.js dashboard** — bare project with shadcn/ui, dark theme, Cormorant Garamond
3. **System health panel** — Prometheus metrics (CPU, RAM, disk, network)
4. **GPU status panel** — DCGM metrics (utilization, VRAM, temperature, loaded models)
5. **Chat integration** — embed or link to Open WebUI
6. **Agent panel** — after ADR-008 (Agent Framework) is implemented
7. **Media panel** — Plex/Tautulli integration
8. **Home panel** — Home Assistant integration
9. **Iterate forever** — the dashboard grows with the system

---

## Sources

- [Open WebUI GitHub](https://github.com/open-webui/open-webui)
- [Open WebUI + vLLM integration](https://docs.vllm.ai/en/latest/deployment/frameworks/open-webui/)
- [Next.js + shadcn/ui template](https://vercel.com/templates/next.js/next-js-and-shadcn-ui-admin-dashboard)
- [shadcn/ui component library](https://ui.shadcn.com/)
