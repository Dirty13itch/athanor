---
name: cluster-status
description: Quick cluster health dashboard with live GPU, container, and disk status from all nodes
triggers:
  - "cluster status"
  - "cluster health"
  - "node status"
disable-model-invocation: true
---

# Athanor Cluster Status

Treat this skill as a read-only status helper, not a live authority surface. Refresh `python scripts/session_restart_brief.py --refresh` and consult the finish scoreboard/runtime packet inbox before treating the probe output below as current queue or deployment truth.

## FOUNDRY (192.168.1.244) — EPYC 7663, 256GB, 5 GPUs

### GPUs
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes foundry 'nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader' 2>/dev/null || echo "UNREACHABLE"`
```

### Containers
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes foundry 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -15' 2>/dev/null || echo "UNREACHABLE"`
```

### Disk & Memory
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes foundry 'echo "DISK:" && df -h / /mnt/vault/models 2>/dev/null | tail -2 && echo "RAM:" && free -h | head -2' 2>/dev/null || echo "UNREACHABLE"`
```

---

## WORKSHOP (192.168.1.225) — TR 7960X, 128GB, 2 GPUs

### GPUs
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes workshop 'nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader' 2>/dev/null || echo "UNREACHABLE"`
```

### Containers
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes workshop 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -15' 2>/dev/null || echo "UNREACHABLE"`
```

---

## VAULT (192.168.1.203) — 9950X, 128GB, Storage

### Containers
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes vault 'docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -20' 2>/dev/null || echo "UNREACHABLE"`
```

### Array
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes vault 'df -h /mnt/user 2>/dev/null | tail -1' 2>/dev/null || echo "UNREACHABLE"`
```

---

## DEV (192.168.1.189) — 9900X, 64GB, Ops Center

### Services
```
!`systemctl is-active local-system-gateway local-system-mind local-system-memory local-system-perception local-system-ui 2>/dev/null || echo "systemctl not available (running from Windows)"`
```

### GPU
```
!`ssh -o ConnectTimeout=3 -o BatchMode=yes dev 'nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader' 2>/dev/null || echo "UNREACHABLE or no SSH alias"`
```
