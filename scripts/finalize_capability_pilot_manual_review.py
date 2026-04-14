from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from routing_contract_support import dump_json, iso_now
from truth_inventory import REPO_ROOT, load_registry


EVAL_RUN_LEDGER_PATH = REPO_ROOT / "config" / "automation-backbone" / "eval-run-ledger.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    dump_json(path, payload)


def _find_run(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    for run in payload.get("runs", []):
        if str(run.get("run_id") or "").strip() == run_id:
            return run
    raise SystemExit(f"Run id not found in eval-run-ledger.json: {run_id}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize a benchmark-spec manual review into the eval artifact and eval-run ledger."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--outcome", choices=["passed", "failed"], required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--note-path", type=Path, help="Optional review note to link from the formal-eval artifact.")
    args = parser.parse_args()

    ledger_payload = _load_json(EVAL_RUN_LEDGER_PATH)
    run = _find_run(ledger_payload, args.run_id)
    artifact_path = Path(str(run.get("formal_eval_artifact_path") or "").strip())
    if not artifact_path.exists():
        raise SystemExit(f"Formal eval artifact is missing: {artifact_path}")

    artifact = _load_json(artifact_path)
    current_status = str(artifact.get("status") or "").strip()
    if current_status != "manual_review_pending":
        raise SystemExit(
            f"Manual review finalizer only supports artifacts currently at manual_review_pending, got: {current_status or 'missing'}"
        )

    note_path = args.note_path.resolve() if args.note_path else None
    if note_path and not note_path.exists():
        raise SystemExit(f"Manual review note does not exist: {note_path}")

    now = iso_now()
    decision_reason = (
        "benchmark_spec_manual_review_passed"
        if args.outcome == "passed"
        else "benchmark_spec_manual_review_failed"
    )
    review_outcome = (
        "sufficient_for_bounded_next_step"
        if args.outcome == "passed"
        else "rejected_as_redundant_for_current_stack"
    )

    artifact["status"] = args.outcome
    artifact["decision_reason"] = decision_reason
    artifact["review_scope"] = "manual_contract_review_completed"
    artifact["manual_review_completed_at"] = now
    artifact["manual_review_outcome"] = review_outcome
    artifact["manual_review_summary"] = args.summary
    if note_path:
        artifact["manual_review_note_path"] = str(note_path)

    run["last_run_at"] = now
    run["status"] = "completed"
    run["promotion_validity"] = "valid" if args.outcome == "passed" else "requires_formal_eval_run"
    notes = [str(item) for item in run.get("notes", []) if str(item).strip()]
    notes.append(
        f"Manual review completed at {now}: {args.summary}"
    )
    if note_path:
        notes.append(f"Manual review note: {note_path}")
    run["notes"] = notes

    _write_json(artifact_path, artifact)
    _write_json(EVAL_RUN_LEDGER_PATH, ledger_payload)
    print(artifact_path)
    print(EVAL_RUN_LEDGER_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
