# Security Follow-Ups

Source of truth: `config/automation-backbone/platform-topology.json`, `config/automation-backbone/credential-surface-registry.json`, `docs/runbooks/credential-rotation.md`
Validated against registry version: `platform-topology.json@2026-04-01.1`, `credential-surface-registry.json@2026-04-02.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: service placement and auth class come from the topology registry. This document tracks secret ownership, rotation priority, and the still-open security backlog.

---

## Security Baseline

- Tracked source may define variable names, empty defaults, and topology.
- Tracked source must not contain live secret values.
- Secrets belong in host-local env files, secret stores, or deployment-time injection.
- Rotation is a separate operational program and must be executed intentionally, not implied by a code change.

## Secret Ownership Map

### Routing and control plane

| Secret input | Owner | Used by |
|--------------|-------|---------|
| `athanor_litellm_api_key` | LiteLLM routing plane | dashboard, agents, EOQ, Ulrich Energy, bridge/control clients |
| `athanor_redis_url` | Shared runtime state plane | agents and any runtime that needs Redis-backed control state |
| `athanor_neo4j_password` | Graph memory plane | agents, dashboard, Neo4j clients |

### Operator and observability plane

| Secret input | Owner | Used by |
|--------------|-------|---------|
| `vault_langfuse_pg_password` | Langfuse storage plane | VAULT Langfuse deployment |
| `vault_langfuse_minio_password` | Langfuse blob plane | VAULT Langfuse deployment |
| `vault_langfuse_init_project_public_key` | Langfuse project bootstrap | Langfuse initialization only |
| `vault_langfuse_init_project_secret_key` | Langfuse project bootstrap | Langfuse initialization only |
| `vault_langfuse_init_user_password` | Langfuse bootstrap user | Langfuse initialization only |
| `athanor_miniflux_db_password` | Miniflux data plane | Miniflux deployment |
| `athanor_miniflux_pass` | Miniflux operator account | agents and Miniflux deployment |

### Media and home plane

| Secret input | Owner | Used by |
|--------------|-------|---------|
| `athanor_ha_token` | Home Assistant plane | agents |
| `athanor_sonarr_api_key` | Media plane | agents |
| `athanor_radarr_api_key` | Media plane | agents |
| `athanor_tautulli_api_key` | Media plane | agents |

### Product and app-specific plane

| Secret input | Owner | Used by |
|--------------|-------|---------|
| `athanor_ulrich_database_url` | Ulrich Energy data plane | Ulrich Energy deployment |

## Rotation Order

Rotate in this order when running a full security pass:

1. LiteLLM routing credentials
2. Neo4j and Redis-backed runtime credentials
3. Home and media API tokens
4. Langfuse bootstrap/storage credentials
5. Miniflux admin and database credentials
6. App-specific product credentials

This order keeps the main control-plane clients aligned with the routing layer before rotating more specialized integrations.

## Open Follow-Ups

- Keep `credential-surface-registry.json` aligned with the live delivery surfaces before changing any secret-bearing runtime path.
- Complete the reconciled credential-rotation runbook so it matches the current topology-backed service map.
- Keep `docs/runbooks/dev-secret-delivery-normalization.md` aligned with the live DEV cron and systemd envfile contract.
- Keep `docs/runbooks/local-runtime-env.md` aligned with the managed DESK script-lane auth path.
- Extend shared auth/privilege classes across the remaining privileged core services.
- Remove any remaining host-local drift that still points at outdated secret file paths or service names.
- Audit bootstrap identifiers that are not passwords but still widen blast radius if leaked.
- Keep secret scanning in the acceptance program and avoid adding new tracked allowlists.
- Keep generated recovery artifacts and automation evidence redacting credential-bearing URLs before writing to disk.

## Credential Surface Remediation Priorities

| Surface id | Current delivery | Target delivery | State | Approval boundary |
|------------|------------------|-----------------|-------|-------------------|
| `dev-user-crontab-inline-env` | `cron_wrapper_envfile` | `cron_wrapper_envfile` | `managed` | ask-first live runtime change |
| `dev-systemd-env-surfaces` | `service_envfile` | `service_envfile` | `managed` | ask-first live runtime change |
| `vault-litellm-container-env` | `container_env` | `container_env` | `managed` | ask-first if changed |
| `script-lane-redis-auth` | `local_runtime_envfile` | `local_runtime_envfile` | `managed` | repo/runtime shell prerequisite |

Use the generated [Secret Surface Report](./operations/SECRET-SURFACE-REPORT.md) for the evidence-backed current state and recommended actions. This document owns the priority order and security intent, not the live secret material.
