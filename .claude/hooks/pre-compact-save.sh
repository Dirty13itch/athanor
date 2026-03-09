#!/bin/bash
# PreCompact hook: Save dynamic session state before context compaction
# Captures real-time info that helps Claude recover context after compaction

STATE_FILE="$HOME/.claude/projects/-home-shaun-repos-athanor/session-state.md"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

{
  echo "# Athanor Session State (Pre-Compaction Snapshot)"
  echo "Captured: $(date -Iseconds)"
  echo ""

  # Git state
  echo "## Git State"
  echo '```'
  echo "Branch: $(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
  echo "Last 5 commits:"
  git -C "$REPO_ROOT" log --oneline -5 2>/dev/null
  echo ""
  echo "Uncommitted changes:"
  git -C "$REPO_ROOT" status --short 2>/dev/null || echo "  (none)"
  echo '```'
  echo ""

  # Modified files diff summary
  CHANGED=$(git -C "$REPO_ROOT" diff --stat 2>/dev/null)
  if [ -n "$CHANGED" ]; then
    echo "## Changed Files (unstaged)"
    echo '```'
    echo "$CHANGED"
    echo '```'
    echo ""
  fi

  # Staged files
  STAGED=$(git -C "$REPO_ROOT" diff --cached --stat 2>/dev/null)
  if [ -n "$STAGED" ]; then
    echo "## Staged Files"
    echo '```'
    echo "$STAGED"
    echo '```'
    echo ""
  fi

  # Quick infrastructure status (non-blocking, 2s timeout)
  echo "## Infrastructure (quick check)"
  N1=$(ssh -o ConnectTimeout=2 -o BatchMode=yes node1 'echo UP' 2>/dev/null && echo "UP" || echo "DOWN")
  N2=$(ssh -o ConnectTimeout=2 -o BatchMode=yes node2 'echo UP' 2>/dev/null && echo "UP" || echo "DOWN")
  echo "- Foundry (Node 1): $N1"
  echo "- Workshop (Node 2): $N2"
  echo ""

  # Remind what files to re-read
  echo "## Re-read After Compaction"
  echo "- CLAUDE.md (role, state, gotchas)"
  echo "- MEMORY.md (session continuity)"
  echo "- docs/BUILD-MANIFEST.md (work queue)"
  echo "- The plan file if one exists"
} > "$STATE_FILE" 2>/dev/null

echo "Session state saved to $STATE_FILE (persistent)"
