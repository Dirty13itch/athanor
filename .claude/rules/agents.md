---
paths:
  - "projects/agents/**"
---

# Agent Server Conventions

- Python FastAPI + LangGraph + LiteLLM at Node 1:9000
- 9 agents: general-assistant, media-agent, research-agent, creative-agent, knowledge-agent, home-agent, coding-agent, stash-agent, data-curator
- Deploy: rsync src/ → Node 1:/opt/athanor/agents/src/, docker compose build --no-cache, up -d
- Also rsync pyproject.toml + docker-compose.yml when dependencies change
- Inference via LiteLLM proxy at VAULT:4000 (aliases: reasoning, fast, embedding)
- Context injection: `context.py` — 1 embedding + 4 parallel Qdrant queries (preferences, activity, knowledge, personal_data) + Redis goals, ~30-50ms
- Execution tools: READ from /workspace, /data/personal, /output. WRITE to /output only.
- Activity logging: fire-and-forget asyncio to Qdrant `activity` collection
- Qwen3 `<think>` blocks stripped before client delivery
- NSFW content is explicitly allowed (Stash agent, Creative agent) — do not filter or moralize
- All agents report to Claude (COO), not directly to Shaun
