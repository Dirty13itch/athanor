from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from automation_records import AutomationRunRecord, emit_automation_run_record


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "audit" / "automation" / "contract-healer-latest.json"

COMMANDS = [
    [sys.executable, "scripts/validate_platform_contract.py"],
    [sys.executable, "scripts/generate_documentation_index.py", "--check"],
    [sys.executable, "scripts/generate_project_maturity_report.py", "--check"],
]


def run_command(command: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "duration_seconds": round(duration, 3),
    }


def main() -> int:
    started = time.perf_counter()
    checks = [run_command(command) for command in COMMANDS]
    success = all(int(check["returncode"]) == 0 for check in checks)
    timestamp = datetime.now(timezone.utc).isoformat()
    artifact = {
        "generated_at": timestamp,
        "lane": "contract_healer",
        "action_class": "drift_report_generation",
        "success": success,
        "checks": checks,
        "operator_visible_summary": (
            "Contract healer regenerated drift evidence successfully."
            if success
            else "Contract healer detected drift or generator failures."
        ),
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    record = AutomationRunRecord(
        automation_id="contract-healer",
        lane="contract_healer",
        action_class="drift_report_generation",
        inputs={"commands": COMMANDS, "artifact_path": str(ARTIFACT_PATH)},
        result={
            "success": success,
            "check_count": len(checks),
            "failed_checks": [check["command"] for check in checks if int(check["returncode"]) != 0],
            "artifact_path": str(ARTIFACT_PATH),
        },
        rollback={
            "mode": "delete_artifact",
            "path": str(ARTIFACT_PATH),
            "note": "No runtime mutation occurred; remove or regenerate the artifact if needed.",
        },
        duration=time.perf_counter() - started,
        operator_visible_summary=str(artifact["operator_visible_summary"]),
    )
    emit_result = asyncio.run(emit_automation_run_record(record))
    artifact["automation_record_persisted"] = emit_result.persisted
    artifact["automation_record_error"] = emit_result.error
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
