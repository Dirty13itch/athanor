#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from proof_workspace_contract import devstack_proof_root, devstack_proof_sync_paths, proof_workspace_sync_paths


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
PROOF_MANIFEST_PATH = REPO_ROOT / "reports" / "truth-inventory" / "proof-workspace-manifest.json"
RUNTIME_SYNC_STATE_PATH = Path.home() / ".athanor" / "runtime-ownership" / "dev-runtime-repo-sync-state.json"
DOC_LIFECYCLE_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "docs-lifecycle-registry.json"
DEVSTACK_LOCAL_ROOT = Path("/mnt/c/athanor-devstack")
DEV_RUNTIME_REPO_ROOT = "/home/shaun/repos/athanor"
FOUNDRY_PROOF_ROOT = "/opt/athanor"
DEV_HOST = "dev"
FOUNDRY_HOST = "foundry"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pick_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _stream_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _run(command: list[str], *, timeout: int = 20) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        input=None,
        check=False,
        timeout=timeout,
    )
    return int(getattr(proc, "returncode", 1)), _stream_text(getattr(proc, "stdout", "")).strip(), _stream_text(getattr(proc, "stderr", "")).strip()


def _run_with_input(command: list[str], *, input_text: str, timeout: int = 20) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        input=input_text,
        check=False,
        timeout=timeout,
    )
    return int(getattr(proc, "returncode", 1)), _stream_text(getattr(proc, "stdout", "")).strip(), _stream_text(getattr(proc, "stderr", "")).strip()


def _git_head(path: Path) -> str | None:
    code, stdout, _ = _run(["git", "-C", str(path), "rev-parse", "HEAD"])
    return stdout if code == 0 and stdout else None


def _git_dirty(path: Path) -> bool | None:
    code, stdout, _ = _run(["git", "-C", str(path), "status", "--porcelain"])
    if code != 0:
        return None
    return bool(stdout.strip())


def _remote_git_head(host: str, path: str) -> str | None:
    code, stdout, _ = _run(["ssh", host, "git", "-C", path, "rev-parse", "HEAD"], timeout=25)
    return stdout if code == 0 and stdout else None


def _remote_git_dirty(host: str, path: str) -> bool | None:
    code, stdout, _ = _run(["ssh", host, "git", "-C", path, "status", "--porcelain"], timeout=25)
    if code != 0:
        return None
    return bool(stdout.strip())


def _remote_git_status_lines(host: str, path: str) -> list[str] | None:
    code, stdout, _ = _run(["ssh", host, "git", "-C", path, "status", "--porcelain"], timeout=25)
    if code != 0:
        return None
    return [line for line in stdout.splitlines() if line.strip()]


def _discover_remote_proof_root(host: str, candidate_root: str) -> str:
    normalized = candidate_root.strip().rstrip("/")
    if not normalized:
        return candidate_root

    candidates = [
        normalized,
        f"{normalized}/live",
        f"{normalized}/current",
        f"{normalized}/runtime",
        f"{normalized}/app",
        "/srv/athanor/live",
        "/srv/athanor",
        "/opt/athanor/live",
        "/opt/athanor/current",
        "/opt/athanor/runtime",
    ]
    unique_candidates: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        unique_candidates.append(item)

    candidate_args = " ".join(shlex.quote(item) for item in unique_candidates)
    probe_script = (
        "for dir in "
        + candidate_args
        + "; do "
        + 'git -C "$dir" rev-parse --show-toplevel >/dev/null 2>&1 && { git -C "$dir" rev-parse --show-toplevel; exit 0; }; '
        + "done; exit 1"
    )
    code, stdout, _ = _run(["ssh", host, "bash", "-lc", probe_script], timeout=30)
    discovered = stdout.strip()
    return discovered or normalized if code == 0 else normalized


def _git_subset_status(path: Path, paths: tuple[str, ...]) -> str | None:
    if not paths:
        return ""
    code, stdout, _ = _run(
        [
            "git",
            "-C",
            str(path),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *paths,
        ],
        timeout=45,
    )
    if code != 0:
        return None
    return stdout


def _remote_git_subset_status(host: str, path: str, paths: tuple[str, ...]) -> str | None:
    if not paths:
        return ""
    code, stdout, _ = _run(
        [
            "ssh",
            host,
            "git",
            "-C",
            path,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *paths,
        ],
        timeout=45,
    )
    if code != 0:
        return None
    return stdout


