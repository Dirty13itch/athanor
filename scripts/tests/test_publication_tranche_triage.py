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


def test_build_triage_bundle_prefers_specific_slice_hints_and_classifies_deferred_families(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "test-sequence",
    "slices": [
      {
        "id": "pilot",
        "title": "Pilot",
        "status": "ready_for_checkpoint",
        "publication_artifact_refs": ["projects/dashboard/src/components/operations-readiness-card.tsx"],
        "generated_artifacts": [],
        "working_tree_path_hints": ["projects/dashboard/src/app/api/governor/operator-tests/"]
      },
      {
        "id": "forge",
        "title": "Forge",
        "status": "ready_for_checkpoint",
        "publication_artifact_refs": ["STATUS.md"],
        "generated_artifacts": [],
        "working_tree_path_hints": ["projects/dashboard/"]
      }
    ],
    "deferred_families": [
      {
        "id": "operator-tooling",
        "title": "Operator Tooling",
        "disposition": "operator_tooling",
        "scope": "Helper surfaces outside the current checkpoint sequence.",
        "owner_workstreams": ["startup-docs-and-prune"],
        "path_hints": [".claude/", "README.md"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )

    repo_root = tmp_path / 'repo'
    (repo_root / 'projects/dashboard/src/components').mkdir(parents=True)
    (repo_root / 'projects/dashboard/src/app/api/governor/operator-tests').mkdir(parents=True)
    (repo_root / 'projects/dashboard/src/components/operations-readiness-card.tsx').write_text('// ui\n', encoding='utf-8')

    entries = [
        {'status': ' M', 'path': 'projects/dashboard/src/components/operations-readiness-card.tsx'},
        {'status': ' M', 'path': 'projects/dashboard/src/app/api/governor/operator-tests/route.ts'},
        {'status': ' M', 'path': 'projects/dashboard/src/app/page.tsx'},
        {'status': '??', 'path': '.claude/hooks/session-start.sh'},
        {'status': '??', 'path': 'output/local.json'},
        {'status': '??', 'path': 'misc/unclassified.txt'},
    ]
    monkeypatch.setattr(module, '_git_status_entries', lambda _repo_root: entries)

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)

    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}
    assert bundle['active_sequence_id'] == 'test-sequence'
    assert slices['pilot']['match_count'] == 2
    assert slices['forge']['match_count'] == 1
    assert deferred_families['operator-tooling']['match_count'] == 1
    assert bundle['summary']['ambiguous_entries'] == 0
    assert bundle['summary']['local_noise_entries'] == 1
    assert bundle['summary']['unclassified_entries'] == 1



def test_build_triage_bundle_ignores_self_managed_publication_outputs(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-self",
    "slices": [
      {
        "id": "backbone",
        "title": "Backbone",
        "status": "published",
        "publication_artifact_refs": ["docs/operations/PUBLICATION-PROVENANCE-REPORT.md"],
        "generated_artifacts": [],
        "working_tree_path_hints": ["docs/operations/"]
      }
    ],
    "deferred_families": []
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text(
        """{
  "documents": [
    {
      "path": "docs/operations/PUBLICATION-TRIAGE-REPORT.md",
      "generator": "python scripts/triage_publication_tranche.py --write docs/operations/PUBLICATION-TRIAGE-REPORT.md"
    },
    {
      "path": "docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md",
      "generator": "python scripts/generate_publication_deferred_family_queue.py"
    },
    {
      "path": "docs/operations/STEADY-STATE-STATUS.md",
      "generator": "python scripts/write_steady_state_status.py"
    },
    {
      "path": "docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md",
      "generator": "python scripts/generate_full_system_audit.py"
    },
    {
      "path": "docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md",
      "generator": "python scripts/generate_ecosystem_master_plan.py"
    },
    {
      "path": "docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md",
      "generator": "python scripts/generate_ecosystem_master_plan.py"
    }
  ]
}""",
        encoding='utf-8',
    )

    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    monkeypatch.setattr(
        module,
        '_git_status_entries',
        lambda _repo_root: [
            {'status': ' M', 'path': 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'},
            {'status': ' M', 'path': 'docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md'},
            {'status': ' M', 'path': 'docs/operations/STEADY-STATE-STATUS.md'},
            {'status': ' M', 'path': 'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md'},
            {'status': ' M', 'path': 'docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md'},
            {'status': ' M', 'path': 'docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md'},
            {'status': '??', 'path': 'reports/truth-inventory/publication-deferred-family-queue.json'},
            {'status': '??', 'path': 'reports/truth-inventory/steady-state-status.json'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    assert bundle['summary']['dirty_entries'] == 0
    assert bundle['summary']['slice_matched_entries'] == 0
    assert bundle['slices'][0]['match_count'] == 0


def test_render_markdown_surfaces_deferred_family_and_unclassified_entries(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-2",
    "slices": [
      {
        "id": "backbone",
        "title": "Backbone",
        "status": "ready_for_checkpoint",
        "publication_artifact_refs": ["docs/operations/PUBLICATION-PROVENANCE-REPORT.md"],
        "generated_artifacts": [],
        "working_tree_path_hints": ["docs/operations/"]
      }
    ],
    "deferred_families": [
      {
        "id": "archive",
        "title": "Archive",
        "disposition": "archive_or_reference",
        "scope": "Historical material outside the current checkpoint wave.",
        "owner_workstreams": ["startup-docs-and-prune"],
        "path_hints": ["docs/archive/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )

    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    monkeypatch.setattr(
        module,
        '_git_status_entries',
        lambda _repo_root: [
            {'status': '??', 'path': 'docs/archive/old.md'},
            {'status': '??', 'path': 'misc/file.txt'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    rendered = module.render_markdown(bundle, limit=5)

    assert 'Publication Triage Summary' in rendered
    assert 'Deferred Family Coverage' in rendered
    assert '`archive`' in rendered
    assert 'Unclassified Entries' in rendered



def test_main_does_not_rewrite_markdown_output_when_only_generated_timestamp_changes(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-3",
    "slices": [
      {
        "id": "backbone",
        "title": "Backbone",
        "status": "published",
        "publication_artifact_refs": ["docs/operations/PUBLICATION-PROVENANCE-REPORT.md"],
        "generated_artifacts": [],
        "working_tree_path_hints": ["docs/operations/"]
      }
    ],
    "deferred_families": []
  }
}""",
        encoding='utf-8',
    )

    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    monkeypatch.setattr(module, '_git_status_entries', lambda _repo_root: [])
    monkeypatch.setattr(module, '_iso_now', lambda: '2026-04-16T19:00:00+00:00')
    initial_bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    output_path = tmp_path / 'PUBLICATION-TRIAGE-REPORT.md'
    output_path.write_text(module.render_markdown(initial_bundle), encoding='utf-8')
    initial_text = output_path.read_text(encoding='utf-8')

    monkeypatch.setattr(module, '_iso_now', lambda: '2026-04-16T20:00:00+00:00')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'triage_publication_tranche.py',
            '--repo-root',
            str(repo_root),
            '--registry',
            str(registry_path),
            '--write',
            str(output_path),
        ],
    )

    assert module.main() == 0
    assert output_path.read_text(encoding='utf-8') == initial_text


def test_git_status_entries_falls_back_to_native_git_when_windows_git_fails(tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    repo_root = tmp_path / 'repo'
    repo_root.mkdir()

    commands: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int, stdout: str = '', stderr: str = '') -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(command, **kwargs):
        commands.append(list(command))
        if len(commands) == 1:
            return _Result(returncode=1, stderr='vsock failure')
        return _Result(returncode=0, stdout=' M scripts/example.py\n')

    original_windows_git = module.WINDOWS_GIT_EXE
    original_to_windows_path = module._to_windows_path
    original_run = module.subprocess.run
    module.WINDOWS_GIT_EXE = tmp_path / 'git.exe'
    module.WINDOWS_GIT_EXE.write_text('', encoding='utf-8')
    module._to_windows_path = lambda _path: 'C:\\repo'
    module.subprocess.run = _fake_run
    try:
        entries = module._git_status_entries(repo_root)
    finally:
        module.WINDOWS_GIT_EXE = original_windows_git
        module._to_windows_path = original_to_windows_path
        module.subprocess.run = original_run

    assert len(commands) == 2
    assert commands[0][0].endswith('git.exe')
    assert commands[1][0] == 'git'
    assert entries == [{'status': ' M', 'path': 'scripts/example.py'}]
