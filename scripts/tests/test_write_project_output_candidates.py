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


def test_build_payload_summarizes_pending_and_accepted_candidates() -> None:
    module = _load_module(
        f"write_project_output_candidates_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_candidates.py",
    )

    contract_registry = {
        "projects": [
            {"project_id": "eoq", "label": "Empire of Broken Queens"},
            {"project_id": "lawnsignal", "label": "LawnSignal"},
        ]
    }
    candidate_records = [
        {
            "generated_at": "2026-04-20T19:32:00+00:00",
            "candidate_id": "eoq-courtyard-alpha",
            "project_id": "eoq",
            "deliverable_kind": "content_artifact",
            "approval_posture": "hybrid",
            "acceptance_state": "pending_acceptance",
            "deliverable_refs": ["projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"],
        },
        {
            "generated_at": "2026-04-20T19:40:00+00:00",
            "candidate_id": "lawnsignal-homepage-alpha",
            "project_id": "lawnsignal",
            "deliverable_kind": "ui_change",
            "approval_posture": "automated",
            "acceptance_state": "accepted",
            "deliverable_refs": ["apps/web/src/app/page.tsx"],
        },
    ]

    payload = module.build_payload(
        contract_registry=contract_registry,
        candidate_records=candidate_records,
    )

    assert payload["candidate_count"] == 2
    assert payload["pending_candidate_count"] == 1
    assert payload["pending_hybrid_acceptance_count"] == 1
    assert payload["accepted_candidate_count"] == 1
    assert payload["latest_pending_candidate"]["project_id"] == "eoq"
    assert payload["project_summaries"]["eoq"]["pending_candidate_count"] == 1
