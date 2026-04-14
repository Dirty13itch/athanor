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


def test_provider_gate_detail_counts_only_active_api_auth_failures() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    provider_catalog = {
        "providers": [
            {
                "id": "openai_api",
                "label": "OpenAI API",
                "category": "api",
                "state_classes": ["active-api"],
                "observed_runtime": {"routing_policy_enabled": True, "active_burn_observed": False},
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "present_key_invalid"},
            },
            {
                "id": "dashscope_qwen_api",
                "label": "DashScope Qwen API",
                "category": "api",
                "state_classes": ["active-api"],
                "observed_runtime": {"routing_policy_enabled": True, "active_burn_observed": False},
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "missing_required_env"},
            },
            {
                "id": "moonshot_api",
                "label": "Moonshot API",
                "category": "api",
                "state_classes": ["active-api"],
                "observed_runtime": {"routing_policy_enabled": False, "active_burn_observed": False},
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "direct_env_gap_not_currently_blocking"},
            },
            {
                "id": "moonshot_kimi",
                "label": "Kimi CLI",
                "category": "subscription",
                "state_classes": ["active-subscription"],
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "present_key_invalid"},
            },
        ]
    }

    detail = module._provider_gate_detail(provider_catalog)

    assert detail["blocking_provider_count"] == 2
    assert detail["blocking_provider_ids"] == ["openai_api", "dashscope_qwen_api"]
    assert detail["excluded_provider_ids"] == ["moonshot_api"]
    assert detail["classification_counts"] == {
        "present_key_invalid": 1,
        "missing_required_env": 1,
    }


def test_provider_gate_detail_excludes_optional_non_routed_api_lanes() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    provider_catalog = {
        "providers": [
            {
                "id": "openai_api",
                "label": "OpenAI API",
                "category": "api",
                "state_classes": ["active-api", "configured-unused"],
                "provider_gate_posture": "optional_elasticity_demoted",
                "observed_runtime": {"routing_policy_enabled": False, "active_burn_observed": False},
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "present_key_invalid"},
            },
            {
                "id": "zai_api",
                "label": "Z.ai API",
                "category": "api",
                "state_classes": ["active-api", "configured-unused"],
                "provider_gate_posture": "turnover_critical_overflow",
                "observed_runtime": {"routing_policy_enabled": False, "active_burn_observed": False},
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "missing_required_env"},
            },
        ],
        "routing_families": [
            {
                "id": "glm_family",
                "primary_provider_id": "zai_glm_coding",
                "overflow_provider_id": "zai_api",
            }
        ],
    }

    detail = module._provider_gate_detail(provider_catalog)

    assert detail["blocking_provider_count"] == 1
    assert detail["blocking_provider_ids"] == ["zai_api"]
    assert detail["excluded_provider_ids"] == ["openai_api"]
    assert detail["excluded_provider_postures"] == {
        "openai_api": "optional_elasticity_demoted",
    }
    assert detail["classification_counts"] == {
        "missing_required_env": 1,
    }


def test_provider_gate_item_carries_blocking_provider_ids() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    completion_program = {
        "reconciliation_end_state": {
            "project_exit_gates": [
                {
                    "id": "provider_gate",
                    "status": "external_dependency_blocked",
                }
            ]
        }
    }
    provider_gate_detail = {
        "blocking_provider_count": 2,
        "blocking_provider_ids": ["openai_api", "dashscope_qwen_api"],
        "excluded_provider_ids": ["moonshot_api"],
    }

    rows = module._build_provider_gate_item(completion_program, provider_gate_detail)

    assert len(rows) == 1
    assert rows[0]["id"] == "gate:provider_gate"
    assert rows[0]["task_id"] == "gate:provider_gate"
    assert rows[0]["title"] == "Repair or explicitly demote 2 active provider lanes"
    assert rows[0]["blocking_provider_ids"] == ["openai_api", "dashscope_qwen_api"]
    assert rows[0]["excluded_provider_ids"] == ["moonshot_api"]
    assert rows[0]["blocking_reason"] == "external_dependency_blocked:openai_api,dashscope_qwen_api"


def test_sync_provider_gate_registry_state_clears_gate_and_workstream_when_no_blockers() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    completion_program = {
        "reconciliation_end_state": {
            "project_exit_gates": [
                {
                    "id": "provider_gate",
                    "status": "external_dependency_blocked",
                    "blocker_type": "external_dependency",
                }
            ]
        },
        "workstreams": [
            {
                "id": "provider-and-secret-remediation",
                "status": "blocked",
                "execution_state": "external_dependency_blocked",
                "blocker_type": "external_dependency",
            }
        ],
    }

    module._sync_provider_gate_registry_state(
        completion_program,
        {
            "blocking_provider_count": 0,
            "blocking_provider_ids": [],
            "excluded_provider_ids": ["openai_api"],
            "classification_counts": {},
        },
    )

    provider_gate = completion_program["reconciliation_end_state"]["project_exit_gates"][0]
    provider_workstream = completion_program["workstreams"][0]

    assert provider_gate["status"] == "completed"
    assert provider_gate["blocker_type"] == "none"
    assert provider_gate["blocking_provider_count"] == 0
    assert provider_workstream["status"] == "continuous"
    assert provider_workstream["execution_state"] == "steady_state_monitoring"
    assert provider_workstream["blocker_type"] == "none"


def test_provider_gate_item_skips_empty_blocker_sets_even_if_registry_lags() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    completion_program = {
        "reconciliation_end_state": {
            "project_exit_gates": [
                {
                    "id": "provider_gate",
                    "status": "external_dependency_blocked",
                }
            ]
        }
    }

    rows = module._build_provider_gate_item(
        completion_program,
        {
            "blocking_provider_count": 0,
            "blocking_provider_ids": [],
            "excluded_provider_ids": ["openai_api"],
        },
    )

    assert rows == []


