# ATHANOR MASTER PLAN - STRATEGIC REFERENCE

> **Last updated:** 2026-03-27
> **Status:** Strategic reference only.
> **Live truth lives here:** `config/automation-backbone/`, `docs/operations/ATHANOR-OPERATING-SYSTEM.md`, `docs/operations/PROVIDER-CATALOG-REPORT.md`, `docs/operations/HARDWARE-REPORT.md`, `docs/operations/MODEL-DEPLOYMENT-REPORT.md`, `docs/SERVICES.md`, `docs/RECOVERY.md`, `STATUS.md`, and `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`.
> **Historical implementation snapshot:** `docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md`

---

## What Athanor Is

Athanor is a sovereign AI system for a solo operator. It combines:

- paid cloud subscriptions and API lanes
- local models and local hardware
- autonomous background agents
- operator-facing control surfaces
- strong privacy, sovereignty, and safety boundaries

The strategic posture remains:

- cloud-first with a local backbone
- routing at the operation level rather than the project level
- swappable models, providers, and tools behind stable contracts
- aggressive automation inside explicit safety rails

This document does not own live topology, deployed model IDs, provider pricing, reset windows, quota posture, or runtime service state.

## Operating Modes

### Interactive

The operator describes intent. The control plane chooses:

- the tool
- the provider or local lane
- the execution mode
- whether work should remain interactive or move into background execution

### Autonomous

The system can continue useful work while the operator is away, but only inside bounded safety and audit rules:

- durable task truth
- explicit operator-action envelopes for privileged mutations
- auditable accepted and denied outcomes
- presence-aware automation posture
- restart-safe recovery and bounded self-healing

## Governance Model

The long-term operating model is organized across seven domains:

1. `Compute`
   Model deployment, inference routing, GPU allocation, model proving and promotion.
2. `Storage`
   Data lifecycle, backups, retention, and archival posture.
3. `Services`
   Deployment, health, dependencies, and recovery behavior.
4. `Generation`
   Creative workflows, media pipelines, and autonomous execution lanes.
5. `Operations`
   Monitoring, alerting, economic governance, and operator presence handling.
6. `Security`
   Secrets, access control, content-policy routing, safety tiers, and approval posture.
7. `Knowledge`
   Memory, search, embeddings, RAG, documentation, and learned operational context.

The live implementation of those domains belongs to the registry-backed operating system, not this document.

## Stable Strategic Decisions

These are the durable decisions this document still owns:

- Athanor should choose tools and providers for the operator whenever practical.
- Resettable, flat-rate, and local lanes should be used intentionally rather than left idle.
- Premium interactive capacity should be protected from low-value async burn unless policy explicitly releases it.
- Sovereign, refusal-sensitive, private, and secret-bearing work remains local unless the active policy class explicitly allows a cloud lane.
- Adult and NSFW work is a valid first-class workload and should be handled explicitly rather than treated as an exception.
- Runtime truth outranks planning-era narrative whenever they disagree.
- Aggressive deletion of stale truth is correct once a verified replacement exists.

## Current Truth Pointers

Use these sources instead of this file for live facts:

- **Authority model and operating state:** `STATUS.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`, `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- **Topology and service/runtime truth:** `config/automation-backbone/platform-topology.json`, `docs/SERVICES.md`
- **Hardware truth:** `config/automation-backbone/hardware-inventory.json`, `docs/operations/HARDWARE-REPORT.md`
- **Model deployment truth:** `config/automation-backbone/model-deployment-registry.json`, `docs/operations/MODEL-DEPLOYMENT-REPORT.md`
- **Provider and routing truth:** `config/automation-backbone/provider-catalog.json`, `config/automation-backbone/routing-taxonomy-map.json`, `docs/operations/PROVIDER-CATALOG-REPORT.md`, `projects/agents/config/subscription-routing-policy.yaml`
- **Recovery and evidence truth:** `docs/RECOVERY.md`, `audit/recovery/`, `audit/automation/`
- **Security and credential-delivery truth:** `docs/SECURITY-FOLLOWUPS.md`, `docs/runbooks/credential-rotation.md`, `config/automation-backbone/credential-surface-registry.json`

## Historical Notes

The March 2026 planning wave included detailed assumptions about:

- exact hardware counts and node roles
- active model placements and ports
- tool versions and subscription/product tiers
- provider pricing and reset windows
- free-tier API overflow lanes
- remote-access and deployment assumptions

Those details are intentionally no longer carried here because they drift too quickly and were starting to compete with the control plane.

Use the archived planning-era full snapshot for historical reasoning only:

- `docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md`

## Architectural Principles

1. Cloud-first with local backbone.
2. Routing at the operation level, not the project level.
3. Models, providers, and tools must be swappable without redesigning the system.
4. Quality, privacy, safety, and operator burden matter more than preserving an old routing preference.
5. Recovery, observability, and auditability are part of the product, not cleanup work.

---

This file is intentionally narrower now. If a fact needs to be current, measurable, or enforced, it belongs in the registry-backed control plane or the generated reports instead.
