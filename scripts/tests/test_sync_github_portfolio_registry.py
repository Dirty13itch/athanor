from __future__ import annotations

import importlib.util
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


def test_build_blocked_portfolio_snapshot_marks_external_auth_block() -> None:
    module = _load_module(
        f"sync_github_portfolio_registry_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "sync_github_portfolio_registry.py",
    )

    registry = {
        "github_portfolio": {
            "owner": "Dirty13itch",
            "repo_count": 35,
            "last_verified_at": "2026-04-14T21:49:00.612707+00:00",
            "repos": [{"github_repo": "Dirty13itch/example"}],
        }
    }

    snapshot = module._build_blocked_portfolio_snapshot(registry, "HTTP 401: Bad credentials")

    assert snapshot["sync_status"] == "external_blocked"
    assert snapshot["blocker_type"] == "external_dependency"
    assert snapshot["blocking_reason"] == "github_auth_required"
    assert snapshot["last_error"] == "HTTP 401: Bad credentials"
    assert snapshot["last_attempted_at"]
    assert snapshot["last_successful_sync_at"] == "2026-04-14T21:49:00.612707+00:00"
    assert snapshot["repo_count"] == 35
    assert snapshot["repos"] == [{"github_repo": "Dirty13itch/example"}]
