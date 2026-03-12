# Athanor Next

Status: Canonical strategic design layer  
Last updated: 2026-03-10

## Purpose

This document is the program-level north star above:

- `docs/VISION.md`
- `docs/SYSTEM-SPEC.md`
- `docs/BUILD-MANIFEST.md`

`BUILD-MANIFEST.md` remains the tactical queue. This document defines what that queue is for.

## Target State

Athanor is a one-person-maintainable AI operating environment.

- **Shaun** sets direction, priorities, and judgment.
- **Claude** operates as COO and meta-orchestrator.
- **Local agents** are the specialist workforce.
- **The Command Center** is the primary operator surface.
- **EoBQ** is the first active first-class tenant beyond Athanor core.

Infrastructure convergence is an enabling track, not the product. The product is unified operational intelligence across:

- system state
- workforce state
- projects
- memory and knowledge
- creative work
- media
- home

## Canonical Operating Model

### Organization

- Shaun -> vision, approvals, constraints, final judgment
- Claude -> architecture, coordination, execution planning, system stewardship
- Agent workforce -> specialized execution inside explicit contracts

### Interfaces

- **Command Center:** primary interface for posture, delegation, results, and project switching
- **Claude Code / Claudeman:** COO workbench for architecture, delivery, and operations
- **Satellite tools:** Grafana, Open WebUI, ComfyUI, and other domain-native tools remain available, but they are satellites, not the system face

### Project Model

- **Athanor core:** active first-class project
- **Empire of Broken Queens:** active first-class tenant
- **Kindred:** scaffolded future tenant
- future projects must fit into the same registry, context, and routing model

### Autonomy Model

- some actions are proactive and silent except for logging
- some actions notify after execution
- some actions always require review
- constitutional boundaries and auditability are mandatory, not optional

## Program Tracks

### 1. Command Center

Make the dashboard the unified operator console for cluster state, workforce state, project state, domain state, and interaction state.

### 2. COO and Agent Operations

Formalize Claude-as-COO, explicit agent contracts, tasking, escalation, trust, feedback, and proactive operations.

### 3. Knowledge and Memory

Treat Qdrant, Neo4j, Redis, logs, and preference signals as one memory fabric with differentiated roles.

### 4. Project Platform

Make project identity, context, routing, outputs, and memory boundaries first-class. EoBQ is the proving ground.

### 5. Infrastructure Convergence

Make Ansible the deployment truth, freeze the runtime map, centralize config, remove tracked secrets, and prevent drift.

### 6. Continuous Refinement

Measure, audit, harden, and keep the system understandable at one-person scale.

## Frozen Contracts

### Runtime Map

- `reasoning`, `coding` -> Foundry coordinator
- `coder` -> Foundry coder
- `creative`, `utility`, `uncensored`, `fast`, `worker` -> Workshop worker
- `embedding`, `reranker` -> DEV retrieval runtimes

### Deployment Truth

- `ansible/` remains the primary desired-state baseline
- `services/` or `projects/*/docker-compose*` may be authoritative when they match live better than stale Ansible roles
- the dashboard and agents must consume centralized runtime config, not scattered literals

### Product Truth

- the Command Center is the primary interface
- LiteLLM is the inference contract
- the project registry is first-class
- EoBQ is an integrated tenant, not a sidecar app

## Acceptance Bar

- repo-level docs do not disagree about Athanor's purpose or active priorities
- production dashboard pages do not hardcode cluster URLs or credentials
- project identity is visible in both dashboard and agent layers
- DEV retrieval services are reflected in routing and observability
- drift checks fail when topology, aliases, or agent roster diverge
