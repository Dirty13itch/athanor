# Agent Routing Page — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add tool event streaming to the agent server and a `/v1/agents` introspection endpoint, then wire the existing dashboard prototype to use real live data instead of hardcoded metadata.

**Architecture:** The agent server (`projects/agents/src/athanor_agents/server.py`) gets two new capabilities: (1) SSE `tool_start`/`tool_end` events interleaved with standard OpenAI streaming chunks, and (2) a `GET /v1/agents` endpoint that returns agent metadata with dynamically discovered tools. The dashboard frontend (`projects/dashboard/src/app/agents/page.tsx`) already has parsing logic for both event types — it just needs the backend to emit them.

**Tech Stack:** Python 3.11+ / FastAPI / LangGraph / langchain-core (backend), Next.js 16 / React 19 / TypeScript (frontend)

---

### Task 1: Add tool event streaming to `_stream_response`

**Files:**
- Modify: `projects/agents/src/athanor_agents/server.py:110-138`

The current `_stream_response` only listens for `on_chat_model_stream` events from LangGraph's `astream_events`. It needs to also handle `on_tool_start` and `on_tool_end` events to emit tool call visibility data.

**Step 1: Modify `_stream_response` to emit tool events**

Replace lines 110-138 of `server.py` with:

```python
async def _stream_response(agent, messages, config, model_name):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # Send initial role chunk
    yield _sse_chunk(chat_id, created, model_name, {"role": "assistant"})

    in_think = False
    tool_timers: dict[str, float] = {}  # run_id -> start_time

    async for event in agent.astream_events(
        {"messages": messages},
        config=config,
        version="v2",
    ):
        kind = event["event"]

        # --- Tool start ---
        if kind == "on_tool_start":
            run_id = event.get("run_id", "")
            tool_timers[run_id] = time.time()
            tool_event = {
                "type": "tool_start",
                "name": event.get("name", "unknown"),
                "args": event.get("data", {}).get("input", {}),
            }
            yield f"data: {json.dumps(tool_event)}\n\n"
            continue

        # --- Tool end ---
        if kind == "on_tool_end":
            run_id = event.get("run_id", "")
            start = tool_timers.pop(run_id, None)
            duration_ms = int((time.time() - start) * 1000) if start else None
            output_data = event.get("data", {})
            # LangGraph tool output is in data.output (ToolMessage content)
            output = output_data.get("output", "")
            if hasattr(output, "content"):
                output = output.content
            output_str = str(output) if output else ""
            # Truncate very long outputs to avoid blowing up SSE
            if len(output_str) > 4000:
                output_str = output_str[:4000] + "\n... (truncated)"
            tool_event = {
                "type": "tool_end",
                "name": event.get("name", "unknown"),
                "output": output_str,
                "duration_ms": duration_ms,
            }
            yield f"data: {json.dumps(tool_event)}\n\n"
            continue

        # --- LLM text stream ---
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = chunk.content if hasattr(chunk, "content") else ""
            if not text:
                continue
            text, in_think = _filter_think_streaming(text, in_think)
            if text:
                yield _sse_chunk(chat_id, created, model_name, {"content": text})

    # Finish
    yield _sse_chunk(chat_id, created, model_name, {}, finish_reason="stop")
    yield "data: [DONE]\n\n"
```

**Step 2: Test manually against the live agent server**

SSH into Node 1 and restart the agent container, then test with curl:

```bash
curl -N -X POST http://192.168.1.244:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"general-assistant","messages":[{"role":"user","content":"Check all service health"}],"stream":true}'
```

Expected: You should see `tool_start` and `tool_end` JSON lines interleaved with standard `chat.completion.chunk` lines. The `tool_start` line should have `"name":"check_services"` and the `tool_end` should have the output string and a `duration_ms` value.

**Step 3: Commit**

```bash
git add projects/agents/src/athanor_agents/server.py
git commit -m "feat(agents): stream tool_start/tool_end SSE events for tool call visibility"
```

---

### Task 2: Add `GET /v1/agents` endpoint with tool introspection

**Files:**
- Modify: `projects/agents/src/athanor_agents/server.py` (add new route)
- Modify: `projects/agents/src/athanor_agents/agents/__init__.py` (add `get_agent_info`)

**Step 1: Add `get_agent_info` helper to `agents/__init__.py`**

