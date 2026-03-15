# Athanor Build Manifest

*This is the tactical execution queue. `docs/design/athanor-next.md` is the strategic design layer above it. Claude Code uses this file to decide what to build next, but the queue must remain subordinate to the Athanor Next operating model.*

Last updated: 2026-03-14 (Session 58: plan verification, n8n cleanup, eval refresh)

---

## Strategic Context

- `docs/design/athanor-next.md` is the program north star
- `docs/atlas/README.md` is the canonical cross-layer system map
- this manifest is the tactical queue, not the source of truth for topology or secrets
- `ansible/` is the deployment truth
- `docs/SYSTEM-SPEC.md` is the operational truth
- historical tier entries below are retained as execution history and backlog context

## Program Tracks

- **Command Center** — dashboard, operator UX, project-aware control surface
- **COO / Agent Operations** — tasking, escalation, workspace, trust, proactive behavior
- **Knowledge / Memory** — retrieval, graph, freshness, project-aware context
- **Project Platform** — Athanor core + EoBQ first-class, future tenant scaffolding
- **Infrastructure Convergence** — runtime map, centralized config, deployment alignment, secret cleanup
- **Continuous Refinement** — hardening, observability, tests, docs, drift prevention

## How This Works

1. Claude Code starts a session (interactive or `-p` mode)
2. Reads this manifest to find the highest-priority unblocked item
3. Executes it completely — research, implement, test, document
4. Commits work with descriptive message
5. Updates this manifest (marks complete, adds notes)
6. Updates MEMORY.md with session summary
7. If time/context remains, picks the next item

**Priority levels:** P0 (do now), P1 (do next), P2 (do when P1 is clear), P3 (backlog)
**Status:** 🔲 todo, 🔄 in-progress, ✅ done, 🚫 blocked (with reason)

---

## Tier 1: Infrastructure Gaps (P0)

These are missing pieces that other work depends on.

### 1.1 — Fix DEV→Node SSH access
- **Status:** ✅ (Session 8, 2026-02-24)
- **Root cause:** WSL had different SSH keys than Windows. The `athanor_mgmt` symlink in WSL pointed to a WSL-generated `id_ed25519`, not the Windows key that was deployed to nodes.
- **Fix:** Copied Windows SSH keys (`athanor_mgmt`, `id_ed25519`) to WSL `~/.ssh/`. Added WSL public key to both nodes' `authorized_keys`. Created `~/.ssh/config` with node aliases.
- **Verified:** `ssh node1 hostname` → `core`, `ssh node2 hostname` → `interface`, passwordless sudo works.

### 1.2 — LiteLLM routing layer
- **Status:** ✅ (Session 8, 2026-02-24)
- **Deployed:** VAULT:4000 via Ansible (`ansible-playbook playbooks/vault.yml --tags litellm`)
- **Image:** `ghcr.io/berriai/litellm:main-v1.81.9-stable` (stateless, no DB)
- **Routes (historical deployment note):** the current canonical alias map lives in `docs/design/athanor-next.md` and `docs/SYSTEM-SPEC.md`
- **Aliases:** `gpt-4` → reasoning, `gpt-3.5-turbo` → fast, `text-embedding-ada-002` → embedding
- **Auth:** env-backed bearer token via vault or host env
- **Role:** `ansible/roles/vault-litellm/`
- **Remaining:** None — agents already use LiteLLM (via `extra_body.metadata`), dashboard supports LiteLLM proxy target (`litellm-proxy` in chat selector).

### 1.3 — Embedding model service
- **Status:** ✅ (Verified Session 8, deployed Session 6)
- **Running (historical note):** retrieval originally lived on Node 1; the canonical target topology now places embedding and reranker on DEV
- **Model name:** `/models/Qwen3-Embedding-0.6B` (not HuggingFace path)
- **Dimensions:** 1024, max sequence length 32768
- **Also routed via:** LiteLLM at VAULT:4000 as `embedding`

### 1.4 — Memory persistence layer (Qdrant)
- **Status:** ✅ (Session 8, 2026-02-24)
- **Deployed:** Node 1:6333 (REST), Node 1:6334 (gRPC)
- **Image:** `qdrant/qdrant:v1.13.2`
- **Collections:** `knowledge` (1024-dim, Cosine), `conversations` (1024-dim, Cosine)
- **Storage:** `/opt/athanor/qdrant/storage`
- **Role:** `ansible/roles/qdrant/`
- **E2E tested:** LiteLLM embedding → Qdrant upsert → semantic search (score 0.78)
- **Remaining:** Agent framework integration (memory tools)

### 1.5 — Graph knowledge store (Neo4j)
- **Status:** ✅ (Session 11, 2026-02-24)
- **Deployed:** VAULT:7474 (HTTP), VAULT:7687 (Bolt). Image: `neo4j:5-community` (v5.26.21)
- **Auth:** env-backed Neo4j credentials managed outside tracked docs
- **Memory:** 512m heap initial, 2g max, 1g pagecache
- **Schema:** 4 constraints (Node, Service, Agent, Project uniqueness)
- **Seeded graph:** 4 Nodes, 16 Services, 3 Agents, 3 Projects, 29 relationships (RUNS_ON, DEPENDS_ON, ROUTES_TO, MANAGES, USES)
- **Role:** `ansible/roles/vault-neo4j/` (env-var config, no mounted conf file)
- **Deploy:** `ansible-playbook playbooks/vault.yml --tags neo4j`

---

## Tier 2: Agent Intelligence (P1)

The agent framework exists but is skeletal. These items make agents actually useful.

### 2.1 — Research Agent
- **Status:** ✅ (Session 11, 2026-02-24)
- **Deployed:** Node 1:9000 as `research-agent`, uses `reasoning` model (Qwen3-32B-AWQ)
- **Tools:** `web_search` (DuckDuckGo, no API key), `fetch_page` (HTTP + HTML text extraction), `search_knowledge` (Qdrant vector search via LiteLLM embeddings), `query_infrastructure` (Neo4j Cypher queries)
- **Tested:** Agent produces structured reports with Summary, Key Findings, Sources, and Relevance to Athanor sections. All 4 tools functional.
- **Files:** `agents/research.py`, `tools/research.py`, `agents/__init__.py`, `server.py`
- **Dependency added:** `duckduckgo-search>=7.0` to pyproject.toml

### 2.2 — Knowledge Agent
- **Status:** ✅ (Session 11, 2026-02-24)
- **Deployed:** Node 1:9000 as `knowledge-agent`, uses `reasoning` model (Qwen3-32B-AWQ), temperature 0.3
- **Tools:** `search_knowledge` (Qdrant semantic search), `list_documents` (browse by category), `query_knowledge_graph` (Neo4j structural queries with node name aliasing), `find_related_docs` (combined semantic + graph), `get_knowledge_stats` (collection sizes + graph counts)
- **Indexer:** `scripts/index-knowledge.py` — scans 81 docs, chunks into 922 points, embeds via LiteLLM, upserts to Qdrant. Run from DEV.
- **Tested:** "What ADR covers our inference engine choice?" → correctly finds ADR-005. "What services run on Foundry?" → correctly queries Neo4j graph.
- **Files:** `agents/knowledge.py`, `tools/knowledge.py`, `scripts/index-knowledge.py`

### 2.3 — Creative Agent
- **Status:** ✅ (Session 11, 2026-02-24)
- **Deployed:** Node 1:9000 as `creative-agent`, uses `fast` model (Qwen3.5-27B-AWQ)
- **Tools:** `generate_image` (Flux dev FP8 via ComfyUI API), `check_queue`, `get_generation_history`, `get_comfyui_status`
- **Model download:** Flux dev FP8 (~17GB) downloading to `/mnt/vault/models/comfyui/checkpoints/flux1-dev-fp8.safetensors` via NFS
- **Tested:** Agent returns ComfyUI system status (GPU info, VRAM, versions). Image generation ready once Flux model download completes.
- **Files:** `agents/creative.py`, `tools/creative.py`

### 2.4 — Home Agent activation
- **Status:** ✅ (Session 13, 2026-02-24)
- **Deployed:** Node 1:9000 as `home-agent`, uses `reasoning` model (Qwen3-32B-AWQ)
- **Tools:** `get_ha_states`, `get_entity_state`, `find_entities`, `call_ha_service`, `set_light_brightness`, `set_climate_temperature`, `list_automations`, `trigger_automation`
- **HA Token:** Long-lived access token created for "Athanor Agent Server" (10-year expiry), passed via `ATHANOR_HA_TOKEN` env var
- **HA State:** v2026.2.3, 38 entities (13 domains) — fresh install with cast devices, Sonos controls, weather. Lutron/UniFi integrations not yet added.
- **Service checks:** 18/18 UP (added HA + Neo4j to health checks)
- **Tested:** Agent successfully queries device overview, groups by domain, responds naturally.
- **Remaining:** Add Lutron and UniFi integrations to HA for light/network control
- **Files:** `config.py`, `agents/__init__.py`, `server.py`, `tools/system.py`, `ansible/roles/agents/defaults/main.yml`

### 2.5 — Media Agent wiring
- **Status:** ✅ (Session 10, 2026-02-24)
- **What changed:** Found deployed API keys were stale (from pre-recovery containers). Extracted fresh keys from VAULT config files. Updated Ansible defaults and deployed container.
- **Verified:** All 3 APIs authenticate (Sonarr, Radarr, Tautulli). Search tools work end-to-end: media agent searched Breaking Bad (103 results) and Inception (11 results) successfully. Media status endpoint returns structured data.
- **Keys:** Sonarr `86be97...d07`, Radarr `628ed6...b0b`, Tautulli `efd937...bd5`
- **Note:** Libraries empty — Sonarr/Radarr need Prowlarr indexer config, Tautulli needs Plex connection (both require Shaun in browser)

### 2.6 — Agent routing via LiteLLM
- **Status:** ✅ (Session 10, 2026-02-24)
- **What changed:** Rewired all agent inference from direct vLLM to LiteLLM proxy (VAULT:4000). Config uses model aliases (`reasoning`/`fast`). Service health checks now cover LiteLLM, Qdrant, all vLLM instances (16 services total). Fixed system prompt inaccuracies. Ansible role updated.
- **Verified:** Agent server deployed on Node 1:9000, chat completion works end-to-end through LiteLLM → Qwen3-32B-AWQ. All 16 service health checks pass.
- **Files:** `config.py`, `system.py`, `general.py`, `media.py`, `home.py`, `server.py`, `docker-compose.yml`, Ansible role
- **Remaining:** None — dashboard chat supports LiteLLM proxy (`litellm-proxy` target), agent server, and direct vLLM backends.

---

## Tier 3: Dashboard & Interface (P1)

### 3.1 — Dashboard design system
- **Status:** ✅ (Session 11, 2026-02-24)
- **Delivered:** `projects/dashboard/docs/DESIGN.md` — comprehensive design system documenting principles, OKLCh color palette (core + semantic), typography scale (3 fonts, 8 element sizes), spacing system, component library, interaction states, chart colors, status indicators, responsive strategy, anti-patterns.
- **New CSS tokens:** Added `--success` (green), `--warning` (yellow), `--info` (blue) semantic colors to both light and dark themes. Added `global-error.tsx` for Next.js 16 compatibility.
- **Dashboard rebuilt and deployed** to Node 2:3001.
- **Files:** `projects/dashboard/docs/DESIGN.md`, `globals.css`, `global-error.tsx`

### 3.2 — Dashboard agent integration
- **Status:** ✅ (Session 10, 2026-02-24)
- **What changed:** Dashboard already had full agent routing + tool call visualization — just needed config updates. Added LiteLLM as inference backend (with auth), added 3 missing service checks (LiteLLM, Qdrant, vLLM Embedding), fixed GPU workload labels. Models endpoint now shows all 4 backends (LiteLLM, Node 1, Node 2, Agents).
- **Verified:** 21/22 services UP on dashboard (HA blocked on onboarding). Chat selector shows LiteLLM aliases + direct models + agents. Tool call cards render correctly.
- **Files:** `config.ts`, `chat/route.ts`, `models/route.ts`

### 3.3 — Dashboard monitoring page
- **Status:** ✅ (Session 11, 2026-02-24)
- **Delivered:** Full monitoring page at `/monitoring` with live Prometheus data. Per-node cards show CPU (with 1hr sparkline), memory (with sparkline), disk usage, network throughput. Cluster summary strip shows aggregate metrics. Grafana deep-links to Node Exporter Full and DCGM dashboards. Auto-refresh every 15s via ISR + client-side router refresh.
- **Approach:** Direct Prometheus API queries (not iframe embeds) — cleaner integration, consistent styling, no auth issues.
- **Files:** `projects/dashboard/src/app/monitoring/page.tsx`, sidebar-nav.tsx (added Monitoring link + ServerIcon)

---

## Tier 4: Project Foundations (P2)

