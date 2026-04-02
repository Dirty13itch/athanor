from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from .bootstrap_registry import get_foundry_proving_registry
from .control_plane_registry import get_project_packet
from .durable_state import (
    _as_datetime,
    _as_json_value,
    _as_timestamp,
    _execute,
    _fetch_all,
    get_durable_state_status,
)


def _repo_root() -> Path:
    preferred: Path | None = None
    for base in Path(__file__).resolve().parents:
        if base.joinpath("STATUS.md").exists() and base.joinpath("config", "automation-backbone").exists():
            return base
        if base.joinpath("config", "automation-backbone").exists():
            preferred = base
    if preferred is not None:
        return preferred
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


def foundry_root_path() -> Path:
    return _runtime_artifact_root() / "var" / "foundry"


def foundry_project_fallback_path(project_id: str) -> Path:
    safe_project_id = str(project_id or "").strip() or "unknown"
    return foundry_root_path() / "projects" / f"{safe_project_id}.json"


def _empty_project_fallback(project_id: str) -> dict[str, Any]:
    return {
        "project_id": str(project_id or "").strip(),
        "project_packet": None,
        "architecture_packet": None,
        "execution_slices": [],
        "foundry_runs": [],
        "deploy_candidates": [],
        "maintenance_runs": [],
        "rollback_events": [],
        "updated_at": datetime.now(timezone.utc).timestamp(),
    }


