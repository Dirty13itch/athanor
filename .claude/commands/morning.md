---
name: morning
description: Daily standup — overnight alerts, system health, task review, plan the day
user-invocable: true
---

Morning standup for Athanor. Run through this checklist:

1. **System Health** — Check all nodes, GPUs, and key services:
   - SSH to node1, node2 for quick `nvidia-smi` and `docker ps` checks
   - VAULT via `python3 scripts/vault-ssh.py "uptime && df -h /mnt/user"`
   - Agent server health: `curl -s http://192.168.1.244:9000/health`
   - Dashboard health: `curl -s http://192.168.1.225:3001`
   - LiteLLM health: `curl -s http://192.168.1.203:4000/health`

2. **Overnight Activity** — What happened while Shaun was away:
   - Check task stats: `curl -s http://192.168.1.244:9000/v1/tasks/stats`
   - Check recent tasks: `curl -s http://192.168.1.244:9000/v1/tasks?limit=10`
   - Check Prometheus alerts: `curl -s 'http://192.168.1.203:9090/api/v1/alerts' | jq '.data.alerts[] | {labels: .labels.alertname, state: .state}'`

3. **State Review** — Read MEMORY.md and BUILD-MANIFEST.md for context

4. **Report** — Summarize in a compact table:
   - Infrastructure status (up/down/degraded)
   - GPU utilization summary
   - Overnight task results (completed/failed)
   - Active alerts
   - Next unblocked work items from BUILD-MANIFEST.md
   - Blockers requiring Shaun
