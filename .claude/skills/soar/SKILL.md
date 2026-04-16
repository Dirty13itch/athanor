---
name: soar
description: SOAR operating loop — Scan, Orient, Act, Record. Full cluster health assessment and prioritized action.
triggers:
  - "soar"
  - "ops check"
  - "cluster sweep"
---

# SOAR Operating Loop

Execute the full Scan-Orient-Act-Record cycle for the Athanor cluster.

## Live Cluster State

```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes foundry 'echo "FOUNDRY: UP"; nvidia-smi --query-gpu=index,name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null; docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null | head -10' 2>/dev/null || echo "FOUNDRY: UNREACHABLE"`
```

```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes workshop 'echo "WORKSHOP: UP"; nvidia-smi --query-gpu=index,name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null; docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null | head -10' 2>/dev/null || echo "WORKSHOP: UNREACHABLE"`
```

```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes vault 'echo "VAULT: UP"; docker ps --format "{{.Names}}" 2>/dev/null | wc -l; echo "containers running"; df -h / /mnt/user 2>/dev/null | tail -2' 2>/dev/null || echo "VAULT: UNREACHABLE"`
```

## Phase 1: SCAN
Review the live cluster state above. Check for:
- Crashed or restarting containers
- GPUs above 85C or with high memory but no workload
- Disk above 90% usage
- Unreachable nodes
- Services that should be running but aren't

## Phase 2: ORIENT
Prioritize findings by severity:
- **P0 BROKEN**: Services down, data at risk, cluster unusable
- **P1 TOIL**: Repetitive manual work that could be automated
- **P2 RISK**: Approaching limits (disk, memory, temp)
- **P3 FOUNDATION**: Infrastructure improvements for future work
- **P4 CAPABILITY**: New features, optimizations

## Phase 3: ACT
Pick the single highest-priority actionable item and execute it:
- If P0: Fix it immediately
- If P1-P4: Execute one complete item (research -> build -> test -> document)
- If nothing actionable: Report clean status

## Phase 4: RECORD
After acting:
1. Update STATUS.md with findings and actions taken
2. Git commit changes
3. Report summary to user

## Rules
- Evidence-based only — SSH into nodes, don't guess
- One action per cycle — depth over breadth
- If a fix requires Shaun (credentials, physical access, money), note it in BLOCKED section and move to next item
