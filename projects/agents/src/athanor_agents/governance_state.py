from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from .bootstrap_registry import get_governance_drill_registry, get_governance_drills
from .durable_state import _as_datetime, _as_json_value, _as_timestamp, _execute, _fetch_all
from .execution_state import list_approval_request_records, list_execution_run_records
from .launch_governance import build_launch_governance_posture
from .model_governance import (
    get_attention_budget_registry,
    get_core_change_window_registry,
    get_operator_runbooks_registry,
    get_system_mode_registry,
)
from .operator_work import inbox_stats


OPEN_INBOX_STATUSES = {"new", "acknowledged", "snoozed"}


def _repo_root() -> Path:
    preferred: Path | None = None
    for base in Path(__file__).resolve().parents:
        if base.joinpath("STATUS.md").exists() and base.joinpath("config", "automation-backbone").exists():
            return base
        if base.joinpath("config", "automation-backbone").exists():
            preferred = base
    if preferred is not None:
        return preferred
    for base in Path(__file__).resolve().parents:
        if base.joinpath("config", "automation-backbone").exists():
            return base
    return Path("/workspace")


@lru_cache(maxsize=1)
def _runtime_artifact_root() -> Path:
    env_root = str(os.getenv("ATHANOR_RUNTIME_ARTIFACT_ROOT") or "").strip()
    if env_root:
        return Path(env_root)

    repo_root = _repo_root()
    if os.access(repo_root, os.W_OK):
        return repo_root

    output_root = Path("/output")
    if output_root.exists() and os.access(output_root, os.W_OK):
        return output_root

    return repo_root


