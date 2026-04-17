from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


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


def test_run_capability_pilot_evals_writes_passed_and_blocked_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_evals_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_evals.py",
    )
    output = tmp_path / "capability-pilot-evals.json"
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    promptfoo_config = tmp_path / "pilot-goose-shell-comparison.yaml"
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                        "captured_at": "2026-04-11T18:05:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    runs = [
        {
            "run_id": "goose-operator-shell-lane-eval-2026q2",
            "initiative_id": "goose-operator-shell",
            "task_class": "operator_shell_comparison",
            "corpus_id": "operator_shell_trials_v1",
            "wrapper_mode": "goose_wrapped",
            "operator_test_flow_id": "goose_operator_shell",
            "promptfoo_config_path": str(promptfoo_config),
            "execution_requirements": {
                "required_commands": ["goose"],
                "preferred_hosts": ["desk"],
                "request_surface_hint": "dashboard task",
            },
            "linked_promotion_packet": "C:/athanor-devstack/docs/promotion-packets/goose-operator-shell.md",
            "evidence_artifacts": [],
        },
        {
            "run_id": "openhands-bounded-worker-lane-eval-2026q2",
            "initiative_id": "openhands-bounded-worker-lane",
            "task_class": "bounded_worker_comparison",
            "corpus_id": "bounded_worker_trials_v1",
            "wrapper_mode": "direct_cli",
            "operator_test_flow_id": "openhands_bounded_worker",
            "execution_requirements": {
                "required_commands": ["openhands"],
                "preferred_hosts": ["desk"],
            },
            "linked_promotion_packet": "C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md",
            "evidence_artifacts": [],
        },
    ]
    capability_map = {
        "goose-operator-shell": {"label": "Goose Operator Shell"},
        "openhands-bounded-worker-lane": {"label": "OpenHands Bounded Worker Lane"},
    }

    async def _fake_run_operator_snapshot(flow_ids: list[str], actor: str):
        return {
            "generated_at": "2026-04-11T18:00:00Z",
            "status": "live_partial",
            "last_outcome": "partial",
            "flows": [
                {
                    "id": "goose_operator_shell",
                    "status": "live_partial",
                    "last_outcome": "passed",
                    "last_run_at": "2026-04-11T18:00:00Z",
                    "details": {"blocking_reasons": []},
                },
                {
                    "id": "openhands_bounded_worker",
                    "status": "configured",
                    "last_outcome": "blocked",
                    "last_run_at": "2026-04-11T18:00:00Z",
                    "details": {"blocking_reasons": ["missing_command:openhands"]},
                },
            ],
        }

    monkeypatch.setattr(module, "_select_runs", lambda run_ids: (runs, capability_map))
    monkeypatch.setattr(module, "_tooling_index", lambda host_id: {})
    monkeypatch.setattr(module, "PILOT_FORMAL_PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "_current_local_command_state",
        lambda command: {
            "command": command,
            "available_locally": command == "goose",
            "local_path": f"/tmp/{command}" if command == "goose" else None,
        },
    )
    monkeypatch.setattr(module, "_run_operator_snapshot", _fake_run_operator_snapshot)
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda command: "/tmp/npx" if command == "npx" else (f"/tmp/{command}" if command == "goose" else None),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_evals.py",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"] == {
        "total": 2,
        "passed": 1,
        "blocked": 1,
        "failed": 0,
        "not_run": 0,
        "operator_smoke_only": 0,
        "ready_for_formal_eval": 1,
    }
    goose = next(item for item in payload["records"] if item["initiative_id"] == "goose-operator-shell")
    openhands = next(item for item in payload["records"] if item["initiative_id"] == "openhands-bounded-worker-lane")
    assert goose["pilot_eval_status"] == "passed"
    assert goose["formal_eval_scaffold_exists"] is True
    assert goose["formal_preflight_status"] == "ready"
    assert goose["proof_tier"] == "operator_smoke_plus_formal_preflight"
    assert openhands["pilot_eval_status"] == "blocked"
    assert openhands["blocking_reasons"] == ["missing_command:openhands"]


