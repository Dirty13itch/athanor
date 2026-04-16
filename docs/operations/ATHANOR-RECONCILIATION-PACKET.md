# Athanor Reconciliation Packet

Last updated: 2026-04-07

## Purpose

Run Athanor reconciliation as a full-system portfolio program instead of a narrow repo cleanup pass.

The program exists to:
- keep `C:\Athanor` as the only implementation-authority root
- reconcile Athanor side roots and evidence workspaces without losing good code or docs
- classify the full Dirty13itch GitHub portfolio into one Athanor ecosystem model
- extract cross-repo platform value into Athanor or Athanor-owned shared surfaces case by case
- treat most product repos as light tenants by default instead of forcing a monorepo collapse

## Locked Decisions

- `C:\Athanor` remains the only implementation-authority root.
- GitHub `Dirty13itch/athanor` `origin/main` remains the only remote mainline.
- `/home/shaun/repos/athanor` on `DEV` remains runtime authority and is governed through runtime-ownership packets, not this reconciliation lane.
- `C:\Users\Shaun\dev\athanor-next` and `C:\Reconcile` are mandatory harvest lanes and then freeze candidates.
- The full Dirty13itch GitHub portfolio is in scope for the Athanor reconciliation program.
- Athanor is the ecosystem parent and control plane, not a blind destination for every repo.
- Shared-code handling remains case by case.
- Default tenant depth is `light-tenant`.
- Final GitHub repo roles are confirmed with Shaun in category batches, not by unilateral automation.

## Control Artifacts

Program control now lives in these Athanor-owned artifacts:
- `config/automation-backbone/reconciliation-source-registry.json`
- `config/automation-backbone/completion-program-registry.json`
- `docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md`
- `docs/operations/ATHANOR-RECONCILIATION-PRESERVATION-BASELINE.md`
- `docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md`
- `docs/operations/ATHANOR-TENANT-QUEUE.md`
- `docs/operations/ATHANOR-RECONCILIATION-LEDGER.md`
- `docs/operations/ATHANOR-TOTAL-COMPLETION-PROGRAM.md`
- `scripts/capture_reconciliation_preservation.py`
- `scripts/discover_reconciliation_sources.py`

`docs/projects/PORTFOLIO-REGISTRY.md` remains the in-repo maturity map. The new ecosystem registry owns the wider Dirty13itch portfolio classification.

## Current Reconcile Findings

- Athanor now owns the imported Reconcile deployment-helper trio:
  - `scripts/render_ansible_template.py`
  - `scripts/Invoke-DeploymentDriftAudit.ps1`
  - `scripts/Invoke-RepoDeploymentManifestAudit.ps1`
- The live deployment-intent audit now writes:
  - `reports/deployment-drift/summary.md`
  - `reports/rendered/*`
  - `reports/live/*`
- The live repo-manifest audit now writes:
  - `reports/repo-manifest-drift/summary.md`
  - `reports/repo-manifest-source/*`
  - `reports/repo-manifest-live/*`
- The repo-manifest audit had to be adapted after import because the March Reconcile version still pointed at retired `services/node1` and `services/node2` compose paths. The Athanor-owned version now compares only current repo-owned compose surfaces under `projects/`.
- Current repo-manifest drift is narrow and reviewable:
  - `foundry-agents-project`
  - `foundry-gpu-orchestrator-project`
  - `workshop-dashboard-project`
  - `workshop-dashboard-src-project`
- Current repo-manifest diffs are mostly expected secret substitution plus one confirmed non-secret config mismatch in the dashboard compose: the tracked default `ATHANOR_QDRANT_URL` in `projects/dashboard/docker-compose.yml` differs from the current live workshop value.
- The deployment audit exposed and closed one stale source-truth mismatch: `ansible/host_vars/vault.yml` was still probing Qdrant on node1/FOUNDRY, and now points at VAULT to match `platform-topology.json`, operator-surface truth, and the tracked dashboard compose defaults.
- Runtime checks on 2026-04-06 now prove the live Qdrant authority side:
  - `http://192.168.1.203:6333/collections` responds successfully
  - `http://192.168.1.244:6333/collections` is unreachable
  - `docker ps` shows a live `qdrant` container on VAULT and no corresponding container on FOUNDRY
