#!/bin/bash
# PostCompact hook: re-orient from live truth after compaction.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STATE_FILE="$REPO_ROOT/.claude/.session-state.md"

echo "=== POST-COMPACTION RECOVERY ==="

if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
  echo ""
fi

echo "## Immediate Actions"
echo "1. Refresh live truth first: STATUS.md, docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md, reports/ralph-loop/latest.json, reports/truth-inventory/ralph-continuity-state.json, reports/truth-inventory/governed-dispatch-state.json, reports/truth-inventory/finish-scoreboard.json, and reports/truth-inventory/runtime-packet-inbox.json"
echo "2. Re-run 'git log --oneline -5' and 'git diff --stat' for the current repo state"
echo "3. Treat .claude/.session-state.md as a hint only, not authority"
echo "4. Continue only after the live surfaces still match the handoff and the finish/runtime packet surfaces agree with the restart brief"
echo "==="
