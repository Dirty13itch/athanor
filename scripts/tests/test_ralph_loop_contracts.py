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


def test_artifact_freshness_treats_external_blocked_github_portfolio_as_fresh_block() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    artifact_path = module.REPO_ROOT / "reports" / "reconciliation" / "github-portfolio-latest.json"
    original_text = artifact_path.read_text(encoding="utf-8") if artifact_path.exists() else None
    try:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            '{\n'
            '  "sync_status": "external_blocked",\n'
            '  "blocking_reason": "github_auth_required",\n'
            '  "last_attempted_at": "2026-04-19T02:40:00+00:00",\n'
            '  "last_error": "HTTP 401: Bad credentials"\n'
            '}\n',
            encoding="utf-8",
        )

        freshness = module._artifact_freshness(now_ts=0)
        github_portfolio = freshness["github_portfolio"]

        assert github_portfolio["stale"] is False
        assert github_portfolio["freshness_state"] == "external_dependency_blocked"
        assert github_portfolio["blocking_reason"] == "github_auth_required"

        evidence_state = module._evidence_state_for_workstream(
            {
                "evidence_artifacts": [
                    "reports/reconciliation/github-portfolio-latest.json",
                ]
            },
            freshness,
        )

        assert evidence_state["stale_count"] == 0
        assert evidence_state["external_blocked_count"] == 1
        assert evidence_state["state"] == "external_dependency_blocked"
    finally:
        if original_text is None:
            artifact_path.unlink(missing_ok=True)
        else:
            artifact_path.write_text(original_text, encoding="utf-8")


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


def test_resolve_validation_state_preserves_previous_validation_when_skip_validation_is_requested() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    previous = {
        "ran": True,
        "results": [{"command": ["python3", "validate.py"], "returncode": 0}],
        "all_passed": True,
    }

    resolved = module._resolve_validation_state(
        skip_validation=True,
        previous_validation=previous,
        validation_results=[],
    )

    assert resolved == previous


def test_resolve_validation_state_records_new_validation_results_when_validation_runs() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    resolved = module._resolve_validation_state(
        skip_validation=False,
        previous_validation={"ran": True, "results": [], "all_passed": True},
        validation_results=[
            {"command": ["python3", "check-a.py"], "returncode": 0},
            {"command": ["python3", "check-b.py"], "returncode": 0},
        ],
    )

    assert resolved["ran"] is True
    assert resolved["all_passed"] is True
    assert len(resolved["results"]) == 2


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


