from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_audit_payload_marks_standalone_runtime_owner_surface() -> None:
    module = _load_module(
        f"vault_litellm_env_audit_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "vault_litellm_env_audit.py",
    )
    payload = module._normalize_audit_payload(
        {
            "ok": True,
            "container_name": "litellm",
            "container_present_env_names": ["VENICE_API_KEY", "CODESTRAL_API_KEY"],
            "container_missing_env_names": ["OPENAI_API_KEY"],
            "host_shell_present_env_names": [],
            "host_shell_missing_env_names": ["OPENAI_API_KEY"],
            "config_referenced_env_names": ["OPENAI_API_KEY", "VENICE_API_KEY"],
            "config_referenced_present_env_names": ["VENICE_API_KEY"],
            "config_referenced_missing_env_names": ["OPENAI_API_KEY"],
            "container_image": "ghcr.io/berriai/litellm:test",
            "container_entrypoint": ["docker/prod_entrypoint.sh"],
            "container_args": ["--config", "/app/config.yaml", "--port", "4000"],
            "container_restart_policy": "unless-stopped",
            "container_started_at": "2026-03-29T03:58:00Z",
            "container_has_compose_labels": False,
            "docker_template_matches": [],
            "compose_manager_matches": [],
            "docker_config_template_mapping": None,
            "container_watchdog_monitored": True,
            "boot_config_reference_files": [
                "/boot/config/plugins/dynamix.my.servers/configs/docker.config.json"
            ],
            "appdata_files": ["/mnt/user/appdata/litellm/config.yaml"],
            "historical_backup_env_snapshots": [
                {
                    "path": "/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022603.json",
                    "env_names": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
                    "image": "ghcr.io/berriai/litellm:main-v1.81.9-stable",
                }
            ],
            "container_mounts": [
                {
                    "source": "/mnt/user/appdata/litellm/config.yaml",
                    "destination": "/app/config.yaml",
                    "mode": "ro",
                    "read_only": True,
                }
            ],
        },
        ["OPENAI_API_KEY", "CODESTRAL_API_KEY", "VENICE_API_KEY"],
    )

    assert payload["ok"] is True
    assert payload["surface_id"] == "vault-litellm-container-env"
    assert payload["service_id"] == "litellm"
    assert payload["host"] == "vault"
    assert payload["runtime_owner_surface"] == "standalone_docker_container"
    assert payload["container_present_env_names"] == ["CODESTRAL_API_KEY", "VENICE_API_KEY"]
    assert payload["container_missing_env_names"] == ["OPENAI_API_KEY"]
    assert payload["config_referenced_env_names"] == ["OPENAI_API_KEY", "VENICE_API_KEY"]
    assert payload["config_referenced_present_env_names"] == ["VENICE_API_KEY"]
    assert payload["config_referenced_missing_env_names"] == ["OPENAI_API_KEY"]
    assert payload["container_entrypoint"] == ["docker/prod_entrypoint.sh"]
    assert payload["container_args"] == ["--config", "/app/config.yaml", "--port", "4000"]
    assert payload["docker_config_template_mapping"] is None
    assert payload["container_watchdog_monitored"] is True
    assert payload["historical_backup_env_snapshots"] == [
        {
            "path": "/mnt/user/appdata/litellm/backups/litellm.inspect.20260330-022603.json",
            "env_names": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "image": "ghcr.io/berriai/litellm:main-v1.81.9-stable",
        }
    ]
    assert payload["boot_config_reference_files"] == [
        "/boot/config/plugins/dynamix.my.servers/configs/docker.config.json"
    ]


def test_collect_vault_litellm_env_audit_returns_failed_payload_on_probe_error(monkeypatch) -> None:
    module = _load_module(
        f"vault_litellm_env_audit_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "vault_litellm_env_audit.py",
    )

    monkeypatch.setattr(module, "_run_remote_probe", lambda script: (False, "ssh failed"))

    payload = module.collect_vault_litellm_env_audit(["OPENAI_API_KEY"])

    assert payload["ok"] is False
    assert payload["surface_id"] == "vault-litellm-container-env"
    assert payload["container_name"] == "litellm"
    assert payload["expected_env_names"] == ["OPENAI_API_KEY"]
    assert payload["error"] == "ssh failed"


def test_write_audit_persists_contract_payload(tmp_path: Path, monkeypatch) -> None:
    module = _load_module(
        f"vault_litellm_env_audit_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "vault_litellm_env_audit.py",
    )
    output = tmp_path / "vault-litellm-env-audit.json"
    monkeypatch.setattr(
        module,
        "collect_vault_litellm_env_audit",
        lambda expected_env_names=None: {
            "version": "2026-03-29.2",
            "surface_id": "vault-litellm-container-env",
            "service_id": "litellm",
            "host": "vault",
            "source": "vault-ssh docker inspect env-name audit",
            "observed_at": "2026-03-29T04:30:00Z",
            "collected_at": "2026-03-29T04:30:00Z",
            "ok": True,
            "container_name": "litellm",
            "expected_env_names": ["OPENAI_API_KEY"],
            "container_present_env_names": [],
            "container_missing_env_names": ["OPENAI_API_KEY"],
            "host_shell_present_env_names": [],
            "host_shell_missing_env_names": ["OPENAI_API_KEY"],
            "config_referenced_env_names": ["OPENAI_API_KEY"],
            "config_referenced_present_env_names": [],
            "config_referenced_missing_env_names": ["OPENAI_API_KEY"],
            "env_change_boundary": "container_recreate_or_redeploy",
            "config_only_boundary": "docker_restart_litellm",
            "runtime_owner_surface": "standalone_docker_container",
        },
    )

    payload = module.write_audit(output)

    assert payload["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["container_name"] == "litellm"
    assert rendered["container_missing_env_names"] == ["OPENAI_API_KEY"]
    assert rendered["config_referenced_missing_env_names"] == ["OPENAI_API_KEY"]
