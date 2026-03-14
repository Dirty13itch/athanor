# DEPRECATED

> **This file is deprecated.** The canonical system map is [`docs/atlas/README.md`](../atlas/README.md). This file is retained for historical context only.

# ATHANOR: Complete System Map

> Atlas note: [`docs/atlas/README.md`](../atlas/README.md) is now the canonical cross-layer system map. This file remains planning-era context and should not be treated as the current single source of truth.

**Compiled March 7, 2026 — Single source of truth for the build sprint**
**Session duration: ~10 hours of deep technical planning and research**

---

## 1. SYSTEM IDENTITY

**Name:** Athanor — the alchemist's self-feeding furnace
**Persona:** Prometheus
**Philosophy:** Sovereign second mind. Not an assistant. Thinks autonomously, improves continuously, manages own infrastructure.
**Values:** Data sovereignty, zero telemetry, uncensored local inference, bleeding edge, depth over speed, right over fast.
**Core principle:** Don't rebuild what works. Upgrade it. Let it compound.

---

## 2. HARDWARE TOPOLOGY

| Node | Hostname | IP | CPU | RAM | GPU(s) | Role | Ports |
|------|----------|----|-----|-----|--------|------|-------|
| FOUNDRY | foundry | .244 | EPYC 7663 | 224GB DDR4 | 4×RTX 5070Ti (16GB ea, TP=4) + RTX 4090 (24GB) | Coordinator + Utility | 8000, 8001 |
| WORKSHOP | workshop | .225 | TR 7960X | 128GB DDR5 | RTX 5090 (32GB) + RTX 5060Ti (16GB) | Worker + Fallback | 8100, 8101 |
| DEV | dev | TBD | Ryzen 9 9900X | 64GB DDR5-5600 | RTX 5060Ti (16GB) | Ops center, Claude Code | — |
| VAULT | vault | .203 | Ryzen 9 9950X | 128GB DDR5 | Intel A380 (Plex) | Services, routing, storage | 4000, 3030 |
| DESK | desk | .215 | i7-13700K | 64GB DDR5 | RTX 3060 (12GB) | Windows workstation | — |
| MOBILE | — | — | Asus ROG Strix G17 | — | — | Field device | — |

**Network:** UniFi UDM Pro + USW Pro XG 10GbE + USW Pro 24 PoE. All servers on 10GbE SFP+ data plane.
**Remote access:** JetKVMs + IPMI for headless management. Tailscale for field access.

---

## 3. DEPLOYED STACK (Running now on Athanor — updated 2026-03-09)

### Inference (Phase 2 — Qwen3.5 complete)
- **Engine:** vLLM nightly 0.16.1rc1.dev32 (Qwen3.5 MoE support, Blackwell SM120 kernels)
- **Coordinator:** Qwen3.5-27B-FP8 TP=4 on FOUNDRY GPUs 0,1,3,4 (:8000) — MTP enabled (18.3 tok/s), prefix caching ~79% hit rate
- **Utility:** Huihui-Qwen3-8B-abliterated-v2 on FOUNDRY GPU 2 (4090) (:8002) — 59 tok/s
- **Worker:** Qwen3.5-35B-A3B-AWQ on WORKSHOP 5090 (:8000) — 215 tok/s
- **Embedding:** Qwen3-Embedding-0.6B on DEV (:8001)
- **Reranker:** Qwen3-Reranker-0.6B on DEV (:8003)
- **Tool-call parser:** `qwen3_xml` (coordinator), `qwen3_coder` (utility, worker)
- **Critical constraints:** `--enforce-eager` (DeltaNet Triton OOM), `--language-model-only`, `--gpu-memory-utilization 0.85`

### Routing & Services
- **LiteLLM:** VAULT:4000 — aliases: reasoning, fast/utility, worker, embedding, reranker
- **Quality Cascade:** Pattern-based task classification (9 types), fallback chains, cost tracking
- **Orchestration:** LangGraph + FastAPI on FOUNDRY:9000 (9 agents, 78+ tools)
- **Task engine:** Redis-backed queue, background worker, 5s poll, max 2 concurrent
- **Dashboard:** Next.js command center on WORKSHOP:3001
- **Circuit breakers:** Per-service with auto-recovery
- **Semantic cache:** Qdrant-backed, 93% similarity threshold

