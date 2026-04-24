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


def test_build_payload_tracks_only_real_project_outputs_and_maps_legacy_aliases() -> None:
    module = _load_module(
        f"write_project_output_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_proof.py",
    )

    contract_registry = {
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "authority_class": "athanor_in_repo_project",
                "legacy_project_ids": [],
            },
            {
                "project_id": "ulrich-website",
                "label": "Ulrich Energy Auditing Website",
                "authority_class": "external_repo_current_authority",
                "legacy_project_ids": ["ulrich-energy"],
            },
            {
                "project_id": "lawnsignal",
                "label": "LawnSignal",
                "authority_class": "external_repo_current_authority",
                "legacy_project_ids": [],
            },
        ]
    }
    autonomous_value_proof = {
        "accepted_entries": [
            {
                "packet_id": "result-eoq-1",
                "project_id": "eoq",
                "title": "EOQ scene pack alpha",
                "value_class": "product_value",
                "deliverable_kind": "content_artifact",
                "deliverable_refs": ["projects/eoq/NEW/scene-pack-alpha/manifest.json"],
                "beneficiary_surface": "eoq",
                "verification_outcome": "passed",
                "acceptance_outcome": "accepted",
                "acceptance_mode": "hybrid",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T20:10:00+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/project-output-acceptance/eoq-scene-pack-alpha.json"],
                "fully_autonomous": True,
                "operator_steered": False,
            },
            {
                "packet_id": "result-dashboard-1",
                "project_id": "dashboard",
                "title": "Dashboard value card",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["projects/dashboard/src/features/operator/operator-console.tsx"],
                "beneficiary_surface": "dashboard",
                "verification_outcome": "passed",
                "acceptance_outcome": "accepted",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T20:11:00+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-proof.json"],
                "fully_autonomous": True,
                "operator_steered": False,
            },
            {
                "packet_id": "result-ulrich-1",
                "project_id": "ulrich-energy",
                "title": "Ulrich lead form tranche",
                "value_class": "product_value",
                "deliverable_kind": "ui_change",
                "deliverable_refs": ["src/app/contact/page.tsx"],
                "beneficiary_surface": "ulrich_site",
                "verification_outcome": "passed",
                "acceptance_outcome": "accepted",
                "acceptance_mode": "hybrid",
                "accepted_by": "Shaun",
                "accepted_at": "2026-04-20T20:12:00+00:00",
                "acceptance_proof_refs": ["reports/truth-inventory/project-output-acceptance/ulrich-lead-form.json"],
                "fully_autonomous": True,
                "operator_steered": False,
            },
        ],
        "disqualified_entries": [
            {
                "packet_id": "result-lawn-2",
                "project_id": "lawnsignal",
                "title": "LawnSignal mobile proof",
                "disqualification_reason": "deliverable_present_but_not_accepted",
                "deliverable_refs": ["apps/mobile/app/index.tsx"],
                "beneficiary_surface": "lawnsignal_mobile",
            }
        ],
    }

    payload = module.build_payload(
        contract_registry=contract_registry,
        autonomous_value_proof=autonomous_value_proof,
    )

    assert payload["accepted_project_output_count"] == 2
    assert payload["distinct_project_count"] == 2
    assert payload["accepted_external_project_output_count"] == 1
    assert payload["accepted_user_facing_output_count"] == 2
    assert payload["stage_status"]["met"] is False
    assert payload["stage_status"]["remaining_project_outputs"] == 1
    assert payload["latest_accepted_entry"]["project_id"] == "ulrich-website"
    assert payload["accepted_entries"][1]["project_id"] == "ulrich-website"
    assert payload["disqualified_entries"][0]["project_id"] == "lawnsignal"
    assert payload["project_summaries"]["dashboard"]["counted"] is False
    assert payload["project_summaries"]["ulrich-website"]["counted"] is True


def test_render_against_existing_preserves_generated_at_for_staleness_checks() -> None:
    module = _load_module(
        f"write_project_output_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_proof.py",
    )

    contract_registry = {
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "authority_class": "athanor_in_repo_project",
                "legacy_project_ids": [],
            }
        ]
    }
    autonomous_value_proof = {"accepted_entries": [], "disqualified_entries": []}

    times = iter(
        [
            "2026-04-20T20:10:00+00:00",
            "2026-04-20T20:11:00+00:00",
        ]
    )
    module._iso_now = lambda: next(times)
    first_payload = module.build_payload(
        contract_registry=contract_registry,
        autonomous_value_proof=autonomous_value_proof,
    )
    first_json = module._json_render(first_payload)
    first_md = module._markdown(first_payload)

    second_payload = module.build_payload(
        contract_registry=contract_registry,
        autonomous_value_proof=autonomous_value_proof,
    )
    comparable_json, comparable_md = module._render_against_existing(second_payload, first_json)

    assert comparable_json == first_json
    assert comparable_md == first_md


def test_build_payload_surfaces_pending_candidates_without_counting_them() -> None:
    module = _load_module(
        f"write_project_output_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_proof.py",
    )

    contract_registry = {
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "authority_class": "athanor_in_repo_project",
                "legacy_project_ids": [],
            }
        ]
    }
    autonomous_value_proof = {"accepted_entries": [], "disqualified_entries": []}
    project_output_candidates = {
        "candidate_count": 1,
        "pending_candidate_count": 1,
        "pending_hybrid_acceptance_count": 1,
        "latest_pending_candidate": {
            "candidate_id": "eoq-courtyard-alpha",
            "project_id": "eoq",
            "deliverable_kind": "content_artifact",
        },
    }

    payload = module.build_payload(
        contract_registry=contract_registry,
        autonomous_value_proof=autonomous_value_proof,
        project_output_candidates=project_output_candidates,
    )

    assert payload["accepted_project_output_count"] == 0
    assert payload["pending_candidate_count"] == 1
    assert payload["pending_hybrid_acceptance_count"] == 1
    assert payload["latest_pending_candidate"]["project_id"] == "eoq"
