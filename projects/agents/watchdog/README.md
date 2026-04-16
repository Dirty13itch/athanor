# Athanor Watchdog Runtime Guard

This is the Athanor-owned watchdog runtime guard that now backs the bounded
live canary remediation surface on FOUNDRY.

The service monitors 28 cluster services across FOUNDRY, WORKSHOP, DEV, and
VAULT. It can perform Band A remediation (`docker restart` via SSH), and the
mutation path is now live but still tightly bounded:

- monitoring stays live
- auto-remediation is live in canary mode
- runtime mutations stay packet-backed through the executed rollout packet and
  explicit env gate
- protected services remain page-only even for manual restart requests

Build-side design and proof still live in devstack:
- `C:/athanor-devstack/designs/watchdog-agent-and-gpu-scheduler.md`
- `C:/athanor-devstack/designs/watchdog-mvw-implementation-plan.md`
- `C:/athanor-devstack/docs/promotion-packets/watchdog-runtime-guard.md`

## Current contract

- Athanor source bundle: `C:/Athanor/projects/agents/watchdog`
- Target runtime root: `/opt/athanor/watchdog`
- Runtime packet: `foundry-watchdog-runtime-guard-rollout-packet`
- Default packet status env: `executed`
- Default mutation gate: `WATCHDOG_MUTATIONS_ENABLED=true`
- Default operating mode: `active`

The watchdog is now a bounded live canary surface, not a free-to-mutate
autonomous repair loop. Packet-backed rollout, protected-service exclusions,
and operator-envelope enforcement remain the governing boundaries.

## Scope

Current scope:
- 28 HTTP, TCP, and SSH probes across all 4 nodes
- Band A remediation (`docker restart` via SSH)
- in-memory circuit breaker
- ntfy paging with priorities and tags
- FastAPI control surface: `/health`, `/status`, `/pause`, `/resume`,
  `/service/{id}/restart`, `/metrics`
- operator-envelope enforcement for all control mutations
- audit log output for accepted, denied, and dry-run mutation requests

Still deferred:
- Bands B, C, and D remediation
- Redis-backed circuit state
- GPU, disk, network, and data checks
- dependency graph enforcement
- GPU scheduler integration
- broader LangGraph promotion work

## Deployment

Runs on **FOUNDRY:9301** with `network_mode: host`.

The rollout must stay packet-backed. Do not treat ad hoc `scp` and `docker
compose up` commands as ordinary maintenance once the packeted deploy path
exists.

## Operating

| Action | Example |
| --- | --- |
| Check liveness | `curl http://192.168.1.244:9301/health` |
| Inspect guard state | `curl http://192.168.1.244:9301/status` |
| Pause auto-remediation | `curl -X POST http://192.168.1.244:9301/pause -H "Content-Type: application/json" -d "{\"actor\":\"shaun\",\"session_id\":\"watchdog-maint\",\"correlation_id\":\"pause-001\",\"reason\":\"Maintenance window\"}"` |
| Dry-run manual restart | `curl -X POST http://192.168.1.244:9301/service/foundry.graphrag/restart -H "Content-Type: application/json" -d "{\"actor\":\"shaun\",\"session_id\":\"watchdog-maint\",\"correlation_id\":\"dryrun-001\",\"reason\":\"Verify restart path\",\"dry_run\":true,\"protected_mode\":true}"` |
| Resume after maintenance pause | `curl -X POST http://192.168.1.244:9301/resume -H "Content-Type: application/json" -d "{\"actor\":\"shaun\",\"session_id\":\"watchdog-maint\",\"correlation_id\":\"resume-001\",\"reason\":\"Resume watchdog canary\",\"protected_mode\":true}"` |
| Scrape metrics | `curl http://192.168.1.244:9301/metrics` |

Notes:
- `/resume` requires a destructive-admin envelope and fails if the runtime
  mutation gate is closed.
- manual restart also requires a destructive-admin envelope.
- `dry_run=true` is supported for pause and restart inspection.
- protected services reject manual restart even with a valid envelope.

## ntfy notifications

Default topic: `http://192.168.1.203:8880/athanor-infra`

Priority levels:
- `default` - recoveries and accepted restart actions
- `high` - guarded unhealthy services that need manual action
- `urgent` - P0 down, restart failed, or circuit open

## Environment variables

| Var | Default | Purpose |
| --- | --- | --- |
| `WATCHDOG_PORT` | `9301` | HTTP port |
| `WATCHDOG_NTFY_URL` | `http://192.168.1.203:8880` | ntfy base URL |
| `WATCHDOG_NTFY_TOPIC` | `athanor-infra` | Default ntfy topic |
| `WATCHDOG_TICK_SECONDS` | `15` | Outer loop interval |
| `WATCHDOG_FAILURE_THRESHOLD` | `3` | Consecutive failures before action |
| `WATCHDOG_INITIAL_PAUSED` | `true` | Code-level safety default; FOUNDRY canary compose sets `false` |
| `WATCHDOG_MUTATIONS_ENABLED` | `false` | Code-level safety default; FOUNDRY canary compose sets `true` |
| `WATCHDOG_RUNTIME_PACKET_ID` | `foundry-watchdog-runtime-guard-rollout-packet` | Governing runtime packet id |
| `WATCHDOG_RUNTIME_PACKET_STATUS` | `ready_for_approval` | Governing packet state; FOUNDRY canary compose sets `executed` |
| `WATCHDOG_AUDIT_LOG` | `/var/log/athanor/watchdog-operator-audit.log` | Audit log path |
| `WATCHDOG_SSH_KEY` | `/ssh-keys/watchdog_key` | SSH key path for probes and restarts |

## Service catalog

See `catalog.py` for the full list.

Protected page-only services include:
- `foundry.vllm-tp4`
- `workshop.vllm-vision`
- `dev.vllm-embedding`
- `vault.redis`
- `vault.ntfy`

These services do not auto-remediate and also reject manual restarts through
the watchdog surface.

## Architecture decisions

1. Standalone FastAPI service, not an in-process agent-server route. The
   watchdog must be able to observe and restart adjacent services without
   becoming coupled to `athanor-agents`.
2. SSH is the single restart path for every node, including FOUNDRY-local
   restarts, so the service does not need Docker socket write access.
3. Runtime mutation remains packet-backed and env-gated even after the service
   lands in Athanor source.
4. Protected services stay page-only until a future bounded packet explicitly
   widens the contract.
