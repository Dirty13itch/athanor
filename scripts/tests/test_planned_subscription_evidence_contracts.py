from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest


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


def test_record_planned_subscription_evidence_persists_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"record_planned_subscription_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "record_planned_subscription_evidence.py",
    )
    output = tmp_path / "planned-subscription-evidence.json"

    monkeypatch.setattr(
        module,
        "load_planned_subscription",
        lambda family_id: {"id": family_id, "provider_id": "zai_glm_coding", "activation_gate": "supported_tool_usage_observed"},
    )
    monkeypatch.setattr(
        module,
        "load_catalog_provider",
        lambda provider_id: {"id": provider_id, "label": "Z.ai GLM Coding"},
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_planned_subscription_evidence.py",
            "--family-id",
            "glm_coding_plan",
            "--status",
            "tooling_ready",
            "--source",
            "planned-subscription-tooling-probe",
            "--request-surface",
            "local command probe",
            "--required-command",
            "codex",
            "--available-command",
            "codex",
            "--required-env-contract",
            "ZAI_API_KEY",
            "--note",
            "catalog_api_configured=true",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    capture = payload["captures"][0]
    assert capture["family_id"] == "glm_coding_plan"
    assert capture["provider_id"] == "zai_glm_coding"
    assert capture["status"] == "tooling_ready"
    assert capture["available_commands"] == ["codex"]
    assert capture["required_env_contracts"] == ["ZAI_API_KEY"]


def test_probe_planned_subscription_evidence_derives_tooling_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"probe_planned_subscription_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "probe_planned_subscription_evidence.py",
    )
    output = tmp_path / "planned-subscription-evidence.json"

    monkeypatch.setattr(
        module,
        "load_planned_subscription",
        lambda family_id: {"id": family_id, "provider_id": "zai_glm_coding", "activation_gate": "supported_tool_usage_observed"},
    )
    monkeypatch.setattr(
        module,
        "load_catalog_provider",
        lambda provider_id: {
            "id": provider_id,
            "label": "Z.ai GLM Coding",
            "env_contracts": ["ZAI_API_KEY"],
            "observed_runtime": {"api_configured": True},
            "evidence": {"tooling_probe": {"status": "supported_tools_present", "supported_commands": ["codex", "gemini"]}},
        },
    )
    monkeypatch.setattr(module.shutil, "which", lambda command: f"/tmp/{command}" if command == "codex" else None)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe_planned_subscription_evidence.py",
            "--family-id",
            "glm_coding_plan",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    capture = payload["captures"][0]
    assert capture["status"] == "tooling_ready"
    assert capture["available_commands"] == ["codex"]
    assert capture["required_commands"] == ["codex", "gemini"]


def test_record_supported_tool_usage_wraps_planned_subscription_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"record_supported_tool_usage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "record_supported_tool_usage.py",
    )
    output = tmp_path / "planned-subscription-evidence.json"

    monkeypatch.setattr(
        module,
        "load_planned_subscription",
        lambda family_id: {
            "id": family_id,
            "provider_id": "zai_glm_coding",
            "activation_gate": "supported_tool_usage_observed",
            "preferred_supported_tools": ["codex", "gemini"],
            "required_env_contracts": ["ZAI_API_KEY", "ZAI_CODING_API_KEY"],
        },
    )
    monkeypatch.setattr(
        module,
        "load_catalog_provider",
        lambda provider_id: {"id": provider_id, "label": "Z.ai GLM Coding"},
    )
    monkeypatch.setattr(module.shutil, "which", lambda command: f"/tmp/{command}" if command == "codex" else None)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_supported_tool_usage.py",
            "--family-id",
            "glm_coding_plan",
            "--tool-name",
            "codex",
            "--request-surface",
            "codex bounded request",
            "--note",
            "pilot succeeded",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    capture = payload["captures"][0]
    assert capture["status"] == "supported_tool_usage_observed"
    assert capture["tool_name"] == "codex"
    assert capture["required_env_contracts"] == ["ZAI_API_KEY", "ZAI_CODING_API_KEY"]
    assert capture["available_commands"] == ["codex"]


def test_subscription_burn_uses_planned_subscription_activation_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"subscription_burn_planned_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "subscription-burn.py",
    )

    module.STATE_FILE = tmp_path / "subscription-burn-state.json"
    module.PROVIDER_USAGE_EVIDENCE_PATH = tmp_path / "provider-usage-evidence.json"
    module.PLANNED_SUBSCRIPTION_EVIDENCE_PATH = tmp_path / "planned-subscription-evidence.json"
    module.CAPACITY_TELEMETRY_PATH = tmp_path / "capacity-telemetry.json"
    module.PROVIDER_CATALOG = {
        "zai_glm_coding": {
            "id": "zai_glm_coding",
            "label": "Z.ai GLM Coding",
            "subscription_product": "GLM Coding Plan",
            "monthly_cost_usd": None,
            "official_pricing_status": "official-source-present-cost-unverified",
        }
    }
    module.BURN_REGISTRY = {
        "quota_truth_contract": {
            "subscription_high_confidence_within_seconds": 21600,
            "metered_high_confidence_within_seconds": 3600,
            "local_compute_high_confidence_within_seconds": 120,
        },
        "planned_subscriptions": [
            {
                "id": "glm_coding_plan",
                "family_id": "glm_coding_plan",
                "provider_id": "zai_glm_coding",
                "type": "rolling_window_plus_weekly",
                "collector_id": "glm_tooling_probe",
                "activation_gate": "supported_tool_usage_observed",
                "harvest_priority": "bulk_coding_overflow",
                "reserve_floor": {"kind": "percent_of_each_window", "five_hour_window_percent": 10, "weekly_window_percent": 10},
                "preferred_supported_tools": ["codex", "claude", "gemini"],
                "required_env_contracts": ["ZAI_API_KEY", "ZAI_CODING_API_KEY"],
                "next_proof_step": "Run one bounded supported-tool request.",
                "proof_record_command": "python scripts/record_supported_tool_usage.py --family-id glm_coding_plan --tool-name codex",
            }
        ],
        "metered_families": [],
        "local_compute_families": [],
        "subscriptions": [],
    }

    evidence_payload = {
        "version": "2026-04-11.1",
        "updated_at": "2026-04-11T16:00:00Z",
        "captures": [
            {
                "family_id": "glm_coding_plan",
                "provider_id": "zai_glm_coding",
                "status": "tooling_ready",
                "observed_at": "2026-04-11T16:00:00Z",
                "source": "planned-subscription-tooling-probe",
                "request_surface": "local command probe",
                "required_commands": ["codex"],
                "available_commands": ["codex"],
                "required_env_contracts": ["ZAI_API_KEY"],
                "present_env_contracts": [],
                "notes": ["catalog_api_configured=true"],
            }
        ],
    }
    module.PLANNED_SUBSCRIPTION_EVIDENCE_PATH.write_text(json.dumps(evidence_payload), encoding="utf-8")

    snapshot = module.build_quota_truth_snapshot()
    record = next(item for item in snapshot["records"] if item["family_id"] == "glm_coding_plan")
    assert record["evidence_source"] == "planned-subscription-tooling-probe"
    assert record["pricing_status"] == "planned_with_activation_evidence"
    assert record["activation_evidence"]["status"] == "tooling_ready"
    assert record["degraded_reason"] == "tooling_ready"
    assert record["activation_evidence"]["preferred_supported_tools"] == ["codex", "claude", "gemini"]
    assert record["next_proof_step"] == "Run one bounded supported-tool request."
