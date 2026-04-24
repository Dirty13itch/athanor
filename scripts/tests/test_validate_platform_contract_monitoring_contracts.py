from __future__ import annotations

import importlib.util
import subprocess
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


def _build_operator_surfaces(module):
    surfaces = []
    for surface_id in sorted(
        module.PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS | module.PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS
    ):
        surfaces.append(
            {
                "id": surface_id,
                "label": f"Label for {surface_id}",
                "node": "vault",
            }
        )
    return {"surfaces": surfaces}


def _build_vault_host_vars(module, operator_surfaces):
    surface_by_id = {
        entry["id"]: entry
        for entry in operator_surfaces["surfaces"]
    }
    return {
        "prometheus_probe_targets": [
            {
                "id": surface_id,
                "name": surface_by_id[surface_id]["label"],
                "url": f"http://example.test/{surface_id}",
                "node_id": surface_by_id[surface_id]["node"],
            }
            for surface_id in sorted(module.PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS)
        ]
    }


def test_vault_prometheus_probe_contract_accepts_canonical_surface_ids() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    operator_surfaces = _build_operator_surfaces(module)
    vault_host_vars = _build_vault_host_vars(module, operator_surfaces)
    errors: list[str] = []

    module._validate_vault_prometheus_probe_contract(
        errors=errors,
        operator_surfaces=operator_surfaces,
        vault_host_vars=vault_host_vars,
    )

    assert errors == []


def test_vault_prometheus_probe_contract_rejects_stale_alias_ids() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    operator_surfaces = _build_operator_surfaces(module)
    vault_host_vars = _build_vault_host_vars(module, operator_surfaces)
    for target in vault_host_vars["prometheus_probe_targets"]:
        if target["id"] == "foundry_coordinator_api":
            target["id"] = "foundry-coordinator"
            break
    errors: list[str] = []

    module._validate_vault_prometheus_probe_contract(
        errors=errors,
        operator_surfaces=operator_surfaces,
        vault_host_vars=vault_host_vars,
    )

    assert any("foundry-coordinator" in error for error in errors)
    assert any("foundry_coordinator_api" in error for error in errors)


def test_docs_lifecycle_registry_shape_rejects_duplicate_paths() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    errors: list[str] = []

    lifecycle_paths = module._validate_docs_lifecycle_registry_shape(
        errors,
        {
            "documents": [
                {"path": "docs/operations/OPERATOR-SURFACE-REPORT.md"},
                {"path": "docs/operations/OPERATOR-SURFACE-REPORT.md"},
            ]
        },
    )

    assert "docs/operations/OPERATOR-SURFACE-REPORT.md" in lifecycle_paths
    assert any("duplicate paths" in error for error in errors)


def test_repo_structure_contract_rejects_root_and_scripts_tmp_files(tmp_path: Path) -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "tmp_probe.py").write_text("print('scratch')\n", encoding="utf-8")
    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "tmp_refresh.py").write_text("print('scratch')\n", encoding="utf-8")

    module.REPO_ROOT = fake_root
    module.SCRIPTS_DIR = scripts_dir

    errors: list[str] = []
    module._validate_repo_structure_contract(errors)

    assert any("tmp_probe.py" in error for error in errors)
    assert any("scripts/tmp_refresh.py" in error for error in errors)


def test_run_generator_check_applies_timeout() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    calls: list[dict[str, object]] = []

    def _fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        raise subprocess.TimeoutExpired(cmd=[sys.executable, "scripts/example.py", "--check"], timeout=30)

    original_run = module.subprocess.run
    module.subprocess.run = _fake_run
    try:
        result = module._run_generator_check(["scripts/example.py"])
    finally:
        module.subprocess.run = original_run

    assert calls
    assert calls[0]["kwargs"]["timeout"] == module.GENERATED_DOC_CHECK_TIMEOUT_SECONDS
    assert result.returncode == 124
    assert "timed out" in result.stderr


def test_allowed_ralph_continuity_stop_states_include_proof_required() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    assert "proof_required" in module.ALLOWED_RALPH_CONTINUITY_STOP_STATES