### Storage
- **Qdrant (FOUNDRY :6333, canonical):** 8 collections — knowledge (2547), personal_data (7386), activity (3230), conversations (39), preferences (56), events (6394), signals (0), implicit_feedback (0)
- **Qdrant (VAULT :6333, secondary):** knowledge_vault, resources, llm_cache, episodic
- **Neo4j:** Knowledge graph on VAULT
- **Redis:** GWT workspace, heartbeats, scheduler, task queue, cache, pub/sub

### Agents (9 live)
| Agent | Type | Cycle | Tools | Interactions |
|-------|------|-------|-------|-------------|
| General Assistant | Reactive + delegation | On-demand | 9 | 370 |
| Research | Reactive | On-demand | 4 | 32 |
| Media | Proactive | 15 min | 13 | 688 |
| Home | Proactive | 5 min | 11 | 2005 |
| Creative | Reactive | On-demand | 6 | 63 |
| Knowledge | Proactive | 24h | 7 | 13 |
| Coding | Reactive | On-demand | 9 | 54 |
| Stash | Reactive | On-demand | 12 | 0 |
| Data Curator | Reactive | On-demand | 7 | 10 |

### Monitoring & Observability
- Prometheus + Grafana + Loki + Grafana Alloy (infrastructure)
- LangFuse v3.155.1 at VAULT:3030 — 12K+ traces, wired via LiteLLM callbacks
- Grafana "Athanor Inference" dashboard (12 panels: request rate, latency, throughput, GPU, cache)
- Self-improvement engine: 5/5 benchmarks passing, 6h cycle
- Node heartbeats from all 3 compute nodes (10s interval via Redis pub/sub)

### Deployment
- Ansible roles at `ansible/roles/` (vault-password file MISSING — blocks VAULT deploys)
- `scripts/deploy-agents.sh` — rsync + docker compose, validates health
- Gitea CI on VAULT:3033 with act_runner on DEV

---

## 4. MODEL UPGRADE PLAN (Qwen3.5) — COMPLETED 2026-03-08

### Deployed fitment

| Slot | Model | GPU | Context | Throughput | Status |
|------|-------|-----|---------|-----------|--------|
| Coordinator | Qwen3.5-27B-FP8 | 4×5070Ti TP=4 (64GB) | 32K (can increase to 131K) | 18.3 tok/s (MTP) | ✅ Live |
| Utility | Huihui-Qwen3-8B-abliterated-v2 | 4090 (24GB) | 32K | 59 tok/s | ✅ Live |
| Worker | Qwen3.5-35B-A3B-AWQ | 5090 (32GB) | 32K | 215 tok/s | ✅ Live |
| Embedding | Qwen3-Embedding-0.6B | 5060Ti (16GB, shared) | — | — | ✅ Live |
| Reranker | Qwen3-Reranker-0.6B | 5060Ti (16GB, shared) | — | — | ✅ Live |

**Note:** Qwen3.5-9B does NOT fit 4090 — MoE expert weights expand to ~25GB. Huihui-Qwen3-8B-abliterated is the utility model instead.

### Critical vLLM configuration

```bash
# ALL Qwen3.5 instances MUST include:
--tool-call-parser qwen3_xml      # XML format for Qwen3.5, qwen3_coder for Qwen3
--kv-cache-dtype auto             # FP8 KV corrupts GDN layers — NEVER use fp8
--enable-auto-tool-choice         # Required for tool calling
--enable-prefix-caching           # ~79% hit rate with shared agent prefixes
--enforce-eager                   # Required — DeltaNet Triton OOM without this
--language-model-only             # Prevent VLM encoder allocation

# vLLM nightly 0.16.1rc1.dev32 supports Qwen3.5 (not stable v0.16.0)
# Image: athanor/vllm:qwen35

# Speculative decoding: MTP-1 native to Qwen3.5 (83% throughput improvement)
--speculative-config '{"method": "mtp", "num_speculative_tokens": 1}'
```

### Quant sources (confirmed, high download counts)
- **Qwen3.5-27B-FP8:** `Qwen/Qwen3.5-27B-FP8` (288K downloads)
- **Qwen3.5-35B-A3B-AWQ:** `cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit` (97K downloads)
- **Qwen3.5-9B:** `Qwen/Qwen3.5-9B` (BF16 fits 4090 natively)

