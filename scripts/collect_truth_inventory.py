from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from truth_inventory import (
    BOOTSTRAP_REPORTS_DIR,
    CONFIG_DIR,
    IMPLEMENTATION_AUTHORITY_ROOT,
    PROVIDER_USAGE_EVIDENCE_PATH,
    REPO_ROOT,
    TRUTH_SNAPSHOT_PATH,
    VAULT_LITELLM_ENV_AUDIT_PATH,
    VAULT_REDIS_AUDIT_PATH,
    load_optional_json,
    load_registry,
    provider_index,
)
from runtime_env import runtime_env_status
from vault_litellm_env_audit import collect_vault_litellm_env_audit
from vault_redis_audit import collect_vault_redis_audit


ATHANOR_REPO_PROBE_FALLBACKS = [REPO_ROOT, Path("/home/shaun/repos/athanor")]
GIT_PROBE_TIMEOUT_SECONDS = 8
WINDOWS_GIT_CANDIDATES = [
    Path('/mnt/c/Program Files/Git/cmd/git.exe'),
    Path('/mnt/c/Program Files/Git/bin/git.exe'),
    Path('/mnt/c/Program Files/Git/mingw64/bin/git.exe'),
]


def _current_repo_probe_root() -> Path:
    for candidate in ATHANOR_REPO_PROBE_FALLBACKS:
        if candidate.exists():
            return candidate
    return REPO_ROOT


