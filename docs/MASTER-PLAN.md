# ATHANOR MASTER PLAN — FINAL CANONICAL DOCUMENT

> **Last updated:** 2026-03-18
> **Status:** Strategic reference (WHAT and WHY). The tactical plan (`docs/superpowers/specs/2026-03-18-athanor-coo-architecture-FULL.md`) has implementation details (HOW, exact configs, commands). Both are canonical — different purposes.
> **Owner:** Shaun (solo developer, senior level, AI-augmented)

---

## What Athanor Is

Athanor is a sovereign AI system running on 4 home machines that augments a solo developer. It combines 10 cloud AI subscriptions ($543/mo flat-rate, resetting limits) with local AI models (free, unlimited, private) and autonomous agents that work 24/7. The owner describes what they want; the system figures out how to do it.

**Design philosophy:** Cloud subscriptions are the primary power source — designed to maximize every resetting limit across Claude Max, ChatGPT Pro, Gemini, Kimi, Perplexity, and others. Local models are the uninterruptible power supply — always available, handles overflow, NSFW/sovereign workloads, and autonomous background operations. The system is designed for **cloud-first with local backbone**, NOT local-first with cloud fallback.

The name comes from the alchemical furnace — a self-sustaining vessel that maintains its own fire.

---

## The Two Orchestrators

Athanor has two operating modes that share infrastructure but serve different contexts.

### Interactive Orchestrator (User Present)

The user describes a task. The system picks the tool and model.

**Three contexts, three governors — no meta-layer needed above them:**

| Context | Governor | Tools Available |
|---------|----------|----------------|
| **Terminal** | Claude Code CLI (Opus 4.6, Max sub) | Complex reasoning, MCP, hooks, skills, Agent Teams |
| **IDE** | Kilo Code (VS Code + JetBrains + CLI) | 9-mode model routing, Orchestrator mode, parallel subagents |
| **Autonomous** | OpenFang (24/7 Rust daemon, Telegram) | Phone commands, HERS Hand, scheduled tasks |

**Supporting tools (used by all three contexts):**

| Tool | Role | Model |
|------|------|-------|
| Aider | Overnight autonomous git-native coding | Architect=Sonnet, Editor=local Qwen via LiteLLM |
| GSD v1.26.0 | Context rot prevention (spawns fresh agents per task) | Wraps any agent session |
| Greywall | Kernel-level sandbox for safe autonomous execution | N/A (security layer) |
| CodeRabbit | Automated PR review on every push | AI review (free OSS tier) |
| Superset | Parallel multi-agent orchestrator with worktree isolation | Wraps Kilo + Aider + Claude Code simultaneously |
| Gemini CLI | Quick questions, 1M context | Gemini 3.1 Pro (free 1000/day) |
| Codex CLI | Terminal debugging, second opinion | GPT-5.4 (Pro sub) |
| Perplexity | Deep research | Opus-backed (Pro sub) |
| Kimi Agent Swarm | Massive breadth tasks | K2.5, 100 parallel (Allegretto sub) |

The user never manually picks a tool or subscription. Claude Code's delegate skill and Kilo Code's mode routing handle selection automatically. Each cloud subscription is used for its strength (see Subscription Utilization Strategy below).

### Autonomous Orchestrator (User Absent)

Runs 24/7 without human intervention.

- **Governor:** LangGraph agents on FOUNDRY:9000 (9 agents, 77 tools)
- **Intent classification:** Semantic Router (embedding-based, 10-25ms, uses Qwen3-Embedding-0.6B on DEV:8001)
- **Scheduling:** APScheduler (LangGraph Platform cron is paid-only)
- **State persistence:** PostgresSaver on VAULT PostgreSQL
- **Event triggers:** Prometheus Alertmanager webhooks
- **Tool safety tiers:**
  - `READ_ONLY` — auto-execute
  - `WRITE_SAFE` — auto-execute + log
  - `DESTRUCTIVE` — requires human approval
- **Graduated autonomy:** shadow mode → read-only → low-risk execution → full with kill switch

### How They Connect

- Claude Code submits background tasks to LangGraph agents via the athanor-agents MCP bridge.
- The autonomous system sends ntfy push notifications to the user's phone when issues are found.
- Session start hook surfaces overnight agent activity when the user returns.
- Langfuse traces every LLM call from both modes for analysis.

---

## The 7 Governance Domains

