import httpx
from langchain_core.tools import tool

SERVICES = {
    "vLLM": {"url": "http://192.168.1.244:8000/health", "node": "Node 1"},
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
}


@tool
def check_services() -> str:
    """Check the health and status of all Athanor homelab services. Returns which services are up or down."""
    results = []
    for name, info in SERVICES.items():
        try:
            resp = httpx.get(info["url"], timeout=5, follow_redirects=True)
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
                "http://192.168.1.203:9090/api/v1/query",
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
    """List the AI models currently loaded and available on the vLLM inference server."""
    try:
        resp = httpx.get("http://192.168.1.244:8000/v1/models", timeout=5)
        data = resp.json()
        models = data.get("data", [])
        if not models:
            return "No models loaded in vLLM."
        lines = ["vLLM Models:"]
        for m in models:
            lines.append(f"  - {m['id']} (owned_by: {m.get('owned_by', 'N/A')})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error querying vLLM: {e}"


@tool
def get_storage_info() -> str:
    """Get storage usage information for the VAULT NFS server."""
    try:
        query = 'node_filesystem_avail_bytes{instance=~"192.168.1.203.*",fstype!~"tmpfs|devtmpfs|overlay"}'
        resp = httpx.get(
            "http://192.168.1.203:9090/api/v1/query",
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
