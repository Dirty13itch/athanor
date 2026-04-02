from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _container_python(container: str, code: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "python", "-"],
        input=code,
        text=True,
        capture_output=True,
        cwd=_repo_root(),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "container python execution failed")
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"container python output was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("container python output must be a JSON object")
    return payload


def _prepare_code(actor: str, reason: str) -> str:
    return f"""
import json
from athanor_agents.restart_proof import prepare_durable_restart_proof
payload = prepare_durable_restart_proof(actor={actor!r}, reason={reason!r})
print(json.dumps(payload))
""".strip()


def _finalize_code(proof_id: str, actor: str, reason: str) -> str:
    return f"""
import json
from athanor_agents.restart_proof import finalize_durable_restart_proof
payload = finalize_durable_restart_proof({proof_id!r}, actor={actor!r}, reason={reason!r})
print(json.dumps(payload))
""".strip()


def _wait_for_health(health_url: str, *, timeout_seconds: int, interval_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + max(timeout_seconds, 1)
    last_error = "health check did not run"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(interval_seconds)
            continue
        if isinstance(payload, dict):
            return payload
        last_error = "health payload was not a JSON object"
        time.sleep(interval_seconds)
    raise TimeoutError(f"Timed out waiting for healthy runtime at {health_url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the live durable restart-proof harness against the athanor-agents container.")
    parser.add_argument("--container", default="athanor-agents", help="Running agents container name.")
    parser.add_argument(
        "--restart-command",
        default="docker restart athanor-agents",
        help="Command used to restart the live agents runtime after the proof checkpoint is prepared.",
    )
    parser.add_argument("--runtime-cwd", default="", help="Optional working directory for the restart command.")
    parser.add_argument("--health-url", default="http://localhost:9000/health", help="Health URL used to wait for the restarted runtime.")
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Maximum wait for the restarted runtime to return health.")
    parser.add_argument("--interval-seconds", type=float, default=2.0, help="Polling interval while waiting for health.")
    parser.add_argument("--actor", default="operator", help="Actor recorded in the proof artifact.")
    parser.add_argument("--reason", default="approved durable persistence restart proof", help="Reason recorded in the proof artifact.")
    parser.add_argument("--json", action="store_true", help="Emit the final proof payload as JSON.")
    args = parser.parse_args()

    prepare_payload = _container_python(args.container, _prepare_code(args.actor, args.reason))
    proof_id = str(prepare_payload.get("proof_id") or "")
    if not proof_id:
        print(json.dumps(prepare_payload, indent=2))
        return 1

    restart = subprocess.run(
        args.restart_command,
        cwd=args.runtime_cwd or None,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    if restart.returncode != 0:
        raise RuntimeError(restart.stderr.strip() or restart.stdout.strip() or "restart command failed")

    health_payload = _wait_for_health(
        args.health_url,
        timeout_seconds=max(args.timeout_seconds, 1),
        interval_seconds=max(args.interval_seconds, 0.25),
    )
    finalize_payload = _container_python(args.container, _finalize_code(proof_id, args.actor, args.reason))
    finalize_payload["restart_command"] = args.restart_command
    finalize_payload["health_url"] = args.health_url
    finalize_payload["health_wait_snapshot"] = health_payload

    if args.json:
        print(json.dumps(finalize_payload, indent=2))
        return 0 if finalize_payload.get("passed") else 1

    print(f"proof_id={finalize_payload.get('proof_id', '')}")
    print(f"phase={finalize_payload.get('phase', '')}")
    print(f"passed={bool(finalize_payload.get('passed'))}")
    print(f"detail={finalize_payload.get('detail', '')}")
    return 0 if finalize_payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
