# Athanor System Specification

Source of truth: `config/automation-backbone/platform-topology.json`, `config/automation-backbone/project-maturity-registry.json`, `config/automation-backbone/program-operating-system.json`, `python scripts/session_restart_brief.py --refresh`, and `reports/truth-inventory/finish-scoreboard.json`
Validated against registry version: `platform-topology.json@2026-04-11.2`, `project-maturity-registry.json@2026-04-20.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: node membership, service placement, endpoints, auth classes, project maturity, review cadence, and closure posture live in the registry set under `config/automation-backbone` plus the generated finish surfaces. This document keeps architecture, operating boundaries, and stable contracts only.

---

## Purpose

Athanor is a registry-governed sovereign AI cluster operated by one person. The system is no longer defined by scattered narrative docs; it is defined by executable contracts:

- topology and service truth
- project maturity truth
- docs lifecycle truth
- operating cadence and lens truth

This document explains how those contracts fit together and what the cluster is supposed to optimize for. It is not the surface that decides queue order, active claim, or remaining typed brakes.

## Validated Registry Snapshot

At registry version `2026-03-25.1`, the snapshot describes Athanor as:

- 5 nodes: `dev`, `foundry`, `workshop`, `vault`, `desk`
- 36 registry-managed services
- 9 tracked projects in the maturity registry
- 12 standing review lenses and 6 standing cadence buckets

If those numbers change, the registry changes first.

## System Objective

The operating objective comes from `program-operating-system.json`:

- secure enough to trust on the LAN
- coherent enough to reason about from one source of truth
- testable enough that velocity is real
- modular enough that each project can mature independently
- measurable enough that autonomy and feature growth can be governed

## Node Roles

| Node | Role | What it owns |
|------|------|--------------|
| `dev` | Ops center | Dashboard, quality gate, semantic router, embedding/reranker, local operator tooling |
| `foundry` | Heavy compute | Agent server, GPU orchestrator, heavy inference lanes |
| `workshop` | Creative compute | WS PTY bridge, interactive inference lanes, ComfyUI, creative/operator adjunct surfaces |
| `vault` | Storage + observability | Redis, Qdrant, Neo4j, LiteLLM, metrics, logs, shared stateful services |
| `desk` | Workstation | Operator desktop and optional compatibility provider-bridge host when explicitly enabled |

Use the topology registry for current host/IP mapping. This table is a role summary only.

## Architecture Layers

### 1. Registry-backed control plane

The control plane is defined in `config/automation-backbone`.

- `platform-topology.json` defines nodes, services, runtime class, auth class, and health path.
- `project-maturity-registry.json` defines what each project must satisfy before it can claim its class.
- `docs-lifecycle-registry.json` defines which docs are canonical, generated, reference, or archive.
- `program-operating-system.json` defines the standing review lenses, cadence, and program roles.

Every helper, env default, CI gate, and canonical doc should flow from that layer.

### 2. Core platform runtimes

In this validated snapshot, the `platform-core` set is:

- `projects/agents`
- `projects/gpu-orchestrator`
- `projects/ws-pty-bridge`

These runtimes carry control-plane obligations. They are expected to pass full acceptance gates from a clean checkout and to fail closed when auth or topology is misconfigured.

### 3. Production product surface

In this validated snapshot, the `production-product` surface is:

- `projects/dashboard`

It is an authenticated operator console, not a public LAN page and not a browser-local prototype. Its mutation paths must prove operator session validity and upstream auth together.

### 4. Non-core portfolio

Everything else is explicitly classed as `active-scaffold`, `incubation`, or `archive`. That matters because Athanor is run as a portfolio, not as one undifferentiated repo blob. Non-core work may proceed, but it does not gain production obligations by accident.

## Stable Contracts

### Topology contract

Use `platform-topology.json` for current:

- node ids and default hosts
- service ids, nodes, schemes, ports, and health paths
- runtime class
- auth class

No code, doc, compose file, or operator runbook should hardcode a conflicting placement.

### Project maturity contract

Use `project-maturity-registry.json` for current:

- project class
- owner
- workspace
- env example
- CI and acceptance gates
- monitoring hooks

Promotion, demotion, and archive decisions happen through that registry.

### Docs lifecycle contract

Use `docs-lifecycle-registry.json` for the current lifecycle class of each document:

- canonical
- generated
- reference
- archive

Canonical docs must stay current. Generated docs must be regenerable and freshness-checked. Reference docs may lag but must not override runtime truth.

### Auth and privilege contract

Privileged surfaces are expected to converge on shared auth and privilege classes:

- `read-only`
- `operator`
- `admin`
- `destructive-admin`

The registry currently records service auth classes at the platform level (`operator`, `admin`, `internal_only`). The implementation program is responsible for mapping mutation behavior onto the stronger shared privilege envelope without reopening services to unauthenticated LAN access.

### Governor and task contract

For this cycle, Redis remains the current runtime store for task-engine and adjacent runtime coordination state. Durable task truth is formalized around the existing `athanor:tasks` namespace, while governor posture stays separate from alternate queue ownership.

## Operating Model

### Standing lenses

All subsystem review rotates through the same lenses:

- security
- truth
- reliability
- developer velocity
- product integrity
- architecture
- observability
- evaluation
- portfolio discipline
- economic efficiency
- knowledge quality
- autonomy governance

### Standing cadence

The operating cadence is registry-backed:

- daily: health, CI, auth drift, queue backlog, artifact cleanup
- twice weekly: one rotating lens audit per subsystem
- weekly: architecture review, portfolio review, dependency review, docs freshness
- biweekly: project maturity review
- monthly: security review, recovery drill review, topology drift review, artifact purge
- quarterly: platform reset and dead-system removal

### Standing roles

The operating system currently assumes these role lanes:

- program manager
- security auditor
- runtime architect
- frontend curator
- DX enforcer
- data and knowledge curator
- eval lead
- infra/SRE
- research scout
- portfolio curator

They are operating roles, not separate sources of truth.

## What This Document Will Not Do

This document does not own:

- exact host/IP values
- exact port lists
- generated service inventories
- per-project acceptance commands
- historical build narrative

Those belong in the registry, generated reports, or reference/archive docs.
