# ADR-020: Layered Interaction Architecture

**Date:** 2026-02-26
**Status:** Accepted
**Deciders:** Shaun, Claude
**Research:** `docs/research/2026-02-26-persistent-development-environment.md`

---

## Context

Athanor's Command Center now has a live canonical front door at `https://athanor.local/`, with the DEV runtime fallback still available at `http://dev.athanor.local:3001/` while hostname rollout finishes across operator clients. It has 17 pages, 5 lens modes, SSE streaming, push notifications, and generative UI. But it lacks a coherent interaction model — there's no clear mapping from "what does Shaun want to do right now?" to "which interface surface handles it." The system needs a layered architecture that:

1. Serves mobile and desktop equally (not responsive-as-afterthought — designed for both)
2. Ranges from passive glancing to active system development
3. Integrates development capabilities without embedding complexity
4. Makes feedback fast and natural (< 2 seconds on mobile)
5. Keeps the system one-person-maintainable

## Decision

**Six interaction layers with progressive depth, served by Command Center (Layers 0-4) as the hub and linked external apps (Layer 5) as spokes.**

```
Layer 0: AMBIENT     "Everything okay?"        Glance, 2 seconds      Mobile: Excellent
Layer 1: MONITOR     "What happened?"           Scan, 30 seconds       Mobile: Excellent
Layer 2: FEEDBACK    "That was good/bad"        React, 5 seconds       Mobile: Excellent
Layer 3: DIRECT      "Do this next"             Instruct, 1-2 min      Mobile: Good
Layer 4: CREATE      "Build this workflow"       Design, 10-30 min      Mobile: Partial
Layer 5: DEVELOP     "Change the system"         Engineer, 1+ hours     Mobile: Review-only
```

### Integration Pattern: Linked Apps with Deep Links

Do NOT iframe-embed development tools. Research shows:
- Iframes break mobile UX (touch scrolling, keyboard, 45s load on iOS web views)
- Micro-frontends solve a team coordination problem a one-person system doesn't have
- Linked apps respect each tool's strengths without the embedding complexity

Command Center is the hub for Layers 0-4. Layer 5 links to Claudeman (DEV:3000) and includes a native xterm.js terminal page as an escape hatch.

### Feedback Mechanisms (Layer 2)

- Inline thumbs up/down on every agent output card
- Swipe right to approve, swipe left to reject on task cards
- Push notification action buttons (Android) / deep-link to approval page (iOS)
- Voice input via Web Speech API on chat page
- Priority adjustment on goals

### Mobile-First Design Principle

Every feature is tested on mobile first, desktop second. Layers 0-3 must be fully mobile-native. Voice input is the highest-impact mobile improvement (zero-dependency browser API).

## Rationale

1. **Layers, not modes.** Users don't "switch modes" — they drill deeper naturally. Tap agent portrait → agent detail → task → feedback → diff review. Back button goes shallower.
2. **Lenses are lateral, not vertical.** The existing lens system (system/media/creative/eoq) changes the domain, not the depth. Lenses and layers are orthogonal.
3. **Chat is Layer 3, not the primary interface.** The primary interface is Layer 0-1 (ambient + monitor). Chat is for when you want to give direction.
4. **Terminal is an escape hatch.** Design it as fallback, not the promoted path. The system should be operable without ever touching a terminal.
5. **Self-modification is safe with GitOps.** Git audit trail, Ansible convergence, Docker isolation, separate nodes, Shaun as safety valve.

## Implementation — Build Order

Sorted by impact per effort:

| Priority | Item | Effort | Layer | Status | Files |
|----------|------|--------|-------|--------|-------|
| 1 | Voice input in chat | 1 day | 3 | DONE | `src/components/voice-input.tsx`, `src/app/chat/page.tsx` |
| 2 | Inline feedback on agent outputs | 1 day | 2 | DONE | `src/components/gen-ui/feedback-buttons.tsx`, Stream/Activity/Tasks pages |
| 3 | Swipe actions on task cards | 2 days | 2 | DONE | `src/components/swipe-card.tsx`, `src/app/tasks/page.tsx` |
| 4 | Diff review page | 3 days | 5 | — | `src/app/review/page.tsx`, `react-diff-viewer-continued` |
| 5 | Terminal page | 2 days | 5 | DONE (frontend) | `src/app/terminal/page.tsx`, xterm.js. Needs ws-pty bridge. |
| 6 | Deep links from notifications | 1 day | 2 | DONE | `public/sw.js` — approve/reject/feedback actions via agent proxy |
| 7 | Voice output for status | 2 days | 0-1 | — | TTS in chat responses |
| 8 | Workflow/prompt templates | 5 days | 4 | — | `src/app/workflows/page.tsx` |

### What NOT to Build

- Full IDE in dashboard (Shaun doesn't write code)
- code-server (missing AI extensions)
- Micro-frontend architecture (no team boundary problem)
- Native mobile app (PWA covers all needs)
- Auto-deploy pipeline (manual deploy works at current scale)
- Separate staging environment (git revert is the rollback mechanism)

## Consequences

### Positive
- Clear mental model for every interaction: "How deep do I need to go right now?"
- Mobile and desktop both first-class, with appropriate capabilities at each layer
- Feedback becomes frictionless — thumbs up/down takes < 2 seconds
- Development stays integrated but isolated — breaks in Layer 5 don't affect Layers 0-4
- Progressive disclosure prevents information overload

### Negative
- 8 items to build (17 days total estimated effort)
- Voice input depends on browser API (needs internet for speech recognition)
- Swipe gestures can conflict with OS gestures (mitigated with thresholds)
- Layer discipline requires ongoing vigilance against feature creep

### Risks
- iOS push notification limitations (no action buttons) — mitigated with deep links
- xterm.js SSR issues in Next.js — mitigated with dynamic import `ssr: false`
- Web Speech API privacy (sends audio to Google/Apple) — migrate to local Whisper later if needed

---

## Architecture Diagram

```
Phone / Desktop Browser
  |
+-- Command Center PWA (`https://athanor.local/`, runtime `dev.athanor.local:3001`)
  |     |
  |     +-- LAYER 0-1: Ambient + Monitor
  |     |     Home, Stream, GPUs, Services, Agents, Monitoring
  |     |     System Pulse strip + CrewBar (persistent all pages)
  |     |
  |     +-- LAYER 2: Feedback
  |     |     Inline thumbs up/down, swipe actions, notification actions
  |     |
  |     +-- LAYER 3: Direct
  |     |     Chat (text + voice), Task dispatch, Goals, Command palette
  |     |
  |     +-- LAYER 4: Create (desktop-primary)
  |     |     Preferences, future workflow editor
  |     |
  |     +-- LAYER 5: Develop (desktop-only, linked)
  |           /terminal (xterm.js), /review (diff viewer)
  |           Link to Claudeman (DEV:3000)
  |
  +-- Claudeman (DEV:3000) -- LAYER 5
  +-- Agent Server (Node 1:9000) -- BACKEND
  +-- Claude Code CLI (DEV) -- LAYER 5
```