def test_governed_dispatch_claim_rotates_off_recent_no_delta_task_when_alternative_exists() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    ranked_autonomous_queue = [
        {
            "task_id": "workstream:validation-and-publication",
            "title": "Validation and Publication",
            "repo": "C:/Athanor",
            "source_type": "workstream",
            "workstream_id": "validation-and-publication",
            "value_class": "failing_eval_or_validator",
            "risk_class": "low",
            "approved_mutation_class": "auto_harvest",
            "preferred_lane_family": "validation_and_checkpoint",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "scripts/run_full_validation.py",
            "closure_rule": "Close validator drift",
            "dispatchable": True,
        },
        {
            "task_id": "capability:agent-governance-toolkit-policy-plane",
            "title": "Agent Governance Toolkit Policy Plane",
            "repo": "C:/Athanor",
            "source_type": "capability",
            "value_class": "promotion_wave_closure",
            "risk_class": "low",
            "approved_mutation_class": "auto_harvest",
            "preferred_lane_family": "promotion_wave_closure",
            "fallback_lane_family": "operator_follow_through",
            "proof_command_or_eval_surface": "reports/promotions/latest.json",
            "closure_rule": "Close the policy-plane promotion tranche",
            "dispatchable": True,
        },
    ]
    dispatch_authority = {
        "governed_dispatch_ready": True,
        "approved_mutation_classes": ["auto_harvest"],
        "work_economy_ready_now": True,
    }
    approval_matrix = {
        "classes": [
            {
                "id": "auto_harvest",
                "label": "Auto harvest",
                "allowed_actions": ["eval_run", "safe_surface_repo_task"],
            },
        ]
    }
    safe_surface_state = {
        "governed_dispatch": {
            "current_task_id": "workstream:validation-and-publication",
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
        automation_feedback_summary={
            "recent_no_delta_task_ids": ["workstream:validation-and-publication"],
        },
    )

    assert claim["status"] == "claimed"
    assert claim["current_task_id"] == "capability:agent-governance-toolkit-policy-plane"
    assert claim["claim_rotation_reason"] == "recent_no_delta_suppressed"
    assert claim["claim_id"] != "ralph-claim-preserved"
    assert claim["on_deck_task_id"] == "workstream:validation-and-publication"


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
            "suppressed_queue_count": 0,
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
            "suppressed_queue_count": 0,
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


def test_materialize_governed_dispatch_claim_ignores_completed_backlog_and_rematerializes() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {
                "backlog": [
                    {
                        "id": "backlog-completed",
                        "status": "completed",
                        "title": "Capacity and Harvest Truth",
                        "prompt": 'Advance the governed dispatch claim for "Capacity and Harvest Truth".',
                        "metadata": {
                            "materialization_source": "governed_dispatch_state",
                            "claim_id": "ralph-claim-99",
                            "current_task_id": "workstream:capacity-and-harvest-truth",
                            "latest_task_id": "task-old",
                        },
                    }
                ]
            }
        return 200, {"backlog": {"id": "backlog-new", "status": "ready"}}

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-99",
            "current_task_id": "workstream:capacity-and-harvest-truth",
            "current_task_title": "Capacity and Harvest Truth",
            "preferred_lane_family": "capacity_truth_repair",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-21T05:05:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "materialized"
    assert materialization["backlog_id"] == "backlog-new"
    assert materialization["backlog_status"] == "ready"
    assert [entry[1] for entry in calls] == [
        "/v1/operator/backlog?limit=120",
        "/v1/operator/backlog",
    ]


def test_materialize_governed_dispatch_claim_carries_validation_proof_commands() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {"backlog": []}
        return 200, {"backlog": {"id": "backlog-proof-1", "status": "ready"}}

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-proof-1",
            "current_task_id": "workstream:validation-and-publication",
            "current_task_title": "Validation and Publication",
            "preferred_lane_family": "validation_and_checkpoint",
            "approved_mutation_class": "auto_read_only",
            "approved_mutation_label": "Auto read only",
            "proof_command_or_eval_surface": f"{module.sys.executable} scripts/validate_platform_contract.py",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-19T01:20:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "materialized"
    created_payload = calls[1][2] or {}
    assert created_payload["metadata"]["proof_commands"] == module.VALIDATION_COMMANDS
    assert created_payload["metadata"]["proof_command_surface"] == f"{module.sys.executable} scripts/validate_platform_contract.py"
    assert created_payload["metadata"]["preferred_provider_id"] == "openai_codex"
    assert created_payload["metadata"]["policy_class"] == "private_but_cloud_allowed"
    assert created_payload["metadata"]["meta_lane"] == "frontier_cloud"


def test_materialize_governed_dispatch_claim_carries_capacity_proof_commands() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {"backlog": []}
        return 200, {"backlog": {"id": "backlog-proof-2", "status": "ready"}}

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-proof-2",
            "current_task_id": "workstream:capacity-and-harvest-truth",
            "current_task_title": "Capacity and Harvest Truth",
            "preferred_lane_family": "capacity_truth_repair",
            "approved_mutation_class": "auto_harvest",
            "approved_mutation_label": "Auto harvest",
            "proof_command_or_eval_surface": f"{module.sys.executable} scripts/run_gpu_scheduler_baseline_eval.py",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-19T01:20:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "materialized"
    created_payload = calls[1][2] or {}
    assert created_payload["metadata"]["proof_commands"] == [
        [module.sys.executable, "scripts/run_gpu_scheduler_baseline_eval.py"],
        [module.sys.executable, "scripts/collect_capacity_telemetry.py"],
        [module.sys.executable, "scripts/write_quota_truth_snapshot.py"],
    ]
    assert created_payload["metadata"]["proof_command_surface"] == f"{module.sys.executable} scripts/run_gpu_scheduler_baseline_eval.py"


def test_materialize_governed_dispatch_claim_carries_product_value_proof_commands() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    module._load_agent_runtime = lambda: ("http://agent.local", "token")

    calls: list[tuple[str, str, dict | None]] = []

    def fake_request_json(base_url: str, token: str, path: str, *, method: str = "GET", payload=None, timeout: int = 20):
        calls.append((method, path, payload))
        if method == "GET":
            return 200, {"backlog": []}
        return 200, {"backlog": {"id": "backlog-proof-3", "status": "ready"}}

    materialization = module._materialize_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-proof-3",
            "current_task_id": "autonomous_value_canary:dashboard-visible-proof",
            "current_task_title": "Produce a visible dashboard value proof",
            "preferred_lane_family": "safe_surface_execution",
            "approved_mutation_class": "auto_read_only",
            "approved_mutation_label": "Auto read only",
            "autonomous_value_canary_id": "dashboard-visible-proof",
            "value_stage": "product_value",
            "beneficiary_surface": "dashboard",
            "deliverable_kind": "ui_change",
            "deliverable_refs": ["projects/dashboard/src/features/overview/command-center.tsx"],
            "task_brief": "Add a visible dashboard proof card.",
            "proof_command_or_eval_surface": "projects/dashboard/src/features/overview/command-center.tsx",
        },
        {
            "provider_gate_state": "completed",
            "work_economy_status": "ready",
        },
        generated_at="2026-04-20T04:50:00+00:00",
        request_json=fake_request_json,
    )

    assert materialization["status"] == "materialized"
    created_payload = calls[1][2] or {}
    assert created_payload["metadata"]["proof_commands"] == [
        [module.sys.executable, "scripts/run_dashboard_value_proof.py", "--surface", "dashboard_overview"]
    ]
    assert created_payload["metadata"]["proof_artifact_paths"] == [
        "projects/dashboard/src/features/overview/command-center.tsx"
    ]
    assert created_payload["metadata"]["proof_execution_stage"] == "after_agent"
    assert created_payload["metadata"]["proof_timeout_seconds"] == 900
    assert created_payload["metadata"]["preferred_provider_id"] == "google_gemini"
    assert created_payload["metadata"]["requires_mutable_implementation_authority"] is True
    assert created_payload["metadata"]["task_brief"] == "Add a visible dashboard proof card."


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


