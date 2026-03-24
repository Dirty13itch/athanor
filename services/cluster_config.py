"""Shared cluster configuration for services — single source of truth for node addresses.

Import in any service:
    from cluster_config import NODES, SERVICES, get_url

Or use individual constants:
    from cluster_config import VAULT_HOST, DEV_HOST, FOUNDRY_HOST, WORKSHOP_HOST

This mirrors scripts/cluster_config.py but lives in services/ so that
services can import it without sys.path hacks.
"""
import os

# ── Node addresses (override via env vars) ─────────────────────────────
DEV_HOST = os.environ.get("ATHANOR_DEV_IP", "192.168.1.189")
VAULT_HOST = os.environ.get("ATHANOR_VAULT_IP", "192.168.1.203")
FOUNDRY_HOST = os.environ.get("ATHANOR_FOUNDRY_IP", "192.168.1.244")
WORKSHOP_HOST = os.environ.get("ATHANOR_WORKSHOP_IP", "192.168.1.225")
DESK_HOST = os.environ.get("ATHANOR_DESK_IP", "192.168.1.50")

NODES = {
    "dev": DEV_HOST,
    "foundry": FOUNDRY_HOST,
    "workshop": WORKSHOP_HOST,
    "vault": VAULT_HOST,
    "desk": DESK_HOST,
}

# ── Common service URLs ────────────────────────────────────────────────
QDRANT_URL = os.environ.get("ATHANOR_QDRANT_URL", f"http://{VAULT_HOST}:6333")
LITELLM_URL = os.environ.get("ATHANOR_LITELLM_URL", f"http://{VAULT_HOST}:4000")
NEO4J_URL = os.environ.get("ATHANOR_NEO4J_URL", f"bolt://{VAULT_HOST}:7687")
NEO4J_HTTP_URL = os.environ.get("ATHANOR_NEO4J_HTTP_URL", f"http://{VAULT_HOST}:7474")
PROMETHEUS_URL = os.environ.get("ATHANOR_PROMETHEUS_URL", f"http://{VAULT_HOST}:9090")
GRAFANA_URL = os.environ.get("ATHANOR_GRAFANA_URL", f"http://{VAULT_HOST}:3000")
EMBEDDING_URL = os.environ.get("ATHANOR_EMBEDDING_URL", f"http://{DEV_HOST}:8001")
RERANKER_URL = os.environ.get("ATHANOR_RERANKER_URL", f"http://{DEV_HOST}:8003")
AGENT_SERVER_URL = os.environ.get("ATHANOR_AGENT_SERVER_URL", f"http://{FOUNDRY_HOST}:9000")
GOVERNOR_URL = os.environ.get("ATHANOR_GOVERNOR_URL", f"http://{DEV_HOST}:8760")
NTFY_URL = os.environ.get("ATHANOR_NTFY_URL", f"http://{VAULT_HOST}:8880")
LANGFUSE_URL = os.environ.get("ATHANOR_LANGFUSE_URL", f"http://{VAULT_HOST}:3030")
REDIS_URL = os.environ.get("ATHANOR_REDIS_URL", f"redis://{VAULT_HOST}:6379/0")
DASHBOARD_URL = os.environ.get("ATHANOR_DASHBOARD_URL", f"http://{DEV_HOST}:3001")
COMFYUI_URL = os.environ.get("ATHANOR_COMFYUI_URL", f"http://{WORKSHOP_HOST}:8188")
OLLAMA_WORKSHOP_URL = os.environ.get("ATHANOR_OLLAMA_WORKSHOP_URL", f"http://{WORKSHOP_HOST}:11434")
VLLM_COORDINATOR_URL = os.environ.get("ATHANOR_VLLM_COORDINATOR_URL", f"http://{FOUNDRY_HOST}:8000")
VLLM_CODER_URL = os.environ.get("ATHANOR_VLLM_CODER_URL", f"http://{FOUNDRY_HOST}:8006")
STASH_URL = os.environ.get("ATHANOR_STASH_URL", f"http://{VAULT_HOST}:9999")
SPEACHES_URL = os.environ.get("ATHANOR_SPEACHES_URL", f"http://{FOUNDRY_HOST}:8200")

# Convenience lookup
SERVICES = {
    "qdrant": QDRANT_URL,
    "litellm": LITELLM_URL,
    "neo4j": NEO4J_URL,
    "neo4j_http": NEO4J_HTTP_URL,
    "prometheus": PROMETHEUS_URL,
    "grafana": GRAFANA_URL,
    "embedding": EMBEDDING_URL,
    "reranker": RERANKER_URL,
    "agent_server": AGENT_SERVER_URL,
    "governor": GOVERNOR_URL,
    "ntfy": NTFY_URL,
    "langfuse": LANGFUSE_URL,
    "redis": REDIS_URL,
    "dashboard": DASHBOARD_URL,
    "comfyui": COMFYUI_URL,
    "ollama_workshop": OLLAMA_WORKSHOP_URL,
    "vllm_coordinator": VLLM_COORDINATOR_URL,
    "vllm_coder": VLLM_CODER_URL,
    "stash": STASH_URL,
    "speaches": SPEACHES_URL,
}


def get_url(service_name: str) -> str:
    """Get the URL for a service by name."""
    url = SERVICES.get(service_name)
    if url is not None:
        return url
    raise KeyError(f"Unknown service: {service_name}")
