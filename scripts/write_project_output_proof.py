#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "project-output-contract-registry.json"
AUTONOMOUS_VALUE_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomous-value-proof.json"
PROJECT_OUTPUT_CANDIDATES_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-candidates.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-proof.json"
STATUS_MD_PATH = REPO_ROOT / "docs" / "operations" / "PROJECT-OUTPUT-PROOF.md"
REQUIRED_PROJECT_OUTPUTS = 3
REQUIRED_DISTINCT_PROJECTS = 3
REQUIRED_USER_FACING_OUTPUTS = 1
REQUIRED_EXTERNAL_PROJECT_OUTPUTS = 1


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


def _build_alias_map(contract_registry: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    projects_by_id: dict[str, dict[str, Any]] = {}
    alias_to_project_id: dict[str, str] = {}
    for item in list(contract_registry.get("projects") or []):
        if not isinstance(item, dict):
            continue
        project_id = _text(item.get("project_id"))
        if not project_id:
            continue
        projects_by_id[project_id] = dict(item)
        alias_to_project_id[project_id] = project_id
        for alias in _string_list(item.get("legacy_project_ids")):
            alias_to_project_id[alias] = project_id
    return projects_by_id, alias_to_project_id


def _is_user_facing(entry: dict[str, Any]) -> bool:
    value_class = _text(entry.get("value_class"))
    beneficiary_surface = _text(entry.get("beneficiary_surface"))
    return value_class == "product_value" or beneficiary_surface not in {"", "athanor_core"}


def build_payload(
    *,
    contract_registry: dict[str, Any],
    autonomous_value_proof: dict[str, Any],
    project_output_candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_output_candidates = dict(project_output_candidates or {})
    projects_by_id, alias_to_project_id = _build_alias_map(contract_registry)
    accepted_input = [dict(item) for item in list(autonomous_value_proof.get("accepted_entries") or []) if isinstance(item, dict)]
    disqualified_input = [dict(item) for item in list(autonomous_value_proof.get("disqualified_entries") or []) if isinstance(item, dict)]

    accepted_entries: list[dict[str, Any]] = []
    disqualified_entries: list[dict[str, Any]] = []
    project_summaries: dict[str, dict[str, Any]] = {
        project_id: {
            "counted": False,
            "accepted_count": 0,
            "disqualified_count": 0,
            "authority_class": _text(project.get("authority_class")),
            "label": _text(project.get("label")) or project_id,
        }
        for project_id, project in projects_by_id.items()
    }

    for entry in accepted_input:
        raw_project_id = _text(entry.get("project_id"))
        canonical_project_id = alias_to_project_id.get(raw_project_id)
        counted = canonical_project_id is not None
        record = {
            **entry,
            "source_project_id": raw_project_id,
            "project_id": canonical_project_id or raw_project_id or "unscoped",
            "counted": counted,
        }
        if counted:
            authority_class = _text(projects_by_id[canonical_project_id].get("authority_class"))
            record["external_project"] = authority_class not in {"athanor_in_repo_project", "needs_root"}
            record["user_facing"] = _is_user_facing(record)
            accepted_entries.append(record)
            project_summaries.setdefault(
                canonical_project_id,
                {
                    "counted": False,
                    "accepted_count": 0,
                    "disqualified_count": 0,
                    "authority_class": authority_class,
                    "label": _text(projects_by_id[canonical_project_id].get("label")) or canonical_project_id,
                },
            )
            project_summaries[canonical_project_id]["counted"] = True
            project_summaries[canonical_project_id]["accepted_count"] += 1
        else:
            project_summaries.setdefault(
                raw_project_id or "unscoped",
                {
                    "counted": False,
                    "accepted_count": 0,
                    "disqualified_count": 0,
                    "authority_class": "out_of_scope",
                    "label": raw_project_id or "unscoped",
                },
            )

    for entry in disqualified_input:
        raw_project_id = _text(entry.get("project_id"))
        canonical_project_id = alias_to_project_id.get(raw_project_id)
        record = {
            **entry,
            "source_project_id": raw_project_id,
            "project_id": canonical_project_id or raw_project_id or "unscoped",
            "counted": canonical_project_id is not None,
        }
        if canonical_project_id is not None:
            project_summaries.setdefault(
                canonical_project_id,
                {
                    "counted": False,
                    "accepted_count": 0,
                    "disqualified_count": 0,
                    "authority_class": _text(projects_by_id[canonical_project_id].get("authority_class")),
                    "label": _text(projects_by_id[canonical_project_id].get("label")) or canonical_project_id,
                },
            )
            project_summaries[canonical_project_id]["disqualified_count"] += 1
        disqualified_entries.append(record)

    accepted_entries.sort(key=lambda item: (_text(item.get("accepted_at")), _text(item.get("packet_id"))))
    distinct_project_count = len({_text(item.get("project_id")) for item in accepted_entries if _text(item.get("project_id"))})
    accepted_user_facing_output_count = sum(1 for item in accepted_entries if bool(item.get("user_facing")))
    accepted_external_project_output_count = sum(1 for item in accepted_entries if bool(item.get("external_project")))
    latest_accepted_entry = accepted_entries[-1] if accepted_entries else None
    pending_candidate_count = int(project_output_candidates.get("pending_candidate_count") or 0)
    pending_hybrid_acceptance_count = int(project_output_candidates.get("pending_hybrid_acceptance_count") or 0)
    latest_pending_candidate = dict(project_output_candidates.get("latest_pending_candidate") or {}) or None

    stage_status = {
        "met": (
            len(accepted_entries) >= REQUIRED_PROJECT_OUTPUTS
            and distinct_project_count >= REQUIRED_DISTINCT_PROJECTS
            and accepted_user_facing_output_count >= REQUIRED_USER_FACING_OUTPUTS
            and accepted_external_project_output_count >= REQUIRED_EXTERNAL_PROJECT_OUTPUTS
        ),
        "required_project_outputs": REQUIRED_PROJECT_OUTPUTS,
        "required_distinct_projects": REQUIRED_DISTINCT_PROJECTS,
        "required_user_facing_outputs": REQUIRED_USER_FACING_OUTPUTS,
        "required_external_project_outputs": REQUIRED_EXTERNAL_PROJECT_OUTPUTS,
        "remaining_project_outputs": max(0, REQUIRED_PROJECT_OUTPUTS - len(accepted_entries)),
        "remaining_distinct_projects": max(0, REQUIRED_DISTINCT_PROJECTS - distinct_project_count),
        "remaining_user_facing_outputs": max(0, REQUIRED_USER_FACING_OUTPUTS - accepted_user_facing_output_count),
        "remaining_external_project_outputs": max(0, REQUIRED_EXTERNAL_PROJECT_OUTPUTS - accepted_external_project_output_count),
    }

    return {
        "generated_at": _iso_now(),
        "accepted_project_output_count": len(accepted_entries),
        "distinct_project_count": distinct_project_count,
        "accepted_user_facing_output_count": accepted_user_facing_output_count,
        "accepted_external_project_output_count": accepted_external_project_output_count,
        "pending_candidate_count": pending_candidate_count,
        "pending_hybrid_acceptance_count": pending_hybrid_acceptance_count,
        "disqualified_project_output_count": len(disqualified_entries),
        "stage_status": stage_status,
        "latest_accepted_entry": latest_accepted_entry,
        "latest_pending_candidate": latest_pending_candidate,
        "accepted_entries": accepted_entries,
        "disqualified_entries": disqualified_entries,
        "project_summaries": project_summaries,
        "source_artifacts": {
            "project_output_contract_registry": str(CONTRACT_REGISTRY_PATH),
            "autonomous_value_proof": str(AUTONOMOUS_VALUE_PROOF_PATH),
            "project_output_candidates": str(PROJECT_OUTPUT_CANDIDATES_PATH),
            "project_output_proof": str(OUTPUT_PATH),
            "project_output_proof_status": str(STATUS_MD_PATH),
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    stage_status = dict(payload.get("stage_status") or {})
    latest = dict(payload.get("latest_accepted_entry") or {})
    lines = [
        "# Project Output Proof",
        "",
        f"- Generated at: {payload.get('generated_at')}",
        f"- Accepted project outputs: {int(payload.get('accepted_project_output_count') or 0)}",
        f"- Distinct projects: {int(payload.get('distinct_project_count') or 0)}",
        f"- External project outputs: {int(payload.get('accepted_external_project_output_count') or 0)}",
        f"- User-facing outputs: {int(payload.get('accepted_user_facing_output_count') or 0)}",
        f"- Pending candidates: {int(payload.get('pending_candidate_count') or 0)}",
        f"- Pending hybrid acceptance: {int(payload.get('pending_hybrid_acceptance_count') or 0)}",
        f"- Stage met: `{str(bool(stage_status.get('met'))).lower()}`",
        "",
        "## Latest Accepted",
        "",
    ]
    if latest:
        lines.extend(
            [
                f"- Project: `{latest.get('project_id')}`",
                f"- Packet: `{latest.get('packet_id')}`",
                f"- Deliverable kind: `{latest.get('deliverable_kind')}`",
                f"- Deliverable refs: `{list(latest.get('deliverable_refs') or [])}`",
            ]
        )
    else:
        lines.append("- No accepted project outputs recorded yet.")

    lines.extend(["", "## Accepted Entries", ""])
    if payload.get("accepted_entries"):
        for entry in list(payload.get("accepted_entries") or [])[:6]:
            lines.append(
                f"- `{entry.get('project_id')}` / `{entry.get('packet_id')}` / `{entry.get('deliverable_kind')}` / refs={list(entry.get('deliverable_refs') or [])}"
            )
    else:
        lines.append("- No accepted project outputs yet.")

    lines.extend(["", "## Pending Candidates", ""])
    latest_pending = dict(payload.get("latest_pending_candidate") or {})
    if latest_pending:
        lines.extend(
            [
                f"- Latest pending project: `{latest_pending.get('project_id')}`",
                f"- Candidate: `{latest_pending.get('candidate_id')}`",
                f"- Deliverable kind: `{latest_pending.get('deliverable_kind')}`",
            ]
        )
    else:
        lines.append("- No pending project-output candidates.")

    lines.extend(["", "## Recent Disqualifications", ""])
    if payload.get("disqualified_entries"):
        for entry in list(payload.get("disqualified_entries") or [])[:6]:
            lines.append(
                f"- `{entry.get('project_id')}` / `{entry.get('packet_id')}`: `{entry.get('disqualification_reason')}`"
            )
    else:
        lines.append("- No project-output disqualifications recorded.")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor project-output proof ledger.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when generated outputs are stale.")
    args = parser.parse_args()

    payload = build_payload(
        contract_registry=_load_optional_json(CONTRACT_REGISTRY_PATH),
        autonomous_value_proof=_load_optional_json(AUTONOMOUS_VALUE_PROOF_PATH),
        project_output_candidates=_load_optional_json(PROJECT_OUTPUT_CANDIDATES_PATH),
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
