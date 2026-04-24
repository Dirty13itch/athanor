#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_ATLAS_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "generated" / "master-atlas.json"
OPERATOR_MOBILE_SUMMARY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "operator-mobile-summary.json"
PROJECT_OUTPUT_READINESS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-readiness.json"
PROJECT_OUTPUT_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-proof.json"
UI_AUDIT_LAST_RUN_PATH = REPO_ROOT / "tests" / "ui-audit" / "last-run.json"
LIVE_DASHBOARD_SMOKE_PATH = REPO_ROOT / "tests" / "ui-audit" / "live-dashboard-smoke-last.json"
UI_AUDIT_FINDINGS_LEDGER_PATH = REPO_ROOT / "tests" / "ui-audit" / "findings-ledger.json"
UI_AUDIT_UNCOVERED_SURFACES_PATH = REPO_ROOT / "tests" / "ui-audit" / "uncovered-surfaces.json"
PROJECTS_CONSOLE_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "features" / "projects" / "projects-console.tsx"
OPERATOR_CONSOLE_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "features" / "operator" / "operator-console.tsx"
ROOT_COMMAND_CENTER_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "features" / "overview" / "command-center.tsx"
MASTER_ATLAS_API_ROUTE_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "master-atlas" / "route.ts"
PROJECT_FACTORY_API_ROUTE_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "projects" / "factory" / "route.ts"
OPERATOR_MOBILE_SUMMARY_API_ROUTE_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "operator" / "mobile-summary" / "route.ts"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "command-center-final-form-status.json"

