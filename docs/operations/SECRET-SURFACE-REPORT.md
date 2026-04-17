# Secret Surface Report

Generated from `config/automation-backbone/credential-surface-registry.json` plus the cached VAULT env audit artifact by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-16.1`
- Surfaces tracked: `6`
- VAULT LiteLLM env audit: `2026-04-17T19:56:21Z`

### Remediation states

| Remediation state | Count |
| --- | --- |
| `managed` | 5 |
| `remediation_required` | 1 |

### VAULT provider blockers

- Missing-secret env blockers: none
- Present-key, auth-mode, or auth-surface mismatch failures: `dashscope_qwen_api (auth_surface_mismatch)`, `google_gemini_api (auth_surface_mismatch)`, `openai_api (auth_surface_mismatch)`, `openrouter_api (auth_surface_mismatch)`
- Unresolved auth failures: none
- Direct env gaps not currently blocking a live observed path: `anthropic_api`, `deepseek_api`, `mistral_codestral_api`, `moonshot_api`, `venice_api`, `zai_api`

| Surface | Host | Delivery | Target | Risk | Remediation |
| --- | --- | --- | --- | --- | --- |
| `dev-user-crontab-inline-env` | `dev` | `cron_wrapper_envfile` | `cron_wrapper_envfile` | `managed_runtime_surface` | `managed` |
| `dev-systemd-env-surfaces` | `dev` | `service_envfile` | `service_envfile` | `managed_runtime_surface` | `managed` |
| `vault-litellm-container-env` | `vault` | `container_env` | `container_env` | `managed_container_surface` | `remediation_required` |
| `script-lane-redis-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |
| `script-lane-vault-ssh-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |
| `script-lane-litellm-gateway-auth` | `desk` | `local_runtime_envfile` | `local_runtime_envfile` | `managed_runtime_surface` | `managed` |

## dev-user-crontab-inline-env

- Path: `/var/spool/cron/crontabs/shaun -> /home/shaun/.athanor/runtime.env`
- Owner surface: recurring subscription and operator jobs
- Env contracts: `ATHANOR_LITELLM_API_KEY`, `LITELLM_MASTER_KEY`, `ATHANOR_AGENT_API_TOKEN`
- Observed state: `envfile_backed`
- Target delivery: `cron_wrapper_envfile`
- Remediation state: `managed`
- Ask-first required: `True`
- Managed by: `dev-runtime-ops`
- Evidence sources: `DEV runtime inventory probe 2026-03-25`, `DEV ssh crontab audit 2026-03-26`, `DEV cron envfile normalization 2026-03-26`
- Recommended actions: `Keep recurring Athanor user-crontab jobs sourcing /home/shaun/.athanor/runtime.env through BASH_ENV instead of reintroducing inline secret-bearing assignments.`, `Keep the dedicated /etc/cron.d/athanor-* files separate from the user-crontab envfile contract so system cron and operator cron do not get conflated.`, `Back up the user crontab before future secret-delivery edits and rerun the truth collector after each live change.`
- Notes: `The Shaun user crontab now uses SHELL=/bin/bash plus BASH_ENV=/home/shaun/.athanor/runtime.env for secret-bearing Athanor jobs.`, `The 2026-03-26 follow-up verified the inline secret-bearing assignments were removed from the user crontab.`, `The 2026-03-26 audit confirmed /etc/cron.d/athanor-drift-check and /etc/cron.d/athanor-overnight remain separate non-user cron surfaces.`, `Presence is tracked here; secret values are intentionally omitted.`

## dev-systemd-env-surfaces

- Path: `/etc/systemd/system/athanor-*.service`
- Owner surface: live Athanor systemd units
- Env contracts: none
- Observed state: `envfile_or_envless_contract`
- Target delivery: `service_envfile`
- Remediation state: `managed`
- Ask-first required: `True`
- Managed by: `dev-runtime-ops`
- Evidence sources: `DEV runtime inventory probe 2026-03-25`, `DEV ssh systemd audit 2026-03-26`, `DEV systemd envfile verification 2026-03-26`
- Recommended actions: `Keep env-bearing Athanor units on explicit EnvironmentFile delivery and treat envless units as a deliberate contract instead of implicit shell inheritance.`, `Back up touched unit files before future runtime edits and rerun systemctl plus the truth collector after each change.`, `Keep dashboard, classifier, and heartbeat as the reference envfile-backed services for future normalization work.`
- Notes: `The reviewed Athanor systemd estate now uses EnvironmentFile where runtime configuration is required and otherwise stays envless by explicit contract.`, `The 2026-03-26 verification confirmed athanor-classifier.service, athanor-dashboard.service, and athanor-heartbeat.service are EnvironmentFile-backed.`

## vault-litellm-container-env

- Path: `appdata/litellm`
- Owner surface: LiteLLM upstream provider keys plus local master-key contract
- Env contracts: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `CODESTRAL_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `MOONSHOT_API_KEY`, `DASHSCOPE_API_KEY`, `VENICE_API_KEY`, `ZAI_API_KEY`, `OPENROUTER_API_KEY`, `LITELLM_MASTER_KEY`, `REDIS_PASSWORD`
- Observed state: `partial_runtime_env_presence`
- Target delivery: `container_env`
- Remediation state: `remediation_required`
- Ask-first required: `True`
- Managed by: `vault-runtime-ops`
- Evidence sources: `VAULT LiteLLM template and appdata layout review 2026-03-25`, `VAULT live docker inspect env-presence audit 2026-03-29`, `VAULT provider-specific LiteLLM probe 2026-03-29`, `VAULT LiteLLM implementation-authority role parity review 2026-03-29`, `VAULT live docker inspect env-presence audit 2026-04-08`, `VAULT live docker inspect env-presence audit 2026-04-16`
- Recommended actions: `Keep LiteLLM provider keys in the managed VAULT container env surface or an equivalent host-local secret source.`, `Keep the live VAULT container env aligned with every provider key referenced by ansible/roles/vault-litellm/templates/litellm_config.yaml.j2.`, `Treat the tracked repo as env-contract authority only; the remaining missing keys are not recoverable from tracked source or the reviewed DESK-local runtime env surfaces.`, `Use the generated VAULT auth-repair packet to decide whether a lane needs missing-key restoration, present-key rotation, or auth-mode review before recreating or redeploying the container.`, `Keep repo truth focused on env contracts, delivery boundaries, and repair sequencing rather than freezing point-in-time live env presence into this registry.`, `Do not move provider keys into tracked source or ad hoc shell history during future routing changes.`
- Notes: `Backed by the current LiteLLM template and runtime appdata layout.`, `Implementation-authority LiteLLM env-contract parity is already fixed and validator-enforced; the remaining work is runtime-only and should be driven by the current env-audit plus provider-probe artifacts.`, `This registry tracks contract names, delivery surface, and remediation posture; the generated reports own point-in-time present or missing env observations.`, `The running VAULT LiteLLM surface currently appears as a standalone Docker container with a config bind mount, not a discovered compose-managed env source.`, `Tracked `ansible/host_vars/vault.yml` does not hold the `vault_*` secret aliases for the remaining missing LiteLLM keys; the intended owner pattern is an untracked Ansible secret-vars surface adjacent to the VAULT host config or an equivalent host-local secret source.`, `This registry tracks contract names only, not secret material.`, `The live VAULT config now proves `LITELLM_MASTER_KEY` is part of the same container-env delivery contract as the provider keys and should stay modeled here.`
- Latest live env audit: `2026-04-17T19:56:21Z`
- Audit status: `failed`
- Runtime owner surface: `standalone_docker_container`
- Container image: `unknown`
- Restart policy: `unknown`
- Env-change boundary: `container_recreate_or_redeploy`
- Config-only boundary: `docker_restart_litellm`
- Container envs present: none
- Container envs missing: `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- Config-referenced envs present at runtime: none
- Config-referenced envs missing at runtime: none
- Host shell envs present (informational snapshot only; not the LiteLLM delivery contract): none
- Host shell envs missing (informational snapshot only; not a blocking delivery contract by itself): `ANTHROPIC_API_KEY`, `CODESTRAL_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `LITELLM_MASTER_KEY`, `MISTRAL_API_KEY`, `MOONSHOT_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `REDIS_PASSWORD`, `VENICE_API_KEY`, `ZAI_API_KEY`
- dockerMan template matches: none
- Compose-manager matches: none
- docker.config.json template mapping: `none`
- container-watchdog monitors litellm: `false`
- Boot-config references: none
- Container launch command: `unknown`
- Appdata files: none
- Historical inspect backups: none
- Repair packet: [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md)
- Audit error: `Command '['/usr/bin/python3', '/mnt/c/Athanor/scripts/vault-ssh.py', 'python3 - <<\'PY\'\nimport glob\nimport json\nimport os\nimport pathlib\nimport re\nimport shlex\nimport subprocess\n\ncontainer_name = \'litellm\'\nexpected_env_names = [\'ANTHROPIC_API_KEY\', \'CODESTRAL_API_KEY\', \'DASHSCOPE_API_KEY\', \'DEEPSEEK_API_KEY\', \'GEMINI_API_KEY\', \'GOOGLE_API_KEY\', \'LITELLM_MASTER_KEY\', \'MISTRAL_API_KEY\', \'MOONSHOT_API_KEY\', \'OPENAI_API_KEY\', \'OPENROUTER_API_KEY\', \'REDIS_PASSWORD\', \'VENICE_API_KEY\', \'ZAI_API_KEY\']\n\n\ndef env_names(values):\n    names = []\n    for item in values or []:\n        if isinstance(item, str) and "=" in item:\n            names.append(item.split("=", 1)[0])\n    return sorted({name for name in names if name})\n\n\ndef limited_matches(root, *, needle="litellm", max_depth=4, require_file=False):\n    root_path = pathlib.Path(root)\n    if not root_path.exists():\n        return []\n    matches = []\n    for path in root_path.rglob("*"):\n        try:\n            depth = len(path.relative_to(root_path).parts)\n        except Exception:\n            continue\n        if depth > max_depth:\n            continue\n        if require_file and not path.is_file():\n            continue\n        if needle in str(path).lower():\n            matches.append(str(path))\n    return sorted(matches)[:50]\n\n\ndef grep_matches(roots, pattern, max_results=20):\n    filtered_roots = [root for root in roots if root]\n    if not filtered_roots:\n        return []\n    shell_roots = " ".join(shlex.quote(root) for root in filtered_roots)\n    command = f"grep -R -l -E {shlex.quote(pattern)} {shell_roots} 2>/dev/null | sed -n \'1,{max_results}p\'"\n    result = subprocess.run(["sh", "-lc", command], capture_output=True, text=True, check=False)\n    if result.returncode not in (0, 1):\n        return []\n    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})\n\n\ndef read_json_file(path):\n    try:\n        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))\n    except Exception:\n        return None\n\n\ndef inspect_backup_env_snapshots(pattern):\n    snapshots = []\n    for raw_path in sorted(glob.glob(pattern))[:20]:\n        payload = read_json_file(raw_path)\n        if payload is None:\n            continue\n        obj = payload[0] if isinstance(payload, list) and payload else payload\n        if not isinstance(obj, dict):\n            continue\n        snapshots.append(\n            {\n                "path": raw_path,\n                "env_names": env_names((obj.get("Config") or {}).get("Env") or []),\n                "image": str(((obj.get("Config") or {}).get("Image")) or ""),\n            }\n        )\n    return snapshots\n\n\ndef config_env_refs(config_path):\n    path = pathlib.Path(config_path)\n    if not path.exists():\n        return []\n    try:\n        text = path.read_text(encoding="utf-8", errors="ignore")\n    except Exception:\n        return []\n    return sorted(\n        {\n            match.strip()\n            for match in re.findall(r"os\\.environ/([A-Z0-9_]+)", text)\n            if str(match).strip()\n        }\n    )\n\n\ninspect_result = subprocess.run(\n    ["docker", "inspect", container_name],\n    capture_output=True,\n    text=True,\n    check=False,\n)\nif inspect_result.returncode != 0:\n    detail = (inspect_result.stderr or inspect_result.stdout or "").strip().splitlines()\n    print(\n        json.dumps(\n            {\n                "ok": False,\n                "container_name": container_name,\n                "expected_env_names": expected_env_names,\n                "error": detail[0][:240] if detail else f"docker inspect returncode={inspect_result.returncode}",\n            },\n            sort_keys=True,\n        )\n    )\n    raise SystemExit(0)\n\npayload = json.loads(inspect_result.stdout)[0]\nconfig = payload.get("Config") or {}\nhost_config = payload.get("HostConfig") or {}\nstate = payload.get("State") or {}\nmounts = payload.get("Mounts") or []\nlabels = config.get("Labels") or {}\nlabel_keys = [str(key).strip() for key in labels.keys() if str(key).strip()]\ncompose_labels_present = any(\n    key.startswith("com.docker.compose.")\n    or key.startswith("com.docker.stack.")\n    or "compose" in key\n    for key in label_keys\n)\ncontainer_env_names = env_names(config.get("Env") or [])\ncontainer_present = sorted(name for name in expected_env_names if name in container_env_names)\ncontainer_missing = sorted(name for name in expected_env_names if name not in container_env_names)\nhost_present = sorted(name for name in expected_env_names if os.environ.get(name))\nhost_missing = sorted(name for name in expected_env_names if not os.environ.get(name))\ndocker_template_matches = limited_matches("/boot/config/plugins/dockerMan/templates-user", max_depth=2)\ncompose_manager_matches = limited_matches("/boot/config/plugins/compose.manager", max_depth=4)\nboot_config_reference_files = grep_matches(\n    ["/boot/config"],\n    r"ghcr.io/berriai/litellm|/mnt/user/appdata/litellm|docker/prod_entrypoint\\.sh|(^|[^A-Za-z])litellm([^A-Za-z]|$)",\n)\nappdata_files = limited_matches("/mnt/user/appdata/litellm", needle="", max_depth=2, require_file=True)\nhistorical_backup_env_snapshots = inspect_backup_env_snapshots("/mnt/user/appdata/litellm/backups/litellm.inspect*.json")\nconfig_referenced_env_names = config_env_refs("/mnt/user/appdata/litellm/config.yaml")\nconfig_referenced_present = sorted(name for name in config_referenced_env_names if name in container_env_names)\nconfig_referenced_missing = sorted(name for name in config_referenced_env_names if name not in container_env_names)\ndocker_config = read_json_file("/boot/config/plugins/dynamix.my.servers/configs/docker.config.json") or {}\ntemplate_mappings = docker_config.get("templateMappings") if isinstance(docker_config, dict) else {}\ndocker_config_template_mapping = None\nif isinstance(template_mappings, dict) and "litellm" in template_mappings:\n    value = template_mappings.get("litellm")\n    docker_config_template_mapping = value if value is None or isinstance(value, str) else str(value)\ncontainer_watchdog_monitored = False\nwatchdog_path = pathlib.Path("/boot/config/custom/backup-scripts/container-watchdog.sh")\nif watchdog_path.exists():\n    try:\n        container_watchdog_monitored = "litellm" in watchdog_path.read_text(encoding="utf-8", errors="ignore").lower()\n    except Exception:\n        container_watchdog_monitored = False\n\nprint(\n    json.dumps(\n        {\n            "ok": True,\n            "container_name": container_name,\n            "expected_env_names": expected_env_names,\n            "container_env_names": container_env_names,\n            "container_present_env_names": container_present,\n            "container_missing_env_names": container_missing,\n            "host_shell_present_env_names": host_present,\n            "host_shell_missing_env_names": host_missing,\n            "host_shell_authority_state": "non_authoritative_snapshot",\n            "host_shell_snapshot_note": "Host shell env inspection is informational only; the LiteLLM delivery contract is the managed container env surface.",\n            "container_image": config.get("Image"),\n            "container_entrypoint": [str(item) for item in (config.get("Entrypoint") or []) if str(item).strip()],\n            "container_args": [str(item) for item in (config.get("Cmd") or []) if str(item).strip()],\n            "container_restart_policy": (host_config.get("RestartPolicy") or {}).get("Name"),\n            "container_started_at": state.get("StartedAt"),\n            "container_mounts": [\n                {\n                    "source": mount.get("Source"),\n                    "destination": mount.get("Destination"),\n                    "mode": mount.get("Mode"),\n                    "read_only": not bool(mount.get("RW", False)),\n                }\n                for mount in mounts\n                if isinstance(mount, dict)\n            ],\n            "container_has_compose_labels": compose_labels_present,\n            "container_label_keys": label_keys,\n            "config_referenced_env_names": config_referenced_env_names,\n            "config_referenced_present_env_names": config_referenced_present,\n            "config_referenced_missing_env_names": config_referenced_missing,\n            "docker_template_matches": docker_template_matches,\n            "compose_manager_matches": compose_manager_matches,\n            "docker_config_template_mapping": docker_config_template_mapping,\n            "container_watchdog_monitored": container_watchdog_monitored,\n            "boot_config_reference_files": boot_config_reference_files,\n            "appdata_files": appdata_files,\n            "historical_backup_env_snapshots": historical_backup_env_snapshots,\n        },\n        sort_keys=True,\n    )\n)\n\nPY']' timed out after 45 seconds`

