#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
BLOCKER_EXECUTION_PLAN_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-execution-plan.json"

PROGRAM_SLICE_EXECUTION_ORDER = [
    "control-plane-registry-and-routing",
    "agent-execution-kernel-follow-on",
    "agent-route-contract-follow-on",
    "control-plane-proof-and-ops-follow-on",
]

SUBTRANCHE_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "control-plane-registry-and-routing": [
        {
            "id": "registry-ledgers-and-matrices",
            "title": "Registry Ledgers and Matrices",
            "focus_categories": ["registry/policy"],
            "path_keywords": [
                "docs-lifecycle-registry",
                "economic-dispatch-ledger",
                "lane-selection-matrix",
                "executive-kernel-registry",
            ],
        },
        {
            "id": "routing-policy-and-subscription-lane",
            "title": "Routing Policy and Subscription Lane",
            "focus_categories": ["registry/policy", "agent runtime"],
            "path_keywords": ["routing", "subscription", "lane", "policy"],
        },
        {
            "id": "agent-routing-runtime-surfaces",
            "title": "Agent Routing Runtime Surfaces",
            "focus_categories": ["agent runtime"],
            "path_keywords": ["projects/agents/src/", "backbone.py", "subscriptions", "model_governance"],
        },
        {
            "id": "routing-proof-tests",
            "title": "Routing Proof Tests",
            "focus_categories": ["proof/ops", "routes/contracts"],
            "path_keywords": ["test", "proof", "validate", "contract"],
        },
    ],
    "agent-execution-kernel-follow-on": [
        {
            "id": "operator-queue-state",
            "title": "Operator Queue State",
            "focus_categories": ["agent runtime"],
            "path_keywords": ["operator_work", "operator_state", "tasks.py"],
        },
        {
            "id": "scheduler-and-research-loop",
            "title": "Scheduler and Research Loop",
            "focus_categories": ["agent runtime"],
            "path_keywords": ["scheduler", "research_jobs", "work_pipeline", "test_research_jobs"],
        },
        {
            "id": "self-improvement-and-proving",
            "title": "Self-Improvement and Proving",
            "focus_categories": ["agent runtime", "proof/ops"],
            "path_keywords": ["self_improvement", "proving_ground"],
        },
        {
            "id": "execution-kernel-tests",
            "title": "Execution Kernel Support and Tests",
            "focus_categories": ["proof/ops"],
            "path_keywords": [
                "autonomous_queue",
                "capability_intelligence",
                "repo_paths",
                "test_repo_paths",
            ],
        },
    ],
    "agent-route-contract-follow-on": [
        {
            "id": "route-surface-code",
            "title": "Route Surface Code",
            "focus_categories": ["routes/contracts", "agent runtime"],
            "path_keywords": ["projects/agents/src/athanor_agents/routes/"],
        },
        {
            "id": "route-contract-tests",
            "title": "Route Contract and CLI Tests",
            "focus_categories": ["proof/ops", "routes/contracts"],
            "path_keywords": ["route_contract", "cli_router_contracts"],
        },
    ],
    "control-plane-proof-and-ops-follow-on": [
        {
            "id": "ralph-and-truth-writers",
            "title": "Ralph and Truth Writers",
            "focus_categories": ["proof/ops"],
            "path_keywords": [
                "run_ralph_loop_pass",
                "truth_inventory",
                "write_steady_state_status",
                "write_current_tree_partition",
                "write_value_throughput_scorecard",
                "ralph_loop_contracts",
                "test_truth_inventory_path_overrides",
            ],
        },
        {
            "id": "proof-generators-and-validators",
            "title": "Proof Generators and Validators",
            "focus_categories": ["proof/ops"],
            "path_keywords": [
                "generate_capability_intelligence",
                "capability_intelligence",
                "proof_workspace_contract",
                "sync_github_portfolio_registry",
                "probe_openhands_bounded_worker",
                "validate_platform_contract_monitoring_contracts",
            ],
        },
        {
            "id": "deploy-and-runtime-ops-helpers",
            "title": "Deploy and Runtime Ops Helpers",
            "focus_categories": ["proof/ops"],
            "path_keywords": ["deploy-agents", "cluster_config", "docker-compose"],
        },
    ],
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _family_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    family_id = str(item.get("id") or "")
    if family_id in PROGRAM_SLICE_EXECUTION_ORDER:
        return (PROGRAM_SLICE_EXECUTION_ORDER.index(family_id), family_id)
    return (999, family_id)


def _normalized_family(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "title": _pick_string(item.get("title"), item.get("id")) or "unknown",
        "execution_class": _pick_string(item.get("execution_class")) or "unknown",
        "match_count": int(item.get("match_count") or 0),
        "next_action": _pick_string(item.get("next_action")) or "",
        "decomposition_required": bool(item.get("decomposition_required")),
        "decomposition_reasons": [
            str(reason).strip()
            for reason in item.get("decomposition_reasons", [])
            if isinstance(reason, str) and str(reason).strip()
        ],
        "categories": [
            str(category).strip()
            for category in item.get("categories", [])
            if isinstance(category, str) and str(category).strip()
        ],
        "sample_paths": [
            str(path).strip()
            for path in item.get("sample_paths", [])
            if isinstance(path, str) and str(path).strip()
        ],
    }


