---
paths:
  - "ansible/**"
---

# Ansible Conventions

- All playbooks must be idempotent (verify with 2 consecutive runs)
- Run from `ansible/` dir: `ansible-playbook playbooks/site.yml --vault-password-file vault-password -i inventory.yml`
- `docker_compose_v2` rebuild bug: when Dockerfile changes, add "stop before rebuild" tasks
- CRLF drift: Dockerfiles from WSL may deploy as CRLF. First convergence run fixes, second is clean.
- NFS `/mnt/vault/data` goes stale after VAULT reboots — common role auto-recovers
- Always include `restart: unless-stopped`, `container_name:`, log rotation, `TZ=America/Chicago`
- GPU services need `ipc: host`, `ulimits: memlock: -1`
- Pin image tags (not `:latest` unless intentionally tracking upstream)
- Vault password file: `ansible/vault-password` (exists, not in repo)
