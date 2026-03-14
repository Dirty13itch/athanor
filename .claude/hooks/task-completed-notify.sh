#!/bin/bash
# TaskCompleted hook: Desktop notification when background tasks complete

INPUT=$(cat)
TASK_DESC=$(echo "$INPUT" | jq -r '.task_description // "Background task"' 2>/dev/null)

notify-send -t 5000 'Claude Code' "Task completed: $TASK_DESC" 2>/dev/null || true

exit 0
