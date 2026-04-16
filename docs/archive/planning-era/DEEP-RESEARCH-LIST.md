# Athanor Deep Research List

**Compiled March 7, 2026 — Every area where research could improve the system**
**Reconciled March 8, 2026 — Cross-referenced against Tiers 1-15 build completion**

Status key: 🔴 Blocking (can't proceed without this) | 🟡 High-impact (should do soon) | 🟢 Enhancement (do when compounding) | ⚪ Exploratory (future consideration) | ✅ Resolved (built or addressed)

### Resolution Summary
- **33/66 items resolved** by Tiers 1-15 build + Phase 2 model upgrade
- **5 items blocked** on Shaun (credentials, physical, OAuth)
- **28 items remain open** (6 high-impact, 14 enhancement, 8 exploratory)

---

## 1. MODEL LAYER

### 1.1 ✅ Qwen3.5 model availability and quantization landscape
> **Resolved:** Phase 2 (2026-03-08). Qwen3.5-27B-FP8 official fits 4×5070Ti TP=4 at 32K context (15.5GB/GPU). Qwen3.5-9B does NOT fit 4090 (MoE expands to ~25GB). Qwen3.5-35B-A3B-AWQ fits 5090 at ~21GB. VRAM budgets confirmed empirically.
- Which AWQ/GPTQ/FP8 quants exist for Qwen3.5-27B, 35B-A3B, 9B?
- Which quant provider (cyankiwi, Qwen official, TheBloke successors) produces the best quality?
- Does Qwen3.5-27B-FP8 official quant actually fit 4×16GB TP=4 with room for KV cache at 131K context?
- VRAM budgets: exact memory usage per model variant per context length

### 1.2 🟡 Qwen3-Coder-Next (80B MoE, 3B active, 512 experts)
- Released after Qwen3.5, specifically optimized for coding and tool calling
- Someone ran it on dual MI60s with vLLM already — how does it compare to Qwen3.5-35B-A3B for coding tasks?
- Would it fit on the 5090 (32GB) in AWQ 4-bit? (~22GB estimated)
- Is it better than Qwen3.5 for the Coding Agent slot specifically?

### 1.3 🟡 Abliterated Qwen3.5 models
- Sovereignty vision requires uncensored local inference
- Are abliterated/uncensored Qwen3.5 variants available on HuggingFace?
- Do abliterated models maintain tool-calling quality? (Often breaks with ablation)
- Which ablation technique preserves the most capability? (DPO, representation engineering, etc.)

### 1.4 ✅ Speculative decoding with Qwen3.5 small models
> **Resolved:** Phase 2. MTP (Multi-Token Prediction) native to Qwen3.5 used instead of draft models. `--speculative-config '{"method": "mtp", "num_speculative_tokens": 1}'` gives 83% throughput improvement (10→18.3 tok/s). No draft model needed.
- Qwen3.5-0.8B or 2B as draft model for Qwen3.5-27B on TP=4
- vLLM now supports unified parallel drafting — what's the throughput gain?
- Can speculative decoding run on the 4090 (draft) feeding TP=4 on the 5070Tis?
- What's the optimal draft model size for 27B target on this hardware?

### 1.5 ✅ Model routing intelligence (RouteLLM / Quality Cascade)
> **Resolved:** Tier 15.1 — `routing.py` (~377 LOC). Pattern-based task classification, LiteLLM route mapping, fallback chains, cost tracking. Cloud escalation blocked on Anthropic API key.
- CLAUDE.md mentions "Quality Cascade cloud escalation" blocked on API key
- RouteLLM from Hydra — how did it classify task difficulty?
- Optimal cascade: local fast (9B) → local strong (35B/27B) → cloud (Sonnet 4.6)
- How does this integrate with LiteLLM's existing fallback routing?
- What confidence threshold triggers escalation?

### 1.6 ⚪ Emerging model architectures
- Mixture of Depths (MoD) — dynamic compute allocation per token
- State Space Models (Mamba-3, RWKV-7) — linear attention for infinite context
- Any MoE variants optimized specifically for 16GB cards?
- DeepSeek-V4 architecture — any lessons for local deployment?

---

## 2. INFERENCE ENGINE

### 2.1 ✅ vLLM nightly vs stable for Qwen3.5
> **Resolved:** Phase 2. Using `athanor/vllm:qwen35` image (nightly 0.16.1rc1.dev32). Stable v0.16.0 does NOT support Qwen3.5. Key constraints: `--enforce-eager` required (DeltaNet Triton OOM), `--kv-cache-dtype auto` (never fp8). v0.18 not yet tested.
- Which nightly build first supported Qwen3_5MoeForConditionalGeneration?
- Is there a pinned nightly known to be stable? (e.g., 0.17.0.dev20260305)
- What broke between v0.16.0 and the nightly? Any regressions?
- vLLM v0.18 just released with 30.8% throughput improvement from async scheduling + pipeline parallelism — does it support Qwen3.5?

### 2.2 🟡 SGLang status for Qwen3.5
- Issue #19644 (AWQ loading broken for 35B-A3B) — is it fixed?
- SGLang RadixAttention: 10-20% boost for multi-agent shared prefixes — validated on Qwen3.5?
- SGLang v0.5.9 vs latest — what changed?
- Performance comparison: SGLang vs vLLM nightly on identical hardware with identical model

### 2.3 ✅ Prefix caching optimization
> **Resolved:** Phase 2. Prefix caching enabled, measured ~79% hit rate (5-min window) / ~42% lifetime. Agent system prompts share common prefix via `create_react_agent`. Context injection moved to HumanMessage to preserve prefix stability.
- Multi-agent shared system prompts: how much KV cache is reused?
- vLLM `--enable-prefix-caching` — what's the actual hit rate with 8 agents sharing a coordinator prefix?
- SGLang RadixAttention automatic prefix sharing — is it measurably better?
- Can we structure agent prompts to maximize prefix overlap?

### 2.4 🟢 RTX 5070Ti and 5090 specific optimizations
- vLLM SM120 (Blackwell) kernel support — what's the current state?
- NVFP4 MoE kernel support for RTX Blackwell workstation GPUs (fixed in recent vLLM)
- FP8 CUTLASS group GEMM fallback to Triton on SM120
- Optimal `--gpu-memory-utilization` for 16GB (5070Ti) vs 32GB (5090)

### 2.5 🟢 Triton autotuner cold start mitigation
- First cold start spikes VRAM due to Triton kernel compilation
- Persist `~/.cache/triton` across restarts — does this fully solve it?
- Pre-warm strategy: send a dummy request before serving real traffic?
- Ansible role to pre-warm Triton cache during deployment

### 2.6 ⚪ llama.cpp as alternative backend
- Someone ran Qwen3.5 with llama.cpp using `--jinja` flag for tool calling
- llama.cpp GGUF quantization: different quality/speed tradeoffs than AWQ
- Useful for the 5060Ti (16GB) where AWQ might be tight?
- llama.cpp RPC for distributed inference across nodes

---

## 3. AGENT ARCHITECTURE

### 3.1 ✅ General Assistant delegation upgrade
> **Resolved:** Tier 13.1 — GA system prompt rewritten with explicit delegation rules, correct architecture, multi-part decomposition guidance.
- Current delegation logic in `_build_task_prompt()` — what does it actually do?
- How to improve decomposition: break complex queries into parallel subtasks
- Confidence-based routing: >0.8 act, 0.5-0.8 act+notify, <0.5 hold+ask
- "Agents as tools" pattern vs current handoff pattern — which is better for Athanor?

### 3.2 ✅ GWT vs delegation vs agents-as-tools
> **Resolved:** Tier 11.6 — Formal competition layer with specialist interface, softmax selection, inhibition tracking. GWT Phase 3 complete.
- Kaizen had a 558-line GWT workspace manager with salience scoring
- Did the salience competition produce measurably better results than simple delegation?
- Can we A/B test: same tasks, GWT routing vs direct delegation, measure quality?
- Is there a hybrid: salience scoring to select the specialist, then delegation?

### 3.3 🟢 AdaptOrch topology-aware routing
- Paper showed 12-23% improvement from topology-aware routing over static baselines
- Orchestration topology > model selection for multi-agent systems
- How to implement: test hierarchical vs parallel vs sequential for YOUR workloads
- LangFuse tracing to compare topologies on identical task sets

### 3.4 ✅ Inference-aware agent scheduling
> **Resolved:** Tier 13.2 — `scheduling.py` queries Prometheus for GPU util + vLLM queue depth. Agent classes (latency-sensitive, batch, creative) throttled under load.
- No existing framework handles GPU contention for local inference
- Need to know vLLM queue depth before spawning new agents
- Which agents tolerate latency (review, research) vs need low latency (user-facing)?
- Custom scheduling logic: query vLLM metrics endpoint, throttle agent spawning
- vLLM Prometheus metrics at /metrics — what's exposed?

### 3.5 ✅ Agent memory and context persistence
> **Resolved:** Tiers 7.8-7.10, 10.5, 11.2-11.4 — Qdrant (8 collections), Neo4j (4447 relationships), Redis (CST, preferences, workspace). Context injection, consolidation, hybrid search all wired.
- Letta (MemGPT) v0.16 — how does it compare to raw Qdrant+Neo4j+Redis?
- Does Letta's automatic context management reduce the need for manual /compact?
- How does Letta interact with the 5-collection Qdrant setup (episodic/semantic/procedural/working/workspace)?
- Is Letta worth adding, or does it duplicate what's already built?

### 3.6 ⚪ A2A (Agent-to-Agent) protocol
- Google's protocol for peer agent communication, v0.9 with 120+ SDKs
- LiteLLM now has A2A support (from their GitHub: `from litellm.a2a_protocol import A2AClient`)
- Could Athanor agents communicate peer-to-peer instead of all through the coordinator?
- When is peer communication better than hub-and-spoke?

---

## 4. INTELLIGENCE PIPELINE

### 4.1 ✅ Miniflux + n8n as RSS/signal processing backbone
> **Resolved:** Tier 12.1 — Miniflux VAULT:8070 (17 feeds, 6 categories), n8n VAULT:5678 (signal pipeline workflow). Qdrant `signals` collection. Needs Shaun to activate n8n workflow in UI.
- Miniflux: self-hosted RSS reader, REST API, PostgreSQL backend
- n8n: self-hosted workflow automation with AI nodes
- How do these connect to the existing Athanor agent framework?
- Does the intelligence pipeline become Agent #9 or enhance the existing Knowledge Agent?

### 4.2 ✅ Hydra n8n workflow portability
> **Resolved:** Tier 12.1 — Signal pipeline workflow created from Hydra patterns. Hydra had 12 workflows (not 41 as initially claimed). Core patterns ported.
- 41 workflow JSONs in the Hydra reference repo
- Can they import directly into a fresh n8n instance?
- Which workflows need endpoint URL updates vs complete rewrites?
- Priority order: morning-briefing, rss-feed-processor, autonomous-research, knowledge-refresh, learnings-capture, health-digest, model-performance-tracker

### 4.3 ✅ Signal classification architecture
> **Resolved:** Tier 12.1 — n8n workflow: Schedule → Fetch Miniflux → LLM Classify (via LiteLLM) → Embed → Qdrant `signals`. Self-hosted weak signal layer operational.
- Inoreader Pro + Readwise Reader as commercial core (~$220/yr)
- Self-hosted weak signal layer: F5Bot, hnrss.org, Reddit RSS, changedetection.io, MonitoRSS
- 6-week agent build plan using Miniflux+n8n+LangGraph+Qdrant+Neo4j
- Four intelligence functions: model horizon scanning, infrastructure/dependency monitoring, tool ecosystem evolution, business/regulatory tracking

### 4.4 🟢 Audio intelligence layer
- Snipd for podcast highlights
- Readwise Reader TTS for reading articles
- NotebookLM Audio Overviews for synthesis
- Can these feed into the knowledge graph automatically?

### 4.5 ⚪ Agentic RSS: LLM-powered feed processing
- Use Qwen3.5-9B (utility slot) to classify/summarize/tag incoming RSS items
- Auto-categorize: model release, vulnerability, tool update, regulatory change
- Generate daily intelligence brief from classified items
- Qdrant vectors for semantic dedup across sources

---

## 5. DEVELOPMENT TOOLING

### 5.1 🟡 Claude Code via local models (ANTHROPIC_BASE_URL)
- Proven to work: `ANTHROPIC_BASE_URL=http://vault:4000 ANTHROPIC_API_KEY=sk-local`
- LiteLLM translates Anthropic Messages API to OpenAI format for vLLM
- Context ceiling issue: agentic sessions hit 32K+ tokens fast
- `--dangerously-skip-permissions` needed for unattended SSH sessions
- What's the minimum model quality for Claude Code to be useful? (Qwen3.5-35B? 27B? 9B?)

### 5.2 🟡 Claude Code Swarms (experimental)
- Discovered via feature flags Jan 24, 2026
- Team lead agent plans and delegates to specialist background agents
- Shared task board, coordination via messaging, parallel work
- Feature flag: how to enable? Is it stable enough for production use?
- CC Mirror: open-source implementation of Claude Code's internal multi-agent system

### 5.3 🟢 Goose Recipes for infrastructure automation
- Recipes are version-controlled YAML workflows
- Scheduler runs timed triggers — map to overnight autonomous operations
- Goose roadmap: built-in inference, meta-agent orchestration, local-first
- Recipe security: Block's red team found prompt injection via poisoned recipes
- Best practices for recipe hygiene in a sovereign context

### 5.4 🟢 OpenCode orchestrator ecosystem
- opencode-orchestrator: hub-and-spoke, work-stealing queues, 50+ parallel sessions
- 2 Planner / 8 Coder / 4 Reviewer worker allocation
- MVCC + mutex for concurrent state
- Is this useful alongside claude-squad, or redundant?

### 5.5 ✅ Promptfoo for eval-driven development
> **Resolved:** Tiers 12.5, 13.4, 15.7 — 36 eval cases (20 baseline + 16 A/B comparison). LLM-as-judge assertions. Abliterated safety rubrics. Baseline 100% (38/38). CI integration via Gitea Actions.
- YAML-based test definitions against local models
- LLM-as-judge assertions
- CI/CD integration (Gitea Actions)
- Track prompt-to-output relationships via LangFuse
- Write evals for each Athanor agent: does prompt change X improve output quality?

### 5.6 ⚪ Context engineering patterns
- Context folding: compress context while preserving key information
- Recursive Language Models (RLMs): store context in Python variables, not in window
- Anthropic's /compact: when to trigger proactively?
- Claude Code's auto-compact: tuning for long infrastructure sessions

---

## 6. OBSERVABILITY & EVALUATION

### 6.1 ✅ LangFuse deployment and integration
> **Resolved:** Tier 12.4 — LangFuse VAULT:3030. LiteLLM wired via `success_callback: ["prometheus", "langfuse"]`. Traces flowing (verified 2026-03-08).
- Docker Compose on VAULT:3030
- Wire into LiteLLM via `success_callback: ["langfuse"]`
- Generate API keys, configure LANGFUSE_PUBLIC_KEY/SECRET_KEY
- First traces flowing within 1 hour of deployment

### 6.2 🟡 Arize Phoenix for agent graph debugging
- Simpler single-container deployment
- Superior agent graph visualization — maps agent flow as node graph
- Span replay for debugging with modified inputs
- Deploy alongside LangFuse: LangFuse for production tracing, Phoenix for debugging

### 6.3 ✅ Accelerated evaluation methodology
> **Resolved:** Tier 13.4 — A/B comparison YAML, 36 total eval cases, preference learning integration. Feedback buttons in dashboard chat.
- 100 representative requests across 10 task categories
- Rate all outputs via feedback endpoint
- Generates month of preference data in one day
- A/B testing via LiteLLM tag-based routing: same task, different model, compare

### 6.4 🟢 Benchmark suite for local inference
- vLLM built-in benchmark: `vllm bench serve` for baseline throughput
- GuideLLM (Red Hat): production-realistic load testing through LiteLLM
- lm-evaluation-harness (EleutherAI): model quality across 60+ benchmarks
- LocalScore (Mozilla): portable hardware comparison with public leaderboard

### 6.5 ✅ Continuous agent quality monitoring
> **Resolved:** Tier 15 — Self-improvement engine (6h benchmark cycle), nightly improvement pipeline (export → score → identify → deploy), preference learning, pattern detection. LangFuse tracing + feedback loop.
- Track per-agent success rate over time
- Detect quality degradation after prompt changes
- Automated regression testing: run eval suite nightly, alert on regressions
- LangFuse → n8n webhook → alert pipeline

---

## 7. CREATIVE PIPELINE (Empire of Broken Queens)

### 7.1 🟢 Character-consistent portrait generation
- LoRA-trained visual identity on PonyXL/SDXL
- IP-Adapter + ControlNet for pose consistency
- InsightFace inswapper_128.onnx for face consistency
- Tier 1 (LoRA + img2img 0.3-0.5 denoising + fixed seed) vs Tier 2 (ControlNet + face swap)

### 7.2 🟢 FLUX.1 pipeline on WORKSHOP 5090
- 32GB VRAM — can run FLUX.1 dev at full precision
- ComfyUI workflow for automated character generation
- Integration with Creative Agent's existing tool bindings
- Scheduling: run creative generation during off-peak GPU hours (overnight)

### 7.3 🟢 Wan2.1 video generation
- Video synthesis from character portraits
- 5090 VRAM budget for Wan2.1 alongside inference
- Integration with the existing Creative Agent

### 7.4 🟢 Voice pipeline
- Kokoro TTS with per-character emotion mapping
- Whisper STT for input
- Wake word detection
- Full pipeline on the new 6-node topology — which node runs what?
- 22 EoBQ queen characters with distinct voice profiles

### 7.5 🟢 Procedural LLM dialogue
- Qwen3.5-35B-A3B for generating in-character dialogue
- Relationship tracking across scenes via Neo4j
- Branching storyline state management
- Abliterated models critical for adult content without refusals

### 7.6 ⚪ Mobile generation (Samsung Galaxy S21 Ultra)
- Local Dream (xororz/local-dream) with unfiltered APK
- SD 1.5 Q4_0 ~1.9GB on Snapdragon 888
- Field character generation when away from the cluster

---

## 8. INFRASTRUCTURE & OPERATIONS

### 8.1 ✅ DEV node integration into cluster
> **Resolved:** DEV .189 fully integrated. SSH keys distributed. Embedding:8001 + Reranker:8003 running. Claude Code + claude-squad installed. Act_runner for Gitea CI. DNS resolution added to all nodes.
- Add to Ansible inventory
- What contract slot does it fill? (Test/validation? Dedicated dev inference?)
- SSH key distribution from DEV → all nodes
- Tailscale setup for field access
- IP address assignment (.xxx — what's available on the subnet?)

### 8.2 🟡 Ansible playbook for Qwen3.5 model swap
- Update the vLLM role variables: model path, tool-call-parser, KV cache dtype
- Rolling deployment: WORKSHOP first, FOUNDRY only after 7 days stable
- Systemd unit templates with `Restart=on-failure` and `RestartSec=10`
- Pre-warm Triton cache as post-deploy step

### 8.3 ✅ Overnight autonomous operation patterns
> **Resolved:** Tier 12.3 — `overnight-ops.sh` (5 phases), systemd timer (11 PM daily). Scheduler has morning plan (7 AM), pattern detection (5 AM), consolidation (3 AM), alert checks (5 min).
- What does the scheduler need to queue for off-peak GPU hours?
- Research tasks, creative generation, infrastructure maintenance
- Morning briefing generation at 6 AM
- RSS processing every hour
- Knowledge graph maintenance (prune stale, strengthen strong connections)
- System health check every 30 minutes

### 8.4 ✅ Gitea + Gitea Actions for CI/CD
> **Resolved:** Tier 12.6 — Gitea VAULT:3033, act_runner on DEV, CI workflow (Python syntax, YAML validation, TypeScript checks, ntfy notifications).
- Self-hosted, low resource (~200-300MB vs GitLab's 8GB+)
- GitHub Actions syntax compatibility
- Pipeline: push → lint → test → build → deploy via Ansible
- Promptfoo eval in CI: every prompt change gets tested

### 8.5 ✅ The 99.13% GPU idle problem on 5090
> **Fully resolved:** Phase 2. 5090 runs Qwen3.5-35B-A3B-AWQ at 215 tok/s. Quality cascade routes worker-class tasks to it. Fallback chains ensure it catches overflow. LangFuse traces confirm traffic flow.
- Session 19 identified the 5090 sitting at 99.13% idle with zero requests
- Fast Agent slot (Qwen3-14B) getting zero traffic
- Root cause: General Assistant not delegating enough? Wrong routing rules?
- Fix: model swap to Qwen3.5-35B-A3B + actually routing traffic to it

### 8.6 ⚪ MTU mismatch across nodes
- Identified in Session 19, not yet resolved
- 5GbE SFP+ data plane — jumbo frames configured consistently?
- Impact on large model weight transfers and inference latency

---

## 9. HOME & MEDIA AUTOMATION

### 9.1 🟢 Home Assistant integration depth
- Home Agent runs every 5 minutes with entity control
- What entities are currently monitored/controlled?
- Wyoming protocol for voice: Piper TTS + Whisper STT
- Can the Home Agent use Qwen3.5-9B on the 4090 for faster response?

### 9.2 🟢 Media management (224TB+ library)
- Media Agent with Sonarr/Radarr/Tautulli hooks, 15-min cycle
- Stash Agent with 12 GraphQL tools
- AI-powered tagging: use Qwen3.5 vision (if available) for content classification?
- Plex on A380: any Plex updates that benefit from better transcoding?

### 9.3 ⚪ Kindred social matching app
- Matching on "drive state" intensity, not static profiles
- Grounded in Epley/Schroeder stranger conversation research and flow theory
- Is there an AI-native implementation path using the Athanor stack?

---

## 10. PROTOCOLS & STANDARDS

### 10.1 🟢 MCP ecosystem for cluster management
- Docker MCP Toolkit: 200+ containerized MCP servers
- Filesystem MCP for file access
- GitHub MCP for PR/CI integration
- Custom MCP server for vLLM metrics, LiteLLM routing, cluster status
- MCP Tool Search: lazy loading reduces context usage by 95%

### 10.2 🟢 A2A (Agent-to-Agent) protocol
- v0.9 with 120+ SDKs
- LiteLLM has native A2A support
- Potential for Athanor agents to discover and communicate without coordinator mediation
- When is peer communication better than hub-and-spoke?

### 10.3 ⚪ AGENTS.md standard
- OpenAI-proposed standard for agent configuration (like CLAUDE.md)
- Cross-tool compatibility with OpenCode, Goose, Codex
- Should Athanor repo have both CLAUDE.md and AGENTS.md?

---

## 11. BUSINESS & REGULATORY (Ulrich Energy)

### 11.1 🟡 RESNET standard updates
- ANSI/RESNET/ICC 380 — any 2025-2026 revisions?
- ENERGY STAR MFNC v1.1 — any updates past Rev.05?
- Impact on testing protocols and reporting requirements

### 11.2 🟡 Minnesota energy code changes
- Minnesota 2012 IECC (CZ 6A, 3.0 ACH50) — any adoption of 2021 IECC?
- Compartmentalization testing requirements (≤0.30 CFM50/sf)
- Impact on pricing and workflow for BKI work

### 11.3 🟢 Airtight-IQ forecasting engine
- Predicting duct leakage from historical BKI data
- Model architecture: what ML approach fits the data best?
- Can Qwen3.5 help analyze the dataset and suggest features?
- Integration with BKI Tracker spreadsheet

### 11.4 ⚪ AI-assisted HERS rating reports
- Could Athanor auto-generate report drafts from test data?
- DG-1000 data → LLM analysis → formatted report
- Time savings per inspection

---

## 12. KNOWLEDGE & MEMORY ARCHITECTURE

### 12.1 🟡 The 10 novel enhancement ideas from planning corpus reconciliation (6/10 implemented)
1. ✅ **Taste profiles via Qdrant** — implicit preference vectors from interaction patterns → Tier 15.6 (preference_learning.py)
2. **Interruption intelligence** — when to interrupt vs when to hold information → partially via Tier 7.9 (escalation protocol)
3. ✅ **Unified conversational router** — single entry point for all interaction modalities → Tier 11.1 + 15.1 (router.py + routing.py)
4. **Content discovery from implicit preference signals** — recommend based on behavior, not explicit requests
5. **Context-aware notification batching** — group related updates for single delivery
6. ✅ **Predictive pre-computation** — anticipate likely queries and pre-compute answers → Tier 15.3 (semantic_cache.py)
7. ✅ **Skill transfer between agents** — when one agent learns something, others benefit → Tier 11.4-11.6 (CST + specialists + competition)
8. ✅ **Failure mode learning** — track what goes wrong, build resistance → Tier 15.2 (diagnosis.py) + Tier 13.3 (pattern detection)
9. ✅ **Temporal pattern recognition** — learn daily/weekly rhythms, act accordingly → Tier 13.3 (behavioral patterns, time-of-day analysis)
10. **Emergent capability discovery** — detect when the system can do something it couldn't before

### 12.2 🟢 Knowledge graph density and utility
- Neo4j has 43 relationships — is this enough to be useful?
- What relationship types produce the most value?
- GraphRAG: structured traversal vs vector similarity for agent context
- Knowledge graph maintenance: pruning stale nodes, strengthening validated connections

### 12.3 🟢 Qdrant collection optimization
- 5 collections with 1200+ points — what's the distribution?
- Which collection is most/least queried?
- Embedding model: Qwen3-Embedding-0.6B — is there a better option in the Qwen3.5 family?
- Collection-specific similarity thresholds

### 12.4 ⚪ Compound learning loop design
- Preference learning + knowledge optimization + self-diagnosis all accumulating
- How long before the system produces noticeably better results?
- What metrics indicate the system is actually learning vs just storing data?
- The "let it run for a month" experiment: what to measure

---

## 13. SECURITY & SOVEREIGNTY

### 13.1 🟢 Prompt injection defenses for local agents
- Block's Goose red team: poisoned recipe with invisible Unicode → infostealer
- Goose now has Unicode detection and alerts
- For Athanor: what attack surface exists via MCP tools, n8n webhooks, RSS feeds?
- Defense: input sanitization, output monitoring, sandboxed execution

### 13.2 🟢 Data sovereignty verification
- Zero telemetry — how to verify no outbound connections from inference nodes?
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` for Claude Code
- Network monitoring: what should each node be allowed to reach?
- Firewall rules for the 5GbE data plane

### 13.3 ⚪ Model integrity verification
- How to verify downloaded model weights haven't been tampered with?
- SHA256 checksums from HuggingFace — automate verification
- Supply chain: trust model from cyankiwi vs Qwen official?

---

## 14. HARDWARE OPTIMIZATION

### 14.1 🟢 Loose hardware inventory utilization
- 6 motherboards, 5 RAM kits, 11 NVMe drives, 4 Intel CPUs, RX 5700 XT
- Could any of this become a 7th node for specific workloads?
- Best use: dedicated build/test server? Spare parts inventory?

### 14.2 🟢 Thermal management under sustained inference
- Arctic Liquid Freezer III Pro 360mm on DEV — sufficient for sustained 9900X?
- FOUNDRY EPYC 7663 cooling under 24/7 inference with 4+1 GPUs
- WORKSHOP TR 7960X with 5090+5060Ti — thermal throttling under load?
- Summer ambient temperatures in Dayton, MN

### 14.3 ⚪ Power consumption and UPS planning
- Total wattage under full inference load across all nodes
- UPS sizing for graceful shutdown
- Power monitoring: smart plugs? PDU with SNMP?

---

## PRIORITY ORDER (Updated March 8, 2026)

**Remaining blocking:**
1. 1.1 — Qwen3.5 quant landscape (still open, impacts model strategy)
2. 2.1 — vLLM nightly stability for Qwen3.5 (ongoing)

**High-impact open:**
3. 1.3 — Abliterated Qwen3.5 models (sovereignty requirement)
4. 6.2 — Arize Phoenix (agent graph debugging)
5. 5.1 — Claude Code via local models
6. 2.2 — SGLang evaluation for Qwen3.5
7. 11.1 — RESNET standard updates (Ulrich Energy)
8. 11.2 — Minnesota energy code changes

**Enhancement (compound):**
9. 12.1 — The 10 novel enhancement ideas (several now implemented)
10. 12.4 — Compound learning loop metrics
11. 13.1 — Prompt injection defenses
12. 13.2 — Data sovereignty verification
13. 6.4 — Benchmark suite (vLLM + GuideLLM)

**Resolved (28 items):**
1.5, 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 5.5, 6.1, 6.3, 6.5, 8.1, 8.3, 8.4, 8.5, plus 12 partial resolutions across tiers
