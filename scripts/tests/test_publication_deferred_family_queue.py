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
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    docs_lifecycle_registry_path.write_text('{"documents": []}', encoding='utf-8')
    fallback_registry_path = registry_path
    fallback_docs_lifecycle_registry_path = docs_lifecycle_registry_path

    entries = [
        {'status': ' M', 'path': 'docs/REFERENCE-INDEX.md'},
        {'status': ' M', 'path': 'docs/MASTER-PLAN.md'},
        {'status': ' M', 'path': 'services/brain/main.py'},
    ]
    monkeypatch.setattr(triage_module, '_git_status_entries', lambda _repo_root: entries)
    monkeypatch.setattr(
        queue_module,
        'build_triage_bundle',
        lambda repo_root, registry_path=None, docs_lifecycle_registry_path=None: triage_module.build_triage_bundle(
            repo_root=repo_root,
            registry_path=registry_path or fallback_registry_path,
            docs_lifecycle_registry_path=docs_lifecycle_registry_path or fallback_docs_lifecycle_registry_path,
        ),
    )

    bundle = queue_module.build_queue_bundle(
        repo_root=tmp_path,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    assert bundle['next_recommended_family']['id'] == 'reference'
    assert bundle['families'][0]['id'] == 'reference'
    assert bundle['families'][0]['match_count'] == 2
    assert bundle['families'][1]['id'] == 'runtime'
    assert 'Next Recommended Tranche' in queue_module.render_markdown(bundle)



def test_build_queue_bundle_surfaces_first_control_plane_subfamily_as_next_tranche(monkeypatch, tmp_path: Path) -> None:
    queue_module = _load_module(
        f"publication_deferred_queue_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'generate_publication_deferred_family_queue.py',
    )

    triage_bundle = {
        'active_sequence_id': 'sequence',
        'summary': {
            'dirty_entries': 4,
            'slice_matched_entries': 0,
            'deferred_entries': 3,
        },
        'deferred_families': [
            {
                'id': 'control-plane-registry-and-routing',
                'title': 'Control-Plane Registry and Routing',
                'disposition': 'deferred_out_of_sequence',
                'execution_rank': 6,
                'execution_class': 'program_slice',
                'next_action': 'Split registry and routing policy residue.',
                'success_condition': 'Registry/routing residue is isolated.',
                'owner_workstreams': ['authority-and-mainline'],
                'match_count': 2,
                'path_hints': ['config/automation-backbone/'],
                'matched_entries': [{'path': 'config/automation-backbone/economic-dispatch-ledger.json'}],
                'scope': 'Registry and routing policy surfaces.',
            },
            {
                'id': 'agent-execution-kernel-follow-on',
                'title': 'Agent Execution Kernel Follow-on',
                'disposition': 'deferred_out_of_sequence',
                'execution_rank': 7,
                'execution_class': 'program_slice',
                'next_action': 'Bound the execution kernel.',
                'success_condition': 'Execution-kernel residue is isolated.',
                'owner_workstreams': ['authority-and-mainline'],
                'match_count': 1,
                'path_hints': ['projects/agents/src/athanor_agents/operator_work.py'],
                'matched_entries': [{'path': 'projects/agents/src/athanor_agents/operator_work.py'}],
                'scope': 'Execution kernel surfaces.',
            },
            {
                'id': 'control-plane-proof-and-ops-follow-on',
                'title': 'Control-Plane Proof and Ops Follow-on',
                'disposition': 'deferred_out_of_sequence',
                'execution_rank': 9,
                'execution_class': 'program_slice',
                'next_action': 'Split proof and ops residue.',
                'success_condition': 'Proof/ops residue is isolated.',
                'owner_workstreams': ['validation-and-publication'],
                'match_count': 0,
                'path_hints': ['scripts/'],
                'matched_entries': [],
                'scope': 'Proof and ops surfaces.',
            },
        ],
    }

    monkeypatch.setattr(
        queue_module,
        'build_triage_bundle',
        lambda repo_root, registry_path=None, docs_lifecycle_registry_path=None: triage_bundle,
    )
    monkeypatch.setattr(queue_module, '_publication_config_fingerprint', lambda _path: 'fingerprint')

    bundle = queue_module.build_queue_bundle(
        repo_root=tmp_path,
        registry_path=tmp_path / 'completion-program-registry.json',
        docs_lifecycle_registry_path=tmp_path / 'docs-lifecycle-registry.json',
    )

    assert bundle['next_recommended_family']['id'] == 'control-plane-registry-and-routing'
    assert [item['id'] for item in bundle['families']] == [
        'control-plane-registry-and-routing',
        'agent-execution-kernel-follow-on',
        'control-plane-proof-and-ops-follow-on',
    ]


def test_build_queue_bundle_advances_to_next_family_once_control_plane_family_is_fully_claimed(monkeypatch, tmp_path: Path) -> None:
    queue_module = _load_module(
        f"publication_deferred_queue_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'generate_publication_deferred_family_queue.py',
    )

    triage_bundle = {
        'active_sequence_id': 'sequence',
        'summary': {
            'dirty_entries': 6,
            'slice_matched_entries': 6,
            'deferred_entries': 3,
        },
        'deferred_families': [
            {
                'id': 'control-plane-registry-and-routing',
                'title': 'Control-Plane Registry and Routing',
                'disposition': 'deferred_out_of_sequence',
                'execution_rank': 6,
                'execution_class': 'program_slice',
                'next_action': 'Split registry and routing policy residue.',
                'success_condition': 'Registry/routing residue is isolated.',
                'owner_workstreams': ['authority-and-mainline'],
                'match_count': 0,
                'path_hints': ['config/automation-backbone/'],
                'matched_entries': [],
                'scope': 'Registry and routing policy surfaces.',
            },
            {
                'id': 'agent-execution-kernel-follow-on',
                'title': 'Agent Execution Kernel Follow-on',
                'disposition': 'deferred_out_of_sequence',
                'execution_rank': 7,
                'execution_class': 'program_slice',
                'next_action': 'Bound the execution kernel.',
                'success_condition': 'Execution-kernel residue is isolated.',
                'owner_workstreams': ['authority-and-mainline'],
                'match_count': 3,
                'path_hints': ['projects/agents/src/athanor_agents/operator_work.py'],
                'matched_entries': [{'path': 'projects/agents/src/athanor_agents/operator_work.py'}],
                'scope': 'Execution kernel surfaces.',
            },
        ],
    }

    monkeypatch.setattr(
        queue_module,
        'build_triage_bundle',
        lambda repo_root, registry_path=None, docs_lifecycle_registry_path=None: triage_bundle,
    )
    monkeypatch.setattr(queue_module, '_publication_config_fingerprint', lambda _path: 'fingerprint')

    bundle = queue_module.build_queue_bundle(
        repo_root=tmp_path,
        registry_path=tmp_path / 'completion-program-registry.json',
        docs_lifecycle_registry_path=tmp_path / 'docs-lifecycle-registry.json',
    )

    assert bundle['next_recommended_family']['id'] == 'agent-execution-kernel-follow-on'


def test_check_does_not_report_stale_when_triage_is_newer_but_outputs_match(monkeypatch, tmp_path: Path) -> None:
    queue_module = _load_module(
        f"publication_deferred_queue_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'generate_publication_deferred_family_queue.py',
    )

    bundle = {
        'publication_config_fingerprint': 'fingerprint',
        'active_sequence_id': 'sequence',
        'dirty_entries': 0,
        'slice_matched_entries': 0,
        'deferred_entries': 0,
        'deferred_family_count': 1,
        'next_recommended_family': None,
        'families': [
            {
                'id': 'reference',
                'title': 'Reference',
                'disposition': 'archive_or_reference',
                'execution_rank': 1,
                'execution_class': 'cash_now',
                'next_action': 'Prune stale references.',
                'success_condition': 'No stale active references remain.',
                'owner_workstreams': ['startup-docs-and-prune'],
                'match_count': 0,
                'path_hints': ['docs/'],
                'sample_paths': [],
                'scope': 'Reference docs.',
            }
        ],
    }
    repo_root = tmp_path / 'repo'
    markdown_output = repo_root / 'docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md'
    json_output = repo_root / 'reports/truth-inventory/publication-deferred-family-queue.json'
    triage_output = repo_root / 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    triage_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(queue_module.render_markdown(bundle), encoding='utf-8')
    json_output.write_text(queue_module._json_render(bundle), encoding='utf-8')
    triage_output.write_text('newer triage marker\n', encoding='utf-8')

    monkeypatch.setattr(queue_module, '_publication_config_fingerprint', lambda _path: 'fingerprint')

    assert queue_module._check_via_dependency_freshness(
        repo_root=repo_root,
        registry_path=repo_root / 'completion-program-registry.json',
        markdown_output=markdown_output,
        json_output=json_output,
    ) == 0


def test_main_does_not_rewrite_outputs_when_bundle_is_unchanged(monkeypatch, tmp_path: Path) -> None:
    queue_module = _load_module(
        f"publication_deferred_queue_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'generate_publication_deferred_family_queue.py',
    )

    bundle = {
        'publication_config_fingerprint': 'fingerprint',
        'active_sequence_id': 'sequence',
        'dirty_entries': 0,
        'slice_matched_entries': 0,
        'deferred_entries': 0,
        'deferred_family_count': 1,
        'next_recommended_family': None,
        'families': [
            {
                'id': 'reference',
                'title': 'Reference',
                'disposition': 'archive_or_reference',
                'execution_rank': 1,
                'execution_class': 'cash_now',
                'next_action': 'Prune stale references.',
                'success_condition': 'No stale active references remain.',
                'owner_workstreams': ['startup-docs-and-prune'],
                'match_count': 0,
                'path_hints': ['docs/'],
                'sample_paths': [],
                'scope': 'Reference docs.',
            }
        ],
    }
    markdown_output = tmp_path / 'PUBLICATION-DEFERRED-FAMILY-QUEUE.md'
    json_output = tmp_path / 'publication-deferred-family-queue.json'
    markdown_output.write_text(queue_module.render_markdown(bundle), encoding='utf-8')
    json_output.write_text(queue_module._json_render(bundle), encoding='utf-8')
    initial_markdown = markdown_output.read_text(encoding='utf-8')
    initial_json = json_output.read_text(encoding='utf-8')

    monkeypatch.setattr(
        queue_module,
        'build_queue_bundle',
        lambda repo_root, registry_path=None, docs_lifecycle_registry_path=None: bundle,
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'generate_publication_deferred_family_queue.py',
            '--repo-root',
            str(tmp_path),
            '--markdown-output',
            str(markdown_output),
            '--json-output',
            str(json_output),
        ],
    )

    assert queue_module.main() == 0
    assert markdown_output.read_text(encoding='utf-8') == initial_markdown
    assert json_output.read_text(encoding='utf-8') == initial_json
