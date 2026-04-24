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


def test_value_canaries_require_guardrails_and_product_stage_waits_for_operator_stage() -> None:
    module = _load_module(
        f"run_ralph_loop_value_canaries_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    registry = {
        "guardrails": {
            "require_runtime_parity_clean": True,
            "require_validator_and_contract_healer_green": True,
            "require_continuity_health_healthy": True,
        },
        "canaries": [
            {
                "id": "operator-proof-1",
                "title": "Accepted operator proof",
                "stage": "operator_value",
                "value_class": "operator_value",
                "deliverable_kind": "code_patch",
                "beneficiary_surface": "athanor_core",
                "preferred_lane_family": "safe_surface_execution",
                "approved_mutation_class": "auto_read_only",
                "proof_command_or_eval_surface": "scripts/validate_platform_contract.py",
                "acceptance_artifact": "reports/truth-inventory/autonomous-value-proof.json",
                "closure_rule": "Land one bounded fix.",
                "ranking_bonus": 50,
            },
            {
                "id": "product-proof-1",
                "title": "Accepted product proof",
                "stage": "product_value",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "beneficiary_surface": "dashboard",
                "preferred_lane_family": "safe_surface_execution",
                "approved_mutation_class": "auto_read_only",
                "proof_command_or_eval_surface": "projects/dashboard/src/app/page.tsx",
                "acceptance_artifact": "reports/truth-inventory/autonomous-value-proof.json",
                "closure_rule": "Ship one visible dashboard improvement.",
                "task_brief": "Add a visible dashboard proof card.",
                "ranking_bonus": 40,
            },
        ],
    }
    blocker_map = {
        "proof_gate": {
            "checks": [
                {"id": "validator_and_contract_healer", "met": True},
            ]
        }
    }
    runtime_parity = {"drift_class": "clean"}
    supervisor_health = {"health_status": "healthy"}

    pre_stage_rows = module._build_value_canary_items(
        registry,
        blocker_map,
        runtime_parity,
        supervisor_health,
        {"stage_status": {"operator_value": {"met": False}}},
    )

    assert [row["autonomous_value_canary_id"] for row in pre_stage_rows] == ["operator-proof-1"]
    assert pre_stage_rows[0]["deliverable_kind"] == "code_patch"
    assert pre_stage_rows[0]["acceptance_proof_refs"] == ["reports/truth-inventory/autonomous-value-proof.json"]

    post_stage_rows = module._build_value_canary_items(
        registry,
        blocker_map,
        runtime_parity,
        supervisor_health,
        {"stage_status": {"operator_value": {"met": True}}},
    )

    assert [row["autonomous_value_canary_id"] for row in post_stage_rows] == ["product-proof-1"]
    assert post_stage_rows[0]["beneficiary_surface"] == "dashboard"
    assert post_stage_rows[0]["task_brief"] == "Add a visible dashboard proof card."

    blocked_rows = module._build_value_canary_items(
        registry,
        blocker_map,
        {"drift_class": "repo_drift"},
        supervisor_health,
        {"stage_status": {"operator_value": {"met": False}}},
    )

    assert blocked_rows == []