- The stale node1/FOUNDRY Qdrant playbook assignment has therefore been removed from `ansible/playbooks/site.yml` and `ansible/playbooks/node1.yml` so Ansible no longer advertises the wrong deployment host.
- The remaining Qdrant gap is narrower: Athanor still lacks a VAULT-native managed role/path for Qdrant, so current Ansible truth is "do not deploy it on FOUNDRY" rather than a full VAULT playbook ownership story.
- Current deployment drift is no longer concentrated in the old Foundry vLLM or VAULT LiteLLM lanes.
- The 2026-04-08 governed runtime pass closed those core surfaces directly:
  - `foundry-vllm` is now identical
  - `vault-litellm` is now identical
  - `vault-prometheus` is now identical
  - `workshop-vllm` is now identical
  - `workshop-dashboard` is now identical
  - `workshop-open-webui` is now identical
- The remaining deployment drift is the narrower packet-and-product set:
  - `foundry-agents`
  - `foundry-gpu-orchestrator`
  - `vault-alert-rules`
  - `workshop-comfyui`
  - `workshop-eoq`
  - `workshop-ulrich-energy`
- The Foundry coder runtime truth is now explicit and reconciled into implementation authority:
  - direct `/v1/models` probing on `http://192.168.1.244:8006` returns `qwen3-coder-30b`
  - live `docker inspect vllm-coder` shows `--served-model-name qwen3-coder-30b`, `--tool-call-parser qwen3_xml`, `--max-num-seqs 16`, and a bind mount from `/mnt/local-fast/models/Qwen3-Coder-30B-A3B-Instruct-AWQ:/model:ro`
  - repo truth now matches that runtime instead of preserving the older Devstral-era assumption
- The VAULT LiteLLM config lane is also closed as a config-reconciliation problem:
  - the live `/mnt/user/appdata/litellm/config.yaml` now carries the canonical Athanor-owned header and matches the rendered authority artifact
  - the `litellm` container restarts healthy on the reconciled config and re-enables Redis cache wiring through the tracked env contract
  - provider-specific closure now lives in the auth and secret lane rather than the config lane
- VAULT Prometheus also had a smaller repo-side lag that could be corrected without touching runtime-owned host configs:
  - the Workshop worker probe was still targeting the retired `:8000` lane instead of the current `:8010` worker runtime
  - the dashboard probe now follows platform-topology truth directly at the DEV runtime health path (`/api/operator/session`) instead of using a root-level URL
  - registry-backed specialist and internal surfaces already present in operator truth but missing from the tracked probe set are now added for `gpu-orchestrator`, `ntfy`, `langfuse`, `eoq`, `ulrich-energy`, and `speaches`
- The remaining Prometheus drift is therefore increasingly concentrated in runtime-owned VAULT config shape: extra blackbox/TCP jobs, direct metrics jobs, and any still-stale shadow targets in the live file.
- Those three runtime-owned drift surfaces are now explicitly packeted in the runtime-ownership layer instead of living only as audit prose:
  - `foundry-vllm-compose-reconciliation-packet`
  - `vault-litellm-config-reconciliation-packet`
  - `vault-prometheus-config-reconciliation-packet`
- The governing intent is now clear:
  - repo-side truth stays in Athanor
  - live FOUNDRY and VAULT config changes move through approval packets with backup, verification, and rollback
  - the remaining disagreement is no longer an undocumented operator-memory lane
- The 2026-04-07 runtime packet tranche then closed three of those live lanes with direct reprobe:
  - `vault-prometheus-config-reconciliation-packet` is now executed and the live Prometheus container answers `/-/healthy`
  - `foundry-vllm-compose-reconciliation-packet` is now executed and both `vllm-coordinator` and `vllm-coder` are healthy on `athanor/vllm:qwen35-20260315`
  - `workshop-vllm-compose-reconciliation-packet` is now executed and `vllm-node2` is healthy on the same pinned image lineage
- The 2026-04-08 follow-on runtime pass then closed the VAULT LiteLLM config lane itself:
  - `vault-litellm-config-reconciliation-packet` is now executed
  - the drift audit now reports `vault-litellm` as identical
  - the remaining VAULT LiteLLM work is provider-auth and secret-source repair, not config divergence
