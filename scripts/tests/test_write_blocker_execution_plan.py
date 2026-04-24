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


def test_build_payload_expands_current_family_into_bounded_subtranches() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": [
                "control-plane-registry-and-routing",
                "agent-execution-kernel-follow-on",
            ],
            "families": [
                {
                    "id": "control-plane-registry-and-routing",
                    "title": "Control-Plane Registry and Routing",
                    "execution_class": "program_slice",
                    "match_count": 10,
                    "next_action": "Bound registry and routing residue.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["spans_more_than_two_surface_categories"],
                    "categories": ["registry/policy", "agent runtime", "proof/ops"],
                    "sample_paths": [
                        "config/automation-backbone/executive-kernel-registry.json",
                        "projects/agents/src/athanor_agents/backbone.py",
                        "projects/agents/tests/test_subscription_policy.py",
                    ],
                },
                {
                    "id": "agent-execution-kernel-follow-on",
                    "title": "Agent Execution Kernel Follow-on",
                    "execution_class": "program_slice",
                    "match_count": 18,
                    "next_action": "Bound the execution kernel tranche.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["match_count_above_12"],
                    "categories": ["agent runtime", "proof/ops"],
                    "sample_paths": [
                        "projects/agents/src/athanor_agents/operator_work.py",
                        "projects/agents/src/athanor_agents/scheduler.py",
                    ],
                },
            ],
        },
        "next_tranche": {
            "id": "control-plane-registry-and-routing",
            "title": "Control-Plane Registry and Routing",
            "execution_class": "program_slice",
            "match_count": 10,
            "next_action": "Bound registry and routing residue.",
            "decomposition_required": True,
            "decomposition_reasons": ["spans_more_than_two_surface_categories"],
            "categories": ["registry/policy", "agent runtime", "proof/ops"],
        },
    }

    payload = module.build_payload(blocker_map)

    assert payload["selection_mode"] == "closure_debt"
    assert payload["next_target"] == {
        "kind": "subtranche",
        "family_id": "control-plane-registry-and-routing",
        "family_title": "Control-Plane Registry and Routing",
        "subtranche_id": "registry-ledgers-and-matrices",
        "subtranche_title": "Registry Ledgers and Matrices",
        "execution_class": "program_slice",
        "approval_gated": False,
        "external_blocked": False,
    }
    current_family = payload["families"][0]
    assert current_family["id"] == "control-plane-registry-and-routing"
    assert [item["id"] for item in current_family["subtranches"]] == [
        "registry-ledgers-and-matrices",
        "routing-policy-and-subscription-lane",
        "agent-routing-runtime-surfaces",
        "routing-proof-tests",
    ]
    assert current_family["next_subtranche_id"] == "registry-ledgers-and-matrices"


def test_build_payload_keeps_direct_family_when_decomposition_is_not_required() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": ["control-plane-registry-and-routing"],
            "families": [
                {
                    "id": "control-plane-registry-and-routing",
                    "title": "Control-Plane Registry and Routing",
                    "execution_class": "program_slice",
                    "match_count": 4,
                    "next_action": "Land the remaining routing residue.",
                    "decomposition_required": False,
                    "decomposition_reasons": [],
                    "categories": ["registry/policy", "agent runtime"],
                    "sample_paths": ["config/automation-backbone/executive-kernel-registry.json"],
                }
            ],
        },
        "next_tranche": {
            "id": "control-plane-registry-and-routing",
            "title": "Control-Plane Registry and Routing",
            "execution_class": "program_slice",
            "match_count": 4,
            "next_action": "Land the remaining routing residue.",
            "decomposition_required": False,
            "decomposition_reasons": [],
            "categories": ["registry/policy", "agent runtime"],
        },
    }

    payload = module.build_payload(blocker_map)

    assert payload["next_target"] == {
        "kind": "family",
        "family_id": "control-plane-registry-and-routing",
        "family_title": "Control-Plane Registry and Routing",
        "subtranche_id": None,
        "subtranche_title": None,
        "execution_class": "program_slice",
        "approval_gated": False,
        "external_blocked": False,
    }
    assert payload["families"][0]["subtranches"] == []