def _fingerprint_hash(parts: list[tuple[str, str | None]]) -> str | None:
    if any(value is None for _, value in parts):
        return None
    digest = hashlib.sha256()
    for key, value in parts:
        digest.update(f"{key}:{value or ''}\n".encode("utf-8"))
    return digest.hexdigest()


def _local_proof_manifest_payload(*, now_iso: str | None = None) -> dict[str, Any]:
    repo_paths = proof_workspace_sync_paths()
    devstack_paths = devstack_proof_sync_paths()
    devstack_root = DEVSTACK_LOCAL_ROOT
    repo_head = _git_head(REPO_ROOT)
    repo_status = _git_subset_status(REPO_ROOT, repo_paths)
    devstack_head = _git_head(devstack_root) if devstack_root.exists() else "missing"
    devstack_status = _git_subset_status(devstack_root, devstack_paths) if devstack_root.exists() else "missing"
    manifest_hash = _fingerprint_hash(
        [
            ("repo_head", repo_head),
            ("repo_status", repo_status),
            ("devstack_head", devstack_head),
            ("devstack_status", devstack_status),
        ]
    ) or "missing"
    return {
        "generated_at": now_iso or _iso_now(),
        "manifest_hash": manifest_hash,
        "repo_head": repo_head,
        "repo_status_available": repo_status is not None,
        "devstack_head": devstack_head,
        "devstack_status_available": devstack_status is not None,
        "source_artifacts": {
            "proof_workspace_contract": str(REPO_ROOT / "scripts" / "proof_workspace_contract.py"),
            "proof_workspace_manifest": str(PROOF_MANIFEST_PATH),
        },
    }


def _local_proof_manifest_hash() -> str:
    return str(_local_proof_manifest_payload().get("manifest_hash") or "missing")


def _managed_generated_doc_paths() -> set[str]:
    payload = _load_optional_json(DOC_LIFECYCLE_REGISTRY_PATH)
    managed: set[str] = set()
    for item in list(payload.get("documents") or []):
        if not isinstance(item, dict) or item.get("generated") is not True:
            continue
        path = str(item.get("path") or "").strip().replace("\\", "/")
        if path:
            managed.add(path)
    return managed


def _status_paths(status_lines: list[str] | None) -> list[str]:
    paths: list[str] = []
    for line in status_lines or []:
        if len(line) < 3:
            continue
        if len(line) >= 3 and line[2] == " ":
            path = line[3:].strip()
        elif len(line) >= 2 and line[1] == " ":
            path = line[2:].strip()
        else:
            path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path.replace("\\", "/"))
    return paths


def _is_managed_generated_runtime_path(path: str, generated_docs: set[str]) -> bool:
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return False
    if normalized in generated_docs:
        return True
    if normalized.startswith("reports/truth-inventory/"):
        return True
    if normalized.startswith("reports/ralph-loop/"):
        return True
    if normalized == "audit/automation/contract-healer-latest.json":
        return True
    if normalized == "config/automation-backbone/completion-program-registry.json":
        return True
    return False


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> None:
    rendered = _json_render(payload)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def _read_nested_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current.strip() if isinstance(current, str) and current.strip() else None


def _remote_artifact_manifest_hash(host: str, remote_root: str) -> str | None:
    remote_script = f"""
from __future__ import annotations

import json
from pathlib import Path

remote_root = Path({remote_root!r})
candidates = (
    (remote_root / "reports" / "truth-inventory" / "proof-workspace-manifest.json", ("manifest_hash",)),
    (remote_root / "reports" / "truth-inventory" / "runtime-parity.json", ("expected_local_proof_manifest_hash",)),
)
for path, keys in candidates:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            current = None
            break
        current = current.get(key)
    if isinstance(current, str) and current.strip():
        print(current.strip())
        raise SystemExit(0)
raise SystemExit(1)
"""
    code, stdout, _ = _run_with_input(["ssh", host, "python3", "-"], input_text=remote_script, timeout=30)
    return stdout if code == 0 and stdout else None


