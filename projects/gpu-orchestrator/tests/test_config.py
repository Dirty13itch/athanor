import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gpu_orchestrator.config import Settings


class SettingsContractTest(unittest.TestCase):
    def test_canonical_athanor_env_aliases_are_supported(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ATHANOR_REDIS_URL": "redis://vault:6379/1",
                "ATHANOR_NODE1_HOST": "10.0.0.11",
                "ATHANOR_NODE2_HOST": "10.0.0.12",
                "ATHANOR_VLLM_COORDINATOR_URL": "http://foundry:8000",
                "ATHANOR_VLLM_CODER_URL": "http://foundry:8100",
                "ATHANOR_VLLM_EMBEDDING_URL": "http://devbox:8001",
                "ATHANOR_VLLM_RERANKER_URL": "http://devbox:8003",
                "ATHANOR_VLLM_WORKER_URL": "http://workshop:8010",
                "ATHANOR_VLLM_VISION_URL": "http://workshop:8012",
                "ATHANOR_PROMETHEUS_URL": "http://vault:9090",
                "ATHANOR_SCHEDULER_MUTATION_ENABLED": "true",
                "ATHANOR_EMBEDDING_AUTO_SLEEP_ENABLED": "true",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertEqual(settings.redis_url, "redis://vault:6379/1")
        self.assertEqual(settings.node1_ip, "10.0.0.11")
        self.assertEqual(settings.node2_ip, "10.0.0.12")
        self.assertEqual(settings.vllm_node1_url, "http://foundry:8000")
        self.assertEqual(settings.vllm_coder_url, "http://foundry:8100")
        self.assertEqual(settings.vllm_node1_embed_url, "http://devbox:8001")
        self.assertEqual(settings.vllm_reranker_url, "http://devbox:8003")
        self.assertEqual(settings.vllm_node2_url, "http://workshop:8010")
        self.assertEqual(settings.vllm_vision_url, "http://workshop:8012")
        self.assertEqual(settings.prometheus_url, "http://vault:9090")
        self.assertTrue(settings.scheduler_mutation_enabled)
        self.assertTrue(settings.embedding_auto_sleep_enabled)

    def test_legacy_gpu_orchestrator_env_names_still_work(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GPU_ORCH_REDIS_URL": "redis://legacy:6379/2",
                "GPU_ORCH_NODE1_IP": "192.168.10.1",
                "GPU_ORCH_NODE2_IP": "192.168.10.2",
                "GPU_ORCH_VLLM_NODE1_URL": "http://legacy-foundry:8000",
                "GPU_ORCH_VLLM_CODER_URL": "http://legacy-foundry:8100",
                "GPU_ORCH_VLLM_NODE1_EMBED_URL": "http://legacy-dev:8001",
                "GPU_ORCH_VLLM_RERANKER_URL": "http://legacy-dev:8003",
                "GPU_ORCH_VLLM_NODE2_URL": "http://legacy-workshop:8010",
                "GPU_ORCH_VLLM_VISION_URL": "http://legacy-workshop:8012",
                "GPU_ORCH_DCGM_NODE1_URL": "http://legacy-foundry:9400",
                "GPU_ORCH_DCGM_NODE2_URL": "http://legacy-workshop:9400",
                "GPU_ORCH_DCGM_NODE3_URL": "http://legacy-dev:9400",
                "GPU_ORCH_PROMETHEUS_URL": "http://legacy-vault:9090",
                "GPU_ORCH_SCHEDULER_MUTATION_ENABLED": "1",
                "GPU_ORCH_EMBEDDING_AUTO_SLEEP_ENABLED": "0",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertEqual(settings.redis_url, "redis://legacy:6379/2")
        self.assertEqual(settings.node1_ip, "192.168.10.1")
        self.assertEqual(settings.node2_ip, "192.168.10.2")
        self.assertEqual(settings.vllm_node1_url, "http://legacy-foundry:8000")
        self.assertEqual(settings.vllm_coder_url, "http://legacy-foundry:8100")
        self.assertEqual(settings.vllm_node1_embed_url, "http://legacy-dev:8001")
        self.assertEqual(settings.vllm_reranker_url, "http://legacy-dev:8003")
        self.assertEqual(settings.vllm_node2_url, "http://legacy-workshop:8010")
        self.assertEqual(settings.vllm_vision_url, "http://legacy-workshop:8012")
        self.assertEqual(settings.dcgm_node1_url, "http://legacy-foundry:9400")
        self.assertEqual(settings.dcgm_node2_url, "http://legacy-workshop:9400")
        self.assertEqual(settings.dcgm_node3_url, "http://legacy-dev:9400")
        self.assertEqual(settings.prometheus_url, "http://legacy-vault:9090")
        self.assertTrue(settings.scheduler_mutation_enabled)
        self.assertFalse(settings.embedding_auto_sleep_enabled)

    def test_defaults_follow_live_six_zone_runtime(self) -> None:
        settings = Settings()

        self.assertEqual(settings.vllm_coder_url, "http://192.168.1.244:8100")
        self.assertEqual(settings.vllm_node1_embed_url, "http://192.168.1.189:8001")
        self.assertEqual(settings.vllm_reranker_url, "http://192.168.1.189:8003")
        self.assertEqual(settings.vllm_vision_url, "http://192.168.1.225:8012")
        self.assertEqual(settings.dcgm_node3_url, "http://192.168.1.189:9400")
        self.assertFalse(settings.scheduler_mutation_enabled)
        self.assertFalse(settings.embedding_auto_sleep_enabled)


if __name__ == "__main__":
    unittest.main()