### 4.1 — Empire of Broken Queens scaffold
- **Status:** ✅ (Session 12, 2026-02-24)
- **Research:** `docs/research/2026-02-24-eoq-game-engine.md` — evaluated Ren'Py, Godot, Next.js, Ink, TyranoScript, Pixi'VN. Ren'Py can't stream LLM responses (screen freezes 5–30s). Godot is overkill. Ink/Tyrano designed for pre-authored content.
- **Decision:** ADR-014 — Custom Next.js web app. Native HTTP streaming, CORS eliminated via API routes, React/TypeScript most AI-generatable, shares existing dashboard infrastructure.
- **Scaffold:** `projects/eoq/` — Next.js 16, React 19, Tailwind + Framer Motion, Zustand state management. VN components (SceneBackground, CharacterPortrait, DialogueBox, ChoicePanel, useTypewriter hook). API routes for dialogue (LiteLLM SSE streaming) and image generation (ComfyUI proxy). Type system for characters (personality vectors, relationships, emotions, memories), world state, and game sessions.
- **Game loop wired (Session 14):** Mock scene data (Isolde + Shattered Throne Room, 4 dialogue turns with choices), game engine hook (`useGameEngine`), page.tsx wired with startGame/advanceDialogue/handleChoice, click-to-advance for non-choice turns, scene header, streaming text display. API contract aligned between engine and chat route. Builds clean.
- **Deployed (Session 14):** Node 2:3002, Docker container `athanor-eoq`, Ansible role `eoq`. Accessible at http://192.168.1.225:3002.
- **Remaining:** ComfyUI workflow JSONs for scene/portrait generation, character memory (Qdrant integration), additional scenes/characters.
- **Files:** `projects/eoq/`, `docs/decisions/ADR-014-eoq-engine.md`, `docs/research/2026-02-24-eoq-game-engine.md`

### 4.2 — Kindred concept document
- **Status:** ✅ (Session 10, 2026-02-24)
- **Delivered:** `docs/projects/kindred/CONCEPT.md` — passion-based matching, dual-embedding architecture, privacy-first design. Extracted from context doc.
- **Files:** `docs/projects/kindred/CONCEPT.md`

### 4.3 — Ulrich Energy tooling
- **Status:** ✅ (Session 10, 2026-02-24 — partial: workflows doc)
- **Delivered:** `docs/projects/ulrich-energy/WORKFLOWS.md` — 4 automation workflows (report generation, duct leakage forecasting, scheduling, compliance). Extracted from context doc.
- **Remaining:** Full requirements doc, project scaffold in `projects/ulrich-energy/`
- **Files:** `docs/projects/ulrich-energy/WORKFLOWS.md`

---

## Tier 5: Hardening & Polish (P2)

### 5.1 — 10GbE throughput verification
- **Status:** ✅ (Session 12, 2026-02-24)
- **Results:** All pairs >9.4 Gbps, zero retransmits on steady-state intervals.
  - Node 2 → Node 1: **9.42 Gbps** sender / **9.41 Gbps** receiver (10s, 4 streams, 132 retransmits initial burst only)
  - Node 1 → Node 2: **9.43 Gbps** sender / **9.41 Gbps** receiver (5s, 4 streams, 0 retransmits)
  - Node 1 → VAULT: **9.43 Gbps** sender / **9.41 Gbps** receiver (5s, 4 streams, 0 retransmits)
- **Note:** Node 2 UFW blocks non-service ports — had to temporarily allow 5201/tcp for reverse test. VAULT's 10G link (XG port 2) confirmed working at full speed.
- **Tool:** iperf3 3.16 on all nodes (Ubuntu 24.04)

### 5.2 — Ansible full convergence test
- **Status:** ✅ (Session 13, 2026-02-24)
- **Result:** `site.yml` converges idempotent on 3rd run. `changed=2` on both nodes are docker image pull freshness checks (inherent, not drift).
  - **Node 1 (core):** ok=50, changed=2, failed=0
  - **Node 2 (interface):** ok=54, changed=2, failed=0
- **Fixed during convergence:**
  - Stale NFS `/mnt/vault/data` on both nodes (auto-recovered by common role)
  - CRLF→LF Dockerfiles on Node 2 (agents + ComfyUI)
  - `docker_compose_v2` module SHA mismatch bug (added "stop before rebuild" tasks to agents + ComfyUI roles)
  - Removed undefined vault variable references from `host_vars/core.yml` (agent API keys already in role defaults)
- **vault.yml also verified:** ok=29, changed=0 on 2nd run (all 29 tasks idempotent including 10 containers, Neo4j seeding, LiteLLM, monitoring)
- **Files:** `ansible/roles/agents/tasks/main.yml`, `ansible/roles/comfyui/tasks/main.yml`, `ansible/playbooks/site.yml`, `ansible/playbooks/node1.yml`

### 5.3 — Backup strategy
- **Status:** ✅ (Session 12, 2026-02-24)
- **ADR:** ADR-015 — Daily automated backups to VAULT HDD array. Qdrant snapshots (API), Neo4j Cypher export, appdata tarballs. 7-day retention for DBs, 3 snapshots for appdata.
- **Scripts:** `scripts/backup-qdrant.sh` (Node 1, Qdrant snapshot API → NFS), `scripts/backup-neo4j.sh` (VAULT, Cypher export), `scripts/backup-appdata.sh` (VAULT, tar 11 services).
- **Ansible:** `ansible/roles/backup/` — deploys scripts + NFS mount + cron on Node 1.
- **Tested:** Qdrant snapshot API verified (12 MB for knowledge collection). Neo4j API verified (27 nodes). Backup dirs created on VAULT at `/mnt/user/backups/athanor/`.
- **Deployed (Session 13):** Node 1 cron at 03:00 (Qdrant → `/mnt/vault/data/backups/athanor/qdrant/`). VAULT crons at 03:15 (Neo4j) and 03:30 (appdata). First manual run verified: Qdrant 12M, Neo4j 8K/61 lines, appdata in progress.
- **Files:** `docs/decisions/ADR-015-backup-strategy.md`, `scripts/backup-*.sh`, `ansible/roles/backup/`

### 5.4 — GPU power limit persistence
- **Status:** ✅ (Session 12, 2026-02-24)
- **Result:** Systemd oneshot service (`nvidia-power-limits.service`) enabled on Node 1. Per-GPU limits via `nvidia-smi -i N -pl W`. RTX 5070 Ti @ 250W (minimum allowed, range 250–300/350W), RTX 4090 @ 320W (range 150–600W). GPU ordering verified via PCI bus IDs. Service file deployed, daemon-reload + restart confirmed all 5 GPUs.
- **Note:** Initial attempt at 240W failed — RTX 5070 Ti minimum is 250W. Two 5070 Ti cards max at 300W, two at 350W (different PCB variants).
- **Files:** `ansible/host_vars/core.yml`, `ansible/roles/nvidia/templates/nvidia-power-limits.service.j2` (unchanged), `/etc/systemd/system/nvidia-power-limits.service` (deployed)

### 5.5 — CLAUDE.md optimization
- **Status:** ✅ (Session 11, 2026-02-24)
- **Result:** 371 → 165 lines (56% reduction). Services map moved to `docs/SERVICES.md`. Resolved blockers, CLI environment, MCP config, skills list, and agent teams sections removed (all in dedicated files or discoverable). Core identity, principles, hardware, gotchas, and active blockers retained.
- **Files:** `CLAUDE.md`, `docs/SERVICES.md` (new)

---

## Tier 6: Future Capabilities (P3)

