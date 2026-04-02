from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import bootstrap_state as state
from .bootstrap_registry import get_bootstrap_execution_policy, get_bootstrap_host
from .execution_state import fetch_execution_run_record, upsert_execution_run_record
from .foundry_state import (
    fetch_deploy_candidate_record,
    list_execution_slice_records,
    list_foundry_run_records,
    upsert_deploy_candidate_record,
    upsert_execution_slice_record,
    upsert_foundry_run_record,
)
from .operator_state import fetch_backlog_record, upsert_backlog_record

logger = logging.getLogger(__name__)

_HOST_EXHAUSTION_STATUSES = {"quota_exhausted", "context_exhausted", "session_exhausted", "cooldown"}


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
    return Path.cwd()


def _worktree_root(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root.parent / f"{root.name}-bootstrap-worktrees"


def _policy_worktree_path(slice_record: dict[str, Any], repo_root: Path) -> Path | None:
    policy = get_bootstrap_execution_policy()
    worktree = dict(policy.get("worktree") or {})
    pattern = str(worktree.get("root_path_pattern") or "").strip()
    family = str(slice_record.get("family") or "").strip()
    slice_id = str(slice_record.get("id") or "").strip()
    if not pattern or not family or not slice_id:
        return None
    if repo_root.name.lower() != "athanor":
        return None
    try:
        return Path(pattern.format(family=family, slice_id=slice_id))
    except KeyError:
        return None


def _policy_branch_name(host_id: str, family: str, slice_id: str) -> str:
    policy = get_bootstrap_execution_policy()
    patterns = dict(dict(policy.get("worktree") or {}).get("branch_name_patterns") or {})
    pattern = str(patterns.get(host_id) or "").strip()
    if not pattern:
        return ""
    try:
        return pattern.format(family=family, slice_id=slice_id)
    except KeyError:
        return ""


def _slice_execution_mode(slice_record: dict[str, Any]) -> str:
    mode = str(slice_record.get("execution_mode") or "").strip()
    if mode:
        return mode
    metadata = dict(slice_record.get("metadata") or {})
    return str(metadata.get("execution_mode") or metadata.get("host_mode") or "").strip()


def _slice_requires_worktree(slice_record: dict[str, Any]) -> bool:
    return _slice_execution_mode(slice_record) == "code_mutation"


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git command failed").strip())
    return result


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _bootstrap_metadata(
    *,
    program_id: str,
    family: str,
    slice_id: str,
    host_id: str,
    continuation_mode: str,
) -> dict[str, Any]:
    return {
        "program_id": program_id,
        "family": family,
        "slice_id": slice_id,
        "host_id": host_id,
        "continuation_mode": continuation_mode,
        "updated_at": _iso_now(),
    }


def _merge_bootstrap_metadata(
    metadata: dict[str, Any] | None,
    *,
    program_id: str,
    family: str,
    slice_id: str,
    host_id: str,
    continuation_mode: str,
) -> dict[str, Any]:
    record = dict(metadata or {})
    record["bootstrap"] = _bootstrap_metadata(
        program_id=program_id,
        family=family,
        slice_id=slice_id,
        host_id=host_id,
        continuation_mode=continuation_mode,
    )
    record["bootstrap_program_id"] = program_id
    record["bootstrap_family"] = family
    record["bootstrap_slice_id"] = slice_id
    record["bootstrap_host"] = host_id
    record["continuation_mode"] = continuation_mode
    return record


async def mirror_bootstrap_lineage(slice_record: dict[str, Any]) -> dict[str, list[str]]:
    metadata = dict(slice_record.get("metadata") or {})
    program_id = str(slice_record.get("program_id") or "")
    family = str(slice_record.get("family") or "")
    slice_id = str(slice_record.get("id") or "")
    host_id = str(slice_record.get("host_id") or "")
    continuation_mode = str(slice_record.get("continuation_mode") or "external_bootstrap")
    mirrored: dict[str, list[str]] = {"backlog": [], "runs": [], "foundry": []}

    backlog_id = str(metadata.get("backlog_id") or metadata.get("canonical_backlog_id") or "")
    if backlog_id:
        backlog = await fetch_backlog_record(backlog_id)
        if backlog:
            backlog["metadata"] = _merge_bootstrap_metadata(
                dict(backlog.get("metadata") or {}),
                program_id=program_id,
                family=family,
                slice_id=slice_id,
                host_id=host_id,
                continuation_mode=continuation_mode,
            )
            await upsert_backlog_record(backlog)
            mirrored["backlog"].append(backlog_id)

    run_ids: list[str] = []
    for raw_run_id in (
        metadata.get("run_id"),
        metadata.get("execution_run_id"),
        metadata.get("canonical_run_id"),
    ):
        run_id = str(raw_run_id or "").strip()
        if run_id and run_id not in run_ids:
            run_ids.append(run_id)
    for run_id in run_ids:
        run_record = await fetch_execution_run_record(run_id)
        if run_record:
            run_record["metadata"] = _merge_bootstrap_metadata(
                dict(run_record.get("metadata") or {}),
                program_id=program_id,
                family=family,
                slice_id=slice_id,
                host_id=host_id,
                continuation_mode=continuation_mode,
            )
            await upsert_execution_run_record(run_record)
            mirrored["runs"].append(run_id)

    project_id = str(metadata.get("project_id") or metadata.get("canonical_project_id") or "")
    foundry_slice_id = str(metadata.get("foundry_slice_id") or metadata.get("execution_slice_id") or "")
    foundry_run_id = str(metadata.get("foundry_run_id") or "")
    candidate_id = str(metadata.get("candidate_id") or metadata.get("deploy_candidate_id") or "")
    if project_id and foundry_slice_id:
        for record in await list_execution_slice_records(project_id, limit=200):
            if str(record.get("id") or "") != foundry_slice_id:
                continue
            record["metadata"] = _merge_bootstrap_metadata(
                dict(record.get("metadata") or {}),
                program_id=program_id,
                family=family,
                slice_id=slice_id,
                host_id=host_id,
                continuation_mode=continuation_mode,
            )
            await upsert_execution_slice_record(record)
            mirrored["foundry"].append(foundry_slice_id)
            break
    if project_id and foundry_run_id:
        for record in await list_foundry_run_records(project_id, limit=200):
            if str(record.get("id") or "") != foundry_run_id:
                continue
            record["metadata"] = _merge_bootstrap_metadata(
                dict(record.get("metadata") or {}),
                program_id=program_id,
                family=family,
                slice_id=slice_id,
                host_id=host_id,
                continuation_mode=continuation_mode,
            )
            await upsert_foundry_run_record(record)
            mirrored["foundry"].append(foundry_run_id)
            break
    if project_id and candidate_id:
        candidate = await fetch_deploy_candidate_record(project_id, candidate_id)
        if candidate:
            candidate["metadata"] = _merge_bootstrap_metadata(
                dict(candidate.get("metadata") or {}),
                program_id=program_id,
                family=family,
                slice_id=slice_id,
                host_id=host_id,
                continuation_mode=continuation_mode,
            )
            await upsert_deploy_candidate_record(candidate)
            mirrored["foundry"].append(candidate_id)
    return mirrored


async def build_bootstrap_handoff_contract(slice_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": _iso_now(),
        "program_id": str(slice_record.get("program_id") or ""),
        "family": str(slice_record.get("family") or ""),
        "slice_id": str(slice_record.get("id") or ""),
        "objective": str(slice_record.get("objective") or ""),
        "current_ref": str(slice_record.get("current_ref") or ""),
        "worktree_path": str(slice_record.get("worktree_path") or ""),
        "files_touched": list(slice_record.get("files_touched") or []),
        "validation_status": str(slice_record.get("validation_status") or "pending"),
        "open_risks": list(slice_record.get("open_risks") or []),
        "next_step": str(slice_record.get("next_step") or ""),
        "stop_reason": str(slice_record.get("stop_reason") or ""),
        "resume_instructions": str(slice_record.get("resume_instructions") or ""),
    }


async def write_bootstrap_handoff_contract(slice_record: dict[str, Any]) -> str:
    contract = await build_bootstrap_handoff_contract(slice_record)
    contract_path = state._slice_dir(str(slice_record.get("id") or "")) / "handoff-contract.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    return str(contract_path)


async def prepare_bootstrap_worktree(
    slice_record: dict[str, Any],
    *,
    repo_root: Path | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    root = repo_root or _repo_root()
    execution_mode = _slice_execution_mode(slice_record)
    requires_worktree = _slice_requires_worktree(slice_record)
    base_ref = str(slice_record.get("current_ref") or "").strip() or "HEAD"
    if not requires_worktree:
        return {
            "repo_root": str(root),
            "worktree_path": "",
            "base_ref": base_ref,
            "branch_name": "",
            "materialized": False,
            "reused": False,
            "executed": execute,
            "stdout": "",
            "stderr": "",
            "worktree_required": False,
            "execution_mode": execution_mode,
        }
    desired = str(slice_record.get("worktree_path") or "").strip()
    policy_path = _policy_worktree_path(slice_record, root)
    worktree_path = Path(desired) if desired else policy_path or (_worktree_root(root) / str(slice_record.get("id") or ""))
    branch_name = _policy_branch_name(
        str(slice_record.get("host_id") or ""),
        str(slice_record.get("family") or ""),
        str(slice_record.get("id") or ""),
    )
    materialized = False
    reused = worktree_path.exists()
    stdout = ""
    stderr = ""

    if execute:
        if base_ref == "HEAD":
            rev = _run_git(["rev-parse", "HEAD"], cwd=root, check=True)
            base_ref = (rev.stdout or "").strip() or "HEAD"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        if not reused:
            result = _run_git(
                ["worktree", "add", "--detach", str(worktree_path), base_ref],
                cwd=root,
                check=False,
            )
            stdout = result.stdout
            stderr = result.stderr
            if result.returncode != 0:
                raise RuntimeError((stderr or stdout or "git worktree add failed").strip())
            materialized = True
            reused = worktree_path.exists()
    return {
        "repo_root": str(root),
        "worktree_path": str(worktree_path),
        "base_ref": base_ref,
        "branch_name": branch_name,
        "materialized": materialized,
        "reused": reused,
        "executed": execute,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "worktree_required": True,
        "execution_mode": execution_mode,
    }


def _host_ready(host_state: dict[str, Any], now: datetime) -> bool:
    status = str(host_state.get("status") or "available")
    if status == "available":
        return True
    if status not in _HOST_EXHAUSTION_STATUSES:
        return False
    cooldown_until = _parse_iso(str(host_state.get("cooldown_until") or ""))
    return cooldown_until is not None and cooldown_until <= now


def _host_sort_key(host_state: dict[str, Any]) -> tuple[int, str]:
    host_id = str(host_state.get("id") or "")
    host = get_bootstrap_host(host_id) or {}
    try:
        priority = int(host.get("relay_priority") or 999)
    except (TypeError, ValueError):
        priority = 999
    return (priority, host_id)


async def select_bootstrap_host_for_slice(
    slice_record: dict[str, Any],
    *,
    exclude_host: str = "",
) -> dict[str, Any] | None:
    hosts = await state.list_bootstrap_host_states()
    now = datetime.now(timezone.utc)
    preferred_host_id = str(slice_record.get("host_id") or "").strip()
    if preferred_host_id and preferred_host_id != exclude_host:
        preferred = next((host for host in hosts if str(host.get("id") or "") == preferred_host_id), None)
        if preferred and _host_ready(preferred, now):
            return preferred

    ready_hosts = [
        host
        for host in hosts
        if str(host.get("id") or "") != exclude_host and _host_ready(host, now)
    ]
    if not ready_hosts:
        return None
    ready_hosts.sort(key=_host_sort_key)
    return ready_hosts[0]


async def claim_next_bootstrap_slice_for_host(
    host_id: str,
    *,
    program_id: str = "",
    execute: bool = False,
) -> dict[str, Any]:
    await state.ensure_bootstrap_state(force=True)
    hosts = await state.list_bootstrap_host_states()
    host_state = next((item for item in hosts if str(item.get("id") or "") == host_id), None)
    if not host_state:
        raise ValueError(f"Unknown bootstrap host '{host_id}'")
    if not _host_ready(host_state, datetime.now(timezone.utc)):
        raise ValueError(f"Bootstrap host '{host_id}' is not ready to claim new work")

    programs = await state.list_bootstrap_programs()
    if program_id:
        programs = [item for item in programs if str(item.get("id") or "") == program_id]
    active_program = next(
        (
            item
            for item in programs
            if str(item.get("status") or "") not in {"completed", "ready_for_takeover_check"}
            and item.get("next_slice")
        ),
        None,
    )
    if not active_program:
        raise ValueError("No claimable bootstrap program is currently active")

    next_slice = dict(active_program.get("next_slice") or {})
    if not next_slice:
        raise ValueError(f"Bootstrap program '{active_program.get('id', '')}' has no claimable slice")

    worktree = await prepare_bootstrap_worktree(next_slice, execute=execute)
    worktree_required = bool(worktree.get("worktree_required"))
    claimed = await state.claim_bootstrap_slice(
        str(next_slice.get("id") or ""),
        host_id=host_id,
        current_ref=str(worktree.get("base_ref") or str(next_slice.get("current_ref") or "")),
        worktree_path=str(worktree.get("worktree_path") or ""),
        files_touched=list(next_slice.get("files_touched") or []),
        next_step=(
            f"Continue {next_slice.get('family', '')} in the prepared bootstrap worktree lane."
            if worktree_required
            else f"Continue {next_slice.get('family', '')} in the bootstrap {str(worktree.get('execution_mode') or 'execution')} lane."
        ),
    )
    contract_path = await write_bootstrap_handoff_contract(claimed)
    return {
        "program_id": str(active_program.get("id") or ""),
        "active_family": str(active_program.get("current_family") or ""),
        "recommended_host_id": str(active_program.get("recommended_host_id") or ""),
        "slice": claimed,
        "worktree": worktree,
        "contract_path": contract_path,
    }


async def relay_bootstrap_slice_for_host(
    host_id: str,
    *,
    slice_id: str = "",
    stop_reason: str = "context_exhausted",
    cooldown_minutes: int | None = None,
    execute: bool = False,
    blocker_class: str = "",
    approval_required: bool = False,
) -> dict[str, Any]:
    await state.ensure_bootstrap_state(force=True)
    hosts = await state.list_bootstrap_host_states()
    host_state = next((item for item in hosts if str(item.get("id") or "") == host_id), None)
    if not host_state:
        raise ValueError(f"Unknown bootstrap host '{host_id}'")

    active_slice_id = slice_id or str(host_state.get("active_slice_id") or "")
    if not active_slice_id:
        raise ValueError(f"Bootstrap host '{host_id}' has no active slice to relay")

    slice_record = await state.get_bootstrap_slice(active_slice_id)
    if not slice_record:
        raise ValueError(f"Unknown bootstrap slice '{active_slice_id}'")
    if str(slice_record.get("host_id") or "") != host_id:
        raise ValueError(f"Bootstrap slice '{active_slice_id}' is not currently claimed by '{host_id}'")

    target_host = await select_bootstrap_host_for_slice(slice_record, exclude_host=host_id)
    if not target_host:
        if execute:
            exhausted_status = stop_reason if stop_reason in _HOST_EXHAUSTION_STATUSES else "cooldown"
            await state.update_bootstrap_host_status(
                host_id,
                status=exhausted_status,
                active_slice_id=active_slice_id,
                last_reason=stop_reason,
                cooldown_minutes=cooldown_minutes or 30,
            )
            blocker = await state.record_bootstrap_blocker(
                program_id=str(slice_record.get("program_id") or ""),
                slice_id=active_slice_id,
                family=str(slice_record.get("family") or ""),
                blocker_class=blocker_class or "host_relay_blocked",
                reason=f"No alternate bootstrap host is ready to take over after {stop_reason}.",
                approval_required=approval_required,
                metadata={"from_host": host_id},
            )
            return {
                "status": "blocked",
                "slice": slice_record,
                "blocker": blocker,
                "stop_reason": stop_reason,
            }
        return {
            "status": "pending",
            "slice": slice_record,
            "stop_reason": stop_reason,
            "to_host_id": "",
        }

    if not execute:
        return {
            "status": "planned",
            "slice": slice_record,
            "from_host_id": host_id,
            "to_host_id": str(target_host.get("id") or ""),
            "stop_reason": stop_reason,
        }

    handoff = await state.handoff_bootstrap_slice(
        active_slice_id,
        from_host=host_id,
        to_host=str(target_host.get("id") or ""),
        current_ref=str(slice_record.get("current_ref") or ""),
        worktree_path=str(slice_record.get("worktree_path") or ""),
        files_touched=list(slice_record.get("files_touched") or []),
        validation_status=str(slice_record.get("validation_status") or "pending"),
        open_risks=list(slice_record.get("open_risks") or []),
        next_step="Resume the claimed bootstrap slice from the existing worktree and handoff contract.",
        stop_reason=stop_reason,
        resume_instructions="Continue from the existing worktree lane without restarting the slice.",
        cooldown_minutes=cooldown_minutes or 30,
        blocker_class=blocker_class,
        approval_required=approval_required,
    )
    contract_path = await write_bootstrap_handoff_contract(handoff["slice"])
    return {
        "status": "relayed",
        "slice": handoff["slice"],
        "handoff": handoff["handoff"],
        "from_host_id": host_id,
        "to_host_id": str(target_host.get("id") or ""),
        "contract_path": contract_path,
        "stop_reason": stop_reason,
    }


async def _set_slice_ready_for_retry(slice_record: dict[str, Any], *, reason: str) -> dict[str, Any]:
    updated = {
        **slice_record,
        "status": "ready",
        "host_id": "",
        "completed_at": "",
        "updated_at": _iso_now(),
        "next_step": reason,
        "stop_reason": "",
        "resume_instructions": reason,
    }
    await state._to_thread(
        state._execute_sync,
        """
        UPDATE bootstrap_slice
        SET status = ?, host_id = ?, completed_at = ?, updated_at = ?, next_step = ?, stop_reason = ?, resume_instructions = ?
        WHERE slice_id = ?
        """,
        (
            updated["status"],
            updated["host_id"],
            None,
            updated["updated_at"],
            updated["next_step"],
            updated["stop_reason"],
            updated["resume_instructions"],
            updated["id"],
        ),
    )
    await state._mirror_slice(updated)
    return updated


async def _set_integration_status(
    integration: dict[str, Any],
    *,
    status: str,
    blocker_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = {
        **integration,
        "status": status,
        "blocker_id": blocker_id or str(integration.get("blocker_id") or ""),
        "metadata": dict(metadata if metadata is not None else integration.get("metadata") or {}),
        "updated_at": _iso_now(),
        "completed_at": _iso_now() if status in {"replayed", "completed", "blocked"} else str(integration.get("completed_at") or ""),
    }
    await state._to_thread(
        state._execute_sync,
        """
        UPDATE bootstrap_integration
        SET status = ?, blocker_id = ?, metadata_json = ?, updated_at = ?, completed_at = ?
        WHERE integration_id = ?
        """,
        (
            updated["status"],
            updated["blocker_id"],
            json.dumps(updated["metadata"]),
            updated["updated_at"],
            updated["completed_at"] or None,
            updated["id"],
        ),
    )
    await state._mirror_integration(updated)
    return updated


async def _resolve_blocker(blocker: dict[str, Any], *, note: str) -> dict[str, Any]:
    metadata = dict(blocker.get("metadata") or {})
    metadata["resolution_note"] = note
    resolved = {
        **blocker,
        "status": "resolved",
        "metadata": metadata,
        "updated_at": _iso_now(),
        "resolved_at": _iso_now(),
    }
    await state._to_thread(
        state._execute_sync,
        """
        UPDATE bootstrap_blocker
        SET status = ?, metadata_json = ?, updated_at = ?, resolved_at = ?
        WHERE blocker_id = ?
        """,
        (
            resolved["status"],
            json.dumps(resolved["metadata"]),
            resolved["updated_at"],
            resolved["resolved_at"],
            resolved["id"],
        ),
    )
    await state._mirror_blocker(resolved)
    return resolved


async def retry_eligible_bootstrap_blockers(*, program_id: str = "") -> dict[str, Any]:
    blockers = await state.list_bootstrap_blockers(status="open", limit=500)
    now = datetime.now(timezone.utc)
    reopened: list[str] = []
    resolved: list[str] = []
    skipped: list[str] = []
    for blocker in blockers:
        if program_id and str(blocker.get("program_id") or "") != program_id:
            continue
        if bool(blocker.get("approval_required")):
            skipped.append(str(blocker.get("id") or ""))
            continue
        retry_at = _parse_iso(str(blocker.get("retry_at") or ""))
        if retry_at and retry_at > now:
            continue
        slice_id = str(blocker.get("slice_id") or "")
        if slice_id:
            slice_record = await state.get_bootstrap_slice(slice_id)
            if slice_record and str(slice_record.get("status") or "") in {"blocked", "completed", "failed", "cancelled"}:
                await _set_slice_ready_for_retry(
                    slice_record,
                    reason=f"Retry after bootstrap blocker {blocker['id']}",
                )
                reopened.append(slice_id)
        await _resolve_blocker(blocker, note="Retry window reached; slice reopened for continued execution.")
        resolved.append(str(blocker.get("id") or ""))
    if resolved or reopened:
        await state._write_snapshot_files()
    return {"resolved_blockers": resolved, "reopened_slices": reopened, "skipped_blockers": skipped}


async def ensure_pending_approval_blockers(*, program_id: str = "") -> dict[str, Any]:
    programs = await state.list_bootstrap_programs()
    if program_id:
        programs = [item for item in programs if str(item.get("id") or "") == program_id]
    slices = await state.list_bootstrap_slices(limit=500)
    blockers = await state.list_bootstrap_blockers(status="open", limit=500)
    created: list[str] = []
    for program in programs:
        program_value = str(program.get("id") or "")
        waiting_families = [
            str(family.get("id") or "")
            for family in program.get("families", [])
            if str(family.get("status") or "") == "waiting_approval"
        ]
        for family_id in waiting_families:
            family_slices = [
                item
                for item in slices
                if str(item.get("program_id") or "") == program_value
                and str(item.get("family") or "") == family_id
                and int(item.get("depth_level") or 1) >= 2
                and str(item.get("status") or "") in state._READY_SLICE_STATUSES
                and state._slice_blocks_on_approval(item)
            ]
            for slice_record in family_slices:
                if any(str(item.get("slice_id") or "") == str(slice_record.get("id") or "") for item in blockers):
                    continue
                metadata = dict(slice_record.get("metadata") or {})
                blocker = await state.record_bootstrap_blocker(
                    program_id=program_value,
                    slice_id=str(slice_record.get("id") or ""),
                    family=family_id,
                    blocker_class=str(metadata.get("blocker_class") or "approval_required"),
                    reason=(
                        f"Slice {slice_record.get('id', '')} requires explicit operator approval before "
                        "runtime mutation or promotion-sensitive continuation."
                    ),
                    approval_required=True,
                    metadata={
                        "catalog_slice_id": str(slice_record.get("catalog_slice_id") or ""),
                        "approval_class": str(metadata.get("approval_class") or ""),
                        "blocking_packet_id": str(slice_record.get("blocking_packet_id") or ""),
                        "execution_mode": str(slice_record.get("execution_mode") or ""),
                    },
                )
                created.append(str(blocker.get("id") or ""))
                blockers.append(blocker)
    return {"created_blockers": created}


async def maybe_relay_exhausted_slices(*, program_id: str = "", execute: bool = False) -> dict[str, Any]:
    slices = await state.list_bootstrap_slices(program_id=program_id, limit=500)
    hosts = {host["id"]: host for host in await state.list_bootstrap_host_states()}
    relayed: list[str] = []
    blocked: list[str] = []
    for slice_record in slices:
        if str(slice_record.get("status") or "") != "claimed":
            continue
        from_host = str(slice_record.get("host_id") or "")
        if not from_host:
            continue
        host_state = hosts.get(from_host)
        if not host_state:
            continue
        host_status = str(host_state.get("status") or "")
        if host_status not in _HOST_EXHAUSTION_STATUSES:
            continue
        target_host = await select_bootstrap_host_for_slice(slice_record, exclude_host=from_host)
        if not target_host:
            blocked.append(str(slice_record.get("id") or ""))
            continue
        if execute:
            handoff = await state.handoff_bootstrap_slice(
                str(slice_record.get("id") or ""),
                from_host=from_host,
                to_host=str(target_host.get("id") or ""),
                current_ref=str(slice_record.get("current_ref") or ""),
                worktree_path=str(slice_record.get("worktree_path") or ""),
                files_touched=list(slice_record.get("files_touched") or []),
                validation_status=str(slice_record.get("validation_status") or "pending"),
                open_risks=list(slice_record.get("open_risks") or []),
                next_step="Resume the claimed bootstrap slice in the same worktree lane.",
                stop_reason=str(host_state.get("last_reason") or host_status),
                resume_instructions="Continue from the existing worktree state without restarting the slice.",
            )
            await write_bootstrap_handoff_contract(handoff["slice"])
        relayed.append(str(slice_record.get("id") or ""))
    return {"relayed_slices": relayed, "blocked_relays": blocked}


async def progress_bootstrap_integrations(*, execute: bool = False) -> dict[str, Any]:
    integrations = await state.list_bootstrap_integrations(status="queued", limit=50)
    if not integrations:
        return {"processed": False, "integration_id": "", "status": "idle"}

    integration = integrations[0]
    repo_root = _repo_root()
    slice_record = await state.get_bootstrap_slice(str(integration.get("slice_id") or ""))
    validation_summary = dict(integration.get("validation_summary") or {})
    worktree_path = str((integration.get("metadata") or {}).get("worktree_path") or (slice_record or {}).get("worktree_path") or "")
    queue_path = str(integration.get("queue_path") or "")
    patch_path = str(integration.get("patch_path") or "")

    if not execute:
        return {
            "processed": False,
            "integration_id": str(integration.get("id") or ""),
            "status": "queued",
            "method": str(integration.get("method") or ""),
            "target_ref": str(integration.get("target_ref") or "main"),
        }

    dirty_status = _run_git(["status", "--porcelain"], cwd=repo_root, check=False)
    if dirty_status.returncode != 0:
        blocker = await state.record_bootstrap_blocker(
            program_id=str(integration.get("program_id") or ""),
            slice_id=str(integration.get("slice_id") or ""),
            family=str(integration.get("family") or ""),
            blocker_class="integration_failure",
            reason=(dirty_status.stderr or dirty_status.stdout or "Failed to inspect integration lane").strip(),
            metadata={"integration_id": integration["id"]},
        )
        await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
        return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}
    if (dirty_status.stdout or "").strip():
        blocker = await state.record_bootstrap_blocker(
            program_id=str(integration.get("program_id") or ""),
            slice_id=str(integration.get("slice_id") or ""),
            family=str(integration.get("family") or ""),
            blocker_class="integration_failure",
            reason="Serial integration lane requires a clean main workspace before replay.",
            metadata={"integration_id": integration["id"]},
        )
        await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
        return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}

    if not worktree_path:
        blocker = await state.record_bootstrap_blocker(
            program_id=str(integration.get("program_id") or ""),
            slice_id=str(integration.get("slice_id") or ""),
            family=str(integration.get("family") or ""),
            blocker_class="integration_failure",
            reason="Integration queue item has no bootstrap worktree to replay from.",
            metadata={"integration_id": integration["id"]},
        )
        await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
        return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}

    worktree = Path(worktree_path)
    if not worktree.exists():
        blocker = await state.record_bootstrap_blocker(
            program_id=str(integration.get("program_id") or ""),
            slice_id=str(integration.get("slice_id") or ""),
            family=str(integration.get("family") or ""),
            blocker_class="integration_failure",
            reason=f"Bootstrap worktree '{worktree}' is missing.",
            metadata={"integration_id": integration["id"]},
        )
        await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
        return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}

    queue_file = Path(queue_path) if queue_path else state._integration_queue_file(str(integration.get("slice_id") or ""))
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    if not patch_path:
        patch_file = queue_file.with_suffix(".patch")
        diff = _run_git(["diff", "--binary", "HEAD"], cwd=worktree, check=False)
        if diff.returncode != 0:
            blocker = await state.record_bootstrap_blocker(
                program_id=str(integration.get("program_id") or ""),
                slice_id=str(integration.get("slice_id") or ""),
                family=str(integration.get("family") or ""),
                blocker_class="integration_failure",
                reason=(diff.stderr or diff.stdout or "Failed to generate patch from bootstrap worktree").strip(),
                metadata={"integration_id": integration["id"]},
            )
            await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
            return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}
        if not (diff.stdout or "").strip():
            blocker = await state.record_bootstrap_blocker(
                program_id=str(integration.get("program_id") or ""),
                slice_id=str(integration.get("slice_id") or ""),
                family=str(integration.get("family") or ""),
                blocker_class="integration_failure",
                reason="Bootstrap worktree has no diff to replay onto the main integration lane.",
                metadata={"integration_id": integration["id"]},
            )
            await _set_integration_status(integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
            return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}
        patch_file.write_text(diff.stdout, encoding="utf-8")
        patch_path = str(patch_file)

    updated_integration = await _set_integration_status(
        integration,
        status="replaying",
        metadata={
            **dict(integration.get("metadata") or {}),
            "patch_path": patch_path,
            "queue_path": str(queue_file),
        },
    )
    apply_result = _run_git(["apply", "--index", patch_path], cwd=repo_root, check=False)
    if apply_result.returncode != 0:
        blocker = await state.record_bootstrap_blocker(
            program_id=str(integration.get("program_id") or ""),
            slice_id=str(integration.get("slice_id") or ""),
            family=str(integration.get("family") or ""),
            blocker_class="integration_failure",
            reason=(apply_result.stderr or apply_result.stdout or "Failed to apply bootstrap patch").strip(),
            metadata={"integration_id": integration["id"], "patch_path": patch_path},
        )
        await _set_integration_status(updated_integration, status="blocked", blocker_id=str(blocker.get("id") or ""))
        return {"processed": True, "integration_id": integration["id"], "status": "blocked", "blocker_id": blocker["id"]}

    completed = await _set_integration_status(
        updated_integration,
        status="replayed",
        metadata={
            **dict(updated_integration.get("metadata") or {}),
            "patch_path": patch_path,
            "replayed_at": _iso_now(),
        },
    )
    if queue_file.exists():
        queue_file.unlink(missing_ok=True)
    await mirror_bootstrap_lineage(slice_record or {})
    await state._write_snapshot_files()
    return {
        "processed": True,
        "integration_id": completed["id"],
        "status": "replayed",
        "patch_path": patch_path,
        "validation_status": validation_summary.get("status", ""),
    }


