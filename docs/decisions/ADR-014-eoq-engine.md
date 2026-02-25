# ADR-014: EoBQ Game Engine

**Date:** 2026-02-24
**Status:** Accepted
**Depends on:** ADR-005 (Inference Engine), ADR-006 (Creative Pipeline), ADR-012 (LiteLLM Routing)
**Research:** `docs/research/2026-02-24-eoq-game-engine.md`

---

## Context

Empire of Broken Queens needs a runtime engine. Unlike traditional visual novels where dialogue is pre-authored and branching is the hard problem, EoBQ generates all dialogue at runtime via LLM (vLLM) and all images at runtime via ComfyUI. The engine must treat HTTP API calls as first-class operations, support streaming LLM responses for typewriter display, manage complex narrative state (personality vectors, relationship scores, emotional states, memory logs), and be web-deployable with no content restrictions.

---

## Decision

**Build EoBQ as a custom Next.js web application.**

- **Runtime:** Next.js 16 (React 19), deployed on Node 2 alongside the existing dashboard
- **Styling:** Tailwind CSS + Framer Motion for transitions and animations
- **State management:** Zustand (client-side), SQLite (narrative persistence)
- **LLM integration:** Next.js API routes → LiteLLM (VAULT:4000) with Server-Sent Events for streaming
- **Image generation:** Next.js API routes → ComfyUI (Node 2:8188) with WebSocket for progress
- **Memory retrieval:** Qdrant (Node 1:6333) via API routes
- **VN presentation:** Custom React components (~500-1000 lines for dialogue box, portraits, backgrounds, choices, transitions)

---

## Alternatives Considered

### Ren'Py (rejected)
The de facto adult VN engine with the largest community (F95zone, itch.io). Has `renpy.fetch()` for HTTP, but **cannot stream LLM responses** — the screen freezes for 5-30 seconds during generation. Web builds have CORS restrictions and no WebSocket support. Designed for pre-authored branching content, not runtime generation.

**Would reconsider if:** Web deployment is dropped and desktop-only distribution is acceptable.

### Godot 4 (rejected)
Full game engine with async HTTP support. Massive overkill for a visual novel — no built-in VN features, steep learning curve, GDScript is the least AI-generatable language evaluated. Web export has CORS and threading limitations.

**Would reconsider if:** EoBQ evolves to include spatial exploration, combat, or physics.

### Ink/Inkle (rejected)
Elegant narrative scripting language for branching stories. Has no HTTP, no UI, no rendering. Would require a full web app wrapper anyway, making the Ink layer dead weight when content is AI-generated.

### TyranoScript (rejected)
Web-native VN engine, popular in Japan. Tag-based scripting fights against dynamic content. Primarily Japanese documentation, minimal AI-generatable code.

### Pixi'VN (deferred, not rejected)
React-compatible VN engine on PixiJS. Provides VN primitives (dialogue, choices, save/load) but is a young project with a small community. Start without it; adopt later if canvas rendering needs exceed what CSS/Framer Motion provide.

---

## Consequences

**Positive:**
- Streaming LLM responses work natively (ReadableStream/SSE)
- API route proxy eliminates CORS — browser never talks to backend services directly
- React/TypeScript is the most AI-generatable stack for Shaun's orchestrator workflow
- Shares infrastructure with the existing Next.js dashboard (same toolchain, deployment, Ansible roles)
- Zero content restrictions — self-hosted, no platform TOS
- Zustand + SQLite handle the complex narrative state without fighting engine limitations

**Negative:**
- VN presentation layer must be built from scratch (~500-1000 lines)
- No pre-built adult VN community/ecosystem (Ren'Py owns this)
- No established distribution channel (F95zone/itch.io favor Ren'Py)

**Risks:**
- If visual effects need canvas-level rendering (particle effects, shader transitions), will need to adopt PixiJS or Pixi'VN as a layer
- If distribution becomes a goal, may need a Ren'Py or Electron port for F95zone/itch.io compatibility

---

## Implementation Notes

- Port: TBD (dashboard is 3001, avoid conflicts)
- Project location: `projects/eoq/` (monorepo)
- First milestone: VN component library + mock mode (UI iteration without GPU cost)
- Mock mode per ARCHITECTURE.md is the first feature — iterate on presentation without burning GPU cycles
