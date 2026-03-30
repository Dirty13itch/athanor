# Athanor Completion Audit Plan

This plan exists to answer one question rigorously:

What is actually finished, partially finished, dormant, broken, or still only planned across every layer of Athanor?

## Implementation Status

This is now an implemented audit program, not just a proposed workflow.

Canonical command:

- `python scripts/run-completion-audit.py`

Stable canonical outputs:

- `docs/atlas/inventory/completion/dashboard-route-census.json`
- `docs/atlas/inventory/completion/dashboard-support-surface-census.json`
- `docs/atlas/inventory/completion/dashboard-api-census.json`
- `docs/atlas/inventory/completion/dashboard-component-census.json`
- `docs/atlas/inventory/completion/dashboard-mount-graph.json`
- `docs/atlas/inventory/completion/agent-endpoint-census.json`
- `docs/atlas/inventory/completion/runtime-subsystem-census.json`
- `docs/atlas/inventory/completion/env-contract-census.json`
- `docs/atlas/inventory/completion/deployment-ownership-matrix.json`

Run-specific evidence:

- `reports/completion-audit/latest/summary.md`
- `reports/completion-audit/latest/release-readiness.json`
- `reports/completion-audit/latest/remediation-backlog.json`
- timestamped run directories under `reports/completion-audit/`

Current gate state as of `2026-03-11`:

- `status`: `ready`
- `failedJobCount`: `0`
- `routeCount`: `25`
- `supportSurfaceCount`: `30`
- `apiCount`: `54`
- `orphanCandidateCount`: `1` (`/api/stash/stats`)
- remaining warnings are deployment drift and explicitly dormant/unmounted UI/runtime surfaces

Recent hardening completed:

- added direct unit coverage for every route-local and global support surface in `projects/dashboard/src/app/support-surfaces.test.tsx`
- removed duplicate root support-surface records from the census
- promoted `/offline` to a fully audited support-route classification
- fixed dynamic API-consumer matching for template-literal paths such as workforce mutation routes
- redeployed the Foundry agent server so the subscription-control endpoints and consolidation stats are live and audited

The previous failure mode was relying too heavily on top-level docs, nav definitions, and obvious entrypoints. That misses hidden routes, dormant components, partially wired APIs, unmounted subsystems, and live/runtime drift. This audit program fixes that by forcing every layer to be inventoried from its strongest source.

## Target Standard

The target is not "feature complete enough." The target is a defensible AAA-grade full-stack system audit where:

- every route, sub-page, layout, and support surface is enumerated
- every API route and agent endpoint is mapped to a real consumer or explicitly marked dormant/supporting
- every major component family is classified as mounted, partially mounted, or unmounted
- every background subsystem is classified as live, wired but unsurfaced, or dead/stale
- every deployment surface is traced back to the repo layer that actually owns it
- every finding turns into a ranked remediation item with evidence

## What I Can Use To Improve Coverage

### Static codebase census

I can enumerate surfaces directly from code instead of relying on docs:

