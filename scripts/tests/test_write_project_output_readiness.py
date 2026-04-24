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


def test_build_payload_materializes_project_factory_readiness_and_safe_surface_gates() -> None:
    module = _load_module(
        f"write_project_output_readiness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_readiness.py",
    )

    contract_registry = {
        "strategy": {
            "creative_first": True,
            "expansion_mode": "project_by_project",
        },
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "canonical_root": r"C:\Athanor\projects\eoq",
                "project_class": "sovereign_creative_runtime_product",
                "platform_class": "creative_runtime",
                "authority_class": "athanor_in_repo_project",
                "routing_class": "sovereign_only",
                "first_output_target": "Scene pack",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Accepted scene pack"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert bundle",
                "autonomy_scope_state": "governed_in_repo_project",
                "factory_priority": 10,
                "next_tranche": "Install the missing EOQ Next toolchain and produce the first scene pack.",
                "observed_baseline": {
                    "build_state": "failed",
                    "detail": "next: not found",
                },
            },
            {
                "project_id": "lawnsignal",
                "label": "LawnSignal",
                "canonical_root": r"C:\LawnSignal",
                "project_class": "web_plus_mobile_consumer_product",
                "platform_class": "web_plus_mobile",
                "authority_class": "external_repo_current_authority",
                "routing_class": "private_but_cloud_allowed",
                "first_output_target": "Nationwide web tranche",
                "verification_bundle": ["npm run build", "npm run test"],
                "acceptance_bundle": ["Shipped tranche"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert tranche",
                "autonomy_scope_state": "contract_defined_pending_admission",
                "factory_priority": 20,
                "next_tranche": "Admit LawnSignal into the governed project-output loop.",
                "observed_baseline": {
                    "build_state": "passed",
                    "detail": "npm run build passes and Expo shell exists.",
                },
            },
            {
                "project_id": "field-inspect",
                "label": "Field Inspect",
                "canonical_root": r"C:\Field Inspect",
                "project_class": "saas_plus_mobile_business_product",
                "platform_class": "web_plus_mobile",
                "authority_class": "external_repo_current_authority",
                "routing_class": "private_but_cloud_allowed",
                "first_output_target": "Owner-facing workflow tranche",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Shipped workflow tranche"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert workflow tranche",
                "autonomy_scope_state": "explicit_admission_required",
                "factory_priority": 30,
                "next_tranche": "Create an explicit project-output contract entry before autonomous work.",
                "observed_baseline": {
                    "build_state": "failed",
                    "detail": "prisma CLI missing",
                },
            },
            {
                "project_id": "todo-almanac",
                "label": "To-do / Personal Almanac",
                "canonical_root": "needs_root",
                "project_class": "unformed_product_slot",
                "platform_class": "unknown",
                "authority_class": "needs_root",
                "routing_class": "private_but_cloud_allowed",
                "first_output_target": "Create canonical root",
                "verification_bundle": [],
                "acceptance_bundle": ["Canonical repo created"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Archive unneeded scaffold",
                "autonomy_scope_state": "needs_root",
                "factory_priority": 90,
                "next_tranche": "Create the canonical repository and first scaffold.",
            },
        ],
    }

    packet_registry = {
        "projects": [
            {"id": "eoq"},
            {"id": "ulrich-energy"},
        ]
    }
    maturity_registry = {
        "projects": [
            {"id": "eoq", "class": "active-scaffold"},
        ]
    }
    safe_surface_scope = {
        "allowed_roots": [r"C:\Ulrich Energy Auditing Website"],
        "deny_patterns": ["athanor", "Field Inspect"],
    }

    def _probe(project: dict[str, object]) -> dict[str, object]:
        by_id = {
            "eoq": {
                "root_exists": True,
                "git_head": "abc1234",
                "dirty_count": 0,
                "package_json_present": True,
                "node_modules_present": False,
                "mobile_shell_present": False,
                "android_contract_present": False,
                "app_root": "/mnt/c/Athanor/projects/eoq",
            },
            "lawnsignal": {
                "root_exists": True,
                "git_head": "46f9331",
                "dirty_count": 0,
                "package_json_present": True,
                "node_modules_present": True,
                "mobile_shell_present": True,
                "android_contract_present": True,
                "app_root": "/mnt/c/LawnSignal",
            },
            "field-inspect": {
                "root_exists": True,
                "git_head": "deadbee",
                "dirty_count": 0,
                "package_json_present": True,
                "node_modules_present": True,
                "mobile_shell_present": True,
                "android_contract_present": True,
                "app_root": "/mnt/c/Field Inspect",
            },
            "todo-almanac": {
                "root_exists": False,
                "git_head": "",
                "dirty_count": 0,
                "package_json_present": False,
                "node_modules_present": False,
                "mobile_shell_present": False,
                "android_contract_present": False,
                "app_root": None,
            },
        }
        return by_id[str(project["project_id"])]

    payload = module.build_payload(
        contract_registry=contract_registry,
        project_packet_registry=packet_registry,
        project_maturity_registry=maturity_registry,
        safe_surface_scope=safe_surface_scope,
        blocker_map={"proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day"]}},
        runtime_parity={"drift_class": "clean"},
        stable_operating_day={"met": False, "covered_window_hours": 14.5, "required_window_hours": 24},
        supervisor_health={"health_status": "healthy"},
        project_probe=_probe,
    )

    assert payload["factory_operating_mode"] == "core_runtime_hold"
    assert payload["top_priority_project_id"] == "eoq"
    assert payload["summary"]["broad_project_factory_ready"] is False
    assert payload["summary"]["single_live_blocker"] == "stable_operating_day"

    records = {item["project_id"]: item for item in payload["projects"]}

    assert records["eoq"]["readiness_tier"] == "toolchain_blocked"
    assert records["eoq"]["autonomy_eligibility"] == "held_by_core_runtime_gate"
    assert records["eoq"]["athanor_project_registry_state"] == "governed"

    assert records["lawnsignal"]["readiness_tier"] == "admission_pending"
    assert records["lawnsignal"]["safe_surface_status"] == "not_allowlisted"
    assert "not_admitted_into_project_factory" in records["lawnsignal"]["blockers"]

    assert records["field-inspect"]["autonomy_eligibility"] == "denied_by_safe_surface"
    assert records["field-inspect"]["safe_surface_status"] == "denied_by_policy"
    assert "safe_surface_denied" in records["field-inspect"]["blockers"]

    assert records["todo-almanac"]["readiness_tier"] == "needs_root"
    assert records["todo-almanac"]["autonomy_eligibility"] == "needs_root"


