# Athanor Build Manifest

*This is the executable build plan. Every item has clear scope, dependencies, definition of done, and priority. Claude Code reads this to decide what to build next.*

Last updated: 2026-02-26 (Session 20 continued: Command Center Phase 1+2 built — PWA, mobile layout, SSE, crew bar, unified stream deployed)

---

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
- **Routes:** `reasoning` → Node 1 Qwen3-32B-AWQ, `fast` → Node 2 Qwen3-14B, `embedding` → Node 1 Qwen3-Embedding-0.6B
- **Aliases:** `gpt-4` → reasoning, `gpt-3.5-turbo` → fast, `text-embedding-ada-002` → embedding
- **Auth:** Bearer `sk-athanor-litellm-2026`
- **Role:** `ansible/roles/vault-litellm/`
- **Remaining:** Wire agents and dashboard to use LiteLLM instead of direct vLLM (item 2.6)

### 1.3 — Embedding model service
- **Status:** ✅ (Verified Session 8, deployed Session 6)
- **Running:** Qwen3-Embedding-0.6B on Node 1 GPU 4 (RTX 5070 Ti), port 8001
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
- **Auth:** neo4j/athanor2026
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
- **Deployed:** Node 1:9000 as `creative-agent`, uses `fast` model (Qwen3-14B)
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
- **Remaining:** Dashboard chat route still needs updating (item 3.2)

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
- **Status:** 🔲 Backlog — depends on 6.8 (remote access)

### 6.5 — qBittorrent + Gluetun VPN (blocked on NordVPN creds)
- **Status:** 🚫 Blocked on Shaun (NordVPN credentials)

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
- **Status:** 🔲 Backlog — deprioritized (not currently needed)
- **Research:** `docs/research/2026-02-24-remote-access.md` — 5 options evaluated
- **Decision:** ADR-016 written but approach TBD. Tailscale-on-UDM-Pro removed as requirement.
- **Note:** Revisit if/when mobile access (6.4) becomes a priority.

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
  - **Agent registration:** All 8 agents register capabilities in Redis on startup. `GET /v1/agents/registry` for discovery.
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
- **Verified:** 10-step coding task ran full loop (4 write-run cycles). Files persisted to disk. Timed out on complex mocks (model quality, not infra) — validates need for 8.5 cloud cascade.
- **Files:** `tools/execution.py`, `tools/__init__.py`, `agents/coding.py`, `Dockerfile`, `docker-compose.yml`, Ansible role

### 8.4 — Dedicated Coding Model (Qwen3-Coder-30B-A3B)
- **Status:** 🔲 deferred
- **Rationale:** Current Qwen3-32B-AWQ (SWE-bench 70.7%) outperforms Qwen3-Coder-30B-A3B (50.3%). The coding agent's test failures were quality issues, not speed issues. A faster but lower-quality model wouldn't help. Node 2's 5090 is fully loaded with Qwen3-14B at FP16 (31 GB / 32 GB). Revisit when: (a) AWQ quant available for Coder-Next 80B/3B (SWE-bench 70.6%), or (b) Node 2 GPU can be freed.
- **Research:** `docs/research/2026-02-16-tool-calling-coding-models.md`

### 8.5 — Quality Gating & Cascade
- **Status:** 🔲 todo
- **Scope:** Local model generates → runs tests → if tests fail, escalate to cloud (Claude/Kimi). Automated quality loops for coding tasks.
- **Depends on:** 8.3, 8.4

---

## Tier 9: Command Center (P1)

*Evolves the dashboard from monitoring surface to primary interface. Web-first PWA with mobile support, real-time updates, human-in-the-loop feedback, and development integration. Design: `docs/design/command-center.md`. Decision: ADR-019.*

### 9.1 — PWA Foundation + Mobile Layout
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** PWA manifest (`app/manifest.ts`), service worker (`public/sw.js`), PWA icons (192/512/maskable), bottom nav (5 tabs), responsive layout (sidebar hidden on mobile, bottom nav `md:hidden`), 44px touch targets, safe-area padding, viewport meta, apple-web-app meta.
- **Done:** Dashboard installable as PWA. Bottom nav on mobile. Sidebar on desktop. `/more` page for full nav. `/offline` fallback. All pages usable on 6" screen.

