from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_inventory import REPO_ROOT, VAULT_LITELLM_ENV_AUDIT_PATH, load_registry


VAULT_SSH_PATH = REPO_ROOT / "scripts" / "vault-ssh.py"
VAULT_LITELLM_CONTAINER_NAME = "litellm"
AUDIT_VERSION = "2026-04-13.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _vault_expected_env_names() -> list[str]:
    registry = load_registry("credential-surface-registry.json")
    surface = next(
        (
            entry
            for entry in registry.get("surfaces", [])
            if isinstance(entry, dict) and str(entry.get("id") or "") == "vault-litellm-container-env"
        ),
        {},
    )
    return sorted(
        {
            str(env_name).strip()
            for env_name in surface.get("env_var_names", [])
            if str(env_name).strip()
        }
    )


def _build_remote_probe_script(container_name: str, expected_env_names: list[str]) -> str:
    return f"""import glob
import json
import os
import pathlib
import re
import shlex
import subprocess

container_name = {container_name!r}
expected_env_names = {expected_env_names!r}


def env_names(values):
    names = []
    for item in values or []:
        if isinstance(item, str) and "=" in item:
            names.append(item.split("=", 1)[0])
    return sorted({{name for name in names if name}})


def limited_matches(root, *, needle="litellm", max_depth=4, require_file=False):
    root_path = pathlib.Path(root)
    if not root_path.exists():
        return []
    matches = []
    for path in root_path.rglob("*"):
        try:
            depth = len(path.relative_to(root_path).parts)
        except Exception:
            continue
        if depth > max_depth:
            continue
        if require_file and not path.is_file():
            continue
        if needle in str(path).lower():
            matches.append(str(path))
    return sorted(matches)[:50]


def grep_matches(roots, pattern, max_results=20):
    filtered_roots = [root for root in roots if root]
    if not filtered_roots:
        return []
    shell_roots = " ".join(shlex.quote(root) for root in filtered_roots)
    command = f"grep -R -l -E {{shlex.quote(pattern)}} {{shell_roots}} 2>/dev/null | sed -n '1,{{max_results}}p'"
    result = subprocess.run(["sh", "-lc", command], capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        return []
    return sorted({{line.strip() for line in result.stdout.splitlines() if line.strip()}})


def read_json_file(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def inspect_backup_env_snapshots(pattern):
    snapshots = []
    for raw_path in sorted(glob.glob(pattern))[:20]:
        payload = read_json_file(raw_path)
        if payload is None:
            continue
        obj = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(obj, dict):
            continue
        snapshots.append(
            {{
                "path": raw_path,
                "env_names": env_names((obj.get("Config") or {{}}).get("Env") or []),
                "image": str(((obj.get("Config") or {{}}).get("Image")) or ""),
            }}
        )
    return snapshots


def config_env_refs(config_path):
    path = pathlib.Path(config_path)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return sorted(
        {{
            match.strip()
            for match in re.findall(r"os\\.environ/([A-Z0-9_]+)", text)
            if str(match).strip()
        }}
    )


inspect_result = subprocess.run(
    ["docker", "inspect", container_name],
    capture_output=True,
    text=True,
    check=False,
)
if inspect_result.returncode != 0:
    detail = (inspect_result.stderr or inspect_result.stdout or "").strip().splitlines()
    print(
        json.dumps(
            {{
                "ok": False,
                "container_name": container_name,
                "expected_env_names": expected_env_names,
                "error": detail[0][:240] if detail else f"docker inspect returncode={{inspect_result.returncode}}",
            }},
            sort_keys=True,
        )
    )
    raise SystemExit(0)

payload = json.loads(inspect_result.stdout)[0]
config = payload.get("Config") or {{}}
host_config = payload.get("HostConfig") or {{}}
state = payload.get("State") or {{}}
mounts = payload.get("Mounts") or []
labels = config.get("Labels") or {{}}
label_keys = [str(key).strip() for key in labels.keys() if str(key).strip()]
compose_labels_present = any(
    key.startswith("com.docker.compose.")
    or key.startswith("com.docker.stack.")
    or "compose" in key
    for key in label_keys
)
container_env_names = env_names(config.get("Env") or [])
container_present = sorted(name for name in expected_env_names if name in container_env_names)
container_missing = sorted(name for name in expected_env_names if name not in container_env_names)
host_present = sorted(name for name in expected_env_names if os.environ.get(name))
host_missing = sorted(name for name in expected_env_names if not os.environ.get(name))
docker_template_matches = limited_matches("/boot/config/plugins/dockerMan/templates-user", max_depth=2)
compose_manager_matches = limited_matches("/boot/config/plugins/compose.manager", max_depth=4)
boot_config_reference_files = grep_matches(
    ["/boot/config"],
    r"ghcr.io/berriai/litellm|/mnt/user/appdata/litellm|docker/prod_entrypoint\\.sh|(^|[^A-Za-z])litellm([^A-Za-z]|$)",
)
appdata_files = limited_matches("/mnt/user/appdata/litellm", needle="", max_depth=2, require_file=True)
historical_backup_env_snapshots = inspect_backup_env_snapshots("/mnt/user/appdata/litellm/backups/litellm.inspect*.json")
config_referenced_env_names = config_env_refs("/mnt/user/appdata/litellm/config.yaml")
config_referenced_present = sorted(name for name in config_referenced_env_names if name in container_env_names)
config_referenced_missing = sorted(name for name in config_referenced_env_names if name not in container_env_names)
docker_config = read_json_file("/boot/config/plugins/dynamix.my.servers/configs/docker.config.json") or {{}}
template_mappings = docker_config.get("templateMappings") if isinstance(docker_config, dict) else {{}}
docker_config_template_mapping = None
if isinstance(template_mappings, dict) and "litellm" in template_mappings:
    value = template_mappings.get("litellm")
    docker_config_template_mapping = value if value is None or isinstance(value, str) else str(value)
container_watchdog_monitored = False
watchdog_path = pathlib.Path("/boot/config/custom/backup-scripts/container-watchdog.sh")
if watchdog_path.exists():
    try:
        container_watchdog_monitored = "litellm" in watchdog_path.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        container_watchdog_monitored = False

print(
    json.dumps(
        {{
            "ok": True,
            "container_name": container_name,
            "expected_env_names": expected_env_names,
            "container_env_names": container_env_names,
            "container_present_env_names": container_present,
            "container_missing_env_names": container_missing,
            "host_shell_present_env_names": host_present,
            "host_shell_missing_env_names": host_missing,
            "host_shell_authority_state": "non_authoritative_snapshot",
            "host_shell_snapshot_note": "Host shell env inspection is informational only; the LiteLLM delivery contract is the managed container env surface.",
            "container_image": config.get("Image"),
            "container_entrypoint": [str(item) for item in (config.get("Entrypoint") or []) if str(item).strip()],
            "container_args": [str(item) for item in (config.get("Cmd") or []) if str(item).strip()],
            "container_restart_policy": (host_config.get("RestartPolicy") or {{}}).get("Name"),
            "container_started_at": state.get("StartedAt"),
            "container_mounts": [
                {{
                    "source": mount.get("Source"),
                    "destination": mount.get("Destination"),
                    "mode": mount.get("Mode"),
                    "read_only": not bool(mount.get("RW", False)),
                }}
                for mount in mounts
                if isinstance(mount, dict)
            ],
            "container_has_compose_labels": compose_labels_present,
            "container_label_keys": label_keys,
            "config_referenced_env_names": config_referenced_env_names,
            "config_referenced_present_env_names": config_referenced_present,
            "config_referenced_missing_env_names": config_referenced_missing,
            "docker_template_matches": docker_template_matches,
            "compose_manager_matches": compose_manager_matches,
            "docker_config_template_mapping": docker_config_template_mapping,
            "container_watchdog_monitored": container_watchdog_monitored,
            "boot_config_reference_files": boot_config_reference_files,
            "appdata_files": appdata_files,
            "historical_backup_env_snapshots": historical_backup_env_snapshots,
        }},
        sort_keys=True,
    )
)
"""


