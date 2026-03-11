#!/usr/bin/env bash
# Backup critical VAULT container appdata.
# Runs on VAULT. Creates compressed tarballs of service configs.
#
# Usage: ./backup-appdata.sh
# Cron: configured by VAULT deployment; backup path can be overridden with BACKUP_DIR

set -euo pipefail

APPDATA_DIR="/mnt/user/appdata"
BACKUP_DIR="${BACKUP_DIR:-/mnt/appdatacache/backups}"
RETENTION_COUNT=3
DATE=$(date +%Y-%m-%d)

echo "[$(date -Iseconds)] Starting appdata backup"

mkdir -p "$BACKUP_DIR"

# Services to back up (configs that are hard to recreate)
# Excludes large/ephemeral dirs like Plex transcodes
SERVICES=(
    "plex"
    "sonarr"
    "radarr"
    "prowlarr"
    "sabnzbd"
    "tautulli"
    "homeassistant"
    "stash"
    "neo4j"
    "grafana"
    "prometheus"
    "redis"
    "wyoming-piper"
    "wyoming-openwakeword"
)

for SVC in "${SERVICES[@]}"; do
    SRC="$APPDATA_DIR/$SVC"
    if [ ! -d "$SRC" ]; then
        echo "[$(date -Iseconds)] SKIP: $SVC (directory not found)"
        continue
    fi

    DEST="$BACKUP_DIR/${SVC}_${DATE}.tar.gz"

    # Exclude cache/temp directories to keep backups small
    tar czf "$DEST" \
        --exclude='*/Cache/*' \
        --exclude='*/cache/*' \
        --exclude='*/Crash Reports/*' \
        --exclude='*/transcodes/*' \
        --exclude='*/Logs/*' \
        --exclude='*/logs/*' \
        -C "$APPDATA_DIR" "$SVC" 2>/dev/null || {
            echo "[$(date -Iseconds)] WARN: tar had warnings for $SVC (likely changed files)"
        }

    if [ -f "$DEST" ]; then
        SIZE=$(du -h "$DEST" | cut -f1)
        echo "[$(date -Iseconds)] Backed up $SVC: $DEST ($SIZE)"
    else
        echo "[$(date -Iseconds)] ERROR: Failed to backup $SVC"
    fi
done

# Prune old backups — keep only N most recent per service
echo "[$(date -Iseconds)] Pruning old backups (keeping $RETENTION_COUNT per service)"
for SVC in "${SERVICES[@]}"; do
    # List backups for this service, sorted newest first, delete all beyond retention count
    ls -t "$BACKUP_DIR/${SVC}_"*.tar.gz 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | while read -r OLD; do
        echo "[$(date -Iseconds)] Removing old backup: $OLD"
        rm -f "$OLD"
    done
done

echo "[$(date -Iseconds)] Appdata backup complete"
