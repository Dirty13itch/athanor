# Archived: 2026-04-19 Athanor Blocker Closure Program Implementation Plan

> Authority class: archive reference only.
> Superseded by live truth surfaces under `reports/truth-inventory/`, `reports/ralph-loop/latest.json`, `docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`, and `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`.
> Reason: this plan captured a temporary runtime-parity and result-credit recovery state that no longer reflects the current closure posture.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the live Athanor blocker set by restoring runtime parity, forcing governed result-credit onto the active capacity lane, reestablishing validator and contract-healer freshness, and starting a new healthy continuity streak that can accumulate the stable operating day.

**Architecture:** Treat this as a four-lane program with one strict dependency: runtime adoption and parity first, then live result-credit and validator/publication closure on the adopted runtime, then continuity streak accumulation. Do not try to solve publication, runtime adoption, and GitHub publication at the same time; the runtime authority must converge first so the live system stops executing the old no-proof path.

**Tech Stack:** Python scripts under `scripts/`, Athanor agent runtime under `projects/agents/src/athanor_agents/`, JSON truth surfaces under `reports/truth-inventory/`, DEV runtime authority at `/home/shaun/repos/athanor`, FOUNDRY proof workspace under `/opt/athanor`.

---

## Live Truth Snapshot

- `reports/truth-inventory/runtime-parity.json` is `repo_drift`:
  - DESK: `c11b1fd18505ae9f55436b0e4472ede046bec402`, dirty
  - DEV: `db01a464ce4c6f959bea699f8205ac40857f2f96`, dirty
  - FOUNDRY manifest unavailable
- `audit/automation/contract-healer-latest.json` is red on stale generated docs.
- `reports/ralph-loop/latest.json` says `validation.ran=false`, `validation_summary="Validation has not been materialized for this Ralph pass yet."`
- `reports/truth-inventory/stable-operating-day.json` is `0.0h`.
- `/v1/tasks/68fc590996b8` completed with `proof_commands=null` and `verification_status=missing_evidence`.
- `/v1/operator/backlog?limit=200` shows `backlog-2caafa26` blocked on `verification_evidence_missing`.

## Program Rules

- Runtime authority outranks local patch confidence. A fix is not live until DEV is running it.
- No new automations until the fixed-point chain and result-credit lane are trustworthy again.
- Use narrow runtime-adoption slices. Do not publish or deploy the whole dirty DESK tree.
- Delta-only operator reporting:
  - runtime parity
  - validator/contract-healer
  - result-evidence ledger
  - continuity health/stable-day start
  - blocker-map proof-gate changes

### Task 1: Runtime Parity Recovery And Runtime Adoption

**Files:**
- Verify: `/mnt/c/Athanor/scripts/write_runtime_parity.py`
- Verify: `/mnt/c/Athanor/scripts/proof_workspace_contract.py`
- Verify: `/mnt/c/Athanor/scripts/deploy-agents.sh`
- Inspect on DEV: `/home/shaun/repos/athanor`
- Inspect on FOUNDRY: `/opt/athanor`

- [ ] **Step 1: Prove the current parity failure on DESK**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/write_runtime_parity.py --json
git rev-parse HEAD
git status --short -- scripts/write_runtime_parity.py scripts/proof_workspace_contract.py \
  projects/agents/src/athanor_agents/operator_work.py \
  projects/agents/src/athanor_agents/tasks.py \
  projects/agents/src/athanor_agents/supervisor.py \
  projects/agents/src/athanor_agents/autonomous_queue.py \
  scripts/run_ralph_loop_pass.py \
  scripts/run_steady_state_control_plane.py \
  scripts/run_continuity_supervisor.py
```

Expected:
- `drift_class=repo_drift`
- DESK commit differs from DEV commit
- The blocker-closure slice is identifiable

- [ ] **Step 2: Prove the current parity failure on DEV**

Run:

```bash
ssh dev '
  cd /home/shaun/repos/athanor &&
  git rev-parse HEAD &&
  git status --short &&
  test -f scripts/write_runtime_parity.py && echo parity_script_present || echo parity_script_missing &&
  test -f scripts/proof_workspace_contract.py && echo proof_contract_present || echo proof_contract_missing
