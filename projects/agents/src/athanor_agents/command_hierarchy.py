from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .model_governance import (
    get_autonomy_activation_registry,
    get_backup_restore_readiness,
    get_capacity_governor_registry,
    get_command_rights_registry,
    get_data_lifecycle_registry,
    get_docs_lifecycle_registry,
    get_economic_governance_registry,
    get_operator_presence_model,
    get_platform_topology,
    get_policy_class_registry,
    get_program_operating_system,
    get_release_ritual_registry,
    get_project_maturity_registry,
    get_system_constitution,
    get_tool_permission_registry,
    get_workload_class_registry,
)
from .subscriptions import get_policy_snapshot


AUTHORITY_ORDER = [
    {
        "id": "shaun",
        "label": "Shaun",
        "role": "owner",
        "summary": "Final authority for vision, irreversible changes, and approvals that exceed autonomous policy.",
    },
    {
        "id": "constitution",
        "label": "Constitution + Policy Registry",
        "role": "highest_non_human_authority",
        "summary": "Immutable constraints, approval bands, cloud boundaries, and command-rights policy.",
    },
    {
        "id": "governor",
        "label": "Athanor Governor",
        "role": "runtime_posture_and_fallback_authority",
        "summary": "Controls runtime posture, fallback choice, capacity posture, and pause or resume decisions inside policy bounds. Durable tasks belong to the task engine, leases to the subscription broker, and schedules to the scheduler.",
    },
    {
        "id": "meta_strategy",
        "label": "Meta Strategy Layer",
        "role": "planning_review",
        "summary": "Frontier and sovereign supervisory lanes that plan, critique, decompose, and review without directly mutating runtime.",
    },
    {
        "id": "control_stack",
        "label": "Orchestrator Control Stack",
        "role": "execution_control",
        "summary": "Server, router, tasks, scheduler, workspace, workplanner, alerts, subscriptions, and capacity arbitration.",
    },
    {
        "id": "specialists",
        "label": "Specialist Agents",
        "role": "domain_execution",
        "summary": "Domain-scoped execution agents operating inside tool and approval boundaries.",
    },
    {
        "id": "workers_judges",
        "label": "Worker and Judge Planes",
        "role": "generation_and_scoring",
        "summary": "Bulk local execution and local verification lanes with no command rights of their own.",
    },
    {
        "id": "tools_infra",
        "label": "Tools and Infrastructure",
        "role": "governed_resources",
        "summary": "Repositories, services, models, stores, and external adapters that never act as free-standing decision-makers.",
    },
]


CONTROL_STACK = [
    {
        "id": "agent-server",
        "label": "Agent Server",
        "role": "runtime boundary and API front door",
        "entrypoints": ["/health", "/v1/chat/completions", "/v1/agents", "/v1/models"],
        "status": "live",
    },
    {
        "id": "router",
        "label": "Router",
        "role": "processing-tier and workload triage",
        "entrypoints": ["/v1/routing/classify"],
        "status": "live",
    },
    {
        "id": "task-engine",
        "label": "Task Engine",
        "role": "durable queued work and approvals",
        "entrypoints": ["/v1/tasks", "/v1/tasks/runs"],
        "status": "live",
    },
    {
        "id": "scheduler",
        "label": "Scheduler",
        "role": "recurring loops and schedule introspection",
        "entrypoints": ["/v1/tasks/schedules", "/v1/tasks/scheduled", "/v1/scheduling/status"],
        "status": "live",
    },
    {
        "id": "workspace",
        "label": "Workspace / GWT",
        "role": "shared attention and broadcast arbitration",
        "entrypoints": ["/v1/workspace", "/v1/workspace/stats"],
        "status": "live",
    },
    {
        "id": "workplanner",
        "label": "Goals and Workplanner",
        "role": "goal steering, plan generation, and redirects",
        "entrypoints": ["/v1/goals", "/v1/workplan", "/v1/workplan/generate", "/v1/workplan/redirect"],
        "status": "live",
    },
    {
        "id": "alerts",
        "label": "Alerts and Escalation",
        "role": "confidence posture, alerts, approvals, and operator escalation",
        "entrypoints": ["/v1/notifications", "/v1/escalation", "/v1/notification-budget"],
        "status": "live",
    },
    {
        "id": "subscription-broker",
        "label": "Subscription Broker",
        "role": "provider leasing and cloud-boundary enforcement",
        "entrypoints": ["/v1/subscriptions/providers", "/v1/subscriptions/leases", "/v1/subscriptions/summary"],
        "status": "live",
    },
    {
        "id": "capacity-governor",
        "label": "Capacity Governor",
        "role": "runtime arbitration of GPU, queue, benchmark, and harvesting contention posture",
        "entrypoints": ["/v1/governor"],
        "status": "live",
    },
]