def _read_project_fallback(project_id: str) -> dict[str, Any]:
    path = foundry_project_fallback_path(project_id)
    if not path.exists():
        return _empty_project_fallback(project_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_project_fallback(project_id)
    if not isinstance(payload, dict):
        return _empty_project_fallback(project_id)
    fallback = _empty_project_fallback(project_id)
    fallback.update(payload)
    fallback["project_id"] = str(project_id or "").strip()
    return fallback


def _write_project_fallback(project_id: str, payload: dict[str, Any]) -> bool:
    path = foundry_project_fallback_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = _empty_project_fallback(project_id)
    serializable.update(payload)
    serializable["project_id"] = str(project_id or "").strip()
    serializable["updated_at"] = datetime.now(timezone.utc).timestamp()
    try:
        path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def _record_identity(record: dict[str, Any], primary_key: str) -> str:
    return str(record.get(primary_key) or record.get("id") or "").strip()


def _upsert_fallback_collection(
    project_id: str,
    collection_key: str,
    primary_key: str,
    record: dict[str, Any],
) -> bool:
    payload = _read_project_fallback(project_id)
    items = [dict(item) for item in payload.get(collection_key, []) if isinstance(item, dict)]
    identity = _record_identity(record, primary_key)
    updated: list[dict[str, Any]] = []
    replaced = False
    for item in items:
        if _record_identity(item, primary_key) == identity:
            updated.append(dict(record))
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(dict(record))
    updated.sort(
        key=lambda item: (
            float(item.get("updated_at") or item.get("created_at") or 0.0),
            _record_identity(item, primary_key),
        ),
        reverse=True,
    )
    payload[collection_key] = updated
    return _write_project_fallback(project_id, payload)


def _write_fallback_scalar(project_id: str, key: str, record: dict[str, Any] | None) -> bool:
    payload = _read_project_fallback(project_id)
    payload[key] = dict(record) if isinstance(record, dict) else None
    return _write_project_fallback(project_id, payload)


def _list_fallback_collection(project_id: str, collection_key: str, *, limit: int) -> list[dict[str, Any]]:
    payload = _read_project_fallback(project_id)
    items = [dict(item) for item in payload.get(collection_key, []) if isinstance(item, dict)]
    items.sort(
        key=lambda item: (
            float(item.get("updated_at") or item.get("created_at") or 0.0),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    return items[: max(int(limit), 1)]


def get_foundry_storage_status() -> dict[str, Any]:
    durable = get_durable_state_status()
    configured = bool(durable.get("configured"))
    ready = bool(durable.get("available")) and bool(durable.get("schema_ready"))
    return {
        "storage_mode": "athanor_postgres" if ready else "local_fallback",
        "postgres_configured": configured,
        "durable_ready": ready,
        "fallback_root": str(foundry_root_path()),
    }


def _current_git_ref(workspace_root: str) -> str:
    cwd = Path(str(workspace_root or "").strip() or str(_repo_root()))
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "HEAD"
    return str(result.stdout or "").strip() or "HEAD"


def _bootstrap_lineage_metadata(project_id: str, bootstrap_slice_id: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "bootstrap_program_id": "launch-readiness-bootstrap",
        "bootstrap_family": "foundry_completion",
        "bootstrap_slice_id": bootstrap_slice_id,
        "bootstrap_host": "codex_external",
        "continuation_mode": "external_bootstrap",
    }


def _build_default_architecture_packet(project_packet: dict[str, Any], proving_registry: dict[str, Any]) -> dict[str, Any]:
    project_id = str(project_packet.get("id") or "").strip()
    validators = list(proving_registry.get("validator_bundle") or [])
    return {
        "project_id": project_id,
        "service_shape": {
            "app": "projects/dashboard",
            "runtime": str(project_packet.get("runtime_target") or "cluster"),
            "primary_route": str(project_packet.get("primary_route") or "/projects"),
            "workspace_root": str(project_packet.get("workspace_root") or ""),
        },
        "data_contracts": [
            {"kind": "project_packet", "ref": str(proving_registry.get("project_packet_ref") or "")},
            {"kind": "architecture_packet", "ref": str(proving_registry.get("architecture_packet_ref") or "")},
            {"kind": "execution_slice", "ref": f"/v1/projects/{project_id}/slices"},
            {"kind": "foundry_run", "ref": f"/v1/projects/{project_id}/foundry/runs"},
            {"kind": "deploy_candidate", "ref": f"/v1/projects/{project_id}/deployments"},
            {"kind": "rollback_event", "ref": f"/v1/projects/{project_id}/rollbacks"},
        ],
        "auth_boundary": {
            "operator_auth_shared": True,
            "mutation_path": "operator_action_envelope",
            "sensitivity": str(project_packet.get("sensitivity") or "private"),
        },
        "deploy_shape": {
            "runtime_target": str(project_packet.get("runtime_target") or ""),
            "deploy_target": str(project_packet.get("deploy_target") or ""),
            "channel": "internal_preview",
        },
        "risk_notes": [
            "Durable foundry persistence is not configured in this repo runtime, so proving records fall back to the local foundry ledger until Postgres cutover is approved."
        ],
        "test_plan": validators or list(project_packet.get("acceptance_bundle") or []),
        "rollback_notes": [str(project_packet.get("rollback_contract") or "")] + list(
            proving_registry.get("rollback_target_requirements") or []
        ),
        "metadata": {
            **_bootstrap_lineage_metadata(project_id, "foundry-02-slice-execution"),
            "source": "foundry_proving_registry",
        },
        "approved_at": datetime.now(timezone.utc).timestamp(),
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp(),
    }


def _build_proving_slice_record(project_packet: dict[str, Any], proving_registry: dict[str, Any]) -> dict[str, Any]:
    project_id = str(project_packet.get("id") or "").strip()
    first_slice_packet = dict(proving_registry.get("first_proving_slice_packet") or {})
    worktree_path = str(project_packet.get("workspace_root") or _repo_root())
    return {
        "id": str(proving_registry.get("first_proving_slice_id") or f"{project_id}-proving-slice"),
        "project_id": project_id,
        "owner_agent": str(first_slice_packet.get("owner_agent") or "coding-agent"),
        "lane": str(first_slice_packet.get("lane") or "software_core_phase_1"),
        "base_sha": _current_git_ref(worktree_path),
        "worktree_path": worktree_path,
        "acceptance_target": "Foundry packet and deploy candidate path",
        "status": "completed",
        "metadata": {
            **_bootstrap_lineage_metadata(project_id, "foundry-02-slice-execution"),
            "objective": str(first_slice_packet.get("objective") or ""),
            "project_packet_ref": str(proving_registry.get("project_packet_ref") or ""),
            "architecture_packet_ref": str(proving_registry.get("architecture_packet_ref") or ""),
        },
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp(),
    }


def _build_proving_run_record(
    project_packet: dict[str, Any],
    proving_registry: dict[str, Any],
    slice_record: dict[str, Any],
) -> dict[str, Any]:
    project_id = str(project_packet.get("id") or "").strip()
    slice_id = str(slice_record.get("id") or "").strip()
    return {
        "id": f"foundry-run-{slice_id}",
        "project_id": project_id,
        "slice_id": slice_id,
        "execution_run_id": f"execution-{slice_id}",
        "status": "completed",
        "summary": "Athanor proving slice executed through governed foundry records.",
        "artifact_refs": [
            str(proving_registry.get("project_packet_ref") or ""),
            str(proving_registry.get("architecture_packet_ref") or ""),
            "reports/bootstrap/foundry-proving-packet.json",
            "reports/bootstrap/latest.json",
        ],
        "review_refs": list(proving_registry.get("validator_bundle") or []),
        "metadata": {
            **_bootstrap_lineage_metadata(project_id, "foundry-02-slice-execution"),
            "acceptance_bundle": list(project_packet.get("acceptance_bundle") or []),
        },
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp(),
        "completed_at": datetime.now(timezone.utc).timestamp(),
    }


def _build_proving_candidate_record(
    project_packet: dict[str, Any],
    proving_registry: dict[str, Any],
    slice_record: dict[str, Any],
    run_record: dict[str, Any],
) -> dict[str, Any]:
    project_id = str(project_packet.get("id") or "").strip()
    slice_id = str(slice_record.get("id") or "").strip()
    base_sha = str(slice_record.get("base_sha") or "HEAD").strip() or "HEAD"
    return {
        "id": f"candidate-{slice_id}",
        "project_id": project_id,
        "channel": "internal_preview",
        "artifact_refs": [
            str(proving_registry.get("project_packet_ref") or ""),
            str(proving_registry.get("architecture_packet_ref") or ""),
            str(run_record.get("id") or ""),
            "reports/bootstrap/foundry-proving-packet.json",
            "reports/bootstrap/latest.json",
        ],
        "env_contract": {
            "runtime_target": str(project_packet.get("runtime_target") or ""),
            "deploy_target": str(project_packet.get("deploy_target") or ""),
            "workspace_root": str(project_packet.get("workspace_root") or ""),
        },
        "smoke_results": {
            "status": "recorded",
            "acceptance_bundle": list(project_packet.get("acceptance_bundle") or []),
            "validator_bundle": list(proving_registry.get("validator_bundle") or []),
        },
        "rollback_target": {
            "kind": "packet_snapshot",
            "project_packet_ref": str(proving_registry.get("project_packet_ref") or ""),
            "architecture_packet_ref": str(proving_registry.get("architecture_packet_ref") or ""),
            "base_sha": base_sha,
            "workspace_root": str(project_packet.get("workspace_root") or ""),
        },
        "promotion_status": "pending",
        "metadata": {
            **_bootstrap_lineage_metadata(project_id, "foundry-03-candidate-evidence"),
            "candidate_evidence_requirements": list(proving_registry.get("candidate_evidence_requirements") or []),
        },
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp(),
        "promoted_at": 0.0,
    }


def _row_to_project_packet_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("project_id") or ""),
        "name": str(row.get("name") or ""),
        "stage": str(row.get("stage") or ""),
        "template": str(row.get("template") or ""),
        "class": str(row.get("project_class") or ""),
        "visibility": str(row.get("visibility") or ""),
        "sensitivity": str(row.get("sensitivity") or ""),
        "runtime_target": str(row.get("runtime_target") or ""),
        "deploy_target": str(row.get("deploy_target") or ""),
        "workspace_root": str(row.get("workspace_root") or ""),
        "primary_route": str(row.get("primary_route") or "/projects"),
        "owner_domain": str(row.get("owner_domain") or "product_foundry"),
        "operators": _as_json_value(row.get("operators_json"), default=[]),
        "agents": _as_json_value(row.get("agents_json"), default=[]),
        "acceptance_bundle": _as_json_value(row.get("acceptance_bundle_json"), default=[]),
        "rollback_contract": str(row.get("rollback_contract") or ""),
        "maintenance_cadence": str(row.get("maintenance_cadence") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


def _row_to_architecture_packet_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(row.get("project_id") or ""),
        "service_shape": _as_json_value(row.get("service_shape_json"), default={}),
        "data_contracts": _as_json_value(row.get("data_contracts_json"), default=[]),
        "auth_boundary": _as_json_value(row.get("auth_boundary_json"), default={}),
        "deploy_shape": _as_json_value(row.get("deploy_shape_json"), default={}),
        "risk_notes": _as_json_value(row.get("risk_notes_json"), default=[]),
        "test_plan": _as_json_value(row.get("test_plan_json"), default=[]),
        "rollback_notes": _as_json_value(row.get("rollback_notes_json"), default=[]),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "approved_at": _as_timestamp(row.get("approved_at")),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


def _row_to_foundry_run_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("foundry_run_id") or ""),
        "project_id": str(row.get("project_id") or ""),
        "slice_id": str(row.get("slice_id") or ""),
        "execution_run_id": str(row.get("execution_run_id") or ""),
        "status": str(row.get("status") or "queued"),
        "summary": str(row.get("summary") or ""),
        "artifact_refs": _as_json_value(row.get("artifact_refs_json"), default=[]),
        "review_refs": _as_json_value(row.get("review_refs_json"), default=[]),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
    }


def _row_to_execution_slice_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("slice_id") or ""),
        "project_id": str(row.get("project_id") or ""),
        "owner_agent": str(row.get("owner_agent") or ""),
        "lane": str(row.get("lane") or ""),
        "base_sha": str(row.get("base_sha") or ""),
        "worktree_path": str(row.get("worktree_path") or ""),
        "acceptance_target": str(row.get("acceptance_target") or ""),
        "status": str(row.get("status") or "planned"),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
    }