'
```

Expected:
- DEV commit is still `db01a464ce4c6f959bea699f8205ac40857f2f96`
- The blocker-closure slice is missing or older than DESK

- [ ] **Step 3: Build the narrow runtime-adoption slice**

Slice contents:

```text
scripts/write_runtime_parity.py
scripts/proof_workspace_contract.py
scripts/run_steady_state_control_plane.py
scripts/run_continuity_supervisor.py
scripts/run_ralph_loop_pass.py
projects/agents/src/athanor_agents/operator_work.py
projects/agents/src/athanor_agents/tasks.py
projects/agents/src/athanor_agents/supervisor.py
projects/agents/src/athanor_agents/autonomous_queue.py
```

Expected:
- This slice contains every local fix needed for parity semantics, governed proof routing, review persistence, and anti-spin

- [ ] **Step 4: Adopt the slice onto DEV runtime authority**

Preferred execution:

```bash
# Use the governed runtime-ownership lane or a narrow manual sync.
# Do not sync the entire dirty DESK workspace.
ssh dev 'cd /home/shaun/repos/athanor && mkdir -p /tmp/athanor-blocker-closure-backup'
```

Acceptance:
- The exact slice above exists on DEV
- DEV can import the updated agent modules and scripts
- No unrelated local churn is overwritten

- [ ] **Step 5: Make FOUNDRY satisfy the proof-root contract**

Run:

```bash
ssh foundry 'for d in /opt/athanor /opt/athanor/live /opt/athanor/current /srv/athanor /srv/athanor/live; do
  git -C "$d" rev-parse --show-toplevel >/dev/null 2>&1 && echo "FOUND:$d";
done'
```

Expected:
- One real Athanor git root is discovered

If none is discovered:
- create or expose a real Athanor checkout at a discoverable root
- or extend discovery to the actual root before retrying parity

- [ ] **Step 6: Verify parity closure**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/write_runtime_parity.py --json
python3 scripts/write_runtime_parity.py --check
```

Expected:
- `drift_class=clean`
- `desk.commit == dev.commit`
- `desk.dirty=false`
- `dev.dirty=false`
- `foundry.available=true`
- `foundry.manifest_hash == expected_local_proof_manifest_hash`

### Task 2: Force Governed Result-Credit On The Active Capacity Lane

**Files:**
- Verify/adopted runtime code:
  - `/mnt/c/Athanor/projects/agents/src/athanor_agents/operator_work.py`
  - `/mnt/c/Athanor/projects/agents/src/athanor_agents/tasks.py`
  - `/mnt/c/Athanor/projects/agents/src/athanor_agents/supervisor.py`
  - `/mnt/c/Athanor/projects/agents/src/athanor_agents/autonomous_queue.py`
  - `/mnt/c/Athanor/scripts/run_ralph_loop_pass.py`
- Inspect:
  - `/mnt/c/Athanor/config/automation-backbone/result-credit-contract.json`
  - `/mnt/c/Athanor/reports/truth-inventory/governed-dispatch-state.json`
  - `/mnt/c/Athanor/reports/truth-inventory/result-evidence-ledger.json`

- [ ] **Step 1: Prove the active backlog/task pair is legacy residue**

Run:

```bash
python3 - <<'PY'
import json
from urllib.request import Request, urlopen
base='http://192.168.1.244:9000'
for path in ['/v1/tasks/68fc590996b8','/v1/operator/backlog?limit=200']:
    with urlopen(Request(base+path, headers={'Accept':'application/json'}), timeout=20) as resp:
        body=json.loads(resp.read().decode())
        print(json.dumps(body, indent=2)[:12000])
PY
```

Expected:
- current task has `proof_commands=null`
- backlog `backlog-2caafa26` is blocked on `verification_evidence_missing`

- [ ] **Step 2: Retire the legacy blocked capacity backlog**

Run:

```bash
# Use operator backlog controls to archive or supersede backlog-2caafa26
# after parity adoption is complete.
```

Acceptance:
- The old backlog no longer anchors dispatch history
- New work will materialize with the adopted governed proof metadata

