# The Capability Codex — Athanor's Complete Expertise Map

## Context

Athanor is a 4-node homelab running 9 AI agents, 55+ services, 8 GPUs (152 GB VRAM), coordinated by Claude Code as COO. After 56 build sessions, it's time to map *every type of expertise the ecosystem possesses or needs* — human, AI, infrastructure, physical, external — organized by **transferable capability type**, not by current domain application.

**Why this matters:** When a new project appears (Kindred, Ulrich Energy tools, a recipe system, anything), the system shouldn't need new expertise categories. It should compose existing expertise types and point them at the new domain. The Codex is the inventory that makes this possible.

**What this produces:**
- **Gap analysis** — unmanned areas, single points of failure, proficiency gaps
- **Agent architecture guidance** — whether 9 is right, what groupings should change
- **Living reference** — consult when making any build, staffing, or resource decision
- **Growth model** — how to absorb new projects without redesign

---

## Framework Structure

### 10 Expertise Categories

Each organized by **type of cognitive/operational work**, not domain:

| # | Category | Verb | Core Question |
|---|---|---|---|
| I | Cognition & Strategy | Directing | What should we do and why? |
| II | Research & Intelligence | Investigating | What's true, what's possible, what's best? |
| III | Creation & Generation | Making | How do we produce new artifacts? |
| IV | Curation & Organization | Structuring | How do we find, maintain, and connect what exists? |
| V | Automation & Control | Reacting | How do we respond to conditions in real-time? |
| VI | Engineering | Building | How do we construct and modify systems? |
| VII | Operations | Maintaining | How do we keep things running and healthy? |
| VIII | Physical | Touching | What requires hands, presence, and hardware? |
| IX | Domain Knowledge | Knowing | What field-specific expertise informs everything else? |
| X | Governance & Coordination | Orchestrating | How do experts connect, cooperate, and stay aligned? |

### Proficiency Scale

| Level | Meaning | Criteria |
|---|---|---|
| **None** | No capability exists | Not even researched |
| **Awareness** | Researched, understood, not implemented | Research doc exists, no deployment |
| **Practitioner** | Functional, handles basic needs | Deployed, works for standard cases |
| **Expert** | Reliable, handles edge cases, well-documented | Battle-tested, gotchas documented, recovery procedures known |
| **Authority** | Defines best practice, pushes boundaries | Teaches, innovates, sets standards for others |

---

## Expert Relationships

Experts don't exist in isolation. These 7 relationship types determine how work flows, who can override whom, and what happens when they disagree.

### 1. Authority (Chain of Command)

```
CONSTITUTION.yaml ← absolute, overrides everything
  └── Shaun (Owner) ← vision, judgment, final say
        └── Claude (COO) ← operational decisions
              └── Local Agents ← domain execution
                    └── Tools & Services ← execute on behalf of agents
```

Authority is context-dependent:
- Claude has authority over architecture decisions
- Shaun has authority over taste and vision
- Home Agent has authority over routine lighting (within escalation thresholds)
- CONSTITUTION.yaml overrides everyone, always

### 2. Delegation (Task Assignment)

| From | To | Scope | Mechanism |
|---|---|---|---|
| Shaun | Claude | Anything | Claude Code, natural language |
| Shaun | Any agent | Direct requests | Dashboard chat |
| Claude | Any agent | Operational tasks | Task API, MCP bridge |
| Agent → Agent | Peer tasks | `delegate_to_agent` tool | Task engine |

Delegation does not transfer authority. The Media Agent can delegate a search to the Research Agent, but can't override the Research Agent's judgment about source quality.

### 3. Dependency (Supply Chain)

```
User-facing capability
  └── Agent (expertise composition)
        └── Inference (LiteLLM → vLLM)
              └── Model (weights on GPU)
                    └── GPU (hardware)
                          └── Power, cooling, network
```

Every expert has dependencies. The Codex maps these so we can answer: "If GPU 2 on FOUNDRY goes down, what expertise is lost?" Answer: Coding Agent loses its dedicated model → code generation/review degrades → falls back to shared coordinator.

### 4. Advisory (Consultation)

Some experts are consulted but don't execute:

| Expert | Advisory Role | Consulted By |
|---|---|---|
| Knowledge Agent | Institutional memory | All agents (via context injection) |
| Preferences collection | User taste/preferences | All agents (before acting) |
| Research Agent | Source evaluation | Claude, other agents |
| Shaun | Taste, values, judgment | Claude (via conversation) |
| CONSTITUTION.yaml | Constraint checking | Everything (enforcement layer) |

### 5. Conflict Resolution (Judiciary)

| Conflict Type | Resolution | Example |
|---|---|---|
| Agent vs. Agent | Escalate to Claude | Media Agent wants GPU for transcoding, Creative Agent needs it for generation |
| Agent vs. Constitution | Constitution wins, always | Agent tries to delete data without approval |
| Claude vs. Shaun | Shaun wins | Claude recommends enterprise tool, Shaun prefers simpler |
| Expert vs. Expert (same level) | Higher proficiency wins, or escalate | Two approaches to same problem |
| Resource contention | GPU Orchestrator (planned), or Claude arbitrates | Two models need same GPU |

### 6. Composition (Joint Operations)

Some capabilities only exist when multiple experts combine:

| Composed Capability | Required Experts | Breaking Point |
|---|---|---|
| Media Operations | Media Agent + Sonarr + Radarr + Plex + NFS | Any service down |
| Image Pipeline | Creative Agent + ComfyUI + Flux Model + GPU + NFS | Any link broken |
| Knowledge Synthesis | Knowledge Agent + Qdrant + Neo4j + Embedding Model | Any store unavailable |
| Agent Coordination | Claude + GWT Workspace + Task Engine + Redis | Redis or agent server down |
| Hybrid AI Reasoning | Claude (cloud) + Local LLMs + LiteLLM + MCP bridge | Internet or LiteLLM down |

### 7. Succession (Who covers when someone is unavailable?)

| Expert | Availability Risk | Succession Plan |
|---|---|---|
| Shaun | Travel, sleep, day job | Agents operate autonomously within boundaries. Claude holds decisions. Physical tasks wait. |
| Claude | Internet outage, API key expired | Local agents continue autonomously. No architecture decisions until restored. |
| FOUNDRY | Hardware failure, power loss | WORKSHOP models cover inference (degraded). DEV embedding survives. Agent server lost. |
| Specific agent | Crash, model OOM | General Assistant as fallback for basic requests. Other agents unaffected. |
| Redis | Crash, data loss | GWT workspace, task queue, agent registry, trust scores all lost. Agents revert to stateless reactive mode. |
| Qdrant | Crash, corruption | Knowledge retrieval, context injection, preferences all lost. Agents still function but without memory. |

---

## Category I: Cognition & Strategy

*Directing — What should we do and why?*

### I.1 — Vision & Direction Setting

| Aspect | Detail |
|---|---|
| **What it is** | Defining what Athanor should become, what projects to pursue, what matters most |
| **Provider** | Shaun (sole, irreplaceable) |
| **Proficiency** | Authority |
| **Artifacts** | `docs/VISION.md`, The Twelve Words, project concepts (EoBQ, Kindred, Ulrich Energy) |
| **Inputs** | Internal motivation (autotelic), affordance sensitivity ("what could this become?"), external inspiration |
| **Gap** | None — this is inherently human and appropriately staffed |
| **Transferable to** | Any new project. Vision-setting is domain-agnostic. |

### I.2 — Architecture & System Design

| Aspect | Detail |
|---|---|
| **What it is** | Designing how components fit together, evaluating tradeoffs, making structural decisions |
| **Provider** | Claude (COO) — primary. Shaun reviews architectural significance. |
| **Proficiency** | Expert |
| **Artifacts** | 21+ ADRs in `docs/decisions/`, `docs/SYSTEM-SPEC.md`, `docs/design/athanor-next.md` |
| **Sub-skills** | Component decomposition, API design, data flow modeling, dependency analysis, scalability assessment, one-person-scale filtering |
| **Tools** | ADR template, research → document → decide workflow, sequential-thinking MCP |
| **Gap** | Architecture decisions are currently all synchronous (Claude Code session). No async architecture review process. |
| **Transferable to** | Any system design — game engines, app backends, infrastructure |

### I.3 — Taste & Aesthetic Judgment

| Aspect | Detail |
|---|---|
| **What it is** | Evaluating quality, beauty, appropriateness — "is this good?" |
| **Provider** | Shaun (final authority), Claude (operational taste, informed by design system) |
| **Proficiency** | Shaun: Authority. Claude: Practitioner. |
| **Artifacts** | `projects/dashboard/docs/DESIGN.md` (OKLCh palette, typography, spacing), The Twelve Words, lens mode theming |
| **Sub-skills** | Visual design evaluation, UI/UX quality assessment, content quality judgment, "does this feel right?" |
| **Gap** | No automated aesthetic evaluation. Creative Agent generates images but can't judge quality — that requires human review. |
| **Transferable to** | Dashboard design, EoBQ visual style, any UI work, content curation quality bars |

### I.4 — Operational Decision-Making

| Aspect | Detail |
|---|---|
| **What it is** | Day-to-day decisions: resource allocation, priority ordering, incident response, workflow optimization |
| **Provider** | Claude (COO) — primary. Autonomy spectrum governs scope. |
| **Proficiency** | Expert |
| **Artifacts** | `CONSTITUTION.yaml` autonomy spectrum, escalation protocol, BUILD-MANIFEST.md priority system |
| **Sub-skills** | Priority triage, resource allocation, cost-benefit analysis, risk assessment, blocker identification |
| **Gap** | Decision-making is session-bound. Between Claude Code sessions, no operational decisions happen unless agents handle them autonomously within their narrow scope. |
| **Transferable to** | Any operational context — project management, incident response, resource planning |

### I.5 — Strategic Planning & Roadmapping

| Aspect | Detail |
|---|---|
| **What it is** | Multi-session planning: what to build in what order, dependency mapping, milestone tracking |
| **Provider** | Claude (COO) with Shaun's input on priorities |
| **Proficiency** | Expert |
| **Artifacts** | `docs/BUILD-MANIFEST.md` (19 tiers, 100+ items), `docs/design/athanor-next.md` (program tracks), MEMORY.md (session continuity) |
| **Sub-skills** | Dependency graphing, priority ranking, blocker tracking, progress reporting, scope management |
| **Tools** | BUILD-MANIFEST.md, MEMORY.md, STATUS.md, plan files |
| **Gap** | No visualization of the dependency graph. No automated progress tracking beyond manual manifest updates. |
| **Transferable to** | Any multi-phase project: EoBQ development roadmap, Kindred development, Ulrich Energy tool buildout |

