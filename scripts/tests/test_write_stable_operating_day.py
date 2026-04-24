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


def test_build_payload_requires_24h_of_consecutive_healthy_passes() -> None:
    module = _load_module(
        f"write_stable_operating_day_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_stable_operating_day.py",
    )

    ledger = {
        "passes": [
            {
                "pass_id": "pass-1",
                "finished_at": "2026-04-18T04:00:00+00:00",
                "healthy": True,
                "proofs": {
                    "validator_and_contract_healer": {"met": True},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
            {
                "pass_id": "pass-2",
                "finished_at": "2026-04-18T16:00:00+00:00",
                "healthy": True,
                "proofs": {
                    "validator_and_contract_healer": {"met": True},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
            {
                "pass_id": "pass-3",
                "finished_at": "2026-04-19T05:00:00+00:00",
                "healthy": True,
                "proofs": {
                    "validator_and_contract_healer": {"met": True},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
        ]
    }

    payload = module.build_payload(ledger, now_iso="2026-04-19T05:15:00+00:00")

    assert payload["met"] is True
    assert payload["included_pass_count"] == 3
    assert payload["consecutive_healthy_pass_count"] == 3
    assert payload["validator_contract_healer_streak"] == 3
    assert payload["stale_claim_streak"] == 3
    assert payload["artifact_consistency_streak"] == 3
    assert payload["covered_window_hours"] == 25.25


def test_build_payload_breaks_the_window_on_an_unhealthy_pass() -> None:
    module = _load_module(
        f"write_stable_operating_day_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_stable_operating_day.py",
    )

    ledger = {
        "passes": [
            {
                "pass_id": "pass-1",
                "finished_at": "2026-04-18T04:00:00+00:00",
                "healthy": True,
                "proofs": {
                    "validator_and_contract_healer": {"met": True},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
            {
                "pass_id": "pass-2",
                "finished_at": "2026-04-18T18:00:00+00:00",
                "healthy": False,
                "proofs": {
                    "validator_and_contract_healer": {"met": False},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
            {
                "pass_id": "pass-3",
                "finished_at": "2026-04-19T05:00:00+00:00",
                "healthy": True,
                "proofs": {
                    "validator_and_contract_healer": {"met": True},
                    "stale_claim_failures": {"met": True},
                    "artifact_consistency": {"met": True},
                },
            },
        ]
    }

    payload = module.build_payload(ledger, now_iso="2026-04-19T05:15:00+00:00")

    assert payload["met"] is False
    assert payload["consecutive_healthy_pass_count"] == 1
    assert payload["validator_contract_healer_streak"] == 1
    assert payload["covered_window_hours"] == 0.25
