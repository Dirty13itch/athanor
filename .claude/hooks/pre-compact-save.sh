#!/bin/bash
# PreCompact hook: save a reference-only handoff before compaction.
# This snapshot is a hint, not authority. Live truth must be refreshed after compaction.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STATE_FILE="$REPO_ROOT/.claude/.session-state.md"
CAPTURED_AT="$(date -Iseconds)"
BRANCH="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
DIRTY_COUNT="$(git -C "$REPO_ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')"
LAST_COMMITS="$(git -C "$REPO_ROOT" log --oneline -5 2>/dev/null || true)"

{
  echo "# Athanor Session State (Reference-Only Compaction Handoff)"
  echo ""
  echo "> **Status:** Reference-only hint."
  echo "> **Captured:** $CAPTURED_AT"
  echo "> **Refresh live truth before relying on anything here.**"
  echo "> **Current truth lives here:** `STATUS.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`, `reports/ralph-loop/latest.json`, `reports/truth-inventory/ralph-continuity-state.json`, `reports/truth-inventory/governed-dispatch-state.json`, `reports/truth-inventory/finish-scoreboard.json`, and `reports/truth-inventory/runtime-packet-inbox.json`."
  echo ""
  echo "## Minimal Git Context"
  echo "- Branch: ${BRANCH:-unknown}"
  echo "- Dirty file count: ${DIRTY_COUNT:-0}"
  echo ""
  echo "## Last 5 Commits"
  echo '```'
  echo "$LAST_COMMITS"
  echo '```'
  echo ""
  echo "## Required Live Refresh After Compaction"
  echo "- STATUS.md"
  echo "- docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md"
  echo "- reports/ralph-loop/latest.json"
  echo "- reports/truth-inventory/ralph-continuity-state.json"
  echo "- reports/truth-inventory/governed-dispatch-state.json"
  echo "- reports/truth-inventory/finish-scoreboard.json"
  echo "- reports/truth-inventory/runtime-packet-inbox.json"
  echo ""
  echo "Do not treat this handoff as runtime, queue, provider, or deployment authority."
} > "$STATE_FILE" 2>/dev/null

echo "Reference-only session handoff saved to $STATE_FILE"
