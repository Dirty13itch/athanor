# Services (Snapshot Only)

These files are point-in-time snapshots of service configurations.
The authoritative source of truth for all service definitions is `ansible/`.

Do NOT modify files here directly. Instead:
1. Update the Ansible role/task in `ansible/`
2. Run the playbook to deploy
3. Take a new snapshot if needed

## Additional Context

- `docs/BUILD-MANIFEST.md` is the tactical work queue.
- These snapshots are useful for reference and forensic comparison, not for deciding current topology.
- When topology, ports, or environment contracts disagree, trust the active Ansible roles and playbooks first.
- Treat diffs between `services/` and deployed state as drift signals that need reconciliation.
