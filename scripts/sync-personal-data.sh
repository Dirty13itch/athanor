#!/usr/bin/env bash
set -euo pipefail

# Sync personal data from Google Drive to FOUNDRY for agent indexing.
#
# Flow: Google Drive (2 accounts) → rclone → DEV staging → rsync → FOUNDRY
#       Docker volume mount → agent container /data/personal/ (read-only)
#       Data Curator agent indexes content on 6-hour schedule
#
# Remotes (configured in rclone):
#   personal-drive:  — Shaun's personal Google Drive (~30 GiB)
#   uea-drive:       — Ulrich Energy Auditing business Drive (~7 GiB)
#
# Usage:
#   scripts/sync-personal-data.sh              # full sync
#   scripts/sync-personal-data.sh --dry-run    # show what would transfer
#   scripts/sync-personal-data.sh --stats      # show destination stats
#   scripts/sync-personal-data.sh --gdrive-only # sync Google Drive to DEV only
#   scripts/sync-personal-data.sh -h           # help
#
# Cron (on DEV): 0 */6 * * * /home/shaun/repos/athanor/scripts/sync-personal-data.sh >> /tmp/sync-personal-data.log 2>&1

NODE1="node1"
DEST="/opt/athanor/personal-data"
STAGING="/home/shaun/data/personal"
DRY_RUN=""
STATS_ONLY=false
GDRIVE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run|-n) DRY_RUN="--dry-run"; echo "=== DRY RUN ===" >&2 ;;
        --stats) STATS_ONLY=true ;;
        --gdrive-only) GDRIVE_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [--dry-run|-n|--stats|--gdrive-only|-h|--help]"
            echo ""
            echo "Syncs personal data from Google Drive to FOUNDRY for agent indexing."
            echo "  --dry-run      Show what would transfer without syncing"
            echo "  --stats        Show destination stats only"
            echo "  --gdrive-only  Sync Google Drive to DEV staging only (skip rsync to FOUNDRY)"
            exit 0
            ;;
    esac
done

if $STATS_ONLY; then
    echo "=== DEV staging ===" >&2
    du -sh "$STAGING"/*/ 2>/dev/null || echo "  No data staged yet" >&2
    echo "" >&2
    echo "=== FOUNDRY destination ===" >&2
    ssh "$NODE1" "du -sh $DEST/*/ 2>/dev/null" || echo "  No data on FOUNDRY yet" >&2
    exit 0
fi

echo "$(date -Iseconds) Starting personal data sync" >&2

# --- Stage 1: Google Drive → DEV staging ---

mkdir -p "$STAGING/personal-drive" "$STAGING/uea-drive"

# Common rclone options
RCLONE_BASE=(
    --transfers 4
    --checkers 8
    --stats 30s
    --stats-one-line
    --exclude '.Trash*/**'
    --exclude '.DS_Store'
    --exclude 'Thumbs.db'
    --exclude 'desktop.ini'
)

echo "" >&2
echo "--- Syncing personal-drive: → DEV staging ---" >&2
rclone sync personal-drive: "$STAGING/personal-drive/" \
    "${RCLONE_BASE[@]}" ${DRY_RUN:+"$DRY_RUN"} 2>&1 || echo "  WARN: personal-drive sync failed" >&2

echo "" >&2
echo "--- Syncing uea-drive: → DEV staging ---" >&2
rclone sync uea-drive: "$STAGING/uea-drive/" \
    "${RCLONE_BASE[@]}" ${DRY_RUN:+"$DRY_RUN"} 2>&1 || echo "  WARN: uea-drive sync failed" >&2

echo "" >&2
echo "--- DEV staging sizes ---" >&2
du -sh "$STAGING"/*/ 2>/dev/null >&2 || true

if $GDRIVE_ONLY; then
    echo "$(date -Iseconds) Google Drive sync complete (--gdrive-only, skipping rsync)" >&2
    exit 0
fi

# --- Stage 2: DEV staging → FOUNDRY ---

ssh "$NODE1" "sudo mkdir -p $DEST && sudo chown -R \$(whoami): $DEST" 2>&1 || {
    echo "ERROR: Cannot reach FOUNDRY" >&2
    exit 1
}

RSYNC_BASE=(
    -avz
    --progress
    --delete
    --exclude='node_modules/'
    --exclude='.git/'
    --exclude='__pycache__/'
    --exclude='*.tmp'
    --exclude='*.log'
    --exclude='Thumbs.db'
    --exclude='desktop.ini'
)

echo "" >&2
echo "--- Syncing DEV staging → FOUNDRY ---" >&2
rsync "${RSYNC_BASE[@]}" ${DRY_RUN:+"$DRY_RUN"} \
    "$STAGING/" "$NODE1:$DEST/" 2>&1 || echo "  WARN: rsync to FOUNDRY failed" >&2

# --- Summary ---
echo "" >&2
echo "$(date -Iseconds) Sync complete" >&2
if [[ -z "$DRY_RUN" ]]; then
    echo "" >&2
    echo "FOUNDRY destination sizes:" >&2
    ssh "$NODE1" "du -sh $DEST/*/ 2>/dev/null" >&2 || true
fi
