# Athanor System Status

*Ground-truth assessment as of 2026-03-08. Auto-generated from live cluster inspection.*

---

## Claude Code Environment

| Item | Status | Details |
|------|--------|---------|
| Claude Code | v2.1.71 native install | `~/.local/share/claude/versions/2.1.71` — auto-updates ✅ |
| Model | opus (claude-opus-4-6) | Set in `~/.claude/settings.json` |
| Effort | high | Set in user settings |
| mosh | Installed | `/usr/bin/mosh` |
| tmux launcher | Created | `~/bin/athanor` |
| Aider | Installed | `~/.local/bin/aider`, config at `.aider.conf.yml` |
| Goose | Installed | v1.27.2 at `/usr/local/bin/goose`, config at `~/.config/goose/profiles.yaml` |
| claude-squad | Installed | v1.0.16 at `/usr/local/bin/cs` |
| VS Code | v1.110.1 | Installed via Microsoft apt repo |
| Continue.dev | v1.2.16 | `~/.continue/config.json` → LiteLLM:4000. Chat: reasoning/worker. Autocomplete: fast (8B, thinking disabled). Embeddings: embedding. |

## MCP Servers

| Server | Source | Status | Purpose |
|--------|--------|--------|---------|
| grafana | .mcp.json (local) | Active | Query Grafana dashboards, alerts, Prometheus, Loki |
| docker | .mcp.json (local) | Active | Docker container management |
| athanor-agents | .mcp.json (local) | Active | Agent server at foundry:9000 |
| redis | .mcp.json (local) | Active | Redis state, heartbeats, workspace, scheduler |
| qdrant | .mcp.json (local) | Active | Vector DB collections, search, scroll |
| smart-reader | .mcp.json (local) | Active | Smart file reading, grep, diff, log |
| sequential-thinking | .mcp.json (local) | Active | Structured reasoning meta-tool |
| neo4j | .mcp.json (local) | Active | Direct Cypher queries to knowledge graph |
| postgres | .mcp.json (local) | Active | SQL access to VAULT databases (Zed fork) |
| gitea | .mcp.json (local) | Active | Repo/issue/PR management on VAULT:3033 |
| Context7 | claude.ai connector | Active | Library documentation lookup |
| Gmail | claude.ai connector | Active | Email integration |
| Google Calendar | claude.ai connector | Active | Calendar management |
| Grafana | claude.ai connector | Active (duplicate) | Same as local, managed by Anthropic |
| Hugging Face | claude.ai connector | Active | Model/dataset search — low value for ops |
| Vercel | claude.ai connector | Active | Deployment platform — not currently used |

**Removed from local config:** context7 (plugin duplicate), filesystem, playwright.

## Configuration Inventory

### Commands (10)
`audit` `build` `decide` `deploy` `health` `morning` `orient` `project` `research` `status`

### Skills (13)
`architecture-decision` `athanor-conventions` `comfyui-deploy` `deploy-agent` `deploy-docker-service` `gpu-placement` `local-coding` `network-diagnostics` `node-ssh` `state-update` `troubleshoot` `verify-inventory` `vllm-deploy`

### Agents (6)
`coder` `debugger` `doc-writer` `infra-auditor` `node-inspector` `researcher`

### Rules (10)
`agents` `ansible` `dashboard` `docker` `docs` `eoq` `knowledge` `scripts` `session-continuity` `vllm`

### Hooks (12 scripts, 14 registrations)
| Hook | Event | Purpose |
|------|-------|---------|
| pre-tool-use-protect-paths | PreToolUse (Edit/Write) | Protects critical files from accidental overwrites |
| pre-tool-use-bash-firewall | PreToolUse (Bash) | Blocks dangerous commands |
| post-tool-use-typecheck | PostToolUse (Edit/Write) | Runs TypeScript/Python checks after edits |
| post-tool-use-failure | PostToolUseFailure | Injects diagnostic context on tool failures |
| pre-compact-save | PreCompact | Saves session state before context compression |
| session-start | SessionStart | Loads context at session start |
| session-start-health | SessionStart | Quick cluster health check |
| session-end | SessionEnd | Updates STATUS.md timestamp |
| stop-autocommit | Stop | Auto-commits state files on session end |
| task-completed-notify | TaskCompleted | Desktop notification for background tasks |
| user-prompt-context | UserPromptSubmit | Injects timestamp + git context |
| statusline | StatusLine | Node health from Redis heartbeats |

## Cluster State

