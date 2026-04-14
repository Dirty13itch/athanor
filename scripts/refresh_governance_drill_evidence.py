#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from routing_contract_support import dump_json


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "governance-drill-registry.json"
DEFAULT_SSH_TARGET = "foundry"
DEFAULT_BASE_URL = "http://127.0.0.1:9000"
DEFAULT_DRILLS = ("constrained-mode", "degraded-mode", "recovery-only")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_remote_python(ssh_target: str, code: str) -> str:
    result = subprocess.run(
        ["ssh", ssh_target, f"python3 -c {shlex.quote(code)}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or f"ssh {ssh_target} failed"
        raise RuntimeError(stderr)
    return result.stdout.strip()


def _remote_request_json(
    ssh_target: str,
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    payload_literal = repr(json.dumps(payload or {}, sort_keys=True))
    code = f"""
import json
import urllib.error
import urllib.request
import sys

method = {method!r}
url = {url!r}
payload = json.loads({payload_literal})
data = None if method == "GET" else json.dumps(payload, sort_keys=True).encode("utf-8")
request = urllib.request.Request(
    url,
    data=data,
    headers={{"Accept": "application/json", "Content-Type": "application/json"}},
    method=method,
)
try:
    with urllib.request.urlopen(request, timeout={int(timeout_seconds)}) as response:
        sys.stdout.write(response.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    raise SystemExit(f"HTTP {{exc.code}} {{body}}")
"""
    output = _run_remote_python(ssh_target, code)
    if not output:
        raise RuntimeError(f"Remote {method} {url} returned no output")
    return json.loads(output)


def _registry_targets() -> dict[str, Path]:
    registry = load_json(REGISTRY_PATH)
    targets: dict[str, Path] = {}
    for drill in registry.get("drills", []):
        if not isinstance(drill, dict):
            continue
        drill_id = str(drill.get("drill_id") or "").strip()
        evidence = drill.get("evidence_artifacts") or []
        if not drill_id or not evidence:
            continue
        targets[drill_id] = REPO_ROOT / str(evidence[0])
    return targets


def _build_operator_payload(drill_id: str, *, actor: str) -> dict[str, Any]:
    return {
        "actor": actor,
        "session_id": f"codex-governance-refresh:{drill_id}",
        "correlation_id": f"codex-governance-refresh:{drill_id}",
        "reason": f"Refresh governance drill evidence from live runtime for {drill_id}",
    }


def _fetch_runtime_snapshot(ssh_target: str, base_url: str) -> dict[str, Any]:
    return _remote_request_json(
        ssh_target,
        method="GET",
        url=f"{base_url}/v1/operator/governance/drills",
    )


def _rehearse_runtime_drill(ssh_target: str, base_url: str, drill_id: str, *, actor: str) -> dict[str, Any]:
    response = _remote_request_json(
        ssh_target,
        method="POST",
        url=f"{base_url}/v1/operator/governance/drills/{drill_id}/rehearse",
        payload=_build_operator_payload(drill_id, actor=actor),
    )
    drill = dict(response.get("drill") or {})
    if not drill:
        raise RuntimeError(f"Runtime response for {drill_id} did not include a drill payload")
    return drill


def _artifact_from_snapshot(snapshot: dict[str, Any], drill_id: str) -> dict[str, Any]:
    for drill in snapshot.get("drills", []):
        if not isinstance(drill, dict):
            continue
        if str(drill.get("drill_id") or "").strip() != drill_id:
            continue
        artifact = dict(drill.get("artifact_payload") or {})
        if artifact:
            return artifact
        raise RuntimeError(f"Runtime snapshot for {drill_id} is missing artifact_payload")
    raise RuntimeError(f"Runtime snapshot did not include drill {drill_id}")


def refresh_drill(
    ssh_target: str,
    base_url: str,
    drill_id: str,
    *,
    actor: str,
    targets: dict[str, Path],
) -> dict[str, Any]:
    artifact = _rehearse_runtime_drill(ssh_target, base_url, drill_id, actor=actor)
    target_path = targets.get(drill_id)
    if target_path is None:
        raise RuntimeError(f"No local evidence target registered for drill {drill_id}")
    dump_json(target_path, artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-target", default=DEFAULT_SSH_TARGET)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--drill-id", dest="drill_ids", action="append")
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args()

    targets = _registry_targets()
    requested = args.drill_ids or list(DEFAULT_DRILLS)
    unknown = sorted(drill_id for drill_id in requested if drill_id not in targets)
    if unknown:
        print(f"Unknown drill ids: {', '.join(unknown)}", file=sys.stderr)
        return 2

    refreshed: list[dict[str, Any]] = []
    snapshot_cache: dict[str, Any] | None = None
    for drill_id in requested:
        if args.snapshot_only:
            if snapshot_cache is None:
                snapshot_cache = _fetch_runtime_snapshot(args.ssh_target, args.base_url)
            artifact = _artifact_from_snapshot(snapshot_cache, drill_id)
        else:
            try:
                artifact = refresh_drill(
                    args.ssh_target,
                    args.base_url,
                    drill_id,
                    actor=args.actor,
                    targets=targets,
                )
            except Exception:
                if snapshot_cache is None:
                    snapshot_cache = _fetch_runtime_snapshot(args.ssh_target, args.base_url)
                artifact = _artifact_from_snapshot(snapshot_cache, drill_id)
                dump_json(targets[drill_id], artifact)
        refreshed.append(
            {
                "drill_id": drill_id,
                "passed": bool(artifact.get("passed")),
                "status": str(artifact.get("status") or ""),
                "trigger_time": artifact.get("trigger_time"),
                "detail": str(artifact.get("detail") or ""),
                "path": targets[drill_id].as_posix(),
            }
        )

    print(json.dumps({"refreshed": refreshed}, indent=2))
    return 0 if all(item["passed"] for item in refreshed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
