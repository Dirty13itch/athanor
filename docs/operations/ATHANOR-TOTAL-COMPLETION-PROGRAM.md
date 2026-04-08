# Athanor Total Completion Program

Source of truth: `config/automation-backbone/completion-program-registry.json`, `config/automation-backbone/program-operating-system.json`, `docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md`, `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
Validated against registry version: `completion-program-registry.json@2026-04-07.6`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: runtime truth outranks stale narrative, registry truth outranks helper prose, and this document must be updated whenever the completion-program registry, active checkpoint sequence, or final acceptance posture changes.

Sources:
- `config/automation-backbone/completion-program-registry.json`
- `config/automation-backbone/program-operating-system.json`
- `docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md`
- `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`
- `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

Versions:
- `completion-program-registry.json`: `2026-04-07.6`
- `program-operating-system.json`: `2026-03-25.1`

Last updated: 2026-04-07

## Purpose

This is the canonical execution program for finishing Athanor end to end.

It exists to prevent the work from fragmenting across:
- chat memory
- one-off fixes
- stale side roots
- runtime-only operator memory
- historical docs that still read like active truth

The program assumes:
- `C:\Athanor` is the only implementation-authority root
- `Dirty13itch/athanor` `main` is the only remote mainline
- `/home/shaun/repos/athanor` on `DEV` remains runtime authority until governed runtime sync finishes
- the Athanor ecosystem includes core, shared modules, tenants, lineage roots, and archive roots

## Program End State

- Athanor implementation truth is singular and current.
- Runtime-owned host state is either mirror-clean or explicitly packeted as governed drift.
- Every meaningful local source root and Dirty13itch repo has a governed role and disposition.
- Provider, deployment, monitoring, startup, and operator truth layers do not contradict each other.
- Side roots remain preserved only as lineage, archive, incubation, or tenant surfaces, never as hidden active authority.

## Execution Model

The completion program runs as one continuous loop:

1. Refresh evidence.
2. Close the highest-confidence source-truth gap.
3. Reclassify the remaining mismatches into repo truth, runtime-owned drift, tenant scope, or archive.
4. Update the ledger, queues, and governing docs.
5. Rerun validation.
6. Move the next bottleneck instead of leaving partial ambiguity behind.

This keeps the work moving without treating runtime repair, portfolio classification, or source harvest as separate disconnected projects.

That execution loop is now materialized through the Ralph-loop controller at `scripts/run_ralph_loop_pass.py`, which writes the live loop-state artifact to `reports/ralph-loop/latest.json`.

## Workstreams

### 1. Authority and Mainline Convergence

Objective:
- keep Athanor implementation truth singular
- stop local and remote history drift from becoming another hidden split-brain

Current scope:
- startup docs
- repo roots
- local-vs-GitHub alignment
- side-root authority demotion

Completion conditions:
- `C:\Athanor` is the only active implementation-authority root
- `origin/main` is explicitly aligned or any remaining drift is packeted
- no startup doc routes operators or agents to shadow authority

### 2. Deployment Authority Reconciliation

Objective:
- close the repo-side deployment mismatches that have strong live evidence
- stop live deploy surfaces from contradicting registries and Ansible truth

Current scope:
- Foundry vLLM lane truth
- Workshop worker lane truth
- VAULT monitoring targets
- Qdrant host ownership
- LiteLLM upstream lane metadata

Completion conditions:
- high-confidence repo-side deployment drift is closed
- remaining mismatches are explicitly runtime-owned or approval-gated

### 3. Runtime Sync and Governed Packets

Objective:
- keep host-level change work approval-gated and repeatable
- replace undocumented runtime repairs with packeted execution

Current scope:
- DEV runtime sync
- Foundry deploy lane
- DEV dashboard deploy lane
- VAULT auth repair packet
- future live config repair packets for stale Foundry and VAULT runtime files

Completion conditions:
- runtime-owned surfaces are mirror-clean or explicitly packeted
- rollback paths and backup roots are always known ahead of mutation

### 4. Provider and Secret Remediation

Objective:
- keep provider truth honest
- repair or deliberately demote auth-failed lanes
- stop secret-delivery ambiguity from poisoning routing truth

Current scope:
- VAULT LiteLLM env audit
- provider-specific evidence capture
- Kimi and GLM verification
- missing-env versus invalid-key versus auth-mode mismatch classification

Completion conditions:
- auth-failed lanes are repaired or demoted
- provider state, billing posture, and env-contract evidence agree

### 5. Monitoring and Observability Truth

Objective:
- make Prometheus and operator-surface monitoring follow current registry truth
- remove stale portal, node, and service assumptions from monitoring config

Current scope:
- VAULT Prometheus probe targets
- blackbox target hygiene
- metrics scrape coverage
- alert rule drift

Completion conditions:
- repo-side monitoring truth follows platform and operator registries
- remaining Prometheus drift is explicitly runtime-owned host config, not source ambiguity

### 6. Portfolio and Source Reconciliation

Objective:
- govern every meaningful local root and GitHub repo under one Athanor ecosystem model

Current scope:
- local source discovery
- GitHub repo classification
- live GitHub portfolio mirroring into machine-readable registry truth
- tenant-family audit for duplicate-heavy product roots
- `Field Inspect` operations-runtime selective replay packet
- `RFI & HERS Rater Assistant` duplicate-evidence packet
- duplicate clone normalization
- source registry upkeep

