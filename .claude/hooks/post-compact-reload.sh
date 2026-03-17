#!/bin/bash
# PostCompact hook: Inject re-orientation context after compaction
# Fires immediately after context compaction completes

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STATE_FILE="$REPO_ROOT/.claude/.session-state.md"

echo "=== POST-COMPACTION RECOVERY ==="

# Inject saved session state if available
if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
  echo ""
fi

# Always remind what to re-read
echo "## Immediate Actions"
echo "1. Re-read CLAUDE.md (role, principles, gotchas)"
echo "2. Check MEMORY.md (session continuity, cluster state)"
echo "3. Check for active plan file (look for 'plan mode' in context)"
echo "4. Run 'git log --oneline -5 && git diff --stat' to see recent work"
echo "5. Continue where you left off — don't restart or re-orient"
echo "==="
