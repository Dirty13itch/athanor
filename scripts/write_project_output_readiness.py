#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = REPO_ROOT / "config" / "automation-backbone"
CONTRACT_REGISTRY_PATH = CONFIG_ROOT / "project-output-contract-registry.json"
PROJECT_PACKET_REGISTRY_PATH = CONFIG_ROOT / "project-packet-registry.json"
PROJECT_MATURITY_REGISTRY_PATH = CONFIG_ROOT / "project-maturity-registry.json"
SAFE_SURFACE_SCOPE_PATH = Path("/mnt/c/Users/Shaun/.codex/control/safe-surface-scope.md")
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
STABLE_OPERATING_DAY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "stable-operating-day.json"
CONTINUITY_SUPERVISOR_HEALTH_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-supervisor-health.json"
PROJECT_OUTPUT_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-proof.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-readiness.json"
STATUS_MD_PATH = REPO_ROOT / "docs" / "operations" / "PROJECT-OUTPUT-READINESS.md"
GIT_TIMEOUT_SECONDS = 8


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _render_against_existing(payload: dict[str, Any], current_json: str) -> tuple[str, str]:
    comparable_payload = dict(payload)
    try:
        existing_payload = json.loads(current_json) if current_json.strip() else {}
    except json.JSONDecodeError:
        existing_payload = {}
    existing_generated_at = _text(existing_payload.get("generated_at")) if isinstance(existing_payload, dict) else ""
    if existing_generated_at:
        comparable_payload["generated_at"] = existing_generated_at
    return _json_render(comparable_payload), _markdown(comparable_payload)


def _normalize_windows_path(value: str) -> str:
    return value.replace("/", "\\").rstrip("\\").lower()


def _local_path_from_canonical(root: str) -> Path | None:
    normalized = _text(root)
    if not normalized or normalized == "needs_root":
        return None
    if normalized.startswith("/mnt/"):
        return Path(normalized)
    match = re.match(r"^([A-Za-z]):[\\/](.*)$", normalized)
    if not match:
        return Path(normalized)
    drive = match.group(1).lower()
    tail = match.group(2).replace("\\", "/")
    return Path(f"/mnt/{drive}/{tail}")


