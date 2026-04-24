from __future__ import annotations

import asyncio
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


def test_build_payload_summarizes_result_and_review_evidence_by_family_and_project() -> None:
    module = _load_module(
        f"write_result_evidence_ledger_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_result_evidence_ledger.py",
    )

    async def _backlog_records():
        return [
            {
                "backlog_id": "backlog-builder-1",
                "title": "Ship builder result",
                "family": "builder",
                "project_id": "athanor",
                "status": "completed",
                "result_id": "result-1",
                "review_id": "",
                "created_at": 100.0,
                "completed_at": 200.0,
                "metadata": {"verification_passed": True},
            },
            {
                "backlog_id": "backlog-review-1",
                "title": "Review maintenance packet",
                "family": "maintenance",
                "project_id": "athanor",
                "status": "waiting_approval",
                "result_id": "",
                "review_id": "review-1",
                "created_at": 100.0,
                "completed_at": None,
                "metadata": {},
            },
            {
                "backlog_id": "backlog-builder-2",
                "title": "Ship builder result 2",
                "family": "builder",
                "project_id": "athanor-docs",
                "status": "completed",
                "result_id": "result-2",
                "review_id": "",
                "created_at": 100.0,
                "completed_at": 250.0,
                "metadata": {"verification_passed": True},
            },
        ]

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return await _backlog_records()

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api

    payload = asyncio.run(module.build_payload())

    assert payload["threshold_required"] == 5
    assert payload["threshold_progress"] == 3
    assert payload["threshold_met"] is False
    assert payload["result_backed_completion_count"] == 2
    assert payload["review_backed_output_count"] == 1
    assert payload["by_family"] == [
        {
            "family": "builder",
            "result_backed_completion_count": 2,
            "review_backed_output_count": 0,
            "threshold_progress": 2,
        },
        {
            "family": "maintenance",
            "result_backed_completion_count": 0,
            "review_backed_output_count": 1,
            "threshold_progress": 1,
        },
    ]
    assert payload["by_project"] == [
        {
            "project_id": "athanor",
            "result_backed_completion_count": 1,
            "review_backed_output_count": 1,
            "threshold_progress": 2,
        },
        {
            "project_id": "athanor-docs",
            "result_backed_completion_count": 1,
            "review_backed_output_count": 0,
            "threshold_progress": 1,
        },
    ]


def test_build_payload_carries_forward_historical_result_evidence_when_live_backlog_is_empty(tmp_path: Path) -> None:
    module = _load_module(
        f"write_result_evidence_ledger_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_result_evidence_ledger.py",
    )

    async def _backlog_records():
        return []

    async def _governed_truth():
        return {}

    async def _backlog_api(_governed_truth):
        return []

    completion_pass_ledger_path = tmp_path / "completion-pass-ledger.json"
    completion_pass_ledger_path.write_text(
        """
        {
          "passes": [
            {
              "pass_id": "continuity-pass-1",
              "finished_at": "2026-04-21T09:00:00+00:00",
              "healthy": true,
              "result_evidence": {
                "threshold_required": 5,
                "threshold_progress": 29,
                "threshold_met": true,
                "result_backed_completion_count": 29,
                "review_backed_output_count": 0
              }
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    module._list_backlog_records = _backlog_records
    module._load_governed_dispatch_truth = _governed_truth
    module._load_backlog_via_api = _backlog_api
    module.COMPLETION_PASS_LEDGER_PATH = completion_pass_ledger_path

    payload = asyncio.run(module.build_payload())

    assert payload["threshold_progress"] == 29
    assert payload["threshold_met"] is True
    assert payload["result_backed_completion_count"] == 29
    assert payload["review_backed_output_count"] == 0
    assert payload["evidence_basis"] == "historical_carry_forward"
    assert payload["carry_forward"] == {
        "source": "completion_pass_ledger",
        "pass_id": "continuity-pass-1",
        "finished_at": "2026-04-21T09:00:00+00:00",
        "healthy": True,
    }
