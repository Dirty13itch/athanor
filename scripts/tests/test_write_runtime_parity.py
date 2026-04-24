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


def test_build_payload_marks_clean_when_repo_runtime_and_proof_manifest_match() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._git_head = lambda path: "desk-head"
    module._git_dirty = lambda path: False
    module._remote_git_head = lambda host, path: "desk-head"
    module._remote_git_dirty = lambda host, path: False
    module._local_proof_manifest_hash = lambda: "proof-hash-1"
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1"

    payload = module.build_payload(
        existing_payload={},
        now_iso="2026-04-19T08:00:00+00:00",
    )

    assert payload["drift_class"] == "clean"
    assert payload["desk"]["commit"] == "desk-head"
    assert payload["dev"]["commit"] == "desk-head"
    assert payload["foundry"]["manifest_hash"] == "proof-hash-1"
    assert payload["last_successful_desk_to_dev_sync"] == "2026-04-19T08:00:00+00:00"
    assert payload["last_successful_dev_to_foundry_sync"] == "2026-04-19T08:00:00+00:00"


def test_build_payload_marks_proof_workspace_drift_and_preserves_prior_sync_timestamps() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._git_head = lambda path: "desk-head"
    module._git_dirty = lambda path: False
    module._remote_git_head = lambda host, path: "desk-head"
    module._remote_git_dirty = lambda host, path: False
    module._local_proof_manifest_hash = lambda: "proof-hash-2"
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1"

    payload = module.build_payload(
        existing_payload={
            "last_successful_desk_to_dev_sync": "2026-04-19T07:30:00+00:00",
            "last_successful_dev_to_foundry_sync": "2026-04-19T07:15:00+00:00",
        },
        now_iso="2026-04-19T08:00:00+00:00",
    )

    assert payload["drift_class"] == "proof_workspace_drift"
    assert payload["last_successful_desk_to_dev_sync"] == "2026-04-19T07:30:00+00:00"
    assert payload["last_successful_dev_to_foundry_sync"] == "2026-04-19T07:15:00+00:00"
    assert "proof workspace" in payload["detail"].lower()


def test_build_payload_discovers_nested_foundry_repo_root() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._git_head = lambda path: "desk-head"
    module._git_dirty = lambda path: False
    module._remote_git_dirty = lambda host, path: False
    module._local_proof_manifest_hash = lambda: "proof-hash-1"
    module._discover_remote_proof_root = lambda host, root: "/srv/athanor/live"
    module._remote_git_head = lambda host, path: "desk-head" if path in {module.DEV_RUNTIME_REPO_ROOT, "/srv/athanor/live"} else None
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1" if root == "/srv/athanor/live" else None

    payload = module.build_payload(
        existing_payload={},
        now_iso="2026-04-19T08:00:00+00:00",
    )

    assert payload["drift_class"] == "clean"
    assert payload["foundry"]["proof_workspace_root"] == "/srv/athanor/live"


def test_build_payload_accepts_tar_deployed_foundry_manifest() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._git_head = lambda path: "desk-head"
    module._git_dirty = lambda path: False
    module._remote_git_head = lambda host, path: "desk-head"
    module._remote_git_dirty = lambda host, path: False
    module._local_proof_manifest_hash = lambda: "proof-hash-1"
    module._discover_remote_proof_root = lambda host, root: "/opt/athanor"
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1" if root == "/opt/athanor" else None

    payload = module.build_payload(
        existing_payload={},
        now_iso="2026-04-19T08:00:00+00:00",
    )

    assert payload["drift_class"] == "clean"
    assert payload["foundry"]["proof_workspace_root"] == "/opt/athanor"
    assert payload["foundry"]["manifest_hash"] == "proof-hash-1"
    assert payload["foundry"]["available"] is True


def test_remote_proof_manifest_hash_prefers_remote_manifest_artifact() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._run_with_input = lambda command, input_text, timeout=20: (0, "proof-hash-1", "")

    manifest_hash = module._remote_proof_manifest_hash("foundry", "/opt/athanor", "_external/devstack")

    assert manifest_hash == "proof-hash-1"


def test_local_proof_manifest_payload_uses_git_fingerprint(tmp_path: Path) -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module.DEVSTACK_LOCAL_ROOT = tmp_path
    module._git_head = lambda path: "head-main" if path == module.REPO_ROOT else "head-devstack"
    module._git_subset_status = lambda path, paths: "dirty-surface" if path == module.REPO_ROOT else ""

    payload = module._local_proof_manifest_payload(now_iso="2026-04-19T08:00:00+00:00")

    assert payload["generated_at"] == "2026-04-19T08:00:00+00:00"
    assert payload["manifest_hash"]
    assert payload["repo_head"] == "head-main"
    assert payload["devstack_head"] == "head-devstack"


