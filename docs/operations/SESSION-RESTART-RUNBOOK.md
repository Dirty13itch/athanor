# Session Restart Runbook

Use this when a fresh Codex or operator session needs to re-enter Athanor quickly without rebuilding context from scratch.

## Fast Path

1. Run `python scripts/session_restart_brief.py --refresh`.
2. Trust the brief's canonical docs and live artifacts before any older narrative or chat memory.
3. If the restart lane is source-heavy, run `python scripts/validate_platform_contract.py` before landing a real tranche.
4. If the restart lane is runtime- or autonomy-heavy, open the live control surfaces immediately:
   - `https://athanor.local/`
   - `https://athanor.local/operator`
   - `https://athanor.local/routing`
   - `https://athanor.local/topology`

## What The Brief Must Answer

- What is the current Ralph loop mode?
- What is the top ranked workstream right now?
- Is the provider gate complete?
- Is the work economy ready or blocked?
- Is governed dispatch already holding a claim?
- Are harvest slots actually open?
- How dirty is the repo right now?
- Which docs are canonical for this session?

If the brief cannot answer those questions from live artifacts, fix the artifact or the helper before trusting any broader narrative.

## Canonical Restart Order

1. `STATUS.md`
2. `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
3. `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
4. `docs/operations/REPO-STRUCTURE-RULES.md`
5. `reports/ralph-loop/latest.json`
6. `reports/truth-inventory/governed-dispatch-state.json`
7. `C:\athanor-devstack\reports\master-atlas\latest.json`

## Rules

- Runtime truth outranks memory.
- Registry and generated-artifact truth outrank stale prose.
- If `STATUS.md`, Ralph, governed dispatch, and the atlas disagree, the disagreement is the first bug to close.
- Do not restart from `MEMORY.md`, archived docs, or chat recap when live artifacts disagree.
- Do not let restart drift recreate shadow authority in `services/`, `projects/reports/`, `athanor-next`, or `athanor-devstack`.

## Deep Path

Use this when the restart lane is likely to mutate runtime truth, publication slices, or packet-backed ownership.

1. Run `python scripts/session_restart_brief.py --refresh`.
2. Run `python scripts/validate_platform_contract.py`.
3. Read the generated operations report most relevant to the lane you are about to touch.
4. If the lane spans runtime ownership, provider posture, or packet review, use the generated report and packet surface before changing code.
5. Re-run the smallest useful validation after the first change instead of stacking blind edits.

## Publication Restart

Use this when the new session is supposed to get work onto GitHub.

1. Start with `git status -sb`, not with staging.
2. Treat the current branch state and the current dirty worktree as separate facts:
   - the branch may already be pushed
   - the local modified and untracked tranche may still be completely unpublished
3. Triage publication candidates by slice before touching the index:
   - control-plane and registry truth
   - agent-runtime and queue truth
   - dashboard and control-surface work
   - gpu-orchestrator and capacity substrate
   - generated reports and ledgers
4. Exclude workstation-local or incidental residue unless the session proves it belongs in source truth.
5. Only stage after the slice boundary is clear enough that the commit message would still make sense a week later.

## Why This Exists

The repo already had the truth, but it was spread across very large docs, JSON artifacts, dashboard surfaces, and runtime reports. The restart brief collapses that into one current posture read so a new session can pick up the real top lane instead of re-solving orientation every time.
