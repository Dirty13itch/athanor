from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _candidate_registry_dirs() -> list[Path]:
    candidates: list[Path] = []
    env_dir = os.getenv("ATHANOR_REGISTRY_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    repo_root = _repo_root()
    candidates.extend(
        [
            repo_root / "config" / "automation-backbone",
            Path.cwd() / "config" / "automation-backbone",
            Path.cwd() / "config",
            Path("/app/config/automation-backbone"),
            Path("/app/config"),
            Path("/opt/athanor/agents/config/automation-backbone"),
            Path("/opt/athanor/agents/config"),
        ]
    )
    return candidates


def _registry_dir(filename: str) -> Path:
    for candidate in _candidate_registry_dirs():
        if (candidate / filename).exists():
            return candidate
    checked = ", ".join(str(path) for path in _candidate_registry_dirs())
    raise FileNotFoundError(
        f"Unable to resolve registry file {filename!r}. Checked: {checked}"
    )


@lru_cache(maxsize=None)
def _load_registry(filename: str) -> dict[str, Any]:
    path = _registry_dir(filename) / filename
    return json.loads(path.read_text(encoding="utf-8"))


def get_command_rights_registry() -> dict[str, Any]:
    return _load_registry("command-rights-registry.json")


def get_system_constitution() -> dict[str, Any]:
    return _load_registry("system-constitution.json")


def get_policy_class_registry() -> dict[str, Any]:
    return _load_registry("policy-class-registry.json")


def get_model_role_registry() -> dict[str, Any]:
    return _load_registry("model-role-registry.json")


def get_workload_class_registry() -> dict[str, Any]:
    return _load_registry("workload-class-registry.json")


def get_model_proving_ground() -> dict[str, Any]:
    return _load_registry("model-proving-ground.json")


def get_model_intelligence_lane() -> dict[str, Any]:
    return _load_registry("model-intelligence-lane.json")


def get_contract_registry() -> dict[str, Any]:
    return _load_registry("contract-registry.json")


def get_eval_corpus_registry() -> dict[str, Any]:
    return _load_registry("eval-corpus-registry.json")


def get_capacity_governor_registry() -> dict[str, Any]:
    return _load_registry("capacity-governor.json")


def get_economic_governance_registry() -> dict[str, Any]:
    return _load_registry("economic-governance.json")


def get_data_lifecycle_registry() -> dict[str, Any]:
    return _load_registry("data-lifecycle-registry.json")


def get_operator_presence_model() -> dict[str, Any]:
    return _load_registry("operator-presence-model.json")


def get_tool_permission_registry() -> dict[str, Any]:
    return _load_registry("tool-permission-registry.json")


def get_backup_restore_readiness() -> dict[str, Any]:
    return _load_registry("backup-restore-readiness.json")


def get_release_ritual_registry() -> dict[str, Any]:
    return _load_registry("release-ritual.json")


def get_experiment_ledger_policy() -> dict[str, Any]:
    return _load_registry("experiment-ledger-policy.json")


def get_deprecation_retirement_policy() -> dict[str, Any]:
    return _load_registry("deprecation-retirement-policy.json")


def get_operator_runbooks_registry() -> dict[str, Any]:
    return _load_registry("operator-runbooks.json")


def _build_registry_versions() -> dict[str, str]:
    return {
        "constitution": get_system_constitution().get("version", "unknown"),
        "command_rights": get_command_rights_registry().get("version", "unknown"),
        "policy_classes": get_policy_class_registry().get("version", "unknown"),
        "contract_registry": get_contract_registry().get("version", "unknown"),
        "eval_corpora": get_eval_corpus_registry().get("version", "unknown"),
        "model_roles": get_model_role_registry().get("version", "unknown"),
        "workload_classes": get_workload_class_registry().get("version", "unknown"),
        "proving_ground": get_model_proving_ground().get("version", "unknown"),
        "model_intelligence": get_model_intelligence_lane().get("version", "unknown"),
        "capacity_governor": get_capacity_governor_registry().get("version", "unknown"),
        "economic_governance": get_economic_governance_registry().get("version", "unknown"),
        "data_lifecycle": get_data_lifecycle_registry().get("version", "unknown"),
        "presence_model": get_operator_presence_model().get("version", "unknown"),
        "tool_permissions": get_tool_permission_registry().get("version", "unknown"),
        "backup_restore": get_backup_restore_readiness().get("version", "unknown"),
        "release_ritual": get_release_ritual_registry().get("version", "unknown"),
        "experiment_ledger": get_experiment_ledger_policy().get("version", "unknown"),
        "deprecation_retirement": get_deprecation_retirement_policy().get("version", "unknown"),
        "operator_runbooks": get_operator_runbooks_registry().get("version", "unknown"),
    }


def _build_contract_registry_snapshot() -> dict[str, Any]:
    contracts = get_contract_registry()
    contract_items = [dict(item) for item in contracts.get("contracts", []) if isinstance(item, dict)]
    status_counts: dict[str, int] = {}
    for item in contract_items:
        status = str(item.get("status") or "configured")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "version": contracts.get("version", "unknown"),
        "status": contracts.get("status", "configured"),
        "count": len(contract_items),
        "contracts": contract_items,
        "status_counts": status_counts,
        "provenance_contract": next(
            (item for item in contract_items if str(item.get("id")) == "artifact_provenance_record"),
            None,
        ),
    }


