from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / 'scripts'

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


def test_build_queue_bundle_orders_families_and_surfaces_next_tranche(monkeypatch, tmp_path: Path) -> None:
    triage_module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )
    queue_module = _load_module(
        f"publication_deferred_queue_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'generate_publication_deferred_family_queue.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence",
    "slices": [],
    "deferred_families": [
      {
        "id": "reference",
        "title": "Reference",
        "disposition": "archive_or_reference",
        "scope": "Reference docs.",
        "execution_rank": 1,
        "execution_class": "cash_now",
        "next_action": "Prune stale references.",
        "success_condition": "No stale active references remain.",
        "owner_workstreams": ["startup-docs-and-prune"],
        "path_hints": ["docs/"]
      },
      {
        "id": "runtime",
        "title": "Runtime",
        "disposition": "runtime_follow_on",
        "scope": "Runtime services.",
        "execution_rank": 2,
        "execution_class": "bounded_follow_on",
        "next_action": "Packet runtime deltas.",
        "success_condition": "Runtime deltas are packet-backed.",
        "owner_workstreams": ["runtime-sync-and-governed-packets"],
        "path_hints": ["services/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )

    entries = [
        {'status': ' M', 'path': 'docs/REFERENCE-INDEX.md'},
        {'status': ' M', 'path': 'docs/MASTER-PLAN.md'},
        {'status': ' M', 'path': 'services/brain/main.py'},
    ]
    monkeypatch.setattr(triage_module, '_git_status_entries', lambda _repo_root: entries)
    monkeypatch.setattr(queue_module, 'build_triage_bundle', lambda repo_root: triage_module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path))

    bundle = queue_module.build_queue_bundle(repo_root=tmp_path)
    assert bundle['next_recommended_family']['id'] == 'reference'
    assert bundle['families'][0]['id'] == 'reference'
    assert bundle['families'][0]['match_count'] == 2
    assert bundle['families'][1]['id'] == 'runtime'
    assert 'Next Recommended Tranche' in queue_module.render_markdown(bundle)
