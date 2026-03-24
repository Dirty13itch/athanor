"""Athanor Cluster Configuration — single source of truth for all node addresses.

Import this instead of hardcoding IPs:
    from cluster_config import NODES, SERVICES, get_url

Usage:
    from cluster_config import SERVICES, get_url
    litellm_url = SERVICES["litellm"]["url"]
    # Returns "http://192.168.1.203:4000"

    litellm_url = get_url("litellm")
    # Same thing
"""
import os

# Node addresses (override via environment)
NODES = {
    "dev":      os.environ.get("ATHANOR_DEV_IP", "192.168.1.189"),
    "foundry":  os.environ.get("ATHANOR_FOUNDRY_IP", "192.168.1.244"),
    "workshop": os.environ.get("ATHANOR_WORKSHOP_IP", "192.168.1.225"),
    "vault":    os.environ.get("ATHANOR_VAULT_IP", "192.168.1.203"),
    "desk":     os.environ.get("ATHANOR_DESK_IP", "192.168.1.50"),
}

# Convenience: LiteLLM master key
LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d")

# Service endpoints
SERVICES = {
    "litellm":          {"node": "vault",    "port": 4000,  "url": f"http://{NODES['vault']}:4000"},
    "vllm_coordinator": {"node": "foundry",  "port": 8000,  "url": f"http://{NODES['foundry']}:8000"},
    "vllm_coder":       {"node": "foundry",  "port": 8006,  "url": f"http://{NODES['foundry']}:8006"},
    "vllm_vision":      {"node": "workshop", "port": 8000,  "url": f"http://{NODES['workshop']}:8000"},
    "agent_server":     {"node": "foundry",  "port": 9000,  "url": f"http://{NODES['foundry']}:9000"},
    "gateway":          {"node": "dev",      "port": 8700,  "url": f"http://{NODES['dev']}:8700"},
    "memory":           {"node": "dev",      "port": 8720,  "url": f"http://{NODES['dev']}:8720"},
    "semantic_router":  {"node": "dev",      "port": 8060,  "url": f"http://{NODES['dev']}:8060"},
    "embedding":        {"node": "dev",      "port": 8001,  "url": f"http://{NODES['dev']}:8001"},
    "reranker":         {"node": "dev",      "port": 8003,  "url": f"http://{NODES['dev']}:8003"},
    "subscription_burn":{"node": "dev",      "port": 8065,  "url": f"http://{NODES['dev']}:8065"},
    "scorer":           {"node": "workshop", "port": 8050,  "url": f"http://{NODES['workshop']}:8050"},
    "comfyui":          {"node": "workshop", "port": 8188,  "url": f"http://{NODES['workshop']}:8188"},
    "speaches":         {"node": "foundry",  "port": 8200,  "url": f"http://{NODES['foundry']}:8200"},
    "ollama_workshop":  {"node": "workshop", "port": 11434, "url": f"http://{NODES['workshop']}:11434"},
    "qdrant":           {"node": "vault",    "port": 6333,  "url": f"http://{NODES['vault']}:6333"},
    "neo4j":            {"node": "vault",    "port": 7687,  "url": f"bolt://{NODES['vault']}:7687"},
    "neo4j_http":       {"node": "vault",    "port": 7474,  "url": f"http://{NODES['vault']}:7474"},
    "redis":            {"node": "vault",    "port": 6379,  "url": f"redis://{NODES['vault']}:6379/0"},
    "prometheus":       {"node": "vault",    "port": 9090,  "url": f"http://{NODES['vault']}:9090"},
    "grafana":          {"node": "vault",    "port": 3000,  "url": f"http://{NODES['vault']}:3000"},
    "ntfy":             {"node": "vault",    "port": 8880,  "url": f"http://{NODES['vault']}:8880"},
    "ntfy_topic":       {"node": "vault",    "port": 8880,  "url": f"http://{NODES['vault']}:8880/athanor"},
    "n8n":              {"node": "vault",    "port": 5678,  "url": f"http://{NODES['vault']}:5678"},
    "stash":            {"node": "vault",    "port": 9999,  "url": f"http://{NODES['vault']}:9999"},
    "uptime_kuma":      {"node": "vault",    "port": 3009,  "url": f"http://{NODES['vault']}:3009"},
    "langfuse":         {"node": "vault",    "port": 3030,  "url": f"http://{NODES['vault']}:3030"},
    "miniflux":         {"node": "vault",    "port": 8070,  "url": f"http://{NODES['vault']}:8070"},
    "dashboard":        {"node": "dev",      "port": 3001,  "url": f"http://{NODES['dev']}:3001"},
    "openfang":         {"node": "dev",      "port": 4200,  "url": f"http://{NODES['dev']}:4200"},
}


def get_url(service_name: str) -> str:
    """Get the URL for a service by name."""
    svc = SERVICES.get(service_name)
    if isinstance(svc, dict):
        return svc["url"]
    raise KeyError(f"Unknown service: {service_name}")