def test_render_against_existing_preserves_generated_at_for_staleness_checks() -> None:
    module = _load_module(
        f"write_project_output_readiness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_readiness.py",
    )

    contract_registry = {
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "canonical_root": r"C:\Athanor\projects\eoq",
                "project_class": "sovereign_creative_runtime_product",
                "platform_class": "creative_runtime",
                "authority_class": "athanor_in_repo_project",
                "routing_class": "sovereign_only",
                "first_output_target": "Scene pack",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Accepted scene pack"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert bundle",
                "autonomy_scope_state": "governed_in_repo_project",
                "factory_priority": 10,
                "next_tranche": "Install the missing EOQ Next toolchain and produce the first scene pack.",
                "observed_baseline": {
                    "build_state": "failed",
                    "detail": "next: not found",
                },
            }
        ]
    }

    def _probe(_project: dict[str, object]) -> dict[str, object]:
        return {
            "root_exists": True,
            "git_head": "abc1234",
            "dirty_count": 0,
            "package_json_present": True,
            "node_modules_present": False,
            "mobile_shell_present": False,
            "android_contract_present": False,
            "app_root": "/mnt/c/Athanor/projects/eoq",
        }

    times = iter(
        [
            "2026-04-20T20:20:00+00:00",
            "2026-04-20T20:21:00+00:00",
        ]
    )
    module._iso_now = lambda: next(times)
    first_payload = module.build_payload(
        contract_registry=contract_registry,
        project_packet_registry={},
        project_maturity_registry={},
        safe_surface_scope={},
        blocker_map={"proof_gate": {"open": True, "blocking_check_ids": []}},
        runtime_parity={"drift_class": "clean"},
        stable_operating_day={"met": True, "covered_window_hours": 24, "required_window_hours": 24},
        supervisor_health={"health_status": "healthy"},
        project_probe=_probe,
    )
    first_json = module._json_render(first_payload)
    first_md = module._markdown(first_payload)

    second_payload = module.build_payload(
        contract_registry=contract_registry,
        project_packet_registry={},
        project_maturity_registry={},
        safe_surface_scope={},
        blocker_map={"proof_gate": {"open": True, "blocking_check_ids": []}},
        runtime_parity={"drift_class": "clean"},
        stable_operating_day={"met": True, "covered_window_hours": 24, "required_window_hours": 24},
        supervisor_health={"health_status": "healthy"},
        project_probe=_probe,
    )
    comparable_json, comparable_md = module._render_against_existing(second_payload, first_json)

    assert comparable_json == first_json
    assert comparable_md == first_md