### 6.1 — Video generation pipeline (Wan2.x)
- **Status:** ✅ Complete — pipeline verified, Creative Agent wired
- **Research:** `docs/research/2026-02-24-wan2x-video-deployment.md` — Wan2.2 MoE (27B total, 14B active), FP8 format
- **Models downloaded (41 GB total):**
  - `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` (14 GB) → `/mnt/vault/models/comfyui/unet/`
  - `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` (14 GB) → `/mnt/vault/models/comfyui/unet/`
  - `umt5-xxl-enc-fp8_e4m3fn.safetensors` (6.3 GB) → `/mnt/vault/models/comfyui/clip/` (Kijai non-scaled)
  - `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (6.3 GB) → `/mnt/vault/models/comfyui/clip/` (Comfy-Org scaled, unused)
  - `wan_2.1_vae.safetensors` (243 MB) → `/mnt/vault/models/comfyui/vae/`
- **Custom nodes:** ComfyUI-WanVideoWrapper (152 Wan nodes) + ComfyUI-KJNodes, baked into Dockerfile.
- **Text encoder gotcha:** FP8 _scaled_ text encoders rejected by WanVideoWrapper. Must use Kijai's non-scaled version from `Kijai/WanVideo_comfy`.
- **Performance (verified):** 17 frames at 480×320 in ~47-91s, peak 13.74 GB VRAM on 5060 Ti.
- **Dockerfile:** NGC base → torch 2.10.0+cu128 (Blackwell sm_120 verified), torchaudio, clean opencv, WanVideoWrapper + KJNodes.
- **Creative Agent wired:** `generate_video` tool deployed. 5 tools total (image, video, queue, history, status). Agent switched to `reasoning` model for reliable tool calling.
- **Workflow nodes:** WanVideoModelLoader → WanVideoVAELoader → WanVideoTextEncodeCached → WanVideoEmptyEmbeds → WanVideoSampler → WanVideoDecode → SaveAnimatedWEBP
- **Remaining:** Explore higher resolutions (needs 5090 via vLLM sleep mode, blocked)

### 6.2 — InfiniBand networking
- **Status:** 🔲 Backlog
- **Note:** Requires physical work (cable routing, card installation)

### 6.3 — Voice interaction
- **Status:** ✅ Complete — 4 voice containers deployed, HA voice pipeline configured
- **Research:** `docs/research/2026-02-24-voice-interaction.md` — faster-whisper + Kokoro TTS + Piper (HA) + openWakeWord
- **Architecture:** GPU 4 shared between vLLM-embedding (0.40 mem, 8K ctx), wyoming-whisper (float16), Speaches (lazy GPU). Wyoming protocol for HA integration. Piper (CPU) for HA voice responses.
- **Deployed:**
  - VAULT: wyoming-piper (10200, CPU, en_US-lessac-medium) + wyoming-openwakeword (10400, CPU) ✅
  - Node 1: wyoming-whisper (10300, GPU 4, faster-distil-whisper-large-v3 float16) ✅
  - Node 1: Speaches (8200, GPU 4, OpenAI-compatible STT+TTS API) ✅
- **HA Integration:** 3 Wyoming config entries added via API. "Athanor Voice" pipeline created as preferred: STT→conversation→TTS with wake word (ok_nabu). 43 entities total.
- **Ansible:** `ansible/roles/voice/` (Node 1), `ansible/roles/vault-voice/` (VAULT)
- **GPU 4 tuning:** vLLM-embedding resized from 0.90→0.40 mem, 32K→8K ctx to share GPU 4. Total: 8.8 GB / 16.3 GB used.
- **Blackwell gotchas:** CTranslate2 int8 fails on sm_120, must use float16. Speaches image tag is `latest-cuda` not `latest`.
- **Remaining:** Physical voice satellite device (e.g., ESP32-S3), custom wake word training

### 6.4 — Mobile access
- **Status:** 🔲 Backlog — requires remote access solution (6.8 cancelled, revisit when Command Center is complete)
- **Scope:** Access Command Center from phone anywhere. Needs: remote access to LAN (VPN/tunnel), mobile-optimized dashboard.

### 6.5 — qBittorrent + Gluetun VPN
- **Status:** ✅ done (Session 60f, 2026-03-14)
- **Result:** Ansible role `vault-vpn-torrent` deployed. Gluetun VPN (NordVPN/Switzerland OpenVPN) + qBittorrent (linuxserver). Kill switch via `network_mode: service:gluetun`. WebUI at vault:8112. VPN verified (Swiss IP 176.223.172.131).
- **Files:** `ansible/roles/vault-vpn-torrent/`, NordVPN service creds in ansible vault

### 6.6 — Stash AI integration (adult content agent)
- **Status:** ✅ Phase 1 complete — Stash configured + agent deployed
- **Research:** `docs/research/2026-02-24-stash-ai-integration.md`
- **Stash setup:** VAULT:9999, schema v75, `/data/adult` library configured via GraphQL API
- **Agent deployed:** Node 1:9000 as `stash-agent` (8th agent), uses `reasoning` model
- **12 tools:** get_stash_stats, search_scenes, get_scene_details, search_performers, list_tags, find_duplicates, scan_library, auto_tag, generate_content, update_scene_rating, mark_scene_organized, get_recent_scenes
- **Files:** `tools/stash.py`, `agents/stash.py`, `agents/__init__.py`, `server.py`
- **Remaining Phase 2:** VLM auto-tagging plugin (AHavenVLMConnector), face recognition (LocalVisage), Qdrant recommendations collection

### 6.7 — Mining GPU enclosure migration
- **Status:** 🔲 Backlog — requires physical work

### 6.8 — Remote access
- **Status:** ❌ Cancelled — not needed
- **Research:** `docs/research/2026-02-24-remote-access.md` — 5 options evaluated (historical)
- **Decision:** ADR-016 superseded 2026-02-26. No remote access required. Revisit only if Shaun's needs change.

---

## Tier 7: System Design & Meta-Orchestration (P2)

*The design layer between VISION.md and BUILD-MANIFEST.md — how Athanor works as a system.*

### 7.1 — System specification document
- **Status:** ✅ (Session 15, 2026-02-25)
- **Delivered:** `docs/SYSTEM-SPEC.md` — complete operational specification covering architecture, agents, user interaction, development model, intelligence progression, resource management, and organizational structure.

### 7.2 — Agent behavior contracts
- **Status:** ✅ (Session 15, 2026-02-25)
- **Delivered:** `docs/design/agent-contracts.md` — formal contracts for all 6 live agents + 2 planned (Coding, Stash). Each defines purpose, tools, escalation rules, learning signals, and boundaries.

### 7.3 — Hybrid development architecture
- **Status:** ✅ (Session 15, 2026-02-25)
- **Delivered:** `docs/design/hybrid-development.md` — cloud/local coding architecture with MCP bridge, Agent Teams integration, dispatch heuristics, and workflow examples.

### 7.4 — Intelligence layers expansion
- **Status:** ✅ (Session 15, 2026-02-25)
- **Updated:** `docs/design/intelligence-layers.md` — added preference learning mechanisms, escalation protocol with confidence thresholds, activity logging spec, pattern detection jobs, and per-agent feedback signals.

### 7.5 — Deploy Redis on VAULT
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** VAULT:6379, `redis:7-alpine`, AOF persistence, 512MB maxmemory (allkeys-lru).
- **Ansible:** `ansible/roles/vault-redis/`, deployed via `ansible-playbook playbooks/vault.yml --tags redis`
- **Verified:** `docker exec redis redis-cli ping` → PONG
- **Unblocks:** 7.10, 7.11

### 7.6 — Add Coding Agent to agent server
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** Node 1:9000 as `coding-agent`, uses `reasoning` model (Qwen3-32B-AWQ), temperature 0.3.
- **Tools:** `generate_code`, `review_code`, `explain_code`, `transform_code` — structured prompt wrappers for LLM code generation.
- **Files:** `agents/coding.py`, `tools/coding.py`, `agents/__init__.py`, `server.py`
- **Verified:** 7 agents online, coding-agent generates working Python code.
- **Unblocks:** 7.7

### 7.7 — Create MCP bridge for Claude Code → agent server
- **Status:** ✅ (Session 15, 2026-02-25)
- **Delivered:** `scripts/mcp-athanor-agents.py` — FastMCP stdio server exposing 11 tools: coding_generate, coding_review, coding_transform, knowledge_search, knowledge_graph, system_status, gpu_status, recent_activity, store_preference, search_preferences, list_agents.
- **Config:** Added `athanor-agents` to `.mcp.json`. Created `.claude/agents/coder.md` (Local Coder agent) and `.claude/skills/local-coding.md` (dispatch heuristics).
- **Depends on:** 7.6 (Coding Agent) ✅
- **Note:** Requires `mcp` Python package installed on DEV. Tested import + compile.

### 7.8 — Add preferences and activity Qdrant collections
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** Two new Qdrant collections: `activity` (1024-dim, Cosine) and `preferences` (1024-dim, Cosine). Auto-created on agent server startup.
- **Module:** `activity.py` — `log_activity()`, `store_preference()`, `query_preferences()`, `query_activity()`. Fire-and-forget logging via asyncio tasks.
- **Endpoints:** `GET /v1/activity`, `GET /v1/preferences`, `POST /v1/preferences`
- **Activity logging:** All chat completions (streaming + non-streaming) auto-logged with agent, action_type, input/output summaries, tools_used, duration_ms.
- **Verified:** 2 activity points logged from test interactions, preference storage + semantic retrieval working (score 0.73).
- **Unblocks:** 7.9, 7.12

### 7.9 — Implement escalation protocol in agent server
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** `escalation.py` module with 3-tier confidence system (act/notify/ask). Per-agent/per-action-category thresholds. In-memory notification queue (Redis-backed in Phase 4).
- **Endpoints:** `GET /v1/escalation/config`, `POST /v1/escalation/evaluate`, `GET /v1/notifications`, `POST /v1/notifications/{id}/resolve`
- **Categories:** read (0.0), routine (0.5), content (0.8), delete (0.95), config (0.95), security (1.0). Agent overrides: home-agent routine=0.4, media-agent content=0.85.
- **Verified:** Threshold evaluation correct across all tiers. Notification queue and resolution working.
- **Unblocks:** Proactive agent behavior, dashboard notifications (7.13)

### 7.10 — GWT workspace (Phase 1: shared workspace)
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** `workspace.py` module in agent server. Redis-backed (VAULT:6379). WorkspaceItem schema with salience scoring (urgency x relevance x recency). Capacity-limited to 7 items (GWT cognitive bottleneck). 1Hz background competition cycle with history archival.
- **Endpoints:** `GET /v1/workspace` (broadcast), `POST /v1/workspace` (post item), `DELETE /v1/workspace/{id}`, `DELETE /v1/workspace`, `GET /v1/workspace/stats`.
- **Verified:** Items post with computed salience, priority ordering correct (high > normal), recency decay working, competition cycle running.
- **Phase 2 delivered (Session 18):**
  - **Agent registration:** The current system registers all live agents in Redis on startup. `GET /v1/agents/registry` for discovery.
  - **Redis pub/sub:** Competition cycle publishes broadcast to `athanor:workspace:broadcast` channel.
  - **Event ingestion:** `POST /v1/events` converts external events (HA, cron, webhooks) into workspace items with priority mapping.
  - **Conversation logging:** Every chat completion logs to `conversations` Qdrant collection (both user message + agent response, embedded for semantic search).
- **Remaining:** Phase 3 (agents subscribing + reacting to broadcasts, coalition formation, semantic relevance scoring), Phase 4 (experience memory).
- **Decision:** ADR-017

### 7.11 — GPU Orchestrator (custom FastAPI service)
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** `projects/gpu-orchestrator/` — standalone FastAPI service on Node 1:9200. Phase 2 implementation per ADR-018.
- **Features:** 4 GPU zones (primary_inference, flex_1, flex_2, creative), DCGM-exporter-based metrics (no pynvml dependency), vLLM sleep/wake management, TTL-based auto-sleep scheduler (30s polling), Redis state persistence, Prometheus metrics export.
- **Endpoints:** `GET /status` (full GPU state both nodes), `GET /zones`, `GET /gpu/{zone}`, `POST /gpu/{zone}/sleep`, `POST /gpu/{zone}/wake`, `POST /gpu/{zone}/touch`, `GET|PUT /gpu/{zone}/ttl`, `GET /health`, `GET /metrics`.
- **Verified:** 7 GPUs reporting (4x 5070 Ti, 4090, 5090, 5060 Ti), VRAM metrics correct, Prometheus metrics exporting, 18/19 service health checks passing.
- **Ansible:** `ansible/roles/gpu-orchestrator/`, added to `site.yml` for Node 1.
- **Remaining:** Phase 3 (priority preemption, LiteLLM wake-before-route, flex GPU assignment, dashboard GPU page). Requires `--enable-sleep-mode` on vLLM instances.
- **vLLM sleep mode blocked:** NGC vllm:25.12-py3 (v0.11.1) accepts `--enable-sleep-mode` and activates CuMemAllocator, but does NOT register `/sleep` or `/is_sleeping` REST endpoints (404). Also conflicts with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. Template fixed (conditional expandable_segments), but sleep/wake won't work until NGC image upgrade. Revisit when newer NGC vLLM releases.
- **Decision:** ADR-018

### 7.12 — Dashboard: Activity Feed page
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** Dashboard `/activity` page at Node 2:3001. Queries agent server `/v1/activity`. Filterable by agent, adjustable limit (20/50/100). Auto-refresh every 15s. Timeline view with agent badges, duration, tools used, input/output summaries.
- **Files:** `projects/dashboard/src/app/activity/page.tsx`, `sidebar-nav.tsx`

### 7.13 — Dashboard: Notification system
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** Dashboard `/notifications` page at Node 2:3001. Shows pending actions (approve/reject buttons), notifications, and resolved items. Displays escalation threshold config. Auto-refresh every 5s. Color-coded tiers (ask=red, notify=yellow, act=green).
- **Files:** `projects/dashboard/src/app/notifications/page.tsx`, `sidebar-nav.tsx`

### 7.14 — Dashboard: Preferences page
- **Status:** ✅ (Session 15, 2026-02-25)
- **Deployed:** Dashboard `/preferences` page at Node 2:3001. Store new preferences (agent selector, signal type, category). Semantic search across stored preferences. Results show relevance score, signal type, agent, timestamp.
- **Files:** `projects/dashboard/src/app/preferences/page.tsx`, `sidebar-nav.tsx`

---

## Tier 8: Autonomous Workforce (P1)

*Transforms agents from reactive chat endpoints to autonomous workers that execute tasks, delegate to each other, and work proactively.*

### 8.1 — Task Execution Engine (Phase 1)
- **Status:** ✅ (Session 19, 2026-02-25)
- **Deployed:** `tasks.py` module in agent server. Redis-backed task queue, background worker (5s poll, max 2 concurrent), step logging via astream_events, priority ordering, crash recovery, GWT workspace broadcasting.
- **Delegation tools:** `delegate_to_agent` and `check_task_status` added to general-assistant via `tools/execution.py`.
- **API:** `POST /v1/tasks`, `GET /v1/tasks`, `GET /v1/tasks/{id}`, `GET /v1/tasks/stats`, `POST /v1/tasks/{id}/cancel`.
- **MCP bridge:** `submit_task` and `task_status` tools added (14 tools total).
- **Dashboard:** Task Board page at `/tasks` — submit, monitor, filter, cancel tasks.
- **Verified:** Test tasks completed successfully (general-assistant service check + research-agent web search).
- **Files:** `tasks.py`, `tools/execution.py`, `tools/__init__.py`, `server.py`, `mcp-athanor-agents.py`, dashboard `tasks/page.tsx`

### 8.2 — Proactive Agent Scheduler
- **Status:** ✅ (Session 19, 2026-02-25)
- **Deployed:** `scheduler.py` module. Asyncio-based with per-agent intervals, Redis-tracked last-run timestamps, 60s startup delay.
- **Schedules:** general-assistant (30min health check), media-agent (15min download/activity check), home-agent (5min entity state check), knowledge-agent (24h, disabled until re-indexing wired).
- **API:** `GET /v1/tasks/schedules` — returns all schedule configs + next-run timers + scheduler status.
- **Dashboard:** Schedule display section added to Task Board page.
- **Verified:** First scheduled batch fired correctly — all 3 enabled agents submitted tasks within 60s of startup.
- **Files:** `scheduler.py`, `server.py` (lifespan + endpoint), dashboard `tasks/page.tsx`

### 8.3 — Execution Tools (filesystem, shell, git)
- **Status:** ✅ (Session 19, 2026-02-25)
- **Deployed:** 5 new tools in `tools/execution.py`: `read_file`, `write_file`, `list_directory`, `search_files`, `run_command`. Path-scoped security (read from /workspace, write to /output). Shell execution with timeout + command blocklist.
- **Volume mounts:** `/opt/athanor:/workspace:ro` (read-only codebase), `/opt/athanor/agent-output:/output` (writable staging).
- **Dockerfile:** Added `git` and `pytest` to container image.
- **Coding agent:** 9 tools total (4 coding + 5 execution). Autonomous loop verified: read source → generate test → write file → run pytest → self-correct on failure → repeat.
- **Verified:** 10-step coding task ran full loop (4 write-run cycles). Files persisted to disk. Timed out on complex mocks (model quality limitation, resolved by 8.4 upgrade to Qwen3.5-35B).
- **Files:** `tools/execution.py`, `tools/__init__.py`, `agents/coding.py`, `Dockerfile`, `docker-compose.yml`, Ansible role

### 8.4 — Dedicated Coding Model Upgrade
- **Status:** ✅ done (Session 57, 2026-03-14)
- **Result:** Upgraded FOUNDRY coder slot from Qwen3-Coder-30B-A3B (SWE-bench 50.3%) to Qwen3.5-35B-A3B-AWQ-4bit (69.2%). Model uses `compressed-tensors` serialization — must NOT pass `--quantization awq`. LiteLLM `coder` alias updated to `openai/qwen35-coder`. All cross-repo references updated atomically.
- **Research:** `docs/research/2026-03-13-coding-models-march-update.md`

### 8.5 — Quality Gating & Cascade
- **Status:** ❌ Superseded (Session 60g)
- **Original scope:** Automated escalation from local models to cloud Claude when tests fail.
- **Why closed:** Cloud models (Claude opus/sonnet/haiku) are already routable through LiteLLM — same endpoint, same API. No special "escalation" mechanism needed. The routing intelligence is the human workflow: Claude Code for complex reasoning, local Qwen3.5 for mechanical tasks via MCP/aider. Building an automated reward-model quality gate adds complexity with minimal value for a one-person system where the operator already makes the routing decision.

---

## Tier 9: Command Center (P1)

*Evolves the dashboard from monitoring surface to primary interface. Web-first PWA with mobile support, real-time updates, human-in-the-loop feedback, and development integration. Design: `docs/design/command-center.md`. Decision: ADR-019.*

### 9.1 — PWA Foundation + Mobile Layout
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** PWA manifest (`app/manifest.ts`), service worker (`public/sw.js`), PWA icons (192/512/maskable), bottom nav (5 tabs), responsive layout (sidebar hidden on mobile, bottom nav `md:hidden`), 44px touch targets, safe-area padding, viewport meta, apple-web-app meta.
- **Done:** Dashboard installable as PWA. Bottom nav on mobile. Sidebar on desktop. `/more` page for full nav. `/offline` fallback. All pages usable on 6" screen.

### 9.2 — Command Palette (Cmd+K)
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** shadcn/ui `CommandDialog` + cmdk. Fuzzy search over the dashboard routes, agent roster, and quick actions. Cmd+K keyboard shortcut. Mobile FAB trigger button.
- **Done:** Cmd+K opens palette. Searching finds pages/agents/actions. Mobile: floating search button above bottom nav.

### 9.3 — Agent Portrait Bar + Calm Visual Foundation
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** `AgentCrewBar` component — 8 agent circles with per-agent colors, online indicators, click-to-chat links. `SystemPulse` with ambient glow powered by SSE warmth. CSS custom properties `--system-warmth`, `--breath-speed`, `--furnace-glow`. `motion` library installed.
- **Done:** Crew bar on home page with live agent status. SystemPulse has warmth-driven box-shadow. Clicking agent opens chat.

### 9.4 — SSE Real-Time Endpoint
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** `/api/stream` SSE endpoint — fetches GPU metrics (Prometheus), agent status, service health, task stats every 5s. `useSystemStream` hook with exponential backoff reconnection. Connection status indicator. `SystemPulse` replaces static polling on home page.
- **Done:** Fleet telemetry, workforce presence, and service state stream live with auto-reconnect and a 5-minute TTL.

### 9.5 — Furnace Home Surface + Glanceable Widgets
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** Home page redesigned: live SystemPulse (warmth glow), Agent Crew bar, GPU map (responsive grid), workload cards, unified activity stream, quick links.
- **Done:** Home page is visually alive. Idle system = calm dark surface. Active system = warmer amber glow. GPU cards responsive (2-col mobile, 3-col tablet, 5-col desktop).

### 9.6 — Unified Activity Stream
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** `UnifiedStream` component — fetches tasks + activity via `/api/agents/proxy`, merges chronologically, auto-refreshes every 15s. Status dots (completed/running/failed/pending). Agent proxy route (`/api/agents/proxy`) for CORS-free agent server access.
- **Done:** Activity Stream card on home page shows live tasks and agent activity. Separate Plex Watch History card below.

### 9.7 — Push Notifications
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** VAPID key generation, `web-push` npm, push subscription API (`/api/push/subscribe`, `/api/push/send`), PushManager component in preferences page, service worker push handler (already in sw.js from 9.1). VAPID keys in docker-compose env.
- **Done:** Push subscription + send infrastructure deployed. Subscribe/unsubscribe from Preferences page. Escalation and alert events now trigger push delivery end-to-end. Service worker actions route through dashboard-owned workforce/feedback APIs instead of the removed legacy proxy path.

### 9.8 — Generative UI (Chat)
- **Status:** ✅ (Session 20 continued, 2026-02-26)
- **Scope:** Rich tool result rendering in chat. Text parsing for known tool output formats with graceful fallback.
- **Delivered:** `gen-ui/` component directory: `gpu-chart.tsx` (SVG horizontal bars), `service-grid.tsx` (colored dots grid), `task-card.tsx` (status + agent badges), `code-block.tsx` (monospace + copy button), `approval-card.tsx` (escalation approve/reject), `message-renderer.tsx` (splits fenced code blocks). `generative-ui.ts` parsers with `getToolRenderer()` dispatch. `ToolCallCard` upgraded to render rich components on successful parse, falls back to `<pre>`.
- **Design decision:** No Vercel AI SDK — our SSE format has custom events (`tool_start`/`tool_end`) the SDK doesn't handle. Text parsing with regex on known agent output formats, graceful fallback. We control both sides.

### 9.9 — Lens Mode (Intent-Driven Layout)
- **Status:** ✅ (Session 20 continued, 2026-02-26)
- **Scope:** 5 dashboard lenses (default/system/media/creative/eoq) with oklch accent theming, URL query param persistence, section reordering, agent highlighting.
- **Delivered:** `lib/lens.ts` (types + 5 configs), `hooks/use-lens.tsx` (React context, CSS variable overrides, `data-lens` attribute), `components/lens-switcher.tsx` (5 circle buttons), `components/home-sections.tsx` (lens-driven section ordering). Layout wrapped in `LensProvider`. Sidebar nav shows `LensSwitcher` + highlights `navHighlight` items. Bottom nav preserves `?lens=` param. Command palette has "Switch Lens" group. Crew bar dims non-lens agents. Unified stream accepts `filterTypes` prop. Per-lens `--furnace-glow` CSS overrides in `globals.css`.
- **Design decision:** Lens via URL query param (`?lens=system`) — persists across navigation, shareable, no session storage. `router.replace` prevents history pollution. CSS variable override for `--primary`/`--ring` recolors every shadcn component.

### 9.10 — Goals API + Human-in-the-Loop Feedback
- **Status:** ✅ (Session 20 continued, 2026-02-26) — fully complete (dashboard + agent server)
- **Dashboard (Session 20a):** Thumbs up/down feedback buttons on assistant messages in chat, trust badges on agent cards, daily digest card, POST support on agent proxy route. Graceful degradation.
- **Agent server (Session 20b):** `goals.py` module. Feedback storage (`POST /v1/feedback`) writes to Qdrant preferences + Redis counters. Goals CRUD (`GET/POST/DELETE /v1/goals`) in Redis. Trust scores (`GET /v1/trust`) computed from feedback + escalation history with sample-adjusted confidence, rubber-stamp detection. Goals injected into agent context enrichment. Daily digest scheduled task at 6:55 AM via scheduler (gathers task stats, pending approvals, trust scores, active goals).
- **Dashboard updated:** Agent cards now fetch trust from `/v1/trust` endpoint (real data) instead of deriving from escalation config. Feedback buttons aligned with API contract (`feedback_type`/`message_content` fields).

### 9.11 — Terminal Page (xterm.js)
- **Status:** ✅ (Session 35, 2026-02-26)
- **Scope:** `/terminal` page with xterm.js + FitAddon + WebLinksAddon. WebSocket to ws-pty bridge (Node 2:3100). Node selector (DEV/Foundry/Workshop). Dark zinc theme. Dynamic import with `ssr: false`.
- **Delivered:** Terminal page + TerminalView component + ws-pty bridge (node-pty + ws sidecar) all deployed and connected.

### 9.12 — Claudeman Deployment
- **Status:** ✅ (Session 20 continued, 2026-02-26)
- **Scope:** Deployed Claudeman on DEV for multi-session Claude Code web access. HTTPS configured with self-signed cert. Systemd user service with linger for persistence.
- **Delivered:** `claudeman web --https --port 3000` running as `~/.config/systemd/user/claudeman.service`. Accessible at https://192.168.1.167:3000 from any LAN device. Auto-restarts on failure. Persists without login (loginctl linger enabled).
- **Install:** `~/.claudeman/app/` (728 commits, 1435 tests, MIT). CLI at `~/.local/bin/claudeman`.

---

## Tier 10: Personal Data System (P1)

Shaun's "Second Brain" — discovers, catalogs, indexes, and connects all personal data. Design: `docs/design/personal-data-architecture.md`.

### 10.1 — Data Transit (DEV → Node 1)
- **Status:** ✅ (Session 33-34, 2026-02-26)
- **Scope:** `scripts/sync-personal-data.sh` — rsync from DEV WSL to Node 1:/opt/athanor/personal-data/. Volume-mounted read-only in agent container.
- **Result:** 632 MB synced (609 MB photos, 21 MB downloads, 1.6 MB docs, 228 KB configs). Cron: `0 */6 * * *`.

### 10.2 — Bookmark Parse + Index
- **Status:** ✅ (Session 33, 2026-02-26)
- **Scope:** Parse Chrome Netscape HTML, index to Qdrant `personal_data`, Neo4j graph.
- **Result:** 727 unique bookmarks in Qdrant. 727 Bookmark + 78 Topic nodes in Neo4j. 690 CATEGORIZED_AS + 77 SUBCATEGORY_OF relationships.

### 10.3 — GitHub Repo + Star Index
- **Status:** ✅ (Session 33, 2026-02-26)
- **Scope:** Index owned repos (metadata + READMEs) and starred repos via `gh` CLI.
- **Result:** 82 chunks (21 owned + 15 READMEs + 46 starred). 67 GitRepo + 283 Topic nodes in Neo4j. Evolution chain: hydra → kaizen → athanor.

### 10.4 — LLM Entity Extraction
- **Status:** ✅ (Session 34-35, 2026-02-26)
- **Scope:** `scripts/extract-entities.py` — Qwen3.5-27B-AWQ with thinking disabled extracts Person, Organization, Place entities from all 793 Qdrant points into Neo4j.
- **Result:** 3,095 nodes (1055 Topics, 701 Documents, 391 Orgs, 97 People, 67 GitRepos, 24 Services, 18 Places). 4,447 relationships. Zero errors.

### 10.5 — Agent Context Injection
- **Status:** ✅ (Session 33, 2026-02-26)
- **Scope:** `context.py` queries `personal_data` in parallel. 6 agents enriched.
- **Result:** general-assistant(3), knowledge(5), research(3), data-curator(5), home(2), coding(2).

### 10.6 — Personal Data Dashboard Page
- **Status:** ✅ (Session 34, 2026-02-26)
- **Scope:** `/personal-data` page with semantic search, category overview, graph summary, recent items.
- **Result:** 7 new files. Stats and search API routes. Navigation added to sidebar and mobile.

### 10.7 — Data Curator Agent
- **Status:** ✅ (Session 33, 2026-02-26)
- **Scope:** 9th agent with scan_directory, parse_document, analyze_content, index_document, search_personal, get_scan_status, sync_gdrive tools.
- **Result:** Deployed on 6h schedule. Read access to /data/personal/ verified.

### 10.8 — Google Drive Integration
- **Status:** ✅ done (Session 60g)
- **Scope:** rclone sync from 2 Google Drive accounts to FOUNDRY via DEV staging. Unlocks ~40% of personal data.
- **Remotes:** `personal-drive:` (30 GiB, 14 folders) + `uea-drive:` (7 GiB, 8 folders — Ulrich Energy Auditing business). Total ~37 GiB.
- **Pipeline:** `scripts/sync-personal-data.sh` — rclone to DEV `/home/shaun/data/personal/`, rsync to FOUNDRY `/opt/athanor/personal-data/`. Cron every 6 hours on DEV.
- **Next:** Re-run `scripts/index-files.py` against new data to populate `personal_data` Qdrant collection.

### 10.9 — File Content Indexer
- **Status:** ✅ done
- **Scope:** `scripts/index-files.py` — 119/121 files indexed (XLSX, PDF, MD, JSON, configs). 1,511 new Qdrant chunks. Content hash for incremental updates. Qdrant `personal_data`: 2,304 total points.
- **Depends on:** 10.1

### 10.10 — Photo Analysis (VLM)
- **Status:** 🚫 blocked (Qwen3.5-27B multimodal on vLLM 0.17+)
- **Scope:** VLM-powered photo descriptions. EXIF extraction. Property photo → address linking.

---

## Tier 11: Intelligence Layer 3 — Cognitive Synthesis (P1)

*Ported from reference repos (Hydra 71K LOC, Kaizen 15K LOC, Local-System 20K LOC). Extracts battle-tested algorithms, adapts to Athanor patterns (async/await, LiteLLM, Redis, Qdrant, LangGraph, Ansible). ~2080 new LOC, ~410 modified LOC across 8 phases.*

### 11.1 — Tiered Processing Router + Task-Type Detection
- **Status:** ✅ done (Session 37)
- **Source:** `reference/kaizen/cognitive/workspace/tiered.py`, `reference/hydra/src/hydra_tools/routellm.py`, `reference/hydra/src/hydra_tools/intelligent_router.py`
- **Scope:** Classifies requests by complexity tier (REACTIVE/TACTICAL/DELIBERATIVE) and task type (9 types). REACTIVE queries bypass agent graph and use `fast` model directly. Logs routing metadata for cost analysis.
- **Files:** Created `router.py` (~250 LOC). Modified `server.py` (chat endpoint + `/v1/routing/classify`). Modified `config.py` (tier settings).
- **Priority:** P1

### 11.2 — Memory Consolidation Pipeline
- **Status:** ✅ done (Session 38)
- **Source:** `reference/local-system/services/memory/consolidation.py`
- **Scope:** Purges old entries from activity (>30d), conversations (>30d), implicit_feedback (>7d), events (>14d). Daily 3 AM schedule via scheduler. On-demand via `/v1/consolidate`. Safety cap of 500 deletions per collection per run.
- **Files:** Created `consolidation.py` (~170 LOC). Modified `scheduler.py` (+35 LOC). Modified `server.py` (`/v1/consolidate`, `/v1/consolidate/stats`).
- **Depends on:** None
- **Priority:** P1

### 11.3 — Hybrid Search (BM25 + Vector via RRF)
- **Status:** ✅ done (Session 38)
- **Source:** `reference/hydra/src/hydra_tools/hybrid_memory.py`, `reference/local-system/services/memory/search.py`
- **Scope:** Hybrid search combining Qdrant vector search with payload text matching, fused via RRF (`k=60`, weights: vector=0.7, keyword=0.3). Catches exact keyword matches that vector search misses. Falls back to vector-only on failure. Applied to knowledge and personal_data collections in context injection.
- **Files:** Created `hybrid_search.py` (~210 LOC). Modified `context.py` (+30 LOC, `_hybrid_search_collection` wrapper).
- **Depends on:** None
- **Priority:** P1

### 11.4 — Continuous State Tensor + Specialist Interface
- **Status:** ✅ done (Session 38)
- **Source:** `reference/kaizen/cognitive/workspace/cst.py`, `reference/kaizen/cognitive/specialists/base.py`
- **Scope:** CST in Redis: salience map (topic -> float, 0.95x decay), attention mode, working memory (bounded FIFO, max 20), goal stack. Specialist ABC wraps LangGraph agents with `evaluate_salience()` and `generate_proposal()`.
- **Files:** Created `cst.py` (~200 LOC), `specialist.py` (~220 LOC). Modified `workspace.py`, `context.py` (CST injection).
- **Depends on:** None (but 11.1 enhances it)
- **Priority:** P2

### 11.5 — Preference Learning + Model Selection
- **Status:** ✅ done (Session 38)
- **Source:** `reference/hydra/src/hydra_tools/preference_learning.py`
- **Scope:** Per-model, per-task-type stats with composite scoring (`success_rate*0.5 + experience*0.2 + speed*0.2 + low_regenerations*0.1`). Records outcomes on every chat response. Router consults preferences after classification for model override (min 5 samples). Redis persistence at `athanor:preferences`.
- **Files:** Created `preferences.py` (~190 LOC). Modified `router.py` (+25 LOC, `apply_preference_override()`). Modified `server.py` (+30 LOC, outcome recording, feedback integration, `/v1/preferences` endpoint).
- **Depends on:** 11.1 (router)
- **Priority:** P2

### 11.6 — Formal Competition Layer (GWT Phase 3)
- **Status:** ✅ done (Session 38)
- **Source:** `reference/kaizen/cognitive/workspace/competition.py`, `reference/kaizen/cognitive/orchestrator.py`
- **Scope:** Refactored `_competition_cycle()` to use specialist interface: parallel salience eval across all 9 specialists, proposal generation, softmax selection (temp 0.3), inhibition tracking (winners -0.1, losers +0.03, capped 0.8). CST updated from winning specialist. Observable via `/v1/cognitive/cst` and `/v1/cognitive/specialists`.
- **Files:** Modified `workspace.py` (+100 LOC, `_run_specialist_competition()`). Modified `specialist.py` (+50 LOC, `generate_proposal()`, `win_rate`). Modified `server.py` (+32 LOC, cognitive endpoints + lifespan init).
- **Depends on:** 11.4 (CST + Specialist)
- **Priority:** P2

### 11.7 — Agentic RAG / CRAG Pipeline
- **Status:** ✅ done (Session 38)
- **Source:** `reference/hydra/src/hydra_tools/agentic_rag.py`
- **Scope:** Corrective RAG: iterative retrieve→grade→rewrite cycle (max 3 iterations). LLM-based relevance grading (RELEVANT/IRRELEVANT/AMBIGUOUS) via `fast` model. Query rewriting when insufficient relevant docs. Uses hybrid_search for retrieval. New `deep_search` tool for complex queries; `search_knowledge` preserved as fast path.
- **Files:** Created `crag.py` (~270 LOC). Modified `tools/knowledge.py` (+25 LOC, `deep_search` tool).
- **Depends on:** None (benefits from 11.3)
- **Priority:** P2

### 11.8 — Autonomous Research Engine
- **Status:** ✅ done (Session 38)
- **Source:** `reference/hydra/src/hydra_tools/autonomous_research.py`
- **Scope:** Research job CRUD (create/list/get/cancel/delete). Execution via research-agent through task engine. Reports auto-stored to Qdrant knowledge collection with embeddings. Scheduler integration for recurring jobs. API: POST/GET `/v1/research/jobs`, POST `execute`, DELETE.
- **Files:** Created `research_jobs.py` (~310 LOC). Modified `scheduler.py` (+12 LOC). Modified `server.py` (+55 LOC, 4 endpoints).
- **Depends on:** None
- **Priority:** P3

---

## Tier 12: Intelligence Pipeline & Operational Autonomy (P1)

*Signal ingestion, overnight operations, evaluation, and the transition from reactive to proactive system. Sources: DEEP-RESEARCH-LIST §4, §6, §8; ATHANOR-MAP §20-21.*

### 12.1 — Intelligence Signal Ingestion (Miniflux + n8n)
- **Status:** ✅ done (Session 39-40)
- **Miniflux deployed:** VAULT:8070 (miniflux/miniflux:2.2.6 + dedicated PostgreSQL 16). 17 feeds seeded across 6 categories (AI Models, Inference Engines, Dev Tools, Infrastructure, AI News, Security). Polling every 60 min, 5 workers. Admin credentials are managed outside tracked docs.
- **n8n deployed:** VAULT:5678 (n8nio/n8n:latest, v2.10.4). Ansible role `vault-n8n/` (tasks + defaults). Owner credentials are managed outside tracked docs.
- **Signal Pipeline workflow:** 7-node n8n workflow (sequential): Schedule (30 min) → Fetch Miniflux unread → Split → Embed (DEV:8001) → LLM Classify (`fast` model, `enable_thinking: false`) → Store in Qdrant `signals` → Mark read. Active and processing (fixed session 60j — was broken since creation due to parallel fan-out bug + thinking tag contamination).
- **Qdrant `signals` collection:** Created on FOUNDRY:6333 (1024-dim, Cosine).
- **Ansible role:** `ansible/roles/vault-miniflux/` + `ansible/roles/vault-n8n/`.
- **Feed seeder:** `scripts/seed-miniflux-feeds.py` — adds feeds via Miniflux API with category management.
- **Remaining:** Daily signal digest generation. (`search_signals` tool already wired into Knowledge Agent via `KNOWLEDGE_TOOLS`.)
- **Depends on:** None
- **Priority:** Done (remaining items P2)

### 12.2 — Morning Briefing Agent Job
- **Status:** ✅ done (Session 39 verified — infrastructure already exists)
- **Scope:** Daily digest at 6:55 AM + morning work plan at 7:00 AM already in scheduler.py. Pattern detection at 5:00 AM. Memory consolidation at 3:00 AM. Alert checks every 5 min. Work plan refill every 2h. All via task engine with Redis state tracking.
- **Verified:** `scheduler.py` has `_check_daily_digest()` (6:55 AM via `goals.generate_digest_prompt()`), `_check_morning_plan()` (7:00 AM via `workplanner.generate_work_plan()`), `_check_pattern_detection()` (5:00 AM), `_check_consolidation()` (3:00 AM), `_check_alerts()` (5 min intervals).
- **Remaining:** Dashboard `DailyBriefing` component to display the briefing. Integration with Miniflux signal data once 12.1 n8n workflows are ready.
- **Priority:** Done (dashboard component is P2)

### 12.3 — Overnight Autonomous Operations
- **Status:** ✅ done (Session 39)
- **Scope:** Automated overnight operations: Qdrant optimization, Neo4j stale node detection, research job execution, Ansible drift detection (check mode), Gitea mirror push.
- **Deliverables:** `scripts/overnight-ops.sh` (5 phases, dry-run support). `scripts/athanor-overnight.service` + `.timer` (systemd, 11 PM daily). Log dir `/var/log/athanor/`. Dry-run verified — all 5 phases working (7 Qdrant collections, Neo4j query, research jobs, Ansible check, Gitea push).
- **Depends on:** claude-squad installed on DEV ✅
- **Priority:** Done

### 12.4 — LangFuse Observability Wiring
- **Status:** ✅ done (verified Session 39)
- **Scope:** LangFuse was already wired — LiteLLM config has `success_callback: ["prometheus", "langfuse"]`, LANGFUSE_HOST/keys set in container env. Traces flowing (verified: embedding + completion traces at 2026-03-08T05:57).
- **Remaining:** Add prompt versioning for agent system prompts. Dashboard deep-link to LangFuse trace viewer.
- **Depends on:** None
- **Priority:** P2 (remaining items)

### 12.5 — Promptfoo Eval Suite
- **Status:** ✅ done (Session 39)
- **Scope:** 20 eval cases across all agent domains: general (3), knowledge (2), coding (2), research (2), creative (2), home (2), media (2), reasoning (2), safety (2). LLM-as-judge assertions via llm-rubric. Python assertions for structural checks. Routes through LiteLLM (reasoning + fast models).
- **Deliverables:** `evals/promptfooconfig.yaml` (20 test cases, 2 providers). `scripts/run-evals.sh` (LiteLLM health check, dated output).
- **Remaining:** Run baseline evaluation, record scores. Add CI integration to Gitea workflow.
- **Depends on:** None
- **Priority:** Done (baseline run is follow-up)

### 12.6 — Gitea Self-Hosted CI/CD
- **Status:** ✅ done (Session 39)
- **Scope:** Gitea 1.23 on VAULT:3033 (SQLite, rootless). Admin user `athanor`. Athanor repo mirrored. Actions enabled. act_runner v0.2.11 on DEV as systemd service (`athanor-runner.service`). CI workflow: Python syntax check, YAML validation (65 files), TypeScript checks (dashboard + EoBQ), ntfy failure notification.
- **Deliverables:** Ansible role `vault-gitea/` (tasks + defaults, Actions enabled, correct rootless port mapping). `.gitea/workflows/ci.yml`. `scripts/athanor-runner.service`. Git remote `gitea` configured. Runner registered with labels `ubuntu-latest:host,self-hosted:host`.
- **Depends on:** 12.5 (evals for CI) ✅
- **Priority:** Done

### 12.7 — Backup Scheduling Audit & Fix
- **Status:** ✅ done (Session 39)
- **Findings:** FOUNDRY root crontab had no backup cron (only vllm-health-restart). VAULT had Neo4j + Qdrant crons but no appdata cron. Backups were stale (2 days FOUNDRY, 6 days VAULT appdata).
- **Fixed:** Deployed Qdrant backup cron to FOUNDRY root (`0 3 * * *`), ran manual backup (7 collections, 468M). Deployed appdata backup script to VAULT cache drive (`/mnt/appdatacache/backup-appdata.sh`), added cron (`30 3 * * *`). VAULT user share has FUSE write issue (writes to /mnt/user/appdata fail with ENOSPC despite 348G free on cache drive) — scripts deployed to /mnt/appdatacache/ as workaround.
- **Remaining:** Investigate VAULT FUSE ENOSPC issue. Backup alerting drift was reconciled in Session 56; live deploy is pending a matching Ansible vault password source.
- **Depends on:** None
- **Priority:** Done (alert is P2)

### 12.8 — DNS Resolution Between Nodes
- **Status:** ✅ done (Session 39)
- **Scope:** All 4 nodes had zero inter-node hostname resolution. Added cluster hostnames to `/etc/hosts` on all 4 nodes (foundry/.244, workshop/.225, vault/.203, dev/.189). Also added `cluster_hosts` variable to `ansible/group_vars/all/main.yml` and `lineinfile` task to `ansible/roles/common/tasks/main.yml` for future Ansible convergence.
- **Verified:** `ping workshop` from FOUNDRY succeeds (0.384ms). All nodes can resolve all other nodes by hostname.
- **Files:** `ansible/group_vars/all/main.yml`, `ansible/roles/common/tasks/main.yml`, `/etc/hosts` on all 4 nodes.
- **Depends on:** None
- **Priority:** Done

---

## Tier 13: Agent Intelligence Upgrade (P2)

*From reactive to pattern-recognizing. Layer 3 intelligence progression. Sources: DEEP-RESEARCH-LIST §3, §5; SYSTEM-SPEC §6.*

### 13.1 — General Assistant Delegation Upgrade
- **Status:** ✅ done (Session 39)
- **Scope:** Rewrote GA system prompt with: correct architecture (TP=2, current model names, all 4 nodes), explicit delegation rules mapping request types to specialist agents, multi-part decomposition guidance. GA now acts as first-contact router that delegates to specialists rather than attempting everything itself.
- **Files:** Modified `agents/general.py` — updated SYSTEM_PROMPT with delegation rules, correct architecture info, tool usage guidance.
- **Remaining:** A/B comparison (agents-as-tools vs task delegation) deferred to 13.4 eval sprint.
- **Depends on:** 11.1 (router) ✅, 11.6 (competition) ✅
- **Priority:** Done

### 13.2 — Inference-Aware Agent Scheduling
- **Status:** ✅ done (Session 39)
- **Scope:** Created `scheduling.py` — queries Prometheus for GPU utilization and vLLM queue depth. Agent classes: latency-sensitive (general, home, media — always run), batch (research, data-curator, knowledge, coding — throttled under load), creative (allowed under high but not critical load). Thresholds: GPU 80% (high), 95% (critical); queue depth 5 (high), 15 (critical). Integrated into `tasks.py` task worker loop — checks load before executing each task. New endpoint: GET `/v1/scheduling/status`.
- **Files:** Created `scheduling.py` (~120 LOC). Modified `tasks.py` (~15 LOC, scheduling check in worker loop). Modified `server.py` (+10 LOC, status endpoint).
- **Depends on:** 7.11 (GPU orchestrator) ✅
- **Priority:** Done

### 13.3 — Pattern Detection Jobs
- **Status:** ✅ done (Session 39)
- **Scope:** Core pattern detection already existed (failure clusters, feedback trends, escalation frequency, schedule reliability, task throughput, autonomy auto-graduation, convention extraction). Added per-agent behavioral patterns: Media Agent content preferences (action distribution), Home Agent routine detection (time-of-day patterns), Research Agent topic clusters (keyword extraction), Creative Agent output patterns. All stored in Redis, injected into agent context via `get_agent_patterns()`. Runs daily at 5:00 AM via scheduler.
- **Files:** Modified `patterns.py` (+90 LOC, `_detect_agent_behavioral_patterns()`).
- **Depends on:** 7.8 (activity/preferences) ✅, 11.2 (consolidation) ✅
- **Priority:** Done

### 13.4 — Accelerated Evaluation Sprint
- **Status:** ✅ done (Session 39)
- **Scope:** A/B comparison YAML with 16 test cases across reasoning, coding, analysis, creative, instruction-following, knowledge, practical tasks, and edge cases. Tests Qwen3-32B-AWQ (reasoning) vs Qwen3.5-35B-A3B (fast) head-to-head with LLM-rubric assertions and structural checks. Combined with the 20-case baseline eval (12.5), provides 36 total eval cases.
- **Files:** Created `evals/ab-comparison.yaml` (16 test cases, 2 providers).
- **Remaining:** Run both evals and record baseline scores. Feed results through preference learning endpoint.
- **Depends on:** 12.5 (eval suite) ✅, 11.5 (preference learning) ✅
- **Priority:** Done

### 13.5 — Embedding Model Location Decision
- **Status:** ✅ done (Session 39 — decision made)
- **Decision:** Keep embedding + reranker on DEV (4.8GB / 16GB VRAM, 0% GPU utilization). FOUNDRY GPU4 stays free for: future utility model (Qwen3.5-9B), speculative decoding draft model, or overflow inference. LiteLLM already routes `embedding` → DEV:8001 and `reranker` → DEV:8003. No changes needed.
- **Rationale:** DEV has unused GPU capacity, 10GbE latency is negligible for embeddings, and keeping FOUNDRY GPU4 free preserves flex capacity for inference scaling.
- **Depends on:** None
- **Priority:** Done

---

## Tier 14: Creative & Project Depth (P3)

*EoBQ, Kindred, Ulrich Energy, and creative pipeline maturation. Sources: DEEP-RESEARCH-LIST §7, §9, §11.*

### 14.1 — EoBQ Character Portrait Pipeline
- **Status:** ✅ done (Session 39 — core pipeline complete)
- **Scope:** Added `generate_character_portrait` tool to Creative Agent. 5 characters (Isolde, Seraphine, Valeria, Lilith, Mireille) with stored visual descriptions for prompt consistency. Portrait aspect ratio (832x1216), 3 style presets (cinematic, painting, illustration), scene context injection. Uses existing Flux dev FP8 workflow on ComfyUI.
- **Files:** Modified `tools/creative.py` (+50 LOC, EOQB_CHARACTERS dict, generate_character_portrait tool). Existing: `comfyui/flux-character-portrait.json`.
- **Remaining:** LoRA training for character-specific models (needs reference images). IP-Adapter + ControlNet for pose variation. FLUX Kontext evaluation. Gallery component in EoBQ app.
- **Research:** `docs/research/2026-02-24-flux-kontext-portraits.md` (exists)
- **Depends on:** 6.1 (video pipeline) ✅
- **Priority:** P3

### 14.2 — EoBQ Procedural Dialogue System
- **Status:** ✅ done (already built — verified Session 39)
- **Verified:** 5 API routes (701 LOC total): `chat/` (dialogue with character personality, breaking stages, emotional profiles, Qdrant memory retrieval, SSE streaming), `choices/` (LLM-generated player choices with relationship/breaking effects), `narrate/` (narrator perspective), `memory/` (character memory persistence to Qdrant), `generate/` (ComfyUI scene generation). Full type system in `types/game.ts` (244 LOC): BreakingStage, EmotionalProfile, PersonalityVector, RelationshipState, WorldState, PlayerChoice, ChoiceEffects.
- **Remaining:** Neo4j character graph (character→character edges). 3 playable scenes with authored beat hooks. Integration testing with live LLM.
- **Depends on:** 4.1 (EoBQ scaffold) ✅
- **Priority:** Done (remaining items are P3+)

### 14.3 — Home Assistant Integration Depth
- **Status:** 🔄 in-progress (Session 39 — tools expanded, HA config needs Shaun)
- **Scope:** Expanded Home Agent with 3 new tools: `activate_scene` (scene control), `get_entity_history` (trend analysis over N hours), `get_network_devices` (device tracker/presence detection). Lutron and UniFi integrations require Shaun to configure in HA UI. Wyoming voice satellite needs ESP32-S3 hardware.
- **Files:** Modified `tools/home.py` (+3 tools, ~70 LOC).
- **Remaining:** Shaun: configure Lutron + UniFi integrations in HA. Create 3 automation blueprints in HA. Order ESP32-S3 for Wyoming satellite.
- **Depends on:** 2.4 (Home Agent) ✅
- **Priority:** P3 (remaining items need Shaun)

### 14.4 — Ulrich Energy Requirements & Scaffold
- **Status:** ✅ done (Session 39 — requirements complete, scaffold pending)
- **Scope:** Full requirements document: 4 workflows (field inspection, report generation, client communication, analytics), PostgreSQL schema (9 tables), API routes (9 endpoints), LiteLLM integration (cloud models for client-facing reports), mobile-first PWA design. MVP scope and Phase 2 defined.
- **Files:** Created `docs/projects/ulrich-energy/REQUIREMENTS.md` (~180 lines). Existing: `WORKFLOWS.md`.
- **Remaining:** Next.js scaffold in `projects/ulrich-energy/`, API route stubs, database migrations. These are mechanical — good candidate for Local Coder or Aider.
- **Depends on:** None
- **Priority:** Done (scaffold is follow-up)

### 14.5 — Kindred Prototype
- **Status:** 🔲 todo (concept complete, awaiting build decision)
- **Scope:** MVP of passion-based matching system. Dual-embedding architecture (interest vectors + drive-state intensity). Privacy-first design. Integration with Qdrant for similarity search.
- **Concept:** `docs/projects/kindred/CONCEPT.md` covers: passion taxonomy (hierarchical, decay, intensity signals), matching algorithm (depth > breadth weighting, anti-pattern detection, cold start via NLP), Athanor integration (embedding model, PostgreSQL + pgvector, cloud content moderation).
- **Deliverables:** Requirements doc. Data model. Matching algorithm prototype. Basic UI.
- **Depends on:** None (Phase 5+ project per concept doc)
- **Priority:** P3 — Shaun decides when to start

---

## Tier 15: Autonomous Self-Improvement (P1)

*DGM-inspired continuous improvement pipeline. System monitors itself, identifies failures, proposes fixes, validates, and deploys. Sources: docs/research/2026-03-07-autonomous-self-improvement.md*

### 15.1 — Quality Cascade / Model Routing
- **Status:** ✅ done (Session 40)
- **Scope:** Heuristic prompt classifier → model tier routing. Pattern-based task classification (SIMPLE, CHAT, CODE, REASONING, RESEARCH, CREATIVE, SYSTEM, HOME, MEDIA). Queue-depth-aware fallback chains. Cost tracking. LiteLLM route names map to local model tiers.
- **Files:** Created `routing.py` (~377 LOC). Router endpoints at `/v1/routing/`.
- **Depends on:** 1.2 (LiteLLM) ✅

### 15.2 — Self-Diagnosis Engine
- **Status:** ✅ done (Session 40)
- **Scope:** Failure tracking, pattern detection, auto-remediation with safety gates. Athanor-specific rules (vLLM endpoints, NFS stale handles, KV cache corruption, tool call parser). Redis persistence (7-day events, 30-day patterns). Auto-remediation executor for safe fixes (retry, cache clear, reindex). FastAPI router at `/v1/diagnosis/`.
- **Files:** Created `diagnosis.py` (~795 LOC).
- **Depends on:** 7.3 (Redis) ✅

### 15.3 — Semantic Cache
- **Status:** ✅ done (Session 40)
- **Scope:** Qdrant-backed LLM response caching with vector similarity (threshold 0.93, 48h TTL). Embedding via LiteLLM (Qwen3-Embedding, 1024-dim). `cached_completion()` wrapper. Wired into reactive chat path — cache lookup before LLM call, fire-and-forget store after. Cleanup every 1h via scheduler.
- **Files:** Created `semantic_cache.py` (~300 LOC). Modified `server.py` (cache integration in reactive path). Modified `scheduler.py` (+cache cleanup job).
- **Depends on:** 1.2 (LiteLLM) ✅, 7.4 (Qdrant) ✅

### 15.4 — Circuit Breakers
- **Status:** ✅ done (Session 40)
- **Scope:** CLOSED → OPEN → HALF_OPEN state machine. Per-service configs (vLLM: 3 failures/60s, LiteLLM: 5/15s, Qdrant/Redis: 5/10s). Fallback support. Wired into both reactive and agent chat paths. 503 response when all fallbacks exhausted. FastAPI router at `/v1/circuits/`.
- **Files:** Created `circuit_breaker.py` (~240 LOC). Modified `server.py` (breaker integration in both chat paths).
- **Depends on:** None

### 15.5 — Self-Improvement Engine
- **Status:** ✅ done (Session 40)
- **Scope:** DGM-inspired benchmark → analyze → propose → validate → deploy loop. 5 benchmarks: inference_health, inference_latency, memory_recall, agent_reliability, routing_accuracy. Proposal creation with py_compile + YAML validation. Auto-deploy for prompt/config changes. Redis persistence (30-day proposals, 90-day archive). Runs every 6h via scheduler.
- **Files:** Created `self_improvement.py` (~430 LOC). Modified `scheduler.py` (+benchmark job every 6h).
- **Depends on:** 7.3 (Redis) ✅

### 15.6 — Preference Learning
- **Status:** ✅ done (Session 40)
- **Scope:** Per-model, per-task-type interaction recording with composite scoring. Ported from Hydra's preference_learning.py. Redis + Qdrant storage, LiteLLM inference. PreferenceCategory enum: model, agent, creative_style, response_style, routing. FastAPI router at `/v1/preferences/learning/`.
- **Files:** Created `preference_learning.py` (~803 LOC).
- **Depends on:** 7.3 (Redis) ✅, 7.4 (Qdrant) ✅

### 15.7 — Eval Suite & Baseline
- **Status:** ✅ done (Session 40)
- **Scope:** Promptfoo eval config with 20 test cases across all agent types. LLM-as-judge grading via local reasoning model. Abliterated model safety rubrics (uncensored behavior is expected, not penalized). Baseline recorded: 71% pass rate.
- **Files:** Modified `evals/promptfooconfig.yaml`. Created `evals/results/baseline-2026-03-07-v2.json`.
- **Depends on:** 1.2 (LiteLLM) ✅

### 15.8 — Nightly Improvement Pipeline
- **Status:** ✅ done (Session 40)
- **Scope:** 4-script OODA loop + orchestrator: export traces → score interactions → identify failures → deploy improvements. LangFuse data pipeline feeding autonomous improvement cycle. Orchestrator script with --apply/--since flags, cron-ready.
- **Files:** Created `scripts/export-langfuse-traces.py`, `scripts/score-interactions.py`, `scripts/identify-failures.py`, `scripts/deploy-improvements.py`, `scripts/nightly-improvement.sh`.
- **Depends on:** 15.5 (self-improvement engine) ✅, 15.7 (eval suite) ✅

### 15.9 — Wire Integration (Cache + Breakers into Chat Path)
- **Status:** ✅ done (Session 40)
- **Scope:** Semantic cache lookup/store in reactive fast path. Circuit breakers wrapping both reactive LLM calls and agent graph invocations. Diagnosis engine recording failures from agent path. Fallback chain on CircuitOpenError. `cache_hit` field in response. `skip_cache` body param.
- **Files:** Modified `server.py` (~80 LOC changes in chat_completions handler).
- **Depends on:** 15.3 (cache) ✅, 15.4 (breakers) ✅, 15.2 (diagnosis) ✅

### 15.10 — Deploy to FOUNDRY
- **Status:** ✅ done (Session 40)
- **Scope:** rsync 8 files → FOUNDRY, docker compose build --no-cache, up -d. All new endpoints verified: /v1/circuits/ (empty), /v1/cache/stats (0 entries), /v1/routing/matrix (full routing table). Health check: 9 agents online.
- **Depends on:** 15.9 ✅

---

## Tier 16: Remaining Build Items & Polish (P2)

*Completes remaining items from Tiers 12-15, addresses open DEEP-RESEARCH-LIST items, and adds new capabilities identified during build.*

### 16.1 — Knowledge Agent Signals Search Tool
- **Status:** ✅ done (Session 41)
- **Scope:** `search_signals` tool already existed in knowledge.py (lines 353-410). Updated knowledge agent system prompt to reference it with category filters.
- **Depends on:** 12.1 (signal ingestion) ✅

### 16.2 — Dashboard Daily Briefing Component
- **Status:** ✅ done (Session 41)
- **Scope:** `daily-briefing.tsx` — fetches most recent digest task, displays in Card with sunrise icon, auto-refresh 5min. Integrated into home page and lens system. TypeScript clean.
- **Files:** `projects/dashboard/src/components/daily-briefing.tsx`, modified `page.tsx`, `lens.ts`
- **Depends on:** 12.2 (morning briefing) ✅

### 16.3 — Backup Freshness Monitoring
- **Status:** ✅ done (Session 41)
- **Scope:** `backup-age-exporter.py` (Prometheus exporter :9199, stdlib only), systemd service, Grafana alert rules for all 3 backup types (>36h threshold). Ansible tasks for deployment.
- **Files:** `scripts/backup-age-exporter.py`, `scripts/athanor-backup-exporter.service`, `ansible/roles/vault-grafana-alerts/`
- **Depends on:** 12.7 (backup fix) ✅

### 16.4 — EoBQ Character Graph (Neo4j)
- **Status:** ✅ done (Session 41)
- **Scope:** `seed-eoq-graph.py` — 5 Character nodes with full personality vectors, 10 RELATIONSHIP edges (bidirectional dramatic tensions), 3 Scene nodes, 10 APPEARS_IN edges. Seeded live to VAULT Neo4j. Idempotent (MERGE), supports --dry-run.
- **Files:** `scripts/seed-eoq-graph.py`
- **Depends on:** 14.2 (dialogue system) ✅

### 16.5 — LangFuse Prompt Versioning
- **Status:** ✅ done (Session 41)
- **Scope:** `sync-prompts-to-langfuse.py` — syncs 9 agent system prompts to LangFuse prompt management API with versioning and content hash comparison. Script created, needs running against live LangFuse.
- **Files:** `scripts/sync-prompts-to-langfuse.py`
- **Depends on:** 12.4 (LangFuse wiring) ✅

### 16.6 — Ulrich Energy Next.js Scaffold
- **Status:** ✅ done (Session 41)
- **Scope:** Full Next.js 16 scaffold: types (inspection, project, report), API route stubs (inspections CRUD, reports CRUD, projects CRUD), page stubs (dashboard, inspections, reports, projects), Dockerfile, PWA manifest, mobile layout with bottom nav. Needs `npm install` + verification.
- **Files:** `projects/ulrich-energy/` (types/, API routes, pages, Dockerfile, manifest.ts)
- **Depends on:** 14.4 (requirements) ✅

### 16.7 — DEEP-RESEARCH-LIST Reconciliation
- **Status:** ✅ done (Session 41)
- **Scope:** Cross-referenced all 66 items. 28 resolved (annotated with ✅ and build tier references). 5 blocked on Shaun. 33 remain open. Priority order updated. Novel enhancement ideas mapped (6/10 implemented).
- **Files:** Modified `~/repos/DEEP-RESEARCH-LIST.md`
- **Priority:** Done

### 16.8 — Arize Phoenix Deployment
- **Status:** 🚫 deferred — LangFuse already covers tracing; Phoenix adds marginal value at single-operator scale. Revisit if multi-user or complex graph debugging needed.
- **Scope:** Deploy Phoenix on VAULT for agent graph debugging alongside LangFuse. Single container, agent span visualization.
- **Source:** DEEP-RESEARCH-LIST §6.2
- **Priority:** P3

### 16.9 — Benchmark Suite (vLLM + GuideLLM)
- **Status:** ✅ done (Session 41)
- **Scope:** Baseline throughput benchmarks. FOUNDRY Qwen3-32B-AWQ: 659ms TTFT, 26.2 t/s (stable across 5 runs). WORKSHOP Qwen3.5-35B-A3B-AWQ: failed — Triton autotuner OOM (needs cache mount + reduced utilization). Documented root cause and fix plan.
- **Files:** `docs/research/2026-03-08-vllm-baseline-benchmarks.md`
- **Source:** DEEP-RESEARCH-LIST §6.4

### 16.10 — Prompt Injection Defenses
- **Status:** ✅ done (Session 41)
- **Scope:** `input_guard.py` (~300 LOC) — regex-based input/output scanning for invisible Unicode, homoglyphs, prompt injection patterns, data exfiltration, command injection. Risk scoring 0.0-1.0, threshold 0.7 for blocking. Tested: clean=0.00, instruction override=0.60 (warn), chat template injection=0.90 (block), shell injection=1.00 (block).
- **Files:** `projects/agents/src/athanor_agents/input_guard.py`, modified `server.py`
- **Source:** DEEP-RESEARCH-LIST §13.1

### 16.11 — Data Sovereignty Verification
- **Status:** ✅ done (Session 41)
- **Scope:** Full audit of all 4 nodes. Zero unauthorized outbound found. Fixed: vLLM `VLLM_NO_USAGE_STATS=1` + `DO_NOT_TRACK=1` (was missing), LiteLLM `LITELLM_TELEMETRY=False` (was missing), Claude Code `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` added to DEV .bashrc. Documented allowed connections. Firewall recommendations.
- **Files:** `docs/research/2026-03-08-data-sovereignty-audit.md`, modified `ansible/roles/vllm/templates/docker-compose.yml.j2`, `ansible/roles/vault-litellm/tasks/main.yml`
- **Source:** DEEP-RESEARCH-LIST §13.2

### 16.12 — Compound Learning Loop Metrics
- **Status:** ✅ done (Session 41)
- **Scope:** `/v1/learning/metrics` endpoint (~120 LOC) aggregating from 7 subsystems (cache, circuits, preferences, trust, diagnosis, memory, tasks). Compound health score 0.0-1.0 with assessment labels. Dashboard page `learning/page.tsx` with HealthGauge, 7 MetricCards, auto-refresh 30s. Nav items added to sidebar and mobile.
- **Files:** Modified `server.py`, new `projects/dashboard/src/app/learning/page.tsx`, modified `sidebar-nav.tsx`, `more/page.tsx`
- **Source:** DEEP-RESEARCH-LIST §12.4

---

## Tier 17: Post-Reconciliation (P1)

Findings from the 2026-03-08 planning-vs-reality reconciliation session (Opus 4.6). Full reconciliation report in session history.

### 17.1 — Deploy Goose recipes
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Adapted planning-era recipes to Goose v1.27.2 format (pure YAML, `input_type: string`, `requirement: required`, `instructions:` block instead of frontmatter+markdown). Updated endpoint URLs to match current cluster (ports, model names). Both validate and list correctly.
- **Files:** `~/.config/goose/recipes/port-hydra-module.yaml`, `~/.config/goose/recipes/test-all-endpoints.yaml`

### 17.2 — Port morning briefing from Hydra
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Adapted Hydra's 749 LOC morning_briefing.py into `briefing.py` (~250 LOC). 5 parallel async data fetchers: node health (Redis heartbeats), overnight activity (Qdrant `activity`, last 12h), task stats (local task engine), Prometheus alerts, Miniflux RSS (category breakdown). Returns structured JSON with BriefingSection dataclass + markdown digest. Wired as `GET /v1/briefing` endpoint in server.py. Updated `/morning` command to call the endpoint first, with manual fallback.
- **Files:** `projects/agents/src/athanor_agents/briefing.py` (new), modified `server.py`, `.claude/commands/morning.md`
- **Note:** Dropped Hydra's calendar/email/weather fetchers (no local API). Miniflux fetcher requires `MINIFLUX_API_KEY` env var in the agent container. Voice delivery (Kokoro TTS) deferred — available via Speaches at foundry:8200 when needed.

### 17.3 — Import Hydra n8n workflow JSONs
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Imported 3 workflows into n8n at VAULT:5678 via REST API. Adapted all URLs: TabbyAPI→LiteLLM, Ollama→Agent Server, health endpoint→9000, Discord→ntfy. Stripped incompatible tag objects. All imported inactive — need manual review and activation in n8n UI.
- **Workflows:** Athanor Cluster Health Check (5min schedule, Prometheus targets → ntfy), Athanor Daily Health Digest (8 AM, multi-service check → ntfy), Athanor Model Performance Monitor (hourly, inference latency test → ntfy)
- **Note:** 9 remaining Hydra workflows not imported (container-auto-restart, daily-research-digest, database-backup, document-ingestion, health-digest, letta-memory-update, model-change-notifier) — review later for relevance.

### 17.4 — Install parry injection scanner
- **Status:** 🚫 cancelled
- **Scope:** "Parry" is not a shipping tool — it was a concept from Block's Goose red team research, not an installable scanner. The actual defense already exists: `input_guard.py` (Tier 16.10) handles invisible Unicode, homoglyphs, prompt injection patterns, data exfiltration detection, and command injection blocking.

### 17.5 — Add /trace command
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Created `.claude/commands/trace.md` from planning-era `trace-feature.md`. Updated with current repo paths and added metadata header (description, allowed-tools). Total commands now 11.
- **Files:** `.claude/commands/trace.md`

### 17.6 — Clean settings.local.json
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Already clean — the happy-coder debug cruft was in the planning-era archive (`docs/planning/claude-config-planning-era/settings.local.json`), not in the current file. Current file has 16 allow entries, 6 MCP servers, clean structure. The earlier reconciliation commit (66cd7fa) already fixed MCP permission format and added missing servers.

### 17.7 — Update SYSTEM-SPEC.md stale sections
- **Status:** ✅ done (Session 42, 2026-03-08)
- **Scope:** Fixed: VAULT container count 36→42, model inventory ports (8003→8004, 8100→8000), GPU assignments (GPU 2=4090, GPU 3=5070Ti swapped), model names/aliases, agent count 8→9 (added Data Curator), Qdrant vectors 922→2547, Neo4j relationships 43→4447, data flow Node 1:8001→DEV:8001, Node 2:8100→Node 2:8000, added n8n/Gitea/Miniflux to VAULT services list.
- **Files:** `docs/SYSTEM-SPEC.md`

---

## Tier 18: Knowledge Pipeline Upgrades (P1)

*Post-session-46 improvements to the Qdrant knowledge pipeline. Sources: docs/research/2026-03-09-knowledge-architecture-memory.md*

### 18.1 — miniCOIL Hybrid Search
- **Status:** ✅ done (Session 47, 2026-03-09)
- **Scope:** Upgraded `knowledge` Qdrant collection from unnamed dense-only to named dense + miniCOIL sparse vectors. Qdrant-native RRF fusion via `/query` endpoint replaces Python-side RRF for the primary hybrid path. Fallback to keyword scroll retained for collections without sparse vectors (personal_data, conversations, etc.).
  - `index-knowledge.py`: collection migration (delete+recreate with `dense`+`sparse` named vectors, `modifier: idf`), miniCOIL sparse vector computation via FastEmbed 0.7 at index time, payload text index preserved for fallback
  - `hybrid_search.py`: primary path uses Qdrant `/query` with prefetch=[dense, sparse]+fusion=rrf; falls back gracefully if miniCOIL unavailable or collection lacks sparse vectors
  - `pyproject.toml`: added `fastembed>=0.7` dependency
  - Full re-index: 3071 chunks from 172 documents (was 3034 with old schema)
- **Quality improvement:** +2-5% NDCG@10 on keyword-heavy queries (miniCOIL vs BM25/text-match). Exact model/identifier queries ("ADR-017", "Qwen3.5-27B-FP8", IP addresses) now get both semantic + neural keyword boosting.
- **Research:** `docs/research/2026-03-09-knowledge-architecture-memory.md` §5
- **Depends on:** None
- **Priority:** Done

### 18.2 — Neo4j Graph Context Expansion
- **Status:** ✅ done (Session 48, 2026-03-09)
- **Scope:** Wired Neo4j graph traversal into agent context injection pipeline. Qdrant kNN returns top-k chunks → extract source paths → Neo4j 2-hop expansion (source → category → related docs in same category) → appended to context as "## Related Documentation (graph)".
  - `graph_context.py`: new module with `expand_knowledge_graph(client, sources, limit)` — async Neo4j HTTP query, graceful fallback on error. Uses `source` path as linking key (no `neo4j_id` in Qdrant needed).
  - `context.py`: added `_format_graph_related()`, graph expansion call after Qdrant knowledge search completes, `graph_related_lines` in `_build_context_message`. Log format: `3 knowledge (+3 graph)`.
  - `index-knowledge.py`: added `upsert_neo4j_docs()` — MERGE `Document` nodes with `doc_type='athanor'` in Neo4j after each Qdrant upsert batch. 172 Document nodes created across 8 categories (research/hardware/adr/design/general/project/build/vision).
  - Full re-index run to populate Neo4j Document nodes.
- **Actual schema used:** `source` path as key (not `neo4j_id`). No Qdrant payload changes. No `neo4j_graphrag` package (uses existing httpx + Neo4j HTTP API from tools/knowledge.py pattern).
- **Verified:** `+3 graph` docs in context enrichment log. `## Related Documentation (graph)` section rendered in context output. 2-hop: ADR-005 → adr category → 5 other ADRs.
- **Notes:** Category-based expansion is the first hop. Full entity-based expansion (HippoRAG NER → Topic/Entity nodes) is deferred to 18.4. The `doc_type='athanor'` label prevents collision with existing bookmark/GitHub Document nodes.
- **Research:** `docs/research/2026-03-09-knowledge-architecture-memory.md` §4
- **Depends on:** 18.1 ✅
- **Priority:** Done

