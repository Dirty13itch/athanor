from __future__ import annotations

import base64
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_inventory import REPO_ROOT, VAULT_REDIS_AUDIT_PATH


VAULT_SSH_PATH = REPO_ROOT / "scripts" / "vault-ssh.py"
VAULT_REDIS_CONTAINER_NAME = "redis"
AUDIT_VERSION = "2026-04-02.1"
NO_SPACE_MARKER = "No space left on device"
SECURITY_ATTACK_MARKER = "Possible SECURITY ATTACK"
TIMESTAMP_PATTERN = re.compile(r"\d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2}\.\d+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_remote_probe_script(container_name: str) -> str:
    return f"""import json
import pathlib
import re
import shlex
import subprocess

container_name = {container_name!r}
no_space_marker = {NO_SPACE_MARKER!r}
security_attack_marker = {SECURITY_ATTACK_MARKER!r}
timestamp_pattern = re.compile(r"\\d{{2}} \\w{{3}} \\d{{4}} \\d{{2}}:\\d{{2}}:\\d{{2}}\\.\\d+")


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_shell(command):
    return run(["sh", "-lc", command])


def first_line(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[0][:240] if lines else ""


def parse_df(path):
    result = run_shell(f"df -B1 -P {{shlex.quote(path)}} | tail -1")
    if result.returncode != 0:
        return {{}}
    parts = [item for item in result.stdout.strip().split() if item]
    if len(parts) < 6:
        return {{}}
    filesystem, size_bytes, used_bytes, avail_bytes, used_percent, mountpoint = parts[:6]
    return {{
        "filesystem": filesystem,
        "size_bytes": int(size_bytes),
        "used_bytes": int(used_bytes),
        "available_bytes": int(avail_bytes),
        "used_percent": used_percent,
        "mountpoint": mountpoint,
    }}


def parse_du(path):
    result = run(["du", "-sb", path])
    if result.returncode != 0:
        return None
    first = first_line(result.stdout)
    if not first:
        return None
    try:
        return int(first.split()[0])
    except Exception:
        return None


def parse_du_top(path, limit=8):
    result = run(["du", "-x", "-B1", "-d1", path])
    if result.returncode != 0:
        return []
    entries = []
    for raw_line in (result.stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        size_text, entry_path = parts
        if entry_path == path:
            continue
        try:
            size_bytes = int(size_text)
        except Exception:
            continue
        entries.append({{
            "path": entry_path,
            "size_bytes": size_bytes,
        }})
    entries.sort(key=lambda item: int(item.get("size_bytes") or 0), reverse=True)
    return entries[:limit]


def parse_find_top_files(path, limit=8):
    result = run([
        "find",
        path,
        "-maxdepth",
        "1",
        "-type",
        "f",
        "-printf",
        "%s %p\\n",
    ])
    if result.returncode != 0:
        return []
    entries = []
    for raw_line in (result.stdout or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        size_text, entry_path = parts
        try:
            size_bytes = int(size_text)
        except Exception:
            continue
        entries.append({{
            "path": entry_path,
            "size_bytes": size_bytes,
        }})
    entries.sort(key=lambda item: int(item.get("size_bytes") or 0), reverse=True)
    return entries[:limit]


def parse_btrfs(path):
    result = run(["btrfs", "filesystem", "usage", path])
    output = (result.stdout or result.stderr or "").strip()
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if result.returncode != 0:
        return {{
            "ok": False,
            "summary_lines": lines[:12],
            "error": first_line(output),
        }}

    def extract(prefix):
        for line in lines:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        return ""

    return {{
        "ok": True,
        "summary_lines": lines[:12],
        "device_allocated": extract("Device allocated:"),
        "device_unallocated": extract("Device unallocated:"),
        "device_missing": extract("Device missing:"),
        "device_slack": extract("Device slack:"),
        "used": extract("Used:"),
        "free_estimated": extract("Free (estimated):"),
    }}


inspect_result = run(["docker", "inspect", container_name])
if inspect_result.returncode != 0:
    detail = first_line(inspect_result.stderr or inspect_result.stdout)
    print(json.dumps({{
        "ok": False,
        "container_name": container_name,
        "error": detail or f"docker inspect returncode={{inspect_result.returncode}}",
    }}, sort_keys=True))
    raise SystemExit(0)

payload = json.loads(inspect_result.stdout)[0]
config = payload.get("Config") or {{}}
host_config = payload.get("HostConfig") or {{}}
state = payload.get("State") or {{}}
mounts = [mount for mount in payload.get("Mounts") or [] if isinstance(mount, dict)]
data_mount = next((mount for mount in mounts if str(mount.get("Destination") or "") == "/data"), {{}})
data_mount_source = str(data_mount.get("Source") or "")
data_mount_destination = str(data_mount.get("Destination") or "/data")
df_info = parse_df(data_mount_source or data_mount_destination)
btrfs_info = parse_btrfs(df_info.get("mountpoint") or data_mount_source or data_mount_destination)
dir_size_bytes = parse_du(data_mount_source) if data_mount_source else None
appdatacache_top_consumers = parse_du_top(df_info.get("mountpoint") or "/mnt/appdatacache")
appdata_parent = str(pathlib.Path(data_mount_source).parent) if data_mount_source else "/mnt/appdatacache/appdata"
appdata_top_consumers = parse_du_top(appdata_parent)
backup_file_top_consumers = parse_find_top_files("/mnt/appdatacache/backups")
stash_generated_top_consumers = parse_du_top("/mnt/appdatacache/appdata/stash/generated")
comfyui_model_top_consumers = parse_du_top("/mnt/appdatacache/models/comfyui")
logs_result = run(["docker", "logs", "--tail", "250", container_name])
log_lines = [line.rstrip() for line in (logs_result.stdout or logs_result.stderr or "").splitlines() if line.strip()]
no_space_lines = [line for line in log_lines if no_space_marker in line]
background_error_lines = [line for line in log_lines if "Background saving error" in line]
security_attack_lines = [line for line in log_lines if security_attack_marker in line]
latest_no_space_line = no_space_lines[-1] if no_space_lines else ""
latest_background_error_line = background_error_lines[-1] if background_error_lines else ""
latest_security_attack_line = security_attack_lines[-1] if security_attack_lines else ""

def line_timestamp(line):
    if not line:
        return ""
    match = timestamp_pattern.search(line)
    return match.group(0) if match else ""


print(json.dumps({{
    "ok": True,
    "container_name": container_name,
    "container_image": str(config.get("Image") or ""),
    "container_restart_policy": str((host_config.get("RestartPolicy") or {{}}).get("Name") or ""),
    "container_started_at": str(state.get("StartedAt") or ""),
    "container_mounts": [
        {{
            "source": str(mount.get("Source") or ""),
            "destination": str(mount.get("Destination") or ""),
            "mode": str(mount.get("Mode") or ""),
            "read_only": not bool(mount.get("RW", False)),
        }}
        for mount in mounts
    ],
    "data_mount_source": data_mount_source,
    "data_mount_destination": data_mount_destination,
    "filesystem": df_info,
    "btrfs_usage": btrfs_info,
    "redis_data_dir_size_bytes": dir_size_bytes,
    "appdatacache_top_consumers": appdatacache_top_consumers,
    "appdata_top_consumers": appdata_top_consumers,
    "backup_file_top_consumers": backup_file_top_consumers,
    "stash_generated_top_consumers": stash_generated_top_consumers,
    "comfyui_model_top_consumers": comfyui_model_top_consumers,
    "log_tail": log_lines[-40:],
    "no_space_error_count": len(no_space_lines),
    "background_save_error_count": len(background_error_lines),
    "security_attack_count": len(security_attack_lines),
    "latest_no_space_error_line": latest_no_space_line,
    "latest_no_space_error_at": line_timestamp(latest_no_space_line),
    "latest_background_save_error_line": latest_background_error_line,
    "latest_background_save_error_at": line_timestamp(latest_background_error_line),
    "latest_security_attack_line": latest_security_attack_line,
    "latest_security_attack_at": line_timestamp(latest_security_attack_line),
}}, sort_keys=True))
"""


def _run_remote_probe(script: str) -> tuple[bool, str]:
    encoded_script = base64.b64encode(script.encode("utf-8")).decode("ascii")
    remote_command = (
        "python3 -c 'import base64; "
        f"exec(base64.b64decode(\"{encoded_script}\").decode(\"utf-8\"))'"
    )
    command = [sys.executable, str(VAULT_SSH_PATH), remote_command]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        return False, str(exc)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return False, detail[0][:240] if detail else f"vault-ssh returncode={completed.returncode}"
    return True, (completed.stdout or "").strip()


def _failed_audit_payload(error: str) -> dict[str, Any]:
    observed_at = utc_now()
    return {
        "version": AUDIT_VERSION,
        "surface_id": "vault-redis-persistence",
        "service_id": "redis",
        "host": "vault",
        "source": "vault-ssh docker inspect + filesystem audit",
        "observed_at": observed_at,
        "collected_at": observed_at,
        "ok": False,
        "runtime_owner_surface": "standalone_docker_container",
        "container_name": VAULT_REDIS_CONTAINER_NAME,
        "container_image": "",
        "container_restart_policy": "",
        "container_started_at": "",
        "container_mounts": [],
        "data_mount_source": "",
        "data_mount_destination": "/data",
        "filesystem": {},
        "btrfs_usage": {},
        "redis_data_dir_size_bytes": None,
        "appdatacache_top_consumers": [],
        "appdata_top_consumers": [],
        "backup_file_top_consumers": [],
        "stash_generated_top_consumers": [],
        "comfyui_model_top_consumers": [],
        "persistence_blocker_code": "probe_failed",
        "persistence_blocker_detail": error,
        "no_space_error_count": 0,
        "background_save_error_count": 0,
        "security_attack_count": 0,
        "latest_no_space_error_line": "",
        "latest_no_space_error_at": "",
        "latest_background_save_error_line": "",
        "latest_background_save_error_at": "",
        "latest_security_attack_line": "",
        "latest_security_attack_at": "",
        "log_tail": [],
        "operator_next_action": "Re-run the VAULT Redis audit and verify docker inspect plus filesystem probes on VAULT.",
        "error": error,
    }


def _normalize_audit_payload(remote_payload: dict[str, Any]) -> dict[str, Any]:
    observed_at = utc_now()
    no_space_count = int(remote_payload.get("no_space_error_count") or 0)
    security_attack_count = int(remote_payload.get("security_attack_count") or 0)
    background_save_error_count = int(remote_payload.get("background_save_error_count") or 0)
    appdatacache_top_consumers = [
        {
            "path": str(item.get("path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for item in remote_payload.get("appdatacache_top_consumers", [])
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    appdata_top_consumers = [
        {
            "path": str(item.get("path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for item in remote_payload.get("appdata_top_consumers", [])
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    backup_file_top_consumers = [
        {
            "path": str(item.get("path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for item in remote_payload.get("backup_file_top_consumers", [])
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    stash_generated_top_consumers = [
        {
            "path": str(item.get("path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for item in remote_payload.get("stash_generated_top_consumers", [])
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    comfyui_model_top_consumers = [
        {
            "path": str(item.get("path") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for item in remote_payload.get("comfyui_model_top_consumers", [])
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    blocker_code = "healthy"
    blocker_detail = "Redis persistence audit is healthy."
    operator_next_action = "No Redis repair action required."
    if no_space_count > 0:
        blocker_code = "rdb_temp_file_no_space"
        blocker_detail = (
            "Redis cannot create temporary RDB files on the VAULT /data mount because the backing filesystem is out "
            "of allocatable space."
        )
        hottest_appdata_paths = ", ".join(
            str(item.get("path") or "").rsplit("/", 1)[-1]
            for item in appdata_top_consumers[:5]
            if str(item.get("path") or "").strip()
        )
        operator_next_action = (
            "Recover or expand allocatable space on the VAULT appdatacache filesystem. Start with the lowest-risk "
            "high-yield targets in /mnt/appdatacache/backups (especially older stash and plex tarballs) before "
            f"touching live appdata hotspots ({hottest_appdata_paths or 'appdata hotspots'}), then verify Redis can "
            "BGSAVE cleanly before clearing the dependency blocker."
        )
    elif background_save_error_count > 0:
        blocker_code = "background_save_error"
        blocker_detail = "Redis background save is failing; inspect the latest persistence error and filesystem posture."
        operator_next_action = "Inspect Redis persistence errors on VAULT and verify the /data mount can accept new writes."

    return {
        "version": AUDIT_VERSION,
        "surface_id": "vault-redis-persistence",
        "service_id": "redis",
        "host": "vault",
        "source": "vault-ssh docker inspect + filesystem audit",
        "observed_at": observed_at,
        "collected_at": observed_at,
        "ok": bool(remote_payload.get("ok")),
        "runtime_owner_surface": "standalone_docker_container",
        "container_name": str(remote_payload.get("container_name") or VAULT_REDIS_CONTAINER_NAME),
        "container_image": str(remote_payload.get("container_image") or ""),
        "container_restart_policy": str(remote_payload.get("container_restart_policy") or ""),
        "container_started_at": str(remote_payload.get("container_started_at") or ""),
        "container_mounts": [
            {
                "source": str(mount.get("source") or ""),
                "destination": str(mount.get("destination") or ""),
                "mode": str(mount.get("mode") or ""),
                "read_only": bool(mount.get("read_only")),
            }
            for mount in remote_payload.get("container_mounts", [])
            if isinstance(mount, dict)
        ],
        "data_mount_source": str(remote_payload.get("data_mount_source") or ""),
        "data_mount_destination": str(remote_payload.get("data_mount_destination") or "/data"),
        "filesystem": dict(remote_payload.get("filesystem") or {}),
        "btrfs_usage": dict(remote_payload.get("btrfs_usage") or {}),
        "redis_data_dir_size_bytes": remote_payload.get("redis_data_dir_size_bytes"),
        "appdatacache_top_consumers": appdatacache_top_consumers,
        "appdata_top_consumers": appdata_top_consumers,
        "backup_file_top_consumers": backup_file_top_consumers,
        "stash_generated_top_consumers": stash_generated_top_consumers,
        "comfyui_model_top_consumers": comfyui_model_top_consumers,
        "persistence_blocker_code": blocker_code,
        "persistence_blocker_detail": blocker_detail,
        "no_space_error_count": no_space_count,
        "background_save_error_count": background_save_error_count,
        "security_attack_count": security_attack_count,
        "latest_no_space_error_line": str(remote_payload.get("latest_no_space_error_line") or ""),
        "latest_no_space_error_at": str(remote_payload.get("latest_no_space_error_at") or ""),
        "latest_background_save_error_line": str(remote_payload.get("latest_background_save_error_line") or ""),
        "latest_background_save_error_at": str(remote_payload.get("latest_background_save_error_at") or ""),
        "latest_security_attack_line": str(remote_payload.get("latest_security_attack_line") or ""),
        "latest_security_attack_at": str(remote_payload.get("latest_security_attack_at") or ""),
        "log_tail": [
            str(line).replace("=", ":")
            for line in remote_payload.get("log_tail", [])
            if str(line).strip()
        ],
        "operator_next_action": operator_next_action,
    }


def collect_vault_redis_audit() -> dict[str, Any]:
    ok, output = _run_remote_probe(_build_remote_probe_script(VAULT_REDIS_CONTAINER_NAME))
    if not ok:
        return _failed_audit_payload(output)
    try:
        remote_payload = json.loads(output)
    except json.JSONDecodeError:
        return _failed_audit_payload("invalid json from vault probe")
    return _normalize_audit_payload(remote_payload)


def write_audit(path: Path = VAULT_REDIS_AUDIT_PATH) -> dict[str, Any]:
    audit = collect_vault_redis_audit()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only VAULT Redis persistence audit.")
    parser.add_argument("--write", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    if args.write:
        audit = write_audit(args.write)
        print(f"Wrote {args.write}")
        return 0 if audit.get("ok") else 1

    audit = collect_vault_redis_audit()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