def _row_to_deploy_candidate_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("candidate_id") or ""),
        "project_id": str(row.get("project_id") or ""),
        "channel": str(row.get("channel") or ""),
        "artifact_refs": _as_json_value(row.get("artifact_refs_json"), default=[]),
        "env_contract": _as_json_value(row.get("env_contract_json"), default={}),
        "smoke_results": _as_json_value(row.get("smoke_results_json"), default={}),
        "rollback_target": _as_json_value(row.get("rollback_target_json"), default={}),
        "promotion_status": str(row.get("promotion_status") or "pending"),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "promoted_at": _as_timestamp(row.get("promoted_at")),
    }


def _row_to_maintenance_run_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("maintenance_id") or ""),
        "project_id": str(row.get("project_id") or ""),
        "kind": str(row.get("kind") or ""),
        "trigger": str(row.get("trigger") or ""),
        "status": str(row.get("status") or "queued"),
        "evidence_ref": str(row.get("evidence_ref") or ""),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
        "updated_at": _as_timestamp(row.get("updated_at")),
        "completed_at": _as_timestamp(row.get("completed_at")),
    }


def _row_to_rollback_event_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("rollback_event_id") or ""),
        "project_id": str(row.get("project_id") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "reason": str(row.get("reason") or ""),
        "rollback_target": _as_json_value(row.get("rollback_target_json"), default={}),
        "status": str(row.get("status") or "recorded"),
        "metadata": _as_json_value(row.get("metadata_json"), default={}),
        "created_at": _as_timestamp(row.get("created_at")),
    }


