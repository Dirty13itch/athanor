"""GPU state monitoring via DCGM-exporter and vLLM sleep/wake management."""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .config import settings

logger = logging.getLogger(__name__)


# --- GPU Metrics ---


@dataclass
class GpuMetrics:
    """Snapshot of a single GPU's metrics from DCGM-exporter."""

    gpu_index: int
    node: str
    utilization_pct: float = 0.0
    vram_used_mb: float = 0.0
    vram_total_mb: float = 0.0
    temperature_c: float = 0.0
    power_watts: float = 0.0
    gpu_name: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def vram_free_mb(self) -> float:
        return self.vram_total_mb - self.vram_used_mb

    @property
    def vram_utilization_pct(self) -> float:
        if self.vram_total_mb == 0:
            return 0.0
        return (self.vram_used_mb / self.vram_total_mb) * 100

    def to_dict(self) -> dict:
        return {
            "gpu_index": self.gpu_index,
            "node": self.node,
            "gpu_name": self.gpu_name,
            "utilization_pct": round(self.utilization_pct, 1),
            "vram_used_mb": round(self.vram_used_mb, 1),
            "vram_total_mb": round(self.vram_total_mb, 1),
            "vram_free_mb": round(self.vram_free_mb, 1),
            "vram_utilization_pct": round(self.vram_utilization_pct, 1),
            "temperature_c": round(self.temperature_c, 1),
            "power_watts": round(self.power_watts, 1),
            "timestamp": self.timestamp,
        }


def parse_dcgm_metrics(text: str, node: str) -> list[GpuMetrics]:
    """Parse Prometheus text format from DCGM-exporter into GpuMetrics."""
    gpus: dict[int, GpuMetrics] = {}
    vram_free: dict[int, float] = {}  # Track free VRAM separately for total calc

    # Match lines like: DCGM_FI_DEV_GPU_UTIL{gpu="0",UUID="...",device="nvidia0",...} 12.3
    metric_re = re.compile(
        r'^(DCGM_FI_\w+)\{([^}]+)\}\s+([\d.eE+-]+)', re.MULTILINE
    )

    for match in metric_re.finditer(text):
        metric_name = match.group(1)
        labels_str = match.group(2)
        value = float(match.group(3))

        # Extract gpu index from labels
        gpu_match = re.search(r'gpu="(\d+)"', labels_str)
        if not gpu_match:
            continue
        gpu_idx = int(gpu_match.group(1))

        if gpu_idx not in gpus:
            gpus[gpu_idx] = GpuMetrics(gpu_index=gpu_idx, node=node)

        gpu = gpus[gpu_idx]

        # Extract GPU model name if available
        model_match = re.search(r'modelName="([^"]+)"', labels_str)
        if model_match and not gpu.gpu_name:
            gpu.gpu_name = model_match.group(1)

        if metric_name == "DCGM_FI_DEV_GPU_UTIL":
            gpu.utilization_pct = value
        elif metric_name == "DCGM_FI_DEV_FB_USED":
            gpu.vram_used_mb = value
        elif metric_name == "DCGM_FI_DEV_FB_FREE":
            vram_free[gpu_idx] = value
        elif metric_name == "DCGM_FI_DEV_GPU_TEMP":
            gpu.temperature_c = value
        elif metric_name == "DCGM_FI_DEV_POWER_USAGE":
            gpu.power_watts = value

    # Compute total VRAM after all metrics are parsed (order-independent)
    for gpu_idx, gpu in gpus.items():
        gpu.vram_total_mb = gpu.vram_used_mb + vram_free.get(gpu_idx, 0.0)

    return sorted(gpus.values(), key=lambda g: g.gpu_index)


async def fetch_gpu_metrics(node: str, dcgm_url: str) -> list[GpuMetrics]:
    """Fetch GPU metrics from a DCGM-exporter endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{dcgm_url}/metrics", timeout=5)
            resp.raise_for_status()
            return parse_dcgm_metrics(resp.text, node)
    except Exception as e:
        logger.warning("Failed to fetch DCGM metrics from %s: %s", dcgm_url, e)
        return []


async def fetch_all_gpu_metrics() -> dict[str, list[GpuMetrics]]:
    """Fetch GPU metrics from both nodes."""
    import asyncio

    node1, node2 = await asyncio.gather(
        fetch_gpu_metrics("node1", settings.dcgm_node1_url),
        fetch_gpu_metrics("node2", settings.dcgm_node2_url),
    )
    return {"node1": node1, "node2": node2}


# --- vLLM Sleep/Wake Management ---


class SleepState(str, Enum):
    AWAKE = "awake"
    SLEEPING = "sleeping"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


@dataclass
class VllmInstance:
    """Tracks a vLLM instance and its sleep state."""

    name: str
    url: str
    node: str
    gpus: list[int]
    sleep_state: SleepState = SleepState.UNKNOWN
    last_request_at: float = 0.0
    last_checked_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "node": self.node,
            "gpus": self.gpus,
            "sleep_state": self.sleep_state.value,
            "last_request_at": self.last_request_at,
            "last_checked_at": self.last_checked_at,
        }


async def check_vllm_sleeping(url: str) -> SleepState:
    """Check if a vLLM instance is sleeping."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/is_sleeping", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # vLLM returns {"is_sleeping": true/false}
                if data.get("is_sleeping", False):
                    return SleepState.SLEEPING
                return SleepState.AWAKE
            # Endpoint doesn't exist — sleep mode not enabled
            return SleepState.UNAVAILABLE
    except httpx.ConnectError:
        return SleepState.UNAVAILABLE
    except Exception as e:
        logger.warning("Failed to check sleep state for %s: %s", url, e)
        return SleepState.UNKNOWN


async def sleep_vllm(url: str, level: int = 1) -> bool:
    """Put a vLLM instance to sleep."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{url}/sleep", params={"level": level}, timeout=30)
            if resp.status_code == 200:
                logger.info("vLLM at %s slept (level %d)", url, level)
                return True
            logger.warning("Failed to sleep vLLM at %s: %d %s", url, resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.warning("Failed to sleep vLLM at %s: %s", url, e)
        return False


async def wake_vllm(url: str) -> bool:
    """Wake a sleeping vLLM instance."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{url}/wake_up", timeout=30)
            if resp.status_code == 200:
                logger.info("vLLM at %s woke up", url)
                return True
            logger.warning("Failed to wake vLLM at %s: %d %s", url, resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.warning("Failed to wake vLLM at %s: %s", url, e)
        return False


async def check_vllm_health(url: str) -> bool:
    """Check if a vLLM instance is responding."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/health", timeout=5)
            return resp.status_code == 200
    except Exception:
        return False
