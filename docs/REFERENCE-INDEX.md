# Athanor Reference Index

> **Last updated:** 2026-04-15
> **Status:** Reference only.
> **Current operator truth starts with:** `python scripts/session_restart_brief.py --refresh`, `reports/truth-inventory/finish-scoreboard.json`, `reports/truth-inventory/runtime-packet-inbox.json`, `STATUS.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`, generated operations reports, and `config/automation-backbone/`.
> **Purpose:** predecessor import catalog and historical reference only.
> **Publication boundary:** this page is not a checkpoint, queue, runtime, or operator authority surface.
> **Execution boundary:** do not trust commands, ports, service names, aliases, or routing assumptions from predecessor roots without rechecking current canon in the restart brief, `docs/SERVICES.md`, `docs/SYSTEM-SPEC.md`, and registry-backed reports.

Athanor evolved through four predecessor iterations. Each contains historical material and import candidates that may still be useful. This index catalogs what is there and where to find it.

Treat every subsection below as a predecessor import catalog, not an execution guide. If a pattern, port, alias, workflow, command, or architectural claim matters now, recheck it against the current restart brief and generated canon before operational use.

All reference repos: `~/repos/reference/`

---

## Hydra (Dec 2025) — Parts Warehouse

66 MCP tools, 710 API endpoints, 37 n8n workflows, 103 Python modules. The largest predecessor — a monolithic FastAPI system with NixOS (rejected in ADR-001) and TabbyAPI/ExLlamaV2 (rejected in ADR-005).

**Historical references / import candidates:**
- n8n workflows (37): `config/n8n/workflows/` — morning-briefing, self-improvement cycle, autonomous-research, health-digest, container-auto-restart, model-performance-monitor, database-backup, discord-notification-bridge, rss-feed-processor, character-consistency-clipvision, and more
- Self-improvement engine (DGM): `src/hydra_tools/dgm_engine.py` + `self_improvement.py` + `self_diagnosis.py`
- Autonomous trigger rules (12 categories): `autonomous/trigger_rules.yaml`
- Constitutional enforcement code: `src/hydra_tools/constitution.py`
- CLIPVision character consistency (157KB): `src/hydra_tools/character_consistency.py`
- Preference learning: `src/hydra_tools/preference_learning.py` + `feedback_integration_loop.py`
- Circuit breaker: `src/hydra_tools/circuit_breaker.py`
- Intelligent model router: `src/hydra_tools/intelligent_router.py`

**Reference only (patterns, not code):**
- Operational runbooks: `docs/runbooks/` (performance-tuning, backup-restore, model-management, maintenance, service-recovery)
- Observability configs: `config/prometheus/prometheus.yml` (40+ targets), `config/loki/`, `config/alertmanager/`
- LiteLLM cascade routing: `config/litellm/config.yaml` -- historical Hydra-only reference; current provider truth is tracked in `config/automation-backbone/provider-catalog.json` and `docs/operations/PROVIDER-CATALOG-REPORT.md`
- Command center design (35+ React components): `design/hydra-command-center/`
- Docker compose (60+ services): `docker-compose/hydra-stack.yml`
- Home Assistant config: `homeassistant/configuration.yaml`
- ComfyUI workflows: `comfyui-workflows/`
- Autonomous steward directives: `docs/autonomous-steward-directives.md`

**Obsolete (platform rejected):** NixOS modules, TabbyAPI/ExLlamaV2 configs, Ollama configs, CrewAI integration.

---

## Kaizen (Jan–Feb 2026) — Cognitive Architecture

GWT (Global Workspace Theory) implementation with 8 specialists, Kubernetes deployment (rejected in ADR-001), SGLang inference (rejected in ADR-005). The cognitive architecture code is the unique value here.