### I.6 — Prompt Engineering

| Aspect | Detail |
|---|---|
| **What it is** | Crafting effective prompts for LLMs, diffusion models, and multi-step agent workflows |
| **Providers** | Claude Code (primary — system prompts, agent definitions), Shaun (ComfyUI prompt craft) |
| **Proficiency** | Expert |
| **Sub-skills** | System prompt design (9 agent system prompts), tool-call formatting (qwen3_xml parser), ComfyUI positive/negative prompts, LoRA trigger words, intensity directives (EoBQ 5 tiers), chain-of-thought elicitation, context window management |
| **Artifacts** | Agent system prompts in `agents/*.py`, ComfyUI workflow JSONs, EoBQ intensity directives, `.claude/skills/`, `.claude/rules/` |
| **Gap** | No prompt versioning or A/B testing. No automated prompt quality evaluation (promptfoo blocked). Agent system prompts not version-controlled separately from code. No prompt library for common patterns. |
| **Transferable to** | Any LLM-driven feature, any creative generation, any new agent design |

---

## Category II: Research & Intelligence

*Investigating — What's true, what's possible, what's best?*

### II.1 — Web Research & Source Evaluation

| Aspect | Detail |
|---|---|
| **What it is** | Finding information on the internet, evaluating source quality, extracting relevant facts |
| **Providers** | Research Agent (local, DuckDuckGo + fetch_page), Claude Code (Firecrawl MCP, WebSearch, WebFetch), HuggingFace MCP (model/paper search) |
| **Proficiency** | Research Agent: Practitioner. Claude: Expert. |
| **Sub-skills** | Query formulation, source credibility assessment, fact extraction, contradiction detection, citation tracking |
| **Tools** | DuckDuckGo search, Firecrawl (crawl, scrape, search, deep_research), HuggingFace (paper_search, hf_doc_search, hub_repo_search), Miniflux MCP (RSS feeds), Context7 (library docs) |
| **Gap** | Research Agent can't do deep multi-source synthesis — it fetches and summarizes but doesn't cross-reference. Claude Code can, but it's session-bound. No persistent research queue that runs overnight. |
| **Transferable to** | Technology evaluation, competitive analysis, game design research, business intelligence |

### II.2 — Technology Evaluation & Benchmarking