def test_work_economy_detail_marks_compounding_ready_when_burn_classes_have_eligible_lanes() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    provider_catalog = {
        "providers": [
            {
                "id": "athanor_local",
                "label": "Athanor Local",
                "category": "local",
            },
            {
                "id": "openai_codex",
                "label": "Codex CLI",
                "category": "subscription",
            },
            {
                "id": "deepseek_api",
                "label": "DeepSeek API",
                "category": "api",
                "evidence": {"provider_specific_usage": {"status": "observed"}},
            },
            {
                "id": "openai_api",
                "label": "OpenAI API",
                "category": "api",
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "present_key_invalid"},
            },
        ]
    }
    routing_policy = {
        "providers": {
            "athanor_local": {"enabled": True, "routing_posture": "ordinary_auto"},
            "openai_codex": {"enabled": True, "routing_posture": "ordinary_auto"},
        }
    }
    burn_registry = {
        "burn_classes": [
            {"id": "local_bulk_sovereign", "routing_chain": ["athanor_local"]},
            {"id": "cheap_bulk_cloud", "routing_chain": ["deepseek_api", "openai_codex"]},
            {"id": "premium_async", "routing_chain": ["openai_codex"]},
        ]
    }
    provider_gate_detail = {
        "blocking_provider_count": 1,
        "blocking_provider_ids": ["openai_api"],
    }

    detail = module._work_economy_detail(
        provider_catalog,
        routing_policy,
        burn_registry,
        provider_gate_detail,
        {
            "records": [
                {
                    "family_id": "athanor_local_compute",
                    "remaining_units": 6,
                    "capacity_breakdown": {
                        "scheduler_slot_count": 2,
                        "harvestable_scheduler_slot_count": 1,
                        "scheduler_queue_depth": 0,
                        "harvestable_by_zone": {"F": 1},
                        "harvestable_by_slot": {"F:TP4": 1},
                        "scheduler_slot_samples": [
                            {
                                "scheduler_slot_id": "F:TP4",
                                "slot_target_id": "foundry-bulk-pool",
                                "harvestable_gpu_count": 1,
                            }
                        ],
                    },
                }
            ]
        },
    )

    assert detail["status"] == "ready"
    assert detail["ready_for_live_compounding"] is True
    assert detail["provider_elasticity_limited"] is True
    assert detail["blocked_burn_class_count"] == 0
    assert detail["selected_provider_ids"] == ["athanor_local", "deepseek_api", "openai_codex"]
    assert detail["slot_aware_ready_for_harvest"] is True
    assert detail["local_compute_capacity"]["harvestable_scheduler_slot_count"] == 1
    assert detail["local_compute_capacity"]["present"] is True
    assert detail["local_compute_capacity"]["remaining_units"] == 6
    assert detail["local_compute_capacity"]["scheduler_slot_count"] == 2
    assert detail["local_compute_capacity"]["scheduler_queue_depth"] == 0
    assert detail["local_compute_capacity"]["harvestable_by_zone"] == {"F": 1}
    assert detail["local_compute_capacity"]["open_harvest_slot_target_ids"] == ["foundry-bulk-pool"]
    assert detail["capacity_harvest_summary"]["admission_state"] == "open_harvest_window"
    assert detail["capacity_harvest_summary"]["ready_for_harvest_now"] is True
    assert detail["capacity_harvest_summary"]["harvestable_zone_ids"] == ["F"]
    assert detail["capacity_harvest_summary"]["protected_reserve_slot_count"] == 0


def test_burn_class_autonomous_items_materialize_ready_and_blocked_burn_lanes() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    burn_registry = {
        "burn_classes": [
            {
                "id": "local_bulk_sovereign",
                "approved_task_families": ["repo_audit"],
                "reserve_rule": "protect_interactive_reserve_then_harvest_idle_slots",
                "max_concurrency": 6,
            },
            {
                "id": "cheap_bulk_cloud",
                "approved_task_families": ["cheap_bulk_transform"],
                "reserve_rule": "spend_cheapest_eligible_cloud_lane_first",
                "max_concurrency": 8,
            },
        ]
    }
    work_economy_detail = {
        "records": [
            {
                "burn_class_id": "local_bulk_sovereign",
                "status": "ready",
                "selected_provider_id": "athanor_local",
                "selected_provider_label": "Athanor Local",
            },
            {
                "burn_class_id": "cheap_bulk_cloud",
                "status": "blocked",
                "blocking_reason": "no_eligible_provider",
            },
        ],
        "local_compute_capacity": {
            "present": True,
            "harvestable_scheduler_slot_count": 2,
            "scheduler_slot_count": 5,
        },
    }

    rows = module._build_burn_class_autonomous_items(burn_registry, work_economy_detail)
    by_id = {row["burn_class_id"]: row for row in rows}

    assert by_id["local_bulk_sovereign"]["dispatchable"] is True
    assert by_id["local_bulk_sovereign"]["approved_mutation_class"] == "auto_harvest"
    assert by_id["local_bulk_sovereign"]["selected_provider_id"] == "athanor_local"
    assert by_id["local_bulk_sovereign"]["capacity_signal"]["harvestable_scheduler_slot_count"] == 2
    assert by_id["cheap_bulk_cloud"]["dispatchable"] is False
    assert by_id["cheap_bulk_cloud"]["approved_mutation_class"] == "approval_required"
    assert by_id["cheap_bulk_cloud"]["blocking_reason"] == "no_eligible_provider"


def test_ranked_autonomous_queue_includes_burn_class_items_beneath_primary_workstreams() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    workstream_rows = [
        {
            "workstream": {
                "id": "dispatch-and-work-economy-closure",
                "title": "Dispatch and Work-Economy Closure",
                "priority": "high",
                "status": "continuous",
                "execution_state": "ready_for_execution",
                "blocker_type": "none",
                "approval_required": False,
                "next_action_family": "dispatch_truth_and_queue_replenishment",
                "evidence_artifacts": ["reports/ralph-loop/latest.json"],
            },
            "evidence_state": {"state": "fresh"},
        }
    ]
    burn_registry = {
        "burn_classes": [
            {
                "id": "local_bulk_sovereign",
                "approved_task_families": ["repo_audit"],
                "reserve_rule": "protect_interactive_reserve_then_harvest_idle_slots",
                "max_concurrency": 6,
            }
        ]
    }
    work_economy_detail = {
        "records": [
            {
                "burn_class_id": "local_bulk_sovereign",
                "status": "ready",
                "selected_provider_id": "athanor_local",
                "selected_provider_label": "Athanor Local",
            }
        ],
        "local_compute_capacity": {
            "present": True,
            "sample_posture": "scheduler_projection_backed",
            "harvestable_scheduler_slot_count": 2,
            "scheduler_slot_count": 5,
            "scheduler_queue_depth": 0,
            "harvestable_by_zone": {"F": 1},
        },
    }
    quota_truth = {
        "records": [
            {
                "family_id": "athanor_local_compute",
                "remaining_units": 6,
                "capacity_breakdown": {
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 5,
                    "harvestable_scheduler_slot_count": 2,
                    "scheduler_queue_depth": 0,
                    "harvestable_by_zone": {"F": 1},
                },
            }
        ]
    }

    rows = module._build_ranked_autonomous_queue(
        queue={"items": []},
        workstream_rows=workstream_rows,
        completion_program={},
        burn_registry=burn_registry,
        work_economy_detail=work_economy_detail,
        provider_gate_detail={"blocking_provider_count": 0},
        quota_truth=quota_truth,
        capacity_telemetry=None,
    )

    assert rows[0]["task_id"] == "workstream:dispatch-and-work-economy-closure"
    assert any(row["task_id"] == "burn_class:local_bulk_sovereign" for row in rows)


