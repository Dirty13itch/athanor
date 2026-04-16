# ADR-012: LiteLLM Proxy for Model Routing

## Status

**Accepted** — Deployed on VAULT:4000 (Session 8, 2026-02-24). Config path: `/mnt/user/appdata/litellm/config.yaml`.

## Context

Athanor runs multiple vLLM instances across nodes with different models. Consumers (agents, dashboard, Open WebUI, external apps) currently connect directly to specific vLLM endpoints. This creates tight coupling between consumers and specific model deployments.

The architecture decision (see VISION.md) mandates LiteLLM as the routing layer: all consumers go through LiteLLM, engine swap = config change.

## Decision

Deploy LiteLLM proxy as the single entry point for all LLM inference:

- **All consumers** connect to LiteLLM, never directly to vLLM
- **Model routing** handled by LiteLLM config (model name → backend endpoint)
- **Fallback chains** — local model → cloud model when local is overloaded or unavailable
- **Cloud-enhanced, local-sovereign** — cloud APIs available through LiteLLM when needed, local models are default

## Planned Configuration

```yaml
# litellm_config.yaml (planned)
model_list:
  - model_name: "reasoning"
    litellm_params:
      model: "openai/Qwen3-32B-AWQ"
      api_base: "http://192.168.1.244:8000/v1"
      api_key: "not-needed"

  - model_name: "fast"
    litellm_params:
      model: "openai/Qwen3-14B-AWQ"
      api_base: "http://192.168.1.225:8000/v1"
      api_key: "not-needed"

  - model_name: "reasoning"
    litellm_params:
      model: "anthropic/claude-sonnet-4-20250514"
      api_key: "os.environ/ANTHROPIC_API_KEY"
    # Cloud fallback — used when local is unavailable
```

## Deployment

- Deploy on VAULT (central, always-on)
- Single Docker container
- Port: 4000 (LiteLLM default)
- Config: `/opt/athanor/litellm/litellm_config.yaml`

## Prerequisites

- vLLM stable on both nodes (done)
- Agent framework updated to use LiteLLM endpoint instead of direct vLLM
- Dashboard updated to use LiteLLM endpoint
- Cloud API keys configured (optional, for fallback)

## Consequences

- Single endpoint for all model access
- Model swaps are config changes, not code changes
- Enables load balancing across nodes
- Enables cloud fallback without consumer changes
- Adds one hop of latency (minimal — LiteLLM is a thin proxy)
