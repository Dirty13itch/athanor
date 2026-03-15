---
paths:
  - "ansible/roles/litellm/**"
  - "agents/**"
  - "projects/agents/**"
---

# LiteLLM Routing

Proxy at VAULT:4000. All inference routes through LiteLLM — agents, dashboard, CLI tools, MCP.

## Model Aliases

| Alias | Backend Model | Location | Use |
|-------|---------------|----------|-----|
| `reasoning` | Qwen3.5-27B-FP8 TP=4 | FOUNDRY:8000 | Complex reasoning, agents |
| `coding` | Qwen3.5-27B-FP8 TP=4 | FOUNDRY:8000 | Code generation (alias of reasoning) |
| `coder` | Qwen3.5-35B-A3B-AWQ-4bit | FOUNDRY:8006 | Dedicated coding lane |
| `worker` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | General tasks |
| `fast` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Low-latency |
| `utility` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Utility tasks |
| `creative` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Creative |
| `uncensored` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Unfiltered |
| `embedding` | Qwen3-Embedding-0.6B | DEV:8001 | Embeddings (1024-dim) |
| `reranker` | Qwen3-Reranker-0.6B | DEV:8003 | Reranking |

## Health Check

```bash
curl -s http://192.168.1.203:4000/health
curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.203:4000/v1/models | jq '.data[].id'
```

## Config Changes

1. Config location: `/opt/litellm/config.yaml` on VAULT
2. **Always backup first:** `cp config.yaml config.yaml.bak.$(date +%s)`
3. Deploy via Ansible when playbook exists
4. After change: restart LiteLLM container on VAULT

## Debugging Slow Requests

1. Identify which model alias was called
2. Check GPU utilization: `ssh node1 'nvidia-smi'` / `ssh node2 'nvidia-smi'`
3. High GPU util + many pending requests = queue backup (reduce concurrency or route elsewhere)
4. LangFuse traces: check time-to-first-token vs total generation time
5. LiteLLM dashboard: `http://192.168.1.203:4000/ui`

## Credentials

- Master key: stored in `~/.claude/mcp-vars.sh` as `LITELLM_MASTER_KEY`
- Env var: `OPENAI_API_KEY` (same value, for OpenAI-compatible tools)
