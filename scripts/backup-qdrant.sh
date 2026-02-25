#!/usr/bin/env bash
# Backup Qdrant collections via snapshot API.
# Runs on Node 1 (where Qdrant is deployed).
# Stores snapshots to VAULT HDD array via NFS.
#
# Usage: ./backup-qdrant.sh
# Cron:  0 3 * * * /opt/athanor/scripts/backup-qdrant.sh >> /var/log/athanor-backup.log 2>&1

set -euo pipefail

QDRANT_URL="http://localhost:6333"
BACKUP_DIR="${BACKUP_DIR:-/mnt/vault/data/backups/athanor/qdrant}"
RETENTION_DAYS=7
DATE=$(date +%Y-%m-%d)

echo "[$(date -Iseconds)] Starting Qdrant backup"

# Ensure backup directory exists (uses NFS data mount: /mnt/vault/data/ on Node 1)
mkdir -p "$BACKUP_DIR"

# Get list of collections
COLLECTIONS=$(curl -sf "$QDRANT_URL/collections" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('result', {}).get('collections', []):
    print(c['name'])
")

if [ -z "$COLLECTIONS" ]; then
    echo "[$(date -Iseconds)] ERROR: No collections found or Qdrant unreachable"
    exit 1
fi

# Create snapshot for each collection
for COLL in $COLLECTIONS; do
    echo "[$(date -Iseconds)] Snapshotting collection: $COLL"

    # Create snapshot via API
    SNAP_RESP=$(curl -sf -X POST "$QDRANT_URL/collections/$COLL/snapshots")
    SNAP_NAME=$(echo "$SNAP_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('result', {}).get('name', ''))
")

    if [ -z "$SNAP_NAME" ]; then
        echo "[$(date -Iseconds)] ERROR: Failed to create snapshot for $COLL"
        continue
    fi

    # Download snapshot to backup dir
    DEST="$BACKUP_DIR/${COLL}_${DATE}.snapshot"
    curl -sf "$QDRANT_URL/collections/$COLL/snapshots/$SNAP_NAME" -o "$DEST"

    if [ -f "$DEST" ]; then
        SIZE=$(du -h "$DEST" | cut -f1)
        echo "[$(date -Iseconds)] Saved $COLL snapshot: $DEST ($SIZE)"
    else
        echo "[$(date -Iseconds)] ERROR: Download failed for $COLL"
    fi

    # Clean up snapshot from Qdrant storage
    curl -sf -X DELETE "$QDRANT_URL/collections/$COLL/snapshots/$SNAP_NAME" > /dev/null || true
done

# Prune old backups
echo "[$(date -Iseconds)] Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "*.snapshot" -mtime +$RETENTION_DAYS -delete -print

echo "[$(date -Iseconds)] Qdrant backup complete"