def test_build_payload_advances_to_next_subtranche_when_first_one_is_cleared() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": ["control-plane-registry-and-routing"],
            "families": [
                {
                    "id": "control-plane-registry-and-routing",
                    "title": "Control-Plane Registry and Routing",
                    "execution_class": "program_slice",
                    "match_count": 6,
                    "next_action": "Land the remaining routing residue.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["spans_more_than_two_surface_categories"],
                    "categories": ["registry/policy", "agent runtime", "proof/ops"],
                    "sample_paths": [
                        "projects/agents/config/subscription-routing-policy.yaml",
                        "projects/agents/src/athanor_agents/backbone.py",
                        "projects/agents/tests/test_subscription_policy.py",
                    ],
                }
            ],
        },
        "next_tranche": {
            "id": "control-plane-registry-and-routing",
            "title": "Control-Plane Registry and Routing",
            "execution_class": "program_slice",
            "match_count": 6,
            "next_action": "Land the remaining routing residue.",
            "decomposition_required": True,
            "decomposition_reasons": ["spans_more_than_two_surface_categories"],
            "categories": ["registry/policy", "agent runtime", "proof/ops"],
        },
    }

    payload = module.build_payload(blocker_map)

    assert payload["next_target"] == {
        "kind": "subtranche",
        "family_id": "control-plane-registry-and-routing",
        "family_title": "Control-Plane Registry and Routing",
        "subtranche_id": "routing-policy-and-subscription-lane",
        "subtranche_title": "Routing Policy and Subscription Lane",
        "execution_class": "program_slice",
        "approval_gated": False,
        "external_blocked": False,
    }
    current_family = payload["families"][0]
    assert current_family["subtranches"][0]["id"] == "registry-ledgers-and-matrices"
    assert current_family["subtranches"][0]["path_hints"] == []
    assert current_family["subtranches"][0]["status"] == "cleared"
    assert current_family["next_subtranche_id"] == "routing-policy-and-subscription-lane"


def test_build_payload_keeps_execution_kernel_support_paths_in_final_subtranche() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": ["agent-execution-kernel-follow-on"],
            "families": [
                {
                    "id": "agent-execution-kernel-follow-on",
                    "title": "Agent Execution Kernel Follow-on",
                    "execution_class": "program_slice",
                    "match_count": 4,
                    "next_action": "Land the remaining execution-kernel residue.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["match_count_above_12"],
                    "categories": ["agent runtime", "proof/ops"],
                    "sample_paths": [
                        "projects/agents/src/athanor_agents/autonomous_queue.py",
                        "projects/agents/src/athanor_agents/capability_intelligence.py",
                        "projects/agents/src/athanor_agents/repo_paths.py",
                        "projects/agents/tests/test_repo_paths.py",
                    ],
                }
            ],
        },
        "next_tranche": {
            "id": "agent-execution-kernel-follow-on",
            "title": "Agent Execution Kernel Follow-on",
            "execution_class": "program_slice",
            "match_count": 4,
            "next_action": "Land the remaining execution-kernel residue.",
            "decomposition_required": True,
            "decomposition_reasons": ["match_count_above_12"],
            "categories": ["agent runtime", "proof/ops"],
        },
    }

    payload = module.build_payload(blocker_map)


def test_build_payload_ignores_zero_match_families_and_falls_back_to_throughput_target() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "result_backed_throughput",
        "remaining": {
            "family_ids": ["reference-and-archive-prune"],
            "families": [
                {
                    "id": "reference-and-archive-prune",
                    "title": "Reference and Archive Prune",
                    "execution_class": "cash_now",
                    "match_count": 0,
                    "next_action": "",
                    "decomposition_required": False,
                    "decomposition_reasons": [],
                    "categories": ["reference/archive"],
                    "sample_paths": [],
                }
            ],
        },
        "throughput_target": {
            "kind": "queue_backed_throughput",
            "family_id": "builder",
            "family_title": "Builder",
            "subtranche_id": "unscoped",
            "subtranche_title": None,
            "execution_class": "queue_backed_throughput",
            "approval_gated": False,
            "external_blocked": False,
        },
    }

    payload = module.build_payload(blocker_map)

    assert payload["next_target"] == {
        "kind": "queue_backed_throughput",
        "family_id": "builder",
        "family_title": "Builder",
        "subtranche_id": "unscoped",
        "subtranche_title": None,
        "execution_class": "queue_backed_throughput",
        "approval_gated": False,
        "external_blocked": False,
    }
    assert payload["families"] == []


