---
description: Quick system health snapshot — nodes, GPUs, services, agents
allowed-tools: Bash(ssh:*), Bash(curl:*), Read, mcp__athanor-agents__system_status, mcp__athanor-agents__gpu_status
---

Get a quick Athanor status snapshot. Use `python scripts/session_restart_brief.py --refresh`, `reports/truth-inventory/finish-scoreboard.json`, `reports/truth-inventory/runtime-packet-inbox.json`, MCP tools, and generated status reports first; treat direct probes as convenience checks, then prefer governed host aliases and canonical hostnames before any raw-IP fallback.

Treat the endpoint and service checks below as convenience probes only, not canonical service truth. Verify current registry-backed status, report surfaces, the restart brief, and the finish/runtime inbox surfaces before assuming any host, port, route, queue state, or lane is still live.

1. Refresh the governed posture surface: `python scripts/session_restart_brief.py --refresh`
2. Get GPU status via MCP: `mcp__athanor-agents__gpu_status`
3. Get system status via MCP: `mcp__athanor-agents__system_status`
4. Check agent server health as a convenience probe: `curl -sf http://core.athanor.local:9000/health`
5. Check registry-backed operator front door: `curl -skf https://athanor.local/api/operator/session -o /dev/null && echo "Command Center FRONT DOOR UP" || echo "Command Center FRONT DOOR DOWN"`
6. Check registry-backed runtime fallback: `curl -sf http://dev.athanor.local:3001/api/operator/session -o /dev/null && echo "Command Center RUNTIME UP" || echo "Command Center RUNTIME DOWN"`
7. Check LiteLLM as secondary confirmation: `curl -sf http://vault.athanor.local:4000/health`
8. Check Qdrant as secondary confirmation: `curl -sf http://vault.athanor.local:6333/collections | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"result\"][\"collections\"])} collections')" 2>/dev/null`

Summarize as a compact table:

| Component | Status | Details |
|-----------|--------|---------|
| FOUNDRY | ... | GPUs, vLLM, Agents |
| WORKSHOP | ... | GPUs, Dashboard, ComfyUI |
| VAULT | ... | Services, Storage |
| Agents | ... | Count, health |
