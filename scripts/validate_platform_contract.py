from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from layered_master_plan import validate_layered_master_plan_contract

from truth_inventory import resolve_external_path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTACK_ROOT = resolve_external_path("C:/athanor-devstack")
SCRIPTS_DIR = REPO_ROOT / "scripts"
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"
PROJECTS_DIR = REPO_ROOT / "projects"
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
DEVSTACK_LANE_REGISTRY_PATH = DEVSTACK_ROOT / "configs" / "devstack-capability-lane-registry.json"
DEVSTACK_ATLAS_SOURCE_PATH = DEVSTACK_ROOT / "reports" / "master-atlas" / "latest.json"
PROVIDER_USAGE_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"
PLANNED_SUBSCRIPTION_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "planned-subscription-evidence.json"
VAULT_LITELLM_ENV_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-litellm-env-audit.json"
VAULT_REDIS_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-redis-audit.json"
QUOTA_TRUTH_PATH = REPO_ROOT / "reports" / "truth-inventory" / "quota-truth.json"
CAPACITY_TELEMETRY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json"
ACTIVE_OVERRIDES_PATH = REPO_ROOT / "reports" / "truth-inventory" / "active-overrides.json"
ROUTING_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "routing-proof.json"
MASTER_ATLAS_DASHBOARD_FEED_PATH = REPO_ROOT / "projects" / "dashboard" / "src" / "generated" / "master-atlas.json"
TRUTH_SNAPSHOT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "latest.json"
BOOTSTRAP_SNAPSHOT_PATH = REPO_ROOT / "reports" / "bootstrap" / "latest.json"
BOOTSTRAP_COMPATIBILITY_CENSUS_PATH = REPO_ROOT / "reports" / "bootstrap" / "compatibility-retirement-census.json"
BOOTSTRAP_OPERATOR_SURFACE_CENSUS_PATH = REPO_ROOT / "reports" / "bootstrap" / "operator-surface-census.json"
BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT_PATH = REPO_ROOT / "reports" / "bootstrap" / "operator-summary-alignment.json"
BOOTSTRAP_OPERATOR_FIXTURE_PARITY_PATH = REPO_ROOT / "reports" / "bootstrap" / "operator-fixture-parity.json"
BOOTSTRAP_OPERATOR_NAV_LOCK_PATH = REPO_ROOT / "reports" / "bootstrap" / "operator-nav-lock.json"
BOOTSTRAP_DURABLE_PERSISTENCE_PACKET_PATH = REPO_ROOT / "reports" / "bootstrap" / "durable-persistence-packet.json"
BOOTSTRAP_DURABLE_RESTART_PROOF_PATH = REPO_ROOT / "reports" / "bootstrap" / "durable-restart-proof.json"
BOOTSTRAP_FOUNDRY_PROVING_PACKET_PATH = REPO_ROOT / "reports" / "bootstrap" / "foundry-proving-packet.json"
BOOTSTRAP_GOVERNANCE_DRILL_PACKETS_PATH = REPO_ROOT / "reports" / "bootstrap" / "governance-drill-packets.json"
BOOTSTRAP_TAKEOVER_PROMOTION_PACKET_PATH = REPO_ROOT / "reports" / "bootstrap" / "takeover-promotion-packet.json"
GITHUB_PORTFOLIO_SNAPSHOT_PATH = REPO_ROOT / "reports" / "reconciliation" / "github-portfolio-latest.json"
TENANT_FAMILY_AUDIT_PATH = REPO_ROOT / "reports" / "reconciliation" / "tenant-family-audit-latest.json"
FIELD_INSPECT_REPLAY_PACKET_REPORT_PATH = REPO_ROOT / "reports" / "reconciliation" / "field-inspect-operations-runtime-replay-latest.json"
RFI_HERS_DUPLICATE_EVIDENCE_PACKET_REPORT_PATH = REPO_ROOT / "reports" / "reconciliation" / "rfi-hers-duplicate-evidence-packet-latest.json"
RFI_HERS_PRIMARY_ROOT_STABILIZATION_REPORT_PATH = REPO_ROOT / "reports" / "reconciliation" / "rfi-hers-primary-root-stabilization-latest.json"
RALPH_LOOP_REPORT_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
RALPH_CONTINUITY_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "ralph-continuity-state.json"
CLAUDE_PRE_COMPACT_SAVE_HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "pre-compact-save.sh"
CLAUDE_POST_COMPACT_RELOAD_HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "post-compact-reload.sh"
CLAUDE_STOP_AUTOCOMMIT_HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "stop-autocommit.sh"
CLAUDE_SESSION_CONTINUITY_RULE_PATH = REPO_ROOT / ".claude" / "rules" / "session-continuity.md"
MCP_CONFIG_PATH = REPO_ROOT / ".mcp.json"
LITELLM_TEMPLATE_PATH = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "templates" / "litellm_config.yaml.j2"
VAULT_LITELLM_TASKS_PATH = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "tasks" / "main.yml"
VAULT_HOST_VARS_PATH = REPO_ROOT / "ansible" / "host_vars" / "vault.yml"
GENERATED_DOC_CHECK_TIMEOUT_SECONDS = 30

PROMETHEUS_INFRA_ONLY_PROBE_IDS = {
    "node1-node-exporter",
    "node2-node-exporter",
    "dev-node-exporter",
    "node1-dcgm-exporter",
    "node2-dcgm-exporter",
    "dev-dcgm-exporter",
    "gitea",
    "n8n",
}
PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS = {
    "aesthetic_scorer_api",
    "agent_server",
    "athanor_command_center",
    "comfyui",
    "embedding_api",
    "eoq",
    "foundry_coder_api",
    "foundry_coordinator_api",
    "gpu_orchestrator",
    "grafana",
    "home_assistant",
    "langfuse",
    "miniflux",
    "neo4j_browser",
    "ntfy",
    "plex",
    "prometheus",
    "prowlarr",
    "qdrant_api",
    "quality_gate",
    "radarr",
    "reranker_api",
    "sabnzbd",
    "semantic_router",
    "sonarr",
    "speaches",
    "stash",
    "subscription_burn",
    "tautulli",
    "ulrich_energy",
    "uptime_kuma",
    "vault_litellm_proxy",
    "vault_open_webui",
    "workshop_open_webui",
    "workshop_worker_api",
    "ws_pty_bridge",
}
PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS = {
    "builder_front_door",
    "desk_goose_operator_shell",
    "workshop_shadow_command_center",
}

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
ALLOWED_RECONCILIATION_SOURCE_KINDS = {
    "local_repo",
    "github_repo",
    "local_docs_stash",
    "local_reference_stash",
    "prototype_root",
    "runtime_root",
    "archive_evidence",
    "excluded",
}
ALLOWED_ECOSYSTEM_ROLES = {
    "core",
    "shared-module",
    "tenant",
    "lineage",
    "operator-tooling",
    "reference",
    "archive",
    "excluded",
}
ALLOWED_SOURCE_AUTHORITY_STATUSES = {"authoritative", "candidate", "non-authoritative", "frozen"}
ALLOWED_SOURCE_REVIEW_STATUSES = {"unreviewed", "fact-gathered", "proposed", "confirmed", "completed"}
ALLOWED_SOURCE_DEFAULT_DISPOSITIONS = {
    "import",
    "extract-shared",
    "tenant-queue",
    "lineage-only",
    "archive",
    "reject",
}
ALLOWED_FIELD_INSPECT_REPLAY_EXECUTION_POSTURES = {
    "ready_for_safe_replay",
    "ready_for_safe_runtime_only",
    "blocked_by_overlap",
}
ALLOWED_RFI_PRIMARY_ROOT_EXECUTION_POSTURES = {
    "ready_for_ordered_stabilization",
    "clean_root_no_stabilization_needed",
}
ALLOWED_SOURCE_PRESERVATION_STATUSES = {
    "authoritative-live",
    "snapshot-required",
    "snapshot-created",
    "candidate-freeze",
    "not-applicable",
    "excluded",
}
ALLOWED_SOURCE_PRIORITIES = {"critical", "high", "medium", "low"}
ALLOWED_COMPLETION_WORKSTREAM_STATUSES = {
    "planned",
    "active",
    "blocked",
    "governed-runtime",
    "continuous",
    "completed",
}
ALLOWED_COMPLETION_CHECKPOINT_STATUSES = {"planned", "active", "blocked", "completed"}
ALLOWED_PUBLICATION_SLICE_STATUSES = {
    "planned",
    "active",
    "approval_gated",
    "ready_for_checkpoint",
    "published",
}
ALLOWED_PUBLICATION_DEFERRED_DISPOSITIONS = {
    "deferred_out_of_sequence",
    "archive_or_reference",
    "tenant_surface",
    "operator_tooling",
    "runtime_follow_on",
    "audit_artifact",
}
ALLOWED_PUBLICATION_DEFERRED_EXECUTION_CLASSES = {
    "cash_now",
    "bounded_follow_on",
    "program_slice",
    "tenant_lane",
}
ALLOWED_COMPLETION_PRIORITY_LEVELS = {"critical", "high", "medium", "low"}
ALLOWED_COMPLETION_LOOP_EXECUTION_STATES = {
    "active",
    "ready_for_execution",
    "ready_for_operator_approval",
    "external_dependency_blocked",
    "steady_state_monitoring",
    "completed",
    "blocked",
    "claimed",
    "executing",
    "evidence_recorded",
    "spin_detected",
    "redirected",
    "escalated",
}
ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES = {
    "none",
    "approval_gate",
    "external_dependency",
    "stale_evidence",
    "runtime_authority",
    "human_decision",
}
ALLOWED_RALPH_CONTINUITY_STOP_STATES = {
    "none",
    "approval_required",
    "external_block",
    "proof_required",
    "destructive_ambiguity",
    "queue_exhausted",
}
DISALLOWED_REPO_ROOT_SCRATCH_PATTERNS = ("tmp_*",)
DISALLOWED_SCRIPTS_TOP_LEVEL_SCRATCH_PATTERNS = ("tmp_*",)
REQUIRED_RECONCILIATION_DOCS = {
    "docs/operations/ATHANOR-RECONCILIATION-PACKET.md",
    "docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md",
    "docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md",
    "docs/operations/ATHANOR-TENANT-QUEUE.md",
    "docs/operations/FIELD-INSPECT-OPERATIONS-RUNTIME-REPLAY-PACKET.md",
    "docs/operations/RFI-HERS-DUPLICATE-EVIDENCE-PACKET.md",
    "docs/operations/RFI-HERS-PRIMARY-ROOT-STABILIZATION-PACKET.md",
    "docs/operations/ATHANOR-RECONCILIATION-LEDGER.md",
}
REQUIRED_COMPLETION_PROGRAM_DOCS = {
    "docs/operations/ATHANOR-TOTAL-COMPLETION-PROGRAM.md",
    "docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md",
    "docs/operations/ATHANOR-RECONCILIATION-END-STATE.md",
}
REQUIRED_COMPLETION_LOOP_FAMILY_IDS = {
    "governor_scheduling",
    "evidence_refresh",
    "classification_backlog",
    "repo_safe_repair_planning",
    "governed_runtime_packets",
    "publication_freeze",
    "steady_state_maintenance",
}
REQUIRED_RECONCILIATION_SOURCE_IDS = {
    "athanor-core",
    "athanor-origin-main",
    "dev-runtime-root",
    "athanor-next",
    "reconcile-workspace",
    "local-system",
    "agentic-coding-tools-root",
    "codex-system-config",
    "docs-stash",
    "reference-stash",
}
REQUIRED_COMPLETION_WORKSTREAM_IDS = {
    "authority-and-mainline",
    "deployment-authority-reconciliation",
    "runtime-sync-and-governed-packets",
    "provider-and-secret-remediation",
    "dispatch-and-work-economy-closure",
    "graphrag-operational-hardening",
    "monitoring-and-observability-truth",
    "portfolio-and-source-reconciliation",
    "lineage-and-shared-extraction",
    "tenant-architecture-and-classification",
    "startup-docs-and-prune",
    "validation-and-publication",
    "goose-shell-boundary-evidence",
}
REQUIRED_COMPLETION_CHECKPOINT_IDS = {
    "control-surface-foundation",
    "deployment-truth-narrowing",
    "lineage-and-side-root-harvest",
    "ecosystem-classification",
    "runtime-repair-and-sync-packets",
    "final-publication-and-freeze",
}


def _validate_docs_lifecycle_registry_shape(errors: list[str], docs: dict) -> set[str]:
    documents = list(docs.get("documents", []))
    seen_paths: set[str] = set()
    duplicate_paths: set[str] = set()
    for document in documents:
        relative_path = str(document.get("path") or "").strip()
        if not relative_path:
            errors.append("docs-lifecycle-registry.json contains an entry with an empty path")
            continue
        if relative_path in seen_paths:
            duplicate_paths.add(relative_path)
        seen_paths.add(relative_path)
    if duplicate_paths:
        errors.append(
            "docs-lifecycle-registry.json contains duplicate paths: " + ", ".join(sorted(duplicate_paths))
        )
    return seen_paths


def _validate_archive_doc_metadata(errors: list[str], docs: dict) -> None:
    required_keys = {
        'layer',
        'authority_plane',
        'volatility',
        'generated',
        'validator',
        'allowed_content_class',
        'downstream_consumers',
        'deprecation_state',
        'replacement_surface',
    }
    for document in docs.get('documents', []):
        if not isinstance(document, dict):
            continue
        relative_path = str(document.get('path') or '').strip()
        if not relative_path.startswith('docs/archive/') or not relative_path.endswith('.md'):
            continue
        if str(document.get('class') or '').strip() != 'archive':
            errors.append(f"{relative_path} must keep class=archive in docs-lifecycle-registry.json")
        missing = sorted(key for key in required_keys if key not in document)
        if missing:
            errors.append(
                f"{relative_path} is missing archive lifecycle metadata: {', '.join(missing)}"
            )
            continue
        if str(document.get('layer') or '').strip() != 'archive_reference':
            errors.append(f"{relative_path} must use layer=archive_reference")
        if str(document.get('authority_plane') or '').strip() != 'adopted_system':
            errors.append(f"{relative_path} must use authority_plane=adopted_system")
        if str(document.get('volatility') or '').strip() != 'frozen_historical':
            errors.append(f"{relative_path} must use volatility=frozen_historical")
        if document.get('generated') is not False:
            errors.append(f"{relative_path} must set generated=false")
        if str(document.get('validator') or '').strip() != 'scripts/validate_platform_contract.py':
            errors.append(f"{relative_path} must validate through scripts/validate_platform_contract.py")
        if str(document.get('allowed_content_class') or '').strip() != 'archive_reference':
            errors.append(f"{relative_path} must use allowed_content_class=archive_reference")
        consumers = [str(item).strip() for item in document.get('downstream_consumers', []) if str(item).strip()]
        if not consumers:
            errors.append(f"{relative_path} must declare at least one archive downstream consumer")
        if str(document.get('deprecation_state') or '').strip() != 'superseded':
            errors.append(f"{relative_path} must use deprecation_state=superseded")
        replacement_surface = str(document.get('replacement_surface') or '').strip()
        if not replacement_surface:
            errors.append(f"{relative_path} must declare a replacement_surface")
            continue
        replacement_path = REPO_ROOT / replacement_surface
        if not replacement_path.exists():
            errors.append(f"{relative_path} replacement_surface does not exist: {replacement_surface}")


def _validate_high_risk_reference_doc_metadata(errors: list[str], docs: dict) -> None:
    docs_by_path = {
        str(document.get('path') or '').strip(): document
        for document in docs.get('documents', [])
        if isinstance(document, dict) and str(document.get('path') or '').strip()
    }
    required_docs = {
        'MEMORY.md': {
            'replacement_surface': 'STATUS.md',
            'deprecation_state': 'superseded',
        },
        'CLAUDE.md': {
            'replacement_surface': 'AGENTS.md',
            'deprecation_state': 'active',
        },
        'SESSION-LOG.md': {
            'replacement_surface': 'STATUS.md',
            'deprecation_state': 'superseded',
        },
    }
    required_keys = {
        'layer',
        'authority_plane',
        'volatility',
        'generated',
        'validator',
        'allowed_content_class',
        'downstream_consumers',
        'deprecation_state',
        'replacement_surface',
    }
    for relative_path, expected in required_docs.items():
        document = docs_by_path.get(relative_path)
        if not document:
            errors.append(f"docs-lifecycle-registry.json is missing {relative_path}")
            continue
        if str(document.get('class') or '').strip() != 'reference':
            errors.append(f"{relative_path} must keep class=reference in docs-lifecycle-registry.json")
        missing = sorted(key for key in required_keys if key not in document)
        if missing:
            errors.append(
                f"{relative_path} is missing high-risk reference metadata: {', '.join(missing)}"
            )
            continue
        if document.get('generated') is not False:
            errors.append(f"{relative_path} must set generated=false")
        if str(document.get('validator') or '').strip() != 'scripts/validate_platform_contract.py':
            errors.append(f"{relative_path} must validate through scripts/validate_platform_contract.py")
        if str(document.get('allowed_content_class') or '').strip() != 'reference_context':
            errors.append(f"{relative_path} must use allowed_content_class=reference_context")
        consumers = [str(item).strip() for item in document.get('downstream_consumers', []) if str(item).strip()]
        if not consumers:
            errors.append(f"{relative_path} must declare at least one downstream consumer")
        replacement_surface = str(document.get('replacement_surface') or '').strip()
        if replacement_surface != expected['replacement_surface']:
            errors.append(
                f"{relative_path} must use replacement_surface={expected['replacement_surface']}"
            )
        else:
            replacement_path = REPO_ROOT / replacement_surface
            if not replacement_path.exists():
                errors.append(f"{relative_path} replacement_surface does not exist: {replacement_surface}")
        if str(document.get('deprecation_state') or '').strip() != expected['deprecation_state']:
            errors.append(
                f"{relative_path} must use deprecation_state={expected['deprecation_state']}"
            )



