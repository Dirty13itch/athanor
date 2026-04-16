---
paths:
  - "projects/agents/**"
  - "ansible/roles/vault-litellm/**"
  - "scripts/**"
---

# LiteLLM Routing

This rule file is stable bootstrap guidance only. Verify live endpoint, alias, and gateway truth in `python scripts/session_restart_brief.py --refresh`, `config/automation-backbone/provider-catalog.json`, `docs/operations/PROVIDER-CATALOG-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, and the current runtime/provider reports before treating any host or alias below as authoritative.

Current inference is intended to route through the governed LiteLLM surface, but live gateway truth must come from the registry-backed provider/runtime surfaces first. Use the hosts, aliases, model names, and UI URLs below as convenience references that still require live confirmation; they are not queue or routing authority.

Master key: `LITELLM_MASTER_KEY` env var (value in `~/.claude/mcp-vars.sh`). Also accepted as `OPENAI_API_KEY` for OpenAI-compatible tools.

Current config file path to verify before mutation: `/mnt/user/appdata/litellm/config.yaml`

## Model Aliases (Reference Only; Verify Live Registry First)

| Alias | Backend Model | Location | Use |
|-------|---------------|----------|-----|
| `reasoning` | dolphin3-r1-24b | FOUNDRY:8100 | Complex reasoning and agent fallbacks on the consolidated live lane |
| `fast` | dolphin3-r1-24b | FOUNDRY:8100 | Quick responses on the current healthy primary lane |
| `coder` | dolphin3-r1-24b | FOUNDRY:8100 | Code generation and primary chat routing |
| `grader` | dolphin3-r1-24b | FOUNDRY:8100 | Eval grading - thinking disabled at routing layer |
| `embedding` | Qwen3-Embedding-0.6B | DEV:8001 | 1024-dim vectors |
| `reranker` | Qwen3-Reranker-0.6B | DEV:8003 | Cross-encoder scoring |

Additional aliases may currently consolidate onto the same healthy text lane, but alias ownership and consolidation must be rechecked in the live provider catalog and runtime reports before operational use.

## Config Changes

Treat the commands below as operator helper references only; canonical approval and live posture still come from the restart brief, provider catalog, and runtime ownership surfaces.

**Always backup before modifying:**
```bash
cp /opt/athanor/litellm/config.yaml /opt/athanor/litellm/config.yaml.bak.$(date +%s)
```

- Deploy changes via Ansible when playbook exists (`ansible/roles/vault-litellm/`)
- After manual edits: restart the LiteLLM container on VAULT
- Never modify running config without backup

## Health Check (Secondary Confirmation Only)

Use these after checking the provider catalog and runtime ownership reports, not instead of them.

```bash
curl -s http://vault.athanor.local:4000/health/liveliness
curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://vault.athanor.local:4000/v1/models | jq '.data[].id'
```

## Qwen3.5 Thinking Mode

Thinking is enabled by default — responses include `<think>` blocks.

Disable per-request when you need deterministic structured output:
```python
extra_body={"chat_template_kwargs": {"enable_thinking": False}}
```

Required for: JSON mode, grading tasks, structured data extraction, any prompt expecting plain output.

## LangFuse Integration

Traces are expected to flow to the governed LangFuse surface when that path is healthy. Tag requests so they are filterable:
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
5. LiteLLM UI (verify current host first): `http://vault.athanor.local:4000/ui`

<!-- updated 2026-03-15 -->