def test_dispatch_authority_carries_work_economy_state_alongside_provider_gate() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    completion_program = {
        "reconciliation_end_state": {
            "project_exit_gates": [
                {
                    "id": "provider_gate",
                    "status": "external_dependency_blocked",
                }
            ]
        }
    }
    burn_registry = {
        "shadow_rollout": {"phase": 1, "phase_label": "governed_dispatch_shadow"},
        "dispatch_policy": {
            "ranked_dispatch_enabled": True,
            "approved_mutation_classes": ["auto_read_only"],
            "approved_work_classes": ["repo_safe_implementation"],
        },
        "burn_classes": [
            {"id": "local_bulk_sovereign", "routing_chain": ["athanor_local"]},
        ],
    }
    routing_policy = {
        "providers": {
            "athanor_local": {"enabled": True, "routing_posture": "ordinary_auto"},
        }
    }
    provider_catalog = {
        "providers": [
            {"id": "athanor_local", "label": "Athanor Local", "category": "local"},
            {
                "id": "openai_api",
                "label": "OpenAI API",
                "category": "api",
                "state_classes": ["active-api"],
                "evidence": {"provider_specific_usage": {"status": "auth_failed"}},
                "vault_remediation": {"classification": "present_key_invalid"},
            },
        ]
    }
    provider_gate_detail = {
        "blocking_provider_count": 1,
        "blocking_provider_ids": ["openai_api"],
    }
    safe_surface_summary = {"dispatchable_queue_count": 0}
    autonomous_queue_summary = {
        "queue_count": 1,
        "dispatchable_queue_count": 1,
        "top_dispatchable_task_id": "workstream:monitoring-and-observability-truth",
        "top_dispatchable_title": "Monitoring and Observability Truth",
    }

    authority = module._build_dispatch_authority(
        completion_program=completion_program,
        burn_registry=burn_registry,
        routing_policy=routing_policy,
        provider_gate_detail=provider_gate_detail,
        safe_surface_summary=safe_surface_summary,
        autonomous_queue_summary=autonomous_queue_summary,
        provider_catalog=provider_catalog,
        quota_truth={
            "records": [
                {
                    "family_id": "athanor_local_compute",
                    "remaining_units": 6,
                    "capacity_breakdown": {
                        "scheduler_slot_count": 2,
                        "harvestable_scheduler_slot_count": 1,
                        "scheduler_queue_depth": 0,
                        "harvestable_by_zone": {"F": 1},
                        "harvestable_by_slot": {"F:TP4": 1},
                        "scheduler_slot_samples": [
                            {
                                "scheduler_slot_id": "F:TP4",
                                "slot_target_id": "foundry-bulk-pool",
                                "harvestable_gpu_count": 1,
                            }
                        ],
                    },
                }
            ]
        },
    )

    assert authority["governed_dispatch_ready"] is True
    assert authority["provider_gate_state"] == "external_dependency_blocked"
    assert authority["work_economy_status"] == "ready"
    assert authority["work_economy_ready_now"] is True
    assert authority["advisory_blockers"] == ["provider_elasticity_limited:1"]
    assert authority["work_economy_detail"]["local_compute_capacity"]["harvestable_scheduler_slot_count"] == 1
    assert authority["capacity_harvest_summary"]["admission_state"] == "open_harvest_window"
    assert authority["capacity_harvest_summary"]["harvestable_scheduler_slot_count"] == 1
    assert authority["capacity_harvest_summary"]["ready_for_harvest_now"] is True


def test_local_compute_capacity_summary_reports_reserve_only_and_missing_projection_states() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    reserve_only = module._local_compute_capacity_detail(
        {
            "records": [
                {
                    "family_id": "athanor_local_compute",
                    "remaining_units": 5,
                    "capacity_breakdown": {
                        "sample_posture": "scheduler_projection_backed",
                        "scheduler_slot_count": 2,
                        "harvestable_scheduler_slot_count": 0,
                        "scheduler_queue_depth": 0,
                        "harvestable_by_zone": {},
                        "harvestable_by_slot": {},
                        "scheduler_slot_samples": [
                            {
                                "scheduler_slot_id": "F:2",
                                "slot_target_id": "foundry-interactive-reserve",
                                "harvestable_gpu_count": 0,
                                "blocked_by": ["protected_reserve"],
                            },
                            "ignore-me",
                        ],
                    },
                }
            ]
        }
    )
    reserve_summary = module._build_capacity_harvest_summary(reserve_only)

    assert reserve_only["slot_pressure_state"] == "reserve_or_busy"
    assert reserve_only["idle_harvest_slots_open"] is False
    assert reserve_only["protected_reserve_slot_count"] == 1
    assert reserve_only["open_harvest_slot_ids"] == []
    assert reserve_summary["admission_state"] == "reserve_or_busy"
    assert reserve_summary["ready_for_harvest_now"] is False

    missing_projection = module._local_compute_capacity_detail({"records": []})
    missing_summary = module._build_capacity_harvest_summary(missing_projection)

    assert missing_projection["present"] is False
    assert missing_projection["slot_pressure_state"] == "no_scheduler_projection"
    assert missing_summary["admission_state"] == "no_scheduler_projection"
    assert missing_summary["harvestable_scheduler_slot_count"] == 0


def test_local_compute_capacity_detail_prefers_scheduler_backed_freshness_window() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    quota_truth = {
        "records": [
            {
                "family_id": "athanor_local_compute",
                "last_observed_at": "2026-04-13T10:00:00+00:00",
                "stale_after": "2026-04-13T10:15:00+00:00",
                "remaining_units": 6,
                "capacity_breakdown": {
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 2,
                    "harvestable_scheduler_slot_count": 1,
                    "scheduler_queue_depth": 0,
                    "harvestable_by_zone": {"F": 1},
                    "harvestable_by_slot": {"F:TP4": 1},
                    "scheduler_slot_samples": [
                        {
                            "scheduler_slot_id": "F:TP4",
                            "slot_target_id": "foundry-bulk-pool",
                            "harvestable_gpu_count": 1,
                        }
                    ],
                },
            }
        ]
    }
    capacity_telemetry = {
        "capacity_summary": {
            "sample_posture": "scheduler_projection_backed",
            "scheduler_observed_at": "2026-04-13T12:30:00+00:00",
            "scheduler_slot_count": 2,
            "harvestable_scheduler_slot_count": 1,
            "scheduler_queue_depth": 0,
            "harvestable_by_zone": {"F": 1},
            "harvestable_by_slot": {"F:TP4": 1},
        },
        "scheduler_slot_samples": [
            {
                "scheduler_slot_id": "F:TP4",
                "slot_target_id": "foundry-bulk-pool",
                "harvestable_gpu_count": 1,
            }
        ],
    }

    detail = module._local_compute_capacity_detail(quota_truth, capacity_telemetry)

    assert detail["observed_at"] == "2026-04-13T12:30:00+00:00"
    assert detail["scheduler_observed_at"] == "2026-04-13T12:30:00+00:00"
    assert detail["stale_after"] == "2026-04-13T12:45:00+00:00"