This function introspects each agent's LangGraph graph to discover its tools dynamically, instead of hardcoding them.

Append to `projects/agents/src/athanor_agents/agents/__init__.py`:

```python
# Agent display metadata (name, description, icon)
_AGENT_META = {
    "general-assistant": {
        "name": "General Assistant",
        "description": "System monitoring, GPU metrics, storage info, and infrastructure queries",
        "icon": "terminal",
    },
    "media-agent": {
        "name": "Media Agent",
        "description": "Search and add TV shows & movies, check downloads, Plex activity",
        "icon": "film",
    },
    "home-agent": {
        "name": "Home Agent",
        "description": "Smart home control — lights, climate, automations via Home Assistant",
        "icon": "home",
    },
}


def get_agent_info() -> list[dict]:
    """Return metadata for all agents with dynamically discovered tool names."""
    _init_agents()
    result = []
    for agent_id, agent in _AGENTS.items():
        meta = _AGENT_META.get(agent_id, {"name": agent_id, "description": "", "icon": "terminal"})
        # Extract tool names from the LangGraph agent
        tools = []
        try:
            # create_react_agent stores tools in the graph's nodes
            # Access via the agent's tool node
            tool_node = agent.nodes.get("tools")
            if tool_node and hasattr(tool_node, "tools_by_name"):
                tools = list(tool_node.tools_by_name.keys())
            elif hasattr(agent, "tools"):
                tools = [t.name for t in agent.tools]
        except Exception:
            pass
        result.append({
            "id": agent_id,
            "name": meta["name"],
            "description": meta["description"],
            "icon": meta["icon"],
            "tools": tools,
            "status": "ready",
        })
    return result
```

**Step 2: Add the `/v1/agents` route to `server.py`**

Add after the existing `/v1/models` route (after line 44):

```python
@app.get("/v1/agents")
async def agents_endpoint():
    from .agents import get_agent_info
    return {"agents": get_agent_info()}
```

**Step 3: Test locally**

```bash
curl http://192.168.1.244:9000/v1/agents | python3 -m json.tool
```

Expected: JSON with `agents` array, each entry having `id`, `name`, `description`, `icon`, `tools` (list of tool name strings), and `status: "ready"`.

**Step 4: Commit**

```bash
git add projects/agents/src/athanor_agents/agents/__init__.py projects/agents/src/athanor_agents/server.py
git commit -m "feat(agents): add GET /v1/agents endpoint with dynamic tool introspection"
```

---

### Task 3: Update dashboard `/api/agents` to use live backend

**Files:**
- Modify: `projects/dashboard/src/app/api/agents/route.ts`

Replace the hardcoded `AGENT_METADATA` with a fetch to the new `/v1/agents` endpoint. Keep the hardcoded data as a fallback.

**Step 1: Rewrite the API route**

Replace the entire file with:

```typescript
import { NextResponse } from "next/server";
import { config } from "@/lib/config";

// Fallback metadata — used when /v1/agents is unavailable
// (e.g., agent server running older version without the endpoint)
const FALLBACK_METADATA: Record<
  string,
  { name: string; description: string; tools: string[]; icon: string }
> = {
  "general-assistant": {
    name: "General Assistant",
    description:
      "System monitoring, GPU metrics, storage info, and infrastructure queries",
    tools: [
      "check_services",
      "get_gpu_metrics",
      "get_vllm_models",
      "get_storage_info",
    ],
    icon: "terminal",
  },
  "media-agent": {
    name: "Media Agent",
    description:
      "Search and add TV shows & movies, check downloads, Plex activity",
    tools: [
      "search_tv_shows",
      "get_tv_calendar",
      "get_tv_queue",
      "get_tv_library",
      "add_tv_show",
      "search_movies",
      "get_movie_calendar",
      "get_movie_queue",
      "get_movie_library",
      "add_movie",
      "get_plex_activity",
      "get_watch_history",
      "get_plex_libraries",
    ],
    icon: "film",
  },
  "home-agent": {
    name: "Home Agent",
    description:
      "Smart home control — lights, climate, automations via Home Assistant",
    tools: [
      "get_ha_states",
      "get_entity_state",
      "find_entities",
      "call_ha_service",
      "set_light_brightness",
      "set_climate_temperature",
      "list_automations",
      "trigger_automation",
    ],
    icon: "home",
  },
};

export async function GET() {
  // Try the new /v1/agents endpoint first (dynamic tool introspection)
  try {
    const res = await fetch(`${config.agentServer.url}/v1/agents`, {
      next: { revalidate: 30 },
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // /v1/agents not available — fall through to health-based approach
  }

  // Fallback: use /health + hardcoded metadata
  try {
    const res = await fetch(`${config.agentServer.url}/health`, {
      next: { revalidate: 30 },
    });

    if (!res.ok) {
      throw new Error(`Agent server returned ${res.status}`);
    }

    const data = await res.json();
    const liveAgents: string[] = data.agents ?? [];

    const agents = Object.entries(FALLBACK_METADATA).map(([id, meta]) => ({
      id,
      ...meta,
      status: liveAgents.includes(id) ? "ready" : "unavailable",
    }));

    return NextResponse.json({ agents });
  } catch {
    // Agent server unreachable — return all as unavailable
    const agents = Object.entries(FALLBACK_METADATA).map(([id, meta]) => ({
      id,
      ...meta,
      status: "unavailable",
    }));

    return NextResponse.json({ agents });
  }
}
```