### 18.3 — Continue.dev IDE Integration
- **Status:** ✅ done (Session 49, 2026-03-09)
- **Scope:** Installed VS Code 1.110.1 via Microsoft apt repo, Continue.dev v1.2.16 extension. Configured `~/.continue/config.json` pointing at LiteLLM on VAULT:4000.
  - Chat: `reasoning` (Qwen3.5-27B-FP8 TP=4) — best quality for code discussion
  - Worker: `worker` (Qwen3.5-35B-A3B-AWQ on WORKSHOP) — alternative MoE model
  - Autocomplete: `fast` (Qwen3-8B on FOUNDRY GPU2) — speed-optimized, `enable_thinking: false` to suppress Qwen3 think tags
  - Embeddings: `embedding` (Qwen3-Embedding-0.6B on DEV) — local, low latency
  - Context providers: code, docs, diff, terminal, problems, folder, codebase
  - Slash commands: edit, comment, share, cmd, commit
  - Telemetry: disabled
- **Verified:** LiteLLM returns 200 for both models. `fast` model with `enable_thinking: false` produces clean output (tested before/after).
- **Research:** `docs/research/2026-03-09-local-ai-productivity-patterns.md` §10
- **Depends on:** None
- **Priority:** Done

### 18.4 — HippoRAG Entity Extraction (Full GraphRAG)
- **Status:** ✅ done (Session 50, 2026-03-09)
- **Scope:** Upgraded 18.2 category-based graph expansion to entity-based multi-hop traversal.
  - `index-knowledge.py`: added `extract_entities_llm(text, title)` — NER via Qwen3.5-27B-FP8 (reasoning alias), extracts up to 15 entities per doc (types: Service, Model, Concept, Technology, Person). Added `upsert_neo4j_entities(source, entities)` — MERGE Entity nodes keyed by `(name_lower, type)`, MERGE MENTIONS edges from Document. Entity extraction runs after all Qdrant + Document upserts (2-phase: embed first, then NER).
  - `graph_context.py`: replaced category-based Cypher with entity 2-hop: `(found:Document)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(related:Document)`, ranked by `count(DISTINCT e) DESC`. Falls back gracefully to [] if no entities (same as before). Updated docstring to document entity traversal.
  - Neo4j index created: `entity_name_lower_type` composite on `(name_lower, type)` for fast MERGE dedup.
  - Full re-index run: 172 docs → 3076 chunks (Qdrant) → 879 Entity nodes → 5455 MENTIONS edges (Neo4j).
