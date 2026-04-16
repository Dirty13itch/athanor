# Dashboard + Unified Interface

> Historical note: archived research retained for ADR-007 decision history. It is not current implementation, provider, topology, or UI truth.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-007 (Dashboard + Unified Interface)
**Depends on:** ADR-004 (Node Roles), ADR-005 (Inference Engine)

---

## The Question

What technology stack should Athanor's dashboard — the unified web UI described in VISION.md — be built with? And how does it relate to existing open-source chat UIs?

---

## Requirements (from VISION.md)

The dashboard is Athanor's face. A single web UI that shows:
- System health (nodes, GPUs, temps, storage)
- AI status (loaded models, active agents, recent tasks)
- Media (now playing, recent additions, library stats)
- Home automation (lights, climate, presence, automations)
- Chat panel (talk to AI without leaving the dashboard)
- Quick actions (trigger agents, run tasks, search)
- Additional panels as new services come online

**Design language:** Dark, minimal, clean. Cormorant Garamond, subtle warmth, no clutter. A crafted interface, not a generic admin panel.

---

## Two Layers: Chat UI vs Dashboard

There are actually two distinct needs:

### 1. Chat Interface (AI Conversations)

Talking to Athanor's LLMs — conversational chat, agent interactions, tool use. This is a solved problem with excellent open-source options.

**Open WebUI** is the clear leader:
- 58k+ GitHub stars, very active development
- Native vLLM integration (any OpenAI-compatible endpoint)
- Multi-user auth with role-based access control
- Built-in RAG (document upload, citations)
- Conversation history with semantic search
- Prompt templates and sharing
- Voice input/output
- Image generation integration
- Dark/light themes
- Mobile-responsive
- Python function calling and tool use
- Artifact storage

Open WebUI connects to vLLM's OpenAI-compatible API with zero configuration — just point it at `http://node1:8000/v1` and it discovers available models.

**Why not build this from scratch:** Open WebUI has thousands of hours of development behind it. Building a comparable chat interface is months of work for zero differentiation. Use it.

### 2. Dashboard (System Overview + Integration)

The unified command center — system health, GPU status, agent activity, media, home automation, quick actions. This is custom because no existing tool combines all of Athanor's domains.

**This is what we build.**

---

## Dashboard Tech Stack Options

### Option A: Next.js + shadcn/ui + Tailwind

- **Next.js 15+** — React framework with server components, API routes, SSR/SSG
- **shadcn/ui** — component library, dark theme built-in, highly customizable
- **Tailwind CSS v4** — utility-first CSS, dark mode support
- **TypeScript** — type safety across the stack

Pros: Modern, huge ecosystem, easy to find examples and components. shadcn/ui components are beautiful and customizable. Server components reduce client-side JS. API routes can proxy to backend services.

Cons: Node.js runtime on server. React ecosystem moves fast (churn risk).

### Option B: SvelteKit + Skeleton UI

- **SvelteKit** — compiled framework, smaller bundles, simpler mental model
- **Skeleton** — Svelte UI toolkit with dark theme

Pros: Simpler than React, less boilerplate, excellent performance.

Cons: Smaller ecosystem, fewer component libraries, harder to find developers/examples.

### Option C: Python (FastAPI + HTMX + Jinja2)

- Backend-rendered with HTMX for interactivity
- Stays in Python ecosystem (matches vLLM, agent framework)

Pros: Simple, no JS build step, Python everywhere.

Cons: Limited interactivity for real-time dashboards. WebSocket support is manual. Less polished UI components.

### Option D: Existing Dashboard Platform (Grafana, Homepage, Dashy)

- **Grafana** — metrics dashboards, plugin ecosystem
- **Homepage/Dashy** — homelab bookmark dashboards

Pros: No custom code. Grafana handles metrics beautifully.

Cons: None of these do what VISION.md describes. Grafana is for metrics, not a unified command center. Homepage/Dashy are bookmark pages. The chat + agents + media + home automation integration requires custom work.

---

## Recommendation

**Use both — don't build what's already solved.**

1. **Open WebUI** for the chat interface. Deploy as a Docker container on Node 2, pointed at vLLM instances on Node 1 and Node 2.

2. **Custom dashboard** built with **Next.js + shadcn/ui + Tailwind CSS** for the unified command center. This is Athanor's primary UI — the thing Shaun opens every day. It embeds or links to Open WebUI for chat, Grafana for detailed metrics, ComfyUI for creative work, and any other service UIs.

3. **Grafana** for detailed metrics visualization (ADR-009). The dashboard shows summary metrics and links to Grafana for deep dives.

**Why Next.js:** Largest ecosystem, most component libraries, best documentation. shadcn/ui's design language (minimal, dark, customizable) aligns with VISION.md's aesthetic. TypeScript provides safety in a custom codebase. Server components enable real-time data fetching without a separate API layer.

**Why not build the chat UI:** Open WebUI has multi-user auth, RAG, voice, conversation history, semantic search, and model management. Building this from scratch would take months and produce an inferior result. The dashboard can embed Open WebUI in an iframe or link to it.

---

## Architecture

```
Browser (DEV or mobile)
  │
  ├── Athanor Dashboard (Node 2:3000)
  │     ├── System Health panel  → Prometheus API
  │     ├── GPU Status panel     → DCGM metrics via Prometheus
  │     ├── Agent Activity panel → Agent API (Node 1)
  │     ├── Media panel          → Plex/Tautulli API (VAULT)
  │     ├── Home panel           → Home Assistant API (VAULT)
  │     ├── Chat panel           → iframe/link to Open WebUI
  │     ├── Creative panel       → link to ComfyUI
  │     └── Quick Actions        → Agent API triggers
  │
  ├── Open WebUI (Node 2:8080)   → vLLM (Node 1:8000, Node 2:8001)
  ├── ComfyUI (Node 2:8188)      → RTX 5090
  └── Grafana (VAULT:3000)       → Prometheus (VAULT:9090)
```

The dashboard is a thin orchestration layer — it doesn't duplicate functionality, it unifies access. Each panel talks to an existing service's API.

---

## Design System

From VISION.md: "Dark, minimal, clean. Cormorant Garamond, subtle warmth, no clutter."

- **Primary font:** Cormorant Garamond (headings, dashboard title)
- **Body font:** Inter or similar sans-serif (data, labels, content)
- **Color palette:** Dark background (#0a0a0a to #1a1a1a), warm accents (amber/gold #d4a574), subtle borders
- **Component style:** shadcn/ui defaults are close — minimal, clean, dark-first
- **No clutter:** Every panel earns its space. No decorative elements.

This is a research/placeholder — the actual design system gets refined when dashboard development begins.

---

## Sources

- [Open WebUI GitHub (58k+ stars)](https://github.com/open-webui/open-webui)
- [Open WebUI vLLM integration](https://docs.vllm.ai/en/latest/deployment/frameworks/open-webui/)
- [Open WebUI overview and quickstart](https://www.glukhov.org/post/2026/01/open-webui-overview-quickstart-and-alternatives/)
- [Open WebUI review (Sider)](https://sider.ai/blog/ai-tools/open-webui-review-the-most-capable-self-hosted-ai-chat-interface-in-2025)
- [Next.js + shadcn/ui dashboard template](https://vercel.com/templates/next.js/next-js-and-shadcn-ui-admin-dashboard)
- [Dashy self-hosted dashboard](https://dashy.to/)
