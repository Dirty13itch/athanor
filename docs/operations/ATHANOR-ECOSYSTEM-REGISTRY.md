# Athanor Ecosystem Registry

Last updated: 2026-04-07

## Purpose

This registry is the portfolio-wide map for the Dirty13itch GitHub ecosystem under the Athanor program.

It does not replace `docs/projects/PORTFOLIO-REGISTRY.md`.
- `docs/projects/PORTFOLIO-REGISTRY.md` covers Athanor in-repo maturity classes.
- this file covers the wider GitHub portfolio and each repo's intended relationship to Athanor

Current entries are seeded from `C:\Reconcile\docs\GITHUB_REPO_REGISTRY.md` and then reclassified into the Athanor ecosystem model.

## Imported Baseline

Imported from the latest Reconcile GitHub governance pass, then live-checked on 2026-04-07 with `gh repo list Dirty13itch --limit 200`:

| Metric | Value |
| --- | --- |
| Reconcile-era repos inventoried | 33 |
| Live repos on 2026-04-07 | 35 |
| Repos added since Reconcile | 2 (`Dirty13itch/Wan2GP`, `Dirty13itch/brayburn-trails-hoa-website`) |
| Repos without confirmed local clone | 1 (`Dirty13itch/Wan2GP`) |
| Machine-readable GitHub mirror | `config/automation-backbone/reconciliation-source-registry.json` `github_portfolio` plus `reports/reconciliation/github-portfolio-latest.json` |

Current classification baseline from that pass:
- 1 `core` repo
- 1 `shared-module` repo
- 1 `operator-tooling` repo
- 26 `tenant` repos
- 4 `lineage` repos
- 2 `archive` repos

## Operating Rules Imported From Reconcile

- Keep quarantined or malformed roots out of reconciliation selection.
- Treat the current portfolio baseline as normalized governance, not as permission to ignore repo-by-repo role decisions.
- Use steady-state audits to detect drift before reopening a remediation lane.
- Do not reopen PR or branch cleanup as a portfolio-wide task unless new drift appears.

## Role Definitions

- `core`: belongs inside Athanor's implementation and truth layer
- `shared-module`: likely source of reusable platform value
- `tenant`: separate product repo that may be operated under Athanor
- `lineage`: historical architecture or design line to mine, not revive
- `archive`: retain only for history or recovery

## Tenant Defaults

Unless a repo clearly needs deeper coupling, a tenant defaults to `light-tenant`:
- separate repo ownership
- separate roadmap
- dashboard visibility optional
- workflows and agents optional
- observability and deployment help optional
- shared auth optional later

`Depends on Athanor` means current hard dependency, not future possibility.

## Batch 1: Core And Lineage

| Repo | Working clone | Current maturity | Proposed role | Likely tenant status | Shared extraction potential | Depends on Athanor | Athanor depends on it | Batch | Shaun decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Dirty13itch/athanor` | `C:\Athanor` | canonical | `core` | n/a | high | n/a | n/a | Batch 1 | locked |
| `Dirty13itch/Local-System` | `C:\Users\Shaun\dev\Local-System` | historical lineage with a substantial local predecessor tree still present for subsystem mining | `lineage` | n/a | high | no | lineage only | Batch 1 | locked 2026-04-07 |
| `Dirty13itch/hydra` | `/home/shaun/repos/reference/hydra` | historical lineage reference repo; current recorded reference path is missing locally, so treat it as remote-only lineage until a live clone reappears | `lineage` | n/a | medium | no | lineage only | Batch 1 | locked 2026-04-07 |
| `Dirty13itch/kaizen` | `/home/shaun/repos/reference/kaizen` | historical lineage reference repo; current recorded reference path is missing locally, so treat it as remote-only lineage until a live clone reappears | `lineage` | n/a | medium | no | lineage only | Batch 1 | locked 2026-04-07 |
| `Dirty13itch/system-bible` | `/home/shaun/repos/reference/system-bible` | historical lineage reference repo; current recorded reference path is missing locally, so treat it as remote-only lineage until a live clone reappears | `lineage` | n/a | medium | no | lineage only | Batch 1 | locked 2026-04-07 |

## Batch 2: Shared-Module Candidates

| Repo | Working clone | Current maturity | Proposed role | Likely tenant status | Shared extraction potential | Depends on Athanor | Athanor depends on it | Batch | Shaun decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Dirty13itch/agentic-coding-tools` | `C:\Agentic Coding Tools` plus preservation duplicate `C:\Users\Shaun\dev\portfolio\agentic-coding-tools` | active separate control-plane tooling workspace with executable route, event, audit, config, and agent-hook surfaces | `shared-module` | n/a | high | no | candidate extraction | Batch 2 | locked 2026-04-07 |
| `Dirty13itch/AI-Dev-Control-Plane` | `C:\Users\Shaun\dev\portfolio\AI-Dev-Control-Plane` | local-first static MVP for provider posture, task dispatch, and result review; retain as operator-tooling lineage/reference unless a future fixture slice is explicitly extracted | `operator-tooling` | n/a | low | no | no | Batch 2 | locked 2026-04-07 |

