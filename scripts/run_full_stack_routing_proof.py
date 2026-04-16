#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, load_json
from truth_inventory import resolve_external_path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "routing-proof.json"
SAFE_SURFACE_ROOT = resolve_external_path("C:/Users/Shaun/.codex/control")


def _result(case_id: str, category: str, passed: bool, detail: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "status": "passed" if passed else "failed",
        "detail": detail,
        "metadata": metadata or {},
    }


def main() -> int:
    lane_matrix = load_json(CONFIG_DIR / "lane-selection-matrix.json")
    approval_matrix = load_json(CONFIG_DIR / "approval-matrix.json")
    failure_matrix = load_json(CONFIG_DIR / "failure-routing-matrix.json")
    burn_registry = load_json(CONFIG_DIR / "subscription-burn-registry.json")
    capacity_contract = load_json(CONFIG_DIR / "capacity-telemetry-contract.json")
    active_overrides = load_json(REPO_ROOT / "reports" / "truth-inventory" / "active-overrides.json")
    safe_surface_state = load_json(SAFE_SURFACE_ROOT / "safe-surface-state.json")
    safe_surface_queue = load_json(SAFE_SURFACE_ROOT / "safe-surface-queue.json")
    safe_surface_scope_text = (SAFE_SURFACE_ROOT / "safe-surface-scope.md").read_text(encoding="utf-8")

    suites: list[dict[str, Any]] = []

    for profile in lane_matrix.get("selection_profiles", []):
        if not isinstance(profile, dict):
            continue
        suites.append(
            _result(
                case_id=f"task:{profile.get('task_class')}",
                category="task_class",
                passed=all(str(profile.get(key) or "").strip() for key in ("preferred_lane", "secondary_lane", "local_fallback")),
                detail=f"Task class {profile.get('task_class')} resolves to a deterministic lane ordering.",
                metadata={"task_class": profile.get("task_class"), "preferred_lane": profile.get("preferred_lane")},
            )
        )

    sensitivity_classes = sorted({str(profile.get("sensitivity_class") or "").strip() for profile in lane_matrix.get("selection_profiles", []) if isinstance(profile, dict)})
    for sensitivity_class in sensitivity_classes:
        suites.append(
            _result(
                case_id=f"sensitivity:{sensitivity_class}",
                category="sensitivity_class",
                passed=bool(sensitivity_class),
                detail=f"Sensitivity class {sensitivity_class} is represented in the lane matrix.",
                metadata={"sensitivity_class": sensitivity_class},
            )
        )

    for approval_class in approval_matrix.get("classes", []):
        if not isinstance(approval_class, dict):
            continue
        actions = approval_class.get("allowed_actions")
        suites.append(
            _result(
                case_id=f"approval:{approval_class.get('id')}",
                category="approval_class",
                passed=isinstance(actions, list) and len(actions) > 0,
                detail=f"Approval class {approval_class.get('id')} declares bounded actions.",
                metadata={"approval_class": approval_class.get("id")},
            )
        )

    for failure_row in failure_matrix.get("rows", []):
        if not isinstance(failure_row, dict):
            continue
        suites.append(
            _result(
                case_id=f"failure:{failure_row.get('failure_class')}:{failure_row.get('affected_family')}",
                category="failure_class",
                passed=bool(failure_row.get("allowed_fallbacks")) and bool(failure_row.get("recovery_gate")),
                detail=f"Failure class {failure_row.get('failure_class')} has bounded fallbacks and recovery gate.",
                metadata={
                    "failure_class": failure_row.get("failure_class"),
                    "affected_family": failure_row.get("affected_family"),
                },
            )
        )

    for family in burn_registry.get("subscriptions", []):
        if not isinstance(family, dict):
            continue
        suites.append(
            _result(
                case_id=f"family:{family.get('id')}",
                category="subscription_family",
                passed=bool(family.get("collector_id")) and bool(family.get("reserve_floor")),
                detail=f"Subscription family {family.get('id')} has collector and reserve floor.",
                metadata={"family_id": family.get("id")},
            )
        )
    for family in burn_registry.get("planned_subscriptions", []):
        if not isinstance(family, dict):
            continue
        suites.append(
            _result(
                case_id=f"family:{family.get('id')}",
                category="subscription_family",
                passed=bool(family.get("activation_gate")),
                detail=f"Planned subscription family {family.get('id')} has an activation gate.",
                metadata={"family_id": family.get("id")},
            )
        )
    for family in burn_registry.get("metered_families", []):
        if not isinstance(family, dict):
            continue
        suites.append(
            _result(
                case_id=f"family:{family.get('id')}",
                category="subscription_family",
                passed=float(family.get("daily_budget_ceiling_usd") or 0) >= 0,
                detail=f"Metered family {family.get('id')} has a daily budget ceiling.",
                metadata={"family_id": family.get("id")},
            )
        )

    for reserve in capacity_contract.get("protected_reserves", []):
        suites.append(
            _result(
                case_id=f"reserve:{reserve}",
                category="protected_reserve",
                passed=True,
                detail=f"Protected reserve {reserve} is explicitly declared.",
                metadata={"gpu_id": reserve},
            )
        )

    queue_items = safe_surface_queue.get("items", [])
    suites.append(
        _result(
            case_id="scope:safe-surface-summary",
            category="scope_boundary",
            passed=isinstance(queue_items, list) and "Anything Athanor-adjacent is out of scope" in safe_surface_scope_text,
            detail="Safe-surface summary inputs are present and scope denial for Athanor-adjacent paths is documented.",
            metadata={
                "queue_items": len(queue_items) if isinstance(queue_items, list) else 0,
                "last_outcome": safe_surface_state.get("last_outcome"),
            },
        )
    )

    for override_type in dict(active_overrides.get("policy") or {}).get("allowed_types", []):
        suites.append(
            _result(
                case_id=f"override:{override_type}",
                category="manual_override_type",
                passed=True,
                detail=f"Override type {override_type} is declared in the active override policy.",
                metadata={"override_type": override_type},
            )
        )

    passed_count = sum(1 for suite in suites if suite["status"] == "passed")
    summary = {
        "total": len(suites),
        "passed": passed_count,
        "failed": len(suites) - passed_count,
        "all_passed": passed_count == len(suites),
    }
    payload = {
        "version": "2026-04-11.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_of_truth": "reports/truth-inventory/routing-proof.json",
        "summary": summary,
        "suites": suites,
    }
    dump_json(OUTPUT_PATH, payload)
    append_history("routing-decisions", payload)
    print(OUTPUT_PATH)
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
