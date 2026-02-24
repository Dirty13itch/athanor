# Athanor Build Manifest

*This is the executable build plan. Every item has clear scope, dependencies, definition of done, and priority. Claude Code reads this to decide what to build next.*

Last updated: 2026-02-24

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
- **Status:** 🔲
- **Why:** Claude Code on DEV/WSL can't SSH to Node 1 or Node 2. This blocks all remote management.
- **Scope:** Diagnose why `ssh shaun@192.168.1.244` and `ssh shaun@192.168.1.225` fail from WSL. Check key, check connectivity (`ping`), check if nodes are up. Fix or document the access path.
- **Done when:** `ssh shaun@192.168.1.244 hostname` and `ssh shaun@192.168.1.225 hostname` both succeed from DEV/WSL.
- **Depends on:** Nothing
- **Files:** `~/.ssh/config`, `~/.ssh/known_hosts`

### 1.2 — LiteLLM routing layer
- **Status:** 🔲
- **Why:** ADR-012 decided on LiteLLM. Without it, agents talk directly to individual vLLM instances. LiteLLM provides model aliasing, fallback, load balancing, and a single endpoint for all inference.
- **Scope:** Deploy LiteLLM on Node 1 (or Node 2) via Docker. Configure routes to Node 1 vLLM (Qwen3-32B-AWQ :8000) and Node 2 vLLM (Qwen3-14B :8000). Write Ansible role. Test from dashboard and agents.
- **Done when:** `curl http://<litellm-host>:4000/v1/models` returns both models. Agents and dashboard point to LiteLLM instead of direct vLLM.
- **Depends on:** 1.1 (SSH access to deploy)
- **Files:** `ansible/roles/litellm/`, ADR-012, `projects/agents/src/athanor_agents/config.py`
- **Research:** Read ADR-012 first. Check latest LiteLLM Docker image and config format.

### 1.3 — Embedding model service
- **Status:** 🔲
- **Why:** RAG, knowledge agent, and semantic search all need embeddings. Qwen3-Embedding-0.6B was downloaded but the service config in BUILD-ROADMAP says it was deployed on GPU 4 port 8001 — verify this is actually running.
- **Scope:** Verify or deploy embedding model via vLLM on Node 1 GPU 4 (RTX 5070 Ti). Expose on port 8001. Write/update Ansible role. Test embedding generation.
- **Done when:** `curl http://192.168.1.244:8001/v1/embeddings` with a test string returns a vector.
- **Depends on:** 1.1
- **Files:** `ansible/roles/vllm/`, `services/node1/`

### 1.4 — Memory persistence layer (Qdrant)
- **Status:** 🔲
- **Why:** Agents need persistent vector memory. Knowledge agent needs a vector store. This is the foundation for all RAG and semantic retrieval.
- **Scope:** Deploy Qdrant on Node 1 via Docker. Create initial collections (conversations, knowledge, embeddings). Write Ansible role. Integrate with agent framework.
- **Done when:** Qdrant API responds at `http://192.168.1.244:6333`. At least one collection created. Agent framework can store and retrieve vectors.
- **Depends on:** 1.1, 1.3 (embeddings for vector storage)
- **Files:** `ansible/roles/qdrant/`, `projects/agents/src/athanor_agents/tools/memory.py`
- **Research:** Qdrant Docker deployment, collection schema design, optimal distance metrics for Qwen3 embeddings.

### 1.5 — Graph knowledge store (Neo4j)
- **Status:** 🔲  
- **Why:** Structured relationships between entities (services, nodes, projects, people, concepts). Complements Qdrant's vector search with graph traversal.
- **Scope:** Deploy Neo4j Community on VAULT (storage node, not GPU-bound). Create initial schema (nodes: Service, Node, Project, Agent; relationships: RUNS_ON, DEPENDS_ON, MANAGES). Write Ansible role.
- **Done when:** Neo4j browser accessible at `http://192.168.1.203:7474`. Schema seeded with current infrastructure graph.
- **Depends on:** Nothing (VAULT access works)
- **Files:** `ansible/roles/neo4j/`, seed scripts

---

## Tier 2: Agent Intelligence (P1)

The agent framework exists but is skeletal. These items make agents actually useful.

### 2.1 — Research Agent
- **Status:** 🔲
- **Why:** VISION.md lists this as a core agent. Web search, summarization, report generation.
- **Scope:** Implement research agent in LangGraph. Tools: web search (via tool-calling LLM), document summarization, report writing to `docs/research/`. Register in agent server.
- **Done when:** Can ask "Research the latest vLLM release notes" and get a structured report saved to docs.
- **Depends on:** 1.2 (LiteLLM for model access)
- **Files:** `projects/agents/src/athanor_agents/agents/research.py`, `projects/agents/src/athanor_agents/tools/research.py`