## Batch 3: Tenant Products

| Repo | Working clone | Current maturity | Proposed role | Likely tenant status | Shared extraction potential | Depends on Athanor | Athanor depends on it | Batch | Shaun decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Dirty13itch/amanda-med-tracker` | `C:\Meds` | active separate product with concrete local root | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/AuditForecaster` | `C:\Users\Shaun\dev\portfolio\AuditForecaster` | active separate product with normalized portfolio root, nested Next.js app, and product-owned Unraid/preview deployment stack | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/BKI-Tracker` | `C:\Users\Shaun\dev\portfolio\BKI-Tracker` | active separate product with workbook-first operator contract and validation tooling | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/BKI-Tracker---Calendar-reconciler` | `C:\Users\Shaun\dev\portfolio\BKI-Tracker---Calendar-reconciler` | active separate product as a local Windows calendar-to-workbook utility | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Buffalog` | `C:\Users\Shaun\dev\portfolio\Buffalog` | active separate product as a local-only wrap-review tracker with static hosting posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/brayburn-trails-hoa-website` | `C:\Brayburn Trails HOA Website` | active separate product with concrete local root, repo-owned Next.js app, VAULT mirror, secret bridge, and infra contracts for Discourse plus Terraform | `tenant` | `light-tenant` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/buff-wrap-inspector` | `C:\Users\Shaun\dev\portfolio\buff-wrap-inspector` | active separate product as a local-first wrap scorecard with Spark/local persistence | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/curator-media-magic` | `C:\Users\Shaun\dev\portfolio\curator-media-magic` | active separate product as a self-contained media manager with optional Plex/Stash integrations | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/darkweb-tools-directory` | `C:\Users\Shaun\dev\portfolio\darkweb-tools-directory` | active separate product as a self-contained research catalog with its own full-stack runtime | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Favorites` | `C:\Users\Shaun\dev\portfolio\Favorites` | active separate product as a local-first favorites organizer with static-host-ready posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Field_Inspect` | primary root `C:\Field Inspect` plus six sibling git worktree lanes under `C:\Field Inspect-*` | active separate product with one dirty primary workspace, one selective replay lane (`operations-runtime`), and the rest classified toward lineage/freeze/archive | `tenant` | `light-tenant` | medium | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Gaming-Ideas` | `C:\Users\Shaun\dev\portfolio\Gaming-Ideas` | active separate product with local app/runtime, rich project-doc corpus, and product-domain Canon Vault references that stay outside Athanor | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/lawn-signal` | `C:\LawnSignal` | active separate product with a concrete Next.js web root, Expo mobile shell, and governed nationwide companion tranche proof | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-21 |
| `Dirty13itch/mood-compass-whisperer` | `C:\Users\Shaun\dev\portfolio\mood-compass-whisperer` | active separate product as a local-first mood tracker with static preview posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/nvidia-gpu-comparison` | `C:\Users\Shaun\dev\portfolio\nvidia-gpu-comparison` | active separate product with local planning-app runtime and Kaizen-oriented hardware research corpus | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/performer-database-app` | `C:\Users\Shaun\dev\portfolio\performer-database-app` | active separate product as a local-first performer exploration app with optional Stash integration | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Reverie` | `C:\Users\Shaun\dev\portfolio\Reverie` | active separate product as a private-first local journal with optional Gemini insight generation | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/reverie-dream-journal` | `C:\Users\Shaun\dev\portfolio\reverie-dream-journal` | active separate product as a local-first reflective journal PWA with optional Gemini analysis | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/sabrina-therapy-blueprint` | `C:\Users\Shaun\dev\portfolio\sabrina-therapy-blueprint` | active separate product as a local-first therapy practice site MVP with browser-local intake flow | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/savor-street-symphony` | `C:\Users\Shaun\dev\portfolio\savor-street-symphony` | active separate product as a local/static food-truck discovery scaffold with preview posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/stash-explorer` | `C:\Users\Shaun\dev\portfolio\stash-explorer` | active separate product as a self-contained Stash command center with Python AI backend and local/containerized deployment posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/subcontractor-snap` | `C:\Users\Shaun\dev\portfolio\subcontractor-snap` | active separate product as a local-first field-capture MVP with preview posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/truck-trail-finder-app` | `C:\Users\Shaun\dev\portfolio\truck-trail-finder-app` | active separate product as a broader food-truck platform scaffold with local/static preview posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/ulrich-energy-auditing` | `C:\Users\Shaun\dev\portfolio\ulrich-energy-auditing` | active separate product as a local-first Python audit workbench with CLI report generation | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/ulrich-energy-website` | `C:\Users\Shaun\Ulrich Energy Auditing Website` | active separate product with concrete local website root and self-contained hosting/monitoring surfaces | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/Wan2GP` | no confirmed local clone yet; targeted 3-depth `C:\` sweep found only Athanor research/docs references and downloaded model files | active separate product | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |
| `Dirty13itch/website-app` | `C:\Users\Shaun\dev\portfolio\website-app` | active separate product with repo-backed content and static-host-ready portfolio-shell posture | `tenant` | `standalone-external` | low | no | no | Batch 3 | locked 2026-04-07 |

## Local-Only Tenant Candidates From The C Drive Sweep

| Root | Current maturity | Proposed role | Likely tenant status | Shared extraction potential | Related GitHub repo | Batch | Shaun decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `C:\RFI & HERS Rater Assistant` | active local internal field-ops workspace with one git-backed primary root and non-git variant roots under `C:\CodexBuild\*`; duplicate variants are now preserved archive evidence rather than parallel authorities and are governed by the dedicated duplicate-evidence packet | `tenant` | `incubating-tenant` | medium | none confirmed yet | Batch 3 | locked 2026-04-07 |
| `C:\Sabrina Ulrich Counseling` | active local website workspace with deployment residue | `tenant` | `standalone-external` | low | none confirmed yet | Batch 3 | locked 2026-04-07 |

## Batch 4: Archive And Low-Priority Edges

| Repo | Working clone | Current maturity | Proposed role | Likely tenant status | Shared extraction potential | Depends on Athanor | Athanor depends on it | Batch | Shaun decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Dirty13itch/airtight-iq-dl-forecasting-engine` | `C:\Users\Shaun\dev\archive\airtight-iq-dl-forecasting-engine` | archive candidate with local forecasting engine source preserved under the archive lane | `archive` | n/a | low | no | no | Batch 4 | locked 2026-04-07 |
| `Dirty13itch/To-Do` | `C:\Users\Shaun\dev\archive\github-old\To-Do` | archive candidate with preserved Vite/React artifact history only | `archive` | n/a | low | no | no | Batch 4 | locked 2026-04-07 |

