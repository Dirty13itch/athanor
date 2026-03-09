# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-03-09 (Session 51: Plan audit + MEMORY.md refresh)

### What happened
- Verified EoBQ uncensored content plan (peaceful-gathering-sundae.md) is **fully implemented** — all steps done in session 46-47
- Confirmed: LoRA in all 3 workflow JSONs, "uncensored" LiteLLM alias live, intensity routing in chat + narrate, abliterated model system prompt in creative agent
- LiteLLM `uncensored` → Huihui-Qwen3-8B-abliterated-v2 at foundry:8002 verified via curl
- Updated MEMORY.md (was stale at session 40, now current through session 51)

### Current blockers
- NordVPN credentials → qBittorrent
- Anthropic API key → Quality Cascade cloud escalation
- Google Drive rclone OAuth → Personal data ~40% (10.8)
- Photo Analysis → Qwen3.5 multimodal + vLLM 0.17+ (10.10)
- n8n workflow activation → Shaun must click Activate at vault:5678
- 14.3 HA depth → Shaun must configure Lutron + UniFi in HA
- 14.5 Kindred → awaiting Shaun's go decision

### What's next (priority order)
1. **Run promptfoo eval baseline** — evals/ dir exists with promptfooconfig.yaml, never executed; run against live LiteLLM
2. **Tier 19 planning** — system has grown significantly, time to define next capability tier
3. **Push 8 commits** — branch is 8 ahead of origin (knowledge pipeline, HippoRAG, LangFuse metadata, Continue.dev)
4. **Kindred** (14.5) — blocked on Shaun's go decision
5. **n8n signal pipeline activation** — Shaun: visit vault:5678, activate "Intelligence Signal Pipeline"

### Git state
- Branch: main
- 8 commits ahead of origin (not pushed)
- Latest: `e5e9017` ops: insights-driven CLAUDE.md improvements + doc-ref checker

---

## Sessions 41-51: What Happened (2026-03-08 to 2026-03-09)

| Session | Focus | Key Outcomes |
|---------|-------|-------------|
| 41 | Tier 16 — remaining items, DEEP-RESEARCH-LIST reconciliation | All Tier 16 complete |
| 42 | Stale doc sweep, session health hook, FOUNDRY heartbeat fixes | Briefing API corrected |
| 43 | MCP expansion (4 new: neo4j, postgres, gitea, sequential-thinking), self-improvement loop closed | 10→13 MCP servers |
| 43b | Goals & Feedback page, circuit breakers, hybrid autonomy, ntfy notifications | 9 agents with autonomy |
| 44 | Session 44 research synthesis, trust loop, creative model routing | Work Planner dashboard page |
| 45 | Dashboard audit (3 bugs fixed), Insights page (pattern detection UI), hardware optimization | 24 dashboard pages |
| 46 | EoBQ uncensored content wiring: LoRA + abliterated model routing + intensity directives | EoBQ fully uncensored |
| 46b | PuLID reference library: face injection for custom personas at workshop:3002/references | EoBQ PuLID complete |
| 47 | miniCOIL hybrid search: neural sparse vectors + Qdrant RRF (18.1) | Hybrid retrieval live |
| 48 | Neo4j 2-hop graph context expansion for knowledge agent (18.2) | Category-based traversal |
| 49 | Continue.dev IDE integration (18.3), per-agent LangFuse metadata on all 9 agents | Local autocomplete |
| 50 | HippoRAG entity extraction (18.4): 879 entities, 5455 MENTIONS edges, entity 2-hop traversal | Knowledge graph complete |
| 50b | Insights-driven CLAUDE.md improvements, doc-ref checker script | Anti-patterns expanded |
| 51 | Plan audit, MEMORY.md refresh | (this session) |

---

## Current System State (verified 2026-03-09)

### Cluster (nodes healthy, all services up)
- **FOUNDRY .244**: vllm-coordinator (Qwen3.5-27B-FP8 TP=4 on GPUs 0,1,3,4 :8000), vllm-utility (Huihui-Qwen3-8B on GPU2/4090 :8002). 11 containers.
- **WORKSHOP .225**: Qwen3.5-35B-A3B-AWQ on 5090 (GPU0) :8000. ComfyUI on 5060Ti. Dashboard:3001, EoBQ:3002, Open WebUI:3000, Ulrich Energy:3003.
- **VAULT .203**: 42+ containers. LiteLLM:4000, LangFuse:3030, Open WebUI:3090, Redis:6379, Qdrant:6333, Neo4j:7474. Storage 86% (141T/164T).
- **DEV .189**: Embedding:8001 + Reranker:8003. Claude Code native install.

