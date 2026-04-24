from __future__ import annotations

import importlib.util
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


def test_build_payload_partitions_dirty_tree_and_exposes_owned_write_set() -> None:
    module = _load_module(
        f"write_current_tree_partition_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_current_tree_partition.py",
    )

    entries = [
        {"path": "scripts/run_ralph_loop_pass.py", "index_status": "M", "worktree_status": "M", "tracked": True},
        {"path": "scripts/tests/test_write_steady_state_status.py", "index_status": " ", "worktree_status": "M", "tracked": True},
        {"path": "projects/dashboard/src/lib/value-throughput.ts", "index_status": "?", "worktree_status": "?", "tracked": False},
        {"path": "projects/agents/src/athanor_agents/self_improvement.py", "index_status": " ", "worktree_status": "M", "tracked": True},
        {"path": "config/automation-backbone/economic-dispatch-ledger.json", "index_status": " ", "worktree_status": "M", "tracked": True},
        {"path": "docs/operations/RUNTIME-OWNERSHIP-REPORT.md", "index_status": " ", "worktree_status": "M", "tracked": True},
        {"path": ".data/runtime/queue-cache.json", "index_status": "?", "worktree_status": "?", "tracked": False},
        {"path": "ansible/host_vars/vault.yml", "index_status": " ", "worktree_status": "M", "tracked": True},
        {"path": "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json", "index_status": "?", "worktree_status": "?", "tracked": False},
        {"path": "docs/archive/plans/old-plan.md", "index_status": "?", "worktree_status": "?", "tracked": False},
    ]

    payload = module.build_payload(entries)

    assert payload["recommended_execution_lane"] == "partition_then_land_verified_slices"
    assert payload["dirty_path_count"] == 10
    assert payload["classification_counts"]["source_commit_candidates"] == 4
    assert payload["classification_counts"]["registry_truth_changes"] == 1
    assert payload["classification_counts"]["runtime_gated_changes"] == 2
    assert payload["classification_counts"]["local_generated_noise"] == 1
    assert payload["classification_counts"]["content_output_review"] == 1
    assert payload["classification_counts"]["archive_or_prune_review"] == 1
    assert payload["commit_candidate_paths"] == [
        "scripts/run_ralph_loop_pass.py",
        "scripts/tests/test_write_steady_state_status.py",
        "projects/dashboard/src/lib/value-throughput.ts",
        "projects/agents/src/athanor_agents/self_improvement.py",
        "config/automation-backbone/economic-dispatch-ledger.json",
    ]
    assert payload["runtime_gated_paths"] == [
        "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
        "ansible/host_vars/vault.yml",
    ]
    assert payload["local_generated_noise_paths"] == [".data/runtime/queue-cache.json"]
    assert payload["content_output_review_paths"] == [
        "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json",
    ]

    by_path = {item["path"]: item for item in payload["paths"]}
    assert by_path["scripts/run_ralph_loop_pass.py"]["classification"] == "source_commit_candidates"
    assert by_path["projects/dashboard/src/lib/value-throughput.ts"]["classification"] == "source_commit_candidates"
    assert by_path["projects/agents/src/athanor_agents/self_improvement.py"]["classification"] == "source_commit_candidates"
    assert by_path["config/automation-backbone/economic-dispatch-ledger.json"]["classification"] == "registry_truth_changes"
    assert by_path["docs/operations/RUNTIME-OWNERSHIP-REPORT.md"]["classification"] == "runtime_gated_changes"
    assert by_path[".data/runtime/queue-cache.json"]["classification"] == "local_generated_noise"
    assert by_path["docs/archive/plans/old-plan.md"]["classification"] == "archive_or_prune_review"
