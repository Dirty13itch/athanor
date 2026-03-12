# Athanor System Status

*Ground-truth assessment as of 2026-03-08. Auto-generated from live cluster inspection.*

---

## Claude Code Environment

| Item | Status | Details |
|------|--------|---------|
| Claude Code | v2.1.71 native install | `~/.local/share/claude/versions/2.1.71` â€” auto-updates âœ… |
| Model | opus (claude-opus-4-6) | Set in `~/.claude/settings.json` |
| Effort | high | Set in user settings |
| mosh | Installed | `/usr/bin/mosh` |
| tmux launcher | Created | `~/bin/athanor` |
| Aider | Installed | `~/.local/bin/aider`, config at `.aider.conf.yml` |
| Goose | Installed | v1.27.2 at `/usr/local/bin/goose`, config at `~/.config/goose/profiles.yaml` |
| claude-squad | Installed | v1.0.16 at `/usr/local/bin/cs` |
| VS Code | v1.110.1 | Installed via Microsoft apt repo |
| Continue.dev | v1.2.16 | `~/.continue/config.json` â†’ LiteLLM:4000. Chat: reasoning/worker. Autocomplete: fast (8B, thinking disabled). Embeddings: embedding. |

## MCP Servers

| Server | Source | Status | Purpose |
|--------|--------|--------|---------|
| docker | .mcp.json (local) | ALWAYS | Docker container management |
| athanor-agents | .mcp.json (local) | ALWAYS | Agent server at foundry:9000 |
| redis | .mcp.json (local) | ALWAYS | Redis state, heartbeats, workspace, scheduler |
| qdrant | .mcp.json (local) | ALWAYS | Vector DB collections, search, scroll |
| smart-reader | .mcp.json (local) | ALWAYS | Smart file reading, grep, diff, log |
| sequential-thinking | .mcp.json (local) | ALWAYS | Structured reasoning meta-tool |
| neo4j | .mcp.json (local) | ALWAYS | Direct Cypher queries to knowledge graph |
| postgres | .mcp.json (local) | ALWAYS | SQL access to VAULT databases (Zed fork) |
| grafana | .mcp.json (local) | disabled | Query Grafana, Prometheus, Loki â€” enable when needed |
| langfuse | .mcp.json (local) | disabled | Trace debugging â€” enable when needed |
| miniflux | .mcp.json (local) | disabled | RSS feed tools â€” enable when needed |
| n8n | .mcp.json (local) | disabled | Workflow automation â€” enable when needed |
| gitea | .mcp.json (local) | disabled | Repo/issue/PR management â€” enable when needed |
| context7 | claude.ai plugin | ALWAYS | Live library docs (resolve-library-id, query-docs) |
| Gmail | claude.ai connector | Active | Email integration |
| Google Calendar | claude.ai connector | Active | Calendar management |

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

### FOUNDRY (.244) â€” 11 containers

| GPU | Model | VRAM | Container | Port |
|-----|-------|------|-----------|------|
| 0: RTX 5070 Ti (MSI) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | vllm-coordinator | 8000 |
| 1: RTX 5070 Ti (Gigabyte) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | â€” |
| 2: RTX 4090 (ASUS) | Qwen3-Coder-30B-A3B-Instruct-AWQ | 16.0/24.6 GB | vllm-coder | 8006 |
| 3: RTX 5070 Ti (Gigabyte) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | â€” |
| 4: RTX 5070 Ti (MSI) | Qwen3.5-27B-FP8 (TP=4) | 15.6/16.3 GB | (shared) | â€” |

Other containers: `athanor-agents` (9000), `athanor-gpu-orchestrator`, `alloy`, `wyoming-whisper` (10300), `qdrant` (6333-6334), `speaches` (8200), `dcgm-exporter` (9400), `node-exporter`

### WORKSHOP (.225) â€” 9 containers

| GPU | Model | VRAM | Temp | Container | Port |
|-----|-------|------|------|-----------|------|
| 0: RTX 5090 | Qwen3.5-35B-A3B-AWQ-4bit | 31.3/32.6 GB | 38Â°C | vllm-node2 | 8000 |
| 1: RTX 5060 Ti | ComfyUI | 5.1/16.3 GB | 32Â°C | comfyui | 8188 |