def _run_remote_probe(script: str) -> tuple[bool, str]:
    command = [sys.executable, str(VAULT_SSH_PATH), f"python3 - <<'PY'\n{script}\nPY"]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        return False, str(exc)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        return False, detail[0][:240] if detail else f"vault-ssh returncode={completed.returncode}"
    return True, (completed.stdout or "").strip()


def _normalize_audit_payload(remote_payload: dict[str, Any], expected_env_names: list[str]) -> dict[str, Any]:
    observed_at = utc_now()
    expected_set = sorted({str(name).strip() for name in expected_env_names if str(name).strip()})
    container_present = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("container_present_env_names", [])
            if str(name).strip()
        }
    )
    container_missing = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("container_missing_env_names", [])
            if str(name).strip()
        }
    )
    host_present = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("host_shell_present_env_names", [])
            if str(name).strip()
        }
    )
    host_missing = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("host_shell_missing_env_names", [])
            if str(name).strip()
        }
    )
    config_referenced = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("config_referenced_env_names", [])
            if str(name).strip()
        }
    )
    config_referenced_present = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("config_referenced_present_env_names", [])
            if str(name).strip()
        }
    )
    config_referenced_missing = sorted(
        {
            str(name).strip()
            for name in remote_payload.get("config_referenced_missing_env_names", [])
            if str(name).strip()
        }
    )
    docker_template_matches = [
        str(path).strip() for path in remote_payload.get("docker_template_matches", []) if str(path).strip()
    ]
    compose_manager_matches = [
        str(path).strip() for path in remote_payload.get("compose_manager_matches", []) if str(path).strip()
    ]
    docker_config_template_mapping = remote_payload.get("docker_config_template_mapping")
    appdata_files = [str(path).strip() for path in remote_payload.get("appdata_files", []) if str(path).strip()]
    historical_backup_env_snapshots = []
    for snapshot in remote_payload.get("historical_backup_env_snapshots", []):
        if not isinstance(snapshot, dict):
            continue
        path = str(snapshot.get("path") or "").strip()
        env_names = sorted(
            {
                str(name).strip()
                for name in snapshot.get("env_names", [])
                if str(name).strip()
            }
        )
        image = str(snapshot.get("image") or "").strip()
        if not path:
            continue
        historical_backup_env_snapshots.append(
            {
                "path": path,
                "env_names": env_names,
                "image": image,
            }
        )
    runtime_owner_surface = (
        "standalone_docker_container"
        if not docker_template_matches
        and not compose_manager_matches
        and not bool(remote_payload.get("container_has_compose_labels"))
        else "template_or_compose_managed"
    )
    return {
        "version": AUDIT_VERSION,
        "surface_id": "vault-litellm-container-env",
        "service_id": "litellm",
        "host": "vault",
        "source": "vault-ssh docker inspect env-name audit",
        "observed_at": observed_at,
        "collected_at": observed_at,
        "ok": bool(remote_payload.get("ok")),
        "container_name": str(remote_payload.get("container_name") or VAULT_LITELLM_CONTAINER_NAME),
        "expected_env_names": expected_set,
        "container_present_env_names": container_present,
        "container_missing_env_names": container_missing,
        "host_shell_present_env_names": host_present,
        "host_shell_missing_env_names": host_missing,
        "config_referenced_env_names": config_referenced,
        "config_referenced_present_env_names": config_referenced_present,
        "config_referenced_missing_env_names": config_referenced_missing,
        "container_image": str(remote_payload.get("container_image") or ""),
        "container_entrypoint": [
            str(item).strip()
            for item in remote_payload.get("container_entrypoint", [])
            if str(item).strip()
        ],
        "container_args": [
            str(item).strip()
            for item in remote_payload.get("container_args", [])
            if str(item).strip()
        ],
        "container_restart_policy": str(remote_payload.get("container_restart_policy") or ""),
        "container_started_at": str(remote_payload.get("container_started_at") or ""),
        "env_change_boundary": "container_recreate_or_redeploy",
        "config_only_boundary": "docker_restart_litellm",
        "runtime_owner_surface": runtime_owner_surface,
        "container_has_compose_labels": bool(remote_payload.get("container_has_compose_labels")),
        "container_label_keys": [
            str(name).strip()
            for name in remote_payload.get("container_label_keys", [])
            if str(name).strip()
        ],
        "docker_template_matches": docker_template_matches,
        "compose_manager_matches": compose_manager_matches,
        "docker_config_template_mapping": (
            None
            if docker_config_template_mapping is None
            else str(docker_config_template_mapping).strip() or None
        ),
        "container_watchdog_monitored": bool(remote_payload.get("container_watchdog_monitored")),
        "boot_config_reference_files": [
            str(path).strip()
            for path in remote_payload.get("boot_config_reference_files", [])
            if str(path).strip()
        ],
        "appdata_files": appdata_files,
        "historical_backup_env_snapshots": historical_backup_env_snapshots,
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
    }


