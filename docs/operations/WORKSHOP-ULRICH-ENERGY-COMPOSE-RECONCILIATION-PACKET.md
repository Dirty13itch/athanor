# Workshop Ulrich Energy Runtime Retirement Packet

## Objective

Retire the remaining Workshop `ulrich-energy` runtime lineage cleanly so the external `Ulrich Energy Auditing Website` stays the only delivery authority and the retired Athanor scaffold stops lingering as a live product lane.

## Scope

- `ansible/roles/ulrich-energy/defaults/main.yml`
- `ansible/roles/ulrich-energy/templates/docker-compose.yml.j2`
- `projects/ulrich-energy`
- `reports/rendered/workshop-ulrich-energy.rendered.yml`
- `reports/live/workshop-ulrich-energy.live.yml`

## Replay Contract

1. Create `/opt/athanor/backups/ulrich-energy/<timestamp>` and capture the current `/opt/athanor/ulrich-energy` bundle plus `docker inspect athanor-ulrich-energy`.
2. Capture the current service state and HTTP probe result for `http://127.0.0.1:3003/` so retirement evidence shows what was removed.
3. Stop and remove only the `athanor-ulrich-energy` container, then remove or archive the governed `/opt/athanor/ulrich-energy` runtime root instead of replacing it from implementation authority.
4. Demote the runtime ownership evidence so the Workshop product lane no longer treats `/opt/athanor/ulrich-energy` as an active compose root.
5. Refresh deployment-drift and runtime-ownership evidence immediately after the retirement so the lineage is preserved only as a retired packet record.

## Proof Commands

- `powershell -ExecutionPolicy Bypass -File .\\scripts\\Invoke-DeploymentDriftAudit.ps1`
- `ssh workshop "test -d /opt/athanor/ulrich-energy && docker compose -f /opt/athanor/ulrich-energy/docker-compose.yml ps || true"`
- `ssh workshop "docker ps --format '{{.Names}}' | rg '^athanor-ulrich-energy$' || true"`
- `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3003/ || true"`
- `python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets`
- `python scripts/validate_platform_contract.py`

## Rollback Contract

- Restore the backed up `/opt/athanor/ulrich-energy` bundle from `/opt/athanor/backups/ulrich-energy/<timestamp>` if the Workshop lineage must be revived.
- Recreate `athanor-ulrich-energy` from the restored compose root only through this packet’s reverse path.
- Re-run the deployment-drift audit and the validator.

## Retirement Condition

- `workshop-ulrich-energy` no longer appears as an active runtime surface in runtime-ownership truth.
- `http://192.168.1.225:3003/` is no longer treated as an Athanor product authority.
- The retired lineage remains only in packet, rollback, and archive/reference surfaces.
