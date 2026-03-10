# Security Follow-Ups

This file tracks credentials and secret-bearing settings that were moved out of tracked source during the Athanor Next convergence work.

Current policy:

- tracked source may define variable names, empty defaults, and host topology
- tracked source must not carry live secrets
- real secret values belong in Ansible vault, host-local env files, or deployment-time secret injection
- credential rotation is deferred and must be handled as a separate follow-up program

## Centralized Secret Inputs

- `athanor_litellm_api_key`
  owner: Athanor routing / LiteLLM
  used by: dashboard, agents, EoBQ, Ulrich, VAULT Open WebUI, LiteLLM role
- `athanor_neo4j_password`
  owner: graph memory plane
  used by: dashboard, agents, VAULT Neo4j
- `athanor_redis_url`
  owner: state plane
  used by: agents
- `athanor_ha_token`
  owner: home automation plane
  used by: agents
- `athanor_sonarr_api_key`
  owner: media plane
  used by: agents
- `athanor_radarr_api_key`
  owner: media plane
  used by: agents
- `athanor_tautulli_api_key`
  owner: media plane
  used by: agents
- `athanor_miniflux_db_password`
  owner: Miniflux database
  used by: VAULT Miniflux role
- `athanor_miniflux_pass`
  owner: Miniflux admin account
  used by: agents, VAULT Miniflux role
- `vault_langfuse_pg_password`
  owner: Langfuse storage plane
  used by: VAULT Langfuse role
- `vault_langfuse_minio_password`
  owner: Langfuse blob storage
  used by: VAULT Langfuse role
- `vault_langfuse_init_project_public_key`
  owner: Langfuse project bootstrap
  used by: VAULT Langfuse role
- `vault_langfuse_init_project_secret_key`
  owner: Langfuse project bootstrap
  used by: VAULT Langfuse role
- `vault_langfuse_init_user_password`
  owner: Langfuse bootstrap user
  used by: VAULT Langfuse role
- `athanor_ulrich_database_url`
  owner: Ulrich Energy app data plane
  used by: Ulrich Energy role

## Rotation Backlog

- Rotate the LiteLLM master key after the reconciled env contract is deployed on VAULT, WORKSHOP, FOUNDRY, and DEV.
- Rotate Neo4j credentials after dashboard and agents are confirmed healthy with env-backed auth.
- Rotate Miniflux admin and DB credentials once the signal pipeline is revalidated.
- Rotate Langfuse bootstrap and storage credentials after the new compose is applied.
- Audit remaining non-secret but sensitive bootstrap identifiers such as Langfuse project keys and replace placeholder defaults where appropriate.