def _path_hints(sample_paths: list[str], keywords: list[str]) -> list[str]:
    matched = [
        path
        for path in sample_paths
        if any(keyword.lower() in path.lower() for keyword in keywords)
    ]
    return matched[:12]


def _build_subtranches(family: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = SUBTRANCHE_DEFAULTS.get(str(family.get("id") or ""), [])
    if not defaults:
        return []

    sample_paths = list(family.get("sample_paths") or [])
    subtranches: list[dict[str, Any]] = []
    for index, definition in enumerate(defaults, start=1):
        path_keywords = [
            str(keyword).strip()
            for keyword in definition.get("path_keywords", [])
            if isinstance(keyword, str) and str(keyword).strip()
        ]
        focus_categories = [
            str(category).strip()
            for category in definition.get("focus_categories", [])
            if isinstance(category, str) and str(category).strip()
        ]
        subtranches.append(
            {
                "id": str(definition["id"]),
                "title": str(definition["title"]),
                "sequence": index,
                "focus_categories": focus_categories,
                "path_hints": _path_hints(sample_paths, path_keywords),
                "status": "pending",
            }
        )
    return subtranches


def _select_next_subtranche(subtranches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not subtranches:
        return None
    for subtranche in subtranches:
        if subtranche.get("path_hints"):
            return subtranche
    return subtranches[0]


def build_payload(blocker_map: dict[str, Any]) -> dict[str, Any]:
    remaining = dict(blocker_map.get("remaining") or {})
    raw_families = remaining.get("families") if isinstance(remaining.get("families"), list) else []
    families = [
        _normalized_family(item)
        for item in raw_families
        if isinstance(item, dict) and int(item.get("match_count") or 0) > 0
    ]
    families.sort(key=_family_sort_key)
    next_family = families[0] if families else None

    plan_families: list[dict[str, Any]] = []
    for family in families:
        decomposition_required = bool(family.get("decomposition_required"))
        subtranches = _build_subtranches(family) if decomposition_required else []
        has_live_subtranche = any(item.get("path_hints") for item in subtranches)
        normalized_subtranches = [
            {
                **item,
                "status": "pending" if item.get("path_hints") else ("cleared" if has_live_subtranche else item["status"]),
            }
            for item in subtranches
        ]
        next_subtranche = _select_next_subtranche(normalized_subtranches)
        plan_families.append(
            {
                **family,
                "subtranches": normalized_subtranches,
                "next_subtranche_id": next_subtranche["id"] if next_subtranche else None,
                "next_subtranche_title": next_subtranche["title"] if next_subtranche else None,
            }
        )

    next_target: dict[str, Any]
    if not next_family:
        next_target = dict(
            blocker_map.get("throughput_target")
            or {
                "kind": "none",
                "family_id": None,
                "family_title": None,
                "subtranche_id": None,
                "subtranche_title": None,
                "execution_class": None,
                "approval_gated": False,
                "external_blocked": False,
            }
        )
    else:
        current_plan_family = plan_families[0]
        first_subtranche = _select_next_subtranche(current_plan_family["subtranches"])
        next_target = {
            "kind": "subtranche" if first_subtranche else "family",
            "family_id": current_plan_family["id"],
            "family_title": current_plan_family["title"],
            "subtranche_id": first_subtranche["id"] if first_subtranche else None,
            "subtranche_title": first_subtranche["title"] if first_subtranche else None,
            "execution_class": current_plan_family["execution_class"],
            "approval_gated": False,
            "external_blocked": False,
        }

    return {
        "generated_at": _iso_now(),
        "selection_mode": str(blocker_map.get("objective") or "closure_debt"),
        "family_order": PROGRAM_SLICE_EXECUTION_ORDER,
        "next_family_id": next_family["id"] if next_family else None,
        "next_target": next_target,
        "families": plan_families,
        "source_artifacts": {
            "blocker_map": str(BLOCKER_MAP_PATH),
            "blocker_execution_plan": str(BLOCKER_EXECUTION_PLAN_PATH),
        },
    }


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.pop("generated_at", None)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the canonical blocker execution plan.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when blocker-execution-plan.json is stale.")
    args = parser.parse_args()

    blocker_map = _load_optional_json(BLOCKER_MAP_PATH)
    payload = build_payload(blocker_map)
    existing = _load_optional_json(BLOCKER_EXECUTION_PLAN_PATH)
    if existing and _normalized_payload(existing) == _normalized_payload(payload):
        payload["generated_at"] = str(existing.get("generated_at") or payload["generated_at"])

    rendered = _json_render(payload)
    if args.check:
        current = BLOCKER_EXECUTION_PLAN_PATH.read_text(encoding="utf-8") if BLOCKER_EXECUTION_PLAN_PATH.exists() else ""
        if current != rendered:
            print(f"{BLOCKER_EXECUTION_PLAN_PATH} is stale")
            return 1
        return 0

    BLOCKER_EXECUTION_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = BLOCKER_EXECUTION_PLAN_PATH.read_text(encoding="utf-8") if BLOCKER_EXECUTION_PLAN_PATH.exists() else ""
    if current != rendered:
        BLOCKER_EXECUTION_PLAN_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(BLOCKER_EXECUTION_PLAN_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
