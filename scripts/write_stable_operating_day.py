#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
COMPLETION_PASS_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "completion-pass-ledger.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "stable-operating-day.json"
REQUIRED_WINDOW_HOURS = 24


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _hours(started_at: datetime | None, ended_at: datetime) -> float:
    if not started_at:
        return 0.0
    return round(max((ended_at - started_at).total_seconds(), 0.0) / 3600.0, 2)


def _proof_met(entry: dict[str, Any], proof_id: str) -> bool:
    proofs = dict(entry.get("proofs") or {})
    proof = dict(proofs.get(proof_id) or {})
    return bool(proof.get("met"))


def build_payload(ledger: dict[str, Any], *, now_iso: str | None = None) -> dict[str, Any]:
    now_dt = _parse_iso(now_iso) or datetime.now(timezone.utc)
    window_start = now_dt - timedelta(hours=REQUIRED_WINDOW_HOURS)
    passes = [dict(item) for item in ledger.get("passes", []) if isinstance(item, dict)]
    passes.sort(key=lambda item: _parse_iso(item.get("finished_at")) or datetime.min.replace(tzinfo=timezone.utc))

    consecutive: list[dict[str, Any]] = []
    for entry in reversed(passes):
        finished_at = _parse_iso(entry.get("finished_at"))
        if not finished_at:
            continue
        if not bool(entry.get("healthy")):
            break
        consecutive.append(entry)
    consecutive.reverse()

    included = list(consecutive)
    earliest_consecutive = _parse_iso(consecutive[0].get("finished_at")) if consecutive else None
    latest_pass_at = _parse_iso(consecutive[-1].get("finished_at")) if consecutive else None

    validator_streak = 0
    stale_claim_streak = 0
    artifact_consistency_streak = 0
    for entry in reversed(consecutive):
        if _proof_met(entry, "validator_and_contract_healer"):
            validator_streak += 1
        else:
            break
    for entry in reversed(consecutive):
        if _proof_met(entry, "stale_claim_failures"):
            stale_claim_streak += 1
        else:
            break
    for entry in reversed(consecutive):
        if _proof_met(entry, "artifact_consistency"):
            artifact_consistency_streak += 1
        else:
            break

    covered_window_hours = _hours(earliest_consecutive, now_dt)
    met = bool(consecutive) and covered_window_hours >= REQUIRED_WINDOW_HOURS
    detail = (
        "Stable operating-day window is satisfied."
        if met
        else f"Stable-day proof needs {REQUIRED_WINDOW_HOURS - min(covered_window_hours, REQUIRED_WINDOW_HOURS):.2f} more hour(s) of consecutive healthy passes."
    )

    return {
        "generated_at": now_dt.isoformat(),
        "required_window_hours": REQUIRED_WINDOW_HOURS,
        "covered_window_hours": covered_window_hours,
        "window_started_at": window_start.isoformat(),
        "oldest_consecutive_pass_at": earliest_consecutive.isoformat() if earliest_consecutive else None,
        "latest_pass_at": latest_pass_at.isoformat() if latest_pass_at else None,
        "included_pass_count": len(included),
        "consecutive_healthy_pass_count": len(consecutive),
        "validator_contract_healer_streak": validator_streak,
        "stale_claim_streak": stale_claim_streak,
        "artifact_consistency_streak": artifact_consistency_streak,
        "met": met,
        "detail": detail,
        "source_artifacts": {
            "completion_pass_ledger": str(COMPLETION_PASS_LEDGER_PATH),
            "stable_operating_day": str(OUTPUT_PATH),
        },
    }


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the stable operating-day proof artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when stable-operating-day.json is stale.")
    args = parser.parse_args()

    payload = build_payload(_load_optional_json(COMPLETION_PASS_LEDGER_PATH))
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if args.check:
        if current != rendered:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