def _remote_proof_manifest_hash(host: str, remote_root: str, devstack_root_name: str) -> str | None:
    artifact_manifest_hash = _remote_artifact_manifest_hash(host, remote_root)
    if artifact_manifest_hash:
        return artifact_manifest_hash
    repo_paths = proof_workspace_sync_paths()
    devstack_paths = devstack_proof_sync_paths()
    remote_devstack_root = f"{remote_root.rstrip('/')}/{devstack_root_name.strip('/')}"
    return _fingerprint_hash(
        [
            ("repo_head", _remote_git_head(host, remote_root)),
            ("repo_status", _remote_git_subset_status(host, remote_root, repo_paths)),
            ("devstack_head", _remote_git_head(host, remote_devstack_root)),
            ("devstack_status", _remote_git_subset_status(host, remote_devstack_root, devstack_paths)),
        ]
    )


def _semantic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized.pop("generated_at", None)
    if normalized.get("authority_source") == "governed_sync_state":
        normalized.pop("observed_checkout", None)
        normalized.pop("observed_local_proof_manifest_hash", None)
    return normalized


def _load_runtime_sync_state() -> dict[str, Any]:
    return _load_optional_json(RUNTIME_SYNC_STATE_PATH)


def _governed_sync_authority(sync_state: dict[str, Any], dev_commit: str | None) -> dict[str, Any] | None:
    source_commit = _pick_string(sync_state.get("source_commit"))
    source_root = _pick_string(sync_state.get("source_root"))
    source_manifest_hash = _pick_string(sync_state.get("source_proof_manifest_hash"))
    synced_at = _pick_string(sync_state.get("synced_at"))
    if not (
        source_commit
        and source_manifest_hash
        and sync_state.get("source_clean") is True
        and dev_commit
        and source_commit == dev_commit
    ):
        return None
    return {
        "repo_root": source_root or str(REPO_ROOT),
        "commit": source_commit,
        "dirty": False,
        "manifest_hash": source_manifest_hash,
        "synced_at": synced_at,
    }


