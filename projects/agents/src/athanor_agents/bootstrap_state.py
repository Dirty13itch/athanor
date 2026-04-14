from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from time import monotonic
from typing import Any

from .bootstrap_registry import (
    build_bootstrap_registry_snapshot,
    get_approval_packet_registry,
    get_bootstrap_host,
    get_bootstrap_hosts,
    get_bootstrap_programs,
    get_bootstrap_slice_definitions,
    get_foundry_proving_registry,
    get_governance_drill_registry,
    get_governance_drills,
    get_bootstrap_takeover_criteria,
    get_bootstrap_takeover_registry,
    reset_bootstrap_registry_cache,
)
from .durable_state import _as_datetime, _execute, ensure_durable_state_schema, get_durable_state_status
from .foundry_state import (
    fetch_architecture_packet_record,
    fetch_project_packet_record,
    get_foundry_storage_status,
    list_deploy_candidate_records,
    list_execution_slice_records,
    list_foundry_run_records,
    list_rollback_event_records,
)
from .model_governance import get_current_autonomy_phase
from .persistence import build_checkpointer, build_checkpointer_contract, get_checkpointer_status
from .restart_proof import durable_restart_proof_path, read_durable_restart_proof

logger = logging.getLogger(__name__)

_BOOTSTRAP_READY = False
_BOOTSTRAP_ATTEMPTED = False
_BOOTSTRAP_SNAPSHOT_WRITING = False
_BOOTSTRAP_LOCK = asyncio.Lock()
_LAST_BOOTSTRAP_STATUS: dict[str, Any] = {}
_BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_TTL_SECONDS = 2.0
_BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE: dict[str, Any] | None = None
_BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT = 0.0
_BOOTSTRAP_RUNTIME_SNAPSHOT_TASK: asyncio.Task[dict[str, Any]] | None = None
_BOOTSTRAP_RUNTIME_SNAPSHOT_LOCK = asyncio.Lock()

_TERMINAL_SLICE_STATUSES = {"completed", "cancelled", "failed", "blocked"}
_READY_SLICE_STATUSES = {"queued", "ready"}
_ACTIVE_SLICE_STATUSES = {"claimed", "handed_off"}
_PASSING_VALIDATION = {"passed", "validated", "green"}
_COOLDOWN_HOST_STATUSES = {"cooldown", "quota_exhausted", "context_exhausted", "session_exhausted"}
_APPROVAL_GATED_SLICE_CLASSES = {"approval_packet", "promotion_explicit", "runtime_mutation_blocked"}
_PRESERVED_SLICE_METADATA_KEYS = (
    "approved_packets",
    "approval_granted_at",
    "approval_granted_by",
    "approval_reason",
    "last_approved_packet_id",
)
_MIRROR_TIMESTAMP_COLUMNS = {
    "claimed_at",
    "completed_at",
    "cooldown_until",
    "created_at",
    "last_heartbeat",
    "retry_at",
    "resolved_at",
    "updated_at",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _parse_iso(value: str) -> datetime | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _repo_root() -> Path:
    preferred: Path | None = None
    for base in Path(__file__).resolve().parents:
        if base.joinpath("STATUS.md").exists() and base.joinpath("config", "automation-backbone").exists():
            return base
        if base.joinpath("config", "automation-backbone").exists():
            preferred = base
    if preferred is not None:
        return preferred
    for base in Path(__file__).resolve().parents:
        if base.joinpath("config", "automation-backbone").exists():
            return base
    return Path("/workspace")


@lru_cache(maxsize=1)
def _runtime_artifact_root() -> Path:
    env_root = str(os.getenv("ATHANOR_RUNTIME_ARTIFACT_ROOT") or "").strip()
    if env_root:
        return Path(env_root)

    repo_root = _repo_root()
    if os.access(repo_root, os.W_OK):
        return repo_root

    output_root = Path("/output")
    if output_root.exists() and os.access(output_root, os.W_OK):
        return output_root

    return repo_root


def _uses_repo_artifact_layout() -> bool:
    try:
        return _runtime_artifact_root().resolve() == _repo_root().resolve()
    except OSError:
        return _runtime_artifact_root() == _repo_root()


def _bootstrap_reports_root() -> Path:
    artifact_root = _runtime_artifact_root()
    if _uses_repo_artifact_layout():
        return artifact_root / "reports" / "bootstrap"
    return artifact_root / "reports" / "bootstrap"


def _read_registry_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _effective_checkpointer_status() -> dict[str, Any]:
    status = dict(get_checkpointer_status())
    if bool(status.get("configured")) and str(status.get("mode") or "") == "uninitialized":
        try:
            build_checkpointer()
        except Exception as exc:  # pragma: no cover - defensive live fallback
            logger.warning("Unable to materialize checkpointer while building bootstrap status: %s", exc)
        status = dict(get_checkpointer_status())
    return status


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _relative_repo_path(path: Path) -> str:
    try:
        return path.relative_to(_repo_root()).as_posix()
    except ValueError:
        return path.as_posix()


def _compatibility_scan_files() -> list[Path]:
    root = _repo_root() / "projects" / "dashboard" / "src"
    if not root.exists():
        return []
    files: list[Path] = []
    for suffix in ("*.ts", "*.tsx"):
        files.extend(root.rglob(suffix))
    return sorted({path for path in files if path.is_file()})


def _is_legacy_workforce_shell(path: Path) -> bool:
    relative = _relative_repo_path(path)
    return relative.startswith("projects/dashboard/src/features/workforce/")


def _is_legacy_workforce_helper(path: Path) -> bool:
    relative = _relative_repo_path(path)
    return relative == "projects/dashboard/src/lib/api.ts"


def _compatibility_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "legacy_get_workforce": ("getWorkforce(",),
        "legacy_get_scheduled_jobs": ("getScheduledJobs(",),
        "direct_workforce_route": ('"/api/workforce', "'/api/workforce"),
    }


def _collect_compatibility_retirement_census() -> dict[str, Any]:
    matches: dict[str, list[dict[str, Any]]] = {
        "first_class_hits": [],
        "legacy_shell_hits": [],
        "legacy_helper_hits": [],
    }
    for path in _compatibility_scan_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        hit_names = [
            name
            for name, patterns in _compatibility_patterns().items()
            if any(pattern in text for pattern in patterns)
        ]
        if not hit_names:
            continue
        entry = {
            "path": _relative_repo_path(path),
            "matches": hit_names,
        }
        if _is_legacy_workforce_shell(path):
            matches["legacy_shell_hits"].append(entry)
        elif _is_legacy_workforce_helper(path):
            matches["legacy_helper_hits"].append(entry)
        else:
            matches["first_class_hits"].append(entry)
    return {
        "generated_at": _utc_now_iso(),
        "allowed_legacy_shell_prefixes": [
            "projects/dashboard/src/features/workforce/",
        ],
        "allowed_legacy_helper_paths": [
            "projects/dashboard/src/lib/api.ts",
        ],
        "first_class_hit_count": len(matches["first_class_hits"]),
        "legacy_shell_hit_count": len(matches["legacy_shell_hits"]),
        "legacy_helper_hit_count": len(matches["legacy_helper_hits"]),
        **matches,
        "complete": len(matches["first_class_hits"]) == 0,
    }


def _operator_surface_scan_files() -> list[Path]:
    root = _repo_root() / "projects" / "dashboard" / "src"
    if not root.exists():
        return []
    files: list[Path] = []
    for relative_root in ("components", "features", "app"):
        scan_root = root / relative_root
        if not scan_root.exists():
            continue
        for suffix in ("*.ts", "*.tsx"):
            files.extend(scan_root.rglob(suffix))
    return sorted(
        {
            path
            for path in files
            if path.is_file() and not _relative_repo_path(path).startswith("projects/dashboard/src/app/api/")
        }
    )


def _is_operator_surface_legacy_shell(path: Path) -> bool:
    relative = _relative_repo_path(path)
    return relative.startswith("projects/dashboard/src/features/workforce/")


def _operator_surface_canonical_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "operator_surface": ('"/api/operator/', "'/api/operator/"),
        "bootstrap_surface": ('"/api/bootstrap/', "'/api/bootstrap/"),
    }


def _operator_surface_drift_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "legacy_get_workforce": ("getWorkforce(",),
        "legacy_get_scheduled_jobs": ("getScheduledJobs(",),
        "direct_workforce_route": ('"/api/workforce', "'/api/workforce"),
        "legacy_goals_route": ('"/api/goals', "'/api/goals"),
        "legacy_tasks_route": ('"/api/tasks', "'/api/tasks"),
        "legacy_notifications_route": ('"/api/notifications', "'/api/notifications"),
        "legacy_workplan_route": ('"/api/workplan', "'/api/workplan", '"/api/workplanner', "'/api/workplanner"),
    }


def _collect_operator_surface_census() -> dict[str, Any]:
    matches: dict[str, list[dict[str, Any]]] = {
        "first_class_drift_hits": [],
        "legacy_shell_drift_hits": [],
        "first_class_canonical_hits": [],
    }
    for path in _operator_surface_scan_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        drift_hit_names = [
            name
            for name, patterns in _operator_surface_drift_patterns().items()
            if any(pattern in text for pattern in patterns)
        ]
        canonical_hit_names = [
            name
            for name, patterns in _operator_surface_canonical_patterns().items()
            if any(pattern in text for pattern in patterns)
        ]
        relative = _relative_repo_path(path)
        if drift_hit_names:
            entry = {
                "path": relative,
                "matches": drift_hit_names,
            }
            if _is_operator_surface_legacy_shell(path):
                matches["legacy_shell_drift_hits"].append(entry)
            else:
                matches["first_class_drift_hits"].append(entry)
        if canonical_hit_names and not _is_operator_surface_legacy_shell(path):
            matches["first_class_canonical_hits"].append(
                {
                    "path": relative,
                    "matches": canonical_hit_names,
                }
            )
    return {
        "generated_at": _utc_now_iso(),
        "scanned_roots": [
            "projects/dashboard/src/components",
            "projects/dashboard/src/features",
            "projects/dashboard/src/app",
        ],
        "excluded_prefixes": [
            "projects/dashboard/src/app/api/",
        ],
        "allowed_legacy_surface_prefixes": [
            "projects/dashboard/src/features/workforce/",
        ],
        "compatibility_redirect_paths": [
            "projects/dashboard/src/app/goals/page.tsx",
            "projects/dashboard/src/app/tasks/page.tsx",
            "projects/dashboard/src/app/notifications/page.tsx",
            "projects/dashboard/src/app/workplanner/page.tsx",
        ],
        "canonical_patterns": sorted(_operator_surface_canonical_patterns()),
        "drift_patterns": sorted(_operator_surface_drift_patterns()),
        "first_class_drift_count": len(matches["first_class_drift_hits"]),
        "legacy_shell_drift_count": len(matches["legacy_shell_drift_hits"]),
        "canonical_hit_count": len(matches["first_class_canonical_hits"]),
        **matches,
        "complete": len(matches["first_class_drift_hits"]) == 0 and len(matches["first_class_canonical_hits"]) > 0,
    }


def _operator_summary_alignment_surface_files() -> list[Path]:
    root = _repo_root()
    targets = [
        root / "projects" / "dashboard" / "src" / "components" / "daily-briefing.tsx",
        root / "projects" / "dashboard" / "src" / "components" / "gen-ui" / "daily-digest.tsx",
        root / "projects" / "dashboard" / "src" / "components" / "scheduled-jobs-card.tsx",
        root / "projects" / "dashboard" / "src" / "components" / "smart-stack.tsx",
        root / "projects" / "dashboard" / "src" / "components" / "work-plan.tsx",
        root / "projects" / "dashboard" / "src" / "features" / "digest" / "digest-console.tsx",
    ]
    return [path for path in targets if path.exists()]


def _operator_summary_alignment_canonical_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "operator_summary": ('"/api/operator/summary', "'/api/operator/summary"),
        "operator_summary_helper": ("getOperatorSummaryData(",),
        "operator_runs": ('"/api/operator/runs', "'/api/operator/runs"),
        "operator_backlog": ('"/api/operator/backlog', "'/api/operator/backlog"),
        "operator_approvals": ('"/api/operator/approvals', "'/api/operator/approvals"),
        "bootstrap_surface": ('"/api/bootstrap/', "'/api/bootstrap/"),
        "bootstrap_programs_helper": ("getBootstrapProgramsData(",),
    }


def _operator_summary_alignment_drift_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "digest_side_route": ('"/api/digests/latest', "'/api/digests/latest"),
        "stalled_projects_side_route": ('"/api/projects/stalled', "'/api/projects/stalled"),
        "outputs_side_route": ('"/api/outputs', "'/api/outputs"),
        "insights_side_route": ('"/api/insights', "'/api/insights"),
    }


def _collect_operator_summary_alignment_report() -> dict[str, Any]:
    drift_hits: list[dict[str, Any]] = []
    canonical_hits: list[dict[str, Any]] = []
    missing_canonical_hits: list[str] = []
    target_paths = _operator_summary_alignment_surface_files()
    for path in target_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        drift_match_names = [
            name
            for name, patterns in _operator_summary_alignment_drift_patterns().items()
            if any(pattern in text for pattern in patterns)
        ]
        canonical_match_names = [
            name
            for name, patterns in _operator_summary_alignment_canonical_patterns().items()
            if any(pattern in text for pattern in patterns)
        ]
        relative = _relative_repo_path(path)
        if drift_match_names:
            drift_hits.append({"path": relative, "matches": drift_match_names})
        if canonical_match_names:
            canonical_hits.append({"path": relative, "matches": canonical_match_names})
        else:
            missing_canonical_hits.append(relative)
    return {
        "generated_at": _utc_now_iso(),
        "target_surfaces": [_relative_repo_path(path) for path in target_paths],
        "canonical_patterns": sorted(_operator_summary_alignment_canonical_patterns()),
        "drift_patterns": sorted(_operator_summary_alignment_drift_patterns()),
        "drift_count": len(drift_hits),
        "canonical_hit_count": len(canonical_hits),
        "missing_canonical_hit_count": len(missing_canonical_hits),
        "drift_hits": drift_hits,
        "canonical_hits": canonical_hits,
        "missing_canonical_hits": missing_canonical_hits,
        "complete": len(drift_hits) == 0 and len(missing_canonical_hits) == 0 and len(canonical_hits) > 0,
    }


def _operator_fixture_parity_target_files() -> dict[str, Path]:
    root = _repo_root()
    return {
        "fixture_backend": root / "projects" / "dashboard" / "src" / "lib" / "server-agent.ts",
        "bootstrap_programs_route": root / "projects" / "dashboard" / "src" / "app" / "api" / "bootstrap" / "programs" / "route.ts",
        "bootstrap_program_detail_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "programs"
        / "[programId]"
        / "route.ts",
        "bootstrap_program_nudge_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "programs"
        / "[programId]"
        / "nudge"
        / "route.ts",
        "bootstrap_program_promote_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "programs"
        / "[programId]"
        / "promote"
        / "route.ts",
        "bootstrap_program_approve_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "programs"
        / "[programId]"
        / "approve"
        / "route.ts",
        "bootstrap_slices_route": root / "projects" / "dashboard" / "src" / "app" / "api" / "bootstrap" / "slices" / "route.ts",
        "bootstrap_slice_claim_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "slices"
        / "[sliceId]"
        / "claim"
        / "route.ts",
        "bootstrap_slice_complete_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "slices"
        / "[sliceId]"
        / "complete"
        / "route.ts",
        "bootstrap_slice_handoff_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "slices"
        / "[sliceId]"
        / "handoff"
        / "route.ts",
        "bootstrap_blockers_route": root / "projects" / "dashboard" / "src" / "app" / "api" / "bootstrap" / "blockers" / "route.ts",
        "bootstrap_handoffs_route": root / "projects" / "dashboard" / "src" / "app" / "api" / "bootstrap" / "handoffs" / "route.ts",
        "bootstrap_integrations_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "integrations"
        / "route.ts",
        "bootstrap_integration_replay_route": root
        / "projects"
        / "dashboard"
        / "src"
        / "app"
        / "api"
        / "bootstrap"
        / "integrations"
        / "[sliceId]"
        / "replay"
        / "route.ts",
    }


def _operator_fixture_parity_patterns() -> dict[str, tuple[str, ...]]:
    return {
        "fixture_backend": (
            "current_family:",
            "next_slice_id:",
            '"/v1/bootstrap/programs"',
            '"/v1/bootstrap/slices"',
            '"/v1/bootstrap/handoffs"',
            '"/v1/bootstrap/blockers"',
            '"/v1/bootstrap/integrations"',
            "bootstrapClaimMatch = basePath.match(",
            "bootstrapCompleteMatch = basePath.match(",
            "bootstrapHandoffMatch = basePath.match(",
            "bootstrapReplayMatch = basePath.match(",
            "bootstrapApproveMatch = basePath.match(",
        ),
        "bootstrap_programs_route": ("/v1/bootstrap/programs",),
        "bootstrap_program_detail_route": ("/v1/bootstrap/programs/${programId}",),
        "bootstrap_program_nudge_route": ("/v1/bootstrap/programs/${encodeURIComponent(programId)}/nudge",),
        "bootstrap_program_promote_route": ("/v1/bootstrap/programs/${encodeURIComponent(programId)}/promote",),
        "bootstrap_program_approve_route": ("/v1/bootstrap/programs/${encodeURIComponent(programId)}/approve",),
        "bootstrap_slices_route": ("/v1/bootstrap/slices",),
        "bootstrap_slice_claim_route": ("/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/claim",),
        "bootstrap_slice_complete_route": ("/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/complete",),
        "bootstrap_slice_handoff_route": ("/v1/bootstrap/slices/${encodeURIComponent(sliceId)}/handoff",),
        "bootstrap_blockers_route": ("/v1/bootstrap/blockers",),
        "bootstrap_handoffs_route": ("/v1/bootstrap/handoffs",),
        "bootstrap_integrations_route": ("/v1/bootstrap/integrations",),
        "bootstrap_integration_replay_route": ("/v1/bootstrap/integrations/${encodeURIComponent(sliceId)}/replay",),
    }


def _collect_operator_fixture_parity_report() -> dict[str, Any]:
    targets = _operator_fixture_parity_target_files()
    patterns_by_target = _operator_fixture_parity_patterns()
    missing_files: list[str] = []
    missing_patterns: list[dict[str, Any]] = []
    satisfied_targets: list[dict[str, Any]] = []
    for target_name, path in targets.items():
        if not path.exists():
            missing_files.append(_relative_repo_path(path))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            missing_files.append(_relative_repo_path(path))
            continue
        required_patterns = patterns_by_target.get(target_name, ())
        matched = [pattern for pattern in required_patterns if pattern in text]
        missing = [pattern for pattern in required_patterns if pattern not in text]
        target_result = {
            "target": target_name,
            "path": _relative_repo_path(path),
            "matched_patterns": matched,
        }
        if missing:
            target_result["missing_patterns"] = missing
            missing_patterns.append(target_result)
        else:
            satisfied_targets.append(target_result)
    return {
        "generated_at": _utc_now_iso(),
        "targets": {
            key: _relative_repo_path(path)
            for key, path in targets.items()
        },
        "missing_file_count": len(missing_files),
        "missing_files": missing_files,
        "missing_pattern_count": len(missing_patterns),
        "missing_patterns": missing_patterns,
        "satisfied_target_count": len(satisfied_targets),
        "satisfied_targets": satisfied_targets,
        "complete": len(missing_files) == 0 and len(missing_patterns) == 0 and len(satisfied_targets) > 0,
    }


