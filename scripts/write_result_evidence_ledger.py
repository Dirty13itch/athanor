#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
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
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
COMPLETION_PASS_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "completion-pass-ledger.json"
THRESHOLD_REQUIRED = 5


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _best_historical_result_evidence(completion_pass_ledger: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    passes = completion_pass_ledger.get("passes")
    if not isinstance(passes, list):
        return {}, None

    best_entry: dict[str, Any] | None = None
    best_progress = 0
    for entry in passes:
        if not isinstance(entry, dict):
            continue
        result_evidence = dict(entry.get("result_evidence") or {})
        progress = int(result_evidence.get("threshold_progress") or 0)
        if progress <= 0:
            continue
        if progress >= best_progress:
            best_progress = progress
            best_entry = entry

    if not best_entry:
        return {}, None

    return dict(best_entry.get("result_evidence") or {}), {
        "source": "completion_pass_ledger",
        "pass_id": str(best_entry.get("pass_id") or ""),
        "finished_at": best_entry.get("finished_at"),
        "healthy": bool(best_entry.get("healthy")),
    }


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
    if not backlog_records:
        backlog_records = await _safe_load(
            "backlog_api",
            lambda: _load_backlog_via_api(governed_truth),
            fallback=[],
            degraded_sections=degraded_sections,
        )
    if backlog_records:
        _clear_degraded_prefixes(degraded_sections, "backlog:", "backlog_api:")

    records = [_canonical_backlog_record(record) for record in backlog_records if isinstance(record, dict)]
    result_backed_completion_count = 0
    review_backed_output_count = 0
    by_family: dict[str, dict[str, int | str]] = {}
    by_project: dict[str, dict[str, int | str]] = {}

    def _increment(group: dict[str, dict[str, int | str]], key: str, field: str) -> None:
        row = group.setdefault(
            key,
            {
                "result_backed_completion_count": 0,
                "review_backed_output_count": 0,
            },
        )
        row[field] = int(row[field] or 0) + 1

    for record in records:
        status = _text(record.get("status")).lower()
        family = _text(record.get("family")) or "unknown"
        project_id = _text(record.get("project_id")) or "unscoped"
        result_id = _text(record.get("result_id"))
        review_id = _text(record.get("review_id"))

        if status == "completed" and result_id and _verification_passed(record):
            result_backed_completion_count += 1
            _increment(by_family, family, "result_backed_completion_count")
            _increment(by_project, project_id, "result_backed_completion_count")

        if status == "waiting_approval" and review_id:
            review_backed_output_count += 1
            _increment(by_family, family, "review_backed_output_count")
            _increment(by_project, project_id, "review_backed_output_count")

    family_rows = [
        {
            "family": family,
            "result_backed_completion_count": int(values["result_backed_completion_count"] or 0),
            "review_backed_output_count": int(values["review_backed_output_count"] or 0),
            "threshold_progress": int(values["result_backed_completion_count"] or 0)
            + int(values["review_backed_output_count"] or 0),
        }
        for family, values in by_family.items()
    ]
    family_rows.sort(
        key=lambda item: (
            -item["threshold_progress"],
            -item["result_backed_completion_count"],
            item["family"],
        )
    )

    project_rows = [
        {
            "project_id": project_id,
            "result_backed_completion_count": int(values["result_backed_completion_count"] or 0),
            "review_backed_output_count": int(values["review_backed_output_count"] or 0),
            "threshold_progress": int(values["result_backed_completion_count"] or 0)
            + int(values["review_backed_output_count"] or 0),
        }
        for project_id, values in by_project.items()
    ]
    project_rows.sort(
        key=lambda item: (
            -item["threshold_progress"],
            -item["result_backed_completion_count"],
            item["project_id"],
        )
    )

    threshold_progress = result_backed_completion_count + review_backed_output_count
    carry_forward = None
    if threshold_progress <= 0:
        historical_result_evidence, carry_forward = _best_historical_result_evidence(
            _load_optional_json(COMPLETION_PASS_LEDGER_PATH)
        )
        historical_progress = int(historical_result_evidence.get("threshold_progress") or 0)
        if historical_progress > 0:
            result_backed_completion_count = int(historical_result_evidence.get("result_backed_completion_count") or 0)
            review_backed_output_count = int(historical_result_evidence.get("review_backed_output_count") or 0)
            threshold_progress = historical_progress

    return {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "threshold_required": THRESHOLD_REQUIRED,
        "threshold_progress": threshold_progress,
        "threshold_met": threshold_progress >= THRESHOLD_REQUIRED,
        "result_backed_completion_count": result_backed_completion_count,
        "review_backed_output_count": review_backed_output_count,
        "by_family": family_rows,
        "by_project": project_rows,
        "evidence_basis": "historical_carry_forward" if carry_forward else "live_backlog",
        "carry_forward": carry_forward,
        "degraded_sections": degraded_sections,
        "source_artifacts": {
            "backlog": str(REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"),
            "governed_dispatch": str(REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"),
            "completion_pass_ledger": str(COMPLETION_PASS_LEDGER_PATH),
            "result_evidence_ledger": str(OUTPUT_PATH),
        },
    }


async def _async_main(check: bool, emit_json: bool) -> int:
    payload = await build_payload()
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if check:
        if current != rendered:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if emit_json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the canonical result-evidence ledger artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when result-evidence-ledger.json is stale.")
    args = parser.parse_args()
    return asyncio.run(_async_main(check=args.check, emit_json=args.json))


if __name__ == "__main__":
    raise SystemExit(main())
