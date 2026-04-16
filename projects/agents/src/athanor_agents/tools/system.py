import httpx
from langchain_core.tools import tool

from athanor_agents.services import registry


@tool
def check_services() -> str:
    """Check the health and status of Athanor services. Returns which services are up or down."""
    results = []
    for service in registry.service_checks:
        try:
            target = service.health_url or service.url()
            resp = httpx.get(
                target,
                timeout=5,
                follow_redirects=True,
                headers=dict(service.headers),
            )
            status = "UP" if resp.status_code < 400 else f"ERROR ({resp.status_code})"
        except httpx.ConnectError:
            status = "DOWN"
        except httpx.TimeoutException:
            status = "TIMEOUT"
        except Exception as exc:
            status = f"ERROR ({type(exc).__name__})"
        results.append(f"  {service.name} ({service.node}): {status}")
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
                registry.prometheus.url("/api/v1/query"),
                params={"query": query},
                timeout=5,
            )
            data = resp.json()
            for result in data.get("data", {}).get("result", []):
                gpu = result["metric"].get("gpu", "?")
                host = result["metric"].get("instance", "?").split(":")[0]
                value = result["value"][1]
                lines.append(f"  {host} GPU {gpu}: {label} = {value}")
        except Exception as exc:
            lines.append(f"  Error fetching {label}: {exc}")
    return "\n".join(lines)


@tool
def get_vllm_models() -> str:
    """List all AI models available through LiteLLM and direct runtime instances."""
    lines = ["Models Available:"]

    for label, service in registry.model_targets:
        try:
            target = service.models_url or service.url("/v1/models")
            resp = httpx.get(
                target,
                headers=dict(service.headers),
                timeout=5,
            )
            data = resp.json()
            models = data.get("data", [])
            if not models:
                lines.append(f"  {label}: no models reported")
                continue
            lines.append(f"  {label}:")
            for model in models:
                owned_by = model.get("owned_by")
                suffix = f" (owned_by: {owned_by})" if owned_by else ""
                lines.append(f"    - {model['id']}{suffix}")
        except Exception as exc:
            lines.append(f"  {label}: Error - {exc}")

    return "\n".join(lines)


@tool
def get_storage_info() -> str:
    """Get storage usage information for the VAULT storage plane."""
    try:
        query = (
            "node_filesystem_avail_bytes{"
            f'instance=~"{registry.vault_instance_regex}.*",'
            'fstype!~"tmpfs|devtmpfs|overlay"'
            "}"
        )
        resp = httpx.get(
            registry.prometheus.url("/api/v1/query"),
            params={"query": query},
            timeout=5,
        )
        data = resp.json()
        lines = ["Storage (VAULT):"]
        for result in data.get("data", {}).get("result", []):
            mount = result["metric"].get("mountpoint", "?")
            avail_gb = float(result["value"][1]) / (1024 ** 3)
            lines.append(f"  {mount}: {avail_gb:.1f} GB available")
        return "\n".join(lines) if len(lines) > 1 else "No storage metrics available."
    except Exception as exc:
        return f"Error querying storage: {exc}"
