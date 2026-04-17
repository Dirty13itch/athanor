#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pilot_benchmark_support import validate_decision_trace_file
from promptfoo_runtime import resolve_promptfoo_runtime
from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry, resolve_external_path


OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capability-pilot-formal-preflight.json"
DEFAULT_RUN_IDS = [
    "goose-operator-shell-lane-eval-2026q2",
    "openhands-bounded-worker-lane-eval-2026q2",
    "letta-memory-plane-eval-2026q2",
    "agt-policy-plane-eval-2026q2",
    "agt-policy-plane-eval-2026q2-degraded-fallback",
]
MISSING_ENV_RE = re.compile(r"Missing ([A-Z0-9_]+)")


def _tooling_index(host_id: str) -> dict[str, dict[str, Any]]:
    tooling_inventory = load_registry("tooling-inventory.json")
    for host in tooling_inventory.get("hosts", []):
        if str(host.get("id") or "").strip().lower() != host_id.lower():
            continue
        return {
            str(tool.get("command") or "").strip(): dict(tool)
            for tool in host.get("tools", [])
            if isinstance(tool, dict) and str(tool.get("command") or "").strip()
        }
    return {}


def _current_local_command_state(command: str) -> dict[str, Any]:
    local_path = shutil.which(command)
    return {
        "command": command,
        "available_locally": bool(local_path),
        "local_path": local_path,
    }


def _promptfoo_runtime_state() -> dict[str, Any]:
    return resolve_promptfoo_runtime()


def _select_runs(selected_run_ids: list[str]) -> list[dict[str, Any]]:
    eval_ledger = load_registry("eval-run-ledger.json")
    run_ids = set(selected_run_ids or DEFAULT_RUN_IDS)
    return [
        dict(run)
        for run in eval_ledger.get("runs", [])
        if isinstance(run, dict) and str(run.get("run_id") or "").strip() in run_ids
    ]


def _scaffold_details(run: dict[str, Any]) -> dict[str, Any]:
    promptfoo_path = str(run.get("promptfoo_config_path") or "").strip() or None
    benchmark_spec_path = str(run.get("benchmark_spec_path") or "").strip() or None
    if promptfoo_path:
        path = resolve_external_path(promptfoo_path)
        return {"type": "promptfoo", "path": str(path), "exists": path.exists()}
    if benchmark_spec_path:
        path = resolve_external_path(benchmark_spec_path)
        return {"type": "benchmark_spec", "path": str(path), "exists": path.exists()}
    return {"type": None, "path": None, "exists": False}


def _path_check(path_value: str) -> dict[str, Any]:
    path = resolve_external_path(path_value)
    return {
        "path": str(path),
        "exists": path.exists(),
        "parent_exists": path.parent.exists(),
    }


def _env_check(name: str) -> dict[str, Any]:
    value = os.environ.get(name)
    return {
        "name": name,
        "present": bool(value),
    }


def _render_probe_value(value: str, tokens: dict[str, str]) -> str:
    rendered = value
    for key, token in tokens.items():
        rendered = rendered.replace(f"{{{key}}}", token)
    return rendered


def _extract_missing_env_hint(*texts: str | None) -> str | None:
    for text in texts:
        if not text:
            continue
        match = MISSING_ENV_RE.search(text)
        if match:
            return match.group(1)
    return None


