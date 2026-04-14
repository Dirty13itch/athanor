#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now


DEFAULT_BASE_URL = "http://192.168.1.244:9300"
DEFAULT_OUTPUT_PATH = Path("C:/Athanor/reports/truth-inventory/graphrag-promotion-eval.json")


def _http_get(url: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    return _perform_request(request, timeout=timeout)


def _http_post(url: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _perform_request(request, timeout=timeout)


def _perform_request(request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
    started_at = iso_now()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body_text = response.read().decode("utf-8")
            parsed_body: Any
            try:
                parsed_body = json.loads(body_text)
            except json.JSONDecodeError:
                parsed_body = body_text
            return {
                "ok": True,
                "status_code": response.status,
                "started_at": started_at,
                "completed_at": iso_now(),
                "body": parsed_body,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_body = raw_body
        return {
            "ok": False,
            "status_code": exc.code,
            "started_at": started_at,
            "completed_at": iso_now(),
            "body": parsed_body,
            "error": f"HTTPError: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "started_at": started_at,
            "completed_at": iso_now(),
            "body": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _ssh_probe(command: str) -> dict[str, Any]:
    started_at = iso_now()
    completed = subprocess.run(
        ["ssh", "foundry", command],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "started_at": started_at,
        "completed_at": iso_now(),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _health_check(base_url: str) -> dict[str, Any]:
    result = _http_get(f"{base_url}/health", timeout=20)
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    passed = bool(result["ok"] and result["status_code"] == 200 and body.get("status") == "ok")
    return {
        "check_id": "health",
        "kind": "http_get",
        "required_for_promotion": True,
        "passed": passed,
        "details": result,
    }


def _query_check(base_url: str, *, scenario_id: str, query: str) -> dict[str, Any]:
    payload = {"query": query, "top_k": 3, "hops": 2}
    result = _http_post(f"{base_url}/query", payload, timeout=60)
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    passed = bool(
        result["ok"]
        and result["status_code"] == 200
        and isinstance(body.get("results"), list)
        and len(body.get("results", [])) > 0
        and int(body.get("entity_matches") or 0) > 0
    )
    return {
        "check_id": scenario_id,
        "kind": "http_post",
        "required_for_promotion": True,
        "payload": payload,
        "passed": passed,
        "details": result,
    }


def _status_check(base_url: str) -> dict[str, Any]:
    result = _http_get(f"{base_url}/status", timeout=30)
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    passed = bool(result["ok"] and result["status_code"] == 200 and isinstance(body, dict))
    return {
        "check_id": "status",
        "kind": "http_get",
        "required_for_promotion": True,
        "passed": passed,
        "details": result,
    }


def _hybrid_check(base_url: str) -> dict[str, Any]:
    payload = {
        "query": "Athanor dashboard routing",
        "top_k": 5,
        "route": "auto",
        "score_threshold": 0.2,
    }
    result = _http_post(f"{base_url}/query/hybrid", payload, timeout=90)
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    warnings = [str(item).strip() for item in body.get("warnings", []) if str(item).strip()]
    route = str(body.get("route") or "").strip()
    degraded_timeout_fallback = route == "graph_fallback" or any(
        "readtimeout" in warning.lower() or "vector path unavailable" in warning.lower()
        for warning in warnings
    )
    passed = bool(
        result["ok"]
        and result["status_code"] == 200
        and isinstance(body.get("results"), list)
        and len(body.get("results", [])) > 0
        and not degraded_timeout_fallback
    )
    return {
        "check_id": "hybrid_query",
        "kind": "http_post",
        "required_for_promotion": True,
        "payload": payload,
        "passed": passed,
        "details": result,
    }


def _runtime_probe() -> dict[str, Any]:
    compose = _ssh_probe("cd /opt/athanor/graphrag && docker compose ps")
    inspect = _ssh_probe(
        "docker inspect athanor-graphrag --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}'"
    )
    running = False
    inspect_stdout = inspect.get("stdout") or ""
    if isinstance(inspect_stdout, str):
        running = inspect_stdout.startswith("running|")
    return {
        "check_id": "runtime_deployment",
        "kind": "ssh",
        "required_for_promotion": True,
        "passed": bool(compose["ok"] and inspect["ok"] and running),
        "details": {
            "compose_ps": compose,
            "container_state": inspect,
        },
    }


def _summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    required = [check for check in checks if check.get("required_for_promotion")]
    failures = [check["check_id"] for check in required if not check.get("passed")]
    promotion_valid = not failures
    return {
        "required_check_count": len(required),
        "required_pass_count": sum(1 for check in required if check.get("passed")),
        "failed_required_checks": failures,
        "promotion_validity": "valid" if promotion_valid else "requires_formal_eval_run",
        "release_tier_recommendation": "shadow" if promotion_valid else "offline_eval",
        "overall_status": "passed" if promotion_valid else "blocked",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GraphRAG promotion eval and persist a machine-readable artifact.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--write", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    checks = [
        _runtime_probe(),
        _health_check(args.base_url),
        _query_check(args.base_url, scenario_id="graph_query_shaun", query="shaun"),
        _query_check(args.base_url, scenario_id="graph_query_athanor", query="athanor"),
        _status_check(args.base_url),
        _hybrid_check(args.base_url),
    ]
    summary = _summary(checks)
    payload = {
        "version": "2026-04-11.1",
        "generated_at": iso_now(),
        "source_of_truth": "reports/truth-inventory/graphrag-promotion-eval.json",
        "initiative_id": "graphrag-hybrid-retrieval",
        "run_id": "graphrag-hybrid-retrieval-golden-core-2026q1",
        "base_url": args.base_url,
        "summary": summary,
        "checks": checks,
    }
    dump_json(args.write, payload)
    append_history(
        "capability-promotion-evals",
        {
            "generated_at": payload["generated_at"],
            "initiative_id": payload["initiative_id"],
            "run_id": payload["run_id"],
            "overall_status": summary["overall_status"],
            "promotion_validity": summary["promotion_validity"],
            "release_tier_recommendation": summary["release_tier_recommendation"],
            "failed_required_checks": summary["failed_required_checks"],
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
