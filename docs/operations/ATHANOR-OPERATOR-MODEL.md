# Athanor Operator Model

Do not edit manually.


## Front Door Sequence

| Order | Surface | Purpose | Use When |
| --- | --- | --- | --- |
| `1` | `/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md` | Volatile adopted-system feed for current work, queue posture, and recent activity without repo-tracked churn. | First read for daily operation. |
| `2` | `/mnt/c/Athanor/docs/operations/STEADY-STATE-STATUS.md` | Durable operator contract defining intervention levels, reopen triggers, and proof paths. | You want the stable operating contract rather than the live ticker. |
| `3` | `/mnt/c/Athanor/docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md` | Cross-system execution spine covering Athanor, devstack, substrate, operator-local, providers, and approval gates. | You need the full ecosystem picture without dropping into raw JSON. |
| `4` | `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` | Current build/proving queue and explicit deferred operator inputs. | You want to know what the next promotion or activation lane is. |
| `5` | `/mnt/c/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md` | Detailed proving-readiness, turnover posture, and pilot evidence. | You need readiness detail before a pilot or promotion move. |
| `6` | `/mnt/c/Codex System Config/docs/CORE-ROLLOUT-STATUS.md` | Operator-local Codex control-plane health across the mandatory rollout set. | Local workstation or Codex control-plane posture may be the blocker. |
| `7` | `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json` | Machine proof for closure state and repo-safe debt counts. | You need proof rather than summary. |
| `8` | `/mnt/c/Athanor/reports/ralph-loop/latest.json` | Machine proof for the current claim, queue state, and Ralph loop posture. | You are debugging the control loop itself. |

## Attention Levels

| Level | Meaning | Operator Expectation |
| --- | --- | --- |
| `No action needed` | Athanor core is green and the system can continue without intervention. | Read the front door only; no action unless you are intentionally activating a new lane. |
| `Review recommended` | Something reopened or drifted, but it is not yet a hard stop. | Review the current work and next handoff before approving new breadth. |
| `Approval required` | A packet, credential gate, or bounded runtime mutation explicitly needs Shaun. | Approve or deny the specific gate; do not treat it as generic system uncertainty. |
| `System attention required` | A typed stop, validator break, or runtime breakage surfaced. | Pause expansion, work the active fault, then regenerate truth surfaces. |

## Intervention Triggers

- runtime-packet inbox rises above zero
- finish-scoreboard leaves repo_safe_complete or typed_brakes_only
- Ralph surfaces a typed stop state
- provider or host posture invalidates an active lane
- a deferred operator input is intentionally being activated

## Ambient Rules

- Current work, next up, and whether Shaun is needed must be visible without reading raw JSON.
- Outside-system blockers must surface on the operator-facing docs, not only in machine artifacts.
- Recent changes should be summarized from Ralph or atlas activity rather than requiring forensic digging.

## Deep Proof Surfaces

- `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- `/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json`
- `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`

## Review Ritual

- Read the live operator feed first.
- Read the ecosystem master plan when work spans more than Athanor core.
- Check the forge board before treating a devstack lane as next.
- Use atlas and machine JSON only when you need proof or to resolve contradiction.