def test_dispatch_governed_dispatch_claim_repairs_completed_scheduled_backlog_then_redispatches() -> None:
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
                    "status": "completed",
                    "source": "operator_backlog_dispatch",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "_autonomy_managed": True,
                        "task_class": "async_backlog_execution",
                        "workload_class": "coding_implementation",
                    },
                }
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/transition":
            return 200, {
                "status": "updated",
                "backlog": {"id": "backlog-42", "status": "ready"},
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
            "current_task_id": "workstream:validation-and-publication",
            "current_task_title": "Validation and Publication",
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
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert execution["repair_reason"] == "stale_terminal_dispatch"
    assert execution["repair_status_code"] == 200
    assert execution["repaired_task_id"] == "task-old"
    assert execution["repaired_stale_task_id"] == "task-old"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog/backlog-42/transition",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]
    assert calls[1][2]["status"] == "ready"
    assert "task-old" in str(calls[1][2]["note"])


def test_dispatch_governed_dispatch_claim_reports_repair_failure_when_stale_terminal_backlog_cannot_reopen() -> None:
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
                    "status": "completed",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "_autonomy_managed": True,
                        "task_class": "async_backlog_execution",
                        "workload_class": "coding_implementation",
                    },
                }
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/transition":
            return 409, {"error": "cannot reopen backlog item"}
        raise AssertionError(f"Unexpected request: {method} {path}")

    execution = module._dispatch_governed_dispatch_claim(
        {
            "status": "claimed",
            "claim_id": "ralph-claim-42",
            "current_task_id": "workstream:validation-and-publication",
            "current_task_title": "Validation and Publication",
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

    assert execution["status"] == "repair_failed"
    assert execution["dispatch_outcome"] == "failed"
    assert execution["repair_status_code"] == 409
    assert execution["repair_reason"] == "stale_terminal_dispatch"
    assert execution["repaired_task_id"] == "task-old"
    assert execution["repaired_stale_task_id"] == "task-old"
    assert "cannot reopen backlog item" in str(execution["error"])
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog/backlog-42/transition",
    ]


def test_dispatch_governed_dispatch_claim_repairs_blocked_verification_backlog_then_redispatches() -> None:
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
                    "status": "completed",
                    "source": "auto-retry",
                    "metadata": {
                        "materialization_source": "governed_dispatch_state",
                        "_autonomy_managed": True,
                        "task_class": "async_backlog_execution",
                        "workload_class": "coding_implementation",
                    },
                }
            }
        if method == "GET" and path == "/v1/operator/backlog?limit=200":
            return 200, {
                "backlog": [
                    {
                        "id": "backlog-42",
                        "status": "blocked",
                        "blocking_reason": "verification_evidence_missing",
                        "metadata": {
                            "verification_pending_reason": "verification_evidence_missing",
                            "failure_detail": "old proof bundle failure",
                        },
                    }
                ]
            }
        if method == "POST" and path == "/v1/operator/backlog/backlog-42/transition":
            return 200, {
                "status": "updated",
                "backlog": {"id": "backlog-42", "status": "ready"},
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
            "current_task_id": "workstream:validation-and-publication",
            "current_task_title": "Validation and Publication",
            "approved_mutation_class": "auto_harvest",
            "dispatch_outcome": "claimed",
        },
        {
            "approved_mutation_classes": ["auto_harvest"],
        },
        {
            "status": "already_materialized",
            "backlog_id": "backlog-42",
            "backlog_status": "blocked",
            "latest_task_id": "task-old",
        },
        generated_at="2026-04-13T21:10:00+00:00",
        request_json=fake_request_json,
    )

    assert execution["status"] == "dispatched"
    assert execution["dispatch_outcome"] == "success"
    assert execution["repair_reason"] == "stale_verification_block"
    assert execution["repair_status_code"] == 200
    assert execution["repaired_task_id"] == "task-old"
    assert execution["task_id"] == "task-new"
    assert execution["task_status"] == "scheduled"
    assert [entry[1] for entry in calls] == [
        "/v1/tasks/task-old",
        "/v1/operator/backlog?limit=200",
        "/v1/operator/backlog/backlog-42/transition",
        "/v1/operator/backlog/backlog-42/dispatch",
    ]
    assert calls[2][2]["status"] == "ready"
    assert "verification evidence" in str(calls[2][2]["note"]).lower()


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
    assert summary["feedback_scope"] == "ralph_loop"
    assert summary["last_outcome"] == "success"
    assert summary["last_success_at"] == "2026-04-13T12:03:00+00:00"
    assert summary["last_failure_at"] == "2026-04-13T12:01:00+00:00"
    assert summary["feedback_state"] == "healthy"