### Abliterated variants (for sovereignty/EoBQ)
- `huihui-ai/Huihui-Qwen3.5-35B-A3B-abliterated` (22K downloads, 192 likes)
- `huihui-ai/Huihui-Qwen3.5-27B-abliterated` (12K downloads)
- ⚠️ Tool-calling quality may degrade — test before production use

---

## 5. DEVELOPMENT TOOLCHAIN (4 tools on DEV)

### Tool roles

| Tool | Model Backend | Role | When |
|------|--------------|------|------|
| **Claude Code** | Anthropic API (Sonnet 4.6) | Complex architecture, multi-file porting, hard reasoning | Primary for hard tasks |
| **Aider** | LiteLLM → local Qwen3.5 | Pair programming, test-fix loops, single-file, routine | Routine work, overnight batch |
| **Goose** | LiteLLM → local Qwen3.5 | Reproducible Recipes, scheduled overnight ops | Infrastructure automation |
| **claude-squad** | Session manager for all above | Parallel git worktrees, auto-accept overnight | Always — manages sessions |

### Daily workflow pattern

```
MORNING:
  Review overnight claude-squad results (git log, test results)
  Merge passing branches, provide feedback on failures
  Queue next batch of tasks

HARD TASK (architecture, porting):
  cd ~/repos/athanor && claude
  # Uses Sonnet 4.6 via Anthropic API

ROUTINE TASK (tests, config edits):
  cs new "Write pytest for task engine" -p "aider --model hosted_vllm/worker"
  # Uses Qwen3.5-35B on WORKSHOP via LiteLLM

REPEATABLE INFRA:
  goose run --recipe recipes/port-hydra-module.yaml --module preference_learning
  goose schedule --recipe recipes/test-all-endpoints.yaml --every 2h

OVERNIGHT PARALLEL:
  cs new "Port self_diagnosis" -y -p "aider --model hosted_vllm/worker"
  cs new "Port resource_optimization" -y -p "aider --model hosted_vllm/worker"
  cs new "Port knowledge_optimization" -y -p "aider --model hosted_vllm/worker"
```

### Configuration files (in athanor-dev-setup.tar.gz)

```
claude-code/
├── CLAUDE.md                    # Ops center root (cluster topology, tool roles, sprint plan)
├── .claude-user/CLAUDE.md       # User-level persona (COO, Twelve Words, principles)
├── .claude/settings.json        # Pre-approved permissions (git, ssh, ansible, docker, vllm)
├── .claude/commands/
│   ├── audit-node.md            # /audit-node $NODE — SSH status report
│   ├── port-module.md           # /port-module $MODULE — Hydra→Athanor porting
│   ├── test-endpoint.md         # /test-endpoint $URL — 5-check validation
│   └── trace-feature.md         # /trace-feature $FEATURE — cross-repo analysis
└── .claude/rules/
    ├── vllm-safety.md           # Qwen3.5 serve flags (never fp8 KV, always qwen3_coder)
    ├── deployment-safety.md     # FOUNDRY read-only, WORKSHOP needs DEV validation
    └── reference-repos.md       # Extract algorithm, rewrite glue

aider/
└── .aider.conf.yml              # LiteLLM at vault:4000, auto-commits, ruff linting

goose/
├── profiles.yaml                # Default profile: LiteLLM local, Hard profile: Anthropic
└── recipes/
    ├── port-hydra-module.yaml   # Parameterized module porting workflow
    └── test-all-endpoints.yaml  # Cluster health check (schedulable)

install.sh                       # One script: installs all 4 tools + deploys all configs
```

---

## 6. REFERENCE REPOSITORIES

```
~/repos/
├── athanor/              ← THE LIVING SYSTEM. All changes go here.
├── reference/
│   ├── hydra/            ← Parts warehouse
│   │   ├── 370+ API endpoints, 66 MCP tools
│   │   ├── 41 n8n workflows (morning-briefing, rss-feed-processor, autonomous-research, etc.)
│   │   ├── Python modules: routellm, preference_learning, self_diagnosis,
│   │   │   resource_optimization, knowledge_optimization, capability_expansion
│   │   ├── Self-improvement loop (93.4% benchmark)
│   │   ├── Overnight autonomous research (2 AM cron)
│   │   ├── 22 EoBQ queen characters with portraits/voice
│   │   └── Full voice pipeline (wake word → Whisper → LLM → Kokoro TTS)
│   │
│   ├── kaizen/           ← Research artifact
│   │   ├── GWT cognitive architecture (Global Workspace Theory)
│   │   ├── 558-line workspace manager with salience scoring
│   │   └── Kubernetes/Talos (abandoned — too complex for one person)
│   │
│   ├── local-system/     ← Design docs (newest iteration)
│   │   ├── CLAUDE.md, VISION.md, STRUCTURE.md
│   │   ├── Confidence-based escalation protocol (>0.8 act / 0.5-0.8 notify / <0.5 hold)
│   │   └── References all other repos as /opt/reference/
│   │
│   └── system-bible/     ← Locked hardware decisions
```

