"""Service catalog for the Athanor Watchdog runtime guard.

28 services across FOUNDRY (6), WORKSHOP (6), DEV (4), and VAULT (12).
The current scope is Band A remediation only (container restart) with explicit
operator and packet gates.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceCheck:
    service_id: str          # unique key, e.g. "foundry.vllm-tp4"
    node: str                # ssh alias: foundry, workshop, dev, vault
    container: str           # docker container name for restart
    url: str                 # http://, tcp://, or ssh:// scheme
    accept_codes: tuple[int, ...] = (200,)
    body_contains: str | None = None
    frequency_seconds: int = 60
    auto_remediate: bool = True
    max_restarts_per_hour: int = 3
    p0: bool = False
    manual_restart_allowed: bool = True


SERVICES: list[ServiceCheck] = [
    # FOUNDRY (.244) - 6
    ServiceCheck(
        service_id="foundry.vllm-tp4",
        node="foundry",
        container="vllm-coordinator",
        url="http://192.168.1.244:8000/v1/models",
        accept_codes=(200,),
        body_contains='"id"',
        frequency_seconds=30,
        auto_remediate=False,
        max_restarts_per_hour=0,
        p0=True,
        manual_restart_allowed=False,
    ),
    ServiceCheck(
        service_id="foundry.llama-dolphin",
        node="foundry",
        container="llama-dolphin",
        url="http://192.168.1.244:8100/health",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="foundry.agents",
        node="foundry",
        container="athanor-agents",
        url="http://192.168.1.244:9000/health",
        frequency_seconds=30,
        max_restarts_per_hour=2,
    ),
    ServiceCheck(
        service_id="foundry.gpu-orchestrator",
        node="foundry",
        container="athanor-gpu-orchestrator",
        url="http://192.168.1.244:9200/health",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="foundry.graphrag",
        node="foundry",
        container="athanor-graphrag",
        url="http://192.168.1.244:9300/health",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="foundry.speaches-tts",
        node="foundry",
        container="speaches",
        url="http://192.168.1.244:8200/v1/models",
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),

    # WORKSHOP (.225) - 6
    ServiceCheck(
        service_id="workshop.vllm-vision",
        node="workshop",
        container="vllm-vision",
        url="http://192.168.1.225:8012/v1/models",
        body_contains='"id"',
        frequency_seconds=30,
        auto_remediate=False,
        max_restarts_per_hour=0,
        p0=True,
        manual_restart_allowed=False,
    ),
    ServiceCheck(
        service_id="workshop.comfyui",
        node="workshop",
        container="comfyui",
        url="ssh://workshop/curl -s -m 3 -o /dev/null -w %{http_code} http://127.0.0.1:8188/system_stats",
        frequency_seconds=60,
        max_restarts_per_hour=2,
    ),
    ServiceCheck(
        service_id="workshop.athanor-dashboard",
        node="workshop",
        container="athanor-dashboard",
        url="http://192.168.1.225:3001/",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="workshop.athanor-eoq",
        node="workshop",
        container="athanor-eoq",
        url="http://192.168.1.225:3002/",
        accept_codes=(200, 404),
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="workshop.aesthetic-scorer",
        node="workshop",
        container="aesthetic-scorer",
        url="http://192.168.1.225:8050/",
        accept_codes=(200, 404),
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="workshop.ws-pty-bridge",
        node="workshop",
        container="athanor-ws-pty-bridge",
        url="http://192.168.1.225:3100/",
        accept_codes=(200, 404, 426),
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),

    # DEV (.189) - 4
    ServiceCheck(
        service_id="dev.vllm-embedding",
        node="dev",
        container="vllm-embedding",
        url="http://192.168.1.189:8001/v1/models",
        body_contains='"id"',
        frequency_seconds=30,
        auto_remediate=False,
        max_restarts_per_hour=0,
        p0=True,
        manual_restart_allowed=False,
    ),
    ServiceCheck(
        service_id="dev.vllm-reranker",
        node="dev",
        container="vllm-reranker",
        url="http://192.168.1.189:8003/v1/models",
        body_contains='"id"',
        frequency_seconds=30,
        max_restarts_per_hour=2,
    ),
    ServiceCheck(
        service_id="dev.cliproxyapi",
        node="dev",
        container="devstack-cliproxyapi",
        url="http://192.168.1.189:8317/v1/models",
        accept_codes=(200, 401),
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="dev.athanor-dashboard",
        node="dev",
        container="athanor-dashboard",
        url="http://192.168.1.189:3001/",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),

    # VAULT (.203) - 12
    ServiceCheck(
        service_id="vault.litellm",
        node="vault",
        container="litellm",
        url="http://192.168.1.203:4000/health/readiness",
        body_contains='"healthy"',
        frequency_seconds=15,
        max_restarts_per_hour=2,
    ),
    ServiceCheck(
        service_id="vault.redis",
        node="vault",
        container="redis",
        url="tcp://192.168.1.203:6379",
        frequency_seconds=15,
        auto_remediate=False,
        max_restarts_per_hour=0,
        manual_restart_allowed=False,
    ),
    ServiceCheck(
        service_id="vault.grafana",
        node="vault",
        container="grafana",
        url="http://192.168.1.203:3000/api/health",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.prometheus",
        node="vault",
        container="prometheus",
        url="http://192.168.1.203:9090/-/healthy",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.langfuse-web",
        node="vault",
        container="langfuse-web",
        url="http://192.168.1.203:3030/api/public/health",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.qdrant",
        node="vault",
        container="qdrant",
        url="http://192.168.1.203:6333/collections",
        frequency_seconds=60,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.neo4j",
        node="vault",
        container="neo4j",
        url="http://192.168.1.203:7474/",
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.ntfy",
        node="vault",
        container="ntfy",
        url="http://192.168.1.203:8880/v1/health",
        frequency_seconds=120,
        auto_remediate=False,
        max_restarts_per_hour=0,
        manual_restart_allowed=False,
    ),
    ServiceCheck(
        service_id="vault.n8n",
        node="vault",
        container="n8n",
        url="http://192.168.1.203:5678/healthz",
        frequency_seconds=120,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.uptime-kuma",
        node="vault",
        container="uptime-kuma",
        url="http://192.168.1.203:3009/",
        accept_codes=(200, 302),
        frequency_seconds=300,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.openwebui",
        node="vault",
        container="vault-open-webui",
        url="http://192.168.1.203:3090/",
        frequency_seconds=300,
        max_restarts_per_hour=3,
    ),
    ServiceCheck(
        service_id="vault.homeassistant",
        node="vault",
        container="homeassistant",
        url="http://192.168.1.203:8123/api/",
        accept_codes=(200, 401),
        frequency_seconds=300,
        max_restarts_per_hour=2,
    ),
]


SERVICES_BY_ID: dict[str, ServiceCheck] = {svc.service_id: svc for svc in SERVICES}
