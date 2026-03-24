#!/bin/bash
# PostToolUse hook: Lint/typecheck after file edits
# Catches errors immediately instead of at deploy time
# Advisory only (exit 0) — never blocks

INPUT=$(cat)

# Extract file path from hook JSON input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# === TypeScript: Dashboard ===
case "$FILE_PATH" in
  */projects/dashboard/src/*.ts|*/projects/dashboard/src/*.tsx)
    DASHBOARD_DIR="$REPO_ROOT/projects/dashboard"
    if [ -d "$DASHBOARD_DIR/node_modules" ]; then
      cd "$DASHBOARD_DIR" || exit 0
      ERRORS=$(npx tsc --noEmit --pretty false 2>&1 | grep -E "^src/" | head -10)
      if [ -n "$ERRORS" ]; then
        echo "TypeScript errors in dashboard:"
        echo "$ERRORS"
      fi
    fi
    exit 0
    ;;
esac

# === TypeScript: EoBQ ===
case "$FILE_PATH" in
  */projects/eoq/src/*.ts|*/projects/eoq/src/*.tsx)
    EOQ_DIR="$REPO_ROOT/projects/eoq"
    if [ -d "$EOQ_DIR/node_modules" ]; then
      cd "$EOQ_DIR" || exit 0
      ERRORS=$(npx tsc --noEmit --pretty false 2>&1 | grep -E "^src/" | head -10)
      if [ -n "$ERRORS" ]; then
        echo "TypeScript errors in eoq:"
        echo "$ERRORS"
      fi
    fi
    exit 0
    ;;
esac

# === Python: Syntax check ===
case "$FILE_PATH" in
  *.py)
    python3 -m py_compile "$FILE_PATH" 2>&1 | head -5
    exit 0
    ;;
esac

exit 0