def _validate_operator_helper_surfaces(errors: list[str]) -> None:
    pre_compact_text = CLAUDE_PRE_COMPACT_SAVE_HOOK_PATH.read_text(encoding='utf-8')
    if 'Reference-Only Compaction Handoff' not in pre_compact_text:
        errors.append('.claude/hooks/pre-compact-save.sh must save a reference-only compaction handoff')
    if 'reports/ralph-loop/latest.json' not in pre_compact_text or 'reports/truth-inventory/ralph-continuity-state.json' not in pre_compact_text:
        errors.append('.claude/hooks/pre-compact-save.sh must point at live Ralph continuity surfaces')
    if 'Infrastructure (quick check)' in pre_compact_text or 'ssh -o ConnectTimeout=2' in pre_compact_text:
        errors.append('.claude/hooks/pre-compact-save.sh must not snapshot ad hoc infrastructure state into the handoff')

    post_compact_text = CLAUDE_POST_COMPACT_RELOAD_HOOK_PATH.read_text(encoding='utf-8')
    if 'Treat .claude/.session-state.md as a hint only, not authority' not in post_compact_text:
        errors.append('.claude/hooks/post-compact-reload.sh must mark the saved session state as non-authoritative')
    if 'reports/truth-inventory/governed-dispatch-state.json' not in post_compact_text:
        errors.append('.claude/hooks/post-compact-reload.sh must refresh governed dispatch truth after compaction')
    if 'Continue where you left off' in post_compact_text:
        errors.append('.claude/hooks/post-compact-reload.sh must not tell the operator to continue blindly from stale state')

    stop_autocommit_text = CLAUDE_STOP_AUTOCOMMIT_HOOK_PATH.read_text(encoding='utf-8')
    if 'ATHANOR_ENABLE_STOP_AUTOCOMMIT' not in stop_autocommit_text:
        errors.append('.claude/hooks/stop-autocommit.sh must stay opt-in via ATHANOR_ENABLE_STOP_AUTOCOMMIT')
    if 'disabled by default' not in stop_autocommit_text:
        errors.append('.claude/hooks/stop-autocommit.sh must explicitly state that auto-commit is disabled by default')

    session_continuity_text = CLAUDE_SESSION_CONTINUITY_RULE_PATH.read_text(encoding='utf-8')
    if 'git push' in session_continuity_text or 'git commit -m "status: update"' in session_continuity_text:
        errors.append('.claude/rules/session-continuity.md must not require automatic commit or push at every stop')
    if 'live runtime truth' not in session_continuity_text:
        errors.append('.claude/rules/session-continuity.md must state that live runtime truth outranks narrative docs')

    try:
        mcp_config = json.loads(MCP_CONFIG_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        errors.append(f'.mcp.json is not valid JSON: {exc}')
        return
    athanor_agents = dict(dict(mcp_config.get('mcpServers') or {}).get('athanor-agents') or {})
    athanor_agent_env = dict(athanor_agents.get('env') or {})
    token_binding = str(athanor_agent_env.get('ATHANOR_AGENT_API_TOKEN') or '').strip()
    if token_binding != 'os.environ/ATHANOR_AGENT_API_TOKEN':
        errors.append('.mcp.json must source ATHANOR_AGENT_API_TOKEN from os.environ/ATHANOR_AGENT_API_TOKEN')

def _validate_repo_structure_contract(errors: list[str]) -> None:
    for pattern in DISALLOWED_REPO_ROOT_SCRATCH_PATTERNS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                errors.append(
                    "Repo root contains scratch file outside tmp/: "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )
    for pattern in DISALLOWED_SCRIPTS_TOP_LEVEL_SCRATCH_PATTERNS:
        for path in SCRIPTS_DIR.glob(pattern):
            if path.is_file():
                errors.append(
                    "scripts/ contains scratch-style top-level file: "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )
REQUIRED_PUBLICATION_SLICE_IDS = [
    "backbone-contracts-and-truth-writers",
    "runtime-ownership-provider-truth-and-reconciliation",
    "pilot-eval-substrate-and-operator-test-machinery",
    "graphrag-promotion-wave",
    "gpu-scheduler-extension-wave",
    "forge-atlas-dashboard-and-startup-truth",
]
REQUIRED_RECONCILIATION_END_STATE_GATE_IDS = {
    "authority_gate",
    "current_state_truth_gate",
    "runtime_gate",
    "provider_gate",
    "portfolio_gate",
    "product_gate",
    "validation_gate",
    "steady_state_gate",
}
REQUIRED_RECONCILIATION_SUCCESS_LEVEL_IDS = {
    "hard_closure",
    "operational_success",
    "steady_state_transition",
}
ALLOWED_RECONCILIATION_END_STATE_STATUSES = {"active_remediation", "steady_state_monitoring"}
ALLOWED_RECONCILIATION_END_STATE_GATE_STATUSES = {
    "active",
    "ready_for_operator_approval",
    "external_dependency_blocked",
    "steady_state_monitoring",
    "completed",
}
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
    "docs/operations/RUNTIME-OWNERSHIP-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "runtime_ownership",
    ],
    "docs/operations/RUNTIME-OWNERSHIP-PACKETS.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "runtime_ownership_packets",
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
    "docs/operations/VAULT-REDIS-REPAIR-PACKET.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "vault_redis_repair_packet",
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
    "docs/operations/STEADY-STATE-STATUS.md": [
        "scripts/write_steady_state_status.py",
    ],
    "docs/operations/SURFACE-OWNER-MATRIX.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "surface_owner_matrix",
    ],
    "docs/operations/PUBLICATION-PROVENANCE-REPORT.md": [
        "scripts/generate_truth_inventory_reports.py",
        "--report",
        "publication_provenance",
    ],
    "docs/operations/PUBLICATION-TRIAGE-REPORT.md": [
        "scripts/triage_publication_tranche.py",
        "--write",
        "docs/operations/PUBLICATION-TRIAGE-REPORT.md",
    ],
    "docs/operations/PUBLICATION-DEFERRED-FAMILY-QUEUE.md": [
        "scripts/generate_publication_deferred_family_queue.py",
    ],
    "docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md": [
        "scripts/generate_full_system_audit.py",
    ],
    "docs/operations/DEVSTACK-MEMBRANE-AUDIT.md": [
        "scripts/generate_full_system_audit.py",
    ],
    "docs/operations/AUDIT-REMEDIATION-BACKLOG.md": [
        "scripts/generate_full_system_audit.py",
    ],
    "docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md": [
        "scripts/generate_ecosystem_master_plan.py",
    ],
    "docs/operations/ATHANOR-ECOSYSTEM-DEPENDENCY-MAP.md": [
        "scripts/generate_ecosystem_master_plan.py",
    ],
    "docs/operations/ATHANOR-OPERATOR-MODEL.md": [
        "scripts/generate_ecosystem_master_plan.py",
    ],
    "docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md": [
        "scripts/generate_ecosystem_master_plan.py",
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
ALLOWED_PROVIDER_EVIDENCE_KINDS = {"cli_subscription", "coding_tool_subscription", "vault_litellm_proxy"}
ALLOWED_PROVIDER_CLI_PROBE_STATUSES = {"installed", "missing", "degraded", "mixed"}
ALLOWED_PROVIDER_TOOLING_PROBE_STATUSES = {"supported_tools_present", "supported_tools_missing", "degraded", "mixed"}
ALLOWED_PROVIDER_BILLING_STATUSES = {
    "verified",
    "operator_visible_tier_unverified",
    "published_tiers_known_subscribed_tier_unverified",
}
ALLOWED_PROVIDER_INTEGRATION_STATUSES = {"verified", "unverified", "degraded"}
ALLOWED_PROVIDER_SPECIFIC_USAGE_STATUSES = {"pending", "observed", "verified", "not_supported", "auth_failed", "request_failed"}
ALLOWED_PROVIDER_USAGE_CAPTURE_STATUSES = {"observed", "verified", "not_supported", "auth_failed", "request_failed"}
ALLOWED_PLANNED_SUBSCRIPTION_CAPTURE_STATUSES = {
    "tooling_present",
    "tooling_ready",
    "supported_tool_usage_observed",
    "missing_tooling",
    "activation_blocked",
}
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
    "build-system",
    "operator-local",
    "incubation",
    "vestigial",
    "archive",
}
REQUIRED_CAPABILITY_AUTHORITY_CLASSES = {
    "adopted_system",
    "build_system",
    "operator_local",
    "archive_evidence",
}
REQUIRED_CAPABILITY_STAGE_IDS = {
    "concept",
    "prototype",
    "proved",
    "adopted",
    "retired",
}
REQUIRED_MASTER_ATLAS_CONTRACT_IDS = {
    "readiness_ledger",
    "wave_admissibility_record",
    "eval_run_ledger",
    "artifact_provenance_record",
    "economic_dispatch_ledger",
    "capacity_envelope",
    "restore_ledger",
    "governance_confidence_record",
    "recommendation_record",
    "lane_selection_matrix",
    "approval_matrix",
    "failure_routing_matrix",
    "artifact_topology_registry",
    "capacity_telemetry_contract",
    "vendor_policy_registry",
    "migration_map",
    "quota_truth_ledger",
    "capacity_telemetry_snapshot",
    "active_override_record",
    "routing_proof_record",
}
ALLOWED_EVAL_INITIATIVE_KINDS = {"capability_promotion", "lane_evaluation"}
ALLOWED_EVAL_LEDGER_STATUSES = {"seeded", "active", "live"}
ALLOWED_EVAL_RUN_STATUSES = {"planned", "evidence_only", "active", "completed"}
ALLOWED_PROMOTION_VALIDITY_STATES = {"requires_formal_eval_run", "valid", "stale", "superseded"}
ALLOWED_PROVENANCE_LEDGER_STATUSES = {"seeded", "active", "live"}
ALLOWED_ECONOMIC_DISPATCH_STATUSES = {"seeded", "active", "live"}
ALLOWED_CAPACITY_ENVELOPE_STATUSES = {"seeded", "active", "live"}
ALLOWED_RESTORE_LEDGER_STATUSES = {"seeded", "active", "live"}
ALLOWED_GOVERNANCE_CONFIDENCE_STATUSES = {"healthy", "warning", "blocked"}
ALLOWED_PROJECT_ROUTING_CLASSES = {
    "sovereign_only",
    "private_but_cloud_allowed",
    "cloud_safe",
    "public_product_only",
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
ALLOWED_RUNTIME_OWNERSHIP_LANE_STATUSES = {"active", "recovery_only", "planned", "retired"}
ALLOWED_RUNTIME_OWNERSHIP_DEPLOYMENT_MODES = {
        "repo_worktree_systemd",
        "repo_worktree_mirror",
    "repo_worktree_script",
    "opt_compose_service",
    "opt_systemd_service",
    "host_state_surface",
    "vault_host_state",
}
ALLOWED_RUNTIME_OWNERSHIP_CRITERION_STATUSES = {"met", "open", "planned"}
ALLOWED_RUNTIME_OWNERSHIP_PACKET_STATUSES = {
    "ready_for_approval",
    "approved_pending_execution",
    "executed",
    "retired",
}
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
            "config/automation-backbone/runtime-ownership-contract.json",
            "config/automation-backbone/runtime-ownership-packets.json",
            "docs/RECOVERY.md",
            "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
            "docs/operations/RUNTIME-OWNERSHIP-PACKETS.md",
        ],
        "versions": [
            "platform-topology.json",
            "runtime-ownership-contract.json",
            "runtime-ownership-packets.json",
            "program-operating-system.json",
        ],
    },
    "docs/runbooks/runtime-ownership-contract.md": {
        "sources": [
            "config/automation-backbone/runtime-ownership-contract.json",
            "config/automation-backbone/runtime-ownership-packets.json",
            "config/automation-backbone/repo-roots-registry.json",
            "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
            "docs/operations/RUNTIME-OWNERSHIP-PACKETS.md",
        ],
        "versions": [
            "runtime-ownership-contract.json",
            "runtime-ownership-packets.json",
            "repo-roots-registry.json",
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
    "docs/operations/ATHANOR-TOTAL-COMPLETION-PROGRAM.md": {
        "sources": [
            "config/automation-backbone/completion-program-registry.json",
            "config/automation-backbone/program-operating-system.json",
            "docs/operations/ATHANOR-RECONCILIATION-END-STATE.md",
            "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
            "docs/operations/ATHANOR-RECONCILIATION-PACKET.md",
            "docs/operations/RUNTIME-OWNERSHIP-PACKETS.md",
        ],
        "versions": [
            "completion-program-registry.json",
            "program-operating-system.json",
        ],
    },
    "docs/operations/ATHANOR-RECONCILIATION-END-STATE.md": {
        "sources": [
            "config/automation-backbone/completion-program-registry.json",
            "reports/ralph-loop/latest.json",
            "STATUS.md",
            "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
            "docs/operations/ATHANOR-OPERATING-SYSTEM.md",
        ],
        "versions": [
            "completion-program-registry.json",
        ],
    },
}


def _clean_markdown_cell(value: str) -> str:
    return re.sub(r"`([^`]+)`", r"\1", value).strip()


def _parse_ecosystem_registry_rows(markdown_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_batch: str | None = None
    table_headers: list[str] | None = None

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## Batch "):
            current_batch = line.removeprefix("## ").strip()
            table_headers = None
            continue
        if not line.startswith("|"):
            table_headers = None
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "Repo":
            table_headers = cells
            continue
        if all(set(cell) <= {"-", " "} for cell in cells):
            continue
        if not current_batch or not table_headers or len(cells) != len(table_headers):
            continue

        row = {header: _clean_markdown_cell(value) for header, value in zip(table_headers, cells)}
        repo_value = row.get("Repo", "")
        if not repo_value.startswith("Dirty13itch/"):
            continue
        row["Batch"] = current_batch
        row["github_repo"] = repo_value
        row["ecosystem_role"] = row.get("Proposed role", "")
        row["working_clone"] = row.get("Working clone", "")
        row["likely_tenant_status"] = row.get("Likely tenant status", "")
        row["shaun_decision"] = row.get("Shaun decision", "")
        rows.append(row)

    return rows


def _load_json(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _is_parseable_iso_datetime(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _resolve_declared_path(raw: Any) -> Path:
    text = str(raw or "").strip()
    return resolve_external_path(text, base=REPO_ROOT)


def _validate_bootstrap_zero_ambiguity_contracts(
    *,
    errors: list[str],
    bootstrap_programs: dict[str, Any],
    bootstrap_takeover: dict[str, Any],
    bootstrap_slice_catalog: dict[str, Any],
    bootstrap_execution_policy: dict[str, Any],
    foundry_proving: dict[str, Any],
    governance_drills: dict[str, Any],
    approval_packets: dict[str, Any],
    operator_runbooks: dict[str, Any],
    project_packets: dict[str, Any],
    latest_bootstrap_snapshot: dict[str, Any],
    operator_surface_census: dict[str, Any],
    operator_summary_alignment: dict[str, Any],
    operator_fixture_parity: dict[str, Any],
    operator_nav_lock: dict[str, Any],
    durable_persistence_packet: dict[str, Any],
    foundry_proving_packet: dict[str, Any],
    governance_drill_packets: dict[str, Any],
    takeover_promotion_packet: dict[str, Any],
) -> None:
    family_ids = {
        str(item.get("id") or "").strip()
        for item in bootstrap_programs.get("families", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    slice_catalog_family_ids = {
        str(item.get("id") or "").strip()
        for item in bootstrap_slice_catalog.get("families", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if family_ids != slice_catalog_family_ids:
        errors.append(
            "bootstrap-slice-catalog.json families must match bootstrap-program-registry.json families exactly"
        )

    required_slice_fields = {
        "id",
        "family",
        "order",
        "objective",
        "write_scope",
        "read_scope",
        "phase_scope",
        "host_mode",
        "mutates_repo",
        "mutates_runtime",
        "approval_class",
        "validator_bundle",
        "integration_priority",
        "retry_class",
        "blocker_class",
        "completion_evidence",
        "next_on_success",
        "next_on_block",
    }
    allowed_host_modes = {"report_only", "code_mutation", "validation_only", "governed_packet"}
    allowed_approval_classes = {
        "none",
        "approval_packet",
        "runtime_mutation_blocked",
        "promotion_explicit",
    }
    family_slice_counts = {family_id: 0 for family_id in family_ids}
    for entry in bootstrap_slice_catalog.get("slices", []):
        if not isinstance(entry, dict):
            errors.append("bootstrap-slice-catalog.json slices entries must be objects")
            continue
        missing_fields = sorted(required_slice_fields - set(entry.keys()))
        if missing_fields:
            errors.append(
                "bootstrap-slice-catalog.json slice "
                f"{entry.get('id')!r} is missing fields: {', '.join(missing_fields)}"
            )
        slice_id = str(entry.get("id") or "").strip()
        family = str(entry.get("family") or "").strip()
        if not slice_id:
            errors.append("bootstrap-slice-catalog.json contains a slice without id")
        if family not in family_ids:
            errors.append(
                f"bootstrap-slice-catalog.json slice {slice_id or '<unknown>'} references unknown family {family!r}"
            )
        else:
            family_slice_counts[family] += 1
        if entry.get("host_mode") not in allowed_host_modes:
            errors.append(
                f"bootstrap-slice-catalog.json slice {slice_id or '<unknown>'} has invalid host_mode {entry.get('host_mode')!r}"
            )
        if entry.get("approval_class") not in allowed_approval_classes:
            errors.append(
                f"bootstrap-slice-catalog.json slice {slice_id or '<unknown>'} has invalid approval_class {entry.get('approval_class')!r}"
            )
        for field_name in (
            "write_scope",
            "read_scope",
            "validator_bundle",
            "completion_evidence",
            "next_on_success",
            "next_on_block",
        ):
            if not isinstance(entry.get(field_name), list):
                errors.append(
                    f"bootstrap-slice-catalog.json slice {slice_id or '<unknown>'} field {field_name} must be a list"
                )
    for family_id, count in family_slice_counts.items():
        if count == 0:
            errors.append(f"bootstrap-slice-catalog.json must define at least one slice for family {family_id}")

    worktree = dict(bootstrap_execution_policy.get("worktree") or {})
    branch_patterns = dict(worktree.get("branch_name_patterns") or {})
    if str(worktree.get("root_path_pattern") or "").strip() != "C:\\Athanor_worktrees\\{family}\\{slice_id}":
        errors.append("bootstrap-execution-policy.json worktree.root_path_pattern must be C:\\Athanor_worktrees\\{family}\\{slice_id}")
    for host_id in ("codex_external", "claude_external"):
        if host_id not in branch_patterns:
            errors.append(
                f"bootstrap-execution-policy.json worktree.branch_name_patterns is missing {host_id}"
            )
    integration = dict(bootstrap_execution_policy.get("integration") or {})
    if str(integration.get("target_ref") or "").strip() != "main":
        errors.append("bootstrap-execution-policy.json integration.target_ref must be 'main'")
    if integration.get("allow_merge_commits") is not False:
        errors.append("bootstrap-execution-policy.json integration.allow_merge_commits must be false")

    project_packet_ids = {
        str(item.get("id") or "").strip()
        for item in project_packets.get("projects", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if str(foundry_proving.get("project_id") or "").strip() != "athanor":
        errors.append("foundry-proving-registry.json project_id must be 'athanor'")
    if str(foundry_proving.get("project_id") or "").strip() not in project_packet_ids:
        errors.append("foundry-proving-registry.json project_id must exist in project-packet-registry.json")
    if not [str(item).strip() for item in foundry_proving.get("validator_bundle", []) if str(item).strip()]:
        errors.append("foundry-proving-registry.json validator_bundle must be non-empty")
    if bool(dict(foundry_proving.get("promotion_gate") or {}).get("allow_direct_ad_hoc_bypass")):
        errors.append("foundry-proving-registry.json promotion_gate.allow_direct_ad_hoc_bypass must be false")

    runbook_ids = {
        str(item.get("id") or "").strip()
        for item in operator_runbooks.get("runbooks", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    drill_ids: set[str] = set()
    for drill in governance_drills.get("drills", []):
        if not isinstance(drill, dict):
            errors.append("governance-drill-registry.json drills entries must be objects")
            continue
        drill_id = str(drill.get("drill_id") or "").strip()
        if not drill_id:
            errors.append("governance-drill-registry.json contains a drill without drill_id")
            continue
        if drill_id in drill_ids:
            errors.append(f"governance-drill-registry.json drill_id {drill_id!r} is duplicated")
        drill_ids.add(drill_id)
        runbook_id = str(drill.get("runbook_id") or "").strip()
        if runbook_id not in runbook_ids:
            errors.append(
                f"governance-drill-registry.json drill {drill_id} references unknown runbook_id {runbook_id!r}"
            )
        if not isinstance(drill.get("evidence_artifacts"), list) or not drill.get("evidence_artifacts"):
            errors.append(
                f"governance-drill-registry.json drill {drill_id} must declare evidence_artifacts"
            )
        if not str(drill.get("health_effect") or "").strip():
            errors.append(f"governance-drill-registry.json drill {drill_id} is missing health_effect")
        if not str(drill.get("dashboard_effect") or "").strip():
            errors.append(f"governance-drill-registry.json drill {drill_id} is missing dashboard_effect")
        if not isinstance(drill.get("pass_criteria"), list) or not drill.get("pass_criteria"):
            errors.append(f"governance-drill-registry.json drill {drill_id} must declare pass_criteria")

    required_packets = {
        "db_schema_change",
        "vault_provider_auth_repair",
        "systemd_runtime_change",
        "destructive_branch_cleanup",
        "runtime_host_reconfiguration",
    }
    packet_ids = {
        str(item.get("id") or "").strip()
        for item in approval_packets.get("packet_types", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if packet_ids != required_packets:
        errors.append("approval-packet-registry.json packet_types must match the required ask-first packet ids exactly")
    for packet in approval_packets.get("packet_types", []):
        if not isinstance(packet, dict):
            errors.append("approval-packet-registry.json packet_types entries must be objects")
            continue
        packet_id = str(packet.get("id") or "").strip()
        for field_name in ("boundary", "approval_authority"):
            if not str(packet.get(field_name) or "").strip():
                errors.append(f"approval-packet-registry.json packet {packet_id or '<unknown>'} is missing {field_name}")
        for field_name in ("evidence_required", "exact_steps", "rollback_steps"):
            if not isinstance(packet.get(field_name), list) or not packet.get(field_name):
                errors.append(
                    f"approval-packet-registry.json packet {packet_id or '<unknown>'} must declare non-empty {field_name}"
                )

    active_bootstrap_program = any(
        str(item.get("status") or "").strip() in {"active", "ready_for_takeover_check", "takeover_promoted"}
        for item in bootstrap_programs.get("programs", [])
        if isinstance(item, dict)
    )
    required_bootstrap_artifacts = {
        "reports/bootstrap/compatibility-retirement-census.json": BOOTSTRAP_COMPATIBILITY_CENSUS_PATH,
        "reports/bootstrap/operator-surface-census.json": BOOTSTRAP_OPERATOR_SURFACE_CENSUS_PATH,
        "reports/bootstrap/operator-summary-alignment.json": BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT_PATH,
        "reports/bootstrap/operator-fixture-parity.json": BOOTSTRAP_OPERATOR_FIXTURE_PARITY_PATH,
        "reports/bootstrap/operator-nav-lock.json": BOOTSTRAP_OPERATOR_NAV_LOCK_PATH,
        "reports/bootstrap/durable-persistence-packet.json": BOOTSTRAP_DURABLE_PERSISTENCE_PACKET_PATH,
        "reports/bootstrap/foundry-proving-packet.json": BOOTSTRAP_FOUNDRY_PROVING_PACKET_PATH,
        "reports/bootstrap/governance-drill-packets.json": BOOTSTRAP_GOVERNANCE_DRILL_PACKETS_PATH,
        "reports/bootstrap/takeover-promotion-packet.json": BOOTSTRAP_TAKEOVER_PROMOTION_PACKET_PATH,
    }
    if active_bootstrap_program and not BOOTSTRAP_SNAPSHOT_PATH.exists():
        errors.append("reports/bootstrap/latest.json is required while a bootstrap program is active")
    if active_bootstrap_program:
        for label, path in required_bootstrap_artifacts.items():
            if not path.exists():
                errors.append(f"{label} is required while a bootstrap program is active")
    if BOOTSTRAP_SNAPSHOT_PATH.exists():
        if not latest_bootstrap_snapshot:
            errors.append("reports/bootstrap/latest.json must contain valid JSON")
        else:
            if not str(latest_bootstrap_snapshot.get("generated_at") or "").strip():
                errors.append("reports/bootstrap/latest.json is missing generated_at")
            if not isinstance(latest_bootstrap_snapshot.get("status"), dict):
                errors.append("reports/bootstrap/latest.json must contain a status object")
            else:
                status = dict(latest_bootstrap_snapshot.get("status") or {})
                if not isinstance(status.get("takeover"), dict):
                    errors.append("reports/bootstrap/latest.json status.takeover must be an object")
                if not isinstance(status.get("registry_snapshot"), dict):
                    errors.append("reports/bootstrap/latest.json status.registry_snapshot must be an object")
                if not isinstance(status.get("control_artifacts"), dict):
                    errors.append("reports/bootstrap/latest.json status.control_artifacts must be an object")
    if BOOTSTRAP_OPERATOR_SURFACE_CENSUS_PATH.exists():
        if not operator_surface_census:
            errors.append("reports/bootstrap/operator-surface-census.json must contain valid JSON")
        else:
            if "first_class_drift_count" not in operator_surface_census:
                errors.append("reports/bootstrap/operator-surface-census.json first_class_drift_count is required")
            if "canonical_hit_count" not in operator_surface_census:
                errors.append("reports/bootstrap/operator-surface-census.json canonical_hit_count is required")
            if "complete" not in operator_surface_census:
                errors.append("reports/bootstrap/operator-surface-census.json complete is required")
    if BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT_PATH.exists():
        if not operator_summary_alignment:
            errors.append("reports/bootstrap/operator-summary-alignment.json must contain valid JSON")
        else:
            if "drift_count" not in operator_summary_alignment:
                errors.append("reports/bootstrap/operator-summary-alignment.json drift_count is required")
            if "missing_canonical_hit_count" not in operator_summary_alignment:
                errors.append("reports/bootstrap/operator-summary-alignment.json missing_canonical_hit_count is required")
            if "complete" not in operator_summary_alignment:
                errors.append("reports/bootstrap/operator-summary-alignment.json complete is required")
    if BOOTSTRAP_OPERATOR_FIXTURE_PARITY_PATH.exists():
        if not operator_fixture_parity:
            errors.append("reports/bootstrap/operator-fixture-parity.json must contain valid JSON")
        else:
            if "missing_file_count" not in operator_fixture_parity:
                errors.append("reports/bootstrap/operator-fixture-parity.json missing_file_count is required")
            if "missing_pattern_count" not in operator_fixture_parity:
                errors.append("reports/bootstrap/operator-fixture-parity.json missing_pattern_count is required")
            if "complete" not in operator_fixture_parity:
                errors.append("reports/bootstrap/operator-fixture-parity.json complete is required")
    if BOOTSTRAP_OPERATOR_NAV_LOCK_PATH.exists():
        if not operator_nav_lock:
            errors.append("reports/bootstrap/operator-nav-lock.json must contain valid JSON")
        else:
            if "missing_file_count" not in operator_nav_lock:
                errors.append("reports/bootstrap/operator-nav-lock.json missing_file_count is required")
            if "missing_pattern_count" not in operator_nav_lock:
                errors.append("reports/bootstrap/operator-nav-lock.json missing_pattern_count is required")
            if "forbidden_pattern_count" not in operator_nav_lock:
                errors.append("reports/bootstrap/operator-nav-lock.json forbidden_pattern_count is required")
            if "complete" not in operator_nav_lock:
                errors.append("reports/bootstrap/operator-nav-lock.json complete is required")
    if BOOTSTRAP_DURABLE_PERSISTENCE_PACKET_PATH.exists():
        if not durable_persistence_packet:
            errors.append("reports/bootstrap/durable-persistence-packet.json must contain valid JSON")
        else:
            contract = dict(durable_persistence_packet.get("contract") or {})
            env_contract = dict(contract.get("env_contract") or {})
            runtime_dependency_packet = dict(durable_persistence_packet.get("runtime_dependency_packet") or {})
            schema_authority = dict(durable_persistence_packet.get("schema_authority") or {})
            approval_packet = dict(durable_persistence_packet.get("approval_packet") or {})
            restart_proof = dict(durable_persistence_packet.get("restart_proof") or {})
            if str(env_contract.get("name") or "").strip() != "ATHANOR_POSTGRES_URL":
                errors.append(
                    "reports/bootstrap/durable-persistence-packet.json contract.env_contract.name must be ATHANOR_POSTGRES_URL"
                )
            required_packages = {
                "langgraph-checkpoint-postgres>=3.0.5",
                "psycopg[binary]>=3.2",
            }
            packet_packages = {str(item).strip() for item in runtime_dependency_packet.get("required_packages", [])}
            if not required_packages.issubset(packet_packages):
                errors.append(
                    "reports/bootstrap/durable-persistence-packet.json runtime_dependency_packet.required_packages is incomplete"
                )
            if str(runtime_dependency_packet.get("env_var") or "").strip() != "ATHANOR_POSTGRES_URL":
                errors.append(
                    "reports/bootstrap/durable-persistence-packet.json runtime_dependency_packet.env_var must be ATHANOR_POSTGRES_URL"
                )
            if not str(schema_authority.get("checkpoint_setup_authority") or "").strip():
                errors.append(
                    "reports/bootstrap/durable-persistence-packet.json schema_authority.checkpoint_setup_authority is required"
                )
            if not isinstance(schema_authority.get("migration_order"), list) or not schema_authority.get("migration_order"):
                errors.append(
                    "reports/bootstrap/durable-persistence-packet.json schema_authority.migration_order must be non-empty"
                )
            if str(approval_packet.get("id") or "").strip() != "db_schema_change":
                errors.append("reports/bootstrap/durable-persistence-packet.json approval_packet.id must be db_schema_change")
            if not isinstance(restart_proof.get("steps"), list) or not restart_proof.get("steps"):
                errors.append("reports/bootstrap/durable-persistence-packet.json restart_proof.steps must be non-empty")
            if not str(restart_proof.get("artifact_path") or "").strip():
                errors.append("reports/bootstrap/durable-persistence-packet.json restart_proof.artifact_path is required")
            if bool(dict(durable_persistence_packet.get("criterion_status") or {}).get("restart_proof_passed")) and not BOOTSTRAP_DURABLE_RESTART_PROOF_PATH.exists():
                errors.append(
                    "reports/bootstrap/durable-restart-proof.json is required when durable-persistence restart proof is marked passed"
                )
    if BOOTSTRAP_DURABLE_RESTART_PROOF_PATH.exists():
        try:
            durable_restart_proof = json.loads(BOOTSTRAP_DURABLE_RESTART_PROOF_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("reports/bootstrap/durable-restart-proof.json must contain valid JSON")
        else:
            if not isinstance(durable_restart_proof, dict):
                errors.append("reports/bootstrap/durable-restart-proof.json must contain an object payload")
            else:
                if not str(durable_restart_proof.get("proof_id") or "").strip():
                    errors.append("reports/bootstrap/durable-restart-proof.json proof_id is required")
                if not str(durable_restart_proof.get("phase") or "").strip():
                    errors.append("reports/bootstrap/durable-restart-proof.json phase is required")
                if "passed" not in durable_restart_proof:
                    errors.append("reports/bootstrap/durable-restart-proof.json passed is required")
                if not str(durable_restart_proof.get("artifact_path") or "").strip():
                    errors.append("reports/bootstrap/durable-restart-proof.json artifact_path is required")
                if durable_restart_proof.get("phase") == "verified":
                    post_restart = durable_restart_proof.get("post_restart") or {}
                    if not isinstance(post_restart, dict):
                        errors.append("reports/bootstrap/durable-restart-proof.json post_restart must be an object after verification")
                    elif "effect_marker_count" not in post_restart:
                        errors.append("reports/bootstrap/durable-restart-proof.json post_restart.effect_marker_count is required after verification")
    if BOOTSTRAP_FOUNDRY_PROVING_PACKET_PATH.exists():
        if not foundry_proving_packet:
            errors.append("reports/bootstrap/foundry-proving-packet.json must contain valid JSON")
        else:
            first_slice_packet = dict(foundry_proving_packet.get("first_proving_slice_packet") or {})
            promotion_gate = dict(foundry_proving_packet.get("promotion_gate") or {})
            if str(foundry_proving_packet.get("project_id") or "").strip() != "athanor":
                errors.append("reports/bootstrap/foundry-proving-packet.json project_id must be athanor")
            if not str(foundry_proving_packet.get("project_packet_ref") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json project_packet_ref is required")
            if not str(foundry_proving_packet.get("architecture_packet_ref") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json architecture_packet_ref is required")
            if not str(foundry_proving_packet.get("first_proving_slice_id") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json first_proving_slice_id is required")
            if not str(first_slice_packet.get("owner_agent") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json first_proving_slice_packet.owner_agent is required")
            if not str(first_slice_packet.get("lane") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json first_proving_slice_packet.lane is required")
            if not str(first_slice_packet.get("objective") or "").strip():
                errors.append("reports/bootstrap/foundry-proving-packet.json first_proving_slice_packet.objective is required")
            if not isinstance(foundry_proving_packet.get("acceptance_evidence_requirements"), list) or not foundry_proving_packet.get("acceptance_evidence_requirements"):
                errors.append("reports/bootstrap/foundry-proving-packet.json acceptance_evidence_requirements must be non-empty")
            if not isinstance(foundry_proving_packet.get("candidate_evidence_requirements"), list) or not foundry_proving_packet.get("candidate_evidence_requirements"):
                errors.append("reports/bootstrap/foundry-proving-packet.json candidate_evidence_requirements must be non-empty")
            if not isinstance(foundry_proving_packet.get("rollback_target_requirements"), list) or not foundry_proving_packet.get("rollback_target_requirements"):
                errors.append("reports/bootstrap/foundry-proving-packet.json rollback_target_requirements must be non-empty")
            if not isinstance(foundry_proving_packet.get("validator_bundle"), list) or not foundry_proving_packet.get("validator_bundle"):
                errors.append("reports/bootstrap/foundry-proving-packet.json validator_bundle must be non-empty")
            if not bool(promotion_gate.get("require_foundry_run")):
                errors.append("reports/bootstrap/foundry-proving-packet.json promotion_gate.require_foundry_run must be true")
            if not bool(promotion_gate.get("require_candidate")):
                errors.append("reports/bootstrap/foundry-proving-packet.json promotion_gate.require_candidate must be true")
            if not bool(promotion_gate.get("require_rollback_target")):
                errors.append("reports/bootstrap/foundry-proving-packet.json promotion_gate.require_rollback_target must be true")
            if not bool(promotion_gate.get("require_acceptance_evidence")):
                errors.append("reports/bootstrap/foundry-proving-packet.json promotion_gate.require_acceptance_evidence must be true")
            if bool(promotion_gate.get("allow_direct_ad_hoc_bypass")):
                errors.append("reports/bootstrap/foundry-proving-packet.json promotion_gate.allow_direct_ad_hoc_bypass must be false")
            if "ready" not in foundry_proving_packet:
                errors.append("reports/bootstrap/foundry-proving-packet.json ready is required")
    if BOOTSTRAP_GOVERNANCE_DRILL_PACKETS_PATH.exists():
        if not governance_drill_packets:
            errors.append("reports/bootstrap/governance-drill-packets.json must contain valid JSON")
        else:
            if not str(governance_drill_packets.get("evidence_root") or "").strip():
                errors.append("reports/bootstrap/governance-drill-packets.json evidence_root is required")
            if not isinstance(governance_drill_packets.get("drills"), list) or not governance_drill_packets.get("drills"):
                errors.append("reports/bootstrap/governance-drill-packets.json drills must be non-empty")
    if BOOTSTRAP_TAKEOVER_PROMOTION_PACKET_PATH.exists():
        if not takeover_promotion_packet:
            errors.append("reports/bootstrap/takeover-promotion-packet.json must contain valid JSON")
        else:
            if str(takeover_promotion_packet.get("promotion_rule") or "").strip() != "explicit_promotion_only":
                errors.append(
                    "reports/bootstrap/takeover-promotion-packet.json promotion_rule must be explicit_promotion_only"
                )
            if not isinstance(takeover_promotion_packet.get("criteria"), list) or not takeover_promotion_packet.get("criteria"):
                errors.append("reports/bootstrap/takeover-promotion-packet.json criteria must be non-empty")
            if not isinstance(takeover_promotion_packet.get("authority_flip_steps"), list) or not takeover_promotion_packet.get("authority_flip_steps"):
                errors.append("reports/bootstrap/takeover-promotion-packet.json authority_flip_steps must be non-empty")


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


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _run_generator_check(command_parts: list[str]) -> subprocess.CompletedProcess[str]:
    script_path = REPO_ROOT / command_parts[0]
    try:
        return subprocess.run(
            [sys.executable, str(script_path), *command_parts[1:], "--check"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=GENERATED_DOC_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        detail = (
            f"Generated doc freshness check timed out after {GENERATED_DOC_CHECK_TIMEOUT_SECONDS}s: "
            + " ".join(command_parts)
        )
        return subprocess.CompletedProcess(
            args=exc.cmd,
            returncode=124,
            stdout=(exc.stdout or ""),
            stderr=((exc.stderr or "") + detail).strip(),
        )


def _parse_registry_generator_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if parts and parts[0] in {"python", "python3", Path(sys.executable).name, sys.executable}:
        parts = parts[1:]
    return parts


def _normalize_generated_doc_path(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("./")


def _parse_ignored_generated_doc_args(argv: list[str]) -> tuple[set[str], list[str]]:
    ignored: set[str] = set()
    remaining: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--ignore-generated-doc":
            if index + 1 >= len(argv):
                raise ValueError("--ignore-generated-doc requires a relative doc path")
            ignored.add(_normalize_generated_doc_path(argv[index + 1]))
            index += 2
            continue
        remaining.append(token)
        index += 1
    return ignored, remaining


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


def _validate_devstack_convergence_boundaries(
    *,
    errors: list[str],
    master_atlas_dashboard_feed: dict[str, Any],
) -> None:
    if not DEVSTACK_LANE_REGISTRY_PATH.exists():
        errors.append(f"Devstack lane registry is missing: {DEVSTACK_LANE_REGISTRY_PATH.as_posix()}")
        return

    devstack_lane_registry = _load_optional_json(DEVSTACK_LANE_REGISTRY_PATH)
    devstack_lane_tokens: set[str] = set()
    for lane in devstack_lane_registry.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        for raw_token in (
            str(lane.get("id") or "").strip(),
            str(lane.get("title") or "").strip(),
            str(lane.get("name") or "").strip(),
        ):
            if raw_token:
                devstack_lane_tokens.add(raw_token.lower())

    startup_docs = {
        "STATUS.md": REPO_ROOT / "STATUS.md",
        "docs/operations/ATHANOR-OPERATING-SYSTEM.md": REPO_ROOT / "docs" / "operations" / "ATHANOR-OPERATING-SYSTEM.md",
        "docs/operations/ATHANOR-COLD-START.md": REPO_ROOT / "docs" / "operations" / "ATHANOR-COLD-START.md",
    }
    for relative_path, path in startup_docs.items():
        if not path.exists():
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for token in sorted(devstack_lane_tokens, key=len, reverse=True):
            if token and token in lowered:
                errors.append(
                    f"{relative_path} must not duplicate devstack volatile lane state token {token!r}; point readers to devstack board/atlas instead"
                )
                break

    status_text = (REPO_ROOT / "STATUS.md").read_text(encoding="utf-8")
    for required in (
        "C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md",
        "C:/athanor-devstack/reports/master-atlas/latest.json",
    ):
        if required not in status_text:
            errors.append(f"STATUS.md must point readers to {required}")

    operating_system_text = (REPO_ROOT / "docs" / "operations" / "ATHANOR-OPERATING-SYSTEM.md").read_text(encoding="utf-8")
    for required in (
        "projects/dashboard/src/generated/master-atlas.json",
        "C:/athanor-devstack/reports/master-atlas/latest.json",
        "downstream consumer",
    ):
        if required not in operating_system_text:
            errors.append(f"docs/operations/ATHANOR-OPERATING-SYSTEM.md must contain {required!r}")

    if not DEVSTACK_ATLAS_SOURCE_PATH.exists():
        errors.append(f"Devstack atlas source is missing: {DEVSTACK_ATLAS_SOURCE_PATH.as_posix()}")
        return
    devstack_atlas_source = _load_optional_json(DEVSTACK_ATLAS_SOURCE_PATH)
    if not devstack_atlas_source:
        errors.append(f"Devstack atlas source must contain valid JSON: {DEVSTACK_ATLAS_SOURCE_PATH.as_posix()}")
        return
    if master_atlas_dashboard_feed != devstack_atlas_source:
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json must match C:/athanor-devstack/reports/master-atlas/latest.json exactly"
        )


def _validate_vault_prometheus_probe_contract(
    *,
    errors: list[str],
    operator_surfaces: dict[str, Any],
    vault_host_vars: dict[str, Any],
) -> None:
    surface_entries = {
        str(entry.get("id") or "").strip(): dict(entry)
        for entry in operator_surfaces.get("surfaces", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    classified_surface_ids = (
        PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS | PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS
    )
    missing_classifications = sorted(set(surface_entries) - classified_surface_ids)
    if missing_classifications:
        errors.append(
            "operator-surface-registry.json has unclassified Prometheus parity surface ids: "
            + ", ".join(missing_classifications)
        )

    unknown_expected = sorted(PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS - set(surface_entries))
    if unknown_expected:
        errors.append(
            "validate_platform_contract.py PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS references unknown surfaces: "
            + ", ".join(unknown_expected)
        )
    unknown_excluded = sorted(PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS - set(surface_entries))
    if unknown_excluded:
        errors.append(
            "validate_platform_contract.py PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS references unknown surfaces: "
            + ", ".join(unknown_excluded)
        )

    probe_targets = [
        dict(target)
        for target in vault_host_vars.get("prometheus_probe_targets", [])
        if isinstance(target, dict)
    ]
    probe_ids = [str(target.get("id") or "").strip() for target in probe_targets if str(target.get("id") or "").strip()]
    duplicate_probe_ids = [probe_id for probe_id, count in Counter(probe_ids).items() if count > 1]
    if duplicate_probe_ids:
        errors.append(
            "ansible/host_vars/vault.yml contains duplicate prometheus_probe_targets ids: "
            + ", ".join(sorted(duplicate_probe_ids))
        )

    canonical_probe_ids: set[str] = set()
    for target in probe_targets:
        probe_id = str(target.get("id") or "").strip()
        if not probe_id:
            errors.append("ansible/host_vars/vault.yml contains a prometheus_probe_targets entry without id")
            continue
        if probe_id in surface_entries:
            canonical_probe_ids.add(probe_id)
            surface = surface_entries[probe_id]
            expected_label = str(surface.get("label") or "").strip()
            if str(target.get("name") or "").strip() != expected_label:
                errors.append(
                    "ansible/host_vars/vault.yml prometheus_probe_targets "
                    f"{probe_id} must use canonical label {expected_label!r}"
                )
            expected_node = str(surface.get("node") or "").strip()
            if str(target.get("node_id") or "").strip() != expected_node:
                errors.append(
                    "ansible/host_vars/vault.yml prometheus_probe_targets "
                    f"{probe_id} must use canonical node_id {expected_node!r}"
                )
            continue
        if probe_id not in PROMETHEUS_INFRA_ONLY_PROBE_IDS:
            errors.append(
                "ansible/host_vars/vault.yml prometheus_probe_targets "
                f"{probe_id} is neither a canonical operator surface id nor an infra-only allowlisted probe"
            )

    missing_expected_ids = sorted(PROMETHEUS_EXPECTED_OPERATOR_SURFACE_IDS - canonical_probe_ids)
    if missing_expected_ids:
        errors.append(
            "ansible/host_vars/vault.yml is missing canonical Prometheus probe targets for: "
            + ", ".join(missing_expected_ids)
        )

    unexpected_excluded_ids = sorted(canonical_probe_ids & PROMETHEUS_EXCLUDED_OPERATOR_SURFACE_IDS)
    if unexpected_excluded_ids:
        errors.append(
            "ansible/host_vars/vault.yml should not probe excluded operator surfaces: "
            + ", ".join(unexpected_excluded_ids)
        )


def _validate_capability_adoption_registry(
    *,
    errors: list[str],
    capability_adoption: dict[str, Any],
    contract_registry: dict[str, Any],
    repo_roots: dict[str, Any],
    runtime_ownership: dict[str, Any],
    runtime_ownership_packets: dict[str, Any],
) -> None:
    if str(capability_adoption.get("source_of_truth") or "") != "config/automation-backbone/capability-adoption-registry.json":
        errors.append(
            "capability-adoption-registry.json source_of_truth must be config/automation-backbone/capability-adoption-registry.json"
        )
    if str(capability_adoption.get("status") or "") != "active":
        errors.append("capability-adoption-registry.json status must be active")

    contract_ids = {
        str(item.get("id") or "").strip()
        for item in contract_registry.get("contracts", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if "promotion_packet" not in contract_ids:
        errors.append("contract-registry.json must declare the promotion_packet contract")
    if str(capability_adoption.get("promotion_contract") or "").strip() != "promotion_packet":
        errors.append("capability-adoption-registry.json promotion_contract must be promotion_packet")

    authority_class_ids = {
        str(item.get("id") or "").strip()
        for item in capability_adoption.get("authority_classes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if authority_class_ids != REQUIRED_CAPABILITY_AUTHORITY_CLASSES:
        errors.append("capability-adoption-registry.json authority_classes must match the required authority-class set")

    stage_ids = {
        str(item.get("id") or "").strip()
        for item in capability_adoption.get("capability_stages", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if stage_ids != REQUIRED_CAPABILITY_STAGE_IDS:
        errors.append("capability-adoption-registry.json capability_stages must match the required stage set")

    repo_root_by_path = {
        str(entry.get("path") or "").strip(): dict(entry)
        for entry in repo_roots.get("roots", [])
        if isinstance(entry, dict) and str(entry.get("path") or "").strip()
    }
    runtime_lane_ids = {
        str(item.get("id") or "").strip()
        for item in runtime_ownership.get("lanes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    runtime_packet_ids = {
        str(item.get("id") or "").strip()
        for item in runtime_ownership_packets.get("packets", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    capabilities = [
        dict(entry)
        for entry in capability_adoption.get("capabilities", [])
        if isinstance(entry, dict)
    ]
    if not capabilities:
        errors.append("capability-adoption-registry.json must declare at least one capability")
        return

    seen_ids: set[str] = set()
    required_scalar_fields = (
        "id",
        "label",
        "owner",
        "source_repo",
        "stage",
        "authority_class",
        "runtime_target",
        "promotion_packet_id",
        "rollback_or_disable_path",
        "archive_instructions",
    )
    required_list_fields = (
        "source_artifacts",
        "proof_artifacts",
        "acceptance_criteria",
        "athanor_target_surfaces",
    )

    for entry in capabilities:
        capability_id = str(entry.get("id") or "").strip()
        if not capability_id:
            errors.append("capability-adoption-registry.json contains a capability without id")
            continue
        if capability_id in seen_ids:
            errors.append(f"capability-adoption-registry.json capability id {capability_id!r} is duplicated")
        seen_ids.add(capability_id)

        for field_name in required_scalar_fields:
            if not str(entry.get(field_name) or "").strip():
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} is missing {field_name}"
                )
        for field_name in required_list_fields:
            if not isinstance(entry.get(field_name), list) or not entry.get(field_name):
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} must declare non-empty {field_name}"
                )

        runtime_rollout_state = str(entry.get("runtime_rollout_state") or "").strip()
        requires_runtime_linkage = runtime_rollout_state != "not_linked"
        for field_name in ("runtime_ownership_lanes", "runtime_packet_ids"):
            field_value = entry.get(field_name)
            if not isinstance(field_value, list):
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} {field_name} must be a list"
                )
                continue
            if requires_runtime_linkage and not field_value:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} must declare non-empty {field_name}"
                )

        stage = str(entry.get("stage") or "").strip()
        authority_class = str(entry.get("authority_class") or "").strip()
        if stage not in REQUIRED_CAPABILITY_STAGE_IDS:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} has invalid stage {stage!r}"
            )
        if authority_class not in REQUIRED_CAPABILITY_AUTHORITY_CLASSES:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} has invalid authority_class {authority_class!r}"
            )
        if authority_class == "adopted_system" and stage not in {"adopted", "retired"}:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} cannot use adopted_system authority while stage is {stage!r}"
            )

        source_repo = str(entry.get("source_repo") or "").strip()
        source_root = repo_root_by_path.get(source_repo)
        if not source_root:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} references unknown source_repo {source_repo!r}"
            )
        elif source_repo == "C:/athanor-devstack" and str(source_root.get("authority_level") or "") != "build-system":
            errors.append(
                "capability-adoption-registry.json requires C:/athanor-devstack to be registered as authority_level build-system"
            )

        packet_id = str(entry.get("promotion_packet_id") or "").strip()
        runtime_rollout_state = str(entry.get("runtime_rollout_state") or "").strip()
        if stage in {"adopted", "retired"} and packet_id.startswith("pending"):
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} must not use a pending promotion_packet_id once stage is {stage!r}"
            )

        lane_values = [str(item).strip() for item in entry.get("runtime_ownership_lanes", []) if str(item).strip()]
        packet_values = [str(item).strip() for item in entry.get("runtime_packet_ids", []) if str(item).strip()]
        requires_runtime_linkage = runtime_rollout_state != "not_linked"
        if stage in {"adopted", "retired"}:
            if requires_runtime_linkage and not lane_values:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} must declare runtime_ownership_lanes once stage is {stage!r}"
                )
            if requires_runtime_linkage and not packet_values:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} must declare runtime_packet_ids once stage is {stage!r}"
                )
        for lane_id in lane_values:
            if lane_id != "pending" and lane_id not in runtime_lane_ids:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} references unknown runtime_ownership_lane {lane_id!r}"
                )
        for runtime_packet_id in packet_values:
            if runtime_packet_id != "pending" and runtime_packet_id not in runtime_packet_ids:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} references unknown runtime_packet_id {runtime_packet_id!r}"
                )


def _validate_capability_adoption_boundary_fields(
    *,
    errors: list[str],
    capability_adoption: dict[str, Any],
    domain_packets: dict[str, Any],
    memory_namespaces: dict[str, Any],
) -> None:
    allowed_release_tiers = {"offline_eval", "shadow", "canary", "production", "retired"}
    allowed_runtime_rollout_states = {"", "not_linked", "shadow_live", "canary_live", "primary_live", "retired"}
    domain_ids = {
        str(item.get("id") or "").strip()
        for item in domain_packets.get("domains", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    namespace_ids = {
        str(item.get("id") or "").strip()
        for item in memory_namespaces.get("namespaces", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    for entry in capability_adoption.get("capabilities", []):
        if not isinstance(entry, dict):
            continue
        capability_id = str(entry.get("id") or "").strip() or "<missing>"
        if not str(entry.get("source_lane_id") or "").strip():
            errors.append(f"capability-adoption-registry.json capability {capability_id} is missing source_lane_id")
        if not str(entry.get("source_packet_id") or "").strip():
            errors.append(f"capability-adoption-registry.json capability {capability_id} is missing source_packet_id")
        if not str(entry.get("landing_project") or "").strip():
            errors.append(f"capability-adoption-registry.json capability {capability_id} is missing landing_project")

        release_tier = str(entry.get("release_tier") or "").strip()
        if release_tier not in allowed_release_tiers:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} has invalid release_tier {release_tier!r}"
            )

        runtime_rollout_state = str(entry.get("runtime_rollout_state") or "").strip()
        if runtime_rollout_state not in allowed_runtime_rollout_states:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} has invalid runtime_rollout_state {runtime_rollout_state!r}"
            )

        affected_domains = entry.get("affected_domains")
        if not isinstance(affected_domains, list) or not affected_domains:
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} must declare non-empty affected_domains"
            )
        else:
            unknown_domains = [str(item).strip() for item in affected_domains if str(item).strip() not in domain_ids]
            if unknown_domains:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} references unknown affected_domains: {', '.join(sorted(unknown_domains))}"
                )

        affected_namespaces = entry.get("affected_namespaces")
        if not isinstance(affected_namespaces, list):
            errors.append(
                f"capability-adoption-registry.json capability {capability_id} affected_namespaces must be a list"
            )
        else:
            unknown_namespaces = [str(item).strip() for item in affected_namespaces if str(item).strip() not in namespace_ids]
            if unknown_namespaces:
                errors.append(
                    f"capability-adoption-registry.json capability {capability_id} references unknown affected_namespaces: {', '.join(sorted(unknown_namespaces))}"
                )


def _validate_master_atlas_contracts(
    *,
    errors: list[str],
    contract_registry: dict[str, Any],
    capability_adoption: dict[str, Any],
    policy_registry: dict[str, Any],
    topology: dict[str, Any],
    coding_lanes: dict[str, Any],
    eval_run_ledger: dict[str, Any],
    artifact_provenance: dict[str, Any],
    economic_dispatch: dict[str, Any],
    capacity_envelope: dict[str, Any],
    restore_ledger: dict[str, Any],
    backup_restore_readiness: dict[str, Any],
    master_atlas_dashboard_feed: dict[str, Any],
    lane_selection_matrix: dict[str, Any],
    approval_matrix: dict[str, Any],
    failure_routing_matrix: dict[str, Any],
    subscription_burn_registry: dict[str, Any],
) -> None:
    contract_ids = {
        str(item.get("id") or "").strip()
        for item in contract_registry.get("contracts", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    missing_contract_ids = sorted(REQUIRED_MASTER_ATLAS_CONTRACT_IDS - contract_ids)
    if missing_contract_ids:
        errors.append(
            "contract-registry.json is missing required master-atlas contracts: "
            + ", ".join(missing_contract_ids)
        )

    capability_ids = {
        str(item.get("id") or "").strip()
        for item in capability_adoption.get("capabilities", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    policy_ids = {
        str(item.get("id") or "").strip()
        for item in policy_registry.get("classes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    coding_lane_ids = {
        str(item.get("id") or "").strip()
        for item in coding_lanes.get("lanes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    topology_node_ids = {
        str(item.get("id") or "").strip()
        for item in topology.get("nodes", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    backup_store_by_id = {
        str(item.get("id") or "").strip(): dict(item)
        for item in backup_restore_readiness.get("critical_stores", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    if str(eval_run_ledger.get("source_of_truth") or "").strip() != "config/automation-backbone/eval-run-ledger.json":
        errors.append("eval-run-ledger.json source_of_truth must be config/automation-backbone/eval-run-ledger.json")
    if str(eval_run_ledger.get("status") or "").strip() not in ALLOWED_EVAL_LEDGER_STATUSES:
        errors.append("eval-run-ledger.json has invalid status")
    eval_runs = [
        dict(item)
        for item in eval_run_ledger.get("runs", [])
        if isinstance(item, dict)
    ]
    if not eval_runs:
        errors.append("eval-run-ledger.json must declare at least one run")
    eval_run_ids: set[str] = set()
    for run in eval_runs:
        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            errors.append("eval-run-ledger.json contains a run without run_id")
            continue
        if run_id in eval_run_ids:
            errors.append(f"eval-run-ledger.json run_id {run_id!r} is duplicated")
        eval_run_ids.add(run_id)
        initiative_kind = str(run.get("initiative_kind") or "").strip()
        if initiative_kind not in ALLOWED_EVAL_INITIATIVE_KINDS:
            errors.append(f"eval-run-ledger.json run {run_id} has invalid initiative_kind {run.get('initiative_kind')!r}")
        initiative_id = str(run.get("initiative_id") or "").strip()
        if initiative_kind == "lane_evaluation":
            if initiative_id not in coding_lane_ids:
                errors.append(
                    f"eval-run-ledger.json run {run_id} references unknown lane initiative_id {initiative_id!r}"
                )
            if not str(run.get("task_class") or "").strip():
                errors.append(f"eval-run-ledger.json lane evaluation run {run_id} must declare task_class")
            if not str(run.get("wrapper_mode") or "").strip():
                errors.append(f"eval-run-ledger.json lane evaluation run {run_id} must declare wrapper_mode")
        elif initiative_id not in capability_ids:
            errors.append(
                f"eval-run-ledger.json run {run_id} references unknown initiative_id {initiative_id!r}"
            )
        packet_path = _resolve_declared_path(run.get("linked_promotion_packet"))
        if not packet_path.exists():
            errors.append(f"eval-run-ledger.json run {run_id} linked_promotion_packet is missing: {packet_path}")
        judge_config = dict(run.get("judge_config") or {})
        policy_class = str(judge_config.get("policy_class") or "").strip()
        if policy_class not in policy_ids:
            errors.append(
                f"eval-run-ledger.json run {run_id} references unknown judge_config.policy_class {policy_class!r}"
            )
        if not isinstance(judge_config.get("evaluation_dimensions"), list) or not judge_config.get("evaluation_dimensions"):
            errors.append(f"eval-run-ledger.json run {run_id} must declare judge_config.evaluation_dimensions")
        if not isinstance(run.get("evidence_artifacts"), list) or not run.get("evidence_artifacts"):
            errors.append(f"eval-run-ledger.json run {run_id} must declare evidence_artifacts")
        else:
            for artifact in run["evidence_artifacts"]:
                artifact_path = _resolve_declared_path(artifact)
                if not artifact_path.exists():
                    errors.append(f"eval-run-ledger.json run {run_id} references missing evidence artifact {artifact_path}")
        freshness_window_days = run.get("freshness_window_days")
        if not isinstance(freshness_window_days, int) or freshness_window_days <= 0:
            errors.append(f"eval-run-ledger.json run {run_id} freshness_window_days must be a positive integer")
        last_run_at = run.get("last_run_at")
        if last_run_at is not None and not _is_parseable_iso_datetime(last_run_at):
            errors.append(f"eval-run-ledger.json run {run_id} has invalid last_run_at {last_run_at!r}")
        if str(run.get("status") or "").strip() not in ALLOWED_EVAL_RUN_STATUSES:
            errors.append(f"eval-run-ledger.json run {run_id} has invalid status {run.get('status')!r}")
        if str(run.get("promotion_validity") or "").strip() not in ALLOWED_PROMOTION_VALIDITY_STATES:
            errors.append(
                f"eval-run-ledger.json run {run_id} has invalid promotion_validity {run.get('promotion_validity')!r}"
            )

    if str(artifact_provenance.get("source_of_truth") or "").strip() != "config/automation-backbone/artifact-provenance-ledger.json":
        errors.append(
            "artifact-provenance-ledger.json source_of_truth must be config/automation-backbone/artifact-provenance-ledger.json"
        )
    if str(artifact_provenance.get("status") or "").strip() not in ALLOWED_PROVENANCE_LEDGER_STATUSES:
        errors.append("artifact-provenance-ledger.json has invalid status")
    provenance_records = [
        dict(item)
        for item in artifact_provenance.get("records", [])
        if isinstance(item, dict)
    ]
    if not provenance_records:
        errors.append("artifact-provenance-ledger.json must declare at least one provenance record")
    provenance_ids: set[str] = set()
    for record in provenance_records:
        provenance_id = str(record.get("provenance_id") or "").strip()
        if not provenance_id:
            errors.append("artifact-provenance-ledger.json contains a record without provenance_id")
            continue
        if provenance_id in provenance_ids:
            errors.append(f"artifact-provenance-ledger.json provenance_id {provenance_id!r} is duplicated")
        provenance_ids.add(provenance_id)
        artifact_path = _resolve_declared_path(record.get("artifact_path"))
        if not artifact_path.exists():
            errors.append(f"artifact-provenance-ledger.json record {provenance_id} artifact_path is missing: {artifact_path}")
        produced_by = dict(record.get("produced_by") or {})
        for field_name in ("system", "workflow", "node"):
            if not str(produced_by.get(field_name) or "").strip():
                errors.append(f"artifact-provenance-ledger.json record {provenance_id} is missing produced_by.{field_name}")
        inputs = dict(record.get("inputs") or {})
        for list_field in ("source_artifacts", "policy_artifacts", "lane_ids", "judge_record_ids"):
            if not isinstance(inputs.get(list_field), list):
                errors.append(f"artifact-provenance-ledger.json record {provenance_id} must declare list {list_field}")
        for evaluation_ref in record.get("evaluation_refs", []) or []:
            if str(evaluation_ref).strip() not in eval_run_ids:
                errors.append(
                    f"artifact-provenance-ledger.json record {provenance_id} references unknown evaluation_ref {evaluation_ref!r}"
                )
        if not _is_parseable_iso_datetime(record.get("last_verified_at")):
            errors.append(f"artifact-provenance-ledger.json record {provenance_id} is missing a valid last_verified_at")

    if str(economic_dispatch.get("source_of_truth") or "").strip() != "config/automation-backbone/economic-dispatch-ledger.json":
        errors.append(
            "economic-dispatch-ledger.json source_of_truth must be config/automation-backbone/economic-dispatch-ledger.json"
        )
    if str(economic_dispatch.get("status") or "").strip() not in ALLOWED_ECONOMIC_DISPATCH_STATUSES:
        errors.append("economic-dispatch-ledger.json has invalid status")
    economic_lanes = [
        dict(item)
        for item in economic_dispatch.get("lanes", [])
        if isinstance(item, dict)
    ]
    if not economic_lanes:
        errors.append("economic-dispatch-ledger.json must declare at least one lane")
    economic_lane_ids: set[str] = set()
    for lane in economic_lanes:
        lane_id = str(lane.get("lane_id") or "").strip()
        if not lane_id:
            errors.append("economic-dispatch-ledger.json contains a lane without lane_id")
            continue
        if lane_id in economic_lane_ids:
            errors.append(f"economic-dispatch-ledger.json lane_id {lane_id!r} is duplicated")
        economic_lane_ids.add(lane_id)
        if lane_id not in coding_lane_ids:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} is missing from coding-lane-registry.json")
        if not str(lane.get("provider_id") or "").strip():
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} is missing provider_id")
        max_parallel_slots = lane.get("max_parallel_slots")
        reserved_parallel_slots = lane.get("reserved_parallel_slots")
        harvestable_parallel_slots = lane.get("harvestable_parallel_slots")
        if not isinstance(max_parallel_slots, int) or max_parallel_slots < 0:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} max_parallel_slots must be a non-negative integer")
            continue
        if not isinstance(reserved_parallel_slots, int) or reserved_parallel_slots < 0:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} reserved_parallel_slots must be a non-negative integer")
        if not isinstance(harvestable_parallel_slots, int) or harvestable_parallel_slots < 0:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} harvestable_parallel_slots must be a non-negative integer")
        if isinstance(reserved_parallel_slots, int) and reserved_parallel_slots > max_parallel_slots:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} reserved_parallel_slots exceeds max_parallel_slots")
        if isinstance(harvestable_parallel_slots, int) and harvestable_parallel_slots > max_parallel_slots:
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} harvestable_parallel_slots exceeds max_parallel_slots")
        if (
            isinstance(reserved_parallel_slots, int)
            and isinstance(harvestable_parallel_slots, int)
            and reserved_parallel_slots + harvestable_parallel_slots > max_parallel_slots
        ):
            errors.append(
                f"economic-dispatch-ledger.json lane {lane_id} reserved_parallel_slots + harvestable_parallel_slots exceeds max_parallel_slots"
            )
        if not _is_parseable_iso_datetime(lane.get("last_verified_at")):
            errors.append(f"economic-dispatch-ledger.json lane {lane_id} is missing a valid last_verified_at")
    if economic_lane_ids != coding_lane_ids:
        missing = sorted(coding_lane_ids - economic_lane_ids)
        extra = sorted(economic_lane_ids - coding_lane_ids)
        if missing:
            errors.append("economic-dispatch-ledger.json is missing coding lanes: " + ", ".join(missing))
        if extra:
            errors.append("economic-dispatch-ledger.json has unexpected lanes: " + ", ".join(extra))

    if str(capacity_envelope.get("source_of_truth") or "").strip() != "config/automation-backbone/capacity-envelope-registry.json":
        errors.append(
            "capacity-envelope-registry.json source_of_truth must be config/automation-backbone/capacity-envelope-registry.json"
        )
    if str(capacity_envelope.get("status") or "").strip() not in ALLOWED_CAPACITY_ENVELOPE_STATUSES:
        errors.append("capacity-envelope-registry.json has invalid status")
    capacity_nodes = [
        dict(item)
        for item in capacity_envelope.get("nodes", [])
        if isinstance(item, dict)
    ]
    if not capacity_nodes:
        errors.append("capacity-envelope-registry.json must declare at least one node")
    capacity_node_ids: set[str] = set()
    for node in capacity_nodes:
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            errors.append("capacity-envelope-registry.json contains a node without node_id")
            continue
        if node_id in capacity_node_ids:
            errors.append(f"capacity-envelope-registry.json node_id {node_id!r} is duplicated")
        capacity_node_ids.add(node_id)
        if node_id not in topology_node_ids:
            errors.append(f"capacity-envelope-registry.json references unknown topology node {node_id!r}")
        gpus = [dict(item) for item in node.get("gpus", []) if isinstance(item, dict)]
        if not gpus:
            errors.append(f"capacity-envelope-registry.json node {node_id} must declare gpus")
            continue
        interactive_reserve = node.get("interactive_reserve_gpu_slots")
        background_fill = node.get("background_fill_gpu_slots")
        if not isinstance(interactive_reserve, int) or interactive_reserve < 0:
            errors.append(f"capacity-envelope-registry.json node {node_id} interactive_reserve_gpu_slots must be a non-negative integer")
        if not isinstance(background_fill, int) or background_fill < 0:
            errors.append(f"capacity-envelope-registry.json node {node_id} background_fill_gpu_slots must be a non-negative integer")
        if (
            isinstance(interactive_reserve, int)
            and isinstance(background_fill, int)
            and interactive_reserve + background_fill > len(gpus)
        ):
            errors.append(
                f"capacity-envelope-registry.json node {node_id} reserve plus background fill exceeds declared GPU count"
            )
        telemetry = dict(node.get("observed_telemetry") or {})
        if not _is_parseable_iso_datetime(telemetry.get("last_verified_at")):
            errors.append(f"capacity-envelope-registry.json node {node_id} is missing a valid observed_telemetry.last_verified_at")
        gpu_ids: set[str] = set()
        for gpu in gpus:
            gpu_id = str(gpu.get("gpu_id") or "").strip()
            if not gpu_id:
                errors.append(f"capacity-envelope-registry.json node {node_id} contains a GPU without gpu_id")
                continue
            if gpu_id in gpu_ids:
                errors.append(f"capacity-envelope-registry.json node {node_id} duplicates gpu_id {gpu_id!r}")
            gpu_ids.add(gpu_id)
            if not str(gpu.get("owner_lane") or "").strip():
                errors.append(f"capacity-envelope-registry.json node {node_id} gpu {gpu_id} is missing owner_lane")
            if not isinstance(gpu.get("allowed_workload_classes"), list) or not gpu.get("allowed_workload_classes"):
                errors.append(
                    f"capacity-envelope-registry.json node {node_id} gpu {gpu_id} must declare allowed_workload_classes"
                )
    if capacity_node_ids != topology_node_ids:
        missing = sorted(topology_node_ids - capacity_node_ids)
        extra = sorted(capacity_node_ids - topology_node_ids)
        if missing:
            errors.append("capacity-envelope-registry.json is missing topology nodes: " + ", ".join(missing))
        if extra:
            errors.append("capacity-envelope-registry.json has unexpected nodes: " + ", ".join(extra))

    if str(restore_ledger.get("source_of_truth") or "").strip() != "config/automation-backbone/restore-ledger.json":
        errors.append("restore-ledger.json source_of_truth must be config/automation-backbone/restore-ledger.json")
    if str(restore_ledger.get("status") or "").strip() not in ALLOWED_RESTORE_LEDGER_STATUSES:
        errors.append("restore-ledger.json has invalid status")
    restore_stores = [
        dict(item)
        for item in restore_ledger.get("stores", [])
        if isinstance(item, dict)
    ]
    if not restore_stores:
        errors.append("restore-ledger.json must declare at least one store")
    restore_store_ids: set[str] = set()
    for store in restore_stores:
        store_id = str(store.get("store_id") or "").strip()
        if not store_id:
            errors.append("restore-ledger.json contains a store without store_id")
            continue
        if store_id in restore_store_ids:
            errors.append(f"restore-ledger.json store_id {store_id!r} is duplicated")
        restore_store_ids.add(store_id)
        if store_id not in backup_store_by_id:
            errors.append(f"restore-ledger.json store {store_id} is missing from backup-restore-readiness.json")
            continue
        backup_entry = backup_store_by_id[store_id]
        if store.get("recovery_order") != backup_entry.get("recovery_order"):
            errors.append(
                f"restore-ledger.json store {store_id} recovery_order must match backup-restore-readiness.json"
            )
        if store.get("restore_status") != backup_entry.get("restore_status"):
            errors.append(
                f"restore-ledger.json store {store_id} restore_status must match backup-restore-readiness.json"
            )
        evidence_path = _resolve_declared_path(store.get("evidence_path"))
        if not evidence_path.exists():
            errors.append(f"restore-ledger.json store {store_id} evidence_path is missing: {evidence_path}")
        if store.get("restore_status") == "drill_backed" and not _is_parseable_iso_datetime(store.get("last_drill_at")):
            errors.append(f"restore-ledger.json store {store_id} must declare valid last_drill_at once drill_backed")
        for field_name in ("owner", "rto_target", "rpo_target", "current_confidence"):
            if not str(store.get(field_name) or "").strip():
                errors.append(f"restore-ledger.json store {store_id} is missing {field_name}")
        if not isinstance(store.get("dependency_validations"), list) or not store.get("dependency_validations"):
            errors.append(f"restore-ledger.json store {store_id} must declare dependency_validations")
    if restore_store_ids != set(backup_store_by_id):
        missing = sorted(set(backup_store_by_id) - restore_store_ids)
        extra = sorted(restore_store_ids - set(backup_store_by_id))
        if missing:
            errors.append("restore-ledger.json is missing critical stores: " + ", ".join(missing))
        if extra:
            errors.append("restore-ledger.json has unexpected stores: " + ", ".join(extra))

    if not MASTER_ATLAS_DASHBOARD_FEED_PATH.exists():
        errors.append("projects/dashboard/src/generated/master-atlas.json is missing")
        return
    if not master_atlas_dashboard_feed:
        errors.append("projects/dashboard/src/generated/master-atlas.json must contain valid JSON")
        return
    if not _is_parseable_iso_datetime(master_atlas_dashboard_feed.get("generated_at")):
        errors.append("projects/dashboard/src/generated/master-atlas.json is missing valid generated_at")
    required_feed_keys = {
        "generated_at",
        "readiness_ledger",
        "wave_admissibility",
        "governance_confidence",
        "turnover_readiness",
        "recommendations",
        "dashboard_summary",
        "eval_run_ledger",
        "artifact_provenance_ledger",
        "economic_dispatch_ledger",
        "capacity_envelope_registry",
        "restore_ledger",
        "quota_truth",
        "capacity_telemetry",
        "active_overrides",
        "routing_proof",
        "lane_selection_matrix",
        "approval_matrix",
        "failure_routing_matrix",
        "subscription_burn_registry",
        "lane_recommendations",
        "router_shadow_summary",
        "routing_decisions_latest",
        "safe_surface_summary",
        "autonomous_queue_summary",
        "coding_lane_registry",
        "provider_catalog",
    }
    missing_feed_keys = sorted(required_feed_keys - set(master_atlas_dashboard_feed.keys()))
    if missing_feed_keys:
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json is missing keys: "
            + ", ".join(missing_feed_keys)
        )
    feed_readiness = dict(master_atlas_dashboard_feed.get("readiness_ledger") or {})
    feed_records = feed_readiness.get("records")
    if not isinstance(feed_records, list):
        errors.append("projects/dashboard/src/generated/master-atlas.json readiness_ledger.records must be a list")
    elif len(feed_records) != len(capability_ids):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json readiness_ledger.records must match capability-adoption-registry.json capability count"
        )
    feed_governance = dict(master_atlas_dashboard_feed.get("governance_confidence") or {})
    if str(feed_governance.get("overall_status") or "").strip() not in ALLOWED_GOVERNANCE_CONFIDENCE_STATUSES:
        errors.append("projects/dashboard/src/generated/master-atlas.json governance_confidence.overall_status is invalid")
    feed_summary = dict(master_atlas_dashboard_feed.get("dashboard_summary") or {})
    if feed_summary.get("capability_count") != len(feed_records or []):
        errors.append("projects/dashboard/src/generated/master-atlas.json dashboard_summary.capability_count must match readiness_ledger.records")
    for summary_key in (
        "blocked_packet_count",
        "governance_blocker_count",
        "packet_ready_count",
        "proving_count",
        "turnover_status",
        "turnover_ready_now",
        "turnover_current_mode",
        "turnover_target_mode",
        "turnover_blocker_count",
        "alert_state",
        "quota_posture",
        "shadow_phase",
        "shadow_phase_label",
        "shadow_disagreement_rate",
        "lane_recommendation_count",
        "active_override_count",
        "safe_surface_queue_count",
        "autonomous_queue_count",
        "autonomous_dispatchable_queue_count",
        "next_required_approval",
    ):
        if summary_key not in feed_summary:
            errors.append(
                f"projects/dashboard/src/generated/master-atlas.json dashboard_summary is missing {summary_key}"
            )
    turnover = dict(master_atlas_dashboard_feed.get("turnover_readiness") or {})
    for field_name in ("current_mode", "target_mode", "autonomous_turnover_status", "operator_answer"):
        if not str(turnover.get(field_name) or "").strip():
            errors.append(
                f"projects/dashboard/src/generated/master-atlas.json turnover_readiness is missing {field_name}"
            )
    if not isinstance(turnover.get("autonomous_turnover_ready_now"), bool):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json turnover_readiness.autonomous_turnover_ready_now must be boolean"
        )
    if not isinstance(turnover.get("blocker_count"), int) or int(turnover.get("blocker_count")) < 0:
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json turnover_readiness.blocker_count must be a non-negative integer"
        )
    autonomous_queue_summary = dict(master_atlas_dashboard_feed.get("autonomous_queue_summary") or {})
    if not isinstance(autonomous_queue_summary.get("queue_count"), int):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json autonomous_queue_summary.queue_count must be an integer"
        )
    if not isinstance(autonomous_queue_summary.get("dispatchable_queue_count"), int):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json autonomous_queue_summary.dispatchable_queue_count must be an integer"
        )
    if dict(master_atlas_dashboard_feed.get("eval_run_ledger") or {}).get("version") != eval_run_ledger.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json eval_run_ledger version must match eval-run-ledger.json")
    if dict(master_atlas_dashboard_feed.get("artifact_provenance_ledger") or {}).get("version") != artifact_provenance.get("version"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json artifact_provenance_ledger version must match artifact-provenance-ledger.json"
        )
    if dict(master_atlas_dashboard_feed.get("economic_dispatch_ledger") or {}).get("version") != economic_dispatch.get("version"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json economic_dispatch_ledger version must match economic-dispatch-ledger.json"
        )
    if dict(master_atlas_dashboard_feed.get("capacity_envelope_registry") or {}).get("version") != capacity_envelope.get("version"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json capacity_envelope_registry version must match capacity-envelope-registry.json"
        )
    if dict(master_atlas_dashboard_feed.get("restore_ledger") or {}).get("version") != restore_ledger.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json restore_ledger version must match restore-ledger.json")
    if dict(master_atlas_dashboard_feed.get("lane_selection_matrix") or {}).get("version") != lane_selection_matrix.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json lane_selection_matrix version must match lane-selection-matrix.json")
    if dict(master_atlas_dashboard_feed.get("approval_matrix") or {}).get("version") != approval_matrix.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json approval_matrix version must match approval-matrix.json")
    if dict(master_atlas_dashboard_feed.get("failure_routing_matrix") or {}).get("version") != failure_routing_matrix.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json failure_routing_matrix version must match failure-routing-matrix.json")
    if dict(master_atlas_dashboard_feed.get("subscription_burn_registry") or {}).get("version") != subscription_burn_registry.get("version"):
        errors.append("projects/dashboard/src/generated/master-atlas.json subscription_burn_registry version must match subscription-burn-registry.json")
    if not isinstance(master_atlas_dashboard_feed.get("lane_recommendations"), list):
        errors.append("projects/dashboard/src/generated/master-atlas.json lane_recommendations must be a list")
    elif int(feed_summary.get("lane_recommendation_count") or 0) != len(master_atlas_dashboard_feed.get("lane_recommendations") or []):
        errors.append("projects/dashboard/src/generated/master-atlas.json dashboard_summary.lane_recommendation_count must match lane_recommendations length")
    shadow_summary = dict(master_atlas_dashboard_feed.get("router_shadow_summary") or {})
    if not isinstance(shadow_summary.get("phase"), int):
        errors.append("projects/dashboard/src/generated/master-atlas.json router_shadow_summary.phase must be an integer")
    if not str(shadow_summary.get("phase_label") or "").strip():
        errors.append("projects/dashboard/src/generated/master-atlas.json router_shadow_summary.phase_label is required")
    routing_latest = dict(master_atlas_dashboard_feed.get("routing_decisions_latest") or {})
    if not str(routing_latest.get("alert_state") or "").strip():
        errors.append("projects/dashboard/src/generated/master-atlas.json routing_decisions_latest.alert_state is required")
    if not isinstance(routing_latest.get("lane_recommendations"), list):
        errors.append("projects/dashboard/src/generated/master-atlas.json routing_decisions_latest.lane_recommendations must be a list")
    if not isinstance(routing_latest.get("next_required_approval"), dict):
        errors.append("projects/dashboard/src/generated/master-atlas.json routing_decisions_latest.next_required_approval must be an object")
    safe_surface_summary = dict(master_atlas_dashboard_feed.get("safe_surface_summary") or {})
    if not isinstance(safe_surface_summary.get("queue_count"), int):
        errors.append("projects/dashboard/src/generated/master-atlas.json safe_surface_summary.queue_count must be an integer")
    if feed_summary.get("turnover_status") != turnover.get("autonomous_turnover_status"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.turnover_status must match turnover_readiness.autonomous_turnover_status"
        )
    if feed_summary.get("turnover_ready_now") != turnover.get("autonomous_turnover_ready_now"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.turnover_ready_now must match turnover_readiness.autonomous_turnover_ready_now"
        )
    if feed_summary.get("turnover_current_mode") != turnover.get("current_mode"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.turnover_current_mode must match turnover_readiness.current_mode"
        )
    if feed_summary.get("turnover_target_mode") != turnover.get("target_mode"):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.turnover_target_mode must match turnover_readiness.target_mode"
        )
    if int(feed_summary.get("turnover_blocker_count") or 0) != int(turnover.get("blocker_count") or 0):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.turnover_blocker_count must match turnover_readiness.blocker_count"
        )
    if int(feed_summary.get("safe_surface_queue_count") or 0) != int(safe_surface_summary.get("queue_count") or 0):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.safe_surface_queue_count must match safe_surface_summary.queue_count"
        )
    if int(feed_summary.get("autonomous_queue_count") or 0) != int(autonomous_queue_summary.get("queue_count") or 0):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.autonomous_queue_count must match autonomous_queue_summary.queue_count"
        )
    if int(feed_summary.get("autonomous_dispatchable_queue_count") or 0) != int(
        autonomous_queue_summary.get("dispatchable_queue_count") or 0
    ):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json dashboard_summary.autonomous_dispatchable_queue_count must match autonomous_queue_summary.dispatchable_queue_count"
        )
    if int(turnover.get("autonomous_queue_count") or 0) != int(autonomous_queue_summary.get("queue_count") or 0):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json turnover_readiness.autonomous_queue_count must match autonomous_queue_summary.queue_count"
        )
    if int(turnover.get("dispatchable_autonomous_queue_count") or 0) != int(
        autonomous_queue_summary.get("dispatchable_queue_count") or 0
    ):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json turnover_readiness.dispatchable_autonomous_queue_count must match autonomous_queue_summary.dispatchable_queue_count"
        )
    if int(routing_latest.get("safe_surface_summary", {}).get("queue_count") or 0) != int(
        safe_surface_summary.get("queue_count") or 0
    ):
        errors.append(
            "projects/dashboard/src/generated/master-atlas.json routing_decisions_latest.safe_surface_summary.queue_count must match safe_surface_summary.queue_count"
        )


