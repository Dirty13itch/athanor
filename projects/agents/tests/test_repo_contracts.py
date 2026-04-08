import asyncio
import ast
import json
import re
import subprocess
import unittest
from functools import lru_cache
from pathlib import Path
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_GITIGNORE = REPO_ROOT / ".gitignore"
AGENTS_DOC = REPO_ROOT / "AGENTS.md"
AGENTS_INIT = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "agents" / "__init__.py"
SERVER_PY = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "server.py"
AGENT_DESCRIPTOR_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "agent-descriptor-registry.json"
DASHBOARD_CONFIG = REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "config.ts"
DASHBOARD_SERVER_CONFIG = REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "server-config.ts"
DASHBOARD_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "dashboard" / "templates" / "docker-compose.yml.j2"
LITELLM_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "templates" / "litellm_config.yaml.j2"
VAULT_LITELLM_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "defaults" / "main.yml"
VAULT_LITELLM_TASKS = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "tasks" / "main.yml"
GPU_ORCH_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "gpu-orchestrator" / "defaults" / "main.yml"
GPU_ORCH_CONFIG = REPO_ROOT / "projects" / "gpu-orchestrator" / "src" / "gpu_orchestrator" / "config.py"
GPU_ORCH_COMPOSE = REPO_ROOT / "projects" / "gpu-orchestrator" / "docker-compose.yml"
BUILD_PROFILE_SCRIPT = REPO_ROOT / "scripts" / "build-profile.sh"
ENDPOINT_HARNESS = REPO_ROOT / "tests" / "harness.py"
STATUSLINE_HOOK = REPO_ROOT / ".claude" / "hooks" / "statusline.sh"
MCP_REDIS_SCRIPT = REPO_ROOT / "scripts" / "mcp-redis.py"
MCP_SMART_READER_SCRIPT = REPO_ROOT / "scripts" / "mcp-smart-reader.py"
MCP_ATHANOR_AGENTS_SCRIPT = REPO_ROOT / "scripts" / "mcp-athanor-agents.py"
MCP_QDRANT_SCRIPT = REPO_ROOT / "scripts" / "mcp-qdrant.py"
AUTOMATION_RECORDS_SCRIPT = REPO_ROOT / "scripts" / "automation_records.py"
RUNTIME_ENV_HELPER = REPO_ROOT / "scripts" / "runtime_env.py"
DEPLOY_AGENTS_SCRIPT = REPO_ROOT / "scripts" / "deploy-agents.sh"
NODE_HEARTBEAT_SCRIPT = REPO_ROOT / "scripts" / "node-heartbeat.py"
EXPORT_LANGFUSE_TRACES_SCRIPT = REPO_ROOT / "scripts" / "export-langfuse-traces.py"
PARSE_BOOKMARKS_SCRIPT = REPO_ROOT / "scripts" / "parse-bookmarks.py"
LANGFUSE_SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-prompts-to-langfuse.py"
MODEL_INVENTORY_SCRIPT = REPO_ROOT / "scripts" / "model-inventory.sh"
ENDPOINT_TEST_SCRIPT = REPO_ROOT / "scripts" / "tests" / "test-endpoints.py"
VAULT_SSH_SCRIPT = REPO_ROOT / "scripts" / "vault-ssh.py"
VAULT_SSH_POWERSHELL = REPO_ROOT / "scripts" / "ssh-vault.ps1"
SESSION_START_HOOK = REPO_ROOT / ".claude" / "hooks" / "session-start-health.sh"
NODE1_PLAYBOOK = REPO_ROOT / "ansible" / "playbooks" / "node1.yml"
NEO4J_TASKS = REPO_ROOT / "ansible" / "roles" / "vault-neo4j" / "tasks" / "main.yml"
PROJECTS_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "projects.py"
DASHBOARD_SW = REPO_ROOT / "projects" / "dashboard" / "public" / "sw.js"
EOQ_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "eoq" / "templates" / "docker-compose.yml.j2"
ULRICH_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "ulrich-energy" / "templates" / "docker-compose.yml.j2"
EOQ_CONFIG = REPO_ROOT / "projects" / "eoq" / "src" / "lib" / "config.ts"
ULRICH_CONFIG = REPO_ROOT / "projects" / "ulrich-energy" / "src" / "lib" / "config.ts"
TASKS_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "tasks.py"
TASK_STORE_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "task_store.py"
INTENT_MINER_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "intent_miner.py"
MORNING_MANAGER_SCRIPT = REPO_ROOT / "scripts" / "morning-manager.py"
INDEX_KNOWLEDGE_SCRIPT = REPO_ROOT / "scripts" / "index-knowledge.py"
ARCHIVED_BUILD_MANIFEST = REPO_ROOT / "docs" / "archive" / "BUILD-MANIFEST.md"
ACTIVE_BUILD_MANIFEST = REPO_ROOT / "docs" / "BUILD-MANIFEST.md"
ARCHIVED_HARDWARE_LEDGER = REPO_ROOT / "docs" / "archive" / "hardware" / "hardware-inventory.md"
ACTIVE_HARDWARE_LEDGER = REPO_ROOT / "docs" / "hardware" / "inventory.md"
BUILD_COMMAND_DOC = REPO_ROOT / ".claude" / "commands" / "build.md"
ACTIVE_DAILY_OPERATIONS_DOC = REPO_ROOT / "docs" / "guides" / "daily-operations.md"
MASTER_PLAN_DOC = REPO_ROOT / "docs" / "MASTER-PLAN.md"
ACTIVE_TACTICAL_PLAN = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-03-18-athanor-coo-architecture.md"
ACTIVE_TACTICAL_PLAN_FULL = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-03-18-athanor-coo-architecture-FULL.md"
ARCHIVED_TACTICAL_PLAN_FULL = REPO_ROOT / "docs" / "archive" / "planning-era" / "2026-03-18-athanor-coo-architecture-FULL.md"
PLATFORM_TOPOLOGY_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "platform-topology.json"
VAULT_HOST_VARS = REPO_ROOT / "ansible" / "host_vars" / "vault.yml"
CORE_HOST_VARS = REPO_ROOT / "ansible" / "host_vars" / "core.yml"
VAULT_LANGFUSE_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "vault-langfuse" / "defaults" / "main.yml"
VAULT_LANGFUSE_TASKS = REPO_ROOT / "ansible" / "roles" / "vault-langfuse" / "tasks" / "main.yml"
REFERENCE_INDEX_DOC = REPO_ROOT / "docs" / "REFERENCE-INDEX.md"
DOC_WRITER_AGENT_DOC = REPO_ROOT / ".claude" / "agents" / "doc-writer.md"
INFRA_AUDITOR_AGENT_DOC = REPO_ROOT / ".claude" / "agents" / "infra-auditor.md"
DOCS_SYNC_RULE = REPO_ROOT / ".claude" / "rules" / "docs-sync.md"
STATE_UPDATE_SKILL = REPO_ROOT / ".claude" / "skills" / "state-update.md"
VERIFY_INVENTORY_SKILL = REPO_ROOT / ".claude" / "skills" / "verify-inventory" / "SKILL.md"
VISUAL_SYSTEM_README = REPO_ROOT / "docs" / "design" / "visual-system" / "README.md"
VISUAL_SYSTEM_AUDIT = REPO_ROOT / "docs" / "design" / "visual-system" / "VISUAL_AUDIT.md"
COMPLETION_AUDIT_COMMON = REPO_ROOT / "scripts" / "completion_audit_common.py"
MAP_AGENT_ENDPOINTS_SCRIPT = REPO_ROOT / "scripts" / "map-agent-endpoints.py"
RUNTIME_SUBSYSTEM_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "runtime-subsystem-registry.json"
RUNTIME_MIGRATION_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "runtime-migration-registry.json"
ACTIVE_DASHBOARD_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-dashboard.md"
ACTIVE_AGENT_FRAMEWORK_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-agent-framework.md"
ACTIVE_BASE_PLATFORM_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-base-platform.md"
ACTIVE_NETWORK_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-network-architecture.md"
ACTIVE_STORAGE_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-storage-architecture.md"
ACTIVE_NODE_ROLES_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-node-roles.md"
ACTIVE_INFERENCE_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-inference-engine.md"
ACTIVE_CREATIVE_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-creative-pipeline.md"
ACTIVE_MONITORING_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-monitoring.md"
ACTIVE_HOME_AUTOMATION_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-home-automation.md"
ACTIVE_MEDIA_STACK_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-15-media-stack.md"
ACTIVE_REMOTE_ACCESS_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-24-remote-access.md"
ACTIVE_VOICE_INTERACTION_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-24-voice-interaction.md"
ACTIVE_COMMAND_CENTER_UI_RESEARCH = REPO_ROOT / "docs" / "research" / "2026-02-25-command-center-ui-design.md"
ACTIVE_RESEARCH_ROADMAP = REPO_ROOT / "docs" / "research" / "2026-02-15-research-roadmap.md"
ACTIVE_DASHBOARD_INTERACTIONS = REPO_ROOT / "docs" / "design" / "dashboard-interactions.md"
ARCHIVED_DASHBOARD_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-dashboard.md"
ARCHIVED_AGENT_FRAMEWORK_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-agent-framework.md"
ARCHIVED_BASE_PLATFORM_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-base-platform.md"
ARCHIVED_NETWORK_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-network-architecture.md"
ARCHIVED_STORAGE_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-storage-architecture.md"
ARCHIVED_NODE_ROLES_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-node-roles.md"
ARCHIVED_INFERENCE_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-inference-engine.md"
ARCHIVED_CREATIVE_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-creative-pipeline.md"
ARCHIVED_MONITORING_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-monitoring.md"
ARCHIVED_HOME_AUTOMATION_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-home-automation.md"
ARCHIVED_MEDIA_STACK_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-15-media-stack.md"
ARCHIVED_REMOTE_ACCESS_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-24-remote-access.md"
ARCHIVED_VOICE_INTERACTION_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-24-voice-interaction.md"
ARCHIVED_COMMAND_CENTER_UI_RESEARCH = REPO_ROOT / "docs" / "archive" / "research" / "2026-02-25-command-center-ui-design.md"
RUN_COMPLETION_AUDIT_SCRIPT = REPO_ROOT / "scripts" / "run-completion-audit.py"
LEGACY_GOVERNOR_SELF_IMPROVE = REPO_ROOT / "services" / "governor" / "self_improve.py"
LEGACY_GOVERNOR_OVERNIGHT = REPO_ROOT / "services" / "governor" / "overnight.py"
LEGACY_GOVERNOR_MORNING_SUMMARY = REPO_ROOT / "services" / "governor" / "morning_summary.py"
LEGACY_GOVERNOR_TASK_MONITOR = REPO_ROOT / "services" / "governor" / "task_monitor.py"
LEGACY_GOVERNOR_ACT_FIRST = REPO_ROOT / "services" / "governor" / "act_first.py"
LEGACY_GOVERNOR_STATUS_REPORT = REPO_ROOT / "services" / "governor" / "status_report.py"
LEGACY_GOVERNOR_MAIN = REPO_ROOT / "services" / "governor" / "main.py"
LEGACY_GOVERNOR_DISPATCHER = REPO_ROOT / "services" / "governor" / "dispatch.py"
LEGACY_GOVERNOR_DISPATCH_LOOP = REPO_ROOT / "services" / "governor" / "continuous_dispatch.py"
LEGACY_GOVERNOR_DB_MODULE = REPO_ROOT / "services" / "governor" / "db.py"
LEGACY_GOVERNOR_IMPORTS = REPO_ROOT / "services" / "governor" / "_imports.py"
GOVERNOR_ARCHIVE_README = REPO_ROOT / "services" / "governor" / "archive" / "README.md"
LEGACY_ATLAS_VALIDATOR = REPO_ROOT / "scripts" / "validate-atlas.py"
ATLAS_README = REPO_ROOT / "docs" / "atlas" / "README.md"
ATLAS_SOURCE_RECONCILIATION = REPO_ROOT / "docs" / "atlas" / "SOURCE_RECONCILIATION.md"
COMMAND_HIERARCHY_ATLAS = REPO_ROOT / "docs" / "atlas" / "COMMAND_HIERARCHY_ATLAS.md"
ARCHITECT_AGENT_DOC = REPO_ROOT / ".claude" / "agents" / "architect.md"
ACTIVE_PHASE11_REPORT = REPO_ROOT / "audit" / "PHASE-11-REPORT.md"
ACTIVE_PHASE16_STATUS = REPO_ROOT / "audit" / "PHASE-16-STATUS.md"
ARCHIVED_PHASE11_REPORT = REPO_ROOT / "docs" / "archive" / "audits" / "PHASE-11-REPORT-2026-03-23.md"
ARCHIVED_PHASE16_STATUS = REPO_ROOT / "docs" / "archive" / "audits" / "PHASE-16-STATUS-2026-03-23.md"
SCRIPTS_README = REPO_ROOT / "scripts" / "README.md"
SERVICES_README = REPO_ROOT / "services" / "README.md"
SERVICES_PYCACHE = REPO_ROOT / "services" / "__pycache__"
SENTINEL_CHECKS = REPO_ROOT / "services" / "sentinel" / "checks.py"
DRIFT_CHECK_SCRIPT = REPO_ROOT / "scripts" / "drift-check.sh"
TROUBLESHOOTING_DOC = REPO_ROOT / "docs" / "TROUBLESHOOTING.md"
GOVERNOR_FACADE_RETIREMENT_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "governor-facade-retirement.md"
PROVIDER_CATALOG_REPORT = REPO_ROOT / "docs" / "operations" / "PROVIDER-CATALOG-REPORT.md"
PROVIDER_CATALOG_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "provider-catalog.json"
CREDENTIAL_SURFACE_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "credential-surface-registry.json"
SERVICE_CONTRACT_TEST_SCRIPT = REPO_ROOT / "scripts" / "run_service_contract_tests.py"
SUBSCRIPTION_BURN_SCRIPT = REPO_ROOT / "scripts" / "subscription-burn.py"
SUBSCRIPTION_BURN_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "subscription-burn-registry.json"
CLI_ROUTER_SCRIPT = REPO_ROOT / "scripts" / "cli-router.py"
QUALITY_GATE_REQUIREMENTS = REPO_ROOT / "services" / "quality-gate" / "requirements.txt"
STATUS_DOC = REPO_ROOT / "STATUS.md"
BACKLOG_DOC = REPO_ROOT / "docs" / "operations" / "CONTINUOUS-COMPLETION-BACKLOG.md"
TRUTH_INVENTORY_COLLECTOR = REPO_ROOT / "scripts" / "collect_truth_inventory.py"
OPERATOR_RUNBOOKS_DOC = REPO_ROOT / "docs" / "operations" / "OPERATOR_RUNBOOKS.md"
OPERATOR_RUNBOOKS_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "operator-runbooks.json"
GOVERNOR_AUTHORITY_MATRIX_DOC = REPO_ROOT / "docs" / "operations" / "GOVERNOR-AUTHORITY-MATRIX.md"
REPO_ROOTS_REPORT_DOC = REPO_ROOT / "docs" / "operations" / "REPO-ROOTS-REPORT.md"
TRUTH_DRIFT_REPORT_DOC = REPO_ROOT / "docs" / "operations" / "TRUTH-DRIFT-REPORT.md"
RUNTIME_MIGRATION_REPORT_DOC = REPO_ROOT / "docs" / "operations" / "RUNTIME-MIGRATION-REPORT.md"
RUNTIME_CUTOVER_PACKET_DOC = REPO_ROOT / "docs" / "operations" / "GOVERNOR-FACADE-CUTOVER-PACKET.md"
DASHBOARD_BRIEFING_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "briefing" / "route.ts"
DASHBOARD_GALLERY_FILES_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "gallery" / "files" / "route.ts"
DASHBOARD_ATTENTION_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "attention" / "route.ts"
DASHBOARD_ATTENTION_PROACTIVE_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "attention" / "proactive" / "route.ts"
DASHBOARD_PIPELINE_INTENTS_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "pipeline" / "intents" / "route.ts"
DASHBOARD_PROJECT_STATE_ROUTE = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "projects" / "[projectId]" / "state" / "route.ts"
TASKS_ROUTE_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "routes" / "tasks.py"
EXECUTION_TOOLS_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "tools" / "execution.py"
SCHEDULER_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "scheduler.py"
WORKPLANNER_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "workplanner.py"
WORKSPACE_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "workspace.py"
WORK_PIPELINE_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "work_pipeline.py"
RESEARCH_JOBS_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "research_jobs.py"
CASCADE_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "cascade.py"
COMMAND_RIGHTS_REGISTRY = REPO_ROOT / "config" / "automation-backbone" / "command-rights-registry.json"
ALLOWED_STALE_DOC_PATH_MENTIONS = {
    "docs/BUILD-MANIFEST.md": {
        "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
    },
    "docs/BUILD-ROADMAP.md": set(),
    "docs/dependency-graph.md": set(),
    "docs/hardware/inventory.md": set(),
}

