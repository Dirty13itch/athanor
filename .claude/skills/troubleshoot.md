---
name: Troubleshoot
description: Structured debugging methodology for infrastructure, services, agents, and deployment issues in Athanor.
---

# Troubleshoot

Systematic debugging for Athanor. Treat this skill as governed helper guidance only. Follow this order and treat the restart brief, runtime ownership report, and registry-backed surfaces as primary evidence; direct probes and helper commands are confirmation steps, not authority.

## Step 1: Gather Evidence (Don't Guess)

Start with `python scripts/session_restart_brief.py --refresh`, the relevant generated operations report, and the current registry-backed truth for the lane you are debugging. Use the direct probes below as confirmation after that first pass.

```bash
# Service health (confirmation probes)
curl -sf http://core.athanor.local:9000/health  # Agent server
curl -skf https://athanor.local/api/operator/session      # Canonical front door
curl -sf http://dev.athanor.local:3001/api/operator/session  # Command Center runtime fallback
curl -sf http://vault.athanor.local:4000/health   # LiteLLM

# Container status
ssh foundry 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
ssh workshop 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# Container logs (last 50 lines)
ssh <node> 'docker logs --tail 50 <container> 2>&1'

# GPU status
ssh foundry 'nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader'

# NFS mounts
ssh foundry 'mount | grep vault; ls /mnt/vault/models/ | head -3'

# Prometheus alerts
curl -sf 'http://vault.athanor.local:9090/api/v1/alerts' | jq '.data.alerts[] | {name: .labels.alertname, state: .state}'
```

## Step 2: Form Hypothesis

Based on evidence, identify the most likely cause. Common patterns:

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Container `Restarting` loop | OOM or startup crash | Check `docker logs`, increase memory/reduce batch size |
| NFS stale handle | VAULT rebooted | `sudo umount -f /mnt/vault/models && sudo mount -a` |
| vLLM 503/timeout | Model loading or GPU OOM | Check vLLM logs for OOM, reduce `--max-num-seqs` |
| Agent hangs | LiteLLM down or model asleep | Check VAULT LiteLLM health, restart if needed |
| Dashboard 500 | API proxy target down | Check agent server health on FOUNDRY |
| SSH timeout | Node down or network issue | `ping <alias-or-host>`, check power/BMC, then confirm current topology/runtime ownership before changing config |

## Step 3: Test Hypothesis

Run the minimal test to confirm or reject. Don't fix anything yet.

## Step 4: Fix

Apply the smallest possible change only after the current owned lane is clear from canonical reports. Verify the fix. Document it if it becomes a recurring gotcha.

## Step 5: Verify + Document

- Confirm the original symptom is resolved
- Check for collateral damage (other services affected?)
- If it's a new gotcha, add to the relevant rule file in `.claude/rules/`
- If it's a recurring issue, add monitoring/alerting for it
