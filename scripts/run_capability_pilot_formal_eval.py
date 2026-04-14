#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from pilot_benchmark_support import (
    build_policy_diff_summary,
    build_rollback_note,
    dump_json_file,
    validate_decision_trace_file,
)
from promptfoo_runtime import resolve_promptfoo_runtime
from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry


PREFLIGHT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-formal-preflight.json"
VAULT_SSH_HELPER_PATH = REPO_ROOT / "scripts" / "vault-ssh.py"


def _load_preflight_index() -> dict[str, dict[str, Any]]:
    if not PREFLIGHT_PATH.exists():
        return {}
    payload = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    return {
        str(record.get("run_id") or "").strip(): dict(record)
        for record in payload.get("records", [])
        if isinstance(record, dict) and str(record.get("run_id") or "").strip()
    }


def _load_run(run_id: str) -> dict[str, Any]:
    ledger = load_registry("eval-run-ledger.json")
    return next(
        (
            dict(run)
            for run in ledger.get("runs", [])
            if isinstance(run, dict) and str(run.get("run_id") or "").strip() == run_id
        ),
        {},
    )


def _scaffold_details(run: dict[str, Any]) -> dict[str, Any]:
    promptfoo_path = str(run.get("promptfoo_config_path") or "").strip() or None
    benchmark_spec_path = str(run.get("benchmark_spec_path") or "").strip() or None
    if promptfoo_path:
        return {"type": "promptfoo", "path": promptfoo_path}
    if benchmark_spec_path:
        return {"type": "benchmark_spec", "path": benchmark_spec_path}
    return {"type": None, "path": None}


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _write_artifact(artifact_path: Path, payload: dict[str, Any]) -> None:
    dump_json(artifact_path, payload)
    append_history(
        "capability-pilot-formal-evals",
        {
            "generated_at": payload["generated_at"],
            "run_id": payload["run_id"],
            "initiative_id": payload["initiative_id"],
            "status": payload["status"],
            "artifact_path": str(artifact_path),
        },
    )


def _promptfoo_runtime_state() -> dict[str, Any]:
    return resolve_promptfoo_runtime()


def _decode_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _key_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _looks_placeholder_key(value: str | None) -> bool:
    normalized = str(value or "").strip()
    return normalized in {"", "placeholder-local-key"} or normalized.startswith("placeholder-local-key")


def _read_vault_litellm_master_key() -> dict[str, Any]:
    if not VAULT_SSH_HELPER_PATH.exists():
        return {
            "key": None,
            "source": None,
            "fingerprint": None,
            "error": "missing_vault_ssh_helper",
        }

    remote_command = """python3 - <<'PY'
import json
import subprocess

raw = subprocess.check_output(['docker', 'inspect', 'litellm'], text=True)
data = json.loads(raw)[0]
for item in data.get('Config', {}).get('Env', []):
    if item.startswith('LITELLM_MASTER_KEY='):
        print(item.split('=', 1)[1], end='')
        break
PY"""
    completed = subprocess.run(
        [sys.executable, str(VAULT_SSH_HELPER_PATH), remote_command],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "key": None,
            "source": None,
            "fingerprint": None,
            "error": _decode_output(completed.stderr).strip() or "vault_ssh_failed",
        }

    key = completed.stdout.strip()
    if not key:
        return {
            "key": None,
            "source": None,
            "fingerprint": None,
            "error": "vault_master_key_missing",
        }

    return {
        "key": key,
        "source": "vault:docker_inspect_env",
        "fingerprint": _key_fingerprint(key),
        "error": None,
    }


def _resolve_promptfoo_grader_key() -> dict[str, Any]:
    candidate_names = [
        "ATHANOR_LITELLM_API_KEY",
        "LITELLM_MASTER_KEY",
        "LITELLM_API_KEY",
    ]
    placeholder_detected = False
    for name in candidate_names:
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        if _looks_placeholder_key(value):
            placeholder_detected = True
            continue
        return {
            "key": value,
            "source": f"env:{name}",
            "fingerprint": _key_fingerprint(value),
            "placeholder_detected": placeholder_detected,
            "error": None,
        }

    vault_key = _read_vault_litellm_master_key()
    vault_key["placeholder_detected"] = placeholder_detected
    return vault_key


