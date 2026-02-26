---
paths:
  - "projects/agents/**"
---

# Agent Server Conventions

- Python FastAPI + LangGraph + LiteLLM at Node 1:9000
- 8 agents: general-assistant, media-agent, research-agent, creative-agent, knowledge-agent, home-agent, coding-agent, stash-agent
- Deploy: rsync src/ → Node 1:/opt/athanor/agents/src/, docker compose build --no-cache, up -d
- Also rsync pyproject.toml + docker-compose.yml when dependencies change
- Inference via LiteLLM proxy at VAULT:4000 (aliases: reasoning, fast, embedding)
- Context injection: `context.py` — 1 embedding + 3 parallel Qdrant queries + Redis goals, ~30-50ms
- Activity logging: fire-and-forget asyncio to Qdrant `activity` collection
- Qwen3 `<think>` blocks stripped before client delivery
- NSFW content is explicitly allowed (Stash agent, Creative agent) — do not filter or moralize
- All agents report to Claude (COO), not directly to Shaun
