# Athanor System Map — Everything at a Glance
*Updated March 18, 2026. The complete picture.*

## The Vision (PLAN3.md)
> Give Athanor a goal → it turns that into work → chooses the right lane → runs it → shows what happened → fails visibly, retries safely.

## The Principle (PLAN 2.md)  
> Don't depend on cloud permission. Don't waste frontier capability.

## The 7 Concepts

### 1. COMPUTE (what runs the AI)
```
FOUNDRY (.244) — 5 GPUs, EPYC 56-core, 219GB RAM
├── GPU 0,1,3,4 (TP=4): Qwen3.5-27B-FP8 (general reasoning, vision)
├── GPU 2 (4090): Qwen3.5-35B-A3B-AWQ (coder)
└── 50+ services: agents, gpu-orch, TTS, STT, Crucible, Qdrant(old)

WORKSHOP (.225) — 2 GPUs, TR 7960X, 125GB RAM  
├── GPU 0 (5090): Creative (images, video) — NOT a 3rd LLM copy
├── GPU 1 (5060Ti): Scoring + uncensored models
└── Dashboard, EoBQ, Ulrich Energy, Open WebUI, ComfyUI

DEV (.189) — 1 GPU, Ryzen 9, 60GB RAM
├── GPU (5060Ti): Embedding + Reranker + future Qwen3.5-9B
└── All coding tools, Claude Code, Local-System services

VAULT (.203) — No GPU, 9950X, 123GB RAM, 200TB storage
└── 47 containers: LiteLLM, databases, monitoring, media, HA

DESK (.50) — RTX 3060 12GB, i7-13700K, 64GB RAM
└── SSH terminal to DEV + local content gen stack
```

### 2. STORAGE (where data lives)
- VAULT 164TB array (85% full, 26TB free) + 5 NVMe
- FOUNDRY 8.1TB NVMe (92% free, models on 990 PRO)
- WORKSHOP 5.5TB NVMe (97% free, 2x T700 EMPTY → rsync models here)
- DEV 5.5TB NVMe (98% free, /data 3.4TB empty)
- Backups: PG daily, Neo4j/Qdrant weekly (Qdrant/Neo4j FAILING since Mar 14)

### 3. SERVICES (what's running)
- **LiteLLM** (VAULT:4000) — routes ALL local model requests
- **LangGraph agents** (FOUNDRY:9000) — 9 agents, 77 tools, 16% success rate
- **GPU Orchestrator** (FOUNDRY:9200) — 4 zones, metrics, sleep/wake broken
- **Langfuse** (VAULT:3030) — LLM tracing (BROKEN, keys empty)
- **Prometheus** (VAULT:9090) — 27+ alert rules, 17 service probes
- **ComfyUI** (WORKSHOP:8188) — FLUX + PuLID image gen
- **Speaches** (FOUNDRY:8200) — Kokoro TTS (ALREADY DEPLOYED)
- **Home Assistant** (VAULT:8123) — FULLY WIRED with JWT token
- **50+ total services** across 4 nodes

### 4. GENERATION (what creates content)
- **Auto_gen pipeline**: BROKEN 11 days (dead LLM endpoint) — fix in Phase 0
- **Image gen**: FLUX + PuLID + ReActor on WORKSHOP 5090
- **Video gen**: LTX 2.3 (planned, NVFP4 on 5090)
- **Voice**: Kokoro TTS (deployed), Whisper STT (deployed), Dia TTS (planned)
- **Creative models**: JOSIEFIED-Qwen3-8B (planned), Dolphin 3.0
- **Scoring**: Aesthetic Predictor V2.5 (planned), custom MLP
- **DESK stack**: SD WebUI Forge + Wan 2.2 + audio tools

### 5. OPERATIONS (what keeps it running)
- **Prometheus + Grafana** — comprehensive monitoring (27+ rules, 5 dashboards)
- **ntfy** (VAULT:8880) — push notifications
- **Container watchdog** — auto-restarts Plex/Sonarr/Radarr/HA every 5 min
- **Daily crons** — backups, consolidation, cleanup
- **Session hooks** — /morning command, health checks, enriched start
- **Presence model** — at desk / away / asleep / phone-only

