# Software-Core Autonomy Operations

Source of truth: `config/automation-backbone/autonomy-activation-registry.json`, `config/automation-backbone/operator-presence-model.json`, `config/automation-backbone/workload-class-registry.json`, `docs/operations/AUTONOMY-ACTIVATION-REPORT.md`, `docs/operations/OPERATOR_RUNBOOKS.md`
Validated against registry version: `autonomy-activation-registry.json@2026-03-29.2`, `operator-presence-model.json@2026-03-12`, `workload-class-registry.json@2026-03-12`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: activation scope, enabled agents, and approval boundaries live in the autonomy-activation registry; this runbook owns the operator sequence for operating, auditing, or promoting software-core autonomy and must not drift into a second policy source.

---

## Purpose

Operate or audit the first post-cutover autonomy wave without widening Athanor into broad unsupervised runtime control.

This runbook is intentionally narrow. It covers software-core autonomy only:

- `coding-agent`
- `research-agent`
- `knowledge-agent`
- `general-assistant`

It does not authorize runtime mutations, full-roster autonomy, or creative and refusal-sensitive autonomy.

## Current contract

- The DEV `:8760` governor-facade cutover is complete and no longer blocks activation.
- `software_core_phase_1` is active.
- Broad autonomy is still off.
- Runtime mutations remain approval-gated.
- Ordinary auto-routing may only use providers that are both configured and observed or otherwise explicitly allowed by canonical routing posture.
- The current activation scope is governed by [AUTONOMY-ACTIVATION-REPORT.md](/C:/Athanor/docs/operations/AUTONOMY-ACTIVATION-REPORT.md), not by `STATUS.md` prose alone.

## Next promotion boundary

- Next phase: `expanded_core_phase_2`
- Phase status: `blocked`
- Phase scope: `bounded_plus_domain_sidecars`
- Remaining blocker count: `1`
- Current blocker: `vault_provider_auth_repair`
- Promotion rule: widen only after the blocker is cleared in the registry-backed report layer and validators are rerun

## Preflight

1. Review [AUTONOMY-ACTIVATION-REPORT.md](/C:/Athanor/docs/operations/AUTONOMY-ACTIVATION-REPORT.md).
2. Review [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md) for weak or auth-failed lanes.
3. Review the current governor posture and operator presence.
4. Confirm the current activation phase is still `software_core_phase_1` and its status is `active`.
5. Confirm runtime mutations remain approval-gated in the registry.
6. Confirm the next promotion boundary still names `expanded_core_phase_2` and that `vault_provider_auth_repair` is the only remaining blocker before treating any wider roster as live.

## Activation sequence

1. Keep the activation scope at software-core only unless the autonomy registry is updated first.
2. Allow governed backlog execution, repo audit and repair, planning, report generation, and self-maintenance inside repo and task-engine bounds.
3. Keep `background_transform`, `refusal_sensitive_creative`, and `explicit_dialogue` out of this first activation phase.
4. Ensure autonomy-managed plans and task decomposition filter out-of-phase agents before submission; manual operator-created plans may still target the broader live roster because they remain approval-driven.
5. Keep host-level runtime work, service restarts, systemd edits, cron edits, VAULT LiteLLM changes, and schema changes behind explicit approval.
6. If a task would require a handoff-only, auth-failed, or configured-unused provider lane, keep it pending or route it through an explicitly approved alternative instead of widening policy ad hoc.
7. If you need to widen beyond software-core autonomy, update `config/automation-backbone/autonomy-activation-registry.json`, regenerate the report layer, and rerun validators before treating the wider scope as real.

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
- Current-state docs no longer disagree about activation scope.
- The first-wave enabled agents and workload classes stay within the software-core contract.
- Autonomy-managed plan generation and decomposition do not silently reintroduce out-of-phase agents.
- Runtime mutations are still explicitly approval-gated.

## Expansion rules

1. Phase 2 expansion requires repaired or explicitly demoted weak provider lanes.
2. Phase 3 expansion requires stronger runtime-ownership maturity and sovereign-only guardrails for creative or refusal-sensitive autonomy.
3. Do not treat ad hoc successful tasks as permission to widen the phase. The registry controls scope, not anecdotal success.