def test_generate_capability_pilot_readiness_includes_latest_pilot_eval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"generate_capability_pilot_readiness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_capability_pilot_readiness.py",
    )
    output = tmp_path / "capability-pilot-readiness.json"
    packet_path = tmp_path / "goose-operator-shell.md"
    promptfoo_config = tmp_path / "pilot-goose-shell-comparison.yaml"
    packet_path.write_text("# packet\n", encoding="utf-8")
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    pilot_evals_path = tmp_path / "capability-pilot-evals.json"
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    pilot_evals_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "initiative_id": "goose-operator-shell",
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "pilot_eval_status": "passed",
                        "last_outcome": "passed",
                        "captured_at": "2026-04-11T18:30:00Z",
                        "proof_tier": "operator_smoke_plus_formal_preflight",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                        "captured_at": "2026-04-11T18:31:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PILOT_EVALS_PATH", pilot_evals_path)
    monkeypatch.setattr(module, "PILOT_FORMAL_PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "_load_json",
        lambda path: (
            {
                "lanes": [
                    {
                        "linked_capability_id": "goose-operator-shell",
                        "lane_status": "drafting_packet",
                        "promotion_packet_path": str(packet_path),
                        "next_action": "Run bounded shell pilot",
                    }
                ]
            }
            if Path(path) == module.DEVSTACK_LANE_REGISTRY_PATH
            else (
                json.loads(pilot_evals_path.read_text(encoding="utf-8"))
                if Path(path) == pilot_evals_path
                else json.loads(preflight_path.read_text(encoding="utf-8"))
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "capability-adoption-registry.json": {
                "capabilities": [
                    {"id": "goose-operator-shell", "label": "Goose Operator Shell", "stage": "prototype"}
                ]
            },
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "initiative_id": "goose-operator-shell",
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "execution_requirements": {
                            "required_commands": ["goose"],
                            "preferred_hosts": ["desk"],
                            "request_surface_hint": "dashboard task",
                        },
                        "promptfoo_config_path": str(promptfoo_config),
                    }
                ]
            },
            "tooling-inventory.json": {
                "hosts": [
                    {
                        "id": "desk",
                        "tools": [
                            {"command": "goose", "status": "installed", "version": "1.0.0"}
                        ],
                    }
                ]
            },
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_current_local_command_state",
        lambda command: {
            "command": command,
            "available_locally": True,
            "local_path": f"/tmp/{command}",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_capability_pilot_readiness.py",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["readiness_state"] == "ready_for_formal_eval"
    assert record["latest_eval_status"] == "passed"
    assert record["latest_eval_run_id"] == "goose-operator-shell-lane-eval-2026q2"
    assert record["formal_preflight_status"] == "ready"
    assert record["formal_preflight_blocker_class"] is None
    assert record["formal_runner_support"] == "promptfoo_supported"
    assert record["next_formal_gate"] is None


def test_generate_capability_pilot_readiness_reports_formal_eval_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"generate_capability_pilot_readiness_formal_failure_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_capability_pilot_readiness.py",
    )
    output = tmp_path / "capability-pilot-readiness.json"
    packet_path = tmp_path / "goose-operator-shell.md"
    promptfoo_config = tmp_path / "pilot-goose-shell-comparison.yaml"
    formal_eval_artifact = tmp_path / "goose-formal-eval.json"
    packet_path.write_text("# packet\n", encoding="utf-8")
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    formal_eval_artifact.write_text(
        json.dumps(
            {
                "status": "failed",
                "decision_reason": "promptfoo_failed",
                "promptfoo_summary": {"successes": 7, "failures": 1, "errors": 0},
                "promptfoo_primary_failure_hint": "Goose remaining miss in task `async-diff-review`: did not recommend httpx or aiohttp.",
                "generated_at": "2026-04-11T18:32:00Z",
            }
        ),
        encoding="utf-8",
    )
    pilot_evals_path = tmp_path / "capability-pilot-evals.json"
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    pilot_evals_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "initiative_id": "goose-operator-shell",
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "pilot_eval_status": "passed",
                        "last_outcome": "passed",
                        "captured_at": "2026-04-11T18:30:00Z",
                        "proof_tier": "operator_smoke_plus_formal_preflight",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                        "captured_at": "2026-04-11T18:31:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PILOT_EVALS_PATH", pilot_evals_path)
    monkeypatch.setattr(module, "PILOT_FORMAL_PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "_load_json",
        lambda path: (
            {
                "lanes": [
                    {
                        "linked_capability_id": "goose-operator-shell",
                        "lane_status": "drafting_packet",
                        "promotion_packet_path": str(packet_path),
                        "next_action": "Run bounded shell pilot",
                    }
                ]
            }
            if Path(path) == module.DEVSTACK_LANE_REGISTRY_PATH
            else json.loads(Path(path).read_text(encoding="utf-8"))
        ),
    )
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "capability-adoption-registry.json": {
                "capabilities": [
                    {"id": "goose-operator-shell", "label": "Goose Operator Shell", "stage": "prototype"}
                ]
            },
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "initiative_id": "goose-operator-shell",
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "formal_eval_artifact_path": str(formal_eval_artifact),
                        "execution_requirements": {
                            "required_commands": ["goose"],
                            "preferred_hosts": ["desk"],
                            "request_surface_hint": "dashboard task",
                        },
                        "promptfoo_config_path": str(promptfoo_config),
                    }
                ]
            },
            "tooling-inventory.json": {
                "hosts": [
                    {
                        "id": "desk",
                        "tools": [
                            {"command": "goose", "status": "installed", "version": "1.0.0"}
                        ],
                    }
                ]
            },
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_current_local_command_state",
        lambda command: {
            "command": command,
            "available_locally": True,
            "local_path": f"/tmp/{command}",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_capability_pilot_readiness.py",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert payload["summary"]["formal_eval_failed"] == 1
    assert record["readiness_state"] == "formal_eval_failed"
    assert record["proof_tier"] == "formal_eval_failed"
    assert record["formal_eval_status"] == "failed"
    assert record["formal_eval_decision_reason"] == "promptfoo_failed"
    assert record["formal_eval_primary_failure_hint"] == "Goose remaining miss in task `async-diff-review`: did not recommend httpx or aiohttp."
    assert record["formal_eval_promptfoo_summary"] == {"successes": 7, "failures": 1, "errors": 0}
    assert record["formal_eval_result_path"] == str(formal_eval_artifact)
    assert "async-diff-review" in record["next_action"]
    assert "httpx or aiohttp" in record["next_formal_gate"]


def test_run_capability_pilot_formal_preflight_blocks_invalid_benchmark_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_preflight_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_preflight.py",
    )
    output = tmp_path / "capability-pilot-formal-preflight.json"
    benchmark_spec = tmp_path / "agt-policy-bridge.yaml"
    benchmark_spec.write_text("pilot_id: agt-policy-bridge\n", encoding="utf-8")
    fixture_one = tmp_path / "agt-native-decision-trace.json"
    fixture_two = tmp_path / "agt-bridge-decision-trace.json"
    fixture_one.write_text(json.dumps({"trace_id": "native-only"}), encoding="utf-8")
    fixture_two.write_text(json.dumps({"trace_id": "bridge-only"}), encoding="utf-8")

    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "benchmark_spec_path": str(benchmark_spec),
                        "formal_eval_artifact_path": str(tmp_path / "agt-formal-eval.json"),
                        "required_result_files": [
                            str(tmp_path / "native-result.json"),
                            str(tmp_path / "bridge-result.json"),
                            str(tmp_path / "policy-diff-summary.md"),
                            str(tmp_path / "rollback-note.md"),
                        ],
                        "required_fixture_files": [
                            str(fixture_one),
                            str(fixture_two),
                        ],
                        "execution_requirements": {
                            "required_commands": [],
                            "preferred_hosts": ["desk"],
                        },
                    }
                ]
            },
            "tooling-inventory.json": {"hosts": [{"id": "desk", "tools": []}]},
        }[name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_preflight.py",
            "--run-id",
            "agt-policy-plane-eval-2026q2",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["preflight_status"] == "blocked"
    assert set(record["blocking_reasons"]) == {
        f"invalid_fixture:{fixture_one}",
        f"invalid_fixture:{fixture_two}",
    }
    assert all(check["valid"] is False for check in record["fixture_file_checks"])
    assert any("missing_or_invalid_field:scenario_id" in check["errors"] for check in record["fixture_file_checks"])


def test_run_capability_pilot_formal_eval_materializes_benchmark_spec_manual_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    artifact_path = tmp_path / "agt-policy-plane-formal-eval.json"
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    benchmark_spec = tmp_path / "agt-policy-bridge.yaml"
    benchmark_spec.write_text("pilot_id: agt-policy-bridge\n", encoding="utf-8")
    native_fixture = tmp_path / "agt-native-decision-trace.json"
    bridge_fixture = tmp_path / "agt-bridge-decision-trace.json"
    native_payload = {
        "trace_id": "native-approval-held-mutation",
        "scenario_id": "approval-held-mutation",
        "request_surface": "operator_action_envelope_for_approval_gated_mutations",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "Native Athanor holds the mutation for approval.",
        "decision_reason": "approval_required gate applied",
        "allowed_actions": ["review_required"],
        "blocked_actions": ["runtime_mutation_without_approval"],
        "command_decision_record_ref": "history/overrides#decision-native",
        "operator_stream_event_ref": "history/overrides#event-native",
    }
    bridge_payload = {
        "trace_id": "bridge-approval-held-mutation",
        "scenario_id": "approval-held-mutation",
        "request_surface": "operator_action_envelope_for_approval_gated_mutations",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "AGT-backed bridge preserves the approval hold.",
        "decision_reason": "approval envelope enforced through bridge contract",
        "allowed_actions": ["review_required"],
        "blocked_actions": ["runtime_mutation_without_approval"],
        "command_decision_record_ref": "history/overrides#decision-bridge",
        "operator_stream_event_ref": "history/overrides#event-bridge",
    }
    native_fixture.write_text(json.dumps(native_payload), encoding="utf-8")
    bridge_fixture.write_text(json.dumps(bridge_payload), encoding="utf-8")
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "benchmark_spec_path": str(benchmark_spec),
                        "formal_eval_artifact_path": str(artifact_path),
                        "required_fixture_files": [
                            str(native_fixture),
                            str(bridge_fixture),
                        ],
                        "required_result_files": [
                            str(tmp_path / "agt-native-result.json"),
                            str(tmp_path / "agt-bridge-result.json"),
                            str(tmp_path / "agt-policy-diff-summary.md"),
                            str(tmp_path / "agt-rollback-note.md"),
                        ],
                    }
                ]
            }
        }[name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_eval.py",
            "--run-id",
            "agt-policy-plane-eval-2026q2",
        ],
    )

    assert module.main() == 0
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "manual_review_pending"
    assert artifact["decision_reason"] == "benchmark_spec_materialized"
    assert artifact["result_paths"][0].endswith("agt-native-result.json")
    assert json.loads((tmp_path / "agt-native-result.json").read_text(encoding="utf-8"))["trace_id"] == native_payload["trace_id"]
    assert json.loads((tmp_path / "agt-bridge-result.json").read_text(encoding="utf-8"))["trace_id"] == bridge_payload["trace_id"]
    assert "AGT Policy Bridge Diff Summary" in (tmp_path / "agt-policy-diff-summary.md").read_text(encoding="utf-8")
    assert "Rollback target" in (tmp_path / "agt-rollback-note.md").read_text(encoding="utf-8")


