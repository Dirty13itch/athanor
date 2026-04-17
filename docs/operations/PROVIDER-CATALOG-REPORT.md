# Provider Catalog Report

Generated from `config/automation-backbone/provider-catalog.json` and `config/automation-backbone/subscription-burn-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-16.3`
- Burn registry version: `2026-04-12.1`
- Providers tracked: `16`
- Burn-enabled lanes tracked: `4`
- Burn schedule windows tracked: `4`
- Official verification date: `2026-03-28`
- Provider usage captures tracked: `10`

| State class | Count |
| --- | --- |
| `active-api` | 10 |
| `active-burn` | 5 |
| `active-routing` | 6 |
| `configured-unused` | 10 |

## Evidence Posture

| Evidence posture | Count |
| --- | --- |
| `live_burn_observed` | 4 |
| `live_burn_observed_cost_unverified` | 1 |
| `local_runtime_available` | 1 |
| `vault_provider_specific_api_observed` | 4 |
| `vault_provider_specific_auth_failed` | 4 |
| `vault_provider_specific_request_failed` | 2 |

## Auth Failure Classes

| Failure class | Count |
| --- | --- |
| `auth_surface_mismatch` | 4 |

## Verification Queue

| Provider | Evidence posture | Verification class | Pricing truth | Next verification |
| --- | --- | --- | --- | --- |
| `moonshot_kimi` | `live_burn_observed_cost_unverified` | `pricing_verification_missing` | `flat_rate_unverified` | Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source. |
| `anthropic_api` | `vault_provider_specific_request_failed` | `routine_or_none` | `metered_api` | Debug the failed provider-specific VAULT LiteLLM request for served model `claude`. |
| `dashscope_qwen_api` | `vault_provider_specific_auth_failed` | `auth_surface_mismatch` | `metered_api` | Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `DashScope Qwen API` on VAULT, then re-probe served model `qwen-max`. Missing env names: `DASHSCOPE_API_KEY`. |
| `google_gemini_api` | `vault_provider_specific_auth_failed` | `auth_surface_mismatch` | `metered_api` | Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `Gemini API` on VAULT, then re-probe served model `gemini`. Missing env names: `GEMINI_API_KEY`, `GOOGLE_API_KEY`. |
| `openai_api` | `vault_provider_specific_auth_failed` | `auth_surface_mismatch` | `metered_api` | Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenAI API` on VAULT, then re-probe served model `gpt`. Missing env names: `OPENAI_API_KEY`. |
| `openrouter_api` | `vault_provider_specific_auth_failed` | `auth_surface_mismatch` | `metered_api` | Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenRouter API` on VAULT, then re-probe served model `openrouter`. Missing env names: `OPENROUTER_API_KEY`. |
| `venice_api` | `vault_provider_specific_request_failed` | `routine_or_none` | `metered_api` | Debug the failed provider-specific VAULT LiteLLM request for served model `venice-uncensored`. |
| `zai_glm_coding` | `live_burn_observed` | `routine_or_none` | `flat_rate_unverified` | Keep GLM Coding Plan in ordinary routing while refreshing supported-tool evidence on DESK or DEV. |

## Providers

| Provider | Category | Access | States | Burn lane | Monthly cost | Pricing status | Evidence posture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `athanor_local` | local | local | `active-routing` | none | $0 | not_applicable | local_runtime_available |
| `anthropic_claude_code` | subscription | cli | `active-routing`, `active-burn` | `claude_max` | $200 | official_verified | live_burn_observed |
| `openai_codex` | subscription | cli | `active-routing`, `active-burn` | `chatgpt_pro` | $200 | official_verified | live_burn_observed |
| `google_gemini` | subscription | cli | `active-routing`, `active-burn` | `gemini_advanced` | $20 | official_verified | live_burn_observed |
| `moonshot_kimi` | subscription | cli | `active-routing`, `active-burn` | `kimi_allegretto` | unverified or metered | official-source-present-cost-unverified | live_burn_observed_cost_unverified |
| `zai_glm_coding` | subscription | cli | `active-routing`, `active-burn` | none | unverified or metered | official-source-present-cost-unverified | live_burn_observed |
| `anthropic_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_request_failed |
| `openai_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_auth_failed |
| `mistral_codestral_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `google_gemini_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_auth_failed |
| `deepseek_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `moonshot_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `dashscope_qwen_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_auth_failed |
| `venice_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_request_failed |
| `zai_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `openrouter_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_auth_failed |

