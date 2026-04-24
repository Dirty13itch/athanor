from __future__ import annotations

import time
from typing import Any

from .control_plane_registry import get_project_packet
from .model_governance import get_completion_program_registry

V1_QUEUE_FAMILIES = {
    "project_bootstrap",
    "builder",
    "research_audit",
    "maintenance",
    "review",
    "runtime_ops",
}

_FAMILY_BY_WORK_CLASS = {
    "approval": "review",
    "approval_review": "review",
    "async_backlog_execution": "builder",
    "coding": "builder",
    "coding_implementation": "builder",
    "feature": "builder",
    "migration": "builder",
    "multi_file_implementation": "builder",
    "private_automation": "maintenance",
    "project_bootstrap": "project_bootstrap",
    "project_build": "project_bootstrap",
    "repo_audit": "research_audit",
    "repo_wide_audit": "research_audit",
    "research": "research_audit",
    "research_synthesis": "research_audit",
    "runtime_ops": "runtime_ops",
    "runtime_repair": "runtime_ops",
    "scaffold": "project_bootstrap",
    "system_improvement": "maintenance",
    "maintenance": "maintenance",
}

_VERIFICATION_CONTRACT_BY_FAMILY = {
    "builder": "bounded_change_verification",
    "maintenance": "maintenance_proof",
    "project_bootstrap": "scaffold_integrity",
    "research_audit": "evidence_bundle",
    "review": "review_packet_present",
    "runtime_ops": "runtime_probe_or_packet",
}

_CLOSURE_RULE_BY_FAMILY = {
    "builder": "verified_result_required",
    "maintenance": "proof_or_review_required",
    "project_bootstrap": "result_or_review_required",
    "research_audit": "result_or_review_required",
    "review": "review_decision_required",
    "runtime_ops": "result_or_review_required",
}

_FAMILY_PRIORITY = {
    "project_bootstrap": 0,
    "builder": 1,
    "research_audit": 2,
    "maintenance": 3,
    "review": 4,
    "runtime_ops": 5,
}

_ROUTING_PRIORITY = {
    "sovereign_only": 0,
    "private_but_cloud_allowed": 1,
    "public_product_only": 2,
}

_STATUS_PRIORITY = {
    "ready": 0,
    "triaged": 1,
    "captured": 2,
    "scheduled": 3,
    "running": 4,
    "waiting_approval": 5,
    "blocked": 6,
    "failed": 7,
    "completed": 8,
    "archived": 9,
}


def is_v1_queue_family(family: str) -> bool:
    return _text(family) in V1_QUEUE_FAMILIES


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = _text(value).lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return bool(value)


