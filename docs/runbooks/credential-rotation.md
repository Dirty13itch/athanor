# Credential Rotation Runbook

## LiteLLM Master Key
**Used by:** 10+ services across 4 nodes (Gateway, MIND, Memory, Perception, OpenFang, aider, Kilo Code, Continue.dev, all CLI tools)
**Location:** ~/.secrets/litellm-master-key on DEV
**LiteLLM config:** /mnt/user/appdata/litellm/config.yaml on VAULT (env var LITELLM_MASTER_KEY)

### Rotation Steps:
1. Generate new key: `openssl rand -hex 32 | sed "s/^/sk-athanor-/" > ~/.secrets/litellm-master-key-new`
2. Update VAULT LiteLLM env: `ssh root@192.168.1.203 "sed -i s/OLD_KEY/NEW_KEY/ /mnt/docker/appdata/litellm/.env"`
3. Restart LiteLLM: `ssh root@192.168.1.203 "docker restart litellm"`
4. Verify LiteLLM health: `curl -H "Authorization: Bearer NEW_KEY" http://192.168.1.203:4000/health`
5. Update DEV services: restart Gateway, MIND, Memory, Perception, OpenFang
6. Update CLI configs: ~/.aider.conf.yml, ~/.continue/config.json, ~/.config/kilo/custom_modes.yaml, ~/.config/goose/profiles.yaml
7. Verify all services: `bash scripts/drift-check.sh`
8. Replace old key file: `mv ~/.secrets/litellm-master-key-new ~/.secrets/litellm-master-key`
9. Remove old key from any tracked files: `gitleaks detect --source . --no-git`

## GitHub PAT
**Location:** ~/.secrets/github-pat
**Used by:** gh CLI, Gitea Actions, Claude Code MCP

## Anthropic API Key
**Location:** ANTHROPIC_API_KEY env var
**Used by:** Claude Code (Max subscription)

## OpenAI API Key  
**Location:** OPENAI_API_KEY env var
**Used by:** Codex CLI (Pro subscription)

## All Secrets Registry
Check ~/.secrets/ for full list. Each file = one secret.
