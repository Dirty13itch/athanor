#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.local/npm-global/bin:$PATH"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_ENV_SCRIPT="$SCRIPT_DIR/runtime_env.py"

if [[ $# -gt 0 ]]; then
  case "$1" in
    --version|-v|version|--help|-h|help)
      exec goose "$@"
      ;;
  esac
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 command not found on PATH." >&2
  exit 1
fi

if ! command -v goose >/dev/null 2>&1; then
  echo "goose command not found on PATH." >&2
  exit 1
fi

resolved="$(python3 "$RUNTIME_ENV_SCRIPT" --resolve ATHANOR_LITELLM_API_KEY ATHANOR_LITELLM_URL OPENAI_API_KEY OPENAI_API_BASE OPENAI_HOST OPENAI_BASE_PATH --format dotenv)"
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

final_args=("$@")
if [[ ${#final_args[@]} -eq 0 ]]; then
  final_args=(session)
fi

subcommand=""
if [[ ${#final_args[@]} -gt 0 && "${final_args[0]}" != -* ]]; then
  subcommand="${final_args[0]}"
fi

if [[ "$subcommand" =~ ^(run|session|s|term)$ ]]; then
  has_provider=false
  has_model=false
  for arg in "${final_args[@]}"; do
    [[ "$arg" == "--provider" ]] && has_provider=true
    [[ "$arg" == "--model" ]] && has_model=true
  done
  prefix=("${final_args[0]}")
  suffix=()
  if [[ ${#final_args[@]} -gt 1 ]]; then
    suffix=("${final_args[@]:1}")
  fi
  if [[ "$has_provider" == false ]]; then
    suffix=(--provider openai "${suffix[@]}")
  fi
  if [[ "$has_model" == false ]]; then
    suffix=(--model deepseek "${suffix[@]}")
  fi
  final_args=("${prefix[@]}" "${suffix[@]}")
fi

exec goose "${final_args[@]}"
