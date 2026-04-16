# Session Restart Runbook

Use this when a fresh Codex or operator session needs to re-enter Athanor quickly without rebuilding context from scratch.

## Fast Path

1. Run `python scripts/session_restart_brief.py --refresh`.
   This helper must surface `selected_workstream`, `active_claim_task`, `current_stop_state`, the next deferred publication family, and the COO brief sections `Program State`, `Landed / Delta`, `Proof`, `Risks`, `Delegation`, `Next Moves`, and `Decision Needed` from live artifacts.
2. Trust the brief's canonical docs and live artifacts before any older narrative or chat memory.
3. If the restart lane is source-heavy, prefer `python scripts/refresh_validation_publication_loop.py` to refresh documentation, truth-inventory, publication, validation, Ralph, and steady-state status surfaces in one pass before landing a real tranche.
4. For post-closure monitoring, use `python scripts/run_steady_state_control_plane.py` as the canonical ordered control-plane pass.
4. If the next queued tranche is a burn-class lane, inspect it directly with `python scripts/preflight_burn_class.py local_bulk_sovereign --json` (or the relevant burn class id) before changing queue-facing source truth. Prefer the generated `reports/truth-inventory/next-rotation-preflight.json` artifact when it is present so the on-deck handoff stays report-backed.
5. If the restart lane is runtime- or autonomy-heavy, open the live control surfaces immediately:
   - `https://athanor.local/`
   - `https://athanor.local/operator`
   - `https://athanor.local/routing`
   - `https://athanor.local/topology`

## What The Brief Must Answer

- What is the current Ralph loop mode?
- What is the top ranked workstream right now?
- What is the active claim task right now?
- What is the current stop state, if any?
- What changed on the last material tranche?
- What proof is currently green?
- What are the top active risks?
- What stays local versus what can be delegated?
- What runs next if no typed brake appears?
- Is the provider gate complete?
- Is the work economy ready or blocked?
- Is governed dispatch already holding a claim?
- Are harvest slots actually open?
- How dirty is the repo right now?
- Which docs are canonical for this session?

If the brief cannot answer those questions from live artifacts, fix the artifact or the helper before trusting any broader narrative.
When the on-deck candidate is a burn-class lane, the live `reports/truth-inventory/next-rotation-preflight.json` artifact should already summarize routing chain, reserve rule, queue posture, and proof surface before rotation.

## COO Brief Contract

The restart brief is not just orientation prose. It is the operator-facing condensation of the live Ralph executive state.

Each material tranche must surface these sections from live artifacts:
- `Program State`
- `Landed / Delta`
- `Proof`
- `Risks`
- `Delegation`
- `Next Moves`
- `Decision Needed`

If any of those sections are missing, stale, or contradictory, treat that as a control-plane bug and fix the artifact or helper before trusting the session handoff.

## Canonical Restart Order

1. `STATUS.md`
2. `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
3. `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
4. `docs/operations/REPO-STRUCTURE-RULES.md`
5. `reports/ralph-loop/latest.json`
6. `reports/truth-inventory/ralph-continuity-state.json`
7. `reports/truth-inventory/governed-dispatch-state.json`
8. `reports/truth-inventory/next-rotation-preflight.json`
9. `C:\athanor-devstack\reports\master-atlas\latest.json`
10. `reports/truth-inventory/finish-scoreboard.json`
11. `reports/truth-inventory/runtime-packet-inbox.json`

## Finish Surfaces

Treat these as the canonical closure-status pair:
- `reports/truth-inventory/finish-scoreboard.json` answers `are we still closing repo-safe work or are only typed brakes left?`
- `reports/truth-inventory/runtime-packet-inbox.json` answers `which approval-gated runtime packets are decision-complete right now?`

If the restart brief, Ralph, or operator prose disagrees with those artifacts, fix the generator or report layer before trusting the narrative.

## Rules

- Runtime truth outranks memory.
- Registry and generated-artifact truth outrank stale prose.
- If `STATUS.md`, Ralph, Ralph continuity, governed dispatch, and the atlas disagree, the disagreement is the first bug to close.
- Ralph continues until a typed brake, not until a green check.
- Show `active_claim_task` as the current execution target and `selected_workstream` as strategic context.
- If the last dispatch lane is verified repo-side no-delta, rotate to the next tranche instead of sticky-reclaiming the same workstream.
- Dispatch closure reopens only on dispatch-scoped repo delta; validation and publication reopens on any material repo delta.
- If workstreams are continuity-suppressed, prefer the highest-ranked `cash_now` deferred publication family before generic burn-class posture.
- `finish-scoreboard.json` is the canonical `are we done yet?` answer for repo-safe closure.
- `STEADY-STATE-STATUS.md` is the operator-facing answer to `did core completion reopen, and what do I do next?`.
- `runtime-packet-inbox.json` stays visible in restart surfaces, but runtime packets remain approval-gated until explicitly approved.
- Automatic steady-state refresh covers Ralph, the restart brief inputs, and truth/report regeneration needed to keep queue truth honest.
- Publication triage, deferred-family recounting, and burn-class preflight generation remain source-drift-driven rather than always-on.
- Runtime host reconfiguration, secret/config mutation on live nodes, and destructive cleanup outside governed prune policy remain approval-gated.
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
