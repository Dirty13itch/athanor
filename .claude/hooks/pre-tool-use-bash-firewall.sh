#!/bin/bash
# PreToolUse hook: Block dangerous Bash commands
# Matcher: Bash
# Blocks: destructive git operations, rm -rf /, force pushes, database drops

INPUT=$(cat)

# Extract the command from tool input using jq
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Fallback to grep if jq fails
if [ -z "$COMMAND" ]; then
  COMMAND=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"command"\s*:\s*"//;s/"$//')
fi

# Dangerous patterns to block
BLOCKED_PATTERNS=(
  "rm -rf /"
  "rm -rf /*"
  "git reset --hard"
  "git push --force"
  "git push -f "
  "git clean -fd"
  "git checkout -- ."
  "DROP TABLE"
  "DROP DATABASE"
  "mkfs\."
  "dd if="
  "> /dev/sd"
)

for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qi "$PATTERN"; then
    echo "BLOCKED: Dangerous command matching '$PATTERN': $COMMAND"
    echo "This command could cause irreversible damage. Ask the user before proceeding."
    exit 2
  fi
done

# Block reading secrets files via Bash (cat .env, etc.)
SECRET_PATTERNS=(
  "cat.*\.env"
  "cat.*vault-password"
  "cat.*credentials\.json"
  "cat.*/\.secret"
)

for PATTERN in "${SECRET_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qiE "$PATTERN"; then
    echo "BLOCKED: Reading secrets via Bash matching '$PATTERN': $COMMAND"
    echo "Use the Read tool instead so the protect-paths hook can check."
    exit 2
  fi
done

exit 0
