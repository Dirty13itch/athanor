#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from scripts._cluster_config import get_url
except ModuleNotFoundError:
    from _cluster_config import get_url

try:
    from scripts.runtime_env import load_optional_runtime_env
except ModuleNotFoundError:
    from runtime_env import load_optional_runtime_env


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "reports" / "autonomy-loop" / "latest.json"
DEFAULT_JOB_ORDER = [
    "alert-check",
    "daily-digest",
    "consolidation",
    "pattern-detection",
    "owner-model",
    "improvement-cycle",
    "pipeline-cycle",
    "morning-plan",
    "workplan-refill",
    "research:scheduler",
    "benchmark-cycle",
    "cache-cleanup",
    "nightly-optimization",
    "knowledge-refresh",
    "weekly-dpo-training",
    "creative-cascade",
    "code-cascade",
]


def _load_runtime() -> tuple[str, str]:
    load_optional_runtime_env(env_names=["ATHANOR_AGENT_API_TOKEN"])
    base_url = os.environ.get("ATHANOR_AGENT_SERVER_URL", "").strip() or get_url("agent_server")
    token = os.environ.get("ATHANOR_AGENT_API_TOKEN", "").strip()
    return base_url.rstrip("/"), token


def _request_json(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 180,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = Request(f"{base_url}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload_data = {"error": body or str(exc)}
        return exc.code, payload_data
    except (TimeoutError, socket.timeout) as exc:
        return 598, {"error": f"timeout: {exc}", "type": type(exc).__name__}
    except URLError as exc:
        return 599, {"error": str(exc)}


def _build_agent_schedule_order(jobs_by_id: dict[str, dict[str, Any]]) -> list[str]:
    agent_ids = sorted(job_id for job_id in jobs_by_id if job_id.startswith("agent-schedule:"))
    return agent_ids


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one governed native autonomy loop pass.")
    parser.add_argument("--base-url", default="", help="Override agent server base URL.")
    parser.add_argument("--actor", default="operator", help="Actor recorded for operator audit.")
    parser.add_argument("--reason", default="Native autonomy loop pass", help="Reason recorded for operator audit.")
    parser.add_argument(
        "--skip-agent-schedules",
        action="store_true",
        help="Skip the per-agent proactive loop runs after the builtin native loop set.",
    )
    parser.add_argument(
        "--force-deferred",
        action="store_true",
        help="Force jobs that are currently deferred by governor posture.",
    )
    parser.add_argument("--timeout", type=int, default=180, help="HTTP timeout per request in seconds.")
    args = parser.parse_args()

    base_url, token = _load_runtime()
    if args.base_url.strip():
        base_url = args.base_url.strip().rstrip("/")

    session_id = f"autonomy-loop-{uuid.uuid4().hex[:12]}"
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    health_status, health_before = _request_json(base_url, token, "/health", timeout=args.timeout)
    scheduled_status, scheduled_payload = _request_json(
        base_url,
        token,
        "/v1/tasks/scheduled?limit=500",
        timeout=args.timeout,
    )
    jobs = list(scheduled_payload.get("jobs") or []) if scheduled_status == 200 else []
    jobs_by_id = {str(job.get("id") or ""): dict(job) for job in jobs if job.get("id")}

    job_order = list(DEFAULT_JOB_ORDER)
    if not args.skip_agent_schedules:
        job_order.extend(_build_agent_schedule_order(jobs_by_id))

    results: list[dict[str, Any]] = []
    counts = {"completed": 0, "queued": 0, "pending_approval": 0, "skipped": 0, "failed": 0, "missing": 0}
    for job_id in job_order:
        job_record = jobs_by_id.get(job_id)
        if job_record is None:
            counts["missing"] += 1
            results.append(
                {
                    "job_id": job_id,
                    "status_code": 404,
                    "status": "missing",
                    "summary": "Job not present in scheduled inventory",
                }
            )
            continue

        force = bool(args.force_deferred and str(job_record.get("current_state") or "") == "deferred")
        body = {
            "actor": args.actor,
            "session_id": session_id,
            "correlation_id": uuid.uuid4().hex,
            "reason": f"{args.reason}: {job_id}",
            "force": force,
        }
        path = f"/v1/tasks/scheduled/{quote(job_id, safe='')}/run"
        status_code, payload = _request_json(
            base_url,
            token,
            path,
            method="POST",
            payload=body,
            timeout=args.timeout,
        )
        status = str(payload.get("status") or ("failed" if status_code >= 400 else "completed"))
        if status in counts:
            counts[status] += 1
        elif status_code >= 400:
            counts["failed"] += 1
        else:
            counts["completed"] += 1
        results.append(
            {
                "job_id": job_id,
                "status_code": status_code,
                "status": status,
                "forced": force,
                "current_state": job_record.get("current_state"),
                "summary": payload.get("summary") or payload.get("error") or "",
                "response": payload,
            }
        )

    _, health_after = _request_json(base_url, token, "/health", timeout=args.timeout)
    completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report = {
        "started_at": started_at,
        "completed_at": completed_at,
        "base_url": base_url,
        "session_id": session_id,
        "force_deferred": bool(args.force_deferred),
        "skip_agent_schedules": bool(args.skip_agent_schedules),
        "health_before_status_code": health_status,
        "scheduled_status_code": scheduled_status,
        "health_before": health_before,
        "health_after": health_after,
        "job_order": job_order,
        "job_count": len(job_order),
        "inventory_count": len(jobs),
        "counts": counts,
        "results": results,
    }
    _write_report(report)
    print(json.dumps(report, indent=2))
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
