# Secret Surface Report

Generated from `config/automation-backbone/credential-surface-registry.json` plus the cached VAULT env audit artifact by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-16.1`
- Surfaces tracked: `6`
- VAULT LiteLLM env audit: `2026-04-16T22:15:59Z`

### Remediation states

| Remediation state | Count |
| --- | --- |
| `managed` | 5 |
| `remediation_required` | 1 |

### VAULT provider blockers

- Missing-secret env blockers: none
- Present-key, auth-mode, or auth-surface mismatch failures: `dashscope_qwen_api (auth_surface_mismatch)`, `google_gemini_api (present_key_invalid)`, `openai_api (present_key_invalid)`, `openrouter_api (present_key_invalid)`
- Unresolved auth failures: none
- Direct env gaps not currently blocking a live observed path: `moonshot_api`

| Surface | Host | Delivery | Target | Risk | Remediation |
| --- | --- | --- | --- | --- | --- |
| `dev-user-crontab-inline-env` | `dev` | `cron_wrapper_envfile` | `cron_wrapper_envfile` | `managed_runtime_surface` | `managed` |
| `dev-systemd-env-surfaces` | `dev` | `service_envfile` | `service_envfile` | `managed_runtime_surface` | `managed` |
| `vault-litellm-container-env` | `vault` | `container_env` | `container_env` | `managed_container_surface` | `remediation_required` |
| `script-lane-redis-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |
| `script-lane-vault-ssh-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |
| `script-lane-litellm-gateway-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |

## dev-user-crontab-inline-env

- Path: `/var/spool/cron/crontabs/shaun -> /home/shaun/.athanor/runtime.env`
- Owner surface: recurring subscription and operator jobs
- Env contracts: `ATHANOR_LITELLM_API_KEY`, `LITELLM_MASTER_KEY`, `ATHANOR_AGENT_API_TOKEN`
- Observed state: `envfile_backed`
- Target delivery: `cron_wrapper_envfile`
- Remediation state: `managed`
- Ask-first required: `True`
- Managed by: `dev-runtime-ops`
- Evidence sources: `DEV runtime inventory probe 2026-03-25`, `DEV ssh crontab audit 2026-03-26`, `DEV cron envfile normalization 2026-03-26`
- Recommended actions: `Keep recurring Athanor user-crontab jobs sourcing /home/shaun/.athanor/runtime.env through BASH_ENV instead of reintroducing inline secret-bearing assignments.`, `Keep the dedicated /etc/cron.d/athanor-* files separate from the user-crontab envfile contract so system cron and operator cron do not get conflated.`, `Back up the user crontab before future secret-delivery edits and rerun the truth collector after each live change.`
- Notes: `The Shaun user crontab now uses SHELL=/bin/bash plus BASH_ENV=/home/shaun/.athanor/runtime.env for secret-bearing Athanor jobs.`, `The 2026-03-26 follow-up verified the inline secret-bearing assignments were removed from the user crontab.`, `The 2026-03-26 audit confirmed /etc/cron.d/athanor-drift-check and /etc/cron.d/athanor-overnight remain separate non-user cron surfaces.`, `Presence is tracked here; secret values are intentionally omitted.`

## dev-systemd-env-surfaces

- Path: `/etc/systemd/system/athanor-*.service`
- Owner surface: live Athanor systemd units
- Env contracts: none
- Observed state: `envfile_or_envless_contract`
- Target delivery: `service_envfile`
- Remediation state: `managed`
- Ask-first required: `True`
- Managed by: `dev-runtime-ops`
- Evidence sources: `DEV runtime inventory probe 2026-03-25`, `DEV ssh systemd audit 2026-03-26`, `DEV systemd envfile verification 2026-03-26`
- Recommended actions: `Keep env-bearing Athanor units on explicit EnvironmentFile delivery and treat envless units as a deliberate contract instead of implicit shell inheritance.`, `Back up touched unit files before future runtime edits and rerun systemctl plus the truth collector after each change.`, `Keep dashboard, classifier, and heartbeat as the reference envfile-backed services for future normalization work.`
- Notes: `The reviewed Athanor systemd estate now uses EnvironmentFile where runtime configuration is required and otherwise stays envless by explicit contract.`, `The 2026-03-26 verification confirmed athanor-classifier.service, athanor-dashboard.service, and athanor-heartbeat.service are EnvironmentFile-backed.`

## vault-litellm-container-env

