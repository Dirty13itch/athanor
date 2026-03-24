---
name: morning
description: Daily standup — overnight alerts, system health, task review, plan the day
user-invocable: true
---

Morning standup for Athanor. Run through this sequence:

1. **Briefing API** — Fetch the structured morning briefing:
   ```
   curl -s http://192.168.1.244:9000/v1/briefing | python3 -m json.tool
   ```
   This aggregates: node health (Redis heartbeats), overnight agent activity (Qdrant), task stats, Prometheus alerts, and RSS news (Miniflux). Display the markdown digest from the response.

   If the briefing endpoint is unreachable, fall back to manual checks:
   - SSH to foundry, workshop for `nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader`
   - VAULT via `python3 scripts/vault-ssh.py "uptime && df -h /mnt/user"`
   - Agent server: `curl -s http://192.168.1.244:9000/health`
   - LiteLLM: `curl -s http://192.168.1.203:4000/health`

2. **Task Review** — Check overnight task results:
   - `curl -s http://192.168.1.244:9000/v1/tasks?limit=10`
   - `curl -s http://192.168.1.244:9000/v1/tasks/stats`

3. **Prometheus Alerts**:
   - `curl -s 'http://192.168.1.203:9090/api/v1/alerts' | python3 -c "import json,sys; [print(f'  {a[\"labels\"][\"alertname\"]}: {a[\"state\"]}') for a in json.load(sys.stdin).get('data',{}).get('alerts',[])]"`

4. **State Review** — Read MEMORY.md and BUILD-MANIFEST.md for context

5. **Report** — Summarize in a compact table:
   - Infrastructure status (up/down/degraded)
   - GPU utilization summary
   - Overnight task results (completed/failed)
   - Active alerts
   - Next unblocked work items from BUILD-MANIFEST.md
   - Blockers requiring Shaun