## Notes

- The shared-module and tenant classifications are starting defaults, not final irreversible assignments.
- Any repo can move between `tenant`, `shared-module`, `lineage`, or `archive` after batch review if the facts support it.
- Product code stays in its own repo unless there is a concrete reason to extract shared platform value into Athanor.
- The 2026-04-07 three-depth `C:\` sweep confirmed that several tenant families have richer live local roots than the older portfolio-clone assumptions captured in Reconcile-era inventory.
- The live GitHub portfolio and this markdown registry are now mirrored into `reconciliation-source-registry.json` and `reports/reconciliation/github-portfolio-latest.json`, so repo-count and role drift can be validator-enforced instead of living only in prose.
- The tenant-family audit at `reports/reconciliation/tenant-family-audit-latest.json` now distinguishes git-backed sibling worktree families such as `Field_Inspect` from non-git duplicate-tree families such as `RFI & HERS Rater Assistant`.
- Artifact-level review is now explicit for the two highest-noise tenant families: `Field_Inspect-operations-runtime` is the only surviving selective replay lane, while `Field Inspect-proof-truth`, `Field Inspect-proof-tooling`, `Field Inspect-platform-ops`, and `Field Inspect-postmark-build` are no longer treated as co-equal product branches, and the `C:\CodexBuild\*` `RFI` variants are preserved archive evidence under the dedicated duplicate-evidence packet rather than shadow roots.
