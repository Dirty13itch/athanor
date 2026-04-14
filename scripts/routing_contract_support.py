from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
TRUTH_INVENTORY_DIR = REPO_ROOT / "reports" / "truth-inventory"
HISTORY_DIR = REPO_ROOT / "reports" / "history"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def append_history(stream_name: str, payload: dict[str, Any]) -> None:
    stamped = dict(payload)
    stamped.setdefault("recorded_at", iso_now())
    append_jsonl(HISTORY_DIR / stream_name / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl", stamped)


def parse_dt(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def expires_at_from_hours(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def confidence_from_age(age_seconds: int | None, *, high_within: int, medium_within: int) -> str:
    if age_seconds is None:
        return "low"
    if age_seconds <= high_within:
        return "high"
    if age_seconds <= medium_within:
        return "medium"
    return "low"
