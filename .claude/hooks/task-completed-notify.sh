#!/bin/bash
# TaskCompleted hook: Desktop notification when background tasks complete

INPUT=$(cat)
TASK_DESC=$(echo "$INPUT" | jq -r '.task_description // "Background task"' 2>/dev/null)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$SCRIPT_DIR/notify.sh" "Claude Code" "Task completed: $TASK_DESC" 5000

exit 0