SPECIALIST_LAYER = {
    "general-assistant": {
        "label": "General Assistant",
        "role": "read-mostly ops, status, and triage",
        "authority": "read, report, delegate",
        "status": "live",
    },
    "research-agent": {
        "label": "Research Agent",
        "role": "external research and synthesis",
        "authority": "research, summarize, request lease",
        "status": "live",
    },
    "knowledge-agent": {
        "label": "Knowledge Agent",
        "role": "internal retrieval and graph/document memory",
        "authority": "retrieve, search, explain",
        "status": "live",
    },
    "coding-agent": {
        "label": "Coding Agent",
        "role": "repo mutation, testing, and controlled code execution",
        "authority": "write inside governed repo and task bounds",
        "status": "live",
    },
    "creative-agent": {
        "label": "Creative Agent",
        "role": "image and video generation workflows",
        "authority": "queue generation and inspect results",
        "status": "live",
    },
    "home-agent": {
        "label": "Home Agent",
        "role": "bounded home automation execution",
        "authority": "bounded device control under escalation policy",
        "status": "live",
    },
    "media-agent": {
        "label": "Media Agent",
        "role": "bounded media search and queue monitoring",
        "authority": "search and monitor; add/delete remain constrained",
        "status": "live",
    },
    "stash-agent": {
        "label": "Stash Agent",
        "role": "bounded stash/library management",
        "authority": "catalog and tagging within domain bounds",
        "status": "live",
    },
    "data-curator": {
        "label": "Data Curator",
        "role": "personal-data ingestion and indexing",
        "authority": "scan, parse, index, and sync within curation bounds",
        "status": "live",
    },
}


COMMAND_RIGHTS = get_command_rights_registry().get("profiles", [])


POLICY_CLASSES = get_policy_class_registry().get("classes", [])
WORKLOAD_CLASSES = get_workload_class_registry().get("classes", [])

WORKLOAD_ALIASES = {
    "interactive_architecture": "architecture_planning",
    "multi_file_implementation": "coding_implementation",
    "async_backlog_execution": "coding_implementation",
    "repo_wide_audit": "repo_audit",
    "cheap_bulk_transform": "background_transform",
    "search_heavy_planning": "research_synthesis",
    "private_internal_automation": "private_automation",
}


WORKLOAD_GUIDANCE = [
    {
        "id": "research_parallel",
        "label": "Research, broad exploration, and synthesis",
        "strategy": "manager_supervisor_plus_parallel_subagents",
        "supervisor_lane": "frontier_cloud",
        "worker_lane": "local_worker_plane",
        "judge_lane": "local_judge_plane",
    },
    {
        "id": "coding_tight",
        "label": "Tightly coupled coding or infrastructure changes",
        "strategy": "manager_first_tight_hierarchy",
        "supervisor_lane": "frontier_cloud_or_sovereign_by_policy",
        "worker_lane": "coding_worker_plane",
        "judge_lane": "local_judge_plane",
    },
    {
        "id": "sovereign_content",
        "label": "Uncensored, explicit, or refusal-sensitive content",
        "strategy": "sovereign_supervisor_plus_local_workers",
        "supervisor_lane": "sovereign_local",
        "worker_lane": "uncensored_local_plane",
        "judge_lane": "local_judge_plane",
    },
]


MODEL_PLANES = [
    {
        "id": "frontier_cloud",
        "label": "Frontier Cloud Meta Lane",
        "role": "best-in-class planning, architecture, critique, and review for allowed workloads",
        "status": "live",
    },
    {
        "id": "sovereign_local",
        "label": "Sovereign Local Meta Lane",
        "role": "private, uncensored, refusal-resilient supervision for protected workloads",
        "status": "live",
    },
    {
        "id": "local_worker_plane",
        "label": "Local Worker Plane",
        "role": "bulk execution, background loops, transforms, and private local work",
        "status": "live",
    },
    {
        "id": "local_judge_plane",
        "label": "Judge and Verifier Plane",
        "role": "score quality, regressions, and promotions without taking command rights",
        "status": "live",
    },
]


