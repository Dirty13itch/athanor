#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "project-output-contract-registry.json"
CANDIDATE_DIR = REPO_ROOT / "reports" / "truth-inventory" / "project-output-candidates"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-candidates.json"
STATUS_MD_PATH = REPO_ROOT / "docs" / "operations" / "PROJECT-OUTPUT-CANDIDATES.md"


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


def _load_candidate_records() -> list[dict[str, Any]]:
    if not CANDIDATE_DIR.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(CANDIDATE_DIR.glob("*.json")):
        payload = _load_optional_json(path)
        if not payload:
            continue
        payload["candidate_artifact_ref"] = path.relative_to(REPO_ROOT).as_posix()
        records.append(payload)
    return records


def build_payload(
    *,
    contract_registry: dict[str, Any],
    candidate_records: list[dict[str, Any]],
) -> dict[str, Any]:
    projects_by_id, alias_to_project_id = _build_alias_map(contract_registry)
    normalized_candidates: list[dict[str, Any]] = []
    project_summaries: dict[str, dict[str, Any]] = {
        project_id: {
            "label": _text(project.get("label")) or project_id,
            "candidate_count": 0,
            "pending_candidate_count": 0,
            "accepted_candidate_count": 0,
        }
        for project_id, project in projects_by_id.items()
    }

    for raw in candidate_records:
        project_id = _text(raw.get("project_id"))
        canonical_project_id = alias_to_project_id.get(project_id, project_id or "unscoped")
        acceptance_state = _text(raw.get("acceptance_state")) or "pending_materialization"
        record = {
            **raw,
            "project_id": canonical_project_id,
            "source_project_id": project_id or canonical_project_id,
            "candidate_id": _text(raw.get("candidate_id")) or canonical_project_id,
            "approval_posture": _text(raw.get("approval_posture")) or "hybrid",
            "acceptance_state": acceptance_state,
            "deliverable_refs": _string_list(raw.get("deliverable_refs")),
            "workflow_refs": _string_list(raw.get("workflow_refs")),
            "verification_refs": _string_list(raw.get("verification_refs")),
            "acceptance_proof_refs": _string_list(raw.get("acceptance_proof_refs")),
            "title": _text(raw.get("title")) or canonical_project_id,
        }
        normalized_candidates.append(record)
        project_summaries.setdefault(
            canonical_project_id,
            {
                "label": canonical_project_id,
                "candidate_count": 0,
                "pending_candidate_count": 0,
                "accepted_candidate_count": 0,
            },
        )
        project_summaries[canonical_project_id]["candidate_count"] += 1
        if acceptance_state == "accepted":
            project_summaries[canonical_project_id]["accepted_candidate_count"] += 1
        else:
            project_summaries[canonical_project_id]["pending_candidate_count"] += 1

    normalized_candidates.sort(
        key=lambda item: (
            _text(item.get("generated_at")),
            _text(item.get("candidate_id")),
        )
    )
    pending_candidates = [item for item in normalized_candidates if _text(item.get("acceptance_state")) != "accepted"]
    pending_hybrid_candidates = [
        item
        for item in pending_candidates
        if _text(item.get("approval_posture")) == "hybrid"
    ]
    accepted_candidates = [item for item in normalized_candidates if _text(item.get("acceptance_state")) == "accepted"]

    return {
        "generated_at": _iso_now(),
        "candidate_count": len(normalized_candidates),
        "pending_candidate_count": len(pending_candidates),
        "pending_hybrid_acceptance_count": len(pending_hybrid_candidates),
        "accepted_candidate_count": len(accepted_candidates),
        "latest_candidate": normalized_candidates[-1] if normalized_candidates else None,
        "latest_pending_candidate": pending_candidates[-1] if pending_candidates else None,
        "candidates": normalized_candidates,
        "project_summaries": project_summaries,
        "source_artifacts": {
            "project_output_contract_registry": str(CONTRACT_REGISTRY_PATH),
            "project_output_candidate_dir": str(CANDIDATE_DIR),
            "project_output_candidates": str(OUTPUT_PATH),
            "project_output_candidates_status": str(STATUS_MD_PATH),
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    latest_pending = dict(payload.get("latest_pending_candidate") or {})
    lines = [
        "# Project Output Candidates",
        "",
        f"- Generated at: {payload.get('generated_at')}",
        f"- Candidate count: {int(payload.get('candidate_count') or 0)}",
        f"- Pending candidates: {int(payload.get('pending_candidate_count') or 0)}",
        f"- Pending hybrid acceptance: {int(payload.get('pending_hybrid_acceptance_count') or 0)}",
        f"- Accepted candidates: {int(payload.get('accepted_candidate_count') or 0)}",
        "",
        "## Latest Pending Candidate",
        "",
    ]
    if latest_pending:
        lines.extend(
            [
                f"- Candidate: `{latest_pending.get('candidate_id')}`",
                f"- Project: `{latest_pending.get('project_id')}`",
                f"- Deliverable kind: `{latest_pending.get('deliverable_kind')}`",
                f"- Acceptance state: `{latest_pending.get('acceptance_state')}`",
            ]
        )
    else:
        lines.append("- No pending project-output candidates.")

    lines.extend(["", "## Candidate Summary", ""])
    if payload.get("candidates"):
        for record in list(payload.get("candidates") or [])[:8]:
            lines.append(
                f"- `{record.get('candidate_id')}` / `{record.get('project_id')}` / `{record.get('acceptance_state')}` / refs={list(record.get('deliverable_refs') or [])}"
            )
    else:
        lines.append("- No project-output candidates recorded.")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the project-output candidate summary.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when project-output-candidates.json is stale.")
    args = parser.parse_args()

    payload = build_payload(
        contract_registry=_load_optional_json(CONTRACT_REGISTRY_PATH),
        candidate_records=_load_candidate_records(),
    )
    current_json = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    rendered_json, rendered_md = _render_against_existing(payload, current_json)
    if args.check:
        current_md = STATUS_MD_PATH.read_text(encoding="utf-8") if STATUS_MD_PATH.exists() else ""
        if current_json != rendered_json or current_md != rendered_md:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current_json != rendered_json:
        OUTPUT_PATH.write_text(rendered_json, encoding="utf-8")
    current_md = STATUS_MD_PATH.read_text(encoding="utf-8") if STATUS_MD_PATH.exists() else ""
    if current_md != rendered_md:
        STATUS_MD_PATH.write_text(rendered_md, encoding="utf-8")
    if args.json:
        print(json.dumps(json.loads(rendered_json), indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
