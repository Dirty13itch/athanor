# Provider Catalog Report

Generated from `config/automation-backbone/provider-catalog.json` and `config/automation-backbone/subscription-burn-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-03-29.1`
- Burn registry version: `2026-03-28.1`
- Providers tracked: `16`
- Burn-enabled lanes tracked: `4`
- Burn schedule windows tracked: `4`
- Official verification date: `2026-03-28`
- Provider usage captures tracked: `0`

| State class | Count |
| --- | --- |
| `active-api` | 10 |
| `active-burn` | 4 |
| `active-routing` | 5 |
| `configured-unused` | 11 |

## Evidence Posture

| Evidence posture | Count |
| --- | --- |
| `live_burn_observed` | 3 |
| `live_burn_observed_cost_unverified` | 1 |
| `local_runtime_available` | 1 |
| `supported_tool_subscription_unverified` | 1 |
| `vault_provider_specific_api_observed` | 3 |
| `vault_proxy_active_no_provider_specific_evidence` | 7 |

## Verification Queue

| Provider | Evidence posture | Pricing truth | Next verification |
| --- | --- | --- | --- |
| `moonshot_kimi` | `live_burn_observed_cost_unverified` | `flat_rate_unverified` | Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source. |
| `zai_glm_coding` | `supported_tool_subscription_unverified` | `flat_rate_unverified` | Verify GLM Coding Plan execution through a supported coding tool on DESK or DEV before promoting `Z.ai GLM Coding` back into live routing. |
| `anthropic_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `claude` and record the timestamp. Current probe alias: `claude`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id anthropic_api`. |
| `dashscope_qwen_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `qwen-max` and record the timestamp. Current probe alias: `qwen-max`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id dashscope_qwen_api`. |
| `google_gemini_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `gemini` and record the timestamp. Current probe alias: `gemini`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id google_gemini_api`. |
| `moonshot_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `kimi-k2.5` and record the timestamp. Current probe alias: `kimi-k2.5`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id moonshot_api`. |
| `openai_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `gpt` and record the timestamp. Current probe alias: `gpt`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openai_api`. |
| `openrouter_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `openrouter` and record the timestamp. Current probe alias: `openrouter`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openrouter_api`. |
| `zai_api` | `vault_proxy_active_no_provider_specific_evidence` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `glm-4.7` and record the timestamp. Current probe alias: `glm-4.7`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id zai_api`. |
| `deepseek_api` | `vault_provider_specific_api_observed` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `deepseek` and record the timestamp. |
| `mistral_codestral_api` | `vault_provider_specific_api_observed` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM alias `codestral` and record the timestamp. |
| `venice_api` | `vault_provider_specific_api_observed` | `metered_api` | Run a provider-specific request through the VAULT LiteLLM served model `venice-uncensored` and record the timestamp. |

## Providers

| Provider | Category | Access | States | Burn lane | Monthly cost | Pricing status | Evidence posture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `athanor_local` | local | local | `active-routing` | none | $0 | not_applicable | local_runtime_available |
| `anthropic_claude_code` | subscription | cli | `active-routing`, `active-burn` | `claude_max` | $200 | official_verified | live_burn_observed |
| `openai_codex` | subscription | cli | `active-routing`, `active-burn` | `chatgpt_pro` | $200 | official_verified | live_burn_observed |
| `google_gemini` | subscription | cli | `active-routing`, `active-burn` | `gemini_advanced` | $20 | official_verified | live_burn_observed |
| `moonshot_kimi` | subscription | cli | `active-routing`, `active-burn` | `kimi_allegretto` | unverified or metered | official-source-present-cost-unverified | live_burn_observed_cost_unverified |
| `zai_glm_coding` | subscription | cli | `configured-unused` | none | unverified or metered | official-source-present-cost-unverified | supported_tool_subscription_unverified |
| `anthropic_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `openai_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `mistral_codestral_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `google_gemini_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `deepseek_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `moonshot_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `dashscope_qwen_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `venice_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_provider_specific_api_observed |
| `zai_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |
| `openrouter_api` | api | api | `active-api`, `configured-unused` | none | unverified or metered | metered | vault_proxy_active_no_provider_specific_evidence |

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
- Tool evidence: `desk:codex:installed 0.116.0`, `dev:codex:installed 0.116.0`
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
- State classes: `configured-unused`
- Evidence posture: `supported_tool_subscription_unverified`
- Burn lanes: none
- Burn windows: none
- Observed hosts: none
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `last_verified_at=2026-03-29T06:17:44Z`
- Evidence contract: `kind=coding_tool_subscription`, `tooling_status=supported_tools_present`, `hosts=desk,dev`, `supported_tools=claude,codex,gemini`, `integration_status=unverified`, `billing_status=published_tiers_known_subscribed_tier_unverified`, `public_prices=lite:10,pro:30`
- Tool evidence: none
- Next verification: Verify GLM Coding Plan execution through a supported coding tool on DESK or DEV before promoting `Z.ai GLM Coding` back into live routing.
- Verification steps: `Verify GLM Coding Plan execution through a supported coding tool on DESK or DEV before promoting `Z.ai GLM Coding` back into live routing.`, `Verify which public GLM Coding Plan tier is actually subscribed before treating any published USD price as this lane's monthly cost.`, `Until supported-tool integration is proven, keep this lane configured-unused and out of ordinary auto-routing.`
- Official sources: [Z.ai GLM-5 overview](https://docs.z.ai/guides/llm), [Z.ai devpack overview](https://docs.z.ai/devpack/overview), [Z.ai pricing](https://docs.z.ai/guides/overview/pricing)
- Env contracts: `ZAI_API_KEY`, `ZAI_CODING_API_KEY`
- CLI commands: `glm`, `zai`
- Notes: `Official Z.ai docs publish GLM Coding Plan floor prices starting at USD 10 per month for Lite and USD 30 per month for Pro.`, `The same docs describe 5-hour rolling and 7-day quota windows, and separate metered API pricing outside the coding plan.`, `Live routing remains disabled until a supported coding tool can prove GLM Coding Plan execution on DESK or DEV.`, `This lane was demoted out of live routing on 2026-03-28 until supported-tool integration evidence is restored.`

## Anthropic API (`anthropic_api`)

- Product: Anthropic API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=claude`, `host=vault`, `preferred_model=claude`, `provider_specific_status=pending`
- Runtime env audit: missing `ANTHROPIC_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `claude` and record the timestamp. Current probe alias: `claude`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id anthropic_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `claude` and record the timestamp. Current probe alias: `claude`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id anthropic_api`.`, `Capture evidence that the request exercised `Anthropic API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Anthropic pricing](https://www.anthropic.com/pricing)
- Env contracts: `ANTHROPIC_API_KEY`
- CLI commands: none
- Notes: none

## OpenAI API (`openai_api`)

- Product: OpenAI API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=gpt`, `host=vault`, `preferred_model=gpt`, `provider_specific_status=pending`
- Runtime env audit: missing none, present `OPENAI_API_KEY`, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `gpt` and record the timestamp. Current probe alias: `gpt`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openai_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `gpt` and record the timestamp. Current probe alias: `gpt`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openai_api`.`, `Capture evidence that the request exercised `OpenAI API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [OpenAI API pricing](https://openai.com/api/pricing/)
- Env contracts: `OPENAI_API_KEY`
- CLI commands: none
- Notes: none

## Codestral API (`mistral_codestral_api`)

- Product: Codestral API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-03-29T03:46:16Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=codestral`, `host=vault`, `preferred_model=codestral`, `provider_specific_status=observed`
- Runtime env audit: missing `MISTRAL_API_KEY`, present `CODESTRAL_API_KEY`, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM alias `codestral` and record the timestamp.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM alias `codestral` and record the timestamp.`, `Capture evidence that the request exercised `Codestral API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Mistral pricing](https://mistral.ai/pricing)
- Env contracts: `MISTRAL_API_KEY`, `CODESTRAL_API_KEY`
- CLI commands: none
- Notes: none

## Gemini API (`google_gemini_api`)

- Product: Gemini API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=gemini`, `host=vault`, `preferred_model=gemini`, `provider_specific_status=pending`
- Runtime env audit: missing `GEMINI_API_KEY`, `GOOGLE_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `gemini` and record the timestamp. Current probe alias: `gemini`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id google_gemini_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `gemini` and record the timestamp. Current probe alias: `gemini`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id google_gemini_api`.`, `Capture evidence that the request exercised `Gemini API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing/), [Gemini API quota docs](https://ai.google.dev/gemini-api/docs/quota)
- Env contracts: `GOOGLE_API_KEY`, `GEMINI_API_KEY`
- CLI commands: none
- Notes: none

## DeepSeek API (`deepseek_api`)

- Product: DeepSeek API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-03-29T03:46:16Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=deepseek`, `host=vault`, `preferred_model=deepseek`, `provider_specific_status=observed`
- Runtime env audit: missing none, present `DEEPSEEK_API_KEY`, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `deepseek` and record the timestamp.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `deepseek` and record the timestamp.`, `Capture evidence that the request exercised `DeepSeek API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing)
- Env contracts: `DEEPSEEK_API_KEY`
- CLI commands: none
- Notes: `DeepSeek is configured as an API lane via LiteLLM.`, `This catalog tracks the lane as configured but not recently observed in burn state.`

## Moonshot API (`moonshot_api`)

- Product: Moonshot API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=kimi-k2.5`, `host=vault`, `preferred_model=kimi-k2.5`, `provider_specific_status=pending`
- Runtime env audit: missing `MOONSHOT_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `kimi-k2.5` and record the timestamp. Current probe alias: `kimi-k2.5`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id moonshot_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `kimi-k2.5` and record the timestamp. Current probe alias: `kimi-k2.5`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id moonshot_api`.`, `Capture evidence that the request exercised `Moonshot API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Moonshot API pricing update](https://platform.moonshot.ai/blog/posts/Kimi_API_Newsletter)
- Env contracts: `MOONSHOT_API_KEY`
- CLI commands: none
- Notes: `Moonshot still exposes public API pricing through a pricing-specific official post rather than a dedicated stable pricing reference page.`

## DashScope Qwen API (`dashscope_qwen_api`)

- Product: DashScope API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=qwen-max`, `host=vault`, `preferred_model=qwen-max`, `provider_specific_status=pending`
- Runtime env audit: missing `DASHSCOPE_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `qwen-max` and record the timestamp. Current probe alias: `qwen-max`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id dashscope_qwen_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `qwen-max` and record the timestamp. Current probe alias: `qwen-max`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id dashscope_qwen_api`.`, `Capture evidence that the request exercised `DashScope Qwen API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Alibaba Model Studio pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- Env contracts: `DASHSCOPE_API_KEY`
- CLI commands: none
- Notes: `Official Model Studio pricing is published on the per-model list and can vary by deployment region.`

## Venice API (`venice_api`)

- Product: Venice API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_provider_specific_api_observed`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-03-29T03:46:17Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=venice-uncensored`, `host=vault`, `preferred_model=venice-uncensored`, `provider_specific_status=observed`
- Runtime env audit: missing none, present `VENICE_API_KEY`, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `venice-uncensored` and record the timestamp.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `venice-uncensored` and record the timestamp.`, `Capture evidence that the request exercised `Venice API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Venice API pricing](https://docs.venice.ai/overview/pricing)
- Env contracts: `VENICE_API_KEY`
- CLI commands: none
- Notes: `Venice remains configured as an API lane and still needs observed runtime usage evidence.`

## Z.ai API (`zai_api`)

- Product: Z.ai API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=glm-4.7`, `host=vault`, `preferred_model=glm-4.7`, `provider_specific_status=pending`
- Runtime env audit: missing `ZAI_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `glm-4.7` and record the timestamp. Current probe alias: `glm-4.7`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id zai_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `glm-4.7` and record the timestamp. Current probe alias: `glm-4.7`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id zai_api`.`, `Capture evidence that the request exercised `Z.ai API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [Z.ai pricing](https://docs.z.ai/guides/overview/pricing)
- Env contracts: `ZAI_API_KEY`
- CLI commands: none
- Notes: none

## OpenRouter API (`openrouter_api`)

- Product: OpenRouter API
- Pricing truth: `metered_api`, `unverified or metered`
- Execution modes: `litellm_proxy`
- State classes: `active-api`, `configured-unused`
- Evidence posture: `vault_proxy_active_no_provider_specific_evidence`
- Burn lanes: none
- Burn windows: none
- Observed hosts: `vault`
- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=False`, `last_verified_at=2026-03-28T06:00:00Z`
- Evidence contract: `kind=vault_litellm_proxy`, `alias=openrouter`, `host=vault`, `preferred_model=openrouter`, `provider_specific_status=pending`
- Runtime env audit: missing `OPENROUTER_API_KEY`, present none, audit `2026-03-31T00:12:36Z`
- Tool evidence: none
- Next verification: Run a provider-specific request through the VAULT LiteLLM served model `openrouter` and record the timestamp. Current probe alias: `openrouter`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openrouter_api`.
- Verification steps: `Run a provider-specific request through the VAULT LiteLLM served model `openrouter` and record the timestamp. Current probe alias: `openrouter`. Then record or refresh the proof with `python scripts/probe_provider_usage_evidence.py --provider-id openrouter_api`.`, `Capture evidence that the request exercised `OpenRouter API` upstream specifically, not just generic proxy activity.`, `If provider-specific evidence cannot be captured, demote the lane to configured-only.`
- Official sources: [OpenRouter pricing](https://openrouter.ai/pricing)
- Env contracts: `OPENROUTER_API_KEY`
- CLI commands: none
- Notes: `Official OpenRouter pricing is pay-as-you-go and states there is no markup over listed provider model prices.`
