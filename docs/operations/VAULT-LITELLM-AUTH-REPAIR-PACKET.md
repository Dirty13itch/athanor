# VAULT LiteLLM Auth Repair Packet

Generated from `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/provider-catalog.json`, and the cached VAULT env-audit plus provider-usage artifacts by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

This packet is the repo-safe execution guide for an approved VAULT LiteLLM provider-auth maintenance window. It scopes the live work to the `litellm` container env surface only and keeps runtime mutation approval-gated.

- Credential surface version: `2026-04-16.1`
- Provider catalog version: `2026-04-16.3`
- Cached truth snapshot: `2026-04-17T04:12:52.397591+00:00`
- Cached env audit: `2026-04-17T04:12:01Z`
- Surface id: `vault-litellm-container-env`
- Host: `vault`
- Runtime owner surface: `standalone_docker_container`
- Container: `litellm`
- Container image: ``
- Restart policy: ``
- Env-change boundary: `container_recreate_or_redeploy`
- Config-only boundary: `docker_restart_litellm`
- Launch command: `unknown`
- Managed source matches: docker template none, compose manager none
- docker.config.json template mapping: `none`
- container-watchdog monitors litellm: `false`
- Boot-config references: none
- Detailed runbook: [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md)
- Companion reports: [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md), [SECRET-SURFACE-REPORT.md](/C:/Athanor/docs/operations/SECRET-SURFACE-REPORT.md)

## Current Runtime Truth

- Container envs present: none
- Container envs missing: `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Config-referenced envs present at runtime: none
- Config-referenced envs missing at runtime: none
- Host shell envs present (informational snapshot only; not the LiteLLM delivery contract): none
- Host shell envs missing (informational snapshot only; not a blocking delivery contract by itself): `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Runtime appdata files: none
- Historical inspect backups: none

## Auth-Failed Provider Lanes

| Provider | Served alias | Failure class | Present env names | Missing env names | Latest auth failure | Next live action |
| --- | --- | --- | --- | --- | --- | --- |
| `dashscope_qwen_api` | `qwen-max` | `auth_surface_mismatch` | none | `DASHSCOPE_API_KEY` | `2026-04-16T14:43:42Z` | Reconcile the actual VAULT credential-delivery path for served model `qwen-max` before rotating secrets blindly. The env audit still marks `DASHSCOPE_API_KEY` as missing, but the latest upstream auth failure shows a bad or expired credential is reaching `DashScope Qwen API`. Inspect alternate secret-delivery surfaces or stale runtime state, then recreate or redeploy `litellm` and re-probe. |
| `google_gemini_api` | `gemini` | `auth_surface_mismatch` | `GEMINI_API_KEY`, `GOOGLE_API_KEY` | `GEMINI_API_KEY`, `GOOGLE_API_KEY` | `2026-04-16T14:43:42Z` | Reconcile the actual VAULT credential-delivery path for served model `gemini` before rotating secrets blindly. The env audit still marks `GEMINI_API_KEY`, `GOOGLE_API_KEY` as missing, but the latest upstream auth failure shows a bad or expired credential is reaching `Gemini API`. Inspect alternate secret-delivery surfaces or stale runtime state, then recreate or redeploy `litellm` and re-probe. |
| `openai_api` | `gpt` | `auth_surface_mismatch` | `OPENAI_API_KEY` | `OPENAI_API_KEY` | `2026-04-16T14:43:43Z` | Reconcile the actual VAULT credential-delivery path for served model `gpt` before rotating secrets blindly. The env audit still marks `OPENAI_API_KEY` as missing, but the latest upstream auth failure shows a bad or expired credential is reaching `OpenAI API`. Inspect alternate secret-delivery surfaces or stale runtime state, then recreate or redeploy `litellm` and re-probe. |
| `openrouter_api` | `openrouter` | `auth_surface_mismatch` | `OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` | `2026-04-16T14:43:43Z` | Reconcile the actual VAULT credential-delivery path for served model `openrouter` before rotating secrets blindly. The env audit still marks `OPENROUTER_API_KEY` as missing, but the latest upstream auth failure shows a bad or expired credential is reaching `OpenRouter API`. Inspect alternate secret-delivery surfaces or stale runtime state, then recreate or redeploy `litellm` and re-probe. |

Current snapshot note: active VAULT auth failures are presently classified as `auth_surface_mismatch`. Treat these as the live remediation buckets for this snapshot and refresh the env audit plus provider probe together after each repair.

## Partial Contract Gaps Without Current Auth Failure

| Provider | Served alias | Present env names | Missing env names | Current posture | Latest verification |
| --- | --- | --- | --- | --- | --- |
| `anthropic_api` | `claude` | none | `ANTHROPIC_API_KEY` | `vault_provider_specific_request_failed` | `2026-04-16T14:43:41Z` |
| `deepseek_api` | `deepseek` | none | `DEEPSEEK_API_KEY` | `vault_provider_specific_api_observed` | `2026-04-16T14:43:42Z` |
| `mistral_codestral_api` | `codestral` | none | `CODESTRAL_API_KEY`, `MISTRAL_API_KEY` | `vault_provider_specific_api_observed` | `2026-04-16T14:43:42Z` |
| `moonshot_api` | `kimi-k2.5` | none | `MOONSHOT_API_KEY` | `vault_provider_specific_api_observed` | `2026-04-16T14:43:42Z` |
| `venice_api` | `venice-uncensored` | none | `VENICE_API_KEY` | `vault_provider_specific_request_failed` | `2026-04-16T14:43:43Z` |
| `zai_api` | `glm-4.7` | none | `ZAI_API_KEY` | `vault_provider_specific_api_observed` | `2026-04-16T14:43:43Z` |

Current snapshot note: `moonshot_api` is a non-blocking direct-env gap while the served `kimi-k2.5` alias remains provider-observed through VAULT LiteLLM.

## Already Proven Provider Lanes

| Provider | Served alias | Present env names | Latest proof |
| --- | --- | --- | --- |
| `deepseek_api` | `deepseek` | none | `2026-04-16T14:43:42Z` |
| `mistral_codestral_api` | `codestral` | none | `2026-04-16T14:43:42Z` |
| `moonshot_api` | `kimi-k2.5` | none | `2026-04-16T14:43:42Z` |
| `zai_api` | `glm-4.7` | none | `2026-04-16T14:43:43Z` |

## Approved Maintenance Sequence

1. Refresh the live env audit and confirm the current missing env-name set before touching VAULT runtime state.
2. Use the `Auth-Failed Provider Lanes` table to classify each broken lane before changing runtime. The current snapshot can legitimately include `missing_required_env`, `present_key_invalid`, `auth_surface_mismatch`, or `auth_mode_mismatch` depending on how the probe and env audit line up.
3. Back up the live `litellm` container metadata and the current config bind-mount file before editing the runtime-managed env surface.
4. For `missing_required_env`, add or restore only the missing provider env names in the managed VAULT secret source. Do not print values to shell history or tracked files.
5. For `present_key_invalid`, rotate or correct the already-present provider env names instead of widening the env surface.
6. For `auth_mode_mismatch`, verify the upstream auth mode or alias contract before changing secrets, and only redeploy if the chosen auth path requires a config or env update.
7. Recreate or redeploy only the `litellm` container when the env set or config actually changed. Use `docker restart litellm` only when the config file changed and the env set did not.
8. Re-run the env audit, provider-specific probe, truth collector, and generated reports so the provider and secret-surface reports reflect the new posture immediately.

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