### 9.2 — Command Palette (Cmd+K)
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** shadcn/ui `CommandDialog` + cmdk. Fuzzy search over 15 pages, 8 agents, quick actions. Cmd+K keyboard shortcut. Mobile FAB trigger button.
- **Done:** Cmd+K opens palette. Searching finds pages/agents/actions. Mobile: floating search button above bottom nav.

### 9.3 — Agent Portrait Bar + Calm Visual Foundation
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** `AgentCrewBar` component — 8 agent circles with per-agent colors, online indicators, click-to-chat links. `SystemPulse` with ambient glow powered by SSE warmth. CSS custom properties `--system-warmth`, `--breath-speed`, `--furnace-glow`. `motion` library installed.
- **Done:** Crew bar on home page with live agent status. SystemPulse has warmth-driven box-shadow. Clicking agent opens chat.

### 9.4 — SSE Real-Time Endpoint
- **Status:** ✅ (Session 20, 2026-02-26)
- **Scope:** `/api/stream` SSE endpoint — fetches GPU metrics (Prometheus), agent status, service health, task stats every 5s. `useSystemStream` hook with exponential backoff reconnection. Connection status indicator. `SystemPulse` replaces static polling on home page.
- **Done:** All 7 GPUs, 8 agents, 19 services streaming live. Auto-reconnect on disconnect. 5-minute TTL prevents resource leaks.

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
- **Done:** Push subscription + send infrastructure deployed. Subscribe/unsubscribe from Preferences page. SW handles push display + notification click routing + approve/reject actions. Remaining: wire agent escalation events to trigger sends (needs agent server integration).

### 9.8 — Generative UI (Chat)
- **Status:** 🔲 todo
- **Scope:** Install Vercel AI SDK (`ai`). Chat responses render React components inline. Initial component types: GPU chart, media gallery, task status, approval card. Wire to agent server via LiteLLM.
- **Depends on:** 9.4
- **Done when:** Asking "how are the GPUs?" in chat returns an interactive GPU chart, not just text.

### 9.9 — Lens Mode (Intent-Driven Layout)
- **Status:** 🔲 todo
- **Scope:** Lens state manager (React context + URL query param). Per-lens layout definitions. Command palette triggers lens changes. Smooth layout transitions via `motion`. Initial lenses: Default, System, Media, Creative, EoBQ.
- **Depends on:** 9.2, 9.5
- **Done when:** Typing "focus on media" in command palette reshapes the interface to show media-relevant agents, activity, and controls.

### 9.10 — Goals API + Human-in-the-Loop Feedback
- **Status:** 🔲 todo
- **Scope:** Agent server endpoints: `/v1/goals`, `/v1/goals/steer`. Formalize autonomy levels (A/B/C/D) in agent config. Implicit feedback tracking. Explicit binary feedback (thumbs up/down on stream entries). Daily digest scheduled task (6:55 AM). Trust calibration (track record display, rubber-stamp detection). Impact visibility.
- **Depends on:** 9.6 (stream for feedback surface)
- **Done when:** Can set goals via dashboard. Agents adjust behavior from goals. Thumbs up/down on agent outputs. Daily morning digest available. Per-agent trust metrics visible.

### 9.11 — Terminal Page (xterm.js)
- **Status:** 🔲 todo
- **Scope:** `/terminal` dashboard page with `react-xtermjs`. WebSocket backend on DEV running `node-pty` → Claude Code. Dynamic import with `ssr: false`.
- **Depends on:** 9.1
- **Done when:** Can open Claude Code in a terminal tab within the dashboard.

### 9.12 — Claudeman Deployment
- **Status:** 🔲 todo
- **Scope:** Deploy Claudeman on DEV for multi-session Claude Code web access. Configure HTTPS for LAN access. Test overnight autonomous operation.
- **Depends on:** Nothing
- **Done when:** Claudeman accessible at DEV:3000 on LAN. Multi-session works. Respawn controller tested.

---

## Blocked on Shaun

These require human action. Claude Code cannot do them.

| Item | Action | Unblocks |
|------|--------|----------|
| ~~HA onboarding~~ | ~~Done (Session 13)~~ | ~~2.4 (Home Agent)~~ |
| NordVPN credentials | Provide service creds | 6.5 (qBittorrent) |
| Node 2 EXPO | BIOS via JetKVM | Performance |
| Samsung 990 PRO reseat | Physical at rack | Node 1 storage |
| BMC config at .216 | Browser: http://192.168.1.216 | Remote power mgmt |
