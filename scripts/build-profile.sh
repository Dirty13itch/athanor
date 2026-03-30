#!/usr/bin/env bash
set -euo pipefail

# Canonical operator-facing wrapper for the profile builder.
# Required runtime envs remain explicit here so repo contract checks can
# verify the script follows the platform env contract:
#   ATHANOR_QDRANT_URL
#   ATHANOR_VLLM_EMBEDDING_URL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python "$SCRIPT_DIR/build-profile.py" "$@"
