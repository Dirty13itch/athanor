# Services Snapshot Status

The files under `services/` are legacy deployment snapshots and runtime copies.

Use these rules:

- `ansible/` is the authoritative deployment source of truth.
- `docs/BUILD-MANIFEST.md` is the tactical work queue.
- `services/` is useful for reference and forensic comparison, not for deciding current topology.

When topology, ports, or environment contracts disagree:

- trust the active Ansible roles and playbooks first
- treat `services/` diffs as drift signals that need reconciliation