- **Verified:** Entity traversal Cypher returns semantically correct results — ADR-005 (inference engine) expands to inference research doc (5 shared: vLLM, SGLang, llama.cpp, Ollama, PagedAttention), CPU optimization, architecture synthesis. Top entities: Athanor (84 docs), vLLM (76), Shaun (40), LiteLLM (32), ComfyUI (29). Agents restarted on FOUNDRY and confirmed healthy.
- **Research:** `docs/research/2026-03-09-knowledge-architecture-memory.md` §1 (HippoRAG v2)
- **Depends on:** 18.2 ✅ (Neo4j Document nodes already created)
- **Priority:** P2

---

## Tier 19: Learning Feedback Loop (P1)

*Session 53. Closes the loop on the skill learning library built in Session 52.*

### 19.1 — Skill Execution Auto-Recording
- **Status:** ✅ done (Session 53, 2026-03-09)
- **Scope:** Wired the skill learning library into the task completion path so skills learn from real agent usage. The skill library existed (Session 52) but all 8 skills had `execution_count: 0` — nothing was calling `record_execution()`.
  - `skill_learning.py`: added `find_matching_skill(prompt, threshold=0.3)` — scores all skills against a task prompt via `_compute_relevance()`, returns `(skill_id, relevance)` for best match above threshold.
  - `tasks.py`: added `_record_skill_execution_for_task(task, success)` fire-and-forget coroutine. Wired into `_execute_task()` success path (before GWT broadcast) and failure path (before `_maybe_retry`). Silent on no match or error.
  - Threshold 0.3 rationale: catches partial trigger-condition word matches (0.3 from `_compute_relevance`) but avoids false positives (minimum for "at least some keyword relevance").