def _failed_audit_payload(expected_env_names: list[str], error: str) -> dict[str, Any]:
    observed_at = utc_now()
    expected = sorted({str(name).strip() for name in expected_env_names if str(name).strip()})
    return {
        "version": AUDIT_VERSION,
        "surface_id": "vault-litellm-container-env",
        "service_id": "litellm",
        "host": "vault",
        "source": "vault-ssh docker inspect env-name audit",
        "observed_at": observed_at,
        "collected_at": observed_at,
        "ok": False,
        "container_name": VAULT_LITELLM_CONTAINER_NAME,
        "expected_env_names": expected,
        "container_present_env_names": [],
        "container_missing_env_names": expected,
        "host_shell_present_env_names": [],
        "host_shell_missing_env_names": expected,
        "config_referenced_env_names": [],
        "config_referenced_present_env_names": [],
        "config_referenced_missing_env_names": [],
        "container_image": "",
        "container_entrypoint": [],
        "container_args": [],
        "container_restart_policy": "",
        "container_started_at": "",
        "env_change_boundary": "container_recreate_or_redeploy",
        "config_only_boundary": "docker_restart_litellm",
        "runtime_owner_surface": "standalone_docker_container",
        "container_has_compose_labels": False,
        "container_label_keys": [],
        "docker_template_matches": [],
        "compose_manager_matches": [],
        "docker_config_template_mapping": None,
        "container_watchdog_monitored": False,
        "boot_config_reference_files": [],
        "appdata_files": [],
        "historical_backup_env_snapshots": [],
        "container_mounts": [],
        "error": error,
    }


def collect_vault_litellm_env_audit(expected_env_names: list[str] | None = None) -> dict[str, Any]:
    expected = expected_env_names or _vault_expected_env_names()
    ok, output = _run_remote_probe(_build_remote_probe_script(VAULT_LITELLM_CONTAINER_NAME, expected))
    if not ok:
        return _failed_audit_payload(expected, output)
    try:
        remote_payload = json.loads(output)
    except json.JSONDecodeError:
        return _failed_audit_payload(expected, "invalid json from vault probe")
    return _normalize_audit_payload(remote_payload, expected)


def write_audit(path: Path = VAULT_LITELLM_ENV_AUDIT_PATH) -> dict[str, Any]:
    audit = collect_vault_litellm_env_audit()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only VAULT LiteLLM env-name audit.")
    parser.add_argument("--write", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    if args.write:
        audit = write_audit(args.write)
        print(f"Wrote {args.write}")
        return 0 if audit.get("ok") else 1

    audit = collect_vault_litellm_env_audit()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
