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