def _load_safe_surface_scope() -> dict[str, Any]:
    if not SAFE_SURFACE_SCOPE_PATH.exists():
        return {}
    text = SAFE_SURFACE_SCOPE_PATH.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _git_probe(local_root: Path) -> dict[str, Any]:
    if not local_root.exists():
        return {"git_head": "", "dirty_count": 0, "status_sample": [], "git_probe_incomplete": True}
    try:
        head = subprocess.run(
            ["git", "-C", str(local_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        status = subprocess.run(
            ["git", "-C", str(local_root), "status", "--short", "--", "."],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"git_head": "", "dirty_count": 0, "status_sample": [], "git_probe_incomplete": True}
    status_lines = [line.rstrip() for line in status.stdout.splitlines() if line.strip()] if status.returncode == 0 else []
    return {
        "git_head": head.stdout.strip() if head.returncode == 0 else "",
        "dirty_count": len(status_lines),
        "status_sample": status_lines[:10],
        "git_probe_incomplete": head.returncode != 0 or status.returncode != 0,
    }


def _default_project_probe(project: dict[str, Any]) -> dict[str, Any]:
    canonical_root = _text(project.get("canonical_root"))
    local_root = _local_path_from_canonical(canonical_root)
    app_root = local_root
    app_root_relative_path = _text(project.get("app_root_relative_path"))
    if local_root is not None and app_root_relative_path:
        app_root = local_root / Path(app_root_relative_path)

    root_exists = bool(local_root and local_root.exists())
    app_root_exists = bool(app_root and app_root.exists())
    package_json_present = bool(app_root and (app_root / "package.json").exists())
    node_modules_present = bool(app_root and (app_root / "node_modules").exists())
    mobile_shell_present = any(
        candidate.exists()
        for candidate in [
            *((
                app_root / "apps" / "mobile" / "package.json",
                app_root / "mobile" / "package.json",
                app_root / "app.json",
                app_root / "app.config.js",
                app_root / "app.config.ts",
                app_root / "android",
            ) if app_root else ()),
            *((
                local_root / "apps" / "mobile" / "package.json",
                local_root / "mobile" / "package.json",
                local_root / "android",
            ) if local_root else ()),
        ]
    )
    android_contract_present = mobile_shell_present
    git_probe = _git_probe(local_root) if local_root is not None else {
        "git_head": "",
        "dirty_count": 0,
        "status_sample": [],
        "git_probe_incomplete": False,
    }
    return {
        "root_exists": root_exists,
        "app_root_exists": app_root_exists,
        "app_root": str(app_root) if app_root else None,
        "package_json_present": package_json_present,
        "node_modules_present": node_modules_present,
        "mobile_shell_present": mobile_shell_present,
        "android_contract_present": android_contract_present,
        **git_probe,
    }


def _safe_surface_status(project: dict[str, Any], safe_surface_scope: dict[str, Any]) -> str:
    canonical_root = _text(project.get("canonical_root"))
    if canonical_root == "needs_root":
        return "needs_root"
    if _text(project.get("authority_class")) == "athanor_in_repo_project":
        return "athanor_in_repo"
    normalized = _normalize_windows_path(canonical_root)
    allowed_roots = {_normalize_windows_path(item) for item in _string_list(safe_surface_scope.get("allowed_roots"))}
    deny_patterns = [item.lower() for item in _string_list(safe_surface_scope.get("deny_patterns"))]
    if normalized in allowed_roots:
        return "allowlisted"
    if any(pattern and pattern in normalized for pattern in deny_patterns):
        return "denied_by_policy"
    return "not_allowlisted"


def _single_live_blocker(
    *,
    blocker_map: dict[str, Any],
    runtime_parity: dict[str, Any],
    stable_operating_day: dict[str, Any],
    supervisor_health: dict[str, Any],
) -> str | None:
    drift_class = _text(runtime_parity.get("drift_class"))
    if drift_class and drift_class not in {"clean", "generated_surface_drift"}:
        return "runtime_parity"
    if _text(supervisor_health.get("health_status")) != "healthy":
        return "continuity_health"
    if not bool(stable_operating_day.get("met")):
        return "stable_operating_day"
    blocking = _string_list((blocker_map.get("proof_gate") or {}).get("blocking_check_ids"))
    return blocking[0] if blocking else None


def _core_runtime_ready(
    *,
    blocker_map: dict[str, Any],
    runtime_parity: dict[str, Any],
    stable_operating_day: dict[str, Any],
    supervisor_health: dict[str, Any],
) -> bool:
    return (
        _text(runtime_parity.get("drift_class")) in {"clean", "generated_surface_drift"}
        and _text(supervisor_health.get("health_status")) == "healthy"
        and bool(stable_operating_day.get("met"))
        and bool((blocker_map.get("proof_gate") or {}).get("open"))
    )


def _readiness_tier(
    *,
    project: dict[str, Any],
    probe: dict[str, Any],
    safe_surface_status: str,
    core_ready: bool,
) -> str:
    canonical_root = _text(project.get("canonical_root"))
    observed = dict(project.get("observed_baseline") or {})
    observed_build_state = _text(observed.get("build_state"))
    authority_class = _text(project.get("authority_class"))
    autonomy_scope_state = _text(project.get("autonomy_scope_state"))

    if canonical_root == "needs_root":
        return "needs_root"
    if not bool(probe.get("root_exists")):
        return "missing_root"
    if safe_surface_status == "denied_by_policy":
        return "policy_blocked"
    if bool(probe.get("package_json_present")) and not bool(probe.get("node_modules_present")):
        return "toolchain_blocked"
    if authority_class != "athanor_in_repo_project" and (
        autonomy_scope_state in {"contract_defined_pending_admission", "explicit_admission_required"}
        or safe_surface_status == "not_allowlisted"
    ):
        return "admission_pending"
    if observed_build_state == "failed":
        return "preflight_blocked"
    if not core_ready:
        return "core_gate_hold"
    return "ready_for_first_output"


def _autonomy_eligibility(
    *,
    project: dict[str, Any],
    probe: dict[str, Any],
    safe_surface_status: str,
    core_ready: bool,
) -> str:
    canonical_root = _text(project.get("canonical_root"))
    authority_class = _text(project.get("authority_class"))
    autonomy_scope_state = _text(project.get("autonomy_scope_state"))

    if canonical_root == "needs_root":
        return "needs_root"
    if not bool(probe.get("root_exists")):
        return "missing_root"
    if safe_surface_status == "denied_by_policy":
        return "denied_by_safe_surface"
    if authority_class == "athanor_in_repo_project":
        return "eligible_now" if core_ready else "held_by_core_runtime_gate"
    if autonomy_scope_state in {"contract_defined_pending_admission", "explicit_admission_required"}:
        return "explicit_admission_required"
    if safe_surface_status == "allowlisted":
        return "eligible_now" if core_ready else "held_by_core_runtime_gate"
    return "explicit_admission_required"


def _record_blockers(
    *,
    project: dict[str, Any],
    probe: dict[str, Any],
    safe_surface_status: str,
    core_ready: bool,
    single_live_blocker: str | None,
) -> list[str]:
    blockers: list[str] = []
    canonical_root = _text(project.get("canonical_root"))
    authority_class = _text(project.get("authority_class"))
    autonomy_scope_state = _text(project.get("autonomy_scope_state"))

    if canonical_root == "needs_root":
        blockers.append("canonical_root_required")
        return blockers
    expectation = _text(project.get("safe_surface_expectation"))
    if expectation and expectation not in {"not_applicable", safe_surface_status}:
        blockers.append("safe_surface_expectation_mismatch")
    if not bool(probe.get("root_exists")):
        blockers.append("canonical_root_missing")
    if safe_surface_status == "denied_by_policy":
        blockers.append("safe_surface_denied")
    elif authority_class != "athanor_in_repo_project" and safe_surface_status != "allowlisted":
        blockers.append("safe_surface_not_allowlisted")
    if autonomy_scope_state in {"contract_defined_pending_admission", "explicit_admission_required"}:
        blockers.append("not_admitted_into_project_factory")
    if bool(probe.get("package_json_present")) and not bool(probe.get("node_modules_present")):
        blockers.append("toolchain_missing")
    if int(probe.get("dirty_count") or 0) > 0:
        blockers.append("dirty_authority_root")
    if _text(project.get("platform_class")) == "web_plus_mobile" and not bool(probe.get("android_contract_present")):
        blockers.append("mobile_contract_missing")
    if not core_ready and single_live_blocker:
        blockers.append(f"core_runtime_gate:{single_live_blocker}")
    return blockers


def _top_priority_record(
    records: list[dict[str, Any]],
    *,
    project_output_proof: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    if not records:
        return {}, "none"
    proof = dict(project_output_proof or {})
    stage_status = dict(proof.get("stage_status") or {})
    accepted_project_ids = {
        _text(item.get("project_id"))
        for item in list(proof.get("accepted_entries") or [])
        if isinstance(item, dict) and _text(item.get("project_id"))
    }
    remaining_distinct = int(stage_status.get("remaining_distinct_projects") or 0)
    remaining_external = int(stage_status.get("remaining_external_project_outputs") or 0)
    if remaining_distinct <= 0 and remaining_external <= 0:
        return records[0], "factory_priority"

    def _selection_key(item: dict[str, Any]) -> tuple[Any, ...]:
        project_id = _text(item.get("project_id"))
        authority_class = _text(item.get("authority_class"))
        autonomy = _text(item.get("autonomy_eligibility"))
        safe_surface_status = _text(item.get("safe_surface_status"))
        accepted = project_id in accepted_project_ids
        external = authority_class not in {"athanor_in_repo_project", "needs_root"}
        denied = autonomy in {"denied_by_safe_surface", "needs_root", "missing_root"}
        requires_admission = autonomy == "explicit_admission_required"
        allowlisted_or_in_repo = safe_surface_status == "allowlisted" or authority_class == "athanor_in_repo_project"
        return (
            0 if (remaining_external > 0 and external) else 1,
            0 if (remaining_distinct > 0 and not accepted) else 1,
            2 if denied else (1 if requires_admission else 0),
            0 if allowlisted_or_in_repo else 1,
            int(item.get("factory_priority") or 999),
            _text(item.get("label")) or project_id,
        )

    return min(records, key=_selection_key), "proof_gap_priority"


def build_payload(
    *,
    contract_registry: dict[str, Any],
    project_packet_registry: dict[str, Any],
    project_maturity_registry: dict[str, Any],
    safe_surface_scope: dict[str, Any],
    blocker_map: dict[str, Any],
    runtime_parity: dict[str, Any],
    stable_operating_day: dict[str, Any],
    supervisor_health: dict[str, Any],
    project_output_proof: dict[str, Any] | None = None,
    project_probe: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    project_probe = project_probe or _default_project_probe
    packet_ids = {_text(item.get("id")) for item in list(project_packet_registry.get("projects") or []) if isinstance(item, dict)}
    maturity_by_id = {
        _text(item.get("id")): _text(item.get("class"))
        for item in list(project_maturity_registry.get("projects") or [])
        if isinstance(item, dict)
    }
    core_ready = _core_runtime_ready(
        blocker_map=blocker_map,
        runtime_parity=runtime_parity,
        stable_operating_day=stable_operating_day,
        supervisor_health=supervisor_health,
    )
    single_live_blocker = _single_live_blocker(
        blocker_map=blocker_map,
        runtime_parity=runtime_parity,
        stable_operating_day=stable_operating_day,
        supervisor_health=supervisor_health,
    )

    projects = sorted(
        [dict(item) for item in list(contract_registry.get("projects") or []) if isinstance(item, dict)],
        key=lambda item: (int(item.get("factory_priority") or 999), _text(item.get("label"))),
    )

    records: list[dict[str, Any]] = []
    for project in projects:
        project_id = _text(project.get("project_id"))
        probe = dict(project_probe(project))
        safe_surface_status = _safe_surface_status(project, safe_surface_scope)
        readiness_tier = _readiness_tier(
            project=project,
            probe=probe,
            safe_surface_status=safe_surface_status,
            core_ready=core_ready,
        )
        autonomy_eligibility = _autonomy_eligibility(
            project=project,
            probe=probe,
            safe_surface_status=safe_surface_status,
            core_ready=core_ready,
        )
        blockers = _record_blockers(
            project=project,
            probe=probe,
            safe_surface_status=safe_surface_status,
            core_ready=core_ready,
            single_live_blocker=single_live_blocker,
        )
        record = {
            "project_id": project_id,
            "label": _text(project.get("label")) or project_id,
            "canonical_root": _text(project.get("canonical_root")),
            "local_app_root": probe.get("app_root"),
            "project_class": _text(project.get("project_class")),
            "platform_class": _text(project.get("platform_class")),
            "authority_class": _text(project.get("authority_class")),
            "routing_class": _text(project.get("routing_class")),
            "safe_surface_expectation": _text(project.get("safe_surface_expectation")) or None,
            "readiness_tier": readiness_tier,
            "authority_cleanliness": "clean" if int(probe.get("dirty_count") or 0) == 0 else "dirty",
            "build_health": (
                "missing_root"
                if not bool(probe.get("root_exists"))
                else (
                    "toolchain_missing"
                    if bool(probe.get("package_json_present")) and not bool(probe.get("node_modules_present"))
                    else _text(dict(project.get("observed_baseline") or {}).get("build_state")) or "unknown"
                )
            ),
            "autonomy_eligibility": autonomy_eligibility,
            "safe_surface_status": safe_surface_status,
            "athanor_project_registry_state": (
                "governed"
                if project_id in packet_ids
                else ("maturity_only" if project_id in maturity_by_id else "external_or_untracked")
            ),
            "maturity_class": maturity_by_id.get(project_id) or None,
            "factory_priority": int(project.get("factory_priority") or 999),
            "first_output_target": _text(project.get("first_output_target")),
            "next_tranche": _text(project.get("next_tranche")),
            "verification_bundle": _string_list(project.get("verification_bundle")),
            "acceptance_bundle": _string_list(project.get("acceptance_bundle")),
            "approval_posture": _text(project.get("approval_posture")),
            "rollback_or_archive_rule": _text(project.get("rollback_or_archive_rule")),
            "observed_baseline": dict(project.get("observed_baseline") or {}),
            "legacy_project_ids": _string_list(project.get("legacy_project_ids")),
            "sibling_roots": list(project.get("sibling_roots") or []),
            "blockers": blockers,
            "git": {
                "head": _text(probe.get("git_head")),
                "dirty_count": int(probe.get("dirty_count") or 0),
                "probe_incomplete": bool(probe.get("git_probe_incomplete")),
                "status_sample": list(probe.get("status_sample") or []),
            },
            "tooling": {
                "root_exists": bool(probe.get("root_exists")),
                "package_json_present": bool(probe.get("package_json_present")),
                "node_modules_present": bool(probe.get("node_modules_present")),
                "mobile_shell_present": bool(probe.get("mobile_shell_present")),
                "android_contract_present": bool(probe.get("android_contract_present")),
            },
        }
        records.append(record)

    top_priority, selection_reason = _top_priority_record(records, project_output_proof=project_output_proof)
    summary = {
        "project_count": len(records),
        "eligible_now_count": sum(1 for item in records if item["autonomy_eligibility"] == "eligible_now"),
        "held_by_core_runtime_gate_count": sum(1 for item in records if item["autonomy_eligibility"] == "held_by_core_runtime_gate"),
        "explicit_admission_required_count": sum(1 for item in records if item["autonomy_eligibility"] == "explicit_admission_required"),
        "denied_count": sum(1 for item in records if item["autonomy_eligibility"] == "denied_by_safe_surface"),
        "needs_root_count": sum(1 for item in records if item["autonomy_eligibility"] == "needs_root"),
        "single_live_blocker": single_live_blocker or "none",
        "top_priority_selection_reason": selection_reason,
        "broad_project_factory_ready": bool(core_ready and top_priority and top_priority.get("autonomy_eligibility") == "eligible_now"),
    }
    return {
        "generated_at": _iso_now(),
        "factory_operating_mode": "project_factory_active" if core_ready else "core_runtime_hold",
        "strategy": {
            "creative_first": bool(dict(contract_registry.get("strategy") or {}).get("creative_first")),
            "expansion_mode": _text(dict(contract_registry.get("strategy") or {}).get("expansion_mode")) or "unknown",
        },
        "core_runtime_gate": {
            "runtime_parity_class": _text(runtime_parity.get("drift_class")) or "unknown",
            "continuity_health_status": _text(supervisor_health.get("health_status")) or "unknown",
            "stable_operating_day_met": bool(stable_operating_day.get("met")),
            "stable_operating_day_hours": float(stable_operating_day.get("covered_window_hours") or 0.0),
            "stable_operating_day_required_hours": float(stable_operating_day.get("required_window_hours") or 24.0),
            "proof_gate_open": bool((blocker_map.get("proof_gate") or {}).get("open")),
            "blocking_check_ids": _string_list((blocker_map.get("proof_gate") or {}).get("blocking_check_ids")),
            "single_live_blocker": single_live_blocker or "none",
        },
        "top_priority_project_id": _text(top_priority.get("project_id")) or None,
        "top_priority_project_label": _text(top_priority.get("label")) or None,
        "top_priority_project": top_priority or None,
        "summary": summary,
        "projects": records,
        "source_artifacts": {
            "project_output_contract_registry": str(CONTRACT_REGISTRY_PATH),
            "project_packet_registry": str(PROJECT_PACKET_REGISTRY_PATH),
            "project_maturity_registry": str(PROJECT_MATURITY_REGISTRY_PATH),
            "safe_surface_scope": str(SAFE_SURFACE_SCOPE_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "stable_operating_day": str(STABLE_OPERATING_DAY_PATH),
            "continuity_supervisor_health": str(CONTINUITY_SUPERVISOR_HEALTH_PATH),
            "project_output_proof": str(PROJECT_OUTPUT_PROOF_PATH),
            "project_output_readiness": str(OUTPUT_PATH),
            "project_output_readiness_status": str(STATUS_MD_PATH),
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    top_priority = dict(payload.get("top_priority_project") or {})
    lines = [
        "# Project Output Readiness",
        "",
        f"- Generated at: {payload.get('generated_at')}",
        f"- Factory operating mode: `{payload.get('factory_operating_mode')}`",
        f"- Broad project factory ready: `{str(bool(summary.get('broad_project_factory_ready'))).lower()}`",
        f"- Single live blocker: `{summary.get('single_live_blocker') or 'none'}`",
        f"- Top priority project: `{payload.get('top_priority_project_label') or 'none'}`",
        f"- Top priority selection reason: `{summary.get('top_priority_selection_reason') or 'factory_priority'}`",
        "",
        "## Top Priority",
        "",
    ]
    if top_priority:
        lines.extend(
            [
                f"- Project id: `{top_priority.get('project_id')}`",
                f"- Readiness tier: `{top_priority.get('readiness_tier')}`",
                f"- Autonomy eligibility: `{top_priority.get('autonomy_eligibility')}`",
                f"- First output target: {top_priority.get('first_output_target')}",
                f"- Next tranche: {top_priority.get('next_tranche')}",
                f"- Blockers: `{list(top_priority.get('blockers') or [])}`",
            ]
        )
    else:
        lines.append("- No project contracts are registered.")

    lines.extend(["", "## Projects", ""])
    for record in list(payload.get("projects") or []):
        lines.append(
            f"- `{record.get('project_id')}`: `{record.get('readiness_tier')}` / `{record.get('autonomy_eligibility')}` / "
            f"`{record.get('safe_surface_status')}` / blockers={list(record.get('blockers') or [])}"
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor project-output readiness ledger.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when generated outputs are stale.")
    args = parser.parse_args()

    payload = build_payload(
        contract_registry=_load_optional_json(CONTRACT_REGISTRY_PATH),
        project_packet_registry=_load_optional_json(PROJECT_PACKET_REGISTRY_PATH),
        project_maturity_registry=_load_optional_json(PROJECT_MATURITY_REGISTRY_PATH),
        safe_surface_scope=_load_safe_surface_scope(),
        blocker_map=_load_optional_json(BLOCKER_MAP_PATH),
        runtime_parity=_load_optional_json(RUNTIME_PARITY_PATH),
        stable_operating_day=_load_optional_json(STABLE_OPERATING_DAY_PATH),
        supervisor_health=_load_optional_json(CONTINUITY_SUPERVISOR_HEALTH_PATH),
        project_output_proof=_load_optional_json(PROJECT_OUTPUT_PROOF_PATH),
    )
    rendered_json = _json_render(payload)
    rendered_md = _markdown(payload)
    current_json = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    current_md = STATUS_MD_PATH.read_text(encoding="utf-8") if STATUS_MD_PATH.exists() else ""
    comparable_json, comparable_md = _render_against_existing(payload, current_json)
    if args.check:
        if current_json != comparable_json or current_md != comparable_md:
            print(f"{OUTPUT_PATH} or {STATUS_MD_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current_json == comparable_json and current_md == comparable_md:
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(str(OUTPUT_PATH))
        return 0
    if current_json != rendered_json:
        OUTPUT_PATH.write_text(rendered_json, encoding="utf-8")
    if current_md != rendered_md:
        STATUS_MD_PATH.write_text(rendered_md, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