- filesystem route discovery for every `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `template.tsx`, `default.tsx`, and `not-found.tsx`
- API route discovery for every `route.ts`
- import-graph analysis to determine which components are actually mounted
- feature-module and component-family mapping
- AST parsing for Python and TypeScript ownership extraction
- environment-variable, flag, and config-key inventory

### Runtime and browser inspection

I can inspect what actually works, not just what exists:

- Playwright route crawling with screenshots, console capture, and network capture
- responsive checks for desktop and mobile breakpoints
- route reachability, redirect, and 404 detection
- live API probing against dashboard and agent-server endpoints
- streaming/SSE/WebSocket validation
- shell, drawer, sheet, and modal interaction checks

### Repo and infrastructure reconciliation

I can trace runtime back to repo truth:

- `ansible/`, `services/`, and `projects/` deployment manifest comparison
- env-var completeness and drift scanning
- node/service reachability and health checks
- local clone, GitHub, and deployment-source reconciliation
- inventory comparison between docs, code, and live nodes

### Quality and completion scoring

I can grade completeness systematically:

- mounted vs unmounted vs orphaned UI detection
- route-to-API consumer mapping
- API-to-runtime dependency mapping
- empty/loading/error-state checks
- test, typecheck, lint, and build coverage
- dead code and stale docs detection

## Evidence Hierarchy

When deciding whether something is finished, use this order:

1. Running code, mounted routes, live configs, and deployed manifests
2. Source files that define routes, endpoints, components, and background behavior
3. Operational docs that still match runtime evidence
4. Design docs and ADRs
5. Planning docs and historical map material

The audit should never let a design doc overrule mounted code or let a planning document imply completion.

## Completion Taxonomy

Every audited item must receive exactly one classification:

- `live_complete`: implemented, reachable, wired, and behaving correctly
- `live_partial`: reachable, but missing actions, states, wiring, or polish
- `implemented_not_live`: exists in code but is not mounted or not part of the main live path
- `stub_only`: shell or placeholder exists, but core behavior is absent
- `planned_only`: documented intent with no meaningful implementation
- `broken`: intended live behavior currently fails
- `deprecated`: still present but not intended to survive
- `legacy`: historical/reference only

## Audit Layers

### 1. UI surface audit

Inventory every UI surface from the filesystem, not just navigation:

- app routes
- nested routes
- dynamic segments
- support routes
- route groups
- layouts and nested layout ownership
- drawers, sheets, modals, and command surfaces
- route-local actions
- hidden or linked sub-pages that are not in primary nav

For every route or sub-page, capture:

- path and owner
- whether it is in primary nav
- whether it is reachable from links or direct URL only
- mounted component tree root
- data sources and API dependencies
- query params and local persistence
- primary actions
- desktop state
- mobile state
- empty/loading/error states
- completion classification

### 2. API and contract audit

Inventory:

- dashboard Next.js API routes
- agent-server endpoints
- backend service dependencies
- typed contracts and normalization layers

For every API surface, capture:

- entrypoint
- source owner
- upstream dependency
- consuming UI routes or runtime subsystems
- contract shape
- error behavior
- whether it is live, support-only, or orphaned

### 3. Runtime subsystem audit

Inventory:

- agents
- task engine
- workspace / CST
- goals and workplan
- notifications and trust
- patterns and learning
- subscription brokerage
- skills/research/consolidation lanes
- schedulers and workers

For each subsystem, capture:

- source files
- live entrypoints
- operator touchpoints
- dashboard visibility
- missing UI exposure
- completion classification

### 4. Deployment and infrastructure audit

Inventory:

- nodes and roles
- compose manifests
- Ansible roles
- project-local manifests
- env files and secrets expectations
- live services and model lanes

For each deployment surface, capture:

- owning repo layer
- live location
- drift against other repo layers
- health status
- whether the live version should be promoted back into repo truth

### 5. Documentation and source-of-truth audit

Inventory:

- atlas docs
- operational docs
- design docs
- build manifest
- older map docs

For each doc, capture:

- what truth it still owns
- what it no longer owns
- whether it is current, partial, stale, or legacy
- whether it is backed by code/runtime evidence

## Tooling To Build

The completion audit should be automated with repo scripts so it can be rerun.

### Static inventory scripts

- `scripts/validate-atlas.py`
  Already in progress. Verifies atlas integrity and coverage.
- `scripts/census-dashboard-routes.py`
  Enumerate every app route file and generate a route inventory from filesystem truth.
- `scripts/census-dashboard-api.py`
  Enumerate every API route and map it to files, contracts, and likely consumers.
- `scripts/census-dashboard-components.py`
  Build a component inventory and ownership map.
- `scripts/find-mounted-ui.py`
  Build the reachability graph and classify UI files as mounted, partial, or unmounted.
- `scripts/map-agent-endpoints.py`
  Enumerate agent-server endpoints and group them into runtime subsystems.
- `scripts/census-env-contracts.py`
  Inventory environment variables and config dependencies across dashboard, agents, and deployment layers.
- `scripts/audit-deployment-ownership.py`
  Classify live deployment ownership and reachability across repo and node layers.

### Runtime validation scripts

- `projects/dashboard/tests/e2e/api-census.spec.ts`
  Probe every generated dashboard API surface in deterministic fixture mode.
- `projects/dashboard/tests/e2e/smoke-routes.spec.ts`
  Visit every discovered route in deterministic fixture mode and fail on runtime issues.
- `projects/dashboard/tests/e2e/audit-capture.spec.ts`
  Capture route screenshots for every discovered route in fixture mode.
- `projects/dashboard/tests/e2e/accessibility.spec.ts`
  Run route-wide accessibility smoke against every discovered route on desktop and mobile.
- `scripts/tests/live-dashboard-smoke.py`
  Probe the live dashboard, live route surface, live JSON APIs, and live chat paths.
- `scripts/probe-agent-runtime.py`
  Probe live agent-server subsystem endpoints and expose missing runtime lanes directly.

### Reporting artifacts

- route inventory JSON
- API inventory JSON
- component mount graph JSON
- unfinished-surface report
- route completion matrix
- API orphan/support report
- runtime subsystem completion report
- deployment drift report
- release readiness report

## Audit Execution Program

### Phase 0: Freeze the audit model

- define the taxonomy and required fields
- define the evidence hierarchy
- define what counts as "finished"
- define which findings are blockers vs refinements

Output:

- completion taxonomy
- inventory schemas
- validator entrypoints

### Phase 1: Exhaustive static census

Do not touch the browser yet. First inventory everything from source:

- all dashboard routes and support files
- all dashboard APIs
- all feature modules
- all major components
- all agent endpoints
- all runtime subsystems
- all deployment manifests
- all env/config dependencies

Output:

- canonical code-derived inventories
- orphan and dormant surface lists
- route/API/component ownership graph

### Phase 2: Mount and reachability audit

Using the static census, test every declared route and sub-surface:

- direct navigation to each route
- auth/redirect behavior if any
- rendering success/failure
- console errors
- failed network requests
- hidden page discovery from in-app links
- drawer/modal/sheet interaction reachability

Output:

- route reachability report
- runtime console/network error report
- screenshot set for every route

### Phase 3: Data and action audit

For every live or intended-live route:

- identify all backing APIs
- confirm real data appears
- confirm primary actions work
- confirm loading, empty, and error states exist
- confirm mutations update state
- confirm cross-route drilldowns work

Output:

- route completion matrix
- broken action list
- missing-state list

### Phase 4: Responsive and polish audit

For every route:

- desktop verification
- mobile verification
- keyboard/accessibility basics
- scroll, overflow, truncation, and drawer behavior
- shell consistency
- visual hierarchy and clarity

Output:

- UI polish backlog
- responsive breakage report
- accessibility-baseline report

### Phase 5: Runtime and infrastructure audit

For each subsystem and node:

- verify live deployment source
- compare runtime manifests against repo truth
- confirm env/config completeness
- confirm health endpoints and service availability
- trace dashboard/API dependencies to their upstream services

Output:

- subsystem readiness report
- deployment-source-of-truth report
- live drift backlog

### Phase 6: Documentation reconciliation

Once source and runtime facts are known:

- update atlas and inventories
- mark stale docs explicitly
- preserve historical docs as reference only
- ensure every live claim in docs is backed by evidence

Output:

- updated atlas
- doc status registry
- stale-doc cleanup queue

### Phase 7: Remediation program

Turn findings into an autonomous execution queue:

- blockers first
- broken live routes second
- live_partial flows third
- implemented_not_live promotion or removal decisions fourth
- polish and AAA refinement last

Each remediation item should include:

- evidence
- source owner
- affected routes/APIs/subsystems
- risk
- exact acceptance criteria

Output:

- ranked remediation backlog
- autonomous execution batches

### Phase 8: Release readiness gate

Do not call the system "ready" until it passes:

- route inventory complete
- no orphan live-critical APIs
- no broken primary routes
- no missing loading/empty/error states on critical surfaces
- no unresolved deployment-source ambiguity on critical nodes
- no stale docs claiming current truth
- dashboard, agent-server, and core runtime flows verified end to end

Output:

- release readiness report
- go/no-go status

## Autonomy Boundaries

I can do these autonomously:

- inventories
- static analysis
- browser crawling
- screenshots and network/console capture
- API probing
- validator creation
- documentation reconciliation
- backlog generation
- most code fixes, tests, and polish passes

I should only stop for explicit direction on:

- destructive cleanup or deletion
- irreversible architecture changes
- production secret rotation
- provider billing/routing policy changes with real spend implications
- product decisions where two valid futures exist

## Immediate Execution Order

This is the order I should actually run:

1. Finish and use `scripts/validate-atlas.py` as the baseline validator.
2. Build filesystem route census so hidden sub-pages stop depending on nav awareness.
3. Build API census and route-to-API consumer graph.
4. Build mounted vs unmounted UI detection from import graphs.
5. Run full Playwright crawl over every discovered route.
6. Generate a route completion matrix with screenshots and error capture.
7. Probe dashboard APIs and agent endpoints to classify support/orphan/live surfaces.
8. Audit deployment truth and env/config completeness for critical nodes.
9. Convert findings into a ranked execution backlog.
10. Execute remediation in batches until the release gate passes.

## Definition Of "AAA Ready"

The system is AAA ready only when:

- the entire surface area is known
- unfinished work is classified and ranked
- critical paths are fully wired and polished
- dormant features are intentionally promoted, deferred, or removed
- docs, code, runtime, and deployment sources no longer contradict each other
- the operator experience is coherent on desktop and mobile
- the system can be validated again automatically after each major change

That is the standard this audit program is meant to enforce.
