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


def test_write_runtime_sync_state_records_clean_governed_source(tmp_path: Path) -> None:
    module = _load_module(
        f"sync_dev_runtime_repo_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "sync_dev_runtime_repo.py",
    )

    module.RUNTIME_SYNC_STATE_PATH = tmp_path / "dev-runtime-repo-sync-state.json"
    module._local_proof_manifest_hash = lambda: "proof-hash-1"

    module._write_runtime_sync_state(
        head_sha="c5c8686ac8cc62da5f7dca51f0bda7939bef69f7",
        synced_at_iso="2026-04-20T01:34:11.438822+00:00",
        remote="dev",
        remote_repo="/home/shaun/repos/athanor",
        temp_branch="runtime-sync/20260420-013411-c5c8686ac8cc",
        backup_branch="backup/runtime-sync-20260420-013411",
        backup_root="/home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/20260420-013411",
    )

    payload = json.loads(module.RUNTIME_SYNC_STATE_PATH.read_text(encoding="utf-8"))
    assert payload["source_root"] == str(module.REPO_ROOT)
    assert payload["source_commit"] == "c5c8686ac8cc62da5f7dca51f0bda7939bef69f7"
    assert payload["source_clean"] is True
    assert payload["source_proof_manifest_hash"] == "proof-hash-1"
    assert payload["synced_at"] == "2026-04-20T01:34:11.438822+00:00"
    assert payload["remote"] == "dev"
    assert payload["remote_repo"] == "/home/shaun/repos/athanor"