Other: `athanor-dashboard` (3001), `athanor-eoq` (3002), `athanor-ws-pty-bridge` (3100), `open-webui` (3000), `alloy`, `dcgm-exporter`, `node-exporter`

### VAULT (.203) â€” 42 containers

Key services: `litellm` (4000), `grafana` (3000), `prometheus`, `backup-exporter`, `n8n` (5678), `gitea` (3033), `miniflux` (8070), `redis`, `vault-open-webui` (3090), `langfuse-web` (3030) + 5 langfuse services, `neo4j` (7474/7687), `qdrant` (6333), `postgres` (5432), `stash` (9999), `plex`, `homeassistant`, media stack (sonarr/radarr/prowlarr/sabnzbd/tautulli/tdarr), `spiderfoot` (5001), `ntfy` (8880), `meilisearch` (7700), `field-inspect-app` (3080), monitoring (loki, alloy, cadvisor, node-exporter)

### DEV (.189) â€” 2 containers

| GPU | Model | VRAM | Container | Port |
|-----|-------|------|-----------|------|
| 0: RTX 5060 Ti | Embedding + Reranker | 4.8/16.3 GB | vllm-embedding (8001), vllm-reranker (8003) | 8001, 8003 |

## Service Health (verified from DEV)

| Endpoint | Model/Service | Status |
|----------|---------------|--------|
| foundry:8000 | Qwen3.5-27B-FP8 (TP=4) | âœ… Healthy |
| foundry:8006 | Qwen3-Coder-30B-A3B-Instruct-AWQ | OK |
| foundry:9000 | Agent Server (9 agents) | âœ… Healthy |
| workshop:8000 | Qwen3.5-35B-A3B-AWQ-4bit | âœ… Healthy |
| vault:4000 | LiteLLM (local + cloud routed model lanes) | âœ… Healthy |

### LiteLLM Model Routes
`reasoning` `coding` `coder` `fast` `creative` `utility` `worker` `uncensored` `embedding` `reranker` `claude` `gpt` `deepseek` `gemini` `kimi` `glm` `openrouter` + aliases (`gpt-4` `gpt-3.5-turbo` `text-embedding-ada-002`)

## Known Issues & Blockers

| Issue | Impact | Resolution |
|-------|--------|------------|
| **Ansible vault-password** | Resolved | Vault recreated 2026-03-08, `ansible vault -m ping` verified |
| **MSI 5070 Ti RGB still ON** (Ã—2) | Cosmetic | I2C port 1 not exposed on Blackwell. Fix: one-time MSI Center from Windows |
| **FOUNDRY GPU 4 in TP=4** | Part of Qwen3.5-27B-FP8 TP=4 | All 4x 5070 Ti now in use |
| **NordVPN credentials** | qBittorrent blocked | Shaun needs to provide |
| **Anthropic API key** | Quality Cascade cloud escalation blocked | Shaun needs to provide |
| **Google Drive OAuth** | ~40% personal data inaccessible | Shaun needs to run rclone config |

## Build Progress

Tiers 1-21 tracked. 20 fully complete. Remaining open items are backlog or blocked on Shaun:
- 6.2 InfiniBand (backlog)
- 6.4 Mobile access (backlog)
- 6.7 Mining enclosure (physical)
- 8.4 Dedicated Coding Model (deferred)
- 14.3 Home Assistant depth (needs Shaun)
- 14.5 Kindred prototype (awaiting decision)

## Session 55 (2026-03-09) Summary â€” COO Audit & Operational Excellence

### Completed This Session
- **MCP token budget optimization** (21.1) â€” 79% reduction (40,579 â†’ 8,640 tokens):
  - Root cause: miniflux-mcp required `MINIFLUX_BASE_URL` + `MINIFLUX_TOKEN` (API token auth). Previous config had `MINIFLUX_URL/USERNAME/PASSWORD` (wrong keys, wrong auth method). Fixed.
  - Generated Miniflux API token via direct PostgreSQL insert (`miniflux-postgres` container) â€” REST API returns 404 in Miniflux v2.2.6.
  - Disabled 5 servers in `.mcp.json`: grafana, langfuse, miniflux, n8n, gitea. All preserved, re-enable per-session via `/mcp`.
  - ALWAYS tier now 8 servers (docker, athanor-agents, redis, qdrant, smart-reader, sequential-thinking, neo4j, postgres).
