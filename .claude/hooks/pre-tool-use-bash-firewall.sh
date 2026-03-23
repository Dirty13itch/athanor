#!/bin/bash
# PreToolUse hook: Block dangerous Bash commands
# Matcher: Bash
# Blocks: destructive operations, evasion patterns, secret access

INPUT=$(cat)

# Extract the command from tool input using jq
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Fallback to grep if jq fails
if [ -z "$COMMAND" ]; then
  COMMAND=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"command"\s*:\s*"//;s/"$//')
fi

# Normalize: lowercase for case-insensitive matching
CMD_LOWER=$(echo "$COMMAND" | tr '[:upper:]' '[:lower:]')

# === EVASION DETECTION ===
# Block eval/exec wrapping
if echo "$CMD_LOWER" | grep -qE '(^|\s|;|&&|\|\|)eval\s'; then
  echo "BLOCKED: eval wrapping detected: $COMMAND"
  echo "Direct commands only — no eval wrappers."
  exit 2
fi

# Block piped execution (echo ... | bash/sh)
if echo "$CMD_LOWER" | grep -qE '\|\s*(ba)?sh(\s|$)'; then
  echo "BLOCKED: Piped shell execution detected: $COMMAND"
  exit 2
fi

# Block base64 decode to shell
if echo "$CMD_LOWER" | grep -qE 'base64.*\|\s*(ba)?sh'; then
  echo "BLOCKED: Encoded command execution detected: $COMMAND"
  exit 2
fi

# Block explicit subshell for dangerous ops
if echo "$CMD_LOWER" | grep -qE '(ba)?sh\s+-c\s+.*rm\s'; then
  echo "BLOCKED: Subshell rm detected: $COMMAND"
  exit 2
fi

# === DESTRUCTIVE FILESYSTEM ===
BLOCKED_FS=(
  "rm -rf /"
  "rm -rf /*"
  "rm -rf ~"
  "rm -rf \$HOME"
)

for PATTERN in "${BLOCKED_FS[@]}"; do
  if echo "$COMMAND" | grep -qi "$PATTERN"; then
    echo "BLOCKED: Dangerous filesystem operation '$PATTERN': $COMMAND"
    exit 2
  fi
done

# === DESTRUCTIVE GIT ===
BLOCKED_GIT=(
  "git reset --hard"
  "git push --force"
  "git push -f "
  "git push.*--force"
  "git clean -fd"
  "git clean -f "
  "git checkout -- \."
  "git branch -D "
  "git stash drop"
  "git stash clear"
)

for PATTERN in "${BLOCKED_GIT[@]}"; do
  if echo "$COMMAND" | grep -qi "$PATTERN"; then
    echo "BLOCKED: Dangerous git operation '$PATTERN': $COMMAND"
    echo "This could cause irreversible data loss. Ask the user before proceeding."
    exit 2
  fi
done

# === DATABASE ===
if echo "$CMD_LOWER" | grep -qE '(drop|truncate)\s+(table|database|schema|index)'; then
  echo "BLOCKED: Destructive database operation detected: $COMMAND"
  exit 2
fi

# === SYSTEM ===
BLOCKED_SYS=(
  "mkfs\."
  "dd if="
  "> /dev/sd"
)

for PATTERN in "${BLOCKED_SYS[@]}"; do
  if echo "$COMMAND" | grep -qi "$PATTERN"; then
    echo "BLOCKED: Dangerous system operation '$PATTERN': $COMMAND"
    exit 2
  fi
done

# === CONSTITUTIONAL: INFRA-002 — protect infrastructure files from deletion ===
if echo "$CMD_LOWER" | grep -qE 'rm\s+.*(docker-compose|playbook|\.yml|\.yaml)'; then
  if echo "$CMD_LOWER" | grep -qE '(ansible|compose|playbook|deploy)'; then
    echo "BLOCKED: Deleting infrastructure config: $COMMAND"
    echo "INFRA-002: Never delete playbooks, compose files, or system configs without approval."
    exit 2
  fi
fi

# === CONSTITUTIONAL: SEC-003/INFRA-001 — block firewall/network changes ===
if echo "$CMD_LOWER" | grep -qE '(ufw|iptables|firewall-cmd|netplan)\s+(delete|allow|deny|reject|apply|reset)'; then
  echo "BLOCKED: Firewall/network modification: $COMMAND"
  echo "SEC-003/INFRA-001: Network/firewall changes require human approval."
  exit 2
fi

# === SECRET ACCESS ===
if echo "$CMD_LOWER" | grep -qE '(cat|less|more|head|tail|bat)\s+.*\.(env|secret|pem|key)'; then
  echo "BLOCKED: Reading secrets via Bash: $COMMAND"
  echo "Use the Read tool so the protect-paths hook can check."
  exit 2
fi

if echo "$CMD_LOWER" | grep -qE '(cat|less|more|head|tail|bat)\s+.*(vault-password|credentials\.json|id_rsa|id_ed25519)'; then
  echo "BLOCKED: Reading credentials via Bash: $COMMAND"
  exit 2
fi

exit 0
