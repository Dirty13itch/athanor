# Athanor Full-Stack COO Architecture Plan

## Executive Summary (COO Perspective)

This plan consolidates findings from 60+ research documents, 28 research/audit agents, live SSH audits of all 4 nodes (FOUNDRY, WORKSHOP, DEV, VAULT), the complete LiteLLM config, all container inventories, actual RAM/NVMe/GPU utilization numbers, the subscription/API key inventory, and the Claude Code configuration on DEV. Every assertion is backed by verified data — no assumptions remain.

**The cluster is running but has critical issues:**
- **LiteLLM 24-minute worst-case failover** (num_retries × timeout × chain_length)
- **LangGraph agents: 16% success rate** across 120 tasks (52% failed, 32% cancelled)
- **305GB system RAM idle** (75% unused), **18.7TB NVMe unused** (92% free)
- **WORKSHOP loading models over NFS** (26s) despite having empty Gen5 NVMe drives (1.9s)
- **Vision endpoint broken** — but Qwen3.5-27B IS a VLM (just needs `--language-model-only` removed)
- **GPU orchestrator already exists** on FOUNDRY:9200 but sleep/wake is broken
- **Qdrant URL wrong** in agent config — points to old FOUNDRY instance, not VAULT
- 6 LiteLLM aliases point to same backend, `coding` route goes to wrong model
- MTP speculative decoding working well (78-100% acceptance rate)

**What we're doing (revised priority after full audit):**
1. **Fix broken things** (hours): Qdrant URL, LiteLLM failover latency, vision endpoint, NVMe model copy, security
2. **Fix agent reliability** (days): coding-agent timeout, task persistence, trust system activation — get from 16% to >80% success
3. **Add autonomous monitoring** (days): APScheduler in agent server, Prometheus webhooks, bash health scripts
4. **Optimize model routing** (days): stream_timeout, model_info, differentiated aliases, swap-space for coder/node2
5. **Deploy new capabilities** (weeks): Aesthetic Predictor, LTX 2.3 video, performer data consolidation
6. **Maximize subscription utilization** (ongoing): Use every sub to its resetting limits, API key verification

**What we're NOT doing:**
- llama-swap (wrong for vLLM Docker — 30-120s swaps)
- claude -p for autonomous monitoring ($400/mo, 23% success on multi-step)
- vmtouch/page cache (marginal 10-30s savings, not transformative)
- ImageReward/PickScore (explicitly penalize NSFW content)
- Split subagent routing (too buggy — hardcoded model IDs in built-in agents)
- SGLang migration (unnecessary complexity when vLLM works)
- LangGraph Platform cron (paid only — use APScheduler instead)

### Latest Developments (Web search March 18, 2026)
- **vLLM v0.17.2rc0** (Mar 17): Pipeline Parallelism +30.8% throughput, WebSocket Realtime API. We stay on v0.13.0 (working).
- **LiteLLM v1.82.4** (Mar 18, TODAY): gpt-5.4 support, Gemini 3.x, 116 new models. Consider update from v1.81.9.
- **Hindsight (vectorize-io)**: Trending agent memory system — retain/recall/reflect, +44.6pts on LongMemEval. MCP server. Could complement/replace 6-tier memory. **EVALUATE.**
- **Karpathy autoresearch**: 22.9K stars in 3 days. Auto AI research on single GPU.
- **Qwen3.5-9B confirmed**: Outperforms last-gen Qwen3-30B. Validates our deployment plan.
- **DEV NIC is 5GbE** (measured), not 10GbE as user stated. Still adequate but not 10GbE.
- **VAULT has 5 NVMe** (not 3 as MEMORY.md says): 4× Samsung 990 EVO Plus 1TB + 1× P310 1TB

**Locked Architectural Decisions (non-negotiable):**
1. Claude Code is primary interactive tool
2. LiteLLM is single routing layer for all local model access
3. Subscription CLIs before BYOK tools (Claude > Gemini > Codex > Kimi > Qwen > local)
4. Coolify on DEV for internal deploys (not yet installed)
5. Cloudflare Pages for production public frontends
6. FOUNDRY is production — never modify without explicit approval
7. Qwen3.5-27B-FP8 stays on coordinator TP=4 (validated by benchmarks)
8. LTX 2.3 is primary video gen
9. SDXL + CivitAI LoRAs for character art; FLUX.2 Dev for photorealism
10. No VS Code lock-in; core workflow is terminal-native
11. ALL EoBQ/NSFW traffic stays local — zero cloud APIs
12. Infrastructure Guardian agent must be sovereign/local-only (no cloud dependency)
13. No peer-to-peer agent communication (centralized orchestrator only)
14. No agent self-modification
15. All subscriptions are sunk cost — maximize utilization of resetting limits, never cut

**Decision authority:** This plan is the single source of truth. MEMORY.md has multiple inaccuracies discovered during the audit (vllm-coder model, GPU sharing, vision model status). MEMORY.md will be corrected after implementation, not before.

---

## Context

The Athanor cluster has extensive hardware (7 GPUs, 527GB RAM, 160 CPU cores, 23TB NVMe across 4 nodes) and software (9 LangGraph agents, LiteLLM, vLLM, ComfyUI, Claude Code with 54 MCP tools) but is significantly underutilized. Research across 60+ documents and 10 agents revealed:

- **llama-swap is wrong** for vLLM Docker (30-120s swaps from full container restart)
- **claude -p is unreliable** for autonomous multi-step tasks (23% success rate, $400+/mo)
- **EAGLE-3 is invalidated** by Qwen3.5 — native MTP replaces it
- **ImageReward explicitly penalizes NSFW** content — unsuitable for this pipeline
- **Standard vLLM Docker doesn't support Blackwell GPUs** — needs cu130-nightly
- **vLLM streaming tool calls with Qwen3.5 produce malformed JSON** (HIGH RISK)
- **364GB system RAM sits idle** across nodes
- **9 LangGraph agents do nothing autonomously** — only respond to manual requests
- **4 conflicting GPU layout proposals** exist across research documents
- **Subscription costs are $543/mo** — all sunk cost, maximize utilization of resetting limits
- **804 performers in Triage data** partially merged into performers.json
- **Plaintext credentials on desktop** (security risk)

The original KAIZEN vision (Jan 2026) planned 30 environments with GWT cognitive architecture, SGLang inference, and Talos Linux. The system has evolved to vLLM + Ubuntu + LangGraph. This plan bridges the gap between what was designed and what's deployed, incorporating all research findings.

**Intended outcome:** A demand-driven, self-monitoring AI cluster that maximizes hardware utilization, routes intelligently between local and cloud models, monitors its own health autonomously, and scores generated content fairly.

