---
paths:
  - "projects/agents/**"
  - "ansible/roles/vault-litellm/**"
  - "scripts/**"
---

# LiteLLM Routing

Proxy at VAULT:4000 (`http://192.168.1.203:4000`). All inference routes through LiteLLM — agents, dashboard, CLI tools, MCP.

Master key: `LITELLM_MASTER_KEY` env var (value in `~/.claude/mcp-vars.sh`). Also accepted as `OPENAI_API_KEY` for OpenAI-compatible tools.

Config file on VAULT: `/mnt/user/appdata/litellm/config.yaml`

## Model Aliases

| Alias | Backend Model | Location | Use |
|-------|---------------|----------|-----|
| `reasoning` | Qwen3.5-27B-FP8 TP=4 | FOUNDRY:8000 | Complex reasoning, architecture, agents |
| `fast` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Quick responses, low-latency |
| `coder` | Qwen3.5-35B-A3B-AWQ-4bit | FOUNDRY:8006 | Code generation |
| `grader` | Qwen3.5-35B-A3B-AWQ | WORKSHOP:8000 | Eval grading — thinking disabled at routing layer |
| `embedding` | Qwen3-Embedding-0.6B | DEV:8001 | 1024-dim vectors |
| `reranker` | Qwen3-Reranker-0.6B | DEV:8003 | Cross-encoder scoring |

Additional aliases on WORKSHOP (`worker`, `utility`, `creative`, `uncensored`) all route to the same 35B-A3B-AWQ backend.

## Config Changes

**Always backup before modifying:**
```bash
cp /opt/athanor/litellm/config.yaml /opt/athanor/litellm/config.yaml.bak.$(date +%s)
```

- Deploy changes via Ansible when playbook exists (`ansible/roles/vault-litellm/`)
- After manual edits: restart the LiteLLM container on VAULT
- Never modify running config without backup

## Health Check

```bash
curl -s http://192.168.1.203:4000/health/liveliness
curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://192.168.1.203:4000/v1/models | jq '.data[].id'
```

## Qwen3.5 Thinking Mode

Thinking is enabled by default — responses include `<think>` blocks.

Disable per-request when you need deterministic structured output:
```python
extra_body={"chat_template_kwargs": {"enable_thinking": False}}
```

Required for: JSON mode, grading tasks, structured data extraction, any prompt expecting plain output.

## LangFuse Integration

Traces auto-forwarded to LangFuse at VAULT:3030. Tag requests so they are filterable:
```python
extra_body={
    "metadata": {
        "trace_name": "agent-name",      # replaces "litellm-acompletion" in UI
        "tags": ["agent-name"],          # filter label
        "trace_metadata": {"agent": "agent-name"},
    }
}
```

Plain `metadata.agent` is NOT read by LangFuse — use the keys above.

## Debugging

1. Check which alias was called and confirm backend is healthy (`/health/liveliness`)
2. GPU utilization: `ssh foundry 'nvidia-smi'` / `ssh workshop 'nvidia-smi'`
3. High GPU util + queued requests = queue backup — reduce concurrency or reroute
4. LangFuse traces: compare time-to-first-token vs total generation time to isolate queue vs inference
5. LiteLLM UI: `http://192.168.1.203:4000/ui`

<!-- updated 2026-03-15 -->