### FOUNDRY (.244) — 11 containers

| GPU | Model | VRAM | Container | Port |
|-----|-------|------|-----------|------|
| 0: RTX 5070 Ti (MSI) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | vllm-coordinator | 8000 |
| 1: RTX 5070 Ti (Gigabyte) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | — |
| 2: RTX 4090 (ASUS) | Huihui-Qwen3-8B-abliterated-v2 | 21.3/24.6 GB | vllm-utility | 8002 |
| 3: RTX 5070 Ti (Gigabyte) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | — |
| 4: RTX 5070 Ti (MSI) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | — |

Other containers: `athanor-agents` (9000), `athanor-gpu-orchestrator`, `alloy`, `wyoming-whisper` (10300), `qdrant` (6333-6334), `speaches` (8200), `dcgm-exporter` (9400), `node-exporter`

### WORKSHOP (.225) — 9 containers

| GPU | Model | VRAM | Temp | Container | Port |
|-----|-------|------|------|-----------|------|
| 0: RTX 5090 | Qwen3.5-35B-A3B-AWQ-4bit | 31.3/32.6 GB | 38°C | vllm-node2 | 8000 |
| 1: RTX 5060 Ti | ComfyUI | 5.1/16.3 GB | 32°C | comfyui | 8188 |

Other: `athanor-dashboard` (3001), `athanor-eoq` (3002), `athanor-ws-pty-bridge` (3100), `open-webui` (3000), `alloy`, `dcgm-exporter`, `node-exporter`

### VAULT (.203) — 42 containers

Key services: `litellm` (4000), `grafana` (3000), `prometheus`, `backup-exporter`, `n8n` (5678), `gitea` (3033), `miniflux` (8070), `redis`, `vault-open-webui` (3090), `langfuse-web` (3030) + 5 langfuse services, `neo4j` (7474/7687), `qdrant` (6333), `postgres` (5432), `stash` (9999), `plex`, `homeassistant`, media stack (sonarr/radarr/prowlarr/sabnzbd/tautulli/tdarr), `spiderfoot` (5001), `ntfy` (8880), `meilisearch` (7700), `field-inspect-app` (3080), monitoring (loki, alloy, cadvisor, node-exporter)

### DEV (.189) — 2 containers

| GPU | Model | VRAM | Container | Port |
|-----|-------|------|-----------|------|
| 0: RTX 5060 Ti | Embedding + Reranker | 4.8/16.3 GB | vllm-embedding (8001), vllm-reranker (8003) | 8001, 8003 |

## Service Health (verified from DEV)

| Endpoint | Model/Service | Status |
|----------|---------------|--------|
| foundry:8000 | Qwen3.5-27B-FP8 (TP=4) | ✅ Healthy |
| foundry:8002 | Huihui-Qwen3-8B-abliterated-v2 | ✅ Healthy |
| foundry:9000 | Agent Server (9 agents) | ✅ Healthy |
| workshop:8000 | Qwen3.5-35B-A3B-AWQ-4bit | ✅ Healthy |
| vault:4000 | LiteLLM (14 model routes) | ✅ Healthy |

### LiteLLM Model Routes
`reasoning` `coding` `fast` `creative` `embedding` `reranker` `worker` `claude` `gpt` `deepseek` `gemini` + aliases (`gpt-4` `gpt-3.5-turbo` `text-embedding-ada-002`)

## Known Issues & Blockers

| Issue | Impact | Resolution |
|-------|--------|------------|
| **Ansible vault-password** | Resolved | Vault recreated 2026-03-08, `ansible vault -m ping` verified |
| **MSI 5070 Ti RGB still ON** (×2) | Cosmetic | I2C port 1 not exposed on Blackwell. Fix: one-time MSI Center from Windows |
| **FOUNDRY GPU 4 in TP=4** | Part of Qwen3.5-27B-FP8 TP=4 | All 4x 5070 Ti now in use |
| **NordVPN credentials** | qBittorrent blocked | Shaun needs to provide |
| **Anthropic API key** | Quality Cascade cloud escalation blocked | Shaun needs to provide |
| **Google Drive OAuth** | ~40% personal data inaccessible | Shaun needs to run rclone config |

## Build Progress

All 16 tiers COMPLETE. Remaining open items are backlog or blocked on Shaun:
- 6.2 InfiniBand (backlog)
- 6.4 Mobile access (backlog)
- 6.7 Mining enclosure (physical)
- 8.4 Dedicated Coding Model (deferred)
- 14.3 Home Assistant depth (needs Shaun)
- 14.5 Kindred prototype (awaiting decision)

