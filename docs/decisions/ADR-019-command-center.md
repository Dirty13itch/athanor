# ADR-019: Command Center Architecture

**Status:** Accepted
**Date:** 2026-02-25
**Deciders:** Shaun + Claude
**Depends on:** ADR-007 (Dashboard), ADR-017 (Meta-Orchestrator), ADR-018 (GPU Orchestration)

---

## Context

The Athanor Command Center is now fronted canonically at `https://athanor.local/`, with the DEV runtime fallback still available at `http://dev.athanor.local:3001/` while hostname rollout finishes across operator clients. It is a 16-page Next.js app with 26 service health checks. It works as a monitoring surface — you can see what's happening but can't meaningfully steer the system. Shaun has clarified that the web interface (not the terminal) is the primary way he wants to interact with Athanor, including from his phone.

Five research documents (totaling ~4,500 lines) were produced covering web-based development environments, command center UI patterns, human-in-the-loop design, mobile PWA architecture, and novel interface patterns. Those inputs now live under `docs/archive/research/` as historical design evidence. They inform the decisions below.

Full design: `docs/design/command-center.md`

---

## Decisions

### 1. PWA, Not Native App

**Decision:** The dashboard becomes a Progressive Web App with manual service worker, VAPID push notifications, and install-to-home-screen. No Capacitor, Tauri, or React Native wrapper.

**Rationale:**
- PWA covers all requirements: push notifications (Android + iOS 16.4+), offline awareness, standalone display, biometric auth (WebAuthn when HTTPS available)
- Zero additional build toolchain (no Xcode, no Android Studio, no signing certificates)
- The dashboard is already a web app — PWA is additive, not rewrite
- Capacitor is reserved as escape hatch if iOS push proves unreliable

**Rejected:**
- Capacitor: unnecessary complexity for a single-user homelab
- React Native: would require full rewrite of existing dashboard
- Tauri Mobile: immature mobile support in 2026

### 2. SSE for Real-Time, WebSocket for Chat Only

**Decision:** Replace dashboard polling with Server-Sent Events (SSE) for all unidirectional real-time data. Keep WebSocket only for the chat interface (which needs bidirectional streaming).

**Rationale:**
- SSE auto-reconnects on network drop (native EventSource behavior), critical for mobile
- SSE works through HTTP proxies without special configuration
- One SSE connection per client vs one WebSocket per channel
- The GWT workspace already broadcasts via Redis pub/sub — SSE endpoint subscribes to this
- Chat needs bidirectional streaming for Vercel AI SDK — WebSocket is correct there

**Rejected:**
- WebSocket for everything: unnecessary complexity, reconnection must be hand-rolled, not needed for unidirectional data
- Polling: current approach, wasteful and introduces latency

### 3. Vercel AI SDK for Generative UI

**Decision:** Use the Vercel AI SDK (`ai` npm package) for chat responses that render React components inline (generative UI).

**Rationale:**
- Works with any OpenAI-compatible endpoint (LiteLLM at VAULT:4000)
- Streaming React Server Components out of the box
- Already designed for Next.js App Router
- Enables rich agent responses: inline charts, approval cards, media galleries
- Active ecosystem, well-documented, 50k+ GitHub stars

**Rejected:**
- AG-UI Protocol (CopilotKit): less mature, more opinionated, smaller ecosystem
- Google A2UI: too new, Google-specific
- Custom streaming: unnecessary when AI SDK exists

### 4. Intent-Based Navigation (Lenses), Not More Pages

**Decision:** Instead of adding more pages to the dashboard, implement an adaptive "lens" system where the same URL reshapes its layout based on declared intent.

**Rationale:**
- 16 pages is already a lot. Adding more pages for each new domain makes navigation worse.
- Lenses solve the "where do I go?" problem: declare intent ("focus on media"), interface adapts.
- Command palette (Cmd+K) becomes primary navigation, not sidebar.
- URL query params make lenses bookmarkable and shareable.
- Progressive: start with 4-5 lenses, add more as domains are added.

**Rejected:**
- More pages: doesn't scale, requires explicit navigation
- Tabs within pages: partial solution, doesn't reshape the whole interface
- Single infinite scroll: loses information hierarchy

### 5. Goals API, Not Static Scheduler Prompts

**Decision:** Replace the static per-agent scheduler prompts with a goal-based system where agents derive their own task generation from natural language goals + constraints.

**Rationale:**
- Current scheduler sends the same prompt every N minutes regardless of what's happening
- Goals give agents judgment: "keep the home comfortable" adapts to weather, time, occupancy
- Commander's intent model: specify what, not how
- Goals are editable via dashboard without code changes
- Enables conversational steering: "focus on media quality this week" adjusts multiple agents

**Rejected:**
- Keep static schedulers: too rigid, doesn't learn or adapt
- Full OKR system: too formal for a one-person system
- Event-driven only (no proactive goals): loses the "autonomous workforce" vision

### 6. Deploy Claudeman for Multi-Session Claude Code Web Access

**Decision:** Deploy Claudeman on DEV (WSL2) as the self-hosted Claude Code web interface. Use Claude Code Remote Control as the zero-effort alternative for quick mobile checks.

**Rationale:**
- Claudeman: multi-session (20), zero-lag mobile input, overnight autonomous operation, live agent visualization
- Self-hosted — no dependency on Anthropic infrastructure for the UI layer
- Remote Control for quick checks — zero deploy, instant, but single-session and Anthropic-dependent
- They coexist: Remote Control for phone checks, Claudeman for serious work sessions

**Rejected:**
- code-server: missing AI extensions, wrong tool for an orchestrator
- Custom xterm.js-only terminal: reinvents what Claudeman already does better
- Jupyter: wrong paradigm for conversational AI development

---

## Consequences

### Positive
- Single interface for all Athanor interaction (desktop + mobile)
- Agents become steerable through goals and feedback, not just observable
- Push notifications bring the system to Shaun, not the other way around
- Real-time updates replace polling (lower latency, lower resource usage)
- Rich chat responses via generative UI make the chat interface genuinely useful

### Negative
- Significant dashboard development effort (~10-15 weekends across 5 phases)
- New dependencies (Vercel AI SDK, motion, web-push, react-xtermjs)
- SSE endpoint needs Redis connection from Node 2 to VAULT
- Push notifications add operational complexity (VAPID keys, subscription management)
- Lens system adds UI complexity vs simple page navigation

### Risks
- Vercel AI SDK + local models (Qwen3-32B): may produce poor generative UI tool calls. Mitigation: test early, fall back to text responses.
- PWA push on iOS: historically flaky. Mitigation: Capacitor as escape hatch.
- Claudeman stability: relatively new project. Mitigation: test thoroughly before overnight autonomous use.
- Scope creep: 5-phase plan could expand indefinitely. Mitigation: each phase delivers usable value independently.

---

## References

- `docs/design/command-center.md` — full design document
- `docs/research/2026-02-25-web-development-environments.md`
- `docs/archive/research/2026-02-25-command-center-ui-design.md`
- `docs/research/2026-02-25-human-in-the-loop-patterns.md`
- `docs/research/2026-02-25-mobile-pwa-architecture.md`
- `docs/research/2026-02-25-novel-interface-patterns.md`