def test_workstream_autonomous_items_gain_slot_capacity_bonus_for_capacity_and_dispatch_truth() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    workstream_rows = [
        {
            "workstream": {
                "id": "capacity-and-harvest-truth",
                "title": "Capacity and Harvest Truth",
                "priority": "high",
                "status": "continuous",
                "execution_state": "ready_for_execution",
                "blocker_type": "none",
                "approval_required": False,
                "next_action_family": "capacity_truth_and_harvest_admission",
                "evidence_artifacts": ["reports/truth-inventory/capacity-telemetry.json"],
            },
            "evidence_state": {"state": "fresh"},
        },
        {
            "workstream": {
                "id": "dispatch-and-work-economy-closure",
                "title": "Dispatch and Work-Economy Closure",
                "priority": "high",
                "status": "continuous",
                "execution_state": "ready_for_execution",
                "blocker_type": "none",
                "approval_required": False,
                "next_action_family": "dispatch_truth_and_queue_replenishment",
                "evidence_artifacts": ["reports/ralph-loop/latest.json"],
            },
            "evidence_state": {"state": "fresh"},
        },
    ]
    quota_truth = {
        "records": [
            {
                "family_id": "athanor_local_compute",
                "remaining_units": 6,
                "capacity_breakdown": {
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 5,
                    "harvestable_scheduler_slot_count": 2,
                    "scheduler_queue_depth": 0,
                    "harvestable_by_zone": {"F": 1, "W": 1},
                    "harvestable_by_slot": {"F:TP4": 1, "W:1": 1},
                    "scheduler_slot_samples": [
                        {
                            "scheduler_slot_id": "F:TP4",
                            "slot_target_id": "foundry-bulk-pool",
                            "harvestable_gpu_count": 1,
                        },
                        {
                            "scheduler_slot_id": "W:1",
                            "slot_target_id": "workshop-batch-support",
                            "harvestable_gpu_count": 1,
                        },
                    ],
                },
            }
        ]
    }

    without_slots = module._build_workstream_autonomous_items(workstream_rows, {})
    with_slots = module._build_workstream_autonomous_items(workstream_rows, quota_truth)

    without_by_id = {entry["workstream_id"]: entry for entry in without_slots}
    with_by_id = {entry["workstream_id"]: entry for entry in with_slots}

    assert with_by_id["capacity-and-harvest-truth"]["id"] == "workstream:capacity-and-harvest-truth"
    assert with_by_id["dispatch-and-work-economy-closure"]["id"] == "workstream:dispatch-and-work-economy-closure"
    assert with_by_id["capacity-and-harvest-truth"]["ranking_score"] > without_by_id["capacity-and-harvest-truth"]["ranking_score"]
    assert with_by_id["dispatch-and-work-economy-closure"]["ranking_score"] > without_by_id["dispatch-and-work-economy-closure"]["ranking_score"]
    assert with_by_id["dispatch-and-work-economy-closure"]["ranking_score"] > with_by_id["capacity-and-harvest-truth"]["ranking_score"]
    assert with_by_id["capacity-and-harvest-truth"]["capacity_signal"]["harvestable_scheduler_slot_count"] == 2
    assert with_by_id["dispatch-and-work-economy-closure"]["capacity_signal"]["open_harvest_slot_ids"] == ["F:TP4", "W:1"]


def test_workstream_autonomous_items_carry_scheduler_backed_capacity_signal_freshness() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    workstream_rows = [
        {
            "workstream": {
                "id": "dispatch-and-work-economy-closure",
                "title": "Dispatch and Work-Economy Closure",
                "priority": "high",
                "status": "continuous",
                "execution_state": "ready_for_execution",
                "blocker_type": "none",
                "approval_required": False,
                "next_action_family": "dispatch_truth_and_queue_replenishment",
                "evidence_artifacts": ["reports/ralph-loop/latest.json"],
            },
            "evidence_state": {"state": "fresh"},
        }
    ]
    quota_truth = {
        "records": [
            {
                "family_id": "athanor_local_compute",
                "last_observed_at": "2026-04-13T10:00:00+00:00",
                "stale_after": "2026-04-13T10:15:00+00:00",
                "remaining_units": 6,
                "capacity_breakdown": {
                    "sample_posture": "scheduler_projection_backed",
                    "scheduler_slot_count": 2,
                    "harvestable_scheduler_slot_count": 1,
                    "scheduler_queue_depth": 0,
                    "harvestable_by_zone": {"F": 1},
                    "harvestable_by_slot": {"F:TP4": 1},
                    "scheduler_slot_samples": [
                        {
                            "scheduler_slot_id": "F:TP4",
                            "slot_target_id": "foundry-bulk-pool",
                            "harvestable_gpu_count": 1,
                        }
                    ],
                },
            }
        ]
    }
    capacity_telemetry = {
        "capacity_summary": {
            "sample_posture": "scheduler_projection_backed",
            "scheduler_observed_at": "2026-04-13T12:30:00+00:00",
            "scheduler_slot_count": 2,
            "harvestable_scheduler_slot_count": 1,
            "scheduler_queue_depth": 0,
            "harvestable_by_zone": {"F": 1},
            "harvestable_by_slot": {"F:TP4": 1},
        },
        "scheduler_slot_samples": [
            {
                "scheduler_slot_id": "F:TP4",
                "slot_target_id": "foundry-bulk-pool",
                "harvestable_gpu_count": 1,
            }
        ],
    }

    rows = module._build_workstream_autonomous_items(workstream_rows, quota_truth, capacity_telemetry)

    assert len(rows) == 1
    assert rows[0]["capacity_signal"]["observed_at"] == "2026-04-13T12:30:00+00:00"
    assert rows[0]["capacity_signal"]["scheduler_observed_at"] == "2026-04-13T12:30:00+00:00"
    assert rows[0]["capacity_signal"]["stale_after"] == "2026-04-13T12:45:00+00:00"


def test_governed_dispatch_claim_selects_top_eligible_item_and_preserves_existing_claim() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    ranked_autonomous_queue = [
        {
            "task_id": "workstream:capacity-and-harvest-truth",
            "title": "Capacity and Harvest Truth",
            "repo": "C:/Athanor",
            "source_type": "workstream",
            "workstream_id": "capacity-and-harvest-truth",
            "value_class": "capacity_truth_drift",
            "risk_class": "low",
            "approved_mutation_class": "auto_harvest",
            "preferred_lane_family": "capacity_truth_repair",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "scripts/collect_capacity_telemetry.py",
            "closure_rule": "Close capacity drift",
            "dispatchable": True,
            "capacity_signal": {"harvestable_scheduler_slot_count": 2},
        },
        {
            "task_id": "workstream:dispatch-and-work-economy-closure",
            "title": "Dispatch and Work-Economy Closure",
            "repo": "C:/Athanor",
            "source_type": "workstream",
            "workstream_id": "dispatch-and-work-economy-closure",
            "value_class": "dispatch_truth_drift",
            "risk_class": "low",
            "approved_mutation_class": "auto_harvest",
            "preferred_lane_family": "dispatch_truth_repair",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "reports/ralph-loop/latest.json",
            "closure_rule": "Close dispatch drift",
            "dispatchable": True,
        },
    ]
    dispatch_authority = {
        "governed_dispatch_ready": True,
        "approved_mutation_classes": ["auto_read_only", "auto_harvest"],
        "work_economy_ready_now": True,
    }
    approval_matrix = {
        "classes": [
            {
                "id": "auto_read_only",
                "label": "Auto read only",
                "allowed_actions": ["report_generation"],
            },
            {
                "id": "auto_harvest",
                "label": "Auto harvest",
                "allowed_actions": ["eval_run", "safe_surface_repo_task"],
            },
        ]
    }
    safe_surface_state = {
        "current_task_id": None,
        "governed_dispatch": {
            "current_task_id": "workstream:capacity-and-harvest-truth",
            "claimed_at": "2026-04-13T17:50:48.654544+00:00",
            "claim_id": "ralph-claim-preserved",
        },
    }

    claim = module._build_governed_dispatch_claim(
        ranked_autonomous_queue,
        dispatch_authority,
        approval_matrix,
        safe_surface_state,
        generated_at="2026-04-13T18:05:00+00:00",
    )

    assert claim["status"] == "claimed"
    assert claim["current_task_id"] == "workstream:capacity-and-harvest-truth"
    assert claim["claimed_at"] == "2026-04-13T17:50:48.654544+00:00"
    assert claim["claim_id"] == "ralph-claim-preserved"
    assert claim["on_deck_task_id"] == "workstream:dispatch-and-work-economy-closure"
    assert claim["approved_mutation_label"] == "Auto harvest"
    assert claim["approved_actions"] == ["eval_run", "safe_surface_repo_task"]


