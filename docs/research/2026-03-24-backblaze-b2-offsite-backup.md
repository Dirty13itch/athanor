# Backblaze B2 Offsite Backup for Athanor

**Date:** 2026-03-24
**Context:** ADR-015 deferred offsite backup. RECOVERY.md identifies "Duplicati to Backblaze B2" as a blocker. VAULT is the single point of failure -- all databases, routing, monitoring, media. Local backups exist (Qdrant/Neo4j/Postgres/Stash/Appdata daily to VAULT HDDs) but a VAULT hardware failure means total data loss.

---

## 1. Backblaze B2 Pricing (as of March 2026)

### Storage

| Tier | Cost | Notes |
|------|------|-------|
| Pay-As-You-Go | **$6/TB/month** ($0.006/GB) | First 10 GB free |
| B2 Reserve | $0.0065/TB/month | Annual commit, 20 TB minimum |
| B2 Overdrive | $15/TB/month | Unlimited egress, higher throughput |

### Egress (Download)

| Scenario | Cost |
|----------|------|
| Within free allowance (3x avg storage) | **Free** |
| Beyond free allowance | $0.01/GB |
| To CDN partners (Cloudflare, Fastly, Vultr, etc.) | **Free, unlimited** |

For 550 GB stored, free egress = 1,650 GB/month. Disaster recovery downloads will never hit that.

### API Calls

| Class | Operations | Cost |
|-------|-----------|------|
| A (uploads) | b2_upload_file, PutObject | **Free** |
| B (downloads) | b2_download_file, GetObject, HeadObject | First 2,500/day free, then $0.004/10K |
| C (listing/admin) | ListObjectsV2, b2_list_buckets, b2_copy_file | First 2,500/day free, then $0.004/1K |

**Note:** Backblaze announced that starting May 1, 2026, all standard API calls will be free for all customers.

### No Charges For

- Uploads (ingress always free)
- Minimum file size
- Minimum storage duration
- Delete operations

**Sources:**
- https://www.backblaze.com/cloud-storage/pricing
- https://www.backblaze.com/cloud-storage/transaction-pricing
- https://noise.getoto.net/2026/03/17/backblaze-pricing-and-product-updates/

---

## 2. Estimated Monthly Cost

| Data Set | Size | Monthly Storage Cost |
|----------|------|---------------------|
| Qdrant snapshots (all collections) | ~2 GB compressed | $0.01 |
| Neo4j dump | ~50 MB | $0.00 |
| PostgreSQL dumps (LangFuse, etc.) | ~500 MB | $0.00 |
| Redis RDB | ~50 MB | $0.00 |
| Stash DB | ~200 MB | $0.00 |
| Docker compose + configs (all nodes) | ~100 MB | $0.00 |
| Agent code + config (/opt/athanor/agents) | ~500 MB | $0.00 |
| Appdata configs (Plex meta, Sonarr/Radarr DBs) | ~5 GB | $0.03 |
| **Subtotal: Critical state** | **~8 GB** | **$0.05** |
| Personal data (Google Drive subset on VAULT NFS) | ~500 GB | $3.00 |
| **Total** | **~508 GB** | **~$3.05/month** |

With 30-day retention of daily snapshots for DB state (~8 GB x 30 = ~240 GB worst case), and personal data as a single current copy:

**Realistic monthly cost: $4-5/month.**

Egress for disaster recovery: free (well within 3x allowance). This is essentially rounding error against the $543/month subscription spend.

---

## 3. rclone B2 Setup

### 3.1 Create B2 Application Key

1. Log in to https://secure.backblaze.com
2. Create a bucket: `athanor-backups` (private, default encryption, no lifecycle rules)
3. Create an **Application Key** (not Master Key) scoped to `athanor-backups` bucket
4. Save the `keyID` and `applicationKey` -- the key is shown only once

### 3.2 Configure rclone Remote

```bash
rclone config

# Choose: n (new remote)
# Name: b2-athanor
# Type: b2 (Backblaze B2)
# Account: <applicationKeyId>   (NOT the master Account ID)
# Key: <applicationKey>
# Endpoint: (leave blank)
```

