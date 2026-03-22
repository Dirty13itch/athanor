# Athanor Full-Stack Architecture & Implementation Plan
**Date:** 2026-03-18 | **Status:** Complete Draft | **Evidence:** 32 agents, 34 docs, 312 verified items

## Non-Negotiables
- Zero per-token LLM API costs. Local models ($0) + flat-rate subscriptions ($0 marginal) only.
- Service APIs (HuggingFace, Tavily, Langfuse, etc.) are fine.
- All development tooling lives on DEV (192.168.1.189), accessed from DESK via SSH/tmux.
- DEV has 5GbE.

## 10 Locked Architectural Decisions
1. Claude Code is primary interactive tool
2. LiteLLM is single routing layer for all local model access
3. Subscription CLIs before BYOK tools
4. Coolify on DEV for internal deploys (not yet installed)
5. Cloudflare Pages for production public frontends
6. FOUNDRY is production - never modify without approval
7. Qwen3.5-35B-A3B is primary local model (deployed)
8. LTX 2.3 is primary video gen
9. SDXL + CivitAI LoRAs for character art; FLUX.2 Dev for photorealism
10. No VS Code lock-in; core workflow is terminal-native
11. ALL EoBQ/NSFW traffic stays local - zero cloud
12. Infrastructure Guardian agent must be sovereign/local-only
13. No peer-to-peer agent communication (centralized orchestrator only)
14. No agent self-modification

## LAYER 1: THE GOVERNOR (Claude Code on DEV)

### Governor Routing Matrix (for delegate skill)
Task Pattern | Tool | Model Source
Complex architecture | Claude Code (Opus) | Max sub
Multi-file coordinated | Agent Teams (7 parallel) | Max sub
Bulk file editing | Aider architect/editor | LiteLLM local
Terminal debugging | Codex CLI | ChatGPT Pro sub
Deep research | Perplexity Deep Research | Perplexity Pro sub
1M context ingestion | Gemini CLI | Gemini Advanced sub
Parallel breadth | claude-squad or Kimi Swarm | Multi-sub
Repeatable ops | Goose Recipes | LiteLLM local
NSFW creative | JOSIEFIED-Qwen3-8B | Local only
Background monitoring | LangGraph agents | Local only
Quick question | Gemini CLI | Free 1000/day
Code review | /code-review plugin | 5x Sonnet
Structured feature | Deep Trilogy | Max sub
Large feature TDD | Compound Engineering | Max sub

### Intelligence Layer
- Intent classifier: Qwen3.5-4B on DEV
- Complexity scorer: token count, code presence, reasoning markers
- Priority routing: task class x privacy x stakes = model selection
- Token budget tracking via anthropic-ratelimit-unified-5h-utilization header
- Effort scaling: simple=1 agent, comparison=2-4, research=5-10+, coding=sequential

### Techniques (local model advantages)
- Best-of-N: 16-32 variations, ModeX spectral clustering (no reward model)
- Context compression: local 30B compresses 50K to 2K for cloud injection
- Afterburner loops: generate-exec-capture-refine hundreds of times at $0
- Living specification: immutable spec.md before dispatching workers
- Best-of-N per task type: bugfix N=8, testgen N=4, compression N=4

## LAYER 2: CODING TOOL ECOSYSTEM (all on DEV)

### Primary (daily use)
Claude Code CLI | Installed | Max sub
Aider 0.86.2 | Installed | LiteLLM local (update model names)
Gemini CLI 0.33.1 | Installed | Gemini sub
Codex CLI 0.114.0 | Installed | ChatGPT Pro sub
Roo Code | NOT INSTALLED | 9-mode LiteLLM routing - INSTALL
Goose 1.27.2 | Installed | LiteLLM + Anthropic profiles
claude-squad | Installed UNUSED | Multi-CLI orchestration - ACTIVATE

### Orchestration
Agent Teams | Not enabled | ENABLE env var
Compound Engineering | Marketplace added | INSTALL
Deep Trilogy | Marketplace added | INSTALL
Superpowers | Active | Already using

### IDE Extensions (DESK)
Cline, Tongyi Lingma, Kimi Code ext, Mistral Code ext, Copilot Pro+

### Install Later
Kimi Code CLI, Qwen Code CLI, OpenCode, Continue, Kilo Code, recall, Claude-Mem, Promptfoo, MuTAP

### Evaluate
OpenHands, RA.Aid, Kiro, Jules, Augment Code, Crush CLI, gptme, Plandex, Qodo