def _build_eval_corpora_snapshot(proving_ground_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    corpora_registry = get_eval_corpus_registry()
    corpora = [dict(item) for item in corpora_registry.get("corpora", []) if isinstance(item, dict)]
    sensitivity_counts: dict[str, int] = {}
    for item in corpora:
        sensitivity = str(item.get("sensitivity") or "unknown")
        sensitivity_counts[sensitivity] = sensitivity_counts.get(sensitivity, 0) + 1

    runtime_results = list((proving_ground_snapshot or {}).get("recent_results") or [])
    runtime_status = str(corpora_registry.get("status", "configured"))
    if runtime_results and runtime_status == "configured":
        runtime_status = "live_partial"

    return {
        "version": corpora_registry.get("version", "unknown"),
        "status": runtime_status,
        "count": len(corpora),
        "corpora": corpora,
        "sensitivity_counts": sensitivity_counts,
        "runtime_result_count": len(runtime_results),
        "latest_result_at": (
            runtime_results[0].get("timestamp") if runtime_results else None
        ),
    }


def _build_experiment_ledger_snapshot(
    *,
    proving_ground_snapshot: dict[str, Any] | None = None,
    promotion_controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = get_experiment_ledger_policy()
    recent_results = list((proving_ground_snapshot or {}).get("recent_results") or [])
    recent_events = list((promotion_controls or {}).get("recent_events") or [])
    recent_experiments = [
        {
            "id": str(result.get("benchmark_id") or f"experiment-{index + 1}"),
            "name": str(result.get("name") or result.get("benchmark_id") or "benchmark"),
            "category": str(result.get("category") or "benchmark"),
            "passed": bool(result.get("passed")),
            "score": float(result.get("score", 0.0) or 0.0),
            "max_score": float(result.get("max_score", 0.0) or 0.0),
            "timestamp": result.get("timestamp"),
        }
        for index, result in enumerate(recent_results[:8])
    ]
    status = str(policy.get("status", "configured"))
    if recent_experiments or recent_events:
        status = "live_partial"

    return {
        "version": policy.get("version", "unknown"),
        "status": status,
        "required_field_count": len(policy.get("required_fields", [])),
        "required_fields": list(policy.get("required_fields", [])),
        "retention": str(policy.get("retention") or "unknown"),
        "promotion_linkage": str(policy.get("promotion_linkage") or ""),
        "evidence_count": len(recent_experiments) + len(recent_events),
        "recent_experiments": recent_experiments,
        "recent_promotion_events": recent_events[:8],
    }


def _build_deprecation_retirement_snapshot(
    retirement_controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retirement_policy = get_deprecation_retirement_policy()
    status = str(retirement_policy.get("status", "configured"))
    controls_status = str((retirement_controls or {}).get("status") or "")
    if controls_status in {"live", "live_partial"} and status == "configured":
        status = "live_partial"
    if controls_status == "degraded":
        status = "degraded"
    return {
        "version": retirement_policy.get("version", "unknown"),
        "status": status,
        "asset_class_count": len(retirement_policy.get("asset_classes", [])),
        "asset_classes": list(retirement_policy.get("asset_classes", [])),
        "stages": list(retirement_policy.get("stages", [])),
        "rule": str(retirement_policy.get("rule") or ""),
    }


def _build_governance_layers_snapshot(
    *,
    proving_ground_snapshot: dict[str, Any] | None = None,
    promotion_controls: dict[str, Any] | None = None,
    retirement_controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    release_ritual = get_release_ritual_registry()
    runbooks = get_operator_runbooks_registry()

    return {
        "contract_registry": _build_contract_registry_snapshot(),
        "eval_corpora": _build_eval_corpora_snapshot(proving_ground_snapshot),
        "release_ritual": {
            "version": release_ritual.get("version", "unknown"),
            "tier_count": len(release_ritual.get("tiers", [])),
            "status": release_ritual.get("status", "configured"),
        },
        "experiment_ledger": _build_experiment_ledger_snapshot(
            proving_ground_snapshot=proving_ground_snapshot,
            promotion_controls=promotion_controls,
        ),
        "deprecation_retirement": _build_deprecation_retirement_snapshot(retirement_controls),
        "operator_runbooks": {
            "version": runbooks.get("version", "unknown"),
            "runbook_count": len(runbooks.get("runbooks", [])),
            "status": runbooks.get("status", "configured"),
        },
    }


def build_model_governance_snapshot() -> dict[str, Any]:
    roles = get_model_role_registry()
    workloads = get_workload_class_registry()
    proving_ground = get_model_proving_ground()
    model_intelligence = get_model_intelligence_lane()

    role_items = roles.get("roles", [])
    champion_summary = [
        {
            "role_id": role["id"],
            "label": role["label"],
            "plane": role["plane"],
            "status": role["status"],
            "champion": role["champion"],
            "challenger_count": len(role.get("challengers", [])),
            "workload_count": len(role.get("workload_classes", [])),
        }
        for role in role_items
    ]

    promotion_controls = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": get_release_ritual_registry().get("status", "configured"),
        "tiers": list(get_release_ritual_registry().get("tiers", [])),
        "ritual": list(get_release_ritual_registry().get("ritual", [])),
        "counts": {},
        "active_promotions": [],
        "recent_promotions": [],
        "recent_events": [],
        "candidate_queue": [
            {
                "role_id": role["id"],
                "label": role["label"],
                "champion": role["champion"],
                "challengers": list(role.get("challengers", [])),
                "plane": role["plane"],
            }
            for role in role_items
            if role.get("challengers")
        ],
        "next_actions": ["Stage a challenger to turn the release ladder into live promotion control."],
    }
    retirement_policy = get_deprecation_retirement_policy()
    retirement_controls = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": retirement_policy.get("status", "configured"),
        "asset_classes": list(retirement_policy.get("asset_classes", [])),
        "stages": list(retirement_policy.get("stages", [])),
        "rule": str(retirement_policy.get("rule") or ""),
        "counts": {},
        "active_retirements": [],
        "recent_retirements": [],
        "recent_events": [],
        "candidate_queue": [
            {
                "asset_class": "models",
                "asset_id": f"{role['id']}:{role['champion']}",
                "label": f"{role['label']} champion {role['champion']}",
                "role_id": role["id"],
                "plane": role["plane"],
                "current_stage": "active",
            }
            for role in role_items
            if role.get("champion")
        ][:8],
        "next_actions": ["Stage a retirement rehearsal to turn deprecation policy into live governance control."],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role_registry_version": roles.get("version", "unknown"),
        "workload_registry_version": workloads.get("version", "unknown"),
        "rights_registry_version": get_command_rights_registry().get("version", "unknown"),
        "policy_registry_version": get_policy_class_registry().get("version", "unknown"),
        "role_count": len(role_items),
        "workload_count": len(workloads.get("classes", [])),
        "champion_summary": champion_summary,
        "role_registry": role_items,
        "workload_registry": workloads.get("classes", []),
        "proving_ground": proving_ground,
        "promotion_controls": promotion_controls,
        "retirement_controls": retirement_controls,
        "model_intelligence": model_intelligence,
        "registry_versions": _build_registry_versions(),
        "governance_layers": _build_governance_layers_snapshot(
            proving_ground_snapshot=proving_ground,
            promotion_controls=promotion_controls,
            retirement_controls=retirement_controls,
        ),
    }


async def build_model_intelligence_snapshot() -> dict[str, Any]:
    from .self_improvement import get_improvement_engine
    from .scheduler import get_model_intelligence_cadence

    intelligence = dict(get_model_intelligence_lane())
    role_registry = get_model_role_registry()
    engine = get_improvement_engine()
    await engine.load()
    summary = await engine.get_improvement_summary()
    cadence_jobs = await get_model_intelligence_cadence()

    candidate_queue = [
        {
            "role_id": role["id"],
            "label": role["label"],
            "plane": role["plane"],
            "champion": role["champion"],
            "challengers": list(role.get("challengers", [])),
        }
        for role in role_registry.get("roles", [])
        if role.get("challengers")
    ]

    benchmark_results = int(summary.get("benchmark_results", 0) or 0)
    pending_proposals = int(summary.get("pending", 0) or 0)
    deployed_proposals = int(summary.get("deployed", 0) or 0)
    validated_proposals = int(summary.get("validated", 0) or 0)
    last_cycle = summary.get("last_cycle")

    next_actions: list[str] = []
    if benchmark_results == 0:
        next_actions.append("Run the proving ground to seed benchmark history for champion lanes.")
    if last_cycle is None:
        next_actions.append("Run the improvement cycle to establish live rebaseline evidence.")
    if pending_proposals > 0:
        next_actions.append("Review pending improvement proposals generated from recent benchmark and pattern cycles.")
    if candidate_queue:
        next_actions.append(
            f"Prioritize challenger evaluation for {candidate_queue[0]['label']} and {max(len(candidate_queue) - 1, 0)} other lane(s)."
        )
    if not next_actions:
        next_actions.append("Continue weekly horizon scan triage and monthly rebaseline checks against Athanor workloads.")

    active_cadence = any(job.get("current_state") == "scheduled" for job in cadence_jobs)
    runtime_status = (
        "live"
        if last_cycle or (benchmark_results > 0 and active_cadence)
        else ("live_partial" if active_cadence else intelligence.get("status", "implemented_not_live"))
    )
    operational_state = (
        "active"
        if last_cycle
        else ("seeded" if benchmark_results > 0 else ("configured" if active_cadence else "pending"))
    )

    return {
        **intelligence,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": runtime_status,
        "operational_state": operational_state,
        "benchmark_results": benchmark_results,
        "pending_proposals": pending_proposals,
        "validated_proposals": validated_proposals,
        "deployed_proposals": deployed_proposals,
        "candidate_queue": candidate_queue,
        "last_cycle": last_cycle,
        "cadence_jobs": cadence_jobs,
        "next_actions": next_actions,
    }


async def build_live_model_governance_snapshot() -> dict[str, Any]:
    from .proving_ground import build_proving_ground_snapshot
    from .promotion_control import build_promotion_controls_snapshot
    from .retirement_control import build_retirement_controls_snapshot

    roles = get_model_role_registry()
    workloads = get_workload_class_registry()
    proving_ground = await build_proving_ground_snapshot(limit=12)
    model_intelligence = await build_model_intelligence_snapshot()
    promotion_controls = await build_promotion_controls_snapshot(limit=12)
    retirement_controls = await build_retirement_controls_snapshot(limit=12)

    role_items = roles.get("roles", [])
    champion_summary = [
        {
            "role_id": role["id"],
            "label": role["label"],
            "plane": role["plane"],
            "status": role["status"],
            "champion": role["champion"],
            "challenger_count": len(role.get("challengers", [])),
            "workload_count": len(role.get("workload_classes", [])),
        }
        for role in role_items
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role_registry_version": roles.get("version", "unknown"),
        "workload_registry_version": workloads.get("version", "unknown"),
        "rights_registry_version": get_command_rights_registry().get("version", "unknown"),
        "policy_registry_version": get_policy_class_registry().get("version", "unknown"),
        "role_count": len(role_items),
        "workload_count": len(workloads.get("classes", [])),
        "champion_summary": champion_summary,
        "role_registry": role_items,
        "workload_registry": workloads.get("classes", []),
        "proving_ground": proving_ground,
        "promotion_controls": promotion_controls,
        "retirement_controls": retirement_controls,
        "model_intelligence": model_intelligence,
        "registry_versions": _build_registry_versions(),
        "governance_layers": _build_governance_layers_snapshot(
            proving_ground_snapshot=proving_ground,
            promotion_controls=promotion_controls,
            retirement_controls=retirement_controls,
        ),
    }