**Historical references / import candidates:**
- GWT formal specification (620 lines): `specs/gwt-architecture.md`
- Workspace Manager (557 lines, production-ready): `cognitive/workspace/src/manager.py` — 7-state FSM, Redis persistence, WebSocket support
- Continuous State Tensor: `cognitive/workspace/cst.py` — 4096-dim embedding + goal stack + PAD emotional model
- Competition layer (specialist bidding): `cognitive/workspace/competition.py` — softmax selection, salience scoring (30% confidence + 40% relevance + 30% urgency)
- Tiered Router (reactive/tactical/deliberative): `cognitive/workspace/tiered.py`
- 8 specialist implementations: `cognitive/specialists/` (reasoning, coding, creative, empire, hers, home, memory, research)
- 8 specialist system prompts (7-13KB each): `prompts/specialists/`
- Tool registry with 40+ tools: `cognitive/tools/`
- Character database (15+ profiles, 841 lines): `data/characters.yaml` — 19-trait personality scores, voice characteristics, emotional tells, relationships
- HERS professional data: `data/hers.yaml` (229 lines) + `prompts/specialists/hers.md` (7.4KB) — IECC 2012 Minnesota compliance, blower door formulas, ENERGY STAR 3.1 Zone 6
- Smart home device data: `data/smart-home.yaml` (212 lines) — Lutron Caseta zones, Bond Bridge, Nest, Roborock, presence automations
- Multi-environment framework (12 contexts): `k8s/apps/base/cognitive-orchestrator/`

**Obsolete (platform rejected):** K8s manifests (63 files), Talos machine configs, SGLang configs, Flux CD setup.

---

## Local-System (Mar 2026) — Service Implementation

Docker Compose architecture (same as Athanor), LangGraph agents, 6-tier memory, EoBQ generation pipeline. Shares the same GitHub remote as Athanor's predecessor. Historically the closest predecessor to current Athanor.

**Historical references / import candidates:**
- 6-tier memory system (full implementation): `services/memory/` — working (Redis), episodic (Qdrant), semantic (Neo4j), procedural (PostgreSQL), resource (Qdrant+Meilisearch), vault (PostgreSQL+Qdrant)
- Memory consolidation pipeline: `services/memory/consolidation.py` — episodic→semantic→vault promotion
- Hybrid search (vector + BM25): `services/memory/search.py`
- EoBQ DNA engine (19-trait to visual modifiers): `services/gateway/dna_engine.py`
- EoBQ scene builder: `services/gateway/scene_builder.py`
- ComfyUI pipeline presets (988 lines): `services/gateway/pipelines.py` — FLUX uncensored, RealVisXL, FaceID, face-swap
- Autonomous generation scanner (913 lines): `services/gateway/auto_gen.py`
- Generation scheduler (1006 lines): `services/gateway/scheduler.py`
- Prompt template library: `services/gateway/prompt_templates.py`
- Feedback system: `services/gateway/feedback.py`
- 100+ Pydantic shared models (17KB): `shared/python/local_system/models.py`
- Qwen3.5 vision encoder OOM analysis (ADR): `docs/adr/001-qwen35-vision-encoder.md`
- LoRA training scripts: `scripts/train_subject_lora.py`, `scripts/extract_face_refs.py`
- vLLM health restart workaround (Issue #28230): `scripts/vllm-health-restart.sh`

**Reference only:** 7 MCP server thin wrappers (`services/mcp-servers/`), Next.js 15 UI (`ui/`).

---

## System-Bible (Feb 2026) — Locked Hardware

Structured as 7 numbered chapters. Only chapter 02 (hardware) was completed. Everything else is outlines. The hardware inventory was physically verified item-by-item.

**Worth preserving:**
- Component-level hardware inventory (historical system-bible ledger, verified Feb 6 2026): `docs/archive/hardware/hardware-inventory.md` — preserved as a detailed owned-hardware record; current hardware truth is now tracked in `config/automation-backbone/hardware-inventory.json` and `docs/operations/HARDWARE-REPORT.md`
- Power budget analysis (PSU→node mapping): `02-hardware/power-budget.md` — NEXUS at 9% headroom warning, transient spike analysis
- Pending acquisitions (RTX PRO 6000, InfiniBand): `02-hardware/pending-acquisitions.md`
- AI archetype properties (10 beloved fictional AIs): `README.md` — properties derived from JARVIS, TARS, Culture Minds, etc.

**Obsolete:** Chapter outlines (01, 03-07) — all unwritten, superseded by Athanor's docs.

---

## Planning Documents (~/repos/ root)

These are historical planning inputs outside the current repo authority boundary. Treat them as import candidates only, not as publication surfaces or live operator truth.

- `ATHANOR-MAP.md` (28KB) — Complete system map from 10-hour planning session (2026-03-07)
- `ATHANOR-MAP-ADDENDUM.md` — Corrections and additions to the map
- `FIRST-PROMPT.md` — The original prompt that launched the Athanor build sprint
- `DEEP-RESEARCH-LIST.md` (26KB) — Comprehensive research backlog and decision log
- `CLAUDE.md` — Operations center workspace instructions (for ~/repos/ as a whole)