## LAYER 3: LiteLLM ROUTER (VAULT:4000)
v1.81.9, 33 entries. 10 cloud keys NOT SET. Langfuse keys empty.

### Fixes Required
- coding alias: FOUNDRY:8000 -> FOUNDRY:8006
- vision alias: WORKSHOP:8010 -> FOUNDRY:8000
- Add stream_timeout: 10 to all local entries
- Add num_retries: 0 to all local entries
- Add model_info with supports_function_calling: true
- Remove deepseek from fallback chains
- Set Langfuse keys: pk-lf-athanor / sk-lf-athanor
- Consolidate 6 identical WORKSHOP aliases

## LAYER 4: LOCAL MODEL SERVING (vLLM 0.13.0 NVIDIA build)

### Current
vllm-coordinator | FOUNDRY GPU 0,1,3,4 | Qwen3.5-27B-FP8 | MTP, prefix-cache, language-model-only, swap-space 16
vllm-coder | FOUNDRY GPU 2 (4090) | Qwen3.5-35B-A3B-AWQ-4bit | NO swap-space, NO MTP
vllm-node2 | WORKSHOP GPU 0 (5090) | Qwen3.5-35B-A3B-AWQ-4bit | NFS mount, NO swap-space
vllm-vision | WORKSHOP GPU 1 (5060Ti) | Qwen3-VL-8B-FP8 | EXITED

### Changes
1. Coordinator: remove --language-model-only, add --limit-mm-per-prompt video=0 image=2, increase swap to 32
2. Coder: add --swap-space 16
3. Node2: add --swap-space 16, change NFS to local /mnt/fast1/models
4. Vision: deprecate (coordinator handles vision)
5. Stay on vLLM 0.13.0 (working, upgrade later)

### Future Deployments
Qwen3.5-4B on DEV (P1, router/classifier, ~8GB)
Qwen3.5-9B on FOUNDRY 4090 or WORKSHOP 5090 (P1, fast draft, ~18GB)
JOSIEFIED-Qwen3-8B on WORKSHOP 5060Ti (P1, EoBQ, ~9GB Q8)
Qwen3-Embedding-8B upgrade (P1, MTEB 70.58)
Whisper large-v3 (P1, STT, ~3GB)
Devstral Small 2 24B (Evaluate, 68% SWE-bench)
Big play: ik_llama.cpp + Qwen3.5-397B on FOUNDRY 219GB RAM

## LAYER 5: AUTONOMOUS AGENTS (FOUNDRY:9000)
9 deployed, 77 tools, 16% success rate

### Fixes
- Qdrant URL: FOUNDRY:6333 -> VAULT:6333
- coding-agent timeout: 600s -> 1800s
- Graceful shutdown + task persistence
- Seed trust system

### Scheduling: APScheduler (LangGraph Platform cron is paid-only)
### Triggers: Prometheus Alertmanager webhooks
### Safety: READ_ONLY auto / WRITE_SAFE log / DESTRUCTIVE interrupt
### State: PostgresSaver on VAULT, stable thread_ids

### 5 Undeployed Agents
Evaluator (T2) | Fact-checker (T2) | Voice interface (T3) | HERS Energy (T4) | EoBQ Game (T4)

## LAYER 6: GPU ORCHESTRATOR (FOUNDRY:9200)
4 zones, 10 endpoints. Fix coder zone, remove broken sleep/wake, metrics only.

## LAYER 7: OBSERVABILITY
Prometheus VAULT:9090 | Grafana VAULT:3000 | Langfuse VAULT:3030 (FIX keys)
ntfy VAULT:8880 | DCGM FOUNDRY+WORKSHOP:9400 | Bash health script (NEW)
Install: Promptfoo for model A/B testing

## LAYER 8: CONTENT PIPELINE

### Auto_Gen - BROKEN since March 7
Fix: LLM_API_URL -> http://192.168.1.203:4000/v1, LLM_MODEL -> creative
Clean 113 empty drop folders. Rebuild gateway venv.
Pipeline: Scheduler 2hr, 18 subjects, 45 themes, 801 performers

### Quality Scoring (NEW)
Phase 1: Aesthetic Predictor V2.5 on WORKSHOP 5060Ti (1.5GB, no NSFW bias, 5-15ms/img)
Phase 2: Custom MLP on SigLIP embeddings (rate 1000 images, train on CPU in seconds)

### Performer Data
801 records, enrichment merge ready. waist 0->86%, hip 0->86%, tosi_score new@82%
6 new fields, 5 dead fields removed. Complete merge script ready.