RAW_IP_PATTERN = re.compile(r"192\.168\.1\.\d+")
ALLOWED_DASHBOARD_IP_FILES = {
    DASHBOARD_CONFIG,
    REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "dashboard-fixtures.ts",
}

CANONICAL_DASHBOARD_ENVS = {
    "NEXT_PUBLIC_PROMETHEUS_URL",
    "NEXT_PUBLIC_VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
    "ATHANOR_NODE1_HOST",
    "ATHANOR_NODE2_HOST",
    "ATHANOR_VAULT_HOST",
    "ATHANOR_DEV_HOST",
    "ATHANOR_AGENT_SERVER_URL",
    "ATHANOR_PROMETHEUS_URL",
    "ATHANOR_GRAFANA_URL",
    "ATHANOR_LITELLM_URL",
    "ATHANOR_VLLM_COORDINATOR_URL",
    "ATHANOR_VLLM_CODER_URL",
    "ATHANOR_VLLM_WORKER_URL",
    "ATHANOR_VLLM_EMBEDDING_URL",
    "ATHANOR_VLLM_RERANKER_URL",
    "ATHANOR_COMFYUI_URL",
    "ATHANOR_OPEN_WEBUI_URL",
    "ATHANOR_VAULT_OPEN_WEBUI_URL",
    "ATHANOR_EOQ_URL",
    "ATHANOR_SONARR_URL",
    "ATHANOR_RADARR_URL",
    "ATHANOR_TAUTULLI_URL",
    "ATHANOR_PLEX_URL",
    "ATHANOR_STASH_URL",
    "ATHANOR_PROWLARR_URL",
    "ATHANOR_SABNZBD_URL",
    "ATHANOR_HOME_ASSISTANT_URL",
    "ATHANOR_QDRANT_URL",
    "ATHANOR_NEO4J_URL",
    "ATHANOR_NEO4J_USER",
    "ATHANOR_NEO4J_PASSWORD",
    "ATHANOR_SPEACHES_URL",
    "ATHANOR_LITELLM_API_KEY",
}

FROZEN_LITELLM_ALIASES = {
    "reasoning": "http://{{ vllm_node1_host }}:{{ vllm_node1_port }}/v1",
    "coding": "http://{{ vllm_node1_host }}:{{ vllm_node1_port }}/v1",
    "utility": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "creative": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "fast": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "worker": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "uncensored": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "coder": "http://{{ vllm_node1_host }}:{{ vllm_node1_coder_port }}/v1",
    "embedding": "http://{{ vllm_embedding_host }}:8001/v1",
    "reranker": "http://{{ vllm_reranker_host }}:{{ vllm_reranker_port }}/v1",
}

CANONICAL_PROJECT_IDS = {
    "athanor",
    "eoq",
    "kindred",
    "ulrich-energy",
    "media",
}

BANNED_LITERAL_SECRETS = {
    "sk-" + "athanor-litellm-2026",
    "sk-" + "athanor-key",
    "miniflux-" + "athanor-2026",
    "athanor-" + "miniflux-2026",
    "n8n-" + "athanor-2026",
    "athanor" + "2026",
    "Hockey" + "1298",
    "Will2" + "live!",
    "Jv1Vg9HAML2j" + "HGWjFnTCcIsqSzqZfIQz",
}
ACTIVE_GOVERNOR_HELPER_MODULES = (
    LEGACY_GOVERNOR_OVERNIGHT,
    LEGACY_GOVERNOR_SELF_IMPROVE,
    LEGACY_GOVERNOR_ACT_FIRST,
    LEGACY_GOVERNOR_STATUS_REPORT,
    LEGACY_GOVERNOR_IMPORTS,
)
ACTIVE_GOVERNOR_LOCAL_STATE_TOKENS = (
    "sqlite",
    "sqlite3",
    "GOVERNOR_DB",
    "task_queue",
    "active_agents",
    "tmux",
    "/tmp/agent-worktrees",
)
ACTIVE_GOVERNOR_LOCAL_STATE_EXEMPTIONS = {}
EXPECTED_GOVERNOR_FACADE_CALLERS = {
    "scripts/drift-check.sh",
    "scripts/smoke-test.sh",
    "services/cluster_config.py",
    "services/gateway/main.py",
    "services/governor/status_report.py",
    "services/governor/overnight.py",
    "services/governor/act_first.py",
    "services/governor/self_improve.py",
    "services/sentinel/checks.py",
}
EXPECTED_GOVERNOR_FACADE_CALLER_SYNC_ORDER = {
    "scripts/drift-check.sh": 1,
    "scripts/smoke-test.sh": 2,
    "services/cluster_config.py": 3,
    "services/gateway/main.py": 4,
    "services/governor/status_report.py": 5,
    "services/governor/overnight.py": 6,
    "services/governor/act_first.py": 7,
    "services/governor/self_improve.py": 8,
    "services/sentinel/checks.py": 9,
}
MIGRATED_GOVERNOR_FACADE_FORBIDDEN_TOKENS = (":8760", "/queue", "/dispatch-and-run", "ATHANOR_GOVERNOR_URL")
MUTATION_ROUTE_DECORATOR = re.compile(r"@(router|app)\.(post|put|patch|delete)\(")
OPERATOR_CONTRACT_TOKENS = (
    "require_operator_action",
    "build_operator_action",
    "emit_operator_audit_event",
)
ALLOWED_MUTATION_MODULES_WITHOUT_OPERATOR_CONTRACT = {
    REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "routes" / "chat.py",
    REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "routing.py",
}


def normalize_agent_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


@lru_cache(maxsize=None)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


@lru_cache(maxsize=1)
def list_tracked_repo_files() -> tuple[Path, ...]:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return tuple(path for path in REPO_ROOT.rglob("*") if path.is_file())

    files: list[Path] = []
    for line in result.stdout.splitlines():
        candidate = (REPO_ROOT / line.strip()).resolve()
        if candidate.is_file():
            files.append(candidate)
    return tuple(files)


def parse_server_agent_metadata() -> dict:
    registry = json.loads(read_text(AGENT_DESCRIPTOR_REGISTRY))
    live_agents = {}
    for entry in registry.get("agents", []):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "").strip().lower() != "live":
            continue
        agent_id = str(entry.get("id") or "").strip()
        if agent_id:
            live_agents[agent_id] = entry
    if not live_agents:
        raise AssertionError("No live agents found in agent-descriptor-registry.json")
    return live_agents


def parse_agent_ids_from_init() -> set[str]:
    module = ast.parse(read_text(AGENTS_INIT))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_AGENT_FACTORIES":
                if isinstance(node.value, ast.Dict):
                    keys: set[str] = set()
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            keys.add(key.value)
                    return keys
    raise AssertionError("_AGENT_FACTORIES not found in agents/__init__.py")


def parse_agent_ids_from_docs() -> set[str]:
    rows = re.findall(r"\| \*\*([^*]+)\*\* \| [^|]+ \| [^|]+ \| Live \|", read_text(AGENTS_DOC))
    return {normalize_agent_name(name) for name in rows}


def parse_compose_envs() -> set[str]:
    envs: set[str] = set()
    for line in read_text(DASHBOARD_TEMPLATE).splitlines():
        match = re.search(r"- ([A-Z0-9_]+)=", line.strip())
        if match:
            envs.add(match.group(1))
    return envs


def parse_litellm_alias_targets() -> dict[str, str]:
    text = read_text(LITELLM_TEMPLATE)
    pattern = re.compile(
        r'- model_name: "([^"]+)"\s+litellm_params:\s+model: "[^"]+"\s+api_base: "([^"]+)"',
        re.MULTILINE,
    )
    return {name: api_base for name, api_base in pattern.findall(text)}


def parse_litellm_model_names() -> set[str]:
    text = read_text(LITELLM_TEMPLATE)
    return set(re.findall(r'- model_name: "([^"]+)"', text))


def parse_litellm_template_env_names() -> set[str]:
    text = read_text(LITELLM_TEMPLATE)
    return set(re.findall(r"os\.environ/([A-Z0-9_]+)", text))


