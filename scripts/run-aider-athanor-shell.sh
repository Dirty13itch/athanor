#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.local/npm-global/bin:$PATH"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_ENV_SCRIPT="$SCRIPT_DIR/runtime_env.py"

if [[ $# -gt 0 ]]; then
  case "$1" in
    --version|-v|version|--help|-h|help)
      if command -v aider >/dev/null 2>&1; then
        exec aider "$@"
      fi
      if ! command -v uv >/dev/null 2>&1; then
        echo "aider is not healthy on PATH and uv is unavailable for fallback." >&2
        exit 1
      fi
      exec uv tool run --from aider-chat==0.86.2 aider "$@"
      ;;
  esac
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 command not found on PATH." >&2
  exit 1
fi

resolved="$(python3 "$RUNTIME_ENV_SCRIPT" --resolve ATHANOR_LITELLM_API_KEY ATHANOR_LITELLM_URL OPENAI_API_KEY OPENAI_API_BASE --format dotenv)"
while IFS='=' read -r key value; do
  [[ -n "${key:-}" ]] || continue
  if [[ -z "${!key:-}" ]]; then
    export "$key=$value"
  fi
done <<< "$resolved"

if [[ -z "${ATHANOR_LITELLM_API_KEY:-}" ]]; then
  echo "ATHANOR_LITELLM_API_KEY could not be resolved from the managed runtime env surface." >&2
  exit 1
fi

export AIDER_OPENAI_API_KEY="${AIDER_OPENAI_API_KEY:-${OPENAI_API_KEY:-}}"
export AIDER_OPENAI_API_BASE="${AIDER_OPENAI_API_BASE:-${OPENAI_API_BASE:-}}"
export AIDER_MODEL="${AIDER_MODEL:-openai/gpt-codex-sub}"

if command -v aider >/dev/null 2>&1; then
  exec aider "$@"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "aider is not healthy on PATH and uv is unavailable for fallback." >&2
  exit 1
fi

exec uv tool run --from aider-chat==0.86.2 aider "$@"