def test_run_capability_pilot_formal_preflight_accepts_promptfoo_runtime_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_preflight_override_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_preflight.py",
    )
    output = tmp_path / "capability-pilot-formal-preflight.json"
    promptfoo_config = tmp_path / "goose-vs-direct-cli.yaml"
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    artifact_path = tmp_path / "goose-formal-eval.json"
    result_path = tmp_path / "goose-promptfoo-results.json"

    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "promptfoo_config_path": str(promptfoo_config),
                        "formal_eval_artifact_path": str(artifact_path),
                        "required_result_files": [str(result_path)],
                        "required_env_vars": [],
                        "execution_requirements": {
                            "required_commands": ["goose"],
                            "preferred_hosts": ["desk"],
                        },
                    }
                ]
            },
            "tooling-inventory.json": {
                "hosts": [
                    {
                        "id": "desk",
                        "tools": [
                            {"command": "goose", "status": "installed", "version": "1.30.0"}
                        ],
                    }
                ]
            },
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_current_local_command_state",
        lambda command: {
            "command": command,
            "available_locally": True,
            "local_path": f"/tmp/{command}",
        },
    )
    monkeypatch.setattr(
        module,
        "_run_command_probe",
        lambda run: {
            "status": "passed",
            "command": "goose",
            "argv": ["/tmp/goose", "run"],
            "cwd": "C:/",
            "timeout_ms": 20000,
            "returncode": 0,
            "stdout_tail": "READY",
            "stderr_tail": "",
            "missing_env_hint": None,
        },
    )
    monkeypatch.setattr(
        module,
        "_promptfoo_runtime_state",
        lambda: {
            "available": True,
            "blocking_reason": None,
            "command": ["C:/Node/node.exe", "C:/Promptfoo/main.js"],
            "command_path": "C:/Node/node.exe",
            "mode": "node_cli",
            "source": "local_runtime_home",
            "cli_path": "C:/Promptfoo/main.js",
            "node_path": "C:/Node/node.exe",
            "node_version": "v22.18.0",
            "node_version_supported": True,
            "probe_attempts": [],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_preflight.py",
            "--run-id",
            "goose-operator-shell-lane-eval-2026q2",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["preflight_status"] == "ready"
    assert record["promptfoo_runtime_mode"] == "node_cli"
    assert record["promptfoo_runtime_source"] == "local_runtime_home"
    assert record["promptfoo_runtime_node_version"] == "v22.18.0"


def test_resolve_promptfoo_grader_key_uses_vault_when_local_env_is_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_key_resolution_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    monkeypatch.delenv("ATHANOR_LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.setenv("LITELLM_API_KEY", "placeholder-local-key")
    monkeypatch.setattr(
        module,
        "_read_vault_litellm_master_key",
        lambda: {
            "key": "resolved-master-key",
            "source": "vault:docker_inspect_env",
            "fingerprint": "abc123def456",
            "error": None,
        },
    )

    resolved = module._resolve_promptfoo_grader_key()
    assert resolved["key"] == "resolved-master-key"
    assert resolved["source"] == "vault:docker_inspect_env"
    assert resolved["fingerprint"] == "abc123def456"
    assert resolved["placeholder_detected"] is True


def test_run_capability_pilot_formal_eval_uses_eval_subcommand_for_promptfoo_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_promptfoo_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    artifact_path = tmp_path / "goose-formal-eval.json"
    result_path = tmp_path / "goose-promptfoo-results.json"
    promptfoo_config = tmp_path / "goose-vs-direct-cli.yaml"
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "promptfoo_config_path": str(promptfoo_config),
                        "formal_eval_artifact_path": str(artifact_path),
                        "required_result_files": [str(result_path)],
                    }
                ]
            }
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_promptfoo_runtime_state",
        lambda: {
            "available": True,
            "blocking_reason": None,
            "command": ["C:/Node/node.exe", "C:/Promptfoo/main.js"],
            "mode": "node_cli",
            "source": "local_runtime_home",
            "node_path": "C:/Node/node.exe",
            "node_version": "v22.18.0",
        },
    )
    monkeypatch.setattr(
        module,
        "_resolve_promptfoo_grader_key",
        lambda: {
            "key": "resolved-master-key",
            "source": "vault:docker_inspect_env",
            "fingerprint": "abc123def456",
            "placeholder_detected": True,
            "error": None,
        },
    )

    captured: dict[str, Any] = {}

    def _fake_run(command: list[str], **kwargs: Any):
        captured["command"] = command
        captured["env"] = kwargs.get("env")
        result_path.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_eval.py",
            "--run-id",
            "goose-operator-shell-lane-eval-2026q2",
        ],
    )

    assert module.main() == 0
    assert captured["command"][:3] == ["C:/Node/node.exe", "C:/Promptfoo/main.js", "eval"]
    assert captured["env"]["LITELLM_API_KEY"] == "resolved-master-key"
    assert captured["env"]["ATHANOR_LITELLM_API_KEY"] == "resolved-master-key"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "passed"
    assert artifact["decision_reason"] == "promptfoo_completed"
    assert artifact["grader_api_key_source"] == "vault:docker_inspect_env"
    assert artifact["grader_api_key_fingerprint"] == "abc123def456"
    assert artifact["grader_api_key_placeholder_detected"] is True