def test_parse_ignored_generated_doc_args_collects_paths() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    ignored, remaining = module._parse_ignored_generated_doc_args(
        [
            "--ignore-generated-doc",
            "docs\\operations\\ATHANOR-FULL-SYSTEM-AUDIT.md",
            "--ignore-generated-doc",
            "./docs/operations/AUDIT-REMEDIATION-BACKLOG.md",
        ]
    )

    assert ignored == {
        "docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md",
        "docs/operations/AUDIT-REMEDIATION-BACKLOG.md",
    }
    assert remaining == []


def test_required_publication_slice_ids_include_execution_kernel_queue_state() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    assert module.REQUIRED_PUBLICATION_SLICE_IDS[-8:] == [
        "agent-execution-kernel-scheduler-and-research-loop",
        "agent-execution-kernel-self-improvement-and-proving",
        "agent-execution-kernel-support-and-tests",
        "agent-route-contract-surface-code",
        "agent-route-contract-tests",
        "control-plane-ralph-and-truth-writers",
        "control-plane-proof-generators-and-validators",
        "control-plane-deploy-and-runtime-ops-helpers",
    ]


def test_load_subscription_policy_supports_workspace_agents_layout(tmp_path: Path) -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    fake_root = tmp_path / "workspace"
    policy_path = fake_root / "agents" / "config" / "subscription-routing-policy.yaml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text("providers:\n  athanor_local:\n    routing_posture: ordinary_auto\n", encoding="utf-8")

    module.REPO_ROOT = fake_root

    policy = module._load_subscription_policy()

    assert "athanor_local" in policy["providers"]


def test_runtime_proof_context_skips_off_host_external_paths(monkeypatch) -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    monkeypatch.setattr(module, "RUNTIME_PROOF_CONTEXT", True)

    assert module._skip_runtime_proof_external_path("C:/Users/Shaun/dev/portfolio/AI-Dev-Control-Plane") is True
    assert module._skip_runtime_proof_external_path("C:/Athanor/config/automation-backbone/lane-selection-matrix.json") is False
    assert module._skip_runtime_proof_external_path("C:/athanor-devstack/docs/CODEX-STATE.md") is False
    assert module._skip_runtime_proof_external_path("C:/Codex System Config/STATUS.md") is True


def test_runtime_proof_context_ignores_git_repo_generator_failures(monkeypatch) -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )
    monkeypatch.setattr(module, "RUNTIME_PROOF_CONTEXT", True)

    assert module._should_ignore_generated_doc_failure("fatal: not a git repository") is True
    assert module._should_ignore_generated_doc_failure("GIT_DISCOVERY_ACROSS_FILESYSTEM not set") is True
    assert module._should_ignore_generated_doc_failure("[Errno 30] Read-only file system: '/workspace/docs/operations/REPO-ROOTS-REPORT.md'") is True
    assert module._should_ignore_generated_doc_failure("docs/operations/REPO-ROOTS-REPORT.md is stale") is False


def test_runtime_proof_context_skips_generated_doc_freshness_validation(monkeypatch) -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    monkeypatch.setattr(module, "RUNTIME_PROOF_CONTEXT", True)
    assert module._skip_generated_doc_freshness_validation() is True

    monkeypatch.setattr(module, "RUNTIME_PROOF_CONTEXT", False)
    assert module._skip_generated_doc_freshness_validation() is False


def test_external_blocked_github_portfolio_snapshot_satisfies_contract() -> None:
    module = _load_module(
        f"validate_platform_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "validate_platform_contract.py",
    )

    registry_snapshot = {
        "owner": "Dirty13itch",
        "last_verified_at": "2026-04-14T21:49:00.612707+00:00",
        "repo_count": 35,
    }
    blocked_snapshot = {
        "owner": "Dirty13itch",
        "sync_status": "external_blocked",
        "blocker_type": "external_dependency",
        "blocking_reason": "github_auth_required",
        "last_attempted_at": "2026-04-19T02:47:24.122158+00:00",
        "last_error": "HTTP 401: Bad credentials",
        "last_successful_sync_at": "2026-04-14T21:49:00.612707+00:00",
    }

    assert module._github_portfolio_snapshot_contract_errors(blocked_snapshot, registry_snapshot) == []
