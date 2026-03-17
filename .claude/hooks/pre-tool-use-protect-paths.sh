#!/bin/bash
# PreToolUse hook: Block writes to protected paths
# Matcher: Edit|Write|MultiEdit
# Protects: VAULT Unraid configs, SSH keys, parity assignments

INPUT=$(cat)

# Extract file path using jq
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Fallback to grep if jq fails
if [ -z "$FILE_PATH" ]; then
  FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"$//')
fi

# Protected patterns
PROTECTED_PATTERNS=(
  "/boot/config/"           # Unraid boot config
  "/etc/ssh/ssh_host"       # SSH host keys
  "/.ssh/id_"               # SSH private keys
  "/.ssh/authorized_keys"   # Managed by setup scripts
  "/proc/mdcmd"             # Unraid array commands
  "disk.cfg"                # Unraid disk/parity config
  ".env"                    # Environment secrets
  "vault-password"          # Ansible vault password
  "credentials.json"        # Service credentials
  ".secret"                 # Generic secrets
  "CONSTITUTION.yaml"       # AUTO-001: Constitutional constraints (immutable)
  "/etc/ufw/"               # SEC-003/INFRA-001: Firewall rules
  "/etc/iptables"           # SEC-003/INFRA-001: Firewall rules
  "/etc/netplan/"           # INFRA-001: Network configuration
)

for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -q "$PATTERN"; then
    echo "BLOCKED: Writing to protected path matching '$PATTERN': $FILE_PATH"
    echo "These paths require manual modification. Ask the user before proceeding."
    exit 2
  fi
done

exit 0
