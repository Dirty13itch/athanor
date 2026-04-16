from __future__ import annotations

import importlib.util
from pathlib import Path


CLUSTER_CONFIG_PATH = Path(__file__).resolve().with_name("cluster_config.py")

spec = importlib.util.spec_from_file_location("athanor_scripts_cluster_config", CLUSTER_CONFIG_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cluster config from {CLUSTER_CONFIG_PATH}")
cluster_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cluster_config)

get_url = cluster_config.get_url
LITELLM_KEY = cluster_config.LITELLM_KEY
