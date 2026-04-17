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


def test_report_check_ignores_runtime_snapshot_timestamp_only_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n"
    rendered = "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n"

    assert module._report_is_stale("runtime_cutover", existing=existing, rendered=rendered) is False


def test_report_check_ignores_vault_audit_timestamp_only_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing_vault_packet = (
        "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n"
        "- Cached env audit: `2026-03-29T05:31:46Z`\n"
    )
    rendered_vault_packet = (
        "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n"
        "- Cached env audit: `2026-03-29T06:58:00Z`\n"
    )
    existing_secret_surface = (
        "- VAULT LiteLLM env audit: `2026-03-29T05:31:46Z`\n"
        "- Latest live env audit: `2026-03-29T05:31:46Z`\n"
    )
    rendered_secret_surface = (
        "- VAULT LiteLLM env audit: `2026-03-29T06:58:00Z`\n"
        "- Latest live env audit: `2026-03-29T06:58:00Z`\n"
    )

    assert (
        module._report_is_stale(
            "vault_litellm_repair_packet",
            existing=existing_vault_packet,
            rendered=rendered_vault_packet,
        )
        is False
    )
    assert (
        module._report_is_stale(
            "secret_surfaces",
            existing=existing_secret_surface,
            rendered=rendered_secret_surface,
        )
        is False
    )


