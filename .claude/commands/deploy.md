---
description: Deploy a service to Athanor infrastructure. Usage: /deploy [service-name]
disable-model-invocation: true
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
argument-hint: "[agents|dashboard|vllm|comfyui|monitoring|gpu-orchestrator|all]"
---

Deploy the specified service: $ARGUMENTS

## Deployment Targets

| Target | Deploy Method | Command |
|--------|--------------|---------|
| `agents` | rsync + docker rebuild | rsync src → Node 1, docker compose build --no-cache, up -d |
| `dashboard` | rsync + docker rebuild | rsync src → Node 2, docker compose up -d --build |
| `vllm` | Ansible | ansible-playbook playbooks/site.yml --tags vllm |
| `comfyui` | Ansible | ansible-playbook playbooks/site.yml --tags comfyui |
| `monitoring` | Ansible vault.yml | ansible-playbook playbooks/vault.yml --tags monitoring |
| `gpu-orchestrator` | rsync + docker rebuild | rsync → Node 1, docker compose up -d --build |
| `all` | Ansible site.yml + vault.yml | Full deployment (both playbooks) |

## Process

1. Identify the target from $ARGUMENTS
2. Check for uncommitted changes that should be deployed
3. Run the appropriate deploy commands
4. Verify the deployment (health check, docker ps, curl endpoints)
5. Report results

## Notes

- Ansible runs from `ansible/` directory with `--vault-password-file vault-password -i inventory.yml`
- Agent/dashboard deploys also need pyproject.toml and docker-compose.yml if deps changed
- Always verify health after deploy before marking complete
