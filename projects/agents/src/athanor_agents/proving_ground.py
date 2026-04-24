from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .model_governance import (
    get_eval_corpus_registry,
    get_experiment_ledger_policy,
    get_model_proving_ground,
    get_model_role_registry,
)
from .promotion_control import build_promotion_controls_snapshot
from .self_improvement import get_improvement_engine


async def build_proving_ground_snapshot(limit: int = 12) -> dict[str, Any]:
    registry = get_model_proving_ground()
    eval_corpus_registry = get_eval_corpus_registry()
    experiment_policy = get_experiment_ledger_policy()
    role_registry = get_model_role_registry()
    engine = get_improvement_engine()
    await engine.load()
    summary = await engine.get_improvement_summary()

    recent_results = [asdict(result) for result in engine.benchmarks.results[-limit:]]
    recent_results.reverse()

    latest_run = None
    if summary.get("last_cycle"):
        latest_run = {
            "timestamp": summary["last_cycle"].get("timestamp"),
            "passed": summary["last_cycle"].get("benchmarks", {}).get("passed", 0),
            "total": summary["last_cycle"].get("benchmarks", {}).get("total", 0),
            "pass_rate": summary["last_cycle"].get("benchmarks", {}).get("pass_rate", 0.0),
            "patterns_consumed": summary["last_cycle"].get("patterns_consumed", 0),
            "proposals_generated": summary["last_cycle"].get("proposals_generated", 0),
            "backlog_items_created": summary["last_cycle"].get("backlog_items_created", 0),
            "backlog_items_refreshed": summary["last_cycle"].get("backlog_items_refreshed", 0),
            "backlog_ids": list(summary["last_cycle"].get("backlog_ids", [])),
            "review_ids": list(summary["last_cycle"].get("review_ids", [])),
            "execution_plane": summary["last_cycle"].get("execution_plane"),
            "admission_classification": summary["last_cycle"].get("admission_classification"),
            "admission_reason": summary["last_cycle"].get("admission_reason"),
            "errors": summary["last_cycle"].get("errors", []),
            "source": "improvement_cycle",
        }
    elif recent_results:
        latest = recent_results[0]
        passed = sum(1 for entry in recent_results if entry.get("passed"))
        total = len(recent_results)
        latest_run = {
            "timestamp": latest.get("timestamp"),
            "passed": passed,
            "total": total,
            "pass_rate": (passed / total) if total else 0.0,
            "patterns_consumed": 0,
            "proposals_generated": 0,
            "errors": [],
            "source": "benchmark_history",
        }

    lane_coverage = [
        {
            "role_id": role["id"],
            "label": role["label"],
            "plane": role["plane"],
            "status": role["status"],
            "champion": role["champion"],
            "challenger_count": len(role.get("challengers", [])),
            "workload_count": len(role.get("workload_classes", [])),
        }
        for role in role_registry.get("roles", [])
    ]
    recent_experiments = [
        {
            "id": str(result.get("benchmark_id") or f"experiment-{index + 1}"),
            "name": str(result.get("name") or result.get("benchmark_id") or "benchmark"),
            "category": str(result.get("category") or "benchmark"),
            "passed": bool(result.get("passed")),
            "score": float(result.get("score", 0.0) or 0.0),
            "max_score": float(result.get("max_score", 0.0) or 0.0),
            "timestamp": result.get("timestamp"),
        }
        for index, result in enumerate(recent_results[:8])
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": registry.get("version", "unknown"),
        "status": "live" if recent_results else registry.get("status", "implemented_not_live"),
        "purpose": registry.get("purpose", ""),
        "evaluation_dimensions": registry.get("evaluation_dimensions", []),
        "corpora": registry.get("corpora", []),
        "pipeline_phases": registry.get("pipeline_phases", []),
        "promotion_path": registry.get("promotion_path", []),
        "rollback_rule": registry.get("rollback_rule", ""),
        "corpus_registry_version": eval_corpus_registry.get("version", "unknown"),
        "governed_corpora": list(eval_corpus_registry.get("corpora", [])),
        "experiment_ledger": {
            "version": experiment_policy.get("version", "unknown"),
            "status": "live_partial" if recent_experiments else experiment_policy.get("status", "configured"),
            "required_fields": list(experiment_policy.get("required_fields", [])),
            "retention": str(experiment_policy.get("retention") or "unknown"),
            "promotion_linkage": str(experiment_policy.get("promotion_linkage") or ""),
            "evidence_count": len(recent_experiments),
        },
        "latest_run": latest_run,
        "recent_results": recent_results,
        "recent_experiments": recent_experiments,
        "improvement_summary": summary,
        "lane_coverage": lane_coverage,
        "promotion_controls": await build_promotion_controls_snapshot(limit=limit),
    }


async def run_proving_ground(limit: int = 12) -> dict[str, Any]:
    engine = get_improvement_engine()
    await engine.load()
    benchmark_summary = await engine.run_benchmark_suite()
    snapshot = await build_proving_ground_snapshot(limit=limit)
    snapshot["latest_benchmark_run"] = benchmark_summary
    snapshot["status"] = "live"
    return snapshot
