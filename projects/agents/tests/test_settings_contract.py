import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
LOCAL_COMPOSE = PROJECT_ROOT / "docker-compose.yml"
AGENTS_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "agents" / "templates" / "docker-compose.yml.j2"
AGENTS_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "agents" / "defaults" / "main.yml"
SERVER_MODULE = SRC_ROOT / "athanor_agents" / "server.py"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.config import Settings
from athanor_agents.services import ServiceRegistry


class SettingsContractTest(unittest.TestCase):
    def test_deploy_contract_exports_new_persistence_and_media_envs(self) -> None:
        local_compose = LOCAL_COMPOSE.read_text(encoding="utf-8", errors="ignore")
        template = AGENTS_TEMPLATE.read_text(encoding="utf-8", errors="ignore")
        defaults = AGENTS_DEFAULTS.read_text(encoding="utf-8", errors="ignore")

        for token in (
            "ATHANOR_POSTGRES_URL",
            "ATHANOR_AGENT_DESCRIPTOR_PATH",
            "ATHANOR_DOMAIN_PACKET_PATH",
            "ATHANOR_PROWLARR_API_KEY",
            "ATHANOR_SABNZBD_API_KEY",
        ):
            self.assertIn(token, local_compose)
            self.assertIn(token, template)

        for token in (
            "agent_postgres_url",
            "agent_descriptor_path",
            "agent_domain_packet_path",
            "agent_prowlarr_api_key",
            "agent_sabnzbd_api_key",
        ):
            self.assertIn(token, defaults)

    def test_server_uses_registry_backed_agent_metadata(self) -> None:
        server_text = SERVER_MODULE.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("def get_agent_metadata()", server_text)
        self.assertIn("return build_agent_metadata()", server_text)
        self.assertIn("build_system_map_snapshot(get_agent_metadata())", server_text)
        self.assertNotIn('"general-assistant": {', server_text)

    def test_pyproject_declares_postgres_checkpointer_dependency(self) -> None:
        pyproject_text = PYPROJECT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn('"langgraph-checkpoint-postgres>=3.0.5"', pyproject_text)
        self.assertIn('"psycopg[binary]>=3.2"', pyproject_text)

    def test_new_registry_and_persistence_envs_are_supported(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_POSTGRES_URL": "postgresql://athanor:test@db.internal:5432/athanor",
                "ATHANOR_AGENT_DESCRIPTOR_PATH": "C:/Athanor/config/automation-backbone/agent-descriptor-registry.json",
                "ATHANOR_DOMAIN_PACKET_PATH": "C:/Athanor/config/automation-backbone/domain-packets-registry.json",
                "ATHANOR_PROWLARR_API_KEY": "prowlarr-key",
                "ATHANOR_SABNZBD_API_KEY": "sab-key",
            },
            clear=True,
        ):
            cfg = Settings()

        self.assertEqual(cfg.postgres_url, "postgresql://athanor:test@db.internal:5432/athanor")
        self.assertEqual(
            cfg.agent_descriptor_path,
            "C:/Athanor/config/automation-backbone/agent-descriptor-registry.json",
        )
        self.assertEqual(
            cfg.domain_packet_path,
            "C:/Athanor/config/automation-backbone/domain-packets-registry.json",
        )
        self.assertEqual(cfg.prowlarr_api_key, "prowlarr-key")
        self.assertEqual(cfg.sabnzbd_api_key, "sab-key")

    def test_canonical_env_contract_normalizes_openai_urls(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_LITELLM_URL": "http://router.internal:4000",
                "ATHANOR_LITELLM_API_KEY": "test-key",
                "ATHANOR_VLLM_COORDINATOR_URL": "http://foundry.internal:8000",
                "ATHANOR_VLLM_WORKER_URL": "http://workshop.internal:8000",
                "ATHANOR_VLLM_EMBEDDING_URL": "http://dev.internal:8001",
                "ATHANOR_VLLM_RERANKER_URL": "http://dev.internal:8003",
                "ATHANOR_GRAPHRAG_URL": "http://foundry.internal:9300",
            },
            clear=True,
        ):
            cfg = Settings()

        self.assertEqual(cfg.litellm_url, "http://router.internal:4000")
        self.assertEqual(cfg.llm_base_url, "http://router.internal:4000/v1")
        self.assertEqual(cfg.vllm_node1_url, "http://foundry.internal:8000/v1")
        self.assertEqual(cfg.vllm_node2_url, "http://workshop.internal:8000/v1")
        self.assertEqual(cfg.vllm_embedding_url, "http://dev.internal:8001/v1")
        self.assertEqual(cfg.vllm_reranker_url, "http://dev.internal:8003/v1")
        self.assertEqual(cfg.graphrag_url, "http://foundry.internal:9300")
        self.assertEqual(cfg.llm_api_key, "test-key")

    def test_legacy_env_names_still_work_for_one_deploy_cycle(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_LLM_BASE_URL": "http://legacy-router.internal:4000/v1",
                "ATHANOR_LLM_API_KEY": "legacy-key",
                "ATHANOR_VLLM_NODE1_URL": "http://legacy-foundry.internal:8000/v1",
                "ATHANOR_VLLM_NODE2_URL": "http://legacy-workshop.internal:8000/v1",
            },
            clear=True,
        ):
            cfg = Settings()

        self.assertEqual(cfg.litellm_url, "http://legacy-router.internal:4000/v1")
        self.assertEqual(cfg.llm_base_url, "http://legacy-router.internal:4000/v1")
        self.assertEqual(cfg.vllm_node1_url, "http://legacy-foundry.internal:8000/v1")
        self.assertEqual(cfg.vllm_node2_url, "http://legacy-workshop.internal:8000/v1")
        self.assertEqual(cfg.llm_api_key, "legacy-key")

    def test_service_registry_builds_canonical_endpoints(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_LITELLM_URL": "http://vault.internal:4000",
                "ATHANOR_LITELLM_API_KEY": "router-key",
                "ATHANOR_HOME_ASSISTANT_URL": "http://vault.internal:8123",
                "ATHANOR_HA_TOKEN": "ha-token",
                "ATHANOR_NEO4J_URL": "http://vault.internal:7474",
                "ATHANOR_NEO4J_USER": "neo4j",
                "ATHANOR_NEO4J_PASSWORD": "graph-secret",
            },
            clear=True,
        ):
            cfg = Settings()
            registry = ServiceRegistry(cfg)

        self.assertEqual(registry.litellm_openai_url, "http://vault.internal:4000/v1")
        self.assertEqual(registry.home_assistant_api_url, "http://vault.internal:8123/api")
        self.assertEqual(registry.prowlarr_api_url, "http://192.168.1.203:9696/api/v1")
        self.assertEqual(registry.sabnzbd_api_url, "http://192.168.1.203:8080/api")
        self.assertEqual(
            registry.litellm_headers,
            {"Authorization": "Bearer router-key"},
        )
        self.assertEqual(
            registry.home_assistant_headers,
            {
                "Authorization": "Bearer ha-token",
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(registry.neo4j_auth, ("neo4j", "graph-secret"))
        self.assertEqual("VAULT", registry.qdrant.node)
        self.assertEqual("Foundry", registry.graphrag.node)
        self.assertEqual("DEV", registry.dashboard.node)

        service_ids = {service.id for service in registry.service_checks}
        self.assertIn("litellm-proxy", service_ids)
        self.assertIn("dev-reranker", service_ids)
        self.assertIn("graphrag", service_ids)
        self.assertIn("vault-open-webui", service_ids)
        self.assertIn("prowlarr", service_ids)
        self.assertIn("sabnzbd", service_ids)

    def test_default_fast_and_router_models_follow_live_coder_lane(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_LITELLM_URL": "http://router.internal:4000",
                "ATHANOR_LITELLM_API_KEY": "router-key",
            },
            clear=True,
        ):
            cfg = Settings()

        self.assertEqual(cfg.llm_model_fast, "coder")
        self.assertEqual(cfg.router_reactive_model, "coder")
        self.assertEqual(cfg.router_tactical_model, "coder")


if __name__ == "__main__":
    unittest.main()
