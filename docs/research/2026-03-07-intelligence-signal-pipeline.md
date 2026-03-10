# Intelligence Signal Ingestion Pipeline — Miniflux + n8n

**Date:** 2026-03-07
**Status:** Research complete, ready for implementation
**BUILD-MANIFEST item:** 12.1 — Intelligence Signal Ingestion
**Author:** Claude (COO)

---

## 1. Executive Summary

Deploy Miniflux (RSS aggregator) and n8n (workflow automation) on VAULT (.203) to create an automated intelligence pipeline. RSS feeds are polled by Miniflux, new entries trigger n8n workflows via webhook, n8n classifies signals using LiteLLM (VAULT:4000) -> Qwen3.5-35B-A3B, and stores tagged results in a new Qdrant `signals` collection on FOUNDRY:6333. The Knowledge Agent and Morning Briefing (12.2) consume from this collection.

**Resource budget on VAULT:** ~512MB RAM, ~1GB disk (excluding PostgreSQL data growth). Miniflux is a single Go binary (~30MB container). n8n is Node.js (~200MB container). PostgreSQL is shared where possible but Miniflux requires its own DB.

---

## 2. Architecture

```
                    ┌─────────────┐
                    │  RSS Feeds  │  (30+ feeds, polled every 30min)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Miniflux   │  VAULT:8085
                    │  (Go, ~30MB)│
                    └──────┬──────┘
                           │ webhook POST on new entries
                    ┌──────▼──────┐
                    │    n8n      │  VAULT:5678
                    │ (Node.js)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼───────┐ ┌─▼──────┐ ┌──▼────────┐
      │ LiteLLM:4000  │ │ Embed  │ │  Qdrant   │
      │ (classify)    │ │:4000   │ │ :6333     │
      │ VAULT         │ │ VAULT  │ │ FOUNDRY   │
      └───────────────┘ └────────┘ └───────────┘
```

### Data Flow