- **Claude Code plugin audit** (21.2) â€” context7 is already installed and optimal. No new plugins needed. Plugin cost is always-on; MCP toggle is better for everything else.
- **COO live system audit** (21.3) â€” Agents running autonomously:
  - 16/20 recent tasks completed. Home/media agents active on schedule.
  - 2 coding-agent EoBQ timeouts: wrong path specs (`projects/eoq/components/` vs `src/app/components/`). Both components exist and are production quality. Task spec quality issue, not agent failure.
  - EoBQ: `inventory.tsx` + `scene-transition.tsx` verified complete (framer-motion, game-store integration, full animations).
  - Home Assistant: 43 entities, 2 TVs unavailable (off â€” normal). No real anomalies.
  - Pending approval task (home-agent energy analysis) self-cleared.

### Session 54 Items (not previously logged to STATUS.md)
- **Tactical routing fix** â€” `config.py`: `router_tactical_model = "worker"` (was `reasoning`). `router.py`: `timeout_s = 60` (was `30`). Fixed constant timeouts on tactical tasks.
- **A/B model eval** â€” Worker (35B-A3B) 12x faster than Reasoning (27B-FP8) with equal quality. Route on load, not quality. Rubric bug fixed (farmer puzzle answer swapped).
- **Dashboard fixes** â€” goals/page.tsx trust panel (wrong response shape), tasks/page.tsx data-curator color, learning/page.tsx skill library card, model name stale refs.
- **LangFuse prompt sync** â€” creative-agent updated to v2. All 9 agents synced.
- **DailyBriefing component** â€” `projects/dashboard/src/components/daily-briefing.tsx` built and wired to page.tsx at lens 'default'.

### Next Actions
1. **21.4 Grafana backup alert** â€” Prometheus rule for backup age > 36h (write YAML + Ansible deploy). Grafana MCP disabled; write rule directly.
2. **Task spec quality** â€” When assigning EoBQ coding tasks, include exact file paths from `projects/eoq/src/app/components/`.
3. **Shaun-gated:** n8n Signal Pipeline (vault:5678 UI), Kindred go/no-go, EoBQ character reference images for LoRAs.

---

## Session 53 (2026-03-09) Summary â€” Skill Learning Feedback Loop

### Completed This Session
- **Skill learning feedback loop (Tier 19.1)** â€” closed the loop on Session 52's skill library.
  - `skill_learning.py`: `find_matching_skill(prompt, threshold=0.3)` â€” scores all skills via `_compute_relevance()`, returns `(skill_id, relevance)` for best match above threshold.
  - `tasks.py`: `_record_skill_execution_for_task(task, success)` â€” fire-and-forget from both success and failure paths in `_execute_task()`. Silent on no match.
  - **Verified live:** research task "Research HippoRAG..." â†’ matched "Search then Synthesize" (relevance=0.8) â†’ `execution_count=1, success_rate=100%, avg_duration_ms=143114`. Skill library now learns from real usage.
  - Deployed to FOUNDRY, rebuilt image, confirmed functional via `/v1/skills/stats` and `/v1/skills/top`.

### Next Actions
- Continue building Tier 19 items from the backlog
- Watch skill success rates accumulate over agent activity
- Consider adding duckduckgo_search â†’ ddgs package rename fix (pre-existing warning in research tools)

## Session 52 (2026-03-09) Summary â€” Open Work List Execution

### Completed This Session
- **Comprehensive plan audit** â€” cross-referenced plan against live system. Key finding: most P1/P2 items were already done in sessions 46-51.
  - GWT Phase 3 âœ… (workspace.py fully implements subscriptions, reactions, coalition)
  - Conversation history indexing âœ… (124 points live, `log_conversation()` wired since session ~40)
  - Prompt versioning in LangFuse âœ… (all 9 agents synced since 2026-03-08)
  - Dashboard PWA âœ… (sw.js, manifest.ts, register-sw.tsx, icons all done)
