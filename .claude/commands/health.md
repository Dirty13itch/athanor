---
name: health
description: Quick infrastructure health check — lighter than /morning, good for mid-session spot checks
user-invocable: true
---

Quick health check. Run these in parallel and report as a compact table:

1. **Nodes** — SSH ping to node1, node2. VAULT via `python3 scripts/vault-ssh.py "echo OK"`.
2. **Key Services** — curl health endpoints:
   - Agent server: `curl -sf http://192.168.1.244:9000/health`
   - Dashboard: `curl -sf -o /dev/null -w '%{http_code}' http://192.168.1.225:3001`
   - LiteLLM: `curl -sf http://192.168.1.203:4000/health`
3. **GPUs** — `ssh node1 'nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader'` and same for node2.

Report format:
```
| Node     | Status | GPUs | Key Services |
|----------|--------|------|-------------|
| Foundry  | UP     | 5/5  | agents OK, vLLM OK |
| Workshop | UP     | 2/2  | dashboard OK |
| VAULT    | UP     | -    | LiteLLM OK, Prometheus OK |
```

Flag anything degraded. Don't read any docs — just check live state.
