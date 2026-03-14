# Athanor Disaster Recovery

*Last updated: 2026-03-14*

---

## Overview

This document covers recovery procedures for the Athanor cluster. VAULT is the most critical node — all databases, routing, and monitoring run there. A VAULT failure is a full-system outage; treat it as the primary recovery scenario.

**RTO target:** 2–4 hours (full cluster)
**RPO target:** 24 hours (daily backups at 03:00–03:30)

---

## Quick Reference

| Node | IP | SSH | Most Critical Services |
|------|-----|-----|----------------------|
| VAULT | 192.168.1.203 | `python3 scripts/vault-ssh.py` or `ssh root@192.168.1.203` | LiteLLM, Redis, Qdrant, Neo4j, Postgres |
| FOUNDRY | 192.168.1.244 | `ssh foundry` | vLLM (inference), Agent Server |
| WORKSHOP | 192.168.1.225 | `ssh workshop` | vLLM (worker), Dashboard, ComfyUI |
| DEV | 192.168.1.189 | local | Embedding, Reranker, Claude Code |

**VAULT SSH note:** Root password login is disabled on Unraid. Key-only auth. Persistent keys at `/boot/config/ssh/root/.ssh/authorized_keys`. Use `python3 scripts/vault-ssh.py` if native SSH hangs.

---

## Service Recovery Order

Restore in this order — later services depend on earlier ones:

1. **Redis** — task state, GWT workspace, scheduler, agent cache
2. **Qdrant** — knowledge, conversations, signals, activity, preferences
3. **Neo4j** — knowledge graph (3095 nodes, 4447 relationships)
4. **Postgres** — LangFuse, Miniflux, field-inspect databases
5. **LiteLLM** — model routing (all inference depends on this)
6. **vLLM (FOUNDRY)** — Qwen3.5-27B-FP8 TP=4 coordinator, Qwen3.5-35B-A3B-AWQ-4bit
7. **vLLM (WORKSHOP)** — Qwen3.5-35B-A3B-AWQ worker
8. **Agent Server** — 9 agents on FOUNDRY:9000
9. **Monitoring** — Prometheus, Grafana, Loki, Alloy
10. **Dashboard** — Command Center on WORKSHOP:3001

---

## Scenario 1: VAULT Failure (Full or Partial)

### 1.1 Assess what's down

```bash
python3 scripts/vault-ssh.py
# Or: ssh root@192.168.1.203
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

If Docker is up but containers are down, restart via compose:

```bash
cd /mnt/user/appdata/<service>
docker compose up -d
```

### 1.2 LiteLLM routing down

All inference fails without LiteLLM. Restore first after databases.

```bash
# On VAULT
cd /mnt/user/appdata/litellm
docker compose up -d

# Verify
curl http://192.168.1.203:4000/health
```

Config lives at: `/mnt/user/appdata/litellm/config.yaml`
Backup: see `scripts/backup-appdata.sh` (daily, 03:30)

### 1.3 Redis down

Agents lose task state. GWT workspace is cleared. Redis is stateful — no persistent storage by default unless configured.

```bash
# Check if just a container crash
docker start redis

# If data volume is corrupt, restore from Qdrant/Neo4j
# (Redis state is ephemeral — agents rebuild on startup)
```

### 1.4 Qdrant down (VAULT instance)

The primary Qdrant is on FOUNDRY:6333. VAULT:6333 is a secondary instance used by VAULT-local services.

```bash
# Restore from backup
scripts/backup-qdrant.sh  # verify backup exists first

# Start container
cd /mnt/user/appdata/qdrant
docker compose up -d
```

### 1.5 Neo4j down

Knowledge graph restoration. Data survives container restarts if volume is intact.

```bash
# Check volume
docker volume inspect neo4j_data

# Start container
cd /mnt/user/appdata/neo4j
docker compose up -d

# Verify
curl http://192.168.1.203:7474
```

Restore from backup: see `scripts/backup-neo4j.sh`

### 1.6 Postgres down

LangFuse, Miniflux, and field-inspect all depend on separate Postgres instances.

```bash
# Start shared Postgres
cd /mnt/user/appdata/postgres
docker compose up -d

# LangFuse has its own dedicated postgres container
cd /mnt/user/appdata/langfuse
docker compose up -d
```

---

## Scenario 2: FOUNDRY Failure

FOUNDRY runs inference (TP=4 coordinator) and all 9 agents. Loss degrades to Workshop-only inference at reduced throughput.

### 2.1 Verify from DEV

```bash
ssh foundry
docker ps
nvidia-smi
```

### 2.2 Restart inference

```bash
# On FOUNDRY
cd /opt/athanor/vllm
docker compose up -d vllm-coordinator vllm-coder

# Monitor startup (takes ~90s for Triton compile on cold start)
docker logs -f vllm-coordinator
```

### 2.3 Restart Agent Server

```bash
cd /opt/athanor/agents
docker compose up -d athanor-agents

