#!/bin/bash
# Stop hook: Auto-commit state files if infrastructure was modified
# Checks for changes to docs/ state files and commits them

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

# Check if any state files were modified
STATE_FILES=$(git diff --name-only docs/BUILD-ROADMAP.md docs/VISION.md docs/hardware/ 2>/dev/null)

if [ -n "$STATE_FILES" ]; then
  echo "Auto-committing modified state files: $STATE_FILES"
  git add docs/BUILD-ROADMAP.md docs/VISION.md docs/hardware/ 2>/dev/null
  git commit -m "State: auto-commit infrastructure changes" 2>/dev/null
fi
