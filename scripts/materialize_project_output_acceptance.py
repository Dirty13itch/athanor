#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"
CANDIDATE_DIR = REPO_ROOT / "reports" / "truth-inventory" / "project-output-candidates"
ACCEPTANCE_OUTPUT_DIR = REPO_ROOT / "reports" / "truth-inventory" / "project-output-acceptance"
DEFAULT_AGENT_SERVER_URL = "http://192.168.1.244:9000"

if str(AGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(AGENTS_SRC))

try:
    from runtime_env import load_optional_runtime_env
except Exception:  # pragma: no cover - defensive import path
    load_optional_runtime_env = None

try:
    from athanor_agents.operator_state import upsert_backlog_record
except Exception:  # pragma: no cover - defensive import path
    upsert_backlog_record = None

if load_optional_runtime_env is not None:
    load_optional_runtime_env(env_names=["ATHANOR_AGENT_API_TOKEN", "ATHANOR_POSTGRES_URL"])


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _load_candidate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"candidate payload is not an object: {path}")
    return payload


def _write_candidate(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _request_agent_json(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, json.loads(raw) if raw else {"error": raw[:240]}
    except URLError as exc:
        return 599, {"error": str(exc.reason)}


def _acceptance_artifact_path(candidate_id: str) -> Path:
    return ACCEPTANCE_OUTPUT_DIR / f"{candidate_id}.json"


def _relative_to_repo(path: Path) -> str:
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    if resolved.is_relative_to(repo_root):
        return resolved.relative_to(repo_root).as_posix()
    return resolved.as_posix()


def _build_acceptance_artifact(
    candidate: dict[str, Any],
    *,
    accepted: bool,
    accepted_at: str | None,
    accepted_by: str | None,
) -> dict[str, Any]:
    return {
        "generated_at": _iso_now(),
        "candidate_id": _text(candidate.get("candidate_id")),
        "project_id": _text(candidate.get("project_id")),
        "title": _text(candidate.get("title")),
        "deliverable_kind": _text(candidate.get("deliverable_kind")),
        "deliverable_refs": _string_list(candidate.get("deliverable_refs")),
        "beneficiary_surface": _text(candidate.get("beneficiary_surface")) or _text(candidate.get("project_id")),
        "approval_posture": _text(candidate.get("approval_posture")) or "hybrid",
        "acceptance_mode": "automated" if accepted else "hybrid",
        "accepted": accepted,
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
    }


def _write_acceptance_artifact(
    candidate: dict[str, Any],
    *,
    accepted: bool,
    accepted_at: str | None,
    accepted_by: str | None,
) -> str:
    candidate_id = _text(candidate.get("candidate_id"))
    path = _acceptance_artifact_path(candidate_id)
    payload = _build_acceptance_artifact(
        candidate,
        accepted=accepted,
        accepted_at=accepted_at,
        accepted_by=accepted_by,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _relative_to_repo(path)


def _find_backlog_by_source_ref(rows: list[dict[str, Any]], source_ref: str) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_updated = float("-inf")
    for row in rows:
        metadata = dict(row.get("metadata") or {})
        row_source_ref = _text(row.get("source_ref") or metadata.get("source_ref"))
        if row_source_ref == source_ref:
            updated = float(row.get("updated_at") or row.get("completed_at") or row.get("created_at") or 0.0)
            if best_match is None or updated >= best_updated:
                best_match = row
                best_updated = updated
    return best_match


def _existing_review_backlog(rows: list[dict[str, Any]], candidate_id: str) -> dict[str, Any] | None:
    return _find_backlog_by_source_ref(rows, f"project-output-candidate:{candidate_id}")


def _backlog_timestamp(row: dict[str, Any]) -> float:
    try:
        return float(row.get("updated_at") or row.get("completed_at") or row.get("created_at") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _matches_accepted_candidate(row: dict[str, Any], candidate_id: str) -> bool:
    metadata = dict(row.get("metadata") or {})
    source_ref = _text(row.get("source_ref") or metadata.get("source_ref"))
    if source_ref == f"project-output-accepted:{candidate_id}":
        return True
    if _text(row.get("work_class")) != "project_output":
        return False
    if _text(metadata.get("candidate_id")) != candidate_id:
        return False
    return True


def _accepted_backlog_rows(rows: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    matches = [dict(row) for row in rows if _matches_accepted_candidate(row, candidate_id)]
    matches.sort(key=_backlog_timestamp, reverse=True)
    return matches


def _canonical_accepted_backlog(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    machine_ready = [row for row in rows if _accepted_backlog_machine_ready(row)]
    candidates = machine_ready or rows
    if not candidates:
        return None
    return max(candidates, key=_backlog_timestamp)


def _hybrid_review_backlog_create_payload(candidate: dict[str, Any], *, acceptance_ref: str) -> dict[str, Any]:
    candidate_id = _text(candidate.get("candidate_id"))
    title = _text(candidate.get("title")) or candidate_id
    project_id = _text(candidate.get("project_id")) or "unscoped"
    deliverable_kind = _text(candidate.get("deliverable_kind")) or "project_output"
    deliverable_refs = _string_list(candidate.get("deliverable_refs"))
    beneficiary_surface = _text(candidate.get("beneficiary_surface")) or project_id
    routing_class = _text(candidate.get("routing_class")) or "private_but_cloud_allowed"
    owner_agent = _text(candidate.get("owner_agent")) or "coding-agent"
    return {
        "actor": "codex",
        "session_id": "codex-project-output-review",
        "correlation_id": uuid.uuid4().hex,
        "reason": f"Materialized reviewable project-output candidate for {candidate_id}",
        "title": f"Review project output: {title}",
        "prompt": (
            f"Review candidate {candidate_id} for project {project_id}. "
            f"Deliverable kind: {deliverable_kind}. "
            f"Refs: {', '.join(deliverable_refs) or 'none recorded'}. "
            "Accept if the deliverable is real, useful, and matches the project-output contract."
        ),
        "owner_agent": owner_agent,
        "scope_type": "project",
        "scope_id": project_id,
        "work_class": "project_output_review",
        "priority": 2,
        "approval_mode": "operator",
        "dispatch_policy": "manual_only",
        "family": "project_factory",
        "project_id": project_id,
        "source_type": "project_output_acceptance",
        "source_ref": f"project-output-candidate:{candidate_id}",
        "routing_class": routing_class,
        "verification_contract": "evidence_bundle",
        "closure_rule": "operator_review_required",
        "materialization_source": "project_output_acceptance",
        "materialization_reason": "Hybrid project-output candidate staged for operator review.",
        "result_id": candidate_id,
        "review_id": f"project-output-review:{candidate_id}",
        "metadata": {
            "candidate_id": candidate_id,
            "project_id": project_id,
            "source_type": "project_output_acceptance",
            "source_ref": f"project-output-candidate:{candidate_id}",
            "routing_class": routing_class,
            "verification_contract": "evidence_bundle",
            "closure_rule": "operator_review_required",
            "materialization_source": "project_output_acceptance",
            "materialization_reason": "Hybrid project-output candidate staged for operator review.",
            "result_id": candidate_id,
            "review_id": f"project-output-review:{candidate_id}",
            "deliverable_kind": deliverable_kind,
            "deliverable_refs": deliverable_refs,
            "beneficiary_surface": beneficiary_surface,
            "approval_posture": "hybrid",
            "acceptance_mode": "hybrid",
            "acceptance_proof_refs": [acceptance_ref],
            "verification_status": _text(candidate.get("verification_status")) or "passed",
            "operator_steered": True,
        },
    }


def _accepted_backlog_create_payload(
    candidate: dict[str, Any],
    *,
    accepted_at: str,
    accepted_by: str,
    acceptance_ref: str,
    review_backlog_id: str | None,
) -> dict[str, Any]:
    candidate_id = _text(candidate.get("candidate_id"))
    title = _text(candidate.get("title")) or candidate_id
    project_id = _text(candidate.get("project_id")) or "unscoped"
    deliverable_kind = _text(candidate.get("deliverable_kind")) or "project_output"
    deliverable_refs = _string_list(candidate.get("deliverable_refs"))
    beneficiary_surface = _text(candidate.get("beneficiary_surface")) or project_id
    routing_class = _text(candidate.get("routing_class")) or "private_but_cloud_allowed"
    owner_agent = _text(candidate.get("owner_agent")) or "coding-agent"
    metadata: dict[str, Any] = {
        "candidate_id": candidate_id,
        "project_id": project_id,
        "source_type": "project_output_acceptance",
        "source_ref": f"project-output-accepted:{candidate_id}",
        "routing_class": routing_class,
        "verification_contract": "evidence_bundle",
        "closure_rule": "operator_review_required",
        "materialization_source": "project_output_acceptance",
        "materialization_reason": "Hybrid project-output acceptance materialized from operator approval.",
        "result_id": candidate_id,
        "review_id": f"project-output-review:{candidate_id}",
        "verification_status": _text(candidate.get("verification_status")) or "passed",
        "value_class": "product_value",
        "deliverable_kind": deliverable_kind,
        "deliverable_refs": deliverable_refs,
        "beneficiary_surface": beneficiary_surface,
        "acceptance_mode": "hybrid",
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
        "acceptance_proof_refs": [acceptance_ref],
        "operator_steered": False,
    }
    if review_backlog_id:
        metadata["review_backlog_id"] = review_backlog_id
    return {
        "actor": "codex",
        "session_id": "codex-project-output-acceptance",
        "correlation_id": uuid.uuid4().hex,
        "reason": f"Materialized hybrid project-output acceptance for {candidate_id}",
        "title": f"Accepted project output: {title}",
        "prompt": f"Persist accepted project output for {title}.",
        "owner_agent": owner_agent,
        "scope_type": "project",
        "scope_id": project_id,
        "work_class": "project_output",
        "priority": 2,
        "approval_mode": "none",
        "dispatch_policy": "planner_eligible",
        "family": "project_factory",
        "project_id": project_id,
        "source_type": "project_output_acceptance",
        "source_ref": f"project-output-accepted:{candidate_id}",
        "routing_class": routing_class,
        "verification_contract": "evidence_bundle",
        "closure_rule": "operator_review_required",
        "materialization_source": "project_output_acceptance",
        "materialization_reason": "Hybrid project-output acceptance materialized from operator approval.",
        "result_id": candidate_id,
        "review_id": f"project-output-review:{candidate_id}",
        "value_class": "product_value",
        "deliverable_kind": deliverable_kind,
        "deliverable_refs": deliverable_refs,
        "beneficiary_surface": beneficiary_surface,
        "acceptance_mode": "hybrid",
        "accepted_by": accepted_by,
        "accepted_at": accepted_at,
        "acceptance_proof_refs": [acceptance_ref],
        "operator_steered": False,
        "metadata": metadata,
    }


def _transition_backlog(
    *,
    base_url: str,
    token: str,
    backlog_id: str,
    candidate_id: str,
    status: str,
    note: str,
    reason: str,
) -> tuple[int, dict[str, Any]]:
    return _request_agent_json(
        base_url,
        token,
        f"/v1/operator/backlog/{backlog_id}/transition",
        method="POST",
        payload={
            "actor": "codex",
            "session_id": "codex-project-output-acceptance",
            "correlation_id": uuid.uuid4().hex,
            "reason": reason or f"Transition project-output backlog for {candidate_id}",
            "status": status,
            "note": note,
        },
        timeout=20,
    )


def _accepted_backlog_fields(row: dict[str, Any], *, default_accepted_by: str) -> tuple[str, str]:
    metadata = dict(row.get("metadata") or {})
    accepted_by = _text(row.get("accepted_by") or metadata.get("accepted_by")) or default_accepted_by
    accepted_at = _text(row.get("accepted_at") or metadata.get("accepted_at")) or _iso_now()
    return accepted_by, accepted_at


def _accepted_backlog_machine_ready(row: dict[str, Any]) -> bool:
    metadata = dict(row.get("metadata") or {})
    return all(
        _text(row.get(field) or metadata.get(field))
        for field in ("project_id", "result_id", "source_ref")
    )


def _upsert_backlog_record_direct(record: dict[str, Any]) -> bool:
    if upsert_backlog_record is None:
        raise RuntimeError("direct backlog upsert unavailable")
    if load_optional_runtime_env is not None:
        load_optional_runtime_env(env_names=["ATHANOR_POSTGRES_URL"])
    return bool(asyncio.run(upsert_backlog_record(record)))


def _repair_existing_accepted_backlog(
    row: dict[str, Any],
    *,
    candidate: dict[str, Any],
    accepted_by: str,
    accepted_at: str,
    acceptance_ref: str,
    review_backlog_id: str | None,
) -> str | None:
    backlog_id = _text(row.get("id") or row.get("backlog_id"))
    if not backlog_id:
        return None
    repair_payload = _accepted_backlog_create_payload(
        candidate,
        accepted_at=accepted_at,
        accepted_by=accepted_by,
        acceptance_ref=acceptance_ref,
        review_backlog_id=review_backlog_id,
    )
    repaired = dict(row)
    repaired["id"] = backlog_id
    for field in (
        "title",
        "prompt",
        "owner_agent",
        "scope_type",
        "scope_id",
        "work_class",
        "priority",
        "approval_mode",
        "dispatch_policy",
        "family",
        "project_id",
        "source_type",
        "source_ref",
        "routing_class",
        "verification_contract",
        "closure_rule",
        "materialization_source",
        "materialization_reason",
        "result_id",
        "review_id",
        "value_class",
        "deliverable_kind",
        "deliverable_refs",
        "beneficiary_surface",
        "acceptance_mode",
        "accepted_by",
        "accepted_at",
        "acceptance_proof_refs",
        "operator_steered",
    ):
        repaired[field] = repair_payload[field]
    metadata = dict(row.get("metadata") or {})
    metadata.update(dict(repair_payload.get("metadata") or {}))
    repaired["metadata"] = metadata
    repaired["status"] = "completed"
    repaired["blocking_reason"] = ""
    now_ts = time.time()
    repaired["created_at"] = float(row.get("created_at") or now_ts)
    repaired["updated_at"] = now_ts
    repaired["completed_at"] = float(row.get("completed_at") or now_ts)
    repaired["ready_at"] = float(row.get("ready_at") or 0.0)
    repaired["scheduled_for"] = float(row.get("scheduled_for") or 0.0)
    repaired["support_agents"] = list(row.get("support_agents") or [])
    repaired["preconditions"] = list(row.get("preconditions") or [])
    repaired["linked_goal_ids"] = list(row.get("linked_goal_ids") or [])
    repaired["linked_todo_ids"] = list(row.get("linked_todo_ids") or [])
    repaired["linked_idea_id"] = _text(row.get("linked_idea_id"))
    repaired["created_by"] = _text(row.get("created_by") or repair_payload.get("actor") or "codex")
    repaired["origin"] = _text(row.get("origin") or "operator")
    if not _upsert_backlog_record_direct(repaired):
        return None
    return backlog_id


def _archive_duplicate_accepted_backlogs(
    rows: list[dict[str, Any]],
    *,
    canonical_backlog_id: str,
    base_url: str,
    token: str,
    candidate_id: str,
) -> list[str]:
    archived_ids: list[str] = []
    for row in rows:
        backlog_id = _text(row.get("id") or row.get("backlog_id"))
        if not backlog_id or backlog_id == canonical_backlog_id:
            continue
        if _text(row.get("status")).lower() == "archived":
            archived_ids.append(backlog_id)
            continue
        status, _body = _transition_backlog(
            base_url=base_url,
            token=token,
            backlog_id=backlog_id,
            candidate_id=candidate_id,
            status="archived",
            note=f"Archived duplicate accepted project-output backlog in favor of {canonical_backlog_id}.",
            reason=f"Archive duplicate accepted project-output backlog for {candidate_id}",
        )
        if status == 200:
            archived_ids.append(backlog_id)
    return archived_ids


def _sync_candidate_as_accepted(
    *,
    candidate: dict[str, Any],
    candidate_path: Path,
    accepted_backlog_id: str,
    review_backlog_id: str | None,
    accepted_by: str,
    accepted_at: str,
) -> tuple[str, dict[str, Any]]:
    acceptance_ref = _write_acceptance_artifact(
        candidate,
        accepted=True,
        accepted_at=accepted_at,
        accepted_by=accepted_by,
    )
    candidate["acceptance_state"] = "accepted"
    candidate["accepted_by"] = accepted_by
    candidate["accepted_at"] = accepted_at
    candidate["acceptance_backlog_id"] = accepted_backlog_id or None
    if review_backlog_id:
        candidate["acceptance_review_backlog_id"] = review_backlog_id
    candidate["acceptance_proof_refs"] = [acceptance_ref]
    _write_candidate(candidate_path, candidate)
    return acceptance_ref, candidate


def materialize_candidate_acceptance(
    candidate_path: Path,
    *,
    base_url: str | None = None,
    token: str | None = None,
    approve_hybrid: bool = False,
    accepted_by: str = "Shaun",
) -> dict[str, Any]:
    candidate = _load_candidate(candidate_path)
    candidate_id = _text(candidate.get("candidate_id"))
    approval_posture = _text(candidate.get("approval_posture")) or "hybrid"
    acceptance_state = _text(candidate.get("acceptance_state")) or "pending_materialization"
    if not candidate_id:
        raise ValueError(f"candidate_id missing in {candidate_path}")
    if acceptance_state == "accepted" and not approve_hybrid and approval_posture != "hybrid":
        return {
            "candidate_id": candidate_id,
            "status": "already_completed",
            "candidate_path": str(candidate_path),
        }
    effective_base_url = (base_url or os.environ.get("ATHANOR_AGENT_SERVER_URL") or DEFAULT_AGENT_SERVER_URL).rstrip("/")
    effective_token = token or os.environ.get("ATHANOR_AGENT_API_TOKEN") or ""
    if approval_posture == "hybrid":
        backlog_status, backlog_body = _request_agent_json(
            effective_base_url,
            effective_token,
            "/v1/operator/backlog?limit=200",
            method="GET",
            timeout=20,
        )
        if backlog_status != 200:
            return {
                "candidate_id": candidate_id,
                "status": "query_failed",
                "candidate_path": str(candidate_path),
                "error": backlog_body.get("error"),
            }
        rows = list(backlog_body.get("backlog") or [])
        existing_review = _existing_review_backlog(rows, candidate_id)
        accepted_rows = _accepted_backlog_rows(rows, candidate_id)
        existing_accepted = _canonical_accepted_backlog(accepted_rows)
        review_backlog_id = _text(dict(existing_review or {}).get("id"))
        if existing_accepted is not None and _accepted_backlog_machine_ready(existing_accepted):
            accepted_backlog_id = _text(dict(existing_accepted).get("id"))
            accepted_by_value, accepted_at_value = _accepted_backlog_fields(
                dict(existing_accepted),
                default_accepted_by=accepted_by,
            )
            acceptance_ref, _ = _sync_candidate_as_accepted(
                candidate=candidate,
                candidate_path=candidate_path,
                accepted_backlog_id=accepted_backlog_id,
                review_backlog_id=review_backlog_id or None,
                accepted_by=accepted_by_value,
                accepted_at=accepted_at_value,
            )
            archived_duplicate_ids = _archive_duplicate_accepted_backlogs(
                accepted_rows,
                canonical_backlog_id=accepted_backlog_id,
                base_url=effective_base_url,
                token=effective_token,
                candidate_id=candidate_id,
            )
            return {
                "candidate_id": candidate_id,
                "status": "already_completed",
                "candidate_path": str(candidate_path),
                "acceptance_artifact": acceptance_ref,
                "acceptance_backlog_id": accepted_backlog_id or None,
                "acceptance_review_backlog_id": review_backlog_id or None,
                "archived_duplicate_backlog_ids": archived_duplicate_ids,
            }
        if approve_hybrid:
            if existing_review is None:
                return {
                    "candidate_id": candidate_id,
                    "status": "approval_missing_review",
                    "candidate_path": str(candidate_path),
                    "error": "Hybrid approval requires an existing review backlog item.",
                }
            accepted_at = _iso_now()
            acceptance_ref = _write_acceptance_artifact(
                candidate,
                accepted=True,
                accepted_at=accepted_at,
                accepted_by=accepted_by,
            )
            if existing_accepted is not None:
                accepted_backlog_id = _repair_existing_accepted_backlog(
                    dict(existing_accepted),
                    candidate=candidate,
                    accepted_by=accepted_by,
                    accepted_at=accepted_at,
                    acceptance_ref=acceptance_ref,
                    review_backlog_id=review_backlog_id or None,
                )
                if not accepted_backlog_id:
                    return {
                        "candidate_id": candidate_id,
                        "status": "repair_failed",
                        "candidate_path": str(candidate_path),
                        "acceptance_artifact": acceptance_ref,
                        "acceptance_review_backlog_id": review_backlog_id or None,
                        "error": "existing accepted backlog repair failed",
                    }
                if review_backlog_id:
                    _transition_backlog(
                        base_url=effective_base_url,
                        token=effective_token,
                        backlog_id=review_backlog_id,
                        candidate_id=candidate_id,
                        status="archived",
                        note=f"Hybrid project-output review superseded by accepted backlog {accepted_backlog_id}.",
                        reason=f"Archive superseded project-output review for {candidate_id}",
                    )
                _sync_candidate_as_accepted(
                    candidate=candidate,
                    candidate_path=candidate_path,
                    accepted_backlog_id=accepted_backlog_id,
                    review_backlog_id=review_backlog_id or None,
                    accepted_by=accepted_by,
                    accepted_at=accepted_at,
                )
                archived_duplicate_ids = _archive_duplicate_accepted_backlogs(
                    accepted_rows,
                    canonical_backlog_id=accepted_backlog_id,
                    base_url=effective_base_url,
                    token=effective_token,
                    candidate_id=candidate_id,
                )
                return {
                    "candidate_id": candidate_id,
                    "status": "completed",
                    "candidate_path": str(candidate_path),
                    "acceptance_artifact": acceptance_ref,
                    "acceptance_backlog_id": accepted_backlog_id,
                    "acceptance_review_backlog_id": review_backlog_id or None,
                    "archived_duplicate_backlog_ids": archived_duplicate_ids,
                }
            create_status, create_body = _request_agent_json(
                effective_base_url,
                effective_token,
                "/v1/operator/backlog",
                method="POST",
                payload=_accepted_backlog_create_payload(
                    candidate,
                    accepted_at=accepted_at,
                    accepted_by=accepted_by,
                    acceptance_ref=acceptance_ref,
                    review_backlog_id=review_backlog_id or None,
                ),
                timeout=20,
            )
            if create_status != 200:
                return {
                    "candidate_id": candidate_id,
                    "status": "create_failed",
                    "candidate_path": str(candidate_path),
                    "acceptance_artifact": acceptance_ref,
                    "acceptance_review_backlog_id": review_backlog_id or None,
                    "error": create_body.get("error"),
                }
            accepted_backlog_id = _text(dict(create_body.get("backlog") or {}).get("id"))
            transition_status, transition_body = _transition_backlog(
                base_url=effective_base_url,
                token=effective_token,
                backlog_id=accepted_backlog_id,
                candidate_id=candidate_id,
                status="completed",
                note="Hybrid project-output acceptance materialized from operator approval.",
                reason=f"Finalize hybrid project-output acceptance for {candidate_id}",
            )
            if transition_status != 200:
                candidate["acceptance_state"] = "materialization_failed"
                candidate["acceptance_proof_refs"] = [acceptance_ref]
                _write_candidate(candidate_path, candidate)
                return {
                    "candidate_id": candidate_id,
                    "status": "transition_failed",
                    "candidate_path": str(candidate_path),
                    "acceptance_artifact": acceptance_ref,
                    "acceptance_backlog_id": accepted_backlog_id,
                    "acceptance_review_backlog_id": review_backlog_id or None,
                    "error": transition_body.get("error"),
                }
            if review_backlog_id:
                _transition_backlog(
                    base_url=effective_base_url,
                    token=effective_token,
                    backlog_id=review_backlog_id,
                    candidate_id=candidate_id,
                    status="archived",
                    note=f"Hybrid project-output review superseded by accepted backlog {accepted_backlog_id}.",
                    reason=f"Archive superseded project-output review for {candidate_id}",
                )
            _sync_candidate_as_accepted(
                candidate=candidate,
                candidate_path=candidate_path,
                accepted_backlog_id=accepted_backlog_id,
                review_backlog_id=review_backlog_id or None,
                accepted_by=accepted_by,
                accepted_at=accepted_at,
            )
            return {
                "candidate_id": candidate_id,
                "status": "completed",
                "candidate_path": str(candidate_path),
                "acceptance_artifact": acceptance_ref,
                "acceptance_backlog_id": accepted_backlog_id,
                "acceptance_review_backlog_id": review_backlog_id or None,
            }
        acceptance_ref = _write_acceptance_artifact(candidate, accepted=False, accepted_at=None, accepted_by=None)
        if existing_review is None:
            create_status, create_body = _request_agent_json(
                effective_base_url,
                effective_token,
                "/v1/operator/backlog",
                method="POST",
                payload=_hybrid_review_backlog_create_payload(candidate, acceptance_ref=acceptance_ref),
                timeout=20,
            )
            if create_status != 200:
                return {
                    "candidate_id": candidate_id,
                    "status": "create_failed",
                    "candidate_path": str(candidate_path),
                    "acceptance_artifact": acceptance_ref,
                    "error": create_body.get("error"),
                }
            review_backlog_id = _text(dict(create_body.get("backlog") or {}).get("id"))
        candidate["acceptance_state"] = "pending_acceptance"
        candidate["accepted_by"] = None
        candidate["accepted_at"] = None
        candidate["acceptance_backlog_id"] = review_backlog_id or None
        candidate["acceptance_proof_refs"] = [acceptance_ref]
        _write_candidate(candidate_path, candidate)
        return {
            "candidate_id": candidate_id,
            "status": "pending_approval",
            "candidate_path": str(candidate_path),
            "acceptance_artifact": acceptance_ref,
            "acceptance_backlog_id": review_backlog_id or None,
        }

    accepted_at = _iso_now()
    acceptance_ref = _write_acceptance_artifact(candidate, accepted=True, accepted_at=accepted_at, accepted_by="system")
    create_status, create_body = _request_agent_json(
        effective_base_url,
        effective_token,
        "/v1/operator/backlog",
        method="POST",
        payload=_accepted_backlog_create_payload(
            candidate,
            accepted_at=accepted_at,
            accepted_by="system",
            acceptance_ref=acceptance_ref,
            review_backlog_id=None,
        ),
        timeout=20,
    )
    if create_status != 200:
        candidate["acceptance_state"] = "materialization_failed"
        candidate["acceptance_proof_refs"] = [acceptance_ref]
        _write_candidate(candidate_path, candidate)
        return {
            "candidate_id": candidate_id,
            "status": "create_failed",
            "candidate_path": str(candidate_path),
            "acceptance_artifact": acceptance_ref,
            "error": create_body.get("error"),
        }

    backlog_id = _text(dict(create_body.get("backlog") or {}).get("id"))
    transition_status, transition_body = _transition_backlog(
        base_url=effective_base_url,
        token=effective_token,
        backlog_id=backlog_id,
        candidate_id=candidate_id,
        status="completed",
        note="Automated project-output acceptance materialized from a verified candidate.",
        reason=f"Finalize project-output acceptance for {candidate_id}",
    )
    if transition_status != 200:
        candidate["acceptance_state"] = "materialization_failed"
        candidate["acceptance_proof_refs"] = [acceptance_ref]
        _write_candidate(candidate_path, candidate)
        return {
            "candidate_id": candidate_id,
            "status": "transition_failed",
            "candidate_path": str(candidate_path),
            "acceptance_artifact": acceptance_ref,
            "acceptance_backlog_id": backlog_id,
            "error": transition_body.get("error"),
        }

    candidate["acceptance_state"] = "accepted"
    candidate["accepted_by"] = "system"
    candidate["accepted_at"] = accepted_at
    candidate["acceptance_backlog_id"] = backlog_id or None
    candidate["acceptance_proof_refs"] = [acceptance_ref]
    _write_candidate(candidate_path, candidate)
    return {
        "candidate_id": candidate_id,
        "status": "completed",
        "candidate_path": str(candidate_path),
        "acceptance_artifact": acceptance_ref,
        "acceptance_backlog_id": backlog_id,
    }


def _candidate_paths_from_dir() -> list[Path]:
    if not CANDIDATE_DIR.exists():
        return []
    return sorted(CANDIDATE_DIR.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize project-output acceptance artifacts.")
    parser.add_argument("--candidate-path", action="append", default=[], help="Repeatable candidate artifact path.")
    parser.add_argument("--all-pending", action="store_true", help="Materialize all pending project-output candidates.")
    parser.add_argument("--approve-hybrid", action="store_true", help="Finalize hybrid candidates as accepted outputs.")
    parser.add_argument("--accepted-by", default="Shaun", help="Accepted-by value for finalized hybrid candidates.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    candidate_paths = [Path(item) for item in args.candidate_path]
    if args.all_pending:
        candidate_paths.extend(_candidate_paths_from_dir())
    if not candidate_paths:
        raise SystemExit("--candidate-path or --all-pending is required")

    seen: set[Path] = set()
    ordered_paths: list[Path] = []
    for path in candidate_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered_paths.append(resolved)

    results = [
        materialize_candidate_acceptance(
            path,
            approve_hybrid=bool(args.approve_hybrid),
            accepted_by=_text(args.accepted_by) or "Shaun",
        )
        for path in ordered_paths
    ]
    payload = {
        "generated_at": _iso_now(),
        "result_count": len(results),
        "results": results,
    }
    print(json.dumps(payload, indent=2))
    return 0 if all(
        result.get("status")
        in {
            "completed",
            "pending_approval",
            "already_pending",
            "already_completed",
        }
        for result in results
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