def test_build_payload_keeps_cli_router_tests_in_route_contract_subtranche() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": ["agent-route-contract-follow-on"],
            "families": [
                {
                    "id": "agent-route-contract-follow-on",
                    "title": "Agent Route Contract Follow-on",
                    "execution_class": "program_slice",
                    "match_count": 3,
                    "next_action": "Land the remaining route residue.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["match_count_above_12"],
                    "categories": ["routes/contracts"],
                    "sample_paths": [
                        "projects/agents/src/athanor_agents/routes/operator_work.py",
                        "projects/agents/tests/test_operator_work_route_contract.py",
                        "scripts/tests/test_cli_router_contracts.py",
                    ],
                }
            ],
        },
        "next_tranche": {
            "id": "agent-route-contract-follow-on",
            "title": "Agent Route Contract Follow-on",
            "execution_class": "program_slice",
            "match_count": 3,
            "next_action": "Land the remaining route residue.",
            "decomposition_required": True,
            "decomposition_reasons": ["match_count_above_12"],
            "categories": ["routes/contracts"],
        },
    }

    payload = module.build_payload(blocker_map)

    current_family = payload["families"][0]
    surface_subtranche = current_family["subtranches"][0]
    contract_subtranche = current_family["subtranches"][1]
    assert surface_subtranche["id"] == "route-surface-code"
    assert surface_subtranche["path_hints"] == ["projects/agents/src/athanor_agents/routes/operator_work.py"]
    assert contract_subtranche["id"] == "route-contract-tests"
    assert contract_subtranche["path_hints"] == [
        "projects/agents/tests/test_operator_work_route_contract.py",
        "scripts/tests/test_cli_router_contracts.py",
    ]


def test_build_payload_covers_proof_and_ops_paths_across_existing_subtranches() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "closure_debt",
        "remaining": {
            "family_ids": ["control-plane-proof-and-ops-follow-on"],
            "families": [
                {
                    "id": "control-plane-proof-and-ops-follow-on",
                    "title": "Control-Plane Proof and Ops Follow-on",
                    "execution_class": "program_slice",
                    "match_count": 6,
                    "next_action": "Land the remaining proof and ops residue.",
                    "decomposition_required": True,
                    "decomposition_reasons": ["match_count_above_12"],
                    "categories": ["proof/ops"],
                    "sample_paths": [
                        "projects/agents/docker-compose.yml",
                        "scripts/.cluster_config.unix.sh",
                        "scripts/run_ralph_loop_pass.py",
                        "scripts/sync_github_portfolio_registry.py",
                        "scripts/write_current_tree_partition.py",
                        "scripts/tests/test_ralph_loop_contracts.py",
                    ],
                }
            ],
        },
        "next_tranche": {
            "id": "control-plane-proof-and-ops-follow-on",
            "title": "Control-Plane Proof and Ops Follow-on",
            "execution_class": "program_slice",
            "match_count": 6,
            "next_action": "Land the remaining proof and ops residue.",
            "decomposition_required": True,
            "decomposition_reasons": ["match_count_above_12"],
            "categories": ["proof/ops"],
        },
    }

    payload = module.build_payload(blocker_map)

    current_family = payload["families"][0]
    assert current_family["subtranches"][0]["path_hints"] == [
        "scripts/run_ralph_loop_pass.py",
        "scripts/write_current_tree_partition.py",
        "scripts/tests/test_ralph_loop_contracts.py",
    ]
    assert current_family["subtranches"][1]["path_hints"] == [
        "scripts/sync_github_portfolio_registry.py",
    ]
    assert current_family["subtranches"][2]["path_hints"] == [
        "projects/agents/docker-compose.yml",
        "scripts/.cluster_config.unix.sh",
    ]


def test_build_payload_switches_to_queue_backed_throughput_target_when_family_debt_is_clear() -> None:
    module = _load_module(
        f"write_blocker_execution_plan_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_blocker_execution_plan.py",
    )

    blocker_map = {
        "objective": "result_backed_throughput",
        "remaining": {
            "family_ids": [],
            "families": [],
        },
        "throughput_target": {
            "kind": "queue_backed_throughput",
            "family_id": "builder",
            "family_title": "Builder",
            "subtranche_id": "unscoped",
            "subtranche_title": None,
            "execution_class": "queue_backed_throughput",
            "approval_gated": False,
            "external_blocked": False,
            "source": "value_throughput",
            "open_item_count": 15,
            "queue_backed_jobs": 2,
            "detail": "Builder",
        },
    }

    payload = module.build_payload(blocker_map)

    assert payload["selection_mode"] == "result_backed_throughput"
    assert payload["next_family_id"] is None
    assert payload["next_target"]["kind"] == "queue_backed_throughput"
    assert payload["next_target"]["family_id"] == "builder"
    assert payload["next_target"]["execution_class"] == "queue_backed_throughput"