def _registry_items(registry: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in registry.get(key, [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def _governance_drill_by_id(drill_id: str) -> dict[str, Any]:
    for item in get_governance_drills():
        if str(item.get("drill_id") or "").strip() == drill_id:
            return dict(item)
    raise ValueError(f"Unknown governance drill: {drill_id}")


def governance_drill_evidence_root_path() -> Path:
    registry = get_governance_drill_registry()
    relative = str(registry.get("evidence_root") or "reports/governance/drills").strip()
    return _runtime_artifact_root() / Path(relative)


def governance_drill_evidence_path(drill_id: str) -> Path:
    drill = _governance_drill_by_id(drill_id)
    artifacts = [
        str(item).strip()
        for item in drill.get("evidence_artifacts", [])
        if str(item).strip()
    ]
    if not artifacts:
        raise ValueError(f"Governance drill {drill_id} does not declare an evidence artifact")
    return _runtime_artifact_root() / Path(artifacts[0])


def build_governance_drill_snapshot() -> dict[str, Any]:
    registry = get_governance_drill_registry()
    runbook_registry = get_operator_runbooks_registry()
    runbook_ids = {
        str(item.get("id") or "").strip()
        for item in runbook_registry.get("runbooks", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    drills: list[dict[str, Any]] = []
    for item in get_governance_drills():
        evidence_artifacts = [
            str(value).strip()
            for value in item.get("evidence_artifacts", [])
            if str(value).strip()
        ]
        evidence_paths = [_runtime_artifact_root() / Path(path) for path in evidence_artifacts]
        missing_artifacts = [path.as_posix() for path in evidence_paths if not path.exists()]
        artifact_payload: dict[str, Any] = {}
        artifact_path = evidence_paths[0].as_posix() if evidence_paths else ""
        artifact_status = "missing"
        passed = False
        detail = ""
        if evidence_paths and evidence_paths[0].exists():
            try:
                artifact_payload = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                artifact_status = "unreadable"
                detail = "Governance drill artifact exists but could not be parsed."
            else:
                passed = bool(artifact_payload.get("passed"))
                artifact_status = "passed" if passed else "failed"
                detail = str(
                    artifact_payload.get("detail")
                    or artifact_payload.get("summary")
                    or artifact_payload.get("status")
                    or ""
                )

        runbook_id = str(item.get("runbook_id") or "").strip()
        runbook_present = runbook_id in runbook_ids
        evidence_present = bool(evidence_paths) and not missing_artifacts
        drills.append(
            {
                **item,
                "runbook_present": runbook_present,
                "evidence_present": evidence_present,
                "missing_artifacts": missing_artifacts,
                "artifact_path": artifact_path,
                "artifact_status": artifact_status,
                "passed": passed,
                "detail": detail,
                "artifact_payload": artifact_payload if artifact_payload else None,
            }
        )

    evidence_complete = all(
        bool(item.get("runbook_present")) and bool(item.get("evidence_present"))
        for item in drills
    )
    all_green = evidence_complete and all(bool(item.get("passed")) for item in drills)
    failed_drill_ids = [
        str(item.get("drill_id") or "")
        for item in drills
        if bool(item.get("evidence_present")) and not bool(item.get("passed"))
    ]
    return {
        "evidence_root": str(registry.get("evidence_root") or ""),
        "evidence_complete": evidence_complete,
        "all_green": all_green,
        "failed_drill_ids": failed_drill_ids,
        "drills": drills,
    }


def _write_governance_drill_artifact(drill_id: str, payload: dict[str, Any]) -> Path:
    path = governance_drill_evidence_path(drill_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


async def rehearse_governance_drill(
    drill_id: str,
    *,
    actor: str = "operator",
    reason: str = "",
    request_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    drill = _governance_drill_by_id(drill_id)
    now = datetime.now(timezone.utc).isoformat()
    current_mode = await get_current_system_mode_record()
    current_mode_name = str(current_mode.get("mode") or "normal")
    launch = build_launch_governance_posture()
    attention = await compute_attention_posture()
    detail = ""
    passed = False
    blocker_id = ""
    evidence_refs = [governance_drill_evidence_path(drill_id).as_posix()]
    affected_services_or_routes = ["/v1/operator/governance", "/v1/operator/system-mode", "/bootstrap", "/operator"]
    expected_mode_change = {"from": current_mode_name, "to": str(drill.get("mode_target") or current_mode_name)}
    observed_mode_change = {
        "from": current_mode_name,
        "to": current_mode_name,
        "changed": False,
        "reason": "bounded_rehearsal",
    }

    if drill_id in {"constrained-mode", "degraded-mode", "recovery-only"}:
        target_mode = str(drill.get("mode_target") or current_mode_name)
        evidence_refs.extend(
            [
                "config/automation-backbone/governance-drill-registry.json",
                "docs/operations/OPERATOR_RUNBOOKS.md",
            ]
        )
        if current_mode_name == target_mode:
            passed = True
            detail = (
                f"System mode is already {target_mode}; live governance posture already matches the drill target."
            )
            observed_mode_change = {
                "from": current_mode_name,
                "to": target_mode,
                "changed": False,
                "restored_to": current_mode_name,
                "restored": True,
                "reason": "target_mode_already_active",
            }
        else:
            entered_record = None
            try:
                entered_record = await enter_system_mode_record(
                    target_mode,
                    entered_by=actor,
                    trigger=f"governance_drill:{drill_id}",
                    exit_conditions=f"Restore prior mode {current_mode_name} after bounded rehearsal.",
                    notes=f"Bounded governance rehearsal for {drill_id}.",
                    metadata={
                        "governance_drill": drill_id,
                        "rehearsal": True,
                        "restore_mode": current_mode_name,
                    },
                )
                changed_mode = await get_current_system_mode_record()
                changed_mode_name = str(changed_mode.get("mode") or current_mode_name)
                changed = changed_mode_name == target_mode
                restored = False
                restored_mode_name = changed_mode_name
                if changed:
                    await enter_system_mode_record(
                        current_mode_name,
                        entered_by=actor,
                        trigger=f"governance_drill:{drill_id}:restore",
                        exit_conditions="No further action; bounded rehearsal completed.",
                        notes=f"Restore prior mode after {drill_id} rehearsal.",
                        metadata={
                            "governance_drill": drill_id,
                            "rehearsal_restore": True,
                            "restored_from": target_mode,
                        },
                    )
                    restored_mode = await get_current_system_mode_record()
                    restored_mode_name = str(restored_mode.get("mode") or changed_mode_name)
                    restored = restored_mode_name == current_mode_name
                passed = changed and restored
                detail = (
                    f"Durable governance rehearsal entered {target_mode} and restored {current_mode_name} cleanly."
                    if passed
                    else (
                        f"System mode entered {changed_mode_name} during rehearsal but restore to "
                        f"{current_mode_name} did not complete cleanly."
                        if changed
                        else f"System mode did not enter {target_mode} during rehearsal."
                    )
                )
                observed_mode_change = {
                    "from": current_mode_name,
                    "to": changed_mode_name,
                    "changed": changed,
                    "restored_to": restored_mode_name,
                    "restored": restored,
                    "reason": "durable_rehearsal",
                }
                evidence_refs.append(f"system_mode_entry:{entered_record['id']}")
            except Exception as exc:
                from .durable_state import get_durable_state_status

                durable_state = get_durable_state_status()
                detail = (
                    f"Durable governance rehearsal failed while entering {target_mode}: {exc}. "
                    f"Durable state configured={bool(durable_state.get('configured'))}, "
                    f"schema_ready={bool(durable_state.get('schema_ready'))}, "
                    f"reason={str(durable_state.get('reason') or 'unknown')}."
                )
                observed_mode_change = {
                    "from": current_mode_name,
                    "to": current_mode_name,
                    "changed": False,
                    "restored_to": current_mode_name,
                    "restored": True,
                    "reason": "rehearsal_error",
                }
                if entered_record is not None:
                    try:
                        await enter_system_mode_record(
                            current_mode_name,
                            entered_by=actor,
                            trigger=f"governance_drill:{drill_id}:error_restore",
                            exit_conditions="No further action; best-effort restore after rehearsal failure.",
                            notes=f"Best-effort restore after failed {drill_id} rehearsal.",
                            metadata={
                                "governance_drill": drill_id,
                                "rehearsal_restore": True,
                                "restored_from": target_mode,
                                "best_effort": True,
                            },
                        )
                    except Exception:
                        pass
    elif drill_id == "blocked-approval":
        from .bootstrap_state import (
            list_bootstrap_blockers,
            list_bootstrap_programs,
            record_bootstrap_blocker,
            resolve_bootstrap_blocker,
        )
        from .operator_work import fetch_operator_inbox_record, resolve_inbox_item

        blockers = await list_bootstrap_blockers(status="open", limit=200)
        approval_blockers = [item for item in blockers if bool(item.get("approval_required"))]
        programs = await list_bootstrap_programs()
        family_statuses = {
            str(family.get("id") or ""): str(family.get("status") or "")
            for program in programs
            for family in program.get("families", [])
            if isinstance(family, dict)
        }
        waiting_approval = any(status == "waiting_approval" for status in family_statuses.values())
        unrelated_ready = any(
            family_id != "durable_persistence_activation" and status in {"ready", "active", "completed"}
            for family_id, status in family_statuses.items()
        )
        created_blocker = None
        created_inbox = None
        if not approval_blockers and not waiting_approval:
            created_blocker = await record_bootstrap_blocker(
                program_id="launch-readiness-bootstrap",
                slice_id="persist-04-activation-cutover",
                family="durable_persistence_activation",
                blocker_class="approval_path_failed",
                reason="Governance rehearsal created a bounded approval blocker to verify inbox/blocker evidence.",
                approval_required=True,
                retry_after_minutes=0,
                metadata={
                    "governance_drill": drill_id,
                    "temporary": True,
                    "created_by": actor,
                },
            )
            if created_blocker:
                blocker_id = str(created_blocker.get("id") or "")
                inbox_id = str(created_blocker.get("inbox_id") or "")
                if inbox_id:
                    created_inbox = await fetch_operator_inbox_record(inbox_id)
            approval_blockers = [*(approval_blockers or []), *([created_blocker] if created_blocker else [])]
        blocker_evidence = bool(approval_blockers or waiting_approval)
        inbox_evidence = bool(
            created_inbox
            or any(str(item.get("inbox_id") or "").strip() for item in approval_blockers)
        )
        if created_blocker is not None:
            passed = blocker_evidence and inbox_evidence and unrelated_ready
        else:
            passed = blocker_evidence and unrelated_ready
        detail = (
            "Approval blockers and inbox evidence are recorded and unrelated bootstrap work continues."
            if passed
            else "Blocked-approval evidence is missing either an approval blocker, inbox evidence, or continued unrelated bootstrap progress."
        )
        observed_mode_change["reason"] = "approval blockers recorded without forcing a global system mode change"
        affected_services_or_routes.extend(["/v1/bootstrap/programs", "/v1/bootstrap/blockers", "/v1/operator/inbox"])
        evidence_refs.extend(["reports/bootstrap/latest.json", "reports/bootstrap/durable-persistence-packet.json"])
        if created_blocker:
            blocker_id = str(created_blocker.get("id") or blocker_id)
            evidence_refs.append(f"bootstrap_blocker:{blocker_id}")
            inbox_id = str(created_blocker.get("inbox_id") or "")
            if inbox_id:
                evidence_refs.append(f"operator_inbox:{inbox_id}")
        if created_blocker and passed:
            await resolve_bootstrap_blocker(
                str(created_blocker.get("id") or ""),
                note="Resolved temporary governance drill approval blocker.",
            )
            inbox_id = str(created_blocker.get("inbox_id") or "")
            if inbox_id:
                await resolve_inbox_item(
                    inbox_id,
                    note="Resolved temporary governance drill approval inbox item.",
                )
    elif drill_id == "restore":
        recovery_artifact = _runtime_artifact_root() / "reports" / "recovery" / "latest.json"
        if recovery_artifact.exists():
            try:
                recovery_payload = json.loads(recovery_artifact.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                passed = False
                detail = "Restore rehearsal artifact exists but could not be parsed."
            else:
                snapshot = dict(recovery_payload.get("snapshot") or {})
                flows = snapshot.get("flows") if isinstance(snapshot.get("flows"), list) else []
                restore_flow = next(
                    (
                        item
                        for item in flows
                        if isinstance(item, dict) and str(item.get("id") or "") == "restore_drill"
                    ),
                    {},
                )
                flow_details = dict(restore_flow.get("details") or {})
                verified_store_count = int(flow_details.get("verified_store_count") or 0)
                store_count = int(flow_details.get("store_count") or 0)
                flow_outcome = str(restore_flow.get("last_outcome") or restore_flow.get("status") or "")
                passed = bool(recovery_payload.get("success")) and flow_outcome == "passed"
                if passed:
                    detail = (
                        "Restore rehearsal artifact is present and the live restore drill passed "
                        f"for all {store_count} critical stores."
                    )
                else:
                    detail = (
                        "Restore rehearsal artifact exists but is not green yet: "
                        f"outcome={flow_outcome or 'unknown'}, "
                        f"verified_stores={verified_store_count}/{store_count}."
                    )
        else:
            passed = False
            detail = "Restore rehearsal artifact is not present yet; bounded restore evidence still needs to be generated."
        evidence_refs.extend(
            [
                "scripts/generate_recovery_evidence.py",
                recovery_artifact.as_posix(),
            ]
        )
        affected_services_or_routes.extend(["/v1/operator/governance", "/api/operator/governance"])
    elif drill_id == "rollback":
        from .foundry_state import list_deploy_candidate_records, list_rollback_event_records

        candidates = await list_deploy_candidate_records("athanor", limit=20)
        rollbacks = await list_rollback_event_records("athanor", limit=20)
        candidate = next(
            (
                item
                for item in candidates
                if dict(item.get("rollback_target") or {})
                and dict(item.get("smoke_results") or {})
            ),
            None,
        )
        passed = candidate is not None and bool(rollbacks)
        detail = (
            "Recorded rollback target, smoke evidence, and rollback event are all present for the Athanor proving candidate."
            if passed
            else "Rollback rehearsal still lacks a recorded rollback event or candidate rollback target."
        )
        evidence_refs.extend(
            [
                "reports/bootstrap/foundry-proving-packet.json",
                "reports/bootstrap/latest.json",
            ]
        )
        affected_services_or_routes.extend(["/v1/projects/athanor/deployments", "/v1/projects/athanor/rollbacks"])
    else:
        detail = "Restore the missing drill implementation before rehearsing it."

    artifact_payload = {
        "drill_id": drill_id,
        "runbook_id": str(drill.get("runbook_id") or ""),
        "passed": passed,
        "status": "passed" if passed else "failed",
        "detail": detail,
        "request_context": {
            "actor": actor,
            "reason": reason or f"Recorded bounded governance rehearsal for {drill_id}",
            "kind": "bounded_rehearsal",
            **(request_context or {}),
        },
        "trigger_time": now,
        "expected_mode_change": expected_mode_change,
        "observed_mode_change": observed_mode_change,
        "affected_services_or_routes": affected_services_or_routes,
        "blocker_id": "",
        "evidence_refs": evidence_refs,
        "attention_posture": attention,
        "launch_posture": {
            "current_phase_id": launch.get("current_phase_id"),
            "current_phase_status": launch.get("current_phase_status"),
            "launch_blockers": list(launch.get("launch_blockers") or []),
            "issues": list(launch.get("issues") or []),
        },
        "metadata": {
            "mode_target": str(drill.get("mode_target") or ""),
            "dashboard_effect": str(drill.get("dashboard_effect") or ""),
            "health_effect": str(drill.get("health_effect") or ""),
            "fail_blocker_class": str(drill.get("fail_blocker_class") or ""),
        },
    }

    artifact_path = _write_governance_drill_artifact(drill_id, artifact_payload)

    from .bootstrap_state import (
        list_bootstrap_blockers,
        record_bootstrap_blocker,
        resolve_bootstrap_blocker,
        update_bootstrap_blocker,
    )

    open_blockers = await list_bootstrap_blockers(status="open", family="governance_rehearsal", limit=200)
    matching_blockers = [
        item
        for item in open_blockers
        if str((item.get("metadata") or {}).get("drill_id") or "") == drill_id
    ]

    if not passed:
        existing = next(
            (
                item
                for item in matching_blockers
                if str(item.get("blocker_class") or "") == str(drill.get("fail_blocker_class") or "")
            ),
            None,
        )
        if existing is None:
            blocker = await record_bootstrap_blocker(
                program_id="launch-readiness-bootstrap",
                slice_id="gov-04-live-rehearsal",
                family="governance_rehearsal",
                blocker_class=str(drill.get("fail_blocker_class") or "governance_drill_failed"),
                reason=f"Governance drill {drill_id} is not green: {detail}",
                retry_after_minutes=1440,
                metadata={"drill_id": drill_id, "artifact_path": artifact_path.as_posix()},
            )
            blocker_id = str(blocker.get("id") or "")
        else:
            await update_bootstrap_blocker(
                str(existing.get("id") or ""),
                reason=f"Governance drill {drill_id} is not green: {detail}",
                retry_after_minutes=1440,
                metadata={"drill_id": drill_id, "artifact_path": artifact_path.as_posix()},
            )
            blocker_id = str(existing.get("id") or "")
        artifact_payload["blocker_id"] = blocker_id
        _write_governance_drill_artifact(drill_id, artifact_payload)
    else:
        for blocker in matching_blockers:
            await resolve_bootstrap_blocker(
                str(blocker.get("id") or ""),
                note=f"Governance drill {drill_id} is now green: {detail}",
            )

    return artifact_payload


async def rehearse_all_governance_drills(
    *,
    actor: str = "operator",
    reason: str = "",
    request_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for drill in get_governance_drills():
        drill_id = str(drill.get("drill_id") or "").strip()
        if not drill_id:
            continue
        results.append(
            await rehearse_governance_drill(
                drill_id,
                actor=actor,
                reason=reason,
                request_context=request_context,
            )
        )
    return results


def _row_to_system_mode_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("mode_entry_id") or ""),
        "mode": str(row.get("mode") or "normal"),
        "entered_at": _as_timestamp(row.get("entered_at")),
        "entered_by": str(row.get("entered_by") or "operator"),
        "trigger": str(row.get("trigger") or ""),
        "exit_conditions": str(row.get("exit_conditions") or ""),
        "notes": str(row.get("notes") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
    }


def _row_to_attention_budget_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("budget_id") or ""),
        "scope_type": str(row.get("scope_type") or "agent"),
        "scope_id": str(row.get("scope_id") or ""),
        "daily_limit": int(row.get("daily_limit") or 0),
        "urgent_bypass": _as_json_value(row.get("urgent_bypass_json"), default=[]),
        "used_today": int(row.get("used_today") or 0),
        "status": str(row.get("status") or "active"),
        "last_reset_at": _as_timestamp(row.get("last_reset_at")),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


def _row_to_core_change_window_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("window_id") or ""),
        "label": str(row.get("label") or ""),
        "schedule": str(row.get("schedule") or ""),
        "start_local": str(row.get("start_local") or ""),
        "end_local": str(row.get("end_local") or ""),
        "allowed_change_classes": _as_json_value(row.get("allowed_change_classes_json"), default=[]),
        "status": str(row.get("status") or "live"),
        "notes": str(row.get("notes") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


async def _seed_default_system_mode() -> None:
    rows = await _fetch_all(
        """
        SELECT mode_entry_id, mode, entered_at, entered_by, trigger, exit_conditions, notes, metadata_json
        FROM control.system_mode_history
        ORDER BY entered_at DESC
        LIMIT 1
        """
    )
    if rows:
        return

    registry = get_system_mode_registry()
    default_mode = str(registry.get("default_mode") or "normal")
    now = datetime.now(timezone.utc)
    await _execute(
        """
        INSERT INTO control.system_mode_history (
            mode_entry_id, mode, entered_at, entered_by, trigger, exit_conditions, notes, metadata_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (mode_entry_id) DO NOTHING
        """,
        (
            f"mode-{default_mode}-initial",
            default_mode,
            now,
            "system",
            "registry_seed",
            "Exit when the registry-backed operating posture changes.",
            "Seeded from system-mode registry.",
            json.dumps({"seeded": True}),
        ),
    )


async def _seed_attention_budgets() -> None:
    registry_items = _registry_items(get_attention_budget_registry(), "budgets")
    if not registry_items:
        return
    existing_rows = await _fetch_all("SELECT budget_id FROM control.attention_budgets")
    existing = {str(row.get("budget_id") or "") for row in existing_rows}
    now = datetime.now(timezone.utc)
    for item in registry_items:
        budget_id = str(item.get("id") or "").strip()
        if not budget_id or budget_id in existing:
            continue
        await _execute(
            """
            INSERT INTO control.attention_budgets (
                budget_id,
                scope_type,
                scope_id,
                daily_limit,
                urgent_bypass_json,
                used_today,
                status,
                last_reset_at,
                metadata_json,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (budget_id) DO NOTHING
            """,
            (
                budget_id,
                str(item.get("scope_type") or "agent"),
                str(item.get("scope_id") or budget_id),
                int(item.get("daily_limit") or 0),
                json.dumps(item.get("urgent_bypass") or []),
                int(item.get("used_today") or 0),
                str(item.get("status") or "active"),
                now,
                json.dumps({"seeded_from_registry": True}),
                now,
                now,
            ),
        )


async def _seed_core_change_windows() -> None:
    registry_items = _registry_items(get_core_change_window_registry(), "windows")
    if not registry_items:
        return
    existing_rows = await _fetch_all("SELECT window_id FROM control.core_change_windows")
    existing = {str(row.get("window_id") or "") for row in existing_rows}
    now = datetime.now(timezone.utc)
    for item in registry_items:
        window_id = str(item.get("id") or "").strip()
        if not window_id or window_id in existing:
            continue
        await _execute(
            """
            INSERT INTO control.core_change_windows (
                window_id,
                label,
                schedule,
                start_local,
                end_local,
                allowed_change_classes_json,
                status,
                notes,
                metadata_json,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (window_id) DO NOTHING
            """,
            (
                window_id,
                str(item.get("label") or window_id),
                str(item.get("schedule") or ""),
                str(item.get("start_local") or ""),
                str(item.get("end_local") or ""),
                json.dumps(item.get("allowed_change_classes") or []),
                str(item.get("status") or "live"),
                str(item.get("notes") or ""),
                json.dumps({"seeded_from_registry": True}),
                now,
                now,
            ),
        )


async def ensure_governance_seed_data() -> None:
    await _seed_default_system_mode()
    await _seed_attention_budgets()
    await _seed_core_change_windows()


async def list_system_mode_records(*, limit: int = 20) -> list[dict[str, Any]]:
    await ensure_governance_seed_data()
    rows = await _fetch_all(
        """
        SELECT mode_entry_id, mode, entered_at, entered_by, trigger, exit_conditions, notes, metadata_json
        FROM control.system_mode_history
        ORDER BY entered_at DESC, mode_entry_id DESC
        LIMIT %s
        """,
        (max(int(limit), 1),),
    )
    return [_row_to_system_mode_record(row) for row in rows]


async def get_current_system_mode_record() -> dict[str, Any]:
    await ensure_governance_seed_data()
    rows = await _fetch_all(
        """
        SELECT mode_entry_id, mode, entered_at, entered_by, trigger, exit_conditions, notes, metadata_json
        FROM control.system_mode_history
        ORDER BY entered_at DESC, mode_entry_id DESC
        LIMIT 1
        """
    )
    if not rows:
        return {"id": "mode-normal-initial", "mode": "normal", "entered_at": 0.0, "entered_by": "system", "trigger": "fallback", "exit_conditions": "", "notes": "", "metadata": {}}
    return _row_to_system_mode_record(rows[0])


async def enter_system_mode_record(
    mode: str,
    *,
    entered_by: str = "operator",
    trigger: str = "",
    exit_conditions: str = "",
    notes: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry_modes = {item.get("id") for item in _registry_items(get_system_mode_registry(), "modes")}
    if mode not in registry_modes:
        raise ValueError(f"Unknown system mode: {mode}")

    record = {
        "id": f"mode-{uuid.uuid4().hex[:8]}",
        "mode": mode,
        "entered_at": datetime.now(timezone.utc).timestamp(),
        "entered_by": entered_by,
        "trigger": trigger,
        "exit_conditions": exit_conditions,
        "notes": notes,
        "metadata": metadata or {},
    }
    ok = await _execute(
        """
        INSERT INTO control.system_mode_history (
            mode_entry_id, mode, entered_at, entered_by, trigger, exit_conditions, notes, metadata_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            record["id"],
            record["mode"],
            _as_datetime(record["entered_at"]) or datetime.now(timezone.utc),
            record["entered_by"],
            record["trigger"],
            record["exit_conditions"],
            record["notes"],
            json.dumps(record["metadata"]),
        ),
    )
    if not ok:
        raise RuntimeError(f"Failed to persist system mode {mode}")
    return record


async def list_attention_budget_records(*, status: str = "", limit: int = 100) -> list[dict[str, Any]]:
    await ensure_governance_seed_data()
    query = """
        SELECT
            budget_id,
            scope_type,
            scope_id,
            daily_limit,
            urgent_bypass_json,
            used_today,
            status,
            last_reset_at,
            metadata_json,
            created_at,
            updated_at
        FROM control.attention_budgets
    """
    params: list[Any] = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    query += " ORDER BY daily_limit DESC, budget_id ASC LIMIT %s"
    params.append(max(int(limit), 1))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_attention_budget_record(row) for row in rows]


async def list_core_change_window_records(*, status: str = "", limit: int = 20) -> list[dict[str, Any]]:
    await ensure_governance_seed_data()
    query = """
        SELECT
            window_id,
            label,
            schedule,
            start_local,
            end_local,
            allowed_change_classes_json,
            status,
            notes,
            metadata_json,
            created_at,
            updated_at
        FROM control.core_change_windows
    """
    params: list[Any] = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    query += " ORDER BY window_id ASC LIMIT %s"
    params.append(max(int(limit), 1))
    rows = await _fetch_all(query, tuple(params))
    return [_row_to_core_change_window_record(row) for row in rows]


async def compute_attention_posture() -> dict[str, Any]:
    inbox = await inbox_stats()
    inbox_items = await _fetch_all(
        """
        SELECT inbox_id, severity, status
        FROM work.operator_inbox
        ORDER BY created_at DESC
        LIMIT 500
        """
    )
    open_inbox_count = sum(1 for row in inbox_items if str(row.get("status") or "") in OPEN_INBOX_STATUSES)
    urgent_inbox_count = sum(
        1
        for row in inbox_items
        if str(row.get("status") or "") in OPEN_INBOX_STATUSES and int(row.get("severity") or 0) >= 3
    )

    pending_approvals = await list_approval_request_records(status="pending", limit=500)
    blocked_runs = await list_execution_run_records(status="blocked", limit=500)
    now_ts = datetime.now(timezone.utc).timestamp()
    stale_blocked_runs = [
        run for run in blocked_runs if (now_ts - float(run.get("updated_at") or 0)) >= 1800
    ]

    breaches: list[str] = []
    if open_inbox_count > 10:
        breaches.append("attention:open_inbox")
    if urgent_inbox_count > 3:
        breaches.append("attention:urgent_inbox")
    if len(pending_approvals) > 5:
        breaches.append("attention:pending_approvals")
    if len(stale_blocked_runs) > 2:
        breaches.append("attention:stale_blocked_runs")

    current_mode = await get_current_system_mode_record()
    current_mode_id = str(current_mode.get("mode") or "normal")
    if current_mode_id in {"degraded", "recovery_only"}:
        recommended_mode = current_mode_id
    else:
        recommended_mode = "constrained" if breaches else "normal"

    return {
        "open_inbox_count": open_inbox_count,
        "urgent_inbox_count": urgent_inbox_count,
        "pending_approval_count": len(pending_approvals),
        "blocked_run_count": len(blocked_runs),
        "stale_blocked_run_count": len(stale_blocked_runs),
        "recommended_mode": recommended_mode,
        "breaches": breaches,
        "by_status": dict(inbox.get("by_status") or {}),
    }


async def build_governance_snapshot() -> dict[str, Any]:
    launch = build_launch_governance_posture()
    current_mode = await get_current_system_mode_record()
    mode_history = await list_system_mode_records(limit=10)
    attention_budgets = await list_attention_budget_records(limit=50)
    change_windows = await list_core_change_window_records(limit=10)
    attention = await compute_attention_posture()

    launch_blockers = list(launch.get("launch_blockers") or [])
    issues = list(launch.get("issues") or [])
    if attention.get("breaches"):
        issues.extend(str(item) for item in attention["breaches"])

    return {
        "current_mode": current_mode,
        "mode_history": mode_history,
        "attention_budgets": attention_budgets,
        "attention_posture": attention,
        "core_change_windows": change_windows,
        "launch_posture": launch,
        "launch_blockers": launch_blockers,
        "issues": issues,
        "launch_ready": not bool(launch_blockers),
    }
