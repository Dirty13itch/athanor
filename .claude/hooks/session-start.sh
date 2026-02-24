#!/usr/bin/env bash
# Session start hook — loads critical context automatically
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "=== ATHANOR SESSION ==="
echo "Node: $(hostname)"
echo "Repo: ${REPO_ROOT}"
echo "Branch: $(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo 'detached')"
echo "Last commit: $(git -C "$REPO_ROOT" log -1 --oneline 2>/dev/null || echo 'none')"
echo ""

# Surface any uncommitted changes
CHANGES=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | wc -l)
if [ "$CHANGES" -gt 0 ]; then
  echo "⚠ ${CHANGES} uncommitted changes"
  git -C "$REPO_ROOT" status --short
  echo ""
fi

# Remind of build principle
echo "BUILD PRINCIPLE: Right over fast. Research → Document → Decide."
echo "==="