async def advance_bootstrap_supervisor_cycle(
    *,
    program_id: str = "",
    execute: bool = False,
    retry_blockers: bool = True,
    process_integrations: bool = True,
) -> dict[str, Any]:
    await state.ensure_bootstrap_state(force=True)
    actions: list[dict[str, Any]] = []

    if retry_blockers:
        retry_result = await retry_eligible_bootstrap_blockers(program_id=program_id)
        if retry_result["resolved_blockers"] or retry_result["reopened_slices"]:
            actions.append({"kind": "retry_blockers", **retry_result})

    approval_blocker_result = await ensure_pending_approval_blockers(program_id=program_id)
    if approval_blocker_result["created_blockers"]:
        actions.append({"kind": "approval_blockers", **approval_blocker_result})

    relay_result = await maybe_relay_exhausted_slices(program_id=program_id, execute=execute)
    if relay_result["relayed_slices"] or relay_result["blocked_relays"]:
        actions.append({"kind": "relay", **relay_result})

    if process_integrations:
        integration_result = await progress_bootstrap_integrations(execute=execute)
        if integration_result.get("processed"):
            actions.append({"kind": "integration", **integration_result})

    programs = await state.list_bootstrap_programs()
    if program_id:
        programs = [item for item in programs if str(item.get("id") or "") == program_id]

    active_program = next(
        (
            item
            for item in programs
            if str(item.get("status") or "") not in {"completed", "ready_for_takeover_check"}
        ),
        programs[0] if programs else None,
    )
    recommendation = None

    if active_program and active_program.get("next_slice"):
        next_slice = dict(active_program["next_slice"])
        host = await select_bootstrap_host_for_slice(next_slice)
        worktree = await prepare_bootstrap_worktree(next_slice, execute=execute)
        worktree_required = bool(worktree.get("worktree_required"))
        recommendation = {
            "program_id": str(active_program.get("id") or ""),
            "family": str(active_program.get("current_family") or ""),
            "slice_id": str(next_slice.get("id") or ""),
            "host_id": str((host or {}).get("id") or ""),
            "continuation_mode": str(next_slice.get("continuation_mode") or "external_bootstrap"),
            "worktree_required": worktree_required,
            "worktree_path": str(worktree.get("worktree_path") or ""),
            "base_ref": str(worktree.get("base_ref") or ""),
            "ready": bool(host),
        }
        if execute and host:
            claimed = await state.claim_bootstrap_slice(
                str(next_slice.get("id") or ""),
                host_id=str(host.get("id") or ""),
                current_ref=str(worktree.get("base_ref") or ""),
                worktree_path=str(worktree.get("worktree_path") or ""),
                next_step=(
                    f"Continue {next_slice.get('family', '')} via {host.get('id', '')} in the prepared worktree lane."
                    if worktree_required
                    else f"Continue {next_slice.get('family', '')} via {host.get('id', '')} in the bootstrap {str(worktree.get('execution_mode') or 'execution')} lane."
                ),
            )
            await write_bootstrap_handoff_contract(claimed)
            actions.append(
                {
                    "kind": "claim",
                    "slice_id": str(claimed.get("id") or ""),
                    "host_id": str(claimed.get("host_id") or ""),
                    "worktree_path": str(claimed.get("worktree_path") or ""),
                }
            )
            recommendation["claimed"] = True

    snapshot = await state.build_bootstrap_runtime_snapshot(include_snapshot_write=False)
    result = {
        "generated_at": _iso_now(),
        "active_program_id": str(active_program.get("id") or "") if active_program else "",
        "active_family": str(active_program.get("current_family") or "") if active_program else "",
        "recommendation": recommendation,
        "programs": programs,
        "status": snapshot,
        "actions": actions,
        "execute": execute,
    }
    await state._write_snapshot_files()
    return result


async def run_bootstrap_supervisor_loop(
    *,
    program_id: str = "",
    interval_seconds: int = 600,
    max_cycles: int | None = None,
    execute: bool = False,
    retry_blockers: bool = True,
    process_integrations: bool = True,
) -> dict[str, Any]:
    cycles: list[dict[str, Any]] = []
    count = 0
    while max_cycles is None or count < max_cycles:
        result = await advance_bootstrap_supervisor_cycle(
            program_id=program_id,
            execute=execute,
            retry_blockers=retry_blockers,
            process_integrations=process_integrations,
        )
        cycles.append(
            {
                "generated_at": result.get("generated_at", ""),
                "active_program_id": result.get("active_program_id", ""),
                "active_family": result.get("active_family", ""),
                "recommendation": result.get("recommendation"),
                "actions": result.get("actions", []),
            }
        )
        count += 1
        if max_cycles is not None and count >= max_cycles:
            break
        await asyncio.sleep(max(int(interval_seconds), 1))
    return {
        "loop_completed_at": _iso_now(),
        "cycle_count": count,
        "cycles": cycles,
        "last_cycle": cycles[-1] if cycles else None,
    }