def _repo_runtime_prefixes() -> list[str]:
    prefixes = [
        '/home/shaun/repos/athanor/',
        REPO_ROOT.as_posix().rstrip('/') + '/',
        IMPLEMENTATION_AUTHORITY_ROOT.rstrip('/') + '/',
        IMPLEMENTATION_AUTHORITY_ROOT.replace('\\', '/').rstrip('/') + '/',
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for prefix in prefixes:
        if prefix not in seen:
            seen.add(prefix)
            deduped.append(prefix)
    return deduped


def _git_probe_context(path: Path) -> tuple[list[str], str]:
    normalized = path.as_posix()
    if normalized.startswith('/mnt/c/'):
        windows_path = 'C:\\' + normalized.removeprefix('/mnt/c/').replace('/', '\\')
        for candidate in WINDOWS_GIT_CANDIDATES:
            if candidate.exists():
                return [str(candidate)], windows_path
    return ['git'], normalized


def _run_git_capture(path: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    command, repo_path = _git_probe_context(path)
    try:
        return subprocess.run([*command, '-C', repo_path, *args], capture_output=True, text=True, timeout=GIT_PROBE_TIMEOUT_SECONDS, check=False)
    except Exception:
        return None


def _normalize_runtime_caller_path(path: str) -> str:
    normalized = str(path).strip().replace('\\', '/')
    for prefix in _repo_runtime_prefixes():
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    pending_cr = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            if pending_cr:
                chunk = b"\r" + chunk
                pending_cr = False
            if chunk.endswith(b"\r"):
                chunk = chunk[:-1]
                pending_cr = True
            digest.update(chunk.replace(b"\r\n", b"\n"))
    if pending_cr:
        digest.update(b"\r")
    return digest.hexdigest()


def _normalized_tree_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.is_file():
        return _normalized_file_sha256(path)

    digest = hashlib.sha256()
    for file_path in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative_path = file_path.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        normalized_sha = _normalized_file_sha256(file_path)
        if normalized_sha:
            digest.update(normalized_sha.encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _file_line_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def _annotate_governor_facade_probe(
    dev_runtime_probe: dict[str, Any],
    runtime_migrations: dict[str, Any],
) -> None:
    if not dev_runtime_probe.get("ok"):
        return
    detail = dev_runtime_probe.get("detail")
    if not isinstance(detail, dict):
        return
    governor_facade = detail.get("governor_facade")
    if not isinstance(governor_facade, dict):
        return

    migration = next(
        (
            entry
            for entry in runtime_migrations.get("migrations", [])
            if str(entry.get("id") or "") == "dev-governor-facade-8760-callers"
        ),
        None,
    )
    if not isinstance(migration, dict):
        return

    caller_specs = {
        str(caller.get("path") or "").strip(): caller
        for caller in migration.get("callers", [])
        if str(caller.get("path") or "").strip()
    }
    planned_callers = set(caller_specs)
    observed_callers = {
        _normalize_runtime_caller_path(path)
        for path in governor_facade.get("caller_files", [])
        if str(path).strip()
    }
    mapped_callers = sorted(observed_callers & planned_callers)
    unmapped_callers = sorted(observed_callers - planned_callers)
    implementation_ready_callers = sorted(
        str(caller.get("path") or "")
        for caller in migration.get("callers", [])
        if str(caller.get("path") or "").strip()
    )
    runtime_records_by_path = {
        _normalize_runtime_caller_path(str(record.get("normalized_path") or record.get("raw_path") or "")): record
        for record in governor_facade.get("caller_records", [])
        if isinstance(record, dict)
        and _normalize_runtime_caller_path(str(record.get("normalized_path") or record.get("raw_path") or ""))
    }

    runtime_backup_root = str(migration.get("runtime_backup_root") or "").rstrip("/")
    systemd_backup_target = str(migration.get("systemd_backup_target") or "")
    content_records: list[dict[str, Any]] = []
    content_state_counts: dict[str, int] = {}
    for caller_path in implementation_ready_callers:
        caller_spec = caller_specs.get(caller_path, {})
        runtime_record = runtime_records_by_path.get(caller_path, {})
        implementation_path = IMPLEMENTATION_AUTHORITY_ROOT / caller_path
        implementation_exists = implementation_path.is_file()
        implementation_sha256 = _file_sha256(implementation_path)
        implementation_normalized_sha256 = _normalized_file_sha256(implementation_path)
        runtime_exists = bool(runtime_record.get("exists"))
        runtime_sha256 = str(runtime_record.get("sha256") or "") or None
        runtime_normalized_sha256 = str(runtime_record.get("normalized_sha256") or "") or None
        observed_in_runtime_probe = caller_path in observed_callers
        configured_runtime_path = str(caller_spec.get("runtime_owner_path") or "")
        observed_runtime_path = str(runtime_record.get("runtime_path") or "")
        if not runtime_exists:
            content_state = "missing_runtime_file"
        elif not implementation_exists:
            content_state = "missing_implementation_file"
        elif runtime_normalized_sha256 == implementation_normalized_sha256:
            content_state = "content_match"
        else:
            content_state = "content_drift"
        line_ending_only_drift = bool(
            runtime_exists
            and implementation_exists
            and runtime_sha256
            and implementation_sha256
            and runtime_sha256 != implementation_sha256
            and runtime_normalized_sha256 == implementation_normalized_sha256
        )
        if content_state == "content_match":
            sync_decision = "already_synced"
        elif content_state == "content_drift":
            sync_decision = "backup_then_replace_runtime_copy"
        elif content_state == "missing_runtime_file":
            sync_decision = "create_runtime_copy_after_backup_root_check"
        else:
            sync_decision = "blocked_missing_implementation_copy"
        content_state_counts[content_state] = content_state_counts.get(content_state, 0) + 1
        content_records.append(
            {
                "path": caller_path,
                "sync_order": caller_spec.get("sync_order"),
                "sync_strategy": str(caller_spec.get("sync_strategy") or ""),
                "sync_decision": sync_decision,
                "observed_in_runtime_probe": observed_in_runtime_probe,
                "runtime_path": observed_runtime_path,
                "runtime_exists": runtime_exists,
                "runtime_sha256": runtime_sha256,
                "runtime_normalized_sha256": runtime_normalized_sha256,
                "runtime_size_bytes": runtime_record.get("size_bytes"),
                "runtime_line_count": runtime_record.get("line_count"),
                "runtime_path_matches_registry": bool(configured_runtime_path) and observed_runtime_path == configured_runtime_path,
                "runtime_owner_path": configured_runtime_path or observed_runtime_path or None,
                "implementation_path": str(implementation_path),
                "implementation_exists": implementation_exists,
                "implementation_sha256": implementation_sha256,
                "implementation_normalized_sha256": implementation_normalized_sha256,
                "implementation_size_bytes": implementation_path.stat().st_size if implementation_exists else None,
                "implementation_line_count": _file_line_count(implementation_path),
                "runtime_backup_root": runtime_backup_root or None,
                "runtime_backup_path": str(caller_spec.get("rollback_target") or ""),
                "rollback_target": str(caller_spec.get("rollback_target") or ""),
                "rollback_ready": bool(runtime_exists and caller_spec.get("rollback_target")),
                "content_state": content_state,
                "content_match": content_state == "content_match",
                "line_ending_only_drift": line_ending_only_drift,
            }
        )

    governor_facade["planned_caller_files"] = sorted(planned_callers)
    governor_facade["mapped_caller_files"] = mapped_callers
    governor_facade["unmapped_caller_files"] = unmapped_callers
    governor_facade["implementation_ready_caller_files"] = implementation_ready_callers
    governor_facade["migration_registry_id"] = str(migration.get("id") or "")
    governor_facade["mapped_caller_count"] = len(mapped_callers)
    governor_facade["unmapped_caller_count"] = len(unmapped_callers)
    governor_facade["runtime_backup_root"] = runtime_backup_root or None
    governor_facade["systemd_backup_target"] = systemd_backup_target or None
    governor_facade["caller_content_records"] = content_records
    governor_facade["content_state_counts"] = content_state_counts
    governor_facade["content_match_count"] = content_state_counts.get("content_match", 0)
    governor_facade["content_drift_count"] = content_state_counts.get("content_drift", 0)
    governor_facade["missing_runtime_file_count"] = content_state_counts.get("missing_runtime_file", 0)
    governor_facade["missing_implementation_file_count"] = content_state_counts.get("missing_implementation_file", 0)
    governor_facade["sync_required_count"] = sum(
        1 for record in content_records if str(record.get("sync_decision") or "").startswith(("backup_", "create_"))
    )
    governor_facade["already_synced_count"] = sum(
        1 for record in content_records if str(record.get("sync_decision") or "") == "already_synced"
    )
    governor_facade["blocked_sync_count"] = sum(
        1 for record in content_records if str(record.get("sync_decision") or "") == "blocked_missing_implementation_copy"
    )
    governor_facade["observed_runtime_reference_count"] = sum(
        1 for record in content_records if bool(record.get("observed_in_runtime_probe"))
    )
    governor_facade["not_observed_runtime_reference_count"] = sum(
        1 for record in content_records if not bool(record.get("observed_in_runtime_probe"))
    )


def _run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - best effort collector
        return {
            "ok": False,
            "command": command,
            "detail": str(exc),
        }

    output = (completed.stdout or completed.stderr or "").strip().splitlines()
    first_line = output[0][:240] if output else ""
    return {
        "ok": completed.returncode == 0,
        "command": command,
        "returncode": completed.returncode,
        "detail": first_line,
    }


def _run_inline_python_json(command: list[str], script: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [*command, "python3", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - best effort collector
        return {"ok": False, "detail": str(exc)}

    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        failure_detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return {
            "ok": False,
            "detail": failure_detail[0][:240] if failure_detail else f"returncode={completed.returncode}",
        }

    try:
        return {"ok": True, "detail": json.loads(output) if output else {}}
    except json.JSONDecodeError:
        return {"ok": False, "detail": "invalid json from remote probe"}


def _run_json_stdout_command(command: list[str], script: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            input=script,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - best effort collector
        return {"ok": False, "detail": str(exc)}

    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        failure_detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return {
            "ok": False,
            "detail": failure_detail[0][:240] if failure_detail else f"returncode={completed.returncode}",
        }

    try:
        return {"ok": True, "detail": json.loads(output) if output else {}}
    except json.JSONDecodeError:
        return {"ok": False, "detail": "invalid json from command output"}


def _probe_dev_runtime(topology: dict[str, Any], runtime_migrations: dict[str, Any]) -> dict[str, Any]:
    dev_host = next(
        (str(node.get("default_host") or "") for node in topology.get("nodes", []) if str(node.get("id") or "") == "dev"),
        "",
    )
    ssh_targets = ["dev"]
    if dev_host:
        ssh_targets.append(f"shaun@{dev_host}")
    migration = next(
        (
            entry
            for entry in runtime_migrations.get("migrations", [])
            if str(entry.get("id") or "") == "dev-governor-facade-8760-callers"
        ),
        None,
    )
    planned_callers = [
        str(caller.get("path") or "").strip()
        for caller in (migration or {}).get("callers", [])
        if str(caller.get("path") or "").strip()
    ]
    planned_callers_json = json.dumps(planned_callers)

    runtime_script = """
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import shutil

PLANNED_CALLERS = __PLANNED_CALLERS__

result = {
    "paths": {},
    "repo_git_head": None,
    "repo_dirty_count": 0,
    "repo_status_sample": [],
    "opt_entries": [],
    "state_entries": [],
    "cron_files": [],
    "user_crontab_job_count": 0,
    "user_crontab_inline_env_keys": [],
    "systemd_units": [],
    "heartbeat_bundle": {
        "script_path": "/opt/athanor/heartbeat/node-heartbeat.py",
        "script_exists": False,
        "script_normalized_sha256": None,
        "env_path": "/opt/athanor/heartbeat/env",
        "env_exists": False,
        "venv_python_path": "/opt/athanor/heartbeat/venv/bin/python3",
        "venv_python_exists": False,
    },
    "governor_facade": {
        "listener_present": False,
        "listener_lines": [],
        "health_status_code": None,
        "unit_present": False,
        "unit_matches": [],
        "runtime_ref_hits": [],
        "caller_ref_hits": [],
        "caller_files": [],
        "recent_queue_request_count": 0,
        "recent_health_request_count": 0,
        "recent_journal_lines": [],
    },
}

def _normalized_file_sha256(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    pending_cr = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            if pending_cr:
                chunk = b"\\r" + chunk
                pending_cr = False
            if chunk.endswith(b"\\r"):
                chunk = chunk[:-1]
                pending_cr = True
            digest.update(chunk.replace(b"\\r\\n", b"\\n"))
    if pending_cr:
        digest.update(b"\\r")
    return digest.hexdigest()

repo = _current_repo_probe_root()
for probe_path in [repo.as_posix(), "/opt/athanor", "/home/shaun/.athanor", "/var/log/athanor", "/home/shaun/repos/athanor"]:
    result["paths"][probe_path] = Path(probe_path).exists()

if repo.exists():
    proc = _run_git_capture(repo, "rev-parse", "--short", "HEAD")
    result["repo_git_head"] = proc.stdout.strip() if proc and proc.returncode == 0 and proc.stdout.strip() else None
    status = _run_git_capture(repo, "status", "--short")
    status_lines = [line.rstrip() for line in status.stdout.splitlines() if line.strip()] if status and status.returncode == 0 else []
    result["repo_dirty_count"] = len(status_lines)
    result["repo_status_sample"] = status_lines[:20]

opt_path = Path("/opt/athanor")
if opt_path.exists():
    result["opt_entries"] = sorted(entry.name for entry in opt_path.iterdir())[:20]

state_path = Path("/home/shaun/.athanor")
if state_path.exists():
    result["state_entries"] = sorted(entry.name for entry in state_path.iterdir())[:30]

heartbeat_bundle = result["heartbeat_bundle"]
heartbeat_script = Path(str(heartbeat_bundle["script_path"]))
heartbeat_bundle["script_exists"] = heartbeat_script.is_file()
if heartbeat_script.is_file():
    heartbeat_bundle["script_normalized_sha256"] = _normalized_file_sha256(heartbeat_script)
heartbeat_bundle["env_exists"] = Path(str(heartbeat_bundle["env_path"])).exists()
heartbeat_bundle["venv_python_exists"] = Path(str(heartbeat_bundle["venv_python_path"])).exists()

for cron_dir in [Path("/etc/cron.d"), Path("/etc/cron.daily")]:
    if cron_dir.exists():
        for entry in sorted(cron_dir.iterdir()):
            if "athanor" in entry.name:
                result["cron_files"].append(str(entry))

cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
job_lines = [line for line in cron.stdout.splitlines() if line.strip() and not line.strip().startswith("#")]
result["user_crontab_job_count"] = len(job_lines)
env_keys = set()
for line in job_lines:
    for part in line.split():
        if "=" in part:
            key = part.split("=", 1)[0]
            if key.isupper() and key not in {"PATH", "SHELL"}:
                env_keys.add(key)
result["user_crontab_inline_env_keys"] = sorted(env_keys)

units = subprocess.run(["systemctl", "list-unit-files", "athanor-*", "--no-legend", "--no-pager"], capture_output=True, text=True, check=False)
for raw in units.stdout.splitlines():
    parts = raw.split()
    if not parts:
        continue
    unit = parts[0]
    cat = subprocess.run(["systemctl", "cat", unit], capture_output=True, text=True, check=False)
    envfile_count = 0
    environment_count = 0
    working_directories = []
    exec_starts = []
    contains_governor_ref = unit == "athanor-governor.service"
    for line in cat.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("EnvironmentFile="):
            envfile_count += 1
        elif stripped.startswith("Environment="):
            environment_count += 1
        elif stripped.startswith("WorkingDirectory="):
            working_directories.append(stripped.split("=", 1)[1])
        elif stripped.startswith("ExecStart="):
            exec_starts.append(stripped.split("=", 1)[1])
        if "8760" in stripped or "governor" in stripped:
            contains_governor_ref = True
    unit_record = {
        "unit": unit,
        "unit_file_state": parts[1] if len(parts) > 1 else "",
        "environment_file_count": envfile_count,
        "environment_count": environment_count,
        "working_directories": working_directories[:3],
        "exec_starts": exec_starts[:2],
    }
    result["systemd_units"].append(unit_record)
    if contains_governor_ref:
        result["governor_facade"]["unit_present"] = True
        result["governor_facade"]["unit_matches"].append(unit_record)

listener = subprocess.run(
    ["bash", "-lc", "ss -ltnp 2>/dev/null | grep 8760 || true"],
    capture_output=True,
    text=True,
    check=False,
)
listener_lines = [line.strip() for line in listener.stdout.splitlines() if line.strip()]
result["governor_facade"]["listener_present"] = bool(listener_lines)
result["governor_facade"]["listener_lines"] = listener_lines[:10]
retired_runtime_facade_paths = {
    "services/governor/main.py",
    "/home/shaun/repos/athanor/services/governor/main.py",
}

health = subprocess.run(
    ["bash", "-lc", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8760/health || true"],
    capture_output=True,
    text=True,
    check=False,
)
health_status_code = (health.stdout or "").strip()
if health_status_code and health_status_code != "000":
    result["governor_facade"]["health_status_code"] = health_status_code

if shutil.which("rg"):
    ref_command = (
        'rg -n --glob "!**/node_modules/**" --glob "!**/.venv/**" --glob "!**/semantic-router-venv/**" --glob "!**/site-packages/**" --glob "!**/*.tsbuildinfo" '
        '":8760|athanor-governor|dispatch-and-run|/queue|/health" '
        '/home/shaun/repos/athanor/services/governor /home/shaun/repos/athanor/services/gateway /home/shaun/repos/athanor/services/sentinel /home/shaun/repos/athanor/services/cluster_config.py /home/shaun/repos/athanor/scripts/drift-check.sh /home/shaun/repos/athanor/scripts/smoke-test.sh /home/shaun/repos/athanor/scripts/contract-tests.sh /home/shaun/repos/athanor/scripts/subscription-status.sh /opt/athanor/scripts /home/shaun/.athanor/systemd /etc/systemd/system/athanor-* /etc/cron.d/athanor-* 2>/dev/null '
        '| head -n 40'
    )
else:
    ref_command = (
        'grep -R -n -E ":8760|athanor-governor|dispatch-and-run|/queue|/health" '
        '/home/shaun/repos/athanor/services/governor /home/shaun/repos/athanor/services/gateway /home/shaun/repos/athanor/services/sentinel /home/shaun/repos/athanor/services/cluster_config.py /home/shaun/repos/athanor/scripts/drift-check.sh /home/shaun/repos/athanor/scripts/smoke-test.sh /home/shaun/repos/athanor/scripts/contract-tests.sh /home/shaun/repos/athanor/scripts/subscription-status.sh /opt/athanor/scripts /home/shaun/.athanor/systemd /etc/systemd/system/athanor-* /etc/cron.d/athanor-* 2>/dev/null '
        '| grep -v "/node_modules/" | grep -v "/.venv/" | grep -v "/semantic-router-venv/" | grep -v "/site-packages/" | grep -v "\\\\.tsbuildinfo:" | head -n 40'
    )
runtime_refs = subprocess.run(
    ["bash", "-lc", ref_command],
    capture_output=True,
    text=True,
    check=False,
)
all_ref_hits = [
    line.strip()
    for line in runtime_refs.stdout.splitlines()
    if line.strip() and line.split(":", 1)[0] not in retired_runtime_facade_paths
][:40]
result["governor_facade"]["runtime_ref_hits"] = all_ref_hits
caller_command = (
    f'(git -C {repo_service_root} grep -n -E "8760|dispatch-and-run|ATHANOR_GOVERNOR_URL" -- services scripts 2>/dev/null; '
    'grep -R -n -E "8760|dispatch-and-run|ATHANOR_GOVERNOR_URL" '
    '/opt/athanor/scripts /home/shaun/.athanor/systemd /etc/systemd/system/athanor-* /etc/cron.d/athanor-* 2>/dev/null || true) '
    '| head -n 60'
)
caller_refs = subprocess.run(
    ["bash", "-lc", caller_command],
    capture_output=True,
    text=True,
    check=False,
)
caller_hits = []
caller_files = []
for line in [line.strip() for line in caller_refs.stdout.splitlines() if line.strip()][:60]:
    if line.startswith("Binary file "):
        continue
    path = line.split(":", 1)[0]
    if path in retired_runtime_facade_paths:
        continue
    if path.endswith("governor.db") or path.endswith("governor.db.bak"):
        continue
    caller_hits.append(line)
    caller_files.append(path)
result["governor_facade"]["caller_ref_hits"] = caller_hits[:20]
result["governor_facade"]["caller_files"] = sorted(set(caller_files))[:20]
caller_records = []
for raw_path in sorted(set(caller_files))[:20]:
    normalized_path = _normalize_runtime_caller_path(raw_path)
    runtime_path = raw_path
    if not raw_path.startswith("/"):
        runtime_path = str(repo / raw_path)
    elif normalized_path != raw_path:
        runtime_path = str(repo / normalized_path)
    runtime_file = Path(runtime_path)
    record = {
        "raw_path": raw_path,
        "normalized_path": normalized_path,
        "runtime_path": runtime_path,
        "exists": runtime_file.is_file(),
    }
    if runtime_file.is_file():
        record["size_bytes"] = runtime_file.stat().st_size
        record["line_count"] = sum(1 for _ in runtime_file.open("rb"))
        record["sha256"] = hashlib.sha256(runtime_file.read_bytes()).hexdigest()
        record["normalized_sha256"] = _normalized_file_sha256(runtime_file)
    caller_records.append(record)
observed_paths = {str(record.get("normalized_path") or "") for record in caller_records}
for planned_path in PLANNED_CALLERS:
    if planned_path in observed_paths:
        continue
    runtime_file = repo / planned_path
    record = {
        "raw_path": planned_path,
        "normalized_path": planned_path,
        "runtime_path": str(runtime_file),
        "exists": runtime_file.is_file(),
    }
    if runtime_file.is_file():
        record["size_bytes"] = runtime_file.stat().st_size
        record["line_count"] = sum(1 for _ in runtime_file.open("rb"))
        record["sha256"] = hashlib.sha256(runtime_file.read_bytes()).hexdigest()
        record["normalized_sha256"] = _normalized_file_sha256(runtime_file)
    caller_records.append(record)
result["governor_facade"]["caller_records"] = caller_records

journal = subprocess.run(
    ["bash", "-lc", "journalctl -u athanor-governor --since '7 days ago' --no-pager 2>/dev/null | tail -n 40"],
    capture_output=True,
    text=True,
    check=False,
)
journal_lines = [line.strip() for line in journal.stdout.splitlines() if line.strip()][:40]
result["governor_facade"]["recent_journal_lines"] = journal_lines
result["governor_facade"]["recent_queue_request_count"] = sum('GET /queue ' in line for line in journal_lines)
result["governor_facade"]["recent_health_request_count"] = sum('GET /health ' in line for line in journal_lines)

print(json.dumps(result))
    """.strip().replace("__PLANNED_CALLERS__", planned_callers_json)

    attempts: list[dict[str, Any]] = []
    for target in ssh_targets:
        result = _run_inline_python_json(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target],
            runtime_script,
        )
        attempts.append({"target": target, "detail": result.get("detail"), "ok": result.get("ok")})
        if result.get("ok"):
            detail = dict(result.get("detail") or {})
            heartbeat_bundle = detail.get("heartbeat_bundle")
            if isinstance(heartbeat_bundle, dict):
                implementation_path = REPO_ROOT / "scripts" / "node-heartbeat.py"
                implementation_exists = implementation_path.is_file()
                heartbeat_bundle["implementation_path"] = str(implementation_path)
                heartbeat_bundle["implementation_exists"] = implementation_exists
                if implementation_exists:
                    heartbeat_bundle["implementation_normalized_sha256"] = _normalized_file_sha256(
                        implementation_path
                    )
                implementation_sha = str(heartbeat_bundle.get("implementation_normalized_sha256") or "")
                deploy_sha = str(heartbeat_bundle.get("script_normalized_sha256") or "")
                heartbeat_bundle["implementation_matches_deploy_root"] = bool(
                    implementation_sha and deploy_sha and implementation_sha == deploy_sha
                )
                detail["heartbeat_bundle"] = heartbeat_bundle
            return {
                "ok": True,
                "target": target,
                "detail": detail,
            }
    return {"ok": False, "target": ssh_targets[0], "detail": "unable to reach DEV via ssh", "attempts": attempts}


def _probe_local_tools() -> list[dict[str, Any]]:
    inventory = load_registry("tooling-inventory.json")
    hostname = os.environ.get("COMPUTERNAME") or socket.gethostname()
    normalized = hostname.upper()
    if normalized.startswith("DESK"):
        host_id = "desk"
    elif normalized.startswith("DEV"):
        host_id = "dev"
    else:
        host_id = ""

    host_entry = next((entry for entry in inventory.get("hosts", []) if entry.get("id") == host_id), None)
    if host_entry is None:
        return []

    records: list[dict[str, Any]] = []
    for tool in host_entry.get("tools", []):
        command = str(tool.get("command") or "").strip()
        resolved = shutil.which(command) if command else None
        record = {
            "tool_id": tool.get("tool_id"),
            "expected_status": tool.get("status"),
            "provider_id": tool.get("provider_id"),
            "command": command,
            "resolved_path": resolved,
        }
        if resolved:
            record["probe"] = _run_command([resolved, "--version"])
        else:
            record["probe"] = {"ok": False, "detail": "command not found"}
        records.append(record)
    return records


async def _probe_urls(urls: list[tuple[str, str]]) -> list[dict[str, Any]]:
    async def _probe_one(probe_id: str, url: str) -> dict[str, Any]:
        result = await asyncio.to_thread(_fetch_url, url, False)
        payload = {"id": probe_id, "url": url, "ok": bool(result.get("ok"))}
        if "status_code" in result:
            payload["status_code"] = result["status_code"]
        if result.get("detail"):
            payload["detail"] = result["detail"]
        return payload

    return await asyncio.gather(*(_probe_one(probe_id, url) for probe_id, url in urls))


def _fetch_url(url: str, read_body: bool, timeout: float = 4.0) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "athanor-truth-inventory/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace") if read_body else ""
            return {
                "ok": int(response.status) < 500,
                "status_code": int(response.status),
                "body": body,
                "content_type": str(response.headers.get("content-type", "")),
            }
    except HTTPError as exc:  # pragma: no cover - network dependent
        body = exc.read().decode("utf-8", "replace") if read_body else ""
        return {
            "ok": int(exc.code) < 500,
            "status_code": int(exc.code),
            "detail": f"HTTPError: {exc.reason}",
            "body": body,
            "content_type": str(exc.headers.get("content-type", "")),
        }
    except URLError as exc:  # pragma: no cover - network dependent
        reason = exc.reason if exc.reason is not None else str(exc)
        return {"ok": False, "detail": f"URLError: {reason}"}
    except Exception as exc:  # pragma: no cover - network dependent
        detail = str(exc) or exc.__class__.__name__
        return {"ok": False, "detail": f"{exc.__class__.__name__}: {detail}"}


def _node_default_host(topology: dict[str, Any], node_id: str) -> str:
    return next(
        (
            str(node.get("default_host") or "")
            for node in topology.get("nodes", [])
            if str(node.get("id") or "") == node_id
        ),
        "",
    )


def _ssh_targets_for_node(topology: dict[str, Any], node_id: str) -> list[str]:
    default_host = _node_default_host(topology, node_id)
    targets = [node_id]
    if default_host:
        if node_id == "vault":
            targets.append(f"root@{default_host}")
        else:
            targets.append(f"shaun@{default_host}")
    return targets


def _extract_next_static_asset_paths(html: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r'(?:"|\')(/_next/static/[^"\']+)(?:"|\')', html):
        asset_path = str(match.group(1) or "").strip()
        if asset_path and asset_path not in paths:
            paths.append(asset_path)
        if len(paths) >= 4:
            break
    return paths


async def _probe_next_static_assets(base_url: str) -> dict[str, Any]:
    try:
        response = await asyncio.to_thread(_fetch_url, base_url, True, 10.0)
        html = response.get("body", "") if "text/html" in str(response.get("content_type", "")) else ""
        asset_paths = _extract_next_static_asset_paths(html)
        asset_results: list[dict[str, Any]] = []
        for asset_path in asset_paths:
            asset_url = urljoin(base_url, asset_path)
            asset_response = await asyncio.to_thread(_fetch_url, asset_url, False, 10.0)
            asset_result = {
                "path": asset_path,
                "url": asset_url,
                "ok": bool(asset_response.get("ok")),
            }
            if "status_code" in asset_response:
                asset_result["status_code"] = asset_response["status_code"]
            if asset_response.get("detail"):
                asset_result["detail"] = asset_response["detail"]
            asset_results.append(asset_result)
        payload = {
            "ok": bool(response.get("ok")),
            "asset_count": len(asset_paths),
            "asset_results": asset_results,
        }
        if "status_code" in response:
            payload["status_code"] = response["status_code"]
        if response.get("detail"):
            payload["detail"] = response["detail"]
        return payload
    except Exception as exc:  # pragma: no cover - network dependent
        return {
            "ok": False,
            "detail": f"{exc.__class__.__name__}: {str(exc) or exc.__class__.__name__}",
            "asset_count": 0,
            "asset_results": [],
        }


def _probe_dev_command_center_runtime(topology: dict[str, Any]) -> dict[str, Any]:
    probe_script = """
import json
import subprocess
import hashlib
from pathlib import Path, PurePosixPath

payload = {
    "deployment_mode": "unknown",
    "working_directory": "",
    "deployment_root": {
        "expected_path": "/opt/athanor/dashboard",
        "expected_exists": False,
        "runtime_repo_path": "/home/shaun/repos/athanor/projects/dashboard",
        "runtime_repo_exists": False,
        "runtime_repo_compose_exists": False,
        "runtime_repo_compose_controls_container": False,
        "observed_active_root": "",
        "drift": False,
    },
    "legacy_service": {
        "service": "athanor-dashboard.service",
        "service_present": False,
        "active_state": "unknown",
        "sub_state": "unknown",
        "exec_start": "",
        "fragment_path": "",
        "standalone_root": "",
        "standalone_static_present": False,
        "standalone_public_present": False,
        "project_static_present": False,
        "project_public_present": False,
        "root_cause_hint": "",
    },
    "container": {
        "name": "athanor-dashboard",
        "running": False,
        "image": "",
        "status": "",
        "ports": "",
    },
    "caddy": {
        "service": "caddy.service",
        "service_present": False,
        "active_state": "unknown",
        "sub_state": "unknown",
        "fragment_path": "",
    },
    "local_runtime_status_code": None,
    "local_canonical_status_code": None,
    "control_files": [],
}
def _exists(path):
    try:
        return path.exists()
    except Exception:
        return False
def _normalized_sha256(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    pending_cr = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            if pending_cr:
                if chunk.startswith(b"\\n"):
                    digest.update(b"\\n")
                    chunk = chunk[1:]
                else:
                    digest.update(b"\\r")
                pending_cr = False
            if chunk.endswith(b"\\r"):
                chunk, pending_cr = chunk[:-1], True
            chunk = chunk.replace(b"\\r\\n", b"\\n")
            digest.update(chunk)
    if pending_cr:
        digest.update(b"\\r")
    return digest.hexdigest()
legacy = payload["legacy_service"]
result = subprocess.run(
    [
        "systemctl",
        "show",
        "athanor-dashboard.service",
        "--property=LoadState,ActiveState,SubState,UnitFileState,WorkingDirectory,ExecStart,FragmentPath",
        "--no-pager",
    ],
    capture_output=True,
    text=True,
    check=False,
)
legacy["returncode"] = result.returncode
if result.returncode == 0:
    legacy["service_present"] = True
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "ActiveState":
            legacy["active_state"] = value or "unknown"
        elif key == "SubState":
            legacy["sub_state"] = value or "unknown"
        elif key == "UnitFileState":
            legacy["unit_file_state"] = value or "unknown"
        elif key == "WorkingDirectory":
            payload["working_directory"] = value
        elif key == "ExecStart":
            legacy["exec_start"] = value
        elif key == "FragmentPath":
            legacy["fragment_path"] = value
    working_directory = payload.get("working_directory") or ""
    if working_directory:
        root = Path(working_directory)
        standalone_root = root / ".next" / "standalone"
        legacy["standalone_root"] = str(standalone_root)
        legacy["standalone_static_present"] = _exists(standalone_root / ".next" / "static")
        legacy["standalone_public_present"] = _exists(standalone_root / "public")
        legacy["project_static_present"] = _exists(root / ".next" / "static")
        legacy["project_public_present"] = _exists(root / "public")
        exec_start = str(legacy.get("exec_start") or "")
        if ".next/standalone/server.js" in exec_start:
            if not legacy["standalone_static_present"] and not legacy["standalone_public_present"]:
                legacy["root_cause_hint"] = "standalone_missing_public_and_static_copy"
            elif not legacy["standalone_static_present"] and legacy["project_static_present"]:
                legacy["root_cause_hint"] = "standalone_missing_static_copy"
            elif not legacy["standalone_public_present"] and legacy["project_public_present"]:
                legacy["root_cause_hint"] = "standalone_missing_public_copy"

docker_result = subprocess.run(
    [
        "docker",
        "ps",
        "--filter",
        "name=athanor-dashboard",
        "--format",
        "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}",
    ],
    capture_output=True,
    text=True,
    check=False,
)
payload["container"]["returncode"] = docker_result.returncode
docker_line = next((entry for entry in docker_result.stdout.splitlines() if entry.strip()), "")
if docker_result.returncode == 0 and docker_line:
    name, image, status, ports = (docker_line.split("|", 3) + ["", "", "", ""])[:4]
    payload["container"]["name"] = name or "athanor-dashboard"
    payload["container"]["running"] = True
    payload["container"]["image"] = image
    payload["container"]["status"] = status
    payload["container"]["ports"] = ports
    inspect_result = subprocess.run(
        ["docker", "inspect", "athanor-dashboard"],
        capture_output=True,
        text=True,
        check=False,
    )
    payload["container"]["inspect_returncode"] = inspect_result.returncode
    if inspect_result.returncode == 0 and inspect_result.stdout.strip():
        try:
            inspect_payload = json.loads(inspect_result.stdout)
        except json.JSONDecodeError:
            inspect_payload = []
        if inspect_payload:
            labels = dict(inspect_payload[0].get("Config", {}).get("Labels", {}) or {})
            payload["container"]["compose_working_dir"] = str(
                labels.get("com.docker.compose.project.working_dir") or ""
            )
            payload["container"]["compose_config_files"] = str(
                labels.get("com.docker.compose.project.config_files") or ""
            )

deployment_root = payload["deployment_root"]
expected_root = Path(deployment_root["expected_path"])
runtime_repo_root = Path(deployment_root["runtime_repo_path"])
deployment_root["expected_exists"] = _exists(expected_root)
deployment_root["runtime_repo_exists"] = _exists(runtime_repo_root)
deployment_root["runtime_repo_compose_exists"] = _exists(runtime_repo_root / "docker-compose.yml")
for relative_path in ["Dockerfile", "docker-compose.yml"]:
    runtime_repo_file = runtime_repo_root / relative_path
    deploy_root_file = expected_root / relative_path
    record = {
        "relative_path": relative_path,
        "runtime_repo_path": str(runtime_repo_file),
        "runtime_repo_exists": _exists(runtime_repo_file),
        "deploy_root_path": str(deploy_root_file),
        "deploy_root_exists": _exists(deploy_root_file),
    }
    if record["runtime_repo_exists"]:
        record["runtime_repo_normalized_sha256"] = _normalized_sha256(runtime_repo_file)
    if record["deploy_root_exists"]:
        record["deploy_root_normalized_sha256"] = _normalized_sha256(deploy_root_file)
    record["deploy_matches_runtime_repo"] = bool(
        record.get("runtime_repo_normalized_sha256")
        and record.get("deploy_root_normalized_sha256")
        and record["runtime_repo_normalized_sha256"] == record["deploy_root_normalized_sha256"]
    )
    payload["control_files"].append(record)
if deployment_root["runtime_repo_compose_exists"]:
    compose_result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(runtime_repo_root / "docker-compose.yml"),
            "ps",
            "dashboard",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    deployment_root["runtime_repo_compose_returncode"] = compose_result.returncode
    deployment_root["runtime_repo_compose_ps"] = next(
        (line.strip() for line in compose_result.stdout.splitlines() if "athanor-dashboard" in line),
        "",
    )
    deployment_root["runtime_repo_compose_controls_container"] = (
        compose_result.returncode == 0 and "athanor-dashboard" in compose_result.stdout
    )
if payload["container"]["running"]:
    compose_working_dir = str(payload["container"].get("compose_working_dir") or "")
    if compose_working_dir:
        deployment_root["observed_active_root"] = compose_working_dir
    elif deployment_root["expected_exists"]:
        deployment_root["observed_active_root"] = deployment_root["expected_path"]
    elif deployment_root["runtime_repo_compose_controls_container"]:
        deployment_root["observed_active_root"] = deployment_root["runtime_repo_path"]
    elif payload.get("working_directory"):
        deployment_root["observed_active_root"] = str(payload.get("working_directory") or "")
    deployment_root["observed_compose_config_files"] = str(
        payload["container"].get("compose_config_files") or ""
    )
    deployment_root["drift"] = bool(
        deployment_root.get("observed_active_root")
        and deployment_root.get("observed_active_root") != deployment_root["expected_path"]
    )

caddy_result = subprocess.run(
    [
        "systemctl",
        "show",
        "caddy.service",
        "--property=LoadState,ActiveState,SubState,FragmentPath",
        "--no-pager",
    ],
    capture_output=True,
    text=True,
    check=False,
)
payload["caddy"]["returncode"] = caddy_result.returncode
if caddy_result.returncode == 0:
    payload["caddy"]["service_present"] = True
    for line in caddy_result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "ActiveState":
            payload["caddy"]["active_state"] = value or "unknown"
        elif key == "SubState":
            payload["caddy"]["sub_state"] = value or "unknown"
        elif key == "FragmentPath":
            payload["caddy"]["fragment_path"] = value

for key, url, insecure in [
    ("local_runtime_status_code", "http://127.0.0.1:3001/", False),
    ("local_canonical_status_code", "https://athanor.local/", True),
]:
    command = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}"]
    if insecure:
        command.append("-k")
    command.append(url)
    curl_result = subprocess.run(command, capture_output=True, text=True, check=False)
    payload[f"{key}_detail"] = curl_result.stdout.strip() or curl_result.stderr.strip()
    if curl_result.returncode == 0:
        try:
            payload[key] = int((curl_result.stdout or "").strip())
        except Exception:
            payload[key] = None

if payload["container"]["running"] and payload["caddy"]["active_state"] == "active":
    payload["deployment_mode"] = "containerized_service_behind_caddy"
elif legacy["active_state"] == "active":
    payload["deployment_mode"] = "legacy_systemd_standalone"
print(json.dumps(payload))
""".strip()

    attempts: list[dict[str, Any]] = []
    for target in _ssh_targets_for_node(topology, "dev"):
        result = _run_inline_python_json(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target],
            probe_script,
        )
        attempts.append({"target": target, "ok": result.get("ok"), "detail": result.get("detail")})
        if result.get("ok"):
            detail = dict(result.get("detail") or {})
            control_files = detail.get("control_files")
            if isinstance(control_files, list):
                for record in control_files:
                    if not isinstance(record, dict):
                        continue
                    relative_path = str(record.get("relative_path") or "").strip()
                    if not relative_path:
                        continue
                    implementation_path = REPO_ROOT / "projects" / "dashboard" / relative_path
                    implementation_exists = implementation_path.is_file()
                    record["implementation_path"] = str(implementation_path)
                    record["implementation_exists"] = implementation_exists
                    if implementation_exists:
                        record["implementation_normalized_sha256"] = _normalized_file_sha256(implementation_path)
                    implementation_sha = str(record.get("implementation_normalized_sha256") or "")
                    runtime_repo_sha = str(record.get("runtime_repo_normalized_sha256") or "")
                    deploy_root_sha = str(record.get("deploy_root_normalized_sha256") or "")
                    record["implementation_matches_runtime_repo"] = bool(
                        implementation_sha and runtime_repo_sha and implementation_sha == runtime_repo_sha
                    )
                    record["implementation_matches_deploy_root"] = bool(
                        implementation_sha and deploy_root_sha and implementation_sha == deploy_root_sha
                    )
                detail["control_files"] = control_files
            return {"ok": True, "target": target, "detail": detail, "attempts": attempts}
    return {"ok": False, "detail": "unable to reach DEV dashboard runtime probe", "attempts": attempts}


def _probe_workshop_shadow_dashboard_runtime(topology: dict[str, Any]) -> dict[str, Any]:
    probe_script = """
import json
import subprocess

payload = {
    "container_name": "athanor-dashboard",
    "running": False,
    "image": "",
    "status": "",
    "ports": "",
}
result = subprocess.run(
    [
        "docker",
        "ps",
        "--filter",
        "name=athanor-dashboard",
        "--format",
        "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}",
    ],
    capture_output=True,
    text=True,
    check=False,
)
payload["returncode"] = result.returncode
line = next((entry for entry in result.stdout.splitlines() if entry.strip()), "")
if result.returncode == 0 and line:
    name, image, status, ports = (line.split("|", 3) + ["", "", "", ""])[:4]
    payload["container_name"] = name or "athanor-dashboard"
    payload["running"] = True
    payload["image"] = image
    payload["status"] = status
    payload["ports"] = ports
print(json.dumps(payload))
""".strip()

    attempts: list[dict[str, Any]] = []
    for target in _ssh_targets_for_node(topology, "workshop"):
        result = _run_inline_python_json(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target],
            probe_script,
        )
        attempts.append({"target": target, "ok": result.get("ok"), "detail": result.get("detail")})
        if result.get("ok"):
            return {"ok": True, "target": target, "detail": result.get("detail"), "attempts": attempts}
    return {"ok": False, "detail": "unable to reach WORKSHOP dashboard runtime probe", "attempts": attempts}


def _probe_foundry_agents_runtime(topology: dict[str, Any]) -> dict[str, Any]:
    probe_script = """
from pathlib import Path
import hashlib
import json
import subprocess

def _normalized_sha256(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    pending_cr = False
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            if pending_cr:
                chunk = b"\\r" + chunk
                pending_cr = False
            if chunk.endswith(b"\\r"):
                chunk = chunk[:-1]
                pending_cr = True
            digest.update(chunk.replace(b"\\r\\n", b"\\n"))
    if pending_cr:
        digest.update(b"\\r")
    return digest.hexdigest()

def _tree_sha256(path: Path):
    if not path.exists():
        return None
    if path.is_file():
        return _normalized_sha256(path)
    digest = hashlib.sha256()
    for file_path in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\\\\0")
        file_sha = _normalized_sha256(file_path)
        if file_sha:
            digest.update(file_sha.encode("utf-8"))
            digest.update(b"\\\\0")
    return digest.hexdigest()

payload = {
    "deployment_root": {
        "expected_path": "/opt/athanor/agents",
        "expected_exists": False,
        "compose_file_exists": False,
        "config_file_exists": False,
        "source_root_exists": False,
        "source_tree_sha256": None,
        "nested_source_dir_exists": False,
        "bak_codex_files": [],
        "build_root_clean": None,
    },
    "container": {
        "name": "athanor-agents",
        "running": False,
        "status": "",
        "image": "",
        "compose_working_dir": "",
        "compose_config_files": "",
        "mounts": [],
        "module_file": "",
        "bootstrap_state_file": "",
        "site_packages_import": False,
    },
    "control_files": [],
    "source_mirrors": [],
}

expected_root = Path(payload["deployment_root"]["expected_path"])
payload["deployment_root"]["expected_exists"] = expected_root.is_dir()
payload["deployment_root"]["compose_file_exists"] = (expected_root / "docker-compose.yml").is_file()
payload["deployment_root"]["config_file_exists"] = (expected_root / "config" / "subscription-routing-policy.yaml").is_file()
source_root = expected_root / "src" / "athanor_agents"
payload["deployment_root"]["source_root_exists"] = source_root.is_dir()
payload["deployment_root"]["source_tree_sha256"] = _tree_sha256(source_root) if source_root.is_dir() else None
payload["deployment_root"]["nested_source_dir_exists"] = (source_root / "athanor_agents").exists()
payload["deployment_root"]["bak_codex_files"] = sorted(
    entry.relative_to(expected_root).as_posix()
    for entry in expected_root.rglob("*.bak-codex")
)[:50] if expected_root.exists() else []
payload["deployment_root"]["build_root_clean"] = not payload["deployment_root"]["nested_source_dir_exists"] and not payload["deployment_root"]["bak_codex_files"]

for relative_path, kind in [
    ("Dockerfile", "file"),
    ("pyproject.toml", "file"),
    ("docker-compose.yml", "file"),
    ("config/subscription-routing-policy.yaml", "file"),
    ("src/athanor_agents", "directory"),
]:
    runtime_path = expected_root / relative_path
    record = {
        "relative_path": relative_path,
        "kind": kind,
        "runtime_path": str(runtime_path),
        "runtime_exists": runtime_path.exists(),
    }
    if runtime_path.exists():
        if kind == "directory":
            record["runtime_tree_sha256"] = _tree_sha256(runtime_path)
        else:
            record["runtime_normalized_sha256"] = _normalized_sha256(runtime_path)
    payload["control_files"].append(record)

result = subprocess.run(
    [
        "docker",
        "ps",
        "--filter",
        "name=athanor-agents",
        "--format",
        "{{.Names}}|{{.Image}}|{{.Status}}",
    ],
    capture_output=True,
    text=True,
    check=False,
)
line = next((entry for entry in result.stdout.splitlines() if entry.strip()), "")
if result.returncode == 0 and line:
    name, image, status = (line.split("|", 2) + ["", "", ""])[:3]
    payload["container"]["name"] = name or "athanor-agents"
    payload["container"]["running"] = True
    payload["container"]["image"] = image
    payload["container"]["status"] = status
    inspect_result = subprocess.run(
        ["docker", "inspect", "athanor-agents"],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect_result.returncode == 0 and inspect_result.stdout.strip():
        try:
            inspect_payload = json.loads(inspect_result.stdout)
        except json.JSONDecodeError:
            inspect_payload = []
        if inspect_payload:
            labels = dict(inspect_payload[0].get("Config", {}).get("Labels", {}) or {})
            mounts = inspect_payload[0].get("Mounts", []) or []
            payload["container"]["compose_working_dir"] = str(
                labels.get("com.docker.compose.project.working_dir") or ""
            )
            payload["container"]["compose_config_files"] = str(
                labels.get("com.docker.compose.project.config_files") or ""
            )
            payload["container"]["mounts"] = [
                {
                    "source": str(mount.get("Source") or ""),
                    "destination": str(mount.get("Destination") or ""),
                    "rw": bool(mount.get("RW")),
                }
                for mount in mounts
            ]
    import_code = '''
from pathlib import Path
import json
import os
import athanor_agents
import athanor_agents.bootstrap_state as bootstrap_state

paths = [
    "/workspace/projects/agents/src/athanor_agents",
    "/workspace/agents/src/athanor_agents",
    "/app/src/athanor_agents",
]

print(json.dumps({
    "module_file": str(Path(athanor_agents.__file__).resolve()),
    "bootstrap_state_file": str(Path(bootstrap_state.__file__).resolve()),
    "site_packages_import": "site-packages" in str(Path(athanor_agents.__file__).resolve()),
    "source_mirrors": [
        {
            "path": path,
            "exists": Path(path).exists(),
            "writable": os.access(path, os.W_OK),
        }
        for path in paths
    ],
}))
'''.strip()
    import_result = subprocess.run(
        ["docker", "exec", "athanor-agents", "python3", "-c", import_code],
        capture_output=True,
        text=True,
        check=False,
    )
    if import_result.returncode == 0 and import_result.stdout.strip():
        try:
            import_payload = json.loads(import_result.stdout)
        except json.JSONDecodeError:
            import_payload = {}
        if import_payload:
            payload["container"]["module_file"] = str(import_payload.get("module_file") or "")
            payload["container"]["bootstrap_state_file"] = str(import_payload.get("bootstrap_state_file") or "")
            payload["container"]["site_packages_import"] = bool(import_payload.get("site_packages_import"))
            payload["source_mirrors"] = [
                dict(entry) for entry in import_payload.get("source_mirrors", []) if isinstance(entry, dict)
            ]

print(json.dumps(payload))
""".strip()

    attempts: list[dict[str, Any]] = []
    for target in _ssh_targets_for_node(topology, "foundry"):
        result = _run_inline_python_json(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target],
            probe_script,
        )
        attempts.append({"target": target, "ok": result.get("ok"), "detail": result.get("detail")})
        if result.get("ok"):
            detail = dict(result.get("detail") or {})
            control_files = [
                dict(entry)
                for entry in detail.get("control_files", [])
                if isinstance(entry, dict) and str(entry.get("relative_path") or "").strip()
            ]
            for record in control_files:
                relative_path = str(record.get("relative_path") or "").strip()
                implementation_path = REPO_ROOT / "projects" / "agents" / PurePosixPath(relative_path)
                implementation_exists = implementation_path.exists()
                record["implementation_path"] = str(implementation_path)
                record["implementation_exists"] = implementation_exists
                kind = str(record.get("kind") or "file")
                if implementation_exists:
                    if kind == "directory":
                        record["implementation_tree_sha256"] = _normalized_tree_sha256(implementation_path)
                    else:
                        record["implementation_normalized_sha256"] = _normalized_file_sha256(implementation_path)
                implementation_sha = str(
                    record.get("implementation_tree_sha256")
                    or record.get("implementation_normalized_sha256")
                    or ""
                )
                runtime_sha = str(
                    record.get("runtime_tree_sha256")
                    or record.get("runtime_normalized_sha256")
                    or ""
                )
                record["implementation_matches_runtime"] = bool(
                    implementation_sha and runtime_sha and implementation_sha == runtime_sha
                )
            detail["control_files"] = control_files
            deployment_root = (
                dict(detail.get("deployment_root") or {})
                if isinstance(detail.get("deployment_root"), dict)
                else {}
            )
            deployment_root["compose_root_matches_expected"] = (
                str(dict(detail.get("container") or {}).get("compose_working_dir") or "")
                == str(deployment_root.get("expected_path") or "")
            )
            detail["deployment_root"] = deployment_root
            return {"ok": True, "target": target, "detail": detail, "attempts": attempts}
    return {"ok": False, "detail": "unable to reach FOUNDRY agents runtime probe", "attempts": attempts}


def _write_json_artifact(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sync_foundry_bootstrap_artifacts(topology: dict[str, Any]) -> dict[str, Any]:
    artifact_names = [
        "compatibility-retirement-census.json",
        "durable-persistence-packet.json",
        "durable-restart-proof.json",
        "foundry-proving-packet.json",
        "governance-drill-packets.json",
        "latest.json",
        "operator-fixture-parity.json",
        "operator-nav-lock.json",
        "operator-summary-alignment.json",
        "operator-surface-census.json",
        "takeover-promotion-packet.json",
    ]
    probe_script = f"""
from pathlib import Path
import hashlib
import json

artifact_names = {json.dumps(artifact_names)}
candidate_roots = [
    Path("/output/reports/bootstrap"),
    Path("/workspace/reports/bootstrap"),
    Path("/app/reports/bootstrap"),
]

def _sha256(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

payload = {{
    "artifact_root": "",
    "artifacts": {{}},
    "artifact_meta": {{}},
    "missing_artifacts": [],
}}
for root in candidate_roots:
    if not root.is_dir():
        continue
    if not any((root / name).is_file() for name in artifact_names):
        continue
    payload["artifact_root"] = str(root)
    for name in artifact_names:
        artifact_path = root / name
        if not artifact_path.is_file():
            payload["missing_artifacts"].append(name)
            continue
        payload["artifacts"][name] = json.loads(artifact_path.read_text(encoding="utf-8"))
        payload["artifact_meta"][name] = {{
            "sha256": _sha256(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
        }}
    break

print(json.dumps(payload))
""".strip()

    attempts: list[dict[str, Any]] = []
    for target in _ssh_targets_for_node(topology, "foundry"):
        result = _run_json_stdout_command(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target, "docker", "exec", "-i", "athanor-agents", "python3", "-"],
            probe_script,
        )
        attempts.append({"target": target, "ok": result.get("ok"), "detail": result.get("detail")})
        if not result.get("ok"):
            continue
        detail = dict(result.get("detail") or {})
        artifacts = {
            str(name): payload
            for name, payload in dict(detail.get("artifacts") or {}).items()
            if str(name).strip()
        }
        if not artifacts:
            continue
        synced_artifacts: list[dict[str, Any]] = []
        for name, payload in artifacts.items():
            destination = BOOTSTRAP_REPORTS_DIR / name
            _write_json_artifact(destination, payload)
            synced_artifacts.append(
                {
                    "name": name,
                    "destination": str(destination),
                    "local_sha256": _file_sha256(destination),
                    "remote_sha256": str(dict(detail.get("artifact_meta") or {}).get(name, {}).get("sha256") or ""),
                    "size_bytes": dict(detail.get("artifact_meta") or {}).get(name, {}).get("size_bytes"),
                }
            )
        detail["synced_artifacts"] = synced_artifacts
        detail["local_root"] = str(BOOTSTRAP_REPORTS_DIR)
        detail["synced_artifact_count"] = len(synced_artifacts)
        return {"ok": True, "target": target, "detail": detail, "attempts": attempts}

    return {"ok": False, "detail": "unable to reach live FOUNDRY bootstrap artifacts", "attempts": attempts}


async def _probe_operator_surfaces(
    topology: dict[str, Any],
    operator_surfaces: dict[str, Any],
) -> dict[str, Any]:
    surfaces = [
        dict(entry)
        for entry in operator_surfaces.get("surfaces", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]
    active_production_portal_ids = [
        str(entry.get("id") or "")
        for entry in surfaces
        if str(entry.get("surface_kind") or "") == "portal"
        and str(entry.get("retirement_state") or "") in {"keep", "canonical_active"}
        and str(entry.get("status") or "") in {"active_production", "degraded_production"}
    ]
    duplicate_active_production_ids = active_production_portal_ids if len(active_production_portal_ids) > 1 else []

    probes: list[tuple[str, str]] = []
    for surface in surfaces:
        surface_id = str(surface.get("id") or "")
        canonical_url = str(surface.get("canonical_url") or "").strip()
        runtime_url = str(surface.get("runtime_url") or "").strip()
        if canonical_url.startswith(("http://", "https://")):
            probes.append((f"{surface_id}:canonical", canonical_url))
        if runtime_url.startswith(("http://", "https://")) and runtime_url != canonical_url:
            probes.append((f"{surface_id}:runtime", runtime_url))

    probe_index = {
        result.get("id"): result
        for result in await _probe_urls(probes)
    }

    surface_rows: list[dict[str, Any]] = []
    runtime_duplicate_groups: list[dict[str, Any]] = []
    for surface in surfaces:
        surface_id = str(surface.get("id") or "")
        runtime_url = str(surface.get("runtime_url") or "").strip()
        asset_probe: dict[str, Any] | None = None
        if surface_id in {"athanor_command_center", "workshop_shadow_command_center"} and runtime_url.startswith(
            ("http://", "https://")
        ):
            asset_probe = await _probe_next_static_assets(runtime_url)
        surface_rows.append(
            {
                "id": surface_id,
                "label": str(surface.get("label") or ""),
                "node": str(surface.get("node") or ""),
                "surface_kind": str(surface.get("surface_kind") or ""),
                "status": str(surface.get("status") or ""),
                "canonical_url": str(surface.get("canonical_url") or ""),
                "runtime_url": runtime_url,
                "canonical_probe": probe_index.get(f"{surface_id}:canonical"),
                "runtime_probe": probe_index.get(f"{surface_id}:runtime")
                if runtime_url != str(surface.get("canonical_url") or "").strip()
                else probe_index.get(f"{surface_id}:canonical"),
                "next_static_probe": asset_probe,
            }
        )

    reachable_by_group: dict[str, list[str]] = {}
    for row in surface_rows:
        runtime_probe = dict(row.get("runtime_probe") or {})
        if runtime_probe.get("ok"):
            reachable_by_group.setdefault(str(row.get("surface_group") or row.get("id") or ""), []).append(
                str(row.get("id") or "")
            )
    for surface_group, surface_ids in sorted(reachable_by_group.items()):
        if len(surface_ids) > 1:
            runtime_duplicate_groups.append(
                {
                    "surface_group": surface_group,
                    "reachable_surface_ids": sorted(surface_ids),
                    "finding": "duplicate_reachable_surface_group",
                }
            )

    return {
        "canonical_front_door": dict(operator_surfaces.get("canonical_front_door") or {}),
        "known_drifts": [dict(entry) for entry in operator_surfaces.get("known_drifts", []) if isinstance(entry, dict)],
        "duplicate_active_production_portal_ids": duplicate_active_production_ids,
        "runtime_duplicate_groups": runtime_duplicate_groups,
        "shadow_surface_ids": [
            str(entry.get("id") or "")
            for entry in surfaces
            if str(entry.get("status") or "") == "shadow"
        ],
        "undeclared_exposed_surfaces": [],
        "dev_command_center_runtime": _probe_dev_command_center_runtime(topology),
        "workshop_shadow_runtime": _probe_workshop_shadow_dashboard_runtime(topology),
        "surfaces": surface_rows,
    }


def _probe_tcp_endpoint(probe_id: str, *, scheme: str, host: str, port: int) -> dict[str, Any]:
    url = f"{scheme}://{host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=4):
            return {
                "id": probe_id,
                "url": url,
                "ok": True,
                "probe_class": "tcp_connect",
                "detail": "tcp connect ok",
            }
    except Exception as exc:  # pragma: no cover - network dependent
        return {
            "id": probe_id,
            "url": url,
            "ok": False,
            "probe_class": "tcp_connect",
            "detail": str(exc),
        }


async def _probe_services(topology: dict[str, Any]) -> list[dict[str, Any]]:
    hosts = {
        str(node.get("id") or ""): str(node.get("default_host") or "")
        for node in topology.get("nodes", [])
    }
    http_targets: list[tuple[str, str]] = []
    tcp_targets: list[tuple[str, str, str, int]] = []

    for service in topology.get("services", []):
        service_id = str(service.get("id") or "")
        node_id = str(service.get("node") or "")
        host = hosts.get(node_id, "")
        scheme = str(service.get("scheme") or "http")
        port = int(service.get("port") or 0)
        if not service_id or not host or not port:
            continue

        if scheme in {"http", "https"}:
            path = str(service.get("health_path") or service.get("path") or "/health")
            http_targets.append((service_id, f"{scheme}://{host}:{port}{path}"))
            continue

        if scheme in {"bolt", "redis", "postgres", "postgresql"}:
            tcp_targets.append((service_id, scheme, host, port))
            continue

    results = await _probe_urls(http_targets)
    for result in results:
        result["probe_class"] = "http"

    for service_id, scheme, host, port in tcp_targets:
        results.append(_probe_tcp_endpoint(service_id, scheme=scheme, host=host, port=port))

    return results


async def build_snapshot() -> dict[str, Any]:
    topology = load_registry("platform-topology.json")
    models = load_registry("model-deployment-registry.json")
    providers = load_registry("provider-catalog.json")
    repo_roots = load_registry("repo-roots-registry.json")
    credentials = load_registry("credential-surface-registry.json")
    runtime_migrations = load_registry("runtime-migration-registry.json")
    operator_surfaces = load_registry("operator-surface-registry.json")

    model_urls = [
        (str(lane.get("id") or ""), str(lane.get("endpoint") or ""))
        for lane in models.get("lanes", [])
        if str(lane.get("endpoint") or "").startswith("http")
    ]

    dev_runtime_probe = _probe_dev_runtime(topology, runtime_migrations)
    _annotate_governor_facade_probe(dev_runtime_probe, runtime_migrations)
    vault_litellm_env_audit = collect_vault_litellm_env_audit()
    vault_redis_audit = collect_vault_redis_audit()
    foundry_bootstrap_artifact_probe = _sync_foundry_bootstrap_artifacts(topology)

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "implementation_authority_root": str(IMPLEMENTATION_AUTHORITY_ROOT),
        "registry_dir": str(CONFIG_DIR),
        "hostname": os.environ.get("COMPUTERNAME") or socket.gethostname(),
        "provider_index": provider_index(providers),
        "provider_usage_evidence": load_optional_json(PROVIDER_USAGE_EVIDENCE_PATH),
        "vault_litellm_env_audit": vault_litellm_env_audit,
        "vault_redis_audit": vault_redis_audit,
        "local_tool_probes": _probe_local_tools(),
        "local_runtime_env_probe": runtime_env_status(
            env_names=[
                "ATHANOR_REDIS_URL",
                "ATHANOR_REDIS_PASSWORD",
                "ATHANOR_VAULT_KEY_PATH",
                "ATHANOR_LITELLM_URL",
                "ATHANOR_LITELLM_API_KEY",
                "OPENAI_API_BASE",
                "OPENAI_API_KEY",
            ]
        ),
        "dev_runtime_probe": dev_runtime_probe,
        "foundry_agents_runtime_probe": _probe_foundry_agents_runtime(topology),
        "foundry_bootstrap_artifact_probe": foundry_bootstrap_artifact_probe,
        "operator_surface_probe": await _probe_operator_surfaces(topology, operator_surfaces),
        "service_probes": await _probe_services(topology),
        "model_endpoint_probes": await _probe_urls(model_urls),
        "registries": {
            "hardware": load_registry("hardware-inventory.json"),
            "models": models,
            "providers": providers,
            "repo_roots": repo_roots,
            "credentials": credentials,
            "operator_surfaces": operator_surfaces,
            "runtime_migrations": runtime_migrations,
            "routing_taxonomy": load_registry("routing-taxonomy-map.json"),
            "tooling": load_registry("tooling-inventory.json")
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    snapshot = asyncio.run(build_snapshot())
    rendered = json.dumps(snapshot, indent=2, sort_keys=True)
    TRUTH_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRUTH_SNAPSHOT_PATH.write_text(rendered, encoding="utf-8")
    VAULT_LITELLM_ENV_AUDIT_PATH.write_text(
        json.dumps(snapshot.get("vault_litellm_env_audit", {}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    VAULT_REDIS_AUDIT_PATH.write_text(
        json.dumps(snapshot.get("vault_redis_audit", {}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.write}")
        return 0

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
