---
name: delegate
description: Auto-route tasks to the optimal tool, model, and subscription. Registry-backed provider and model truth only. Content governance enforced.
triggers:
  - "delegate"
  - "local model"
  - "offload"
  - "route"
  - "which tool"
---

# Smart Task Routing

Automatically pick the best tool, model, and subscription for any task. The user never decides manually.

## Task: $ARGUMENTS

## Step 1: Content Classification

| Class | Route | Examples |
|-------|-------|---------|
| cloud_safe | Any tool/sub | Open-source code, docs, public data |
| private_but_cloud_allowed | Trusted cloud or local | Business data, client info |
| hybrid_abstractable | Cloud sees structure only, raw stays local | Sensitive designs |
| refusal_sensitive | LOCAL ONLY (JOSIEFIED/Dolphin) | NSFW, adult content, EoBQ |
| sovereign_only | LOCAL ONLY | Pen testing, credentials, hacking |

If refusal_sensitive or sovereign_only → skip to Step 3 (local routing).

## Step 2: Cloud Subscription Routing (follow current registry truth)

Do not route from a hardcoded subscription table. Use the current truth sources:

- Provider inventory and confidence: `config/automation-backbone/provider-catalog.json`
- Subscription and provider routing policy: `projects/agents/config/subscription-routing-policy.yaml`
- Operator-facing provider evidence: `docs/operations/PROVIDER-CATALOG-REPORT.md`

Choose the lowest-cost lane that still matches the task, current confidence, and live availability. Keep `refusal_sensitive` and `sovereign_only` work off cloud lanes even if a provider looks healthy.

## Step 3: Local Model Routing ($0, unlimited)

Do not route from stale endpoint tables. Use the current truth sources:

- Local model deployments: `config/automation-backbone/model-deployment-registry.json`
- Operator-facing local model summary: `docs/operations/MODEL-DEPLOYMENT-REPORT.md`
- Hardware capability and ownership: `config/automation-backbone/hardware-inventory.json`

Keep `refusal_sensitive` and `sovereign_only` work local-only. Choose the local lane that matches the task class and current deployment status.

## Step 4: Autonomous Agent Routing

For background or autonomous tasks, route through the current live control-plane surfaces and agent roster. Do not rely on archived MCP command examples or stale local endpoint notes. Use the active operator and routing truth in the current registries and reports before delegating work.

## Quality Gate (always)

Review all delegated output before accepting. Check correctness, style, security, completeness, and that the chosen provider or model lane still matches the current registry-backed truth.