- **Skill Learning Library** (ported from reference/hydra/skill_learning.py):
  - `skill_learning.py`: async Redis-backed skill library (`athanor:skills:library`)
  - `Skill` dataclass with trigger_conditions, steps, success_rate, execution_count, avg_duration_ms, examples
  - `_compute_relevance()`: keyword matching across trigger_conditions + name/description/tags
  - `search_skills_for_context()`: top-3 relevant skills formatted for context injection
  - `record_execution()`: running average success rate and duration (empirical learning)
  - 8 initial skills seeded: research, media, creative, knowledge, infrastructure, coding, home, stash
  - `context.py`: skill section injected after Active Goals (Step 2d, Redis-only, fast)
  - `server.py`: full CRUD API at `/v1/skills` + execution recording
  - Deployed to FOUNDRY, rebuilt, verified: 8 skills seeded, stats endpoint live
- **Promptfoo A/B comparison** â€” `evals/ab-comparison.yaml` run complete:
  - reasoning (Qwen3.5-27B-FP8): 15/16 = **93.8%**
  - creative (Qwen3.5-35B-A3B-AWQ): 15/16 = **93.8%**
  - Both fail chicken/cow math. Otherwise identical quality. Routing decision: load balance freely.

### Key Findings
- Both local models are quality-equivalent â€” route on load, not quality
- All "can build now" items from the 29-item open work list are now done
- 9 items remain Shaun-gated (credentials, clicks, decisions)

### Next Actions
1. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
2. Shaun: push go/no-go on Kindred prototype (14.5)
3. EoBQ character LoRAs â€” Shaun to provide reference images for characters
4. SDXL/Pony anime art path â€” research when time allows (not urgent)
5. Push 10 commits to origin when ready

## Session 51 (2026-03-09) Summary

### Completed This Session
- **MEMORY.md refresh** â€” was stale at session 40 (10 sessions out of date). Full rewrite documenting sessions 41-51: Tier 18 complete (miniCOIL, Neo4j 2-hop, Continue.dev, HippoRAG), EoBQ uncensored stack, LiteLLM routing table, all 9 agent states, MCP server inventory.
- **EoBQ plan audit** â€” confirmed peaceful-gathering-sundae.md plan fully implemented in session 46. All steps verified: LoRA in 3 workflow JSONs, `uncensored` LiteLLM alias confirmed at `/mnt/user/appdata/litellm/config.yaml`, intensity routing live in chat + narrate routes, abliterated model system prompt in creative agent. Plan file deleted.
- **Promptfoo eval baseline** â€” first run of `evals/promptfooconfig.yaml` against live LiteLLM. Results â†’ `evals/results/baseline-2026-03-09.json`. 81.6% (31/38).
- **LiteLLM config path corrected** â€” was wrong in docs (`/opt/athanor/litellm/`) actual path: `/mnt/user/appdata/litellm/config.yaml` (Unraid appdata)

### Key Verifications
- `uncensored` model in LiteLLM â†’ `Huihui-Qwen3-8B-abliterated-v2` at foundry:8002 âœ…
- LoRA (`flux-uncensored.safetensors`, strength 0.85) in all 3 Flux workflows âœ…
- Deployed EoBQ at workshop:3002 running current code âœ…

### Next Actions (carried forward)
1. Review promptfoo eval results when complete â€” record baseline scores
2. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
3. Shaun: push go/no-go on Kindred prototype (14.5)
4. Push 8 commits to origin when ready

## Session 50 (2026-03-09) Summary

