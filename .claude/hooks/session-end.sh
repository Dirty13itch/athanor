#!/bin/bash
# SessionEnd hook: Update STATUS.md timestamp on session exit

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
  exit 0
fi

STATUS_FILE="$REPO_ROOT/STATUS.md"
if [ -f "$STATUS_FILE" ]; then
  # Update the "Last updated" line if it exists
  DATE=$(date '+%Y-%m-%d %H:%M %Z')
  if grep -q "Last updated:" "$STATUS_FILE" 2>/dev/null; then
    sed -i "s/Last updated:.*/Last updated: $DATE/" "$STATUS_FILE"
  fi
fi

# Desktop notification
notify-send -t 3000 'Claude Code' 'Session ended' 2>/dev/null || true

exit 0