def test_run_capability_pilot_formal_eval_records_timeout_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_timeout_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    artifact_path = tmp_path / "goose-formal-eval.json"
    result_path = tmp_path / "goose-promptfoo-results.json"
    promptfoo_config = tmp_path / "goose-vs-direct-cli.yaml"
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "promptfoo_config_path": str(promptfoo_config),
                        "formal_eval_artifact_path": str(artifact_path),
                        "required_result_files": [str(result_path)],
                        "formal_eval_timeout_ms": 1234,
                    }
                ]
            }
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_promptfoo_runtime_state",
        lambda: {
            "available": True,
            "blocking_reason": None,
            "command": ["C:/Node/node.exe", "C:/Promptfoo/main.js"],
            "mode": "node_cli",
            "source": "local_runtime_home",
            "node_path": "C:/Node/node.exe",
            "node_version": "v22.18.0",
        },
    )
    monkeypatch.setattr(
        module,
        "_resolve_promptfoo_grader_key",
        lambda: {
            "key": "resolved-master-key",
            "source": "vault:docker_inspect_env",
            "fingerprint": "abc123def456",
            "placeholder_detected": True,
            "error": None,
        },
    )

    def _fake_run(command: list[str], **kwargs: Any):
        raise subprocess.TimeoutExpired(command, timeout=1.234, output=b"partial-output", stderr=b"still-running")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_eval.py",
            "--run-id",
            "goose-operator-shell-lane-eval-2026q2",
        ],
    )

    assert module.main() == 0
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "failed"
    assert artifact["decision_reason"] == "promptfoo_timeout"
    assert artifact["timeout_ms"] == 1234
    assert artifact["grader_api_key_source"] == "vault:docker_inspect_env"
    assert artifact["stdout_tail"] == "partial-output"
    assert artifact["stderr_tail"] == "still-running"