def test_sync_governed_dispatch_state_preserves_safe_surface_current_task_fields() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    safe_surface_state = {
        "current_task_id": "watch-refresh-foundry-remote-verification-baseline",
        "on_deck": {"task_id": "remote-baseline-dev"},
    }
    claim = {
        "status": "claimed",
        "current_task_id": "workstream:capacity-and-harvest-truth",
        "claimed_at": "2026-04-13T18:05:00+00:00",
    }

    updated = module._sync_governed_dispatch_state(safe_surface_state, claim)

    assert updated["current_task_id"] == "watch-refresh-foundry-remote-verification-baseline"
    assert updated["on_deck"]["task_id"] == "remote-baseline-dev"
    assert updated["governed_dispatch"]["current_task_id"] == "workstream:capacity-and-harvest-truth"
    assert updated["last_governed_dispatch_claimed_task_id"] == "workstream:capacity-and-harvest-truth"


def test_governed_dispatch_runtime_state_emits_durable_claim_artifact() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    runtime_state = module._build_governed_dispatch_runtime_state(
        {
            "status": "claimed",
            "dispatch_outcome": "claimed",
            "claim_source": "reports/ralph-loop/latest.json#ranked_autonomous_queue",
            "claim_id": "ralph-claim-1",
            "claimed_at": "2026-04-13T19:31:57.627318+00:00",
            "observed_at": "2026-04-13T19:31:57.627318+00:00",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "current_workstream_id": "dispatch-and-work-economy-closure",
            "current_repo": "C:/Athanor",
            "current_source_type": "workstream",
            "value_class": "dispatch_truth_drift",
            "risk_class": "low",
            "approved_mutation_class": "auto_harvest",
            "approved_mutation_label": "Auto harvest",
            "approved_actions": ["eval_run", "safe_surface_repo_task"],
            "preferred_lane_family": "dispatch_truth_repair",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "scripts/run_ralph_loop_pass.py --skip-refresh",
            "closure_rule": "Keep queue replenished.",
            "on_deck_task_id": "workstream:capacity-and-harvest-truth",
            "on_deck_task_title": "Capacity and Harvest Truth",
            "on_deck_lane_family": "capacity_truth_repair",
            "capacity_signal": {"harvestable_scheduler_slot_count": 2},
            "eligible_queue_count": 3,
        },
        {
            "phase_label": "governed_dispatch_shadow",
            "governed_dispatch_ready": True,
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
            "work_economy_ready_now": True,
        },
        {
            "queue_count": 4,
            "dispatchable_queue_count": 3,
            "blocked_queue_count": 1,
            "top_dispatchable_task_id": "workstream:dispatch-and-work-economy-closure",
            "top_dispatchable_title": "Dispatch and Work-Economy Closure",
            "top_dispatchable_lane_family": "dispatch_truth_repair",
            "recent_dispatch_outcome_count": 2,
            "last_outcome": "claimed",
            "last_success_at": None,
            "recent_dispatch_outcomes": [{"task_id": "workstream:dispatch-and-work-economy-closure"}],
        },
        {
            "queue_count": 0,
            "dispatchable_queue_count": 0,
        },
        {
            "status": "materialized",
            "backlog_id": "backlog-7",
            "backlog_status": "ready",
        },
        {
            "status": "dispatched",
            "dispatch_outcome": "success",
            "backlog_id": "backlog-7",
            "backlog_status": "scheduled",
            "task_id": "task-7",
            "task_status": "scheduled",
            "report_path": "reports/truth-inventory/governed-dispatch-execution.json",
        },
        generated_at="2026-04-13T19:31:57.627318+00:00",
    )

    assert runtime_state["report_path"] == "reports/truth-inventory/governed-dispatch-state.json"
    assert runtime_state["status"] == "claimed"
    assert runtime_state["current_task_id"] == "workstream:dispatch-and-work-economy-closure"
    assert runtime_state["approved_actions"] == ["eval_run", "safe_surface_repo_task"]
    assert runtime_state["dispatchable_queue_count"] == 3
    assert runtime_state["top_dispatchable_lane_family"] == "dispatch_truth_repair"
    assert runtime_state["dispatch_outcome"] == "success"
    assert runtime_state["materialization"]["status"] == "materialized"
    assert runtime_state["materialization"]["backlog_id"] == "backlog-7"
    assert runtime_state["execution"]["status"] == "dispatched"
    assert runtime_state["execution"]["task_id"] == "task-7"
    assert runtime_state["governed_dispatch_claim"]["claim_id"] == "ralph-claim-1"


def test_governed_dispatch_runtime_state_stays_truthful_when_idle() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    runtime_state = module._build_governed_dispatch_runtime_state(
        {
            "status": "idle",
            "dispatch_outcome": "idle",
            "current_task_id": None,
            "current_task_title": None,
            "approved_actions": [],
        },
        {
            "phase_label": "governed_dispatch_shadow",
            "governed_dispatch_ready": False,
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
            "work_economy_ready_now": False,
        },
        {
            "queue_count": 0,
            "dispatchable_queue_count": 0,
            "blocked_queue_count": 0,
            "recent_dispatch_outcome_count": 0,
            "recent_dispatch_outcomes": [],
        },
        {
            "queue_count": 0,
            "dispatchable_queue_count": 0,
        },
        {
            "status": "no_claim",
        },
        {
            "status": "no_claim",
        },
        generated_at="2026-04-13T19:31:57.627318+00:00",
    )

    assert runtime_state["status"] == "idle"
    assert runtime_state["current_task_id"] is None
    assert runtime_state["governed_dispatch_ready"] is False
    assert runtime_state["dispatchable_queue_count"] == 0
    assert runtime_state["recent_dispatch_outcome_count"] == 0
    assert runtime_state["materialization"]["status"] == "no_claim"
    assert runtime_state["execution"]["status"] == "no_claim"


