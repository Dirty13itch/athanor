#!/bin/bash
# UserPromptSubmit hook: Inject contextual info into every prompt
# Adds timestamp + active work context without cluttering CLAUDE.md

echo "Current time: $(date '+%Y-%m-%d %H:%M %Z')"

# Show active git branch and uncommitted file count
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -n "$REPO_ROOT" ]; then
  BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)
  DIRTY=$(git -C "$REPO_ROOT" status --short 2>/dev/null | wc -l)
  if [ "$DIRTY" -gt 0 ]; then
    echo "Git: $BRANCH ($DIRTY uncommitted files)"
  fi
fi
