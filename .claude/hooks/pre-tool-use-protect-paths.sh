#!/bin/bash
# PreToolUse hook: Block writes to protected paths
# Matcher: Write|Edit
# Protects: VAULT Unraid configs, SSH keys, parity assignments

# Read the tool input from stdin
INPUT=$(cat)

# Extract file path from the input
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"$//')

# Protected patterns
PROTECTED_PATTERNS=(
  "/boot/config/"           # Unraid boot config
  "/etc/ssh/ssh_host"       # SSH host keys
  "/.ssh/id_"               # SSH private keys
  "/.ssh/authorized_keys"   # Managed by setup scripts
  "/proc/mdcmd"             # Unraid array commands
  "disk.cfg"                # Unraid disk/parity config
)

for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -q "$PATTERN"; then
    echo "BLOCKED: Writing to protected path matching '$PATTERN': $FILE_PATH"
    echo "These paths require manual modification. Ask the user before proceeding."
    exit 2
  fi
done

exit 0
