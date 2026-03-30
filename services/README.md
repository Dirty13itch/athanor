# Services

This directory contains shared service implementations, compatibility shims, and service-local tests that have not all been moved under `projects/` yet.

Authority is split:
1. `config/automation-backbone/platform-topology.json` owns service identity, node placement, runtime class, auth class, and the canonical live service map.
2. `ansible/` owns deployment implementation and rollout behavior.
3. `STATUS.md` and `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` own current-state and execution-priority truth.
4. `services/` owns code for the service implementations and any remaining service-local helper shims that still live here.

Do not treat `services/` as the first source of truth for topology, ports, or deployment ownership.

When changing a service:
1. Update the topology/registry truth first if service identity, ownership, auth class, or placement changes.
2. Update the implementation code here when the service behavior itself changes.
3. Update the Ansible role or playbook when deployment behavior changes.
4. Redeploy and rerun the relevant contract and acceptance checks.

## Additional Context

- Treat diffs between `services/`, the topology registry, and deployed state as drift signals that need reconciliation.
- The retired standalone governor facade has been deleted from implementation authority; do not recreate it under `services/`.
- When topology, ports, or environment contracts disagree, trust the topology registry first and Ansible second.