### 2.2 — Knowledge Agent
- **Status:** 🔲
- **Why:** VISION.md: "organizes and surfaces accumulated data: 1,173+ bookmarks, documents, research notes." Proactive, runs daily.
- **Scope:** Implement knowledge agent. Ingests markdown docs from `docs/`, indexes into Qdrant, builds graph relationships in Neo4j. Can answer questions about the project's own documentation and history.
- **Done when:** Can ask "What ADR covers our inference engine choice?" and get accurate retrieval. Daily indexing cron configured.
- **Depends on:** 1.4 (Qdrant), 1.5 (Neo4j), 1.3 (embeddings)
- **Files:** `projects/agents/src/athanor_agents/agents/knowledge.py`, `projects/agents/src/athanor_agents/tools/knowledge.py`

### 2.3 — Creative Agent
- **Status:** 🔲
- **Why:** VISION.md lists as core agent. Generates images/video on demand. ComfyUI is deployed on Node 2.
- **Scope:** Implement creative agent. Tools: trigger ComfyUI workflows (via API), check generation status, retrieve outputs. Support Flux text-to-image initially.
- **Done when:** Can ask "Generate an image of a dark castle at sunset" and get a Flux-generated image returned.
- **Depends on:** 1.2 (LiteLLM), ComfyUI running on Node 2 (verify)
- **Files:** `projects/agents/src/athanor_agents/agents/creative.py`, `projects/agents/src/athanor_agents/tools/creative.py`

### 2.4 — Home Agent activation
- **Status:** 🚫 blocked — HA onboarding requires Shaun in browser
- **Why:** Skeleton exists but tools are disabled pending HA long-lived access token.
- **Scope:** After Shaun completes HA onboarding at :8123, get long-lived token, set ATHANOR_HA_TOKEN, configure Lutron + UniFi integrations, activate home agent tools.
- **Done when:** Home agent can query entity states and control lights.
- **Depends on:** Shaun completing HA onboarding
- **Files:** `projects/agents/src/athanor_agents/agents/home.py`, `projects/agents/src/athanor_agents/tools/home.py`

### 2.5 — Media Agent wiring
- **Status:** 🔲
- **Why:** Media agent code exists but needs verification against the freshly deployed VAULT services. Sonarr/Radarr/Prowlarr API keys may need updating.
- **Scope:** Verify media agent tools work against live Sonarr (:8989), Radarr (:7878), Prowlarr (:9696), Tautulli (:8181). Update API keys/URLs. Test each tool.
- **Done when:** Media agent can search for a show via Sonarr API, search for a movie via Radarr, and report Plex activity via Tautulli.
- **Depends on:** 1.1 or direct VAULT access
- **Files:** `projects/agents/src/athanor_agents/tools/media.py`, `projects/agents/src/athanor_agents/config.py`

### 2.6 — Agent routing via LiteLLM
- **Status:** 🔲
- **Why:** Agents currently hardcode vLLM endpoints. Should route through LiteLLM for model aliasing and fallback.
- **Scope:** Update agent config to use LiteLLM endpoint. Map agent types to model aliases (reasoning tasks → Qwen3-32B, fast responses → Qwen3-14B). Update dashboard chat API route.
- **Done when:** All agents use LiteLLM. Model selection is by alias, not direct URL.
- **Depends on:** 1.2 (LiteLLM deployed)
- **Files:** `projects/agents/src/athanor_agents/config.py`, `projects/dashboard/src/lib/config.ts`

---

## Tier 3: Dashboard & Interface (P1)

### 3.1 — Dashboard design system
- **Status:** 🔲
- **Why:** VISION.md: "Dark, minimal, clean. Inspired by the Twelve Words artifact — Cormorant Garamond, subtle warmth, no clutter. This is a crafted interface, not a generic admin panel."
- **Scope:** Define and implement a proper design system. Typography (Cormorant Garamond for headers, system font for body), color palette (dark with warm accents), spacing scale, component library refinement. This is craft work — take the time.
- **Done when:** Design system documented in `projects/dashboard/docs/DESIGN.md`. All existing pages updated to use it. Feels distinctly Athanor, not generic shadcn.
- **Depends on:** Nothing
- **Files:** `projects/dashboard/src/`, `projects/dashboard/docs/DESIGN.md`

### 3.2 — Dashboard agent integration
- **Status:** 🔲
- **Why:** Dashboard has a chat page but it talks directly to vLLM. Should route through the agent framework for tool-calling capabilities.
- **Scope:** Update chat API route to hit agent server (:9000). Support streaming. Show tool calls in the UI. Allow agent selection (general, media, home, creative).
- **Done when:** Chat in dashboard can trigger agent tools (e.g., "show me GPU temps" actually calls the system tools agent).
- **Depends on:** 2.6 (agents on LiteLLM), 1.1 (SSH for deploy)
- **Files:** `projects/dashboard/src/app/chat/`, `projects/dashboard/src/app/api/chat/`

