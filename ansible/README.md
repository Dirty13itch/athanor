# Athanor Ansible

Infrastructure-as-code for the Athanor cluster. Ansible is the **authoritative source of truth** for all service deployments.

## Usage

```bash
cd ansible/
ansible-playbook playbooks/site.yml -i inventory.yml
ansible-playbook playbooks/foundry.yml --tags vllm
ansible-playbook playbooks/vault.yml --tags monitoring
ansible-playbook playbooks/workshop.yml --tags dashboard
```

## Structure

```
ansible.cfg          # Connection defaults, inventory path
inventory.yml        # Node definitions (foundry, workshop, vault, dev)
group_vars/          # Shared variables
host_vars/           # Per-node variables (vault.yml, foundry.yml, etc.)
playbooks/           # Entry points per node + site.yml
roles/               # One role per service (vault-monitoring, vllm, etc.)
```

## Relationship to services/

The `services/` directory at the repo root contains **legacy deployment snapshots** — manually authored compose files from before Ansible was adopted. Some are still used directly (e.g., `services/node1/agents/`), but most are superseded by Ansible roles that generate compose configs.

**When in doubt:** Ansible roles and `host_vars/` are the source of truth. Treat `services/` compose files as reference or drift signals, not deployment configs.

## Key conventions

- All playbooks must be idempotent
- Pin image tags (not `:latest`)
- Include `restart: unless-stopped`, `container_name:`, log rotation, `TZ=America/Chicago`
- GPU services need `ipc: host`, `ulimits: memlock: -1`
- VAULT uses paramiko SSH (dropbear) with root user, no become needed
- Deploy via `vault-ssh.py` for ad-hoc VAULT access