### What to port from Hydra (one module per day)
1. `routellm.py` → LiteLLM routing enhancement
2. `preference_learning.py` → feedback loop from LangFuse traces
3. `self_diagnosis.py` → health monitoring agent
4. `resource_optimization.py` → GPU utilization intelligence
5. `knowledge_optimization.py` → knowledge graph maintenance
6. `capability_expansion.py` → self-improvement loop

### n8n workflows to import
Priority order: morning-briefing → rss-feed-processor → autonomous-research → knowledge-refresh → learnings-capture → health-digest → model-performance-tracker

---

## 7. OBSERVABILITY STACK

### LangFuse v3 (deploy on VAULT:3030)
- 6-service Docker Compose: web, worker, PostgreSQL, ClickHouse, Redis, MinIO
- 4 vCPUs, 16GB RAM, 100GB storage minimum
- LiteLLM integration: `success_callback: ["langfuse"]`
- Prompt management: version numbering, labels (production/staging), A/B testing
- Per-agent prompt versioning in folders: `agents/router`, `agents/researcher`, etc.
- Custom cost tracking for local models (amortized GPU cost per token)

### Arize Phoenix (supplement, single container)
- `docker run -p 6006:6006 arizephoenix/phoenix:latest`
- Superior agent graph visualization for debugging multi-agent flows
- No prompt management — use alongside LangFuse, not instead of

### Evaluation pipeline
- **Promptfoo** for YAML-based eval definitions with LLM-as-judge
- **LangFuse traces** feed evaluation data
- 100 representative requests across 10 task categories for accelerated eval
- Gitea Actions CI: every prompt change gets tested before merge

---

## 8. INTELLIGENCE PIPELINE (Unbuilt — highest impact new feature)

### Architecture
```
Inoreader Pro ($90/yr)  ─────────────────────┐
F5Bot (Reddit/HN monitoring) ────────────────┤
changedetection.io (web page monitoring) ────┤
hnrss.org (Hacker News RSS) ─────────────────┤──→ Miniflux ──→ n8n workflows ──→ Athanor agents
Reddit RSS ──────────────────────────────────┤      (RSS hub)    (AI processing)   (action/store)
MonitoRSS ───────────────────────────────────┘
```

### Four intelligence functions
1. **Model horizon scanning** — new model releases, benchmark results, quant availability
2. **Infrastructure/dependency monitoring** — vLLM releases, LiteLLM updates, security patches
3. **Tool ecosystem evolution** — new MCP servers, agent frameworks, development tools
4. **Business/regulatory tracking** — RESNET standards, IECC updates, ENERGY STAR changes

### Integration with existing agents
- Knowledge Agent (currently disabled, 24h cycle) becomes the intelligence pipeline host
- Or create Agent #9 dedicated to intelligence gathering
- Feed classified signals into Qdrant vectors + Neo4j knowledge graph
- Generate morning briefing at 6 AM from overnight signal processing

---

## 9. QUALITY CASCADE / MODEL ROUTING

### Three-tier cascade via LiteLLM
```
Tier 1: Utility (Qwen3.5-9B on 4090)     ← Fast, cheap, handles ~70-80% of requests
  ↓ fallback (confidence < threshold)
Tier 2: Coordinator (Qwen3.5-27B on TP=4) ← Strong reasoning, complex tasks
  ↓ fallback (still insufficient)
Tier 3: Cloud (Claude Sonnet 4.6)          ← Frontier quality, costs money
```

### RouteLLM integration
- LMSYS framework, ICLR 2025, uses `mf` (matrix factorization) router
- Trained on Chatbot Arena data, generalizes across model pairs without retraining
- Up to 85% cost reduction at 95% of GPT-4 quality
- Natively uses LiteLLM for backend routing
- Port from Hydra's `routellm.py` into Athanor's LiteLLM config

