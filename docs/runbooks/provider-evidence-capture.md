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

## Cost-unverified CLI lanes

1. Verify the current CLI is still installed on the expected host.
2. Check the operator-visible billing surface or current product page.
3. Keep the lane cost-unverified until the subscribed tier or flat-rate price is proven from a current operator-visible or runtime-visible source.
