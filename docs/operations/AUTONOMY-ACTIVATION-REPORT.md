# Autonomy Activation Report

Generated from `config/automation-backbone/autonomy-activation-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Registry version: `2026-04-02.4`
- Status: `live`
- Activation state: `full_system_active`
- Current phase: `full_system_phase_3`
- Current phase status: `active`
- Current phase scope: `broad_with_explicit_exceptions`
- Next phase: `none`
- Next phase status: `none`
- Next phase scope: `n/a`
- Next phase blocker count: `0`
- Next phase blocker ids: none
- Broad autonomy enabled: `True`
- Runtime mutations approval gated: `True`

## Next Promotion Boundary

No next phase is registered beyond the current active scope.

## Prerequisites

| Prerequisite | Status | Phase Scope | Evidence |
| --- | --- | --- | --- |
| `dev_governor_facade_cutover` | `verified` | `software_core_phase_1` | `docs/operations/RUNTIME-MIGRATION-REPORT.md`, `docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md` |
| `provider_routing_truth` | `verified` | `software_core_phase_1` | `config/automation-backbone/provider-catalog.json`, `projects/agents/config/subscription-routing-policy.yaml`, `docs/operations/PROVIDER-CATALOG-REPORT.md` |
| `vault_provider_auth_repair` | `verified` | `expanded_core_phase_2` | `projects/agents/config/subscription-routing-policy.yaml`, `docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md`, `docs/operations/SECRET-SURFACE-REPORT.md`, `docs/operations/PROVIDER-CATALOG-REPORT.md` |
| `runtime_ownership_maturity` | `verified` | `full_system_phase_3` | `config/automation-backbone/repo-roots-registry.json`, `config/automation-backbone/runtime-ownership-contract.json`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/RUNTIME-MIGRATION-REPORT.md`, `docs/operations/TRUTH-DRIFT-REPORT.md`, `scripts/vault-ssh.py`, `scripts/ssh-vault.ps1` |

## Approval Gates

### Runtime mutations

- Gate id: `runtime_mutations`
- Approval required: `True`
- Blocked actions: `systemd changes`, `cron changes`, `live service restarts outside an approved maintenance packet`, `host-level config mutations`, `destructive runtime operations`, `VAULT LiteLLM config or env changes`, `database schema changes`

### Provider scope

- Gate id: `provider_scope`
- Approval required: `False`
- Blocked actions: `treating auth-failed or configured-unused providers as ordinary auto-routing lanes`, `treating governed-handoff-only providers as ordinary auto-routing lanes without explicit opt-in`

## Phase Matrix

| Phase | Status | Scope | Enabled Agents | Allowed Workloads |
| --- | --- | --- | --- | --- |
| `software_core_phase_1` | `active` | `bounded` | `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant` | `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification` |
| `expanded_core_phase_2` | `active` | `bounded_plus_domain_sidecars` | `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant`, `data-curator`, `stash-agent`, `home-agent`, `media-agent` | `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification`, `background_transform` |
| `full_system_phase_3` | `active` | `broad_with_explicit_exceptions` | `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant`, `data-curator`, `stash-agent`, `home-agent`, `media-agent`, `creative-agent` | `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification`, `background_transform`, `refusal_sensitive_creative`, `explicit_dialogue` |

### Software-core autonomy

- Phase id: `software_core_phase_1`
- Status: `active`
- Scope: `bounded`
- Enabled agents: `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant`
- Allowed workload classes: `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification`
- Blocked workload classes: `background_transform`, `refusal_sensitive_creative`, `explicit_dialogue`
- Allowed loop families: `governed backlog execution`, `repo audit and repair`, `planning and workplan generation`, `truth-report generation and current-state maintenance`, `provider routing and governed fallback selection`, `self-maintenance inside repo and task-engine bounds`
- Blocked without approval: `runtime mutations`, `host reconfiguration`, `new provider activation outside catalog-backed posture`, `broad domain roster expansion`
- Entry criteria: `The DEV governor-facade cutover remains verified.`, `Canonical provider routing posture remains catalog-backed.`, `Operator presence and release-tier posture remain live.`
- Success criteria: `Governed autonomous work can plan, route, execute, and persist results across proven local and cloud lanes.`, `No runtime mutation occurs without explicit approval.`, `Status, reports, and route surfaces all describe the same activation scope.`

### Expanded core autonomy

- Phase id: `expanded_core_phase_2`
- Status: `active`
- Scope: `bounded_plus_domain_sidecars`
- Enabled agents: `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant`, `data-curator`, `stash-agent`, `home-agent`, `media-agent`
- Allowed workload classes: `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification`, `background_transform`
- Blocked workload classes: `refusal_sensitive_creative`, `explicit_dialogue`
- Allowed loop families: `software-core loops`, `data curation`, `bounded media and home automation`, `background transforms on approved lanes`
- Blocked without approval: `runtime mutations`, `VAULT provider expansion without repaired auth posture`, `creative or refusal-sensitive autonomy`
- Entry criteria: `The currently blocked or demoted VAULT API lanes are either repaired, contract-corrected, or explicitly kept out of ordinary auto-routing with packet-backed evidence.`, `Weak CLI and billing lanes have either been verified or explicitly kept demoted.`
- Success criteria: `The broader live roster can execute within the same governed provider and approval boundaries as software-core autonomy.`

### Full-system autonomy

- Phase id: `full_system_phase_3`
- Status: `active`
- Scope: `broad_with_explicit_exceptions`
- Enabled agents: `coding-agent`, `research-agent`, `knowledge-agent`, `general-assistant`, `data-curator`, `stash-agent`, `home-agent`, `media-agent`, `creative-agent`
- Allowed workload classes: `architecture_planning`, `repo_audit`, `coding_implementation`, `private_automation`, `research_synthesis`, `workplan_generation`, `briefing_digest`, `judge_verification`, `background_transform`, `refusal_sensitive_creative`, `explicit_dialogue`
- Blocked workload classes: none
- Allowed loop families: `software-core loops`, `broader live roster autonomy`, `creative and refusal-sensitive sovereign-only loops`
- Blocked without approval: `runtime mutations that still exceed the standing approval gate`
- Entry criteria: `Runtime ownership is explicit enough that host-level maintenance no longer depends on undocumented operator memory.`, `Creative and refusal-sensitive loops stay on sovereign-only lanes by contract.`
- Success criteria: `Athanor can operate across the full live roster under registry-backed scope, provider posture, and approval boundaries.`