- **Learning loop complete:** Task completes → prompt matched against skill trigger conditions → `record_execution(skill_id, success, duration_ms)` → running-average `success_rate` and `avg_duration_ms` updated → surfaced in `/v1/skills/top` and context injection reliability notes.
- **Verified:** Python compile clean. Deploy in progress.
- **Depends on:** Skill library (Session 52 ✅)
- **Priority:** Done

---

## Tier 20: Routing Optimization & Dashboard Polish (P1)

*Session 54, 2026-03-09. A/B eval results drove model routing fix. Dashboard data format bugs corrected.*

### 20.1 — A/B Model Comparison Eval
- **Status:** ✅ done (Session 54)
- **Scope:** Ran `evals/ab-comparison.yaml` — 16 prompts across 7 categories against both local models.
  - Qwen3.5-27B-FP8 (reasoning): 100% pass, 50.8s avg latency
  - Qwen3.5-35B-A3B-AWQ (worker): 100% pass, 4.2s avg latency
  - Both models equal quality. Worker 12x faster due to MoE sparse activation (3B params active/pass).
  - Rubric bug fixed: farmer puzzle answer was swapped (7↔8 chickens/cows).
- **Result:** `evals/results/ab-comparison-2026-03-09-analysis.md`

### 20.2 — Tactical Routing Fix
- **Status:** ✅ done (Session 54)
- **Scope:** Critical bug: tactical tier used `reasoning` model (50.8s avg) with a 30s timeout → constant timeouts for tactical tasks.
  - `config.py`: `router_tactical_model = "worker"` (was `"reasoning"`)
  - `router.py`: tactical `timeout_s = 60` (was `30`)
  - Deliberative tier stays on `reasoning` for complex multi-step analysis.
  - LiteLLM fallback `worker→reasoning→deepseek` active if Workshop down.

