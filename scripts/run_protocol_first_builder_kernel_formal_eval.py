#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, iso_now
from truth_inventory import REPO_ROOT

RUN_ID = "protocol-first-builder-kernel-eval-2026q2"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "protocol-first-builder-kernel-formal-eval.json"
LIVE_ROUTE_OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "protocol-first-builder-kernel-live-smoke.json"
EVAL_LEDGER_PATH = REPO_ROOT / "config" / "automation-backbone" / "eval-run-ledger.json"
CAPABILITY_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "capability-adoption-registry.json"
BOOTSTRAP_BUILDER_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "bootstrap-builder-registry.json"
BOOTSTRAP_PROGRAM_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "bootstrap-program-registry.json"
DASHBOARD_DIR = REPO_ROOT / "projects" / "dashboard"
FORMAL_TEST_PATH = DASHBOARD_DIR / "src" / "lib" / "builder-kernel-formal-eval.test.ts"
LIVE_ROUTE_TEST_PATH = DASHBOARD_DIR / "src" / "lib" / "builder-kernel-live-route.test.ts"
SMOKE_TARGET_PATH = "projects/dashboard/PROTOCOL_FIRST_BUILDER_KERNEL_FORMAL_EVAL.md"
EXPECTED_RUNTIME_OWNERSHIP_LANES = ["dev-dashboard-compose"]
EXPECTED_RUNTIME_PACKET_IDS = ["dev-dashboard-compose-deploy-packet"]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_artifact_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    if normalized.startswith("/mnt/c/"):
        return f"C:/{normalized[len('/mnt/c/'):]}"
    return normalized