- [ ] **Step 3: Re-materialize the governed capacity claim on adopted runtime code**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/run_ralph_loop_pass.py --skip-refresh
python3 - <<'PY'
import json
from pathlib import Path
p=Path('reports/truth-inventory/governed-dispatch-state.json')
print(json.dumps(json.loads(p.read_text()), indent=2)[:12000])
PY
```

Expected:
- new materialized/dispatched task contains:
  - `proof_commands`
  - `proof_command_surface`
  - `proof_artifact_paths`

- [ ] **Step 4: Execute the capacity proof bundle to a ResultPacket-equivalent closure**

Run:

```bash
python3 scripts/run_gpu_scheduler_baseline_eval.py
python3 scripts/collect_capacity_telemetry.py
python3 scripts/write_quota_truth_snapshot.py
```

Expected:
- all three commands exit `0`
- artifacts exist:
  - `reports/truth-inventory/gpu-scheduler-baseline-eval.json`
  - `reports/truth-inventory/capacity-telemetry.json`
  - `reports/truth-inventory/quota-truth.json`

- [ ] **Step 5: Verify task/backlog/result credit reconciliation**

Run:

```bash
python3 - <<'PY'
import json
from urllib.request import Request, urlopen
base='http://192.168.1.244:9000'
with urlopen(Request(base+'/v1/tasks?limit=200', headers={'Accept':'application/json'}), timeout=20) as resp:
    print(resp.read().decode()[:20000])
PY
python3 scripts/write_result_evidence_ledger.py --json
```

Expected:
- active capacity task shows `verification_passed=true`
- backlog transitions to `completed` or `waiting_approval`
- `result-evidence-ledger.json` increments above `0/5`

- [ ] **Step 6: Only use review hold if proof execution fails for a legitimate reason**

Acceptance:
- If review is used, the task stores a durable `review_id`
- backlog status becomes `waiting_approval`
- ledger counts a `ReviewPacket` path, not narrative success text

### Task 3: Restore Validator And Contract-Healer Freshness On The Adopted Runtime

**Files:**
- `/mnt/c/Athanor/scripts/run_steady_state_control_plane.py`
- `/mnt/c/Athanor/scripts/run_continuity_supervisor.py`
- `/mnt/c/Athanor/audit/automation/contract-healer-latest.json`
- `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- generated surfaces under `/mnt/c/Athanor/docs/operations/`

- [ ] **Step 1: Prove the live validator failure directly**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/validate_platform_contract.py
```

Expected current failure set:
- `ATHANOR-FULL-SYSTEM-AUDIT.md`
- `AUDIT-REMEDIATION-BACKLOG.md`
- `DEVSTACK-MEMBRANE-AUDIT.md`
- `PUBLICATION-TRIAGE-REPORT.md`
- `STEADY-STATE-STATUS.md`
- ecosystem master-plan and dependent docs

- [ ] **Step 2: Refresh the full fixed-point publication chain on the adopted runtime**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/run_steady_state_control_plane.py --skip-restart-brief --json
```

Expected:
- truth writers run first
- ecosystem and full audit regenerate
- validator runs
- contract healer runs
- blocker/continuity/front-door surfaces regenerate last

- [ ] **Step 3: Re-run contract healer after the fixed-point pass**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/run_contract_healer.py
python3 scripts/validate_platform_contract.py
```

Expected:
- `contract-healer-latest.json.success=true`
- validator exits `0`

- [ ] **Step 4: Materialize Ralph validation on the current pass**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/mnt/c/Athanor/reports/ralph-loop/latest.json')
obj=json.loads(p.read_text(encoding='utf-8'))
print(json.dumps({'validation': obj.get('validation')}, indent=2))
PY
```

Expected:
- `validation.ran=true`
- `validation.all_passed=true`

### Task 4: Start A New Healthy Continuity Streak

**Files:**
- `/mnt/c/Athanor/scripts/run_continuity_supervisor.py`
- `/mnt/c/Athanor/scripts/run_continuity_control_pass.py`
- `/mnt/c/Athanor/scripts/write_stable_operating_day.py`
- `/mnt/c/Athanor/reports/truth-inventory/completion-pass-ledger.json`
- `/mnt/c/Athanor/reports/truth-inventory/stable-operating-day.json`

