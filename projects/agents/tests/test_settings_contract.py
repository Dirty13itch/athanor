import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.config import Settings
from athanor_agents.services import ServiceRegistry


class SettingsContractTest(unittest.TestCase):
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

        service_ids = {service.id for service in registry.service_checks}
        self.assertIn("litellm-proxy", service_ids)
        self.assertIn("dev-reranker", service_ids)
        self.assertIn("vault-open-webui", service_ids)


if __name__ == "__main__":
    unittest.main()
