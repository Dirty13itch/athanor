# Agent Routing Page Design

**Date:** 2026-02-23
**Status:** Approved, prototype built

## Problem

Agents are only accessible via direct API calls to `192.168.1.244:9000`. The dashboard has no way to discover, select, or interact with agents. Tool execution is invisible — when an agent calls `check_services` or `search_tv_shows`, the user sees nothing until the final response arrives.

## Decision

**Approach A — New `/agents` route.** Keep `/chat` for raw vLLM model access. The agents page is a separate experience with its own agent hub and tool-aware chat.

## Architecture

### Frontend (`/agents` route)

**Agent Hub** — horizontal card grid at the top of the page.
Each card shows: icon, name, description (2-line clamp), tool count badge, and a live status dot (green = ready, gray = unavailable). Clicking a ready agent selects it and opens the chat area below. Selected card gets an amber ring + accent background.

**Chat Area** — appears below the hub when an agent is selected.
- Header: "Conversation" + tool count
- Messages: user bubbles (right, primary color), assistant bubbles (left, muted background)
- Tool call cards: inline between assistant text. Collapsible. Shows tool name (monospace), arguments, status badge (ok/err/spinner), duration. Click to expand and see full output in a scrollable `<pre>` block.
- Suggestion chips: contextual per-agent, shown in empty state. "How are the GPUs doing?", "Search for Severance", "What lights are on?" etc.
- Input: text field + Send button at bottom, disabled during streaming.
- Streaming: standard SSE with blinking cursor. Tool events interleaved.

**Empty state** — wrench icon + "Select an agent above to begin"

### Backend changes needed

**1. `GET /v1/agents` endpoint** (new) — returns agent metadata with tool introspection. Currently hardcoded in the frontend API route (`/api/agents/route.ts`). Should move to the agent server so tools are discovered dynamically via LangGraph's agent graph.

**2. SSE tool event streaming** — extend `_stream_response` in `server.py` to emit:
```
data: {"type":"tool_start","name":"check_services","args":{}}
data: {"type":"tool_end","name":"check_services","output":"...","duration_ms":142}
```
These are interleaved with standard OpenAI `chat.completion.chunk` events. The frontend already handles both event types.

### Data flow

```
User types message
  -> POST /api/chat (Next.js proxy)
    -> POST /v1/chat/completions (agent server, stream=true)
      -> LangGraph agent invokes tools
        <- SSE: tool_start events
        <- SSE: tool_end events
        <- SSE: chat.completion.chunk (assistant text)
      <- SSE: [DONE]
  <- Tool call cards appear inline as events arrive
  <- Assistant text streams in real-time
```

### API route (`/api/agents`)

Fetches agent health from `GET /health` on the agent server. Cross-references with hardcoded metadata (name, description, tools, icon). Returns merged array with live status. Falls back to "unavailable" for all agents if server unreachable.

Long-term: replace hardcoded metadata with `GET /v1/agents` from the backend.

### Sidebar

Added "Agents" nav item between "GPU Metrics" and "Chat" with a robot icon. Active state uses the same amber highlight as other nav items.

## Config

```typescript
agentServer: { url: "http://192.168.1.244:9000" }
```

Agents removed from `inferenceBackends` array so they no longer appear in the `/chat` model dropdown. Clean separation: `/chat` = raw vLLM models, `/agents` = LangGraph agents with tool calling.

## Files

| File | Status | Purpose |
|------|--------|---------|
| `src/app/agents/page.tsx` | Created | Agent hub + chat UI with tool call cards |
| `src/app/api/agents/route.ts` | Created | Agent metadata API with live status |
| `src/components/sidebar-nav.tsx` | Modified | Added Agents nav item |
| `src/lib/config.ts` | Modified | Added agentServer config, removed agents from inferenceBackends |

## Implementation plan

### Phase 1: Backend tool event streaming (agent server)
1. Add tool event emission to `_stream_response` in `server.py` — listen for `on_tool_start` and `on_tool_end` events from LangGraph's `astream_events`
2. Add `GET /v1/agents` endpoint that returns agent metadata with dynamically discovered tools from each agent's graph
3. Update `/api/agents/route.ts` to fetch from `/v1/agents` instead of using hardcoded metadata

### Phase 2: Frontend refinements
4. Wire real tool events into the chat — currently the parsing logic exists but no events are emitted by the backend
5. Add tool output formatting — detect JSON and render with syntax highlighting
6. Add agent-specific system prompts display (collapsible, for transparency)
7. Mobile responsiveness pass — ensure cards stack properly on small screens

### Phase 3: Hardening
8. Add error recovery — retry on SSE disconnect, show reconnecting state
9. Add conversation persistence (localStorage or backend threads)
10. Rate limiting / throttling on the chat proxy
