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


def test_generate_capability_intelligence_writes_all_expected_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module(
        f"generate_capability_intelligence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_capability_intelligence.py",
    )
    snapshot = {
        "version": "2026-04-17.1",
        "generated_at": "2026-04-17T23:50:00Z",
        "source_of_truth": "reports/truth-inventory/capability-intelligence.json",
        "provider_count": 1,
        "local_endpoint_count": 1,
        "providers": [
            {
                "subject_id": "openai_codex",
                "subject_kind": "provider",
                "task_class": "multi_file_implementation",
                "capability_score": 90,
            }
        ],
        "local_endpoints": [
            {
                "subject_id": "foundry-coder-lane",
                "subject_kind": "local_endpoint",
                "task_class": "multi_file_implementation",
                "capability_score": 95,
            }
        ],
        "degraded_subjects": [],
    }
    monkeypatch.setattr(module, "build_capability_intelligence_snapshot", lambda: snapshot)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_capability_intelligence.py",
            "--write-dir",
            str(tmp_path),
        ],
    )

    assert module.main() == 0

    capability_payload = json.loads((tmp_path / "capability-intelligence.json").read_text(encoding="utf-8"))
    local_payload = json.loads((tmp_path / "local-endpoint-capability.json").read_text(encoding="utf-8"))
    history_payload = json.loads((tmp_path / "capability-refresh-history.json").read_text(encoding="utf-8"))

    assert capability_payload["providers"][0]["subject_id"] == "openai_codex"
    assert local_payload["local_endpoints"][0]["subject_id"] == "foundry-coder-lane"
    assert history_payload["history"][0]["provider_count"] == 1