Resulting config (`~/.config/rclone/rclone.conf`):
```ini
[b2-athanor]
type = b2
account = 004xxxxxxxxxxxx0000000001
key = K004xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3.3 Add Encryption Layer (rclone crypt)

Client-side encryption before upload. Backblaze never sees plaintext.

```bash
rclone config

# Choose: n (new remote)
# Name: b2-encrypted
# Type: crypt
# Remote: b2-athanor:athanor-backups
# Filename encryption: standard
# Directory name encryption: true
# Password: (enter a strong password or let rclone generate one)
# Password2 (salt): (enter a different password or let rclone generate one)
```

Resulting config:
```ini
[b2-encrypted]
type = crypt
remote = b2-athanor:athanor-backups
password = *** ENCRYPTED ***
password2 = *** ENCRYPTED ***
```

**Critical: Back up `rclone.conf` separately** (e.g., in a password manager). If you lose the config, the encrypted data is unrecoverable. The encryption uses NaCl SecretBox (XSalsa20 + Poly1305) with Scrypt key derivation -- there is no password reset.

### 3.4 Key rclone Flags for B2

| Flag | Purpose |
|------|---------|
| `--transfers 16` | Parallel uploads (default 4 is too conservative for homelab upload bandwidth) |
| `--fast-list` | Reduce API calls by batching listings (uses more RAM) |
| `--b2-hard-delete` | Actually delete files instead of hiding them (B2 default is hide = you still pay for storage) |
| `--log-file /var/log/athanor-b2-backup.log` | Persistent logging |
| `--log-level INFO` | Sufficient for debugging without noise |
| `--stats 30s --stats-one-line` | Progress reporting to log |
| `--bwlimit 50M` | Optional: limit to 50 MB/s to not saturate uplink during business hours |

### 3.5 sync vs copy

| Command | Behavior | Use For |
|---------|----------|---------|
| `rclone copy` | Upload new/changed files only. Never deletes remote files. | Personal data (accidental local deletion won't propagate) |
| `rclone sync` | Mirror source to dest. Deletes remote files not in source. | DB snapshots with retention (old snapshots pruned locally, then synced) |
| `rclone copy --max-age 24h` | Only upload files modified in last 24h | Incremental config backup |

**Recommendation:** Use `copy` for personal data (safe -- won't delete remote if local file is removed). Use `sync` for DB snapshots where local retention scripts already manage the lifecycle.

---

## 4. What to Back Up

### Tier 1: Critical State (daily, 30-day retention)

These are the things you cannot rebuild from code/Ansible:

| Data | Source | Backup Method | Size |
|------|--------|---------------|------|
| **Qdrant snapshots** | VAULT .203:6333 (also FOUNDRY .244:6333) | POST `/snapshots` (full storage snapshot), download `.snapshot` file, upload to B2 | ~2 GB |
| **Neo4j dump** | VAULT .203:7474 | `neo4j-admin database dump` or Cypher HTTP export | ~50 MB |
| **PostgreSQL** | VAULT .203:5432 | `pg_dumpall` or per-DB `pg_dump` | ~500 MB |
| **Redis RDB** | VAULT .203:6379 | `redis-cli BGSAVE` then copy `/data/dump.rdb` | ~50 MB |
| **Stash DB** | VAULT .203:9999 | SQLite copy from appdata | ~200 MB |

### Tier 2: Configs and Code (daily, 7-day retention)

Rebuildable from Ansible/Git but saves hours of reconfiguration:

| Data | Source | Method | Size |
|------|--------|--------|------|
| **Docker compose files** | All 4 nodes | rsync from each node's `/opt/athanor/*/docker-compose.yml` + `.env` | ~10 MB |
| **Appdata configs** | VAULT `/mnt/user/appdata/` subset | tar selected dirs (Plex DB, Sonarr/Radarr DB, HA config, Grafana dashboards) | ~5 GB |
| **Agent code + config** | FOUNDRY `/opt/athanor/agents/` | rsync | ~500 MB |
| **LiteLLM config** | VAULT | Copy `proxy_config.yaml` + env files | ~1 MB |
| **Grafana dashboards** | VAULT .203:3000 | API export or file copy | ~5 MB |
| **Prometheus config** | VAULT | Copy `prometheus.yml` + rules | ~1 MB |

### Tier 3: Personal Data (weekly, single copy)

| Data | Source | Method | Size |
|------|--------|--------|------|
| **Google Drive mirror** | VAULT NFS or DEV staging `/home/shaun/data/personal/` | rclone copy | ~37 GB |
| **Selected VAULT NFS data** | VAULT `/mnt/user/data/` subset | rclone copy (documents, photos, important archives) | ~500 GB |

### What NOT to Back Up

- AI models (80+ GB, downloadable from HuggingFace)
- Media library (135+ TB, protected by Unraid parity, too expensive for B2)
- Docker images (pulled from registries)
- Transcodes/cache (ephemeral)
- Logs (ephemeral)

---

## 5. Recommended Script Structure

The script runs from **VAULT** (where most data lives and local backups already land). It uploads the local backup files to B2.

```bash
#!/usr/bin/env bash
set -euo pipefail

# backup-b2.sh — Upload local backups to Backblaze B2
#
# Expects local backups to already exist (created by backup-qdrant.sh,
# backup-neo4j.sh, backup-postgres.sh etc. running earlier in the night).
#
# Schedule: Daily at 05:00 CST (after all local backup jobs finish by ~04:30)
#
# Usage:
#   backup-b2.sh              # full upload
#   backup-b2.sh --dry-run    # show what would transfer
#   backup-b2.sh --tier1      # databases only
#   backup-b2.sh --tier2      # configs only
#   backup-b2.sh --tier3      # personal data only
#   backup-b2.sh -h           # help

# ─── Config ──────────────────────────────────────────────────────────────────

REMOTE="b2-encrypted"                          # rclone crypt remote wrapping B2
LOG="/var/log/athanor-b2-backup.log"
DRY_RUN=""
TIER_FILTER=""

# Local backup directories (populated by nightly cron jobs)
QDRANT_BACKUP_DIR="/mnt/user/data/backups/qdrant"
NEO4J_BACKUP_DIR="/mnt/user/data/backups/neo4j"
POSTGRES_BACKUP_DIR="/mnt/user/data/backups/postgres"
REDIS_BACKUP_DIR="/mnt/user/data/backups/redis"    # or wherever BGSAVE lands
STASH_BACKUP_DIR="/mnt/user/data/backups/stash"
APPDATA_BACKUP_DIR="/mnt/appdatacache/backups/appdata"
PERSONAL_DATA_DIR="/mnt/user/data/personal"         # adjust to actual path

# Remote paths
REMOTE_DB="${REMOTE}:databases"
REMOTE_CONFIG="${REMOTE}:configs"
REMOTE_PERSONAL="${REMOTE}:personal"

# rclone common flags
RCLONE_FLAGS=(
    --transfers 16
    --fast-list
    --b2-hard-delete
    --log-file "$LOG"
    --log-level INFO
    --stats 30s
    --stats-one-line
)

# ─── Args ────────────────────────────────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --dry-run|-n) DRY_RUN="--dry-run" ;;
        --tier1) TIER_FILTER="tier1" ;;
        --tier2) TIER_FILTER="tier2" ;;
        --tier3) TIER_FILTER="tier3" ;;
        -h|--help)
            echo "Usage: $0 [--dry-run|-n] [--tier1|--tier2|--tier3] [-h]"
            echo ""
            echo "Upload local Athanor backups to Backblaze B2 (encrypted)."
            echo "  --dry-run   Show what would upload without transferring"
            echo "  --tier1     Databases only (Qdrant, Neo4j, Postgres, Redis, Stash)"
            echo "  --tier2     Configs only (appdata, compose files)"
            echo "  --tier3     Personal data only"
            exit 0
            ;;
    esac
done

# ─── Helpers ─────────────────────────────────────────────────────────────────

log() { echo "$(date -Iseconds) $1" >&2; }

upload_sync() {
    local src="$1" dest="$2" label="$3"
    if [[ ! -d "$src" ]]; then
        log "SKIP $label — source dir missing: $src"
        return 0
    fi
    log "SYNC $label: $src → $dest"
    rclone sync "$src" "$dest" "${RCLONE_FLAGS[@]}" ${DRY_RUN:+"$DRY_RUN"} 2>&1
    log "DONE $label"
}

upload_copy() {
    local src="$1" dest="$2" label="$3"
    if [[ ! -d "$src" ]]; then
        log "SKIP $label — source dir missing: $src"
        return 0
    fi
    log "COPY $label: $src → $dest"
    rclone copy "$src" "$dest" "${RCLONE_FLAGS[@]}" ${DRY_RUN:+"$DRY_RUN"} 2>&1
    log "DONE $label"
}

should_run() {
    [[ -z "$TIER_FILTER" || "$TIER_FILTER" == "$1" ]]
}

# ─── Tier 1: Databases ──────────────────────────────────────────────────────

if should_run "tier1"; then
    log "=== TIER 1: Databases ==="
    upload_sync "$QDRANT_BACKUP_DIR"   "${REMOTE_DB}/qdrant"   "Qdrant snapshots"
    upload_sync "$NEO4J_BACKUP_DIR"    "${REMOTE_DB}/neo4j"    "Neo4j dumps"
    upload_sync "$POSTGRES_BACKUP_DIR" "${REMOTE_DB}/postgres" "PostgreSQL dumps"
    upload_sync "$REDIS_BACKUP_DIR"    "${REMOTE_DB}/redis"    "Redis RDB"
    upload_sync "$STASH_BACKUP_DIR"    "${REMOTE_DB}/stash"    "Stash DB"
fi

# ─── Tier 2: Configs ────────────────────────────────────────────────────────

if should_run "tier2"; then
    log "=== TIER 2: Configs ==="
    upload_sync "$APPDATA_BACKUP_DIR" "${REMOTE_CONFIG}/appdata" "Appdata configs"

    # Collect docker-compose + .env from all nodes into a staging dir
    COMPOSE_STAGING="/tmp/b2-compose-staging"
    mkdir -p "$COMPOSE_STAGING"/{foundry,workshop,vault,dev}

    # VAULT (local)
    cp /opt/athanor/*/docker-compose.yml "$COMPOSE_STAGING/vault/" 2>/dev/null || true
    cp /opt/athanor/*/.env "$COMPOSE_STAGING/vault/" 2>/dev/null || true

    # Remote nodes (SSH)
    for node_pair in "node1:foundry" "node2:workshop" "dev:dev"; do
        node="${node_pair%%:*}"
        label="${node_pair##*:}"
        ssh "$node" 'find /opt/athanor -maxdepth 2 -name "docker-compose.yml" -o -name ".env" 2>/dev/null' | while read -r f; do
            scp -q "$node:$f" "$COMPOSE_STAGING/$label/$(basename "$(dirname "$f")")-$(basename "$f")" 2>/dev/null || true
        done
    done

    upload_sync "$COMPOSE_STAGING" "${REMOTE_CONFIG}/compose" "Docker compose files"
    rm -rf "$COMPOSE_STAGING"
fi

# ─── Tier 3: Personal Data ──────────────────────────────────────────────────

if should_run "tier3"; then
    log "=== TIER 3: Personal Data ==="
    # Use copy (not sync) — never delete remote if local file is removed
    upload_copy "$PERSONAL_DATA_DIR" "${REMOTE_PERSONAL}" "Personal data"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────

log "=== B2 Backup Complete ==="
if [[ -z "$DRY_RUN" ]]; then
    # Show remote usage
    rclone size "${REMOTE}:" 2>/dev/null | head -5 >&2 || true
fi
```

### Cron Entry (on VAULT)

```bash
# /boot/config/go (Unraid persistent cron)
# After local backups finish (~04:30), upload to B2 at 05:00
echo "0 5 * * * /opt/athanor/scripts/backup-b2.sh >> /var/log/athanor-b2-backup.log 2>&1" >> /var/spool/cron/crontabs/root

# Personal data weekly (Sunday 06:00)
echo "0 6 * * 0 /opt/athanor/scripts/backup-b2.sh --tier3 >> /var/log/athanor-b2-backup.log 2>&1" >> /var/spool/cron/crontabs/root
```

### Verify It Works

```bash
# Test with dry-run first
backup-b2.sh --dry-run

# Check a single tier
backup-b2.sh --tier1

# Verify remote contents
rclone ls b2-encrypted:databases/qdrant/ | head
rclone size b2-encrypted:

# Test restore (download a file)
rclone copy b2-encrypted:databases/neo4j/latest.dump /tmp/neo4j-restore-test/
```

---

## 6. rclone vs Duplicati vs restic

RECOVERY.md mentions "Duplicati to Backblaze B2." Here's a quick comparison:

| Feature | rclone | Duplicati | restic |
|---------|--------|-----------|--------|
| B2 support | Native, first-class | Native | Native |
| Client-side encryption | rclone crypt (XSalsa20) | AES-256 built-in | AES-256 built-in |
| Deduplication | No | Block-level | Content-defined chunking |
| Incremental backups | File-level (copy only changed) | Block-level | Block-level |
| Compression | No | Yes (zip) | Yes (zstd) |
| Retention policies | Manual (prune locally) | Built-in schedules | Built-in `forget` policies |
| GUI | No (CLI only) | Web GUI | No (CLI only) |
| Restore complexity | Simple (just download) | Need Duplicati to restore | Need restic to restore |
| Homelab fit | Best for file sync | Best for set-and-forget | Best for versioned archives |
| Failure mode | Transparent (files are files) | Opaque (block-level chunks) | Opaque (repos) |

**Recommendation: rclone.** For this use case:
- The local backup scripts already handle retention and snapshots
- rclone just needs to mirror the local backup dirs to B2
- Encrypted files on B2 are still individual files, not opaque block stores
- Restore is trivial: `rclone copy` back down
- No extra daemon, no database, no GUI -- just a cron job
- Already installed and configured on the cluster (sync-personal-data.sh uses it)
- Duplicati/restic add dedup and compression, but the data is small enough (<10 GB for DBs) that the savings don't justify the operational complexity
- One-person-scale: "Can Shaun debug this at 2am?" rclone wins

restic would be the choice if you wanted versioned backups with dedup for the 500 GB personal data tier. But since personal data already has versions in Google Drive, and the DB snapshots are managed locally, rclone is sufficient.

---

## 7. Setup Checklist

1. [ ] Create Backblaze B2 account (or use existing)
2. [ ] Create bucket `athanor-backups` (private, no lifecycle rules)
3. [ ] Create Application Key scoped to bucket, save keyID + key
4. [ ] Install rclone on VAULT: `curl https://rclone.org/install.sh | sudo bash`
5. [ ] Configure `b2-athanor` remote with Application Key
6. [ ] Configure `b2-encrypted` crypt remote wrapping `b2-athanor:athanor-backups`
7. [ ] **Back up `rclone.conf` to password manager** (encryption keys are unrecoverable)
8. [ ] Deploy `backup-b2.sh` to `/opt/athanor/scripts/` on VAULT
9. [ ] Test: `backup-b2.sh --dry-run` then `backup-b2.sh --tier1`
10. [ ] Verify: `rclone ls b2-encrypted:databases/` shows uploaded files
11. [ ] Test restore: download a snapshot, verify it's valid
12. [ ] Add cron entries to `/boot/config/go` (Unraid persistent)
13. [ ] Add Redis BGSAVE to local backup chain (currently missing from nightly jobs)
14. [ ] Update RECOVERY.md to remove "Duplicati to Backblaze B2" blocker
15. [ ] Update ADR-015 status or create ADR-016 for offsite backup

---

## 8. Gaps Identified

- **Redis backup is not in the nightly chain.** RECOVERY.md lists Qdrant/Neo4j/Postgres/Stash but not Redis. Redis holds GWT workspace state, GPU orchestrator state, and scheduler data. Add a `BGSAVE` + copy step before the B2 upload.
- **Qdrant runs on both FOUNDRY (.244:6333) and VAULT (.203:6333).** The local backup scripts should snapshot both instances. The FOUNDRY instance has the larger collections (knowledge: 2484 vectors, personal_data: 2304 vectors).
- **rclone.conf is a critical secret.** Losing it = losing access to encrypted B2 data. Must be stored outside the cluster (password manager, printed, USB key in fireproof safe -- pick two).

---

*Last updated: 2026-03-24*
