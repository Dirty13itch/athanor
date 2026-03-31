"""Shared import shim for governor helper scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parent
CLUSTER_CONFIG_PATH = SERVICE_DIR.parent / "cluster_config.py"

spec = importlib.util.spec_from_file_location("athanor_services_cluster_config", CLUSTER_CONFIG_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cluster config from {CLUSTER_CONFIG_PATH}")
cluster_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster_config)

AGENT_SERVER_URL = cluster_config.AGENT_SERVER_URL
DASHBOARD_URL = cluster_config.DASHBOARD_URL
NTFY_URL = cluster_config.NTFY_URL


REPO_ROOT = SERVICE_DIR.parent.parent