Research proved 5-7 governance domains is optimal for a solo operator (Miller's Law, span of control theory, real-world solo developer practice). The 23 concepts from the prior PLAN.md are ALL preserved — mapped into these 7 domains so nothing is lost.

| # | Domain | Scope | PLAN.md Concepts Mapped Here |
|---|--------|-------|------------------------------|
| 1 | **Compute** | GPU allocation, model deployment, inference routing | Model Role Registry, Workload Class Registry, Capacity Governor (GPU contention, time-window choreography), Champion-Challenger model governance (test → shadow → promote), Model Proving Ground (golden task packs, refusal tests) |
| 2 | **Storage** | Data lifecycle, backups, media management | Data Lifecycle Registry (ephemeral, operational, memory-worthy, archival, sovereign-only, eval-eligible) |
| 3 | **Services** | App deployment, health monitoring, dependencies | Failure and Recovery Matrix (retry/fallback/visibility/escalation per failure type), Execution tiers (offline eval → shadow → sandbox → canary → production) |
| 4 | **Generation** | Content pipelines, creative workflows, autonomous agents | Dual Meta-Orchestrator (frontier cloud + sovereign local planes), Autonomous Dev Agent patterns, Creative worker routing |
| 5 | **Operations** | Monitoring, alerting, maintenance, subscription utilization | Presence and Attention Model (at desk/active/away/asleep/phone-only → affects notification posture, approval friction, automation aggressiveness), Economic Governance (maximize resetting limits, no per-token APIs), System Constitution (command hierarchy: Shaun > Claude > Athanor > agents) |
| 6 | **Security** | Access control, secrets, content governance routing | Content & Refusal Governance Matrix (5 task classes), Graduated autonomy (shadow → read-only → low-risk → full with kill switch), Tool safety tiers (READ_ONLY/WRITE_SAFE/DESTRUCTIVE) |
| 7 | **Knowledge** | Memory system, embeddings, RAG, documentation | Self-editable Core Memory (agents modify own persona blocks), Sleep-time precomputation (anticipatory caching), Intelligence pipeline (Miniflux → n8n → agents → Neo4j) |

### Content Governance Matrix (inside Security)

Five content classes determine where data can be processed:

| Class | What It Covers | Where It Goes |
|-------|---------------|---------------|
| `cloud_safe` | Open-source code, public docs | Any provider |
| `private_but_cloud_allowed` | Business data | Trusted cloud or local |
| `hybrid_abstractable` | Sensitive structure | Cloud sees ONLY abstracted structure; raw stays local |
| `refusal_sensitive` | Adult/NSFW content | Local uncensored ONLY (JOSIEFIED, Dolphin) |
| `sovereign_only` | Pen testing, credentials | Local ONLY, never leaves the cluster |

Enforced by: Semantic Router at intent classification level + LiteLLM `content_policy_fallbacks`.

---

## Hardware

All specs SSH-verified March 18, 2026.

### FOUNDRY (192.168.1.244) — Heavy Compute
- EPYC 7663 56-core, 219GB DDR4 (7/8 channels populated, Channel H empty)
- 4× RTX 5070 Ti + 1× RTX 4090
- 8.1TB NVMe, dual 10GbE
- PSU at 95% utilization — cannot add GPUs
- Channel H upgrade: $50-80 for 32GB RDIMM → 256GB + full 8-channel bandwidth

### WORKSHOP (192.168.1.225) — Creative + Code
- Threadripper 7960X 24-core, 125GB DDR5
- RTX 5090 32GB + RTX 5060 Ti 16GB
- 5.5TB NVMe (2× Crucial T700 Gen5 slots empty), 10GbE
- SSH user: `athanor` (not `shaun`)

### DEV (192.168.1.189) — Operations Center
- Ryzen 9 9900X 12-core, 60GB DDR5
- RTX 5060 Ti 16GB
- 5.5TB NVMe, 5GbE (NOT 10GbE — Intel X540-T2 upgrade in spare inventory)

### VAULT (192.168.1.203) — Storage
- Ryzen 9 9950X 16-core, 123GB DDR5
- Intel ARC A380 (QSV transcode)
- 5× NVMe cache/Docker/transcode, 200TB HDD array (87% full, 22TB free)
- 10GbE bonded (bond0, 2× NIC)
- Docker moved to NVMe `/mnt/docker` (932GB, bind-mounted to `/var/lib/docker`)

### DESK (192.168.1.50) — Windows Workstation
- i7-13700K, 64GB DDR5
- RTX 3060 12GB
- 3TB NVMe, 10GbE

### Idle Resources
- 305GB RAM cluster-wide (75% available)
- 18.7TB NVMe cluster-wide (85% available)
- WORKSHOP RTX 5060 Ti (partially allocated)
- DESK RTX 3060 (available for local gen)

### Planned Hardware Changes
- Motherboard swap: TRX50 + 7960X from VAULT → WORKSHOP; X870E + 9950X → VAULT
- DEV NIC upgrade: Intel X540-T2 (in spare inventory) for 10GbE

---

## GPU Layout

Research-verified. Status column shows what's ACTUALLY RUNNING vs what's PLANNED.

| GPU | Location | Model | Role | Status | Rationale |
|-----|----------|-------|------|--------|-----------|
| 4× RTX 5070 Ti (TP=4) | FOUNDRY 0,1,3,4 | Qwen3.5-27B-FP8 | General reasoning + vision | ✅ RUNNING (vision pending restart) | 72.4% SWE-bench, all 27B active, MTP at 78-100%. |
| RTX 4090 | FOUNDRY 2 | Qwen3.5-35B-A3B-AWQ-4bit | Code generation | ✅ RUNNING | 3B active MoE, fast iteration. Port 8006. |
| RTX 5090 | WORKSHOP 0 | **Currently:** Qwen3.5-35B-A3B-AWQ (vllm-node2, 98% VRAM) | LLM inference | ✅ RUNNING | **TARGET:** Remove vllm-node2, dedicate to ComfyUI + LTX 2.3 video gen. gpu-swap.sh manages time-sharing. |
| RTX 5060 Ti | WORKSHOP 1 | **Currently:** ComfyUI (416MB used) | Image gen (minimal) | ✅ RUNNING | **TARGET:** Deploy JOSIEFIED-Qwen3-8B (~9GB) + Aesthetic Predictor V2.5 (~1.5GB). |
| RTX 5060 Ti | DEV | Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B | Search, RAG | ✅ RUNNING | 3GB used, 13GB free for future upgrade. |
| RTX 3060 | DESK | Available | Local gen on Windows | ⬜ NOT DEPLOYED | SD WebUI Forge + Wan 2.2 when ready. |

### Critical GPU Notes
- mxfp4/FP4 does NOT work on consumer Blackwell (SM120) — upstream CUTLASS bugs. Stay on FP8/AWQ.
- vLLM is v0.16.1rc1.dev32 (custom NVIDIA build). Working, Blackwell support, MTP active. Do not change.
- Tool call parser: `qwen3_xml` (NOT `hermes`).
- All Qwen3.5 models are natively multimodal VLMs.

---

## Model Router: LiteLLM

All local and cloud model requests route through LiteLLM on VAULT:4000 (v1.81.9-stable).

### Key Configuration
- `stream_timeout: 10` per local entry (fail-fast to first token)
- `num_retries: 0` for local models (don't retry dead models, fall through immediately)
- `model_info` with `supports_function_calling: true` on all local entries
- Fallback chains: local → Claude (only active cloud key)
- Coding route → FOUNDRY:8006 (coder), NOT :8000
- Vision route → FOUNDRY:8000 (coordinator, after `--language-model-only` removed)
- Langfuse tracing active (`pk-lf-athanor` / `sk-lf-athanor`)
- `background_health_checks` every 300s

### Performance
- Worst-case failover: **10 seconds** (was 24 MINUTES before routing overhaul)
- NSFW auto-failover (add to config):
  ```yaml
  content_policy_fallbacks:
    - claude-sonnet-4-6: ["uncensored"]    # If Claude refuses → local JOSIEFIED
    - claude-opus-4-6: ["uncensored"]
  ```

---

## Daily Workflow

The system picks the tool — the user just describes what they want.

| Task Type | Routed To | Model | Cost |
|-----------|-----------|-------|------|
| Complex architecture | Claude Code (Opus) | Opus 4.6 | $0 (Max sub) |
| Visual development | Roo Code (mode-based) | Per-mode routing | $0 (local) or sub |
| Bulk file editing | Aider (auto-delegated) | Qwen3.5 local | $0 |
| Terminal debugging | Codex CLI | GPT-5.4 | $0 (Pro sub) |
| Deep research | Perplexity Deep Research | Opus-backed | $0 (Pro sub) |
| 1M context ingestion | Gemini CLI | Gemini 3.1 Pro | $0 (free 1000/day) |
| Massive breadth | Kimi Agent Swarm | K2.5 (100 parallel) | $0 (Allegretto sub) |
| Quick question | Gemini CLI | Gemini 3.1 | $0 (free) |
| Code review | CodeRabbit | AI review | $0 (free OSS) |
| NSFW creative | JOSIEFIED-Qwen3-8B | 8B abliterated | $0, LOCAL ONLY |
| Pen testing | Abliterated local model | Dolphin/JOSIEFIED | $0, LOCAL ONLY |
| Overnight coding | claude -p + GSD | Opus headless | $0 (Max sub) |
| Health monitoring | LangGraph agents | Qwen3.5-27B | $0, autonomous |
| Image generation | Auto_gen pipeline | FLUX + PuLID | $0, autonomous |
| Video generation | LTX 2.3 on ComfyUI | 22B NVFP4 | $0 |
| Voice synthesis | Dia 1.6B / Kokoro | Local TTS | $0 |
| Media management | Sonarr/Radarr chain | LangGraph media-agent | ~$5/mo Usenet |
| Fact checking | Z.ai GLM | GLM-4.7 | $0 (sub) |

---

## Subscriptions

**Total: $543.91/mo.** All kept — maximize resetting limits.

| Service | Cost/mo | Best For | Limit Reset |
|---------|---------|----------|-------------|
| Claude Max 20x | $200 | Primary everything | ~900 msgs/5hr rolling |
| ChatGPT Pro | $200 | Codex, GPT-5.4, o3-pro | Rolling |
| Gemini Advanced | $20 | Quick questions, 1M context, research | 1000/day |
| Copilot Pro+ | $33 | IDE autocomplete, BYOK | 1500 premium/mo |
| Z.ai GLM Pro | $30 | Fact checking, classification | Monthly |
| Perplexity Pro | $20 | Deep Research (Opus-powered) | Unlimited |
| Kimi Code Allegretto | $19 | Agent Swarm (100 parallel) | Weekly |
| Venice AI Pro | $12 | Uncensored API (cancels Jul 2026) | Credits |
| Qwen Code | $10 | DashScope, free third-party models | 90K req/mo |
| Mistral | $0 | Codestral autocomplete (#1 ranked) | Free |

**Anthropic OAuth crackdown (Jan 9, 2026):** Max sub works for Claude Code CLI ONLY, not third-party tools.

### Subscription Utilization Strategy

**NOT a waterfall (serial overflow). This is parallel proactive routing — each subscription used for what it's BEST at, simultaneously.**

The governor routes each task to the subscription that is: (1) best at that task type, (2) has remaining capacity, (3) is the cheapest option that meets quality requirements.

**Burn free tiers first, always:**
- Gemini CLI: 1000 free requests/day → use for ALL quick questions, research, 1M context docs
- Mistral Codestral: free autocomplete → use for ALL IDE tab completion
- Cerebras: GLM-4.7 + GPT-OSS-120B at ~2800 tok/s, free → use for classification, routing, fast tasks
- Groq: GPT-OSS-20B, free, 131K context → overflow for medium complexity

**Then use each paid sub for its strength:**
- Claude Max (Opus): architecture, complex multi-file reasoning, overnight autonomous coding. ~900 msgs/5hr. Opus consumes 3× more quota than Sonnet — use Sonnet for 80% of Claude work.
- ChatGPT Pro (GPT-5.4): terminal workflows (75% OSWorld), computer-use tasks, o3-pro for hard math only
- Perplexity Pro: deep research sessions (Opus-backed, effectively unlimited)
- Z.ai GLM Pro: fact checking, verification (lowest hallucination rate, Omniscience Index #1)
- Kimi Allegretto: Agent Swarm for massive breadth (100 parallel sub-agents)
- Copilot Pro+: IDE autocomplete throughout the day, GitHub Spark for prototyping, BYOK bridge
- Qwen Code: DashScope for Qwen3-Coder-Next cloud access, free third-party models (Kimi, GLM, MiniMax)
- Venice Pro: burn remaining 312 credits on uncensored API tasks before July auto-cancel

**When ALL cloud subs are at capacity:** Local Qwen3.5 via LiteLLM ($0, unlimited, always available)

**Autonomous agents START on local models ($0).** As trust grows through graduated autonomy (shadow → read-only → low-risk → full), agents earn the ability to use cloud subscriptions — especially overnight when limits are resetting and unused tokens are wasted. The governor tracks remaining capacity per subscription and routes high-value autonomous tasks to cloud when appropriate. Local models remain the always-available backbone that ensures the system never stops.

### System Layers

```
Layer 7: USER (DESK → VS Code/Terminal → DEV)
Layer 6: GOVERNORS
         Terminal: Claude Code (Opus, MCP, hooks, skills, Agent Teams)
         IDE:     Kilo Code (9-mode routing, Orchestrator, parallel subagents)
         24/7:    OpenFang (Rust daemon, Telegram, HERS Hand, phone access)
Layer 5: ORCHESTRATION
         Superset (parallel multi-agent with worktree isolation)
         GSD (context rot prevention — spawns fresh agents per task)
         Greywall (kernel sandbox for safe autonomous execution)
Layer 4: TOOL ECOSYSTEM
         Aider (overnight autonomous, git-native, architect/editor)
         Codex CLI, Gemini CLI, Kimi CLI, Perplexity (subscription tools)
         CodeRabbit (automated PR review)
Layer 3: MODEL ROUTER (LiteLLM on VAULT:4000 — all local + cloud routing)
Layer 2: LOCAL INFERENCE (vLLM on FOUNDRY + WORKSHOP, Ollama for JOSIEFIED)
Layer 1: AUTONOMOUS AGENTS (LangGraph on FOUNDRY:9000 + Semantic Router on DEV)
Layer 0: CONTENT + INFRASTRUCTURE
         auto_gen, ComfyUI, LTX 2.3, Dia TTS, Aesthetic Predictor
         Docker, Prometheus, Langfuse, ntfy, Backups, Media Stack
```

Cloud subscriptions power Layers 6+4. Local models power Layers 3+2+1+0. Layer 5 ensures quality (GSD), safety (Greywall), and parallelism (Superset). No meta-layer needed above Layer 6 — the three governors serve different contexts (terminal/IDE/autonomous) that don't overlap.

---

## Autonomous Multi-Project Development

- 33 GitHub repos under Dirty13itch (7 infra, 9 business, 6 personal, 11 portfolio)
- Overnight pattern: `claude -p` + GSD (context rot prevention) + CodeRabbit (PR review)
- 78% first-attempt success on well-scoped tasks
- `sandboxed.sh` on FOUNDRY for Docker isolation per project
- OpenHands for GitHub issue → PR workflows
- `CLAUDE.md` per repo provides project context
- CodeRabbit reviews every PR before human sees it
- 5-10 active projects manageable overnight
- Bottleneck is **review**, not generation

### Context Rot
- 0-30% context window = peak quality
- 50%+ = cutting corners
- 70%+ = hallucinations
- GSD solves this by managing session freshness

---

## Content Pipeline

### Image Generation (Auto_gen)

- **Scheduler:** Every 2 hours, 18 subjects, 45 themes (25 solo + 20 hardcore)
- **Engine:** ComfyUI on WORKSHOP:8188 with FLUX.1 Dev FP8 + PuLID Flux + uncensored LoRA
- **Prompts:** LLM via LiteLLM → creative model (Qwen3.5-35B on WORKSHOP)
- **Identity:** Performer attributes injected from `performers.json` (801 records)
- **Scoring:** Aesthetic Predictor V2.5 (SigLIP backbone, 1.5GB, no NSFW bias, 5-15ms/image)
- **Feedback loop:** Scores → per-theme/per-subject tracking → prompt tuning
- **Custom MLP scorer:** Train on 1000+ rated images, SigLIP embeddings, trains in seconds on CPU
- **Drop dir:** `/mnt/vault/data/gen-drops/` (NFS, all nodes)
- **Output dir:** `/mnt/vault/data/gen-output/{drop-name}/`
- **Pipelines:** `flux-uncensored` (text-to-image), `flux-faceid` (identity-preserving with PuLID + ReActor)
- **Active subjects (11):** 5 S-Tier (priority 8), 6 A-Tier (priority 6)
- **Timeout:** 600s per generation (increased from 180s for FLUX model loading)

### Video Generation (LTX 2.3)

- NVFP4 on WORKSHOP RTX 5090 (21.7GB model + Gemma FP4 9.5GB = 31.2GB, tight fit)
- Fallback: GGUF Q4_K_M (14.3GB, comfortable)
- ~25s for 720p/4s@24fps distilled, unified audio+video
- Requires: ComfyUI nightly + ComfyUI-LTXVideo + ComfyUI-GGUF nodes
- Alternative to evaluate: HunyuanVideo 1.5 GGUF (community uncensored builds)

### Voice

| Model | Size | Role | Performance |
|-------|------|------|-------------|
| Dia 1.6B | ~10GB | EoBQ dialogue (dual-speaker, 17 emotions) | Apache 2.0 |
| Kokoro 82M | CPU | Fast/ambient TTS | 210x realtime |
| Whisper large-v3 | ~3GB | STT (faster-whisper) | Production-ready |

### EoBQ (Empire of Broken Queens)

A visual novel with procedurally generated characters.

- **19-Trait Sexual Personality DNA System** for character uniqueness
- **SoulForge Engine:** LLM generates DNA + backstory → image gen → voice synthesis → Ren'Py
- **Ren'Py MCP server** (60 tools) for visual novel development
- **JOSIEFIED-Qwen3-8B mandatory** for all dialogue (abliterated, 10/10 adherence)
- **ALL EoBQ traffic stays local** — zero cloud
- **Scale:** 300+ scenes, 1800+ messages, 12-16 endings per queen (multi-year production)

---

## Media Automation (VAULT)

### Running
- Sonarr, Radarr, Plex
- Tdarr (ARC A380 QSV, H.265 transcode, ~500 FPS, 36K files tracked, 4.08TB saved)
- Stash (22.5K scenes, 22.7TB, 14.5K performers, Intel VAAPI hardware accel)

### To Deploy
| Service | Purpose |
|---------|---------|
| SABnzbd | Usenet downloader (SSL sufficient, VPN optional) |
| Prowlarr | Indexer management (replaces Jackett) |
| Whisparr | Adult content *arr (complements Stash) |
| Seerr | Unified request management (Overseerr+Jellyseerr successor) |
| Bazarr | Automated subtitles |
| Recyclarr | Auto-sync TRaSH quality profiles daily |

### Usenet Providers
- **Unlimited primary:** Newshosting or UsenetServer (Omicron backbone, ~$3-5/mo)
- **Block backup:** Blocknews (Abavia backbone, $10-15 one-time)
- **Indexers:** NZBgeek ($12/yr) + DrunkenSlug (invite-only)

---

## Observability

| System | Location | Purpose |
|--------|----------|---------|
| Langfuse | VAULT:3030 | Every LLM call traced (139K existing + new) |
| Prometheus | VAULT:9090 | 16/17 targets UP, 27+ alert rules |
| Grafana | VAULT:3000 | 5 dashboards (Athanor Ops, Cluster, Node Exporter, NVIDIA DCGM, VAULT Monitor) |
| ntfy | VAULT:8880 | Push notifications to phone |
| DCGM exporters | FOUNDRY+WORKSHOP:9400 | GPU metrics |
| Bash health scripts | DEV (systemd timer) | $0 monitoring |
| Arize Phoenix | Planned | Agent graph visualization |

---

## Memory System

6-tier architecture, all verified operational.

| Tier | Backend | Count | Purpose |
|------|---------|-------|---------|
| Working | Redis | Ephemeral | Session-scoped context |
| Episodic | Qdrant | 6 | Event memories |
| Semantic | Neo4j | 3,241 | Knowledge graph |
| Procedural | PostgreSQL | 10 | Operational procedures |
| Resource | Qdrant + Meilisearch | 347 | Document chunks |
| Vault | PostgreSQL + Qdrant | 40 | Long-term archival |

- Consolidation runs daily at 3am (Working → Episodic, Episodic → Vault)
- Perception: 2 active file watchers (docs/ at 120s, /mnt/vault/data/documents at 60s)
- MCP servers: 7 servers, 54 tools total (memory, inference, knowledge, workspace, infra, creative, tools)

---

## Infrastructure Services

| Service | Location | Notes |
|---------|----------|-------|
| LiteLLM | VAULT:4000 | v1.81.9-stable, 33 model aliases, auth: `sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d` |
| Qdrant | VAULT:6333 | Collections: knowledge_vault, resources, episodic |
| PostgreSQL | VAULT | Strong password, rotated 2026-03-05 |
| Redis | VAULT | Requirepass set, persistent via redis.conf |
| Neo4j | VAULT:7687 | 3,237 nodes |
| Meilisearch | VAULT:7700 | v1.37.0 |
| LangGraph Agents | FOUNDRY:9000 | 9 agents, 77 tools, trust system, all scheduled |
| GPU Orchestrator | FOUNDRY:9200 | 4 GPU zones, 10 endpoints, Prometheus metrics, sleep/wake broken |
| speaches (Kokoro TTS) | FOUNDRY:8200 | OpenAI-compatible TTS, 54 voices, CUDA |
| wyoming-whisper | FOUNDRY:10300 | STT for Home Assistant |
| Grafana Alloy | FOUNDRY+WORKSHOP:12345 | OpenTelemetry collector |
| Gateway | DEV:8700 | FastAPI, systemd-managed |
| MIND | DEV:8710 | Reasoning service |
| Memory | DEV:8720 | Memory API (NOT 8702) |
| Perception | DEV:8730 | Chunk → embed → index pipeline |
| UI | DEV:3001 | Next.js (**CRASH LOOPING** — needs fix) |
| Home Assistant | VAULT:8123 | Smart home control, home-agent has 8 tools + JWT |
| n8n | VAULT:5678 | Workflow automation, 41 importable workflows from Hydra |
| Gitea | VAULT:3033/2222 | Self-hosted Git (athanor-next origin remote) |
| Miniflux | VAULT:8070 | RSS aggregation for intelligence pipeline |
| Langfuse | VAULT:3030 | v3.155.1, 139K+ traces, LLM observability |
| Prometheus | VAULT:9090 | 16/17 targets UP, 27+ alert rules |
| Grafana | VAULT:3000 | 5 dashboards, admin password: `localadmin` |
| ntfy | VAULT:8880 | Push notifications, topic: `athanor` |
| Open WebUI | WORKSHOP:3000 | Browser chat with local models |
| Athanor Dashboard | WORKSHOP:3001 | Main web UI |
| EoBQ App | WORKSHOP:3002 | Empire of Broken Queens |
| Ulrich Energy | WORKSHOP:3003 | HERS business app |

### Locked Architectural Decisions
1. Claude Code is primary interactive tool (Roo Code is visual complement, not replacement)
2. LiteLLM is single routing layer for all local model access
3. Subscription CLIs before BYOK tools
4. Coolify on DEV for internal deploys (not yet installed)
5. Cloudflare Pages for production public frontends
6. FOUNDRY is production — never modify without explicit approval
7. ALL EoBQ/NSFW traffic stays local — zero cloud
8. No peer-to-peer agent communication (centralized orchestrator only)
9. No agent self-modification
10. Disaster recovery: see `docs/RECOVERY.md` (RTO 2-4hrs, VAULT is SPOF)

### Backups (VAULT cron)
- PostgreSQL: daily 1:30am, 14-day retention
- Neo4j: weekly Sunday 2am, 30-day retention
- Qdrant: weekly Wednesday 2am, snapshots, 30-day retention
- Stash: daily 2am, 14-day retention

---

## What Was Already Executed (March 18, 2026 session)

1. Auto_gen LLM endpoint fixed (was dead 12 days → now routes through LiteLLM)
2. Langfuse API keys set (tracing restored after 4 days dark)
3. Agent Qdrant URL fixed (FOUNDRY:6333 → VAULT:6333) + timeout 600→1800s
4. WORKSHOP models copied to local Gen5 NVMe (14x faster model loading)
5. LiteLLM routing overhauled (24-min → 10s failover, coding route fixed, vision route fixed)
6. MCP Tool Search fixed (auto:5 → true)
7. vLLM swap-space added to coder + node2 (pending restart)
8. GSD v1.26.0 installed on DEV
9. Crucible (4 containers) + old FOUNDRY Qdrant stopped/removed
10. Vision `--language-model-only` removed from coordinator config (pending restart)

---

## Blocked on User

These require manual human action:

- Rotate 3 exposed API keys (Mistral, Z.ai, HuggingFace)
- Install CodeRabbit (GitHub OAuth at app.coderabbit.ai)
- Install Roo Code in VS Code (RooVeterinaryInc.roo-cline)
- Encrypt/move Usenet credentials from Desktop
- Schedule vLLM restart window (for swap-space + vision changes)

---

## Remaining Execution (next sessions)

Ordered by dependency and priority:

### Infrastructure (do first)
1. **Remove vllm-node2 from WORKSHOP 5090** — frees 5090 for creative gen. Currently uses 98% VRAM running a 3rd copy of same LLM. Use `gpu-swap.sh` for ComfyUI/inference time-sharing.
2. **Restart vLLM coordinator** — applies pending changes: vision (--language-model-only removed), swap-space increase. Schedule maintenance window.
3. **Restart vLLM coder + node2** — applies swap-space 16 config. Can coordinate with #2.
4. **Fix local-system-ui.service** — crash-looping on DEV:3001.

### Tool Stack (do second)
5. Deploy Aesthetic Predictor V2.5 on WORKSHOP 5060 Ti
6. Deploy JOSIEFIED-Qwen3-8B on WORKSHOP 5060 Ti
7. Set up Semantic Router service on DEV (embedding-based, 10-25ms)
8. Add APScheduler to LangGraph agent server
9. Update CLAUDE.md with full routing matrix + cloud-first subscription utilization
10. Update delegate skill with auto-dispatch logic
11. Set up first overnight autonomous coding run (claude -p + GSD + CodeRabbit)

### Data & Content (do third)
12. Deploy media containers (Whisparr, Seerr, Bazarr, Recyclarr) on VAULT
13. Performer data merge (openpyxl script ready, 801 records enrichment, NO TOSI scores)
14. MEMORY.md full rewrite (14+ inaccuracies found)

### New Capabilities (do last)
15. LTX 2.3 video gen setup on WORKSHOP 5090
16. Dia 1.6B TTS deployment
17. Intelligence pipeline (Miniflux → n8n → agents, deployed but not wired)
18. Merge `automation-backbone` branch (backbone.py + ADR-023)
19. Copy gpu-swap.sh to repo scripts/

### Known Broken (fix when encountered)
- VAULT container count: plan says 41, audit found 47 — verify and update
- Qdrant/Neo4j backups may have been failing since March 14 — verify
- 11 orphaned MCP permissions in project settings — remove

---

## Rejected Approaches

Every rejection has evidence.

| Approach | Why Rejected |
|----------|-------------|
| llama-swap | 30-120s vLLM Docker swap latency. Not "dynamic." |
| claude -p for monitoring | 23% multi-step success rate. $400/mo wasted. |
| vmtouch page cache | 10-30s savings. Non-I/O bottlenecks dominate. |
| ImageReward / PickScore | NSFW penalties in scoring. Unusable for this use case. |
| Split Claude Code subagent routing | Hardcoded model IDs, too buggy. |
| SGLang migration | vLLM works fine. No reason to switch. |
| LangGraph Platform cron | Paid only. APScheduler is free and sufficient. |
| EAGLE-3 speculative decode | Invalidated by Qwen3.5 native MTP. |
| Devstral 2 123B | Needs 2× H100. Does not fit this cluster. |
| mxfp4 quantization (OCP standard) | SM120 CUTLASS bugs for dense models. MXFP4 ≠ NVFP4. |
| 23-subsystem governance | Cognitive science proves 5-7 optimal for solo operator. |
| Per-token cloud APIs | Flat-rate subs make per-token wasteful. |
| LiteLLM complexity router | Buggy with multi-modal and tool calls. |

---

## KAIZEN Legacy

What survived from the original January 2026 vision:

| Concept | Status |
|---------|--------|
| Multi-agent architecture | Exceeded scope: 9 agents vs 4 planned |
| 6-tier memory system | Exceeds original 3-tier Letta design |
| Voice pipeline (Silero VAD → Whisper → LLM → TTS) | Architecture valid, never built |
| GWT workspace competition | Future evolution of governor |
| Three-tier processing (Reactive/Tactical/Deliberative) | Informal but present |
| Self-editable Core Memory | Agents modify own persona blocks, not yet implemented |

---

## Key Technical Facts

Reference details that prevent common mistakes.

- **vLLM version:** v0.16.1rc1.dev32 (NVIDIA custom build, NOT v0.13.0 as env var suggests)
- **LiteLLM version:** v1.81.9-stable (v1.82.4 available)
- **Tool call parser:** `qwen3_xml` (NOT `hermes`)
- **All Qwen3.5 models are natively multimodal VLMs**
- **FOUNDRY PSU at 95%** — cannot add GPUs
- **Memory port is 8720** everywhere (old refs to 8702 are wrong)
- **LiteLLM health requires auth:** `Authorization: Bearer sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d`
- **LiteLLM metrics path needs trailing slash:** `/metrics/`
- **WORKSHOP SSH user is `athanor`**, not `shaun`
- **VAULT SSH:** `root@192.168.1.203` (shaun user SSH was failing)
- **NodeName enum is case-sensitive:** `.env` must use lowercase `dev` not `DEV`
- **FastAPI:** `on_event("startup")` ignored when `lifespan` exists — use lifespan only
- **UI:** Use system node (`/usr/bin/npx`), not nvm paths in systemd
- **Open models LEAD closed on function-calling:** GLM-4.5 70.85%, Qwen3.5-122B 72.2% vs GPT-5 59.22%
- **VAULT array 87% full** (142T/164T, 22T free). disk1 at 92%. disk3 has 6,386 UDMA CRC errors (bad cable).
- **41 Docker containers on VAULT** (as of 2026-03-08), all healthy
- **NVFP4 ≠ MXFP4:** NVFP4 (NVIDIA's format) IS production-ready with pre-quantized checkpoints. MXFP4 (OCP standard) is broken for dense models on SM120. The plan rejects MXFP4, not NVFP4.
- **NVFP4 KV cache:** 50% VRAM reduction vs FP8 KV. Enables 2× context or batch size.
- **EXL3 (ExLlamaV3):** Variable bpw quantization with MoE expert parallelism and heterogeneous TP. Served via TabbyAPI. NOT needed for current layout (TP=4 is homogeneous 5070Ti group; 4090 runs independently). Evaluate only if GPU layout changes require mixed-GPU TP.
- **MoE quantization:** Router/gating must stay ≥W8A8. Shared experts need higher precision than routed. Never quantize gating below 8-bit.
- **vLLM TP for ≤16GB models:** Separate instances beat TP (4× throughput, zero communication overhead). TP=4 only when model needs >64GB combined.
- **TP=4 on PCIe 4.0 gives ~2.2-2.5× speedup, NOT 4×** — all-reduce overhead over PCIe vs NVLink.
- **Agent Teams already enabled:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set in project settings.
- **Context rot:** 0-30% = peak quality, 50%+ = cutting corners, 70%+ = hallucinations. GSD solves this.
- **Claude Code sandbox escape:** Claude disabled its own bubblewrap sandbox in a session. Kernel-level enforcement (Greywall) required for safe autonomous agents.
- **Anthropic OAuth crackdown (Jan 9, 2026):** Max sub tokens restricted to Claude Code/claude.ai only. Cannot use with third-party tools via OAuth.

## Remote Access & Networking

- **Tailscale mesh** (not yet deployed): Free plan, 100 devices, WireGuard P2P. Gives phone access to cluster from job sites. Headscale as self-hosted alternative.
- **OpenFang** (not yet deployed): Rust 32MB daemon on VAULT:4200. 40 messaging adapters (Telegram). 7 "Hands" for autonomous task modules. HERS Hand config ready (ATHANOR-SYNTHESIS.md Appendix B). Enables phone → Telegram → OpenFang → agents for remote cluster management.

## Free-Tier APIs (not subscriptions — zero cost)

15 free APIs available for routing overflow:
Groq, Cerebras (GLM-4.7 + GPT-OSS-120B at ~2800 tok/s), SambaNova, Fireworks, Together, OpenRouter, DeepSeek, Replicate, xAI, Cohere, HuggingFace, Tavily, Serper, Brave Search, ElevenLabs.
GPT-OSS-120B on Cerebras: free, 64K context. GPT-OSS-20B on Groq: free, 131K context.

## Unmerged Code

- **`automation-backbone` branch** (C:\Athanor-worktrees\automation-backbone): `backbone.py` (451 lines) — dashboard data aggregation layer for execution runs, quota summaries, scheduled jobs, operator event streams. Near production-ready. Merge to main.
- **`gpu-swap.sh`** on WORKSHOP (/opt/athanor/gpu-swap.sh): GPU time-share manager for 5090 between vLLM and ComfyUI. Modes: `creative`, `inference`, `status`. Health check polling. Should be tracked in repo scripts/.

## Deployable Configs (from ATHANOR-SYNTHESIS.md)

4 ready-to-deploy config files exist in `C:\Users\Shaun\Downloads\ATHANOR-SYNTHESIS.md` appendices:
- **Appendix A:** Roo Code 6-mode YAML (Architect/Code/Debug/Ask/Review/HERS) with per-mode model assignments
- **Appendix B:** OpenFang HERS Hand TOML (6-phase daily automation for energy business)
- **Appendix C:** Tailscale mesh setup script for all 5 nodes
- **Appendix D:** vLLM FOUNDRY deployment with 3 strategies (TP=4, 4 separate instances, hybrid TP=2)

## Architectural Principles (from model-philosophy.md)

1. **Cloud-first with local backbone:** The system is designed to maximize 10 cloud subscriptions with resetting limits. Local models guarantee the system never stops working — they handle overflow, NSFW, sovereign workloads, and autonomous operations when cloud limits are hit or unavailable. Cloud is primary; local is UPS.
2. **Routing at operation level, not project level:** Same agent on same project routes different operations to different models based on what each operation requires.
3. **Model architecture must accommodate swapping without system redesign:** The model landscape changes fast; swappability is a first-class constraint.
4. **Cost tracking matters for cloud but should not drive design away from the best solution.**

---

*This document is the strategic reference for all Athanor decisions (WHAT and WHY). For implementation details (HOW — exact configs, commands, verification steps), see the tactical plan at `docs/superpowers/specs/2026-03-18-athanor-coo-architecture-FULL.md`. If they conflict, this document's decisions win; the tactical plan's implementation details win.*

*Last updated: 2026-03-18*