**CRITICAL REFRAMING (discovered iteration 38):** The "Athanor OS" — a 6-phase autonomous pipeline with governor, subscription tracking, GWT workspace, goal tracking, plan lifecycle, 14+ API endpoint groups — is ALREADY DEPLOYED on FOUNDRY:9000. BUILD-MANIFEST.md (March 16) shows it executing cross-project work autonomously. The agent server has `/v1/subscriptions/*`, `/v1/goals/*`, `/v1/workspace/*`, `/v1/plans/*` endpoints. This plan is about FIXING and IMPROVING what exists, not building from scratch. Key existing systems not previously documented:
- **Continue.dev** installed on DEV with LiteLLM routing (2 model profiles) — NOT in "evaluate" status
- **Speaches** provides BOTH STT (faster-whisper) AND TTS (Kokoro) — voice pipeline 2/4 done
- **Dashboard** is a full Next.js 16 PWA with 5 lens modes, 17+ pages, SSE real-time
- **Multi-CLI dispatch daemon** running as systemd on DEV
- **LoRA training pipeline** already built (Ansible + Docker + kohya sd-scripts)
- **Task dedup** in agent submission (hash-based)
- **Governor auto-executes** LOW_RISK_AGENTS without approval
- **ComfyUI + vLLM Vision share** WORKSHOP GPU 1 (can't run simultaneously)
- **Reference repos** at ~/repos/reference/ (hydra, kaizen, local-system, system-bible)
- **SERVICES.md** on DEV is the live service inventory (more detailed than this plan's service map)

---

## Verified Cluster State (SSH audited 2026-03-18)

### Complete Hardware Inventory (verified via SSH + PowerShell)

**FOUNDRY (.244) — Heavy Compute**
- CPU: AMD EPYC 7663 56-Core (112 threads, Zen 3, NO AVX-512)
- RAM: 219GB DDR4-3200 ECC (7/8 channels populated, Channel H empty — $50-80 for 32GB RDIMM → 256GB + full bandwidth)
- GPUs: 4× RTX 5070Ti 16GB + 1× RTX 4090 24GB = 88GB VRAM
- NVMe: 3.6TB Samsung 990 PRO (/mnt/local-fast, models), 3.6TB Crucial P3 Plus (OS), 932GB Crucial P310 (**UNMOUNTED** — waste)
- Network: 2× 10GbE (enp66s0f0 + enp66s0f1), both UP at 10000Mb/s
- Kernel: 6.17.0-14-generic, Docker 29.2.1

**WORKSHOP (.225) — Creative**
- CPU: AMD Threadripper 7960X 24-Core (48 threads, Zen 4)
- RAM: 125GB DDR5-5600
- GPUs: RTX 5090 32GB + RTX 5060Ti 16GB = 48GB VRAM
- NVMe: 3.6TB Crucial T700 Gen5 (OS), 932GB T700 Gen5 (/mnt/fast1, **EMPTY**), 932GB T700 Gen5 (/mnt/fast2, **EMPTY**)
- Network: 10GbE (eno1 at 10000Mb/s) + 2.5GbE (enp70s0) + WiFi
- Kernel: 6.17.0-14-generic, Docker 29.2.1

**DEV (.189) — Ops Center**
- CPU: AMD Ryzen 9 9900X 12-Core (24 threads, Zen 5)
- RAM: 60GB
- GPU: RTX 5060Ti 16GB
- NVMe: 932GB Crucial T700 Gen5 (OS /), 3.6TB Crucial P3 Plus (/data, **EMPTY**), 932GB Samsung 970 EVO Plus (/var/lib/docker)
- Network: **5GbE** (enp14s0, measured 5000Mb/s — NOT 10GbE) + WiFi
- Kernel: 6.17.0-14-generic, Docker 29.2.1

**VAULT (.203) — Storage**
- CPU: AMD Ryzen 9 9950X 16-Core (32 threads, Zen 5)
- RAM: 123GB
- GPUs: Intel ARC A380 (QSV transcode) + AMD Radeon iGPU
- NVMe: 4× Samsung 990 EVO Plus 1TB + 1× Crucial P310 1TB = **5 NVMe** (MEMORY.md says 3)
- HDDs: 2× WDC 22TB + 5× WDC 20TB + 1× Seagate 20TB + 2× WDC 18TB = **~200TB raw** (164TB usable array)
- Network: bond0 active-backup (eth0 10GbE primary + eth1 2.5GbE backup)
- Kernel: 6.12.54-Unraid

**DESK (.50) — Windows Workstation**
- CPU: Intel i7-13700K 16-Core (24 threads)
- RAM: 64GB DDR5-4800 (2× 32GB)
- GPU: RTX 3060 12GB + Intel UHD 770
- NVMe: 2TB Crucial P310 + 1TB Crucial T700 = 3TB
- Network: 1GbE (Ethernet 2) + 10GbE (vEthernet FSE HostVnic / Hyper-V)

**Cluster Totals:**
- CPUs: 120 cores / 240 threads
- RAM: 527GB (305GB idle)
- VRAM: 120.5GB GPU + 12GB DESK = 132.5GB
- NVMe: ~25TB (18.7TB idle)
- HDD: ~200TB raw (164TB usable, 22TB free)
- Network: All nodes 5-10GbE

### MEMORY.md Corrections Required

| Item | MEMORY.md Says | Actually Running |
|------|----------------|-----------------|
| FOUNDRY 4090 model | Qwen3-Coder-30B-A3B-AWQ | **Qwen3.5-35B-A3B-AWQ-4bit** (`qwen35-coder`) |
| WORKSHOP GPU sharing | GPU 0 shared between vLLM + ComfyUI | **NOT shared** — vLLM on GPU 0 (5090), ComfyUI on GPU 1 (5060Ti) |
| WORKSHOP GPU 1 | idle | ComfyUI (but only 416MB VRAM used) |
| Vision model | Qwen3-VL-8B-FP8 on WORKSHOP:8010 | **EXITED** — container exists but crashed ~39hrs ago (likely OOM on 5060Ti 16GB). Port 8010 not responding. |
| FOUNDRY containers | vllm-coordinator, vllm-coder, athanor-agents | Also: **Crucible** (API+Ollama+ChromaDB+SearXNG), **GPU orchestrator**, wyoming-whisper, speaches, qdrant, alloy |
| WORKSHOP containers | vllm-node2, comfyui | Also: **athanor-dashboard**, **ws-pty-bridge**, **athanor-eoq**, **athanor-ulrich-energy**, open-webui |
| DESK GPU | Not documented | **RTX 3060 12GB** + Intel UHD 770 |
| DESK full specs | Not documented | **i7-13700K 16C/24T, 64GB DDR5-4800, RTX 3060 12GB, 2TB P310 + 1TB T700 NVMe, 10GbE (vEthernet/Hyper-V)** |

### Verified GPU Map

| Node | GPU | Model | Container | VRAM Used | Port | Health |
|------|-----|-------|-----------|-----------|------|--------|
| FOUNDRY | 0,1,3,4 (4×5070Ti TP=4) | Qwen3.5-27B-FP8 | vllm-coordinator | 96% (62.5/65.2GB) | :8000 | 200 OK |
| FOUNDRY | 2 (RTX 4090) | Qwen3.5-35B-A3B-AWQ-4bit | vllm-coder | 94% (23.0/24.6GB) | :8006 | 200 OK |
| WORKSHOP | 0 (RTX 5090) | Qwen3.5-35B-A3B-AWQ-4bit | vllm-node2 | 98% (32.1/32.6GB) | :8000 | 200 OK |
| WORKSHOP | 1 (RTX 5060Ti) | ComfyUI (minimal) | comfyui | 3% (0.4/16.3GB) | :8188 | - |
| DEV | 0 (RTX 5060Ti) | Embed 0.6B + Rerank 0.6B | vllm-embedding + vllm-reranker | 29% (4.8/16.3GB) | :8001,:8003 | OK |

### Verified LiteLLM Config (VAULT:4000)

**Critical bugs in current config:**
1. **24-minute worst-case failover**: `num_retries: 2` × `timeout: 120` × 4 chain models = 1440s
2. **No stream_timeout**: Can't fail-fast on cold/crashed local endpoints
3. **No model_info**: `supports_function_calling` silently returns false for all local models (#23054)
4. **Vision route broken**: `vision` → WORKSHOP:8010 but no container exists
5. **6 aliases to same endpoint**: utility/fast/creative/worker/uncensored/grader all → WORKSHOP:8000
6. **`coding` routes to coordinator (27B)**, not the dedicated coder (35B on 4090)

### Verified Services on DEV
- 4 Local-System services (gateway:8700, mind:8710, memory:8720, perception:8730)
- athanor-heartbeat daemon
- Gitea Actions Runner
- vllm-embedding:8001 + vllm-reranker:8003 (NVIDIA NGC image, NOT custom athanor/vllm)

### Additional Discovered Services (not in MEMORY.md)
| Service | Node | Port | Status | Purpose |
|---------|------|------|--------|---------|
| speaches (Kokoro-82M TTS) | FOUNDRY | :8200 | ✅ UP | OpenAI-compatible TTS, 54 voices, CUDA |
| wyoming-whisper | FOUNDRY | :10300 | ✅ UP | STT for Home Assistant (Wyoming protocol) |
| Grafana Alloy | FOUNDRY+WORKSHOP | :12345 | ✅ UP | OpenTelemetry collector (metrics/logs → Prometheus/Loki) |
| n8n | VAULT | :5678 | ✅ UP | Workflow automation (intelligence curation triggers) |
| Gitea | VAULT | :3033 (web), :2222 (SSH) | ✅ UP | Self-hosted Git server |
| Open WebUI | WORKSHOP | :3000 | ✅ UP | Web chat UI → FOUNDRY:8000 (Qwen3.5-27B-FP8). LAN-accessible browser chat with local model. Good for phone/tablet access. |
| athanor-dashboard | WORKSHOP | :3001 | ✅ UP | Athanor web dashboard |
| athanor-eoq | WORKSHOP | :3002 | ✅ UP | Empire of Broken Queens app |
| athanor-ulrich-energy | WORKSHOP | :3003 | ✅ UP | Ulrich Energy HERS app |
| athanor-ws-pty-bridge | WORKSHOP | :3100 | ✅ UP | WebSocket terminal bridge |

### VAULT Container Count: 47
Key services: LiteLLM, Langfuse (full stack), n8n, Stash, Home Assistant, Plex, *arr stack, Grafana, Prometheus, Loki, Alloy, Neo4j, Qdrant, PostgreSQL, Redis, Meilisearch, Gitea, ntfy, Tdarr (server+node), cAdvisor, multiple web apps

---

## Phase 0: Critical Blockers

These must be fixed before any other work. They are either security risks or blocking issues.

### 0.1 Security Audit (Multiple Issues)

**0.1a Plaintext Credentials on Desktop**
**File:** `C:\Users\Shaun\Desktop\research\Triage\Usenet _ Provider & Indexer Login Information (1).xlsx`
**Problem:** Contains plaintext usernames, passwords, API keys, and server addresses for 12 Usenet providers, 17 indexers, and 11 private trackers.
**Action:** Move to VAULT secrets management or at minimum encrypt with 7-Zip AES-256. Delete the plaintext copy from desktop.

**0.1b Docker Socket Proxy Exposed on LAN**
FOUNDRY exposes Docker API at `192.168.1.244:2375` via `docker-socket-proxy` container. This gives unauthenticated Docker control to anyone on the LAN.
**Risk:** Medium (LAN-only, no internet exposure). But if any device on the network is compromised, full Docker control is available.
**Action:** Restrict to localhost or specific IPs via firewall rules. Or remove if not needed (what consumes this?).

**0.1c API Keys Exposed in This Session**
Mistral, Zhipu (Z.ai), HuggingFace API keys were visible in XLSX read output.
**Action:** Rotate these 3 keys immediately.

**0.1d Old Qdrant Instance Still Running**
FOUNDRY:6333 — old Qdrant instance still running and still receiving agent traffic (agents point here instead of VAULT:6333).
**Action:** After fixing agent Qdrant URL (0.3f), verify FOUNDRY Qdrant is no longer receiving requests, then stop it.

**0.1e Crucible Containers Unnecessary**
4 Crucible containers running with 5% success rate: API, Ollama (empty), ChromaDB (empty), SearXNG.
**Action:** Stop all 4 after evaluating deprecation decision. Frees ports 8001, 8080, 8742, 11434 on FOUNDRY.

### 0.2 Blackwell CUDA Compatibility — ALREADY SOLVED ✅
Custom `athanor/vllm:qwen35` image has CUDA 12.8 with sm_120 support. Verified via SSH: `torch.cuda.get_arch_list()` includes sm_120. No action needed.

### 0.2b GPU Orchestrator Fix (DISCOVERED — already deployed on FOUNDRY:9200)
**Finding:** `athanor-gpu-orchestrator` is a live FastAPI service managing 4 GPU zones with 10 API endpoints (health, status, TTL, sleep/wake, Prometheus metrics). It was NOT documented in MEMORY.md.
**Problem:** Sleep/wake is broken because vLLM returns 404 on `/sleep` and `/is_sleeping` endpoints. All zones show idle for 48+ hours because TTL-based sleep can't execute.
**Fixes needed:**
1. Update coder zone to track vllm-coder on FOUNDRY:8006 (currently `vllm: null`)
2. Fix or remove sleep/wake integration (vLLM Sleep Mode REST API is broken on V1 engine)
3. Update vision zone to either deploy Qwen3-VL-8B or mark as intentionally offline
4. Consider: replace sleep/wake with docker stop/start for the worker zone (WORKSHOP 5090 time-sharing with ComfyUI)
**Port:** FOUNDRY:9200
**Prometheus metrics:** Already exposed at `/metrics`

### 0.3 Fix MCP Tool Search Mode
**Current state:** DEV has `ENABLE_TOOL_SEARCH=auto:5` in project settings. Research found `auto:N` modes are BUGGY (issues #19422, #19890 — measures 0 chars at decision time, fails to trigger).
**Fix:** Change from `auto:5` to `true` (always-on, no threshold — more reliable).
**DESK:** Verify same setting exists in DESK project settings.
**MCP server gap:** Only 2 servers in `.mcp.json` (docker + athanor-agents). But AGENTS.md on DEV specifies 8 always-on + 7 disabled. The missing 6 always-on servers (redis, qdrant, smart-reader, sequential-thinking, neo4j, postgres) need to be added to `.mcp.json`. The 7 disabled servers (grafana, langfuse, miniflux, n8n, gitea, context7, github) should be added with `"disabled": true` for on-demand activation via `/mcp`.
**Also:** Remove orphaned MCP permissions for non-existent `ls-*` servers from project settings.
**Also add:** `serverInstructions` to MCP server configs for better tool discovery.

### 0.3b Fix Broken Vision Endpoint (DISCOVERED — Qwen3.5-27B IS ALREADY A VLM)
**Finding:** All Qwen3.5 models are natively multimodal VLMs. The FOUNDRY coordinator (Qwen3.5-27B-FP8) is deployed with `--language-model-only` which explicitly disables the vision encoder.
**Fix (Option B — recommended, zero additional GPU):**
1. Remove `--language-model-only` from vllm-coordinator startup command
2. Add: `--limit-mm-per-prompt video=0 --limit-mm-per-prompt image=2`
3. Update LiteLLM `vision` route: point at FOUNDRY:8000 instead of broken WORKSHOP:8010
4. Update GPU orchestrator vision zone to reference FOUNDRY coordinator
**Trade-off:** Vision encoder consumes some VRAM currently used for KV cache, reducing text concurrency slightly. But 27B vision is better than deploying a separate 8B model.
**Alternative (Option A):** Deploy Qwen3-VL-8B-FP8 (~18-20GB with images) on FOUNDRY 4090 by displacing vllm-coder. Not recommended — loses the dedicated coding endpoint.

### 0.3c NVMe Quick Win: Copy WORKSHOP Models to Local Storage
**Finding:** WORKSHOP loads models over NFS from VAULT at 873 MB/s (10GbE saturated). Meanwhile, TWO Crucial T700 Gen5 NVMe drives sit EMPTY on WORKSHOP (`/mnt/fast1`, `/mnt/fast2`, 870GB each, 12.4 GB/s).
**Impact:** Model load time 26s (NFS) → 1.9s (local Gen5). 14x improvement. Also eliminates VAULT dependency for inference.
**Fix:**
```bash
ssh workshop "rsync -av /mnt/vault/models/Qwen3.5-35B-A3B-AWQ-4bit/ /mnt/fast1/models/Qwen3.5-35B-A3B-AWQ-4bit/"
# Update vllm-node2 docker mount: -v /mnt/fast1/models:/models
```
**Also:** Mount FOUNDRY's unmounted 1TB P310 (`/dev/nvme1n1p1`, Gen4, btrfs formatted, unused) as `/mnt/fast-cache`.
**Also:** DEV has 3.4TB empty at `/data` (Crucial P3 Plus 4TB) — available for embedding cache or training data.
**Cluster NVMe utilization:** 8% → should target ~30% after model pre-positioning.

### 0.3d Fix Qdrant + Neo4j Backups (FAILING since March 14)
**Finding:** Prometheus alerts firing: Qdrant backup 4+ days old, Neo4j backup 4+ days old. PostgreSQL backups are fine (daily, latest March 18). The specific service backup scripts (`/opt/athanor/scripts/backup-qdrant.sh` and `backup-neo4j.sh`) have been failing since March 14. Appdata-level backups in `/mnt/appdatacache/backups/` ARE running (separate system).
**Action:** SSH to VAULT, check backup script logs, fix the scripts. Likely cause: Qdrant API change, Neo4j connection issue, or VAULT service disruption around March 14 (same date Langfuse broke).

### 0.3e Fix Langfuse Tracing (BROKEN since March 14)
**Finding:** Langfuse v3.155.1 on VAULT:3030 captured 139,084 traces (March 11-14), then stopped. LiteLLM's Langfuse env vars are empty strings.
**Fix:**
```bash
# Add to LiteLLM container env:
LANGFUSE_PUBLIC_KEY=pk-lf-athanor
LANGFUSE_SECRET_KEY=sk-lf-athanor
# LANGFUSE_HOST=http://192.168.1.203:3030 (already correct)
```
**Impact:** Restores full LLM observability — every inference request logged with input/output, model, latency, routing info. The existing 139K traces contain routing optimization data.

**Langfuse Trace Analysis Plan (139K traces from March 11-14):**
Once keys are restored, analyze the existing data to optimize routing:
1. **Latency distribution per model** — which local models are fastest? Any outliers?
2. **Error rate per endpoint** — which vLLM instances fail most?
3. **Token usage per model** — which models consume most tokens per request?
4. **Routing pattern analysis** — which fallback chains trigger most? Are cloud fallbacks happening unnecessarily?
5. **Time-of-day patterns** — when is the cluster busiest? When are GPUs idle?
6. **Quality signals** — do certain models produce longer/shorter responses for same prompts? (proxy for quality)
7. **Export dashboard:** Create a Grafana dashboard pulling from Langfuse API for real-time routing visibility
**Root cause:** Container restart/recreate lost the env vars. Add to compose template to persist.

### 0.3e Fix Auto_Gen Pipeline (BROKEN 11 DAYS — zero output since March 7)
**Finding:** Every generation since March 7 fails with `All connection attempts failed` to `FOUNDRY:8004`. No vLLM instance on port 8004. The endpoint referenced a removed model (`Huihui-Qwen3-8B-abliterated-v2`).
**Impact:** 11 days of zero image output. 113 empty drop folders accumulated. 127 scheduler runs all failing.
**Fix:**
```bash
# In .env: VLLM_CREATIVE_HOST=http://192.168.1.203:4000  (LiteLLM)
# In auto_gen.py line 49-52:
LLM_API_URL = "http://192.168.1.203:4000/v1"
LLM_MODEL = "creative"  # LiteLLM alias → WORKSHOP Qwen3.5-35B-A3B-AWQ
# Also set: LLM_API_KEY = "sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d"
```
**Also:** Clean up 113 empty drop folders. Rebuild gateway venv (Python binary marked "(deleted)").
**Pipeline stats (when working):** 84 images generated (March 6-7), 54 rated (81% rejection rate), 18 active subjects, 45 themes. FLUX.1 Dev FP8 + PuLID Flux on 5090.

**Full auto_gen restoration plan (beyond just fixing the endpoint):**
1. Fix LLM endpoint (immediate — point to LiteLLM creative alias)
2. Clean 113 empty drop folders: `find /mnt/vault/data/gen-output/ -maxdepth 1 -empty -type d -delete`
3. Rebuild gateway venv (Python binary deleted on disk from system upgrade)
4. Verify ComfyUI on WORKSHOP:8188 is healthy and FLUX models are loaded
5. Test one manual drop (create drop folder with reference.jpg, watch pipeline pick it up)
6. Verify feedback injection still works (logs should show "Injected feedback context")
7. Verify performer attribute injection (DB lookup for subject slug)
8. Enable FaceDetailer (currently disabled — install ultralytics in ComfyUI container)
9. Connect Aesthetic Predictor V2.5 (when deployed) for automatic quality scoring
10. Set scoring threshold: <5.5 → regenerate, >6.5 → flag as quality
11. Monitor first 24 hours of restored pipeline, check rejection rate vs baseline 81%

### 0.3f Fix Agent Qdrant URL
**Finding:** `ATHANOR_QDRANT_URL` in athanor-agents container points to `http://192.168.1.244:6333` (FOUNDRY, old instance). Should be `http://192.168.1.203:6333` (VAULT). MEMORY.md claims this was fixed — it was NOT.
**Fix:** Update env var in athanor-agents container and restart.

### 0.4 LiteLLM Local Model Bug Workaround
**Problem:** LiteLLM issue #23054 — local models with arbitrary names (like `qwen3.5-27b`) silently break function calling detection, provider routing, and error classification. `supports_function_calling()` returns false, non-standard errors get misclassified as `ContentPolicyViolationError` with 60s cooldown.
**Action:** Add explicit `model_info` blocks in LiteLLM config for every local model:
```yaml
model_info:
  supports_function_calling: true
  supports_vision: false  # or true for VL models
  input_cost_per_token: 0
  output_cost_per_token: 0
  max_tokens: 32768
  max_input_tokens: 131072
```

---

## Phase 1: GPU Layout & Model Serving

The single most impactful change. Resolves 4 conflicting proposals with evidence-based decisions.

### 1.1 GPU Layout Decision

**Research found 4 proposals.** Recommended layout (synthesis of all findings):

| GPU | Model | Quant | Role | Rationale |
|-----|-------|-------|------|-----------|
| FOUNDRY 4×5070Ti (64GB, TP=4) | Qwen3.5-27B-FP8 **(KEEP CURRENT)** | FP8 (~27GB) | Primary general/reasoning | 72.4% SWE-bench (matches GPT-5 mini). All 27B params active = higher quality reasoning than 35B-A3B (only 3B active). MTP speculative decode working (78-100% acceptance). Already deployed and working — no change needed. |
| FOUNDRY RTX 4090 (24GB) | Qwen3.5-9B | BF16 (~20GB) | Fast draft/review/code assist | Dense model, no MoE overhead. Standard vLLM image works (Ada GPU). |
| WORKSHOP RTX 5090 (32GB) | **Creative Primary**: ComfyUI (FLUX/PuLID image gen) + LTX 2.3 (video gen) | NVFP4/GGUF | Image gen + video gen + uncensored creative | This is the creative GPU. NOT a 3rd copy of the same LLM. LLM overflow goes to cloud subs (sunk cost). |
| WORKSHOP RTX 5060Ti (16GB) | Aesthetic Predictor V2.5 (~2.5GB) + Custom MLP (~0.1GB) + JOSIEFIED-Qwen3-8B (~9GB) | FP16/BF16 | Quality scoring + uncensored creative | Fits comfortably in 16GB. |
| DEV RTX 5060Ti (16GB) | Qwen3-Embedding-0.6B + Reranker-0.6B (~3GB) + Qwen3.5-9B (~10GB) | BF16/FP8 | Embed/rerank + fast local inference | 13GB available for the 9B model. |

**Why keep Qwen3.5-27B-FP8 on TP=4 (not switch to 35B-A3B)?**
- 27B dense activates ALL 27B params per token = higher quality reasoning (72.4% SWE-bench)
- 35B-A3B only activates 3B params = 3-5x faster but lower quality on complex tasks
- 27B is better for the coordinator role (reasoning, architecture, planning)
- 35B-A3B is already on the 4090 as coder (fast iteration where speed > quality)
- Current deployment works with MTP at 78-100% acceptance — don't fix what works
- Research confirms: "Pick 27B if you value functional completeness on interactive tasks"

**WORKSHOP 5090 — Dedicated Creative GPU (NOT another LLM):**
- Currently running vllm-node2 (Qwen3.5-35B-A3B) using 98% VRAM — this is a 3rd copy of essentially the same model already on FOUNDRY. Wasteful.
- **Change:** Remove vllm-node2. Dedicate 5090 to creative workloads:
  - ComfyUI with FLUX.1 Dev FP8 + PuLID Flux for image gen (~12-15GB)
  - LTX 2.3 NVFP4 for video gen (~31GB — needs full GPU, loads on-demand)
  - Uncensored image/video generation is the PRIMARY use case for this GPU
- LLM inference overflow goes to cloud subscriptions (sunk cost, limits reset)
- ComfyUI lives here permanently. LTX 2.3 loads when video gen is triggered, ComfyUI unloads models first.

**Why TP=4 on FOUNDRY is NOT wasteful:**
- Qwen3.5-27B-FP8 is ~27GB. Across 4 GPUs = ~6.75GB/shard, leaving ~9GB/GPU = **36GB total KV cache**
- This supports the 131K context window at reasonable concurrency
- At TP=2 (2 GPUs), each shard = ~13.5GB, leaving only ~2.5GB/GPU = 5GB KV cache — too little for 131K context
- TP=4 is the right call for this model + context length combination
- The remaining GPU (4090) runs the dedicated coder model — properly utilized

### 1.2 vLLM Upgrade Path

**Current:** v0.13.0+faa43dbf (NVIDIA 26.01 build) with custom `athanor/vllm:qwen35` image — NOT v0.16.1 as MEMORY.md claims
**Decision: STAY on v0.13.0.** It works. MTP active (78-100% acceptance). Blackwell supported. Tool calling works with qwen3_xml parser.
**Future target:** vLLM v0.18+ when Qwen3.5 streaming tool call bugs are fixed (issue #35266)

**Migration steps:**
1. Pull `vllm/vllm-openai:cu130-nightly` (Blackwell support)
2. Test on FOUNDRY with Qwen3.5-35B-A3B-GPTQ-Int4:
   ```bash
   vllm serve Qwen/Qwen3.5-35B-A3B-Instruct-GPTQ-Int4 \
     --tensor-parallel-size 4 \
     --quantization moe_wna16 \
     --enable-auto-tool-choice \
     --tool-call-parser qwen3_coder \
     --reasoning-parser qwen3 \
     --language-model-only \
     --speculative-config '{"method":"qwen3_next_mtp","num_speculative_tokens":2}' \
     --performance-mode balanced
   ```
3. Test on 4090 with standard image (Ada GPU, no Blackwell issue):
   ```bash
   vllm serve Qwen/Qwen3.5-9B-Instruct \
     --enable-auto-tool-choice \
     --tool-call-parser qwen3_coder
   ```

**HIGH RISK mitigations:**
- `qwen3_coder` streaming tool calls produce malformed JSON (issue #35266): Test thoroughly before production. Watch for PR #35347 (`qwen35_coder` parser).
- `qwen3_coder` uses `eval()` on untrusted input (GHSA-79j6-g2m3-jgfw): Don't expose vLLM endpoints to untrusted users. Acceptable for internal cluster.
- MTP and prefix caching are mutually exclusive: At low concurrency use MTP (1.3-1.8x speedup). At high concurrency disable MTP and enable prefix caching.

### 1.3 LiteLLM Routing Reconfiguration

**Current:** v1.81.9 on VAULT:4000 with 33 model aliases
**Goal:** Local-first with cloud fallback via stream_timeout

**Key config changes:**
```yaml
model_list:
  # LOCAL MODELS (order: 1 = try first)
  - model_name: general
    litellm_params:
      model: hosted_vllm/qwen3.5-35b-a3b
      api_base: http://192.168.1.244:8000
      api_key: none
      order: 1
      stream_timeout: 10  # fail fast if no first token in 10s
      timeout: 300
    model_info:
      supports_function_calling: true
      input_cost_per_token: 0
      output_cost_per_token: 0

  - model_name: fast
    litellm_params:
      model: hosted_vllm/qwen3.5-9b
      api_base: http://192.168.1.244:8006  # 4090
      api_key: none
      order: 1
      stream_timeout: 5
    model_info:
      supports_function_calling: true
      input_cost_per_token: 0
      output_cost_per_token: 0

  - model_name: coder
    litellm_params:
      model: hosted_vllm/qwen3.5-35b-a3b
      api_base: http://192.168.1.244:8000
      api_key: none
      order: 1
      stream_timeout: 10
    model_info:
      supports_function_calling: true
      input_cost_per_token: 0
      output_cost_per_token: 0

  # CLOUD FALLBACKS (order: 2 = try after local fails)
  - model_name: general
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20250514
      order: 2

  - model_name: coder
    litellm_params:
      model: codestral/codestral-latest
      api_base: https://codestral.mistral.ai/v1
      order: 2

  - model_name: reasoning
    litellm_params:
      model: openai/o3-pro
      order: 2

  # DIRECT CLOUD (no local equivalent)
  - model_name: opus
    litellm_params:
      model: anthropic/claude-opus-4-6-20250415

  - model_name: sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20250514

  - model_name: creative
    litellm_params:
      model: hosted_vllm/qwen3.5-27b-fp8  # Route to FOUNDRY coordinator (5090 is now creative GPU, no vLLM)
      api_base: http://192.168.1.244:8000
      api_key: none
      order: 1
      stream_timeout: 10

litellm_settings:
  drop_params: true
  modify_params: true
  fallbacks:
    - {"general": ["sonnet"]}
    - {"coder": ["codestral", "sonnet"]}
    - {"fast": ["sonnet"]}
    - {"creative": ["sonnet"]}
  callbacks: ["prometheus"]

router_settings:
  routing_strategy: simple-shuffle
  enable_pre_call_checks: true
  num_retries: 0  # don't retry local — fall through immediately
```

**Key design decisions (verified via deep research):**
- `stream_timeout` per-model in `litellm_params`: Measures time-to-first-chunk. If local model is cold/crashed, fails in 10-15s instead of the current 24-MINUTE worst case.
- **Current config worst case: `(num_retries+1) × timeout × chain_length` = `(2+1) × 120 × 4` = 1440s = 24 MINUTES.** This is the #1 fix.
- `num_retries: 0` per-model for local endpoints (PR #18975 confirmed per-model works). Don't retry dead local — fall through immediately.
- `model_info` is SIBLING to `litellm_params` (NOT nested inside). Setting `supports_function_calling: true` here fixes #23054 detection (confirmed PR #11381).
- `order: 1` (local) vs `order: 2` (cloud): LiteLLM tries lower order first.
- `drop_params: true`: Required for Claude Code → LiteLLM → vLLM chain (fixes issue #22963).
- `background_health_checks: true` with `health_check_interval: 300` is SAFE on v1.81.9 (CPU hang fix shipped earlier).
- `pre_call_checks` only checks context window metadata — does NOT probe health endpoints. Still useful for preventing oversized requests.
- Removed `DISABLE_PROMPT_CACHING` and `DISABLE_INTERLEAVED_THINKING` — NOT real LiteLLM env vars.

### 1.4 Claude Code → Local Model Routing (VERIFIED — FRAGILE)

**The haiku alias trick has significant bugs:**
- Built-in subagents (Explore) hardcode `claude-haiku-4-5-20251001` and bypass alias resolution (issue #19578)
- Short names (`haiku`) sometimes sent raw to API without resolution (issue #17562, closed NOT_PLANNED)
- `CLAUDE_CODE_SUBAGENT_MODEL` does NOT override built-in agent model selection (issue #25546)
- Nobody has successfully done "Opus main + local Qwen subagents" in production

**What DOES work (verified by real users):**
1. **Separate sessions for bulk work** — run `claude` with `ANTHROPIC_BASE_URL` pointed at LiteLLM, which routes to local vLLM. Use for implementation/bulk coding. Keep normal Opus sessions for complex architecture.
2. **Wildcard model matching in LiteLLM** — catches inconsistent model name resolution:
   ```yaml
   - model_name: "claude-*"
     litellm_params:
       model: hosted_vllm/qwen3.5-35b
       api_base: http://192.168.1.244:8000/v1
       drop_params: true
   ```
3. **vLLM native Anthropic Messages API** (PR #22627, merged Oct 2025) — skip LiteLLM entirely:
   ```bash
   ANTHROPIC_BASE_URL=http://192.168.1.244:8006 claude
   ```
   Cannot serve both OpenAI and Anthropic endpoints on same vLLM process.

**Real-world performance** (local Qwen3.5-35B-A3B via LiteLLM, based on community reports of similar MoE models): 60-100+ tok/s (MoE 3B active), tool calling works with qwen3_xml parser. Good for implementation, not for complex architecture.

**Recommended approach:** Don't split main/subagent routing (too buggy). Instead:
- Primary session: Claude Code with Opus 4.6 (complex work, design, architecture)
- Bulk session: Claude Code pointed at LiteLLM → local Qwen3.5 (boilerplate, tests, docs)
- Aider: Architect=Sonnet, Editor=local Qwen3.5 (git-first coding via LiteLLM)
- Roo Code: 9-mode routing already configured with local models

---

## Phase 2: Agent Autonomy & Monitoring

### 2.0 Fix Existing Agent Issues (DISCOVERED — 16% success rate)

**Finding:** Live audit of athanor-agents on FOUNDRY:9000 shows 120 historical tasks with only 16% success rate (19 completed, 62 failed, 39 cancelled). All 9 agents ARE scheduled and active (not 5 as MEMORY.md claims), with 77 tools (not 72).

**Immediate fixes:**
1. **Fix Qdrant URL** — env `ATHANOR_QDRANT_URL` points to `http://192.168.1.244:6333` (FOUNDRY, old instance), should be `http://192.168.1.203:6333` (VAULT). MEMORY.md claims this was fixed — it was NOT.
2. **Increase coding-agent timeout** — currently 600s, most failures are timeouts on complex coding tasks. Increase to 1800s.
3. **Reduce cancelled tasks** — 32% of tasks cancelled by server restarts. Implement graceful shutdown with task persistence.
4. **Activate trust system** — all agents at grade C (0.55 baseline), only 1 feedback entry. System is effectively unused.
5. **creative-agent is working well** — generating EoBQ game assets successfully. Model for other agents.

### 2.1 Extend LangGraph Agents for Autonomous Monitoring

**Current state:** 9 agents on FOUNDRY:9000, 77 tools, all scheduled but 52% failure rate.
**Target:** Fix reliability first, then add autonomous monitoring capabilities.

**New agent: Infrastructure Guardian (Tier 3)**
- Model: Qwen3.5-9B on FOUNDRY 4090 (local, free, always-on)
- Tools: Prometheus query, Docker inspect, SSH exec, ntfy push, systemd status
- Schedule: Every 5 minutes via LangGraph cron trigger
- Checks: GPU utilization, container health, disk usage, service status, memory pressure
- Alerting: ntfy push to `athanor` topic on VAULT:8880 for any degradation
- Guardrails: Read-only. Can restart containers but NOT delete data or modify configs.

**Implementation pattern (verified — LangGraph Platform cron is PAID ONLY, use APScheduler):**
```python
# In the existing athanor-agents FastAPI server on FOUNDRY:9000
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgres://user:pass@192.168.1.203:5432/agents"
checkpointer = PostgresSaver.from_conn_string(DB_URI)

scheduler = AsyncIOScheduler()

async def run_health_agent():
    result = await health_graph.ainvoke(
        {"messages": [{"role": "user", "content": "Run cluster health check"}]},
        config={"configurable": {"thread_id": "health-monitor"}}  # Same ID = stateful
    )
    if result.get("alerts"):
        await send_ntfy(result["alerts"])

scheduler.add_job(run_health_agent, CronTrigger(minute="*/5"))  # Every 5 min
scheduler.start()
```

**Event-driven triggers (Prometheus Alertmanager webhooks):**
```python
@app.post("/webhook/alertmanager")
async def handle_alert(request: Request):
    payload = await request.json()
    for alert in payload.get("alerts", []):
        if alert["status"] == "firing":
            agent_name = map_alert_to_agent(alert["labels"])
            await invoke_agent(agent_name, {"alert": alert})
```

**Tool safety tiers:**
- READ_ONLY (auto-execute): docker ps, nvidia-smi, prometheus query, df
- WRITE_SAFE (auto-execute + log): restart container, scale replicas
- DESTRUCTIVE (interrupt for approval): docker rm, volume delete, config modify

**Why not claude -p?**
- 23% success rate on multi-step tasks (Stanford HAI)
- $400+/mo at 5-min intervals
- LangGraph agents on local Qwen3.5-9B cost $0
- LangGraph has state persistence, conditional routing, tool-specific error handling

### 2.2 Health Check Scripts (Free Baseline)

**For immediate alerting (before agent architecture is ready):**

Create `cluster-health.sh` on DEV:
```bash
#!/bin/bash
# Run via systemd timer every 5 minutes
ALERT_TOPIC="http://192.168.1.203:8880/athanor"

# Check each node
for node in foundry workshop vault dev; do
    if ! ssh -o ConnectTimeout=5 $node "echo ok" &>/dev/null; then
        curl -s -d "{\"title\":\"NODE DOWN\",\"message\":\"$node unreachable\"}" $ALERT_TOPIC
    fi
done

# Check GPU utilization on FOUNDRY
gpu_util=$(ssh foundry "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits" 2>/dev/null)
# Check Docker containers
down=$(ssh foundry "docker ps --filter 'status=exited' --format '{{.Names}}'" 2>/dev/null)
if [ -n "$down" ]; then
    curl -s -d "{\"title\":\"Container Down\",\"message\":\"$down\"}" $ALERT_TOPIC
fi

# Check disk
disk_pct=$(ssh vault "df /mnt/user | tail -1 | awk '{print \$5}' | tr -d '%'" 2>/dev/null)
if [ "$disk_pct" -gt 90 ]; then
    curl -s -d "{\"title\":\"DISK WARNING\",\"message\":\"VAULT array at ${disk_pct}%\"}" $ALERT_TOPIC
fi
```

Cost: $0. Runs forever. Reliable. Complements the LangGraph agent which does intelligent analysis.

### 2.3 Enriched Session Start — ✅ MOSTLY ALREADY DONE

**Discovery:** Session start hooks are MORE advanced than previously documented:

`session-start.sh` — shows branch, last commit, uncommitted changes count
`session-start-health.sh` — tries FOUNDRY:9000 briefing API first (Redis heartbeats, instant), falls back to parallel SSH checks. Already displays node health, models, alerts.
`/morning` command — comprehensive daily standup: briefing API, task review (last 10 + stats), Prometheus alerts, MEMORY.md context, compact summary table.
`/health` command — mid-session quick check: SSH ping, service health, GPU utilization.

**What's still missing (minor additions):**
- Active plan file name in session start output
- ntfy alerts from last hour (currently only Prometheus alerts)
- Langfuse token usage summary (once keys restored)
- Auto_gen pipeline status (last generation, queue depth)

### 2.4 Governor Architecture (Research-Proven Hybrid Two-Tier)

**Research across 3 deep agents (RouteLLM, Semantic Router, NadirClaw, Martian, Not Diamond, Unify, AutoGen, CrewAI, Magentic-One, Swarm, 7 framework comparison) conclusively shows:**

**Interactive mode (human present): Claude Code IS the governor.**
- It already makes routing decisions naturally through conversation
- Trying to replace it with a local router is a downgrade
- The routing cost is amortized into conversation latency
- Commercial routers (Martian, Not Diamond, Unify) are irrelevant — they optimize per-token cost, which flat-rate subscriptions eliminate

**Autonomous mode (human absent): Embedding classifier + LangGraph.**
Two-stage classification:
1. Regex/keyword rules: handles 40-60% of requests, <1ms
2. Semantic Router with existing Qwen3-Embedding-0.6B on DEV:8001: handles the rest, 10-25ms, 90-94% accuracy

**Why NOT a 4B LLM classifier?** Research proved embedding routing matches 4B accuracy at 5-10x less latency:
| Approach | Latency | Accuracy |
|----------|---------|----------|
| Regex/keyword | <1ms | 40-60% coverage |
| Semantic Router (embedding) | 10-25ms | 90-94% |
| Qwen 0.5B-1.5B LLM | 50-150ms | ~90% |
| Qwen 4B LLM | 150-300ms | ~92% |
| Cloud Opus | 800-3000ms | ~99% |

**Best real implementation: NadirClaw** — 10ms classification, 94% accuracy, MIT, OpenAI-compatible proxy, three-tier routing. Routes 60% to cheaper models with zero quality loss.

**Implementation:** Either NadirClaw (drop-in) or custom 50-line FastAPI with `semantic-router` library using existing Qwen3-Embedding-0.6B. Exposed as endpoint on DEV that LangGraph agents call for routing decisions.

**The delegate skill** in Claude Code gets the routing matrix for interactive decisions. Claude Code suggests the best tool, the human confirms or overrides.

**Multi-agent constraints (Google DeepMind, 180 configurations):**
- Cap at 4 agents per task (diminishing returns beyond)
- Centralized coordination +80.9% parallel, -39-70% sequential — don't multi-agent everything
- Independent agents amplify errors 17.2x — always have coordinator
- Plan-and-Execute outer loop beats ReAct for autonomous routing
- Full infra autonomy NOT safe yet — human-in-the-loop for destructive ops
- Trace every routing decision to Langfuse for feedback loop

**Frameworks evaluated and rejected:**
- AutoGen: maintenance mode, merged into Microsoft Agent Framework
- CrewAI: struggles with 7B local models, 56% token overhead
- Swarm/Agents SDK: educational only, replaced by OpenAI Agents SDK
- LangGraph: KEEP — right choice, production-stable, already running

**The Athanor v1 Starter Pack (from research docs):** Deferred. Contains good patterns (surfaces YAML, review gates, worktree isolation) but deploying a 4-service orchestrator while 17 things are broken is premature. Revisit after stabilization.

### 2.5 Autonomous Routing Classifier (Implementation)

**What:** A lightweight service on DEV that LangGraph agents call to classify tasks and pick the right model/tool.

**Option A: NadirClaw (drop-in)**
- 10ms classification, 94% accuracy, MIT licensed
- OpenAI-compatible proxy with three-tier routing
- Install: `pip install nadirclaw` or Docker
- Configure tiers: fast (Qwen3.5-9B), standard (Qwen3.5-27B coordinator), complex (Qwen3.5-35B coder)
- Sits between LangGraph agents and LiteLLM

**Option B: Custom 50-line FastAPI with Semantic Router (preferred — uses existing infra)**
```python
# classifier.py — runs on DEV, uses existing Qwen3-Embedding-0.6B on :8001
from semantic_router import Route, RouteLayer
from semantic_router.encoders import OpenAIEncoder  # compatible with any OpenAI-format API

encoder = OpenAIEncoder(
    name="qwen3-embedding",
    openai_base_url="http://192.168.1.189:8001/v1",
    openai_api_key="none"
)

# Define routes with example utterances
coding = Route(name="coding", utterances=[
    "refactor this function", "write unit tests", "fix this bug",
    "add error handling", "implement the API endpoint"
])
research = Route(name="research", utterances=[
    "what is the latest on", "find documentation for",
    "compare these approaches", "deep dive into"
])
creative = Route(name="creative", utterances=[
    "write a scene", "generate a prompt", "create dialogue",
    "describe this character"
])
infra = Route(name="infrastructure", utterances=[
    "check GPU status", "restart container", "disk usage",
    "is the service healthy", "deployment status"
])
simple = Route(name="simple", utterances=[
    "what time is it", "how do I", "explain this",
    "quick question about"
])

router = RouteLayer(encoder=encoder, routes=[coding, research, creative, infra, simple])

# FastAPI endpoint
from fastapi import FastAPI
app = FastAPI()

@app.post("/classify")
async def classify(request: dict):
    route = router(request["text"])
    model_map = {
        "coding": "coder",    # FOUNDRY:8006
        "research": "general", # FOUNDRY:8000
        "creative": "creative",# FOUNDRY:8000
        "infra": "fast",       # when deployed
        "simple": "fast",
        None: "general"        # default fallback
    }
    return {"route": route.name if route else None, "model": model_map.get(route.name if route else None, "general")}
```

**When to build:** After Phase 0 fixes, before Phase 2 agent work. The classifier makes agent routing decisions free and instant instead of burning LLM tokens on classification.

### 2.6 Daily Development Workflow (How a Session Looks)

**Morning startup:**
1. SSH from DESK to DEV: `ssh dev`
2. Attach tmux: `~/bin/athanor` → ATHANOR session (claude + shell windows)
3. Claude Code starts → SessionStart hook fires → shows:
   - Last health check result (any alerts?)
   - Active plan file
   - GPU utilization summary
   - Pending agent tasks
   - VAULT disk usage
4. Check morning report from overnight LangGraph agents

**Interactive work (human present — Claude Code is governor):**
- Complex architecture/design → stay in Opus
- Need to edit 40 files → "Let me set up Aider for this" → `aider --architect`
- Need parallel tasks → "Let me start claude-squad" → 3 tmux panes with worktrees
- Quick research → "Let me check with Gemini" → `gemini "what is the latest..."`
- Terminal debugging → "This needs Codex" → `codex "debug the network issue"`
- Need deep research → "Run this through Perplexity Deep Research"
- Bulk boilerplate → `ANTHROPIC_BASE_URL=http://192.168.1.203:4000 claude` → local Qwen3.5
- Code review → `/code-review` → 5 parallel Sonnet agents

**Background work (human absent — LangGraph agents are governor):**
- APScheduler fires health checks every 5 min (reads only)
- Creative agent generates EoBQ assets when WORKSHOP 5090 is free
- Intelligence curator scans feeds (when implemented)
- Prometheus alerts trigger incident response agents
- All on local models ($0), results logged to PostgreSQL + Langfuse

**Subscription limit management:**
- Track Opus utilization via response headers
- When approaching daily limit → Claude Code suggests switching to Gemini CLI or local
- Gemini CLI has 1000 free/day — use for quick questions instead of Opus
- Codex CLI for terminal-heavy work (separate from Claude rate limit)
- Kimi Agent Swarm for massive parallel research (separate from Claude rate limit)
- All subscriptions have independent rate limits — spread work across all of them

### 2.7 Five Undeployed Agents (Phase 4 Build)

**Agent 1: Evaluator (Tier 2 — The Judge)**
- Model: Opus via Max subscription (quality gate needs best model)
- Purpose: Score agent output quality on 0-1 scales (accuracy, coverage, tool efficiency)
- Pattern: Evaluate-and-Iterate loop — agent produces output → evaluator scores → accept/retry
- Tools: LLM completion (for scoring), file read (for context), PostgreSQL (log scores)
- Trigger: Invoked by orchestrator after high-stakes agent tasks
- Implementation: LangGraph node with structured JSON output schema
- Guardrail: Use surgically, not on every task (Opus tokens are rate-limited)

**Agent 2: Fact-Checker (Tier 2 — The Verifier)**
- Model: GLM-5 via Z.ai subscription (Omniscience Index #1, lowest hallucination)
- Purpose: Decompose claims into atomic statements → verify each → flag contradictions
- Tools: Web search (Tavily/Brave), knowledge graph query (Neo4j), document search (Qdrant)
- Pattern: claim_list = decompose(output) → for each claim: evidence = search(claim) → score(claim, evidence) → flag contradictions
- Trigger: Invoked on research agent output before presenting to user

**Agent 3: Voice Interface (Tier 3 — The Mouth/Ear)**
- Model: Whisper large-v3 (STT) + Qwen3.5-9B (intent) + Kokoro-82M (TTS)
- Purpose: Hands-free cluster interaction via voice
- Pipeline: Silero VAD (30ms) → faster-whisper (150ms) → intent classification (10ms) → LLM response (300ms) → Kokoro TTS (100ms) = ~590ms end-to-end
- Deploy on: DEV (Whisper on 5060Ti, Kokoro on CPU)
- Tools: All existing agent tools via voice commands
- Trigger: Always-on listening mode when activated

**Agent 4: HERS Energy (Tier 4 — The Inspector)**
- Model: Sonnet via Max subscription (structured data) + Gemini (math)
- Purpose: Domain-specific for Ulrich Energy S-Corp business
- Tools: RESNET database lookup, duct leakage calculators, BKI tracking, ENERGY STAR MFNC
- Pattern: Input data → calculate → generate report
- Trigger: Manual invocation for energy audit work

**Agent 5: EoBQ Game Agent (Tier 4 — The Dungeon Master)**
- Model: JOSIEFIED-Qwen3-8B (mandatory — abliterated, 10/10 NSFW adherence)
- Backup: Nous Hermes 3 8B (character voice consistency), Midnight Miqu 70B (premium narrative)
- Purpose: Procedural dialogue generation with character memory for Empire of Broken Queens
- Tools: Qdrant (character memory), Neo4j (relationship graph), file write (dialogue export), Stash API (reference scenes)
- **19-Trait Sexual Personality DNA System** (verified from Empire design docs):
  Each of 21 queens has unique values across: Desire Type, Accelerator/Brake Sensitivity, Pain Tolerance, Humiliation Enjoyment, Exhibitionism Level, Gagging Response, Moaning Style, Tear Trigger, Orgasm Style, Awakening Type, Blackmail Need, Addiction Speed, Jealousy Type, Aftercare Need, Switch Potential, Group Sex, Roleplay, Betrayal, Voice
  These traits MUST be injected into every dialogue prompt for character consistency
- **Content scale:** 21 queens × 10+ scenes × 8 endings = 1680+ unique scene variations
- **Asset pipeline per character:** FLUX prompt (physical blueprint defined per queen) → PuLID face consistency → LTX 2.3 animated scenes → Dia 1.6B dialogue audio
- **Game engine:** Ren'Py (visual novel framework, Python-based)
- Hard rule: ALL traffic stays local, zero cloud APIs
- Trigger: Manual invocation for writing sessions
- **SoulForge Engine (from design docs):** Procedural character generation — LLM generates 19-trait DNA + backstory → image gen creates appearance via LoRA merge → voice synthesis → Ren'Py integration. Target <68s/character. Phase 5 evaluate.
- **Scale warning:** Full spec = 300+ scenes, 1800+ phone messages, 12-16 endings/queen, 1200+ achievements. Multi-year production. Build the AGENT first, content follows.
- **Tool updates from design docs:** Mochi 1→LTX 2.3, Llama-3.1-8B→JOSIEFIED-Qwen3-8B, RVC v2.2→Dia 1.6B
- **Source docs:** Empire/ folder — ALL 17 files READ and verified March 18. Contains full master blueprint, 19-trait DNA profiles for all 21 queens, physics docs, gap analysis, tools audit, performer databases.

---

## Phase 3: Content Pipeline & Quality Scoring

### 3.1 Image Quality Scoring Service

**Deploy on WORKSHOP RTX 5060Ti (16GB):**

| Model | VRAM | Purpose |
|-------|------|---------|
| Aesthetic Predictor V2.5 | ~2.5GB | Primary quality filter (SigLIP-based, scores 1-10, content-agnostic) |
| Custom MLP | ~0.1GB | NSFW-fair quality scoring (trained on own rated data) |
| Total | ~2.6GB | Leaves 13.4GB for JOSIEFIED-Qwen3-8B |

**Why Aesthetic Predictor V2.5:**
- SigLIP-SO400M backbone (~878M params)
- Improved over LAION Aesthetic V2 for diverse domains
- ComfyUI node exists: `comfyui-aesthetic-predictor-v2-5`
- No explicit harmlessness penalty (unlike ImageReward)
- Scores 1-10 scale

**Why NOT ImageReward/PickScore/LAION Aesthetic V1:**
- ImageReward: Explicitly scores on "harmlessness" — penalizes pornographic content by design
- PickScore: Trained on SFW Pick-a-Pic data — scores on NSFW are essentially random
- LAION Aesthetic V1: Has Western cultural biases, unreliable on generated images

**Custom MLP Training (Phase 3.2 — VERIFIED, complete procedure):**

**Why SigLIP over CLIP:** SigLIP-SO400M was trained WITHOUT explicit NSFW filtering (unlike OpenAI CLIP which aggressively filtered nudity). Its embedding space has better coverage of adult content characteristics. 1152-dim embeddings vs CLIP's 768-dim — richer representation.

**Training procedure (verified from improved-aesthetic-predictor + LAION + QUASAR papers):**
1. **Collect training data**: Rate 1000-2000 auto_gen images on 1-10 scale
2. **Pre-compute embeddings**: Load SigLIP-SO400M, extract 1152-dim vectors for each image. Save as `embeddings.npy` + `ratings.npy`. Takes ~5 min on GPU, ~15 min on CPU.
3. **Train MLP**:
   ```python
   # Start with linear (LAION found linear beat MLPs for ranking)
   model = nn.Linear(1152, 1)
   # Graduate to MLP if underfitting:
   # nn.Sequential(nn.Linear(1152, 512), nn.ReLU(), nn.Dropout(0.2), nn.Linear(512, 1))
   optimizer = Adam(lr=1e-3)
   loss_fn = nn.MSELoss()
   # Train: batch 64-256, 50 epochs, early stopping on val loss
   ```
4. **Evaluate**: 5-fold CV on 80%, report SRCC on held-out 20%. Target: >0.5 (meaningful), >0.65 (good).
5. **Training time**: Seconds on CPU (just an MLP on .npy files). No GPU needed.

**Reference code**: Fork [christophschuhmann/improved-aesthetic-predictor](https://github.com/christophschuhmann/improved-aesthetic-predictor), swap CLIP for SigLIP, adjust input dim 768→1152.

**Key insight from LAION team**: Lower MSE ≠ better subjective ranking. A single linear layer outperformed 5-layer MLPs for visual ranking quality. Start simple.

### 3.1b Closed Feedback Loop: Scores → Prompt Tuning (User Priority #6)

**The gap:** Scoring images is step 1. The ACTUAL value is closing the loop — scores feed back into prompt generation to improve quality over time.

**Concrete mechanism:**
1. Auto_gen generates image with LLM prompt → ComfyUI → output
2. Aesthetic Predictor V2.5 scores the output (1-10)
3. Score is logged with: prompt text, theme, subject, model params, timestamp
4. **Per-theme quality tracking:** Running average score per theme. If theme X consistently scores <5.5, flag it for prompt revision.
5. **Per-subject quality tracking:** Running average per performer. If subject Y scores low, their reference images or physical attribute injection may need updating.
6. **Feedback injection into LLM prompts:** The existing `feedback.py` already injects feedback context into LLM prompt generation. Extend it to include: "Recent images of [subject] with [theme] scored [avg]. Previous high-scoring prompts used [keywords]. Avoid [low-scoring patterns]."
7. **Best-of-N for auto_gen:** Generate N=4 images per drop, score all 4, keep the best. Discard <5.5. This alone could reduce the 81% rejection rate.

**Data flow:**
```
LLM prompt gen ←── feedback.py ←── score_history.json
     ↓                                      ↑
ComfyUI FLUX pipeline                       |
     ↓                                      |
Output image → Aesthetic V2.5 scorer ──→ log score
```

**Already partially implemented:** feedback.py logs ratings and injects context. The scoring model and N>1 generation are the missing pieces.

### 3.2 Performer Data Consolidation (VERIFIED — complete merge plan)

**Current performers.json:** 801 records, 37 fields, on VAULT at `/mnt/user/data/performers.json`
**All 3 Triage sources are SUBSETS** — pure enrichment merge, no new performers.

**Major enrichments achievable:**
| Field | Current Fill | After Merge | Source |
|-------|-------------|-------------|--------|
| waist | 0% | 86% | MPL (688/801) |
| hip | 0% | 86% | MPL (691/801) |
| implant_detail | NEW | 78% | MPL (622) |
| career_start | 23% | 78% | MPL (623) |
| rare_media | 32% | 60% | MPL (460) |
| bust_to_frame | 4.5% | ~9% | Master TOSI sheet (36 records) |

**NOTE: TOSI score is DEPRECATED and WRONG — do NOT import tosi_score or tosi_category fields. Use the spreadsheet data (measurements, career, rare scenes) but discard the TOSI scoring metric.**

**4 new fields:** implant_detail, rare_scene_title, rare_scene_category, bust_to_frame_description
**5 dead fields to remove:** content_specialization, rating, style_match, is_subject, reference_count

**Complete merge script provided** (Python/openpyxl) — agent output at `a7258e81389fca4a2`. Needs modification: remove TOSI score import, remove gen_suitability recalculation from TOSI. Keep all physical attribute and career data imports.

**Execution:** Upload 3 XLSX to VAULT, run merge script, output to `performers_merged.json` with automatic backup.

**Target:** Merge into existing `performers.json` on VAULT (currently 801 performers from 5 sources)

**Consolidation steps:**
1. Deduplicate (2 confirmed duplicate file pairs)
2. Backfill physical attributes from Performers Master (85% fill rate on bra/implants/body)
3. Import `bust_to_frame_description` from TOSI sheet (populated for ~36 performers — high value for prompt injection). Do NOT import TOSI score (deprecated/wrong).
4. Import measurements (waist, hip, height, weight) from MPL sheet
6. Import trait tags from OF Models data (new taxonomy for theme system)
7. Build studio registry: merge Studios Master (359) + sites files (42) + defunct doc (40+)
8. Export as updated `performers.json` and push to VAULT

### 3.3 WORKSHOP 5090 — Dedicated Creative GPU

**Decision:** Remove vllm-node2 (3rd copy of same LLM). Dedicate 5090 to creative generation.

**Layout:**
- ComfyUI with FLUX.1 Dev FP8 + PuLID Flux — permanent (image gen, ~12-15GB)
- LTX 2.3 NVFP4 — on-demand (video gen, ~31GB — needs full GPU, ComfyUI unloads first)
- JOSIEFIED prompt generation routes to WORKSHOP 5060Ti or FOUNDRY coder

**Time-sharing between image gen and video gen:**
- Image gen (ComfyUI + FLUX): loads models per workflow, releases between runs
- Video gen (LTX 2.3): needs full GPU — trigger ComfyUI `free` command first, load LTX, generate, unload
- LangGraph creative-agent orchestrates the swap sequence
- Both run through ComfyUI (LTX has ComfyUI nodes) — so it's actually the same process managing both

**LLM inference for creative prompts:**
- Auto_gen pipeline's LLM prompts → LiteLLM `creative` alias → FOUNDRY coordinator (not WORKSHOP)
- No vLLM on WORKSHOP 5090 anymore — that GPU is 100% creative generation
- Cloud subscription overflow available if FOUNDRY is busy (sunk cost)

---

## Phase 4: Video & Creative Pipeline

### 4.1 LTX 2.3 Video Generation

**Model:** LTX Video 2.3 (22B params, March 5 2026)
**GPU:** WORKSHOP RTX 5090 (32GB)
**Optimal format: NVFP4** (official Lightricks/LTX-2.3-nvfp4, ~21.7GB) — uses native Blackwell FP4 tensor cores for maximum throughput. Significantly faster than GGUF on RTX 5090.
**Fallback: GGUF Q4_K_M** (14.3GB) if NVFP4 has issues.

**VRAM Budget (NVFP4 path):**
- LTX-2.3 NVFP4: ~21.7GB
- Gemma 3 12B FP4: ~9.5GB
- Total: ~31.2GB (tight fit on 32GB, viable with ComfyUI model offloading)

**VRAM Budget (GGUF Q4_K_M path):**
- LTX-2.3 Q4_K_M: 14.3GB
- Gemma 3 12B UD-Q4_K_XL: ~7.4GB
- Embeddings connectors: ~2.3GB + VAE ~1.5GB + working memory ~2-3GB
- Total: ~27.5GB (comfortable, 4.5GB headroom)

**Q8_0 GGUF does NOT fit** (~32.5GB with Gemma — exceeds 32GB)**
**GGUF is slower than NVFP4 on Blackwell** — dequantization overhead negates FP4 tensor core benefit

**ComfyUI integration:**
- Required nodes: ComfyUI-LTXVideo (Lightricks), ComfyUI-GGUF (city96)
- T2V workflow: CLIP→LTXVConditioning→EmptyLatent+EmptyAudio→Concat→Scheduler→Sampler→Separate→VAEDecode→Combine→Save
- Speed: ~25s for 720p/4s@24fps on 5090 (distilled pipeline)

**Two-stage upscale:**
1. Generate at 480p/720p
2. LTXVLatentUpsampler (2x spatial) in latent space
3. 8-step sampling with distilled LoRA
4. VAEDecodeTiled for 1080p/1440p output

**LoRA training:**
- Official LTX2-Trainer in Lightricks/LTX-2 monorepo
- RTX 5090: supported via `ltx2_av_lora_low_vram.yaml`
- Dataset: MP4, dims divisible by 32, frame count = 8n+1
- Character LoRA: 10-20 images or 5-10 clips, 1-2 hours on 5090
- **All LTX 2.0 LoRAs must be retrained** — new latent space

**Alternative video models to evaluate (from r/generativeAI March 2026):**
| Model | Params | VRAM | Local? | Uncensored? | Notes |
|-------|--------|------|--------|-------------|-------|
| **LTX 2.3** (planned) | 22B | ~27-31GB Q4/NVFP4 | Yes | Yes (Apache 2.0) | 5.7x faster than Wan, native audio, BEST LOCAL OPTION |
| **HunyuanVideo 1.5** | Large | 8GB+ with GGUF Q4 via ComfyUI | Yes | Filter-free open weights | Tencent. ComfyUI support. Quality competitive. GGUF path viable. |
| **Open-Sora 2.0** | 11B | 24GB+ consumer, 40GB+ full | Partially | Open weight | Trained for $200K. Competitive with HunyuanVideo. 720p max. |
| **Wan 2.2 A14B** | 14B MoE | ~24GB | Yes | Community forks exist | Higher ceiling on complex motion. 18x slower than LTX. |
| **Seedance 2.0** | Unknown | API only (ByteDance) | **No** — API only | Unknown | 2K native, native audio. No open weights. Violates sovereignty. |
| **Veo 3.1** | Unknown | API only (Google) | **No** — API only | No | 4K + native audio. Expensive credits. Violates sovereignty. |

**Decision:** LTX 2.3 remains PRIMARY — Apache 2.0, fastest local, native audio, fits on 5090. HunyuanVideo 1.5 GGUF is worth evaluating as secondary option (ComfyUI support, potentially better quality at lower quants). Seedance/Veo rejected — API-only, violates data sovereignty principle.

### 4.2 TTS for Dialogue (EoBQ)

**Top pick: Dia 1.6B (Nari Labs)**
- ~10GB VRAM on 5060Ti
- Dual-speaker [S1]/[S2] tags for dialogue
- 17+ emotion tags
- Apache 2.0 license
- Best fit for Empire of Broken Queens visual novel

**Alternatives:**
- Orpheus TTS 3B: <4GB GGUF Q4, llama.cpp integration, 8 voices
- Kokoro-82M: ✅ **ALREADY DEPLOYED** on FOUNDRY:8200 via `speaches` container (Kokoro-82M v1.0 ONNX, 54 voices, OpenAI-compatible API)
- Chatterbox Turbo: ~4-8GB, emotion slider, sub-200ms latency

### 4.3 Image Generation Optimization

**Current:** FLUX + PuLID/ReActor on WORKSHOP, auto_gen pipeline producing ~10s/image
**Enhancements:**
- FLUX.2 Dev with PuLID Flux II: ~12GB VRAM (FP8), 80-93% face consistency
- InfiniteYou (ByteDance): already installed, FP8 mode ~24GB on 5090
- JOSIEFIED-Qwen3-8B on 5060Ti for uncensored prompt generation (10/10 adherence, abliterated)
- Best-of-N sampling (N=4-8): generate multiple, score with Aesthetic Predictor V2.5, keep best

### 4.4 Voice Pipeline (from KAIZEN vision)

**End-to-end target: ~580ms**
1. Silero VAD: ~30ms (speech detection)
2. faster-whisper large-v3-turbo: ~150ms (STT, ~1.5GB VRAM)
3. LLM inference (Qwen3.5-9B): ~300ms TTFT
4. Kokoro-82M: ~100ms TTFB (TTS, CPU)

**Deploy on:** DEV RTX 5060Ti (Whisper) + DEV CPU (Kokoro)

---

## Phase 4B: Meta-Orchestrator Layer (NEW — CCManager)

**Discovery:** [CCManager](https://github.com/kbwo/ccmanager) is a Coding Agent Session Manager that manages ALL coding CLIs from a single interface: Claude Code, Gemini CLI, Codex CLI, Cursor Agent, Copilot CLI, Cline CLI, OpenCode, AND Kimi CLI.

**What it does:** Manages sessions across tools, projects, and git worktrees. Tracks session state per tool. Auto-approval via Haiku analysis. Worktree hooks for env setup. Status change hooks for notifications. Devcontainer support for sandboxing.

**Why it matters:** This is the layer ABOVE Claude Code that the user asked about. It doesn't replace Claude Code — it COORDINATES it alongside every other CLI tool.

**Alternatives evaluated:**
- [Mozzie](https://producthunt.com/products/mozzie) — local-first desktop orchestrator for parallel agents
- [Codirigent](https://github.com/oso95/Codirigent) — tmux-style workspace for side-by-side CLIs
- [multi-agent-shogun](https://github.com/yohey-w/multi-agent-shogun) — samurai hierarchy (shogun→karo→ashigaru)

**Architecture with CCManager:**
```
CCManager (meta-orchestrator)
  ├── Claude Code (Opus) → complex architecture
  ├── Codex CLI (GPT-5.4) → terminal workflows
  ├── Kimi CLI (K2.5) → Agent Swarm breadth
  ├── Gemini CLI → quick tasks, free
  ├── Aider → structured diffs (local models)
  ├── OpenCode → overflow (any provider)
  └── Goose → repeatable recipes
```

**Install:** `cargo install ccmanager` or download binary from GitHub releases. Self-contained, no tmux needed.

---

## Phase 4C: Autonomous Multi-Project Development (NEW)

**Goal:** While Shaun sleeps, AI agents work on 5-10 projects simultaneously. He wakes up to PRs with diffs, test results, and AI review comments.

**Evidence:** Real solo developers in March 2026 serving 15-20 concurrent clients, shipping 5x faster. One solo dev runs $55K MRR SaaS with 400+ customers using coding agents for boilerplate/tests/docs. Agent Teams built a 100,000-line Rust C compiler across 2000 sessions.

**Architecture:**
- **sandboxed.sh** on FOUNDRY — Docker Compose orchestrator, isolated container per project
- **Claude Code headless** (`-p`) as primary agent runtime (subscription parallelism)
- **OpenHands** self-hosted for GitHub-issue-to-PR on repos with good issue descriptions
- **CodeRabbit** on all repos for automated PR review
- **Local Qwen3.5** via LiteLLM for cheaper triage/planning/review

**The overnight pattern:**
```
2am cron → for each project in PROJECT_QUEUE:
  claude -p "Pick up next issue labeled ai-ready" \
    --worktree nightly \
    --allowedTools "Edit,Bash(git:*),Bash(npm test)" \
    --dangerously-skip-permissions \
    --max-budget-usd 2.00
  → TDD (writes tests first) → implements → tests → pushes PR
  → CI → CodeRabbit reviews → human approves in morning
```

**Project types that work autonomously:**
| Type | Fit | Notes |
|------|-----|-------|
| Websites (Next.js) | Excellent | Clear components, strong test frameworks |
| APIs/backends | Good | OpenAPI contracts, CRUD automatable |
| Ren'Py visual novels (EoBQ) | Surprisingly good | `renpy-mcp` has 60 tools for VN development |
| Godot games | Good | Godogen (Mar 2026) generates complete games |
| Infrastructure/Ansible | Good | Declarative, testable |
| Mobile (React Native) | Feasible | Similar to Next.js patterns |

**Quality gates:**
1. TDD — agent writes tests FIRST
2. CI/CD with full test suite on every PR
3. CodeRabbit automated review
4. Mutation testing (MuTAP)
5. Weekly human architecture review
6. Agents constrained to SPECIFIC tasks, not open-ended

**Key tools to install:**
- sandboxed.sh (Docker Compose on FOUNDRY)
- OpenHands (self-hosted Docker)
- CodeRabbit (GitHub integration)
- renpy-mcp (60 tools for EoBQ)
- Godogen skills (Godot game generation)

**The bottleneck is REVIEW, not generation.** Agents produce fast. Verifying correctness is the constraint. AI code review (CodeRabbit) reduces this burden by catching issues before human sees the PR.

---

## Phase 4D: Uncensored Content Routing (NEW — Sovereignty Layer)

**Problem:** Cloud AI models (Opus, GPT-5.4, Gemini) WILL refuse explicit content, pen testing code, and adult content curation. The system needs automatic failover to uncensored local models WITHOUT the user having to think about it.

**Principle:** NSFW content NEVER touches cloud APIs. Not to avoid refusals — for sovereignty and privacy. The intent classifier pre-routes sensitive content to local models.

### Uncensored Model Stack (verified March 2026)

**Small (7-9B) — Fast uncensored:**
| Model | Method | VRAM (Q4) | Best For |
|-------|--------|-----------|----------|
| JOSIEFIED-Qwen3-8B-abliterated | Abliteration | ~6-8GB | General uncensored chat, 10/10 adherence |
| Dolphin 3.0 Llama 3.1 8B | Training-filtered | ~6-7GB | Zero refusal, steerable, coding |
| Nous Hermes 3 (8B) | ChatML-tuned | ~6-8GB | Long-form narrative, character voice |

**Medium (14-32B) — Quality uncensored:**
| Model | Method | VRAM (Q4) | Best For |
|-------|--------|-----------|----------|
| JOSIEFIED-Qwen3-14B-v3 | Abliteration | ~10-12GB | All-rounder uncensored |
| GPT-OSS-20B abliterated | Abliteration | ~14-16GB | OpenAI quality, uncensored |
| Qwen3-42B-A3B MASTER-CODER abliterated | Abliteration (MoE) | ~24GB | Coding-focused uncensored, fits single GPU |

**Large (70B+) — Frontier uncensored:**
| Model | Method | VRAM (Q4) | Best For |
|-------|--------|-----------|----------|
| DeepSeek-R1-70B abliterated | Abliteration | ~48GB (dual GPU) | Frontier reasoning, 97.3% MATH-500 |
| Llama 4 70B abliterated | Abliteration | ~40GB | Deep narrative, uncensored reasoning |

### Uncensored Image/Video Generation
- **FLUX:** Already uncensored via `flux-uncensored.safetensors` LoRA (in pipeline)
- **SDXL:** Pony Diffusion V6 XL, Juggernaut XL v9 — uncensored by default
- **LTX 2.3:** Apache 2.0, no built-in content filter — fully uncensored
- **Wan 2.2:** Open-source, no filters. NSFW forks exist. Already have Wan2GP
- **HunyuanVideo:** Official censored, community builds strip filters (CivitAI)
- **ComfyUI:** No content filtering — it's a local tool

### Routing Architecture

**LiteLLM `content_policy_fallbacks` (already supported in v1.81.9):**
```yaml
router_settings:
  content_policy_fallbacks:
    - claude-sonnet-4-6: ["local-uncensored"]
    - gpt-5.4: ["local-uncensored"]
    - gemini: ["local-uncensored"]

model_list:
  - model_name: local-uncensored
    litellm_params:
      model: openai/josiefied-qwen3-8b
      api_base: http://192.168.1.225:8001/v1
```

**Intent-based pre-routing (preferred — never sends NSFW to cloud):**
```
User request → Semantic Router (Qwen3-Embedding)
  ├── nsfw_flag: false → Route normally (any model)
  └── nsfw_flag: true → SOVEREIGN ROUTE
        ├── Text → JOSIEFIED-Qwen3-8B (local)
        ├── Code → Qwen3-42B-A3B MASTER-CODER (local)
        ├── Images → ComfyUI + FLUX uncensored LoRA (local)
        ├── Video → LTX 2.3 / Wan 2.2 (local, no filter)
        ├── Voice → Dia / Kokoro (local, no filter)
        └── Scraping → Local agents (no content policy)
```

**Claude Code specific pattern:**
- Claude Code handles game ENGINE code (Ren'Py mechanics, branching, UI) — no refusal
- Explicit PROSE/DIALOGUE routes to JOSIEFIED via delegate skill
- renpy-mcp (60 tools) works with ANY model — point at uncensored for explicit content

### Workflows That Require Uncensored Path

| Workflow | What gets refused by cloud | Local uncensored model |
|----------|---------------------------|----------------------|
| EoBQ game development | Explicit dialogue, NSFW Ren'Py scenes | JOSIEFIED-8B or Dolphin 3.0 |
| Adult image generation | NSFW prompt creation | Local Qwen3.5-35B (already working) |
| Adult video generation | NSFW choreography | LTX 2.3 / Wan 2.2 (no filter) |
| Performer data curation | Adult metadata, scene descriptions | Local knowledge agent |
| Adult web scraping | Site crawling, content indexing | Local data-curator agent |
| Pen testing / security | Exploit code, vuln scanning | Qwen3-42B-A3B MASTER-CODER |
| Creative writing (EoBQ) | Explicit sexual narratives | JOSIEFIED / Midnight Miqu |
| Stash integration | Scene matching, auto-tagging | Local stash-agent |

### Legal Framework (US)
- Running abliterated models on private hardware: **Legal** (no law prohibits)
- AI-generated adult content of fictional characters: **Legal**
- Pen testing own infrastructure: **Legal** (CFAA requires "unauthorized access")
- NEVER generate CSAM. NEVER create non-consensual deepfakes for distribution.
- Take It Down Act (May 2025): illegal to SHARE non-consensual explicit images

---

## Phase 4E: Unraid Media Server & Usenet Automation (NEW)

**Current state:** VAULT runs Plex, Sonarr, Radarr, Prowlarr, SABnzbd, Tautulli, Overseerr, Tdarr, Stash. Container watchdog monitors critical services every 5 minutes. Media agent has 13 tools for Sonarr/Radarr/Plex management.

**Usenet setup:** Provider/indexer credentials exist in XLSX (SECURITY: encrypt!). SABnzbd is deployed. The automation chain: Sonarr/Radarr → Prowlarr (indexer) → SABnzbd (downloader) → post-processing → Plex library scan.

**Tdarr:** Intel ARC A380 QSV transcoding. Flow-based H.265 conversion. 36K+ files tracked. Memory-limited to 16GB after V8 heap bloat fix.

**Stash:** 22.5K scenes, 14.5K performers, Intel VAAPI hardware acceleration. 9 plugins, 9 scrapers. Daily backup. Auto_gen pipeline generates images based on performer data.

**What the media-agent (already running) can do:**
- Search TV shows/movies (Sonarr/Radarr API)
- Check calendar (upcoming releases)
- View download queue
- Get library stats
- Add shows/movies
- Check Plex activity and watch history

**What's missing:**
- VPN container (Gluetun) for download privacy — BLOCKED on NordVPN credentials (BLOCKED.md)
- Quality-based auto-upgrading (replace 720p with 1080p when available)
- Integration between Stash performer DB and auto_gen pipeline performer.json (partial)
- AI-powered scene tagging (using vision model to auto-tag scenes in Stash)
- SpiderFoot OSINT setup (setup script exists in Downloads: `setup-spiderfoot-vault.sh`)

### Complete Usenet Stack (research complete)

**Downloader:** SABnzbd (better *arr integration). **Providers:** Newshosting unlimited (Omicron, ~$3-5/mo) + Blocknews block (Abavia, $10-15 one-time) + optional UsenetExpress (independent). **Indexers:** NZBgeek ($12/yr) + DrunkenSlug (invite). Via Prowlarr.

**VPN:** SSL sufficient for Usenet. VPN optional unless torrenting. Gluetun with split tunnel if needed. **BLOCKED:** NordVPN credentials (BLOCKED.md).

**Chain:** Seerr request → Sonarr/Radarr → Prowlarr → indexers → SABnzbd → post-process → Tdarr (H.265 QSV) → Plex → Bazarr (subs) → ntfy confirm.

**Missing containers to deploy on VAULT:**
| Container | Port | Purpose |
|-----------|------|---------|
| Whisparr | 6969 | Adult content *arr (complements Stash: acquisition vs metadata) |
| Seerr | 5055 | Unified request management (Overseerr+Jellyseerr successor) |
| Bazarr | 6767 | Automated subtitle downloads |
| Recyclarr | — | Auto-syncs TRaSH quality profiles to Sonarr/Radarr daily |

**Tdarr optimizations:** AV1 encoding available (ARC A380 supports, 20-30% better than HEVC). ICQ mode `-global_quality 22`. 10-bit `-profile:v main10`.

**Stash + AI:** InsightFace face recognition (already on WORKSHOP) → Stash GraphQL → auto-tag performers. Cross-ref against performers.json. Submit fingerprints to StashDB.

---

## Phase 5: Subscription Utilization & Maximization

### 5.1 Current Subscription Inventory (from AI_Subscriptions_and_API_Keys_Master.xlsx)

**Paid Subscriptions ($543.91/mo):**

| Service | Cost/mo | Status | Action |
|---------|---------|--------|--------|
| Claude Max 20x | $200 | Core — 60%+ of all work | Keep |
| ChatGPT Pro | $200 | GPT-5.4 + o3-pro + computer-use | Evaluate — biggest target |
| GitHub Copilot Pro+ | $32.50 | IDE GPT-5.4/Opus + OpenRouter BYOK | Evaluate — BYOK bridge value |
| Z.ai GLM Coding Pro | $30 | GLM-4.7 (Terminal-Bench 56.2%) | Evaluate — auto-renewed Mar 17 |
| Perplexity Pro | $20 | Deep Research (Opus-powered) | Keep — "highest ROI research tool" |
| Gemini Advanced | $19.99 | GPQA 94.3%, 1M context | Keep — essential |
| Kimi Code Allegretto | $19 | K2.5 Agent Swarm (100 parallel), CLI available | Maximize — Agent Swarm is unique capability |
| Venice AI Pro | $12.42 | NSFW API, $149/yr | Auto-cancel July 23, 2026 |
| Qwen Code | $10 | DashScope access, 1M free tokens/model | Evaluate — local Qwen3.5 reduces need |
| Mistral Code | $0 | Codestral autocomplete, free Experiment | Keep — free |

**Free AI Coding Tools (Active — In Use):**

| Tool | Type | Key Feature |
|------|------|-------------|
| Claude Code CLI | Terminal agent | Primary. Opus 4.6, MCP, subagents, 1M context |
| Codex CLI (OpenAI) | Terminal agent | GPT-5.3-Codex, Rust rewrite, MCP support, Apache 2.0 |
| Gemini CLI | Terminal agent | 1M context, free 1000 req/day, web search grounding |
| Roo Code | VS Code IDE | Apache 2.0, primary multi-model IDE, 9 mode routing |
| Aider | Terminal agent | LiteLLM-powered, architect/editor split, git-first |
| Cline | VS Code ext | Browser automation, MCP tool creation, high token usage |
| claude-squad | Multi-agent | Manages Claude Code, Codex, Aider, OpenCode, Amp in tmux with git worktree isolation |
| Tongyi Lingma | VS Code ext | Alibaba, Qwen-based autocomplete + chat |
| Kimi Code ext | VS Code ext | Moonshot, dedicated extension for Kimi models |
| Mistral Code ext | VS Code/Zed ext | Codestral autocomplete |
| Qwen Code CLI | Terminal agent | Alibaba, 480B MoE Qwen3-Coder, free quota, Apache 2.0 |
| Happy Coder | Mobile | Mobile Claude Code access |

**Free AI Coding Tools (Evaluate — Being Assessed):**

| Tool | Type | Key Feature | Stars/Users |
|------|------|-------------|-------------|
| OpenCode | Terminal (Go TUI) | BYOK 75+ providers, LSP, multi-session | 120K+ stars |
| Goose (Block) | CLI + Desktop | MCP-native, Recipes, Apache 2.0 | Used by 60% of Block (12K employees) |
| Kilo Code | VS Code/JB/CLI/Slack | Cline/Roo fork, orchestrator mode | 1.5M users |
| OpenHands | Autonomous agent | GitHub issue → working PR, 77.6% SWE-bench | Major OSS |
| Kiro (AWS) | IDE + CLI | Spec-driven dev, free preview, Claude Sonnet powered | New (AWS) |
| Continue | VS Code/JetBrains | YAML config, shareable assistants | OSS |
| Zed | GPU editor | Rust, ACP protocol, multiplayer AI | Growing |
| Trae (ByteDance) | IDE | Free premium models, builder mode | **Telemetry concerns** |
| Amp | Coding agent | Model-agnostic, free (ad-supported) | New |
| Amazon Q Developer CLI | CLI | IaC, AWS troubleshooting, best practices | AWS ecosystem |
| Plandex | Terminal agent | 2M token context, large project planning | OSS |
| Crush CLI | Terminal (TUI) | Charmbracelet, beautiful UI, multi-model | New |

**API Keys (Active — Confirmed Working):**
Anthropic, OpenAI, Google AI, Mistral, DeepSeek, Moonshot (Kimi), DashScope (Qwen), Venice AI, Z.ai (Zhipu/GLM), OpenRouter, HuggingFace

**API Keys (Verify — Status Unknown, may need rotation/reactivation):**
xAI (Grok), Cohere, Groq, Cerebras, SambaNova, Fireworks, Together, Lepton, Replicate, Tavily, Serper, Exa, Brave Search, Perplexity API, ElevenLabs, Stability AI, fal.ai, Runway, LangSmith, Langfuse

**Current total:** $543.91/mo subscriptions (all sunk cost — maximize every resetting limit)

**Total Cost of Ownership (estimated):**
| Category | Monthly | Annual |
|----------|---------|--------|
| Subscriptions | $543.91 | $6,527 |
| Electricity (~800W avg cluster) | ~$50-80 | ~$600-960 |
| Hardware depreciation (est. $15K over 3yr) | ~$417 | ~$5,000 |
| Internet (part of existing service) | $0 additive | $0 |
| Cloud API tokens | $0 (flat-rate subs) | $0 |
| **Total** | **~$1,010-1,040** | **~$12,127-12,487** |

**What this buys:** 7 GPUs (132.5GB VRAM), 527GB RAM, 120 CPU cores, 25TB NVMe, 200TB HDD, unlimited local inference, 10 subscription AI services, 9 autonomous agents. Equivalent cloud compute would cost $5,000-10,000+/mo.

### 5.2 Subscription Philosophy: Maximize Utilization

**All subscriptions are sunk cost. Limits reset. The goal is to USE every subscription to its full capacity, not cut them.**

**Subscription utilization strategy:**

| Service | Resetting Limits | How to Maximize |
|---------|-----------------|-----------------|
| Claude Max 20x ($200) | ~900 msgs/5hr, weekly Opus quota | Primary for complex work. Overflow to Sonnet within same session. Track via anthropic-ratelimit-unified-5h-utilization header. |
| ChatGPT Pro ($200) | o3-pro ~15-20/mo, GPT-5.4 generous, Codex 300 tasks/mo | Use Codex CLI for terminal workflows. GPT-5.4 for computer-use tasks. o3-pro for hard math/algo only. |
| Gemini Advanced ($20) | 1000 req/day CLI (separate from sub), ~100 prompts/day web | Use Gemini CLI as daily driver for quick questions, research, 1M context ingestion. Free tier = unlimited overflow. |
| Copilot Pro+ ($33) | 1500 premium requests (Haiku 0.33x, Sonnet 1x, Opus 3x) | BYOK via OpenRouter for routing to Kimi/Mistral/Qwen. IDE autocomplete. GitHub Spark for prototyping. |
| Z.ai GLM ($30) | 5× Lite usage, Vision, Web Search, Zread MCP | Use for fact-checking (Omniscience Index #1). GLM-4.7 Flash for high-speed classification. |
| Perplexity Pro ($20) | Unlimited Deep Research (Opus-backed) | Primary for deep research tasks. Higher ROI than burning Claude tokens on research. |
| Kimi Code Allegretto ($19) | K2.5 Agent Swarm up to 100 parallel sub-agents | Use for massive breadth research. CLI available (install on DEV). Visual-to-code capability. |
| Venice AI Pro ($12) | 312 credits, auto-cancels Jul 2026 | Burn remaining credits on uncensored API tasks before cancellation. JOSIEFIED local replaces. |
| Qwen Code ($10) | 1M free tokens/model on DashScope, 90K req/mo | Use for Qwen3-Coder-Next cloud access. Tongyi Lingma extension. Free third-party models (Kimi, GLM, MiniMax). |
| Mistral ($0) | Free Experiment tier, Codestral autocomplete | Use for IDE autocomplete (#1 on LMsys copilot arena). Devstral 2 API access. |

**Daily workflow waterfall (maximize each sub's limits before moving to next):**
1. Claude Code (Opus) — complex architecture, design
2. Gemini CLI — quick questions, research, 1M context (1000 free/day)
3. Codex CLI — terminal workflows, GPT-5.4 tasks
4. Kimi Code CLI — Agent Swarm for breadth, visual-to-code
5. Perplexity — deep research sessions
6. Claude Code → LiteLLM → local — bulk coding, boilerplate ($0, unlimited)
7. Aider/Goose/Roo Code → LiteLLM → local — specialized patterns ($0)

**Venice auto-cancels July 23, 2026** — the only subscription ending. All others are sunk cost to maximize.

### A Day in the Life (Post-Implementation)

**Morning (DESK → SSH → DEV tmux "ATHANOR"):**
1. `~/bin/athanor` → attaches tmux session
2. SessionStart hook fires → shows: overnight agent report (which tasks ran, pass/fail), GPU status, disk, any ntfy alerts, active plan file
3. `/morning` command → comprehensive cluster health summary via LangGraph general-assistant
4. Auto_gen pipeline ran overnight → new images in gen-output, scored by Aesthetic Predictor V2.5 (>5.5 kept, <5.5 discarded)
5. Check Langfuse dashboard (VAULT:3030) for token usage trends

**Working session — Governor routing in action:**
- "Design the payment module" → Claude Code stays in Opus (architecture work)
- "Now implement it across 12 files" → Claude Code suggests: "This is bulk implementation. Want me to set up an Aider session with local Qwen3.5?" → `aider --architect openai/reasoning --editor openai/coder`
- "Research what auth library is best for this" → Perplexity Deep Research or Gemini CLI
- "Run these 3 tasks in parallel" → `claude-squad` with 3 tmux panes
- "Check if FOUNDRY containers are healthy" → delegates to infra-auditor agent via MCP
- "Write some EoBQ dialogue for Queen 7" → JOSIEFIED-Qwen3-8B on WORKSHOP 5060Ti (local, uncensored)
- "Generate a video of this scene" → LTX 2.3 on WORKSHOP 5090 via ComfyUI

**Background (autonomous, no human needed):**
- APScheduler runs health checks every 5 min via LangGraph agents
- Auto_gen pipeline generates images every 2 hours (18 subjects rotating)
- Memory consolidation at 3am (working → episodic → vault)
- Prometheus Alertmanager → webhook → agent for any degradation
- Langfuse traces every LLM call for cost/quality analysis

---

## Phase 6: Data Consolidation & Knowledge

### 6.1 Triage Data Summary

| Dataset | Records | Action |
|---------|---------|--------|
| Performers Master | 804 | Merge into performers.json |
| Master TOSI | 728 (duplicate pair) | Import physical attributes + career data ONLY — TOSI score is deprecated/wrong, do NOT import |
| Scenes Master | 515 | Import to Stash metadata |
| Studios Master | 359 | Build studio registry |
| OF Models | 11 | Import trait tag taxonomy |
| Sites files | 42 (duplicate pair) | Reference/bookmark registry |
| Defunct studios | 40+ | Historical studio tagging |
| Pipeline tools | 25 | Reconcile with WORKSHOP ComfyUI |
| Project Index | 368 | Meta-project tracking |
| Male Performers | 41 | Low priority — name list only |
| Usenet credentials | 40 | **SECURITY: Encrypt immediately** |

### 6.2 Current Memory System (6-tier, running on DEV)

| Tier | Backend | Records | Purpose |
|------|---------|---------|---------|
| Working | Redis (VAULT:6379) | Ephemeral | Session state, fast cache |
| Episodic | Qdrant (VAULT:6333) | 6 | Recent interactions |
| Semantic | Neo4j (VAULT:7687) | 3,241 nodes | Knowledge graph relationships |
| Procedural | PostgreSQL (VAULT:5432) | 10 | Operational procedures (seeded) |
| Resource | Qdrant + Meilisearch (VAULT:7700) | 347 | Ingested docs + search |
| Vault | PostgreSQL + Qdrant | 40 | Long-term consolidated knowledge |

**Services:** Memory service on DEV:8720, Perception on DEV:8730 (2 active watchers)
**Consolidation:** Daily 3am cron (Working→Episodic, Episodic→Vault)
**Status:** Operational but lightly populated. Perception ingested 7 project docs (95 chunks) + 15 codebase files (235 chunks).
**Issue:** Agent Qdrant URL points to FOUNDRY:6333 (old), not VAULT:6333 (current) — agents can't access vector memory properly.

### 6.3 Evaluate: Hindsight Agent Memory (Trending March 2026)

**What:** [Hindsight](https://github.com/vectorize-io/hindsight) — MCP-native agent memory system. Single Docker container with embedded PostgreSQL. MIT license. +44.6 points over full-context baseline on LongMemEval.
**Architecture:** retain() → recall() → reflect(). Four memory networks: World (facts), Experiences, Opinions (confidence-scored beliefs), Observations (derived mental models). Multi-strategy retrieval: semantic + BM25 + entity graph + temporal, cross-encoder reranking.
**Runs with Ollama** — can use local models, no cloud dependency.
**Why evaluate:** Could complement or simplify our 6-tier memory system (Redis + Qdrant + Neo4j + PostgreSQL + Meilisearch). Single container vs 5 separate services. MCP integration means Claude Code can use it directly.
**When:** Phase 5 — after stabilization. Run as parallel experiment alongside existing memory system.
**Install:** `docker run -p 8123:8123 vectorize/hindsight:latest`

### 6.4 Intelligence Stack (Future)

**Planned but not yet set up:**
| Service | Cost | Purpose | Status |
|---------|------|---------|--------|
| Inoreader Pro | ~$10/mo | RSS feed aggregation, AI-filtered | Planned |
| Readwise Reader | ~$8.49/mo | Read-later + highlights + export | Planned |
| Snipd | TBD | Audio layer (podcast highlights) | Verify if subscribed |
| NotebookLM | $0 | Google, included with Gemini Advanced | Active |
| n8n | $0 (self-hosted) | Webhook triggers for intelligence curation | Running on VAULT |
| Miniflux | $0 (self-hosted) | RSS feed aggregation | Running on VAULT |

**Intelligence Curator Agent (from 14-agent architecture):**
- Qwen3.5-4B classify (hundreds/hr) → Qwen3.5-9B summarize → Qwen3.5-27B deep analysis
- Sources: Miniflux RSS, Exa.ai neural search, arXiv, HuggingFace, GitHub
- Schedule: Classification every 30 min, deep analysis nightly
- Yields GPU when user is active, full bandwidth when idle

### 6.5 Multi-Account Claude Strategy (Future)

**Purpose:** When Claude Max rate limits hit during heavy autonomous coding sessions
**Setup:**
- Create second Claude account (Max 20x, $200/mo)
- Separate email: shaun+claude2@domain.com
- CLAUDE_CONFIG_DIR environment variable for switching: `alias claude-a="CLAUDE_CONFIG_DIR=~/.claude-primary claude"` / `claude-b`
- Separate Chrome profile for web UI
- Mirror: user preferences, custom style, 19 memory edits, projects, connected MCP servers
- Organic memories diverge naturally (fine for overflow)
**When to deploy:** Only when current rate limits consistently block work. Not yet.

### 6.6 API Key Audit

**20 keys in "Verify" status — check each, rotate or deactivate:**
xAI, Cohere, Groq, Cerebras, SambaNova, Fireworks, Together, Lepton, Replicate, Tavily, Serper, Exa, Brave Search, Perplexity API, ElevenLabs, Stability, fal.ai, Runway, LangSmith, Langfuse

**Keys exposed in this session (ROTATE):**
Mistral, Zhipu (Z.ai), HuggingFace — visible in XLSX read output

### 6.7 KAIZEN → Athanor Migration

The original KAIZEN vision (Jan 2026) had elements worth preserving:
- **30 environments** in 6 tiers — most are not yet implemented
- **GWT cognitive architecture** (Global Workspace Theory) — sound design, maps to LangGraph orchestration
- **Three-tier processing** (Reactive <100ms, Tactical 100ms-5s, Deliberative 5s-5min) — good framework for model routing
- **Voice pipeline** — ✅ PARTIALLY ALREADY DEPLOYED:
  - `speaches` on FOUNDRY:8200 = Kokoro-82M v1.0 ONNX TTS, 54 voices, OpenAI-compatible API, CUDA
  - `wyoming-whisper` on FOUNDRY:10300 = Whisper STT (Wyoming protocol for HA)
  - Missing: Silero VAD (speech detection), LLM intent routing, end-to-end integration

**Elements verified from KAIZEN docs (read March 18):**
- Original cluster was 6 nodes: INTERFACE (5090+4090), CORE (EPYC+4×5070Ti), VAULT (TR7960X), DEV, DESK, DECK (Steam Deck)
- INTERFACE and CORE merged into FOUNDRY (EPYC+GPUs) and WORKSHOP (TR7960X+5090) — hardware consolidated
- KAIZEN specified SGLang v0.4, ik_llama.cpp, LangGraph+PostgreSQL, Qdrant, Letta memory, voice pipeline
- 30 environments in 6 tiers: Foundation (inference/memory/cognitive/voice) → Daily (HERS/home/media/comms/knowledge/gaming/legal) → Projects (EoBQ/PROMETHEUS/Kindred) → Intelligence (research/feeds/arXiv) → Optimization (fine-tuning/sleep-compute/Stash) → Sovereignty (self-improvement)

**Obsolete:**
- SGLang as primary → vLLM (deployed, working)
- Talos Linux → Ubuntu + Docker (deployed)
- Qwen3 → Qwen3.5 (deployed)
- 6 nodes → 4 active (DECK shelved)
- Letta/MemGPT → custom 6-tier memory (deployed on DEV:8720)
- EAGLE-3 → native MTP (invalidated by Qwen3.5 architecture)
- 138GB VRAM → 120.5GB + 12GB DESK (RTX 3060 on DESK, not in compute cluster)

**Still valuable (verified by reading all 10 KAIZEN docs):**
1. **Voice Pipeline was PRIMARY interaction mode** — never built. Silero→Whisper→LLM→TTS ~580ms. Core to vision, not nice-to-have.
2. **Self-editable Core Memory** — agents modify own persona/user blocks in real-time. More dynamic than current static prompts.
3. **Three-tier Processing** — Reactive <100ms (cache/regex) → Tactical 100ms-5s (local LLM) → Deliberative 5s-5min (Opus). Formalize in routing.
4. **Home Assistant** — Tier 1 critical. ✅ VERIFIED WORKING. HA deployed on VAULT:8123 (200 OK). home-agent has 8 tools + URL + long-lived JWT token configured in athanor-agents container. Integration is LIVE.
5. **GWT Workspace Competition** — modules bid for tasks based on confidence. Future governor evolution.
6. **Sleep-time Precomputation** — beyond consolidation, proactively cache likely responses (e.g., pre-run morning health check).
7. **Only 10-12 of 30 environments matter** — Focus: Inference, Memory, Cognitive, Voice, HERS, Home, Media, EoBQ, Software Dev, Stash, Monitoring, Dashboard. Rest is scope creep.
8. **ik_llama.cpp** → potential for Qwen3.5-397B with CPU expert offloading on FOUNDRY 219GB RAM

---

## Phase 7: Implementation Priorities

### Execution Order (Solo Developer UX Perspective — what improves daily life most)

**THE FIVE THAT MATTER MOST (Day 1):**

| # | Fix | Effort | Daily Impact |
|---|-----|--------|-------------|
| 1 | LiteLLM 24-min failover → 15s (stream_timeout + num_retries + model_info + fix coding/vision routes) | 1 hr | **Eliminates 24-min hangs** whenever local model hiccups |
| 2 | Fix auto_gen LLM endpoint + clean drops + rebuild venv | 30 min | **Restores image generation** (11 days dead) |
| 3 | Fix Langfuse API keys on LiteLLM container | 5 min | **Restores observability** — see every LLM call across cluster |
| 4 | Fix agent Qdrant URL (FOUNDRY→VAULT) + increase coding-agent timeout | 10 min | **Fixes 16% agent success rate** (wrong knowledge DB + timeouts) |
| 5 | rsync WORKSHOP models to local NVMe | 15 min | **14x faster model loading** (26s→1.9s), removes VAULT dependency |

After these 5 fixes (~2 hours total), the cluster goes from "mostly broken" to "working baseline."

**Rollback plan for each fix:**
1. LiteLLM config: backup current config.yaml before editing. Rollback = restore backup. LiteLLM can be restarted without affecting vLLM containers.
2. Auto_gen: changes are to .env and auto_gen.py. Rollback = revert file changes, restart gateway service.
3. Langfuse keys: adding env vars only. Rollback = remove vars, restart LiteLLM container.
4. Qdrant URL: single env var change on athanor-agents container. Rollback = set back to old URL.
5. rsync: additive only (copies files, doesn't delete source). Rollback = update docker mount back to NFS path.
**None of these changes are destructive.** All are additive or config-only. Worst case = restart the container with old config.

**Verification commands for each fix:**
```bash
# Fix 1: LiteLLM failover — verify stream_timeout works
curl -s -w "\nTime: %{time_total}s\n" http://192.168.1.203:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d" \
  -H "Content-Type: application/json" \
  -d '{"model":"reasoning","messages":[{"role":"user","content":"hi"}],"stream":true}' | head -5
# Should get first token within 10s or fail fast (not 24 min)

# Fix 1b: Verify coding route goes to coder (8006), not coordinator (8000)
curl -s http://192.168.1.203:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d" \
  -d '{"model":"coding","messages":[{"role":"user","content":"hi"}]}' 2>&1 | grep -o '"model":"[^"]*"'
# Should return qwen35-coder, not Qwen3.5-27B-FP8

# Fix 2: Auto_gen — verify images start generating
ssh dev "tail -5 /var/log/local-system/gateway.log | grep -i 'generation\|prompt\|comfyui'"
# Should show successful LLM prompt gen + ComfyUI dispatch

# Fix 3: Langfuse — verify traces resuming
curl -s http://192.168.1.203:3030/api/public/traces?limit=1 \
  -H "Authorization: Basic $(echo -n 'pk-lf-athanor:sk-lf-athanor' | base64)" | head -3
# Should show new traces with timestamps after fix was applied

# Fix 4: Agent Qdrant — verify correct endpoint
ssh foundry "docker exec athanor-agents env | grep QDRANT"
# Should show http://192.168.1.203:6333 (VAULT), NOT 192.168.1.244

# Fix 5: WORKSHOP NVMe — verify local model load
ssh workshop "ls /mnt/fast1/models/Qwen3.5-35B-A3B-AWQ-4bit/ | head -3"
# Should list model files
ssh workshop "docker inspect vllm-node2 --format '{{range .Mounts}}{{.Source}}{{end}}'"
# Should show /mnt/fast1/models, NOT /mnt/vault/models
```

**THEN (Days 2-3):**

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 6 | Security: encrypt credentials, rotate exposed API keys, evaluate Docker socket proxy | 30 min | Security hygiene |
| 7 | MCP Tool Search: auto:5 → true, remove orphaned permissions | 5 min | Reliable tool discovery |
| 8 | Add --swap-space 16 to vllm-coder and vllm-node2 | 10 min | Prevents preemption under load |
| 9 | Enable vision on coordinator (remove --language-model-only) | 30 min | Unlocks image analysis without new GPU |
| 10 | Install Roo Code on DEV with 9-mode config | 30 min | Model-agnostic IDE routing |
| 11 | Update Aider config (Qwen3→3.5 model names) | 10 min | Fix broken Aider routing |
| 12 | Enable Agent Teams env var | 2 min | 7 parallel Opus agents available |
| 13 | Update CLAUDE.md + delegate skill with routing matrix + locked decisions | 1 hr | Governor knows all available tools |

**THEN (Week 1-2):**

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 14 | Stop Crucible containers (deprecated, 5% success) | 5 min | Free resources on FOUNDRY |
| 15 | Stop old Qdrant on FOUNDRY (after agent URL fix verified) | 5 min | Eliminate confusion |
| 16 | Remove vllm-node2 from WORKSHOP, dedicate 5090 to creative | 1 hr | GPU properly allocated |
| 17 | Bash health check script + systemd timer | 1 hr | Free monitoring, ntfy alerts |
| 18 | Enriched session start hook | 1 hr | See cluster health on every session start |
| 19 | Mount FOUNDRY unmounted NVMe | 10 min | Free 932GB fast storage |
| 20 | Rewrite MEMORY.md (correct all inaccuracies) | 1 hr | Accurate system documentation |

**THEN (Week 2-4):**

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 21 | APScheduler in agent server | 4-8 hrs | Autonomous agent scheduling |
| 22 | Deploy Aesthetic Predictor V2.5 on 5060Ti | 2-4 hrs | Auto image quality scoring |
| 23 | Performer data merge (openpyxl script) | 4-8 hrs | Richer gen pipeline |
| 24 | Deploy JOSIEFIED-Qwen3-8B on 5060Ti | 2-4 hrs | Uncensored creative model |
| 25 | Autonomous routing classifier (Semantic Router) | 2-4 hrs | Agent routing without LLM cost |
| 26 | Install remaining tools (Kimi CLI, Qwen CLI, Compound Engineering, Deep Trilogy) | 1 hr | Full tool ecosystem |
| 27 | ~~Activate claude-squad~~ **DECIDED AGAINST** per dev-environment.md — Agent Teams replaces it | — | Use Agent Teams instead |
| 28 | LTX 2.3 video gen setup on 5090 | 4-8 hrs | Video generation capability |

**THEN (Month 2+, Evaluate):**

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 29 | Dia 1.6B TTS deployment | 2-4 hrs | Voice synthesis |
| 30 | Custom MLP scorer training (rate 1000 images first) | 8-16 hrs | NSFW-fair quality scoring |
| 31 | Hindsight agent memory evaluation | 4-8 hrs | Potential memory system improvement |
| 32 | LiteLLM upgrade v1.81.9 → v1.82.x | 2 hrs | 116 new models, bug fixes |
| 33 | 5 undeployed agents (Evaluator, Fact-checker, Voice, HERS, EoBQ) | 20-40 hrs | Full 14-agent architecture |
| 34 | ik_llama.cpp + Qwen3.5-397B evaluation | 8-16 hrs | Frontier model locally |
| 35 | FOUNDRY Channel H DDR4 purchase ($50-80) | 1 hr | 256GB + full 8-ch bandwidth |
| 36 | Coolify deployment on DEV | 4-8 hrs | Self-hosted deploy platform |
| 37 | Intelligence stack (Inoreader, Readwise, Snipd) | 4-8 hrs | AI-filtered information intake |
| 38 | Devstral Small 2 evaluation as coder replacement | 4-8 hrs | Potentially stronger coding |
| 42 | NVIDIA Nemotron 3 Super (120B/12B active MoE, Mar 11) | Evaluate | Multi-agent optimized, could be powerful local agent brain |
| 43 | Gemini Embedding 2 (multimodal, Mar 15) | Evaluate | Unified text+image+video embedding — possible embedding upgrade |
| 39 | Account B setup (when rate limits consistently block work) | 2 hrs | Double Claude capacity |
| 40 | Voice pipeline end-to-end (Whisper + intent + TTS) | 8-16 hrs | Hands-free cluster interaction |
| 41 | Full EoBQ game pipeline (character LoRAs + LTX video + Dia dialogue) | 40+ hrs | Complete creative pipeline |

---

## Verification Strategy

After each phase, verify:

**Phase 0:** MCP Tool Search active (check token count), LiteLLM routes to local models correctly, credentials moved.

**Phase 1:** SSH to each node, confirm correct models loaded, run inference test through LiteLLM, confirm fallback chains work (stop local model, verify cloud fallback triggers).

**Phase 2:** Health check script runs on schedule, ntfy alerts fire on simulated failure, enriched session start shows live data.

**Phase 3:** Aesthetic Predictor V2.5 scores test images (check scores are not NSFW-biased), performers.json has physical data merged (waist/hip/career — NOT TOSI scores), 5090 dedicated to creative generation.

**Phase 4:** LTX 2.3 generates 720p/4s video on 5090, upscale to 1080p works, Dia generates dialogue audio.

**Phase 5:** Subscription utilization plan in effect — each service's resetting limits being actively consumed.

---

## Critical Files

| File | Location | Purpose |
|------|----------|---------|
| `.mcp.json` | DEV: `~/repos/athanor/`, DESK: `C:\Users\Shaun\dev\athanor-next\` | MCP server config |
| `settings.json` | DEV: `~/.claude/settings.json`, project-level | Claude Code settings |
| `config.yaml` | VAULT: LiteLLM config | Model routing |
| `docker-compose.yml` | FOUNDRY/WORKSHOP: vLLM containers | Model serving |
| `performers.json` | VAULT: `/mnt/vault/data/performers.json` | Performer database |
| `cluster-health.sh` | DEV: `~/bin/` or systemd | Health monitoring |
| MEMORY.md | DESK: `C:\Users\Shaun\.claude\projects\C--\memory\` | Session memory (needs update after implementation) |

## Prior Implementation (SAAE) Analysis

The prior "Sovereign Autonomous Agent Engine" (50+ Python/shell/JSON files in Triage) was early prototype stage. 12 of 32 code files were empty stubs, only 1 (`auto_label_advanced.py`) was near-production quality.

**Reusable patterns to incorporate:**
1. **Two-tier classification** (`auto_label_advanced.py`, 294 lines): Fast rule-based scoring with confidence threshold → LLM fallback. Apply to: auto_gen theme selection, Perception document categorization.
2. **Meta-reflection feedback loop** (`meta_reflection_engine.py`): Run → assess → generate improvement suggestion → persist. Apply to: agent trust system enhancement, auto_gen quality feedback.
3. **4-role agent taxonomy** (Planner/Executor/Refiner/Meta): Maps cleanly to current 9-agent system. Use for meta-routing decisions.
4. **Performer physical data** (`enhanced_ultimate_master_data.json`, 783 performers): Unique rare content tracking and deletion context not in current performers.json. Merge during Phase 6. NOTE: TOSI score from this data is deprecated — import physical attributes and rare content data only.

**Discarded patterns (superseded by current stack):**
- File-based state machines (YAML status files, trigger registries) → use Redis/PostgreSQL
- Shell-script LLM orchestration (Gemini CLI piping, input_bus.txt polling) → use LiteLLM
- SOVEREIGN_SYSTEM scaffold (empty YAML frontmatter files) → use actual code
- subprocess.run with shell=True → use SSH-based remote execution
- Markdown-file knowledge persistence → use 6-tier memory system

---

## Files Read & Unread

### Unread (discovered during audit, may contain unique content)
- `Empire/` folder (11 files): EoBQ game design docs — master blueprint, storytelling doc, deep throat mechanics, implant physics, 19-trait DNA system doc, gap analysis, tools audit. **Should read before building EoBQ agent.**
- `Empire/Performer Data - Ultimate_Bimbo_Performer_Database_Complete.xlsx` — may have additional performer data not in main sheets
- `Empire/Sovereign_Task_Tracker_Cycle_8.xlsx` — task tracking history
- `Empire/movies.xlsx` — movie reference data
- `Empire/Models_Sites _ Account Information.xlsx` — site credentials (SECURITY: may contain plaintext passwords)
- `files (14)/` KAIZEN docs (10 .docx): quickstart, cognitive, memory, voice, build, roadmap, environments, inference, models, index — **original KAIZEN architecture docs**
- `Need to be organized/` zip — unknown contents, likely performer dossiers + agent design docs
- `master_data_capture_folder_structure/` — 30+ screenshots of data organization structure

### Files Read (all processed)

- `AI Coding System Research & Architecture.docx` — READ. 48K chars, 6 parts, 85 citations. Master research/architecture doc. Key unique content: 1Gbps DEV bottleneck analysis (DOCX said 1Gbps, user said 10GbE, SSH measurement shows **5GbE** — partially corrected), $91.42/mo subscription savings calc, Best-of-N with ModeX, context compression "Focus" agent, NVMe partitioning strategy.
- `AI_Subscriptions_and_API_Keys_Master (2).xlsx` — READ. 4 sheets: Subscriptions (10 paid, 35+ free tools), API Keys (32 entries, 20 in "Verify" status), Local Models (inventory with priorities), MCP & Integrations (plugins, marketplaces, skills). **Note: Several API keys exposed in plaintext during reading — Mistral, Zhipu, HuggingFace keys should be rotated.**

## Coding Tool Stack (DEFINITIVE — research-proven for non-coder operator)

### CORRECTED VISION: One governor orchestrating ALL tools, not "just use 3."
The system's purpose is to LEVERAGE every subscription, every local model, and every GPU through intelligent routing. You talk to ONE interface. It delegates to the right tool for each task. Every subscription gets used to its resetting limits. Every GPU stays utilized.

### CORE (daily use)
| Tool | Version | Purpose | Why Essential |
|------|---------|---------|--------------|
| **Claude Code CLI** | v2.1.76 | 80% of all work | Best reasoning (Opus 4.6), Agent Teams for parallelism, headless for overnight (78% success), spec-driven dev via CLAUDE.md |
| **GSD** | npm | Context rot prevention | Spawns fresh sub-agents per task. Non-coder won't notice hallucination from context bloat — GSD prevents it structurally. |
| **CodeRabbit** | GitHub app | Automated PR review | Non-coder can't review code. 82% bug detection. Free for open source. Plain English PR summaries. |

### SITUATIONAL (keep installed)
| Tool | Version | Purpose | When to Use |
|------|---------|---------|------------|
| Codex CLI | 0.114.0 | Second opinion | When Claude loops on a specific problem |
| Gemini CLI | 0.33.1 | Free bulk queries | Quick questions, 1M context, 1000 free/day |
| Greywall | npm | Kernel sandbox | When running --dangerously-skip-permissions |

### ALL TOOLS SERVE A PURPOSE IN THE ORCHESTRATED SYSTEM
| Tool | Role in Orchestrated System | When Governor Routes Here |
|------|---------------------------|--------------------------|
| **Claude Code** (Opus) | Complex architecture, multi-file reasoning, primary interactive | Design, planning, novel problems |
| **Codex CLI** (GPT-5.4) | Terminal workflows, computer-use, debugging | Terminal-heavy tasks, OS-level automation |
| **Kimi CLI** (K2.5) | Agent Swarm — 100 parallel sub-agents | Massive breadth research, bulk analysis |
| **Gemini CLI** | 1M context, free 1000/day, web search | Quick questions, long doc ingestion, research |
| **Z.ai GLM** | Fact-checking (#1 Omniscience), fast classification | Verification tasks, routing classification |
| **Aider** (local models) | Structured architect/editor coding at $0 | Bulk file editing, refactoring, test writing |
| **Goose** (local models) | Repeatable recipes via MCP | Infrastructure tasks, deployment patterns |
| **OpenCode** (any provider) | 75+ providers, overflow routing | When primary subs hit limits |
| **Local Qwen3.5** (LiteLLM) | Unlimited inference at $0 | ALL background agent work, uncensored content |
| **JOSIEFIED** (local) | Abliterated uncensored | EoBQ dialogue, NSFW content, pen testing |
| **ComfyUI** (local GPUs) | Image + video generation | Creative pipeline, auto_gen |

**NO TOOLS ARE CUT.** Each serves a purpose in the orchestrated system. The governor routes work to maximize utilization of every subscription's resetting limits and every GPU's compute capacity.

### OVERNIGHT AUTONOMOUS PATTERN
```bash
# In tmux before bed:
claude -p "$(cat task-spec.md)" \
  --dangerously-skip-permissions \
  --model opus \
  --max-turns 50 \
  2>&1 | tee session-$(date +%s).log
```
+ GSD prevents context rot (quality degrades at 50%+ context)
+ CodeRabbit auto-reviews resulting PRs
+ Greywall sandboxes dangerous operations

### THE NON-CODER'S CORE SKILL
**Context engineering via CLAUDE.md is the skill to develop.** Not learning diffs, not understanding git internals. Writing good specs and project memory IS the job. Each of the ~20 repos gets a CLAUDE.md with conventions and SKILL.md files for recurring tasks.

### Previously documented tools (still installed on DEV)
| Tool | Version | Config | Status |
|------|---------|--------|--------|
| Claude Code | v2.1.76 | ~/.claude/ + ~/repos/athanor/.claude/ | Primary, working |
| Aider | 0.86.2 (pipx) | ~/.aider.conf.yml | Installed, deprioritized |
| Goose | 1.27.2 | ~/.config/goose/ | Installed, deprioritized |
| Gemini CLI | 0.33.1 (npm) | ~/.gemini/ | Situational |
| Codex CLI | 0.114.0 (npm) | ~/.codex/ | Situational |
| claude-squad | binary | ~/.claude-squad/ | Multi-CLI (NEVER USED — 0 instances) |
| Mistral Vibe CLI | installed | — | Mistral free |

### NOT Installed (install in Phase 1)
Roo Code (9-mode routing) | Kimi Code CLI | Qwen Code CLI | OpenCode | recall | Claude-Mem | Promptfoo

### Roo Code 9-Mode Config (when installed)
Architect=Gemini 3.1 Pro | Code=qwen3.5-35b (LiteLLM) | Debug=qwen3.5-9b (LiteLLM)
Ask=kimi-k2.5 | Review=codestral (free) | Orchestrator=qwen3.5-27b (LiteLLM)
Heavy=Claude Sonnet 4.6 | EBQ=josiefied-qwen3-8b (local) | Research=Gemini 3.1 Pro

### Claude Code Plugins (on DEV)
Installed: Superpowers, code-review, feature-dev, hookify, security-monitor, playwright, frontend-design, commit-commands, context7
Install: Compound Engineering (29 agents), Deep Trilogy (TDD+adversarial)
Evaluate: Everything Claude Code, claude-task-master

### Daily Workflow Waterfall
1. Claude Code (Opus) — complex architecture, design, multi-file reasoning
2. Claude Code → LiteLLM → local Qwen3.5 — bulk coding, boilerplate ($0)
3. Gemini CLI — research, 1M context, 1000 free/day
4. Codex CLI — terminal workflows, GPT-5.4
5. Aider — structured architect/editor coding via LiteLLM ($0)
6. Goose — MCP-native tasks, recipes via LiteLLM ($0)
7. claude-squad — parallel sessions when needed

### Techniques for Local Models
- Best-of-N: 16-32 variations, ModeX spectral clustering (no reward model needed)
- Context compression: local 30B compresses 50K→2K for cloud injection (22.7% savings)
- Afterburner loops: generate→sandbox→capture error→refine (hundreds at $0)
- Living specification: immutable spec.md before dispatching workers
- Iterative refinement: 2-4 iterations achieve most gains

### DEV as Dedicated Development Machine (Full Stack)

**Hardware:** Ryzen 9 9900X 12C/24T, 60GB RAM (51GB available), RTX 5060Ti 16GB (11.5GB available), **5GbE** (NOT 10GbE — measured 5000 Mbps via sysfs, likely Realtek RTL8126 onboard)
**NVMe:** 5.5TB total — 932GB Crucial T700 OS (/), 3.4TB Crucial P3 Plus empty (/data), 932GB Samsung 970 EVO Plus Docker (/var/lib/docker)

**NVMe Partitioning Strategy (from research):**
- `/data/worktrees/` — Isolated git worktrees for parallel agent compilation (prevents namespace collisions, file locking)
- `/data/models/` — Local model weight cache (fast staging for testing new models)
- `/data/rag-cache/` — Local Qdrant vector cache for active workspace (eliminates network round-trips)
- `/data/sandbox/` — Rapid Docker container creation/destruction for iterative refinement loops

**Running Services (systemd):**
- local-system-gateway:8700 (active)
- local-system-mind:8710 (active)
- local-system-memory:8720 (active)
- local-system-perception:8730 (active)
- local-system-ui:3001 (**CRASH LOOPING** — needs fix)
- vllm-embedding:8001 (Qwen3-Embedding-0.6B)
- vllm-reranker:8003 (Qwen3-Reranker-0.6B)
- athanor-heartbeat daemon
- Gitea Actions Runner

**tmux Sessions:**
- `ATHANOR` (2 windows: claude + shell) — primary, launched by ~/bin/athanor
- `happy` (1 window) — secondary

**Launcher Script (~/bin/athanor):**
Creates/attaches ATHANOR tmux session with `claude` (auto-launches Claude Code in ~/repos/athanor) + `shell` windows.

**Repos (/home/shaun/repos/):**
- `athanor/` — Main monorepo (git, ansible, projects, services, scripts, .claude/)
- `quarantine/` — Contains old `athanor/` and `Local-System/` (quarantined, auto_gen code lives here)
- `reference/hydra/` — Reference codebase for porting modules (Goose recipe uses this)
- `reference/kaizen/` — Original KAIZEN architecture docs
- `reference/local-system/` — Local-System v4 reference code
- `reference/system-bible/` — System documentation reference

**Formal Architecture Docs (on DEV at ~/repos/athanor/docs/):**
- `design/` — 22 design documents including: agent-contracts, athanor-next, audio-gen pipeline, command-center, command-hierarchy, dashboard-interactions, HA integration, hybrid-dev, intelligence-layers, LoRA training pipeline, model-swap-protocol, personal-data architecture, project-platform, stash-agent workflow, system-constitution, tdarr deployment, VAULT storage, VPN torrent stack, VRAM workload profiles
- `decisions/` — 10+ ADRs: ADR-001 (base platform) through ADR-010 (home automation), covering inference engine, agent framework, network, storage, creative pipeline, dashboard, monitoring
- `architecture/` — complete-context-raw.md
- These are the FORMAL architectural decisions. This plan should NOT contradict them without explicit justification.

**Claude Code Router (CCR) — ALREADY INSTALLED:**
Alias `ccc`. Routes to different providers when Max quota exhausted. Config at `~/.claude-code-router/config.json`. This IS the governor routing for interactive overflow — already working.

**OpenCode — ALREADY INSTALLED (missed in audit):**
Aliases `oc`, `opencode-glm()`, `opencode-or()`. 75+ providers, LSP, multi-session. Working on DEV.

**Agent Teams — ALREADY ENABLED:**
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set in Claude Code config. Ready to use.

**Shell aliases on DEV:** `cc` (Claude Code), `ccc` (CCR), `gc` (Gemini CLI), `oc` (OpenCode), `aider-glm()`, `aider-or()`, `opencode-glm()`, `opencode-or()`

**Tools DECIDED AGAINST (per dev-environment.md, do NOT install):**
claude-squad (Agent Teams replaces), Kilo Code (redundant with Roo), Kiro (separate IDE), Amp (cloud-locked), Amazon Q (AWS lock-in), CrewAI/AutoGen (own frameworks), Droid/Copilot CLI/1Code/OhMyOpenCode

**Tools BOOKMARKED for later (from dev-environment.md):**
- **OpenClaw**: Always-on interface (WhatsApp/Discord/Slack/Telegram/Signal/iMessage) → routes to agents
- **Cipher**: Cross-tool memory layer (MCP, dual memory System1+System2, Ollama+Neo4j)
- **Plandex**: 2M token context, for tasks touching 50+ files
- **Deep Trilogy**: When starting major new components

**Goose recipes to fix:**
- `test-all-endpoints.yaml` references dead FOUNDRY:8002 (Huihui-Qwen3-8B) — update to current endpoints
- `port-hydra-module.yaml` works if hydra reference repo is current

**Python:** System Python 3.12.3, tools via pipx (aider-chat 0.86.2, ansible-core 2.20.3)
**Node:** v24.14.0 (system, no nvm)
**Go binaries:** claude-squad (4.5MB standalone), goose (243MB)

**Claude Code Setup on DEV:**
- Global settings: opus[1m], telemetry disabled, tool search enabled, all permissions allowed
- Project settings: 13 MCP permissions whitelisted (11 orphaned), autocompact 80%, bash timeout 180s
- 6 custom agents, 18 skills, 11 commands, 13 rules, 15 hooks
- 2 MCP servers: docker + athanor-agents
- launch.json: dashboard:3000, agents:9000

**Tools Installed & Configured:**
| Tool | Version | Config | Status |
|------|---------|--------|--------|
| Claude Code | v2.1.76 | ~/.claude/ + project .claude/ | Primary, working |
| Aider | 0.86.2 (pipx) | ~/.aider.conf.yml | Working — **needs model name update** Qwen3→3.5 |
| Goose | 1.27.2 (Go binary) | ~/.config/goose/ | Working — LiteLLM + Anthropic profiles, 2 custom recipes |
| Gemini CLI | 0.33.1 (npm) | ~/.gemini/ | Working |
| Codex CLI | 0.114.0 (npm) | ~/.codex/ | Working |
| claude-squad | binary | ~/.claude-squad/ | Installed, **NEVER USED** (0 instances) |
| Mistral Vibe CLI | installed | — | Working |

**Tools NOT Installed (Phase 1 installs):**
| Tool | Priority | Install Method | Purpose |
|------|----------|---------------|---------|
| Roo Code | HIGH | VS Code extension | 9-mode model routing |
| Kimi Code CLI | MEDIUM | uv (Python installer) | Agent Swarm, visual-to-code. Also: `kimi-code-mcp` npm package wraps as MCP server with 14 tools |
| Qwen Code CLI | MEDIUM | npm | DashScope free quota |
| OpenCode | LOW | Go binary or npm | Evaluate as terminal overflow |
| recall | LOW | npm | Search across all AI conversations |
| Claude-Mem | LOW | pip | Session memory → SQLite + Chroma |
| Promptfoo | LOW | npm | Offline model A/B testing |
| Coolify | MEDIUM | Docker | Self-hosted deploy platform (locked decision #4) |

**DEV Environment Issues to Fix:**
- local-system-ui.service: CRASH LOOPING (auto-restart, never reaching running)
- Aider config COMMENTS reference old model names (Qwen3-32B-AWQ) but the actual LiteLLM aliases (`reasoning`, `coder`, `fast`) already route to the correct Qwen3.5 models. Fix = update comments only, routing is correct.
- claude-squad installed but **DECIDED AGAINST** per dev-environment.md (Agent Teams replaces it)
- Coolify not installed (locked architectural decision #4 — deploy when ready)
- 11 orphaned MCP permissions for non-existent servers (remove from project settings)
- MCP Tool Search set to auto:5 (buggy) → change to true

### WORKSHOP Application Containers (running, not in MEMORY.md)

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| athanor-dashboard | athanor/dashboard:latest | :3001 | Main Athanor web dashboard |
| athanor-eoq | athanor/eoq:latest | :3002 | Empire of Broken Queens game/tool |
| athanor-ulrich-energy | athanor/ulrich-energy:latest | :3003 | Ulrich Energy HERS business app |
| athanor-ws-pty-bridge | athanor/ws-pty-bridge:latest | :3100 | WebSocket terminal bridge |
| open-webui | open-webui:main | :3000 | Chat UI for local models (OpenAI-compatible) |
| comfyui | athanor/comfyui:blackwell | :8188 | Image/video generation |

**Notes:**
- These are custom-built apps (athanor/* images) that represent active projects
- open-webui provides a chat interface to local models — useful for non-CLI interaction
- ws-pty-bridge enables web-based terminal access to the cluster
- ComfyUI image is custom Blackwell build (athanor/comfyui:blackwell) with CUDA 12.8 support
- All consume minimal RAM (<200MB each) except ComfyUI which holds model weights

### DESK as Local Workstation (Windows, currently just SSH terminal)

**Hardware:** i7-13700K 16C/24T, 64GB DDR5-4800, RTX 3060 12GB, 2TB P310 + 1TB T700, 10GbE (Hyper-V vSwitch)

**Current use:** SSH terminal to DEV via tmux. No local AI workloads.

**Potential use (Phase 5 evaluate):**
- **Qwen3.5-4B on RTX 3060** (~8GB Q8) — local autocomplete, commit messages, quick questions without hitting DEV
- **Codestral autocomplete** via Mistral extension (already free, no VRAM needed for API-based)
- **Ollama for lightweight local models** — 3060 handles 7B-14B models at 25-37 tok/s
- **Local embedding for VS Code extensions** — Cline, Roo Code, Continue can route to local Ollama
- **Development preview server** — 64GB RAM + fast NVMe for running full-stack apps locally while AI runs on cluster
- **Note:** Primary development MUST stay on DEV (per locked decision). DESK is supplementary.

### Network Topology (verified via ethtool/sysfs)

| Node | Interface | Speed | Notes |
|------|-----------|-------|-------|
| FOUNDRY | enp66s0f0 | 10 Gbps | Primary, UP |
| FOUNDRY | enp66s0f1 | 10 Gbps | Secondary, UP (not bonded) |
| WORKSHOP | eno1 | 10 Gbps | Primary, UP |
| DEV | enp14s0 | **5 Gbps** | Onboard (user claimed 10GbE — verify if 10GbE NIC available) |
| VAULT | bond0 | 10 Gbps | Active-backup: eth0 (10GbE primary) + eth1 (2.5GbE backup) |
| DESK | vEthernet | 10 Gbps | Hyper-V vSwitch over physical 10GbE NIC |

**Network Equipment:** Ubiquiti UDM Pro + USW switches (10GbE backbone)
- **UDM Pro built-in VPN:** WireGuard VPN server (native, no additional software needed)
- **WiFiman:** Ubiquiti's network monitoring/management app
- **Remote access options:** UDM Pro WireGuard > Tailscale > OpenVPN. WireGuard is kernel-native, lowest latency, built into the UDM Pro — may eliminate need for Tailscale on the NETWORK level (though Tailscale still useful for device-level mesh + MagicDNS on phone)
- **VLAN capability:** UDM Pro supports VLANs for network segmentation (IoT devices, guest network, inference traffic isolation)

**Single Point of Failure: VAULT (47 containers)**
If VAULT goes down, the cluster loses: LiteLLM (routing), PostgreSQL (agent state), Redis (cache), Qdrant (vectors), Neo4j (knowledge graph), Langfuse (observability), Prometheus/Grafana (monitoring), ntfy (alerts), Stash (media), all *arr services, Tdarr (transcoding).
**Mitigation already in plan:**
- rsync models to local NVMe removes NFS dependency for inference
- vLLM on FOUNDRY/WORKSHOP runs independently (no VAULT dependency once models are local)
- Bash health scripts on DEV can detect VAULT outage and alert
- **Prometheus monitoring is comprehensive:** 5 alert groups, 27+ rules covering: backup freshness, 17 service blackbox probes (LiteLLM, vLLM coordinator/coder/worker, agent server, dashboard, ComfyUI, Gitea, Miniflux, n8n, Redis, Postgres, Langfuse, ntfy, Qdrant, Neo4j, GPU orchestrator), GPU temp/memory, CPU/memory/disk
- **Currently firing alerts (March 18):** Qdrant backup 4d old, Neo4j backup 4d old (weekly crons may have failed), 5090 VRAM 99% (expected — vllm-node2)
**Not mitigated (future consideration):**
- LiteLLM fallback: if VAULT:4000 is down, direct vLLM access still works but needs manual endpoint config
- Agent state: PostgresSaver on VAULT — agent runs fail if VAULT PG is down
- Backups exist (PG daily, Neo4j weekly, Qdrant weekly). **RECOVERY.md EXISTS** on DEV with full disaster recovery runbook (RTO 2-4hrs, RPO 24hrs, service recovery order)
- UPS monitoring (NUT) needs USB data cable — if power fails, no graceful shutdown

**Impact of DEV 5GbE:**
- 5 Gbps = ~625 MB/s theoretical, ~500 MB/s practical
- Adequate for: SSH sessions, LiteLLM API calls, embedding requests, file editing
- NOT adequate for: tensor parallelism across nodes (needs 100Gbps+), large model transfers (use rsync overnight)
- DEV is the ops center, not a compute node — 5GbE is sufficient for its role
- FOUNDRY↔WORKSHOP: both 10GbE, can do fast model sync between compute nodes
- NFS from VAULT: currently saturates 10GbE at 873 MB/s — plan fixes this by copying models to local NVMe

### Complete Service Map (verified live March 18, 2026 — 50+ services across 4 nodes)

**FOUNDRY (.244):** vllm-coordinator:8000, vllm-coder:8006, speaches(Kokoro TTS):8200, athanor-agents:9000, gpu-orchestrator:9200, dcgm:9400, wyoming-whisper:10300, qdrant(OLD):6333, docker-proxy:2375, alloy:12345, crucible(4 containers, DEPRECATE):8742/8080/8001/11434

**WORKSHOP (.225):** vllm-node2:8000, comfyui:8188, open-webui:3000(→FOUNDRY:8000), dashboard:3001, eoq:3002, ulrich-energy:3003, ws-pty-bridge:3100, dcgm:9400, alloy:12345

**DEV (.189):** embedding:8001, reranker:8003, gateway:8700, mind:8710, memory:8720, perception:8730, ui:3001(CRASH LOOP), node-exporter:9100

**VAULT (.203):** litellm:4000, langfuse:3030, n8n:5678, gitea:3033, stash:9999, homeassistant:8123, miniflux:8070, ntfy:8880, prometheus:9090, grafana:3000, qdrant:6333, neo4j:7687, meilisearch:7700, postgresql:5432, redis:6379, tdarr:8265, cadvisor:9880, node-exporter:9100, plex, sonarr, radarr, prowlarr, sabnzbd, tautulli, overseerr, tdarr-node

### Architecture Flow (how a request moves through the system)

```
SHAUN at DESK
    │
    ├── SSH → DEV tmux "ATHANOR" session
    │         │
    │         ├── Claude Code (Opus 4.6) ← GOVERNOR for interactive work
    │         │     ├── Direct to Anthropic API (Max 20x sub)
    │         │     ├── → LiteLLM (VAULT:4000) → vLLM coordinator (FOUNDRY:8000) [local reasoning]
    │         │     ├── → LiteLLM → vllm-coder (FOUNDRY:8006) [local coding]
    │         │     ├── → athanor-agents MCP → LangGraph (FOUNDRY:9000) [agent dispatch]
    │         │     └── Suggests: "Use Codex CLI for this" / "Aider would be better"
    │         │
    │         ├── Aider (architect/editor via LiteLLM → local)
    │         ├── Gemini CLI (Gemini Advanced sub, 1000 free/day)
    │         ├── Codex CLI (ChatGPT Pro sub)
    │         ├── Goose (LiteLLM → local, Recipes)
    │         ├── claude-squad (parallel sessions in tmux panes)
    │         └── Kimi/Qwen/Mistral CLIs (subscription overflow)
    │
    ├── Browser → claude.ai (same Max 20x sub)
    │         ├── Google Calendar, Gmail, Drive MCP
    │         ├── Perplexity Deep Research (separate sub)
    │         └── Vercel, HuggingFace, Context7 MCP
    │
    └── VS Code (DESK) → Roo Code (9-mode routing via LiteLLM)
              ├── Copilot Pro+ (GPT-5.4/Opus via sub)
              ├── Cline, Tongyi Lingma, Kimi ext, Mistral ext
              └── Optional: local Ollama on 3060 for autocomplete

AUTONOMOUS (no human present):
    LangGraph agents (FOUNDRY:9000)
        ├── APScheduler triggers (every 5min/15min/1hr/etc.)
        ├── Prometheus Alertmanager webhooks
        ├── → LiteLLM → local models only ($0)
        ├── → Semantic Router (DEV:8001 embedding) for routing decisions
        └── PostgresSaver (VAULT) for state persistence
```

---

## Appendix A: Delegate Skill Content (for .claude/skills/delegate/SKILL.md)

```markdown
name: delegate
description: Route tasks to the optimal tool based on task type, complexity, and available resources

# Delegation Guide

## When to Delegate (vs doing it yourself)
- Bulk file editing (>10 files) → Aider
- Terminal-heavy debugging → Codex CLI
- Research requiring many sources → Perplexity Deep Research
- Quick factual questions → Gemini CLI (free, saves Opus tokens)
- Parallel independent tasks → claude-squad
- NSFW creative writing → local JOSIEFIED (MUST stay local)
- Background monitoring → LangGraph agents (FOUNDRY:9000)
- Repeatable operations → Goose Recipes

## Routing Matrix
| Task Pattern | Tool | Command |
|---|---|---|
| Bulk refactoring | Aider | `aider --architect --model openai/reasoning --editor-model openai/coder` |
| Terminal workflow | Codex CLI | `codex` (ChatGPT Pro) |
| Deep research | Perplexity | Browser → perplexity.ai/pro |
| Quick question | Gemini CLI | `gemini "question"` |
| Parallel tasks | claude-squad | `claude-squad` (manages tmux panes) |
| NSFW dialogue | JOSIEFIED | Via athanor-agents MCP → EoBQ agent |
| Health check | LangGraph | Via athanor-agents MCP → general-assistant |
| Code review | /code-review | Built-in plugin (5 parallel Sonnet agents) |
| Large feature | Deep Trilogy | /deep-project |
| Structured build | Compound Engineering | /compound |

## Available Local Models (via LiteLLM at VAULT:4000)
- `reasoning` → Qwen3.5-27B-FP8 (FOUNDRY, 72.4% SWE-bench)
- `coder` / `coding` → Qwen3.5-35B-A3B (FOUNDRY 4090)
- `worker` / `creative` → Qwen3.5-35B-A3B (WORKSHOP 5090)
- `vision` → Qwen3.5-27B with VLM (FOUNDRY, after --language-model-only removed)
- `embedding` → Qwen3-Embedding-0.6B (DEV:8001)

## Subscription CLIs (all on DEV, flat-rate)
- Claude Code (this tool) — $200/mo Max, Opus 4.6
- Gemini CLI — $20/mo, 1000 free/day
- Codex CLI — $200/mo ChatGPT Pro
- Kimi Code CLI — $19/mo Allegretto, Agent Swarm
- Qwen Code CLI — $10/mo DashScope
```

## Appendix B: CLAUDE.md Additions (for project CLAUDE.md on DEV)

**NOTE:** The existing project CLAUDE.md (50+ lines) is already well-written with COO role, agent hierarchy, work principles, anti-patterns, compaction instructions, and build mode. The additions below should be MERGED into appropriate existing sections, not appended as a separate block. The existing delegate skill (50 lines, coding-only) should be REPLACED with the expanded version from Appendix A.

The following should be added to the project CLAUDE.md at `~/repos/athanor/CLAUDE.md`:

```markdown
## Available Infrastructure
- LiteLLM: VAULT:4000 (key: sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d) — routes to local models
- LangGraph: FOUNDRY:9000 — 9 agents, 77 tools (via athanor-agents MCP)
- GPU Orchestrator: FOUNDRY:9200 — 4 GPU zones, metrics
- Langfuse: VAULT:3030 — LLM observability (139K+ traces)
- Prometheus: VAULT:9090 — cluster metrics
- ntfy: VAULT:8880 — push notifications (topic: athanor)

## Subscription Tools (maximize each, never cut)
Use the /delegate skill to route tasks to the optimal tool.
All subscriptions are sunk cost — use every resetting limit before it resets.

## Model Routing
When doing bulk work, use a separate session pointed at local models:
ANTHROPIC_BASE_URL=http://192.168.1.203:4000 claude

## Hard Rules
- ALL NSFW/EoBQ content generation stays LOCAL — zero cloud APIs
- FOUNDRY is production — never modify without explicit approval
- Check health first: /health command or ssh foundry "nvidia-smi"
```

---

## ADDENDUM A: ATHANOR-SYNTHESIS.md Findings (March 18, 2026)

**Source:** `C:\Users\Shaun\Downloads\ATHANOR-SYNTHESIS.md` (55.7KB) — self-described as "the ONE file" containing 170+ tools, all findings, install commands, configs. Dated March 18, 2026.

### Critical Owner Context (MUST inform all decisions)
**Shaun is a NON-CODER.** He uses AI coding agents exclusively. Agents write ALL code. This means:
- Every tool must be AI-agent-friendly (not requiring manual coding)
- The system must work through natural language commands, not code writing
- Autonomous operation is MORE important than interactive coding features
- Phone access matters — he's at HERS job sites during the day

### 7-Layer Architecture (from synthesis, more precise than plan's current layers)
```
Layer 0 — MODELS/INFERENCE (vLLM, GPUStack on cluster hardware)
Layer 1 — CLI AGENTS (Claude Code, Codex, Kimi, Gemini, Aider, OpenCode)
Layer 2 — IDE EXTENSIONS (Roo Code, Continue.dev, Copilot, Cline)
Layer 3 — PROXY/ROUTER (CCR, LiteLLM → universal API)
Layer 4 — PROJECT FRAMEWORKS (GSD context management, CLAUDE.md, AGENTS.md)
Layer 5 — ORCHESTRATORS (CCManager, Agent Teams, git worktree isolation)
Layer 6 — GOVERNORS (OpenFang daemon, 24/7, phone access, Telegram)
Layer 7 — SKILLS + PROTOCOLS (MCP, A2A, universal skills)
```

### NEW Tools Not In Plan (from synthesis Tier 1 installs)
| Tool | Purpose | Install | Priority |
|------|---------|---------|----------|
| **OpenFang** | 24/7 daemon on VAULT, Telegram adapter, phone dashboard at :4200 | Docker on VAULT | HIGH — phone access from job sites |
| **Tailscale** | Encrypted P2P mesh, MagicDNS (`vault`, `foundry`, `dev`), phone connectivity | All nodes + phone | HIGH — secure remote access |
| **GSD (Get Shit Done)** | Context management, prevents "context rot" in long sessions | `npx get-shit-done-cc --all --global` | HIGH |
| **Greywall** | Security sandbox for coding agents | `npm install -g greywall` | MEDIUM |
| **Tokscale** | Token usage tracking across ALL agents | `bunx tokscale@latest` | MEDIUM |
| **Claude-Code-Usage-Monitor** | Subscription usage monitoring | Python script from GitHub | MEDIUM |
| **GPUStack** | Alternative inference engine (evaluated alongside vLLM) | Docker | Evaluate |
| **Roo Code CLI** | Roo Code runs HEADLESSLY from terminal (not just VS Code) | Node package | HIGH |

### NEW Findings from Synthesis
1. **Anthropic OAuth Crackdown (Jan 9, 2026):** Anthropic BANS third-party OAuth forwarding. Claude Code ONLY works with Anthropic models via Max subscription. Cannot route Claude Code to other providers via OAuth. CCR uses API KEY auth, not OAuth.
2. **Roo Code is the cross-provider answer:** Custom Modes assign different models per role. Architect→GLM-4.7, Code→Kimi K2.5, Debug→fast local. Runs headlessly AND in VS Code.
3. **Phone access via OpenFang + Tailscale + Telegram:** Daemon on VAULT, 4-second typing indicator, dashboard at vault:4200 accessible from phone. Custom "HERS Hand" for business automation from job sites.
4. **GitHub username:** Dirty13itch (private repo: Dirty13itch/Athanor)

### Contradictions with Plan
| Item | Plan says | Synthesis says | Resolution |
|------|-----------|---------------|------------|
| Kimi Code tier | Allegretto | Moderato (300-1200 calls/5hr, 256K context, concurrency 30) | **VERIFY current subscription tier** |
| VAULT RAM | 123GB | 128GB DDR5 | Synthesis may be from specs, plan is from `free -h` (actual) |
| Total VRAM | 120.5GB | 138GB | Synthesis includes DESK 3060 12GB + Arc A380 6GB |
| Roo Code CLI | "NOT INSTALLED" | Runs headlessly from terminal | **Synthesis says Roo Code has a CLI mode — VERIFY** |
| Claude Squad | "Decided Against" | Listed as orchestrator option | Plan's decision is more recent — keep "decided against" |

---

## ADDENDUM B: DEEP-RESEARCH-LIST.md — Complete Goals Inventory

**Source:** `C:\Users\Shaun\Downloads\DEEP-RESEARCH-LIST.md` (488 lines, 14 sections)

### ALL Stated Projects/Goals (extracted from DEEP-RESEARCH-LIST + all prior sessions)

| Project | Domain | Status | Priority |
|---------|--------|--------|----------|
| **Athanor OS** | Core infrastructure | Deployed (6-phase build complete) | P0 — maintain |
| **Empire of Broken Queens** | Adult visual novel (Ren'Py) | Design docs complete, dashboard app running | P1 — build |
| **Ulrich Energy HERS automation** | Business (energy auditing) | App on WORKSHOP:3003, BKI tracker, forecasting | P1 — maintain |
| **Kindred** | Social matching app | Concept only | P3 — future |
| **Media server** | Plex/Sonarr/Radarr/Usenet | Running but incomplete (VPN blocked) | P1 — complete |
| **Home automation** | Home Assistant | Running, agent wired | P2 — expand |
| **Intelligence pipeline** | RSS/signal processing | Miniflux + n8n deployed, not integrated | P2 — integrate |
| **HERS Hand** (OpenFang) | Mobile business assistant | Design exists | P2 — build |
| **Airtight-IQ** | Duct leakage forecasting ML | Concept + data exists | P3 — evaluate |
| **Portfolio/website** | Personal portfolio | Dir exists on DESK | P3 — low priority |
| **Knowledge graph** | Neo4j-based knowledge | 3237 nodes, working | P2 — expand |
| **Stash intelligence** | AI-powered media management | 22.5K scenes, agent running | P2 — enhance |
| **Voice pipeline** | STT → LLM → TTS | 2/4 components deployed (Whisper + Kokoro) | P2 — complete |
| **Creative image pipeline** | Auto_gen with FLUX/PuLID | BROKEN (11 days, fix in Phase 0) | P0 — fix |
| **Video generation** | LTX 2.3 / Wan 2.2 | Not deployed yet | P2 — new |
| **Autonomous coding** | Overnight multi-project dev | Not deployed, architecture designed | P2 — build |
| **Pen testing** | Security research on own infra | SpiderFoot script exists | P3 — evaluate |

### Research Areas from DEEP-RESEARCH-LIST (14 domains)
1. Model Layer (Qwen3.5 variants, abliteration, speculative decoding)
2. Inference Engine (vLLM vs SGLang, prefix caching, Blackwell optimization)
3. Agent Architecture (delegation, GWT, agents-as-tools)
4. Intelligence Pipeline (Miniflux, n8n, signal classification)
5. Development Tooling (Claude Code, CCR, local models, cross-provider)
6. Observability & Evaluation (Langfuse, accelerated eval, A/B testing)
7. Creative Pipeline (EoBQ: SoulForge, face consistency, LoRA training)
8. Infrastructure & Operations (SOAR, overnight operations, backup testing)
9. Home & Media Automation (HA depth, 224TB library, Kindred app)
10. Protocols & Standards (MCP registry, AGENTS.md, Agent File .af)
11. Business & Regulatory (RESNET updates, MN energy code, Airtight-IQ)
12. Knowledge & Memory Architecture (10 novel ideas, compound learning)
13. Security & Sovereignty (prompt injection, data sovereignty, model integrity)
14. Hardware Optimization (loose hardware, thermal, power/UPS)

---

## ADDENDUM C: Downloads Batch 2 Findings (12 files)

### Game-Changing Findings

**1. Open models NOW LEAD closed on function-calling (BFCL-V4):**
GLM-4.5 at 70.85%, Qwen3.5-122B at 72.2% vs GPT-5 at 59.22%. This means the LOCAL orchestrator can be BETTER than cloud for tool-calling/agentic work.

**2. NVIDIA proved an 8B RL-trained orchestrator beats GPT-5 and Opus** while costing 70% less. A small local model trained specifically for orchestration outperforms frontier cloud models. This validates the local orchestrator approach.

**3. Five Intelligence Planes (from prior research):**
- Governor Plane — intent classification, routing, budget enforcement
- Frontier Meta Plane — cloud models for complex reasoning
- Sovereign Meta Plane — local uncensored models for sensitive work
- Worker Plane — execution models for coding, generation
- Judge/Verifier Plane — quality gates, fact-checking, code review

**4. Content & Refusal Governance Matrix (5 task classes):**
Route by data sensitivity BEFORE provider selection:
| Class | Examples | Allowed Providers |
|-------|---------|-------------------|
| PUBLIC | Open-source code, docs | Any (cloud or local) |
| PRIVATE | Business data, personal code | Cloud (trusted subs) or local |
| SENSITIVE | Credentials, financial, medical | Local ONLY |
| NSFW | Adult content, EoBQ, explicit | Local uncensored ONLY |
| ADVERSARIAL | Pen testing, exploit dev | Local uncensored ONLY |

**5. Dual-loop controller** (Magentic-One pattern):
- Task Ledger in Neo4j — tracks goals, dependencies, completion
- Progress Ledger in Redis — tracks real-time execution state
- Both databases already deployed on VAULT

### Technical Findings
- **AWQ strongly preferred over GPTQ** for agentic workloads (better tool-calling reliability)
- **Prefix caching** is the SINGLE most important optimization for agent orchestration throughput
- **MoE models** run 3-5x faster for orchestration's short-burst JSON workloads
- **Quantization floor:** Never go below Q4 for tool-calling reliability
- **Adaptive thinking budgets:** Qwen3 `/think`/`/no_think` (0 to 2048 tokens per request)
- **Champion-challenger model governance:** 8-step promotion path before a model becomes production default

### Undeployed Tools (ready to install)
| Tool | Purpose | Status |
|------|---------|--------|
| SpiderFoot 4.0 | OSINT reconnaissance | Deploy script ready: `setup-spiderfoot-vault.sh`, port 5001 |
| Iris v0.1 | vLLM Semantic Router (Rust) | Production-ready, alternative to Python semantic-router |
| ModernBERT | Semantic routing on 5060Ti | Lighter than CLIP/SigLIP for classification |

### Hydra Reference Repo Assets (on DEV at ~/repos/reference/hydra/)
- **66 MCP tools** — potentially portable to current agent server
- **41 n8n workflows** — intelligence pipeline automation
- **6 Python modules** to evaluate for porting: routellm, preference_learning, self_diagnosis, resource_optimization, knowledge_optimization, capability_expansion

### Data Discrepancy
- **DESK IP:** .215 in some deploy/audit scripts vs .50 in MEMORY.md — NEEDS RECONCILIATION

## ADDENDUM D: Downloads Batch 1 — 10 Critical Files (MAJOR FINDINGS)

### PLAN.md — 23-Subsystem Governance → SIMPLIFIED TO 7 CONCEPTS

**RESEARCH VERDICT (definitive):** 23 subsystems is categorically worse for a solo operator. Evidence from cognitive science (Miller's Law 7±2), management theory (span of control 3-7), Fred Brooks (essential vs accidental complexity), Parkinson's Law, DHH/37signals, YC, and real solo operators (Pieter Levels) ALL converge: **5-7 top-level concepts is optimal.**

**The 7 concepts (replaces 23 subsystems):**
1. **Compute** — GPU allocation, model deployment, inference routing, model evaluation
2. **Storage** — Data lifecycle, backups, media management, NVMe/HDD
3. **Services** — App deployment, health monitoring, agent trust, dependencies
4. **Generation** — Content pipelines, creative workflows, autonomous agents, overnight builds
5. **Operations** — Monitoring, alerting, maintenance, presence-aware automation
6. **Security** — Access control, secrets, content governance routing (5 sensitivity classes), sandboxing
7. **Knowledge** — Memory system, embeddings, RAG, intelligence pipeline, documentation

**The end-state vision (from PLAN3.md — the CLEAREST statement):**
> Give Athanor a goal → it turns that into work → chooses the right local or cloud lane → runs on schedule or on demand → shows what happened in one cockpit → fails visibly, retries safely, lets you override without SSH or guesswork.

**The sovereignty principle (from PLAN 2.md):**
> "Athanor should not depend on cloud permission to function, but it also should not waste frontier capability."

**Valuable PLAN.md ideas preserved AS CONVENTIONS within these 7:**
- Content Governance Matrix (5 classes) → convention inside Security
- Presence Model (at desk/away/asleep/phone) → convention inside Operations
- Champion-Challenger → simplified to test→shadow→promote inside Compute
- Graduated autonomy → convention inside Services (agent trust levels)
- Failure Matrix → Prometheus alert rules inside Operations
- System Constitution → CLAUDE.md on DEV (already exists)

**PLAN.md ideas DROPPED (enterprise patterns for 50-person teams):**
- 13 Workload Class Registry → Semantic Router handles classification
- Model Role Registry → LiteLLM aliases handle this
- Economic Governance → subscriptions are sunk cost
- Data Lifecycle Registry → 6-tier memory already handles this
- 12 normalized internal contracts → over-engineering
- 25-route cockpit → dashboard already has 17 pages

### Game-Changing Technical Findings
- **RTX 5070 Ti FP4 (mxfp4): ❌ DOES NOT WORK AS CLAIMED (verified on actual hardware).** `mxfp4` only quantizes MoE experts, NOT dense layers (TODO in source code). SM120 FP4 kernels produce garbage (CUTLASS bug #3096). NVFP4 works for dense BUT needs pre-quantized checkpoints. Current 27B-FP8 TP=4 is correct. Also: **vLLM is v0.16.1rc1.dev32** (Python package), not v0.13.0 (NVIDIA env var tag).
- **Anthropic OAuth Crackdown (Jan 9, 2026):** Banning accounts using Max sub with third-party OAuth forwarding. Claude Code = Anthropic models ONLY. Critical constraint.
- **Context Rot:** 0-30%=peak, 50%+=cutting corners, 70%+=hallucinations. **Solution: GSD** (`npx get-shit-done-cc --all --global`), 32.2K stars.
- **Greywall:** Claude Code disabled its own sandbox. Kernel-level enforcement REQUIRED for autonomous agents.
- **Open models LEAD closed on function-calling:** BFCL-V4 GLM-4.5 70.85%, Qwen3.5-122B 72.2% vs GPT-5 59.22%.

### New Tools (from all 10 files)
GSD (context rot), Greywall/nono (kernel sandbox), SWE-agent (Princeton, SOTA fleet worker), Stoneforge (merge resolution), Arize Phoenix (agent graph viz), Bifrost (54x faster than LiteLLM), claude-code-mux (Rust router), EXO (pool VRAM across network), Letta Code (memory-first agent), CoPaw (Alibaba, ReMe memory), SkillKit (44 agents, 400K skills)

### DESK RTX 3060 Content Gen Stack (from RTX3060-AI-Content-Generation-Stack.md)
Images: SD WebUI Forge + SDXL checkpoints + ADetailer + ReActor. Video: Wan 2.2 Remix NSFW + SVI 2.0 Pro (infinite-length) + Fun Control 5B (pose). Audio: MMAudio V2 + XTTS v2 (voice clone) + Bark (expressive) + RVC. ~120-130GB disk.

### Codex Multi-Agent Patterns (5 patterns)
Hub-and-Spoke (1 planner + N builders), Assembly Line (sequential), Tournament (compete, verifier picks), Refactor Sweep (iterative), Autonomous Pipeline (signal → plan → build). Controlled concurrency: 1 planner, 2-4 builders, 1 verifier. 5 maturity stages: Assisted → Structured → Verified → Automated → Autonomous.

### Deep Research — Governor Architecture
Meta Orchestrator emits ActionPlan JSON → Governor verifies against constitution → executes. LLM NEVER calls tools directly. Migration path: shadow → read-only → low-risk → lease-gated → full autonomy with kill switch.

### Intelligence Pipeline (already partially deployed)
Inoreader + F5Bot + changedetection.io + hnrss.org + Reddit RSS → Miniflux (VAULT:8070 ✅) → n8n (VAULT:5678 ✅) → agents (FOUNDRY:9000 ✅) → Neo4j (VAULT:7687 ✅). 41 n8n workflows in Hydra repo ready to import.

### Full details: See agent output at `C:\Users\Shaun\AppData\Local\Temp\claude\C--\tasks\a027cce401785de97.output`

## ADDENDUM E: GitHub Repository Inventory (Dirty13itch — 33 repos)

**33 GitHub repos reveal ~20 active projects across infrastructure, business, personal, and creative domains.**

**Infrastructure (7):** athanor (TS, main), Local-System (Python, v4), system-bible, kaizen (reference), hydra (66 MCP tools + 41 n8n workflows), agentic-coding-tools (private), AI-Dev-Control-Plane (private)

**Business/Ulrich Energy (9):** Field_Inspect (TS, multi-tenant inspection platform, Mar 15), AuditForecaster (TS), ulrich-energy-website (HTML), ulrich-energy-auditing (Python), BKI-Tracker (Python, private), BKI-Calendar-reconciler (private), airtight-iq (Python, ML forecasting, archived), buff-wrap-inspector (TS, private), subcontractor-snap (TS, private)

**Personal (6):** amanda-med-tracker (JS, NO local clone!), Reverie (Cannabis Cabinet), Buffalog (BWW reviews), Favorites, sabrina-therapy-blueprint, To-Do (archived)

**Manus-Built (11, all private TS, portfolio/):** website-app, stash-explorer, performer-database-app, nvidia-gpu-comparison, darkweb-tools-directory, Gaming-Ideas, curator-media-magic, mood-compass-whisperer, savor-street-symphony, reverie-dream-journal, truck-trail-finder-app

**Issues:** local-system-v4/ UNVERSIONED (no .git), amanda-med-tracker no local clone, Gitea needs API token for full listing, 5 quarantine duplicates to clean

**Autonomous dev priority:** P0=athanor+Local-System, P1=Field_Inspect+BKI-Tracker+ulrich (business revenue), P2=EoBQ+amanda-med-tracker (personal), P3=Portfolio apps (maintenance only)

## ADDENDUM F: Pending — dev/docs/ scan (79 files, 1 agent still running)