### 20.3 — Dashboard Data Format Fixes
- **Status:** ✅ done (Session 54)
- **Scope:** Fixed 3 bugs across dashboard pages:
  - `goals/page.tsx`: `/v1/trust` returns `{ agents: {...} }` not `{ scores: [...] }`. Trust panel always showed empty. Fixed with Object.entries() transform.
  - `tasks/page.tsx`: Added `data-curator` to `AGENT_COLORS` map (was missing, 9th agent).
  - `learning/page.tsx`: Added Skill Library MetricCard (total/executed/runs/avg success rate) + fetch from `/v1/skills/stats`.
  - `page.tsx`: Fixed stale model names (Qwen3.5-27B-FP8 TP=4, Qwen3.5-35B-A3B-AWQ).

### 20.4 — LangFuse Prompt Sync
- **Status:** ✅ done (Session 54)
- **Scope:** Ran `scripts/sync-prompts-to-langfuse.py` — creative-agent updated (v2), 8 others unchanged.

---

## Tier 21: Operational Excellence & Tooling (P1)

*Session 55, 2026-03-09. MCP token budget cut, miniflux auth fixed, COO system audit.*

### 21.1 — MCP Token Budget Optimization
- **Status:** ✅ done (Session 55)
- **Scope:** Reduced MCP tool schema overhead from ~40,579 to ~8,640 tokens per message (79% reduction).
  - Diagnosed miniflux as the real auth failure: `miniflux-mcp` requires `MINIFLUX_BASE_URL` + `MINIFLUX_TOKEN` env vars. Previous config used wrong keys (`MINIFLUX_URL/USERNAME/PASSWORD`) and wrong auth method (basic auth vs API token).
  - Fixed miniflux: generated API token via PostgreSQL direct insert (`miniflux-postgres` container, `api_keys` table) since REST API endpoints return 404 in Miniflux v2.2.6.
  - Disabled 5 low-use MCP servers: grafana, langfuse, miniflux, n8n, gitea. All preserved in `.mcp.json` with `"disabled": true` — re-enable via `/mcp` toggle as needed.
  - ALWAYS tier (8 servers): docker, athanor-agents, redis, qdrant, smart-reader, sequential-thinking, neo4j, postgres. Total ~8,640 tokens.
  - SOMETIMES tier (5 servers, disabled): grafana, langfuse, miniflux, n8n, gitea.