---

## 10. CREATIVE PIPELINE (Empire of Broken Queens)

### Character generation
- **FLUX.1 Kontext** (12B) on RTX 5090 — native character consistency, ~10s/image
- LoRA training via AI Toolkit or Flux Gym for per-character identity
- PuLID Flux II for facial identity preservation
- IP-Adapter for style transfer
- ComfyUI workflows for automated generation

### Voice
- **Kokoro TTS v1.0** (82M params, Apache 2.0) — 210× real-time on RTX 4090
- 54+ voices, voice blending for per-character profiles
- Kokoro-FastAPI server with OpenAI-compatible Speech API
- ⚠️ No native emotion control — consider Chatterbox for emotion-critical characters

### Video
- **Wan2.1** (14B) on RTX 5090 — ~25 clips/hour at 480P, ~28GB VRAM
- Wan2.2 (July 2025) uses MoE, same inference cost, better quality
- T2V, I2V, and video editing supported

### Procedural dialogue
- Qwen3.5-35B-A3B (abliterated) for in-character generation
- Relationship tracking via Neo4j
- Branching storyline state management in Redis

---

## 11. BUSINESS CONTEXT (Ulrich Energy)

### Current operations
- RESNET-certified HERS Rating S-Corp, Dayton MN
- Blower door, duct leakage, ENERGY STAR MFNC testing
- Primary client: M/I Homes, Twin Cities metro
- Field colleague: Erik Kittilstved
- Pricing: $350 full tests, $100 site visits, $200 blower door, $400/unit MF EnergyStar

### Regulatory landscape
- **Minnesota:** Still on 2012 IECC (CZ 6A, 3.0 ACH50). Update process started (HF 5242A), won't take effect until ~2027.
- **RESNET:** ANSI/RESNET/ICC 380-2022 + Addendum A-2023 current. 301-2022 mandatory July 2025.
- **ENERGY STAR MFNC:** v1.1 Rev.05 current. v1.2 required nationally Jan 1, 2027 (prerequisite for §45L tax credit $2,500/unit). v1.3 finalized with 3.5 ACH50 backstop.
- **ENERGY STAR program:** Survived elimination attempt May 2025. Congress funded $33M FY2026.
- **HERS software:** Ekotrope RATER v5.2 (~85% market share). No AI/ML-powered tools exist commercially.

### Athanor-powered opportunities
- Airtight-IQ forecasting engine (predicting duct leakage from BKI data)
- AI-assisted report generation from DG-1000 test data
- Automated BKI Tracker updates from Google Calendar sync

---

## 12. BUILD SPRINT PLAN

### Week 0: Tonight (DEV setup)
1. SSH into DEV, extract `athanor-dev-setup.tar.gz`, run `install.sh`
2. Set `ANTHROPIC_API_KEY` in `~/.bashrc`
3. SSH key distribution: DEV → FOUNDRY, WORKSHOP, VAULT
4. Clone all repos: `git clone` athanor + 4 reference repos
5. Verify connectivity: `ssh foundry`, `curl http://vault:4000/health`

### Week 1: Model swap on WORKSHOP
1. Install vLLM v0.17.0 on WORKSHOP (not nightly — v0.17.0 is stable now)
2. Download `cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit` to WORKSHOP
3. Serve on 5090 with full Qwen3.5 flags (see Section 4)
4. Keep Qwen3-14B on 5060Ti as fallback
5. Update LiteLLM config on VAULT (add new model, update routing)
6. Deploy LangFuse v3 on VAULT:3030
7. Run test harness against all endpoints
8. Validate via LangFuse traces

### Week 2: FOUNDRY upgrade + intelligence port begins
1. Download `Qwen/Qwen3.5-27B-FP8` to FOUNDRY (only after WORKSHOP stable 7 days)
2. Serve on TP=4 with full Qwen3.5 flags
3. Add Qwen3.5-9B on 4090 as utility
4. Begin porting Hydra modules (one per day): routellm → preference_learning → self_diagnosis
5. Import priority n8n workflows: morning-briefing, rss-feed-processor