def test_check_mode_ignores_generated_at_only_drift(tmp_path: Path, monkeypatch) -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    output_path = tmp_path / "runtime-parity.json"
    monkeypatch.setattr(module, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(module, "build_payload", lambda existing_payload=None, now_iso=None: {
        "generated_at": "2026-04-19T09:00:00+00:00",
        "drift_class": "clean",
        "detail": "aligned",
        "desk": {"commit": "desk", "dirty": False, "available": True},
        "dev": {"commit": "desk", "dirty": False, "available": True},
        "foundry": {"proof_workspace_root": "/srv/athanor/live", "manifest_hash": "proof-hash", "available": True},
        "expected_local_proof_manifest_hash": "proof-hash",
        "last_successful_desk_to_dev_sync": "2026-04-19T08:00:00+00:00",
        "last_successful_dev_to_foundry_sync": "2026-04-19T08:00:00+00:00",
        "source_artifacts": {"runtime_parity": str(output_path)},
    })
    output_path.write_text(
        '{\n'
        '  "generated_at": "2026-04-19T08:00:00+00:00",\n'
        '  "drift_class": "clean",\n'
        '  "detail": "aligned",\n'
        '  "desk": {"commit": "desk", "dirty": false, "available": true},\n'
        '  "dev": {"commit": "desk", "dirty": false, "available": true},\n'
        '  "foundry": {"proof_workspace_root": "/srv/athanor/live", "manifest_hash": "proof-hash", "available": true},\n'
        '  "expected_local_proof_manifest_hash": "proof-hash",\n'
        '  "last_successful_desk_to_dev_sync": "2026-04-19T08:00:00+00:00",\n'
        '  "last_successful_dev_to_foundry_sync": "2026-04-19T08:00:00+00:00",\n'
        '  "source_artifacts": {"runtime_parity": "'
        + str(output_path).replace("\\", "\\\\")
        + '"}\n'
        '}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(module.sys, "argv", ["write_runtime_parity.py", "--check"])
    assert module.main() == 0


def test_write_mode_refreshes_generated_at_even_when_semantics_match(tmp_path: Path, monkeypatch) -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    output_path = tmp_path / "runtime-parity.json"
    monkeypatch.setattr(module, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(
        module,
        "build_payload",
        lambda existing_payload=None, now_iso=None: {
            "generated_at": "2026-04-19T09:00:00+00:00",
            "drift_class": "clean",
            "detail": "aligned",
            "desk": {"commit": "desk", "dirty": False, "available": True},
            "dev": {"commit": "desk", "dirty": False, "available": True},
            "foundry": {
                "proof_workspace_root": "/srv/athanor/live",
                "manifest_hash": "proof-hash",
                "available": True,
            },
            "expected_local_proof_manifest_hash": "proof-hash",
            "last_successful_desk_to_dev_sync": "2026-04-19T08:00:00+00:00",
            "last_successful_dev_to_foundry_sync": "2026-04-19T08:00:00+00:00",
            "source_artifacts": {"runtime_parity": str(output_path)},
        },
    )
    output_path.write_text(
        '{\n'
        '  "generated_at": "2026-04-19T08:00:00+00:00",\n'
        '  "drift_class": "clean",\n'
        '  "detail": "aligned",\n'
        '  "desk": {"commit": "desk", "dirty": false, "available": true},\n'
        '  "dev": {"commit": "desk", "dirty": false, "available": true},\n'
        '  "foundry": {"proof_workspace_root": "/srv/athanor/live", "manifest_hash": "proof-hash", "available": true},\n'
        '  "expected_local_proof_manifest_hash": "proof-hash",\n'
        '  "last_successful_desk_to_dev_sync": "2026-04-19T08:00:00+00:00",\n'
        '  "last_successful_dev_to_foundry_sync": "2026-04-19T08:00:00+00:00",\n'
        '  "source_artifacts": {"runtime_parity": "'
        + str(output_path).replace("\\", "\\\\")
        + '"}\n'
        '}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(module.sys, "argv", ["write_runtime_parity.py"])
    assert module.main() == 0
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["generated_at"] == "2026-04-19T09:00:00+00:00"


def test_build_payload_prefers_governed_sync_state_when_current_checkout_is_dirty(tmp_path: Path) -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    sync_state_path = tmp_path / "dev-runtime-repo-sync-state.json"
    sync_state_path.write_text(
        json.dumps(
            {
                "source_root": "/mnt/c/Users/Shaun/.config/superpowers/worktrees/Athanor/codex/runtime-parity-closure",
                "source_commit": "runtime-authority-head",
                "source_clean": True,
                "source_proof_manifest_hash": "proof-hash-1",
                "synced_at": "2026-04-20T01:34:11.438822+00:00",
            }
        ),
        encoding="utf-8",
    )

    module.RUNTIME_SYNC_STATE_PATH = sync_state_path
    module.PROOF_MANIFEST_PATH = tmp_path / "proof-workspace-manifest.json"
    module._git_head = lambda path: "dirty-operator-head"
    module._git_dirty = lambda path: True
    module._remote_git_head = lambda host, path: "runtime-authority-head"
    module._remote_git_dirty = lambda host, path: False
    module._local_proof_manifest_hash = lambda: "dirty-proof-hash"
    module._local_proof_manifest_payload = lambda now_iso=None: {
        "generated_at": now_iso or "2026-04-20T01:40:00+00:00",
        "manifest_hash": "dirty-proof-hash",
        "repo_head": "dirty-operator-head",
        "repo_status_available": True,
        "devstack_head": "devstack-head",
        "devstack_status_available": True,
        "source_artifacts": {
            "proof_workspace_contract": str(module.REPO_ROOT / "scripts" / "proof_workspace_contract.py"),
            "proof_workspace_manifest": str(module.PROOF_MANIFEST_PATH),
        },
    }
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1"

    payload = module.build_payload(
        existing_payload={},
        now_iso="2026-04-20T01:40:00+00:00",
    )

    assert payload["drift_class"] == "clean"
    assert payload["authority_source"] == "governed_sync_state"
    assert payload["desk"]["repo_root"] == "/mnt/c/Users/Shaun/.config/superpowers/worktrees/Athanor/codex/runtime-parity-closure"
    assert payload["desk"]["commit"] == "runtime-authority-head"
    assert payload["desk"]["dirty"] is False
    assert payload["expected_local_proof_manifest_hash"] == "proof-hash-1"
    assert payload["observed_checkout"]["commit"] == "dirty-operator-head"
    assert payload["observed_checkout"]["dirty"] is True
    assert payload["last_successful_desk_to_dev_sync"] == "2026-04-20T01:34:11.438822+00:00"


def test_build_payload_treats_managed_generated_runtime_surfaces_as_non_blocking_drift() -> None:
    module = _load_module(
        f"write_runtime_parity_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_runtime_parity.py",
    )

    module._git_head = lambda path: "desk-head"
    module._git_dirty = lambda path: False
    module._remote_git_head = lambda host, path: "desk-head"
    module._remote_git_dirty = lambda host, path: True
    module._remote_git_status_lines = lambda host, path: [
        "M audit/automation/contract-healer-latest.json",
        " M reports/truth-inventory/blocker-map.json",
        " M docs/operations/STEADY-STATE-STATUS.md",
    ]
    module._local_proof_manifest_hash = lambda: "proof-hash-1"
    module._local_proof_manifest_payload = lambda now_iso=None: {
        "generated_at": now_iso or "2026-04-20T19:00:00+00:00",
        "manifest_hash": "proof-hash-1",
        "repo_head": "desk-head",
        "repo_status_available": True,
        "devstack_head": "devstack-head",
        "devstack_status_available": True,
        "source_artifacts": {
            "proof_workspace_contract": str(module.REPO_ROOT / "scripts" / "proof_workspace_contract.py"),
            "proof_workspace_manifest": str(module.PROOF_MANIFEST_PATH),
        },
    }
    module._remote_proof_manifest_hash = lambda host, root, devstack_root: "proof-hash-1"
    module._managed_generated_doc_paths = lambda: {"docs/operations/STEADY-STATE-STATUS.md"}

    payload = module.build_payload(
        existing_payload={},
        now_iso="2026-04-20T19:00:00+00:00",
    )

    assert payload["drift_class"] == "generated_surface_drift"
    assert payload["dev"]["generated_surface_only"] is True
    assert payload["dev"]["dirty_path_count"] == 3
    assert payload["last_successful_desk_to_dev_sync"] == "2026-04-20T19:00:00+00:00"
    assert payload["last_successful_dev_to_foundry_sync"] == "2026-04-20T19:00:00+00:00"