1. **Miniflux** polls RSS feeds on configurable schedule (default 30min)
2. On new entry, Miniflux fires webhook to `http://localhost:5678/webhook/miniflux-signal`
3. **n8n workflow** receives entry, extracts title + content + metadata
4. n8n calls LiteLLM `/v1/chat/completions` to classify signal:
   - Categories: `model_release`, `framework_update`, `security_advisory`, `infrastructure`, `research_paper`, `homelab`, `other`
   - Priority: `critical`, `high`, `normal`, `low`
   - Relevance score: 0.0-1.0 (to Athanor's focus areas)
5. n8n calls LiteLLM `/embeddings` to generate vector embedding
6. n8n upserts to Qdrant `signals` collection with full metadata

### Why Miniflux over raw RSS polling in n8n

- Miniflux handles feed parsing, deduplication, error recovery, OPML import/export
- Miniflux tracks read/unread state — useful for human review via web UI (VAULT:8085)
- Miniflux's webhook fires only on genuinely new entries (no duplicate processing)
- n8n's built-in RSS node has no state management — it re-fetches everything each run
- Separation of concerns: Miniflux owns feed management, n8n owns signal processing

### Why not Miniflux alone

- Miniflux has no LLM classification capability
- No vector embedding generation
- No Qdrant integration
- No complex workflow orchestration (conditional routing, error handling, retries)

---

## 3. Miniflux Deployment

### Docker Image

- **Image:** `miniflux/miniflux:2.2` (pin to major.minor, track patch via Watchtower or manual update)
- **Also available:** `ghcr.io/miniflux/miniflux:2.2`
- **Size:** ~30MB (single Go binary, Alpine-based)
- **Architecture:** amd64, arm64

### PostgreSQL Backend

Miniflux requires PostgreSQL. Options:
- **Option A (recommended):** Dedicated `miniflux-postgres` container in the Miniflux compose stack. Keeps blast radius small, follows the langfuse pattern.
- **Option B:** Shared PostgreSQL instance. Saves RAM but couples services.

Going with Option A for consistency with existing vault roles.

### Key Environment Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgres://miniflux:PASSWORD@miniflux-postgres:5432/miniflux?sslmode=disable` | Internal network |
| `RUN_MIGRATIONS` | `1` | Auto-migrate on startup |
| `CREATE_ADMIN` | `1` | First run only |
| `ADMIN_USERNAME` | `athanor` | |
| `ADMIN_PASSWORD` | `(vault-encrypted)` | |
| `POLLING_FREQUENCY` | `30` | Minutes between poll cycles |
| `BATCH_SIZE` | `10` | Feeds per poll cycle |
| `POLLING_PARSING_ERROR_LIMIT` | `3` | Max consecutive errors before disabling feed |
| `LISTEN_ADDR` | `0.0.0.0:8080` | Internal port |
| `BASE_URL` | `http://192.168.1.203:8085` | External URL |
| `CLEANUP_ARCHIVE_UNREAD_DAYS` | `90` | Keep unread entries 90 days |
| `CLEANUP_ARCHIVE_READ_DAYS` | `30` | Keep read entries 30 days |
| `METRICS_COLLECTOR` | `1` | Enable Prometheus metrics at `/metrics` |
| `METRICS_ALLOWED_NETWORKS` | `192.168.1.0/24` | Allow LAN scraping |
| `WEBHOOK_URL` | `http://n8n:5678/webhook/miniflux-signal` | n8n webhook endpoint |
| `TZ` | `America/Chicago` | |

### Health Check

Miniflux has a built-in health check binary:
```
/usr/bin/miniflux -healthcheck auto
```

### Prometheus Metrics

When `METRICS_COLLECTOR=1`, Miniflux exposes metrics at `/metrics`:
- `miniflux_feeds_count` — total feeds
- `miniflux_entries_count` — total entries
- `miniflux_unread_entries_count` — unread entries
- `miniflux_errors_count` — feed parsing errors

Add to Grafana Alloy scrape config on VAULT.

---

## 4. n8n Deployment

### Docker Image

- **Image:** `n8nio/n8n:1.100` (pin to major.minor)
- **Size:** ~200MB
- **Architecture:** amd64, arm64

### Resource Requirements

- **RAM:** 256MB minimum, 512MB recommended for AI workflow execution
- **CPU:** 1-2 cores sufficient for scheduled workflows
- **Disk:** Workflow data stored in PostgreSQL, execution logs can grow — configure retention

### Key Environment Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `DB_TYPE` | `postgresdb` | Production requirement |
| `DB_POSTGRESDB_HOST` | `n8n-postgres` | Internal network |
| `DB_POSTGRESDB_PORT` | `5432` | |
| `DB_POSTGRESDB_DATABASE` | `n8n` | |
| `DB_POSTGRESDB_USER` | `n8n` | |
| `DB_POSTGRESDB_PASSWORD` | `(vault-encrypted)` | |
| `N8N_PORT` | `5678` | |
| `N8N_PROTOCOL` | `http` | |
| `N8N_HOST` | `192.168.1.203` | |
| `WEBHOOK_URL` | `http://192.168.1.203:5678/` | External webhook base URL |
| `GENERIC_TIMEZONE` | `America/Chicago` | |
| `TZ` | `America/Chicago` | |
| `N8N_DIAGNOSTICS_ENABLED` | `false` | No telemetry |
| `N8N_PERSONALIZATION_ENABLED` | `false` | Skip onboarding |
| `EXECUTIONS_DATA_PRUNE` | `true` | Auto-prune old executions |
| `EXECUTIONS_DATA_MAX_AGE` | `168` | 7 days retention (hours) |
| `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` | `true` | Security hardening |

### AI Nodes

n8n has ~70 LangChain/AI nodes built in. For our use case, we primarily use the **HTTP Request** node to call LiteLLM directly (OpenAI-compatible API). This avoids n8n's credential management complexity and keeps LiteLLM as the single inference gateway.

Relevant n8n nodes for signal pipeline:
- `n8n-nodes-base.webhook` — receive Miniflux webhooks
- `n8n-nodes-base.code` — JavaScript signal processing logic
- `n8n-nodes-base.httpRequest` — call LiteLLM, Qdrant, agent server APIs
- `n8n-nodes-base.if` — conditional routing by signal category
- `n8n-nodes-base.scheduleTrigger` — periodic batch processing
- `n8n-nodes-base.splitInBatches` — rate-limited processing

---

## 5. RSS Feed Subscriptions

### AI/ML Model Releases

| Feed | URL | Category |
|------|-----|----------|
| HuggingFace Trending Models | `https://zernel.github.io/huggingface-trending-feed/feed.xml` | `model_release` |
| HuggingFace Daily Papers | `https://papers.takara.ai/api/feed` | `research_paper` |
| HuggingFace Blog | `https://huggingface.co/blog/feed.xml` | `model_release` |
| Ollama Blog | `https://ollama.com/blog/feed` | `model_release` |

### Inference Frameworks

| Feed | URL | Category |
|------|-----|----------|
| vLLM Releases | `https://github.com/vllm-project/vllm/releases.atom` | `framework_update` |
| SGLang Releases | `https://github.com/sgl-project/sglang/releases.atom` | `framework_update` |
| llama.cpp Releases | `https://github.com/ggml-org/llama.cpp/releases.atom` | `framework_update` |
| LiteLLM Releases | `https://github.com/BerriAI/litellm/releases.atom` | `framework_update` |
| LangChain Releases | `https://github.com/langchain-ai/langchain/releases.atom` | `framework_update` |
| LangGraph Releases | `https://github.com/langchain-ai/langgraph/releases.atom` | `framework_update` |

### NVIDIA / GPU

| Feed | URL | Category |
|------|-----|----------|
| NVIDIA Blog (AI) | `https://blogs.nvidia.com/feed/` | `infrastructure` |
| NVIDIA Container Toolkit | `https://github.com/NVIDIA/nvidia-container-toolkit/releases.atom` | `infrastructure` |

### Home Automation

| Feed | URL | Category |
|------|-----|----------|
| Home Assistant Blog | `https://www.home-assistant.io/atom.xml` | `homelab` |
| Home Assistant Releases | `https://github.com/home-assistant/core/releases.atom` | `homelab` |

### Security Advisories

| Feed | URL | Category |
|------|-----|----------|
| Ubuntu Security Notices | `https://ubuntu.com/security/notices/rss.xml` | `security_advisory` |
| Docker Security | `https://docs.docker.com/security/security-announcements/index.xml` | `security_advisory` |
| LinuxSecurity Advisories | `https://linuxsecurity.com/advisories/feed` | `security_advisory` |
| NIST NVD (High Severity) | `https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml` | `security_advisory` |

### Infrastructure / DevOps

| Feed | URL | Category |
|------|-----|----------|
| Ansible Blog | `https://www.ansible.com/blog/rss.xml` | `infrastructure` |
| Grafana Blog | `https://grafana.com/blog/index.xml` | `infrastructure` |
| Qdrant Blog | `https://qdrant.tech/blog/feed.xml` | `infrastructure` |
| n8n Blog | `https://blog.n8n.io/rss/` | `infrastructure` |

### General Tech Intelligence

| Feed | URL | Category |
|------|-----|----------|
| Hacker News Best | `https://hnrss.org/best` | `research_paper` |
| arXiv cs.AI | `https://export.arxiv.org/rss/cs.AI` | `research_paper` |
| arXiv cs.LG | `https://export.arxiv.org/rss/cs.LG` | `research_paper` |
| The Gradient | `https://thegradient.pub/rss/` | `research_paper` |

**Total: ~30 feeds across 7 categories.**

---

## 6. n8n Workflow Design: Signal Classifier

### Workflow 1: `miniflux-signal-classifier` (webhook-triggered)

```
Miniflux Webhook → Parse Entry → Classify via LLM → Generate Embedding → Upsert Qdrant
```

**Trigger:** Webhook at `/webhook/miniflux-signal`

**Step 1: Parse Entry** (Code node)
```javascript
const entry = $input.item.json;
return {
  json: {
    id: `signal_${entry.id || Date.now()}`,
    title: entry.title || '',
    content: (entry.content || entry.description || '').substring(0, 3000),
    url: entry.url || entry.feed_url || '',
    feed_title: entry.feed?.title || 'Unknown',
    published_at: entry.published_at || new Date().toISOString(),
    category: entry.feed?.category?.title || 'uncategorized'
  }
};
```

**Step 2: Classify via LiteLLM** (HTTP Request node)
```
POST http://192.168.1.203:4000/v1/chat/completions

{
  "model": "qwen3.5-35b",
  "messages": [
    {
      "role": "system",
      "content": "You are a signal classifier for a homelab AI cluster called Athanor. Classify the following RSS entry. Respond ONLY with valid JSON.\n\nCategories: model_release, framework_update, security_advisory, infrastructure, research_paper, homelab, other\nPriority: critical (security/breaking), high (directly relevant), normal (interesting), low (tangential)\nRelevance: 0.0-1.0 score for relevance to: local AI inference, GPU optimization, vLLM, home automation, system administration\n\nJSON format: {\"category\": \"...\", \"priority\": \"...\", \"relevance\": 0.0, \"summary\": \"one-line summary\", \"tags\": [\"tag1\", \"tag2\"]}"
    },
    {
      "role": "user",
      "content": "Title: {{title}}\nSource: {{feed_title}}\nContent: {{content}}"
    }
  ],
  "max_tokens": 256,
  "temperature": 0.1
}
```

**Step 3: Parse Classification** (Code node)
```javascript
const response = $input.item.json;
const content = response.choices?.[0]?.message?.content || '{}';
let classification;
try {
  // Extract JSON from potential markdown code blocks
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  classification = JSON.parse(jsonMatch ? jsonMatch[0] : content);
} catch (e) {
  classification = { category: 'other', priority: 'low', relevance: 0.3, summary: 'Classification failed', tags: [] };
}
return { json: { ...classification } };
```

**Step 4: Filter Low-Value** (If node)
- Condition: `relevance >= 0.2` OR `priority in ['critical', 'high']`
- Drop entries that score below threshold to avoid noise

**Step 5: Generate Embedding** (HTTP Request node)
```
POST http://192.168.1.203:4000/embeddings

{
  "model": "nomic-embed-text",
  "input": "{{title}}. {{summary}}"
}
```

**Step 6: Upsert to Qdrant** (HTTP Request node)
```
PUT http://192.168.1.244:6333/collections/signals/points

{
  "points": [{
    "id": "{{signal_id_as_uuid}}",
    "vector": [embedding array],
    "payload": {
      "title": "...",
      "summary": "...",
      "url": "...",
      "source_feed": "...",
      "category": "...",
      "priority": "...",
      "relevance": 0.0,
      "tags": [],
      "published_at": "...",
      "ingested_at": "...",
      "read": false
    }
  }]
}
```

### Workflow 2: `signal-digest` (scheduled, daily 5:30 AM)

Feeds into Morning Briefing (12.2).

```
Schedule 5:30AM → Query Qdrant (last 24h signals) → Group by category → Summarize via LLM → POST to agent server
```

**Summary prompt:**
```
Summarize these intelligence signals for a homelab AI operator's morning briefing.
Group by category. Highlight critical/high priority items first.
Keep it concise — this is a digest, not a report.
```

### Workflow 3: `signal-security-alert` (webhook-triggered, immediate)

When classification returns `category: security_advisory` AND `priority: critical`:
```
Classify → IF critical security → POST to agent server /v1/notifications → Log to activity
```

This enables immediate push notifications for critical security advisories.

### Workflow 4: `feed-health-monitor` (scheduled, daily 2 AM)

```
Schedule 2AM → Miniflux API: GET /v1/feeds → Filter errored feeds → Log/alert
```

Monitors feed health via Miniflux API. Alerts if feeds have been failing for >24h.

### Workflow 5: `signal-cleanup` (scheduled, weekly Sunday 3 AM)

```
Schedule Sun 3AM → Qdrant: delete signals older than 90 days with relevance < 0.3
```

Prevents unbounded growth of the signals collection.

---

## 7. Qdrant `signals` Collection

### Collection Configuration

```json
{
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "optimizers_config": {
    "indexing_threshold": 10000
  }
}
```

Vector size 768 matches `nomic-embed-text` output dimension.

### Payload Index Fields

Create payload indexes for efficient filtering:
- `category` (keyword)
- `priority` (keyword)
- `relevance` (float range)
- `published_at` (datetime range)
- `read` (bool)
- `tags` (keyword, array)

---

## 8. Ansible Role Structure

### `vault-miniflux/`

```
ansible/roles/vault-miniflux/
├── defaults/
│   └── main.yml          # Ports, image tags, polling config
├── tasks/
│   └── main.yml          # Create dir, template compose, pull, start, healthcheck
└── templates/
    └── docker-compose.yml.j2
```

### `vault-n8n/`

```
ansible/roles/vault-n8n/
├── defaults/
│   └── main.yml          # Ports, image tags, execution settings
├── tasks/
│   └── main.yml          # Create dir, template compose, pull, start, healthcheck, import workflows
├── templates/
│   └── docker-compose.yml.j2
└── files/
    └── workflows/        # n8n workflow JSON files for auto-import
        ├── miniflux-signal-classifier.json
        ├── signal-digest.json
        ├── signal-security-alert.json
        ├── feed-health-monitor.json
        └── signal-cleanup.json
```

### Docker Compose — Miniflux

```yaml
# Athanor Miniflux — Managed by Ansible
services:
  miniflux:
    image: {{ miniflux_image }}
    container_name: miniflux
    restart: unless-stopped
    depends_on:
      miniflux-postgres:
        condition: service_healthy
    ports:
      - "{{ miniflux_port }}:8080"
    environment:
      - DATABASE_URL=postgres://{{ miniflux_pg_user }}:{{ miniflux_pg_password }}@miniflux-postgres:5432/{{ miniflux_pg_db }}?sslmode=disable
      - RUN_MIGRATIONS=1
      - CREATE_ADMIN={{ miniflux_create_admin | default('1') }}
      - ADMIN_USERNAME={{ miniflux_admin_user }}
      - ADMIN_PASSWORD={{ miniflux_admin_password }}
      - POLLING_FREQUENCY={{ miniflux_polling_frequency }}
      - BATCH_SIZE={{ miniflux_batch_size }}
      - POLLING_PARSING_ERROR_LIMIT=3
      - BASE_URL=http://192.168.1.203:{{ miniflux_port }}
      - CLEANUP_ARCHIVE_UNREAD_DAYS=90
      - CLEANUP_ARCHIVE_READ_DAYS=30
      - METRICS_COLLECTOR=1
      - METRICS_ALLOWED_NETWORKS=192.168.1.0/24
      - WEBHOOK_URL=http://n8n:5678/webhook/miniflux-signal
      - TZ=America/Chicago
    networks:
      - signals-net
    healthcheck:
      test: ["CMD", "/usr/bin/miniflux", "-healthcheck", "auto"]
      interval: 30s
      timeout: 10s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  miniflux-postgres:
    image: {{ miniflux_postgres_image }}
    container_name: miniflux-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER={{ miniflux_pg_user }}
      - POSTGRES_PASSWORD={{ miniflux_pg_password }}
      - POSTGRES_DB={{ miniflux_pg_db }}
      - TZ=America/Chicago
    volumes:
      - miniflux-pg-data:/var/lib/postgresql/data
    networks:
      - signals-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ miniflux_pg_user }} -d {{ miniflux_pg_db }}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  signals-net:
    name: signals-net

volumes:
  miniflux-pg-data:
```

### Docker Compose — n8n

```yaml
# Athanor n8n — Managed by Ansible
services:
  n8n:
    image: {{ n8n_image }}
    container_name: n8n
    restart: unless-stopped
    depends_on:
      n8n-postgres:
        condition: service_healthy
    ports:
      - "{{ n8n_port }}:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=n8n-postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE={{ n8n_pg_db }}
      - DB_POSTGRESDB_USER={{ n8n_pg_user }}
      - DB_POSTGRESDB_PASSWORD={{ n8n_pg_password }}
      - N8N_HOST=192.168.1.203
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://192.168.1.203:{{ n8n_port }}/
      - GENERIC_TIMEZONE=America/Chicago
      - TZ=America/Chicago
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_PERSONALIZATION_ENABLED=false
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=168
      - N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true
    volumes:
      - n8n-data:/home/node/.n8n
    networks:
      - signals-net
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  n8n-postgres:
    image: {{ n8n_postgres_image }}
    container_name: n8n-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER={{ n8n_pg_user }}
      - POSTGRES_PASSWORD={{ n8n_pg_password }}
      - POSTGRES_DB={{ n8n_pg_db }}
      - TZ=America/Chicago
    volumes:
      - n8n-pg-data:/var/lib/postgresql/data
    networks:
      - signals-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ n8n_pg_user }} -d {{ n8n_pg_db }}"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  signals-net:
    name: signals-net

volumes:
  n8n-data:
  n8n-pg-data:
```

**Important:** Both compose files use the same `signals-net` Docker network so Miniflux can reach n8n's webhook endpoint via container name (`http://n8n:5678/webhook/miniflux-signal`).

### Defaults — `vault-miniflux/defaults/main.yml`

```yaml
---
miniflux_deploy_dir: "{{ vault_appdata_path | default('/mnt/user/appdata') }}/miniflux"
miniflux_port: 8085
miniflux_image: "miniflux/miniflux:2.2"
miniflux_postgres_image: "postgres:16-alpine"

miniflux_pg_user: miniflux
miniflux_pg_password: "{{ vault_miniflux_pg_password | default('<vault_miniflux_pg_password>') }}"
miniflux_pg_db: miniflux

miniflux_admin_user: athanor
miniflux_admin_password: "{{ vault_miniflux_admin_password | default('<vault_miniflux_admin_password>') }}"
miniflux_create_admin: "1"

miniflux_polling_frequency: 30
miniflux_batch_size: 10
```

### Defaults — `vault-n8n/defaults/main.yml`

```yaml
---
n8n_deploy_dir: "{{ vault_appdata_path | default('/mnt/user/appdata') }}/n8n"
n8n_port: 5678
n8n_image: "n8nio/n8n:1.100"
n8n_postgres_image: "postgres:16-alpine"

n8n_pg_user: n8n
n8n_pg_password: "{{ vault_n8n_pg_password | default('<vault_n8n_pg_password>') }}"
n8n_pg_db: n8n
```

---

## 9. Integration Points

### Miniflux API (for feed management automation)

```bash
# List feeds
curl -H "X-Auth-Token: $MINIFLUX_API_TOKEN" http://192.168.1.203:8085/v1/feeds

# Create feed
curl -X POST -H "X-Auth-Token: $MINIFLUX_API_TOKEN" \
  -d '{"feed_url": "https://github.com/vllm-project/vllm/releases.atom", "category_id": 2}' \
  http://192.168.1.203:8085/v1/feeds

# Get unread entries
curl -H "X-Auth-Token: $MINIFLUX_API_TOKEN" \
  http://192.168.1.203:8085/v1/entries?status=unread&limit=50
```

Future: The Knowledge Agent can use the Miniflux API to manage feed subscriptions dynamically.

### n8n API (for workflow management)

```bash
# List workflows
curl http://192.168.1.203:5678/api/v1/workflows

# Import workflow
curl -X POST -H "Content-Type: application/json" \
  -d @workflow.json \
  http://192.168.1.203:5678/api/v1/workflows
```

### Agent Server Integration

The signal digest workflow (Workflow 2) posts to the agent server:
```
POST http://192.168.1.244:9000/v1/signals/digest
```

The Knowledge Agent queries signals via Qdrant semantic search:
```
POST http://192.168.1.244:6333/collections/signals/points/search
```

---

## 10. Hydra Reference Artifacts

### Portable (adapt to Athanor patterns)

| Artifact | Path | What to extract |
|----------|------|-----------------|
| RSS Feed Processor | `reference/hydra/config/n8n/workflows-fixed/rss-feed-processor.json` | Feed loop + embed + Qdrant upsert pattern |
| Morning Briefing | `reference/hydra/config/n8n/workflows-fixed/morning-briefing.json` | Schedule trigger + data aggregation + LLM synthesis |
| Autonomous Research | `reference/hydra/config/n8n/workflows-fixed/autonomous-research-clean.json` | Webhook + LLM synthesis + report generation |
| News Intelligence Engine | `reference/hydra/src/hydra_tools/news_intelligence.py` | Topic extraction, relevance scoring, focus areas, trending detection |

### Key differences from Hydra

- Hydra used `192.168.1.244:4000` for LiteLLM — Athanor uses `192.168.1.203:4000` (VAULT)
- Hydra used `192.168.1.244:6333` for Qdrant — same in Athanor (FOUNDRY)
- Hydra used Letta agent for notifications — Athanor uses agent server at FOUNDRY:9000
- Hydra had no Miniflux — relied on n8n's raw RSS node (lost dedup/state)
- Hydra's news_intelligence.py relevance scoring logic is directly portable as a reference for the LLM classification prompt

---

## 11. Port Assignments

| Service | Port | Protocol |
|---------|------|----------|
| Miniflux Web UI | VAULT:8085 | HTTP |
| Miniflux Metrics | VAULT:8085/metrics | HTTP (Prometheus) |
| n8n Web UI | VAULT:5678 | HTTP |
| n8n Webhook | VAULT:5678/webhook/* | HTTP |

These ports do not conflict with existing VAULT services:
- LiteLLM: 4000
- LangFuse: 3030
- Grafana: 3000
- Neo4j: 7474/7687
- Redis: 6379
- Plex: 32400
- Home Assistant: 8123

---

## 12. Implementation Order

1. **Create Ansible roles** — `vault-miniflux/`, `vault-n8n/` following existing patterns
2. **Deploy Miniflux + n8n** — `ansible-playbook playbooks/vault.yml --tags miniflux,n8n`
3. **Create Qdrant `signals` collection** — via API or add to qdrant role
4. **Import starter feeds** — via Miniflux API (script or n8n setup workflow)
5. **Import n8n workflows** — 5 workflows from `files/workflows/`
6. **Configure Miniflux webhook** — point to n8n signal classifier
7. **Test end-to-end** — trigger manual feed refresh, verify signal appears in Qdrant
8. **Add Prometheus scrape** — Miniflux metrics to Grafana Alloy config
9. **Update vault.yml playbook** — add new roles with tags

---

## 13. Open Questions

1. **Shared `signals-net`?** Both compose files declare the same network. Ansible will deploy them separately. Use `external: true` on one, or deploy both in a single compose. **Decision needed:** Single compose (simpler networking) vs separate composes (follows existing pattern, independent restarts). Recommendation: **separate composes** with a pre-created external Docker network, matching the existing vault role pattern but adding a shared network task.

2. **PostgreSQL consolidation?** Two separate PostgreSQL instances (~50MB each) vs one shared. Recommendation: **keep separate** — isolation is worth 50MB RAM on a 128GB machine.

3. **Miniflux API token provisioning.** The webhook URL is set globally. Per-feed webhooks are not yet supported (GitHub issue #2080). All new entries trigger the same webhook. The n8n workflow must handle routing by feed category internally.

---

## Sources

- [Miniflux Docker Installation](https://miniflux.app/docs/docker.html)
- [Miniflux Configuration Parameters](https://miniflux.app/docs/configuration.html)
- [Miniflux Webhooks](https://miniflux.app/docs/webhooks.html)
- [Miniflux API Reference](https://miniflux.app/docs/api.html)
- [n8n Docker Documentation](https://docs.n8n.io/hosting/installation/docker/)
- [n8n Self-Hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)
- [n8n Self-Hosted Requirements 2026](https://thinkpeak.ai/n8n-self-hosted-requirements-2026/)
- [HuggingFace Trending Models RSS](https://github.com/zernel/huggingface-trending-feed)
- [HuggingFace Daily Papers RSS](https://papers.takara.ai/api/feed)
- [Ubuntu Security Notices](https://ubuntu.com/security/notices)
- [miniflux/miniflux Docker Hub](https://hub.docker.com/r/miniflux/miniflux)
- [n8nio/n8n Docker Hub](https://hub.docker.com/r/n8nio/n8n/tags)