# Verify all 9 agents healthy
curl http://192.168.1.244:9000/v1/agents
```

### 2.4 EPYC POST delay

FOUNDRY takes ~3 minutes to POST (224 GB ECC RAM check). If the node is rebooting, wait the full 3 minutes before SSH attempts.

---

## Scenario 3: WORKSHOP Failure

WORKSHOP runs the worker inference lane, dashboard, ComfyUI, and EoBQ.

```bash
ssh workshop
docker ps
nvidia-smi

# Restart worker inference
cd /opt/athanor/vllm
docker compose up -d vllm-node2

# Restart dashboard
cd /opt/athanor/dashboard
docker compose up -d athanor-dashboard
```

---

## Scenario 4: DEV Failure

DEV runs Claude Code, embedding, and reranker. LiteLLM falls back to cloud embedding if DEV embedding is unavailable.

```bash
# On DEV (local)
docker ps
docker start vllm-embedding vllm-reranker
```

---

## Backup Procedures

### Existing Scripts

| Script | What | Schedule | Location |
|--------|------|----------|----------|
| `scripts/backup-qdrant.sh` | Qdrant snapshots (all collections) | Daily 03:00 FOUNDRY cron | `/opt/athanor/backups/qdrant/` |
| `scripts/backup-neo4j.sh` | Neo4j dump | Daily VAULT cron | `/mnt/appdatacache/backups/neo4j/` |
| `scripts/backup-appdata.sh` | VAULT appdata configs | Daily 03:30 VAULT cron | `/mnt/appdatacache/backups/appdata/` |

### Verify Backups Are Fresh

```bash
# Check backup timestamps
ls -lht /opt/athanor/backups/qdrant/          # on FOUNDRY
ls -lht /mnt/appdatacache/backups/            # on VAULT

# Grafana alert: backup-exporter (VAULT:9199) exports backup age metrics
curl http://192.168.1.203:9199/metrics | grep backup_age
```

### Qdrant Restore

```bash
# List available snapshots
ls /opt/athanor/backups/qdrant/

# Restore specific collection via API
curl -X POST "http://localhost:6333/collections/{collection}/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "file:///opt/athanor/backups/qdrant/{snapshot}.snapshot"}'
```

### Neo4j Restore

```bash
# Stop Neo4j
docker stop neo4j

# Restore dump
neo4j-admin database load --from=/mnt/appdatacache/backups/neo4j/neo4j.dump neo4j --overwrite-destination

# Start Neo4j
docker start neo4j
```

---

## Key Config File Locations

| Service | Config Path | Node |
|---------|------------|------|
| LiteLLM | `/mnt/user/appdata/litellm/config.yaml` | VAULT |
| vLLM coordinator | `/opt/athanor/vllm/docker-compose.yml` | FOUNDRY |
| vLLM worker | `/opt/athanor/vllm/docker-compose.yml` | WORKSHOP |
| Agent Server | `/opt/athanor/agents/docker-compose.yml` | FOUNDRY |
| Dashboard | `/opt/athanor/dashboard/docker-compose.yml` | WORKSHOP |
| Ansible vars | `ansible/group_vars/all/main.yml` | DEV (repo) |
| Ansible vault | `ansible/vault.yml` (encrypted) | DEV (repo) |

---

## Credential Locations

- **Primary secrets:** `.claude/CLAUDE.local.md` (not committed, on DEV)
- **Ansible secrets:** Ansible vault (`ansible/vault.yml`) — vault password stored per Ansible config
- **Service API keys:** Docker compose `.env` files at `/opt/athanor/<service>/` on each node
- **VAULT persistent SSH keys:** `/boot/config/ssh/root/.ssh/authorized_keys` (survives Unraid reboots)
- **LangFuse:** `pk-lf-athanor:sk-lf-athanor` basic auth at `http://192.168.1.203:3030`

**Never search for credentials in tracked docs.** If a key isn't in `.claude/CLAUDE.local.md` or the Ansible vault, SSH to the relevant node and check the compose `.env`.

---

## Deploy via Ansible (preferred)

Always prefer Ansible over manual SSH for reproducible restores:

```bash
# Full VAULT stack
ansible-playbook playbooks/vault.yml

# Specific service
ansible-playbook playbooks/vault.yml --tags litellm

# Foundry agents
ansible-playbook playbooks/foundry.yml --tags agents

# Full site
ansible-playbook playbooks/site.yml
```

Playbooks are at `ansible/playbooks/`. Roles at `ansible/roles/`.

---

## NFS Stale Handles (after VAULT reboot)

FOUNDRY and WORKSHOP mount `/mnt/vault/models/` from VAULT over NFS. After VAULT reboots:

```bash
# On FOUNDRY and WORKSHOP
sudo umount -f /mnt/vault/models
sudo mount -a
```

If models were loading from NFS at time of VAULT failure, vLLM containers will need restart after remount.

---

*See also: `docs/SERVICES.md` (full service inventory), `ansible/` (deployment automation), `scripts/` (backup and ops scripts)*
