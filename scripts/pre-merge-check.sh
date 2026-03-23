#!/bin/bash
# Pre-merge quality gate for agent-generated code
# Usage: pre-merge-check.sh [worktree_dir]
# Exit 0 = pass, Exit 1 = fail

WORKTREE="${1:-.}"
FAILURES=0
WARNINGS=0

echo "=== Pre-merge check on $WORKTREE ==="

# Check 1: Python files compile
for f in $(find "$WORKTREE" -name "*.py" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/__pycache__/*" 2>/dev/null | head -100); do
  python3 -m py_compile "$f" 2>/dev/null || { echo "FAIL: $f does not compile" >&2; FAILURES=$((FAILURES+1)); }
done

# Check 2: Python linting (ruff)
if command -v ruff &>/dev/null; then
  ruff_output=$(ruff check "$WORKTREE" --select E9,F63,F7,F82 --quiet 2>/dev/null)
  if [ -n "$ruff_output" ]; then
    echo "FAIL: ruff found critical errors" >&2
    echo "$ruff_output" >&2
    FAILURES=$((FAILURES+1))
  fi
fi

# Check 3: No secrets leaked
if command -v gitleaks &>/dev/null; then
  gitleaks detect --source "$WORKTREE" --no-git --quiet 2>/dev/null || { echo "FAIL: secrets detected by gitleaks" >&2; FAILURES=$((FAILURES+1)); }
fi

# Check 4: No giant files (>1MB)
while IFS= read -r f; do
  echo "WARN: large file $f ($(du -h "$f" | cut -f1))" >&2
  WARNINGS=$((WARNINGS+1))
done < <(find "$WORKTREE" -not -path "*/.git/*" -not -path "*/node_modules/*" -size +1M -type f 2>/dev/null)

# Check 5: Shell scripts parse
for f in $(find "$WORKTREE" -name "*.sh" -not -path "*/node_modules/*" 2>/dev/null | head -50); do
  bash -n "$f" 2>/dev/null || { echo "FAIL: $f has syntax errors" >&2; FAILURES=$((FAILURES+1)); }
done

echo "=== Result: $FAILURES failures, $WARNINGS warnings ==="
exit $((FAILURES > 0))
