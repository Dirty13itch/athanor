#!/usr/bin/env bash
# Backup Stash SQLite database.
# Runs on VAULT where Stash is deployed.
#
# Usage: ./backup-stash.sh
# Cron:  0 2 * * * /opt/athanor/scripts/backup-stash.sh >> /var/log/athanor-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/mnt/user/data/backups/stash"
DB_PATH="/mnt/user/appdata/stash/config/stash-go.sqlite"
RETENTION_DAYS=14
DATE=$(date +%Y%m%d_%H%M%S)
DEST="$BACKUP_DIR/stash-go_${DATE}.sqlite"

echo "[$(date -Iseconds)] Starting Stash backup"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "[$(date -Iseconds)] ERROR: Stash DB not found at $DB_PATH" >&2
    exit 1
fi

cp "$DB_PATH" "$DEST"

if [ -f "$DEST" ] && [ -s "$DEST" ]; then
    SIZE=$(du -h "$DEST" | cut -f1)
    echo "[$(date -Iseconds)] Saved Stash backup: $DEST ($SIZE)"
else
    echo "[$(date -Iseconds)] ERROR: Stash backup failed or empty" >&2
    exit 1
fi

echo "[$(date -Iseconds)] Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "stash-go_*.sqlite" -mtime +$RETENTION_DAYS -delete -print

echo "[$(date -Iseconds)] Stash backup complete"