def _build_autonomy_activation_summary(live_presence: dict[str, Any]) -> dict[str, Any]:
    from .model_governance import get_current_autonomy_phase, get_next_autonomy_phase, get_unmet_autonomy_prerequisites

    activation, current_phase = get_current_autonomy_phase()
    current_phase_id = str(activation.get("current_phase_id") or "")
    next_phase = get_next_autonomy_phase(activation, phase_id=current_phase_id)
    next_phase_id = str(next_phase.get("id") or "").strip() or None
    next_phase_blockers = get_unmet_autonomy_prerequisites(activation, phase_id=next_phase_id) if next_phase_id else []
    return {
        "status": str(activation.get("status") or "configured"),
        "activation_state": str(activation.get("activation_state") or "unknown"),
        "current_phase_id": current_phase_id or None,
        "current_phase_status": str(current_phase.get("status") or "unknown"),
        "current_phase_scope": str(current_phase.get("scope") or "") or None,
        "next_phase_id": next_phase_id,
        "next_phase_status": str(next_phase.get("status") or "complete") if next_phase_id else None,
        "next_phase_scope": str(next_phase.get("scope") or "") or None,
        "next_phase_blocker_count": len(next_phase_blockers),
        "next_phase_blocker_ids": [str(item.get("id") or "").strip() for item in next_phase_blockers if str(item.get("id") or "").strip()],
        "broad_autonomy_enabled": bool(activation.get("broad_autonomy_enabled")),
        "runtime_mutations_approval_gated": bool(activation.get("runtime_mutations_approval_gated", True)),
        "enabled_agents": list(current_phase.get("enabled_agents", [])),
        "allowed_workload_classes": list(current_phase.get("allowed_workload_classes", [])),
        "blocked_workload_classes": list(current_phase.get("blocked_workload_classes", [])),
        "presence_state": live_presence.get("state"),
        "presence_reason": live_presence.get("effective_reason"),
    }


def _build_constitution_snapshot() -> dict[str, Any]:
    constitution = get_system_constitution()
    return {
        "label": constitution.get("label", "Athanor System Constitution"),
        "source": "system-constitution.json + policy registry",
        "enforcement": constitution.get("enforcement", "highest_non_human_authority"),
        "version": constitution.get("version", "unknown"),
        "core_rules": list(constitution.get("no_go_rules", [])),
        "local_only_domains": list(constitution.get("local_only_domains", [])),
    }


