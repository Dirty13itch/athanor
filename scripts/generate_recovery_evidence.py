from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from automation_records import AutomationRunRecord, emit_automation_run_record


ROOT = Path(__file__).resolve().parents[1]
AGENTS_SRC = ROOT / "projects" / "agents" / "src"
ARTIFACT_PATH = ROOT / "audit" / "recovery" / "restore-drill-latest.json"

RUNNER = """
import asyncio
import json
from unittest.mock import AsyncMock, patch
from athanor_agents.operator_tests import run_operator_tests

class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.values = {}

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def ping(self):
        return True

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)

async def _main():
    fake_redis = FakeRedis()
    with (
        patch("athanor_agents.operator_tests._get_redis", AsyncMock(return_value=fake_redis)),
        patch("athanor_agents.activity.log_event", AsyncMock()),
    ):
        return await run_operator_tests(flow_ids=["restore_drill"], actor="recovery-evidence")

snapshot = asyncio.run(_main())
print(json.dumps(snapshot))
""".strip()


def _sanitize_string(value: str) -> str:
    if "://" not in value:
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.netloc:
        return value
    if parsed.username is None and parsed.password is None and "@" not in parsed.netloc:
        return value
    host = parsed.hostname or ""
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _sanitize_payload(value):
    if isinstance(value, dict):
        return {key: _sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def main() -> int:
    started = time.perf_counter()
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = str(AGENTS_SRC) if not existing_pythonpath else f"{AGENTS_SRC}{os.pathsep}{existing_pythonpath}"

    completed = subprocess.run(
        [sys.executable, "-c", RUNNER],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    success = completed.returncode == 0
    timestamp = datetime.now(timezone.utc).isoformat()
    snapshot = None
    error = None

    if success:
        try:
            snapshot = json.loads(completed.stdout.strip())
            snapshot = _sanitize_payload(snapshot)
        except json.JSONDecodeError as exc:
            success = False
            error = f"restore drill output was not valid JSON: {exc}"
    else:
        error = completed.stderr.strip() or completed.stdout.strip() or "restore drill subprocess failed"

    artifact = {
        "generated_at": timestamp,
        "lane": "recovery_evidence",
        "action_class": "restore_drill_rehearsal",
        "success": success,
        "artifact_mode": "non_destructive_live_probe",
        "snapshot": snapshot,
        "error": error,
    }

    artifact = _sanitize_payload(artifact)

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    verified_store_count = 0
    if isinstance(snapshot, dict):
        flows = snapshot.get("flows", [])
        if isinstance(flows, list) and flows:
            details = flows[0].get("details", {})
            if isinstance(details, dict):
                verified_store_count = int(details.get("verified_store_count") or 0)

    sanitized_error = _sanitize_payload(error)

    summary = (
        f"Restore drill rehearsal captured evidence for {verified_store_count} verified stores."
        if success
        else "Restore drill rehearsal failed to produce evidence."
    )

    record = AutomationRunRecord(
        automation_id="restore-drill-evidence",
        lane="recovery_evidence",
        action_class="restore_drill_rehearsal",
        inputs={
            "flow_ids": ["restore_drill"],
            "artifact_path": str(ARTIFACT_PATH),
            "pythonpath": str(AGENTS_SRC),
        },
        result={
            "success": success,
            "verified_store_count": verified_store_count,
            "artifact_path": str(ARTIFACT_PATH),
            "error": sanitized_error,
        },
        rollback={
            "mode": "delete_artifact",
            "path": str(ARTIFACT_PATH),
            "note": "This drill is read-only; remove or regenerate the artifact if needed.",
        },
        duration=time.perf_counter() - started,
        operator_visible_summary=summary,
    )
    emit_result = asyncio.run(emit_automation_run_record(record))
    artifact["automation_record_persisted"] = emit_result.persisted
    artifact["automation_record_error"] = emit_result.error
    artifact = _sanitize_payload(artifact)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