- Path: `appdata/litellm`
- Owner surface: LiteLLM upstream provider keys plus local master-key contract
- Env contracts: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `CODESTRAL_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `MOONSHOT_API_KEY`, `DASHSCOPE_API_KEY`, `VENICE_API_KEY`, `ZAI_API_KEY`, `OPENROUTER_API_KEY`, `LITELLM_MASTER_KEY`, `REDIS_PASSWORD`
- Observed state: `partial_runtime_env_presence`
- Target delivery: `container_env`
- Remediation state: `remediation_required`
- Ask-first required: `True`
- Managed by: `vault-runtime-ops`
- Evidence sources: `VAULT LiteLLM template and appdata layout review 2026-03-25`, `VAULT live docker inspect env-presence audit 2026-03-29`, `VAULT provider-specific LiteLLM probe 2026-03-29`, `VAULT LiteLLM implementation-authority role parity review 2026-03-29`, `VAULT live docker inspect env-presence audit 2026-04-08`, `VAULT live docker inspect env-presence audit 2026-04-16`
- Recommended actions: `Keep LiteLLM provider keys in the managed VAULT container env surface or an equivalent host-local secret source.`, `Keep the live VAULT container env aligned with every provider key referenced by ansible/roles/vault-litellm/templates/litellm_config.yaml.j2.`, `Treat the tracked repo as env-contract authority only; the remaining missing keys are not recoverable from tracked source or the reviewed DESK-local runtime env surfaces.`, `Use the generated VAULT auth-repair packet to decide whether a lane needs missing-key restoration, present-key rotation, or auth-mode review before recreating or redeploying the container.`, `Keep repo truth focused on env contracts, delivery boundaries, and repair sequencing rather than freezing point-in-time live env presence into this registry.`, `Do not move provider keys into tracked source or ad hoc shell history during future routing changes.`
- Notes: `Backed by the current LiteLLM template and runtime appdata layout.`, `Implementation-authority LiteLLM env-contract parity is already fixed and validator-enforced; the remaining work is runtime-only and should be driven by the current env-audit plus provider-probe artifacts.`, `This registry tracks contract names, delivery surface, and remediation posture; the generated reports own point-in-time present or missing env observations.`, `The running VAULT LiteLLM surface currently appears as a standalone Docker container with a config bind mount, not a discovered compose-managed env source.`, `Tracked `ansible/host_vars/vault.yml` does not hold the `vault_*` secret aliases for the remaining missing LiteLLM keys; the intended owner pattern is an untracked Ansible secret-vars surface adjacent to the VAULT host config or an equivalent host-local secret source.`, `This registry tracks contract names only, not secret material.`, `The live VAULT config now proves `LITELLM_MASTER_KEY` is part of the same container-env delivery contract as the provider keys and should stay modeled here.`
- Latest live env audit: `2026-04-16T22:15:59Z`
- Audit status: `ok`
- Runtime owner surface: `standalone_docker_container`
- Container image: `ghcr.io/berriai/litellm:main-stable`
- Restart policy: `unless-stopped`
- Env-change boundary: `container_recreate_or_redeploy`
- Config-only boundary: `docker_restart_litellm`
- Container envs present: `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Container envs missing: `DASHSCOPE_API_KEY`, `MOONSHOT_API_KEY`
- Config-referenced envs present at runtime: `CODESTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Config-referenced envs missing at runtime: `DASHSCOPE_API_KEY`
- Host shell envs present (informational snapshot only; not the LiteLLM delivery contract): none
- Host shell envs missing (informational snapshot only; not a blocking delivery contract by itself): `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- dockerMan template matches: none
- Compose-manager matches: none
- docker.config.json template mapping: `none`
- container-watchdog monitors litellm: `true`
- Boot-config references: `/boot/config/custom/backup-scripts/container-watchdog.sh`, `/boot/config/plugins/dynamix.my.servers/configs/docker.config.json`
- Container launch command: `docker/prod_entrypoint.sh --config /app/config.yaml --port 4000 --num_workers 4`
- Appdata files: `/mnt/user/appdata/litellm/backups/config.yaml.$ts.bak`, `/mnt/user/appdata/litellm/backups/config.yaml.20260329-191944.bak`, `/mnt/user/appdata/litellm/backups/config.yaml.20260329-192005.bak`, `/mnt/user/appdata/litellm/backups/config.yaml.20260330-022430.bak`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260329-191944.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022430.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022603.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.rollback-source.20260330-022725.json`, `/mnt/user/appdata/litellm/config.yaml`, `/mnt/user/appdata/litellm/config.yaml.bak`, `/mnt/user/appdata/litellm/config.yaml.bak-20260318-2354`, `/mnt/user/appdata/litellm/config.yaml.bak-20260319-0936`, `/mnt/user/appdata/litellm/config.yaml.bak-20260407`, `/mnt/user/appdata/litellm/config.yaml.bak-20260408`, `/mnt/user/appdata/litellm/config.yaml.bak-20260409-session4`, `/mnt/user/appdata/litellm/config.yaml.bak-tier24`, `/mnt/user/appdata/litellm/config.yaml.bak.1344`, `/mnt/user/appdata/litellm/config.yaml.bak.1772921405`, `/mnt/user/appdata/litellm/config.yaml.bak.1773047728`, `/mnt/user/appdata/litellm/config.yaml.bak.1773469196`, `/mnt/user/appdata/litellm/config.yaml.bak.1773546264`, `/mnt/user/appdata/litellm/config.yaml.broken`, `/mnt/user/appdata/litellm/config.yaml.pre-reroute`
- Historical inspect backups: `/mnt/user/appdata/litellm/backups/litellm.inspect.20260329-191944.json` -> `CODESTRAL_API_KEY`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LITELLM_MASTER_KEY`, `PATH`, `SSL_CERT_FILE`, `VENICE_API_KEY`; `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022430.json` -> `CODESTRAL_API_KEY`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LITELLM_MASTER_KEY`, `OPENAI_API_KEY`, `PATH`, `SSL_CERT_FILE`, `VENICE_API_KEY`; `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022603.json` -> `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `PATH`, `SSL_CERT_FILE`, `VENICE_API_KEY`; `/mnt/user/appdata/litellm/backups/litellm.inspect.rollback-source.20260330-022725.json` -> `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `PATH`, `SSL_CERT_FILE`, `VENICE_API_KEY`
- Repair packet: [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md)

## script-lane-redis-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: automation record persistence
- Env contracts: `ATHANOR_REDIS_URL`, `ATHANOR_REDIS_PASSWORD`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `Automation artifact persistence failure on DESK shell 2026-03-25`, `DESK runtime env audit 2026-03-26`, `DESK runtime env bootstrap 2026-03-26`, `Contract healer and recovery evidence persistence succeeded 2026-03-26`
- Recommended actions: `Keep ATHANOR_REDIS_URL and ATHANOR_REDIS_PASSWORD in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE rather than ad hoc shell exports.`, `Use python scripts/runtime_env.py --check ATHANOR_REDIS_URL ATHANOR_REDIS_PASSWORD to verify the managed local env surface without printing secret values.`, `Keep Redis-backed automation scripts failing closed if the managed local env surface disappears.`
- Notes: `The managed local runtime env surface is present and resolves both ATHANOR_REDIS_URL and ATHANOR_REDIS_PASSWORD.`, `Redis-backed automation evidence now persists through the managed local env surface instead of ad hoc shell exports.`

## script-lane-vault-ssh-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: VAULT SSH-backed operator access
- Env contracts: `ATHANOR_VAULT_KEY_PATH`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `VAULT browser-terminal recovery 2026-04-02`, `DESK runtime env audit 2026-04-02`, `DESK direct vault-ssh helper verification 2026-04-02`
- Recommended actions: `Keep ATHANOR_VAULT_KEY_PATH in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE so the VAULT helpers use the managed local SSH key path instead of ad hoc shell state or browser-only recovery.`, `Use python scripts/runtime_env.py --check ATHANOR_VAULT_KEY_PATH and python scripts/vault-ssh.py "echo CONNECTED && hostname" to verify the managed local env surface without printing secret values.`, `Treat ATHANOR_VAULT_USER and ATHANOR_VAULT_PASSWORD as optional overrides; the current contract uses the managed key path and the default VAULT root user.`
- Notes: `The managed local runtime env surface now carries the explicit VAULT SSH key-path contract needed by scripts/vault-ssh.py and scripts/ssh-vault.ps1.`, `DESK-side VAULT operator access no longer depends on the authenticated browser terminal as the only working recovery path.`

## script-lane-litellm-gateway-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: gateway-backed CLI and editor adapters
- Env contracts: `ATHANOR_LITELLM_API_KEY`, `ATHANOR_LITELLM_URL`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `DESK gateway env audit 2026-04-14`, `Goose wrapper smoke via managed runtime env 2026-04-14`, `Aider wrapper smoke via managed runtime env 2026-04-14`
- Recommended actions: `Keep the canonical DESK LiteLLM contract anchored in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE instead of ad hoc shell exports.`, `Allow LITELLM_API_KEY or LITELLM_MASTER_KEY to satisfy ATHANOR_LITELLM_API_KEY through scripts/runtime_env.py rather than copying the same secret into multiple local files.`, `Use python scripts/runtime_env.py --check ATHANOR_LITELLM_URL ATHANOR_LITELLM_API_KEY OPENAI_API_BASE OPENAI_API_KEY plus the Goose and Aider wrappers to verify the managed local env surface without printing secret values.`
- Notes: `The DESK managed runtime env surface now resolves the Athanor LiteLLM gateway contract for Goose, Aider, and generated editor-adapter profiles.`, `Compatibility envs OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_HOST, and OPENAI_BASE_PATH are derived at launcher time from the canonical Athanor contract rather than being tracked as independent secret-bearing surface entries.`
