#!/bin/bash
# Stop hook: Auto-commit state files if they were modified during session
# Covers all tracking/state files, not just a few

# Guard against infinite loop: if this stop hook triggers another stop, bail
INPUT=$(cat)
IS_STOP_HOOK=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stop_hook_active','false'))" 2>/dev/null)
if [ "$IS_STOP_HOOK" = "true" ] || [ "$IS_STOP_HOOK" = "True" ]; then
  exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

# All files that track system state
STATE_PATHS=(
  "STATUS.md"
  "CLAUDE.md"
  "docs/BUILD-MANIFEST.md"
  "docs/VISION.md"
  "docs/SYSTEM-SPEC.md"
  "docs/SERVICES.md"
  "docs/hardware/"
  "docs/design/"
  "docs/decisions/"
  ".claude/skills/"
  ".claude/commands/"
  ".claude/hooks/"
)

CHANGED_FILES=""
for path in "${STATE_PATHS[@]}"; do
  changes=$(git diff --name-only -- "$path" 2>/dev/null)
  if [ -n "$changes" ]; then
    CHANGED_FILES="$CHANGED_FILES $changes"
  fi
done

if [ -n "$CHANGED_FILES" ]; then
  echo "Auto-committing state files:$CHANGED_FILES"
  for path in "${STATE_PATHS[@]}"; do
    git add -- "$path" 2>/dev/null
  done
  git commit -m "state: auto-commit session changes

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" 2>/dev/null
fi