def _operator_nav_lock_target_files() -> dict[str, Path]:
    root = _repo_root()
    return {
        "navigation": root / "projects" / "dashboard" / "src" / "lib" / "navigation.ts",
        "more_page": root / "projects" / "dashboard" / "src" / "app" / "more" / "page.tsx",
        "nav_attention": root / "projects" / "dashboard" / "src" / "lib" / "nav-attention.ts",
        "lens": root / "projects" / "dashboard" / "src" / "lib" / "lens.ts",
        "task_card": root / "projects" / "dashboard" / "src" / "components" / "gen-ui" / "task-card.tsx",
        "command_center": root / "projects" / "dashboard" / "src" / "features" / "overview" / "command-center.tsx",
        "history_console": root / "projects" / "dashboard" / "src" / "features" / "history" / "history-console.tsx",
        "intelligence_console": root
        / "projects"
        / "dashboard"
        / "src"
        / "features"
        / "intelligence"
        / "intelligence-console.tsx",
        "memory_console": root / "projects" / "dashboard" / "src" / "features" / "memory" / "memory-console.tsx",
        "dashboard_data": root / "projects" / "dashboard" / "src" / "lib" / "dashboard-data.ts",
        "dashboard_config": root / "projects" / "dashboard" / "src" / "lib" / "config.ts",
        "server_agent": root / "projects" / "dashboard" / "src" / "lib" / "server-agent.ts",
    }


def _operator_nav_lock_patterns() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        "navigation": {
            "required": (
                'routeClass: "compatibility_redirect"',
                'routeClass: "compatibility_shell"',
                "includeCompatibility?: boolean",
                "getCompatibilityRoutes()",
            ),
            "forbidden": (),
        },
        "more_page": {
            "required": (
                "getCompatibilityRoutes",
                "Compatibility Surfaces",
                "Compatibility",
            ),
            "forbidden": (),
        },
        "nav_attention": {
            "required": ('"/runs"', '"/inbox"', '"/backlog"'),
            "forbidden": ('"/tasks"', '"/notifications"', '"/workplanner"'),
        },
        "lens": {
            "required": ('"/runs"', '"/backlog"'),
            "forbidden": ('"/tasks"', '"/workplanner"'),
        },
        "task_card": {
            "required": ('href="/runs"',),
            "forbidden": ('href="/tasks"',),
        },
        "command_center": {
            "required": ('href="/backlog"',),
            "forbidden": ('href="/workplanner">Work planner</Link>', 'href="/workplanner"'),
        },
        "history_console": {
            "required": (
                'href={`/backlog?project=${item.projectId}`}',
                'href={`/runs?selection=${item.relatedTaskId}`}',
                "Open run",
            ),
            "forbidden": (
                'href={`/workplanner?project=${item.projectId}`}',
                'href={`/tasks?selection=${item.relatedTaskId}`}',
                "Open task",
            ),
        },
        "intelligence_console": {
            "required": (
                'href={`/runs?agent=${selectedReviewTask.agentId}`}',
                'href={`/backlog?project=${selectedReviewTask.projectId}`}',
                "Open runs",
            ),
            "forbidden": (
                'href={`/tasks?agent=${selectedReviewTask.agentId}`}',
                'href={`/workplanner?project=${selectedReviewTask.projectId}`}',
                "Open task board",
            ),
        },
        "memory_console": {
            "required": ('href={`/backlog?project=${inferProjectIdFromMemory(',),
            "forbidden": ('href={`/workplanner?project=${inferProjectIdFromMemory(',),
        },
        "dashboard_data": {
            "required": ('?? "/backlog"', 'href: "/backlog"'),
            "forbidden": ('?? "/workplanner"', 'href: "/workplanner"'),
        },
        "dashboard_config": {
            "required": (
                'primaryRoute: "/backlog?project=eoq"',
                'primaryRoute: "/backlog?project=kindred"',
                'primaryRoute: "/backlog?project=ulrich-energy"',
            ),
            "forbidden": (
                'primaryRoute: "/workplanner?project=eoq"',
                'primaryRoute: "/workplanner?project=kindred"',
                'primaryRoute: "/workplanner?project=ulrich-energy"',
            ),
        },
        "server_agent": {
            "required": (
                "current_family:",
                "next_slice_id:",
                'related_surface: "/runs"',
                'related_surface: "/inbox"',
                'artifact_refs: [{ label: "runs", href: "/runs" }]',
                'artifact_refs: [{ label: "backlog", href: "/backlog" }]',
                'deep_link: "/runs"',
                'deep_link: "/backlog"',
                'deep_link: "/inbox"',
            ),
            "forbidden": (
                'related_surface: "/tasks"',
                'related_surface: "/notifications"',
                'artifact_refs: [{ label: "tasks", href: "/tasks" }]',
                'artifact_refs: [{ label: "workplanner", href: "/workplanner" }]',
                'deep_link: "/tasks"',
                'deep_link: "/workplanner"',
                'deep_link: "/notifications"',
            ),
        },
    }


def _collect_operator_nav_lock_report() -> dict[str, Any]:
    targets = _operator_nav_lock_target_files()
    patterns_by_target = _operator_nav_lock_patterns()
    missing_files: list[str] = []
    missing_patterns: list[dict[str, Any]] = []
    forbidden_patterns: list[dict[str, Any]] = []
    satisfied_targets: list[dict[str, Any]] = []
    for target_name, path in targets.items():
        if not path.exists():
            missing_files.append(_relative_repo_path(path))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            missing_files.append(_relative_repo_path(path))
            continue
        pattern_group = patterns_by_target.get(target_name, {})
        required_patterns = tuple(pattern_group.get("required") or ())
        forbidden_candidates = tuple(pattern_group.get("forbidden") or ())
        matched = [pattern for pattern in required_patterns if pattern in text]
        missing = [pattern for pattern in required_patterns if pattern not in text]
        forbidden = [pattern for pattern in forbidden_candidates if pattern in text]
        result = {
            "target": target_name,
            "path": _relative_repo_path(path),
            "matched_patterns": matched,
        }
        if missing:
            missing_patterns.append({**result, "missing_patterns": missing})
        if forbidden:
            forbidden_patterns.append({**result, "forbidden_patterns": forbidden})
        if not missing and not forbidden:
            satisfied_targets.append(result)
    return {
        "generated_at": _utc_now_iso(),
        "targets": {key: _relative_repo_path(path) for key, path in targets.items()},
        "missing_file_count": len(missing_files),
        "missing_files": missing_files,
        "missing_pattern_count": len(missing_patterns),
        "missing_patterns": missing_patterns,
        "forbidden_pattern_count": len(forbidden_patterns),
        "forbidden_patterns": forbidden_patterns,
        "satisfied_target_count": len(satisfied_targets),
        "satisfied_targets": satisfied_targets,
        "complete": len(missing_files) == 0 and len(missing_patterns) == 0 and len(forbidden_patterns) == 0,
    }


async def _build_foundry_proving_status() -> dict[str, Any]:
    registry = get_foundry_proving_registry()
    project_id = str(registry.get("project_id") or "").strip()
    status = {
        "project_id": project_id,
        "project_packet_ref": str(registry.get("project_packet_ref") or ""),
        "architecture_packet_ref": str(registry.get("architecture_packet_ref") or ""),
        "first_proving_slice_id": str(registry.get("first_proving_slice_id") or ""),
        "first_proving_slice_packet": dict(registry.get("first_proving_slice_packet") or {}),
        "acceptance_evidence_requirements": list(registry.get("acceptance_evidence_requirements") or []),
        "candidate_evidence_requirements": list(registry.get("candidate_evidence_requirements") or []),
        "rollback_target_requirements": list(registry.get("rollback_target_requirements") or []),
        "validator_bundle": list(registry.get("validator_bundle") or []),
        "promotion_gate": dict(registry.get("promotion_gate") or {}),
        "storage": get_foundry_storage_status(),
        "packet_contract_ready": False,
        "slice_count": 0,
        "run_count": 0,
        "candidate_count": 0,
        "rollback_event_count": 0,
        "has_project_packet": False,
        "has_architecture_packet": False,
        "has_rollback_target": False,
        "promotion_or_rollback_recorded": False,
        "ready": False,
    }
    first_slice_packet = dict(status["first_proving_slice_packet"] or {})
    promotion_gate = dict(status["promotion_gate"] or {})
    status["packet_contract_ready"] = all(
        (
            project_id == "athanor",
            bool(status["project_packet_ref"]),
            bool(status["architecture_packet_ref"]),
            bool(status["first_proving_slice_id"]),
            bool(str(first_slice_packet.get("owner_agent") or "").strip()),
            bool(str(first_slice_packet.get("lane") or "").strip()),
            bool(str(first_slice_packet.get("objective") or "").strip()),
            bool(status["acceptance_evidence_requirements"]),
            bool(status["candidate_evidence_requirements"]),
            bool(status["rollback_target_requirements"]),
            bool(status["validator_bundle"]),
            bool(promotion_gate.get("require_foundry_run")),
            bool(promotion_gate.get("require_candidate")),
            bool(promotion_gate.get("require_rollback_target")),
            bool(promotion_gate.get("require_acceptance_evidence")),
            not bool(promotion_gate.get("allow_direct_ad_hoc_bypass")),
        )
    )
    if not project_id:
        return status
    try:
        project_packet, architecture_packet, slices, runs, candidates, rollback_events = await asyncio.gather(
            fetch_project_packet_record(project_id),
            fetch_architecture_packet_record(project_id),
            list_execution_slice_records(project_id, limit=200),
            list_foundry_run_records(project_id, limit=200),
            list_deploy_candidate_records(project_id, limit=200),
            list_rollback_event_records(project_id, limit=200),
        )
    except Exception:
        return status
    status["has_project_packet"] = project_packet is not None
    status["has_architecture_packet"] = architecture_packet is not None
    status["slice_count"] = len(slices)
    status["run_count"] = len(runs)
    status["candidate_count"] = len(candidates)
    status["rollback_event_count"] = len(rollback_events)
    status["has_rollback_target"] = any(bool(dict(item.get("rollback_target") or {})) for item in candidates)
    status["promotion_or_rollback_recorded"] = any(
        str(item.get("promotion_status") or "").strip() in {"promoted", "rolled_back"}
        or bool(item.get("promoted_at"))
        for item in candidates
    ) or bool(rollback_events)
    status["ready"] = all(
        (
            status["has_project_packet"],
            status["has_architecture_packet"],
            status["slice_count"] > 0,
            status["run_count"] > 0,
            status["candidate_count"] > 0,
            status["has_rollback_target"],
            status["promotion_or_rollback_recorded"],
        )
    )
    return status


def _build_governance_drill_status() -> dict[str, Any]:
    from .governance_state import build_governance_drill_snapshot

    return build_governance_drill_snapshot()


def _build_durable_persistence_packet(*, generated_at: str, takeover_ready: bool) -> dict[str, Any]:
    approval_packets = get_approval_packet_registry()
    approval_packet = next(
        (
            dict(item)
            for item in approval_packets.get("packet_types", [])
            if str(item.get("id") or "") == "db_schema_change"
        ),
        {},
    )
    persistence = _effective_checkpointer_status()
    contract = build_checkpointer_contract()
    contract["env_contract"] = {
        **dict(contract.get("env_contract") or {}),
        "configured": bool(persistence.get("configured")),
    }
    contract["driver_contract"] = {
        **dict(contract.get("driver_contract") or {}),
        "active": str(persistence.get("driver") or ""),
    }
    contract["runtime_contract"] = {
        "mode": str(persistence.get("mode") or "unknown"),
        "durable": bool(persistence.get("durable")),
        "configured": bool(persistence.get("configured")),
        "driver": str(persistence.get("driver") or ""),
        "reason": str(persistence.get("reason") or ""),
    }
    durable_state = get_durable_state_status()
    restart_proof_artifact = _durable_restart_proof_ready()
    configured = bool(persistence.get("configured"))
    durable = bool(persistence.get("durable"))
    schema_ready = bool(durable_state.get("schema_ready"))
    restart_proof_passed = bool(restart_proof_artifact.get("passed"))
    if not configured:
        restart_proof_status = "pending_activation"
    elif not durable or not schema_ready:
        restart_proof_status = "pending_approval"
    elif restart_proof_passed:
        restart_proof_status = "passed"
    else:
        restart_proof_status = "required_after_cutover"

    return {
        "generated_at": generated_at,
        "criterion_id": "durable_persistence_live",
        "contract": contract,
        "persistence": persistence,
        "durable_state": durable_state,
        "runtime_dependency_packet": {
            "env_var": str(contract.get("env_contract", {}).get("name") or "ATHANOR_POSTGRES_URL"),
            "env_example_path": "projects/agents/.env.example",
            "pyproject_path": "projects/agents/pyproject.toml",
            "required_packages": list(contract.get("dependency_contract", {}).get("required_packages") or []),
            "blank_env_behavior": str(contract.get("env_contract", {}).get("blank_means") or ""),
            "configured_env_behavior": str(contract.get("env_contract", {}).get("set_means") or ""),
        },
        "schema_authority": {
            "checkpoint_setup_authority": str(contract.get("driver_contract", {}).get("setup_authority") or ""),
            "bootstrap_mirror_sql_path": str(durable_state.get("bootstrap_sql_path") or ""),
            "affected_objects": [
                "langgraph checkpoint tables",
                "control.bootstrap_programs",
                "control.bootstrap_slices",
                "control.bootstrap_handoffs",
                "control.bootstrap_integrations",
                "control.bootstrap_blockers",
                "control.bootstrap_host_state",
            ],
            "migration_order": [
                "Validate Python dependency and env contract.",
                "Apply bootstrap_durable_state.sql to Postgres.",
                "Run PostgresSaver.setup() against the configured ATHANOR_POSTGRES_URL.",
                "Switch configured runtimes off memory fallback.",
                "Run restart-safe recovery proof.",
            ],
        },
        "launch_blocker_rules": dict(contract.get("launch_blocker_contract") or {}),
        "approval_packet": approval_packet,
        "approval_status": {
            "required": True,
            "approval_packet_id": str(approval_packet.get("id") or "db_schema_change"),
            "approval_required_for_cutover": True,
            "approval_required_for_restart_proof": True,
        },
        "restart_proof": {
            "status": restart_proof_status,
            "steps": [
                "Start a run with durable persistence enabled.",
                "Restart the agent-server during execution.",
                "Verify the persisted checkpoint resumes without duplicate destructive effects.",
                "Verify health and bootstrap status still report truthful persistence posture.",
            ],
            "evidence_paths": [
                "reports/bootstrap/durable-restart-proof.json",
                "reports/bootstrap/durable-persistence-packet.json",
                "reports/bootstrap/latest.json",
            ],
            "artifact_path": str(bootstrap_durable_restart_proof_path()),
            "artifact": restart_proof_artifact or None,
        },
        "criterion_status": {
            "passed": configured and durable and schema_ready and restart_proof_passed,
            "configured": configured,
            "durable": durable,
            "schema_ready": schema_ready,
            "restart_proof_passed": restart_proof_passed,
            "takeover_ready": takeover_ready,
        },
    }


def bootstrap_root_path() -> Path:
    artifact_root = _runtime_artifact_root()
    if _uses_repo_artifact_layout():
        return artifact_root / "var" / "bootstrap"
    return artifact_root / "bootstrap"


def bootstrap_ledger_path() -> Path:
    return bootstrap_root_path() / "ledger.sqlite"


def bootstrap_snapshot_path() -> Path:
    return _bootstrap_reports_root() / "latest.json"


def bootstrap_compatibility_census_path() -> Path:
    return _bootstrap_reports_root() / "compatibility-retirement-census.json"


def bootstrap_operator_surface_census_path() -> Path:
    return _bootstrap_reports_root() / "operator-surface-census.json"


def bootstrap_operator_summary_alignment_path() -> Path:
    return _bootstrap_reports_root() / "operator-summary-alignment.json"


def bootstrap_operator_fixture_parity_path() -> Path:
    return _bootstrap_reports_root() / "operator-fixture-parity.json"


def bootstrap_operator_nav_lock_path() -> Path:
    return _bootstrap_reports_root() / "operator-nav-lock.json"


def bootstrap_durable_persistence_packet_path() -> Path:
    return _bootstrap_reports_root() / "durable-persistence-packet.json"


def bootstrap_durable_restart_proof_path() -> Path:
    return durable_restart_proof_path()


def bootstrap_foundry_proving_packet_path() -> Path:
    return _bootstrap_reports_root() / "foundry-proving-packet.json"


def bootstrap_governance_drill_packets_path() -> Path:
    return _bootstrap_reports_root() / "governance-drill-packets.json"


def bootstrap_takeover_promotion_packet_path() -> Path:
    return _bootstrap_reports_root() / "takeover-promotion-packet.json"


def bootstrap_approval_packet_registry_path() -> Path:
    return _repo_root() / "config" / "automation-backbone" / "approval-packet-registry.json"


def bootstrap_durable_state_sql_path() -> Path:
    return _repo_root() / "projects" / "agents" / "src" / "athanor_agents" / "sql" / "bootstrap_durable_state.sql"


def _program_dir(program_id: str) -> Path:
    return bootstrap_root_path() / "programs" / program_id


def _slice_dir(slice_id: str) -> Path:
    return bootstrap_root_path() / "slices" / slice_id


def _handoff_file(handoff_id: str) -> Path:
    return bootstrap_root_path() / "handoffs" / f"{handoff_id}.json"


def _integration_queue_file(slice_id: str) -> Path:
    return bootstrap_root_path() / "integration" / "queue" / f"{slice_id}.json"


def _set_bootstrap_status(
    mode: str,
    *,
    sqlite_ready: bool,
    mirror_ready: bool,
    reason: str | None = None,
    last_snapshot_at: str | None = None,
) -> None:
    global _LAST_BOOTSTRAP_STATUS
    durable_state = get_durable_state_status()
    _LAST_BOOTSTRAP_STATUS = {
        "mode": mode,
        "authority": "hybrid_local_ledger",
        "sqlite_ready": sqlite_ready,
        "mirror_ready": mirror_ready,
        "mirror_configured": bool(durable_state.get("configured")),
        "ledger_path": str(bootstrap_ledger_path()),
        "snapshot_path": str(bootstrap_snapshot_path()),
        "reason": reason,
        "last_snapshot_at": last_snapshot_at,
        "last_updated_at": _utc_now_iso(),
    }


def get_bootstrap_status() -> dict[str, Any]:
    if not _LAST_BOOTSTRAP_STATUS:
        durable_state = get_durable_state_status()
        _set_bootstrap_status(
            "uninitialized",
            sqlite_ready=False,
            mirror_ready=bool(durable_state.get("schema_ready")),
            reason="Bootstrap ledger has not been initialized yet",
        )
    return dict(_LAST_BOOTSTRAP_STATUS)


