import httpx
from langchain_core.tools import tool

from athanor_agents.config import settings

SERVICES = {
    "LiteLLM": {"url": "http://192.168.1.203:4000/v1/models", "node": "VAULT",
                 "headers": {"Authorization": f"Bearer {settings.llm_api_key}"}},
    "vLLM (Node 1)": {"url": "http://192.168.1.244:8000/health", "node": "Node 1"},
    "vLLM Embedding": {"url": "http://192.168.1.244:8001/health", "node": "Node 1"},
    "vLLM (Node 2)": {"url": "http://192.168.1.225:8000/health", "node": "Node 2"},
    "Qdrant": {"url": "http://192.168.1.244:6333/collections", "node": "Node 1"},
    "ComfyUI": {"url": "http://192.168.1.225:8188/system_stats", "node": "Node 2"},
    "Open WebUI": {"url": "http://192.168.1.225:3000", "node": "Node 2"},
    "Dashboard": {"url": "http://192.168.1.225:3001", "node": "Node 2"},
    "Prometheus": {"url": "http://192.168.1.203:9090/-/healthy", "node": "VAULT"},
    "Grafana": {"url": "http://192.168.1.203:3000/api/health", "node": "VAULT"},
    "Sonarr": {"url": "http://192.168.1.203:8989/ping", "node": "VAULT"},
    "Radarr": {"url": "http://192.168.1.203:7878/ping", "node": "VAULT"},
    "SABnzbd": {"url": "http://192.168.1.203:8080", "node": "VAULT"},
    "Tautulli": {"url": "http://192.168.1.203:8181", "node": "VAULT"},
    "Stash": {"url": "http://192.168.1.203:9999", "node": "VAULT"},
    "Plex": {"url": "http://192.168.1.203:32400/identity", "node": "VAULT"},
    "Home Assistant": {"url": "http://192.168.1.203:8123/api/", "node": "VAULT",
                        "headers": {"Authorization": f"Bearer {settings.ha_token}"}},
    "Neo4j": {"url": "http://192.168.1.203:7474", "node": "VAULT"},
    "GPU Orchestrator": {"url": "http://192.168.1.244:9200/health", "node": "Node 1"},
}


@tool
def check_services() -> str:
    """Check the health and status of all Athanor homelab services. Returns which services are up or down."""
    results = []
    for name, info in SERVICES.items():
        try:
            headers = info.get("headers", {})
            resp = httpx.get(info["url"], timeout=5, follow_redirects=True, headers=headers)
            status = "UP" if resp.status_code < 400 else f"ERROR ({resp.status_code})"
        except httpx.ConnectError:
            status = "DOWN"
        except httpx.TimeoutException:
            status = "TIMEOUT"
        except Exception as e:
            status = f"ERROR ({type(e).__name__})"
        results.append(f"  {name} ({info['node']}): {status}")
    return "Service Health:\n" + "\n".join(results)


@tool
def get_gpu_metrics() -> str:
    """Get current GPU utilization, temperature, memory usage, and power draw for all GPUs across all nodes."""
    metrics = [
        ("Utilization %", "DCGM_FI_DEV_GPU_UTIL"),
        ("Temperature C", "DCGM_FI_DEV_GPU_TEMP"),
        ("Memory Used MB", "DCGM_FI_DEV_FB_USED"),
        ("Memory Free MB", "DCGM_FI_DEV_FB_FREE"),
        ("Power W", "DCGM_FI_DEV_POWER_USAGE"),
    ]
    lines = ["GPU Metrics:"]
    for label, query in metrics:
        try:
            resp = httpx.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=5,
            )
            data = resp.json()
            for r in data.get("data", {}).get("result", []):
                gpu = r["metric"].get("gpu", "?")
                host = r["metric"].get("instance", "?").split(":")[0]
                val = r["value"][1]
                lines.append(f"  {host} GPU {gpu}: {label} = {val}")
        except Exception as e:
            lines.append(f"  Error fetching {label}: {e}")
    return "\n".join(lines)


@tool
def get_vllm_models() -> str:
    """List all AI models available through the LiteLLM routing proxy and directly on vLLM instances."""
    lines = ["Models Available:"]

    # Query LiteLLM proxy (authoritative list of routable models)
    try:
        resp = httpx.get(
            f"{settings.llm_base_url}/models",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=5,
        )
        data = resp.json()
        models = data.get("data", [])
        lines.append("  LiteLLM Proxy (VAULT:4000):")
        for m in models:
            lines.append(f"    - {m['id']} (owned_by: {m.get('owned_by', 'N/A')})")
    except Exception as e:
        lines.append(f"  LiteLLM: Error - {e}")

    # Query direct vLLM instances (for operational visibility)
    for label, url in [
        ("Node 1 (TP=4)", settings.vllm_node1_url),
        ("Node 2 (5090)", settings.vllm_node2_url),
        ("Embedding (GPU 4)", settings.vllm_embedding_url),
    ]:
        try:
            resp = httpx.get(f"{url}/models", timeout=5)
            data = resp.json()
            for m in data.get("data", []):
                lines.append(f"  {label}: {m['id']}")
        except Exception as e:
            lines.append(f"  {label}: Error - {e}")

    return "\n".join(lines)


@tool
def get_storage_info() -> str:
    """Get storage usage information for the VAULT NFS server."""
    try:
        query = 'node_filesystem_avail_bytes{instance=~"192.168.1.203.*",fstype!~"tmpfs|devtmpfs|overlay"}'
        resp = httpx.get(
            f"{settings.prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        data = resp.json()
        lines = ["Storage (VAULT):"]
        for r in data.get("data", {}).get("result", []):
            mount = r["metric"].get("mountpoint", "?")
            avail_gb = float(r["value"][1]) / (1024**3)
            lines.append(f"  {mount}: {avail_gb:.1f} GB available")
        return "\n".join(lines) if len(lines) > 1 else "No storage metrics available."
    except Exception as e:
        return f"Error querying storage: {e}"