async def _build_operational_governance() -> dict[str, Any]:
    capacity = get_capacity_governor_registry()
    economic = get_economic_governance_registry()
    presence = get_operator_presence_model()
    lifecycle = get_data_lifecycle_registry()
    backup_restore = get_backup_restore_readiness()
    tool_permissions = get_tool_permission_registry()
    release_ritual = get_release_ritual_registry()
    from .governor import build_governor_snapshot, build_operations_readiness_snapshot

    runtime_status = "live"
    runtime_error = ""
    try:
        governor_snapshot = await build_governor_snapshot()
        readiness_snapshot = await build_operations_readiness_snapshot()
    except Exception as exc:
        governor_snapshot = {}
        readiness_snapshot = {}
        runtime_status = "degraded"
        runtime_error = str(exc)[:160]
    capacity_snapshot = dict(governor_snapshot.get("capacity") or {})
    live_economic = dict(readiness_snapshot.get("economic_governance") or {})
    live_lifecycle = dict(readiness_snapshot.get("data_lifecycle") or {})
    live_backup_restore = dict(readiness_snapshot.get("backup_restore") or {})
    live_tool_permissions = dict(readiness_snapshot.get("tool_permissions") or {})
    live_release_ritual = dict(readiness_snapshot.get("release_ritual") or {})
    live_presence = dict(governor_snapshot.get("presence") or {})
    live_autonomy = dict(readiness_snapshot.get("autonomy_activation") or {})
    autonomy_summary = _build_autonomy_activation_summary(live_presence)
    if live_autonomy:
        autonomy_summary.update(
            {
                "status": str(live_autonomy.get("status") or autonomy_summary["status"]),
                "activation_state": str(
                    live_autonomy.get("activation_state") or autonomy_summary["activation_state"]
                ),
                "current_phase_id": live_autonomy.get("current_phase_id") or autonomy_summary["current_phase_id"],
                "current_phase_status": str(
                    live_autonomy.get("current_phase_status") or autonomy_summary["current_phase_status"]
                ),
                "current_phase_scope": live_autonomy.get("current_phase_scope") or autonomy_summary["current_phase_scope"],
                "enabled_agents": list(live_autonomy.get("enabled_agents", autonomy_summary["enabled_agents"])),
                "allowed_workload_classes": list(
                    live_autonomy.get("allowed_workload_classes", autonomy_summary["allowed_workload_classes"])
                ),
                "blocked_workload_classes": list(
                    live_autonomy.get("blocked_workload_classes", autonomy_summary["blocked_workload_classes"])
                ),
            }
        )

    return {
        "capacity_governor": {
            "status": runtime_status if capacity_snapshot else capacity.get("status", runtime_status),
            "arbitration_order": list(capacity.get("priority_order", [])),
            "time_window_count": len(capacity.get("time_windows", [])),
            "posture": capacity_snapshot.get("posture"),
            "active_window_count": len(capacity_snapshot.get("active_time_windows", [])),
        },
        "economic_governance": {
            "status": live_economic.get("status", economic.get("status", "configured")),
            "reserve_lanes": list(economic.get("premium_reserve_lanes", [])),
            "downgrade_order": list(economic.get("downgrade_order", [])),
            "provider_count": live_economic.get("provider_count"),
            "recent_lease_count": live_economic.get("recent_lease_count"),
        },
        "presence_model": {
            "status": presence.get("status", "configured"),
            "default_state": presence.get("default_state", "unknown"),
            "states": list(presence.get("states", [])),
            "effective_state": live_presence.get("state"),
            "effective_reason": live_presence.get("effective_reason"),
        },
        "data_lifecycle": {
            "status": live_lifecycle.get("status", lifecycle.get("status", "configured")),
            "class_count": len(lifecycle.get("classes", [])),
            "sovereign_only_classes": [
                entry["id"]
                for entry in lifecycle.get("classes", [])
                if entry.get("cloud_allowed") is False
            ],
            "run_count": live_lifecycle.get("run_count"),
            "eval_artifact_count": live_lifecycle.get("eval_artifact_count"),
        },
        "backup_restore": {
            "status": live_backup_restore.get("status", backup_restore.get("status", "configured")),
            "critical_store_count": len(backup_restore.get("critical_stores", [])),
            "drill_status": live_backup_restore.get("status", "planned"),
            "verified_store_count": live_backup_restore.get("verified_store_count"),
            "last_drill_at": live_backup_restore.get("last_drill_at"),
        },
        "tool_permissions": {
            "status": live_tool_permissions.get("status", tool_permissions.get("status", "configured")),
            "subject_count": len(tool_permissions.get("subjects", [])),
            "default_mode": tool_permissions.get("default_mode", "governor_mediated"),
            "enforced_subject_count": live_tool_permissions.get("enforced_subject_count"),
            "denied_action_count": live_tool_permissions.get("denied_action_count"),
        },
        "release_ritual": {
            "status": live_release_ritual.get("status", release_ritual.get("status", "configured")),
            "tiers": list(release_ritual.get("tiers", [])),
            "active_promotion_count": live_release_ritual.get("active_promotion_count"),
            "last_rehearsal_at": live_release_ritual.get("last_rehearsal_at"),
        },
        "autonomy_activation": autonomy_summary,
        "runtime_state": {
            "status": runtime_status,
            "error": runtime_error or None,
        },
    }


def _build_registry_versions() -> dict[str, str]:
    return {
        "constitution": get_system_constitution().get("version", "unknown"),
        "command_rights": get_command_rights_registry().get("version", "unknown"),
        "policy_classes": get_policy_class_registry().get("version", "unknown"),
        "capacity_governor": get_capacity_governor_registry().get("version", "unknown"),
        "economic_governance": get_economic_governance_registry().get("version", "unknown"),
        "data_lifecycle": get_data_lifecycle_registry().get("version", "unknown"),
        "presence_model": get_operator_presence_model().get("version", "unknown"),
        "tool_permissions": get_tool_permission_registry().get("version", "unknown"),
        "backup_restore": get_backup_restore_readiness().get("version", "unknown"),
        "release_ritual": get_release_ritual_registry().get("version", "unknown"),
        "autonomy_activation": get_autonomy_activation_registry().get("version", "unknown"),
        "platform_topology": get_platform_topology().get("version", "unknown"),
        "project_maturity": get_project_maturity_registry().get("version", "unknown"),
        "docs_lifecycle": get_docs_lifecycle_registry().get("version", "unknown"),
        "program_operating_system": get_program_operating_system().get("version", "unknown"),
    }


