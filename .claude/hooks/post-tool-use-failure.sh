#!/bin/bash
# PostToolUseFailure hook: Inject diagnostic context when tools fail
# Helps with faster recovery from SSH timeouts, docker errors, etc.

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
ERROR=$(echo "$INPUT" | jq -r '.error // empty' 2>/dev/null)

case "$TOOL_NAME" in
  Bash)
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    if echo "$COMMAND" | grep -q "ssh "; then
      echo "[Diagnostic] SSH command failed. Common causes:"
      echo "  - Node may be down (check with ping)"
      echo "  - SSH key not loaded (ssh-add)"
      echo "  - VAULT requires scripts/vault-ssh.py, not direct SSH"
      echo "  - Timeout: increase with 'ssh -o ConnectTimeout=10'"
    elif echo "$COMMAND" | grep -q "docker "; then
      echo "[Diagnostic] Docker command failed. Common causes:"
      echo "  - Container may not exist (docker ps -a)"
      echo "  - Docker daemon may be down on remote node"
      echo "  - Permission issue (check user in SSH config)"
    elif echo "$COMMAND" | grep -q "curl "; then
      echo "[Diagnostic] curl failed. Common causes:"
      echo "  - Service may be down (check container status)"
      echo "  - Wrong port number (verify with docker ps)"
      echo "  - DNS: use IPs (.244, .225, .203) not hostnames"
    fi
    ;;
esac

exit 0