def _compact_text(value: Any, *, limit: int = 280) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _summarize_promptfoo_results(result_path: Path) -> dict[str, Any]:
    if not result_path.exists():
        return {}
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    results_root = payload.get("results", {})
    if not isinstance(results_root, dict):
        return {}

    stats = results_root.get("stats", {})
    result_rows = results_root.get("results", [])
    if not isinstance(stats, dict) or not isinstance(result_rows, list):
        return {}

    failed_cases: list[dict[str, Any]] = []
    for item in result_rows:
        if not isinstance(item, dict):
            continue
        if bool(item.get("success")):
            continue
        provider = item.get("provider")
        provider_label = provider.get("label") if isinstance(provider, dict) else provider
        vars_payload = item.get("vars", {})
        task_id = vars_payload.get("task_id") if isinstance(vars_payload, dict) else None
        grading_result = item.get("gradingResult", {})
        failure_reason = (
            grading_result.get("reason")
            if isinstance(grading_result, dict)
            else item.get("error")
        )
        failed_cases.append(
            {
                "provider": str(provider_label or "").strip() or None,
                "task_id": str(task_id or "").strip() or None,
                "score": item.get("score"),
                "failure_reason": _compact_text(failure_reason, limit=360),
            }
        )

    primary_failure_hint = None
    if failed_cases:
        lead = failed_cases[0]
        parts = []
        if lead.get("provider"):
            parts.append(str(lead["provider"]))
        if lead.get("task_id"):
            parts.append(f"task `{lead['task_id']}`")
        prefix = " remaining miss in ".join(parts[:1]) if parts else "remaining miss"
        if len(parts) > 1:
            prefix = f"{parts[0]} remaining miss in {parts[1]}"
        if lead.get("failure_reason"):
            primary_failure_hint = f"{prefix}: {lead['failure_reason']}"
        else:
            primary_failure_hint = prefix

    return {
        "promptfoo_summary": {
            "successes": int(stats.get("successes") or 0),
            "failures": int(stats.get("failures") or 0),
            "errors": int(stats.get("errors") or 0),
            "duration_ms": int(stats.get("durationMs") or 0),
        },
        "promptfoo_failed_cases": failed_cases[:5],
        "promptfoo_primary_failure_hint": primary_failure_hint,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one formal pilot eval when preflight is ready, or emit a blocked artifact when it is not."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()

    run = _load_run(args.run_id)
    if not run:
        raise SystemExit(f"Unknown run id: {args.run_id}")

    artifact_path_value = str(run.get("formal_eval_artifact_path") or "").strip()
    if not artifact_path_value:
        raise SystemExit(f"Run {args.run_id} is missing formal_eval_artifact_path")
    artifact_path = Path(artifact_path_value)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    initiative_id = str(run.get("initiative_id") or "").strip()
    preflight = _load_preflight_index().get(args.run_id, {})
    preflight_status = str(preflight.get("preflight_status") or "not_run")
    preflight_blockers = [
        str(item).strip()
        for item in preflight.get("blocking_reasons", [])
        if str(item).strip()
    ]
    scaffold = _scaffold_details(run)
    result_files = [
        str(item).strip()
        for item in run.get("required_result_files", [])
        if str(item).strip()
    ]
    fixture_files = [
        str(item).strip()
        for item in run.get("required_fixture_files", [])
        if str(item).strip()
    ]

    payload: dict[str, Any] = {
        "version": "2026-04-11.2",
        "generated_at": iso_now(),
        "run_id": args.run_id,
        "initiative_id": initiative_id,
        "scaffold_type": scaffold["type"],
        "scaffold_path": scaffold["path"],
        "formal_result_files": result_files,
        "preflight_status": preflight_status,
        "preflight_blocking_reasons": preflight_blockers,
    }

    if preflight_status != "ready" and not args.allow_blocked:
        payload.update(
            {
                "status": "blocked",
                "decision_reason": "formal_preflight_blocked",
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0

    if not result_files:
        payload.update(
            {
                "status": "blocked",
                "decision_reason": "missing_result_output_target",
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0

    if scaffold["type"] == "benchmark_spec":
        fixture_validation = [validate_decision_trace_file(path) for path in fixture_files]
        invalid_fixtures = [
            {
                "path": item["path"],
                "errors": list(item.get("errors", [])),
            }
            for item in fixture_validation
            if not item.get("valid")
        ]
        if invalid_fixtures:
            payload.update(
                {
                    "status": "blocked",
                    "decision_reason": "invalid_fixture_contract",
                    "fixture_validation": fixture_validation,
                }
            )
            _write_artifact(artifact_path, payload)
            print(artifact_path)
            return 0

        if len(result_files) < len(fixture_validation):
            payload.update(
                {
                    "status": "blocked",
                    "decision_reason": "missing_result_output_target",
                    "fixture_validation": fixture_validation,
                }
            )
            _write_artifact(artifact_path, payload)
            print(artifact_path)
            return 0

        for source, destination in zip(fixture_validation, result_files, strict=False):
            dump_json_file(destination, dict(source["payload"]))

        native_payload = dict(fixture_validation[0]["payload"]) if fixture_validation else {}
        bridge_payload = dict(fixture_validation[1]["payload"]) if len(fixture_validation) > 1 else {}
        if len(result_files) >= 3:
            _write_text(result_files[2], build_policy_diff_summary(native_payload, bridge_payload))
        if len(result_files) >= 4:
            _write_text(result_files[3], build_rollback_note(native_payload, bridge_payload))

        payload.update(
            {
                "status": "manual_review_pending",
                "decision_reason": "benchmark_spec_materialized",
                "fixture_validation": fixture_validation,
                "result_paths": result_files,
                "review_scope": "manual_contract_review",
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0

    if scaffold["type"] != "promptfoo":
        payload.update(
            {
                "status": "blocked",
                "decision_reason": "unsupported_scaffold_type",
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0

    result_path = Path(result_files[0])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    promptfoo_runtime = _promptfoo_runtime_state()
    promptfoo_command = promptfoo_runtime["command"]
    if not promptfoo_command:
        payload.update(
            {
                "status": "blocked",
                "decision_reason": str(promptfoo_runtime.get("blocking_reason") or "missing_promptfoo_runtime"),
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0
    if not promptfoo_runtime["available"]:
        payload.update(
            {
                "status": "blocked",
                "decision_reason": str(promptfoo_runtime.get("blocking_reason") or "missing_promptfoo_runtime"),
                "node_version": promptfoo_runtime["node_version"],
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0

    command = [
        *promptfoo_command,
        "eval",
        "-c",
        str(scaffold["path"]),
        "-o",
        str(result_path),
        "--no-cache",
    ]
    grader_key = _resolve_promptfoo_grader_key()
    formal_eval_timeout_ms = int(run.get("formal_eval_timeout_ms") or 900000)
    child_env = os.environ.copy()
    if grader_key.get("key"):
        child_env["LITELLM_API_KEY"] = str(grader_key["key"])
        child_env.setdefault("ATHANOR_LITELLM_API_KEY", str(grader_key["key"]))
    payload.update(
        {
            "grader_api_key_source": grader_key.get("source"),
            "grader_api_key_fingerprint": grader_key.get("fingerprint"),
            "grader_api_key_error": grader_key.get("error"),
            "grader_api_key_placeholder_detected": bool(grader_key.get("placeholder_detected")),
            "timeout_ms": formal_eval_timeout_ms,
        }
    )
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env=child_env,
            capture_output=True,
            text=False,
            timeout=formal_eval_timeout_ms / 1000,
            check=False,
        )
    except FileNotFoundError as exc:
        payload.update(
            {
                "status": "failed",
                "decision_reason": "promptfoo_launch_failed",
                "command": command,
                "promptfoo_runtime_mode": promptfoo_runtime.get("mode"),
                "promptfoo_runtime_source": promptfoo_runtime.get("source"),
                "error": str(exc),
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0
    except subprocess.TimeoutExpired as exc:
        payload.update(
            {
                "status": "failed",
                "decision_reason": "promptfoo_timeout",
                "command": command,
                "promptfoo_runtime_mode": promptfoo_runtime.get("mode"),
                "promptfoo_runtime_source": promptfoo_runtime.get("source"),
                "promptfoo_runtime_node_path": promptfoo_runtime.get("node_path"),
                "promptfoo_runtime_node_version": promptfoo_runtime.get("node_version"),
                "stdout_tail": _decode_output(exc.stdout)[-4000:],
                "stderr_tail": _decode_output(exc.stderr)[-4000:],
                "result_path": str(result_path),
                "result_exists": result_path.exists(),
            }
        )
        _write_artifact(artifact_path, payload)
        print(artifact_path)
        return 0
    stdout_text = _decode_output(completed.stdout)
    stderr_text = _decode_output(completed.stderr)
    payload.update(
        {
            "status": "passed" if completed.returncode == 0 else "failed",
            "decision_reason": "promptfoo_completed" if completed.returncode == 0 else "promptfoo_failed",
            "command": command,
            "promptfoo_runtime_mode": promptfoo_runtime.get("mode"),
            "promptfoo_runtime_source": promptfoo_runtime.get("source"),
            "promptfoo_runtime_node_path": promptfoo_runtime.get("node_path"),
            "promptfoo_runtime_node_version": promptfoo_runtime.get("node_version"),
            "returncode": completed.returncode,
            "stdout_tail": stdout_text[-4000:],
            "stderr_tail": stderr_text[-4000:],
            "result_path": str(result_path),
            "result_exists": result_path.exists(),
        }
    )
    payload.update(_summarize_promptfoo_results(result_path))
    _write_artifact(artifact_path, payload)
    print(artifact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