def test_materialize_governed_dispatch_claim_creates_backlog_item_when_missing() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((base_url, token, path, payload))
        if method == "GET":
            return 200, {"backlog": []}
        return 200, {"backlog": {"id": "backlog-42", "status": "ready"}}

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "preferred_lane_family": "dispatch_truth_repair",
            "approved_mutation_class": "auto_harvest",
            "approved_mutation_label": "Auto harvest",
            "proof_command_or_eval_surface": "scripts/run_ralph_loop_pass.py --skip-refresh",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-13T20:55:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "materialized"
    assert materialization["backlog_id"] == "backlog-42"
    assert materialization["backlog_status"] == "ready"
    assert calls[0][2] == "/v1/operator/backlog?limit=120"
    assert calls[1][2] == "/v1/operator/backlog"
    created_payload = calls[1][3] or {}
    assert created_payload["title"] == "Dispatch and Work-Economy Closure"
    assert created_payload["owner_agent"] == "coding-agent"
    assert created_payload["approval_mode"] == "none"
    assert created_payload["metadata"]["claim_id"] == "ralph-claim-42"
    assert created_payload["metadata"]["_autonomy_managed"] is True
    assert created_payload["metadata"]["_autonomy_source"] == "pipeline"
    assert created_payload["metadata"]["task_class"] == "async_backlog_execution"
    assert created_payload["metadata"]["workload_class"] == "coding_implementation"


def test_materialize_governed_dispatch_claim_reuses_existing_backlog_item() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        assert method == "GET"
        return 200, {
            "backlog": [
                {
                    "id": "backlog-existing",
                    "status": "ready",
                    "title": "Dispatch and Work-Economy Closure",
                    "prompt": 'Advance the governed dispatch claim for "Dispatch and Work-Economy Closure".',
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "claim_id": "ralph-claim-99",
                        "current_task_id": "workstream:dispatch-and-work-economy-closure",
                        "latest_task_id": "task-old",
                    },
                }
            ]
        }

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-99",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-13T20:55:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "already_materialized"
    assert materialization["backlog_id"] == "backlog-existing"
    assert materialization["backlog_status"] == "ready"
    assert materialization["latest_task_id"] == "task-old"


def test_refresh_governed_dispatch_materialization_after_dispatch_requeries_backlog() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path))
        assert method == "GET"
        return 200, {
            "backlog": [
                {
                    "id": "backlog-existing",
                    "status": "scheduled",
                    "title": "Dispatch and Work-Economy Closure",
                    "prompt": 'Advance the governed dispatch claim for "Dispatch and Work-Economy Closure".',
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "claim_id": "ralph-claim-99",
                        "current_task_id": "workstream:dispatch-and-work-economy-closure",
                        "latest_task_id": "task-new",
                    },
                }
            ]
        }

    refreshed = module._refresh_governed_dispatch_materialization_after_execution(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-99",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-existing",
            "backlog_status": "running",
            "latest_task_id": "task-old",
        },
        {
            "status": "dispatched",
            "backlog_id": "backlog-existing",
            "task_id": "task-new",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert refreshed["status"] == "already_materialized"
    assert refreshed["backlog_id"] == "backlog-existing"
    assert refreshed["backlog_status"] == "scheduled"
    assert refreshed["latest_task_id"] == "task-new"
    assert calls == [("GET", "/v1/operator/backlog?limit=120")]


def test_dispatch_governed_dispatch_claim_repairs_stale_waiting_approval_task_then_redispatches() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET" and path == "/v1/tasks/task-old":
            return 200, {
                "task": {
                    "id": "task-old",
                    "status": "pending_approval",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "governor_autonomy_level": "C",
                    },
                }
            }
        if method == "POST" and path == "/v1/tasks/task-old/reject":
            return 200, {"status": "rejected"}
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/dispatch":
            return 200, {
                "backlog": {"id": "backlog-42", "status": "scheduled"},
                "task": {"id": "task-new", "status": "scheduled"},
                "governor": {"reason": "phase_gate_auto", "level": "A"},
            }
        raise AssertionError(f"Unexpected request: {method} {path}")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "waiting_approval",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["repaired_stale_task_id"] == "task-old"
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert execution["governor_level"] == "A"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/tasks/task-old/reject",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]


def test_dispatch_governed_dispatch_claim_dispatches_ready_backlog_item() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((base_url, token, path, payload))
        assert method == "POST"
        return 200, {
            "backlog": {"id": "backlog-42", "status": "scheduled"},
            "task": {"id": "task-42", "status": "scheduled"},
            "governor": {"reason": "auto_harvest", "level": "allow"},
        }

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "ready",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["backlog_id"] == "backlog-42"
    assert execution["backlog_status"] == "scheduled"
    assert execution["task_id"] == "task-42"
    assert execution["task_status"] == "scheduled"
    assert execution["governor_reason"] == "auto_harvest"
    assert execution["governor_level"] == "allow"
    assert execution["dispatch_path"] == "/v1/operator/backlog/backlog-42/dispatch"
    assert calls == [
        (
            "http://agent.local",
            "token",
            "/v1/operator/backlog/backlog-42/dispatch",
            {
                "actor": "ralph-loop",
                "session_id": "ralph-loop",
                "correlation_id": calls[0][3]["correlation_id"],
                "reason": "Auto-dispatched governed dispatch claim ralph-claim-42",
            },
        )
    ]


def test_dispatch_governed_dispatch_claim_skips_already_scheduled_backlog_item() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    def fake_request_json(*args, **kwargs):
        raise AssertionError("request_json should not be called for already scheduled backlog")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "already_dispatched"
    assert execution["dispatch_outcome"] == "claimed"
    assert execution["backlog_id"] == "backlog-42"
    assert execution["backlog_status"] == "scheduled"


def test_dispatch_governed_dispatch_claim_surfaces_restart_recovered_retry_truth() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        assert method == "GET"
        assert path == "/v1/tasks/task-retry"
        return 200, {
            "task": {
                "id": "task-retry",
                "status": "running",
                "source": "auto-retry",
                "retry_count": 1,
                "retry_lineage": ["task-old"],
                "previous_error": "Execution lease expired during server restart",
                "metadata": {
                    "materialization_source": "governed_dispatch_state",
                    "retry_of": "task-old",
                    "recovery": {
                        "event": "stale_lease_recovered",
                        "reason": "server_restart",
                    },
                    "governor_decision": "auto_retry_allowed",
                    "governor_autonomy_level": "A",
                },
            }
        }

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
            "latest_task_id": "task-retry",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "already_dispatched"
    assert execution["dispatch_outcome"] == "claimed"
    assert execution["task_id"] == "task-retry"
    assert execution["task_source"] == "auto-retry"
    assert execution["retry_of_task_id"] == "task-old"
    assert execution["retry_count"] == 1
    assert execution["retry_lineage_depth"] == 1
    assert execution["recovery_event"] == "stale_lease_recovered"
    assert execution["recovery_reason"] == "server_restart"
    assert execution["resilience_state"] == "restart_recovered"
    assert execution["advisory_blockers"] == ["agent_runtime_restart_recovered"]