Completion conditions:
- every local root has a disposition
- every Dirty13itch repo has an ecosystem role

### 7. Lineage and Shared Extraction

Objective:
- absorb reusable value from lineage and adjacent tooling roots without reviving old systems as authorities

Current scope:
- `athanor-next`
- `C:\Reconcile`
- `Local-System`
- `local-system-v4`
- `Agentic Coding Tools`
- `AI-Dev-Control-Plane`
- `Codex System Config`

Completion conditions:
- every reviewed subsystem is imported, queued, archived, or rejected explicitly
- lineage roots remain non-authoritative after harvest

### 8. Tenant Architecture and Classification

Objective:
- turn separate products and local app roots into intentional Athanor tenants instead of unmanaged side projects

Current scope:
- `Field Inspect`
- `RFI & HERS Rater Assistant`
- `Field Inspect` sibling-lane collapse with an explicit operations-runtime replay packet
- `RFI & HERS Rater Assistant` duplicate-tree collapse with an explicit duplicate-evidence packet
- `Brayburn Trails HOA Website` locked `light-tenant`
- `Ulrich Energy`
- `Meds`
- `Sabrina Ulrich Counseling`
- other Dirty13itch product repos

Completion conditions:
- each product is classified as `light-tenant`, `deep-tenant`, `standalone-external`, or incubation only
- tenant queue and ecosystem registry agree on those decisions

### 9. Startup Docs and Prune

Objective:
- keep the active truth layer small, current, and unambiguous

Current scope:
- startup docs
- reference index
- archive discipline
- stale active-root deletions

Completion conditions:
- startup docs point only at current truth
- stale active-root material is deleted or archived once replaced

### 10. Validation and Publication

Objective:
- keep the whole program governable and publishable
- prevent another pile of unpublished reconciliation work

Current scope:
- validator coverage
- generated-doc freshness
- checkpoint discipline
- publication readiness

Completion conditions:
- validator and generated-doc checks remain green after each tranche
- reconciliation work can be published in slices instead of one giant dump

## Checkpoints

### Checkpoint 1: Control Surface Foundation

Already landed.

Includes:
- reconciliation control docs
- source registry
- tenant queue
- ecosystem registry
- preservation baseline
- validator wiring

### Checkpoint 2: Deployment Truth Narrowing

Active now.

Includes:
- repo-side closure of high-confidence deployment drift
- explicit separation of source-truth fixes from runtime-owned live config drift

Current examples:
- Qdrant host ownership fixed in source truth
- Foundry coder lane corrected to `devstral-small-2`
- Workshop worker batching cap imported into host vars
- VAULT monitoring probes corrected toward current topology and operator truth

### Checkpoint 3: Lineage and Side-Root Harvest

Includes:
- selective import and rejection decisions across `athanor-next`, Reconcile, Local-System, Agentic Coding Tools, and adjacent operator tooling

### Checkpoint 4: Ecosystem Classification

Includes:
- batch review of GitHub repos and local product roots into core, shared-module, tenant, lineage, operator-tooling, reference, or archive

### Checkpoint 5: Runtime Repair and Sync Packets

Includes:
- approval-gated live Foundry, VAULT, DEV, and WORKSHOP config repairs where runtime-owned drift still contradicts implementation authority

### Checkpoint 6: Final Publication and Freeze

Includes:
- checkpointed publication
- side-root freeze
- final truth normalization
- completion evidence refresh

## Current Priority Order

1. Keep implementation authority singular and current.
2. Keep closing high-confidence repo-side deployment drift.
3. Turn every remaining live mismatch into either runtime-owned drift or a governed repair packet.
4. Finish ecosystem classification so no repo or local root remains ambiguous.
5. Keep provider and secret truth honest enough that routing and autonomy decisions are not built on fiction.
6. Keep pruning stale active-root truth as soon as verified replacements exist.

## Acceptance Matrix

The completion program is not done until these hold together:

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_documentation_index.py --check`
- `python scripts/generate_project_maturity_report.py --check`
- `python scripts/generate_truth_inventory_reports.py --check`
- `python scripts/collect_truth_inventory.py`
- `python scripts/run_service_contract_tests.py`
- `cd projects/dashboard && npm test`
- `cd projects/dashboard && npm run typecheck`
- `cd projects/dashboard && npm run build`
- `cd projects/dashboard && npm run test:e2e:terminal`
- `cd projects/dashboard && npm run test:e2e:audit`
- `cd projects/agents && C:\Athanor\projects\agents\.venv\Scripts\python.exe -m pytest tests -q`
- `cd projects/gpu-orchestrator && C:\Athanor\projects\gpu-orchestrator\.venv\Scripts\python.exe -m pytest tests -q`
- `cd projects/ws-pty-bridge && npm run ci`

## Standing Rules

- Do not publish from a stale local mainline.
- Do not merge side roots wholesale.
- Do not promote runtime-owned host state into implementation authority without corroborating registry or live evidence.
- Do not leave a reviewed repo, root, or runtime lane in a “maybe important” state.
- Do not keep stale startup or active-root guidance once replacement truth is verified.