- The owner-surface audit remains important because the remaining VAULT blocker is now purely secret and auth oriented:
  - `/boot/config/plugins/dynamix.my.servers/configs/docker.config.json` has no `litellm` template mapping
  - `container-watchdog.sh` explicitly monitors `litellm`
  - the live container still runs as a standalone Docker surface rather than a discovered compose-manager or template-managed service
  - historical `/mnt/user/appdata/litellm/backups/litellm.inspect.*.json` captures prove the container env set changed inline over time, including a broader provider-key set on 2026-03-30
- That means the unresolved VAULT LiteLLM work is no longer "find the management plane." The current blocker is "restore or formalize the secret owner for a container that is already behaving like the practical owner surface."
- The vLLM closure also changed the governing runtime story:
  - the old floating `athanor/vllm:qwen35` tag was not deterministic across hosts
  - Workshop and Foundry are now intentionally converged on the same pinned artifact, `athanor/vllm:qwen35-20260315`
  - the remaining vLLM work is to keep repo truth, packet docs, and operator guidance pinned to that deterministic image contract instead of drifting back toward a floating-tag model
- Workshop vLLM also had one narrow tuning delta worth importing into source truth:
  - live `docker inspect` on `vllm-node2` confirms `--max-num-batched-tokens 2096`
  - `ansible/host_vars/interface.yml` now carries that flag so the tracked worker lane preserves the current batching ceiling without yet asserting broader image or launch-flag parity
- Workshop ownership is also deeper now:
  - `repo-roots-registry.json` now tracks `workshop-opt-athanor` as an explicit runtime-state root
  - runtime ownership now covers a Workshop control-surface lane, a Workshop vLLM lane, and a grouped Workshop product/creative lane
  - the Workshop control-surface source contract now explicitly includes `projects/ws-pty-bridge` and the shadow-dashboard compose template
- One source-truth hole was closed in the same pass:
  - `ansible/roles/dashboard/defaults/main.yml` now points `dashboard_vllm_worker_url` at the live `:8010` worker lane
  - the Workshop shadow dashboard role now templates `ws-pty-bridge` and syncs `projects/ws-pty-bridge` into `/opt/athanor/ws-pty-bridge` for recovery-only governance
- The remaining Workshop drift is therefore narrower and now closed on the control-surface lane:
  - repo truth was corrected to the actual shadow-dashboard/ws-pty contract before any live mutation
  - the 2026-04-08 backup-first `workshop-control-surface-compose-reconciliation-packet` then synced the Workshop shadow-dashboard and `ws-pty-bridge` source bundles, replaced `/opt/athanor/dashboard/docker-compose.yml` from `reports/rendered/workshop-dashboard.rendered.yml`, and re-probed both `http://127.0.0.1:3001/` and `http://127.0.0.1:3100/health` at `200`
  - `workshop-vllm` is now an executed runtime packet with a healthy reprobe on the pinned image lane
  - `workshop-open-webui`, `workshop-comfyui`, `workshop-eoq`, and `workshop-ulrich-energy` are explicit runtime-owned surfaces even where they are not yet split into narrower repair packets
- The governed DEV runtime-repo sync lane is now more precise too:
  - the sync path itself has already been proven
- fresh 2026-04-08 runtime probing shows the DEV mirror reset succeeds, but `athanor-overnight.service` immediately re-dirties tracked generated artifacts after the clean reset window
  - the remaining DEV runtime blocker is therefore a reopened mirror-clean rerun, not uncertainty about how the packet should work
- fresh 2026-04-08 runtime probing also superseded the older Foundry coder assumption that had been imported into repo truth on the previous pass:
  - direct `/v1/models` probing on `http://192.168.1.244:8006` now returns `qwen3-coder-30b`
  - live `docker inspect vllm-coder` shows `--served-model-name qwen3-coder-30b`, `--tool-call-parser qwen3_xml`, `--max-num-seqs 16`, and a bind mount from `/mnt/local-fast/models/Qwen3-Coder-30B-A3B-Instruct-AWQ:/model:ro`
  - the host compose file at `/opt/athanor/vllm/docker-compose.yml` is itself stale and still advertises the older Devstral lane, so this is now a split between implementation truth, host compose residue, and the actually running container rather than a simple repo-only mismatch
  - Athanor source truth is being re-aligned to the live container/runtime evidence first; the remaining live compose correction stays runtime-owned until the packet rerun installs the same Qwen3-coder contract on the host source surface

## Ecosystem Model

### Core platform

