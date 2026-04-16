# Personal Data Analysis & Organization Tools: Local AI for Continuous Knowledge Extraction

*Research: 2026-02-26*
*Status: Complete -- recommendation ready*
*Unblocks: Tier 10 -- Personal Knowledge Graph, Google Drive integration, autonomous data analysis*

---

## Context

Shaun has extensive personal data in Google Drive (old project files from "Hydra" and "Kaizen" -- previous iterations of Athanor -- plus personal documents, notes, etc.) and wants a system that runs 24/7 on the homelab analyzing this data, extracting insights, building a personal knowledge graph, and making everything searchable/actionable through the existing agent framework.

### Requirements

1. Connect to Google Drive + local files + GitHub and index/analyze them locally
2. Run fully local with local LLMs (no cloud API required)
3. Run 24/7 autonomously -- not just on-demand Q&A
4. Self-hosted, Docker-deployable
5. Must integrate with existing Athanor infrastructure: Qdrant, LiteLLM, LangGraph agents, Redis, Neo4j

### Existing Infrastructure

| Component | Status | Relevance |
|-----------|--------|-----------|
| Qdrant (Node 1:6333) | 2220 vectors, 1024-dim Cosine | Vector store for knowledge |
| LiteLLM (VAULT:4000) | Routing to vLLM instances | Inference gateway |
| vLLM (Node 1:8000) | Qwen3-32B-AWQ, TP=4 | Primary inference |
| Neo4j (VAULT:7474) | Deployed | Knowledge graph DB |
| Redis (VAULT:6379) | AOF, 512MB | Task queue, agent state |
| 8 LangGraph agents (Node 1:9000) | Live, including knowledge-agent | Agent framework |
| index-knowledge.py | 81 files, 922 vectors | Current indexer (docs only) |
| Embedding: Qwen3-Embedding-0.6B | Node 1:8001 | 1024-dim embeddings |

### Hardware Available

| Node | CPU | RAM | GPUs | Available for this workload |
|------|-----|-----|------|----|
| Foundry (.244) | EPYC 56C/112T | 224 GB | 4x 5070 Ti + 4090 (88 GB) | Yes, GPU 4 has headroom |
| Workshop (.225) | TR 7960X 24C/48T | 128 GB | 5090 + 5060 Ti (48 GB) | Possible secondary |

---

## Tool-by-Tool Evaluation

### 1. Khoj (khoj-ai/khoj)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 32.5k |
| Latest Version | v1.41.0 (Feb 2026) |
| License | AGPL-3.0 |
| Development | Very active (weekly releases) |

**Architecture:** Django + PostgreSQL (pgvector) + SearXNG for web search. Runs as a single server with scheduled automation support.

**Connectors:**
- File upload (PDF, Markdown, Org-mode, Word, images)
- Notion (native integration)
- GitHub (native but **deprecated/unmaintained**)
- **Google Drive: NOT SUPPORTED** -- no native connector

**Local LLM Support:** YES. Supports any OpenAI-compatible API including vLLM, LiteLLM, Ollama. Configuration via admin panel: set base_url to LiteLLM proxy, specify model name.

**Autonomous Scheduling:** YES. Cron-based automations that run queries on schedule and deliver results via email. Requires Resend email service setup for self-hosted instances.

**Docker:** YES. `docker-compose.yml` with pgvector, searxng, sandbox (terrarium), and the khoj server on port 42110. Five persistent volumes.

**Resources:** ~4 GB RAM minimum, grows with usage. No GPU required (uses external LLM API).

**Continuous Re-indexing:** Limited. Files must be uploaded via API or web interface. No directory watching or automatic file discovery.

**Verdict:** Strong scheduling/automation capabilities and LiteLLM integration. However, the lack of Google Drive connector and limited file ingestion pipeline make it unsuitable as the primary tool. Could serve as an additional Q&A/automation layer on top of indexed data.

