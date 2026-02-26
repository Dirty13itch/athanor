#!/usr/bin/env bash
set -euo pipefail

# Sync personal data from DEV (WSL2) to Node 1 for agent indexing.
#
# Flow: DEV local drives → rsync over SSH → Node 1 /opt/athanor/personal-data/
#       Docker volume mount → agent container /data/personal/ (read-only)
#       Data Curator agent indexes content on 6-hour schedule
#
# Why Node 1 (not VAULT): VAULT SSH doesn't support direct rsync.
# Node 1 has passwordless SSH from DEV and runs the agents.
#
# Usage:
#   scripts/sync-personal-data.sh          # full sync
#   scripts/sync-personal-data.sh --dry-run # show what would transfer
#   scripts/sync-personal-data.sh -h       # help
#
# Cron (on DEV): 0 */6 * * * /home/shaun/repos/Athanor/scripts/sync-personal-data.sh >> /tmp/sync-personal-data.log 2>&1

NODE1="node1"
DEST="/opt/athanor/personal-data"
DRY_RUN=""
STATS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run|-n) DRY_RUN="--dry-run"; echo "=== DRY RUN ===" >&2 ;;
        --stats) STATS_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [--dry-run|-n|--stats|-h|--help]"
            echo ""
            echo "Syncs personal data from DEV local drives to Node 1 for agent indexing."
            echo "  --dry-run  Show what would transfer without syncing"
            echo "  --stats    Show destination stats only"
            exit 0
            ;;
    esac
done

if $STATS_ONLY; then
    ssh "$NODE1" "du -sh $DEST/*/ 2>/dev/null || echo 'No data synced yet'"
    exit 0
fi

echo "$(date -Iseconds) Starting personal data sync to $NODE1:$DEST" >&2

# Ensure destination exists on Node 1
ssh "$NODE1" "sudo mkdir -p $DEST/{work,finance,documents,downloads,photos,configs} && sudo chown -R \$(whoami): $DEST" 2>&1 || {
    echo "ERROR: Cannot reach Node 1" >&2
    exit 1
}

# Common rsync options
RSYNC_BASE=(
    -avz
    --progress
    --exclude='node_modules/'
    --exclude='.git/'
    --exclude='__pycache__/'
    --exclude='*.tmp'
    --exclude='*.log'
    --exclude='Thumbs.db'
    --exclude='desktop.ini'
)

sync_dir() {
    local label="$1"
    local src="$2"
    local dst="$3"
    shift 3
    local extra_opts=("$@")

    echo "" >&2
    echo "--- $label ---" >&2

    if [[ ! -d "$src" ]]; then
        echo "  SKIP: $src does not exist" >&2
        return 0
    fi

    rsync "${RSYNC_BASE[@]}" ${DRY_RUN:+"$DRY_RUN"} "${extra_opts[@]}" \
        "$src" "$NODE1:$dst" 2>&1 || echo "  WARN: $label sync failed" >&2
}

# --- Work documents (spreadsheets, PDFs, plans, photos) ---
sync_dir "Work documents" \
    "/mnt/c/Users/Shaun/Desktop/Work/" \
    "$DEST/work/" \
    --include='*.xlsx' --include='*.xls' \
    --include='*.pdf' --include='*.docx' --include='*.doc' \
    --include='*.csv' --include='*.txt' --include='*.md' \
    --include='*.png' --include='*.jpg' --include='*.jpeg' \
    --include='*/' --exclude='*' \
    --max-size=100M

# --- Finance documents ---
sync_dir "Finance documents" \
    "/mnt/c/Users/Shaun/Desktop/Finance/" \
    "$DEST/finance/" \
    --max-size=50M

# --- Athanor reference documents ---
sync_dir "Athanor reference" \
    "/mnt/c/Users/Shaun/Documents/Athanor-Reference/" \
    "$DEST/documents/athanor-reference/"

# --- Bookmarks ---
sync_dir "Bookmarks" \
    "/mnt/c/Users/Shaun/Documents/" \
    "$DEST/documents/" \
    --include='bookmarks*' --include='Bookmarks' \
    --include='ChromeBackup/' --include='ChromeBackup/**' \
    --exclude='*'

# --- C: Downloads (docs only, skip installers) ---
sync_dir "C: Downloads (docs)" \
    "/mnt/c/Users/Shaun/Downloads/" \
    "$DEST/downloads/c-downloads/" \
    --include='*.xlsx' --include='*.xls' \
    --include='*.pdf' --include='*.docx' --include='*.doc' \
    --include='*.csv' --include='*.md' --include='*.json' \
    --include='*/' --exclude='*' \
    --max-size=50M

# --- D: Downloads (docs only, skip ISOs/empty dirs) ---
sync_dir "D: Downloads (docs)" \
    "/mnt/d/Users/Shaun/Downloads/" \
    "$DEST/downloads/d-downloads/" \
    --include='*.xlsx' --include='*.xls' \
    --include='*.pdf' --include='*.docx' --include='*.doc' \
    --include='*.csv' --include='*.md' --include='*.json' \
    --include='*.txt' \
    --include='*/' --exclude='*' \
    --max-size=50M \
    --prune-empty-dirs

# --- Property inspection photos ---
echo "" >&2
echo "--- Property inspection photos ---" >&2
for dir in /mnt/c/Users/Shaun/Desktop/*/; do
    [[ -d "$dir" ]] || continue
    dirname="$(basename "$dir")"
    # Skip known non-property directories
    case "$dirname" in
        Work|Finance|Shortcuts*) continue ;;
    esac
    # Only sync directories containing photos
    if compgen -G "$dir*.jpg" >/dev/null 2>&1 || \
       compgen -G "$dir*.jpeg" >/dev/null 2>&1 || \
       compgen -G "$dir*.png" >/dev/null 2>&1; then
        sync_dir "  Photos: $dirname" \
            "$dir" \
            "$DEST/photos/$dirname/" \
            --include='*.jpg' --include='*.jpeg' --include='*.png' \
            --include='*/' --exclude='*'
    fi
done

# --- ShareX configs ---
sync_dir "ShareX configs" \
    "/mnt/c/Users/Shaun/Documents/ShareX/" \
    "$DEST/configs/sharex/"

# --- Summary ---
echo "" >&2
echo "$(date -Iseconds) Sync complete" >&2
if [[ -z "$DRY_RUN" ]]; then
    echo "" >&2
    echo "Destination sizes:" >&2
    ssh "$NODE1" "du -sh $DEST/*/ 2>/dev/null" >&2 || true
fi
