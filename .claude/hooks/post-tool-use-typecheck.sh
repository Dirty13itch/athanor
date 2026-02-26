#!/bin/bash
# PostToolUse hook: Type-check dashboard files after Write/Edit
# Catches TypeScript errors immediately instead of at deploy time

# Only run for dashboard file modifications
FILE_PATH="${CLAUDE_TOOL_INPUT_FILE_PATH:-${CLAUDE_TOOL_INPUT_file_path:-}}"
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only check .ts/.tsx files in the dashboard project
case "$FILE_PATH" in
  */projects/dashboard/src/*.ts|*/projects/dashboard/src/*.tsx)
    ;;
  *)
    exit 0
    ;;
esac

DASHBOARD_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/projects/dashboard"

# Quick check — only if npx/tsc is available and node_modules exists
if [ ! -d "$DASHBOARD_DIR/node_modules" ]; then
  exit 0
fi

# Run tsc --noEmit on just the changed file (fast, ~2-5s)
cd "$DASHBOARD_DIR" || exit 0
ERRORS=$(npx tsc --noEmit --pretty false 2>&1 | grep -E "^src/" | head -10)

if [ -n "$ERRORS" ]; then
  echo "TypeScript errors detected after editing $FILE_PATH:"
  echo "$ERRORS"
  echo ""
  echo "Fix these before deploying."
fi

# Always exit 0 — this is advisory, not blocking
exit 0
