#!/usr/bin/env bash
# Run Athanor agent evaluation suite via promptfoo.
#
# Usage: ./scripts/run-evals.sh [--output FILE]
# Requires: npx (Node.js), LiteLLM accessible at VAULT:4000

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVAL_CONFIG="$REPO_DIR/evals/promptfooconfig.yaml"
OUTPUT_DIR="$REPO_DIR/evals/results"
OUTPUT_FILE="${1:-$OUTPUT_DIR/baseline-$(date +%Y-%m-%d).json}"
LITELLM_BASE_URL="${ATHANOR_LITELLM_URL:-http://192.168.1.203:4000}"
LITELLM_API_KEY="${ATHANOR_LITELLM_API_KEY:-${OPENAI_API_KEY:-}}"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0 [--output FILE]" >&2
    echo "Run Athanor agent evaluation suite." >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --output FILE  Save results to FILE (default: evals/results/baseline-DATE.json)" >&2
    exit 0
fi

# Check LiteLLM is reachable
if [ -z "${LITELLM_API_KEY}" ]; then
    echo "ERROR: set ATHANOR_LITELLM_API_KEY or OPENAI_API_KEY before running evals" >&2
    exit 1
fi

if ! curl -sf -H "Authorization: Bearer ${LITELLM_API_KEY}" "${LITELLM_BASE_URL}/health" > /dev/null 2>&1; then
    echo "ERROR: LiteLLM not reachable at ${LITELLM_BASE_URL}" >&2
    exit 1
fi

export OPENAI_API_KEY="${LITELLM_API_KEY}"
export OPENAI_BASE_URL="${LITELLM_BASE_URL%/}/v1"

mkdir -p "$OUTPUT_DIR"

echo "Running evaluations..." >&2
echo "Config: $EVAL_CONFIG" >&2
echo "Output: $OUTPUT_FILE" >&2

npx promptfoo eval \
    -c "$EVAL_CONFIG" \
    -o "$OUTPUT_FILE" \
    --no-cache \
    2>&1

echo "" >&2
echo "Results saved to: $OUTPUT_FILE" >&2
echo "View results: npx promptfoo view" >&2
