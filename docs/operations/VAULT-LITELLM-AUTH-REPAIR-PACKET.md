# VAULT LiteLLM Auth Repair Packet

Generated from `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/provider-catalog.json`, and the cached VAULT env-audit plus provider-usage artifacts by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

This packet is the repo-safe execution guide for an approved VAULT LiteLLM provider-auth maintenance window. It scopes the live work to the `litellm` container env surface only and keeps runtime mutation approval-gated.

- Credential surface version: `2026-03-29.2`
- Provider catalog version: `2026-03-29.1`
- Cached truth snapshot: `2026-03-30T16:42:28.938927+00:00`
- Cached env audit: `2026-03-30T16:42:28Z`
- Surface id: `vault-litellm-container-env`
- Host: `vault`
- Runtime owner surface: `standalone_docker_container`
- Container: `litellm`
- Container image: `ghcr.io/berriai/litellm:main-v1.81.9-stable`
- Restart policy: `unless-stopped`
- Env-change boundary: `container_recreate_or_redeploy`
- Config-only boundary: `docker_restart_litellm`
- Launch command: `docker/prod_entrypoint.sh --config /app/config.yaml --port 4000 --num_workers 4`
- Managed source matches: docker template none, compose manager none
- Boot-config references: `/boot/config/plugins/dynamix.my.servers/configs/docker.config.json`
- Detailed runbook: [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md)
- Companion reports: [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md), [SECRET-SURFACE-REPORT.md](/C:/Athanor/docs/operations/SECRET-SURFACE-REPORT.md)

## Current Runtime Truth