- [ ] **Step 1: Prove continuity is clear to run**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/mnt/c/Athanor/reports/truth-inventory/continuity-controller-state.json')
print(json.dumps(json.loads(p.read_text()), indent=2))
PY
```

Expected:
- `controller_status=idle`
- `backoff_until=null`
- `consecutive_no_delta_passes=0`

- [ ] **Step 2: Run one full supervisor wake without an artificial tiny budget**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/run_continuity_supervisor.py --json --runtime-budget-seconds 1800
```

Expected:
- a new completion pass is written
- post-finish refreshes complete

- [ ] **Step 3: Verify the new pass is healthy**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path('/mnt/c/Athanor/reports/truth-inventory/completion-pass-ledger.json')
obj=json.loads(p.read_text())
print(json.dumps(obj['passes'][-1], indent=2))
PY
```

Expected:
- `healthy=true`
- `proofs.validator_and_contract_healer.met=true`
- `proofs.stale_claim_failures.met=true`
- `proofs.artifact_consistency.met=true`

- [ ] **Step 4: Verify the stable-day clock has started**

Run:

```bash
cd /mnt/c/Athanor
python3 scripts/write_stable_operating_day.py --json
```

Expected:
- `consecutive_healthy_pass_count>=1`
- `covered_window_hours>0`
- `oldest_consecutive_pass_at` populated

### Task 5: COO Operating Loop Until Proof Gate Opens

**Files:**
- `/mnt/c/Athanor/reports/truth-inventory/blocker-map.json`
- `/mnt/c/Athanor/reports/truth-inventory/result-evidence-ledger.json`
- `/mnt/c/Athanor/reports/truth-inventory/runtime-parity.json`
- `/mnt/c/Athanor/audit/automation/contract-healer-latest.json`
- `/mnt/c/Athanor/reports/truth-inventory/stable-operating-day.json`

- [ ] **Step 1: Run the primary sequence in this order every cycle**

Sequence:

```text
1. Runtime parity check
2. Adopt runtime slice if parity is not clean
3. Re-materialize and execute capacity proof lane
4. Run fixed-point control-plane pass
5. Run contract healer + validator
6. Run full continuity supervisor wake
7. Recompute blocker map + result evidence + stable day
```

- [ ] **Step 2: Keep owner lanes explicit**

Owners:

```text
Executive / COO lane: sequencing, operator brief, stop/go decisions
Runtime parity lane: DESK/DEV/FOUNDRY alignment
Result-credit lane: governed capacity proof and ledger increment
Publication lane: fixed-point refresh, validator, contract healer
Continuity lane: healthy pass streak and stable-day accumulation
```

- [ ] **Step 3: Do not reopen external automation yet**

Acceptance:
- no external Codex control loop drives Athanor until:
  - runtime parity is clean
  - capacity lane can produce creditable proof
  - validator and contract-healer stay green across consecutive passes

### Task 6: Final Acceptance Gate

**Files:**
- `/mnt/c/Athanor/reports/truth-inventory/runtime-parity.json`
- `/mnt/c/Athanor/reports/truth-inventory/result-evidence-ledger.json`
- `/mnt/c/Athanor/audit/automation/contract-healer-latest.json`
- `/mnt/c/Athanor/reports/truth-inventory/completion-pass-ledger.json`
- `/mnt/c/Athanor/reports/truth-inventory/stable-operating-day.json`
- `/mnt/c/Athanor/reports/truth-inventory/blocker-map.json`

- [ ] **Step 1: Gate the program closed only when all of these are true**

Acceptance checklist:

```text
runtime-parity.json.drift_class == clean
contract-healer-latest.json.success == true
ralph-loop/latest.json.validation.ran == true
ralph-loop/latest.json.validation.all_passed == true
result-evidence-ledger.json.threshold_progress >= 1 for first closure
completion-pass-ledger latest pass healthy == true
stable-operating-day.json.covered_window_hours > 0
blocker-map proof_gate blocking checks shrink accordingly
```

- [ ] **Step 2: Keep going until proof gate is actually open**

Final proof-gate target:

```text
stable_operating_day == met
result_backed_threshold == met
runtime_parity == met
validator_and_contract_healer == met
```