### Video - LTX 2.3 (NEW)
NVFP4 on WORKSHOP 5090 (31.2GB tight fit). Fallback: GGUF Q4_K_M (14.3GB).
~25s for 720p/4s. Unified audio+video. ComfyUI nightly required.

### Voice (NEW)
Dia 1.6B (~10GB, dual-speaker, 17 emotions) | Kokoro 82M (CPU, 210x RT)
Whisper large-v3 (~3GB, faster-whisper) | Orpheus 3B (voice cloning)

### EoBQ Creative Pipeline
Character art: SDXL LoRAs -> FLUX.2 Dev -> LTX 2.3 -> Dia TTS
19-Trait Sexual Personality DNA system
JOSIEFIED-Qwen3-8B mandatory. Nous Hermes 3 for character voice.
Character memory: Qdrant + Neo4j. ALL traffic local.

### Crucible GPU Scavenger - DEPRECATE
5% success rate. auto_gen pipeline is superior.

## LAYER 9: DATA & STORAGE (VAULT)
PostgreSQL | Redis | Qdrant | Neo4j | Meilisearch | Stash | Tdarr
164TB array (87% full). Backups: PG daily, Neo4j/Qdrant weekly, Stash daily.
Intelligence stack (planned): Inoreader, Readwise, Snipd, n8n, Miniflux

## LAYER 10: PHYSICAL INFRASTRUCTURE
4 nodes, 7 GPUs, 527GB RAM (305GB idle), 21.9TB NVMe (18.7TB idle)
5GbE all nodes. UPS connected (NUT monitoring needs USB cable).
Upgrades: FOUNDRY Channel H 32GB DDR4 ($50-80)

## SUBSCRIPTIONS ($543.91/mo)
KEEP: Claude Max $200, ChatGPT Pro $200, Gemini $20, Perplexity $20, Mistral $0
EVALUATE: Copilot Pro+ $32.50, Z.ai GLM $30, Kimi $19
CUT: Qwen Code $10 (local replaces)
AUTO-CANCEL: Venice $12.42 (July 2026)
FUTURE: Account B $200 (when rate limits hit)

## REJECTED (14 items with evidence)
llama-swap | claude -p monitoring | vmtouch | ImageReward | PickScore
LAION Aesthetic | Split subagent routing | LangGraph Platform cron
EAGLE-3 | Devstral 2 123B | SGLang | Complexity router | Per-token APIs

## EXECUTION ORDER

### Phase 0: Fix Broken (2 hours)
1. Auto_gen LLM endpoint
2. Langfuse API keys
3. Agent Qdrant URL
4. rsync WORKSHOP models to local NVMe
5. LiteLLM config fixes (coding/vision/timeout/retries/fallbacks)
6. Encrypt credentials
7. MCP Tool Search auto:5 -> true
8. coding-agent timeout 600->1800
9. Add swap-space to coder and node2

### Phase 1: Optimize & Configure (days)
10. Enable vision on coordinator
11. Update Aider config
12. Increase coordinator swap 16->32
13. Mount FOUNDRY nvme1n1
14. Bash health script + systemd timer
15. Rewrite MEMORY.md
16. Install Roo Code with 9-mode config
17. Enable Agent Teams
18. Activate claude-squad
19. Install Compound Engineering + Deep Trilogy
20. Update delegate skill with routing matrix
21. Update CLAUDE.md with tools + locked decisions

### Phase 2: Agent Reliability (days)
22. APScheduler in agent server
23. Prometheus Alertmanager webhook
24. Tool safety tiers
25. PostgresSaver for agent state
26. Target >80% success rate
27. Seed trust system

### Phase 3: Content Pipeline (weeks)
28. Deploy Aesthetic Predictor V2.5
29. Performer data merge
30. Rate 1000 images for custom MLP
31. Fix auto_gen gateway venv
32. Deploy JOSIEFIED-Qwen3-8B

### Phase 4: New Capabilities (weeks)
33. LTX 2.3 video gen
34. Dia 1.6B TTS
35. Deploy Qwen3.5-4B intent classifier
36. Deploy Qwen3-Embedding-8B upgrade
37. Build 5 undeployed agents
38. Install remaining tools

### Phase 5: Evaluate (ongoing)
39-47. Subscriptions, Devstral Small 2, ik_llama.cpp 397B, FOUNDRY DDR4, Coolify, Intelligence stack, Account B, P2 models