### Week 3: Compound loop
1. Continue porting: resource_optimization → knowledge_optimization → capability_expansion
2. Import remaining n8n workflows
3. Configure overnight autonomous operations (research, creative gen, maintenance)
4. Run accelerated eval: 100 requests across 10 categories
5. Switch all workflows to steady-state schedules
6. Let it compound.

---

## 13. SECURITY & SOVEREIGNTY

### Environment variables for zero telemetry
```bash
export HF_HUB_DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
export VLLM_CONFIGURE_LOGGING=0
export TRANSFORMERS_OFFLINE=1         # After models cached
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### Model integrity
- Use safetensors format ONLY (audited, safe from arbitrary code execution)
- Pin model versions by commit hash, never `main` branch
- `hf cache verify` after every download

### MCP security
- Recipe poisoning via invisible Unicode characters (Block red team finding)
- Execute MCP servers in sandboxed containers with `--network=none --read-only`
- Enforce least-privilege per tool
- nftables default-deny egress on inference nodes

---

## 14. DEEP RESEARCH BACKLOG

### 🔴 Blocking (this week)
- [ ] 2.1 — vLLM v0.17.0 install and Qwen3.5 validation ✅ RESEARCHED
- [ ] 6.1 — LangFuse v3 deployment ✅ RESEARCHED
- [ ] 1.1 — Qwen3.5 quant selection and VRAM validation ✅ RESEARCHED

### 🟡 High-impact (next week)
- [ ] 3.1 — General Assistant delegation upgrade (read `_build_task_prompt()`)
- [ ] 5.1 — Claude Code via local models (ANTHROPIC_BASE_URL) ✅ RESEARCHED
- [ ] 4.2 — Hydra n8n workflow portability (can JSONs import directly?)
- [ ] 1.5 — RouteLLM / Quality Cascade integration ✅ RESEARCHED
- [ ] 1.2 — Qwen3-Coder-Next evaluation for Coding Agent slot ✅ RESEARCHED
- [ ] 1.3 — Abliterated Qwen3.5 tool-calling quality testing ✅ RESEARCHED
- [ ] 8.5 — 5090 idle problem root cause (routing rules? delegation logic?)

### 🟢 Enhancement (week 3+)
- [ ] 2.2 — SGLang AWQ fix status (issue #19644 still open) ✅ RESEARCHED
- [ ] 2.3 — Prefix caching optimization for multi-agent prompts ✅ RESEARCHED
- [ ] 2.4 — RTX 5070Ti/5090 SM120 kernel optimizations ✅ RESEARCHED
- [ ] 2.5 — Triton autotuner cold start mitigation
- [ ] 3.2 — GWT salience scoring vs simple delegation A/B test
- [ ] 3.3 — AdaptOrch topology-aware routing implementation ✅ RESEARCHED
- [ ] 3.4 — Inference-aware agent scheduling (vLLM queue depth)
- [ ] 3.5 — Letta (MemGPT) v0.16 evaluation ✅ RESEARCHED
- [ ] 4.1 — Miniflux + n8n intelligence pipeline deployment ✅ RESEARCHED
- [ ] 5.2 — Claude Code Swarms / Agent Teams ✅ RESEARCHED
- [ ] 5.3 — Goose Recipes for infrastructure automation ✅ RESEARCHED
- [ ] 5.5 — Promptfoo eval-driven development ✅ RESEARCHED
- [ ] 6.2 — Arize Phoenix deployment ✅ RESEARCHED
- [ ] 6.3 — Accelerated evaluation methodology
- [ ] 7.1 — EoBQ character portrait pipeline (FLUX Kontext) ✅ RESEARCHED
- [ ] 7.4 — Kokoro TTS voice pipeline ✅ RESEARCHED
- [ ] 7.3 — Wan2.1/2.2 video generation ✅ RESEARCHED
- [ ] 8.2 — Ansible playbook for Qwen3.5 model swap
- [ ] 8.3 — Overnight autonomous operation patterns
- [ ] 8.4 — Gitea + Gitea Actions CI/CD
- [ ] 11.1-11.4 — RESNET/ENERGY STAR/MN code updates ✅ RESEARCHED

### ⚪ Exploratory (as time permits)
- [ ] 1.4 — Speculative decoding with MTP-1 ✅ RESEARCHED
- [ ] 1.6 — Emerging architectures (MoD, Mamba-3, RWKV-7)
- [ ] 2.6 — llama.cpp as alternative backend
- [ ] 3.6 — A2A protocol for peer agent communication ✅ RESEARCHED
- [ ] 4.4 — Audio intelligence layer (Snipd, Readwise, NotebookLM)
- [ ] 4.5 — Agentic RSS with LLM classification
- [ ] 5.4 — OpenCode orchestrator ecosystem
- [ ] 5.6 — Context engineering patterns (RLMs, context folding)
- [ ] 6.4 — Local inference benchmark suite
- [ ] 6.5 — Continuous agent quality monitoring
- [ ] 7.2 — FLUX.1 ComfyUI pipeline optimization
- [ ] 7.5 — Procedural LLM dialogue for EoBQ
- [ ] 7.6 — Mobile Stable Diffusion (Galaxy S21 Ultra)
- [ ] 8.1 — DEV node IP assignment and Ansible inventory
- [ ] 8.6 — MTU mismatch across nodes
- [ ] 9.1-9.3 — Home/media automation depth
- [ ] 10.1-10.3 — MCP/A2A/AGENTS.md standards
- [ ] 12.1 — The 10 novel enhancement ideas:
  1. Taste profiles via Qdrant
  2. Interruption intelligence
  3. Unified conversational router
  4. Content discovery from implicit preference signals
  5. Context-aware notification batching
  6. Predictive pre-computation
  7. Skill transfer between agents
  8. Failure mode learning
  9. Temporal pattern recognition
  10. Emergent capability discovery
- [ ] 12.2 — Knowledge graph density optimization
- [ ] 12.3 — Qdrant collection optimization
- [ ] 12.4 — Compound learning loop metrics
- [ ] 13.1-13.3 — Security hardening ✅ RESEARCHED
- [ ] 14.1-14.3 — Hardware optimization (loose inventory, thermal, power)

---

## 15. KEY DECISIONS MADE THIS SESSION

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Don't rebuild — upgrade Athanor | 4 rebuilds with same vision. Infrastructure churn resets intelligence to zero. |
| 2 | Qwen3.5-27B-FP8 for Coordinator | Fits 4×5070Ti TP=4 at 131K context. Hybrid GDN architecture keeps KV tiny. |
| 3 | Qwen3.5-35B-A3B-AWQ for Worker | Fits 5090 at 128K. Solves 99.13% GPU idle problem. |
| 4 | Qwen3.5-9B for Utility | BF16 fits 4090 natively at full context. Routing/classification tasks. |
| 5 | vLLM v0.17.0, not nightly | First stable release with Qwen3.5. v0.18 doesn't exist yet. |
| 6 | BF16 KV cache only | FP8 KV corrupts GDN layers. --kv-cache-dtype auto always. |
| 7 | --tool-call-parser qwen3_coder | Qwen3.5 uses XML format, not hermes. |
| 8 | 4 dev tools, specific roles | Claude Code (hard), Aider (routine), Goose (recipes), claude-squad (parallel). |
| 9 | Claude Code for hard tasks on Anthropic API | Sovereignty for routine work, cloud quality for architecture decisions. |
| 10 | Hydra is a parts warehouse, not a blueprint | Port modules one at a time. Don't rebuild the house to match the warehouse. |
| 11 | FOUNDRY never at risk during sprint | All testing on DEV → WORKSHOP → FOUNDRY only after 7 days stable. |
| 12 | LangFuse for observability | Air-gapped, full LiteLLM integration, prompt versioning for 8 agents. |
| 13 | RouteLLM mf router for quality cascade | 85% cost reduction at 95% quality. Natively uses LiteLLM. |
| 14 | MTP-1 for speculative decoding | Draft-model speculative decoding broken in vLLM V1. MTP works. |
| 15 | Knowledge Agent or Agent #9 for intelligence pipeline | Miniflux → n8n → LangGraph → agents. Highest impact unbuilt feature. |

---

## 16. OPEN RISKS

| Risk | Impact | Mitigation |
|------|--------|------------|
| SGLang AWQ still broken (#19644) | Can't use RadixAttention with quantized MoE | Use vLLM prefix caching instead. Monitor issue. |
| Abliterated models degrade tool-calling | EoBQ needs uncensored + tool use | Test before production. Heretic (DPO) variants may be better. |
| FP8 KV cache corruption | Silent output degradation | Enforced via .claude/rules/vllm-safety.md. Never use fp8 KV. |
| MCP prompt injection | Recipe poisoning, Unicode smuggling | Sandboxed execution, Unicode stripping, input validation. |
| Context ceiling with local Claude Code | 32K-65K limits hit fast in agentic sessions | Use Aider for routine work, Claude Code for hard tasks only. |
| ENERGY STAR MFNC v1.2 Jan 2027 | Must prepare for national compliance | Track requirements, update testing protocols. |
| The rebuild cycle | Zetetic impulse to start over | "Don't rebuild. Upgrade. Let it compound." Enforced in CLAUDE.md. |

---

*This document is the single source of truth. It lives at `~/repos/ATHANOR-MAP.md` and updates as the system evolves. When in doubt, read this first.*

# ATHANOR-MAP ADDENDUM — March 7, 2026 (Late Session)

**Append this to ATHANOR-MAP.md on DEV. These sections were developed after the initial map.**

---

## 17. VERIFIED CLUSTER STATE (Live, March 7 2026 ~3:00 PM CT)

| Node | SSH | User | GPUs Confirmed | Services Running | Services NOT Running |
|------|-----|------|----------------|-----------------|---------------------|
| FOUNDRY (.244) | OK | athanor | 4x5070Ti + 4090 | vLLM on :8000 | :8001 (utility slot empty) |
| WORKSHOP (.225) | OK | athanor | 5090 + 5060Ti | Dashboard on :3001 | vLLM :8100/:8101 CLOSED |
| VAULT (.203) | OK | root | Intel A380 | LiteLLM :4000, Qdrant :6333, Redis :6379 | LangFuse :3030 NOT deployed |
| DEV (.189) | local | shaun | 5060Ti | Claude Code + dev tools | N/A |

Corrections: DEV IP=.189 (was TBD), DEV NIC=5GbE Realtek (not 10GbE), SSH users: DEV=shaun FOUNDRY/WORKSHOP=athanor VAULT=root, both keys (id_ed25519 + athanor_mgmt) needed on all nodes.

---

## 18. MOBILE OPS STACK (Permanent)

Phone (S21 Ultra) via Tailscale to VAULT services:
- Open WebUI :3080 (chat, RAG with Qdrant, MCP tools, voice, PWA) - connects to LiteLLM :4000
- Grafana :3000 (GPU/service dashboards, push alerts to Telegram)
- LangFuse :3030 (agent traces, prompt versioning)
- Termux+Mosh to DEV (full Claude Code terminal, survives network drops)
- GitHub Mobile (PR review for overnight runs)

DEV needs: mosh installed. Open WebUI connects to existing LiteLLM+Qdrant on VAULT.

---

## 19. BLEEDING-EDGE TOOLS (Evaluated)

Install now: claude-tmux (session TUI), claude-esp (hidden output viewer), parry (injection scanner).
Evaluate Week 2: OpenClaw (messaging gateway), DeerFlow 2.0 (study middleware patterns), Composio Orchestrator (just-in-time tools).
Skip: CrewAI, AutoGen, MetaGPT, Dify, Langflow, any cloud-dependent tool.

---

## 20. THREE-AGENT COGNITIVE ARCHITECTURE

Prometheus (27B-FP8, FOUNDRY TP=4) = coordinator, only voice user hears.
Worker Pool (35B-A3B-AWQ, WORKSHOP 5090) = undifferentiated, role prompts per task.
Sentinel (9B, FOUNDRY 4090) = always-on monitoring, classification, embedding.

Existing 8 agents: don't consolidate, enhance. Three-agent is future delegation logic.
Autonomy gradient: Level 0 (now) through Level 4 (future). Start with intelligence pipeline.

---

## 21. CORRECTED SPRINT PLAN

Week 0 (DONE): DEV bootstrapped, all tools+configs+repos, SSH verified.
Week 1: Fix SSH config, install mosh, deploy Open WebUI + LangFuse on VAULT, vLLM v0.17.0 + Qwen3.5-35B-A3B on WORKSHOP 5090, update LiteLLM, test harness.
Week 2: FOUNDRY upgrade (only after 7 days stable), Hydra module porting, n8n workflows, Grafana dashboards.
Week 3: Intelligence pipeline (Miniflux+n8n), Telegram bot, Grafana alerts, accelerated eval.
Week 4: Autonomous tasks, overnight claude-squad, steady-state rhythm.
