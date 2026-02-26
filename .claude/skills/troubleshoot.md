---
name: Troubleshoot
description: Structured debugging methodology for infrastructure, services, agents, and deployment issues in Athanor.
---

# Troubleshoot

Systematic debugging for Athanor. Follow this order — don't skip steps.

## Step 1: Gather Evidence (Don't Guess)

```bash
# Service health
curl -sf http://192.168.1.244:9000/health  # Agent server
curl -sf http://192.168.1.225:3001          # Dashboard
curl -sf http://192.168.1.203:4000/health   # LiteLLM

# Container status
ssh node1 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
ssh node2 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# Container logs (last 50 lines)
ssh <node> 'docker logs --tail 50 <container> 2>&1'

# GPU status
ssh node1 'nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader'

# NFS mounts
ssh node1 'mount | grep vault; ls /mnt/vault/models/ | head -3'

# Prometheus alerts
curl -sf 'http://192.168.1.203:9090/api/v1/alerts' | jq '.data.alerts[] | {name: .labels.alertname, state: .state}'
```

## Step 2: Form Hypothesis

Based on evidence, identify the most likely cause. Common patterns:

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Container `Restarting` loop | OOM or startup crash | Check `docker logs`, increase memory/reduce batch size |
| NFS stale handle | VAULT rebooted | `sudo umount -f /mnt/vault/models && sudo mount -a` |
| vLLM 503/timeout | Model loading or GPU OOM | Check vLLM logs for OOM, reduce `--max-num-seqs` |
| Agent hangs | LiteLLM down or model asleep | Check VAULT LiteLLM health, restart if needed |
| Dashboard 500 | API proxy target down | Check agent server health on Node 1 |
| SSH timeout | Node down or network issue | `ping <ip>`, check power/BMC |

## Step 3: Test Hypothesis

Run the minimal test to confirm or reject. Don't fix anything yet.

## Step 4: Fix

Apply the smallest possible change. Verify the fix. Document if it's a new gotcha.

## Step 5: Verify + Document

- Confirm the original symptom is resolved
- Check for collateral damage (other services affected?)
- If it's a new gotcha, add to the relevant rule file in `.claude/rules/`
- If it's a recurring issue, add monitoring/alerting for it
