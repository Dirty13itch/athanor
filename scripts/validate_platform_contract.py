from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
PROVIDER_USAGE_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"
VAULT_LITELLM_ENV_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-litellm-env-audit.json"
TRUTH_SNAPSHOT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "latest.json"
LITELLM_TEMPLATE_PATH = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "templates" / "litellm_config.yaml.j2"
VAULT_LITELLM_TASKS_PATH = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "tasks" / "main.yml"

ALLOWED_RUNTIME_CLASSES = {
    "control_plane",
    "data_plane",
    "product_app",
    "scaffold",
    "deprecated",
}
ALLOWED_AUTH_CLASSES = {
    "public_read",
    "operator",
    "admin",
    "destructive_admin",
    "internal_only",
}
ALLOWED_PROJECT_CLASSES = {
    "platform-core",
    "production-product",
    "active-scaffold",
    "incubation",
    "archive",
}
ALLOWED_DOC_CLASSES = {"canonical", "generated", "reference", "archive"}
REQUIRED_LENSES = {
    "security",
    "truth",
    "reliability",
    "developer_velocity",
    "product_integrity",
    "architecture",
    "observability",
    "evaluation",
    "portfolio_discipline",
    "economic_efficiency",
    "knowledge_quality",
    "autonomy_governance",
}
REQUIRED_CADENCE_KEYS = {"daily", "twice_weekly", "weekly", "biweekly", "monthly", "quarterly"}
DOC_LIFECYCLE_SCAN_PATHS = (
    ("*.md",),
    ("docs", "*.md"),
    ("docs", "operations", "*.md"),
    ("docs", "projects", "*.md"),
    ("docs", "runbooks", "*.md"),
    ("docs", "projects", "*", "*.md"),
    ("projects", "*", "docs", "*.md"),
)
GENERATED_DOC_GENERATORS = {
    "docs/DOCUMENTATION-INDEX.md": ["scripts/generate_documentation_index.py"],
    "docs/operations/PROJECT-MATURITY-REPORT.md": ["scripts/generate_project_maturity_report.py"],
    "docs/operations/HARDWARE-REPORT.md": ["scripts/generate_truth_inventory_reports.py", "--report", "hardware"],
    "docs/operations/MODEL-DEPLOYMENT-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "models",
    ],
    "docs/operations/PROVIDER-CATALOG-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "providers",
    ],
    "docs/operations/TOOLING-INVENTORY-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "tooling",
    ],
    "docs/operations/REPO-ROOTS-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "repo_roots",
    ],
    "docs/operations/OPERATOR-SURFACE-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "operator_surfaces",
    ],
    "docs/operations/RUNTIME-MIGRATION-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "runtime_migrations",
    ],
    "docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "runtime_cutover",
    ],
    "docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "vault_litellm_repair_packet",
    ],
    "docs/operations/AUTONOMY-ACTIVATION-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "autonomy_activation",
    ],
    "docs/operations/TRUTH-DRIFT-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "drift",
    ],
    "docs/operations/SECRET-SURFACE-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "secret_surfaces",
    ],
}
CI_WORKFLOW_PATH = REPO_ROOT / ".gitea" / "workflows" / "ci.yml"
BUILD_MANIFEST_ACTIVE_PATH = REPO_ROOT / "docs" / "BUILD-MANIFEST.md"
BUILD_MANIFEST_ARCHIVE_PATH = REPO_ROOT / "docs" / "archive" / "BUILD-MANIFEST.md"
ACTIVE_HARDWARE_LEDGER_PATH = REPO_ROOT / "docs" / "hardware" / "inventory.md"
ARCHIVED_HARDWARE_LEDGER_PATH = REPO_ROOT / "docs" / "archive" / "hardware" / "hardware-inventory.md"
BUILD_COMMAND_PATH = REPO_ROOT / ".claude" / "commands" / "build.md"
ACTIVE_DAILY_OPERATIONS_PATH = REPO_ROOT / "docs" / "guides" / "daily-operations.md"
MASTER_PLAN_PATH = REPO_ROOT / "docs" / "MASTER-PLAN.md"
ACTIVE_TACTICAL_PLAN_PATH = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-03-18-athanor-coo-architecture.md"
ACTIVE_TACTICAL_PLAN_FULL_PATH = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-03-18-athanor-coo-architecture-FULL.md"
ARCHIVED_TACTICAL_PLAN_FULL_PATH = REPO_ROOT / "docs" / "archive" / "planning-era" / "2026-03-18-athanor-coo-architecture-FULL.md"
PLATFORM_TOPOLOGY_PATH = CONFIG_DIR / "platform-topology.json"
REFERENCE_INDEX_PATH = REPO_ROOT / "docs" / "REFERENCE-INDEX.md"
ALLOWED_STALE_DOC_PATH_MENTIONS = {
    "docs/BUILD-MANIFEST.md": {
        "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
    },
    "docs/hardware/inventory.md": set(),
}
ACTIVE_PORTAL_REFERENCE_SCAN_PATHS = (
    "ansible/files/monitoring/prometheus.yml",
    "ansible/host_vars/vault.yml",
    "ansible/roles/agents/defaults/main.yml",
    "projects/agents/.env.example",
    "projects/agents/docker-compose.yml",
    "projects/agents/src/athanor_agents/escalation.py",
    "tests/harness.py",
    "tests/ui-audit/last-run.json",
    ".claude/commands/health.md",
    ".claude/commands/status.md",
    ".claude/skills/troubleshoot.md",
    "docs/decisions/ADR-019-command-center.md",
    "docs/decisions/ADR-020-interaction-architecture.md",
    "docs/decisions/adr-remote-access.md",
    "docs/design/command-center.md",
    "docs/design/personal-data-architecture.md",
    "docs/design/project-platform-architecture.md",
    "docs/design/visual-system/THEME_SAMPLER_NOTES.md",
    "scripts/build-profile.py",
    "tests/ui-audit/last-run.json",
)
DEFAULT_DEPLOYMENT_PLAYBOOKS = (
    "ansible/playbooks/site.yml",
    "ansible/playbooks/deploy-services.yml",
    "ansible/playbooks/node2.yml",
)
STALE_WORKSHOP_PORTAL_PATTERNS = (
    "192.168.1.225:3001",
    "workshop:3001",
    "{{ node2_ip }}:3001",
    "{{ agent_node2_host }}:3001",
    "{{ node2_host }}:3001",
)
STALE_DEV_PORTAL_PATTERNS = (
    "192.168.1.189:3001",
    "{{ agent_dev_host }}:3001",
    "{{ dev_ip }}:3001",
)
REQUIRED_STARTUP_DOC_CONTRACT = {
    "README.md": [
        "Implementation authority: `C:\\Athanor`",
        "Runtime authority: `/home/shaun/repos/athanor` on `DEV`",
        "Reference-only docs:",
        "Archive criteria:",
    ],
    "AGENTS.md": [
        "Implementation authority: `C:\\Athanor`",
        "Runtime authority: `/home/shaun/repos/athanor` on `DEV`",
        "Reference-only docs:",
        "Archive criteria:",
    ],
    "CLAUDE.md": [
        "Implementation authority: `C:\\Athanor`",
        "Runtime authority: `/home/shaun/repos/athanor` on `DEV`",
        "Reference-only docs:",
        "Archive criteria:",
    ],
}
ALLOWED_PROVIDER_CATEGORIES = {"local", "subscription", "api"}
ALLOWED_PROVIDER_ROUTING_POSTURES = {"ordinary_auto", "governed_handoff_only", "disabled"}
ALLOWED_PROVIDER_EVIDENCE_KINDS = {"cli_subscription", "vault_litellm_proxy"}
ALLOWED_PROVIDER_CLI_PROBE_STATUSES = {"installed", "missing", "degraded", "mixed"}
ALLOWED_PROVIDER_BILLING_STATUSES = {
    "verified",
    "operator_visible_tier_unverified",
    "published_tiers_known_subscribed_tier_unverified",
}
ALLOWED_PROVIDER_SPECIFIC_USAGE_STATUSES = {"pending", "observed", "verified", "not_supported"}
ALLOWED_PROVIDER_USAGE_CAPTURE_STATUSES = {"observed", "verified", "not_supported", "auth_failed", "request_failed"}
ALLOWED_PROVIDER_STATES = {
    "active-routing",
    "active-burn",
    "active-api",
    "configured-unused",
    "research-only",
    "historical",
}
ALLOWED_BURN_SUBSCRIPTION_TYPES = {"rolling_window", "daily_reset", "monthly_reset", "depleting"}
ALLOWED_OPERATOR_SURFACE_KINDS = {"portal", "domain_app", "specialist_tool", "internal_api", "retired"}
ALLOWED_OPERATOR_SURFACE_DEPLOYMENT_MODES = {
    "repo_standalone_process",
    "containerized_service",
    "containerized_service_behind_caddy",
    "docker_container",
    "service_runtime",
    "retired_shadow",
}
ALLOWED_OPERATOR_SURFACE_NAVIGATION_ROLES = {"front_door", "launchpad", "hidden"}
ALLOWED_OPERATOR_SURFACE_STATUSES = {
    "active_production",
    "degraded_production",
    "active_specialist",
    "active_internal",
    "shadow",
    "retired",
    "planned",
}
ALLOWED_OPERATOR_SURFACE_RETIREMENT_STATES = {"keep", "candidate", "shadow_pending_retirement", "retired"}
ALLOWED_ROOT_AUTHORITY_LEVELS = {
    "implementation-authority",
    "runtime-authority",
    "runtime-state",
    "incubation",
    "vestigial",
    "archive",
}
ALLOWED_MODEL_STATE_CLASSES = {
    "deployed",
    "degraded",
    "configured",
    "stored_local",
    "stored_shared",
    "researched",
    "historical",
}
ALLOWED_CREDENTIAL_DELIVERY_METHODS = {
    "inline_env_assignments",
    "cron_wrapper_envfile",
    "service_env_or_envfile",
    "service_envfile",
    "container_env",
    "process_env",
    "local_runtime_envfile",
}
ALLOWED_CREDENTIAL_REMEDIATION_STATES = {
    "remediation_required",
    "review_required",
    "managed",
    "runtime_prerequisite",
}
ALLOWED_RUNTIME_SUBSYSTEM_STATUSES = {"live", "implemented_not_live", "planned", "deprecated", "legacy"}
ALLOWED_RUNTIME_MIGRATION_STATUSES = {"runtime_pending", "repo_ready", "cutover_ready", "retired"}
ALLOWED_RUNTIME_IMPLEMENTATION_STATES = {"repo_pending", "migrated", "retired"}
ALLOWED_RUNTIME_CUTOVER_STATES = {"pending_dev_cutover", "cutover_in_progress", "cutover_verified"}
ALLOWED_RUNTIME_SYNC_STRATEGIES = {"backup_then_replace_from_implementation_authority"}
ALLOWED_AUTONOMY_REGISTRY_STATUSES = {"configured", "live_partial", "live", "degraded"}
ALLOWED_AUTONOMY_ACTIVATION_STATES = {
    "blocked",
    "ready_for_operator_enable",
    "software_core_active",
    "expanded_core_active",
    "full_system_active",
}
AUTONOMY_ACTIVE_STATE_TO_PHASE_ID = {
    "software_core_active": "software_core_phase_1",
    "expanded_core_active": "expanded_core_phase_2",
    "full_system_active": "full_system_phase_3",
}
ALLOWED_AUTONOMY_PHASE_STATUSES = {"planned", "blocked", "ready", "active"}
ALLOWED_AUTONOMY_PREREQUISITE_STATUSES = {"pending", "verified", "blocked"}
RUNTIME_MIGRATION_MIGRATED_FORBIDDEN_TOKENS = (":8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL")
REQUIRED_CANONICAL_DOC_HEADERS = {
    "docs/SYSTEM-SPEC.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "config/automation-backbone/project-maturity-registry.json",
            "config/automation-backbone/program-operating-system.json",
        ],
        "versions": [
            "platform-topology.json",
            "project-maturity-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/SERVICES.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "docs/projects/PORTFOLIO-REGISTRY.md",
        ],
        "versions": [
            "platform-topology.json",
            "project-maturity-registry.json",
        ],
    },
    "docs/RECOVERY.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "docs/operations/OPERATOR_RUNBOOKS.md",
            "docs/runbooks/credential-rotation.md",
        ],
        "versions": [
            "platform-topology.json",
            "program-operating-system.json",
        ],
    },
    "docs/SECURITY-FOLLOWUPS.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "config/automation-backbone/credential-surface-registry.json",
            "docs/runbooks/credential-rotation.md",
        ],
        "versions": [
            "platform-topology.json",
            "credential-surface-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/credential-rotation.md": {
        "sources": [
            "docs/SECURITY-FOLLOWUPS.md",
            "config/automation-backbone/platform-topology.json",
            "config/automation-backbone/credential-surface-registry.json",
        ],
        "versions": [
            "platform-topology.json",
            "credential-surface-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/rebuild-dev.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "docs/RECOVERY.md",
        ],
        "versions": [
            "platform-topology.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/dev-secret-delivery-normalization.md": {
        "sources": [
            "config/automation-backbone/credential-surface-registry.json",
            "config/automation-backbone/repo-roots-registry.json",
            "docs/SECURITY-FOLLOWUPS.md",
        ],
        "versions": [
            "credential-surface-registry.json",
            "repo-roots-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/local-runtime-env.md": {
        "sources": [
            "config/automation-backbone/credential-surface-registry.json",
            "config/automation-backbone/repo-roots-registry.json",
            "docs/operations/OPERATOR_RUNBOOKS.md",
        ],
        "versions": [
            "credential-surface-registry.json",
            "repo-roots-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/governor-facade-retirement.md": {
        "sources": [
            "config/automation-backbone/platform-topology.json",
            "config/automation-backbone/runtime-subsystem-registry.json",
            "config/automation-backbone/runtime-migration-registry.json",
            "config/automation-backbone/repo-roots-registry.json",
        ],
        "versions": [
            "platform-topology.json",
            "runtime-subsystem-registry.json",
            "runtime-migration-registry.json",
            "repo-roots-registry.json",
        ],
    },
    "docs/runbooks/vault-litellm-provider-auth-repair.md": {
        "sources": [
            "config/automation-backbone/credential-surface-registry.json",
            "config/automation-backbone/provider-catalog.json",
            "docs/operations/SECRET-SURFACE-REPORT.md",
            "docs/operations/PROVIDER-CATALOG-REPORT.md",
        ],
        "versions": [
            "credential-surface-registry.json",
            "provider-catalog.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/software-core-autonomy-activation.md": {
        "sources": [
            "config/automation-backbone/autonomy-activation-registry.json",
            "docs/operations/AUTONOMY-ACTIVATION-REPORT.md",
            "docs/operations/OPERATOR_RUNBOOKS.md",
        ],
        "versions": [
            "autonomy-activation-registry.json",
            "program-operating-system.json",
        ],
    },
}


def _load_json(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_litellm_template_env_names() -> set[str]:
    text = LITELLM_TEMPLATE_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"os\.environ/([A-Z0-9_]+)", text))


def _parse_vault_litellm_task_env_names() -> set[str]:
    text = VAULT_LITELLM_TASKS_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^\s{6}([A-Z0-9_]+):", text, re.MULTILINE))


def _first_env(names: list[str], default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def _expected_hosts(topology: dict[str, Any]) -> dict[str, str]:
    hosts: dict[str, str] = {}
    for node in topology.get("nodes", []):
        env_names = [str(name) for name in node.get("host_envs", [])]
        hosts[str(node["id"])] = _first_env(env_names, str(node.get("default_host") or ""))
    return hosts


def _expected_url(service: dict[str, Any], hosts: dict[str, str]) -> str:
    env_name = str(service.get("url_env") or f"ATHANOR_{str(service['id']).upper().replace('-', '_')}_URL")
    override = os.environ.get(env_name, "").strip()
    if override:
        return override
    return f"{service['scheme']}://{hosts[str(service['node'])]}:{int(service['port'])}{service.get('path', '') or ''}"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_agents_settings():
    agents_src = REPO_ROOT / "projects" / "agents" / "src"
    pythonpath = os.pathsep.join([str(agents_src), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    code = """
import json
from athanor_agents.config import Settings

settings = Settings()
print(json.dumps(settings.model_dump()))
""".strip()
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": pythonpath},
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise RuntimeError(f"Unable to load agent settings via subprocess: {detail}")
    return json.loads(result.stdout)


def _workflow_step_names() -> set[str]:
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    return {
        match.group(1).strip()
        for match in re.finditer(r"^\s*-\s+name:\s*(.+?)\s*$", content, re.MULTILINE)
    }


def _extract_header_value(text: str, label: str) -> str:
    match = re.search(rf"(?mi)^{re.escape(label)}:\s*(.+)$", text)
    return match.group(1).strip() if match else ""


def _load_subscription_policy() -> dict[str, Any]:
    path = REPO_ROOT / "projects" / "agents" / "config" / "subscription-routing-policy.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _run_generator_check(command_parts: list[str]) -> subprocess.CompletedProcess[str]:
    script_path = REPO_ROOT / command_parts[0]
    return subprocess.run(
        [sys.executable, str(script_path), *command_parts[1:], "--check"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _looks_like_secret(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if "=" in stripped:
        return True
    lowered = stripped.lower()
    secret_markers = ("sk-", "ghp_", "api_key", "token", "secret", "password")
    return any(marker in lowered for marker in secret_markers)


def _validate_canonical_doc_headers(
    *,
    relative_path: str,
    text: str,
    required_sources: list[str],
    required_versions: list[str],
    registry_versions: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    source_of_truth = _extract_header_value(text, "Source of truth")
    validated_version = _extract_header_value(text, "Validated against registry version")
    mutable_facts_policy = _extract_header_value(text, "Mutable facts policy")

    if not source_of_truth:
        errors.append(f"{relative_path} is missing canonical header line: Source of truth")
    if not validated_version:
        errors.append(f"{relative_path} is missing canonical header line: Validated against registry version")
    if not mutable_facts_policy:
        errors.append(f"{relative_path} is missing canonical header line: Mutable facts policy")

    for source in required_sources:
        if source_of_truth and source not in source_of_truth:
            errors.append(f"{relative_path} canonical header is missing source reference {source}")

    for version_name in required_versions:
        expected = f"{version_name}@{registry_versions[version_name]}"
        if validated_version and expected not in validated_version:
            errors.append(f"{relative_path} canonical header is missing registry version {expected}")

    return errors


def _validate_startup_doc_contract(relative_path: str, text: str) -> list[str]:
    errors: list[str] = []
    for required in REQUIRED_STARTUP_DOC_CONTRACT.get(relative_path, []):
        if required not in text:
            errors.append(f"{relative_path} is missing startup-doc authority contract line containing: {required}")
    return errors


def main() -> int:
    errors: list[str] = []

    topology = _load_json("platform-topology.json")
    hardware_inventory = _load_json("hardware-inventory.json")
    model_deployments = _load_json("model-deployment-registry.json")
    provider_catalog = _load_json("provider-catalog.json")
    subscription_burn = _load_json("subscription-burn-registry.json")
    autonomy_activation = _load_json("autonomy-activation-registry.json")
    tooling_inventory = _load_json("tooling-inventory.json")
    credential_surfaces = _load_json("credential-surface-registry.json")
    operator_surfaces = _load_json("operator-surface-registry.json")
    repo_roots = _load_json("repo-roots-registry.json")
    runtime_subsystems = _load_json("runtime-subsystem-registry.json")
    runtime_migrations = _load_json("runtime-migration-registry.json")
    routing_taxonomy = _load_json("routing-taxonomy-map.json")
    portfolio = _load_json("project-maturity-registry.json")
    docs = _load_json("docs-lifecycle-registry.json")
    provider_usage_evidence = {}
    if PROVIDER_USAGE_EVIDENCE_PATH.exists():
        provider_usage_evidence = json.loads(PROVIDER_USAGE_EVIDENCE_PATH.read_text(encoding="utf-8"))
    vault_litellm_env_audit = {}
    if VAULT_LITELLM_ENV_AUDIT_PATH.exists():
        vault_litellm_env_audit = json.loads(VAULT_LITELLM_ENV_AUDIT_PATH.read_text(encoding="utf-8"))
    latest_truth_snapshot = {}
    if TRUTH_SNAPSHOT_PATH.exists():
        latest_truth_snapshot = json.loads(TRUTH_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    operating_system = _load_json("program-operating-system.json")
    release_ritual = _load_json("release-ritual.json")
    workload_registry = _load_json("workload-class-registry.json")
    policy_registry = _load_json("policy-class-registry.json")
    presence_model = _load_json("operator-presence-model.json")
    subscription_policy = _load_subscription_policy()
    registry_versions = {
        "platform-topology.json": str(topology.get("version") or ""),
        "hardware-inventory.json": str(hardware_inventory.get("version") or ""),
        "model-deployment-registry.json": str(model_deployments.get("version") or ""),
        "provider-catalog.json": str(provider_catalog.get("version") or ""),
        "subscription-burn-registry.json": str(subscription_burn.get("version") or ""),
        "autonomy-activation-registry.json": str(autonomy_activation.get("version") or ""),
        "tooling-inventory.json": str(tooling_inventory.get("version") or ""),
        "credential-surface-registry.json": str(credential_surfaces.get("version") or ""),
        "operator-surface-registry.json": str(operator_surfaces.get("version") or ""),
        "repo-roots-registry.json": str(repo_roots.get("version") or ""),
        "runtime-subsystem-registry.json": str(runtime_subsystems.get("version") or ""),
        "runtime-migration-registry.json": str(runtime_migrations.get("version") or ""),
        "routing-taxonomy-map.json": str(routing_taxonomy.get("version") or ""),
        "project-maturity-registry.json": str(portfolio.get("version") or ""),
        "docs-lifecycle-registry.json": str(docs.get("version") or ""),
        "program-operating-system.json": str(operating_system.get("version") or ""),
    }
    lifecycle_paths = {str(document.get("path") or "") for document in docs.get("documents", [])}
    workflow_steps = _workflow_step_names()

    if BUILD_MANIFEST_ACTIVE_PATH.exists():
        errors.append("docs/BUILD-MANIFEST.md should not exist in the active truth layer; archive it instead")
    if not BUILD_MANIFEST_ARCHIVE_PATH.exists():
        errors.append("docs/archive/BUILD-MANIFEST.md is missing from the archive layer")
    if "docs/BUILD-MANIFEST.md" in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json should not classify docs/BUILD-MANIFEST.md as an active lifecycle entry")
    if "docs/archive/BUILD-MANIFEST.md" not in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json is missing docs/archive/BUILD-MANIFEST.md")

    if ACTIVE_HARDWARE_LEDGER_PATH.exists():
        errors.append("docs/hardware/inventory.md should not remain in the active truth layer; archive it instead")
    if not ARCHIVED_HARDWARE_LEDGER_PATH.exists():
        errors.append("docs/archive/hardware/hardware-inventory.md is missing from the archive layer")
    if "docs/hardware/inventory.md" in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json should not classify docs/hardware/inventory.md as an active lifecycle entry")
    if "docs/archive/hardware/hardware-inventory.md" not in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json is missing docs/archive/hardware/hardware-inventory.md")

    build_command_text = BUILD_COMMAND_PATH.read_text(encoding="utf-8")
    if "docs/BUILD-MANIFEST.md" in build_command_text or "The manifest is updated" in build_command_text:
        errors.append(".claude/commands/build.md still refers to BUILD-MANIFEST as active planning truth")
    if "CONTINUOUS-COMPLETION-BACKLOG.md" not in build_command_text:
        errors.append(".claude/commands/build.md must point at the live execution backlog")

    if ACTIVE_DAILY_OPERATIONS_PATH.exists():
        errors.append("docs/guides/daily-operations.md should not remain in the active truth layer")
    if "docs/guides/daily-operations.md" in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json should not classify docs/guides/daily-operations.md as an active lifecycle entry")

    if ACTIVE_TACTICAL_PLAN_PATH.exists() or ACTIVE_TACTICAL_PLAN_FULL_PATH.exists():
        errors.append("The March 2026 tactical superpowers plans should not remain in the active truth layer")
    if not ARCHIVED_TACTICAL_PLAN_FULL_PATH.exists():
        errors.append("docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md must exist while the historical plan is retained")
    if "docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md" not in lifecycle_paths:
        errors.append("docs-lifecycle-registry.json is missing docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md")

    master_plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    if "FINAL CANONICAL DOCUMENT" in master_plan_text or "Both are canonical" in master_plan_text:
        errors.append("docs/MASTER-PLAN.md still presents stale canonical-status language")
    if "$543.91/mo" in master_plan_text or "Claude Max 20x" in master_plan_text or "Venice AI Pro" in master_plan_text:
        errors.append("docs/MASTER-PLAN.md still carries stale provider pricing or reset tables")
    if "provider-catalog.json" not in master_plan_text or "PROVIDER-CATALOG-REPORT.md" not in master_plan_text:
        errors.append("docs/MASTER-PLAN.md must point live provider truth at the provider catalog and generated report")

    platform_topology_text = PLATFORM_TOPOLOGY_PATH.read_text(encoding="utf-8")
    if "build-manifest" in platform_topology_text.lower():
        errors.append("config/automation-backbone/platform-topology.json still cites build-manifest as active topology truth")

    reference_index_text = REFERENCE_INDEX_PATH.read_text(encoding="utf-8")
    if "docs/hardware/inventory.md" in reference_index_text or "02-hardware/inventory.md" in reference_index_text:
        errors.append("docs/REFERENCE-INDEX.md still points at the old active hardware ledger path")
    if "docs/archive/hardware/hardware-inventory.md" not in reference_index_text:
        errors.append("docs/REFERENCE-INDEX.md must point at docs/archive/hardware/hardware-inventory.md for the historical ledger")

    for stale_reference, allowed_paths in ALLOWED_STALE_DOC_PATH_MENTIONS.items():
        for path in REPO_ROOT.joinpath("docs").rglob("*.md"):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative.startswith("docs/archive/") or relative.startswith("docs/data/"):
                continue
            text = path.read_text(encoding="utf-8")
            if stale_reference in text and relative not in allowed_paths:
                errors.append(f"{relative} still mentions stale active path {stale_reference}")

    node_ids = [str(node["id"]) for node in topology.get("nodes", [])]
    if len(node_ids) != len(set(node_ids)):
        errors.append("platform-topology.json contains duplicate node ids")

    service_ids = [str(service["id"]) for service in topology.get("services", [])]
    if len(service_ids) != len(set(service_ids)):
        errors.append("platform-topology.json contains duplicate service ids")

    known_nodes = set(node_ids)
    for service in topology.get("services", []):
        service_id = str(service["id"])
        if str(service.get("node") or "") not in known_nodes:
            errors.append(f"Service {service_id} references unknown node {service.get('node')!r}")
        if str(service.get("runtime_class") or "") not in ALLOWED_RUNTIME_CLASSES:
            errors.append(f"Service {service_id} has invalid runtime_class {service.get('runtime_class')!r}")
        if str(service.get("auth_class") or "") not in ALLOWED_AUTH_CLASSES:
            errors.append(f"Service {service_id} has invalid auth_class {service.get('auth_class')!r}")

    operator_surface_source = str(operator_surfaces.get("source_of_truth") or "")
    if operator_surface_source != "config/automation-backbone/operator-surface-registry.json":
        errors.append(
            "operator-surface-registry.json must declare source_of_truth "
            "config/automation-backbone/operator-surface-registry.json"
        )
    front_door_contract = dict(operator_surfaces.get("front_door_contract") or {})
    canonical_portal_id = str(front_door_contract.get("canonical_portal_id") or "").strip()
    if not canonical_portal_id:
        errors.append("operator-surface-registry.json is missing front_door_contract.canonical_portal_id")
    canonical_front_door_url = str(front_door_contract.get("canonical_url") or "").strip()
    if canonical_front_door_url != "https://athanor.local/":
        errors.append("operator-surface-registry.json must use https://athanor.local/ as the canonical operator URL")
    if front_door_contract.get("allow_multiple_active_portals") is not False:
        errors.append("operator-surface-registry.json must keep allow_multiple_active_portals=false")

    operator_surface_entries = [
        dict(entry) for entry in operator_surfaces.get("surfaces", []) if isinstance(entry, dict)
    ]
    operator_surface_ids = [str(entry.get("id") or "").strip() for entry in operator_surface_entries if str(entry.get("id") or "").strip()]
    if len(operator_surface_ids) != len(set(operator_surface_ids)):
        errors.append("operator-surface-registry.json contains duplicate surface ids")
    active_production_portals: list[str] = []
    for entry in operator_surface_entries:
        surface_id = str(entry.get("id") or "").strip()
        if not surface_id:
            errors.append("operator-surface-registry.json contains a surface without id")
            continue
        surface_kind = str(entry.get("surface_kind") or "").strip()
        node = str(entry.get("node") or "").strip()
        auth_class = str(entry.get("auth_class") or "").strip()
        deployment_mode = str(entry.get("deployment_mode") or "").strip()
        navigation_role = str(entry.get("navigation_role") or "").strip()
        status = str(entry.get("status") or "").strip()
        retirement_state = str(entry.get("retirement_state") or "").strip()
        canonical_url = str(entry.get("canonical_url") or "").strip()
        runtime_url = str(entry.get("runtime_url") or "").strip()
        if surface_kind not in ALLOWED_OPERATOR_SURFACE_KINDS:
            errors.append(f"operator-surface-registry.json surface {surface_id} has invalid surface_kind {surface_kind!r}")
        if node not in known_nodes:
            errors.append(f"operator-surface-registry.json surface {surface_id} references unknown node {node!r}")
        if auth_class not in ALLOWED_AUTH_CLASSES:
            errors.append(f"operator-surface-registry.json surface {surface_id} has invalid auth_class {auth_class!r}")
        if deployment_mode not in ALLOWED_OPERATOR_SURFACE_DEPLOYMENT_MODES:
            errors.append(
                f"operator-surface-registry.json surface {surface_id} has invalid deployment_mode {deployment_mode!r}"
            )
        if navigation_role not in ALLOWED_OPERATOR_SURFACE_NAVIGATION_ROLES:
            errors.append(
                f"operator-surface-registry.json surface {surface_id} has invalid navigation_role {navigation_role!r}"
            )
        if status not in ALLOWED_OPERATOR_SURFACE_STATUSES:
            errors.append(f"operator-surface-registry.json surface {surface_id} has invalid status {status!r}")
        if retirement_state not in ALLOWED_OPERATOR_SURFACE_RETIREMENT_STATES:
            errors.append(
                f"operator-surface-registry.json surface {surface_id} has invalid retirement_state {retirement_state!r}"
            )
        if surface_kind != "retired" and not canonical_url:
            errors.append(f"operator-surface-registry.json surface {surface_id} is missing canonical_url")
        if not runtime_url:
            errors.append(f"operator-surface-registry.json surface {surface_id} is missing runtime_url")
        if surface_kind == "portal" and status in {"active_production", "degraded_production"}:
            active_production_portals.append(surface_id)
        if surface_id == "workshop_shadow_command_center" and status not in {"shadow", "retired"}:
            errors.append("operator-surface-registry.json workshop_shadow_command_center must stay shadow or retired")
        if node == "workshop" and surface_kind == "portal":
            errors.append("operator-surface-registry.json must not define a production WORKSHOP portal")
    if len(active_production_portals) != 1:
        errors.append(
            "operator-surface-registry.json must define exactly one active production portal; found "
            + ", ".join(active_production_portals or ["none"])
        )
    elif canonical_portal_id and canonical_portal_id not in active_production_portals:
        errors.append(
            "operator-surface-registry.json canonical_portal_id must reference the sole active production portal"
        )
    operator_surface_probe = dict(latest_truth_snapshot.get("operator_surface_probe") or {})
    dev_command_center_runtime = dict(operator_surface_probe.get("dev_command_center_runtime") or {})
    dev_runtime_detail = (
        dict(dev_command_center_runtime.get("detail") or {})
        if isinstance(dev_command_center_runtime.get("detail"), dict)
        else {}
    )
    if str(dev_runtime_detail.get("deployment_mode") or "") == "containerized_service_behind_caddy":
        deployment_root = dict(dev_runtime_detail.get("deployment_root") or {})
        expected_path = str(deployment_root.get("expected_path") or "").strip()
        observed_active_root = str(deployment_root.get("observed_active_root") or "").strip()
        observed_compose_config_files = str(deployment_root.get("observed_compose_config_files") or "").strip()
        if expected_path and observed_active_root and observed_active_root != expected_path:
            errors.append(
                "reports/truth-inventory/latest.json shows dashboard deploy-root drift: "
                f"observed {observed_active_root!r}, expected {expected_path!r}"
            )
        expected_config_path = f"{expected_path}/docker-compose.yml" if expected_path else ""
        if expected_config_path and observed_compose_config_files and observed_compose_config_files != expected_config_path:
            errors.append(
                "reports/truth-inventory/latest.json shows dashboard compose-config drift: "
                f"observed {observed_compose_config_files!r}, expected {expected_config_path!r}"
            )

    for relative_path in ACTIVE_PORTAL_REFERENCE_SCAN_PATHS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for stale_pattern in STALE_WORKSHOP_PORTAL_PATTERNS:
            if stale_pattern in text:
                errors.append(f"{relative_path} still points at the retired WORKSHOP command center via {stale_pattern}")
        for stale_pattern in STALE_DEV_PORTAL_PATTERNS:
            if stale_pattern in text:
                errors.append(f"{relative_path} still points at the raw DEV command-center runtime via {stale_pattern}")
    for relative_path in DEFAULT_DEPLOYMENT_PLAYBOOKS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\s*-\s*\{\s*role:\s*dashboard\b", text) or re.search(r"(?m)^\s*-\s*dashboard\b", text):
            errors.append(
                f"{relative_path} must not deploy the dashboard role by default; use command-center-dev.yml or workshop-shadow-dashboard.yml instead"
            )

    hardware_node_ids = [str(node.get("id") or "") for node in hardware_inventory.get("nodes", [])]
    if set(hardware_node_ids) != known_nodes:
        missing = sorted(known_nodes - set(hardware_node_ids))
        extra = sorted(set(hardware_node_ids) - known_nodes)
        if missing:
            errors.append(f"hardware-inventory.json is missing topology nodes: {', '.join(missing)}")
        if extra:
            errors.append(f"hardware-inventory.json includes non-topology nodes: {', '.join(extra)}")

    provider_entries = [dict(entry) for entry in provider_catalog.get("providers", []) if isinstance(entry, dict)]
    provider_ids = [str(entry.get("id") or "") for entry in provider_entries]
    provider_index = {str(entry.get("id") or ""): entry for entry in provider_entries if str(entry.get("id") or "").strip()}
    tooling_by_provider: dict[str, list[dict[str, Any]]] = {}
    for host in tooling_inventory.get("hosts", []):
        for tool in host.get("tools", []):
            provider_id = str(tool.get("provider_id") or "").strip()
            if provider_id:
                tooling_by_provider.setdefault(provider_id, []).append(dict(tool))
    if len(provider_ids) != len(set(provider_ids)):
        errors.append("provider-catalog.json contains duplicate provider ids")
    provider_categories = {str(entry.get("category") or "") for entry in provider_entries}
    unknown_categories = sorted(provider_categories - ALLOWED_PROVIDER_CATEGORIES)
    if unknown_categories:
        errors.append(f"provider-catalog.json has invalid categories: {', '.join(unknown_categories)}")
    for entry in provider_entries:
        provider_id = str(entry.get("id") or "")
        state_classes = {str(item) for item in entry.get("state_classes", [])}
        invalid_states = sorted(state_classes - ALLOWED_PROVIDER_STATES)
        if invalid_states:
            errors.append(
                f"provider-catalog.json provider {provider_id} has invalid state classes: {', '.join(invalid_states)}"
            )
        if not str(entry.get("label") or "").strip():
            errors.append(f"provider-catalog.json provider {provider_id} is missing label")
        observed_runtime = dict(entry.get("observed_runtime") or {})
        verification_steps = [str(step).strip() for step in entry.get("verification_steps", [])]
        if "verification_steps" in entry and any(not step for step in verification_steps):
            errors.append(
                f"provider-catalog.json provider {provider_id} contains blank verification_steps entries"
            )
        if "configured-unused" in state_classes and bool(observed_runtime.get("active_burn_observed")):
            errors.append(
                f"provider-catalog.json provider {provider_id} cannot be configured-unused while active_burn_observed is true"
            )
        if str(entry.get("official_pricing_status") or "") == "official_verified" and entry.get("monthly_cost_usd") is None:
            errors.append(
                f"provider-catalog.json provider {provider_id} must declare monthly_cost_usd when official_pricing_status is official_verified"
            )
        evidence = dict(entry.get("evidence") or {})
        evidence_kind = str(evidence.get("kind") or "")
        if evidence_kind and evidence_kind not in ALLOWED_PROVIDER_EVIDENCE_KINDS:
            errors.append(
                f"provider-catalog.json provider {provider_id} has invalid evidence.kind {evidence_kind!r}"
            )
        execution_modes = {str(item) for item in entry.get("execution_modes", []) if str(item).strip()}
        observed_hosts = {str(host).strip().lower() for host in entry.get("observed_hosts", []) if str(host).strip()}
        pricing_status = str(entry.get("official_pricing_status") or "")
        requires_explicit_evidence = (
            ("cost-unverified" in pricing_status)
            or (
                str(entry.get("access_mode") or "") == "api"
                and "litellm_proxy" in execution_modes
                and "vault" in observed_hosts
            )
        )
        if requires_explicit_evidence and not evidence:
            errors.append(
                f"provider-catalog.json provider {provider_id} must declare explicit evidence for weak-lane verification"
            )
        if evidence_kind == "cli_subscription":
            cli_probe = dict(evidence.get("cli_probe") or {})
            billing = dict(evidence.get("billing") or {})
            cli_status = str(cli_probe.get("status") or "")
            if cli_status not in ALLOWED_PROVIDER_CLI_PROBE_STATUSES:
                errors.append(
                    f"provider-catalog.json provider {provider_id} has invalid cli_probe.status {cli_status!r}"
                )
            if not list(cli_probe.get("expected_hosts", [])):
                errors.append(f"provider-catalog.json provider {provider_id} cli_probe must declare expected_hosts")
            if not list(cli_probe.get("required_commands", [])):
                errors.append(f"provider-catalog.json provider {provider_id} cli_probe must declare required_commands")
            if not str(cli_probe.get("last_verified_at") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} cli_probe is missing last_verified_at")
            if not str(cli_probe.get("source") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} cli_probe is missing source")
            if "cost-unverified" in pricing_status:
                billing_status = str(billing.get("status") or "")
                if billing_status not in ALLOWED_PROVIDER_BILLING_STATUSES:
                    errors.append(
                        f"provider-catalog.json provider {provider_id} has invalid billing.status {billing_status!r}"
                    )
                if not str(billing.get("last_verified_at") or "").strip():
                    errors.append(f"provider-catalog.json provider {provider_id} billing is missing last_verified_at")
                if not str(billing.get("source") or "").strip():
                    errors.append(f"provider-catalog.json provider {provider_id} billing is missing source")
                if billing_status == "verified" and billing.get("verified_monthly_cost_usd") is None:
                    errors.append(
                        f"provider-catalog.json provider {provider_id} billing.status verified requires verified_monthly_cost_usd"
                    )
        if evidence_kind == "vault_litellm_proxy":
            proxy = dict(evidence.get("proxy") or {})
            provider_specific_usage = dict(evidence.get("provider_specific_usage") or {})
            if str(proxy.get("host") or "").strip().lower() != "vault":
                errors.append(f"provider-catalog.json provider {provider_id} proxy.host must be 'vault'")
            if not str(proxy.get("alias") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} proxy is missing alias")
            preferred_models = [str(item).strip() for item in proxy.get("preferred_models", []) if str(item).strip()]
            if not preferred_models:
                errors.append(
                    f"provider-catalog.json provider {provider_id} proxy is missing preferred_models"
                )
            match_tokens = [str(item).strip() for item in proxy.get("served_model_match_tokens", []) if str(item).strip()]
            if not match_tokens:
                errors.append(
                    f"provider-catalog.json provider {provider_id} proxy is missing served_model_match_tokens"
                )
            if not str(proxy.get("last_verified_at") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} proxy is missing last_verified_at")
            if not str(proxy.get("source") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} proxy is missing source")
            provider_specific_status = str(provider_specific_usage.get("status") or "")
            if provider_specific_status not in ALLOWED_PROVIDER_SPECIFIC_USAGE_STATUSES:
                errors.append(
                    f"provider-catalog.json provider {provider_id} has invalid provider_specific_usage.status {provider_specific_status!r}"
                )
            if not str(provider_specific_usage.get("proof_kind") or "").strip():
                errors.append(
                    f"provider-catalog.json provider {provider_id} provider_specific_usage is missing proof_kind"
                )
            if provider_specific_status in {"observed", "verified"}:
                if not str(provider_specific_usage.get("last_verified_at") or "").strip():
                    errors.append(
                        f"provider-catalog.json provider {provider_id} provider_specific_usage is missing last_verified_at"
                    )
                if not str(provider_specific_usage.get("source") or "").strip():
                    errors.append(
                        f"provider-catalog.json provider {provider_id} provider_specific_usage is missing source"
                    )

    burn_source = str(subscription_burn.get("source_of_truth") or "")
    if burn_source != "config/automation-backbone/subscription-burn-registry.json":
        errors.append(
            "subscription-burn-registry.json must declare source_of_truth "
            "config/automation-backbone/subscription-burn-registry.json"
        )
    burn_subscriptions = [dict(entry) for entry in subscription_burn.get("subscriptions", []) if isinstance(entry, dict)]
    burn_subscription_ids = [str(entry.get("id") or "") for entry in burn_subscriptions]
    if len(burn_subscription_ids) != len(set(burn_subscription_ids)):
        errors.append("subscription-burn-registry.json contains duplicate subscription ids")
    burn_stats_keys = [str(entry.get("stats_key") or "") for entry in burn_subscriptions if str(entry.get("stats_key") or "").strip()]
    if len(burn_stats_keys) != len(set(burn_stats_keys)):
        errors.append("subscription-burn-registry.json contains duplicate stats_key values")
    burn_subscription_id_set = {sub_id for sub_id in burn_subscription_ids if sub_id}
    for entry in burn_subscriptions:
        subscription_id = str(entry.get("id") or "").strip()
        if not subscription_id:
            errors.append("subscription-burn-registry.json contains a subscription without id")
            continue
        provider_id = str(entry.get("provider_id") or "").strip()
        if not provider_id:
            errors.append(f"subscription-burn-registry.json subscription {subscription_id} is missing provider_id")
        elif provider_id not in provider_index:
            errors.append(
                f"subscription-burn-registry.json subscription {subscription_id} references unknown provider_id {provider_id!r}"
            )
        subscription_type = str(entry.get("type") or "").strip()
        if subscription_type not in ALLOWED_BURN_SUBSCRIPTION_TYPES:
            errors.append(
                f"subscription-burn-registry.json subscription {subscription_id} has invalid type {subscription_type!r}"
            )
        if not str(entry.get("task_file") or "").strip():
            errors.append(f"subscription-burn-registry.json subscription {subscription_id} is missing task_file")
        if not str(entry.get("cli_env") or "").strip():
            errors.append(f"subscription-burn-registry.json subscription {subscription_id} is missing cli_env")
        if not str(entry.get("cli_command") or "").strip():
            errors.append(f"subscription-burn-registry.json subscription {subscription_id} is missing cli_command")
        if not str(entry.get("stats_key") or "").strip():
            errors.append(f"subscription-burn-registry.json subscription {subscription_id} is missing stats_key")
        if subscription_type == "daily_reset" and entry.get("daily_limit") is None:
            errors.append(
                f"subscription-burn-registry.json subscription {subscription_id} daily_reset entries must declare daily_limit"
            )
        if subscription_type == "rolling_window" and entry.get("window_hours") is None:
            errors.append(
                f"subscription-burn-registry.json subscription {subscription_id} rolling_window entries must declare window_hours"
            )

    burn_windows = [dict(entry) for entry in subscription_burn.get("windows", []) if isinstance(entry, dict)]
    burn_window_ids = [str(entry.get("id") or "") for entry in burn_windows]
    if len(burn_window_ids) != len(set(burn_window_ids)):
        errors.append("subscription-burn-registry.json contains duplicate window ids")
    for entry in burn_windows:
        window_id = str(entry.get("id") or "").strip()
        if not window_id:
            errors.append("subscription-burn-registry.json contains a window without id")
            continue
        subscriptions = [str(item) for item in entry.get("subscriptions", []) if str(item).strip()]
        if not subscriptions:
            errors.append(f"subscription-burn-registry.json window {window_id} must declare subscriptions")
        unknown_subscriptions = sorted(set(subscriptions) - burn_subscription_id_set)
        if unknown_subscriptions:
            errors.append(
                f"subscription-burn-registry.json window {window_id} references unknown subscriptions: "
                + ", ".join(unknown_subscriptions)
            )

    autonomy_source = str(autonomy_activation.get("source_of_truth") or "")
    if autonomy_source != "config/automation-backbone/autonomy-activation-registry.json":
        errors.append(
            "autonomy-activation-registry.json must declare source_of_truth "
            "config/automation-backbone/autonomy-activation-registry.json"
        )
    autonomy_status = str(autonomy_activation.get("status") or "")
    if autonomy_status not in ALLOWED_AUTONOMY_REGISTRY_STATUSES:
        errors.append(f"autonomy-activation-registry.json has invalid status {autonomy_status!r}")
    activation_state = str(autonomy_activation.get("activation_state") or "")
    if activation_state not in ALLOWED_AUTONOMY_ACTIVATION_STATES:
        errors.append(f"autonomy-activation-registry.json has invalid activation_state {activation_state!r}")
    if not isinstance(autonomy_activation.get("broad_autonomy_enabled"), bool):
        errors.append("autonomy-activation-registry.json broad_autonomy_enabled must be a boolean")
    if not isinstance(autonomy_activation.get("runtime_mutations_approval_gated"), bool):
        errors.append("autonomy-activation-registry.json runtime_mutations_approval_gated must be a boolean")
    if autonomy_activation.get("runtime_mutations_approval_gated") is not True:
        errors.append("autonomy-activation-registry.json runtime_mutations_approval_gated must remain true")

    workload_ids = {
        str(item.get("id") or "").strip()
        for item in workload_registry.get("classes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    phase_entries = [
        dict(entry)
        for entry in autonomy_activation.get("phases", [])
        if isinstance(entry, dict)
    ]
    phase_ids = [str(entry.get("id") or "").strip() for entry in phase_entries if str(entry.get("id") or "").strip()]
    if len(phase_ids) != len(set(phase_ids)):
        errors.append("autonomy-activation-registry.json contains duplicate phase ids")
    phase_id_set = set(phase_ids)
    phase_order = {phase_id: index for index, phase_id in enumerate(phase_ids)}
    current_phase_id = str(autonomy_activation.get("current_phase_id") or "").strip()
    if not current_phase_id:
        errors.append("autonomy-activation-registry.json is missing current_phase_id")
    elif current_phase_id not in phase_id_set:
        errors.append(
            "autonomy-activation-registry.json current_phase_id references unknown phase "
            f"{current_phase_id!r}"
        )

    for phase in phase_entries:
        phase_id = str(phase.get("id") or "").strip()
        if not phase_id:
            errors.append("autonomy-activation-registry.json contains a phase without id")
            continue
        phase_status = str(phase.get("status") or "").strip()
        if phase_status not in ALLOWED_AUTONOMY_PHASE_STATUSES:
            errors.append(
                f"autonomy-activation-registry.json phase {phase_id} has invalid status {phase_status!r}"
            )
        allowed_workloads = [str(item).strip() for item in phase.get("allowed_workload_classes", []) if str(item).strip()]
        blocked_workloads = [str(item).strip() for item in phase.get("blocked_workload_classes", []) if str(item).strip()]
        unknown_allowed = sorted(set(allowed_workloads) - workload_ids)
        if unknown_allowed:
            errors.append(
                f"autonomy-activation-registry.json phase {phase_id} references unknown allowed workload classes: "
                + ", ".join(unknown_allowed)
            )
        unknown_blocked = sorted(set(blocked_workloads) - workload_ids)
        if unknown_blocked:
            errors.append(
                f"autonomy-activation-registry.json phase {phase_id} references unknown blocked workload classes: "
                + ", ".join(unknown_blocked)
            )
        if not [str(item).strip() for item in phase.get("allowed_loop_families", []) if str(item).strip()]:
            errors.append(
                f"autonomy-activation-registry.json phase {phase_id} must declare allowed_loop_families"
            )
        if not [str(item).strip() for item in phase.get("blocked_without_approval", []) if str(item).strip()]:
            errors.append(
                f"autonomy-activation-registry.json phase {phase_id} must declare blocked_without_approval"
            )

    prerequisites = [
        dict(entry)
        for entry in autonomy_activation.get("prerequisites", [])
        if isinstance(entry, dict)
    ]
    unmet_scoped_prerequisites: list[str] = []
    for prerequisite in prerequisites:
        prerequisite_id = str(prerequisite.get("id") or "").strip()
        status = str(prerequisite.get("status") or "").strip()
        phase_scope = str(prerequisite.get("phase_scope") or "").strip()
        if not prerequisite_id:
            errors.append("autonomy-activation-registry.json contains a prerequisite without id")
            continue
        if status not in ALLOWED_AUTONOMY_PREREQUISITE_STATUSES:
            errors.append(
                f"autonomy-activation-registry.json prerequisite {prerequisite_id} has invalid status {status!r}"
            )
        if phase_scope and phase_scope not in phase_id_set:
            errors.append(
                f"autonomy-activation-registry.json prerequisite {prerequisite_id} references unknown phase_scope {phase_scope!r}"
            )
        if status == "verified":
            continue
        current_phase_order = phase_order.get(current_phase_id)
        if current_phase_order is None:
            continue
        if not phase_scope:
            unmet_scoped_prerequisites.append(prerequisite_id)
            continue
        scope_order = phase_order.get(phase_scope)
        if scope_order is None or scope_order <= current_phase_order:
            unmet_scoped_prerequisites.append(prerequisite_id)

    current_phase = next((entry for entry in phase_entries if str(entry.get("id") or "") == current_phase_id), None)
    expected_active_phase_id = AUTONOMY_ACTIVE_STATE_TO_PHASE_ID.get(activation_state)
    if expected_active_phase_id and current_phase_id != expected_active_phase_id:
        errors.append(
            "autonomy-activation-registry.json activation_state "
            f"{activation_state!r} must use current_phase_id {expected_active_phase_id!r}"
        )
    if activation_state == "ready_for_operator_enable":
        if current_phase is None or str(current_phase.get("status") or "").strip() != "ready":
            errors.append(
                "autonomy-activation-registry.json ready_for_operator_enable requires the current phase status to be 'ready'"
            )
    elif expected_active_phase_id:
        if current_phase is None or str(current_phase.get("status") or "").strip() != "active":
            errors.append(
                f"autonomy-activation-registry.json activation_state {activation_state!r} requires the current phase status to be 'active'"
            )
    if activation_state in {"ready_for_operator_enable", *AUTONOMY_ACTIVE_STATE_TO_PHASE_ID.keys()} and unmet_scoped_prerequisites:
        errors.append(
            "autonomy-activation-registry.json current phase cannot advance while scoped prerequisites remain unverified: "
            + ", ".join(sorted(set(unmet_scoped_prerequisites)))
        )
    if bool(autonomy_activation.get("broad_autonomy_enabled")) and activation_state != "full_system_active":
        errors.append(
            "autonomy-activation-registry.json broad_autonomy_enabled may only be true when activation_state is 'full_system_active'"
        )
    if activation_state == "full_system_active" and autonomy_activation.get("broad_autonomy_enabled") is not True:
        errors.append(
            "autonomy-activation-registry.json full_system_active requires broad_autonomy_enabled=true"
        )

    software_core_phase = next((entry for entry in phase_entries if str(entry.get("id") or "") == "software_core_phase_1"), None)
    if software_core_phase is None:
        errors.append("autonomy-activation-registry.json must define software_core_phase_1")
    else:
        enabled_agents = {str(item).strip() for item in software_core_phase.get("enabled_agents", []) if str(item).strip()}
        required_agents = {"coding-agent", "research-agent", "knowledge-agent", "general-assistant"}
        if not required_agents.issubset(enabled_agents):
            missing_agents = sorted(required_agents - enabled_agents)
            errors.append(
                "autonomy-activation-registry.json software_core_phase_1 is missing required enabled agents: "
                + ", ".join(missing_agents)
            )
        blocked_workloads = {
            str(item).strip() for item in software_core_phase.get("blocked_workload_classes", []) if str(item).strip()
        }
        required_blocked = {"refusal_sensitive_creative", "explicit_dialogue"}
        if not required_blocked.issubset(blocked_workloads):
            missing_blocked = sorted(required_blocked - blocked_workloads)
            errors.append(
                "autonomy-activation-registry.json software_core_phase_1 must block: "
                + ", ".join(missing_blocked)
            )

    captures = provider_usage_evidence.get("captures", []) if isinstance(provider_usage_evidence, dict) else []
    if captures and not isinstance(captures, list):
        errors.append("reports/truth-inventory/provider-usage-evidence.json captures must be a list")
        captures = []
    for capture in captures:
        if not isinstance(capture, dict):
            errors.append("reports/truth-inventory/provider-usage-evidence.json captures entries must be objects")
            continue
        provider_id = str(capture.get("provider_id") or "").strip()
        status = str(capture.get("status") or "").strip()
        observed_at = str(capture.get("observed_at") or "").strip()
        source = str(capture.get("source") or "").strip()
        proof_kind = str(capture.get("proof_kind") or "").strip()
        alias = str(capture.get("alias") or "").strip()
        requested_model = str(capture.get("requested_model") or "").strip()
        response_model = str(capture.get("response_model") or "").strip()
        matched_by = str(capture.get("matched_by") or "").strip()
        request_surface = str(capture.get("request_surface") or "").strip()
        error_snippet = capture.get("error_snippet")
        http_status = capture.get("http_status")
        if provider_id not in provider_index:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture references unknown provider "
                f"{provider_id!r}"
            )
            continue
        provider = provider_index[provider_id]
        expected_alias = str((dict(dict(provider.get("evidence") or {}).get("proxy") or {}).get("alias") or "")).strip()
        if status not in ALLOWED_PROVIDER_USAGE_CAPTURE_STATUSES:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} has invalid status {status!r}"
            )
        if not observed_at:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} is missing observed_at"
            )
        if not source:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} is missing source"
            )
        if not proof_kind:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} is missing proof_kind"
            )
        if expected_alias and alias != expected_alias:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} has alias {alias!r} but expected {expected_alias!r}"
            )
        if not request_surface:
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} is missing request_surface"
            )
        if status in {"observed", "verified"}:
            if not requested_model:
                errors.append(
                    "reports/truth-inventory/provider-usage-evidence.json capture for "
                    f"{provider_id} is missing requested_model"
                )
            if not response_model:
                errors.append(
                    "reports/truth-inventory/provider-usage-evidence.json capture for "
                    f"{provider_id} is missing response_model"
                )
            if not matched_by:
                errors.append(
                    "reports/truth-inventory/provider-usage-evidence.json capture for "
                    f"{provider_id} is missing matched_by"
                )
        if status in {"auth_failed", "request_failed"} and not str(error_snippet or "").strip():
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} is missing error_snippet"
            )
        if http_status is not None and not isinstance(http_status, int):
            errors.append(
                "reports/truth-inventory/provider-usage-evidence.json capture for "
                f"{provider_id} has non-integer http_status"
            )

    routing_provider_ids = {str(item) for item in dict(subscription_policy.get("providers") or {}).keys()}
    missing_catalog_providers = sorted(routing_provider_ids - set(provider_ids))
    if missing_catalog_providers:
        errors.append(
            "subscription-routing-policy.yaml providers missing from provider-catalog.json: "
            + ", ".join(missing_catalog_providers)
        )
    for provider_id, provider_meta in dict(subscription_policy.get("providers") or {}).items():
        policy_entry = dict(provider_meta or {})
        routing_posture = str(policy_entry.get("routing_posture") or "")
        if routing_posture not in ALLOWED_PROVIDER_ROUTING_POSTURES:
            errors.append(
                f"subscription-routing-policy.yaml provider {provider_id} has invalid routing_posture {routing_posture!r}"
            )
        if not str(policy_entry.get("routing_reason") or "").strip():
            errors.append(f"subscription-routing-policy.yaml provider {provider_id} is missing routing_reason")
        catalog_entry = provider_index.get(provider_id)
        if not catalog_entry:
            continue
        access_mode = str(catalog_entry.get("access_mode") or "")
        state_classes = {str(item) for item in catalog_entry.get("state_classes", [])}
        execution_modes = {str(item) for item in catalog_entry.get("execution_modes", [])}
        observed_runtime = dict(catalog_entry.get("observed_runtime") or {})
        installed_tool_present = any(str(tool.get("status") or "") == "installed" for tool in tooling_by_provider.get(provider_id, []))
        if routing_posture == "ordinary_auto":
            if access_mode == "api":
                errors.append(
                    f"subscription-routing-policy.yaml provider {provider_id} cannot be ordinary_auto with access_mode=api"
                )
            if "active-routing" not in state_classes:
                errors.append(
                    f"subscription-routing-policy.yaml provider {provider_id} ordinary_auto posture requires active-routing state"
                )
            if access_mode == "local" and not bool(observed_runtime.get("routing_policy_enabled")):
                errors.append(
                    f"subscription-routing-policy.yaml provider {provider_id} ordinary_auto local lane must be routing_policy_enabled"
                )
            if access_mode == "cli" and not (
                bool(observed_runtime.get("active_burn_observed")) or installed_tool_present
            ):
                errors.append(
                    f"subscription-routing-policy.yaml provider {provider_id} ordinary_auto CLI lane requires installed tool or recent burn evidence"
                )
        if routing_posture == "governed_handoff_only":
            if "handoff_bundle" not in execution_modes:
                errors.append(
                    f"subscription-routing-policy.yaml provider {provider_id} governed_handoff_only posture requires handoff_bundle execution mode"
                )
            for task_class, task_meta in dict(subscription_policy.get("task_classes") or {}).items():
                task_candidates = [str(item) for item in list(task_meta.get("primary", [])) + list(task_meta.get("fallback", []))]
                if provider_id in task_candidates:
                    errors.append(
                        f"subscription-routing-policy.yaml provider {provider_id} governed_handoff_only posture cannot appear in task class {task_class}"
                    )

    tooling_provider_ids = {
        str(tool.get("provider_id") or "")
        for host in tooling_inventory.get("hosts", [])
        for tool in host.get("tools", [])
        if str(tool.get("provider_id") or "").strip()
    }
    unknown_tooling_providers = sorted(tooling_provider_ids - set(provider_ids))
    if unknown_tooling_providers:
        errors.append(
            "tooling-inventory.json references unknown provider ids: " + ", ".join(unknown_tooling_providers)
        )

    implementation_roots = [
        entry
        for entry in repo_roots.get("roots", [])
        if str(entry.get("authority_level") or "") == "implementation-authority"
        and str(entry.get("status") or "") == "active"
    ]
    runtime_roots = [
        entry
        for entry in repo_roots.get("roots", [])
        if str(entry.get("authority_level") or "") == "runtime-authority"
        and str(entry.get("status") or "") == "active"
    ]
    if len(implementation_roots) != 1:
        errors.append("repo-roots-registry.json must declare exactly one active implementation-authority root")
    if len(runtime_roots) != 1:
        errors.append("repo-roots-registry.json must declare exactly one active runtime-authority root")
    for entry in repo_roots.get("roots", []):
        authority_level = str(entry.get("authority_level") or "")
        if authority_level not in ALLOWED_ROOT_AUTHORITY_LEVELS:
            errors.append(
                f"repo-roots-registry.json path {entry.get('path')!r} has invalid authority_level {authority_level!r}"
            )

    runtime_subsystem_entries = [
        dict(entry) for entry in runtime_subsystems.get("subsystems", []) if isinstance(entry, dict)
    ]
    runtime_subsystem_ids = [str(entry.get("id") or "") for entry in runtime_subsystem_entries]
    if len(runtime_subsystem_ids) != len(set(runtime_subsystem_ids)):
        errors.append("runtime-subsystem-registry.json contains duplicate subsystem ids")
    for entry in runtime_subsystem_entries:
        subsystem_id = str(entry.get("id") or "")
        if not subsystem_id:
            errors.append("runtime-subsystem-registry.json contains a subsystem without an id")
            continue
        if not str(entry.get("title") or "").strip():
            errors.append(f"runtime-subsystem-registry.json subsystem {subsystem_id} is missing title")
        status_tag = str(entry.get("status_tag") or "")
        if status_tag not in ALLOWED_RUNTIME_SUBSYSTEM_STATUSES:
            errors.append(
                f"runtime-subsystem-registry.json subsystem {subsystem_id} has invalid status_tag {status_tag!r}"
            )
        invalid_touchpoints = sorted(
            {
                str(path)
                for path in entry.get("dashboard_touchpoints", [])
                if not str(path).startswith("/")
            }
        )
        if invalid_touchpoints:
            errors.append(
                "runtime-subsystem-registry.json subsystem "
                f"{subsystem_id} has invalid dashboard_touchpoints: {', '.join(invalid_touchpoints)}"
            )

    runtime_migration_entries = list(runtime_migrations.get("migrations", []))
    runtime_migration_ids = [str(entry.get("id") or "") for entry in runtime_migration_entries]
    if len(runtime_migration_ids) != len(set(runtime_migration_ids)):
        errors.append("runtime-migration-registry.json contains duplicate migration ids")
    for entry in runtime_migration_entries:
        migration_id = str(entry.get("id") or "")
        if not migration_id:
            errors.append("runtime-migration-registry.json contains a migration without an id")
            continue
        status = str(entry.get("status") or "")
        if status not in ALLOWED_RUNTIME_MIGRATION_STATUSES:
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} has invalid status {status!r}"
            )
        runbook_path = str(entry.get("runbook_path") or "")
        if not runbook_path or not (REPO_ROOT / runbook_path).exists():
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} references missing runbook_path"
            )
        report_path = str(entry.get("generated_report_path") or "")
        if not report_path or not report_path.startswith("docs/operations/"):
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} must declare a docs/operations generated_report_path"
            )
        elif not (REPO_ROOT / report_path).exists():
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} references missing generated_report_path"
            )
        runtime_backup_root = str(entry.get("runtime_backup_root") or "")
        if not runtime_backup_root or not runtime_backup_root.startswith("/home/shaun/.athanor/backups/"):
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} must declare runtime_backup_root under /home/shaun/.athanor/backups/"
            )
        systemd_backup_target = str(entry.get("systemd_backup_target") or "")
        expected_systemd_backup_target = f"{runtime_backup_root}/athanor-governor.service" if runtime_backup_root else ""
        if systemd_backup_target != expected_systemd_backup_target:
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} must declare systemd_backup_target {expected_systemd_backup_target}"
            )
        successor_surfaces = list(entry.get("canonical_successor_surfaces", []))
        if not successor_surfaces:
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} is missing canonical_successor_surfaces"
            )
        acceptance_criteria = list(entry.get("acceptance_criteria", []))
        if not acceptance_criteria:
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} is missing acceptance_criteria"
            )
        maintenance_window_required = entry.get("maintenance_window_required")
        runtime_backup_root = str(entry.get("runtime_backup_root") or "").rstrip("/")
        systemd_backup_target = str(entry.get("systemd_backup_target") or "")
        if not isinstance(maintenance_window_required, bool):
            errors.append(
                f"runtime-migration-registry.json migration {migration_id} must declare boolean maintenance_window_required"
            )
        if maintenance_window_required:
            if not runtime_backup_root:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} must declare runtime_backup_root"
                )
            if not systemd_backup_target:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} must declare systemd_backup_target"
                )
            elif runtime_backup_root and not systemd_backup_target.startswith(runtime_backup_root.rstrip("/") + "/"):
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} systemd_backup_target must live under runtime_backup_root"
                )
        delete_gate = list(entry.get("delete_gate", []))
        if not delete_gate:
            errors.append(f"runtime-migration-registry.json migration {migration_id} is missing delete_gate")
        callers = list(entry.get("callers", []))
        if not callers:
            errors.append(f"runtime-migration-registry.json migration {migration_id} is missing caller mappings")
        caller_paths = [str(caller.get("path") or "") for caller in callers]
        if len(caller_paths) != len(set(caller_paths)):
            errors.append(f"runtime-migration-registry.json migration {migration_id} contains duplicate caller paths")
        sync_orders = [caller.get("sync_order") for caller in callers]
        if len(sync_orders) != len(set(sync_orders)):
            errors.append(f"runtime-migration-registry.json migration {migration_id} contains duplicate sync_order values")
        for caller in callers:
            caller_path = str(caller.get("path") or "")
            if not caller_path:
                errors.append(f"runtime-migration-registry.json migration {migration_id} has a caller without path")
                continue
            sync_order = caller.get("sync_order")
            if not isinstance(sync_order, int) or sync_order <= 0:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} must declare positive integer sync_order"
                )
            if not (REPO_ROOT / caller_path).exists():
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} does not exist in repo"
                )
            runtime_owner_path = str(caller.get("runtime_owner_path") or "")
            if not runtime_owner_path:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing runtime_owner_path"
                )
            elif not runtime_owner_path.endswith(caller_path.replace("\\", "/")):
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} runtime_owner_path must end with the caller path"
                )
            if not str(caller.get("sync_strategy") or "").strip():
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing sync_strategy"
                )
            rollback_target = str(caller.get("rollback_target") or "")
            if not rollback_target:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing rollback_target"
                )
            elif not rollback_target.endswith(caller_path.replace("\\", "/")):
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} rollback_target must end with the caller path"
                )
            elif runtime_backup_root and not rollback_target.startswith(runtime_backup_root.rstrip("/") + "/"):
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} rollback_target must live under runtime_backup_root"
                )
            if not str(caller.get("current_purpose") or "").strip():
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing current_purpose"
                )
            if not str(caller.get("canonical_replacement") or "").strip():
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing canonical_replacement"
                )
            if not list(caller.get("canonical_targets", [])):
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing canonical_targets"
                )
            replacement_paths = list(caller.get("replacement_owner_paths", []))
            if not replacement_paths:
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing replacement_owner_paths"
                )
            for replacement_path in replacement_paths:
                if not (REPO_ROOT / str(replacement_path)).exists():
                    errors.append(
                        "runtime-migration-registry.json migration "
                        f"{migration_id} caller {caller_path} references missing replacement_owner_path {replacement_path}"
                    )
            if not list(caller.get("repo_side_gates", [])):
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing repo_side_gates"
                )
            implementation_state = str(caller.get("implementation_state") or "")
            if implementation_state not in ALLOWED_RUNTIME_IMPLEMENTATION_STATES:
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} has invalid implementation_state {implementation_state!r}"
                )
            runtime_cutover_state = str(caller.get("runtime_cutover_state") or "")
            if runtime_cutover_state not in ALLOWED_RUNTIME_CUTOVER_STATES:
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} has invalid runtime_cutover_state {runtime_cutover_state!r}"
                )
            elif status == "retired" and runtime_cutover_state != "cutover_verified":
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} must declare runtime_cutover_state 'cutover_verified' once the migration is retired"
                )
            ask_first_required = caller.get("ask_first_required")
            if not isinstance(ask_first_required, bool):
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} must declare boolean ask_first_required"
                )
            runtime_owner_path = str(caller.get("runtime_owner_path") or "")
            expected_runtime_owner_path = f"/home/shaun/repos/athanor/{caller_path}"
            if runtime_owner_path != expected_runtime_owner_path:
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} must declare runtime_owner_path {expected_runtime_owner_path}"
                )
            sync_strategy = str(caller.get("sync_strategy") or "")
            if sync_strategy not in ALLOWED_RUNTIME_SYNC_STRATEGIES:
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} has invalid sync_strategy {sync_strategy!r}"
                )
            rollback_target = str(caller.get("rollback_target") or "")
            expected_rollback_target = f"{runtime_backup_root}/{caller_path}"
            if rollback_target != expected_rollback_target:
                errors.append(
                    "runtime-migration-registry.json migration "
                    f"{migration_id} caller {caller_path} must declare rollback_target {expected_rollback_target}"
                )
            if not str(caller.get("cutover_check") or "").strip():
                errors.append(
                    f"runtime-migration-registry.json migration {migration_id} caller {caller_path} is missing cutover_check"
                )
            if implementation_state == "migrated" and (REPO_ROOT / caller_path).exists():
                caller_text = (REPO_ROOT / caller_path).read_text(encoding="utf-8", errors="ignore")
                forbidden_hits = [token for token in RUNTIME_MIGRATION_MIGRATED_FORBIDDEN_TOKENS if token in caller_text]
                if forbidden_hits:
                    errors.append(
                        "runtime-migration-registry.json migration "
                        f"{migration_id} caller {caller_path} is marked migrated but still contains retired facade tokens: {', '.join(forbidden_hits)}"
                    )

    service_ids_set = set(service_ids)
    for lane in model_deployments.get("lanes", []):
        lane_id = str(lane.get("id") or "")
        if str(lane.get("service_id") or "") not in service_ids_set:
            errors.append(f"model-deployment-registry.json lane {lane_id} references unknown service id")
        if str(lane.get("node_id") or "") not in known_nodes:
            errors.append(f"model-deployment-registry.json lane {lane_id} references unknown node id")
        state_class = str(lane.get("state_class") or "")
        if state_class not in ALLOWED_MODEL_STATE_CLASSES:
            errors.append(f"model-deployment-registry.json lane {lane_id} has invalid state_class {state_class!r}")

    workload_ids = {str(entry.get("id") or "") for entry in workload_registry.get("classes", [])}
    policy_ids = {str(entry.get("id") or "") for entry in policy_registry.get("classes", [])}
    presence_ids = {str(entry.get("id") or "") for entry in presence_model.get("states", [])}
    release_tiers = {str(item) for item in release_ritual.get("tiers", [])}
    task_class_ids = {str(item) for item in dict(subscription_policy.get("task_classes") or {}).keys()}
    for mapping in routing_taxonomy.get("mappings", []):
        task_class = str(mapping.get("task_class") or "")
        if task_class not in task_class_ids:
            errors.append(f"routing-taxonomy-map.json references unknown task_class {task_class!r}")
        if str(mapping.get("workload_class") or "") not in workload_ids:
            errors.append(
                f"routing-taxonomy-map.json task_class {task_class} references unknown workload_class"
            )
        if str(mapping.get("policy_class") or "") not in policy_ids:
            errors.append(f"routing-taxonomy-map.json task_class {task_class} references unknown policy_class")
        unknown_presence = sorted({str(item) for item in mapping.get("presence_states", [])} - presence_ids)
        if unknown_presence:
            errors.append(
                f"routing-taxonomy-map.json task_class {task_class} references unknown presence states: "
                + ", ".join(unknown_presence)
            )
        unknown_tiers = sorted({str(item) for item in mapping.get("release_tiers", [])} - release_tiers)
        if unknown_tiers:
            errors.append(
                f"routing-taxonomy-map.json task_class {task_class} references unknown release tiers: "
                + ", ".join(unknown_tiers)
            )
    mapped_task_classes = {str(mapping.get("task_class") or "") for mapping in routing_taxonomy.get("mappings", [])}
    missing_task_mappings = sorted(task_class_ids - mapped_task_classes)
    if missing_task_mappings:
        errors.append(
            "routing-taxonomy-map.json is missing task_class mappings for: " + ", ".join(missing_task_mappings)
        )

    credential_surface_index = {
        str(surface.get("id") or ""): dict(surface)
        for surface in credential_surfaces.get("surfaces", [])
        if isinstance(surface, dict) and str(surface.get("id") or "").strip()
    }
    for surface in credential_surfaces.get("surfaces", []):
        surface_id = str(surface.get("id") or "")
        delivery_method = str(surface.get("delivery_method") or "")
        target_delivery_method = str(surface.get("target_delivery_method") or "")
        remediation_state = str(surface.get("remediation_state") or "")
        ask_first_required = surface.get("ask_first_required")
        if delivery_method not in ALLOWED_CREDENTIAL_DELIVERY_METHODS:
            errors.append(
                f"credential-surface-registry.json surface {surface_id} has invalid delivery_method {delivery_method!r}"
            )
        if target_delivery_method not in ALLOWED_CREDENTIAL_DELIVERY_METHODS:
            errors.append(
                "credential-surface-registry.json surface "
                f"{surface_id} has invalid target_delivery_method {target_delivery_method!r}"
            )
        if remediation_state not in ALLOWED_CREDENTIAL_REMEDIATION_STATES:
            errors.append(
                f"credential-surface-registry.json surface {surface_id} has invalid remediation_state {remediation_state!r}"
            )
        if not isinstance(ask_first_required, bool):
            errors.append(
                f"credential-surface-registry.json surface {surface_id} must declare boolean ask_first_required"
            )
        if not str(surface.get("managed_by") or "").strip():
            errors.append(f"credential-surface-registry.json surface {surface_id} is missing managed_by")
        if remediation_state in {"remediation_required", "review_required"} and not [
            str(item).strip() for item in surface.get("recommended_actions", []) if str(item).strip()
        ]:
            errors.append(
                "credential-surface-registry.json surface "
                f"{surface_id} must declare recommended_actions for active remediation states"
            )
        for env_name in surface.get("env_var_names", []):
            raw_env = str(env_name)
            if not raw_env.isupper():
                errors.append(f"credential-surface-registry.json surface {surface_id} has non-uppercase env name {raw_env!r}")
            if _looks_like_secret(raw_env) and "=" in raw_env:
                errors.append(f"credential-surface-registry.json surface {surface_id} appears to contain a secret value")

    vault_surface = next(
        (
            surface
            for surface in credential_surfaces.get("surfaces", [])
            if str(surface.get("id") or "") == "vault-litellm-container-env"
        ),
        None,
    )
    if vault_surface is None:
        errors.append("credential-surface-registry.json is missing vault-litellm-container-env")
    else:
        registry_env_names = {
            str(env_name)
            for env_name in vault_surface.get("env_var_names", [])
            if str(env_name).strip()
        }
        template_provider_envs = _parse_litellm_template_env_names() - {"LITELLM_MASTER_KEY"}
        task_env_names = _parse_vault_litellm_task_env_names()
        provider_catalog_vault_envs = {
            str(env_name)
            for provider in provider_catalog.get("providers", [])
            if str(dict(provider.get("evidence") or {}).get("kind") or "") == "vault_litellm_proxy"
            for env_name in provider.get("env_contracts", [])
            if str(env_name).strip()
        }

        missing_registry_envs = sorted(template_provider_envs - registry_env_names)
        if missing_registry_envs:
            errors.append(
                "credential-surface-registry.json vault-litellm-container-env is missing template env contracts: "
                + ", ".join(missing_registry_envs)
            )

        missing_catalog_envs = sorted(provider_catalog_vault_envs - registry_env_names)
        if missing_catalog_envs:
            errors.append(
                "credential-surface-registry.json vault-litellm-container-env is missing provider-catalog env contracts: "
                + ", ".join(missing_catalog_envs)
            )

        missing_task_envs = sorted(template_provider_envs - task_env_names)
        if missing_task_envs:
            errors.append(
                "ansible/roles/vault-litellm/tasks/main.yml is missing container env passthrough for: "
                + ", ".join(missing_task_envs)
            )

    vault_litellm_surface = credential_surface_index.get("vault-litellm-container-env")
    if not vault_litellm_surface:
        errors.append("credential-surface-registry.json is missing vault-litellm-container-env")
    else:
        vault_env_names = {
            str(item).strip()
            for item in vault_litellm_surface.get("env_var_names", [])
            if str(item).strip()
        }
        expected_vault_envs = {
            str(env_name).strip()
            for provider in provider_entries
            if str(dict(provider.get("evidence") or {}).get("kind") or "") == "vault_litellm_proxy"
            for env_name in provider.get("env_contracts", [])
            if str(env_name).strip()
        }
        missing_vault_envs = sorted(expected_vault_envs - vault_env_names)
        if missing_vault_envs:
            errors.append(
                "credential-surface-registry.json vault-litellm-container-env is missing provider env contracts: "
                + ", ".join(missing_vault_envs)
            )
        if not vault_litellm_env_audit:
            errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing")
        else:
            if str(vault_litellm_env_audit.get("surface_id") or "") != "vault-litellm-container-env":
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json surface_id must be vault-litellm-container-env"
                )
            if str(vault_litellm_env_audit.get("service_id") or "") != "litellm":
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json service_id must be litellm")
            if str(vault_litellm_env_audit.get("host") or "") != "vault":
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json host must be vault")
            if not str(vault_litellm_env_audit.get("observed_at") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing observed_at")
            if not str(vault_litellm_env_audit.get("source") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing source")
            expected_env_names = vault_litellm_env_audit.get("expected_env_names", [])
            container_present = vault_litellm_env_audit.get("container_present_env_names", [])
            container_missing = vault_litellm_env_audit.get("container_missing_env_names", [])
            host_present = vault_litellm_env_audit.get("host_shell_present_env_names", [])
            host_missing = vault_litellm_env_audit.get("host_shell_missing_env_names", [])
            container_entrypoint = vault_litellm_env_audit.get("container_entrypoint", [])
            container_args = vault_litellm_env_audit.get("container_args", [])
            boot_config_reference_files = vault_litellm_env_audit.get("boot_config_reference_files", [])
            if not isinstance(expected_env_names, list):
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json expected_env_names must be a list")
                expected_env_names = []
            if not isinstance(container_present, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json container_present_env_names must be a list"
                )
                container_present = []
            if not isinstance(container_missing, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json container_missing_env_names must be a list"
                )
                container_missing = []
            if not isinstance(host_present, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json host_shell_present_env_names must be a list"
                )
                host_present = []
            if not isinstance(host_missing, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json host_shell_missing_env_names must be a list"
                )
                host_missing = []
            if not isinstance(container_entrypoint, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json container_entrypoint must be a list"
                )
            if not isinstance(container_args, list):
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json container_args must be a list")
            if not isinstance(boot_config_reference_files, list):
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json boot_config_reference_files must be a list"
                )
            for field_name, values in (
                ("expected_env_names", expected_env_names),
                ("container_present_env_names", container_present),
                ("container_missing_env_names", container_missing),
                ("host_shell_present_env_names", host_present),
                ("host_shell_missing_env_names", host_missing),
            ):
                normalized = [str(value).strip() for value in values if str(value).strip()]
                if any(not value.isupper() for value in normalized):
                    errors.append(
                        f"reports/truth-inventory/vault-litellm-env-audit.json {field_name} must contain uppercase env names only"
                    )
                if any(_looks_like_secret(value) and "=" in value for value in normalized):
                    errors.append(
                        f"reports/truth-inventory/vault-litellm-env-audit.json {field_name} appears to contain a secret value"
                    )
            expected_env_set = {str(value).strip() for value in expected_env_names if str(value).strip()}
            if expected_env_set != vault_env_names:
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json expected_env_names must match "
                    "credential-surface-registry.json vault-litellm-container-env"
                )
            present_set = {str(value).strip() for value in container_present if str(value).strip()}
            missing_set = {str(value).strip() for value in container_missing if str(value).strip()}
            if present_set & missing_set:
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json container env present/missing sets overlap"
                )
            if (present_set | missing_set) != expected_env_set:
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json container env present/missing sets must cover expected_env_names exactly"
                )
            if str(vault_litellm_surface.get("observed_state") or "") == "partial_runtime_env_presence" and not missing_set:
                errors.append(
                    "reports/truth-inventory/vault-litellm-env-audit.json must record missing env names while vault-litellm-container-env remains partial_runtime_env_presence"
                )
            if not str(vault_litellm_env_audit.get("env_change_boundary") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing env_change_boundary")
            if not str(vault_litellm_env_audit.get("config_only_boundary") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing config_only_boundary")
            if not str(vault_litellm_env_audit.get("runtime_owner_surface") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing runtime_owner_surface")
            if not str(vault_litellm_env_audit.get("container_name") or "").strip():
                errors.append("reports/truth-inventory/vault-litellm-env-audit.json is missing container_name")

    for project in portfolio.get("projects", []):
        project_id = str(project["id"])
        project_class = str(project.get("class") or "")
        if project_class not in ALLOWED_PROJECT_CLASSES:
            errors.append(f"Project {project_id} has invalid class {project.get('class')!r}")
        workspace = REPO_ROOT / str(project.get("workspace") or "")
        if not workspace.exists():
            errors.append(f"Project {project_id} references missing workspace {workspace}")
        for doc_path in project.get("docs", []):
            relative_doc_path = str(doc_path)
            if not (REPO_ROOT / relative_doc_path).exists():
                errors.append(f"Project {project_id} references missing doc {doc_path}")
            elif relative_doc_path not in lifecycle_paths:
                errors.append(f"Project {project_id} doc is missing from docs lifecycle registry: {doc_path}")

        requirement_entry = next(
            (entry for entry in portfolio.get("classes", []) if str(entry.get("id")) == project_class),
            None,
        )
        requirements = [str(item) for item in (requirement_entry or {}).get("requirements", [])]
        for requirement in requirements:
            if requirement == "owner" and not str(project.get("owner") or "").strip():
                errors.append(f"Project {project_id} is missing required owner")
            elif requirement == "workspace" and not str(project.get("workspace") or "").strip():
                errors.append(f"Project {project_id} is missing required workspace")
            elif requirement == "docs" and not project.get("docs"):
                errors.append(f"Project {project_id} is missing required docs")
            elif requirement == "env_example":
                env_example = str(project.get("env_example") or "").strip()
                if not env_example:
                    errors.append(f"Project {project_id} is missing required env_example")
                elif not (REPO_ROOT / env_example).exists():
                    errors.append(f"Project {project_id} env_example path is missing: {env_example}")
            elif requirement == "ci":
                ci_commands = [str(item).strip() for item in project.get("ci", []) if str(item).strip()]
                if not ci_commands:
                    errors.append(f"Project {project_id} is missing required ci commands")
                ci_steps = [str(item).strip() for item in project.get("ci_workflow_steps", []) if str(item).strip()]
                if not ci_steps:
                    errors.append(f"Project {project_id} is missing required ci_workflow_steps")
                else:
                    missing_steps = [step for step in ci_steps if step not in workflow_steps]
                    if missing_steps:
                        errors.append(
                            f"Project {project_id} references missing CI workflow steps: {', '.join(missing_steps)}"
                        )
            elif requirement == "monitoring":
                monitoring = [str(item).strip() for item in project.get("monitoring", []) if str(item).strip()]
                if not monitoring:
                    errors.append(f"Project {project_id} is missing required monitoring services")
                else:
                    unknown = [item for item in monitoring if item not in service_ids]
                    if unknown:
                        errors.append(
                            f"Project {project_id} references unknown monitoring services: {', '.join(unknown)}"
                        )
            elif requirement == "acceptance_gate":
                gates = [str(item).strip() for item in project.get("acceptance_gate", []) if str(item).strip()]
                if not gates:
                    errors.append(f"Project {project_id} is missing required acceptance_gate commands")
                gate_steps = [
                    str(item).strip()
                    for item in project.get("acceptance_workflow_steps", [])
                    if str(item).strip()
                ]
                if not gate_steps:
                    errors.append(f"Project {project_id} is missing required acceptance_workflow_steps")
                else:
                    missing_steps = [step for step in gate_steps if step not in workflow_steps]
                    if missing_steps:
                        errors.append(
                            f"Project {project_id} references missing acceptance workflow steps: "
                            f"{', '.join(missing_steps)}"
                        )
            elif requirement == "explicit_status" and not str(project.get("explicit_status") or "").strip():
                errors.append(f"Project {project_id} is missing required explicit_status")
            elif requirement == "archive_note" and not str(project.get("archive_note") or "").strip():
                errors.append(f"Project {project_id} is missing required archive_note")

    for document in docs.get("documents", []):
        relative_path = str(document.get("path") or "")
        doc_path = REPO_ROOT / relative_path
        doc_class = str(document.get("class") or "")
        if doc_class not in ALLOWED_DOC_CLASSES:
            errors.append(f"Doc entry {document.get('path')!r} has invalid class {document.get('class')!r}")
        if not doc_path.exists():
            errors.append(f"Doc lifecycle entry references missing path {document.get('path')}")
            continue
        text = doc_path.read_text(encoding="utf-8") if doc_path.is_file() else ""
        if relative_path in REQUIRED_STARTUP_DOC_CONTRACT:
            errors.extend(_validate_startup_doc_contract(relative_path, text))
        if relative_path in REQUIRED_CANONICAL_DOC_HEADERS:
            if doc_class != "canonical":
                errors.append(f"Doc {relative_path} must remain canonical while header validation is enforced")
            errors.extend(
                _validate_canonical_doc_headers(
                    relative_path=relative_path,
                    text=text,
                    required_sources=REQUIRED_CANONICAL_DOC_HEADERS[relative_path]["sources"],
                    required_versions=REQUIRED_CANONICAL_DOC_HEADERS[relative_path]["versions"],
                    registry_versions=registry_versions,
                )
            )
        if doc_class == "generated":
            generator_command = GENERATED_DOC_GENERATORS.get(relative_path)
            if not generator_command:
                errors.append(f"Generated doc {relative_path} has no registered freshness generator")
                continue
            command_parts = generator_command if isinstance(generator_command, list) else [generator_command]
            generator_result = _run_generator_check(command_parts)
            if generator_result.returncode != 0:
                detail = (generator_result.stdout + generator_result.stderr).strip()
                errors.append(f"Generated doc is stale: {relative_path}{f' ({detail})' if detail else ''}")

    for path_segments in DOC_LIFECYCLE_SCAN_PATHS:
        scan_root = REPO_ROOT.joinpath(*path_segments[:-1])
        pattern = path_segments[-1]
        if not scan_root.exists():
            continue
        for path in scan_root.glob(pattern):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative not in lifecycle_paths:
                errors.append(f"Active doc is missing from docs lifecycle registry: {relative}")

    lens_ids = {str(item) for item in operating_system.get("lenses", [])}
    if lens_ids != REQUIRED_LENSES:
        missing = sorted(REQUIRED_LENSES - lens_ids)
        extra = sorted(lens_ids - REQUIRED_LENSES)
        if missing:
            errors.append(f"program-operating-system.json is missing lenses: {', '.join(missing)}")
        if extra:
            errors.append(f"program-operating-system.json has unexpected lenses: {', '.join(extra)}")

    cadence_keys = {str(key) for key in operating_system.get("cadence", {}).keys()}
    if cadence_keys != REQUIRED_CADENCE_KEYS:
        missing = sorted(REQUIRED_CADENCE_KEYS - cadence_keys)
        extra = sorted(cadence_keys - REQUIRED_CADENCE_KEYS)
        if missing:
            errors.append(f"program-operating-system.json is missing cadence keys: {', '.join(missing)}")
        if extra:
            errors.append(f"program-operating-system.json has unexpected cadence keys: {', '.join(extra)}")

    hosts = _expected_hosts(topology)
    expected_urls = {str(service["id"]): _expected_url(service, hosts) for service in topology.get("services", [])}

    scripts_cluster = _load_module("athanor_scripts_cluster_config", REPO_ROOT / "scripts" / "cluster_config.py")
    services_cluster = _load_module("athanor_services_cluster_config", REPO_ROOT / "services" / "cluster_config.py")
    agents_settings = _load_agents_settings()

    if dict(scripts_cluster.NODES) != hosts:
        errors.append("scripts/cluster_config.py does not resolve nodes from platform-topology.json")
    if dict(services_cluster.NODES) != hosts:
        errors.append("services/cluster_config.py does not resolve nodes from platform-topology.json")

    for service_id, expected in expected_urls.items():
        if scripts_cluster.get_url(service_id) != expected:
            errors.append(f"scripts/cluster_config.py URL mismatch for {service_id}")
        if services_cluster.get_url(service_id) != expected:
            errors.append(f"services/cluster_config.py URL mismatch for {service_id}")

    agent_node_fields = {
        "node1_host": "foundry",
        "node2_host": "workshop",
        "vault_host": "vault",
        "dev_host": "dev",
    }
    for field_name, node_id in agent_node_fields.items():
        if agents_settings.get(field_name) != hosts[node_id]:
            errors.append(f"projects/agents config default mismatch for {field_name}")

    agent_service_fields = {
        "litellm_url": "litellm",
        "coordinator_url": "vllm_coordinator",
        "coder_url": "vllm_coder",
        "worker_url": "vllm_worker",
        "embedding_url": "embedding",
        "reranker_url": "reranker",
        "vision_url": "vllm_vision",
        "agent_server_url": "agent_server",
        "dashboard_url": "dashboard",
        "prometheus_url": "prometheus",
        "grafana_url": "grafana",
        "qdrant_url": "qdrant",
        "redis_url": "redis",
        "neo4j_url": "neo4j_http",
        "stash_url": "stash",
        "comfyui_url": "comfyui",
        "speaches_url": "speaches",
        "gpu_orchestrator_url": "gpu_orchestrator",
        "langfuse_url": "langfuse",
        "miniflux_url": "miniflux",
        "ntfy_url": "ntfy",
    }
    for field_name, service_id in agent_service_fields.items():
        if agents_settings.get(field_name) != expected_urls[service_id]:
            errors.append(f"projects/agents config default mismatch for {field_name}")

    dashboard_role_defaults = yaml.safe_load(
        (REPO_ROOT / "ansible" / "roles" / "dashboard" / "defaults" / "main.yml").read_text(encoding="utf-8")
    ) or {}
    if dashboard_role_defaults.get("dashboard_qdrant_url") != "http://{{ vault_ip | default('192.168.1.203') }}:6333":
        errors.append("ansible/roles/dashboard/defaults/main.yml qdrant URL mismatch")

    eoq_role_defaults = yaml.safe_load(
        (REPO_ROOT / "ansible" / "roles" / "eoq" / "defaults" / "main.yml").read_text(encoding="utf-8")
    ) or {}
    if eoq_role_defaults.get("eoq_qdrant_url") != "http://{{ vault_ip | default('192.168.1.203') }}:6333":
        errors.append("ansible/roles/eoq/defaults/main.yml qdrant URL mismatch")

    agents_role_defaults = yaml.safe_load(
        (REPO_ROOT / "ansible" / "roles" / "agents" / "defaults" / "main.yml").read_text(encoding="utf-8")
    ) or {}
    if agents_role_defaults.get("agent_qdrant_url") != "http://{{ agent_vault_host }}:6333":
        errors.append("ansible/roles/agents/defaults/main.yml qdrant URL mismatch")

    dashboard_compose = yaml.safe_load(
        (REPO_ROOT / "projects" / "dashboard" / "docker-compose.yml").read_text(encoding="utf-8")
    ) or {}
    dashboard_env = (
        dashboard_compose.get("services", {})
        .get("dashboard", {})
        .get("environment", {})
    )
    if dashboard_env.get("ATHANOR_QDRANT_URL") != "${ATHANOR_QDRANT_URL:-http://192.168.1.203:6333}":
        errors.append("projects/dashboard/docker-compose.yml qdrant fallback must point at VAULT")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print(
        "Platform contract OK: "
        f"{len(node_ids)} nodes, {len(service_ids)} services, "
        f"{len(portfolio.get('projects', []))} projects, "
        f"{len(docs.get('documents', []))} doc lifecycle entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
