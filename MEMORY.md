# Athanor Session Memory

*Updated by Claude Code after each build session. Read this first to know where we left off.*

---

## Last Session: 2026-03-11 (Session 56: Backup alerting drift reconciliation)

### What happened
- Reconciled backup freshness monitoring drift across scripts, Ansible, and the tactical backlog.
- Fixed `scripts/backup-age-exporter.py`: emits both `type` and `target` labels, supports env-configured backup paths, defaults appdata to `/mnt/appdatacache/backups`, keeps legacy fallback paths for direct host runs.
- Fixed `ansible/roles/vault-grafana-alerts/`: exporter container now mounts qdrant, neo4j, and appdata backup directories explicitly. Removed dead VAULT textfile-collector deployment path.
- Fixed `scripts/backup-appdata.sh` default backup dir to `/mnt/appdatacache/backups` so source matches the Session 39 FUSE workaround.
- Added Prometheus `BackupExporterDown` rule to `ansible/roles/vault-monitoring/templates/alert-rules.yml.j2`.
- Verified locally: `python -m py_compile scripts/backup-age-exporter.py`; fixture run returned expected backup ages; WSL Ansible syntax check passed with explicit `ANSIBLE_ROLES_PATH`.

### Current blockers
- Live deploy of `playbooks/vault.yml --tags monitoring,alerts --limit vault` is blocked in this environment because `/home/shaun/athanor/ansible/vault-password` does not decrypt `ansible/group_vars/all/secrets.vault.yml`.
- Promptfoo baseline run from this workspace is blocked because neither `ATHANOR_LITELLM_API_KEY` nor `OPENAI_API_KEY` is exported in the active WSL shell context, and no local `.env` file provides one.
- NordVPN credentials → qBittorrent
- Anthropic API key → Quality Cascade cloud escalation
- Google Drive rclone OAuth → Personal data ~40% (10.8)
- Photo Analysis → Qwen3.5 multimodal + vLLM 0.17+ (10.10)
- n8n workflow activation → Shaun must click Activate at vault:5678
- 14.3 HA depth → Shaun must configure Lutron + UniFi in HA
- 14.5 Kindred → awaiting Shaun's go decision

### What's next (priority order)
1. **Restore matching Ansible vault secret source** — then deploy `playbooks/vault.yml --tags monitoring,alerts --limit vault` and verify `backup-exporter` + Prometheus alerts live on VAULT.
2. **Investigate VAULT FUSE ENOSPC** — repo and manifest still point to the cache-drive workaround; underlying Unraid user-share issue remains unresolved.
3. **Run promptfoo eval baseline** — after exporting `ATHANOR_LITELLM_API_KEY` or `OPENAI_API_KEY` into WSL, run `scripts/run-evals.sh` and record the fresh baseline.
4. **Kindred** (14.5) — blocked on Shaun's go decision.
5. **n8n signal pipeline activation** — Shaun: visit vault:5678, activate "Intelligence Signal Pipeline".

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

## Current System State (verified 2026-03-11)

### Cluster (nodes healthy, all services up)
- **FOUNDRY .244**: vllm-coordinator (Qwen3.5-27B-FP8 TP=4 on GPUs 0,1,3,4 :8000), vllm-coder (Qwen3.5-35B-A3B-AWQ-4bit on GPU2/4090 :8006). 11 containers.
- **WORKSHOP .225**: Qwen3.5-35B-A3B-AWQ on 5090 (GPU0) :8000. ComfyUI on 5060Ti. Dashboard:3001, EoBQ:3002, Open WebUI:3000, Ulrich Energy:3003.
- **VAULT .203**: 42+ containers. LiteLLM:4000, LangFuse:3030, Open WebUI:3090, Redis:6379, Qdrant:6333, Neo4j:7474. Storage 86% (141T/164T).
- **DEV .189**: Embedding:8001 + Reranker:8003. Claude Code native install.

### LiteLLM Routing (at VAULT:4000)
- `reasoning` → Qwen3.5-27B-FP8 at foundry:8000
- `coding` → Qwen3.5-27B-FP8 at foundry:8000
- `coder` → Qwen3.5-35B-A3B-AWQ-4bit at foundry:8006
- `fast` → Qwen3.5-35B-A3B-AWQ-4bit at workshop:8000
- `uncensored` → Qwen3.5-35B-A3B-AWQ-4bit at workshop:8000
- `utility` → Qwen3.5-35B-A3B-AWQ-4bit at workshop:8000
- `creative` → Qwen3.5-35B-A3B-AWQ-4bit at workshop:8000
- `worker` → Qwen3.5-35B-A3B-AWQ-4bit at workshop:8000
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
