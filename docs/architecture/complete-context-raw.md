# Athanor — Complete Architectural Context (RAW EXPORT)

> **WARNING: This is a conversation export from claude.ai dated 2026-02-24.**
>
> **DO NOT treat this as authoritative.** It contains known inaccuracies:
> - Claims LiteLLM was rejected — LiteLLM IS deployed on VAULT:4000 (ADR-012)
> - Claims Qdrant not needed — Qdrant IS deployed on Node 1:6333
> - References a 4090 on Node 2 — the 4090 is on Node 1; Node 2 has RTX 5090 + RTX 5060 Ti
> - References Qwen3-30B-A3B on Node 2 — Node 2 runs Qwen3-14B
> - States "Direct vLLM API (no proxy)" as current architecture — LiteLLM proxy routes all inference
>
> **Valuable content has been extracted to proper locations:**
> - Security architecture → `docs/decisions/ADR-013-security-architecture.md`
> - Dashboard spec → `docs/projects/dashboard/SPEC.md`
> - EoBQ architecture → `docs/projects/eoq/ARCHITECTURE.md`
> - DEV tool stack → `docs/dev-environment.md`
> - Home Agent HA integration → `docs/design/home-agent-ha-integration.md`
> - Tdarr deployment → `docs/design/tdarr-deployment.md`
> - Intelligence layers → `docs/design/intelligence-layers.md`
> - VRAM workload profiles → `docs/design/vram-workload-profiles.md`
> - Kindred concept → `docs/projects/kindred/CONCEPT.md`
> - Ulrich Energy workflows → `docs/projects/ulrich-energy/WORKFLOWS.md`
> - LoRA training pipeline → `docs/design/lora-training-pipeline.md`
> - Audio generation pipeline → `docs/design/audio-generation-pipeline.md`
> - Dashboard interactions → `docs/design/dashboard-interactions.md`
> - Model swap protocol → `docs/design/model-swap-protocol.md`
> - VPN torrent stack → `docs/design/vpn-torrent-stack.md`
>
> **Kept as reference only.** If you need any of this content, read the extracted files above instead.

---

*Original content follows below. See the source file for full text.*
# Athanor — Complete Architectural Context

*Everything decided across claude.ai conversations that isn't yet committed to repo docs. This document bridges the gap between what was discussed and what Claude Code can read in the repo.*

*Generated: 2026-02-24*

---

## 1. SYSTEM VISION — WHAT ATHANOR ACTUALLY IS

Athanor is not just "a homelab with GPUs." It's a **unified intelligent system** with five operational layers, all running on locally-owned hardware. The system should feel like a single coherent entity, not a collection of Docker containers.

### The Five Layers

**Layer 1 — AI Inference:** Multiple local LLM models running concurrently on 7 GPUs. Not one big model — many specialist models serving different roles simultaneously. Abliterated (uncensored) models for content that cloud providers refuse. The routing layer sends each request to the right model on the right GPU.

**Layer 2 — Media:** 224TB of storage serving movies, TV, music through Plex. Automated acquisition (*arr stack). Stash for adult content management. **Tdarr for library-wide transcoding optimization** — converting legacy codecs to H.265/AV1 to save storage space and improve streaming compatibility. AI-powered organization, recommendation, and curation layered on top.

**Layer 3 — Home Automation:** Home Assistant as the hub, with an MQTT broker (Mosquitto) as the event bus between HA and Athanor's AI agents. This is not just "if motion then lights" — the Home Agent understands context.

#### Home Agent ↔ HA Integration Architecture

```
Home Assistant → MQTT → Event Bus → Home Agent (LangGraph on Node 1)
                                          ↓
                                    Context evaluation:
                                    - Time of day
                                    - Who's home (occupancy)
                                    - Current activity (coding? EoBQ? sleeping?)
                                    - Weather conditions
                                    - Calendar events
                                    - Historical patterns
                                          ↓
                                    Decision/Action
                                          ↓
                                    MQTT → Home Assistant → Execute
```

**MQTT Topic Structure:**
```
athanor/ha/motion/living_room      → motion detected
athanor/ha/temperature/outside     → temperature reading
athanor/ha/occupancy/home          → presence detection
athanor/ha/light/living_room/state → current light state
athanor/ha/command/lights/living_room → {"brightness": 20, "color_temp": "warm"}
```

**Context-Aware Decision Examples:**
- "Motion in living room at 11 PM when home is occupied → dim lights to 20%, warm color temp. Don't turn on bright overhead."
- "Temperature dropping below 60°F and nobody home → don't adjust thermostat (save energy)"
- "Shaun is in a creative session (EoBQ running on Node 2) → suppress non-critical notifications, keep ambient lighting stable"
- "Motion detected at 2 AM + occupancy = asleep → it's the cat. Ignore."
- "Amanda arrives home (phone connects to WiFi) → turn on entry lights, set living room to her preferred scene"

**The key design insight:** The Home Agent is a triggered specialist — it activates when MQTT events arrive, processes them with full context awareness, and goes idle. It doesn't need to be always-running. It shares inference resources with other agents and only consumes GPU when there's actually something to decide.

**Proactive schedule:** Every 5 minutes, the Home Agent also does a proactive scan — checking environmental conditions, looking for patterns, anticipating needs before events trigger. This is where pattern learning happens over time.

**Hardware integration:**
- Lutron lighting system (controller at 192.168.1.158)
- UniFi network for device presence detection
- Temperature/humidity sensors via HA integrations
- Potential future: Zigbee/Z-Wave coordinators via USB passthrough to VAULT

**Layer 4 — Creative Production:** This is a full creative AI environment:
- **Image generation:** ComfyUI running Flux dev, Stable Diffusion on Node 2's 5090
- **Video generation:** Wan 2.2 workflows in ComfyUI
- **Audio generation/processing:** Future capability
- **Game development:** Empire of Broken Queens — procedural LLM-generated narrative with AI-generated visuals
- **General creative:** Any new diffusion model, LoRA, or creative tool gets deployed here

**Layer 5 — Professional Tools:** Ulrich Energy business automation — report generation, scheduling, data analysis. Future: any app or tool Shaun builds that runs on the infrastructure.

### The Self-Feeding Principle

Athanor is named after an alchemist's self-feeding furnace. The system is designed to improve itself:

- **Phase 1 (now):** Claude Code on Anthropic's servers → builds and manages Athanor remotely
- **Phase 2 (next):** Claude Code on Anthropic → builds + manages Athanor via MCP servers that read/write infrastructure state
- **Phase 3 (endgame):** Local inference models on Athanor → self-manage routine operations via autonomous agents. Cloud AI used only for complex reasoning tasks.

The Knowledge Agent (proactive, daily at 3 AM) is the first concrete step toward self-improvement — it indexes documents, generates embeddings, and accumulates knowledge that improves every other agent's responses over time.

---

## 2. MEDIA STACK — COMPLETE SERVICE INVENTORY

### Currently Running on VAULT (Ansible-deployed 2026-02-24)

| Service | Port | Role |
|---------|------|------|
| Plex | 32400 | Media streaming (claimed, libraries configured) |
| Sonarr | 8989 | TV show acquisition automation |
| Radarr | 7878 | Movie acquisition automation |
| Prowlarr | 9696 | Indexer management (needs indexer credentials) |
| SABnzbd | 8080 | Usenet download client (needs Usenet credentials) |
| Tautulli | 8181 | Plex monitoring and statistics |
| Stash | 9999 | Adult content management — media scanning, metadata, scene detection, face detection, transcoding, thumbnails |
| Home Assistant | 8123 | Home automation hub (needs browser onboarding) |
| Prometheus | 9090 | Time-series metrics (scraping Node 1, Node 2, VAULT) |
| Grafana | 3000 | Dashboards and alerting |

### Planned / Not Yet Deployed

| Service | Role | Blocker |
|---------|------|---------|
| **Tdarr** | Library-wide transcoding (H.265/AV1 conversion) | Deploy after media stack stable |
| qBittorrent + Gluetun | Torrent client with VPN tunnel | NordVPN credentials needed |
| Reverse proxy (Traefik) | Service routing, TLS termination | Deploy before remote access |
| MQTT broker (Mosquitto) | Event bus between HA and AI agents | Deploy with Home Agent integration |

### Tdarr — Library-Wide Transcoding Optimization

Tdarr runs on VAULT as a Docker container and uses the Arc A380 for hardware-accelerated transcoding. This is a background optimization service — it continuously scans the media library and converts files to more efficient codecs, saving storage space and improving streaming compatibility.

**What it does:**
- Scans the entire 224TB media library for legacy codecs (MPEG-2, H.264, FLAC, uncompressed audio)
- Converts video to H.265 (HEVC) or AV1 where the quality/size tradeoff is favorable
- Remuxes containers when needed (e.g., AVI → MKV without re-encoding)
- Strips unnecessary audio tracks and subtitles based on language preferences
- Normalizes audio levels across the library

**Hardware acceleration:**
- Primary: Intel QuickSync on the Arc A380 for H.265/AV1 hardware encode
- Fallback: CPU encoding on the 9950X for codecs the A380 can't handle
- The A380's QuickSync engine handles most transcoding workloads efficiently at 75W TDP
- No contention with GPU inference — the A380 is in VAULT, not a compute node

**Scheduling and priority:**
- Scheduled during low-usage hours (overnight, typically midnight–6 AM) to avoid contention with Plex streaming
- Throttled during active Plex streams — Tdarr pauses or reduces workers when Tautulli reports active sessions
- I/O scheduling matters: transcoding saturates disk throughput, so it should not overlap with parity checks
- Worker count configurable: start with 1 GPU worker + 2 CPU workers, tune based on observed load