Athanor owns:
- control plane
- governance and truth registries
- operator surfaces
- shared platform contracts
- extracted cross-repo infrastructure that clearly belongs under Athanor authority

### Shared platform modules

Reusable subsystems from other repos may become:
- Athanor core modules
- Athanor-owned shared packages
- Athanor-owned scripts or templates

This is decided per subsystem, not per repo slogan.

### Tenant products

Most external product repos default to `light-tenant`:
- separate repo
- separate roadmap
- optional Athanor auth later
- optional dashboard surfacing later
- optional workflows, agents, observability, and deployment help later

### Lineage and archive

Historical repos, evidence workspaces, architecture mines, research stashes, and superseded project lanes stay available for mining, but they do not compete with current Athanor truth.

## Source Inventory

| Source | Role | Default Disposition | Current Program Use |
| --- | --- | --- | --- |
| `C:\Athanor` | `core` | authoritative baseline | landing zone for imports and control docs |
| GitHub `Dirty13itch/athanor` | `core` | authoritative publication line | remote mainline to align before publication |
| `/home/shaun/repos/athanor` on `DEV` | runtime authority | runtime-only | governed outside implementation absorption |
| `C:\Users\Shaun\dev\athanor-next` | `lineage` + incubation | selective import | harvest unique docs and code, then freeze |
| `C:\Reconcile` | `reference` + archive evidence | docs/tooling harvest | import governance findings and preserve the rest |
| `C:\Users\Shaun\dev\Local-System` | `lineage` | deep mine | review by subsystem for platform value |
| `C:\Users\Shaun\dev\local-system-v4` | `lineage reference` | shallow delta mine | check only for residual value not covered elsewhere |
| `C:\Agentic Coding Tools` | shared-module candidate | selective extraction | review route, event, audit, config, and agent-hook subsystems |
| `C:\Users\Shaun\dev\portfolio\agentic-coding-tools` | duplicate evidence root | compare and preserve | pick the richer clone, mark the other as duplicate evidence |
| `C:\Users\Shaun\dev\portfolio\AI-Dev-Control-Plane` | shared-module candidate | selective extraction | category-batch review for control-plane value |
| `C:\Codex System Config` | `operator-tooling` | selective adoption | mine worktree, scaffold, and audit helpers |
| `C:\Users\Shaun\dev\docs` | `reference` | document mine | extract still-true architecture and runbook content |
| `C:\Users\Shaun\dev\reference` | `reference` | research mine | extract MCP, tooling, model, and provider background where useful |
| `C:\CodexBuild\*` | future tenant candidates | tenant queue | register and classify prototypes without merging into core |
| `C:\Field Inspect` and `C:\Field Inspect-*` | tenant family | tenant queue | primary root plus sibling working lanes discovered by the 3-depth `C:\` sweep |
| `C:\RFI & HERS Rater Assistant` plus `C:\CodexBuild\*` variants | tenant family | tenant queue | keep the root-level workspace as the only authority candidate and govern the variants through the duplicate-evidence packet |
| `C:\Brayburn Trails HOA Website`, `C:\Users\Shaun\Ulrich Energy Auditing Website`, `C:\Meds`, and `C:\Sabrina Ulrich Counseling` | governed local product roots | tenant queue | newly governed local roots from the 3-depth `C:\` sweep; Brayburn is now locked as `light-tenant`, while Ulrich Energy, Meds, and Sabrina Ulrich Counseling are locked `standalone-external` |
| `C:\Users\Shaun\dev\quarantine\athanor` | `excluded` | reject | never use as a merge source |

## GitHub Portfolio Operating Model

Every Dirty13itch repo must end in one explicit role:
- `core`
- `shared-module`
- `tenant`
- `lineage`
- `operator-tooling`
- `reference`
- `archive`

Review order:
1. Batch 1: core and lineage
2. Batch 2: shared-module candidates
3. Batch 3: tenant products
4. Batch 4: archive and low-priority edges

The current authoritative portfolio map is tracked in [ATHANOR-ECOSYSTEM-REGISTRY.md](/C:/Athanor/docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md).

Imported baseline from the latest Reconcile governance pass:
- 33 repos inventoried
- 33 reachable clones
- 0 remote-only repos
- 0 open governance-drift entries

Live GitHub verification on 2026-04-07 via `gh repo list Dirty13itch --limit 200` updated that baseline:
- 35 repos currently exist on GitHub
- `Dirty13itch/brayburn-trails-hoa-website` is now confirmed as a live repo with a concrete local root at `C:\Brayburn Trails HOA Website`
- `Dirty13itch/Wan2GP` is a live repo without a confirmed local clone yet
- the live GitHub list, ecosystem markdown, and machine-readable reconciliation registry are now mirrored together through `scripts/sync_github_portfolio_registry.py` and `reports/reconciliation/github-portfolio-latest.json`
- the tenant-family audit at `reports/reconciliation/tenant-family-audit-latest.json` now makes one important portfolio distinction explicit: `Field_Inspect` is a git-backed multi-worktree family, while `RFI & HERS Rater Assistant` currently has one git-backed root plus non-git duplicate-tree variants under `C:\CodexBuild\*`
- the same audit is now paired with artifact-level rulings:
  - `Field_Inspect-operations-runtime` remains the only active selective replay lane because it carries real operations runtime product code and tests, but it must stay governed by the dedicated replay packet and generated report rather than being merged wholesale
  - `Field Inspect-proof-truth` and `Field Inspect-proof-tooling` are now lineage/reference lanes to mine selectively before freeze, not co-equal product branches
  - `Field Inspect-postmark-build` is archive evidence except for a narrow optional Serwist/service-worker replay, `Field Inspect-platform-ops` is lineage/reference for the mobile client seam, and `Field Inspect-mobile-followup` is a freeze-first lane at `+0`
  - `RFI & HERS Rater Assistant` should keep the git-backed root as the only authority candidate; the three `C:\CodexBuild\*` variants are now bounded archive-evidence lanes because their extra feature files are superseded by the root workspace and their remaining distinct value is limited to SQLite and migration artifacts
- `Field_Inspect-operations-runtime` now also has a dedicated execution packet at `docs/operations/FIELD-INSPECT-OPERATIONS-RUNTIME-REPLAY-PACKET.md` plus the generated report `reports/reconciliation/field-inspect-operations-runtime-replay-latest.json`, so the surviving replay lane is governed by a file-bucketed packet with live `execution_posture` instead of branch-name prose alone
- the safe operations-runtime tranche is now materially present in a dedicated review worktree at `C:\Field Inspect-ops-safe-review` on branch `codex/replay-operations-runtime-safe`, where `npm run typecheck` plus the targeted replay tests passed without touching the dirty primary root
- that same `Field Inspect` tranche is now also replayed into the real authority root at `C:\Field Inspect`; `npm run typecheck` and the packet's targeted replay test bundle passed there on 2026-04-07, so the surviving open work is the shared-project/report-delivery second tranche plus sibling-lane freeze follow-through rather than the safe operations landing itself
- `RFI & HERS Rater Assistant` now also has a dedicated duplicate-evidence packet at `docs/operations/RFI-HERS-DUPLICATE-EVIDENCE-PACKET.md` plus the generated report `reports/reconciliation/rfi-hers-duplicate-evidence-packet-latest.json`, so the duplicate-tree variants are governed as bounded archive evidence instead of prose-only archive notes
- `C:\RFI & HERS Rater Assistant` now also has a dedicated primary-root stabilization packet at `docs/operations/RFI-HERS-PRIMARY-ROOT-STABILIZATION-PACKET.md` plus the generated report `reports/reconciliation/rfi-hers-primary-root-stabilization-latest.json`, so the remaining dirty repo-backed root is governed by explicit data/script/workbook/doc tranches instead of staying an unstructured product blocker
- the shared preservation baseline at `reports/reconciliation/preservation-latest.json` now also captures the dirty `C:\RFI & HERS Rater Assistant` root before later stabilization work mutates it
- the first four RFI stabilization tranches are now materialized in a dedicated review worktree at `C:\RFI & HERS Rater Assistant-stabilization-review` on branch `codex/stabilize-settlers-ridge-root`, and the same branch validates cleanly from the safe mirror path `C:\CodexBuild\rfi-hers-stabilization-review`
- the review-branch-only RFI fix slice is now landed into the authority root as well: `scripts/db-seed.ts`, `src/features/unit-types/library.ts`, and `tests/domain-validation.test.ts` now match the validated stabilization branch, `python scripts/validate_settlers_ridge_packet.py` passes in the root, and `scripts/codex/validate-safe.ps1` remains the governed validation lane while the spaced workspace still lacks a usable local Node toolchain
- `Dirty13itch/Wan2GP` now also has a dedicated remote-only watch packet at `docs/operations/WAN2GP-REMOTE-ONLY-WATCH-PACKET.md` plus `reports/reconciliation/wan2gp-remote-only-watch-latest.json`, so the no-clone state is governed explicitly until a real local working root appears
- the remaining open GitHub role rows are now closed as well: `Local-System` is locked lineage, `hydra`/`kaizen`/`system-bible` are locked as remote-only lineage references at their currently missing recorded reference paths, `agentic-coding-tools` is locked as the active shared-module candidate with `C:\Agentic Coding Tools` as the primary review root, `AI-Dev-Control-Plane` is locked as operator-tooling lineage/reference, and `airtight-iq-dl-forecasting-engine` plus `To-Do` are locked archive-only
- portfolio classification is now effectively complete across all 35 live Dirty13itch repos; the remaining reconciliation work is execution, preservation, extraction, and runtime-owned repair rather than more open-ended repo-role triage
- Athanor's own verification loop is now tighter as part of the reconciliation closure: `projects/dashboard/scripts/ensure-completion-audit.mjs` and the `pretest:e2e:audit` hook make the dashboard Playwright audit self-preparing, and the shared bootstrap test harness now reuses seeded bootstrap fixtures so the slow agent bootstrap suites no longer reseed the entire world per test file

## Implementation Phases

### Phase 0: Expanded discovery freeze

- register all known local roots and relevant portfolio sources
- run the maintained three-depth `C:\` discovery sweep to catch top-level and near-root product families outside the original Athanor/Reconcile set
- map duplicate clones and excluded roots
- establish one review root per meaningful repo

### Phase 1: Preservation baseline

- capture Git state or filesystem evidence for every non-authoritative source with unique value
- preserve `athanor-next`, `C:\Reconcile`, `Local-System`, `Agentic Coding Tools`, and `Codex System Config` before deeper harvesting

### Phase 2: Canonical alignment

- fetch `origin`
- align local Athanor work to current `origin/main` before publication
- do not publish from stale local history

### Phase 3: Mandatory core absorption

- mine `athanor-next`
- harvest `C:\Reconcile`
- move still-valid findings into Athanor-owned truth and queue remaining source-specific work

### Phase 4: Lineage and shared-module review

- review `Local-System`, `local-system-v4`, `Agentic Coding Tools`, and `AI-Dev-Control-Plane` by subsystem
- queue concrete extraction work instead of promising broad future consolidation

### Phase 5: Operator tooling review

- review `Codex System Config` and related operator docs/scripts
- adopt only Athanor-relevant workflow and scaffolding value

### Phase 6: Knowledge stash mining

- mine `dev\docs` and `dev\reference`
- promote only current, verified, non-duplicative material

### Phase 7: GitHub category-batch review

- confirm batch-level repo roles with Shaun
- move repos into `tenant`, `shared-module`, `lineage`, or `archive` deliberately

### Phase 8: Shared extraction planning

- turn reusable subsystems into explicit extraction work items
- define destination, validation, and blockers per subsystem

### Phase 9: Tenant architecture planning

- lock default tenant depth and required integrations per tenant candidate

### Phase 10: Truth-layer normalization

- keep registries, queues, lifecycle entries, and startup docs aligned

### Phase 11: Phased publication

Checkpoint order:
1. discovery, preservation, registry, and control-doc foundation
2. `athanor-next` and `C:\Reconcile` harvest
3. lineage and shared-module landings
4. operator-tooling and stash-mining landings
5. ecosystem registry, tenant queue, and extraction queue consolidation
6. freeze and cleanup

## Validation

Per checkpoint:
- update the source registry and reconciliation ledger
- update ecosystem or queue docs when the decision surface changes
- run `python scripts/generate_documentation_index.py`
- run `python scripts/validate_platform_contract.py`

Subsystem-specific imports still require the smallest useful project-level tests before they are called complete.

## Guardrails

- Do not merge side roots wholesale.
- Do not publish from a stale local head when GitHub has newer commits.
- Do not let `athanor-next`, `C:\Reconcile`, `Local-System`, or any product clone compete with `C:\Athanor`.
- Do not confuse runtime authority with implementation authority.
- Do not leave GitHub portfolio repos in an ambiguous “maybe important” state once they have been reviewed.
