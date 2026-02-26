# ADR-015: Backup Strategy

**Date:** 2026-02-24
**Status:** Accepted
**Depends on:** ADR-003 (Storage Architecture), 1.4 (Qdrant), 1.5 (Neo4j)

---

## Context

Athanor has no backup infrastructure. The Feb 2026 ZFS pool destruction proved this is a real risk — 1.9 TB of container appdata, model cache, and VM images were lost when the NVMe pool was destroyed during a motherboard swap. Unraid parity protects against single HDD failure but not against pool destruction, accidental deletion, or data corruption.

Critical data now exists in:
- **Qdrant** (Node 1) — 922 indexed knowledge chunks, conversation history
- **Neo4j** (VAULT) — infrastructure graph with 30+ entities, 29 relationships
- **Container appdata** (VAULT) — Plex metadata, Sonarr/Radarr configs, HA automations
- **Git repos** (DEV → GitHub) — Ansible, dashboard, agents, project code

---

## Decision

Implement a **daily automated backup** of databases and critical appdata to VAULT's HDD array (`/mnt/user/backups/athanor/`). Backups stored locally with 7-day retention. No off-site backup initially — add when remote access (Tailscale/WireGuard) is operational.

### What Gets Backed Up

| Data | Method | Source | Destination | Retention |
|------|--------|--------|-------------|-----------|
| Qdrant collections | Snapshot API | Node 1:6333 | VAULT `/mnt/user/backups/athanor/qdrant/` | 7 days |
| Neo4j graph | Cypher export | VAULT:7474 | VAULT `/mnt/user/backups/athanor/neo4j/` | 7 days |
| Container appdata | btrfs snapshot or tar | VAULT `/mnt/user/appdata/` | VAULT `/mnt/user/backups/athanor/appdata/` | 3 snapshots |
| Ansible + code | Git (GitHub) | DEV | GitHub (already pushed) | Full history |

### What Does NOT Get Backed Up

- **AI models** — downloadable, 80+ GB total, not worth backing up
- **Media files** — protected by Unraid parity, too large for backup (146 TB)
- **Transcodes/cache** — ephemeral by design
- **Docker images** — pulled from registries, rebuilt by Ansible

### Schedule

Daily at 03:00 CST via cron on each host. Qdrant backup runs on Node 1, Neo4j and appdata backups run on VAULT.

---

## Alternatives Considered

### Off-site to cloud (S3, Backblaze B2)
Rejected for now. Databases are small (<1 GB total) so cost would be trivial, but adds complexity. Revisit if off-site backup becomes a priority.

### Cross-node replication
Rejected. Adds network traffic for databases that can be re-seeded from Ansible in under an hour. The knowledge base can be re-indexed from docs in ~5 minutes. Not worth the operational overhead.

### Unraid btrfs snapshots only
Insufficient. Snapshots protect against accidental deletion but not against pool destruction (the exact failure mode from Feb 2026). Need file-level copies to the HDD array.

---

## Consequences

**Positive:**
- Daily backups of all critical mutable data
- 7-day retention allows recovery from delayed-discovery corruption
- Backup scripts are simple shell scripts — debuggable by Shaun alone
- Backup destination (HDD array) is parity-protected

**Negative:**
- No off-site backup — total loss of VAULT hardware means total data loss
- Backup monitoring is manual until Prometheus integration (future)
- Appdata backup may be large if Plex metadata grows

**Risks:**
- Qdrant snapshot API may lock briefly during snapshot creation — acceptable for 03:00 CST
- Neo4j Cypher export won't capture internal IDs — re-import creates new IDs (acceptable, relationships preserved by name)

---

## Implementation

1. Create `scripts/backup-qdrant.sh` — runs on Node 1, calls Qdrant snapshot API
2. Create `scripts/backup-neo4j.sh` — runs on VAULT, exports via Cypher HTTP API
3. Create `scripts/backup-appdata.sh` — runs on VAULT, tar critical appdata dirs
4. Create Ansible role `backup` to deploy scripts + cron jobs
5. Create backup destination directory on VAULT HDD array