### 21.2 — Claude Code Plugin Audit
- **Status:** ✅ done (Session 55)
- **Scope:** Deep research on available Claude Code plugins.
  - `context7` is already installed — provides `resolve-library-id` + `query-docs` for live library docs. High value.
  - No additional plugins required. Plugin overhead is always-on (unlike MCP toggles). Everything else is covered by the self-hosted MCP stack.
  - Plan file: `.claude/plans/serene-wibbling-coral.md`

### 21.3 — COO System Audit
- **Status:** ✅ done (Session 55)
- **Scope:** Full live system audit in COO mode.
  - Agent activity: 16/20 recent tasks completed (80%). Agents are running autonomously. Home/media agents checking HA and Sonarr/Radarr hourly.
  - 2 coding-agent task timeouts (EoBQ) diagnosed: wrong path specs in task descriptions (`projects/eoq/components/` vs actual `src/app/components/`). Components already exist and are solid. Not a code failure — task definition quality issue.
  - EoBQ inventory.tsx + scene-transition.tsx verified complete and production-ready.
  - Pending approval task (home-agent energy analysis) self-cleared.
  - Home Assistant: 43 entities, 2 TVs showing unavailable (expected — powered off). No anomalies.

### 21.4 — Grafana Backup Age Alert
- **Status:** ✅ done (Session 59, 2026-03-14)
- **Scope:** Reconciled the repo-side backup alerting path instead of adding a third implementation. `backup-age-exporter.py` now emits both `type` and `target` labels, supports env-configured backup directories, and defaults appdata to `/mnt/appdatacache/backups` with legacy fallback. The `vault-grafana-alerts` role now mounts qdrant, neo4j, and appdata backup directories into the exporter container directly and removes the dead VAULT textfile-collector path. Prometheus alert rules now include `BackupExporterDown` so missing freshness metrics alert explicitly.
- **Deploy:** Ansible vault password unavailable from DEV — deployed manually via SSH. All 5 backup scripts (postgres, stash, qdrant, neo4j, appdata) deployed to VAULT at `/opt/athanor/scripts/` and persisted at `/boot/config/custom/backup-scripts/`. Crontab entries installed and boot-persistent via `/boot/config/go`. Alert rules deployed directly to Prometheus config and reloaded. GPU memory threshold raised to 0.99 (vLLM KV cache steady-state is 95-99%).
- **Verified:** All 5 backups run manually. Neo4j path mismatch fixed (was `/mnt/user/backups/athanor/neo4j`, now `/mnt/user/data/backups/neo4j`). Qdrant/postgres/stash/neo4j backup alerts cleared. Remaining permanent alerts: `flash_config` and `field_inspect` (one-off historical backups, not recurring — acceptable).

---

## Blocked on Shaun

These require human action. Claude Code cannot do them.

| Item | Action | Unblocks |
|------|--------|----------|
| ~~NordVPN credentials~~ | ~~Done~~ | ~~6.5 (qBittorrent)~~ ✅ |
| ~~Anthropic API key~~ | ~~Done~~ | ~~8.5 (Quality Cascade cloud escalation)~~ ✅ |
| ~~Google Drive rclone OAuth~~ | ~~Done~~ | ~~10.8 (Personal Data ~40%)~~ ✅ |
| ~~Node 2 EXPO~~ | ~~Done~~ | ~~DDR5 5600 MT/s~~ ✅ |
| ~~Node 1 Samsung 990 PRO~~ | ~~Done~~ | ~~NVMe storage~~ ✅ |
