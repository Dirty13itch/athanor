# Athanor Ecosystem System Bible

Do not edit manually.


## Scope

This appendix is exhaustive by subsystem. It exists to make every ecosystem domain explicit without overloading the daily execution spine.

## Cluster Substrate Inventory

| Node | Role | IP |
| --- | --- | --- |
| `DEV` | `ops_center` | `192.168.1.189` |
| `FOUNDRY` | `heavy_compute` | `192.168.1.244` |
| `WORKSHOP` | `creative_compute` | `192.168.1.225` |
| `VAULT` | `storage_observability` | `192.168.1.203` |
| `DESK` | `workstation` | `192.168.1.50` |

## Athanor core adopted system

- Owner: `C:/Athanor`
- State class: `adopted`
- Why it is part of the ecosystem: This is the adopted implementation and operator authority that all other ecosystem layers ultimately support or feed.
- Source of truth:
- `reports/truth-inventory/steady-state-status.json`
- `reports/truth-inventory/steady-state-live.md`
- `reports/truth-inventory/finish-scoreboard.json`
- `reports/ralph-loop/latest.json`
- `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- Current state: Core posture is `repo_safe_complete` with `active_closure`; live claim, queue posture, and packet inbox state are intentionally carried by the ignored live operator feed and machine JSON surfaces.
- Blockers: none
- Failure mode: If this layer drifts, the system loses authoritative state, operator visibility, and safe execution ordering.
- Next maturity move: Keep the steady-state control-plane pass green and reopen only on typed debt, packet, or validator evidence.
- Dependencies: cluster_and_host_substrate, external_providers_and_saas, artifact_and_evidence_systems, human_approval_and_decision_gates

## devstack forge

- Owner: `C:/athanor-devstack`
- State class: `proving`
- Why it is part of the ecosystem: Devstack owns concept, prototype, and proved capability work that directly determines what can graduate into Athanor next.
- Source of truth:
- `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`
- `C:/athanor-devstack/reports/master-atlas/latest.json`
- `C:/athanor-devstack/MASTER-PLAN.md`
- Current state: Turnover is `ready_for_low_touch_execution`; current top lane and packet drafting flow are carried live by the forge board and atlas surfaces.
- Blockers: Provider secret repair, LETTA_API_KEY, OpenHands substrate readiness
- Failure mode: If build truth is stale or overruns its boundary, shadow authority leaks into Athanor and pilot work becomes ambiguous.
- Next maturity move: Advance the next bounded promotion lane through proof, packet, and Athanor landing surfaces without leaking build truth into runtime truth.
- Dependencies: athanor_core_adopted_system, operator_local_systems, external_providers_and_saas, human_approval_and_decision_gates

## cluster and host substrate

- Owner: `FOUNDRY / WORKSHOP / VAULT / DEV / DESK`
- State class: `runtime`
- Why it is part of the ecosystem: Athanor only works if the nodes, runtime ownership, and host-specific constraints are current and governable.
- Source of truth:
- `config/automation-backbone/platform-topology.json`
- `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`
- `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- `reports/truth-inventory/capacity-telemetry.json`
- Current state: Topology tracks `5` nodes; atlas harvest posture is `open_harvest_window` and work-economy posture is `ready`.
- Blockers: OpenHands substrate readiness on DESK
- Failure mode: Host drift or ambiguous runtime ownership can reopen deployment debt and invalidate operator truth.
- Next maturity move: Keep runtime mutations packet-backed, preserve host-role clarity, and only widen pilot substrate work when a specific activation lane needs it.
- Dependencies: external_providers_and_saas, human_approval_and_decision_gates

## operator-local systems

- Owner: `C:/Users/Shaun/.codex and C:/Codex System Config`
- State class: `local_only`
- Why it is part of the ecosystem: The operator-local layer determines how Shaun sees and drives the system, especially on DESK and in Codex.
- Source of truth:
- `C:/Codex System Config/STATUS.md`
- `C:/Codex System Config/docs/CODEX-NEXT-STEPS.md`
- `C:/Users/Shaun/.codex/control/safe-surface-scope.md`
- `C:/Users/Shaun/.codex/control/safe-surface-policy.md`
- Current state: Codex System Config is the machine-level control plane, WSL-first execution is the default, and the safe-surface loop remains explicitly non-Athanor by policy.
- Blockers: none
- Failure mode: If local control surfaces drift, the user loses visibility and starts operating from stale or split control planes.
- Next maturity move: Keep worktree audits, WSL tooling parity, and machine-level control proof current without letting global defaults absorb repo-local truth.
- Dependencies: athanor_core_adopted_system, devstack_forge

## external providers and SaaS

- Owner: `External APIs, billing systems, and SaaS control planes`
- State class: `external`
- Why it is part of the ecosystem: Model routing, billing posture, gateway auth, and SaaS observability are external but can still block real work.
- Source of truth:
- `docs/operations/PROVIDER-CATALOG-REPORT.md`
- `reports/truth-inventory/provider-usage-evidence.json`
- `reports/truth-inventory/planned-subscription-evidence.json`
- `reports/truth-inventory/quota-truth.json`
- Current state: Provider evidence is explicit with `170` usage captures and `2` planned-subscription captures; optional elasticity maintenance remains externalized rather than core-blocking.
- Blockers: Provider secret repair
- Failure mode: If provider posture is implicit or stale, routing decisions and pilot readiness become misleading.
- Next maturity move: Keep provider proof current, rotate or repair keys only when a live lane or pilot actually requires the expanded surface, and avoid treating optional elasticity as core blockage.
- Dependencies: human_approval_and_decision_gates

