#!/usr/bin/env bash
set -euo pipefail

# Nightly Improvement Cycle for Athanor
# Runs the full OODA loop: export → score → identify → (optional) deploy
#
# Usage:
#   scripts/nightly-improvement.sh              # Full cycle, dry-run deploy
#   scripts/nightly-improvement.sh --apply      # Full cycle with deploy
#   scripts/nightly-improvement.sh --since 7d   # Custom time window
#
# Designed to run as cron job or Goose recipe:
#   0 3 * * * cd /home/shaun/repos/athanor && scripts/nightly-improvement.sh 2>&1 | tee /tmp/nightly-improvement.log

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="/tmp/athanor-improvement/$(date +%Y%m%d)"
SINCE="${SINCE:-24h}"
APPLY=""

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply) APPLY="--apply"; shift ;;
        --since) SINCE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--apply] [--since DURATION]" >&2
            echo "  --apply   Deploy improvements (default: dry-run)" >&2
            echo "  --since   Time window for traces (default: 24h)" >&2
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

mkdir -p "$WORK_DIR"
echo "=== Athanor Nightly Improvement ===" >&2
echo "Work dir: $WORK_DIR" >&2
echo "Since: $SINCE" >&2
echo "Apply: ${APPLY:-dry-run}" >&2
echo "" >&2

# Step 1: Export traces
echo "--- Step 1: Export LangFuse traces ---" >&2
python3 "$SCRIPT_DIR/export-langfuse-traces.py" \
    --since "$SINCE" --limit 500 \
    --output "$WORK_DIR/traces.json"

TRACE_COUNT=$(python3 -c "import json; print(len(json.load(open('$WORK_DIR/traces.json'))))")
echo "Exported $TRACE_COUNT traces" >&2

if [[ "$TRACE_COUNT" -eq 0 ]]; then
    echo "No traces to process. Exiting." >&2
    exit 0
fi

# Step 2: Score interactions
echo "" >&2
echo "--- Step 2: Score interactions ---" >&2
python3 "$SCRIPT_DIR/score-interactions.py" \
    --input "$WORK_DIR/traces.json" \
    --output "$WORK_DIR/scored.json"

# Step 3: Identify failures
echo "" >&2
echo "--- Step 3: Identify failures ---" >&2
python3 "$SCRIPT_DIR/identify-failures.py" \
    --input "$WORK_DIR/scored.json" \
    --output "$WORK_DIR/failures.json"

# Step 4: Summary
echo "" >&2
echo "--- Summary ---" >&2
python3 -c "
import json, sys
with open('$WORK_DIR/failures.json') as f:
    data = json.load(f)
clusters = data.get('failure_clusters', [])
suggestions = data.get('improvement_suggestions', [])
print(f'Failure clusters: {len(clusters)}', file=sys.stderr)
print(f'Improvement suggestions: {len(suggestions)}', file=sys.stderr)
for s in suggestions[:5]:
    print(f'  - [{s.get(\"priority\", \"?\")}] {s.get(\"description\", \"?\")[:80]}', file=sys.stderr)
"

# Step 5: Deploy (if --apply and there are proposals)
if [[ -n "$APPLY" ]]; then
    echo "" >&2
    echo "--- Step 5: Deploy improvements ---" >&2
    python3 "$SCRIPT_DIR/deploy-improvements.py" \
        --input "$WORK_DIR/failures.json" \
        $APPLY
else
    echo "" >&2
    echo "Dry-run complete. Re-run with --apply to deploy." >&2
fi

echo "" >&2
echo "=== Done. Results in $WORK_DIR ===" >&2
