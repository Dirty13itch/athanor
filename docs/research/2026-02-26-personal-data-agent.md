# Personal Data Agent: Local 24/7 Autonomous Data Management

*Research Date: 2026-02-26*

## Problem Statement

Shaun has personal and professional data scattered across:
- **Google Drive** (unknown volume, includes old Hydra/Kaizen AI system configs)
- **C:\Documents\** — Athanor reference docs, Work (energy audit PDFs), Finance
- **C:\Downloads\** — BKI Tracker spreadsheets, athanor-complete-context.md (1,509 lines of strategic vision never committed), handoff-instructions.md
- **C:\Desktop\** — Property address folders (energy audits), AI/Duct Leakage Forecasting
- **D:\ (old Windows OS drive)** — Old ComfyUI/SwarmUI, HuggingFace model cache, ChatGPT Files (SOVEREIGN_DUMP_001, MASTER LISTS, Facebook Data, Online Data, UEA business data, performer databases), 150+ files in Downloads
- **VAULT /mnt/user/** — hydra/kaizen snapshots, media library

**Need:** A 24/7 autonomous system running entirely on local hardware (zero API fees) that discovers, catalogs, parses, analyzes, indexes, and keeps personal data searchable and organized. Must handle PDFs, spreadsheets, Word docs, images, plain text, JSON, and markdown.

## Options Evaluated

### Option 1: Khoj (Self-Hosted Personal AI)

**What:** Open-source personal AI assistant. Self-hostable via Docker. Supports local LLMs via OpenAI-compatible API (works with vLLM/LiteLLM directly).

**Pros:**
- Designed specifically as personal knowledge assistant
- Docker deployment, PostgreSQL + pgvector backend
- Supports vLLM/LiteLLM via `openai_chat_model_name` config pointed at our LiteLLM proxy
- RAG search over uploaded documents
- Chat interface with context from personal data
- Automation API for scheduled tasks
- Active development (8.5k+ GitHub stars)

**Cons:**
- **NO Google Drive connector** — only Notion and GitHub (deprecated) as integrations
- Data ingestion limited to manual upload or API push
- No workflow automation / ETL pipeline
- Would need rclone + custom sync script to feed it
- Another Docker service to maintain (8GB RAM / 16GB VRAM recommended)
- Duplicates what our agent framework already does (RAG, chat, Qdrant)

**Verdict:** Too limited for our needs. No native connectors, and it duplicates our existing agent infrastructure.

### Option 2: n8n (Self-Hosted Workflow Automation)

**What:** Self-hosted workflow automation platform with 400+ integrations. Has AI Agent nodes, RAG chatbot capabilities, local LLM support.

**Pros:**
- **Google Drive connector** (native, OAuth-based, triggers on file changes)
- 400+ integrations (Google Drive, Slack, email, databases, APIs)
- AI Agent node supports OpenAI-compatible endpoints (our LiteLLM)
- Visual workflow builder — Shaun can modify flows
- Cron triggers for scheduled runs
- Can chain: Google Drive watch → download → parse → embed → Qdrant upsert
- Lightweight (Node.js, SQLite or PostgreSQL backend)
- Very active (50k+ GitHub stars)
- MCP server support (experimental)

**Cons:**
- Not purpose-built for document analysis (more of an ETL tool)
- AI Agent capabilities are basic compared to our LangGraph agents
- Another service to deploy and maintain
- Visual workflow can't express complex analysis logic easily
- Doesn't replace need for document parsing libraries
- License: Source-available (not fully OSS), fair-use for personal

**Verdict:** Best integration story. Would serve as the sync/ETL layer feeding data into our existing agent framework. Not a replacement for agents — a complement.

### Option 3: RAGFlow (Document Intelligence)

**What:** Open-source RAG engine with "DeepDoc" vision model for complex document parsing (tables, layouts, forms, scanned PDFs).

**Pros:**
- Best-in-class document parsing (DeepDoc handles PDFs with tables, forms, figures)
- Chunking strategies: naive, QA-pair, table, knowledge graph
- Supports local LLMs via OpenAI-compatible API
- Docker Compose deployment
- Elasticsearch + MinIO backend

**Cons:**
- **No Google Drive connector** — file upload only
- Heavy resource requirements (Elasticsearch, Redis, MinIO, Infinity embedding)
- Focused on Q&A, not autonomous analysis/organization
- Doesn't integrate with existing Qdrant (uses its own vector store)
- Complex deployment, many moving parts
- Would duplicate our knowledge pipeline

**Verdict:** Overkill for our needs. DeepDoc is impressive but we can use pymupdf/camelot for PDF parsing. Doesn't solve the sync problem.

### Option 4: AnythingLLM (Simple Document Chat)

**What:** Simplest self-hosted LLM document chat. Upload files, ask questions.

**Pros:**
- Simplest setup of all options
- Supports local LLMs (LM Studio, Ollama, OpenAI-compatible)
- Multi-user, workspaces
- Built-in vector store (LanceDB)

**Cons:**
- No Google Drive connector
- No automation, no scheduling, no ETL
- No autonomous analysis capability
- Just a chat UI with document context
- Duplicates our dashboard chat

**Verdict:** Too simple. Just a chat wrapper, no autonomous capabilities.

### Option 5: Letta (ex-MemGPT — Persistent Memory Agents)

**What:** Stateful AI agents with persistent memory. Successor to MemGPT.

**Pros:**
- Persistent memory across conversations (core memory + archival memory)
- Agent framework with tools
- Self-hostable
- Can create long-running autonomous agents

**Cons:**
- Focused on conversational memory, not document ingestion
- No file system connectors, no Google Drive
- Immature compared to our LangGraph agents
- Would compete with our existing agent framework
- Python SDK, needs custom integration

**Verdict:** Interesting memory architecture but doesn't solve data sync/ingestion. Our agents already have persistent memory via Qdrant.

### Option 6: Native Data Curator Agent (Build In-House)

**What:** 9th agent in existing Athanor framework. Uses rclone for Google Drive sync, adds multi-format document parsing, schedules continuous indexing.

**Architecture:**
```
rclone (cron) → /mnt/vault/personal-data/ (NFS)
                    ↓
Data Curator Agent (Node 1:9000)
  ├── File watcher (inotify or polling)
  ├── Multi-format parser (pymupdf, python-docx, openpyxl, beautifulsoup4)
  ├── LLM analysis (Qwen3-32B via LiteLLM — zero API cost)
  ├── Embedding (Qwen3-Embedding-0.6B)
  ├── Qdrant upsert (knowledge + personal_data collections)
  ├── Neo4j relationships (Person → Document → Topic)
  └── Classification/tagging
```

**Pros:**
- Zero new infrastructure — uses existing agents, Qdrant, LiteLLM, Qwen3-32B
- Zero API fees — everything runs on local GPUs
- 24/7 via existing scheduler (configurable interval)
- Full control over parsing, analysis, and indexing logic
- Integrates with existing context injection (all agents benefit)
- rclone handles Google Drive sync (installed, needs OAuth)
- Can also scan C:\, D:\ via WSL mount points (/mnt/c, /mnt/d)
- Shaun already understands the agent architecture
- Can delegate to other agents (creative for images, coding for code files)

**Cons:**
- Development effort (~2-3 sessions to build)
- Need to add document parsing deps to agent server (pymupdf, python-docx, openpyxl)
- rclone OAuth requires one-time browser auth from Shaun
- WSL mount performance for C:\D:\ scanning (acceptable for batch)

**Verdict:** Best fit. Leverages everything we already have. No new services. Zero ongoing cost.

## Quantitative Comparison

| Criteria | Khoj | n8n | RAGFlow | AnythingLLM | Letta | Native Agent |
|----------|------|-----|---------|-------------|-------|-------------|
| Google Drive sync | No | **Yes** | No | No | No | **Yes** (rclone) |
| Local file scanning | No | **Yes** | No | Upload only | No | **Yes** |
| Document parsing quality | Basic | Basic | **Best** | Basic | None | Good (pymupdf) |
| Local LLM support | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Autonomous scheduling | Basic | **Yes** | No | No | No | **Yes** |
| Zero new infra | No | No | No | No | No | **Yes** |
| Zero API cost | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |
| Qdrant integration | No | Possible | No | No | No | **Native** |
| Development effort | Low | Low | Medium | Lowest | Medium | **Medium** |
| Maintenance burden | Medium | Medium | High | Low | Medium | **Lowest** |
| Agent delegation | No | Limited | No | No | Yes | **Yes** |

## Recommended Approach

### Primary: Native Data Curator Agent (Option 6)

Build a 9th agent with these tools:
1. `scan_directory` — Recursive file discovery with filters
2. `parse_document` — Multi-format extraction (PDF, DOCX, XLSX, HTML, TXT, MD, JSON, images via VLM)
3. `analyze_content` — LLM-powered classification, summarization, entity extraction
4. `index_document` — Embed and upsert to Qdrant
5. `graph_relationships` — Neo4j entity/topic linking
6. `sync_gdrive` — Trigger rclone sync
7. `get_scan_status` — Progress and statistics
8. `search_personal` — Semantic search across personal data

### Supplementary: rclone for Google Drive

rclone v1.73.1 already installed at `~/.local/bin/rclone`. Config steps:
1. Shaun runs `rclone config` → choose Google Drive → browser OAuth
2. Cron job: `rclone sync gdrive: /mnt/vault/personal-data/gdrive/ --transfers 4`
3. Data curator agent watches the sync target directory

### Supplementary: n8n (Optional, Later)

If Shaun wants broader automation (email triggers, calendar sync, etc.), n8n can be added as a lightweight Node.js service on VAULT. But for the core personal data use case, the native agent is sufficient.

## Implementation Plan

### Phase 1: Foundation (1 session)
- Add document parsing deps to agent server (`pymupdf`, `python-docx`, `openpyxl`, `beautifulsoup4`)
- Create `personal_data` Qdrant collection (1024-dim, Cosine)
- Create data-curator agent with scan/parse/index tools
- Add to scheduler (6-hour interval for full scan, continuous for new files)

### Phase 2: Content Ingestion (1 session)
- Scan and index all local data (C:\, D:\ via WSL mounts)
- Copy `athanor-complete-context.md` to repo and index
- Parse BKI Tracker spreadsheets, energy audit PDFs
- Index old Hydra/Kaizen configs for historical reference

### Phase 3: Google Drive (needs Shaun)
- Shaun completes rclone OAuth (one-time, browser-based)
- Set up cron sync to `/mnt/vault/personal-data/gdrive/`
- Agent watches sync target, indexes new/changed files

### Phase 4: Intelligence (1 session)
- LLM-powered document classification and tagging
- Neo4j relationship graphs (Person → Document → Topic → Project)
- Dashboard page: Personal Data browser with semantic search
- Cross-reference: link personal data to agent knowledge

## Best Local Models for Document Work

Already deployed and sufficient:
- **Qwen3-32B-AWQ** (Node 1, TP=4) — Analysis, classification, summarization, entity extraction
- **Qwen3-Embedding-0.6B** (Node 1, GPU 4) — Vector embeddings for semantic search

Future upgrades (no action needed now):
- **Qwen3.5-27B** (multimodal VLM) — Once vLLM 0.17+ deployed, can do OCR/image analysis natively
- **Qwen2.5-VL-7B** — Lighter VLM for image-heavy documents, could run on 5060 Ti

## Cost Analysis

| Component | One-Time | Ongoing |
|-----------|----------|---------|
| Development | ~3 sessions | 0 |
| API fees | $0 | **$0** |
| Additional hardware | $0 | $0 |
| Additional services | 0 new containers | 0 |
| Storage | ~10-50 GB on VAULT | Grows with data |

**Total ongoing cost: $0/month.** Everything runs on existing hardware with existing models.

## Decision

**Build the native Data Curator agent.** It's the only option that:
1. Requires zero new infrastructure
2. Costs nothing to run
3. Integrates natively with all existing agents and data stores
4. Supports all data sources (local files + Google Drive via rclone)
5. Can be extended incrementally without architectural changes

---

*Last updated: 2026-02-26*
