---
paths:
  - "projects/agents/**"
---

# Agent Server Conventions

- Python FastAPI + LangGraph + LiteLLM at Node 1:9000
- 9 agents: general-assistant, media-agent, research-agent, creative-agent, knowledge-agent, home-agent, coding-agent, stash-agent, data-curator
- Deploy: rsync src/ + pyproject.toml → FOUNDRY:/opt/athanor/agents/, then `docker compose build --no-cache agents && docker compose up -d agents`
- CRITICAL: `scp` + `restart` does NOT work — the container pip-installs the package at build time. MUST rebuild the image.
- Also rsync docker-compose.yml when compose config changes
- Inference via LiteLLM proxy at VAULT:4000 (aliases: reasoning, fast, embedding)
- Context injection: `context.py` — 1 embedding + 4 parallel Qdrant queries (preferences, activity, knowledge, personal_data) + Redis goals, ~30-50ms
- Execution tools: READ from /workspace, /data/personal, /output. WRITE to /output only.
- Activity logging: fire-and-forget asyncio to Qdrant `activity` collection
- Qwen3 `<think>` blocks stripped before client delivery (3-layer: think tags → orphaned tags → untagged CoT preambles)
- NSFW content is explicitly allowed (Stash agent, Creative agent) — do not filter or moralize
- All agents report to Claude (COO), not directly to Shaun