def build_payload(*, existing_payload: dict[str, Any] | None = None, now_iso: str | None = None) -> dict[str, Any]:
    existing_payload = dict(existing_payload or {})
    now_iso = now_iso or _iso_now()

    observed_checkout_commit = _git_head(REPO_ROOT)
    observed_checkout_dirty = _git_dirty(REPO_ROOT)
    dev_commit = _remote_git_head(DEV_HOST, DEV_RUNTIME_REPO_ROOT)
    dev_dirty = _remote_git_dirty(DEV_HOST, DEV_RUNTIME_REPO_ROOT)
    dev_status_lines = _remote_git_status_lines(DEV_HOST, DEV_RUNTIME_REPO_ROOT) if dev_dirty else []
    proof_manifest_hash = _local_proof_manifest_hash()
    proof_manifest_payload = {
        **_local_proof_manifest_payload(now_iso=now_iso),
        "manifest_hash": proof_manifest_hash,
    }
    _write_json_if_changed(PROOF_MANIFEST_PATH, proof_manifest_payload)
    sync_state = _load_runtime_sync_state()
    governed_authority = _governed_sync_authority(sync_state, dev_commit)
    authority_source = "local_checkout"
    desk_repo_root = str(REPO_ROOT)
    desk_commit = observed_checkout_commit
    desk_dirty = observed_checkout_dirty
    local_manifest_hash = proof_manifest_hash
    if governed_authority is not None:
        authority_source = "governed_sync_state"
        desk_repo_root = str(governed_authority["repo_root"])
        desk_commit = str(governed_authority["commit"])
        desk_dirty = False
        local_manifest_hash = str(governed_authority["manifest_hash"])
    managed_generated_docs = _managed_generated_doc_paths()
    dev_dirty_paths = _status_paths(dev_status_lines) if dev_status_lines is not None else []
    dev_generated_surface_only = bool(dev_dirty_paths) and all(
        _is_managed_generated_runtime_path(path, managed_generated_docs) for path in dev_dirty_paths
    )
    foundry_proof_root = _discover_remote_proof_root(FOUNDRY_HOST, FOUNDRY_PROOF_ROOT)
    foundry_manifest_hash = _remote_proof_manifest_hash(FOUNDRY_HOST, foundry_proof_root, devstack_proof_root())

    desk_to_dev_commit_match = bool(desk_commit) and bool(dev_commit) and desk_commit == dev_commit and desk_dirty is False
    dev_managed_generated_drift = desk_to_dev_commit_match and dev_dirty is True and dev_generated_surface_only
    desk_to_dev_match = (
        desk_to_dev_commit_match
        and (dev_dirty is False or dev_managed_generated_drift)
    )
    proof_match = bool(foundry_manifest_hash) and foundry_manifest_hash == local_manifest_hash

    if dev_commit is None or dev_dirty is None:
        drift_class = "runtime_config_drift"
        detail = "DEV runtime workspace state is unavailable."
    elif dev_managed_generated_drift:
        drift_class = "generated_surface_drift"
        detail = "DEV controller workspace matches the governed authority commit, but live runtime regenerated managed truth artifacts."
    elif not desk_to_dev_match:
        drift_class = "repo_drift"
        detail = "DESK repo state and DEV controller workspace are not aligned."
    elif foundry_manifest_hash is None:
        drift_class = "runtime_config_drift"
        detail = "FOUNDRY proof workspace manifest is unavailable."
    elif not proof_match:
        drift_class = "proof_workspace_drift"
        detail = "FOUNDRY proof workspace manifest does not match the local proof manifest."
    else:
        drift_class = "clean"
        detail = "DESK, DEV, and FOUNDRY proof surfaces are aligned."

    last_successful_desk_to_dev_sync = existing_payload.get("last_successful_desk_to_dev_sync")
    if governed_authority and governed_authority.get("synced_at"):
        last_successful_desk_to_dev_sync = governed_authority["synced_at"]
    elif desk_to_dev_match:
        last_successful_desk_to_dev_sync = last_successful_desk_to_dev_sync or now_iso

    last_successful_dev_to_foundry_sync = existing_payload.get("last_successful_dev_to_foundry_sync")
    if proof_match and drift_class in {"clean", "generated_surface_drift"}:
        last_successful_dev_to_foundry_sync = last_successful_dev_to_foundry_sync or now_iso

    return {
        "generated_at": now_iso,
        "controller_host": DEV_HOST,
        "execution_host": FOUNDRY_HOST,
        "authority_source": authority_source,
        "drift_class": drift_class,
        "detail": detail,
        "desk": {
            "repo_root": desk_repo_root,
            "commit": desk_commit,
            "dirty": desk_dirty,
            "available": desk_commit is not None and desk_dirty is not None,
        },
        "observed_checkout": {
            "repo_root": str(REPO_ROOT),
            "commit": observed_checkout_commit,
            "dirty": observed_checkout_dirty,
            "available": observed_checkout_commit is not None and observed_checkout_dirty is not None,
        },
        "dev": {
            "workspace_root": DEV_RUNTIME_REPO_ROOT,
            "commit": dev_commit,
            "dirty": dev_dirty,
            "available": dev_commit is not None and dev_dirty is not None,
            "dirty_path_count": len(dev_dirty_paths),
            "dirty_paths_sample": dev_dirty_paths[:20],
            "generated_surface_only": dev_generated_surface_only,
        },
        "foundry": {
            "proof_workspace_root": foundry_proof_root,
            "manifest_hash": foundry_manifest_hash,
            "available": foundry_manifest_hash is not None,
        },
        "expected_local_proof_manifest_hash": local_manifest_hash,
        "observed_local_proof_manifest_hash": proof_manifest_hash,
        "last_successful_desk_to_dev_sync": last_successful_desk_to_dev_sync,
        "last_successful_dev_to_foundry_sync": last_successful_dev_to_foundry_sync,
        "source_artifacts": {
            "runtime_parity": str(OUTPUT_PATH),
            "proof_workspace_contract": str(REPO_ROOT / "scripts" / "proof_workspace_contract.py"),
            "proof_workspace_manifest": str(PROOF_MANIFEST_PATH),
            "runtime_sync_state": str(RUNTIME_SYNC_STATE_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor repo/runtime/proof parity artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when runtime-parity.json is stale.")
    args = parser.parse_args()

    existing_payload = _load_optional_json(OUTPUT_PATH)
    payload = build_payload(existing_payload=existing_payload)
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if args.check:
        if not OUTPUT_PATH.exists() or _semantic_payload(existing_payload) != _semantic_payload(payload):
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
