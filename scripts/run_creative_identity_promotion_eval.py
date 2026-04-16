#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry, resolve_external_path


RUN_ID = "creative-identity-pipeline-refusal-sovereignty-2026q1"
EVAL_LEDGER_PATH = REPO_ROOT / "config" / "automation-backbone" / "eval-run-ledger.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "creative-identity-promotion-eval.json"
DEVSTACK_BASELINE_REPORT = resolve_external_path(
    "C:/athanor-devstack/reports/creative-identity/creative-identity-i2v-baseline-latest.json"
)
DEVSTACK_ANALYSIS_REPORT = resolve_external_path(
    "C:/athanor-devstack/reports/creative-identity/creative-identity-i2v-analysis-latest.json"
)
DEVSTACK_MANIFEST_PATH = resolve_external_path("C:/athanor-devstack/shipped/MANIFEST.md")
DEVSTACK_PACKET_PATH = resolve_external_path("C:/athanor-devstack/docs/promotion-packets/creative-identity-pipeline.md")
DEVSTACK_GENERATOR_PATH = resolve_external_path("C:/athanor-devstack/scripts/generate-kayla-i2v-test.py")
DEVSTACK_ANALYZER_PATH = resolve_external_path("C:/athanor-devstack/scripts/analyze-creative-identity-baseline.py")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    dump_json(path, payload)


def _find_run(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    for run in payload.get("runs", []):
        if str(run.get("run_id") or "").strip() == run_id:
            return run
    raise SystemExit(f"Run id not found in eval-run-ledger.json: {run_id}")


def _project_record(projects: dict[str, Any], project_id: str) -> dict[str, Any]:
    for project in projects.get("projects", []):
        if str(project.get("id") or "").strip() == project_id:
            return dict(project)
    return {}


def main() -> int:
    now = iso_now()
    eval_payload = _load_json(EVAL_LEDGER_PATH)
    run = _find_run(eval_payload, RUN_ID)
    project_packets = load_registry("project-packet-registry.json")
    project = _project_record(project_packets, "eoq")
    baseline = _load_json(DEVSTACK_BASELINE_REPORT)
    analysis = _load_json(DEVSTACK_ANALYSIS_REPORT)
    manifest_text = DEVSTACK_MANIFEST_PATH.read_text(encoding="utf-8")

    artifact_path = resolve_external_path(analysis.get("artifact_path"))
    contact_sheet_path = resolve_external_path(analysis.get("contact_sheet_path"))
    artifact_repo_relative = None
    try:
        artifact_repo_relative = artifact_path.relative_to(resolve_external_path("C:/athanor-devstack")).as_posix()
    except ValueError:
        artifact_repo_relative = None
    manifest_links_artifact = any(
        token and token in manifest_text
        for token in (
            str(analysis.get("artifact_path") or "").strip(),
            artifact_repo_relative,
            artifact_path.name,
        )
    )
    baseline_completed = str(baseline.get("status") or "").strip() == "completed"
    latest_run_matches = str(baseline.get("run_id") or "").strip() == str(analysis.get("run_id") or "").strip()
    policy_class = str(run.get("judge_config", {}).get("policy_class") or "").strip()
    project_routing_class = str(project.get("routing_class") or "").strip()

    checks = {
        "baseline_report_completed": baseline_completed,
        "analysis_report_present": str(analysis.get("status") or "").strip() in {"blocked", "passed"},
        "artifact_exists": artifact_path.exists(),
        "contact_sheet_exists": contact_sheet_path.exists(),
        "latest_run_consistent": latest_run_matches,
        "manifest_references_artifact": manifest_links_artifact,
        "policy_class_sovereign_only": policy_class == "sovereign_only",
        "eoq_project_routing_sovereign_only": project_routing_class == "sovereign_only",
        "technical_visibility_review_passed": str(analysis.get("status") or "").strip() == "passed",
    }
    blocking_reasons = [name for name, passed in checks.items() if not passed]
    promotion_validity = "valid" if not blocking_reasons else "requires_formal_eval_run"
    overall_status = "passed" if not blocking_reasons else "blocked"

    summary = (
        "Creative identity baseline is sovereignty-safe, manifest-disciplined, and technically visible enough to support packet progression."
        if overall_status == "passed"
        else "Creative identity promotion remains blocked because the baseline artifact is not yet technically strong enough for packet progression."
    )

    report = {
        "version": "2026-04-15.1",
        "generated_at": now,
        "source_of_truth": "reports/truth-inventory/creative-identity-promotion-eval.json",
        "initiative_id": "creative-identity-pipeline",
        "run_id": RUN_ID,
        "promotion_eval_status": overall_status,
        "promotion_validity": promotion_validity,
        "blocking_reasons": blocking_reasons,
        "checks": checks,
        "baseline_report_path": str(DEVSTACK_BASELINE_REPORT).replace('\\', '/'),
        "analysis_report_path": str(DEVSTACK_ANALYSIS_REPORT).replace('\\', '/'),
        "packet_path": str(DEVSTACK_PACKET_PATH).replace('\\', '/'),
        "artifact_path": str(analysis.get("artifact_path") or ""),
        "contact_sheet_path": str(analysis.get("contact_sheet_path") or ""),
        "analysis_summary": str(analysis.get("summary") or ""),
        "summary": summary,
    }
    _write_json(OUTPUT_PATH, report)

    evidence_artifacts = [str(item) for item in run.get("evidence_artifacts", []) if str(item).strip()]
    for artifact in (
        str(DEVSTACK_GENERATOR_PATH).replace('\\', '/'),
        str(DEVSTACK_ANALYZER_PATH).replace('\\', '/'),
        str(DEVSTACK_BASELINE_REPORT).replace('\\', '/'),
        str(DEVSTACK_ANALYSIS_REPORT).replace('\\', '/'),
        str(contact_sheet_path).replace('\\', '/'),
        str(OUTPUT_PATH).replace('\\', '/'),
    ):
        if artifact not in evidence_artifacts:
            evidence_artifacts.append(artifact)

    notes = [str(item) for item in run.get("notes", []) if str(item).strip()]
    notes.insert(
        0,
        "Formal creative eval now inspects the shipped I2V baseline, verifies manifest discipline plus sovereign routing, and blocks packet progression when the generated clip is technically too dark to review.",
    )
    notes.append(f"{now}: {summary}")

    run["evidence_artifacts"] = evidence_artifacts
    run["formal_eval_artifact_path"] = str(OUTPUT_PATH).replace('\\', '/')
    run["last_run_at"] = now
    run["notes"] = notes
    run["promotion_validity"] = promotion_validity
    run["source_safe_remaining"] = [
        "Keep the creative lane in devstack until a visibly reviewable I2V baseline exists and the packet can advance without widening into Athanor runtime surfaces."
    ]
    run["status"] = "completed"
    run["task_class"] = "creative_visibility_boundary_eval"
    run["wrapper_mode"] = "artifact_review"

    eval_payload["updated_at"] = now
    eval_payload["version"] = "2026-04-15.3"
    _write_json(EVAL_LEDGER_PATH, eval_payload)

    append_history(
        "capability-promotion-evals",
        {
            "generated_at": now,
            "initiative_id": "creative-identity-pipeline",
            "run_id": RUN_ID,
            "promotion_eval_status": overall_status,
            "promotion_validity": promotion_validity,
            "blocking_reasons": blocking_reasons,
            "artifact_path": str(OUTPUT_PATH).replace('\\', '/'),
        },
    )
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
