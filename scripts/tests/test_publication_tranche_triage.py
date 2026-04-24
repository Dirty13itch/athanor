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
        {'status': '??', 'path': '.data/builder-runs/session-1/codex-events.jsonl'},
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
    assert bundle['summary']['local_noise_entries'] == 2
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
      "path": "docs/DOCUMENTATION-INDEX.md",
      "generator": "python scripts/generate_documentation_index.py"
    },
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
    },
    {
      "path": "docs/operations/REPO-ROOTS-REPORT.md",
      "generator": "python scripts/generate_truth_inventory_reports.py"
    },
    {
      "path": "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
      "generator": "python scripts/generate_truth_inventory_reports.py"
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
            {'status': ' M', 'path': 'docs/DOCUMENTATION-INDEX.md'},
            {'status': ' M', 'path': 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'},
            {'status': ' M', 'path': 'docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md'},
            {'status': ' M', 'path': 'docs/operations/STEADY-STATE-STATUS.md'},
            {'status': ' M', 'path': 'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md'},
            {'status': ' M', 'path': 'docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md'},
            {'status': ' M', 'path': 'docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md'},
            {'status': ' M', 'path': 'docs/operations/REPO-ROOTS-REPORT.md'},
            {'status': ' M', 'path': 'docs/operations/RUNTIME-OWNERSHIP-REPORT.md'},
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


def test_build_triage_bundle_ignores_generated_value_and_project_factory_outputs(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-generated-proof",
    "slices": [],
    "deferred_families": [
      {
        "id": "reference-and-archive-prune",
        "title": "Reference and Archive Prune",
        "disposition": "archive_or_reference",
        "scope": "Stale reference surfaces.",
        "owner_workstreams": ["startup-docs-and-prune"],
        "path_hints": ["docs/operations/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text(
        """{
  "documents": [
    {
      "path": "docs/operations/AUTONOMOUS-VALUE-STATUS.md",
      "generator": "python scripts/write_autonomous_value_proof.py"
    },
    {
      "path": "docs/operations/PROJECT-OUTPUT-PROOF.md",
      "generator": "python scripts/write_project_output_proof.py"
    },
    {
      "path": "docs/operations/PROJECT-OUTPUT-READINESS.md",
      "generator": "python scripts/write_project_output_readiness.py"
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
            {'status': ' M', 'path': 'docs/operations/AUTONOMOUS-VALUE-STATUS.md'},
            {'status': ' M', 'path': 'docs/operations/PROJECT-OUTPUT-PROOF.md'},
            {'status': ' M', 'path': 'docs/operations/PROJECT-OUTPUT-READINESS.md'},
            {'status': '??', 'path': 'reports/truth-inventory/autonomous-value-proof.json'},
            {'status': '??', 'path': 'reports/truth-inventory/project-output-proof.json'},
            {'status': '??', 'path': 'reports/truth-inventory/project-output-readiness.json'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )

    deferred = bundle['deferred_families'][0]
    assert bundle['summary']['dirty_entries'] == 0
    assert bundle['summary']['deferred_entries'] == 0
    assert deferred['match_count'] == 0
    assert deferred['matched_entries'] == []


def test_build_triage_bundle_ignores_governed_project_output_paths(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    project_output_candidates_path = tmp_path / 'project-output-candidates.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-tenant-product-lanes",
    "slices": [],
    "deferred_families": [
      {
        "id": "tenant-product-lanes",
        "title": "Tenant Product Lanes",
        "disposition": "tenant_surface",
        "scope": "Tenant and product-lane repos outside checkpoint publication.",
        "owner_workstreams": ["tenant-architecture-and-classification"],
        "path_hints": ["projects/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text('{"documents": []}', encoding='utf-8')
    project_output_candidates_path.write_text(
        """{
  "candidates": [
    {
      "candidate_id": "eoq-courtyard-scene-pack-alpha",
      "project_id": "eoq",
      "deliverable_refs": [
        "projects/eoq/NEW/courtyard-scene-pack-alpha/courtyard-20260420.png",
        "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json"
      ],
      "manifest_ref": "projects/eoq/NEW/courtyard-scene-pack-alpha/manifest.json",
      "source_generator": "projects/eoq/scripts/generate_scene_pack.py",
      "workflow_refs": [
        "projects/eoq/comfyui/flux-scene.json"
      ],
      "verification_refs": [
        "projects/eoq/NEW/MANIFEST.md"
      ],
      "acceptance_proof_refs": [
        "reports/truth-inventory/project-output-acceptance/eoq-courtyard-scene-pack-alpha.json"
      ]
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
            {'status': '??', 'path': 'projects/eoq/NEW/'},
            {'status': '??', 'path': 'projects/eoq/scripts/'},
            {'status': '??', 'path': 'projects/other/tmp.txt'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
        project_output_candidates_path=project_output_candidates_path,
    )

    deferred = bundle['deferred_families'][0]
    assert bundle['summary']['dirty_entries'] == 1
    assert bundle['summary']['deferred_entries'] == 1
    assert deferred['match_count'] == 1
    assert deferred['matched_entries'] == [{'status': '??', 'path': 'projects/other/tmp.txt'}]


def test_build_triage_bundle_classifies_dashboard_deployment_authority_into_runtime_slice(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-runtime-dashboard",
    "slices": [
      {
        "id": "runtime-ownership-provider-truth-and-reconciliation",
        "title": "Runtime Ownership, Provider Truth, and Reconciliation",
        "status": "published",
        "publication_artifact_refs": [
          "ansible/roles/dashboard/defaults/main.yml",
          "ansible/roles/dashboard/tasks/main.yml",
          "ansible/roles/dashboard/templates/docker-compose.yml.j2"
        ],
        "generated_artifacts": [],
        "working_tree_path_hints": [
          "ansible/roles/dashboard/defaults/main.yml",
          "ansible/roles/dashboard/tasks/main.yml",
          "ansible/roles/dashboard/templates/docker-compose.yml.j2"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "deployment-authority-follow-on",
        "title": "Deployment Authority Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Unowned deployment authority paths.",
        "owner_workstreams": ["deployment-authority-reconciliation"],
        "path_hints": ["ansible/"]
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
            {'status': ' M', 'path': 'ansible/roles/dashboard/defaults/main.yml'},
            {'status': ' M', 'path': 'ansible/roles/dashboard/tasks/main.yml'},
            {'status': ' M', 'path': 'ansible/roles/dashboard/templates/docker-compose.yml.j2'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)

    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['runtime-ownership-provider-truth-and-reconciliation']['match_count'] == 3
    assert deferred_families['deployment-authority-follow-on']['match_count'] == 0


def test_build_triage_bundle_ignores_contract_healer_artifact_output(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-contract-healer",
    "slices": [],
    "deferred_families": [
      {
        "id": "audit-and-eval-artifacts",
        "title": "Audit and Eval Artifacts",
        "disposition": "audit_artifact",
        "scope": "Eval and audit proof outputs.",
        "owner_workstreams": ["validation-and-publication"],
        "path_hints": ["audit/", "evals/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text('{"documents": []}', encoding='utf-8')

    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    monkeypatch.setattr(
        module,
        '_git_status_entries',
        lambda _repo_root: [
            {'status': ' M', 'path': 'audit/automation/contract-healer-latest.json'},
            {'status': ' M', 'path': 'evals/pilot-agent-compare/README.md'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    deferred = bundle['deferred_families'][0]

    assert bundle['summary']['dirty_entries'] == 1
    assert deferred['match_count'] == 1
    assert deferred['matched_entries'] == [{'status': ' M', 'path': 'evals/pilot-agent-compare/README.md'}]


def test_build_triage_bundle_routes_reference_archive_and_deploy_packet_paths_into_owned_slices(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "slice-ownership-test",
    "slices": [
      {
        "id": "backbone",
        "title": "Backbone",
        "status": "published",
        "publication_artifact_refs": [
          "docs/archive/plans/2026-04-19-athanor-blocker-closure-program.md",
          "docs/operations/REFERENCE-AND-ARCHIVE-PRUNE-PACKET.md"
        ],
        "generated_artifacts": [],
        "working_tree_path_hints": [
          "docs/superpowers/",
          "docs/archive/plans/2026-04-19-athanor-blocker-closure-program.md",
          "docs/operations/REFERENCE-AND-ARCHIVE-PRUNE-PACKET.md"
        ]
      },
      {
        "id": "runtime",
        "title": "Runtime Ownership",
        "status": "published",
        "publication_artifact_refs": [
          "ansible/roles/open-webui/templates/docker-compose.yml.j2",
          "docs/operations/WORKSHOP-OPEN-WEBUI-COMPOSE-RECONCILIATION-PACKET.md"
        ],
        "generated_artifacts": [],
        "working_tree_path_hints": [
          "ansible/roles/open-webui/",
          "docs/operations/WORKSHOP-OPEN-WEBUI-COMPOSE-RECONCILIATION-PACKET.md"
        ]
      },
      {
        "id": "deploy",
        "title": "Deploy Helpers",
        "status": "active",
        "publication_artifact_refs": [
          "ansible/roles/agents/templates/docker-compose.yml.j2",
          "docs/operations/CONTROL-PLANE-DEPLOY-AND-RUNTIME-OPS-HELPERS-PACKET.md"
        ],
        "generated_artifacts": [],
        "working_tree_path_hints": [
          "ansible/roles/agents/templates/docker-compose.yml.j2",
          "docs/operations/CONTROL-PLANE-DEPLOY-AND-RUNTIME-OPS-HELPERS-PACKET.md"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "reference-and-archive-prune",
        "title": "Reference and Archive Prune",
        "disposition": "archive_or_reference",
        "scope": "Stale reference surfaces.",
        "owner_workstreams": ["startup-docs-and-prune"],
        "path_hints": ["docs/archive/", "docs/"]
      },
      {
        "id": "deployment-authority-follow-on",
        "title": "Deployment Authority Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Unowned deployment authority paths.",
        "owner_workstreams": ["deployment-authority-reconciliation"],
        "path_hints": ["ansible/"]
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
            {'status': ' D', 'path': 'docs/superpowers/plans/2026-04-19-athanor-blocker-closure-program.md'},
            {'status': '??', 'path': 'docs/archive/plans/2026-04-19-athanor-blocker-closure-program.md'},
            {'status': '??', 'path': 'docs/operations/REFERENCE-AND-ARCHIVE-PRUNE-PACKET.md'},
            {'status': ' M', 'path': 'ansible/roles/agents/templates/docker-compose.yml.j2'},
            {'status': '??', 'path': 'docs/operations/WORKSHOP-OPEN-WEBUI-COMPOSE-RECONCILIATION-PACKET.md'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)

    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['backbone']['match_count'] == 3
    assert slices['runtime']['match_count'] == 1
    assert slices['deploy']['match_count'] == 1
    assert deferred_families['reference-and-archive-prune']['match_count'] == 0
    assert deferred_families['deployment-authority-follow-on']['match_count'] == 0


def test_build_triage_bundle_ignores_lifecycle_managed_eval_reference(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-lifecycle-eval",
    "slices": [],
    "deferred_families": [
      {
        "id": "audit-and-eval-artifacts",
        "title": "Audit and Eval Artifacts",
        "disposition": "audit_artifact",
        "scope": "Eval and audit proof outputs.",
        "owner_workstreams": ["validation-and-publication"],
        "path_hints": ["evals/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text(
        """{
  "documents": [
    {
      "path": "evals/pilot-agent-compare/README.md",
      "class": "reference",
      "owner": "shaun"
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
            {'status': ' M', 'path': 'evals/pilot-agent-compare/README.md'},
            {'status': ' M', 'path': 'evals/pilot-agent-compare/openhands-vs-native-worker.yaml'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    deferred = bundle['deferred_families'][0]

    assert bundle['summary']['dirty_entries'] == 1
    assert deferred['match_count'] == 1
    assert deferred['matched_entries'] == [
        {'status': ' M', 'path': 'evals/pilot-agent-compare/openhands-vs-native-worker.yaml'}
    ]


def test_build_triage_bundle_ignores_lifecycle_managed_ui_audit_reference(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    docs_lifecycle_registry_path = tmp_path / 'docs-lifecycle-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-ui-audit",
    "slices": [],
    "deferred_families": [
      {
        "id": "audit-and-eval-artifacts",
        "title": "Audit and Eval Artifacts",
        "disposition": "audit_artifact",
        "scope": "Eval and audit proof outputs.",
        "owner_workstreams": ["validation-and-publication"],
        "path_hints": ["tests/ui-audit/"]
      }
    ]
  }
}""",
        encoding='utf-8',
    )
    docs_lifecycle_registry_path.write_text(
        """{
  "documents": [
    {"path": "tests/ui-audit/last-run.json", "class": "reference"},
    {"path": "tests/ui-audit/surface-registry.json", "class": "reference"},
    {"path": "tests/ui-audit/uncovered-surfaces.json", "class": "reference"}
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
            {'status': ' M', 'path': 'tests/ui-audit/last-run.json'},
            {'status': ' M', 'path': 'tests/ui-audit/surface-registry.json'},
            {'status': ' M', 'path': 'tests/ui-audit/uncovered-surfaces.json'},
        ],
    )

    bundle = module.build_triage_bundle(
        repo_root=repo_root,
        registry_path=registry_path,
        docs_lifecycle_registry_path=docs_lifecycle_registry_path,
    )
    deferred = bundle['deferred_families'][0]

    assert bundle['summary']['dirty_entries'] == 0
    assert bundle['summary']['deferred_entries'] == 0
    assert deferred['match_count'] == 0
    assert deferred['matched_entries'] == []


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



def test_build_triage_bundle_decomposes_control_plane_follow_on_into_specific_families(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-control-plane",
    "slices": [],
    "deferred_families": [
      {
        "id": "control-plane-registry-and-routing",
        "title": "Control-Plane Registry and Routing",
        "disposition": "deferred_out_of_sequence",
        "scope": "Registry, routing, and dispatch policy surfaces.",
        "execution_rank": 6,
        "execution_class": "program_slice",
        "next_action": "Split registry and routing policy residue into a bounded follow-on tranche.",
        "success_condition": "Registry/routing residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "config/automation-backbone/",
          "projects/agents/config/subscription-routing-policy.yaml",
          "projects/agents/src/athanor_agents/backbone.py",
          "projects/agents/src/athanor_agents/model_governance.py",
          "projects/agents/src/athanor_agents/subscriptions.py"
        ]
      },
      {
        "id": "agent-execution-kernel-follow-on",
        "title": "Agent Execution Kernel Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Agent execution, scheduler, queue, and proving logic.",
        "execution_rank": 7,
        "execution_class": "program_slice",
        "next_action": "Bound the agent execution kernel into a publication-ready tranche.",
        "success_condition": "Execution-kernel residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "projects/agents/src/athanor_agents/operator_work.py",
          "projects/agents/src/athanor_agents/scheduler.py",
          "projects/agents/src/athanor_agents/self_improvement.py"
        ]
      },
      {
        "id": "agent-route-contract-follow-on",
        "title": "Agent Route Contract Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "HTTP route and route-contract residue.",
        "execution_rank": 8,
        "execution_class": "program_slice",
        "next_action": "Split route surfaces and route contracts into a bounded tranche.",
        "success_condition": "Route-contract residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "projects/agents/src/athanor_agents/routes/",
          "projects/agents/tests/test_operator_work_route_contract.py"
        ]
      },
      {
        "id": "control-plane-proof-and-ops-follow-on",
        "title": "Control-Plane Proof and Ops Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Control-plane proof scripts and ops automation residue.",
        "execution_rank": 9,
        "execution_class": "program_slice",
        "next_action": "Split proof and ops scripts into a bounded tranche.",
        "success_condition": "Proof/ops residue is isolated and publication-ready.",
        "owner_workstreams": ["validation-and-publication"],
        "path_hints": [
          "scripts/run_ralph_loop_pass.py",
          "scripts/write_steady_state_status.py",
          "scripts/tests/test_ralph_loop_contracts.py"
        ]
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
            {'status': ' M', 'path': 'config/automation-backbone/economic-dispatch-ledger.json'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/operator_work.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/operator_work.py'},
            {'status': ' M', 'path': 'scripts/run_ralph_loop_pass.py'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert bundle['summary']['dirty_entries'] == 4
    assert bundle['summary']['unclassified_entries'] == 0
    assert deferred_families['control-plane-registry-and-routing']['match_count'] == 1
    assert deferred_families['agent-execution-kernel-follow-on']['match_count'] == 1
    assert deferred_families['agent-route-contract-follow-on']['match_count'] == 1
    assert deferred_families['control-plane-proof-and-ops-follow-on']['match_count'] == 1


def test_build_triage_bundle_prefers_registry_ledgers_slice_over_deferred_control_plane_family(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-control-plane",
    "slices": [
      {
        "id": "control-plane-registry-ledgers-and-matrices",
        "title": "Control-Plane Registry Ledgers and Matrices",
        "status": "active",
        "publication_artifact_refs": [
          "config/automation-backbone/docs-lifecycle-registry.json",
          "config/automation-backbone/economic-dispatch-ledger.json",
          "config/automation-backbone/lane-selection-matrix.json",
          "config/automation-backbone/executive-kernel-registry.json"
        ],
        "generated_artifacts": [
          "reports/truth-inventory/blocker-execution-plan.json"
        ],
        "working_tree_path_hints": [
          "config/automation-backbone/docs-lifecycle-registry.json",
          "config/automation-backbone/economic-dispatch-ledger.json",
          "config/automation-backbone/lane-selection-matrix.json",
          "config/automation-backbone/executive-kernel-registry.json"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "control-plane-registry-and-routing",
        "title": "Control-Plane Registry and Routing",
        "disposition": "deferred_out_of_sequence",
        "scope": "Registry, routing, and dispatch policy surfaces.",
        "execution_rank": 6,
        "execution_class": "program_slice",
        "next_action": "Split registry and routing policy residue into a bounded follow-on tranche.",
        "success_condition": "Registry/routing residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "config/automation-backbone/docs-lifecycle-registry.json",
          "config/automation-backbone/economic-dispatch-ledger.json",
          "config/automation-backbone/executive-kernel-registry.json",
          "config/automation-backbone/lane-selection-matrix.json",
          "projects/agents/config/subscription-routing-policy.yaml"
        ]
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
            {'status': ' M', 'path': 'config/automation-backbone/docs-lifecycle-registry.json'},
            {'status': ' M', 'path': 'config/automation-backbone/economic-dispatch-ledger.json'},
            {'status': ' M', 'path': 'config/automation-backbone/lane-selection-matrix.json'},
            {'status': '??', 'path': 'config/automation-backbone/executive-kernel-registry.json'},
            {'status': ' M', 'path': 'projects/agents/config/subscription-routing-policy.yaml'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['control-plane-registry-ledgers-and-matrices']['match_count'] == 4
    assert deferred_families['control-plane-registry-and-routing']['match_count'] == 1
    assert deferred_families['control-plane-registry-and-routing']['matched_entries'] == [
        {'status': ' M', 'path': 'projects/agents/config/subscription-routing-policy.yaml'}
    ]


def test_build_triage_bundle_clears_control_plane_family_once_both_subtranche_slices_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-control-plane",
    "slices": [
      {
        "id": "control-plane-registry-ledgers-and-matrices",
        "title": "Control-Plane Registry Ledgers and Matrices",
        "status": "active",
        "publication_artifact_refs": ["config/automation-backbone/economic-dispatch-ledger.json"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "config/automation-backbone/docs-lifecycle-registry.json",
          "config/automation-backbone/economic-dispatch-ledger.json",
          "config/automation-backbone/lane-selection-matrix.json",
          "config/automation-backbone/executive-kernel-registry.json"
        ]
      },
      {
        "id": "control-plane-routing-policy-and-subscription-lane",
        "title": "Control-Plane Routing Policy and Subscription Lane",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/config/subscription-routing-policy.yaml"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/config/subscription-routing-policy.yaml",
          "projects/agents/src/athanor_agents/backbone.py",
          "projects/agents/src/athanor_agents/model_governance.py",
          "projects/agents/src/athanor_agents/subscriptions.py",
          "projects/agents/tests/test_model_governance.py",
          "projects/agents/tests/test_subscription_policy.py"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "control-plane-registry-and-routing",
        "title": "Control-Plane Registry and Routing",
        "disposition": "deferred_out_of_sequence",
        "scope": "Registry, routing, and dispatch policy surfaces.",
        "execution_rank": 6,
        "execution_class": "program_slice",
        "next_action": "Split registry and routing policy residue into a bounded follow-on tranche.",
        "success_condition": "Registry/routing residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "config/automation-backbone/docs-lifecycle-registry.json",
          "config/automation-backbone/economic-dispatch-ledger.json",
          "config/automation-backbone/executive-kernel-registry.json",
          "config/automation-backbone/lane-selection-matrix.json",
          "projects/agents/config/subscription-routing-policy.yaml",
          "projects/agents/src/athanor_agents/backbone.py",
          "projects/agents/src/athanor_agents/model_governance.py",
          "projects/agents/src/athanor_agents/subscriptions.py",
          "projects/agents/tests/test_model_governance.py",
          "projects/agents/tests/test_subscription_policy.py"
        ]
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
            {'status': ' M', 'path': 'config/automation-backbone/docs-lifecycle-registry.json'},
            {'status': ' M', 'path': 'config/automation-backbone/economic-dispatch-ledger.json'},
            {'status': ' M', 'path': 'config/automation-backbone/lane-selection-matrix.json'},
            {'status': '??', 'path': 'config/automation-backbone/executive-kernel-registry.json'},
            {'status': ' M', 'path': 'projects/agents/config/subscription-routing-policy.yaml'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/backbone.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/model_governance.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/subscriptions.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_model_governance.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_subscription_policy.py'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['control-plane-registry-ledgers-and-matrices']['match_count'] == 4
    assert slices['control-plane-routing-policy-and-subscription-lane']['match_count'] == 6
    assert deferred_families['control-plane-registry-and-routing']['match_count'] == 0


def test_build_triage_bundle_clears_execution_kernel_family_once_all_subtranche_slices_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-execution-kernel",
    "slices": [
      {
        "id": "agent-execution-kernel-scheduler-and-research-loop",
        "title": "Agent Execution Kernel Scheduler and Research Loop",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/src/athanor_agents/scheduler.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/src/athanor_agents/research_jobs.py",
          "projects/agents/src/athanor_agents/scheduler.py",
          "projects/agents/src/athanor_agents/work_pipeline.py",
          "projects/agents/tests/test_research_jobs.py",
          "projects/agents/tests/test_scheduler.py",
          "projects/agents/tests/test_work_pipeline.py"
        ]
      },
      {
        "id": "agent-execution-kernel-self-improvement-and-proving",
        "title": "Agent Execution Kernel Self-Improvement and Proving",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/src/athanor_agents/self_improvement.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/src/athanor_agents/proving_ground.py",
          "projects/agents/src/athanor_agents/self_improvement.py",
          "projects/agents/tests/test_self_improvement.py"
        ]
      },
      {
        "id": "agent-execution-kernel-support-and-tests",
        "title": "Agent Execution Kernel Support and Tests",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/src/athanor_agents/autonomous_queue.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/src/athanor_agents/autonomous_queue.py",
          "projects/agents/src/athanor_agents/capability_intelligence.py",
          "projects/agents/src/athanor_agents/repo_paths.py",
          "projects/agents/tests/test_repo_paths.py"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "agent-execution-kernel-follow-on",
        "title": "Agent Execution Kernel Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Execution-kernel, queue, scheduler, and proving surfaces.",
        "execution_rank": 7,
        "execution_class": "program_slice",
        "next_action": "Split execution-kernel residue into bounded follow-on tranches.",
        "success_condition": "Execution-kernel residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "projects/agents/src/athanor_agents/proving_ground.py",
          "projects/agents/src/athanor_agents/research_jobs.py",
          "projects/agents/src/athanor_agents/scheduler.py",
          "projects/agents/src/athanor_agents/self_improvement.py",
          "projects/agents/src/athanor_agents/work_pipeline.py",
          "projects/agents/src/athanor_agents/autonomous_queue.py",
          "projects/agents/src/athanor_agents/capability_intelligence.py",
          "projects/agents/src/athanor_agents/repo_paths.py",
          "projects/agents/tests/test_research_jobs.py",
          "projects/agents/tests/test_scheduler.py",
          "projects/agents/tests/test_self_improvement.py",
          "projects/agents/tests/test_work_pipeline.py",
          "projects/agents/tests/test_repo_paths.py"
        ]
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
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/proving_ground.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/research_jobs.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/scheduler.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/self_improvement.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/work_pipeline.py'},
            {'status': '??', 'path': 'projects/agents/src/athanor_agents/autonomous_queue.py'},
            {'status': '??', 'path': 'projects/agents/src/athanor_agents/capability_intelligence.py'},
            {'status': '??', 'path': 'projects/agents/src/athanor_agents/repo_paths.py'},
            {'status': '??', 'path': 'projects/agents/tests/test_research_jobs.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_scheduler.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_self_improvement.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_work_pipeline.py'},
            {'status': '??', 'path': 'projects/agents/tests/test_repo_paths.py'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['agent-execution-kernel-scheduler-and-research-loop']['match_count'] == 6
    assert slices['agent-execution-kernel-self-improvement-and-proving']['match_count'] == 3
    assert slices['agent-execution-kernel-support-and-tests']['match_count'] == 4
    assert deferred_families['agent-execution-kernel-follow-on']['match_count'] == 0


def test_build_triage_bundle_clears_route_contract_family_once_surface_and_test_slices_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-route-contracts",
    "slices": [
      {
        "id": "agent-route-contract-surface-code",
        "title": "Agent Route Contract Surface Code",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/src/athanor_agents/routes/operator_work.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/src/athanor_agents/routes/bootstrap.py",
          "projects/agents/src/athanor_agents/routes/model_governance.py",
          "projects/agents/src/athanor_agents/routes/operator_work.py",
          "projects/agents/src/athanor_agents/routes/plans.py",
          "projects/agents/src/athanor_agents/routes/projects.py",
          "projects/agents/src/athanor_agents/routes/research.py",
          "projects/agents/src/athanor_agents/routes/tasks.py"
        ]
      },
      {
        "id": "agent-route-contract-tests",
        "title": "Agent Route Contract Tests",
        "status": "active",
        "publication_artifact_refs": ["projects/agents/tests/test_operator_work_route_contract.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/tests/test_bootstrap_route_contract.py",
          "projects/agents/tests/test_foundry_route_contract.py",
          "projects/agents/tests/test_model_governance_route_contract.py",
          "projects/agents/tests/test_operator_work_route_contract.py",
          "projects/agents/tests/test_task_route_contract.py",
          "scripts/tests/test_cli_router_contracts.py"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "agent-route-contract-follow-on",
        "title": "Agent Route Contract Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Route surfaces and contract tests.",
        "execution_rank": 8,
        "execution_class": "program_slice",
        "next_action": "Split route surfaces and route-contract verification into bounded tranches.",
        "success_condition": "Route residue is isolated and publication-ready.",
        "owner_workstreams": ["authority-and-mainline"],
        "path_hints": [
          "projects/agents/src/athanor_agents/routes/bootstrap.py",
          "projects/agents/src/athanor_agents/routes/model_governance.py",
          "projects/agents/src/athanor_agents/routes/operator_work.py",
          "projects/agents/src/athanor_agents/routes/plans.py",
          "projects/agents/src/athanor_agents/routes/projects.py",
          "projects/agents/src/athanor_agents/routes/research.py",
          "projects/agents/src/athanor_agents/routes/tasks.py",
          "projects/agents/tests/test_bootstrap_route_contract.py",
          "projects/agents/tests/test_foundry_route_contract.py",
          "projects/agents/tests/test_model_governance_route_contract.py",
          "projects/agents/tests/test_operator_work_route_contract.py",
          "projects/agents/tests/test_task_route_contract.py",
          "scripts/tests/test_cli_router_contracts.py"
        ]
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
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/bootstrap.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/model_governance.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/operator_work.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/plans.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/projects.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/research.py'},
            {'status': ' M', 'path': 'projects/agents/src/athanor_agents/routes/tasks.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_bootstrap_route_contract.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_foundry_route_contract.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_model_governance_route_contract.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_operator_work_route_contract.py'},
            {'status': ' M', 'path': 'projects/agents/tests/test_task_route_contract.py'},
            {'status': ' M', 'path': 'scripts/tests/test_cli_router_contracts.py'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['agent-route-contract-surface-code']['match_count'] == 7
    assert slices['agent-route-contract-tests']['match_count'] == 6
    assert deferred_families['agent-route-contract-follow-on']['match_count'] == 0


def test_build_triage_bundle_clears_proof_ops_family_once_all_subtranche_slices_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module(
        f"publication_tranche_triage_{uuid.uuid4().hex}",
        SCRIPTS_DIR / 'triage_publication_tranche.py',
    )

    registry_path = tmp_path / 'completion-program-registry.json'
    registry_path.write_text(
        """{
  "publication_slices": {
    "active_sequence_id": "sequence-proof-ops",
    "slices": [
      {
        "id": "control-plane-ralph-and-truth-writers",
        "title": "Control-Plane Ralph and Truth Writers",
        "status": "active",
        "publication_artifact_refs": ["scripts/run_ralph_loop_pass.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "scripts/run_ralph_loop_pass.py",
          "scripts/tests/test_ralph_loop_contracts.py",
          "scripts/tests/test_truth_inventory_path_overrides.py",
          "scripts/tests/test_write_steady_state_status.py",
          "scripts/truth_inventory.py",
          "scripts/write_steady_state_status.py"
        ]
      },
      {
        "id": "control-plane-proof-generators-and-validators",
        "title": "Control-Plane Proof Generators and Validators",
        "status": "active",
        "publication_artifact_refs": ["scripts/generate_capability_intelligence.py"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "scripts/generate_capability_intelligence.py",
          "scripts/probe_openhands_bounded_worker.py",
          "scripts/proof_workspace_contract.py",
          "scripts/sync_github_portfolio_registry.py",
          "scripts/tests/test_capability_intelligence_contracts.py",
          "scripts/tests/test_proof_workspace_contract.py",
          "scripts/tests/test_sync_github_portfolio_registry.py",
          "scripts/tests/test_validate_platform_contract_monitoring_contracts.py",
          "scripts/tests/test_write_current_tree_partition.py",
          "scripts/tests/test_write_value_throughput_scorecard.py",
          "scripts/write_current_tree_partition.py",
          "scripts/write_value_throughput_scorecard.py"
        ]
      },
      {
        "id": "control-plane-deploy-and-runtime-ops-helpers",
        "title": "Control-Plane Deploy and Runtime Ops Helpers",
        "status": "active",
        "publication_artifact_refs": ["scripts/deploy-agents.sh"],
        "generated_artifacts": ["reports/truth-inventory/blocker-execution-plan.json"],
        "working_tree_path_hints": [
          "projects/agents/docker-compose.yml",
          "scripts/.cluster_config.unix.sh",
          "scripts/.deploy-agents.unix.sh",
          "scripts/deploy-agents.sh"
        ]
      }
    ],
    "deferred_families": [
      {
        "id": "control-plane-proof-and-ops-follow-on",
        "title": "Control-Plane Proof and Ops Follow-on",
        "disposition": "deferred_out_of_sequence",
        "scope": "Truth writers, proof generators, validators, and deploy/runtime helpers.",
        "execution_rank": 9,
        "execution_class": "program_slice",
        "next_action": "Split proof-generation and ops residue into bounded tranches.",
        "success_condition": "Proof and ops residue is isolated and publication-ready.",
        "owner_workstreams": ["validation-and-publication"],
        "path_hints": [
          "projects/agents/docker-compose.yml",
          "scripts/deploy-agents.sh",
          "scripts/run_ralph_loop_pass.py",
          "scripts/sync_github_portfolio_registry.py",
          "scripts/tests/test_ralph_loop_contracts.py",
          "scripts/tests/test_validate_platform_contract_monitoring_contracts.py",
          "scripts/tests/test_write_steady_state_status.py",
          "scripts/truth_inventory.py",
          "scripts/write_steady_state_status.py",
          "scripts/.cluster_config.unix.sh",
          "scripts/.deploy-agents.unix.sh",
          "scripts/generate_capability_intelligence.py",
          "scripts/probe_openhands_bounded_worker.py",
          "scripts/proof_workspace_contract.py",
          "scripts/tests/test_capability_intelligence_contracts.py",
          "scripts/tests/test_proof_workspace_contract.py",
          "scripts/tests/test_sync_github_portfolio_registry.py",
          "scripts/tests/test_truth_inventory_path_overrides.py",
          "scripts/tests/test_write_current_tree_partition.py",
          "scripts/tests/test_write_value_throughput_scorecard.py",
          "scripts/write_current_tree_partition.py",
          "scripts/write_value_throughput_scorecard.py"
        ]
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
            {'status': ' M', 'path': 'projects/agents/docker-compose.yml'},
            {'status': ' M', 'path': 'scripts/deploy-agents.sh'},
            {'status': ' M', 'path': 'scripts/run_ralph_loop_pass.py'},
            {'status': ' M', 'path': 'scripts/sync_github_portfolio_registry.py'},
            {'status': ' M', 'path': 'scripts/tests/test_ralph_loop_contracts.py'},
            {'status': ' M', 'path': 'scripts/tests/test_validate_platform_contract_monitoring_contracts.py'},
            {'status': ' M', 'path': 'scripts/tests/test_write_steady_state_status.py'},
            {'status': ' M', 'path': 'scripts/truth_inventory.py'},
            {'status': ' M', 'path': 'scripts/write_steady_state_status.py'},
            {'status': '??', 'path': 'scripts/.cluster_config.unix.sh'},
            {'status': '??', 'path': 'scripts/.deploy-agents.unix.sh'},
            {'status': '??', 'path': 'scripts/generate_capability_intelligence.py'},
            {'status': '??', 'path': 'scripts/probe_openhands_bounded_worker.py'},
            {'status': '??', 'path': 'scripts/proof_workspace_contract.py'},
            {'status': '??', 'path': 'scripts/tests/test_capability_intelligence_contracts.py'},
            {'status': '??', 'path': 'scripts/tests/test_proof_workspace_contract.py'},
            {'status': '??', 'path': 'scripts/tests/test_sync_github_portfolio_registry.py'},
            {'status': '??', 'path': 'scripts/tests/test_truth_inventory_path_overrides.py'},
            {'status': '??', 'path': 'scripts/tests/test_write_current_tree_partition.py'},
            {'status': '??', 'path': 'scripts/tests/test_write_value_throughput_scorecard.py'},
            {'status': '??', 'path': 'scripts/write_current_tree_partition.py'},
            {'status': '??', 'path': 'scripts/write_value_throughput_scorecard.py'},
        ],
    )

    bundle = module.build_triage_bundle(repo_root=repo_root, registry_path=registry_path)
    slices = {entry['id']: entry for entry in bundle['slices']}
    deferred_families = {entry['id']: entry for entry in bundle['deferred_families']}

    assert slices['control-plane-ralph-and-truth-writers']['match_count'] == 6
    assert slices['control-plane-proof-generators-and-validators']['match_count'] == 12
    assert slices['control-plane-deploy-and-runtime-ops-helpers']['match_count'] == 4
    assert deferred_families['control-plane-proof-and-ops-follow-on']['match_count'] == 0


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
        return _Result(returncode=0, stdout=' M scripts/example.py\n')

    original_run = module.subprocess.run
    module.subprocess.run = _fake_run
    try:
        entries = module._git_status_entries(repo_root)
    finally:
        module.subprocess.run = original_run

    assert len(commands) == 1
    assert commands[0][0] == 'git'
    assert entries == [{'status': ' M', 'path': 'scripts/example.py'}]
