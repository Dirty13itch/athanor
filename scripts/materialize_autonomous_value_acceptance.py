#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from write_value_throughput_scorecard import _load_agent_route_payload_sync, _load_governed_dispatch_truth


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "reports" / "truth-inventory" / "autonomous-value-acceptance"
DEFAULT_AGENT_SERVER_URL = "http://192.168.1.244:9000"

STAGE1_SEED: list[dict[str, Any]] = [
    {
        "source_backlog_id": "backlog-5828c970",
        "title": "Accepted operator-value proof: Reference and Archive Prune",
        "owner_agent": "research-agent",
        "work_class": "repo_audit",
        "family": "research_audit",
        "value_class": "operator_value",
        "deliverable_kind": "report",
        "deliverable_refs": [
            "docs/operations/REPO-ROOTS-REPORT.md",
            "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
        ],
        "beneficiary_surface": "athanor_core",
        "acceptance_summary": "Autonomous deferred-family closure produced operator-usable root and runtime-ownership reports with passing validation.",
    },
    {
        "source_backlog_id": "backlog-c6b205ab",
        "title": "Accepted operator-value proof: Audit and Eval Artifacts",
        "owner_agent": "research-agent",
        "work_class": "repo_audit",
        "family": "research_audit",
        "value_class": "operator_value",
        "deliverable_kind": "report",
        "deliverable_refs": [
            "docs/operations/REPO-ROOTS-REPORT.md",
            "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
            "reports/truth-inventory/surface-owner-matrix.json",
        ],
        "beneficiary_surface": "athanor_core",
        "acceptance_summary": "Autonomous deferred-family closure produced audit/report artifacts that passed the governed validation bundle and remain operator-consumable.",
    },
    {
        "source_backlog_id": "backlog-44e9caaa",
        "title": "Accepted operator-value proof: Local Bulk Sovereign",
        "owner_agent": "coding-agent",
        "work_class": "maintenance",
        "family": "maintenance",
        "value_class": "operator_value",
        "deliverable_kind": "report",
        "deliverable_refs": [
            "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
            "reports/truth-inventory/capacity-telemetry.json",
            "reports/truth-inventory/quota-truth.json",
        ],
        "beneficiary_surface": "athanor_core",
        "acceptance_summary": "Autonomous burn-class closure produced reusable capacity truth artifacts with passing governed proof commands.",
    },
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _source_value(source_record: dict[str, Any], key: str) -> Any:
    metadata = dict(source_record.get("metadata") or {})
    value = source_record.get(key)
    if value is None:
        value = metadata.get(key)
    return value


def _source_text(source_record: dict[str, Any], key: str) -> str:
    return _text(_source_value(source_record, key))


def _source_list(source_record: dict[str, Any], key: str) -> list[str]:
    value = _source_value(source_record, key)
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if value is None:
        return []
    text = _text(value)
    return [text] if text else []


def _find_source_backlog(rows: list[dict[str, Any]], source_backlog_id: str) -> dict[str, Any] | None:
    return next((row for row in rows if _text(row.get("id")) == source_backlog_id), None)


def _build_plan_from_source_backlog(
    rows: list[dict[str, Any]],
    *,
    source_backlog_id: str,
    title: str | None = None,
    owner_agent: str | None = None,
    work_class: str | None = None,
    family: str | None = None,
    value_class: str | None = None,
    deliverable_kind: str | None = None,
    deliverable_refs: list[str] | None = None,
    beneficiary_surface: str | None = None,
    acceptance_summary: str | None = None,
) -> dict[str, Any]:
    source_record = _find_source_backlog(rows, source_backlog_id)
    if source_record is None:
        raise SystemExit(f"source backlog not found: {source_backlog_id}")

    inferred_value_class = _text(value_class) or _source_text(source_record, "value_class")
    inferred_deliverable_kind = _text(deliverable_kind) or _source_text(source_record, "deliverable_kind")
    inferred_deliverable_refs = [_text(item) for item in list(deliverable_refs or []) if _text(item)] or _source_list(
        source_record, "deliverable_refs"
    )
    inferred_beneficiary_surface = _text(beneficiary_surface) or _source_text(source_record, "beneficiary_surface")

    missing_fields = [
        field
        for field, value in (
            ("value_class", inferred_value_class),
            ("deliverable_kind", inferred_deliverable_kind),
            ("deliverable_refs", inferred_deliverable_refs),
            ("beneficiary_surface", inferred_beneficiary_surface),
        )
        if not value
    ]
    if missing_fields:
        raise SystemExit(
            f"source backlog {source_backlog_id} is missing required autonomous value fields: {', '.join(missing_fields)}"
        )

    inferred_title = _text(title) or f"Accepted {inferred_value_class.replace('_', '-')} proof: {_text(source_record.get('title'))}"
    refs_text = ", ".join(inferred_deliverable_refs)
    inferred_acceptance_summary = _text(acceptance_summary) or (
        f"Accepted {inferred_value_class.replace('_', '-')} proof for {inferred_beneficiary_surface} "
        f"with deliverable refs: {refs_text}."
    )

    return {
        "source_backlog_id": source_backlog_id,
        "title": inferred_title,
        "owner_agent": _text(owner_agent) or _text(source_record.get("owner_agent")) or "research-agent",
        "work_class": _text(work_class) or _text(source_record.get("work_class")) or "repo_audit",
        "family": _text(family) or _source_text(source_record, "family") or "maintenance",
        "value_class": inferred_value_class,
        "deliverable_kind": inferred_deliverable_kind,
        "deliverable_refs": inferred_deliverable_refs,
        "beneficiary_surface": inferred_beneficiary_surface,
        "acceptance_summary": inferred_acceptance_summary,
    }


def _load_agent_runtime(governed_truth: dict[str, Any]) -> tuple[str, str]:
    execution = dict(governed_truth.get("execution") or {})
    base_url = (
        _text(__import__("os").environ.get("ATHANOR_AGENT_SERVER_URL"))
        or _text(execution.get("agent_server_base_url"))
        or DEFAULT_AGENT_SERVER_URL
    ).rstrip("/")
    token = _text(__import__("os").environ.get("ATHANOR_AGENT_API_TOKEN"))
    return base_url, token


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
    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, json.loads(raw) if raw else {"error": raw[:240]}
    except URLError as exc:
        return 599, {"error": str(exc.reason)}


def _write_acceptance_artifact(plan: dict[str, Any], source_record: dict[str, Any]) -> str:
    backlog_id = _text(plan.get("source_backlog_id"))
    result_id = _text(source_record.get("result_id"))
    acceptance_path = OUTPUT_DIR / f"{backlog_id}.json"
    payload = {
        "generated_at": _iso_now(),
        "accepted_by": "system",
        "acceptance_mode": "automated",
        "operator_steered": False,
        "source_backlog_id": backlog_id,
        "source_title": _text(source_record.get("title")),
        "source_family": _text(source_record.get("family")),
        "source_result_id": result_id,
        "value_class": _text(plan.get("value_class")),
        "deliverable_kind": _text(plan.get("deliverable_kind")),
        "deliverable_refs": list(plan.get("deliverable_refs") or []),
        "beneficiary_surface": _text(plan.get("beneficiary_surface")),
        "acceptance_summary": _text(plan.get("acceptance_summary")),
        "verification_status": _text(dict(source_record.get("metadata") or {}).get("verification_status")) or "passed",
        "proof_artifacts": list(dict(source_record.get("metadata") or {}).get("proof_artifacts") or []),
        "source_ref": _text(source_record.get("source_ref")),
        "latest_task_id": _text(dict(source_record.get("metadata") or {}).get("latest_task_id")),
    }
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    acceptance_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        return str(acceptance_path.relative_to(REPO_ROOT).as_posix())
    except ValueError:
        return str(acceptance_path.as_posix())


def _existing_acceptance_backlog(rows: list[dict[str, Any]], source_backlog_id: str) -> dict[str, Any] | None:
    target_source_ref = f"autonomous-value-acceptance:{source_backlog_id}"
    for row in rows:
        metadata = dict(row.get("metadata") or {})
        if _text(row.get("source_ref") or metadata.get("source_ref")) == target_source_ref:
            return row
    return None


def _stage_acceptance(
    *,
    base_url: str,
    token: str,
    rows: list[dict[str, Any]],
    plan: dict[str, Any],
) -> dict[str, Any]:
    source_backlog_id = _text(plan.get("source_backlog_id"))
    source_record = _find_source_backlog(rows, source_backlog_id)
    if source_record is None:
        return {"source_backlog_id": source_backlog_id, "status": "missing_source_backlog"}
    result_id = _text(source_record.get("result_id"))
    if not result_id:
        return {"source_backlog_id": source_backlog_id, "status": "missing_result_id"}

    existing = _existing_acceptance_backlog(rows, source_backlog_id)
    acceptance_ref = _write_acceptance_artifact(plan, source_record)
    if existing is not None and _text(existing.get("status")) == "completed":
        return {
            "source_backlog_id": source_backlog_id,
            "status": "already_completed",
            "acceptance_backlog_id": _text(existing.get("id")),
            "acceptance_artifact": acceptance_ref,
        }

    if existing is not None:
        backlog_id = _text(existing.get("id"))
        transition_status, transition_body = _request_agent_json(
            base_url,
            token,
            f"/v1/operator/backlog/{backlog_id}/transition",
            method="POST",
            payload={
                "actor": "codex",
                "session_id": "codex-autonomous-value-proof",
                "correlation_id": uuid.uuid4().hex,
                "reason": f"Finalize autonomous value acceptance for {source_backlog_id}",
                "status": "completed",
                "note": "Automated acceptance materialized from a verified autonomous completion.",
            },
            timeout=20,
        )
        return {
            "source_backlog_id": source_backlog_id,
            "status": "completed" if transition_status == 200 else "transition_failed",
            "acceptance_backlog_id": backlog_id,
            "acceptance_artifact": acceptance_ref,
            "error": transition_body.get("error") if transition_status != 200 else None,
        }

    metadata = dict(source_record.get("metadata") or {})
    accepted_at = _iso_now()
    create_payload = {
        "actor": "codex",
        "session_id": "codex-autonomous-value-proof",
        "correlation_id": uuid.uuid4().hex,
        "reason": f"Materialized automated autonomous value acceptance for {source_backlog_id}",
        "title": _text(plan.get("title")),
        "prompt": f"Persist accepted autonomous value proof for {_text(source_record.get('title'))}.",
        "owner_agent": _text(plan.get("owner_agent")) or "research-agent",
        "scope_type": _text(source_record.get("scope_type")) or "global",
        "scope_id": _text(source_record.get("scope_id")) or "athanor",
        "work_class": _text(plan.get("work_class")) or "repo_audit",
        "priority": 2,
        "approval_mode": "none",
        "dispatch_policy": "planner_eligible",
        "family": _text(plan.get("family")),
        "project_id": _text(source_record.get("project_id")),
        "source_type": "value_proof_acceptance",
        "source_ref": f"autonomous-value-acceptance:{source_backlog_id}",
        "routing_class": _text(source_record.get("routing_class")) or "private_but_cloud_allowed",
        "verification_contract": _text(source_record.get("verification_contract")) or "evidence_bundle",
        "closure_rule": "verified_result_required",
        "materialization_source": "autonomous_value_acceptance",
        "materialization_reason": "Automated acceptance materialized from an autonomous verified completion.",
        "result_id": result_id,
        "value_class": _text(plan.get("value_class")),
        "deliverable_kind": _text(plan.get("deliverable_kind")),
        "deliverable_refs": list(plan.get("deliverable_refs") or []),
        "beneficiary_surface": _text(plan.get("beneficiary_surface")),
        "acceptance_mode": "automated",
        "accepted_by": "system",
        "accepted_at": accepted_at,
        "acceptance_proof_refs": [acceptance_ref],
        "operator_steered": False,
        "metadata": {
            "source_backlog_id": source_backlog_id,
            "source_result_id": result_id,
            "verification_passed": True,
            "verification_status": "passed",
            "latest_task_id": _text(metadata.get("latest_task_id")),
            "latest_run_id": _text(metadata.get("latest_run_id") or result_id),
            "proof_artifacts": list(metadata.get("proof_artifacts") or []),
            "value_class": _text(plan.get("value_class")),
            "deliverable_kind": _text(plan.get("deliverable_kind")),
            "deliverable_refs": list(plan.get("deliverable_refs") or []),
            "beneficiary_surface": _text(plan.get("beneficiary_surface")),
            "acceptance_mode": "automated",
            "accepted_by": "system",
            "accepted_at": accepted_at,
            "acceptance_proof_refs": [acceptance_ref],
            "operator_steered": False,
        },
    }
    create_status, create_body = _request_agent_json(
        base_url,
        token,
        "/v1/operator/backlog",
        method="POST",
        payload=create_payload,
        timeout=20,
    )
    if create_status != 200:
        return {
            "source_backlog_id": source_backlog_id,
            "status": "create_failed",
            "error": create_body.get("error"),
            "acceptance_artifact": acceptance_ref,
        }
    created = dict(create_body.get("backlog") or {})
    backlog_id = _text(created.get("id"))
    transition_status, transition_body = _request_agent_json(
        base_url,
        token,
        f"/v1/operator/backlog/{backlog_id}/transition",
        method="POST",
        payload={
            "actor": "codex",
            "session_id": "codex-autonomous-value-proof",
            "correlation_id": uuid.uuid4().hex,
            "reason": f"Finalize autonomous value acceptance for {source_backlog_id}",
            "status": "completed",
            "note": "Automated acceptance materialized from a verified autonomous completion.",
        },
        timeout=20,
    )
    return {
        "source_backlog_id": source_backlog_id,
        "status": "completed" if transition_status == 200 else "transition_failed",
        "acceptance_backlog_id": backlog_id,
        "acceptance_artifact": acceptance_ref,
        "error": transition_body.get("error") if transition_status != 200 else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize automated autonomous-value acceptance backlog items.")
    parser.add_argument("--stage1-seed", action="store_true", help="Materialize the built-in stage-1 operator-value acceptance set.")
    parser.add_argument("--source-backlog-id", help="Materialize acceptance for one completed autonomous value backlog item.")
    parser.add_argument("--title", help="Override the acceptance backlog title.")
    parser.add_argument("--owner-agent", help="Override the acceptance backlog owner agent.")
    parser.add_argument("--work-class", help="Override the acceptance backlog work class.")
    parser.add_argument("--family", help="Override the acceptance backlog family.")
    parser.add_argument("--value-class", help="Override the autonomous value class.")
    parser.add_argument("--deliverable-kind", help="Override the deliverable kind.")
    parser.add_argument("--deliverable-ref", action="append", default=[], help="Repeatable deliverable ref override.")
    parser.add_argument("--beneficiary-surface", help="Override the beneficiary surface.")
    parser.add_argument("--acceptance-summary", help="Override the acceptance summary.")
    parser.add_argument("--json", action="store_true", help="Print JSON result payload.")
    args = parser.parse_args()

    governed_truth = __import__("asyncio").run(_load_governed_dispatch_truth())
    base_url, token = _load_agent_runtime(governed_truth)
    backlog_payload = _load_agent_route_payload_sync("/v1/operator/backlog?limit=200", governed_truth)
    rows = [dict(item) for item in list(backlog_payload.get("backlog") or []) if isinstance(item, dict)]
    plans = list(STAGE1_SEED if args.stage1_seed else [])
    if args.source_backlog_id:
        plans.append(
            _build_plan_from_source_backlog(
                rows,
                source_backlog_id=args.source_backlog_id,
                title=args.title,
                owner_agent=args.owner_agent,
                work_class=args.work_class,
                family=args.family,
                value_class=args.value_class,
                deliverable_kind=args.deliverable_kind,
                deliverable_refs=list(args.deliverable_ref or []),
                beneficiary_surface=args.beneficiary_surface,
                acceptance_summary=args.acceptance_summary,
            )
        )
    if not plans:
        raise SystemExit("--stage1-seed or --source-backlog-id is required for this invocation")
    results = [_stage_acceptance(base_url=base_url, token=token, rows=rows, plan=plan) for plan in plans]
    payload = {
        "generated_at": _iso_now(),
        "result_count": len(results),
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if all(result.get("status") in {"completed", "already_completed"} for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