PROJECT_FACTORY_SUMMARY_KEYS = (
    "factory_operating_mode",
    "top_priority_project_id",
    "top_priority_project_label",
    "accepted_project_output_count",
    "pending_candidate_count",
    "pending_hybrid_acceptance_count",
    "latest_pending_project_id",
    "project_output_stage_met",
)
MASTER_ATLAS_SUMMARY_KEYS = (
    "project_factory_operating_mode",
    "project_factory_top_priority_project_id",
    "project_factory_top_priority_project_label",
    "accepted_project_output_count",
    "pending_project_output_candidate_count",
    "pending_hybrid_project_output_count",
    "project_factory_latest_pending_project_id",
    "project_output_stage_met",
)
LIVE_SMOKE_API_FAILURE_PATTERN = re.compile(
    r"^(?:post )?api (?P<path>/api/\S+) (?:(?:failed: HTTP Error (?P<http_error>\d+):)"
    r"|(?:unexpected status: (?P<unexpected_status>\d+)))"
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _required_keys_present(candidate: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(key in candidate for key in keys)


def _severity_rank(value: str) -> int:
    order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }
    return order.get(str(value).lower(), 0)


def _last_ui_audit_generated_at(last_run: dict[str, Any]) -> str | None:
    value = last_run.get("generatedAt")
    return str(value) if isinstance(value, str) and value else None


def _load_live_dashboard_smoke_payload(
    *,
    live_dashboard_smoke: dict[str, Any],
    ui_audit_last_run: dict[str, Any],
) -> dict[str, Any]:
    if live_dashboard_smoke:
        return live_dashboard_smoke
    for result in ui_audit_last_run.get("results", []):
        if not isinstance(result, dict) or str(result.get("label") or "") != "dashboard:live-smoke":
            continue
        stdout = result.get("stdout")
        if not isinstance(stdout, str) or not stdout.strip():
            continue
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _parse_live_smoke_api_failures(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for item in payload.get("failures", []):
        if not isinstance(item, str):
            continue
        match = LIVE_SMOKE_API_FAILURE_PATTERN.match(item)
        if not match:
            continue
        code = match.group("http_error") or match.group("unexpected_status")
        parsed[match.group("path")] = {
            "status": int(code) if code else None,
            "detail": item,
        }
    return parsed


def _load_live_smoke_api_runtime_status(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runtime_status = payload.get("apiRuntimeStatus")
    if not isinstance(runtime_status, dict):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for route, status in runtime_status.items():
        if not isinstance(route, str) or not isinstance(status, dict):
            continue
        semantic_status = status.get("semanticStatus")
        if not isinstance(semantic_status, str) or not semantic_status:
            continue
        parsed[route] = {
            "semantic_status": semantic_status,
            "detail": status.get("detail") if isinstance(status.get("detail"), str) else None,
        }
    return parsed


def _load_live_smoke_route_runtime_status(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runtime_status = payload.get("routeRuntimeStatus")
    if not isinstance(runtime_status, dict):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for route, status in runtime_status.items():
        if not isinstance(route, str) or not isinstance(status, dict):
            continue
        semantic_status = status.get("semanticStatus")
        if not isinstance(semantic_status, str) or not semantic_status:
            continue
        parsed[route] = {
            "semantic_status": semantic_status,
            "detail": status.get("detail") if isinstance(status.get("detail"), str) else None,
        }
    return parsed


def _build_route_status(
    *,
    route: str,
    tranche: str,
    contract_met: bool,
    last_successful_evidence_pass_at: str | None,
) -> dict[str, Any]:
    return {
        "route": route,
        "tranche": tranche,
        "status": "ready" if contract_met else "needs_work",
        "verification_state": "verified_once" if contract_met and last_successful_evidence_pass_at else "pending",
        "last_successful_evidence_pass_at": last_successful_evidence_pass_at,
    }


def _calculate_clean_pass_streak(
    *,
    last_ui_audit_generated_at: str | None,
    last_ui_audit_clean: bool,
    previous_status: dict[str, Any] | None,
) -> int:
    if not last_ui_audit_clean:
        return 0

    previous_summary = dict((previous_status or {}).get("summary") or {})
    previous_generated_at = previous_summary.get("latest_ui_audit_generated_at")
    previous_clean = bool(previous_summary.get("latest_ui_audit_clean"))
    previous_streak = int(previous_summary.get("consecutive_clean_ui_audit_pass_count") or 0)

    if (
        isinstance(previous_generated_at, str)
        and last_ui_audit_generated_at
        and previous_generated_at == last_ui_audit_generated_at
        and previous_clean
        and previous_streak > 0
    ):
        return previous_streak

    if isinstance(previous_generated_at, str) and previous_generated_at and previous_clean and previous_streak > 0:
        return previous_streak + 1

    return 1


def build_payload(
    *,
    master_atlas: dict[str, Any],
    operator_mobile_summary: dict[str, Any],
    project_output_readiness: dict[str, Any],
    project_output_proof: dict[str, Any],
    previous_status: dict[str, Any] | None,
    ui_audit_last_run: dict[str, Any],
    live_dashboard_smoke: dict[str, Any],
    ui_audit_findings_ledger: dict[str, Any],
    ui_audit_uncovered_surfaces: dict[str, Any],
    projects_console_source: str,
    operator_console_source: str,
    root_command_center_source: str,
    master_atlas_api_source: str = "",
    project_factory_api_source: str,
    operator_mobile_summary_api_source: str,
) -> dict[str, Any]:
    master_atlas_summary = dict(master_atlas.get("summary") or {})
    project_factory_summary = dict(operator_mobile_summary.get("project_factory") or {})
    project_output_stage = dict(project_output_proof.get("stage_status") or {})
    latest_pending_candidate = dict(project_output_proof.get("latest_pending_candidate") or {})
    findings = list(ui_audit_findings_ledger.get("findings") or [])
    open_findings = [item for item in findings if isinstance(item, dict) and str(item.get("status") or "") != "resolved"]
    uncovered_surfaces = list(ui_audit_uncovered_surfaces.get("surfaces") or [])
    last_ui_audit_generated_at = _last_ui_audit_generated_at(ui_audit_last_run)
    live_dashboard_smoke_payload = _load_live_dashboard_smoke_payload(
        live_dashboard_smoke=live_dashboard_smoke,
        ui_audit_last_run=ui_audit_last_run,
    )
    live_dashboard_smoke_generated_at = live_dashboard_smoke_payload.get("generatedAt")
    live_smoke_api_failures = _parse_live_smoke_api_failures(live_dashboard_smoke_payload)
    live_smoke_api_runtime_status = _load_live_smoke_api_runtime_status(live_dashboard_smoke_payload)
    live_smoke_route_runtime_status = _load_live_smoke_route_runtime_status(live_dashboard_smoke_payload)
    live_master_atlas_failure = live_smoke_api_failures.get("/api/master-atlas")
    live_operator_mobile_summary_failure = live_smoke_api_failures.get("/api/operator/mobile-summary")
    live_project_factory_failure = live_smoke_api_failures.get("/api/projects/factory")
    live_master_atlas_runtime = live_smoke_api_runtime_status.get("/api/master-atlas")
    live_operator_mobile_summary_runtime = live_smoke_api_runtime_status.get("/api/operator/mobile-summary")
    live_project_factory_runtime = live_smoke_api_runtime_status.get("/api/projects/factory")
    live_root_runtime = live_smoke_route_runtime_status.get("/")
    live_operator_runtime = live_smoke_route_runtime_status.get("/operator")
    live_projects_runtime = live_smoke_route_runtime_status.get("/projects")
    last_ui_audit_failures = list(ui_audit_last_run.get("failures") or [])
    last_ui_audit_clean = not last_ui_audit_failures and not uncovered_surfaces
    consecutive_clean_ui_audit_pass_count = _calculate_clean_pass_streak(
        last_ui_audit_generated_at=last_ui_audit_generated_at,
        last_ui_audit_clean=last_ui_audit_clean,
        previous_status=previous_status,
    )

    shared_project_factory_summary_met = _required_keys_present(
        project_factory_summary, PROJECT_FACTORY_SUMMARY_KEYS
    ) and _required_keys_present(master_atlas_summary, MASTER_ATLAS_SUMMARY_KEYS)
    projects_console_contract_met = (
        '"/api/projects/factory"' in projects_console_source
        and "Project Factory" in projects_console_source
        and "first-class governed lanes".lower() in projects_console_source.lower()
    )
    operator_review_contract_met = (
        "Project-output review" in operator_console_source
        and 'href="/projects"' in operator_console_source
    )
    root_front_door_contract_met = (
        "Project factory" in root_command_center_source
        and 'href: "/projects"' in root_command_center_source
        and "next governed move".lower() in root_command_center_source.lower()
    )
    master_atlas_api_contract_met = (
        "readGeneratedMasterAtlas" in master_atlas_api_source
        and "pickMasterAtlasRelationshipMap" in master_atlas_api_source
    )
    front_door_api_contract_met = (
        "loadOperatorMobileSummary" in operator_mobile_summary_api_source
        and "loadProjectFactorySnapshot" in project_factory_api_source
    )

    route_status = {
        "/": _build_route_status(
            route="/",
            tranche="executive_front_door",
            contract_met=shared_project_factory_summary_met and root_front_door_contract_met,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
        "/operator": _build_route_status(
            route="/operator",
            tranche="operator_desk",
            contract_met=operator_review_contract_met,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
        "/projects": _build_route_status(
            route="/projects",
            tranche="project_factory_console",
            contract_met=projects_console_contract_met,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
        "/api/master-atlas": _build_route_status(
            route="/api/master-atlas",
            tranche="api_contract",
            contract_met=master_atlas_api_contract_met and not live_master_atlas_failure,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
        "/api/operator/mobile-summary": _build_route_status(
            route="/api/operator/mobile-summary",
            tranche="api_contract",
            contract_met=front_door_api_contract_met and not live_operator_mobile_summary_failure,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
        "/api/projects/factory": _build_route_status(
            route="/api/projects/factory",
            tranche="api_contract",
            contract_met=front_door_api_contract_met and not live_project_factory_failure,
            last_successful_evidence_pass_at=last_ui_audit_generated_at if last_ui_audit_clean else None,
        ),
    }
    if live_master_atlas_failure:
        route_status["/api/master-atlas"] = {
            "route": "/api/master-atlas",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": f"live_http_{live_master_atlas_failure.get('status')}",
            "last_successful_evidence_pass_at": None,
        }
    elif live_master_atlas_runtime and live_master_atlas_runtime.get("semantic_status") != "ok":
        route_status["/api/master-atlas"] = {
            "route": "/api/master-atlas",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": str(live_master_atlas_runtime.get("semantic_status")),
            "last_successful_evidence_pass_at": None,
        }
    if live_operator_mobile_summary_failure:
        route_status["/api/operator/mobile-summary"] = {
            "route": "/api/operator/mobile-summary",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": f"live_http_{live_operator_mobile_summary_failure.get('status')}",
            "last_successful_evidence_pass_at": None,
        }
    elif live_operator_mobile_summary_runtime and live_operator_mobile_summary_runtime.get("semantic_status") != "ok":
        route_status["/api/operator/mobile-summary"] = {
            "route": "/api/operator/mobile-summary",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": str(live_operator_mobile_summary_runtime.get("semantic_status")),
            "last_successful_evidence_pass_at": None,
        }
    if live_project_factory_failure:
        route_status["/api/projects/factory"] = {
            "route": "/api/projects/factory",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": f"live_http_{live_project_factory_failure.get('status')}",
            "last_successful_evidence_pass_at": None,
        }
    elif live_project_factory_runtime and live_project_factory_runtime.get("semantic_status") != "ok":
        route_status["/api/projects/factory"] = {
            "route": "/api/projects/factory",
            "tranche": "api_contract",
            "status": "blocked",
            "verification_state": str(live_project_factory_runtime.get("semantic_status")),
            "last_successful_evidence_pass_at": None,
        }
    for route, runtime in (
        ("/", live_root_runtime),
        ("/operator", live_operator_runtime),
        ("/projects", live_projects_runtime),
    ):
        if runtime and runtime.get("semantic_status") != "ok":
            route_status[route] = {
                "route": route,
                "tranche": route_status[route]["tranche"],
                "status": "blocked",
                "verification_state": str(runtime.get("semantic_status")),
                "last_successful_evidence_pass_at": None,
            }

    open_gaps: list[dict[str, Any]] = []
    if not shared_project_factory_summary_met:
        open_gaps.append(
            {
                "id": "shared-project-factory-summary",
                "route": "/",
                "severity": "high",
                "tranche": "executive_front_door",
                "verification_state": "missing_shared_projection",
                "detail": "Executive read models are missing one or more shared project-factory summary fields.",
                "last_successful_evidence_pass_at": None,
            }
        )
    if not root_front_door_contract_met:
        open_gaps.append(
            {
                "id": "root-front-door-contract",
                "route": "/",
                "severity": "high",
                "tranche": "executive_front_door",
                "verification_state": "route_contract_missing",
                "detail": "The root command center source is still missing one or more required executive front-door blocks or project-factory route ownership links.",
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_root_runtime and live_root_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "root-live-first-paint-semantic-mismatch",
                "route": "/",
                "severity": "high",
                "tranche": "executive_front_door",
                "verification_state": str(live_root_runtime.get("semantic_status")),
                "detail": str(
                    live_root_runtime.get("detail")
                    or "Root route first paint still hides live command-center truth."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if not operator_review_contract_met and int(project_output_proof.get("pending_hybrid_acceptance_count") or 0) > 0:
        open_gaps.append(
            {
                "id": "operator-project-review-surface",
                "route": "/operator",
                "severity": "high",
                "tranche": "operator_desk",
                "verification_state": "pending_review_not_visible",
                "detail": "Hybrid project-output review exists but the operator desk source does not yet expose the required review block and project-factory handoff.",
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_operator_runtime and live_operator_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "operator-live-first-paint-semantic-mismatch",
                "route": "/operator",
                "severity": "high",
                "tranche": "operator_desk",
                "verification_state": str(live_operator_runtime.get("semantic_status")),
                "detail": str(
                    live_operator_runtime.get("detail")
                    or "Operator route first paint still hides live operator truth."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if not projects_console_contract_met:
        open_gaps.append(
            {
                "id": "projects-project-factory-console",
                "route": "/projects",
                "severity": "high",
                "tranche": "project_factory_console",
                "verification_state": "route_contract_missing",
                "detail": "The projects route source is not yet wired to the governed project-factory API and route contract.",
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_projects_runtime and live_projects_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "projects-live-first-paint-semantic-mismatch",
                "route": "/projects",
                "severity": "high",
                "tranche": "project_factory_console",
                "verification_state": str(live_projects_runtime.get("semantic_status")),
                "detail": str(
                    live_projects_runtime.get("detail")
                    or "Projects route first paint still hides live project-factory truth."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if not front_door_api_contract_met:
        open_gaps.append(
            {
                "id": "front-door-api-json-contract",
                "route": "/api/operator/mobile-summary",
                "severity": "high",
                "tranche": "api_contract",
                "verification_state": "route_or_loader_missing",
                "detail": "One or more front-door JSON routes are not yet backed by the required server-side loaders.",
                "last_successful_evidence_pass_at": None,
            }
        )
    if not master_atlas_api_contract_met:
        open_gaps.append(
            {
                "id": "master-atlas-api-json-contract",
                "route": "/api/master-atlas",
                "severity": "high",
                "tranche": "api_contract",
                "verification_state": "route_or_loader_missing",
                "detail": "The master-atlas JSON route is not yet backed by the required server-side loader and relationship-map projection.",
                "last_successful_evidence_pass_at": None,
            }
        )
    if live_master_atlas_failure:
        open_gaps.append(
            {
                "id": "master-atlas-live-runtime-mismatch",
                "route": "/api/master-atlas",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": f"live_http_{live_master_atlas_failure.get('status')}",
                "detail": (
                    "Live dashboard runtime returns "
                    f"{live_master_atlas_failure.get('status')} for /api/master-atlas "
                    "even though the source route exists. The active dashboard atlas feed is stale or missing."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_master_atlas_runtime and live_master_atlas_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "master-atlas-live-semantic-mismatch",
                "route": "/api/master-atlas",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": str(live_master_atlas_runtime.get("semantic_status")),
                "detail": str(
                    live_master_atlas_runtime.get("detail")
                    or "Live dashboard runtime serves a semantically stale or incomplete master-atlas payload."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if live_operator_mobile_summary_failure:
        open_gaps.append(
            {
                "id": "operator-mobile-summary-live-runtime-mismatch",
                "route": "/api/operator/mobile-summary",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": f"live_http_{live_operator_mobile_summary_failure.get('status')}",
                "detail": (
                    "Live dashboard runtime returns "
                    f"{live_operator_mobile_summary_failure.get('status')} for /api/operator/mobile-summary "
                    "even though the source route exists. The active /opt/athanor/dashboard bundle is stale."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_operator_mobile_summary_runtime and live_operator_mobile_summary_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "operator-mobile-summary-live-semantic-mismatch",
                "route": "/api/operator/mobile-summary",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": str(live_operator_mobile_summary_runtime.get("semantic_status")),
                "detail": str(
                    live_operator_mobile_summary_runtime.get("detail")
                    or "Live dashboard runtime serves a semantically incomplete operator mobile summary payload."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if live_project_factory_failure:
        open_gaps.append(
            {
                "id": "projects-factory-live-runtime-mismatch",
                "route": "/api/projects/factory",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": f"live_http_{live_project_factory_failure.get('status')}",
                "detail": (
                    "Live dashboard runtime returns "
                    f"{live_project_factory_failure.get('status')} for /api/projects/factory "
                    "even though the source route exists. The active /opt/athanor/dashboard bundle is stale."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    elif live_project_factory_runtime and live_project_factory_runtime.get("semantic_status") != "ok":
        open_gaps.append(
            {
                "id": "projects-factory-live-semantic-mismatch",
                "route": "/api/projects/factory",
                "severity": "high",
                "tranche": "deployment",
                "verification_state": str(live_project_factory_runtime.get("semantic_status")),
                "detail": str(
                    live_project_factory_runtime.get("detail")
                    or "Live dashboard runtime serves a semantically incomplete project factory payload."
                ),
                "last_successful_evidence_pass_at": None,
            }
        )
    if uncovered_surfaces:
        open_gaps.append(
            {
                "id": "ui-audit-uncovered-surfaces",
                "route": "/",
                "severity": "high",
                "tranche": "verification",
                "verification_state": "coverage_gap",
                "detail": f"UI audit still reports {len(uncovered_surfaces)} uncovered surface(s).",
                "last_successful_evidence_pass_at": None,
            }
        )
    if open_findings:
        highest_open_finding = max(
            (str(item.get("severity") or "low").lower() for item in open_findings),
            key=_severity_rank,
            default="low",
        )
        open_gaps.append(
            {
                "id": "ui-audit-open-findings",
                "route": "/",
                "severity": highest_open_finding,
                "tranche": "verification",
                "verification_state": "audit_findings_open",
                "detail": f"UI audit findings ledger still contains {len(open_findings)} unresolved finding(s).",
                "last_successful_evidence_pass_at": None,
            }
        )
    if last_ui_audit_failures:
        open_gaps.append(
            {
                "id": "ui-audit-last-run-failures",
                "route": "/",
                "severity": "high",
                "tranche": "verification",
                "verification_state": "last_run_failed",
                "detail": f"The latest UI audit run reported {len(last_ui_audit_failures)} failing job(s).",
                "last_successful_evidence_pass_at": None,
            }
        )
    if consecutive_clean_ui_audit_pass_count < 2:
        open_gaps.append(
            {
                "id": "ui-audit-clean-pass-streak",
                "route": "/",
                "severity": "medium",
                "tranche": "verification",
                "verification_state": "needs_second_clean_pass",
                "detail": "The final-form bar requires two consecutive UI audit passes with no new actionable findings.",
                "last_successful_evidence_pass_at": last_ui_audit_generated_at if last_ui_audit_clean else None,
            }
        )

    highest_severity = (
        max((gap["severity"] for gap in open_gaps), key=_severity_rank, default="none")
        if open_gaps
        else "none"
    )
    latest_ui_audit_result = next(
        (
            item
            for item in ui_audit_last_run.get("results", [])
            if isinstance(item, dict) and str(item.get("label") or "") == "dashboard:live-smoke"
        ),
        None,
    )

    return {
        "generated_at": _iso_now(),
        "status": "complete" if not open_gaps else "in_progress",
        "done": not open_gaps,
        "summary": {
            "open_gap_count": len(open_gaps),
            "highest_severity": highest_severity,
            "consecutive_clean_ui_audit_pass_count": consecutive_clean_ui_audit_pass_count,
            "latest_ui_audit_generated_at": last_ui_audit_generated_at,
            "latest_ui_audit_clean": last_ui_audit_clean,
            "latest_ui_audit_failure_count": len(last_ui_audit_failures),
            "latest_live_dashboard_smoke_generated_at": (
                str(live_dashboard_smoke_generated_at) if isinstance(live_dashboard_smoke_generated_at, str) else None
            ),
            "live_dashboard_smoke_failure_count": len(live_dashboard_smoke_payload.get("failures") or []),
            "live_dashboard_api_failure_count": len(live_smoke_api_failures),
            "uncovered_surface_count": len(uncovered_surfaces),
            "pending_hybrid_acceptance_count": int(project_output_proof.get("pending_hybrid_acceptance_count") or 0),
            "pending_candidate_count": int(project_output_proof.get("pending_candidate_count") or 0),
            "accepted_project_output_count": int(project_output_proof.get("accepted_project_output_count") or 0),
            "top_priority_project_id": str(project_output_readiness.get("top_priority_project_id") or "none"),
            "top_priority_project_label": str(project_output_readiness.get("top_priority_project_label") or "none"),
            "project_output_stage_met": bool(project_output_stage.get("met")),
            "latest_pending_project_id": str(latest_pending_candidate.get("project_id") or "none"),
        },
        "route_status": route_status,
        "open_gaps": open_gaps,
        "latest_ui_audit_dashboard_result": {
            "returncode": int(latest_ui_audit_result.get("returncode") or 0) if isinstance(latest_ui_audit_result, dict) else None,
            "label": latest_ui_audit_result.get("label") if isinstance(latest_ui_audit_result, dict) else None,
        },
        "source_artifacts": {
            "master_atlas": str(MASTER_ATLAS_PATH),
            "operator_mobile_summary": str(OPERATOR_MOBILE_SUMMARY_PATH),
            "project_output_readiness": str(PROJECT_OUTPUT_READINESS_PATH),
            "project_output_proof": str(PROJECT_OUTPUT_PROOF_PATH),
            "ui_audit_last_run": str(UI_AUDIT_LAST_RUN_PATH),
            "live_dashboard_smoke": str(LIVE_DASHBOARD_SMOKE_PATH),
            "ui_audit_findings_ledger": str(UI_AUDIT_FINDINGS_LEDGER_PATH),
            "ui_audit_uncovered_surfaces": str(UI_AUDIT_UNCOVERED_SURFACES_PATH),
            "projects_console_source": str(PROJECTS_CONSOLE_PATH),
            "operator_console_source": str(OPERATOR_CONSOLE_PATH),
            "root_command_center_source": str(ROOT_COMMAND_CENTER_PATH),
            "master_atlas_api_route": str(MASTER_ATLAS_API_ROUTE_PATH),
            "project_factory_api_route": str(PROJECT_FACTORY_API_ROUTE_PATH),
            "operator_mobile_summary_api_route": str(OPERATOR_MOBILE_SUMMARY_API_ROUTE_PATH),
            "command_center_final_form_status": str(OUTPUT_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the command-center final-form status ledger.")
    parser.add_argument("--json", action="store_true", help="Print JSON after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when the artifact is stale.")
    args = parser.parse_args()

    payload = build_payload(
        master_atlas=_load_optional_json(MASTER_ATLAS_PATH),
        operator_mobile_summary=_load_optional_json(OPERATOR_MOBILE_SUMMARY_PATH),
        project_output_readiness=_load_optional_json(PROJECT_OUTPUT_READINESS_PATH),
        project_output_proof=_load_optional_json(PROJECT_OUTPUT_PROOF_PATH),
        previous_status=_load_optional_json(OUTPUT_PATH),
        ui_audit_last_run=_load_optional_json(UI_AUDIT_LAST_RUN_PATH),
        live_dashboard_smoke=_load_optional_json(LIVE_DASHBOARD_SMOKE_PATH),
        ui_audit_findings_ledger=_load_optional_json(UI_AUDIT_FINDINGS_LEDGER_PATH),
        ui_audit_uncovered_surfaces=_load_optional_json(UI_AUDIT_UNCOVERED_SURFACES_PATH),
        projects_console_source=_load_optional_text(PROJECTS_CONSOLE_PATH),
        operator_console_source=_load_optional_text(OPERATOR_CONSOLE_PATH),
        root_command_center_source=_load_optional_text(ROOT_COMMAND_CENTER_PATH),
        master_atlas_api_source=_load_optional_text(MASTER_ATLAS_API_ROUTE_PATH),
        project_factory_api_source=_load_optional_text(PROJECT_FACTORY_API_ROUTE_PATH),
        operator_mobile_summary_api_source=_load_optional_text(OPERATOR_MOBILE_SUMMARY_API_ROUTE_PATH),
    )
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if args.check:
        if current != rendered:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
