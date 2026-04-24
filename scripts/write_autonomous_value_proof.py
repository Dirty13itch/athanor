#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from write_value_throughput_scorecard import (
    _canonical_backlog_record,
    _clear_degraded_prefixes,
    _list_backlog_records,
    _load_backlog_via_api,
    _load_governed_dispatch_truth,
    _safe_load,
    _text,
    _verification_passed,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomous-value-proof.json"
STATUS_MD_PATH = REPO_ROOT / "docs" / "operations" / "AUTONOMOUS-VALUE-STATUS.md"
OPERATOR_VALUE_REQUIRED = 3
OPERATOR_VALUE_FAMILY_REQUIRED = 2
PRODUCT_VALUE_REQUIRED = 2
PRODUCT_VISIBLE_SURFACES = {"dashboard", "builder", "builder_front_door"}
FAILURE_CLASSES = [
    "bookkeeping_only",
    "control_plane_only",
    "operator_steered",
    "verification_passed_but_no_deliverable",
    "deliverable_present_but_not_accepted",
]
CONTROL_PLANE_REF_TOKENS = (
    "steady-state-status",
    "blocker-map",
    "continuity",
    "result-evidence-ledger",
    "runtime-parity",
)


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_against_existing(payload: dict[str, Any], current_json: str) -> tuple[str, str]:
    comparable_payload = dict(payload)
    try:
        existing_payload = json.loads(current_json) if current_json.strip() else {}
    except json.JSONDecodeError:
        existing_payload = {}
    existing_generated_at = _text(existing_payload.get("generated_at")) if isinstance(existing_payload, dict) else ""
    if existing_generated_at:
        comparable_payload["generated_at"] = existing_generated_at
    return _json_render(comparable_payload), _markdown(comparable_payload)


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


def _verification_outcome(record: dict[str, Any]) -> str:
    if _verification_passed(record):
        return "passed"
    status = _text(record.get("status")).lower()
    if status == "waiting_approval" and _text(record.get("review_id")):
        return "review_packet_present"
    metadata = dict(record.get("metadata") or {})
    return _text(metadata.get("verification_status")).lower() or "missing"


def _acceptance_outcome(
    *,
    accepted_by: str,
    accepted_at: str,
    operator_steered: bool,
) -> str:
    if operator_steered:
        return "disqualified"
    if accepted_by and accepted_at:
        return "accepted"
    return "pending"


def _is_bookkeeping_only(deliverable_refs: list[str]) -> bool:
    if not deliverable_refs:
        return False
    normalized = [ref.lower() for ref in deliverable_refs]
    return all(any(token in ref for token in CONTROL_PLANE_REF_TOKENS) for ref in normalized)


