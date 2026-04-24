# Workshop EOQ Compose Reconciliation Packet

## Objective

Split the Workshop EOQ deployment-authority delta into one bounded repair packet so it no longer lives inside the generic `deployment-authority-follow-on` bucket.

## Scope

- `ansible/roles/eoq/defaults/main.yml`
- `ansible/roles/eoq/templates/docker-compose.yml.j2`
- `projects/eoq`
- `reports/rendered/workshop-eoq.rendered.yml`
- `reports/live/workshop-eoq.live.yml`

## Replay Contract

1. Create `/opt/athanor/backups/eoq/<timestamp>` and capture the current `/opt/athanor/eoq` bundle plus `docker inspect athanor-eoq`.
2. Re-render the canonical compose artifact from implementation authority before touching the runtime root.
3. Replace the governed `/opt/athanor/eoq` source bundle from implementation authority when the approved change actually depends on in-repo source, then replace `/opt/athanor/eoq/docker-compose.yml` from the rendered artifact.
4. Recreate only the `athanor-eoq` container and refresh deployment-drift evidence immediately after the replacement.

## Proof Commands

- `powershell -ExecutionPolicy Bypass -File .\\scripts\\Invoke-DeploymentDriftAudit.ps1`
- `ssh workshop "cd /opt/athanor/eoq && docker compose ps"`
- `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3002/"`
- `python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets`
- `python scripts/validate_platform_contract.py`

## Rollback Contract

- Restore the backed up `/opt/athanor/eoq` bundle from `/opt/athanor/backups/eoq/<timestamp>`.
- Recreate `athanor-eoq` from the restored compose root.
- Re-run the deployment-drift audit and the validator.

## Retirement Condition

- `workshop-eoq` is identical in deployment-drift truth, or the lane is explicitly retired through a replacement packet.
