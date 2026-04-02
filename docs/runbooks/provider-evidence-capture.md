# Provider Evidence Capture

Use this runbook when a weak provider lane needs provider-specific proof instead of generic proxy activity.

## Vault LiteLLM API lanes

1. Prefer the automated probe first: `python scripts/probe_provider_usage_evidence.py --provider-id <provider-id>`.
2. The probe uses the catalog-owned served model contract, not a guessed generic provider alias.
3. Treat `observed` as provider-specific proof, `auth_failed` as a real credential/runtime finding, and `not_supported` as catalog-vs-runtime drift that must be fixed before the lane is treated as active-api.
4. If the result is `auth_failed`, switch to [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md) before recording any manual override.
5. Use `python scripts/record_provider_usage_evidence.py ...` only for manual captures that cannot be produced through the automated probe path.
6. Add `--request-surface` and `--note` whenever the evidence came from a specific command, route, log path, or operator-only surface.
7. Regenerate truth reports after recording captures so the provider report reflects the new evidence and failure posture.

`reports/truth-inventory/provider-usage-evidence.json` is reserved for these VAULT LiteLLM proxy lanes. Do not overload it with CLI-only or supported-tool subscription evidence.

## Cost-unverified CLI lanes

1. Verify the current CLI is still installed on the expected host.
2. Check the operator-visible billing surface or current product page.
3. Keep the lane cost-unverified until the subscribed tier or flat-rate price is proven from a current operator-visible or runtime-visible source.
4. Record the proof by updating the provider's `evidence.billing` block in [provider-catalog.json](/C:/Athanor/config/automation-backbone/provider-catalog.json), then regenerate truth reports.

## Supported-tool subscription lanes

1. Use this lane for providers whose proof comes from a supported coding tool or IDE integration rather than the VAULT proxy.
2. Treat `provider-usage-evidence.json` as out of scope for this class; the artifact schema is request/model-centric and VAULT-proxy-only.
3. Verify the supported tool is present on the expected host and that the provider-specific integration actually works, not just that the generic tool is installed.
4. If the integration cannot be proven repo-safely, keep the lane explicitly demoted in routing policy and provider reports instead of marking it active from assumption.
5. Record positive proof by updating the provider's `evidence.tooling_probe`, `evidence.billing`, and any lane notes directly in [provider-catalog.json](/C:/Athanor/config/automation-backbone/provider-catalog.json), then regenerate truth reports.