**Sources:**
- [Khoj GitHub](https://github.com/khoj-ai/khoj)
- [Khoj Automations Docs](https://docs.khoj.dev/features/automations/)
- [Khoj Data Sources](https://docs.khoj.dev/category/data-sources/)
- [Khoj OpenAI Proxy Setup](https://docs.khoj.dev/advanced/use-openai-proxy/)
- [Khoj LiteLLM Integration](https://docs.khoj.dev/advanced/litellm/)
- [Khoj Self-Host Setup](https://docs.khoj.dev/get-started/setup/)

---

### 2. RAGFlow (infiniflow/ragflow)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 73.6k |
| Latest Version | v0.24.0 (Feb 2025), nightly builds active |
| License | Apache 2.0 |
| Development | Very active (weekly commits, 2026 roadmap published) |

**Architecture:** Python (FastAPI) + Elasticsearch/Infinity for retrieval + DeepDoc for document parsing + MinIO for object storage. Multi-container Docker deployment.

**Connectors (as of v0.22.0+):**
- **Google Drive: YES** (native, with automatic sync)
- AWS S3 (and S3-compatible like MinIO)
- Notion
- Confluence
- Discord
- Gmail (v0.23.0+)
- Dropbox (v0.23.0+)
- WebDAV (v0.23.0+)
- Airtable (v0.23.0+)
- Google Cloud Storage (v0.23.0+)
- Zendesk, Bitbucket, JIRA (v0.24.0+)
- Local file upload (PDF, DOC, DOCX, TXT, MD, MDX, CSV, XLSX, PPT, PPTX, images)

**Local LLM Support:** YES via Ollama, Xinference, LocalAI. OpenAI-compatible API support through these intermediaries. Direct vLLM/LiteLLM integration requires Xinference or Ollama as proxy, or the OpenAI-compatible model config.

**Autonomous Scheduling:** YES. Data sources auto-sync on configurable schedules. Document parsing runs automatically on new files.

**Docker:** YES. Full `docker-compose.yml` with ragflow-server, Elasticsearch, MinIO, MySQL. GPU-accelerated option via `DEVICE=gpu` in `.env`.

**Resources:** 4+ CPU cores, 16+ GB RAM, 50+ GB disk. Docker image ~7 GB unpacked. `vm.max_map_count >= 262144` required for Elasticsearch.

**Continuous Re-indexing:** YES. Native data source sync from Google Drive and other connectors. Automatic document processing on new/changed files.

**DeepDoc Parser:** RAGFlow's key differentiator. Vision-based document understanding that handles tables, layouts, headers, footers, figures, and complex formatting far better than naive text extraction. Supports MinerU 2.6.3 and Docling as PDF parsing backends.

**Verdict:** **STRONGEST tool for the core use case.** Native Google Drive connector with auto-sync, best-in-class document parsing (DeepDoc), automatic re-indexing, and Docker deployment. The main concern is resource overhead (Elasticsearch, MinIO, MySQL add up) and that it uses its own vector store rather than Qdrant. Integration with existing infrastructure would require an API bridge or data export pipeline.

**Sources:**
- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [RAGFlow v0.22.0 Data Sources](https://medium.com/@infiniflowai/ragflow-0-22-0-newly-supported-data-sources-enhanced-parser-agent-optimizations-and-admin-u-cad724d5992b)
- [RAGFlow v0.23.0 Release](https://ragflow.io/blog/ragflow-0.22.0-data-source-synchronization-enhanced-parser-agent-optimization-and-admin-ui)
- [RAGFlow Docs](https://ragflow.io/docs)
- [RAGFlow Local LLM Deploy](https://github.com/infiniflow/ragflow/blob/main/docs/guides/models/deploy_local_llm.mdx)
- [RAGFlow 2026 Roadmap](https://github.com/infiniflow/ragflow/issues/12241)

---

### 3. PrivateGPT (zylon-ai/private-gpt)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 57k |
| Latest Version | v0.6.2 |
| License | Apache 2.0 |
| Development | Active but slowing (last repo update Nov 2024, pivoting to enterprise Zylon) |

**Connectors:** File upload only. No Google Drive, no GitHub, no cloud connectors.

**Local LLM:** YES. llama-cpp-python, Ollama, various backends. Supports Gemini as of v0.6.0.

**Scheduling:** NO. Purely reactive document Q&A.

**Docker:** YES. Environment-specific profiles (CPU, CUDA, macOS).

**Resources:** Moderate. Runs its own embedding model.

**Continuous Re-indexing:** NO. Batch ingestion only.

**Verdict:** Document Q&A tool, not a data analysis platform. No connectors, no scheduling, no autonomy. The project is pivoting toward enterprise (Zylon), and community development has slowed. **Not recommended.**

**Sources:**
- [PrivateGPT GitHub](https://github.com/zylon-ai/private-gpt)
- [PrivateGPT v0.6.0](https://www.zylon.ai/blog/privategpt-v0-6-0-recipes)
- [PrivateGPT Docker](https://hub.docker.com/r/zylonai/private-gpt)

---

### 4. Quivr (QuivrHQ/quivr)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 38.8k |
| Latest Version | core-0.0.33 (Feb 2026) |
| License | Apache 2.0 |
| Development | Active but pivoting to SaaS (quivr.com = customer support automation) |

**Connectors:** Google Drive (mentioned in marketing), SharePoint, Dropbox, URLs, file upload. However, the project has pivoted significantly from "second brain" to enterprise RAG platform.

**Local LLM:** YES via Ollama. Any OpenAI-compatible endpoint.

**Scheduling:** NO built-in scheduling or autonomous mode.

**Docker:** YES but self-host documentation has degraded as focus shifted to cloud platform.

**Resources:** Moderate. Uses Supabase (Postgres + pgvector) or PGVector directly.

**Continuous Re-indexing:** Limited. No native file watching or automatic sync.

**Verdict:** The "second brain" pitch is now marketing for an enterprise SaaS product. Self-hosted version is falling behind the cloud offering. The Google Drive connector exists but reliability for self-hosted is uncertain. **Not recommended** due to project direction drift.

**Sources:**
- [Quivr GitHub](https://github.com/QuivrHQ/quivr)
- [Quivr Docs](https://docs.quivr.app/intro)
- [Quivr LiteLLM Integration](https://docs.litellm.ai/docs/projects/Quivr)

---

### 5. AnythingLLM (Mintplex-Labs/anything-llm)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 53k |
| Latest Version | Active (continuous releases) |
| License | MIT |
| Development | Very active |

**Connectors:** Confluence, GitHub, YouTube, file upload. **Google Drive: NOT SUPPORTED** (feature requested since 2023, not implemented).

**Local LLM:** YES. 30+ providers including Ollama, vLLM direct, LiteLLM. Best LLM flexibility of any tool evaluated.

**Scheduling:** Limited. Hourly file sync for watched files, 7-day stale marking.

**Docker:** YES. MCP compatibility in Docker mode.

**Resources:** Light-moderate. No heavy dependencies.

**Continuous Re-indexing:** YES for watched files (hourly check). Individual files only, not directories.

**Verdict:** Best all-in-one desktop/Docker AI app for document chat. However, no Google Drive connector and limited autonomous capabilities make it a poor fit for the 24/7 continuous analysis requirement. Good as a supplementary Q&A interface.

**Sources:**
- [AnythingLLM GitHub](https://github.com/Mintplex-Labs/anything-llm)
- [AnythingLLM Document Sync](https://docs.anythingllm.com/beta-preview/active-features/live-document-sync)
- [AnythingLLM Google Drive Request](https://github.com/Mintplex-Labs/anything-llm/issues/119)
- [AnythingLLM Setup Guide 2026](https://localaimaster.com/blog/anythingllm-setup-guide)

---

### 6. Mem0 (mem0ai/mem0)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | ~23k |
| Latest Version | Active (2026) |
| License | Apache 2.0 |
| Development | Active ($24M raised Oct 2025) |

**What it is:** A memory layer for AI agents, not a document analysis tool. Extracts and stores memories from conversations, providing context to future interactions.

**Connectors:** None. It processes conversation data, not documents.

**Local LLM:** YES via Ollama. Full local stack: Ollama (LLM + embeddings) + Qdrant (vectors) + Postgres.

**Qdrant Integration:** YES, native. Configurable with host, port, collection_name, embedding_model_dims, cosine distance.

**Scheduling:** NO.

**Docker:** YES (OpenMemory: API + Qdrant + Postgres).

**Resources:** Light (~2-4 GB).

**Verdict:** Wrong tool category. Mem0 is a memory layer that augments agents with conversational memory -- not a document indexing or analysis tool. However, it could be a **valuable complement** to the existing agent framework for adding persistent memory to the knowledge-agent. The native Qdrant integration is a plus. Athanor already has similar functionality via its preferences/activity/knowledge context injection system.

**Sources:**
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Mem0 Qdrant Integration](https://qdrant.tech/documentation/frameworks/mem0/)
- [Mem0 + Qdrant + Ollama Local Setup](https://loze.hashnode.dev/fixing-mem0-local-ollama-and-openclaw-mem0-with-qdrant-ollama-locally)
- [Mem0 Self-Host Docker Guide](https://mem0.ai/blog/self-host-mem0-docker)
- [Mem0 Paper (arXiv)](https://arxiv.org/abs/2504.19413)

---

### 7. Letta (letta-ai/letta, formerly MemGPT)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 21.2k |
| Latest Version | v0.5+ (2026) |
| License | Apache 2.0 |
| Development | Very active (Context Repositories Feb 2026, Conversations API Jan 2026) |

**What it is:** A platform for building stateful agents with advanced memory (core memory as RAM, archival/recall memory as disk). Agents self-manage their context window.

**Connectors:** None. It is an agent framework, not a document ingestion tool.

**Local LLM:** YES via OpenAI-compatible API (vLLM, Ollama). Environment variable configuration for multiple providers.

**Scheduling:** NO built-in scheduling. Agents are persistent and stateful but must be invoked.

**Docker:** YES (`docker run` with env vars, compose.yaml available including a vLLM-specific compose file).

**Resources:** Moderate. PostgreSQL backend. 100K+ Docker pulls.

**Continuous Re-indexing:** NO.

**Recent Innovation:** Context Repositories (Feb 2026) -- programmatic context management with git-based versioning. Interesting for long-running knowledge agents.

**Verdict:** Impressive agent memory architecture but wrong tool for document analysis/ingestion. Could potentially replace or augment the LangGraph knowledge-agent with superior memory management, but would not solve the Google Drive -> index -> analyze pipeline. The context repositories feature is interesting for future consideration.

**Sources:**
- [Letta GitHub](https://github.com/letta-ai/letta)
- [Letta Docker Guide](https://docs.letta.com/guides/docker/)
- [Letta v0.5 Release](https://www.letta.com/blog/letta-v0-5-release)
- [Letta Docker Hub](https://hub.docker.com/r/letta/letta)
- [Letta vLLM Compose](https://github.com/letta-ai/letta/blob/main/docker-compose-vllm.yaml)

---

### 8. Perplexica (ItzCrazyKns/Perplexica)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | ~20k |
| License | MIT |

**What it is:** Self-hosted AI-powered web search engine (Perplexity alternative). Uses SearXNG for web search + LLM for answer synthesis.

**Connectors:** Web search only. No document ingestion, no file system access, no Google Drive.

**Local LLM:** YES via Ollama or OpenAI-compatible API.

**Verdict:** Wrong category entirely. Web search tool, not personal data analysis. **Not applicable.**

**Sources:**
- [Perplexica GitHub](https://github.com/ItzCrazyKns/Perplexica)

---

### 9. n8n (n8n-io/n8n)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | 72k+ |
| Latest Version | Active (continuous releases, 2026) |
| License | Sustainable Use License (fair-code, not OSS) |
| Development | Very active (company-backed, major 2026 updates) |

**What it is:** Visual workflow automation platform with native AI capabilities. 400+ integrations including Google Drive, GitHub, Slack, email, databases, and more.

**Connectors:**
- **Google Drive: YES** (native, read/write/watch triggers)
- GitHub: YES
- Slack, Discord, Email, HTTP, databases, 400+ more
- File system triggers
- Webhooks

**Local LLM:** YES. Ollama node for local models, custom OpenAI-compatible endpoints, LangChain integration for building AI agent workflows.

**Scheduling:** **BEST-IN-CLASS.** Full cron-based scheduling, file-change triggers, webhook triggers, event-driven workflows, interval-based polling. This is its core purpose.

**Docker:** YES. `docker-compose` with persistent volumes. Self-hosted AI Starter Kit includes n8n + Ollama + Qdrant pre-configured.

**Resources:** Light (~1-2 GB for n8n itself). Workflows execute on demand.

**Continuous Re-indexing:** YES. Build any pipeline: watch Google Drive for changes, process new files, embed, store in Qdrant. Fully customizable.

**AI Nodes:** AI Agent node, Text Classifier, Information Extractor, Summarizer. Can build complex AI pipelines visually.

**Qdrant Integration:** YES. Native Qdrant node in the self-hosted AI starter kit.

**Verdict:** **STRONGEST orchestration tool.** Not a RAG engine itself, but can orchestrate any pipeline: Google Drive watch -> file download -> document parsing -> LLM analysis -> Qdrant upsert -> Neo4j graph update. The visual workflow builder makes complex pipelines maintainable by one person. Integrates natively with Qdrant, Ollama, and can call any OpenAI-compatible API (LiteLLM). The fair-code license is the main concern -- free for self-host but not technically open-source.

**Sources:**
- [n8n GitHub](https://github.com/n8n-io/n8n)
- [n8n Self-hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)
- [n8n AI Workflow Automation](https://n8n.io/ai/)
- [n8n Features](https://n8n.io/features/)
- [Self-Hosted AI with n8n and Ollama (2026)](https://dev.to/lyraalishaikh/self-hosted-ai-in-2026-automating-your-linux-workflow-with-n8n-and-ollama-1a9l)
- [Build AI Agents with n8n Guide (2026)](https://strapi.io/blog/build-ai-agents-n8n)

---

### 10. ActivePieces (activepieces/activepieces)

| Attribute | Value |
|-----------|-------|
| GitHub Stars | ~15k |
| License | MIT |
| Development | Active |

**What it is:** Open-source (MIT) alternative to Zapier/n8n. AI-first automation with 450+ integrations.

**Connectors:** 450+ integrations. Google Drive likely included but not verified in detail.

**Local LLM:** YES via Ollama and MCP integration. AI Agents built in.

**Scheduling:** YES. Full workflow automation with triggers, schedules, webhooks.

**Docker:** YES.

**Verdict:** Viable n8n alternative with a truly open-source (MIT) license. Less mature ecosystem and community than n8n, fewer AI-specific features. Worth watching but n8n is the safer bet today.

**Sources:**
- [ActivePieces GitHub](https://github.com/activepieces/activepieces)
- [ActivePieces Website](https://www.activepieces.com/)
- [ActivePieces XDA Review](https://www.xda-developers.com/activepieces-is-self-hosted-automation-suite-powered-by-local-llm/)

---

### 11. Paperless-ngx + AI Plugins

| Attribute | Value |
|-----------|-------|
| GitHub Stars | ~25k (paperless-ngx) |
| License | GPL-3.0 |
| Development | Very active |

**What it is:** Document management system with OCR, tagging, and search. AI plugins add LLM-powered analysis.

**Connectors:** File import (manual, watched folder, email). No Google Drive native connector.

**AI Plugins:**
- **paperless-gpt** (icereed/paperless-gpt): LLM-powered OCR (via vision models), title/tag/correspondent generation, ad-hoc document analysis with custom prompts. Supports Ollama.
- **paperless-ai** (clusterzx/paperless-ai): Automated document analyzer with OpenAI-compatible API, Ollama, Deepseek-r1.

**Local LLM:** YES via both plugins with Ollama. Vision LLMs (minicpm-v, Qwen2.5-VL) for OCR.

**Scheduling:** YES for document processing (auto-process on import). No autonomous analysis scheduling.

**Docker:** YES.

**Verdict:** Excellent for document management and OCR but narrow scope. Best as a **complement** for managing physical/scanned documents, not as the primary personal data analysis tool. Could receive Google Drive files via rclone -> watched folder.

**Sources:**
- [Paperless-GPT GitHub](https://github.com/icereed/paperless-gpt)
- [Paperless-AI GitHub](https://github.com/clusterzx/paperless-ai)
- [Paperless-ngx + Local AI (Techno Tim)](https://technotim.com/posts/paperless-ngx-local-ai/)
- [Paperless-ngx with Local LLM (XDA)](https://www.xda-developers.com/paperless-ngx-with-a-local-llm/)

---

### 12. Neo4j LLM Knowledge Graph Builder

| Attribute | Value |
|-----------|-------|
| GitHub Stars | ~3k (neo4j-labs/llm-graph-builder) |
| License | Apache 2.0 |
| Development | Active (Neo4j Labs) |

**What it is:** Web application for turning unstructured text into a knowledge graph. Uses LLMs to extract entities and relationships from documents.

**Connectors:** Web UI upload, URLs, YouTube transcripts. No Google Drive, no automated file discovery.

**Local LLM:** YES via Ollama (llama3, qwen, etc.). Configuration via environment variables.

**Scheduling:** NO. Interactive tool, not a background service.

**Docker:** YES (`docker compose`).

**Verdict:** Directly relevant for the knowledge graph construction goal but lacks automation. The entity extraction logic could be adapted into a pipeline step. Athanor already has Neo4j deployed -- this tool writes directly to it. Best used as a **reference implementation** for building a custom entity extraction pipeline, or as an occasional interactive tool for processing document batches.

**Sources:**
- [Neo4j LLM Graph Builder GitHub](https://github.com/neo4j-labs/llm-graph-builder)
- [Neo4j LLM Graph Builder Blog](https://neo4j.com/blog/developer/llm-knowledge-graph-builder-release/)
- [Neo4j LLM Graph Builder Local Deployment](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder-deployment/)
- [Building Knowledge Graph Locally with Neo4j & Ollama](https://blog.greenflux.us/building-a-knowledge-graph-locally-with-neo4j-and-ollama/)

---

## Comparison Matrix

| Tool | Google Drive | Local LLM | Autonomous 24/7 | Docker | Qdrant Compat | Re-indexing | Stars | Fit |
|------|:-----------:|:---------:|:----------------:|:------:|:-------------:|:-----------:|------:|:---:|
| **RAGFlow** | Native | Via Ollama/Xinference | Auto-sync | YES | No (own store) | Auto | 73.6k | A |
| **n8n** | Native | Via Ollama/OpenAI | Full cron/triggers | YES | Native node | Build any | 72k+ | A |
| **Khoj** | NO | Via OpenAI API | Cron automations | YES | No (pgvector) | Limited | 32.5k | B |
| **AnythingLLM** | NO | 30+ providers | Hourly file sync | YES | No (own store) | Limited | 53k | C |
| **Quivr** | Claimed | Via Ollama | NO | YES | No (pgvector) | Limited | 38.8k | C |
| **PrivateGPT** | NO | YES | NO | YES | No (own store) | Batch only | 57k | D |
| **Letta** | NO | Via OpenAI API | Persistent agents | YES | No (Postgres) | NO | 21.2k | D |
| **Mem0** | NO | Via Ollama | NO | YES | **YES native** | NO | ~23k | D* |
| **Perplexica** | NO | Via Ollama | NO | YES | NO | NO | ~20k | F |
| **ActivePieces** | Likely | Via Ollama/MCP | Full cron/triggers | YES | Unknown | Build any | ~15k | B |
| **Paperless-ngx** | NO | Via plugins | On-import | YES | NO | On-import | ~25k | C* |
| **Neo4j Graph Builder** | NO | Via Ollama | NO | YES | N/A (Neo4j) | NO | ~3k | C* |

*Fit ratings: A = strong primary candidate, B = strong secondary, C = useful complement, D = wrong tool, F = not applicable*
*Asterisk = valuable as complement despite low primary fit*

---

## Google Drive Access: Setup Guide

### Option 1: rclone bisync (RECOMMENDED for Athanor)

rclone provides the most reliable, well-tested Google Drive sync for headless Linux servers. It decouples data acquisition from analysis, allowing any tool to process the local mirror.

**Authentication for personal Google Drive:**

OAuth2 refresh token is the correct approach (service accounts cannot access personal Drive files without explicit sharing).

```bash
# On DEV (has browser) -- generate the OAuth token
rclone authorize "drive"
# This opens browser, you authenticate, it prints a JSON token

# On target node (headless) -- configure
rclone config
# Choose: New remote -> name: gdrive -> type: drive
# Paste the token from DEV
# Set scope: drive.readonly (safest) or drive (read/write)
```

**Continuous sync via systemd timer:**

```ini
# /etc/systemd/system/rclone-gdrive-sync.service
[Unit]
Description=Sync Google Drive to local mirror
After=network-online.target

[Service]
Type=oneshot
User=shaun
ExecStart=/usr/bin/rclone sync gdrive: /mnt/local-fast/gdrive-mirror \
  --config /home/shaun/.config/rclone/rclone.conf \
  --transfers 8 \
  --checkers 16 \
  --log-file /var/log/rclone-gdrive.log \
  --log-level INFO \
  --exclude ".Trash-*" \
  --exclude ".~lock.*"
```

```ini
# /etc/systemd/system/rclone-gdrive-sync.timer
[Unit]
Description=Sync Google Drive every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

**Alternative: rclone mount (FUSE):**

```bash
rclone mount gdrive: /mnt/gdrive \
  --config /home/shaun/.config/rclone/rclone.conf \
  --vfs-cache-mode full \
  --vfs-cache-max-size 50G \
  --allow-other \
  --daemon
```

FUSE mount provides transparent access but is less reliable for batch processing. `sync` is preferred for indexing workloads.

**Storage estimate:** Personal Google Drive is typically 15-100 GB. Node 1 has 930 GB free on `/mnt/local-fast` (btrfs).

### Option 2: RAGFlow Native Connector

RAGFlow's Google Drive data source handles OAuth and sync internally. Simpler setup but locks you into RAGFlow's ecosystem.

### Option 3: n8n Google Drive Trigger

n8n's Google Drive node can trigger workflows on file creation/modification. Most flexible for custom pipelines.

**Sources:**
- [rclone Google Drive Docs](https://rclone.org/drive/)
- [rclone Remote Setup (Headless)](https://rclone.org/remote_setup/)
- [rclone bisync + systemd Tutorial](https://forum.rclone.org/t/tutorial-sync-google-drive-files-on-linux-with-rclone-bisync-and-systemd/46468)
- [Google OAuth2 for Server Apps](https://developers.google.com/identity/protocols/oauth2/web-server)

---

## Best Models for Document Analysis

For the document analysis/summarization workload (not chat), the following models are best suited:

### Already Deployed (Use First)

| Model | Location | Strengths |
|-------|----------|-----------|
| Qwen3-32B-AWQ | Node 1, TP=4 | 32K context, strong summarization, structured extraction, tool calling |
| Qwen3-Embedding-0.6B | Node 1:8001 | 1024-dim embeddings, 32K input, Matryoshka support |

Qwen3-32B is already excellent for document analysis. No need to deploy additional models initially.

### For Vision/OCR Tasks (Future)

| Model | Parameters | VRAM | Strength |
|-------|-----------|------|----------|
| Qwen2.5-VL-7B-Instruct | 7B | ~8 GB (AWQ) | Best small vision model for document OCR, table extraction |
| Qwen2.5-VL-72B-Instruct | 72B | ~40 GB (AWQ) | Best vision model for complex documents, 131K context |
| GLM-4.5V | 12B active (106B total MoE) | ~15 GB | Strong multimodal, flexible thinking mode |

For scanned documents or image-heavy PDFs, a vision model like Qwen2.5-VL-7B could run on GPU 4 (5070 Ti, 16 GB VRAM) alongside the embedding model. This would handle OCR better than any text-only approach.

### For Structured Extraction

Qwen3-32B with structured output prompting (JSON mode) is already the best option. For lighter workloads, Qwen3-8B-AWQ could run on a single 5070 Ti and handle entity extraction at higher throughput.

**Sources:**
- [Best LLMs for Document Screening 2026](https://www.siliconflow.com/articles/en/best-open-source-LLM-for-Document-screening)
- [Best Open Source LLMs for Summarization 2026](https://www.siliconflow.com/articles/en/best-open-source-llms-for-summarization)
- [LLMs for Structured Data Extraction from PDFs 2026](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)
- [DocMind AI (vLLM + LlamaIndex)](https://github.com/BjornMelin/docmind-ai-llm)
- [Best Local LLMs for PDF Chat & RAG](https://localllm.in/blog/best-local-llms-pdf-chat-rag)

---

## Analysis: Three Architecture Options

### Option A: RAGFlow as Standalone Service

Deploy RAGFlow alongside the existing stack. It handles Google Drive sync, document parsing, and indexing internally. Build a bridge to export parsed/chunked data into Qdrant and Neo4j.

```
Google Drive ──> RAGFlow (auto-sync) ──> DeepDoc parsing ──> RAGFlow internal store
                                                               │
                                                     Bridge script (cron)
                                                               │
                                              ┌────────────────┼────────────────┐
                                              ▼                ▼                ▼
                                           Qdrant          Neo4j          Agent context
                                        (embeddings)  (knowledge graph) (enriched prompts)
```

**Pros:**
- Best document parsing (DeepDoc) out of any tool evaluated
- Native Google Drive connector with auto-sync
- Handles 15+ file formats natively
- Active development, large community
- Self-contained -- minimal integration work to get basic functionality

**Cons:**
- Heavy resource footprint (Elasticsearch, MinIO, MySQL, ~16 GB RAM minimum)
- Uses its own vector store -- need bridge to Qdrant
- Duplicated storage (RAGFlow store + Qdrant)
- Another large system to maintain
- LLM integration via Ollama/Xinference -- not direct LiteLLM

**Resource estimate:** 16-32 GB RAM, 50+ GB disk, 4+ CPU cores. Fits on Node 1 given 224 GB RAM.

---

### Option B: n8n Orchestration + Custom Pipeline

Deploy n8n as the workflow orchestrator. Build AI pipelines that watch Google Drive, process documents through LiteLLM/vLLM, and store results in Qdrant + Neo4j. Extend the existing knowledge-agent.

```
Google Drive ──> n8n (watch trigger) ──> Download file
                                              │
                                    n8n AI pipeline
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                        Text extraction  LLM summarization  Entity extraction
                        (Apache Tika     (via LiteLLM →     (via LiteLLM →
                         or Unstructured) Qwen3-32B)         Qwen3-32B)
                              │               │               │
                              ▼               ▼               ▼
                           Qdrant          Qdrant          Neo4j
                        (full-text      (summaries,       (entities,
                         embeddings)     insights)        relationships)
```

**Pros:**
- Uses existing infrastructure (LiteLLM, Qdrant, Neo4j, vLLM) -- no duplication
- Visual workflow builder -- one-person maintainable
- 400+ integrations for future data sources
- Light resource footprint (~1-2 GB for n8n)
- Full scheduling control (cron, triggers, webhooks)
- Can call any API -- fully flexible

**Cons:**
- Must build document parsing pipeline manually (no DeepDoc equivalent)
- Text extraction from complex PDFs will be worse than RAGFlow
- More initial setup work
- n8n license is fair-code, not true open source

**Resource estimate:** 2-4 GB RAM for n8n, uses existing vLLM/LiteLLM for inference.

---

### Option C: Extend Existing Agent Framework (Build Custom)

No new tools. Extend `index-knowledge.py` and the knowledge-agent to handle Google Drive (via rclone mirror), more file types, entity extraction, and continuous scheduling.

```
rclone sync (systemd timer, 15min) ──> /mnt/local-fast/gdrive-mirror/
                                              │
                              Extended index-knowledge.py (cron, 30min)
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                        Chunking +       LLM analysis     Entity extraction
                        embedding        (summaries,       (people, projects,
                        (existing         topics,          dates, concepts)
                         pipeline)        insights)              │
                              │               │               ▼
                              ▼               ▼            Neo4j
                           Qdrant          Qdrant        (knowledge
                        (knowledge      (analysis         graph)
                         collection)    collection)
                                              │
                              Knowledge agent can query all three stores
```

**Pros:**
- Zero new services to deploy or maintain
- Uses all existing infrastructure perfectly
- Full control over every pipeline step
- Lightest resource footprint
- Best integration with existing agent framework
- Can incrementally improve (start simple, add sophistication)

**Cons:**
- Must build all document parsing from scratch (or use libraries like Unstructured, PyMuPDF, python-docx)
- No visual workflow builder -- all Python code
- Entity extraction quality depends on prompt engineering
- More development time upfront

**Resource estimate:** Near zero additional -- uses existing infrastructure.

---

## Recommendation

### Primary: Option C (Extend Existing) with Option A (RAGFlow) for Document Parsing

The recommended approach is a **hybrid**:

1. **Phase 1 (Immediate): rclone + Extended indexer**
   - Set up rclone bisync for Google Drive mirror on Node 1 (`/mnt/local-fast/gdrive-mirror/`)
   - Extend `index-knowledge.py` to scan the Google Drive mirror directory
   - Add file type support: PDF (PyMuPDF), DOCX (python-docx), PPTX (python-pptx), images (OCR via vision model)
   - Run on a cron schedule (every 30 minutes)
   - Store embeddings in Qdrant `knowledge` collection with metadata tags for source (gdrive, github, local)

2. **Phase 2 (Next sprint): LLM Analysis Pipeline**
   - Add a document analysis pass: for each new/changed document, call Qwen3-32B via LiteLLM to generate:
     - Summary (1-2 paragraphs)
     - Key topics/tags
     - Named entities (people, organizations, projects, dates)
     - Relationships between entities
   - Store summaries in Qdrant `analysis` collection
   - Store entities and relationships in Neo4j

3. **Phase 3 (If document parsing quality is insufficient): RAGFlow as Parser**
   - Deploy RAGFlow specifically for its DeepDoc parsing capability
   - Use RAGFlow's API to submit documents and retrieve parsed/structured output
   - Feed the structured output into the existing Qdrant/Neo4j pipeline
   - This avoids duplicating the vector store while leveraging RAGFlow's best feature

4. **Phase 4 (If workflow complexity grows): n8n Orchestration**
   - Deploy n8n if the cron-based pipeline becomes insufficient
   - Migrate scheduling/triggering to n8n workflows
   - Keep the Python analysis code but trigger it from n8n
   - Add n8n integrations for notifications, monitoring, error handling

### Why Not RAGFlow as Primary?

RAGFlow is the most capable single tool, but deploying it means:
- Another 16+ GB RAM for Elasticsearch, MinIO, MySQL
- Duplicated vector storage (RAGFlow's store vs. Qdrant)
- The agents cannot query RAGFlow's store natively -- need a bridge
- Another large system to maintain and update

The existing Athanor infrastructure already has everything needed except the document parsing and Google Drive sync. Adding those capabilities to the existing pipeline is simpler, lighter, and more maintainable than deploying a parallel system.

### Why Not n8n as Primary?

n8n is excellent for orchestration but overkill for Phase 1. If the pipeline grows complex (multiple data sources, conditional logic, error handling, notifications), n8n becomes the right choice. Start without it and add it if needed.

---

## Deployment Plan

### Phase 1: Google Drive Mirror + Extended Indexer (1-2 days)

```bash
# 1. Install rclone on Node 1
sudo apt install rclone

# 2. Configure Google Drive remote (requires browser on DEV for auth)
# On DEV:
rclone authorize "drive"
# Copy token, then on Node 1:
rclone config
# New remote -> gdrive -> drive -> paste token

# 3. Initial sync
rclone sync gdrive: /mnt/local-fast/gdrive-mirror/ \
  --transfers 8 --checkers 16 --progress

# 4. Set up systemd timer (see Google Drive Access section above)
sudo systemctl enable --now rclone-gdrive-sync.timer

# 5. Extend index-knowledge.py
# Add GDRIVE_DIR = Path("/mnt/local-fast/gdrive-mirror")
# Add PDF parsing (PyMuPDF), DOCX (python-docx), PPTX (python-pptx)
# Add source metadata tagging
# Run: python3 scripts/index-knowledge.py --full
```

### Phase 2: Analysis Pipeline (2-3 days)

```bash
# New script: scripts/analyze-documents.py
# For each new/changed document in Qdrant:
#   1. Retrieve full text
#   2. Call LiteLLM → Qwen3-32B for summarization
#   3. Call LiteLLM → Qwen3-32B for entity extraction (JSON mode)
#   4. Upsert summary to Qdrant 'analysis' collection
#   5. Upsert entities/relationships to Neo4j
#
# Cron: */30 * * * * python3 /home/shaun/repos/Athanor/scripts/analyze-documents.py
```

### Phase 3: RAGFlow Parser (If Needed) (1 day)

```bash
# Deploy RAGFlow on Node 1 alongside existing services
cd /opt/ragflow
docker compose -f docker-compose.yml up -d

# Use RAGFlow API for document parsing only:
# POST /api/v1/datasets/{dataset_id}/documents
# GET /api/v1/datasets/{dataset_id}/documents/{doc_id}/chunks
# Feed chunks into existing Qdrant pipeline
```

### Phase 4: n8n Orchestration (If Needed) (1 day)

```bash
# Deploy n8n on VAULT or Node 2
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n

# Build workflows:
# - Google Drive watch → document processing → Qdrant/Neo4j
# - Scheduled analysis runs
# - Error notifications → Command Center
```

---

## Open Questions

1. **Google Drive data volume**: How much data is in Shaun's Google Drive? This affects storage requirements and initial sync time.
2. **File types**: What formats dominate (PDFs, Google Docs, images, spreadsheets)? This determines which parsers to prioritize.
3. **Google API credentials**: OAuth token generation requires browser access and a Google Cloud project with Drive API enabled. Shaun will need to do the initial auth flow.
4. **Analysis depth**: Simple embedding + search? Or deep entity extraction + knowledge graph construction? The latter requires significantly more LLM compute.
5. **GitHub repos**: Which repos should be indexed? All personal repos, or specific ones (Hydra, Kaizen)?

---

*Last updated: 2026-02-26*