def test_run_capability_pilot_formal_eval_records_promptfoo_failure_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_failure_summary_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    artifact_path = tmp_path / "goose-formal-eval.json"
    result_path = tmp_path / "goose-promptfoo-results.json"
    promptfoo_config = tmp_path / "goose-vs-direct-cli.yaml"
    promptfoo_config.write_text("description: test\n", encoding="utf-8")
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "goose-operator-shell-lane-eval-2026q2",
                        "initiative_id": "goose-operator-shell",
                        "promptfoo_config_path": str(promptfoo_config),
                        "formal_eval_artifact_path": str(artifact_path),
                        "required_result_files": [str(result_path)],
                    }
                ]
            }
        }[name],
    )
    monkeypatch.setattr(
        module,
        "_promptfoo_runtime_state",
        lambda: {
            "available": True,
            "blocking_reason": None,
            "command": ["C:/Node/node.exe", "C:/Promptfoo/main.js"],
            "mode": "node_cli",
            "source": "local_runtime_home",
            "node_path": "C:/Node/node.exe",
            "node_version": "v22.18.0",
        },
    )
    monkeypatch.setattr(
        module,
        "_resolve_promptfoo_grader_key",
        lambda: {
            "key": "resolved-master-key",
            "source": "vault:docker_inspect_env",
            "fingerprint": "abc123def456",
            "placeholder_detected": True,
            "error": None,
        },
    )

    def _fake_run(command: list[str], **kwargs: Any):
        result_path.write_text(
            json.dumps(
                {
                    "results": {
                        "stats": {"successes": 7, "failures": 1, "errors": 0, "durationMs": 12345},
                        "results": [
                            {
                                "provider": {"label": "Goose"},
                                "success": False,
                                "score": 0.25,
                                "vars": {"task_id": "async-diff-review"},
                                "gradingResult": {
                                    "reason": "The output identifies the sync mismatch but does not recommend httpx or aiohttp.",
                                },
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 100, stdout="failed", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_eval.py",
            "--run-id",
            "goose-operator-shell-lane-eval-2026q2",
        ],
    )

    assert module.main() == 0
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "failed"
    assert artifact["decision_reason"] == "promptfoo_failed"
    assert artifact["promptfoo_summary"] == {
        "successes": 7,
        "failures": 1,
        "errors": 0,
        "duration_ms": 12345,
    }
    assert artifact["promptfoo_failed_cases"] == [
        {
            "provider": "Goose",
            "task_id": "async-diff-review",
            "score": 0.25,
            "failure_reason": "The output identifies the sync mismatch but does not recommend httpx or aiohttp.",
        }
    ]
    assert artifact["promptfoo_primary_failure_hint"] == "Goose remaining miss in task `async-diff-review`: The output identifies the sync mismatch but does not recommend httpx or aiohttp."


def test_generate_capability_pilot_readiness_reports_benchmark_spec_manual_review_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"generate_capability_pilot_readiness_benchmark_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_capability_pilot_readiness.py",
    )
    output = tmp_path / "capability-pilot-readiness.json"
    packet_path = tmp_path / "agent-governance-toolkit-policy-plane.md"
    benchmark_spec = tmp_path / "agt-policy-bridge.yaml"
    packet_path.write_text("# packet\n", encoding="utf-8")
    benchmark_spec.write_text("pilot_id: agt-policy-bridge\n", encoding="utf-8")
    pilot_evals_path = tmp_path / "capability-pilot-evals.json"
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    pilot_evals_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "pilot_eval_status": "passed",
                        "last_outcome": "passed",
                        "captured_at": "2026-04-11T18:30:00Z",
                        "proof_tier": "operator_smoke_plus_formal_scaffold",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "preflight_status": "blocked",
                        "blocking_reasons": [
                            "missing_fixture:C:\\Athanor\\evals\\pilot-agent-compare\\fixtures\\agt-native-decision-trace.json",
                            "missing_fixture:C:\\Athanor\\evals\\pilot-agent-compare\\fixtures\\agt-bridge-decision-trace.json",
                        ],
                        "captured_at": "2026-04-11T18:31:00Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "PILOT_EVALS_PATH", pilot_evals_path)
    monkeypatch.setattr(module, "PILOT_FORMAL_PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(
        module,
        "_load_json",
        lambda path: (
            {
                "lanes": [
                    {
                        "linked_capability_id": "agent-governance-toolkit-policy-plane",
                        "lane_status": "drafting_packet",
                        "promotion_packet_path": str(packet_path),
                        "next_action": "Create narrow bridge fixtures",
                    }
                ]
            }
            if Path(path) == module.DEVSTACK_LANE_REGISTRY_PATH
            else (
                json.loads(pilot_evals_path.read_text(encoding="utf-8"))
                if Path(path) == pilot_evals_path
                else json.loads(preflight_path.read_text(encoding="utf-8"))
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "capability-adoption-registry.json": {
                "capabilities": [
                    {
                        "id": "agent-governance-toolkit-policy-plane",
                        "label": "Agent Governance Toolkit Policy Plane",
                        "stage": "concept",
                    }
                ]
            },
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "run_id": "agt-policy-plane-eval-2026q2",
                        "execution_requirements": {
                            "required_commands": [],
                            "preferred_hosts": ["dev"],
                            "request_surface_hint": "narrow policy bridge",
                        },
                        "benchmark_spec_path": str(benchmark_spec),
                    }
                ]
            },
            "tooling-inventory.json": {"hosts": [{"id": "desk", "tools": []}]},
        }[name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_capability_pilot_readiness.py",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["formal_runner_support"] == "benchmark_spec_manual_review_supported"
    assert record["formal_preflight_blocker_class"] == "fixture_required"
    assert "manual contract review" in record["next_formal_gate"]
    assert "benchmark-spec runner" not in record["next_formal_gate"]



def test_run_capability_pilot_formal_preflight_resolves_windows_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_preflight_windows_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_preflight.py",
    )
    output = tmp_path / "capability-pilot-formal-preflight.json"
    benchmark_spec = tmp_path / "evals" / "pilot-agent-compare" / "agt-policy-bridge.yaml"
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("pilot_id: agt-policy-bridge\n", encoding="utf-8")
    fixture_dir = tmp_path / "evals" / "pilot-agent-compare" / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_one = fixture_dir / "agt-native-decision-trace.json"
    fixture_two = fixture_dir / "agt-bridge-decision-trace.json"
    native_payload = {
        "trace_id": "native-degraded-fallback",
        "scenario_id": "degraded-mode-fallback",
        "request_surface": "builder_policy_conflict",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "Native allows the external bootstrap fallback.",
        "decision_reason": "degraded fallback leaves bootstrap path available",
        "allowed_actions": ["fallback_to_external_bootstrap_builder"],
        "blocked_actions": [],
        "command_decision_record_ref": "history/fallback#native",
        "operator_stream_event_ref": "history/fallback#native-event",
    }
    bridge_payload = {
        "trace_id": "bridge-degraded-fallback",
        "scenario_id": "degraded-mode-fallback",
        "request_surface": "builder_policy_conflict",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "Bridge removes the external bootstrap fallback without trust.",
        "decision_reason": "trust-boundary verdict required",
        "allowed_actions": ["fallback_to_sovereign_coder"],
        "blocked_actions": ["fallback_to_external_bootstrap_builder_without_trust_verdict"],
        "command_decision_record_ref": "history/fallback#bridge",
        "operator_stream_event_ref": "history/fallback#bridge-event",
    }
    fixture_one.write_text(json.dumps(native_payload), encoding="utf-8")
    fixture_two.write_text(json.dumps(bridge_payload), encoding="utf-8")

    def _resolve(path_value):
        text = str(path_value)
        prefix = "C:/Athanor/"
        if text.startswith(prefix):
            return tmp_path / text.removeprefix(prefix)
        return Path(text)

    monkeypatch.setattr(module, "resolve_external_path", _resolve)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2-degraded-fallback",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "benchmark_spec_path": "C:/Athanor/evals/pilot-agent-compare/agt-policy-bridge.yaml",
                        "formal_eval_artifact_path": "C:/Athanor/reports/truth-inventory/agt-formal-eval.json",
                        "required_result_files": [
                            "C:/Athanor/reports/truth-inventory/agt-native-result.json",
                            "C:/Athanor/reports/truth-inventory/agt-bridge-result.json",
                            "C:/Athanor/reports/truth-inventory/agt-policy-diff-summary.md",
                            "C:/Athanor/reports/truth-inventory/agt-rollback-note.md",
                        ],
                        "required_fixture_files": [
                            "C:/Athanor/evals/pilot-agent-compare/fixtures/agt-native-decision-trace.json",
                            "C:/Athanor/evals/pilot-agent-compare/fixtures/agt-bridge-decision-trace.json",
                        ],
                        "execution_requirements": {
                            "required_commands": [],
                            "preferred_hosts": ["desk"],
                        },
                    }
                ]
            },
            "tooling-inventory.json": {"hosts": [{"id": "desk", "tools": []}]},
        }[name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_preflight.py",
            "--run-id",
            "agt-policy-plane-eval-2026q2-degraded-fallback",
            "--host-id",
            "desk",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["preflight_status"] == "ready"
    assert record["scaffold_path"] == str(benchmark_spec)
    assert record["formal_eval_artifact_path"] == str(tmp_path / "reports" / "truth-inventory" / "agt-formal-eval.json")
    assert record["required_result_files"][0] == str(tmp_path / "reports" / "truth-inventory" / "agt-native-result.json")
    assert all(check["exists"] for check in record["fixture_file_checks"])


def test_run_capability_pilot_formal_eval_resolves_windows_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"run_capability_pilot_formal_eval_windows_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_capability_pilot_formal_eval.py",
    )
    preflight_path = tmp_path / "capability-pilot-formal-preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2-degraded-fallback",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "preflight_status": "ready",
                        "blocking_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    benchmark_spec = tmp_path / "evals" / "pilot-agent-compare" / "agt-policy-bridge.yaml"
    benchmark_spec.parent.mkdir(parents=True, exist_ok=True)
    benchmark_spec.write_text("pilot_id: agt-policy-bridge\n", encoding="utf-8")
    fixture_dir = tmp_path / "evals" / "pilot-agent-compare" / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    native_fixture = fixture_dir / "agt-native-decision-trace.json"
    bridge_fixture = fixture_dir / "agt-bridge-decision-trace.json"
    native_payload = {
        "trace_id": "native-degraded-fallback",
        "scenario_id": "degraded-mode-fallback",
        "request_surface": "builder_policy_conflict",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "Native allows the external bootstrap fallback.",
        "decision_reason": "degraded fallback leaves bootstrap path available",
        "allowed_actions": ["fallback_to_external_bootstrap_builder"],
        "blocked_actions": [],
        "command_decision_record_ref": "history/fallback#native",
        "operator_stream_event_ref": "history/fallback#native-event",
    }
    bridge_payload = {
        "trace_id": "bridge-degraded-fallback",
        "scenario_id": "degraded-mode-fallback",
        "request_surface": "builder_policy_conflict",
        "policy_class": "private_but_cloud_allowed",
        "decision_summary": "Bridge removes the external bootstrap fallback without trust.",
        "decision_reason": "trust-boundary verdict required",
        "allowed_actions": ["fallback_to_sovereign_coder"],
        "blocked_actions": ["fallback_to_external_bootstrap_builder_without_trust_verdict"],
        "command_decision_record_ref": "history/fallback#bridge",
        "operator_stream_event_ref": "history/fallback#bridge-event",
    }
    native_fixture.write_text(json.dumps(native_payload), encoding="utf-8")
    bridge_fixture.write_text(json.dumps(bridge_payload), encoding="utf-8")

    def _resolve(path_value):
        text = str(path_value)
        prefix = "C:/Athanor/"
        if text.startswith(prefix):
            return tmp_path / text.removeprefix(prefix)
        return Path(text)

    monkeypatch.setattr(module, "PREFLIGHT_PATH", preflight_path)
    monkeypatch.setattr(module, "resolve_external_path", _resolve)
    monkeypatch.setattr(
        module,
        "load_registry",
        lambda name: {
            "eval-run-ledger.json": {
                "runs": [
                    {
                        "run_id": "agt-policy-plane-eval-2026q2-degraded-fallback",
                        "initiative_id": "agent-governance-toolkit-policy-plane",
                        "benchmark_spec_path": "C:/Athanor/evals/pilot-agent-compare/agt-policy-bridge.yaml",
                        "formal_eval_artifact_path": "C:/Athanor/reports/truth-inventory/agt-formal-eval.json",
                        "required_fixture_files": [
                            "C:/Athanor/evals/pilot-agent-compare/fixtures/agt-native-decision-trace.json",
                            "C:/Athanor/evals/pilot-agent-compare/fixtures/agt-bridge-decision-trace.json",
                        ],
                        "required_result_files": [
                            "C:/Athanor/reports/truth-inventory/agt-native-result.json",
                            "C:/Athanor/reports/truth-inventory/agt-bridge-result.json",
                            "C:/Athanor/reports/truth-inventory/agt-policy-diff-summary.md",
                            "C:/Athanor/reports/truth-inventory/agt-rollback-note.md",
                        ],
                    }
                ]
            }
        }[name],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_capability_pilot_formal_eval.py",
            "--run-id",
            "agt-policy-plane-eval-2026q2-degraded-fallback",
        ],
    )

    assert module.main() == 0
    artifact_path = tmp_path / "reports" / "truth-inventory" / "agt-formal-eval.json"
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "manual_review_pending"
    assert artifact["result_paths"][0] == str(tmp_path / "reports" / "truth-inventory" / "agt-native-result.json")
    assert json.loads((tmp_path / "reports" / "truth-inventory" / "agt-native-result.json").read_text(encoding="utf-8"))["trace_id"] == "native-degraded-fallback"
    assert json.loads((tmp_path / "reports" / "truth-inventory" / "agt-bridge-result.json").read_text(encoding="utf-8"))["trace_id"] == "bridge-degraded-fallback"