def _run_command_probe(run: dict[str, Any]) -> dict[str, Any] | None:
    probe = dict(run.get("preflight_command_probe") or {})
    if not probe:
        return None

    command = str(probe.get("command") or "").strip()
    if not command:
        return {
            "status": "missing_config",
            "command": None,
        }

    local_state = _current_local_command_state(command)
    if not local_state["available_locally"]:
        return {
            "status": "command_missing",
            "command": command,
            "available_locally": False,
            "local_path": local_state["local_path"],
        }

    probe_prompt = str(probe.get("probe_prompt") or "Reply with READY only.").strip()
    tokens = {
        "probe_prompt": probe_prompt,
    }
    args = [
        _render_probe_value(str(item), tokens)
        for item in probe.get("args", [])
    ]
    cwd = str(resolve_external_path(probe.get("cwd") or REPO_ROOT))
    cwd_path = Path(cwd)
    if not cwd_path.exists():
        return {
            "status": "missing_cwd",
            "command": command,
            "cwd": cwd,
        }
    timeout_ms = int(probe.get("timeout_ms") or 20000)
    stdin_mode = str(probe.get("stdin_mode") or "none").strip().lower()
    stdin_payload = probe_prompt if stdin_mode == "text" else None
    success_substrings = [
        str(item)
        for item in probe.get("success_substrings", [])
        if str(item).strip()
    ]
    executable = str(local_state["local_path"] or command)
    argv = [executable, *args]

    try:
        completed = subprocess.run(
            argv,
            input=stdin_payload,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout_ms / 1000,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "status": "launch_failed",
            "command": command,
            "argv": argv,
            "cwd": cwd,
            "timeout_ms": timeout_ms,
            "error": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return {
            "status": "timeout",
            "command": command,
            "argv": argv,
            "cwd": cwd,
            "timeout_ms": timeout_ms,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
            "missing_env_hint": _extract_missing_env_hint(stdout, stderr),
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    combined = "\n".join(part for part in [stdout, stderr] if part)
    success = completed.returncode == 0
    if success_substrings:
        success = success and all(token in combined for token in success_substrings)

    return {
        "status": "passed" if success else "failed",
        "command": command,
        "argv": argv,
        "cwd": cwd,
        "timeout_ms": timeout_ms,
        "returncode": completed.returncode,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "missing_env_hint": _extract_missing_env_hint(stdout, stderr),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate source-safe formal pilot preflight requirements without executing the pilot."
    )
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--host-id", default="desk")
    parser.add_argument("--write", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    runs = _select_runs([str(item).strip() for item in args.run_id if str(item).strip()])
    tooling_index = _tooling_index(args.host_id)
    promptfoo_runtime = _promptfoo_runtime_state()

    records: list[dict[str, Any]] = []
    for run in runs:
        run_id = str(run.get("run_id") or "").strip()
        scaffold = _scaffold_details(run)
        execution_requirements = dict(run.get("execution_requirements") or {})
        required_commands = [
            str(item).strip()
            for item in execution_requirements.get("required_commands", [])
            if str(item).strip()
        ]
        required_env_vars = [
            str(item).strip()
            for item in run.get("required_env_vars", [])
            if str(item).strip()
        ]
        required_result_files = [
            str(resolve_external_path(str(item).strip()))
            for item in run.get("required_result_files", [])
            if str(item).strip()
        ]
        required_fixture_files = [
            str(resolve_external_path(str(item).strip()))
            for item in run.get("required_fixture_files", [])
            if str(item).strip()
        ]
        formal_eval_artifact_path_raw = str(run.get("formal_eval_artifact_path") or "").strip()
        formal_eval_artifact_path = (
            str(resolve_external_path(formal_eval_artifact_path_raw))
            if formal_eval_artifact_path_raw
            else None
        )
        preflight_only_allowed = bool(run.get("preflight_only_allowed", False))

        command_checks: list[dict[str, Any]] = []
        blockers: list[str] = []
        for command in required_commands:
            inventory_tool = tooling_index.get(command)
            local_state = _current_local_command_state(command)
            installed_in_inventory = (
                str(inventory_tool.get("status") or "").strip() == "installed"
                if inventory_tool
                else False
            )
            if not installed_in_inventory and not local_state["available_locally"]:
                blockers.append(f"missing_command:{command}")
            command_checks.append(
                {
                    "command": command,
                    "inventory_status": (
                        str(inventory_tool.get("status") or "missing") if inventory_tool else "missing"
                    ),
                    "inventory_version": (
                        str(inventory_tool.get("version") or "") or None
                        if inventory_tool
                        else None
                    ),
                    "available_locally": local_state["available_locally"],
                    "local_path": local_state["local_path"],
                }
            )

        if not scaffold["path"]:
            blockers.append("missing_formal_eval_scaffold")
        elif not scaffold["exists"]:
            blockers.append(f"missing_scaffold:{scaffold['path']}")

        if scaffold["type"] == "promptfoo" and not promptfoo_runtime["available"]:
            blockers.append(str(promptfoo_runtime.get("blocking_reason") or "missing_promptfoo_runtime"))

        env_checks = [_env_check(name) for name in required_env_vars]
        for env_check in env_checks:
            if not env_check["present"]:
                blockers.append(f"missing_env:{env_check['name']}")

        command_probe = _run_command_probe(run)
        if command_probe:
            probe_status = str(command_probe.get("status") or "").strip()
            probe_command = str(command_probe.get("command") or "").strip()
            missing_env_hint = str(command_probe.get("missing_env_hint") or "").strip() or None
            if probe_status == "command_missing":
                if probe_command:
                    blockers.append(f"missing_command:{probe_command}")
            elif probe_status == "missing_cwd":
                missing_cwd = str(command_probe.get("cwd") or "").strip()
                if missing_cwd:
                    blockers.append(f"missing_probe_cwd:{missing_cwd}")
            elif probe_status == "timeout":
                if missing_env_hint:
                    blockers.append(f"missing_env:{missing_env_hint}")
                elif probe_command:
                    blockers.append(f"probe_timeout:{probe_command}")
            elif probe_status in {"failed", "launch_failed"}:
                if missing_env_hint:
                    blockers.append(f"missing_env:{missing_env_hint}")
                elif probe_command:
                    blockers.append(f"probe_failed:{probe_command}")
            elif probe_status == "missing_config":
                blockers.append("missing_command_probe_config")

        artifact_check = _path_check(formal_eval_artifact_path) if formal_eval_artifact_path else None
        if artifact_check is None:
            blockers.append("missing_formal_eval_artifact_path")
        elif not artifact_check["parent_exists"]:
            blockers.append(f"missing_artifact_parent:{artifact_check['path']}")

        result_file_checks = [_path_check(path_value) for path_value in required_result_files]
        if not result_file_checks:
            blockers.append("missing_required_result_files")
        for result_file_check in result_file_checks:
            if not result_file_check["parent_exists"]:
                blockers.append(f"missing_result_parent:{result_file_check['path']}")

        fixture_file_checks = []
        for path_value in required_fixture_files:
            fixture_file_check = _path_check(path_value)
            if not fixture_file_check["exists"]:
                blockers.append(f"missing_fixture:{fixture_file_check['path']}")
            elif scaffold["type"] == "benchmark_spec":
                validation = validate_decision_trace_file(path_value)
                fixture_file_check.update(
                    {
                        "valid": validation["valid"],
                        "errors": list(validation.get("errors", [])),
                        "trace_id": validation.get("trace_id"),
                        "scenario_id": validation.get("scenario_id"),
                        "policy_class": validation.get("policy_class"),
                    }
                )
                if not validation["valid"]:
                    blockers.append(f"invalid_fixture:{fixture_file_check['path']}")
            fixture_file_checks.append(fixture_file_check)

        blockers = list(dict.fromkeys(blockers))
        status = "ready" if not blockers else "blocked"
        records.append(
            {
                "run_id": run_id,
                "initiative_id": str(run.get("initiative_id") or "").strip(),
                "host_id": args.host_id,
                "preflight_status": status,
                "blocking_reasons": blockers,
                "scaffold_type": scaffold["type"],
                "scaffold_path": scaffold["path"],
                "scaffold_exists": scaffold["exists"],
                "promptfoo_runtime_available": promptfoo_runtime["available"],
                "promptfoo_runtime_command_path": promptfoo_runtime["command_path"],
                "promptfoo_runtime_mode": promptfoo_runtime.get("mode"),
                "promptfoo_runtime_source": promptfoo_runtime.get("source"),
                "promptfoo_runtime_cli_path": promptfoo_runtime.get("cli_path"),
                "promptfoo_runtime_node_version": promptfoo_runtime["node_version"],
                "promptfoo_runtime_node_path": promptfoo_runtime.get("node_path"),
                "promptfoo_runtime_node_supported": promptfoo_runtime["node_version_supported"],
                "promptfoo_runtime_probe_attempts": promptfoo_runtime.get("probe_attempts", []),
                "required_commands": required_commands,
                "command_checks": command_checks,
                "required_env_vars": required_env_vars,
                "env_checks": env_checks,
                "command_probe": command_probe,
                "formal_eval_artifact_path": formal_eval_artifact_path,
                "formal_eval_artifact_check": artifact_check,
                "required_result_files": required_result_files,
                "result_file_checks": result_file_checks,
                "required_fixture_files": required_fixture_files,
                "fixture_file_checks": fixture_file_checks,
                "preflight_only_allowed": preflight_only_allowed,
                "captured_at": iso_now(),
            }
        )

    summary = {
        "total": len(records),
        "ready": sum(1 for item in records if item["preflight_status"] == "ready"),
        "blocked": sum(1 for item in records if item["preflight_status"] == "blocked"),
    }
    payload = {
        "version": "2026-04-11.4",
        "generated_at": iso_now(),
        "host_id": args.host_id,
        "source_of_truth": "reports/truth-inventory/capability-pilot-formal-preflight.json",
        "summary": summary,
        "records": records,
    }
    dump_json(args.write, payload)
    append_history(
        "capability-pilot-formal-preflight",
        {
            "generated_at": payload["generated_at"],
            "source_of_truth": payload["source_of_truth"],
            "host_id": payload["host_id"],
            "summary": summary,
            "run_ids": [record["run_id"] for record in records],
        },
    )
    print(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