def reset_bootstrap_state_cache() -> None:
    global _BOOTSTRAP_READY, _BOOTSTRAP_ATTEMPTED
    _BOOTSTRAP_READY = False
    _BOOTSTRAP_ATTEMPTED = False
    _invalidate_bootstrap_runtime_snapshot_cache()
    reset_bootstrap_registry_cache()
    durable_state = get_durable_state_status()
    _set_bootstrap_status(
        "uninitialized",
        sqlite_ready=False,
        mirror_ready=bool(durable_state.get("schema_ready")),
        reason="Bootstrap cache reset",
    )


def _ensure_dirs_sync() -> None:
    root = bootstrap_root_path()
    for path in (
        root,
        root / "programs",
        root / "slices",
        root / "handoffs",
        root / "integration",
        root / "integration" / "queue",
        bootstrap_snapshot_path().parent,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _slice_sort_key(slice_record: dict[str, Any]) -> tuple[int, int, str]:
    metadata = dict(slice_record.get("metadata") or {})
    try:
        order = int(metadata.get("order") or slice_record.get("priority") or 999)
    except (TypeError, ValueError):
        order = 999
    try:
        priority = int(slice_record.get("priority") or order)
    except (TypeError, ValueError):
        priority = order
    return (order, priority, str(slice_record.get("created_at") or ""))


def _slice_host_mode(slice_record: dict[str, Any]) -> str:
    metadata = dict(slice_record.get("metadata") or {})
    return str(metadata.get("host_mode") or metadata.get("execution_mode") or "").strip()


def _slice_approval_class(slice_record: dict[str, Any]) -> str:
    metadata = dict(slice_record.get("metadata") or {})
    return str(metadata.get("approval_class") or "").strip()


def _slice_catalog_id(slice_record: dict[str, Any]) -> str:
    metadata = dict(slice_record.get("metadata") or {})
    return str(metadata.get("catalog_slice_id") or slice_record.get("id") or "").strip()


def _slice_requires_explicit_approval(slice_record: dict[str, Any]) -> bool:
    metadata = dict(slice_record.get("metadata") or {})
    approval_class = _slice_approval_class(slice_record)
    if approval_class not in _APPROVAL_GATED_SLICE_CLASSES:
        return False
    return bool(metadata.get("mutates_runtime"))


def _required_packet_id_for_slice(slice_record: dict[str, Any]) -> str:
    family = str(slice_record.get("family") or "").strip()
    approval_class = _slice_approval_class(slice_record)
    metadata = dict(slice_record.get("metadata") or {})
    if family == "durable_persistence_activation" and approval_class == "approval_packet":
        return "db_schema_change"
    explicit_packet_id = str(metadata.get("blocking_packet_id") or metadata.get("approval_packet_id") or "").strip()
    return explicit_packet_id or approval_class


def _approved_packet_ids_for_slice(slice_record: dict[str, Any]) -> set[str]:
    metadata = dict(slice_record.get("metadata") or {})
    return {
        str(item).strip()
        for item in list(metadata.get("approved_packets") or [])
        if str(item).strip()
    }


def _slice_has_required_approval(slice_record: dict[str, Any]) -> bool:
    packet_id = _required_packet_id_for_slice(slice_record)
    if not packet_id:
        return False
    return packet_id in _approved_packet_ids_for_slice(slice_record)


def _slice_blocks_on_approval(slice_record: dict[str, Any]) -> bool:
    approval_class = _slice_approval_class(slice_record)
    if approval_class in {"approval_packet", "promotion_explicit"} and _slice_host_mode(slice_record) == "governed_packet":
        return False
    return _slice_requires_explicit_approval(slice_record) and not _slice_has_required_approval(slice_record)


def _slice_requires_worktree(slice_record: dict[str, Any]) -> bool:
    return _slice_host_mode(slice_record) == "code_mutation"


def _execution_slices_for_family(program_slices: list[dict[str, Any]], family_id: str) -> list[dict[str, Any]]:
    family_slices = [item for item in program_slices if str(item.get("family") or "") == family_id]
    catalog_slices = [item for item in family_slices if int(item.get("depth_level") or 1) >= 2]
    effective = catalog_slices or family_slices
    return sorted(effective, key=_slice_sort_key)


def _select_next_slice(
    family_slices: list[dict[str, Any]],
    *,
    repo_safe_only: bool = True,
) -> dict[str, Any] | None:
    eligible = []
    for item in family_slices:
        if str(item.get("status") or "") not in _READY_SLICE_STATUSES:
            continue
        if repo_safe_only and _slice_blocks_on_approval(item):
            continue
        eligible.append(item)
    if not eligible:
        return None
    eligible.sort(key=_slice_sort_key)
    return eligible[0]


def _family_seed_slice_map(program: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for seed_slice in program.get("seed_slices", []) or []:
        if not isinstance(seed_slice, dict):
            continue
        family = str(seed_slice.get("family") or "").strip()
        slice_id = str(seed_slice.get("id") or "").strip()
        if family and slice_id:
            mapping[family] = slice_id
    return mapping


def _catalog_slice_metadata(catalog_slice: dict[str, Any], *, family_seed_slice_id: str) -> dict[str, Any]:
    approval_class = str(catalog_slice.get("approval_class") or "none")
    host_mode = str(catalog_slice.get("host_mode") or "").strip()
    return {
        "seeded_from_catalog": True,
        "catalog_slice_id": str(catalog_slice.get("id") or ""),
        "family_seed_slice_id": family_seed_slice_id,
        "order": int(catalog_slice.get("order") or 0),
        "execution_mode": host_mode,
        "host_mode": host_mode,
        "mutates_repo": bool(catalog_slice.get("mutates_repo")),
        "mutates_runtime": bool(catalog_slice.get("mutates_runtime")),
        "approval_class": approval_class,
        "validator_bundle": list(catalog_slice.get("validator_bundle") or []),
        "integration_priority": int(catalog_slice.get("integration_priority") or 0),
        "retry_class": str(catalog_slice.get("retry_class") or ""),
        "blocker_class": str(catalog_slice.get("blocker_class") or ""),
        "completion_evidence": list(catalog_slice.get("completion_evidence") or []),
        "next_on_success": list(catalog_slice.get("next_on_success") or []),
        "next_on_block": list(catalog_slice.get("next_on_block") or []),
        "write_scope": list(catalog_slice.get("write_scope") or []),
        "read_scope": list(catalog_slice.get("read_scope") or []),
        "approval_packet_id": approval_class if approval_class in _APPROVAL_GATED_SLICE_CLASSES else "",
        "blocking_packet_id": approval_class if approval_class in _APPROVAL_GATED_SLICE_CLASSES else "",
    }


def _preserve_runtime_slice_metadata(existing_metadata: dict[str, Any]) -> dict[str, Any]:
    preserved: dict[str, Any] = {}
    approved_packets = sorted(
        {
            str(item).strip()
            for item in list(existing_metadata.get("approved_packets") or [])
            if str(item).strip()
        }
    )
    if approved_packets:
        preserved["approved_packets"] = approved_packets
    for key in _PRESERVED_SLICE_METADATA_KEYS:
        if key == "approved_packets":
            continue
        value = existing_metadata.get(key)
        if isinstance(value, str) and value.strip():
            preserved[key] = value.strip()
    return preserved


def _connect_sqlite_sync() -> sqlite3.Connection:
    _ensure_dirs_sync()
    connection = sqlite3.connect(bootstrap_ledger_path())
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _sqlite_connection_sync():
    connection = _connect_sqlite_sync()
    try:
        yield connection
    finally:
        connection.close()


def _ensure_sqlite_schema_sync() -> None:
    with _sqlite_connection_sync() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS bootstrap_program (
                program_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                family_order_json TEXT NOT NULL DEFAULT '[]',
                objective TEXT NOT NULL DEFAULT '',
                phase_scope TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                validator_bundle_json TEXT NOT NULL DEFAULT '[]',
                max_parallel_slices INTEGER NOT NULL DEFAULT 1,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bootstrap_slice (
                slice_id TEXT PRIMARY KEY,
                program_id TEXT NOT NULL,
                family TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                host_id TEXT NOT NULL DEFAULT '',
                current_ref TEXT NOT NULL DEFAULT '',
                worktree_path TEXT NOT NULL DEFAULT '',
                files_touched_json TEXT NOT NULL DEFAULT '[]',
                validation_status TEXT NOT NULL DEFAULT 'pending',
                open_risks_json TEXT NOT NULL DEFAULT '[]',
                next_step TEXT NOT NULL DEFAULT '',
                stop_reason TEXT NOT NULL DEFAULT '',
                resume_instructions TEXT NOT NULL DEFAULT '',
                depth_level INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 3,
                phase_scope TEXT NOT NULL DEFAULT '',
                continuation_mode TEXT NOT NULL DEFAULT 'external_bootstrap',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                claimed_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(program_id) REFERENCES bootstrap_program(program_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_bootstrap_slice_program_status
                ON bootstrap_slice(program_id, status, priority, created_at);

            CREATE TABLE IF NOT EXISTS bootstrap_handoff (
                handoff_id TEXT PRIMARY KEY,
                program_id TEXT NOT NULL,
                slice_id TEXT NOT NULL,
                family TEXT NOT NULL,
                from_host TEXT NOT NULL DEFAULT '',
                to_host TEXT NOT NULL DEFAULT '',
                objective TEXT NOT NULL DEFAULT '',
                current_ref TEXT NOT NULL DEFAULT '',
                worktree_path TEXT NOT NULL DEFAULT '',
                files_touched_json TEXT NOT NULL DEFAULT '[]',
                validation_status TEXT NOT NULL DEFAULT 'pending',
                open_risks_json TEXT NOT NULL DEFAULT '[]',
                next_step TEXT NOT NULL DEFAULT '',
                stop_reason TEXT NOT NULL DEFAULT '',
                resume_instructions TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'recorded',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS bootstrap_integration (
                integration_id TEXT PRIMARY KEY,
                program_id TEXT NOT NULL,
                slice_id TEXT NOT NULL,
                family TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'squash_commit',
                source_ref TEXT NOT NULL DEFAULT '',
                target_ref TEXT NOT NULL DEFAULT 'main',
                patch_path TEXT NOT NULL DEFAULT '',
                queue_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued',
                priority INTEGER NOT NULL DEFAULT 3,
                validation_summary_json TEXT NOT NULL DEFAULT '{}',
                blocker_id TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS bootstrap_blocker (
                blocker_id TEXT PRIMARY KEY,
                program_id TEXT NOT NULL,
                slice_id TEXT NOT NULL DEFAULT '',
                family TEXT NOT NULL DEFAULT '',
                blocker_class TEXT NOT NULL DEFAULT 'implementation_failure',
                reason TEXT NOT NULL DEFAULT '',
                approval_required INTEGER NOT NULL DEFAULT 0,
                inbox_id TEXT NOT NULL DEFAULT '',
                retry_at TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS bootstrap_host_state (
                host_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'available',
                cooldown_until TEXT,
                last_heartbeat TEXT,
                active_slice_id TEXT NOT NULL DEFAULT '',
                last_reason TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            );
            """
        )


def _load_json(value: Any, *, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    for key, value in list(record.items()):
        if key.endswith("_json"):
            default = [] if str(value).startswith("[") else {}
            record[key[:-5]] = _load_json(value, default=default)
            del record[key]
    return record


def _mirror_enabled() -> bool:
    durable_state = get_durable_state_status()
    return bool(durable_state.get("configured")) and bool(durable_state.get("schema_ready"))


async def _to_thread(func, *args):
    return await asyncio.to_thread(func, *args)


def _invalidate_bootstrap_runtime_snapshot_cache() -> None:
    global _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE, _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT
    _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE = None
    _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT = 0.0


def _prime_bootstrap_runtime_snapshot_cache(snapshot: dict[str, Any]) -> None:
    global _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE, _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT
    _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE = dict(snapshot)
    _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT = monotonic() + _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_TTL_SECONDS


async def _refresh_bootstrap_runtime_snapshot_task(*, include_snapshot_write: bool) -> dict[str, Any]:
    global _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK

    try:
        snapshot = await _build_bootstrap_runtime_snapshot_uncached(
            include_snapshot_write=include_snapshot_write
        )
        _prime_bootstrap_runtime_snapshot_cache(snapshot)
        return snapshot
    finally:
        current_task = asyncio.current_task()
        async with _BOOTSTRAP_RUNTIME_SNAPSHOT_LOCK:
            if _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK is current_task:
                _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK = None


def _query_rows_sync(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with _sqlite_connection_sync() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _execute_sync(query: str, params: tuple[Any, ...] = ()) -> None:
    with _sqlite_connection_sync() as conn:
        conn.execute(query, params)
        conn.commit()


def _sqlite_table_exists_sync(table_name: str) -> bool:
    try:
        with _sqlite_connection_sync() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
        return bool(row)
    except sqlite3.Error:
        return False


async def _mirror_record(table: str, record: dict[str, Any]) -> None:
    if not _mirror_enabled():
        return

    json_keys = {key: value for key, value in record.items() if isinstance(value, (dict, list))}
    raw_keys = {key: value for key, value in record.items() if key not in json_keys}
    now = _utc_now_iso()
    created_at = raw_keys.get("created_at")
    updated_at = raw_keys.get("updated_at")
    if "created_at" in raw_keys and not created_at:
        raw_keys["created_at"] = updated_at or now
    if "updated_at" in raw_keys and not updated_at:
        raw_keys["updated_at"] = raw_keys.get("created_at") or now
    columns = list(raw_keys.keys()) + [f"{key}_json" for key in json_keys.keys()]
    values = [
        _as_datetime(raw_keys[key]) if key in _MIRROR_TIMESTAMP_COLUMNS else raw_keys[key]
        for key in raw_keys.keys()
    ] + [json.dumps(json_keys[key]) for key in json_keys.keys()]
    conflict_key = {
        "control.bootstrap_programs": "program_id",
        "control.bootstrap_slices": "slice_id",
        "control.bootstrap_handoffs": "handoff_id",
        "control.bootstrap_integrations": "integration_id",
        "control.bootstrap_blockers": "blocker_id",
        "control.bootstrap_host_state": "host_id",
    }[table]
    assignments = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in columns
        if column != conflict_key
    )
    placeholders = ", ".join("%s" for _ in columns)
    query = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_key}) DO UPDATE SET
            {assignments}
    """
    await _execute(query, tuple(values))


async def _mirror_program(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_programs",
        {
            "program_id": record["id"],
            "label": record["label"],
            "family_order": record.get("family_order", []),
            "objective": record.get("objective", ""),
            "phase_scope": record.get("phase_scope", ""),
            "status": record.get("status", "active"),
            "validator_bundle": record.get("validator_bundle", []),
            "max_parallel_slices": int(record.get("max_parallel_slices") or 1),
            "metadata": record.get("metadata", {}),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        },
    )


async def _mirror_slice(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_slices",
        {
            "slice_id": record["id"],
            "program_id": record["program_id"],
            "family": record.get("family", ""),
            "objective": record.get("objective", ""),
            "status": record.get("status", "queued"),
            "host_id": record.get("host_id", ""),
            "current_ref": record.get("current_ref", ""),
            "worktree_path": record.get("worktree_path", ""),
            "files_touched": record.get("files_touched", []),
            "validation_status": record.get("validation_status", "pending"),
            "open_risks": record.get("open_risks", []),
            "next_step": record.get("next_step", ""),
            "stop_reason": record.get("stop_reason", ""),
            "resume_instructions": record.get("resume_instructions", ""),
            "depth_level": int(record.get("depth_level") or 1),
            "priority": int(record.get("priority") or 3),
            "phase_scope": record.get("phase_scope", ""),
            "continuation_mode": record.get("continuation_mode", "external_bootstrap"),
            "metadata": record.get("metadata", {}),
            "claimed_at": record.get("claimed_at"),
            "completed_at": record.get("completed_at"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        },
    )


async def _mirror_handoff(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_handoffs",
        {
            "handoff_id": record["id"],
            "program_id": record["program_id"],
            "slice_id": record["slice_id"],
            "family": record.get("family", ""),
            "from_host": record.get("from_host", ""),
            "to_host": record.get("to_host", ""),
            "objective": record.get("objective", ""),
            "current_ref": record.get("current_ref", ""),
            "worktree_path": record.get("worktree_path", ""),
            "files_touched": record.get("files_touched", []),
            "validation_status": record.get("validation_status", "pending"),
            "open_risks": record.get("open_risks", []),
            "next_step": record.get("next_step", ""),
            "stop_reason": record.get("stop_reason", ""),
            "resume_instructions": record.get("resume_instructions", ""),
            "status": record.get("status", "recorded"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "completed_at": record.get("completed_at"),
        },
    )


async def _mirror_integration(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_integrations",
        {
            "integration_id": record["id"],
            "program_id": record["program_id"],
            "slice_id": record["slice_id"],
            "family": record.get("family", ""),
            "method": record.get("method", "squash_commit"),
            "source_ref": record.get("source_ref", ""),
            "target_ref": record.get("target_ref", "main"),
            "patch_path": record.get("patch_path", ""),
            "queue_path": record.get("queue_path", ""),
            "status": record.get("status", "queued"),
            "priority": int(record.get("priority") or 3),
            "validation_summary": record.get("validation_summary", {}),
            "blocker_id": record.get("blocker_id", ""),
            "metadata": record.get("metadata", {}),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "completed_at": record.get("completed_at"),
        },
    )


async def _mirror_blocker(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_blockers",
        {
            "blocker_id": record["id"],
            "program_id": record.get("program_id", ""),
            "slice_id": record.get("slice_id", ""),
            "family": record.get("family", ""),
            "blocker_class": record.get("blocker_class", "implementation_failure"),
            "reason": record.get("reason", ""),
            "approval_required": bool(record.get("approval_required")),
            "inbox_id": record.get("inbox_id", ""),
            "retry_at": record.get("retry_at"),
            "status": record.get("status", "open"),
            "metadata": record.get("metadata", {}),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "resolved_at": record.get("resolved_at"),
        },
    )


async def _mirror_host_state(record: dict[str, Any]) -> None:
    await _mirror_record(
        "control.bootstrap_host_state",
        {
            "host_id": record["id"],
            "status": record.get("status", "available"),
            "cooldown_until": record.get("cooldown_until"),
            "last_heartbeat": record.get("last_heartbeat"),
            "active_slice_id": record.get("active_slice_id", ""),
            "last_reason": record.get("last_reason", ""),
            "metadata": record.get("metadata", {}),
            "updated_at": record.get("updated_at"),
        },
    )


def _seed_from_registry_sync() -> None:
    now = _utc_now_iso()
    with _sqlite_connection_sync() as conn:
        for host in get_bootstrap_hosts():
            conn.execute(
                """
                INSERT OR IGNORE INTO bootstrap_host_state (
                    host_id, status, cooldown_until, last_heartbeat, active_slice_id, last_reason, metadata_json, updated_at
                )
                VALUES (?, ?, NULL, NULL, '', '', ?, ?)
                """,
                (
                    str(host.get("id") or ""),
                    "available",
                    json.dumps({"label": host.get("label", ""), "relay_priority": host.get("relay_priority", 0)}),
                    now,
                ),
            )

        for program in get_bootstrap_programs():
            conn.execute(
                """
                INSERT OR IGNORE INTO bootstrap_program (
                    program_id, label, family_order_json, objective, phase_scope, status, validator_bundle_json,
                    max_parallel_slices, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(program.get("id") or ""),
                    str(program.get("label") or program.get("id") or ""),
                    json.dumps(program.get("family_order") or []),
                    str(program.get("objective") or ""),
                    str(program.get("phase_scope") or ""),
                    str(program.get("status") or "active"),
                    json.dumps(program.get("validator_bundle") or []),
                    int(program.get("max_parallel_slices") or 1),
                    json.dumps({"seeded_from_registry": True}),
                    now,
                    now,
                ),
            )
            for seed_slice in program.get("seed_slices", []) or []:
                if not isinstance(seed_slice, dict):
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bootstrap_slice (
                        slice_id, program_id, family, objective, status, host_id, current_ref, worktree_path,
                        files_touched_json, validation_status, open_risks_json, next_step, stop_reason,
                        resume_instructions, depth_level, priority, phase_scope, continuation_mode,
                        metadata_json, claimed_at, completed_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, '', '', '', '[]', 'pending', '[]', '', '', '', ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        str(seed_slice.get("id") or f"slice-{uuid.uuid4().hex[:10]}"),
                        str(program.get("id") or ""),
                        str(seed_slice.get("family") or ""),
                        str(seed_slice.get("objective") or ""),
                        str(seed_slice.get("status") or "queued"),
                        1,
                        int(seed_slice.get("priority") or 3),
                        str(seed_slice.get("phase_scope") or program.get("phase_scope") or ""),
                        str(seed_slice.get("continuation_mode") or "external_bootstrap"),
                        json.dumps({"seeded_from_registry": True}),
                        now,
                        now,
                    ),
                )
        conn.commit()


async def _mirror_seed_from_registry() -> None:
    if not _mirror_enabled():
        return

    now = _utc_now_iso()
    for host in get_bootstrap_hosts():
        await _mirror_host_state(
            {
                "id": str(host.get("id") or ""),
                "status": "available",
                "cooldown_until": "",
                "last_heartbeat": "",
                "active_slice_id": "",
                "last_reason": "seeded from registry",
                "metadata": {"label": host.get("label", ""), "relay_priority": host.get("relay_priority", 0)},
                "updated_at": now,
            }
        )

    for program in get_bootstrap_programs():
        program_record = {
            "id": str(program.get("id") or ""),
            "label": str(program.get("label") or program.get("id") or ""),
            "family_order": list(program.get("family_order") or []),
            "objective": str(program.get("objective") or ""),
            "phase_scope": str(program.get("phase_scope") or ""),
            "status": str(program.get("status") or "active"),
            "validator_bundle": list(program.get("validator_bundle") or []),
            "max_parallel_slices": int(program.get("max_parallel_slices") or 1),
            "metadata": {"seeded_from_registry": True},
            "created_at": now,
            "updated_at": now,
        }
        await _mirror_program(program_record)

        for seed_slice in program.get("seed_slices", []) or []:
            if not isinstance(seed_slice, dict):
                continue
            await _mirror_slice(
                {
                    "id": str(seed_slice.get("id") or f"slice-{uuid.uuid4().hex[:10]}"),
                    "program_id": program_record["id"],
                    "family": str(seed_slice.get("family") or ""),
                    "objective": str(seed_slice.get("objective") or ""),
                    "status": str(seed_slice.get("status") or "queued"),
                    "host_id": "",
                    "current_ref": "",
                    "worktree_path": "",
                    "files_touched": [],
                    "validation_status": "pending",
                    "open_risks": [],
                    "next_step": "",
                    "stop_reason": "",
                    "resume_instructions": "",
                    "depth_level": 1,
                    "priority": int(seed_slice.get("priority") or 3),
                    "phase_scope": str(seed_slice.get("phase_scope") or program_record["phase_scope"]),
                    "continuation_mode": str(seed_slice.get("continuation_mode") or "external_bootstrap"),
                    "metadata": {"seeded_from_registry": True},
                    "claimed_at": "",
                    "completed_at": "",
                    "created_at": now,
                    "updated_at": now,
                }
            )


def _sync_catalog_slices_sync() -> None:
    now = _utc_now_iso()
    catalog_slices = [
        dict(item)
        for item in get_bootstrap_slice_definitions()
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    with _sqlite_connection_sync() as conn:
        existing_metadata_by_slice_id = {
            str(row["slice_id"]): _load_json(row["metadata_json"], default={})
            for row in conn.execute(
                "SELECT slice_id, metadata_json FROM bootstrap_slice WHERE depth_level >= 2"
            ).fetchall()
        }
        for program in get_bootstrap_programs():
            program_id = str(program.get("id") or "").strip()
            if not program_id:
                continue
            allowed_families = {
                str(item).strip()
                for item in program.get("family_order", []) or []
                if str(item).strip()
            }
            seed_slice_map = _family_seed_slice_map(program)
            for catalog_slice in catalog_slices:
                family = str(catalog_slice.get("family") or "").strip()
                slice_id = str(catalog_slice.get("id") or "").strip()
                if not family or not slice_id or (allowed_families and family not in allowed_families):
                    continue
                metadata = {
                    **_catalog_slice_metadata(
                        catalog_slice,
                        family_seed_slice_id=seed_slice_map.get(family, ""),
                    ),
                    **_preserve_runtime_slice_metadata(existing_metadata_by_slice_id.get(slice_id, {})),
                }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bootstrap_slice (
                        slice_id, program_id, family, objective, status, host_id, current_ref, worktree_path,
                        files_touched_json, validation_status, open_risks_json, next_step, stop_reason,
                        resume_instructions, depth_level, priority, phase_scope, continuation_mode,
                        metadata_json, claimed_at, completed_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, '', '', '', '[]', 'pending', '[]', '', '', '', ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        slice_id,
                        program_id,
                        family,
                        str(catalog_slice.get("objective") or ""),
                        "queued",
                        2,
                        int(catalog_slice.get("order") or 999),
                        str(catalog_slice.get("phase_scope") or program.get("phase_scope") or ""),
                        "external_bootstrap",
                        json.dumps(metadata),
                        now,
                        now,
                    ),
                )
                conn.execute(
                    """
                    UPDATE bootstrap_slice
                    SET program_id = ?, family = ?, objective = ?, depth_level = ?, priority = ?, phase_scope = ?,
                        continuation_mode = ?, metadata_json = ?, updated_at = ?
                    WHERE slice_id = ? AND depth_level >= 2
                    """,
                    (
                        program_id,
                        family,
                        str(catalog_slice.get("objective") or ""),
                        2,
                        int(catalog_slice.get("order") or 999),
                        str(catalog_slice.get("phase_scope") or program.get("phase_scope") or ""),
                        "external_bootstrap",
                        json.dumps(metadata),
                        now,
                        slice_id,
                    ),
                )
        conn.commit()


def _compatibility_completion_detector_present() -> bool:
    root = _repo_root()
    return (
        root.joinpath("projects", "agents", "tests", "test_bootstrap_zero_ambiguity_contracts.py").exists()
        and root.joinpath("scripts", "validate_platform_contract.py").exists()
    )


def _operator_surface_contract_present() -> bool:
    root = _repo_root()
    contract_test_path = root / "projects" / "agents" / "tests" / "test_bootstrap_zero_ambiguity_contracts.py"
    if not contract_test_path.exists():
        return False
    try:
        text = contract_test_path.read_text(encoding="utf-8")
    except OSError:
        return False
    required_tests = (
        "def test_operator_surface_census_is_green_for_first_class_shell",
        "def test_operator_summary_alignment_is_green_for_first_class_digest_surfaces",
        "def test_operator_fixture_parity_is_green_for_canonical_operator_and_bootstrap_routes",
        "def test_operator_nav_lock_is_green_for_first_class_routes",
    )
    return all(test_name in text for test_name in required_tests)


def _foundry_proving_packet_contract_present() -> bool:
    if not bootstrap_foundry_proving_packet_path().exists():
        return False
    try:
        packet = json.loads(bootstrap_foundry_proving_packet_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    first_slice_packet = dict(packet.get("first_proving_slice_packet") or {})
    promotion_gate = dict(packet.get("promotion_gate") or {})
    return all(
        (
            str(packet.get("project_id") or "").strip() == "athanor",
            bool(packet.get("has_project_packet")),
            bool(str(packet.get("project_packet_ref") or "").strip()),
            bool(str(packet.get("architecture_packet_ref") or "").strip()),
            bool(str(packet.get("first_proving_slice_id") or "").strip()),
            bool(str(first_slice_packet.get("owner_agent") or "").strip()),
            bool(str(first_slice_packet.get("lane") or "").strip()),
            bool(str(first_slice_packet.get("objective") or "").strip()),
            bool(list(packet.get("acceptance_evidence_requirements") or [])),
            bool(list(packet.get("candidate_evidence_requirements") or [])),
            bool(list(packet.get("rollback_target_requirements") or [])),
            bool(list(packet.get("validator_bundle") or [])),
            bool(promotion_gate.get("require_foundry_run")),
            bool(promotion_gate.get("require_candidate")),
            bool(promotion_gate.get("require_rollback_target")),
            bool(promotion_gate.get("require_acceptance_evidence")),
            not bool(promotion_gate.get("allow_direct_ad_hoc_bypass")),
        )
    )


def _foundry_bypass_detector_present() -> bool:
    root = _repo_root()
    contract_test_path = root / "projects" / "agents" / "tests" / "test_bootstrap_zero_ambiguity_contracts.py"
    if not contract_test_path.exists():
        return False
    try:
        text = contract_test_path.read_text(encoding="utf-8")
    except OSError:
        return False
    required_markers = (
        "def test_athanor_proving_flow_is_packet_backed_and_not_ad_hoc",
        "/projects/{project_id}/proving",
        "materialize_foundry_proving_stage",
    )
    return all(marker in text for marker in required_markers)


def _report_contains(path: Path, *markers: str) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(marker in text for marker in markers)


def _provider_usage_evidence_ready() -> bool:
    evidence = _read_registry_json(_repo_root() / "reports" / "truth-inventory" / "provider-usage-evidence.json")
    captures = evidence.get("captures")
    return isinstance(captures, list) and any(
        isinstance(item, dict)
        and str(item.get("provider_id") or "").strip()
        and str(item.get("status") or "").strip()
        and str(item.get("observed_at") or "").strip()
        for item in captures
    )


def _vault_litellm_env_audit_ready() -> bool:
    audit = _read_registry_json(_repo_root() / "reports" / "truth-inventory" / "vault-litellm-env-audit.json")
    return all(
        (
            str(audit.get("surface_id") or "").strip() == "vault-litellm-container-env",
            str(audit.get("service_id") or "").strip() == "litellm",
            str(audit.get("host") or "").strip() == "vault",
            bool(audit.get("expected_env_names")),
            bool(str(audit.get("observed_at") or audit.get("collected_at") or "").strip()),
        )
    )


def _provider_catalog_report_ready() -> bool:
    return _report_contains(
        _repo_root() / "docs" / "operations" / "PROVIDER-CATALOG-REPORT.md",
        "# Provider Catalog Report",
        "## Verification Queue",
        "vault_provider_specific_auth_failed",
    )


def _secret_surface_report_ready() -> bool:
    return _report_contains(
        _repo_root() / "docs" / "operations" / "SECRET-SURFACE-REPORT.md",
        "# Secret Surface Report",
        "vault-litellm-container-env",
        "remediation_required",
    )


def _vault_litellm_auth_repair_packet_ready() -> bool:
    packet_types = [
        dict(item)
        for item in get_approval_packet_registry().get("packet_types", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    has_packet_type = any(str(item.get("id") or "") == "vault_provider_auth_repair" for item in packet_types)
    return has_packet_type and _report_contains(
        _repo_root() / "docs" / "operations" / "VAULT-LITELLM-AUTH-REPAIR-PACKET.md",
        "# VAULT LiteLLM Auth Repair Packet",
        "## Approved Maintenance Sequence",
        "## Read-Only Verification Commands",
    )


def _takeover_promotion_packet_ready() -> bool:
    packet = _read_registry_json(bootstrap_takeover_promotion_packet_path())
    external_posture = dict(packet.get("external_posture") or {})
    demotion_contract = dict(packet.get("demotion_contract") or {})
    fallback_modes = list(external_posture.get("fallback_modes") or demotion_contract.get("fallback_modes") or [])
    return all(
        (
            str(packet.get("promotion_rule") or "").strip() == "explicit_promotion_only",
            bool(list(packet.get("criteria") or [])),
            isinstance(packet.get("blocker_ids"), list),
            bool(list(packet.get("authority_flip_steps") or [])),
            bool(list(packet.get("reversal_path") or [])),
            bool(fallback_modes),
        )
    )


def _takeover_criteria_ready() -> bool:
    packet = _read_registry_json(bootstrap_takeover_promotion_packet_path())
    if list(packet.get("criteria") or []):
        return True
    snapshot = _read_registry_json(bootstrap_snapshot_path())
    takeover = dict(snapshot.get("takeover") or {})
    status = dict(snapshot.get("status") or {})
    status_takeover = dict(status.get("takeover") or {})
    return bool(list(status_takeover.get("criteria") or takeover.get("criteria") or []))


def _governance_drill_contract_present() -> bool:
    registry = get_governance_drill_registry()
    drills = get_governance_drills()
    if not registry or not drills:
        return False
    runbook_registry = _read_registry_json(_repo_root() / "config" / "automation-backbone" / "operator-runbooks.json")
    runbook_ids = {
        str(item.get("id") or "").strip()
        for item in runbook_registry.get("runbooks", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    required_headings = (
        "## Constrained mode",
        "## Degraded mode",
        "## Recovery-only",
        "## Blocked approval",
        "## Restore drill",
        "## Failed promotion",
    )
    doc_text = _read_text_if_exists(_repo_root() / "docs" / "operations" / "OPERATOR_RUNBOOKS.md")
    if not doc_text:
        return False
    return all(str(item.get("runbook_id") or "") in runbook_ids for item in drills) and all(
        heading in doc_text for heading in required_headings
    )


def _governance_evidence_contract_present() -> bool:
    state_source = _read_text_if_exists(
        _repo_root() / "projects" / "agents" / "src" / "athanor_agents" / "governance_state.py"
    )
    route_source = _read_text_if_exists(
        _repo_root() / "projects" / "agents" / "src" / "athanor_agents" / "routes" / "operator_governance.py"
    )
    if not state_source and not route_source:
        return False
    required_markers = (
        "def build_governance_drill_snapshot",
        "async def rehearse_governance_drill",
        "async def rehearse_all_governance_drills",
        '"/governance/drills"',
        '"/governance/drills/{drill_id}/rehearse"',
    )
    return all(marker in state_source or marker in route_source for marker in required_markers)


def _governance_dashboard_wiring_present() -> bool:
    bootstrap_console = _read_text_if_exists(
        _repo_root() / "projects" / "dashboard" / "src" / "features" / "operator" / "bootstrap-console.tsx"
    )
    operator_console = _read_text_if_exists(
        _repo_root() / "projects" / "dashboard" / "src" / "features" / "operator" / "operator-console.tsx"
    )
    if not bootstrap_console or not operator_console:
        return False
    return all(
        marker in bootstrap_console
        for marker in ("Governance drills", "takeover?.governance_drills", "drill.artifact_status")
    ) and "launch_blockers" in operator_console


def _durable_persistence_packet_ready() -> dict[str, Any]:
    return _read_registry_json(bootstrap_durable_persistence_packet_path())


def _durable_restart_proof_ready() -> dict[str, Any]:
    return dict(read_durable_restart_proof())


def _auto_complete_reason(slice_record: dict[str, Any]) -> str:
    if int(slice_record.get("depth_level") or 1) < 2:
        return ""
    if str(slice_record.get("status") or "") not in _READY_SLICE_STATUSES:
        return ""
    catalog_slice_id = _slice_catalog_id(slice_record)
    family = str(slice_record.get("family") or "")
    if family == "compatibility_retirement":
        census = _collect_compatibility_retirement_census()
        if catalog_slice_id == "compat-01-active-usage-census" and bootstrap_compatibility_census_path().exists():
            return "Compatibility census artifact is already current."
        if catalog_slice_id in {"compat-02-lib-api-canonicalization", "compat-03-first-class-component-cutover"} and bool(census.get("complete")):
            return "Compatibility census is already green for first-class operator surfaces."
        if (
            catalog_slice_id == "compat-04-completion-detector"
            and bool(census.get("complete"))
            and _compatibility_completion_detector_present()
        ):
            return "Compatibility completion detector is already present and the census is green."
        return ""

    if family == "durable_persistence_activation":
        packet = _durable_persistence_packet_ready()
        contract = dict(packet.get("contract") or {})
        runtime_contract = dict(contract.get("runtime_contract") or {})
        runtime_dependency_packet = dict(packet.get("runtime_dependency_packet") or {})
        schema_authority = dict(packet.get("schema_authority") or {})
        approval_packet = dict(packet.get("approval_packet") or {})
        criterion_status = dict(packet.get("criterion_status") or {})
        restart_proof = dict(packet.get("restart_proof") or {})
        if (
            catalog_slice_id == "persist-01-checkpointer-contract"
            and dict(contract.get("launch_blocker_contract") or {})
            and {"configured", "durable", "driver", "reason"}.issubset(runtime_contract)
        ):
            return "Durable persistence contract packet already freezes the checkpointer posture."
        if (
            catalog_slice_id == "persist-02-schema-packet"
            and str(approval_packet.get("id") or "") == "db_schema_change"
            and schema_authority.get("checkpoint_setup_authority")
            and schema_authority.get("migration_order")
        ):
            return "Durable schema approval packet is already defined in registry-backed truth."
        if (
            catalog_slice_id == "persist-03-runtime-dependency-packet"
            and str(runtime_dependency_packet.get("env_var") or "") == "ATHANOR_POSTGRES_URL"
            and "langgraph-checkpoint-postgres>=3.0.5" in list(runtime_dependency_packet.get("required_packages") or [])
            and "psycopg[binary]>=3.2" in list(runtime_dependency_packet.get("required_packages") or [])
            and "ATHANOR_POSTGRES_URL" in _read_text_if_exists(_repo_root() / "projects" / "agents" / ".env.example")
        ):
            return "Runtime dependency packet already freezes env and package authority for durable persistence."
        if (
            catalog_slice_id == "persist-04-activation-cutover"
            and bool(criterion_status.get("configured"))
            and bool(criterion_status.get("durable"))
            and bool(criterion_status.get("schema_ready"))
        ):
            return "Configured runtime is already using durable Postgres persistence and the durable-state schema is ready."
        if (
            catalog_slice_id == "persist-05-restart-proof"
            and bool(criterion_status.get("restart_proof_passed"))
            and str(restart_proof.get("status") or "") == "passed"
            and bootstrap_durable_restart_proof_path().exists()
        ):
            return "Durable restart proof artifact already verifies checkpoint survival and non-duplicated effect markers after restart."
    if family == "operator_surface_canonicalization":
        census = _collect_operator_surface_census()
        if (
            catalog_slice_id == "opsurf-01-shell-census"
            and bootstrap_operator_surface_census_path().exists()
            and bool(census.get("complete"))
        ):
            return "Operator-surface census already shows first-class shell surfaces reading canonical operator APIs only."
        summary_alignment = _collect_operator_summary_alignment_report()
        if (
            catalog_slice_id == "opsurf-02-summary-alignment"
            and bootstrap_operator_summary_alignment_path().exists()
            and bool(summary_alignment.get("complete"))
        ):
            return "Operator summary-alignment report already shows first-class digest and shell cards reading canonical operator or bootstrap APIs only."
        fixture_parity = _collect_operator_fixture_parity_report()
        if (
            catalog_slice_id == "opsurf-03-fixture-parity"
            and bootstrap_operator_fixture_parity_path().exists()
            and bool(fixture_parity.get("complete"))
        ):
            return "Fixture mode already exposes canonical operator and bootstrap routes, including the bootstrap mutation endpoints, through the dashboard proxy and fixture backend."
        nav_lock = _collect_operator_nav_lock_report()
        if (
            catalog_slice_id == "opsurf-04-nav-lock"
            and bootstrap_operator_nav_lock_path().exists()
            and bool(nav_lock.get("complete"))
        ):
            return "First-class navigation now points to canonical operator surfaces while compatibility pages remain explicit redirects or shells."
        if (
            catalog_slice_id == "opsurf-05-surface-contract"
            and _operator_surface_contract_present()
            and bool(census.get("complete"))
            and bool(summary_alignment.get("complete"))
            and bool(fixture_parity.get("complete"))
            and bool(nav_lock.get("complete"))
        ):
            return "Repo contract coverage now fails closed when first-class operator surfaces drift away from canonical operator and bootstrap truth."
    if family == "foundry_completion":
        foundry_status = _read_registry_json(bootstrap_foundry_proving_packet_path())
        if (
            catalog_slice_id == "foundry-01-proving-packet"
            and _foundry_proving_packet_contract_present()
        ):
            return "Foundry proving packet already locks the Athanor proving project, first slice contract, validator bundle, promotion gate, and rollback requirements."
        if (
            catalog_slice_id == "foundry-02-slice-execution"
            and bool(foundry_status.get("has_architecture_packet"))
            and int(foundry_status.get("slice_count") or 0) > 0
            and int(foundry_status.get("run_count") or 0) > 0
        ):
            return "Athanor proving slice execution is already recorded through governed architecture, execution-slice, and foundry-run records."
        if (
            catalog_slice_id == "foundry-03-candidate-evidence"
            and int(foundry_status.get("candidate_count") or 0) > 0
            and bool(foundry_status.get("has_rollback_target"))
        ):
            return "Athanor proving candidate evidence is already attached to a governed deploy candidate with a rollback target."
        if (
            catalog_slice_id == "foundry-04-promotion-or-rollback"
            and bool(foundry_status.get("promotion_or_rollback_recorded"))
        ):
            return "Athanor proving flow already includes a governed promotion or rollback record."
        if (
            catalog_slice_id == "foundry-05-bypass-detector"
            and _foundry_bypass_detector_present()
        ):
            return "Repo contract coverage now fails closed if the Athanor proving path drifts away from packet-backed foundry records."
    if family == "governance_rehearsal":
        governance_status = _build_governance_drill_status()
        if catalog_slice_id == "gov-01-drill-contracts" and _governance_drill_contract_present():
            return "Governance drill registry and operator runbooks now define every required drill contract explicitly."
        if catalog_slice_id == "gov-02-evidence-artifacts" and _governance_evidence_contract_present():
            return "Governance drill rehearsals now write standardized evidence artifacts for every required drill."
        if catalog_slice_id == "gov-03-health-and-dashboard-wiring" and _governance_dashboard_wiring_present():
            return "Bootstrap and operator surfaces now expose governance drill status directly instead of relying on prose."
        if (
            catalog_slice_id == "gov-04-live-rehearsal"
            and bool(governance_status.get("evidence_complete"))
        ):
            return "Governance drill evidence artifacts now exist for every required rehearsal, with pass/fail posture captured explicitly."
    if family == "provider_repair_preflight":
        if (
            catalog_slice_id == "prov-01-read-only-reprobe"
            and _provider_usage_evidence_ready()
            and _vault_litellm_env_audit_ready()
        ):
            return "Provider usage evidence and the VAULT LiteLLM env audit have both been refreshed from live read-only probes."
        if (
            catalog_slice_id == "prov-02-auth-classification-refresh"
            and _provider_catalog_report_ready()
            and _secret_surface_report_ready()
        ):
            return "Provider and secret-surface reports already classify unresolved lanes into explicit auth and remediation buckets."
        if (
            catalog_slice_id == "prov-03-maintenance-packet-refresh"
            and _vault_litellm_auth_repair_packet_ready()
        ):
            return "The VAULT LiteLLM auth-repair packet already freezes the approval-gated maintenance sequence and rollback path."
        if (
            catalog_slice_id == "prov-04-blocker-normalization"
            and bootstrap_snapshot_path().exists()
            and _provider_catalog_report_ready()
            and _secret_surface_report_ready()
            and _vault_litellm_auth_repair_packet_ready()
        ):
            return "Provider follow-up is already normalized into explicit reports, packets, and bootstrap blocker truth."
    if family == "takeover_promotion_check":
        if (
            catalog_slice_id == "takeover-01-criteria-evaluator"
            and _takeover_criteria_ready()
        ):
            return "Takeover readiness is already computed directly from live bootstrap evidence in the canonical snapshot."
        if (
            catalog_slice_id == "takeover-02-promotion-packet"
            and _takeover_promotion_packet_ready()
        ):
            return "The takeover promotion packet already captures criteria, blockers, authority-flip steps, and reversal path."
        if (
            catalog_slice_id == "takeover-03-demotion-contract"
            and _takeover_promotion_packet_ready()
            and bool(get_bootstrap_takeover_registry().get("external_posture"))
        ):
            return "The external-host demotion contract is already frozen in takeover registry truth and the promotion packet."
    return ""


async def _refresh_catalog_slice_states() -> list[str]:
    completed: list[str] = []
    for slice_record in await list_bootstrap_slices(limit=500):
        reason = _auto_complete_reason(slice_record)
        if not reason:
            continue
        await complete_bootstrap_slice(
            str(slice_record.get("id") or ""),
            validation_status="green",
            next_step="No manual mutation required; live evidence already satisfies this catalog slice.",
            summary=reason,
            queue_integration=False,
            completion_disposition="already_satisfied",
        )
        completed.append(str(slice_record.get("id") or ""))
    return completed


async def _mirror_catalog_slice_records() -> None:
    if not _mirror_enabled():
        return
    for slice_record in await list_bootstrap_slices(limit=500):
        if int(slice_record.get("depth_level") or 1) < 2:
            continue
        await _mirror_slice(slice_record)


async def ensure_bootstrap_state(*, force: bool = False) -> bool:
    global _BOOTSTRAP_READY, _BOOTSTRAP_ATTEMPTED
    snapshot_needed = False
    initialize_needed = False
    refresh_catalog_state = False
    async with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_READY and not force:
            schema_ready = await _to_thread(_sqlite_table_exists_sync, "bootstrap_program")
            if schema_ready:
                snapshot_needed = not _BOOTSTRAP_SNAPSHOT_WRITING and not bootstrap_snapshot_path().exists()
                if not snapshot_needed:
                    return True
            else:
                _BOOTSTRAP_READY = False
                _BOOTSTRAP_ATTEMPTED = False
        if _BOOTSTRAP_ATTEMPTED and not force:
            if not _BOOTSTRAP_READY:
                return False
        else:
            initialize_needed = True
        if initialize_needed:
            try:
                await _to_thread(_ensure_sqlite_schema_sync)
                await _to_thread(_seed_from_registry_sync)
                await _to_thread(_sync_catalog_slices_sync)
                await ensure_durable_state_schema()
                await _mirror_seed_from_registry()
            except Exception as exc:
                logger.exception("Failed to initialize bootstrap state")
                _BOOTSTRAP_ATTEMPTED = True
                _BOOTSTRAP_READY = False
                _set_bootstrap_status(
                    "error",
                    sqlite_ready=False,
                    mirror_ready=False,
                    reason=f"Bootstrap initialization failed: {exc}",
                )
                return False

            _BOOTSTRAP_ATTEMPTED = True
            _BOOTSTRAP_READY = True
            _set_bootstrap_status(
                "ready",
                sqlite_ready=True,
                mirror_ready=_mirror_enabled(),
                reason=None,
            )
            snapshot_needed = True
            refresh_catalog_state = True
        elif force and _BOOTSTRAP_READY:
            await _to_thread(_sync_catalog_slices_sync)
            refresh_catalog_state = True
    if snapshot_needed:
        await _write_snapshot_files()
    if refresh_catalog_state:
        await _refresh_catalog_slice_states()
        await _mirror_catalog_slice_records()
        await _write_snapshot_files()
    return True


async def list_bootstrap_slices(
    *,
    program_id: str = "",
    status: str = "",
    family: str = "",
    host_id: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            slice_id,
            program_id,
            family,
            objective,
            status,
            host_id,
            current_ref,
            worktree_path,
            files_touched_json,
            validation_status,
            open_risks_json,
            next_step,
            stop_reason,
            resume_instructions,
            depth_level,
            priority,
            phase_scope,
            continuation_mode,
            metadata_json,
            claimed_at,
            completed_at,
            created_at,
            updated_at
        FROM bootstrap_slice
        ORDER BY priority ASC, created_at ASC
        """,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        metadata = dict(row.get("metadata") or {})
        item = {
            "id": str(row.get("slice_id") or ""),
            "program_id": str(row.get("program_id") or ""),
            "family": str(row.get("family") or ""),
            "objective": str(row.get("objective") or ""),
            "status": str(row.get("status") or "queued"),
            "host_id": str(row.get("host_id") or ""),
            "current_ref": str(row.get("current_ref") or ""),
            "worktree_path": str(row.get("worktree_path") or ""),
            "files_touched": list(row.get("files_touched") or []),
            "validation_status": str(row.get("validation_status") or "pending"),
            "open_risks": list(row.get("open_risks") or []),
            "next_step": str(row.get("next_step") or ""),
            "stop_reason": str(row.get("stop_reason") or ""),
            "resume_instructions": str(row.get("resume_instructions") or ""),
            "depth_level": int(row.get("depth_level") or 1),
            "priority": int(row.get("priority") or 3),
            "phase_scope": str(row.get("phase_scope") or ""),
            "continuation_mode": str(row.get("continuation_mode") or "external_bootstrap"),
            "metadata": metadata,
            "catalog_slice_id": str(metadata.get("catalog_slice_id") or ""),
            "family_seed_slice_id": str(metadata.get("family_seed_slice_id") or ""),
            "execution_mode": str(metadata.get("execution_mode") or metadata.get("host_mode") or ""),
            "completion_evidence_paths": list(metadata.get("completion_evidence") or []),
            "blocking_packet_id": str(metadata.get("blocking_packet_id") or ""),
            "claimed_at": str(row.get("claimed_at") or ""),
            "completed_at": str(row.get("completed_at") or ""),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
        }
        if program_id and item["program_id"] != program_id:
            continue
        if status and item["status"] != status:
            continue
        if family and item["family"] != family:
            continue
        if host_id and item["host_id"] != host_id:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break
    return items


async def get_bootstrap_slice(slice_id: str) -> dict[str, Any] | None:
    rows = await list_bootstrap_slices(limit=500)
    for row in rows:
        if str(row.get("id") or "") == slice_id:
            return row
    return None


async def list_bootstrap_programs() -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    hosts = await _refresh_host_cooldowns()
    slices = await list_bootstrap_slices(limit=500)
    blockers = await list_bootstrap_blockers(limit=500)
    integrations = await list_bootstrap_integrations(limit=500)
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            program_id,
            label,
            family_order_json,
            objective,
            phase_scope,
            status,
            validator_bundle_json,
            max_parallel_slices,
            metadata_json,
            created_at,
            updated_at
        FROM bootstrap_program
        ORDER BY created_at ASC
        """,
    )
    programs: list[dict[str, Any]] = []
    for row in rows:
        programs.append(
            await _build_program_detail(
                row,
                slices=slices,
                blockers=blockers,
                integrations=integrations,
                hosts=hosts,
            )
        )
    return programs


async def get_bootstrap_program_summary(program_id: str) -> dict[str, Any] | None:
    for program in await list_bootstrap_programs():
        if str(program.get("id") or "") == program_id:
            return program
    return None


async def get_bootstrap_program_detail(program_id: str) -> dict[str, Any] | None:
    return await get_bootstrap_program_summary(program_id)


async def run_bootstrap_supervisor_cycle(
    *,
    program_id: str = "",
    execute: bool = False,
    retry_blockers: bool = True,
    process_integrations: bool = True,
) -> dict[str, Any]:
    from .bootstrap_runtime import advance_bootstrap_supervisor_cycle

    return await advance_bootstrap_supervisor_cycle(
        program_id=program_id,
        execute=execute,
        retry_blockers=retry_blockers,
        process_integrations=process_integrations,
    )


async def run_bootstrap_supervisor_loop(
    *,
    program_id: str = "",
    interval_seconds: int = 600,
    max_cycles: int | None = None,
    execute: bool = False,
    retry_blockers: bool = True,
    process_integrations: bool = True,
) -> dict[str, Any]:
    from .bootstrap_runtime import run_bootstrap_supervisor_loop as _run_bootstrap_supervisor_loop

    return await _run_bootstrap_supervisor_loop(
        program_id=program_id,
        interval_seconds=interval_seconds,
        max_cycles=max_cycles,
        execute=execute,
        retry_blockers=retry_blockers,
        process_integrations=process_integrations,
    )


async def promote_bootstrap_program(
    program_id: str,
    *,
    promoted_by: str,
    reason: str,
    force: bool = False,
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    program = await get_bootstrap_program_detail(program_id)
    if not program:
        raise ValueError(f"Unknown bootstrap program '{program_id}'")

    takeover = await build_takeover_status()
    blocker_ids = [str(item) for item in takeover.get("blocker_ids", []) if str(item)]
    pre_promotion_blockers = [item for item in blocker_ids if item != "external_dependency_removed"]
    if pre_promotion_blockers and not force:
        blocker_ids = ", ".join(pre_promotion_blockers)
        raise ValueError(f"Bootstrap takeover is not ready: {blocker_ids}")

    metadata = {
        **dict(program.get("metadata") or {}),
        "internal_builder_primary": True,
        "promoted_at": _utc_now_iso(),
        "promoted_by": promoted_by,
        "promotion_reason": reason,
        "forced": bool(force),
    }
    updated = await _update_program_record(
        program_id,
        status="takeover_promoted",
        metadata=metadata,
    )
    await _write_snapshot_files()
    return updated


async def list_bootstrap_handoffs(*, slice_id: str = "", status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            handoff_id,
            program_id,
            slice_id,
            family,
            from_host,
            to_host,
            objective,
            current_ref,
            worktree_path,
            files_touched_json,
            validation_status,
            open_risks_json,
            next_step,
            stop_reason,
            resume_instructions,
            status,
            created_at,
            updated_at,
            completed_at
        FROM bootstrap_handoff
        ORDER BY created_at DESC
        """,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "id": str(row.get("handoff_id") or ""),
            "program_id": str(row.get("program_id") or ""),
            "slice_id": str(row.get("slice_id") or ""),
            "family": str(row.get("family") or ""),
            "from_host": str(row.get("from_host") or ""),
            "to_host": str(row.get("to_host") or ""),
            "objective": str(row.get("objective") or ""),
            "current_ref": str(row.get("current_ref") or ""),
            "worktree_path": str(row.get("worktree_path") or ""),
            "files_touched": list(row.get("files_touched") or []),
            "validation_status": str(row.get("validation_status") or "pending"),
            "open_risks": list(row.get("open_risks") or []),
            "next_step": str(row.get("next_step") or ""),
            "stop_reason": str(row.get("stop_reason") or ""),
            "resume_instructions": str(row.get("resume_instructions") or ""),
            "status": str(row.get("status") or "recorded"),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "completed_at": str(row.get("completed_at") or ""),
        }
        if slice_id and item["slice_id"] != slice_id:
            continue
        if status and item["status"] != status:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break
    return items


async def list_bootstrap_blockers(*, status: str = "", family: str = "", limit: int = 50) -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            blocker_id,
            program_id,
            slice_id,
            family,
            blocker_class,
            reason,
            approval_required,
            inbox_id,
            retry_at,
            status,
            metadata_json,
            created_at,
            updated_at,
            resolved_at
        FROM bootstrap_blocker
        ORDER BY created_at DESC
        """,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "id": str(row.get("blocker_id") or ""),
            "program_id": str(row.get("program_id") or ""),
            "slice_id": str(row.get("slice_id") or ""),
            "family": str(row.get("family") or ""),
            "blocker_class": str(row.get("blocker_class") or ""),
            "reason": str(row.get("reason") or ""),
            "approval_required": bool(row.get("approval_required")),
            "inbox_id": str(row.get("inbox_id") or ""),
            "retry_at": str(row.get("retry_at") or ""),
            "status": str(row.get("status") or "open"),
            "metadata": dict(row.get("metadata") or {}),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "resolved_at": str(row.get("resolved_at") or ""),
        }
        if status and item["status"] != status:
            continue
        if family and item["family"] != family:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break
    return items


async def list_bootstrap_host_states() -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            host_id,
            status,
            cooldown_until,
            last_heartbeat,
            active_slice_id,
            last_reason,
            metadata_json,
            updated_at
        FROM bootstrap_host_state
        ORDER BY host_id ASC
        """,
    )
    return [
        {
            "id": str(row.get("host_id") or ""),
            "status": str(row.get("status") or "available"),
            "cooldown_until": str(row.get("cooldown_until") or ""),
            "last_heartbeat": str(row.get("last_heartbeat") or ""),
            "active_slice_id": str(row.get("active_slice_id") or ""),
            "last_reason": str(row.get("last_reason") or ""),
            "metadata": dict(row.get("metadata") or {}),
            "updated_at": str(row.get("updated_at") or ""),
        }
        for row in rows
    ]


async def list_bootstrap_integrations(*, status: str = "", family: str = "", limit: int = 50) -> list[dict[str, Any]]:
    await ensure_bootstrap_state()
    rows = await _to_thread(
        _query_rows_sync,
        """
        SELECT
            integration_id,
            program_id,
            slice_id,
            family,
            method,
            source_ref,
            target_ref,
            patch_path,
            queue_path,
            status,
            priority,
            validation_summary_json,
            blocker_id,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM bootstrap_integration
        ORDER BY priority ASC, created_at ASC
        """,
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "id": str(row.get("integration_id") or ""),
            "program_id": str(row.get("program_id") or ""),
            "slice_id": str(row.get("slice_id") or ""),
            "family": str(row.get("family") or ""),
            "method": str(row.get("method") or "squash_commit"),
            "source_ref": str(row.get("source_ref") or ""),
            "target_ref": str(row.get("target_ref") or "main"),
            "patch_path": str(row.get("patch_path") or ""),
            "queue_path": str(row.get("queue_path") or ""),
            "status": str(row.get("status") or "queued"),
            "priority": int(row.get("priority") or 3),
            "validation_summary": dict(row.get("validation_summary") or {}),
            "blocker_id": str(row.get("blocker_id") or ""),
            "metadata": dict(row.get("metadata") or {}),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "completed_at": str(row.get("completed_at") or ""),
        }
        if status and item["status"] != status:
            continue
        if family and item["family"] != family:
            continue
        items.append(item)
        if limit and len(items) >= limit:
            break
    return items


def _host_registry_priority(host_id: str) -> int:
    host = get_bootstrap_host(host_id) or {}
    try:
        return int(host.get("relay_priority") or 999)
    except (TypeError, ValueError):
        return 999


def _host_ready_for_assignment(host: dict[str, Any], now: datetime) -> bool:
    status = str(host.get("status") or "available")
    if status == "available":
        return True
    if status not in _COOLDOWN_HOST_STATUSES:
        return False
    cooldown_until = _parse_iso(str(host.get("cooldown_until") or ""))
    return cooldown_until is not None and cooldown_until <= now


def _host_assignment_sort_key(host: dict[str, Any]) -> tuple[int, str]:
    return (_host_registry_priority(str(host.get("id") or "")), str(host.get("id") or ""))


async def _refresh_host_cooldowns() -> list[dict[str, Any]]:
    now = _utc_now()
    hosts = await list_bootstrap_host_states()
    refreshed: list[dict[str, Any]] = []
    for host in hosts:
        if _host_ready_for_assignment(host, now) and str(host.get("status") or "") != "available":
            refreshed.append(
                await _update_host_state(
                    str(host.get("id") or ""),
                    status="available",
                    active_slice_id="",
                    last_reason="cooldown expired",
                    metadata=dict(host.get("metadata") or {}),
                )
            )
        else:
            refreshed.append(host)
    return sorted(refreshed, key=_host_assignment_sort_key)


async def _family_exit_satisfied(
    family_id: str,
    family_slices: list[dict[str, Any]],
) -> bool:
    if not family_slices:
        return False
    if family_id == "compatibility_retirement":
        census = _collect_compatibility_retirement_census()
        return bool(census.get("complete")) and _compatibility_completion_detector_present()
    if family_id == "durable_persistence_activation":
        return bool(_effective_checkpointer_status().get("durable"))
    if family_id == "operator_surface_canonicalization":
        return bool(_collect_operator_surface_census().get("complete")) and bool(
            _collect_operator_summary_alignment_report().get("complete")
        ) and bool(
            _collect_operator_fixture_parity_report().get("complete")
        ) and bool(
            _collect_operator_nav_lock_report().get("complete")
        ) and _operator_surface_contract_present()
    if family_id == "foundry_completion":
        return bool((await _build_foundry_proving_status()).get("ready"))
    if family_id == "governance_rehearsal":
        return bool(_build_governance_drill_status().get("evidence_complete"))
    return all(str(item.get("status") or "") in _TERMINAL_SLICE_STATUSES for item in family_slices)


def _family_status(
    family_slices: list[dict[str, Any]],
    family_blockers: list[dict[str, Any]],
    *,
    exit_satisfied: bool,
) -> str:
    open_approval_blockers = [item for item in family_blockers if bool(item.get("approval_required"))]
    if family_slices and exit_satisfied and all(str(item.get("status") or "") in _TERMINAL_SLICE_STATUSES for item in family_slices):
        return "completed"
    if any(str(item.get("status") or "") in _ACTIVE_SLICE_STATUSES for item in family_slices):
        return "active"
    if _select_next_slice(family_slices, repo_safe_only=True):
        return "ready"
    if open_approval_blockers or any(
        str(item.get("status") or "") in _READY_SLICE_STATUSES and _slice_blocks_on_approval(item)
        for item in family_slices
    ):
        return "waiting_approval"
    if family_blockers or any(str(item.get("status") or "") == "blocked" for item in family_slices):
        return "blocked"
    return "pending"


def _recommended_host_for_slice(slice_record: dict[str, Any], hosts: list[dict[str, Any]]) -> dict[str, Any] | None:
    now = _utc_now()
    preferred_host_id = str(slice_record.get("host_id") or "").strip()
    if preferred_host_id:
        preferred = next((host for host in hosts if str(host.get("id") or "") == preferred_host_id), None)
        if preferred and _host_ready_for_assignment(preferred, now):
            return preferred

    available_hosts = [host for host in hosts if _host_ready_for_assignment(host, now)]
    if not available_hosts:
        return None
    available_hosts.sort(key=_host_assignment_sort_key)
    return available_hosts[0]


def _open_blocker_ids_for_slice(blockers: list[dict[str, Any]], slice_id: str) -> list[str]:
    return [
        str(item.get("id") or "")
        for item in blockers
        if str(item.get("status") or "") == "open" and str(item.get("slice_id") or "") == slice_id
    ]


def _approval_wait_action(
    slice_record: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
    *,
    family_id: str,
) -> dict[str, Any] | None:
    if not slice_record:
        return None
    if not _slice_blocks_on_approval(slice_record):
        return None
    metadata = dict(slice_record.get("metadata") or {})
    blocker_ids = _open_blocker_ids_for_slice(blockers, str(slice_record.get("id") or ""))
    return {
        "kind": "approval_required",
        "family": family_id,
        "slice_id": str(slice_record.get("id") or ""),
        "approval_class": _slice_approval_class(slice_record),
        "blocking_packet_id": str(
            metadata.get("blocking_packet_id") or metadata.get("approval_packet_id") or ""
        ),
        "open_blocker_ids": blocker_ids,
    }


def _slice_sort_key(slice_record: dict[str, Any]) -> tuple[int, int, str, str]:
    metadata = dict(slice_record.get("metadata") or {})
    priority = int(slice_record.get("priority") or 999)
    order = int(metadata.get("order") or 999)
    created_at = str(slice_record.get("created_at") or "")
    slice_id = str(slice_record.get("id") or "")
    return priority, order, created_at, slice_id


def _follow_on_slice_id(
    slices: list[dict[str, Any]],
    *,
    family_id: str,
    current_slice_id: str,
) -> str:
    family_slices = [
        item
        for item in slices
        if str(item.get("family") or "") == family_id
        and str(item.get("id") or "") != current_slice_id
        and int(item.get("depth_level") or 0) >= 2
    ]
    family_slices.sort(key=_slice_sort_key)
    for item in family_slices:
        if str(item.get("status") or "") in _READY_SLICE_STATUSES:
            return str(item.get("id") or "")
    return ""


def _build_approval_context(
    active_program: dict[str, Any] | None,
    *,
    slices: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    if not active_program:
        return {}
    next_action = dict(active_program.get("next_action") or {})
    waiting_family_id = str(active_program.get("waiting_on_approval_family") or "")
    waiting_slice_id = str(active_program.get("waiting_on_approval_slice_id") or "")
    if waiting_family_id and waiting_slice_id:
        family_id = waiting_family_id
        slice_id = waiting_slice_id
    elif str(next_action.get("kind") or "") == "approval_required":
        family_id = str(next_action.get("family") or "")
        slice_id = str(next_action.get("slice_id") or "")
    else:
        return {}
    if not family_id or not slice_id:
        return {}
    slice_record = next(
        (item for item in slices if str(item.get("id") or "") == slice_id),
        None,
    )
    approval_class = str(next_action.get("approval_class") or _slice_approval_class(slice_record or {}))
    blocker_ids = list(next_action.get("open_blocker_ids") or _open_blocker_ids_for_slice(blockers, slice_id))
    follow_on_slice_id = _follow_on_slice_id(slices, family_id=family_id, current_slice_id=slice_id)

    packet_id = ""
    packet_label = ""
    approval_authority = "operator"
    summary = "Explicit operator approval is required before this bootstrap slice can continue."
    unlocks = f"Unblocks {slice_id}."
    exact_steps: list[str] = []
    rollback_steps: list[str] = []
    review_artifacts = [
        str(bootstrap_snapshot_path()),
        str(bootstrap_approval_packet_registry_path()),
    ]

    if family_id == "durable_persistence_activation":
        durable_packet = _read_registry_json(bootstrap_durable_persistence_packet_path())
        approval_packet = dict(durable_packet.get("approval_packet") or {})
        packet_id = str(approval_packet.get("id") or "db_schema_change")
        packet_label = str(approval_packet.get("label") or "DB schema change")
        approval_authority = str(approval_packet.get("approval_authority") or "operator")
        summary = "Authorize the durable persistence schema and runtime cutover maintenance window."
        unlock_target = follow_on_slice_id or "persist-05-restart-proof"
        unlocks = f"Unblocks {slice_id} and the follow-on {unlock_target} restart-proof slice."
        exact_steps = [str(step) for step in approval_packet.get("exact_steps") or [] if str(step).strip()]
        rollback_steps = [str(step) for step in approval_packet.get("rollback_steps") or [] if str(step).strip()]
        review_artifacts = [
            str(bootstrap_durable_persistence_packet_path()),
            str(bootstrap_approval_packet_registry_path()),
            str(bootstrap_durable_state_sql_path()),
            str(bootstrap_snapshot_path()),
        ]
    else:
        packet_types = [
            dict(item)
            for item in get_approval_packet_registry().get("packet_types", [])
            if isinstance(item, dict)
        ]
        packet = next(
            (
                item
                for item in packet_types
                if str(item.get("id") or "") in {
                    str(next_action.get("blocking_packet_id") or ""),
                    approval_class,
                }
            ),
            None,
        )
        if packet:
            packet_id = str(packet.get("id") or "")
            packet_label = str(packet.get("label") or packet_id)
            approval_authority = str(packet.get("approval_authority") or approval_authority)
            exact_steps = [str(step) for step in packet.get("exact_steps") or [] if str(step).strip()]
            rollback_steps = [str(step) for step in packet.get("rollback_steps") or [] if str(step).strip()]

    if not packet_id:
        packet_id = approval_class or str(next_action.get("blocking_packet_id") or "approval_required")
    if not packet_label:
        packet_label = packet_id.replace("_", " ")

    operator_instruction = f"Approve {packet_id} for {slice_id} and proceed with the maintenance window."
    if follow_on_slice_id:
        operator_instruction += f" After cutover, continue with {follow_on_slice_id}."

    return {
        "kind": "approval_required",
        "family": family_id,
        "slice_id": slice_id,
        "approval_class": approval_class,
        "packet_id": packet_id,
        "packet_label": packet_label,
        "approval_authority": approval_authority,
        "open_blocker_ids": blocker_ids,
        "follow_on_slice_id": follow_on_slice_id,
        "summary": summary,
        "unlocks": unlocks,
        "operator_instruction": operator_instruction,
        "review_artifacts": review_artifacts,
        "exact_steps": exact_steps,
        "rollback_steps": rollback_steps,
    }


def _status_for_handoff_reason(stop_reason: str) -> str:
    normalized = str(stop_reason or "").strip().lower()
    if normalized == "quota_exhausted":
        return "quota_exhausted"
    if normalized == "context_exhausted":
        return "context_exhausted"
    if normalized == "session_exhausted":
        return "session_exhausted"
    return "cooldown"


async def _build_program_detail(
    row: dict[str, Any],
    *,
    slices: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    integrations: list[dict[str, Any]],
    hosts: list[dict[str, Any]],
) -> dict[str, Any]:
    program_id_value = str(row.get("program_id") or "")
    program_slices = [item for item in slices if str(item.get("program_id") or "") == program_id_value]
    program_blockers = [item for item in blockers if str(item.get("program_id") or "") == program_id_value]
    program_integrations = [item for item in integrations if str(item.get("program_id") or "") == program_id_value]
    family_order = [str(item) for item in row.get("family_order") or [] if str(item).strip()]

    families: list[dict[str, Any]] = []
    for family_id in family_order:
        family_slices = _execution_slices_for_family(program_slices, family_id)
        family_blockers = [item for item in program_blockers if str(item.get("family") or "") == family_id and str(item.get("status") or "") == "open"]
        family_integrations = [item for item in program_integrations if str(item.get("family") or "") == family_id]
        exit_satisfied = await _family_exit_satisfied(family_id, family_slices)
        family_status = _family_status(family_slices, family_blockers, exit_satisfied=exit_satisfied)
        next_slice = _select_next_slice(family_slices, repo_safe_only=True)
        recommended_host = _recommended_host_for_slice(next_slice, hosts) if next_slice else None
        waiting_on_approval_slice = (
            _select_next_slice(family_slices, repo_safe_only=False) if family_status == "waiting_approval" else None
        )
        approval_wait_action = _approval_wait_action(
            waiting_on_approval_slice,
            family_blockers,
            family_id=family_id,
        )
        next_action = None
        if next_slice:
            next_action = {
                "kind": "dispatch",
                "family": family_id,
                "slice_id": str(next_slice.get("id") or ""),
                "host_id": str(recommended_host.get("id") or "") if recommended_host else "",
                "worktree_required": _slice_requires_worktree(next_slice),
            }
        elif approval_wait_action is not None:
            next_action = approval_wait_action
        families.append(
            {
                "id": family_id,
                "status": family_status,
                "slice_counts": {
                    "total": len(family_slices),
                    "queued": sum(1 for item in family_slices if str(item.get("status") or "") in _READY_SLICE_STATUSES),
                    "active": sum(1 for item in family_slices if str(item.get("status") or "") in _ACTIVE_SLICE_STATUSES),
                    "blocked": sum(1 for item in family_slices if str(item.get("status") or "") == "blocked"),
                    "completed": sum(1 for item in family_slices if str(item.get("status") or "") == "completed"),
                },
                "open_blockers": len(family_blockers),
                "pending_integrations": sum(1 for item in family_integrations if str(item.get("status") or "") == "queued"),
                "next_slice_id": str(next_slice.get("id") or "") if next_slice else "",
                "recommended_host_id": str(recommended_host.get("id") or "") if recommended_host else "",
                "waiting_on_approval_slice_id": str(waiting_on_approval_slice.get("id") or "") if approval_wait_action else "",
                "waiting_on_approval_blocker_ids": list(approval_wait_action.get("open_blocker_ids") or []) if approval_wait_action else [],
                "next_action": next_action,
                "exit_satisfied": exit_satisfied,
            }
        )

    dispatch_family = next((family for family in families if family["status"] not in {"completed", "waiting_approval"}), None)
    display_family = dispatch_family or next((family for family in families if family["status"] == "waiting_approval"), None)
    waiting_family = next((family for family in families if family["status"] == "waiting_approval"), None)
    next_slice = None
    recommended_host = None
    next_action = None
    if dispatch_family:
        next_slice = _select_next_slice(
            _execution_slices_for_family(program_slices, dispatch_family["id"]),
            repo_safe_only=True,
        )
        if next_slice:
            recommended_host = _recommended_host_for_slice(next_slice, hosts)
            next_action = {
                "kind": "dispatch",
                "family": str(dispatch_family.get("id") or ""),
                "slice_id": str(next_slice.get("id") or ""),
                "host_id": str(recommended_host.get("id") or "") if recommended_host else "",
                "worktree_required": _slice_requires_worktree(next_slice),
            }
    elif display_family and str(display_family.get("status") or "") == "waiting_approval":
        next_action = dict(display_family.get("next_action") or {})

    if dispatch_family is None and families and all(family["status"] == "completed" for family in families):
        derived_status = "ready_for_takeover_check"
    elif dispatch_family is None and any(family["status"] == "waiting_approval" for family in families):
        derived_status = "waiting_approval"
    elif dispatch_family and dispatch_family["status"] == "blocked":
        derived_status = "blocked"
    else:
        derived_status = str(row.get("status") or "active")

    effective_slices = []
    for family_id in family_order:
        effective_slices.extend(_execution_slices_for_family(program_slices, family_id))

    return {
        "id": program_id_value,
        "label": str(row.get("label") or program_id_value),
        "family_order": family_order,
        "objective": str(row.get("objective") or ""),
        "phase_scope": str(row.get("phase_scope") or ""),
        "status": derived_status,
        "validator_bundle": list(row.get("validator_bundle") or []),
        "max_parallel_slices": int(row.get("max_parallel_slices") or 1),
        "metadata": dict(row.get("metadata") or {}),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "slice_counts": {
            "total": len(effective_slices),
            "queued": sum(1 for item in effective_slices if str(item.get("status") or "") in _READY_SLICE_STATUSES),
            "active": sum(1 for item in effective_slices if str(item.get("status") or "") in _ACTIVE_SLICE_STATUSES),
            "blocked": sum(1 for item in effective_slices if str(item.get("status") or "") == "blocked"),
            "completed": sum(1 for item in effective_slices if str(item.get("status") or "") == "completed"),
        },
        "current_family": str(display_family.get("id") or "") if display_family else "",
        "next_slice_id": str(next_slice.get("id") or "") if next_slice else "",
        "recommended_host_id": str(recommended_host.get("id") or "") if recommended_host else "",
        "waiting_on_approval_family": str(waiting_family.get("id") or "") if waiting_family else "",
        "waiting_on_approval_slice_id": str(waiting_family.get("waiting_on_approval_slice_id") or "") if waiting_family else "",
        "next_action": next_action,
        "pending_integrations": sum(1 for item in program_integrations if str(item.get("status") or "") == "queued"),
        "families": families,
        "next_slice": next_slice,
    }


async def _write_snapshot_files() -> None:
    global _BOOTSTRAP_SNAPSHOT_WRITING
    if _BOOTSTRAP_SNAPSHOT_WRITING:
        return
    _BOOTSTRAP_SNAPSHOT_WRITING = True
    try:
        programs = await list_bootstrap_programs()
        slices = await list_bootstrap_slices(limit=500)
        handoffs = await list_bootstrap_handoffs(limit=500)
        blockers = await list_bootstrap_blockers(limit=500)
        integrations = await list_bootstrap_integrations(limit=500)
        registry_snapshot = build_bootstrap_registry_snapshot()
        compatibility_census = _collect_compatibility_retirement_census()
        operator_surface_census = _collect_operator_surface_census()
        operator_summary_alignment = _collect_operator_summary_alignment_report()
        operator_fixture_parity = _collect_operator_fixture_parity_report()
        operator_nav_lock = _collect_operator_nav_lock_report()
        foundry_proving = await _build_foundry_proving_status()
        governance_drills = _build_governance_drill_status()
        approval_packets = get_approval_packet_registry()
        status = await _build_bootstrap_runtime_snapshot_uncached(include_snapshot_write=False)
        generated_at = _utc_now_iso()
        snapshot = {
            "generated_at": generated_at,
            "status": status,
            "registry_snapshot": registry_snapshot,
            "compatibility_census": compatibility_census,
            "operator_surface_census": operator_surface_census,
            "operator_summary_alignment": operator_summary_alignment,
            "operator_fixture_parity": operator_fixture_parity,
            "operator_nav_lock": operator_nav_lock,
            "foundry_proving": foundry_proving,
            "governance_drills": governance_drills,
            "approval_packets": approval_packets,
            "programs": programs,
            "slices": slices,
            "handoffs": handoffs,
            "blockers": blockers,
            "integrations": integrations,
        }
        path = bootstrap_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        bootstrap_compatibility_census_path().write_text(json.dumps(compatibility_census, indent=2), encoding="utf-8")
        bootstrap_operator_surface_census_path().write_text(json.dumps(operator_surface_census, indent=2), encoding="utf-8")
        bootstrap_operator_summary_alignment_path().write_text(
            json.dumps(operator_summary_alignment, indent=2),
            encoding="utf-8",
        )
        bootstrap_operator_fixture_parity_path().write_text(
            json.dumps(operator_fixture_parity, indent=2),
            encoding="utf-8",
        )
        bootstrap_operator_nav_lock_path().write_text(
            json.dumps(operator_nav_lock, indent=2),
            encoding="utf-8",
        )
        bootstrap_durable_persistence_packet_path().write_text(
            json.dumps(
                _build_durable_persistence_packet(
                    generated_at=generated_at,
                    takeover_ready=bool(status.get("takeover", {}).get("ready")),
                ),
                indent=2,
            ),
            encoding="utf-8",
        )
        bootstrap_foundry_proving_packet_path().write_text(json.dumps(foundry_proving, indent=2), encoding="utf-8")
        bootstrap_governance_drill_packets_path().write_text(json.dumps(governance_drills, indent=2), encoding="utf-8")
        bootstrap_takeover_promotion_packet_path().write_text(
            json.dumps(
                {
                    "generated_at": generated_at,
                    "promotion_rule": status.get("takeover", {}).get("promotion_rule", "explicit_promotion_only"),
                    "before_takeover_authority": status.get("takeover", {}).get("before_takeover_authority", "hybrid_local_ledger"),
                    "after_takeover_authority": status.get("takeover", {}).get("after_takeover_authority", "athanor_postgres"),
                    "external_posture": status.get("takeover", {}).get("external_posture", {}),
                    "criteria": status.get("takeover", {}).get("criteria", []),
                    "blocker_ids": status.get("takeover", {}).get("blocker_ids", []),
                    "ready": bool(status.get("takeover", {}).get("ready")),
                    "demotion_contract": status.get("takeover", {}).get("external_posture", {}),
                    "authority_flip_steps": [
                        "Promote the internal builder program explicitly.",
                        "Switch builder authority from the hybrid local ledger to Athanor Postgres.",
                        "Demote external hosts to fallback, repair, emergency continuity, and explicit override only.",
                    ],
                    "reversal_path": [
                        "Unset the promoted internal builder flag.",
                        "Return builder authority to the hybrid local ledger.",
                        "Restore external hosts as primary builders until evidence is green again.",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        for program in programs:
            program_id = str(program.get("id") or "")
            program_path = _program_dir(program_id) / "program.json"
            program_path.parent.mkdir(parents=True, exist_ok=True)
            program_path.write_text(json.dumps(program, indent=2), encoding="utf-8")

        for slice_record in slices:
            slice_id = str(slice_record.get("id") or "")
            slice_path = _slice_dir(slice_id) / "slice.json"
            slice_path.parent.mkdir(parents=True, exist_ok=True)
            slice_path.write_text(json.dumps(slice_record, indent=2), encoding="utf-8")

        for handoff in handoffs:
            _handoff_file(str(handoff.get("id") or "")).write_text(json.dumps(handoff, indent=2), encoding="utf-8")

        _set_bootstrap_status(
            "ready",
            sqlite_ready=True,
            mirror_ready=_mirror_enabled(),
            reason=None,
            last_snapshot_at=generated_at,
        )
        _prime_bootstrap_runtime_snapshot_cache(status)
    finally:
        _BOOTSTRAP_SNAPSHOT_WRITING = False


async def _update_program_record(
    program_id: str,
    *,
    status: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    now = _utc_now_iso()
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_program
        SET status = ?, metadata_json = ?, updated_at = ?
        WHERE program_id = ?
        """,
        (
            status,
            json.dumps(metadata),
            now,
            program_id,
        ),
    )
    record = await get_bootstrap_program_detail(program_id)
    if not record:
        raise ValueError(f"Unknown bootstrap program '{program_id}'")
    updated = {
        **record,
        "status": status,
        "metadata": metadata,
        "updated_at": now,
    }
    await _mirror_program(updated)
    return updated


async def _update_host_state(
    host_id: str,
    *,
    status: str,
    active_slice_id: str = "",
    last_reason: str = "",
    cooldown_minutes: int = 0,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    cooldown_until = (now + timedelta(minutes=cooldown_minutes)).isoformat() if cooldown_minutes > 0 else ""
    current_host = next((item for item in await list_bootstrap_host_states() if item["id"] == host_id), None)
    record = {
        "id": host_id,
        "status": status,
        "cooldown_until": cooldown_until,
        "last_heartbeat": now.isoformat(),
        "active_slice_id": active_slice_id,
        "last_reason": last_reason,
        "metadata": dict(metadata if metadata is not None else current_host.get("metadata", {}) if current_host else {}),
        "updated_at": now.isoformat(),
    }
    await _to_thread(
        _execute_sync,
        """
        INSERT INTO bootstrap_host_state (
            host_id, status, cooldown_until, last_heartbeat, active_slice_id, last_reason, metadata_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(host_id) DO UPDATE SET
            status = excluded.status,
            cooldown_until = excluded.cooldown_until,
            last_heartbeat = excluded.last_heartbeat,
            active_slice_id = excluded.active_slice_id,
            last_reason = excluded.last_reason,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            record["id"],
            record["status"],
            record["cooldown_until"] or None,
            record["last_heartbeat"],
            record["active_slice_id"],
            record["last_reason"],
            json.dumps(record["metadata"]),
            record["updated_at"],
        ),
    )
    await _mirror_host_state(record)
    return record


async def update_bootstrap_host_status(
    host_id: str,
    *,
    status: str,
    active_slice_id: str = "",
    last_reason: str = "",
    cooldown_minutes: int = 0,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    if not get_bootstrap_host(host_id):
        raise ValueError(f"Unknown bootstrap host '{host_id}'")
    record = await _update_host_state(
        host_id,
        status=status,
        active_slice_id=active_slice_id,
        last_reason=last_reason,
        cooldown_minutes=cooldown_minutes,
        metadata=metadata,
    )
    await _write_snapshot_files()
    return record


async def record_bootstrap_blocker(
    *,
    program_id: str,
    slice_id: str,
    family: str,
    blocker_class: str,
    reason: str,
    approval_required: bool = False,
    retry_after_minutes: int = 30,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    now = _utc_now()
    retry_at = (now + timedelta(minutes=retry_after_minutes)).isoformat() if retry_after_minutes > 0 else ""
    inbox_id = ""
    if approval_required:
        try:
            from .operator_work import create_inbox_item

            inbox = await create_inbox_item(
                kind="approval_request",
                title=f"Bootstrap blocker for {family}",
                description=reason,
                severity=3,
                source="bootstrap",
                requires_decision=True,
                decision_type="bootstrap_blocker",
                metadata={
                    "program_id": program_id,
                    "slice_id": slice_id,
                    "family": family,
                    "blocker_class": blocker_class,
                },
            )
            inbox_id = str(inbox.get("id") or "")
        except Exception as exc:
            logger.warning("Failed to create bootstrap inbox item: %s", exc)

    record = {
        "id": f"blocker-{uuid.uuid4().hex[:10]}",
        "program_id": program_id,
        "slice_id": slice_id,
        "family": family,
        "blocker_class": blocker_class,
        "reason": reason,
        "approval_required": approval_required,
        "inbox_id": inbox_id,
        "retry_at": retry_at,
        "status": "open",
        "metadata": metadata or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "resolved_at": "",
    }
    await _to_thread(
        _execute_sync,
        """
        INSERT INTO bootstrap_blocker (
            blocker_id, program_id, slice_id, family, blocker_class, reason, approval_required, inbox_id, retry_at,
            status, metadata_json, created_at, updated_at, resolved_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["program_id"],
            record["slice_id"],
            record["family"],
            record["blocker_class"],
            record["reason"],
            int(record["approval_required"]),
            record["inbox_id"],
            record["retry_at"] or None,
            record["status"],
            json.dumps(record["metadata"]),
            record["created_at"],
            record["updated_at"],
            None,
        ),
    )
    await _mirror_blocker(record)
    await _write_snapshot_files()
    return record


async def resolve_bootstrap_blocker(blocker_id: str, *, note: str = "") -> dict[str, Any] | None:
    await ensure_bootstrap_state()
    blocker = next(
        (
            item
            for item in await list_bootstrap_blockers(limit=500)
            if str(item.get("id") or "") == blocker_id
        ),
        None,
    )
    if blocker is None:
        return None
    metadata = dict(blocker.get("metadata") or {})
    if note:
        metadata["resolution_note"] = note
    now = _utc_now().isoformat()
    resolved = {
        **blocker,
        "status": "resolved",
        "metadata": metadata,
        "updated_at": now,
        "resolved_at": now,
    }
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_blocker
        SET status = ?, metadata_json = ?, updated_at = ?, resolved_at = ?
        WHERE blocker_id = ?
        """,
        (
            resolved["status"],
            json.dumps(resolved["metadata"]),
            resolved["updated_at"],
            resolved["resolved_at"],
            blocker_id,
        ),
    )
    await _mirror_blocker(resolved)
    await _write_snapshot_files()
    return resolved


async def update_bootstrap_blocker(
    blocker_id: str,
    *,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
    retry_after_minutes: int | None = None,
) -> dict[str, Any] | None:
    await ensure_bootstrap_state()
    blocker = next(
        (
            item
            for item in await list_bootstrap_blockers(limit=500)
            if str(item.get("id") or "") == blocker_id
        ),
        None,
    )
    if blocker is None:
        return None
    now = _utc_now()
    merged_metadata = {**dict(blocker.get("metadata") or {}), **dict(metadata or {})}
    retry_at = blocker.get("retry_at") or ""
    if retry_after_minutes is not None:
        retry_at = (
            (now + timedelta(minutes=retry_after_minutes)).isoformat()
            if retry_after_minutes > 0
            else ""
        )
    updated = {
        **blocker,
        "reason": reason or str(blocker.get("reason") or ""),
        "metadata": merged_metadata,
        "retry_at": retry_at,
        "updated_at": now.isoformat(),
    }
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_blocker
        SET reason = ?, metadata_json = ?, retry_at = ?, updated_at = ?
        WHERE blocker_id = ?
        """,
        (
            updated["reason"],
            json.dumps(updated["metadata"]),
            updated["retry_at"] or None,
            updated["updated_at"],
            blocker_id,
        ),
    )
    await _mirror_blocker(updated)
    await _write_snapshot_files()
    return updated


async def approve_bootstrap_packet(
    program_id: str,
    *,
    packet_id: str,
    approved_by: str = "operator",
    reason: str = "",
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    program = await get_bootstrap_program_detail(program_id)
    if program is None:
        raise ValueError(f"Unknown bootstrap program '{program_id}'")

    slices = await list_bootstrap_slices(program_id=program_id, limit=500)
    blockers = await list_bootstrap_blockers(limit=500)
    normalized_packet_id = str(packet_id or "").strip()
    if not normalized_packet_id:
        waiting_slice_id = str(program.get("waiting_on_approval_slice_id") or "").strip()
        waiting_slice = next((item for item in slices if str(item.get("id") or "") == waiting_slice_id), None)
        normalized_packet_id = _required_packet_id_for_slice(waiting_slice or {})
    if not normalized_packet_id:
        raise ValueError(f"No approval packet is currently waiting for bootstrap program '{program_id}'")

    family_filter = str(program.get("waiting_on_approval_family") or "").strip()
    candidate_slices = [
        item
        for item in slices
        if str(item.get("status") or "") not in _TERMINAL_SLICE_STATUSES
        and _slice_requires_explicit_approval(item)
        and _required_packet_id_for_slice(item) == normalized_packet_id
        and normalized_packet_id not in _approved_packet_ids_for_slice(item)
        and (not family_filter or str(item.get("family") or "") == family_filter)
    ]
    if not candidate_slices:
        already_approved_slices = [
            item
            for item in slices
            if normalized_packet_id in _approved_packet_ids_for_slice(item)
        ]
        if already_approved_slices:
            refreshed_program = await get_bootstrap_program_detail(program_id)
            runtime_snapshot = await build_bootstrap_runtime_snapshot(include_snapshot_write=False)
            takeover = dict(runtime_snapshot.get("takeover") or {})
            approved_slice_ids = [str(item.get("id") or "") for item in already_approved_slices if str(item.get("id") or "")]
            return {
                "program": refreshed_program,
                "snapshot": runtime_snapshot,
                "takeover": takeover,
                "approved_packet_id": normalized_packet_id,
                "approved_slice_ids": approved_slice_ids,
                "resolved_blocker_ids": [],
                "recommendation": (refreshed_program or {}).get("next_action"),
                "active_family": (refreshed_program or {}).get("current_family") or runtime_snapshot.get("active_family"),
                "next_action": (refreshed_program or {}).get("next_action"),
                "already_approved": True,
            }
        raise ValueError(
            f"No approval-gated bootstrap slices match packet '{normalized_packet_id}' for program '{program_id}'"
        )

    now = _utc_now_iso()
    approved_slice_ids: list[str] = []
    for slice_record in candidate_slices:
        metadata = dict(slice_record.get("metadata") or {})
        approved_packets = _approved_packet_ids_for_slice(slice_record)
        approved_packets.add(normalized_packet_id)
        metadata.update(
            {
                "approved_packets": sorted(approved_packets),
                "approval_granted_at": now,
                "approval_granted_by": approved_by or "operator",
                "approval_reason": reason or f"Approved {normalized_packet_id}",
                "last_approved_packet_id": normalized_packet_id,
            }
        )
        updated = {
            **slice_record,
            "metadata": metadata,
            "updated_at": now,
        }
        await _to_thread(
            _execute_sync,
            """
            UPDATE bootstrap_slice
            SET metadata_json = ?, updated_at = ?
            WHERE slice_id = ?
            """,
            (
                json.dumps(updated["metadata"]),
                updated["updated_at"],
                str(slice_record.get("id") or ""),
            ),
        )
        await _mirror_slice(updated)
        approved_slice_ids.append(str(slice_record.get("id") or ""))

    resolved_blocker_ids: list[str] = []
    resolution_note = reason or f"Approved {normalized_packet_id} for bootstrap execution."
    for blocker in blockers:
        if (
            str(blocker.get("status") or "") == "open"
            and bool(blocker.get("approval_required"))
            and str(blocker.get("slice_id") or "") in approved_slice_ids
        ):
            resolved = await resolve_bootstrap_blocker(str(blocker.get("id") or ""), note=resolution_note)
            if resolved is not None:
                resolved_blocker_ids.append(str(resolved.get("id") or ""))

    cycle = await run_bootstrap_supervisor_cycle(
        program_id=program_id,
        execute=False,
        retry_blockers=True,
        process_integrations=True,
    )
    refreshed_program = await get_bootstrap_program_detail(program_id)
    runtime_snapshot = await build_bootstrap_runtime_snapshot(include_snapshot_write=False)
    takeover = dict(runtime_snapshot.get("takeover") or {})
    return {
        "program": refreshed_program,
        "snapshot": runtime_snapshot,
        "takeover": takeover,
        "approved_packet_id": normalized_packet_id,
        "approved_slice_ids": approved_slice_ids,
        "resolved_blocker_ids": resolved_blocker_ids,
        "recommendation": cycle.get("recommendation"),
        "active_family": cycle.get("active_family"),
        "next_action": (refreshed_program or {}).get("next_action"),
    }


async def claim_bootstrap_slice(
    slice_id: str,
    *,
    host_id: str,
    current_ref: str = "",
    worktree_path: str = "",
    files_touched: list[str] | None = None,
    next_step: str = "",
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    if not get_bootstrap_host(host_id):
        raise ValueError(f"Unknown bootstrap host '{host_id}'")

    record = await get_bootstrap_slice(slice_id)
    if not record:
        raise ValueError(f"Unknown bootstrap slice '{slice_id}'")
    if record["status"] not in {"queued", "ready", "handed_off"}:
        raise ValueError(f"Bootstrap slice '{slice_id}' is not claimable from status '{record['status']}'")

    now = _utc_now_iso()
    updated = {
        **record,
        "status": "claimed",
        "host_id": host_id,
        "current_ref": current_ref or record.get("current_ref", ""),
        "worktree_path": worktree_path or record.get("worktree_path", ""),
        "files_touched": files_touched or list(record.get("files_touched") or []),
        "next_step": next_step or record.get("next_step", ""),
        "claimed_at": now,
        "updated_at": now,
    }
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_slice
        SET status = ?, host_id = ?, current_ref = ?, worktree_path = ?, files_touched_json = ?, next_step = ?,
            claimed_at = ?, updated_at = ?
        WHERE slice_id = ?
        """,
        (
            updated["status"],
            updated["host_id"],
            updated["current_ref"],
            updated["worktree_path"],
            json.dumps(updated["files_touched"]),
            updated["next_step"],
            updated["claimed_at"],
            updated["updated_at"],
            slice_id,
        ),
    )
    await _mirror_slice(updated)
    await _update_host_state(host_id, status="busy", active_slice_id=slice_id, last_reason="claimed slice")
    await _write_snapshot_files()
    return updated


async def handoff_bootstrap_slice(
    slice_id: str,
    *,
    from_host: str,
    to_host: str,
    current_ref: str = "",
    worktree_path: str = "",
    files_touched: list[str] | None = None,
    validation_status: str = "pending",
    open_risks: list[str] | None = None,
    next_step: str = "",
    stop_reason: str = "",
    resume_instructions: str = "",
    cooldown_minutes: int = 30,
    blocker_class: str = "",
    approval_required: bool = False,
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    if not get_bootstrap_host(from_host):
        raise ValueError(f"Unknown bootstrap host '{from_host}'")
    if not get_bootstrap_host(to_host):
        raise ValueError(f"Unknown bootstrap host '{to_host}'")

    record = await get_bootstrap_slice(slice_id)
    if not record:
        raise ValueError(f"Unknown bootstrap slice '{slice_id}'")

    now = _utc_now_iso()
    updated = {
        **record,
        "status": "ready",
        "host_id": to_host,
        "current_ref": current_ref or record.get("current_ref", ""),
        "worktree_path": worktree_path or record.get("worktree_path", ""),
        "files_touched": files_touched or list(record.get("files_touched") or []),
        "validation_status": validation_status or record.get("validation_status", "pending"),
        "open_risks": open_risks or list(record.get("open_risks") or []),
        "next_step": next_step or record.get("next_step", ""),
        "stop_reason": stop_reason or record.get("stop_reason", ""),
        "resume_instructions": resume_instructions or record.get("resume_instructions", ""),
        "updated_at": now,
    }
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_slice
        SET status = ?, host_id = ?, current_ref = ?, worktree_path = ?, files_touched_json = ?, validation_status = ?,
            open_risks_json = ?, next_step = ?, stop_reason = ?, resume_instructions = ?, updated_at = ?
        WHERE slice_id = ?
        """,
        (
            updated["status"],
            updated["host_id"],
            updated["current_ref"],
            updated["worktree_path"],
            json.dumps(updated["files_touched"]),
            updated["validation_status"],
            json.dumps(updated["open_risks"]),
            updated["next_step"],
            updated["stop_reason"],
            updated["resume_instructions"],
            updated["updated_at"],
            slice_id,
        ),
    )
    await _mirror_slice(updated)

    handoff = {
        "id": f"handoff-{uuid.uuid4().hex[:10]}",
        "program_id": updated["program_id"],
        "slice_id": updated["id"],
        "family": updated["family"],
        "from_host": from_host,
        "to_host": to_host,
        "objective": updated["objective"],
        "current_ref": updated["current_ref"],
        "worktree_path": updated["worktree_path"],
        "files_touched": updated["files_touched"],
        "validation_status": updated["validation_status"],
        "open_risks": updated["open_risks"],
        "next_step": updated["next_step"],
        "stop_reason": updated["stop_reason"],
        "resume_instructions": updated["resume_instructions"],
        "status": "recorded",
        "created_at": now,
        "updated_at": now,
        "completed_at": "",
    }
    await _to_thread(
        _execute_sync,
        """
        INSERT INTO bootstrap_handoff (
            handoff_id, program_id, slice_id, family, from_host, to_host, objective, current_ref, worktree_path,
            files_touched_json, validation_status, open_risks_json, next_step, stop_reason, resume_instructions,
            status, created_at, updated_at, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            handoff["id"],
            handoff["program_id"],
            handoff["slice_id"],
            handoff["family"],
            handoff["from_host"],
            handoff["to_host"],
            handoff["objective"],
            handoff["current_ref"],
            handoff["worktree_path"],
            json.dumps(handoff["files_touched"]),
            handoff["validation_status"],
            json.dumps(handoff["open_risks"]),
            handoff["next_step"],
            handoff["stop_reason"],
            handoff["resume_instructions"],
            handoff["status"],
            handoff["created_at"],
            handoff["updated_at"],
            None,
        ),
    )
    await _mirror_handoff(handoff)
    from_host_state = next((item for item in await list_bootstrap_host_states() if item["id"] == from_host), None)
    to_host_state = next((item for item in await list_bootstrap_host_states() if item["id"] == to_host), None)
    await _update_host_state(
        from_host,
        status=_status_for_handoff_reason(stop_reason),
        last_reason=stop_reason or "handoff",
        cooldown_minutes=cooldown_minutes,
        metadata=dict(from_host_state.get("metadata") or {}) if from_host_state else None,
    )
    await _update_host_state(
        to_host,
        status="available",
        last_reason="handoff received",
        metadata=dict(to_host_state.get("metadata") or {}) if to_host_state else None,
    )

    if blocker_class:
        await record_bootstrap_blocker(
            program_id=updated["program_id"],
            slice_id=updated["id"],
            family=updated["family"],
            blocker_class=blocker_class,
            reason=stop_reason or blocker_class,
            approval_required=approval_required,
            metadata={"handoff_id": handoff["id"], "from_host": from_host, "to_host": to_host},
        )
    else:
        await _write_snapshot_files()
    return {"slice": updated, "handoff": handoff}


async def _queue_integration_record(record: dict[str, Any]) -> None:
    queue_path = _integration_queue_file(str(record.get("slice_id") or ""))
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(record, indent=2), encoding="utf-8")


async def complete_bootstrap_slice(
    slice_id: str,
    *,
    host_id: str = "",
    current_ref: str = "",
    worktree_path: str = "",
    files_touched: list[str] | None = None,
    validation_status: str = "passed",
    open_risks: list[str] | None = None,
    next_step: str = "",
    summary: str = "",
    integration_method: str = "squash_commit",
    target_ref: str = "main",
    queue_priority: int = 3,
    queue_integration: bool | None = None,
    completion_disposition: str = "",
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    record = await get_bootstrap_slice(slice_id)
    if not record:
        raise ValueError(f"Unknown bootstrap slice '{slice_id}'")

    now = _utc_now_iso()
    updated = {
        **record,
        "status": "completed",
        "host_id": host_id or record.get("host_id", ""),
        "current_ref": current_ref or record.get("current_ref", ""),
        "worktree_path": worktree_path or record.get("worktree_path", ""),
        "files_touched": files_touched or list(record.get("files_touched") or []),
        "validation_status": validation_status or record.get("validation_status", "pending"),
        "open_risks": open_risks or list(record.get("open_risks") or []),
        "next_step": next_step or record.get("next_step", ""),
        "completed_at": now,
        "updated_at": now,
        "metadata": {
            **dict(record.get("metadata") or {}),
            "summary": summary,
            **({"completion_disposition": completion_disposition} if completion_disposition else {}),
        },
    }
    await _to_thread(
        _execute_sync,
        """
        UPDATE bootstrap_slice
        SET status = ?, host_id = ?, current_ref = ?, worktree_path = ?, files_touched_json = ?, validation_status = ?,
            open_risks_json = ?, next_step = ?, metadata_json = ?, completed_at = ?, updated_at = ?
        WHERE slice_id = ?
        """,
        (
            updated["status"],
            updated["host_id"],
            updated["current_ref"],
            updated["worktree_path"],
            json.dumps(updated["files_touched"]),
            updated["validation_status"],
            json.dumps(updated["open_risks"]),
            updated["next_step"],
            json.dumps(updated["metadata"]),
            updated["completed_at"],
            updated["updated_at"],
            slice_id,
        ),
    )
    await _mirror_slice(updated)
    if updated["host_id"]:
        await _update_host_state(updated["host_id"], status="available", last_reason="slice completed")

    if queue_integration is None:
        queue_integration = _slice_host_mode(updated) == "code_mutation"

    integration: dict[str, Any] | None = None
    if updated["validation_status"] in _PASSING_VALIDATION and queue_integration:
        integration = {
            "id": f"integration-{uuid.uuid4().hex[:10]}",
            "program_id": updated["program_id"],
            "slice_id": updated["id"],
            "family": updated["family"],
            "method": integration_method,
            "source_ref": updated["current_ref"],
            "target_ref": target_ref,
            "patch_path": "",
            "queue_path": str(_integration_queue_file(updated["id"])),
            "status": "queued",
            "priority": int(queue_priority),
            "validation_summary": {
                "status": updated["validation_status"],
                "summary": summary,
                "open_risks": updated["open_risks"],
            },
            "blocker_id": "",
            "metadata": {"files_touched": updated["files_touched"], "worktree_path": updated["worktree_path"]},
            "created_at": now,
            "updated_at": now,
            "completed_at": "",
        }
        await _to_thread(
            _execute_sync,
            """
            INSERT INTO bootstrap_integration (
                integration_id, program_id, slice_id, family, method, source_ref, target_ref, patch_path, queue_path,
                status, priority, validation_summary_json, blocker_id, metadata_json, created_at, updated_at, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                integration["id"],
                integration["program_id"],
                integration["slice_id"],
                integration["family"],
                integration["method"],
                integration["source_ref"],
                integration["target_ref"],
                integration["patch_path"],
                integration["queue_path"],
                integration["status"],
                integration["priority"],
                json.dumps(integration["validation_summary"]),
                integration["blocker_id"],
                json.dumps(integration["metadata"]),
                integration["created_at"],
                integration["updated_at"],
                None,
            ),
        )
        await _queue_integration_record(integration)
        await _mirror_integration(integration)
    elif updated["validation_status"] not in _PASSING_VALIDATION:
        await record_bootstrap_blocker(
            program_id=updated["program_id"],
            slice_id=updated["id"],
            family=updated["family"],
            blocker_class="implementation_failure",
            reason=summary or f"Validation failed for {updated['id']}",
            metadata={"validation_status": updated["validation_status"]},
        )
        return {"slice": updated, "integration": None}

    await _write_snapshot_files()
    return {"slice": updated, "integration": integration}


async def replay_bootstrap_integration(
    slice_id: str,
    *,
    method: str = "squash_commit",
    source_ref: str = "",
    target_ref: str = "main",
    patch_path: str = "",
    priority: int = 3,
) -> dict[str, Any]:
    await ensure_bootstrap_state()
    record = await get_bootstrap_slice(slice_id)
    if not record:
        raise ValueError(f"Unknown bootstrap slice '{slice_id}'")

    now = _utc_now_iso()
    integration = {
        "id": f"integration-{uuid.uuid4().hex[:10]}",
        "program_id": record["program_id"],
        "slice_id": slice_id,
        "family": record["family"],
        "method": method,
        "source_ref": source_ref or record.get("current_ref", ""),
        "target_ref": target_ref,
        "patch_path": patch_path,
        "queue_path": str(_integration_queue_file(slice_id)),
        "status": "queued",
        "priority": int(priority),
        "validation_summary": {"status": record.get("validation_status", "pending")},
        "blocker_id": "",
        "metadata": {"replayed_at": now},
        "created_at": now,
        "updated_at": now,
        "completed_at": "",
    }
    await _to_thread(
        _execute_sync,
        """
        INSERT INTO bootstrap_integration (
            integration_id, program_id, slice_id, family, method, source_ref, target_ref, patch_path, queue_path,
            status, priority, validation_summary_json, blocker_id, metadata_json, created_at, updated_at, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            integration["id"],
            integration["program_id"],
            integration["slice_id"],
            integration["family"],
            integration["method"],
            integration["source_ref"],
            integration["target_ref"],
            integration["patch_path"],
            integration["queue_path"],
            integration["status"],
            integration["priority"],
            json.dumps(integration["validation_summary"]),
            integration["blocker_id"],
            json.dumps(integration["metadata"]),
            integration["created_at"],
            integration["updated_at"],
            None,
        ),
    )
    await _queue_integration_record(integration)
    await _mirror_integration(integration)
    await _write_snapshot_files()
    return integration


async def build_takeover_status() -> dict[str, Any]:
    from .governance_state import build_governance_snapshot
    from .operator_work import backlog_stats, idea_stats, inbox_stats, run_stats, todo_stats

    activation, current_phase = get_current_autonomy_phase()
    persistence = _effective_checkpointer_status()
    durable_state = get_durable_state_status()
    durable_packet = _build_durable_persistence_packet(generated_at=_utc_now_iso(), takeover_ready=False)
    durable_criterion = dict(durable_packet.get("criterion_status") or {})
    restart_proof = dict(durable_packet.get("restart_proof") or {})
    programs = await list_bootstrap_programs()
    compatibility_census = _collect_compatibility_retirement_census()
    foundry_proving = await _build_foundry_proving_status()
    governance_drill_status = _build_governance_drill_status()
    idea_summary, inbox_summary, todo_summary, backlog_summary, run_summary, governance = await asyncio.gather(
        idea_stats(),
        inbox_stats(),
        todo_stats(),
        backlog_stats(),
        run_stats(),
        build_governance_snapshot(),
    )
    promoted_program = next(
        (
            item
            for item in programs
            if bool((item.get("metadata") or {}).get("internal_builder_primary"))
        ),
        None,
    )
    operator_runbooks = _read_registry_json(_repo_root() / "config" / "automation-backbone" / "operator-runbooks.json")
    runbook_status = str(operator_runbooks.get("status") or "unknown")
    launch_blockers = [str(item) for item in governance.get("launch_blockers") or []]
    canonical_operator_work_system_ready = all(
        isinstance(summary, dict) and "total" in summary
        for summary in (idea_summary, inbox_summary, todo_summary, backlog_summary, run_summary)
    )
    canonical_operator_work_system_detail = (
        "Canonical operator surfaces are live: "
        f"ideas={idea_summary.get('total', 0)}, "
        f"inbox={inbox_summary.get('total', 0)}, "
        f"todos={todo_summary.get('total', 0)}, "
        f"backlog={backlog_summary.get('total', 0)}, "
        f"runs={run_summary.get('total', 0)}."
    )
    failed_drills = [str(item) for item in governance_drill_status.get("failed_drill_ids") or []]
    governance_drills_green = bool(governance_drill_status.get("all_green"))
    governance_detail = (
        "All required governance drill artifacts are present and green."
        if governance_drills_green
        else (
            f"Governance drill evidence is still failing: failed_drills={failed_drills or ['unknown']}; "
            f"evidence_complete={bool(governance_drill_status.get('evidence_complete'))}; "
            f"runbook_registry_status={runbook_status}."
        )
    )
    durable_persistence_detail = (
        "Configured runtimes are using durable persistence, the durable-state schema is ready, and restart proof is recorded."
        if bool(durable_criterion.get("passed"))
        else (
            f"Durable persistence is not live: configured={bool(persistence.get('configured'))}, "
            f"durable={bool(persistence.get('durable'))}, "
            f"schema_ready={bool(durable_state.get('schema_ready'))}, "
            f"restart_proof_status={str(restart_proof.get('status') or 'unknown')}, "
            f"reason={str(durable_state.get('reason') or persistence.get('reason') or 'unknown')}."
        )
    )

    evaluations = {
        "software_core_active": (
            str(activation.get("activation_state") or "") in {
                "software_core_active",
                "expanded_core_active",
                "full_system_active",
            }
            and str(current_phase.get("status") or "") == "active",
            (
                "Current autonomy phase is "
                f"{str(activation.get('current_phase_id') or 'unknown')} and active, which keeps software-core autonomy live."
            ),
        ),
        "canonical_operator_work_system": (
            canonical_operator_work_system_ready,
            canonical_operator_work_system_detail,
        ),
        "compatibility_retirement_complete": (
            bool(compatibility_census.get("complete")),
            (
                "Compatibility census shows no first-class workforce-era dependencies."
                if compatibility_census.get("complete")
                else f"Compatibility census still has {compatibility_census.get('first_class_hit_count', 0)} first-class hits."
            ),
        ),
        "durable_persistence_live": (
            bool(durable_criterion.get("passed")),
            durable_persistence_detail,
        ),
        "foundry_path_live": (
            bool(foundry_proving.get("ready")),
            (
                "Foundry proving packet has project, architecture, slice, run, candidate, and rollback evidence."
                if foundry_proving.get("ready")
                else (
                    "Foundry proving packet is incomplete: "
                    f"slices={foundry_proving.get('slice_count', 0)}, "
                    f"runs={foundry_proving.get('run_count', 0)}, "
                    f"candidates={foundry_proving.get('candidate_count', 0)}, "
                    f"rollback_recorded={bool(foundry_proving.get('promotion_or_rollback_recorded'))}."
                )
            ),
        ),
        "governance_drills_green": (
            governance_drills_green,
            governance_detail,
        ),
        "external_dependency_removed": (
            promoted_program is not None,
            "Internal builder has been explicitly promoted as primary." if promoted_program else "External builders are still primary in the current bootstrap posture.",
        ),
    }

    criteria = []
    for criterion in get_bootstrap_takeover_criteria():
        criterion_id = str(criterion.get("id") or "")
        passed, detail = evaluations.get(criterion_id, (False, "No evaluator is registered for this criterion yet."))
        criteria.append({**criterion, "passed": bool(passed), "detail": detail})

    blockers = [item["id"] for item in criteria if not bool(item.get("passed"))]
    registry = get_bootstrap_takeover_registry()
    return {
        "promotion_rule": str(registry.get("promotion_rule") or "explicit_promotion_only"),
        "before_takeover_authority": str(registry.get("before_takeover_authority") or "hybrid_local_ledger"),
        "after_takeover_authority": str(registry.get("after_takeover_authority") or "athanor_postgres"),
        "external_posture": dict(registry.get("external_posture") or {}),
        "promoted": promoted_program is not None,
        "promoted_program_id": str(promoted_program.get("id") or "") if promoted_program else "",
        "promoted_at": str((promoted_program.get("metadata") or {}).get("promoted_at") or "") if promoted_program else "",
        "compatibility_census": compatibility_census,
        "foundry_proving": foundry_proving,
        "governance_drills": governance_drill_status,
        "criteria": criteria,
        "ready": not blockers,
        "blocker_ids": blockers,
    }


async def _build_bootstrap_runtime_snapshot_uncached(*, include_snapshot_write: bool = True) -> dict[str, Any]:
    await ensure_bootstrap_state()
    programs = await list_bootstrap_programs()
    slices = await list_bootstrap_slices(limit=500)
    blockers = await list_bootstrap_blockers(limit=500)
    hosts = await _refresh_host_cooldowns()
    integrations = await list_bootstrap_integrations(limit=500)
    takeover = await build_takeover_status()
    registry_snapshot = build_bootstrap_registry_snapshot()
    active_program = next(
        (
            item
            for item in programs
            if str(item.get("status") or "") not in {"completed", "ready_for_takeover_check"}
        ),
        programs[0] if programs else None,
    )
    approval_context = _build_approval_context(active_program, slices=slices, blockers=blockers)
    snapshot = {
        **get_bootstrap_status(),
        "program_count": len(programs),
        "slice_count": len(slices),
        "open_blockers": sum(1 for item in blockers if str(item.get("status") or "") == "open"),
        "busy_hosts": sum(1 for item in hosts if str(item.get("status") or "") == "busy"),
        "pending_integrations": sum(1 for item in integrations if str(item.get("status") or "") == "queued"),
        "active_program_id": str(active_program.get("id") or "") if active_program else "",
        "active_family": str(active_program.get("current_family") or "") if active_program else "",
        "next_slice_id": str(active_program.get("next_slice_id") or "") if active_program else "",
        "recommended_host_id": str(active_program.get("recommended_host_id") or "") if active_program else "",
        "waiting_on_approval_family": str(active_program.get("waiting_on_approval_family") or "") if active_program else "",
        "waiting_on_approval_slice_id": str(active_program.get("waiting_on_approval_slice_id") or "") if active_program else "",
        "next_action": dict(active_program.get("next_action") or {}) if active_program else {},
        "approval_context": approval_context,
        "hosts": hosts,
        "registry_snapshot": registry_snapshot,
        "control_artifacts": {
            "snapshot_path": str(bootstrap_snapshot_path()),
            "compatibility_census_path": str(bootstrap_compatibility_census_path()),
            "operator_surface_census_path": str(bootstrap_operator_surface_census_path()),
            "operator_summary_alignment_path": str(bootstrap_operator_summary_alignment_path()),
            "operator_fixture_parity_path": str(bootstrap_operator_fixture_parity_path()),
            "operator_nav_lock_path": str(bootstrap_operator_nav_lock_path()),
            "durable_persistence_packet_path": str(bootstrap_durable_persistence_packet_path()),
            "durable_restart_proof_path": str(bootstrap_durable_restart_proof_path()),
            "approval_packet_registry_path": str(bootstrap_approval_packet_registry_path()),
            "durable_state_sql_path": str(bootstrap_durable_state_sql_path()),
            "foundry_proving_packet_path": str(bootstrap_foundry_proving_packet_path()),
            "governance_drill_packets_path": str(bootstrap_governance_drill_packets_path()),
            "takeover_promotion_packet_path": str(bootstrap_takeover_promotion_packet_path()),
        },
        "takeover": takeover,
    }
    if include_snapshot_write:
        await _write_snapshot_files()
    return snapshot


async def build_bootstrap_runtime_snapshot(
    *,
    include_snapshot_write: bool = True,
    allow_stale: bool = False,
) -> dict[str, Any]:
    global _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK

    if include_snapshot_write:
        snapshot = await _build_bootstrap_runtime_snapshot_uncached(include_snapshot_write=True)
        _prime_bootstrap_runtime_snapshot_cache(snapshot)
        return snapshot

    now = monotonic()
    cached = _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE
    if cached is not None and now < _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT:
        return dict(cached)

    task: asyncio.Task[dict[str, Any]] | None = None
    async with _BOOTSTRAP_RUNTIME_SNAPSHOT_LOCK:
        now = monotonic()
        cached = _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE
        if cached is not None and now < _BOOTSTRAP_RUNTIME_SNAPSHOT_CACHE_EXPIRES_AT:
            return dict(cached)

        if _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK is None or _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK.done():
            _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK = asyncio.create_task(
                _refresh_bootstrap_runtime_snapshot_task(include_snapshot_write=False)
            )
        task = _BOOTSTRAP_RUNTIME_SNAPSHOT_TASK
        if allow_stale and cached is not None:
            return dict(cached)

    snapshot = await asyncio.shield(task)
    return dict(snapshot)
