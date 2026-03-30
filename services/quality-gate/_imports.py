"""Local import shim for quality-gate service modules."""

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
QDRANT_URL = cluster_config.QDRANT_URL
