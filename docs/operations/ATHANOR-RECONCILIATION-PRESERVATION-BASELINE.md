# Athanor Reconciliation Preservation Baseline

Last updated: 2026-04-06

## Purpose

Capture the current state of the mandatory non-authoritative source roots before deeper reconciliation imports or cleanup.

This file is preservation evidence, not the final preservation artifact. A source marked `snapshot required` here still needs its full branch, diff-manifest, or filesystem archive work completed before freeze or destructive cleanup.

Use `python scripts/capture_reconciliation_preservation.py` to refresh the machine-readable snapshot at `reports/reconciliation/preservation-latest.json`.

## Mandatory Baseline

| Source root | Git state | Working-tree state | Current evidence captured | Next preservation action |
| --- | --- | --- | --- | --- |
| `C:\Users\Shaun\dev\athanor-next` | branch `codex/vault-ssh-key-default`, unique commits `2fd649b` and `f43bf0c` over `origin/main` | dirty tracked files: `.serena/project.yml`, `AGENTS.md` | unique commit list, changed-file list, imported continuity-doc slice | capture diff manifest and preservation ref before freeze work |
| `C:\Reconcile` | git repo with no commits on `master` | entire workspace uncommitted; current file census observed `186288` files under the workspace | key governance docs already read into Athanor control docs | create dated filesystem archive plus manifest and checksums |
| `C:\Users\Shaun\dev\Local-System` | `main` at `bb3b95d` | untracked files: `nul`, `performers.json` | current branch, head commit, and working-tree residue recorded here | capture diff manifest and preservation ref before subsystem harvest |
| `C:\Agentic Coding Tools` | `main` at `6af5c83`, tracking `origin/main` | untracked file: `AGENTS.md` | current branch, head commit, repo identity, and package surface recorded here | choose primary review clone versus portfolio clone, then capture preservation ref |
| `C:\Users\Shaun\dev\portfolio\agentic-coding-tools` | `main` at `6af5c83`, tracking `origin/main` | clean working tree | duplicate clone compared against `C:\Agentic Coding Tools`; same observed head commit | keep as preservation duplicate after primary review root is chosen |
| `C:\Users\Shaun\dev\portfolio\AI-Dev-Control-Plane` | `main` at `24994a7`, tracking `origin/main` | untracked file: `AGENTS.md` | current branch, head commit, README posture, and local-first MVP scope recorded here | capture dirty diff manifest before any shared-module or tenant extraction decision |
| `C:\Codex System Config` | `main` at `8a0afff` | tracked modifications: `AGENTS.md`, `PROJECT.md`, `README.md`, `STATUS.md`, `docs/CODEX-FEATURE-MATRIX.md`, `docs/CODEX-HOME-AUDIT-LATEST.md`, `docs/CODEX-NEXT-STEPS.md`, `docs/CORE-ROLLOUT-STATUS.md`, `templates/repo-local/AGENTS-template.md`; untracked files: `docs/CONTEXTUAL-ROUTING-MODEL.md`, `docs/WORKTREE-LANE-OPERATING-MODEL.md`, `docs/WORKTREE-LANES-LATEST.md`, `scripts/audit-worktree-lanes.ps1`, `scripts/new-codex-worktree.ps1` | current branch, head commit, and dirty-file posture recorded here | capture dirty diff manifest before selective tooling adoption |

## Additional Candidate Roots

| Source root | Current state | Reason tracked |
| --- | --- | --- |
| `C:\Users\Shaun\dev\local-system-v4` | non-canonical lineage reference | likely shallow delta source behind `Local-System` |
| `C:\Users\Shaun\dev\portfolio\agentic-coding-tools` | duplicate clone of `agentic-coding-tools` | must be compared against `C:\Agentic Coding Tools` before freezing one as duplicate evidence |
| `C:\Users\Shaun\dev\portfolio\AI-Dev-Control-Plane` | Batch 2 shared-module candidate | likely reusable control-plane value |
| `C:\Users\Shaun\dev\docs` | document stash | mine for current architecture and runbook content only |
| `C:\Users\Shaun\dev\reference` | research stash | mine for MCP, provider, and tooling background only |
| `C:\CodexBuild\*` | prototype roots | tracked as future tenant candidates, not core merge material |

## Rules

- Do not call a source preserved just because it has been inspected.
- No freeze or cleanup action should happen until the preservation action in this baseline is complete for that source.
- Artifact-level imports should be logged in `ATHANOR-RECONCILIATION-LEDGER.md` as they land.
