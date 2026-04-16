#!/bin/bash
# UserPromptSubmit hook: Inject contextual info into every prompt
# Adds timestamp + active work context without cluttering CLAUDE.md
# MUST stay fast — this fires on EVERY prompt

echo "Current time: $(date '+%Y-%m-%d %H:%M %Z')"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$REPO_ROOT" ]; then
  # Git state
  BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)
  DIRTY=$(git -C "$REPO_ROOT" status --short 2>/dev/null | wc -l)
  if [ "$DIRTY" -gt 0 ]; then
    echo "Git: $BRANCH ($DIRTY uncommitted files)"
  fi

  # Active plan file (newest .md in plans dir)
  PLANS_DIR="$REPO_ROOT/.claude/plans"
  if [ -d "$PLANS_DIR" ]; then
    PLAN=$(ls -t "$PLANS_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$PLAN" ]; then
      echo "Active plan: $(basename "$PLAN")"
    fi
  fi

  # Cached node health (written by session-start-health, no SSH per-prompt)
  HEALTH_CACHE="$REPO_ROOT/.claude/.health-cache"
  if [ -f "$HEALTH_CACHE" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$HEALTH_CACHE" 2>/dev/null || stat -f %m "$HEALTH_CACHE" 2>/dev/null || echo 0) ))
    if [ "$AGE" -lt 3600 ]; then
      cat "$HEALTH_CACHE"
    fi
  fi
fi