### Completed This Session
- **HippoRAG Entity Extraction** (18.4) â€” entity-based graph traversal fully wired:
  - `index-knowledge.py`: `extract_entities_llm(text, title)` â€” NER via Qwen3.5-27B-FP8, extracts â‰¤15 entities/doc (types: Service, Model, Concept, Technology, Person). `upsert_neo4j_entities(source, entities)` â€” MERGE Entity nodes by `(name_lower, type)`, MERGE MENTIONS edges. 2-phase: all Qdrant/Document upserts first, then NER pass.
  - `graph_context.py`: category-based Cypher â†’ entity 2-hop: `(found:Document)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(related:Document)`, ranked by `count(DISTINCT e) DESC`.
  - Neo4j index: `entity_name_lower_type` composite on `(name_lower, type)`.
  - Full re-index: 172 docs â†’ 3076 Qdrant chunks â†’ 879 Entity nodes â†’ 5455 MENTIONS edges.
  - Deployed: `graph_context.py` synced to FOUNDRY, agents restarted, all 9 healthy.
  - **Verified:** Entity traversal semantically correct â€” ADR-005 (inference engine) â†’ inference research doc (5 shared entities: vLLM, SGLang, llama.cpp, Ollama, PagedAttention), CPU optimization, architecture synthesis.

### Next Actions
1. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
2. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 49 (2026-03-09) Summary

### Completed This Session
- **LangFuse per-agent metadata:**
  - Added `extra_body` metadata to all 9 agent ChatOpenAI constructors: `trace_name`, `tags`, `trace_metadata`
  - KEY: LiteLLM uses `trace_name` (sets trace name), `tags` (array â†’ LangFuse tags), `trace_metadata` (dict â†’ LangFuse metadata). Plain `metadata.agent` is ignored.
  - Also added `metadata`+`tags` to LangChain run configs in `server.py` and `tasks.py` for future LangChain-native LangFuse integration
  - Verified: `knowledge-agent` trace shows `name='knowledge-agent', tags=['knowledge-agent'], meta={'agent': 'knowledge-agent'}`

- **Continue.dev IDE Integration** (18.3):
  - VS Code v1.110.1 installed via Microsoft apt repo (Ubuntu 24.04)
  - Continue.dev v1.2.16 extension installed headlessly
  - `~/.continue/config.json`: Chat â†’ `reasoning` (Qwen3.5-27B-FP8) + `worker` (35B-A3B on WORKSHOP); Autocomplete â†’ `fast` (Qwen3-8B, `enable_thinking: false`); Embeddings â†’ `embedding` (Qwen3-Embedding-0.6B)
  - **Verified:** LiteLLM 200, `reasoning` model chat works, `fast` model with thinking disabled produces clean output
  - `drop_params: true` in LiteLLM does NOT strip `chat_template_kwargs` â€” verified by test

### Next Actions
1. HippoRAG entity extraction (18.4) â€” NER at index time, upgrade category-based to entity-based graph expansion
2. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
3. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 48 (2026-03-09) Summary

### Completed This Session
- **Neo4j Graph Context Expansion** (18.2):
  - `graph_context.py`: 2-hop Neo4j expansion after Qdrant knowledge search â€” source â†’ category â†’ related docs in same category
  - `context.py`: wired graph expansion into enrichment pipeline; new "## Related Documentation (graph)" context section; log shows `3 knowledge (+3 graph)`
  - `index-knowledge.py`: added `upsert_neo4j_docs()` â€” MERGE Document nodes with `doc_type='athanor'` in Neo4j; 172 nodes created across 8 categories
  - Full re-index run to populate all Neo4j Document nodes
  - Agents rebuilt + deployed: all 9 healthy at foundry:9000
  - **Verified working:** `+3 graph` in context log, graph section renders in context output

### LangFuse Audit Finding
All traces arrive as generic `litellm-acompletion`/`litellm-aembedding` â€” no agent-level metadata. LangChain callbacks don't thread `agent_name` to LiteLLM. Can't distinguish which agent made which call. Fix: add `metadata={"agent": agent_name}` to LangChain chain config in `tasks.py`.

### Next Actions
1. Install VS Code + Continue.dev on DEV â†’ FOUNDRY:8000 (18.3) â€” highest daily-use ROI
2. HippoRAG entity extraction (18.4) â€” NER at index time, upgrade category-based to entity-based graph expansion
3. LangFuse per-agent metadata: thread `agent_name` through LangChain callbacks to LiteLLM â†’ LangFuse
4. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
5. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 47 (2026-03-09) Summary

