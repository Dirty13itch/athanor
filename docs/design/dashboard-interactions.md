# Dashboard Interaction Patterns — Actions vs Observation

*The dashboard is not just a monitoring tool — it's a control surface. Extends the Dashboard SPEC.*

---

## Observation-Only (read, no write)

- System health metrics (CPU, RAM, GPU temp/utilization, network throughput)
- Agent execution traces (what happened, step by step)
- Plex now playing and recently added
- Home Agent decision log (what it decided and why)
- Supervisor routing log (which agent handled which request)
- Tdarr transcoding history

---

## Direct Actions (click to do)

| Action | What Happens | Backend API |
|--------|-------------|-------------|
| **Agent toggle** | Turn agent on/off. Proactive agents stop their timer. Reactive agents stop accepting supervisor requests. | LangGraph API (Node 1:9000) |
| **Agent config edit** | Change model endpoint, update tool list, change proactive schedule interval. Changes apply immediately if LangGraph supports hot reload, otherwise container restart. | LangGraph API |
| **Model swap** | Load or unload a model on a specific vLLM instance. E.g., "Replace Qwen3-32B on Node 1:8000 with Qwen3-30B-A3B" | vLLM model management API |
| **Inference queue** | View pending requests, cancel stuck requests, reprioritize | vLLM API |
| **Creative queue** | Cancel queued ComfyUI generation, reprioritize | ComfyUI API (Node 2:8188) |
| **Media actions** | Trigger Plex library scan, pause/resume Tdarr, manually add to *arr request queue | Tautulli/Sonarr/Radarr APIs |
| **Home override** | Override Home Agent decision (e.g., turn lights back on). Override is logged and fed back as signal for pattern learning. | Home Assistant REST API |
| **System actions** | Restart Docker container, trigger Ansible playbook re-run, initiate model staging (rsync VAULT → node) | Docker Engine API, Ansible API |

---

## Dangerous Actions (confirmation required)

These require a confirmation dialog before execution:

- Stop all vLLM instances on a node
- Restart a node (requires SSH under the hood)
- Delete a model from Tier 1 cache
- Clear Knowledge Agent embeddings
- Factory reset an agent's config to defaults

---

## Implementation Pattern

```
Dashboard button click
  → Next.js API route
  → Calls the appropriate service API:
    - vLLM model management API for model swaps
    - LangGraph API for agent state changes
    - Docker Engine API for container management
    - Home Assistant REST API for home overrides
    - *arr APIs for media actions
  → Returns result to dashboard
  → Updates UI reactively
```

The dashboard never SSHes into nodes directly. All actions go through documented APIs. This is both a security boundary (API access, not root access) and a reliability pattern (if the dashboard breaks, services run independently).

---

## Open WebUI as Interim

Before the dashboard has full agent management, Open WebUI provides the chat interface with agent selection. The dashboard adds system health, agent management, media, home, and creative panels that Open WebUI can't provide. They coexist — Open WebUI for conversation, dashboard for system control.
