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


def test_report_check_ignores_runtime_snapshot_timestamp_only_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n"
    rendered = "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n"

    assert module._report_is_stale("runtime_cutover", existing=existing, rendered=rendered) is False


def test_report_check_ignores_vault_audit_timestamp_only_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing_vault_packet = (
        "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n"
        "- Cached env audit: `2026-03-29T05:31:46Z`\n"
    )
    rendered_vault_packet = (
        "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n"
        "- Cached env audit: `2026-03-29T06:58:00Z`\n"
    )
    existing_secret_surface = (
        "- VAULT LiteLLM env audit: `2026-03-29T05:31:46Z`\n"
        "- Latest live env audit: `2026-03-29T05:31:46Z`\n"
    )
    rendered_secret_surface = (
        "- VAULT LiteLLM env audit: `2026-03-29T06:58:00Z`\n"
        "- Latest live env audit: `2026-03-29T06:58:00Z`\n"
    )

    assert (
        module._report_is_stale(
            "vault_litellm_repair_packet",
            existing=existing_vault_packet,
            rendered=rendered_vault_packet,
        )
        is False
    )
    assert (
        module._report_is_stale(
            "secret_surfaces",
            existing=existing_secret_surface,
            rendered=rendered_secret_surface,
        )
        is False
    )


def test_report_check_still_flags_real_content_drift() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    existing = "- Cached truth snapshot: `2026-03-29T05:31:46.726811+00:00`\n- Status: `retired`\n"
    rendered = "- Cached truth snapshot: `2026-03-29T06:58:00.000000+00:00`\n- Status: `active`\n"

    assert module._report_is_stale("runtime_cutover", existing=existing, rendered=rendered) is True


def test_autonomy_activation_report_includes_next_phase_boundary() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    registry = {
        "version": "test",
        "status": "live_partial",
        "activation_state": "software_core_active",
        "current_phase_id": "phase_1",
        "broad_autonomy_enabled": False,
        "runtime_mutations_approval_gated": True,
        "prerequisites": [
            {
                "id": "already_done",
                "status": "verified",
                "phase_scope": "phase_1",
                "evidence_paths": ["docs/ok.md"],
            },
            {
                "id": "vault_provider_auth_repair",
                "status": "pending",
                "phase_scope": "phase_2",
                "evidence_paths": ["docs/vault.md"],
            },
        ],
        "approval_gates": [],
        "phases": [
            {
                "id": "phase_1",
                "label": "Phase One",
                "status": "active",
                "scope": "bounded",
                "enabled_agents": ["coding-agent"],
                "allowed_workload_classes": ["repo_audit"],
                "blocked_workload_classes": [],
                "allowed_loop_families": ["audit"],
                "blocked_without_approval": ["runtime mutations"],
                "entry_criteria": ["ready"],
                "success_criteria": ["green"],
            },
            {
                "id": "phase_2",
                "label": "Phase Two",
                "status": "blocked",
                "scope": "bounded_plus_domain_sidecars",
                "enabled_agents": ["coding-agent", "data-curator"],
                "allowed_workload_classes": ["repo_audit", "background_transform"],
                "blocked_workload_classes": [],
                "allowed_loop_families": ["audit", "background transforms"],
                "blocked_without_approval": ["runtime mutations"],
                "entry_criteria": ["vault fixed"],
                "success_criteria": ["broader loops live"],
            },
        ],
    }
    module.load_registry = lambda name: registry

    rendered = module.render_autonomy_activation_report()

    assert "- Next phase: `phase_2`" in rendered
    assert "- Next phase blocker count: `1`" in rendered
    assert "## Next Promotion Boundary" in rendered
    assert "| `vault_provider_auth_repair` | `pending` | `phase_2` | `docs/vault.md` |" in rendered
def test_classify_vault_auth_failure_missing_env() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "anthropic_api",
        "env_contracts": ["ANTHROPIC_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "ANTHROPIC_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "claude"}},
    }
    capture = {
        "requested_model": "claude",
        "error_snippet": "Missing Anthropic API Key - no key is set either in the environment variables or via params.",
    }
    audit = {
        "container_missing_env_names": ["ANTHROPIC_API_KEY"],
        "container_present_env_names": [],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "missing_required_env"
    assert "Restore `ANTHROPIC_API_KEY`" in classification["next_action"]


def test_classify_vault_auth_failure_present_invalid_key() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "openai_api",
        "env_contracts": ["OPENAI_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "OPENAI_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "gpt"}},
    }
    capture = {
        "requested_model": "gpt",
        "error_snippet": "AuthenticationError: OpenAIException - Incorrect API key provided.",
    }
    audit = {
        "container_missing_env_names": [],
        "container_present_env_names": ["OPENAI_API_KEY"],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "present_key_invalid"
    assert "Rotate `OPENAI_API_KEY`" in classification["next_action"]


def test_classify_vault_auth_failure_auth_mode_mismatch() -> None:
    module = _load_module(
        f"truth_inventory_report_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "generate_truth_inventory_reports.py",
    )
    provider = {
        "id": "openrouter_api",
        "env_contracts": ["OPENROUTER_API_KEY"],
        "vault_runtime_contract": {"env_rules": [{"name": "OPENROUTER_API_KEY", "role": "required"}]},
        "evidence": {"proxy": {"alias": "openrouter"}},
    }
    capture = {
        "requested_model": "openrouter",
        "error_snippet": 'AuthenticationError: OpenrouterException - {"error":{"message":"No cookie auth credentials found","code":401}}',
    }
    audit = {
        "container_missing_env_names": ["OPENROUTER_API_KEY"],
        "container_present_env_names": [],
    }

    classification = module._classify_vault_auth_failure(provider, capture, audit)

    assert classification["code"] == "auth_mode_mismatch"
    assert "Verify the upstream auth mode" in classification["next_action"]