### 3.3 — Dashboard monitoring page
- **Status:** 🔲
- **Why:** Dashboard has GPU cards but should embed Grafana panels for deep monitoring.
- **Scope:** Add iframe/API integration with Grafana dashboards. Show key metrics: GPU util/temp/VRAM, CPU, memory, disk, network, container health. Auto-refresh.
- **Done when:** Monitoring page shows live data from Grafana. No need to open Grafana separately.
- **Depends on:** Grafana running on VAULT (it is)
- **Files:** `projects/dashboard/src/app/monitoring/`

---

## Tier 4: Project Foundations (P2)

### 4.1 — Empire of Broken Queens scaffold
- **Status:** 🔲
- **Why:** EoBQ is the flagship creative project. Needs proper project structure, tech stack decisions, and initial prototype.
- **Scope:** Research game engine options for AI-integrated visual novel (Ren'Py, Godot, custom web). Create ADR. Set up project structure in `projects/eoq/`. Define character system, dialogue pipeline, image generation workflow.
- **Done when:** ADR written, project scaffold created, tech stack decided, README with architecture overview.
- **Depends on:** Nothing (research phase)
- **Files:** `projects/eoq/`, `docs/decisions/ADR-013-eoq-engine.md`, `docs/projects/eoq/`

### 4.2 — Kindred concept document
- **Status:** 🔲
- **Why:** Listed in VISION.md as a known project. Needs concept crystallization.
- **Scope:** Write concept document defining what Kindred is, how it works, what tech it needs. Not implementation — just clear thinking on paper.
- **Done when:** `docs/projects/kindred/CONCEPT.md` exists with clear product vision.
- **Depends on:** Nothing
- **Files:** `docs/projects/kindred/`

### 4.3 — Ulrich Energy tooling
- **Status:** 🔲
- **Why:** Listed as a project. Shaun's business could benefit from automation tools.
- **Scope:** Audit what Shaun needs for Ulrich Energy (scheduling, reporting, compliance docs, duct leakage forecasting). The airtight-iq-dl-forecasting-engine was mentioned in memory. Create project structure.
- **Done when:** `docs/projects/ulrich-energy/REQUIREMENTS.md` exists. Project scaffold in `projects/ulrich-energy/`.
- **Depends on:** Conversation with Shaun about priorities
- **Files:** `projects/ulrich-energy/`, `docs/projects/ulrich-energy/`

---

## Tier 5: Hardening & Polish (P2)

### 5.1 — 10GbE throughput verification
- **Status:** 🔲
- **Scope:** Run iperf3 between all node pairs. Verify full 10Gbps on data plane. Document results.
- **Done when:** iperf3 results documented, all pairs hitting >9 Gbps.
- **Depends on:** 1.1

### 5.2 — Ansible full convergence test
- **Status:** 🔲
- **Scope:** Run `ansible-playbook playbooks/site.yml` and `playbooks/vault.yml` end to end. Fix any drift. Verify idempotency (second run = 0 changed).
- **Done when:** Both playbooks converge with 0 changed on second run.
- **Depends on:** 1.1

### 5.3 — Backup strategy
- **Status:** 🔲
- **Scope:** Design backup approach for: Ansible configs (git), container appdata (VAULT snapshots), databases (Qdrant/Neo4j dumps), dashboard/agent code (git). Document in ADR.
- **Done when:** ADR written, backup scripts created, tested.
- **Depends on:** 1.4, 1.5 (databases to back up)

### 5.4 — GPU power limit persistence
- **Status:** 🔲
- **Scope:** Create systemd service on Node 1 for persistent GPU power limits (4090 @ 320W, 5070 Ti @ 240W). Add to Ansible nvidia role.
- **Done when:** Power limits survive reboot.
- **Depends on:** 1.1

### 5.5 — CLAUDE.md optimization
- **Status:** 🔲
- **Scope:** CLAUDE.md is 336 lines. Move operational state to MEMORY.md, move service details to dedicated docs. Keep CLAUDE.md focused on role, principles, and structure. Target <200 lines.
- **Done when:** CLAUDE.md is lean. Operational state lives in MEMORY.md. No information lost.
- **Depends on:** Nothing

---

## Tier 6: Future Capabilities (P3)

### 6.1 — Video generation pipeline (Wan2.x)
### 6.2 — InfiniBand networking
### 6.3 — Voice interaction
### 6.4 — Mobile access
### 6.5 — qBittorrent + Gluetun VPN (blocked on NordVPN creds)
### 6.6 — Stash AI integration (adult content agent)
### 6.7 — Mining GPU enclosure migration
### 6.8 — Remote access (Tailscale/WireGuard)

---

## Blocked on Shaun

These require human action. Claude Code cannot do them.

| Item | Action | Unblocks |
|------|--------|----------|
| HA onboarding | Browser: http://192.168.1.203:8123 | 2.4 (Home Agent) |
| NordVPN credentials | Provide service creds | 6.5 (qBittorrent) |
| Node 2 EXPO | BIOS via JetKVM | Performance |
| Samsung 990 PRO reseat | Physical at rack | Node 1 storage |
| BMC config at .216 | Browser: http://192.168.1.216 | Remote power mgmt |
