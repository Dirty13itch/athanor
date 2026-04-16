# Athanor Dashboard — Full Specification

*Extends ADR-007. This is the detailed spec for what the dashboard shows, how it gets data, and the information hierarchy.*

**Stack:** Next.js 16 + shadcn/ui + Tailwind CSS + TypeScript
**Deployed to:** Node 2:3001
**Design:** Dark theme, Cormorant Garabmond typography, warm amber accents (#d4a574)

---

## Panels

### System Health Panel

- Node status cards (Node 1, Node 2, VAULT, DEV) — CPU, RAM, disk, network
- GPU cards with VRAM usage, temperature, power draw, current model loaded
- Network status (5GbE throughput between nodes)
- Storage status (NVMe usage per node, VAULT HDD array health and capacity)

### Agent Management Panel

- Agent cards showing: status (idle/running/error), current model, last execution time
- Toggle agents on/off
- Edit agent config: model endpoint, tools, schedule interval (for proactive agents)
- View execution logs and traces
- Supervisor routing visualization — which agent handled which request

### Inference Panel

- Active vLLM instances with model name, VRAM usage, request queue depth
- Model swap controls (load/unload models via vLLM model management API)
- Inference latency graphs (tokens/second, time-to-first-token)
- LiteLLM routing status — which model alias maps to which backend

### Media Panel

- Plex now playing / recently added (via Tautulli API)
- *arr stack status (downloads in progress, queue depth)
- Stash scan status
- Tdarr transcoding queue and progress (when deployed)

### Home Panel

- Home Assistant entity states (lights, sensors, climate)
- Recent automation triggers and actions
- Home Agent decision log

### Creative Panel

- ComfyUI queue status
- Recent generations (thumbnail gallery)
- GPU allocation for creative workloads

---

## Data Sources and Telemetry Pipeline

### Metrics Collection (Prometheus at VAULT:9090)

| Source | Endpoint | What |
|--------|----------|------|
| node_exporter | Node 1:9100, Node 2:9100 | CPU, RAM, disk, network per node |
| dcgm-exporter | Node 1:9400, Node 2:9400 | GPU temp, VRAM, utilization, power per GPU |
| vLLM metrics | Node 1:8000/metrics, Node 2:8000/metrics | Request queue, tokens/sec, TTFT, model status |
| Docker metrics | Per-node | CPU/RAM per container |

### Agent State (LangGraph API at Node 1:9000)

- Agent status: idle / running / error per agent
- Current model assignment per agent
- Last execution timestamp and duration
- Execution trace: tool calls, model responses, routing decisions
- Supervisor routing log: which agent handled which request and why

### Service APIs (direct polling)

| Service | API | Data |
|---------|-----|------|
| Plex/Tautulli | Tautulli API (VAULT:8181) | Now playing, recently added, history |
| Sonarr | REST API (VAULT:8989) | Download queue, upcoming, wanted |
| Radarr | REST API (VAULT:7878) | Download queue, upcoming, wanted |
| Tdarr | REST API (when deployed) | Transcoding queue, progress, ETA |
| Home Assistant | REST/WebSocket (VAULT:8123) | Entity states, automations, event log |
| ComfyUI | REST API (Node 2:8188) | Queue status, active generation, outputs |

---

## Information Hierarchy

### Glance (top-level, visible without interaction)

- Node status dots (green/yellow/red)
- Total GPU utilization bar
- Active agent count
- Active Plex streams count

### Click (panel-level, one interaction)

- Individual GPU cards with model loaded and VRAM usage
- Agent cards with status and last execution
- Media pipeline with queue depths
- Home entity states

### Drill-down (detail, secondary interaction)

- Full inference latency graphs
- Agent execution traces (step-by-step)
- Per-container resource usage
- Tdarr job history
- Home Agent decision reasoning

---

## Implementation Notes

- Dashboard is a thin presentation layer — no business logic
- All data comes from existing APIs (Prometheus, LangGraph, Tautulli, HA, etc.)
- Next.js API routes act as proxies to service APIs
- WebSocket for real-time updates (agent status, Plex now playing)
- Polling for less time-sensitive data (metrics, media library)
- The dashboard never SSHes into nodes — all actions go through documented APIs
- Open WebUI coexists as the chat interface; dashboard is the control surface
