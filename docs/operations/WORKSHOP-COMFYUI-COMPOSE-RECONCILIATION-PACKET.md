# Workshop ComfyUI Compose Reconciliation Packet

## Objective

Split the Workshop ComfyUI deployment-authority delta into one bounded repair packet so it no longer lives inside the generic `deployment-authority-follow-on` bucket.

## Scope

- `ansible/roles/comfyui/defaults/main.yml`
- `ansible/roles/comfyui/templates/docker-compose.yml.j2`
- `reports/rendered/workshop-comfyui.rendered.yml`
- `reports/live/workshop-comfyui.live.yml`

## Replay Contract

1. Create `/opt/athanor/backups/comfyui/<timestamp>` and capture the current `/opt/athanor/comfyui/docker-compose.yml` plus `docker inspect comfyui`.
2. Re-render the canonical compose artifact from implementation authority before touching the runtime root.
3. Replace only `/opt/athanor/comfyui/docker-compose.yml` from the rendered artifact during the approved maintenance window.
4. Recreate only the `comfyui` container and refresh deployment-drift evidence immediately after the replacement.

## Proof Commands

- `powershell -ExecutionPolicy Bypass -File .\\scripts\\Invoke-DeploymentDriftAudit.ps1`
- `ssh workshop "cd /opt/athanor/comfyui && docker compose ps"`
- `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8188/system_stats"`
- `python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets`
- `python scripts/validate_platform_contract.py`

## Rollback Contract

- Restore the backed up `/opt/athanor/comfyui/docker-compose.yml` from `/opt/athanor/backups/comfyui/<timestamp>`.
- Recreate `comfyui` from the restored compose root.
- Re-run the deployment-drift audit and the validator.

## Retirement Condition

- `workshop-comfyui` is identical in deployment-drift truth, or the lane is explicitly retired through a replacement packet.
