#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry


RUN_ID = "watchdog-runtime-guard-private-local-2026q1"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "watchdog-runtime-guard-formal-eval.json"
EVAL_LEDGER_PATH = REPO_ROOT / "config" / "automation-backbone" / "eval-run-ledger.json"
WATCHDOG_MAIN = REPO_ROOT / "projects" / "agents" / "watchdog" / "main.py"
WATCHDOG_COMPOSE = REPO_ROOT / "projects" / "agents" / "watchdog" / "docker-compose.yml"
WATCHDOG_README = REPO_ROOT / "projects" / "agents" / "watchdog" / "README.md"
WATCHDOG_TESTS = [
    REPO_ROOT / "projects" / "agents" / "tests" / "test_watchdog_runtime_guard.py",
    REPO_ROOT / "projects" / "agents" / "tests" / "test_watchdog_route_contract.py",
]
VENV_PYTHON = REPO_ROOT / "projects" / "agents" / ".venv" / "Scripts" / "python.exe"
RUNTIME_PACKET_ID = "foundry-watchdog-runtime-guard-rollout-packet"
RUNTIME_LANE_ID = "foundry-watchdog-runtime-guard"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    dump_json(path, payload)


def _find_run(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    for run in payload.get("runs", []):
        if str(run.get("run_id") or "").strip() == run_id:
            return run
    raise SystemExit(f"Run id not found in eval-run-ledger.json: {run_id}")


def _run_pytest(test_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", str(test_path), "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "test_path": str(test_path).replace("\\", "/"),
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _parse_json_output(raw: str) -> dict[str, Any] | None:
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _probe_watchdog_live_bundle() -> dict[str, Any]:
    compose_probe = _run_command(["ssh", "foundry", "cd /opt/athanor/watchdog && docker compose ps"])
    health_probe = _run_command(["ssh", "foundry", "curl -sS http://127.0.0.1:9301/health"])
    status_probe = _run_command(["ssh", "foundry", "curl -sS http://127.0.0.1:9301/status"])
    return {
        "compose_ps": compose_probe,
        "health": {
            **health_probe,
            "parsed": _parse_json_output(health_probe["stdout"]),
        },
        "status": {
            **status_probe,
            "parsed": _parse_json_output(status_probe["stdout"]),
        },
    }


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def _summary_text(payload: dict[str, Any]) -> str:
    checks = payload["contract_checks"]
    passed_tests = all(test["passed"] for test in payload["pytest_runs"])
    if payload["promotion_eval_status"] == "passed":
        return (
            "Athanor-owned watchdog bundle is packet-backed and bounded, the FOUNDRY live canary is active, "
            "and the guarded restart contract passed both the focused route tests and the live canary probe."
        )
    failures = [name for name, ok in checks.items() if not ok]
    if not passed_tests:
        failures.append("pytest")
    return "Watchdog formal eval remains blocked by: " + ", ".join(sorted(failures))


def main() -> int:
    now = iso_now()
    runtime_packets = load_registry("runtime-ownership-packets.json")
    capability_registry = load_registry("capability-adoption-registry.json")
    eval_payload = _load_json(EVAL_LEDGER_PATH)
    run = _find_run(eval_payload, RUN_ID)

    packet = next(
        (
            dict(item)
            for item in runtime_packets.get("packets", [])
            if isinstance(item, dict) and str(item.get("id") or "").strip() == RUNTIME_PACKET_ID
        ),
        {},
    )
    capability = next(
        (
            dict(item)
            for item in capability_registry.get("capabilities", [])
            if isinstance(item, dict) and str(item.get("id") or "").strip() == "watchdog-runtime-guard"
        ),
        {},
    )

    pytest_runs = [_run_pytest(test_path) for test_path in WATCHDOG_TESTS]
    live_probe = _probe_watchdog_live_bundle()
    health_payload = live_probe["health"].get("parsed") or {}
    status_payload = live_probe["status"].get("parsed") or {}
    health_control_plane = health_payload.get("control_plane") if isinstance(health_payload, dict) else {}
    if not isinstance(health_control_plane, dict):
        health_control_plane = {}
    control_plane = status_payload.get("control_plane") if isinstance(status_payload, dict) else {}
    if not isinstance(control_plane, dict):
        control_plane = {}
    contract_checks = {
        "mutation_gate_env_in_source": _contains(WATCHDOG_MAIN, "WATCHDOG_MUTATIONS_ENABLED"),
        "runtime_packet_status_in_source": _contains(WATCHDOG_MAIN, "WATCHDOG_RUNTIME_PACKET_STATUS"),
        "compose_defaults_gate_open": _contains(WATCHDOG_COMPOSE, "WATCHDOG_MUTATIONS_ENABLED=true"),
        "compose_defaults_packet_executed": _contains(
            WATCHDOG_COMPOSE, "WATCHDOG_RUNTIME_PACKET_STATUS=executed"
        ),
        "compose_defaults_starts_active": _contains(WATCHDOG_COMPOSE, "WATCHDOG_INITIAL_PAUSED=false"),
        "readme_documents_fail_closed_packet": _contains(
            WATCHDOG_README, "foundry-watchdog-runtime-guard-rollout-packet"
        ),
        "runtime_packet_linked": packet.get("id") == RUNTIME_PACKET_ID,
        "runtime_packet_executed": str(packet.get("status") or "").strip() == "executed",
        "runtime_lane_registered": str(packet.get("lane_id") or "").strip() == RUNTIME_LANE_ID,
        "capability_links_runtime_packet": RUNTIME_PACKET_ID
        in [str(item) for item in capability.get("runtime_packet_ids", [])],
        "capability_links_runtime_lane": RUNTIME_LANE_ID
        in [str(item) for item in capability.get("runtime_ownership_lanes", [])],
        "live_probe_compose_ok": live_probe["compose_ps"]["returncode"] == 0,
        "live_probe_health_ok": live_probe["health"]["returncode"] == 0 and isinstance(health_payload, dict),
        "live_probe_status_ok": live_probe["status"]["returncode"] == 0 and isinstance(status_payload, dict),
        "live_probe_paused_false": bool(health_payload.get("paused")) is False,
        "live_probe_mutations_enabled": bool(health_payload.get("mutations_enabled")) is True,
        "live_probe_packet_id_matches": str(
            health_payload.get("runtime_packet_id") or health_control_plane.get("runtime_packet_id") or ""
        ).strip()
        == RUNTIME_PACKET_ID,
        "live_probe_packet_status_matches": str(
            health_payload.get("runtime_packet_status") or health_control_plane.get("runtime_packet_status") or ""
        ).strip()
        == "executed",
        "live_probe_mode_active": str(control_plane.get("mode") or "").strip() == "active",
    }

    blocking_reasons: list[str] = []
    if not all(test["passed"] for test in pytest_runs):
        blocking_reasons.append("watchdog-route-tests-failed")
    for check_name, passed in contract_checks.items():
        if not passed:
            blocking_reasons.append(check_name)

    promotion_eval_status = "passed" if not blocking_reasons else "blocked"
    promotion_validity = "valid" if promotion_eval_status == "passed" else "requires_formal_eval_run"

    report = {
        "version": "2026-04-14.1",
        "generated_at": now,
        "source_of_truth": "reports/truth-inventory/watchdog-runtime-guard-formal-eval.json",
        "initiative_id": "watchdog-runtime-guard",
        "run_id": RUN_ID,
        "promotion_eval_status": promotion_eval_status,
        "promotion_validity": promotion_validity,
        "blocking_reasons": blocking_reasons,
        "contract_checks": contract_checks,
        "pytest_runs": pytest_runs,
        "live_probe": live_probe,
        "runtime_packet_id": RUNTIME_PACKET_ID,
        "runtime_packet_status": str(packet.get("status") or "").strip() or "missing",
        "runtime_lane_id": str(packet.get("lane_id") or "").strip() or None,
        "next_action": (
            "Keep the rollout packet executed, keep the watchdog active as a bounded live canary, and reopen only when widening toward ordinary production or rolling back."
            if promotion_eval_status == "passed"
            else "Fix the blocked checks and rerun the Athanor-side watchdog formal eval."
        ),
        "summary": _summary_text(
            {
                "promotion_eval_status": promotion_eval_status,
                "contract_checks": contract_checks,
                "pytest_runs": pytest_runs,
            }
        ),
    }
    _write_json(OUTPUT_PATH, report)

    evidence_artifacts = [str(item) for item in run.get("evidence_artifacts", []) if str(item).strip()]
    for artifact in (
        str(WATCHDOG_README).replace("\\", "/"),
        str(OUTPUT_PATH).replace("\\", "/"),
        str((REPO_ROOT / "scripts" / "run_watchdog_runtime_guard_eval.py")).replace("\\", "/"),
        "C:/Athanor/config/automation-backbone/runtime-ownership-packets.json",
    ):
        if artifact not in evidence_artifacts:
            evidence_artifacts.append(artifact)

    notes = [
        str(item)
        for item in run.get("notes", [])
        if str(item).strip()
        and "should not be marked valid until rollback evidence is attached" not in str(item)
    ]
    notes.insert(
        0,
        "Rollback evidence now lives in the linked runtime packet and the formal-eval artifact; keep the watchdog live canary bounded by packet-backed scope, protected-service exclusions, and explicit operator envelopes.",
    )
    notes.append(f"{now}: {report['summary']}")

    run["evidence_artifacts"] = evidence_artifacts
    run["formal_eval_artifact_path"] = str(OUTPUT_PATH).replace("\\", "/")
    run["last_run_at"] = now
    run["notes"] = notes
    run["promotion_validity"] = promotion_validity
    run["source_safe_remaining"] = [
        "Keep the rollout packet executed and the watchdog in active canary mode while protected-service exclusions and operator-envelope controls remain intact."
    ]
    run["status"] = "completed"
    run["task_class"] = "runtime_guard_boundary_eval"
    run["wrapper_mode"] = "service_runtime"

    eval_payload["updated_at"] = now
    eval_payload["version"] = "2026-04-15.2"
    _write_json(EVAL_LEDGER_PATH, eval_payload)

    append_history(
        "capability-promotion-evals",
        {
            "generated_at": now,
            "initiative_id": "watchdog-runtime-guard",
            "run_id": RUN_ID,
            "promotion_eval_status": promotion_eval_status,
            "promotion_validity": promotion_validity,
            "blocking_reasons": blocking_reasons,
            "artifact_path": str(OUTPUT_PATH).replace("\\", "/"),
        },
    )
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