## Athanor Local (`athanor_local`)

- Product: Sovereign local cluster
- Pricing truth: `not_applicable`, `$0/mo`
- Execution modes: `local_runtime`
- State classes: `active-routing`
- Evidence posture: `local_runtime_available`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `foundry`, `workshop`, `dev`
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=False`, `api_configured=False`, `last_verified_at=2026-03-25T19:15:00Z`
- Evidence contract: none
- Tool evidence: none
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: none
- Env contracts: none
- CLI commands: none
- Notes: `Primary sovereign execution lane.`, `Use for private, refusal-sensitive, and local-first automation.`

## Claude Code (`anthropic_claude_code`)

- Product: Claude Max
- Pricing truth: `verified_flat_rate`, `$200/mo`
- Execution modes: `direct_cli`, `bridge_cli`, `handoff_bundle`
- State classes: `active-routing`, `active-burn`
- Evidence posture: `live_burn_observed`
- Burn lanes: `claude_max`
- Burn windows: `Window 1 - Morning`, `Window 2 - Midday`, `Window 3 - Evening`, `Window 4 - Overnight`
- Observed hosts: `desk`, `dev`
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=True`, `api_configured=True`, `last_verified_at=2026-03-25T19:15:00Z`
- Evidence contract: none
- Tool evidence: `desk:claude:installed 2.1.76`, `dev:claude:installed 2.1.77`
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [Claude Max plan](https://support.claude.com/en/articles/11049741-what-is-the-max-plan), [Claude plan chooser](https://support.claude.com/en/articles/11049762-choosing-a-claude-plan)
- Env contracts: `ANTHROPIC_API_KEY`
- CLI commands: `claude`
- Notes: `Primary frontier architecture and final-review lane.`

## Codex CLI (`openai_codex`)

- Product: ChatGPT Pro
- Pricing truth: `verified_flat_rate`, `$200/mo`
- Execution modes: `direct_cli`, `bridge_cli`, `handoff_bundle`
- State classes: `active-routing`, `active-burn`
- Evidence posture: `live_burn_observed`
- Burn lanes: `chatgpt_pro`
- Burn windows: `Window 2 - Midday`, `Window 4 - Overnight`
- Observed hosts: `desk`, `dev`
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=True`, `api_configured=True`, `last_verified_at=2026-03-25T19:15:00Z`
- Evidence contract: none
- Tool evidence: `desk:codex:installed 0.116.0`, `dev:codex:installed 0.116.0`, `desk-wsl:codex:installed 0.116.0`
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [ChatGPT Pro](https://help.openai.com/en/articles/9793128)
- Env contracts: `OPENAI_API_KEY`
- CLI commands: `codex`
- Notes: `Primary async cloud execution lane.`

## Gemini CLI (`google_gemini`)

- Product: Google AI Pro / Gemini CLI
- Pricing truth: `verified_flat_rate`, `$20/mo`
- Execution modes: `direct_cli`, `handoff_bundle`
- State classes: `active-routing`, `active-burn`
- Evidence posture: `live_burn_observed`
- Burn lanes: `gemini_advanced`
- Burn windows: `Window 1 - Morning`
- Observed hosts: `desk`, `dev`
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=True`, `api_configured=True`, `last_verified_at=2026-03-25T19:15:00Z`
- Evidence contract: none
- Tool evidence: `desk:gemini:installed 0.34.0`, `dev:gemini:installed 0.34.0`
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [Google AI plans](https://one.google.com/about/google-ai-plans/), [Gemini CLI README](https://github.com/google-gemini/gemini-cli), [Gemini API quota docs](https://ai.google.dev/gemini-api/docs/quota)
- Env contracts: `GEMINI_API_KEY`, `GOOGLE_API_KEY`
- CLI commands: `gemini`
- Notes: `Preferred large-context audit lane.`, `Official plan and CLI limits drift independently; measure actual usage separately from plan pricing.`

## Kimi Code (`moonshot_kimi`)

- Product: Kimi Membership / Kimi Code
- Pricing truth: `flat_rate_unverified`, `unverified or metered`
- Execution modes: `direct_cli`, `handoff_bundle`
- State classes: `active-routing`, `active-burn`
- Evidence posture: `live_burn_observed_cost_unverified`
- Burn lanes: `kimi_allegretto`
- Burn windows: `Window 1 - Morning`, `Window 3 - Evening`
- Observed hosts: `desk`, `dev`
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=True`, `api_configured=True`, `last_verified_at=2026-03-29T06:17:44Z`
- Evidence contract: `kind=cli_subscription`, `cli_status=installed`, `hosts=desk,dev`, `commands=kimi`, `billing_status=operator_visible_tier_unverified`, `pricing_scope=membership_included`, `quota_cycle=7_day_rolling`
- Tool evidence: `desk:kimi:installed 1.18.0`, `dev:kimi:installed 1.24.0`
- Next verification: Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.
- Verification steps: `Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.`, `Keep this lane cost-unverified until the billing tier is proven from a current runtime-visible or operator-visible surface.`
- Official sources: [Kimi Code docs](https://www.kimi.com/code/docs/en/), [Kimi Code membership benefits](https://www.kimi.com/code/docs/en/benefits.html)
- Env contracts: `MOONSHOT_API_KEY`, `KIMI_API_KEY`
- CLI commands: `kimi`
- Notes: `Official docs confirm Kimi Code benefits are included in Kimi Membership, refresh on a 7-day rolling cycle, and are limited to personal development use.`, `The public Kimi docs used here still do not publish the exact subscribed membership price for this lane.`, `The exact subscribed monthly tier still needs runtime billing verification.`, `Live CLI probes reconfirmed `kimi --version` on DESK and DEV during the 2026-03-29 verification pass.`

## Z.ai GLM Coding (`zai_glm_coding`)

- Product: GLM Coding Plan
- Pricing truth: `flat_rate_unverified`, `unverified or metered`
- Execution modes: `direct_cli`, `handoff_bundle`
- State classes: `active-routing`, `active-burn`
- Evidence posture: `live_burn_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: none
- Observed runtime: `routing_policy_enabled=True`, `active_burn_observed=True`, `api_configured=True`, `last_verified_at=2026-04-13T15:08:02Z`
- Evidence contract: `kind=coding_tool_subscription`, `tooling_status=supported_tools_present`, `hosts=desk,dev`, `supported_tools=claude,codex,gemini`, `integration_status=verified`, `billing_status=published_tiers_known_subscribed_tier_unverified`, `public_prices=lite:10,pro:30`
- Tool evidence: none
- Next verification: Keep GLM Coding Plan in ordinary routing while refreshing supported-tool evidence on DESK or DEV.
- Verification steps: `Keep GLM Coding Plan in ordinary routing while refreshing supported-tool evidence on DESK or DEV.`, `Record future supported-tool refreshes with `python C:/Athanor/scripts/record_supported_tool_usage.py --family-id glm_coding_plan --tool-name <tool> --request-surface <surface> ...` so quota-truth can stay activation-proven.`, `Verify which public GLM Coding Plan tier is actually subscribed before treating any published USD price as this lane's monthly cost.`, `If supported-tool evidence regresses, demote the lane back out of ordinary auto-routing.`
- Official sources: [Z.ai GLM-5 overview](https://docs.z.ai/guides/llm), [Z.ai devpack overview](https://docs.z.ai/devpack/overview), [Z.ai pricing](https://docs.z.ai/guides/overview/pricing)
- Env contracts: `ZAI_API_KEY`, `ZAI_CODING_API_KEY`
- CLI commands: `glm`, `zai`
- Notes: `Official Z.ai docs publish GLM Coding Plan floor prices starting at USD 10 per month for Lite and USD 30 per month for Pro.`, `The same docs describe 5-hour rolling and 7-day quota windows, and separate metered API pricing outside the coding plan.`, `Live routing is now enabled because supported-tool usage was observed through Codex on 2026-04-13.`, `Current activation posture is supported_tool_usage_observed, so the lane may participate in ordinary auto-routing while evidence stays fresh.`

## Anthropic API (`anthropic_api`)

- Product: Anthropic API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_request_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:41Z`, `provider_usage_capture_status=request_failed`, `provider_usage_capture_at=2026-04-16T14:43:41Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=claude`, `host=vault`, `preferred_model=claude`, `provider_specific_status=request_failed`, `capture_status=request_failed`, `captured_at=2026-04-16T14:43:41Z`, `requested_model=claude`, `matched_by=preferred_exact`
- Runtime env audit: missing `ANTHROPIC_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Debug the failed provider-specific VAULT LiteLLM request for served model `claude`.
- Verification steps: `Debug the failed provider-specific VAULT LiteLLM request for served model `claude`.`, `Capture one successful completion or demote the lane to configured-only if the request path is not actually usable.`
- Official sources: [Anthropic pricing](https://www.anthropic.com/pricing)
- Env contracts: `ANTHROPIC_API_KEY`
- CLI commands: none
- Notes: `The 2026-04-16 live VAULT provider probe hit `request_failed` on the `claude` alias because the fallback path reported cooling-down pressure instead of a fresh secret-delivery regression.`

## OpenAI API (`openai_api`)

- Product: OpenAI API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_auth_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:43Z`, `provider_usage_capture_status=auth_failed`, `provider_usage_capture_at=2026-04-16T14:43:43Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=gpt`, `host=vault`, `preferred_model=gpt`, `provider_specific_status=auth_failed`, `capture_status=auth_failed`, `captured_at=2026-04-16T14:43:43Z`, `requested_model=gpt`, `matched_by=preferred_exact`
- Runtime env audit: missing `OPENAI_API_KEY`, present `OPENAI_API_KEY`, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenAI API` on VAULT, then re-probe served model `gpt`. Missing env names: `OPENAI_API_KEY`.
- Verification steps: `Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenAI API` on VAULT, then re-probe served model `gpt`. Missing env names: `OPENAI_API_KEY`.`, `Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.`
- Official sources: [OpenAI API pricing](https://openai.com/api/pricing/)
- Env contracts: `OPENAI_API_KEY`
- CLI commands: none
- Notes: `Latest live VAULT provider probe classified this lane as auth_failed even though OPENAI_API_KEY is now present in the container env.`

## Codestral API (`mistral_codestral_api`)

- Product: Codestral API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-04-16T14:43:42Z`, `provider_usage_capture_status=observed`, `provider_usage_capture_at=2026-04-16T14:43:42Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=codestral`, `host=vault`, `preferred_model=codestral`, `provider_specific_status=observed`, `capture_status=observed`, `captured_at=2026-04-16T14:43:42Z`, `requested_model=codestral`, `response_model=codestral`, `matched_by=preferred_exact`
- Runtime env audit: missing `CODESTRAL_API_KEY`, `MISTRAL_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [Mistral pricing](https://mistral.ai/pricing)
- Env contracts: `MISTRAL_API_KEY`, `CODESTRAL_API_KEY`
- CLI commands: none
- Notes: `Codestral is currently provider-specific observed through the VAULT LiteLLM proxy.`, `MISTRAL_API_KEY is now present in the container env, so the remaining observed lane does not depend on a partial missing-env contract.`

## Gemini API (`google_gemini_api`)

- Product: Gemini API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_auth_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:42Z`, `provider_usage_capture_status=auth_failed`, `provider_usage_capture_at=2026-04-16T14:43:42Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=gemini`, `host=vault`, `preferred_model=gemini`, `provider_specific_status=auth_failed`, `capture_status=auth_failed`, `captured_at=2026-04-16T14:43:42Z`, `requested_model=gemini`, `matched_by=preferred_exact`
- Runtime env audit: missing `GEMINI_API_KEY`, `GOOGLE_API_KEY`, present `GEMINI_API_KEY`, `GOOGLE_API_KEY`, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `Gemini API` on VAULT, then re-probe served model `gemini`. Missing env names: `GEMINI_API_KEY`, `GOOGLE_API_KEY`.
- Verification steps: `Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `Gemini API` on VAULT, then re-probe served model `gemini`. Missing env names: `GEMINI_API_KEY`, `GOOGLE_API_KEY`.`, `Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.`
- Official sources: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing/), [Gemini API quota docs](https://ai.google.dev/gemini-api/docs/quota)
- Env contracts: `GOOGLE_API_KEY`, `GEMINI_API_KEY`
- CLI commands: none
- Notes: `Latest live VAULT provider probe now shows Gemini upstream returning explicit invalid-key errors while GEMINI_API_KEY and GOOGLE_API_KEY are both present in the container env.`, `Treat the current failure as a present-key validity problem first; only reopen auth-mode mismatch if a rotated or corrected key still fails on the same served alias.`

## DeepSeek API (`deepseek_api`)

- Product: DeepSeek API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-04-16T14:43:42Z`, `provider_usage_capture_status=observed`, `provider_usage_capture_at=2026-04-16T14:43:42Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=deepseek`, `host=vault`, `preferred_model=deepseek`, `provider_specific_status=observed`, `capture_status=observed`, `captured_at=2026-04-16T14:43:42Z`, `requested_model=deepseek`, `response_model=deepseek`, `matched_by=preferred_exact`
- Runtime env audit: missing `DEEPSEEK_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing)
- Env contracts: `DEEPSEEK_API_KEY`
- CLI commands: none
- Notes: `DeepSeek is configured as an API lane via LiteLLM.`, `Provider-specific completion proof is current through 2026-04-16.`

## Moonshot API (`moonshot_api`)

- Product: Moonshot API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-04-16T14:43:42Z`, `provider_usage_capture_status=observed`, `provider_usage_capture_at=2026-04-16T14:43:42Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=kimi-k2.5`, `host=vault`, `preferred_model=kimi-k2.5`, `provider_specific_status=observed`, `capture_status=observed`, `captured_at=2026-04-16T14:43:42Z`, `requested_model=kimi-k2.5`, `response_model=kimi-k2.5`, `matched_by=preferred_exact`
- Runtime env audit: missing `MOONSHOT_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [Moonshot API pricing update](https://platform.moonshot.ai/blog/posts/Kimi_API_Newsletter)
- Env contracts: `MOONSHOT_API_KEY`
- CLI commands: none
- Notes: `Moonshot still exposes public API pricing through a pricing-specific official post rather than a dedicated stable pricing reference page.`, `Latest live VAULT provider proof records successful `kimi-k2.5` completions, so the missing direct `MOONSHOT_API_KEY` env contract is tracked as optional cleanup until Athanor chooses to make the direct Moonshot lane authoritative again.`

## DashScope Qwen API (`dashscope_qwen_api`)

- Product: DashScope API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_auth_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:42Z`, `provider_usage_capture_status=auth_failed`, `provider_usage_capture_at=2026-04-16T14:43:42Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=qwen-max`, `host=vault`, `preferred_model=qwen-max`, `provider_specific_status=auth_failed`, `capture_status=auth_failed`, `captured_at=2026-04-16T14:43:42Z`, `requested_model=qwen-max`, `matched_by=preferred_exact`
- Runtime env audit: missing `DASHSCOPE_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `DashScope Qwen API` on VAULT, then re-probe served model `qwen-max`. Missing env names: `DASHSCOPE_API_KEY`.
- Verification steps: `Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `DashScope Qwen API` on VAULT, then re-probe served model `qwen-max`. Missing env names: `DASHSCOPE_API_KEY`.`, `Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.`
- Official sources: [Alibaba Model Studio pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- Env contracts: `DASHSCOPE_API_KEY`
- CLI commands: none
- Notes: `Official Model Studio pricing is published on the per-model list and can vary by deployment region.`, `Latest live VAULT provider probe classified this lane as auth_failed, and the current env audit shows `DASHSCOPE_API_KEY` absent from both container delivery and config-referenced resolution on the live surface.`

## Venice API (`venice_api`)

- Product: Venice API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_request_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:43Z`, `provider_usage_capture_status=request_failed`, `provider_usage_capture_at=2026-04-16T14:43:43Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=venice-uncensored`, `host=vault`, `preferred_model=venice-uncensored`, `provider_specific_status=request_failed`, `capture_status=request_failed`, `captured_at=2026-04-16T14:43:43Z`, `requested_model=venice-uncensored`, `matched_by=preferred_exact`
- Runtime env audit: missing `VENICE_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Debug the failed provider-specific VAULT LiteLLM request for served model `venice-uncensored`.
- Verification steps: `Debug the failed provider-specific VAULT LiteLLM request for served model `venice-uncensored`.`, `Capture one successful completion or demote the lane to configured-only if the request path is not actually usable.`
- Official sources: [Venice API pricing](https://docs.venice.ai/overview/pricing)
- Env contracts: `VENICE_API_KEY`
- CLI commands: none
- Notes: `Venice remains configured as an API lane.`, `Latest live VAULT provider probe ended in `request_failed` on 2026-04-16 because Venice reported insufficient balance, so keep the lane demoted until credits are restored and completion succeeds again.`

## Z.ai API (`zai_api`)

- Product: Z.ai API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-04-16T14:43:43Z`, `provider_usage_capture_status=observed`, `provider_usage_capture_at=2026-04-16T14:43:43Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=glm-4.7`, `host=vault`, `preferred_model=glm-4.7`, `provider_specific_status=observed`, `capture_status=observed`, `captured_at=2026-04-16T14:43:43Z`, `requested_model=glm-4.7`, `response_model=glm-4.7`, `matched_by=preferred_exact`
- Runtime env audit: missing `ZAI_API_KEY`, present none, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: No immediate verification gap recorded.
- Verification steps: `No immediate verification gap recorded.`
- Official sources: [Z.ai pricing](https://docs.z.ai/guides/overview/pricing)
- Env contracts: `ZAI_API_KEY`
- CLI commands: none
- Notes: `The 2026-04-16 live VAULT provider probe now succeeds through the `glm-4.7` alias after restoring `ZAI_API_KEY` to the running LiteLLM container.`

## OpenRouter API (`openrouter_api`)

- Product: OpenRouter API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_auth_failed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-04-16T14:43:43Z`, `provider_usage_capture_status=auth_failed`, `provider_usage_capture_at=2026-04-16T14:43:43Z`, `provider_usage_capture_source=vault-litellm-live-probe`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=openrouter`, `host=vault`, `preferred_model=openrouter`, `provider_specific_status=auth_failed`, `capture_status=auth_failed`, `captured_at=2026-04-16T14:43:43Z`, `requested_model=openrouter`, `matched_by=preferred_exact`
- Runtime env audit: missing `OPENROUTER_API_KEY`, present `OPENROUTER_API_KEY`, audit `2026-04-17T20:12:51Z`
- Tool evidence: none
- Next verification: Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenRouter API` on VAULT, then re-probe served model `openrouter`. Missing env names: `OPENROUTER_API_KEY`.
- Verification steps: `Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenRouter API` on VAULT, then re-probe served model `openrouter`. Missing env names: `OPENROUTER_API_KEY`.`, `Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.`
- Official sources: [OpenRouter pricing](https://openrouter.ai/pricing)
- Env contracts: `OPENROUTER_API_KEY`
- CLI commands: none
- Notes: `Official OpenRouter pricing is pay-as-you-go and states there is no markup over listed provider model prices.`, `Latest live VAULT provider probe still classified this lane as auth_failed after OPENROUTER_API_KEY was restored, so the remaining issue is upstream auth mode or credential validity rather than pure env absence.`