def test_automation_feedback_summary_uses_stream_scope_when_ralph_records_absent() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    recent_records = [
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

    assert summary["feedback_scope"] == "automation_stream"
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


def test_automation_feedback_summary_treats_already_dispatched_claims_as_non_failures() -> None:
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
            "status": "failure",
            "result": {
                "dispatch_outcome": "claimed",
                "dispatch_execution_status": "already_dispatched",
                "claimed_task_id": "workstream:capacity-and-harvest-truth",
                "claimed_task_title": "Capacity and Harvest Truth",
            },
            "operator_visible_summary": "Ralph loop retained the current claim without issuing a duplicate dispatch.",
        }
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0
    assert summary["feedback_state"] == "healthy"
    assert summary["dispatch_last_outcome"] == "claimed"


def test_automation_feedback_summary_treats_stale_dispatched_terminal_claims_as_failures() -> None:
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
                "dispatch_outcome": "failed",
                "dispatch_execution_status": "stale_dispatched_task",
                "dispatched_backlog_status": "scheduled",
                "dispatched_task_id": "task-old",
                "dispatched_task_status": "completed",
                "claimed_task_id": "workstream:validation-and-publication",
                "claimed_task_title": "Validation and Publication",
            },
            "operator_visible_summary": "Ralph loop found a stale scheduled backlog claim whose latest task already completed.",
        }
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["success_count"] == 0
    assert summary["failure_count"] == 1
    assert summary["feedback_state"] == "degraded"
    assert summary["dispatch_last_outcome"] == "failed"
    assert summary["recent_no_delta_task_ids"] == ["workstream:validation-and-publication"]


def test_automation_feedback_summary_treats_null_validation_idle_runs_as_neutral() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    recent_records = [
        {
            "timestamp": "2026-04-13T18:08:00+00:00",
            "automation_id": "ralph-loop",
            "lane": "ralph_loop",
            "action_class": "autonomous_planning",
            "result": {
                "dispatch_outcome": "idle",
                "dispatch_execution_status": "no_claim",
                "claimed_task_id": None,
                "validation_passed": None,
            },
            "operator_visible_summary": "Ralph loop correctly stayed idle because no claim was available.",
        },
        {
            "timestamp": "2026-04-13T18:05:00+00:00",
            "automation_id": "ralph-loop",
            "lane": "ralph_loop",
            "action_class": "autonomous_planning",
            "result": {
                "dispatch_outcome": "claimed",
                "dispatch_execution_status": "already_dispatched",
                "claimed_task_id": "workstream:capacity-and-harvest-truth",
                "claimed_task_title": "Capacity and Harvest Truth",
            },
            "operator_visible_summary": "Ralph loop retained the current claim without issuing a duplicate dispatch.",
        },
    ]

    summary = module._build_automation_feedback_summary(recent_records)

    assert summary["success_count"] == 1
    assert summary["failure_count"] == 0
    assert summary["unknown_count"] == 1
    assert summary["last_outcome"] == "unknown"
    assert summary["feedback_state"] == "healthy"


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
    assert aliases["selected_workstream_id"] == "dispatch-and-work-economy-closure"
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


def test_sync_registry_loop_state_avoids_timestamp_only_registry_rewrites(tmp_path) -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )
    original_config_dir = module.CONFIG_DIR
    module.CONFIG_DIR = tmp_path
    try:
        completion_program = {
            "ralph_loop": {
                "status": "active",
                "current_phase_scope": "phase-3",
                "controller_script": "scripts/run_ralph_loop_pass.py",
                "report_path": "reports/ralph-loop/latest.json",
                "current_loop_family": "governor_scheduling",
                "selected_workstream": "dispatch-and-work-economy-closure",
                "evidence_freshness": "fresh",
                "approval_status": "not_required",
                "blocker_type": "none",
                "next_action_family": "dispatch_truth_and_queue_replenishment",
                "last_validation_run": "2026-04-16T20:00:00+00:00",
                "execution_posture": "active_remediation",
            }
        }
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

        assert completion_program["ralph_loop"]["last_validation_run"] == "2026-04-16T20:00:00+00:00"
        assert not (tmp_path / "completion-program-registry.json").exists()
    finally:
        module.CONFIG_DIR = original_config_dir


def test_refresh_commands_cover_capacity_override_and_routing_evidence() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    assert [module.sys.executable, "scripts/collect_capacity_telemetry.py"] in module.REFRESH_COMMANDS
    assert [
        module.sys.executable,
        "scripts/manage_active_overrides.py",
        "expire",
        "--reason",
        "scheduled Ralph freshness sweep",
        "--actor",
        "Ralph",
        "--session-id",
        "ralph-loop",
    ] in module.REFRESH_COMMANDS
    assert [module.sys.executable, "scripts/run_full_stack_routing_proof.py"] in module.REFRESH_COMMANDS
    assert module.LOOP_FAMILY_NEXT_COMMANDS["evidence_refresh"] == module.REFRESH_COMMANDS


