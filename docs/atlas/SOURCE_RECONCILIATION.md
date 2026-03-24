# Atlas Source Reconciliation

This document explains which Athanor sources still own truth, which sources are synthesis layers, and which older documents are now reference-only. The goal is to stop conflicting documents from competing as equal authority.

## Decision Rule

When sources disagree, resolve them in this order:

1. Running code, route definitions, deployment manifests, and current config files
2. Current operational docs that still match repo and runtime evidence
3. Design docs and ADRs that explain intent and contracts
4. Tactical planning and build-queue documents
5. Older map documents and historical planning bundles

The atlas sits above those layers as the canonical cross-layer synthesis. It does not outrank code or live-defining config. It reconciles them.

## Canonical Atlas Layer

| Source | Classification | What it owns now | What it does not own |
| --- | --- | --- | --- |
| [`README.md`](./README.md) | canonical atlas index | authority model, atlas layout, status taxonomy, source anchors | detailed service, route, or endpoint truth |
| [`TOPOLOGY_ATLAS.md`](./TOPOLOGY_ATLAS.md) | canonical synthesized map | nodes, services, model lanes, stores, flows, deployment-source precedence | low-level deployment implementation details |
| [`RUNTIME_ATLAS.md`](./RUNTIME_ATLAS.md) | canonical synthesized map | agent roster, orchestration subsystems, task/workspace loops, subscription layer | source code internals beyond the mapped runtime surface |
| [`UI_ATLAS.md`](./UI_ATLAS.md) | canonical synthesized map | dashboard shell, route families, route-by-route inventory, shared consoles, dormant UI systems | component implementation details that belong in code |
| [`API_ATLAS.md`](./API_ATLAS.md) | canonical synthesized map | dashboard API families, agent-server boundary, consumer matrix, ownership | endpoint implementation logic |
| [`inventory/*.json`](./inventory/atlas-record.schema.json) | canonical machine-readable atlas | systematic inventory records that back the prose atlas | product-facing runtime contracts |

## Code and Config Sources That Still Own Truth

| Source | Classification | Current authority | Notes |
| --- | --- | --- | --- |
| `projects/dashboard/src/lib/navigation.ts` | canonical code source | dashboard route families, labels, and route inventory | UI atlas must stay synchronized with this file |
| `projects/dashboard/src/app/**` | canonical code source | mounted route pages, layouts, and Next.js API route handlers | strongest source for actual dashboard surface area |
| `projects/dashboard/src/features/**` | canonical code source | page-console ownership and route-specific behavior | used to map page modules and feature families |
| `projects/dashboard/src/components/**` | canonical code source | shell systems, shared widgets, dormant UI capability | code may exist without being mounted; atlas status tags handle that distinction |
| `projects/agents/src/athanor_agents/server.py` | canonical runtime code source | agent-server endpoint surface and agent roster | strongest source for runtime API shape |
| `projects/agents/src/athanor_agents/*.py` | canonical runtime code source | task engine, workspace, goals, notifications, subscriptions, memory, learning | runtime atlas should follow these modules when behavior changes |
| `ansible/` | deployment source | intended deployment shape when templates are current | not always the strongest source when service or project manifests match live better |
| `services/` | deployment source | node-scoped service manifests, especially for compute nodes | currently stronger than some Ansible roles for parts of FOUNDRY and WORKSHOP |
| `projects/*/docker-compose*` | deployment source | app-local deployment truth for dashboard, agents, and similar app surfaces | especially relevant when the project owns its own runtime stack |

## Current Supporting Docs

| Source | Classification | What truth it still owns | Reconciliation note |
| --- | --- | --- | --- |
| [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) | current operational spec | overall architecture, runtime responsibilities, flow descriptions | strongest prose source for system behavior when it matches code/runtime |
| [`../SERVICES.md`](../SERVICES.md) | current operational spec | node placement, model routing, and service location | strongest prose source for deployment topology short of manifests |
| [`../design/agent-contracts.md`](../design/agent-contracts.md) | design contract doc | agent roles, operating boundaries, and expectations | authoritative for intent, subordinate to live code for actual agent roster |
| [`../design/athanor-next.md`](../design/athanor-next.md) | strategic design doc | north-star design direction and strategic intent | not a topology or route source of truth |
| [`../design/command-center.md`](../design/command-center.md) | design doc | dashboard intent and operator-experience goals | subordinate to mounted dashboard code and route definitions |
| [`../../projects/dashboard/README.md`](../../projects/dashboard/README.md) | product support doc | dashboard architecture and local development context | useful support source, not the canonical UI map |
| [`../../projects/dashboard/docs/UI_AUDIT.md`](../../projects/dashboard/docs/UI_AUDIT.md) | support audit doc | route quality baseline and UI observations | useful for verification, not the main atlas |
| [`../BUILD-MANIFEST.md`](../BUILD-MANIFEST.md) | tactical queue | current execution priorities and historical build notes | must not be used as topology or secrets truth |

## Reconciled But Non-Canonical Map Docs

| Source | Classification | Still useful for | Why it is no longer canonical |
| --- | --- | --- | --- |
| [`../archive/planning-era/ATHANOR-MAP.md`](../archive/planning-era/ATHANOR-MAP.md) | legacy planning map | philosophy, earlier design synthesis, planning-era assumptions | mixes live facts, intentions, and sprint-era planning into one document |
| [`../archive/planning-era/ATHANOR-MAP-ADDENDUM.md`](../archive/planning-era/ATHANOR-MAP-ADDENDUM.md) | legacy planning addendum | point-in-time corrections and late-session clarifications | tied to a specific planning session, not durable repo truth |
| [`../hardware/ATHANOR-SYSTEM-MAP.md`](../hardware/ATHANOR-SYSTEM-MAP.md) | hardware reference | rack, ports, hardware inventory, physical context | valuable hardware detail, but not the current system map |
| [`../hardware/COMPLETE-SYSTEM-BREAKDOWN.md`](../hardware/COMPLETE-SYSTEM-BREAKDOWN.md) | exhaustive hardware reference | deep physical inventory and rack-level documentation | too hardware-heavy to serve as the primary cross-layer map |

## Reconciliation Rules For Known Divergence Zones

| Divergence zone | Strongest source today | How the atlas reads it |
| --- | --- | --- |
| Dashboard route surface | route files plus `navigation.ts` | mounted route definitions win over older UI planning docs |
| Dormant UI capability like lens, bottom-nav, and ambient widgets | component code plus root shell wiring | code exists, but atlas tags these `implemented_not_live` unless mounted |
| Agent roster and runtime endpoints | `server.py` plus runtime modules | runtime code wins over older contract docs when they disagree |
| FOUNDRY and WORKSHOP deployment layout | `services/` and project-local manifests when they match live better | atlas records Ansible drift instead of pretending stale templates are authoritative |
| VAULT LiteLLM and monitoring drift | live-config evidence plus repo-side vault roles | live files are evidence; surviving truth must be promoted back into repo-owned deployment sources |

## How To Update The Atlas

1. Change the real source first: code, route definition, operational doc, or deployment manifest.
2. Update the relevant atlas prose doc and inventory JSON so the synthesis matches the real source.
3. Run `python scripts/validate-atlas.py`.
4. Run `python scripts/check-doc-refs.py docs/atlas`.
5. If a formerly important document lost authority, add or update its atlas note instead of deleting its historical value.

## Reading Guidance

- Use the atlas when you need the full current system shape.
- Drop into code and deployment files when you need exact implementation truth.
- Use operational and design docs for intent and narrative context.
- Use legacy map docs only when you need lineage, hardware depth, or planning history.
