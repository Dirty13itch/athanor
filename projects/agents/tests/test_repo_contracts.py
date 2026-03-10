import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DOC = REPO_ROOT / "AGENTS.md"
AGENTS_INIT = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "agents" / "__init__.py"
SERVER_PY = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "server.py"
DASHBOARD_CONFIG = REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "config.ts"
DASHBOARD_SERVER_CONFIG = REPO_ROOT / "projects" / "dashboard" / "src" / "lib" / "server-config.ts"
DASHBOARD_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "dashboard" / "templates" / "docker-compose.yml.j2"
LITELLM_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "vault-litellm" / "templates" / "litellm_config.yaml.j2"
NODE1_PLAYBOOK = REPO_ROOT / "ansible" / "playbooks" / "node1.yml"
NEO4J_TASKS = REPO_ROOT / "ansible" / "roles" / "vault-neo4j" / "tasks" / "main.yml"
PROJECTS_MODULE = REPO_ROOT / "projects" / "agents" / "src" / "athanor_agents" / "projects.py"
DASHBOARD_SW = REPO_ROOT / "projects" / "dashboard" / "public" / "sw.js"

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
    "ATHANOR_VLLM_UTILITY_URL",
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
    "utility": "http://{{ vllm_node1_host }}:{{ vllm_node1_utility_port }}/v1",
    "creative": "http://{{ vllm_node1_host }}:{{ vllm_node1_utility_port }}/v1",
    "fast": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
    "worker": "http://{{ vllm_node2_host }}:{{ vllm_node2_port }}/v1",
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


def normalize_agent_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def parse_server_agent_metadata() -> dict:
    module = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "AGENT_METADATA":
                    return ast.literal_eval(node.value)
    raise AssertionError("AGENT_METADATA not found in server.py")


def parse_agent_ids_from_init() -> set[str]:
    text = AGENTS_INIT.read_text(encoding="utf-8")
    return set(re.findall(r'_AGENTS\["([^"]+)"\]\s*=', text))


def parse_agent_ids_from_docs() -> set[str]:
    rows = re.findall(r"\| \*\*([^*]+)\*\* \| [^|]+ \| [^|]+ \| Live \|", AGENTS_DOC.read_text(encoding="utf-8"))
    return {normalize_agent_name(name) for name in rows}


def parse_compose_envs() -> set[str]:
    envs: set[str] = set()
    for line in DASHBOARD_TEMPLATE.read_text(encoding="utf-8").splitlines():
        match = re.search(r"- ([A-Z0-9_]+)=", line.strip())
        if match:
            envs.add(match.group(1))
    return envs


def parse_litellm_alias_targets() -> dict[str, str]:
    text = LITELLM_TEMPLATE.read_text(encoding="utf-8")
    pattern = re.compile(
        r'- model_name: "([^"]+)"\s+litellm_params:\s+model: "[^"]+"\s+api_base: "([^"]+)"',
        re.MULTILINE,
    )
    return {name: api_base for name, api_base in pattern.findall(text)}


def parse_dashboard_project_registry_ids() -> set[str]:
    text = DASHBOARD_CONFIG.read_text(encoding="utf-8")
    block = re.search(r"projectRegistry:\s*\[(.*?)\],\s*grafanaDashboards:", text, re.DOTALL)
    if not block:
        raise AssertionError("dashboard projectRegistry block not found")
    return set(re.findall(r'id:\s*"([^"]+)"', block.group(1)))


def parse_agent_project_registry_ids() -> set[str]:
    text = PROJECTS_MODULE.read_text(encoding="utf-8")
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

    def test_node1_playbook_no_longer_deploys_embedding(self) -> None:
        text = NODE1_PLAYBOOK.read_text(encoding="utf-8")
        self.assertNotIn("vllm-embedding", text, "Node 1 playbook still deploys the embedding role")

    def test_neo4j_seed_topology_matches_current_runtime_map(self) -> None:
        text = NEO4J_TASKS.read_text(encoding="utf-8")
        for required in [
            "foundry-coordinator",
            "foundry-utility",
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
            text = path.read_text(encoding="utf-8", errors="ignore")
            if RAW_IP_PATTERN.search(text):
                violations.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Raw dashboard IP literals leaked outside config/fixtures: {violations}")

    def test_dashboard_server_config_credentials_are_exported(self) -> None:
        server_envs = set(re.findall(r"process\.env\.([A-Z0-9_]+)", DASHBOARD_SERVER_CONFIG.read_text(encoding="utf-8")))
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
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                if "/api/agents/proxy" in text:
                    violations.append(str(file_path.relative_to(REPO_ROOT)))

        self.assertEqual([], violations, f"Legacy agent proxy references remain in dashboard code: {violations}")


if __name__ == "__main__":
    unittest.main()