def _entry_from_record(record: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(record.get("metadata") or {})
    accepted_by = _text(record.get("accepted_by") or metadata.get("accepted_by"))
    accepted_at = _text(record.get("accepted_at") or metadata.get("accepted_at"))
    acceptance_mode = _text(record.get("acceptance_mode") or metadata.get("acceptance_mode"))
    acceptance_proof_refs = _string_list(record.get("acceptance_proof_refs")) or _string_list(
        metadata.get("acceptance_proof_refs")
    )
    operator_steered = _boolish(record.get("operator_steered") if "operator_steered" in record else metadata.get("operator_steered"))
    deliverable_refs = _string_list(record.get("deliverable_refs")) or _string_list(metadata.get("deliverable_refs"))
    packet_id = _text(record.get("result_id") or record.get("review_id"))
    verification_outcome = _verification_outcome(record)
    entry = {
        "packet_id": packet_id,
        "backlog_id": _text(record.get("id")),
        "workstream_or_task_id": _text(
            metadata.get("latest_task_id")
            or record.get("source_ref")
            or metadata.get("source_ref")
            or record.get("id")
        ),
        "title": _text(record.get("title")),
        "family": _text(record.get("family")) or "unknown",
        "project_id": _text(record.get("project_id")) or "unscoped",
        "status": _text(record.get("status")).lower() or "unknown",
        "value_class": _text(record.get("value_class") or metadata.get("value_class")),
        "deliverable_kind": _text(record.get("deliverable_kind") or metadata.get("deliverable_kind")),
        "deliverable_refs": deliverable_refs,
        "beneficiary_surface": _text(record.get("beneficiary_surface") or metadata.get("beneficiary_surface")),
        "verification_outcome": verification_outcome,
        "acceptance_mode": acceptance_mode,
        "acceptance_outcome": _acceptance_outcome(
            accepted_by=accepted_by,
            accepted_at=accepted_at,
            operator_steered=operator_steered,
        ),
        "accepted_by": accepted_by or None,
        "accepted_at": accepted_at or None,
        "acceptance_proof_refs": acceptance_proof_refs,
        "fully_autonomous": not operator_steered,
        "operator_steered": operator_steered,
        "deliverable_acceptance_record": {
            "acceptance_mode": acceptance_mode or None,
            "accepted_by": accepted_by or None,
            "accepted_at": accepted_at or None,
            "acceptance_proof_refs": acceptance_proof_refs,
            "operator_steered": operator_steered,
            "accepted": bool(accepted_by and accepted_at and not operator_steered),
        },
    }
    return entry


def _disqualification_reason(entry: dict[str, Any]) -> str | None:
    value_class = _text(entry.get("value_class"))
    if value_class == "control_plane":
        return "control_plane_only"
    if _boolish(entry.get("operator_steered")):
        return "operator_steered"
    deliverable_refs = _string_list(entry.get("deliverable_refs"))
    if _is_bookkeeping_only(deliverable_refs):
        return "bookkeeping_only"
    if str(entry.get("verification_outcome") or "") in {"passed", "review_packet_present"} and (
        not deliverable_refs or not _text(entry.get("deliverable_kind"))
    ):
        return "verification_passed_but_no_deliverable"
    if deliverable_refs and str(entry.get("acceptance_outcome") or "") != "accepted":
        return "deliverable_present_but_not_accepted"
    return None


def _entry_preference(entry: dict[str, Any]) -> tuple[int, int, int, int, str]:
    acceptance_outcome = str(entry.get("acceptance_outcome") or "")
    disqualification_reason = _disqualification_reason(entry)
    packet_id = str(entry.get("packet_id") or "")
    richness = 0
    if _text(entry.get("value_class")):
        richness += 1
    if _text(entry.get("deliverable_kind")):
        richness += 1
    if _string_list(entry.get("deliverable_refs")):
        richness += 1
    if _text(entry.get("beneficiary_surface")):
        richness += 1
    if _text(entry.get("acceptance_mode")):
        richness += 1
    if _text(entry.get("accepted_by")):
        richness += 1
    if _text(entry.get("accepted_at")):
        richness += 1
    return (
        1 if acceptance_outcome == "accepted" else 0,
        0 if disqualification_reason is None else -1,
        richness,
        len(_string_list(entry.get("deliverable_refs"))),
        packet_id,
    )


def _status_mark(met: bool) -> str:
    return "met" if met else "pending"


def _markdown(payload: dict[str, Any]) -> str:
    operator_stage = dict(payload.get("stage_status", {}).get("operator_value") or {})
    product_stage = dict(payload.get("stage_status", {}).get("product_value") or {})
    latest = dict(payload.get("latest_accepted_entry") or {})
    lines = [
        "# Autonomous Value Status",
        "",
        f"- Generated at: {payload.get('generated_at')}",
        (
            f"- Operator-value stage: {_status_mark(bool(operator_stage.get('met')))} "
            f"({int(operator_stage.get('accepted_count') or 0)}/{int(operator_stage.get('required_count') or OPERATOR_VALUE_REQUIRED)} "
            f"accepted across {int(operator_stage.get('distinct_family_count') or 0)}/{int(operator_stage.get('required_family_count') or OPERATOR_VALUE_FAMILY_REQUIRED)} families)"
        ),
        (
            f"- Product-value stage: {_status_mark(bool(product_stage.get('met')))} "
            f"({int(product_stage.get('accepted_count') or 0)}/{int(product_stage.get('required_count') or PRODUCT_VALUE_REQUIRED)} accepted)"
        ),
        f"- Disqualified entries: {int(payload.get('disqualified_entry_count') or 0)}",
        "",
        "## Latest Accepted",
        "",
    ]
    if latest:
        lines.extend(
            [
                f"- Packet: {latest.get('packet_id')}",
                f"- Title: {latest.get('title')}",
                f"- Value class: {latest.get('value_class')}",
                f"- Beneficiary surface: {latest.get('beneficiary_surface') or 'unscoped'}",
                f"- Deliverable: {latest.get('deliverable_kind') or 'unknown'}",
            ]
        )
    else:
        lines.append("- No accepted autonomous value proof has been recorded yet.")

    lines.extend(["", "## Accepted Proofs", ""])
    accepted_entries = list(payload.get("accepted_entries") or [])
    if accepted_entries:
        for entry in accepted_entries[:5]:
            deliverable_refs = ", ".join(_string_list(entry.get("deliverable_refs"))) or "no deliverable refs"
            lines.append(
                f"- {entry.get('packet_id')}: {entry.get('value_class')} for {entry.get('beneficiary_surface') or 'unscoped'} via {entry.get('deliverable_kind') or 'unknown'} ({deliverable_refs})"
            )
    else:
        lines.append("- No accepted autonomous value proofs yet.")

    lines.extend(["", "## Recent Disqualifications", ""])
    disqualified_entries = list(payload.get("disqualified_entries") or [])
    if disqualified_entries:
        for entry in disqualified_entries[:5]:
            lines.append(f"- {entry.get('packet_id')}: {entry.get('disqualification_reason')}")
    else:
        lines.append("- No disqualifications recorded.")
    return "\n".join(lines).rstrip() + "\n"


async def build_payload() -> dict[str, Any]:
    degraded_sections: list[str] = []
    governed_truth = await _safe_load(
        "governed_dispatch",
        _load_governed_dispatch_truth,
        fallback={},
        degraded_sections=degraded_sections,
    )
    backlog_records = await _safe_load(
        "backlog",
        _list_backlog_records,
        fallback=[],
        degraded_sections=degraded_sections,
    )
    backlog_api_records = await _safe_load(
        "backlog_api",
        lambda: _load_backlog_via_api(governed_truth),
        fallback=[],
        degraded_sections=degraded_sections,
    )
    if backlog_api_records:
        backlog_records = list(backlog_records) + list(backlog_api_records)
    if backlog_records or backlog_api_records:
        _clear_degraded_prefixes(degraded_sections, "backlog:", "backlog_api:")

    accepted_entries: list[dict[str, Any]] = []
    disqualified_entries: list[dict[str, Any]] = []
    failure_counts = {failure_id: 0 for failure_id in FAILURE_CLASSES}
    entries_by_packet_id: dict[str, dict[str, Any]] = {}

    for raw_record in backlog_records:
        if not isinstance(raw_record, dict):
            continue
        record = _canonical_backlog_record(raw_record)
        packet_id = _text(record.get("result_id") or record.get("review_id"))
        if not packet_id:
            continue

        entry = _entry_from_record(record)
        existing = entries_by_packet_id.get(packet_id)
        if existing is None or _entry_preference(entry) > _entry_preference(existing):
            entries_by_packet_id[packet_id] = entry

    for entry in entries_by_packet_id.values():
        disqualification_reason = _disqualification_reason(entry)
        if disqualification_reason:
            failure_counts[disqualification_reason] += 1
            disqualified_entries.append({**entry, "disqualification_reason": disqualification_reason})
            continue

        if entry["value_class"] not in {"operator_value", "product_value"}:
            continue
        if entry["acceptance_outcome"] != "accepted":
            continue
        accepted_entries.append(entry)

    accepted_operator_entries = [entry for entry in accepted_entries if entry.get("value_class") == "operator_value"]
    accepted_product_entries = [entry for entry in accepted_entries if entry.get("value_class") == "product_value"]
    operator_families = sorted(
        {
            _text(entry.get("family"))
            for entry in accepted_operator_entries
            if _text(entry.get("family"))
        }
    )
    product_surfaces = sorted(
        {
            _text(entry.get("beneficiary_surface"))
            for entry in accepted_product_entries
            if _text(entry.get("beneficiary_surface"))
        }
    )
    visible_surface_count = sum(1 for surface in product_surfaces if surface in PRODUCT_VISIBLE_SURFACES)
    operator_stage_met = (
        len(accepted_operator_entries) >= OPERATOR_VALUE_REQUIRED
        and len(operator_families) >= OPERATOR_VALUE_FAMILY_REQUIRED
    )
    product_stage_met = (
        operator_stage_met
        and len(accepted_product_entries) >= PRODUCT_VALUE_REQUIRED
        and visible_surface_count >= 1
    )
    accepted_entries.sort(key=lambda item: (_text(item.get("accepted_at")), _text(item.get("packet_id"))))
    latest_accepted_entry = accepted_entries[-1] if accepted_entries else None
    disqualified_entries.sort(key=lambda item: (_text(item.get("packet_id")), _text(item.get("title"))))

    return {
        "generated_at": _iso_now(),
        "accepted_entry_count": len(accepted_entries),
        "accepted_operator_value_count": len(accepted_operator_entries),
        "accepted_product_value_count": len(accepted_product_entries),
        "disqualified_entry_count": len(disqualified_entries),
        "accepted_entries": accepted_entries,
        "disqualified_entries": disqualified_entries,
        "latest_accepted_entry": latest_accepted_entry,
        "failure_counts": failure_counts,
        "stage_status": {
            "operator_value": {
                "required_count": OPERATOR_VALUE_REQUIRED,
                "accepted_count": len(accepted_operator_entries),
                "distinct_family_count": len(operator_families),
                "distinct_families": operator_families,
                "required_family_count": OPERATOR_VALUE_FAMILY_REQUIRED,
                "remaining_required": max(0, OPERATOR_VALUE_REQUIRED - len(accepted_operator_entries)),
                "remaining_family_count": max(0, OPERATOR_VALUE_FAMILY_REQUIRED - len(operator_families)),
                "met": operator_stage_met,
            },
            "product_value": {
                "required_count": PRODUCT_VALUE_REQUIRED,
                "accepted_count": len(accepted_product_entries),
                "beneficiary_surfaces": product_surfaces,
                "visible_surface_count": visible_surface_count,
                "remaining_required": max(0, PRODUCT_VALUE_REQUIRED - len(accepted_product_entries)),
                "met": product_stage_met,
            },
        },
        "degraded_sections": degraded_sections,
        "source_artifacts": {
            "backlog": str(REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"),
            "governed_dispatch": str(REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"),
            "autonomous_value_proof": str(OUTPUT_PATH),
            "autonomous_value_status": str(STATUS_MD_PATH),
        },
    }


async def _async_main(check: bool, emit_json: bool) -> int:
    payload = await build_payload()
    rendered = _json_render(payload)
    status_md = _markdown(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    current_md = STATUS_MD_PATH.read_text(encoding="utf-8") if STATUS_MD_PATH.exists() else ""
    comparable_rendered, comparable_md = _render_against_existing(payload, current)
    if check:
        if current != comparable_rendered or current_md != comparable_md:
            print(f"{OUTPUT_PATH} or {STATUS_MD_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current == comparable_rendered and current_md == comparable_md:
        if emit_json:
            print(json.dumps(payload, indent=2))
        else:
            print(str(OUTPUT_PATH))
        return 0
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if current_md != status_md:
        STATUS_MD_PATH.write_text(status_md, encoding="utf-8")
    if emit_json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the canonical autonomous-value proof artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when autonomous-value-proof artifacts are stale.")
    args = parser.parse_args()
    return asyncio.run(_async_main(check=args.check, emit_json=args.json))


if __name__ == "__main__":
    raise SystemExit(main())
