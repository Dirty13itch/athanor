#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-supervisor-health.json"
SERVICE_CONTRACT_PATH = REPO_ROOT / "scripts" / "athanor-continuity.service"
CONTINUITY_PROCESS_MARKERS = (
    "run_continuity_supervisor.py",
    "run_steady_state_control_plane.py",
    "collect_truth_inventory.py",
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_pid(value: Any) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _supervisor_pid_is_live(pid: Any) -> bool:
    normalized = _normalize_pid(pid)
    if normalized is None:
        return False
    try:
        cmdline = (Path("/proc") / str(normalized) / "cmdline").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "run_continuity_supervisor.py" in cmdline


def _any_continuity_process_alive() -> bool:
    proc_root = Path("/proc")
    try:
        proc_entries = list(proc_root.iterdir())
    except OSError:
        return False
    for entry in proc_entries:
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in cmdline for marker in CONTINUITY_PROCESS_MARKERS):
            return True
    return False


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_payload(
    *,
    continuity_state: dict[str, Any],
    runtime_parity: dict[str, Any],
    blocker_map: dict[str, Any],
    now_iso: str | None = None,
) -> dict[str, Any]:
    now_dt = _parse_iso(now_iso) or datetime.now(timezone.utc)
    last_successful = _parse_iso(continuity_state.get("last_successful_pass_at"))
    controller_status = str(continuity_state.get("controller_status") or "unknown")
    controller_pid = _normalize_pid(continuity_state.get("controller_pid"))
    controller_process_alive = _supervisor_pid_is_live(controller_pid)
    continuity_process_alive = _any_continuity_process_alive()
    typed_brake = continuity_state.get("typed_brake")
    drift_class = str(runtime_parity.get("drift_class") or "unknown")

    recent_success = bool(last_successful and now_dt - last_successful <= timedelta(minutes=10))
    if typed_brake or drift_class not in {"clean", "generated_surface_drift"}:
        health_status = "degraded"
        detail = str(typed_brake or runtime_parity.get("detail") or "Typed brake is active.")
    elif controller_status == "running" and not continuity_process_alive:
        health_status = "degraded"
        detail = "Continuity controller is marked running, but no live supervisor process was found."
    elif controller_status == "running" or recent_success:
        health_status = "healthy"
        detail = "Continuity supervisor is active with recent successful passes."
    elif controller_status in {"skipped", "blocked"}:
        health_status = "warning"
        detail = str(continuity_state.get("last_skip_reason") or "Supervisor is paused or skipped.")
    else:
        health_status = "degraded"
        detail = "Continuity supervisor has no recent healthy pass."

    return {
        "generated_at": now_dt.isoformat(),
        "controller_host": str(continuity_state.get("controller_host") or "dev"),
        "controller_pid": controller_pid,
        "controller_process_alive": controller_process_alive,
        "continuity_process_alive": continuity_process_alive,
        "controller_mode": str(continuity_state.get("controller_mode") or "unknown"),
        "controller_status": controller_status,
        "service_name": "athanor-continuity.service",
        "service_contract_path": str(SERVICE_CONTRACT_PATH),
        "typed_brake": typed_brake,
        "health_status": health_status,
        "detail": detail,
        "proof_gate_open": bool((blocker_map.get("proof_gate") or {}).get("open")),
        "last_successful_pass_at": continuity_state.get("last_successful_pass_at"),
        "source_artifacts": {
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
            "continuity_supervisor_health": str(OUTPUT_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor continuity supervisor health artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when continuity-supervisor-health.json is stale.")
    args = parser.parse_args()

    payload = build_payload(
        continuity_state=_load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH),
        runtime_parity=_load_optional_json(RUNTIME_PARITY_PATH),
        blocker_map=_load_optional_json(BLOCKER_MAP_PATH),
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