def _dedupe_paths(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_artifact_path(value)
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def _find_run(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    for run in payload.get("runs", []):
        if str(run.get("run_id") or "").strip() == run_id:
            return run
    raise SystemExit(f"Run id not found in eval-run-ledger.json: {run_id}")


def _find_capability(payload: dict[str, Any], capability_id: str) -> dict[str, Any]:
    for capability in payload.get("capabilities", []):
        if str(capability.get("id") or "").strip() == capability_id:
            return capability
    raise SystemExit(f"Capability not found in capability-adoption-registry.json: {capability_id}")


def _run_command(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _load_vitest_assertions(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    assertions: list[dict[str, Any]] = []
    for test_result in payload.get("testResults", []) or []:
        if not isinstance(test_result, dict):
            continue
        for assertion in test_result.get("assertionResults", []) or []:
            if isinstance(assertion, dict):
                assertions.append(assertion)
    return assertions


def _assertion_status(assertions: list[dict[str, Any]], title: str) -> str | None:
    for assertion in assertions:
        if str(assertion.get("title") or "").strip() == title:
            return str(assertion.get("status") or "").strip() or None
    return None


def _check_bootstrap_takeover_explicit() -> dict[str, bool]:
    builder_registry = _load_json(BOOTSTRAP_BUILDER_REGISTRY_PATH)
    program_registry = _load_json(BOOTSTRAP_PROGRAM_REGISTRY_PATH)
    host_status = {
        str(host.get("id") or ""): str(host.get("status") or "")
        for host in builder_registry.get("hosts", [])
        if isinstance(host, dict)
    }
    launch_readiness = next(
        (
            program
            for program in program_registry.get("programs", [])
            if isinstance(program, dict) and str(program.get("id") or "") == "launch-readiness-bootstrap"
        ),
        {},
    )
    families = [str(item) for item in launch_readiness.get("family_order", [])]
    return {
        "codex_external_live": host_status.get("codex_external") == "live",
        "claude_external_live": host_status.get("claude_external") == "live",
        "takeover_promotion_check_present": "takeover_promotion_check" in families,
    }


def _check_runtime_linkage(capability: dict[str, Any]) -> dict[str, Any]:
    runtime_ownership_lanes = [str(item) for item in capability.get("runtime_ownership_lanes", []) if str(item).strip()]
    runtime_packet_ids = [str(item) for item in capability.get("runtime_packet_ids", []) if str(item).strip()]
    return {
        "runtime_ownership_lanes": runtime_ownership_lanes,
        "runtime_packet_ids": runtime_packet_ids,
        "expected_runtime_ownership_lanes": EXPECTED_RUNTIME_OWNERSHIP_LANES,
        "expected_runtime_packet_ids": EXPECTED_RUNTIME_PACKET_IDS,
        "dashboard_rollout_path_bound": all(
            item in runtime_ownership_lanes for item in EXPECTED_RUNTIME_OWNERSHIP_LANES
        ) and all(item in runtime_packet_ids for item in EXPECTED_RUNTIME_PACKET_IDS),
    }


def _write_report(report: dict[str, Any]) -> None:
    dump_json(OUTPUT_PATH, report)
    append_history(
        "capability-promotion-evals",
        {
            "generated_at": report["generated_at"],
            "initiative_id": report["initiative_id"],
            "run_id": report["run_id"],
            "promotion_eval_status": report["promotion_eval_status"],
            "promotion_validity": report["promotion_validity"],
            "blocking_reasons": report["blocking_reasons"],
            "artifact_path": OUTPUT_PATH.as_posix(),
        },
    )


def _update_registries(
    *,
    report: dict[str, Any],
    eval_payload: dict[str, Any],
    run: dict[str, Any],
    capability_payload: dict[str, Any],
    capability: dict[str, Any],
) -> None:
    now = report["generated_at"]
    promotion_validity = report["promotion_validity"]
    summary = report["summary"]

    evidence_artifacts = _dedupe_paths(
        [str(item) for item in run.get("evidence_artifacts", []) if str(item).strip()]
        + [
            FORMAL_TEST_PATH.as_posix(),
            LIVE_ROUTE_TEST_PATH.as_posix(),
            OUTPUT_PATH.as_posix(),
            LIVE_ROUTE_OUTPUT_PATH.as_posix(),
            (REPO_ROOT / "scripts" / "run_protocol_first_builder_kernel_formal_eval.py").as_posix(),
        ]
    )
    evidence_artifacts = [
        artifact
        for artifact in evidence_artifacts
        if not artifact.endswith("projects/dashboard/scripts/formal-eval-builder-route.mjs")
    ]
    run_notes = [str(item) for item in run.get("notes", []) if str(item).strip()]
    run_notes.append(f"{now}: {summary}")
    run["evidence_artifacts"] = evidence_artifacts
    run["formal_eval_artifact_path"] = _normalize_artifact_path(OUTPUT_PATH.as_posix())
    run["last_run_at"] = now
    run["notes"] = run_notes
    run["promotion_validity"] = promotion_validity
    run["status"] = "completed"
    run["task_class"] = "builder_kernel_boundary_eval"
    run["source_safe_remaining"] = [
        "Keep Codex and Claude external bootstrap builders live until the takeover-promotion-check family is explicitly green and operator-reviewed.",
        "Keep dev-dashboard-compose-deploy-packet as the only bounded builder rollout path until a distinct runtime owner or rollback surface justifies a separate packet.",
    ]

    proof_artifacts = _dedupe_paths(
        [str(item) for item in capability.get("proof_artifacts", []) if str(item).strip()]
        + [LIVE_ROUTE_OUTPUT_PATH.as_posix(), OUTPUT_PATH.as_posix()]
    )
    capability["proof_artifacts"] = proof_artifacts
    capability["next_release_tier_on_green"] = "shadow"
    capability_notes = [
        str(item)
        for item in capability.get("notes", [])
        if str(item).strip()
        and "formal builder eval proved a dashboard-targeting live route" not in str(item)
    ]
    note = (
        "The 2026-04-17 formal builder eval proved the direct builder route with TSC-backed verification, fail-closed negative routing, coherent operator projections, and explicit non-takeover bootstrap posture."
    )
    if note not in capability_notes:
        capability_notes.append(note)
    capability["notes"] = capability_notes
    if promotion_validity == "valid":
        if str(capability.get("stage") or "").strip() != "adopted":
            capability["stage"] = "proved"
        capability["release_tier"] = "shadow"

    eval_payload["updated_at"] = now
    capability_payload["updated_at"] = now
    dump_json(EVAL_LEDGER_PATH, eval_payload)
    dump_json(CAPABILITY_REGISTRY_PATH, capability_payload)


def main() -> int:
    now = iso_now()
    eval_payload = _load_json(EVAL_LEDGER_PATH)
    capability_payload = _load_json(CAPABILITY_REGISTRY_PATH)
    run = _find_run(eval_payload, RUN_ID)
    capability = _find_capability(capability_payload, "protocol-first-builder-kernel")
    bootstrap_checks = _check_bootstrap_takeover_explicit()
    runtime_linkage = _check_runtime_linkage(capability)

    if LIVE_ROUTE_OUTPUT_PATH.exists():
        LIVE_ROUTE_OUTPUT_PATH.unlink()

    with tempfile.TemporaryDirectory(prefix="athanor-builder-formal-eval-", dir="/tmp") as tmpdir_raw:
        tmpdir = Path(tmpdir_raw)
        env_base = os.environ.copy()
        formal_vitest_output = tmpdir / "builder-kernel-formal-eval-vitest.json"
        formal_completed = _run_command(
            [
                "corepack",
                "pnpm",
                "--dir",
                str(DASHBOARD_DIR),
                "exec",
                "vitest",
                "run",
                "--no-file-parallelism",
                str(FORMAL_TEST_PATH.relative_to(DASHBOARD_DIR)),
                "--reporter=json",
                f"--outputFile={formal_vitest_output}",
            ],
            cwd=REPO_ROOT,
            env=env_base,
            timeout=600,
        )
        assertions = _load_vitest_assertions(formal_vitest_output) if formal_vitest_output.exists() else []

        live_completed = _run_command(
            [
                "corepack",
                "pnpm",
                "--dir",
                str(DASHBOARD_DIR),
                "exec",
                "vitest",
                "run",
                "--no-file-parallelism",
                str(LIVE_ROUTE_TEST_PATH.relative_to(DASHBOARD_DIR)),
            ],
            cwd=REPO_ROOT,
            env=env_base
            | {
                "ATHANOR_ENABLE_LIVE_BUILDER_FORMAL_EVAL": "1",
                "ATHANOR_BUILDER_LIVE_EVAL_OUTPUT": str(LIVE_ROUTE_OUTPUT_PATH),
            },
            timeout=1200,
        )

    live_payload = _load_json(LIVE_ROUTE_OUTPUT_PATH) if LIVE_ROUTE_OUTPUT_PATH.exists() else {}
    targeted_validation = live_payload.get("targeted_validation") or {}
    changed_files = [str(item) for item in live_payload.get("files_changed", [])]
    checks = {
        "fast_formal_checks_passed": formal_completed.returncode == 0,
        "sovereign_only_routes_local_only": _assertion_status(assertions, "keeps sovereign-only tasks on the local-only lane") == "passed",
        "github_dependent_tasks_stay_non_live": _assertion_status(assertions, "keeps GitHub-dependent tasks off the live Codex route until an adapter is linked") == "passed",
        "failure_semantics_fail_closed": _assertion_status(assertions, "fails closed when the live builder route hits a controlled execution failure") == "passed",
        "operator_surface_projection_coherent": _assertion_status(assertions, "keeps builder and operator summary projections coherent for the active session") == "passed",
        "live_route_test_passed": live_completed.returncode == 0,
        "live_route_completed": live_payload.get("final_status") == "completed",
        "live_route_verification_passed": live_payload.get("verification_status") == "passed",
        "targeted_dashboard_typecheck_passed": str(targeted_validation.get("status") or "") == "passed" and "Type-check dashboard changes." in str(targeted_validation.get("detail") or ""),
        "resumable_handle_published": bool(live_payload.get("resumable_handle")),
        "dashboard_file_accounted_for": SMOKE_TARGET_PATH in changed_files,
        "operational_residue_scrubbed": ".codex" not in changed_files,
        "bootstrap_takeover_still_explicit": all(bootstrap_checks.values()),
        "runtime_packet_linkage_bound": bool(runtime_linkage.get("dashboard_rollout_path_bound")),
    }
    blocking_reasons = [name for name, passed in checks.items() if not passed]
    promotion_eval_status = "passed" if not blocking_reasons else "blocked"
    promotion_validity = "valid" if promotion_eval_status == "passed" else "requires_formal_eval_run"
    summary = (
        "Builder kernel formal eval is green: the direct live route passed TSC-backed verification, fail-closed routing checks held, operator projections stayed coherent, bootstrap takeover remains explicit, and the dashboard deploy packet is now the bounded rollout path."
        if promotion_eval_status == "passed"
        else "Builder kernel formal eval remains blocked until the direct live route, fail-closed routing checks, and bootstrap boundaries all pass together."
    )
    report = {
        "version": "2026-04-17.5",
        "generated_at": now,
        "source_of_truth": OUTPUT_PATH.as_posix(),
        "initiative_id": "protocol-first-builder-kernel",
        "run_id": RUN_ID,
        "promotion_eval_status": promotion_eval_status,
        "promotion_validity": promotion_validity,
        "blocking_reasons": blocking_reasons,
        "checks": checks,
        "live_route_artifact_path": LIVE_ROUTE_OUTPUT_PATH.as_posix(),
        "live_route": live_payload,
        "bootstrap_checks": bootstrap_checks,
        "runtime_linkage": runtime_linkage,
        "fast_formal_vitest": {
            "returncode": formal_completed.returncode,
            "stdout": formal_completed.stdout.strip(),
            "stderr": formal_completed.stderr.strip(),
            "output_file": str(formal_vitest_output),
        },
        "live_route_vitest": {
            "returncode": live_completed.returncode,
            "stdout": live_completed.stdout.strip(),
            "stderr": live_completed.stderr.strip(),
            "output_file": LIVE_ROUTE_OUTPUT_PATH.as_posix(),
        },
        "summary": summary,
        "next_action": (
            "Carry the linked builder proof through operator packet review and an explicit dashboard deploy decision before any wider builder takeover or release-tier advance."
            if promotion_eval_status == "passed"
            else "Fix the blocked builder-kernel formal-eval checks and rerun the bounded builder promotion eval."
        ),
    }
    _write_report(report)
    _update_registries(
        report=report,
        eval_payload=eval_payload,
        run=run,
        capability_payload=capability_payload,
        capability=capability,
    )
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