| Aspect | Detail |
|---|---|
| **What it is** | Comparing tools, frameworks, models, approaches with quantitative data |
| **Provider** | Claude (COO) — primary. Research Agent assists. |
| **Proficiency** | Expert |
| **Artifacts** | 20+ research docs in `docs/research/`, minimum 3 options compared per decision |
| **Sub-skills** | Benchmark interpretation, spec sheet analysis, compatibility checking, gotcha documentation, community signal reading |
| **Examples** | vLLM on Blackwell research, game engine evaluation (Ren'Py vs. Godot vs. Next.js), voice interaction stack comparison, Wan2.x video deployment research |
| **Gap** | No automated benchmark runner. Model evaluations are manual. Promptfoo eval baseline blocked on API key. |
| **Transferable to** | Any technology choice — new AI models, new tools, new services |

### II.3 — Knowledge Retrieval & Synthesis

| Aspect | Detail |
|---|---|
| **What it is** | Finding and connecting information across Athanor's institutional memory |
| **Providers** | Knowledge Agent (Qdrant + Neo4j), Claude Code (memory files, git history), Context injection system |
| **Proficiency** | Expert (Tier 18 complete — HippoRAG entity extraction, miniCOIL hybrid search, Neo4j 2-hop traversal) |
| **Sub-skills** | Semantic search, graph traversal, entity linking, relevance ranking, hybrid retrieval (BM25 + vector via RRF) |
| **Tools** | Qdrant (9 collections, 2547+ vectors), Neo4j (3095 nodes, 4447 relationships), embedding model (Qwen3-Embedding-0.6B), reranker (Qwen3-Reranker-0.6B) |
| **Current state** | 9 Qdrant collections (knowledge, conversations, signals, activity, preferences, implicit_feedback, events, llm_cache, eoq_characters). HippoRAG entity extraction (879 entities, 5455 MENTIONS edges). |
| **Gap** | Conversation history indexing exists but isn't populated. Knowledge indexing is manual (should be cron). Personal data photo analysis blocked (VLM needed). |
| **Transferable to** | Any knowledge-intensive task — research synthesis, documentation, Q&A, recommendation |

### II.4 — Pattern Recognition & Trend Detection

| Aspect | Detail |
|---|---|
| **What it is** | Finding patterns in behavior, usage, system performance over time |
| **Providers** | Planned (Layer 3 intelligence). Partial: Prometheus metrics, LangFuse traces. |
| **Proficiency** | Awareness (designed, not implemented) |
| **Sub-skills** | Time series analysis, behavioral pattern extraction, anomaly detection, preference inference |
| **Planned signals** | Media: watch completion rates, genre preferences. Home: occupancy patterns, daily routines. Creative: kept vs. regenerated images. Research: accepted vs. rejected sources. |
| **Gap** | No pattern detection jobs exist. Signal collection infrastructure is deployed (activity logging, implicit feedback, events collections) but no analysis layer runs on top. |
| **Transferable to** | Any domain with repeated interactions — media recommendations, home optimization, content curation |

### II.5 — Competitive & Market Intelligence

| Aspect | Detail |
|---|---|
| **What it is** | Understanding what's happening in relevant markets, technologies, communities |
| **Providers** | Miniflux (RSS reader at VAULT), Claude Code (web research), HuggingFace MCP |
| **Proficiency** | Awareness |
| **Sub-skills** | Industry trend tracking, competitor monitoring, community signal detection |
| **Tools** | Miniflux MCP (RSS feeds), n8n (intelligence signal pipeline — configured but activation blocked on Shaun), Firecrawl |
| **Gap** | RSS feeds configured but n8n signal pipeline not activated. No automated daily intelligence digest. No tracking of AI model releases, new tool announcements, or homelab community developments. |
| **Transferable to** | Business intelligence (Ulrich Energy competitors), game dev trends, AI model landscape |

### II.6 — Data Analysis & Visualization

| Aspect | Detail |
|---|---|
| **What it is** | Analyzing structured data, creating charts, interpreting trends, building dashboards |
| **Providers** | Claude Code (primary), Grafana (metrics visualization), Dashboard (custom charts) |
| **Proficiency** | Expert |
| **Sub-skills** | Spreadsheet analysis/generation (xlsx skill), chart design (SVG in dashboard, Grafana panels), PromQL queries for time series, statistical reasoning, data cleaning, CSV/JSON transformation |
| **Tools** | anthropic-skills:xlsx (spreadsheet manipulation), Grafana (time series dashboards), Dashboard GPU chart (SVG bars), Prometheus (raw metrics), pandas/numpy (available in Python scripts) |
| **Gap** | No dedicated data analysis environment (no Jupyter notebooks deployed). No automated report generation from metrics. No interactive data exploration tool beyond Grafana. |
| **Transferable to** | Business analytics (Ulrich Energy), system performance analysis, user behavior analysis, any data-driven decision |

---

## Category III: Creation & Generation

*Making — How do we produce new artifacts?*

### III.1 — Still Image Generation

| Aspect | Detail |
|---|---|
| **What it is** | Creating images from text prompts using diffusion models |
| **Providers** | Creative Agent (orchestrates), ComfyUI (engine, Workshop GPU 1 / 5060 Ti) |
| **Proficiency** | Practitioner |
| **Sub-skills** | Prompt engineering (positive/negative, style tokens, LoRA triggers), workflow design (ComfyUI node graphs), model selection, resolution/quality tradeoffs, inpainting, upscaling |
| **Models** | Flux dev FP8 (~17 GB), flux-uncensored.safetensors LoRA (0.85 strength) |
| **Workflows** | 3 Flux workflows: portrait, scene, PuLID face injection |
| **EoBQ integration** | Character portraits, scene backgrounds, PuLID reference library for custom personas |
| **Gap** | No automated quality assessment (human must judge). No style consistency enforcement across sessions. No batch generation with variation. No SDXL/Pony path for anime art (identified as candidate). No LoRA training pipeline (capability exists in ComfyUI but no workflow defined). |
| **Transferable to** | Marketing images, presentation visuals, game assets, creative projects, social media |

### III.2 — Video Generation

| Aspect | Detail |
|---|---|
| **What it is** | Creating short video clips from text or image prompts |
| **Providers** | Creative Agent (orchestrates), ComfyUI + Wan2.2 MoE (Workshop GPU 1) |
| **Proficiency** | Practitioner (basic pipeline verified, 480x320 @ 17 frames) |
| **Sub-skills** | Text-to-video prompting, resolution/frame management, text encoder selection, VRAM optimization |
| **Models** | Wan2.2 t2v 14B FP8 (high/low noise), umt5-xxl-enc (Kijai non-scaled), Wan 2.1 VAE |
| **Performance** | 17 frames @ 480×320 in ~47-91s, peak 13.74 GB on 5060 Ti |
| **Gap** | Higher resolutions blocked (needs 5090 via vLLM sleep mode). No video-to-video. No image-to-video animation pipeline. No video editing/compositing. |
| **Transferable to** | Game cinematics (EoBQ), content creation, marketing, creative experiments |

### III.3 — Code Generation & Transformation

| Aspect | Detail |
|---|---|
| **What it is** | Writing, reviewing, transforming, and testing code |
| **Providers** | Claude Code (primary, Expert level), Coding Agent (local, 9 tools), Qwen3-Coder-30B on FOUNDRY GPU2 (dedicated coding lane), Qwen3.5-27B-FP8 TP=4 (coordinator) |
| **Proficiency** | Claude: Expert. Coding Agent: Practitioner. |
| **Sub-skills** | Architecture-aware code generation, code review, code transformation (JS→TS, sync→async), test writing, refactoring, type annotation, boilerplate generation, Ansible task generation |
| **Tools** | Claude Code (full IDE capabilities), Coding Agent tools (generate_code, review_code, explain_code, transform_code, read_file, write_file, list_directory, search_files, run_command), Serena MCP (symbolic code analysis — find_symbol, replace_symbol_body, get_symbols_overview) |
| **MCP bridge** | `mcp-athanor-agents.py` — coding_generate, coding_review, coding_transform for delegating to local models |
| **Languages** | TypeScript/React (dashboard, EoBQ), Python (agents, scripts, Ansible modules), YAML (Ansible, configs), Bash (scripts), CSS/Tailwind |
| **Gap** | Coding Agent quality issues on complex tasks — SWE-bench 70.7% (Qwen3-32B) vs. Claude's near-perfect. Quality cascade (local → cloud escalation) blocked on Anthropic API key. No automated test coverage tracking. |
| **Transferable to** | Any software project — Kindred, Ulrich Energy tools, new games, utilities |

### III.4 — Narrative & Dialogue Writing

| Aspect | Detail |
|---|---|
| **What it is** | Crafting stories, character dialogue, emotional arcs, interactive fiction |
| **Providers** | EoBQ system (LLM-driven dialogue), Claude Code (narrative design consulting) |
| **Proficiency** | Practitioner (EoBQ has 5 characters with emotional profiles, intensity tiers, breaking mechanics) |
| **Sub-skills** | Character voice consistency, emotional arc design, branching dialogue, intensity calibration, player responsiveness |
| **EoBQ specifics** | 5 characters, emotional profiles, content_intensity 1-5, breaking mechanics, model routing by intensity (≥3 → uncensored, 1-2 → reasoning), intensity directives (suggestive → absolute) |
| **Gap** | No long-form narrative planning tool. No character consistency verification across sessions. No player memory (Qdrant integration planned but not wired). |
| **Transferable to** | Interactive fiction, chatbots, RPG dialogue systems, creative writing assistance |

### III.5 — Document & Presentation Creation

| Aspect | Detail |
|---|---|
| **What it is** | Creating formatted documents, spreadsheets, presentations, PDFs |
| **Providers** | Claude Code (skills: docx, xlsx, pptx, pdf) |
| **Proficiency** | Expert (robust skill set available) |
| **Sub-skills** | Word document generation (TOC, headings, tables, letterheads), spreadsheet creation/manipulation, presentation design, PDF operations (fill, merge, split, OCR), theme application (10 pre-set themes) |
| **Tools** | anthropic-skills:docx, anthropic-skills:xlsx, anthropic-skills:pptx, anthropic-skills:pdf, anthropic-skills:theme-factory, PDF Tools MCP (fill, extract, analyze, bulk operations) |
| **Gap** | Not currently used for Athanor operations. Ulrich Energy workflows identify report generation as a need but nothing's built. |
| **Transferable to** | Ulrich Energy reports (HERS rating reports, duct leakage forecasts), business documents, presentations, invoices |

### III.6 — Interface & Visual Design

| Aspect | Detail |
|---|---|
| **What it is** | Designing user interfaces, interaction patterns, visual language |
| **Providers** | Claude Code (implementation), Shaun (taste/judgment), Dashboard design system |
| **Proficiency** | Expert (24 dashboard pages, 5 lens modes, responsive PWA, ambient design language) |
| **Sub-skills** | Component design (shadcn/ui), responsive layout, dark theme design, OKLCh color systems, animation/motion (Framer Motion), ambient UX (SystemPulse, furnace glow), mobile-first PWA, interactive playground creation |
| **Artifacts** | `projects/dashboard/docs/DESIGN.md`, 24 pages, generative UI for chat, lens mode system |
| **Tools** | anthropic-skills:canvas-design (visual art), anthropic-skills:web-artifacts-builder (complex React artifacts), playground skill (interactive HTML explorers) |
| **Gap** | No design system documentation beyond DESIGN.md. No component storybook. No accessibility audit. No user testing framework. |
| **Transferable to** | EoBQ UI, Kindred UI, Ulrich Energy UI, any web application |

### III.7 — Music & Audio Production

| Aspect | Detail |
|---|---|
| **What it is** | Creating music, sound effects, audio processing |
| **Providers** | None |
| **Proficiency** | None |
| **Gap** | Complete gap. No tools, no models, no pipeline. |
| **Potential** | Open-source music generation models exist (MusicGen, Stable Audio). Could be relevant for EoBQ soundtrack, ambient audio, content creation. |
| **Transferable to** | Game audio, content creation, creative experiments |

### III.8 — 3D Asset Creation

| Aspect | Detail |
|---|---|
| **What it is** | Creating 3D models, environments, characters |
| **Providers** | None |
| **Proficiency** | None |
| **Gap** | Complete gap. Not currently needed but identified in VISION.md as potential future workload. |
| **Transferable to** | Game development, visualization, virtual environments |

### III.9 — Communication & Writing

| Aspect | Detail |
|---|---|
| **What it is** | Writing clear prose, emails, summaries, explanations, reports — adapting tone and depth for audience |
| **Providers** | Claude Code (primary — Expert level), local LLMs (basic text generation) |
| **Proficiency** | Claude: Expert. Local: Practitioner. |
| **Sub-skills** | Technical writing (ADRs, research docs, SYSTEM-SPEC), explanatory writing (adapting to audience level), email composition (Gmail MCP), summarization, translation between languages, tone calibration, documentation co-authoring (doc-coauthoring skill) |
| **Tools** | Gmail MCP (draft/send emails), anthropic-skills:doc-coauthoring (structured documentation workflow), anthropic-skills:internal-comms (status reports, updates, FAQs) |
| **Current use** | 81+ docs written, ADR authoring, SYSTEM-SPEC maintenance, session summaries, code documentation |
| **Gap** | Local agents can't compose emails or external communications. No writing style guide beyond the Twelve Words. No automated summary generation from session logs. |
| **Transferable to** | Business communications (Ulrich Energy), user-facing documentation, marketing copy, blog posts, any project requiring written output |

---

## Category IV: Curation & Organization

*Structuring — How do we find, maintain, and connect what exists?*

### IV.1 — Content Discovery & Acquisition

| Aspect | Detail |
|---|---|
| **What it is** | Finding content that matches criteria and acquiring it |
| **Providers** | Media Agent (TV/movies), Stash Agent (adult content), Research Agent (web content), Data Curator (personal data) |
| **Proficiency** | Practitioner across all providers |
| **Sub-skills** | Search query construction, quality profile matching, duplicate detection, source evaluation, automated monitoring |
| **Tools** | Sonarr (TV search + monitor), Radarr (movie search + monitor), Prowlarr (indexer management), SABnzbd (download client), Stash (adult content scanning), DuckDuckGo (web search), RSS feeds (Miniflux) |
| **Gap** | qBittorrent blocked (NordVPN creds). Prowlarr needs indexer configuration. Sonarr/Radarr libraries are empty. No automated content quality assessment. |
| **Transferable to** | Any content domain — recipes, academic papers, news, datasets, software packages |

### IV.2 — Library Taxonomy & Metadata Management

| Aspect | Detail |
|---|---|
| **What it is** | Organizing content with consistent taxonomy, rich metadata, and findability |
| **Providers** | Media Agent (Sonarr/Radarr/Plex metadata), Stash Agent (12 tools for tagging/organizing), Knowledge Agent (Qdrant/Neo4j), Data Curator (personal data indexing) |
| **Proficiency** | Practitioner |
| **Sub-skills** | Category design, tag management, metadata enrichment, auto-tagging, relationship mapping, deduplication |
| **Tools** | Plex (media metadata + thumbnails), Stash (tag management, auto-tag, duplicate finder), Qdrant (semantic metadata), Neo4j (structural relationships), Meilisearch (full-text search) |
| **Gap** | Stash VLM auto-tagging plugin not deployed (Phase 2). No cross-domain taxonomy (media tags ≠ knowledge tags ≠ Stash tags). No unified search across all content types. |
| **Transferable to** | Any organized collection — bookmarks (727 indexed), photos, documents, code repositories, recipes |

### IV.3 — Knowledge Indexing & Graph Modeling

| Aspect | Detail |
|---|---|
| **What it is** | Converting unstructured information into searchable, connected knowledge |
| **Providers** | Knowledge Agent, `scripts/index-knowledge.py`, `scripts/extract-entities.py`, `scripts/index-files.py` |
| **Proficiency** | Expert (Tier 18 complete) |
| **Sub-skills** | Document chunking, embedding generation, entity extraction (LLM NER), relationship mapping, hybrid retrieval (BM25 + vector), graph traversal |
| **Current state** | 9 Qdrant collections. Neo4j: 3095 nodes (1055 Topics, 701 Documents, 391 Orgs, 97 People, 67 GitRepos, 24 Services, 18 Places). 4447 relationships. HippoRAG entity 2-hop traversal. miniCOIL neural sparse vectors. |
| **Gap** | Indexing is manual (no cron). Graph context could be deeper (currently 2-hop). No freshness tracking (stale docs not flagged). No automated re-indexing on doc changes. |
| **Transferable to** | Any knowledge-intensive system — documentation, research archives, personal data, project wikis |

### IV.4 — Data Quality & Lifecycle Management

| Aspect | Detail |
|---|---|
| **What it is** | Ensuring data is accurate, current, deduplicated, and properly aged |
| **Providers** | Data Curator (9th agent), memory consolidation pipeline, backup scripts |
| **Proficiency** | Practitioner |
| **Sub-skills** | Duplicate detection, content hash comparison, age-based purging, backup freshness monitoring, data integrity checking |
| **Tools** | Memory consolidation (activity >30d, conversations >30d, implicit_feedback >7d, events >14d), backup-age-exporter (Prometheus), content hash indexing in personal data |
| **Gap** | No data quality dashboard. No automated stale document detection in docs/. Consolidation runs but doesn't report what it purged. |
| **Transferable to** | Any data-heavy system — databases, content libraries, knowledge bases |

### IV.5 — Personal Data Management

| Aspect | Detail |
|---|---|
| **What it is** | Organizing, indexing, and making accessible Shaun's personal data |
| **Providers** | Data Curator (7 tools), personal data indexing scripts, dashboard `/personal-data` page |
| **Proficiency** | Practitioner (Tier 10 largely complete) |
| **Current state** | 727 bookmarks indexed, 82 GitHub repo chunks, 1511 file content chunks, 2304 total Qdrant points, 3095 Neo4j nodes. Photo analysis blocked. Google Drive ~40% blocked. |
| **Tools** | `scripts/sync-personal-data.sh` (rsync DEV→Node 1, 6h cron), `scripts/index-files.py`, `scripts/extract-entities.py`, Qdrant `personal_data` collection |
| **Gap** | Google Drive integration blocked (OAuth). Photo VLM analysis blocked (vLLM 0.17+ needed). No personal finance data. No email indexing. No calendar data integration. |
| **Transferable to** | Second-brain / PKM systems, life logging, personal analytics |

---

## Category V: Automation & Control

*Reacting — How do we respond to conditions in real-time?*

### V.1 — Smart Home Device Control

| Aspect | Detail |
|---|---|
| **What it is** | Controlling lights, climate, media, and other smart devices |
| **Providers** | Home Agent (8 tools), Home Assistant (VAULT) |
| **Proficiency** | Practitioner |
| **Sub-skills** | Entity discovery, service calling, automation creation, scene management, presence detection |
| **Tools** | get_ha_states, get_entity_state, find_entities, call_ha_service, set_light_brightness, set_climate_temperature, list_automations, trigger_automation |
| **Current state** | HA v2026.2.3, 43 entities (13 domains), Sonos + Cast devices, weather. Athanor Voice pipeline (STT/TTS/wake word). |
| **Gap** | Lutron lighting integration not configured (blocked on Shaun). UniFi network integration not added. No occupancy-based automation. No seasonal patterns. Limited to reactive control — no proactive optimization. |
| **Transferable to** | Any IoT system — office automation, environmental control, energy management |

### V.2 — Scheduled & Proactive Execution

| Aspect | Detail |
|---|---|
| **What it is** | Running tasks on schedule without human initiation |
| **Providers** | Proactive scheduler (asyncio, per-agent intervals), cron scripts, n8n workflows |
| **Proficiency** | Practitioner |
| **Sub-skills** | Interval scheduling, cron configuration, workflow orchestration, result broadcasting |
| **Schedules** | General (30min health), Media (15min downloads), Home (5min entity state), Knowledge (24h, disabled), Daily digest (6:55 AM), Memory consolidation (3 AM), Backups (3:00/3:15/3:30 AM) |
| **Tools** | scheduler.py (agent proactive tasks), cron (backups, data sync), n8n (intelligence pipeline — not activated), Claude Code scheduled tasks MCP |
| **Gap** | n8n signal pipeline not activated (Shaun must click Activate). Knowledge re-indexing not on cron. No dynamic scheduling (adjusting intervals based on system load). |
| **Transferable to** | Any automated workflow — report generation, data pipelines, monitoring, notifications |

### V.3 — Event-Driven Response

| Aspect | Detail |
|---|---|
| **What it is** | Reacting to system events, external triggers, and condition changes |
| **Providers** | GWT workspace (Redis-backed, 1Hz competition cycle), event ingestion API, Prometheus alerting |
| **Proficiency** | Practitioner |
| **Sub-skills** | Event detection, salience scoring, priority routing, cascade triggering |
| **Tools** | `POST /v1/events` (HA state changes, cron, webhooks → workspace items), Redis pub/sub (`athanor:workspace:broadcast`), Prometheus alert rules, ntfy push notifications |
| **Examples** | New episode → Media Agent broadcasts → Home Agent dims lights. Service crash → alert → ntfy notification. |
| **Gap** | Agents subscribe to broadcasts but don't reliably act on them yet (Phase 3 of GWT not started — coalition formation, semantic relevance scoring). No complex event processing. |
| **Transferable to** | Any event-driven system — webhooks, IoT triggers, notification pipelines |

### V.4 — Voice Interaction

| Aspect | Detail |
|---|---|
| **What it is** | Hearing commands and speaking responses |
| **Providers** | Wyoming stack: whisper (STT, FOUNDRY GPU4), Piper (TTS, VAULT CPU), openwakeword (VAULT CPU), Speaches (OpenAI-compat STT+TTS API, FOUNDRY GPU4) |
| **Proficiency** | Practitioner (deployed, functional) |
| **Sub-skills** | Speech-to-text, text-to-speech, wake word detection, voice pipeline management |
| **Gap** | No physical voice satellite device (ESP32-S3 planned). No custom wake word training. Voice is HA-only — not integrated with agent system directly. Limited to single-turn commands. |
| **Transferable to** | Any voice interface — smart speakers, accessibility, hands-free operation |

### V.5 — Desktop & Browser Automation

| Aspect | Detail |
|---|---|
| **What it is** | Automating desktop applications, browser interactions, and OS-level tasks |
| **Providers** | Claude Code (via MCP servers) |
| **Proficiency** | Expert (rich MCP toolset available) |
| **Sub-skills** | Browser navigation and interaction (click, fill, screenshot, evaluate JS), page performance analysis (Lighthouse, LCP), desktop screenshots and OCR, process management, file system operations, registry manipulation, keyboard/mouse automation |
| **Tools** | Playwright MCP (browser_navigate, browser_click, browser_fill_form, browser_snapshot, browser_take_screenshot, browser_evaluate, browser_network_requests), Chrome DevTools MCP (navigate_page, click, fill, evaluate_script, lighthouse_audit, take_screenshot, performance tracing), Windows MCP (Screenshot, Click, Type, Scroll, Process, PowerShell, FileSystem, Registry, App) |
| **Gap** | Session-only — no persistent browser automation. Agents can't use these tools. No scheduled browser tasks (e.g., automated form filling, web scraping pipelines). No RPA-style workflow builder. |
| **Transferable to** | E2E testing, web scraping, form automation, UI verification, accessibility auditing, Ulrich Energy portal interactions |

### V.6 — External Service Management

| Aspect | Detail |
|---|---|
| **What it is** | Managing calendars, email, notes, files, and deployments through external service APIs |
| **Providers** | Claude Code (via MCP servers — session-only) |
| **Proficiency** | Expert (extensive MCP coverage) |
| **Sub-skills** | Email management (search, read, draft, organize), calendar management (create/update events, find free time, schedule), note-taking (create/query Notion pages and databases), file management (Google Drive search/fetch), deployment management (Vercel/Netlify deploy, logs, status) |
| **Tools** | Gmail MCP (search, read, draft, labels), Google Calendar MCP (list, create, update, delete events, find free time), Notion MCP (search, create pages, query databases, create views), Google Drive MCP (search, fetch files), Vercel MCP (deploy, get logs, list projects), Netlify MCP (deploy, project management) |
| **Gap** | All session-only — agents can't access any external services. No email notifications from agents. No calendar-aware scheduling. No Notion-backed project tracking. No automated deployment pipeline. These are powerful capabilities locked inside Claude Code sessions. |
| **Transferable to** | Business operations (Ulrich Energy scheduling, invoicing), project management, personal productivity, automated reporting |

---

## Category VI: Engineering

*Building — How do we construct and modify systems?*

### VI.1 — Application Development (TypeScript/React)

| Aspect | Detail |
|---|---|
| **What it is** | Building web applications with TypeScript, React, Next.js |
| **Providers** | Claude Code (primary), Coding Agent (assists) |
| **Proficiency** | Expert |
| **Sub-skills** | Next.js 16 app router, React 19 (server components, suspense), Tailwind CSS, shadcn/ui components, Zustand state management, Framer Motion animation, SSE streaming, PWA service workers, responsive design |
| **Projects** | Dashboard (24 pages, PWA), EoBQ (interactive fiction), Ulrich Energy (placeholder) |
| **Tools** | `npx tsc --noEmit` (type checking), Serena MCP (symbolic code analysis), Vercel/Netlify MCPs (deployment), Context7 (library docs) |
| **Gap** | No automated testing (no Jest/Vitest configured). No E2E tests (Playwright available via MCP but not wired). No Storybook for component development. No CI/CD pipeline. |
| **Transferable to** | Kindred (web app), Ulrich Energy (web tools), any web project |

### VI.2 — Application Development (Python)

| Aspect | Detail |
|---|---|
| **What it is** | Building Python applications, scripts, and services |
| **Providers** | Claude Code (primary), Coding Agent (assists) |
| **Proficiency** | Expert |
| **Sub-skills** | FastAPI (agent server), LangGraph (agent framework), asyncio, Pydantic models, Docker containerization, pip/pyproject.toml dependency management |
| **Projects** | Agent Server (9 agents, 50+ tools, FastAPI), GPU Orchestrator (FastAPI), utility scripts (20+) |
| **Tools** | `python3 -m py_compile` (syntax checking), Serena MCP |
| **Gap** | No pytest test suite for agent server. No type checking (mypy not configured). No linting. |
| **Transferable to** | Any Python project — data pipelines, APIs, automation |

### VI.3 — AI/ML Model Deployment & Tuning

| Aspect | Detail |
|---|---|
| **What it is** | Selecting, deploying, configuring, and optimizing AI models |
| **Providers** | Claude Code (primary — Expert level) |
| **Proficiency** | Expert |
| **Sub-skills** | vLLM configuration (TP, quantization, attention backends, memory utilization, max-seqs), NGC container customization, Blackwell sm_120 gotchas, quantization selection (FP8 vs AWQ vs GPTQ), model routing via LiteLLM, ComfyUI model loading, LoRA deployment |
| **Hard-won knowledge** | Extensive gotchas documented in `.claude/rules/vllm.md`: flash-attn removal, flashinfer version mismatch, AWQ vs Marlin, enforce-eager for DeltaNet/Mamba Triton kernels, cpu-offload incompatibility, language-model-only flag, tool-call-parser qwen3_xml |
| **Models deployed** | Qwen3.5-27B-FP8 (TP=4), Qwen3-Coder-30B-A3B-AWQ, Qwen3.5-35B-A3B-AWQ, Qwen3-Embedding-0.6B, Qwen3-Reranker-0.6B, Flux dev FP8, Wan2.2 MoE |
| **Gap** | No automated model evaluation (promptfoo baseline blocked). No A/B testing framework. No automatic model update pipeline. GPU orchestrator sleep/wake not functional (vLLM v0.16.0 limitation). |
| **Transferable to** | Any AI deployment — new models, new quantizations, new hardware |

### VI.4 — Infrastructure as Code (Ansible)

| Aspect | Detail |
|---|---|
| **What it is** | Managing infrastructure configuration declaratively |
| **Providers** | Claude Code (writes roles/playbooks), Ansible (executes) |
| **Proficiency** | Expert (site.yml converges idempotent, 3 playbooks, 20+ roles) |
| **Sub-skills** | Role design, Jinja2 templating, Docker Compose management via `docker_compose_v2`, vault-encrypted secrets, inventory management, idempotent task design |
| **Current state** | `ansible/` — roles for all nodes, all services. `site.yml` converges on 3rd run. VAULT managed via separate playbook due to Unraid SSH constraints. |
| **Gap** | ansible-lint not routinely run. No molecule tests. Secret management has tracked-vault drift. VAULT SSH requires workaround script. |
| **Transferable to** | Any infrastructure — new nodes, new services, new clusters |

### VI.5 — Container Orchestration

| Aspect | Detail |
|---|---|
| **What it is** | Managing Docker containers across nodes |
| **Providers** | Claude Code + Ansible (deployment), Docker MCP (inspection/management) |
| **Proficiency** | Expert (55+ containers managed) |
| **Sub-skills** | Dockerfile authoring (NGC base images, multi-stage builds), docker-compose design, volume mounting, networking, resource limits, health checks, image building |
| **Gap** | No container image registry (images built locally on each node). No automated image rebuilds on dependency updates. No container resource limits enforced. |
| **Transferable to** | Any containerized service |

### VI.6 — Database Design & Management

| Aspect | Detail |
|---|---|
| **What it is** | Designing schemas, queries, and managing database services |
| **Providers** | Claude Code |
| **Proficiency** | Expert |
| **Sub-skills** | Qdrant collection design (dimensions, distance metrics, payload indexes), Neo4j graph modeling (node types, relationship types, Cypher queries, constraints), Redis data structures, PostgreSQL (Gitea backend) |
| **Tools** | Qdrant MCP, Neo4j MCP (cypher queries), Redis MCP, Postgres MCP |
| **Gap** | No database migration framework. No automated backup verification (restore testing). No performance monitoring for database queries. |
| **Transferable to** | Any data-intensive application |

### VI.7 — API Design & Integration

| Aspect | Detail |
|---|---|
| **What it is** | Designing, building, and consuming APIs |
| **Providers** | Claude Code |
| **Proficiency** | Expert |
| **Sub-skills** | RESTful API design, OpenAI-compatible API conformance, SSE streaming, WebSocket, GraphQL (Stash), MCP protocol, FastAPI endpoint design |
| **Current APIs** | Agent Server (/v1/chat, /v1/tasks, /v1/workspace, /v1/agents, /v1/events, etc.), GPU Orchestrator (/status, /zones, /gpu), Dashboard API routes |
| **Gap** | No API documentation (no OpenAPI/Swagger). No API versioning strategy. No rate limiting. |

### VI.8 — Security Engineering

| Aspect | Detail |
|---|---|
| **What it is** | Protecting systems, managing access, auditing |
| **Providers** | Claude Code, CONSTITUTION.yaml (enforcement) |
| **Proficiency** | Practitioner |
| **Sub-skills** | UFW firewall management, SSH key management, bearer token auth, secrets handling, path-scoped file access (agent sandbox), command blocklist, audit logging |
| **Current state** | UFW on all nodes, SSH key auth (passwordless), LiteLLM bearer token, agent execution sandbox (read /workspace, write /output), command blocklist in execution tools |
| **Gap** | No intrusion detection. No automated security scanning. No secrets rotation. HTTPS only on Claudeman (self-signed). Dashboard/agent server on plain HTTP internally. Sentry MCP connected but not configured for Athanor apps. |
| **Transferable to** | Any security-critical system |

### VI.9 — Network Engineering

| Aspect | Detail |
|---|---|
| **What it is** | Designing and managing network infrastructure |
| **Providers** | Shaun (physical layer), Claude Code (configuration) |
| **Proficiency** | Expert (10GbE verified >9.4 Gbps all pairs) |
| **Sub-skills** | VLAN design, SFP+ configuration, NFS mount management, DNS, iperf3 testing, UniFi management |
| **Hardware** | USW Pro XG 10 PoE (.31), all server nodes on SFP+ data plane |
| **Gap** | InfiniBand not deployed (backlog, requires physical work). No network monitoring beyond basic availability. UniFi not integrated with Home Assistant. |

### VI.10 — Testing Strategy & Automation

| Aspect | Detail |
|---|---|
| **What it is** | Designing test suites, test automation, quality gates, and verification strategies |
| **Providers** | Claude Code (design and implementation), Coding Agent (code review) |
| **Proficiency** | Awareness (capability exists but almost nothing is automated) |
| **Sub-skills** | Unit test design (pytest, Jest/Vitest), E2E test design (Playwright), integration testing, load testing, API testing, prompt evaluation (promptfoo), accessibility testing (Chrome DevTools Lighthouse), code review (CodeRabbit skill), TDD methodology |
| **Tools available but unused** | Playwright MCP (full browser automation for E2E tests), Chrome DevTools MCP (Lighthouse accessibility/performance audits), CodeRabbit skill (automated code review), promptfoo (LLM output evaluation), pytest (Python), Jest/Vitest (TypeScript) |
| **Gap** | No test suites exist for any project. No CI/CD pipeline. Promptfoo blocked on API key. Playwright available but not wired for testing. CodeRabbit available but not utilized. This is one of the largest gaps in the system — we build and verify manually every time. |
| **Transferable to** | Any software project. Testing strategy is universal. |

### VI.11 — Meta-Capability Development

| Aspect | Detail |
|---|---|
| **What it is** | Building new capabilities for the system itself — new MCP servers, new Claude Code skills/hooks, new agents, new tools |
| **Providers** | Claude Code (primary) |
| **Proficiency** | Expert |
| **Sub-skills** | MCP server development (anthropic-skills:mcp-builder), Claude Code skill creation (anthropic-skills:skill-creator with evals and benchmarking), hook design (settings.json automation), agent design (LangGraph create_react_agent), tool development (Python tool functions), skill generation from documentation (firecrawl:skill-gen) |
| **Tools** | mcp-builder skill, skill-creator skill (create, modify, eval, benchmark), firecrawl:skill-gen (generate skills from docs), update-config skill (hooks, permissions, env vars) |
| **Current state** | 13 MCP servers deployed, 20+ skills available, 9 agents, hooks system active, `.claude/rules/` for domain-specific guidance |
| **Gap** | No skill performance tracking. No automated skill regression testing. No agent performance comparison framework. Skills evolve but there's no changelog or versioning. |
| **Transferable to** | Any AI agent system. The ability to extend its own capabilities is Athanor's most distinctive meta-property. |

---

## Category VII: Operations

*Maintaining — How do we keep things running and healthy?*

### VII.1 — System Administration

| Aspect | Detail |
|---|---|
| **What it is** | Managing nodes, services, containers, users, filesystems |
| **Providers** | Claude Code (primary), General Assistant (monitoring), Ansible (automation) |
| **Proficiency** | Expert |
| **Sub-skills** | Container lifecycle management, systemd service management, filesystem management, NFS troubleshooting, package management, log analysis |
| **Tools** | Docker MCP, SSH (passwordless to all nodes), Ansible, vault-ssh.py (VAULT workaround) |
| **Gap** | No automated drift detection (are deployed configs matching Ansible state?). VAULT SSH still requires workaround. |

### VII.2 — Monitoring & Observability

| Aspect | Detail |
|---|---|
| **What it is** | Collecting metrics, visualizing health, detecting problems |
| **Providers** | Prometheus (metrics), Grafana (dashboards), Loki (logs), Alloy (collection), DCGM-exporter (GPU), node_exporter (system), LangFuse (LLM traces), Dashboard (custom views) |
| **Proficiency** | Expert |
| **Sub-skills** | PromQL queries, Grafana dashboard design, alert rule authoring, log aggregation, GPU metrics (DCGM), LLM observability (LangFuse per-agent metadata) |
| **Current state** | Prometheus scraping all nodes + DCGM + node_exporter. Grafana with Node Exporter Full + DCGM dashboards. Loki + Alloy for log aggregation. LangFuse tracing all 9 agents. Dashboard monitoring page with live Prometheus data. Backup freshness exporter deployed. |
| **Gap** | No SLA tracking. No automated anomaly detection on metrics. Alert routing limited (ntfy only). No Grafana → dashboard correlation (they're separate views). |

### VII.3 — Backup & Disaster Recovery

| Aspect | Detail |
|---|---|
| **What it is** | Protecting data and recovering from failures |
| **Providers** | Cron scripts, Claude Code (verification), Ansible (deployment) |
| **Proficiency** | Practitioner |
| **Sub-skills** | Qdrant snapshot API, Neo4j Cypher export, appdata tarball, backup freshness monitoring, restore procedures |
| **Schedule** | 03:00 Qdrant → NFS, 03:15 Neo4j export, 03:30 appdata tar (11 services), 6h personal data rsync |
| **Gap** | No restore testing (backups exist but never verified by restoring). VAULT FUSE ENOSPC issue unresolved (cache-drive workaround). No off-site backup. No git repo backup (8 commits ahead of origin, not pushed). |

### VII.4 — Incident Response

| Aspect | Detail |
|---|---|
| **What it is** | Detecting, diagnosing, and resolving production incidents |
| **Providers** | Claude Code (primary), General Assistant (initial detection), Prometheus alerts (notification) |
| **Proficiency** | Expert |
| **Sub-skills** | Alert triage, metrics correlation, service recovery, container restart, NFS stale handle recovery, escalation |
| **Common incidents** | NFS stale handles (VAULT reboot), vLLM OOM (model too large), container drift (stale images), EPYC slow POST (3min ECC check), Blackwell kernel issues |
| **Gap** | No incident tracking system. No postmortem template. No automated remediation (self-healing infrastructure is emergent capability, not formalized). |

### VII.5 — Resource Management & Capacity Planning

| Aspect | Detail |
|---|---|
| **What it is** | Allocating GPU/CPU/memory/storage efficiently, planning for growth |
| **Providers** | Claude Code, GPU Orchestrator (planned Phase 3), Prometheus metrics |
| **Proficiency** | Practitioner |
| **Sub-skills** | GPU VRAM allocation, container resource estimation, storage capacity forecasting, power/thermal budgeting |
| **Current state** | 152 GB VRAM, ~15% average compute utilization. Storage 86% (143T/164T). GPU Orchestrator Phase 2 deployed but sleep/wake non-functional. |
| **Gap** | GPU orchestrator sleep mode blocked (vLLM v0.16.0 limitation). No automated resource right-sizing. No cost tracking (power consumption). Storage at 86% with no automated cleanup policy. |

### VII.6 — Debugging & Troubleshooting

| Aspect | Detail |
|---|---|
| **What it is** | Systematically diagnosing why something doesn't work — code bugs, configuration errors, performance problems, integration failures |
| **Providers** | Claude Code (primary — Expert level), Chrome DevTools MCP (web debugging), Sentry MCP (error tracking) |
| **Proficiency** | Expert |
| **Sub-skills** | Code debugging (reading stack traces, setting up reproduction, bisecting), configuration debugging (checking env vars, volume mounts, network connectivity), performance profiling (Lighthouse, Chrome DevTools performance tracing, memory snapshots), log correlation (Loki + Grafana), GPU debugging (nvidia-smi, DCGM, CUDA errors), network debugging (iperf3, curl, DNS resolution) |
| **Tools** | Chrome DevTools MCP (evaluate_script, list_console_messages, list_network_requests, performance_start_trace, take_memory_snapshot, lighthouse_audit), Sentry MCP (search_issues, get_issue_details, analyze_issue_with_seer, search_events, get_trace_details), Grafana MCP, Docker MCP (container logs), SSH access to all nodes |
| **Gap** | Sentry not configured for Athanor applications (MCP connected but no DSNs set up). No distributed tracing across services (agent request → LiteLLM → vLLM → response). No automated error aggregation or trending. |
| **Transferable to** | Any system — debugging is the most universal engineering skill |

---

## Category VIII: Physical

*Touching — What requires hands, presence, and hardware?*

### VIII.1 — Hardware Installation & Assembly

| Aspect | Detail |
|---|---|
| **Sole provider** | Shaun |
| **Proficiency** | Expert |
| **Sub-skills** | GPU installation (5 GPUs across 2 nodes), SFP+ module installation, NVMe installation, RAM installation, rack mounting, cable management |
| **Recent** | 4x 5070 Ti + 4090 in FOUNDRY, 5090 + 5060 Ti in WORKSHOP, 5060 Ti in DEV |
| **Backlog** | Mining GPU enclosure migration (6.7), Samsung 990 PRO check for 4TB NVMe (blocked on inspection) |

### VIII.2 — Network Physical Layer

| Aspect | Detail |
|---|---|
| **Sole provider** | Shaun |
| **Proficiency** | Expert |
| **Sub-skills** | Patch panel management, SFP+ cable routing, switch configuration (UniFi physical), fiber/DAC selection |
| **Backlog** | InfiniBand cabling (6.2) |

### VIII.3 — Power & Thermal Management

| Aspect | Detail |
|---|---|
| **Sole provider** | Shaun |
| **Proficiency** | Practitioner |
| **Sub-skills** | UPS management, circuit capacity planning, thermal monitoring, GPU power limit tuning |
| **Current** | nvidia-power-limits.service deployed (5070 Ti @ 250W, 4090 @ 320W) |
| **Gap** | No UPS monitoring integration. No power consumption tracking. No thermal alerting beyond GPU temps. |

### VIII.4 — Physical Site Access

| Aspect | Detail |
|---|---|
| **Sole provider** | Shaun (sole, irreplaceable, no delegation possible) |
| **Criticality** | This is the single most critical bottleneck. If Shaun is unavailable and something requires physical access, it waits. |
| **Sub-skills** | Button pressing, cable plugging, drive swapping, visual inspection |
| **Mitigation** | Maximize remote management (IPMI/iDRAC where available, Ansible, SSH). Reduce frequency of physical intervention. |

---

## Category IX: Domain Knowledge

*Knowing — What field-specific expertise informs everything else?*

### IX.1 — Building Science & Energy Efficiency

| Aspect | Detail |
|---|---|
| **Provider** | Shaun (RESNET-certified HERS Rater) |
| **Proficiency** | Authority (professional credential) |
| **Sub-skills** | HERS rating methodology, duct leakage testing, blower door testing, insulation assessment, building envelope analysis, energy code compliance |
| **Business** | Ulrich Energy (S-Corp) — energy efficiency inspections in Twin Cities area |
| **Athanor integration** | `projects/ulrich-energy/` (placeholder), `docs/projects/ulrich-energy/WORKFLOWS.md` (4 automation workflows identified) |
| **Gap** | No automation built yet. Report generation, duct leakage forecasting, scheduling, and compliance tools all identified but not started. |

### IX.2 — Media & Entertainment Ecosystems

| Aspect | Detail |
|---|---|
| **Providers** | Media Agent (Sonarr/Radarr/Plex), Shaun (taste/preferences) |
| **Proficiency** | Practitioner |
| **Sub-skills** | TV/movie metadata understanding, quality profile management, content acquisition workflows, Plex library management, watch history analysis |
| **Gap** | Libraries are empty. Prowlarr needs indexer config. No content recommendation engine. No viewing pattern analysis. |

### IX.3 — Adult Content Domain

| Aspect | Detail |
|---|---|
| **Providers** | Stash Agent (12 tools), Stash (VAULT:9999) |
| **Proficiency** | Practitioner |
| **Sub-skills** | Content scanning, performer identification, tag management, duplicate detection, organization workflows |
| **Gap** | VLM auto-tagging plugin not deployed (AHavenVLMConnector). Face recognition not deployed (LocalVisage). No Qdrant recommendations collection. No NSFW video pipeline. |

### IX.4 — Game Design & Interactive Fiction

| Aspect | Detail |
|---|---|
| **Providers** | Shaun (vision/design), Claude Code (architecture/implementation), EoBQ codebase |
| **Proficiency** | Practitioner (EoBQ deployed with 5 characters, emotional profiles, breaking mechanics) |
| **Sub-skills** | Character system design, emotional arc engineering, branching narrative, intensity calibration, AI-driven dialogue, procedural content generation |
| **Gap** | No formal game design document (design lives in code + session notes). No player testing framework. No analytics. Character memory (Qdrant) planned but not wired. |

### IX.5 — AI/ML Landscape Knowledge

| Aspect | Detail |
|---|---|
| **Providers** | Claude Code (primary — deep awareness of model landscape), HuggingFace MCP |
| **Proficiency** | Expert |
| **Sub-skills** | Model architecture understanding, quantization tradeoffs, inference optimization, vLLM internals, Blackwell-specific constraints, embedding/retrieval techniques |
| **Tools** | HuggingFace MCP (hub_repo_search, paper_search, hf_doc_search), Context7 (library docs) |
| **Gap** | Knowledge decays without active monitoring. No automated new-model-release tracking. |

### IX.6 — Social Matching & Recommendation Systems

| Aspect | Detail |
|---|---|
| **Providers** | Claude Code (design), concept docs |
| **Proficiency** | Awareness (Kindred concept doc exists, no implementation) |
| **Sub-skills** | Dual-embedding architecture, passion-based matching, privacy-first design |
| **Gap** | Entirely unbuilt. Awaiting Shaun's go decision. |

### IX.7 — Financial & Business Operations

| Aspect | Detail |
|---|---|
| **What it is** | Managing business finances, invoicing, expense tracking, tax preparation, S-Corp compliance |
| **Providers** | Shaun (primary — business owner), Claude Code (potential automation) |
| **Proficiency** | Shaun: Practitioner (runs the business). System: None (no automation). |
| **Sub-skills** | Invoice generation, expense categorization, mileage tracking, quarterly tax estimation, annual filing, client scheduling, payment tracking |
| **Available tools (unused)** | anthropic-skills:xlsx (spreadsheet generation for financial reports), anthropic-skills:docx (invoice templates), Google Calendar MCP (scheduling), Gmail MCP (client communications) |
| **Gap** | Complete automation gap. No financial tracking system. No invoice generation pipeline. No expense categorization. No integration with accounting software. This represents one of the highest-value automation opportunities for protecting Shaun's time. |
| **Transferable to** | Any business operations, personal finance, budgeting |

### IX.8 — Emulation & Gaming Infrastructure

| Aspect | Detail |
|---|---|
| **What it is** | Running game servers, emulation platforms, retro gaming systems |
| **Providers** | None |
| **Proficiency** | None |
| **Sub-skills** | Game server deployment (Minecraft, Valheim, etc.), emulator configuration (RetroArch, PCSX2), ROM management, multiplayer networking |
| **Gap** | VISION.md explicitly mentions "game servers, emulation platforms" as future workloads. Nothing exists. Hardware is more than capable. |
| **Transferable to** | Entertainment, social gaming, retro computing preservation |

---

## Category X: Governance & Coordination

*Orchestrating — How do experts connect, cooperate, and stay aligned?*

### X.1 — Constitutional Enforcement

| Aspect | Detail |
|---|---|
| **What it is** | Immutable constraints that no autonomous process can violate |
| **Provider** | `CONSTITUTION.yaml` (static), enforcement layer (planned) |
| **Proficiency** | Deployed (document exists) but not enforced programmatically |
| **Current state** | 17 immutable constraints (data protection, security, infrastructure, autonomy, git). Autonomy spectrum defined. Supervised operations listed. Emergency protocols documented. |
| **Gap** | No runtime enforcement — CONSTITUTION.yaml is a document that Claude and agents are instructed to follow, not a programmatic guard. No audit log. No violation alerting. |

### X.2 — Inter-Agent Coordination

| Aspect | Detail |
|---|---|
| **What it is** | How agents communicate, delegate, and collaborate |
| **Providers** | GWT workspace (Redis, 1Hz competition), task engine (Redis, 5s poll), delegation tools, agent registry |
| **Proficiency** | Practitioner |
| **Sub-skills** | Task submission/routing, salience-based broadcasting, agent capability discovery, delegation, status tracking |
| **Tools** | `POST /v1/tasks`, `delegate_to_agent`, `check_task_status`, GWT workspace (capacity 7, 1Hz cycle), agent registry (`GET /v1/agents/registry`), Redis pub/sub |
| **Gap** | GWT Phase 3 not started (agents subscribing + reacting to broadcasts, coalition formation). No semantic relevance scoring for broadcasts. No conflict resolution between agents. |

### X.3 — Human-System Communication

| Aspect | Detail |
|---|---|
| **What it is** | How Shaun interacts with and is informed by the system |
| **Providers** | Dashboard (primary), Claude Code / Claudeman, Voice, Push notifications, ntfy |
| **Proficiency** | Expert (24-page PWA, 5 lenses, SSE live metrics, generative UI chat) |
| **Sub-skills** | Dashboard design, notification management, voice interaction, mobile responsiveness, push notification delivery |
| **Tools** | Dashboard PWA, Claudeman (HTTPS), HA Wyoming voice, VAPID push notifications, ntfy |
| **Gap** | No unified notification center (ntfy, push, dashboard notifications are separate channels). No notification preferences (which events go where). |

### X.4 — External Integration

| Aspect | Detail |
|---|---|
| **What it is** | Connecting Athanor to external services and platforms |
| **Providers** | Claude Code MCP servers (many) |
| **Proficiency** | Expert (extensive MCP ecosystem) |
| **Available integrations** | Notion (pages, databases, search), Google Calendar (events, scheduling), Gmail (email, drafts), Google Drive (files, search), Vercel (deployments), Netlify (sites), Sentry (error monitoring), HuggingFace (models, papers), Firecrawl (web scraping/research), Playwright (browser automation), Chrome DevTools (debugging), Windows MCP (desktop automation) |
| **Gap** | Most integrations are Claude Code session-only — agents can't use Notion, Calendar, Gmail etc. No persistent integration layer between external services and the agent workforce. |

### X.5 — Documentation & Institutional Memory

| Aspect | Detail |
|---|---|
| **What it is** | Keeping documentation accurate, complete, and useful |
| **Providers** | Claude Code (primary), Knowledge Agent (indexing), `scripts/check-doc-refs.py` (link checking) |
| **Proficiency** | Expert |
| **Sub-skills** | ADR authoring (21+), research documentation, SYSTEM-SPEC maintenance, BUILD-MANIFEST tracking, MEMORY.md session continuity, cross-repo reference checking |
| **Artifacts** | 81+ docs, 21 ADRs, 20+ research docs, design docs, hardware docs |
| **Gap** | MEMORY.md was 10 sessions stale at one point. No automated staleness detection. No doc health dashboard. |

### X.6 — Workforce Management & Trust

| Aspect | Detail |
|---|---|
| **What it is** | Managing agent performance, trust, and autonomy levels |
| **Providers** | Claude Code (COO role), escalation protocol, trust scoring, goals API |
| **Proficiency** | Practitioner |
| **Sub-skills** | Trust score computation (feedback + escalation history), feedback collection (thumbs up/down), goal setting, daily digest generation, autonomy calibration |
| **Tools** | `/v1/trust` (scores), `/v1/feedback` (collection), `/v1/goals` (CRUD), dashboard trust badges, feedback buttons in chat |
| **Gap** | Trust scores don't actually change agent autonomy (they're informational, not enforcement). No dynamic autonomy adjustment based on track record. No agent performance comparison. |

### X.7 — Quality Assurance & Verification

| Aspect | Detail |
|---|---|
| **What it is** | Ensuring code, configs, and systems work correctly |
| **Providers** | Claude Code (manual verification), Coding Agent (code review tool) |
| **Proficiency** | Practitioner |
| **Sub-skills** | TypeScript type checking (`npx tsc --noEmit`), Python syntax checking (`py_compile`), Ansible syntax validation, YAML validation, manual endpoint testing (curl), SSH-and-check verification |
| **Gap** | No automated test suites (no pytest, no Jest/Vitest). No CI/CD. No integration tests. No load testing. Promptfoo eval baseline blocked. Code review available via Coding Agent but not routinely used. CodeRabbit skill available but not utilized. |

---

## Expert Registry — Full Profiles

### Shaun (Human / Owner)

```
Type: human
Availability: ~4 hrs/day Athanor (evenings/weekends, day job constraints)
Cost: HIGHEST — irreplaceable, scarce, protect above all else
Authority: Absolute (vision, taste, judgment, physical, financial)

Expertise:
  I.1 Vision & Direction: Authority
  I.3 Taste & Aesthetic Judgment: Authority
  VIII.1 Hardware Installation: Expert
  VIII.2 Network Physical Layer: Expert
  VIII.3 Power & Thermal: Practitioner
  VIII.4 Physical Site Access: Sole provider
  IX.1 Building Science: Authority (HERS Rater)
  IX.2 Media preferences: Authority (taste)
  IX.4 Game Design vision: Authority
  IX.7 Financial/Business: Practitioner (runs the S-Corp)

Constraints:
  - Day job (Ulrich Energy) limits weekday availability
  - Sole provider for all Physical (VIII) capabilities
  - Travel = total Physical capability loss
  - Judgment calls cannot be automated

Succession:
  - Physical: NONE (wait for Shaun)
  - Vision: NONE (hold decisions for Shaun)
  - Taste: Claude approximates from design system + preferences
```

### Claude Code (Cloud AI / COO)

```
Type: cloud_ai
Availability: 24/7 when internet + API key available
Cost: Medium (API tokens, budget-constrained)
Authority: Operational (architecture, coordination, execution within scope)

Expertise:
  I.2 Architecture & System Design: Expert
  I.4 Operational Decision-Making: Expert
  I.5 Strategic Planning: Expert
  I.6 Prompt Engineering: Expert
  II.1 Web Research: Expert (Firecrawl, WebSearch)
  II.2 Technology Evaluation: Expert
  II.3 Knowledge Retrieval: Expert
  II.6 Data Analysis: Expert
  III.3 Code Generation: Expert
  III.5 Document Creation: Expert (docx, xlsx, pptx, pdf skills)
  III.6 Interface Design: Expert
  III.9 Communication & Writing: Expert
  V.5 Desktop & Browser Automation: Expert
  V.6 External Service Management: Expert
  VI.1-VI.11 All Engineering: Expert
  VII.1 System Administration: Expert
  VII.4 Incident Response: Expert
  VII.6 Debugging: Expert
  X.4 External Integration: Expert (13+ MCP servers)
  X.5 Documentation: Expert

Constraints:
  - Internet outage = total loss
  - API key expiry = total loss
  - Session-bound (no persistence between sessions without memory files)
  - Cannot perform physical tasks
  - Token cost constrains long sessions

Succession:
  - Local agents continue autonomously within boundaries
  - No architecture decisions until Claude restored
  - Operational monitoring via Prometheus/Grafana continues

Unique capabilities (not available to agents):
  - Notion integration (notes, databases, pages, views)
  - Google Calendar management (events, scheduling, free time)
  - Gmail access (search, read, draft, labels)
  - Google Drive access (search, fetch files)
  - Vercel/Netlify deployment management
  - Sentry error monitoring and analysis
  - Browser automation (Playwright, Chrome DevTools)
  - Windows desktop automation (screenshots, clicks, processes)
  - PDF/DOCX/XLSX/PPTX creation and manipulation
  - HuggingFace model/paper search
  - Scheduled task creation
  - Symbolic code analysis (Serena)
  - Plan mode, brainstorming, feature-dev workflows
  - Skill creation and evaluation
  - MCP server development
```

### Local AI Agents (9 total)

```
Type: local_ai (LangGraph create_react_agent, FOUNDRY:9000)
Availability: 24/7 (hardware-dependent)
Cost: LOWEST — free marginal cost (hardware already paid for)
Models: reasoning (Qwen3.5-27B-FP8 TP=4), coder (Qwen3-Coder-30B-A3B-AWQ),
        fast/worker/uncensored (Qwen3.5-35B-A3B-AWQ)

Per-agent profiles:

General Assistant:
  Tools: 9 (4 system + 2 delegation + 3 filesystem)
  Expertise: VII.1 System Admin (Practitioner), V.2 Proactive (30min health)
  Mode: Reactive + Proactive (30min)

Media Agent:
  Tools: 13 (Sonarr + Radarr + Plex)
  Expertise: IV.1 Content Discovery (Practitioner), IV.2 Library (Practitioner), IX.2 Media (Practitioner)
  Mode: Reactive + Proactive (15min)

Home Agent:
  Tools: 8 (HA control)
  Expertise: V.1 Device Control (Practitioner), V.3 Event Response (Practitioner)
  Mode: Reactive + Proactive (5min)

Research Agent:
  Tools: 4 (web search + knowledge)
  Expertise: II.1 Web Research (Practitioner), II.3 Knowledge Retrieval (Practitioner)
  Mode: Reactive

Creative Agent:
  Tools: 5 (ComfyUI image + video)
  Expertise: III.1 Image Gen (Practitioner), III.2 Video Gen (Practitioner)
  Mode: Reactive

Knowledge Agent:
  Tools: 5 (Qdrant + Neo4j)
  Expertise: IV.3 Knowledge Indexing (Practitioner), II.3 Retrieval (Practitioner)
  Mode: Reactive

Coding Agent:
  Tools: 9 (4 coding + 5 execution)
  Expertise: III.3 Code Gen (Practitioner), X.7 QA (Practitioner)
  Mode: Reactive

Stash Agent:
  Tools: 12 (Stash GraphQL)
  Expertise: IX.3 Adult Content (Practitioner), IV.2 Taxonomy (Practitioner)
  Mode: Reactive

Data Curator:
  Tools: 7 (data processing)
  Expertise: IV.5 Personal Data (Practitioner), IV.4 Data Quality (Practitioner)
  Mode: Reactive (6h schedule)
```

### Infrastructure Services

```
LiteLLM (VAULT:4000) — Model routing, alias management, auth
Prometheus (VAULT:9090) — Metrics collection, alerting, PromQL
Grafana (VAULT:3000) — Metrics visualization, dashboards
Loki (VAULT:3100) — Log aggregation, LogQL
Alloy (FOUNDRY + WORKSHOP) — Metrics/log collection agent
Qdrant (FOUNDRY:6333) — Vector search, 9 collections, 2547+ vectors
Neo4j (VAULT:7474) — Graph database, 3095 nodes, 4447 relationships
Redis (VAULT:6379) — Caching, state, pub/sub, task queue, agent registry
ComfyUI (WORKSHOP:8188) — Image/video generation engine
Plex (VAULT:32400) — Media server
Sonarr (VAULT:8989) — TV management
Radarr (VAULT:7878) — Movie management
Prowlarr (VAULT:9696) — Indexer management
SABnzbd (VAULT:8080) — Download client
Home Assistant (VAULT:8123) — Home automation, Wyoming voice
Stash (VAULT:9999) — Adult content management
Gitea (VAULT) — Git hosting
n8n (VAULT:5678) — Workflow automation (not activated)
ntfy (VAULT) — Push notifications
Meilisearch (VAULT) — Full-text search
Miniflux (VAULT) — RSS reader
LangFuse (VAULT:3030) — LLM observability, per-agent tracing
Open WebUI (WORKSHOP:3000) — Direct model chat (legacy)
```

---

## Emergent Capabilities

These only exist when multiple experts combine:

| Capability | Contributing Experts | Breaking Point |
|---|---|---|
| **Institutional Intelligence** | Claude + Knowledge Agent + Qdrant + Neo4j + docs/ | Any knowledge store loss |
| **Ambient Living Environment** | Home Agent + Media Agent + HA + Presence Detection + Plex | HA or presence detection failure |
| **Dynamic Visual Storytelling** | EoBQ + Creative Agent + ComfyUI + Local LLM + Flux + LoRA | Any link in generation pipeline |
| **Self-Monitoring Infrastructure** | Prometheus + Grafana + Loki + Alloy + ntfy + Dashboard | Prometheus or Grafana down |
| **Autonomous Workforce** | 9 Agents + Task Engine + GWT Workspace + Redis + Proactive Scheduler | Agent Server or Redis failure |
| **Hybrid AI Reasoning** | Claude (cloud) + Local LLMs + LiteLLM routing + MCP bridge | Internet or LiteLLM failure |
| **Knowledge Synthesis Pipeline** | Research Agent + Knowledge Agent + Embedding Model + Qdrant + Neo4j + HippoRAG | Embedding model or Qdrant failure |
| **Personal Data System** | Data Curator + Qdrant + Neo4j + indexing scripts + Dashboard | Any indexing failure |
| **Unified Operator Experience** | Dashboard + SSE stream + Lens modes + Agent chat + Generative UI | Dashboard or SSE failure |

---

## Cross-Cutting Dimensions (Populated)

### Information Flow Topology

| Pattern | Description | Active Examples |
|---|---|---|
| **Broadcast** | One → all subscribed | GWT workspace: agent broadcasts to `athanor:workspace:broadcast` channel. Dashboard SSE: system state → all connected clients. |
| **Query** | Pull on demand | Agent → Qdrant: semantic search. Agent → LiteLLM → vLLM: inference request. Dashboard → Prometheus: metrics query. |
| **Stream** | Continuous flow | Prometheus → Grafana: metrics every 15s. Alloy → Loki: log stream. Dashboard SSE → browser: 5s system state updates. |
| **Escalation** | Upward when confidence is low | Agent (confidence < 0.5) → notification queue → Dashboard/push → Shaun. Agent → Claude (via task API or MCP bridge) for complex decisions. |
| **Cascade** | Action triggers downstream actions | New episode (Sonarr) → Media Agent detects → GWT broadcast → Home Agent dims lights → Dashboard activity feed updates. |
| **Silo** | Intentionally isolated | Stash Agent data stays within Stash scope. Ulrich Energy data separate from personal data. CONSTITUTION.yaml read-only to all. |

**Bottlenecks:**
- All agent inference routes through LiteLLM → single point of routing failure
- Claude Code is the sole bridge to external services (MCP servers)
- All agent coordination routes through Redis — Redis failure breaks GWT, tasks, and registry

### Temporal Model

| Expert | Available | Peak | Degraded When |
|---|---|---|---|
| **Shaun** | Evenings (6-11PM), weekends | Focused weekend mornings | Day job hours (8-5), travel, family commitments |
| **Claude Code** | 24/7 (session-based) | Active session with Shaun | Between sessions (no operational decisions), internet outage |
| **Local Agents** | 24/7 (always-on) | Off-peak (low queue contention) | Heavy inference load (queue depth > 64), GPU thermal throttle |
| **Proactive Scheduler** | 24/7 (background) | 3-6 AM (backups, consolidation) | Competing with interactive requests during peak hours |
| **Creative Pipeline** | On-demand (GPU shared) | When 5060 Ti is idle | During video generation (Wan2.2 consumes full VRAM) |
| **Dashboard** | 24/7 (static deployment) | Always consistent | Workshop node down = dashboard down |

**Key temporal gaps:**
- Between Claude Code sessions (~20 hrs/day), system runs on autopilot with limited decision-making
- Shaun's ~4 hrs/day constrains all Physical (VIII) work and all vision/taste decisions
- No overnight build capability (Claude squad exists but not routinely used for autonomous builds)

### Cost & Scarcity Model

| Expert | Cost Type | Relative Cost | Substitution Path |
|---|---|---|---|
| **Shaun's time** | Opportunity cost (irreplaceable) | **$$$$$** | Maximize automation. Never waste on tasks agents can do. Batch physical work. |
| **Claude Code (API)** | Tokens ($/session) | **$$$** | Delegate mechanical work to local models via MCP bridge. Use Local Coder subagent. |
| **Local LLM inference** | Electricity (~$0.15/kWh) | **$** | Free marginal cost. Use heavily for boilerplate, review, research. |
| **Infrastructure services** | Hardware amortization + power | **$** | Already paid for. Minimal marginal cost per query. |
| **External MCP services** | Free tier / API costs | **$** | Gmail, Calendar, Notion, Drive all free tier. HuggingFace free. |
| **Physical hardware** | Capital cost (purchased) | **$$$$$** (sunk) | 8 GPUs, 4 nodes, 164TB storage — significant investment, treat carefully |

**Cost optimization principles:**
1. Route mechanical work to local models first (free)
2. Use Claude for architecture, novel problems, complex reasoning (expensive but irreplaceable)
3. Protect Shaun's time above all — his 4 hrs/day is the scarcest resource
4. Infrastructure is sunk cost — utilize it (15% average GPU utilization is wasteful)

### Evolution & Learning Mechanisms

| Mechanism | How It Works | Current State |
|---|---|---|
| **Feedback loop** | Agent acts → user responds → preference stored → agent improves | Deployed: preferences collection, thumbs up/down, "remember" statements. Not yet closing the loop (preferences queried but don't modify behavior). |
| **Knowledge accumulation** | New information indexed → available to all agents | Deployed: indexing scripts, Qdrant, Neo4j. Gap: manual indexing, no cron. |
| **Tool acquisition** | New tool added → existing expert gains capability | Deployed: 13 MCP servers added over 56 sessions. Process is manual (Claude builds, deploys). |
| **Composition discovery** | Experts combined for first time → emergent capability | Organic: ambient living environment, dynamic visual storytelling emerged during builds. Not formalized. |
| **Proficiency graduation** | Repeated success → increased autonomy/trust | Planned: trust scores exist but don't change agent autonomy. No graduation criteria defined. |
| **Degradation detection** | Skills atrophy, docs go stale | Partial: backup freshness exporter catches backup staleness. MEMORY.md staleness caught manually. No general freshness system. |
| **Self-improvement loop** | System benchmarks itself → proposes improvements | Deployed: 5:30 AM benchmark cycle → pattern detection → proposals → Goals page. Not yet acting on proposals autonomously. |

**Proficiency graduation criteria (proposed):**

| From → To | Criteria |
|---|---|
| None → Awareness | Research document exists, options evaluated |
| Awareness → Practitioner | Deployed, handles standard cases, basic documentation |
| Practitioner → Expert | 50+ successful operations, edge case documentation, recovery procedures documented, gotchas captured |
| Expert → Authority | Teaches/informs other experts, innovates beyond standard patterns, defines best practice |

---

## Gap Analysis — Critical

### Single Points of Failure
1. **Shaun** — sole provider of Physical (VIII.1-VIII.4), Vision (I.1), Taste (I.3), Financial (IX.7)
2. **Claude Code** — sole provider of Architecture (I.2), all Engineering (VI), most Operations (VII), external service management (V.6)
3. **Internet** — Claude Code + all MCP integrations + Firecrawl research
4. **FOUNDRY** — 5/8 GPUs, agent server, coordinator model, Qdrant
5. **Redis** — GWT workspace, task queue, agent registry, trust scores, goals

### Unmanned Expertise Areas (None level)
- III.7 Music & Audio Production
- III.8 3D Asset Creation
- IX.8 Emulation & Gaming Infrastructure

### Blocked Capabilities
- qBittorrent (NordVPN creds)
- Quality Cascade cloud escalation (Anthropic API key)
- Google Drive personal data (OAuth)
- Photo VLM analysis (vLLM 0.17+)
- n8n intelligence pipeline (Shaun must activate)
- HA depth (Shaun must configure Lutron + UniFi)
- Kindred (Shaun go decision)

### Proficiency Gaps (Awareness when Practitioner+ needed)
- II.4 Pattern Recognition (designed, not implemented — Layer 3)
- II.5 Market Intelligence (RSS configured, not automated)
- VI.10 Testing Strategy (tools available, nothing automated)
- X.1 Constitutional Enforcement (document, not runtime guard)
- X.6 Dynamic Trust/Autonomy (informational, not enforcement)

### Integration Gaps
- MCP servers (Notion, Calendar, Gmail, Drive, etc.) are Claude-session-only — agents can't use them
- No cross-domain taxonomy (media tags ≠ knowledge tags ≠ Stash tags)
- No unified notification center (ntfy, push, dashboard are separate)
- No distributed tracing across services
- No automated testing of any kind
- Sentry connected but not configured for Athanor apps

### Highest-Value Automation Opportunities
1. **Ulrich Energy business tools** (IX.7) — invoicing, scheduling, reports protect Shaun's time
2. **Testing automation** (VI.10) — eliminate manual verification, catch regressions
3. **Knowledge re-indexing on cron** (IV.3) — currently manual
4. **MCP bridge to agents** (X.4) — unlock external service access for agents
5. **Pattern recognition jobs** (II.4) — close the feedback loop

---

## Growth Model — How New Projects Absorb

When a new project appears (e.g., personal finance tracker, recipe system, podcast manager):

1. **Map required expertise** — which of the 10 categories does it need?
2. **Check existing coverage** — do we have providers at Practitioner+ for each?
3. **Identify gaps** — what new tools, integrations, or domain knowledge is needed?
4. **Compose agents** — either assign to existing agents or create a new one composed of existing expertise types
5. **Add domain knowledge** — only Category IX needs expansion; all other categories are transferable
6. **Deploy** — Ansible role + docker-compose + agent registration

Example: **Personal Finance Tracker**
- II.1 Research (find deals, monitor accounts) — ✅ Research Agent
- II.6 Data Analysis (spending analysis, trends) — ✅ Claude Code
- IV.1 Discovery (transaction monitoring) — needs new data source integration
- IV.2 Taxonomy (categorize transactions) — ✅ Curation expertise exists
- IV.4 Data Quality (reconciliation) — ✅ Data Curator pattern
- II.4 Pattern Recognition (spending analysis) — ⚠ not implemented
- V.2 Scheduled (regular imports) — ✅ Proactive scheduler
- V.6 External Service (bank API integration) — ⚠ Claude-session-only
- X.3 Communication (dashboard page) — ✅ Dashboard pattern
- IX.new Finance domain knowledge — ❌ new Category IX entry

The framework absorbs it without restructuring.

---

## Implementation Plan

### Phase 1: Document (this spec)
- Write the Capability Codex as `docs/design/capability-codex.md`
- Commit and index in knowledge base

### Phase 2: Gap Prioritization
- Score each gap by impact × urgency × feasibility
- Add top gaps to BUILD-MANIFEST as new tier items
- Cross-reference with existing blockers

### Phase 3: Agent Architecture Review
- Evaluate whether 9 agents is optimal based on expertise overlap and gaps
- Consider: should MCP integrations be accessible to local agents?
- Consider: should pattern recognition (II.4) be a new agent or an enhancement to existing ones?
- Consider: should constitutional enforcement (X.1) become a runtime service?

### Phase 4: Living Document
- Knowledge Agent indexes the Codex
- Proficiency levels updated as capabilities change
- Gap analysis refreshed each session via automated audit
- New projects mapped against the framework before building

### Verification
- Cross-reference Codex against SYSTEM-SPEC.md for consistency
- Validate all listed tools/endpoints are actually deployed
- Confirm proficiency assessments against real system behavior
- Test growth model by mapping Kindred against the framework

---

*The Codex is the furnace's inventory of what it can transform — and what it cannot yet.*

*Last updated: 2026-03-23*