async def upsert_project_packet_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    project_id = str(record.get("id") or "")
    query = """
        INSERT INTO foundry.project_packets (
            project_id,
            name,
            stage,
            template,
            project_class,
            visibility,
            sensitivity,
            runtime_target,
            deploy_target,
            workspace_root,
            primary_route,
            owner_domain,
            operators_json,
            agents_json,
            acceptance_bundle_json,
            rollback_contract,
            maintenance_cadence,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s, %s
        )
        ON CONFLICT (project_id) DO UPDATE SET
            name = EXCLUDED.name,
            stage = EXCLUDED.stage,
            template = EXCLUDED.template,
            project_class = EXCLUDED.project_class,
            visibility = EXCLUDED.visibility,
            sensitivity = EXCLUDED.sensitivity,
            runtime_target = EXCLUDED.runtime_target,
            deploy_target = EXCLUDED.deploy_target,
            workspace_root = EXCLUDED.workspace_root,
            primary_route = EXCLUDED.primary_route,
            owner_domain = EXCLUDED.owner_domain,
            operators_json = EXCLUDED.operators_json,
            agents_json = EXCLUDED.agents_json,
            acceptance_bundle_json = EXCLUDED.acceptance_bundle_json,
            rollback_contract = EXCLUDED.rollback_contract,
            maintenance_cadence = EXCLUDED.maintenance_cadence,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = EXCLUDED.updated_at
    """
    params = (
        project_id,
        str(record.get("name") or ""),
        str(record.get("stage") or "scaffold"),
        str(record.get("template") or ""),
        str(record.get("class") or ""),
        str(record.get("visibility") or "private"),
        str(record.get("sensitivity") or "private"),
        str(record.get("runtime_target") or ""),
        str(record.get("deploy_target") or ""),
        str(record.get("workspace_root") or ""),
        str(record.get("primary_route") or "/projects"),
        str(record.get("owner_domain") or "product_foundry"),
        json.dumps(record.get("operators") or []),
        json.dumps(record.get("agents") or []),
        json.dumps(record.get("acceptance_bundle") or []),
        str(record.get("rollback_contract") or ""),
        str(record.get("maintenance_cadence") or ""),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _write_fallback_scalar(
        project_id,
        "project_packet",
        {
            "id": project_id,
            "name": str(record.get("name") or ""),
            "stage": str(record.get("stage") or "scaffold"),
            "template": str(record.get("template") or ""),
            "class": str(record.get("class") or ""),
            "visibility": str(record.get("visibility") or "private"),
            "sensitivity": str(record.get("sensitivity") or "private"),
            "runtime_target": str(record.get("runtime_target") or ""),
            "deploy_target": str(record.get("deploy_target") or ""),
            "workspace_root": str(record.get("workspace_root") or ""),
            "primary_route": str(record.get("primary_route") or "/projects"),
            "owner_domain": str(record.get("owner_domain") or "product_foundry"),
            "operators": list(record.get("operators") or []),
            "agents": list(record.get("agents") or []),
            "acceptance_bundle": list(record.get("acceptance_bundle") or []),
            "rollback_contract": str(record.get("rollback_contract") or ""),
            "maintenance_cadence": str(record.get("maintenance_cadence") or ""),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
        },
    )
    return bool(durable_saved or fallback_saved)


async def fetch_project_packet_record(project_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            project_id,
            name,
            stage,
            template,
            project_class,
            visibility,
            sensitivity,
            runtime_target,
            deploy_target,
            workspace_root,
            primary_route,
            owner_domain,
            operators_json,
            agents_json,
            acceptance_bundle_json,
            rollback_contract,
            maintenance_cadence,
            metadata_json,
            created_at,
            updated_at
        FROM foundry.project_packets
        WHERE project_id = %s
        """,
        (project_id,),
    )
    if rows:
        return _row_to_project_packet_record(rows[0])

    fallback_packet = _read_project_fallback(project_id).get("project_packet")
    if isinstance(fallback_packet, dict) and str(fallback_packet.get("id") or "").strip():
        return dict(fallback_packet)

    seeded = get_project_packet(project_id)
    if not seeded:
        return None

    record = {
        "id": str(seeded.get("id") or project_id),
        "name": str(seeded.get("name") or project_id),
        "stage": str(seeded.get("stage") or "scaffold"),
        "template": str(seeded.get("template") or ""),
        "class": str(seeded.get("class") or ""),
        "visibility": str(seeded.get("visibility") or "private"),
        "sensitivity": str(seeded.get("sensitivity") or "private"),
        "runtime_target": str(seeded.get("runtime_target") or ""),
        "deploy_target": str(seeded.get("deploy_target") or ""),
        "workspace_root": str(seeded.get("workspace_root") or ""),
        "primary_route": str(seeded.get("primary_route") or "/projects"),
        "owner_domain": str(seeded.get("owner_domain") or "product_foundry"),
        "operators": list(seeded.get("operators") or []),
        "agents": list(seeded.get("agents") or []),
        "acceptance_bundle": list(seeded.get("acceptance_bundle") or []),
        "rollback_contract": str(seeded.get("rollback_contract") or ""),
        "maintenance_cadence": str(seeded.get("maintenance_cadence") or ""),
        "metadata": {},
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp(),
    }
    await upsert_project_packet_record(record)
    return record


async def upsert_architecture_packet_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.architecture_packets (
            project_id,
            service_shape_json,
            data_contracts_json,
            auth_boundary_json,
            deploy_shape_json,
            risk_notes_json,
            test_plan_json,
            rollback_notes_json,
            metadata_json,
            approved_at,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
            %s::jsonb, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (project_id) DO UPDATE SET
            service_shape_json = EXCLUDED.service_shape_json,
            data_contracts_json = EXCLUDED.data_contracts_json,
            auth_boundary_json = EXCLUDED.auth_boundary_json,
            deploy_shape_json = EXCLUDED.deploy_shape_json,
            risk_notes_json = EXCLUDED.risk_notes_json,
            test_plan_json = EXCLUDED.test_plan_json,
            rollback_notes_json = EXCLUDED.rollback_notes_json,
            metadata_json = EXCLUDED.metadata_json,
            approved_at = EXCLUDED.approved_at,
            updated_at = EXCLUDED.updated_at
    """
    params = (
        project_id,
        json.dumps(record.get("service_shape") or {}),
        json.dumps(record.get("data_contracts") or []),
        json.dumps(record.get("auth_boundary") or {}),
        json.dumps(record.get("deploy_shape") or {}),
        json.dumps(record.get("risk_notes") or []),
        json.dumps(record.get("test_plan") or []),
        json.dumps(record.get("rollback_notes") or []),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("approved_at")),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _write_fallback_scalar(
        project_id,
        "architecture_packet",
        {
            "project_id": project_id,
            "service_shape": dict(record.get("service_shape") or {}),
            "data_contracts": list(record.get("data_contracts") or []),
            "auth_boundary": dict(record.get("auth_boundary") or {}),
            "deploy_shape": dict(record.get("deploy_shape") or {}),
            "risk_notes": list(record.get("risk_notes") or []),
            "test_plan": list(record.get("test_plan") or []),
            "rollback_notes": list(record.get("rollback_notes") or []),
            "metadata": dict(record.get("metadata") or {}),
            "approved_at": _as_timestamp(_as_datetime(record.get("approved_at")) or record.get("approved_at")),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
        },
    )
    return bool(durable_saved or fallback_saved)


async def fetch_architecture_packet_record(project_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            project_id,
            service_shape_json,
            data_contracts_json,
            auth_boundary_json,
            deploy_shape_json,
            risk_notes_json,
            test_plan_json,
            rollback_notes_json,
            metadata_json,
            approved_at,
            created_at,
            updated_at
        FROM foundry.architecture_packets
        WHERE project_id = %s
        """,
        (project_id,),
    )
    if not rows:
        fallback_packet = _read_project_fallback(project_id).get("architecture_packet")
        if isinstance(fallback_packet, dict) and str(fallback_packet.get("project_id") or "").strip():
            return dict(fallback_packet)
        return None
    return _row_to_architecture_packet_record(rows[0])


async def upsert_execution_slice_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    slice_id = str(record.get("id") or f"slice-{uuid.uuid4().hex[:8]}")
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.execution_slices (
            slice_id,
            project_id,
            owner_agent,
            lane,
            base_sha,
            worktree_path,
            acceptance_target,
            status,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
        )
        ON CONFLICT (slice_id) DO UPDATE SET
            project_id = EXCLUDED.project_id,
            owner_agent = EXCLUDED.owner_agent,
            lane = EXCLUDED.lane,
            base_sha = EXCLUDED.base_sha,
            worktree_path = EXCLUDED.worktree_path,
            acceptance_target = EXCLUDED.acceptance_target,
            status = EXCLUDED.status,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = EXCLUDED.updated_at
    """
    params = (
        slice_id,
        project_id,
        str(record.get("owner_agent") or ""),
        str(record.get("lane") or ""),
        str(record.get("base_sha") or ""),
        str(record.get("worktree_path") or ""),
        str(record.get("acceptance_target") or ""),
        str(record.get("status") or "planned"),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _upsert_fallback_collection(
        project_id,
        "execution_slices",
        "slice_id",
        {
            "id": slice_id,
            "project_id": project_id,
            "owner_agent": str(record.get("owner_agent") or ""),
            "lane": str(record.get("lane") or ""),
            "base_sha": str(record.get("base_sha") or ""),
            "worktree_path": str(record.get("worktree_path") or ""),
            "acceptance_target": str(record.get("acceptance_target") or ""),
            "status": str(record.get("status") or "planned"),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
        },
    )
    return bool(durable_saved or fallback_saved)


async def list_execution_slice_records(project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        """
        SELECT
            slice_id,
            project_id,
            owner_agent,
            lane,
            base_sha,
            worktree_path,
            acceptance_target,
            status,
            metadata_json,
            created_at,
            updated_at
        FROM foundry.execution_slices
        WHERE project_id = %s
        ORDER BY updated_at DESC, slice_id DESC
        LIMIT %s
        """,
        (project_id, max(int(limit), 1)),
    )
    if rows:
        return [_row_to_execution_slice_record(row) for row in rows]
    return _list_fallback_collection(project_id, "execution_slices", limit=limit)


async def upsert_foundry_run_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    run_id = str(record.get("id") or f"foundry-run-{uuid.uuid4().hex[:8]}")
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.foundry_runs (
            foundry_run_id,
            project_id,
            slice_id,
            execution_run_id,
            status,
            summary,
            artifact_refs_json,
            review_refs_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (foundry_run_id) DO UPDATE SET
            project_id = EXCLUDED.project_id,
            slice_id = EXCLUDED.slice_id,
            execution_run_id = EXCLUDED.execution_run_id,
            status = EXCLUDED.status,
            summary = EXCLUDED.summary,
            artifact_refs_json = EXCLUDED.artifact_refs_json,
            review_refs_json = EXCLUDED.review_refs_json,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = EXCLUDED.updated_at,
            completed_at = EXCLUDED.completed_at
    """
    params = (
        run_id,
        project_id,
        str(record.get("slice_id") or ""),
        str(record.get("execution_run_id") or ""),
        str(record.get("status") or "queued"),
        str(record.get("summary") or ""),
        json.dumps(record.get("artifact_refs") or []),
        json.dumps(record.get("review_refs") or []),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
        _as_datetime(record.get("completed_at")),
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _upsert_fallback_collection(
        project_id,
        "foundry_runs",
        "foundry_run_id",
        {
            "id": run_id,
            "project_id": project_id,
            "slice_id": str(record.get("slice_id") or ""),
            "execution_run_id": str(record.get("execution_run_id") or ""),
            "status": str(record.get("status") or "queued"),
            "summary": str(record.get("summary") or ""),
            "artifact_refs": list(record.get("artifact_refs") or []),
            "review_refs": list(record.get("review_refs") or []),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
            "completed_at": _as_timestamp(_as_datetime(record.get("completed_at")) or record.get("completed_at")),
        },
    )
    return bool(durable_saved or fallback_saved)


async def list_foundry_run_records(project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        """
        SELECT
            foundry_run_id,
            project_id,
            slice_id,
            execution_run_id,
            status,
            summary,
            artifact_refs_json,
            review_refs_json,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM foundry.foundry_runs
        WHERE project_id = %s
        ORDER BY updated_at DESC, foundry_run_id DESC
        LIMIT %s
        """,
        (project_id, max(int(limit), 1)),
    )
    if rows:
        return [_row_to_foundry_run_record(row) for row in rows]
    return _list_fallback_collection(project_id, "foundry_runs", limit=limit)


async def upsert_maintenance_run_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    maintenance_id = str(record.get("id") or f"maintenance-{uuid.uuid4().hex[:8]}")
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.maintenance_runs (
            maintenance_id,
            project_id,
            kind,
            trigger,
            status,
            evidence_ref,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (maintenance_id) DO UPDATE SET
            project_id = EXCLUDED.project_id,
            kind = EXCLUDED.kind,
            trigger = EXCLUDED.trigger,
            status = EXCLUDED.status,
            evidence_ref = EXCLUDED.evidence_ref,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = EXCLUDED.updated_at,
            completed_at = EXCLUDED.completed_at
    """
    params = (
        maintenance_id,
        project_id,
        str(record.get("kind") or ""),
        str(record.get("trigger") or ""),
        str(record.get("status") or "queued"),
        str(record.get("evidence_ref") or ""),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
        _as_datetime(record.get("completed_at")),
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _upsert_fallback_collection(
        project_id,
        "maintenance_runs",
        "maintenance_id",
        {
            "id": maintenance_id,
            "project_id": project_id,
            "kind": str(record.get("kind") or ""),
            "trigger": str(record.get("trigger") or ""),
            "status": str(record.get("status") or "queued"),
            "evidence_ref": str(record.get("evidence_ref") or ""),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
            "completed_at": _as_timestamp(_as_datetime(record.get("completed_at")) or record.get("completed_at")),
        },
    )
    return bool(durable_saved or fallback_saved)


async def list_maintenance_run_records(project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        """
        SELECT
            maintenance_id,
            project_id,
            kind,
            trigger,
            status,
            evidence_ref,
            metadata_json,
            created_at,
            updated_at,
            completed_at
        FROM foundry.maintenance_runs
        WHERE project_id = %s
        ORDER BY updated_at DESC, maintenance_id DESC
        LIMIT %s
        """,
        (project_id, max(int(limit), 1)),
    )
    if rows:
        return [_row_to_maintenance_run_record(row) for row in rows]
    return _list_fallback_collection(project_id, "maintenance_runs", limit=limit)


async def upsert_deploy_candidate_record(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    candidate_id = str(record.get("id") or f"candidate-{uuid.uuid4().hex[:8]}")
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.deploy_candidates (
            candidate_id,
            project_id,
            channel,
            artifact_refs_json,
            env_contract_json,
            smoke_results_json,
            rollback_target_json,
            promotion_status,
            metadata_json,
            created_at,
            updated_at,
            promoted_at
        )
        VALUES (
            %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (candidate_id) DO UPDATE SET
            project_id = EXCLUDED.project_id,
            channel = EXCLUDED.channel,
            artifact_refs_json = EXCLUDED.artifact_refs_json,
            env_contract_json = EXCLUDED.env_contract_json,
            smoke_results_json = EXCLUDED.smoke_results_json,
            rollback_target_json = EXCLUDED.rollback_target_json,
            promotion_status = EXCLUDED.promotion_status,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = EXCLUDED.updated_at,
            promoted_at = EXCLUDED.promoted_at
    """
    params = (
        candidate_id,
        project_id,
        str(record.get("channel") or "internal_preview"),
        json.dumps(record.get("artifact_refs") or []),
        json.dumps(record.get("env_contract") or {}),
        json.dumps(record.get("smoke_results") or {}),
        json.dumps(record.get("rollback_target") or {}),
        str(record.get("promotion_status") or "pending"),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or now,
        _as_datetime(record.get("updated_at")) or now,
        _as_datetime(record.get("promoted_at")),
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _upsert_fallback_collection(
        project_id,
        "deploy_candidates",
        "candidate_id",
        {
            "id": candidate_id,
            "project_id": project_id,
            "channel": str(record.get("channel") or "internal_preview"),
            "artifact_refs": list(record.get("artifact_refs") or []),
            "env_contract": dict(record.get("env_contract") or {}),
            "smoke_results": dict(record.get("smoke_results") or {}),
            "rollback_target": dict(record.get("rollback_target") or {}),
            "promotion_status": str(record.get("promotion_status") or "pending"),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": (_as_datetime(record.get("created_at")) or now).timestamp(),
            "updated_at": (_as_datetime(record.get("updated_at")) or now).timestamp(),
            "promoted_at": _as_timestamp(_as_datetime(record.get("promoted_at")) or record.get("promoted_at")),
        },
    )
    return bool(durable_saved or fallback_saved)


async def fetch_deploy_candidate_record(project_id: str, candidate_id: str) -> dict[str, Any] | None:
    rows = await _fetch_all(
        """
        SELECT
            candidate_id,
            project_id,
            channel,
            artifact_refs_json,
            env_contract_json,
            smoke_results_json,
            rollback_target_json,
            promotion_status,
            metadata_json,
            created_at,
            updated_at,
            promoted_at
        FROM foundry.deploy_candidates
        WHERE project_id = %s AND candidate_id = %s
        """,
        (project_id, candidate_id),
    )
    if not rows:
        for item in _list_fallback_collection(project_id, "deploy_candidates", limit=200):
            if str(item.get("id") or "") == candidate_id:
                return dict(item)
        return None
    return _row_to_deploy_candidate_record(rows[0])


async def list_deploy_candidate_records(project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        """
        SELECT
            candidate_id,
            project_id,
            channel,
            artifact_refs_json,
            env_contract_json,
            smoke_results_json,
            rollback_target_json,
            promotion_status,
            metadata_json,
            created_at,
            updated_at,
            promoted_at
        FROM foundry.deploy_candidates
        WHERE project_id = %s
        ORDER BY updated_at DESC, candidate_id DESC
        LIMIT %s
        """,
        (project_id, max(int(limit), 1)),
    )
    if rows:
        return [_row_to_deploy_candidate_record(row) for row in rows]
    return _list_fallback_collection(project_id, "deploy_candidates", limit=limit)


async def record_rollback_event(record: dict[str, Any]) -> bool:
    rollback_id = str(record.get("id") or f"rollback-{uuid.uuid4().hex[:8]}")
    project_id = str(record.get("project_id") or "")
    query = """
        INSERT INTO foundry.rollback_events (
            rollback_event_id,
            project_id,
            candidate_id,
            reason,
            rollback_target_json,
            status,
            metadata_json,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
        ON CONFLICT (rollback_event_id) DO UPDATE SET
            candidate_id = EXCLUDED.candidate_id,
            reason = EXCLUDED.reason,
            rollback_target_json = EXCLUDED.rollback_target_json,
            status = EXCLUDED.status,
            metadata_json = EXCLUDED.metadata_json,
            created_at = EXCLUDED.created_at
    """
    params = (
        rollback_id,
        project_id,
        str(record.get("candidate_id") or ""),
        str(record.get("reason") or ""),
        json.dumps(record.get("rollback_target") or {}),
        str(record.get("status") or "recorded"),
        json.dumps(record.get("metadata") or {}),
        _as_datetime(record.get("created_at")) or datetime.now(timezone.utc),
    )
    durable_saved = await _execute(query, params)
    fallback_saved = _upsert_fallback_collection(
        project_id,
        "rollback_events",
        "rollback_event_id",
        {
            "id": rollback_id,
            "project_id": project_id,
            "candidate_id": str(record.get("candidate_id") or ""),
            "reason": str(record.get("reason") or ""),
            "rollback_target": dict(record.get("rollback_target") or {}),
            "status": str(record.get("status") or "recorded"),
            "metadata": dict(record.get("metadata") or {}),
            "created_at": _as_timestamp(_as_datetime(record.get("created_at")) or record.get("created_at")),
        },
    )
    return bool(durable_saved or fallback_saved)


async def list_rollback_event_records(project_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        """
        SELECT
            rollback_event_id,
            project_id,
            candidate_id,
            reason,
            rollback_target_json,
            status,
            metadata_json,
            created_at
        FROM foundry.rollback_events
        WHERE project_id = %s
        ORDER BY created_at DESC, rollback_event_id DESC
        LIMIT %s
        """,
        (project_id, max(int(limit), 1)),
    )
    if rows:
        return [_row_to_rollback_event_record(row) for row in rows]
    return _list_fallback_collection(project_id, "rollback_events", limit=limit)


async def materialize_foundry_proving_stage(project_id: str, *, stage: str) -> dict[str, Any]:
    proving_registry = get_foundry_proving_registry()
    configured_project_id = str(proving_registry.get("project_id") or "").strip()
    if not configured_project_id or project_id != configured_project_id:
        raise ValueError(f"Foundry proving is only configured for '{configured_project_id or 'athanor'}'")

    if stage not in {"slice_execution", "candidate_evidence", "rollback_record"}:
        raise ValueError(f"Unsupported proving stage '{stage}'")

    project_packet = await fetch_project_packet_record(project_id)
    if not project_packet:
        raise ValueError(f"Project packet '{project_id}' not found")

    architecture_packet = await fetch_architecture_packet_record(project_id)
    if not architecture_packet:
        architecture_packet = _build_default_architecture_packet(project_packet, proving_registry)
        await upsert_architecture_packet_record(architecture_packet)
        architecture_packet = await fetch_architecture_packet_record(project_id) or architecture_packet

    first_slice_id = str(proving_registry.get("first_proving_slice_id") or "").strip()
    slices = await list_execution_slice_records(project_id, limit=200)
    slice_record = next((item for item in slices if str(item.get("id") or "") == first_slice_id), None)
    if not slice_record:
        slice_record = _build_proving_slice_record(project_packet, proving_registry)
        await upsert_execution_slice_record(slice_record)
        slices = await list_execution_slice_records(project_id, limit=200)
        slice_record = next((item for item in slices if str(item.get("id") or "") == first_slice_id), None) or slice_record

    runs = await list_foundry_run_records(project_id, limit=200)
    run_record = next(
        (
            item
            for item in runs
            if str(item.get("slice_id") or "") == first_slice_id
            or str(item.get("id") or "") == f"foundry-run-{first_slice_id}"
        ),
        None,
    )
    if not run_record:
        run_record = _build_proving_run_record(project_packet, proving_registry, slice_record)
        await upsert_foundry_run_record(run_record)
        runs = await list_foundry_run_records(project_id, limit=200)
        run_record = next(
            (
                item
                for item in runs
                if str(item.get("slice_id") or "") == first_slice_id
                or str(item.get("id") or "") == f"foundry-run-{first_slice_id}"
            ),
            None,
        ) or run_record

    candidate_record: dict[str, Any] | None = None
    if stage in {"candidate_evidence", "rollback_record"}:
        candidate_id = f"candidate-{first_slice_id}"
        candidates = await list_deploy_candidate_records(project_id, limit=200)
        candidate_record = next((item for item in candidates if str(item.get("id") or "") == candidate_id), None)
        if not candidate_record:
            candidate_record = _build_proving_candidate_record(project_packet, proving_registry, slice_record, run_record)
            await upsert_deploy_candidate_record(candidate_record)
            candidates = await list_deploy_candidate_records(project_id, limit=200)
            candidate_record = next((item for item in candidates if str(item.get("id") or "") == candidate_id), None) or candidate_record

    rollback_event: dict[str, Any] | None = None
    if stage == "rollback_record":
        rollback_events = await list_rollback_event_records(project_id, limit=200)
        rollback_event = next(
            (
                item
                for item in rollback_events
                if str(item.get("candidate_id") or "") == str(candidate_record.get("id") if candidate_record else "")
            ),
            None,
        )
        if not rollback_event and candidate_record:
            rollback_event = {
                "id": f"rollback-{first_slice_id}",
                "project_id": project_id,
                "candidate_id": str(candidate_record.get("id") or ""),
                "reason": "Recorded bounded rollback proof for the Athanor proving candidate.",
                "rollback_target": dict(candidate_record.get("rollback_target") or {}),
                "status": "recorded",
                "metadata": {
                    **_bootstrap_lineage_metadata(project_id, "foundry-04-promotion-or-rollback"),
                    "decision": "rollback_record",
                },
                "created_at": datetime.now(timezone.utc).timestamp(),
            }
            await record_rollback_event(rollback_event)
            rollback_events = await list_rollback_event_records(project_id, limit=200)
            rollback_event = next(
                (
                    item
                    for item in rollback_events
                    if str(item.get("candidate_id") or "") == str(candidate_record.get("id") or "")
                ),
                None,
            ) or rollback_event

    return {
        "project_id": project_id,
        "stage": stage,
        "storage": get_foundry_storage_status(),
        "packet": project_packet,
        "architecture": architecture_packet,
        "slice": slice_record,
        "run": run_record,
        "candidate": candidate_record,
        "rollback_event": rollback_event,
    }