def test_git_probe_scopes_status_to_project_subtree(tmp_path: Path) -> None:
    module = _load_module(
        f"write_project_output_readiness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_readiness.py",
    )

    project_root = tmp_path / "projects" / "eoq"
    project_root.mkdir(parents=True)
    calls: list[list[str]] = []

    class _Completed:
        def __init__(self, *, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(command: list[str], **_kwargs: object) -> _Completed:
        calls.append(command)
        if "rev-parse" in command:
            return _Completed(returncode=0, stdout="abc1234\n")
        return _Completed(returncode=0, stdout="")

    module.subprocess.run = _fake_run

    probe = module._git_probe(project_root)

    assert probe["git_head"] == "abc1234"
    assert probe["dirty_count"] == 0
    assert calls[1] == [
        "git",
        "-C",
        str(project_root),
        "status",
        "--short",
        "--",
        ".",
    ]


def test_build_payload_reranks_to_external_gap_project_after_first_accepted_output() -> None:
    module = _load_module(
        f"write_project_output_readiness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_project_output_readiness.py",
    )

    contract_registry = {
        "projects": [
            {
                "project_id": "eoq",
                "label": "Empire of Broken Queens",
                "canonical_root": r"C:\Athanor\projects\eoq",
                "project_class": "sovereign_creative_runtime_product",
                "platform_class": "creative_runtime",
                "authority_class": "athanor_in_repo_project",
                "routing_class": "sovereign_only",
                "first_output_target": "Scene pack",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Accepted scene pack"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert bundle",
                "autonomy_scope_state": "governed_in_repo_project",
                "factory_priority": 10,
                "next_tranche": "Produce the first accepted EOQ scene pack.",
                "observed_baseline": {"build_state": "passed"},
            },
            {
                "project_id": "lawnsignal",
                "label": "LawnSignal",
                "canonical_root": r"C:\LawnSignal",
                "project_class": "web_plus_mobile_consumer_product",
                "platform_class": "web_plus_mobile",
                "authority_class": "external_repo_current_authority",
                "routing_class": "private_but_cloud_allowed",
                "first_output_target": "Nationwide web tranche",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Shipped tranche"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert tranche",
                "autonomy_scope_state": "contract_defined_pending_admission",
                "factory_priority": 20,
                "next_tranche": "Admit LawnSignal.",
                "observed_baseline": {"build_state": "passed"},
            },
            {
                "project_id": "ulrich-website",
                "label": "Ulrich Energy Auditing Website",
                "canonical_root": r"C:\Users\Shaun\Ulrich Energy Auditing Website",
                "project_class": "business_website_external_delivery",
                "platform_class": "web",
                "authority_class": "external_repo_current_authority",
                "routing_class": "private_but_cloud_allowed",
                "safe_surface_expectation": "allowlisted",
                "first_output_target": "Site release",
                "verification_bundle": ["npm run build"],
                "acceptance_bundle": ["Shipped release"],
                "approval_posture": "hybrid",
                "rollback_or_archive_rule": "Revert release",
                "autonomy_scope_state": "allowlisted_external_delivery",
                "factory_priority": 30,
                "next_tranche": "Ship one real business-facing release.",
                "observed_baseline": {"build_state": "passed"},
            },
        ]
    }

    def _probe(project: dict[str, object]) -> dict[str, object]:
        return {
            "root_exists": True,
            "git_head": "abc1234",
            "dirty_count": 0,
            "package_json_present": True,
            "node_modules_present": True,
            "mobile_shell_present": False,
            "android_contract_present": False,
            "app_root": f"/tmp/{project['project_id']}",
        }

    payload = module.build_payload(
        contract_registry=contract_registry,
        project_packet_registry={},
        project_maturity_registry={},
        safe_surface_scope={"allowed_roots": [r"C:\Users\Shaun\Ulrich Energy Auditing Website"]},
        blocker_map={"proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day"]}},
        runtime_parity={"drift_class": "clean"},
        stable_operating_day={"met": False, "covered_window_hours": 12, "required_window_hours": 24},
        supervisor_health={"health_status": "healthy"},
        project_output_proof={
            "accepted_entries": [{"project_id": "eoq"}],
            "stage_status": {
                "remaining_distinct_projects": 2,
                "remaining_external_project_outputs": 1,
            },
        },
        project_probe=_probe,
    )

    assert payload["top_priority_project_id"] == "ulrich-website"
    assert payload["summary"]["top_priority_selection_reason"] == "proof_gap_priority"
