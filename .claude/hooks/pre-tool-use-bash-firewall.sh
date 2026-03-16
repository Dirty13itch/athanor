#!/bin/bash
# PreToolUse hook: Block dangerous Bash commands
# Matcher: Bash
# Guards: destructive operations, production nodes, credential exposure
# All blocks are advisory (exit 2) — user can approve individual commands.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
if [ -z "$COMMAND" ]; then
  COMMAND=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"command"\s*:\s*"//;s/"$//')
fi

block() {
  echo "BLOCKED: $1"
  echo "Command: $COMMAND"
  echo "$2"
  exit 2
}

# --- Destructive Git/Filesystem ---
for P in \
  "rm -rf /" \
  "rm -rf /\*" \
  "git reset --hard" \
  "git push --force" \
  "git push -f " \
  "git clean -fd" \
  "git checkout -- \." \
  "mkfs\." \
  "dd if=" \
  "> /dev/sd"; do
  echo "$COMMAND" | grep -qi "$P" && block "Dangerous pattern '$P'" "Could cause irreversible damage. Ask the user first."
done

# --- Docker Container Protection ---
# Hard blocks for destructive data operations.
# docker stop/rm/down are allowed — graceful lifecycle ops.
for P in \
  "docker kill " \
  "docker volume rm" \
  "docker volume prune" \
  "docker network rm"; do
  echo "$COMMAND" | grep -qi "$P" && block "Docker destructive operation '$P'" "Container operations require user approval."
done

# --- Database Operations ---
for P in \
  "DROP TABLE" \
  "DROP DATABASE" \
  "DELETE FROM" \
  "TRUNCATE " \
  "DETACH DELETE"; do
  echo "$COMMAND" | grep -qi "$P" && block "Database destructive operation '$P'" "Mass data deletion requires user approval."
done

# --- Systemctl via SSH ---
for P in \
  "ssh.*systemctl stop" \
  "ssh.*systemctl restart" \
  "ssh.*systemctl disable" \
  "systemctl restart docker"; do
  echo "$COMMAND" | grep -qiE "$P" && block "Remote service control '$P'" "Service lifecycle changes require user approval."
done

# --- Filesystem/Partition Operations ---
for P in "fdisk " "parted " "mdadm " "lvremove"; do
  echo "$COMMAND" | grep -qi "$P" && block "Filesystem/partition operation '$P'" "Partition changes require user approval."
done

# --- Credential Leakage ---
for P in \
  'echo.*\$.*KEY' \
  'echo.*\$.*SECRET' \
  'echo.*\$.*PASSWORD'; do
  echo "$COMMAND" | grep -qiE "$P" && block "Potential credential exposure '$P'" "Credentials must not be printed to terminal."
done

# --- Ansible Production Gate ---
# Block ansible-playbook targeting FOUNDRY/site.yml unless --check is present
if echo "$COMMAND" | grep -qi "ansible-playbook"; then
  if echo "$COMMAND" | grep -qiE "(node1|foundry|192\.168\.1\.244|site\.yml)"; then
    if ! echo "$COMMAND" | grep -qi "\-\-check"; then
      block "Ansible targeting production without --check" \
        "Add --check for dry-run, or get explicit user approval."
    fi
  fi
fi

# --- Node-aware FOUNDRY Protection ---
# Block destructive verbs targeting FOUNDRY, allow read-only and graceful ops
if echo "$COMMAND" | grep -qiE "(192\.168\.1\.244|foundry|node1)" && \
   echo "$COMMAND" | grep -qiE "\b(delete|destroy|kill|disable)\b" && \
   ! echo "$COMMAND" | grep -qiE "(docker ps|nvidia-smi|docker logs|journalctl|cat |head |tail |ls |df |free |mount |curl |wget|docker stats|docker inspect|rsync |docker compose up|docker compose build|docker stop|docker rm |docker rename)"; then
  block "Destructive operation targeting FOUNDRY (.244)" \
    "FOUNDRY is production. Read-only ops allowed. Destructive actions require user approval."
fi

# --- Secrets File Access via Bash ---
for P in \
  "cat.*\.env" \
  "cat.*vault-password" \
  "cat.*credentials\.json" \
  "cat.*/\.secret"; do
  echo "$COMMAND" | grep -qiE "$P" && block "Reading secrets via Bash '$P'" "Use the Read tool instead for path protection."
done

exit 0