**Step 2: Test via the preview**

Navigate to `http://localhost:3000/agents` in the preview. Agent cards should still render (using the fallback path since the live agent server hasn't been redeployed yet). Once Task 2 is deployed, they'll use the dynamic path.

**Step 3: Commit**

```bash
git add projects/dashboard/src/app/api/agents/route.ts
git commit -m "feat(dashboard): fetch agent metadata from /v1/agents with fallback"
```

---

### Task 4: Deploy backend changes to Node 1

**Files:**
- No code changes — Ansible deployment

**Step 1: Deploy the agent server**

The agent server runs as a Docker container on Node 1. Ansible's `agents` role handles building and deploying it.

```bash
cd /home/athanor/athanor/ansible
ansible-playbook playbooks/site.yml --tags agents --limit node1
```

If running from DEV (Windows):
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "cd ~/athanor/ansible && ansible-playbook playbooks/site.yml --tags agents --limit node1"
```

Alternatively, if the agent container is running directly (not via Ansible):
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244
cd ~/athanor/projects/agents
docker compose down && docker compose up -d --build
```

**Step 2: Verify tool streaming**

```bash
curl -N -X POST http://192.168.1.244:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"general-assistant","messages":[{"role":"user","content":"Check all services"}],"stream":true}'
```

Verify you see `tool_start` and `tool_end` lines in the stream.

**Step 3: Verify `/v1/agents`**

```bash
curl http://192.168.1.244:9000/v1/agents | python3 -m json.tool
```

Verify it returns all agents with dynamically discovered tool names.

---

### Task 5: Deploy dashboard to Node 2

**Files:**
- No code changes — Ansible deployment

**Step 1: Deploy**

```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "cd ~/athanor/ansible && ansible-playbook playbooks/site.yml --tags dashboard --limit node2"
```

**Step 2: Verify**

Open `http://192.168.1.225:3001/agents` in a browser. Should show agent cards with live status. Click an agent, send a message, and verify tool call cards appear inline in the chat stream.

**Step 3: Commit any deployment fixes**

If any config or build changes were needed, commit them.

---

### Task 6: End-to-end verification

**Step 1: Full flow test**

1. Open `http://192.168.1.225:3001/agents`
2. Verify all 3 agent cards show with green "ready" dots (general-assistant and media-agent should be ready; home-agent may be unavailable if not registered in `_init_agents`)
3. Click General Assistant
4. Type "Check all service health" and send
5. Watch for: tool_start card (spinner + "check_services"), tool_end card (ok badge + duration), then assistant text response
6. Click the tool call card to expand — verify output is visible
7. Test Media Agent: "What's in the Sonarr queue?"
8. Verify tool calls appear inline

**Step 2: Edge cases to test**

- Send a message that doesn't trigger tools (e.g., "What is Athanor?") — should get clean text response with no tool cards
- Click an unavailable agent — should be a no-op (card stays grayed out)
- Rapid messages while streaming — Send button should be disabled during stream
- Very long tool output — should be truncated at 4000 chars with "... (truncated)"
- Agent server down — cards should all show "unavailable", chat should show error message on send

**Step 3: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: end-to-end agent page fixes from integration testing"
```