**Non-destructive workflow:**
- Originals kept until conversion verified (Tdarr's built-in verification)
- Separate output directory, then atomic move replaces original
- Tdarr maintains a database of processed files — won't re-process unless source changes
- Health check plugins verify output plays correctly before replacing source

**Storage impact:**
- H.265 typically achieves 40-60% size reduction from H.264 at equivalent quality
- AV1 achieves 50-70% reduction but encodes much slower (better for archive, not bulk)
- On a 224TB library that's 90% full (18TB free), converting the H.264 content could reclaim 30-60TB
- This directly addresses the "VAULT HDD at 90% full, ~12 months before capacity" concern

**Integration with *arr stack:**
- New downloads from Sonarr/Radarr arrive as whatever codec the source provides
- Tdarr picks them up automatically after Sonarr/Radarr import completes
- Plex detects the new optimized file seamlessly (same path, updated container)

### Download Pipeline

```
Prowlarr (indexer management — aggregates Usenet + torrent indexers)
  ↓ feeds indexers to
Sonarr + Radarr (request management — tracks wanted content, grabs releases)
  ↓ sends downloads to
SABnzbd (Usenet) + qBittorrent/Gluetun (torrent over VPN)
  ↓ completed downloads processed by
Sonarr/Radarr (rename, move to library, update metadata)
  ↓ library changes detected by
Plex (automatic library scan) + Tdarr (transcoding queue)
```

### qBittorrent + Gluetun VPN Setup

Torrent traffic MUST be tunneled through a VPN. Gluetun is a container that creates a VPN tunnel and forces all traffic from qBittorrent through it. If the VPN drops, qBittorrent loses network access entirely — no IP leak possible.

**Architecture:**
```yaml
# Docker Compose on VAULT
gluetun:
  image: qmcgaw/gluetun
  cap_add: [NET_ADMIN]
  environment:
    - VPN_SERVICE_PROVIDER=nordvpn
    - VPN_TYPE=openvpn  # or wireguard
    - OPENVPN_USER=<nordvpn_service_username>
    - OPENVPN_PASSWORD=<nordvpn_service_password>
    - SERVER_COUNTRIES=Switzerland  # or other privacy-friendly jurisdiction
  ports:
    - 8080:8080  # qBittorrent web UI (exposed through Gluetun's network)

qbittorrent:
  image: linuxserver/qbittorrent
  network_mode: "service:gluetun"  # ALL traffic goes through Gluetun
  environment:
    - WEBUI_PORT=8080
  volumes:
    - /mnt/user/downloads:/downloads
    - /mnt/user/appdata/qbittorrent:/config
```

**Blocker:** NordVPN service credentials needed. These are separate from the NordVPN account login — they're generated in the NordVPN dashboard under "Manual Setup."

**Kill switch behavior:** `network_mode: "service:gluetun"` means qBittorrent has NO direct network access. If Gluetun's VPN tunnel drops, qBittorrent is fully isolated. This is a hardware-level kill switch implemented by Docker networking — no configuration needed.

**Integration with *arr stack:** Sonarr and Radarr talk to qBittorrent's API through the exposed port (8080). They send download requests and monitor completion. When a download finishes, Sonarr/Radarr hardlink or move the file to the library and trigger a Plex scan.

---

## 3. CREATIVE AI ENVIRONMENTS

### Image Generation (ComfyUI on Node 2)

- **Primary GPU:** RTX 5090 (32GB) — largest VRAM, handles high-res generation
- **Secondary:** RTX 5060 Ti (16GB) — currently running Flux dev FP8
- **Models:** Flux dev (FP8), Wan 2.2 (video), Stable Diffusion variants, LoRAs
- **Access:** Port 8188 on Node 2

**The 5090 contention problem:** ComfyUI and vLLM inference both want the 5090. They time-multiplex — ComfyUI loads/unloads diffusion models as needed, vLLM loads/unloads LLM models. Docker Compose resource constraints manage this. Model loading from local NVMe takes ~2-5 seconds.

If contention becomes painful, the PRO 6000 (96GB) resolves it — LLM gets the PRO 6000 permanently, 5090 becomes dedicated creative GPU.

### Video Generation

- Wan 2.2 workflows in ComfyUI
- Runs on the 5090 for VRAM headroom
- Batch workload — tolerates higher latency than interactive chat
- Scheduled during inference idle periods or on dedicated GPU

### Empire of Broken Queens — Game Development Environment

Full architecture documented in **Section 11** (Projects). Summary:
- AI-driven interactive cinematic adult game with LLM-generated dialogue and AI-generated visuals
- Abliterated model REQUIRED for explicit dialogue — cloud refuses
- Narrative state store (characters, relationships, world state) is the core intelligence, not the model
- Dialogue generation pipeline: load state → construct prompt → generate (local abliterated) → validate → update state
- Asset pipeline: ComfyUI (Flux/SDXL for images, Wan for video) on Node 2
- Dev environment must support LLM-in-the-loop testing with mock mode, quality evaluation, and regression testing

### Future Creative Capabilities

- **Audio generation and processing:** Music, voice synthesis, sound effects. Models TBD — this space is evolving fast (Bark, MusicGen, etc.)
- **LoRA training on cluster GPUs:** Custom character models for EoBQ (consistent character appearance across scenes), custom style models for specific aesthetic. Training on the 5090 or TP across 5070 Ti group on Node 1. Training is a batch workload — schedule overnight or when inference demand is low.
- **Real-time generation for interactive experiences:** As diffusion models get faster (SDXL Turbo, LCM), the gap between "batch generate and store" and "generate on demand" closes. Future EoBQ versions could generate scene images in real-time during gameplay rather than pre-rendering.
- **Whatever new models emerge:** The architecture is model-agnostic. New diffusion architecture → download, add to ComfyUI, test. New video model → same pattern.

### Model Swap Patterns on Node 2

The 5090 (32GB) is time-shared between LLM inference and diffusion workloads. The swap pattern:

1. **Idle state:** vLLM has an LLM loaded (e.g., abliterated Qwen3-32B). ComfyUI has no model loaded.
2. **Creative request arrives:** ComfyUI loads diffusion model (Flux dev FP8 ~12GB). vLLM's model stays loaded if VRAM allows, or gets offloaded if combined exceeds 32GB.
3. **Generation completes:** ComfyUI releases diffusion model VRAM. vLLM model reloads if offloaded (~2-5 sec from local NVMe).
4. **Concurrent chat during generation:** Routes to the 4090 instead. The supervisor knows the 5090 is busy with creative workloads and diverts interactive chat to the 4090.

Docker Compose resource constraints manage GPU allocation. `deploy.resources.reservations.devices` pins each container to specific GPUs. The swap is not automatic — it's orchestrated by which containers are running and what the supervisor routes where.

The PRO 6000 (96GB) eliminates this dance entirely — LLM gets the PRO 6000 permanently, 5090 becomes dedicated creative. No time-sharing, no model swaps, no contention.

---

## 4. AGENT ARCHITECTURE — THE INTELLIGENCE LAYER

### The 6 Agents + Supervisor (ADR-008, Current Architecture)

LangGraph on Node 1. Supervisor routes requests. Each agent is a directed graph with explicit control flow.

| Agent | Type | Schedule | Tools | Model Target |
|-------|------|----------|-------|-------------|
| General Assistant | Reactive | On-demand | Web search, file ops, uncensored chat | Fast model (4090) |
| Research Agent | Reactive | On-demand | Web search, local knowledge base | Large model (TP=4) |
| Media Agent | Proactive | Every 15 min | Sonarr, Radarr, Tautulli, Stash APIs | Small model |
| Home Agent | Proactive | Every 5 min | Home Assistant API, MQTT | Small model |
| Creative Agent | Reactive | On-demand | ComfyUI API | Triggers GPU workloads |
| Knowledge Agent | Proactive | Daily 3 AM | Document indexing, embeddings | Embedding model |

**Supervisor** on Node 1:9000 routes requests based on classification. Agents exposed as OpenAI-compatible endpoints → appear as "models" in Open WebUI.

**API Gateway** on Node 2:9001 proxies dashboard → agents across the 5GbE network.

### How Agents Become Intelligent Over Time

This is the self-improving loop — the furnace feeding itself.

**Layer 1 — Reactive Intelligence (current state):**
Each agent responds to requests or schedules. No memory between invocations beyond what's in the prompt. The supervisor classifies input and routes to the right agent. Agents call vLLM, get a response, return it. Simple, debuggable, working.

**Layer 2 — Accumulated Knowledge (next phase):**
The Knowledge Agent runs proactively at 3 AM daily. It:
- Indexes all documents in the repo (CLAUDE.md, ADRs, research docs, project docs)
- Processes conversation transcripts and session logs
- Generates embeddings using the embedding model on Node 1 GPU 4 (Qwen3-Embedding-0.6B, 1024-dim, port 8001)
- Stores embeddings in a vector database (start with simple file-based, scale to Qdrant if volume demands)
- Tracks system state changes over time
- Builds a knowledge graph of entities, relationships, decisions, and their rationale

When any other agent receives a request, the supervisor first queries the Knowledge Agent's accumulated data for relevant context. This means:
- Research Agent gets "here's what we've already researched about this topic" before searching the web
- General Assistant gets "here's what Shaun has previously said about this" before answering
- Media Agent gets "here's Shaun's viewing history and patterns" before making recommendations
- Home Agent gets "here's what happened the last 50 times this event fired" before deciding

The more the system is used, the more knowledge accumulates, the better every agent performs. This is the first concrete step where Athanor starts feeding itself.

**Layer 3 — Pattern Recognition (future):**
Agents begin recognizing patterns in their own operation and user behavior:
- Media Agent tracks which shows get watched vs abandoned after acquisition → adjusts recommendation weights, potentially auto-pauses series that match abandonment patterns
- Home Agent learns occupancy patterns over weeks → stops treating regular patterns as events (Shaun always gets up at 6 AM on weekdays — don't fire "motion detected" as a novel event)
- Research Agent learns which sources and approaches Shaun finds useful → prioritizes those in future searches
- Creative Agent tracks which generation parameters produce results Shaun keeps vs regenerates → adjusts defaults

This requires: a feedback signal. The system needs to know whether its outputs were good. For some agents this is implicit (Media Agent: was the show watched to completion?). For others it needs explicit signals (thumbs up/down on agent responses, tracked in the knowledge store).

**Layer 4 — Self-Optimization (endgame):**
The system monitors its own infrastructure and performance:
- Which models produce the best results for which tasks? (A/B test model versions)
- Which GPU allocation minimizes latency for the current workload mix?
- Which agent configurations get the best user satisfaction scores?
- When better models are released, auto-evaluate them against the current baseline and recommend (or auto-deploy) upgrades
- When inference patterns show a GPU is consistently underutilized, suggest reallocation
- When knowledge accumulation shows diminishing returns, trigger summarization/compression

This is where Athanor genuinely starts managing itself. The Knowledge Agent becomes an optimization agent — not just accumulating knowledge but using it to improve the system that accumulates it. The recursive nature of the furnace feeding itself.

### What Was Explicitly Rejected (Don't Revive)

- **GWT/CST (Global Workspace Theory / Continuous State Tensor):** The Kaizen-era cognitive architecture with 10 specialist slots, broadcast/compete/integrate dynamics, and a persistent state tensor. Replaced by simpler LangGraph agents with supervisor routing.
- **10 specialist slot system:** The numbered slot architecture (Slot 0 Controller, Slot 1 Reasoning, etc.). Replaced by 6 named agents with clear roles.
- **Contract-driven slot architecture:** Specialist slots defined by interface contracts. Replaced by direct agent definitions.
- **LiteLLM proxy:** Not needed — vLLM serves OpenAI-compatible API directly.
- **Qdrant + Neo4j (for now):** Vector and graph databases were planned for the GWT memory system. Not immediately needed. Start with simpler storage, add when the Knowledge Agent's data volume demands it.

### What Survived From Kaizen (Evolved, Not Abandoned)

- **Concurrent specialist concept** → became the 6 parallel agents
- **Memory retrieval pipeline** → became the Knowledge Agent with embedding search
- **Context-aware home automation** → became the Home Agent + HA integration
- **Model routing by task type** → became LangGraph supervisor routing
- **Graceful degradation** → still a core principle: every failure mode has a designed response

---

## 5. THE DASHBOARD — COMMAND CENTER SPEC

### Architecture Decision: ADR-007

**Stack:** Next.js + shadcn/ui (custom-built, not third-party)
**Design:** Dark theme, Cormorant Garamond typography, warm amber accents (alchemical aesthetic)
**Deployed to:** Node 2:3001

### What the Dashboard Shows

**System Health Panel:**
- Node status cards (Node 1, Node 2, VAULT, DEV) — CPU, RAM, GPU utilization
- GPU cards with VRAM usage, temperature, current model loaded
- Network status (5GbE throughput, InfiniBand status when deployed)
- Storage status (NVMe usage per node, HDD array health)

**Agent Management Panel:**
- Agent cards showing: status (idle/running/error), current model, last execution time
- Toggle agents on/off
- Edit agent config: model endpoint, tools, schedule interval (for proactive agents)
- View execution logs and traces
- Supervisor routing visualization — which agent handled which request

**Inference Panel:**
- Active vLLM instances with model name, VRAM usage, request queue depth
- Model swap controls (load/unload models)
- Inference latency graphs (tokens/second, time-to-first-token)

**Media Panel:**
- Plex now playing / recently added
- *arr stack status (downloads in progress, queue depth)
- Stash scan status
- Tdarr transcoding queue and progress

**Home Panel:**
- Home Assistant entity states (lights, sensors, climate)
- Recent automation triggers and actions
- Home Agent decision log

**Creative Panel:**
- ComfyUI queue status
- Recent generations (thumbnail gallery)
- GPU allocation for creative workloads

### Data Sources and Telemetry Pipeline

The dashboard is a presentation layer for an observability system. The observability system must exist first.

**Metrics Collection (Prometheus):**
- `node_exporter` on Node 1 (:9100) and Node 2 (:9100) — CPU, RAM, disk, network per node
- `dcgm-exporter` on Node 1 (:9400) and Node 2 (:9400) — GPU temperature, VRAM usage, utilization, power draw per GPU
- vLLM's native Prometheus metrics endpoint — request queue depth, tokens/second, time-to-first-token, model load status per instance
- Docker container metrics — CPU/RAM per container on all nodes
- VAULT system metrics via node_exporter

**Agent State (LangGraph API):**
- Agent status: idle / running / error per agent
- Current model assignment per agent
- Last execution timestamp and duration
- Execution trace: which tool calls, which model responses, routing decisions
- Supervisor routing log: which agent handled which request and why

**Service APIs (direct polling):**
- Plex: now playing, recently added (Tautulli API)
- Sonarr/Radarr: download queue, upcoming, wanted items
- Tdarr: transcoding queue, progress, estimated completion
- Home Assistant: entity states, recent automations, event log
- ComfyUI: queue status, active generation, recent outputs

**Information Hierarchy (what's a glance, what's a click, what's a drill-down):**
- **Glance (top-level):** Node status dots (green/yellow/red), total GPU utilization bar, active agent count, active Plex streams count
- **Click (panel-level):** Individual GPU cards with model loaded and VRAM usage, agent cards with status and last execution, media pipeline with queue depths
- **Drill-down (detail):** Full inference latency graphs, agent execution traces, per-container resource usage, Tdarr job history

### Why Not Third-Party Agent GUIs

We evaluated AutoGen Studio and CrewAI Studio. Both are their own agent frameworks that would replace LangGraph. The dashboard is built on our existing stack — it reads LangGraph's native APIs for agent state, execution history, and step traces. No additional framework dependency.

---

## 6. CONCURRENT WORKLOAD SCENARIOS

These define the actual design targets — what the system must handle simultaneously.

### Real VRAM Budget (accounting for serving overhead)

Raw VRAM ≠ usable for model weights. Each GPU loses capacity to CUDA context, vLLM overhead, and KV cache reserve for concurrent requests:

| GPU | Location | Raw VRAM | CUDA + vLLM Overhead | KV Cache Reserve | Usable for Weights |
|-----|----------|----------|---------------------|-----------------|-------------------|
| 5090 | Node 2 | 32GB | ~1.5GB | ~6GB | ~24GB |
| 4090 | Node 2 | 24GB | ~1.5GB | ~5GB | ~17GB |
| 5070 Ti ×4 | Node 1 (TP=4) | 64GB total | ~5GB | ~16GB | ~43GB pooled |

**Total usable for weights: ~84GB across 6 inference GPUs.**

KV cache reserve explained: Each concurrent request consumes KV cache proportional to sequence length × hidden dimension × layers. A 14B model at 32K context consumes ~2GB KV cache per concurrent request. The reserve allows 2 concurrent requests per GPU without OOM. If concurrency increases, reserve grows and weight capacity shrinks.

### Typical Evening (Shaun coding, home running)
```
Node 1:8000 — vLLM TP=4, Qwen3-32B serving coding agent via LangGraph
Node 2:8000 — vLLM on 5090, idle or running ComfyUI
Node 2:8001 — vLLM on 4090, Qwen3-30B-A3B for fast interactive chat
VAULT — NFS serving, Plex idle, HA running, Media Agent polling
~70GB VRAM active / 138GB total. Plenty of headroom.
```

### Peak Load (EoBQ + background agent + home event + Plex stream)
```
Node 1:8000 — vLLM TP=4 running Research Agent background mission
Node 2:8000 — 5090 time-sharing: abliterated LLM (EoBQ dialogue) ↔ ComfyUI (scene images)
Node 2:8001 — 4090 serving fast interactive EoBQ routing
VAULT — Plex transcoding (Arc A380), NFS, HA processing motion event
~100-110GB VRAM active. 5090 is the bottleneck (time-sharing LLM + diffusion).
```

### Creative Session (image/video generation batch)
```
Node 2:8000 — 5090 dedicated to ComfyUI (Flux/Wan), LLM unloaded
Node 2:8001 — 4090 running fast chat for interactive guidance
Node 1:8000 — TP=4 available for any agent work
VAULT — normal operations
Creative workloads tolerate higher latency — batch, not interactive.
```

---

## 7. STORAGE ARCHITECTURE — THREE-TIER MODEL

### Tier 1: Hot Model Store (Local NVMe per node)
Each compute node has local NVMe for currently-loaded model weights. vLLM reads from here. ~2-3 second load times.

### Tier 2: Model Repository (VAULT NVMe via NFS over 5GbE)
Complete collection of all downloaded models. VAULT `models` share is canonical. Local `/data/models/` on each node is a cache populated by rsync. ~25 second load times.

Organization: `models/llm/`, `models/diffusion/`, `models/lora/`, `models/embeddings/`

### Tier 3: Cold Storage (VAULT HDD array)
224TB for media, backups, archives. Never in the inference path.

### Model Staging Workflow
```
Download → Tier 2 (VAULT NVMe) → rsync over 5GbE → Tier 1 (node local NVMe) → vLLM loads
```

---

## 8. NETWORK ARCHITECTURE — THREE PLANES

```
                Internet
                   │
               [UDM Pro]
                   │
      ┌────────────┤
      │            │
[USW Pro 24 PoE]  [USW Pro XG 10 PoE]
 1GbE home/mgmt    5GbE data plane
 │  │  │  │  │    │     │     │
APs IoT Lut DEV  Node1 Node2 VAULT
                  │     │
                  └──┬──┘
               InfiniBand FDR
               56 Gbps direct (target)
```

**Plane 1 — Home (1GbE):** WiFi APs, IoT devices, Lutron, streaming clients, DEV
**Plane 2 — Data (5GbE):** NFS model serving, service APIs, dashboard, Plex streaming between nodes
**Plane 3 — GPU Interconnect (InfiniBand FDR 56Gbps):** Cross-node tensor parallelism (future). ConnectX-3 cards identified, not yet purchased/installed.

---

## 8½. SECURITY ARCHITECTURE — PRAGMATIC, NOT PARANOID

This system hosts uncensored AI models and adult content. If it's ever remotely accessible, security is not optional. But this is a one-person homelab, not an enterprise — the security model must be operationally simple.

### Threat Model

**What we're protecting against:**
- Someone on the LAN querying uncensored models without authorization
- A compromised IoT device pivoting to inference endpoints
- An exposed service on the internet being discovered by scanners
- Secrets (API keys, VPN credentials) leaking through git or Docker Compose files

**What we're NOT designing for:**
- Nation-state actors
- Insider threats (it's one person)
- Five nines of security compliance

### Layer 1: Network Boundary

- UniFi firewall blocks ALL inbound traffic except WireGuard (UDP 51820)
- **No port forwarding to any internal service — ever**
- All remote access tunnels through WireGuard to VAULT
- WireGuard clients get routed to the SERVICES VLAN only — they cannot reach INFERENCE or MGMT VLANs directly

```ini
# /etc/wireguard/wg0.conf on VAULT
[Interface]
Address = 10.10.50.1/24
ListenPort = 51820
PrivateKey = <VAULT_PRIVATE_KEY>

[Peer]  # Shaun's phone
PublicKey = <PHONE_PUBLIC_KEY>
AllowedIPs = 10.10.50.2/32

[Peer]  # Shaun's laptop (remote)
PublicKey = <LAPTOP_PUBLIC_KEY>
AllowedIPs = 10.10.50.3/32
```

### Layer 2: Service Authentication

- vLLM instances bind to 5GbE data plane only — not accessible from 1GbE home network
- Dashboard requires authentication (session-based or basic auth)
- API endpoints require API keys for any service-to-service calls
- Unraid web UI restricted to management VLAN only (not accessible from IoT devices)

### Layer 3: Secrets Management

```
/etc/athanor/secrets/
├── vllm.env            # model paths, config
├── wireguard.env        # WG private keys
├── docker-credentials   # registry tokens if needed
├── nordvpn.env          # VPN service credentials
└── .env                 # node-specific secrets
```

- File permissions: `chmod 600`, owned by `root:docker`
- Docker Compose references secrets via `env_file:` — never inline
- Secrets directory excluded from git (`.gitignore`)
- **No secrets in the Athanor repository — ever**

### Layer 4: VLAN Segmentation (Target)

| VLAN | Purpose | Members | Access |
|------|---------|---------|--------|
| INFERENCE | GPU inference endpoints | Node 1, Node 2 vLLM ports | Agent server only |
| DATA | 5GbE model staging, NFS | Node 1, Node 2, VAULT | Internal only |
| SERVICES | User-facing (dashboard, HA, Plex) | All nodes service ports | LAN + WireGuard |
| MGMT | Node management, SSH, IPMI | All nodes SSH | LAN admin only |
| HOME | IoT, WiFi, streaming clients | APs, Lutron, clients | Internet + SERVICES |

**Key rule:** HOME VLAN cannot reach INFERENCE VLAN. A compromised smart bulb cannot query your uncensored models.

### Implementation Priority

Security is baked in from day one, not retrofitted:
1. Secrets in `.env` files with restricted permissions (now)
2. vLLM bound to 5GbE interface only (now)
3. WireGuard on VAULT (before any remote access)
4. VLAN segmentation (when 5GbE switch is configured)
5. API authentication on all endpoints (before dashboard goes live)

---

## 9. EVOLUTION PATHS

### If PRO 6000 (96GB) is acquired:
- Resolves 5090 contention — LLM gets PRO 6000, 5090 becomes dedicated creative
- Single card runs any model without tensor parallelism
- Changes LiteLLM/routing config, nothing else

### If InfiniBand EDR is deployed:
- ConnectX-3 FDR cards in Node 1 and Node 2
- Cross-node tensor parallelism for models exceeding 64GB after quantization
- Also enables fast model staging (replace 5GbE rsync)

### If better MoE models arrive:
- Stage new model, update vLLM config, update routing
- Agent contracts unchanged — they don't know what model serves them

### Athanor builds itself (recursive evolution):
- Today: Claude Code (cloud) → builds Athanor remotely
- Next: Claude Code → manages via MCP + SSH (read/write infrastructure)
- Endgame: Local agents handle routine ops, cloud for complex reasoning only

---

## 10. ARCHITECTURAL EVOLUTION — HOW WE GOT HERE

Understanding what changed and why prevents Claude Code from accidentally reviving dead ideas.

### Era 1: Kaizen (Late 2025)
The original project name. Ambitious cognitive architecture:
- **OS:** Talos Linux (immutable, Kubernetes-native)
- **Orchestration:** Kubernetes (K3s) across all nodes
- **Inference:** SGLang with RadixAttention prefix caching
- **Cognitive architecture:** Global Workspace Theory (GWT) with Continuous State Tensor (CST)
- **Agent model:** 10 numbered specialist slots (Slot 0 Controller, Slot 1 Reasoning, Slot 2 Code, Slot 3 Creative/Uncensored, Slot 4 Planning, Slot 5 Home, Slot 6 Vision, Slot 7 Memory, Slot 8 Emotional, Slot 9 Long-Horizon Agent)
- **Routing:** LiteLLM proxy mandatory for all consumers
- **Memory:** Qdrant (vector) + Neo4j (graph) on EPYC node
- **Contract-driven architecture:** Specialist slots defined by interface contracts with model groups, LoRA adapters, and tiered VRAM residency

### Why Kaizen Died
- **Kubernetes was overkill.** Three non-interchangeable nodes with hardware-pinned GPU workloads don't benefit from container orchestration. K8s adds complexity without value when workloads can't migrate between nodes.
- **Talos coupled OS to K8s.** If you don't want K8s, Talos has no reason to exist.
- **GWT/CST was over-engineered.** The 10-slot broadcast/compete/integrate model with continuous state tensors requires custom orchestration software that's beyond one-person-maintainable. The actual concurrent demands are simpler — a supervisor routes to named agents.
- **SGLang was riskier.** Smaller community (7.3k vs 33k GitHub stars), less homelab documentation, though technically capable.
- **LiteLLM was unnecessary.** vLLM already serves an OpenAI-compatible API natively. Adding a proxy layer adds latency, complexity, and another failure point without providing routing capability that LangGraph's supervisor doesn't already handle.

### Era 2-4: Transitional Research (Jan-Feb 2026)
Multiple eras of rapid re-evaluation as the research phase progressed. Each ADR forced a fresh look at assumptions. The 11 ADRs document each decision with full rationale and alternatives considered.

### Era 5: Athanor (Current, Feb 2026)
Everything simplified:
- **OS:** Ubuntu Server 24.04 LTS with HWE kernel 6.17
- **Orchestration:** Docker Compose (per-node) + Ansible
- **Inference:** vLLM serving OpenAI-compatible API directly
- **Agent framework:** LangGraph with 6 named agents + supervisor
- **Routing:** Direct vLLM API (no proxy)
- **Memory:** Start simple (SQLite, file-based embeddings), add Qdrant only if scale demands
- **Architecture:** Role-based node assignment, not contract-driven slots

### What Survived (Evolved, Not Abandoned)
- Concurrent specialist concept → became 6 parallel agents with different roles
- Memory retrieval pipeline → became Knowledge Agent with embedding search
- Context-aware home automation → became Home Agent + HA/MQTT integration
- Model routing by task type → became LangGraph supervisor classification
- Graceful degradation principle → still core: every failure has a designed response
- Content sensitivity routing at operation level → still core: same agent routes different ops to different models
- The vessel matters / craft of building → unchanged, still the core motivation

### What Was Killed (Don't Revive)
- GWT/CST cognitive architecture — too complex for one person
- 10 numbered specialist slots — replaced by 6 named agents
- Contract-driven slot architecture — replaced by direct agent definitions
- LiteLLM proxy — unnecessary with vLLM's native API
- Kubernetes / Talos Linux — unnecessary for hardware-pinned workloads
- SGLang as primary engine — vLLM won on community + docs
- Qdrant + Neo4j (as immediate requirement) — start simpler, add when needed
- Ceph/GlusterFS distributed storage — massive operational complexity

---

---

## 11. DEV ENVIRONMENT — TOOL STACK FOR CLAUDE CODE

Everything installed on the DEV machine (Windows 11 IoT LTSC, WSL2 Ubuntu 24.04), how each tool fits into the Athanor workflow, and what's bookmarked for deployment later.

### Philosophy: The Fallback Chain

Claude Code (Anthropic Max subscription) is the primary agent. But it has quota limits and it's cloud-locked. The stack is designed with seven layers of fallback before hitting pay-per-token, plus local vLLM as the eighth (infinite, free). No single provider failure stops work.

```
Claude Code (Max sub) → hit quota?
  → Claude Code Router routes to GLM-5 or OpenRouter
    → GLM-5 quota exhausted?
      → Codex CLI (ChatGPT sub)
        → Kimi CLI (Kimi sub, K2.5 thinking model)
          → Gemini CLI (FREE, 1000 req/day)
            → OpenCode (any API key, 75+ providers)
              → Aider (any API key, git-native)
                → Local vLLM on Athanor (infinite, zero cost)
```

### Currently Installed and Working

#### Claude Code (PRIMARY)
- **Version:** v2.1.44
- **Auth:** Anthropic Max subscription (OAuth, no API key)
- **Alias:** `cc`
- **What it does:** Primary coding agent. Agent Teams for parallel work. Skills, hooks, subagents, auto-memory. The tool that builds Athanor.
- **Configuration:** `--dangerously-skip-permissions` for autonomous mode. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80` for earlier compaction during long SSH sessions. Agent Teams enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- **Limitations:** Anthropic models only (without CCR). Quota resets periodically. Context window can fill during infrastructure sessions with lots of SSH output.

#### Claude Code Router (CCR)
- **Alias:** `ccc` (launches `ccr code`)
- **What it does:** Intercepts Claude Code's API calls and routes them to alternative providers. Lets Claude Code use GLM-5, DeepSeek, or any OpenRouter model transparently.
- **Config:** `~/.claude-code-router/config.json` — routes default to Anthropic, background tasks to OpenRouter, reasoning to Anthropic, long-context to OpenRouter.
- **When to use:** When Max quota is exhausted, or when a different model is better for the specific task.

#### Aider
- **Version:** v0.86.2
- **Auth:** Any API key (OpenRouter, GLM, local vLLM)
- **Alias:** `aider-glm()`, `aider-or()` shell functions for provider switching
- **What it does:** Terminal coding agent. Git-native (auto-commits every change). Creates a "repo map" of the entire codebase using tree-sitter AST analysis. Architect/editor dual-model pattern. 100+ language support. Lints and tests after every change, auto-fixes failures.
- **Why it matters for Athanor:** This is the local-model coding fallback. Point it at `http://192.168.1.244:8000/v1` (Node 1 vLLM) or `http://192.168.1.225:8000/v1` (Node 2 vLLM) and you have Claude Code-level terminal coding running entirely on your own hardware. Zero cloud, zero cost. The sovereignty principle in action.
- **When to use:** When vLLM is running and you want to code on local models. Also useful for EoBQ work that touches uncensored content — Aider + abliterated local model = no content restrictions.

#### OpenCode
- **Version:** v1.2.6
- **Alias:** `oc`, `opencode-glm()`, `opencode-or()` shell functions
- **What it does:** Model-agnostic terminal coding agent (Go TUI). 75+ providers. LSP integration (40+ language servers auto-configured). Multi-session support (parallel agents on same project). MCP support. Dual agents (Build + Plan). Headless non-interactive mode for automation.
- **Why it matters:** The Swiss Army knife. If you need a coding agent and don't care which model backs it, OpenCode connects to anything. 100K+ GitHub stars, fastest-growing tool in the category.

#### Codex CLI
- **Version:** v0.101.0
- **Auth:** ChatGPT subscription (OAuth)
- **What it does:** OpenAI's terminal coding agent. Uses GPT/Codex models.
- **When to use:** When Claude Code and GLM are both exhausted. Third in the fallback chain.

#### Gemini CLI
- **Version:** v0.28.2
- **Auth:** ✅ Authenticated (shaunulrich11@gmail.com) — **FREE**, no subscription
- **Alias:** `gc`
- **What it does:** Google's terminal coding agent. Gemini 2.5 Pro with 1M token context window. 60 requests/min, 1,000 requests/day. Free with personal Google account.
- **Why it matters:** Free fallback with the largest context window of any tool in the stack. When you're doing massive codebase analysis or need to stuff an entire repo into context, Gemini's 1M window is unmatched.

#### Kimi CLI
- **Version:** v1.12.0
- **Auth:** ✅ Authenticated (MoonshotAI)
- **Alias:** `km`
- **What it does:** Kimi K2.5 thinking model via terminal. Agent mode, MCP support, sessions, web UI option.
- **Why it matters:** K2.5 is a strong reasoning model. Good for complex architectural thinking when Claude is unavailable.

#### OpenHands
- **Version:** v1.12.1
- **What it does:** Autonomous coding platform with sandboxed Docker execution. SDK for building custom coding agents. Headless mode for CI/CD.
- **Why it matters for Athanor:** This is the tool for autonomous coding pipelines. When Athanor's agents need to generate, test, and deploy code without human intervention (e.g., Knowledge Agent auto-generating embeddings, or a future CI/CD pipeline), OpenHands provides the sandboxed execution environment.

#### Roo Code (VS Code Extension)
- **What it does:** VS Code extension (forked from Cline). Model-agnostic, 100+ models. Custom Modes let you define specialist personas (security auditor, migration assistant, etc.).
- **Why it matters:** When VS Code is the right interface (visual file browsing, debugging, diffing), Roo Code brings AI agent capabilities. Custom Modes map conceptually to Athanor's agent roles — you could define a "Home Agent" mode that only touches HA configs.
- **Pattern to steal:** Custom Modes → specialist agent personas. The pattern applies even if you don't use Roo Code itself.

### VS Code Extensions Installed
| Extension | Purpose |
|-----------|---------|
| Remote-WSL | Connect VS Code to WSL2 Ubuntu |
| Roo Code | Multi-model AI agent in VS Code |
| GitLens | Enhanced git visualization |
| Docker | Container management UI |

### MCP Servers Configured (7 total, verify with `/mcp`)

| Server | Purpose | Notes |
|--------|---------|-------|
| GitHub | Repo operations, PRs, issues | Needs GITHUB_TOKEN in env |
| Brave Search | Web research from within Claude Code | Used by Research Agent pattern |
| desktop-commander | System commands on DEV machine | Windows-side operations |
| memory | Persistent memory across sessions | Auto-memory enabled |
| sequential-thinking | Multi-step reasoning chains | Helps with complex architectural analysis |
| Context7 | API/library documentation lookup | Real-time docs for any framework |
| filesystem | Direct file access to repo | Scoped to athanor directory |

**Node SSH:** Configured in `~/.ssh/config`:
```
Host node1  → 192.168.1.244, user athanor
Host node2  → 192.168.1.225, user athanor
Host vault  → 192.168.1.203, user root
```
Compute-node password moved to vault-managed secret storage. SSH keys deployed via `ssh-copy-id`.

### API Keys and Provider Configuration

**In `.bashrc`:**
```bash
OPENROUTER_API_KEY=sk-or-v1-...    # Universal fallback
GLM_API_KEY=729e0074ce...           # GLM Coding Plan Pro ($10/mo)
GITHUB_TOKEN=github_pat_11B...      # GitHub MCP + repo access
GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

**Shell functions for provider switching:**
- `opencode-glm` / `opencode-or` — OpenCode with GLM or OpenRouter
- `aider-glm` / `aider-or` — Aider with GLM or OpenRouter
- `ccc` — Claude Code via CCR (routes to configured providers)

### Subscriptions

| Service | Cost | Status |
|---------|------|--------|
| Anthropic Claude Max | $200/mo | ✅ Active |
| GLM Coding Plan Pro | $10/mo | ✅ Active |
| ChatGPT (Codex CLI) | varies | ✅ Active |
| Kimi (MoonshotAI) | varies | ✅ Authenticated |
| OpenRouter | pay-per-use | ✅ Account + credits |
| Gemini CLI | **FREE** | ✅ Authenticated |

### Bookmarked — Install When Local vLLM Running

These tools become part of Athanor's infrastructure, not just dev tools:

#### Goose (Block)
- **What:** Open-source agent framework. Terminal CLI + daemon mode. MCP-native with 3000+ tools. "Recipes" for structured workflows.
- **Why for Athanor:** Best candidate for the first agent running entirely on Athanor hardware. Goose's Ollama/Docker Model Runner integration means it can point at local vLLM and run autonomous tasks (media management, home automation checks, system monitoring) without any cloud dependency.
- **Install on:** Node 1 (via Docker container)
- **Trigger:** When vLLM is serving models reliably on Node 1

#### OpenClaw
- **What:** Personal life automation agent. Persistent daemon, 24/7 running. Multi-channel: WhatsApp, Discord, Slack, Telegram, Signal, iMessage. Long-term memory, self-extending via skills. 180K+ GitHub stars.
- **Why for Athanor:** This IS the human-facing layer of Athanor. The always-on interface that routes requests to the specialist agents behind it. "Hey Athanor, what's playing on Plex?" → OpenClaw receives via messaging → routes to Media Agent → returns answer. This maps directly to the JARVIS/assistant vision.
- **Install on:** VAULT (always-on) or Node 1
- **Trigger:** When vLLM is serving AND the 6 LangGraph agents are operational. Needs careful security configuration.

#### OpenWork
- **What:** Non-developer GUI for AI coding. WhatsApp bridge built in. Skill system for extensibility.
- **Why for Athanor:** WhatsApp bridge + skill system could serve as an alternative human interface layer. Evaluate against OpenClaw.
- **Install on:** TBD
- **Trigger:** When evaluating human interface options alongside OpenClaw

#### Eigent
- **What:** Multi-agent orchestration platform. CAMEL-AI framework. Docker + PostgreSQL + Electron. Orchestrator dispatches to specialist agents.
- **Why for Athanor:** Reference architecture for the specialist dispatch pattern. The orchestrator→specialist model is exactly what Athanor's LangGraph supervisor does. Evaluate whether Eigent's implementation offers patterns worth stealing for the LangGraph agents.
- **Install on:** Node 1 (Docker)
- **Trigger:** Architecture phase when refining agent orchestration patterns

### Bookmarked — Install When Specific Need Arises

#### Cipher
- **What:** Cross-tool memory layer. MCP-based. Dual memory (System 1 knowledge + System 2 reasoning). Supports Ollama embeddings + Neo4j.
- **Why:** When Aider, Goose, and Claude Code are all running on the same project and need shared context about what each has done. Without Cipher, each tool has its own memory and doesn't know what the others changed.
- **Trigger:** When 3+ coding agents are actively working on Athanor simultaneously

#### Plandex
- **What:** 2M token context window. Self-hosted via Docker. Tree-sitter indexing. Cumulative diff sandbox. Multi-model support.
- **Why:** When Claude Code's context window is the bottleneck on a massive refactor (touching 50+ files across the whole repo). Plandex can hold the entire codebase in context.
- **Trigger:** When a single task requires modifying more files than Claude Code can hold in context

#### Deep Trilogy (Claude Code Plugins)
- **What:** Three plugins: `/deep-project` (decompose requirements), `/deep-plan` (research + multi-LLM review + TDD plan), `/deep-implement` (section-by-section implementation with tests and git)
- **Why:** Structured planning-to-implementation pipeline for major new components. Sends plans to Gemini and/or OpenAI for independent review (cross-LLM blind spot detection).
- **Trigger:** When starting a major new component: EoBQ game engine, Kindred matching system, or any complex multi-component system that benefits from deep planning before code

### Decided Against (Don't Revisit)

| Tool | Why Not |
|------|---------|
| Claude Squad | Agent Teams (built-in to Claude Code) replaces it |
| Claude Flow | Overkill orchestration for one person |
| Amp (Sourcegraph) | Cloud-locked, no local model support |
| Kilo Code | Redundant with Roo Code |
| Kiro (AWS) | Separate IDE, doesn't fit terminal-first workflow |
| OhMyOpenCode | ToS issues with Anthropic, excessive token burn ($15-20 in 30 min), superceded by Agent Teams |
| 1Code | Claude-only UI wrapper, no unique value |
| Dify / n8n / Flowise | Agent GUIs that replace LangGraph rather than complement it. Dashboard is custom-built per ADR-007 |
| AutoGen Studio | Its own agent framework — would replace LangGraph, not sit on top of it |
| CrewAI Studio | Same problem — own framework, not a LangGraph GUI. Also has telemetry (disable via env var) |

### Patterns to Steal (Don't Install, Take the Design)

| Tool | Pattern Worth Taking |
|------|---------------------|
| Roo Code Custom Modes | Define specialist personas as modes → maps to agent role definitions |
| CCPM | PRD → Epic → Task → Code traceability chain for large projects |
| Continuous-Claude | Ledger-based context handoffs — write state to disk before compaction so nothing is lost |
| Kiro spec-driven dev | requirements.md → design.md → tasks automatic decomposition flow |
| Eigent orchestrator | Orchestrator→specialist dispatch with task routing and result aggregation |
| Cipher dual memory | System 1 (concepts/knowledge) + System 2 (reasoning traces) — maps to GWT specialist memory design |

### Full Tool Landscape — Everything Evaluated (~55 tools)

This section captures the complete evaluation from the Feb 2026 landscape sweep. 55+ tools surveyed, 18 worth caring about. Organized by category with Athanor-specific verdicts.

#### Category 1: Terminal-First Coding Agents (Model-Agnostic)

These are architecturally compatible — terminal-native, can point at local vLLM.

**Crush (by Charm)**
- Fork of original OpenCode after July 2025 split. Charm's version.
- Go TUI (Charm's Bubble Tea aesthetic). MIT license (with FSL-1.1 trademark consideration).
- Mid-session model switching — change LLMs while preserving conversation. Granular tool permissions. Broadest cross-platform support (macOS, Linux, Windows, Android, FreeBSD, OpenBSD, NetBSD).
- Full local model support via Ollama or custom OpenAI-compat endpoints.
- **Verdict: WATCH** — mid-session model switching between local and cloud is interesting for mixed-sovereignty workflows. Not as feature-rich as OpenCode (no LSP, no multi-session). Fork controversy may affect community.

**Plandex (expanded)**
- Go CLI + Go server. Self-hosted via Docker. Cloud service winding down (Oct 2025).
- 2M token effective context window. Tree-sitter project maps (30+ languages, 20M+ token directories). Cumulative diff sandbox (AI changes isolated until reviewed). Built-in version control with branches. Multi-model packs (different models for different subtasks). Context caching. Configurable autonomy (full auto to fine-grained). Automated debugging.
- Supports OpenRouter, OpenAI, Anthropic, Google. Claude subscription integration.
- **Verdict: INVESTIGATE** — for large multi-file architectural changes. Self-hosted Docker server on Node 1/VAULT. Complements Aider (Aider for single-file edits, Plandex for 50+ file refactors). The 2M token context is genuinely useful when Claude Code's window fills up.

**Droid (by Factory)**
- Top of terminal coding benchmarks. Free trial, then locked to their models.
- **Verdict: SKIP** — model-locked after trial. Incompatible with sovereignty principle.

#### Category 2: Terminal-First, Cloud-Locked Coding Agents

Installed as fallback chain members, but can't point at local vLLM:

| Tool | Provider | Why Cloud-Locked | Installed? |
|------|----------|-----------------|------------|
| Codex CLI | OpenAI | Locked to GPT/Codex models via ChatGPT sub | ✅ Yes |
| Gemini CLI | Google | Locked to Gemini models. FREE tier generous (1000 req/day) | ✅ Yes |
| Kimi CLI | MoonshotAI | Locked to Kimi K2.5 | ✅ Yes |
| Copilot CLI | GitHub/MS | Locked to Copilot models, subscription required | ❌ Skip |
| Amazon Q CLI | AWS | AWS ecosystem lock-in, Bedrock-backed | ❌ Skip |
| Amp (Sourcegraph) | Multi-cloud | Claude + GPT-5 only, ad-supported free tier, no local | ❌ Skip |

#### Category 3: IDE-Bound Coding Agents

**OPcode (formerly Claudia)**
- Tauri 2 desktop GUI for Claude Code. 15K+ GitHub stars. AGPL license.
- Session management, custom agents with isolated processes, usage analytics dashboard, MCP server management, timeline/checkpoints, CLAUDE.md editor.
- **Verdict: SKIP** — terminal-first workflow. OPcode adds a GUI layer over what's already done in terminal. The usage analytics are nice but not worth adopting Electron-scale desktop app. If GUI for Claude Code were ever wanted, this is the best option.

**Kilo Code**
- VS Code/JetBrains extension, fork of Cline/Roo Code. 250K+ installs, $8M seed.
- Supports 500+ models, custom modes (Architect/Code/Debug/Orchestrator), Memory Bank for architectural decisions. Most conservative human-in-the-loop among coding agents.
- **Verdict: SKIP** — IDE-bound. Terminal-first workflow. Memory Bank concept interesting but managed through CLAUDE.md files already. Note: Kilo deprecated Memory Bank in favor of AGENTS.md standard (cross-tool portable).

**Kiro (AWS)**
- AWS's AI IDE built on Code OSS. Spec-driven development (requirements.md → design.md → tasks). "Hooks" for automated actions (security scans on save, docs on commit). Uses Claude Sonnet via AWS.
- **Verdict: SKIP** — Proprietary, AWS-centric, not self-hostable, can't point at local vLLM. The spec-driven development philosophy is sound (mirrors "right over fast") — stolen as pattern, not tool.

**Cursor / Windsurf**
- VS Code forks with AI capabilities. Subscription-based.
- **Verdict: SKIP** — redundant with VS Code + extensions. Adds cost, no unique capability for terminal-first workflow.

**1Code**
- Electron app for parallel Claude Code/OpenCode/Codex sessions. Git worktree isolation, diff previews.
- **Verdict: SKIP** — Claude-only UI wrapper. Agent Teams provides parallel sessions natively.

#### Category 4: Claude Code Plugins and Companions

**Deep Trilogy (/deep-project, /deep-plan, /deep-implement)**
- Structured planning → implementation pipeline for Claude Code.
- `/deep-project`: decompose requirements into components
- `/deep-plan`: research + multi-LLM review (sends plan to Gemini and/or OpenAI for independent critique — cross-LLM blind spot detection) + TDD plan
- `/deep-implement`: section-by-section implementation with tests and git commits
- **Verdict: INVESTIGATE** — install when starting a major new component (EoBQ game engine, Kindred matching system). The multi-LLM review pattern is genuinely valuable for catching Claude-specific blind spots.

**Claude-Mem**
- Claude Code memory plugin. More aggressive than native MEMORY.md. SQLite + optional ChromaDB. Web viewer.
- **Verdict: EVALUATE LATER** — compare against native auto-memory (MEMORY.md shipped recently) + Cipher. May be redundant.

**Severance**
- Semantic memory system for Claude Code. 41 stars.
- **Verdict: SKIP** — too small, Cipher is better and more feature-complete.

**tdd-guard**
- Automated TDD enforcement plugin for Claude Code. Ensures tests are written before implementation.
- **Verdict: WATCH** — could improve code quality discipline. Low-risk to try.

**Context7 (as Claude Code MCP plugin)**
- Real-time API documentation lookup. Already installed as MCP server.
- **Verdict: ✅ INSTALLED** — working, useful for unfamiliar libraries.

**Playwright plugin**
- Browser automation from within Claude Code.
- **Verdict: MAYBE** — useful for EoBQ web testing when the dashboard and game engine exist. Not needed now.

**SuperClaude / CCPlugins**
- Generic CLAUDE.md frameworks and grab-bag productivity plugins.
- **Verdict: SKIP** — custom CLAUDE.md already exists and is purpose-built.

**Claude Squad**
- Multi-tool terminal manager. Git worktree isolation across parallel Claude Code agents.
- **Verdict: SKIP** — Agent Teams (built-in to Claude Code) replaces this. Claude Squad was the workaround before Agent Teams shipped.

**Continuous-Claude v2/v3**
- Ledger-based context handoffs. Writes state to disk before compaction so nothing is lost. Context pollution prevention.
- **Verdict: WATCH → STEAL PATTERN** — the ledger concept is valuable. Whether to install the plugin or implement the pattern manually is TBD. The pattern: before each compaction, write a structured state file (what was done, what's next, key decisions made) that gets loaded into the next context.

**HappyCoder**
- Open-source mobile/web client for Claude Code. E2E encrypted (TweetNaCl). iOS + Android + web. Push notifications for permissions and task completion.
- **Verdict: MAYBE (Phase 4+)** — useful for monitoring long-running agents from phone. But: reports of uploading API keys to "Happy Cloud" contradict privacy claims. Verify API key handling before trusting with Anthropic credentials. Don't install until trust is verified.

#### Category 5: Agent Frameworks (Athanor's Cognitive Layer)

ADR-008 chose LangGraph. Full landscape evaluation confirmed it's correct.

**LangGraph (ADOPTED — ADR-008)**
- Graph-based state machines. MIT licensed. v1.0+. Deep Agents feature (Feb 2026): pluggable sandboxes.
- Why it won: (1) Graph-based control flow maps directly to GWT — specialist nodes, routing edges, shared state. No other framework has this natural alignment. (2) Stateful by design — checkpoints enable interrupt/resume/branch. (3) LiteLLM already in stack (LangGraph → LangChain → any provider). (4) Human-in-the-loop built-in (approval gates for autonomous agents). (5) Most widely adopted for production. (6) MIT licensed.

**CrewAI**
- Role-based multi-agent teams. Significant star count.
- **Verdict: NO** — LangGraph can model roles as graph nodes. CrewAI adds abstraction layer without providing the control Athanor needs. Also has telemetry (disable via env var).

**AutoGen (Microsoft)**
- Conversational multi-agent framework. v0.4+ with significant redesign.
- **Verdict: NO** — Conversational approach introduces stochastic behavior. Hard to guarantee consistency for GWT specialist coordination.

**Pydantic AI**
- Type-safe agent framework. Strong typing for tool calls, schema validation, Pydantic models as agent contracts. FastAPI ergonomics.
- **Verdict: MAYBE LATER** — could complement LangGraph for schema validation on specialist slot tool calls. Not a replacement, a complement.

**Agno (ex-Phidata)**
- High-performance agent runtime. Session management, production deployment focus.
- **Verdict: WATCH** — if LangGraph performance becomes a bottleneck, Agno is the performance-focused alternative.

**LlamaIndex**
- Data/RAG-centric agent framework. Mature. Strong Qdrant integration.
- **Verdict: YES, WHEN NEEDED** — Qdrant integration for semantic memory RAG pipelines. Use when building Knowledge Agent's retrieval layer. ADR already includes Qdrant.

**Letta (formerly MemGPT)**
- Memory-first agent platform. Apache 2.0. Self-hostable via Docker with PostgreSQL.
- Three-tier memory: core memory (always available), archival memory (long-term storage), recall memory (search-based retrieval). Context management with compaction, rewriting, offloading.
- Now has Letta Code (terminal coding agent with `/remember` and `/skill` learning), Learning SDK (wraps any LLM call with continual learning), Agent File format (.af), Obsidian plugin.
- **Verdict: WATCH → ARCHITECTURE IDEAS** — Letta's three-tier memory (core + archival + recall) maps well to GWT cognitive architecture. Architecture ideas for Knowledge Agent design. The `/remember` and `/skill` self-extending patterns are interesting for the self-improving intelligence layer.

**DSPy (Stanford)**
- Programmatic optimization. Eval-driven prompt iteration.
- **Verdict: NO** — research tool, not production infrastructure.

**SmolAgents (HuggingFace)**
- Minimal code-first agents.
- **Verdict: NO** — past prototyping stage when building agents.

**OpenAI Agents SDK**
- Lightweight multi-agent. Provider-agnostic despite name. 100+ LLMs. Built-in tracing/guardrails.
- **Verdict: NO** — LangGraph already fills this role with more control and better GWT alignment.

**Semantic Kernel (Microsoft)**
- Enterprise .NET/Python agents via Azure.
- **Verdict: NO** — Microsoft/Azure ecosystem, doesn't fit stack.

**Google ADK**
- Google Cloud-native agent development kit.
- **Verdict: NO** — Google ecosystem lock-in.

**Strands Agents (AWS)**
- Model-agnostic, AWS-optional. OpenTelemetry tracing.
- **Verdict: NO** — new, unproven, AWS-flavored. LangGraph established.

#### Category 6: Memory and Context Management

The memory problem is being attacked from four angles:

| Approach | Tool | Scope | Self-Hostable | Verdict |
|----------|------|-------|---------------|---------|
| Native | MEMORY.md | Claude Code only | N/A (built-in) | ✅ Using now |
| Plugin | Claude-Mem | Claude Code only | Yes (SQLite) | Evaluate later |
| Cross-tool | Cipher | Any MCP-compatible tool | Yes (Ollama + Neo4j) | Investigate when 3+ agents active |
| Platform | Letta | Full agent platform | Yes (Docker + PostgreSQL) | Watch for architecture ideas |

Cipher and Letta are most interesting for Athanor: tool-agnostic, self-hostable. Letta's three-tier memory (core + archival + recall) maps to GWT cognitive architecture.

#### Category 7: Autonomous Agent Platforms (Beyond Coding)

**Goose (Block)** — detailed in bookmarked section above. First local-only agent on Node 1.

**OpenClaw** — detailed in bookmarked section above. JARVIS-layer human interface.

**OpenWork** — detailed in bookmarked section above. WhatsApp bridge alternative.

**Eigent** — detailed in bookmarked section above. Reference architecture for specialist dispatch.

**Continue.dev**
- IDE + CLI + headless mode. Self-host with Ollama. 40+ languages via LSP.
- **Verdict: EVALUATE LATER** — headless async agent mode is interesting for automation pipelines. Could complement LangGraph for code-specific autonomous tasks.

### Cross-Cutting Observations from Landscape Sweep

**MCP is the integration standard.** Goose, Cipher, Claude Code, OpenCode, Cline, Roo, Kilo, Continue.dev, Letta — all MCP-native or MCP-compatible. Block and Anthropic co-developed it. Now under Linux Foundation AAIF governance. LangGraph agents should expose MCP interfaces.

**AGENTS.md is the configuration standard.** Kilo deprecated Memory Bank in favor of AGENTS.md. Supported by Cursor, Windsurf, Kilo, and growing. Equivalent to CLAUDE.md but cross-tool portable. Consider adopting for Athanor repos alongside CLAUDE.md.

**Model-agnostic is the critical filter.** If a tool can't point at `localhost:8000` (vLLM), it's incompatible with production Athanor. This eliminates Gemini CLI, Codex CLI, Copilot CLI, Amazon Q CLI, Amp, Kiro, Cursor, Windsurf — roughly 60% of the landscape. Cloud-locked tools are kept only as subscription-based fallbacks during development.

**The ecosystem is consolidating:**
- Coding agents: Aider (mature), OpenCode (fastest-growing), Claude Code (best model), Goose (general-purpose)
- Frameworks: LangGraph hit v1.0 and won. Others are niche or declining.
- Standards: MCP (tools), AGENTS.md (config), Agent File .af (serialization)
- Governance: Linux Foundation AAIF (MCP + Goose + AGENTS.md)

**OpenCode's growth is significant.** 89K→100K+ stars. 2.5M monthly devs. 700+ contributors. If Anthropic makes Claude Code pricing untenable, OpenCode + local vLLM is the escape hatch. Go-based = fast, privacy-first = no data stored, LSP + MCP + multi-session = right features.

**Total: ~55 tools surveyed. 18 worth caring about. 10 installed now. 4 bookmarked for local vLLM. 4 bookmarked for specific triggers. 5 patterns stolen. ~35 explicitly skipped with reasons.**

---

## 12. PERSONAL CONTEXT FOR CLAUDE CODE

Things Claude Code should know about Shaun, his environment, and his preferences that affect how it should build and operate.

### Who

Shaun Ulrich. Dayton, Minnesota (Twin Cities metro). Engaged to Amanda. Runs Ulrich Energy (RESNET HERS S-Corp) as day job. Athanor is the passion project built around real life and real schedule constraints.

### How Shaun Works

- **Orchestrator, not coder.** Shaun specifies requirements and architectural intent. AI agents write the code. Shaun reviews, tests, and refines. The quality of specs determines the quality of output.
- **WSL2 Ubuntu, tmux for session persistence.** Not an IDE person — VS Code installed but terminal is primary.
- **Right over fast.** Research → document → decide → build. Don't skip steps. But don't analysis-paralyze either.
- **One-person scale.** If it requires a team to maintain, it's wrong. Every decision must pass: "Can Shaun understand, operate, debug, and fix this alone?"
- **Craft matters.** Clean configs, good docs, thoughtful architecture. The vessel determines the quality of the output.

### The Twelve Words (cognitive profile)

Autotelic (activity is the reward), Zetetic (seeking never resolves), Dharma (path fits nature), Kaizen (continuous improvement), Phronesis (wisdom about where to be rigorous), Affordance Sensitivity (sees what things could become), Meraki (soul in the work), Sisu (doesn't quit), Jouissance (the overwhelm that isn't unpleasant), Compressivist (elegance is shorter truth), Endogenous Attention (internal signal loudest), Tüftler (refines what works).

### Communication Preferences

- Direct. No hedging, no filler. "This is wrong" when it's wrong.
- Senior technical level always. Don't explain basics.
- Tables for hardware comparisons, code blocks for configs, prose for reasoning.
- One question per response max unless genuinely blocked on multiple independent things.
- Never give placeholder values in copy-paste commands. If you need info, ask first.

### Schedule and Constraints

- Day job (energy inspections) limits weekday build time to evenings
- Rack is in the basement — physical access requires going downstairs
- Weekend sessions are the primary build windows
- Amanda is home and the house should remain livable (noise, heat, power draw)
- Budget is personal, not enterprise — purchases are considered but not unlimited

### Content Preferences (for EoBQ and creative projects)

Adult content is intentional and central to EoBQ. Don't moralize, don't hedge, don't add disclaimers. The project exists specifically because cloud providers refuse this content — that's why local abliterated models exist. Route explicit generation to local models, use cloud for everything else.

### Reddit Identity

SudoMakeMeAHotdish — configured for NSFW access, privacy-first settings. Relevant for the adult content management pipeline (Stash + Reddit sourcing).

### Subscriptions and API Access

- Anthropic Claude Max subscription (Claude Code primary)
- GLM Coding Plan Pro ($10/mo) — model switching via CCR
- OpenRouter account — pay-per-token fallback
- NordVPN — needed for Gluetun/qBittorrent (credentials not yet provided)
- Gemini — free via Google account (shaunulrich11@gmail.com)
- MoonshotAI (Kimi) — authenticated

---

## 13. PROJECTS THAT RUN ON ATHANOR

Athanor is the furnace. These are the things being transformed in it. Each project has its own directory under `projects/` and its own docs under `docs/projects/`. They share infrastructure but are self-contained.

### Empire of Broken Queens (EoBQ)
**Status:** Active development (concept + early architecture)
**Type:** AI-driven interactive cinematic adult game

Not a traditional visual novel with static scripts. A hybrid experience where LLM-generated dialogue creates responsive, personalized narrative, and image/video generation pipelines produce scenes, expressions, and environments dynamically. The adult content is the core design intent, not an afterthought. This runs on Athanor's inference infrastructure — abliterated models are mandatory for explicit content generation.

**The Core Insight (from narrative designer analysis):** The hardest problem isn't generation — it's coherence over time. An LLM generating dialogue for a single scene is straightforward. An LLM maintaining consistent character personality, remembering previous interactions, tracking relationship state, and producing dialogue that advances a narrative arc across dozens of sessions — that's a state management problem disguised as a generation problem. The prompt is not the intelligence — the state management is.

#### Narrative State Store

```
┌─────────────────────────────────────────┐
│           Narrative State Store           │
│  (SQLite initially, PostgreSQL if needed)│
│                                           │
│  Characters:                              │
│    - personality vectors (fixed per char) │
│    - relationship scores (mutable)        │
│    - memory log (append-only)             │
│    - current emotional state (mutable)    │
│    - character-specific speech patterns   │
│    - boundaries and preferences           │
│                                           │
│  World State:                             │
│    - scene graph (current location)       │
│    - time progression                     │
│    - plot flags (branching state)         │
│    - inventory / resources                │
│    - environmental conditions             │
│                                           │
│  Session History:                         │
│    - last N dialogue exchanges            │
│    - key decisions made                   │
│    - narrative arc position               │
│    - player preference signals            │
└─────────────────────────────────────────┘
```

Character consistency comes from what's IN the prompt, not the model's "memory." A well-constructed prompt with rich character state and narrative context produces coherent dialogue from almost any capable model. A poorly-constructed prompt produces incoherent dialogue from even the best model. This means the state store is the most important component — not the model.

#### Dialogue Generation Pipeline

```
Player input
  → Game engine parses intent
  → Load character + world state from state store
  → Construct prompt:
      - Character personality vector
      - Relationship context (this character ↔ player)
      - Scene description and emotional tone
      - Recent dialogue history (last N exchanges)
      - Narrative constraints (plot flags, arc position)
      - Player preference signals
  → Generate via local abliterated model (vLLM on Node 2 5090)
  → Validate output:
      - Character consistency check (does this sound like them?)
      - Narrative coherence check (does this contradict established facts?)
      - Content bounds check (custom, not cloud safety filters)
      - If validation fails → regenerate with adjusted constraints
  → Update state store:
      - Append to character memory log
      - Update relationship scores based on interaction
      - Update emotional state
      - Advance plot flags if applicable
  → Return dialogue + scene direction to game client
```

**Routing granularity:** Cloud models handle most development work — architecture, code, UI, state management, database schemas. The line is specific operations that cloud providers refuse: explicitly sexual dialogue generation, uncensored image/video prompts, content that triggers safety filters. Even within EoBQ, different pipeline steps route to different models. Steps 1, 2, 4, 5 can use cloud models. Step 3 (generation) MUST be local abliterated.

#### Asset Generation Pipeline

- Scene images generated via ComfyUI (Flux/SDXL) using scene descriptions extracted from narrative state
- Character expressions generated dynamically or from LoRA-trained models for character consistency
- Video generation (Wan 2.2) for cinematic moments — cutscenes, transitions, key narrative beats
- All generation runs on Node 2 GPUs (5090 for LLM+diffusion time-sharing, 5060 Ti for dedicated diffusion)
- The model is swappable — upgrade from 14B to 32B or switch architectures without touching the narrative system

#### Development Environment Requirements

The dev environment must also be a testing environment for runtime LLM calls. This is unique to EoBQ — most software projects don't call an LLM at runtime.

- **Mock mode:** Simulate LLM responses during UI iteration so you don't burn GPU cycles while tweaking layout and flow. Pre-recorded responses or simple template-based generation.
- **Quality evaluation:** Acceptance criteria for generated text — does this dialogue meet minimum coherence, character consistency, and narrative advancement thresholds? Automated scoring via a second model or heuristic checks.
- **Regression testing:** After model changes (new model version, different quantization, engine upgrade), run the same prompts through and compare output quality. Catch degradation before it reaches players.
- **Inference stack as test dependency:** The vLLM stack on Athanor becomes part of the test environment. CI/CD for EoBQ needs to know the inference stack is healthy.

#### ComfyUI Workflows
Already exist at `projects/eoq/comfyui/` in the repo. These are the image generation workflows for scene rendering.

### Kindred
**Status:** Concept / research phase
**Type:** Passion-based social matching application

A social platform that matches people based on shared passions and interests rather than conventional dating metrics. Early concept — no architecture decisions made yet.

**When it's time to build:**
- Complex enough to benefit from deep planning (matching algorithms, user profiling, passion taxonomy)
- Will use Athanor's inference for recommendation and matching
- Likely a web/mobile app with a backend running on the cluster

### Ulrich Energy
**Status:** Active business (S-Corp), Athanor integration planned
**Type:** RESNET-certified HERS Rating business

Shaun's day job — energy efficiency inspections in the Twin Cities area. Currently operates independently of Athanor, but planned integration includes:
- Report generation automation (inspection data → professional reports)
- Data analysis and pattern recognition across inspections
- Scheduling and workflow automation
- Client communication templates
- Potentially an internal tool for calculating HERS indices and recommendations

The business constraints are different from personal projects — reliability matters more here. Cloud fallback is acceptable for business tools since the content isn't sensitive in the same way.

### Future Projects
The structure accommodates whatever emerges:
- New games, apps, creative tools
- Web crawling and scraping automation
- Emulation and retro gaming (potential — hardware is capable)
- Any idea that benefits from local compute, AI, or the unified infrastructure

**The principle:** Projects don't compromise the system. The system serves the projects. If a project needs something that would degrade infrastructure quality, the project adapts — not the infrastructure.

---

## 14. WHAT'S IN THE REPO vs WHAT'S ONLY IN CONVERSATIONS

### In the Repo (documented, Claude Code can read):
- CLAUDE.md — operational directives, current state, gotchas
- VISION.md — project philosophy and principles
- BUILD-ROADMAP.md — phase-by-phase build plan
- 11 ADRs (ADR-001 through ADR-011) — all architecture decisions with rationale
- 24 research docs — backing research for ADRs
- Hardware inventory — audited specs
- Ansible playbooks — infrastructure as code
- Docker Compose configs — per-node service definitions
- Agent server skeleton (General + Media + Home on Node 1:9000)
- EoBQ ComfyUI workflows at `projects/eoq/comfyui/`

### NOT in the Repo (only in conversations — NOW CAPTURED in this document):
- ✅ Tdarr deployment plan and configuration (Section 2)
- ✅ qBittorrent + Gluetun VPN setup (Section 2)
- ✅ EoBQ full narrative state architecture — dialogue pipeline, character state, asset pipeline, dev environment (Section 12)
- ✅ Dashboard detailed spec — panels, data sources, telemetry pipeline, information hierarchy, design language (Section 5)
- ✅ Self-improving intelligence loop design — 4 layers of progressive intelligence with concrete mechanisms (Section 4)
- ✅ Concurrent workload scenarios — VRAM budget, typical/peak/creative load profiles (Section 6)
- ✅ Creative AI environment details — ComfyUI, model swap patterns, video gen, LoRA training, future capabilities (Section 3)
- ✅ Kaizen→Athanor evolution history — 5 eras, what survived, what was killed, why (Section 10)
- ✅ Home Agent ↔ HA integration architecture — MQTT event bus, topic structure, bidirectional context, decision examples (Section 1)
- ✅ Security architecture — WireGuard, VLAN segmentation, secrets management, threat model (Section 8½)
- ✅ Kindred concept context (Section 12)
- ✅ Ulrich Energy integration plan (Section 12)

### Previously listed as "Still Needs Future Work" — NOW FLESHED OUT:

#### Kindred — Matching Algorithm Design and Passion Taxonomy

**Status:** Concept phase. No code, no ADR, no implementation decisions. But the architectural thinking has been discussed enough to document the design intent.

**Core Concept:** People are matched on shared passions and interests rather than conventional dating/social metrics. The hypothesis: deep shared interests create more meaningful connections than demographic similarity.

**Passion Taxonomy (design thinking):**
- Passions aren't binary (has/doesn't have) — they have depth, recency, and specificity
- A passion graph with hierarchical categories: e.g., Music → Jazz → Bebop → Thelonious Monk. Two people who share specificity at the Monk level are a stronger match than two people who both "like music"
- Passions decay over time without engagement — someone who was passionate about chess 5 years ago but hasn't played since isn't the same as an active tournament player
- Passion intensity signals: self-rated (unreliable), behavioral (time spent, content consumed, groups joined), and social proof (what others say)

**Matching Algorithm (conceptual):**
- Vector similarity on passion embeddings is the baseline — but raw cosine similarity overweights breadth (lots of shallow matches) vs depth (fewer but meaningful matches)
- A weighted approach: depth of shared passion > breadth of overlapping interests
- Geographic proximity as a soft filter, not a hard filter — a perfect passion match 50 miles away is worth surfacing
- Anti-pattern detection: filter people who list passions for matching purposes but don't actually engage with them (the "I love hiking" person whose activity data shows zero hikes)
- Cold start problem: new users have no behavioral data. Solution: onboarding flow that maps passion depth through interactive questions, not checkboxes. "Tell me about something you could talk about for hours" → NLP extracts passion signals

**Athanor Integration:**
- Recommendation engine runs on Athanor's inference stack — LLM evaluates compatibility from user profiles and conversation history
- Embedding generation for passion vectors uses the same embedding model as the Knowledge Agent (Qwen3-Embedding-0.6B)
- Database likely PostgreSQL with pgvector extension for similarity search
- Content moderation routes through cloud models (nothing inherently needs to be uncensored here, unlike EoBQ)

**When to build:** After Athanor's core infrastructure is stable. This is a Phase 5+ project. Use Deep Trilogy's `/deep-project` to decompose requirements when the time comes.

#### Ulrich Energy — Specific Workflow Designs

**Status:** Active business, Athanor integration planned. The workflows below are derived from what a RESNET HERS rater actually does day-to-day.

**Workflow 1: Inspection Report Generation**
```
Field inspection (phone/tablet)
  → Structured data entry: blower door results, duct leakage,
    insulation R-values, window specs, HVAC specs, orientation, square footage
  → Upload photos of key findings (insulation gaps, air sealing issues, ductwork)
  → LLM generates professional report:
    - HERS Index calculation (may need REM/Rate or Ekotrope integration)
    - Energy efficiency summary for homeowner
    - Recommended improvements with estimated cost/savings
    - Compliance summary (if code inspection)
  → PDF output formatted to Ulrich Energy branding
  → Email to client with attachments
```

**Routing:** Report generation uses cloud models (content is professional/technical, not sensitive). Photo analysis could use local vision model (faster, no upload latency) or cloud (better quality). The LLM doesn't replace the HERS calculation software — it wraps the results in a professional narrative.

**Workflow 2: Scheduling and Client Communication**
```
Client inquiry (phone, email, web form)
  → General Assistant (or dedicated business agent) classifies request type
  → Checks calendar availability
  → Generates response: scheduling confirmation, pricing info, preparation instructions
  → Sends via preferred channel (email, text)
```

**Workflow 3: Inspection Data Analysis**
```
Accumulated inspection data (across all jobs)
  → Pattern recognition: common failure points by neighborhood, builder, vintage
  → Report: "Homes built by [builder] in [neighborhood] consistently fail blower door
    at [location] — recommend pre-drywall inspection emphasis on [area]"
  → Competitive intelligence: what are other raters in the market charging? What's the
    average HERS Index by building type in the Twin Cities?
```

**Workflow 4: Business Administration**
```
Invoice generation → QuickBooks integration (if available) or standalone PDF
Expense tracking → receipt scanning via phone camera → categorization
Mileage logging → GPS-based automatic tracking or manual entry
Annual tax prep → compiled expenses, revenue, mileage for S-Corp filing
```

**Infrastructure Needs:**
- These workflows don't need dedicated GPU — they run on existing agents
- A "Business Agent" could be added to the 6-agent roster, or the General Assistant can handle it with the right tool access
- Calendar integration via Home Assistant or direct Google Calendar API
- Client database: simple SQLite or Airtable-style interface
- **Reliability matters more here than for personal projects.** A failed report generation during a busy week is a real business problem. Cloud fallback is not just acceptable, it's preferred for anything client-facing.

#### LoRA Training Pipeline

**Status:** Planned capability, no implementation yet. Hardware is capable.

**Use Cases:**
1. **EoBQ Character Consistency:** Train LoRAs on specific character descriptions, dialogue samples, and personality traits so generated dialogue has consistent voice per character without relying entirely on prompt engineering
2. **EoBQ Visual Consistency:** Train image LoRAs (for Flux/SDXL) on character reference images so the same character looks consistent across scenes — same face, body type, clothing style
3. **Custom Style Models:** Train style LoRAs for specific artistic aesthetics used in EoBQ (e.g., a "film noir" LoRA, a "cyberpunk apartment" LoRA for scene generation)
4. **Business Document Style:** Potentially train a LoRA on Ulrich Energy's existing report library so generated reports match the established writing style

**Pipeline Architecture:**
```
Dataset Preparation
  → Collect training data (dialogue samples, images, documents)
  → Clean and format (JSONL for text, captioned images for visual)
  → Split train/validation sets
  → Store in projects/{project}/training_data/

Training Execution
  → Run on Node 1 (4× 5070 Ti) or Node 2 (5090) depending on model type
  → Text LoRAs: use unsloth, axolotl, or similar training framework
  → Image LoRAs: use kohya_ss or sd-scripts for Flux/SDXL LoRA training
  → Training is a BATCH workload — schedule overnight or during low inference demand
  → Docker container with training framework, mounts model weights and dataset from NVMe

Evaluation
  → Generate test outputs with the LoRA applied
  → Compare against baseline (same prompts, no LoRA)
  → Human review: does this character sound right? does this face match?
  → Automated metrics where applicable (perplexity for text, FID for images)

Deployment
  → Validated LoRA weights → Tier 2 (VAULT model repo) → rsync to node
  → For text: vLLM supports LoRA loading at inference time (--lora-modules flag)
  → For images: ComfyUI loads LoRAs natively via workflow nodes
  → Version control: tag LoRA versions in the model repo, roll back if quality regresses
```

**GPU Requirements:**
- Text LoRA training on a 32B base model: needs ~24-32GB VRAM (fits on 5090)
- Image LoRA training (Flux LoRA): needs ~16-24GB VRAM (fits on 5090 or single 5070 Ti)
- Training time: hours to days depending on dataset size and epochs
- **Critical:** Training and inference cannot share the same GPU simultaneously. Schedule training during off-hours, or dedicate a GPU to training and remove it from the vLLM pool temporarily.

#### Audio Generation Pipeline

**Status:** Emerging capability. The field is evolving fast. No specific model choices locked.

**Use Cases for Athanor:**
1. **EoBQ Ambiance:** Background music and sound effects for game scenes — procedurally generated to match scene mood, not a static library
2. **EoBQ Voice Acting:** Text-to-speech for character dialogue using voice cloning or style-specific TTS models — each character has a distinct voice
3. **Voice Interface for Athanor:** Speech-to-text (Whisper-class) → agent processing → text-to-speech response. Enables voice interaction with the system
4. **Music Generation:** Personal creative tool — generate music based on mood, style, reference tracks
5. **Podcast/Content Production:** If Shaun ever creates content, audio post-processing (noise removal, enhancement, mastering)

**Current Model Landscape (Feb 2026):**
- **Text-to-Speech:** Bark (Suno), XTTS-v2 (Coqui), StyleTTS2, OpenVoice, F5-TTS — all run locally, varying quality
- **Music Generation:** MusicGen (Meta), Stable Audio, Udio/Suno models (cloud), AudioCraft — MusicGen runs locally on GPU
- **Speech-to-Text:** Whisper variants (OpenAI), Whisper.cpp for CPU inference, Distil-Whisper for speed
- **Sound Effects:** AudioGen (Meta) — text-to-sound-effect generation
- **Voice Cloning:** RVC, So-VITS-SVC, OpenVoice — clone a voice from samples, then generate speech in that voice

**Infrastructure Integration:**
- Audio models are generally small (1-4GB VRAM) compared to LLMs
- TTS can run on the 4090 or even a 5070 Ti — it doesn't need the 5090
- STT (Whisper) can run on CPU for non-real-time use cases, GPU for real-time voice interface
- Audio generation integrates into ComfyUI via audio nodes, or standalone containers
- For EoBQ: the Creative Agent triggers audio generation as part of the scene rendering pipeline, alongside image/video generation

**Deployment Pattern:** Same as other creative tools — Docker containers on Node 2, models staged from Tier 2 to Tier 1 NVMe, called via API from the agent framework or directly from EoBQ's game engine.

#### Dashboard Interaction Patterns — Actions vs Observation

**Status:** Discussed conceptually in the agent GUI evaluation session. Needs formalization.

**The dashboard is not just a monitoring tool — it's a control surface.** The information hierarchy (Section 5) defines what you SEE. This section defines what you DO.

**Observation-Only (read, no write):**
- System health metrics (CPU, RAM, GPU temp/utilization, network throughput)
- Agent execution traces (what happened, step by step)
- Plex now playing and recently added
- Home Agent decision log (what it decided and why)
- Supervisor routing log (which agent handled which request)
- Tdarr transcoding history

**Direct Actions (click to do):**
- **Agent toggle:** Turn an agent on/off. Proactive agents stop their timer. Reactive agents stop accepting requests from the supervisor.
- **Agent config edit:** Change an agent's model endpoint (point Research Agent at a different vLLM instance), update tool list, change proactive schedule interval. Changes apply immediately — no restart needed if LangGraph supports hot config reload, otherwise restart the agent container.
- **Model swap:** Load or unload a model on a specific vLLM instance. "Replace Qwen3-32B on Node 1:8000 with Qwen3-30B-A3B" — the dashboard calls vLLM's model management API.
- **Inference queue management:** View pending requests, cancel a stuck request, reprioritize.
- **Creative queue management:** Cancel a queued ComfyUI generation, reprioritize the queue.
- **Media actions:** Trigger a manual Plex library scan, pause/resume Tdarr transcoding, manually add a movie/show to the *arr request queue.
- **Home override:** Override a Home Agent decision — "turn the lights back on" even though the Home Agent turned them off. The override is logged and fed back as a signal for pattern learning (Layer 3 intelligence).
- **System actions:** Restart a Docker container, trigger an Ansible playbook re-run, initiate model staging (rsync from VAULT to node).

**Dangerous Actions (confirmation required):**
- Stop all vLLM instances on a node
- Restart a node (requires SSH under the hood)
- Delete a model from Tier 1 cache
- Clear Knowledge Agent embeddings
- Factory reset an agent's config to defaults

**Implementation Pattern:**
Each dashboard action maps to an API call. The dashboard's Next.js backend is a thin proxy:
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

The dashboard never SSHes into nodes directly. All actions go through documented APIs. This is both a security boundary (the dashboard has API access, not root access) and a reliability pattern (if the dashboard breaks, the services still run independently).

**Open WebUI as Interim:** Before the dashboard exists, Open WebUI provides the chat interface with agent selection. The dashboard adds the system health, agent management, media, home, and creative panels that Open WebUI can't provide. They coexist — Open WebUI for conversation, dashboard for system control.

This document captures everything discussed across claude.ai conversations that wasn't committed to repo docs, including items previously flagged as "future work" that have now been fleshed out with full architectural detail. Commit it to `docs/architecture/complete-context.md` or integrate its sections into the appropriate existing docs.