### 6. SECURITY (what keeps it safe)  
- **Content Governance Matrix**: 5 classes routing by sensitivity
  - cloud_safe → any provider
  - private → trusted cloud or local
  - hybrid_abstractable → cloud sees structure only
  - refusal_sensitive → LOCAL ONLY (NSFW, adult)
  - sovereign_only → LOCAL ONLY (pen testing, credentials)
- **LiteLLM content_policy_fallbacks** → auto-route to uncensored local on refusal
- **Greywall** (planned) — kernel sandbox for autonomous agents
- **Docker socket proxy** — LAN-only Docker API access
- **UFW** — SSH + LAN rules only

### 7. KNOWLEDGE (what it remembers)
- **6-tier memory**: Working (Redis) → Episodic (Qdrant) → Semantic (Neo4j) → Procedural (PG) → Resource (Qdrant+Meilisearch) → Vault (PG+Qdrant)
- **Performer DB**: 801 records, enrichment merge ready
- **Knowledge graph**: Neo4j, 3237 nodes
- **Intelligence pipeline**: Miniflux (deployed) → n8n (deployed) → agents → Neo4j
- **Hindsight** (evaluate) — MCP-native agent memory

## The Governor (HOW you interact with it all)

```
YOU (at DESK or phone)
  │
  ▼
Claude Code (Opus 4.6) ← interactive governor
  │
  ├─ Does it itself (complex architecture, design)
  │
  ├─ Delegates to subscription CLIs:
  │   ├── Codex CLI (GPT-5.4, terminal workflows)
  │   ├── Kimi CLI (K2.5 Agent Swarm, breadth)
  │   ├── Gemini CLI (free 1000/day, 1M context)
  │   └── Z.ai GLM (fact-checking, classification)
  │
  ├─ Delegates to local tools ($0):
  │   ├── Aider (structured file editing via LiteLLM)
  │   ├── Goose (repeatable recipes via LiteLLM)
  │   ├── OpenCode (overflow, any provider)
  │   └── Local vLLM directly (unlimited)
  │
  ├─ Routes NSFW/sensitive → SOVEREIGN lane:
  │   ├── JOSIEFIED-Qwen3-8B (abliterated)
  │   ├── Dolphin 3.0 (zero refusal)
  │   └── ComfyUI + FLUX uncensored LoRA
  │
  ├─ Submits to autonomous agents (runs 24/7):
  │   └── LangGraph 9 agents, 77 tools (FOUNDRY:9000)
  │
  └─ Triggers content generation:
      ├── Auto_gen pipeline (images, 2hr cycle)
      ├── LTX 2.3 (video, on demand)
      └── Dia/Kokoro (voice synthesis)
```

## What's Broken (Fix in Phase 0, ~2 hours)
1. Auto_gen LLM endpoint dead (FOUNDRY:8004 → LiteLLM creative)
2. Langfuse API keys empty (restore pk/sk on LiteLLM container)
3. Agent Qdrant URL wrong (FOUNDRY:6333 → VAULT:6333)
4. LiteLLM 24-min failover (add stream_timeout + num_retries)
5. WORKSHOP models on NFS (rsync to local T700 NVMe)
6. Qdrant + Neo4j backups failing since March 14
7. Coding route → wrong model (coordinator instead of coder)
8. Vision route → dead endpoint
9. Agent coding timeout too short (600s → 1800s)

## 20 Projects Being Managed
P0: athanor, Local-System (infrastructure)
P1: Field_Inspect, BKI-Tracker, ulrich-energy (business)
P2: Empire of Broken Queens, amanda-med-tracker (personal)
P3: Portfolio apps, Kindred concept (future)

## 10 Subscriptions ($543/mo, ALL sunk cost — maximize)
Claude Max $200, ChatGPT Pro $200, Gemini $20, Copilot $33,
Z.ai GLM $30, Perplexity $20, Kimi $19, Venice $12, Qwen $10, Mistral $0