def parse_vault_litellm_task_env_names() -> set[str]:
    text = read_text(VAULT_LITELLM_TASKS)
    return set(re.findall(r"^\s{6}([A-Z0-9_]+):", text, re.MULTILINE))


def parse_vault_litellm_default_names() -> set[str]:
    text = read_text(VAULT_LITELLM_DEFAULTS)
    return set(re.findall(r"^(litellm_[a-z0-9_]+):", text, re.MULTILINE))


def parse_dashboard_project_registry_ids() -> set[str]:
    text = read_text(DASHBOARD_CONFIG)
    block = re.search(r"projectRegistry:\s*\[(.*?)\],\s*grafanaDashboards:", text, re.DOTALL)
    if not block:
        raise AssertionError("dashboard projectRegistry block not found")
    return set(re.findall(r'id:\s*"([^"]+)"', block.group(1)))


def parse_agent_project_registry_ids() -> set[str]:
    text = read_text(PROJECTS_MODULE)
    return set(re.findall(r'"([^"]+)":\s*ProjectDefinition\(', text))


class RepoContractsTest(unittest.TestCase):
    def test_agent_docs_and_runtime_roster_match(self) -> None:
        runtime_ids = set(parse_server_agent_metadata().keys())
        init_ids = parse_agent_ids_from_init()
        documented_ids = parse_agent_ids_from_docs()

        self.assertEqual(runtime_ids, init_ids, "server.py and agents/__init__.py disagree on live agent ids")
        self.assertEqual(runtime_ids, documented_ids, "AGENTS.md agent roster drifted from runtime metadata")

    def test_dashboard_env_contract_matches_ansible_template(self) -> None:
        exported_envs = parse_compose_envs()
        self.assertEqual(
            set(),
            CANONICAL_DASHBOARD_ENVS - exported_envs,
            "Dashboard compose template is missing canonical env exports",
        )

    def test_litellm_alias_map_matches_frozen_runtime_slots(self) -> None:
        alias_map = parse_litellm_alias_targets()
        for alias, expected_target in FROZEN_LITELLM_ALIASES.items():
            self.assertEqual(expected_target, alias_map.get(alias), f"LiteLLM alias {alias} routes to the wrong runtime")

    def test_provider_catalog_vault_proxy_aliases_exist_in_litellm_template(self) -> None:
        model_names = parse_litellm_model_names()
        registry = json.loads(read_text(PROVIDER_CATALOG_REGISTRY))
        for provider in registry.get("providers", []):
            evidence = dict(provider.get("evidence") or {})
            if str(evidence.get("kind") or "") != "vault_litellm_proxy":
                continue
            proxy = dict(evidence.get("proxy") or {})
            alias = str(proxy.get("alias") or "")
            self.assertIn(alias, model_names, f"{provider.get('id')} proxy alias {alias!r} is missing from LiteLLM template")
            preferred_models = [str(item) for item in proxy.get("preferred_models", []) if str(item).strip()]
            self.assertTrue(preferred_models, f"{provider.get('id')} must declare proxy preferred_models")
            self.assertTrue(
                set(preferred_models) <= model_names,
                f"{provider.get('id')} preferred_models are not all present in LiteLLM template: {preferred_models}",
            )

    def test_vault_litellm_task_env_covers_template_provider_envs(self) -> None:
        template_envs = parse_litellm_template_env_names() - {"LITELLM_MASTER_KEY"}
        task_envs = parse_vault_litellm_task_env_names()
        self.assertTrue(
            template_envs <= task_envs,
            f"vault-litellm task env is missing template provider contracts: {sorted(template_envs - task_envs)}",
        )

    def test_vault_litellm_credential_surface_matches_catalog_and_template(self) -> None:
        template_envs = parse_litellm_template_env_names() - {"LITELLM_MASTER_KEY"}
        credential_registry = json.loads(read_text(CREDENTIAL_SURFACE_REGISTRY))
        provider_catalog = json.loads(read_text(PROVIDER_CATALOG_REGISTRY))
        vault_surface = next(
            surface
            for surface in credential_registry.get("surfaces", [])
            if str(surface.get("id") or "") == "vault-litellm-container-env"
        )
        surface_envs = {str(item) for item in vault_surface.get("env_var_names", []) if str(item).strip()}
        catalog_envs = {
            str(env_name)
            for provider in provider_catalog.get("providers", [])
            if str(dict(provider.get("evidence") or {}).get("kind") or "") == "vault_litellm_proxy"
            for env_name in provider.get("env_contracts", [])
            if str(env_name).strip()
        }
        self.assertTrue(
            template_envs <= surface_envs,
            f"vault-litellm credential surface is missing template env contracts: {sorted(template_envs - surface_envs)}",
        )
        self.assertTrue(
            catalog_envs <= surface_envs,
            f"vault-litellm credential surface is missing provider-catalog env contracts: {sorted(catalog_envs - surface_envs)}",
        )

    def test_vault_litellm_defaults_cover_provider_env_contracts(self) -> None:
        provider_catalog = json.loads(read_text(PROVIDER_CATALOG_REGISTRY))
        expected_default_names = {"litellm_master_key"} | {
            f"litellm_{env_name[:-8].lower()}_api_key"
            for provider in provider_catalog.get("providers", [])
            if str(dict(provider.get("evidence") or {}).get("kind") or "") == "vault_litellm_proxy"
            for env_name in provider.get("env_contracts", [])
            if str(env_name).endswith("_API_KEY")
        }
        default_names = parse_vault_litellm_default_names()
        self.assertTrue(
            expected_default_names <= default_names,
            f"vault-litellm defaults are missing provider env defaults: {sorted(expected_default_names - default_names)}",
        )

    def test_node1_playbook_no_longer_deploys_embedding(self) -> None:
        text = read_text(NODE1_PLAYBOOK)
        self.assertNotIn("vllm-embedding", text, "Node 1 playbook still deploys the embedding role")

    def test_neo4j_seed_topology_matches_current_runtime_map(self) -> None:
        text = read_text(NEO4J_TASKS)
        for required in [
            "foundry-coordinator",
            "foundry-coder",
            "workshop-worker",
            "dev-embedding",
            "dev-reranker",
            "workshop-open-webui",
            "vault-open-webui",
            "Node {name: 'DEV'}",
        ]:
            self.assertIn(required, text)

        for obsolete in [
            "vllm-fast",
            "MATCH (s:Service {name: 'vllm-embedding'}), (n:Node {name: 'Foundry'})",
            "MATCH (s:Service {name: 'open-webui'}), (n:Node {name: 'Workshop'})",
        ]:
            self.assertNotIn(obsolete, text)

    def test_dashboard_source_keeps_raw_ips_scoped_to_config_and_fixtures(self) -> None:
        violations: list[str] = []
        dashboard_src = REPO_ROOT / "projects" / "dashboard" / "src"
        for path in dashboard_src.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".ts", ".tsx"}:
                continue
            if ".test." in path.name or ".stories." in path.name:
                continue
            if path in ALLOWED_DASHBOARD_IP_FILES:
                continue
            text = read_text(path)
            if RAW_IP_PATTERN.search(text):
                violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Raw dashboard IP literals leaked outside config/fixtures: {violations}")

    def test_dashboard_server_config_credentials_are_exported(self) -> None:
        server_envs = set(re.findall(r"process\.env\.([A-Z0-9_]+)", read_text(DASHBOARD_SERVER_CONFIG)))
        exported_envs = parse_compose_envs()
        self.assertEqual(set(), server_envs - exported_envs, "Server-side dashboard envs are not exported by Ansible")

    def test_project_registry_fallback_matches_agent_platform_contract(self) -> None:
        self.assertEqual(CANONICAL_PROJECT_IDS, parse_agent_project_registry_ids())
        self.assertEqual(CANONICAL_PROJECT_IDS, parse_dashboard_project_registry_ids())

    def test_dashboard_code_no_longer_uses_legacy_agent_proxy_route(self) -> None:
        dashboard_paths = [REPO_ROOT / "projects" / "dashboard" / "src", DASHBOARD_SW]
        violations: list[str] = []
        for path in dashboard_paths:
            if path.is_dir():
                files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
            else:
                files = [path]
            for file_path in files:
                if file_path.suffix not in {".ts", ".tsx", ".js"}:
                    continue
                text = read_text(file_path)
                if "/api/agents/proxy" in text:
                    violations.append(str(file_path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Legacy agent proxy references remain in dashboard code: {violations}")

    def test_dashboard_governor_queue_and_dispatch_routes_remain_deleted(self) -> None:
        queue_route = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "governor" / "queue" / "route.ts"
        dispatch_route = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "governor" / "dispatch" / "route.ts"

        self.assertFalse(queue_route.exists(), "Dashboard governor queue compatibility route should remain deleted")
        self.assertFalse(dispatch_route.exists(), "Dashboard governor dispatch compatibility route should remain deleted")

    def test_dashboard_attention_routes_do_not_depend_on_legacy_governor_reads(self) -> None:
        self.assertFalse(
            DASHBOARD_ATTENTION_ROUTE.exists(),
            "/api/attention should remain pruned after overview/nav-attention convergence",
        )
        self.assertFalse(
            DASHBOARD_ATTENTION_PROACTIVE_ROUTE.exists(),
            "/api/attention/proactive should remain pruned after overview/nav-attention convergence",
        )

    def test_dashboard_attention_routes_no_longer_depend_on_legacy_governor_reads(self) -> None:
        commits_route = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "governor" / "commits" / "route.ts"
        sessions_route = REPO_ROOT / "projects" / "dashboard" / "src" / "app" / "api" / "governor" / "sessions" / "route.ts"
        self.assertFalse(
            DASHBOARD_ATTENTION_ROUTE.exists(),
            "/api/attention should remain pruned after overview/nav-attention convergence",
        )
        self.assertFalse(
            DASHBOARD_ATTENTION_PROACTIVE_ROUTE.exists(),
            "/api/attention/proactive should remain pruned after overview/nav-attention convergence",
        )
        self.assertFalse(commits_route.exists())
        self.assertFalse(sessions_route.exists())

        for component_path in [
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "agent-work-panel.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "attention-banner.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "cluster-compact.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "comfyui-live.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "goals-panel.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "live-activity-panel.tsx",
            REPO_ROOT / "projects" / "dashboard" / "src" / "components" / "eoq" / "breaking-timeline-card.tsx",
        ]:
            self.assertFalse(component_path.exists(), f"{component_path} should remain pruned from the active UI layer")

    def test_agent_uv_lock_is_ignored(self) -> None:
        gitignore = read_text(ROOT_GITIGNORE)
        self.assertIn("/projects/agents/uv.lock", gitignore)
        self.assertIn("/projects/gpu-orchestrator/uv.lock", gitignore)
        self.assertIn("/projects/gpu-orchestrator/src/gpu_orchestrator.egg-info/", gitignore)

    def test_gpu_orchestrator_uses_dev_embedding_contract(self) -> None:
        defaults_text = read_text(GPU_ORCH_DEFAULTS)
        self.assertIn("gpu_orch_vllm_node1_embed_url: \"http://{{ dev_ip | default('192.168.1.189') }}:8001\"", defaults_text)
        self.assertNotIn("gpu_orch_vllm_node1_embed_url: \"http://192.168.1.244:8001\"", defaults_text)

        config_text = read_text(GPU_ORCH_CONFIG)
        self.assertIn("ATHANOR_VLLM_EMBEDDING_URL", config_text)
        self.assertIn("default=\"http://192.168.1.189:8001\"", config_text)

        compose_text = read_text(GPU_ORCH_COMPOSE)
        self.assertIn("ATHANOR_VLLM_EMBEDDING_URL", compose_text)
        self.assertNotIn("GPU_ORCH_VLLM_NODE1_EMBED_URL=http://192.168.1.244:8001", compose_text)

    def test_task_persistence_private_helper_is_not_imported_outside_tasks_module(self) -> None:
        tasks_text = read_text(TASKS_MODULE)
        self.assertNotIn("async def _update_task", tasks_text, "tasks.py should not retain the legacy _update_task wrapper")

        violations: list[str] = []
        agents_src = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents"
        pattern = re.compile(r"from\s+\.+tasks\s+import\s+.*\b_update_task\b")

        for path in agents_src.rglob("*.py"):
            if path == TASKS_MODULE:
                continue
            text = read_text(path)
            if pattern.search(text):
                violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Private task persistence helper leaked outside tasks.py: {violations}")

    def test_full_hash_task_reads_do_not_leak_outside_task_store(self) -> None:
        task_store_text = read_text(TASK_STORE_MODULE)
        self.assertIn("async def read_all_task_records", task_store_text)

        violations: list[str] = []
        agents_src = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents"
        pattern = re.compile(r"from\s+\.+task_store\s+import\s+.*\bread_all_task_records\b")

        for path in agents_src.rglob("*.py"):
            if path == TASK_STORE_MODULE:
                continue
            text = read_text(path)
            if pattern.search(text) or "read_all_task_records(" in text:
                violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            [],
            violations,
            f"Full-hash task reads leaked outside task_store.py: {violations}",
        )

    def test_operator_scripts_use_canonical_runtime_envs(self) -> None:
        build_profile_text = read_text(BUILD_PROFILE_SCRIPT)
        self.assertIn("ATHANOR_QDRANT_URL", build_profile_text)
        self.assertIn("ATHANOR_VLLM_EMBEDDING_URL", build_profile_text)
        self.assertNotIn("ssh node1", build_profile_text)

        endpoint_harness_text = read_text(ENDPOINT_HARNESS)
        self.assertIn("ATHANOR_LITELLM_API_KEY", endpoint_harness_text)
        self.assertIn("ATHANOR_VLLM_EMBEDDING_URL", endpoint_harness_text)
        self.assertNotIn("sk-" + "athanor-litellm-2026", endpoint_harness_text)

        statusline_text = read_text(STATUSLINE_HOOK)
        self.assertIn("ATHANOR_REDIS_URL", statusline_text)
        self.assertIn("ATHANOR_REDIS_PASSWORD", statusline_text)

        redis_tool_text = read_text(MCP_REDIS_SCRIPT)
        self.assertIn("ATHANOR_REDIS_PASSWORD", redis_tool_text)

        smart_reader_text = read_text(MCP_SMART_READER_SCRIPT)
        self.assertIn("ATHANOR_REDIS_PASSWORD", smart_reader_text)
        self.assertIn("ATHANOR_LITELLM_URL", smart_reader_text)

        automation_records_text = read_text(AUTOMATION_RECORDS_SCRIPT)
        self.assertIn("ATHANOR_REDIS_PASSWORD", automation_records_text)
        self.assertIn("load_optional_runtime_env", automation_records_text)

        runtime_env_helper_text = read_text(RUNTIME_ENV_HELPER)
        self.assertIn("ATHANOR_RUNTIME_ENV_FILE", runtime_env_helper_text)
        self.assertIn(".athanor", runtime_env_helper_text)
        self.assertIn("runtime.env", runtime_env_helper_text)

        heartbeat_text = read_text(NODE_HEARTBEAT_SCRIPT)
        self.assertIn("ATHANOR_REDIS_URL", heartbeat_text)

        vault_ssh_text = read_text(VAULT_SSH_SCRIPT)
        self.assertIn("ATHANOR_VAULT_PASSWORD", vault_ssh_text)
        self.assertIn("ATHANOR_VAULT_KEY_PATH", vault_ssh_text)

        vault_ssh_ps_text = read_text(VAULT_SSH_POWERSHELL)
        self.assertIn("ATHANOR_VAULT_PASSWORD", vault_ssh_ps_text)
        self.assertIn("ATHANOR_VAULT_KEY_PATH", vault_ssh_ps_text)

        mcp_agents_text = read_text(MCP_ATHANOR_AGENTS_SCRIPT)
        self.assertIn("ATHANOR_AGENT_SERVER_URL", mcp_agents_text)

        qdrant_text = read_text(MCP_QDRANT_SCRIPT)
        self.assertIn("ATHANOR_QDRANT_URL", qdrant_text)
        self.assertIn("ATHANOR_LITELLM_URL", qdrant_text)

        bookmarks_text = read_text(PARSE_BOOKMARKS_SCRIPT)
        self.assertIn("ATHANOR_QDRANT_URL", bookmarks_text)
        self.assertIn("ATHANOR_LITELLM_URL", bookmarks_text)

        langfuse_sync_text = read_text(LANGFUSE_SYNC_SCRIPT)
        self.assertIn("ATHANOR_LANGFUSE_URL", langfuse_sync_text)
        self.assertNotIn("pk-lf-athanor", langfuse_sync_text)
        self.assertNotIn("sk-lf-athanor", langfuse_sync_text)

        model_inventory_text = read_text(MODEL_INVENTORY_SCRIPT)
        self.assertIn("ATHANOR_VAULT_HOST", model_inventory_text)
        self.assertIn("ATHANOR_VLLM_COORDINATOR_URL", model_inventory_text)
        self.assertIn("ATHANOR_VLLM_RERANKER_URL", model_inventory_text)

        session_start_text = read_text(SESSION_START_HOOK)
        self.assertIn("ATHANOR_AGENT_SERVER_URL", session_start_text)

        deploy_agents_text = read_text(DEPLOY_AGENTS_SCRIPT)
        self.assertIn("ATHANOR_AGENT_SERVER_URL", deploy_agents_text)
        self.assertIn("tar \\", deploy_agents_text)
        self.assertIn("src \\", deploy_agents_text)
        self.assertIn("config \\", deploy_agents_text)
        self.assertIn("docker-compose.yml \\", deploy_agents_text)

        export_langfuse_text = read_text(EXPORT_LANGFUSE_TRACES_SCRIPT)
        self.assertIn("ATHANOR_LANGFUSE_URL", export_langfuse_text)
        self.assertNotIn("pk-lf-athanor", export_langfuse_text)
        self.assertNotIn("sk-lf-athanor", export_langfuse_text)

        endpoint_test_text = read_text(ENDPOINT_TEST_SCRIPT)
        self.assertIn("ATHANOR_LITELLM_URL", endpoint_test_text)
        self.assertIn("ATHANOR_LANGFUSE_URL", endpoint_test_text)

    def test_secondary_app_compose_templates_export_canonical_envs(self) -> None:
        eoq_template_text = read_text(EOQ_TEMPLATE)
        self.assertIn("ATHANOR_LITELLM_URL", eoq_template_text)
        self.assertIn("ATHANOR_LITELLM_API_KEY", eoq_template_text)
        self.assertIn("ATHANOR_COMFYUI_URL", eoq_template_text)
        self.assertIn("ATHANOR_QDRANT_URL", eoq_template_text)

        ulrich_template_text = read_text(ULRICH_TEMPLATE)
        self.assertIn("ATHANOR_ULRICH_DATABASE_URL", ulrich_template_text)
        self.assertIn("ATHANOR_LITELLM_URL", ulrich_template_text)
        self.assertIn("ATHANOR_LITELLM_API_KEY", ulrich_template_text)

        eoq_config_text = read_text(EOQ_CONFIG)
        self.assertIn("ATHANOR_VAULT_HOST", eoq_config_text)
        self.assertIn("ATHANOR_NODE1_HOST", eoq_config_text)
        self.assertIn("ATHANOR_NODE2_HOST", eoq_config_text)

        ulrich_config_text = read_text(ULRICH_CONFIG)
        self.assertIn("ATHANOR_VAULT_HOST", ulrich_config_text)

    def test_repo_no_longer_tracks_known_secret_literals(self) -> None:
        violations: list[str] = []
        allowed_suffixes = {".md", ".yml", ".yaml", ".json", ".py", ".ts", ".tsx", ".js", ".sh", ".toml", ".env"}

        for path in list_tracked_repo_files():
            if path.suffix not in allowed_suffixes:
                continue
            if any(part in {".git", "node_modules", ".next", ".venv", "__pycache__"} for part in path.parts):
                continue

            text = read_text(path)
            for literal in BANNED_LITERAL_SECRETS:
                if literal in text:
                    violations.append(f"{path.relative_to(REPO_ROOT)}::{literal}")

        self.assertEqual([], violations, f"Tracked secret-like literals remain in repo: {violations}")

    def test_active_planning_scripts_use_live_backlog_not_build_manifest(self) -> None:
        for path in [INTENT_MINER_MODULE, MORNING_MANAGER_SCRIPT, INDEX_KNOWLEDGE_SCRIPT]:
            text = read_text(path)
            self.assertNotIn("docs/BUILD-MANIFEST.md", text, f"{path} still depends on BUILD-MANIFEST.md")
            self.assertIn("CONTINUOUS-COMPLETION-BACKLOG.md", text, f"{path} does not use the live execution backlog")

    def test_build_manifest_is_archived_and_live_helpers_use_backlog(self) -> None:
        self.assertFalse(ACTIVE_BUILD_MANIFEST.exists(), "docs/BUILD-MANIFEST.md should not remain in the active truth layer")
        self.assertTrue(ARCHIVED_BUILD_MANIFEST.exists(), "Archived build manifest is missing")

        build_command_text = read_text(BUILD_COMMAND_DOC)
        self.assertNotIn("docs/BUILD-MANIFEST.md", build_command_text)
        self.assertNotIn("docs/BUILD-ROADMAP.md", build_command_text)
        self.assertNotIn("The manifest is updated", build_command_text)
        self.assertIn("CONTINUOUS-COMPLETION-BACKLOG.md", build_command_text)

        self.assertFalse(
            ACTIVE_DAILY_OPERATIONS_DOC.exists(),
            "docs/guides/daily-operations.md should not remain in the active truth layer",
        )

        platform_topology_text = read_text(PLATFORM_TOPOLOGY_REGISTRY)
        self.assertNotIn("build-manifest", platform_topology_text.lower())

    def test_master_plan_uses_provider_catalog_for_live_provider_truth_and_tactical_snapshot_is_archived(self) -> None:
        self.assertFalse(ACTIVE_TACTICAL_PLAN.exists(), "Stale tactical planning snapshot should not remain in the active truth layer")
        self.assertFalse(
            ACTIVE_TACTICAL_PLAN_FULL.exists(),
            "Stale full tactical planning snapshot should not remain in the active truth layer",
        )
        self.assertTrue(ARCHIVED_TACTICAL_PLAN_FULL.exists(), "Archived full tactical planning snapshot is missing")

        master_plan_text = read_text(MASTER_PLAN_DOC)
        self.assertNotIn("FINAL CANONICAL DOCUMENT", master_plan_text)
        self.assertNotIn("Both are canonical", master_plan_text)
        self.assertNotIn("$543.91/mo", master_plan_text)
        self.assertNotIn("Claude Max 20x", master_plan_text)
        self.assertNotIn("Venice AI Pro", master_plan_text)
        self.assertNotIn("docs/superpowers/specs/2026-03-18-athanor-coo-architecture-FULL.md", master_plan_text)
        self.assertIn("provider-catalog.json", master_plan_text)
        self.assertIn("PROVIDER-CATALOG-REPORT.md", master_plan_text)
        self.assertNotIn("docs/archive/planning-era/2026-03-18-athanor-coo-architecture.md", master_plan_text)
        self.assertIn("docs/archive/planning-era/2026-03-18-athanor-coo-architecture-FULL.md", master_plan_text)

    def test_historical_hardware_ledger_is_archived_and_helper_docs_use_archive_path(self) -> None:
        self.assertFalse(ACTIVE_HARDWARE_LEDGER.exists(), "docs/hardware/inventory.md should not remain in the active truth layer")
        self.assertTrue(ARCHIVED_HARDWARE_LEDGER.exists(), "Archived hardware ledger is missing")

        reference_index_text = read_text(REFERENCE_INDEX_DOC)
        self.assertNotIn("docs/hardware/inventory.md", reference_index_text)
        self.assertNotIn("02-hardware/inventory.md", reference_index_text)
        self.assertIn("docs/archive/hardware/hardware-inventory.md", reference_index_text)

        for path in [
            DOC_WRITER_AGENT_DOC,
            INFRA_AUDITOR_AGENT_DOC,
            DOCS_SYNC_RULE,
            STATE_UPDATE_SKILL,
            VERIFY_INVENTORY_SKILL,
        ]:
            text = read_text(path)
            self.assertNotIn("docs/hardware/inventory.md", text, f"{path} still points at the old hardware ledger path")
            self.assertIn(
                "docs/archive/hardware/hardware-inventory.md",
                text,
                f"{path} does not point at the archived hardware ledger",
            )

    def test_visual_system_docs_no_longer_depend_on_atlas_route_inventory(self) -> None:
        for path in [VISUAL_SYSTEM_README, VISUAL_SYSTEM_AUDIT]:
            text = read_text(path)
            self.assertNotIn("docs/atlas/UI_ATLAS.md", text, f"{path} still depends on atlas UI inventory")
            self.assertNotIn("docs/atlas/inventory/ui-inventory.json", text, f"{path} still depends on atlas UI inventory JSON")
            self.assertIn("projects/dashboard/src/lib/navigation.ts", text, f"{path} does not point at the live dashboard route inventory")
            self.assertIn(
                "projects/dashboard/docs/OPERATOR-ROUTE-CONTRACTS.md",
                text,
                f"{path} does not point at the live operator route contract",
            )

    def test_legacy_atlas_validator_is_retired_and_live_atlas_docs_use_current_truth(self) -> None:
        self.assertFalse(LEGACY_ATLAS_VALIDATOR.exists(), "scripts/validate-atlas.py should be retired")

        scripts_readme_text = read_text(SCRIPTS_README)
        self.assertNotIn("validate-atlas.py", scripts_readme_text)

        atlas_readme_text = read_text(ATLAS_README)
        self.assertNotIn("TOPOLOGY_ATLAS.md", atlas_readme_text)
        self.assertNotIn("UI_ATLAS.md", atlas_readme_text)
        self.assertNotIn("API_ATLAS.md", atlas_readme_text)
        self.assertNotIn("inventory/atlas-record.schema.json", atlas_readme_text)
        self.assertIn("reports/completion-audit/latest/inventory/", atlas_readme_text)
        self.assertIn("validate_platform_contract.py", atlas_readme_text)

        reconciliation_text = read_text(ATLAS_SOURCE_RECONCILIATION)
        self.assertNotIn("validate-atlas.py", reconciliation_text)
        self.assertNotIn("[`TOPOLOGY_ATLAS.md`](./TOPOLOGY_ATLAS.md)", reconciliation_text)
        self.assertNotIn("[`UI_ATLAS.md`](./UI_ATLAS.md)", reconciliation_text)
        self.assertNotIn("[`API_ATLAS.md`](./API_ATLAS.md)", reconciliation_text)

    def test_command_hierarchy_atlas_and_architect_agent_use_current_governor_authority_split(self) -> None:
        atlas_text = read_text(COMMAND_HIERARCHY_ATLAS)
        self.assertNotIn("durable tasks, leases, schedules", atlas_text)
        self.assertNotIn("create tasks, issue leases, own schedules", atlas_text)
        self.assertIn("posture, fallback, release-tier", atlas_text)
        self.assertIn("pause or resume controlled execution", atlas_text)

        architect_text = read_text(ARCHITECT_AGENT_DOC)
        self.assertNotIn("Governor uses SQLite", architect_text)
        self.assertIn("Redis task store", architect_text)
        self.assertIn("compatibility and posture authority", architect_text)

    def test_governor_registry_and_system_map_keep_posture_only_authority_split(self) -> None:
        registry = json.loads(read_text(COMMAND_RIGHTS_REGISTRY))
        governor_profile = next(
            profile for profile in registry["profiles"] if profile["subject"] == "Athanor Governor"
        )
        self.assertIn("route work", governor_profile["can"])
        self.assertIn("pause or resume automation", governor_profile["can"])
        self.assertIn("choose fallback or degraded mode", governor_profile["can"])
        self.assertNotIn("create durable tasks", governor_profile["can"])
        self.assertNotIn("issue leases", governor_profile["can"])
        self.assertIn("create durable tasks", governor_profile["cannot"])
        self.assertIn("issue leases", governor_profile["cannot"])
        self.assertIn("own recurring schedules", governor_profile["cannot"])

        from athanor_agents.command_hierarchy import build_system_map_snapshot

        with (
            patch(
                "athanor_agents.governor.build_governor_snapshot",
                AsyncMock(
                    return_value={
                        "capacity": {"posture": "healthy", "active_time_windows": []},
                        "presence": {
                            "state": "at_desk",
                            "effective_reason": "repo contract",
                        },
                    }
                ),
            ),
            patch(
                "athanor_agents.governor.build_operations_readiness_snapshot",
                AsyncMock(
                    return_value={
                        "economic_governance": {
                            "status": "live_partial",
                            "provider_count": 6,
                            "recent_lease_count": 3,
                        },
                        "data_lifecycle": {
                            "status": "live_partial",
                            "run_count": 5,
                            "eval_artifact_count": 2,
                        },
                        "backup_restore": {
                            "status": "live_partial",
                            "verified_store_count": 2,
                            "last_drill_at": "2026-03-27T18:40:00Z",
                        },
                        "tool_permissions": {
                            "status": "live_partial",
                            "enforced_subject_count": 4,
                            "denied_action_count": 1,
                        },
                        "release_ritual": {
                            "status": "live_partial",
                            "active_promotion_count": 0,
                            "last_rehearsal_at": "2026-03-27T18:40:00Z",
                        },
                        "autonomy_activation": {
                            "status": "live_partial",
                            "activation_state": "ready_for_operator_enable",
                            "current_phase_id": "software_core_phase_1",
                            "current_phase_status": "ready",
                            "enabled_agents": ["coding-agent", "research-agent"],
                            "allowed_workload_classes": ["coding_implementation"],
                            "blocked_workload_classes": ["explicit_dialogue"],
                        },
                    }
                ),
            ),
        ):
            snapshot = asyncio.run(build_system_map_snapshot({}))

        governor = snapshot["governor"]
        self.assertEqual("runtime posture and fallback authority", governor["role"])
        self.assertIn("route work", governor["rights"])
        self.assertIn("pause or resume automation", governor["rights"])
        self.assertIn("choose fallback or degraded mode", governor["rights"])
        self.assertNotIn("create durable tasks", governor["rights"])
        self.assertNotIn("issue execution leases", governor["rights"])
        self.assertNotIn("schedule recurring jobs", governor["rights"])

        authority = next(entry for entry in snapshot["authority_order"] if entry["id"] == "governor")
        self.assertIn("task engine", authority["summary"])
        self.assertIn("subscription broker", authority["summary"])
        self.assertIn("scheduler", authority["summary"])
        self.assertEqual(
            "software_core_phase_1",
            snapshot["operational_governance"]["autonomy_activation"]["current_phase_id"],
        )

    def test_phase_history_reports_are_archived_out_of_active_audit_root(self) -> None:
        self.assertFalse(ACTIVE_PHASE11_REPORT.exists(), "Phase 11 report should not remain in active audit root")
        self.assertFalse(ACTIVE_PHASE16_STATUS.exists(), "Phase 16 status should not remain in active audit root")
        self.assertTrue(ARCHIVED_PHASE11_REPORT.exists(), "Archived Phase 11 report is missing")
        self.assertTrue(ARCHIVED_PHASE16_STATUS.exists(), "Archived Phase 16 status is missing")

    def test_completion_audit_common_keeps_runtime_subsystem_registry_in_control_plane(self) -> None:
        common_text = read_text(COMPLETION_AUDIT_COMMON)
        self.assertIn("runtime-subsystem-registry.json", common_text)
        self.assertNotIn("docs/atlas/inventory/runtime-inventory.json", common_text)

        registry_text = read_text(RUNTIME_SUBSYSTEM_REGISTRY)
        self.assertIn('"runtime.subsystem.task-engine"', registry_text)
        self.assertIn('"Task engine and governor posture"', registry_text)
        self.assertIn("Durable task lifecycle and canonical stats belong to the task engine.", registry_text)
        self.assertIn("standalone governor facade", registry_text)
        self.assertIn('"/governor"', registry_text)

    def test_completion_audit_runtime_subsystem_census_no_longer_depends_on_atlas_runtime_inventory(self) -> None:
        common_text = read_text(COMPLETION_AUDIT_COMMON)
        map_text = read_text(MAP_AGENT_ENDPOINTS_SCRIPT)

        self.assertNotIn(
            "docs/atlas/inventory/runtime-inventory.json",
            common_text,
            "completion_audit_common.py still depends on atlas runtime inventory",
        )
        self.assertNotIn(
            "load_runtime_inventory",
            map_text,
            "map-agent-endpoints.py still depends on atlas runtime inventory helpers",
        )
        self.assertIn(
            "athanor_agents.server import app",
            map_text,
            "map-agent-endpoints.py should derive runtime census from the live FastAPI app",
        )
        self.assertIn(
            "app.routes",
            map_text,
            "map-agent-endpoints.py should walk the live FastAPI route registry",
        )
        self.assertIn(
            "load_navigation",
            map_text,
            "map-agent-endpoints.py should map runtime subsystems back to live dashboard navigation",
        )

    def test_completion_audit_runner_uses_agents_pytest_suite(self) -> None:
        text = read_text(RUN_COMPLETION_AUDIT_SCRIPT)
        self.assertIn('"agents:tests"', text)
        self.assertIn('"dashboard:e2e:audit"', text)
        self.assertIn('"test:e2e:audit"', text)
        self.assertIn('"pytest"', text)
        self.assertIn('".venv"', text)
        self.assertNotIn('"unittest", "discover"', text)

    def test_dashboard_completion_audit_excludes_retired_and_support_only_surfaces(self) -> None:
        api_census_text = read_text(REPO_ROOT / "scripts" / "census-dashboard-api.py")
        completion_common_text = read_text(COMPLETION_AUDIT_COMMON)

        self.assertFalse(DASHBOARD_BRIEFING_ROUTE.exists(), "/api/briefing should remain pruned after digest takeover")
        self.assertFalse(
            DASHBOARD_GALLERY_FILES_ROUTE.exists(),
            "/api/gallery/files should remain pruned after overview/history convergence",
        )
        self.assertFalse(
            DASHBOARD_PIPELINE_INTENTS_ROUTE.exists(),
            "/api/pipeline/intents should remain pruned until a real pipeline intents surface exists",
        )
        self.assertFalse(
            DASHBOARD_PROJECT_STATE_ROUTE.exists(),
            "/api/projects/:projectId/state should remain pruned while projects use milestone and advance surfaces only",
        )

        for expected_path in [
            "/api/agents/proxy",
            "/api/governor/tool-permissions",
            "/api/gpu/swap",
            "/api/operator/session",
        ]:
            self.assertIn(expected_path, api_census_text, f"{expected_path} should stay classified in the API census")

        self.assertIn("ACTION_WILDCARD_SEGMENTS", api_census_text)
        self.assertIn('not path.name.endswith(".d.ts")', completion_common_text)
        self.assertIn('!= "proxy.ts"', completion_common_text)

    def test_non_archive_docs_do_not_reintroduce_stale_active_truth_paths(self) -> None:
        docs_root = REPO_ROOT / "docs"
        for stale_reference, allowed_paths in ALLOWED_STALE_DOC_PATH_MENTIONS.items():
            violations: list[str] = []
            for path in docs_root.rglob("*.md"):
                relative = path.relative_to(REPO_ROOT).as_posix()
                if relative.startswith("docs/archive/") or relative.startswith("docs/data/"):
                    continue
                if relative in allowed_paths:
                    continue
                text = read_text(path)
                if stale_reference in text:
                    violations.append(relative)
            self.assertEqual([], violations, f"Non-archive docs still reference stale active path {stale_reference}: {violations}")

    def test_provider_catalog_report_flags_supported_tool_subscription_without_verified_integration(self) -> None:
        report_text = read_text(PROVIDER_CATALOG_REPORT)
        self.assertIn("## Z.ai GLM Coding (`zai_glm_coding`)", report_text)
        self.assertIn("- State classes: `configured-unused`", report_text)
        self.assertIn("- Evidence posture: `supported_tool_subscription_unverified`", report_text)
        self.assertIn(
            "- Evidence contract: `kind=coding_tool_subscription`, `tooling_status=supported_tools_present`, `hosts=desk,dev`, `supported_tools=claude,codex,gemini`, `integration_status=unverified`, `billing_status=published_tiers_known_subscribed_tier_unverified`, `public_prices=lite:10,pro:30`",
            report_text,
        )
        self.assertIn("- Tool evidence: none", report_text)
        self.assertIn(
            "- Next verification: Verify GLM Coding Plan execution through a supported coding tool on DESK or DEV before promoting `Z.ai GLM Coding` back into live routing.",
            report_text,
        )
        self.assertIn(
            "- Verification steps: `Verify GLM Coding Plan execution through a supported coding tool on DESK or DEV before promoting `Z.ai GLM Coding` back into live routing.`, `Verify which public GLM Coding Plan tier is actually subscribed before treating any published USD price as this lane's monthly cost.`, `Until supported-tool integration is proven, keep this lane configured-unused and out of ordinary auto-routing.`",
            report_text,
        )

    def test_provider_catalog_report_flags_litellm_proxy_configured_api_lanes(self) -> None:
        report_text = read_text(PROVIDER_CATALOG_REPORT)
        self.assertIn("## DeepSeek API (`deepseek_api`)", report_text)
        self.assertIn("- Evidence posture: `vault_provider_specific_api_observed`", report_text)
        self.assertIn(
            "- Evidence contract: `kind=vault_litellm_proxy`, `alias=deepseek`, `host=vault`, `preferred_model=deepseek`, `provider_specific_status=observed`, `capture_status=observed`",
            report_text,
        )
        self.assertIn("- Observed hosts: `vault`", report_text)
        self.assertIn("- Pricing truth: `metered_api`, `unverified or metered`", report_text)
        self.assertIn(
            "- Observed runtime: `routing_policy_enabled=False`, `active_burn_observed=False`, `api_configured=True`, `proxy_activity_observed=True`, `provider_specific_usage_observed=True`, `last_verified_at=2026-03-29T03:46:16Z`",
            report_text,
        )
        self.assertIn("- Next verification: No immediate verification gap recorded.", report_text)
        self.assertIn("`requested_model=deepseek`, `response_model=deepseek`, `matched_by=preferred_exact`", report_text)
        self.assertIn("provider_usage_capture_status=observed", report_text)

        self.assertIn("## OpenAI API (`openai_api`)", report_text)
        self.assertIn("- Evidence posture: `vault_provider_specific_auth_failed`", report_text)
        self.assertIn(
            "- Next verification: Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `OpenAI API` on VAULT, then re-probe served model `gpt`.",
            report_text,
        )
        self.assertIn("provider_usage_capture_status=auth_failed", report_text)

    def test_provider_catalog_report_flags_cost_unverified_live_burn_subscription_lanes(self) -> None:
        report_text = read_text(PROVIDER_CATALOG_REPORT)
        self.assertIn("## Kimi Code (`moonshot_kimi`)", report_text)
        self.assertIn("- Evidence posture: `live_burn_observed_cost_unverified`", report_text)
        self.assertIn(
            "- Evidence contract: `kind=cli_subscription`, `cli_status=installed`, `hosts=desk,dev`, `commands=kimi`, `billing_status=operator_visible_tier_unverified`, `pricing_scope=membership_included`, `quota_cycle=7_day_rolling`",
            report_text,
        )
        self.assertIn(
            "- Next verification: Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.",
            report_text,
        )
        self.assertIn(
            "- Verification steps: `Verify the subscribed monthly tier or billing surface for `Kimi Code` from a current operator-visible source.`, `Keep this lane cost-unverified until the billing tier is proven from a current runtime-visible or operator-visible surface.`",
            report_text,
        )

    def test_provider_catalog_uses_pricing_specific_sources_for_weak_provider_lanes(self) -> None:
        registry = json.loads(read_text(PROVIDER_CATALOG_REGISTRY))
        providers = {str(entry.get("id") or ""): entry for entry in registry.get("providers", [])}

        gemini_api_sources = [str(item.get("url") or "") for item in providers["google_gemini_api"].get("official_sources", [])]
        self.assertIn("https://ai.google.dev/gemini-api/docs/pricing", gemini_api_sources)
        self.assertIn("https://ai.google.dev/gemini-api/docs/billing/", gemini_api_sources)

        moonshot_kimi_sources = [str(item.get("url") or "") for item in providers["moonshot_kimi"].get("official_sources", [])]
        self.assertNotIn("https://platform.moonshot.ai/", moonshot_kimi_sources)
        self.assertIn("https://www.kimi.com/code/docs/en/benefits.html", moonshot_kimi_sources)

        moonshot_api_sources = [str(item.get("url") or "") for item in providers["moonshot_api"].get("official_sources", [])]
        self.assertIn("https://platform.moonshot.ai/blog/posts/Kimi_API_Newsletter", moonshot_api_sources)

        dashscope_sources = [str(item.get("url") or "") for item in providers["dashscope_qwen_api"].get("official_sources", [])]
        self.assertIn("https://www.alibabacloud.com/help/en/model-studio/model-pricing", dashscope_sources)

    def test_subscription_policy_declares_explicit_routing_posture_for_glm(self) -> None:
        policy_text = read_text(REPO_ROOT / "projects" / "agents" / "config" / "subscription-routing-policy.yaml")
        self.assertIn("zai_glm_coding:", policy_text)
        self.assertIn("routing_posture: governed_handoff_only", policy_text)
        self.assertIn("routing_reason: missing_cli_evidence", policy_text)

    def test_subscription_policy_no_longer_uses_builtin_fallback_policy(self) -> None:
        subscriptions_text = read_text(REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "subscriptions.py")
        self.assertNotIn("_fallback_policy", subscriptions_text)
        self.assertNotIn('builtin-fallback', subscriptions_text)

    def test_provider_usage_evidence_artifact_and_runbook_exist(self) -> None:
        artifact = json.loads(read_text(REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"))
        captures = artifact.get("captures", [])
        self.assertTrue(captures, "provider usage evidence artifact should contain live captures once probes run")
        provider_ids = {str(entry.get("provider_id") or "") for entry in captures if isinstance(entry, dict)}
        self.assertTrue({"deepseek_api", "mistral_codestral_api", "venice_api", "openai_api"} <= provider_ids)
        runbook_text = read_text(REPO_ROOT / "docs" / "runbooks" / "provider-evidence-capture.md")
        self.assertIn("probe_provider_usage_evidence.py", runbook_text)
        self.assertIn("record_provider_usage_evidence.py", runbook_text)

    def test_legacy_governor_automation_uses_canonical_task_routes(self) -> None:
        self_improve_text = read_text(LEGACY_GOVERNOR_SELF_IMPROVE)
        self.assertIn('/v1/tasks', self_improve_text)
        self.assertNotIn('GOVERNOR}/tasks', self_improve_text)

        overnight_text = read_text(LEGACY_GOVERNOR_OVERNIGHT)
        self.assertIn('/v1/tasks?status=pending&limit=50', overnight_text)
        self.assertIn('/v1/tasks/dispatch', overnight_text)
        self.assertNotIn('/queue', overnight_text)
        self.assertNotIn('/dispatch-and-run', overnight_text)

        act_first_text = read_text(LEGACY_GOVERNOR_ACT_FIRST)
        self.assertIn('/v1/tasks?limit=50', act_first_text)
        self.assertNotIn('/queue', act_first_text)
        self.assertNotIn('task["status"] = "queued"', act_first_text)

        status_report_text = read_text(LEGACY_GOVERNOR_STATUS_REPORT)
        self.assertIn('/v1/tasks/stats', status_report_text)
        self.assertNotIn('GOVERNOR}/stats', status_report_text)

    def test_ci_runs_governor_helper_contracts(self) -> None:
        ci_text = read_text(REPO_ROOT / ".gitea" / "workflows" / "ci.yml")
        self.assertIn("Governor helper contract", ci_text)
        self.assertIn("services/governor/tests", ci_text)
        self.assertIn("services/governor/requirements-test.txt", ci_text)
        self.assertIn("python3 -m pytest services/governor/tests -q", ci_text)

    def test_legacy_governor_queue_routes_are_removed_from_active_services(self) -> None:
        legacy_refs = ("/queue", "/dispatch-and-run")
        violations: list[str] = []

        for path in (REPO_ROOT / "services").rglob("*.py"):
            if "tests" in path.parts:
                continue
            text = read_text(path)
            if not any(reference in text for reference in legacy_refs):
                continue
            violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            [],
            violations,
            f"Legacy governor queue routes remain in active services: {violations}",
        )

    def test_legacy_governor_main_is_deleted_from_implementation_authority(self) -> None:
        self.assertFalse(
            LEGACY_GOVERNOR_MAIN.exists(),
            "services/governor/main.py should stay deleted once the runtime cutover is verified",
        )

        sentinel_text = read_text(SENTINEL_CHECKS)
        self.assertIn('/v1/tasks/stats', sentinel_text)
        self.assertNotIn('http://localhost:8760/queue', sentinel_text)
        self.assertNotIn('http://localhost:8760/health', sentinel_text)

    def test_subscription_burn_surface_stays_limited_to_live_burn_lanes(self) -> None:
        burn_text = read_text(SUBSCRIPTION_BURN_SCRIPT)
        self.assertTrue(SUBSCRIPTION_BURN_REGISTRY.exists())
        self.assertIn("BURN_REGISTRY_PATH", burn_text)
        self.assertIn("load_subscription_burn_registry", burn_text)
        self.assertIn("build_runtime_subscriptions_from_registry", burn_text)
        self.assertIn("build_burn_schedule_from_registry", burn_text)
        self.assertIn("apply_burn_registry", burn_text)
        self.assertNotIn('SUBSCRIPTIONS = {\n    "claude_max"', burn_text)
        self.assertNotIn('BURN_SCHEDULE = [\n    {"hour": 7', burn_text)
        self.assertNotIn('"zai_glm_pro"', burn_text)
        self.assertNotIn('"venice_pro"', burn_text)
        self.assertNotIn('"cost_per_month": 19', burn_text)
        self.assertNotIn('"cost_per_month": 30', burn_text)
        self.assertNotIn('"cost_per_month": 12', burn_text)

    def test_cli_router_derives_provider_truth_from_canonical_policy(self) -> None:
        router_text = read_text(CLI_ROUTER_SCRIPT)
        self.assertNotIn("TASK_RULES: dict[str, list[str]]", router_text)
        self.assertNotIn("CLI_TO_SUB: dict[str, str]", router_text)
        self.assertIn("POLICY_PATH", router_text)
        self.assertIn("PROVIDER_CATALOG_PATH", router_text)
        self.assertIn("_load_policy", router_text)
        self.assertIn("_provider_catalog_snapshot", router_text)
        self.assertIn("_canonical_cli_candidates", router_text)
        self.assertIn("policy_preference", router_text)

    def test_task_submission_producers_use_canonical_governed_helper(self) -> None:
        producer_paths = (
            TASKS_ROUTE_MODULE,
            EXECUTION_TOOLS_MODULE,
            SCHEDULER_MODULE,
            WORKPLANNER_MODULE,
            WORKSPACE_MODULE,
            WORK_PIPELINE_MODULE,
        )
        for path in producer_paths:
            text = read_text(path)
            self.assertIn("submit_governed_task", text, f"{path} should use the canonical governed submission helper")
        for path in (TASKS_ROUTE_MODULE, SCHEDULER_MODULE, WORKPLANNER_MODULE, WORKSPACE_MODULE):
            text = read_text(path)
            self.assertNotIn("gate_task_submission(", text, f"{path} should not gate task submission directly")
        for path in (EXECUTION_TOOLS_MODULE, SCHEDULER_MODULE, WORK_PIPELINE_MODULE, RESEARCH_JOBS_MODULE, CASCADE_MODULE):
            text = read_text(path)
            self.assertNotIn("submit_task(", text, f"{path} should not bypass the canonical governed submission helper")

    def test_retired_legacy_governor_sqlite_artifacts_are_not_active_truth(self) -> None:
        self.assertFalse(
            LEGACY_GOVERNOR_DISPATCHER.exists(),
            "services/governor/dispatch.py should be deleted after facade cutover",
        )
        self.assertFalse(
            LEGACY_GOVERNOR_DISPATCH_LOOP.exists(),
            "services/governor/continuous_dispatch.py should be deleted after facade cutover",
        )
        self.assertFalse(
            LEGACY_GOVERNOR_DB_MODULE.exists(),
            "services/governor/db.py should be deleted after facade cutover",
        )
        self.assertFalse(
            (REPO_ROOT / "services" / "governor" / "archive" / "governor.db").exists(),
            "Historical governor.db should be deleted once the facade cutover is verified",
        )
        self.assertTrue(GOVERNOR_ARCHIVE_README.exists(), "Governor archive README is missing")

    def test_legacy_governor_local_helper_scripts_match_live_runtime_truth(self) -> None:
        self.assertFalse(
            LEGACY_GOVERNOR_MORNING_SUMMARY.exists(),
            "services/governor/morning_summary.py should be deleted once no live runtime ownership remains in repo truth",
        )
        self.assertFalse(
            LEGACY_GOVERNOR_TASK_MONITOR.exists(),
            "services/governor/task_monitor.py should be deleted once local tmux/log queue ownership is retired",
        )

        drift_check_text = read_text(DRIFT_CHECK_SCRIPT)
        self.assertNotIn('GOVERNOR_URL=', drift_check_text)
        self.assertNotIn('compat_mode', drift_check_text)
        self.assertNotIn('journal_mode', drift_check_text)
        self.assertNotIn('services", "governor", "*.db"', drift_check_text)
        self.assertNotIn('find "${REPO_ROOT}/services/governor" -maxdepth 1 -name "*.py"', drift_check_text)
        self.assertIn('GOVERNOR_HELPER_FILES=(', drift_check_text)
        self.assertIn('/services/governor/${helper_file}', drift_check_text)
        for helper_path in ACTIVE_GOVERNOR_HELPER_MODULES:
            self.assertIn(
                f'"{helper_path.name}"',
                drift_check_text,
                f"drift-check.sh should compile the approved governor helper {helper_path.name}",
            )

        troubleshooting_text = read_text(TROUBLESHOOTING_DOC)
        self.assertNotIn("services/governor/governor.db", troubleshooting_text)
        self.assertIn("retired and removed from the live DEV runtime", troubleshooting_text)
        self.assertIn("/v1/governor", troubleshooting_text)
        self.assertIn("/v1/tasks/stats", troubleshooting_text)

        imports_text = read_text(LEGACY_GOVERNOR_IMPORTS)
        self.assertNotIn("GOVERNOR_URL", imports_text)

    def test_governor_facade_runtime_refs_are_quarantined(self) -> None:
        allowed_8760_refs = {
            TROUBLESHOOTING_DOC,
            GOVERNOR_FACADE_RETIREMENT_RUNBOOK,
            RUNTIME_MIGRATION_REPORT_DOC,
            RUNTIME_CUTOVER_PACKET_DOC,
        }
        allowed_service_name_refs = {
            TROUBLESHOOTING_DOC,
            GOVERNOR_FACADE_RETIREMENT_RUNBOOK,
            OPERATOR_RUNBOOKS_DOC,
            BACKLOG_DOC,
            GOVERNOR_AUTHORITY_MATRIX_DOC,
            REPO_ROOTS_REPORT_DOC,
            TRUTH_DRIFT_REPORT_DOC,
            RUNTIME_MIGRATION_REPORT_DOC,
            RUNTIME_CUTOVER_PACKET_DOC,
        }

        active_doc_roots = (REPO_ROOT / "docs",)
        ignored_parts = {"archive", "research"}

        facade_url_violations: list[str] = []
        facade_service_violations: list[str] = []

        for root in active_doc_roots:
            for path in root.rglob("*.md"):
                if any(part in ignored_parts for part in path.parts):
                    continue
                text = read_text(path)
                if "127.0.0.1:8760" in text and path not in allowed_8760_refs:
                    facade_url_violations.append(str(path.relative_to(REPO_ROOT)))
                if "athanor-governor" in text and path not in allowed_service_name_refs:
                    facade_service_violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual([], facade_url_violations, f"Unexpected active-doc 8760 refs: {facade_url_violations}")
        self.assertEqual(
            [],
            facade_service_violations,
            f"Unexpected active-doc athanor-governor refs: {facade_service_violations}",
        )

    def test_governor_facade_retirement_runbook_matches_current_contract(self) -> None:
        runbook_text = read_text(GOVERNOR_FACADE_RETIREMENT_RUNBOOK)
        self.assertIn("ask-first runtime lane", runbook_text)
        self.assertIn("athanor-governor.service", runbook_text)
        self.assertIn("http://127.0.0.1:8760/health", runbook_text)
        self.assertIn("/v1/governor", runbook_text)
        self.assertIn("/v1/tasks/stats", runbook_text)
        self.assertIn("python scripts/collect_truth_inventory.py", runbook_text)
        self.assertIn("implementation-authority facade file is deleted", runbook_text)
        self.assertIn("RUNTIME-MIGRATION-REPORT.md", runbook_text)
        self.assertIn("/home/shaun/.athanor/backups/governor-facade-cutover", runbook_text)

    def test_stale_dashboard_and_agent_framework_research_docs_are_archived(self) -> None:
        self.assertFalse(ACTIVE_DASHBOARD_RESEARCH.exists())
        self.assertFalse(ACTIVE_AGENT_FRAMEWORK_RESEARCH.exists())
        self.assertFalse(ACTIVE_BASE_PLATFORM_RESEARCH.exists())
        self.assertFalse(ACTIVE_NETWORK_RESEARCH.exists())
        self.assertFalse(ACTIVE_STORAGE_RESEARCH.exists())
        self.assertFalse(ACTIVE_NODE_ROLES_RESEARCH.exists())
        self.assertFalse(ACTIVE_INFERENCE_RESEARCH.exists())
        self.assertFalse(ACTIVE_CREATIVE_RESEARCH.exists())
        self.assertFalse(ACTIVE_MONITORING_RESEARCH.exists())
        self.assertFalse(ACTIVE_HOME_AUTOMATION_RESEARCH.exists())
        self.assertFalse(ACTIVE_MEDIA_STACK_RESEARCH.exists())
        self.assertFalse(ACTIVE_REMOTE_ACCESS_RESEARCH.exists())
        self.assertFalse(ACTIVE_VOICE_INTERACTION_RESEARCH.exists())
        self.assertFalse(ACTIVE_COMMAND_CENTER_UI_RESEARCH.exists())
        self.assertFalse(ACTIVE_RESEARCH_ROADMAP.exists())
        self.assertFalse(ACTIVE_DASHBOARD_INTERACTIONS.exists())

        self.assertTrue(ARCHIVED_DASHBOARD_RESEARCH.exists())
        self.assertTrue(ARCHIVED_AGENT_FRAMEWORK_RESEARCH.exists())
        self.assertTrue(ARCHIVED_BASE_PLATFORM_RESEARCH.exists())
        self.assertTrue(ARCHIVED_NETWORK_RESEARCH.exists())
        self.assertTrue(ARCHIVED_STORAGE_RESEARCH.exists())
        self.assertTrue(ARCHIVED_NODE_ROLES_RESEARCH.exists())
        self.assertTrue(ARCHIVED_INFERENCE_RESEARCH.exists())
        self.assertTrue(ARCHIVED_CREATIVE_RESEARCH.exists())
        self.assertTrue(ARCHIVED_MONITORING_RESEARCH.exists())
        self.assertTrue(ARCHIVED_HOME_AUTOMATION_RESEARCH.exists())
        self.assertTrue(ARCHIVED_MEDIA_STACK_RESEARCH.exists())
        self.assertTrue(ARCHIVED_REMOTE_ACCESS_RESEARCH.exists())
        self.assertTrue(ARCHIVED_VOICE_INTERACTION_RESEARCH.exists())
        self.assertTrue(ARCHIVED_COMMAND_CENTER_UI_RESEARCH.exists())

        adr_dashboard_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-007-dashboard.md")
        self.assertIn("../archive/research/2026-02-15-dashboard.md", adr_dashboard_text)

        adr_agent_framework_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-008-agent-framework.md")
        self.assertIn("../archive/research/2026-02-15-agent-framework.md", adr_agent_framework_text)

        adr_base_platform_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-001-base-platform.md")
        self.assertIn("../archive/research/2026-02-15-base-platform.md", adr_base_platform_text)

        adr_network_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-002-network-architecture.md")
        self.assertIn("../archive/research/2026-02-15-network-architecture.md", adr_network_text)

        adr_storage_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-003-storage-architecture.md")
        self.assertIn("../archive/research/2026-02-15-storage-architecture.md", adr_storage_text)

        adr_node_roles_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-004-node-roles.md")
        self.assertIn("../archive/research/2026-02-15-node-roles.md", adr_node_roles_text)

        adr_inference_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-005-inference-engine.md")
        self.assertIn("../archive/research/2026-02-15-inference-engine.md", adr_inference_text)

        adr_creative_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-006-creative-pipeline.md")
        self.assertIn("../archive/research/2026-02-15-creative-pipeline.md", adr_creative_text)

        adr_monitoring_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-009-monitoring.md")
        self.assertIn("../archive/research/2026-02-15-monitoring.md", adr_monitoring_text)

        adr_home_automation_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-010-home-automation.md")
        self.assertIn("../archive/research/2026-02-15-home-automation.md", adr_home_automation_text)

        adr_media_stack_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-011-media-stack.md")
        self.assertIn("../archive/research/2026-02-15-media-stack.md", adr_media_stack_text)

        adr_remote_access_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-016-remote-access.md")
        self.assertIn("docs/archive/research/2026-02-24-remote-access.md", adr_remote_access_text)

        adr_command_center_text = read_text(REPO_ROOT / "docs" / "decisions" / "ADR-019-command-center.md")
        self.assertIn("docs/archive/research/2026-02-25-command-center-ui-design.md", adr_command_center_text)

        command_center_text = read_text(REPO_ROOT / "docs" / "design" / "command-center.md")
        self.assertIn("docs/archive/research/2026-02-25-command-center-ui-design.md", command_center_text)

    def test_runtime_migration_registry_tracks_governor_facade_callers(self) -> None:
        registry = json.loads(read_text(RUNTIME_MIGRATION_REGISTRY))
        migration = next(
            entry for entry in registry.get("migrations", []) if entry.get("id") == "dev-governor-facade-8760-callers"
        )
        self.assertEqual("retired", migration.get("status"))
        self.assertEqual("docs/runbooks/governor-facade-retirement.md", migration.get("runbook_path"))
        self.assertEqual("docs/operations/RUNTIME-MIGRATION-REPORT.md", migration.get("generated_report_path"))
        self.assertEqual("/home/shaun/.athanor/backups/governor-facade-cutover", migration.get("runtime_backup_root"))
        self.assertEqual(
            "/home/shaun/.athanor/backups/governor-facade-cutover/athanor-governor.service",
            migration.get("systemd_backup_target"),
        )
        self.assertTrue(migration.get("acceptance_criteria"))
        self.assertTrue(migration.get("delete_gate"))

        callers = {str(item.get("path") or ""): item for item in migration.get("callers", [])}
        self.assertEqual(EXPECTED_GOVERNOR_FACADE_CALLERS, set(callers))
        sync_orders = [callers[path].get("sync_order") for path in sorted(callers)]
        self.assertEqual(len(sync_orders), len(set(sync_orders)))
        self.assertEqual(
            EXPECTED_GOVERNOR_FACADE_CALLER_SYNC_ORDER,
            {caller_path: callers[caller_path].get("sync_order") for caller_path in callers},
        )

        for caller_path, caller in callers.items():
            self.assertIsInstance(caller.get("sync_order"), int)
            self.assertTrue(caller.get("current_purpose"))
            self.assertTrue(caller.get("canonical_replacement"))
            self.assertTrue(caller.get("canonical_targets"))
            self.assertTrue(caller.get("replacement_owner_paths"))
            self.assertTrue(caller.get("repo_side_gates"))
            self.assertTrue(caller.get("ask_first_required"))
            self.assertEqual("migrated", caller.get("implementation_state"))
            self.assertEqual("cutover_verified", caller.get("runtime_cutover_state"))
            self.assertEqual(
                f"/home/shaun/repos/athanor/{caller_path}",
                caller.get("runtime_owner_path"),
            )
            self.assertEqual(
                "backup_then_replace_from_implementation_authority",
                caller.get("sync_strategy"),
            )
            self.assertEqual(
                f"/home/shaun/.athanor/backups/governor-facade-cutover/{caller_path}",
                caller.get("rollback_target"),
            )
            caller_text = read_text(REPO_ROOT / caller_path)
            for forbidden in MIGRATED_GOVERNOR_FACADE_FORBIDDEN_TOKENS:
                self.assertNotIn(
                    forbidden,
                    caller_text,
                    f"{caller_path} is marked migrated but still references retired facade token {forbidden!r}",
                )

    def test_runtime_migration_report_and_drift_report_reference_governor_facade_cutover(self) -> None:
        runtime_migration_text = read_text(RUNTIME_MIGRATION_REPORT_DOC)
        self.assertIn("dev-governor-facade-8760-callers", runtime_migration_text)
        self.assertIn("Runtime-Owned Caller Map", runtime_migration_text)
        self.assertIn("Runtime Sync Verification Checklist", runtime_migration_text)
        self.assertIn("Runtime backup root", runtime_migration_text)
        self.assertIn("Systemd backup target", runtime_migration_text)
        self.assertIn("Sync order", runtime_migration_text)
        self.assertIn("Sync decision", runtime_migration_text)
        self.assertIn("Sync strategy", runtime_migration_text)
        self.assertIn("Rollback target", runtime_migration_text)
        self.assertIn("Rollback ready", runtime_migration_text)
        self.assertIn("Next action", runtime_migration_text)
        for caller_path in EXPECTED_GOVERNOR_FACADE_CALLERS:
            self.assertIn(caller_path, runtime_migration_text)

        truth_drift_text = read_text(TRUTH_DRIFT_REPORT_DOC)
        self.assertIn("Retired Runtime Migration Seams", truth_drift_text)
        self.assertIn("RUNTIME-MIGRATION-REPORT.md", truth_drift_text)

    def test_runtime_cutover_packet_tracks_governor_facade_sync_commands(self) -> None:
        packet_text = read_text(RUNTIME_CUTOVER_PACKET_DOC)
        self.assertIn("Governor Facade Cutover Packet", packet_text)
        self.assertIn("Recorded Preflight Commands", packet_text)
        self.assertIn("Recorded Caller Sync Commands", packet_text)
        self.assertIn("Post-Cutover Verification Record", packet_text)
        self.assertIn("systemctl cat athanor-governor.service", packet_text)
        self.assertIn("python scripts/generate_truth_inventory_reports.py --report runtime_migrations --report runtime_cutover --check", packet_text)
        self.assertIn("# scripts/drift-check.sh already matches implementation authority; no file copy required.", packet_text)
        for caller_path in EXPECTED_GOVERNOR_FACADE_CALLERS:
            self.assertIn(caller_path, packet_text)

    def test_operator_runbooks_registry_includes_current_runtime_runbooks(self) -> None:
        registry = json.loads(read_text(OPERATOR_RUNBOOKS_REGISTRY))
        runbook_ids = {str(entry.get("id") or "") for entry in registry.get("runbooks", [])}
        self.assertTrue(
            {
                "local-runtime-env-bootstrap",
                "dev-secret-delivery-normalization",
                "governor-facade-retirement",
                "constrained-mode",
                "degraded-mode",
                "recovery-only",
                "postgres-restore",
                "redis-reconciliation",
                "failed-promotion",
                "stuck-media-pipeline",
                "source-auth-expiry",
                "model-lane-outage",
                "operator-auth-failure",
            }
            <= runbook_ids
        )

        operator_runbooks_text = read_text(OPERATOR_RUNBOOKS_DOC)
        self.assertIn("## Local runtime env bootstrap", operator_runbooks_text)
        self.assertIn("## DEV secret-delivery normalization", operator_runbooks_text)
        self.assertIn("## Governor facade rollback and audit", operator_runbooks_text)
        self.assertIn("## Constrained mode", operator_runbooks_text)
        self.assertIn("## Degraded mode", operator_runbooks_text)
        self.assertIn("## Recovery-only", operator_runbooks_text)
        self.assertIn("## Postgres restore", operator_runbooks_text)
        self.assertIn("## Redis reconciliation", operator_runbooks_text)
        self.assertIn("## Failed promotion", operator_runbooks_text)
        self.assertIn("## Stuck media pipeline", operator_runbooks_text)
        self.assertIn("## Source auth expiry", operator_runbooks_text)
        self.assertIn("## Model lane outage", operator_runbooks_text)
        self.assertIn("## Operator auth failure", operator_runbooks_text)
        self.assertIn("GOVERNOR-FACADE-CUTOVER-PACKET.md", operator_runbooks_text)

    def test_truth_inventory_collector_tracks_governor_facade_runtime_evidence(self) -> None:
        collector_text = read_text(TRUTH_INVENTORY_COLLECTOR)
        self.assertIn('"governor_facade"', collector_text)
        self.assertIn('ss -ltnp 2>/dev/null | grep 8760 || true', collector_text)
        self.assertIn('http://127.0.0.1:8760/health', collector_text)
        self.assertIn('journalctl -u athanor-governor', collector_text)
        self.assertIn('runtime_ref_hits', collector_text)
        self.assertIn('mapped_caller_files', collector_text)
        self.assertIn('unmapped_caller_files', collector_text)
        self.assertIn('migration_registry_id', collector_text)
        self.assertIn('runtime_backup_root', collector_text)
        self.assertIn('sync_decision', collector_text)
        self.assertIn('rollback_ready', collector_text)
        self.assertIn('runtime-migration-registry.json', collector_text)

    def test_services_readme_matches_registry_first_authority_model(self) -> None:
        services_readme_text = read_text(SERVICES_README)
        self.assertIn("platform-topology.json", services_readme_text)
        self.assertIn("ansible/", services_readme_text)
        self.assertIn("STATUS.md", services_readme_text)
        self.assertIn("CONTINUOUS-COMPLETION-BACKLOG.md", services_readme_text)
        self.assertIn("deleted from implementation authority", services_readme_text)
        self.assertNotIn("The authoritative source of truth for all service definitions is `ansible/`.", services_readme_text)
        self.assertNotIn("# Services (Snapshot Only)", services_readme_text)

    def test_services_root_generated_pycache_artifacts_are_not_tracked(self) -> None:
        tracked_paths = {path.relative_to(REPO_ROOT).as_posix() for path in list_tracked_repo_files()}
        tracked_pycache = sorted(path for path in tracked_paths if path.startswith("services/__pycache__/"))
        self.assertEqual([], tracked_pycache, f"services/__pycache__ artifacts should not be tracked: {tracked_pycache}")

    def test_service_contract_bundle_script_is_documented_and_quality_gate_declares_redis(self) -> None:
        self.assertTrue(SERVICE_CONTRACT_TEST_SCRIPT.exists(), "scripts/run_service_contract_tests.py is missing")

        requirements_text = read_text(QUALITY_GATE_REQUIREMENTS)
        self.assertRegex(
            requirements_text,
            r"(?m)^redis(?:[<>=!~].*)?$",
            "services/quality-gate/requirements.txt must declare redis for operator audit events",
        )

        script_text = read_text(SERVICE_CONTRACT_TEST_SCRIPT)
        for required_fragment in [
            ".venv-services-ci",
            "services/quality-gate/tests",
            "services/gateway/tests",
            "services/governor/tests",
            "services/brain/tests/test_brain_contracts.py",
            "services/classifier/tests/test_classifier_contracts.py",
            "services/sentinel/tests/test_sentinel_contracts.py",
            '"scripts" / "requirements-test.txt"',
            "scripts/tests/test_mcp_athanor_agents_contracts.py",
            "scripts/tests/test_subscription_burn_contracts.py",
            "scripts/tests/test_semantic_router_contracts.py",
        ]:
            self.assertIn(required_fragment, script_text)

        for path in [AGENTS_DOC, SCRIPTS_README, STATUS_DOC, BACKLOG_DOC]:
            self.assertIn(
                "scripts/run_service_contract_tests.py",
                read_text(path),
                f"{path} should reference the canonical service contract bundle script",
            )

    def test_truth_inventory_collector_respects_known_health_paths_and_tcp_service_planes(self) -> None:
        topology = json.loads(read_text(PLATFORM_TOPOLOGY_REGISTRY))
        service_map = {str(service["id"]): service for service in topology.get("services", [])}

        self.assertEqual("/api/health", service_map["openfang"].get("health_path"))
        self.assertEqual("/api/public/health", service_map["langfuse"].get("health_path"))
        self.assertEqual("/healthcheck", service_map["miniflux"].get("health_path"))
        self.assertEqual("/", service_map["neo4j_http"].get("health_path"))
        self.assertEqual("redis", service_map["redis"].get("scheme"))
        self.assertEqual("bolt", service_map["neo4j"].get("scheme"))

        collector_text = read_text(TRUTH_INVENTORY_COLLECTOR)
        self.assertIn('service.get("health_path") or service.get("path") or "/health"', collector_text)
        self.assertIn('if scheme in {"bolt", "redis", "postgres", "postgresql"}', collector_text)
        self.assertIn('"probe_class": "tcp_connect"', collector_text)

    def test_topology_and_vault_probe_truth_cover_live_media_stack(self) -> None:
        topology = json.loads(read_text(PLATFORM_TOPOLOGY_REGISTRY))
        service_map = {str(service["id"]): service for service in topology.get("services", [])}

        expected_topology = {
            "home_assistant": "/",
            "sonarr": "/ping",
            "radarr": "/ping",
            "prowlarr": "/ping",
            "sabnzbd": "/api?mode=version&output=json",
            "tautulli": "/",
            "plex": "/identity",
            "stash": None,
        }
        for service_id, health_path in expected_topology.items():
            self.assertIn(service_id, service_map, f"{service_id} must exist in platform-topology.json")
            if health_path is not None:
                self.assertEqual(health_path, service_map[service_id].get("health_path"))
            self.assertEqual("vault", service_map[service_id].get("node"))
            self.assertEqual("operator", service_map[service_id].get("auth_class"))

        vault_host_vars_text = read_text(VAULT_HOST_VARS)
        for fragment in [
            '- id: sonarr',
            'url: "http://{{ vault_ip }}:8989/ping"',
            '- id: radarr',
            'url: "http://{{ vault_ip }}:7878/ping"',
            '- id: prowlarr',
            'url: "http://{{ vault_ip }}:9696/ping"',
            '- id: sabnzbd',
            'url: "http://{{ vault_ip }}:8080/api?mode=version&output=json"',
            '- id: tautulli',
            'url: "http://{{ vault_ip }}:8181"',
            '- id: plex',
            'url: "http://{{ vault_ip }}:32400/identity"',
            '- id: home-assistant',
            'url: "http://{{ vault_ip }}:8123/"',
        ]:
            self.assertIn(fragment, vault_host_vars_text)

    def test_topology_declares_athanor_postgres_service(self) -> None:
        topology = json.loads(read_text(PLATFORM_TOPOLOGY_REGISTRY))
        service_map = {str(service["id"]): service for service in topology.get("services", [])}
        self.assertIn("athanor_postgres", service_map)
        athanor_postgres = service_map["athanor_postgres"]
        self.assertEqual("vault", athanor_postgres.get("node"))
        self.assertEqual("postgresql", athanor_postgres.get("scheme"))
        self.assertEqual(5434, athanor_postgres.get("port"))
        self.assertEqual("ATHANOR_POSTGRES_URL", athanor_postgres.get("url_env"))
        self.assertEqual("internal_only", athanor_postgres.get("auth_class"))

    def test_durable_persistence_contract_uses_the_cluster_postgres_target(self) -> None:
        core_host_vars_text = read_text(CORE_HOST_VARS)
        self.assertIn("athanor_postgres_url:", core_host_vars_text)
        self.assertIn("vault_langfuse_pg_password | urlencode", core_host_vars_text)
        self.assertIn("athanor_postgres_port: 5434", core_host_vars_text)
        self.assertIn("athanor_postgres_db: athanor", core_host_vars_text)

        langfuse_defaults_text = read_text(VAULT_LANGFUSE_DEFAULTS)
        self.assertIn("langfuse_pg_host_port: 5434", langfuse_defaults_text)
        self.assertIn("athanor_postgres_db: athanor", langfuse_defaults_text)

        langfuse_tasks_text = read_text(VAULT_LANGFUSE_TASKS)
        self.assertIn("Check whether the Athanor Postgres database already exists", langfuse_tasks_text)
        self.assertIn("Ensure Athanor Postgres database exists", langfuse_tasks_text)
        self.assertIn("createdb", langfuse_tasks_text)
        self.assertIn("athanor_postgres_db", langfuse_tasks_text)

    def test_active_governor_helpers_do_not_reintroduce_local_state_ownership(self) -> None:
        for path in ACTIVE_GOVERNOR_HELPER_MODULES:
            text = read_text(path)
            allowed_tokens = ACTIVE_GOVERNOR_LOCAL_STATE_EXEMPTIONS.get(path, set())
            for token in ACTIVE_GOVERNOR_LOCAL_STATE_TOKENS:
                if token in allowed_tokens:
                    continue
                self.assertNotIn(
                    token,
                    text,
                    f"{path.relative_to(REPO_ROOT)} reintroduced retired local-state token {token!r}",
                )

    def test_mutating_agent_modules_use_operator_contract_or_are_allowlisted(self) -> None:
        violations: list[str] = []
        agents_root = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents"
        for path in agents_root.rglob("*.py"):
            if path in ALLOWED_MUTATION_MODULES_WITHOUT_OPERATOR_CONTRACT:
                continue
            text = read_text(path)
            if not MUTATION_ROUTE_DECORATOR.search(text):
                continue
            if any(token in text for token in OPERATOR_CONTRACT_TOKENS):
                continue
            violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(
            [],
            violations,
            f"Mutating agent modules are missing the shared operator contract: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