def test_validation_commands_refresh_steady_state_and_ecosystem_docs_before_validator() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    assert module.VALIDATION_COMMANDS[:11] == [
        [module.sys.executable, "scripts/write_steady_state_status.py", "--json"],
        [module.sys.executable, "scripts/generate_full_system_audit.py", "--skip-checks"],
        [module.sys.executable, "scripts/write_project_output_readiness.py", "--json"],
        [module.sys.executable, "scripts/write_project_output_candidates.py", "--json"],
        [module.sys.executable, "scripts/materialize_project_output_acceptance.py", "--all-pending", "--json"],
        [module.sys.executable, "scripts/write_project_output_candidates.py", "--json"],
        [module.sys.executable, "scripts/write_project_output_proof.py", "--json"],
        [module.sys.executable, "scripts/write_command_center_final_form_status.py", "--json"],
        [module.sys.executable, "scripts/generate_truth_inventory_reports.py"],
        [module.sys.executable, "scripts/generate_ecosystem_master_plan.py"],
        [module.sys.executable, "scripts/validate_platform_contract.py"],
    ]
    assert module.LOCAL_VALIDATION_COMMANDS[:13] == [
        [module.sys.executable, "scripts/write_steady_state_status.py", "--json"],
        [module.sys.executable, "scripts/generate_full_system_audit.py", "--skip-checks"],
        [module.sys.executable, "scripts/write_project_output_readiness.py", "--json"],
        [module.sys.executable, "scripts/write_project_output_candidates.py", "--json"],
        [module.sys.executable, "scripts/materialize_project_output_acceptance.py", "--all-pending", "--json"],
        [module.sys.executable, "scripts/write_project_output_candidates.py", "--json"],
        [module.sys.executable, "scripts/write_project_output_proof.py", "--json"],
        [module.sys.executable, "scripts/write_command_center_final_form_status.py", "--json"],
        [module.sys.executable, "scripts/generate_truth_inventory_reports.py"],
        [module.sys.executable, "scripts/triage_publication_tranche.py", "--write", "docs/operations/PUBLICATION-TRIAGE-REPORT.md"],
        [module.sys.executable, "scripts/generate_publication_deferred_family_queue.py"],
        [module.sys.executable, "scripts/generate_ecosystem_master_plan.py"],
        [module.sys.executable, "scripts/validate_platform_contract.py"],
    ]


