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
REDIS_BACKUP_DIR="/mnt/user/data/backups/redis"
STASH_BACKUP_DIR="/mnt/user/data/backups/stash"
APPDATA_BACKUP_DIR="/mnt/appdatacache/backups/appdata"
PERSONAL_DATA_DIR="/mnt/user/data/personal"

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
    rm -r "$COMPOSE_STAGING"
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
    rclone size "${REMOTE}:" 2>/dev/null | head -5 >&2 || true
fi
