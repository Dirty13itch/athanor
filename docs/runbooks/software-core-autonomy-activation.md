# Autonomy Operations

Source of truth: `config/automation-backbone/autonomy-activation-registry.json`, `config/automation-backbone/operator-presence-model.json`, `config/automation-backbone/workload-class-registry.json`, `docs/operations/AUTONOMY-ACTIVATION-REPORT.md`, `docs/operations/OPERATOR_RUNBOOKS.md`
Validated against registry version: `autonomy-activation-registry.json@2026-04-02.4`, `operator-presence-model.json@2026-03-12`, `workload-class-registry.json@2026-03-12`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: activation scope, enabled agents, and approval boundaries live in the autonomy-activation registry; this runbook owns the operator sequence for operating, auditing, or changing autonomy scope and must not drift into a second policy source.

---

## Purpose

Operate or audit the live full-system autonomy phase without relaxing the standing provider, sovereignty, or runtime-mutation boundaries.

This runbook covers the live full-system roster:

- `coding-agent`
- `research-agent`
- `knowledge-agent`
- `general-assistant`
- `data-curator`
- `stash-agent`
- `home-agent`
- `media-agent`
- `creative-agent`

It still does not authorize runtime mutations. Creative and refusal-sensitive autonomy are live now, but only on sovereign-only lanes by contract.

## Current contract

- The DEV `:8760` governor-facade cutover is complete and no longer blocks activation.
- `full_system_phase_3` is active.
- Broad autonomy is on.
- Runtime mutations remain approval-gated.
- Ordinary auto-routing may only use providers that are both configured and observed or otherwise explicitly allowed by canonical routing posture.
- `data-curator`, `stash-agent`, `home-agent`, and `media-agent` are intentionally bounded to the sovereign local machine lane and do not widen ordinary routing onto the auth-failed VAULT API lanes.
- `creative-agent` is active, but refusal-sensitive and private creative loops must still stay on sovereign-only lanes by contract.
- The current activation scope is governed by [AUTONOMY-ACTIVATION-REPORT.md](/C:/Athanor/docs/operations/AUTONOMY-ACTIVATION-REPORT.md), not by `STATUS.md` prose alone.

## Current phase

- Current phase: `full_system_phase_3`
- Phase status: `active`
- Phase scope: `broad_with_explicit_exceptions`
- Runtime ownership prerequisite: `verified`
- Broad autonomy enabled: `true`
- Remaining blocker count: `0`
- Next phase: none
- Promotion rule: this is the live top-level autonomy phase; any further widening must happen by registry change, not ad hoc drift

## Preflight

1. Review [AUTONOMY-ACTIVATION-REPORT.md](/C:/Athanor/docs/operations/AUTONOMY-ACTIVATION-REPORT.md).
2. Review [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md) for weak or auth-failed lanes.
3. Review the current governor posture and operator presence.
4. Confirm the current activation phase is `full_system_phase_3` and its status is `active`.
5. Confirm broad autonomy remains enabled in the registry and report layer.
6. Confirm runtime mutations remain approval-gated in the registry.
7. Confirm provider scope and sovereign-only routing constraints still match canonical policy.

## Activation sequence

1. Keep the activation scope at the currently active full-system phase unless the autonomy registry is updated first.
2. Allow the full live roster to execute within the current provider, sovereignty, and approval boundaries.
3. Keep `background_transform` on approved lanes and keep refusal-sensitive or private creative work on sovereign-only lanes even though those workload classes are now active.
4. Ensure autonomy-managed plans and task decomposition keep using the shared phase policy instead of hardcoded agent or workload allowlists.
5. Keep host-level runtime work, service restarts, systemd edits, cron edits, VAULT LiteLLM changes, and schema changes behind explicit approval.
6. If a task would require a handoff-only, auth-failed, or configured-unused provider lane, keep it pending or route it through an explicitly approved alternative instead of widening policy ad hoc.
7. If you need to change the current scope or exceptions, update `config/automation-backbone/autonomy-activation-registry.json`, regenerate the report layer, and rerun validators before treating the change as real.

## Verification

From `C:\Athanor`:

```powershell
python scripts/validate_platform_contract.py
python scripts/generate_truth_inventory_reports.py --report autonomy_activation --check
python scripts/generate_documentation_index.py --check
python scripts/generate_project_maturity_report.py --check
cd projects/agents; .\.venv\Scripts\python -m pytest tests\test_command_hierarchy.py tests\test_repo_contracts.py -q
```

Success criteria:

- The autonomy report matches the registry-backed current phase and enabled-agent set.
- The autonomy report shows `full_system_phase_3`, `full_system_active`, and `broad_autonomy_enabled=true`.
- Current-state docs no longer disagree about activation scope.
- The enabled agents and workload classes stay within the current full-system contract.
- Autonomy-managed plan generation and decomposition do not silently reintroduce out-of-phase agents.
- Runtime mutations are still explicitly approval-gated.

## Scope changes

1. There is no broader registered phase than `full_system_phase_3`; further widening means changing explicit exceptions, not promoting to another hidden mode.
2. Do not treat ad hoc successful tasks as permission to widen provider scope, runtime mutation rights, or sovereignty exceptions. The registry controls scope, not anecdotal success.
3. If creative or dialogue lanes need additional constraints, record them in the registry and rerun the report and validation layer before treating them as live policy.
