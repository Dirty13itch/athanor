# DEV Node Rebuild Runbook

Source of truth: `config/automation-backbone/platform-topology.json`, `config/automation-backbone/runtime-ownership-contract.json`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/RECOVERY.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
Validated against registry version: `platform-topology.json@2026-04-01.1`, `runtime-ownership-contract.json@2026-04-02.5`, `runtime-ownership-packets.json@2026-04-02.5`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: DEV host responsibilities, service placement, port ownership, and runtime/deploy lanes come from the topology registry plus the runtime-ownership contract. This runbook covers the rebuild order for the current DEV role, not historical service layouts.

---

## DEV Role In The Current Topology

`dev` is the ops-center host. At the current registry version it owns:

- `dashboard` (`3001`)
- `quality_gate` (`8790`)
- `semantic_router` (`8060`)
- `gateway` (`8700`)
- `embedding` (`8001`)
- `reranker` (`8003`)
- `memory` (`8720`)
- `subscription_burn` (`8065`, scaffold)
- `openfang` (`4200`, scaffold)

If that list changes, update the topology registry first.

## Rebuild Order

### 1. Base host

- Install the current supported OS image for DEV.
- Restore SSH access and the operator account.
- Restore Docker, Python, Node, and any GPU/runtime prerequisites needed for embedding and reranker services.
- Restore host-local secrets without committing them into the repo.

### 2. Repo and toolchain

1. Restore the DEV runtime repo at `/home/shaun/repos/athanor`.
2. Restore Python virtual environments or recreate them for DEV-owned services.
3. Restore Node dependencies for the dashboard and any DEV-owned JS surfaces.
4. Verify the local operator toolchain needed to run the core acceptance commands.

### 3. Shared dependencies

Before bringing DEV services online, confirm these upstreams are already healthy:

- `redis`
- `qdrant`
- `neo4j`
- `litellm`

DEV should not come back “green” while disconnected from its state and routing dependencies.

### 4. Restore DEV services

Bring back the services in this order:

1. Restore repo-root systemd services from `/home/shaun/repos/athanor`:
   - `embedding`
   - `reranker`
   - `semantic_router`
   - `gateway`
   - `memory`
   - `quality_gate`
2. Restore `/opt/athanor/heartbeat` and `athanor-heartbeat.service`.
3. Restore `/opt/athanor/dashboard` from the runtime repo dashboard project and bring back the compose lane behind Caddy.
4. Restore scaffold surfaces only if needed for the current incident (`subscription_burn`, `openfang`).

The first healthy human-facing check should happen only after `quality_gate` and the `/opt/athanor/dashboard` compose lane are connected to their upstreams and the canonical agent-server task/governor surfaces are healthy.

## Runtime Ownership Notes

- Repo-root systemd services on DEV run from `/home/shaun/repos/athanor`.
- The active dashboard runs from `/opt/athanor/dashboard` through Docker Compose behind Caddy.
- `athanor-dashboard.service` is not the active deployment path and should be treated as recovery-only until it is retired explicitly.
- Heartbeat is a separate `/opt/athanor/heartbeat` lane.
- `/home/shaun/.athanor`, `/etc/systemd/system/athanor-*`, and `/etc/cron.d/athanor-*` are runtime-state roots and must be rebuilt as host state, not guessed from repo layout.

### 5. Verify

Run the smallest useful checks in order:

- `python scripts/validate_platform_contract.py`
- dashboard acceptance contract
- `docker compose -f /opt/athanor/dashboard/docker-compose.yml ps`
- `systemctl is-active athanor-heartbeat.service`
- focused service health checks for the canonical agent-server task/governor surfaces, `quality_gate`, `embedding`, and `reranker`
- any incident-specific read/write check required by the restore

## What This Runbook Excludes

- historical `mind`, `perception`, `classifier`, or legacy `ui` rebuild steps
- ad hoc shell-tool restoration from old personal notes
- non-registry service sprawl unless it is explicitly promoted back into the topology

If a host-level tool matters operationally but is not in the topology registry, treat it as reference-only until the registry is updated.
