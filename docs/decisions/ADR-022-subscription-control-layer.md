# ADR-022: Subscription Control Layer

**Date:** 2026-03-11
**Status:** Accepted
**Deciders:** Shaun, Claude

## Context

Athanor already has a canonical local inference contract: all application and
agent inference flows through LiteLLM on VAULT and then into the local vLLM
stack on Foundry, Workshop, and DEV.

What Athanor does not have is a canonical way to use cloud and subscription
capacity. Anthropic, OpenAI, Google, Moonshot, and Z.ai are currently best
understood as disconnected operator tools rather than a managed system layer.
That creates four problems:

1. Local agents cannot request outside capacity through policy.
2. Premium subscription usage is not deliberately reserved or harvested.
3. Privacy decisions are left to ad hoc human judgment at call time.
4. There is no local ledger of observed throttling, resets, or useful capacity.

## Decision

Introduce a **subscription control layer** as a brokered provider plane above
the local LiteLLM model layer.

The rule is:

- **LiteLLM remains the canonical local inference contract**
- **subscription-backed tooling is controlled through execution leases**
- **local agents request policy, not vendors**

Initial implementation lives in the agent platform:

- policy file: `projects/agents/config/subscription-routing-policy.yaml`
- broker module: `projects/agents/src/athanor_agents/subscriptions.py`
- API surface: `/v1/subscriptions/*`
- first integrated agents: `coding-agent`, `research-agent`

## Rationale

1. **Separate local inference from provider control.** LiteLLM is the right
   local routing edge, but it is not a complete control plane for subscription
   coding tools.
2. **Use policy before automation.** The first slice should issue auditable
   leases and record outcomes before it tries to directly execute vendor CLI
   flows.
3. **Preserve premium interactive capacity.** Claude Code and similar premium
   lanes should not be consumed by low-value automation when cheaper or free
   lanes fit.
4. **Keep sensitive work local by default.** Privacy-sensitive tasks should
   stay on Athanor unless policy explicitly allows cloud escalation.
5. **Track observed limits, not marketing claims.** Provider quotas drift over
   time and by plan. Athanor should record effective capacity locally.

## Implementation

### Phase 1: Lease issuance and observability

- YAML policy loaded from repo config
- Lease issuance endpoint
- Lease outcome endpoint
- Redis-backed lease and provider event ledger
- Coding and Research agents gain `request_execution_lease`
- Background tasks for those agents get a lease attached automatically

### Phase 2: Human and dashboard visibility

- surface lease decisions in Command Center
- expose per-provider observed throttle/reset history
- add daily quota-harvesting jobs for low-risk backlog work

### Phase 3: Adapter execution

- optional provider adapters for Codex, Gemini CLI, Kimi Code, GLM coding
- handoff bundle generation when a lane is approved but not directly callable
- richer policy around spend ceilings and async execution windows

## Consequences

### Positive

- Local agents can now reason about off-cluster execution through policy.
- Premium subscriptions can be used deliberately instead of opportunistically.
- Privacy boundaries become explicit and machine-enforceable.
- Athanor gains an empirical provider-usage ledger for future automation.

### Negative

- Adds another control-plane surface to maintain.
- Requires policy hygiene as subscription mix changes.
- The first slice does not yet directly execute external coding clients.

## Guardrails

- Keep Home, Media, and Knowledge agents local-only unless policy says otherwise.
- Do not hardcode vendor quota numbers into the runtime.
- Do not allow raw provider credentials to leak into tracked docs or prompts.
- Treat lease issuance as advisory until adapter execution is mature and tested.