## artifact and evidence systems

- Owner: `Generated reports, docs, local artifacts, and audit traces`
- State class: `evidence`
- Why it is part of the ecosystem: The ecosystem depends on reviewable proof, not memory or ad hoc narration.
- Source of truth:
- `docs/operations/STEADY-STATE-STATUS.md`
- `docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md`
- `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`
- `reports/truth-inventory/`
- Current state: Generated evidence covers capacity (`2026-04-11.1`), quota (`2026-04-12.1`), audit, steady-state, forge, and atlas surfaces.
- Blockers: none
- Failure mode: If generated evidence goes stale, operators and agents make decisions from contradictory surfaces.
- Next maturity move: Keep evidence regenerated in canonical order and make stale generated docs a hard trust signal rather than background noise.
- Dependencies: athanor_core_adopted_system, devstack_forge, operator_local_systems

## tenant and product systems

- Owner: `Registry-backed tenant roots and adjacent products`
- State class: `segregated`
- Why it is part of the ecosystem: Adjacent products affect the ecosystem boundary even when they should not block Athanor core operation.
- Source of truth:
- `config/automation-backbone/project-packet-registry.json`
- `config/automation-backbone/reconciliation-source-registry.json`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`
- `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
- Current state: Registry-backed tenant and adjacent roots remain segregated; current tenant source ids include `brayburn-trails-hoa-website, codexbuild-rfi-hers-rater-assistant, codexbuild-rfi-hers-rater-assistant-safe, codexbuild-rfi-hers-rater-assistant-v2, codexbuild-rfi-hers-stabilization-review, field-inspect-operations-runtime`.
- Blockers: none
- Failure mode: If tenant roots are not bounded, product work reopens core control-plane ambiguity.
- Next maturity move: Keep tenant lanes visible but non-blocking unless they leak back into Athanor startup, runtime, queue, or operator surfaces.
- Dependencies: athanor_core_adopted_system, human_approval_and_decision_gates

## human approval and decision gates

- Owner: `Shaun`
- State class: `approval`
- Why it is part of the ecosystem: Some work should remain paused until Shaun explicitly chooses to spend trust, credentials, or runtime mutation budget.
- Source of truth:
- `reports/truth-inventory/runtime-packet-inbox.json`
- `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`
- `docs/operations/STEADY-STATE-STATUS.md`
- Current state: Approvals stay explicit and lane-specific; live attention posture and pending gates surface through the live operator feed, steady-state JSON, and forge deferred inputs.
- Blockers: Provider secret repair, LETTA_API_KEY, OpenHands substrate readiness
- Failure mode: If approval gates are vague, the system either stalls invisibly or mutates live runtime without clear consent.
- Next maturity move: Keep approvals explicit and lane-specific: only elevate them when a bounded runtime mutation, credential gate, or pilot activation is intentionally being executed.
- Dependencies: athanor_core_adopted_system, devstack_forge, external_providers_and_saas, cluster_and_host_substrate

## Activation Lane Appendix

| Lane | Landing Repo | Landing Workspace | Approval State | Blocking Gate | Next Action |
| --- | --- | --- | --- | --- | --- |
| `Letta Memory Plane` | `C:/Athanor` | `config/automation-backbone` | `operator_review_required_before_adoption` | `continuity-gain-unproven` | Wire LETTA_API_KEY, run the bounded continuity benchmark, and keep replayability and pruning explicit. |
| `Agent Governance Toolkit Policy Plane` | `C:/Athanor` | `config/automation-backbone` | `operator_review_required_before_adoption` | `policy-bridge-slice-unproven` | Hold AGT below adapter work and only reopen the lane if a second protocol-boundary scenario proves unique value over native Athanor policy. |
| `OpenHands Bounded Worker Lane` | `C:/Athanor` | `config/automation-backbone` | `operator_review_required_before_adoption` | `bounded-worker-value-unproven` | Expose the OpenHands command on DESK, clear the worker env wiring, and run the bounded-worker eval. |

## Tenant and Product Boundary

- Project registry count: `6`
- Tenant source ids: `brayburn-trails-hoa-website, codexbuild-rfi-hers-rater-assistant, codexbuild-rfi-hers-rater-assistant-safe, codexbuild-rfi-hers-rater-assistant-v2, codexbuild-rfi-hers-stabilization-review, field-inspect-operations-runtime, field-inspect-root, meds-root, rfi-hers-rater-assistant-root, rfi-hers-stabilization-review, sabrina-ulrich-counseling-root, ulrich-energy-auditing-website-root`
- Rule: tenant and adjacent product systems remain visible but non-blocking unless they leak authority back into Athanor startup, queue, runtime, or operator surfaces.
