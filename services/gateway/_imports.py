"""Local import shim for gateway service modules."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_SERVICE_DIR = Path(__file__).resolve().parent
_CLUSTER_CONFIG_PATH = _SERVICE_DIR.parent / "cluster_config.py"

spec = importlib.util.spec_from_file_location("athanor_services_cluster_config", _CLUSTER_CONFIG_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cluster config from {_CLUSTER_CONFIG_PATH}")
cluster_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster_config)

AGENT_SERVER_URL = cluster_config.AGENT_SERVER_URL
COMFYUI_URL = cluster_config.COMFYUI_URL
DASHBOARD_URL = cluster_config.DASHBOARD_URL
LANGFUSE_URL = cluster_config.LANGFUSE_URL
LITELLM_URL = cluster_config.LITELLM_URL
QDRANT_URL = cluster_config.QDRANT_URL
SERVICE_DEFINITIONS = cluster_config.SERVICE_DEFINITIONS
SERVICES = cluster_config.SERVICES
VLLM_CODER_URL = cluster_config.VLLM_CODER_URL
VLLM_COORDINATOR_URL = cluster_config.VLLM_COORDINATOR_URL
WORKSHOP_HOST = cluster_config.WORKSHOP_HOST
get_health_url = cluster_config.get_health_url