def _validate_routing_runtime_ledgers(
    *,
    errors: list[str],
    quota_truth: dict[str, Any],
    planned_subscription_evidence: dict[str, Any],
    capacity_telemetry: dict[str, Any],
    active_overrides: dict[str, Any],
    routing_proof: dict[str, Any],
    project_packets: dict[str, Any],
) -> None:
    if not QUOTA_TRUTH_PATH.exists():
        errors.append("reports/truth-inventory/quota-truth.json is missing")
    else:
        if not _is_parseable_iso_datetime(quota_truth.get("generated_at")):
            errors.append("reports/truth-inventory/quota-truth.json is missing valid generated_at")
        records = quota_truth.get("records")
        if not isinstance(records, list) or not records:
            errors.append("reports/truth-inventory/quota-truth.json records must be a non-empty list")
        if str(quota_truth.get("source_of_truth") or "").strip() != "reports/truth-inventory/quota-truth.json":
            errors.append("reports/truth-inventory/quota-truth.json source_of_truth must point at itself")

    if not PLANNED_SUBSCRIPTION_EVIDENCE_PATH.exists():
        errors.append("reports/truth-inventory/planned-subscription-evidence.json is missing")
    else:
        if not _is_parseable_iso_datetime(planned_subscription_evidence.get("updated_at")):
            errors.append("reports/truth-inventory/planned-subscription-evidence.json is missing valid updated_at")
        planned_captures = planned_subscription_evidence.get("captures")
        if not isinstance(planned_captures, list):
            errors.append("reports/truth-inventory/planned-subscription-evidence.json captures must be a list")

    if not CAPACITY_TELEMETRY_PATH.exists():
        errors.append("reports/truth-inventory/capacity-telemetry.json is missing")
    else:
        if not _is_parseable_iso_datetime(capacity_telemetry.get("generated_at")):
            errors.append("reports/truth-inventory/capacity-telemetry.json is missing valid generated_at")
        if not isinstance(capacity_telemetry.get("node_samples"), list) or not capacity_telemetry.get("node_samples"):
            errors.append("reports/truth-inventory/capacity-telemetry.json node_samples must be a non-empty list")
        if not isinstance(capacity_telemetry.get("gpu_samples"), list) or not capacity_telemetry.get("gpu_samples"):
            errors.append("reports/truth-inventory/capacity-telemetry.json gpu_samples must be a non-empty list")
        capacity_summary = dict(capacity_telemetry.get("capacity_summary") or {})
        sample_posture = str(capacity_summary.get("sample_posture") or "").strip()
        if sample_posture == "scheduler_projection_backed":
            if not isinstance(capacity_summary.get("harvestable_by_zone"), dict):
                errors.append("reports/truth-inventory/capacity-telemetry.json capacity_summary.harvestable_by_zone must be a mapping when scheduler projection is active")
            if not isinstance(capacity_summary.get("harvestable_by_slot"), dict):
                errors.append("reports/truth-inventory/capacity-telemetry.json capacity_summary.harvestable_by_slot must be a mapping when scheduler projection is active")
            scheduler_slot_samples = capacity_telemetry.get("scheduler_slot_samples")
            if not isinstance(scheduler_slot_samples, list) or not scheduler_slot_samples:
                errors.append("reports/truth-inventory/capacity-telemetry.json scheduler_slot_samples must be a non-empty list when scheduler projection is active")
            else:
                for sample in scheduler_slot_samples:
                    if not isinstance(sample, dict):
                        errors.append("reports/truth-inventory/capacity-telemetry.json scheduler_slot_samples entries must be objects")
                        continue
                    if not str(sample.get("scheduler_slot_id") or "").strip():
                        errors.append("reports/truth-inventory/capacity-telemetry.json scheduler_slot_samples entries must include scheduler_slot_id")
                    if not isinstance(sample.get("member_gpu_ids"), list):
                        errors.append("reports/truth-inventory/capacity-telemetry.json scheduler_slot_samples entries must include member_gpu_ids lists")
                    if not isinstance(sample.get("admissible_gpu_ids"), list):
                        errors.append("reports/truth-inventory/capacity-telemetry.json scheduler_slot_samples entries must include admissible_gpu_ids lists")

    if not ACTIVE_OVERRIDES_PATH.exists():
        errors.append("reports/truth-inventory/active-overrides.json is missing")
    else:
        policy = dict(active_overrides.get("policy") or {})
        allowed_types = policy.get("allowed_types")
        if not isinstance(allowed_types, list) or not allowed_types:
            errors.append("reports/truth-inventory/active-overrides.json policy.allowed_types must be a non-empty list")
        if not isinstance(active_overrides.get("active_overrides"), list):
            errors.append("reports/truth-inventory/active-overrides.json active_overrides must be a list")

    if not ROUTING_PROOF_PATH.exists():
        errors.append("reports/truth-inventory/routing-proof.json is missing")
    else:
        if not _is_parseable_iso_datetime(routing_proof.get("generated_at")):
            errors.append("reports/truth-inventory/routing-proof.json is missing valid generated_at")
        suites = routing_proof.get("suites")
        if not isinstance(suites, list) or not suites:
            errors.append("reports/truth-inventory/routing-proof.json suites must be a non-empty list")

    for project in project_packets.get("projects", []):
        if not isinstance(project, dict):
            continue
        project_id = str(project.get("id") or "").strip()
        routing_class = str(project.get("routing_class") or "").strip()
        if routing_class not in ALLOWED_PROJECT_ROUTING_CLASSES:
            errors.append(f"project-packet-registry.json project {project_id} has invalid routing_class {routing_class!r}")
        if not str(project.get("routing_reason") or "").strip():
            errors.append(f"project-packet-registry.json project {project_id} is missing routing_reason")


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    try:
        ignored_generated_docs, remaining_args = _parse_ignored_generated_doc_args(args)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 2
    if remaining_args:
        print(f"FAIL: Unexpected arguments: {' '.join(remaining_args)}")
        return 2

    errors: list[str] = []

    vault_host_vars = _load_yaml(VAULT_HOST_VARS_PATH)
    topology = _load_json("platform-topology.json")
    hardware_inventory = _load_json("hardware-inventory.json")
    model_deployments = _load_json("model-deployment-registry.json")
    provider_catalog = _load_json("provider-catalog.json")
    subscription_burn = _load_json("subscription-burn-registry.json")
    lane_selection_matrix = _load_json("lane-selection-matrix.json")
    approval_matrix = _load_json("approval-matrix.json")
    failure_routing_matrix = _load_json("failure-routing-matrix.json")
    autonomy_activation = _load_json("autonomy-activation-registry.json")
    tooling_inventory = _load_json("tooling-inventory.json")
    coding_lanes = _load_json("coding-lane-registry.json")
    credential_surfaces = _load_json("credential-surface-registry.json")
    operator_surfaces = _load_json("operator-surface-registry.json")
    operator_runbooks = _load_json("operator-runbooks.json")
    repo_roots = _load_json("repo-roots-registry.json")
    runtime_ownership = _load_json("runtime-ownership-contract.json")
    runtime_ownership_packets = _load_json("runtime-ownership-packets.json")
    runtime_subsystems = _load_json("runtime-subsystem-registry.json")
    runtime_migrations = _load_json("runtime-migration-registry.json")
    routing_taxonomy = _load_json("routing-taxonomy-map.json")
    reconciliation_sources = _load_json("reconciliation-source-registry.json")
    completion_program = _load_json("completion-program-registry.json")
    portfolio = _load_json("project-maturity-registry.json")
    project_packets = _load_json("project-packet-registry.json")
    domain_packets = _load_json("domain-packets-registry.json")
    memory_namespaces = _load_json("memory-namespace-registry.json")
    bootstrap_programs = _load_json("bootstrap-program-registry.json")
    bootstrap_takeover = _load_json("bootstrap-takeover-registry.json")
    bootstrap_slice_catalog = _load_json("bootstrap-slice-catalog.json")
    bootstrap_execution_policy = _load_json("bootstrap-execution-policy.json")
    foundry_proving = _load_json("foundry-proving-registry.json")
    governance_drills = _load_json("governance-drill-registry.json")
    approval_packets = _load_json("approval-packet-registry.json")
    contract_registry = _load_json("contract-registry.json")
    capability_adoption = _load_json("capability-adoption-registry.json")
    eval_run_ledger = _load_json("eval-run-ledger.json")
    artifact_provenance = _load_json("artifact-provenance-ledger.json")
    economic_dispatch = _load_json("economic-dispatch-ledger.json")
    capacity_envelope = _load_json("capacity-envelope-registry.json")
    restore_ledger = _load_json("restore-ledger.json")
    backup_restore_readiness = _load_json("backup-restore-readiness.json")
    artifact_topology = _load_json("artifact-topology-registry.json")
    data_lifecycle = _load_json("data-lifecycle-registry.json")
    docs = _load_json("docs-lifecycle-registry.json")
    provider_usage_evidence = {}
    if PROVIDER_USAGE_EVIDENCE_PATH.exists():
        provider_usage_evidence = json.loads(PROVIDER_USAGE_EVIDENCE_PATH.read_text(encoding="utf-8"))
    planned_subscription_evidence = {}
    if PLANNED_SUBSCRIPTION_EVIDENCE_PATH.exists():
        planned_subscription_evidence = json.loads(PLANNED_SUBSCRIPTION_EVIDENCE_PATH.read_text(encoding="utf-8"))
    vault_litellm_env_audit = {}
    if VAULT_LITELLM_ENV_AUDIT_PATH.exists():
        vault_litellm_env_audit = json.loads(VAULT_LITELLM_ENV_AUDIT_PATH.read_text(encoding="utf-8"))
    vault_redis_audit = {}
    if VAULT_REDIS_AUDIT_PATH.exists():
        vault_redis_audit = json.loads(VAULT_REDIS_AUDIT_PATH.read_text(encoding="utf-8"))
    latest_truth_snapshot = {}
    if TRUTH_SNAPSHOT_PATH.exists():
        latest_truth_snapshot = json.loads(TRUTH_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    quota_truth = {}
    if QUOTA_TRUTH_PATH.exists():
        quota_truth = json.loads(QUOTA_TRUTH_PATH.read_text(encoding="utf-8"))
    capacity_telemetry = {}
    if CAPACITY_TELEMETRY_PATH.exists():
        capacity_telemetry = json.loads(CAPACITY_TELEMETRY_PATH.read_text(encoding="utf-8"))
    active_overrides = {}
    if ACTIVE_OVERRIDES_PATH.exists():
        active_overrides = json.loads(ACTIVE_OVERRIDES_PATH.read_text(encoding="utf-8"))
    routing_proof = {}
    if ROUTING_PROOF_PATH.exists():
        routing_proof = json.loads(ROUTING_PROOF_PATH.read_text(encoding="utf-8"))
    latest_bootstrap_snapshot = {}
    if BOOTSTRAP_SNAPSHOT_PATH.exists():
        latest_bootstrap_snapshot = json.loads(BOOTSTRAP_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    operator_surface_census = {}
    if BOOTSTRAP_OPERATOR_SURFACE_CENSUS_PATH.exists():
        operator_surface_census = json.loads(BOOTSTRAP_OPERATOR_SURFACE_CENSUS_PATH.read_text(encoding="utf-8"))
    operator_summary_alignment = {}
    if BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT_PATH.exists():
        operator_summary_alignment = json.loads(BOOTSTRAP_OPERATOR_SUMMARY_ALIGNMENT_PATH.read_text(encoding="utf-8"))
    operator_fixture_parity = {}
    if BOOTSTRAP_OPERATOR_FIXTURE_PARITY_PATH.exists():
        operator_fixture_parity = json.loads(BOOTSTRAP_OPERATOR_FIXTURE_PARITY_PATH.read_text(encoding="utf-8"))
    operator_nav_lock = {}
    if BOOTSTRAP_OPERATOR_NAV_LOCK_PATH.exists():
        operator_nav_lock = json.loads(BOOTSTRAP_OPERATOR_NAV_LOCK_PATH.read_text(encoding="utf-8"))
    durable_persistence_packet = {}
    if BOOTSTRAP_DURABLE_PERSISTENCE_PACKET_PATH.exists():
        durable_persistence_packet = json.loads(BOOTSTRAP_DURABLE_PERSISTENCE_PACKET_PATH.read_text(encoding="utf-8"))
    foundry_proving_packet = {}
    if BOOTSTRAP_FOUNDRY_PROVING_PACKET_PATH.exists():
        foundry_proving_packet = json.loads(BOOTSTRAP_FOUNDRY_PROVING_PACKET_PATH.read_text(encoding="utf-8"))
    ralph_loop_report = {}
    if RALPH_LOOP_REPORT_PATH.exists():
        ralph_loop_report = json.loads(RALPH_LOOP_REPORT_PATH.read_text(encoding="utf-8"))
    governance_drill_packets = {}
    if BOOTSTRAP_GOVERNANCE_DRILL_PACKETS_PATH.exists():
        governance_drill_packets = json.loads(BOOTSTRAP_GOVERNANCE_DRILL_PACKETS_PATH.read_text(encoding="utf-8"))
    takeover_promotion_packet = {}
    if BOOTSTRAP_TAKEOVER_PROMOTION_PACKET_PATH.exists():
        takeover_promotion_packet = json.loads(BOOTSTRAP_TAKEOVER_PROMOTION_PACKET_PATH.read_text(encoding="utf-8"))
    master_atlas_dashboard_feed = {}
    if MASTER_ATLAS_DASHBOARD_FEED_PATH.exists():
        master_atlas_dashboard_feed = json.loads(MASTER_ATLAS_DASHBOARD_FEED_PATH.read_text(encoding="utf-8"))
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
        "coding-lane-registry.json": str(coding_lanes.get("version") or ""),
        "credential-surface-registry.json": str(credential_surfaces.get("version") or ""),
        "operator-surface-registry.json": str(operator_surfaces.get("version") or ""),
        "operator-runbooks.json": str(operator_runbooks.get("version") or ""),
        "repo-roots-registry.json": str(repo_roots.get("version") or ""),
        "runtime-ownership-contract.json": str(runtime_ownership.get("version") or ""),
        "runtime-ownership-packets.json": str(runtime_ownership_packets.get("version") or ""),
        "runtime-subsystem-registry.json": str(runtime_subsystems.get("version") or ""),
        "runtime-migration-registry.json": str(runtime_migrations.get("version") or ""),
        "routing-taxonomy-map.json": str(routing_taxonomy.get("version") or ""),
        "reconciliation-source-registry.json": str(reconciliation_sources.get("version") or ""),
        "completion-program-registry.json": str(completion_program.get("version") or ""),
        "project-maturity-registry.json": str(portfolio.get("version") or ""),
        "project-packet-registry.json": str(project_packets.get("version") or ""),
        "bootstrap-program-registry.json": str(bootstrap_programs.get("version") or ""),
        "bootstrap-takeover-registry.json": str(bootstrap_takeover.get("version") or ""),
        "bootstrap-slice-catalog.json": str(bootstrap_slice_catalog.get("version") or ""),
        "bootstrap-execution-policy.json": str(bootstrap_execution_policy.get("version") or ""),
        "foundry-proving-registry.json": str(foundry_proving.get("version") or ""),
        "governance-drill-registry.json": str(governance_drills.get("version") or ""),
        "approval-packet-registry.json": str(approval_packets.get("version") or ""),
        "contract-registry.json": str(contract_registry.get("version") or ""),
        "capability-adoption-registry.json": str(capability_adoption.get("version") or ""),
        "eval-run-ledger.json": str(eval_run_ledger.get("version") or ""),
        "artifact-provenance-ledger.json": str(artifact_provenance.get("version") or ""),
        "economic-dispatch-ledger.json": str(economic_dispatch.get("version") or ""),
        "capacity-envelope-registry.json": str(capacity_envelope.get("version") or ""),
        "restore-ledger.json": str(restore_ledger.get("version") or ""),
        "backup-restore-readiness.json": str(backup_restore_readiness.get("version") or ""),
        "docs-lifecycle-registry.json": str(docs.get("version") or ""),
        "program-operating-system.json": str(operating_system.get("version") or ""),
    }
    errors.extend(validate_layered_master_plan_contract())

    _validate_bootstrap_zero_ambiguity_contracts(
        errors=errors,
        bootstrap_programs=bootstrap_programs,
        bootstrap_takeover=bootstrap_takeover,
        bootstrap_slice_catalog=bootstrap_slice_catalog,
        bootstrap_execution_policy=bootstrap_execution_policy,
        foundry_proving=foundry_proving,
        governance_drills=governance_drills,
        approval_packets=approval_packets,
        operator_runbooks=operator_runbooks,
        project_packets=project_packets,
        latest_bootstrap_snapshot=latest_bootstrap_snapshot,
        operator_surface_census=operator_surface_census,
        operator_summary_alignment=operator_summary_alignment,
        operator_fixture_parity=operator_fixture_parity,
        operator_nav_lock=operator_nav_lock,
        durable_persistence_packet=durable_persistence_packet,
        foundry_proving_packet=foundry_proving_packet,
        governance_drill_packets=governance_drill_packets,
        takeover_promotion_packet=takeover_promotion_packet,
    )
    _validate_capability_adoption_registry(
        errors=errors,
        capability_adoption=capability_adoption,
        contract_registry=contract_registry,
        repo_roots=repo_roots,
        runtime_ownership=runtime_ownership,
        runtime_ownership_packets=runtime_ownership_packets,
    )
    _validate_capability_adoption_boundary_fields(
        errors=errors,
        capability_adoption=capability_adoption,
        domain_packets=domain_packets,
        memory_namespaces=memory_namespaces,
    )
    _validate_repo_structure_contract(errors)
    _validate_master_atlas_contracts(
        errors=errors,
        contract_registry=contract_registry,
        capability_adoption=capability_adoption,
        policy_registry=policy_registry,
        topology=topology,
        coding_lanes=coding_lanes,
        eval_run_ledger=eval_run_ledger,
        artifact_provenance=artifact_provenance,
        economic_dispatch=economic_dispatch,
        capacity_envelope=capacity_envelope,
        restore_ledger=restore_ledger,
        backup_restore_readiness=backup_restore_readiness,
        master_atlas_dashboard_feed=master_atlas_dashboard_feed,
        lane_selection_matrix=lane_selection_matrix,
        approval_matrix=approval_matrix,
        failure_routing_matrix=failure_routing_matrix,
        subscription_burn_registry=subscription_burn,
    )
    _validate_devstack_convergence_boundaries(
        errors=errors,
        master_atlas_dashboard_feed=master_atlas_dashboard_feed,
    )
    _validate_routing_runtime_ledgers(
        errors=errors,
        quota_truth=quota_truth,
        planned_subscription_evidence=planned_subscription_evidence,
        capacity_telemetry=capacity_telemetry,
        active_overrides=active_overrides,
        routing_proof=routing_proof,
        project_packets=project_packets,
    )
    lifecycle_paths = _validate_docs_lifecycle_registry_shape(errors, docs)
    _validate_archive_doc_metadata(errors, docs)
    _validate_high_risk_reference_doc_metadata(errors, docs)
    _validate_operator_helper_surfaces(errors)
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
    _validate_vault_prometheus_probe_contract(
        errors=errors,
        operator_surfaces=operator_surfaces,
        vault_host_vars=vault_host_vars,
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
        if evidence_kind == "coding_tool_subscription":
            tooling_probe = dict(evidence.get("tooling_probe") or {})
            billing = dict(evidence.get("billing") or {})
            tooling_status = str(tooling_probe.get("status") or "")
            if tooling_status not in ALLOWED_PROVIDER_TOOLING_PROBE_STATUSES:
                errors.append(
                    f"provider-catalog.json provider {provider_id} has invalid tooling_probe.status {tooling_status!r}"
                )
            if not list(tooling_probe.get("expected_hosts", [])):
                errors.append(f"provider-catalog.json provider {provider_id} tooling_probe must declare expected_hosts")
            if not list(tooling_probe.get("supported_commands", [])):
                errors.append(
                    f"provider-catalog.json provider {provider_id} tooling_probe must declare supported_commands"
                )
            integration_status = str(tooling_probe.get("integration_status") or "")
            if integration_status not in ALLOWED_PROVIDER_INTEGRATION_STATUSES:
                errors.append(
                    f"provider-catalog.json provider {provider_id} has invalid tooling_probe.integration_status {integration_status!r}"
                )
            if not str(tooling_probe.get("last_verified_at") or "").strip():
                errors.append(
                    f"provider-catalog.json provider {provider_id} tooling_probe is missing last_verified_at"
                )
            if not str(tooling_probe.get("source") or "").strip():
                errors.append(f"provider-catalog.json provider {provider_id} tooling_probe is missing source")
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

    planned_subscription_index = {
        str(entry.get("id") or ""): dict(entry)
        for entry in subscription_burn.get("planned_subscriptions", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    planned_captures = planned_subscription_evidence.get("captures", []) if isinstance(planned_subscription_evidence, dict) else []
    if planned_captures and not isinstance(planned_captures, list):
        errors.append("reports/truth-inventory/planned-subscription-evidence.json captures must be a list")
        planned_captures = []
    for capture in planned_captures:
        if not isinstance(capture, dict):
            errors.append("reports/truth-inventory/planned-subscription-evidence.json captures entries must be objects")
            continue
        family_id = str(capture.get("family_id") or "").strip()
        provider_id = str(capture.get("provider_id") or "").strip()
        status = str(capture.get("status") or "").strip()
        observed_at = str(capture.get("observed_at") or "").strip()
        source = str(capture.get("source") or "").strip()
        request_surface = str(capture.get("request_surface") or "").strip()
        required_commands = capture.get("required_commands")
        available_commands = capture.get("available_commands")
        required_env_contracts = capture.get("required_env_contracts")
        present_env_contracts = capture.get("present_env_contracts")
        family = planned_subscription_index.get(family_id)
        if family is None:
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture references unknown planned family "
                f"{family_id!r}"
            )
            continue
        expected_provider_id = str(family.get("provider_id") or "").strip()
        if provider_id != expected_provider_id:
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} has provider_id {provider_id!r} but expected {expected_provider_id!r}"
            )
        if status not in ALLOWED_PLANNED_SUBSCRIPTION_CAPTURE_STATUSES:
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} has invalid status {status!r}"
            )
        if not observed_at or not _is_parseable_iso_datetime(observed_at):
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} is missing valid observed_at"
            )
        if not source:
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} is missing source"
            )
        if not request_surface:
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} is missing request_surface"
            )
        for field_name, value in (
            ("required_commands", required_commands),
            ("available_commands", available_commands),
            ("required_env_contracts", required_env_contracts),
            ("present_env_contracts", present_env_contracts),
        ):
            if not isinstance(value, list):
                errors.append(
                    "reports/truth-inventory/planned-subscription-evidence.json capture for "
                    f"{family_id} field {field_name} must be a list"
                )
        if status in {"tooling_ready", "supported_tool_usage_observed"} and not list(available_commands or []):
            errors.append(
                "reports/truth-inventory/planned-subscription-evidence.json capture for "
                f"{family_id} requires available_commands when status is {status!r}"
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
    repo_root_ids = {
        str(entry.get("id") or "")
        for entry in repo_roots.get("roots", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    implementation_root_id = str(runtime_ownership.get("implementation_authority_root_id") or "")
    runtime_root_id = str(runtime_ownership.get("runtime_authority_root_id") or "")
    if implementation_root_id not in repo_root_ids:
        errors.append(
            "runtime-ownership-contract.json implementation_authority_root_id must reference a root id from repo-roots-registry.json"
        )
    if runtime_root_id not in repo_root_ids:
        errors.append(
            "runtime-ownership-contract.json runtime_authority_root_id must reference a root id from repo-roots-registry.json"
        )
    runtime_state_root_ids = [
        str(root_id) for root_id in runtime_ownership.get("runtime_state_root_ids", []) if str(root_id).strip()
    ]
    if not runtime_state_root_ids:
        errors.append("runtime-ownership-contract.json must declare runtime_state_root_ids")
    for root_id in runtime_state_root_ids:
        if root_id not in repo_root_ids:
            errors.append(
                f"runtime-ownership-contract.json runtime_state_root_ids references unknown root id {root_id!r}"
            )

    if str(reconciliation_sources.get("source_of_truth") or "") != "config/automation-backbone/reconciliation-source-registry.json":
        errors.append(
            "reconciliation-source-registry.json source_of_truth must be config/automation-backbone/reconciliation-source-registry.json"
        )
    if str(reconciliation_sources.get("status") or "") != "active":
        errors.append("reconciliation-source-registry.json status must be active")
    if set(str(item) for item in reconciliation_sources.get("source_kinds", [])) != ALLOWED_RECONCILIATION_SOURCE_KINDS:
        errors.append("reconciliation-source-registry.json source_kinds must match the allowed source-kind set")
    if set(str(item) for item in reconciliation_sources.get("ecosystem_roles", [])) != ALLOWED_ECOSYSTEM_ROLES:
        errors.append("reconciliation-source-registry.json ecosystem_roles must match the allowed ecosystem-role set")
    if set(str(item) for item in reconciliation_sources.get("authority_statuses", [])) != ALLOWED_SOURCE_AUTHORITY_STATUSES:
        errors.append("reconciliation-source-registry.json authority_statuses must match the allowed authority-status set")
    if set(str(item) for item in reconciliation_sources.get("review_statuses", [])) != ALLOWED_SOURCE_REVIEW_STATUSES:
        errors.append("reconciliation-source-registry.json review_statuses must match the allowed review-status set")
    if set(str(item) for item in reconciliation_sources.get("default_dispositions", [])) != ALLOWED_SOURCE_DEFAULT_DISPOSITIONS:
        errors.append("reconciliation-source-registry.json default_dispositions must match the allowed disposition set")
    if set(str(item) for item in reconciliation_sources.get("preservation_statuses", [])) != ALLOWED_SOURCE_PRESERVATION_STATUSES:
        errors.append("reconciliation-source-registry.json preservation_statuses must match the allowed preservation-status set")
    if set(str(item) for item in reconciliation_sources.get("priorities", [])) != ALLOWED_SOURCE_PRIORITIES:
        errors.append("reconciliation-source-registry.json priorities must match the allowed priority set")

    reconciliation_source_entries = [
        dict(entry) for entry in reconciliation_sources.get("sources", []) if isinstance(entry, dict)
    ]
    if not reconciliation_source_entries:
        errors.append("reconciliation-source-registry.json must declare at least one source entry")
    reconciliation_source_ids = [str(entry.get("id") or "").strip() for entry in reconciliation_source_entries]
    if len(reconciliation_source_ids) != len(set(reconciliation_source_ids)):
        errors.append("reconciliation-source-registry.json contains duplicate source ids")
    missing_reconciliation_source_ids = sorted(
        required_id
        for required_id in REQUIRED_RECONCILIATION_SOURCE_IDS
        if required_id not in set(reconciliation_source_ids)
    )
    if missing_reconciliation_source_ids:
        errors.append(
            "reconciliation-source-registry.json is missing required source ids: "
            + ", ".join(missing_reconciliation_source_ids)
        )

    github_repo_pattern = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    for entry in reconciliation_source_entries:
        source_id = str(entry.get("id") or "").strip()
        if not source_id:
            errors.append("reconciliation-source-registry.json contains a source without an id")
            continue
        path_value = str(entry.get("path") or "").strip()
        if not path_value:
            errors.append(f"reconciliation-source-registry.json source {source_id} is missing path")
        source_kind = str(entry.get("source_kind") or "")
        if source_kind not in ALLOWED_RECONCILIATION_SOURCE_KINDS:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid source_kind {source_kind!r}"
            )
        ecosystem_role = str(entry.get("ecosystem_role") or "")
        if ecosystem_role not in ALLOWED_ECOSYSTEM_ROLES:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid ecosystem_role {ecosystem_role!r}"
            )
        authority_status = str(entry.get("authority_status") or "")
        if authority_status not in ALLOWED_SOURCE_AUTHORITY_STATUSES:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid authority_status {authority_status!r}"
            )
        review_status = str(entry.get("review_status") or "")
        if review_status not in ALLOWED_SOURCE_REVIEW_STATUSES:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid review_status {review_status!r}"
            )
        disposition = str(entry.get("default_disposition") or "")
        if disposition not in ALLOWED_SOURCE_DEFAULT_DISPOSITIONS:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid default_disposition {disposition!r}"
            )
        preservation_status = str(entry.get("preservation_status") or "")
        if preservation_status not in ALLOWED_SOURCE_PRESERVATION_STATUSES:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid preservation_status {preservation_status!r}"
            )
        priority = str(entry.get("priority") or "")
        if priority not in ALLOWED_SOURCE_PRIORITIES:
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid priority {priority!r}"
            )
        github_repo = str(entry.get("github_repo") or "").strip()
        if github_repo and not github_repo_pattern.match(github_repo):
            errors.append(
                f"reconciliation-source-registry.json source {source_id} has invalid github_repo {github_repo!r}"
            )
        if not isinstance(entry.get("shaun_decision_required"), bool):
            errors.append(
                f"reconciliation-source-registry.json source {source_id} must set shaun_decision_required as a boolean"
            )
        duplicate_of = str(entry.get("duplicate_of") or "").strip()
        if duplicate_of and duplicate_of not in set(reconciliation_source_ids):
            errors.append(
                f"reconciliation-source-registry.json source {source_id} duplicate_of references unknown source id {duplicate_of!r}"
            )
        notes = entry.get("notes", [])
        if not isinstance(notes, list) or not all(str(item).strip() for item in notes):
            errors.append(f"reconciliation-source-registry.json source {source_id} notes must be a non-empty string list")
        evidence_paths = entry.get("evidence_paths", [])
        if not isinstance(evidence_paths, list) or not all(str(item).strip() for item in evidence_paths):
            errors.append(
                f"reconciliation-source-registry.json source {source_id} evidence_paths must be a non-empty string list"
            )
        else:
            for evidence_path in evidence_paths:
                evidence_value = str(evidence_path).strip()
                if re.match(r"^[A-Za-z]:/", evidence_value) or re.match(r"^[A-Za-z]:\\\\", evidence_value):
                    if not resolve_external_path(evidence_value).exists():
                        errors.append(
                            f"reconciliation-source-registry.json source {source_id} evidence path is missing: {evidence_value}"
                        )
                elif evidence_value.startswith("http://") or evidence_value.startswith("https://"):
                    continue
                else:
                    if not (REPO_ROOT / evidence_value).exists():
                        errors.append(
                            f"reconciliation-source-registry.json source {source_id} evidence path is missing: {evidence_value}"
                        )
        if path_value and re.match(r"^[A-Za-z]:/", path_value):
            if not resolve_external_path(path_value).exists():
                errors.append(f"reconciliation-source-registry.json source {source_id} path is missing: {path_value}")
        if source_kind == "github_repo" and not path_value.startswith("https://github.com/"):
            errors.append(
                f"reconciliation-source-registry.json source {source_id} github_repo entries must use a GitHub URL path"
            )

    github_portfolio = dict(reconciliation_sources.get("github_portfolio") or {})
    if not github_portfolio:
        errors.append("reconciliation-source-registry.json must declare github_portfolio")
    else:
        if str(github_portfolio.get("owner") or "") != "Dirty13itch":
            errors.append("reconciliation-source-registry.json github_portfolio owner must be Dirty13itch")
        if not str(github_portfolio.get("last_verified_at") or "").strip():
            errors.append("reconciliation-source-registry.json github_portfolio last_verified_at must be set")

        github_portfolio_repos = [
            dict(entry) for entry in github_portfolio.get("repos", []) if isinstance(entry, dict)
        ]
        if not github_portfolio_repos:
            errors.append("reconciliation-source-registry.json github_portfolio must declare repos")

        repo_count = github_portfolio.get("repo_count")
        if not isinstance(repo_count, int) or repo_count != len(github_portfolio_repos):
            errors.append("reconciliation-source-registry.json github_portfolio repo_count must match repos length")
        doc_repo_count = github_portfolio.get("doc_repo_count")
        if not isinstance(doc_repo_count, int) or doc_repo_count != len(github_portfolio_repos):
            errors.append("reconciliation-source-registry.json github_portfolio doc_repo_count must match repos length")
        live_repo_count = github_portfolio.get("live_repo_count")
        if not isinstance(live_repo_count, int) or live_repo_count != len(github_portfolio_repos):
            errors.append("reconciliation-source-registry.json github_portfolio live_repo_count must match repos length")

        doc_only_repos = github_portfolio.get("doc_only_repos", [])
        github_only_repos = github_portfolio.get("github_only_repos", [])
        repos_without_confirmed_local_clone = github_portfolio.get("repos_without_confirmed_local_clone", [])
        for field_name, value in (
            ("doc_only_repos", doc_only_repos),
            ("github_only_repos", github_only_repos),
            ("repos_without_confirmed_local_clone", repos_without_confirmed_local_clone),
        ):
            if not isinstance(value, list) or not all(str(item).strip() for item in value):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio {field_name} must be a string list"
                )
        if doc_only_repos:
            errors.append(
                "reconciliation-source-registry.json github_portfolio doc_only_repos must be empty after sync"
            )
        if github_only_repos:
            errors.append(
                "reconciliation-source-registry.json github_portfolio github_only_repos must be empty after sync"
            )

        role_counts_value = github_portfolio.get("role_counts", {})
        batch_counts_value = github_portfolio.get("batch_counts", {})
        if not isinstance(role_counts_value, dict) or not all(
            isinstance(key, str) and key.strip() and isinstance(value, int)
            for key, value in role_counts_value.items()
        ):
            errors.append("reconciliation-source-registry.json github_portfolio role_counts must be a string->int map")
        if not isinstance(batch_counts_value, dict) or not all(
            isinstance(key, str) and key.strip() and isinstance(value, int)
            for key, value in batch_counts_value.items()
        ):
            errors.append("reconciliation-source-registry.json github_portfolio batch_counts must be a string->int map")

        github_portfolio_ids = [str(entry.get("id") or "").strip() for entry in github_portfolio_repos]
        if len(github_portfolio_ids) != len(set(github_portfolio_ids)):
            errors.append("reconciliation-source-registry.json github_portfolio contains duplicate repo ids")
        github_portfolio_repo_names = [str(entry.get("github_repo") or "").strip() for entry in github_portfolio_repos]
        if len(github_portfolio_repo_names) != len(set(github_portfolio_repo_names)):
            errors.append("reconciliation-source-registry.json github_portfolio contains duplicate github_repo values")

        portfolio_role_counts = Counter()
        portfolio_batch_counts = Counter()
        portfolio_repo_set: set[str] = set()
        unconfirmed_local_clone_repos: list[str] = []
        for entry in github_portfolio_repos:
            repo_name = str(entry.get("github_repo") or "").strip()
            if not github_repo_pattern.match(repo_name):
                errors.append(
                    "reconciliation-source-registry.json github_portfolio contains invalid github_repo "
                    + repr(repo_name)
                )
                continue
            if not repo_name.startswith("Dirty13itch/"):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must stay under Dirty13itch/"
                )
            portfolio_repo_set.add(repo_name)

            role_value = str(entry.get("ecosystem_role") or "")
            if role_value not in ALLOWED_ECOSYSTEM_ROLES:
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} has invalid ecosystem_role {role_value!r}"
                )
            else:
                portfolio_role_counts[role_value] += 1

            batch_value = str(entry.get("batch") or "").strip()
            if not batch_value:
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set batch"
                )
            else:
                portfolio_batch_counts[batch_value] += 1

            for required_field in ("name", "url", "working_clone", "current_maturity", "shaun_decision"):
                if not str(entry.get(required_field) or "").strip():
                    errors.append(
                        f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} is missing {required_field}"
                    )
            if not isinstance(entry.get("is_private"), bool):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set is_private as a boolean"
                )
            if not isinstance(entry.get("is_fork"), bool):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set is_fork as a boolean"
                )
            if not isinstance(entry.get("doc_classified"), bool):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set doc_classified as a boolean"
                )
            if not isinstance(entry.get("live_on_github"), bool):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set live_on_github as a boolean"
                )
            if not isinstance(entry.get("has_confirmed_local_clone"), bool):
                errors.append(
                    f"reconciliation-source-registry.json github_portfolio repo {repo_name!r} must set has_confirmed_local_clone as a boolean"
                )
            elif not entry.get("has_confirmed_local_clone"):
                unconfirmed_local_clone_repos.append(repo_name)

        if role_counts_value != dict(sorted(portfolio_role_counts.items())):
            errors.append(
                "reconciliation-source-registry.json github_portfolio role_counts must match the counted repo roles"
            )
        if batch_counts_value != dict(sorted(portfolio_batch_counts.items())):
            errors.append(
                "reconciliation-source-registry.json github_portfolio batch_counts must match the counted repo batches"
            )
        if sorted(str(item) for item in repos_without_confirmed_local_clone) != sorted(unconfirmed_local_clone_repos):
            errors.append(
                "reconciliation-source-registry.json github_portfolio repos_without_confirmed_local_clone must match repo entries"
            )

        ecosystem_registry_text = (
            REPO_ROOT / "docs" / "operations" / "ATHANOR-ECOSYSTEM-REGISTRY.md"
        ).read_text(encoding="utf-8")
        ecosystem_registry_rows = _parse_ecosystem_registry_rows(ecosystem_registry_text)
        ecosystem_repo_map = {
            str(entry.get("github_repo") or "").strip(): entry
            for entry in ecosystem_registry_rows
            if str(entry.get("github_repo") or "").strip()
        }
        if portfolio_repo_set != set(ecosystem_repo_map):
            missing_from_portfolio = sorted(set(ecosystem_repo_map) - portfolio_repo_set)
            missing_from_doc = sorted(portfolio_repo_set - set(ecosystem_repo_map))
            if missing_from_portfolio:
                errors.append(
                    "reconciliation-source-registry.json github_portfolio is missing ecosystem-registry repos: "
                    + ", ".join(missing_from_portfolio)
                )
            if missing_from_doc:
                errors.append(
                    "ATHANOR-ECOSYSTEM-REGISTRY.md is missing github_portfolio repos: "
                    + ", ".join(missing_from_doc)
                )

        ecosystem_role_counts = Counter(
            str(entry.get("ecosystem_role") or "")
            for entry in ecosystem_registry_rows
            if str(entry.get("ecosystem_role") or "") in ALLOWED_ECOSYSTEM_ROLES
        )
        if role_counts_value != dict(sorted(ecosystem_role_counts.items())):
            errors.append(
                "ATHANOR-ECOSYSTEM-REGISTRY.md role counts do not match github_portfolio role_counts"
            )

        for repo_name, row in ecosystem_repo_map.items():
            portfolio_row = next((entry for entry in github_portfolio_repos if str(entry.get("github_repo") or "") == repo_name), None)
            if portfolio_row is None:
                continue
            for portfolio_field, doc_field in (
                ("ecosystem_role", "ecosystem_role"),
                ("working_clone", "working_clone"),
                ("likely_tenant_status", "likely_tenant_status"),
                ("batch", "Batch"),
                ("shaun_decision", "shaun_decision"),
            ):
                if str(portfolio_row.get(portfolio_field) or "").strip() != str(row.get(doc_field) or "").strip():
                    errors.append(
                        "reconciliation-source-registry.json github_portfolio does not match ATHANOR-ECOSYSTEM-REGISTRY.md "
                        f"for {repo_name} field {portfolio_field}"
                    )

        if not GITHUB_PORTFOLIO_SNAPSHOT_PATH.exists():
            errors.append("reports/reconciliation/github-portfolio-latest.json is missing")
        else:
            github_portfolio_snapshot = json.loads(GITHUB_PORTFOLIO_SNAPSHOT_PATH.read_text(encoding="utf-8"))
            if github_portfolio_snapshot != github_portfolio:
                errors.append(
                    "reports/reconciliation/github-portfolio-latest.json must match reconciliation-source-registry.json github_portfolio"
                )

    tenant_family_roots = [
        dict(entry)
        for entry in reconciliation_source_entries
        if str(entry.get("ecosystem_role") or "") == "tenant" and not str(entry.get("duplicate_of") or "").strip()
    ]
    tenant_family_roots_with_members = {
        str(root.get("id") or ""): root
        for root in tenant_family_roots
        if any(str(entry.get("duplicate_of") or "").strip() == str(root.get("id") or "").strip() for entry in reconciliation_source_entries)
    }
    if not TENANT_FAMILY_AUDIT_PATH.exists():
        errors.append("reports/reconciliation/tenant-family-audit-latest.json is missing")
    else:
        tenant_family_audit = json.loads(TENANT_FAMILY_AUDIT_PATH.read_text(encoding="utf-8"))
        families = [dict(entry) for entry in tenant_family_audit.get("families", []) if isinstance(entry, dict)]
        if tenant_family_audit.get("family_count") != len(families):
            errors.append("tenant-family-audit-latest.json family_count must match families length")
        family_map = {
            str(family.get("root_id") or "").strip(): family
            for family in families
            if str(family.get("root_id") or "").strip()
        }
        if set(family_map) != set(tenant_family_roots_with_members):
            errors.append(
                "tenant-family-audit-latest.json roots must match tenant families with duplicate members from reconciliation-source-registry.json"
            )
        allowed_direct_replay_risks = {"high", "low", "not-applicable", "unknown"}
        for root_id, root_entry in tenant_family_roots_with_members.items():
            family = family_map.get(root_id)
            if family is None:
                continue
            if str(family.get("root_authority_status") or "") != str(root_entry.get("authority_status") or ""):
                errors.append(f"tenant-family-audit-latest.json root {root_id} authority status must match source registry")
            if str(family.get("root_review_status") or "") != str(root_entry.get("review_status") or ""):
                errors.append(f"tenant-family-audit-latest.json root {root_id} review status must match source registry")
            if str(family.get("root_default_disposition") or "") != str(root_entry.get("default_disposition") or ""):
                errors.append(f"tenant-family-audit-latest.json root {root_id} default disposition must match source registry")
            if str(family.get("root_preservation_status") or "") != str(root_entry.get("preservation_status") or ""):
                errors.append(f"tenant-family-audit-latest.json root {root_id} preservation status must match source registry")
            if bool(family.get("root_shaun_decision_required")) != bool(root_entry.get("shaun_decision_required")):
                errors.append(f"tenant-family-audit-latest.json root {root_id} Shaun-decision flag must match source registry")
            if list(family.get("root_notes") or []) != list(root_entry.get("notes") or []):
                errors.append(f"tenant-family-audit-latest.json root {root_id} notes must match source registry")

            member_entries = [
                dict(entry)
                for entry in reconciliation_source_entries
                if str(entry.get("duplicate_of") or "").strip() == root_id
            ]
            member_map = {str(entry.get("id") or "").strip(): entry for entry in member_entries}
            audit_members = [dict(entry) for entry in family.get("members", []) if isinstance(entry, dict)]
            audit_member_map = {str(entry.get("id") or "").strip(): entry for entry in audit_members if str(entry.get("id") or "").strip()}
            if set(audit_member_map) != set(member_map):
                errors.append(f"tenant-family-audit-latest.json family {root_id} members must match source registry duplicates")

            risk_rows = [dict(entry) for entry in family.get("direct_replay_risk_summary", []) if isinstance(entry, dict)]
            risk_map = {str(entry.get("id") or "").strip(): entry for entry in risk_rows if str(entry.get("id") or "").strip()}
            if set(risk_map) != set(member_map):
                errors.append(f"tenant-family-audit-latest.json family {root_id} direct replay risk rows must match family members")

            for member_id, member_entry in member_map.items():
                audit_member = audit_member_map.get(member_id)
                if audit_member is None:
                    continue
                for field in (
                    "authority_status",
                    "review_status",
                    "default_disposition",
                    "preservation_status",
                ):
                    if str(audit_member.get(field) or "") != str(member_entry.get(field) or ""):
                        errors.append(
                            f"tenant-family-audit-latest.json member {member_id} field {field} must match source registry"
                        )
                if bool(audit_member.get("shaun_decision_required")) != bool(member_entry.get("shaun_decision_required")):
                    errors.append(
                        f"tenant-family-audit-latest.json member {member_id} Shaun-decision flag must match source registry"
                    )
                if list(audit_member.get("notes") or []) != list(member_entry.get("notes") or []):
                    errors.append(f"tenant-family-audit-latest.json member {member_id} notes must match source registry")

                risk_row = risk_map.get(member_id)
                if risk_row is None:
                    continue
                risk_value = str(risk_row.get("direct_replay_risk") or "")
                if risk_value not in allowed_direct_replay_risks:
                    errors.append(
                        f"tenant-family-audit-latest.json member {member_id} has invalid direct_replay_risk {risk_value!r}"
                    )
                overlap_paths = risk_row.get("overlapping_dirty_paths", [])
                if not isinstance(overlap_paths, list) or not all(str(item).strip() for item in overlap_paths):
                    if overlap_paths != []:
                        errors.append(
                            f"tenant-family-audit-latest.json member {member_id} overlapping_dirty_paths must be a string list"
                        )

    if not FIELD_INSPECT_REPLAY_PACKET_REPORT_PATH.exists():
        errors.append("reports/reconciliation/field-inspect-operations-runtime-replay-latest.json is missing")
    else:
        replay_packet_report = json.loads(FIELD_INSPECT_REPLAY_PACKET_REPORT_PATH.read_text(encoding="utf-8"))
        if str(replay_packet_report.get("field_inspect_root") or "") != r"C:\Field Inspect":
            errors.append("field-inspect-operations-runtime-replay-latest.json must target C:\\Field Inspect")
        if str(replay_packet_report.get("primary_branch") or "") != "codex/perpetual-coo-loop":
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json primary_branch must be codex/perpetual-coo-loop"
            )
        if str(replay_packet_report.get("replay_branch") or "") != "codex/reconcile-operations-runtime":
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json replay_branch must be codex/reconcile-operations-runtime"
            )
        execution_posture = str(replay_packet_report.get("execution_posture") or "")
        if execution_posture not in ALLOWED_FIELD_INSPECT_REPLAY_EXECUTION_POSTURES:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture must be one of: "
                + ", ".join(sorted(ALLOWED_FIELD_INSPECT_REPLAY_EXECUTION_POSTURES))
            )
        overlap_paths = replay_packet_report.get("overlap_paths", [])
        if not isinstance(overlap_paths, list) or not all(str(item).strip() for item in overlap_paths):
            errors.append("field-inspect-operations-runtime-replay-latest.json overlap_paths must be a string list")
            overlap_paths = []
        overlap_count = replay_packet_report.get("overlap_count")
        if not isinstance(overlap_count, int) or overlap_count < 0:
            errors.append("field-inspect-operations-runtime-replay-latest.json overlap_count must be a non-negative integer")
        elif overlap_count != len(overlap_paths):
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json overlap_count must match overlap_paths length"
            )
        safe_runtime_overlap_paths = replay_packet_report.get("safe_runtime_overlap_paths", [])
        if not isinstance(safe_runtime_overlap_paths, list) or not all(str(item).strip() for item in safe_runtime_overlap_paths):
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json safe_runtime_overlap_paths must be a string list"
            )
            safe_runtime_overlap_paths = []
        safe_runtime_overlap_count = replay_packet_report.get("safe_runtime_overlap_count")
        if not isinstance(safe_runtime_overlap_count, int) or safe_runtime_overlap_count < 0:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json safe_runtime_overlap_count must be a non-negative integer"
            )
        elif safe_runtime_overlap_count != len(safe_runtime_overlap_paths):
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json safe_runtime_overlap_count must match safe_runtime_overlap_paths length"
            )
        if execution_posture == "ready_for_safe_replay" and overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture ready_for_safe_replay requires overlap_paths to be empty"
            )
        if execution_posture == "ready_for_safe_replay" and safe_runtime_overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture ready_for_safe_replay requires safe_runtime_overlap_paths to be empty"
            )
        if execution_posture == "ready_for_safe_runtime_only" and not overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture ready_for_safe_runtime_only requires overlap_paths"
            )
        if execution_posture == "ready_for_safe_runtime_only" and safe_runtime_overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture ready_for_safe_runtime_only requires safe_runtime_overlap_paths to be empty"
            )
        if execution_posture == "blocked_by_overlap" and not overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture blocked_by_overlap requires overlap_paths"
            )
        if execution_posture == "blocked_by_overlap" and not safe_runtime_overlap_paths:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json execution_posture blocked_by_overlap requires safe_runtime_overlap_paths"
            )
        bucket_counts = replay_packet_report.get("bucket_counts", {})
        buckets = replay_packet_report.get("buckets", {})
        required_replay_buckets = {
            "safe_operations_runtime_replay",
            "shared_project_follow_through_hold",
            "secondary_cross_surface_review",
            "docs_meta_reference",
            "blocked_overlap",
        }
        if set(buckets) != required_replay_buckets:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json buckets must match the required replay bucket set"
            )
        if set(bucket_counts) != required_replay_buckets:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json bucket_counts must match the required replay bucket set"
            )
        else:
            for bucket_name in required_replay_buckets:
                bucket_paths = buckets.get(bucket_name, [])
                if not isinstance(bucket_paths, list) or not all(str(item).strip() for item in bucket_paths):
                    errors.append(
                        f"field-inspect-operations-runtime-replay-latest.json bucket {bucket_name} must be a string list"
                    )
                    continue
                if bucket_counts.get(bucket_name) != len(bucket_paths):
                    errors.append(
                        f"field-inspect-operations-runtime-replay-latest.json bucket_counts[{bucket_name}] must match the bucket length"
                    )
        validation_commands = replay_packet_report.get("targeted_validation_commands", [])
        if not isinstance(validation_commands, list) or len(validation_commands) < 2:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json targeted_validation_commands must declare at least two commands"
            )

        reconciliation_source_map = {
            str(entry.get("id") or "").strip(): dict(entry) for entry in reconciliation_source_entries
        }
        ops_lane_entry = reconciliation_source_map.get("field-inspect-operations-runtime")
        if ops_lane_entry is None:
            errors.append(
                "field-inspect-operations-runtime-replay-latest.json requires field-inspect-operations-runtime in reconciliation-source-registry.json"
            )
        else:
            if str(ops_lane_entry.get("default_disposition") or "") != "tenant-queue":
                errors.append(
                    "field-inspect-operations-runtime must remain tenant-queue while the replay packet is active"
                )
            if str(ops_lane_entry.get("review_status") or "") != "completed":
                errors.append(
                    "field-inspect-operations-runtime must stay review_status=completed once the replay packet is generated"
                )

    if not RFI_HERS_DUPLICATE_EVIDENCE_PACKET_REPORT_PATH.exists():
        errors.append("reports/reconciliation/rfi-hers-duplicate-evidence-packet-latest.json is missing")
    else:
        rfi_packet_report = json.loads(RFI_HERS_DUPLICATE_EVIDENCE_PACKET_REPORT_PATH.read_text(encoding="utf-8"))
        if str(rfi_packet_report.get("family_root_id") or "") != "rfi-hers-rater-assistant-root":
            errors.append(
                "rfi-hers-duplicate-evidence-packet-latest.json family_root_id must be rfi-hers-rater-assistant-root"
            )
        variant_entries = rfi_packet_report.get("variants", [])
        if not isinstance(variant_entries, list) or len(variant_entries) != 3:
            errors.append(
                "rfi-hers-duplicate-evidence-packet-latest.json variants must contain the three duplicate-tree entries"
            )
            variant_entries = []
        expected_variant_ids = {
            "codexbuild-rfi-hers-rater-assistant",
            "codexbuild-rfi-hers-rater-assistant-safe",
            "codexbuild-rfi-hers-rater-assistant-v2",
        }
        variant_ids = {str(entry.get("id") or "") for entry in variant_entries if isinstance(entry, dict)}
        if variant_ids != expected_variant_ids:
            errors.append(
                "rfi-hers-duplicate-evidence-packet-latest.json variants must match the governed RFI duplicate ids"
            )
        reconciliation_source_map = {
            str(entry.get("id") or "").strip(): dict(entry) for entry in reconciliation_source_entries
        }
        for variant in variant_entries:
            if not isinstance(variant, dict):
                continue
            variant_id = str(variant.get("id") or "")
            source_entry = reconciliation_source_map.get(variant_id)
            if source_entry is None:
                errors.append(
                    f"rfi-hers-duplicate-evidence-packet-latest.json variant {variant_id} is missing from reconciliation-source-registry.json"
                )
                continue
            if str(source_entry.get("authority_status") or "") != "non-authoritative":
                errors.append(f"{variant_id} must remain non-authoritative while the duplicate-evidence packet is active")
            if str(source_entry.get("default_disposition") or "") != "archive":
                errors.append(f"{variant_id} must remain archive while the duplicate-evidence packet is active")
            for field_name in (
                "preserve_archive_evidence",
                "superseded_by_root",
                "disposable_artifacts",
                "unclassified_artifacts",
            ):
                value = variant.get(field_name)
                if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                    errors.append(
                        f"rfi-hers-duplicate-evidence-packet-latest.json variant {variant_id} field {field_name} must be a string list"
                    )
            if list(variant.get("unclassified_artifacts") or []):
                errors.append(
                    f"rfi-hers-duplicate-evidence-packet-latest.json variant {variant_id} has unclassified artifacts"
                )
            if not list(variant.get("preserve_archive_evidence") or []):
                errors.append(
                    f"rfi-hers-duplicate-evidence-packet-latest.json variant {variant_id} must preserve at least one archive evidence artifact"
                )

    if not RFI_HERS_PRIMARY_ROOT_STABILIZATION_REPORT_PATH.exists():
        errors.append("reports/reconciliation/rfi-hers-primary-root-stabilization-latest.json is missing")
    else:
        rfi_root_report = json.loads(RFI_HERS_PRIMARY_ROOT_STABILIZATION_REPORT_PATH.read_text(encoding="utf-8"))
        if str(rfi_root_report.get("root_id") or "") != "rfi-hers-rater-assistant-root":
            errors.append(
                "rfi-hers-primary-root-stabilization-latest.json root_id must be rfi-hers-rater-assistant-root"
            )
        if str(rfi_root_report.get("root_path") or "") != r"C:\RFI & HERS Rater Assistant":
            errors.append(
                "rfi-hers-primary-root-stabilization-latest.json must target C:\\RFI & HERS Rater Assistant"
            )
        execution_posture = str(rfi_root_report.get("execution_posture") or "")
        if execution_posture not in ALLOWED_RFI_PRIMARY_ROOT_EXECUTION_POSTURES:
            errors.append(
                "rfi-hers-primary-root-stabilization-latest.json execution_posture must be one of: "
                + ", ".join(sorted(ALLOWED_RFI_PRIMARY_ROOT_EXECUTION_POSTURES))
            )
        for required_field in (
            "authority_status",
            "review_status",
            "default_disposition",
            "preservation_status",
            "branch",
            "head",
        ):
            if not str(rfi_root_report.get(required_field) or "").strip():
                errors.append(
                    f"rfi-hers-primary-root-stabilization-latest.json is missing {required_field}"
                )
        for count_field in ("dirty_file_count", "tracked_dirty_count", "untracked_count"):
            if not isinstance(rfi_root_report.get(count_field), int):
                errors.append(
                    f"rfi-hers-primary-root-stabilization-latest.json {count_field} must be an integer"
                )
        for list_field in (
            "dirty_paths",
            "tracked_dirty_paths",
            "untracked_paths",
            "validation_commands",
            "rules",
            "recommended_tranche_order",
        ):
            value = rfi_root_report.get(list_field)
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                errors.append(
                    f"rfi-hers-primary-root-stabilization-latest.json field {list_field} must be a string list"
                )
        bucket_counts = rfi_root_report.get("bucket_counts", {})
        buckets = rfi_root_report.get("buckets", {})
        required_rfi_buckets = {
            "repo_contracts_and_meta",
            "docs_and_runbooks",
            "canonical_project_data",
            "generators_and_importers",
            "workbook_outputs",
            "operator_residue",
        }
        if set(bucket_counts) != required_rfi_buckets:
            errors.append(
                "rfi-hers-primary-root-stabilization-latest.json bucket_counts must match the required bucket set"
            )
        if set(buckets) != required_rfi_buckets:
            errors.append(
                "rfi-hers-primary-root-stabilization-latest.json buckets must match the required bucket set"
            )
        else:
            for bucket_name in required_rfi_buckets:
                bucket_paths = buckets.get(bucket_name, [])
                if not isinstance(bucket_paths, list) or not all(isinstance(item, str) and item.strip() for item in bucket_paths):
                    errors.append(
                        f"rfi-hers-primary-root-stabilization-latest.json bucket {bucket_name} must be a string list"
                    )
                    continue
                if bucket_counts.get(bucket_name) != len(bucket_paths):
                    errors.append(
                        f"rfi-hers-primary-root-stabilization-latest.json bucket_counts[{bucket_name}] must match the bucket length"
                    )
        root_source_entry = next(
            (
                dict(entry)
                for entry in reconciliation_source_entries
                if str(entry.get("id") or "") == "rfi-hers-rater-assistant-root"
            ),
            None,
        )
        if root_source_entry is None:
            errors.append(
                "reconciliation-source-registry.json must contain rfi-hers-rater-assistant-root while the primary-root stabilization packet is active"
            )
        else:
            for report_field, source_field in (
                ("authority_status", "authority_status"),
                ("review_status", "review_status"),
                ("default_disposition", "default_disposition"),
                ("preservation_status", "preservation_status"),
            ):
                if str(rfi_root_report.get(report_field) or "") != str(root_source_entry.get(source_field) or ""):
                    errors.append(
                        "rfi-hers-primary-root-stabilization-latest.json does not match reconciliation-source-registry.json "
                        f"for field {report_field}"
                    )

    if str(completion_program.get("source_of_truth") or "") != "config/automation-backbone/completion-program-registry.json":
        errors.append(
            "completion-program-registry.json source_of_truth must be config/automation-backbone/completion-program-registry.json"
        )
    if str(completion_program.get("status") or "") != "active":
        errors.append("completion-program-registry.json status must be active")
    if str(completion_program.get("program_id") or "") != "athanor-total-completion":
        errors.append("completion-program-registry.json program_id must be athanor-total-completion")
    if str(completion_program.get("tenant_depth_default") or "") != "light-tenant":
        errors.append("completion-program-registry.json tenant_depth_default must be light-tenant")

    authority_defaults = dict(completion_program.get("authority_defaults") or {})
    if str(authority_defaults.get("implementation_root") or "") != "C:\\Athanor":
        errors.append("completion-program-registry.json implementation_root must be C:\\Athanor")
    if str(authority_defaults.get("runtime_root") or "") != "/home/shaun/repos/athanor":
        errors.append("completion-program-registry.json runtime_root must be /home/shaun/repos/athanor")
    if str(authority_defaults.get("runtime_node") or "") != "dev":
        errors.append("completion-program-registry.json runtime_node must be dev")

    if set(str(item) for item in completion_program.get("workstream_statuses", [])) != ALLOWED_COMPLETION_WORKSTREAM_STATUSES:
        errors.append("completion-program-registry.json workstream_statuses must match the allowed workstream-status set")
    if set(str(item) for item in completion_program.get("checkpoint_statuses", [])) != ALLOWED_COMPLETION_CHECKPOINT_STATUSES:
        errors.append("completion-program-registry.json checkpoint_statuses must match the allowed checkpoint-status set")
    if set(str(item) for item in completion_program.get("loop_execution_states", [])) != ALLOWED_COMPLETION_LOOP_EXECUTION_STATES:
        errors.append("completion-program-registry.json loop_execution_states must match the allowed loop-execution-state set")
    if set(str(item) for item in completion_program.get("loop_blocker_types", [])) != ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES:
        errors.append("completion-program-registry.json loop_blocker_types must match the allowed loop-blocker-type set")
    if set(str(item) for item in completion_program.get("priority_levels", [])) != ALLOWED_COMPLETION_PRIORITY_LEVELS:
        errors.append("completion-program-registry.json priority_levels must match the allowed priority set")

    publication_slices = dict(completion_program.get("publication_slices") or {})
    if str(publication_slices.get("owner_workstream_id") or "") != "validation-and-publication":
        errors.append("completion-program-registry.json publication_slices.owner_workstream_id must be validation-and-publication")
    if str(publication_slices.get("checkpoint_id") or "") != "final-publication-and-freeze":
        errors.append("completion-program-registry.json publication_slices.checkpoint_id must be final-publication-and-freeze")
    if str(publication_slices.get("source_doc") or "") != "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md":
        errors.append("completion-program-registry.json publication_slices.source_doc must be docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md")
    if not str(publication_slices.get("active_sequence_id") or "").strip():
        errors.append("completion-program-registry.json publication_slices.active_sequence_id is missing")
    slice_statuses = set(str(item) for item in publication_slices.get("slice_statuses", []))
    if slice_statuses != ALLOWED_PUBLICATION_SLICE_STATUSES:
        errors.append("completion-program-registry.json publication_slices.slice_statuses must match the allowed publication-slice status set")
    publication_rules = publication_slices.get("rules", [])
    if not isinstance(publication_rules, list) or len(publication_rules) != 3 or not all(str(item).strip() for item in publication_rules):
        errors.append("completion-program-registry.json publication_slices.rules must be a 3-item non-empty string list")

    deferred_family_entries = [
        dict(entry) for entry in publication_slices.get("deferred_families", []) if isinstance(entry, dict)
    ]
    if not deferred_family_entries:
        errors.append("completion-program-registry.json publication_slices.deferred_families must be a non-empty object list")
    deferred_family_ids = [str(entry.get("id") or "").strip() for entry in deferred_family_entries]
    if len(deferred_family_ids) != len(set(item for item in deferred_family_ids if item)):
        errors.append("completion-program-registry.json publication_slices.deferred_families contains duplicate ids")
    for entry in deferred_family_entries:
        family_id = str(entry.get("id") or "").strip()
        if not family_id:
            errors.append("completion-program-registry.json publication_slices.deferred_families contains an entry without id")
            continue
        if not str(entry.get("title") or "").strip():
            errors.append(f"completion-program-registry.json publication deferred family {family_id} is missing title")
        if not str(entry.get("scope") or "").strip():
            errors.append(f"completion-program-registry.json publication deferred family {family_id} is missing scope")
        if str(entry.get("disposition") or "") not in ALLOWED_PUBLICATION_DEFERRED_DISPOSITIONS:
            errors.append(
                f"completion-program-registry.json publication deferred family {family_id} has invalid disposition {entry.get('disposition')!r}"
            )
        if int(entry.get("execution_rank") or 0) <= 0:
            errors.append(
                f"completion-program-registry.json publication deferred family {family_id} must declare a positive execution_rank"
            )
        if str(entry.get("execution_class") or "") not in ALLOWED_PUBLICATION_DEFERRED_EXECUTION_CLASSES:
            errors.append(
                f"completion-program-registry.json publication deferred family {family_id} has invalid execution_class {entry.get('execution_class')!r}"
            )
        if not str(entry.get("next_action") or "").strip():
            errors.append(f"completion-program-registry.json publication deferred family {family_id} is missing next_action")
        if not str(entry.get("success_condition") or "").strip():
            errors.append(f"completion-program-registry.json publication deferred family {family_id} is missing success_condition")
        owner_workstreams = entry.get("owner_workstreams", [])
        if not isinstance(owner_workstreams, list) or not owner_workstreams or not all(str(item).strip() for item in owner_workstreams):
            errors.append(
                f"completion-program-registry.json publication deferred family {family_id} owner_workstreams must be a non-empty string list"
            )
        else:
            for owner_workstream in owner_workstreams:
                if str(owner_workstream) not in REQUIRED_COMPLETION_WORKSTREAM_IDS:
                    errors.append(
                        f"completion-program-registry.json publication deferred family {family_id} references unknown owner_workstream {owner_workstream!r}"
                    )
        path_hints = entry.get("path_hints", [])
        if not isinstance(path_hints, list) or not path_hints or not all(str(item).strip() for item in path_hints):
            errors.append(
                f"completion-program-registry.json publication deferred family {family_id} path_hints must be a non-empty string list"
            )

    publication_slice_entries = [
        dict(entry) for entry in publication_slices.get("slices", []) if isinstance(entry, dict)
    ]
    publication_slice_ids = [str(entry.get("id") or "").strip() for entry in publication_slice_entries]
    if publication_slice_ids != REQUIRED_PUBLICATION_SLICE_IDS:
        errors.append(
            "completion-program-registry.json publication_slices.slices must contain the required slice ids in order: "
            + ", ".join(REQUIRED_PUBLICATION_SLICE_IDS)
        )
    for expected_order, entry in enumerate(publication_slice_entries, start=1):
        slice_id = str(entry.get("id") or "").strip()
        if not slice_id:
            errors.append("completion-program-registry.json publication_slices contains a slice without id")
            continue
        if str(entry.get("status") or "") not in ALLOWED_PUBLICATION_SLICE_STATUSES:
            errors.append(
                f"completion-program-registry.json publication_slices slice {slice_id} has invalid status {entry.get('status')!r}"
            )
        if int(entry.get("order") or 0) != expected_order:
            errors.append(
                f"completion-program-registry.json publication_slices slice {slice_id} must have order {expected_order}"
            )
        if not str(entry.get("title") or "").strip():
            errors.append(f"completion-program-registry.json publication_slices slice {slice_id} is missing title")
        if not str(entry.get("scope") or "").strip():
            errors.append(f"completion-program-registry.json publication_slices slice {slice_id} is missing scope")
        if not str(entry.get("blocking_gate") or "").strip():
            errors.append(f"completion-program-registry.json publication_slices slice {slice_id} is missing blocking_gate")
        dependencies = entry.get("dependencies", [])
        if not isinstance(dependencies, list):
            errors.append(
                f"completion-program-registry.json publication_slices slice {slice_id} dependencies must be a list"
            )
        elif any(str(dependency).strip() not in REQUIRED_PUBLICATION_SLICE_IDS for dependency in dependencies):
            errors.append(
                f"completion-program-registry.json publication_slices slice {slice_id} has unknown dependency ids"
            )
        owner_workstreams = entry.get("owner_workstreams", [])
        if not isinstance(owner_workstreams, list) or not all(str(item).strip() for item in owner_workstreams):
            errors.append(
                f"completion-program-registry.json publication_slices slice {slice_id} owner_workstreams must be a non-empty string list"
            )
        else:
            for owner_workstream in owner_workstreams:
                if str(owner_workstream) not in REQUIRED_COMPLETION_WORKSTREAM_IDS:
                    errors.append(
                        f"completion-program-registry.json publication_slices slice {slice_id} references unknown owner_workstream {owner_workstream!r}"
                    )
        for list_field in ("publication_artifact_refs", "generated_artifacts", "validator_run_set", "working_tree_path_hints"):
            values = entry.get(list_field, [])
            if not isinstance(values, list) or not all(str(item).strip() for item in values):
                errors.append(
                    f"completion-program-registry.json publication_slices slice {slice_id} {list_field} must be a non-empty string list"
                )
                continue
            if list_field in {"publication_artifact_refs", "working_tree_path_hints"} and not values:
                errors.append(
                    f"completion-program-registry.json publication_slices slice {slice_id} must declare {list_field}"
                )

    loop_family_entries = [
        dict(entry) for entry in completion_program.get("loop_families", []) if isinstance(entry, dict)
    ]
    if not loop_family_entries:
        errors.append("completion-program-registry.json must declare loop_families")
    loop_family_ids = [str(entry.get("id") or "").strip() for entry in loop_family_entries]
    if len(loop_family_ids) != len(set(loop_family_ids)):
        errors.append("completion-program-registry.json contains duplicate loop_families ids")
    missing_loop_family_ids = sorted(
        required_id
        for required_id in REQUIRED_COMPLETION_LOOP_FAMILY_IDS
        if required_id not in set(loop_family_ids)
    )
    if missing_loop_family_ids:
        errors.append(
            "completion-program-registry.json is missing required loop_families ids: "
            + ", ".join(missing_loop_family_ids)
        )
    for entry in loop_family_entries:
        loop_family_id = str(entry.get("id") or "").strip()
        if not loop_family_id:
            errors.append("completion-program-registry.json contains a loop_family without id")
            continue
        if not str(entry.get("title") or "").strip():
            errors.append(f"completion-program-registry.json loop_family {loop_family_id} is missing title")
        if not str(entry.get("description") or "").strip():
            errors.append(f"completion-program-registry.json loop_family {loop_family_id} is missing description")
        if not isinstance(entry.get("approval_sensitive"), bool):
            errors.append(f"completion-program-registry.json loop_family {loop_family_id} must set boolean approval_sensitive")

    ralph_loop = dict(completion_program.get("ralph_loop") or {})
    if str(ralph_loop.get("status") or "") != "active":
        errors.append("completion-program-registry.json ralph_loop.status must be active")
    if str(ralph_loop.get("current_phase_scope") or "") != str(autonomy_activation.get("current_phase_id") or ""):
        errors.append("completion-program-registry.json ralph_loop.current_phase_scope must match autonomy-activation-registry current_phase_id")
    if str(ralph_loop.get("controller_script") or "") != "scripts/run_ralph_loop_pass.py":
        errors.append("completion-program-registry.json ralph_loop.controller_script must be scripts/run_ralph_loop_pass.py")
    if str(ralph_loop.get("report_path") or "") != "reports/ralph-loop/latest.json":
        errors.append("completion-program-registry.json ralph_loop.report_path must be reports/ralph-loop/latest.json")
    if str(ralph_loop.get("current_loop_family") or "") not in REQUIRED_COMPLETION_LOOP_FAMILY_IDS:
        errors.append("completion-program-registry.json ralph_loop.current_loop_family must be a known loop_family id")
    if str(ralph_loop.get("selected_workstream") or "") not in REQUIRED_COMPLETION_WORKSTREAM_IDS:
        errors.append("completion-program-registry.json ralph_loop.selected_workstream must be a known required workstream id")
    if str(ralph_loop.get("blocker_type") or "") not in ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES:
        errors.append("completion-program-registry.json ralph_loop.blocker_type must be a valid loop blocker type")
    if not str(ralph_loop.get("next_action_family") or "").strip():
        errors.append("completion-program-registry.json ralph_loop.next_action_family is missing")
    if not str(ralph_loop.get("approval_status") or "").strip():
        errors.append("completion-program-registry.json ralph_loop.approval_status is missing")
    if not str(ralph_loop.get("last_validation_run") or "").strip():
        errors.append("completion-program-registry.json ralph_loop.last_validation_run is missing")
    if str(ralph_loop.get("execution_posture") or "") not in {"active_remediation", "steady_state"}:
        errors.append("completion-program-registry.json ralph_loop.execution_posture must be active_remediation or steady_state")

    continuity_policy = dict(completion_program.get("continuity_policy") or {})
    if not continuity_policy:
        errors.append("completion-program-registry.json continuity_policy is missing")
    else:
        if int(continuity_policy.get("no_delta_suppression_ttl_hours") or 0) <= 0:
            errors.append("completion-program-registry.json continuity_policy.no_delta_suppression_ttl_hours must be > 0")
        feeder_precedence = [
            str(item).strip()
            for item in continuity_policy.get("feeder_precedence", [])
            if str(item).strip()
        ]
        if not feeder_precedence:
            errors.append("completion-program-registry.json continuity_policy.feeder_precedence must be a non-empty list")
        elif "cash_now_deferred_family" not in feeder_precedence:
            errors.append("completion-program-registry.json continuity_policy.feeder_precedence must include cash_now_deferred_family")
        elif "burn_class" not in feeder_precedence:
            errors.append("completion-program-registry.json continuity_policy.feeder_precedence must include burn_class")
        elif feeder_precedence.index("cash_now_deferred_family") > feeder_precedence.index("burn_class"):
            errors.append(
                "completion-program-registry.json continuity_policy.feeder_precedence must rank cash_now_deferred_family ahead of burn_class"
            )
        hard_brakes = {
            str(item).strip()
            for item in continuity_policy.get("hard_brakes", [])
            if str(item).strip()
        }
        missing_hard_brakes = sorted(ALLOWED_RALPH_CONTINUITY_STOP_STATES - {"none"} - hard_brakes)
        if missing_hard_brakes:
            errors.append(
                "completion-program-registry.json continuity_policy.hard_brakes is missing: " + ", ".join(missing_hard_brakes)
            )
        if continuity_policy.get("cash_now_deferred_families_are_autonomous_inputs") is not True:
            errors.append("completion-program-registry.json continuity_policy.cash_now_deferred_families_are_autonomous_inputs must be true")
        if continuity_policy.get("cash_now_requires_no_unsuppressed_workstream") is not True:
            errors.append("completion-program-registry.json continuity_policy.cash_now_requires_no_unsuppressed_workstream must be true")
        if continuity_policy.get("green_not_stop_condition") is not True:
            errors.append("completion-program-registry.json continuity_policy.green_not_stop_condition must be true")

    role_ids = {
        str(item.get("id") or "").strip()
        for item in operating_system.get("roles", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    workstream_entries = [
        dict(entry) for entry in completion_program.get("workstreams", []) if isinstance(entry, dict)
    ]
    if not workstream_entries:
        errors.append("completion-program-registry.json must declare at least one workstream")
    workstream_ids = [str(entry.get("id") or "").strip() for entry in workstream_entries]
    if len(workstream_ids) != len(set(workstream_ids)):
        errors.append("completion-program-registry.json contains duplicate workstream ids")
    missing_workstream_ids = sorted(
        required_id
        for required_id in REQUIRED_COMPLETION_WORKSTREAM_IDS
        if required_id not in set(workstream_ids)
    )
    if missing_workstream_ids:
        errors.append(
            "completion-program-registry.json is missing required workstream ids: "
            + ", ".join(missing_workstream_ids)
        )

    for entry in workstream_entries:
        workstream_id = str(entry.get("id") or "").strip()
        if not workstream_id:
            errors.append("completion-program-registry.json contains a workstream without id")
            continue
        if str(entry.get("status") or "") not in ALLOWED_COMPLETION_WORKSTREAM_STATUSES:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has invalid status {entry.get('status')!r}"
            )
        if str(entry.get("priority") or "") not in ALLOWED_COMPLETION_PRIORITY_LEVELS:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has invalid priority {entry.get('priority')!r}"
            )
        owner_role = str(entry.get("owner_role") or "").strip()
        if owner_role not in role_ids:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has unknown owner_role {owner_role!r}"
            )
        if str(entry.get("loop_family") or "") not in REQUIRED_COMPLETION_LOOP_FAMILY_IDS:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has invalid loop_family {entry.get('loop_family')!r}"
            )
        if str(entry.get("execution_state") or "") not in ALLOWED_COMPLETION_LOOP_EXECUTION_STATES:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has invalid execution_state {entry.get('execution_state')!r}"
            )
        if str(entry.get("blocker_type") or "") not in ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES:
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} has invalid blocker_type {entry.get('blocker_type')!r}"
            )
        if not isinstance(entry.get("approval_required"), bool):
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} must set boolean approval_required"
            )
        if not str(entry.get("next_action_family") or "").strip():
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} is missing next_action_family"
            )
        for field_name in ("title", "objective"):
            if not str(entry.get(field_name) or "").strip():
                errors.append(
                    f"completion-program-registry.json workstream {workstream_id} is missing {field_name}"
                )
        dependencies = entry.get("dependencies", [])
        if not isinstance(dependencies, list):
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} dependencies must be a list"
            )
        primary_artifacts = entry.get("primary_artifacts", [])
        if not isinstance(primary_artifacts, list) or not all(str(item).strip() for item in primary_artifacts):
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} primary_artifacts must be a non-empty string list"
            )
        else:
            for artifact in primary_artifacts:
                artifact_path = REPO_ROOT / str(artifact)
                if not artifact_path.exists():
                    errors.append(
                        f"completion-program-registry.json workstream {workstream_id} artifact is missing: {artifact}"
                    )
        evidence_artifacts = entry.get("evidence_artifacts", [])
        if not isinstance(evidence_artifacts, list) or not all(str(item).strip() for item in evidence_artifacts):
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} evidence_artifacts must be a non-empty string list"
            )
        else:
            for artifact in evidence_artifacts:
                artifact_path = REPO_ROOT / str(artifact)
                if not artifact_path.exists():
                    errors.append(
                        f"completion-program-registry.json workstream {workstream_id} evidence artifact is missing: {artifact}"
                    )
        exit_criteria = entry.get("exit_criteria", [])
        if not isinstance(exit_criteria, list) or not all(str(item).strip() for item in exit_criteria):
            errors.append(
                f"completion-program-registry.json workstream {workstream_id} exit_criteria must be a non-empty string list"
            )

    checkpoint_entries = [
        dict(entry) for entry in completion_program.get("checkpoints", []) if isinstance(entry, dict)
    ]
    if not checkpoint_entries:
        errors.append("completion-program-registry.json must declare at least one checkpoint")
    checkpoint_ids = [str(entry.get("id") or "").strip() for entry in checkpoint_entries]
    if len(checkpoint_ids) != len(set(checkpoint_ids)):
        errors.append("completion-program-registry.json contains duplicate checkpoint ids")
    missing_checkpoint_ids = sorted(
        required_id
        for required_id in REQUIRED_COMPLETION_CHECKPOINT_IDS
        if required_id not in set(checkpoint_ids)
    )
    if missing_checkpoint_ids:
        errors.append(
            "completion-program-registry.json is missing required checkpoint ids: "
            + ", ".join(missing_checkpoint_ids)
        )
    checkpoint_id_set = set(checkpoint_ids)
    for entry in checkpoint_entries:
        checkpoint_id = str(entry.get("id") or "").strip()
        if not checkpoint_id:
            errors.append("completion-program-registry.json contains a checkpoint without id")
            continue
        if str(entry.get("status") or "") not in ALLOWED_COMPLETION_CHECKPOINT_STATUSES:
            errors.append(
                f"completion-program-registry.json checkpoint {checkpoint_id} has invalid status {entry.get('status')!r}"
            )
        if not isinstance(entry.get("order"), int):
            errors.append(f"completion-program-registry.json checkpoint {checkpoint_id} must set integer order")
        for field_name in ("scope",):
            if not str(entry.get(field_name) or "").strip():
                errors.append(
                    f"completion-program-registry.json checkpoint {checkpoint_id} is missing {field_name}"
                )
        dependencies = entry.get("dependencies", [])
        if not isinstance(dependencies, list):
            errors.append(
                f"completion-program-registry.json checkpoint {checkpoint_id} dependencies must be a list"
            )
        else:
            for dependency in dependencies:
                if str(dependency) not in checkpoint_id_set:
                    errors.append(
                        f"completion-program-registry.json checkpoint {checkpoint_id} references unknown dependency {dependency!r}"
                    )
        exit_criteria = entry.get("exit_criteria", [])
        if not isinstance(exit_criteria, list) or not all(str(item).strip() for item in exit_criteria):
            errors.append(
                f"completion-program-registry.json checkpoint {checkpoint_id} exit_criteria must be a non-empty string list"
            )

    for field_name in ("standing_rules", "final_acceptance"):
        values = completion_program.get(field_name, [])
        if not isinstance(values, list) or not all(str(item).strip() for item in values):
            errors.append(
                f"completion-program-registry.json {field_name} must be a non-empty string list"
            )

    reconciliation_end_state = dict(completion_program.get("reconciliation_end_state") or {})
    if str(reconciliation_end_state.get("source_of_truth") or "") != "docs/operations/ATHANOR-RECONCILIATION-END-STATE.md":
        errors.append(
            "completion-program-registry.json reconciliation_end_state.source_of_truth must be docs/operations/ATHANOR-RECONCILIATION-END-STATE.md"
        )
    if str(reconciliation_end_state.get("status") or "") not in ALLOWED_RECONCILIATION_END_STATE_STATUSES:
        errors.append(
            "completion-program-registry.json reconciliation_end_state.status must be a valid reconciliation end-state status"
        )
    top_entry_truth_surfaces = reconciliation_end_state.get("top_entry_truth_surfaces", [])
    expected_top_entry_truth_surfaces = [
        "STATUS.md",
        "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
        "docs/operations/ATHANOR-OPERATING-SYSTEM.md",
        "config/automation-backbone/completion-program-registry.json",
        "reports/ralph-loop/latest.json",
    ]
    if top_entry_truth_surfaces != expected_top_entry_truth_surfaces:
        errors.append(
            "completion-program-registry.json reconciliation_end_state.top_entry_truth_surfaces must match the canonical top-entry truth surface order"
        )
    success_levels = [
        dict(entry) for entry in reconciliation_end_state.get("success_levels", []) if isinstance(entry, dict)
    ]
    success_level_ids = [str(entry.get("id") or "").strip() for entry in success_levels]
    if set(success_level_ids) != REQUIRED_RECONCILIATION_SUCCESS_LEVEL_IDS:
        missing = sorted(REQUIRED_RECONCILIATION_SUCCESS_LEVEL_IDS - set(success_level_ids))
        extra = sorted(set(success_level_ids) - REQUIRED_RECONCILIATION_SUCCESS_LEVEL_IDS)
        if missing:
            errors.append(
                "completion-program-registry.json reconciliation_end_state.success_levels is missing ids: "
                + ", ".join(missing)
            )
        if extra:
            errors.append(
                "completion-program-registry.json reconciliation_end_state.success_levels has unexpected ids: "
                + ", ".join(extra)
            )
    for entry in success_levels:
        for field_name in ("id", "title", "description"):
            if not str(entry.get(field_name) or "").strip():
                errors.append(
                    f"completion-program-registry.json reconciliation_end_state.success_levels entry is missing {field_name}"
                )
    project_exit_gates = [
        dict(entry) for entry in reconciliation_end_state.get("project_exit_gates", []) if isinstance(entry, dict)
    ]
    gate_ids = [str(entry.get("id") or "").strip() for entry in project_exit_gates]
    if set(gate_ids) != REQUIRED_RECONCILIATION_END_STATE_GATE_IDS:
        missing = sorted(REQUIRED_RECONCILIATION_END_STATE_GATE_IDS - set(gate_ids))
        extra = sorted(set(gate_ids) - REQUIRED_RECONCILIATION_END_STATE_GATE_IDS)
        if missing:
            errors.append(
                "completion-program-registry.json reconciliation_end_state.project_exit_gates is missing ids: "
                + ", ".join(missing)
            )
        if extra:
            errors.append(
                "completion-program-registry.json reconciliation_end_state.project_exit_gates has unexpected ids: "
                + ", ".join(extra)
            )
    workstream_id_set = set(workstream_ids)
    for entry in project_exit_gates:
        gate_id = str(entry.get("id") or "").strip()
        if not gate_id:
            errors.append("completion-program-registry.json reconciliation_end_state contains a gate without id")
            continue
        if str(entry.get("status") or "") not in ALLOWED_RECONCILIATION_END_STATE_GATE_STATUSES:
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} has invalid status {entry.get('status')!r}"
            )
        if str(entry.get("blocker_type") or "") not in ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES:
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} has invalid blocker_type {entry.get('blocker_type')!r}"
            )
        if not str(entry.get("title") or "").strip():
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} is missing title"
            )
        owner_workstreams = entry.get("owner_workstreams", [])
        if not isinstance(owner_workstreams, list) or not all(str(item).strip() for item in owner_workstreams):
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} owner_workstreams must be a non-empty string list"
            )
        else:
            for owner_workstream in owner_workstreams:
                if str(owner_workstream) not in workstream_id_set:
                    errors.append(
                        f"completion-program-registry.json reconciliation_end_state gate {gate_id} references unknown owner_workstream {owner_workstream!r}"
                    )
        evidence_paths = entry.get("evidence_paths", [])
        if not isinstance(evidence_paths, list) or not all(str(item).strip() for item in evidence_paths):
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} evidence_paths must be a non-empty string list"
            )
        else:
            for evidence_path in evidence_paths:
                if not (REPO_ROOT / str(evidence_path)).exists():
                    errors.append(
                        f"completion-program-registry.json reconciliation_end_state gate {gate_id} evidence path is missing: {evidence_path}"
                    )
        success_criteria = entry.get("success_criteria", [])
        if not isinstance(success_criteria, list) or not all(str(item).strip() for item in success_criteria):
            errors.append(
                f"completion-program-registry.json reconciliation_end_state gate {gate_id} success_criteria must be a non-empty string list"
            )
    steady_state_acceptance = dict(reconciliation_end_state.get("steady_state_acceptance") or {})
    if not isinstance(steady_state_acceptance.get("required_consecutive_clean_cycles"), int) or int(
        steady_state_acceptance.get("required_consecutive_clean_cycles")
    ) < 1:
        errors.append(
            "completion-program-registry.json reconciliation_end_state.steady_state_acceptance.required_consecutive_clean_cycles must be an integer >= 1"
        )
    if not isinstance(steady_state_acceptance.get("current_consecutive_clean_cycles"), int) or int(
        steady_state_acceptance.get("current_consecutive_clean_cycles")
    ) < 0:
        errors.append(
            "completion-program-registry.json reconciliation_end_state.steady_state_acceptance.current_consecutive_clean_cycles must be an integer >= 0"
        )
    if not isinstance(steady_state_acceptance.get("ready_to_transition"), bool):
        errors.append(
            "completion-program-registry.json reconciliation_end_state.steady_state_acceptance.ready_to_transition must be boolean"
        )
    steady_state_conditions = steady_state_acceptance.get("conditions", [])
    if not isinstance(steady_state_conditions, list) or not all(str(item).strip() for item in steady_state_conditions):
        errors.append(
            "completion-program-registry.json reconciliation_end_state.steady_state_acceptance.conditions must be a non-empty string list"
        )

    runtime_ownership_lanes = [
        dict(entry) for entry in runtime_ownership.get("lanes", []) if isinstance(entry, dict)
    ]
    lane_ids = [str(entry.get("id") or "") for entry in runtime_ownership_lanes]
    runtime_ownership_packet_entries = [
        dict(entry) for entry in runtime_ownership_packets.get("packets", []) if isinstance(entry, dict)
    ]
    runtime_ownership_packet_ids = [str(entry.get("id") or "") for entry in runtime_ownership_packet_entries]
    approval_packet_ids = {
        str(item.get("id") or "").strip()
        for item in approval_packets.get("packet_types", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if not runtime_ownership_lanes:
        errors.append("runtime-ownership-contract.json must declare at least one ownership lane")
    if len(lane_ids) != len(set(lane_ids)):
        errors.append("runtime-ownership-contract.json contains duplicate lane ids")
    for lane in runtime_ownership_lanes:
        lane_id = str(lane.get("id") or "")
        if not lane_id:
            errors.append("runtime-ownership-contract.json contains a lane without an id")
            continue
        lane_status = str(lane.get("status") or "")
        if lane_status not in ALLOWED_RUNTIME_OWNERSHIP_LANE_STATUSES:
            errors.append(
                f"runtime-ownership-contract.json lane {lane_id} has invalid status {lane_status!r}"
            )
        deployment_mode = str(lane.get("deployment_mode") or "")
        if deployment_mode not in ALLOWED_RUNTIME_OWNERSHIP_DEPLOYMENT_MODES:
            errors.append(
                f"runtime-ownership-contract.json lane {lane_id} has invalid deployment_mode {deployment_mode!r}"
            )
        owner_root_ids = [
            str(root_id) for root_id in lane.get("owner_root_ids", []) if str(root_id).strip()
        ]
        if not owner_root_ids:
            errors.append(f"runtime-ownership-contract.json lane {lane_id} must declare owner_root_ids")
        for root_id in owner_root_ids:
            if root_id not in repo_root_ids:
                errors.append(
                    f"runtime-ownership-contract.json lane {lane_id} references unknown owner_root_id {root_id!r}"
                )
        source_root_id = str(lane.get("source_root_id") or "")
        if source_root_id and source_root_id not in repo_root_ids:
            errors.append(
                f"runtime-ownership-contract.json lane {lane_id} references unknown source_root_id {source_root_id!r}"
            )
        execution_packet_id = str(lane.get("execution_packet_id") or "")
        if execution_packet_id and execution_packet_id not in runtime_ownership_packet_ids:
            errors.append(
                f"runtime-ownership-contract.json lane {lane_id} references unknown execution_packet_id {execution_packet_id!r}"
            )
        for field_name in (
            "runtime_scope",
            "rollback_contract",
            "approval_boundary",
            "next_action",
        ):
            if not str(lane.get(field_name) or "").strip():
                errors.append(f"runtime-ownership-contract.json lane {lane_id} is missing {field_name}")
        for list_field in ("runtime_paths", "active_surfaces", "evidence_paths", "verification_commands"):
            values = [str(item) for item in lane.get(list_field, []) if str(item).strip()]
            if not values:
                errors.append(f"runtime-ownership-contract.json lane {lane_id} must declare {list_field}")

    runtime_ownership_criteria = [
        dict(entry) for entry in runtime_ownership.get("promotion_criteria", []) if isinstance(entry, dict)
    ]
    if not runtime_ownership_criteria:
        errors.append("runtime-ownership-contract.json must declare promotion_criteria")
    criterion_ids = [str(entry.get("id") or "") for entry in runtime_ownership_criteria]
    if len(criterion_ids) != len(set(criterion_ids)):
        errors.append("runtime-ownership-contract.json contains duplicate promotion criterion ids")
    for criterion in runtime_ownership_criteria:
        criterion_id = str(criterion.get("id") or "")
        if not criterion_id:
            errors.append("runtime-ownership-contract.json contains a promotion criterion without an id")
            continue
        criterion_status = str(criterion.get("status") or "")
        if criterion_status not in ALLOWED_RUNTIME_OWNERSHIP_CRITERION_STATUSES:
            errors.append(
                f"runtime-ownership-contract.json promotion criterion {criterion_id} has invalid status {criterion_status!r}"
            )
        if not str(criterion.get("requirement") or "").strip():
            errors.append(
                f"runtime-ownership-contract.json promotion criterion {criterion_id} is missing requirement"
            )
        evidence_paths = [str(item) for item in criterion.get("evidence_paths", []) if str(item).strip()]
        if not evidence_paths:
            errors.append(
                f"runtime-ownership-contract.json promotion criterion {criterion_id} must declare evidence_paths"
            )

    if not runtime_ownership_packet_entries:
        errors.append("runtime-ownership-packets.json must declare packets")
    if len(runtime_ownership_packet_ids) != len(set(runtime_ownership_packet_ids)):
        errors.append("runtime-ownership-packets.json contains duplicate packet ids")
    for packet in runtime_ownership_packet_entries:
        packet_id = str(packet.get("id") or "")
        if not packet_id:
            errors.append("runtime-ownership-packets.json contains a packet without an id")
            continue
        packet_status = str(packet.get("status") or "")
        if packet_status not in ALLOWED_RUNTIME_OWNERSHIP_PACKET_STATUSES:
            errors.append(
                f"runtime-ownership-packets.json packet {packet_id} has invalid status {packet_status!r}"
            )
        lane_id = str(packet.get("lane_id") or "")
        if lane_id not in lane_ids:
            errors.append(
                f"runtime-ownership-packets.json packet {packet_id} references unknown lane_id {lane_id!r}"
            )
        approval_packet_type = str(packet.get("approval_packet_type") or "")
        if approval_packet_type not in approval_packet_ids:
            errors.append(
                f"runtime-ownership-packets.json packet {packet_id} references unknown approval_packet_type {approval_packet_type!r}"
            )
        for field_name in ("label", "goal", "backup_root", "host"):
            if not str(packet.get(field_name) or "").strip():
                errors.append(f"runtime-ownership-packets.json packet {packet_id} is missing {field_name}")
        for list_field in ("preflight_commands", "exact_steps", "verification_commands", "rollback_steps", "evidence_paths"):
            values = [str(item) for item in packet.get(list_field, []) if str(item).strip()]
            if not values:
                errors.append(
                    f"runtime-ownership-packets.json packet {packet_id} must declare non-empty {list_field}"
                )
        path_mappings = [dict(entry) for entry in packet.get("path_mappings", []) if isinstance(entry, dict)]
        target_units = [str(item) for item in packet.get("target_units", []) if str(item).strip()]
        if not path_mappings and not target_units:
            errors.append(
                f"runtime-ownership-packets.json packet {packet_id} must declare path_mappings or target_units"
            )
        for mapping in path_mappings:
            source_path = str(mapping.get("source_path") or "").strip()
            runtime_path = str(mapping.get("runtime_path") or "").strip()
            restart_units = [str(item) for item in mapping.get("restart_units", []) if str(item).strip()]
            if not source_path or not runtime_path:
                errors.append(
                    f"runtime-ownership-packets.json packet {packet_id} contains an incomplete path_mappings entry"
                )
            if not restart_units:
                errors.append(
                    f"runtime-ownership-packets.json packet {packet_id} path mapping {source_path or '<unknown>'} must declare restart_units"
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

    if not vault_redis_audit:
        errors.append("reports/truth-inventory/vault-redis-audit.json is missing")
    else:
        if str(vault_redis_audit.get("surface_id") or "") != "vault-redis-persistence":
            errors.append("reports/truth-inventory/vault-redis-audit.json surface_id must be vault-redis-persistence")
        if str(vault_redis_audit.get("service_id") or "") != "redis":
            errors.append("reports/truth-inventory/vault-redis-audit.json service_id must be redis")
        if str(vault_redis_audit.get("host") or "") != "vault":
            errors.append("reports/truth-inventory/vault-redis-audit.json host must be vault")
        if not str(vault_redis_audit.get("observed_at") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing observed_at")
        if not str(vault_redis_audit.get("source") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing source")
        if not str(vault_redis_audit.get("runtime_owner_surface") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing runtime_owner_surface")
        if not str(vault_redis_audit.get("container_name") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing container_name")
        if not str(vault_redis_audit.get("data_mount_destination") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing data_mount_destination")
        if not str(vault_redis_audit.get("persistence_blocker_code") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing persistence_blocker_code")
        if not str(vault_redis_audit.get("operator_next_action") or "").strip():
            errors.append("reports/truth-inventory/vault-redis-audit.json is missing operator_next_action")
        filesystem = vault_redis_audit.get("filesystem", {})
        if not isinstance(filesystem, dict):
            errors.append("reports/truth-inventory/vault-redis-audit.json filesystem must be an object")
            filesystem = {}
        btrfs_usage = vault_redis_audit.get("btrfs_usage", {})
        if not isinstance(btrfs_usage, dict):
            errors.append("reports/truth-inventory/vault-redis-audit.json btrfs_usage must be an object")
            btrfs_usage = {}
        log_tail = vault_redis_audit.get("log_tail", [])
        if not isinstance(log_tail, list):
            errors.append("reports/truth-inventory/vault-redis-audit.json log_tail must be a list")
            log_tail = []
        for field_name in (
            "appdatacache_top_consumers",
            "appdata_top_consumers",
            "backup_file_top_consumers",
            "stash_generated_top_consumers",
            "comfyui_model_top_consumers",
        ):
            value = vault_redis_audit.get(field_name, [])
            if not isinstance(value, list):
                errors.append(f"reports/truth-inventory/vault-redis-audit.json {field_name} must be a list")
                continue
            for index, entry in enumerate(value):
                if not isinstance(entry, dict):
                    errors.append(
                        f"reports/truth-inventory/vault-redis-audit.json {field_name}[{index}] must be an object"
                    )
                    continue
                if not str(entry.get('path') or '').strip():
                    errors.append(
                        f"reports/truth-inventory/vault-redis-audit.json {field_name}[{index}].path is missing"
                    )
                size_bytes = entry.get("size_bytes")
                if not isinstance(size_bytes, int) or size_bytes < 0:
                    errors.append(
                        f"reports/truth-inventory/vault-redis-audit.json {field_name}[{index}].size_bytes must be a non-negative integer"
                    )
        for field_name in ("no_space_error_count", "background_save_error_count", "security_attack_count"):
            value = vault_redis_audit.get(field_name)
            if not isinstance(value, int) or value < 0:
                errors.append(f"reports/truth-inventory/vault-redis-audit.json {field_name} must be a non-negative integer")
        data_dir_size = vault_redis_audit.get("redis_data_dir_size_bytes")
        if data_dir_size is not None and (not isinstance(data_dir_size, int) or data_dir_size < 0):
            errors.append("reports/truth-inventory/vault-redis-audit.json redis_data_dir_size_bytes must be null or a non-negative integer")
        if filesystem:
            for field_name in ("filesystem", "mountpoint", "used_percent"):
                if not str(filesystem.get(field_name) or "").strip():
                    errors.append(f"reports/truth-inventory/vault-redis-audit.json filesystem.{field_name} is missing")
            for field_name in ("size_bytes", "used_bytes", "available_bytes"):
                value = filesystem.get(field_name)
                if not isinstance(value, int) or value < 0:
                    errors.append(f"reports/truth-inventory/vault-redis-audit.json filesystem.{field_name} must be a non-negative integer")
        if btrfs_usage and "ok" not in btrfs_usage:
            errors.append("reports/truth-inventory/vault-redis-audit.json btrfs_usage must include ok")
        if any(_looks_like_secret(str(line)) for line in log_tail):
            errors.append("reports/truth-inventory/vault-redis-audit.json log_tail appears to contain a secret value")

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
            if relative_path in ignored_generated_docs:
                continue
            generator_command = None
            registry_generator = str(document.get("generator") or "").strip()
            if registry_generator:
                parsed = _parse_registry_generator_command(registry_generator)
                if parsed:
                    generator_command = parsed
            if generator_command is None:
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

    missing_reconciliation_docs = sorted(REQUIRED_RECONCILIATION_DOCS - lifecycle_paths)
    if missing_reconciliation_docs:
        errors.append(
            "docs-lifecycle-registry.json is missing reconciliation docs: " + ", ".join(missing_reconciliation_docs)
        )
    missing_completion_docs = sorted(REQUIRED_COMPLETION_PROGRAM_DOCS - lifecycle_paths)
    if missing_completion_docs:
        errors.append(
            "docs-lifecycle-registry.json is missing completion-program docs: " + ", ".join(missing_completion_docs)
        )
    portfolio_registry_text = (REPO_ROOT / "docs" / "projects" / "PORTFOLIO-REGISTRY.md").read_text(encoding="utf-8")
    if "ATHANOR-ECOSYSTEM-REGISTRY.md" not in portfolio_registry_text:
        errors.append("docs/projects/PORTFOLIO-REGISTRY.md must point readers to ATHANOR-ECOSYSTEM-REGISTRY.md")

    completion_program_text = (REPO_ROOT / "docs" / "operations" / "ATHANOR-TOTAL-COMPLETION-PROGRAM.md").read_text(encoding="utf-8")
    if "completion-program-registry.json" not in completion_program_text:
        errors.append("ATHANOR-TOTAL-COMPLETION-PROGRAM.md must point readers to completion-program-registry.json")
    if "ATHANOR-RECONCILIATION-END-STATE.md" not in completion_program_text:
        errors.append("ATHANOR-TOTAL-COMPLETION-PROGRAM.md must point readers to ATHANOR-RECONCILIATION-END-STATE.md")
    ralph_loop_program_text = (REPO_ROOT / "docs" / "operations" / "ATHANOR-RALPH-LOOP-PROGRAM.md").read_text(encoding="utf-8")
    if "scripts/run_ralph_loop_pass.py" not in ralph_loop_program_text:
        errors.append("ATHANOR-RALPH-LOOP-PROGRAM.md must point readers to scripts/run_ralph_loop_pass.py")
    if "reports/ralph-loop/latest.json" not in ralph_loop_program_text:
        errors.append("ATHANOR-RALPH-LOOP-PROGRAM.md must point readers to reports/ralph-loop/latest.json")
    if "ATHANOR-RECONCILIATION-END-STATE.md" not in ralph_loop_program_text:
        errors.append("ATHANOR-RALPH-LOOP-PROGRAM.md must point readers to ATHANOR-RECONCILIATION-END-STATE.md")
    if "typed brake" not in ralph_loop_program_text or "green check" not in ralph_loop_program_text:
        errors.append("ATHANOR-RALPH-LOOP-PROGRAM.md must state that Ralph continues until a typed brake, not until a green check")
    completion_backlog_text = (REPO_ROOT / "docs" / "operations" / "CONTINUOUS-COMPLETION-BACKLOG.md").read_text(encoding="utf-8")
    if "reports/truth-inventory/ralph-continuity-state.json" not in completion_backlog_text:
        errors.append("CONTINUOUS-COMPLETION-BACKLOG.md must point readers to reports/truth-inventory/ralph-continuity-state.json")
    session_restart_text = (REPO_ROOT / "docs" / "operations" / "SESSION-RESTART-RUNBOOK.md").read_text(encoding="utf-8")
    if "session_restart_brief.py" not in session_restart_text:
        errors.append("SESSION-RESTART-RUNBOOK.md must point readers to scripts/session_restart_brief.py")
    if "reports/truth-inventory/ralph-continuity-state.json" not in session_restart_text:
        errors.append("SESSION-RESTART-RUNBOOK.md must point readers to reports/truth-inventory/ralph-continuity-state.json")
    if "typed brake" not in session_restart_text:
        errors.append("SESSION-RESTART-RUNBOOK.md must state the typed-brake restart rule")
    operating_system_text = (REPO_ROOT / "docs" / "operations" / "ATHANOR-OPERATING-SYSTEM.md").read_text(encoding="utf-8")
    if "ATHANOR-RECONCILIATION-END-STATE.md" not in operating_system_text:
        errors.append("ATHANOR-OPERATING-SYSTEM.md must point readers to ATHANOR-RECONCILIATION-END-STATE.md")
    if not RALPH_LOOP_REPORT_PATH.exists():
        errors.append("reports/ralph-loop/latest.json is missing")
    else:
        if str(ralph_loop_report.get("generated_at") or "").strip() == "":
            errors.append("reports/ralph-loop/latest.json is missing generated_at")
        loop_state = dict(ralph_loop_report.get("loop_state") or {})
        if str(loop_state.get("current_loop_family") or "") not in REQUIRED_COMPLETION_LOOP_FAMILY_IDS:
            errors.append("reports/ralph-loop/latest.json loop_state.current_loop_family must be a known loop family")
        if str(loop_state.get("selected_workstream") or "") not in REQUIRED_COMPLETION_WORKSTREAM_IDS:
            errors.append("reports/ralph-loop/latest.json loop_state.selected_workstream must be a known workstream id")
        if str(loop_state.get("selected_execution_state") or "") not in ALLOWED_COMPLETION_LOOP_EXECUTION_STATES:
            errors.append("reports/ralph-loop/latest.json loop_state.selected_execution_state must be a valid execution state")
        if str(loop_state.get("blocker_type") or "") not in ALLOWED_COMPLETION_LOOP_BLOCKER_TYPES:
            errors.append("reports/ralph-loop/latest.json loop_state.blocker_type must be a valid blocker type")
        controller = dict(ralph_loop_report.get("controller") or {})
        if str(controller.get("phase_scope") or "") != str(autonomy_activation.get("current_phase_id") or ""):
            errors.append("reports/ralph-loop/latest.json controller.phase_scope must match autonomy current_phase_id")
        freshness = dict(ralph_loop_report.get("freshness") or {})
        artifact_rows = freshness.get("artifacts", [])
        if not isinstance(artifact_rows, list) or not artifact_rows:
            errors.append("reports/ralph-loop/latest.json freshness.artifacts must be a non-empty list")
        workstream_rows = ralph_loop_report.get("workstreams", [])
        if not isinstance(workstream_rows, list) or not workstream_rows:
            errors.append("reports/ralph-loop/latest.json workstreams must be a non-empty list")
        next_actions = ralph_loop_report.get("next_actions", [])
        if not isinstance(next_actions, list):
            errors.append("reports/ralph-loop/latest.json next_actions must be a list")
        if not isinstance(ralph_loop_report.get("continue_allowed"), bool):
            errors.append("reports/ralph-loop/latest.json continue_allowed must be boolean")
        if str(ralph_loop_report.get("stop_state") or "") not in ALLOWED_RALPH_CONTINUITY_STOP_STATES:
            errors.append("reports/ralph-loop/latest.json stop_state must be a valid Ralph continuity stop state")
        next_unblocked_candidate = ralph_loop_report.get("next_unblocked_candidate")
        if next_unblocked_candidate is not None and not isinstance(next_unblocked_candidate, dict):
            errors.append("reports/ralph-loop/latest.json next_unblocked_candidate must be an object when present")
        if str(loop_state.get("stop_state") or "") not in ALLOWED_RALPH_CONTINUITY_STOP_STATES:
            errors.append("reports/ralph-loop/latest.json loop_state.stop_state must be a valid Ralph continuity stop state")
        if bool(ralph_loop_report.get("continue_allowed")) != bool(loop_state.get("continue_allowed")):
            errors.append("reports/ralph-loop/latest.json continue_allowed must match loop_state.continue_allowed")
        if str(ralph_loop_report.get("stop_state") or "") != str(loop_state.get("stop_state") or ""):
            errors.append("reports/ralph-loop/latest.json stop_state must match loop_state.stop_state")
        continuity_block = dict(ralph_loop_report.get("continuity") or {})
        if str(continuity_block.get("state_path") or "") != "reports/truth-inventory/ralph-continuity-state.json":
            errors.append("reports/ralph-loop/latest.json continuity.state_path must point at reports/truth-inventory/ralph-continuity-state.json")
        if str(dict(ralph_loop_report.get("source_of_truth") or {}).get("completion_program_registry") or "") != "config/automation-backbone/completion-program-registry.json":
            errors.append("reports/ralph-loop/latest.json source_of_truth.completion_program_registry must point at completion-program-registry.json")
        if str(ralph_loop.get("current_loop_family") or "") != str(loop_state.get("current_loop_family") or ""):
            errors.append("completion-program-registry.json ralph_loop.current_loop_family must match reports/ralph-loop/latest.json loop_state.current_loop_family")
        if str(ralph_loop.get("selected_workstream") or "") != str(loop_state.get("selected_workstream") or ""):
            errors.append("completion-program-registry.json ralph_loop.selected_workstream must match reports/ralph-loop/latest.json loop_state.selected_workstream")
        if str(ralph_loop.get("blocker_type") or "") != str(loop_state.get("blocker_type") or ""):
            errors.append("completion-program-registry.json ralph_loop.blocker_type must match reports/ralph-loop/latest.json loop_state.blocker_type")
        if str(ralph_loop.get("approval_status") or "") != str(loop_state.get("approval_status") or ""):
            errors.append("completion-program-registry.json ralph_loop.approval_status must match reports/ralph-loop/latest.json loop_state.approval_status")
        if str(ralph_loop.get("execution_posture") or "") != str(loop_state.get("execution_posture") or ""):
            errors.append("completion-program-registry.json ralph_loop.execution_posture must match reports/ralph-loop/latest.json loop_state.execution_posture")
        if str(ralph_loop.get("evidence_freshness") or "") != str(loop_state.get("evidence_freshness") or ""):
            errors.append("completion-program-registry.json ralph_loop.evidence_freshness must match reports/ralph-loop/latest.json loop_state.evidence_freshness")
        if str(ralph_loop_report.get("active_claim_task_id") or "").strip() != str(dict(ralph_loop_report.get("governed_dispatch_claim") or {}).get("current_task_id") or "").strip():
            errors.append("reports/ralph-loop/latest.json active_claim_task_id must match governed_dispatch_claim.current_task_id")
        if str(ralph_loop_report.get("active_claim_task_title") or "").strip() != str(dict(ralph_loop_report.get("governed_dispatch_claim") or {}).get("current_task_title") or "").strip():
            errors.append("reports/ralph-loop/latest.json active_claim_task_title must match governed_dispatch_claim.current_task_title")
        report_end_state = dict(ralph_loop_report.get("reconciliation_end_state") or {})
        if str(report_end_state.get("source_of_truth") or "") != str(reconciliation_end_state.get("source_of_truth") or ""):
            errors.append("reports/ralph-loop/latest.json reconciliation_end_state.source_of_truth must match completion-program-registry.json")
        if str(report_end_state.get("status") or "") != str(reconciliation_end_state.get("status") or ""):
            errors.append("reports/ralph-loop/latest.json reconciliation_end_state.status must match completion-program-registry.json")
        report_gate_rows = [
            dict(entry) for entry in report_end_state.get("project_exit_gates", []) if isinstance(entry, dict)
        ]
        report_gate_ids = {str(entry.get("id") or "").strip() for entry in report_gate_rows}
        registry_gate_ids = {
            str(entry.get("id") or "").strip() for entry in reconciliation_end_state.get("project_exit_gates", []) if isinstance(entry, dict)
        }
        if report_gate_ids != registry_gate_ids:
            errors.append("reports/ralph-loop/latest.json reconciliation_end_state.project_exit_gates must match completion-program-registry.json gate ids")
        for gate in report_gate_rows:
            gate_id = str(gate.get("id") or "").strip()
            if str(gate.get("status") or "") not in ALLOWED_RECONCILIATION_END_STATE_GATE_STATUSES:
                errors.append(
                    f"reports/ralph-loop/latest.json reconciliation_end_state gate {gate_id} has invalid status {gate.get('status')!r}"
                )
        report_steady_state = dict(report_end_state.get("steady_state_acceptance") or {})
        registry_steady_state = dict(reconciliation_end_state.get("steady_state_acceptance") or {})
        if int(report_steady_state.get("current_consecutive_clean_cycles") or 0) != int(
            registry_steady_state.get("current_consecutive_clean_cycles") or 0
        ):
            errors.append(
                "reports/ralph-loop/latest.json reconciliation_end_state.steady_state_acceptance.current_consecutive_clean_cycles must match completion-program-registry.json"
            )
        if bool(report_steady_state.get("ready_to_transition")) != bool(
            registry_steady_state.get("ready_to_transition")
        ):
            errors.append(
                "reports/ralph-loop/latest.json reconciliation_end_state.steady_state_acceptance.ready_to_transition must match completion-program-registry.json"
            )

    if not RALPH_CONTINUITY_STATE_PATH.exists():
        errors.append("reports/truth-inventory/ralph-continuity-state.json is missing")
    else:
        try:
            continuity_state = json.loads(RALPH_CONTINUITY_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continuity_state = {}
            errors.append("reports/truth-inventory/ralph-continuity-state.json is invalid JSON")
        if isinstance(continuity_state, dict):
            if str(continuity_state.get("generated_at") or "").strip() == "":
                errors.append("reports/truth-inventory/ralph-continuity-state.json is missing generated_at")
            if not isinstance(continuity_state.get("continue_allowed"), bool):
                errors.append("reports/truth-inventory/ralph-continuity-state.json continue_allowed must be boolean")
            if str(continuity_state.get("current_stop_state") or "") not in ALLOWED_RALPH_CONTINUITY_STOP_STATES:
                errors.append("reports/truth-inventory/ralph-continuity-state.json current_stop_state must be valid")
            if not isinstance(continuity_state.get("recent_no_delta_task_ids", []), list):
                errors.append("reports/truth-inventory/ralph-continuity-state.json recent_no_delta_task_ids must be a list")
            if not isinstance(continuity_state.get("suppressed_until_by_task", {}), dict):
                errors.append("reports/truth-inventory/ralph-continuity-state.json suppressed_until_by_task must be an object")
            if not isinstance(continuity_state.get("claim_history", []), list):
                errors.append("reports/truth-inventory/ralph-continuity-state.json claim_history must be a list")
            if not isinstance(continuity_state.get("active_claim_history", []), list):
                errors.append("reports/truth-inventory/ralph-continuity-state.json active_claim_history must be a list")
            if RALPH_LOOP_REPORT_PATH.exists() and isinstance(ralph_loop_report, dict):
                report_continuity = dict(ralph_loop_report.get("continuity") or {})
                if bool(continuity_state.get("continue_allowed")) != bool(ralph_loop_report.get("continue_allowed")):
                    errors.append("ralph-continuity-state.json continue_allowed must match reports/ralph-loop/latest.json")
                if str(continuity_state.get("current_stop_state") or "") != str(ralph_loop_report.get("stop_state") or ""):
                    errors.append("ralph-continuity-state.json current_stop_state must match reports/ralph-loop/latest.json stop_state")
                if dict(report_continuity.get("suppressed_until_by_task") or {}) != dict(continuity_state.get("suppressed_until_by_task") or {}):
                    errors.append("reports/ralph-loop/latest.json continuity.suppressed_until_by_task must match ralph-continuity-state.json")

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
    raise SystemExit(main(sys.argv[1:]))