## script-lane-redis-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: automation record persistence
- Env contracts: `ATHANOR_REDIS_URL`, `ATHANOR_REDIS_PASSWORD`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `Automation artifact persistence failure on DESK shell 2026-03-25`, `DESK runtime env audit 2026-03-26`, `DESK runtime env bootstrap 2026-03-26`, `Contract healer and recovery evidence persistence succeeded 2026-03-26`
- Recommended actions: `Keep ATHANOR_REDIS_URL and ATHANOR_REDIS_PASSWORD in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE rather than ad hoc shell exports.`, `Use python scripts/runtime_env.py --check ATHANOR_REDIS_URL ATHANOR_REDIS_PASSWORD to verify the managed local env surface without printing secret values.`, `Keep Redis-backed automation scripts failing closed if the managed local env surface disappears.`
- Notes: `The managed local runtime env surface is present and resolves both ATHANOR_REDIS_URL and ATHANOR_REDIS_PASSWORD.`, `Redis-backed automation evidence now persists through the managed local env surface instead of ad hoc shell exports.`

## script-lane-vault-ssh-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: VAULT SSH-backed operator access
- Env contracts: `ATHANOR_VAULT_KEY_PATH`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `VAULT browser-terminal recovery 2026-04-02`, `DESK runtime env audit 2026-04-02`, `DESK direct vault-ssh helper verification 2026-04-02`
- Recommended actions: `Keep ATHANOR_VAULT_KEY_PATH in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE so the VAULT helpers use the managed local SSH key path instead of ad hoc shell state or browser-only recovery.`, `Use python scripts/runtime_env.py --check ATHANOR_VAULT_KEY_PATH and python scripts/vault-ssh.py "echo CONNECTED && hostname" to verify the managed local env surface without printing secret values.`, `Treat ATHANOR_VAULT_USER and ATHANOR_VAULT_PASSWORD as optional overrides; the current contract uses the managed key path and the default VAULT root user.`
- Notes: `The managed local runtime env surface now carries the explicit VAULT SSH key-path contract needed by scripts/vault-ssh.py and scripts/ssh-vault.ps1.`, `DESK-side VAULT operator access no longer depends on the authenticated browser terminal as the only working recovery path.`

