# Workshop Open WebUI Compose Reconciliation Packet

## Objective

Split the Workshop Open WebUI deployment-authority delta into one bounded repair packet so it no longer lives inside the generic `deployment-authority-follow-on` bucket.

## Scope

- `ansible/roles/open-webui/defaults/main.yml`
- `ansible/roles/open-webui/templates/docker-compose.yml.j2`
- `reports/rendered/workshop-open-webui.rendered.yml`
- `reports/live/workshop-open-webui.live.yml`

## Replay Contract

1. Create `/opt/athanor/backups/open-webui/<timestamp>` and capture the current `/opt/athanor/open-webui/docker-compose.yml` plus `docker inspect open-webui`.
2. Re-render the canonical compose artifact from implementation authority before touching the runtime root.
3. Replace only `/opt/athanor/open-webui/docker-compose.yml` from the rendered artifact during the approved maintenance window.
4. Recreate only the `open-webui` container and refresh deployment-drift evidence immediately after the replacement.

## Proof Commands

- `powershell -ExecutionPolicy Bypass -File .\\scripts\\Invoke-DeploymentDriftAudit.ps1`
- `ssh workshop "cd /opt/athanor/open-webui && docker compose ps"`
- `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/"`
- `python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets`
- `python scripts/validate_platform_contract.py`

## Rollback Contract

- Restore the backed up `/opt/athanor/open-webui/docker-compose.yml` from `/opt/athanor/backups/open-webui/<timestamp>`.
- Recreate `open-webui` from the restored compose root.
- Re-run the deployment-drift audit and the validator.

## Retirement Condition

- `workshop-open-webui` is identical in deployment-drift truth, or the lane is explicitly retired through a replacement packet.