### LiteLLM Routing (at VAULT:4000)
- `reasoning` → Qwen3.5-27B-FP8 at foundry:8000
- `fast` → Huihui-Qwen3-8B-abliterated-v2 at foundry:8002
- `uncensored` → Huihui-Qwen3-8B-abliterated-v2 at foundry:8002 (EoBQ adult content)
- `utility` → Huihui-Qwen3-8B-abliterated-v2 at foundry:8002
- `creative` → Qwen3.5-35B-A3B-AWQ at workshop:8000
- `coding` → Qwen3.5-27B-FP8 at foundry:8000
- `worker` → Qwen3.5-35B-A3B-AWQ at workshop:8000
- `embedding` → Qwen3-Embedding-0.6B at dev:8001
- `reranker` → Qwen3-Reranker-0.6B at dev:8003

### Knowledge System (Tier 18 complete)
- **18.1 miniCOIL hybrid search**: Neural sparse vectors via FastEmbed, Qdrant RRF fusion, SPLADE-style retrieval
- **18.2 Neo4j 2-hop graph context**: Category-based traversal in graph_context.py — finds related docs via shared category
- **18.3 Continue.dev**: IDE local inference autocomplete via vLLM OpenAI-compat API
- **18.4 HippoRAG entity extraction**: LLM NER at index time → 879 Entity nodes in Neo4j, 5455 MENTIONS edges, entity 2-hop traversal in retrieval (replaces category-based)
- **Neo4j schema**: Document nodes, Entity nodes (Service/Model/Concept/Technology/Person), MENTIONS edges, `entity_name_lower_type` composite index
- **Qdrant collections**: knowledge, conversations, signals, activity, preferences, implicit_feedback, events, llm_cache, eoq_characters (9 total)

### EoBQ (Empire of Broken Queens) — Fully Deployed
- URL: workshop:3002. Dark fantasy interactive fiction.
- 5 characters with emotional profiles, breaking mechanics, content_intensity 1-5
- **LoRA**: `flux-uncensored.safetensors` (strength 0.85) in all 3 Flux workflows (portrait, scene, PuLID)
- **Model routing**: intensity >= 3 → `uncensored` (Huihui abliterated), intensity 1-2 → `reasoning`
- **PuLID reference library**: face injection for custom personas at /references page
- Intensity directives: 5 tiers (suggestive → absolute) in both chat and narrate routes

### MCP Servers (13 total)
- **Original (6):** grafana, docker, athanor-agents, redis, qdrant, smart-reader
- **Tier 1 (4):** sequential-thinking, neo4j (mcp-neo4j-cypher), postgres (Zed fork), gitea (Go binary)
- **Tier 2 (3):** langfuse, miniflux, n8n

### Dashboard (24 pages)
Furnace Home, System, Agents, Command Center, Media, Data, Signals, Knowledge, Goals, Insights, Work Planner, Learning, Reasoning, EoBQ hub + game + gallery + portraits + references, Kindred, Ulrich Energy

### Agents (9, all deployed on FOUNDRY:9000)
All 9 have: per-agent LangFuse metadata tags, proactive schedules (5:30AM cycle), circuit breakers, hybrid autonomy.
- General, Research, Media, Home, Creative, Knowledge, Coding, Stash, Data Curator
- Self-improvement loop: 5:30AM benchmarks → pattern detection → proposals → Goals page

---

## Build State (as of 2026-03-09)

- **Tiers 1-18: COMPLETE** (Tier 16 done session 41, Tier 18 done session 50)
- **Open items**: 6.2/6.4/6.7 (physical backlog), 8.4 (deferred), 14.3 (blocked Shaun), 14.5 (awaiting decision)
- **Blocked on Shaun**: NordVPN, Anthropic API key, Google Drive OAuth, n8n activation, HA config
- **No Tier 19 defined yet** — natural next candidates: promptfoo eval baseline, Kindred prototype, video NSFW pipeline, SDXL/Pony path for anime art

## Key Corrections Since Session 40

- MEMORY.md was 10 sessions stale — corrected in session 51
- LiteLLM config at `/mnt/user/appdata/litellm/config.yaml` (not `/opt/athanor/litellm/`)
- EoBQ uncensored plan (peaceful-gathering-sundae.md) completed in session 46, plan file now archived
- Tier 18 knowledge pipeline (18.1-18.4) all complete as of session 50
- HippoRAG entity traversal replaces category-based graph expansion (18.2 → 18.4 upgrade path)

## Patterns Learned

- Don't re-audit the cluster every session. Trust dated audits.
- MEMORY.md in repo has session state. ~/.claude/projects/.../memory/MEMORY.md has patterns.
- The MAP and DEEP-RESEARCH-LIST at ~/repos/ root are strategic docs from a 10hr planning session.
- Reference repos are READ-ONLY parts warehouses. Port algorithms, rewrite glue.
- LiteLLM config path on VAULT: `/mnt/user/appdata/litellm/config.yaml` (Unraid appdata, not /opt/)
- vault-ssh.py works for all VAULT commands. Direct ssh hangs on Unraid.
- GRAFANA_PASSWORD is "admin" (default, set in ~/.bashrc for MCP).
- git push origin main — branch 8 ahead. Push when Shaun says to.
