---
description: Quick system health snapshot — nodes, GPUs, services, agents
allowed-tools: Bash(ssh:*), Bash(curl:*), Read, mcp__athanor-agents__system_status, mcp__athanor-agents__gpu_status
---

Get a quick Athanor system status. Use MCP tools first, fall back to direct SSH.

1. Check agent server health: `curl -sf http://192.168.1.244:9000/health`
2. Get GPU status via MCP: `mcp__athanor-agents__gpu_status`
3. Get system status via MCP: `mcp__athanor-agents__system_status`
4. Check dashboard: `curl -sf http://192.168.1.225:3001 -o /dev/null && echo "Dashboard UP" || echo "Dashboard DOWN"`
5. Check LiteLLM: `curl -sf http://192.168.1.203:4000/health`
6. Check Qdrant: `curl -sf http://192.168.1.244:6333/collections | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"result\"][\"collections\"])} collections')" 2>/dev/null`

Summarize as a compact table:

| Component | Status | Details |
|-----------|--------|---------|
| Foundry (Node 1) | ... | GPUs, vLLM, Agents |
| Workshop (Node 2) | ... | GPUs, Dashboard, ComfyUI |
| VAULT | ... | Services, Storage |
| Agents | ... | Count, health |
