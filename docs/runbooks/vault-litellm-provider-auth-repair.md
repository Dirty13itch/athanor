# VAULT LiteLLM Provider Auth Repair

Source of truth: `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/provider-catalog.json`, `docs/operations/SECRET-SURFACE-REPORT.md`, `docs/operations/PROVIDER-CATALOG-REPORT.md`
Validated against registry version: `credential-surface-registry.json@2026-04-02.1`, `provider-catalog.json@2026-03-29.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: live env names and provider auth posture come from the generated audit artifact and reports; this runbook owns the operator sequence and must never record secret values.

---

Use this runbook when `scripts/probe_provider_usage_evidence.py` reports `vault_provider_specific_auth_failed` for VAULT LiteLLM API lanes.

Current runtime evidence should come from:
- `reports/truth-inventory/vault-litellm-env-audit.json`
- [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md)
- [SECRET-SURFACE-REPORT.md](/C:/Athanor/docs/operations/SECRET-SURFACE-REPORT.md)
- [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md)

## Current runtime truth

- Container: `litellm`
- Host: `vault`
- Runtime surface: standalone Docker container with bind mount `/mnt/user/appdata/litellm/config.yaml:/app/config.yaml:ro`
- Env-change boundary: container recreate or redeploy
- Config-only boundary: `docker restart litellm`
- Runtime appdata path: `/mnt/user/appdata/litellm`
- Source-location note: the 2026-03-29 read-only VAULT scan did not find a dockerMan template or host envfile that obviously owns this container by name, so treat the live container definition as the visible runtime authority until a managed source is identified.
- Template and registry parity for the provider env contract are validator-enforced; use the live env audit artifact to decide what is still missing at runtime.

## Latest env-name audit

- Refresh the live env audit first with `python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json`.
- Regenerate [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) if you need the current provider-by-provider missing-env checklist.
- Treat the generated audit artifact as the current list of present and missing container env names.
- Do not hand-maintain dated present or missing env-name lists in this runbook.

## Repair packet

1. Refresh `reports/truth-inventory/vault-litellm-env-audit.json` and confirm which env names are still missing by contract.
2. Back up the current `docker inspect litellm` metadata before touching the runtime-managed env surface.
3. Confirm the intended provider env vars exist in the managed VAULT LiteLLM secret source by name only; do not print values into shell history or tracked files.
4. Add or restore only the missing env vars in the runtime-managed container surface for `litellm`.
5. Keep the config bind mount unchanged unless the served model ids themselves need repair.
6. Recreate or redeploy the `litellm` container so the updated env set is applied.
7. Use `docker restart litellm` only when the config file changed but the env set did not.
8. Re-run `python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json`.
9. Re-run `python scripts/probe_provider_usage_evidence.py --all-vault-proxy`.
10. Regenerate the truth reports so the provider catalog report and secret-surface report reflect the new posture.

## Read-only verification commands

From `C:\Athanor`:

```powershell
python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json
python scripts/probe_provider_usage_evidence.py --all-vault-proxy
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --report providers --report secret_surfaces --report vault_litellm_repair_packet
```

## Notes

- This runbook tracks env var names and runtime boundaries only. It must never record secret values.
- Successful provider-specific probes for `mistral_codestral_api`, `deepseek_api`, and `venice_api` already prove the current runtime surface works when the upstream env var is present.
- The remaining auth-failed lanes are a runtime credential-delivery problem first, not a missing-probe problem.
- Because no dockerMan template or host envfile source was identified by name during the 2026-03-29 read-only scan, any live repair pass should begin by backing up the current `docker inspect litellm` metadata before editing the runtime-managed env surface.
- The 2026-03-29 host-env check also showed the missing provider keys are absent from the VAULT shell env, so the live repair pass requires an actual secret-source update rather than only a container restart.