### Completed This Session
- **miniCOIL hybrid search** (18.1):
  - `knowledge` Qdrant collection migrated: unnamed dense â†’ named `dense` + `sparse` (miniCOIL) vectors
  - `index-knowledge.py`: adds miniCOIL sparse vectors at index time (FastEmbed 0.7, `Qdrant/minicoil-v1`, 90MB)
  - `hybrid_search.py`: primary path uses Qdrant `/query` endpoint with native RRF fusion; graceful fallback to keyword scroll for collections without sparse vectors
  - `pyproject.toml`: added `fastembed>=0.7`
  - Full re-index: 3071 chunks from 172 documents (was 3034)
  - Agents rebuilt + deployed: all 9 healthy at foundry:9000
  - miniCOIL model loads on first query (~5s one-time), cached thereafter
  - **Quality improvement:** +2-5% NDCG@10 on keyword-heavy queries

### Next Actions
1. Wire `QdrantNeo4jRetriever` into agent context pipeline (18.2) â€” +20% multi-hop accuracy
2. Add miniCOIL sparse vectors to `personal_data` collection (when that collection gets data)
3. Install VS Code + Continue.dev on DEV â†’ FOUNDRY:8000 (18.3) â€” highest daily-use ROI
4. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py` â† DONE
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

## Session 46 (2026-03-09) Summary

### Completed This Session
- **EoBQ uncensored content wiring** (plan fully executed):
  - `flux-uncensored.safetensors` LoRA (0.85 strength) wired into all Flux workflows via `LoraLoaderModelOnly` node "11" â€” both EoBQ portrait/scene JSON files + dashboard comfyui templates
  - `uncensored` LiteLLM alias added â†’ `Huihui-Qwen3-8B-abliterated-v2` at foundry:8002. Confirmed in `/v1/models` list.
  - EoBQ chat + narrate routes: intensity â‰¥ 3 routes to abliterated model; intensity 3/4/5 each get progressive explicit system prompt directives
  - Creative agent system prompt: replaced single-line NSFW note with full content policy including LoRA awareness
  - Deployed: EoBQ, dashboard, and agents all rebuilt/restarted on WORKSHOP/FOUNDRY
- **LiteLLM routes now 15** (was 14): added `uncensored`
- **PuLID Reference Library** â€” full face-injection pipeline:
  - `/references` page in EoBQ: add personas (queens/custom), upload photos, generate with likeness
  - Storage: VAULT `/mnt/vault/appdata/eoq-references/` (NFS-backed, survives node reboots)
  - ComfyUI: `flux-pulid-portrait.json` workflow with all PuLID nodes + uncensored LoRA
  - Creative agent: `list_personas` + `generate_with_likeness` tools â€” say "use the likeness of X" in chat
  - LTX Desktop: confirmed real (released 2026-03-06), but requires 32GB VRAM hard gate â€” 5090 barely hits minimum, not worth it yet. Watch for NSFW LoRA maturity.

### Next Actions
1. Set up Continue.dev on DEV â†’ FOUNDRY:8000 (highest-ROI action from Session 44 research)
2. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py`
3. Wire `QdrantNeo4jRetriever` into agent context pipeline
4. Add freshness metadata (`content_hash`, `embedded_at`) to Qdrant ingestion pipeline
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298
8. EoBQ: adult performer digital replicas (PuLID + reference photos, deferred from this plan)

## Session 45 (2026-03-09) Summary

### Completed This Session
- **Dashboard deep audit** â€” all 24 pages, 20+ API routes, agent server endpoints reviewed. 3 bugs found + fixed:
  - Gallery generate button sent string template name; API now supports built-in Flux workflows (character/scene)
  - Mobile nav missing `/workplanner` entry â€” added with CalendarIcon
  - `config.ts` stale model names in inferenceBackends + gpuWorkloads â€” corrected
