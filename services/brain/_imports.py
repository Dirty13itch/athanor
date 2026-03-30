"""Local import shim for brain service modules.

This keeps the cwd-based entrypoint (`uvicorn main:app`) working while
loading the canonical services cluster config explicitly.
"""

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

EMBEDDING_URL = cluster_config.EMBEDDING_URL
NODES = cluster_config.NODES
OLLAMA_WORKSHOP_URL = cluster_config.OLLAMA_WORKSHOP_URL
PROMETHEUS_URL = cluster_config.PROMETHEUS_URL
RERANKER_URL = cluster_config.RERANKER_URL
VLLM_CODER_URL = cluster_config.VLLM_CODER_URL
VLLM_COORDINATOR_URL = cluster_config.VLLM_COORDINATOR_URL