def test_operator_surface_artifact_check_ignores_runtime_timestamp_only_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = json.dumps(
        {
            "frontDoor": {"id": "athanor_command_center"},
            "generatedAt": "2026-03-29T05:31:46.726811+00:00",
            "runtimeObservedAt": "2026-03-29T05:31:46.726811+00:00",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
    rendered = json.dumps(
        {
            "frontDoor": {"id": "athanor_command_center"},
            "generatedAt": "2026-03-29T06:58:00.000000+00:00",
            "runtimeObservedAt": "2026-03-29T06:58:00.000000+00:00",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"

    assert module._artifact_is_stale("operator_surfaces", existing=existing, rendered=rendered) is False


def test_operator_surface_artifact_check_still_flags_real_content_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = json.dumps(
        {
            "frontDoor": {"id": "athanor_command_center"},
            "generatedAt": "2026-03-29T05:31:46.726811+00:00",
            "runtimeObservedAt": "2026-03-29T05:31:46.726811+00:00",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
    rendered = json.dumps(
        {
            "frontDoor": {"id": "another_surface"},
            "generatedAt": "2026-03-29T06:58:00.000000+00:00",
            "runtimeObservedAt": "2026-03-29T06:58:00.000000+00:00",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"

    assert module._artifact_is_stale("operator_surfaces", existing=existing, rendered=rendered) is True


def test_generated_local_git_ignore_paths_include_publication_loop_outputs() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )

    assert "docs/operations/PUBLICATION-TRIAGE-REPORT.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "reports/truth-inventory/publication-deferred-family-queue.json" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "docs/operations/STEADY-STATE-STATUS.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "reports/truth-inventory/steady-state-status.json" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS
    assert "docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md" in module.GENERATED_LOCAL_GIT_IGNORE_PATHS


def test_docs_lifecycle_registry_generated_reports_have_generators() -> None:
    registry = json.loads((REPO_ROOT / 'config' / 'automation-backbone' / 'docs-lifecycle-registry.json').read_text(encoding='utf-8'))
    docs_by_path = {doc['path']: doc for doc in registry['documents']}

    for path in [
        'docs/operations/PROVIDER-CATALOG-REPORT.md',
        'docs/operations/OPERATOR-SURFACE-REPORT.md',
        'docs/operations/REPO-ROOTS-REPORT.md',
        'docs/operations/RUNTIME-OWNERSHIP-REPORT.md',
        'docs/operations/RUNTIME-OWNERSHIP-PACKETS.md',
        'docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md',
        'docs/operations/SECRET-SURFACE-REPORT.md',
        'docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md',
        'docs/operations/VAULT-REDIS-REPAIR-PACKET.md',
    ]:
        document = docs_by_path[path]
        assert document['class'] == 'generated'
        assert document['generator']
        assert document['validator']


def test_report_check_still_flags_real_content_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n- Status: `retired`\n"
    rendered = "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n- Status: `active`\n"

    assert module._report_is_stale("runtime_cutover", existing=existing, rendered=rendered) is True


def test_load_vault_litellm_env_audit_prefers_newer_file_payload(tmp_path: Path) -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    audit_path = tmp_path / "vault-litellm-env-audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "collected_at": "2026-04-13T19:07:53Z",
                "config_referenced_missing_env_names": ["DASHSCOPE_API_KEY"],
            }
        ),
        encoding="utf-8",
    )
    module.VAULT_LITELLM_ENV_AUDIT_PATH = audit_path

    loaded = module._load_vault_litellm_env_audit(
        {
            "vault_litellm_env_audit": {
                "collected_at": "2026-04-13T15:33:43Z",
                "config_referenced_missing_env_names": [],
            }
        }
    )

    assert loaded["config_referenced_missing_env_names"] == ["DASHSCOPE_API_KEY"]


def test_runtime_ownership_report_includes_foundry_agents_lane_evidence() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )

    registries = {
        "runtime-ownership-contract.json": {
            "version": "test",
            "promotion_gate_id": "runtime_ownership_maturity",
            "goal": "test goal",
            "implementation_authority_root_id": "desk-main",
            "runtime_authority_root_id": "dev-runtime-repo",
            "runtime_state_root_ids": ["foundry-opt-athanor"],
            "lanes": [
                {
                    "id": "foundry-agents-compose",
                    "label": "FOUNDRY athanor-agents compose lane",
                    "host": "foundry",
                    "status": "active",
                    "deployment_mode": "opt_compose_service",
                    "owner_root_ids": ["foundry-opt-athanor"],
                    "source_root_id": "desk-main",
                    "runtime_scope": "Active athanor-agents deployment",
                    "source_paths": ["projects/agents/src/athanor_agents"],
                    "runtime_paths": ["/opt/athanor/agents/src/athanor_agents"],
                    "active_surfaces": ["athanor-agents container"],
                    "execution_packet_id": "foundry-agents-compose-deploy-packet",
                    "evidence_paths": ["reports/truth-inventory/latest.json"],
                    "verification_commands": ["ssh foundry \"curl -sS http://localhost:9000/health\""],
                    "rollback_contract": "backup first",
                    "approval_boundary": "approval-gated",
                    "next_action": "Use the packet",
                }
            ],
            "promotion_criteria": [],
            "known_gaps": [],
        },
        "runtime-ownership-packets.json": {
            "version": "test",
            "packets": [
                {
                    "id": "foundry-agents-compose-deploy-packet",
                    "status": "ready_for_approval",
                    "lane_id": "foundry-agents-compose",
                    "approval_packet_type": "runtime_host_reconfiguration",
                    "goal": "normalize deploy path",
                }
            ],
        },
        "repo-roots-registry.json": {
            "roots": [
                {"id": "desk-main", "path": "C:/Athanor"},
                {"id": "dev-runtime-repo", "path": "/home/shaun/repos/athanor"},
                {"id": "foundry-opt-athanor", "path": "/opt/athanor"},
            ]
        },
    }
    module.load_registry = lambda name: registries.get(name, {})
    module._load_latest_truth_snapshot = lambda: {
        "collected_at": "2026-04-02T18:10:00Z",
        "foundry_agents_runtime_probe": {
            "ok": True,
            "detail": {
                "deployment_root": {
                    "expected_exists": True,
                    "compose_root_matches_expected": True,
                    "build_root_clean": False,
                    "nested_source_dir_exists": True,
                    "bak_codex_files": ["src/athanor_agents/server.py.bak-codex"],
                },
                "container": {
                    "running": True,
                    "status": "Up 2 minutes",
                    "compose_working_dir": "/opt/athanor/agents",
                    "compose_config_files": "/opt/athanor/agents/docker-compose.yml",
                    "module_file": "/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py",
                    "site_packages_import": True,
                },
                "control_files": [
                    {
                        "relative_path": "src/athanor_agents",
                        "kind": "directory",
                        "implementation_exists": True,
                        "runtime_exists": True,
                        "implementation_matches_runtime": False,
                    }
                ],
                "source_mirrors": [{"path": "/workspace/projects/agents/src/athanor_agents"}],
            },
        },
    }
    module._local_git_probe = lambda path: {"head": "abc1234", "dirty_count": 0, "status_sample": []}

    rendered = module.render_runtime_ownership_report()

    assert "## foundry-agents-compose" in rendered
    assert "### Live FOUNDRY agents evidence" in rendered
    assert "- Build root clean: `False`" in rendered
    assert "/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py" in rendered


def test_runtime_ownership_report_interprets_workshop_drift_for_operator_truth() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )

    registries = {
        "runtime-ownership-contract.json": {
            "version": "test",
            "promotion_gate_id": "runtime_ownership_maturity",
            "goal": "test goal",
            "implementation_authority_root_id": "desk-main",
            "runtime_authority_root_id": "dev-runtime-repo",
            "runtime_state_root_ids": ["workshop-opt-athanor"],
            "lanes": [
                {
                    "id": "workshop-vllm-compose",
                    "label": "WORKSHOP vLLM compose lane",
                    "host": "workshop",
                    "status": "active",
                    "deployment_mode": "opt_compose_service",
                    "owner_root_ids": ["workshop-opt-athanor"],
                    "source_root_id": "desk-main",
                    "runtime_scope": "Workshop worker contract",
                    "source_paths": ["ansible/roles/vllm/templates/docker-compose.yml.j2"],
                    "runtime_paths": ["/opt/athanor/vllm-node2/docker-compose.yml"],
                    "active_surfaces": ["http://workshop:8010/v1/models"],
                    "execution_packet_id": "workshop-vllm-compose-reconciliation-packet",
                    "evidence_paths": ["reports/deployment-drift/summary.md"],
                    "verification_commands": ["ssh workshop \"curl -sS http://127.0.0.1:8010/v1/models\""],
                    "rollback_contract": "backup first",
                    "approval_boundary": "approval-gated",
                    "next_action": "reconcile worker",
                },
                {
                    "id": "workshop-product-compose",
                    "label": "WORKSHOP product compose lane",
                    "host": "workshop",
                    "status": "active",
                    "deployment_mode": "opt_compose_service",
                    "owner_root_ids": ["workshop-opt-athanor"],
                    "source_root_id": "desk-main",
                    "runtime_scope": "Workshop product services",
                    "source_paths": ["ansible/roles/open-webui/templates/docker-compose.yml.j2"],
                    "runtime_paths": [
                        "/opt/athanor/open-webui/docker-compose.yml",
                        "/opt/athanor/comfyui/docker-compose.yml",
                    ],
                    "active_surfaces": ["http://workshop:3000/", "http://workshop:8188/"],
                    "execution_packet_id": "none",
                    "evidence_paths": ["reports/deployment-drift/summary.md"],
                    "verification_commands": ["ssh workshop \"docker compose ps\""],
                    "rollback_contract": "backup first",
                    "approval_boundary": "approval-gated",
                    "next_action": "repair product lane",
                },
            ],
            "promotion_criteria": [],
            "known_gaps": [],
        },
        "runtime-ownership-packets.json": {"version": "test", "packets": []},
        "repo-roots-registry.json": {
            "roots": [
                {"id": "desk-main", "path": "C:/Athanor"},
                {"id": "dev-runtime-repo", "path": "/home/shaun/repos/athanor"},
                {"id": "workshop-opt-athanor", "path": "/opt/athanor"},
            ]
        },
        "model-deployment-registry.json": {
            "lanes": [
                {
                    "id": "workshop-worker",
                    "endpoint": "http://192.168.1.225:8010/v1/models",
                    "drift_status": "drifted",
                    "evidence_source": "worker probe on :8010 was refused while vision remained live",
                },
                {
                    "id": "workshop-vision",
                    "endpoint": "http://192.168.1.225:8012/v1/models",
                    "drift_status": "aligned",
                },
            ]
        },
    }
    module.load_registry = lambda name: registries.get(name, {})
    module._load_latest_truth_snapshot = lambda: {
        "collected_at": "2026-04-14T01:48:22Z",
        "operator_surface_probe": {
            "surfaces": [
                {
                    "id": "workshop_worker_api",
                    "runtime_probe": {"detail": "URLError: timed out", "ok": False},
                },
                {
                    "id": "workshop_open_webui",
                    "runtime_probe": {
                        "detail": "URLError: [WinError 10061] No connection could be made because the target machine actively refused it",
                        "ok": False,
                    },
                },
                {
                    "id": "comfyui",
                    "runtime_probe": {"detail": "URLError: timed out", "ok": False},
                },
            ]
        },
    }
    module._load_deployment_drift_summary = lambda: [
        {
            "Id": "workshop-vllm",
            "LivePath": "/opt/athanor/vllm-node2/docker-compose.yml",
            "Status": "identical",
            "RuntimeState": "no_containers",
            "RuntimeRunningCount": "0",
            "RuntimeContainerCount": "0",
            "RuntimeOutputPath": ".\\reports\\live\\workshop-vllm.runtime.json",
        },
        {
            "Id": "workshop-open-webui",
            "LivePath": "/opt/athanor/open-webui/docker-compose.yml",
            "Status": "identical",
            "RuntimeState": "no_containers",
            "RuntimeRunningCount": "0",
            "RuntimeContainerCount": "0",
            "RuntimeOutputPath": ".\\reports\\live\\workshop-open-webui.runtime.json",
        },
        {
            "Id": "workshop-comfyui",
            "LivePath": "/opt/athanor/comfyui/docker-compose.yml",
            "Status": "different",
            "RuntimeState": "running",
            "RuntimeRunningCount": "1",
            "RuntimeContainerCount": "1",
            "RuntimeOutputPath": ".\\reports\\live\\workshop-comfyui.runtime.json",
        },
    ]
    module._local_git_probe = lambda path: {"head": "abc1234", "dirty_count": 0, "status_sample": []}

    rendered = module.render_runtime_ownership_report()

    assert "Latest deployment-drift evidence found no running containers under `/opt/athanor/vllm-node2`." in rendered
    assert "The currently aligned Workshop model lane is `workshop-vision` on `http://192.168.1.225:8012/v1/models`." in rendered
    assert "Treat the `:8010` Workshop worker as restore-or-retire debt" in rendered
    assert "Latest deployment-drift evidence found no running Open WebUI containers under `/opt/athanor/open-webui`." in rendered
    assert "ComfyUI is still running locally on WORKSHOP under `/opt/athanor/comfyui`." in rendered
    assert "reachability problem rather than a missing container" in rendered


def test_autonomy_activation_report_includes_next_phase_boundary() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    registry = {
        "version": "test",
        "status": "live_partial",
        "activation_state": "software_core_active",
        "current_phase_id": "phase_1",
        "broad_autonomy_enabled": False,
        "runtime_mutations_approval_gated": True,
        "prerequisites": [
            {
                "id": "already_done",
                "status": "verified",
                "phase_scope": "phase_1",
                "evidence_paths": ["docs/ok.md"],
            },
            {
                "id": "vault_provider_auth_repair",
                "status": "pending",
                "phase_scope": "phase_2",
                "evidence_paths": ["docs/vault.md"],
            },
        ],
        "approval_gates": [],
        "phases": [
            {
                "id": "phase_1",
                "label": "Phase One",
                "status": "active",
                "scope": "bounded",
                "enabled_agents": ["coding-agent"],
                "allowed_workload_classes": ["repo_audit"],
                "blocked_workload_classes": [],
                "allowed_loop_families": ["audit"],
                "blocked_without_approval": ["runtime mutations"],
                "entry_criteria": ["ready"],
                "success_criteria": ["green"],
            },
            {
                "id": "phase_2",
                "label": "Phase Two",
                "status": "blocked",
                "scope": "bounded_plus_domain_sidecars",
                "enabled_agents": ["coding-agent", "data-curator"],
                "allowed_workload_classes": ["repo_audit", "background_transform"],
                "blocked_workload_classes": [],
                "allowed_loop_families": ["audit", "background transforms"],
                "blocked_without_approval": ["runtime mutations"],
                "entry_criteria": ["vault fixed"],
                "success_criteria": ["broader loops live"],
            },
        ],
    }
    module.load_registry = lambda name: registry

    rendered = module.render_autonomy_activation_report()

    assert "- Next phase: `phase_2`" in rendered
    assert "- Next phase blocker count: `1`" in rendered
    assert "## Next Promotion Boundary" in rendered
    assert "| `vault_provider_auth_repair` | `pending` | `phase_2` | `docs/vault.md` |" in rendered
def test_classify_vault_auth_failure_missing_env() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "anthropic_api",
        "env_contracts": ["ANTHROPIC_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "ANTHROPIC_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "claude"}},
    }
    capture = {
        "requested_model": "claude",
        "error_snippet": "Missing Anthropic API Key - no key is set either in the environment variables or via params.",
    }
    audit = {
        "container_missing_env_names": ["ANTHROPIC_API_KEY"],
        "container_present_env_names": [],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "missing_required_env"
    assert "Restore `ANTHROPIC_API_KEY`" in classification["next_action"]


def test_classify_vault_auth_failure_present_invalid_key() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "openai_api",
        "env_contracts": ["OPENAI_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "OPENAI_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "gpt"}},
    }
    capture = {
        "requested_model": "gpt",
        "error_snippet": "AuthenticationError: OpenAIException - Incorrect API key provided.",
    }
    audit = {
        "container_missing_env_names": [],
        "container_present_env_names": ["OPENAI_API_KEY"],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "present_key_invalid"
    assert "Rotate `OPENAI_API_KEY`" in classification["next_action"]


def test_classify_vault_auth_failure_auth_mode_mismatch() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "openrouter_api",
        "env_contracts": ["OPENROUTER_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "OPENROUTER_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "openrouter"}},
    }
    capture = {
        "requested_model": "openrouter",
        "error_snippet": 'AuthenticationError: OpenrouterException - {"error":{"message":"No cookie auth credentials found","code":401}}',
    }
    audit = {
        "container_missing_env_names": ["OPENROUTER_API_KEY"],
        "container_present_env_names": [],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "auth_mode_mismatch"
    assert "Verify the upstream auth mode" in classification["next_action"]


def test_classify_vault_auth_failure_auth_surface_mismatch() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "dashscope_qwen_api",
        "env_contracts": ["DASHSCOPE_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "DASHSCOPE_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "qwen-max"}},
    }
    capture = {
        "requested_model": "qwen-max",
        "error_snippet": "AuthenticationError: DashscopeException - Incorrect API key provided.",
    }
    audit = {
        "container_missing_env_names": ["DASHSCOPE_API_KEY"],
        "container_present_env_names": [],
        "config_referenced_missing_env_names": ["DASHSCOPE_API_KEY"],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "auth_surface_mismatch"
    assert "credential-delivery path" in classification["next_action"]
    assert "os.environ" in classification["next_action"]
