#!/usr/bin/env bash
# Backup Postgres via pg_dumpall from the container.
# Runs on VAULT where the postgres container is deployed.
#
# Usage: ./backup-postgres.sh
# Cron:  30 1 * * * /opt/athanor/scripts/backup-postgres.sh >> /var/log/athanor-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/mnt/user/data/backups/postgres"
RETENTION_DAYS=14
DATE=$(date +%Y%m%d-%H%M%S)
DEST="$BACKUP_DIR/pg-backup-${DATE}.sql.gz"

echo "[$(date -Iseconds)] Starting Postgres backup"

mkdir -p "$BACKUP_DIR"

PG_USER="${POSTGRES_USER:-local_system}"
docker exec postgres pg_dumpall -U "$PG_USER" | gzip > "$DEST"

if [ -f "$DEST" ] && [ -s "$DEST" ]; then
    SIZE=$(du -h "$DEST" | cut -f1)
    echo "[$(date -Iseconds)] Saved Postgres backup: $DEST ($SIZE)"
else
    echo "[$(date -Iseconds)] ERROR: Postgres backup failed or empty" >&2
    exit 1
fi

echo "[$(date -Iseconds)] Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "pg-backup-*.sql.gz" -mtime +$RETENTION_DAYS -delete -print

echo "[$(date -Iseconds)] Postgres backup complete"
