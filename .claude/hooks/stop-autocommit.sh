#!/bin/bash
# Stop hook: opt-in continuity commit helper.
# Disabled by default so helper churn does not silently become source truth.
# Generated reports and restart surfaces remain the current authority; this hook only captures helper continuity when explicitly enabled.

INPUT=$(cat 2>/dev/null || true)
if echo "$INPUT" | grep -qi '"stop_hook_active"[[:space:]]*:[[:space:]]*true' 2>/dev/null; then
  exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

if [ "${ATHANOR_ENABLE_STOP_AUTOCOMMIT:-0}" != "1" ]; then
  echo "stop-autocommit disabled by default; set ATHANOR_ENABLE_STOP_AUTOCOMMIT=1 to opt in"
  exit 0
fi

STATE_PATHS=(
  "STATUS.md"
  "CLAUDE.md"
  "SESSION-LOG.md"
  "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md"
  ".claude/skills/"
  ".claude/commands/"
  ".claude/hooks/"
  ".claude/rules/"
)

CHANGED_FILES=""
for path in "${STATE_PATHS[@]}"; do
  changes=$(git diff --name-only -- "$path" 2>/dev/null)
  if [ -n "$changes" ]; then
    CHANGED_FILES="$CHANGED_FILES $changes"
  fi
done

if [ -z "$CHANGED_FILES" ]; then
  exit 0
fi

echo "Opt-in auto-committing helper/state files:$CHANGED_FILES"
echo "Refresh the restart brief and generated truth surfaces after any such helper commit before treating it as current state."
for path in "${STATE_PATHS[@]}"; do
  git add -- "$path" 2>/dev/null
done

git commit -m "state: opt-in helper continuity commit

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" 2>/dev/null