## Session 49 (2026-03-09) Summary

### Completed This Session
- **LangFuse per-agent metadata:**
  - Added `extra_body` metadata to all 9 agent ChatOpenAI constructors: `trace_name`, `tags`, `trace_metadata`
  - KEY: LiteLLM uses `trace_name` (sets trace name), `tags` (array → LangFuse tags), `trace_metadata` (dict → LangFuse metadata). Plain `metadata.agent` is ignored.
  - Also added `metadata`+`tags` to LangChain run configs in `server.py` and `tasks.py` for future LangChain-native LangFuse integration
  - Verified: `knowledge-agent` trace shows `name='knowledge-agent', tags=['knowledge-agent'], meta={'agent': 'knowledge-agent'}`

- **Continue.dev IDE Integration** (18.3):
  - VS Code v1.110.1 installed via Microsoft apt repo (Ubuntu 24.04)
  - Continue.dev v1.2.16 extension installed headlessly
  - `~/.continue/config.json`: Chat → `reasoning` (Qwen3.5-27B-FP8) + `worker` (35B-A3B on WORKSHOP); Autocomplete → `fast` (Qwen3-8B, `enable_thinking: false`); Embeddings → `embedding` (Qwen3-Embedding-0.6B)
  - **Verified:** LiteLLM 200, `reasoning` model chat works, `fast` model with thinking disabled produces clean output
  - `drop_params: true` in LiteLLM does NOT strip `chat_template_kwargs` — verified by test

### Next Actions
1. HippoRAG entity extraction (18.4) — NER at index time, upgrade category-based to entity-based graph expansion
2. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
3. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 48 (2026-03-09) Summary

### Completed This Session
- **Neo4j Graph Context Expansion** (18.2):
  - `graph_context.py`: 2-hop Neo4j expansion after Qdrant knowledge search — source → category → related docs in same category
  - `context.py`: wired graph expansion into enrichment pipeline; new "## Related Documentation (graph)" context section; log shows `3 knowledge (+3 graph)`
  - `index-knowledge.py`: added `upsert_neo4j_docs()` — MERGE Document nodes with `doc_type='athanor'` in Neo4j; 172 nodes created across 8 categories
  - Full re-index run to populate all Neo4j Document nodes
  - Agents rebuilt + deployed: all 9 healthy at foundry:9000
  - **Verified working:** `+3 graph` in context log, graph section renders in context output

### LangFuse Audit Finding
All traces arrive as generic `litellm-acompletion`/`litellm-aembedding` — no agent-level metadata. LangChain callbacks don't thread `agent_name` to LiteLLM. Can't distinguish which agent made which call. Fix: add `metadata={"agent": agent_name}` to LangChain chain config in `tasks.py`.

### Next Actions
1. Install VS Code + Continue.dev on DEV → FOUNDRY:8000 (18.3) — highest daily-use ROI
2. HippoRAG entity extraction (18.4) — NER at index time, upgrade category-based to entity-based graph expansion
3. LangFuse per-agent metadata: thread `agent_name` through LangChain callbacks to LiteLLM → LangFuse
4. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
5. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 47 (2026-03-09) Summary

### Completed This Session
- **miniCOIL hybrid search** (18.1):
  - `knowledge` Qdrant collection migrated: unnamed dense → named `dense` + `sparse` (miniCOIL) vectors
  - `index-knowledge.py`: adds miniCOIL sparse vectors at index time (FastEmbed 0.7, `Qdrant/minicoil-v1`, 90MB)
  - `hybrid_search.py`: primary path uses Qdrant `/query` endpoint with native RRF fusion; graceful fallback to keyword scroll for collections without sparse vectors
  - `pyproject.toml`: added `fastembed>=0.7`
  - Full re-index: 3071 chunks from 172 documents (was 3034)
  - Agents rebuilt + deployed: all 9 healthy at foundry:9000
  - miniCOIL model loads on first query (~5s one-time), cached thereafter
  - **Quality improvement:** +2-5% NDCG@10 on keyword-heavy queries