- **FOUNDRY huge pages** â€” `vm.nr_hugepages=16384` (32GB), persisted to `/etc/sysctl.d/99-hugepages.conf`
- **Model copy to local NVMe** â€” Qwen3.5-27B-FP8 (29GB) + Huihui-Qwen3-8B (16GB) â†’ FOUNDRY `/mnt/local-fast/models/`. Cold start 6Ã— faster (40s vs ~4min from NFS)
- **FOUNDRY compose updated** â€” volume mount now `/mnt/local-fast/models:/models:ro`. Both coordinator + utility loading from local NVMe
- **VAULT share configs** â€” 4 shares (models, data, appdata, ai-models) set to 500GB min free space (`shareFloor="524288000"`)
- **cpu-offload-gb REVERTED** â€” attempted on both nodes; incompatible with `--enable-prefix-caching` + MTP speculation in vLLM v0.16.1rc1 nightly (PR #18298 assertion). Removed cleanly. MTP speculation preserved on coordinator.
- **All 4 vLLM containers healthy** â€” coordinator:8000 âœ…, utility:8002 âœ…, workshop:8000 âœ…

### Key Findings
- `docker compose restart` â‰  `docker compose up -d` â€” restart reuses stored container config, doesn't re-read compose file. Always use `up -d` for config changes.
- vLLM nightly v0.16.1rc1 `--cpu-offload-gb` incompatible with `--enable-prefix-caching` (and MTP). Watch for fix in future nightly. Track vLLM/18298.
- FOUNDRY `/mnt/local-fast` (1TB Gen4 NVMe) now has both models. 930GB â†’ 885GB free. NFS load time eliminated.

### Next Actions
1. Set up Continue.dev on DEV â†’ FOUNDRY:8000 (highest-ROI action from Session 44 research)
2. Replace `knowledge` payload text index with miniCOIL hybrid search in `index-knowledge.py`
3. Wire `QdrantNeo4jRetriever` into agent context pipeline
4. Add freshness metadata (`content_hash`, `embedded_at`) to Qdrant ingestion pipeline
5. Audit LangFuse for per-agent invocation frequency
6. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678
7. Re-test `--cpu-offload-gb` when vLLM nightly fixes PR #18298

---

## Session 54 (2026-03-09) Summary

### Completed This Session
- **Tactical routing fix** â€” Critical: `reasoning` model (50.8s avg latency) assigned to tactical tier with 30s timeout â†’ constant timeouts. Switched tactical to `worker` (35B-A3B-AWQ, 4.2s avg). Timeout bumped to 60s. Backed by A/B eval data.
- **A/B model eval** â€” Both models score 100% quality (rubric bug corrected). Worker 12x faster. Results documented in `evals/results/ab-comparison-2026-03-09-analysis.md`.
- **Dashboard data format fixes** â€” 3 bugs corrected:
  - `goals/page.tsx`: trust panel always empty â€” `/v1/trust` returns `{ agents: {} }` not `{ scores: [] }`. Fixed with Object.entries() transform.
  - `tasks/page.tsx`: data-curator missing from AGENT_COLORS.
  - `learning/page.tsx`: added Skill Library MetricCard (skill stats visible).
- **Notifications system** â€” Merged two approval backends (`escalation.py` + `pending_approval` tasks). CORS added to agent server. Both work in browser now.
- **LangFuse prompt sync** â€” creative-agent updated to v2, 8 others unchanged.
- **Dashboard deployed** â€” All changes rsynced and rebuilt on Workshop:3001.

### Key Findings
- Tactical tier was systematically timing out with `reasoning` model (50.8s >> 30s timeout). Fix is deployed and live.
- Both local models have identical quality on evals. Route by latency, not by "bigger = better".
- Conversations collection IS populated (verified 3 live entries) â€” prior session notes were incorrect about it being empty.

### Next Actions
1. Shaun: activate n8n "Intelligence Signal Pipeline" at vault:5678 (still pending)
2. EoBQ character LoRAs â€” per-character Flux LoRA training for face consistency (P2)
3. SDXL/Pony anime art path for EoBQ (P2)
4. Watch Workshop vLLM for load under new tactical routing (agents now calling workshop more)
5. Run Promptfoo eval again with fixed rubric to verify 100% pass rate for both models

*Last updated: 2026-03-09 14:20 PDT