## script-lane-litellm-gateway-auth

- Path: `~/.athanor/runtime.env`
- Owner surface: gateway-backed CLI and editor adapters
- Env contracts: `ATHANOR_LITELLM_API_KEY`, `ATHANOR_LITELLM_URL`
- Observed state: `runtime_envfile_present`
- Target delivery: `local_runtime_envfile`
- Remediation state: `managed`
- Ask-first required: `False`
- Managed by: `desk-session-context`
- Evidence sources: `DESK gateway env audit 2026-04-14`, `Goose wrapper smoke via managed runtime env 2026-04-14`, `Aider wrapper smoke via managed runtime env 2026-04-14`
- Recommended actions: `Keep the canonical DESK LiteLLM contract anchored in ~/.athanor/runtime.env or ATHANOR_RUNTIME_ENV_FILE instead of ad hoc shell exports.`, `Allow LITELLM_API_KEY or LITELLM_MASTER_KEY to satisfy ATHANOR_LITELLM_API_KEY through scripts/runtime_env.py rather than copying the same secret into multiple local files.`, `Use python scripts/runtime_env.py --check ATHANOR_LITELLM_URL ATHANOR_LITELLM_API_KEY OPENAI_API_BASE OPENAI_API_KEY plus the Goose and Aider wrappers to verify the managed local env surface without printing secret values.`
- Notes: `The DESK managed runtime env surface now resolves the Athanor LiteLLM gateway contract for Goose, Aider, and generated editor-adapter profiles.`, `Compatibility envs OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_HOST, and OPENAI_BASE_PATH are derived at launcher time from the canonical Athanor contract rather than being tracked as independent secret-bearing surface entries.`