def test_dispatch_governed_dispatch_claim_redispatches_scheduled_backlog_item_after_stale_lease() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET" and path == "/v1/tasks/task-old":
            return 200, {
                "task": {
                    "id": "task-old",
                    "status": "stale_lease",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "recovery": {
                            "event": "stale_lease_recovered",
                            "reason": "server_restart",
                        },
                    },
                }
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/dispatch":
            return 200, {
                "backlog": {"id": "backlog-42", "status": "scheduled"},
                "task": {"id": "task-new", "status": "scheduled"},
                "governor": {"reason": "phase_gate_auto", "level": "A"},
            }
        raise AssertionError(f"Unexpected request: {method} {path}")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["repaired_stale_task_id"] == "task-old"
    assert execution["recovery_event"] == "stale_lease_recovered"
    assert execution["resilience_state"] == "restart_interfering"
    assert execution["advisory_blockers"] == ["agent_runtime_restart_interfering"]
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]


def test_dispatch_governed_dispatch_claim_repairs_failed_private_local_task_then_redispatches() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET" and path == "/v1/tasks/task-old":
            return 200, {
                "task": {
                    "id": "task-old",
                    "status": "failed",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "task_class": "private_automation",
                        "workload_class": "private_automation",
                        "execution_lease": {
                            "provider": "athanor_local",
                            "fallback": [],
                        },
                    },
                }
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/dispatch":
            return 200, {
                "backlog": {"id": "backlog-42", "status": "scheduled"},
                "task": {"id": "task-new", "status": "scheduled"},
                "governor": {"reason": "phase_gate_auto", "level": "A"},
            }
        raise AssertionError(f"Unexpected request: {method} {path}")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["repair_reason"] == "failed_private_local_dispatch"
    assert execution["repaired_task_id"] == "task-old"
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]


def test_dispatch_governed_dispatch_claim_repairs_retry_eligible_failed_task_then_redispatches() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET" and path == "/v1/tasks/task-old":
            return 200, {
                "task": {
                    "id": "task-old",
                    "status": "failed",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "_autonomy_managed": True,
                        "task_class": "async_backlog_execution",
                        "workload_class": "coding_implementation",
                        "execution_lease": {
                            "provider": "openai_codex",
                            "fallback": ["zai_glm_coding", "athanor_local"],
                        },
                        "failure": {
                            "retry_eligible": True,
                            "stage": "execution_exception",
                        },
                    },
                }
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/dispatch":
            return 200, {
                "backlog": {"id": "backlog-42", "status": "scheduled"},
                "task": {"id": "task-new", "status": "scheduled"},
                "governor": {"reason": "phase_gate_auto", "level": "A"},
            }
        raise AssertionError(f"Unexpected request: {method} {path}")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["repair_reason"] == "retry_eligible_failed_dispatch"
    assert execution["repaired_task_id"] == "task-old"
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]


def test_dispatch_governed_dispatch_claim_surfaces_failed_existing_task_when_not_repairable() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        assert method == "GET"
        assert path == "/v1/tasks/task-old"
        return 200, {
            "task": {
                "id": "task-old",
                "status": "failed",
                "metadata": {
                    "materialization_source": "governed_dispatch_state",
                    "_autonomy_managed": True,
                    "task_class": "async_backlog_execution",
                    "workload_class": "coding_implementation",
                    "execution_lease": {
                        "provider": "openai_codex",
                        "fallback": ["zai_glm_coding"],
                    },
                    "failure": {
                        "retry_eligible": False,
                        "stage": "execution_exception",
                    },
                },
            }
        }

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:dispatch-and-work-economy-closure",
            "current_task_title": "Dispatch and Work-Economy Closure",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "scheduled",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "failed_existing_task"
    assert execution["dispatch_outcome"] == "failed"
    assert execution["task_id"] == "task-old"
    assert execution["task_status"] == "failed"
    assert execution["advisory_blockers"] == ["governed_dispatch_failed_task"]