def test_workstream_scoped_repo_delta_reopen_keeps_dispatch_closed_on_unrelated_churn() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    continuity_policy = {
        "workstream_continuity": {
            "dispatch-and-work-economy-closure": {
                "reopen_scope": {
                    "reason_scope": "dispatch_evidence_chain_only",
                    "repo_delta_prefixes": [
                        "scripts/run_ralph_loop_pass.py",
                        "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                    ],
                }
            },
            "validation-and-publication": {
                "reopen_scope": {
                    "reason_scope": "material_repo_delta_any",
                    "repo_delta_prefixes": [],
                }
            },
        }
    }
    repo_delta_paths = ["docs/operations/PUBLICATION-TRIAGE-REPORT.md"]
    dispatch_detail = module._continuity_repo_delta_reopen_detail(
        {
            "task_id": "workstream:dispatch-and-work-economy-closure",
            "source_type": "workstream",
            "workstream_id": "dispatch-and-work-economy-closure",
        },
        enabled=True,
        continuity_policy=continuity_policy,
        repo_delta_paths=repo_delta_paths,
    )
    validation_detail = module._continuity_repo_delta_reopen_detail(
        {
            "task_id": "workstream:validation-and-publication",
            "source_type": "workstream",
            "workstream_id": "validation-and-publication",
        },
        enabled=True,
        continuity_policy=continuity_policy,
        repo_delta_paths=repo_delta_paths,
    )

    assert dispatch_detail["reopened"] is False
    assert dispatch_detail["reopen_reason_scope"] == "dispatch_evidence_chain_only"
    assert validation_detail["reopened"] is True
    assert validation_detail["reopen_reason_scope"] == "material_repo_delta_any"


def test_dispatch_repo_side_no_delta_marks_rotation_ready_with_green_evidence() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    continuity_policy = {
        "workstream_continuity": {
            "dispatch-and-work-economy-closure": {
                "no_delta_closure_criteria": {
                    "required_evidence_refs": [
                        "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                        "reports/truth-inventory/capacity-telemetry.json",
                        "reports/truth-inventory/quota-truth.json",
                    ],
                    "summary": "Dispatch closure is green.",
                },
                "reopen_scope": {
                    "reason_scope": "dispatch_evidence_chain_only",
                    "repo_delta_prefixes": ["scripts/run_ralph_loop_pass.py"],
                },
            }
        }
    }
    original_loader = module._load_optional_repo_json
    module._load_optional_repo_json = lambda _path: {
        "summary": {
            "baseline_alignment_status": "passed",
            "capacity_truth_alignment_status": "passed",
            "formal_eval_ready": True,
        }
    }
    try:
        detail = module._workstream_repo_side_no_delta_detail(
            {
                "task_id": "workstream:dispatch-and-work-economy-closure",
                "source_type": "workstream",
                "workstream_id": "dispatch-and-work-economy-closure",
            },
            continuity_policy,
            [],
            {
                "records": [
                    {
                        "degraded_reason": None,
                    }
                ]
            },
            {
                "capacity_summary": {
                    "scheduler_slot_count": 5,
                    "sample_posture": "scheduler_projection_backed",
                }
            },
        )
    finally:
        module._load_optional_repo_json = original_loader

    assert detail["repo_side_no_delta"] is True
    assert detail["rotation_ready"] is True
    assert detail["no_delta_evidence_refs"] == [
        "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
        "reports/truth-inventory/capacity-telemetry.json",
        "reports/truth-inventory/quota-truth.json",
    ]



def test_build_executive_brief_adds_burn_class_preflight_guidance() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    report = {
        "stop_state": "none",
        "stop_reason": None,
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "active_claim_rotation_reason": "recent_no_delta_suppressed",
        "repo_side_no_delta": False,
        "rotation_ready": False,
        "reopen_reason_scope": "material_repo_delta_any",
        "no_delta_evidence_refs": ["reports/truth-inventory/latest.json"],
        "selected_workstream": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "loop_mode": "governor_scheduling",
        "next_action_family": "dispatch_truth_and_queue_replenishment",
        "execution_posture": "steady_state",
        "continue_allowed": True,
        "dispatch_status": "already_dispatched",
        "provider_gate_state": "completed",
        "work_economy_status": "ready",
        "validation_summary": "4/4 validation checks passed.",
        "validation_checks": [{"status": "passed"}] * 4,
        "autonomous_queue_summary": {
            "blocked_queue_count": 0,
            "dispatchable_queue_count": 7,
            "suppressed_queue_count": 2,
        },
        "advisory_blockers": [],
        "governed_dispatch_state": {
            "execution": {"status": "already_dispatched", "ready": True},
            "claim": {
                "current_task_id": "workstream:validation-and-publication",
                "current_task_title": "Validation and Publication",
                "current_lane_family": "validation_and_checkpoint",
                "claim_rotation_reason": "recent_no_delta_suppressed",
            },
        },
        "publication_debt_status": {},
        "next_unblocked_candidate": {
            "task_id": "burn_class:local_bulk_sovereign",
            "title": "Local Bulk Sovereign",
            "preferred_lane_family": "capacity_truth_repair",
            "source_type": "burn_class",
        },
    }
    continuity_policy = {
        "executive_reporting": {
            "required_sections": [
                "program_state",
                "landed_or_delta",
                "proof",
                "risks",
                "delegation",
                "next_moves",
                "decision_needed",
            ],
            "required_trigger_points": ["material_tranche_landed"],
            "use_active_claim_for_current_task": True,
        }
    }

    brief = module._build_executive_brief(report, continuity_policy)

    assert any(
        "preflight_burn_class.py local_bulk_sovereign --json" in item
        for item in brief["delegation"]["delegate_now"]
    )
    assert any(
        "burn_class:local_bulk_sovereign" in item and "preflight_burn_class.py local_bulk_sovereign --json" in item
        for item in brief["next_moves"]
    )


def test_build_executive_brief_prefers_execution_dispatch_outcome_over_claim() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    brief = module._build_executive_brief(
        {
            "active_claim_task_id": "workstream:validation-and-publication",
            "active_claim_task_title": "Validation and Publication",
            "selected_workstream": "dispatch-and-work-economy-closure",
            "selected_workstream_title": "Dispatch and Work-Economy Closure",
            "continue_allowed": True,
            "repo_side_no_delta": False,
            "rotation_ready": False,
            "dispatch_authority": {
                "governed_dispatch_execution": {
                    "status": "stale_dispatched_task",
                    "dispatch_outcome": "failed",
                }
            },
            "governed_dispatch_claim": {
                "current_task_id": "workstream:validation-and-publication",
                "current_task_title": "Validation and Publication",
                "dispatch_outcome": "claimed",
            },
            "autonomous_queue_summary": {
                "blocked_queue_count": 0,
                "dispatchable_queue_count": 2,
                "suppressed_queue_count": 0,
            },
            "validation": {"ran": False, "results": [], "all_passed": None},
        },
        {"executive_reporting_contract": {}},
    )

    assert brief["landed_or_delta"]["dispatch_status"] == "stale_dispatched_task"
    assert brief["landed_or_delta"]["dispatch_outcome"] == "failed"


def test_build_ranked_autonomous_queue_keeps_cash_now_deferred_family_ahead_of_burn_class_during_validation() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    workstream_rows = [
        {
            "workstream": {
                "id": "validation-and-publication",
                "title": "Validation and Publication",
                "status": "continuous",
                "execution_state": "ready_for_execution",
                "loop_family": "publication_freeze",
                "next_action_family": "validation_and_checkpoint",
                "approval_required": False,
            },
            "dependency_state": "ready",
            "evidence_state": {"state": "fresh"},
        }
    ]
    burn_registry = {
        "dispatch_policy": {
            "ranked_dispatch_enabled": True,
            "approved_mutation_classes": ["auto_harvest"],
            "approved_work_classes": ["repo_safe_implementation"],
        },
        "providers": {"athanor_local": {"enabled": True}},
        "burn_classes": [
            {"id": "local_bulk_sovereign", "routing_chain": ["athanor_local"]},
        ],
    }
    work_economy_detail = {
        "status": "compounding_ready",
        "harvest_ready": True,
        "provider_availability": {"athanor_local": {"enabled": True, "label": "Athanor Local"}},
        "eligible_burn_class_ids": ["local_bulk_sovereign"],
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
    publication_queue = {
        "families": [
            {
                "id": "reference-and-archive-prune",
                "title": "Reference and Archive Prune",
                "execution_class": "cash_now",
                "execution_rank": 1,
                "match_count": 34,
                "next_action": "Prune reference debt.",
            }
        ],
        "next_recommended_family": {
            "id": "reference-and-archive-prune",
            "title": "Reference and Archive Prune",
        },
    }

    rows = module._build_ranked_autonomous_queue(
        queue={"items": []},
        workstream_rows=workstream_rows,
        completion_program={
            "continuity_policy": {
                "cash_now_deferred_families_are_autonomous_inputs": True,
                "cash_now_requires_no_unsuppressed_workstream": True,
                "feeder_precedence": [
                    "workstream",
                    "cash_now_deferred_family",
                    "burn_class",
                    "safe_surface",
                    "provider_gate",
                ],
            }
        },
        burn_registry=burn_registry,
        work_economy_detail=work_economy_detail,
        provider_gate_detail={"blocking_provider_count": 0},
        quota_truth=quota_truth,
        publication_queue=publication_queue,
        continuity_state={"recent_no_delta_task_ids": [], "next_unblocked_candidate": {}},
        capacity_telemetry=None,
    )

    task_ids = [row["task_id"] for row in rows]
    assert "workstream:validation-and-publication" in task_ids
    assert "deferred_family:reference-and-archive-prune" in task_ids
    assert "burn_class:local_bulk_sovereign" in task_ids
    assert task_ids.index("deferred_family:reference-and-archive-prune") < task_ids.index("burn_class:local_bulk_sovereign")


def test_build_publication_deferred_family_items_marks_zero_match_family_non_dispatchable() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    rows = module._build_publication_deferred_family_items(
        {
            "families": [
                {
                    "id": "reference-and-archive-prune",
                    "title": "Reference and Archive Prune",
                    "execution_class": "cash_now",
                    "execution_rank": 1,
                    "match_count": 0,
                    "next_action": "Prune reference debt.",
                    "path_hints": ["docs/archive/"],
                    "sample_paths": [],
                }
            ]
        }
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["task_id"] == "deferred_family:reference-and-archive-prune"
    assert row["dispatchable"] is False
    assert row["status"] == "deferred_no_delta"
    assert row["blocking_reason"] == "no_repo_delta"
    assert row["repo_side_no_delta"] is True
    assert "no matched repo paths" in row["no_delta_summary"]



def test_build_capability_adoption_items_exposes_proved_builder_rollout() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    rows = module._build_capability_adoption_items(
        {
            "capabilities": [
                {
                    "id": "protocol-first-builder-kernel",
                    "label": "Protocol-First Builder Kernel",
                    "authority_class": "build_system",
                    "stage": "proved",
                    "release_tier": "shadow",
                    "next_release_tier_on_green": "shadow",
                    "runtime_packet_ids": ["dev-dashboard-compose-deploy-packet"],
                    "runtime_target": "Athanor builder front door",
                    "source_repo": "C:/athanor-devstack",
                    "proof_artifacts": [
                        "C:/Athanor/reports/truth-inventory/protocol-first-builder-kernel-formal-eval.json"
                    ],
                    "notes": [
                        "Carry the linked builder proof through operator packet review and an explicit dashboard deploy decision before any wider builder takeover or release-tier advance."
                    ],
                }
            ]
        },
        {
            "packets": [
                {
                    "id": "dev-dashboard-compose-deploy-packet",
                    "status": "executed",
                }
            ]
        },
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["task_id"] == "capability:protocol-first-builder-kernel"
    assert row["dispatchable"] is True
    assert row["preferred_lane_family"] == "promotion_wave_closure"
    assert row["approved_mutation_class"] == "auto_read_only"
    assert row["runtime_packet_ids"] == ["dev-dashboard-compose-deploy-packet"]


def test_build_capability_adoption_items_surfaces_concept_pilot_blockers() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    rows = module._build_capability_adoption_items(
        {
            "capabilities": [
                {
                    "id": "letta-memory-plane",
                    "label": "Letta Memory Plane",
                    "authority_class": "build_system",
                    "stage": "concept",
                    "pilot_blocker_class": "env_wiring",
                    "release_tier": "offline_eval",
                    "runtime_target": "Athanor memory plane",
                    "proof_artifacts": ["C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md"],
                    "notes": ["Letta needs explicit env wiring before the lane can reopen."],
                },
                {
                    "id": "agent-governance-toolkit-policy-plane",
                    "label": "Agent Governance Toolkit Policy Plane",
                    "authority_class": "build_system",
                    "stage": "concept",
                    "pilot_blocker_class": "non_duplicative_value_unproven",
                    "release_tier": "offline_eval",
                    "runtime_target": "Athanor protocol policy plane",
                    "proof_artifacts": ["C:/Athanor/reports/truth-inventory/agt-policy-plane-formal-eval.json"],
                    "source_safe_remaining": [
                        "Only reopen this lane if a second protocol-boundary scenario shows non-duplicative value over the native approval matrix without widening permissions."
                    ],
                    "notes": ["AGT still needs non-duplicative value proof."],
                },
            ]
        },
        {"packets": []},
    )

    by_id = {row["task_id"]: row for row in rows}
    letta = by_id["capability:letta-memory-plane"]
    assert letta["dispatchable"] is False
    assert letta["blocking_reason"] == "external_dependency_blocked"
    assert letta["pilot_blocker_class"] == "env_wiring"
    assert letta["status"] == "blocked_env_wiring"

    agt = by_id["capability:agent-governance-toolkit-policy-plane"]
    assert agt["dispatchable"] is False
    assert agt["blocking_reason"] == "proof_required"
    assert agt["pilot_blocker_class"] == "non_duplicative_value_unproven"
    assert agt["status"] == "blocked_proof_required"


def test_build_ranked_autonomous_queue_prioritizes_proved_capability_over_zero_match_deferred_family() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    rows = module._build_ranked_autonomous_queue(
        queue={"items": []},
        workstream_rows=[],
        completion_program={
            "continuity_policy": {
                "cash_now_deferred_families_are_autonomous_inputs": True,
                "cash_now_requires_no_unsuppressed_workstream": True,
                "feeder_precedence": [
                    "workstream",
                    "cash_now_deferred_family",
                    "burn_class",
                    "safe_surface",
                    "provider_gate",
                ],
            }
        },
        burn_registry={"burn_classes": []},
        work_economy_detail={"records": [], "provider_availability": {}},
        provider_gate_detail={"blocking_provider_count": 0},
        quota_truth={"records": []},
        publication_queue={
            "families": [
                {
                    "id": "reference-and-archive-prune",
                    "title": "Reference and Archive Prune",
                    "execution_class": "cash_now",
                    "execution_rank": 1,
                    "match_count": 0,
                }
            ]
        },
        continuity_state={"recent_no_delta_task_ids": [], "next_unblocked_candidate": {}},
        capacity_telemetry=None,
        capability_registry={
            "capabilities": [
                {
                    "id": "protocol-first-builder-kernel",
                    "label": "Protocol-First Builder Kernel",
                    "authority_class": "build_system",
                    "stage": "proved",
                    "release_tier": "shadow",
                    "next_release_tier_on_green": "shadow",
                    "runtime_packet_ids": ["dev-dashboard-compose-deploy-packet"],
                    "runtime_target": "Athanor builder front door",
                    "source_repo": "C:/athanor-devstack",
                    "proof_artifacts": [
                        "C:/Athanor/reports/truth-inventory/protocol-first-builder-kernel-formal-eval.json"
                    ],
                    "notes": [
                        "Carry the linked builder proof through operator packet review and an explicit dashboard deploy decision before any wider builder takeover or release-tier advance."
                    ],
                }
            ]
        },
        runtime_packets_payload={
            "packets": [
                {
                    "id": "dev-dashboard-compose-deploy-packet",
                    "status": "executed",
                }
            ]
        },
    )

    assert rows[0]["task_id"] == "capability:protocol-first-builder-kernel"
    assert rows[1]["task_id"] == "deferred_family:reference-and-archive-prune"



def test_build_loop_continuity_status_prefers_typed_proof_required_brake() -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    payload = module._build_loop_continuity_status(
        ranked_autonomous_queue=[
            {
                "task_id": "capability:agent-governance-toolkit-policy-plane",
                "title": "Agent Governance Toolkit Policy Plane",
                "dispatchable": False,
                "suppressed_by_continuity": False,
                "blocking_reason": "proof_required",
                "pilot_blocker_class": "non_duplicative_value_unproven",
            }
        ],
        governed_dispatch_claim={},
        publication_next_family={},
    )

    assert payload["continue_allowed"] is False
    assert payload["stop_state"] == "proof_required"
    assert "non-duplicative proof slice" in str(payload["stop_reason"])