def _build_meta_lanes(policy: dict[str, Any]) -> list[dict[str, Any]]:
    providers = sorted(dict(policy.get("providers") or {}).keys())
    frontier_examples = [provider for provider in providers if provider != "athanor_local"]
    return [
        {
            "id": "frontier_cloud",
            "label": "Frontier Cloud Meta Lead",
            "lead": "Claude",
            "default_for": ["cloud_safe", "private_but_cloud_allowed", "hybrid_abstractable"],
            "cloud_allowed": True,
            "status": "live",
            "examples": frontier_examples,
        },
        {
            "id": "sovereign_local",
            "label": "Sovereign Local Meta Lead",
            "lead": "Local sovereign supervisor",
            "default_for": ["refusal_sensitive", "sovereign_only"],
            "cloud_allowed": False,
            "status": "live",
            "examples": ["reasoning", "coding", "uncensored"],
        },
    ]


async def build_system_map_snapshot(agent_metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    policy = get_policy_snapshot()
    specialists = []
    for agent_id, meta in agent_metadata.items():
        specialist_meta = SPECIALIST_LAYER.get(agent_id, {})
        specialists.append(
            {
                "id": agent_id,
                "label": specialist_meta.get("label", agent_id),
                "role": specialist_meta.get("role", meta.get("description", "")),
                "authority": specialist_meta.get("authority", "scoped execution"),
                "tool_count": len(meta.get("tools", [])),
                "mode": meta.get("type", "reactive"),
                "status": specialist_meta.get("status", "live"),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "owner": {
            "id": "shaun",
            "label": "Shaun",
            "role": "owner",
        },
        "constitution": _build_constitution_snapshot(),
        "governor": {
            "label": "Athanor governor",
            "role": "runtime posture and fallback authority",
            "status": "live",
            "rights": [
                "route work",
                "pause or resume automation",
                "choose fallback or degraded mode",
                "arbitrate capacity posture",
                "enforce release-tier posture",
            ],
        },
        "authority_order": AUTHORITY_ORDER,
        "meta_lanes": _build_meta_lanes(policy),
        "control_stack": CONTROL_STACK,
        "specialists": specialists,
        "model_planes": MODEL_PLANES,
        "command_rights": COMMAND_RIGHTS,
        "policy_classes": POLICY_CLASSES,
        "operational_governance": await _build_operational_governance(),
        "workload_guidance": WORKLOAD_GUIDANCE,
        "registry_versions": _build_registry_versions(),
        "policy_source": policy.get("policy_source", "unknown"),
        "platform_topology": get_platform_topology(),
        "project_portfolio": get_project_maturity_registry(),
        "docs_lifecycle": get_docs_lifecycle_registry(),
        "program_operating_system": get_program_operating_system(),
    }


def normalize_workload_class(task_class: str) -> str:
    return WORKLOAD_ALIASES.get(task_class, task_class)


def classify_policy_class(
    prompt: str,
    metadata: dict[str, Any] | None = None,
    task_class: str = "",
) -> dict[str, Any]:
    text = prompt.lower()
    meta = metadata or {}
    workload = _workload_profile(task_class)
    policy_class = str(meta.get("policy_class") or workload.get("policy_default", "cloud_safe"))

    if bool(meta.get("sovereign_only")):
        policy_class = "sovereign_only"
    elif any(token in text for token in ("nsfw", "explicit", "uncensored", "taboo", "erotic")):
        policy_class = "refusal_sensitive"
    elif any(token in text for token in ("abstract", "redacted", "structure only", "outline first")):
        policy_class = "hybrid_abstractable"
    elif any(token in text for token in ("private", "confidential", "local only", "lan only", "never leave")):
        policy_class = "private_but_cloud_allowed"

    meta_lane = "sovereign_local" if policy_class in {"refusal_sensitive", "sovereign_only"} else "frontier_cloud"
    return {
        "policy_class": policy_class,
        "meta_lane": meta_lane,
        "cloud_allowed": policy_class in {"cloud_safe", "private_but_cloud_allowed", "hybrid_abstractable"},
        "requires_sovereign": policy_class in {"hybrid_abstractable", "refusal_sensitive", "sovereign_only"},
    }


def _approval_mode_for_autonomy(default_autonomy: str) -> str:
    mapping = {
        "A": "act_log",
        "B": "act_notify",
        "C": "propose_wait",
        "D": "suggest_only",
    }
    return mapping.get(default_autonomy, "propose_wait")


def _workload_profile(task_class: str) -> dict[str, Any]:
    normalized_id = normalize_workload_class(task_class)
    return next(
        (entry for entry in WORKLOAD_CLASSES if entry.get("id") == normalized_id),
        {
            "id": normalized_id or "private_automation",
            "label": normalized_id or "private automation",
            "policy_default": "private_but_cloud_allowed",
            "frontier_supervisor": "frontier_supervisor",
            "sovereign_supervisor": "sovereign_supervisor",
            "primary_worker_lane": "bulk_worker",
            "fallback_worker_lanes": ["coding_worker"],
            "judge_lane": "judge_verifier",
            "default_autonomy": "C",
            "parallelism": "manager_first",
        },
    )


def build_command_decision_record(
    prompt: str,
    task_class: str,
    requester: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(metadata or {})
    classification = classify_policy_class(prompt, meta, task_class=task_class)
    workload = _workload_profile(task_class)
    approved = classification["policy_class"] in {"cloud_safe", "private_but_cloud_allowed"}
    prompt_version = str(meta.get("prompt_version") or "inline-unversioned")

    reason_parts = [
        f"requester={requester}",
        f"workload={workload['id']}",
        f"policy={classification['policy_class']}",
        f"meta_lane={classification['meta_lane']}",
        f"parallelism={workload.get('parallelism', 'manager_first')}",
    ]
    if classification["requires_sovereign"]:
        reason_parts.append("sovereign_routing_required")
    elif classification["cloud_allowed"]:
        reason_parts.append("cloud_eligible")

    return {
        "id": f"decision-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "decided_by": "Athanor Governor",
        "authority_layer": "governor",
        "workload_class": workload["id"],
        "policy_class": classification["policy_class"],
        "meta_lane": classification["meta_lane"],
        "policy_version": get_policy_class_registry().get("version", "unknown"),
        "rights_version": get_command_rights_registry().get("version", "unknown"),
        "workload_registry_version": get_workload_class_registry().get("version", "unknown"),
        "prompt_version": prompt_version,
        "corpus_version": meta.get("corpus_version"),
        "reason": "; ".join(reason_parts),
        "approved": approved,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_plan_packet(
    prompt: str,
    task_class: str,
    requester: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(metadata or {})
    classification = classify_policy_class(prompt, meta, task_class=task_class)
    workload = _workload_profile(task_class)
    prompt_version = str(meta.get("prompt_version") or "inline-unversioned")

    if classification["meta_lane"] == "sovereign_local":
        supervisor_lane = workload.get("sovereign_supervisor", "sovereign_supervisor")
    else:
        supervisor_lane = workload.get("frontier_supervisor", "frontier_supervisor")

    notes = [
        f"Requester: {requester}",
        f"Workload class: {workload['label']}",
        f"Policy class: {classification['policy_class']}",
        f"Meta lane: {classification['meta_lane']}",
        f"Primary worker: {workload.get('primary_worker_lane', 'bulk_worker')}",
        f"Parallelism: {workload.get('parallelism', 'manager_first')}",
    ]
    if classification["requires_sovereign"]:
        notes.append("Keep raw content and review on sovereign local lanes.")
    elif classification["cloud_allowed"]:
        notes.append("Cloud supervision is eligible within policy boundaries.")

    return {
        "id": f"packet-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "summary": prompt[:160] or workload["label"],
        "workload_class": workload["id"],
        "policy_class": classification["policy_class"],
        "meta_lane": classification["meta_lane"],
        "supervisor_lane": supervisor_lane,
        "worker_lane": workload.get("primary_worker_lane", "bulk_worker"),
        "judge_lane": workload.get("judge_lane", "judge_verifier"),
        "fallback_worker_lanes": list(workload.get("fallback_worker_lanes", [])),
        "approval_mode": _approval_mode_for_autonomy(workload.get("default_autonomy", "C")),
        "policy_version": get_policy_class_registry().get("version", "unknown"),
        "workload_registry_version": get_workload_class_registry().get("version", "unknown"),
        "prompt_version": prompt_version,
        "corpus_version": meta.get("corpus_version"),
        "notes": notes,
    }