def _metadata(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("metadata")
    if isinstance(value, dict):
        return dict(value)
    return {}


def _project_id(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    explicit = _text(record.get("project_id") or metadata.get("project_id"))
    if explicit:
        return explicit
    if _text(record.get("scope_type")) == "project":
        return _text(record.get("scope_id"))
    return ""


def _project_packet(project_id: str) -> dict[str, Any] | None:
    if not project_id:
        return None
    packet = get_project_packet(project_id)
    if packet:
        return dict(packet)
    return None


def _source_type(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    explicit = _text(record.get("source_type") or metadata.get("source_type"))
    if explicit:
        return explicit

    materialization_source = _text(record.get("materialization_source") or metadata.get("materialization_source"))
    if materialization_source == "bootstrap_program":
        return "bootstrap_follow_up"
    if materialization_source in {"project_packet_cadence", "maintenance_signal"}:
        return "program_signal"

    origin = _text(record.get("origin") or metadata.get("origin"))
    if origin in {"operator", "routing-console", "operator_inbox", "idea_garden", "task_api"}:
        return "operator_request"
    return origin or "operator_request"


def _source_ref(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(
        record.get("source_ref")
        or metadata.get("source_ref")
        or metadata.get("claim_id")
        or metadata.get("current_task_id")
        or metadata.get("linked_slice_id")
        or record.get("linked_idea_id")
    )


def _family(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    explicit = _text(record.get("family") or metadata.get("family"))
    if explicit in V1_QUEUE_FAMILIES:
        return explicit

    work_class = _text(record.get("work_class") or metadata.get("work_class") or metadata.get("task_class"))
    family = _FAMILY_BY_WORK_CLASS.get(work_class)
    if family:
        return family

    approval_mode = _text(record.get("approval_mode"))
    if approval_mode and approval_mode != "none":
        return "review"
    return "builder"


def _routing_class(record: dict[str, Any], metadata: dict[str, Any], packet: dict[str, Any] | None) -> str:
    explicit = _text(record.get("routing_class") or metadata.get("routing_class") or metadata.get("policy_class"))
    if explicit:
        return explicit
    if packet:
        return _text(packet.get("routing_class")) or "private_but_cloud_allowed"
    return "private_but_cloud_allowed"


def _verification_contract(record: dict[str, Any], metadata: dict[str, Any], family: str) -> str:
    explicit = _text(record.get("verification_contract") or metadata.get("verification_contract"))
    if explicit:
        return explicit
    return _VERIFICATION_CONTRACT_BY_FAMILY.get(family, "result_or_review")


def _closure_rule(record: dict[str, Any], metadata: dict[str, Any], family: str) -> str:
    explicit = _text(record.get("closure_rule") or metadata.get("closure_rule"))
    if explicit:
        return explicit
    return _CLOSURE_RULE_BY_FAMILY.get(family, "result_or_review_required")


def _materialization_source(record: dict[str, Any], metadata: dict[str, Any], source_type: str) -> str:
    explicit = _text(record.get("materialization_source") or metadata.get("materialization_source"))
    if explicit:
        return explicit
    if source_type == "bootstrap_follow_up":
        return "bootstrap_program"
    if source_type == "program_signal":
        return "project_packet_cadence"
    return "operator_request"


def _materialization_reason(record: dict[str, Any], metadata: dict[str, Any], source_type: str) -> str:
    explicit = _text(record.get("materialization_reason") or metadata.get("materialization_reason"))
    if explicit:
        return explicit
    if source_type == "bootstrap_follow_up":
        return "Bootstrap follow-up emitted governed queue work."
    if source_type == "program_signal":
        return "Recurring program emitted governed queue work."
    return "Operator captured governed queue work."


def _recurrence_program_id(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(
        record.get("recurrence_program_id")
        or metadata.get("recurrence_program_id")
        or metadata.get("program_id")
        or metadata.get("bootstrap_program_id")
    )


def _result_id(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("result_id") or metadata.get("result_id"))


def _review_id(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("review_id") or metadata.get("review_id") or metadata.get("approval_request_id"))


def _value_class(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("value_class") or metadata.get("value_class"))


def _deliverable_kind(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("deliverable_kind") or metadata.get("deliverable_kind"))


def _deliverable_refs(record: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    return _string_list(record.get("deliverable_refs")) or _string_list(metadata.get("deliverable_refs"))


def _beneficiary_surface(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("beneficiary_surface") or metadata.get("beneficiary_surface"))


def _acceptance_mode(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("acceptance_mode") or metadata.get("acceptance_mode"))


def _accepted_by(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("accepted_by") or metadata.get("accepted_by"))


def _accepted_at(record: dict[str, Any], metadata: dict[str, Any]) -> str:
    return _text(record.get("accepted_at") or metadata.get("accepted_at"))


def _acceptance_proof_refs(record: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    return _string_list(record.get("acceptance_proof_refs")) or _string_list(metadata.get("acceptance_proof_refs"))


def _operator_steered(record: dict[str, Any], metadata: dict[str, Any]) -> bool:
    return _boolish(record.get("operator_steered") if "operator_steered" in record else metadata.get("operator_steered"))


def _deliverable_acceptance_record(
    *,
    acceptance_mode: str,
    accepted_by: str,
    accepted_at: str,
    acceptance_proof_refs: list[str],
    operator_steered: bool,
) -> dict[str, Any] | None:
    if not any([acceptance_mode, accepted_by, accepted_at, acceptance_proof_refs, operator_steered]):
        return None
    return {
        "acceptance_mode": acceptance_mode or None,
        "accepted_by": accepted_by or None,
        "accepted_at": accepted_at or None,
        "acceptance_proof_refs": acceptance_proof_refs,
        "operator_steered": operator_steered,
        "accepted": bool(accepted_by and accepted_at and not operator_steered),
    }


def canonicalize_backlog_record(record: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(record)
    metadata = _metadata(canonical)
    project_id = _project_id(canonical, metadata)
    packet = _project_packet(project_id)
    source_type = _source_type(canonical, metadata)
    family = _family(canonical, metadata)
    routing_class = _routing_class(canonical, metadata, packet)
    verification_contract = _verification_contract(canonical, metadata, family)
    closure_rule = _closure_rule(canonical, metadata, family)
    materialization_source = _materialization_source(canonical, metadata, source_type)
    materialization_reason = _materialization_reason(canonical, metadata, source_type)
    source_ref = _source_ref(canonical, metadata)
    recurrence_program_id = _recurrence_program_id(canonical, metadata)
    result_id = _result_id(canonical, metadata)
    review_id = _review_id(canonical, metadata)
    value_class = _value_class(canonical, metadata)
    deliverable_kind = _deliverable_kind(canonical, metadata)
    deliverable_refs = _deliverable_refs(canonical, metadata)
    beneficiary_surface = _beneficiary_surface(canonical, metadata)
    acceptance_mode = _acceptance_mode(canonical, metadata)
    accepted_by = _accepted_by(canonical, metadata)
    accepted_at = _accepted_at(canonical, metadata)
    acceptance_proof_refs = _acceptance_proof_refs(canonical, metadata)
    operator_steered = _operator_steered(canonical, metadata)
    deliverable_acceptance_record = _deliverable_acceptance_record(
        acceptance_mode=acceptance_mode,
        accepted_by=accepted_by,
        accepted_at=accepted_at,
        acceptance_proof_refs=acceptance_proof_refs,
        operator_steered=operator_steered,
    )

    metadata.update(
        {
            "family": family,
            "project_id": project_id,
            "source_type": source_type,
            "source_ref": source_ref,
            "routing_class": routing_class,
            "verification_contract": verification_contract,
            "closure_rule": closure_rule,
            "materialization_source": materialization_source,
            "materialization_reason": materialization_reason,
            "recurrence_program_id": recurrence_program_id,
            "result_id": result_id,
            "review_id": review_id,
            "value_class": value_class,
            "deliverable_kind": deliverable_kind,
            "deliverable_refs": deliverable_refs,
            "beneficiary_surface": beneficiary_surface,
            "acceptance_mode": acceptance_mode,
            "accepted_by": accepted_by,
            "accepted_at": accepted_at,
            "acceptance_proof_refs": acceptance_proof_refs,
            "operator_steered": operator_steered,
        }
    )
    if deliverable_acceptance_record is not None:
        metadata["deliverable_acceptance_record"] = deliverable_acceptance_record

    canonical["family"] = family
    canonical["project_id"] = project_id
    canonical["source_type"] = source_type
    canonical["source_ref"] = source_ref
    canonical["routing_class"] = routing_class
    canonical["verification_contract"] = verification_contract
    canonical["closure_rule"] = closure_rule
    canonical["materialization_source"] = materialization_source
    canonical["materialization_reason"] = materialization_reason
    canonical["recurrence_program_id"] = recurrence_program_id
    canonical["result_id"] = result_id
    canonical["review_id"] = review_id
    canonical["value_class"] = value_class
    canonical["deliverable_kind"] = deliverable_kind
    canonical["deliverable_refs"] = deliverable_refs
    canonical["beneficiary_surface"] = beneficiary_surface
    canonical["acceptance_mode"] = acceptance_mode
    canonical["accepted_by"] = accepted_by
    canonical["accepted_at"] = accepted_at
    canonical["acceptance_proof_refs"] = acceptance_proof_refs
    canonical["operator_steered"] = operator_steered
    if deliverable_acceptance_record is not None:
        canonical["deliverable_acceptance_record"] = deliverable_acceptance_record
    canonical["metadata"] = metadata
    return canonical


def validate_backlog_transition(
    record: dict[str, Any],
    *,
    status: str,
    blocking_reason: str = "",
) -> dict[str, Any]:
    canonical = canonicalize_backlog_record(record)
    metadata = _metadata(canonical)
    result_id = _text(canonical.get("result_id") or metadata.get("latest_run_id") or metadata.get("execution_run_id"))
    review_id = _text(canonical.get("review_id"))
    failure_detail = _text(
        metadata.get("failure")
        or metadata.get("failure_detail")
        or metadata.get("last_error")
        or canonical.get("blocking_reason")
    )
    recovery_posture = _text(metadata.get("recovery_posture") or metadata.get("failure_repair") or metadata.get("recovery"))
    verification_passed = bool(
        metadata.get("verification_passed")
        or _text(metadata.get("verification_status")).lower() in {"passed", "verified", "green", "success"}
    )

    if status == "completed":
        if not result_id:
            raise ValueError("completed backlog items require linked result evidence")
        if _text(canonical.get("verification_contract")) and not verification_passed:
            raise ValueError("completed backlog items require result evidence and a passed verification contract")
    if status == "waiting_approval" and not review_id:
        raise ValueError("waiting_approval backlog items require linked review evidence")
    if status == "blocked" and not _text(blocking_reason or canonical.get("blocking_reason") or metadata.get("blocking_reason")):
        raise ValueError("blocked backlog items require a machine-readable blocking_reason")
    if status == "failed":
        if not failure_detail:
            raise ValueError("failed backlog items require failure detail")
        if not recovery_posture:
            raise ValueError("failed backlog items require failure detail and recovery posture")
    return canonical


def backlog_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    canonical = canonicalize_backlog_record(record)
    status = _text(canonical.get("status")).lower()
    priority = int(canonical.get("priority") or 0)
    routing_class = _text(canonical.get("routing_class"))
    family = _text(canonical.get("family"))
    approval_mode = _text(canonical.get("approval_mode"))
    proof_gap = 0 if _text(canonical.get("verification_contract")) else 1
    freshness = float(canonical.get("ready_at") or canonical.get("updated_at") or canonical.get("created_at") or 0.0)
    return (
        _STATUS_PRIORITY.get(status, 99),
        1 if approval_mode and approval_mode != "none" and status in {"captured", "triaged", "ready"} else 0,
        _ROUTING_PRIORITY.get(routing_class, 9),
        _FAMILY_PRIORITY.get(family, 99),
        proof_gap,
        -priority,
        freshness,
    )


def _dispatch_evidence_signature(record: dict[str, Any]) -> str:
    canonical = canonicalize_backlog_record(record)
    metadata = _metadata(canonical)
    proof_artifacts = sorted(
        {
            _text(item)
            for item in list(metadata.get("proof_artifacts") or [])
            if _text(item)
        }
    )
    failure = _text(
        metadata.get("failure")
        or metadata.get("failure_detail")
        or (metadata.get("failure_display") or {}).get("message")
    )
    recovery_posture = _text(metadata.get("recovery_posture") or metadata.get("failure_repair") or metadata.get("recovery"))
    failure_surface = failure
    if recovery_posture:
        failure_surface = f"{failure_surface}::{recovery_posture}" if failure_surface else f"recovery:{recovery_posture}"
    fields = [
        _text(canonical.get("status")),
        "",
        _text(canonical.get("review_id")),
        _text(canonical.get("blocking_reason")),
        _text(metadata.get("verification_status")),
        str(
            bool(
                metadata.get("verification_passed")
                or _text(metadata.get("verification_status")).lower() in {"passed", "verified", "green", "success"}
            )
        ).lower(),
        ",".join(proof_artifacts),
        failure_surface,
    ]
    return "|".join(fields)


def redispatch_block_reason(record: dict[str, Any]) -> str:
    canonical = canonicalize_backlog_record(record)
    metadata = _metadata(canonical)
    if bool(metadata.get("replay_allowed")) or "replay_allowed" in _text(canonical.get("closure_rule")):
        return ""

    policy = dict(get_completion_program_registry().get("automation_anti_spin_policy") or {})
    if not bool(policy.get("require_new_artifact_or_state_delta", True)):
        return ""

    history = [item for item in list(metadata.get("dispatch_history") or []) if isinstance(item, dict)]
    if not history:
        return ""

    signature = _dispatch_evidence_signature(canonical)
    now = time.time()
    threshold_12h = int(policy.get("same_task_claims_12h_threshold") or 2)
    threshold_24h = int(policy.get("same_task_claims_24h_threshold") or 3)

    matching_12h = 0
    matching_24h = 0
    for item in history:
        if _text(item.get("evidence_signature")) != signature:
            continue
        try:
            timestamp = float(item.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            timestamp = 0.0
        if timestamp >= now - (12 * 3600):
            matching_12h += 1
        if timestamp >= now - (24 * 3600):
            matching_24h += 1

    if matching_12h >= threshold_12h or matching_24h >= threshold_24h:
        return "Redispatch suppressed by completion-program anti-spin policy because no new evidence or state delta exists."
    return ""


def record_dispatch_event(record: dict[str, Any], *, reason: str) -> dict[str, Any]:
    canonical = canonicalize_backlog_record(record)
    metadata = _metadata(canonical)
    history = [item for item in list(metadata.get("dispatch_history") or []) if isinstance(item, dict)]
    history.append(
        {
            "timestamp": time.time(),
            "reason": _text(reason),
            "evidence_signature": _dispatch_evidence_signature(canonical),
        }
    )
    metadata["dispatch_history"] = history[-20:]
    canonical["metadata"] = metadata
    return canonical