### Next Actions
1. Wire `QdrantNeo4jRetriever` into agent context pipeline (18.2) — +20% multi-hop accuracy
2. Add miniCOIL sparse vectors to `personal_data` collection (when that collection gets data)
3. Install VS Code + Continue.dev on DEV → FOUNDRY:8000 (18.3) — highest daily-use ROI
4. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py` ← DONE
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 46 (2026-03-09) Summary

### Completed This Session
- **EoBQ uncensored content wiring** (plan fully executed):
  - `flux-uncensored.safetensors` LoRA (0.85 strength) wired into all Flux workflows via `LoraLoaderModelOnly` node "11" — both EoBQ portrait/scene JSON files + dashboard comfyui templates
  - `uncensored` LiteLLM alias added → `Huihui-Qwen3-8B-abliterated-v2` at foundry:8002. Confirmed in `/v1/models` list.
  - EoBQ chat + narrate routes: intensity ≥ 3 routes to abliterated model; intensity 3/4/5 each get progressive explicit system prompt directives
  - Creative agent system prompt: replaced single-line NSFW note with full content policy including LoRA awareness
  - Deployed: EoBQ, dashboard, and agents all rebuilt/restarted on WORKSHOP/FOUNDRY
- **LiteLLM routes now 15** (was 14): added `uncensored`
- **PuLID Reference Library** — full face-injection pipeline:
  - `/references` page in EoBQ: add personas (queens/custom), upload photos, generate with likeness
  - Storage: VAULT `/mnt/vault/appdata/eoq-references/` (NFS-backed, survives node reboots)
  - ComfyUI: `flux-pulid-portrait.json` workflow with all PuLID nodes + uncensored LoRA
  - Creative agent: `list_personas` + `generate_with_likeness` tools — say "use the likeness of X" in chat
  - LTX Desktop: confirmed real (released 2026-03-06), but requires 32GB VRAM hard gate — 5090 barely hits minimum, not worth it yet. Watch for NSFW LoRA maturity.

### Next Actions
1. Set up Continue.dev on DEV → FOUNDRY:8000 (highest-ROI action from Session 44 research)
2. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py`
3. Wire `QdrantNeo4jRetriever` into agent context pipeline
4. Add freshness metadata (`content_hash`, `embedded_at`) to Qdrant ingestion pipeline
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298
8. EoBQ: adult performer digital replicas (PuLID + reference photos, deferred from this plan)

## Session 45 (2026-03-09) Summary

### Completed This Session
- **Dashboard deep audit** — all 24 pages, 20+ API routes, agent server endpoints reviewed. 3 bugs found + fixed:
  - Gallery generate button sent string template name; API now supports built-in Flux workflows (character/scene)
  - Mobile nav missing `/workplanner` entry — added with CalendarIcon
  - `config.ts` stale model names in inferenceBackends + gpuWorkloads — corrected
- **FOUNDRY huge pages** — `vm.nr_hugepages=16384` (32GB), persisted to `/etc/sysctl.d/99-hugepages.conf`
- **Model copy to local NVMe** — Qwen3.5-27B-FP8 (29GB) + Huihui-Qwen3-8B (16GB) → FOUNDRY `/mnt/local-fast/models/`. Cold start 6× faster (40s vs ~4min from NFS)
- **FOUNDRY compose updated** — volume mount now `/mnt/local-fast/models:/models:ro`. Both coordinator + utility loading from local NVMe
- **VAULT share configs** — 4 shares (models, data, appdata, ai-models) set to 500GB min free space (`shareFloor="524288000"`)
- **cpu-offload-gb REVERTED** — attempted on both nodes; incompatible with `--enable-prefix-caching` + MTP speculation in vLLM v0.16.1rc1 nightly (PR #18298 assertion). Removed cleanly. MTP speculation preserved on coordinator.
- **All 4 vLLM containers healthy** — coordinator:8000 ✅, utility:8002 ✅, workshop:8000 ✅

### Key Findings
- `docker compose restart` ≠ `docker compose up -d` — restart reuses stored container config, doesn't re-read compose file. Always use `up -d` for config changes.
- vLLM nightly v0.16.1rc1 `--cpu-offload-gb` incompatible with `--enable-prefix-caching` (and MTP). Watch for fix in future nightly. Track vLLM/18298.
- FOUNDRY `/mnt/local-fast` (1TB Gen4 NVMe) now has both models. 930GB → 885GB free. NFS load time eliminated.

### Next Actions
1. Set up Continue.dev on DEV → FOUNDRY:8000 (highest-ROI action from Session 44 research)
2. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py`
3. Wire `QdrantNeo4jRetriever` into agent context pipeline
4. Add freshness metadata (`content_hash`, `embedded_at`) to Qdrant ingestion pipeline
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

---

*Last updated: 2026-03-09 02:10 PDT