- Container envs present: `CODESTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `VENICE_API_KEY`
- Container envs missing: `ANTHROPIC_API_KEY`, `DASHSCOPE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENROUTER_API_KEY`, `ZAI_API_KEY`
- Host shell envs present: none
- Host shell envs missing: `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Runtime appdata files: `/mnt/user/appdata/litellm/backups/config.yaml.20260329-191944.bak`, `/mnt/user/appdata/litellm/backups/config.yaml.20260329-192005.bak`, `/mnt/user/appdata/litellm/backups/config.yaml.20260330-022430.bak`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260329-191944.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022430.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022603.json`, `/mnt/user/appdata/litellm/backups/litellm.inspect.rollback-source.20260330-022725.json`, `/mnt/user/appdata/litellm/config.yaml`, `/mnt/user/appdata/litellm/config.yaml.bak`, `/mnt/user/appdata/litellm/config.yaml.bak-20260318-2354`, `/mnt/user/appdata/litellm/config.yaml.bak-20260319-0936`, `/mnt/user/appdata/litellm/config.yaml.bak-tier24`, `/mnt/user/appdata/litellm/config.yaml.bak.1344`, `/mnt/user/appdata/litellm/config.yaml.bak.1772921405`, `/mnt/user/appdata/litellm/config.yaml.bak.1773047728`, `/mnt/user/appdata/litellm/config.yaml.bak.1773469196`, `/mnt/user/appdata/litellm/config.yaml.bak.1773546264`, `/mnt/user/appdata/litellm/config.yaml.broken`, `/mnt/user/appdata/litellm/config.yaml.pre-reroute`

## Auth-Failed Provider Lanes

| Provider | Served alias | Missing env names | Latest auth failure | Next live action |
| --- | --- | --- | --- | --- |
| `anthropic_api` | `claude` | `ANTHROPIC_API_KEY` | `2026-03-30T09:00:02Z` | Restore `ANTHROPIC_API_KEY` in the managed VAULT secret source, recreate or redeploy `litellm`, then re-probe served model `claude`. |
| `dashscope_qwen_api` | `qwen-max` | `DASHSCOPE_API_KEY` | `2026-03-30T09:00:03Z` | Restore `DASHSCOPE_API_KEY` in the managed VAULT secret source, recreate or redeploy `litellm`, then re-probe served model `qwen-max`. |
| `google_gemini_api` | `gemini` | `GEMINI_API_KEY`, `GOOGLE_API_KEY` | `2026-03-30T09:00:06Z` | Restore `GEMINI_API_KEY`, `GOOGLE_API_KEY` in the managed VAULT secret source, recreate or redeploy `litellm`, then re-probe served model `gemini`. |
| `moonshot_api` | `kimi-k2.5` | `MOONSHOT_API_KEY` | `2026-03-30T09:00:06Z` | Inspect the latest auth failure for served model `kimi-k2.5` and reconcile `Moonshot API` on VAULT. Check `MOONSHOT_API_KEY` while reconciling the auth path. |
| `openai_api` | `gpt` | none | `2026-03-30T09:00:06Z` | Rotate `OPENAI_API_KEY` in the managed VAULT secret source, recreate or redeploy `litellm`, then re-probe served model `gpt`. |
| `openrouter_api` | `openrouter` | `OPENROUTER_API_KEY` | `2026-03-30T09:00:07Z` | Verify the upstream auth mode for served model `openrouter` before re-probing `OpenRouter API`. Ensure `OPENROUTER_API_KEY` is delivered to `litellm`. |
| `zai_api` | `glm-4.7` | `ZAI_API_KEY` | `2026-03-30T09:00:08Z` | Inspect the latest auth failure for served model `glm-4.7` and reconcile `Z.ai API` on VAULT. Check `ZAI_API_KEY` while reconciling the auth path. |

## Partial Contract Gaps Without Current Auth Failure

| Provider | Served alias | Present env names | Missing env names | Current posture | Latest verification |
| --- | --- | --- | --- | --- | --- |
| `mistral_codestral_api` | `codestral` | `CODESTRAL_API_KEY` | `MISTRAL_API_KEY` | `vault_provider_specific_api_observed` | `2026-03-30T09:00:06Z` |

## Already Proven Provider Lanes

| Provider | Served alias | Present env names | Latest proof |
| --- | --- | --- | --- |
| `deepseek_api` | `deepseek` | `DEEPSEEK_API_KEY` | `2026-03-30T09:00:06Z` |
| `mistral_codestral_api` | `codestral` | `CODESTRAL_API_KEY` | `2026-03-30T09:00:06Z` |
| `venice_api` | `venice-uncensored` | `VENICE_API_KEY` | `2026-03-30T09:00:07Z` |

## Approved Maintenance Sequence

1. Refresh the live env audit and confirm the current missing env-name set before touching VAULT runtime state.
2. Use the `Auth-Failed Provider Lanes` table to limit changes to the exact missing provider env names instead of changing unrelated LiteLLM settings.
3. Back up the live `litellm` container metadata and the current config bind-mount file before editing the runtime-managed env surface.
4. Add or restore only the missing provider env names in the managed VAULT secret source. Do not print values to shell history or tracked files.
5. Recreate or redeploy only the `litellm` container so the updated env set is applied. Use `docker restart litellm` only when the config file changed and the env set did not.
6. Re-run the env audit, provider-specific probe, truth collector, and generated reports so the provider and secret-surface reports reflect the new posture immediately.

## Backup Commands

```powershell
python scripts/vault-ssh.py "mkdir -p /mnt/user/appdata/litellm/backups"
python scripts/vault-ssh.py "docker inspect litellm > /mnt/user/appdata/litellm/backups/litellm.inspect.$(date +%Y%m%d-%H%M%S).json"
python scripts/vault-ssh.py "cp /mnt/user/appdata/litellm/config.yaml /mnt/user/appdata/litellm/backups/config.yaml.$(date +%Y%m%d-%H%M%S).bak"
```

## Read-Only Verification Commands

```powershell
python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json
python scripts/probe_provider_usage_evidence.py --all-vault-proxy
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --report providers --report secret_surfaces --report vault_litellm_repair_packet
python scripts/validate_platform_contract.py
```
