from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_render_restart_brief_surfaces_current_queue_and_harvest_posture() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-14T20:05:17+00:00",
        "loop_mode": "governor_scheduling",
        "provider_gate_state": "completed",
        "work_economy_status": "ready",
        "top_task_title": "Dispatch and Work-Economy Closure",
        "queue_total": 4,
        "queue_dispatchable": 3,
        "dispatch_status": "claimed",
        "dispatch_phase_label": "governed_dispatch_shadow",
        "queue": [
            {
                "title": "Dispatch and Work-Economy Closure",
                "value_class": "dispatch_truth_drift",
                "approved_mutation_class": "auto_harvest",
                "preferred_lane_family": "dispatch_truth_repair",
                "proof_command_or_eval_surface": "python scripts/run_gpu_scheduler_baseline_eval.py",
            },
            {
                "title": "Capacity and Harvest Truth",
                "value_class": "capacity_truth_drift",
                "approved_mutation_class": "auto_harvest",
                "preferred_lane_family": "capacity_truth_repair",
                "proof_command_or_eval_surface": "python scripts/collect_capacity_telemetry.py",
            },
        ],
        "harvest_summary": {
            "admission_state": "open_harvest_window",
            "ready_for_harvest_now": True,
            "harvestable_scheduler_slot_count": 2,
            "harvestable_zone_ids": ["F", "W"],
            "open_harvest_slot_target_ids": ["foundry-bulk-pool", "workshop-batch-support"],
        },
        "advisory_blockers": ["agent_runtime_restart_recovered"],
        "recent_commits": ["abc1234 Example commit"],
        "status_lines": [" M STATUS.md"],
        "diff_stat_lines": [" STATUS.md | 2 +-"],
        "canonical_docs": ["STATUS.md"],
        "control_surfaces": ["https://athanor.local/"],
        "artifacts": {
            "ralph_latest": "C:/Athanor/reports/ralph-loop/latest.json",
            "dispatch_state": "C:/Athanor/reports/truth-inventory/governed-dispatch-state.json",
            "capacity_telemetry": "C:/Athanor/reports/truth-inventory/capacity-telemetry.json",
            "master_atlas_latest": "C:/athanor-devstack/reports/master-atlas/latest.json",
        },
    }

    rendered = module.render_restart_brief(snapshot)

    assert "# Athanor Session Restart Brief" in rendered
    assert "`governor_scheduling`" in rendered
    assert "Dispatch and Work-Economy Closure" in rendered
    assert "open_harvest_window" in rendered
    assert "foundry-bulk-pool" in rendered
    assert "agent_runtime_restart_recovered" in rendered
    assert "https://athanor.local/" in rendered


def test_build_restart_snapshot_reads_git_and_live_artifacts(tmp_path: Path) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    ralph_path = tmp_path / "ralph.json"
    dispatch_path = tmp_path / "dispatch.json"
    capacity_path = tmp_path / "capacity.json"
    atlas_path = tmp_path / "atlas.json"

    ralph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14T20:05:17+00:00",
                "loop_mode": "governor_scheduling",
                "provider_gate_state": "completed",
                "work_economy_status": "ready",
                "top_task": {"title": "Dispatch and Work-Economy Closure", "task_id": "workstream:dispatch"},
                "ranked_autonomous_queue": [
                    {"title": "Dispatch and Work-Economy Closure", "id": "workstream:dispatch"}
                ],
                "autonomous_queue_summary": {"total_count": 9, "dispatchable_count": 7},
            }
        ),
        encoding="utf-8",
    )
    dispatch_path.write_text(
        json.dumps(
            {
                "dispatch_outcome": "claimed",
                "dispatch_phase_label": "governed_dispatch_shadow",
                "governed_dispatch_ready": True,
                "advisory_blockers": ["agent_runtime_restart_recovered"],
                "capacity_harvest_summary": {
                    "admission_state": "open_harvest_window",
                    "ready_for_harvest_now": True,
                    "harvestable_scheduler_slot_count": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    capacity_path.write_text(json.dumps({"capacity_summary": {"scheduler_slot_count": 5}}), encoding="utf-8")
    atlas_path.write_text(json.dumps({"generated_at": "2026-04-14T20:05:17+00:00"}), encoding="utf-8")

    module.RALPH_LATEST_PATH = ralph_path
    module.DISPATCH_STATE_PATH = dispatch_path
    module.CAPACITY_TELEMETRY_PATH = capacity_path
    module.ATLAS_LATEST_PATH = atlas_path
    module._run_git = lambda *args: {
        ("status", "--short"): [" M STATUS.md"],
        ("diff", "--stat"): [" STATUS.md | 2 +-"],
        ("log", "--oneline", "-5"): ["abc1234 Example commit"],
    }.get(tuple(args), [])

    snapshot = module.build_restart_snapshot()

    assert snapshot["loop_mode"] == "governor_scheduling"
    assert snapshot["provider_gate_state"] == "completed"
    assert snapshot["work_economy_status"] == "ready"
    assert snapshot["queue_total"] == 9
    assert snapshot["queue_dispatchable"] == 7
    assert snapshot["dispatch_status"] == "claimed"
    assert snapshot["advisory_blockers"] == ["agent_runtime_restart_recovered"]
    assert snapshot["status_lines"] == [" M STATUS.md"]


def test_run_refresh_uses_current_python_and_ralph_loop_script(monkeypatch) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    recorded: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(command, cwd=None, capture_output=None, text=None, encoding=None, errors=None, check=None):  # noqa: ANN001
        recorded["command"] = command
        recorded["cwd"] = cwd
        recorded["capture_output"] = capture_output
        recorded["text"] = text
        recorded["encoding"] = encoding
        recorded["errors"] = errors
        recorded["check"] = check
        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_refresh()

    assert recorded["command"] == [module.sys.executable, str(module.RALPH_LOOP_SCRIPT), "--skip-validation"]
    assert recorded["cwd"] == module.REPO_ROOT
    assert recorded["capture_output"] is True
    assert recorded["text"] is True
    assert recorded["encoding"] == "utf-8"
    assert recorded["errors"] == "replace"
    assert recorded["check"] is False