def test_automation_feedback_summary_compresses_recent_runs_without_noise() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    recent_records = [
        {
            "timestamp": "2026-04-13T12:03:00+00:00",
            "automation_id": "ralph-loop",
            "lane": "ralph_loop",
            "action_class": "autonomous_planning",
            "result": {"validation_passed": True},
        },
        {
            "timestamp": "2026-04-13T12:01:00+00:00",
            "automation_id": "contract-healer",
            "lane": "contract_healer",
            "action_class": "drift_report_generation",
            "result": {"success": False},
        },
        {
            "timestamp": "2026-04-13T11:58:00+00:00",
            "automation_id": "restore-drill-evidence",
            "lane": "recovery_evidence",
            "action_class": "restore_drill_rehearsal",
            "result": {"success": True},
        },
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["source_stream"] == "athanor:automation:runs"
    assert summary["recent_run_count"] == 3
    assert summary["recognized_run_count"] == 3
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 1
    assert summary["unknown_count"] == 0
    assert summary["last_outcome"] == "success"
    assert summary["last_success_at"] == "2026-04-13T12:03:00+00:00"
    assert summary["last_failure_at"] == "2026-04-13T12:01:00+00:00"
    assert summary["feedback_state"] == "mixed"


def test_automation_feedback_summary_surfaces_dispatch_completion_records() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    recent_records = [
        {
            "timestamp": "2026-04-13T15:05:00+00:00",
            "automation_id": "subscription-burn:claude_max",
            "lane": "subscription_burn",
            "action_class": "burn_reaper_completion",
            "inputs": {
                "subscription": "claude_max",
                "task_id": "task-42",
                "task_title": "Close validator debt",
            },
            "result": {
                "subscription": "claude_max",
                "dispatch_outcome": "success",
                "success": True,
                "completed_at": "2026-04-13T15:05:00+00:00",
            },
            "operator_visible_summary": "Subscription burn claude_max completed with success.",
        },
        {
            "timestamp": "2026-04-13T14:55:00+00:00",
            "automation_id": "ralph-loop",
            "lane": "ralph_loop",
            "action_class": "autonomous_planning",
            "result": {"validation_passed": True},
            "operator_visible_summary": "Ralph loop selected governor scheduling.",
        },
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["dispatch_last_outcome"] == "success"
    assert summary["dispatch_last_success_at"] == "2026-04-13T15:05:00+00:00"
    assert summary["recent_dispatch_outcome_count"] == 1
    assert summary["recent_dispatch_outcomes"][0]["task_id"] == "task-42"
    assert summary["recent_dispatch_outcomes"][0]["summary"] == "Subscription burn claude_max completed with success."


def test_automation_feedback_summary_surfaces_dispatch_claim_records() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    recent_records = [
        {
            "timestamp": "2026-04-13T18:05:00+00:00",
            "automation_id": "ralph-loop",
            "lane": "ralph_loop",
            "action_class": "autonomous_planning",
            "result": {
                "dispatch_outcome": "claimed",
                "claimed_task_id": "workstream:capacity-and-harvest-truth",
                "claimed_task_title": "Capacity and Harvest Truth",
            },
            "operator_visible_summary": "Ralph loop claimed capacity-and-harvest-truth.",
        }
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["dispatch_last_outcome"] == "claimed"
    assert summary["recent_dispatch_outcome_count"] == 1
    assert summary["recent_dispatch_outcomes"][0]["task_id"] == "workstream:capacity-and-harvest-truth"
    assert summary["recent_dispatch_outcomes"][0]["task_title"] == "Capacity and Harvest Truth"


def test_capture_automation_feedback_and_emit_includes_same_pass_claim_record() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    emitted = {"done": False}

    class DummyEmitResult:
        def __init__(self, persisted: bool) -> None:
            self.persisted = persisted

    async def fake_emit(record):
        emitted["done"] = True
        return DummyEmitResult(persisted=True)

    async def fake_read_recent_automation_run_records(*, limit=8, **_kwargs):
        if not emitted["done"]:
            return []
        return [
            {
                "timestamp": "2026-04-13T18:05:00+00:00",
                "automation_id": "ralph-loop",
                "lane": "ralph_loop",
                "action_class": "autonomous_planning",
                "result": {
                    "dispatch_outcome": "claimed",
                    "claimed_task_id": "workstream:capacity-and-harvest-truth",
                    "claimed_task_title": "Capacity and Harvest Truth",
                },
                "operator_visible_summary": "Ralph loop claimed capacity-and-harvest-truth.",
            }
        ]

    module.emit_automation_run_record = fake_emit
    module.read_recent_automation_run_records = fake_read_recent_automation_run_records

    record = module.AutomationRunRecord(
        automation_id="ralph-loop",
        lane="ralph_loop",
        action_class="autonomous_planning",
        inputs={"selected_workstream_id": "capacity-and-harvest-truth"},
        result={"dispatch_outcome": "claimed"},
        rollback={},
        duration=0.05,
        operator_visible_summary="Ralph loop claimed capacity-and-harvest-truth.",
    )

    summary, emit_result = module.asyncio.run(module._capture_automation_feedback_and_emit(record, limit=4))

    assert emit_result.persisted is True
    assert summary["dispatch_last_outcome"] == "claimed"
    assert summary["recent_dispatch_outcome_count"] == 1
    assert summary["recent_dispatch_outcomes"][0]["task_id"] == "workstream:capacity-and-harvest-truth"


def test_governor_scheduling_next_actions_include_dispatch_replenishment_commands() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    selected_workstream = {
        "id": "dispatch-and-work-economy-closure",
        "title": "Dispatch and Work-Economy Closure",
        "execution_state": "ready_for_execution",
        "approval_required": False,
        "blocker_type": "none",
        "next_action_family": "dispatch_truth_and_queue_replenishment",
        "evidence_artifacts": ["reports/ralph-loop/latest.json"],
    }
    ranked_autonomous_queue = [
        {"dispatchable": True, "task_id": "task-1", "title": "Task 1"},
    ]

    actions = module._build_next_actions("governor_scheduling", selected_workstream, ranked_autonomous_queue)

    assert actions[0]["type"] == "queue_item"
    assert {"type": "command", "command": [module.sys.executable, "scripts/collect_capacity_telemetry.py"]} in actions
    assert {"type": "command", "command": [module.sys.executable, "scripts/run_ralph_loop_pass.py", "--skip-refresh"]} in actions
    assert {"type": "command", "command": [module.sys.executable, "scripts/validate_platform_contract.py"]} in actions


def test_operator_facing_state_aliases_surface_loop_mode_top_task_and_queue() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    selected_workstream = {
        "id": "dispatch-and-work-economy-closure",
        "title": "Dispatch and Work-Economy Closure",
    }
    ranked_autonomous_queue = [
        {
            "task_id": "workstream:dispatch-and-work-economy-closure",
            "title": "Dispatch and Work-Economy Closure",
            "dispatchable": True,
            "preferred_lane_family": "dispatch_truth_repair",
            "approved_mutation_class": "auto_harvest",
            "value_class": "dispatch_truth_drift",
            "risk_class": "medium",
        }
    ]
    autonomous_queue_summary = {
        "dispatchable_queue_count": 1,
        "top_dispatchable_task_id": "workstream:dispatch-and-work-economy-closure",
        "top_dispatchable_title": "Dispatch and Work-Economy Closure",
    }
    dispatch_authority = {
        "provider_gate_state": "completed",
        "work_economy_status": "ready",
    }

    aliases = module._build_operator_facing_state_aliases(
        "governor_scheduling",
        selected_workstream,
        ranked_autonomous_queue,
        autonomous_queue_summary,
        dispatch_authority,
    )

    assert aliases["loop_mode"] == "governor_scheduling"
    assert aliases["dispatchable_queue_count"] == 1
    assert aliases["provider_gate_state"] == "completed"
    assert aliases["work_economy_status"] == "ready"
    assert aliases["autonomous_queue"] == ranked_autonomous_queue
    assert aliases["top_task"] == {
        "id": "workstream:dispatch-and-work-economy-closure",
        "title": "Dispatch and Work-Economy Closure",
        "dispatch_ready": True,
        "preferred_lane_family": "dispatch_truth_repair",
        "approved_mutation_class": "auto_harvest",
        "value_class": "dispatch_truth_drift",
        "risk_class": "medium",
        "source": "ranked_autonomous_queue",
    }


def test_sync_registry_loop_state_preserves_specific_next_action_family_for_dispatch_closure(tmp_path) -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    original_config_dir = module.CONFIG_DIR
    module.CONFIG_DIR = tmp_path
    try:
        completion_program = {}
        autonomy_activation = {"current_phase_id": "phase-3"}
        selected_workstream = {
            "id": "dispatch-and-work-economy-closure",
            "title": "Dispatch and Work-Economy Closure",
            "execution_state": "ready_for_execution",
            "approval_required": False,
            "blocker_type": "none",
            "next_action_family": "dispatch_truth_and_queue_replenishment",
        }

        module._sync_registry_loop_state(
            completion_program=completion_program,
            autonomy_activation=autonomy_activation,
            selected_family="governor_scheduling",
            selected_workstream=selected_workstream,
            any_stale_evidence=False,
        )

        written = (tmp_path / "completion-program-registry.json").read_text(encoding="utf-8")
        assert '"next_action_family": "dispatch_truth_and_queue_replenishment"' in written
        assert completion_program["ralph_loop"]["next_action_family"] == "dispatch_truth_and_queue_replenishment"
    finally:
        module.CONFIG_DIR = original_config_dir


def test_refresh_commands_include_capacity_telemetry_collection() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    assert [module.sys.executable, "scripts/collect_capacity_telemetry.py"] in module.REFRESH_COMMANDS
    assert module.LOOP_FAMILY_NEXT_COMMANDS["evidence_refresh"] == module.REFRESH_COMMANDS
